"""
Phase 2 Ayah Segmenter — splits a multi-ayah WAV into individual ayah segments.

Uses a dual-condition boundary detection approach:
  1. VAD silence (webrtcvad): no speech for >= 800ms
  2. Energy reset: RMS drops below 2% of peak for >= 600ms

Both conditions must be true simultaneously for a boundary to be detected.
This prevents breath pauses mid-ayah from being misidentified as boundaries.

After splitting, validates segment durations against expected phone counts
from Phase 1 and attempts auto-recovery for wrong splits.

Usage:
    from phase2_alignment.ayah_segmenter import segment_ayahs

    segments = segment_ayahs("/tmp/surah1_full.wav", surah=1, start_ayah=1, end_ayah=7)
"""

import logging
import os
import sys
import tempfile
from typing import List, Tuple

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
DEFAULT_MEDIAN_PHONE_DURATION_MS = 120

# Boundary detection defaults
VAD_SILENCE_MIN_MS = 800
ENERGY_RESET_MIN_MS = 600
ENERGY_RESET_THRESHOLD = 0.02  # 2% of peak RMS

# Tighter thresholds for re-split recovery
TIGHT_VAD_SILENCE_MIN_MS = 500
TIGHT_ENERGY_RESET_MIN_MS = 400
TIGHT_ENERGY_RESET_THRESHOLD = 0.01  # 1% of peak RMS

# Duration validation thresholds
SHORT_SEGMENT_RATIO = 0.40   # < 40% of expected → merge with next
LONG_SEGMENT_RATIO = 2.50    # > 250% of expected → attempt re-split


# ── VAD helpers ──────────────────────────────────────────────────────────

def _run_vad_frames(audio: np.ndarray, sample_rate: int = SAMPLE_RATE,
                    aggressiveness: int = 2) -> List[bool]:
    """Run WebRTC VAD and return per-frame (30ms) speech/non-speech flags."""
    import webrtcvad

    vad = webrtcvad.Vad(aggressiveness)
    frame_duration_ms = 30
    frame_size = int(sample_rate * frame_duration_ms / 1000)

    pcm = (audio * 32767).astype(np.int16)
    raw = pcm.tobytes()

    frames = []
    for offset in range(0, len(pcm) - frame_size + 1, frame_size):
        frame_bytes = raw[offset * 2:(offset + frame_size) * 2]
        if len(frame_bytes) < frame_size * 2:
            break
        is_speech = vad.is_speech(frame_bytes, sample_rate)
        frames.append(is_speech)

    return frames


def _compute_rms_frames(audio: np.ndarray, sample_rate: int = SAMPLE_RATE,
                        frame_ms: int = 30) -> np.ndarray:
    """Compute per-frame RMS energy (same frame size as VAD: 30ms)."""
    frame_size = int(sample_rate * frame_ms / 1000)
    n_frames = len(audio) // frame_size
    rms = np.zeros(n_frames)
    for i in range(n_frames):
        frame = audio[i * frame_size:(i + 1) * frame_size]
        rms[i] = float(np.sqrt(np.mean(frame ** 2)))
    return rms


# ── Boundary detection ───────────────────────────────────────────────────

