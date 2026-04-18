#!/usr/bin/env python3
"""Run Phase 3 assessment pipeline on all available surahs."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phase3_assessment.pipeline import run_pipeline

AVAILABLE_SURAHS = [1, 36, 56, 67, 93, 97, 113, 114]


def main():
    print("=" * 84)
    print("  PHASE 3 — Acoustic Verification Assessment")
    print("  Reciter: reciter_2 | Calibration: adaptive per-audio")
    print("=" * 84)

    summary = run_pipeline(AVAILABLE_SURAHS)

    print(f"\n  {'Surah':>5} {'Hrkh':>6} {'Assd':>5} {'Skip':>5}"
          f" {'Maj':>4} {'Min':>4} {'Styl':>5} {'Score':>7} {'Reli':>5}")
    print(f"  {'─' * 58}")

    for s in summary["surahs"]:
        reli = "hi" if s["score_reliability"] == "high" else "LOW"
        print(f"  {s['surah']:>5} {s['harakah_ms']:>5.0f}ms {s['assessed']:>5} {s['skipped']:>5}"
              f" {s['major']:>4} {s['minor']:>4} {s['style']:>5} {s['score']:>6.1f}% {reli:>5}")

    tot_a = sum(s['assessed'] for s in summary['surahs'])
    tot_sk = sum(s['skipped'] for s in summary['surahs'])
    tot_M = sum(s['major'] for s in summary['surahs'])
    tot_m = sum(s['minor'] for s in summary['surahs'])
    tot_s = sum(s['style'] for s in summary['surahs'])
    tot_w = tot_M + 0.5 * tot_m
    tot_score = round(100 * (1 - tot_w / max(tot_a, 1)), 1)
    print(f"  {'─' * 58}")
    print(f"  {'TOTAL':>5} {'':>6} {tot_a:>5} {tot_sk:>5}"
          f" {tot_M:>4} {tot_m:>4} {tot_s:>5} {tot_score:>6.1f}%")


if __name__ == "__main__":
    main()
