"""Tests for videcook.core.subtitle_formatter — matches the TypeScript
Çeviri-Uygulaması fixture tests exactly.
"""

from videcook.core.subtitle_formatter import (
    convert_srt,
    build_export_filename,
    parse_srt,
    normalize_cues,
    format_subtitles,
    stringify_formatted_lines,
)


# ---------------------------------------------------------------------------
# Fixtures — copied directly from the TS test fixtures
# ---------------------------------------------------------------------------

FIXTURE_NORMAL_DIALOGUE_SRT = """\
1
00:00:05,400 --> 00:00:07,900
Merhaba dünya.

2
00:00:09,050 --> 00:00:11,100
Nasılsın?
"""

FIXTURE_NORMAL_DIALOGUE_TXT = """\
00.05 - (Karakter İsmi) - Merhaba dünya.

00.09 - (Karakter İsmi) - Nasılsın?"""

FIXTURE_MULTI_SPEAKER_SRT = """\
1
00:02:04,050 --> 00:02:06,100
Ayşe + Mehmet: Hazır mısınız?
"""

FIXTURE_MULTI_SPEAKER_TXT = """\
02.04 - (Ayşe + Mehmet) - Hazır mısınız?"""

FIXTURE_UNICODE_TURKISH_SRT = """\
1
00:00:10,000 --> 00:00:12,000
ğ Ğ ü Ü ş Ş ı İ ö Ö ç Ç
"""

FIXTURE_UNICODE_TURKISH_TXT = """\
00.10 - (Karakter İsmi) - Ğ Ğ ü Ü ş Ş ı İ ö Ö ç Ç"""

FIXTURE_MALFORMED_SRT = """\
1
00:00:01,000 --> 00:00:02,000
Sağlam satır.

2
00:00:aa,000 --> 00:00:05,000
Bozuk zaman.

3
00:00:06,000 --> 00:00:07,000
İkinci sağlam satır.
"""

FIXTURE_MALFORMED_TXT = """\
00.01 - (Karakter İsmi) - Sağlam satır.

00.06 - (Karakter İsmi) - İkinci sağlam satır."""

FIXTURE_SEQUENCE_GAP_SRT = """\
1
00:00:17,792 --> 00:00:20,041
Flamme.

2
00:01:00,333 --> 00:01:02,999
adımı diledikleri gibi kötüye çıkarabilirler.

3
00:02:34,458 --> 00:02:37,458
Kanamayı durduramıyorum.

4
00:19:10,000 --> 00:19:12,500
Son saldırıya hazırlan.

5
00:20:45,000 --> 00:20:48,000
Yolun sonu geldi.
"""

FIXTURE_SEQUENCE_GAP_TXT = """\
00.17 - (Karakter İsmi) - Flamme.

01.00 - (Karakter İsmi) - Adımı diledikleri gibi kötüye çıkarabilirler.


01.00 - 02.34 - Opening


02.34 - (Karakter İsmi) - Kanamayı durduramıyorum.

19.10 - (Karakter İsmi) - Son saldırıya hazırlan.


19.10 - 20.45 - Ending


20.45 - (Karakter İsmi) - Yolun sonu geldi."""

FIXTURE_EFFECT_LINES_SRT = """\
1
00:00:12,000 --> 00:00:13,900
Ayşe: (nefes narası)

2
00:04:10,000 --> 00:04:16,200
Ayşe: (naralar)
"""

FIXTURE_EFFECT_LINES_TXT = """\
00.12 - (Ayşe) - (nefes narası)

04.10 - (Ayşe) - (naralar)"""

FIXTURE_OVERLAP_SRT = """\
1
00:00:20,100 --> 00:00:22,000
İlk satır.

2
00:00:20,100 --> 00:00:23,500
İkinci satır.

3
00:00:21,600 --> 00:00:25,000
Üçüncü satır.
"""

FIXTURE_OVERLAP_TXT = """\
00.20 - (Karakter İsmi) - İlk satır.

00.20 - (Karakter İsmi) - İkinci satır.

00.21 - (Karakter İsmi) - Üçüncü satır."""

FIXTURE_OPENING_ENDING_SRT = """\
1
00:01:30,000 --> 00:03:00,000
Opening

2
00:20:45,000 --> 00:22:15,000
Ending
"""

FIXTURE_OPENING_ENDING_TXT = """\
01.30 - 03.00 - Opening


20.45 - 22.15 - Ending"""


# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------


