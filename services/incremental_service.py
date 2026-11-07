"""Incremental catalog resources: targeted staging, integrity cache and atomic conversion."""
import hashlib
import json
import re
import os
import tempfile
import shutil
import threading
from pathlib import Path
from services.process_service import run_hidden_command, raise_if_cancelled
from services.json_store import write_json
from util import ASSETS_DIR, CONFIG_DIR, repakPath, uejsonPath

_LOCK = threading.Lock()
SCHEMA = 3


def digest(path):
    if not path.is_file():return None
    result=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def catalog_entry(entry):
    return bool(re.fullmatch(r'HerovsGame/Content/Character/Ch(?!000)[0-3]\d\d/(?:PA_Ch\d{3}|GUI/Costume/L/[^/]*0_[^/]*L)\.(?:uasset|uexp|ubulk)',entry))


def valid_output(path):
    try:
        if path.suffix=='.json':return isinstance(json.loads(path.read_text(encoding='utf-8-sig')),(dict,list))
        from PySide6.QtGui import QImage
        return not QImage(str(path)).isNull()
    except (ValueError,OSError):return False


def unpack_entries(aes,game,entries,destination,cancel,progress,whole_catalog=False):
    if whole_catalog and entries:
        progress(0,0,'Leyendo solo recursos del catálogo / Reading only catalog resources')
        run_hidden_command([repakPath,'--aes-key',aes,'unpack','-f','-o',str(destination),
                            '-i','**/Ch[0-3][0-9][0-9]/PA_Ch[0-9][0-9][0-9].*',
                            '-i','**/Ch[0-3][0-9][0-9]/GUI/Costume/L/*0_*L.*',game],cancel)
        for entry in entries:
            if not (destination/entry).is_file():raise RuntimeError('Incomplete extraction: '+entry)
        return
    for offset in range(0,len(entries),100):
        raise_if_cancelled(cancel)
        args=[repakPath,'--aes-key',aes,'unpack','-f','-o',str(destination)]
        for entry in entries[offset:offset+100]:args+=['-i',entry]
        run_hidden_command(args+[game],cancel)
        progress(min(40,int(40*(offset+100)/max(1,len(entries)))),100,'Leyendo recursos del catálogo / Reading catalog resources')
    for entry in entries:
        if not (destination/entry).is_file():raise RuntimeError('Incomplete extraction: '+entry)


def refresh_assets(aes,game,cancel=None,progress=None):
    if not _LOCK.acquire(blocking=False):raise RuntimeError('Ya hay una actualización en curso / An update is already running')
    try:return _refresh(aes,game,cancel,progress or (lambda *args:None))
    finally:_LOCK.release()


def _refresh(aes,game,cancel,progress):
    from services.game_service import _process_single_thumbnail
    manifest=Path(CONFIG_DIR)/'incremental-assets.json'
    try:
        old=json.loads(manifest.read_text(encoding='utf-8-sig'))
        if not isinstance(old,dict):old={}
    except (OSError,ValueError):old={}
    stat=Path(game).stat()
    fingerprint=[str(Path(game).resolve()),stat.st_size,stat.st_mtime_ns,hashlib.sha256(aes.encode()).hexdigest()]
    same=old.get('schema')==SCHEMA and old.get('game')==fingerprint
    progress(0,100,'Verificando caché / Checking cache')
    if same:
        entries=old.get('entries',[])
    else:
        result=run_hidden_command([repakPath,'--aes-key',aes,'list',game],cancel,output_limit=128*1024*1024)
        entries=sorted({e.strip().replace('\\','/').removeprefix('../../../') for e in result['stdout'].splitlines() if catalog_entry(e.strip().replace('\\','/').removeprefix('../../../'))})
    if not entries or not all(catalog_entry(e) for e in entries):raise ValueError('No valid catalog resources found')
    current={}
    for entry in entries:
        raise_if_cancelled(cancel);current[entry]=digest(Path(ASSETS_DIR)/entry)
    pending=[e for e in entries if not same or not current[e] or current[e]!=old.get('files',{}).get(e)]
    changed=set();hashes=dict(current)
    # When the PAK changes, read only PA and large costume thumbnails, never every game asset.
    with tempfile.TemporaryDirectory(prefix='outfitflux-catalog-') as temp:
        staging=Path(temp)
        unpack_entries(aes,game,pending,staging,cancel,progress,whole_catalog=not same)
        for entry in pending:
            raise_if_cancelled(cancel)
            source=staging/entry;new_hash=digest(source);hashes[entry]=new_hash
            if new_hash!=current[entry]:
                target=Path(ASSETS_DIR)/entry;target.parent.mkdir(parents=True,exist_ok=True)
                temporary=target.with_name(target.name+'.updating')
                try:shutil.copy2(source,temporary);os.replace(temporary,target)
                finally:temporary.unlink(missing_ok=True)
                changed.add(entry)
    derived={}
    inputs={}
    converted=0;warnings=[]
    assets=[e for e in entries if e.endswith('.uasset')]
    cached_derived=old.get('derived',{})
    cached_inputs=old.get('inputs',{})
    for index,entry in enumerate(assets):
        raise_if_cancelled(cancel)
        path=Path(ASSETS_DIR)/entry
        output=path.with_suffix('.json' if path.name.startswith('PA_') else '.png')
        key=output.relative_to(ASSETS_DIR).as_posix()
        signature=[hashes.get(str(Path(entry).with_suffix(ext)).replace('\\','/')) for ext in ('.uasset','.uexp','.ubulk')]
        intact=digest(output)
        source_changed=any(str(Path(entry).with_suffix(ext)).replace('\\','/') in changed for ext in ('.uasset','.uexp','.ubulk'))
        reuse=bool(intact and ((cached_inputs.get(key)==signature and cached_derived.get(key)==intact) or (key not in cached_inputs and not source_changed and valid_output(output))))
        if not reuse:
            try:
                with tempfile.TemporaryDirectory(prefix='outfitflux-convert-') as temp:
                    folder=Path(temp);staged=folder/output.name
                    if path.name.startswith('PA_'):
                        for ext in ('.uasset','.uexp','.ubulk'):
                            companion=path.with_suffix(ext)
                            if companion.is_file():shutil.copy2(companion,folder/companion.name)
                        run_hidden_command([uejsonPath,'-e',str(folder/path.name)],cancel)
                    else:
                        error=_process_single_thumbnail(str(path),str(folder),str(staged),str(staged.with_suffix('.tga')),cancel)
                        if error:raise RuntimeError(error)
                    if not valid_output(staged):raise ValueError('Invalid conversion: '+entry)
                    temporary=output.with_name(output.name+'.updating')
                    try:shutil.copy2(staged,temporary);os.replace(temporary,output)
                    finally:temporary.unlink(missing_ok=True)
                converted+=1;intact=digest(output)
            except Exception as exc:
                from services.process_service import ExportCancelled
                if isinstance(exc,ExportCancelled):raise
                warnings.append(str(exc));inputs[key]=signature;continue
        derived[key]=intact;inputs[key]=signature
        progress(40+int(60*(index+1)/max(1,len(assets))),100,'Preparando catálogo / Preparing catalog')
    raise_if_cancelled(cancel)
    write_json(manifest,dict(schema=SCHEMA,game=fingerprint,entries=entries,files=hashes,derived=derived,inputs=inputs))
    if not warnings:
        from services.cache_service import update_startup_cache
        update_startup_cache(game,aes)
    return dict(updated_files=len(changed),unchanged_files=len(entries)-len(changed),converted=converted,reused=len(derived)-converted,used_cache=same and not pending and not converted,warnings=warnings)
