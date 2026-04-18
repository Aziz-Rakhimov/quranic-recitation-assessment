#!/usr/bin/env python3
"""
Complete Verse Validation Script

Tests the system on complete Qur'anic verses (not fragments) to validate
that it detects all expected Tajwīd rules in realistic contexts.

This approach is closer to actual usage and shows how rules interact.
"""

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline

# Rules to EXCLUDE from validation (internal phonetic rules, not assessable Tajwīd)
EXCLUDED_RULES = {
    'emphasis_blocking_by_front_vowel',
    'vowel_backing_after_emphatic_short',
    'vowel_backing_after_emphatic_long',
    'vowel_backing_before_emphatic_short',
    'vowel_backing_before_emphatic_long',
    'cross_word_emphasis_continuation',
}

# Complete verses with manual rule annotations
COMPLETE_VERSES = [
    {
        'name': 'Al-Fātiḥah 1:1 - Basmala',
        'surah': 1,
        'ayah': 1,
        'text': 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ',
        'transliteration': 'Bismillāhi r-raḥmāni r-raḥīm',
        'translation': 'In the name of Allah, the Most Gracious, the Most Merciful',
        'expected_rules': [
            'madd_tabii',  # Multiple natural long vowels (ii, aa)
            'madd_arid_lissukun',  # ٱلرَّحِيمِ - long ii before final meem at verse end
        ],
        'notes': 'The opening verse - tests madd ṭabīʿī and madd ʿāriḍ. No noon/meem with shaddah in Basmala.'
    },
    {
        'name': 'Al-Fātiḥah 1:5',
        'surah': 1,
        'ayah': 5,
        'text': 'إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ',
        'transliteration': 'Iyyāka na\'budu wa-iyyāka nasta\'īn',
        'translation': 'You alone we worship, and You alone we ask for help',
        'expected_rules': [
            'madd_tabii',  # Long ii in إِيَّاكَ
            'madd_arid_lissukun',  # نَسْتَعِينُ at verse end with long ii
        ],
        'notes': 'Tests madd ʿāriḍ at verse end. No noon with shaddah — يَّا is yaa shaddah, not ghunnah mushaddadah noon.'
    },
    {
        'name': 'Al-Fātiḥah 1:7',
        'surah': 1,
        'ayah': 7,
        'text': 'صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ',
        'transliteration': 'Ṣirāṭa l-ladhīna an\'amta \'alayhim ghayri l-maghḍūbi \'alayhim wa-lā ḍ-ḍāllīn',
        'translation': 'The path of those You have blessed, not of those who earned anger, nor of those who went astray',
        'expected_rules': [
            'madd_tabii',  # Multiple occurrences
            'madd_lazim_kalimi',  # ٱلضَّآلِّينَ - long aa before doubled laam (6 counts)
            'idhhar_halqi_noon',  # أَنْعَمْتَ - noon before ain
            'idhhar_shafawi',  # عَلَيْهِمْ غَيْرِ - meem before ghayn, عَلَيْهِمْ وَ - meem before waw
            'madd_arid_lissukun',  # ٱلضَّآلِّينَ at verse end
        ],
        'notes': 'Long verse with diverse rules - tests iẓhār, madd lāzim, and verse-end madd'
    },
    {
        'name': 'Al-Kawthar 108:1',
        'surah': 108,
        'ayah': 1,
        'text': 'إِنَّآ أَعْطَيْنَٰكَ ٱلْكَوْثَرَ',
        'transliteration': 'Innā a\'ṭaynāka l-kawthar',
        'translation': 'Indeed, We have granted you abundant goodness',
        'expected_rules': [
            'ghunnah_mushaddadah_noon',  # إِنَّ - noon with shaddah
            'madd_munfasil',  # إِنَّآ أَعْطَيْنَٰكَ - long aː at end of إِنَّآ, hamza starts next word
            'madd_tabii',  # Multiple natural long vowels
        ],
        'notes': 'Tests ghunnah mushaddadah and madd munfaṣil. No madd ʿāriḍ: ٱلْكَوْثَرَ ends in short vowel (ra+a), no long vowel before verse end.'
    },
    {
        'name': 'Al-Baqarah 2:2',
        'surah': 2,
        'ayah': 2,
        'text': 'ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبً ۛ فِيهِ ۛ هُدًى لِّلْمُتَّقِينَ',
        'transliteration': 'Dhālika l-kitābu lā rayba fīhi hudan li-l-muttaqīn',
        'translation': 'This is the Book about which there is no doubt, guidance for the righteous',
        'expected_rules': [
            'madd_tabii',  # Multiple occurrences
            'ikhfaa_light',  # رَيْبً فِيهِ - tanween before faa
            'idgham_no_ghunnah',  # هُدًى لِّ - tanween before laam with idghām
            'madd_arid_lissukun',  # ٱلْمُتَّقِينَ at verse end
        ],
        'notes': 'Tests ikhfāʾ and idghām with tanween - important noon/meem rules'
    },
    {
        'name': 'Al-Falaq 113:1-2',
        'surah': 113,
        'ayah': 1,
        'text': 'قُلْ أَعُوذُ بِرَبِّ ٱلْفَلَقِ مِن شَرِّ مَا خَلَقَ',
        'transliteration': 'Qul a\'ūdhu bi-rabbi l-falaqi min sharri mā khalaq',
        'translation': 'Say: I seek refuge with the Lord of daybreak from the evil of what He created',
        'expected_rules': [
            'madd_tabii',  # Long uu in أَعُوذُ
            'qalqalah_major',  # خَلَقَ at verse end → خَلَقْ (qaaf gets waqf sukoon)
            'qalqalah_emphatic',  # verse-end qaaf (ق) is emphatic + has sukoon in waqf
            'ikhfaa_light',  # مِن شَرِّ - noon before shiin
            'qalqalah_with_shaddah',  # رَبِّ - baa with shaddah (qalqalah letter + geminated)
        ],
        'notes': 'Tests qalqalah and ikhfāʾ. qalqalah_major fires on verse-final qaaf (خَلَقَ→خَلَقْ in waqf). Qaaf is also emphatic.'
    },
    {
        'name': 'Al-Ikhlāṣ 112:1-2',
        'surah': 112,
        'ayah': 1,
        'text': 'قُلْ هُوَ ٱللَّهُ أَحَدٌ ٱللَّهُ ٱلصَّمَدُ',
        'transliteration': 'Qul huwa llāhu aḥad, Allāhu ṣ-ṣamad',
        'translation': 'Say: He is Allah, the One. Allah, the Eternal Refuge',
        'expected_rules': [
            'madd_tabii',  # هُوَ - long uu
            'qalqalah_major',  # ٱلصَّمَدُ at verse end → ٱلصَّمَدْ (daal gets waqf sukoon)
            'idgham_no_ghunnah',  # أَحَدٌ ٱللَّهُ - tanween noon before laam → idghām without ghunnah
        ],
        'notes': 'Tests qalqalah_major (waqf daal) and idgham. No ghunnah_mushaddadah (tanween≠shaddah), no madd_arid (ٱلصَّمَدُ ends in short u, no long vowel before verse end).'
    },
    {
        'name': 'Al-Baqarah 2:255 (Ayat al-Kursi - fragment)',
        'surah': 2,
        'ayah': 255,
        'text': 'ٱللَّهُ لَآ إِلَٰهَ إِلَّا هُوَ ٱلْحَىُّ ٱلْقَيُّومُ',
        'transliteration': 'Allāhu lā ilāha illā huwa l-ḥayyu l-qayyūm',
        'translation': 'Allah - there is no deity except Him, the Ever-Living, the Sustainer',
        'expected_rules': [
            'madd_tabii',  # Multiple
            'madd_munfasil',  # لَآ إِلَٰهَ - long aa at end of word, next word starts with hamza
            'madd_arid_lissukun',  # ٱلْقَيُّومُ - long uu at verse end (pausal prolongation)
        ],
        'notes': 'Ayat al-Kursi fragment - tests madd munfaṣil. No ghunnah_mushaddadah_meem (no meem shaddah). No idgham_no_ghunnah (إِلَّا is lexical gemination, not tajweed idghām).'
    },
]


