import os
import subprocess
from pathlib import Path

from util import (
    MOD_DIR,
    repakPath,
    CREATE_NO_WINDOW,
    ensure_dir,
    safe_rmtree,
)


def run_hidden_command(command):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=CREATE_NO_WINDOW,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (code {result.returncode}):\n{' '.join(map(str, command))}\n\n"
            f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        )

    return result


def cleanup_mod_workspace():
    safe_rmtree(MOD_DIR)


def unpack_mod_file(mod_file, output_dir=MOD_DIR):
    # Only the legacy owned workspace may be cleared automatically.
    if Path(output_dir).resolve() == Path(MOD_DIR).resolve():
        cleanup_mod_workspace()
    ensure_dir(output_dir)

    from services.pak_service import extract_pak
    extract_pak(mod_file, output_dir)


def build_expected_mesh_filename(mesh_dir: Path):
    """
    Reproduce la lógica actual del proyecto,
    pero encapsulada y más segura.
    """
    try:
        if mesh_dir.parent.name == "Default":
            # .../Character/Ch001/Model/Default/Mesh
            return f"SK_{mesh_dir.parents[2].name}_Default_00.uasset"

        # .../Character/Ch001/Model/Costume/01/Mesh
        return f"SK_{mesh_dir.parents[3].name}_{mesh_dir.parents[1].name}{mesh_dir.parent.name}.uasset"
    except IndexError:
        return None


def find_candidate_mesh_files(mod_extract_dir):
    root = Path(mod_extract_dir)
    if not root.exists():
        return []

    mesh_files = []

    for mesh_dir in root.rglob("Mesh"):
        if not mesh_dir.is_dir():
            continue

        expected_filename = build_expected_mesh_filename(mesh_dir)
        if not expected_filename:
            continue

        candidate = mesh_dir / expected_filename
        if candidate.exists():
            mesh_files.append(candidate)

    # quitar duplicados por si acaso
    unique_files = []
    seen = set()

    for path in mesh_files:
        norm = str(path.resolve()).lower()
        if norm not in seen:
            seen.add(norm)
            unique_files.append(path)

    return unique_files


def detect_character_from_mesh_file(mesh_file: Path):
    parts = list(mesh_file.parts)

    try:
        idx = parts.index("Character")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    except ValueError:
        pass

    return None


def detect_mod_type(mesh_file: Path):
    parts = set(mesh_file.parts)

    if "Default" in parts:
        return "default"
    if "Costume" in parts:
        return "costume"

    return "unknown"


def detect_mod_mesh(mod_extract_dir):
    result = {
        "valid": False,
        "error_message": "",
        "detected_character": None,
        "current_skin_name_internal": None,
        "current_mesh_file": None,
        "current_mesh_path": None,
        "detected_mod_type": None,
    }

    if not os.path.exists(mod_extract_dir):
        result["error_message"] = "The extracted mod directory does not exist."
        return result

    mesh_files = find_candidate_mesh_files(mod_extract_dir)

    if not mesh_files:
        result["error_message"] = (
            "Invalid mod file.\n\n"
            "No compatible skin mesh was found in the extracted mod."
        )
        return result

    if len(mesh_files) > 1:
        preview = "\n".join(f"- {path.name}" for path in mesh_files[:10])
        result["error_message"] = (
            "Invalid mod file.\n\n"
            "The mod contains multiple compatible skin meshes.\n"
            "This version of the app expects exactly one.\n\n"
            f"Detected meshes:\n{preview}"
        )
        return result

    mesh_file = mesh_files[0]
    detected_character = detect_character_from_mesh_file(mesh_file)

    if not detected_character:
        result["error_message"] = (
            "A compatible mesh was found, but the character could not be detected."
        )
        return result

    result.update({
        "valid": True,
        "error_message": "",
        "detected_character": detected_character,
        "current_skin_name_internal": mesh_file.stem,
        "current_mesh_file": mesh_file.name,
        "current_mesh_path": str(mesh_file.parent),
        "detected_mod_type": detect_mod_type(mesh_file),
    })

    return result


def analyze_mod_pak(mod_file):
    if not mod_file or not os.path.isfile(mod_file):
        return {
            "valid": False,
            "error_message": "The selected mod file does not exist.",
            "detected_character": None,
            "current_skin_name_internal": None,
            "current_mesh_file": None,
            "current_mesh_path": None,
            "detected_mod_type": None,
        }

    unpack_mod_file(mod_file, MOD_DIR)
    return detect_mod_mesh(MOD_DIR)
