# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Videcook — portable build.
# Cross-platform: Windows, macOS, and Linux.

import platform
import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

_system = platform.system().lower()  # 'windows', 'darwin', 'linux'
_spec_dir = Path(SPECPATH) if "SPECPATH" in dir() else Path(".").resolve()

# ---------------------------------------------------------------------------
# Optional helper binaries from bin/ (only bundled when present)
# ---------------------------------------------------------------------------

_bin_dir = _spec_dir / "bin"
_binaries = []

if _system == "windows":
    for _exe in sorted(_bin_dir.glob("*.exe")):
        _binaries.append((str(_exe), "bin"))
else:
    # macOS and Linux: helper binaries have no extension
    for _name in ("yt-dlp", "ffmpeg", "ffprobe"):
        _path = _bin_dir / _name
        if _path.is_file():
            _binaries.append((str(_path), "bin"))

# ---------------------------------------------------------------------------
# Version (read from videcook/__init__.py for Info.plist on macOS)
# ---------------------------------------------------------------------------

try:
    _init_text = (_spec_dir / "videcook" / "__init__.py").read_text(encoding="utf-8")
    _version = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', _init_text).group(1)
except Exception:
    _version = "0.0.0"

# ---------------------------------------------------------------------------
# Icon (platform-specific)
# ---------------------------------------------------------------------------

if _system == "windows":
    _icon_path = str(_spec_dir / "assets" / "videcook.ico")
elif _system == "darwin":
    _icon_path = str(_spec_dir / "assets" / "videcook.icns")
else:
    _icon_path = None

# ---------------------------------------------------------------------------
# macOS Info.plist (bundled inside the .app)
# ---------------------------------------------------------------------------

_info_plist = None
if _system == "darwin":
    _info_plist = {
        "CFBundleIdentifier": "com.anilberkayalici.videcook",
        "CFBundleName": "Videcook",
        "CFBundleDisplayName": "Videcook",
        "CFBundleVersion": _version,
        "CFBundleShortVersionString": _version,
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "NSHumanReadableCopyright": "© 2026 Anıl Berlay Alıcı",
    }

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Dynamic dependencies collection (Groq, Pedalboard, SoundDevice)
# ---------------------------------------------------------------------------

_groq_datas, _groq_binaries, _groq_hiddenimports = collect_all("groq")
_pb_datas, _pb_binaries, _pb_hiddenimports = collect_all("pedalboard")
_sd_datas, _sd_binaries, _sd_hiddenimports = collect_all("sounddevice")
_mp_datas, _mp_binaries, _mp_hiddenimports = collect_all("moviepy")

# ---------------------------------------------------------------------------
# PyInstaller Analysis
# ---------------------------------------------------------------------------

a = Analysis(
    ["videcook/main.py"],
    pathex=[],
    binaries=_binaries + _groq_binaries + _pb_binaries + _sd_binaries + _mp_binaries,
    datas=[
        ("locales", "locales"),
        ("assets", "assets"),
        ("README.md", "."),
        ("THIRD_PARTY_LICENSES.md", "."),
    ] + _groq_datas + _pb_datas + _sd_datas + _mp_datas,
    hiddenimports=_groq_hiddenimports + _pb_hiddenimports + _sd_hiddenimports + _mp_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "xml",
        "pydoc",
    ],
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
    icon=_icon_path,
    info_plist=_info_plist,
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
