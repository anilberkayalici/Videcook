# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Videcook — portable folder build.

import sys
from pathlib import Path

# Collect bin/*.exe files if they exist, skip otherwise
_bin_dir = Path(__file__).resolve().parent / "bin"
_binaries = []
for _exe in sorted(_bin_dir.glob("*.exe")):
    _binaries.append((str(_exe), "bin"))

a = Analysis(
    ["videcook/main.py"],
    pathex=[],
    binaries=_binaries,
    datas=[
        ("locales", "locales"),
        ("README.md", "."),
        ("THIRD_PARTY_LICENSES.md", "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "email",
        "html",
        "http",
        "xml",
        "pydoc",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Videcook",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Videcook",
)
