import logging
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

# Suppress torchcodec warning: we always pass pre-decoded waveform tensors,
# never let pyannote decode audio files itself.
warnings.filterwarnings(
    "ignore",
    message=".*torchcodec is not installed correctly.*",
)

from pyannote.audio import Pipeline  # noqa: E402
from transformers import pipeline as hf_pipeline  # noqa: E402

logger = logging.getLogger(__name__)

WHISPER_DIR = Path(settings.WHISPER_MODEL_DIR).resolve()
DIARIZATION_DIR = Path(settings.DIARIZATION_MODEL_DIR).resolve()
DIARIZATION_CONFIG = DIARIZATION_DIR / "config.yaml"

device = "cuda" if torch.cuda.is_available() else "cpu"
TARGET_SR = 16000

_asr_pipe = None
_diar_pipeline: Pipeline | None = None


@dataclass
class Segment:
    speaker: str
    text: str
    t_start: float
    t_end: float


@dataclass
class DiarizationResult:
    """
    segments: list of Segment with raw labels:
        - mode='stereo' → labels are CHANNEL_0, CHANNEL_1, ... (per audio channel)
        - mode='mono'   → labels are SPEAKER_0, SPEAKER_1, ... (pyannote-derived,
                          renumbered in order of first appearance)
    mode: how diarization was produced.
    n_channels: source audio channels (1 = mono, 2+ = multi-track telephony).
    """
    segments: list[Segment]
    mode: Literal["stereo", "mono"]
    n_channels: int
    speaker_labels: list[str] = field(default_factory=list)


def _get_asr_pipe():
    global _asr_pipe
    if _asr_pipe is None:
        logger.info("Loading Whisper ASR pipeline from %s", WHISPER_DIR)
        _asr_pipe = hf_pipeline(
            "automatic-speech-recognition",
            model=str(WHISPER_DIR),
            chunk_length_s=30,
            return_timestamps=True,
            device=0 if device == "cuda" else -1,
        )
        logger.info("Whisper ASR pipeline ready")
    return _asr_pipe


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


def _load_audio(audio_bytes: bytes) -> tuple[np.ndarray, int, int]:
    """
    Returns (audio, sr, n_channels). audio shape:
      - mono: (samples,)
      - stereo: (channels, samples)
    """
    try:
        data, sr = sf.read(BytesIO(audio_bytes), dtype="float32", always_2d=True)
        # data shape: (samples, channels) → transpose to (channels, samples)
        data = data.T
        n_channels = data.shape[0]
        if sr != TARGET_SR:
            # Resample each channel
            resampled = np.stack([
                librosa.resample(data[c], orig_sr=sr, target_sr=TARGET_SR)
                for c in range(n_channels)
            ])
            data = resampled
            sr = TARGET_SR
        if n_channels == 1:
            return data[0], sr, 1
        return data, sr, n_channels
    except Exception:
        logger.warning("soundfile decode failed; falling back to librosa mono", exc_info=True)
        mono, sr = librosa.load(BytesIO(audio_bytes), sr=TARGET_SR, mono=True)
        return mono, sr, 1


def _diarize_stereo_telephony(stereo: np.ndarray, sr: int) -> list[tuple[float, float, str]]:
    """
    Telephony stereo: channel 0 = one party, channel 1 = other party.
    Use simple energy-based VAD per channel — perfect speaker separation
    without ML model.
    """
    turns: list[tuple[float, float, str]] = []
    frame_ms = 30
    hop = int(sr * frame_ms / 1000)
    energy_threshold = 0.005  # RMS

    for ch_idx in range(stereo.shape[0]):
        ch = stereo[ch_idx]
        # Frame-level RMS
        n_frames = (len(ch) - hop) // hop
        if n_frames <= 0:
            continue
        rms = np.sqrt(
            np.mean(
                ch[: n_frames * hop].reshape(n_frames, hop) ** 2, axis=1
            ) + 1e-10
        )
        active = rms > energy_threshold

        # Group consecutive active frames into turns
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
) -> DiarizationResult:
    """
    Pipeline:
    1. Load audio. If stereo (telephony) → use per-channel separation
       (labels: CHANNEL_0, CHANNEL_1, ...). If mono → run pyannote diarization
       (labels: SPEAKER_0, SPEAKER_1, ... after normalization).
    2. Run Whisper ASR on mixed mono signal.
    3. Map each ASR chunk to overlapping diarization turn (max-overlap).
    4. Merge consecutive same-speaker segments.
    Returns DiarizationResult with raw labels — caller (analysis.py) decides
    which speaker is manager vs client.
    """
    audio, sr, n_channels = _load_audio(audio_bytes)
    if n_channels == 1:
        waveform_np = audio
    else:
        waveform_np = audio.mean(axis=0)
    total_duration = len(waveform_np) / sr
    logger.info(
        "Audio: %.1fs, sr=%d, channels=%d, samples=%d",
        total_duration, sr, n_channels, len(waveform_np),
    )

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

    asr = _get_asr_pipe()
    asr_result = asr(
        {"array": waveform_np, "sampling_rate": sr},
        generate_kwargs={"language": "ru", "task": "transcribe"},
    )
    chunks = asr_result.get("chunks") or []

    if not chunks:
        full_text = (asr_result.get("text") or "").strip()
        logger.warning("No ASR chunks — single segment fallback")
        speaker = turns[0][2] if turns else (
            "CHANNEL_0" if mode == "stereo" else "SPEAKER_0"
        )
        segments = (
            [Segment(speaker, full_text, 0.0, total_duration)] if full_text else []
        )
        return DiarizationResult(
            segments=segments,
            mode=mode,
            n_channels=n_channels,
            speaker_labels=sorted({t[2] for t in turns}),
        )

    segments: list[Segment] = []
    for chunk in chunks:
        ts = chunk.get("timestamp") or (None, None)
        if ts[0] is None:
            continue
        t_start = float(ts[0])
        t_end = float(ts[1]) if ts[1] is not None else total_duration
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        speaker = _assign_speaker(t_start, t_end, turns)
        segments.append(Segment(speaker, text, t_start, t_end))

    if not segments:
        return DiarizationResult(
            segments=[], mode=mode, n_channels=n_channels, speaker_labels=[],
        )

    # Mono only: renumber pyannote's SPEAKER_XX into SPEAKER_0/1/...
    # Stereo: keep CHANNEL_0/CHANNEL_1 as-is (channel index is meaningful).
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


def _assign_speaker(
    t_start: float, t_end: float, turns: list[tuple[float, float, str]]
) -> str:
    if not turns:
        return "SPEAKER_00"
    best_speaker = turns[0][2]
    best_overlap = 0.0
    for turn_start, turn_end, speaker in turns:
        overlap = max(0.0, min(t_end, turn_end) - max(t_start, turn_start))
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = speaker
    if best_overlap == 0.0:
        mid = 0.5 * (t_start + t_end)
        nearest = min(turns, key=lambda t: min(abs(mid - t[0]), abs(mid - t[1])))
        best_speaker = nearest[2]
    return best_speaker


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
