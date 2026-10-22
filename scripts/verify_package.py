"""Fail the workflow when the generated portable ZIP misses critical elements."""
from pathlib import Path
import struct
import sys
import zipfile


def verify(target):
    if not target.is_file():
        raise AssertionError("Missing packaged ZIP: " + str(target))
    with zipfile.ZipFile(target) as f:
        root = "qBittorrentEnhancedPortable/"
        files = set(f.namelist())
        required = [
            root + "qBittorrentEnhancedPortable.exe",
            root + "App/qBittorrent/qbittorrent.exe",
            root + "App/AppInfo/appinfo.ini",
            root + "App/AppInfo/appicon.ico",
            root + "App/AppInfo/appicon_16.png",
            root + "App/AppInfo/appicon_32.png",
            root + "Other/PORTABLE-README.txt",
            root + "Other/Source/upstream-release.json",
            root + "Data/profile/",
            root + "Data/Downloads/",
        ]
        missing = sorted(set(required) - files)
        if missing:
            raise AssertionError("Missing entries: " + ", ".join(missing))
        if any(not name.startswith(root) or ".." in Path(name).parts for name in files):
            raise AssertionError("Unexpected file outside the top-level portable folder")
        if root + "App/qBittorrent/profile/" in files:
            raise AssertionError("An in-App profile would be lost during upgrades")
        for name in (root + "App/qBittorrent/qbittorrent.exe", root + "qBittorrentEnhancedPortable.exe"):
            with f.open(name) as binary:
                if binary.read(2) != b"MZ":
                    raise AssertionError(name + " is not a Windows executable")
        with f.open(root + "App/AppInfo/appicon.ico") as i:
            data = i.read(6)
            if len(data) != 6 or struct.unpack("<HHH", data)[0:2] != (0, 1):
                raise AssertionError("Official .ico header is invalid")
        info = f.read(root + "App/AppInfo/appinfo.ini").decode("utf-8")
        if "Start=qBittorrentEnhancedPortable.exe" not in info:
            raise AssertionError("PortableApps Menu entry is missing")
        # New packages must NOT overwrite existing user settings/torrent data.
        if any(name.startswith(root + "Data/") and not name.endswith("/") for name in files):
            raise AssertionError("The new ZIP contains data that would overwrite user data on upgrade")
    print("Portable ZIP verified:", target)


if __name__ == "__main__":
    result_files = list(Path("dist").glob("*.zip"))
    if len(result_files) != 1:
        print("Exactly one application ZIP is required; found", len(result_files), file=sys.stderr)
        sys.exit(1)
    verify(result_files[0])
