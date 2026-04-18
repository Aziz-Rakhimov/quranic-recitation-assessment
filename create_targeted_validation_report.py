#!/usr/bin/env python3
"""
Create a targeted validation report that tests ALL Tajweed rule types.

This script specifically selects verses to ensure coverage of:
- Noon/Meem Sakinah rules (idhhar, idgham, iqlab, ikhfaa)
- Madd rules (tabii, muttasil, munfasil)
- Qalqalah rules
- Raa rules (tafkheem, tarqeeq)
- Emphasis rules
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline


def find_verses_by_pattern(quran_data, target_rules):
    """
    Find verses that are likely to contain specific Tajweed patterns.

    Returns a dict mapping rule types to list of (surah, ayah, text) tuples.
    """
    verse_candidates = defaultdict(list)

    # Search through all surahs
    for surah in quran_data['surahs'][:114]:  # All surahs
        surah_num = surah['number']
        for i, ayah in enumerate(surah['ayahs']):
            ayah_num = i + 1
            text = ayah['text'].replace('\ufeff', '')

            # Split into words for cross-word pattern matching
            words = text.split()

            # Check for idhhar (noon sakinah before throat letters: ء ه ع ح غ خ)
            if 'نْع' in text or 'نْ ع' in text or 'نْه' in text or 'نْ ه' in text:
                verse_candidates['idhhar'].append((surah_num, ayah_num, text))

            # Check for idgham (noon sakinah before ي و ن م)
            for word_idx in range(len(words) - 1):
                if 'نْ' in words[word_idx]:
                    next_first = words[word_idx + 1][0] if words[word_idx + 1] else ''
                    if next_first in 'يونم':
                        verse_candidates['idgham'].append((surah_num, ayah_num, text))
                        break

            # Check for iqlab (noon sakinah before ب)
            for word_idx in range(len(words) - 1):
                if 'نْ' in words[word_idx]:
                    next_word = words[word_idx + 1]
                    # Get first non-diacritic letter
                    for char in next_word:
                        if char not in 'ًٌٍَُِّْ\u0670':
                            if char == 'ب':
                                verse_candidates['iqlab'].append((surah_num, ayah_num, text))
                            break
                    if (surah_num, ayah_num, text) in verse_candidates['iqlab']:
                        break

            # Check for ikhfaa (noon sakinah before 15 letters: ت ث ج د ذ ز س ش ص ض ط ظ ف ق ك)
            for word_idx in range(len(words) - 1):
                if 'نْ' in words[word_idx]:
                    next_word = words[word_idx + 1]
                    # Get first non-diacritic letter
                    for char in next_word:
                        if char not in 'ًٌٍَُِّْ\u0670':
                            if char in 'تثجدذزسشصضطظفقك':
                                verse_candidates['ikhfaa'].append((surah_num, ayah_num, text))
                            break
                    if (surah_num, ayah_num, text) in verse_candidates['ikhfaa']:
                        break

            # Check for madd muttasil (long vowel + hamza same word)
            if 'آء' in text or ('َا' in text and 'ء' in text):
                # More sophisticated check for same word
                for word in words:
                    if ('آء' in word) or (('َا' in word or 'ِي' in word or 'ُو' in word) and 'ء' in word):
                        verse_candidates['madd_muttasil'].append((surah_num, ayah_num, text))
                        break

            # Check for madd munfasil (long vowel end of word, hamza start of next)
            for word_idx in range(len(words) - 1):
                current = words[word_idx]
                next_word = words[word_idx + 1]
                if (('َا' in current or 'ِي' in current or 'ُو' in current) and
                    any(c == 'ء' or c == 'أ' or c == 'إ' for c in next_word)):
                    verse_candidates['madd_munfasil'].append((surah_num, ayah_num, text))
                    break

            # Check for qalqalah (ق ط ب ج د with sukoon)
            if any(c in text for c in ['قْ', 'طْ', 'بْ', 'جْ', 'دْ']):
                verse_candidates['qalqalah'].append((surah_num, ayah_num, text))

            # Check for raa tafkheem (heavy)
            if 'رَ' in text or 'رُ' in text or 'رْ' in text:
                verse_candidates['raa_heavy'].append((surah_num, ayah_num, text))

            # Check for raa tarqeeq (light)
            if 'رِ' in text:
                verse_candidates['raa_light'].append((surah_num, ayah_num, text))

            # Check for emphatic letters
            if any(c in text for c in ['ص', 'ض', 'ط', 'ظ', 'ق']):
                verse_candidates['emphatic'].append((surah_num, ayah_num, text))

    return verse_candidates


def select_test_verses(verse_candidates, target_count_per_type=2):
    """
    Select a balanced set of test verses covering all rule types.
    """
    selected = []
    used_verses = set()

    # Ensure we get at least target_count verses for each rule type
    for rule_type, candidates in verse_candidates.items():
        count = 0
        for surah, ayah, text in candidates:
            if (surah, ayah) not in used_verses and count < target_count_per_type:
                selected.append({
                    'surah': surah,
                    'ayah': ayah,
                    'text': text,
                    'expected_rule_type': rule_type
                })
                used_verses.add((surah, ayah))
                count += 1

    return selected


def extract_rule_context(text, rule_app, annotated_seq):
    """
    Extract the Arabic text snippet where a rule applies.

    This helps show the expert EXACTLY where the rule was detected.
    """
    # Get the phoneme indices affected by this rule
    start_idx = rule_app.start_index
    end_idx = rule_app.end_index

    # Get phoneme symbols
    phoneme_symbols = []
    if rule_app.modified_phonemes:
        phoneme_symbols = [p.symbol for p in rule_app.modified_phonemes]

    # Build context string
    context_parts = []

    # 1. Phoneme position
    if start_idx == end_idx:
        context_parts.append(f"Position {start_idx}")
    else:
        context_parts.append(f"Positions {start_idx}-{end_idx}")

    # 2. Phonemes affected
    if phoneme_symbols:
        context_parts.append(f"Phonemes: [{' '.join(phoneme_symbols)}]")

    # 3. Try to extract approximate Arabic context
    # Split text into words
    words = text.split()

    # Estimate which word this phoneme belongs to
    # Rough heuristic: average 3-4 phonemes per word
    estimated_word_idx = min(start_idx // 4, len(words) - 1)

    # Get word and surrounding context
    if 0 <= estimated_word_idx < len(words):
        # Show the word and maybe neighbors
        context_words = []
        if estimated_word_idx > 0:
            context_words.append(words[estimated_word_idx - 1])
        context_words.append(f"**{words[estimated_word_idx]}**")  # Highlight target word
        if estimated_word_idx < len(words) - 1:
            context_words.append(words[estimated_word_idx + 1])

        arabic_snippet = ' '.join(context_words)
        context_parts.append(f"≈ {arabic_snippet}")

    return ' | '.join(context_parts)


def get_rule_description(rule_name):
    """Get human-readable English description of a rule."""
    descriptions = {
        # Noon/Meem Sakinah rules
        'idhhar_halqi_noon': 'Iẓhār Ḥalqī (Clear pronunciation of noon saakinah before throat letters: ء ه ع ح غ خ)',
        'idhhar_halqi_meem': 'Iẓhār (Clear pronunciation of meem saakinah)',
        'idgham_ghunnah_noon': 'Idghām with Ghunnah (Assimilation of noon saakinah with nasalization before: ي و ن م)',
        'idgham_bila_ghunnah_noon': 'Idghām without Ghunnah (Assimilation of noon saakinah without nasalization before: ل ر)',
        'idgham_mutamathelain': 'Idghām Mutamāthelain (Assimilation of identical letters)',
        'idgham_meem_sakinah': 'Idghām of Meem Saakinah (Assimilation of م into م)',
        'iqlab': 'Iqlāb (Conversion of noon saakinah to meem before ب)',
        'ikhfaa_noon': 'Ikhfāʾ (Concealment of noon saakinah before remaining letters)',
        'ikhfaa_meem': 'Ikhfāʾ Shafawī (Labial concealment of meem saakinah before ب)',

        # Madd rules
        'madd_tabii': 'Madd Ṭabīʿī (Natural prolongation - 2 counts)',
        'madd_muttasil': 'Madd Muttaṣil (Connected prolongation - 4-5 counts when hamza follows in same word)',
        'madd_munfasil': 'Madd Munfaṣil (Disconnected prolongation - 2-5 counts when hamza follows in next word)',
        'madd_lazim': 'Madd Lāzim (Necessary prolongation - 6 counts)',
        'madd_aarid': 'Madd ʿĀriḍ (Prolongation due to pause)',
        'madd_leen': 'Madd Leen (Softness prolongation)',

        # Qalqalah rules
        'qalqalah_minor': 'Qalqalah Ṣughrā (Minor echoing on ق ط ب ج د with sukoon mid-word)',
        'qalqalah_major': 'Qalqalah Kubrā (Major echoing on ق ط ب ج د with sukoon at word/verse end)',
        'qalqalah_sughra_qaf': 'Qalqalah on Qāf (ق with sukoon)',
        'qalqalah_sughra_taa': 'Qalqalah on Ṭāʾ (ط with sukoon)',

        # Raa rules
        'raa_tafkheem': 'Rāʾ Tafkhīm (Heavy/thick rāʾ with fatha or damma)',
        'raa_tarqeeq': 'Rāʾ Tarqīq (Light/thin rāʾ with kasra)',
        'raa_tafkheem_before_alif': 'Rāʾ Tafkhīm before Alif (Heavy rāʾ)',
        'raa_tarqeeq_with_kasra': 'Rāʾ Tarqīq with Kasra (Light rāʾ)',
        'raa_after_yaa_sakinah': 'Rāʾ after Yāʾ Saakinah',
        'raa_after_hamzat_wasl_kasra': 'Rāʾ after Hamzat Waṣl with Kasra',

        # Emphasis rules
        'vowel_backing_after': 'Vowel Backing after Emphatic (Emphatic influence: [a] → [ɑ])',
        'vowel_backing_before': 'Vowel Backing before Emphatic (Anticipatory emphasis)',
        'emphasis_blocking_by_front_vowel': 'Emphasis Blocking (Front vowel limits emphasis spread)',
    }

    return descriptions.get(rule_name, rule_name)


def generate_html_report(test_results, output_path):
    """Generate comprehensive HTML validation report."""

    # Group rules by category for summary
    category_stats = defaultdict(lambda: {'count': 0, 'rules': set()})
    for result in test_results:
        for app in result['rule_applications']:
            cat = app.rule.category.value
            category_stats[cat]['count'] += 1
            category_stats[cat]['rules'].add(app.rule.name)

    # Count totals
    total_verses = len(test_results)
    total_rules = sum(len(r['rule_applications']) for r in test_results)
    total_phonemes = sum(len(r['phoneme_sequence']) for r in test_results)

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Targeted Tajweed Validation Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .verse {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .verse-header {{
            border-bottom: 2px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .verse-ref {{
            font-size: 1.2em;
            font-weight: bold;
            color: #667eea;
        }}
        .verse-text {{
            font-family: 'Traditional Arabic', 'Scheherazade', serif;
            font-size: 1.8em;
            line-height: 2.2;
            text-align: right;
            direction: rtl;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            margin: 15px 0;
        }}
        .phonemes {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            font-family: 'Courier New', monospace;
            font-size: 1.1em;
        }}
        .rules-section {{
            margin-top: 20px;
        }}
        .rule-item {{
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #4caf50;
        }}
        .rule-name {{
            font-weight: bold;
            color: #2e7d32;
            margin-bottom: 8px;
        }}
        .rule-category {{
            display: inline-block;
            background: #4caf50;
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            margin-left: 10px;
        }}
        .rule-context {{
            background: #fff3e0;
            padding: 10px;
            margin-top: 8px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        .rule-details {{
            color: #666;
            margin-top: 8px;
            font-size: 0.95em;
        }}
        .acoustic-features {{
            background: #e8f5e9;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }}
        .feature-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        .feature-item {{
            background: white;
            padding: 10px;
            border-radius: 5px;
        }}
        .category-summary {{
            background: #fff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .category-item {{
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Targeted Tajweed Validation Report</h1>
        <p>Comprehensive test of ALL Tajweed rule categories</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="summary">
        <h2>Summary Statistics</h2>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{total_verses}</div>
                <div class="stat-label">Test Verses</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{total_rules}</div>
                <div class="stat-label">Rule Applications</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{total_phonemes}</div>
                <div class="stat-label">Total Phonemes</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{len(category_stats)}</div>
                <div class="stat-label">Rule Categories</div>
            </div>
        </div>
    </div>

    <div class="category-summary">
        <h2>Rules by Category</h2>
"""

    for category, stats in sorted(category_stats.items()):
        html += f"""
        <div class="category-item">
            <strong>{category}:</strong> {stats['count']} applications
            <br><small>Rules: {', '.join(sorted(stats['rules']))}</small>
        </div>
"""

    html += """
    </div>

    <h2>Verse Analysis</h2>
"""

    # Add each verse
    for i, result in enumerate(test_results, 1):
        surah = result['surah']
        ayah = result['ayah']
        text = result['text']
        phonemes = result['phonemes']
        rule_apps = result['rule_applications']
        expected_type = result.get('expected_rule_type', 'general')

        html += f"""
    <div class="verse">
        <div class="verse-header">
            <span class="verse-ref">Verse {surah}:{ayah}</span>
            <span style="color: #666; margin-left: 15px;">(Testing: {expected_type})</span>
        </div>

        <div class="verse-text">{text}</div>

        <div class="phonemes">
            <strong>IPA Phonemes:</strong><br>
            [{phonemes}]
        </div>

        <div class="rules-section">
            <h3>Applied Tajweed Rules ({len(rule_apps)})</h3>
"""

        if rule_apps:
            for app in rule_apps:
                rule_name = app.rule.name
                rule_desc = get_rule_description(rule_name)
                category = app.rule.category.value
                context = extract_rule_context(text, app, result['annotated_sequence'])

                # Get phoneme transformation
                orig_phonemes = ' '.join(p.symbol for p in app.original_phonemes)
                mod_phonemes = ' '.join(p.symbol for p in app.modified_phonemes)

                html += f"""
            <div class="rule-item">
                <div class="rule-name">
                    {rule_desc}
                    <span class="rule-category">{category}</span>
                </div>
                <div class="rule-context">
                    📍 Context: {context}
                </div>
                <div class="rule-details">
                    Original phonemes: [{orig_phonemes}]<br>
                    Modified phonemes: [{mod_phonemes}]<br>
                    Confidence: {app.confidence:.1%}
                </div>
            </div>
"""
        else:
            html += """
            <p style="color: #999;">No Tajweed rules applied to this verse.</p>
"""

        # Add acoustic features summary
        features = result['acoustic_features']
        html += f"""
        <div class="acoustic-features">
            <h4>Acoustic Features</h4>
            <div class="feature-grid">
                <div class="feature-item">
                    <strong>Duration:</strong><br>
                    {features.total_duration_ms:.0f} ms
                </div>
                <div class="feature-item">
                    <strong>Phonemes:</strong><br>
                    {features.sequence_length}
                </div>
                <div class="feature-item">
                    <strong>Avg/Phoneme:</strong><br>
                    {features.total_duration_ms/features.sequence_length:.0f} ms
                </div>
            </div>
        </div>
"""

        html += """
    </div>
"""

    html += """
</body>
</html>
"""

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Report generated: {output_path}")
    print(f"   Total size: {len(html) / 1024:.1f} KB")


