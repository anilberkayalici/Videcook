"""Unit tests for the Dubbing / Translation File Parser (translation_file_parser.py)."""

from pathlib import Path
from videcook.core.translation_file_parser import (
    parse_timestamp_to_seconds,
    clean_dialogue_line,
    parse_translation_content,
    parse_translation_file,
)


def test_parse_timestamp_to_seconds():
    assert parse_timestamp_to_seconds("00.31") == 31.0
    assert parse_timestamp_to_seconds("01.35") == 95.0
    assert parse_timestamp_to_seconds("04:59.50") == 299.5
    assert parse_timestamp_to_seconds("01:02:03.500") == 3723.5


def test_clean_dialogue_line():
    assert clean_dialogue_line("(Karakter İsmi) - Hello there!") == "Hello there!"
    assert clean_dialogue_line("(Glam) - Bugün sınav olduğuna emin misin?") == "Bugün sınav olduğuna emin misin?"
    assert clean_dialogue_line("Dee: Yapabileceğiniz en uzun piercing hangisi?") == "Yapabileceğiniz en uzun piercing hangisi?"
    assert clean_dialogue_line("| Dee | Benim hatam. |") == "Benim hatam."
    assert clean_dialogue_line(r"\- (nara) Titanyum?") == "Titanyum?"
    assert clean_dialogue_line(r"\- Bunlar benim ilk") == "Bunlar benim ilk"
    assert clean_dialogue_line(r"04.59 - (Dee) - (nara atar) Titanyum?") == "Titanyum?"


def test_parse_translation_content_markdown_table():
    md = """
# Çeviri Tablosu
| Süre | Karakter | Replik |
| :--- | :--- | :--- |
| 00:31 | Glam | Bugün sınav olduğuna emin misin? |
| 00:36 | Dee | Kahretsin, ikinci derste mi gerçekten? |
| 04:59 | Dee | En uzun piercing hangisi? |
"""
    segs = parse_translation_content(md, file_ext=".md")
    assert len(segs) == 3
    assert segs[0].start == 31.0
    assert segs[0].text == "Bugün sınav olduğuna emin misin?"
    assert segs[1].start == 36.0
    assert segs[1].text == "Kahretsin, ikinci derste mi gerçekten?"
    assert segs[2].start == 299.0
    assert segs[2].text == "En uzun piercing hangisi?"


def test_parse_translation_content_gecekondu_formatted_text():
    txt = """
00.31 - (Karakter İsmi) - Are you sure the test is today?

00.36 - (Karakter İsmi) - Damn, in the second period, really?

00.41 - (Karakter İsmi) - Prepared?
"""
    segs = parse_translation_content(txt, file_ext=".txt")
    assert len(segs) == 3
    assert segs[0].start == 31.0
    assert segs[0].text == "Are you sure the test is today?"
    assert segs[1].start == 36.0
    assert segs[1].text == "Damn, in the second period, really?"
    assert segs[2].start == 41.0
    assert segs[2].text == "Prepared?"


def test_parse_translation_file_non_existent(tmp_path: Path):
    missing = tmp_path / "missing.md"
    assert parse_translation_file(missing) == []


def test_detect_music_category_from_prompt():
    from videcook.core.bg_music import detect_music_category_from_prompt
    # Negative music intent should strictly return None
    assert detect_music_category_from_prompt("müzik koyma, sadece altyazı olsun") is None
    assert detect_music_category_from_prompt("arkaya müzik ekleme") is None
    assert detect_music_category_from_prompt("müziksiz olsun") is None
    assert detect_music_category_from_prompt("fon müziği olmasın") is None
    assert detect_music_category_from_prompt("no music please") is None

    # Normal prompts without music request should return None
    assert detect_music_category_from_prompt("Glam'in güldüğü yeri kes") is None

    # Explicit positive music intent
    assert detect_music_category_from_prompt("arkaya gaza getirici phonk müzik ekle") == "phonk"
    assert detect_music_category_from_prompt("duygusal anime fon müziği koy") == "sad_anime"
    assert detect_music_category_from_prompt("arkaya komik müzik koy") == "funny_comedy"
