#!/usr/bin/env python3
"""Test runner for ikhfa nasalization quality assessor.

Runs on surahs 1, 36, 93, 97, 113 for reciter_2.
Prints per-phone results and a summary table.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from phase3_assessment.calibration import calibrate
from phase3_assessment.assessors.ikhfa import assess_ikhfa, IkhfaResult
from phase3_assessment.utils.loader import load_surah, VALIDATION_DIR


SURAHS = [1, 36, 93, 97, 113]
RECITER = "reciter_2"


def run_surah(surah_num: int) -> list[tuple[int, IkhfaResult]]:
    """Run ikhfa assessment on a single surah.

    Returns list of (ayah, IkhfaResult) tuples.
    """
    json_path = VALIDATION_DIR / f"surah_{surah_num}" / f"surah_{surah_num}_aligned.json"
    if not json_path.exists():
        print(f"  [SKIP] surah {surah_num}: {json_path} not found")
        return []

    data = load_surah(surah_num)
    cal = calibrate(data)

    all_details: list[tuple[int, IkhfaResult]] = []
    for verse in data.verses:
        _errors, _assessed, _skipped, details = assess_ikhfa(
            verse, cal, load_audio=True, collect_details=True,
        )
        for d in details:
            all_details.append((verse.ayah, d))

    return all_details


def print_per_phone(surah_num: int, results: list[tuple[int, IkhfaResult]]) -> None:
    """Print per-phone results for a surah."""
    if not results:
        return
    print(f"\n{'='*80}")
    print(f"  Surah {surah_num} — per-phone ikhfa results ({len(results)} phones)")
    print(f"{'='*80}")
    print(f"  {'ayah':>4}  {'idx':>4}  {'word':<12} {'ipa':<8} {'rule':<16} "
          f"{'dur_ms':>6} {'verdict':<18} {'sev':<8} "
          f"{'mean_ratio':>10} {'frames':>6}  {'skip_reason'}")
    print(f"  {'-'*4}  {'-'*4}  {'-'*12} {'-'*8} {'-'*16} "
          f"{'-'*6} {'-'*18} {'-'*8} "
          f"{'-'*10} {'-'*6}  {'-'*20}")

    for ayah, r in results:
        skip = r.skip_reason or ""
        print(f"  {ayah:>4}  {r.phone_index:>4}  {r.word:<12} {r.ipa:<8} {r.tajweed_rule:<16} "
              f"{r.duration_ms:>6.1f} {r.verdict:<18} {r.severity:<8} "
              f"{r.mean_nasality_ratio:>10.4f} {r.frame_count:>6}  {skip}")


def print_summary(surah_results: dict[int, list[tuple[int, IkhfaResult]]]) -> None:
    """Print a summary table across all surahs."""
    print(f"\n{'='*80}")
    print("  IKHFA ASSESSMENT SUMMARY")
    print(f"{'='*80}")
    print(f"  {'surah':>5}  {'total':>6}  {'pass':>6}  {'major':>6}  "
          f"{'minor':>6}  {'style':>6}  {'skipped':>7}")
    print(f"  {'-'*5}  {'-'*6}  {'-'*6}  {'-'*6}  "
          f"{'-'*6}  {'-'*6}  {'-'*7}")

    grand = {"total": 0, "pass": 0, "major": 0, "minor": 0, "style": 0, "skipped": 0}

    for surah_num in sorted(surah_results.keys()):
        pairs = surah_results[surah_num]
        total = len(pairs)
        n_pass = sum(1 for _, r in pairs if r.severity == "pass")
        n_major = sum(1 for _, r in pairs if r.severity == "major")
        n_minor = sum(1 for _, r in pairs if r.severity == "minor")
        n_style = sum(1 for _, r in pairs if r.severity == "style")
        n_skip = sum(1 for _, r in pairs if r.severity == "skipped")

        print(f"  {surah_num:>5}  {total:>6}  {n_pass:>6}  {n_major:>6}  "
              f"{n_minor:>6}  {n_style:>6}  {n_skip:>7}")

        grand["total"] += total
        grand["pass"] += n_pass
        grand["major"] += n_major
        grand["minor"] += n_minor
        grand["style"] += n_style
        grand["skipped"] += n_skip

    print(f"  {'-'*5}  {'-'*6}  {'-'*6}  {'-'*6}  "
          f"{'-'*6}  {'-'*6}  {'-'*7}")
    print(f"  {'TOTAL':>5}  {grand['total']:>6}  {grand['pass']:>6}  "
          f"{grand['major']:>6}  {grand['minor']:>6}  {grand['style']:>6}  "
          f"{grand['skipped']:>7}")


def main() -> None:
    print("Ikhfa nasalization quality assessment")
    print(f"Reciter: {RECITER}")
    print(f"Surahs:  {SURAHS}")

    surah_results: dict[int, list[IkhfaResult]] = {}

    for surah_num in SURAHS:
        print(f"\nProcessing surah {surah_num}...")
        results = run_surah(surah_num)
        surah_results[surah_num] = results
        print_per_phone(surah_num, results)

    print_summary(surah_results)

    # ── Diagnostic: over_nasalized duration distribution ────────────
    all_pairs = [(a, r) for pairs in surah_results.values() for a, r in pairs]
    over = [(a, r) for a, r in all_pairs if r.verdict == "over_nasalized"]

    print(f"\n{'='*80}")
    print(f"  OVER_NASALIZED DURATION DISTRIBUTION ({len(over)} phones)")
    print(f"{'='*80}")
    if over:
        import statistics
        durs = [r.duration_ms for _, r in over]
        buckets = {
            "  <=50ms": sum(1 for d in durs if d <= 50),
            " 51-100ms": sum(1 for d in durs if 51 <= d <= 100),
            "101-150ms": sum(1 for d in durs if 101 <= d <= 150),
            "151-200ms": sum(1 for d in durs if 151 <= d <= 200),
            "   >200ms": sum(1 for d in durs if d > 200),
        }
        for label, count in buckets.items():
            bar = "#" * count
            print(f"  {label}: {count:>3}  {bar}")
        print()
        print(f"  min={min(durs):.1f} ms  median={statistics.median(durs):.1f} ms  max={max(durs):.1f} ms")

    # ── Diagnostic: pass phones full details ────────────────────────
    passing = [(a, r) for a, r in all_pairs if r.verdict == "pass"]

    print(f"\n{'='*80}")
    print(f"  PASS PHONES — FULL DETAILS ({len(passing)} phones)")
    print(f"{'='*80}")
    for ayah, r in passing:
        # Find surah number from surah_results
        surah_num = None
        for s, pairs in surah_results.items():
            if any(r2 is r for _, r2 in pairs):
                surah_num = s
                break
        print(f"  surah={surah_num}  ayah={ayah}  word={r.word}  ipa={r.ipa}  "
              f"rule={r.tajweed_rule}")
        print(f"    start_ms={r.start_ms:.0f}  end_ms={r.end_ms:.0f}  "
              f"duration_ms={r.duration_ms:.1f}")
        print(f"    mean_nasality_ratio={r.mean_nasality_ratio:.6f}  "
              f"frame_count={r.frame_count}")
        print()


if __name__ == "__main__":
    main()
