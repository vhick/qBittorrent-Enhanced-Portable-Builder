"""Package extracted official Windows installer files and native-profile launcher."""
from pathlib import Path
import argparse
import json
import shutil
import zipfile
from PIL import Image

APP_NAME = "qBittorrentEnhancedPortable"
SKIP_FILES = {"uninst.exe", "uninstall.exe", "uninstaller.exe", "uninst.dat", "installoptions.ini"}
SKIP_DIRS = {"$pluginsdir", "$exedir", "$_outdir", "$_temp", "$_tempdir", "__macosx"}


def find_payload(extraction_root):
    candidates = [f for f in extraction_root.rglob("*") if f.is_file() and f.name.lower() == "qbittorrent.exe"]
    if not candidates:
        raise RuntimeError("7-Zip extracted no qbittorrent.exe. Installer format/layout may have changed.")
    def score(path):
        siblings = {p.name.lower() for p in path.parent.iterdir()}
        return (int("qt.conf" in siblings) * 10 + int("platforms" in siblings) * 10 +
                sum(n.endswith(".dll") for n in siblings), -len(path.parts))
    candidates.sort(key=score, reverse=True)
    selected = candidates[0].parent
    print("Discovered upstream program directory:", selected)
    return selected


def copy_program(source, destination):
    if not (source / "qbittorrent.exe").exists() and not any(p.name.lower() == "qbittorrent.exe" for p in source.iterdir()):
        raise RuntimeError("Program folder lacks qbittorrent.exe")
    destination.mkdir(parents=True, exist_ok=True)
    for entry in source.iterdir():
        if entry.name.lower() in SKIP_FILES or entry.name.lower() in SKIP_DIRS or entry.name.lower().startswith("$pluginsdir"):
            continue
        dest = destination / entry.name
        if entry.is_symlink():
            raise RuntimeError("Unsafe symlink in extracted payload: " + str(entry))
        if entry.is_dir():
            shutil.copytree(entry, dest, symlinks=False)
        elif entry.is_file():
            shutil.copy2(entry, dest)
    exe = destination / "qbittorrent.exe"
    if not exe.exists() or exe.stat().st_size < 500_000:
        raise RuntimeError("Packaged qBittorrent.exe is absent or too small.")
    print("Copied upstream application files:", len(list(destination.rglob("*"))), "entries")


def build(metadata, payload_root, work_dir, output_dir):
    version = metadata["tag"].removeprefix("release-")
    root = work_dir / APP_NAME
    if root.exists():
        shutil.rmtree(root)
    app_dir = root / "App" / "qBittorrent"
    info_dir = root / "App" / "AppInfo"
    other = root / "Other"
    source = other / "Source"
    for folder in (app_dir, info_dir, source, root / "Data" / "profile", root / "Data" / "Downloads"):
        folder.mkdir(parents=True, exist_ok=True)
    copy_program(find_payload(payload_root), app_dir)
    launcher_exe = work_dir / (APP_NAME + ".exe")
    icon = work_dir / "appicon.ico"
    if not launcher_exe.exists() or not icon.exists():
        raise RuntimeError("Launcher or original icon was not generated.")
    shutil.copy2(launcher_exe, root / launcher_exe.name)
    shutil.copy2(icon, info_dir / "appicon.ico")
    with Image.open(icon) as icon_image:
        for size in (16, 32, 48, 128):
            image = icon_image.copy().convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            image.save(info_dir / ("appicon_%d.png" % size))
    appinfo = """[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=qBittorrent Enhanced Edition Portable
AppID=qBittorrentEnhancedPortable
Publisher=c0re100 and qBittorrent contributors
Homepage=https://github.com/c0re100/qBittorrent-Enhanced-Edition
Category=Internet
Description=Unofficial enhanced qBittorrent client with a self-contained profile
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion={version}
DisplayVersion={version}

[Control]
Icons=1
Start=qBittorrentEnhancedPortable.exe
""".format(version=version)
    (info_dir / "appinfo.ini").write_text(appinfo, encoding="utf-8")
    shutil.copy2(Path("launcher/qBittorrentEnhancedPortable.cs"), source / "qBittorrentEnhancedPortable.cs")
    (source / "upstream-release.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (other / "PORTABLE-README.txt").write_text(
        "qBittorrent Enhanced Edition Portable " + version + "\n\n"
        "Run qBittorrentEnhancedPortable.exe (at the root).\n"
        "Settings, resume data and torrent metadata: Data\\profile\\\n"
        "Default first-run downloads: Data\\Downloads\\\n"
        "Launcher uses the official --profile option, NOT an installed Windows profile.\n\n"
        "UPGRADING: Close qBittorrent completely. Replace App, Other, and the root launcher\n"
        "with the new ZIP's files. KEEP your original Data folder unchanged.\n\n"
        "MOVING TO ANOTHER PC/DRIVE: The launcher updates its own default Data\\Downloads\n"
        "preference if the drive path changes. Existing active torrent save paths can still\n"
        "contain old absolute drive paths. Review/repair them before resuming torrents.\n\n"
        "Windows file associations, protocol handlers, shell integration and firewall rules\n"
        "are NOT installed by this builder. Enabling such features inside the app is\n"
        "optional and may write Windows settings; disable them for maximum portability.\n"
        "A torrent client can create OS network/firewall caches outside the package;\n"
        "this is not an isolation sandbox. Use torrents legally and responsibly.\n",
        encoding="utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / ("qBittorrent-Enhanced-Portable-" + version + "-Windows-x64.zip")
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root.parent).as_posix()
            if path.is_dir():
                z.writestr(rel + "/", b"")
            else:
                z.write(path, rel)
    print("PACKAGED:", dest, "(" + str(dest.stat().st_size) + " bytes)")
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extracted", default="work/extracted")
    ap.add_argument("--download", default="work/download")
    ap.add_argument("--work", default="work")
    ap.add_argument("--output", default="dist")
    a = ap.parse_args()
    manifest = json.loads((Path(a.download) / "release.json").read_text(encoding="utf-8"))
    build(manifest, Path(a.extracted), Path(a.work), Path(a.output))


if __name__ == "__main__":
    main()
