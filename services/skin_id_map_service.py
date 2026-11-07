import json
import os
from services.json_store import write_json

from util import CHARACTER_DIR, CONFIG_DIR, SKIN_ID_MAP_FILE, ensure_dir
from services.catalog_service import load_catalog, save_catalog


def get_default_skin_id_map():
    return {}


def ensure_skin_id_map_exists():
    ensure_dir(CONFIG_DIR)

    if not os.path.exists(SKIN_ID_MAP_FILE):
        save_skin_id_map(get_default_skin_id_map())

    return SKIN_ID_MAP_FILE


def load_skin_id_map():
    ensure_skin_id_map_exists()

    try:
        with open(SKIN_ID_MAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = get_default_skin_id_map()
        save_skin_id_map(data)

    if not isinstance(data, dict):
        data = get_default_skin_id_map()
        save_skin_id_map(data)

    return data


def save_skin_id_map(data):
    ensure_dir(CONFIG_DIR)

    if not isinstance(data, dict):
        data = get_default_skin_id_map()

    write_json(SKIN_ID_MAP_FILE, data)

    return data


def extract_costume_meshs_from_pa_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    exports = data.get("Exports", [])
    if not exports:
        return []

    data_block = exports[0].get("Data", [])
    for value in data_block:
        if value.get("Name") == "_costumeMeshs":
            return value.get("Value", [])

    return []


def parse_skin_id_map_for_character(character_code, pa_json_path):
    skins = extract_costume_meshs_from_pa_json(pa_json_path)
    character_map = {}

    for skin in skins:
        try:
            skin_id = str(skin[0]["Value"]).strip()
            asset_name = str(skin[1]["Value"]["AssetPath"]["AssetName"]).strip()
            internal_name = asset_name.partition("Mesh/")[2].partition(".")[0].strip()

            if skin_id and internal_name:
                character_map[skin_id] = internal_name
        except Exception:
            continue

    return character_map


def build_skin_id_map_from_assets():
    if not os.path.isdir(CHARACTER_DIR):
        raise RuntimeError(
            "Character assets were not found.\n\n"
            "Run the app first so it can extract PA_*.json files."
        )

    result = {}
    found_any = False

    for entry in sorted(os.listdir(CHARACTER_DIR)):
        character_dir = os.path.join(CHARACTER_DIR, entry)
        if not os.path.isdir(character_dir):
            continue

        if not entry.startswith("Ch"):
            continue

        pa_json_path = os.path.join(character_dir, f"PA_{entry}.json")
        if not os.path.exists(pa_json_path):
            continue

        character_map = parse_skin_id_map_for_character(entry, pa_json_path)
        if character_map:
            result[entry] = character_map
            found_any = True

    if not found_any:
        raise RuntimeError(
            "No valid PA_*.json files were found to build skin_id_map.json."
        )

    return result


def rebuild_skin_id_map_file():
    data = build_skin_id_map_from_assets()
    save_skin_id_map(data)

    total_entries = sum(len(v) for v in data.values())

    return {
        "characters_found": len(data),
        "mapped_entries": total_entries,
        "path": SKIN_ID_MAP_FILE,
    }


def cleanup_legacy_web_keys_in_catalog():
    """
    Si ya existe un mapeo real skin_id -> internal_name,
    mueve entradas antiguas WEB_<id> al internal_name real.
    """
    mapping = load_skin_id_map()
    catalog = load_catalog()

    changed = False

    for character, skin_map in mapping.items():
        character_catalog = catalog.get(character)
        if not isinstance(character_catalog, dict):
            continue

        for skin_id, internal_name in skin_map.items():
            legacy_key = f"WEB_{skin_id}"
            if legacy_key not in character_catalog:
                continue

            legacy_entry = character_catalog.get(legacy_key, {})
            real_entry = character_catalog.get(internal_name, {})

            if not isinstance(legacy_entry, dict):
                legacy_entry = {}
            if not isinstance(real_entry, dict):
                real_entry = {}

            merged = {
                "display_name": real_entry.get("display_name") or legacy_entry.get("display_name") or internal_name,
                "display_name_es": real_entry.get("display_name_es") or legacy_entry.get("display_name_es") or real_entry.get("display_name") or legacy_entry.get("display_name") or internal_name,
                "aliases": real_entry.get("aliases") or legacy_entry.get("aliases") or [],
                "internal_name": internal_name,
                "skin_id": skin_id,
                "description": real_entry.get("description") or legacy_entry.get("description") or "",
                "source_url": real_entry.get("source_url") or legacy_entry.get("source_url") or "",
            }

            character_catalog[internal_name] = merged
            del character_catalog[legacy_key]
            changed = True

    if changed:
        save_catalog(catalog)

    return changed
