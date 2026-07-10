# Videcook

**TR:** Videcook, yt-dlp + cookies.txt + FFmpeg kullanarak video indirmeyi kolaylaştıran; ayrıca kendi Groq API anahtarınızla İngilizce SRT altyazı üretebilen bir Windows masaüstü uygulamasıdır. Kullanıcıların komut satırı (CMD) ile uğraşmasına gerek kalmaz.

**EN:** Videcook is a Windows desktop application that simplifies video downloading using yt-dlp + cookies.txt + FFmpeg and can create English SRT subtitles using the user's own Groq API key. Users never need to touch the command line.

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

Video download, first-run helper tool setup, and English SRT creation are implemented. The portable Windows package contains the Python/Qt/Groq runtime; users supply their own Groq API key for subtitles.

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

## English SRT Subtitles

1. Obtain a personal Groq API key and save it from **Settings**.
2. Open **Subtitles**, choose an audio file, and choose the target `.srt` path.
3. Click **Create SRT**.

Videcook converts the audio to a compact temporary format, sends sequential
chunks to Groq Whisper, and creates an English `.srt` file. The API key is
stored with Windows user encryption and is never included in the portable
package or GitHub repository.

---

## Building a Portable Windows Distribution

### Build

```bash
scripts\build_portable.bat
```

This runs PyInstaller with `Videcook.spec` and produces:

```
dist/
  Videcook/
    Videcook.exe
    _internal/    ← Qt, Python, Groq and bundled resources
    locales/      ← tr.json, en.json
    README.md
    THIRD_PARTY_LICENSES.md
```

Zip and distribute the entire `dist/Videcook/` folder. No installation is
required: users extract the ZIP and double-click `Videcook.exe`.

### What Happens

- The PyInstaller spec (`Videcook.spec`) bundles all `.py` files + required
  Qt/PySide6 DLLs automatically.
- `locales/`, `README.md`, and `THIRD_PARTY_LICENSES.md` are included as data.
- Any `bin/*.exe` files present at build time are placed into the package. If
  they are absent, the app still opens and its first-run setup can download
  them with the user's confirmation.
- Preferences, logs and helper tools downloaded after installation are kept in
  `%LOCALAPPDATA%\\Videcook`, never inside the application folder.
- The `--clean` flag removes previous build artifacts before each build.

### Important

- The portable folder is **not** a single `.exe`. Distribute the whole folder
  inside a ZIP, and tell users to extract it before opening the app.
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
