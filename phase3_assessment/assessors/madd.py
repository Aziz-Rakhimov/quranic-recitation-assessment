"""Assessment 1 — Madd (prolongation) duration checker.

For each phone with a madd rule, measure its duration in harakāt
and compare to the expected count range for that rule.

FIX 1 — Verse-final handling (assessment-only, Phase 1/2 unchanged):
  1a. madd_tabii + is_verse_final → assessed as madd_arid_lissukun.
  1b. madd_arid_lissukun + is_verse_final + too long → cap to style.
  1c. madd_arid_lissukun + last-word-in-ayah + too long → cap to style.
      is_verse_final only flags the absolute last phone; earlier phones
      in the last word also reflect waqf wind-down elongation.
      At waqf the 6-count upper bound is not enforced.

FIX 2 — MFA artifact detection (ALL madd rules):
  (a) next phone in flat sequence: conf=low AND dur ≤ 30ms.
  (b) word.duration_ms > 1500ms (over-segmented word).
  (c) next phone ipa in {m, n} AND dur > 400ms (tanwīn absorbing).
  (d) phone_ms > 1.5 × rule_max × harakah_ms (pause captured before
      following hamza — common for munfasil/muttasil).
  (e) PREV phone in same word: conf=low AND dur ≤ 30ms (hamza
      boundary error absorbed into the long vowel — e.g. وَلَآ).
  → downgrade major/minor → style.

FIX 3 — Tanwīn absorbing: handled by FIX 2c.

FIX 4 — Tartil-aware madd_tabii thresholds:
  1.5 – 2.5  : correct (no error)
  2.5 – 5.5  : style  (tartil elongation, reciter choice)
  > 5.5      : major  (genuinely too long)
  1.0 – 1.5  : minor  (slightly short)
  < 1.0      : major  (too short — genuine error)

FIX 5 — MFA resolution exemption (30ms):
  MFA minimum frame = 30ms; differences ≤ 30ms from the nearest
  acceptable boundary are measurement noise, not real errors.
  major → minor, minor → style if |phone_ms – boundary_ms| ≤ 30ms.

FIX 6 — Near-floor exemption:
  If phone_ms ≤ floor_ms + 30ms AND severity == minor (too short)
  → downgrade to style.
  Handles phones clustered just above the floor gate that are flagged
  only because FIX 4 made 1.0–1.5c = minor.

MFA alignment guard rails (unchanged):
  Floor gate  : skip phone with dur ≤ short_vowel_median
  Ceiling gate: skip phone with dur > 2× rule_max × harakah_ms
"""

from __future__ import annotations
from typing import List, Optional, Tuple

from phase3_assessment.models import AssessmentError, CalibrationResult, Phone, Verse, Word

# ── Expected ranges per rule: (min_counts, max_counts) ───────────────
MADD_RULES: dict[str, Tuple[float, float]] = {
    "madd_tabii":           (1.5, 2.5),
    "madd_muttasil":        (4.0, 5.5),
    "madd_munfasil":        (1.5, 5.5),
    "madd_lazim_kalimi":    (5.5, 6.5),
    "madd_arid_lissukun":   (1.5, 6.5),
    "madd_silah_kubra":     (4.0, 5.5),
}

# Severity thresholds (counts from range boundary)
BASE_MAJOR_THRESHOLD = 1.0
BASE_MINOR_THRESHOLD = 0.5

# MFA ceiling gate
CEILING_MULTIPLIER = 2.0

# FIX 2 thresholds
WORD_OVERSEG_MS = 1500.0
TANWIN_CONSONANTS = {"m", "n"}
TANWIN_ABSORB_MS = 400.0
OVERLONG_FACTOR = 1.5         # phone_ms > 1.5 × max_c × harakah_ms → artifact

# FIX 5 / 6 threshold
MFA_FRAME_MS = 30.0


# ── FIX 4: Tartil-aware severity for madd_tabii ───────────────────────

def _severity_madd_tabii(actual_counts: float) -> Optional[str]:
    """Tartil-aware severity for madd_tabii.

    Correct  : 1.5–2.5 counts
    Style    : 2.5–5.5 counts  (tartil elongation)
    Major    : > 5.5 counts    (genuinely too long)
    Minor    : 1.0–1.5 counts  (slightly short)
    Major    : < 1.0 counts    (too short)
    """
    if 1.5 <= actual_counts <= 2.5:
        return None
    if actual_counts > 5.5:
        return "major"
    if actual_counts > 2.5:
        return "style"
    if actual_counts < 1.0:
        return "major"
    return "minor"


