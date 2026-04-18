"""Assessment 5 — Tafkhim (emphasis / heaviness) F2 checker.

Scope:
  Tafkhim (تفخيم, "heaviness") is the articulatory emphasis applied to
  the Arabic heavy letters — inherently: ص ض ط ظ (sˤ dˤ tˤ ðˤ), and
  contextually: ر (rˤ), plus ق خ غ (q x ɣ) which are also classically
  counted among the emphatics. When produced correctly, the back of
  the tongue is raised toward the velum/uvula, which acoustically
  lowers F2 (second formant). A low F2 on a heavy phone = correct
  tafkhim. A high F2 = the student is pronouncing the letter "lightly"
  (tarqiq — تَرقيق error).

  This assessor ONLY handles phones whose tajweed_rules list contains
  the literal token "tafkhim". It does not infer tafkhim targets from
  IPA alone, and it does not overlap with emphatic_backing_rules (which
  concern adjacent *vowel* backing, not the heavy consonant itself).

Method:
  For each phone tagged "tafkhim":
    1. Load the WAV file with parselmouth (Praat wrapper)
    2. Extract a Burg formant object (5 formants, 5500 Hz max — tuned
       for male reciters)
    3. Sample F2 at the phone midpoint ((start+end)/2)
    4. Compare to thresholds and emit a verdict

Thresholds (PROVISIONAL — pending empirical calibration on reciter_2):
    F2 < 1200 Hz           → correct tafkhim (pass)
    1200 ≤ F2 ≤ 1500 Hz    → borderline — minor error
    F2 > 1500 Hz           → tarqiq error — major error

Skip conditions:
    - skip_assessment = True
    - alignment_confidence in {low, failed}
    - duration_ms <= 20 (too short for a reliable F2 read)
    - parselmouth returns NaN/undefined at the midpoint
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from phase3_assessment.models import (
    AssessmentError,
    CalibrationResult,
    Phone,
    Verse,
    Word,
)
from phase3_assessment.utils.loader import audio_path

logger = logging.getLogger(__name__)

# ── Rules handled by this assessor ──────────────────────────────────
TAFKHIM_RULES = {"tafkhim"}

# ── Parselmouth / formant extraction parameters ─────────────────────
# Tuned for male reciters; 5500 Hz ceiling is Praat's standard male
# male-voice setting for to_formant_burg.
MAX_FORMANTS = 5.0
MAX_FORMANT_FREQ_HZ = 5500.0

# ── F2 thresholds (provisional — calibrate empirically) ─────────────
F2_CORRECT_CEILING_HZ = 1200.0   # F2 < 1200 → pass
F2_BORDERLINE_CEILING_HZ = 1500.0  # 1200 ≤ F2 ≤ 1500 → borderline / minor
# F2 > 1500 → tarqiq error / major

# ── Skip gate — too short for reliable F2 ──────────────────────────
MIN_PHONE_DURATION_MS = 20.0


# ── Result dataclass ────────────────────────────────────────────────

@dataclass
class TafkhimResult:
    """Per-phone tafkhim F2 result."""
    phone_index: int
    word: str
    ipa: str
    tajweed_rule: str
    start_ms: float
    end_ms: float
    duration_ms: float
    verdict: str        # "pass" | "borderline" | "tarqiq_error" | "skipped"
    severity: str       # "pass" | "minor" | "major" | "skipped"
    f2_hz: float        # measured F2 at midpoint (0.0 if unmeasurable)
    skip_reason: Optional[str] = None


# ── F2 extraction via parselmouth ───────────────────────────────────

def _extract_f2_at_midpoint(
    audio_file, start_ms: float, end_ms: float,
) -> Optional[float]:
    """Return F2 (Hz) at the phone midpoint, or None if unavailable.

    Loads the full WAV (parselmouth caches this reasonably well) and
    asks Praat for the Burg formant object, then samples F2 at the
    midpoint in seconds. Praat returns NaN (``undefined``) when F2 is
    indeterminable — we map that to None.
    """
    try:
        import parselmouth
    except ImportError:
        logger.error("parselmouth not installed — cannot assess tafkhim")
        return None

    try:
        sound = parselmouth.Sound(str(audio_file))
        formant = sound.to_formant_burg(
            max_number_of_formants=MAX_FORMANTS,
            maximum_formant=MAX_FORMANT_FREQ_HZ,
        )
        mid_s = (start_ms + end_ms) / 2000.0
        f2 = formant.get_value_at_time(formant_number=2, time=mid_s)
        if f2 is None:
            return None
        # Praat returns NaN for undefined frames
        if f2 != f2:  # NaN check
            return None
        return float(f2)
    except Exception as exc:
        logger.warning(
            "parselmouth F2 failed for %s [%.0f-%.0f ms]: %s",
            audio_file, start_ms, end_ms, exc,
        )
        return None


# ── Verdict / severity mapping ──────────────────────────────────────

def _verdict_severity(f2_hz: float) -> Tuple[str, str]:
    """Classify a measured F2 against tafkhim thresholds.

    F2 < 1200        → ("pass",          "pass")
    1200 ≤ F2 ≤ 1500 → ("borderline",    "minor")
    F2 > 1500        → ("tarqiq_error",  "major")
    """
    if f2_hz < F2_CORRECT_CEILING_HZ:
        return "pass", "pass"
    if f2_hz <= F2_BORDERLINE_CEILING_HZ:
        return "borderline", "minor"
    return "tarqiq_error", "major"


def _describe(verdict: str, f2_hz: float) -> str:
    if verdict == "tarqiq_error":
        return (
            f"Tafkhim — tarqiq error, heavy letter pronounced lightly "
            f"(F2={f2_hz:.0f} Hz, threshold>{F2_BORDERLINE_CEILING_HZ:.0f})"
        )
    if verdict == "borderline":
        return (
            f"Tafkhim — borderline, emphasis weaker than expected "
            f"(F2={f2_hz:.0f} Hz, correct<{F2_CORRECT_CEILING_HZ:.0f})"
        )
    return (
        f"Tafkhim — correct emphasis "
        f"(F2={f2_hz:.0f} Hz)"
    )


# ── Main assessment function ────────────────────────────────────────

def assess_tafkhim(
    verse: Verse,
    cal: CalibrationResult,
    load_audio: bool = True,
    collect_details: bool = False,
) -> Tuple[List[AssessmentError], int, int, List[TafkhimResult]]:
    """Assess F2-based tafkhim on all 'tafkhim'-tagged phones in a verse.

    Returns (errors, phones_assessed, phones_skipped, details).

    `details` is populated only when collect_details=True (for test /
    reporting scripts); disabled by default for pipeline runs.
    """
    errors: List[AssessmentError] = []
    details: List[TafkhimResult] = []
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
            r for r in phone.tajweed_rules if r in TAFKHIM_RULES
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
        skip_reason: Optional[str] = None
        if phone.skip_assessment:
            skip_reason = "skip_assessment=True"
        elif phone.alignment_confidence in ("low", "failed"):
            skip_reason = f"alignment_confidence={phone.alignment_confidence}"
        elif duration_ms <= MIN_PHONE_DURATION_MS:
            skip_reason = f"duration_ms={duration_ms:.1f} <= {MIN_PHONE_DURATION_MS}"

        if skip_reason is not None:
            skipped += 1
            if collect_details:
                for rule in rules_on_phone:
                    details.append(TafkhimResult(
                        phone_index=i,
                        word=word.text,
                        ipa=phone.ipa,
                        tajweed_rule=rule,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        duration_ms=duration_ms,
                        verdict="skipped",
                        severity="skipped",
                        f2_hz=0.0,
                        skip_reason=skip_reason,
                    ))
            continue

        # ── Acoustic analysis ───────────────────────────────────────
        f2_hz: Optional[float] = None
        if load_audio and wav_file is not None:
            f2_hz = _extract_f2_at_midpoint(wav_file, start_ms, end_ms)

        if f2_hz is None:
            skipped += 1
            if collect_details:
                for rule in rules_on_phone:
                    details.append(TafkhimResult(
                        phone_index=i,
                        word=word.text,
                        ipa=phone.ipa,
                        tajweed_rule=rule,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        duration_ms=duration_ms,
                        verdict="skipped",
                        severity="skipped",
                        f2_hz=0.0,
                        skip_reason="f2_undefined",
                    ))
            continue

        # ── Per-rule assessment ─────────────────────────────────────
        for rule in rules_on_phone:
            assessed += 1
            verdict, severity = _verdict_severity(f2_hz)

            if collect_details:
                details.append(TafkhimResult(
                    phone_index=i,
                    word=word.text,
                    ipa=phone.ipa,
                    tajweed_rule=rule,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    duration_ms=duration_ms,
                    verdict=verdict,
                    severity=severity,
                    f2_hz=round(f2_hz, 1),
                ))

            if verdict == "pass":
                continue

            errors.append(AssessmentError(
                word=word.text,
                phone=phone.ipa,
                phone_index=i,
                timestamp_ms=start_ms,
                rule=rule,
                assessment="formant",
                expected=F2_CORRECT_CEILING_HZ,
                actual=round(f2_hz, 1),
                unit="hz",
                severity=severity,
                description=_describe(verdict, f2_hz),
            ))

    return errors, assessed, skipped, details
