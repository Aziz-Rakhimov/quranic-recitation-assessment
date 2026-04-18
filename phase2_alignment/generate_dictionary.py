import sys
import os
import unicodedata

# Add Phase 1 source to path
sys.path.insert(0, '/Users/aziz_rakhimov/quranic-recitation-assessment/src')

from symbolic_layer.pipeline import SymbolicLayerPipeline

# IPA → MFA Arabic acoustic model phone mapping
# The MFA 'arabic' model uses a Buckwalter-like phone set, not IPA.
IPA_TO_MFA = {
    'ʔ': 'Q',    # hamza (glottal stop)
    'ħ': 'H',    # ح (voiceless pharyngeal fricative)
    'ʕ': 'Hq',   # ع (voiced pharyngeal fricative)
    'ɣ': 'G',    # غ (voiced velar fricative)
    'ð': 'z',    # ذ (voiced interdental → merged with z in model)
    'θ': 's',    # ث (voiceless interdental → merged with s in model)
    'ʃ': 'C',    # ش (voiceless postalveolar fricative)
    'dʒ': 'j',   # ج (voiced postalveolar affricate → closest in model)
    'sˤ': 'S',   # ص (emphatic s)
    'dˤ': 'D',   # ض (emphatic d)
    'tˤ': 'T',   # ط (emphatic t)
    'aː': 'al',  # long a
    'iː': 'il',  # long i
    'uː': 'ul',  # long u
}

def convert_phones_to_mfa(ipa_phones_str):
    """Convert IPA phone string to MFA Arabic model phone string."""
    phones = ipa_phones_str.split()
    converted = []
    for p in phones:
        converted.append(IPA_TO_MFA.get(p, p))
    return ' '.join(converted)

# Config
SURAH = 1
OUTPUT_DICT = '/Users/aziz_rakhimov/quranic-recitation-assessment/phase2_alignment/dictionary/al_fatiha.dict'

os.makedirs(os.path.dirname(OUTPUT_DICT), exist_ok=True)

print("Initializing Phase 1 pipeline...")
pipeline = SymbolicLayerPipeline()

all_entries = {}  # word -> set of pronunciation variants
errors = []

print(f"\nGenerating dictionary for Surah {SURAH}...")
for ayah_num in range(1, 8):  # Al-Fatiha has 7 ayahs
    try:
        output = pipeline.process_verse(surah=SURAH, ayah=ayah_num)
        mfa_dict = output.to_mfa_dict()

        # Parse entries (NFC-normalize words to match .lab files)
        for line in mfa_dict.strip().split('\n'):
            if '\t' in line:
                word, phonemes = line.split('\t', 1)
                word = unicodedata.normalize('NFC', word.strip())
                phonemes = phonemes.strip()
                if word and phonemes:
                    converted = convert_phones_to_mfa(phonemes)
                    if word not in all_entries:
                        all_entries[word] = set()
                    all_entries[word].add(converted)

        print(f"  ✅ Ayah {ayah_num}: {output.original_text[:40]}...")

    except Exception as e:
        errors.append((ayah_num, str(e)))
        print(f"  ❌ Ayah {ayah_num} failed: {e}")

# Write dictionary with multiple pronunciation variants per word
with open(OUTPUT_DICT, 'w', encoding='utf-8') as f:
    for word in sorted(all_entries.keys()):
        for phonemes in sorted(all_entries[word]):
            f.write(f"{word}\t{phonemes}\n")

total_variants = sum(len(v) for v in all_entries.values())
multi_pron = sum(1 for v in all_entries.values() if len(v) > 1)

print(f"\n{'='*50}")
print(f"Dictionary written: {OUTPUT_DICT}")
print(f"Total unique words: {len(all_entries)}")
print(f"Total pronunciation variants: {total_variants}")
print(f"Words with multiple pronunciations: {multi_pron}")
print(f"Errors: {len(errors)}")

# Preview
print(f"\nFirst 10 entries:")
for i, (word, variants) in enumerate(list(all_entries.items())[:10]):
    for pron in sorted(variants):
        print(f"  {word}\t{pron}")
