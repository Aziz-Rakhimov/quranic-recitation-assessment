"""Validation script — run vowel_backing assessor on reciter_2, all 8 surahs."""

from __future__ import annotations
import sys
sys.path.insert(0, ".")

from phase3_assessment.utils.loader import load_surah
from phase3_assessment.calibration import calibrate
from phase3_assessment.assessors.vowel_backing import assess_vowel_backing

SURAHS = [1, 36, 56, 67, 93, 97, 113, 114]

grand_total = 0
grand_pass = 0
grand_minor = 0
grand_major = 0
grand_skipped = 0
sample_phones = []
major_phones = []

for s in SURAHS:
    data = load_surah(s)
    cal = calibrate(data)

    total = 0
    n_pass = 0
    n_minor = 0
    n_major = 0
    n_skipped = 0

    for verse in data.verses:
        errors, assessed, skipped, details = assess_vowel_backing(
            verse, cal, load_audio=True, collect_details=True,
        )
        total += assessed
        n_skipped += skipped

        for d in details:
            if d.verdict == "skipped":
                continue
            if d.severity == "pass":
                n_pass += 1
            elif d.severity == "minor":
                n_minor += 1
            elif d.severity == "major":
                n_major += 1
                major_phones.append({
                    "surah": s,
                    "ayah": verse.ayah,
                    "word": d.word,
                    "ipa": d.ipa,
                    "rule": d.tajweed_rule,
                    "f2_hz": d.f2_hz,
                })

            # Collect samples
            if len(sample_phones) < 30:
                sample_phones.append({
                    "surah": s,
                    "ayah": verse.ayah,
                    "word": d.word,
                    "ipa": d.ipa,
                    "rule": d.tajweed_rule,
                    "f2_hz": d.f2_hz,
                    "verdict": d.verdict,
                    "start_ms": d.start_ms,
                    "end_ms": d.end_ms,
                })

    flag = " *** 0 PHONES ***" if total == 0 else ""
    print(f"Surah {s:>3}: assessed={total:>4}  pass={n_pass:>4}  minor={n_minor:>4}  major={n_major:>4}  skipped={n_skipped:>3}{flag}")
    grand_total += total
    grand_pass += n_pass
    grand_minor += n_minor
    grand_major += n_major
    grand_skipped += n_skipped

print(f"\n{'TOTAL':>9}: assessed={grand_total:>4}  pass={grand_pass:>4}  minor={grand_minor:>4}  major={grand_major:>4}  skipped={grand_skipped:>3}")

if major_phones:
    print(f"\n--- MAJOR errors (F2 > 2500 Hz): {len(major_phones)} phones ---")
    print(f"{'Surah':>5} {'Ayah':>4} {'Word':<20} {'IPA':<6} {'Rule':<40} {'F2 Hz':>8}")
    for mp in major_phones:
        print(f"{mp['surah']:>5} {mp['ayah']:>4} {mp['word']:<20} {mp['ipa']:<6} {mp['rule']:<40} {mp['f2_hz']:>8.1f}")
else:
    print("\n--- No MAJOR errors (F2 > 2500 Hz) found ---")

print(f"\n--- Sample phones (up to 30) ---")
print(f"{'Surah':>5} {'Ayah':>4} {'Word':<15} {'IPA':<6} {'Rule':<40} {'F2 Hz':>8} {'Verdict':<20} {'Start ms':>9} {'End ms':>9}")
for sp in sample_phones:
    print(f"{sp['surah']:>5} {sp['ayah']:>4} {sp['word']:<15} {sp['ipa']:<6} {sp['rule']:<40} {sp['f2_hz']:>8.1f} {sp['verdict']:<20} {sp['start_ms']:>9.1f} {sp['end_ms']:>9.1f}")
