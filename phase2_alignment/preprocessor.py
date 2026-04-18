"""
Phase 2 Audio Preprocessor — runs BEFORE MFA alignment.

Handles noisy / imperfect real-world student audio.  All behaviour is
opt-in via boolean flags in PreprocessorConfig so that clean studio
audio passes through unchanged.

Usage:
    from phase2_alignment.preprocessor import PreprocessorConfig, preprocess_audio

    config = PreprocessorConfig(enable_noise_reduction=True)
    result = preprocess_audio("/path/to/audio.wav", config)
    wav_for_mfa = result["cleaned_wav_path"]
"""

import logging
import os
import struct
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000  # project standard — all WAVs are 16 kHz mono


# ── Configuration ────────────────────────────────────────────────────────

@dataclass
class PreprocessorConfig:
    """All flags default to False — clean audio passes through unchanged."""
    enable_noise_reduction: bool = False
    enable_restart_detection: bool = False
    enable_repetition_detection: bool = False
    enable_pause_handling: bool = False

    # Noise-reduction tunables
    noise_profile_seconds: float = 0.5
    prop_decrease: float = 0.5       # MUST stay <= 0.7
    rms_speech_threshold: float = 0.02

    # Restart-detection tunables
    restart_silence_min_ms: int = 2000

    # Repetition-detection tunables
    repetition_corr_threshold: float = 0.85

    # Pause-handling tunables
    pause_min_silence_ms: int = 500
    pause_low_confidence_ms: int = 200


# ── Result type ──────────────────────────────────────────────────────────

def _empty_result(wav_path: str) -> dict:
    return {
        "cleaned_wav_path": wav_path,
        "restart_trim_ms": None,
        "repetition_segments": [],
        "silence_segments": [],
        "preprocessing_applied": [],
    }


# ── VAD helpers ──────────────────────────────────────────────────────────

def _run_vad(audio: np.ndarray, sample_rate: int = SAMPLE_RATE,
             aggressiveness: int = 2) -> List[Tuple[int, int]]:
    """Run WebRTC VAD and return speech segments as (start_ms, end_ms).

    Parameters
    ----------
    audio : np.ndarray
        Float32 mono audio, values in [-1, 1].
    sample_rate : int
        Must be 8000, 16000, 32000, or 48000.
    aggressiveness : int
        0-3, higher = more aggressive at filtering non-speech.
    """
    import webrtcvad

    vad = webrtcvad.Vad(aggressiveness)
    frame_duration_ms = 30          # WebRTC requires 10/20/30 ms frames
    frame_size = int(sample_rate * frame_duration_ms / 1000)

    # Convert float32 → int16 PCM bytes
    pcm = (audio * 32767).astype(np.int16)
    raw = pcm.tobytes()

    segments: List[Tuple[int, int]] = []
    in_speech = False
    seg_start = 0

    for offset in range(0, len(pcm) - frame_size + 1, frame_size):
        frame_bytes = raw[offset * 2:(offset + frame_size) * 2]
        if len(frame_bytes) < frame_size * 2:
            break
        is_speech = vad.is_speech(frame_bytes, sample_rate)
        time_ms = int(offset / sample_rate * 1000)

        if is_speech and not in_speech:
            seg_start = time_ms
            in_speech = True
        elif not is_speech and in_speech:
            segments.append((seg_start, time_ms))
            in_speech = False

    if in_speech:
        segments.append((seg_start, int(len(pcm) / sample_rate * 1000)))

    return segments


def _compute_silences(speech_segments: List[Tuple[int, int]],
                      total_ms: int) -> List[Tuple[int, int]]:
    """Derive silence segments from the gaps between speech segments."""
    silences = []
    prev_end = 0
    for start, end in speech_segments:
        if start > prev_end:
            silences.append((prev_end, start))
        prev_end = end
    if prev_end < total_ms:
        silences.append((prev_end, total_ms))
    return silences


# ── 1. Noise Reduction ──────────────────────────────────────────────────

def _noise_reduction(wav_path: str, cfg: PreprocessorConfig) -> str:
    """Apply mild spectral-subtraction noise reduction.

    Returns path to cleaned WAV (temp file) or original path if skipped.
    """
    import noisereduce as nr

    audio, sr = sf.read(wav_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio[:, 0]

    # Estimate noise from first N seconds (assumed pre-recitation silence)
    profile_samples = int(cfg.noise_profile_seconds * sr)
    profile_samples = min(profile_samples, len(audio))
    noise_clip = audio[:profile_samples]

    # Safety: if first segment has high RMS → speech, not silence — skip
    rms = float(np.sqrt(np.mean(noise_clip ** 2)))
    if rms > cfg.rms_speech_threshold:
        logger.warning(
            "Noise-reduction skipped: first %.1fs has RMS %.4f > threshold %.4f "
            "(likely contains speech)",
            cfg.noise_profile_seconds, rms, cfg.rms_speech_threshold,
        )
        return wav_path

    # Clamp prop_decrease for safety
    prop = min(cfg.prop_decrease, 0.7)

    cleaned = nr.reduce_noise(
        y=audio, sr=sr,
        y_noise=noise_clip,
        prop_decrease=prop,
    )

    # Write to temp WAV
    fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="nr_")
    os.close(fd)
    sf.write(tmp_path, cleaned, sr)
    logger.info("Noise-reduced audio written to %s", tmp_path)
    return tmp_path


