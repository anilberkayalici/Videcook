# Videcook

**TR:** Videcook, yt-dlp + cookies.txt + FFmpeg kullanarak video indirmeyi kolaylaştıran bir Windows masaüstü uygulamasıdır. Kullanıcıların komut satırı (CMD) ile uğraşmasına gerek kalmaz.

**EN:** Videcook is a Windows desktop application that simplifies video downloading using yt-dlp + cookies.txt + FFmpeg. Users never need to touch the command line.

## Languages

Videcook supports **Turkish** (default) and **English**. A small TR/EN toggle switches all UI text instantly.

## Architecture

- **`videcook/core/`** — URL/cookie/path validation, yt-dlp command construction
  (safe argument lists, never shell strings), progress output parsing, playlist detection.
- **`videcook/services/`** — Binary locator, download process (subprocess with cancellation).
- **`videcook/ui/`** — PySide6 dark-themed GUI with download form, integrated help page,
  settings page, TR/EN toggle, and off-thread download worker.
- **`locales/`** — Turkish (default) and English JSON string tables.

Cookie files are **never** read, stored, or logged by Videcook.

## Status

Engine integration complete. GUI + download worker wired. Packaging implemented.

---

## Development

### Prerequisites

- Python 3.11 or later
- Windows 10 / 11

### Setup

```bash
git clone <repo-url> videcook
cd videcook
python -m pip install -r requirements.txt
```

### Run (Development)

```bash
python -m videcook.main
```

The app will launch in its dark-themed GUI. You can toggle Turkish/English
with the **TR/EN** button in the header.

No real downloads can happen until helper binaries are installed (see below).

### Tests

```bash
python -m pytest -q
```

UI smoke tests use `pytest-qt` and do **not** require binaries or network access.

---

## Required Binaries for Downloading

Videcook wraps these command-line tools as subprocesses:

| Tool | File | Purpose |
|------|------|---------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | `yt-dlp.exe` | Video download engine |
| [FFmpeg](https://ffmpeg.org/) | `ffmpeg.exe` | Format conversion / muxing |
| [FFprobe](https://ffmpeg.org/) | `ffprobe.exe` | Media inspection |

### Method 1 — Download Script

```bash
python scripts/download_binaries.py --all
```

This downloads pre-built Windows binaries from the official GitHub releases of
yt-dlp and BtbN/FFmpeg-Builds.

### Method 2 — Manual Placement

Place the following files inside the `bin/` folder:

```
bin/
  yt-dlp.exe
  ffmpeg.exe
  ffprobe.exe
```

The app will auto-detect them on launch. If they are missing, the Settings page
will show **MISSING** for each binary and the Download button will show a
helpful error message instead of crashing.

Note: `bin/` is git-ignored (except `.gitkeep`). These files are **never**
committed to the repository.

---

## Building a Portable Windows Distribution

### One-time Setup

```bash
python -m pip install pyinstaller
```

### Build

```bash
scripts\build_portable.bat
```

This runs PyInstaller with `Videcook.spec` and produces:

```
dist/
  Videcook/
    Videcook.exe
    bin/          ← yt-dlp.exe, ffmpeg.exe, ffprobe.exe (if available)
    locales/      ← tr.json, en.json
    README.md
    THIRD_PARTY_LICENSES.md
```

Copy the entire `dist/Videcook/` folder anywhere. No installation required.
Double-click `Videcook.exe` to run.

### What Happens

- The PyInstaller spec (`Videcook.spec`) bundles all `.py` files + required
  Qt/PySide6 DLLs automatically.
- `locales/`, `README.md`, and `THIRD_PARTY_LICENSES.md` are included as data.
- Any `bin/*.exe` files present at build time are placed into `bin/` in the
  output. If `bin/` is empty, the built `.exe` will still run — only downloads
  will fail with a clear message.
- The `--clean` flag removes previous build artifacts before each build.

### Important

- The portable folder is **not** a single `.exe`. Distribute the whole folder.
- Microsoft Defender may flag unsigned PyInstaller files. Adding a code-signing
  certificate to `Videcook.spec` can resolve this for distribution.
- If you update binaries, re-run the build script.

---

## Cookie Safety

Videcook follows strict cookie-handling rules verified by automated tests:

1. **Never reads** cookie file contents.
2. **Never persists** cookie file paths across sessions.
3. **Never logs** full cookie file paths in the log panel.
4. Only the **filename** (e.g., `cookies.txt`, never `C:\Users\...\cookies.txt`)
   appears in the UI and logs.
5. The internal cookie path reference is cleared after every download
   (success, failure, or cancellation).

---

## License

Videcook source code is available under the MIT License (see LICENSE file if
present). Third-party licenses for yt-dlp and FFmpeg are documented in
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
