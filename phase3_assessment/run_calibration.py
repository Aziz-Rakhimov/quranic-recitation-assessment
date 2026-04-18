#!/usr/bin/env python3
"""Run adaptive harakah calibration on available surahs and report results."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phase3_assessment.utils.loader import load_surah, VALIDATION_DIR
from phase3_assessment.calibration import (
    calibrate,
    calibrate_multi_surah,
    collect_short_vowels,
    collect_madd_tabii,
)

AVAILABLE_SURAHS = [1, 36, 56, 67, 93, 97, 113, 114]


def main():
    print("=" * 70)
    print("  PHASE 3 — Adaptive Harakah Calibration Report (reciter_2)")
    print("=" * 70)

    all_data = []
    for s in AVAILABLE_SURAHS:
        json_path = VALIDATION_DIR / f"surah_{s}" / f"surah_{s}_aligned.json"
        if not json_path.exists():
            continue
        data = load_surah(s)
        cal = calibrate(data)
        all_data.append(data)

        dflt = " DEFAULT" if cal.is_default else ""
        print(f"\n  Surah {s}: {data.num_ayahs} ayahs{dflt}")
        print(f"    Short vowels: n={cal.short_vowel_count:>4}  "
              f"median={cal.short_vowel_median_ms:>5.0f}ms  std={cal.short_vowel_std_ms:>4.0f}ms")
        print(f"    Madd tabii:   n={cal.madd_tabii_count:>4}  "
              f"median={cal.madd_tabii_median_ms:>5.0f}ms  std={cal.madd_tabii_std_ms:>4.0f}ms")
        print(f"    Ratio: {cal.ratio:.2f}x  |  Harakah: {cal.harakah_ms:.1f}ms  "
              f"|  Tolerance: {cal.tolerance_factor:.1f}x")

    if len(all_data) > 1:
        cal = calibrate_multi_surah(all_data)
        print(f"\n{'═' * 70}")
        print(f"  COMBINED ({len(all_data)} surahs): "
              f"n_short={cal.short_vowel_count} n_madd={cal.madd_tabii_count}")
        print(f"  Harakah={cal.harakah_ms:.1f}ms  Ratio={cal.ratio:.2f}x  "
              f"Default={cal.is_default}")


if __name__ == "__main__":
    main()