def _detect_boundaries(
    audio: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    vad_silence_min_ms: int = VAD_SILENCE_MIN_MS,
    energy_reset_min_ms: int = ENERGY_RESET_MIN_MS,
    energy_threshold_ratio: float = ENERGY_RESET_THRESHOLD,
) -> List[int]:
    """Detect ayah boundaries using dual VAD+energy condition.

    Returns list of boundary positions in milliseconds (midpoints of
    silence regions that satisfy both conditions).
    """
    frame_ms = 30

    vad_frames = _run_vad_frames(audio, sample_rate, aggressiveness=2)
    rms_frames = _compute_rms_frames(audio, sample_rate, frame_ms)

    n_frames = min(len(vad_frames), len(rms_frames))
    if n_frames == 0:
        return []

    peak_rms = float(np.max(rms_frames))
    if peak_rms < 1e-10:
        return []

    energy_threshold = peak_rms * energy_threshold_ratio

    vad_silence_min_frames = max(1, int(vad_silence_min_ms / frame_ms))
    energy_reset_min_frames = max(1, int(energy_reset_min_ms / frame_ms))

    # Find regions where BOTH conditions are met simultaneously:
    # - VAD says no speech
    # - RMS energy is below threshold
    both_silent = []
    for i in range(n_frames):
        is_vad_silent = not vad_frames[i]
        is_energy_low = rms_frames[i] < energy_threshold
        both_silent.append(is_vad_silent and is_energy_low)

    # Find contiguous runs of dual-silent frames
    boundaries = []
    run_start = None
    run_length = 0

    for i in range(n_frames):
        if both_silent[i]:
            if run_start is None:
                run_start = i
            run_length += 1
        else:
            if run_start is not None:
                # Check if this run satisfies BOTH minimum durations
                vad_run = _count_vad_silent_in_range(vad_frames, run_start, run_start + run_length)
                energy_run = _count_energy_low_in_range(rms_frames, energy_threshold, run_start, run_start + run_length)

                if (vad_run >= vad_silence_min_frames and
                        energy_run >= energy_reset_min_frames):
                    midpoint_ms = int((run_start + run_length / 2) * frame_ms)
                    boundaries.append(midpoint_ms)

                run_start = None
                run_length = 0

    # Handle final run
    if run_start is not None:
        vad_run = _count_vad_silent_in_range(vad_frames, run_start, run_start + run_length)
        energy_run = _count_energy_low_in_range(rms_frames, energy_threshold, run_start, run_start + run_length)
        if (vad_run >= vad_silence_min_frames and
                energy_run >= energy_reset_min_frames):
            midpoint_ms = int((run_start + run_length / 2) * frame_ms)
            boundaries.append(midpoint_ms)

    return boundaries


def _count_vad_silent_in_range(vad_frames: List[bool], start: int, end: int) -> int:
    """Count consecutive VAD-silent frames in a range."""
    count = 0
    for i in range(start, min(end, len(vad_frames))):
        if not vad_frames[i]:
            count += 1
    return count


def _count_energy_low_in_range(rms_frames: np.ndarray, threshold: float,
                               start: int, end: int) -> int:
    """Count frames with energy below threshold in a range."""
    count = 0
    for i in range(start, min(end, len(rms_frames))):
        if rms_frames[i] < threshold:
            count += 1
    return count


# ── Segment extraction ───────────────────────────────────────────────────

def _split_at_boundaries(
    audio: np.ndarray,
    boundaries_ms: List[int],
    sample_rate: int = SAMPLE_RATE,
) -> List[dict]:
    """Split audio at boundary positions, returning segment info dicts."""
    total_ms = int(len(audio) / sample_rate * 1000)
    segments = []

    # Create split points: [0, boundary1, boundary2, ..., total_ms]
    split_points = [0] + boundaries_ms + [total_ms]

    for i in range(len(split_points) - 1):
        start_ms = split_points[i]
        end_ms = split_points[i + 1]
        duration_ms = end_ms - start_ms

        if duration_ms <= 0:
            continue

        start_sample = int(start_ms / 1000 * sample_rate)
        end_sample = int(end_ms / 1000 * sample_rate)
        segment_audio = audio[start_sample:end_sample]

        # Skip near-empty segments (< 100ms)
        if duration_ms < 100:
            continue

        segments.append({
            "audio": segment_audio,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": duration_ms,
        })

    return segments


def _write_segment_wav(segment_audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> str:
    """Write a segment to a temporary WAV file."""
    fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="ayah_seg_")
    os.close(fd)
    sf.write(tmp_path, segment_audio, sample_rate)
    return tmp_path


# ── Phone count from Phase 1 ────────────────────────────────────────────

