#!/usr/bin/env python3
"""
Diagnose the 6 remaining failing rules to identify root causes and prioritize fixes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline


def diagnose_rule(rule_name: str, test_cases: list):
    """Analyze why a rule is failing."""
    print(f"\n{'='*80}")
    print(f"DIAGNOSING: {rule_name}")
    print(f"{'='*80}")

    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)

    for i, test in enumerate(test_cases, 1):
        text = test['text']
        note = test['note']

        print(f"\n--- Test {i}: {text[:50]}... ---")
        print(f"Note: {note}")

        try:
            output = pipeline.process_text(text)

            # Check if rule was detected
            rule_found = any(
                rule_name in app.rule.name or app.rule.name in rule_name
                for app in output.annotated_sequence.rule_applications
            )

            if rule_found:
                print(f"✅ DETECTED (shouldn't be here!)")
            else:
                print(f"❌ NOT DETECTED")

                # Show phonemes
                phonemes = [p.symbol for p in output.phoneme_sequence.phonemes]
                print(f"\nPhonemes ({len(phonemes)} total): {phonemes[:30]}{'...' if len(phonemes) > 30 else ''}")
                print(f"Word boundaries: {output.phoneme_sequence.word_boundaries}")
                print(f"Verse boundaries: {output.phoneme_sequence.verse_boundaries}")

                # Find the rule definition
                engine = pipeline.tajweed_engine
                rule = next((r for r in engine.rules if rule_name in r.name or r.name in rule_name), None)

                if rule:
                    print(f"\n📋 Rule Pattern:")
                    print(f"   Target: {rule.pattern.target}")
                    print(f"   Conditions: {rule.pattern.conditions}")
                    if rule.pattern.following_context:
                        print(f"   Following: {rule.pattern.following_context}")
                    if rule.pattern.preceding_context:
                        print(f"   Preceding: {rule.pattern.preceding_context}")

                    # Try to find potential matches
                    print(f"\n🔍 Searching for target matches:")
                    matches_found = 0
                    for idx, phoneme in enumerate(output.phoneme_sequence.phonemes[:20]):  # Check first 20
                        if rule.pattern.matches_target(phoneme.symbol):
                            matches_found += 1
                            print(f"   Position {idx}: '{phoneme.symbol}' matches target!")

                            # Build context at this position
                            context = engine._build_context(
                                output.phoneme_sequence.phonemes,
                                idx,
                                output.phoneme_sequence.word_boundaries,
                                output.phoneme_sequence.verse_boundaries
                            )

                            # Check which conditions fail
                            print(f"   Checking conditions:")
                            all_pass = True
                            for cond_key, cond_val in rule.pattern.conditions.items():
                                actual = context.get(cond_key, "NOT_IN_CONTEXT")
                                match = actual == cond_val if actual != "NOT_IN_CONTEXT" else False
                                symbol = "✓" if match else "✗"
                                print(f"      {symbol} {cond_key}: expected={cond_val}, actual={actual}")
                                if not match:
                                    all_pass = False

                            if all_pass:
                                print(f"   ⚠️  ALL CONDITIONS PASS but rule not applied!")

                            if matches_found >= 3:
                                print(f"   ... (showing first 3 matches only)")
                                break

                    if matches_found == 0:
                        print(f"   No target matches found in first 20 phonemes")
                else:
                    print(f"\n❌ Rule '{rule_name}' not found in loaded rules!")

                # Show what rules WERE detected
                if output.annotated_sequence.rule_applications:
                    print(f"\n📊 Other rules detected:")
                    for app in output.annotated_sequence.rule_applications[:5]:
                        print(f"   • {app.rule.name} ({app.rule.category.value}) at pos {app.start_index}")

        except Exception as e:
            print(f"⚠️  ERROR: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Diagnose all 6 remaining failing rules."""

    test_cases = {
        'madd_munfasil': [
            {'text': 'إِنَّآ أَعْطَيْنَٰكَ ٱلْكَوْثَرَ', 'note': 'إِنَّآ أَعْطَيْنَٰكَ - long aa before hamza in next word'},
            {'text': 'لِّلَّهِ مَا فِى ٱلسَّمَٰوَٰتِ وَمَا فِى ٱلْأَرْضِ', 'note': 'مَا فِى - long aa before hamza'},
        ],

        'madd_arid_lissukun': [
            {'text': 'إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ', 'note': 'نَسْتَعِينُ - long ii at verse end'},
            {'text': 'ٱلرَّحْمَٰنِ ٱلرَّحِيمِ', 'note': 'ٱلرَّحِيمِ - ends with long ii + meem at verse end'},
        ],

        'madd_silah_kubra': [
            {'text': 'لَّٰكِنَّا۟ هُوَ ٱللَّهُ رَبِّى', 'note': 'Check for pronoun haa before hamza'},
            {'text': 'أَن رَّءَاهُ ٱسْتَغْنَىٰٓ', 'note': 'رَّءَاهُ ٱسْتَ - pronoun haa before hamza in next word'},
        ],

        'qalqalah_major': [
            {'text': 'قُلْ أَعُوذُ بِرَبِّ ٱلْفَلَقِ', 'note': 'ٱلْفَلَقِ - qaaf at verse end'},
            {'text': 'عَلِمَتْ نَفْسٌ مَّا قَدَّمَتْ', 'note': 'قَدَّمَتْ - taa at end'},
        ],

        'qalqalah_emphatic': [
            {'text': 'وَٱلتِّينِ وَٱلزَّيْتُونِ', 'note': 'Check for emphatic qalqalah'},
            {'text': 'وَٱلشَّفْعِ وَٱلْوَتْرِ', 'note': 'Taa emphatic context'},
        ],

        'qalqalah_non_emphatic': [
            {'text': 'ذَٰلِكَ ٱلْكِتَٰبُ', 'note': 'ذَٰلِكَ - daal in light context'},
            {'text': 'وَٱلضُّحَىٰ', 'note': 'Check daal/baa in non-emphatic context'},
        ],
    }

    print("="*80)
    print("DIAGNOSING 6 REMAINING FAILING RULES")
    print("="*80)
    print("\nGoal: Identify root causes and prioritize fixes")
    print("Current rate: 16/22 (72.7%) → Target: 22/22 (100%)")

    for rule_name, tests in test_cases.items():
        diagnose_rule(rule_name, tests)

    print(f"\n\n{'='*80}")
    print("ANALYSIS SUMMARY")
    print(f"{'='*80}")
    print("\nReview the diagnostics above to identify:")
    print("1. Which rule has the simplest fix (missing context condition, etc.)")
    print("2. Which rules need implementation changes vs just test case fixes")
    print("3. Priority order for fixing")


if __name__ == "__main__":
    main()
