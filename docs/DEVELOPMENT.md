# 🛠️ Development

## Environment

Use Windows x64 and Python 3.10. Install `requirements-dev.txt` in a virtual environment. UEJSON requires the .NET 8 runtime. The application uses PySide6; no Node.js toolchain is needed.

## External tools

The source package deliberately excludes binaries and personal data. Restore the matching tool distributions at these paths before running extraction/export:

| Tool | Required location |
| --- | --- |
| repak | `dependencies/repak/repak.exe` |
| UnrealPak and its runtime files | `dependencies/unrealpak/UnrealPak.exe` |
| FFmpeg | `dependencies/ffmpeg/bin/ffmpeg.exe` |
| UE4-DDS Tools | `dependencies/ue4dds/src/main.py` |
| Compatible embedded Python for UE4-DDS Tools | `dependencies/ue4dds/python/python.exe` |
| UEJSON and its companion DLL/runtime files | `UEJSON/UEJSON.exe` |

Use **Tools → Settings → Diagnostics** to check local dependencies. Keep complete tool distributions, including runtime files and notices. The current project contains a compiled UEJSON tool but no UEJSON application source; a complete rebuild of that tool is not provided here. UAssetAPI alone is a library, not a replacement for the UEJSON command-line interface.

## Run and test

```powershell
python main.py
python -m unittest discover -s tests
```

Tests that require a prepared game library or real external binaries may be skipped in a clean source checkout. `python main.py --classic` opens the legacy interface.

## Source map

| Path | Purpose |
| --- | --- |
| `ui/studio_layout.py` | Main workspace layout |
| `ui/studio_shell.py` | Dark/light palettes and widget styling |
| `ui/studio_window.py` | User actions and orchestration |
| `ui/export_review.py` | Export confirmation and folder options |
| `ui/export_queue.py` | Background jobs and progress |
| `ui/outfit_translations.py` | Secondary interface translations |
| `services/studio_service.py` | Library and batch export |
| `services/safe_export_service.py` | Isolated export and PAK checks |
| `services/incremental_service.py` | Cached asset preparation |
| `services/update_service.py` | GitHub Releases updater |

## Build

```powershell
python -m PyInstaller --noconfirm aurora.spec
python scripts/package_release.py dist/OutfitFlux
```

For local development only, set `OUTFITFLUX_EXE_ONLY=1` to rebuild just `build/aurora/OutfitFlux.exe` and reuse a compatible existing `_internal` directory. Remove that environment variable for a full distributable build. Never assume an old runtime includes newly introduced dependencies.

Update `APP_VERSION` in `util.py` and `CHANGELOG.md` together. Do not commit caches, PAKs, game assets, settings or compiled distributions.

## Automated checks

The included GitHub Actions workflow runs tests on Windows for pushes and pull requests. Game-dependent integration tests are skipped when external tools or local assets are unavailable. Binary releases are built locally with the required tools.