class TestParseSrt:
    def test_empty(self) -> None:
        result = parse_srt("")
        assert result.cues == []
        assert len(result.issues) == 1

    def test_single_cue(self) -> None:
        result = parse_srt(FIXTURE_NORMAL_DIALOGUE_SRT)
        assert len(result.cues) == 2
        assert result.cues[0].start_ms == 5_400
        assert result.cues[0].end_ms == 7_900
        assert result.cues[0].text_lines == ["Merhaba dünya."]

    def test_malformed_time_skipped(self) -> None:
        result = parse_srt(FIXTURE_MALFORMED_SRT)
        assert len(result.cues) == 2  # only valid blocks
        assert result.cues[0].text_lines == ["Sağlam satır."]
        assert result.cues[1].text_lines == ["İkinci sağlam satır."]
        # One parse issue for the bad block
        assert any(i.message.startswith("2.") for i in result.issues)

    def test_speaker_format(self) -> None:
        result = parse_srt(FIXTURE_MULTI_SPEAKER_SRT)
        assert len(result.cues) == 1

    def test_sequence_number_preserved(self) -> None:
        result = parse_srt(FIXTURE_NORMAL_DIALOGUE_SRT)
        assert result.cues[0].sequence == 1
        assert result.cues[1].sequence == 2


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------


class TestNormalizeCues:
    def test_speaker_extraction(self) -> None:
        parsed = parse_srt(FIXTURE_MULTI_SPEAKER_SRT)
        cues = normalize_cues(parsed.cues)
        assert cues[0].speakers == ["Ayşe", "Mehmet"]
        assert cues[0].text == "Hazır mısınız?"

    def test_effect_lines(self) -> None:
        parsed = parse_srt(FIXTURE_EFFECT_LINES_SRT)
        cues = normalize_cues(parsed.cues)
        assert cues[0].speakers == ["Ayşe"]
        assert cues[0].text == "(nefes narası)"

    def test_opening_marker_detected(self) -> None:
        parsed = parse_srt(FIXTURE_OPENING_ENDING_SRT)
        cues = normalize_cues(parsed.cues)
        assert cues[0].marker_hint == "opening"
        assert cues[1].marker_hint == "ending"


# ---------------------------------------------------------------------------
# Full pipeline tests (matches expected output)
# ---------------------------------------------------------------------------


class TestConvertSrt:
    def test_normal_dialogue(self) -> None:
        result = convert_srt(FIXTURE_NORMAL_DIALOGUE_SRT)
        assert result.output == FIXTURE_NORMAL_DIALOGUE_TXT

    def test_multi_speaker(self) -> None:
        result = convert_srt(FIXTURE_MULTI_SPEAKER_SRT)
        assert result.output == FIXTURE_MULTI_SPEAKER_TXT

    def test_unicode_turkish(self) -> None:
        result = convert_srt(FIXTURE_UNICODE_TURKISH_SRT)
        assert result.output == FIXTURE_UNICODE_TURKISH_TXT

    def test_malformed_recovery(self) -> None:
        result = convert_srt(FIXTURE_MALFORMED_SRT)
        assert result.output == FIXTURE_MALFORMED_TXT
        # Should have notices for the skipped block.
        assert len(result.notices) >= 1

    def test_sequence_gap_markers(self) -> None:
        result = convert_srt(FIXTURE_SEQUENCE_GAP_SRT)
        assert result.output == FIXTURE_SEQUENCE_GAP_TXT

    def test_effect_lines(self) -> None:
        result = convert_srt(FIXTURE_EFFECT_LINES_SRT)
        assert result.output == FIXTURE_EFFECT_LINES_TXT

    def test_overlap_repeated(self) -> None:
        result = convert_srt(FIXTURE_OVERLAP_SRT)
        assert result.output == FIXTURE_OVERLAP_TXT

    def test_opening_ending(self) -> None:
        result = convert_srt(FIXTURE_OPENING_ENDING_SRT)
        assert result.output == FIXTURE_OPENING_ENDING_TXT

    def test_empty_input_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            convert_srt("")


# ---------------------------------------------------------------------------
# Export filename
# ---------------------------------------------------------------------------


class TestBuildExportFilename:
    def test_basic(self) -> None:
        assert build_export_filename("subtitle.srt") == "subtitle_formatted.txt"

    def test_without_extension(self) -> None:
        assert build_export_filename("subtitle") == "subtitle_formatted.txt"

    def test_complex_name(self) -> None:
        assert (
            build_export_filename("My File.srt")
            == "My File_formatted.txt"
        )
