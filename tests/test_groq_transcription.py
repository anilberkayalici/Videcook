from pathlib import Path

from videcook.services.groq_transcription import GroqTranscriptionClient, parse_verbose_transcription


def test_verbose_groq_response_becomes_subtitle_segments() -> None:
    segments = parse_verbose_transcription(
        {
            "segments": [
                {"start": 0.25, "end": 1.75, "text": " Hello, world. "},
                {"start": 2.0, "end": 3.0, "text": "Second line."},
            ]
        }
    )

    assert [(segment.start, segment.end, segment.text) for segment in segments] == [
        (0.25, 1.75, "Hello, world."),
        (2.0, 3.0, "Second line."),
    ]


def test_client_uses_official_sdk_with_verbose_segment_timestamps() -> None:
    class FakeTranscriptions:
        def __init__(self) -> None:
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return {"segments": [{"start": 0, "end": 1, "text": "Hello."}]}

    class FakeClient:
        def __init__(self) -> None:
            self.audio = type("Audio", (), {"transcriptions": FakeTranscriptions()})()

    audio = Path(__file__)
    fake = FakeClient()

    segments = GroqTranscriptionClient("gsk_test", client=fake).transcribe(Path(audio))

    assert segments[0].text == "Hello."
    assert fake.audio.transcriptions.kwargs["model"] == "whisper-large-v3"
    assert fake.audio.transcriptions.kwargs["response_format"] == "verbose_json"
    assert fake.audio.transcriptions.kwargs["timestamp_granularities"] == ["segment", "word"]
