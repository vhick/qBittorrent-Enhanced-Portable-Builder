"""Extract upstream full-resolution Windows PE icon, keeping original artwork."""
import struct
import sys
from pathlib import Path
from PIL import Image
import pefile


def extract(exe, dest):
    pe = pefile.PE(str(exe))
    icons = {}
    groups = []
    if not hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
        raise RuntimeError('Executable has no embedded Windows icon resource.')
    for kind in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if kind.id == pefile.RESOURCE_TYPE['RT_ICON']:
            for id_entry in kind.directory.entries:
                for lang in id_entry.directory.entries:
                    r = lang.data.struct
                    icons[id_entry.id] = pe.get_data(r.OffsetToData, r.Size)
        if kind.id == pefile.RESOURCE_TYPE['RT_GROUP_ICON']:
            for id_entry in kind.directory.entries:
                for lang in id_entry.directory.entries:
                    r = lang.data.struct
                    groups.append(pe.get_data(r.OffsetToData, r.Size))
    prepared=[]
    for group in groups:
        reserved, kind, count = struct.unpack_from('<HHH', group)
        if reserved != 0 or kind != 1:
            continue
        rows=[]
        for i in range(count):
            chunk = group[6+i*14:6+(i+1)*14]
            width, height, colors, unused, planes, bpp, size, icon_id = struct.unpack('<BBBBHHIH',chunk)
            if icon_id in icons:
                rows.append((width,height,colors,unused,planes,bpp,icons[icon_id]))
        if rows:
            prepared.append(rows)
    if not prepared:
        raise RuntimeError('Unable to recover original ICO group')
    selection=max(prepared,key=lambda group:(len(group),sum(len(x[-1]) for x in group)))
    offset=6+len(selection)*16
    toc=[]
    data=[]
    for w,h,c,u,p,b,blob in selection:
        toc.append(struct.pack('<BBBBHHII',w,h,c,u,p,b,len(blob),offset))
        data.append(blob)
        offset+=len(blob)
    dest=Path(dest)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(struct.pack('<HHH',0,1,len(selection))+b''.join(toc)+b''.join(data))
    with Image.open(dest) as source:
        for size in (16,32,75,128):
            source.copy().convert('RGBA').resize((size,size),Image.Resampling.LANCZOS).save(dest.parent/f'appicon_{size}.png')
    print('Upstream original icon extracted, resolutions:',len(selection))


if __name__ == '__main__':
    extract(Path(sys.argv[1]),Path(sys.argv[2]))
