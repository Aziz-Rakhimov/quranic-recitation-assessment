"""
Phase 3 Multi-Ayah Assessment Pipeline.

Orchestrates end-to-end assessment of a continuous multi-ayah recording:
  1. Preprocess the full WAV (noise reduction, etc.)
  2. Detect ayah boundaries in the audio (timestamps only)
  3. Run Phase 2 alignment ONCE on the full audio against all ayahs
  4. Split alignment results by ayah boundary, enrich per-ayah
  5. Run Phase 3 assessment on aligned data
  6. Return a unified JSON report

Usage:
    from phase3_assessment.multi_ayah_pipeline import assess_recitation

    result = assess_recitation(
        wav_path="/tmp/surah1_full.wav",
        surah=1, start_ayah=1, end_ayah=7,
    )
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import List, Optional

from phase2_alignment.preprocessor import PreprocessorConfig, preprocess_audio
from phase2_alignment.ayah_segmenter import segment_ayahs
from phase2_alignment.alignment_pipeline import (
    AlignmentPipeline, AlignedVerse, IPA_TO_MFA,
)
from phase2_alignment.textgrid_parser import parse_textgrid, AlignedUtterance
from phase2_alignment.postprocessor import PostprocessorConfig, postprocess_alignment
from phase3_assessment.models import (
    AyahReport, CalibrationResult, SurahData, Verse, Word, Phone,
)
from phase3_assessment.calibration import SHORT_VOWELS
from phase3_assessment.pipeline import assess_surah
from phase2_alignment.word_verification import verify_ayah
from phase2_alignment.models import WordVerificationReport, VerifiedAyah

logger = logging.getLogger(__name__)

# MFA invocation — use conda env if 'mfa' is not directly available
_MFA_CONDA_ENV = "aligner"


COMBINED_CAL_FLOOR_MS = 30.0
COMBINED_CAL_DEFAULT_HARAKAH_MS = 107.0
COMBINED_CAL_MIN_PHONES = 5

# Rule prefixes that disqualify a phone from the harakah calibration pool
_EXCLUDE_RULE_PREFIXES = ("madd_", "ghunnah_", "qalqalah")


def _collect_combined_harakah_pool(surah_data: SurahData) -> List[float]:
    """Collect short vowel durations from ALL verses for combined calibration.

    Filters: IPA must be a short vowel, no madd/ghunnah/qalqalah rules,
    high alignment confidence, not skipped/geminate/verse-final,
    and duration above the 30ms floor.
    """
    pool: List[float] = []
    for verse in surah_data.verses:
        for _word, phone in verse.all_phones():
            if phone.ipa not in SHORT_VOWELS:
                continue
            if phone.alignment_confidence != "high":
                continue
            if phone.skip_assessment or phone.is_verse_final or phone.geminate_pair:
                continue
            if phone.duration_ms < COMBINED_CAL_FLOOR_MS:
                continue
            if any(r.startswith(p) for p in _EXCLUDE_RULE_PREFIXES for r in phone.tajweed_rules):
                continue
            pool.append(phone.duration_ms)
    return pool


def _calibrate_combined(surah_data: SurahData) -> CalibrationResult:
    """Compute a single harakah_ms from ALL ayah segments combined.

    Returns a CalibrationResult with the combined median or falls back
    to the default if fewer than COMBINED_CAL_MIN_PHONES are found.
    """
    pool = _collect_combined_harakah_pool(surah_data)
    n = len(pool)

    if n >= COMBINED_CAL_MIN_PHONES:
        harakah_ms = statistics.median(pool)
        return CalibrationResult(
            harakah_ms=harakah_ms,
            short_vowel_median_ms=harakah_ms,
            madd_tabii_median_ms=0.0,
            short_vowel_count=n,
            madd_tabii_count=0,
            ratio=0.0,
            short_vowel_std_ms=statistics.stdev(pool) if n > 1 else 0.0,
            madd_tabii_std_ms=0.0,
            is_default=False,
            tolerance_factor=1.0,
        )
    else:
        logger.warning(
            "Combined calibration: only %d phones (need %d), falling back to default",
            n, COMBINED_CAL_MIN_PHONES,
        )
        return CalibrationResult(
            harakah_ms=COMBINED_CAL_DEFAULT_HARAKAH_MS,
            short_vowel_median_ms=statistics.median(pool) if pool else 0.0,
            madd_tabii_median_ms=0.0,
            short_vowel_count=n,
            madd_tabii_count=0,
            ratio=0.0,
            short_vowel_std_ms=statistics.stdev(pool) if n > 1 else 0.0,
            madd_tabii_std_ms=0.0,
            is_default=True,
            tolerance_factor=1.6,
        )


def _find_mfa_command() -> List[str]:
    """Return the command prefix needed to invoke MFA."""
    # Try direct invocation first
    try:
        result = subprocess.run(
            ["mfa", "version"], capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return ["mfa"]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fall back to conda run
    return ["conda", "run", "-n", _MFA_CONDA_ENV, "mfa"]


def _run_mfa_alignment(
    corpus_dir: str,
    dict_path: str,
    output_dir: str,
    acoustic_model: str = "arabic",
) -> None:
    """Run MFA forced alignment, using conda env if needed."""
    mfa_prefix = _find_mfa_command()
    cmd = mfa_prefix + [
        "align", corpus_dir, dict_path, acoustic_model, output_dir,
        "--clean",
    ]
    logger.info("Running MFA: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"MFA alignment failed:\n{result.stderr}")
    logger.info("MFA alignment complete")


# ── Full-audio alignment approach ───────────────────────────────────────


def _generate_combined_lab(
    surah: int,
    start_ayah: int,
    end_ayah: int,
    corpus_dir: str,
    file_id: str,
    project_root: str,
) -> None:
    """Generate a single .lab file with all ayah texts concatenated."""
    quran_json = os.path.join(project_root, "data", "quran_text", "quran_hafs.json")
    with open(quran_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    lookup = {}
    for s in data["surahs"]:
        for a in s["ayahs"]:
            lookup[(s["number"], a["number"])] = a["text"]

    WAQF = set(
        "\u06D6\u06D7\u06D8\u06D9\u06DA\u06DB\u06DC\u06DD"
        "\u06DE\u06DF\u06E0\u06E2\u06ED"
    )

    texts = []
    for ayah_num in range(start_ayah, end_ayah + 1):
        key = (surah, ayah_num)
        if key not in lookup:
            logger.warning("surah %d, ayah %d not in quran_hafs.json", surah, ayah_num)
            continue
        text = unicodedata.normalize("NFC", lookup[key])
        text = text.replace("\u0640", "")  # strip kashida
        text = "".join(c for c in text if c not in WAQF)
        texts.append(text)

    combined = " ".join(texts)
    lab_path = os.path.join(corpus_dir, f"{file_id}.lab")
    with open(lab_path, "w", encoding="utf-8") as f:
        f.write(combined)

    logger.info(
        "Generated combined .lab for ayahs %d-%d (%d words)",
        start_ayah, end_ayah, len(combined.split()),
    )


def _split_alignment_by_ayah(
    full_alignment: AlignedUtterance,
    segments: List[dict],
    surah: int,
    start_ayah: int,
    end_ayah: int,
    alignment_pipeline: AlignmentPipeline,
) -> List[AlignedVerse]:
    """Split full-audio alignment into per-ayah AlignedVerse objects.

    Uses segment timestamps from the ayah segmenter to determine which
    words belong to which ayah based on word midpoint.
    """
    # Build ayah time windows from segment boundaries
    ayah_windows = []
    for seg in segments:
        ayah_windows.append({
            "ayah": seg["ayah"],
            "start_s": seg["start_ms"] / 1000.0,
            "end_s": seg["end_ms"] / 1000.0,
        })

    # Assign words to ayahs by midpoint
    words_by_ayah: dict[int, list] = {seg["ayah"]: [] for seg in segments}

    for word in full_alignment.words:
        midpoint = (word.start + word.end) / 2.0
        assigned = False
        for win in ayah_windows:
            if win["start_s"] <= midpoint <= win["end_s"]:
                words_by_ayah[win["ayah"]].append(word)
                assigned = True
                break
        if not assigned:
            # Assign to nearest ayah by center distance
            min_dist = float("inf")
            nearest_ayah = segments[0]["ayah"]
            for win in ayah_windows:
                center = (win["start_s"] + win["end_s"]) / 2.0
                dist = abs(midpoint - center)
                if dist < min_dist:
                    min_dist = dist
                    nearest_ayah = win["ayah"]
            words_by_ayah[nearest_ayah].append(word)
            logger.warning(
                "Word '%s' at %.2fs assigned to nearest ayah %d",
                word.word, midpoint, nearest_ayah,
            )

    # For each ayah, create a synthetic AlignedUtterance and merge with Phase 1
    results = []
    for ayah_num in range(start_ayah, end_ayah + 1):
        words = words_by_ayah.get(ayah_num, [])
        if not words:
            logger.warning("No words assigned to ayah %d", ayah_num)
            continue

        ayah_start = words[0].start
        ayah_end = words[-1].end
        duration = ayah_end - ayah_start

        file_id = f"{surah:03d}_{ayah_num:03d}"
        synthetic = AlignedUtterance(
            file_id=file_id,
            duration=duration,
            words=words,
        )

        try:
            phase1_output = alignment_pipeline.phase1.process_verse(
                surah=surah, ayah=ayah_num,
            )
            ps = phase1_output.phoneme_sequence
            ann = phase1_output.annotated_sequence
            rule_index = alignment_pipeline._build_rule_index(ann)

            aligned_verse = alignment_pipeline._merge(
                surah=surah,
                ayah=ayah_num,
                phase1_seq=ps,
                annotated_seq=ann,
                alignment=synthetic,
                rule_index=rule_index,
            )
            results.append(aligned_verse)
        except Exception as e:
            logger.error("Failed to merge ayah %d: %s", ayah_num, e)

    return results


def _run_phase2_full_audio(
    cleaned_wav: str,
    segments: List[dict],
    surah: int,
    start_ayah: int,
    end_ayah: int,
    alignment_pipeline: AlignmentPipeline,
) -> List[AlignedVerse]:
    """Run Phase 2 alignment on the FULL audio with all ayahs in one pass.

    Steps:
      1. Place the full WAV in the MFA corpus (one file)
      2. Generate one combined .lab with all ayah texts concatenated
      3. Generate pronunciation dictionary covering all ayahs
      4. Run MFA ONCE on the full audio
      5. Parse the single TextGrid result
      6. Split words by ayah boundary timestamps → per-ayah AlignedVerse
    """
    work_dir = tempfile.mkdtemp(prefix="mfa_full_")
    corpus_dir = os.path.join(work_dir, "corpus")
    output_dir = os.path.join(work_dir, "output")
    dict_path = os.path.join(work_dir, "full_audio.dict")
    os.makedirs(corpus_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    file_id = f"{surah:03d}_full"

    try:
        # Step 1: Copy full audio to corpus
        wav_dest = os.path.join(corpus_dir, f"{file_id}.wav")
        shutil.copy2(cleaned_wav, wav_dest)

        # Step 2: Generate combined .lab file
        _generate_combined_lab(
            surah, start_ayah, end_ayah, corpus_dir, file_id,
            alignment_pipeline.project_root,
        )

        # Step 3: Generate dictionary covering all ayahs
        alignment_pipeline._generate_dictionary(surah, end_ayah, dict_path)

        # Step 4: Run MFA ONCE on the full audio
        logger.info("Running MFA alignment on full audio (single invocation)")
        _run_mfa_alignment(corpus_dir, dict_path, output_dir)

        # Step 5: Parse the single TextGrid
        textgrid_path = os.path.join(output_dir, f"{file_id}.TextGrid")
        if not os.path.exists(textgrid_path):
            raise FileNotFoundError(
                f"MFA did not produce TextGrid: {textgrid_path}"
            )
        full_alignment = parse_textgrid(textgrid_path)
        logger.info(
            "Full-audio alignment: %d words, %d phones",
            full_alignment.num_words, full_alignment.num_phones,
        )

        # Step 6: Split alignment by ayah boundaries
        results = _split_alignment_by_ayah(
            full_alignment, segments, surah, start_ayah, end_ayah,
            alignment_pipeline,
        )

        return results

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _build_surah_data(
    surah: int,
    aligned_verses: List[AlignedVerse],
) -> SurahData:
    """Build a SurahData object from AlignedVerse results."""
    verse_dicts = [av.to_dict() for av in aligned_verses]
    return SurahData(
        surah=surah,
        num_ayahs=len(verse_dicts),
        verses=[Verse.from_dict(vd) for vd in verse_dicts],
    )


def _build_ayah_output(
    report: AyahReport,
    boundary_confidence: str,
) -> dict:
    """Build the per-ayah section of the unified output."""
    # Categorize errors by assessor rule name
    assessor_errors: dict[str, list] = {}
    for error in report.errors:
        rule = error.rule
        if rule not in assessor_errors:
            assessor_errors[rule] = []
        assessor_errors[rule].append(error.to_dict())

    # Group into assessor categories
    assessor_mapping = {
        "madd": [
            "madd_tabii", "madd_muttasil", "madd_munfasil", "madd_lazim",
            "madd_aarid", "madd_leen", "madd_badal", "madd_silah_kubra",
            "madd_silah_sughra",
        ],
        "ghunnah": [
            "ghunnah_mushaddadah_noon", "ghunnah_mushaddadah_meem",
            "ghunnah_idgham_with_ghunnah",
        ],
        "qalqalah": ["qalqalah", "qalqalah_with_shaddah"],
        "ikhfa": ["ikhfa_haqiqi", "ikhfa_shafawi", "ikhfa_meem_saakin"],
        "vowel_backing": ["emphatic_backing", "pharyngeal_backing"],
        "tafkhim": ["tafkhim"],
    }

    assessor_results = {}
    for category, rule_names in assessor_mapping.items():
        category_errors = []
        for rn in rule_names:
            if rn in assessor_errors:
                category_errors.extend(assessor_errors[rn])
        assessor_results[category] = {
            "errors": category_errors,
            "error_count": len(category_errors),
        }

    phones_passed = report.total_phones_assessed - sum(
        1 for e in report.errors if e.severity in ("major", "minor")
    )

    return {
        "ayah": report.ayah,
        "boundary_confidence": boundary_confidence,
        "errors": [e.to_dict() for e in report.errors],
        "phones_assessed": report.total_phones_assessed,
        "phones_passed": max(0, phones_passed),
        "phones_skipped": report.phones_skipped,
        "assessor_results": assessor_results,
    }


def _load_expected_words(surah: int, ayah: int) -> List[str]:
    """Load expected Arabic words for a given surah/ayah from quran_hafs.json."""
    quran_path = Path(__file__).resolve().parent.parent / "data" / "quran_text" / "quran_hafs.json"
    with open(quran_path, "r", encoding="utf-8") as f:
        quran_data = json.load(f)

    for s in quran_data["surahs"]:
        if s["number"] != surah:
            continue
        for a in s["ayahs"]:
            if a["number"] == ayah:
                return a["text"].split()

    logger.warning("Ayah not found in quran_hafs.json: surah %d, ayah %d", surah, ayah)
    return []


def assess_recitation(
    wav_path: str,
    surah: int,
    start_ayah: int,
    end_ayah: int,
    preprocessor_config: PreprocessorConfig = None,
) -> dict:
    """Run the full multi-ayah assessment pipeline.

    Parameters
    ----------
    wav_path : str
        Path to a 16 kHz mono WAV containing continuous recitation
        of ayahs start_ayah through end_ayah.
    surah : int
        Surah number.
    start_ayah : int
        First ayah number in the recording.
    end_ayah : int
        Last ayah number in the recording.
    preprocessor_config : PreprocessorConfig, optional
        Audio preprocessing options. Defaults to all disabled.

    Returns
    -------
    dict — unified assessment JSON with per-ayah results and overall score.
    """
    if preprocessor_config is None:
        preprocessor_config = PreprocessorConfig()

    expected_count = end_ayah - start_ayah + 1

    # ── Step 1: Preprocess full audio ────────────────────────────────
    logger.info("Step 1: Preprocessing audio %s", wav_path)
    preprocess_result = preprocess_audio(wav_path, preprocessor_config)
    cleaned_wav = preprocess_result["cleaned_wav_path"]

    # ── Step 2: Detect ayah boundaries (timestamps only) ────────────
    logger.info("Step 2: Detecting ayah boundaries for %d ayahs", expected_count)
    segments = segment_ayahs(cleaned_wav, surah, start_ayah, end_ayah)

    segmentation_warnings: List[str] = []
    if segments and segments[0].get("_warnings"):
        segmentation_warnings = segments[0]["_warnings"]

    if len(segments) != expected_count:
        segmentation_warnings.append(
            f"Segmentation produced {len(segments)} segments "
            f"instead of expected {expected_count}"
        )

    # ── Step 2.5: Word Verification (runs independently of MFA) ──────
    logger.info("Step 2.5: Running word verification via Whisper")
    verification_report = WordVerificationReport(
        surah=surah,
        start_ayah=start_ayah,
        end_ayah=end_ayah,
    )

    for seg in segments:
        expected_words = _load_expected_words(surah, seg["ayah"])
        seg_wav = seg.get("segment_wav_path")
        if expected_words and seg_wav and os.path.exists(seg_wav):
            verified_ayah = verify_ayah(
                audio_path=seg_wav,
                surah=surah,
                ayah=seg["ayah"],
                expected_words=expected_words,
            )
            verification_report.ayahs.append(verified_ayah)
            verification_report.total_word_errors += len(verified_ayah.word_errors)

    logger.info(
        "Word verification complete: %d word errors across %d ayahs",
        verification_report.total_word_errors, len(verification_report.ayahs),
    )

    # Clean up segment WAV files — we only need their timestamps
    for seg in segments:
        wav_path_seg = seg.get("segment_wav_path")
        if wav_path_seg and os.path.exists(wav_path_seg):
            try:
                os.unlink(wav_path_seg)
            except OSError:
                pass

    # ── Step 3: Align full audio once against all ayahs ─────────────
    logger.info("Step 3: Running Phase 2 alignment on full audio (single MFA call)")

    alignment_pipeline = AlignmentPipeline()
    aligned_verses = _run_phase2_full_audio(
        cleaned_wav, segments, surah, start_ayah, end_ayah,
        alignment_pipeline,
    )

    # Track which ayahs were successfully aligned
    aligned_ayah_nums = {av.ayah for av in aligned_verses}
    for seg in segments:
        if seg["ayah"] not in aligned_ayah_nums:
            segmentation_warnings.append(
                f"Phase 2 alignment failed for ayah {seg['ayah']}"
            )

    if not aligned_verses:
        return {
            "surah": surah,
            "start_ayah": start_ayah,
            "end_ayah": end_ayah,
            "total_ayahs_assessed": 0,
            "total_errors": 0,
            "total_phones_assessed": 0,
            "overall_score": 0.0,
            "segmentation_warnings": segmentation_warnings + [
                "No ayahs could be aligned"
            ],
            "ayahs": [],
        }

    # ── Step 4: Build SurahData and run Phase 3 assessment ──────────
    logger.info("Step 4: Running Phase 3 assessment")

    surah_data = _build_surah_data(surah, aligned_verses)

    # ── Apply word verification results to Word objects ─────────────
    for verse in surah_data.verses:
        skipped_indices = verification_report.get_skipped_indices_for_ayah(verse.ayah)
        word_errors = verification_report.get_word_errors_for_ayah(verse.ayah)

        for word in verse.words:
            if word.word_index in skipped_indices:
                word.skip_tajwid = True
                for we in word_errors:
                    if we.word_position == word.word_index:
                        word.word_error_type = we.error_type
                        break
                for phone in word.phones:
                    phone.skip_assessment = True

    # Post-alignment processing (no-op when flags are False)
    postprocess_config = PostprocessorConfig()
    postprocess_alignment(surah_data, [], postprocess_config)

    # Combined multi-ayah calibration: one harakah_ms from ALL segments
    cal = _calibrate_combined(surah_data)
    logger.info(
        "Combined calibration: harakah_ms=%.1f from %d phones",
        cal.harakah_ms, cal.short_vowel_count,
    )

    # Assess all ayahs with the shared calibration
    reports = assess_surah(surah_data, cal)

    # ── Step 5: Build unified output ────────────────────────────────
    logger.info("Step 5: Building unified output")

    # Map segment metadata by ayah number
    meta_by_ayah = {seg["ayah"]: seg for seg in segments}

    ayah_outputs = []
    total_errors = 0
    total_assessed = 0
    total_passed = 0

    for report in reports:
        seg_meta = meta_by_ayah.get(report.ayah, {})
        bc = seg_meta.get("boundary_confidence", "low")

        ayah_out = _build_ayah_output(report, bc)
        ayah_outputs.append(ayah_out)

        total_errors += len(report.errors)
        total_assessed += report.total_phones_assessed
        total_passed += ayah_out["phones_passed"]

    overall_score = round(
        (total_passed / max(total_assessed, 1)) * 100, 1
    )

    result = {
        "surah": surah,
        "start_ayah": start_ayah,
        "end_ayah": end_ayah,
        "calibration": {
            "harakah_ms": round(cal.harakah_ms, 1),
            "phones_used_for_calibration": cal.short_vowel_count,
            "calibration_source": "combined_multi_ayah",
        },
        "total_ayahs_assessed": len(reports),
        "total_errors": total_errors,
        "total_phones_assessed": total_assessed,
        "overall_score": overall_score,
        "segmentation_warnings": segmentation_warnings,
        "ayahs": ayah_outputs,
    }

    # ── Attach word verification report ───────────────────────────────
    result["word_verification"] = {
        "total_word_errors": verification_report.total_word_errors,
        "ayahs": [
            {
                "ayah": va.ayah,
                "verified_word_indices": sorted(va.verified_word_indices),
                "skipped_word_indices": sorted(va.skipped_word_indices),
                "word_errors": [
                    {
                        "error_type": we.error_type,
                        "expected_word": we.expected_word,
                        "detected_word": we.detected_word,
                        "word_position": we.word_position,
                    }
                    for we in va.word_errors
                ],
            }
            for va in verification_report.ayahs
        ],
    }

    logger.info(
        "Assessment complete: %d ayahs, %d tajwid errors, %d word errors, %.1f%% score",
        len(reports), total_errors, verification_report.total_word_errors, overall_score,
    )

    return result


# ===================================================================
# Quick CLI test
# ===================================================================
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s",
        stream=sys.stderr,
    )

    wav = "/Users/aziz_rakhimov/Desktop/quran_vc_dataset/reciter_2/surah_1_wav16k/001_001.wav"

    result = assess_recitation(wav_path=wav, surah=1, start_ayah=1, end_ayah=1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
