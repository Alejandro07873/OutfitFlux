"""Create the GitHub release ZIP, excluding all local user data."""
import argparse
import hashlib
from pathlib import Path
import zipfile

parser=argparse.ArgumentParser()
parser.add_argument('distribution',type=Path)
parser.add_argument('--output',type=Path,default=Path('release/OutfitFlux-windows-x64.zip'))
args=parser.parse_args()
root=args.distribution.resolve()
if not (root/'OutfitFlux.exe').is_file() or not (root/'_internal').is_dir():
    raise SystemExit('Expected a complete OutfitFlux distribution')
args.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    archive.write(root/'OutfitFlux.exe','OutfitFlux/OutfitFlux.exe')
    for path in sorted((root/'_internal').rglob('*')):
        if path.is_symlink():raise ValueError('Symbolic link in distribution')
        if path.is_file():archive.write(path,'OutfitFlux/'+path.relative_to(root).as_posix())
    for name in ['README.md','CHANGELOG.md','STUDIO.md','UPDATES.md']:
        path=Path(name)
        if path.is_file():archive.write(path,'OutfitFlux/'+name)
    for folder in ['docs', 'branding']:
        for path in sorted(Path(folder).rglob('*')):
            if path.is_file() and not path.is_symlink() and path.suffix.lower() in ('.md','.svg','.png','.ico'):
                archive.write(path,'OutfitFlux/'+path.as_posix())
checksum=hashlib.sha256(args.output.read_bytes()).hexdigest()
args.output.with_suffix('.zip.sha256').write_text(checksum+'  '+args.output.name+'\n')
print(args.output.resolve())
print('SHA256:',checksum)
