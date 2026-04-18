#!/usr/bin/env python3
"""
Comprehensive diagnostics for failing Tajwīd rules.

This script analyzes WHY each rule is failing by:
1. Processing test verses
2. Showing phonemes created
3. Checking pattern matching
4. Identifying missing context conditions
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline
from symbolic_layer.models.phoneme import Phoneme

# Test cases for each rule category
TEST_CASES = {
    # Noon Sakinah / Tanween Rules
    'idhhar_halqi': [
        {'text': 'مِنْ هُدًى', 'surah': 2, 'ayah': 2, 'expected_phonemes': ['n', 'h']},
        {'text': 'مِنْ عِلْمٍ', 'surah': 12, 'ayah': 68, 'expected_phonemes': ['n', 'ʕ']},
    ],
    'idgham_with_ghunnah': [
        {'text': 'مِنْ وَلِيٍّ', 'surah': 2, 'ayah': 107, 'expected_phonemes': ['n', 'w']},
        {'text': 'مَنْ يَعْمَلْ', 'surah': 99, 'ayah': 7, 'expected_phonemes': ['n', 'j']},
    ],
    'idgham_without_ghunnah': [
        {'text': 'مِنْ رَبِّهِمْ', 'surah': 2, 'ayah': 5, 'expected_phonemes': ['n', 'r']},
        {'text': 'مِنْ لَدُنْهُ', 'surah': 18, 'ayah': 2, 'expected_phonemes': ['n', 'l']},
    ],
    'iqlab': [
        {'text': 'مِنْ بَعْدِ', 'surah': 2, 'ayah': 27, 'expected_phonemes': ['n', 'b']},
        {'text': 'سَمِيعٌۢ بَصِيرٌ', 'surah': 2, 'ayah': 137, 'expected_phonemes': ['n', 'b']},
    ],
    'ikhfaa_haqiqi': [
        {'text': 'مِنْ تَحْتِ', 'surah': 2, 'ayah': 25, 'expected_phonemes': ['n', 't']},
        {'text': 'أَنْ صَدُّوكُمْ', 'surah': 5, 'ayah': 2, 'expected_phonemes': ['n', 'sˤ']},
    ],

    # Meem Sakinah Rules
    'idhhar_shafawi': [
        {'text': 'هُمْ فِيهَا', 'surah': 2, 'ayah': 39, 'expected_phonemes': ['m', 'f']},
        {'text': 'لَهُمْ عَذَابٌ', 'surah': 2, 'ayah': 7, 'expected_phonemes': ['m', 'ʕ']},
    ],
    'idgham_shafawi': [
        {'text': 'لَهُمْ مَا', 'surah': 2, 'ayah': 134, 'expected_phonemes': ['m', 'm']},
    ],
    'ikhfaa_shafawi': [
        {'text': 'عَلَيْهِمْ بِمَا', 'surah': 1, 'ayah': 7, 'expected_phonemes': ['m', 'b']},
    ],

    # Madd Rules
    'madd_muttasil': [
        {'text': 'السَّمَآءِ', 'surah': 2, 'ayah': 19, 'expected_long_vowel': 'aː', 'expected_hamza': 'ʔ'},
        {'text': 'جَآءَ', 'surah': 2, 'ayah': 89, 'expected_long_vowel': 'aː', 'expected_hamza': 'ʔ'},
    ],
    'madd_munfasil': [
        {'text': 'إِنَّآ أَعْطَيْنَٰكَ', 'surah': 108, 'ayah': 1, 'expected_long_vowel': 'aː', 'next_word_hamza': True},
        {'text': 'فِىٓ أَحْسَنِ', 'surah': 95, 'ayah': 4, 'expected_long_vowel': 'iː', 'next_word_hamza': True},
    ],
    'madd_lazim_kalimi': [
        {'text': 'الضَّآلِّينَ', 'surah': 1, 'ayah': 7, 'expected_long_vowel': 'aː', 'expected_shaddah': True},
    ],
    'madd_arid_lissukun': [
        {'text': 'نَسْتَعِينُ', 'surah': 1, 'ayah': 5, 'expected_long_vowel': 'iː', 'verse_end': True},
        {'text': 'الْعَالَمِينَ', 'surah': 1, 'ayah': 2, 'expected_long_vowel': 'iː', 'verse_end': True},
    ],

    # Qalqalah Rules
    'qalqalah_minor': [
        {'text': 'يَخْلُقْ', 'surah': 36, 'ayah': 81, 'expected_phoneme': 'q', 'mid_word': True},
    ],
    'qalqalah_major': [
        {'text': 'قَدْ', 'surah': 2, 'ayah': 108, 'expected_phoneme': 'd', 'word_end': True},
    ],
    'qalqalah_with_shaddah': [
        {'text': 'الْحَقِّ', 'surah': 2, 'ayah': 42, 'expected_phoneme': 'q', 'has_shaddah': True},
    ],
}


def analyze_phoneme_sequence(text: str, pipeline: SymbolicLayerPipeline) -> Dict[str, Any]:
    """Process text and return detailed analysis."""
    output = pipeline.process_text(text)
    phonemes = output.phoneme_sequence.phonemes

    return {
        'text': text,
        'phonemes': [p.symbol for p in phonemes],
        'phoneme_details': [
            {
                'symbol': p.symbol,
                'is_long': p.is_long(),
                'is_vowel': p.is_vowel(),
                'is_consonant': p.is_consonant(),
            }
            for p in phonemes
        ],
        'word_boundaries': output.phoneme_sequence.word_boundaries,
        'rules_applied': [
            {
                'name': ra.rule.name,
                'position': ra.start_index,
                'original': [p.symbol for p in ra.original_phonemes],
                'modified': [p.symbol for p in ra.modified_phonemes],
            }
            for ra in output.annotated_sequence.rule_applications
        ]
    }


def check_noon_meem_pattern(phonemes: List[str], expected_n_m: str, expected_next: str) -> Dict[str, Any]:
    """Check if noon/meem + following letter pattern exists."""
    for i, p in enumerate(phonemes):
        if p == expected_n_m and i + 1 < len(phonemes):
            next_p = phonemes[i + 1]
            if next_p == expected_next:
                return {
                    'found': True,
                    'position': i,
                    'pattern': f"{p} + {next_p}",
                }
    return {'found': False, 'reason': f"Pattern '{expected_n_m} + {expected_next}' not found"}


def check_long_vowel_pattern(phoneme_details: List[Dict], expected_vowel: str,
                             check_hamza_after: bool = False) -> Dict[str, Any]:
    """Check if long vowel pattern exists."""
    for i, pd in enumerate(phoneme_details):
        if pd['symbol'] == expected_vowel and pd['is_long']:
            result = {
                'found': True,
                'position': i,
                'vowel': expected_vowel,
            }
            if check_hamza_after and i + 1 < len(phoneme_details):
                next_phoneme = phoneme_details[i + 1]['symbol']
                result['hamza_after'] = next_phoneme == 'ʔ'
            return result
    return {'found': False, 'reason': f"Long vowel '{expected_vowel}' not found"}


def check_qalqalah_pattern(phonemes: List[str], expected_letter: str,
                           word_boundaries: List[int]) -> Dict[str, Any]:
    """Check if qalqalah letter exists with proper context."""
    qalqalah_letters = ['q', 'tˤ', 'b', 'd', 'dʒ']

    for i, p in enumerate(phonemes):
        if p in qalqalah_letters:
            is_word_end = (i + 1) in word_boundaries or (i + 1) >= len(phonemes)
            return {
                'found': True,
                'position': i,
                'letter': p,
                'is_word_end': is_word_end,
                'has_sukoon': i + 1 < len(phonemes) and not phonemes[i + 1] in ['a', 'i', 'u', 'aː', 'iː', 'uː']
            }
    return {'found': False, 'reason': 'No qalqalah letter found'}


def diagnose_rule(rule_name: str, test_cases: List[Dict], pipeline: SymbolicLayerPipeline):
    """Diagnose why a specific rule is failing."""
    print(f"\n{'='*80}")
    print(f"DIAGNOSING: {rule_name}")
    print(f"{'='*80}")

    for idx, test in enumerate(test_cases, 1):
        print(f"\n--- Test Case {idx}: {test['text']} ---")

        # Analyze phoneme sequence
        analysis = analyze_phoneme_sequence(test['text'], pipeline)

        print(f"\nPhonemes created: {' '.join(analysis['phonemes'])}")
        print(f"Word boundaries: {analysis['word_boundaries']}")

        # Check if rule was applied
        rule_applied = any(ra['name'] == rule_name for ra in analysis['rules_applied'])
        print(f"\n✓ Rule applied: {rule_applied}")

        if rule_applied:
            matching_apps = [ra for ra in analysis['rules_applied'] if ra['name'] == rule_name]
            for ra in matching_apps:
                print(f"  - Position {ra['position']}: {' '.join(ra['original'])} → {' '.join(ra['modified'])}")
        else:
            print(f"✗ Rule NOT applied")

            # Diagnose why based on rule category
            if 'expected_phonemes' in test:
                # Noon/Meem rule
                expected = test['expected_phonemes']
                pattern_check = check_noon_meem_pattern(analysis['phonemes'], expected[0], expected[1])
                print(f"\nPattern check: {pattern_check}")

                if pattern_check['found']:
                    print(f"  → Pattern EXISTS at position {pattern_check['position']}")
                    print(f"  → ISSUE: Rule engine not matching pattern")
                    print(f"  → Likely cause: Missing context condition or wrong pattern definition")
                else:
                    print(f"  → Pattern NOT FOUND in phonemes")
                    print(f"  → ISSUE: {pattern_check['reason']}")
                    print(f"  → Likely cause: Phonemizer not creating expected phonemes")

            elif 'expected_long_vowel' in test:
                # Madd rule
                vowel_check = check_long_vowel_pattern(
                    analysis['phoneme_details'],
                    test['expected_long_vowel'],
                    'expected_hamza' in test
                )
                print(f"\nLong vowel check: {vowel_check}")

                if vowel_check['found']:
                    print(f"  → Long vowel EXISTS at position {vowel_check['position']}")
                    if 'hamza_after' in vowel_check:
                        print(f"  → Hamza after: {vowel_check.get('hamza_after', False)}")
                    print(f"  → ISSUE: Rule engine not matching Madd pattern")
                    print(f"  → Likely cause: Missing context conditions (no_hamza_following, etc.)")
                else:
                    print(f"  → Long vowel NOT FOUND")
                    print(f"  → ISSUE: {vowel_check['reason']}")
                    print(f"  → Likely cause: Phonemizer not creating long vowels correctly")

            elif 'expected_phoneme' in test:
                # Qalqalah rule
                qalqalah_check = check_qalqalah_pattern(
                    analysis['phonemes'],
                    test['expected_phoneme'],
                    analysis['word_boundaries']
                )
                print(f"\nQalqalah check: {qalqalah_check}")

                if qalqalah_check['found']:
                    print(f"  → Qalqalah letter EXISTS at position {qalqalah_check['position']}")
                    print(f"  → Is word end: {qalqalah_check['is_word_end']}")
                    print(f"  → Has sukoon: {qalqalah_check['has_sukoon']}")
                    print(f"  → ISSUE: Rule engine not matching pattern")
                    print(f"  → Likely cause: Missing sukoon condition or position condition")
                else:
                    print(f"  → Qalqalah letter NOT FOUND")
                    print(f"  → ISSUE: {qalqalah_check['reason']}")


def main():
    """Run comprehensive diagnostics."""
    print("="*80)
    print("COMPREHENSIVE TAJWĪD RULE DIAGNOSTICS")
    print("="*80)

    # Initialize pipeline
    print("\nInitializing pipeline...")
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)

    # Track issues by category
    issues = defaultdict(list)

    # Diagnose each rule category
    for rule_name, test_cases in TEST_CASES.items():
        diagnose_rule(rule_name, test_cases, pipeline)

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY - TOP BLOCKING ISSUES")
    print(f"{'='*80}")

    print("\n1. PHONEMIZER ISSUES (Missing phonemes)")
    print("   - Tanween not creating final 'n' phoneme")
    print("   - Some long vowels not being created")
    print("   - Sukoon detection may be incorrect")

    print("\n2. RULE PATTERN MATCHING ISSUES")
    print("   - Context conditions not set correctly")
    print("   - Pattern definitions may be too strict")
    print("   - Following/preceding context checks failing")

    print("\n3. WORD BOUNDARY ISSUES")
    print("   - Rules not checking across word boundaries")
    print("   - Madd Munfasil requires cross-word detection")
    print("   - Qalqalah word-end detection may be off")


if __name__ == "__main__":
    main()
