"""Assessment 4 — Ikhfa nasalization quality checker.

Scope:
  ghunnah.py already assesses ikhfaa_light and ikhfaa_heavy phones for
  BOTH duration (via _duration_severity_ikhfaa) AND nasalization (via
  _nasalization_severity using peak nasality). This assessor therefore
  handles *nasalization quality classification only* — distinguishing
  izhar error, under-nasalized, correct partial concealment, and
  over-nasalized — and does NOT re-assess duration.

  ghunnah.py's nasalization check is binary (present/absent via peak
  ratio). This assessor applies a finer 4-tier classification using
  mean nasality ratio across all frames, which is the appropriate
  metric for ikhfa's *partial* concealment character.

Method:
  For each phone tagged ikhfaa_light or ikhfaa_heavy:
    1. Load audio window [start_ms, end_ms] (exact MFA boundaries,
       no extension — ±50ms margin tested and rejected, it pulls in
       surrounding vowel energy without changing verdicts)
    2. Compute FFT per 10ms frame (non-overlapping, matching ghunnah)
    3. Per frame: nasality_ratio = energy(200-400 Hz) / energy(200-4000 Hz)
    4. Compute mean nasality ratio across all frames
    5. Classify verdict from mean ratio against rule-specific thresholds

Calibration:
  Empirically calibrated on reciter_2, 5 surahs (1, 36, 93, 97, 113),
  62 assessed phones. Thresholds validated against professional recitation.
  ikhfaa_light ceiling 0.55 — well calibrated (56 phones).
  ikhfaa_heavy ceiling 0.55 — provisional (4 phones only, expand when
  full Quran dataset available).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from phase3_assessment.models import (
    AssessmentError,
    CalibrationResult,
    Phone,
    Verse,
    Word,
)
from phase3_assessment.utils.loader import audio_path

logger = logging.getLogger(__name__)

# ── Ikhfa rules handled by this assessor ────────────────────────────
IKHFA_RULES = {"ikhfaa_light", "ikhfaa_heavy"}

# ── Audio / acoustic constants (matching ghunnah.py exactly) ────────
SAMPLE_RATE = 16000
FRAME_SAMPLES = 160          # 10ms at 16kHz
FRAME_MS = 10.0
FFT_WINDOW_SIZE = 512        # 32ms at 16kHz for FFT

# Frequency bands for nasality ratio (same as ghunnah.py)
NASAL_BAND_LOW_HZ = 200      # lower bound of nasal formant band
NASAL_BAND_HIGH_HZ = 400     # upper bound of nasal formant band
TOTAL_BAND_LOW_HZ = 200      # lower bound of total energy band
TOTAL_BAND_HIGH_HZ = 4000    # upper bound of total energy band

# Search window extension beyond MFA boundaries
SEARCH_MARGIN_MS = 0.0        # no extension — use exact MFA boundaries

# Skip gate — phones shorter than this cannot be reliably assessed
MIN_PHONE_DURATION_MS = 30.0

# ── Nasalization quality thresholds (mean ratio, majority vote) ─────
# Empirically calibrated on reciter_2, 5 surahs, 62 assessed phones

# --- ikhfaa_light (56 phones, well calibrated) ---
LIGHT_RATIO_IZHAR_ERROR = 0.05    # below → no nasalization (major)
LIGHT_RATIO_UNDER_NASAL = 0.08    # 0.05–0.08 → too weak (minor)
LIGHT_RATIO_CORRECT_MAX = 0.55    # 0.08–0.55 → correct (pass)
# above 0.55 → over_nasalized (style)

# --- ikhfaa_heavy (4 phones only — PROVISIONAL, needs recalibration
#     once full Quran dataset is tested across all emphatic contexts) ---
HEAVY_RATIO_IZHAR_ERROR = 0.05
HEAVY_RATIO_UNDER_NASAL = 0.08
HEAVY_RATIO_CORRECT_MAX = 0.55    # PROVISIONAL — may need to raise
# above 0.55 → over_nasalized (style)


# ── Result dataclass ────────────────────────────────────────────────

@dataclass
class IkhfaResult:
    """Per-phone ikhfa nasalization quality result."""
    phone_index: int
    word: str
    ipa: str
    tajweed_rule: str
    start_ms: float
    end_ms: float
    duration_ms: float
    verdict: str               # "pass" | "izhar_error" | "under_nasalized" | "over_nasalized" | "skipped"
    severity: str              # "major" | "minor" | "style" | "pass" | "skipped"
    mean_nasality_ratio: float  # mean across assessed frames
    frame_count: int           # number of frames analysed
    skip_reason: Optional[str] = None


# ── Audio loading (matches ghunnah.py pattern) ──────────────────────

def _load_audio_segment(
    audio_file, start_ms: float, end_ms: float,
) -> Optional[np.ndarray]:
    """Load a segment of audio from a WAV file at 16kHz."""
    try:
        import soundfile as sf

        start_sample = int(start_ms / 1000.0 * SAMPLE_RATE)
        end_sample = int(end_ms / 1000.0 * SAMPLE_RATE)

        info = sf.info(str(audio_file))
        total_samples = int(info.frames)
        start_sample = max(0, min(start_sample, total_samples))
        end_sample = max(start_sample, min(end_sample, total_samples))

        if end_sample - start_sample < FFT_WINDOW_SIZE:
            return None

        y, _ = sf.read(
            str(audio_file),
            start=start_sample,
            stop=end_sample,
            dtype="float32",
        )
        if y.ndim > 1:
            y = y[:, 0]
        return y
    except Exception as exc:
        logger.warning("Audio load failed for %s [%.0f-%.0f ms]: %s",
                       audio_file, start_ms, end_ms, exc)
        return None


# ── Per-frame nasality computation (matches ghunnah.py exactly) ─────

def _compute_frame_nasality(segment: np.ndarray) -> List[float]:
    """Compute per-frame nasality ratio (10ms frames, 512-pt FFT).

    nasality[t] = energy(200-400Hz) / energy(200-4000Hz)

    Each frame is 160 samples (10ms). FFT is zero-padded to 512 points
    for frequency resolution. Hann window applied.
    """
    n_fft = FFT_WINDOW_SIZE
    window = np.hanning(FRAME_SAMPLES)
    freq_res = SAMPLE_RATE / n_fft

    nasal_lo_bin = int(NASAL_BAND_LOW_HZ / freq_res)
    nasal_hi_bin = int(NASAL_BAND_HIGH_HZ / freq_res) + 1
    total_lo_bin = int(TOTAL_BAND_LOW_HZ / freq_res)
    total_hi_bin = int(TOTAL_BAND_HIGH_HZ / freq_res) + 1

    ratios = []
    for start in range(0, len(segment) - FRAME_SAMPLES + 1, FRAME_SAMPLES):
        frame = segment[start : start + FRAME_SAMPLES] * window
        # Zero-pad to n_fft for better frequency resolution
        padded = np.zeros(n_fft)
        padded[:FRAME_SAMPLES] = frame
        spectrum = np.abs(np.fft.rfft(padded)) ** 2

        total_energy = float(np.sum(spectrum[total_lo_bin:total_hi_bin]))
        nasal_energy = float(np.sum(spectrum[nasal_lo_bin:nasal_hi_bin]))

        if total_energy < 1e-12:
            ratios.append(0.0)
        else:
            ratios.append(nasal_energy / total_energy)

    return ratios


# ── Frame classification + majority vote ────────────────────────────

def _thresholds_for_rule(rule: str) -> Tuple[float, float, float]:
    """Return (izhar_ceiling, under_nasal_ceiling, correct_max) for a rule."""
    if rule == "ikhfaa_heavy":
        return HEAVY_RATIO_IZHAR_ERROR, HEAVY_RATIO_UNDER_NASAL, HEAVY_RATIO_CORRECT_MAX
    return LIGHT_RATIO_IZHAR_ERROR, LIGHT_RATIO_UNDER_NASAL, LIGHT_RATIO_CORRECT_MAX


def _classify_frame(ratio: float, rule: str) -> str:
    """Classify a single frame's nasality ratio for a given rule."""
    izhar_ceil, under_ceil, correct_max = _thresholds_for_rule(rule)
    if ratio < izhar_ceil:
        return "izhar_error"
    if ratio < under_ceil:
        return "under_nasalized"
    if ratio <= correct_max:
        return "correct"
    return "over_nasalized"


