import json
import os
from services.json_store import write_json

from util import CATALOG_FILE, CONFIG_DIR, ensure_dir
from services.config_service import load_config

def get_default_catalog():
    return {
        "_meta": {
            "version": 2,
            "source": "local",
            "last_updated": "",
            "language": "en",
        }
    }


def ensure_catalog_exists():
    ensure_dir(CONFIG_DIR)

    if not os.path.exists(CATALOG_FILE):
        save_catalog(get_default_catalog())

    return CATALOG_FILE


def load_catalog():
    ensure_catalog_exists()

    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = get_default_catalog()
        save_catalog(data)

    if not isinstance(data, dict):
        data = get_default_catalog()
        save_catalog(data)

    data.setdefault("_meta", {})
    data["_meta"].setdefault("version", 2)
    data["_meta"].setdefault("source", "local")
    data["_meta"].setdefault("last_updated", "")
    data["_meta"].setdefault("language", "en")

    return data


def save_catalog(catalog):
    ensure_dir(CONFIG_DIR)

    if not isinstance(catalog, dict):
        catalog = get_default_catalog()

    catalog.setdefault("_meta", {})
    catalog["_meta"].setdefault("version", 2)
    catalog["_meta"].setdefault("source", "local")
    catalog["_meta"].setdefault("last_updated", "")
    catalog["_meta"].setdefault("language", "en")

    write_json(CATALOG_FILE, catalog)

    return catalog


def normalize_catalog_entry(entry, internal_name="", skin_id=""):
    if isinstance(entry, str):
        return {
            "display_name": entry.strip() or internal_name,
            "display_name_es": entry.strip() or internal_name,
            "aliases": [],
            "internal_name": internal_name,
            "skin_id": skin_id,
            "description": "",
            "description_es": "",
            "source_url": "",
            "is_known": True,
        }

    if isinstance(entry, dict):
        display_name = str(entry.get("display_name", "")).strip()
        display_name_es = str(entry.get("display_name_es", "")).strip()
        description = str(entry.get("description", "")).strip()
        description_es = str(entry.get("description_es", "")).strip()
        aliases = entry.get("aliases", [])

        if not isinstance(aliases, list):
            aliases = []

        return {
            "display_name": display_name or internal_name,
            "display_name_es": display_name_es or display_name or internal_name,
            "aliases": [str(x).strip() for x in aliases if str(x).strip()],
            "internal_name": internal_name or str(entry.get("internal_name", "")).strip(),
            "skin_id": str(entry.get("skin_id", skin_id)).strip(),
            "description": description,
            "description_es": description_es or description,
            "source_url": str(entry.get("source_url", "")).strip(),
            "is_known": bool(display_name or display_name_es),
        }

    return {
        "display_name": internal_name,
        "display_name_es": internal_name,
        "aliases": [],
        "internal_name": internal_name,
        "skin_id": skin_id,
        "description": "",
        "description_es": "",
        "source_url": "",
        "is_known": False,
    }


def get_character_catalog(character):
    catalog = load_catalog()
    character_data = catalog.get(character, {})

    if not isinstance(character_data, dict):
        return {}


def costume_filename_names():
    """Known names in both languages, independent of the current UI language."""
    names = set()
    for character, entries in load_catalog().items():
        if not character.startswith('Ch') or not isinstance(entries, dict):
            continue
        for internal, entry in entries.items():
            data = normalize_catalog_entry(entry, internal)
            names.update([internal, data['display_name'], data['display_name_es'], *data['aliases']])
    names.discard('')
    return names

    return character_data


def get_default_friendly_name(internal_name):
    if str(internal_name).endswith("_Default_00"):
        return "Default"
    return None


def get_skin_display_data(character, internal_name, skin_id=""):
    # Cargamos el idioma aquí para que la función sepa qué descripción devolver
    lang = load_config().get("language", "en")
    
    internal_name = str(internal_name or "").strip()
    skin_id = str(skin_id or "").strip()

    character_catalog = get_character_catalog(character)

    # Buscar entry original
    entry = None
    if internal_name in character_catalog:
        entry = character_catalog.get(internal_name)
    else:
        # Buscar por skin_id si no se encuentra por nombre
        for _internal_name, candidate in character_catalog.items():
            if skin_id and isinstance(candidate, dict) and str(candidate.get("skin_id", "")).strip() == skin_id:
                entry = candidate
                internal_name = _internal_name
                break

    if entry is not None:
        data = normalize_catalog_entry(entry, internal_name=internal_name, skin_id=skin_id)
        return {
            "display_name": data["display_name_es"] if lang == "es" else data["display_name"],
            "display_name_es": data["display_name_es"],
            "aliases": data["aliases"],
            "internal_name": data["internal_name"],
            "skin_id": data["skin_id"],
            # LA MAGIA: Intercambia la descripción según el idioma elegido
            "description": data["description_es"] if lang == "es" else data["description"],
            "source_url": data["source_url"],
            "is_known": data["is_known"],
        }

    # Fallback si no está en el catálogo
    inferred_name = get_default_friendly_name(internal_name)
    return {
        "display_name": inferred_name or internal_name,
        "display_name_es": inferred_name or internal_name,
        "aliases": [],
        "internal_name": internal_name,
        "skin_id": skin_id,
        "description": "",
        "source_url": "",
        "is_known": False,
    }


def upsert_catalog_entry(
    catalog,
    character,
    skin_id,
    internal_name,
    display_name="",
    display_name_es="",
    description="",
    description_es="",
    source_url="",
    aliases=None,
):
    if aliases is None:
        aliases = []

    catalog.setdefault(character, {})

    catalog[character][internal_name] = {
        "display_name": str(display_name or internal_name).strip(),
        "display_name_es": str(display_name_es or display_name or internal_name).strip(),
        "aliases": [str(x).strip() for x in aliases if str(x).strip()],
        "internal_name": str(internal_name).strip(),
        "skin_id": str(skin_id).strip(),
        "description": str(description or "").strip(),
        "description_es": str(description_es or description or "").strip(),
        "source_url": str(source_url or "").strip(),
    }

    return catalog

def is_skin_known(character, internal_name, skin_id=""):
    data = get_skin_display_data(character, internal_name, skin_id)
    return bool(data.get("is_known", False))


def get_unknown_skin_count(character, skin_records):
    count = 0
    for item in skin_records:
        if isinstance(item, dict):
            internal_name = item.get("internal_name", "")
            skin_id = item.get("skin_id", "")
        else:
            internal_name = str(item or "")
            skin_id = ""

        data = get_skin_display_data(character, internal_name, skin_id)
        if not data.get("is_known", False):
            count += 1
    return count
