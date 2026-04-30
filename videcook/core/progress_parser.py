"""Parse yt-dlp ``--newline`` stdout/stderr into structured progress events.

Stateless — each call to :func:`parse_progress_line` is independent.
"""

import re
from typing import Any

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_DOWNLOAD_DONE_RE = re.compile(
    r"\[download\]\s+100%"
)

_DOWNLOAD_PROGRESS_RE = re.compile(
    r"\[download\]\s+(?P<percent>[0-9.]+)%\s+of\s+~?\s*(?P<total>\S+)\s*"
    r"(?:at\s+(?P<speed>\S+)\s+ETA\s+(?P<eta>[\d:]+))?"
)

_DESTINATION_RE = re.compile(
    r"\[download\]\s+Destination:"
)

_POSTPROCESS_RE = re.compile(
    r"\[(?![Dd]ownload)(?P<stage>[A-Za-z]+)\]\s+"
)

_EXTRACT_RE = re.compile(
    r"\[(?P<stage>Extract\w*)\]\s+"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_progress_line(line: str) -> dict[str, Any]:
    """Parse one line of yt-dlp ``--newline`` output into a structured dict.

    Returns a dict with at least a ``"type"`` key and the original ``"raw"``
    line.  Unrecognized lines return ``{"type": "log", "raw": line}``.
    """
    stripped = line.strip()
    if not stripped:
        return {"type": "log", "raw": line}

    # --- destination (checked before progress to avoid false match) ---
    if _DESTINATION_RE.search(stripped):
        return {"type": "destination", "raw": line}

    # --- download completed (checked before progress — both start same) ---
    if _DOWNLOAD_DONE_RE.search(stripped):
        return {"type": "download_completed", "percent": 100.0, "raw": line}

    # --- download progress (e.g. "[download]  12.3% of 50.00MiB at ...") ---
    match = _DOWNLOAD_PROGRESS_RE.search(stripped)
    if match:
        result: dict[str, Any] = {
            "type": "download_progress",
            "percent": float(match.group("percent")),
            "raw": line,
        }
        speed = match.group("speed")
        eta = match.group("eta")
        if speed is not None:
            result["speed"] = speed
        if eta is not None:
            result["eta"] = eta
        return result

    # --- post-processing (e.g. "[Merger] Merging formats into ...") ---
    match = _POSTPROCESS_RE.match(stripped)
    if match:
        return {"type": "postprocess", "stage": match.group("stage").lower(), "raw": line}

    # --- extraction (e.g. "[ExtractAudio] ...") ---
    match = _EXTRACT_RE.match(stripped)
    if match:
        return {"type": "postprocess", "stage": match.group("stage").lower(), "raw": line}

    # --- everything else ---
    return {"type": "log", "raw": line}
