# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Videcook — portable folder build.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# Collect bin/*.exe files if they exist, skip otherwise
# SPECPATH is set by PyInstaller to the directory containing the spec file
_spec_dir = Path(SPECPATH) if "SPECPATH" in dir() else Path(".").resolve()
_bin_dir = _spec_dir / "bin"
_binaries = []
for _exe in sorted(_bin_dir.glob("*.exe")):
    _binaries.append((str(_exe), "bin"))

# The Groq SDK has dynamically loaded pieces; include its package metadata and
# imports so the distributed executable has the same runtime as development.
_groq_datas, _groq_binaries, _groq_hiddenimports = collect_all("groq")

a = Analysis(
    ["videcook/main.py"],
    pathex=[],
    binaries=_binaries + _groq_binaries,
    datas=[
        ("locales", "locales"),
        ("assets", "assets"),
        ("README.md", "."),
        ("THIRD_PARTY_LICENSES.md", "."),
    ] + _groq_datas,
    hiddenimports=_groq_hiddenimports,
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
    icon=str(_spec_dir / "assets" / "videcook.ico"),
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