def _severity_standard(
    actual_counts: float,
    min_c: float,
    max_c: float,
    tolerance_factor: float = 1.0,
) -> Optional[str]:
    """Standard symmetric severity for all non-tabii madd rules."""
    if min_c <= actual_counts <= max_c:
        return None
    distance = (min_c - actual_counts) if actual_counts < min_c else (actual_counts - max_c)
    major = BASE_MAJOR_THRESHOLD * tolerance_factor
    minor = BASE_MINOR_THRESHOLD * tolerance_factor
    if distance > major:
        return "major"
    if distance > minor:
        return "minor"
    return "style"


# ── FIX 2: MFA artifact detector ──────────────────────────────────────

def _is_mfa_artifact(
    phone: Phone,
    word: Word,
    prev_phone: Optional[Phone],
    prev_same_word: bool,
    next_phone: Optional[Phone],
    max_c: float,
    harakah_ms: float,
) -> bool:
    """Return True if this madd phone is likely an MFA segmentation error.

    Conditions (all madd rules):
      (a) next phone conf=low AND dur ≤ 30ms: trailing boundary marker.
      (b) word_dur > 1500ms: MFA over-segmented the parent word.
      (c) next phone is m/n (tanwīn) AND dur > 400ms: tanwīn absorbing.
      (d) phone_ms > 1.5 × max_c × harakah_ms: pause captured before
          following hamza.
      (e) PREV phone in SAME word conf=low AND dur ≤ 30ms: hamza
          boundary error absorbed into this long vowel (FIX 7).
    """
    if next_phone is not None:
        # (a) trailing low-conf micro-phone
        if next_phone.alignment_confidence == "low" and next_phone.duration_ms <= MFA_FRAME_MS:
            return True
        # (c) tanwīn absorbing
        if next_phone.ipa in TANWIN_CONSONANTS and next_phone.duration_ms > TANWIN_ABSORB_MS:
            return True
    # (b) word-level over-segmentation
    if word.duration_ms > WORD_OVERSEG_MS:
        return True
    # (d) over-long phone capturing a pause
    if phone.duration_ms > OVERLONG_FACTOR * max_c * harakah_ms:
        return True
    # (e) preceding low-conf micro-phone in same word (FIX 7)
    if (prev_same_word
            and prev_phone is not None
            and prev_phone.alignment_confidence == "low"
            and prev_phone.duration_ms <= MFA_FRAME_MS):
        return True
    return False


# ── FIX 5: MFA resolution exemption ──────────────────────────────────

def _mfa_resolution_downgrade(
    severity: Optional[str],
    actual_counts: float,
    min_c: float,
    effective_max_c: float,
    harakah_ms: float,
) -> Optional[str]:
    """FIX 5: downgrade if distance from nearest boundary ≤ 30ms.

    effective_max_c: use 5.5 for madd_tabii (FIX 4 high threshold),
                     rule max_c for all other rules.
    """
    if severity not in ("major", "minor"):
        return severity
    if actual_counts < min_c:
        boundary_ms = min_c * harakah_ms
        dist_ms = boundary_ms - actual_counts * harakah_ms
    else:
        boundary_ms = effective_max_c * harakah_ms
        dist_ms = actual_counts * harakah_ms - boundary_ms
    if dist_ms <= MFA_FRAME_MS:
        return "minor" if severity == "major" else "style"
    return severity


# ── Description helper ────────────────────────────────────────────────

def _describe(rule: str, actual: float, min_c: float, max_c: float, note: str = "") -> str:
    display = rule.replace("_", " ").title()
    direction = "too short" if actual < min_c else "too long"
    base = (f"{display} {direction} — held {actual:.1f} counts, "
            f"expected {min_c:.1f}–{max_c:.1f}")
    return f"{base} [{note}]" if note else base


# ── Main assessment function ──────────────────────────────────────────

