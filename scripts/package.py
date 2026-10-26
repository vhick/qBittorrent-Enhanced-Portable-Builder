"""Build one ZIP with a single PortableApps-compliant parent folder."""
import json
from pathlib import Path
import struct
import zipfile


def verify(root):
    expected = ['qBittorrentEnhancedPortable.exe','App/qBittorrent/qbittorrent.exe',
                'App/Python/python.exe','App/Python/python314.zip','App/Python/python314._pth',
                'App/AppInfo/appinfo.ini','App/AppInfo/appicon.ico',
                'Data/profile','Data/Downloads','Other/build-info.json','Other/Launcher-Source.cs']
    for path in expected:
        if not (root/path).exists():
            raise RuntimeError('Missing required package item: '+path)
    for path in ('qBittorrentEnhancedPortable.exe','App/qBittorrent/qbittorrent.exe','App/Python/python.exe'):
        with (root/path).open('rb') as binary:
            magic = binary.read(2)
        if magic != b'MZ':
            raise RuntimeError('Invalid Windows executable: '+path)
    icon=(root/'App/AppInfo/appicon.ico').read_bytes()
    if len(icon)<100 or icon[:4]!=b'\0\0\1\0':
        raise RuntimeError('Missing original multi-resolution icon')
    if any(f.is_file() for f in (root/'Data').rglob('*')):
        raise RuntimeError('Data must be empty of user files on upgrades')
    source=(root/'Other/Launcher-Source.cs').read_text(encoding='utf-8')
    if 'Search\\pythonExecutablePath' not in source or '--portable-self-test' not in source:
        raise RuntimeError('Missing bundled Python configuration in portable launcher')
    print('PASS: full program, original icon, embedded Python, empty update-safe Data, native launcher')


def pack(root, output):
    root=Path(root).resolve()
    verify(root)
    output=Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for item in sorted(root.rglob('*')):
            name=item.relative_to(root.parent).as_posix()
            if item.is_dir():
                z.writestr(name+'/',b'')
            elif item.is_file():
                z.write(item,name)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert all(n.startswith('qBittorrentEnhancedPortable/') for n in z.namelist())
    print('Final portable ZIP:',output,'size',output.stat().st_size)


if __name__=='__main__':
    import sys
    pack(sys.argv[1],sys.argv[2])
