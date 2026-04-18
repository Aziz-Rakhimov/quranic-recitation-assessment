"""
Word verification layer for Quranic recitation assessment.

Runs faster-whisper on an ayah audio segment, compares the transcription
against the expected Quranic text, and reports word-level errors
(missing, wrong, added) using sequence alignment.
"""

import json
import difflib
import os
from pathlib import Path
from typing import List, Set

from faster_whisper import WhisperModel

from phase2_alignment.models import WordError, VerifiedAyah
from phase2_alignment.text_normalization import normalize


# -------------------------------------------------------------------
# Whisper model singleton
# -------------------------------------------------------------------

_whisper_model = None

# Similarity threshold: if a "wrong" pair is at least this similar,
# treat it as correct (Whisper transcription noise).
_SIMILARITY_THRESHOLD = 0.75


def get_whisper_model() -> WhisperModel:
    """Load the faster-whisper model once and reuse across calls."""
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel("small", device="cpu", compute_type="float32")
    return _whisper_model


# -------------------------------------------------------------------
# Core transcription helper
# -------------------------------------------------------------------

def _transcribe(audio_path: str) -> str:
    """Run faster-whisper on *audio_path* and return the full transcribed text."""
    model = get_whisper_model()
    segments, _info = model.transcribe(audio_path, language="ar", word_timestamps=False)
    # segments is a generator — consume it to get the text
    return " ".join(seg.text.strip() for seg in segments)


# -------------------------------------------------------------------
# Main verification function
# -------------------------------------------------------------------

def verify_ayah(
    audio_path: str,
    surah: int,
    ayah: int,
    expected_words: List[str],
) -> VerifiedAyah:
    """Compare Whisper transcription of *audio_path* against *expected_words*.

    Returns a ``VerifiedAyah`` that lists word errors and marks which word
    indices should be skipped during tajwid assessment.
    """

    # 1. Transcribe
    raw_transcript = _transcribe(audio_path)

    # 2. Split into words (Whisper may insert extra whitespace)
    transcribed_words_raw = raw_transcript.split()

    # 3. Normalize both sides
    expected_norm = [normalize(w) for w in expected_words]
    transcribed_norm = [normalize(w) for w in transcribed_words_raw]

    # Keep the original (un-normalized) forms for reporting
    expected_orig = list(expected_words)
    transcribed_orig = list(transcribed_words_raw)

    # 4. Sequence-align normalized word lists
    matcher = difflib.SequenceMatcher(None, expected_norm, transcribed_norm)
    opcodes = matcher.get_opcodes()

    # 5-8. Walk opcodes and build result
    word_errors: List[WordError] = []
    verified: Set[int] = set()
    skipped: Set[int] = set()

    for tag, i1, i2, j1, j2 in opcodes:

        if tag == "equal":
            # Words match — mark every expected index as verified
            for idx in range(i1, i2):
                verified.add(idx)

        elif tag == "replace":
            # One-to-one (or many-to-many) substitution
            exp_slice = list(range(i1, i2))
            det_slice = list(range(j1, j2))

            # Pair up as far as possible; excess on either side becomes
            # missing or added.
            pairs = min(len(exp_slice), len(det_slice))
            for k in range(pairs):
                ei = exp_slice[k]
                di = det_slice[k]
                # Apply similarity threshold
                sim = difflib.SequenceMatcher(
                    None, expected_norm[ei], transcribed_norm[di],
                ).ratio()
                if sim >= _SIMILARITY_THRESHOLD:
                    verified.add(ei)
                else:
                    skipped.add(ei)
                    word_errors.append(WordError(
                        error_type="wrong",
                        expected_word=expected_orig[ei],
                        detected_word=transcribed_orig[di],
                        word_position=ei,
                        ayah=ayah,
                    ))

            # Leftover expected words → missing
            for k in range(pairs, len(exp_slice)):
                ei = exp_slice[k]
                skipped.add(ei)
                word_errors.append(WordError(
                    error_type="missing",
                    expected_word=expected_orig[ei],
                    detected_word=None,
                    word_position=ei,
                    ayah=ayah,
                ))

            # Leftover transcribed words → added
            for k in range(pairs, len(det_slice)):
                word_errors.append(WordError(
                    error_type="added",
                    expected_word=None,
                    detected_word=transcribed_orig[det_slice[k]],
                    word_position=None,
                    ayah=ayah,
                ))

        elif tag == "delete":
            # In expected but not in transcription → missing
            for idx in range(i1, i2):
                skipped.add(idx)
                word_errors.append(WordError(
                    error_type="missing",
                    expected_word=expected_orig[idx],
                    detected_word=None,
                    word_position=idx,
                    ayah=ayah,
                ))

        elif tag == "insert":
            # In transcription but not in expected → added
            for idx in range(j1, j2):
                word_errors.append(WordError(
                    error_type="added",
                    expected_word=None,
                    detected_word=transcribed_orig[idx],
                    word_position=None,
                    ayah=ayah,
                ))

    return VerifiedAyah(
        surah=surah,
        ayah=ayah,
        word_errors=word_errors,
        verified_word_indices=verified,
        skipped_word_indices=skipped,
    )


# ===================================================================
# Manual test
# ===================================================================
if __name__ == "__main__":

    # ------ load expected words for Surah 1, Ayah 1 ------
    data_path = Path(__file__).resolve().parent.parent / "data" / "quran_text" / "quran_hafs.json"
    with open(data_path, encoding="utf-8") as f:
        quran = json.load(f)

    surah_1 = quran["surahs"][0]
    ayah_1_text = surah_1["ayahs"][0]["text"]
    expected = ayah_1_text.split()

    print(f"Expected words ({len(expected)}): {expected}\n")

    # ------ run verification on test audio ------
    test_wav = "/Users/aziz_rakhimov/Desktop/quran_vc_dataset/reciter_2/surah_1_wav16k/001_001.wav"
    if not os.path.isfile(test_wav):
        print(f"Test WAV not found: {test_wav}")
        raise SystemExit(1)

    result = verify_ayah(
        audio_path=test_wav,
        surah=1,
        ayah=1,
        expected_words=expected,
    )

    # ------ print results ------
    print(f"Surah: {result.surah}, Ayah: {result.ayah}")
    print(f"Verified indices: {sorted(result.verified_word_indices)}")
    print(f"Skipped indices:  {sorted(result.skipped_word_indices)}")
    print(f"Word errors:      {len(result.word_errors)}")
    for err in result.word_errors:
        print(f"  [{err.error_type}] pos={err.word_position} "
              f"expected={err.expected_word!r} detected={err.detected_word!r}")
    if not result.word_errors:
        print("  (none — all words verified)")
