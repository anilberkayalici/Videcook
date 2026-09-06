"""Cross-platform secure storage for the user's Groq API key.

Windows: DPAPI (CryptProtectData / CryptUnprotectData)
Linux:   file permissions (chmod 600) + restricted directory
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from videcook.paths import get_user_data_dir


def _store_dir() -> Path:
    path = get_user_data_dir() / "secure"
    if os.name != "nt":
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _key_path() -> Path:
    return _store_dir() / "groq_api_key.bin"


def save_groq_api_key(api_key: str) -> None:
    """Persist the key using platform-appropriate protection."""
    value = api_key.strip()
    if not value:
        raise ValueError("API key must not be empty.")

    if os.name == "nt":
        _save_windows(value)
    else:
        _save_linux(value)


def load_groq_api_key() -> str:
    """Return the current user's key, or an empty string when unset."""
    path = _key_path()
    if not path.is_file():
        return ""

    if os.name == "nt":
        return _load_windows(path)
    return _load_linux(path)


def remove_groq_api_key() -> None:
    """Remove the encrypted local key, if it exists."""
    _key_path().unlink(missing_ok=True)


# ------------------------------------------------------------------
# Windows DPAPI
# ------------------------------------------------------------------

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    class _DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    def _blob(data: bytes) -> tuple[_DataBlob, object]:
        buffer = (ctypes.c_byte * len(data)).from_buffer_copy(data)
        return _DataBlob(len(data), buffer), buffer

    def _save_windows(value: str) -> None:
        source, _source_buffer = _blob(value.encode("utf-8"))
        encrypted = _DataBlob()
        crypt32 = ctypes.windll.crypt32
        if not crypt32.CryptProtectData(
            ctypes.byref(source), "Videcook Groq API key",
            None, None, None, 0, ctypes.byref(encrypted),
        ):
            raise ctypes.WinError()
        try:
            _key_path().write_bytes(ctypes.string_at(encrypted.pbData, encrypted.cbData))
        finally:
            ctypes.windll.kernel32.LocalFree(encrypted.pbData)

    def _load_windows(path: Path) -> str:
        encrypted, _encrypted_buffer = _blob(path.read_bytes())
        decrypted = _DataBlob()
        crypt32 = ctypes.windll.crypt32
        if not crypt32.CryptUnprotectData(
            ctypes.byref(encrypted), None, None, None, None, 0, ctypes.byref(decrypted),
        ):
            raise ctypes.WinError()
        try:
            return ctypes.string_at(decrypted.pbData, decrypted.cbData).decode("utf-8")
        finally:
            ctypes.windll.kernel32.LocalFree(decrypted.pbData)

else:
    # Linux stubs – the real implementations are below
    pass


# ------------------------------------------------------------------
# Linux chmod 600
# ------------------------------------------------------------------

import base64


def _save_linux(value: str) -> None:
    encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
    path = _key_path()
    path.write_text(encoded, encoding="ascii")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def _load_linux(path: Path) -> str:
    encoded = path.read_text(encoding="ascii")
    return base64.b64decode(encoded.encode("ascii")).decode("utf-8")