def assess_madd(
    verse: Verse,
    cal: CalibrationResult,
) -> Tuple[List[AssessmentError], int, int]:
    """Assess all madd phones in a verse.

    Returns (errors, phones_assessed, phones_skipped).
    """
    harakah_ms = cal.harakah_ms
    floor_ms = cal.short_vowel_median_ms
    tol = cal.tolerance_factor

    errors: List[AssessmentError] = []
    assessed = 0
    skipped = 0

    # Build flat list for prev/next phone context
    flat: List[Tuple[Word, Phone]] = [
        (w, p) for w in verse.words for p in w.phones
    ]
    last_word = verse.words[-1] if verse.words else None

    for i, (word, phone) in enumerate(flat):
        madd_rules_on_phone = [r for r in phone.tajweed_rules if r in MADD_RULES]
        if not madd_rules_on_phone:
            continue

        # Skip: low confidence or explicitly flagged
        if phone.skip_assessment or phone.alignment_confidence in ("low", "failed"):
            skipped += 1
            continue

        # Effective duration
        duration_ms = (
            phone.geminate_total_ms
            if phone.geminate_pair and phone.geminate_total_ms is not None
            else phone.duration_ms
        )

        # Floor gate
        if floor_ms > 0 and duration_ms <= floor_ms:
            skipped += 1
            continue

        actual_counts = duration_ms / harakah_ms

        # Context: prev/next phone
        prev_word, prev_phone = flat[i - 1] if i > 0 else (None, None)
        next_phone = flat[i + 1][1] if i + 1 < len(flat) else None
        prev_same_word = (prev_word is word) if prev_word is not None else False

        for rule in madd_rules_on_phone:
            # FIX 1a: verse-final madd_tabii → assess as madd_arid_lissukun
            effective_rule = rule
            note = ""
            if rule == "madd_tabii" and phone.is_verse_final:
                effective_rule = "madd_arid_lissukun"
                note = "verse-final: assessed as madd_arid_lissukun"

            min_c, max_c = MADD_RULES[effective_rule]

            # Ceiling gate
            if duration_ms > max_c * CEILING_MULTIPLIER * harakah_ms:
                skipped += 1
                continue

            # Compute severity
            if effective_rule == "madd_tabii":
                severity = _severity_madd_tabii(actual_counts)
                effective_max_for_fix5 = 5.5
            else:
                severity = _severity_standard(actual_counts, min_c, max_c, tol)
                effective_max_for_fix5 = max_c

            # FIX 1b/1c: madd_arid_lissukun too-long at verse end → style.
            # 1b: phone.is_verse_final (absolute last phone of verse).
            # 1c: word is the last word of the ayah — earlier phones in
            #     the final word also reflect waqf wind-down elongation.
            # At waqf the upper 6-count bound is not enforced.
            at_verse_end = phone.is_verse_final or (word is last_word)
            if (effective_rule == "madd_arid_lissukun"
                    and at_verse_end
                    and severity in ("major", "minor")
                    and actual_counts > max_c):
                severity = "style"
                note = "verse-end waqf: elongation beyond 6c accepted"

            # FIX 2+: MFA artifact → cap to style
            artifact = False
            if severity in ("major", "minor"):
                if _is_mfa_artifact(
                    phone, word, prev_phone, prev_same_word, next_phone, max_c, harakah_ms
                ):
                    severity = "style"
                    artifact = True
                    note = "MFA artifact (downgraded)"

            # FIX 5: MFA resolution exemption (30ms boundary proximity)
            if severity in ("major", "minor"):
                severity = _mfa_resolution_downgrade(
                    severity, actual_counts, min_c, effective_max_for_fix5, harakah_ms
                )
                if severity not in ("major", "minor") and not note:
                    note = "within MFA resolution (30ms)"

            # FIX 6: near-floor exemption — too-short, near the floor
            if (severity == "minor"
                    and actual_counts < min_c
                    and duration_ms <= floor_ms + MFA_FRAME_MS):
                severity = "style"
                if not note:
                    note = "near-floor (MFA quantization)"

            assessed += 1

            if severity is not None:
                expected_mid = (min_c + max_c) / 2.0
                errors.append(AssessmentError(
                    word=word.text,
                    phone=phone.ipa,
                    phone_index=i,
                    timestamp_ms=phone.start * 1000,
                    rule=rule,
                    assessment="duration",
                    expected=expected_mid,
                    actual=round(actual_counts, 2),
                    unit="counts",
                    severity=severity,
                    description=_describe(effective_rule, actual_counts, min_c, max_c, note),
                ))

    return errors, assessed, skipped
