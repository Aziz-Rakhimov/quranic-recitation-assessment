"""Assessment 2 — Ghunnah duration + nasalization checker.

For each phone with a ghunnah-related tajweed rule, this assessor:

PART A — Duration (acoustic boundary detection):
  MFA phone boundaries for nasal consonants are unreliable — MFA absorbs
  surrounding vowels into the nasal phone, inflating duration by 3–5x.

  Instead of using MFA start_ms/end_ms directly, we detect the true nasal
  segment boundaries from the audio:

  1. Take search window = MFA boundaries [mfa_start, mfa_end]
     (no extension — neighboring vowels are nasalized by coarticulation
     and would inflate the detected segment)
  2. Load audio in this window at 16kHz
  3. Compute frame-by-frame nasality ratio:
       nasality[t] = nasal_band_energy(200–400Hz) / total_band_energy(200–4000Hz)
     using 10ms frames (160 samples)
  4. Find nasal segment boundaries:
       START = first frame with nasality > threshold sustained for ≥3 frames
       END   = last frame with nasality > threshold preceded by ≥3 sustained
  5. true_ghunnah_duration = nasal_end - nasal_start

PART B — Nasalization:
  Peak nasality ratio from the detected segment determines presence/absence.

Guards (same as madd assessor):
  - Skip alignment_confidence=low or failed
  - Skip skip_assessment=true
  - MFA resolution exemption (within 30ms of boundary → downgrade)
  - Near-floor exemption (≤ floor_ms + 30ms → style)
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
from phase3_assessment.f0_tracker import track_f0, F0Result

logger = logging.getLogger(__name__)

# ── Expected counts per ghunnah rule ─────────────────────────────────
GHUNNAH_RULES: Dict[str, float] = {
    "ghunnah_mushaddadah_noon": 2.0,
    "ghunnah_mushaddadah_meem": 2.0,
    "idgham_ghunnah_noon":     2.0,
    "iqlab":                   2.0,
    "ikhfaa_light":            1.5,
    "ikhfaa_heavy":            1.5,
}

# Shaddah (geminate) rules — use geminate span for search window
SHADDAH_RULES = {"ghunnah_mushaddadah_noon", "ghunnah_mushaddadah_meem"}

# ── Tartil-aware duration thresholds ─────────────────────────────────
# Mushaddadah / idgham (2-count target):
#   < 0.8c  = major   (ghunnah almost absent)
#   0.8–1.2 = minor   (too brief)
#   1.2–2.8 = pass    (standard 2-count ghunnah)
#   2.8–8.0 = style   (tartil elongation — correct articulation, slow)
#   8.0–12  = minor   (exceptionally long, worth noting)
#   > 12    = major   (likely MFA pause absorption)
#
# Ikhfaa (1.5-count target):
#   < 0.6c  = major
#   0.6–1.0 = minor
#   1.0–3.0 = pass
#   3.0–7.0 = style   (tartil)
#   > 7.0   = minor   (likely pause absorption)

# MFA resolution floor
MFA_FRAME_MS = 30.0

# Hard ceiling: duration above this is almost certainly MFA pause absorption
PAUSE_ABSORPTION_CEILING_MS = 1500.0

# ── Audio / acoustic detection constants ─────────────────────────────
SAMPLE_RATE = 16000
FRAME_SAMPLES = 160          # 10ms at 16kHz
FRAME_MS = 10.0
FFT_WINDOW_SIZE = 512        # 32ms at 16kHz for FFT
SEARCH_MARGIN_MS = 0.0       # search within MFA boundaries only
                              # (±100ms extension leaked into nasalized
                              # neighboring vowels via coarticulation)

# Frequency bands for nasality ratio
NASAL_BAND_LOW_HZ = 200
NASAL_BAND_HIGH_HZ = 400
TOTAL_BAND_LOW_HZ = 200
TOTAL_BAND_HIGH_HZ = 4000

# Nasality detection thresholds
NASALITY_ONSET_THRESHOLD = 0.12   # frame nasality must exceed this
SUSTAINED_FRAMES = 3              # must be sustained for ≥3 frames (30ms)
MIN_NASAL_DURATION_MS = 50.0      # segments < 50ms are noise

# Nasalization assessment thresholds (peak ratio)
NASAL_PRESENT_THRESHOLD = 0.15
NASAL_ABSENT_THRESHOLD = 0.08

# F0 borderline range — phones flagged "minor" because they sit in the
# 8–12 harakah window are a known mix of (a) genuine tartil ghunnah held
# unusually long and (b) MFA absorbing surrounding silence/breath into
# the nasal phone. F0 stability separates them: stable voiced F0 across
# the region confirms genuine sustained phonation (keep as minor); the
# absence of stable voicing implies the long duration is a measurement
# artifact and the phone is downgraded to style so the reciter is not
# penalized for an MFA error.
F0_BORDERLINE_LO_COUNTS = 8.0
F0_BORDERLINE_HI_COUNTS = 12.0


# ── Per-phone debugging result ───────────────────────────────────────

@dataclass
class GhunnahResult:
    """Per-phone ghunnah assessment detail.

    Populated only when assess_ghunnah is called with collect_details=True
    (e.g., from test_f0.py). The standard pipeline path returns just
    the (errors, assessed, skipped) triple and never builds this list.

    Fields:
      severity         : final severity emitted (None = pass)
      pre_f0_severity  : severity before the F0 borderline check ran
                         (equal to severity unless F0 changed it)
      f0_checked       : True if the F0 borderline check ran on this phone
      f0_confirmed     : True  → stable voiced F0 → kept as minor
                         False → unstable/unvoiced → downgraded to style
                         None  → F0 check did not run
      voiced_fraction / f0_std_hz / is_voiced / is_stable :
                         raw F0Result fields, populated only when
                         f0_checked is True. None otherwise.
    """
    word: str
    phone: str
    phone_index: int
    rule: str
    duration_ms: float
    actual_counts: float
    severity: Optional[str]
    pre_f0_severity: Optional[str] = None
    f0_checked: bool = False
    f0_confirmed: Optional[bool] = None
    voiced_fraction: Optional[float] = None
    f0_std_hz: Optional[float] = None
    is_voiced: Optional[bool] = None
    is_stable: Optional[bool] = None


# ── Acoustic analysis result ─────────────────────────────────────────

@dataclass
class AcousticResult:
    """Result of acoustic nasal boundary detection."""
    nasal_start_ms: float       # true nasal start (absolute in audio)
    nasal_end_ms: float         # true nasal end (absolute in audio)
    acoustic_duration_ms: float # nasal_end - nasal_start
    peak_nasality: float        # peak nasality ratio in detected segment
    mean_nasality: float        # mean nasality ratio in detected segment
    boundary_corrected: bool    # True if acoustic ≠ MFA
    mfa_duration_ms: float      # original MFA-based duration
    found: bool = True          # False if no nasal segment detected


# ── Ikhfaa rules (use separate thresholds) ──────────────────────────
IKHFAA_RULES = {"ikhfaa_light", "ikhfaa_heavy"}


# ── Tartil-aware duration severity ──────────────────────────────────

def _duration_severity_2count(actual_counts: float) -> Optional[str]:
    """Tartil-aware severity for 2-count ghunnah rules.

    mushaddadah_noon/meem, idgham_ghunnah_noon, iqlab.

    < 0.8   : major  (ghunnah almost absent)
    0.8–1.2 : minor  (too brief)
    1.2–2.8 : pass   (standard 2-count ghunnah)
    2.8–8.0 : style  (tartil elongation)
    8.0–12  : minor  (exceptionally long)
    > 12    : major  (likely MFA pause absorption)
    """
    if actual_counts < 0.8:
        return "major"
    if actual_counts < 1.2:
        return "minor"
    if actual_counts <= 2.8:
        return None
    if actual_counts <= 8.0:
        return "style"
    if actual_counts <= 12.0:
        return "minor"
    return "major"


def _duration_severity_ikhfaa(actual_counts: float) -> Optional[str]:
    """Tartil-aware severity for 1.5-count ikhfaa rules.

    < 0.6   : major
    0.6–1.0 : minor
    1.0–3.0 : pass
    3.0–7.0 : style  (tartil)
    > 7.0   : minor  (likely pause absorption)
    """
    if actual_counts < 0.6:
        return "major"
    if actual_counts < 1.0:
        return "minor"
    if actual_counts <= 3.0:
        return None
    if actual_counts <= 7.0:
        return "style"
    return "minor"


def _duration_severity(
    actual_counts: float,
    rule: str,
) -> Optional[str]:
    """Route to rule-type-specific severity function."""
    if rule in IKHFAA_RULES:
        return _duration_severity_ikhfaa(actual_counts)
    return _duration_severity_2count(actual_counts)


# ── Audio loading ───────────────────────────────────────────────────

def _load_audio_segment(
    audio_file, start_ms: float, end_ms: float,
) -> Optional[np.ndarray]:
    """Load a segment of audio from a WAV file."""
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
        logger.warning("Audio load failed for %s [%.0f–%.0f ms]: %s",
                       audio_file, start_ms, end_ms, exc)
        return None


# ── Acoustic nasal boundary detection ───────────────────────────────

def _compute_frame_nasality(segment: np.ndarray) -> List[float]:
    """Compute per-frame nasality ratio (10ms frames, 512-pt FFT).

    nasality[t] = energy(200–400Hz) / energy(200–4000Hz)

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


