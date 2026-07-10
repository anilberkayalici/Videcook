"""Windows DPAPI storage for the user's Groq API key."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _path(create: bool = False) -> Path:
    root = Path(os.environ.get("APPDATA", Path.home())) / "Videcook"
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root / "groq_api_key.bin"


def _blob(data: bytes) -> tuple[_DataBlob, object]:
    buffer = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    return _DataBlob(len(data), buffer), buffer


def save_groq_api_key(api_key: str) -> None:
    """Encrypt and persist the key for the current Windows user only."""
    if os.name != "nt":
        raise RuntimeError("Güvenli anahtar deposu yalnızca Windows'ta destekleniyor.")
    value = api_key.strip().encode("utf-8")
    if not value:
        raise ValueError("API anahtarı boş olamaz.")
    source, _source_buffer = _blob(value)
    encrypted = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptProtectData(ctypes.byref(source), "Videcook Groq API key", None, None, None, 0, ctypes.byref(encrypted)):
        raise ctypes.WinError()
    try:
        _path(create=True).write_bytes(ctypes.string_at(encrypted.pbData, encrypted.cbData))
    finally:
        ctypes.windll.kernel32.LocalFree(encrypted.pbData)


def load_groq_api_key() -> str:
    """Return the current user's decrypted key, or an empty string when unset."""
    path = _path()
    if not path.is_file():
        return ""
    encrypted, _encrypted_buffer = _blob(path.read_bytes())
    decrypted = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptUnprotectData(ctypes.byref(encrypted), None, None, None, None, 0, ctypes.byref(decrypted)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(decrypted.pbData, decrypted.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(decrypted.pbData)


def remove_groq_api_key() -> None:
    """Remove the encrypted local key, if it exists."""
    _path().unlink(missing_ok=True)
