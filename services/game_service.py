import os
import shutil
import subprocess
import concurrent.futures
from services.process_service import run_hidden_command, raise_if_cancelled, ExportCancelled
from util import (
    CHARACTER_DIR,
    ASSETS_DIR,
    uejsonPath,
    repakPath,
    ue4ddsPath,
    ffmpegPath,
    ue4ddsPythonPath,
    unrealPak,
    CREATE_NO_WINDOW,
    ensure_dir,
    safe_rmtree,
)
from services.cache_service import (
    is_startup_cache_valid,
    update_startup_cache,
)


def check_dotnet_runtime():
    try:
        proc = subprocess.Popen(
            ["dotnet", "--list-runtimes"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
        )
        stdout, _stderr = proc.communicate()

        for line in stdout.splitlines():
            if b"Microsoft.NETCore.App" in line and b"8.0." in line:
                return True
    except Exception:
        return False

    return False


def validate_game_path(game_path):
    return bool(game_path and os.path.isfile(game_path))


def validate_dependency_paths():
    missing = []

    dependency_paths = {
        "UnrealPak": unrealPak,
        "UEJSON": uejsonPath,
        "repak": repakPath,
        "ffmpeg": ffmpegPath,
        "ue4dds": ue4ddsPath,
        "ue4dds python": ue4ddsPythonPath,
    }

    for name, path in dependency_paths.items():
        if not path or not os.path.exists(path):
            missing.append(f"{name}: {path}")

    return missing


def clean_mod_workspace():
    safe_rmtree(os.path.join(ASSETS_DIR, "mod"))


def extract_character_assets(aes_key, game_path, cancel=None):
    ensure_dir(ASSETS_DIR)

    run_hidden_command(
        [
            repakPath,
            "--aes-key", aes_key,
            "unpack",
            "-o", ASSETS_DIR,
            "-i", "**/Ch[0-3][0-9][0-9]/PA_Ch[0-9][0-9][0-9].*",
            game_path,
        ],
        is_cancelled_callback=cancel,
    )

    run_hidden_command(
        [
            repakPath,
            "--aes-key", aes_key,
            "unpack",
            "-o", ASSETS_DIR,
            "-i", "**/Ch[0-3][0-9][0-9]/GUI/Costume/L/*0_*L.*",
            game_path,
        ],
        is_cancelled_callback=cancel,
    )


def remove_character_zero():
    ch000 = os.path.join(CHARACTER_DIR, "Ch000")
    if os.path.exists(ch000):
        shutil.rmtree(ch000, ignore_errors=True)


def extract_character_jsons(cancel=None):
    if not os.path.isdir(CHARACTER_DIR):
        raise RuntimeError("Character directory was not found after extraction.")

    for character in os.listdir(CHARACTER_DIR):
        character_dir = os.path.join(CHARACTER_DIR, character)
        if not os.path.isdir(character_dir):
            continue

        pa_path = os.path.normpath(os.path.join(character_dir, f"PA_{character}.uasset"))
        if not os.path.exists(pa_path):
            continue

        run_hidden_command(
            [uejsonPath, "-e", pa_path],
            is_cancelled_callback=cancel,
        )


def _process_single_thumbnail(skin_path, gui_dir, png_path, tga_path, cancel=None):
    """Función de ayuda para procesar una sola imagen en un hilo secundario."""
    try:
        # The bundled converter supports PNG directly; retain the established
        # TGA/ffmpeg path for textures it cannot convert directly.
        try:
            run_hidden_command([ue4ddsPythonPath, ue4ddsPath, skin_path,
                                f'--save_folder={gui_dir}', '--mode=export',
                                '--export_as=png', '--skip_non_texture'],
                               is_cancelled_callback=cancel)
            from PySide6.QtGui import QImage
            if not QImage(png_path).isNull():
                return None
        except ExportCancelled:
            raise
        except Exception:
            pass
        run_hidden_command(
            [
                ue4ddsPythonPath,
                ue4ddsPath,
                skin_path,
                f"--save_folder={gui_dir}",
                "--mode=export",
                "--export_as=tga",
                "--skip_non_texture",
            ],
            is_cancelled_callback=cancel
        )

        if os.path.exists(tga_path):
            run_hidden_command(
                [
                    ffmpegPath,
                    "-y",
                    "-i", tga_path,
                    png_path,
                ],
                is_cancelled_callback=cancel
            )
            try:
                os.remove(tga_path)
            except OSError:
                pass
        if not os.path.isfile(png_path):
            return f"No se generó miniatura: {skin_path}"
    except ExportCancelled:
        raise
    except Exception as exc:
        return f"{skin_path}: {exc}"
    return None


def extract_missing_thumbnails(cancel=None):
    """Versión optimizada con Multithreading."""
    if not os.path.isdir(CHARACTER_DIR):
        return

    tasks = []

    for character in os.listdir(CHARACTER_DIR):
        character_dir = os.path.join(CHARACTER_DIR, character)
        if not os.path.isdir(character_dir):
            continue

        gui_dir = os.path.join(character_dir, "GUI", "Costume", "L")
        if not os.path.isdir(gui_dir):
            continue

        for skin_image in os.listdir(gui_dir):
            if not skin_image.lower().endswith(".uasset"):
                continue

            skin_path = os.path.join(gui_dir, skin_image)
            png_path = skin_path[:-7] + ".png"
            tga_path = skin_path[:-7] + ".tga"

            if os.path.exists(png_path):
                continue

            tasks.append((skin_path, gui_dir, png_path, tga_path))

    if not tasks:
        return

    # Usamos ThreadPoolExecutor pero limitamos a los núcleos disponibles para no ahogar la PC
    max_threads = min(4, os.cpu_count() or 2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(_process_single_thumbnail, *task, cancel=cancel) for task in tasks]
        warnings = []
        for future in concurrent.futures.as_completed(futures):
            raise_if_cancelled(cancel)
            warning = future.result()
            if warning:
                warnings.append(warning)
        return warnings


def prepare_game_assets(aes_key, game_path, use_cache=True, progress_callback=None, is_cancelled_callback=None):
    from services.incremental_service import refresh_assets
    result = refresh_assets(aes_key, game_path, is_cancelled_callback, progress_callback)
    result['prepared'] = not result['used_cache']
    return result
