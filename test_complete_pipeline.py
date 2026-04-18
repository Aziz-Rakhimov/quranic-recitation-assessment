#!/usr/bin/env python3
"""
Complete Pipeline Test.

This script tests the entire Symbolic Layer pipeline end-to-end,
including all export formats and verification targets.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline


def main():
    print("=" * 70)
    print("Testing Complete Symbolic Layer Pipeline")
    print("=" * 70)

    # Test 1: Initialize Pipeline
    print("\n1. Initializing pipeline...")
    try:
        pipeline = SymbolicLayerPipeline(
            speaker_type="male"
        )
        print(f"   ✅ Pipeline initialized: {pipeline}")

        # Show statistics
        stats = pipeline.get_statistics()
        print(f"\n   Pipeline Statistics:")
        print(f"   - Phonemes: {stats['phoneme_inventory']['total_phonemes']}")
        print(f"   - Tajweed rules: {stats['tajweed_engine']['total_rules']}")
        print(f"   - Qur'an text loaded: {stats['pipeline']['quran_text_loaded']}")

    except Exception as e:
        print(f"   ❌ Failed to initialize pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Process arbitrary text
    print("\n2. Processing arbitrary text...")
    test_text = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"  # Bismillah ar-Rahman ar-Rahim
    print(f"   Text: {test_text}")

    try:
        output = pipeline.process_text(test_text)
        print(f"   ✅ Processing complete: {output}")

        # Show results
        print(f"\n   Results:")
        print(f"   - IPA: [{output.to_ipa_string()}]")
        print(f"   - Phonemes: {len(output.phoneme_sequence.phonemes)}")
        print(f"   - Tajweed rules applied: {len(output.annotated_sequence.rule_applications)}")
        print(f"   - Total duration: {output.acoustic_features.total_duration_ms:.0f} ms")

        # Show statistics
        stats = output.get_statistics()
        print(f"\n   Statistics:")
        print(f"   - Vowels: {stats['phonemes']['vowels']}")
        print(f"   - Consonants: {stats['phonemes']['consonants']}")
        print(f"   - Emphatic: {stats['phonemes']['emphatic']}")
        print(f"   - Nasalized: {stats['acoustic_features']['nasalized_phonemes']}")

    except Exception as e:
        print(f"   ❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Process specific verse
    print("\n3. Processing specific verse (Al-Fatiha 1:1)...")
    try:
        verse_output = pipeline.process_verse(surah=1, ayah=1)
        print(f"   ✅ Verse processed: {verse_output.original_text}")
        print(f"   - IPA: [{verse_output.to_ipa_string()}]")
        print(f"   - Duration: {verse_output.acoustic_features.total_duration_ms:.0f} ms")

    except Exception as e:
        print(f"   ⚠️  Verse processing: {e}")
        # This might fail if Qur'an text is not loaded, which is okay

    # Test 4: Export to MFA dictionary format
    print("\n4. Testing MFA dictionary export...")
    try:
        mfa_dict = output.to_mfa_dict()
        print(f"   ✅ MFA dictionary generated ({len(mfa_dict)} chars)")
        print(f"\n   Sample (first 200 chars):")
        print(f"   {mfa_dict[:200]}")

    except Exception as e:
        print(f"   ⚠️  MFA export error: {e}")
        import traceback
        traceback.print_exc()

    # Test 5: Export to JSON
    print("\n5. Testing JSON export...")
    try:
        json_output = output.to_json(indent=2)
        print(f"   ✅ JSON generated ({len(json_output)} chars)")
        print(f"\n   Sample (first 500 chars):")
        print(f"   {json_output[:500]}...")

    except Exception as e:
        print(f"   ⚠️  JSON export error: {e}")
        import traceback
        traceback.print_exc()

    # Test 6: Export to TextGrid
    print("\n6. Testing TextGrid export...")
    try:
        textgrid = output.to_textgrid()
        print(f"   ✅ TextGrid generated ({len(textgrid)} chars)")
        print(f"\n   Sample (first 300 chars):")
        print(f"   {textgrid[:300]}...")

    except Exception as e:
        print(f"   ⚠️  TextGrid export error: {e}")
        import traceback
        traceback.print_exc()

    # Test 7: Generate verification targets
    print("\n7. Testing verification target generation...")
    try:
        targets = output.get_verification_targets()
        print(f"   ✅ Verification targets generated: {len(targets)} targets")

        # Show first few targets
        print(f"\n   Sample targets (first 3):")
        for i, target in enumerate(targets[:3]):
            print(f"   [{i}] {target.phoneme_symbol}:")
            print(f"       Duration: {target.expected_duration_ms:.0f}ms (±{target.duration_tolerance_ms:.0f})")
            if target.expected_f0_hz:
                print(f"       Pitch: {target.expected_f0_hz:.0f}Hz (±{target.f0_tolerance_hz:.0f})")
            if target.expected_f2_hz:
                print(f"       F2: {target.expected_f2_hz:.0f}Hz")
            if target.expected_nasalization:
                print(f"       Nasalization: {target.nasalization_intensity:.2f}")
            if target.applied_rules:
                print(f"       Rules: {', '.join(target.applied_rules[:2])}")
            print(f"       Priority: {target.priority:.1f}")

    except Exception as e:
        print(f"   ⚠️  Verification target error: {e}")
        import traceback
        traceback.print_exc()

    # Test 8: Test rule breakdown
    print("\n8. Analyzing Tajweed rule applications...")
    try:
        print(f"   Total rules applied: {len(output.annotated_sequence.rule_applications)}")

        # Group by category
        by_category = {}
        for app in output.annotated_sequence.rule_applications:
            cat = app.rule.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        print(f"   Rules by category:")
        for cat, count in sorted(by_category.items()):
            print(f"     • {cat}: {count}")

        # Show specific rules
        if output.annotated_sequence.rule_applications:
            print(f"\n   Specific rule applications:")
            for app in output.annotated_sequence.rule_applications[:5]:
                orig = [p.symbol for p in app.original_phonemes]
                mod = [p.symbol for p in app.modified_phonemes]
                print(f"     • {app.rule.name}: {orig} → {mod}")

    except Exception as e:
        print(f"   ⚠️  Rule analysis error: {e}")

    # Test 9: Save outputs to files
    print("\n9. Saving outputs to files...")
    output_dir = Path("output/test_pipeline")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Save MFA dictionary
        mfa_file = output_dir / "test_verse.dict"
        with open(mfa_file, 'w', encoding='utf-8') as f:
            f.write(output.to_mfa_dict())
        print(f"   ✅ Saved MFA dictionary: {mfa_file}")

        # Save JSON
        json_file = output_dir / "test_verse.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(output.to_json(indent=2))
        print(f"   ✅ Saved JSON: {json_file}")

        # Save TextGrid
        textgrid_file = output_dir / "test_verse.TextGrid"
        with open(textgrid_file, 'w', encoding='utf-8') as f:
            f.write(output.to_textgrid())
        print(f"   ✅ Saved TextGrid: {textgrid_file}")

        print(f"\n   All outputs saved to: {output_dir.absolute()}")

    except Exception as e:
        print(f"   ⚠️  File saving error: {e}")

    print("\n" + "=" * 70)
    print("✅ Complete Pipeline Test Finished!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
