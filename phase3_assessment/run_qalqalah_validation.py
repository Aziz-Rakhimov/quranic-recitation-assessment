#!/usr/bin/env python3
"""Validation + reporting script for Assessment 4 — Qalqalah.

Runs assess_qalqalah on a fixed set of surahs, collects per-phone
detection details, and prints:

  1. Per-surah qalqalah scores (counts of pass / weak / absent)
  2. Echo duration distribution (min / median / max)
  3. Echo peak ratio distribution (min / median / max)
  4. Phones where echo was absent or weak (with full context)
  5. Any unexpected findings
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phase3_assessment.assessors.qalqalah import assess_qalqalah
from phase3_assessment.calibration import calibrate
from phase3_assessment.utils.loader import load_surah, VALIDATION_DIR


SURAHS = [1, 93, 97, 113, 114, 67, 56, 36]


def _fmt_dist(values: List[float], unit: str = "") -> str:
    if not values:
        return "   (n=0)"
    values_sorted = sorted(values)
    return (
        f"n={len(values):>3}  "
        f"min={values_sorted[0]:6.1f}{unit}  "
        f"p25={values_sorted[len(values_sorted) // 4]:6.1f}{unit}  "
        f"median={statistics.median(values_sorted):6.1f}{unit}  "
        f"p75={values_sorted[(3 * len(values_sorted)) // 4]:6.1f}{unit}  "
        f"max={values_sorted[-1]:6.1f}{unit}"
    )


def main() -> None:
    print("=" * 88)
    print("  ASSESSMENT 4 — Qalqalah Echo Detection   (reciter_2)")
    print("=" * 88)

    all_details: list[dict] = []
    per_surah_stats = []

    for s in SURAHS:
        json_path = VALIDATION_DIR / f"surah_{s}" / f"surah_{s}_aligned.json"
        if not json_path.exists():
            print(f"  [skip] surah {s} — no alignment JSON")
            continue

        surah_data = load_surah(s)
        cal = calibrate(surah_data)

        surah_details: list[dict] = []
        n_errors_major = 0
        n_errors_minor = 0
        n_errors_style = 0
        n_assessed = 0
        n_skipped = 0

        for verse in surah_data.verses:
            errors, assessed, skipped, details = assess_qalqalah(
                verse, cal, collect_details=True,
            )
            n_assessed += assessed
            n_skipped += skipped
            surah_details.extend(details)

            for e in errors:
                if e.severity == "major":
                    n_errors_major += 1
                elif e.severity == "minor":
                    n_errors_minor += 1
                elif e.severity == "style":
                    n_errors_style += 1

        all_details.extend(surah_details)

        weighted = n_errors_major + 0.5 * n_errors_minor
        score = (
            100.0 * (1.0 - weighted / n_assessed) if n_assessed else 100.0
        )
        per_surah_stats.append({
            "surah": s,
            "assessed": n_assessed,
            "skipped": n_skipped,
            "major": n_errors_major,
            "minor": n_errors_minor,
            "style": n_errors_style,
            "score": score,
            "details": surah_details,
        })

    # ── 1. Per-surah scores ─────────────────────────────────────────
    print("\n1. PER-SURAH QALQALAH SCORES")
    print("   " + "-" * 92)
    print(f"   {'Surah':>5} {'Assd':>5} {'Skip':>5} {'NoCl':>5} {'Pass':>5}"
          f" {'Style':>6} {'Minor':>6} {'Major':>6} {'Score':>8}")
    print("   " + "-" * 92)
    for st in per_surah_stats:
        n_pass = sum(
            1 for d in st["details"] if d["echo_label"] == "present"
        )
        # Count unique phones skipped due to acoustic detection failure
        nocl_phones = set()
        for d in st["details"]:
            if d.get("echo_label") == "skipped" and d.get("skip_reason"):
                nocl_phones.add((d["ayah"], d["phone_index"]))
        print(
            f"   {st['surah']:>5} {st['assessed']:>5} {st['skipped']:>5}"
            f" {len(nocl_phones):>5} {n_pass:>5}"
            f" {st['style']:>6} {st['minor']:>6}"
            f" {st['major']:>6}  {st['score']:>6.1f}%"
        )
    print("   " + "-" * 92)

    # Aggregate distributions across assessed details only (exclude
    # skipped phones — they were not measured as real qalqalah).
    assessed_details = [
        d for d in all_details if d["echo_label"] != "skipped"
    ]
    echo_durations = [
        d["echo_duration_ms"] for d in assessed_details
        if d["echo_label"] in ("present", "weak")
    ]
    echo_peaks = [d["echo_peak_ratio"] for d in assessed_details]

    # ── 2. Echo duration distribution ───────────────────────────────
    print("\n2. ECHO DURATION DISTRIBUTION (frames where energy > 1.2× baseline)")
    print("   " + _fmt_dist(echo_durations, "ms"))

    # ── 3. Peak ratio distribution ──────────────────────────────────
    print("\n3. ECHO PEAK RATIO DISTRIBUTION (peak / baseline)")
    print("   " + _fmt_dist(echo_peaks, "×"))

    # ── 4. Non-pass cases ────────────────────────────────────────────
    print("\n4. NON-PASS PHONES (absent / weak / skipped)")
    problems = [d for d in all_details if d["echo_label"] != "present"]
    if not problems:
        print("   (none — every phone registered a sustained echo)")
    else:
        # Dedup by (surah, ayah, phone_index) so multiple rules on the
        # same phone produce one context line.
        seen: set = set()
        rows = []
        for d in problems:
            key = (d["surah"], d["ayah"], d["phone_index"])
            if key in seen:
                rows[-1]["rules"].append(d["rule"])
                continue
            seen.add(key)
            rows.append({**d, "rules": [d["rule"]]})
        print(
            f"   {'Surah':>5} {'Ayah':>4} {'Word':<18} {'Ph':>3}"
            f" {'Label':>8} {'Dur':>6} {'Peak':>6}  Rules"
        )
        print("   " + "-" * 88)
        for r in rows:
            rules_str = ", ".join(sorted(set(r["rules"])))
            reason = f" [{r.get('skip_reason')}]" if r.get("skip_reason") else ""
            print(
                f"   {r['surah']:>5} {r['ayah']:>4} {r['word']:<18}"
                f" {r['phone']:>3} {r['echo_label']:>8}"
                f" {r['echo_duration_ms']:>5.0f}ms {r['echo_peak_ratio']:>5.2f}×"
                f"  {rules_str}{reason}"
            )

    # ── 5. Spec-mentioned check cases ───────────────────────────────
    print("\n5. SPEC-MENTIONED VALIDATION CASES")
    spec_cases = [
        (1, 2, "رَبِّ", "b", "qalqalah_with_shaddah"),
        (1, 4, "ٱلدِّينِ", "d", "qalqalah_with_shaddah"),
        (93, 3, "وَدَّعَكَ", "d", "qalqalah_with_shaddah"),
        (93, 3, "رَبُّكَ", "b", "qalqalah_with_shaddah"),
        (93, 5, "رَبُّكَ", "b", "qalqalah_with_shaddah"),
        (93, 11, "رَبِّكَ", "b", "qalqalah_with_shaddah"),
        (114, 1, "بِرَبِّ", "b", "qalqalah_with_shaddah"),
    ]
    for (su, ay, w, ph, rule) in spec_cases:
        match = next(
            (d for d in all_details
             if d["surah"] == su and d["ayah"] == ay
             and d["word"] == w and d["phone"] == ph and d["rule"] == rule),
            None,
        )
        if match is None:
            print(f"   ? {su}:{ay} {w:<15} {ph} {rule} — not evaluated")
            continue
        ok = "✔" if match["echo_label"] == "present" else "✗"
        print(
            f"   {ok} {su}:{ay} {w:<15} {ph} {rule:<22}"
            f" → {match['echo_label']:<7}"
            f"  dur={match['echo_duration_ms']:>4.0f}ms"
            f"  peak={match['echo_peak_ratio']:>4.2f}×"
        )

    print("\n" + "=" * 88)


if __name__ == "__main__":
    main()
