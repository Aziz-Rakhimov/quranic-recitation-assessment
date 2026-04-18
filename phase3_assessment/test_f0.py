#!/usr/bin/env python3
"""Test runner for the F0 borderline check on ghunnah minor phones.

Runs assess_ghunnah(collect_details=True) on Surah 114 — the surah that
sits at 62.5% because of 6 borderline minor ghunnah phones in the
8–12 harakah range. For each borderline phone we report the F0 stats,
the pre-F0 verdict (always "minor" by definition of borderline), and
the post-F0 verdict (kept as minor or downgraded to style).

Reporting only — no thresholds are tuned based on this run.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so the package imports resolve.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from phase3_assessment.assessors.ghunnah import (
    F0_BORDERLINE_HI_COUNTS,
    F0_BORDERLINE_LO_COUNTS,
    GhunnahResult,
    assess_ghunnah,
)
from phase3_assessment.calibration import calibrate
from phase3_assessment.utils.loader import VALIDATION_DIR, load_surah


DEFAULT_SURAHS = [114]


def run_surah(surah_num: int) -> None:
    json_path = (
        VALIDATION_DIR / f"surah_{surah_num}" / f"surah_{surah_num}_aligned.json"
    )
    if not json_path.exists():
        print(f"[ERROR] {json_path} not found")
        return

    data = load_surah(surah_num)
    cal = calibrate(data)
    print("=" * 110)
    print(
        f"Surah {surah_num}: {data.num_ayahs} ayahs   "
        f"harakah_ms={cal.harakah_ms:.1f}   "
        f"short_n={cal.short_vowel_count}   "
        f"is_default={cal.is_default}"
    )
    print(
        f"F0 borderline window: "
        f"{F0_BORDERLINE_LO_COUNTS:.0f}–{F0_BORDERLINE_HI_COUNTS:.0f} counts"
    )
    print()

    # Collect every detail across the surah, tagged with ayah number.
    all_details: list[tuple[int, GhunnahResult]] = []
    for verse in data.verses:
        _errors, _assessed, _skipped, details = assess_ghunnah(
            verse, cal, load_audio=True, collect_details=True,
        )
        for d in details:
            all_details.append((verse.ayah, d))

    # Borderline = pre-F0 verdict was minor AND counts in 8–12 window.
    # (That is exactly the set on which the F0 check is run.)
    borderline = [
        (a, d) for a, d in all_details
        if d.pre_f0_severity == "minor"
        and F0_BORDERLINE_LO_COUNTS <= d.actual_counts <= F0_BORDERLINE_HI_COUNTS
    ]

    print(f"Borderline phones (pre-F0 minor, 8–12 counts): {len(borderline)}")
    print()

    if not borderline:
        print("(none — nothing to inspect)")
    else:
        header = (
            f"{'ayah':>4}  {'word':<18}  {'phone':<6}  "
            f"{'dur_ms':>7}  {'counts':>6}  "
            f"{'voiced_f':>8}  {'f0_std':>7}  "
            f"{'voiced':>6}  {'stable':>6}  "
            f"{'old':<6} → {'new':<6}  changed"
        )
        print(header)
        print("-" * len(header))
        for ayah, d in borderline:
            vf = "  --  " if d.voiced_fraction is None else f"{d.voiced_fraction:8.2f}"
            std = "  --  " if d.f0_std_hz is None else f"{d.f0_std_hz:7.1f}"
            iv = "  --  " if d.is_voiced is None else f"{str(d.is_voiced):>6}"
            ist = "  --  " if d.is_stable is None else f"{str(d.is_stable):>6}"
            changed = "YES" if d.severity != d.pre_f0_severity else "no"
            print(
                f"{ayah:>4}  {d.word:<18}  {d.phone:<6}  "
                f"{d.duration_ms:7.0f}  {d.actual_counts:6.2f}  "
                f"{vf}  {std}  {iv}  {ist}  "
                f"{str(d.pre_f0_severity):<6} → {str(d.severity):<6}  {changed}"
            )

    # ── Summary ────────────────────────────────────────────────────
    print()
    n_kept = sum(
        1 for _, d in borderline
        if d.severity == "minor" and d.pre_f0_severity == "minor"
    )
    n_downgraded = sum(
        1 for _, d in borderline
        if d.severity == "style" and d.pre_f0_severity == "minor"
    )
    n_other = len(borderline) - n_kept - n_downgraded
    n_unchecked = sum(1 for _, d in borderline if not d.f0_checked)

    print("── Summary ──")
    print(f"  borderline phones inspected : {len(borderline)}")
    print(f"  F0 check did not run        : {n_unchecked}")
    print(f"  kept as minor (genuine)     : {n_kept}")
    print(f"  downgraded to style (artifact): {n_downgraded}")
    if n_other:
        print(f"  other transitions           : {n_other}")
    print()


def main() -> None:
    if len(sys.argv) > 1:
        try:
            surahs = [int(s) for s in sys.argv[1:]]
        except ValueError:
            print(f"usage: {sys.argv[0]} [surah_num ...]")
            sys.exit(1)
    else:
        surahs = DEFAULT_SURAHS
    for s in surahs:
        run_surah(s)


if __name__ == "__main__":
    main()
