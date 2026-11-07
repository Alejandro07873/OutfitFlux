import os
import sys
import shutil
import subprocess

APP_NAME = "OutfitFlux"
APP_VERSION = "1.1.5"

DEFAULT_AES_KEY = "0x332F41B1130F125444A35F420EC6D05EA3E27A972A36DAD90C83FC6958D941C7"
DEFAULT_GAME_PAK_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\My Hero Ultra Rumble\HerovsGame\Content\Paks\HerovsGame-WindowsNoEditor.pak"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def is_frozen():
    return getattr(sys, "frozen", False)


def resource_root():
    try:
        return sys._MEIPASS
    except AttributeError:
        return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    return os.path.join(resource_root(), relative_path)


def workspace_root():
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


WORKSPACE_DIR = workspace_root()

ASSETS_DIR = os.path.join(WORKSPACE_DIR, "assets")
MOD_DIR = os.path.join(ASSETS_DIR, "mod")
CONFIG_DIR = os.path.join(ASSETS_DIR, "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CATALOG_FILE = os.path.join(CONFIG_DIR, "skin_catalog.json")
SKIN_ID_MAP_FILE = os.path.join(CONFIG_DIR, "skin_id_map.json")
CACHE_DIR = os.path.join(ASSETS_DIR, "cache")
CACHE_META_FILE = os.path.join(CACHE_DIR, "startup_cache.json")
TEMP_DIR = os.path.join(WORKSPACE_DIR, "temp")

CHARACTER_DIR = os.path.join(ASSETS_DIR, "HerovsGame", "Content", "Character")
ICON_PATH = resource_path("branding/outfitflux.ico")

# Dependencies
uejsonPath = resource_path(os.path.join("UEJSON", "UEJSON.exe"))
repakPath = resource_path(os.path.join("dependencies", "repak", "repak.exe"))
unrealPak = resource_path(os.path.join("dependencies", "unrealpak", "UnrealPak.exe"))
ffmpegPath = resource_path(os.path.join("dependencies", "ffmpeg", "bin", "ffmpeg.exe"))
ue4ddsPath = resource_path(os.path.join("dependencies", "ue4dds", "src", "main.py"))
ue4ddsPythonPath = resource_path(os.path.join("dependencies", "ue4dds", "python", "python.exe"))


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def safe_rmtree(path):
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
