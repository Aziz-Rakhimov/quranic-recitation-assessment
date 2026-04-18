#!/usr/bin/env python3
"""
Tajweed Analysis Report — Surah 93 (Aḍ-Ḍuḥā)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from symbolic_layer.pipeline import SymbolicLayerPipeline

sys.path.insert(0, str(Path(__file__).parent))
from systematic_validation import process_verse
from surah_97_report import generate_html, strip_waqf

# ── Surah 93 verse data ────────────────────────────────────────────
SURAH_93 = {
    'number': 93,
    'name': 'Aḍ-Ḍuḥā',
    'arabic_name': 'الضحى',
    'meaning': 'The Morning Brightness',
    'verses': [
        {
            'ayah': 1,
            'text': 'وَٱلضُّحَىٰ',
            'transliteration': 'Wa-ḍ-ḍuḥā',
            'translation': 'By the morning brightness',
        },
        {
            'ayah': 2,
            'text': 'وَٱلَّيْلِ إِذَا سَجَىٰ',
            'transliteration': 'Wa-l-layli idhā sajā',
            'translation': 'And [by] the night when it is still,',
        },
        {
            'ayah': 3,
            'text': 'مَا وَدَّعَكَ رَبُّكَ وَمَا قَلَىٰ',
            'transliteration': 'Mā waddaʿaka rabbuka wa-mā qalā',
            'translation': 'Your Lord has not taken leave of you, [O Muhammad], nor has He detested [you].',
        },
        {
            'ayah': 4,
            'text': 'وَلَلْءَاخِرَةُ خَيْرٌ لَّكَ مِنَ ٱلْأُولَىٰ',
            'transliteration': 'Wa-la-l-ākhiratu khayrun laka mina l-ūlā',
            'translation': 'And the Hereafter is better for you than the first [life].',
        },
        {
            'ayah': 5,
            'text': 'وَلَسَوْفَ يُعْطِيكَ رَبُّكَ فَتَرْضَىٰ',
            'transliteration': 'Wa-la-sawfa yuʿṭīka rabbuka fa-tarḍā',
            'translation': 'And your Lord is going to give you, and you will be satisfied.',
        },
        {
            'ayah': 6,
            'text': 'أَلَمْ يَجِدْكَ يَتِيمًا فَـَٔاوَىٰ',
            'transliteration': 'Alam yajidka yatīman fa-āwā',
            'translation': 'Did He not find you an orphan and give [you] refuge?',
        },
        {
            'ayah': 7,
            'text': 'وَوَجَدَكَ ضَآلًّا فَهَدَىٰ',
            'transliteration': 'Wa-wajadaka ḍāllan fa-hadā',
            'translation': 'And He found you lost and guided [you],',
        },
        {
            'ayah': 8,
            'text': 'وَوَجَدَكَ عَآئِلًا فَأَغْنَىٰ',
            'transliteration': 'Wa-wajadaka ʿāʾilan fa-aghnā',
            'translation': 'And He found you poor and made [you] self-sufficient.',
        },
        {
            'ayah': 9,
            'text': 'فَأَمَّا ٱلْيَتِيمَ فَلَا تَقْهَرْ',
            'transliteration': 'Fa-ammā l-yatīma fa-lā taqhar',
            'translation': 'So as for the orphan, do not oppress [him].',
        },
        {
            'ayah': 10,
            'text': 'وَأَمَّا ٱلسَّآئِلَ فَلَا تَنْهَرْ',
            'transliteration': 'Wa-ammā s-sāʾila fa-lā tanhar',
            'translation': 'And as for the petitioner, do not repel [him].',
        },
        {
            'ayah': 11,
            'text': 'وَأَمَّا بِنِعْمَةِ رَبِّكَ فَحَدِّثْ',
            'transliteration': 'Wa-ammā bi-niʿmati rabbika fa-ḥaddith',
            'translation': 'But as for the favor of your Lord, report [it].',
        },
    ],
}


def main():
    print('=' * 60)
    print('SURAH 93 (AḌ-ḌUḤĀ) — TAJWEED ANALYSIS REPORT')
    print('=' * 60)

    print('\nInitializing pipeline...')
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f'Pipeline ready: {len(pipeline.tajweed_engine.rules)} rules\n')

    verse_results = []
    for verse in SURAH_93['verses']:
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

    html = generate_html(SURAH_93, verse_results)
    out_dir = Path(__file__).parent / 'output'
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / 'surah_93_report.html'
    out_file.write_text(html, encoding='utf-8')

    total = sum(len(r['detected']) for r in verse_results)
    print(f'\nTotal rules detected: {total}')
    print(f'Report: {out_file}')
    print('=' * 60)


if __name__ == '__main__':
    main()
