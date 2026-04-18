#!/usr/bin/env python3
"""
Tajweed Analysis Report — Surah 109 (Al-Kāfirūn) + Surah 1:7 (Al-Fātiḥah)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from symbolic_layer.pipeline import SymbolicLayerPipeline

sys.path.insert(0, str(Path(__file__).parent))
from systematic_validation import process_verse
from surah_97_report import generate_html, strip_waqf

# ── Surah 109 verse data ───────────────────────────────────────────
SURAH_109 = {
    'number': 109,
    'name': 'Al-Kāfirūn',
    'arabic_name': 'الكافرون',
    'meaning': 'The Disbelievers · with Al-Fātiḥah 1:7',
    'verses': [
        {
            'ayah': 1,
            'text': 'قُلْ يَٰٓأَيُّهَا ٱلْكَٰفِرُونَ',
            'transliteration': 'Qul yā-ayyuhā l-kāfirūn',
            'translation': 'Say, "O disbelievers,"',
        },
        {
            'ayah': 2,
            'text': 'لَآ أَعْبُدُ مَا تَعْبُدُونَ',
            'transliteration': 'Lā aʿbudu mā taʿbudūn',
            'translation': '"I do not worship what you worship,"',
        },
        {
            'ayah': 3,
            'text': 'وَلَآ أَنتُمْ عَٰبِدُونَ مَآ أَعْبُدُ',
            'transliteration': 'Wa-lā antum ʿābidūna mā aʿbud',
            'translation': '"Nor are you worshippers of what I worship,"',
        },
        {
            'ayah': 4,
            'text': 'وَلَآ أَنَا۠ عَابِدٌ مَّا عَبَدتُّمْ',
            'transliteration': 'Wa-lā anā ʿābidun mā ʿabadtum',
            'translation': '"Nor will I be a worshipper of what you worship,"',
        },
        {
            'ayah': 5,
            'text': 'وَلَآ أَنتُمْ عَٰبِدُونَ مَآ أَعْبُدُ',
            'transliteration': 'Wa-lā antum ʿābidūna mā aʿbud',
            'translation': '"Nor will you be worshippers of what I worship,"',
        },
        {
            'ayah': 6,
            'text': 'لَكُمْ دِينُكُمْ وَلِىَ دِينِ',
            'transliteration': 'Lakum dīnukum wa-liya dīn',
            'translation': '"For you is your religion, and for me is my religion."',
        },
    ],
}

# ── Surah 1:7 (addendum) ───────────────────────────────────────────
VERSE_1_7 = {
    'ayah': '1:7',
    'text': 'صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ',
    'transliteration': "Ṣirāṭa lladhīna anʿamta ʿalayhim ghayri l-maghḍūbi ʿalayhim wa-lā ḍ-ḍāllīn",
    'translation': 'The path of those upon whom You have bestowed favor, not of those who evoked [Your] anger, nor of those who are astray.',
}


def main():
    print('=' * 60)
    print('SURAH 109 (AL-KĀFIRŪN) + SURAH 1:7 — TAJWEED ANALYSIS REPORT')
    print('=' * 60)

    print('\nInitializing pipeline...')
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f'Pipeline ready: {len(pipeline.tajweed_engine.rules)} rules\n')

    verse_results = []
    for verse in SURAH_109['verses'] + [VERSE_1_7]:
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

    html = generate_html(SURAH_109, verse_results)
    out_dir = Path(__file__).parent / 'output'
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / 'surah_109_report.html'
    out_file.write_text(html, encoding='utf-8')

    total = sum(len(r['detected']) for r in verse_results)
    print(f'\nTotal rules detected: {total}')
    print(f'Report: {out_file}')
    print('=' * 60)


if __name__ == '__main__':
    main()
