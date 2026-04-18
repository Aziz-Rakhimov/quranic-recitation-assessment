"""
Phase 2 Post-Alignment Processor — runs AFTER MFA alignment, BEFORE Phase 3.

Fixes known MFA alignment artifacts in the Phase 2 JSON output.
All behaviour is opt-in via boolean flags in PostprocessorConfig so that
clean studio audio passes through unchanged.

Usage:
    from phase2_alignment.postprocessor import PostprocessorConfig, postprocess_alignment

    config = PostprocessorConfig(enable_spn_detection=True)
    result = postprocess_alignment(surah_data, silence_segments=[], config=config)
    surah_data = result["surah_data"]
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple

from phase3_assessment.models import SurahData

logger = logging.getLogger(__name__)


# ── Configuration ────────────────────────────────────────────────────────

@dataclass
class PostprocessorConfig:
    """All flags default to False — clean audio passes through unchanged."""
    enable_spn_detection: bool = False
    enable_pause_flagging: bool = False

    # Pause-flagging tunables
    pause_overlap_threshold_ms: float = 200.0


# ── SPN noise markers ───────────────────────────────────────────────────

_SPN_MARKERS = {"spn", "sil", "<unk>"}


# ── 1. SPN Detection ────────────────────────────────────────────────────

def _detect_spn(surah_data: SurahData) -> dict:
    """Scan for MFA spoken-noise phones and mark them + neighbors.

    Returns summary dict with spn_count and affected_neighbors.
    """
    spn_count = 0
    affected_neighbors = 0

    for verse in surah_data.verses:
        # Build flat phone list with (word, phone, word_idx, phone_idx)
        flat: List[Tuple] = []
        for w in verse.words:
            for pi, p in enumerate(w.phones):
                flat.append((w, p, w.word_index, pi))

        for i, (word, phone, w_idx, p_idx) in enumerate(flat):
            if phone.ipa in _SPN_MARKERS or phone.mfa in _SPN_MARKERS:
                phone.skip_assessment = True
                spn_count += 1

                logger.info(
                    "SPN detected: surah %d ayah %d word '%s' "
                    "phone_idx=%d ipa='%s' [%.3f–%.3f]",
                    verse.surah, verse.ayah, word.text,
                    p_idx, phone.ipa, phone.start, phone.end,
                )

                # Mark preceding neighbor
                if i > 0:
                    _, prev_phone, _, _ = flat[i - 1]
                    if prev_phone.alignment_confidence != "low":
                        prev_phone.alignment_confidence = "low"
                        affected_neighbors += 1

                # Mark following neighbor
                if i < len(flat) - 1:
                    _, next_phone, _, _ = flat[i + 1]
                    if next_phone.alignment_confidence != "low":
                        next_phone.alignment_confidence = "low"
                        affected_neighbors += 1

    return {"spn_count": spn_count, "affected_neighbors": affected_neighbors}


# ── 2. Pause / Silence Phone Flagging ──────────────────────────────────

def _flag_pause_phones(
    surah_data: SurahData,
    silence_segments: List[dict],
    overlap_threshold_ms: float,
) -> int:
    """Flag phones whose time windows overlap with silence segments.

    Returns count of phones flagged.
    """
    if not silence_segments:
        return 0

    flagged = 0

    for verse in surah_data.verses:
        for word in verse.words:
            for phone in word.phones:
                phone_start_ms = phone.start * 1000.0
                phone_end_ms = phone.end * 1000.0

                for seg in silence_segments:
                    seg_start = seg["start_ms"]
                    seg_end = seg["end_ms"]

                    # Compute overlap
                    overlap_start = max(phone_start_ms, seg_start)
                    overlap_end = min(phone_end_ms, seg_end)
                    overlap_ms = max(0.0, overlap_end - overlap_start)

                    if overlap_ms > overlap_threshold_ms:
                        if phone.alignment_confidence != "low":
                            phone.alignment_confidence = "low"
                            flagged += 1
                        break  # already flagged, no need to check more segments

    return flagged


# ── Entry point ──────────────────────────────────────────────────────────

def postprocess_alignment(
    surah_data: SurahData,
    silence_segments: List[dict],
    config: PostprocessorConfig,
) -> dict:
    """Run enabled post-alignment fixes on Phase 2 data.

    Parameters
    ----------
    surah_data : SurahData
        Loaded Phase 2 alignment data (modified in-place).
    silence_segments : list of dict
        Each dict has "start_ms" and "end_ms" keys.
        Typically from preprocessor output.
    config : PostprocessorConfig
        Which steps to enable.

    Returns
    -------
    dict with keys:
        surah_data             – the (possibly modified) SurahData
        spn_count              – number of spn phones found
        affected_neighbors     – number of neighbor phones marked low-confidence
        pause_flagged_count    – number of phones flagged due to pause overlap
        postprocessing_applied – list of step names that actually ran
    """
    applied = []
    spn_count = 0
    affected_neighbors = 0
    pause_flagged = 0

    # 1. SPN detection
    if config.enable_spn_detection:
        spn_result = _detect_spn(surah_data)
        spn_count = spn_result["spn_count"]
        affected_neighbors = spn_result["affected_neighbors"]
        if spn_count > 0:
            applied.append("spn_detection")
            logger.info(
                "SPN detection: %d spn phones, %d neighbors affected",
                spn_count, affected_neighbors,
            )

    # 2. Pause flagging
    if config.enable_pause_flagging:
        pause_flagged = _flag_pause_phones(
            surah_data,
            silence_segments,
            config.pause_overlap_threshold_ms,
        )
        if pause_flagged > 0:
            applied.append("pause_flagging")
            logger.info("Pause flagging: %d phones flagged", pause_flagged)

    return {
        "surah_data": surah_data,
        "spn_count": spn_count,
        "affected_neighbors": affected_neighbors,
        "pause_flagged_count": pause_flagged,
        "postprocessing_applied": applied,
    }
