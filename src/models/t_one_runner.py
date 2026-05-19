from tone import StreamingCTCPipeline, read_audio

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = StreamingCTCPipeline.from_hugging_face()
    return _pipeline


def transcribe_t_one(audio_path: str) -> str:
    pipeline = _get_pipeline()
    audio = read_audio(audio_path)
    phrases = pipeline.forward_offline(audio)
    return " ".join(p.text for p in phrases if p.text).strip()
