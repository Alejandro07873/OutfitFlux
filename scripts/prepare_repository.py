"""Create a small source-only repository folder; never copy user data or binaries."""
import argparse
import shutil
import zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=ROOT / 'repository-ready/OutfitFlux')
parser.add_argument('--refresh', action='store_true', help='Update only the explicit source-file allowlist')
parser.add_argument('--archive', type=Path, help='Also create a source ZIP from the same allowlist')
args = parser.parse_args()
output = args.output.resolve()
if output == ROOT or ROOT.is_relative_to(output):
    raise SystemExit('Choose a separate output folder, not the project or its parent.')
if output.exists() and any(output.iterdir()) and not args.refresh:
    raise SystemExit('Output must be empty; existing source files are never overwritten.')
output.mkdir(parents=True, exist_ok=True)
files = [*ROOT.glob('*.py'), *[ROOT / name for name in ['README.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'STUDIO.md', 'UPDATES.md', '.gitignore', 'aurora.spec', 'requirements.txt', 'requirements-dev.txt']]]
for directory in ['ui', 'services', 'workers', 'tests', 'scripts', 'docs', 'branding', '.github']:
    files.extend(p for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix.lower() in {'.py','.md','.txt','.png','.ico','.svg','.yml','.yaml'})
for path in files:
    relative = path.relative_to(ROOT)
    if path.is_symlink():
        raise SystemExit('Refusing symbolic link: ' + str(relative))
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
print(str(output))
print(str(len(files)) + ' files; no local game data or runtime binaries included.')

if args.archive:
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, 'OutfitFlux/' + path.relative_to(ROOT).as_posix())
    print(args.archive.resolve())
