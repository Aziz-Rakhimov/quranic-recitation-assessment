#!/usr/bin/env python3
"""
Quick integration test for the Tajweed Engine.

This script tests:
1. Loading the TajweedEngine with YAML rules
2. Loading phoneme inventory
3. Creating a simple phoneme sequence
4. Applying rules and checking results
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.tajweed_engine import TajweedEngine
from symbolic_layer.phonemizer import QuranPhonemizer
from symbolic_layer.text_processor import QuranTextProcessor
from symbolic_layer.models.phoneme import PhonemeInventory

def main():
    print("=" * 70)
    print("Testing Tajweed Engine Integration")
    print("=" * 70)

    # Test 1: Load TajweedEngine
    print("\n1. Loading TajweedEngine...")
    try:
        engine = TajweedEngine(
            rule_config_dir="data/tajweed_rules"
        )
        print(f"   ✅ Engine loaded: {engine}")
        print(f"   - Total rules loaded: {len(engine.rules)}")

        # Show statistics
        stats = engine.get_statistics()
        print(f"   - Priority range: {stats['priority_range']}")
        print(f"   - Rules by category:")
        for cat, count in stats['rules_by_category'].items():
            if count > 0:
                print(f"     • {cat}: {count} rules")

    except Exception as e:
        print(f"   ❌ Failed to load engine: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Load PhonemeInventory
    print("\n2. Loading PhonemeInventory...")
    try:
        inventory = PhonemeInventory.from_yaml_files(
            base_phonemes_path="data/pronunciation_dict/base_phonemes.yaml",
            tajweed_phonemes_path="data/pronunciation_dict/tajweed_phonemes.yaml"
        )
        print(f"   ✅ Inventory loaded with {len(inventory.phonemes)} phonemes")

        # Show some phonemes
        print(f"   - Sample consonants: {[p.symbol for p in inventory.get_consonants()[:5]]}")
        print(f"   - Sample vowels: {[p.symbol for p in inventory.get_vowels()[:5]]}")

    except Exception as e:
        print(f"   ❌ Failed to load inventory: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Load Phonemizer
    print("\n3. Loading QuranPhonemizer...")
    try:
        phonemizer = QuranPhonemizer(
            base_phonemes_path="data/pronunciation_dict/base_phonemes.yaml",
            tajweed_phonemes_path="data/pronunciation_dict/tajweed_phonemes.yaml",
            g2p_rules_path="data/pronunciation_dict/g2p_rules.yaml"
        )
        print(f"   ✅ Phonemizer loaded")

    except Exception as e:
        print(f"   ❌ Failed to load phonemizer: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Phonemize a simple test phrase
    print("\n4. Testing phonemization...")
    test_texts = [
        "بِسْمِ",  # bismillah (first word of Al-Fatiha)
        "ٱللَّهِ",  # Allah
        "ٱلرَّحْمَٰنِ",  # ar-Rahman (should have emphatic backing)
    ]

    for text in test_texts:
        try:
            print(f"\n   Text: {text}")

            # Process text
            processor = QuranTextProcessor()
            normalized = processor.normalize(text)
            print(f"   - Normalized: {normalized}")

            # Phonemize
            phoneme_seq = phonemizer.phonemize(text)
            ipa_string = phoneme_seq.to_ipa_string()
            print(f"   - IPA: [{ipa_string}]")
            print(f"   - Phoneme count: {len(phoneme_seq.phonemes)}")

        except Exception as e:
            print(f"   ⚠️  Error processing '{text}': {e}")
            import traceback
            traceback.print_exc()

    # Test 5: Apply Tajweed rules
    print("\n5. Testing Tajweed rule application...")
    try:
        # Create engine with inventory
        engine = TajweedEngine(
            rule_config_dir="data/tajweed_rules",
            phoneme_inventory=inventory
        )

        # Test with a simple sequence
        test_word = "مِنْ"  # "min" - should trigger ikhfaa/idgham depending on next letter
        print(f"\n   Test word: {test_word}")

        # Phonemize it
        phoneme_seq = phonemizer.phonemize(test_word)
        print(f"   - Before rules: [{phoneme_seq.to_ipa_string()}]")

        # Apply rules
        annotated_seq = engine.apply_rules(phoneme_seq)
        print(f"   - After rules: [{annotated_seq.to_ipa_string()}]")
        print(f"   - Rules applied: {len(annotated_seq.rule_applications)}")

        for app in annotated_seq.rule_applications:
            print(f"     • {app.rule.name} ({app.rule.category.value})")
            print(f"       Original: {[p.symbol for p in app.original_phonemes]}")
            print(f"       Modified: {[p.symbol for p in app.modified_phonemes]}")

    except Exception as e:
        print(f"   ⚠️  Error applying rules: {e}")
        import traceback
        traceback.print_exc()

    # Test 6: Acoustic Feature Generator
    print("\n6. Testing Acoustic Feature Generator...")
    try:
        from symbolic_layer.acoustic_features import AcousticFeatureGenerator

        # Initialize generator
        feature_gen = AcousticFeatureGenerator(
            config_path="data/acoustic_features/feature_defaults.yaml",
            speaker_type="male"
        )
        print(f"   ✅ Generator initialized: {feature_gen}")

        # Generate features for a real sequence
        test_word = "بِسْمِ ٱللَّهِ"  # "Bismillāh"
        print(f"\n   Test phrase: {test_word}")

        # Phonemize
        phoneme_seq = phonemizer.phonemize(test_word)
        print(f"   - Phonemes: [{phoneme_seq.to_ipa_string()}]")

        # Apply Tajweed rules
        annotated_seq = engine.apply_rules(phoneme_seq)
        print(f"   - Rules applied: {len(annotated_seq.rule_applications)}")

        # Generate acoustic features
        acoustic_features = feature_gen.generate_features(annotated_seq)
        print(f"   ✅ Features generated for {acoustic_features.sequence_length} phonemes")
        print(f"   - Total duration: {acoustic_features.total_duration_ms:.0f} ms")

        # Show statistics
        stats = feature_gen.get_statistics(acoustic_features)
        print(f"   - Average phoneme duration: {stats['average_duration_ms']:.0f} ms")
        print(f"   - Vowels with formants: {stats['num_vowels']}")
        print(f"   - Nasalized phonemes: {stats['num_nasalized']}")
        print(f"   - Pitch range: {stats['pitch_range_hz'][0]:.0f}-{stats['pitch_range_hz'][1]:.0f} Hz")

        # Show details for first few phonemes
        print(f"\n   First 3 phonemes with features:")
        for i, pf in enumerate(acoustic_features.phoneme_features[:3]):
            print(f"   [{i}] {pf.phoneme_symbol}:")
            print(f"       Duration: {pf.duration.expected_ms:.0f} ms (±{pf.duration.expected_ms - pf.duration.min_acceptable_ms:.0f})")
            print(f"       Pitch: {pf.pitch.expected_f0_hz:.0f} Hz ({pf.pitch.contour_type.value})")
            if pf.formants:
                print(f"       Formants: F1={pf.formants.f1_hz:.0f}, F2={pf.formants.f2_hz:.0f}, F3={pf.formants.f3_hz:.0f}")
            if pf.nasalization:
                print(f"       Nasalization: intensity={pf.nasalization.nasal_intensity:.2f}")

    except Exception as e:
        print(f"   ⚠️  Error testing acoustic features: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("✅ Integration test complete!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
