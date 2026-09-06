#!/usr/bin/env bash
# Build a portable Linux AppImage for Videcook.
# Prerequisites: python3, pip, PyInstaller, appimagetool (see below)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing Python dependencies"
pip install -r requirements.txt build

echo "==> Cleaning previous build"
rm -rf build dist release/Videcook-v*-linux.AppImage 2>/dev/null || true

echo "==> Building with PyInstaller"
pyinstaller --clean --noconfirm Videcook.spec

echo "==> Preparing AppDir"
APPDIR="$(pwd)/dist/Videcook.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR"

cp -r dist/Videcook/* "$APPDIR/"
cp assets/videcook.png "$APPDIR/" 2>/dev/null || true
cp assets/videcook.desktop "$APPDIR/" 2>/dev/null || true

echo "==> Creating AppImage"
VERSION=$(python -c "from videcook import __version__; print(__version__)")
OUTPUT="release/Videcook-v${VERSION}-linux-x86_64.AppImage"

if command -v appimagetool &>/dev/null; then
    ARCH=x86_64 appimagetool "$APPDIR" "$OUTPUT"
    chmod +x "$OUTPUT"
    echo "==> AppImage created: $OUTPUT"
else
    echo "==> appimagetool not found – skipping AppImage creation"
    echo "==> Portable folder ready at: dist/Videcook/"
    echo "   Install appimagetool: https://github.com/AppImage/AppImageKit/releases"
fi

echo "==> Done"
