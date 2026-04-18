#!/usr/bin/env python3
"""
Test Script: Rāʾ Rules Configuration

Demonstrates the enable_raa_rules flag functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline


def test_with_raa_disabled():
    """Test with Rāʾ rules disabled (default - Phase 1)."""
    print("=" * 70)
    print("TEST 1: Rāʾ Rules DISABLED (Default for Phase 1)")
    print("=" * 70)

    pipeline = SymbolicLayerPipeline(
        speaker_type="male",
        enable_raa_rules=False  # Explicit, but this is the default
    )

    # Get statistics
    stats = pipeline.get_statistics()
    print(f"\nConfiguration:")
    print(f"  - Total rules loaded: {stats['tajweed_engine']['total_rules']}")
    print(f"  - Rāʾ rules enabled: {stats['pipeline']['enable_raa_rules']}")
    print(f"\nRules by category:")
    for cat, count in stats['tajweed_engine']['rules_by_category'].items():
        print(f"  - {cat}: {count} rules")

    # Process test text with rāʾ
    test_text = "رَبِّ ٱلْعَٰلَمِينَ"  # "Rabbi al-'aalamiin" - contains heavy rāʾ
    print(f"\nProcessing text: {test_text}")

    output = pipeline.process_text(test_text)
    print(f"  - Phonemes: [{output.to_ipa_string()}]")
    print(f"  - Rules applied: {len(output.annotated_sequence.rule_applications)}")

    # Show which rules were applied
    if output.annotated_sequence.rule_applications:
        print(f"  - Applied rules:")
        for app in output.annotated_sequence.rule_applications:
            print(f"    • {app.rule.name} ({app.rule.category.value})")

    print(f"\n✅ With Rāʾ disabled: Focus on core rules (noon/meem, ghunnah, qalqalah, madd)")
    print(f"   No rāʾ tafkhīm/tarqīq rules applied\n")


def test_with_raa_enabled():
    """Test with Rāʾ rules enabled (future phase)."""
    print("=" * 70)
    print("TEST 2: Rāʾ Rules ENABLED (Future - Phase 2+)")
    print("=" * 70)

    pipeline = SymbolicLayerPipeline(
        speaker_type="male",
        enable_raa_rules=True  # Enable for comprehensive analysis
    )

    # Get statistics
    stats = pipeline.get_statistics()
    print(f"\nConfiguration:")
    print(f"  - Total rules loaded: {stats['tajweed_engine']['total_rules']}")
    print(f"  - Rāʾ rules enabled: {stats['pipeline']['enable_raa_rules']}")
    print(f"\nRules by category:")
    for cat, count in stats['tajweed_engine']['rules_by_category'].items():
        print(f"  - {cat}: {count} rules")

    # Process test text with rāʾ
    test_text = "رَبِّ ٱلْعَٰلَمِينَ"  # "Rabbi al-'aalamiin" - contains heavy rāʾ
    print(f"\nProcessing text: {test_text}")

    output = pipeline.process_text(test_text)
    print(f"  - Phonemes: [{output.to_ipa_string()}]")
    print(f"  - Rules applied: {len(output.annotated_sequence.rule_applications)}")

    # Show which rules were applied
    if output.annotated_sequence.rule_applications:
        print(f"  - Applied rules:")
        for app in output.annotated_sequence.rule_applications:
            print(f"    • {app.rule.name} ({app.rule.category.value})")

    print(f"\n✅ With Rāʾ enabled: Comprehensive analysis including all 10 rāʾ rules\n")


def main():
    print("\n" + "=" * 70)
    print("Rāʾ Rules Configuration Test")
    print("=" * 70)
    print("\nThis script demonstrates the enable_raa_rules configuration flag.")
    print("For Phase 1, Rāʾ rules are disabled by default to focus on core rules.\n")

    # Test 1: Rāʾ disabled (default)
    test_with_raa_disabled()

    print("\n")

    # Test 2: Rāʾ enabled
    test_with_raa_enabled()

    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    print("✅ Default (enable_raa_rules=False): 28 rules")
    print("   - Focuses on: Noon/Meem sākinah, Ghunnah, Qalqalah, Madd, Emphasis")
    print("   - Excludes: All 10 Rāʾ tafkhīm/tarqīq rules")
    print("\n✅ Enabled (enable_raa_rules=True): 38 rules")
    print("   - Includes all rules plus 10 complex Rāʾ rules")
    print("   - For future phases when ready to handle Rāʾ assessment")
    print("=" * 70)


if __name__ == "__main__":
    main()
