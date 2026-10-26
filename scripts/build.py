"""Stage official qBittorrent Enhanced setup and CPython embedded Windows runtime.
Do not run the installer; extract with the Windows runner's installed 7-Zip.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

REPO = 'c0re100/qBittorrent-Enhanced-Edition'
PYTHON_VERSION = '3.14.10'
PYTHON_SHA256 = '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
PYTHON_URI = f'https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip'
USER_AGENT = 'qBittorrent-Enhanced-PortableBuilder-v1.2'


def api_json(uri):
    hdr = {'User-Agent': USER_AGENT, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    if os.environ.get('GH_TOKEN'):
        hdr['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(uri, headers=hdr), timeout=60) as response:
        return json.load(response)


def select_asset(assets):
    matches = [a for a in assets if re.fullmatch(r'qbittorrent[_-]enhanced_[0-9.]+_x64_setup\.exe', a['name'], re.I)]
    if len(matches) != 1:
        raise RuntimeError('Expected exactly one official Windows x64 installer. Found: ' + ', '.join(a['name'] for a in assets))
    return matches[0]


def download(uri, target, expected=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(uri, headers={'User-Agent': USER_AGENT}), timeout=150) as response, target.open('wb') as f:
        while data := response.read(1024 * 1024):
            f.write(data)
            h.update(data)
    digest = h.hexdigest()
    if target.stat().st_size < 100_000:
        raise RuntimeError('Downloaded file is unexpectedly small')
    if expected and digest.lower() != expected.lower():
        target.unlink(missing_ok=True)
        raise RuntimeError('SHA256 mismatch for ' + uri)
    return digest


def safe_unzip(archive, dest):
    with zipfile.ZipFile(archive) as z:
        for m in z.infolist():
            name = m.filename.replace('\\', '/')
            if (name.startswith('/') or '..' in name.split('/') or re.match(r'^[a-zA-Z]:', name) or
                    ((m.external_attr >> 16) & 0o170000) == 0o120000):
                raise RuntimeError('Unsafe ZIP entry: ' + name)
        z.extractall(dest)


def pick_program(extracted):
    exes = [p for p in extracted.rglob('*') if p.is_file() and p.name.lower() == 'qbittorrent.exe']
    if not exes:
        raise RuntimeError('Installer does not contain qbittorrent.exe. Check upstream layout.')
    def quality(path):
        s = {x.name.lower() for x in path.parent.iterdir()}
        return (10 * int('platforms' in s) + 10 * int('qt.conf' in s) + len([x for x in s if x.endswith('.dll')]), -len(path.parts))
    exes.sort(key=quality, reverse=True)
    return exes[0]


def stage_program(found, dest):
    dest.mkdir(parents=True, exist_ok=True)
    blacklist = {'uninst.exe', 'uninstall.exe', 'uninstaller.exe', 'uninst.dat', '$pluginsdir'}
    for x in found.parent.iterdir():
        if x.name.lower() in blacklist or x.name.lower().startswith('$') or x.is_symlink():
            continue
        output = dest / x.name
        if x.is_dir():
            shutil.copytree(x, output, symlinks=False)
        elif x.is_file():
            shutil.copy2(x, output)
    if not (dest / 'qbittorrent.exe').is_file():
        raise RuntimeError('Missing qBittorrent binary in stage directory')


def stage_python(package, dest):
    dest.mkdir(parents=True, exist_ok=True)
    safe_unzip(package, dest)
    if not (dest / 'python.exe').is_file():
        raise RuntimeError('Embedded CPython missing python.exe')
    if not (dest / 'python314.zip').is_file():
        raise RuntimeError('Embedded CPython missing python314.zip standard library')
    # Leave upstream ._pth isolation in place. qBittorrent's nova2.py explicitly
    # adds its own directory to sys.path when run in isolated Python mode.
    if not (dest / 'python314._pth').is_file():
        raise RuntimeError('Embedded CPython missing isolated-path configuration')


def metadata(root, tag, qbinfo):
    import textwrap
    match = re.fullmatch(r'release-(\d+)\.(\d+)\.(\d+)\.(\d+)', tag)
    if not match:
        raise RuntimeError('Unexpected release tag format: ' + tag)
    info = root / 'App' / 'AppInfo'
    info.mkdir(parents=True, exist_ok=True)
    major, minor, patch, extra = match.groups()
    (info / 'appinfo.ini').write_text(f'''[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=qBittorrent Enhanced Edition Portable
AppID=qBittorrentEnhancedPortable
Publisher=c0re100 & qBittorrent contributors
Homepage=https://github.com/{REPO}
Category=Internet
Description=qBittorrent Enhanced with portable settings, search plugins, and Python
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion={major}.{minor}.{patch}.{extra}
DisplayVersion={major}.{minor}.{patch}.{extra}

[Control]
Icons=1
Start=qBittorrentEnhancedPortable.exe
''', encoding='utf-8')
    other = root / 'Other'
    other.mkdir(parents=True, exist_ok=True)
    (other / 'build-info.json').write_text(json.dumps({**qbinfo, 'python_version': PYTHON_VERSION,
        'python_sha256': PYTHON_SHA256, 'python_download_url': PYTHON_URI}, indent=2)+'\n', encoding='utf-8')
    (other / 'SOURCE-LICENSES.txt').write_text('''Original application: https://github.com/c0re100/qBittorrent-Enhanced-Edition
License: consult the original application's COPYING/license and repo.
Portable Python: https://www.python.org/downloads/release/python-31410/
Python Software Foundation License: https://docs.python.org/3/license.html
qBittorrent plugins: https://github.com/qbittorrent/search-plugins
Third-party search plugins can execute Python code; only install trusted plugins.
''', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='latest')
    ap.add_argument('--out', default='work')
    opts = ap.parse_args()
    if opts.tag != 'latest' and not re.fullmatch(r'release-\d+(?:\.\d+){3}', opts.tag):
        raise ValueError('Only latest or release-X.Y.Z.N tags are supported')
    uri = f'https://api.github.com/repos/{REPO}/releases/' + ('latest' if opts.tag == 'latest' else 'tags/'+opts.tag)
    release = api_json(uri)
    if release.get('draft') or release.get('prerelease'):
        raise RuntimeError('No draft or prerelease asset accepted')
    asset = select_asset(release.get('assets', []))
    src = asset['browser_download_url']
    if not src.startswith(f'https://github.com/{REPO}/releases/download/'):
        raise RuntimeError('Unexpected official installer download URL')
    root = Path(opts.out).resolve()
    root.mkdir(parents=True, exist_ok=True)
    application = root / 'qBittorrentEnhancedPortable'
    if application.exists():
        shutil.rmtree(application)
    app = application / 'App'
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        setup = temp / 'setup.exe'
        sha = download(src, setup, (asset.get('digest') or '').removeprefix('sha256:') or None)
        extracted = temp / 'extracted'
        extracted.mkdir()
        # Official installer is a self-extracting archive, not executed.
        seven = shutil.which('7z.exe') or r'C:\Program Files\7-Zip\7z.exe'
        subprocess.run([seven, 'x', '-y', '-o'+str(extracted), str(setup)], check=True, timeout=180)
        chosen = pick_program(extracted)
        stage_program(chosen, app / 'qBittorrent')
        python_archive = temp / 'python-embed.zip'
        download(PYTHON_URI, python_archive, PYTHON_SHA256)
        stage_python(python_archive, app / 'Python')
    (application / 'Data' / 'profile').mkdir(parents=True)
    (application / 'Data' / 'Downloads').mkdir(parents=True)
    qb = {'tag': release['tag_name'], 'upstream': f'https://github.com/{REPO}',
          'installer': asset['name'], 'installer_sha256': sha,
          'installer_verified_against_github': bool(asset.get('digest'))}
    metadata(application, release['tag_name'], qb)
    print('PACKAGED SOURCE: ', chosen.name)
    print('APP VERSION:', release['tag_name'])
    print('PYTHON VERSION:', PYTHON_VERSION)
    print('APP DIR:', application)


if __name__ == '__main__':
    main()
