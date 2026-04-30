"""Input validators for Videcook download requests.

All functions raise :class:`ValidationError` (or a subclass) on failure.
"""

from pathlib import Path

from videcook.core.models import DownloadRequest


class ValidationError(ValueError):
    """Base validation error for Videcook."""


class InvalidUrlError(ValidationError):
    """The supplied URL is empty or has an unsupported scheme."""


class InvalidCookieFileError(ValidationError):
    """The cookie file path is missing, is a directory, or has a bad extension."""


class InvalidOutputFolderError(ValidationError):
    """The output folder is missing or is not a directory."""


def validate_url(url: str) -> None:
    """Check that *url* is a non-empty http/https URL."""
    if not url or not url.strip():
        raise InvalidUrlError("URL cannot be empty.")

    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise InvalidUrlError(f"URL must start with http:// or https://, got: {url!r}")


def validate_cookie_file(path: Path) -> None:
    """Check that *path* points to an existing file.

    **The file contents are never read.** Only the existence and type are checked.
    """
    if not path.exists():
        raise InvalidCookieFileError(f"Cookie file not found: {path}")

    if path.is_dir():
        raise InvalidCookieFileError(f"Cookie path is a directory, not a file: {path}")

    if path.suffix.lower() != ".txt":
        raise InvalidCookieFileError(
            f"Cookie file should have a .txt extension, got: {path.suffix!r}"
        )


def validate_output_folder(path: Path) -> None:
    """Check that *path* is an existing directory."""
    if not path.exists():
        raise InvalidOutputFolderError(f"Output folder does not exist: {path}")

    if not path.is_dir():
        raise InvalidOutputFolderError(f"Output path is not a directory: {path}")


def validate_download_request(request: DownloadRequest) -> None:
    """Run all validation checks on *request*."""
    validate_url(request.url)
    validate_cookie_file(request.cookie_file)
    validate_output_folder(request.output_folder)