def _find_nasal_boundaries(
    nasality: List[float],
    threshold: float = NASALITY_ONSET_THRESHOLD,
    min_sustained: int = SUSTAINED_FRAMES,
) -> Optional[Tuple[int, int]]:
    """Find start and end frame indices of the nasal segment.

    START: first frame where nasality > threshold AND sustained for
           at least min_sustained consecutive frames.
    END:   last frame where nasality > threshold AND followed by
           at least min_sustained frames below threshold.

    Returns (start_frame, end_frame) or None if no segment found.
    """
    n = len(nasality)
    if n < min_sustained:
        return None

    # Build boolean mask: True where nasality exceeds threshold
    above = [r > threshold for r in nasality]

    # Find runs of True values
    runs: List[Tuple[int, int]] = []  # (start, end) inclusive
    i = 0
    while i < n:
        if above[i]:
            run_start = i
            while i < n and above[i]:
                i += 1
            run_end = i - 1
            runs.append((run_start, run_end))
        else:
            i += 1

    if not runs:
        return None

    # Filter: only keep runs with length ≥ min_sustained
    valid_runs = [(s, e) for s, e in runs if (e - s + 1) >= min_sustained]
    if not valid_runs:
        return None

    # Merge runs that are separated by ≤2 frames (20ms gap — brief dips)
    merged = [valid_runs[0]]
    for s, e in valid_runs[1:]:
        prev_s, prev_e = merged[-1]
        if s - prev_e <= 2:
            merged[-1] = (prev_s, e)
        else:
            merged.append((s, e))

    # Take the longest merged run as the primary nasal segment
    best = max(merged, key=lambda r: r[1] - r[0])
    return best


