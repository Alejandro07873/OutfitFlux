import json
import os
from services.json_store import write_json
from typing import Iterable

from util import (
    APP_VERSION,
    CACHE_DIR,
    CACHE_META_FILE,
    CHARACTER_DIR,
    CATALOG_FILE,
    SKIN_ID_MAP_FILE,
    ensure_dir,
)


CACHE_SCHEMA_VERSION = 2


def get_cache_metadata():
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "app_version": APP_VERSION,
        "game_path": "",
        "aes_key": "",
        "catalog_mtime": 0.0,
        "skin_id_map_mtime": 0.0,
    }


def load_cache_metadata():
    ensure_dir(CACHE_DIR)

    if not os.path.exists(CACHE_META_FILE):
        return get_cache_metadata()

    try:
        with open(CACHE_META_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return get_cache_metadata()

    if not isinstance(data, dict):
        return get_cache_metadata()

    meta = get_cache_metadata()
    meta.update(data)
    return meta


def save_cache_metadata(data: dict):
    ensure_dir(CACHE_DIR)

    meta = get_cache_metadata()
    if isinstance(data, dict):
        meta.update(data)

    write_json(CACHE_META_FILE, meta)

    return meta


def safe_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def build_cache_metadata(game_path: str, aes_key: str):
    try:
        stat = os.stat(game_path)
        fingerprint = [stat.st_size, stat.st_mtime_ns]
    except (OSError, TypeError):
        fingerprint = None
    return {
        "game_fingerprint": fingerprint,
        "schema_version": CACHE_SCHEMA_VERSION,
        "app_version": APP_VERSION,
        "game_path": str(game_path or ""),
        "aes_key": str(aes_key or ""),
        "catalog_mtime": safe_mtime(CATALOG_FILE),
        "skin_id_map_mtime": safe_mtime(SKIN_ID_MAP_FILE),
    }


def is_cache_metadata_compatible(game_path: str, aes_key: str) -> bool:
    current = build_cache_metadata(game_path, aes_key)
    saved = load_cache_metadata()

    keys = [
        "game_fingerprint",
        "schema_version",
        "app_version",
        "game_path",
        "aes_key",
        "catalog_mtime",
        "skin_id_map_mtime",
    ]

    return all(saved.get(k) == current.get(k) for k in keys)


def character_dirs() -> list[str]:
    if not os.path.isdir(CHARACTER_DIR):
        return []

    result = []
    for name in os.listdir(CHARACTER_DIR):
        full = os.path.join(CHARACTER_DIR, name)
        if os.path.isdir(full) and name.startswith("Ch"):
            result.append(full)
    return result


def has_required_character_outputs(min_characters: int = 3) -> bool:
    dirs = character_dirs()
    if len(dirs) < min_characters:
        return False

    json_count = 0
    png_count = 0

    for character_dir in dirs:
        character = os.path.basename(character_dir)

        pa_json = os.path.join(character_dir, f"PA_{character}.json")
        if os.path.exists(pa_json):
            json_count += 1

        gui_dir = os.path.join(character_dir, "GUI", "Costume", "L")
        if os.path.isdir(gui_dir):
            if any(name.lower().endswith(".png") for name in os.listdir(gui_dir)):
                png_count += 1

    return json_count >= min_characters and png_count >= min_characters


def is_startup_cache_valid(game_path: str, aes_key: str) -> bool:
    if not is_cache_metadata_compatible(game_path, aes_key):
        return False

    if not has_required_character_outputs():
        return False

    return True


def update_startup_cache(game_path: str, aes_key: str):
    meta = build_cache_metadata(game_path, aes_key)
    save_cache_metadata(meta)
    return meta


def invalidate_startup_cache():
    if os.path.exists(CACHE_META_FILE):
        try:
            os.remove(CACHE_META_FILE)
        except OSError:
            pass