# ── 2. Restart Detection ────────────────────────────────────────────────

def _detect_restart(wav_path: str, cfg: PreprocessorConfig) -> Optional[int]:
    """Detect if the student restarted mid-recitation.

    Returns start_ms of the final attempt, or None if no restart detected.
    """
    audio, sr = sf.read(wav_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio[:, 0]

    speech_segments = _run_vad(audio, sr)
    if len(speech_segments) < 2:
        return None

    total_ms = int(len(audio) / sr * 1000)
    silences = _compute_silences(speech_segments, total_ms)

    # Find long silences (> threshold) that indicate a restart
    long_silence_indices = []
    for i, (sil_start, sil_end) in enumerate(silences):
        if (sil_end - sil_start) >= cfg.restart_silence_min_ms:
            long_silence_indices.append(i)

    if not long_silence_indices:
        return None

    # The restart point is the speech segment AFTER the last long silence.
    # Find which speech segment follows the last long silence.
    last_sil_idx = long_silence_indices[-1]
    last_sil_end = silences[last_sil_idx][1]

    # Find the first speech segment starting at or after that silence end
    for seg_start, seg_end in speech_segments:
        if seg_start >= last_sil_end - 50:  # 50ms tolerance
            # Validate: energy pattern should "reset" — the post-silence
            # segment should resemble the beginning of the recitation.
            # Compare RMS energy envelopes of the first speech segment
            # and this restart candidate.
            first_seg = speech_segments[0]
            first_samples = audio[
                int(first_seg[0] / 1000 * sr):int(first_seg[1] / 1000 * sr)
            ]
            restart_samples = audio[
                int(seg_start / 1000 * sr):int(seg_end / 1000 * sr)
            ]

            if len(first_samples) > 0 and len(restart_samples) > 0:
                # Compare energy envelopes (coarse check)
                first_rms = float(np.sqrt(np.mean(first_samples ** 2)))
                restart_rms = float(np.sqrt(np.mean(restart_samples ** 2)))
                ratio = restart_rms / max(first_rms, 1e-10)
                # Accept if energy is within 5x of opening — similar
                # loudness indicates a fresh start, not a coda/trail-off
                if 0.2 < ratio < 5.0:
                    logger.info(
                        "Restart detected: trimming to %d ms (energy ratio %.2f)",
                        seg_start, ratio,
                    )
                    return seg_start

    return None


# ── 3. Repetition Detection ─────────────────────────────────────────────

def _detect_repetitions(wav_path: str,
                        cfg: PreprocessorConfig) -> List[dict]:
    """Detect repeated words/phrases via energy-envelope correlation.

    Returns list of {"start_ms": int, "end_ms": int, "repetition_suspected": True}.
    """
    audio, sr = sf.read(wav_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio[:, 0]

    speech_segments = _run_vad(audio, sr)
    if len(speech_segments) < 2:
        return []

    flagged = []

    for i in range(len(speech_segments) - 1):
        seg_a_start, seg_a_end = speech_segments[i]
        seg_b_start, seg_b_end = speech_segments[i + 1]

        samples_a = audio[int(seg_a_start / 1000 * sr):int(seg_a_end / 1000 * sr)]
        samples_b = audio[int(seg_b_start / 1000 * sr):int(seg_b_end / 1000 * sr)]

        if len(samples_a) < 160 or len(samples_b) < 160:
            continue

        # Compute energy envelopes (windowed RMS)
        env_a = _energy_envelope(samples_a, sr)
        env_b = _energy_envelope(samples_b, sr)

        if len(env_a) == 0 or len(env_b) == 0:
            continue

        # Resample to equal length for correlation
        min_len = min(len(env_a), len(env_b))
        max_len = max(len(env_a), len(env_b))
        # Only compare if segment lengths are within 2x of each other
        if max_len > 2 * min_len:
            continue

        env_a_r = np.interp(
            np.linspace(0, 1, min_len), np.linspace(0, 1, len(env_a)), env_a
        )
        env_b_r = np.interp(
            np.linspace(0, 1, min_len), np.linspace(0, 1, len(env_b)), env_b
        )

        # Pearson correlation
        corr = _pearson_corr(env_a_r, env_b_r)
        if corr > cfg.repetition_corr_threshold:
            logger.info(
                "Repetition suspected: segments [%d–%d] and [%d–%d] ms, corr=%.3f",
                seg_a_start, seg_a_end, seg_b_start, seg_b_end, corr,
            )
            # Flag the first of the pair (the repeated attempt)
            flagged.append({
                "start_ms": seg_a_start,
                "end_ms": seg_a_end,
                "repetition_suspected": True,
            })

    return flagged


def _energy_envelope(samples: np.ndarray, sr: int,
                     window_ms: int = 20) -> np.ndarray:
    """Compute windowed RMS energy envelope."""
    win_size = int(sr * window_ms / 1000)
    if win_size < 1 or len(samples) < win_size:
        return np.array([])
    n_frames = len(samples) // win_size
    envelope = np.zeros(n_frames)
    for i in range(n_frames):
        frame = samples[i * win_size:(i + 1) * win_size]
        envelope[i] = float(np.sqrt(np.mean(frame ** 2)))
    return envelope


def _pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation, returns 0.0 on degenerate input."""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    a_std = np.std(a)
    b_std = np.std(b)
    if a_std < 1e-10 or b_std < 1e-10:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


# ── 4. Silence / Pause Handling ──────────────────────────────────────────

def _detect_pauses(wav_path: str,
                   cfg: PreprocessorConfig) -> List[dict]:
    """Detect long mid-speech silences that may corrupt phone durations.

    Returns list of {"start_ms": int, "end_ms": int}.
    """
    audio, sr = sf.read(wav_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio[:, 0]

    speech_segments = _run_vad(audio, sr)
    if not speech_segments:
        return []

    total_ms = int(len(audio) / sr * 1000)

    # Overall speech region: from first speech start to last speech end
    speech_start = speech_segments[0][0]
    speech_end = speech_segments[-1][1]

    silences = _compute_silences(speech_segments, total_ms)

    pauses = []
    for sil_start, sil_end in silences:
        # Only consider silences within the speech region
        if sil_start < speech_start or sil_end > speech_end:
            continue
        duration_ms = sil_end - sil_start
        if duration_ms >= cfg.pause_min_silence_ms:
            pauses.append({"start_ms": sil_start, "end_ms": sil_end})

    if pauses:
        logger.info("Detected %d long pauses within speech region", len(pauses))

    return pauses


# ── Entry point ──────────────────────────────────────────────────────────

def preprocess_audio(wav_path: str, config: PreprocessorConfig) -> dict:
    """Run enabled preprocessing steps on a raw WAV file.

    Parameters
    ----------
    wav_path : str
        Path to the input 16 kHz mono WAV.
    config : PreprocessorConfig
        Which steps to enable.

    Returns
    -------
    dict with keys:
        cleaned_wav_path      – path to use for MFA (same as input if no cleaning)
        restart_trim_ms       – trim audio before this point (or None)
        repetition_segments   – segments to flag skip_assessment
        silence_segments      – segments with long pauses
        preprocessing_applied – list of step names that actually ran
    """
    result = _empty_result(wav_path)

    # 1. Noise reduction (produces a new WAV for MFA)
    if config.enable_noise_reduction:
        cleaned_path = _noise_reduction(wav_path, config)
        if cleaned_path != wav_path:
            result["cleaned_wav_path"] = cleaned_path
            result["preprocessing_applied"].append("noise_reduction")

    # Use cleaned audio for subsequent analysis
    analysis_path = result["cleaned_wav_path"]

    # 2. Restart detection
    if config.enable_restart_detection:
        trim_ms = _detect_restart(analysis_path, config)
        if trim_ms is not None:
            result["restart_trim_ms"] = trim_ms
            result["preprocessing_applied"].append("restart_detection")

            # Trim the audio file for MFA
            audio, sr = sf.read(analysis_path, dtype="float32")
            if audio.ndim > 1:
                audio = audio[:, 0]
            trim_sample = int(trim_ms / 1000.0 * sr)
            trimmed = audio[trim_sample:]

            fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="trim_")
            os.close(fd)
            sf.write(tmp_path, trimmed, sr)
            result["cleaned_wav_path"] = tmp_path
            analysis_path = tmp_path
            logger.info("Restart-trimmed audio written to %s", tmp_path)

    # 3. Repetition detection (flag only — do not remove audio)
    if config.enable_repetition_detection:
        reps = _detect_repetitions(analysis_path, config)
        if reps:
            result["repetition_segments"] = reps
            result["preprocessing_applied"].append("repetition_detection")

    # 4. Silence / pause handling
    if config.enable_pause_handling:
        pauses = _detect_pauses(analysis_path, config)
        if pauses:
            result["silence_segments"] = pauses
            result["preprocessing_applied"].append("pause_handling")

    return result
