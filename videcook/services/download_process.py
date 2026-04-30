"""Download process — safe subprocess execution for yt-dlp.

Public API design:
  :func:`stream_lines` consumes an iterable of output lines (real subprocess
  stdout *or* a fake iterable for tests) and calls a callback for each line.
  Cancellation is supported via an optional polling function.

The caller is responsible for creating the subprocess via :func:`Popen`.
This separation keeps the module testable without real binaries.
"""

import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass
class DownloadProcessResult:
    """Outcome of a download attempt."""

    success: bool
    return_code: int | None
    cancelled: bool
    message: str


def create_process(args: list[str]) -> subprocess.Popen:
    """Launch a subprocess with the given *args*.

    - ``shell=False`` (hard-coded).
    - stdout is piped; stderr is merged into stdout.
    - Text mode with UTF-8 encoding.
    """
    return subprocess.Popen(  # noqa: S603  — args list, not shell string
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def stream_lines(
    lines: Iterable[str],
    on_line: Callable[[str], None],
    check_cancelled: Callable[[], bool] | None = None,
) -> None:
    """Iterate *lines*, calling ``on_line(line)`` for each stripped entry.

    If *check_cancelled* is provided and returns ``True``, the iteration
    stops immediately.  The function itself does **not** terminate the
    underlying subprocess — that is the caller's responsibility.
    """
    for line in lines:
        line = line.rstrip("\n\r")
        if check_cancelled and check_cancelled():
            break
        on_line(line)


def wait_process(
    process: subprocess.Popen,
    cancelled: bool = False,
) -> DownloadProcessResult:
    """Wait for *process* to exit and build a :class:`DownloadProcessResult`."""
    rc = process.wait(timeout=30)
    if cancelled:
        return DownloadProcessResult(
            success=False, return_code=rc, cancelled=True, message="Cancelled by user."
        )
    if rc == 0:
        return DownloadProcessResult(
            success=True, return_code=rc, cancelled=False, message="Download completed."
        )
    return DownloadProcessResult(
        success=False,
        return_code=rc,
        cancelled=False,
        message=f"Download failed (exit code {rc}).",
    )
