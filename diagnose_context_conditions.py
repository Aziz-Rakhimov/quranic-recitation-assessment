#!/usr/bin/env python3
"""
Deep diagnostic: Show exact context conditions for failing rules.

This script shows WHY each rule pattern doesn't match by displaying
the exact context conditions that are checked.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline


def diagnose_rule_at_position(text: str, rule_name: str, expected_position: int):
    """Diagnose why a rule doesn't match at a specific position."""
    print(f"\n{'='*80}")
    print(f"DIAGNOSING: {rule_name} in '{text}'")
    print(f"Expected position: {expected_position}")
    print(f"{'='*80}")

    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    output = pipeline.process_text(text)

    phonemes = output.phoneme_sequence.phonemes
    engine = pipeline.tajweed_engine

    print(f"\nPhonemes: {[p.symbol for p in phonemes]}")
    print(f"Word boundaries: {output.phoneme_sequence.word_boundaries}")

    # Find the rule
    rule = next((r for r in engine.rules if r.name == rule_name), None)
    if not rule:
        print(f"❌ Rule '{rule_name}' not found!")
        return

    print(f"\n📋 Rule Definition:")
    print(f"   Target: {rule.pattern.target}")
    print(f"   Conditions: {rule.pattern.conditions}")
    print(f"   Following context: {rule.pattern.following_context}")
    print(f"   Preceding context: {rule.pattern.preceding_context}")

    # Build context at expected position
    if expected_position >= len(phonemes):
        print(f"\n❌ Position {expected_position} out of range (max: {len(phonemes)-1})")
        return

    context = engine._build_context(
        phonemes,
        expected_position,
        output.phoneme_sequence.word_boundaries,
        output.phoneme_sequence.verse_boundaries
    )

    print(f"\n🔍 Context at position {expected_position}:")
    print(f"   Phoneme: '{phonemes[expected_position].symbol}'")
    print(f"\n   Full context:")
    for key in sorted(context.keys()):
        print(f"      {key}: {context[key]}")

    # Check each condition
    print(f"\n✓ Condition Checks:")

    # 1. Target check
    target_match = rule.pattern.matches_target(phonemes[expected_position].symbol)
    print(f"   Target '{rule.pattern.target}' matches '{phonemes[expected_position].symbol}': {target_match}")

    # 2. Condition checks
    all_conditions_pass = True
    for condition_key, condition_value in rule.pattern.conditions.items():
        if condition_key not in context:
            print(f"   ⚠️  Condition '{condition_key}': NOT IN CONTEXT (skipped)")
            continue

        actual_value = context[condition_key]
        matches = actual_value == condition_value
        symbol = "✓" if matches else "✗"

        print(f"   {symbol} Condition '{condition_key}': expected={condition_value}, actual={actual_value}")

        if not matches:
            all_conditions_pass = False

    # 3. Following context check
    if rule.pattern.following_context:
        if expected_position + 1 < len(phonemes):
            next_symbol = phonemes[expected_position + 1].symbol
            following_match = engine._matches_pattern(next_symbol, rule.pattern.following_context)
            symbol = "✓" if following_match else "✗"
            print(f"   {symbol} Following context '{rule.pattern.following_context}' matches '{next_symbol}': {following_match}")
            if not following_match:
                all_conditions_pass = False
        else:
            print(f"   ✗ Following context: No next phoneme")
            all_conditions_pass = False

    # 4. Preceding context check
    if rule.pattern.preceding_context:
        if expected_position > 0:
            prev_symbol = phonemes[expected_position - 1].symbol
            preceding_match = engine._matches_pattern(prev_symbol, rule.pattern.preceding_context)
            symbol = "✓" if preceding_match else "✗"
            print(f"   {symbol} Preceding context '{rule.pattern.preceding_context}' matches '{prev_symbol}': {preceding_match}")
            if not preceding_match:
                all_conditions_pass = False
        else:
            print(f"   ✗ Preceding context: No previous phoneme")
            all_conditions_pass = False

    # Final verdict
    print(f"\n{'='*80}")
    if all_conditions_pass and target_match:
        print(f"✅ SHOULD MATCH - Rule should be applied!")
    else:
        print(f"❌ SHOULD NOT MATCH - Conditions failing")
    print(f"{'='*80}")

    # Check if actually applied
    applied = any(
        ra.rule.name == rule_name and ra.start_index == expected_position
        for ra in output.annotated_sequence.rule_applications
    )
    print(f"\n📊 Actually applied: {applied}")

    if (all_conditions_pass and target_match) and not applied:
        print(f"\n🐛 BUG DETECTED: Rule should match but wasn't applied!")
    elif not (all_conditions_pass and target_match) and applied:
        print(f"\n🐛 BUG DETECTED: Rule shouldn't match but was applied!")


def main():
    """Run deep diagnostics on key failing rules."""

    # Test cases: (text, rule_name, expected_position)
    test_cases = [
        # Noon Sakinah rules
        ("مِنْ هُدًى", "idhhar_halqi_noon", 2),  # n + h
        ("مِنْ وَلِيٍّ", "idgham_ghunnah_noon", 2),  # n + w
        ("مِنْ رَبِّهِمْ", "idgham_no_ghunnah", 2),  # n + r
        ("مِنْ تَحْتِ", "ikhfaa_light", 2),  # n + t

        # Meem Sakinah rules
        ("هُمْ فِيهَا", "idhhar_shafawi", 2),  # m + f
        ("لَهُمْ مَا", "idgham_shafawi_meem", 4),  # m + m

        # Madd rules
        ("إِنَّآ أَعْطَيْنَٰكَ", "madd_munfasil", 3),  # aː before next word
        ("الضَّآلِّينَ", "madd_lazim_kalimi", 4),  # aː before shaddah
        ("نَسْتَعِينُ", "madd_arid_lissukun", 7),  # iː at verse end

        # Qalqalah
        ("يَخْلُقْ", "qalqalah_minor", 5),  # q with sukoon mid-word
    ]

    for text, rule_name, position in test_cases:
        diagnose_rule_at_position(text, rule_name, position)

    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print("\nKey findings from diagnostics will appear above.")
    print("Look for:")
    print("  - Conditions marked as 'NOT IN CONTEXT' (need to be added)")
    print("  - Conditions with mismatched expected vs actual values")
    print("  - '🐛 BUG DETECTED' messages")


if __name__ == "__main__":
    main()
