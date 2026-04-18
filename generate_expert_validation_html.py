#!/usr/bin/env python3
"""
Generate Professional HTML Validation Report for Tajwīd Expert Review

Creates a beautifully formatted HTML report with:
- Arabic text in Uthmani font
- Rule detection results
- Phoneme sequences
- Acoustic expectations
- Print-friendly CSS for PDF export
"""

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline

# Test verses for each rule type (MUST match verify_all_rules.py exactly!)
TEST_VERSES = {
    # Noon/Meem Sakinah Rules
    'ghunnah_mushaddadah_noon': [
        {'surah': 108, 'ayah': 1, 'text': 'إِنَّآ أَعْطَيْنَٰكَ', 'note': 'إِنَّ has noon with shaddah'},
        {'surah': 2, 'ayah': 25, 'text': 'وَبَشِّرِ ٱلَّذِينَ ءَامَنُوا۟ وَعَمِلُوا۟ ٱلصَّٰلِحَٰتِ أَنَّ لَهُمْ جَنَّٰتٍ', 'note': 'أَنَّ and جَنَّٰتٍ have noon with shaddah'},
    ],
    'ghunnah_mushaddadah_meem': [
        {'surah': 2, 'ayah': 28, 'text': 'ثُمَّ يُمِيتُكُمْ ثُمَّ يُحْيِيكُمْ', 'note': 'ثُمَّ has meem with shaddah'},
        {'surah': 89, 'ayah': 15, 'text': 'فَأَمَّا ٱلْإِنسَٰنُ إِذَا', 'note': 'فَأَمَّا has meem with shaddah'},
    ],
    'idhhar_halqi_noon': [
        {'surah': 1, 'ayah': 7, 'text': 'صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ', 'note': 'أَنْعَمْتَ - noon before ع'},
        {'surah': 2, 'ayah': 6, 'text': 'إِنَّ ٱلَّذِينَ كَفَرُوا۟ سَوَآءٌ عَلَيْهِمْ', 'note': 'سَوَآءٌ عَلَيْهِمْ - tanween before ع'},
    ],
    'idgham_ghunnah_noon': [
        {'surah': 18, 'ayah': 16, 'text': 'فَأْوُۥٓا۟ إِلَى ٱلْكَهْفِ مِن وَرَآئِهِمْ', 'note': 'مِن وَرَآئِ - noon before waw'},
        {'surah': 2, 'ayah': 107, 'text': 'مِن وَلِىٍّ وَلَا نَصِيرٍ', 'note': 'مِن وَلِىٍّ - noon before waw'},
    ],
    'idgham_no_ghunnah': [
        {'surah': 96, 'ayah': 15, 'text': 'كَلَّا لَئِن لَّمْ يَنتَهِ', 'note': 'لَئِن لَّمْ - noon before lam'},
        {'surah': 2, 'ayah': 2, 'text': 'هُدًى لِّلْمُتَّقِينَ', 'note': 'هُدًى لِّ - tanween before lam with idgham'},
    ],
    'iqlab': [
        {'surah': 2, 'ayah': 27, 'text': 'مِن بَعْدِ مِيثَٰقِهِۦ', 'note': 'مِن بَعْدِ - noon before baa'},
        {'surah': 96, 'ayah': 15, 'text': 'لَنَسْفَعًۢا بِٱلنَّاصِيَةِ', 'note': 'لَنَسْفَعًۢا بِ - tanween before baa'},
    ],
    'ikhfaa_light': [
        {'surah': 2, 'ayah': 2, 'text': 'ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبً ۛ فِيهِ', 'note': 'رَيْبً فِيهِ - tanween before ف'},
        {'surah': 114, 'ayah': 4, 'text': 'مِن شَرِّ ٱلْوَسْوَاسِ', 'note': 'مِن شَرِّ - noon before ش'},
    ],
    'ikhfaa_heavy': [
        {'surah': 23, 'ayah': 12, 'text': 'وَلَقَدْ خَلَقْنَا ٱلْإِنسَٰنَ مِن صَلْصَٰلٍ', 'note': 'مِن صَلْصَٰلٍ - noon before emphatic saad (ص)'},
        {'surah': 23, 'ayah': 33, 'text': 'مِن طِينٍ', 'note': 'مِن طِينٍ - noon before emphatic taa (ط)'},
    ],
    'idhhar_shafawi': [
        {'surah': 1, 'ayah': 7, 'text': 'غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ', 'note': 'عَلَيْهِمْ وَ - meem before waw'},
        {'surah': 2, 'ayah': 7, 'text': 'خَتَمَ ٱللَّهُ عَلَىٰ قُلُوبِهِمْ وَعَلَىٰ سَمْعِهِمْ', 'note': 'قُلُوبِهِمْ وَ - meem before waw'},
    ],
    'idgham_shafawi_meem': [
        {'surah': 2, 'ayah': 25, 'text': 'وَبَشِّرِ ٱلَّذِينَ ءَامَنُوا۟ وَعَمِلُوا۟ ٱلصَّٰلِحَٰتِ أَنَّ لَهُم مَّا', 'note': 'لَهُم مَّا - meem before meem'},
        {'surah': 30, 'ayah': 10, 'text': 'ثُمَّ كَانَ عَٰقِبَةَ', 'note': 'ثُمَّ has meem with shaddah (doubled meem)'},
    ],
    'ikhfaa_shafawi': [
        {'surah': 105, 'ayah': 4, 'text': 'تَرْمِيهِم بِحِجَارَةٍ', 'note': 'تَرْمِيهِم بِ - meem before baa'},
        {'surah': 2, 'ayah': 233, 'text': 'وَٱللَّهُ بِمَا تَعْمَلُونَ بَصِيرٌ وَأَنتُمْ بِهِ', 'note': 'Check for meem before baa - تُمْ بِ pattern'},
    ],

    # Madd Rules
    'madd_tabii': [
        {'surah': 1, 'ayah': 1, 'text': 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ', 'note': 'ٱلرَّحْمَٰنِ has long aa'},
        {'surah': 112, 'ayah': 1, 'text': 'قُلْ هُوَ ٱللَّهُ أَحَدٌ', 'note': 'هُوَ has long uu'},
    ],
    'madd_muttasil': [
        {'surah': 2, 'ayah': 19, 'text': 'أَوْ كَصَيِّبٍ مِّنَ ٱلسَّمَآءِ', 'note': 'ٱلسَّمَآءِ - long aa before hamza in same word'},
        {'surah': 2, 'ayah': 61, 'text': 'فَٱدْعُ لَنَا رَبَّكَ جَآءَ بِمَا', 'note': 'جَآءَ - long aa before hamza in same word'},
    ],
    'madd_munfasil': [
        {'surah': 51, 'ayah': 21, 'text': 'وَفِي أَنفُسِكُمْ', 'note': 'long ii in fii + hamza at start of anfusikum'},
        {'surah': 2, 'ayah': 13, 'text': 'قَالُوٓا۟ ءَأَمِنُ', 'note': 'qaaloo ends with long uu + next word starts with hamza'},
    ],
    'madd_lazim_kalimi': [
        {'surah': 1, 'ayah': 7, 'text': 'غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ', 'note': 'ٱلضَّآلِّينَ - aa before doubled lam'},
        {'surah': 69, 'ayah': 1, 'text': 'ٱلْحَآقَّةُ', 'note': 'ٱلْحَآقَّةُ - aa before doubled qaaf'},
    ],
    'madd_arid_lissukun': [
        {'surah': 1, 'ayah': 5, 'text': 'إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ', 'note': 'نَسْتَعِينُ - long ii at verse end'},
        {'surah': 1, 'ayah': 2, 'text': 'ٱلرَّحْمَٰنِ ٱلرَّحِيمِ', 'note': 'ٱلرَّحِيمِ - ends with long ii + meem at verse end'},
    ],
    'madd_silah_kubra': [
        {'surah': 18, 'ayah': 38, 'text': 'بِهِۦٓ أَسَفًا', 'note': 'bihi asafan - pronoun haa with kasra before hamza'},
        {'surah': 3, 'ayah': 73, 'text': 'لَهُۥٓ أَجْرٌ عِندَ', 'note': 'lahu ajr - pronoun haa with damma before hamza'},
    ],

    # Qalqalah Rules
    'qalqalah_minor': [
        {'surah': 2, 'ayah': 245, 'text': 'وَٱللَّهُ يَقْبِضُ وَيَبْسُطُ', 'note': 'يَقْبِضُ and يَبْسُطُ have qalqalah with sukoon mid-word'},
        {'surah': 2, 'ayah': 191, 'text': 'وَٱقْتُلُوهُمْ حَيْثُ', 'note': 'وَٱقْتُلُوهُمْ has qaaf with sukoon mid-word'},
    ],
    'qalqalah_major': [
        {'surah': 5, 'ayah': 15, 'text': 'قَدْ جَآءَكُمْ', 'note': 'قَدْ has daal with sukoon at word end'},
        {'surah': 23, 'ayah': 1, 'text': 'قَدْ أَفْلَحَ ٱلْمُؤْمِنُونَ', 'note': 'قَدْ أَفْلَحَ - daal with sukoon at word end'},
    ],
    'qalqalah_with_shaddah': [
        {'surah': 111, 'ayah': 1, 'text': 'تَبَّتْ يَدَآ أَبِى لَهَبٍ', 'note': 'تَبَّتْ has baa with shaddah'},
        {'surah': 54, 'ayah': 17, 'text': 'فَهَلْ مِن مُّدَّكِرٍ', 'note': 'مُدَّكِرٍ has daal (د) with shaddah - doubled daal is a qalqalah letter'},
    ],
    'qalqalah_emphatic': [
        {'surah': 2, 'ayah': 245, 'text': 'وَٱللَّهُ يَقْبِضُ وَيَبْسُطُ', 'note': 'قَبْ and بَسْ have qalqalah in emphatic context'},
        {'surah': 16, 'ayah': 2, 'text': 'قَدْ جَآءَكُمْ', 'note': 'قَدْ has daal with sukoon in context'},
    ],
    'qalqalah_non_emphatic': [
        {'surah': 112, 'ayah': 3, 'text': 'لَمْ يَلِدْ وَلَمْ يُولَدْ', 'note': 'يَلِدْ has daal at end with kasra context'},
        {'surah': 112, 'ayah': 3, 'text': 'لَمْ يُولَدْ', 'note': 'يُولَدْ has daal at end in non-emphatic context'},
    ],

    # Pronunciation Rules
    'ta_marbuta_wasl': [
        {'surah': 1, 'ayah': 1, 'text': 'رَحْمَةُ اللَّهِ', 'note': 'رَحْمَةُ اللَّهِ - ta marbuta continues to next word (t sound)'},
        {'surah': 16, 'ayah': 18, 'text': 'نِعْمَةَ ٱللَّهِ', 'note': 'نِعْمَةَ ٱللَّهِ - ta marbuta (ة) continues to next word in wasl'},
    ],
    'ta_marbuta_waqf': [
        {'surah': 1, 'ayah': 1, 'text': 'جَنَّةٌ', 'note': 'جَنَّةٌ - ta marbuta at end (h sound in waqf)'},
        {'surah': 2, 'ayah': 157, 'text': 'وَرَحْمَةٌ', 'note': 'وَرَحْمَةٌ - ta marbuta at end of phrase (waqf)'},
    ],
}

# Rule metadata
RULE_METADATA = {
    'ghunnah_mushaddadah_noon': {'arabic': 'غنة مشددة - نون', 'category': 'Noon/Meem Sākinah'},
    'ghunnah_mushaddadah_meem': {'arabic': 'غنة مشددة - ميم', 'category': 'Noon/Meem Sākinah'},
    'idhhar_halqi_noon': {'arabic': 'إظهار حلقي', 'category': 'Noon/Meem Sākinah'},
    'idhhar_shafawi': {'arabic': 'إظهار شفوي', 'category': 'Noon/Meem Sākinah'},
    'idgham_ghunnah_noon': {'arabic': 'إدغام بغنة', 'category': 'Noon/Meem Sākinah'},
    'idgham_no_ghunnah': {'arabic': 'إدغام بلا غنة', 'category': 'Noon/Meem Sākinah'},
    'idgham_shafawi_meem': {'arabic': 'إدغام شفوي', 'category': 'Noon/Meem Sākinah'},
    'iqlab': {'arabic': 'إقلاب', 'category': 'Noon/Meem Sākinah'},
    'ikhfaa_light': {'arabic': 'إخفاء خفيف', 'category': 'Noon/Meem Sākinah'},
    'ikhfaa_heavy': {'arabic': 'إخفاء ثقيل', 'category': 'Noon/Meem Sākinah'},
    'ikhfaa_shafawi': {'arabic': 'إخفاء شفوي', 'category': 'Noon/Meem Sākinah'},
    'madd_tabii': {'arabic': 'مد طبيعي', 'category': 'Madd'},
    'madd_muttasil': {'arabic': 'مد متصل', 'category': 'Madd'},
    'madd_munfasil': {'arabic': 'مد منفصل', 'category': 'Madd'},
    'madd_lazim_kalimi': {'arabic': 'مد لازم كلمي', 'category': 'Madd'},
    'madd_arid_lissukun': {'arabic': 'مد عارض للسكون', 'category': 'Madd'},
    'madd_silah_kubra': {'arabic': 'مد صلة كبرى', 'category': 'Madd'},
    'qalqalah_minor': {'arabic': 'قلقلة صغرى', 'category': 'Qalqalah'},
    'qalqalah_major': {'arabic': 'قلقلة كبرى', 'category': 'Qalqalah'},
    'qalqalah_with_shaddah': {'arabic': 'قلقلة مع شدة', 'category': 'Qalqalah'},
    'qalqalah_emphatic': {'arabic': 'قلقلة مفخمة', 'category': 'Qalqalah'},
    'qalqalah_non_emphatic': {'arabic': 'قلقلة مرققة', 'category': 'Qalqalah'},
    'ta_marbuta_wasl': {'arabic': 'تاء مربوطة - وصل', 'category': 'Pronunciation'},
    'ta_marbuta_waqf': {'arabic': 'تاء مربوطة - وقف', 'category': 'Pronunciation'},
}


def generate_html_report():
    """Generate comprehensive HTML validation report."""
    print("Generating Expert Validation HTML Report...")
    print("=" * 80)

    # Initialize pipeline
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)

    # Run tests and collect results
    results = defaultdict(list)
    rule_detection_status = {}

    for rule_type, test_cases in TEST_VERSES.items():
        print(f"\nTesting: {rule_type}")
        detected_count = 0

        for i, test_case in enumerate(test_cases, 1):
            text = test_case['text']
            note = test_case['note']

            try:
                output = pipeline.process_text(text)

                # Check if rule detected
                rule_found = any(
                    rule_type in app.rule.name or app.rule.name in rule_type
                    for app in output.annotated_sequence.rule_applications
                )

                if rule_found:
                    detected_count += 1
                    print(f"  Test {i}: ✅ DETECTED")
                else:
                    print(f"  Test {i}: ❌ NOT DETECTED")

                # Store detailed result
                phonemes = [p.symbol for p in output.phoneme_sequence.phonemes]
                matching_apps = [
                    app for app in output.annotated_sequence.rule_applications
                    if rule_type in app.rule.name or app.rule.name in rule_type
                ]

                results[rule_type].append({
                    'text': text,
                    'note': note,
                    'detected': rule_found,
                    'phonemes': phonemes,
                    'applications': matching_apps,
                    'all_rules': output.annotated_sequence.rule_applications
                })

            except Exception as e:
                print(f"  Test {i}: ⚠️  ERROR - {e}")
                results[rule_type].append({
                    'text': text,
                    'note': note,
                    'detected': False,
                    'error': str(e)
                })

        # Update status
        total = len(test_cases)
        if detected_count == total:
            status = '✅ VERIFIED'
        elif detected_count > 0:
            status = '⚠️  PARTIAL'
        else:
            status = '❌ FAILED'

        rule_detection_status[rule_type] = {
            'status': status,
            'detected': detected_count,
            'total': total
        }

    # Generate HTML
    html = generate_html_content(results, rule_detection_status, pipeline)

    # Save to file
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'tajweed_expert_validation_report.html'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n{'=' * 80}")
    print(f"✅ HTML Report Generated Successfully!")
    print(f"📄 Location: {output_file}")
    print(f"🌐 Open in browser to view")
    print(f"🖨️  Use browser's Print function to save as PDF")
    print(f"{'=' * 80}")

    return output_file


