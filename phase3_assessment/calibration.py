"""Adaptive per-audio harakah calibration.

Priority order:
  1. High-confidence short vowels (50–300ms) from the current audio — primary signal.
  2. Supplement with madd_tabii phones (duration / 2) if available.
  3. IQR-filter both pools, combine as weighted median.
  4. If total n >= 5 → use calibrated value (tolerance_factor = 1.0).
  5. If n < 5  → use 107ms default with wider tolerance (tolerance_factor = 1.6).

Works for single-ayah input (3–5 short vowels), full surah (hundreds),
or cold-start with no prior data.
"""

from __future__ import annotations
import statistics
from typing import List

from phase3_assessment.models import CalibrationResult, Phone, SurahData, Verse

SHORT_VOWELS = {"a", "i", "u"}
DEFAULT_HARAKAH_MS = 107.0
MIN_SAMPLES = 5

# Duration band for eligible short vowels: 50–300ms
# Below 50ms → MFA floor artifact; above 300ms → phrase-final lengthening
SHORT_VOWEL_MIN_MS = 50.0
SHORT_VOWEL_MAX_MS = 300.0


def _is_eligible_base(phone: Phone) -> bool:
    """Base eligibility: high confidence, not skipped/geminate/verse-final."""
    return (
        phone.alignment_confidence == "high"
        and not phone.skip_assessment
        and not phone.is_verse_final
        and not phone.geminate_pair
    )


def _iqr_filter(values: List[float], k: float = 1.5) -> List[float]:
    """Remove outliers using IQR method."""
    if len(values) < 4:
        return values
    s = sorted(values)
    n = len(s)
    q1 = s[n // 4]
    q3 = s[(3 * n) // 4]
    iqr = q3 - q1
    lo = q1 - k * iqr
    hi = q3 + k * iqr
    return [v for v in values if lo <= v <= hi]


def _collect_short_vowels_from_verse(verse: Verse) -> List[float]:
    """Collect band-filtered short vowel durations from a single verse."""
    durations = []
    for word, phone in verse.all_phones():
        if (phone.ipa in SHORT_VOWELS
                and _is_eligible_base(phone)
                and SHORT_VOWEL_MIN_MS <= phone.duration_ms <= SHORT_VOWEL_MAX_MS):
            # Exclude phones that have madd rules
            if not any(r.startswith("madd_") for r in phone.tajweed_rules):
                durations.append(phone.duration_ms)
    return durations


def _collect_madd_tabii_from_verse(verse: Verse) -> List[float]:
    """Collect madd_tabii durations from a single verse."""
    durations = []
    for word, phone in verse.all_phones():
        if ("madd_tabii" in phone.tajweed_rules
                and _is_eligible_base(phone)
                and phone.duration_ms >= SHORT_VOWEL_MIN_MS):
            durations.append(phone.duration_ms)
    return durations


def collect_short_vowels(surah_data: SurahData) -> List[float]:
    """Collect from all verses in a surah."""
    result = []
    for v in surah_data.verses:
        result.extend(_collect_short_vowels_from_verse(v))
    return result


def collect_madd_tabii(surah_data: SurahData) -> List[float]:
    """Collect from all verses in a surah."""
    result = []
    for v in surah_data.verses:
        result.extend(_collect_madd_tabii_from_verse(v))
    return result


def calibrate_from_phones(
    short_raw: List[float],
    madd_raw: List[float],
) -> CalibrationResult:
    """Adaptive calibration from raw duration lists.

    Short vowels are the primary signal (1-harakah references).
    Madd_tabii phones supplement (2-harakah references, divided by 2).
    Falls back to DEFAULT_HARAKAH_MS if total samples < MIN_SAMPLES.
    """
    # IQR-filter short vowels
    short = _iqr_filter(short_raw) if short_raw else []
    if not short:
        short = short_raw

    # IQR-filter madd_tabii, gate out those shorter than short-vowel median
    madd_halved: List[float] = []
    if madd_raw and short:
        short_median = statistics.median(short)
        madd_gated = [d for d in madd_raw if d > short_median]
        madd_filtered = _iqr_filter(madd_gated) if len(madd_gated) >= 4 else madd_gated
        madd_halved = [d / 2.0 for d in madd_filtered]
    elif madd_raw:
        madd_filtered = _iqr_filter(madd_raw) if len(madd_raw) >= 4 else madd_raw
        madd_halved = [d / 2.0 for d in madd_filtered]

    # Combine both signals into one pool of harakah estimates
    all_estimates = list(short) + list(madd_halved)
    total_n = len(all_estimates)

    # Stats for reporting
    short_median = statistics.median(short) if short else 0.0
    short_std = statistics.stdev(short) if len(short) > 1 else 0.0
    short_count = len(short)

    madd_median_raw = statistics.median(madd_filtered) if madd_raw and madd_filtered else 0.0
    madd_std = statistics.stdev(madd_filtered) if madd_raw and len(madd_filtered) > 1 else 0.0
    madd_count = len(madd_filtered) if madd_raw else 0

    ratio = madd_median_raw / short_median if short_median > 0 and madd_median_raw > 0 else 0.0

    # Decision: enough data or fallback?
    if total_n >= MIN_SAMPLES:
        harakah_ms = statistics.median(all_estimates)
        return CalibrationResult(
            harakah_ms=harakah_ms,
            short_vowel_median_ms=short_median,
            madd_tabii_median_ms=madd_median_raw,
            short_vowel_count=short_count,
            madd_tabii_count=madd_count,
            ratio=ratio,
            short_vowel_std_ms=short_std,
            madd_tabii_std_ms=madd_std,
            is_default=False,
            tolerance_factor=1.0,
        )
    else:
        return CalibrationResult(
            harakah_ms=DEFAULT_HARAKAH_MS,
            short_vowel_median_ms=short_median,
            madd_tabii_median_ms=madd_median_raw,
            short_vowel_count=short_count,
            madd_tabii_count=madd_count,
            ratio=ratio,
            short_vowel_std_ms=short_std,
            madd_tabii_std_ms=madd_std,
            is_default=True,
            tolerance_factor=1.6,
        )


def calibrate(surah_data: SurahData) -> CalibrationResult:
    """Calibrate from a single surah."""
    return calibrate_from_phones(
        collect_short_vowels(surah_data),
        collect_madd_tabii(surah_data),
    )


def calibrate_verse(verse: Verse) -> CalibrationResult:
    """Calibrate from a single ayah/verse (may fall back to default)."""
    return calibrate_from_phones(
        _collect_short_vowels_from_verse(verse),
        _collect_madd_tabii_from_verse(verse),
    )


def calibrate_multi_surah(surah_datasets: List[SurahData]) -> CalibrationResult:
    """Calibrate from multiple surahs pooled together."""
    all_short: List[float] = []
    all_madd: List[float] = []
    for sd in surah_datasets:
        all_short.extend(collect_short_vowels(sd))
        all_madd.extend(collect_madd_tabii(sd))
    return calibrate_from_phones(all_short, all_madd)
