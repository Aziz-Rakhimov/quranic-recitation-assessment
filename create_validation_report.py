#!/usr/bin/env python3
"""
Tajwīd Validation Report Generator.

This script:
1. Randomly selects 20 verses from the Qur'an
2. Processes each through the Symbolic Layer pipeline
3. Generates an HTML validation report showing:
   - Arabic text with rule highlighting
   - Detected Tajwīd rules with positions
   - IPA phoneme sequences
   - Expected acoustic features
4. Saves to output/validation_report.html

For review by Tajwīd experts to verify correctness.
"""

import sys
import json
import random
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline


def load_quran_text(path: str = "data/quran_text/quran_hafs.json"):
    """Load Qur'anic text from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def select_random_verses(quran_data, count=20):
    """Select random verses from the Qur'an."""
    verses = []

    for surah_data in quran_data.get('surahs', []):
        surah_num = surah_data.get('number')
        surah_name = surah_data.get('name')

        for ayah_data in surah_data.get('ayahs', []):
            ayah_num = ayah_data.get('numberInSurah')
            text = ayah_data.get('text', '')

            verses.append({
                'surah': surah_num,
                'surah_name': surah_name,
                'ayah': ayah_num,
                'text': text
            })

    # Select random verses
    return random.sample(verses, min(count, len(verses)))


def get_rule_color(category):
    """Get color for rule category."""
    colors = {
        'noon_meem_sakinah': '#FF6B6B',  # Red
        'madd': '#4ECDC4',               # Teal
        'qalqalah': '#95E1D3',           # Light green
        'raa': '#F38181',                # Pink
        'general': '#AA96DA',            # Purple (for emphasis)
    }
    return colors.get(category, '#CCCCCC')


def get_rule_description(rule_name):
    """Get English description for common rules."""
    mapping = {
        'idhhar_halqi_noon': 'Iẓhār Ḥalqī (Clear pronunciation before throat letters)',
        'idgham_ghunnah_noon': 'Idghām with Ghunnah (Assimilation with nasalization)',
        'idgham_no_ghunnah': 'Idghām without Ghunnah (Assimilation without nasalization)',
        'idgham_shafawi': 'Idghām Shafawī (Labial assimilation)',
        'iqlab': 'Iqlāb (Conversion to mīm before bāʾ)',
        'ikhfaa_light': 'Ikhfāʾ Light (Light concealment)',
        'ikhfaa_heavy': 'Ikhfāʾ Heavy (Heavy concealment with emphasis)',
        'ikhfaa_shafawi': 'Ikhfāʾ Shafawī (Labial concealment)',
        'idhhar_shafawi': 'Iẓhār Shafawī (Clear labial pronunciation)',
        'madd_tabii': 'Madd Ṭabīʿī (Natural prolongation - 2 counts)',
        'madd_muttasil': 'Madd Muttaṣil (Connected prolongation - 4-5 counts)',
        'madd_munfasil': 'Madd Munfaṣil (Disconnected prolongation - 2-5 counts)',
        'madd_lazim': 'Madd Lāzim (Necessary prolongation - 6 counts)',
        'madd_arid': 'Madd ʿĀriḍ (Accidental prolongation - 2-6 counts)',
        'qalqalah_minor': 'Qalqalah Minor (Echo sound mid-word)',
        'qalqalah_major': 'Qalqalah Major (Echo sound at word/verse end)',
        'qalqalah_emphatic': 'Qalqalah Emphatic (Echo with emphasis)',
        'raa_tafkheem': 'Rāʾ Tafkhīm (Heavy/thick rāʾ)',
        'raa_tarqeeq': 'Rāʾ Tarqīq (Light/thin rāʾ)',
        'vowel_backing_after': 'Vowel Backing (Emphatic influence: [a] → [ɑ])',
        'vowel_backing_before': 'Regressive Vowel Backing ([a] → [ɑ] before emphatic)',
        'emphasis_blocking': 'Emphasis Blocking (Front vowel blocks backing)',
    }

    for key, description in mapping.items():
        if key in rule_name:
            return description

    # Default: make rule name readable
    return rule_name.replace('_', ' ').title()