def _majority_vote(ratios: List[float], rule: str) -> Tuple[str, float]:
    """Classify each frame and return (majority_class, mean_ratio).

    Returns the class that appears most frequently across all frames.
    Ties broken by severity order: izhar_error > under_nasalized >
    over_nasalized > correct (prefer flagging errors).
    """
    if not ratios:
        return "izhar_error", 0.0

    counts: Dict[str, int] = {
        "izhar_error": 0,
        "under_nasalized": 0,
        "correct": 0,
        "over_nasalized": 0,
    }
    for r in ratios:
        label = _classify_frame(r, rule)
        counts[label] += 1

    mean_ratio = float(np.mean(ratios))

    # Sort by count descending, then by severity priority for ties
    priority = {"izhar_error": 0, "under_nasalized": 1, "over_nasalized": 2, "correct": 3}
    majority = sorted(counts.keys(), key=lambda k: (-counts[k], priority[k]))[0]

    return majority, mean_ratio


# ── Verdict / severity mapping ──────────────────────────────────────

def _verdict_severity(mean_ratio: float, rule: str) -> Tuple[str, str]:
    """Classify verdict from mean_nasality_ratio against rule thresholds.

    Uses mean ratio exclusively — not majority vote — for the pass/fail
    decision. This avoids tie-breaker artifacts where a 50/50 frame
    split incorrectly overrides a passing mean.

    izhar_error    → ("izhar_error",    "major")  — no nasalization
    under_nasalized → ("under_nasalized", "minor") — concealment too weak
    correct        → ("pass",           "pass")   — correct partial concealment
    over_nasalized → ("over_nasalized", "style")  — too nasal, acceptable in tartil
    """
    izhar_ceil, under_ceil, correct_max = _thresholds_for_rule(rule)
    if mean_ratio < izhar_ceil:
        return "izhar_error", "major"
    if mean_ratio < under_ceil:
        return "under_nasalized", "minor"
    if mean_ratio <= correct_max:
        return "pass", "pass"
    return "over_nasalized", "style"


