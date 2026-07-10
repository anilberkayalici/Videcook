from videcook.core.subtitles import SubtitleSegment, merge_chunk_segments, render_srt


def test_render_srt_uses_standard_timestamps() -> None:
    output = render_srt([SubtitleSegment(start=1.25, end=3.5, text="Hello there")])

    assert output == "1\n00:00:01,250 --> 00:00:03,500\nHello there\n"


def test_merge_chunk_segments_removes_overlap_duplicate() -> None:
    segments = merge_chunk_segments(
        [
            SubtitleSegment(start=0.0, end=2.0, text="Welcome back."),
            SubtitleSegment(start=2.1, end=4.0, text="Today we begin."),
        ],
        [
            SubtitleSegment(start=1.0, end=3.0, text="Today we begin."),
            SubtitleSegment(start=3.1, end=5.0, text="With the next lesson."),
        ],
    )

    assert [segment.text for segment in segments] == [
        "Welcome back.",
        "Today we begin.",
        "With the next lesson.",
    ]
