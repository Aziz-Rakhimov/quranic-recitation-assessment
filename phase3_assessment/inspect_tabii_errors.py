#!/usr/bin/env python3
"""Inspect the 9 Group B madd_tabii major errors in full context."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phase3_assessment.utils.loader import load_surah

# (surah, ayah, word_text, phone_ipa, approx_ms)
CASES = [
    (36, 46, "تَأْتِيهِم",    "iː", 500),
    (36, 48, "وَيَقُولُونَ",  "uː", 430),
    (36, 53, "جَمِيعٌ",       "iː", 420),
    (36, 58, "سَلَٰمٌ",       "aː", 380),
    (36, 67, "ٱسْتَطَٰعُوا", "uː", 500),
    (36, 69, "يَنبَغِى",      "iː", 360),
    (36, 73, "فِيهَا",        "iː", 370),
    (36, 79, "يُحْيِيهَا",   "iː", 450),
    (97,  4, "وَٱلرُّوحُ",   "uː", 530),
]

HARAKAH = {36: 100.0, 97: 120.0}
SEP = "-" * 72


def find_word(words, target_text):
    for i, w in enumerate(words):
        if w.text == target_text:
            return i
    for i, w in enumerate(words):
        if target_text in w.text or w.text in target_text:
            return i
    return None


def find_phone_after(words, word_idx, target_ipa, target_start):
    """Return the first phone that comes after the target phone."""
    passed = False
    for wi, w in enumerate(words):
        for p in w.phones:
            if passed:
                return p, w
            if (wi == word_idx
                    and p.ipa == target_ipa
                    and abs(p.start - target_start) < 0.02):
                passed = True
    return None, None


def main():
    cache = {}

    for case_num, (surah, ayah_num, target_word, target_ipa, approx_ms) in enumerate(CASES, 1):
        if surah not in cache:
            cache[surah] = load_surah(surah)
        data = cache[surah]

        verse = next(v for v in data.verses if v.ayah == ayah_num)
        words = verse.words
        hrkh = HARAKAH[surah]

        wi = find_word(words, target_word)
        if wi is None:
            print(f"ERROR: word '{target_word}' not found in S{surah}:{ayah_num}")
            continue

        word = words[wi]

        # Find target phone
        target_phone = None
        for p in word.phones:
            if p.ipa == target_ipa and abs(p.duration_ms - approx_ms) <= 30:
                target_phone = p
                break
        if target_phone is None:
            for p in word.phones:
                if p.ipa == target_ipa:
                    target_phone = p
                    break

        prev_word = words[wi - 1] if wi > 0 else None
        next_word = words[wi + 1] if wi + 1 < len(words) else None

        gap_ms = None
        if next_word is not None:
            gap_ms = round((next_word.start - word.end) * 1000)

        # Phone immediately after target
        next_phone, next_phone_word = None, None
        if target_phone:
            next_phone, next_phone_word = find_phone_after(words, wi, target_ipa, target_phone.start)

        # Ayah display: mark target word with >>> <<<
        highlighted = []
        for i, w in enumerate(words):
            if i == wi:
                highlighted.append(f">>>{w.text}<<<")
            else:
                highlighted.append(w.text)
        ayah_display = " ".join(highlighted)

        # Print
        print(SEP)
        counts = approx_ms / hrkh
        print(f"CASE {case_num}  S{surah}:{ayah_num}   word: {target_word}   [{target_ipa}]")
        print(f"       Duration: {approx_ms}ms = {counts:.2f} counts @ {hrkh:.0f}ms/harakah")
        print()
        print(f"  Full ayah ({len(words)} words):")
        print(f"  {ayah_display}")
        print()
        print(f"  Context:")
        print(f"    Prev  : {prev_word.text if prev_word else '(first word)'}")
        print(f"    THIS  : {word.text}")

        if target_phone:
            rules_str = (", ".join(target_phone.tajweed_rules)
                         if target_phone.tajweed_rules else "(none)")
            print(f"      [{target_ipa}]: {target_phone.duration_ms:.0f}ms = "
                  f"{target_phone.duration_ms / hrkh:.2f}c   conf={target_phone.alignment_confidence}")
            print(f"      Tajweed rules: {rules_str}")
            print(f"      Word: {word.start*1000:.0f}ms – {word.end*1000:.0f}ms  "
                  f"(word_dur={word.duration_ms:.0f}ms)")
        print(f"    Next  : {next_word.text if next_word else '(last word)'}")
        print()

        if gap_ms is not None:
            pause = "PAUSE" if gap_ms > 100 else "connected"
            print(f"  Gap to next word: {gap_ms}ms  ->  {pause}")
        else:
            print("  Gap to next word: N/A (last word in ayah)")

        if next_phone and next_phone_word:
            nr = (", ".join(next_phone.tajweed_rules)
                  if next_phone.tajweed_rules else "(none)")
            print(f"  Next phone: [{next_phone.ipa}] in '{next_phone_word.text}'  "
                  f"rules: {nr}   dur={next_phone.duration_ms:.0f}ms  "
                  f"conf={next_phone.alignment_confidence}")
        print()


if __name__ == "__main__":
    main()
