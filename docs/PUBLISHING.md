# 🚀 Publish OutfitFlux

[Guía paso a paso en español](GUIA_PUBLICACION_ES.md)

## 1. Create the repository

Create an empty GitHub repository named **OutfitFlux**. Suggested description:

> A polished Windows costume swapper for My Hero Ultra Rumble, with batch exports, a background queue and dark/light themes.

Suggested topics: `python`, `pyside6`, `windows`, `modding`, `unreal-engine`, `my-hero-ultra-rumble`.

From the prepared source folder, after replacing OWNER with your GitHub username:

```powershell
git init -b main
git add .
git status
git commit -m "Introduce OutfitFlux"
git remote add origin https://github.com/OWNER/OutfitFlux.git
git push -u origin main
```

Review `git status` before committing. The prepared source excludes personal settings, caches, game content, mods and third-party binaries. Choose the project's license only after checking the inherited code and dependencies; this preparation does not invent permission to relicense them.

## 2. Publish a Windows release

1. Build locally with the external tools installed; see [Development](DEVELOPMENT.md).
2. Run `python scripts/package_release.py dist/OutfitFlux`.
3. In GitHub, open **Releases → Draft a new release**.
4. Use a tag matching `util.py`, for example `v1.1.5`.
5. Copy the matching entry from `CHANGELOG.md` and attach `OutfitFlux-windows-x64.zip` plus its `.sha256` file.
6. Check the package in a separate writable directory, then publish a stable release.

The automatic GitHub source-code ZIP is not the Windows application. The updater expects the exact asset name `OutfitFlux-windows-x64.zip` and an `OutfitFlux/` root containing the executable and `_internal/` directory.

## 3. Connect the app

Open **Tools → Settings → Updates**, enter `OWNER/OutfitFlux`, then check for updates. The repository is deliberately unset until you create it. Updates install beside the previous version and preserve user data. They do not automatically remove older folders.

## 4. Maintain the presentation

- Edit `README.md` for the repository homepage.
- Edit `docs/media/banner.svg` for the header.
- Regenerate screenshots using `python scripts/capture_screenshots.py` with a prepared local library.
- Follow `docs/BRAND.md` for icon assets.
- Use the included issue and pull-request templates.

GitHub reference: [Managing releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
