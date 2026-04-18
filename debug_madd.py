#!/usr/bin/env python3
"""Debug script for Madd rule detection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline

# Test Madd Tabii
text = 'قَالَ'  # qaala

print(f"Testing: {text}")
print("=" * 80)

pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
output = pipeline.process_text(text)

phonemes = output.phoneme_sequence.phonemes

print(f"\nPhonemes:")
for i, p in enumerate(phonemes):
    print(f"  [{i}] {p.symbol} - is_long: {p.is_long()}, is_vowel: {p.is_vowel()}")

# Manually build context for position 2 (the aː)
if len(phonemes) > 2:
    engine = pipeline.tajweed_engine
    context = engine._build_context(
        phonemes,
        2,  # Index of aː
        output.phoneme_sequence.word_boundaries,
        output.phoneme_sequence.verse_boundaries
    )

    print(f"\nContext at position 2 (aː):")
    for key, value in sorted(context.items()):
        if 'long' in key.lower() or 'hamza' in key.lower() or 'sukoon' in key.lower():
            print(f"  {key}: {value}")

# Check if madd_tabii rule exists
madd_rules = [r for r in engine.rules if 'madd' in r.name.lower()]
print(f"\nMadd rules loaded: {[r.name for r in madd_rules]}")

if madd_rules:
    madd_tabii = next((r for r in madd_rules if r.name == 'madd_tabii'), None)
    if madd_tabii:
        print(f"\nMadd Tabii pattern:")
        print(f"  target: {madd_tabii.pattern.target}")
        print(f"  conditions: {madd_tabii.pattern.conditions}")
