"""Isolated export pipeline. Never edits the source mod or shared assets/mod."""
import json
import os
import re
import tempfile
import shutil
from pathlib import Path, PurePosixPath
from services.process_service import ExportCancelled, raise_if_cancelled, run_hidden_command
from services.pak_service import extract_pak, list_pak, validate_entry
from services.json_store import write_json
from util import uejsonPath, unrealPak, MOD_DIR


def normalize_export_path(selected_path):
    path = str(selected_path or '').strip()
    if not path:
        raise ValueError('Selecciona una ruta de salida.')
    root, _ = os.path.splitext(path)
    if not re.search(r'(_P|\-WindowsNoEditor_P)(\(\d+\))?$', root, re.I):
        root += '_P'
    return root + '.pak'


def ensure_unique_output_path(path):
    path = Path(normalize_export_path(path))
    candidate = path
    index = 2
    while candidate.exists():
        candidate = path.with_name(f'{path.stem}({index}){path.suffix}')
        index += 1
    return str(candidate)


def validate_target(selected_skin):
    value = validate_entry(str(selected_skin))
    if not re.fullmatch(r'Ch\d{3}/Model/[A-Za-z0-9_\-/]+/Mesh/SK_[A-Za-z0-9_]+', value):
        raise ValueError(f'Ruta de traje no admitida: {value}')
    return value


def patch_mesh_json(json_path, original_filename, selected_skin):
    target = validate_target(selected_skin)
    original = Path(original_filename).stem
    new_name = PurePosixPath(target).name
    with open(json_path, encoding='utf-8') as stream:
        data = json.load(stream)
    if not isinstance(data, dict) or not isinstance(data.get('NameMap'), list) or not isinstance(data.get('Exports'), list):
        raise ValueError('UEJSON no devolvió un documento de asset válido.')
    changes = 0
    for index, name in enumerate(data['NameMap']):
        if not isinstance(name, str):
            continue
        replacement = name
        if name.casefold() == original.casefold():
            replacement = new_name
        elif '/Character/' in name:
            package, separator, obj = name.partition('.')
            if package.rsplit('/', 1)[-1].casefold() == original.casefold():
                replacement = package.partition('/Character/')[0] + '/Character/' + target
                if separator:
                    replacement += '.' + (new_name if obj.casefold() == original.casefold() else obj)
        if replacement != name:
            data['NameMap'][index] = replacement
            changes += 1
    matched = False
    for export in data['Exports']:
        if isinstance(export, dict) and str(export.get('ObjectName', '')).casefold() == original.casefold():
            export['ObjectName'] = new_name
            matched = True
    if not matched:
        raise ValueError('No se encontró el objeto exacto de la malla; no se aplicará un reemplazo ambiguo.')
    write_json(json_path, data)
    return changes


def find_current_mod_mesh(root=MOD_DIR, selected_mesh=None):
    root = Path(root).resolve()
    if selected_mesh:
        mesh = (root / validate_entry(selected_mesh)).resolve()
        if not mesh.is_relative_to(root) or not mesh.is_file():
            raise ValueError('La malla seleccionada no pertenece al mod.')
        candidates = [mesh]
    else:
        candidates = [p for p in root.rglob('SK_*.uasset') if p.parent.name == 'Mesh'
                      and not re.search(r'_(PhysicsAsset|Skeleton|Clothing|Cloth|Physics)(?:_\d+)?$', p.stem, re.I)]
    if len(candidates) != 1:
        raise ValueError(f'Se detectaron {len(candidates)} mallas. Selecciona una malla de origen.')
    mesh = candidates[0]
    return {'mesh_file_path': str(mesh), 'mesh_dir': str(mesh.parent), 'mesh_filename': mesh.name, 'mesh_stem': mesh.stem}


def move_rebuilt_mesh_files(mesh_dir, original_filename, selected_skin, workspace=MOD_DIR):
    target = validate_target(selected_skin)
    original = Path(mesh_dir) / original_filename
    destination = Path(workspace) / 'HerovsGame/Content/Character' / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    moved = []
    for suffix in ['.uasset', '.uexp', '.ubulk']:
        source = original.with_suffix(suffix)
        dest = destination.with_suffix(suffix)
        if not source.exists():
            continue
        if source.resolve() != dest.resolve():
            if dest.exists():
                raise FileExistsError(f'El mod ya incluye el destino: {dest.name}')
            os.replace(source, dest)
        moved.append(str(dest))
    if not destination.with_suffix('.uasset').is_file():
        raise RuntimeError('No se reconstruyó la malla de salida.')
    return moved


