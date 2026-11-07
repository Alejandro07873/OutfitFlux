import traceback

from services.catalog_web_service import merge_web_catalog_into_local
from services.skin_id_map_service import rebuild_skin_id_map_file, load_skin_id_map


def update_language(language, internal_name_map):
    print(f"Updating {language} catalog...")
    result = merge_web_catalog_into_local(
        language=language,
        internal_name_map=internal_name_map,
    )
    print(f"Done {language}: {result}")


def main():
    try:
        print("Rebuilding skin_id_map.json from PA files...")
        map_result = rebuild_skin_id_map_file()
        print(f"Skin ID map rebuilt: {map_result}")

        internal_name_map = load_skin_id_map()

        update_language("en", internal_name_map)
        update_language("es", internal_name_map)

        print("Catalog update finished successfully.")

    except Exception as e:
        print("Catalog update failed.")
        print(str(e))
        print(traceback.format_exc())


if __name__ == "__main__":
    main()