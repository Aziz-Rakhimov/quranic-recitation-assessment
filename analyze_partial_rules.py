#!/usr/bin/env python3
"""
Analyze the 5 partially working rules to understand why one test passes and the other fails.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline


def analyze_rule(rule_name: str, test_cases: list):
    """Analyze why a rule is only partially working."""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {rule_name}")
    print(f"{'='*80}")

    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)

    for i, test in enumerate(test_cases, 1):
        text = test['text']
        note = test['note']

        print(f"\n--- Test {i}: {text} ---")
        print(f"Note: {note}")

        try:
            output = pipeline.process_text(text)

            # Check if rule was detected
            rule_found = any(
                rule_name in app.rule.name or app.rule.name in rule_name
                for app in output.annotated_sequence.rule_applications
            )

            if rule_found:
                print(f"✅ DETECTED")
                for app in output.annotated_sequence.rule_applications:
                    if rule_name in app.rule.name or app.rule.name in rule_name:
                        print(f"   • {app.rule.name} at position {app.start_index}")
            else:
                print(f"❌ NOT DETECTED")

                # Show phonemes
                phonemes = [p.symbol for p in output.phoneme_sequence.phonemes]
                print(f"\nPhonemes: {phonemes}")

                # Show what rules were detected
                if output.annotated_sequence.rule_applications:
                    print(f"\nOther rules detected:")
                    for app in output.annotated_sequence.rule_applications[:5]:
                        print(f"   • {app.rule.name} ({app.rule.category.value}) at pos {app.start_index}")
                else:
                    print("\nNo rules detected at all!")

                # Find the rule definition
                engine = pipeline.tajweed_engine
                rule = next((r for r in engine.rules if rule_name in r.name or r.name in rule_name), None)

                if rule:
                    print(f"\n📋 Rule Pattern:")
                    print(f"   Target: {rule.pattern.target}")
                    print(f"   Conditions: {rule.pattern.conditions}")
                    print(f"   Following: {rule.pattern.following_context}")
                    print(f"   Preceding: {rule.pattern.preceding_context}")

                    # Try to find potential matches
                    print(f"\n🔍 Searching for potential matches in phonemes:")
                    for idx, phoneme in enumerate(output.phoneme_sequence.phonemes):
                        if rule.pattern.matches_target(phoneme.symbol):
                            print(f"   Position {idx}: '{phoneme.symbol}' matches target!")

                            # Build context at this position
                            context = engine._build_context(
                                output.phoneme_sequence.phonemes,
                                idx,
                                output.phoneme_sequence.word_boundaries,
                                output.phoneme_sequence.verse_boundaries
                            )

                            # Check conditions
                            print(f"   Context conditions:")
                            for cond_key, cond_val in rule.pattern.conditions.items():
                                actual = context.get(cond_key, "NOT IN CONTEXT")
                                match = actual == cond_val if actual != "NOT IN CONTEXT" else False
                                symbol = "✓" if match else "✗"
                                print(f"      {symbol} {cond_key}: expected={cond_val}, actual={actual}")

                            # Check following context
                            if rule.pattern.following_context and idx + 1 < len(output.phoneme_sequence.phonemes):
                                next_sym = output.phoneme_sequence.phonemes[idx + 1].symbol
                                following_match = engine._matches_pattern(next_sym, rule.pattern.following_context)
                                symbol = "✓" if following_match else "✗"
                                print(f"      {symbol} Following '{rule.pattern.following_context}' matches '{next_sym}': {following_match}")

        except Exception as e:
            print(f"⚠️  ERROR: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Analyze the 5 partially working rules."""

    # Define test cases for each partial rule
    test_cases = {
        'idgham_ghunnah_noon': [
            {'text': 'وَبَشِّرِ ٱلَّذِينَ ءَامَنُوا۟ وَعَمِلُوا۟', 'note': 'ءَامَنُوا۟ وَ - tanween before waw'},
            {'text': 'مِن وَلِىٍّ وَلَا نَصِيرٍ', 'note': 'مِن وَلِىٍّ - noon before waw'},
        ],

        'ikhfaa_shafawi': [
            {'text': 'تَرْمِيهِم بِحِجَارَةٍ', 'note': 'تَرْمِيهِم بِ - meem before baa'},
            {'text': 'وَعَلَىٰ سَمْعِهِمْ وَعَلَىٰ أَبْصَٰرِهِمْ', 'note': 'Check for meem before baa pattern'},
        ],

        'madd_muttasil': [
            {'text': 'أَوْ كَصَيِّبٍ مِّنَ ٱلسَّمَآءِ', 'note': 'ٱلسَّمَآءِ - long aa before hamza in same word'},
            {'text': 'وَلَا تَسْتَوِى ٱلْحَسَنَةُ وَلَا ٱلسَّيِّئَةُ', 'note': 'ٱلسَّيِّئَةُ has long ii before hamza in same word'},
        ],

        'qalqalah_minor': [
            {'text': 'ذَٰلِكَ ٱلْكِتَٰبُ', 'note': 'ذَٰلِكَ has daal with sukoon mid-word'},
            {'text': 'وَٱقْتُلُوهُمْ حَيْثُ', 'note': 'يَقْتُلُوهُمْ has qaaf with sukoon mid-word'},
        ],

        'qalqalah_with_shaddah': [
            {'text': 'وَٱلشَّفْعِ وَٱلْوَتْرِ', 'note': 'Check for shaddah on qalqalah letter'},
            {'text': 'أَءُلْقِىَ ٱلذِّكْرُ', 'note': 'ٱلذِّكْرُ may have qalqalah + shaddah'},
        ],
    }

    for rule_name, tests in test_cases.items():
        analyze_rule(rule_name, tests)

    print(f"\n\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print("\nNext steps:")
    print("1. Review failing tests and identify root causes")
    print("2. Fix test cases or implementation as needed")
    print("3. Re-run verification to confirm improvements")


if __name__ == "__main__":
    main()
