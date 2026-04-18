#!/usr/bin/env python3
"""
Debug script for tanween fath issue.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline
from symbolic_layer.utils.diacritic_utils import extract_diacritics
from symbolic_layer.utils.unicode_utils import TANWEEN_FATH

def debug_word(word):
    """Debug a single word."""
    print(f"\n{'=' * 80}")
    print(f"Word: {word}")
    print(f"{'=' * 80}")

    # Show Unicode codepoints
    print(f"\nUnicode codepoints:")
    for i, char in enumerate(word):
        print(f"  [{i}] {char} = U+{ord(char):04X}")

    # Extract diacritics
    diacritics = extract_diacritics(word)
    print(f"\nExtracted diacritics:")
    for d in diacritics:
        print(f"  Position {d.position}: {d.diacritic_type.value} ({d.char})")

    # Check for tanween fath
    print(f"\nTANWEEN_FATH constant: U+{ord(TANWEEN_FATH):04X}")
    has_tanween_fath = TANWEEN_FATH in word
    print(f"Has TANWEEN_FATH character: {has_tanween_fath}")

    # Phonemize
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    output = pipeline.process_text(word)
    phonemes = output.phoneme_sequence.phonemes

    print(f"\nPhonemized:")
    for i, p in enumerate(phonemes):
        print(f"  [{i}] {p.symbol}")

    # Check for noon
    noon_count = sum(1 for p in phonemes if p.symbol == 'n')
    print(f"\nNoon phonemes found: {noon_count}")

    if noon_count == 0:
        print("❌ NO NOON - This is the bug!")
    else:
        print("✅ Noon found")


def main():
    """Main function."""
    # Test cases
    test_words = [
        "رَيْبَ",        # Should have tanween fath → [a, n]
        "كِتَابٌ",       # Tanween damm → [u, n] (working)
        "أَلِيمٌۢ",      # Tanween damm with superscript alef
    ]

    for word in test_words:
        debug_word(word)


if __name__ == "__main__":
    main()