def validate_complete_verses():
    """Main validation function for complete verses."""
    print("=" * 80)
    print("COMPLETE VERSE VALIDATION")
    print("=" * 80)
    print(f"\nValidating system performance on {len(COMPLETE_VERSES)} complete Qur'anic verses")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Initialize pipeline
    print("Initializing pipeline...")
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f"✅ Pipeline ready with {len(pipeline.tajweed_engine.rules)} rules loaded\n")

    # Process each verse
    results = []

    for i, verse_data in enumerate(COMPLETE_VERSES, 1):
        print(f"\n{'=' * 80}")
        print(f"Verse {i}/{len(COMPLETE_VERSES)}: {verse_data['name']}")
        print(f"{'=' * 80}")
        print(f"Arabic: {verse_data['text']}")
        print(f"Translation: {verse_data['translation']}")
        print(f"\nExpected rules ({len(verse_data['expected_rules'])}): {', '.join(verse_data['expected_rules'])}")

        try:
            # Process verse
            output = pipeline.process_text(verse_data['text'])

            # Extract detected rules
            detected_rules = []
            rule_applications = []
            for app in output.annotated_sequence.rule_applications:
                rule_name = app.rule.name
                # Skip excluded rules (internal phonetic rules, not assessable Tajwīd)
                if rule_name in EXCLUDED_RULES:
                    continue
                if rule_name not in detected_rules:
                    detected_rules.append(rule_name)
                rule_applications.append({
                    'name': rule_name,
                    'position': f"{app.start_index}-{app.end_index}",
                    'original': [p.symbol for p in app.original_phonemes],
                    'modified': [p.symbol for p in app.modified_phonemes],
                })

            print(f"Detected rules ({len(detected_rules)} - core Tajwīd only): {', '.join(detected_rules)}")

            # Compare expected vs detected
            expected_set = set(verse_data['expected_rules'])
            detected_set = set(detected_rules)

            correct = expected_set & detected_set  # Rules that were expected AND detected
            missed = expected_set - detected_set   # Rules that were expected but NOT detected
            false_positive = detected_set - expected_set  # Rules detected but NOT expected

            print(f"\n✅ Correct: {len(correct)}/{len(expected_set)}")
            if correct:
                print(f"   {', '.join(correct)}")

            if missed:
                print(f"\n❌ Missed ({len(missed)}): {', '.join(missed)}")

            if false_positive:
                print(f"\n⚠️  False Positives ({len(false_positive)}): {', '.join(false_positive)}")

            # Calculate score
            if len(expected_set) > 0:
                precision = len(correct) / len(detected_set) if len(detected_set) > 0 else 0
                recall = len(correct) / len(expected_set)
                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            else:
                precision = recall = f1_score = 0

            print(f"\nMetrics:")
            print(f"  Precision: {precision:.1%} ({len(correct)}/{len(detected_set)})")
            print(f"  Recall: {recall:.1%} ({len(correct)}/{len(expected_set)})")
            print(f"  F1 Score: {f1_score:.1%}")

            # Store results
            results.append({
                'verse_data': verse_data,
                'phonemes': [p.symbol for p in output.phoneme_sequence.phonemes],
                'expected_rules': verse_data['expected_rules'],
                'detected_rules': detected_rules,
                'rule_applications': rule_applications,
                'correct': list(correct),
                'missed': list(missed),
                'false_positive': list(false_positive),
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score,
            })

        except Exception as e:
            print(f"⚠️  ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'verse_data': verse_data,
                'error': str(e),
                'expected_rules': verse_data['expected_rules'],
                'detected_rules': [],
                'correct': [],
                'missed': verse_data['expected_rules'],
                'false_positive': [],
                'precision': 0,
                'recall': 0,
                'f1_score': 0,
            })

    # Generate HTML report
    print(f"\n{'=' * 80}")
    print("GENERATING HTML REPORT")
    print(f"{'=' * 80}")

    html_content = generate_html_report(results)

    # Save HTML
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'verse_validation_report_core_rules.html'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✅ HTML Report Generated!")
    print(f"📄 Location: {output_file}")
    print(f"🌐 Open in browser to view")
    print(f"{'=' * 80}\n")

    # Summary statistics
    total_correct = sum(len(r['correct']) for r in results)
    total_expected = sum(len(r['expected_rules']) for r in results)
    total_detected = sum(len(r['detected_rules']) for r in results)
    total_missed = sum(len(r['missed']) for r in results)
    total_fp = sum(len(r['false_positive']) for r in results)

    avg_precision = sum(r['precision'] for r in results) / len(results)
    avg_recall = sum(r['recall'] for r in results) / len(results)
    avg_f1 = sum(r['f1_score'] for r in results) / len(results)

    print("OVERALL STATISTICS")
    print("=" * 80)
    print(f"Total verses tested: {len(COMPLETE_VERSES)}")
    print(f"Total expected rules: {total_expected}")
    print(f"Total detected rules: {total_detected}")
    print(f"Correct detections: {total_correct}")
    print(f"Missed rules: {total_missed}")
    print(f"False positives: {total_fp}")
    print(f"\nAverage Precision: {avg_precision:.1%}")
    print(f"Average Recall: {avg_recall:.1%}")
    print(f"Average F1 Score: {avg_f1:.1%}")
    print("=" * 80)

    return results


