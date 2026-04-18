"""F0 pitch tracking utility for Phase 3 assessors.

Reusable module for extracting fundamental frequency (F0) over a region
of audio. Used across Phase 3 to distinguish genuine periodic phonation
from breath residue, MFA silence absorption, or unvoiced noise.

Consumers:
  * ghunnah.py — confirm sustained voicing in 8-12 count borderline
    nasal phones (separate tartil from MFA-absorbed silence).
  * tafkhim.py (future) — heavy Ra has measurably lower F0 than light Ra.
  * ikhfa.py (future) — confirm reciter is vocalizing rather than
    exhaling during nasal hold.

Uses librosa.pyin() — probabilistic YIN, more robust than classic YIN
for voiced speech and it natively reports per-frame voicing flags.

Standalone: imports nothing from phase3_assessment so it can be used
without pulling in the rest of the assessment pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────

# Minimum fraction of analysis frames that must be voiced for the whole
# region to count as "voiced". 0.5 rejects regions that are more silence
# or noise than phonation.
VOICED_FRACTION_THRESHOLD = 0.5

# Std deviation ceiling (Hz) across voiced F0 frames below which the
# phonation is considered stable. Genuine sustained ghunnah holds a
# steady fundamental; breath residue and MFA-absorbed noise do not.
F0_STABILITY_HZ = 30.0

# Expected F0 search range for an adult male Quran reciter. pyin() needs
# fmin/fmax bounds — 65 Hz covers deep chest voice (and is the lowest
# value that fits ≥2 periods inside a 512-sample frame at 16 kHz, which
# is what librosa.pyin requires for reliable detection), 400 Hz allows
# head-voice excursions without letting pyin chase harmonics into noise.
FMIN_HZ = 65.0
FMAX_HZ = 400.0

# Project-wide sample rate (Phase 2 WAV corpus is 16 kHz mono).
SAMPLE_RATE = 16000

# pyin frame sizing — chosen to match ghunnah.py's FFT framing so F0
# frames align with nasality frames when both are computed on the same
# region.
FRAME_LENGTH = 512          # 32 ms at 16 kHz
HOP_LENGTH = 160            # 10 ms at 16 kHz


# ── Result dataclass ─────────────────────────────────────────────────

@dataclass
class F0Result:
    """Per-region F0 tracking result.

    f0_hz           : F0 estimate per frame, 0.0 for unvoiced frames
    voiced_flags    : per-frame voicing decision from pyin
    mean_f0_hz      : mean F0 across voiced frames only (0.0 if none)
    voiced_fraction : fraction of frames flagged voiced (0.0–1.0)
    f0_std_hz       : std dev of F0 across voiced frames (stability
                      metric — low std = stable pitch = real phonation)
    is_voiced       : voiced_fraction > VOICED_FRACTION_THRESHOLD
    is_stable       : is_voiced AND f0_std_hz < F0_STABILITY_HZ
    frame_count     : total analysis frames
    """
    f0_hz: List[float] = field(default_factory=list)
    voiced_flags: List[bool] = field(default_factory=list)
    mean_f0_hz: float = 0.0
    voiced_fraction: float = 0.0
    f0_std_hz: float = 0.0
    is_voiced: bool = False
    is_stable: bool = False
    frame_count: int = 0


# ── Main entry point ─────────────────────────────────────────────────

def track_f0(
    audio: np.ndarray,
    sr: int,
    start_ms: float,
    end_ms: float,
) -> F0Result:
    """Track F0 across a region of an audio buffer.

    Parameters
    ----------
    audio    : mono audio samples (float32). Treated as the reference
               buffer — start_ms/end_ms are offsets into it.
    sr       : sample rate (expected 16000).
    start_ms : region start in ms relative to audio[0].
    end_ms   : region end in ms relative to audio[0].

    Returns
    -------
    F0Result with per-frame F0, voicing flags, and aggregate stats.
    Returns an empty (all-default) F0Result on any failure — caller
    should inspect frame_count / is_voiced rather than assume success.
    """
    import librosa

    if audio is None or len(audio) == 0:
        return F0Result()

    start_sample = max(0, int(start_ms / 1000.0 * sr))
    end_sample = min(len(audio), int(end_ms / 1000.0 * sr))

    if end_sample - start_sample < FRAME_LENGTH:
        # Region too short for a single pyin frame — nothing to analyse.
        return F0Result()

    segment = np.asarray(audio[start_sample:end_sample], dtype=np.float32)

    try:
        f0, voiced_flag, _voiced_prob = librosa.pyin(
            segment,
            fmin=FMIN_HZ,
            fmax=FMAX_HZ,
            sr=sr,
            frame_length=FRAME_LENGTH,
            hop_length=HOP_LENGTH,
        )
    except Exception as exc:
        logger.warning(
            "librosa.pyin failed on region [%.0f–%.0f ms]: %s",
            start_ms, end_ms, exc,
        )
        return F0Result()

    # librosa.pyin returns NaN for unvoiced frames — replace with 0.0.
    f0_clean = np.where(np.isnan(f0), 0.0, f0).astype(float)
    voiced = np.asarray(voiced_flag, dtype=bool)

    frame_count = int(len(f0_clean))
    if frame_count == 0:
        return F0Result()

    voiced_count = int(np.sum(voiced))
    voiced_fraction = voiced_count / frame_count

    if voiced_count > 0:
        voiced_vals = f0_clean[voiced]
        # Guard against residual zeros (pyin occasionally flags voiced
        # but assigns 0) — filter them out of the stability stats.
        nonzero = voiced_vals[voiced_vals > 0.0]
        if nonzero.size > 0:
            mean_f0 = float(np.mean(nonzero))
            f0_std = float(np.std(nonzero))
        else:
            mean_f0 = 0.0
            f0_std = 0.0
    else:
        mean_f0 = 0.0
        f0_std = 0.0

    is_voiced = voiced_fraction > VOICED_FRACTION_THRESHOLD
    is_stable = is_voiced and f0_std < F0_STABILITY_HZ

    return F0Result(
        f0_hz=f0_clean.tolist(),
        voiced_flags=voiced.tolist(),
        mean_f0_hz=mean_f0,
        voiced_fraction=voiced_fraction,
        f0_std_hz=f0_std,
        is_voiced=is_voiced,
        is_stable=is_stable,
        frame_count=frame_count,
    )
