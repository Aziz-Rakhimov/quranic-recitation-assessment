"""
Phase 2 Full Validation Runner

Processes multiple surahs through the complete pipeline:
  Phase 1 (symbolic) → dictionary + labs → MFA alignment → TextGrid parsing → validation

Produces per-surah JSON exports and a final validation report.
"""

import json
import math
import os
import struct
import sys
import shutil
import subprocess
import unicodedata
import time
import wave
from dataclasses import dataclass, field

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
sys.path.insert(0, PROJECT_ROOT)

from symbolic_layer.pipeline import SymbolicLayerPipeline
from phase2_alignment.textgrid_parser import parse_textgrid, parse_all_textgrids
from phase2_alignment.alignment_pipeline import (
    AlignmentPipeline, AlignedVerse, export_surah_json,
    IPA_TO_MFA, MFA_TO_IPA,
)
from symbolic_layer.utils.unicode_utils import QURANIC_WAQF_SIGNS

# ── Audio utilities (stdlib only: wave, struct, math) ──────────

def get_wav_duration(wav_path: str) -> float:
    """Return WAV file duration in seconds."""
    with wave.open(wav_path, 'rb') as wf:
        return wf.getnframes() / wf.getframerate()


def _read_wav_samples(wav_path: str):
    """Read 16-bit mono WAV samples. Returns (samples, sample_rate)."""
    with wave.open(wav_path, 'rb') as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sample_width != 2:
        raise ValueError(f'Expected 16-bit WAV, got {sample_width * 8}-bit')

    total_samples = n_frames * n_channels
    samples = struct.unpack(f'<{total_samples}h', raw)

    # If stereo, take first channel
    if n_channels > 1:
        samples = samples[::n_channels]

    return list(samples), sample_rate


