# -*- mode: python ; coding: utf-8 -*-
# Build: python -m PyInstaller --noconfirm aurora.spec
import os
a = Analysis(
    ['main.py'], pathex=[], binaries=[],
    datas=[('dependencies', 'dependencies'), ('UEJSON', 'UEJSON'), ('branding/outfitflux.ico', 'branding')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter'], noarchive=False, optimize=0,
)
# Qt uses Windows' unversioned ICU API. Do not shadow the system ICU shim with
# a version-suffixed Poppler/Conda DLL discovered through the build host PATH.
a.binaries = [entry for entry in a.binaries
              if entry[0].lower() not in ('icuuc.dll', 'icudt78.dll')]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='OutfitFlux',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=bool(os.environ.get('AURORA_BUILD_CONSOLE')), icon='branding/outfitflux.ico')
if not os.environ.get('OUTFITFLUX_EXE_ONLY'):
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='OutfitFlux')