def create_final_pak(export_path, is_cancelled_callback=None, workspace=MOD_DIR, overwrite=False):
    output = Path(export_path).resolve()
    root = Path(workspace).resolve()
    if output.is_relative_to(root):
        raise ValueError('La salida no puede estar dentro de los archivos que se empaquetan.')
    if output.exists() and not overwrite:
        raise FileExistsError(f'El destino ya existe: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    files = [p for p in root.rglob('*') if p.is_file()]
    if not files:
        raise ValueError('No hay archivos para empaquetar.')
    expected = set()
    for file in files:
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError('No se admiten enlaces a archivos externos.')
        relative = file.relative_to(root).as_posix()
        validate_entry(relative)
        if '"' in str(file):
            raise ValueError('Ruta no válida para UnrealPak.')
        expected.add(relative.casefold())
    # Stage alongside the destination, so publication stays on the same volume.
    with tempfile.TemporaryDirectory(prefix='.aurora-', dir=output.parent) as temporary:
        temporary = Path(temporary)
        listing = temporary / 'files.txt'
        listing.write_text('\n'.join(f'"{p}" "../../../{p.relative_to(root).as_posix()}"' for p in files), encoding='utf-8')
        staged = temporary / 'result_P.pak'
        run_hidden_command([unrealPak, str(staged), f'-create={listing}', '-compress'], is_cancelled_callback)
        if not staged.is_file() or staged.stat().st_size == 0:
            raise RuntimeError('UnrealPak no produjo un archivo válido.')
        actual = {entry.casefold() for entry in list_pak(staged, is_cancelled_callback)}
        if actual != expected:
            raise RuntimeError('El contenido del PAK no coincide con el manifiesto de exportación.')
        raise_if_cancelled(is_cancelled_callback)
        if overwrite:
            os.replace(staged, output)
        else:
            # Windows rename fails if destination appeared since initial validation.
            if os.name == 'nt':
                os.rename(staged, output)
            else:
                os.link(staged, output)
    return str(output)


def export_mod_to_skin(mod_file, selected_skin, output_path, is_cancelled_callback=None,
                       source_mesh=None, allow_cross_character=False, overwrite=False, extracted_source=None,
                       progress_callback=None):
    def stage(step, name):
        if progress_callback:
            progress_callback(step, name)
    stage(0, 'preparing')
    target = validate_target(selected_skin)
    source_path = Path(mod_file).resolve()
    output = Path(normalize_export_path(output_path)).resolve()
    from services.config_service import load_config
    game_path = load_config().get('gamePakPath')
    if output == source_path or (game_path and output == Path(game_path).resolve()):
        raise ValueError('La salida no puede reemplazar el mod original ni el PAK del juego.')
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    with tempfile.TemporaryDirectory(prefix='aurora-export-') as temporary:
        root = Path(temporary) / 'content'
        if extracted_source is None:
            extract_pak(source_path, root, is_cancelled_callback)
        else:
            base = Path(extracted_source).resolve()
            for file in base.rglob('*'):
                raise_if_cancelled(is_cancelled_callback)
                if file.is_file():
                    if file.is_symlink() or not file.resolve().is_relative_to(base):
                        raise ValueError('El origen contiene enlaces externos.')
                    destination = root / file.relative_to(base)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, destination)
        stage(1, 'reading')
        mesh = find_current_mod_mesh(root, source_mesh)
        mesh_path = Path(mesh['mesh_file_path'])
        source_character = next((p for p in mesh_path.relative_to(root).parts if re.fullmatch(r'Ch\d{3}', p)), None)
        if source_character != target.split('/')[0] and not allow_cross_character:
            raise ValueError('Confirma el intercambio entre personajes antes de exportar.')
        stage(2, 'converting')
        run_hidden_command([uejsonPath, '-e', str(mesh_path)], is_cancelled_callback)
        json_path = mesh_path.with_suffix('.json')
        if not json_path.exists():
            raise RuntimeError('UEJSON no creó el documento de la malla.')
        patch_mesh_json(json_path, mesh_path.name, target)
        stage(3, 'rebuilding')
        run_hidden_command([uejsonPath, '-i', str(json_path)], is_cancelled_callback)
        move_rebuilt_mesh_files(str(mesh_path.parent), mesh_path.name, target, root)
        json_path.unlink(missing_ok=True)
        stage(4, 'packing')
        result = create_final_pak(str(output), is_cancelled_callback, root, overwrite)
        stage(5, 'done')
        return result
