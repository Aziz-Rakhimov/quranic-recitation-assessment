#!/usr/bin/env python3
"""Validate ghunnah assessor across all 8 test surahs.

Reports:
1. New scores per surah
2. Distribution of duration findings (major/minor/pass/style)
3. Any remaining major errors with full context
4. Key phone-level checks
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phase3_assessment.calibration import calibrate
from phase3_assessment.assessors.ghunnah import (
    assess_ghunnah,
    detect_nasal_boundaries,
    GHUNNAH_RULES,
    SHADDAH_RULES,
    IKHFAA_RULES,
    PAUSE_ABSORPTION_CEILING_MS,
    _geminate_span_ms,
)
from phase3_assessment.utils.loader import load_surah, audio_path

TEST_SURAHS = [1, 36, 56, 67, 93, 97, 113, 114]


def analyze_surah(surah_num: int):
    """Analyze one surah and return summary dict + phone details."""
    data = load_surah(surah_num)
    cal = calibrate(data)

    total_assessed = 0
    total_skipped = 0
    all_errors = []
    phone_details = []

    for verse in data.verses:
        errors, assessed, skipped_count = assess_ghunnah(verse, cal, load_audio=True)
        total_assessed += assessed
        total_skipped += skipped_count
        all_errors.extend(errors)

        # Collect per-phone details
        flat = [(w, p) for w in verse.words for p in w.phones]
        wav = audio_path(verse.surah, verse.ayah)

        for idx, (word, phone) in enumerate(flat):
            rules = [r for r in phone.tajweed_rules if r in GHUNNAH_RULES]
            if not rules:
                continue
            if phone.geminate_pair and phone.geminate_position == "second":
                continue
            if phone.skip_assessment or phone.alignment_confidence in ("low", "failed"):
                continue

            is_shaddah = any(r in SHADDAH_RULES for r in rules)
            if is_shaddah and phone.geminate_pair and phone.geminate_total_ms is not None:
                mfa_dur = phone.geminate_total_ms
            else:
                mfa_dur = phone.duration_ms

            if cal.short_vowel_median_ms > 0 and mfa_dur <= cal.short_vowel_median_ms:
                continue  # skipped by floor gate

            mfa_start, mfa_end = _geminate_span_ms(phone, flat, idx)
            acoustic = detect_nasal_boundaries(wav, mfa_start, mfa_end, mfa_dur)

            dur_ms = acoustic.acoustic_duration_ms if acoustic.found else mfa_dur
            counts = dur_ms / cal.harakah_ms

            dur_errors = [e for e in errors if e.phone_index == idx and e.assessment == "duration"]
            nas_errors = [e for e in errors if e.phone_index == idx and e.assessment == "nasalization"]

            phone_details.append({
                "surah": surah_num,
                "ayah": verse.ayah,
                "word": word.text,
                "phone": phone.ipa,
                "rule": rules[0],
                "mfa_ms": round(mfa_dur, 1),
                "acoustic_ms": round(acoustic.acoustic_duration_ms, 1),
                "counts": round(counts, 2),
                "peak_nasality": round(acoustic.peak_nasality, 4),
                "dur_sev": dur_errors[0].severity if dur_errors else None,
                "dur_desc": dur_errors[0].description if dur_errors else None,
                "nas_sev": nas_errors[0].severity if nas_errors else None,
                "corrected": acoustic.boundary_corrected,
            })

    dur_errors = [e for e in all_errors if e.assessment == "duration"]
    nas_errors = [e for e in all_errors if e.assessment == "nasalization"]

    n_major = sum(1 for e in all_errors if e.severity == "major")
    n_minor = sum(1 for e in all_errors if e.severity == "minor")
    weighted = n_major + 0.5 * n_minor
    score = round(100 * (1 - weighted / max(total_assessed, 1)), 1)

    return {
        "surah": surah_num,
        "harakah_ms": cal.harakah_ms,
        "assessed": total_assessed,
        "skipped": total_skipped,
        "dur_major": sum(1 for e in dur_errors if e.severity == "major"),
        "dur_minor": sum(1 for e in dur_errors if e.severity == "minor"),
        "dur_style": sum(1 for e in dur_errors if e.severity == "style"),
        "dur_pass": total_assessed - len(dur_errors),
        "nas_major": sum(1 for e in nas_errors if e.severity == "major"),
        "nas_style": sum(1 for e in nas_errors if e.severity == "style"),
        "nas_pass": total_assessed - len(nas_errors),
        "score": score,
        "reliability": "high" if total_assessed >= 10 else "low",
    }, phone_details, all_errors


def main():
    print("=" * 90)
    print("  Ghunnah Assessment — Tartil-Aware Thresholds — All 8 Test Surahs")
    print("=" * 90)

    all_summaries = []
    all_phones = []
    all_majors = []

    for s in TEST_SURAHS:
        summary, phones, errors = analyze_surah(s)
        all_summaries.append(summary)
        all_phones.extend(phones)
        majors = [e for e in errors if e.severity == "major"]
        for e in majors:
            all_majors.append((s, e))

    # ── 1. Scores per surah ──────────────────────────────────────────
    print(f"\n{'─' * 90}")
    print("  1. Per-Surah Scores")
    print(f"{'─' * 90}")
    print(f"  {'Surah':>5} {'Hrkh':>5} {'Assd':>5} {'Skip':>5} "
          f"{'Pass':>5} {'Style':>5} {'Minor':>5} {'Major':>5} "
          f"{'Score':>6} {'Rel':>4}")
    print(f"  {'─'*5} {'─'*5} {'─'*5} {'─'*5} "
          f"{'─'*5} {'─'*5} {'─'*5} {'─'*5} "
          f"{'─'*6} {'─'*4}")

    for s in all_summaries:
        print(f"  {s['surah']:>5} {s['harakah_ms']:>5.0f} {s['assessed']:>5} {s['skipped']:>5} "
              f"{s['dur_pass']:>5} {s['dur_style']:>5} {s['dur_minor']:>5} {s['dur_major']:>5} "
              f"{s['score']:>5.1f}% {s['reliability']:>4}")

    total_assessed = sum(s["assessed"] for s in all_summaries)
    total_pass = sum(s["dur_pass"] for s in all_summaries)
    total_style = sum(s["dur_style"] for s in all_summaries)
    total_minor = sum(s["dur_minor"] for s in all_summaries)
    total_major = sum(s["dur_major"] for s in all_summaries)
    total_weighted = total_major + 0.5 * total_minor
    overall_score = round(100 * (1 - total_weighted / max(total_assessed, 1)), 1)
    print(f"  {'TOTAL':>5} {'':>5} {total_assessed:>5} {sum(s['skipped'] for s in all_summaries):>5} "
          f"{total_pass:>5} {total_style:>5} {total_minor:>5} {total_major:>5} "
          f"{overall_score:>5.1f}%")

    # ── 2. Duration finding distribution ─────────────────────────────
    print(f"\n{'─' * 90}")
    print("  2. Duration Finding Distribution")
    print(f"{'─' * 90}")
    print(f"  Pass:  {total_pass:>4} ({100*total_pass/max(total_assessed,1):.1f}%)")
    print(f"  Style: {total_style:>4} ({100*total_style/max(total_assessed,1):.1f}%) — tartil elongation / pause absorption")
    print(f"  Minor: {total_minor:>4} ({100*total_minor/max(total_assessed,1):.1f}%)")
    print(f"  Major: {total_major:>4} ({100*total_major/max(total_assessed,1):.1f}%)")

    # Count distribution by count ranges
    count_ranges = {"<0.8": 0, "0.8-1.2": 0, "1.2-2.8": 0, "2.8-8.0": 0,
                    "8.0-12": 0, ">12": 0}
    for p in all_phones:
        c = p["counts"]
        if c < 0.8: count_ranges["<0.8"] += 1
        elif c < 1.2: count_ranges["0.8-1.2"] += 1
        elif c <= 2.8: count_ranges["1.2-2.8"] += 1
        elif c <= 8.0: count_ranges["2.8-8.0"] += 1
        elif c <= 12.0: count_ranges["8.0-12"] += 1
        else: count_ranges[">12"] += 1

    print(f"\n  Count distribution (all phones):")
    for label, n in count_ranges.items():
        bar = "█" * (n * 2)
        print(f"    {label:>8}: {n:>3} {bar}")

    # ── 3. Remaining major errors ────────────────────────────────────
    print(f"\n{'─' * 90}")
    print("  3. Remaining Major Errors (full context)")
    print(f"{'─' * 90}")
    if all_majors:
        for surah, e in all_majors:
            print(f"  Surah {surah}: [{e.severity}] {e.assessment} | "
                  f"{e.word} ({e.phone}) {e.rule}")
            print(f"    {e.description}")
    else:
        print("  None!")

    # ── 4. Key phone checks ──────────────────────────────────────────
    print(f"\n{'─' * 90}")
    print("  4. Key Phone Checks")
    print(f"{'─' * 90}")

    # Surah 114 score
    s114 = next((s for s in all_summaries if s["surah"] == 114), None)
    if s114:
        print(f"\n  Surah 114 score: {s114['score']}% "
              f"(was 0.0% before tartil thresholds)")
        print(f"    Pass={s114['dur_pass']} Style={s114['dur_style']} "
              f"Minor={s114['dur_minor']} Major={s114['dur_major']}")

    # Surah 97 خَيْرٌ check
    khayr = [p for p in all_phones if p["surah"] == 97 and p["word"] == "خَيْرٌ"]
    if khayr:
        k = khayr[0]
        status = "PASS ✓" if k["dur_sev"] is None else f"FAIL: {k['dur_sev']}"
        print(f"\n  Surah 97 خَيْرٌ (idgham, 1.67c): {status}")

    # Surah 97 مِّن 16.42c check
    min_ikhfaa = [p for p in all_phones if p["surah"] == 97
                  and "ikhfaa" in p["rule"] and p["counts"] > 10]
    if min_ikhfaa:
        m = min_ikhfaa[0]
        print(f"\n  Surah 97 مِّن ikhfaa ({m['counts']:.1f}c, {m['mfa_ms']:.0f}ms): "
              f"severity={m['dur_sev'] or 'pass'}")
        if m["dur_desc"]:
            print(f"    {m['dur_desc']}")

    # ── 5. Nasalization summary ──────────────────────────────────────
    print(f"\n{'─' * 90}")
    print("  5. Nasalization Summary")
    print(f"{'─' * 90}")
    nas_ratios = [p["peak_nasality"] for p in all_phones if p["peak_nasality"] > 0]
    if nas_ratios:
        present = sum(1 for r in nas_ratios if r >= 0.15)
        uncertain = sum(1 for r in nas_ratios if 0.08 <= r < 0.15)
        absent = sum(1 for r in nas_ratios if r < 0.08)
        print(f"  Present: {present}  Uncertain: {uncertain}  Absent: {absent}")
        print(f"  Peak ratio: min={min(nas_ratios):.4f}  "
              f"median={statistics.median(nas_ratios):.4f}  "
              f"max={max(nas_ratios):.4f}")

    nas_major = sum(1 for s in all_summaries for _ in range(s["nas_major"]))
    nas_style = sum(1 for s in all_summaries for _ in range(s["nas_style"]))
    if nas_major or nas_style:
        nas_phones = [p for p in all_phones if p["nas_sev"] is not None]
        print(f"\n  Nasalization errors ({nas_major} major, {nas_style} style):")
        for p in nas_phones:
            print(f"    Surah {p['surah']}:{p['ayah']} {p['word']} "
                  f"({p['rule']}) ratio={p['peak_nasality']:.4f} → {p['nas_sev']}")

    # ── 6. Full phone table for Surahs 114 + 97 ─────────────────────
    print(f"\n{'─' * 90}")
    print("  6. Phone Detail — Surahs 114 & 97")
    print(f"{'─' * 90}")
    print(f"  {'S':>3}:{'A':<2} {'Word':<15} {'Rule':<25} {'MFA':>5} {'Acou':>5} "
          f"{'Cnt':>5} {'Nasl':>5} {'Dur':>5} {'Corr':>4}")
    print(f"  {'─'*5} {'─'*15} {'─'*25} {'─'*5} {'─'*5} "
          f"{'─'*5} {'─'*5} {'─'*5} {'─'*4}")
    for p in all_phones:
        if p["surah"] not in (97, 114):
            continue
        sev = p["dur_sev"] or "pass"
        nsev = p["nas_sev"] or "pass"
        corr = "Y" if p["corrected"] else "-"
        print(f"  {p['surah']:>3}:{p['ayah']:<2} {p['word']:<15} {p['rule']:<25} "
              f"{p['mfa_ms']:>5.0f} {p['acoustic_ms']:>5.0f} "
              f"{p['counts']:>5.1f} {p['peak_nasality']:>5.3f} {sev:>5} {corr:>4}")

    print(f"\n{'=' * 90}")
    print(f"  Overall: {overall_score}% across {total_assessed} phones in {len(TEST_SURAHS)} surahs")
    print(f"{'=' * 90}")


if __name__ == "__main__":
    main()
