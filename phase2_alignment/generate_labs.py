import json
import os
import unicodedata

# Paths
QURAN_JSON = '/Users/aziz_rakhimov/quranic-recitation-assessment/data/quran_text/quran_hafs.json'
CORPUS_DIR = '/Users/aziz_rakhimov/quranic-recitation-assessment/phase2_alignment/corpus'

# Load Quran data
with open(QURAN_JSON) as f:
    data = json.load(f)

# Build lookup: (surah_number, ayah_number) -> text
lookup = {}
for surah in data['surahs']:
    for ayah in surah['ayahs']:
        lookup[(surah['number'], ayah['number'])] = ayah['text']

# Generate .lab for each .wav in corpus
generated = 0
missing = []

for filename in sorted(os.listdir(CORPUS_DIR)):
    if not filename.endswith('.wav'):
        continue

    # Parse surah and ayah from filename: 001_001.wav
    name = filename.replace('.wav', '')
    parts = name.split('_')
    if len(parts) != 2:
        print(f"  SKIP (unexpected name format): {filename}")
        continue

    surah_num = int(parts[0])
    ayah_num  = int(parts[1])

    key = (surah_num, ayah_num)
    if key not in lookup:
        missing.append(filename)
        print(f"  MISSING in JSON: surah {surah_num}, ayah {ayah_num}")
        continue

    # Write .lab file (NFC-normalized to match dictionary)
    lab_path = os.path.join(CORPUS_DIR, name + '.lab')
    text = unicodedata.normalize('NFC', lookup[key])
    # Strip kashida and waqf signs to match Phase 1 output
    text = text.replace('\u0640', '')
    WAQF = set('\u06D6\u06D7\u06D8\u06D9\u06DA\u06DB\u06DC\u06DD\u06DE\u06DF\u06E0\u06E2\u06ED')
    text = ''.join(c for c in text if c not in WAQF)
    with open(lab_path, 'w', encoding='utf-8') as f:
        f.write(text)

    print(f"  ✅ {name}.lab → {lookup[key]}")
    generated += 1

print(f"\nDone. Generated: {generated} | Missing: {len(missing)}")
