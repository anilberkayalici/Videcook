from videcook.services.subtitle_pipeline import build_chunk_windows


def test_twenty_minute_audio_is_split_with_one_second_overlap() -> None:
    windows = build_chunk_windows(1200.0, chunk_seconds=600.0, overlap_seconds=1.0)

    assert [(window.start, window.end) for window in windows] == [
        (0.0, 600.0),
        (599.0, 1200.0),
    ]
