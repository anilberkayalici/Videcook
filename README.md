# Videcook

**TR:** Videcook, yt-dlp + cookies.txt + FFmpeg kullanarak video indirmeyi kolaylaştıran; kendi Groq API anahtarınızla İngilizce SRT altyazı üretebilen; Windows ve Linux üzerinde çalışan bir masaüstü uygulamasıdır. Kullanıcıların komut satırı (CMD/Terminal) ile uğraşmasına gerek kalmaz.

**EN:** Videcook is a cross-platform desktop application that simplifies video downloading using yt-dlp + cookies.txt + FFmpeg, and can create English SRT subtitles using the user's own Groq API key. It runs on Windows and Linux. Users never need to touch the command line.

## Languages

Videcook supports **Turkish** (default) and **English**. A TR/EN toggle in the header switches all UI text instantly. The selected language is remembered across restarts.

## Supported Platforms

- **Windows:** Windows 10 / 11 (64-bit) portable ZIP
- **Linux:** x86_64 AppImage

Pre-built releases for both platforms are available from the [GitHub Releases](https://github.com/anilberkayalici/Videcook/releases) page.

## Features

- **Cross-platform GUI** — Built with PySide6; runs on Windows and Linux.
- **Video downloads** — Quality presets: Best, 1080p, 720p, 480p.
- **Audio-only downloads** — Extract audio to MP3, M4A, OPUS, AAC, FLAC, or WAV.
- **Playlist support** — Automatically detects playlist URLs and handles them as a single job.
- **Members-only / private videos** — Optional `cookies.txt` support for authenticated downloads.
- **Embed thumbnail & metadata** — For audio downloads.
- **Advanced yt-dlp arguments** — Power users can add custom flags such as `--limit-rate 5M` or `--sleep-interval 3`.
- **In-app binary management** — First-run setup wizard downloads yt-dlp, FFmpeg, and FFprobe automatically.
- **yt-dlp update checker** — Check the installed yt-dlp version against the latest GitHub release and update in one click.
- **English SRT subtitles** — Convert any audio file to English `.srt` using Groq Whisper.
- **Secure API key storage** — Groq API key is encrypted on Windows (DPAPI) and protected on Linux (chmod 600).
- **Preference persistence** — Last output folder, quality choice, audio format, embed-thumbnail option, language, and advanced args are all remembered.
- **Modern dark wine theme** — Updated dark UI with sidebar navigation.
- **Help page** — Built-in guides for download, subtitle, and settings workflows.
- **Cancellation & cleanup** — Downloads and subtitle jobs can be cancelled cleanly without leaking threads or leaving zombie processes.

## Architecture

- **`videcook/core/`** — URL/cookie/path validation, yt-dlp command construction (safe argument lists, never shell strings), progress output parsing, playlist detection, and subtitle utilities.
- **`videcook/services/`** — Binary locator/downloader, download process (subprocess with cancellation), Groq Whisper transcription, secure API-key storage, and yt-dlp update checker.
- **`videcook/ui/`** — PySide6 dark-themed GUI with sidebar navigation, download page, subtitle page, settings page, help page, setup wizard, and off-thread workers.
- **`locales/`** — Turkish (default) and English JSON string tables.

Cookie files are **never** read, stored, or logged by Videcook.

## Development

### Prerequisites

- Python 3.11 or later
- Windows 10 / 11 or Linux

### Setup

```bash
git clone https://github.com/anilberkayalici/Videcook.git videcook
cd videcook
python -m pip install -r requirements.txt
```

### Run (Development)

```bash
python -m videcook.main
```

The app will launch in its dark-themed GUI. You can toggle Turkish/English with the **TR/EN** button in the header.

No real downloads can happen until helper binaries are installed (see below).

### Tests

```bash
python -m pytest -q
```

UI smoke tests use `pytest-qt` and do **not** require binaries or network access.

---

## Required Binaries for Downloading

Videcook wraps these command-line tools as subprocesses:

| Tool | Windows | Linux | Purpose |
|------|---------|-------|---------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | `yt-dlp.exe` | `yt-dlp` | Video download engine |
| [FFmpeg](https://ffmpeg.org/) | `ffmpeg.exe` | `ffmpeg` | Format conversion / muxing |
| [FFprobe](https://ffmpeg.org/) | `ffprobe.exe` | `ffprobe` | Media inspection |

### Method 1 — First-Run Setup Wizard

When binaries are missing, Videcook shows a setup wizard. Click the download button and the app will fetch the official yt-dlp and FFmpeg/FFprobe builds automatically.

### Method 2 — Download Script

```bash
python scripts/download_binaries.py --all
```

This downloads pre-built binaries from the official GitHub releases of yt-dlp and BtbN/FFmpeg-Builds for the current platform.

### Method 3 — Manual Placement

Place the files inside the `bin/` folder:

```
bin/
  yt-dlp      (yt-dlp.exe on Windows)
  ffmpeg      (ffmpeg.exe on Windows)
  ffprobe     (ffprobe.exe on Windows)
```

The app will auto-detect them on launch. If they are missing, the Settings page will show **MISSING** for each binary and the Download button will show a helpful error message instead of crashing.

Note: `bin/` is git-ignored (except `.gitkeep`). These files are **never** committed to the repository.

---

## Download Page

The main download page lets you:

1. Paste a video or playlist URL.
2. Choose **Video** or **Audio** mode.
3. Pick a quality (video) or audio format.
4. Toggle **Members-only** to attach a `cookies.txt` file for authenticated content.
5. Choose the output folder.
6. Start the download and monitor progress, speed, and logs in real time.

### Advanced yt-dlp Arguments

Open **Settings** and enter extra flags in the **Advanced yt-dlp arguments** field. These are appended safely to every yt-dlp command. Example:

```text
--limit-rate 5M --sleep-interval 3
```

Arguments are parsed with `shlex`, so quoted values such as `--proxy "http://..."` are handled correctly.

---

## English SRT Subtitles

1. Obtain a personal Groq API key and save it from **Settings**.
2. Open **Subtitles**, choose an audio file, and choose the target `.srt` path.
3. Click **Create SRT**.

Videcook converts the audio to a compact temporary format, sends sequential chunks to Groq Whisper, and creates an English `.srt` file.

The API key is stored using platform-native protection:

- **Windows:** DPAPI (CryptProtectData / CryptUnprotectData)
- **Linux:** file permissions `chmod 600` inside a restricted directory

It is never included in the portable package or GitHub repository.

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

Zip and distribute the entire `dist/Videcook/` folder. No installation is required: users extract the ZIP and double-click `Videcook.exe`.

### Important

- The portable folder is **not** a single `.exe`. Distribute the whole folder inside a ZIP, and tell users to extract it before opening the app.
- Microsoft Defender may flag unsigned PyInstaller files. Adding a code-signing certificate to `Videcook.spec` can resolve this for distribution.
- If you update binaries, re-run the build script.

---

## Building a Linux AppImage

AppImage builds must be created on a Linux machine because PyInstaller and `appimagetool` need native Linux tooling.

### Build

```bash
scripts/build_linux.sh
```

This will:

1. Install Python dependencies.
2. Build the portable folder with PyInstaller.
3. Prepare an AppDir from `dist/Videcook/`.
4. Create `release/Videcook-v{VERSION}-linux-x86_64.AppImage`.

### Prerequisites

- `python3` and `pip`
- `pyinstaller`
- `appimagetool` from [AppImageKit releases](https://github.com/AppImage/AppImageKit/releases)

### Run the AppImage

```bash
chmod +x Videcook-v0.2.0-linux-x86_64.AppImage
./Videcook-v0.2.0-linux-x86_64.AppImage
```

If the AppImage does not start, install `libfuse2` on your distribution. Downloaded helper binaries and user preferences are stored in the platform-appropriate user data directory (`~/.local/share/Videcook` on Linux).

---

## Data & Privacy

- **Cookie files** are never read, stored, or logged by Videcook. Only the filename appears in the UI; the full path is never logged.
- **Groq API keys** are encrypted/protected locally and never leave the device except when sent to Groq's API for transcription.
- **Preferences, logs, and downloaded helper binaries** are stored in the user's data directory, never inside the application folder.

## Cookie Safety

Videcook follows strict cookie-handling rules verified by automated tests:

1. **Never reads** cookie file contents.
2. **Never persists** cookie file paths across sessions.
3. **Never logs** full cookie file paths in the log panel.
4. Only the **filename** (e.g., `cookies.txt`) appears in the UI and logs.
5. The internal cookie path reference is cleared after every download (success, failure, or cancellation).

---

## License

Videcook source code is available under the MIT License (see LICENSE file if present). Third-party licenses for yt-dlp, FFmpeg, and other bundled tools are documented in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