def detect_nasal_boundaries(
    audio_file,
    mfa_start_ms: float,
    mfa_end_ms: float,
    mfa_duration_ms: float,
) -> AcousticResult:
    """Detect true nasal segment boundaries from audio.

    1. Extend MFA window by ±100ms
    2. Compute per-frame nasality ratio
    3. Find sustained nasal segment
    4. Return acoustic duration
    """
    search_start_ms = max(0.0, mfa_start_ms - SEARCH_MARGIN_MS)
    search_end_ms = mfa_end_ms + SEARCH_MARGIN_MS

    segment = _load_audio_segment(audio_file, search_start_ms, search_end_ms)
    if segment is None or len(segment) < FRAME_SAMPLES:
        return AcousticResult(
            nasal_start_ms=mfa_start_ms,
            nasal_end_ms=mfa_end_ms,
            acoustic_duration_ms=mfa_duration_ms,
            peak_nasality=0.0,
            mean_nasality=0.0,
            boundary_corrected=False,
            mfa_duration_ms=mfa_duration_ms,
            found=False,
        )

    # Compute per-frame nasality
    nasality = _compute_frame_nasality(segment)
    if not nasality:
        return AcousticResult(
            nasal_start_ms=mfa_start_ms,
            nasal_end_ms=mfa_end_ms,
            acoustic_duration_ms=mfa_duration_ms,
            peak_nasality=0.0,
            mean_nasality=0.0,
            boundary_corrected=False,
            mfa_duration_ms=mfa_duration_ms,
            found=False,
        )

    # Find nasal boundaries
    bounds = _find_nasal_boundaries(nasality)
    if bounds is None:
        # No sustained nasal segment — nasalization absent
        peak = max(nasality) if nasality else 0.0
        mean = float(np.mean(nasality)) if nasality else 0.0
        return AcousticResult(
            nasal_start_ms=mfa_start_ms,
            nasal_end_ms=mfa_end_ms,
            acoustic_duration_ms=mfa_duration_ms,
            peak_nasality=peak,
            mean_nasality=mean,
            boundary_corrected=False,
            mfa_duration_ms=mfa_duration_ms,
            found=False,
        )

    start_frame, end_frame = bounds

    # Convert frame indices to absolute ms
    nasal_start_ms = search_start_ms + start_frame * FRAME_MS
    nasal_end_ms = search_start_ms + (end_frame + 1) * FRAME_MS
    acoustic_duration_ms = nasal_end_ms - nasal_start_ms

    # Nasality statistics within detected segment
    segment_nasality = nasality[start_frame : end_frame + 1]
    peak = max(segment_nasality)
    mean = float(np.mean(segment_nasality))

    # Too short to be real ghunnah?
    if acoustic_duration_ms < MIN_NASAL_DURATION_MS:
        return AcousticResult(
            nasal_start_ms=nasal_start_ms,
            nasal_end_ms=nasal_end_ms,
            acoustic_duration_ms=acoustic_duration_ms,
            peak_nasality=peak,
            mean_nasality=mean,
            boundary_corrected=True,
            mfa_duration_ms=mfa_duration_ms,
            found=False,
        )

    boundary_corrected = (
        abs(acoustic_duration_ms - mfa_duration_ms) > FRAME_MS
    )

    return AcousticResult(
        nasal_start_ms=nasal_start_ms,
        nasal_end_ms=nasal_end_ms,
        acoustic_duration_ms=acoustic_duration_ms,
        peak_nasality=peak,
        mean_nasality=mean,
        boundary_corrected=boundary_corrected,
        mfa_duration_ms=mfa_duration_ms,
        found=True,
    )