def generate_html_report(verses_data, output_path="output/validation_report.html"):
    """Generate HTML validation report."""

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tajwīd Validation Report - تقرير التحقق من أحكام التجويد</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            direction: rtl;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .header p {{
            font-size: 1.1em;
            opacity: 0.95;
        }}

        .meta-info {{
            background: #f8f9fa;
            padding: 20px 40px;
            border-bottom: 3px solid #667eea;
        }}

        .meta-info p {{
            margin: 5px 0;
            font-size: 0.95em;
        }}

        .verse {{
            padding: 40px;
            border-bottom: 2px solid #e0e0e0;
        }}

        .verse:last-child {{
            border-bottom: none;
        }}

        .verse-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #667eea;
        }}

        .verse-title {{
            font-size: 1.5em;
            color: #667eea;
            font-weight: bold;
        }}

        .verse-ref {{
            background: #667eea;
            color: white;
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: bold;
        }}

        .arabic-text {{
            font-size: 2em;
            line-height: 2.2;
            margin: 20px 0;
            padding: 25px;
            background: #f8f9fa;
            border-right: 4px solid #667eea;
            border-radius: 8px;
            font-family: 'Traditional Arabic', 'Scheherazade', 'Arial', sans-serif;
        }}

        .highlighted {{
            background-color: rgba(255, 107, 107, 0.3);
            padding: 2px 4px;
            border-radius: 3px;
            transition: all 0.3s;
        }}

        .highlighted:hover {{
            background-color: rgba(255, 107, 107, 0.5);
            transform: scale(1.05);
        }}

        .section {{
            margin: 25px 0;
        }}

        .section-title {{
            font-size: 1.3em;
            color: #333;
            margin-bottom: 15px;
            padding: 10px;
            background: #f0f0f0;
            border-right: 4px solid #667eea;
            font-weight: bold;
        }}

        .ipa-text {{
            font-family: 'Courier New', monospace;
            font-size: 1.2em;
            padding: 15px;
            background: #fff3cd;
            border-radius: 5px;
            direction: ltr;
            text-align: left;
            border: 2px solid #ffc107;
        }}

        .rules-list {{
            list-style: none;
        }}

        .rule-item {{
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-right: 4px solid;
            background: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }}

        .rule-item:hover {{
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            transform: translateX(-5px);
        }}

        .rule-name {{
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 5px;
        }}

        .rule-category {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            color: white;
            margin-left: 10px;
        }}

        .rule-details {{
            font-size: 0.9em;
            color: #666;
            margin-top: 8px;
        }}

        .phoneme-change {{
            font-family: monospace;
            background: #e3f2fd;
            padding: 4px 8px;
            border-radius: 4px;
            margin: 0 5px;
        }}

        .features-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}

        .feature-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #e0e0e0;
        }}

        .feature-label {{
            font-weight: bold;
            color: #667eea;
            margin-bottom: 8px;
            font-size: 0.95em;
        }}

        .feature-value {{
            font-size: 1.1em;
            color: #333;
        }}

        .stats {{
            background: #e8f5e9;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }}

        .legend {{
            background: #f8f9fa;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            border: 2px solid #e0e0e0;
        }}

        .legend-title {{
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}

        .legend-items {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .legend-color {{
            width: 30px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid #ccc;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #666;
            border-top: 3px solid #667eea;
        }}

        @media print {{
            body {{
                background: white;
                padding: 0;
            }}

            .verse {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕌 Tajwīd Validation Report</h1>
            <h2>Automated Analysis of Tajwīd Rules</h2>
            <p>Qur'anic Recitation Assessment System</p>
            <p>Narration: Ḥafṣ ʿan ʿĀṣim | حفص عن عاصم</p>
        </div>

        <div class="meta-info">
            <p><strong>Report Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Number of Verses:</strong> {len(verses_data)} randomly selected</p>
            <p><strong>System:</strong> Symbolic Layer Pipeline v1.0</p>
            <p><strong>Purpose:</strong> Expert validation of automatic Tajwīd rule detection</p>
        </div>

        <div class="legend" style="margin: 20px 40px;">
            <div class="legend-title">🎨 Rule Category Colors:</div>
            <div class="legend-items">
                <div class="legend-item">
                    <div class="legend-color" style="background: #FF6B6B;"></div>
                    <span>Nūn/Mīm Sākinah Rules (Iẓhār, Idghām, Iqlāb, Ikhfāʾ)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #4ECDC4;"></div>
                    <span>Madd Rules (Prolongation: Ṭabīʿī, Muttaṣil, Munfaṣil)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #95E1D3;"></div>
                    <span>Qalqalah (Echo sound on ق ط ب ج د)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #F38181;"></div>
                    <span>Rāʾ Rules (Tafkhīm/Tarqīq - Heavy/Light)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #AA96DA;"></div>
                    <span>Emphasis Rules (Vowel backing near emphatic letters)</span>
                </div>
            </div>
        </div>
"""

    # Add each verse
    for idx, verse_data in enumerate(verses_data, 1):
        output = verse_data['output']

        # Count rules by category
        rules_by_category = {}
        for app in output.annotated_sequence.rule_applications:
            cat = app.rule.category.value
            rules_by_category[cat] = rules_by_category.get(cat, 0) + 1

        html += f"""
        <div class="verse">
            <div class="verse-header">
                <div class="verse-title">{verse_data['surah_name']}</div>
                <div class="verse-ref">Surah {verse_data['surah']} : Ayah {verse_data['ayah']}</div>
            </div>

            <div class="arabic-text">
                {output.original_text}
            </div>

            <div class="stats">
                <strong>📊 Statistics:</strong>
                Phonemes: {len(output.phoneme_sequence.phonemes)} |
                Tajwīd Rules: {len(output.annotated_sequence.rule_applications)} |
                Duration: {output.acoustic_features.total_duration_ms:.0f} ms ({output.acoustic_features.total_duration_ms/1000:.1f} seconds)
            </div>

            <div class="section">
                <div class="section-title">🔤 IPA Phoneme Sequence</div>
                <div class="ipa-text">[{output.to_ipa_string()}]</div>
            </div>
"""

        # Add Tajweed rules
        if output.annotated_sequence.rule_applications:
            html += """
            <div class="section">
                <div class="section-title">📋 Applied Tajwīd Rules</div>
                <ul class="rules-list">
"""

            for app in output.annotated_sequence.rule_applications:
                color = get_rule_color(app.rule.category.value)
                rule_description = get_rule_description(app.rule.name)

                orig_phonemes = ' '.join([p.symbol for p in app.original_phonemes])
                mod_phonemes = ' '.join([p.symbol for p in app.modified_phonemes])

                html += f"""
                    <li class="rule-item" style="border-right-color: {color};">
                        <div class="rule-name">
                            {rule_description}
                            <span class="rule-category" style="background: {color};">
                                {app.rule.category.value}
                            </span>
                        </div>
                        <div class="rule-details">
                            📍 Position: {app.start_index}-{app.end_index} |
                            Phoneme Change:
                            <span class="phoneme-change">{orig_phonemes}</span>
                            →
                            <span class="phoneme-change">{mod_phonemes}</span>
                            | Confidence: {app.confidence:.2f}
                        </div>
                    </li>
"""

            html += """
                </ul>
            </div>
"""

        # Add acoustic features summary
        stats = output.get_statistics()
        html += f"""
            <div class="section">
                <div class="section-title">🎵 Expected Acoustic Features</div>
                <div class="features-grid">
                    <div class="feature-card">
                        <div class="feature-label">Total Duration</div>
                        <div class="feature-value">{output.acoustic_features.total_duration_ms:.0f} ms</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-label">Avg Phoneme Duration</div>
                        <div class="feature-value">{stats['acoustic_features']['average_phoneme_duration_ms']:.0f} ms</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-label">Nasalized Phonemes</div>
                        <div class="feature-value">{stats['acoustic_features']['nasalized_phonemes']}</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-label">Emphatic Consonants</div>
                        <div class="feature-value">{stats['phonemes']['emphatic']}</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-label">Consonants</div>
                        <div class="feature-value">{stats['phonemes']['consonants']}</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-label">Vowels</div>
                        <div class="feature-value">{stats['phonemes']['vowels']}</div>
                    </div>
                </div>
            </div>
        </div>
"""

    # Add footer
    html += f"""
        <div class="footer">
            <p><strong>⚠️ Important Note:</strong></p>
            <p>This report shows automated analysis results of Tajwīd rule detection.</p>
            <p><strong>Please review by a Tajwīd expert to verify correctness of:</strong></p>
            <ul style="text-align: right; margin: 10px auto; max-width: 600px;">
                <li>Rule detection accuracy (are the right rules applied?)</li>
                <li>Rule positions (are they in the correct locations?)</li>
                <li>Phoneme transformations (are changes appropriate?)</li>
                <li>Missing rules (are any rules not detected?)</li>
            </ul>
            <br>
            <p style="font-size: 0.9em; color: #999;">
                Generated by Symbolic Layer Pipeline<br>
                Qur'anic Recitation Assessment System<br>
                نظام تقييم التلاوة القرآنية
            </p>
        </div>
    </div>
</body>
</html>
"""

    return html


def main():
    print("=" * 70)
    print("Tajwīd Validation Report Generator")
    print("=" * 70)

    # Load Qur'an text
    print("\n1. Loading Qur'anic text...")
    try:
        quran_data = load_quran_text()
        total_verses = sum(len(s.get('ayahs', [])) for s in quran_data.get('surahs', []))
        print(f"   ✅ Loaded {total_verses} verses")
    except Exception as e:
        print(f"   ❌ Failed to load Qur'an text: {e}")
        return False

    # Select random verses
    print("\n2. Selecting 20 random verses...")
    selected_verses = select_random_verses(quran_data, count=20)
    print(f"   ✅ Selected {len(selected_verses)} verses")

    # Initialize pipeline
    print("\n3. Initializing Symbolic Layer Pipeline...")
    try:
        pipeline = SymbolicLayerPipeline(speaker_type="male")
        print(f"   ✅ Pipeline initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Process verses
    print("\n4. Processing verses through pipeline...")
    verses_data = []

    for i, verse in enumerate(selected_verses, 1):
        try:
            print(f"   Processing verse {i}/{len(selected_verses)}: {verse['surah_name']} {verse['surah']}:{verse['ayah']}")

            output = pipeline.process_text(
                verse['text'],
                surah=verse['surah'],
                ayah=verse['ayah']
            )

            verses_data.append({
                'surah': verse['surah'],
                'surah_name': verse['surah_name'],
                'ayah': verse['ayah'],
                'text': verse['text'],
                'output': output
            })

        except Exception as e:
            print(f"   ⚠️  Error processing verse: {e}")
            continue

    print(f"   ✅ Successfully processed {len(verses_data)} verses")

    # Generate HTML report
    print("\n5. Generating HTML report...")
    try:
        html_content = generate_html_report(verses_data)

        # Save to file
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / "validation_report.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"   ✅ Report saved to: {output_path.absolute()}")
        print(f"   📄 Report size: {len(html_content) / 1024:.1f} KB")

    except Exception as e:
        print(f"   ❌ Failed to generate report: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Print summary
    print("\n" + "=" * 70)
    print("✅ Validation Report Generated Successfully!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   - Total verses processed: {len(verses_data)}")
    print(f"   - Total Tajweed rules detected: {sum(len(v['output'].annotated_sequence.rule_applications) for v in verses_data)}")
    print(f"   - Total phonemes: {sum(len(v['output'].phoneme_sequence.phonemes) for v in verses_data)}")
    print(f"\n📂 Output file: {output_path.absolute()}")
    print(f"\n💡 Next step: Open the HTML file in a browser and review with a Tajwīd expert")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
