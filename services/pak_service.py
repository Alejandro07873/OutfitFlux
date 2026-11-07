"""Read-only inspection and guarded extraction of mod PAKs."""
from pathlib import Path, PurePosixPath
import re
from services.process_service import run_hidden_command, raise_if_cancelled
from util import repakPath


def validate_entry(name):
    name = name.replace('\\', '/')
    path = PurePosixPath(name)
    if not name or path.is_absolute() or any(p in ('..', '.') or ':' in p for p in path.parts):
        raise ValueError(f"Ruta interna no válida: {name}")
    return path.as_posix()


def list_pak(path, cancel=None):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    result = run_hidden_command([repakPath, 'list', str(path)], cancel)
    entries = [validate_entry(s.strip()) for s in result['stdout'].splitlines() if s.strip()]
    if not entries:
        raise ValueError('El PAK no contiene archivos.')
    if len({s.casefold() for s in entries}) != len(entries):
        raise ValueError('El PAK contiene rutas duplicadas (ignorando mayúsculas).')
    return entries


def extract_pak(path, destination, cancel=None):
    entries = list_pak(path, cancel)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError('La extracción requiere una carpeta vacía.')
    run_hidden_command([repakPath, 'unpack', '-o', str(destination), str(path)], cancel)
    for entry in entries:
        raise_if_cancelled(cancel)
        if not (destination / entry).is_file():
            raise RuntimeError(f'Extracción incompleta: {entry}')
    return entries


def inspect_pak(path, cancel=None):
    entries = list_pak(path, cancel)
    meshes = [s for s in entries if '/Mesh/' in s and Path(s).name.startswith('SK_') and s.endswith('.uasset')
              and not re.search(r'_(PhysicsAsset|Skeleton|Clothing|Cloth|Physics)(?:_\d+)?\.uasset$', s, re.I)]
    characters = sorted({part for s in entries for part in s.split('/') if len(part) == 5 and part.startswith('Ch') and part[2:].isdigit()})
    missing = [s for s in entries if s.endswith('.uexp') and s[:-5] + '.uasset' not in entries]
    return {'path': str(Path(path).resolve()), 'entries': entries, 'meshes': meshes,
            'characters': characters, 'orphan_uexp': missing, 'size': Path(path).stat().st_size}


def compare_paks(paths, cancel=None):
    owners = {}
    for path in paths:
        for entry in list_pak(path, cancel):
            owners.setdefault(entry.casefold(), []).append(str(path))
    return {entry: files for entry, files in owners.items() if len(files) > 1}
