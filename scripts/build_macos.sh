#!/usr/bin/env bash
# Build a macOS .app bundle and package it as a DMG.
# Must be run on macOS (PyInstaller and create-dmg need native macOS).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "==> Checking macOS"
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "ERROR: This build must run on macOS." >&2
    exit 1
fi

VERSION=$(python3 -c "from videcook import __version__; print(__version__)")

echo "==> Installing Python dependencies"
python3 -m pip install -r requirements.txt
python3 -m pip install "pyinstaller>=6.0"

echo "==> Ensuring create-dmg is available"
if ! command -v create-dmg &>/dev/null; then
    if command -v brew &>/dev/null; then
        brew install create-dmg
    else
        echo "ERROR: create-dmg not found. Install Homebrew or download create-dmg manually." >&2
        exit 1
    fi
fi

echo "==> Cleaning previous build"
rm -rf build dist "release/Videcook-v*-macos.dmg" 2>/dev/null || true

echo "==> Generating .icns icon from .png"
ICONSET="$(pwd)/assets/videcook.iconset"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
PNG="assets/videcook.png"
if [[ ! -f "$PNG" ]]; then
    echo "ERROR: $PNG not found." >&2
    exit 1
fi
sips -z 16 16    "$PNG" --out "$ICONSET/icon_16x16.png"       >/dev/null
sips -z 32 32    "$PNG" --out "$ICONSET/icon_16x16@2x.png"    >/dev/null
sips -z 32 32    "$PNG" --out "$ICONSET/icon_32x32.png"       >/dev/null
sips -z 64 64    "$PNG" --out "$ICONSET/icon_32x32@2x.png"    >/dev/null
sips -z 128 128  "$PNG" --out "$ICONSET/icon_128x128.png"     >/dev/null
sips -z 256 256  "$PNG" --out "$ICONSET/icon_128x128@2x.png"  >/dev/null
sips -z 256 256  "$PNG" --out "$ICONSET/icon_256x256.png"     >/dev/null
sips -z 512 512  "$PNG" --out "$ICONSET/icon_256x256@2x.png"  >/dev/null
sips -z 512 512  "$PNG" --out "$ICONSET/icon_512x512.png"     >/dev/null
sips -z 1024 1024 "$PNG" --out "$ICONSET/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$ICONSET" -o "assets/videcook.icns"
rm -rf "$ICONSET"

echo "==> Building with PyInstaller"
pyinstaller --clean --noconfirm --windowed --osx-bundle-identifier com.anilberkayalici.videcook Videcook.spec

echo "==> Creating DMG"
OUTPUT="release/Videcook-v${VERSION}-macos.dmg"
rm -f "$OUTPUT"
create-dmg \
  --volname "Videcook" \
  --volicon "assets/videcook.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "Videcook.app" 200 190 \
  --hide-extension "Videcook.app" \
  --app-drop-link 600 185 \
  --no-internet-enable \
  "$OUTPUT" \
  "dist/Videcook.app" \
  || true

if [[ ! -f "$OUTPUT" ]]; then
    echo "==> create-dmg failed, falling back to hdiutil"
    hdiutil create -volname "Videcook" -srcfolder "dist/Videcook.app" -ov -format UDZO "$OUTPUT"
fi

echo "==> Done: $OUTPUT"
