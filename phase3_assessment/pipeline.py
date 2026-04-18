"""Phase 3 pipeline — run all assessments on Phase 2 JSON output."""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional

from phase3_assessment.models import AyahReport, CalibrationResult, SurahData
from phase3_assessment.calibration import calibrate
from phase3_assessment.assessors.madd import assess_madd
from phase3_assessment.assessors.ghunnah import assess_ghunnah
from phase3_assessment.assessors.qalqalah import assess_qalqalah
from phase3_assessment.assessors.ikhfa import assess_ikhfa
from phase3_assessment.assessors.tafkhim import assess_tafkhim
from phase3_assessment.assessors.vowel_backing import assess_vowel_backing
from phase3_assessment.utils.loader import load_surah, VALIDATION_DIR
from phase2_alignment.postprocessor import PostprocessorConfig, postprocess_alignment

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def assess_surah(
    surah_data: SurahData,
    cal: CalibrationResult,
    reciter: str = "reciter_2",
) -> List[AyahReport]:
    """Run all assessments on every ayah of a surah."""
    reports = []

    for verse in surah_data.verses:
        madd_errors, madd_assessed, madd_skipped = assess_madd(verse, cal)
        ghunnah_errors, ghunnah_assessed, ghunnah_skipped = assess_ghunnah(
            verse, cal,
        )
        qalq_errors, qalq_assessed, qalq_skipped, _ = assess_qalqalah(
            verse, cal,
        )
        ikhfa_errors, ikhfa_assessed, ikhfa_skipped, _ = assess_ikhfa(
            verse, cal,
        )
        tafkhim_errors, tafkhim_assessed, tafkhim_skipped, _ = assess_tafkhim(
            verse, cal,
        )
        vb_errors, vb_assessed, vb_skipped, _ = assess_vowel_backing(
            verse, cal,
        )

        report = AyahReport(
            surah=verse.surah,
            ayah=verse.ayah,
            reciter=reciter,
            harakah_ms=cal.harakah_ms,
            errors=(
                madd_errors + ghunnah_errors + qalq_errors + ikhfa_errors
                + tafkhim_errors + vb_errors
            ),
            total_phones_assessed=(
                madd_assessed + ghunnah_assessed + qalq_assessed
                + ikhfa_assessed + tafkhim_assessed + vb_assessed
            ),
            phones_skipped=(
                madd_skipped + ghunnah_skipped + qalq_skipped
                + ikhfa_skipped + tafkhim_skipped + vb_skipped
            ),
        )
        reports.append(report)

    return reports


def run_pipeline(
    surah_nums: List[int],
    reciter: str = "reciter_2",
    output_dir: Optional[Path] = None,
    postprocessor_config: Optional[PostprocessorConfig] = None,
    silence_segments: Optional[List[dict]] = None,
) -> dict:
    """Full Phase 3 pipeline: calibrate per-audio → assess → export."""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if postprocessor_config is None:
        postprocessor_config = PostprocessorConfig()
    if silence_segments is None:
        silence_segments = []

    # Load all surahs
    all_data = []
    for s in surah_nums:
        json_path = VALIDATION_DIR / f"surah_{s}" / f"surah_{s}_aligned.json"
        if json_path.exists():
            all_data.append(load_surah(s))

    # Post-alignment processing (no-op when both flags are False)
    for data in all_data:
        postprocess_alignment(data, silence_segments, postprocessor_config)

    if not all_data:
        raise ValueError("No surah data found")

    # Per-audio (per-surah) adaptive calibration
    surah_cals: dict[int, CalibrationResult] = {}
    for data in all_data:
        surah_cals[data.surah] = calibrate(data)

    # Assess each surah
    all_reports: List[AyahReport] = []
    surah_summaries = []

    for data in all_data:
        cal = surah_cals[data.surah]
        reports = assess_surah(data, cal, reciter)
        all_reports.extend(reports)

        total_assessed = sum(r.total_phones_assessed for r in reports)
        total_skipped = sum(r.phones_skipped for r in reports)

        n_major = sum(1 for r in reports for e in r.errors if e.severity == "major")
        n_minor = sum(1 for r in reports for e in r.errors if e.severity == "minor")
        n_style = sum(1 for r in reports for e in r.errors if e.severity == "style")
        weighted = n_major + 0.5 * n_minor
        score = round(100 * (1 - weighted / max(total_assessed, 1)), 1)
        reliability = "high" if total_assessed >= 10 else "low"

        surah_summaries.append({
            "surah": data.surah,
            "ayahs": data.num_ayahs,
            "harakah_ms": round(cal.harakah_ms, 1),
            "is_default": cal.is_default,
            "tolerance": cal.tolerance_factor,
            "short_n": cal.short_vowel_count,
            "madd_n": cal.madd_tabii_count,
            "errors": n_major + n_minor + n_style,
            "major": n_major,
            "minor": n_minor,
            "style": n_style,
            "assessed": total_assessed,
            "skipped": total_skipped,
            "score": score,
            "score_reliability": reliability,
        })

        # Export per-surah JSON
        surah_report = {
            "surah": data.surah,
            "reciter": reciter,
            "harakah_ms": round(cal.harakah_ms, 1),
            "calibration": {
                "short_vowel_median_ms": round(cal.short_vowel_median_ms, 1),
                "madd_tabii_median_ms": round(cal.madd_tabii_median_ms, 1),
                "ratio": round(cal.ratio, 2),
                "short_vowel_count": cal.short_vowel_count,
                "madd_tabii_count": cal.madd_tabii_count,
                "is_default": cal.is_default,
                "tolerance_factor": cal.tolerance_factor,
            },
            "ayahs": [r.to_dict() for r in reports],
        }
        out_path = output_dir / f"surah_{data.surah}_assessment.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(surah_report, f, ensure_ascii=False, indent=2)

    summary = {
        "reciter": reciter,
        "surahs": surah_summaries,
        "total_errors": sum(s["errors"] for s in surah_summaries),
        "total_assessed": sum(s["assessed"] for s in surah_summaries),
        "total_skipped": sum(s["skipped"] for s in surah_summaries),
    }

    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary
