#!/usr/bin/env python3
"""Download helper binaries for Videcook.

Downloads yt-dlp.exe and FFmpeg (ffmpeg.exe, ffprobe.exe) into bin/.

Usage:
    python scripts/download_binaries.py          # interactive
    python scripts/download_binaries.py --all    # download everything
    python scripts/download_binaries.py --yt-dlp # only yt-dlp
    python scripts/download_binaries.py --ffmpeg # only ffmpeg + ffprobe

This script uses only the standard library (no extra dependencies).
It does NOT run during tests or during normal app startup.
"""

import argparse
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BIN_DIR = _PROJECT_ROOT / "bin"

_YTDLP_URL = (
    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
)
_FFMPEG_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)


def _download(url: str, dest: Path, label: str) -> None:
    """Download a file from *url* to *dest* with progress reporting."""
    if dest.exists():
        print(f"[SKIP] {label} already exists: {dest}")
        return

    print(f"[DOWNLOAD] {label} from {url}")
    try:
        with urllib.request.urlopen(url) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            buf = bytearray(8192)
            with open(dest, "wb") as outf:
                while True:
                    n = resp.readinto(buf)
                    if n == 0:
                        break
                    outf.write(buf[:n])
                    downloaded += n
                    if total:
                        pct = downloaded * 100 // total
                        print(f"  {pct}% ({downloaded}/{total} bytes)", end="\r")
        print(f"\n[DONE] {label} saved to {dest}")
    except Exception as exc:
        print(f"\n[ERROR] Failed to download {label}: {exc}")
        if dest.exists():
            dest.unlink()
        raise


def download_ytdlp() -> Path:
    """Download yt-dlp.exe and return its path."""
    _BIN_DIR.mkdir(parents=True, exist_ok=True)
    dest = _BIN_DIR / "yt-dlp.exe"
    _download(_YTDLP_URL, dest, "yt-dlp.exe")
    return dest


def download_ffmpeg() -> tuple[Path, Path]:
    """Download ffmpeg.exe and ffprobe.exe, return their paths."""
    _BIN_DIR.mkdir(parents=True, exist_ok=True)

    ffmpeg_dest = _BIN_DIR / "ffmpeg.exe"
    ffprobe_dest = _BIN_DIR / "ffprobe.exe"

    if ffmpeg_dest.exists() and ffprobe_dest.exists():
        print("[SKIP] ffmpeg.exe and ffprobe.exe already exist")
        return ffmpeg_dest, ffprobe_dest

    print(f"[DOWNLOAD] FFmpeg from {_FFMPEG_URL}")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "ffmpeg.zip"
            _download(_FFMPEG_URL, zip_path, "ffmpeg.zip")

            with zipfile.ZipFile(zip_path, "r") as zf:
                # Find ffmpeg.exe and ffprobe.exe inside the archive
                ffmpeg_member = None
                ffprobe_member = None
                for name in zf.namelist():
                    if name.endswith("/ffmpeg.exe"):
                        ffmpeg_member = name
                    elif name.endswith("/ffprobe.exe"):
                        ffprobe_member = name
                if not ffmpeg_member or not ffprobe_member:
                    raise RuntimeError(
                        "Could not find ffmpeg.exe / ffprobe.exe in the archive"
                    )
                zf.extract(ffmpeg_member, tmp)
                zf.extract(ffprobe_member, tmp)

            shutil.move(str(Path(tmp) / ffmpeg_member), str(ffmpeg_dest))
            shutil.move(str(Path(tmp) / ffprobe_member), str(ffprobe_dest))
        print(f"[DONE] ffmpeg.exe -> {ffmpeg_dest}")
        print(f"[DONE] ffprobe.exe -> {ffprobe_dest}")
    except Exception as exc:
        print(f"[ERROR] Failed to download FFmpeg: {exc}")
        raise

    return ffmpeg_dest, ffprobe_dest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download helper binaries for Videcook"
    )
    parser.add_argument("--all", action="store_true", help="Download all binaries")
    parser.add_argument(
        "--yt-dlp", action="store_true", help="Download only yt-dlp.exe"
    )
    parser.add_argument(
        "--ffmpeg", action="store_true", help="Download only ffmpeg.exe + ffprobe.exe"
    )
    args = parser.parse_args()

    if not any([args.all, getattr(args, "yt-dlp"), getattr(args, "ffmpeg")]):
        parser.print_help()
        print(
            "\nNo option selected. Use --all to download everything, "
            "or --yt-dlp / --ffmpeg for individual tools."
        )
        return 1

    do_ytdlp = args.all or getattr(args, "yt-dlp")
    do_ffmpeg = args.all or getattr(args, "ffmpeg")

    try:
        if do_ytdlp:
            download_ytdlp()
        if do_ffmpeg:
            download_ffmpeg()
    except Exception:
        return 1

    print("\n[READY] All requested binaries are in bin/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