def generate_html_content(results, rule_detection_status, pipeline):
    """Generate HTML content with embedded CSS."""

    # Calculate statistics
    total_verified = sum(1 for s in rule_detection_status.values() if '✅' in s['status'])
    total_partial = sum(1 for s in rule_detection_status.values() if '⚠️' in s['status'])
    total_failed = sum(1 for s in rule_detection_status.values() if '❌' in s['status'])
    total_rules = len(rule_detection_status)
    verification_rate = (total_verified / total_rules) * 100 if total_rules > 0 else 0

    html = f'''<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tajwīd Rule Validation Report - Expert Review</title>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* ===== GENERAL STYLES ===== */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            background: #f5f7fa;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 2px 20px rgba(0,0,0,0.08);
            border-radius: 12px;
            overflow: hidden;
        }}

        /* ===== ARABIC TEXT STYLES ===== */
        .arabic {{
            font-family: 'Amiri', 'Traditional Arabic', serif;
            font-size: 24px;
            line-height: 2;
            direction: rtl;
            text-align: right;
            color: #2c3e50;
            font-weight: 400;
        }}

        .arabic-small {{
            font-family: 'Amiri', 'Traditional Arabic', serif;
            font-size: 18px;
            direction: rtl;
            text-align: right;
            color: #34495e;
        }}

        /* ===== HEADER ===== */
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
            font-weight: 300;
        }}

        .header .date {{
            margin-top: 20px;
            font-size: 14px;
            opacity: 0.8;
        }}

        /* ===== STATISTICS SUMMARY ===== */
        .stats-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }}

        .stat-card {{
            background: white;
            padding: 24px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        .stat-value {{
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .stat-value.verified {{ color: #10b981; }}
        .stat-value.partial {{ color: #f59e0b; }}
        .stat-value.failed {{ color: #ef4444; }}
        .stat-value.rate {{ color: #667eea; }}

        .stat-label {{
            font-size: 14px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
        }}

        /* ===== PRINT INSTRUCTIONS ===== */
        .print-instructions {{
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
            padding: 20px 30px;
            margin: 0 40px 30px;
            border-radius: 8px;
        }}

        .print-instructions h3 {{
            color: #92400e;
            font-size: 16px;
            margin-bottom: 10px;
        }}

        .print-instructions p {{
            color: #78350f;
            font-size: 14px;
            line-height: 1.6;
        }}

        /* ===== CONTENT SECTION ===== */
        .content {{
            padding: 40px;
        }}

        .category {{
            margin-bottom: 50px;
        }}

        .category-header {{
            background: #f8f9fa;
            padding: 20px;
            border-left: 5px solid #667eea;
            margin-bottom: 30px;
            border-radius: 8px;
        }}

        .category-header h2 {{
            font-size: 24px;
            color: #1a1a1a;
            margin-bottom: 5px;
        }}

        .category-stats {{
            font-size: 14px;
            color: #6b7280;
            margin-top: 8px;
        }}

        /* ===== RULE CARD ===== */
        .rule-card {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            margin-bottom: 30px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }}

        .rule-header {{
            padding: 20px 30px;
            background: #fafbfc;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .rule-title {{
            flex: 1;
        }}

        .rule-name {{
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 5px;
        }}

        .rule-status {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .status-verified {{
            background: #d1fae5;
            color: #065f46;
        }}

        .status-partial {{
            background: #fef3c7;
            color: #92400e;
        }}

        .status-failed {{
            background: #fee2e2;
            color: #991b1b;
        }}

        /* ===== TEST CASE ===== */
        .test-case {{
            padding: 30px;
            border-bottom: 1px solid #f3f4f6;
        }}

        .test-case:last-child {{
            border-bottom: none;
        }}

        .test-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }}

        .test-number {{
            font-size: 14px;
            font-weight: 600;
            color: #667eea;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .test-result {{
            font-size: 24px;
        }}

        .verse-box {{
            background: #fafbfc;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}

        .verse-text {{
            margin-bottom: 12px;
        }}

        .verse-note {{
            font-size: 13px;
            color: #6b7280;
            font-style: italic;
            line-height: 1.5;
        }}

        /* ===== PHONEMES ===== */
        .phonemes-section {{
            margin-top: 20px;
        }}

        .section-title {{
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }}

        .phoneme-list {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            color: #1f2937;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }}

        /* ===== RULE APPLICATIONS ===== */
        .applications {{
            margin-top: 20px;
        }}

        .application-item {{
            background: #ecfdf5;
            border-left: 3px solid #10b981;
            padding: 15px;
            margin-bottom: 12px;
            border-radius: 6px;
        }}

        .app-rule-name {{
            font-weight: 600;
            color: #065f46;
            margin-bottom: 8px;
        }}

        .app-detail {{
            font-size: 13px;
            color: #047857;
            margin-bottom: 4px;
        }}

        .app-phonemes {{
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #065f46;
            margin-top: 8px;
        }}

        .app-acoustic {{
            font-size: 13px;
            color: #047857;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #a7f3d0;
        }}

        /* ===== ERROR BOX ===== */
        .error-box {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-left: 3px solid #ef4444;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
        }}

        .error-text {{
            color: #991b1b;
            font-size: 14px;
        }}

        /* ===== FOOTER ===== */
        .footer {{
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 14px;
        }}

        /* ===== PRINT STYLES ===== */
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}

            .container {{
                box-shadow: none;
                border-radius: 0;
            }}

            .print-instructions {{
                display: none;
            }}

            .rule-card {{
                page-break-inside: avoid;
                break-inside: avoid;
            }}

            .test-case {{
                page-break-inside: avoid;
                break-inside: avoid;
            }}

            .header {{
                background: #667eea !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            .stat-card {{
                break-inside: avoid;
            }}
        }}

        /* ===== RESPONSIVE ===== */
        @media (max-width: 768px) {{
            body {{
                padding: 0;
            }}

            .container {{
                border-radius: 0;
            }}

            .header {{
                padding: 30px 20px;
            }}

            .header h1 {{
                font-size: 24px;
            }}

            .stats-container {{
                grid-template-columns: 1fr;
                padding: 20px;
            }}

            .content {{
                padding: 20px;
            }}

            .arabic {{
                font-size: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <h1>Tajwīd Rule Validation Report</h1>
            <div class="subtitle">Expert Review - Symbolic Layer Implementation</div>
            <div class="date">Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</div>
        </div>

        <!-- STATISTICS SUMMARY -->
        <div class="stats-container">
            <div class="stat-card">
                <div class="stat-value verified">{total_verified}</div>
                <div class="stat-label">Fully Verified</div>
            </div>
            <div class="stat-card">
                <div class="stat-value partial">{total_partial}</div>
                <div class="stat-label">Partially Working</div>
            </div>
            <div class="stat-card">
                <div class="stat-value failed">{total_failed}</div>
                <div class="stat-label">Not Detected</div>
            </div>
            <div class="stat-card">
                <div class="stat-value rate">{verification_rate:.1f}%</div>
                <div class="stat-label">Verification Rate</div>
            </div>
        </div>

        <!-- PRINT INSTRUCTIONS -->
        <div class="print-instructions">
            <h3>📄 How to Save as PDF</h3>
            <p>
                <strong>Browser Method:</strong> Press Ctrl+P (Windows/Linux) or Cmd+P (Mac),
                then select "Save as PDF" as the destination. The report is optimized for printing
                with proper page breaks and formatting.
            </p>
        </div>

        <!-- MAIN CONTENT -->
        <div class="content">
'''

    # Group rules by category
    categories = {
        'Noon/Meem Sākinah': [],
        'Madd': [],
        'Qalqalah': [],
        'Pronunciation': []
    }

    for rule_name, status_info in rule_detection_status.items():
        category = RULE_METADATA.get(rule_name, {}).get('category', 'Other')
        categories[category].append((rule_name, status_info))

    # Generate HTML for each category
    for category_name, rules in categories.items():
        if not rules:
            continue

        # Calculate category stats
        cat_verified = sum(1 for _, s in rules if '✅' in s['status'])
        cat_total = len(rules)
        cat_rate = (cat_verified / cat_total * 100) if cat_total > 0 else 0

        html += f'''
            <div class="category">
                <div class="category-header">
                    <h2>{category_name}</h2>
                    <div class="category-stats">
                        {cat_verified}/{cat_total} rules verified ({cat_rate:.1f}%)
                    </div>
                </div>
'''

        # Generate HTML for each rule in category
        for rule_name, status_info in rules:
            metadata = RULE_METADATA.get(rule_name, {})
            arabic_name = metadata.get('arabic', '')
            english_name = rule_name.replace('_', ' ').title()

            status = status_info['status']
            status_class = 'verified' if '✅' in status else 'partial' if '⚠️' in status else 'failed'

            html += f'''
                <div class="rule-card">
                    <div class="rule-header">
                        <div class="rule-title">
                            <div class="rule-name">{english_name}</div>
                            <div class="arabic-small">{arabic_name}</div>
                        </div>
                        <div class="rule-status status-{status_class}">
                            {status} ({status_info['detected']}/{status_info['total']})
                        </div>
                    </div>
'''

            # Generate HTML for each test case
            test_results = results.get(rule_name, [])
            for i, test_result in enumerate(test_results, 1):
                result_icon = '✅' if test_result.get('detected') else '❌'

                html += f'''
                    <div class="test-case">
                        <div class="test-header">
                            <div class="test-number">Test Case {i}</div>
                            <div class="test-result">{result_icon}</div>
                        </div>

                        <div class="verse-box">
                            <div class="verse-text arabic">{test_result['text']}</div>
                            <div class="verse-note">{test_result['note']}</div>
                        </div>
'''

                # Show phonemes
                if 'phonemes' in test_result:
                    phonemes_str = ' '.join(test_result['phonemes'])
                    html += f'''
                        <div class="phonemes-section">
                            <div class="section-title">Phoneme Sequence</div>
                            <div class="phoneme-list">{phonemes_str}</div>
                        </div>
'''

                # Show rule applications
                if test_result.get('detected') and test_result.get('applications'):
                    html += '''
                        <div class="applications">
                            <div class="section-title">Rule Applications Detected</div>
'''
                    for app in test_result['applications']:
                        orig_phonemes = ' '.join([p.symbol for p in app.original_phonemes])
                        mod_phonemes = ' '.join([p.symbol for p in app.modified_phonemes])

                        html += f'''
                            <div class="application-item">
                                <div class="app-rule-name">{app.rule.name}</div>
                                <div class="app-detail">Position: {app.start_index} - {app.end_index}</div>
                                <div class="app-phonemes">
                                    Original: [{orig_phonemes}]<br>
                                    Modified: [{mod_phonemes}]
                                </div>
'''

                        # Show acoustic expectations
                        if app.acoustic_expectations:
                            ae = app.acoustic_expectations
                            html += '<div class="app-acoustic"><strong>Acoustic Expectations:</strong><br>'
                            if hasattr(ae, 'duration_ms'):
                                html += f'Duration: {ae.duration_ms}ms'
                            if hasattr(ae, 'ghunnah_present') and ae.ghunnah_present:
                                html += f' | Nasalization: Yes'
                            if hasattr(ae, 'prolonged') and ae.prolonged:
                                html += f' | Prolonged: Yes'
                            html += '</div>'

                        html += '</div>'

                    html += '</div>'

                # Show error if present
                if 'error' in test_result:
                    html += f'''
                        <div class="error-box">
                            <div class="error-text"><strong>Error:</strong> {test_result['error']}</div>
                        </div>
'''

                html += '                    </div>\n'

            html += '                </div>\n'

        html += '            </div>\n'

    # Footer
    html += f'''
        </div>

        <!-- FOOTER -->
        <div class="footer">
            <p><strong>Qur'anic Recitation Assessment System</strong></p>
            <p>Phase 1: Symbolic Layer - {total_rules} Tajwīd Rules Implemented</p>
            <p>Riwāyah: Ḥafṣ ʿan ʿĀṣim | {pipeline.tajweed_engine.rules.__len__()} rules loaded in engine</p>
            <p style="margin-top: 15px; font-size: 12px;">
                Generated on {datetime.now().strftime('%B %d, %Y')} |
                For expert validation review
            </p>
        </div>
    </div>
</body>
</html>
'''

    return html


if __name__ == "__main__":
    generate_html_report()