def detect_silence_regions(
    wav_path: str,
    min_silence_ms: int = 200,
    energy_threshold: float = None,
    window_ms: int = 30,
) -> list:
    """Detect silence regions in a WAV file.

    Returns list of (start_seconds, end_seconds) tuples.
    Uses adaptive threshold (10th percentile of RMS * 1.5) if not specified.
    """
    samples, sample_rate = _read_wav_samples(wav_path)
    window_size = int(sample_rate * window_ms / 1000)
    min_silent_windows = max(1, int(min_silence_ms / window_ms))

    # Compute RMS per window
    rms_values = []
    for i in range(0, len(samples) - window_size, window_size):
        window = samples[i:i + window_size]
        rms = math.sqrt(sum(s * s for s in window) / len(window))
        rms_values.append(rms)

    if not rms_values:
        return []

    # Adaptive threshold
    if energy_threshold is None:
        sorted_rms = sorted(rms_values)
        p10 = sorted_rms[max(0, len(sorted_rms) // 10)]
        energy_threshold = p10 * 1.5
        # Floor: don't go below 100 RMS for very quiet recordings
        energy_threshold = max(energy_threshold, 100.0)

    # Find silence regions
    regions = []
    silent_start = None
    for idx, rms in enumerate(rms_values):
        if rms < energy_threshold:
            if silent_start is None:
                silent_start = idx
        else:
            if silent_start is not None:
                length = idx - silent_start
                if length >= min_silent_windows:
                    start_s = silent_start * window_ms / 1000
                    end_s = idx * window_ms / 1000
                    regions.append((start_s, end_s))
                silent_start = None

    # Handle trailing silence
    if silent_start is not None:
        length = len(rms_values) - silent_start
        if length >= min_silent_windows:
            start_s = silent_start * window_ms / 1000
            end_s = len(rms_values) * window_ms / 1000
            regions.append((start_s, end_s))

    return regions


SILENCE_PAD_S = 0.3  # 300ms silence padding for split segments


def _make_silence_frames(sample_rate: int, n_channels: int, sample_width: int, duration_s: float) -> bytes:
    """Generate silent audio frames."""
    n_frames = int(sample_rate * duration_s)
    return b'\x00' * (n_frames * n_channels * sample_width)


def split_wav(wav_path: str, split_point_s: float, out_before: str, out_after: str):
    """Split a WAV file at a time point into two files.

    Adds SILENCE_PAD_S of silence at the end of 'before' and start of 'after'
    to ensure MFA has leading/trailing silence for alignment.
    """
    with wave.open(wav_path, 'rb') as wf:
        params = wf.getparams()
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        split_frame = int(split_point_s * sample_rate)
        total_frames = wf.getnframes()

        wf.setpos(0)
        frames_before = wf.readframes(split_frame)
        frames_after = wf.readframes(total_frames - split_frame)

    silence = _make_silence_frames(sample_rate, n_channels, sample_width, SILENCE_PAD_S)

    # Before segment: audio + trailing silence
    with wave.open(out_before, 'wb') as wf_out:
        wf_out.setparams(params)
        wf_out.writeframes(frames_before + silence)

    # After segment: leading silence + audio
    with wave.open(out_after, 'wb') as wf_out:
        wf_out.setparams(params)
        wf_out.writeframes(silence + frames_after)


def split_wav_multi(wav_path: str, split_points_s: list, out_paths: list):
    """Split a WAV file at multiple time points into N+1 segments.

    Adds silence padding at segment boundaries for MFA.
    """
    with wave.open(wav_path, 'rb') as wf:
        params = wf.getparams()
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        total_frames = wf.getnframes()

        boundaries = [0] + [int(s * sample_rate) for s in split_points_s] + [total_frames]

        silence = _make_silence_frames(sample_rate, n_channels, sample_width, SILENCE_PAD_S)

        for i, out_path in enumerate(out_paths):
            start_frame = boundaries[i]
            end_frame = boundaries[i + 1]
            wf.setpos(start_frame)
            frames = wf.readframes(end_frame - start_frame)
            with wave.open(out_path, 'wb') as wf_out:
                wf_out.setparams(params)
                # Add padding: silence at start and end of each segment
                wf_out.writeframes(silence + frames + silence)


# ── Basmalah detection & splitting ─────────────────────────────

BASMALAH_VARIANTS = [
    'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ',
    'بِّسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ',   # shaddah variant (surah 97)
]

# Number of words in the basmalah
BASMALAH_WORD_COUNT = 4


def detect_basmalah_in_text(text: str, surah: int):
    """Check if text starts with basmalah and has content after it.

    Returns (has_basmalah, basmalah_text, content_text).
    Surah 1 ayah 1 IS the basmalah — returns (False, '', text).
    """
    if surah == 1:
        return False, '', text

    text_nfc = unicodedata.normalize('NFC', text.strip())
    for prefix in BASMALAH_VARIANTS:
        prefix_nfc = unicodedata.normalize('NFC', prefix)
        if text_nfc.startswith(prefix_nfc):
            remainder = text_nfc[len(prefix_nfc):].strip()
            if remainder:
                return True, prefix_nfc, remainder
    return False, '', text


def find_basmalah_split_point(wav_path: str) -> float:
    """Find the boundary between basmalah and content in audio.

    Two-pass approach:
    1. Smoothed RMS energy locates the approximate silence area
       (smoothing prevents noise spikes from misleading the search).
    2. Raw RMS energy in a ±500ms window around the smoothed minimum
       pinpoints the true silence center, avoiding the leading-edge
       bias that smoothing introduces.

    Fallback: 3.0s if analysis fails.
    """
    try:
        samples, sample_rate = _read_wav_samples(wav_path)
    except Exception:
        return 3.0

    duration = len(samples) / sample_rate
    window_ms = 30
    window_size = int(sample_rate * window_ms / 1000)

    # Compute RMS in 30ms windows
    rms_values = []
    for i in range(0, len(samples) - window_size, window_size):
        window = samples[i:i + window_size]
        rms = math.sqrt(sum(s * s for s in window) / len(window))
        rms_values.append(rms)

    if not rms_values:
        return 3.0

    # Pass 1: Smooth with a 300ms sliding average to find approximate area
    smooth_radius = 5
    smoothed = []
    for i in range(len(rms_values)):
        start_idx = max(0, i - smooth_radius)
        end_idx = min(len(rms_values), i + smooth_radius + 1)
        avg = sum(rms_values[start_idx:end_idx]) / (end_idx - start_idx)
        smoothed.append(avg)

    # Search window: 1.5s to min(6.0s, duration-1.0s)
    search_start = int(1.5 * 1000 / window_ms)
    search_end = int(min(6.0, duration - 1.0) * 1000 / window_ms)
    search_end = min(search_end, len(smoothed))

    if search_start >= search_end:
        return 3.0

    # Find smoothed minimum (approximate silence location)
    min_idx = search_start
    for i in range(search_start, search_end):
        if smoothed[i] < smoothed[min_idx]:
            min_idx = i

    # Pass 2: Refine with raw RMS in ±500ms window around smoothed minimum
    refine_radius = int(500 / window_ms)
    refine_start = max(0, min_idx - refine_radius)
    refine_end = min(len(rms_values), min_idx + refine_radius + 1)

    raw_min_idx = refine_start
    for i in range(refine_start, refine_end):
        if rms_values[i] < rms_values[raw_min_idx]:
            raw_min_idx = i

    split_time = raw_min_idx * window_ms / 1000
    return split_time


# ── Long audio segmentation ───────────────────────────────────

MAX_SEGMENT_DURATION = 10.0  # seconds


def find_split_points_for_long_audio(
    wav_path: str,
    max_duration_s: float = MAX_SEGMENT_DURATION,
) -> list:
    """Find split points for audio exceeding max_duration_s.

    Returns list of split point times (seconds), or empty if no split needed.
    """
    duration = get_wav_duration(wav_path)
    if duration <= max_duration_s:
        return []

    regions = detect_silence_regions(wav_path, min_silence_ms=150)

    # Build candidate split points (midpoints of silence regions)
    # Exclude leading/trailing silence (first 0.5s and last 0.5s)
    candidates = []
    for start, end in regions:
        mid = (start + end) / 2
        if 0.5 < mid < duration - 0.5:
            silence_len = end - start
            candidates.append((mid, silence_len))

    if not candidates:
        # Fallback: split at duration midpoint
        return [duration / 2]

    # Greedy: iteratively split the longest segment at its best silence
    split_points = []
    segments = [(0.0, duration)]

    while True:
        # Find the longest segment
        longest_idx = max(range(len(segments)), key=lambda i: segments[i][1] - segments[i][0])
        seg_start, seg_end = segments[longest_idx]
        seg_dur = seg_end - seg_start

        if seg_dur <= max_duration_s:
            break  # All segments are short enough

        # Find best candidate within this segment (prefer longest silence near midpoint)
        seg_mid = (seg_start + seg_end) / 2
        best = None
        best_score = -1
        for mid, sil_len in candidates:
            if seg_start + 1.0 < mid < seg_end - 1.0:
                # Score: prefer longer silences near the segment midpoint
                distance_penalty = abs(mid - seg_mid) / seg_dur
                score = sil_len * (1.0 - distance_penalty)
                if score > best_score:
                    best_score = score
                    best = mid

        if best is None:
            # No silence found — split at midpoint
            best = seg_mid

        split_points.append(best)
        # Replace the segment with two sub-segments
        segments[longest_idx:longest_idx + 1] = [
            (seg_start, best),
            (best, seg_end),
        ]

    return sorted(split_points)


def segment_long_audio(
    wav_path: str,
    lab_path: str,
    file_id: str,
    corpus_dir: str,
    max_duration_s: float = MAX_SEGMENT_DURATION,
) -> list:
    """Split a long audio file and its lab text into segments.

    Returns list of dicts: [{'file_id': ..., 'offset': ..., 'duration': ...}]
    or empty list if no splitting needed.
    Removes the original wav/lab files after splitting.
    """
    split_points = find_split_points_for_long_audio(wav_path, max_duration_s)
    if not split_points:
        return []

    duration = get_wav_duration(wav_path)

    # Read text and split proportionally
    with open(lab_path, 'r', encoding='utf-8') as f:
        words = f.read().strip().split()

    total_words = len(words)
    n_segments = len(split_points) + 1

    # Compute segment durations
    boundaries = [0.0] + split_points + [duration]
    seg_durations = [boundaries[i + 1] - boundaries[i] for i in range(n_segments)]
    total_dur = sum(seg_durations)

    # Assign words proportionally
    word_assignments = []
    word_idx = 0
    for i, seg_dur in enumerate(seg_durations):
        if i == n_segments - 1:
            # Last segment gets remaining words
            n_words = total_words - word_idx
        else:
            n_words = round((seg_dur / total_dur) * total_words)
            # Ensure at least 1 word per segment and don't overshoot
            n_words = max(1, min(n_words, total_words - word_idx - (n_segments - i - 1)))
        seg_words = words[word_idx:word_idx + n_words]
        word_assignments.append(seg_words)
        word_idx += n_words

    # Create segment files
    seg_wav_paths = [
        os.path.join(corpus_dir, f'{file_id}_seg{i + 1:03d}.wav')
        for i in range(n_segments)
    ]
    split_wav_multi(wav_path, split_points, seg_wav_paths)

    segments = []
    for i in range(n_segments):
        seg_file_id = f'{file_id}_seg{i + 1:03d}'
        seg_lab = os.path.join(corpus_dir, f'{seg_file_id}.lab')
        with open(seg_lab, 'w', encoding='utf-8') as f:
            f.write(' '.join(word_assignments[i]))
        segments.append({
            'file_id': seg_file_id,
            'offset': boundaries[i],
            'duration': seg_durations[i],
            'padding': SILENCE_PAD_S,  # padding added at start of each segment
        })

    # Remove original files
    os.remove(wav_path)
    os.remove(lab_path)

    return segments


# ── Configuration ──────────────────────────────────────────────

AUDIO_ROOT = os.path.expanduser('~/Desktop/quran_vc_dataset/reciter_2')
VALIDATION_DIR = os.path.join(PROJECT_ROOT, 'phase2_alignment', 'validation')
QURAN_JSON = os.path.join(PROJECT_ROOT, 'data', 'quran_text', 'quran_hafs.json')

TEST_CASES = [
    {'surah': 1,   'ayahs': range(1, 8),  'name': 'Al-Faatiha'},
    {'surah': 93,  'ayahs': range(1, 12), 'name': 'Ad-Dhuhaa'},
    {'surah': 97,  'ayahs': range(1, 6),  'name': 'Al-Qadr'},
    {'surah': 113, 'ayahs': range(1, 6),  'name': 'Al-Falaq'},
    {'surah': 114, 'ayahs': range(1, 7),  'name': 'An-Naas'},
    {'surah': 67,  'ayahs': range(1, 6),  'name': 'Al-Mulk (1-5)'},
    {'surah': 56,  'ayahs': range(1, 6),  'name': 'Al-Waaqia (1-5)'},
    {'surah': 36,  'ayahs': range(1, 84), 'name': 'Ya-Sin'},
]

# ── Data classes for validation results ──────────────────────

@dataclass
class PhoneDurationIssue:
    file_id: str
    word: str
    phone_ipa: str
    phone_mfa: str
    duration_ms: float
    issue: str  # "too_short" or "too_long"

@dataclass
class PhoneCountMismatch:
    file_id: str
    word: str
    expected: int
    actual: int

@dataclass
class SurahValidationResult:
    surah: int
    name: str
    ayah_range: str
    num_ayahs: int
    total_words: int
    total_phones: int
    oov_count: int
    failed_alignments: int
    failed_ayahs: list
    phone_duration_issues: list
    phone_count_mismatches: list
    phones_with_tajweed: int
    total_audio_duration: float
    total_aligned_span: float
    alignment_coverage_pct: float
    mfa_time_seconds: float
    errors: list
    verses: list  # list of AlignedVerse


# ── Helper functions ─────────────────────────────────────────

def load_quran_text():
    """Load and index Quran text."""
    with open(QURAN_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    lookup = {}
    for s in data['surahs']:
        for a in s['ayahs']:
            lookup[(s['number'], a['number'])] = a['text']
    return lookup


def _clean_text(text: str) -> str:
    """NFC-normalize and strip kashida + waqf signs."""
    text = unicodedata.normalize('NFC', text)
    text = text.replace('\u0640', '')
    text = ''.join(c for c in text if c not in QURANIC_WAQF_SIGNS)
    return text


def setup_corpus(surah: int, ayahs, corpus_dir: str, quran_lookup: dict,
                 pipeline: SymbolicLayerPipeline = None):
    """Create corpus directory with WAVs and .lab files.

    Handles basmalah separation and long audio segmentation.
    When *pipeline* is provided, lab text is derived from Phase 1
    word_texts so that words in lab files are guaranteed to match
    the dictionary entries (avoids hamza-seat / kashida OOV mismatches).
    Returns (missing_audio, missing_text, split_info, segment_info).
    """
    os.makedirs(corpus_dir, exist_ok=True)

    # Clean existing files
    for f in os.listdir(corpus_dir):
        os.remove(os.path.join(corpus_dir, f))

    audio_dir = os.path.join(AUDIO_ROOT, f'surah_{surah}_wav16k')
    missing_audio = []
    missing_text = []
    split_info = {}    # file_id -> basmalah split metadata
    segment_info = {}  # file_id -> segment metadata

    for ayah in ayahs:
        file_id = f'{surah:03d}_{ayah:03d}'

        # Check audio exists
        wav_src = os.path.join(audio_dir, f'{file_id}.wav')
        if not os.path.exists(wav_src):
            missing_audio.append(file_id)
            continue

        # Check text exists
        key = (surah, ayah)
        if key not in quran_lookup:
            missing_text.append(file_id)
            continue

        # Get lab text from Phase 1 word_texts when available.
        # This ensures the .lab words exactly match dictionary entries,
        # avoiding mismatches caused by kashida/hamza-seat normalization.
        text = None
        if pipeline is not None:
            try:
                output = pipeline.process_verse(surah=surah, ayah=ayah)
                text = ' '.join(output.phoneme_sequence.word_texts)
            except Exception:
                pass  # fall back to _clean_text below
        if text is None:
            text = _clean_text(quran_lookup[key])

        # ── Basmalah handling for ayah 1 ──
        if ayah == 1:
            has_basmalah, basmalah_text, content_text = detect_basmalah_in_text(text, surah)
            if has_basmalah:
                # Split audio at silence between basmalah and content
                split_point = find_basmalah_split_point(wav_src)
                basmalah_file_id = f'{surah:03d}_000'
                content_file_id = file_id  # keeps 001

                # Split audio (copy, not symlink, since we need real files)
                basmalah_wav = os.path.join(corpus_dir, f'{basmalah_file_id}.wav')
                content_wav = os.path.join(corpus_dir, f'{content_file_id}.wav')
                split_wav(wav_src, split_point, basmalah_wav, content_wav)

                # Write separate lab files
                basmalah_lab = os.path.join(corpus_dir, f'{basmalah_file_id}.lab')
                with open(basmalah_lab, 'w', encoding='utf-8') as f:
                    f.write(basmalah_text)

                content_lab = os.path.join(corpus_dir, f'{content_file_id}.lab')
                with open(content_lab, 'w', encoding='utf-8') as f:
                    f.write(content_text)

                split_info[file_id] = {
                    'basmalah_file_id': basmalah_file_id,
                    'content_file_id': content_file_id,
                    'basmalah_text': basmalah_text,
                    'content_text': content_text,
                    'split_point': split_point,
                }
                print(f'    Basmalah split: {file_id} → {basmalah_file_id} + {content_file_id} '
                      f'(at {split_point:.2f}s)')
                continue  # Skip normal symlink + lab creation

        # Normal: symlink WAV and write lab
        wav_dst = os.path.join(corpus_dir, f'{file_id}.wav')
        os.symlink(wav_src, wav_dst)
        lab_path = os.path.join(corpus_dir, f'{file_id}.lab')
        with open(lab_path, 'w', encoding='utf-8') as f:
            f.write(text)

    # ── Long audio segmentation pass ──
    # Scan all wav/lab files in corpus and segment any > MAX_SEGMENT_DURATION
    corpus_files = sorted(f[:-4] for f in os.listdir(corpus_dir) if f.endswith('.wav'))
    for fid in corpus_files:
        wav_path = os.path.join(corpus_dir, f'{fid}.wav')
        lab_path = os.path.join(corpus_dir, f'{fid}.lab')
        if not os.path.exists(lab_path):
            continue

        duration = get_wav_duration(wav_path)
        if duration > MAX_SEGMENT_DURATION:
            # Need to resolve symlinks for splitting
            real_wav = os.path.realpath(wav_path)
            if os.path.islink(wav_path):
                # Replace symlink with a copy so we can split it
                os.remove(wav_path)
                shutil.copy2(real_wav, wav_path)

            segs = segment_long_audio(wav_path, lab_path, fid, corpus_dir, MAX_SEGMENT_DURATION)
            if segs:
                segment_info[fid] = {
                    'segments': segs,
                    'original_duration': duration,
                }
                print(f'    Segmented: {fid} ({duration:.1f}s) → '
                      f'{len(segs)} segments')

    return missing_audio, missing_text, split_info, segment_info


def generate_dictionary(pipeline: SymbolicLayerPipeline, surah: int, ayahs, dict_path: str):
    """Generate MFA-compatible dictionary for given ayahs.

    Supports multiple pronunciations per word (e.g. hamzat al-wasl
    pronounced verse-initially but elided mid-verse). MFA picks the
    best-matching variant during alignment.
    """
    os.makedirs(os.path.dirname(dict_path), exist_ok=True)
    # word -> set of pronunciation strings (allows multiple variants)
    all_entries: dict[str, set[str]] = {}
    errors = []

    for ayah in ayahs:
        # Retry up to 2 times for intermittent Phase 1 failures
        last_err = None
        for attempt in range(2):
            try:
                output = pipeline.process_verse(surah=surah, ayah=ayah)
                for line in output.to_mfa_dict().strip().split('\n'):
                    if '\t' in line:
                        word, phonemes = line.split('\t', 1)
                        word = unicodedata.normalize('NFC', word.strip())
                        phonemes = phonemes.strip()
                        if word and phonemes:
                            converted = ' '.join(
                                IPA_TO_MFA.get(p, p) for p in phonemes.split()
                            )
                            if word not in all_entries:
                                all_entries[word] = set()
                            all_entries[word].add(converted)
                last_err = None
                break
            except Exception as e:
                last_err = (ayah, str(e))
        if last_err:
            errors.append(last_err)

    # Write dictionary — multiple pronunciations per word on separate lines
    with open(dict_path, 'w', encoding='utf-8') as f:
        for word in sorted(all_entries.keys()):
            for phonemes in sorted(all_entries[word]):
                f.write(f'{word}\t{phonemes}\n')

    return all_entries, errors


def check_oovs(corpus_dir: str, dict_words: set) -> list:
    """Find words in .lab files not in dictionary."""
    oovs = []
    for fname in sorted(os.listdir(corpus_dir)):
        if fname.endswith('.lab'):
            with open(os.path.join(corpus_dir, fname), 'r', encoding='utf-8') as f:
                for word in f.read().strip().split():
                    if word not in dict_words:
                        oovs.append((fname, word))
    return oovs


def run_mfa(corpus_dir: str, dict_path: str, output_dir: str):
    """Run MFA alignment, return (success, stderr, elapsed_seconds)."""
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        'mfa', 'align',
        corpus_dir, dict_path, 'arabic', output_dir,
        '--clean'
    ]
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    elapsed = time.time() - start
    success = result.returncode == 0
    return success, result.stderr, elapsed


def validate_surah(
    test_case: dict,
    pipeline: SymbolicLayerPipeline,
    align_pipeline: AlignmentPipeline,
    quran_lookup: dict,
) -> SurahValidationResult:
    """Run full validation for one surah test case."""
    surah = test_case['surah']
    ayahs = list(test_case['ayahs'])
    name = test_case['name']
    num_ayahs = len(ayahs)

    print(f'\n{"="*70}')
    print(f'  Surah {surah} — {name} ({num_ayahs} ayahs)')
    print(f'{"="*70}')

    # Directories
    base_dir = os.path.join(VALIDATION_DIR, f'surah_{surah}')
    corpus_dir = os.path.join(base_dir, 'corpus')
    dict_path = os.path.join(base_dir, 'dictionary.dict')
    output_dir = os.path.join(base_dir, 'output')
    errors = []

    # Step 1: Setup corpus (with basmalah splitting + long audio segmentation)
    print(f'  [1/5] Setting up corpus...')
    missing_audio, missing_text, split_info, segment_info = setup_corpus(
        surah, ayahs, corpus_dir, quran_lookup, pipeline=pipeline
    )
    if missing_audio:
        errors.append(f'Missing audio: {missing_audio}')
        print(f'    WARNING: Missing audio files: {missing_audio}')
    if missing_text:
        errors.append(f'Missing text: {missing_text}')
        print(f'    WARNING: Missing text entries: {missing_text}')
    if split_info:
        print(f'    Basmalah splits: {len(split_info)}')
    if segment_info:
        print(f'    Segmented files: {len(segment_info)}')

    # Step 2: Generate dictionary
    print(f'  [2/5] Generating dictionary...')
    dict_entries, dict_errors = generate_dictionary(pipeline, surah, ayahs, dict_path)
    if dict_errors:
        errors.append(f'Dictionary errors: {dict_errors}')
        print(f'    WARNING: Dict generation errors: {dict_errors}')
    print(f'    {len(dict_entries)} dictionary entries')

    # Step 3: Check OOVs (dict_entries keys are the unique words)
    oovs = check_oovs(corpus_dir, set(dict_entries.keys()))
    oov_count = len(oovs)
    if oovs:
        errors.append(f'OOV words: {oovs}')
        print(f'    FAIL: {oov_count} OOV words found: {oovs[:5]}...')
    else:
        print(f'    OOV check: PASS (0 OOVs)')

    # Step 4: Run MFA alignment
    print(f'  [3/5] Running MFA alignment...')
    mfa_success, mfa_stderr, mfa_time = run_mfa(corpus_dir, dict_path, output_dir)
    if not mfa_success:
        errors.append(f'MFA failed: {mfa_stderr[-500:]}')
        print(f'    FAIL: MFA alignment failed')
        return SurahValidationResult(
            surah=surah, name=name, ayah_range=f'{ayahs[0]}-{ayahs[-1]}',
            num_ayahs=num_ayahs, total_words=0, total_phones=0,
            oov_count=oov_count, failed_alignments=num_ayahs,
            failed_ayahs=list(ayahs),
            phone_duration_issues=[], phone_count_mismatches=[],
            phones_with_tajweed=0, total_audio_duration=0,
            total_aligned_span=0, alignment_coverage_pct=0,
            mfa_time_seconds=mfa_time, errors=errors, verses=[],
        )

    # Check for phone mismatch warnings in MFA stderr
    if 'pronunciations in the dictionary that were ignored' in mfa_stderr:
        import re
        match = re.search(r'(\d+) pronunciations.*ignored.*containing.*?(\d+) phones', mfa_stderr)
        if match:
            errors.append(f'MFA ignored {match.group(1)} pronunciations ({match.group(2)} unknown phones)')
            print(f'    WARNING: MFA ignored {match.group(1)} pronunciations')

    print(f'    MFA complete in {mfa_time:.1f}s')

    # Step 5: Count generated TextGrids and check for failures
    tg_files = set(f for f in os.listdir(output_dir) if f.endswith('.TextGrid'))

    # Build expected TextGrid list accounting for splits and segments
    expected_tg_ids = set()
    for ayah in ayahs:
        file_id = f'{surah:03d}_{ayah:03d}'
        if file_id in split_info:
            si = split_info[file_id]
            expected_tg_ids.add(si['basmalah_file_id'])
            cid = si['content_file_id']
            if cid in segment_info:
                for seg in segment_info[cid]['segments']:
                    expected_tg_ids.add(seg['file_id'])
            else:
                expected_tg_ids.add(cid)
        elif file_id in segment_info:
            for seg in segment_info[file_id]['segments']:
                expected_tg_ids.add(seg['file_id'])
        else:
            expected_tg_ids.add(file_id)

    missing_tg = [fid for fid in expected_tg_ids if f'{fid}.TextGrid' not in tg_files]
    # Map back to ayahs for failure reporting
    failed_ayahs = []
    for ayah in ayahs:
        file_id = f'{surah:03d}_{ayah:03d}'
        ayah_tg_ids = set()
        if file_id in split_info:
            si = split_info[file_id]
            ayah_tg_ids.add(si['basmalah_file_id'])
            cid = si['content_file_id']
            if cid in segment_info:
                for seg in segment_info[cid]['segments']:
                    ayah_tg_ids.add(seg['file_id'])
            else:
                ayah_tg_ids.add(cid)
        elif file_id in segment_info:
            for seg in segment_info[file_id]['segments']:
                ayah_tg_ids.add(seg['file_id'])
        else:
            ayah_tg_ids.add(file_id)
        if any(f'{fid}.TextGrid' not in tg_files for fid in ayah_tg_ids):
            failed_ayahs.append(ayah)

    failed_count = len(failed_ayahs)
    if failed_ayahs:
        errors.append(f'Failed alignments for ayahs: {failed_ayahs}')
        print(f'    FAIL: {failed_count} ayahs failed alignment: {failed_ayahs}')
    else:
        print(f'    TextGrids: {len(tg_files)}/{len(expected_tg_ids)} generated')

    # Step 6: Parse TextGrids and merge with Phase 1
    print(f'  [4/5] Parsing & merging with Phase 1...')
    verses = []
    merge_errors = []
    for ayah in ayahs:
        if ayah in failed_ayahs:
            continue
        file_id = f'{surah:03d}_{ayah:03d}'
        try:
            if file_id in split_info:
                # ── Basmalah-split ayah ──
                si = split_info[file_id]

                # Process basmalah as ayah 0
                basmalah_verse = align_pipeline.process_verse_from_text(
                    text=si['basmalah_text'],
                    surah=surah, ayah=0,
                    output_dir=output_dir,
                    file_id=si['basmalah_file_id'],
                )
                verses.append(basmalah_verse)

                # Process content (may also be segmented)
                cid = si['content_file_id']
                if cid in segment_info:
                    seg_data = segment_info[cid]
                    content_verse = align_pipeline.process_verse_segments_from_text(
                        text=si['content_text'],
                        surah=surah, ayah=ayah,
                        segment_infos=seg_data['segments'],
                        output_dir=output_dir,
                        original_duration=seg_data['original_duration'],
                    )
                else:
                    content_verse = align_pipeline.process_verse_from_text(
                        text=si['content_text'],
                        surah=surah, ayah=ayah,
                        output_dir=output_dir,
                        file_id=cid,
                    )
                verses.append(content_verse)

            elif file_id in segment_info:
                # ── Segmented (no basmalah split) ──
                seg_data = segment_info[file_id]
                verse = align_pipeline.process_verse_segments(
                    surah=surah, ayah=ayah,
                    segment_infos=seg_data['segments'],
                    output_dir=output_dir,
                    original_duration=seg_data['original_duration'],
                )
                verses.append(verse)

            else:
                # ── Normal ayah ──
                verse = align_pipeline.process_verse(
                    surah=surah, ayah=ayah, output_dir=output_dir
                )
                verses.append(verse)

        except Exception as e:
            merge_errors.append((ayah, str(e)))
            errors.append(f'Merge error ayah {ayah}: {e}')

    if merge_errors:
        print(f'    WARNING: {len(merge_errors)} merge errors: {merge_errors}')

    # Step 7: Validate
    print(f'  [5/5] Validating...')
    total_words = sum(len(v.words) for v in verses)
    total_phones = sum(sum(len(w.phones) for w in v.words) for v in verses)

    # Phone duration check
    duration_issues = []
    for v in verses:
        for w in v.words:
            for p in w.phones:
                if p.duration_ms < 10:
                    duration_issues.append(PhoneDurationIssue(
                        v.file_id, w.text, p.ipa, p.mfa, p.duration_ms, 'too_short'))
                elif p.duration_ms > 5000:
                    duration_issues.append(PhoneDurationIssue(
                        v.file_id, w.text, p.ipa, p.mfa, p.duration_ms, 'too_long'))

    # Phone count match: compare Phase 1 per-ayah output with TextGrid
    count_mismatches = []
    for v in verses:
        try:
            if v.ayah == 0:
                # Basmalah — use process_text
                p1_output = pipeline.process_text(v.text, surah=surah, ayah=0)
            else:
                # Check if this was a split content verse
                orig_file_id = f'{surah:03d}_{v.ayah:03d}'
                if orig_file_id in split_info:
                    p1_output = pipeline.process_text(
                        split_info[orig_file_id]['content_text'],
                        surah=surah, ayah=v.ayah
                    )
                else:
                    p1_output = pipeline.process_verse(surah=surah, ayah=v.ayah)
            ps = p1_output.phoneme_sequence
            wb = list(ps.word_boundaries)
            starts = [0] + wb
            ends = wb + [len(ps.phonemes)]
            p1_word_counts = {
                unicodedata.normalize('NFC', wt): (e - s)
                for wt, s, e in zip(ps.word_texts, starts, ends)
            }
            for w in v.words:
                w_nfc = unicodedata.normalize('NFC', w.text)
                expected = p1_word_counts.get(w_nfc, -1)
                actual = len(w.phones)
                if expected != actual:
                    count_mismatches.append(PhoneCountMismatch(
                        v.file_id, w.text, expected, actual))
        except Exception:
            pass  # Phase 1 error — already tracked

    # Tajweed coverage
    phones_with_tajweed = 0
    for v in verses:
        for w in v.words:
            for p in w.phones:
                if p.tajweed_rules:
                    phones_with_tajweed += 1

    # Audio duration vs alignment span
    total_audio_duration = sum(v.duration for v in verses)
    total_aligned_span = 0
    for v in verses:
        if v.words:
            span = v.words[-1].end - v.words[0].start
            total_aligned_span += span
    coverage_pct = (total_aligned_span / total_audio_duration * 100) if total_audio_duration > 0 else 0

    # Print summary
    print(f'    Words: {total_words} | Phones: {total_phones}')
    print(f'    Duration issues: {len(duration_issues)}')
    print(f'    Phone count mismatches: {len(count_mismatches)}')
    print(f'    Tajweed coverage: {phones_with_tajweed}/{total_phones} '
          f'({phones_with_tajweed/total_phones*100:.1f}%)' if total_phones > 0 else '')
    print(f'    Audio: {total_audio_duration:.1f}s | Aligned span: {total_aligned_span:.1f}s '
          f'| Coverage: {coverage_pct:.1f}%')

    # Export JSON
    if verses:
        json_path = os.path.join(base_dir, f'surah_{surah}_aligned.json')
        export_surah_json(verses, json_path)

    return SurahValidationResult(
        surah=surah, name=name, ayah_range=f'{ayahs[0]}-{ayahs[-1]}',
        num_ayahs=num_ayahs, total_words=total_words, total_phones=total_phones,
        oov_count=oov_count, failed_alignments=failed_count,
        failed_ayahs=failed_ayahs,
        phone_duration_issues=duration_issues,
        phone_count_mismatches=count_mismatches,
        phones_with_tajweed=phones_with_tajweed,
        total_audio_duration=total_audio_duration,
        total_aligned_span=total_aligned_span,
        alignment_coverage_pct=coverage_pct,
        mfa_time_seconds=mfa_time,
        errors=errors, verses=verses,
    )


def generate_report(results: list[SurahValidationResult], report_path: str):
    """Generate markdown validation report."""
    total_ayahs = sum(r.num_ayahs for r in results)
    total_words = sum(r.total_words for r in results)
    total_phones = sum(r.total_phones for r in results)
    total_oov = sum(r.oov_count for r in results)
    total_failed = sum(r.failed_alignments for r in results)
    total_duration_issues = sum(len(r.phone_duration_issues) for r in results)
    total_count_mismatches = sum(len(r.phone_count_mismatches) for r in results)
    total_tajweed = sum(r.phones_with_tajweed for r in results)
    total_audio = sum(r.total_audio_duration for r in results)
    total_aligned = sum(r.total_aligned_span for r in results)
    total_mfa_time = sum(r.mfa_time_seconds for r in results)
    all_errors = []
    for r in results:
        for e in r.errors:
            all_errors.append(f'Surah {r.surah}: {e}')

    # Determine overall pass/fail
    critical_failures = total_oov + total_failed + total_count_mismatches
    overall_status = 'PASS' if critical_failures == 0 else 'FAIL'

    lines = []
    lines.append('# Phase 2 Alignment — Validation Report\n')
    lines.append(f'**Status: {overall_status}**\n')
    lines.append(f'Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')

    # Overall summary table
    lines.append('## Overall Summary\n')
    lines.append('| Metric | Value |')
    lines.append('|--------|-------|')
    lines.append(f'| Test surahs | {len(results)} |')
    lines.append(f'| Total ayahs | {total_ayahs} |')
    lines.append(f'| Total words aligned | {total_words} |')
    lines.append(f'| Total phones aligned | {total_phones} |')
    lines.append(f'| OOV words | {total_oov} |')
    lines.append(f'| Failed alignments | {total_failed} |')
    lines.append(f'| Phone count mismatches | {total_count_mismatches} |')
    lines.append(f'| Phone duration issues | {total_duration_issues} |')
    lines.append(f'| Phones with tajweed rules | {total_tajweed}/{total_phones} ({total_tajweed/total_phones*100:.1f}%) |' if total_phones > 0 else '| Phones with tajweed rules | 0 |')
    lines.append(f'| Total audio duration | {total_audio:.1f}s |')
    lines.append(f'| Total aligned span | {total_aligned:.1f}s |')
    lines.append(f'| Alignment coverage | {total_aligned/total_audio*100:.1f}% |' if total_audio > 0 else '| Alignment coverage | N/A |')
    lines.append(f'| Total MFA time | {total_mfa_time:.1f}s |')
    lines.append('')

    # Per-surah results
    lines.append('## Per-Surah Results\n')
    lines.append('| Surah | Name | Ayahs | Words | Phones | OOV | Failed | Duration Issues | Phone Mismatches | Tajweed % | Coverage % | MFA Time |')
    lines.append('|-------|------|-------|-------|--------|-----|--------|-----------------|------------------|-----------|------------|----------|')
    for r in results:
        tj_pct = f'{r.phones_with_tajweed/r.total_phones*100:.1f}' if r.total_phones > 0 else 'N/A'
        lines.append(
            f'| {r.surah} | {r.name} | {r.ayah_range} | {r.total_words} | {r.total_phones} '
            f'| {r.oov_count} | {r.failed_alignments} | {len(r.phone_duration_issues)} '
            f'| {len(r.phone_count_mismatches)} | {tj_pct}% | {r.alignment_coverage_pct:.1f}% '
            f'| {r.mfa_time_seconds:.1f}s |'
        )
    lines.append('')

    # Critical checks
    lines.append('## Critical Checks\n')

    lines.append('### 1. OOV Words (must be 0)\n')
    if total_oov == 0:
        lines.append('PASS: No OOV words found across all test surahs.\n')
    else:
        lines.append(f'**FAIL: {total_oov} OOV words found.**\n')
        for r in results:
            if r.oov_count > 0:
                lines.append(f'- Surah {r.surah}: {r.oov_count} OOVs')
        lines.append('')

    lines.append('### 2. Failed Alignments (must be 0)\n')
    if total_failed == 0:
        lines.append('PASS: All ayahs aligned successfully.\n')
    else:
        lines.append(f'**FAIL: {total_failed} ayahs failed alignment.**\n')
        for r in results:
            if r.failed_alignments > 0:
                lines.append(f'- Surah {r.surah}: ayahs {r.failed_ayahs}')
        lines.append('')

    lines.append('### 3. Phone Count Consistency\n')
    if total_count_mismatches == 0:
        lines.append('PASS: All word phone counts match dictionary entries.\n')
    else:
        lines.append(f'**FAIL: {total_count_mismatches} mismatches.**\n')
        for r in results:
            for m in r.phone_count_mismatches:
                lines.append(f'- {m.file_id}: "{m.word}" expected={m.expected} actual={m.actual}')
        lines.append('')

    # Duration analysis
    lines.append('### 4. Phone Duration Sanity\n')
    if total_duration_issues == 0:
        lines.append('PASS: No phones outside expected duration range.\n')
    else:
        lines.append(f'**{total_duration_issues} issues found:**\n')

    # Collect all short/long phones across all results
    short_phones = []
    long_phones = []
    for r in results:
        for d in r.phone_duration_issues:
            if d.issue == 'too_short':
                short_phones.append(d)
            else:
                long_phones.append(d)

    if short_phones:
        lines.append(f'#### Phones < 10ms ({len(short_phones)})\n')
        lines.append('| File | Word | Phone (IPA) | Phone (MFA) | Duration |')
        lines.append('|------|------|-------------|-------------|----------|')
        for d in short_phones[:20]:
            lines.append(f'| {d.file_id} | {d.word} | {d.phone_ipa} | {d.phone_mfa} | {d.duration_ms:.1f}ms |')
        if len(short_phones) > 20:
            lines.append(f'\n*...and {len(short_phones)-20} more*\n')
        lines.append('')

    if long_phones:
        lines.append(f'#### Phones > 5000ms ({len(long_phones)})\n')
        lines.append('| File | Word | Phone (IPA) | Phone (MFA) | Duration |')
        lines.append('|------|------|-------------|-------------|----------|')
        for d in long_phones[:20]:
            lines.append(f'| {d.file_id} | {d.word} | {d.phone_ipa} | {d.phone_mfa} | {d.duration_ms:.1f}ms |')
        lines.append('')

    # Tajweed coverage detail
    lines.append('### 5. Tajweed Rule Coverage\n')
    lines.append(f'Phones with at least one tajweed annotation: '
                 f'{total_tajweed}/{total_phones} ({total_tajweed/total_phones*100:.1f}%)\n' if total_phones > 0 else '')

    # Collect all unique rules across all verses
    rule_counts = {}
    for r in results:
        for v in r.verses:
            for w in v.words:
                for p in w.phones:
                    for rule in p.tajweed_rules:
                        rule_counts[rule] = rule_counts.get(rule, 0) + 1

    if rule_counts:
        lines.append('| Rule | Occurrences |')
        lines.append('|------|-------------|')
        for rule, count in sorted(rule_counts.items(), key=lambda x: -x[1]):
            lines.append(f'| {rule} | {count} |')
        lines.append('')

    # Alignment coverage detail
    lines.append('### 6. Audio Coverage\n')
    lines.append('Ratio of aligned speech span to total audio duration '
                 '(lower values indicate more silence/padding).\n')
    lines.append('| Surah | Audio Duration | Aligned Span | Coverage |')
    lines.append('|-------|---------------|--------------|----------|')
    for r in results:
        lines.append(f'| {r.surah} ({r.name}) | {r.total_audio_duration:.1f}s '
                     f'| {r.total_aligned_span:.1f}s | {r.alignment_coverage_pct:.1f}% |')
    lines.append('')

    # Errors & warnings
    if all_errors:
        lines.append('## Errors & Warnings\n')
        for e in all_errors:
            lines.append(f'- {e}')
        lines.append('')

    # IPA-MFA phone mapping reference
    lines.append('## Appendix: IPA ↔ MFA Phone Mapping\n')
    lines.append('| IPA | MFA | Arabic Letter |')
    lines.append('|-----|-----|---------------|')
    ipa_arabic = {
        'ʔ': 'ء (hamza)', 'ħ': 'ح', 'ʕ': 'ع', 'ɣ': 'غ', 'ð': 'ذ',
        'sˤ': 'ص', 'dˤ': 'ض', 'tˤ': 'ط',
        'aː': 'long a (ا)', 'iː': 'long i (ي)', 'uː': 'long u (و)',
    }
    for ipa, mfa in sorted(IPA_TO_MFA.items()):
        arabic = ipa_arabic.get(ipa, '')
        lines.append(f'| {ipa} | {mfa} | {arabic} |')
    lines.append('')

    # Write report
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'\nReport written to {report_path}')


# ── Main ─────────────────────────────────────────────────────

def main():
    print('Phase 2 Alignment — Full Validation')
    print(f'Test cases: {len(TEST_CASES)} surahs, '
          f'{sum(len(list(tc["ayahs"])) for tc in TEST_CASES)} total ayahs\n')

    # Load shared resources
    quran_lookup = load_quran_text()
    pipeline = SymbolicLayerPipeline()
    align_pipeline = AlignmentPipeline(project_root=PROJECT_ROOT)

    results = []
    for tc in TEST_CASES:
        result = validate_surah(tc, pipeline, align_pipeline, quran_lookup)
        results.append(result)

    # Generate report
    report_path = os.path.join(VALIDATION_DIR, 'phase2_validation_report.md')
    generate_report(results, report_path)

    # Final summary
    print(f'\n{"="*70}')
    print(f'  VALIDATION COMPLETE')
    print(f'{"="*70}')
    total_ayahs = sum(r.num_ayahs for r in results)
    total_failed = sum(r.failed_alignments for r in results)
    total_oov = sum(r.oov_count for r in results)
    print(f'  Ayahs: {total_ayahs - total_failed}/{total_ayahs} aligned')
    print(f'  OOV: {total_oov}')
    print(f'  Status: {"PASS" if total_oov + total_failed == 0 else "FAIL"}')


if __name__ == '__main__':
    main()
