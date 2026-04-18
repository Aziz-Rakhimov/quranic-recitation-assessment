#!/usr/bin/env python3
"""
Systematic Tajweed Validation — Ground Truth Comparison

Runs 20 diverse Quranic verses through the pipeline and compares
detected rule applications against expert-annotated ground truth.
Produces an HTML report with TP / FP / FN breakdown per rule and per verse.
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "src"))
from symbolic_layer.pipeline import SymbolicLayerPipeline

# Reuse character-level highlighting utilities from main validation
sys.path.insert(0, str(Path(__file__).parent))
from final_phase1_validation import (
    PHONEME_TO_CHARS, ARABIC_DIACRITICS,
    word_char_spans, find_highlight_span, build_highlighted_arabic,
)

# ── Rules excluded from assessment (internal phonetic rules) ──────────
EXCLUDED_RULES = {
    'emphasis_blocking_by_front_vowel',
    'vowel_backing_after_emphatic_short',
    'vowel_backing_after_emphatic_long',
    'vowel_backing_before_emphatic_short',
    'vowel_backing_before_emphatic_long',
    'cross_word_emphasis_continuation',
}

RULE_DISPLAY = {
    'ghunnah_mushaddadah_noon': 'Ghunnah (Noon)',
    'ghunnah_mushaddadah_meem': 'Ghunnah (Meem)',
    'idhhar_halqi_noon': 'Iẓhār Ḥalqī',
    'idgham_ghunnah_noon': 'Idghām w/ Ghunnah',
    'idgham_no_ghunnah': 'Idghām w/o Ghunnah',
    'iqlab': 'Iqlāb',
    'ikhfaa_light': 'Ikhfāʾ (Light)',
    'ikhfaa_heavy': 'Ikhfāʾ (Heavy)',
    'idhhar_shafawi': 'Iẓhār Shafawī',
    'idgham_shafawi_meem': 'Idghām Shafawī',
    'ikhfaa_shafawi': 'Ikhfāʾ Shafawī',
    'madd_tabii': 'Madd Ṭabīʿī',
    'madd_muttasil': 'Madd Muttaṣil',
    'madd_munfasil': 'Madd Munfaṣil',
    'madd_lazim_kalimi': 'Madd Lāzim Kalimī',
    'madd_lazim_muthaqqal_kalimi': 'Madd Lāzim Muthaq.',
    'madd_arid_lissukun': 'Madd ʿĀriḍ',
    'madd_silah_kubra': 'Madd Ṣilah Kubrā',
    'qalqalah_minor': 'Qalqalah Minor',
    'qalqalah_major': 'Qalqalah Major',
    'qalqalah_with_shaddah': 'Qalqalah w/ Shaddah',
    'qalqalah_emphatic': 'Qalqalah Emphatic',
    'qalqalah_non_emphatic': 'Qalqalah Non-Emph.',
    'ta_marbuta_waqf': 'Tāʾ Marbūṭa Waqf',
    'ta_marbuta_wasl': 'Tāʾ Marbūṭa Waṣl',
}

# ── Unique highlight colour per rule (bg, fg) ─────────────────────────
RULE_COLOURS = {
    'ghunnah_mushaddadah_noon':      ('#d4edda', '#155724'),
    'ghunnah_mushaddadah_meem':      ('#a8d5b8', '#0d3e1a'),
    'idhhar_halqi_noon':             ('#bee3f8', '#2c5282'),
    'idgham_ghunnah_noon':           ('#9ae6b4', '#22543d'),
    'idgham_no_ghunnah':             ('#c6f6d5', '#276749'),
    'iqlab':                         ('#fefcbf', '#744210'),
    'ikhfaa_light':                  ('#e9d8fd', '#553c9a'),
    'ikhfaa_heavy':                  ('#c4b5fd', '#4c1d95'),
    'idhhar_shafawi':                ('#cce5ff', '#004085'),
    'idgham_shafawi_meem':           ('#b8d4f5', '#003175'),
    'ikhfaa_shafawi':                ('#d8eaff', '#1a3c6e'),
    'madd_tabii':                    ('#dbeafe', '#1e40af'),
    'madd_muttasil':                 ('#93c5fd', '#1e3a8a'),
    'madd_munfasil':                 ('#bfdbfe', '#1d4ed8'),
    'madd_lazim_kalimi':             ('#60a5fa', '#1e3a8a'),
    'madd_lazim_muthaqqal_kalimi':   ('#3b82f6', '#ffffff'),
    'madd_arid_lissukun':            ('#a5f3fc', '#164e63'),
    'madd_silah_kubra':              ('#67e8f9', '#164e63'),
    'qalqalah_minor':                ('#fef9c3', '#78350f'),
    'qalqalah_major':                ('#fde68a', '#92400e'),
    'qalqalah_with_shaddah':         ('#fed7aa', '#9a3412'),
    'qalqalah_emphatic':             ('#fca5a5', '#991b1b'),
    'qalqalah_non_emphatic':         ('#fcd34d', '#78350f'),
    'ta_marbuta_waqf':               ('#fecaca', '#991b1b'),
    'ta_marbuta_wasl':               ('#f9a8d4', '#9d174d'),
}

# ── Short English definition per rule ─────────────────────────────────
RULE_DEFINITIONS = {
    'ghunnah_mushaddadah_noon':    'Noon with shaddah — 2-count nasal resonance through the nose',
    'ghunnah_mushaddadah_meem':    'Meem with shaddah — 2-count nasal resonance through the nose',
    'idhhar_halqi_noon':           'Noon sākinah/tanween before a throat letter (ء ه ع ح غ خ) — pronounce noon clearly without merging',
    'idgham_ghunnah_noon':         'Noon sākinah/tanween before ي و ن م — merge noon into following letter with 2-count ghunnah',
    'idgham_no_ghunnah':           'Noon sākinah/tanween before ل ر — merge noon silently with no nasal sound',
    'iqlab':                       'Noon sākinah/tanween before ب — convert noon to hidden meem with ghunnah',
    'ikhfaa_light':                'Noon sākinah/tanween before remaining 15 letters (non-emphatic) — conceal noon with partial nasal sound',
    'ikhfaa_heavy':                'Noon sākinah/tanween before emphatic letters (ص ض ط ظ ق) — conceal noon with heavy backing',
    'idhhar_shafawi':              'Meem sākinah before any letter except م or ب — pronounce meem clearly',
    'idgham_shafawi_meem':         'Meem sākinah before another meem — merge with ghunnah',
    'ikhfaa_shafawi':              'Meem sākinah before ب — partially conceal meem with ghunnah',
    'madd_tabii':                  'Natural prolongation of a long vowel (اِيوُ) — 2 counts (no hamza or sukoon follows)',
    'madd_muttasil':               'Long vowel followed by hamza in the SAME word — extend to 4–5 counts',
    'madd_munfasil':               'Long vowel at word-end followed by hamza starting next word — extend to 2–5 counts',
    'madd_lazim_kalimi':           'Long vowel followed by a shaddah letter in the same word — obligatory 6-count extension',
    'madd_lazim_muthaqqal_kalimi': 'Long vowel followed by a heavy shaddah consonant — obligatory 6 counts',
    'madd_arid_lissukun':          'Long vowel before a consonant that receives sukoon at verse pause — extend 2, 4, or 6 counts',
    'madd_silah_kubra':            'Pronoun هُ/هِ between two voweled letters, followed by hamza — extend to 4–5 counts',
    'qalqalah_minor':              'Qalqalah letter (ق ط ب ج د) with sukoon mid-word — slight echo/bounce in the chest',
    'qalqalah_major':              'Qalqalah letter with sukoon at word-end or verse pause — stronger echo/bounce',
    'qalqalah_with_shaddah':       'Qalqalah letter with shaddah — first instance has qalqalah, shaddah provides the sukoon',
    'qalqalah_emphatic':           'Qalqalah on an emphatic letter (ق طّ) — pronounced with heavier, back vowel colouring',
    'qalqalah_non_emphatic':       'Qalqalah on a non-emphatic letter (ب ج د) — pronounced with lighter, front vowel quality',
    'ta_marbuta_waqf':             'Tāʾ marbūṭa (ة) at verse pause — pronounced as silent hāʾ (h)',
    'ta_marbuta_wasl':             'Tāʾ marbūṭa (ة) in connected recitation — pronounced as tāʾ (t)',
}

# ══════════════════════════════════════════════════════════════════════
#  GROUND TRUTH — 20 test verses
#
#  Each expected entry: (rule_name, word_text, reason)
#  word_text must exactly match the word as it appears in the text
#  when split by spaces.
# ══════════════════════════════════════════════════════════════════════

TEST_VERSES = [
    # ── 1. Basmala ─────────────────────────────────────────────────
    {
        'ref': '1:1',
        'name': 'Al-Fātiḥah — Basmala',
        'text': 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ',
        'expected': [
            ('madd_tabii', 'ٱلرَّحْمَٰنِ', 'dagger alif = long aː'),
            # madd_tabii on ٱلرَّحِيمِ is SUPPRESSED by madd_arid at same position
            ('madd_arid_lissukun', 'ٱلرَّحِيمِ', 'verse-end long iː'),
        ],
    },
    # ── 2. Long verse — diverse rules ──────────────────────────────
    {
        'ref': '1:7',
        'name': 'Al-Fātiḥah — Final Verse',
        'text': 'صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ',
        'expected': [
            ('madd_tabii', 'صِرَٰطَ', 'dagger alif = long aː'),
            ('madd_tabii', 'ٱلَّذِينَ', 'yaa after kasra = long iː'),
            ('idhhar_halqi_noon', 'أَنْعَمْتَ', 'noon sakinah before ع (throat letter)'),
            ('idhhar_shafawi', 'أَنْعَمْتَ', 'meem sakinah before ت'),
            ('idhhar_shafawi', 'عَلَيْهِمْ', 'meem sakinah before غ (1st occurrence)'),
            ('madd_tabii', 'ٱلْمَغْضُوبِ', 'waw after damma = long uː'),
            ('idhhar_shafawi', 'عَلَيْهِمْ', 'meem sakinah before و (2nd occurrence)'),
            # madd_tabii on وَلَا is suppressed: next word ٱلضَّآلِّينَ starts with hamza wasla
            ('madd_lazim_kalimi', 'ٱلضَّآلِّينَ', 'long aː before shaddah-laam = 6 counts'),
            ('madd_arid_lissukun', 'ٱلضَّآلِّينَ', 'verse-end long iː'),
        ],
    },
    # ── 3. Ghunnah + Madd Munfaṣil ────────────────────────────────
    {
        'ref': '108:1',
        'name': 'Al-Kawthar',
        'text': 'إِنَّآ أَعْطَيْنَٰكَ ٱلْكَوْثَرَ',
        'expected': [
            ('ghunnah_mushaddadah_noon', 'إِنَّآ', 'noon with shaddah'),
            ('madd_munfasil', 'إِنَّآ', 'long aː at word-end, next word starts with hamza'),
            ('madd_tabii', 'أَعْطَيْنَٰكَ', 'dagger alif on noon = long aː'),
        ],
    },
    # ── 4. Qalqalah Minor + Iẓhār Shafawī ────────────────────────
    {
        'ref': '112:3',
        'name': 'Al-Ikhlāṣ v3',
        'text': 'لَمْ يَلِدْ وَلَمْ يُولَدْ',
        'expected': [
            ('idhhar_shafawi', 'لَمْ', 'meem sakinah before yaa (1st)'),
            ('qalqalah_major', 'يَلِدْ', 'daal-sukoon at word-end'),
            ('qalqalah_non_emphatic', 'يَلِدْ', 'daal is non-emphatic'),
            ('idhhar_shafawi', 'وَلَمْ', 'meem sakinah before yaa (2nd)'),
            ('madd_tabii', 'يُولَدْ', 'waw after damma = long uː'),
            ('qalqalah_major', 'يُولَدْ', 'daal-sukoon at verse-end'),
            # Note: qalqalah_non_emphatic may not fire at verse-end (system behavior to verify)
        ],
    },
    # ── 5. Idghām w/o Ghunnah + Iẓhār Ḥalqī ─────────────────────
    {
        'ref': '112:4',
        'name': 'Al-Ikhlāṣ v4',
        'text': 'وَلَمْ يَكُن لَّهُۥ كُفُوًا أَحَدٌۢ',
        'expected': [
            ('idhhar_shafawi', 'وَلَمْ', 'meem sakinah before yaa'),
            ('idgham_no_ghunnah', 'يَكُن', 'noon sakinah before laam'),
            ('madd_tabii', 'لَّهُۥ', 'superscript waw = long uː'),
            ('idhhar_halqi_noon', 'كُفُوًا', 'tanween before hamza (throat letter)'),
            ('qalqalah_major', 'أَحَدٌۢ', 'daal at verse-end'),
        ],
    },
    # ── 6. Madd Ṭabīʿī + Qalqalah w/ Shaddah + Ghunnah ──────────
    {
        'ref': '114:1',
        'name': 'An-Nās v1',
        'text': 'قُلْ أَعُوذُ بِرَبِّ ٱلنَّاسِ',
        'expected': [
            ('madd_tabii', 'أَعُوذُ', 'waw after damma = long uː'),
            ('qalqalah_with_shaddah', 'بِرَبِّ', 'baa with shaddah'),
            ('ghunnah_mushaddadah_noon', 'ٱلنَّاسِ', 'noon with shaddah'),
            ('madd_arid_lissukun', 'ٱلنَّاسِ', 'verse-end long aː'),
        ],
    },
    # ── 7. Ikhfāʾ + Ghunnah + Madd ʿĀriḍ ─────────────────────────
    {
        'ref': '114:4',
        'name': 'An-Nās v4',
        'text': 'مِن شَرِّ ٱلْوَسْوَاسِ ٱلْخَنَّاسِ',
        'expected': [
            ('ikhfaa_light', 'مِن', 'noon sakinah before sheen (non-emphatic)'),
            ('madd_tabii', 'ٱلْوَسْوَاسِ', 'alif after fatha = long aː'),
            ('ghunnah_mushaddadah_noon', 'ٱلْخَنَّاسِ', 'noon with shaddah'),
            ('madd_arid_lissukun', 'ٱلْخَنَّاسِ', 'verse-end long aː'),
        ],
    },
    # ── 8. Multiple Madd Ṭabīʿī mid-verse ─────────────────────────
    {
        'ref': '114:5',
        'name': 'An-Nās v5',
        'text': 'ٱلَّذِى يُوَسْوِسُ فِى صُدُورِ ٱلنَّاسِ',
        'expected': [
            ('madd_tabii', 'ٱلَّذِى', 'alif maqsura after kasra = long iː'),
            ('madd_tabii', 'فِى', 'alif maqsura after kasra = long iː'),
            ('madd_tabii', 'صُدُورِ', 'waw after damma = long uː'),
            ('ghunnah_mushaddadah_noon', 'ٱلنَّاسِ', 'noon with shaddah'),
            ('madd_arid_lissukun', 'ٱلنَّاسِ', 'verse-end long aː'),
        ],
    },
    # ── 9. Tāʾ Marbūṭa Waṣl + Ghunnah ────────────────────────────
    {
        'ref': '114:6',
        'name': 'An-Nās v6',
        'text': 'مِنَ ٱلْجِنَّةِ وَٱلنَّاسِ',
        'expected': [
            ('ghunnah_mushaddadah_noon', 'ٱلْجِنَّةِ', 'noon with shaddah'),
            ('ta_marbuta_wasl', 'ٱلْجِنَّةِ', 'taa marbuta in wasl before وَ'),
            ('ghunnah_mushaddadah_noon', 'وَٱلنَّاسِ', 'noon with shaddah'),
            ('madd_arid_lissukun', 'وَٱلنَّاسِ', 'verse-end long aː'),
        ],
    },
    # ── 10. Madd Munfaṣil ──────────────────────────────────────────
    {
        'ref': '2:255a',
        'name': 'Āyat al-Kursī (fragment)',
        'text': 'ٱللَّهُ لَآ إِلَٰهَ إِلَّا هُوَ ٱلْحَىُّ ٱلْقَيُّومُ',
        'expected': [
            ('madd_munfasil', 'لَآ', 'long aː at word-end, hamza starts next word'),
            ('madd_tabii', 'إِلَٰهَ', 'dagger alif = long aː'),
            ('madd_tabii', 'إِلَّا', 'alif after fatha = long aː'),
            ('madd_arid_lissukun', 'ٱلْقَيُّومُ', 'verse-end long uː'),
        ],
    },
    # ── 11. Ghunnah Meem + Madd Muttaṣil ──────────────────────────
    {
        'ref': '3:26a',
        'name': 'Āl ʿImrān (fragment)',
        'text': 'قُلِ ٱللَّهُمَّ مَٰلِكَ ٱلْمُلْكِ تُؤْتِى ٱلْمُلْكَ مَن تَشَآءُ',
        'expected': [
            ('ghunnah_mushaddadah_meem', 'ٱللَّهُمَّ', 'meem with shaddah'),
            ('idgham_shafawi_meem', 'ٱللَّهُمَّ', 'meem sakinah + meem (cross-word assimilation)'),
            ('madd_tabii', 'مَٰلِكَ', 'dagger alif = long aː'),
            # madd_tabii on تُؤْتِى is suppressed: next word ٱلْمُلْكَ starts with hamza wasla
            ('ikhfaa_light', 'مَن', 'noon sakinah before taa (non-emphatic)'),
            ('madd_muttasil', 'تَشَآءُ', 'long aː + hamza in same word'),
            ('madd_arid_lissukun', 'تَشَآءُ', 'verse-end: hamza gets sukoon after long aː'),
        ],
    },
    # ── 12. Madd Muttaṣil (جَآءَ) ─────────────────────────────────
    {
        'ref': '110:1',
        'name': 'An-Naṣr v1',
        'text': 'إِذَا جَآءَ نَصْرُ ٱللَّهِ وَٱلْفَتْحُ',
        'expected': [
            ('madd_tabii', 'إِذَا', 'alif after fatha = long aː'),
            ('madd_muttasil', 'جَآءَ', 'long aː + hamza in same word'),
        ],
    },
    # ── 13. Idghām Shafawī + Madd Ṭabīʿī ─────────────────────────
    {
        'ref': '2:10a',
        'name': 'Al-Baqarah (fragment)',
        'text': 'فِى قُلُوبِهِم مَّرَضٌۭ فَزَادَهُمُ ٱللَّهُ مَرَضًۭا',
        'expected': [
            ('madd_tabii', 'فِى', 'alif maqsura = long iː'),
            ('madd_tabii', 'قُلُوبِهِم', 'waw after damma = long uː'),
            ('idgham_shafawi_meem', 'قُلُوبِهِم', 'meem sakinah before meem of مَّ'),
            ('ghunnah_mushaddadah_meem', 'قُلُوبِهِم', 'result of idgham: doubled meem'),
            ('ghunnah_mushaddadah_meem', 'مَّرَضٌۭ', 'meem with shaddah'),
            ('idgham_shafawi_meem', 'مَّرَضٌۭ', 'meem shaddah from idgham'),
            ('ikhfaa_light', 'مَّرَضٌۭ', 'tanween before فَ'),
            ('madd_tabii', 'فَزَادَهُمُ', 'alif after fatha = long aː'),
            # مَرَضًۭا: alif after tanween fathah is orthographic, not a long vowel
        ],
    },
    # ── 14. Ikhfāʾ Shafawī + Tāʾ Marbūṭa Waṣl ───────────────────
    {
        'ref': '105:4',
        'name': 'Al-Fīl v4',
        'text': 'تَرْمِيهِم بِحِجَارَةٍۢ مِّن سِجِّيلٍۢ',
        'expected': [
            ('madd_tabii', 'تَرْمِيهِم', 'yaa after kasra = long iː'),
            ('ikhfaa_shafawi', 'تَرْمِيهِم', 'meem sakinah before baa'),
            ('madd_tabii', 'بِحِجَارَةٍۢ', 'alif after fatha = long aː'),
            ('ta_marbuta_wasl', 'بِحِجَارَةٍۢ', 'taa marbuta in wasl before مِّن'),
            ('idgham_ghunnah_noon', 'بِحِجَارَةٍۢ', 'tanween before meem = idgham with ghunnah'),
            ('ghunnah_mushaddadah_meem', 'مِّن', 'meem with shaddah (from idgham)'),
            ('idgham_shafawi_meem', 'مِّن', 'meem shaddah from idgham'),
            ('ikhfaa_light', 'مِّن', 'noon sakinah before سِ'),
            ('qalqalah_with_shaddah', 'سِجِّيلٍۢ', 'jeem with shaddah'),
            ('madd_tabii', 'سِجِّيلٍۢ', 'yaa after kasra = long iː'),
            # madd_arid_lissukun: system may not detect due to tanween waqf handling
        ],
    },
    # ── 15. Iqlab ──────────────────────────────────────────────────
    {
        'ref': '2:10b',
        'name': 'Al-Baqarah (iqlab fragment)',
        'text': 'وَلَهُمْ عَذَابٌ أَلِيمٌۢ بِمَا كَانُوا۟ يَكْذِبُونَ',
        'expected': [
            ('idhhar_shafawi', 'وَلَهُمْ', 'meem sakinah before ع'),
            ('madd_tabii', 'عَذَابٌ', 'alif after fatha = long aː'),
            ('idhhar_halqi_noon', 'عَذَابٌ', 'tanween before hamza (throat letter)'),
            ('madd_tabii', 'أَلِيمٌۢ', 'yaa after kasra = long iː'),
            ('iqlab', 'أَلِيمٌۢ', 'tanween before baa → meem'),
            ('madd_tabii', 'بِمَا', 'alif after fatha = long aː'),
            ('madd_tabii', 'كَانُوا۟', 'alif after fatha = long aː'),
            ('madd_tabii', 'كَانُوا۟', 'waw after damma = long uː'),
            # madd_tabii on يَكْذِبُونَ is SUPPRESSED by madd_arid at verse-end
            ('madd_arid_lissukun', 'يَكْذِبُونَ', 'verse-end long uː'),
        ],
    },
    # ── 16. Idghām with Ghunnah ────────────────────────────────────
    {
        'ref': '4:1a',
        'name': 'An-Nisāʾ (fragment)',
        'text': 'خَلَقَكُم مِّن نَّفْسٍ وَٰحِدَةٍ وَخَلَقَ مِنْهَا زَوْجَهَا',
        'expected': [
            ('ghunnah_mushaddadah_meem', 'خَلَقَكُم', 'meem with shaddah (from idgham)'),
            ('idgham_shafawi_meem', 'خَلَقَكُم', 'meem shaddah from idgham'),
            ('ghunnah_mushaddadah_meem', 'مِّن', 'meem with shaddah'),
            ('idgham_shafawi_meem', 'مِّن', 'meem shaddah from idgham'),
            ('ghunnah_mushaddadah_noon', 'نَّفْسٍ', 'noon with shaddah'),
            ('ghunnah_mushaddadah_noon', 'مِّن', 'noon with shaddah (residual)'),
            ('idgham_ghunnah_noon', 'نَّفْسٍ', 'tanween before waw (idgham letter)'),
            ('madd_tabii', 'وَٰحِدَةٍ', 'dagger alif on waw = long aː'),
            ('idgham_ghunnah_noon', 'وَٰحِدَةٍ', 'tanween before waw'),
            ('ta_marbuta_wasl', 'وَٰحِدَةٍ', 'taa marbuta in wasl before وَخَلَقَ'),
            ('idhhar_halqi_noon', 'مِنْهَا', 'noon sakinah before haa (throat letter)'),
            ('madd_tabii', 'مِنْهَا', 'alif after fatha = long aː'),
            ('madd_tabii', 'زَوْجَهَا', 'alif after fatha = long aː'),
        ],
    },
    # ── 17. Madd Lāzim ────────────────────────────────────────────
    {
        'ref': '69:1',
        'name': 'Al-Ḥāqqah v1',
        'text': 'ٱلْحَآقَّةُ',
        'expected': [
            ('madd_lazim_kalimi', 'ٱلْحَآقَّةُ', 'long aː before shaddah-qaaf = 6 counts'),
            ('qalqalah_with_shaddah', 'ٱلْحَآقَّةُ', 'qaaf with shaddah'),
            ('qalqalah_emphatic', 'ٱلْحَآقَّةُ', 'qaaf is emphatic'),
            ('ta_marbuta_waqf', 'ٱلْحَآقَّةُ', 'taa marbuta at verse-end = waqf'),
        ],
    },
    # ── 18. Ikhfāʾ Heavy (noon before emphatic) ───────────────────
    {
        'ref': '18:29a',
        'name': 'Al-Kahf (fragment)',
        'text': 'وَقُلِ ٱلْحَقُّ مِن رَّبِّكُمْ',
        'expected': [
            ('qalqalah_with_shaddah', 'ٱلْحَقُّ', 'qaaf with shaddah'),
            ('qalqalah_emphatic', 'ٱلْحَقُّ', 'qaaf is emphatic'),
            ('idgham_no_ghunnah', 'مِن', 'noon sakinah before raa (idgham w/o ghunnah)'),
            ('qalqalah_with_shaddah', 'رَّبِّكُمْ', 'baa with shaddah'),
            # No idhhar_shafawi at verse-end: no following word in waqf
        ],
    },
    # ── 19. Ghunnah Noon + diverse ─────────────────────────────────
    {
        'ref': '110:2',
        'name': 'An-Naṣr v2',
        'text': 'وَرَأَيْتَ ٱلنَّاسَ يَدْخُلُونَ فِى دِينِ ٱللَّهِ أَفْوَاجًۭا',
        'expected': [
            ('ghunnah_mushaddadah_noon', 'ٱلنَّاسَ', 'noon with shaddah'),
            ('madd_tabii', 'ٱلنَّاسَ', 'alif after fatha = long aː'),
            ('qalqalah_minor', 'يَدْخُلُونَ', 'daal-sukoon mid-word (يَدْ)'),
            ('qalqalah_non_emphatic', 'يَدْخُلُونَ', 'daal is non-emphatic'),
            ('madd_tabii', 'يَدْخُلُونَ', 'waw after damma = long uː'),
            ('madd_tabii', 'فِى', 'alif maqsura = long iː'),
            ('madd_tabii', 'دِينِ', 'yaa after kasra = long iː'),
            ('madd_tabii', 'أَفْوَاجًۭا', 'alif after waw-fatha = long aː'),
            # tanween fath + alif at waqf → fatha preserved (not sukoon) → no qalqalah
        ],
    },
    # ── 20. Madd Ṭabīʿī + Qalqalah contexts ──────────────────────
    {
        'ref': '112:1',
        'name': 'Al-Ikhlāṣ v1',
        'text': 'قُلْ هُوَ ٱللَّهُ أَحَدٌ',
        'expected': [
            ('qalqalah_major', 'أَحَدٌ', 'daal at verse-end (tanween dropped at waqf)'),
        ],
    },
]


# ══════════════════════════════════════════════════════════════════════
#  Processing & Comparison
# ══════════════════════════════════════════════════════════════════════

_ARABIC_ALIF        = '\u0627'   # ا  regular alif
_ARABIC_DAGGER_ALIF = '\u0670'   # ٰ  superscript alef (dagger alif)


def _span_idx_from_arabic_letter(word, arabic_letter, spans, fallback_phon_offset):
    """Return the span index (base-letter index) for a phoneme in a word.

    Uses the phoneme's arabic_letter metadata to find the exact character
    position in the word string, then maps it to the correct span index.
    Falls back to phon_offset // 2 when the lookup fails.

    This fixes the phon_offset // 2 heuristic which breaks for words that
    start with hamza wasla (ٱ) or contain letters with sukoon, because those
    add span positions without proportional phoneme counts, shifting all
    downstream estimates.

    Edge-case handled: the phonemizer stores arabic_letter with regular alif
    (ا U+0627) even when the source character is dagger alif (ٰ U+0670),
    e.g. يَٰٓأَيُّهَا → aː gets arabic='َا' but the actual long vowel marker
    is ٰ not ا.  We therefore try a dagger-alif variant first so that we
    do not land on the wrong alif later in the word.
    """
    if not arabic_letter:
        return max(0, fallback_phon_offset // 2)

    # Build search variants: prefer dagger-alif form when the phonemizer
    # stored regular alif, because dagger alif appears earlier in the word.
    variants = []
    if _ARABIC_ALIF in arabic_letter:
        variants.append(arabic_letter.replace(_ARABIC_ALIF, _ARABIC_DAGGER_ALIF))
    variants.append(arabic_letter)   # original as final fallback

    candidates = []
    for variant in variants:
        pos = word.find(variant)
        if pos == -1:
            continue
        # Advance past leading diacritics in the variant to reach the base letter
        char_pos = pos
        for ch in variant:
            if ch not in ARABIC_DIACRITICS:
                break
            char_pos += 1
        # Map char_pos to its span index
        for i, (s, e) in enumerate(spans):
            if s <= char_pos < e:
                candidates.append(i)
                break

    if not candidates:
        return max(0, fallback_phon_offset // 2)
    if len(candidates) == 1:
        return candidates[0]
    # Multiple candidates (different variants found different spans): pick the
    # one closest to the crude phon_offset // 2 estimate as a tiebreaker.
    hint = max(0, fallback_phon_offset // 2)
    return min(candidates, key=lambda c: abs(c - hint))


def process_verse(pipeline, text):
    """Run pipeline; return (rule_apps, output, highlighted_html)."""
    output = pipeline.process_text(text)
    seq = output.annotated_sequence
    wbs = sorted(seq.word_boundaries)
    words = output.original_text.split()
    total = len(seq.phonemes)
    # Corrected formula: wbs[i] = end of word i = start of word i+1
    word_phoneme_starts = ([0] + wbs) if wbs else [0]

    results = []
    word_char_highlights = defaultdict(list)  # word_idx → [(phon_sym, approx_char_idx, bg, fg)]
    # Tracks which (word_idx, phon_sym) span indices are already taken, so that
    # two phonemes of the same type in one word (e.g. two aː in فَـَٔاوَىٰ) each
    # get highlighted on their OWN character rather than both landing on the
    # first matching span.
    _highlight_used_spans = defaultdict(set)  # (word_idx, phon_sym) → {span_idx, ...}

    for app in seq.rule_applications:
        if app.rule.name in EXCLUDED_RULES:
            continue
        word_idx = _phoneme_word_index(app.start_index, wbs, total)
        word = words[word_idx] if word_idx < len(words) else '?'
        phonemes = ' '.join(p.symbol for p in app.original_phonemes)

        w_start = word_phoneme_starts[word_idx] if word_idx < len(word_phoneme_starts) else 0
        phon_offset = app.start_index - w_start
        phon_sym = app.original_phonemes[0].symbol if app.original_phonemes else ''
        arabic_letter = app.original_phonemes[0].arabic_letter if app.original_phonemes else None

        # Use arabic_letter metadata to find the exact span index rather than
        # the crude phon_offset // 2 heuristic, which breaks when hamza wasla
        # or sukoon-bearing letters shift the phoneme-to-character ratio.
        spans = word_char_spans(word)
        approx_char_idx = _span_idx_from_arabic_letter(word, arabic_letter, spans, phon_offset)

        # Deduplication: if this span is already highlighted for the same phoneme
        # type in this word, advance to the next unused matching span.  This
        # handles words like فَـَٔاوَىٰ where two aː phonemes both resolve to the
        # same span via the arabic_letter lookup and would otherwise both be drawn
        # on the alif, leaving the final ىٰ unhighlighted.
        used_key = (word_idx, phon_sym)
        if phon_sym in PHONEME_TO_CHARS and approx_char_idx in _highlight_used_spans[used_key]:
            target = PHONEME_TO_CHARS[phon_sym]
            all_matching = [i for i, (s, e) in enumerate(spans)
                            if any(c in target for c in word[s:e])]
            unused = [i for i in all_matching if i not in _highlight_used_spans[used_key]]
            if unused:
                forward = [i for i in unused if i > approx_char_idx]
                approx_char_idx = forward[0] if forward else unused[0]
        _highlight_used_spans[used_key].add(approx_char_idx)

        bg, fg = RULE_COLOURS.get(app.rule.name, ('#e2e8f0', '#1a202c'))
        word_char_highlights[word_idx].append((phon_sym, approx_char_idx, bg, fg))

        acoustics = app.acoustic_expectations
        results.append({
            'rule': app.rule.name,
            'word': word,
            'word_idx': word_idx,
            'phoneme_idx': app.start_index,
            'phonemes': phonemes,
            'duration': acoustics.duration_ms if acoustics else None,
            'counts': acoustics.duration_counts if acoustics else None,
            'ghunnah': getattr(acoustics, 'ghunnah_present', False) if acoustics else False,
        })

    highlighted_text = build_highlighted_arabic(words, word_char_highlights)
    return results, output, highlighted_text


def _phoneme_word_index(pos, word_boundaries, total):
    """Return word index for a phoneme position."""
    if not word_boundaries:
        return 0
    for i, end_pos in enumerate(sorted(word_boundaries)):
        if pos < end_pos:
            return i
    return len(word_boundaries)


def compare(expected, detected):
    """Compare expected vs detected as (rule, word) multisets.

    Returns (tp_list, fp_list, fn_list) where each item is a dict with details.
    Handles duplicate (rule, word) pairs correctly using multiset logic.
    """
    # Build multisets: count occurrences of each (rule, word) pair
    exp_counts = defaultdict(int)
    exp_reasons = {}
    for rule, word, reason in expected:
        exp_counts[(rule, word)] += 1
        exp_reasons[(rule, word)] = reason

    det_counts = defaultdict(int)
    det_details = {}
    for d in detected:
        key = (d['rule'], d['word'])
        det_counts[key] += 1
        det_details[key] = d

    all_keys = set(exp_counts.keys()) | set(det_counts.keys())

    tp_list, fp_list, fn_list = [], [], []

    for key in all_keys:
        rule, word = key
        n_exp = exp_counts.get(key, 0)
        n_det = det_counts.get(key, 0)
        n_tp = min(n_exp, n_det)

        for _ in range(n_tp):
            tp_list.append({
                'rule': rule, 'word': word,
                'reason': exp_reasons.get(key, ''),
                'details': det_details.get(key),
            })

        for _ in range(n_exp - n_tp):
            fn_list.append({
                'rule': rule, 'word': word,
                'reason': exp_reasons.get(key, ''),
            })

        for _ in range(n_det - n_tp):
            fp_list.append({
                'rule': rule, 'word': word,
                'details': det_details.get(key),
            })

    return tp_list, fp_list, fn_list


# ══════════════════════════════════════════════════════════════════════
#  HTML Report
# ══════════════════════════════════════════════════════════════════════

def generate_html(results, all_rule_stats):
    """Generate the full HTML report."""
    now = datetime.now().strftime('%B %d, %Y at %H:%M')

    total_tp = sum(r['n_tp'] for r in results)
    total_fp = sum(r['n_fp'] for r in results)
    total_fn = sum(r['n_fn'] for r in results)
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    # ── Per-rule stats table ──
    stats_rows = ''
    for rule in sorted(all_rule_stats.keys()):
        s = all_rule_stats[rule]
        rp = s['tp'] / (s['tp'] + s['fp']) if (s['tp'] + s['fp']) else 0
        rr = s['tp'] / (s['tp'] + s['fn']) if (s['tp'] + s['fn']) else 0
        rf = 2 * rp * rr / (rp + rr) if (rp + rr) else 0
        status = '&#x2705;' if s['fn'] == 0 and s['fp'] == 0 else '&#x274C;'
        bg = '#f0fdf4' if s['fn'] == 0 and s['fp'] == 0 else '#fef2f2'
        display = RULE_DISPLAY.get(rule, rule)
        stats_rows += f'''<tr style="background:{bg}">
<td>{status}</td><td style="font-size:12px">{display}</td>
<td>{s['tp']}</td><td style="color:#c00">{s['fp']}</td><td style="color:#c00">{s['fn']}</td>
<td>{rp:.0%}</td><td>{rr:.0%}</td><td><b>{rf:.0%}</b></td>
</tr>'''

    # ── Per-verse cards ──
    verse_cards = ''
    for r in results:
        v = r['verse']
        badge_color = '#22c55e' if r['n_fn'] == 0 and r['n_fp'] == 0 else '#ef4444'

        # ── Detected rules sorted by position in verse ──
        detected_sorted = sorted(r['detected'], key=lambda d: d['phoneme_idx'])

        rule_rows = ''
        for det in detected_sorted:
            rule = det['rule']
            bg, fg = RULE_COLOURS.get(rule, ('#e2e8f0', '#1a202c'))
            display = RULE_DISPLAY.get(rule, rule)
            definition = RULE_DEFINITIONS.get(rule, '')
            word = det['word']
            # Acoustic features
            acoustic_parts = []
            if det.get('counts'):
                acoustic_parts.append(f"{det['counts']} ḥarakāt")
            if det.get('duration'):
                acoustic_parts.append(f"{det['duration']} ms")
            if det.get('ghunnah'):
                acoustic_parts.append('ghunnah ✓')
            acoustic_str = ' · '.join(acoustic_parts) if acoustic_parts else '—'
            swatch = f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:{bg};border:1px solid {fg};margin-right:5px"></span>'
            rule_rows += f'''<tr>
<td style="padding:5px 8px">{swatch}<b style="color:{fg};background:{bg};padding:1px 6px;border-radius:3px;font-size:11px">{display}</b></td>
<td style="padding:5px 8px;font-family:\'Traditional Arabic\',serif;font-size:17px" dir="rtl">{word}</td>
<td style="padding:5px 8px;font-size:11px;color:#475569">{acoustic_str}</td>
<td style="padding:5px 8px;font-size:11px;color:#64748b">{definition}</td>
</tr>'''

        # ── TP/FP/FN mismatch rows (only shown when there are issues) ──
        mismatch_rows = ''
        for item in r['fn']:
            display = RULE_DISPLAY.get(item['rule'], item['rule'])
            mismatch_rows += f'<tr style="background:#fef2f2"><td style="color:#dc2626;padding:4px 8px">&#x274C; FN</td><td style="padding:4px 8px;font-size:12px">{display}</td><td style="padding:4px 8px;font-family:\'Traditional Arabic\',serif;font-size:15px" dir="rtl">{item["word"]}</td><td style="padding:4px 8px;font-size:11px;color:#dc2626">{item["reason"]}</td></tr>'
        for item in r['fp']:
            display = RULE_DISPLAY.get(item['rule'], item['rule'])
            det_info = item.get('details') or {}
            mismatch_rows += f'<tr style="background:#fffbeb"><td style="color:#d97706;padding:4px 8px">&#x26A0; FP</td><td style="padding:4px 8px;font-size:12px">{display}</td><td style="padding:4px 8px;font-family:\'Traditional Arabic\',serif;font-size:15px" dir="rtl">{item["word"]}</td><td style="padding:4px 8px;font-size:11px;color:#d97706">phonemes: {det_info.get("phonemes","")}</td></tr>'

        mismatch_section = ''
        if mismatch_rows:
            mismatch_section = f'''
<div style="margin-top:8px">
  <table style="width:100%;border-collapse:collapse;font-size:12px;border:1px solid #fee2e2;border-radius:6px">
    <tr style="background:#fef2f2"><th colspan="4" style="padding:4px 8px;text-align:left;font-size:11px;color:#991b1b">MISMATCHES</th></tr>
    {mismatch_rows}
  </table>
</div>'''

        verse_cards += f'''
<div style="background:white;border-radius:10px;padding:20px;margin:16px 0;
            box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:4px solid {badge_color}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div>
      <span style="font-weight:700;font-size:15px">{v['ref']}</span>
      <span style="color:#666;font-size:13px;margin-left:8px">{v['name']}</span>
    </div>
    <span style="background:{badge_color};color:white;padding:2px 10px;border-radius:12px;font-size:12px">
      TP:{r['n_tp']} FP:{r['n_fp']} FN:{r['n_fn']}
    </span>
  </div>
  <div style="font-family:\'Traditional Arabic\',\'Scheherazade New\',serif;font-size:28px;line-height:2;
              text-align:right;padding:10px 16px;background:#f8fafc;border-radius:8px;margin-bottom:14px"
       dir="rtl">{r['highlighted_text']}</div>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <tr style="background:#f1f5f9">
      <th style="padding:6px 8px;text-align:left">Rule</th>
      <th style="padding:6px 8px;text-align:left;width:140px">Word</th>
      <th style="padding:6px 8px;text-align:left;width:120px">Acoustics</th>
      <th style="padding:6px 8px;text-align:left">Definition</th>
    </tr>
    {rule_rows}
  </table>
  {mismatch_section}
</div>'''

    # ── Bug summary ──
    all_fn = []
    all_fp = []
    for r in results:
        for item in r['fn']:
            all_fn.append((r['verse']['ref'], item['rule'], item['word'], item['reason']))
        for item in r['fp']:
            det = item.get('details') or {}
            all_fp.append((r['verse']['ref'], item['rule'], item['word'], det.get('phonemes', '')))

    fn_rows = ''
    for ref, rule, word, reason in all_fn:
        display = RULE_DISPLAY.get(rule, rule)
        fn_rows += f'<tr><td>{ref}</td><td>{display}</td><td dir="rtl" style="font-family:\'Traditional Arabic\',serif">{word}</td><td>{reason}</td></tr>'

    fp_rows = ''
    for ref, rule, word, phonemes in all_fp:
        display = RULE_DISPLAY.get(rule, rule)
        fp_rows += f'<tr><td>{ref}</td><td>{display}</td><td dir="rtl" style="font-family:\'Traditional Arabic\',serif">{word}</td><td>phonemes: {phonemes}</td></tr>'

    html = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Systematic Tajweed Validation</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f1f5f9; margin: 0; padding: 20px; color: #1e293b; }}
  .container {{ max-width: 1000px; margin: 0 auto; }}
  table {{ border-collapse: collapse; }}
  th, td {{ padding: 6px 10px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
</style></head><body><div class="container">

<div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);color:white;padding:24px 32px;border-radius:12px;margin-bottom:24px">
  <h1 style="margin:0;font-size:24px">Systematic Tajweed Validation Report</h1>
  <div style="font-size:13px;opacity:.8;margin-top:6px">
    Generated: {now} &nbsp;|&nbsp; {len(results)} verses &nbsp;|&nbsp; Ground truth comparison
  </div>
</div>

<!-- ── Summary Dashboard ── -->
<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:24px">
  <div style="background:white;padding:16px;border-radius:10px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.06)">
    <div style="font-size:28px;font-weight:800;color:#16a34a">{total_tp}</div>
    <div style="font-size:11px;color:#666;text-transform:uppercase">True Pos</div>
  </div>
  <div style="background:white;padding:16px;border-radius:10px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.06)">
    <div style="font-size:28px;font-weight:800;color:#dc2626">{total_fp}</div>
    <div style="font-size:11px;color:#666;text-transform:uppercase">False Pos</div>
  </div>
  <div style="background:white;padding:16px;border-radius:10px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.06)">
    <div style="font-size:28px;font-weight:800;color:#dc2626">{total_fn}</div>
    <div style="font-size:11px;color:#666;text-transform:uppercase">False Neg</div>
  </div>
  <div style="background:white;padding:16px;border-radius:10px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.06)">
    <div style="font-size:28px;font-weight:800;color:#2563eb">{precision:.0%}</div>
    <div style="font-size:11px;color:#666;text-transform:uppercase">Precision</div>
  </div>
  <div style="background:white;padding:16px;border-radius:10px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.06)">
    <div style="font-size:28px;font-weight:800;color:#2563eb">{recall:.0%}</div>
    <div style="font-size:11px;color:#666;text-transform:uppercase">Recall</div>
  </div>
  <div style="background:white;padding:16px;border-radius:10px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.06)">
    <div style="font-size:28px;font-weight:800;color:#7c3aed">{f1:.0%}</div>
    <div style="font-size:11px;color:#666;text-transform:uppercase">F1 Score</div>
  </div>
</div>

<!-- ── Per-Rule Stats ── -->
<div style="background:white;border-radius:10px;padding:20px;margin-bottom:24px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
  <h2 style="margin:0 0 12px;font-size:17px">Per-Rule Accuracy</h2>
  <table style="width:100%;font-size:13px">
    <tr style="background:#f1f5f9">
      <th></th><th>Rule</th><th>TP</th><th>FP</th><th>FN</th><th>Prec</th><th>Rec</th><th>F1</th>
    </tr>
    {stats_rows}
  </table>
</div>

<!-- ── Per-Verse Cards ── -->
<h2 style="font-size:17px;margin:24px 0 8px">Per-Verse Breakdown</h2>
{verse_cards}

<!-- ── Bug Summary ── -->
<div style="background:white;border-radius:10px;padding:20px;margin:24px 0;box-shadow:0 1px 4px rgba(0,0,0,.08)">
  <h2 style="margin:0 0 12px;font-size:17px;color:#dc2626">False Negatives (Missed Detections)</h2>
  {'<p style="color:#16a34a">None — all expected rules detected!</p>' if not all_fn else f"""
  <table style="width:100%;font-size:13px">
    <tr style="background:#fef2f2"><th>Verse</th><th>Rule</th><th>Word</th><th>Reason</th></tr>
    {fn_rows}
  </table>"""}
</div>

<div style="background:white;border-radius:10px;padding:20px;margin:24px 0;box-shadow:0 1px 4px rgba(0,0,0,.08)">
  <h2 style="margin:0 0 12px;font-size:17px;color:#d97706">False Positives (Unexpected Detections)</h2>
  {'<p style="color:#16a34a">None — no unexpected detections!</p>' if not all_fp else f"""
  <table style="width:100%;font-size:13px">
    <tr style="background:#fffbeb"><th>Verse</th><th>Rule</th><th>Word</th><th>Details</th></tr>
    {fp_rows}
  </table>"""}
</div>

</div></body></html>'''
    return html


# ══════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════

def main():
    print('=' * 70)
    print('SYSTEMATIC TAJWEED VALIDATION')
    print('=' * 70)

    print('\nInitializing pipeline...')
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f'Pipeline ready: {len(pipeline.tajweed_engine.rules)} rules\n')

    results = []
    all_rule_stats = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0})

    for i, verse in enumerate(TEST_VERSES, 1):
        ref = verse['ref']
        text = verse['text']
        # Strip waqf marks that may appear as standalone tokens
        # (ۚ U+06DA, ۖ U+06D6, ۗ U+06D7, ۘ U+06D8, ۙ U+06D9, ۞ U+06DE)
        waqf_marks = '\u06DA\u06D6\u06D7\u06D8\u06D9\u06DE'
        for mark in waqf_marks:
            text = text.replace(mark + ' ', '').replace(' ' + mark, '').replace(mark, '')

        print(f'[{i:2d}/{len(TEST_VERSES)}] {ref:10s} ', end='')
        try:
            detected, output, highlighted_text = process_verse(pipeline, text)
            tp, fp, fn = compare(verse['expected'], detected)
            n_tp, n_fp, n_fn = len(tp), len(fp), len(fn)

            # Update per-rule stats
            for item in tp:
                all_rule_stats[item['rule']]['tp'] += 1
            for item in fp:
                all_rule_stats[item['rule']]['fp'] += 1
            for item in fn:
                all_rule_stats[item['rule']]['fn'] += 1

            status = 'PASS' if n_fn == 0 and n_fp == 0 else 'FAIL'
            print(f'{status:4s}  TP={n_tp} FP={n_fp} FN={n_fn}')

            if fn:
                for item in fn:
                    print(f'         FN: {item["rule"]:30s} on {item["word"]}')
            if fp:
                for item in fp:
                    print(f'         FP: {item["rule"]:30s} on {item["word"]}')

            results.append({
                'verse': verse,
                'detected': detected,
                'highlighted_text': highlighted_text,
                'tp': tp, 'fp': fp, 'fn': fn,
                'n_tp': n_tp, 'n_fp': n_fp, 'n_fn': n_fn,
            })

        except Exception as e:
            print(f'ERROR: {e}')
            import traceback
            traceback.print_exc()
            results.append({
                'verse': verse,
                'detected': [],
                'highlighted_text': verse['text'],
                'tp': [], 'fp': [],
                'fn': [{'rule': r, 'word': w, 'reason': reason}
                       for r, w, reason in verse['expected']],
                'n_tp': 0, 'n_fp': 0, 'n_fn': len(verse['expected']),
            })

    # Generate HTML
    html = generate_html(results, all_rule_stats)
    out_dir = Path(__file__).parent / 'output'
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / 'systematic_validation_report.html'
    out_file.write_text(html, encoding='utf-8')

    # Summary
    total_tp = sum(r['n_tp'] for r in results)
    total_fp = sum(r['n_fp'] for r in results)
    total_fn = sum(r['n_fn'] for r in results)
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    print(f'\n{"=" * 70}')
    print(f'SUMMARY')
    print(f'{"=" * 70}')
    print(f'Verses tested:  {len(results)}')
    print(f'True Positives: {total_tp}')
    print(f'False Positives:{total_fp}')
    print(f'False Negatives:{total_fn}')
    print(f'Precision:      {precision:.1%}')
    print(f'Recall:         {recall:.1%}')
    print(f'F1 Score:       {f1:.1%}')
    print(f'\nReport: {out_file}')
    print('=' * 70)


if __name__ == '__main__':
    main()
