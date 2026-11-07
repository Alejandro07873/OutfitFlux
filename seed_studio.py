"""Copy the local prepared library into the generated portable distribution."""
import shutil
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    source = root / 'assets'
    destination = root / (sys.argv[1] if len(sys.argv) > 1 else 'dist/OutfitFlux')
    if not (destination / 'OutfitFlux.exe').is_file():
        raise SystemExit('Compila primero: python -m PyInstaller --noconfirm aurora.spec')
    files = list((source / 'HerovsGame/Content/Character').rglob('*.png'))
    files += list((source / 'HerovsGame/Content/Character').glob('Ch*/PA_*.json'))
    # This is a local migration, retaining this user's routes and preferences.
    files += list((source / 'config').rglob('*.json'))
    for file in files:
        output = destination / 'assets' / file.relative_to(source)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Existing portable settings and history belong to that installation.
        if not output.exists():
            shutil.copy2(file, output)
    shutil.copy2(root / 'STUDIO.md', destination / 'STUDIO.md')
    (destination / 'Abrir interfaz clasica.cmd').write_text(
        '@echo off\nstart "" "%~dp0OutfitFlux.exe" --classic\n', encoding='utf-8')
    print(f'Biblioteca preparada: {len(files)} archivos disponibles para la instalación portable.')


if __name__ == '__main__':
    main()
