"""Assessment 4 — Qalqalah echo detection.

Qalqalah letters (ق ط ب ج د — IPA: q tˤ b dʒ d) bear a brief resonant
"echo" / "bounce" when they carry sukūn (no following vowel). The
reciter lightly releases the closure, producing a short burst of
energy after the consonant stop.

This assessor detects that echo from the audio:

  1. For every phone tagged with a qalqalah rule, take the phone span
     [start_ms, end_ms] (for shaddah rules, span both geminate halves).
  2. Extend the window by +50ms beyond end_ms — qalqalah echo occurs
     AFTER the closure release, so it often leaks into the next phone.
  3. Load the audio segment at 16kHz and compute RMS energy in 5ms
     frames.
  4. Find the consonant release point:
        - closure = first half of the phone span
        - release = second half; the release starts at the first frame
          where energy rises above the closure baseline.
  5. Look for an echo burst in the window 20–80ms after release:
        - peak must exceed 1.5× the closure baseline
        - echo duration = how long energy stays above 1.2× baseline
          around the peak
  6. Classify:
        peak ratio ≥ 1.5 AND duration ≥ 20ms → present  (pass)
        peak ratio ≥ 1.5 AND duration <  20ms → weak     (style for minor,
                                                          minor for major)
        peak ratio <  1.5                     → absent   (minor for minor,
                                                          major for major)

Severity mapping
----------------
  qalqalah_major:
    absent → major, weak → minor, present → pass
  qalqalah_minor, qalqalah_with_shaddah,
  qalqalah_emphatic, qalqalah_non_emphatic:
    absent → minor, weak → style,  present → pass

Skip conditions
---------------
  - alignment_confidence in {low, failed}
  - skip_assessment = True
  - effective phone duration ≤ 30ms (too short to assess)

Notes
-----
  For shaddah-bearing qalqalah letters the first phone is the silent
  closure and the second is the release; the echo begins near the end
  of the second phone. We therefore span both phones and place the
  release near the boundary between them.

  A qalqalah phone may carry multiple rules simultaneously (e.g. both
  qalqalah_major and qalqalah_non_emphatic). The acoustic detection is
  computed once per phone and classified separately for each rule.
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

# ── Qalqalah rule taxonomy ───────────────────────────────────────────
QALQALAH_RULES: set = {
    "qalqalah_major",
    "qalqalah_minor",
    "qalqalah_with_shaddah",
    "qalqalah_emphatic",
    "qalqalah_non_emphatic",
}

# Shaddah-bearing rules use the combined geminate span for detection
SHADDAH_RULES = {"qalqalah_with_shaddah"}

# ── Audio / acoustic constants ───────────────────────────────────────
SAMPLE_RATE = 16000
FRAME_MS = 5.0                   # 5ms analysis frames
FRAME_SAMPLES = 80               # 5ms at 16kHz
POST_WINDOW_MS = 100.0           # extend search +100ms past phone end
BASELINE_WINDOW_MS = 20.0        # first 20ms = closure baseline

# Echo search window (relative to release point)
ECHO_SEARCH_START_MS = 20.0
ECHO_SEARCH_END_MS = 80.0

# Echo detection thresholds (multiples of baseline)
PEAK_RATIO_THRESHOLD = 1.5       # peak must exceed 1.5× baseline
SUSTAIN_RATIO_THRESHOLD = 1.2    # duration measured above 1.2× baseline
MIN_ECHO_DURATION_MS = 20.0      # below this = "weak"

# Skip gate — too short to hold a closure + release
MIN_PHONE_DURATION_MS = 30.0

# Closure-detection gate: if baseline ≥ this fraction of the window
# max, the "closure" region is not actually silent — MFA boundaries
# are misaligned (Fix B). Phone is skipped rather than counted absent.
NO_CLOSURE_BASELINE_RATIO = 0.5


# ── Acoustic analysis result ─────────────────────────────────────────

@dataclass
class QalqalahAcoustic:
    """Result of qalqalah echo detection on a single phone span."""
    window_start_ms: float       # absolute ms of audio window start
    window_end_ms: float         # absolute ms of audio window end
    release_ms: float            # absolute ms of detected release point
    baseline_energy: float       # RMS of quietest 20ms window in closure
    peak_energy: float           # peak RMS in echo search window
    peak_ratio: float            # peak / baseline (∞ if baseline ≈ 0)
    peak_ms: float               # absolute ms of peak
    echo_duration_ms: float      # time sustained above SUSTAIN_RATIO
    echo_present: bool           # peak_ratio ≥ PEAK_RATIO_THRESHOLD
    echo_label: str              # "present" | "weak" | "absent" | "skipped"
    found: bool = True           # False if segment couldn't be loaded
    skip_reason: Optional[str] = None   # populated when echo_label=="skipped"


# ── Audio loader ─────────────────────────────────────────────────────

def _load_audio_segment(
    audio_file, start_ms: float, end_ms: float,
) -> Optional[np.ndarray]:
    """Load [start_ms, end_ms] from a WAV file at 16kHz."""
    try:
        import soundfile as sf

        start_sample = int(start_ms / 1000.0 * SAMPLE_RATE)
        end_sample = int(end_ms / 1000.0 * SAMPLE_RATE)

        info = sf.info(str(audio_file))
        total_samples = int(info.frames)
        start_sample = max(0, min(start_sample, total_samples))
        end_sample = max(start_sample, min(end_sample, total_samples))

        if end_sample - start_sample < FRAME_SAMPLES * 2:
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
        logger.warning(
            "Audio load failed for %s [%.0f–%.0f ms]: %s",
            audio_file, start_ms, end_ms, exc,
        )
        return None


# ── RMS energy per frame ─────────────────────────────────────────────

def _frame_rms(segment: np.ndarray) -> np.ndarray:
    """Return per-frame RMS energy (non-overlapping 5ms frames)."""
    n_frames = len(segment) // FRAME_SAMPLES
    if n_frames == 0:
        return np.zeros(0, dtype=np.float32)
    trimmed = segment[: n_frames * FRAME_SAMPLES]
    frames = trimmed.reshape(n_frames, FRAME_SAMPLES)
    rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    return rms.astype(np.float32)


# ── Baseline & release detection ─────────────────────────────────────

def _closure_baseline(
    rms: np.ndarray,
    closure_start_frame: int,
    closure_end_frame: int,
) -> float:
    """Return the RMS of the quietest 20ms window inside the closure.

    Robust to coarticulation from the preceding vowel (common for
    shaddah-bearing qalqalah, where the phone span begins while the
    preceding vowel is still fading). We slide a 20ms window across the
    closure region and pick the minimum-mean window as the baseline.
    """
    win = max(1, int(BASELINE_WINDOW_MS / FRAME_MS))
    lo = max(0, closure_start_frame)
    hi = min(len(rms), closure_end_frame)
    if hi - lo <= 0:
        return 0.0
    if hi - lo < win:
        return float(np.mean(rms[lo:hi]))

    best = float("inf")
    for i in range(lo, hi - win + 1):
        m = float(np.mean(rms[i : i + win]))
        if m < best:
            best = m
    return best if best != float("inf") else 0.0


def _find_release_frame(
    rms: np.ndarray,
    closure_end_frame: int,
    baseline: float,
) -> Optional[int]:
    """Find the release frame inside the phone span.

    Scan forward from the end of the closure. The release is the first
    frame F where both rms[F] and rms[F+1] exceed 2× baseline (a
    sustained rise — single-frame blips in the closure region often
    trigger a simple threshold).

    Returns the release frame index, or None if no sustained rise is
    found. A None return means "no detectable closure→release boundary
    in the MFA-defined span" — the caller should treat the phone as a
    MFA alignment artifact and skip it rather than counting an absent
    echo.

    Note: the search extends all the way to the end of the available
    RMS signal, not just to the MFA phone_end. Qalqalah bursts often
    fall slightly past the MFA boundary, because MFA tends to cut the
    phone before the release is fully articulated.
    """
    lo = max(0, closure_end_frame)
    hi = len(rms)
    if hi - lo < 2:
        return None

    threshold = baseline * 2.0
    for f in range(lo, hi - 1):
        if rms[f] > threshold and rms[f + 1] > threshold:
            return f

    return None


# ── Echo search ──────────────────────────────────────────────────────

def _measure_echo(
    rms: np.ndarray,
    release_frame: int,
    baseline: float,
) -> Tuple[float, int, float]:
    """Scan the 20–80ms window after release for an echo burst.

    Returns (peak_ratio, peak_frame, echo_duration_ms):
      peak_ratio        = max frame energy / baseline
      peak_frame        = absolute frame index of peak
      echo_duration_ms  = contiguous run around peak where energy stays
                          above SUSTAIN_RATIO_THRESHOLD × baseline
    """
    start_off = int(ECHO_SEARCH_START_MS / FRAME_MS)
    end_off = int(ECHO_SEARCH_END_MS / FRAME_MS)
    search_start = release_frame + start_off
    search_end = min(release_frame + end_off, len(rms))
    if search_start >= search_end:
        return 0.0, release_frame, 0.0

    search = rms[search_start:search_end]
    if len(search) == 0 or baseline <= 1e-9:
        return 0.0, release_frame, 0.0

    local_peak = float(np.max(search))
    local_peak_off = int(np.argmax(search))
    peak_frame = search_start + local_peak_off
    peak_ratio = local_peak / baseline

    # Measure echo duration: contiguous span around peak where energy
    # remains above SUSTAIN_RATIO_THRESHOLD × baseline. Expand from the
    # peak frame outward (both directions) using the full available
    # signal — the echo may tail past the 80ms cap.
    sustain = baseline * SUSTAIN_RATIO_THRESHOLD
    left = peak_frame
    while left - 1 >= release_frame and rms[left - 1] > sustain:
        left -= 1
    right = peak_frame
    while right + 1 < len(rms) and rms[right + 1] > sustain:
        right += 1

    duration_frames = right - left + 1
    echo_duration_ms = duration_frames * FRAME_MS
    return peak_ratio, peak_frame, echo_duration_ms


# ── Top-level detection ──────────────────────────────────────────────

def detect_qalqalah_echo(
    audio_file,
    phone_start_ms: float,
    phone_end_ms: float,
    closure_end_ms: Optional[float] = None,
) -> QalqalahAcoustic:
    """Run the full echo detection over a phone span.

    phone_start_ms / phone_end_ms are the phone boundaries (or combined
    geminate span for shaddah rules). The search window is extended
    +50ms past phone_end_ms to catch the echo tail.

    closure_end_ms marks the end of the silent closure region and the
    start of the release region:
      - For shaddah rules, pass the boundary between the first and
        second geminate phones (end of first phone).
      - For non-shaddah rules, leave as None — the closure is assumed
        to occupy the first half of the phone.
    """
    window_start_ms = max(0.0, phone_start_ms)
    window_end_ms = phone_end_ms + POST_WINDOW_MS

    segment = _load_audio_segment(audio_file, window_start_ms, window_end_ms)
    if segment is None:
        return QalqalahAcoustic(
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            release_ms=phone_start_ms,
            baseline_energy=0.0,
            peak_energy=0.0,
            peak_ratio=0.0,
            peak_ms=phone_start_ms,
            echo_duration_ms=0.0,
            echo_present=False,
            echo_label="absent",
            found=False,
        )

    rms = _frame_rms(segment)
    if len(rms) < 4:
        return QalqalahAcoustic(
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            release_ms=phone_start_ms,
            baseline_energy=0.0,
            peak_energy=0.0,
            peak_ratio=0.0,
            peak_ms=phone_start_ms,
            echo_duration_ms=0.0,
            echo_present=False,
            echo_label="absent",
            found=False,
        )

    # Frame indices (relative to window_start_ms)
    phone_start_frame = 0
    phone_dur_frames = int((phone_end_ms - phone_start_ms) / FRAME_MS)
    phone_end_frame = min(phone_start_frame + phone_dur_frames, len(rms))
    if phone_end_frame - phone_start_frame < 2:
        phone_end_frame = min(phone_start_frame + 2, len(rms))

    # Closure region: from phone start up to closure_end_ms, or to the
    # midpoint if not provided.
    if closure_end_ms is not None:
        closure_end_frame = int((closure_end_ms - phone_start_ms) / FRAME_MS)
        closure_end_frame = max(
            phone_start_frame + 1,
            min(closure_end_frame, phone_end_frame),
        )
    else:
        closure_end_frame = (phone_start_frame + phone_end_frame) // 2
        closure_end_frame = max(phone_start_frame + 1, closure_end_frame)

    # Baseline = quietest 20ms window inside the closure region.
    # Using min rather than first-20ms avoids residual energy from the
    # preceding vowel (a common coarticulation artifact, especially
    # around shaddah-bearing qalqalah letters).
    baseline = _closure_baseline(rms, phone_start_frame, closure_end_frame)

    # ── Fix B: no-closure gate ──────────────────────────────────────
    # A real qalqalah closure is substantially quieter than the max
    # energy in the phone span. If the baseline is within 0.5× of the
    # window max, the "closure" region is not actually silent — MFA
    # has misaligned the phone boundaries into the middle of a voiced
    # region. Skip rather than mark absent.
    window_max = float(np.max(rms)) if len(rms) else 0.0
    if window_max > 1e-9 and baseline >= NO_CLOSURE_BASELINE_RATIO * window_max:
        return QalqalahAcoustic(
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            release_ms=phone_start_ms,
            baseline_energy=baseline,
            peak_energy=window_max,
            peak_ratio=(window_max / baseline) if baseline > 1e-9 else 0.0,
            peak_ms=phone_start_ms,
            echo_duration_ms=0.0,
            echo_present=False,
            echo_label="skipped",
            found=True,
            skip_reason="no_closure_detected",
        )

    # Find release frame (first sustained energy rise past closure end)
    release_frame = _find_release_frame(rms, closure_end_frame, baseline)

    # ── Fix A: no-release gate ──────────────────────────────────────
    # If nothing in the post-closure region sustains a 2× rise, there
    # is no detectable release burst inside the MFA span. Treat as an
    # alignment artifact and skip rather than count as absent echo.
    if release_frame is None:
        return QalqalahAcoustic(
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            release_ms=phone_start_ms,
            baseline_energy=baseline,
            peak_energy=window_max,
            peak_ratio=(window_max / baseline) if baseline > 1e-9 else 0.0,
            peak_ms=phone_start_ms,
            echo_duration_ms=0.0,
            echo_present=False,
            echo_label="skipped",
            found=True,
            skip_reason="no_closure_detected",
        )

    # ── Fix C: echo search window overflow ─────────────────────────
    # If the release was detected so close to the end of the audio
    # window that the echo search range [release+20ms, release+80ms]
    # starts past the last frame, there is nothing to measure. This
    # happens when MFA places the phone boundary before the real
    # release burst and the +50ms post-extension is not enough.
    echo_search_start_frame = release_frame + int(ECHO_SEARCH_START_MS / FRAME_MS)
    if echo_search_start_frame >= len(rms):
        return QalqalahAcoustic(
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            release_ms=window_start_ms + release_frame * FRAME_MS,
            baseline_energy=baseline,
            peak_energy=window_max,
            peak_ratio=(window_max / baseline) if baseline > 1e-9 else 0.0,
            peak_ms=window_start_ms + release_frame * FRAME_MS,
            echo_duration_ms=0.0,
            echo_present=False,
            echo_label="skipped",
            found=True,
            skip_reason="echo_window_overflow",
        )

    # Search for echo burst
    peak_ratio, peak_frame, echo_duration_ms = _measure_echo(
        rms, release_frame, baseline,
    )
    peak_energy = float(rms[peak_frame]) if peak_frame < len(rms) else 0.0

    # Classify
    if peak_ratio >= PEAK_RATIO_THRESHOLD:
        if echo_duration_ms >= MIN_ECHO_DURATION_MS:
            label = "present"
            present = True
        else:
            label = "weak"
            present = True
    else:
        label = "absent"
        present = False

    return QalqalahAcoustic(
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        release_ms=window_start_ms + release_frame * FRAME_MS,
        baseline_energy=baseline,
        peak_energy=peak_energy,
        peak_ratio=peak_ratio,
        peak_ms=window_start_ms + peak_frame * FRAME_MS,
        echo_duration_ms=echo_duration_ms,
        echo_present=present,
        echo_label=label,
        found=True,
    )


# ── Severity classification ──────────────────────────────────────────

def _severity_for_rule(rule: str, label: str) -> Optional[str]:
    """Map (rule, echo_label) → severity or None (pass).

    qalqalah_major:        absent→major, weak→minor,  present→pass
    all other qalqalah_*:  absent→minor, weak→style,  present→pass
    """
    if label == "present":
        return None
    if rule == "qalqalah_major":
        return "major" if label == "absent" else "minor"
    return "minor" if label == "absent" else "style"


def _describe(
    rule: str,
    acoustic: QalqalahAcoustic,
    severity: Optional[str],
) -> str:
    display = rule.replace("_", " ").title()
    if acoustic.echo_label == "absent":
        return (
            f"{display} echo absent — peak ratio "
            f"{acoustic.peak_ratio:.2f}× baseline "
            f"(threshold {PEAK_RATIO_THRESHOLD}×)"
        )
    if acoustic.echo_label == "weak":
        return (
            f"{display} echo weak — burst only "
            f"{acoustic.echo_duration_ms:.0f}ms "
            f"(minimum {MIN_ECHO_DURATION_MS:.0f}ms)"
        )
    return (
        f"{display} echo present — "
        f"{acoustic.echo_duration_ms:.0f}ms at "
        f"{acoustic.peak_ratio:.2f}× baseline"
    )


# ── Geminate span helper ─────────────────────────────────────────────

def _geminate_span_ms(
    phone: Phone,
    flat: List[Tuple[Word, Phone]],
    idx: int,
) -> Tuple[float, float]:
    """For shaddah rules, return span covering both geminate halves."""
    if not phone.geminate_pair:
        return phone.start * 1000, phone.end * 1000

    if phone.geminate_position == "first":
        if idx + 1 < len(flat):
            _, nxt = flat[idx + 1]
            if nxt.geminate_pair and nxt.geminate_position == "second":
                return phone.start * 1000, nxt.end * 1000
    elif phone.geminate_position == "second":
        if idx - 1 >= 0:
            _, prv = flat[idx - 1]
            if prv.geminate_pair and prv.geminate_position == "first":
                return prv.start * 1000, phone.end * 1000

    return phone.start * 1000, phone.end * 1000


# ── Assessment entry point ───────────────────────────────────────────

def assess_qalqalah(
    verse: Verse,
    cal: CalibrationResult,
    load_audio: bool = True,
    collect_details: bool = False,
) -> Tuple[List[AssessmentError], int, int, List[dict]]:
    """Assess every qalqalah phone in a verse.

    Returns (errors, phones_assessed, phones_skipped, details).

    `details` is a list of per-phone dicts (one per rule instance)
    matching the schema requested in the task spec:
        {
          "rule", "echo_present", "echo_duration_ms",
          "echo_peak_ratio", "assessment", "severity",
          "word", "ayah", "phone", "phone_index"
        }
    Populated only when collect_details=True (used by the reporting
    script); disabled by default for pipeline runs.
    """
    errors: List[AssessmentError] = []
    details: List[dict] = []
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
            r for r in phone.tajweed_rules if r in QALQALAH_RULES
        ]
        if not rules_on_phone:
            continue

        # For geminate pairs, only assess the "first" phone (the closure
        # — the second phone is the release of the same consonant).
        if phone.geminate_pair and phone.geminate_position == "second":
            continue

        # Skip: low/failed confidence or explicitly flagged
        if phone.skip_assessment or phone.alignment_confidence in (
            "low", "failed",
        ):
            skipped += 1
            continue

        # Compute effective span
        is_shaddah = any(r in SHADDAH_RULES for r in rules_on_phone)
        closure_end_ms: Optional[float] = None
        if is_shaddah:
            span_start, span_end = _geminate_span_ms(phone, flat, i)
            # Closure = the first phone of the geminate pair
            closure_end_ms = phone.end * 1000
        else:
            span_start = phone.start * 1000
            span_end = phone.end * 1000
        effective_duration_ms = span_end - span_start

        # Skip: too short to hold a meaningful closure + release
        if effective_duration_ms <= MIN_PHONE_DURATION_MS:
            skipped += 1
            continue

        # Acoustic echo detection (shared across all rules on this phone)
        acoustic: Optional[QalqalahAcoustic] = None
        if load_audio and wav_file is not None:
            acoustic = detect_qalqalah_echo(
                wav_file, span_start, span_end, closure_end_ms,
            )

        if acoustic is None or not acoustic.found:
            skipped += 1
            continue

        # Fixes A+B: no closure or no release detected → MFA alignment
        # artifact. Skip the phone (do NOT count as absent echo) and
        # record the reason so it shows up in validation reports.
        if acoustic.echo_label == "skipped":
            skipped += 1
            if collect_details:
                for rule in rules_on_phone:
                    details.append({
                        "surah": verse.surah,
                        "ayah": verse.ayah,
                        "word": word.text,
                        "phone": phone.ipa,
                        "phone_index": i,
                        "rule": rule,
                        "echo_present": False,
                        "echo_label": "skipped",
                        "echo_duration_ms": 0.0,
                        "echo_peak_ratio": round(acoustic.peak_ratio, 3),
                        "assessment": "skipped",
                        "severity": None,
                        "skip_reason": acoustic.skip_reason,
                    })
            continue

        # Emit one assessment per rule on this phone
        for rule in rules_on_phone:
            assessed += 1
            severity = _severity_for_rule(rule, acoustic.echo_label)

            if collect_details:
                details.append({
                    "surah": verse.surah,
                    "ayah": verse.ayah,
                    "word": word.text,
                    "phone": phone.ipa,
                    "phone_index": i,
                    "rule": rule,
                    "echo_present": acoustic.echo_present,
                    "echo_label": acoustic.echo_label,
                    "echo_duration_ms": round(acoustic.echo_duration_ms, 1),
                    "echo_peak_ratio": round(acoustic.peak_ratio, 3),
                    "assessment": "pass" if severity is None else severity,
                    "severity": severity,
                })

            if severity is None:
                continue

            errors.append(AssessmentError(
                word=word.text,
                phone=phone.ipa,
                phone_index=i,
                timestamp_ms=phone.start * 1000,
                rule=rule,
                assessment="echo",
                expected=PEAK_RATIO_THRESHOLD,
                actual=round(acoustic.peak_ratio, 3),
                unit="ratio",
                severity=severity,
                description=_describe(rule, acoustic, severity),
            ))

    return errors, assessed, skipped, details