# ── Description helper ──────────────────────────────────────────────

def _describe(
    rule: str, verdict: str, mean_ratio: float, frame_count: int,
) -> str:
    izhar_ceil, under_ceil, correct_max = _thresholds_for_rule(rule)
    display = rule.replace("_", " ").title()
    if verdict == "izhar_error":
        return (f"Ikhfa {display} — no nasalization detected, noon "
                f"pronounced clearly (mean ratio={mean_ratio:.4f}, "
                f"threshold={izhar_ceil}, frames={frame_count})")
    if verdict == "under_nasalized":
        return (f"Ikhfa {display} — concealment too weak "
                f"(mean ratio={mean_ratio:.4f}, "
                f"range {izhar_ceil}-{under_ceil}, "
                f"frames={frame_count})")
    if verdict == "over_nasalized":
        return (f"Ikhfa {display} — over-nasalized, too much ghunnah "
                f"(mean ratio={mean_ratio:.4f}, "
                f"ceiling={correct_max}, frames={frame_count})")
    return (f"Ikhfa {display} — correct partial concealment "
            f"(mean ratio={mean_ratio:.4f}, frames={frame_count})")


# ── Main assessment function ────────────────────────────────────────

def assess_ikhfa(
    verse: Verse,
    cal: CalibrationResult,
    load_audio: bool = True,
    collect_details: bool = False,
) -> Tuple[List[AssessmentError], int, int, List[IkhfaResult]]:
    """Assess nasalization quality for all ikhfa phones in a verse.

    This assesses *nasalization quality only* — duration is already
    handled by ghunnah.py for ikhfaa_light and ikhfaa_heavy rules.

    Returns (errors, phones_assessed, phones_skipped, details).

    `details` is populated only when collect_details=True (for test/
    reporting scripts); disabled by default for pipeline runs.
    """
    errors: List[AssessmentError] = []
    details: List[IkhfaResult] = []
    assessed = 0
    skipped = 0

    flat: List[Tuple[Word, Phone]] = [
        (w, p) for w in verse.words for p in w.phones
    ]

    wav_file = None
    if load_audio:
        wav_file = audio_path(verse.surah, verse.ayah)

    for i, (word, phone) in enumerate(flat):
        rules_on_phone = [
            r for r in phone.tajweed_rules if r in IKHFA_RULES
        ]
        if not rules_on_phone:
            continue

        # For geminate pairs, only assess the "first" phone
        if phone.geminate_pair and phone.geminate_position == "second":
            continue

        start_ms = phone.start * 1000
        end_ms = phone.end * 1000
        duration_ms = phone.duration_ms

        # ── Skip conditions ─────────────────────────────────────────
        skip_reason = None
        if phone.alignment_confidence in ("low", "failed"):
            skip_reason = f"alignment_confidence={phone.alignment_confidence}"
        elif phone.skip_assessment:
            skip_reason = "skip_assessment=True"
        elif duration_ms <= MIN_PHONE_DURATION_MS:
            skip_reason = f"duration_ms={duration_ms:.1f} <= {MIN_PHONE_DURATION_MS}"

        if skip_reason is not None:
            skipped += 1
            if collect_details:
                for rule in rules_on_phone:
                    details.append(IkhfaResult(
                        phone_index=i,
                        word=word.text,
                        ipa=phone.ipa,
                        tajweed_rule=rule,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        duration_ms=duration_ms,
                        verdict="skipped",
                        severity="skipped",
                        mean_nasality_ratio=0.0,
                        frame_count=0,
                        skip_reason=skip_reason,
                    ))
            continue

        # ── Acoustic analysis ───────────────────────────────────────
        ratios: Optional[List[float]] = None
        frame_count = 0

        if load_audio and wav_file is not None:
            search_start = max(0.0, start_ms - SEARCH_MARGIN_MS)
            search_end = end_ms + SEARCH_MARGIN_MS

            segment = _load_audio_segment(wav_file, search_start, search_end)
            if segment is not None and len(segment) >= FRAME_SAMPLES:
                ratios = _compute_frame_nasality(segment)
                frame_count = len(ratios) if ratios else 0

        # ── Per-rule assessment ─────────────────────────────────────
        for rule in rules_on_phone:
            if ratios:
                mean_ratio = float(np.mean(ratios))
            else:
                mean_ratio = 0.0
            assessed += 1
            verdict, severity = _verdict_severity(mean_ratio, rule)

            if collect_details:
                details.append(IkhfaResult(
                    phone_index=i,
                    word=word.text,
                    ipa=phone.ipa,
                    tajweed_rule=rule,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    duration_ms=duration_ms,
                    verdict=verdict,
                    severity=severity,
                    mean_nasality_ratio=round(mean_ratio, 6),
                    frame_count=frame_count,
                ))

            # Only emit AssessmentError for non-pass verdicts
            if verdict == "pass":
                continue

            errors.append(AssessmentError(
                word=word.text,
                phone=phone.ipa,
                phone_index=i,
                timestamp_ms=start_ms,
                rule=rule,
                assessment="nasalization_quality",
                expected=0.14,  # midpoint of correct range
                actual=round(mean_ratio, 4),
                unit="ratio",
                severity=severity,
                description=_describe(rule, verdict, mean_ratio, frame_count),
            ))

    return errors, assessed, skipped, details
