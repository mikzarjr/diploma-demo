import logging
import os
from io import BytesIO
from pathlib import Path

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

MODEL_DIR = Path(os.getenv("ASR_MODEL_DIR", "/app/models/t-one")).resolve()
TARGET_SR = 8000

T_ONE_PEAK_DBFS = float(os.getenv("T_ONE_PEAK_DBFS", "-3.0"))
T_ONE_HIGHPASS_HZ = float(os.getenv("T_ONE_HIGHPASS_HZ", "80"))

_pipe = None
_load_error: Exception | None = None


def _get_pipe():
    global _pipe, _load_error
    if _pipe is not None:
        return _pipe
    if _load_error is not None:
        raise RuntimeError(f"T-one previously failed to load: {_load_error}")

    try:
        from tone import StreamingCTCPipeline

        logger.info("loading T-one pipeline from %s", MODEL_DIR)
        _pipe = StreamingCTCPipeline.from_local(str(MODEL_DIR))
        logger.info("T-one pipeline ready (vanilla defaults)")
        return _pipe
    except Exception as exc:
        _load_error = exc
        logger.exception("T-one pipeline failed to load")
        raise RuntimeError(f"T-one load failed: {exc}") from exc


def _decode(result) -> str:
    items = result if isinstance(result, list) else [result]
    extracted: list[tuple[float, str]] = []
    for item in items:
        if isinstance(item, str):
            t = item.strip()
            start = 0.0
        elif isinstance(item, dict):
            t = (item.get("text") or "").strip()
            start = float(item.get("start_time") or item.get("start") or 0.0)
        else:
            t = (getattr(item, "text", "") or "").strip()
            start = float(getattr(item, "start_time", 0.0) or 0.0)
        if t:
            extracted.append((start, t))
    extracted.sort(key=lambda x: x[0])
    return " ".join(t for _, t in extracted).strip()


def _normalize_audio(audio_int16: np.ndarray) -> np.ndarray:
    audio_f = audio_int16.astype(np.float32) / 32768.0

    if T_ONE_HIGHPASS_HZ > 0:
        try:
            from scipy.signal import butter, sosfilt
            sos = butter(4, T_ONE_HIGHPASS_HZ, "high", fs=TARGET_SR, output="sos")
            audio_f = sosfilt(sos, audio_f).astype(np.float32)
        except Exception:
            logger.exception("highpass filter failed, skip")

    peak = float(np.abs(audio_f).max())
    if peak > 0:
        target_peak = 10 ** (T_ONE_PEAK_DBFS / 20)
        gain = target_peak / peak
        audio_f = audio_f * gain
        logger.info(
            "audio normalized: peak=%.4f → gain=%.2f (target %.1f dBFS)",
            peak, gain, T_ONE_PEAK_DBFS,
        )

    return np.clip(audio_f * 32768.0, -32768.0, 32767.0).astype(np.int16)


def _load_pcm(audio_bytes: bytes) -> np.ndarray:
    audio, sr = sf.read(BytesIO(audio_bytes), dtype="int16")
    if audio.ndim > 1:
        audio = audio.mean(axis=1).astype(np.int16)
    if sr != TARGET_SR:
        import librosa

        audio_f = librosa.resample(
            audio.astype(np.float32) / 32768.0,
            orig_sr=sr,
            target_sr=TARGET_SR,
        )
        audio = np.clip(audio_f * 32768.0, -32768.0, 32767.0).astype(np.int16)
    audio = _normalize_audio(audio)
    return np.ascontiguousarray(audio.astype(np.int32))


def transcribe_wav(audio_bytes: bytes) -> str:
    audio = _load_pcm(audio_bytes)
    if audio.size < int(0.1 * TARGET_SR):
        return ""
    pipe = _get_pipe()
    try:
        result = pipe.forward_offline(audio)
    except AttributeError:
        result = pipe.forward(audio)
    text = _decode(result)
    logger.info(
        "ASR slice: dur=%.2fs raw_result=%r decoded=%r",
        audio.size / TARGET_SR,
        result,
        text,
    )
    return text