# ── Nasalization severity ───────────────────────────────────────────

def _nasalization_severity(ratio: float) -> Optional[str]:
    """Assess nasalization from peak ratio.

    > 0.15 : present (pass)
    0.08–0.15 : uncertain (style)
    < 0.08 : absent (major error)
    """
    if ratio >= NASAL_PRESENT_THRESHOLD:
        return None
    if ratio >= NASAL_ABSENT_THRESHOLD:
        return "style"
    return "major"


def _nasalization_label(ratio: float) -> str:
    if ratio >= NASAL_PRESENT_THRESHOLD:
        return "present"
    if ratio >= NASAL_ABSENT_THRESHOLD:
        return "uncertain"
    return "absent"


# ── Description helpers ──────────────────────────────────────────────

def _describe_duration(
    rule: str, actual: float, note: str = "",
) -> str:
    display = rule.replace("_", " ").replace("ghunnah ", "").title()
    if rule in IKHFAA_RULES:
        lo, hi = 1.0, 3.0
    else:
        lo, hi = 1.2, 2.8
    direction = "too short" if actual < lo else "too long"
    base = (f"Ghunnah {display} {direction} — held {actual:.1f} counts, "
            f"expected {lo}–{hi}")
    return f"{base} [{note}]" if note else base


def _describe_nasalization(
    rule: str, ratio: float, label: str,
) -> str:
    display = rule.replace("_", " ").replace("ghunnah ", "").title()
    if label == "absent":
        return (f"Ghunnah nasalization missing on {display} "
                f"(ratio={ratio:.3f}, threshold={NASAL_PRESENT_THRESHOLD})")
    return (f"Ghunnah nasalization weak on {display} "
            f"(ratio={ratio:.3f}, range {NASAL_ABSENT_THRESHOLD}–"
            f"{NASAL_PRESENT_THRESHOLD})")


# ── Geminate span helper ────────────────────────────────────────────

def _geminate_span_ms(
    phone: Phone,
    flat: List[Tuple[Word, Phone]],
    idx: int,
) -> Tuple[float, float]:
    """Return (start_ms, end_ms) covering both phones of a geminate pair."""
    if not phone.geminate_pair:
        return phone.start * 1000, phone.end * 1000

    if phone.geminate_position == "first":
        if idx + 1 < len(flat):
            _, next_p = flat[idx + 1]
            if next_p.geminate_pair and next_p.geminate_position == "second":
                return phone.start * 1000, next_p.end * 1000
    elif phone.geminate_position == "second":
        if idx - 1 >= 0:
            _, prev_p = flat[idx - 1]
            if prev_p.geminate_pair and prev_p.geminate_position == "first":
                return prev_p.start * 1000, phone.end * 1000

    return phone.start * 1000, phone.end * 1000


