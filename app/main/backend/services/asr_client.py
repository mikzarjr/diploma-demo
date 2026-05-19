import logging
import os
from io import BytesIO

import httpx
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

ASR_URL = os.getenv("ASR_SERVICE_URL", "http://asr:7002").rstrip("/")
ASR_TIMEOUT = float(os.getenv("ASR_TIMEOUT", "600"))


def _to_wav_bytes(audio: np.ndarray, sr: int) -> bytes:
    if audio.dtype != np.int16:
        audio_f = audio.astype(np.float32, copy=False)
        audio = np.clip(audio_f * 32768.0, -32768.0, 32767.0).astype(np.int16)
    buf = BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def transcribe_slice(audio: np.ndarray, sr: int) -> str:
    if audio.size < int(0.1 * sr):
        return ""
    audio = np.ascontiguousarray(audio, dtype=np.float32)
    wav_bytes = _to_wav_bytes(audio, sr)
    url = f"{ASR_URL}/transcribe"
    try:
        resp = httpx.post(
            url,
            content=wav_bytes,
            headers={"Content-Type": "application/octet-stream"},
            timeout=ASR_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("ASR request to %s failed: %s", url, exc)
        return ""
    try:
        data = resp.json()
    except ValueError:
        logger.error("ASR returned non-JSON: %r", resp.text[:200])
        return ""
    return (data.get("text") or "").strip()
