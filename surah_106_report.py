#!/usr/bin/env python3
"""
Tajweed Analysis Report — Surah 106 (Quraysh)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from symbolic_layer.pipeline import SymbolicLayerPipeline

sys.path.insert(0, str(Path(__file__).parent))
from systematic_validation import process_verse
from surah_97_report import generate_html, strip_waqf

# ── Surah 106 verse data ───────────────────────────────────────────
SURAH_106 = {
    'number': 106,
    'name': 'Quraysh',
    'arabic_name': 'قريش',
    'meaning': 'Quraysh',
    'verses': [
        {
            'ayah': 1,
            'text': 'لِإِيلَٰفِ قُرَيْشٍ',
            'transliteration': 'Li-ʾīlāfi Quraysh',
            'translation': '(Mentioned) for the accustomed security of the Quraysh',
        },
        {
            'ayah': 2,
            'text': 'إِۦلَٰفِهِمْ رِحْلَةَ ٱلشِّتَآءِ وَٱلصَّيْفِ',
            'transliteration': 'ʾĪlāfihim riḥlata sh-shitāʾi wa-ṣ-ṣayf',
            'translation': 'Their accustomed security [in] the caravan of winter and summer —',
        },
        {
            'ayah': 3,
            'text': 'فَلْيَعْبُدُوا۟ رَبَّ هَٰذَا ٱلْبَيْتِ',
            'transliteration': 'Fal-yaʿbudū rabba hādhā l-bayt',
            'translation': 'Let them worship the Lord of this House,',
        },
        {
            'ayah': 4,
            'text': 'ٱلَّذِىٓ أَطْعَمَهُم مِّن جُوعٍ وَءَامَنَهُم مِّنْ خَوْفٍ',
            'transliteration': "Alladhī aṭʿamahum min jūʿin wa-āmanahum min khawf",
            'translation': 'Who has fed them, [saving them] from hunger, and made them safe from fear.',
        },
    ],
}


def main():
    print('=' * 60)
    print('SURAH 106 (QURAYSH) — TAJWEED ANALYSIS REPORT')
    print('=' * 60)

    print('\nInitializing pipeline...')
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f'Pipeline ready: {len(pipeline.tajweed_engine.rules)} rules\n')

    verse_results = []
    for verse in SURAH_106['verses']:
        text = strip_waqf(verse['text'])
        print(f"  Processing ayah {verse['ayah']}: {text[:45]}...")
        try:
            detected, output, highlighted_text = process_verse(pipeline, text)
            verse_results.append({
                'verse': verse,
                'detected': detected,
                'highlighted_text': highlighted_text,
            })
            print(f"    → {len(detected)} rule(s) detected")
            for d in sorted(detected, key=lambda x: x['phoneme_idx']):
                print(f"       {d['rule']:35s}  {d['word']}")
        except Exception as e:
            import traceback
            print(f'    ERROR: {e}')
            traceback.print_exc()
            verse_results.append({
                'verse': verse,
                'detected': [],
                'highlighted_text': verse['text'],
            })

    html = generate_html(SURAH_106, verse_results)
    out_dir = Path(__file__).parent / 'output'
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / 'surah_106_report.html'
    out_file.write_text(html, encoding='utf-8')

    total = sum(len(r['detected']) for r in verse_results)
    print(f'\nTotal rules detected: {total}')
    print(f'Report: {out_file}')
    print('=' * 60)


if __name__ == '__main__':
    main()
