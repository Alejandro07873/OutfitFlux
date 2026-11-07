"""GitHub Releases updater: stable versions, verified ZIP, side-by-side install."""
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import urllib.request
import urllib.error
import zipfile
from pathlib import Path, PurePosixPath
from services.process_service import raise_if_cancelled
from util import APP_VERSION, WORKSPACE_DIR

ASSET_NAME = 'OutfitFlux-windows-x64.zip'
MAX_PACKAGE = 2 * 1024**3
MAX_EXPANDED = 8 * 1024**3


def repository(value):
    value = value.strip().removeprefix('https://github.com/').removesuffix('/').removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*', value):
        raise ValueError('Usa usuario/repositorio / Use owner/repository')
    return value


def version(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value)
    if not match:
        raise ValueError('Versión inválida / Invalid version: ' + value)
    return tuple(map(int, match.groups()))


def request(url):
    return urllib.request.Request(url, headers={'User-Agent':'OutfitFlux/'+APP_VERSION, 'Accept':'application/vnd.github+json'})


def check_update(repo, cancel=None):
    repo = repository(repo)
    raise_if_cancelled(cancel)
    try:
        with urllib.request.urlopen(request('https://api.github.com/repos/'+repo+'/releases/latest'), timeout=25) as response:
            raw = response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:
            raise ValueError('Release metadata too large')
        data=json.loads(raw)
    except urllib.error.HTTPError as exc:
        if exc.code==404:
            raise ValueError('No hay una versión pública publicada / No public release found') from exc
        if exc.code in (403,429):
            raise ValueError('GitHub ha limitado las consultas. Inténtalo después / GitHub rate limit; try later') from exc
        raise
    raise_if_cancelled(cancel)
    latest=data.get('tag_name','')
    newer=version(latest)>version(APP_VERSION)
    if data.get('draft') or data.get('prerelease'):
        raise ValueError('Only stable public releases are supported')
    asset=next((a for a in data.get('assets',[]) if a.get('name')==ASSET_NAME),None)
    return dict(repo=repo,version=latest,newer=newer,notes=str(data.get('body') or ''),asset=asset)


def validated_entries(archive):
    seen=set();total=0
    entries=archive.infolist()
    if len(entries)>100000:raise ValueError('Too many package entries')
    for entry in entries:
        name=entry.filename
        parts=PurePosixPath(name).parts
        if not parts or '\\' in name or name.startswith('/') or any(p in ('..','.') or ':' in p or p.endswith((' ','.')) for p in parts):
            raise ValueError('Unsafe package path: '+name)
        if any(re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',p,re.I) for p in parts):
            raise ValueError('Reserved Windows path')
        if parts[0]!='OutfitFlux' or (len(parts)>1 and parts[1].casefold() in ('assets','temp','updates')):
            raise ValueError('Invalid package layout: '+name)
        if stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Package contains a symbolic link')
        key=name.casefold().rstrip('/')
        if key in seen:raise ValueError('Duplicate package entry')
        seen.add(key);total+=entry.file_size
        if total>MAX_EXPANDED:raise ValueError('Package expands beyond limit')
    if 'outfitflux/outfitflux.exe' not in seen:raise ValueError('OutfitFlux.exe missing')
    return entries


def install_update(release, cancel=None, progress=None, workspace=None):
    progress=progress or (lambda *args:None)
    repo=repository(release['repo']);tag=release['version'];version(tag)
    if version(tag)<=version(APP_VERSION):raise ValueError('Update is not newer')
    asset=release.get('asset') or {}
    url=asset.get('browser_download_url','')
    if asset.get('name')!=ASSET_NAME or not url.startswith('https://github.com/'+repo+'/releases/download/'):
        raise ValueError('Invalid release asset')
    checksum=asset.get('digest') or ''
    if not re.fullmatch('sha256:[0-9a-fA-F]{64}',checksum):
        raise ValueError('Falta la suma SHA256 de GitHub / GitHub SHA256 digest missing')
    size=int(asset.get('size',0))
    if size<=0 or size>MAX_PACKAGE:raise ValueError('Invalid package size')
    current=Path(workspace or WORKSPACE_DIR).resolve()
    destination=current.parent/('OutfitFlux-'+tag.lstrip('v'))
    if destination.exists():raise FileExistsError(str(destination))
    with tempfile.TemporaryDirectory(prefix='.outfitflux-update-',dir=current.parent) as temporary:
        stage=Path(temporary);package=stage/'release.zip';hasher=hashlib.sha256();count=0
        with urllib.request.urlopen(request(url),timeout=45) as response, package.open('wb') as out:
            while True:
                raise_if_cancelled(cancel)
                chunk=response.read(1024*1024)
                if not chunk:break
                count+=len(chunk)
                if count>size:raise ValueError('Downloaded package exceeds declared size')
                out.write(chunk);hasher.update(chunk)
                progress(int(count*70/size),100,'Descargando / Downloading')
        if count!=size or hasher.hexdigest()!=checksum[7:].lower():raise ValueError('SHA256 mismatch')
        with zipfile.ZipFile(package) as archive:
            entries=validated_entries(archive)
            for i,entry in enumerate(entries):
                raise_if_cancelled(cancel)
                target=stage/entry.filename
                if entry.is_dir():target.mkdir(parents=True,exist_ok=True)
                else:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with archive.open(entry) as source,target.open('wb') as out:
                        while chunk:=source.read(1024*1024):
                            raise_if_cancelled(cancel);out.write(chunk)
                progress(70+int(20*(i+1)/max(1,len(entries))),100,'Preparando / Preparing')
        app=stage/'OutfitFlux'
        with (app/'OutfitFlux.exe').open('rb') as exe:
            if exe.read(2)!=b'MZ':raise ValueError('Invalid Windows executable')
        if not (app/'_internal').is_dir():raise ValueError('Runtime missing')
        source_assets=current/'assets'
        if source_assets.is_dir():
            for path in source_assets.rglob('*'):
                raise_if_cancelled(cancel)
                if path.is_symlink():raise ValueError('User library contains symbolic links')
                if path.is_file():
                    target=app/'assets'/path.relative_to(source_assets)
                    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        raise_if_cancelled(cancel)
        os.rename(app,destination)
        progress(100,100,'Listo / Ready')
    return str(destination/'OutfitFlux.exe')
