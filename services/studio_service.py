"""Indexed library, persistent history, FModel inventory and batch orchestration."""
import json
import re
import uuid
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from services.catalog_service import load_catalog, normalize_catalog_entry
from services.skin_id_map_service import extract_costume_meshs_from_pa_json
from services.json_store import write_json
from services.process_service import raise_if_cancelled, ExportCancelled
from services.safe_export_service import export_mod_to_skin, ensure_unique_output_path
from services.filename_service import build_output_filename, sanitize_filename_component
from util import CHARACTER_DIR, CONFIG_DIR


def load_library():
    from services.config_service import load_config
    language = load_config().get('language', 'es')
    catalog = load_catalog()
    records = []
    warnings = []
    for folder in sorted(Path(CHARACTER_DIR).glob('Ch*')):
        images = {p.stem.split('_')[-2]: str(p) for p in (folder / 'GUI/Costume/L').glob('*.png')}
        pa = folder / f'PA_{folder.name}.json'
        if not pa.is_file():
            continue
        try:
            rows = extract_costume_meshs_from_pa_json(pa)
        except (OSError, ValueError, TypeError) as exc:
            warnings.append(f'{pa.name}: {exc}')
            continue
        entries = catalog.get(folder.name, {})
        if not isinstance(entries, dict):
            entries = {}
        for row in rows:
            try:
                sid = str(row[0]['Value'])
                asset = row[1]['Value']['AssetPath']['AssetName']
                path = asset.partition('Character/')[2].partition('.')[0]
                internal = path.rsplit('/', 1)[-1]
                if not path or not internal:
                    continue
                metadata = normalize_catalog_entry(entries.get(internal), internal, sid)
                name = (metadata['display_name_es'] if language == 'es' else metadata['display_name']) or internal
                record = dict(character=folder.name, internal=internal, id=sid, name=name,
                              description=metadata['description_es'] if language == 'es' else metadata['description'], image=images.get(sid, ''),
                              skin_path=path, display_name=name, internal_name=internal,
                              is_known=metadata['is_known'])
                record['search'] = ' '.join([name, metadata['display_name'], internal, sid, folder.name, *metadata['aliases']]).casefold()
                records.append(record)
            except (KeyError, TypeError, IndexError) as exc:
                warnings.append(f'{pa.name}: entrada inválida ({exc})')
    return records, warnings


def save_history(payload):
    data = dict(payload, timestamp=datetime.now(timezone.utc).isoformat(), id=uuid.uuid4().hex)
    write_json(Path(CONFIG_DIR) / 'history' / (data['id'] + '.json'), data)
    return data


def read_history():
    history = []
    for path in (Path(CONFIG_DIR) / 'history').glob('*.json'):
        try:
            entry = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(entry, dict):
                history.append(entry)
        except (OSError, ValueError):
            continue
    return sorted(history, key=lambda item: item.get('timestamp', ''), reverse=True)


def export_queue(mod_file, source_mesh, records, directory, grouped=True, cross=False,
                 cancel=None, progress=None):
    from services.pak_service import extract_pak
    with tempfile.TemporaryDirectory(prefix='aurora-batch-source-') as temporary:
        if progress:
            progress(0, 0, 'Extrayendo el origen una sola vez…')
        extract_pak(mod_file, temporary, cancel)
        return _export_queue(mod_file, source_mesh, records, directory, grouped, cross, cancel, progress, temporary)


def _export_queue(mod_file, source_mesh, records, directory, grouped, cross, cancel, progress, extracted_source):
    from services.catalog_service import costume_filename_names
    known_names = costume_filename_names()
    completed, failed, history_errors = [], [], []
    cancelled = False
    for index, record in enumerate(records):
        if cancel and cancel():
            cancelled = True
            break
        if progress:
            progress(index, len(records), f'{record["character"]} · {record["name"]}')
        output = None
        def target_progress(step, state):
            if progress:
                progress(index, len(records), 'outfitflux-target:' + json.dumps(
                    dict(index=index, step=step, state=state)))
        try:
            folder = Path(directory)
            if grouped:
                folder /= sanitize_filename_component(record['character'])
            # The legacy helper returns a full path when given a full source path.
            # Only its basename belongs under the destination selected by the user.
            name = Path(build_output_filename(mod_file, record['name'],
                        current_skin_internal_name=Path(source_mesh).stem if source_mesh else '',
                        known_skin_names=known_names)).name
            output = ensure_unique_output_path(str(folder / name))
            result = export_mod_to_skin(mod_file, record['skin_path'], output, cancel,
                                        source_mesh=source_mesh, allow_cross_character=cross, extracted_source=extracted_source,
                                        progress_callback=target_progress)
            target_progress(5, 'done')
            row = {'source': mod_file, 'target': record['skin_path'], 'output': result, 'status': 'completed'}
            completed.append(row)
        except ExportCancelled:
            target_progress(0, 'cancelled')
            cancelled = True
            break
        except Exception as exc:
            target_progress(0, 'failed')
            row = {'source': mod_file, 'target': record['skin_path'], 'output': output, 'status': 'failed', 'error': str(exc)}
            failed.append(row)
        try:
            save_history(row)
        except OSError as exc:
            history_errors.append(str(exc))
    if progress:
        progress(len(completed) + len(failed), len(records), 'Finalizado' if not cancelled else 'Cancelado')
    return dict(completed=completed, failed=failed, cancelled=cancelled, history_errors=history_errors)


def index_fmodel(root, cancel=None, progress=None):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Selecciona la carpeta Character de FModel.')
    counts = Counter()
    characters = {}
    meshes = []
    for index, path in enumerate(root.rglob('*')):
        raise_if_cancelled(cancel)
        if not path.is_file():
            continue
        counts[path.suffix.lower()] += 1
        relative = path.relative_to(root)
        if relative.parts:
            characters[relative.parts[0]] = characters.get(relative.parts[0], 0) + 1
        if path.suffix.lower() == '.uasset' and path.parent.name == 'Mesh' and path.name.startswith('SK_'):
            if not re.search(r'_(PhysicsAsset|Skeleton|Cloth|Clothing|Physics)(?:_\d+)?$', path.stem, re.I):
                meshes.append({'path': relative.as_posix(), 'uexp': path.with_suffix('.uexp').is_file(), 'ubulk': path.with_suffix('.ubulk').is_file()})
        if progress and index % 1500 == 0:
            progress(0, 0, f'{sum(counts.values())} archivos inspeccionados')
    result = dict(root=str(root), files=sum(counts.values()), extensions=dict(counts), characters=characters,
                  meshes=meshes, generated_at=datetime.now(timezone.utc).isoformat())
    raise_if_cancelled(cancel)
    write_json(Path(CONFIG_DIR) / 'fmodel_index.json', result)
    return result


def inspect_asset_json(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    references = set()
    def walk(value):
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and value.startswith(('/Game/', '/Engine/')):
            references.add(value)
    walk(data)
    return {'path': str(path), 'references': sorted(references),
            'skeleton_physics': sorted(r for r in references if any(s in r.casefold() for s in ('skeleton', 'physics', 'cloth'))),
            'materials': sorted(r for r in references if '/mat/' in r.casefold() or 'material' in r.casefold()),
            'note': 'Référencias declaradas; no verifica compatibilidad de huesos ni resultado en juego.'}