def generate_html_report(results):
    """Generate HTML report for verse validation."""

    # Calculate overall stats
    total_correct = sum(len(r['correct']) for r in results)
    total_expected = sum(len(r['expected_rules']) for r in results)
    total_detected = sum(len(r['detected_rules']) for r in results)
    avg_precision = sum(r['precision'] for r in results) / len(results) if results else 0
    avg_recall = sum(r['recall'] for r in results) / len(results) if results else 0
    avg_f1 = sum(r['f1_score'] for r in results) / len(results) if results else 0

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Complete Verse Validation Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            background: #f5f7fa;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 2px 20px rgba(0,0,0,0.08);
            border-radius: 12px;
            overflow: hidden;
        }}

        .arabic {{
            font-family: 'Amiri', serif;
            font-size: 28px;
            line-height: 2.2;
            direction: rtl;
            text-align: right;
            color: #2c3e50;
            font-weight: 400;
        }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }}

        .header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}

        /* Stats */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}

        .stat-card {{
            background: white;
            padding: 24px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}

        .stat-value {{
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .stat-value.correct {{ color: #10b981; }}
        .stat-value.missed {{ color: #ef4444; }}
        .stat-value.precision {{ color: #3b82f6; }}

        .stat-label {{
            font-size: 14px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* Verse Cards */
        .content {{
            padding: 40px;
        }}

        .verse-card {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            margin-bottom: 30px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }}

        .verse-header {{
            background: #fafbfc;
            padding: 20px 30px;
            border-bottom: 1px solid #e5e7eb;
        }}

        .verse-title {{
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 5px;
        }}

        .verse-body {{
            padding: 30px;
        }}

        .verse-text {{
            background: #fafbfc;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 25px;
        }}

        .translation {{
            font-size: 15px;
            color: #4b5563;
            font-style: italic;
            margin-top: 12px;
        }}

        /* Rules Section */
        .rules-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 25px 0;
        }}

        .rules-box {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
        }}

        .rules-box-title {{
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }}

        .rule-tag {{
            display: inline-block;
            padding: 6px 12px;
            margin: 4px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
        }}

        .rule-correct {{
            background: #d1fae5;
            color: #065f46;
        }}

        .rule-missed {{
            background: #fee2e2;
            color: #991b1b;
        }}

        .rule-false-positive {{
            background: #fef3c7;
            color: #92400e;
        }}

        .rule-expected {{
            background: #e0e7ff;
            color: #3730a3;
        }}

        .rule-detected {{
            background: #dbeafe;
            color: #1e40af;
        }}

        /* Metrics */
        .metrics {{
            display: flex;
            gap: 20px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }}

        .metric {{
            flex: 1;
            text-align: center;
            padding: 15px;
            background: #f9fafb;
            border-radius: 8px;
        }}

        .metric-value {{
            font-size: 24px;
            font-weight: 700;
            color: #667eea;
        }}

        .metric-label {{
            font-size: 12px;
            color: #6b7280;
            margin-top: 4px;
        }}

        /* Applications */
        .applications {{
            margin-top: 20px;
        }}

        .app-item {{
            background: #ecfdf5;
            border-left: 3px solid #10b981;
            padding: 12px 15px;
            margin-bottom: 10px;
            border-radius: 6px;
            font-size: 13px;
        }}

        .app-name {{
            font-weight: 600;
            color: #065f46;
        }}

        .app-phonemes {{
            font-family: 'Courier New', monospace;
            color: #047857;
            margin-top: 4px;
        }}

        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; }}
            .verse-card {{ page-break-inside: avoid; }}
        }}

        @media (max-width: 768px) {{
            .rules-comparison {{ grid-template-columns: 1fr; }}
            .stats-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Complete Verse Validation Report</h1>
            <div class="subtitle">System Performance on Complete Qur'anic Verses (24 Core Assessable Tajwīd Rules)</div>
            <div style="margin-top: 15px; font-size: 14px;">
                Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}
            </div>
            <div style="margin-top: 10px; font-size: 13px; opacity: 0.9;">
                Note: Excludes internal phonetic rules (emphasis/vowel backing)
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value correct">{total_correct}</div>
                <div class="stat-label">Correct Detections</div>
            </div>
            <div class="stat-card">
                <div class="stat-value missed">{total_expected - total_correct}</div>
                <div class="stat-label">Missed Rules</div>
            </div>
            <div class="stat-card">
                <div class="stat-value precision">{avg_precision:.0%}</div>
                <div class="stat-label">Avg Precision</div>
            </div>
            <div class="stat-card">
                <div class="stat-value precision">{avg_recall:.0%}</div>
                <div class="stat-label">Avg Recall</div>
            </div>
            <div class="stat-card">
                <div class="stat-value precision">{avg_f1:.0%}</div>
                <div class="stat-label">Avg F1 Score</div>
            </div>
        </div>

        <div class="content">
'''

    # Add each verse
    for i, result in enumerate(results, 1):
        verse = result['verse_data']
        correct = result['correct']
        missed = result['missed']
        fp = result['false_positive']

        html += f'''
            <div class="verse-card">
                <div class="verse-header">
                    <div class="verse-title">Verse {i}: {verse['name']}</div>
                </div>
                <div class="verse-body">
                    <div class="verse-text">
                        <div class="arabic">{verse['text']}</div>
                        <div class="translation">{verse['translation']}</div>
                    </div>

                    <div class="rules-comparison">
                        <div class="rules-box">
                            <div class="rules-box-title">Expected Rules ({len(result['expected_rules'])})</div>
'''

        for rule in result['expected_rules']:
            tag_class = 'rule-correct' if rule in correct else 'rule-missed'
            icon = '✓' if rule in correct else '✗'
            html += f'                            <span class="rule-tag {tag_class}">{icon} {rule.replace("_", " ").title()}</span>\n'

        html += '''
                        </div>
                        <div class="rules-box">
                            <div class="rules-box-title">Detected Rules (''' + str(len(result['detected_rules'])) + ''')</div>
'''

        for rule in result['detected_rules']:
            tag_class = 'rule-correct' if rule in correct else 'rule-false-positive'
            icon = '✓' if rule in correct else '⚠'
            html += f'                            <span class="rule-tag {tag_class}">{icon} {rule.replace("_", " ").title()}</span>\n'

        html += f'''
                        </div>
                    </div>

                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value">{result['precision']:.0%}</div>
                            <div class="metric-label">Precision</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{result['recall']:.0%}</div>
                            <div class="metric-label">Recall</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{result['f1_score']:.0%}</div>
                            <div class="metric-label">F1 Score</div>
                        </div>
                    </div>
'''

        # Show rule applications
        if 'rule_applications' in result and result['rule_applications']:
            html += '''
                    <div class="applications">
                        <div class="rules-box-title">Rule Applications Detected</div>
'''
            for app in result['rule_applications'][:10]:  # Limit to first 10
                orig = ' '.join(app['original'])
                mod = ' '.join(app['modified'])
                html += f'''
                        <div class="app-item">
                            <span class="app-name">{app['name']}</span> at position {app['position']}<br>
                            <span class="app-phonemes">[{orig}] → [{mod}]</span>
                        </div>
'''
            html += '                    </div>\n'

        html += '''
                </div>
            </div>
'''

    html += '''
        </div>
    </div>
</body>
</html>
'''

    return html


if __name__ == "__main__":
    validate_complete_verses()
