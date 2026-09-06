"""Parse available video formats from yt-dlp JSON output."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def fetch_available_formats(ytdlp_path: Path, url: str, timeout: float = 15.0) -> list[str]:
    """Fetch and return a sorted list of available video format labels.
    
    Example output: ["8K (4320p)", "4K (2160p)", "2K (1440p)", "1080p", "720p", "480p", "360p"]
    """
    if not ytdlp_path.is_file():
        return []

    args: list[str] = [
        str(ytdlp_path),
        "--extractor-args", "youtube:player_client=visionos,android,mweb",
        "--dump-json",
        "--no-warnings",
        "--no-progress",
        "--skip-download",
        url,
    ]
    kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

    proc = subprocess.Popen(args, **kwargs)  # noqa: S603
    try:
        stdout, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate(timeout=2)
        return []
    except Exception:
        return []

    if proc.returncode != 0 or not stdout:
        return []

    first_line = stdout.splitlines()[0].strip() if stdout else ""
    if not first_line.startswith("{"):
        return []

    try:
        data = json.loads(first_line)
    except json.JSONDecodeError:
        return []

    formats = data.get("formats", [])
    heights = set()
    
    for f in formats:
        h = f.get("height")
        vcodec = f.get("vcodec", "")
        # Ensure it has video and is not a dummy/images codec
        if h and isinstance(h, int) and h > 0 and vcodec and vcodec != "none" and vcodec != "images":
            heights.add(h)

    sorted_heights = sorted(list(heights), reverse=True)
    
    results = []
    for h in sorted_heights:
        if h >= 4320:
            results.append(f"8K ({h}p)")
        elif h >= 2160:
            results.append(f"4K ({h}p)")
        elif h >= 1440:
            results.append(f"2K ({h}p)")
        else:
            results.append(f"{h}p")
            
    return results
