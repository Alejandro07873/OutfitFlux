"""Public export API; legacy UI and Studio share the isolated pipeline."""
import os
from util import ensure_dir
from services.filename_service import build_output_filename
from services.safe_export_service import (ExportCancelled, raise_if_cancelled, run_hidden_command, normalize_export_path, ensure_unique_output_path, find_current_mod_mesh, patch_mesh_json, move_rebuilt_mesh_files, create_final_pak, export_mod_to_skin)


def export_mod_to_many_skins(
    mod_file: str,
    selected_records: list,
    output_dir: str,
    current_record: dict | None = None,
    progress_callback=None,
    is_cancelled_callback=None,
):
    ensure_dir(output_dir)
    from services.catalog_service import costume_filename_names
    known_names = costume_filename_names()

    completed = []
    failed = []
    cancelled = False

    total = len(selected_records)

    for index, record in enumerate(selected_records, start=1):
        if is_cancelled_callback and is_cancelled_callback():
            cancelled = True
            break

        if progress_callback:
            progress_callback(index, total, record)

        try:
            suggested_name = build_output_filename(
                original_mod_path=os.path.basename(mod_file),
                target_skin_name=record["display_name"],
                current_skin_display_name=current_record["display_name"] if current_record else "",
                current_skin_internal_name=current_record["internal_name"] if current_record else "",
                known_skin_names=known_names,
            )

            base_output_path = os.path.join(output_dir, os.path.basename(suggested_name))
            final_output_path = ensure_unique_output_path(base_output_path)

            exported_path = export_mod_to_skin(
                mod_file=mod_file,
                selected_skin=record["skin_path"],
                output_path=final_output_path,
                is_cancelled_callback=is_cancelled_callback,
            )

            completed.append({
                "record": record,
                "output_path": exported_path,
            })

        except ExportCancelled:
            cancelled = True
            break
        except Exception as e:
            failed.append({
                "record": record,
                "error": str(e),
            })

    return {
        "completed": completed,
        "failed": failed,
        "cancelled": cancelled,
        "total": total,
    }
