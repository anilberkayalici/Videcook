# Videcook

**TR:** Videcook, yt-dlp + cookies.txt + FFmpeg kullanarak video indirmeyi kolaylaştıran bir Windows masaüstü uygulamasıdır. Kullanıcıların komut satırı (CMD) ile uğraşmasına gerek kalmaz.

**EN:** Videcook is a Windows desktop application that simplifies video downloading using yt-dlp + cookies.txt + FFmpeg. Users never need to touch the command line.

## Languages

Videcook supports **Turkish** (default) and **English**. A small TR/EN toggle switches all UI text instantly.

## Architecture

The `videcook/core/` package contains testable, non-GUI download logic: URL/cookie/path
validation, yt-dlp command construction (safe argument lists — never shell strings),
progress output parsing, and playlist detection.

The `videcook/ui/` package contains a PySide6 dark-themed GUI shell with a download
form, integrated help page, settings placeholder, and TR/EN language toggle.
Real yt-dlp/ffmpeg download execution is not yet connected.

## Architecture

- **`videcook/core/`** — URL/cookie/path validation, yt-dlp command construction
  (safe argument lists, never shell strings), progress output parsing, playlist detection.
- **`videcook/services/`** — Binary locator, download process (subprocess with cancellation).
- **`videcook/ui/`** — PySide6 dark-themed GUI with download form, integrated help page,
  settings placeholder, TR/EN toggle, and off-thread download worker.
- **`locales/`** — Turkish (default) and English JSON string tables.

Actual downloading requires `yt-dlp.exe` and `ffmpeg.exe` in the `bin/` directory.
Cookie files are **never** read, stored, or logged by Videcook.

## Status

In development — engine integration complete. GUI + download worker wired.
Packaging pending.