def main():
    print("=" * 70)
    print("Targeted Tajweed Validation Report Generator")
    print("=" * 70)

    # Load Qur'an text
    print("\n1. Loading Qur'an text...")
    with open('data/quran_text/quran_hafs.json', 'r', encoding='utf-8') as f:
        quran_data = json.load(f)
    print(f"   ✅ Loaded {len(quran_data['surahs'])} surahs")

    # Find verses with specific patterns
    print("\n2. Searching for verses with specific Tajweed patterns...")
    verse_candidates = find_verses_by_pattern(quran_data, target_rules=[
        'idhhar', 'idgham', 'iqlab', 'ikhfaa',
        'madd_muttasil', 'madd_munfasil',
        'qalqalah', 'raa_heavy', 'raa_light', 'emphatic'
    ])

    print("\n   Pattern search results:")
    for rule_type, verses in sorted(verse_candidates.items()):
        print(f"     • {rule_type}: {len(verses)} verses found")

    # Select balanced test set
    print("\n3. Selecting balanced test verses (2 per rule type)...")
    test_verses = select_test_verses(verse_candidates, target_count_per_type=2)
    print(f"   ✅ Selected {len(test_verses)} test verses")

    # Initialize pipeline
    print("\n4. Initializing Symbolic Layer Pipeline...")
    pipeline = SymbolicLayerPipeline(speaker_type="male")

    # Process each test verse
    print("\n5. Processing verses through pipeline...")
    test_results = []

    for verse_info in test_verses:
        surah = verse_info['surah']
        ayah = verse_info['ayah']
        expected_type = verse_info['expected_rule_type']

        print(f"\n   Processing {surah}:{ayah} (testing {expected_type})...")

        try:
            output = pipeline.process_verse(surah=surah, ayah=ayah)

            result = {
                'surah': surah,
                'ayah': ayah,
                'text': output.original_text,
                'expected_rule_type': expected_type,
                'phonemes': output.to_ipa_string(),
                'phoneme_sequence': output.phoneme_sequence.phonemes,
                'annotated_sequence': output.annotated_sequence,
                'rule_applications': output.annotated_sequence.rule_applications,
                'acoustic_features': output.acoustic_features
            }

            test_results.append(result)

            # Show rules applied
            rules_found = defaultdict(int)
            for app in output.annotated_sequence.rule_applications:
                rules_found[app.rule.category.value] += 1

            print(f"     Rules applied: {sum(rules_found.values())}")
            for cat, count in sorted(rules_found.items()):
                print(f"       • {cat}: {count}")

        except Exception as e:
            print(f"     ⚠️  Error processing verse: {e}")
            import traceback
            traceback.print_exc()

    # Generate report
    print("\n6. Generating HTML validation report...")
    output_path = Path("output/targeted_validation_report.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_html_report(test_results, output_path)

    print("\n" + "=" * 70)
    print(f"✅ Targeted Validation Report Complete!")
    print(f"   Report: {output_path.absolute()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
