#!/usr/bin/env python3
"""
Diagnostic Script - Core Issues

Diagnoses the root causes of rule detection failures:
1. Long vowel detection
2. Sukoon representation
3. Cross-word boundaries
4. Context building
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline


def diagnose_long_vowels():
    """Diagnose long vowel phonemization."""
    print("=" * 80)
    print("DIAGNOSIS 1: Long Vowel Detection")
    print("=" * 80)

    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)

    # Test cases with known long vowels
    test_cases = [
        ("بِسْمِ ٱللَّهِ", "Should have long [aː] in ٱللَّهِ"),
        ("ٱلرَّحْمَٰنِ", "Should have long [aː] in ٱلرَّحْمَٰنِ"),
        ("قُلْ هُوَ", "Should have long [uː] in هُوَ"),
        ("ٱلضَّآلِّينَ", "Should have long [aː] before doubled لّ"),
    ]

    for text, note in test_cases:
        print(f"\nText: {text}")
        print(f"Note: {note}")

        output = pipeline.process_text(text)
        phonemes = output.phoneme_sequence.phonemes

        # Check for long vowels
        long_vowels = [p for p in phonemes if 'ː' in p.symbol]
        print(f"Phonemes: {[p.symbol for p in phonemes]}")
        print(f"Long vowels found: {[p.symbol for p in long_vowels]}")

        if not long_vowels:
            print("❌ NO LONG VOWELS DETECTED - This is the problem!")
        else:
            print(f"✅ {len(long_vowels)} long vowel(s) found")


def diagnose_sukoon():
    """Diagnose sukoon detection."""
    print("\n\n" + "=" * 80)
    print("DIAGNOSIS 2: Sukoon Detection")
    print("=" * 80)

    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)

    # Test cases with sukoon (consonant not followed by vowel)
    test_cases = [
        ("ذَٰلِكَ", "دْ should have sukoon (no vowel after د)"),
        ("قَدْ", "دْ at end should have sukoon"),
        ("ٱلْكِتَٰبُ", "لْ should have sukoon"),
        ("مِنْ شَرِّ", "نْ should have sukoon"),
    ]

    for text, note in test_cases:
        print(f"\nText: {text}")
        print(f"Note: {note}")

        output = pipeline.process_text(text)
        phonemes = output.phoneme_sequence.phonemes

        print(f"Phonemes: {[p.symbol for p in phonemes]}")

        # Check phoneme sequence pattern
        print("Consonant-Vowel pattern:")
        for i, p in enumerate(phonemes):
            p_type = "V" if p.is_vowel() else "C"
            # Check if next is vowel
            has_vowel_after = (i + 1 < len(phonemes) and phonemes[i + 1].is_vowel())
            sukoon_marker = " (SUKOON)" if not p.is_vowel() and not has_vowel_after else ""
            print(f"  [{i}] {p.symbol:<3} {p_type}{sukoon_marker}")

        # Count consonants without following vowels
        sukoon_count = sum(
            1 for i, p in enumerate(phonemes)
            if not p.is_vowel() and (i + 1 >= len(phonemes) or not phonemes[i + 1].is_vowel())
        )
        print(f"\nConsonants with sukoon (no following vowel): {sukoon_count}")


def diagnose_word_boundaries():
    """Diagnose word boundary handling."""
    print("\n\n" + "=" * 80)
    print("DIAGNOSIS 3: Word Boundaries & Cross-Word Detection")
    print("=" * 80)

    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)

    # Test cross-word patterns
    test_cases = [
        ("مِن شَرِّ", "noon before ش across word boundary"),
        ("رَيْبَ فِيهِ", "tanween before ف across word boundary"),
        ("لَنَسْفَعًۢا بِٱلنَّاصِيَةِ", "tanween before ب (iqlab)"),
    ]

    for text, note in test_cases:
        print(f"\nText: {text}")
        print(f"Note: {note}")

        output = pipeline.process_text(text)
        phonemes = output.phoneme_sequence.phonemes
        word_boundaries = output.phoneme_sequence.word_boundaries

        print(f"Phonemes: {[p.symbol for p in phonemes]}")
        print(f"Word boundaries at indices: {word_boundaries}")

        # Show phonemes with word boundary markers
        print("\nPhoneme sequence with word boundaries:")
        for i, p in enumerate(phonemes):
            boundary_marker = " | WORD_BOUNDARY" if i in word_boundaries else ""
            print(f"  [{i:2d}] {p.symbol:<3}{boundary_marker}")

        # Check if we can access phonemes across boundaries
        print("\nCross-boundary access test:")
        for i in range(len(phonemes) - 1):
            current = phonemes[i]
            next_p = phonemes[i + 1]
            crosses_boundary = (i + 1) in word_boundaries
            print(f"  [{i}] {current.symbol} → [{i+1}] {next_p.symbol} "
                  f"{'(crosses word boundary)' if crosses_boundary else ''}")


def diagnose_context_building():
    """Diagnose context building in rule engine."""
    print("\n\n" + "=" * 80)
    print("DIAGNOSIS 4: Context Building")
    print("=" * 80)

    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)

    # Test a simple case
    text = "مِنْ شَرِّ"
    print(f"Text: {text}")
    print(f"Expected: noon before ش should trigger ikhfaa")

    output = pipeline.process_text(text)
    phonemes = output.phoneme_sequence.phonemes

    print(f"\nPhonemes: {[p.symbol for p in phonemes]}")

    # Manually check context at each position
    print("\nContext details at each position:")
    for i, p in enumerate(phonemes):
        print(f"\n  Position [{i}]: {p.symbol}")
        print(f"    is_vowel: {p.is_vowel()}")
        print(f"    is_consonant: {p.is_consonant()}")

        if i + 1 < len(phonemes):
            next_p = phonemes[i + 1]
            has_sukoon = not next_p.is_vowel() if not p.is_vowel() else False
            print(f"    next phoneme: {next_p.symbol}")
            print(f"    has_sukoon: {has_sukoon}")
            print(f"    next_is_vowel: {next_p.is_vowel()}")

    # Show what rules were actually detected
    print(f"\nRules detected:")
    for app in output.annotated_sequence.rule_applications:
        print(f"  • {app.rule.name} at position {app.start_index}")


def diagnose_tanween():
    """Diagnose tanween phonemization."""
    print("\n\n" + "=" * 80)
    print("DIAGNOSIS 5: Tanween Phonemization")
    print("=" * 80)

    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)

    # Test tanween cases
    test_cases = [
        ("كِتَابٌ", "Tanween damm (ٌ) should produce [u, n]"),
        ("رَيْبَ", "Tanween fath (ً) should produce [a, n]"),
        ("أَلِيمٌۢ بِمَا", "Tanween before ب should trigger iqlab"),
    ]

    for text, note in test_cases:
        print(f"\nText: {text}")
        print(f"Note: {note}")

        output = pipeline.process_text(text)
        phonemes = output.phoneme_sequence.phonemes

        print(f"Phonemes: {[p.symbol for p in phonemes]}")

        # Check for noon phonemes (from tanween)
        noon_phonemes = [i for i, p in enumerate(phonemes) if p.symbol == 'n']
        if noon_phonemes:
            print(f"✅ Noon phonemes found at positions: {noon_phonemes}")
            # Check what follows each noon
            for idx in noon_phonemes:
                if idx + 1 < len(phonemes):
                    next_p = phonemes[idx + 1]
                    print(f"   Noon at [{idx}] followed by [{idx+1}] {next_p.symbol}")
        else:
            print(f"❌ NO NOON PHONEMES from tanween!")


def main():
    """Run all diagnostics."""
    print("\n" + "=" * 80)
    print("SYMBOLIC LAYER DIAGNOSTIC SUITE")
    print("=" * 80)
    print("\nDiagnosing core issues preventing rule detection...\n")

    try:
        diagnose_long_vowels()
        diagnose_sukoon()
        diagnose_word_boundaries()
        diagnose_context_building()
        diagnose_tanween()

        print("\n\n" + "=" * 80)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 80)
        print("\nReview the output above to identify root causes.")
        print("\nKey questions:")
        print("  1. Are long vowels (aː, iː, uː) being created?")
        print("  2. Are consonants without following vowels identified?")
        print("  3. Can rules access phonemes across word boundaries?")
        print("  4. Is context (has_sukoon, etc.) being set correctly?")
        print("  5. Does tanween produce two phonemes [vowel, n]?")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Diagnostic failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