def _get_expected_phone_counts(surah: int, start_ayah: int, end_ayah: int) -> dict:
    """Get expected phone count per ayah from Phase 1 symbolic pipeline.

    Returns {ayah_num: phone_count}.
    """
    # Add project root and src to path for Phase 1 imports
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    src_path = os.path.join(project_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from symbolic_layer.pipeline import SymbolicLayerPipeline
    pipeline = SymbolicLayerPipeline()

    counts = {}
    for ayah in range(start_ayah, end_ayah + 1):
        try:
            output = pipeline.process_verse(surah=surah, ayah=ayah)
            counts[ayah] = len(output.phoneme_sequence.phonemes)
        except Exception as e:
            logger.warning("Could not get phone count for %d:%d: %s", surah, ayah, e)
            counts[ayah] = 0

    return counts


# ── Auto-recovery ────────────────────────────────────────────────────────

def _expected_duration_ms(phone_count: int) -> float:
    """Estimate expected segment duration from phone count."""
    return phone_count * DEFAULT_MEDIAN_PHONE_DURATION_MS


def _attempt_resplit(
    segment_audio: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
) -> List[dict]:
    """Try to re-split a segment using tighter thresholds."""
    boundaries = _detect_boundaries(
        segment_audio,
        sample_rate,
        vad_silence_min_ms=TIGHT_VAD_SILENCE_MIN_MS,
        energy_reset_min_ms=TIGHT_ENERGY_RESET_MIN_MS,
        energy_threshold_ratio=TIGHT_ENERGY_RESET_THRESHOLD,
    )

    if not boundaries:
        return []

    return _split_at_boundaries(segment_audio, boundaries, sample_rate)


def _recover_segments(
    segments: List[dict],
    expected_count: int,
    phone_counts: dict,
    start_ayah: int,
) -> Tuple[List[dict], List[str]]:
    """Validate and recover segments against expected ayah phone counts.

    Returns (recovered_segments, warnings).
    """
    warnings = []

    # First pass: merge short segments
    merged = []
    i = 0
    while i < len(segments):
        seg = segments[i]
        ayah_idx = min(i, expected_count - 1)
        ayah_num = start_ayah + ayah_idx
        phone_count = phone_counts.get(ayah_num, 0)

        if phone_count > 0:
            expected_dur = _expected_duration_ms(phone_count)
            if seg["duration_ms"] < expected_dur * SHORT_SEGMENT_RATIO:
                # Too short — merge with next segment
                if i + 1 < len(segments):
                    next_seg = segments[i + 1]
                    combined_audio = np.concatenate([seg["audio"], next_seg["audio"]])
                    merged_seg = {
                        "audio": combined_audio,
                        "start_ms": seg["start_ms"],
                        "end_ms": next_seg["end_ms"],
                        "duration_ms": seg["duration_ms"] + next_seg["duration_ms"],
                        "boundary_confidence": "recovered",
                    }
                    merged.append(merged_seg)
                    warnings.append(
                        f"Ayah {ayah_num}: segment too short "
                        f"({seg['duration_ms']}ms < {int(expected_dur * SHORT_SEGMENT_RATIO)}ms), "
                        f"merged with next"
                    )
                    i += 2
                    continue
                else:
                    seg["boundary_confidence"] = "low"
                    warnings.append(
                        f"Ayah {ayah_num}: segment too short but no next segment to merge"
                    )

        if "boundary_confidence" not in seg:
            seg["boundary_confidence"] = "high"
        merged.append(seg)
        i += 1

    # Second pass: re-split long segments
    final = []
    for j, seg in enumerate(merged):
        ayah_idx = min(j, expected_count - 1)
        ayah_num = start_ayah + ayah_idx
        phone_count = phone_counts.get(ayah_num, 0)

        if phone_count > 0:
            expected_dur = _expected_duration_ms(phone_count)
            if seg["duration_ms"] > expected_dur * LONG_SEGMENT_RATIO:
                # Too long — try re-split with tighter thresholds
                sub_segments = _attempt_resplit(seg["audio"], SAMPLE_RATE)
                if len(sub_segments) >= 2:
                    # Adjust start_ms/end_ms relative to original audio
                    offset = seg["start_ms"]
                    for sub in sub_segments:
                        sub["start_ms"] += offset
                        sub["end_ms"] += offset
                        sub["boundary_confidence"] = "recovered"
                    final.extend(sub_segments)
                    warnings.append(
                        f"Ayah {ayah_num}: segment too long "
                        f"({seg['duration_ms']}ms > {int(expected_dur * LONG_SEGMENT_RATIO)}ms), "
                        f"re-split into {len(sub_segments)} parts"
                    )
                    continue

        final.append(seg)

    return final, warnings


# ── Entry point ──────────────────────────────────────────────────────────

def segment_ayahs(
    wav_path: str,
    surah: int,
    start_ayah: int,
    end_ayah: int,
) -> List[dict]:
    """Segment a multi-ayah WAV file into individual ayah audio segments.

    Parameters
    ----------
    wav_path : str
        Path to the input 16 kHz mono WAV containing multiple ayahs.
    surah : int
        Surah number.
    start_ayah : int
        First ayah number in the recording.
    end_ayah : int
        Last ayah number in the recording.

    Returns
    -------
    List of dicts, one per ayah segment:
        surah, ayah, segment_wav_path, start_ms, end_ms,
        duration_ms, boundary_confidence, expected_phone_count
    """
    expected_count = end_ayah - start_ayah + 1

    # Load audio
    audio, sr = sf.read(wav_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio[:, 0]
    if sr != SAMPLE_RATE:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
        sr = SAMPLE_RATE

    logger.info(
        "Segmenting %s: surah %d, ayahs %d-%d (%d expected), %.1fs audio",
        wav_path, surah, start_ayah, end_ayah, expected_count,
        len(audio) / sr,
    )

    # Get expected phone counts from Phase 1
    phone_counts = _get_expected_phone_counts(surah, start_ayah, end_ayah)

    # Detect boundaries
    boundaries = _detect_boundaries(audio, sr)
    logger.info("Detected %d boundaries → %d segments", len(boundaries), len(boundaries) + 1)

    # Split audio at boundaries
    raw_segments = _split_at_boundaries(audio, boundaries, sr)

    # Check count match
    warnings = []
    if len(raw_segments) != expected_count:
        warnings.append(
            f"Expected {expected_count} segments but detected {len(raw_segments)} — "
            f"attempting recovery"
        )
        logger.warning(warnings[-1])

        # Attempt recovery
        raw_segments, recovery_warnings = _recover_segments(
            raw_segments, expected_count, phone_counts, start_ayah
        )
        warnings.extend(recovery_warnings)

        if len(raw_segments) != expected_count:
            warnings.append(
                f"Recovery produced {len(raw_segments)} segments "
                f"(expected {expected_count}) — proceeding with available segments"
            )
            logger.warning(warnings[-1])
    else:
        # Even if count matches, validate durations for confidence tagging
        for i, seg in enumerate(raw_segments):
            ayah_num = start_ayah + i
            pc = phone_counts.get(ayah_num, 0)
            if pc > 0:
                expected_dur = _expected_duration_ms(pc)
                if (seg["duration_ms"] < expected_dur * SHORT_SEGMENT_RATIO or
                        seg["duration_ms"] > expected_dur * LONG_SEGMENT_RATIO):
                    seg["boundary_confidence"] = "low"
                    warnings.append(
                        f"Ayah {ayah_num}: duration {seg['duration_ms']}ms "
                        f"outside expected range for {pc} phones"
                    )

    # Build result list
    results = []
    for i, seg in enumerate(raw_segments):
        ayah_num = start_ayah + i
        if ayah_num > end_ayah:
            ayah_num = end_ayah  # cap at end_ayah for extra segments

        wav_out = _write_segment_wav(seg["audio"], sr)
        pc = phone_counts.get(ayah_num, 0)
        confidence = seg.get("boundary_confidence", "high")

        results.append({
            "surah": surah,
            "ayah": ayah_num,
            "segment_wav_path": wav_out,
            "start_ms": seg["start_ms"],
            "end_ms": seg["end_ms"],
            "duration_ms": seg["duration_ms"],
            "boundary_confidence": confidence,
            "expected_phone_count": pc,
        })

    if warnings:
        for r in results:
            r.setdefault("_warnings", [])
        # Attach warnings to the result set (accessible via first segment)
        if results:
            results[0]["_warnings"] = warnings

    logger.info(
        "Segmentation complete: %d segments, %d warnings",
        len(results), len(warnings),
    )

    return results
