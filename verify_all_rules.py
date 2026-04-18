#!/usr/bin/env python3
"""
Comprehensive Rule Verification Script

Tests all 24 core Tajwīd rules (excluding Rāʾ) with specific test verses.
Generates a detailed validation report showing which rules are detected.
"""

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from symbolic_layer.pipeline import SymbolicLayerPipeline


# Define test verses for each rule type
TEST_VERSES = {
    # ============================================================
    # NOON/MEEM SAKINAH RULES (11 rules)
    # ============================================================

    # 1. Ghunnah Mushaddadah Noon (نّ)
    'ghunnah_mushaddadah_noon': [
        {'surah': 108, 'ayah': 1, 'text': 'إِنَّآ أَعْطَيْنَٰكَ', 'note': 'إِنَّ has noon with shaddah'},
        {'surah': 2, 'ayah': 25, 'text': 'وَبَشِّرِ ٱلَّذِينَ ءَامَنُوا۟ وَعَمِلُوا۟ ٱلصَّٰلِحَٰتِ أَنَّ لَهُمْ جَنَّٰتٍ', 'note': 'أَنَّ and جَنَّٰتٍ have noon with shaddah'},
    ],

    # 2. Ghunnah Mushaddadah Meem (مّ)
    'ghunnah_mushaddadah_meem': [
        {'surah': 2, 'ayah': 28, 'text': 'ثُمَّ يُمِيتُكُمْ ثُمَّ يُحْيِيكُمْ', 'note': 'ثُمَّ has meem with shaddah'},
        {'surah': 89, 'ayah': 15, 'text': 'فَأَمَّا ٱلْإِنسَٰنُ إِذَا', 'note': 'فَأَمَّا has meem with shaddah'},
    ],

    # 3. Idhhar Halqi - Noon before throat letters (ء ه ع ح غ خ)
    'idhhar_halqi_noon': [
        {'surah': 1, 'ayah': 7, 'text': 'صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ', 'note': 'أَنْعَمْتَ - noon before ع'},
        {'surah': 2, 'ayah': 6, 'text': 'إِنَّ ٱلَّذِينَ كَفَرُوا۟ سَوَآءٌ عَلَيْهِمْ', 'note': 'سَوَآءٌ عَلَيْهِمْ - tanween before ع'},
    ],

    # 4. Idgham with Ghunnah - Noon before ي و ن م
    'idgham_ghunnah_noon': [
        {'surah': 18, 'ayah': 16, 'text': 'فَأْوُۥٓا۟ إِلَى ٱلْكَهْفِ مِن وَرَآئِهِمْ', 'note': 'مِن وَرَآئِ - noon before waw'},
        {'surah': 2, 'ayah': 107, 'text': 'مِن وَلِىٍّ وَلَا نَصِيرٍ', 'note': 'مِن وَلِىٍّ - noon before waw'},
    ],

    # 5. Idgham WITHOUT Ghunnah - Noon before ل ر
    'idgham_no_ghunnah': [
        {'surah': 96, 'ayah': 15, 'text': 'كَلَّا لَئِن لَّمْ يَنتَهِ', 'note': 'لَئِن لَّمْ - noon before lam'},
        {'surah': 2, 'ayah': 2, 'text': 'هُدًى لِّلْمُتَّقِينَ', 'note': 'هُدًى لِّ - tanween before lam with idgham'},
    ],

    # 6. Iqlab - Noon before ب
    'iqlab': [
        {'surah': 2, 'ayah': 27, 'text': 'مِن بَعْدِ مِيثَٰقِهِۦ', 'note': 'مِن بَعْدِ - noon before baa'},
        {'surah': 96, 'ayah': 15, 'text': 'لَنَسْفَعًۢا بِٱلنَّاصِيَةِ', 'note': 'لَنَسْفَعًۢا بِ - tanween before baa'},
    ],

    # 7. Ikhfaa Light - Noon before light letters
    'ikhfaa_light': [
        {'surah': 2, 'ayah': 2, 'text': 'ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبً ۛ فِيهِ', 'note': 'رَيْبً فِيهِ - tanween before ف'},
        {'surah': 114, 'ayah': 4, 'text': 'مِن شَرِّ ٱلْوَسْوَاسِ', 'note': 'مِن شَرِّ - noon before ش'},
    ],

    # 8. Ikhfaa Heavy - Noon before emphatic letters (ط ظ ص ض)
    'ikhfaa_heavy': [
        {'surah': 23, 'ayah': 12, 'text': 'وَلَقَدْ خَلَقْنَا ٱلْإِنسَٰنَ مِن صَلْصَٰلٍ', 'note': 'مِن صَلْصَٰلٍ - noon before emphatic saad (ص)'},
        {'surah': 23, 'ayah': 33, 'text': 'مِن طِينٍ', 'note': 'مِن طِينٍ - noon before emphatic taa (ط)'},
    ],

    # 9. Idhhar Shafawi - Meem before non-meem/baa
    'idhhar_shafawi': [
        {'surah': 1, 'ayah': 7, 'text': 'غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ', 'note': 'عَلَيْهِمْ وَ - meem before waw'},
        {'surah': 2, 'ayah': 7, 'text': 'خَتَمَ ٱللَّهُ عَلَىٰ قُلُوبِهِمْ وَعَلَىٰ سَمْعِهِمْ', 'note': 'قُلُوبِهِمْ وَ - meem before waw'},
    ],

    # 10. Idgham Shafawi - Meem before meem
    'idgham_shafawi_meem': [
        {'surah': 2, 'ayah': 25, 'text': 'وَبَشِّرِ ٱلَّذِينَ ءَامَنُوا۟ وَعَمِلُوا۟ ٱلصَّٰلِحَٰتِ أَنَّ لَهُم مَّا', 'note': 'لَهُم مَّا - meem before meem'},
        {'surah': 30, 'ayah': 10, 'text': 'ثُمَّ كَانَ عَٰقِبَةَ', 'note': 'ثُمَّ has meem with shaddah (doubled meem)'},
    ],

    # 11. Ikhfaa Shafawi - Meem before baa
    'ikhfaa_shafawi': [
        {'surah': 105, 'ayah': 4, 'text': 'تَرْمِيهِم بِحِجَارَةٍ', 'note': 'تَرْمِيهِم بِ - meem before baa'},
        {'surah': 2, 'ayah': 233, 'text': 'وَٱللَّهُ بِمَا تَعْمَلُونَ بَصِيرٌ وَأَنتُمْ بِهِ', 'note': 'Check for meem before baa - تُمْ بِ pattern'},
    ],

    # ============================================================
    # MADD RULES (6 rules)
    # ============================================================

    # 1. Madd Tabii (natural - 2 counts)
    'madd_tabii': [
        {'surah': 1, 'ayah': 1, 'text': 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ', 'note': 'ٱلرَّحْمَٰنِ has long aa'},
        {'surah': 112, 'ayah': 1, 'text': 'قُلْ هُوَ ٱللَّهُ أَحَدٌ', 'note': 'هُوَ has long uu'},
    ],

    # 2. Madd Muttasil (connected - 4-5 counts, hamza in same word)
    'madd_muttasil': [
        {'surah': 2, 'ayah': 19, 'text': 'أَوْ كَصَيِّبٍ مِّنَ ٱلسَّمَآءِ', 'note': 'ٱلسَّمَآءِ - long aa before hamza in same word'},
        {'surah': 2, 'ayah': 61, 'text': 'فَٱدْعُ لَنَا رَبَّكَ جَآءَ بِمَا', 'note': 'جَآءَ - long aa before hamza in same word'},
    ],

    # 3. Madd Munfasil (disconnected - 2-5 counts, hamza in next word)
    'madd_munfasil': [
        {'surah': 51, 'ayah': 21, 'text': 'وَفِي أَنفُسِكُمْ', 'note': 'long ii in fii + hamza at start of anfusikum'},
        {'surah': 2, 'ayah': 13, 'text': 'قَالُوٓا۟ ءَأَمِنُ', 'note': 'qaaloo ends with long uu + next word starts with hamza - clear cross-word pattern'},
    ],

    # 4. Madd Lazim Kalimi (necessary - 6 counts, doubled letter after long vowel)
    'madd_lazim_kalimi': [
        {'surah': 1, 'ayah': 7, 'text': 'غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ', 'note': 'ٱلضَّآلِّينَ - aa before doubled lam'},
        {'surah': 69, 'ayah': 1, 'text': 'ٱلْحَآقَّةُ', 'note': 'ٱلْحَآقَّةُ - aa before doubled qaaf'},
    ],

    # 5. Madd Arid (accidental - 2/4/6 counts, at pause)
    'madd_arid_lissukun': [
        {'surah': 1, 'ayah': 5, 'text': 'إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ', 'note': 'نَسْتَعِينُ - long ii at verse end'},
        {'surah': 1, 'ayah': 2, 'text': 'ٱلرَّحْمَٰنِ ٱلرَّحِيمِ', 'note': 'ٱلرَّحِيمِ - ends with long ii + meem at verse end'},
    ],

    # 6. Madd Silah Kubra (major connection - 4-5 counts)
    'madd_silah_kubra': [
        {'surah': 18, 'ayah': 38, 'text': 'بِهِۦٓ أَسَفًا', 'note': 'bihi asafan - pronoun haa with kasra before hamza'},
        {'surah': 3, 'ayah': 73, 'text': 'لَهُۥٓ أَجْرٌ عِندَ', 'note': 'lahu ajr - pronoun haa with damma before hamza'},
    ],

    # ============================================================
    # QALQALAH RULES (5 rules)
    # ============================================================

    # 1. Qalqalah Minor (mid-word)
    'qalqalah_minor': [
        {'surah': 2, 'ayah': 245, 'text': 'وَٱللَّهُ يَقْبِضُ وَيَبْسُطُ', 'note': 'يَقْبِضُ and يَبْسُطُ have qalqalah with sukoon mid-word'},
        {'surah': 2, 'ayah': 191, 'text': 'وَٱقْتُلُوهُمْ حَيْثُ', 'note': 'وَٱقْتُلُوهُمْ has qaaf with sukoon mid-word'},
    ],

    # 2. Qalqalah Major (word/verse end)
    'qalqalah_major': [
        {'surah': 5, 'ayah': 15, 'text': 'قَدْ جَآءَكُمْ', 'note': 'قَدْ has daal with sukoon at word end'},
        {'surah': 23, 'ayah': 1, 'text': 'قَدْ أَفْلَحَ ٱلْمُؤْمِنُونَ', 'note': 'قَدْ أَفْلَحَ - daal with sukoon at word end'},
    ],

    # 3. Qalqalah with Shaddah
    'qalqalah_with_shaddah': [
        {'surah': 111, 'ayah': 1, 'text': 'تَبَّتْ يَدَآ أَبِى لَهَبٍ', 'note': 'تَبَّتْ has baa with shaddah (qalqalah + shaddah)'},
        {'surah': 54, 'ayah': 17, 'text': 'فَهَلْ مِن مُّدَّكِرٍ', 'note': 'مُدَّكِرٍ has daal (د) with shaddah - doubled daal is a qalqalah letter'},
    ],

    # 4. Qalqalah Emphatic
    'qalqalah_emphatic': [
        {'surah': 2, 'ayah': 245, 'text': 'وَٱللَّهُ يَقْبِضُ وَيَبْسُطُ', 'note': 'قَبْ and بَسْ have qalqalah in emphatic context'},
        {'surah': 2, 'ayah': 27, 'text': 'وَيَقْطَعُونَ مَا أَمَرَ', 'note': 'يَقْطَعُونَ - qaaf with sukoon before emphatic taa (ط), emphatic environment'},
    ],

    # 5. Qalqalah Non-Emphatic
    'qalqalah_non_emphatic': [
        {'surah': 112, 'ayah': 3, 'text': 'لَمْ يَلِدْ وَلَمْ يُولَدْ', 'note': 'يَلِدْ has daal at word-end mid-verse (non-emphatic, light kasra context)'},
        {'surah': 46, 'ayah': 31, 'text': 'وَيُجِبْ لَكُمْ مِن ذُنُوبِكُمْ', 'note': 'يُجِبْ - jeem with sukoon at word-end before lam (light letter), non-emphatic context'},
    ],

    # ============================================================
    # PRONUNCIATION RULES (2 rules)
    # ============================================================

    # 1. Tāʾ Marbūṭa - Waṣl (continuing)
    'ta_marbuta_wasl': [
        {'surah': 1, 'ayah': 1, 'text': 'رَحْمَةُ اللَّهِ', 'note': 'رَحْمَةُ اللَّهِ - ta marbuta (ة) continues to next word, pronounced as t'},
        {'surah': 16, 'ayah': 18, 'text': 'نِعْمَةَ ٱللَّهِ', 'note': 'نِعْمَةَ ٱللَّهِ - ta marbuta (ة) continues to next word in wasl'},
    ],

    # 2. Tāʾ Marbūṭa - Waqf (stopping)
    'ta_marbuta_waqf': [
        {'surah': 1, 'ayah': 1, 'text': 'جَنَّةٌ', 'note': 'جَنَّةٌ - ta marbuta (ة) at end, pronounced as h in pausal form'},
        {'surah': 2, 'ayah': 157, 'text': 'وَرَحْمَةٌ', 'note': 'وَرَحْمَةٌ - ta marbuta at end of phrase, waqf (stopping)'},
    ],
}


def verify_all_rules():
    """Main verification function."""
    print("=" * 80)
    print("COMPREHENSIVE TAJWĪD RULE VERIFICATION")
    print("=" * 80)
    print(f"\nTesting all 24 core rules (Rāʾ disabled for Phase 1)")
    print(f"Total test verses: {sum(len(verses) for verses in TEST_VERSES.values())}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Initialize pipeline (Rāʾ disabled)
    print("Initializing pipeline...")
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f"✅ Pipeline ready with {len(pipeline.tajweed_engine.rules)} rules loaded\n")

    # Track results
    results = defaultdict(list)
    rule_detection_status = {}

    # Process each rule type
    for rule_type, test_cases in TEST_VERSES.items():
        print(f"\n{'=' * 80}")
        print(f"Testing: {rule_type.upper().replace('_', ' ')}")
        print(f"{'=' * 80}")

        detected_count = 0

        for i, test_case in enumerate(test_cases, 1):
            text = test_case['text']
            note = test_case.get('note', '')

            print(f"\n  Test {i}: {text}")
            print(f"  Note: {note}")

            try:
                # Process the text
                output = pipeline.process_text(text)

                # Check if expected rule was detected
                rule_found = False
                matching_apps = []

                for app in output.annotated_sequence.rule_applications:
                    # Check if rule name contains the expected pattern
                    if rule_type in app.rule.name or app.rule.name in rule_type:
                        rule_found = True
                        matching_apps.append(app)

                if rule_found:
                    print(f"  ✅ DETECTED: {len(matching_apps)} application(s)")
                    detected_count += 1

                    # Show details
                    for app in matching_apps:
                        orig = ' '.join([p.symbol for p in app.original_phonemes])
                        mod = ' '.join([p.symbol for p in app.modified_phonemes])
                        print(f"     • {app.rule.name}")
                        print(f"       Position: {app.start_index}-{app.end_index}")
                        print(f"       Change: [{orig}] → [{mod}]")

                        # Show acoustic expectations
                        if app.acoustic_expectations:
                            if hasattr(app.acoustic_expectations, 'duration_ms'):
                                print(f"       Duration: {app.acoustic_expectations.duration_ms}ms")
                            if hasattr(app.acoustic_expectations, 'ghunnah_present') and app.acoustic_expectations.ghunnah_present:
                                print(f"       Ghunnah: Yes")
                else:
                    print(f"  ❌ NOT DETECTED")
                    # Show what was detected instead
                    if output.annotated_sequence.rule_applications:
                        print(f"     Other rules detected:")
                        for app in output.annotated_sequence.rule_applications[:3]:
                            print(f"       • {app.rule.name} ({app.rule.category.value})")

                # Store result
                results[rule_type].append({
                    'text': text,
                    'note': note,
                    'detected': rule_found,
                    'applications': matching_apps
                })

            except Exception as e:
                print(f"  ⚠️  ERROR: {e}")
                results[rule_type].append({
                    'text': text,
                    'note': note,
                    'detected': False,
                    'error': str(e)
                })

        # Determine status for this rule type
        if detected_count == len(test_cases):
            status = '✅ VERIFIED'
        elif detected_count > 0:
            status = f'⚠️  PARTIAL ({detected_count}/{len(test_cases)})'
        else:
            status = '❌ NOT DETECTED'

        rule_detection_status[rule_type] = {
            'status': status,
            'detected': detected_count,
            'total': len(test_cases)
        }

        print(f"\n  Status: {status}")

    # Generate summary report
    print("\n\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    # Categorize rules
    categories = {
        'Noon/Meem Sākinah (11 rules)': [
            'ghunnah_mushaddadah_noon', 'ghunnah_mushaddadah_meem',
            'idhhar_halqi_noon', 'idhhar_shafawi',
            'idgham_ghunnah_noon', 'idgham_no_ghunnah', 'idgham_shafawi_meem',
            'iqlab', 'ikhfaa_light', 'ikhfaa_heavy', 'ikhfaa_shafawi'
        ],
        'Madd/Prolongation (6 rules)': [
            'madd_tabii', 'madd_muttasil', 'madd_munfasil',
            'madd_lazim_kalimi', 'madd_arid_lissukun', 'madd_silah_kubra'
        ],
        'Qalqalah (5 rules)': [
            'qalqalah_minor', 'qalqalah_major', 'qalqalah_with_shaddah',
            'qalqalah_emphatic', 'qalqalah_non_emphatic'
        ],
        'Pronunciation (2 rules)': [
            'ta_marbuta_wasl', 'ta_marbuta_waqf'
        ]
    }

    total_verified = 0
    total_partial = 0
    total_failed = 0

    for category_name, rule_list in categories.items():
        print(f"\n{category_name}")
        print("-" * 80)

        for rule in rule_list:
            if rule in rule_detection_status:
                status_info = rule_detection_status[rule]
                status = status_info['status']
                detected = status_info['detected']
                total = status_info['total']

                # Format rule name nicely
                rule_display = rule.replace('_', ' ').title()

                print(f"  {status:<20} {rule_display:<40} ({detected}/{total})")

                if '✅' in status:
                    total_verified += 1
                elif '⚠️' in status:
                    total_partial += 1
                else:
                    total_failed += 1

    # Final statistics
    print("\n" + "=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)
    print(f"  ✅ Fully Verified:  {total_verified} rules")
    print(f"  ⚠️  Partially Working: {total_partial} rules")
    print(f"  ❌ Not Detected:    {total_failed} rules")
    print(f"  📊 Total Tested:    {total_verified + total_partial + total_failed} rules")

    verification_rate = (total_verified / 24) * 100 if 24 > 0 else 0
    print(f"\n  Verification Rate: {verification_rate:.1f}%")

    # Identify problem rules
    if total_failed > 0 or total_partial > 0:
        print("\n⚠️  RULES NEEDING ATTENTION:")
        print("-" * 80)
        for rule, status_info in rule_detection_status.items():
            if '❌' in status_info['status'] or '⚠️' in status_info['status']:
                rule_display = rule.replace('_', ' ').title()
                print(f"  • {rule_display}: {status_info['status']}")

    print("\n" + "=" * 80)

    return rule_detection_status


if __name__ == "__main__":
    verify_all_rules()
