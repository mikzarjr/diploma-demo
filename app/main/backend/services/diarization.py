import logging
import shutil
import subprocess
import tempfile
import warnings
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Literal

import librosa
import numpy as np
import soundfile as sf
import torch
from core.config import settings

warnings.filterwarnings(
    "ignore",
    message=".*torchcodec is not installed correctly.*",
)

from pyannote.audio import Pipeline

logger = logging.getLogger(__name__)

DIARIZATION_DIR = Path(settings.DIARIZATION_MODEL_DIR).resolve()
DIARIZATION_CONFIG = DIARIZATION_DIR / "config.yaml"

device = "cuda" if torch.cuda.is_available() else "cpu"
TARGET_SR = 16000

_diar_pipeline: Pipeline | None = None


@dataclass
class Segment:
    speaker: str
    text: str
    t_start: float
    t_end: float


@dataclass
class DiarizationResult:
    segments: list[Segment]
    mode: Literal["stereo", "mono"]
    n_channels: int
    speaker_labels: list[str] = field(default_factory=list)


_ASR_MAX_SEGMENT_SEC = 25.0


def _asr_transcribe_slice(audio_slice: np.ndarray, sr: int) -> str:
    from services.asr_client import transcribe_slice as _remote_transcribe

    if len(audio_slice) < int(0.1 * sr):
        return ""
    max_samples = int(_ASR_MAX_SEGMENT_SEC * sr)
    if len(audio_slice) <= max_samples:
        return _remote_transcribe(audio_slice, sr)
    parts: list[str] = []
    step = max_samples
    overlap = int(0.5 * sr)
    i = 0
    while i < len(audio_slice):
        end = min(i + step, len(audio_slice))
        chunk = audio_slice[i:end]
        text = _remote_transcribe(chunk, sr)
        if text:
            parts.append(text)
        if end == len(audio_slice):
            break
        i = end - overlap
    return " ".join(parts).strip()


def _get_diar_pipeline() -> Pipeline:
    global _diar_pipeline
    if _diar_pipeline is None:
        if not DIARIZATION_CONFIG.exists():
            raise FileNotFoundError(
                f"Diarization config missing: {DIARIZATION_CONFIG}. "
                "Run `python models/download_model.py` first."
            )
        logger.info("Loading pyannote diarization pipeline from %s", DIARIZATION_CONFIG)
        _diar_pipeline = Pipeline.from_pretrained(str(DIARIZATION_CONFIG))
        if device == "cuda":
            _diar_pipeline.to(torch.device("cuda"))
        logger.info("Pyannote diarization pipeline ready on %s", device)
    return _diar_pipeline


def _ffmpeg_to_wav(audio_bytes: bytes) -> bytes:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg binary not found in PATH")
    if not audio_bytes:
        raise ValueError("Audio payload is empty")
    with tempfile.NamedTemporaryFile(suffix=".bin") as in_f, \
            tempfile.NamedTemporaryFile(suffix=".wav") as out_f:
        in_f.write(audio_bytes)
        in_f.flush()
        proc = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
                "-i", in_f.name,
                "-vn",
                "-acodec", "pcm_s16le",
                "-f", "wav", out_f.name,
            ],
            capture_output=True,
            check=False,
        )
        stderr_tail = proc.stderr.decode(errors="replace")[-500:]
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg decode failed (rc={proc.returncode}): {stderr_tail}")
        out_f.seek(0)
        wav = out_f.read()
    if len(wav) < 64:
        raise RuntimeError(f"ffmpeg produced empty WAV ({len(wav)} bytes). stderr: {stderr_tail}")
    logger.debug("ffmpeg decoded %d bytes → %d wav bytes", len(audio_bytes), len(wav))
    return wav


def _load_audio(audio_bytes: bytes) -> tuple[np.ndarray, int, int]:
    if not audio_bytes:
        raise ValueError("Empty audio bytes")
    try:
        data, sr = sf.read(BytesIO(audio_bytes), dtype="float32", always_2d=True)
        if data.shape[0] == 0:
            raise sf.LibsndfileError(0, prefix="zero-length PCM payload: ")
    except sf.LibsndfileError:
        logger.info("soundfile decode failed; transcoding via ffmpeg (input=%d bytes)", len(audio_bytes))
        wav_bytes = _ffmpeg_to_wav(audio_bytes)
        data, sr = sf.read(BytesIO(wav_bytes), dtype="float32", always_2d=True)
    if data.shape[0] == 0:
        raise ValueError(
            f"Decoded audio has 0 samples (input {len(audio_bytes)} bytes, sr={sr}). "
            "File is silent / corrupted / no audio stream."
        )

    data = data.T
    n_channels = data.shape[0]
    if sr != TARGET_SR:
        resampled = np.stack([
            librosa.resample(data[c], orig_sr=sr, target_sr=TARGET_SR)
            for c in range(n_channels)
        ])
        data = resampled
        sr = TARGET_SR
    if n_channels == 1:
        return data[0], sr, 1
    return data, sr, n_channels


def _diarize_stereo_telephony(stereo: np.ndarray, sr: int) -> list[tuple[float, float, str]]:
    turns: list[tuple[float, float, str]] = []
    frame_ms = 30
    hop = int(sr * frame_ms / 1000)
    energy_threshold = 0.005  # RMS

    for ch_idx in range(stereo.shape[0]):
        ch = stereo[ch_idx]
        n_frames = (len(ch) - hop) // hop
        if n_frames <= 0:
            continue
        rms = np.sqrt(
            np.mean(
                ch[: n_frames * hop].reshape(n_frames, hop) ** 2, axis=1
            ) + 1e-10
        )
        active = rms > energy_threshold

        i = 0
        while i < n_frames:
            if not active[i]:
                i += 1
                continue
            j = i
            while j < n_frames and active[j]:
                j += 1
            t_start = i * hop / sr
            t_end = j * hop / sr
            if t_end - t_start >= 0.3:  # ignore <300ms blips
                turns.append((t_start, t_end, f"CHANNEL_{ch_idx}"))
            i = j

    turns.sort(key=lambda t: t[0])
    return turns


