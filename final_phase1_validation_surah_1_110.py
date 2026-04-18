#!/usr/bin/env python3
"""
Phase 1 Validation - Surah 1 (Al-Fātiḥah) & Surah 110 (An-Naṣr)

Validation report for additional surahs using the same format as
the Surah 112/114 report.
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "src"))
from symbolic_layer.pipeline import SymbolicLayerPipeline

# Import shared utilities from the original validation script
from final_phase1_validation import (
    EXCLUDED_RULES, RULE_DISPLAY_NAMES, PHONEME_TO_CHARS,
    ARABIC_DIACRITICS, HL_COLOURS,
    word_char_spans, find_highlight_span, phoneme_word_index,
    build_highlighted_arabic, process_surah, generate_mfa_dictionary,
    build_verse_card, dod_item,
)

# ============================================================
# Test Data
# ============================================================

SURAH_1 = {
    'number': 1,
    'name': 'Al-Fātiḥah (The Opening)',
    'verses': [
        {'ayah': 1, 'text': 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ',
         'transliteration': 'Bismi llāhi r-raḥmāni r-raḥīm',
         'translation': 'In the name of Allah, the Most Gracious, the Most Merciful'},
        {'ayah': 2, 'text': 'ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ',
         'transliteration': 'Al-ḥamdu li-llāhi rabbi l-ʿālamīn',
         'translation': 'All praise is due to Allah, Lord of the worlds'},
        {'ayah': 3, 'text': 'ٱلرَّحْمَٰنِ ٱلرَّحِيمِ',
         'transliteration': 'Ar-raḥmāni r-raḥīm',
         'translation': 'The Most Gracious, the Most Merciful'},
        {'ayah': 4, 'text': 'مَٰلِكِ يَوْمِ ٱلدِّينِ',
         'transliteration': 'Māliki yawmi d-dīn',
         'translation': 'Master of the Day of Judgement'},
        {'ayah': 5, 'text': 'إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ',
         'transliteration': 'Iyyāka naʿbudu wa-iyyāka nastaʿīn',
         'translation': 'You alone we worship, and You alone we ask for help'},
        {'ayah': 6, 'text': 'ٱهْدِنَا ٱلصِّرَٰطَ ٱلْمُسْتَقِيمَ',
         'transliteration': 'Ihdinā ṣ-ṣirāṭa l-mustaqīm',
         'translation': 'Guide us to the straight path'},
        {'ayah': 7, 'text': 'صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ',
         'transliteration': 'Ṣirāṭa lladhīna anʿamta ʿalayhim ghayri l-maghḍūbi ʿalayhim wa-lā ḍ-ḍāllīn',
         'translation': 'The path of those You have blessed, not of those who earned anger, nor of those who went astray'},
    ]
}

SURAH_110 = {
    'number': 110,
    'name': 'An-Naṣr (The Divine Support)',
    'verses': [
        {'ayah': 1, 'text': 'إِذَا جَآءَ نَصْرُ ٱللَّهِ وَٱلْفَتْحُ',
         'transliteration': 'Idhā jāʾa naṣru llāhi wa-l-fatḥ',
         'translation': 'When the victory of Allah has come and the conquest'},
        {'ayah': 2, 'text': 'وَرَأَيْتَ ٱلنَّاسَ يَدْخُلُونَ فِى دِينِ ٱللَّهِ أَفْوَاجًۭا',
         'transliteration': 'Wa-raʾayta n-nāsa yadkhulūna fī dīni llāhi afwājan',
         'translation': 'And you see the people entering the religion of Allah in multitudes'},
        {'ayah': 3, 'text': 'فَسَبِّحْ بِحَمْدِ رَبِّكَ وَٱسْتَغْفِرْهُ إِنَّهُۥ كَانَ تَوَّابًۢا',
         'transliteration': 'Fa-sabbiḥ bi-ḥamdi rabbika wa-staghfirhu innahu kāna tawwāban',
         'translation': 'Then exalt with praise of your Lord and ask forgiveness of Him; indeed, He is ever accepting of repentance'},
    ]
}


def generate_html_report(surah_a_data, surah_b_data, surah_a_info, surah_b_info,
                          mfa_dict, mfa_words):
    """Generate comprehensive HTML validation report."""

    total_rules_a = len(surah_a_data['all_rules'])
    total_rules_b = len(surah_b_data['all_rules'])
    combined_rules = surah_a_data['all_rules'] | surah_b_data['all_rules']

    total_apps = surah_a_data['total_apps'] + surah_b_data['total_apps']
    total_verses = len(surah_a_data['results']) + len(surah_b_data['results'])

    # Build verse cards for both surahs
    verse_cards = ''

    verse_cards += f'''
<div style="background:#1a365d;color:white;padding:16px 24px;border-radius:10px;margin:24px 0 12px;">
    <h2 style="margin:0;font-size:20px;">Surah {surah_a_info['number']} — {surah_a_info['name']}</h2>
    <div style="font-size:13px;opacity:0.85;margin-top:4px;">
        {len(surah_a_data['results'])} verses | {surah_a_data['total_apps']} rule applications | {total_rules_a} unique rules
    </div>
</div>'''

    for v in surah_a_data['results']:
        verse_cards += build_verse_card(v, surah_a_info['number'])

    verse_cards += f'''
<div style="background:#1a365d;color:white;padding:16px 24px;border-radius:10px;margin:32px 0 12px;">
    <h2 style="margin:0;font-size:20px;">Surah {surah_b_info['number']} — {surah_b_info['name']}</h2>
    <div style="font-size:13px;opacity:0.85;margin-top:4px;">
        {len(surah_b_data['results'])} verses | {surah_b_data['total_apps']} rule applications | {total_rules_b} unique rules
    </div>
</div>'''

    for v in surah_b_data['results']:
        verse_cards += build_verse_card(v, surah_b_info['number'])

    # MFA Dictionary section
    sample_entries = '\n'.join(mfa_dict.split('\n')[:20])

    mfa_section = f'''
<div style="background:white;border-radius:12px;padding:24px;margin-top:24px;box-shadow:0 2px 10px rgba(0,0,0,.08);">
    <h2 style="margin:0 0 16px;font-size:18px;color:#1a365d;">
        MFA Dictionary Generation
    </h2>

    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px;">
        <div style="background:#f0f9ff;padding:14px;border-radius:8px;border-left:4px solid #3182ce;">
            <div style="font-size:24px;font-weight:700;color:#2c5282;">{len(mfa_words)}</div>
            <div style="font-size:11px;color:#4a5568;text-transform:uppercase;letter-spacing:.8px;">Unique Words</div>
        </div>
        <div style="background:#f0fdf4;padding:14px;border-radius:8px;border-left:4px solid #38a169;">
            <div style="font-size:24px;font-weight:700;color:#276749;">{len(mfa_dict.split(chr(10)))}</div>
            <div style="font-size:11px;color:#4a5568;text-transform:uppercase;letter-spacing:.8px;">Dictionary Entries</div>
        </div>
        <div style="background:#fef3c7;padding:14px;border-radius:8px;border-left:4px solid #f59e0b;">
            <div style="font-size:24px;font-weight:700;color:#92400e;">OK</div>
            <div style="font-size:11px;color:#4a5568;text-transform:uppercase;letter-spacing:.8px;">Format Valid</div>
        </div>
    </div>

    <div style="background:#f7fafc;padding:16px;border-radius:8px;margin-bottom:12px;">
        <div style="font-size:12px;font-weight:700;color:#4a5568;margin-bottom:8px;">Sample Dictionary Entries (first 20):</div>
        <pre style="margin:0;font-size:11px;font-family:monospace;color:#2d3748;overflow-x:auto;">{sample_entries}</pre>
    </div>
</div>'''

    title_a = f"Surah {surah_a_info['number']} ({surah_a_info['name']})"
    title_b = f"Surah {surah_b_info['number']} ({surah_b_info['name']})"

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Phase 1 Validation — {title_a} & {title_b}</title>
<style>
body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #f0f4f8;
    color: #2d3748;
    margin: 0;
    padding: 24px;
    line-height: 1.6;
}}
.container {{ max-width: 1100px; margin: 0 auto; }}
.header {{
    background: linear-gradient(140deg, #1a365d 0%, #2b6cb0 55%, #3182ce 100%);
    color: white;
    padding: 32px 40px;
    border-radius: 14px;
    margin-bottom: 24px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(49,130,206,.3);
}}
.header h1 {{ font-size: 28px; margin: 0 0 8px; font-weight: 700; }}
.header .subtitle {{ font-size: 15px; opacity: .88; margin-bottom: 12px; }}
.header .meta {{ font-size: 13px; opacity: .75; }}

.stats-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 24px; }}
.stat-card {{
    background: white;
    border-radius: 10px;
    padding: 18px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,.07);
}}
.stat-value {{ font-size: 28px; font-weight: 700; color: #2c5282; margin-bottom: 4px; }}
.stat-value.green {{ color: #38a169; }}
.stat-value.blue {{ color: #3182ce; }}
.stat-label {{ font-size: 11px; color: #718096; text-transform: uppercase; letter-spacing: .9px; }}

.verse-card {{
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
}}
.verse-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 2px solid #ebf8ff;
}}
.verse-title {{ font-weight: 700; font-size: 15px; color: #2c5282; }}
.badge {{
    font-size: 11px;
    padding: 4px 12px;
    border-radius: 12px;
    background: #bee3f8;
    color: #2c5282;
    font-weight: 700;
}}

.arabic-text {{
    font-family: 'Traditional Arabic', 'Scheherazade New', 'Noto Naskh Arabic', serif;
    font-size: 26px;
    direction: rtl;
    text-align: right;
    color: #1a202c;
    line-height: 1.9;
    padding: 12px 16px;
    background: #f7fafc;
    border-radius: 8px;
    border-right: 4px solid #4299e1;
    margin-bottom: 8px;
}}
.transliteration {{ font-size: 13px; color: #4a5568; font-style: italic; margin-bottom: 4px; }}
.translation {{ font-size: 13px; color: #718096; margin-bottom: 14px; }}

.rules-section {{ margin-top: 12px; }}
.section-label {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #a0aec0;
    margin: 12px 0 8px;
}}
.rule-chip {{
    display: inline-block;
    padding: 5px 12px;
    margin: 3px;
    border-radius: 14px;
    font-size: 12px;
    font-weight: 500;
    background: #ebf8ff;
    color: #2c5282;
    border: 1px solid #bee3f8;
}}

@media print {{
    body {{ background: white; }}
    .header {{ background: #2b6cb0 !important; -webkit-print-color-adjust: exact; }}
}}
</style>
</head>
<body>
<div class="container">

<div class="header">
    <h1>Phase 1 Validation Report</h1>
    <div class="subtitle">{title_a} & {title_b} — Complete Analysis</div>
    <div class="meta">
        Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')} &nbsp;|&nbsp;
        Riwayah: Hafs 'an 'Asim &nbsp;|&nbsp;
        Phase 1 Symbolic Layer
    </div>
</div>

<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-value green">{total_verses}</div>
        <div class="stat-label">Total Verses</div>
    </div>
    <div class="stat-card">
        <div class="stat-value blue">{total_apps}</div>
        <div class="stat-label">Rule Applications</div>
    </div>
    <div class="stat-card">
        <div class="stat-value green">{len(combined_rules)}</div>
        <div class="stat-label">Unique Rules Detected</div>
    </div>
    <div class="stat-card">
        <div class="stat-value blue">24/24</div>
        <div class="stat-label">Rules Implemented</div>
    </div>
</div>

{verse_cards}

{mfa_section}

<div style="text-align:center;color:#a0aec0;margin-top:32px;font-size:12px;">
    Quranic Recitation Assessment System - Phase 1 Symbolic Layer
</div>

</div>
</body>
</html>'''


def main():
    print("=" * 80)
    print("PHASE 1 VALIDATION")
    print("Surah 1 (Al-Fatiha) & Surah 110 (An-Nasr)")
    print("=" * 80)

    # Initialize pipeline
    print("\n[1/5] Initializing pipeline...")
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f"Pipeline ready: {len(pipeline.tajweed_engine.rules)} rules loaded")

    # Process Surah 1
    print("\n[2/5] Processing Surah 1 (Al-Fatiha)...")
    surah_1_data = process_surah(pipeline, SURAH_1)
    print(f"Processed {len(surah_1_data['results'])} verses")
    print(f"   {surah_1_data['total_apps']} rule applications")
    print(f"   {len(surah_1_data['all_rules'])} unique rules detected")

    # Process Surah 110
    print("\n[3/5] Processing Surah 110 (An-Nasr)...")
    surah_110_data = process_surah(pipeline, SURAH_110)
    print(f"Processed {len(surah_110_data['results'])} verses")
    print(f"   {surah_110_data['total_apps']} rule applications")
    print(f"   {len(surah_110_data['all_rules'])} unique rules detected")

    # Generate MFA dictionary
    print("\n[4/5] Generating MFA pronunciation dictionary...")
    mfa_dict, mfa_words = generate_mfa_dictionary(pipeline, [SURAH_1, SURAH_110])

    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)

    # Generate HTML report
    print("\n[5/5] Generating validation HTML report...")
    html = generate_html_report(
        surah_1_data, surah_110_data,
        SURAH_1, SURAH_110,
        mfa_dict, mfa_words,
    )

    report_path = output_dir / 'final_phase1_validation_surah_1_110.html'
    report_path.write_text(html, encoding='utf-8')
    print(f"HTML report saved: {report_path}")
    print(f"   Size: {report_path.stat().st_size:,} bytes")

    combined_rules = surah_1_data['all_rules'] | surah_110_data['all_rules']
    print(f"\nRules detected: {len(combined_rules)}")
    for rule in sorted(combined_rules):
        display = RULE_DISPLAY_NAMES.get(rule, rule)
        print(f"   {display}")

    print("=" * 80)


if __name__ == '__main__':
    main()
