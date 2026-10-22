"""Download the official c0re100 Windows x64 installer from its GitHub release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, urlopen

REPO = "c0re100/qBittorrent-Enhanced-Edition"
BASE = "https://api.github.com/repos/" + REPO + "/releases/"


def get_json(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "qBittorrentEnhancedPortableBuilder-v1"}
    token = os.environ.get("GH_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=45) as response:
        return json.load(response)


def find_installer(assets):
    possible = [a for a in assets if re.search(r"(?i)^qbittorrent[_-]enhanced[_-].*x64.*(?:setup|installer)\.exe$", a["name"])]
    if len(possible) == 1:
        return possible[0]
    if len(possible) > 1:
        exact = [a for a in possible if re.match(r"(?i)^qbittorrent_enhanced_[0-9.]+_x64_setup\.exe$", a["name"])]
        if len(exact) == 1:
            return exact[0]
    raise RuntimeError("Cannot uniquely identify the official Windows x64 installer. Available files:\n" + "\n".join(a["name"] for a in assets))


def download(url, target):
    if not url.startswith("https://github.com/c0re100/qBittorrent-Enhanced-Edition/releases/download/"):
        raise RuntimeError("Unexpected installer download host/path: " + url)
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "qBittorrentEnhancedPortableBuilder-v1", "Accept": "application/octet-stream"})
            with urlopen(req, timeout=120) as inp, target.open("wb") as out:
                while True:
                    block = inp.read(1024 * 1024)
                    if not block:
                        break
                    out.write(block)
            if target.stat().st_size < 2_000_000:
                raise RuntimeError("Installer is unusually small; download may be incomplete.")
            return
        except Exception:
            target.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="latest")
    parser.add_argument("--output-dir", default="work/download")
    args = parser.parse_args()
    if args.tag != "latest" and not re.fullmatch(r"release-[0-9]+(?:\.[0-9]+)+", args.tag):
        raise RuntimeError("Use 'latest' or an official release tag such as release-5.2.4.10")
    url = BASE + ("latest" if args.tag == "latest" else "tags/" + args.tag)
    release = get_json(url)
    if release.get("draft") or release.get("prerelease"):
        raise RuntimeError("Only published stable releases are accepted.")
    asset = find_installer(release.get("assets", []))
    target_dir = Path(args.output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / asset["name"]
    print("Official release:", release["tag_name"], flush=True)
    print("Installer:", asset["name"], flush=True)
    download(asset["browser_download_url"], target)
    actual = hashlib.sha256(target.read_bytes()).hexdigest().lower()
    expected = (asset.get("digest") or "").lower()
    if expected:
        if not expected.startswith("sha256:") or actual != expected.removeprefix("sha256:"):
            target.unlink(missing_ok=True)
            raise RuntimeError("Official GitHub SHA256 digest verification FAILED.")
        print("GitHub SHA256 verification: PASS", flush=True)
    else:
        print("WARNING: GitHub did not publish an asset digest. Local SHA256:", actual, flush=True)
    manifest = {"repo": REPO, "tag": release["tag_name"], "asset": asset["name"], "sha256": actual,
                "sha256_verified_against_github": bool(expected), "release_url": release["html_url"]}
    (target_dir / "release.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Installer saved:", target, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print("ERROR:", ex, file=sys.stderr)
        sys.exit(1)
