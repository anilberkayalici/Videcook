"""Preset manager for AI Edit custom prompt templates."""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_PRESETS: list[dict[str, str]] = [
    {
        "name": "⚡ En Aksiyonlu Sahne",
        "prompt": "Videonun en heyecanlı ve yüksek tempolu aksiyon sahnesini kes.",
    },
    {
        "name": "😂 En Komik Diyalog",
        "prompt": "Videonun en komik ve esprili konuşma sahnesini dikey kes.",
    },
    {
        "name": "🎸 Metal Family",
        "prompt": "Metal Family karakter diyaloglarının en eğlenceli ve komik anını kes. Karakter repliklerini ön plana çıkar, arka plan müziği ekleme.",
    },
    {
        "name": "🎭 Dramatik Sahne",
        "prompt": "Duygusal ve dramatik açıdan en etkileyici diyalog sahnesini çıkar.",
    },
    {
        "name": "🎣 Merak Uyandıran Kanca",
        "prompt": "Videonun en çok merak uyandıran cümlesini başa kanca (hook) yap.",
    },
]


def get_presets_file_path() -> Path:
    """Return path to edit_presets.json config file."""
    home_dir = Path.home() / ".videcook"
    home_dir.mkdir(parents=True, exist_ok=True)
    return home_dir / "edit_presets.json"


def get_edit_presets() -> list[dict[str, str]]:
    """Load presets from disk or return default presets."""
    preset_file = get_presets_file_path()
    if not preset_file.is_file():
        save_edit_presets(DEFAULT_PRESETS)
        return list(DEFAULT_PRESETS)

    try:
        data = json.loads(preset_file.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            valid = []
            for item in data:
                if isinstance(item, dict) and "name" in item and "prompt" in item:
                    valid.append({"name": str(item["name"]), "prompt": str(item["prompt"])})
            if valid:
                return valid
    except Exception:
        pass

    return list(DEFAULT_PRESETS)


def save_edit_presets(presets: list[dict[str, str]]) -> bool:
    """Save presets list to disk."""
    try:
        preset_file = get_presets_file_path()
        preset_file.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def add_edit_preset(name: str, prompt: str) -> bool:
    """Add a new preset to the list and save."""
    name = name.strip()
    prompt = prompt.strip()
    if not name or not prompt:
        return False

    presets = get_edit_presets()
    presets.append({"name": name, "prompt": prompt})
    return save_edit_presets(presets)


def delete_edit_preset(index: int) -> bool:
    """Delete a preset by index."""
    presets = get_edit_presets()
    if 0 <= index < len(presets):
        presets.pop(index)
        return save_edit_presets(presets)
    return False


def move_edit_preset(from_index: int, to_index: int) -> bool:
    """Move a preset from one position to another."""
    presets = get_edit_presets()
    if 0 <= from_index < len(presets) and 0 <= to_index < len(presets):
        item = presets.pop(from_index)
        presets.insert(to_index, item)
        return save_edit_presets(presets)
    return False
