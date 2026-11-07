# 🚀 Guía para publicar OutfitFlux

Esta guía es para ti y está en español. La portada del repositorio, las capturas y la documentación principal siguen en inglés.

## 1. Qué archivo sirve para cada cosa

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| `repository-ready/OutfitFlux-source.zip` | Código limpio del proyecto. Descomprímelo para editarlo o subirlo al repositorio. |
| `repository-ready/OutfitFlux/` | La misma copia del código, ya descomprimida. |
| `release/OutfitFlux-windows-x64.zip` | La aplicación compilada que descargarán los usuarios. Se sube a Releases. |
| `release/OutfitFlux-windows-x64.zip.sha256` | Huella de comprobación del paquete. Súbela junto al ZIP de Windows. |

No subas toda tu carpeta de trabajo. Usa la copia preparada: así evitas incluir tus mods, cachés, exportaciones y configuraciones personales. Tampoco hace falta subir las carpetas `dist-*`.

## 2. Crear tu repositorio

1. Entra en GitHub con tu cuenta.
2. Pulsa **New repository**.
3. Ponle el nombre **OutfitFlux**.
4. Elige **Public** para que el actualizador pueda consultar las versiones.
5. Déjalo vacío: el proyecto ya incluye README y `.gitignore`.
6. Pulsa **Create repository**.

Puedes usar esta descripción en inglés:

> A polished Windows costume swapper for My Hero Ultra Rumble, with batch exports, a background queue and dark/light themes.

## 3. Subir el código

Descomprime `OutfitFlux-source.zip`. Abre la carpeta que contiene `README.md` con Visual Studio Code y abre una terminal de PowerShell ahí.

Necesitas Git instalado. Sustituye `TU_USUARIO` por tu nombre de usuario real de GitHub:

```powershell
git init -b main
git add .
git status
git commit -m "Introduce OutfitFlux"
git remote add origin https://github.com/TU_USUARIO/OutfitFlux.git
git push -u origin main
```

Antes de `git commit`, revisa lo que muestra `git status`: no deben aparecer tus mods, claves personales, cachés ni carpetas de compilación. GitHub puede pedirte iniciar sesión cuando subas los archivos.

La portada se toma de `README.md`. Las imágenes ya están incluidas y usan rutas relativas: no necesitas subirlas a un servicio aparte.

## 4. Publicar la app para descargarla

1. En tu repositorio, entra en **Releases**.
2. Pulsa **Draft a new release**.
3. Crea una etiqueta igual a la versión de `util.py`: para esta entrega, **v1.1.5**.
4. Usa **OutfitFlux 1.1.5** como título.
5. Copia las novedades de esa versión desde `CHANGELOG.md`.
6. Adjunta `OutfitFlux-windows-x64.zip` y su archivo `.sha256`.
7. Para que la detecte el actualizador, publícala como versión estable, no como borrador ni prerelease.
8. Pulsa **Publish release** cuando hayas revisado los archivos.

**No cambies el nombre del ZIP de Windows:** el actualizador busca exactamente `OutfitFlux-windows-x64.zip`. El ZIP automático de código fuente de GitHub no sustituye este paquete.

## 5. Conectar las actualizaciones en la app

Abre **Herramientas → Configuración → Actualizaciones · GitHub**. Escribe:

```text
TU_USUARIO/OutfitFlux
```

Pulsa **Buscar actualización**. Si ya tienes la misma versión publicada, la app indicará que está al día. Para ofrecer una actualización futura, aumenta `APP_VERSION` en `util.py`, compila y publica una versión con esa misma etiqueta.

## 6. Qué puedes editar

| Quieres cambiar… | Archivo |
| --- | --- |
| La portada del repositorio | `README.md` |
| El banner | `docs/media/banner.svg` |
| El icono | `branding/outfitflux.png` y `branding/outfitflux.ico` |
| Las novedades | `CHANGELOG.md` |
| La distribución de la interfaz | `ui/studio_layout.py` |
| Los colores | `ui/studio_shell.py` |
| El brillo animado del nombre | `ui/animated_wordmark.py` |
| La ventana de exportación | `ui/export_review.py` |
| La cola de intercambios | `ui/export_queue.py` |
| Las traducciones de ventanas secundarias | `ui/outfit_translations.py` |

Para regenerar las capturas con tu biblioteca local preparada:

```powershell
python scripts/capture_screenshots.py
```

## 7. Compilar futuras versiones

El código usa Python 3.10 y PySide6. Primero instala los paquetes:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

La interfaz puede abrirse con `python main.py`. Para extraer y exportar también necesitas los programas externos en las rutas indicadas en [Development](DEVELOPMENT.md): repak, UnrealPak, FFmpeg, UE4-DDS Tools y UEJSON con sus archivos complementarios. El repositorio limpio no incluye esos binarios. UEJSON requiere .NET 8; en el proyecto actual está disponible compilado, pero no se dispone del código de esa herramienta para reconstruirla desde cero.

Con las dependencias preparadas:

```powershell
python -m unittest discover -s tests
python -m PyInstaller --noconfirm aurora.spec
python scripts/package_release.py dist/OutfitFlux
```

No establezcas `OUTFITFLUX_EXE_ONLY` para una compilación completa: ese modo es solo para reutilizar una instalación local existente.

Conserva los créditos del proyecto base y los avisos de las dependencias. La preparación del repositorio no asigna una licencia nueva al código heredado; los detalles están en [Third-party notes](THIRD_PARTY.md).

Referencia oficial: [gestionar Releases en GitHub](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