# ── Main assessment function ────────────────────────────────────────

def assess_ghunnah(
    verse: Verse,
    cal: CalibrationResult,
    load_audio: bool = True,
    *,
    collect_details: bool = False,
):
    """Assess all ghunnah phones in a verse.

    Uses acoustic nasal boundary detection to measure true ghunnah
    duration, correcting for MFA's tendency to absorb surrounding
    vowels into nasal phones.

    Returns (errors, phones_assessed, phones_skipped) by default.
    When collect_details=True, returns
    (errors, phones_assessed, phones_skipped, List[GhunnahResult]) —
    one entry per phone that was actually assessed (post-skip), used by
    test_f0.py to inspect the F0 borderline reclassification.
    """
    harakah_ms = cal.harakah_ms
    floor_ms = cal.short_vowel_median_ms

    errors: List[AssessmentError] = []
    details: List[GhunnahResult] = []
    assessed = 0
    skipped = 0

    flat: List[Tuple[Word, Phone]] = [
        (w, p) for w in verse.words for p in w.phones
    ]

    wav_file = None
    if load_audio:
        wav_file = audio_path(verse.surah, verse.ayah)

    for i, (word, phone) in enumerate(flat):
        ghunnah_rules_on_phone = [
            r for r in phone.tajweed_rules if r in GHUNNAH_RULES
        ]
        if not ghunnah_rules_on_phone:
            continue

        # For geminate pairs, only assess the "first" phone
        if phone.geminate_pair and phone.geminate_position == "second":
            continue

        # Skip: low confidence or explicitly flagged
        if phone.skip_assessment or phone.alignment_confidence in (
            "low", "failed",
        ):
            skipped += 1
            continue

        # ── Determine MFA duration ──────────────────────────────────
        is_shaddah = any(r in SHADDAH_RULES for r in ghunnah_rules_on_phone)
        if is_shaddah and phone.geminate_pair and phone.geminate_total_ms is not None:
            mfa_duration_ms = phone.geminate_total_ms
        else:
            mfa_duration_ms = phone.duration_ms

        # Floor gate on MFA duration (pre-acoustic)
        if floor_ms > 0 and mfa_duration_ms <= floor_ms:
            skipped += 1
            continue

        # ── Acoustic boundary detection ─────────────────────────────
        acoustic: Optional[AcousticResult] = None
        if load_audio and wav_file is not None:
            mfa_start_ms, mfa_end_ms = _geminate_span_ms(phone, flat, i)
            acoustic = detect_nasal_boundaries(
                wav_file, mfa_start_ms, mfa_end_ms, mfa_duration_ms,
            )

        # Choose duration: acoustic if available and valid, else MFA
        if acoustic is not None and acoustic.found:
            duration_ms = acoustic.acoustic_duration_ms
        else:
            duration_ms = mfa_duration_ms

        actual_counts = duration_ms / harakah_ms

        # ── Pause absorption ceiling ─────────────────────────────────
        pause_absorbed = duration_ms > PAUSE_ABSORPTION_CEILING_MS

        # ── Per-rule assessment ──────────────────────────────────────
        for rule in ghunnah_rules_on_phone:
            expected_counts = GHUNNAH_RULES[rule]

            # PART A: Duration
            severity = _duration_severity(actual_counts, rule)
            note = ""

            # Annotate acoustic correction
            if acoustic is not None and acoustic.boundary_corrected:
                note = (f"acoustic={acoustic.acoustic_duration_ms:.0f}ms "
                        f"vs MFA={acoustic.mfa_duration_ms:.0f}ms")

            # Pause absorption ceiling: > 1500ms is physically
            # implausible even for extreme tartil → downgrade to style
            if pause_absorbed and severity in ("major", "minor"):
                severity = "style"
                note = (f"likely pause absorption "
                        f"({duration_ms:.0f}ms > {PAUSE_ABSORPTION_CEILING_MS:.0f}ms)")

            # Near-floor exemption (too-short near the gate)
            if (severity == "minor"
                    and actual_counts < 1.2
                    and duration_ms <= floor_ms + MFA_FRAME_MS):
                severity = "style"
                if not note:
                    note = "near-floor (MFA quantization)"

            # ── F0 borderline check (8–12 count minor only) ─────────
            # For phones flagged minor solely because they sit in the
            # "exceptionally long" 8–12 count band, run F0 over the
            # nasal region and downgrade to style if the audio shows
            # no stable phonation (i.e. the long duration is MFA
            # silence absorption, not real ghunnah).
            pre_f0_severity = severity
            f0_checked = False
            f0_confirmed: Optional[bool] = None
            f0_result: Optional[F0Result] = None

            if (severity == "minor"
                    and F0_BORDERLINE_LO_COUNTS <= actual_counts <= F0_BORDERLINE_HI_COUNTS
                    and load_audio
                    and wav_file is not None):
                # Use the acoustically-detected nasal region when
                # available — that is the actual span we're scoring;
                # fall back to the (geminate-aware) MFA span otherwise.
                if acoustic is not None and acoustic.found:
                    f0_start_ms = acoustic.nasal_start_ms
                    f0_end_ms = acoustic.nasal_end_ms
                else:
                    f0_start_ms, f0_end_ms = _geminate_span_ms(
                        phone, flat, i,
                    )

                f0_segment = _load_audio_segment(
                    wav_file, f0_start_ms, f0_end_ms,
                )
                if f0_segment is not None:
                    f0_checked = True
                    f0_result = track_f0(
                        f0_segment,
                        SAMPLE_RATE,
                        0.0,
                        f0_end_ms - f0_start_ms,
                    )
                    if f0_result.is_voiced and f0_result.is_stable:
                        # Genuine sustained tartil ghunnah — keep minor
                        f0_confirmed = True
                    else:
                        # Breath residue / MFA silence absorption —
                        # not a recitation error, downgrade to style.
                        f0_confirmed = False
                        severity = "style"
                        f0_note = (
                            f"f0 unstable "
                            f"(voiced_frac={f0_result.voiced_fraction:.2f}, "
                            f"std={f0_result.f0_std_hz:.1f}Hz) — "
                            f"likely MFA silence absorption"
                        )
                        note = f"{note}; {f0_note}" if note else f0_note

            assessed += 1

            if collect_details:
                details.append(GhunnahResult(
                    word=word.text,
                    phone=phone.ipa,
                    phone_index=i,
                    rule=rule,
                    duration_ms=duration_ms,
                    actual_counts=actual_counts,
                    severity=severity,
                    pre_f0_severity=pre_f0_severity,
                    f0_checked=f0_checked,
                    f0_confirmed=f0_confirmed,
                    voiced_fraction=(
                        f0_result.voiced_fraction if f0_result is not None else None
                    ),
                    f0_std_hz=(
                        f0_result.f0_std_hz if f0_result is not None else None
                    ),
                    is_voiced=(
                        f0_result.is_voiced if f0_result is not None else None
                    ),
                    is_stable=(
                        f0_result.is_stable if f0_result is not None else None
                    ),
                ))

            if severity is not None:
                errors.append(AssessmentError(
                    word=word.text,
                    phone=phone.ipa,
                    phone_index=i,
                    timestamp_ms=phone.start * 1000,
                    rule=rule,
                    assessment="duration",
                    expected=expected_counts,
                    actual=round(actual_counts, 2),
                    unit="counts",
                    severity=severity,
                    description=_describe_duration(
                        rule, actual_counts, note,
                    ),
                ))

            # PART B: Nasalization
            if acoustic is not None:
                nasal_ratio = acoustic.peak_nasality
                nasal_sev = _nasalization_severity(nasal_ratio)
                if nasal_sev is not None:
                    label = _nasalization_label(nasal_ratio)
                    errors.append(AssessmentError(
                        word=word.text,
                        phone=phone.ipa,
                        phone_index=i,
                        timestamp_ms=phone.start * 1000,
                        rule=rule,
                        assessment="nasalization",
                        expected=NASAL_PRESENT_THRESHOLD,
                        actual=round(nasal_ratio, 4),
                        unit="ratio",
                        severity=nasal_sev,
                        description=_describe_nasalization(
                            rule, nasal_ratio, label,
                        ),
                    ))

    if collect_details:
        return errors, assessed, skipped, details
    return errors, assessed, skipped
