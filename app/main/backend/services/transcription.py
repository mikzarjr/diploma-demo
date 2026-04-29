from services.diarization import DiarizationResult, Segment, transcribe_and_diarize


def transcribe_audio(audio_bytes: bytes) -> str:
    result = transcribe_and_diarize(audio_bytes)
    return " ".join(seg.text for seg in result.segments)


def transcribe_with_diarization(audio_bytes: bytes) -> DiarizationResult:
    return transcribe_and_diarize(audio_bytes)