def transcribe_and_diarize(
        audio_bytes: bytes,
        num_speakers: int | None = None,
        min_speakers: int = 2,
        max_speakers: int = 4,
        force_mono: bool = False,
) -> DiarizationResult:
    audio, sr, n_channels = _load_audio(audio_bytes)
    if n_channels == 1:
        waveform_np = audio
    else:
        waveform_np = audio.mean(axis=0)
    total_duration = len(waveform_np) / sr
    logger.info(
        "Audio: %.1fs, sr=%d, channels=%d, samples=%d, force_mono=%s",
        total_duration, sr, n_channels, len(waveform_np), force_mono,
    )

    if force_mono and n_channels >= 2:
        logger.info("force_mono=True → downmixing %d-channel audio", n_channels)
        n_channels = 1

    mode: Literal["stereo", "mono"]
    if n_channels >= 2:
        mode = "stereo"
        turns = _diarize_stereo_telephony(audio, sr)
        logger.info(
            "Stereo telephony diarization: %d turns, channels: %s",
            len(turns), sorted({t[2] for t in turns}),
        )
    else:
        mode = "mono"
        diar = _get_diar_pipeline()
        diar_kwargs: dict = {}
        if num_speakers is not None:
            diar_kwargs["num_speakers"] = num_speakers
        else:
            diar_kwargs["min_speakers"] = min_speakers
            diar_kwargs["max_speakers"] = max_speakers
        waveform_t = torch.from_numpy(waveform_np).unsqueeze(0)
        diar_output = diar({"waveform": waveform_t, "sample_rate": sr}, **diar_kwargs)

        # community-1 returns DiarizeOutput; older versions returned Annotation.
        annotation = getattr(diar_output, "exclusive_diarization", None)
        if annotation is None:
            annotation = getattr(diar_output, "speaker_diarization", diar_output)

        turns = [
            (turn.start, turn.end, speaker)
            for turn, _, speaker in annotation.itertracks(yield_label=True)
        ]
        logger.info(
            "Pyannote diarization: %d turns, speakers: %s, kwargs=%s",
            len(turns), sorted({t[2] for t in turns}), diar_kwargs,
        )

    for t_start_log, t_end_log, spk_log in turns:
        logger.info(
            "DIAR_TURN_PRE speaker=%s start=%.2f end=%.2f dur=%.2f",
            spk_log, t_start_log, t_end_log, t_end_log - t_start_log,
        )

    if not turns:
        logger.warning("No diarization turns — full-audio ASR fallback")
        full_text = _asr_transcribe_slice(waveform_np, sr)
        speaker = "CHANNEL_0" if mode == "stereo" else "SPEAKER_0"
        segments = (
            [Segment(speaker, full_text, 0.0, total_duration)] if full_text else []
        )
        return DiarizationResult(
            segments=segments,
            mode=mode,
            n_channels=n_channels,
            speaker_labels=[speaker] if full_text else [],
        )

    segments: list[Segment] = []
    for t_start, t_end, speaker in turns:
        if t_end <= t_start:
            continue
        if mode == "stereo":
            ch_idx = 0 if speaker.endswith("0") else 1
            ch_idx = min(ch_idx, audio.shape[0] - 1)
            source = audio[ch_idx]
        else:
            source = waveform_np
        i0 = max(0, int(t_start * sr))
        i1 = min(len(source), int(t_end * sr))
        if i1 - i0 < int(0.1 * sr):
            continue
        text = _asr_transcribe_slice(source[i0:i1], sr)
        logger.info(
            "DIAR_TURN speaker=%s [%.2f-%.2f] text=%r",
            speaker, t_start, t_end, text,
        )
        if not text:
            continue
        segments.append(Segment(speaker, text, t_start, t_end))

    if not segments:
        return DiarizationResult(
            segments=[], mode=mode, n_channels=n_channels, speaker_labels=[],
        )

    if mode == "mono":
        segments = _normalize_speakers(segments)
    segments = _merge_consecutive(segments)

    speaker_labels = sorted({s.speaker for s in segments})
    logger.info(
        "Final: %d segments, mode=%s, speakers: %s",
        len(segments), mode, speaker_labels,
    )
    return DiarizationResult(
        segments=segments,
        mode=mode,
        n_channels=n_channels,
        speaker_labels=speaker_labels,
    )


def _normalize_speakers(segments: list[Segment]) -> list[Segment]:
    mapping: dict[str, str] = {}
    for seg in segments:
        if seg.speaker not in mapping:
            mapping[seg.speaker] = f"SPEAKER_{len(mapping)}"
    for seg in segments:
        seg.speaker = mapping[seg.speaker]
    return segments


def _merge_consecutive(segments: list[Segment]) -> list[Segment]:
    if not segments:
        return segments
    merged = [Segment(
        speaker=segments[0].speaker,
        text=segments[0].text,
        t_start=segments[0].t_start,
        t_end=segments[0].t_end,
    )]
    for seg in segments[1:]:
        if seg.speaker == merged[-1].speaker:
            merged[-1].text += " " + seg.text
            merged[-1].t_end = seg.t_end
        else:
            merged.append(Segment(
                speaker=seg.speaker,
                text=seg.text,
                t_start=seg.t_start,
                t_end=seg.t_end,
            ))
    return merged
