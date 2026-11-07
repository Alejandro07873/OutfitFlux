import json
import os
import shutil
import time
from services.json_store import write_json

from util import (
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_AES_KEY,
    DEFAULT_GAME_PAK_PATH,
    ensure_dir,
)


def get_default_config():
    return {
        "aesKey": DEFAULT_AES_KEY,
        "gamePakPath": DEFAULT_GAME_PAK_PATH,
    }


def ensure_config_exists():
    ensure_dir(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE):
        save_config(get_default_config())
    return CONFIG_FILE


def load_config():
    ensure_config_exists()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        if not isinstance(config, dict):
            raise ValueError("La configuración debe ser un objeto JSON")
    except (ValueError, OSError):
        if os.path.isfile(CONFIG_FILE):
            shutil.copy2(CONFIG_FILE, CONFIG_FILE + f".invalid-{time.time_ns()}.bak")
        config = get_default_config()
        save_config(config)

    default_config = get_default_config()
    for key, value in default_config.items():
        config.setdefault(key, value)

    return config


def save_config(config):
    ensure_dir(CONFIG_DIR)

    normalized = get_default_config()
    normalized.update({k: v for k, v in config.items() if v is not None})

    write_json(CONFIG_FILE, normalized)

    return normalized
