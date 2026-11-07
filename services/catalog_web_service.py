import re
import urllib.request
import urllib.error
import hashlib
import json
from pathlib import Path
from util import CONFIG_DIR
from services.json_store import write_json
from datetime import datetime, timezone
from html import unescape

from services.catalog_service import load_catalog, save_catalog, upsert_catalog_entry


BASE_LANG_URLS = {
    "en": "https://ultrarumble.com",
    "es": "https://es.ultrarumble.com",
}


def fetch_text(url, timeout=30):
    folder = Path(CONFIG_DIR) / 'web-cache'
    key = hashlib.sha256(url.encode()).hexdigest()
    body_path = folder / (key + '.html')
    meta_path = folder / (key + '.json')
    try:
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        cached = body_path.read_bytes()
        if hashlib.sha256(cached).hexdigest() != meta.get('sha256'):
            meta, cached = {}, None
    except (OSError, ValueError):
        meta, cached = {}, None
    language = 'es' if '://es.' in url else 'en'
    headers = {'User-Agent': 'OutfitFlux Catalog Updater', 'Accept-Language': language,
               'Cookie': 'language=' + language + ';'}
    if cached is not None:
        if meta.get('etag'): headers['If-None-Match'] = meta['etag']
        if meta.get('modified'): headers['If-Modified-Since'] = meta['modified']
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
            body = response.read(16*1024*1024+1)
            if len(body)>16*1024*1024: raise ValueError('Catalog response too large')
            etag, modified = response.headers.get('ETag'), response.headers.get('Last-Modified')
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and cached is not None:
            return cached.decode('utf-8', errors='replace')
        raise
    folder.mkdir(parents=True, exist_ok=True)
    temporary = body_path.with_suffix('.tmp')
    temporary.write_bytes(body)
    temporary.replace(body_path)
    write_json(meta_path, {'etag': etag, 'modified': modified, 'sha256': hashlib.sha256(body).hexdigest()})
    return body.decode('utf-8', errors='replace')


def clean_text(value):
    value = unescape(value or "")
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = " ".join(value.split())
    return value.strip()


def extract_costume_entries_from_list(list_html, base_url):
    from html.parser import HTMLParser
    class CostumeParser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.current = None
            self.results = []
            self.seen = set()
        def handle_starttag(self, tag, attributes):
            attrs = dict(attributes)
            if tag == 'a':
                match = re.fullmatch(r'/costume/(\d+)/?', attrs.get('href') or '')
                if match:
                    self.current = dict(skin_id=match[1], display_name=attrs.get('title') or '', description='', character_code='', text=[])
            elif self.current and tag == 'img':
                match = re.search(r'/Character/(Ch\d{3})/GUI/Costume/', attrs.get('src') or '')
                if match:
                    self.current['character_code'] = match[1]
                    self.current['description'] = attrs.get('title') or ''
            elif self.current and tag == 'div' and 'name' in (attrs.get('class') or '').split():
                self.current['display_name'] = attrs.get('title') or self.current['display_name']
        def handle_data(self, data):
            if self.current:
                self.current['text'].append(data)
        def handle_endtag(self, tag):
            if tag == 'a' and self.current:
                item = self.current
                self.current = None
                key = (item['character_code'], item['skin_id'])
                if item['character_code'] and key not in self.seen:
                    self.seen.add(key)
                    item['display_name'] = clean_text(item['display_name'] or ' '.join(item['text'])) or item['skin_id']
                    item['description'] = clean_text(item['description'])
                    item['source_url'] = base_url + '/costume/' + item['skin_id']
                    del item['text']
                    self.results.append(item)
    parser = CostumeParser()
    parser.feed(list_html)
    parser.close()
    return parser.results


def fetch_web_catalog(language="en"):
    if language not in BASE_LANG_URLS:
        raise ValueError(f"Unsupported language: {language}")

    base_url = BASE_LANG_URLS[language]
    list_url = f"{base_url}/costumes"

    list_html = fetch_text(list_url)
    return extract_costume_entries_from_list(list_html, base_url)


def remove_legacy_web_entries(catalog):
    changed = False

    for character, character_entries in list(catalog.items()):
        if character == "_meta":
            continue
        if not isinstance(character_entries, dict):
            continue

        keys_to_delete = [key for key in character_entries if str(key).startswith("WEB_")]
        for key in keys_to_delete:
            del character_entries[key]
            changed = True

    return changed


def merge_web_catalog_into_local(language="en", internal_name_map=None):
    if internal_name_map is None:
        internal_name_map = {}

    catalog = load_catalog()
    web_entries = fetch_web_catalog(language=language)
    if not web_entries:
        raise RuntimeError('El catálogo descargado está vacío; se conserva el catálogo local.')

    # limpiar basura vieja tipo WEB_4, WEB_2402100, etc
    # Keep unresolved legacy entries; deleting them here loses user metadata.

    merged_count = 0
    changed_count = 0
    added = []
    unresolved_count = 0

    for entry in web_entries:
        character = entry.get("character_code")
        skin_id = entry.get("skin_id")
        source_url = entry.get("source_url", "")
        if skin_id:
            source_url = BASE_LANG_URLS['en'] + '/costume/' + str(skin_id)
        description = entry.get("description", "")
        web_display_name = entry.get("display_name", "").strip()

        if not character or not skin_id:
            continue

        mapped_internal_name = internal_name_map.get(character, {}).get(skin_id)
        if not mapped_internal_name:
            unresolved_count += 1
            continue

        current_entry = catalog.get(character, {}).get(mapped_internal_name, {})
        if not isinstance(current_entry, dict):
            current_entry = {}

        current_display_name = str(current_entry.get("display_name", "")).strip()
        current_display_name_es = str(current_entry.get("display_name_es", "")).strip()
        current_description = str(current_entry.get("description", "")).strip()
        current_description_es = str(current_entry.get("description_es", "")).strip()
        current_aliases = current_entry.get("aliases", [])

        # --- AQUÍ ESTÁ LA CORRECCIÓN DE LA LÓGICA DE TRADUCCIÓN ---
        if language == "en":
            display_name = web_display_name or current_display_name or mapped_internal_name
            display_name_es = current_display_name_es or display_name
            final_desc = description or current_description
            final_desc_es = current_description_es or final_desc
        else:
            display_name = current_display_name or mapped_internal_name
            display_name_es = web_display_name or current_display_name_es or display_name
            final_desc = current_description
            final_desc_es = description or current_description_es or final_desc

        catalog = upsert_catalog_entry(
            catalog=catalog,
            character=character,
            skin_id=skin_id,
            internal_name=mapped_internal_name,
            display_name=display_name,
            display_name_es=display_name_es,
            description=final_desc,
            description_es=final_desc_es,
            source_url=source_url,
            aliases=current_aliases,
        )

        updated = {**current_entry, **catalog[character][mapped_internal_name]}
        catalog[character][mapped_internal_name] = updated
        if updated != current_entry:
            changed_count += 1
            if not current_entry:
                added.append({'character': character, 'name': web_display_name, 'id': skin_id})
        merged_count += 1

    catalog["_meta"]["version"] = 3
    catalog["_meta"]["source"] = "ultrarumble.com-id-match"
    catalog["_meta"]["language"] = language
    catalog["_meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()

    if changed_count:
        save_catalog(catalog)

    return {
        "merged_count": merged_count,
        "changed_count": changed_count,
        "added": added,
        "unchanged_count": merged_count - changed_count,
        "unresolved_count": unresolved_count,
        "language": language,
        "entries_downloaded": len(web_entries),
    }
