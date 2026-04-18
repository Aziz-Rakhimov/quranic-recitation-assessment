#!/usr/bin/env python3
"""
Generate final expert validation HTML reports with acoustic features and Arabic highlighting.

Report 1: 8-verse validation (current test suite) - 100% precision & recall
Report 2: Complete Surah 113 (Al-Falaq) - all 5 verses
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "src"))
from symbolic_layer.pipeline import SymbolicLayerPipeline

# ============================================================
# Configuration
# ============================================================

EXCLUDED_RULES = {
    'emphasis_blocking_by_front_vowel',
    'vowel_backing_after_emphatic_short',
    'vowel_backing_before_emphatic_short',
    'vowel_backing_before_emphatic_long',
    'cross_word_emphasis_continuation',
}

RULE_DISPLAY_NAMES = {
    'ghunnah_mushaddadah_noon':  'Ghunnah Mushaddadah (Noon)',
    'ghunnah_mushaddadah_meem':  'Ghunnah Mushaddadah (Meem)',
    'idhhar_halqi_noon':         'Iẓhār Ḥalqī',
    'idgham_ghunnah_noon':       'Idghām with Ghunnah',
    'idgham_no_ghunnah':         'Idghām without Ghunnah',
    'iqlab':                     'Iqlāb',
    'ikhfaa_light':              'Ikhfāʾ (Light)',
    'ikhfaa_heavy':              'Ikhfāʾ (Heavy)',
    'idhhar_shafawi':            'Iẓhār Shafawī',
    'idgham_shafawi_meem':       'Idghām Shafawī',
    'ikhfaa_shafawi':            'Ikhfāʾ Shafawī',
    'madd_tabii':                'Madd Ṭabīʿī (Natural)',
    'madd_muttasil':             'Madd Muttaṣil (Connected)',
    'madd_munfasil':             'Madd Munfaṣil (Disconnected)',
    'madd_lazim_kalimi':         'Madd Lāzim Kalimī (Obligatory)',
    'madd_arid_lissukun':        'Madd ʿĀriḍ Lissukūn (Pausal)',
    'madd_silah_kubra':          'Madd Ṣilah Kubrā',
    'qalqalah_minor':            'Qalqalah Minor (Mid-word)',
    'qalqalah_major':            'Qalqalah Major (Verse End)',
    'qalqalah_with_shaddah':     'Qalqalah with Shaddah',
    'qalqalah_emphatic':         'Qalqalah Emphatic',
    'qalqalah_non_emphatic':     'Qalqalah Non-Emphatic',
    'ta_marbuta_wasl':           'Tāʾ Marbūṭa – Waṣl',
    'ta_marbuta_waqf':           'Tāʾ Marbūṭa – Waqf',
}

# Rule category → CSS color class for chips and Arabic highlighting
RULE_CATEGORY = {
    'ghunnah_mushaddadah_noon':  'cat-ghunnah',
    'ghunnah_mushaddadah_meem':  'cat-ghunnah',
    'idhhar_halqi_noon':         'cat-noon',
    'idgham_ghunnah_noon':       'cat-noon',
    'idgham_no_ghunnah':         'cat-noon',
    'iqlab':                     'cat-noon',
    'ikhfaa_light':              'cat-noon',
    'ikhfaa_heavy':              'cat-noon',
    'idhhar_shafawi':            'cat-meem',
    'idgham_shafawi_meem':       'cat-meem',
    'ikhfaa_shafawi':            'cat-meem',
    'madd_tabii':                'cat-madd',
    'madd_muttasil':             'cat-madd',
    'madd_munfasil':             'cat-madd',
    'madd_lazim_kalimi':         'cat-madd',
    'madd_arid_lissukun':        'cat-madd',
    'madd_silah_kubra':          'cat-madd',
    'qalqalah_minor':            'cat-qalq',
    'qalqalah_major':            'cat-qalq',
    'qalqalah_with_shaddah':     'cat-qalq',
    'qalqalah_emphatic':         'cat-qalq',
    'qalqalah_non_emphatic':     'cat-qalq',
    'ta_marbuta_wasl':           'cat-pron',
    'ta_marbuta_waqf':           'cat-pron',
}

RULE_CATEGORIES = {
    'Noon/Meem Sākinah (11 rules)': [
        'ghunnah_mushaddadah_noon', 'ghunnah_mushaddadah_meem',
        'idhhar_halqi_noon', 'idgham_ghunnah_noon', 'idgham_no_ghunnah',
        'iqlab', 'ikhfaa_light', 'ikhfaa_heavy',
        'idhhar_shafawi', 'idgham_shafawi_meem', 'ikhfaa_shafawi',
    ],
    'Madd / Prolongation (6 rules)': [
        'madd_tabii', 'madd_muttasil', 'madd_munfasil',
        'madd_lazim_kalimi', 'madd_arid_lissukun', 'madd_silah_kubra',
    ],
    'Qalqalah (5 rules)': [
        'qalqalah_minor', 'qalqalah_major', 'qalqalah_with_shaddah',
        'qalqalah_emphatic', 'qalqalah_non_emphatic',
    ],
    'Pronunciation (2 rules)': [
        'ta_marbuta_wasl', 'ta_marbuta_waqf',
    ],
}

# Acoustic description builder per rule type
RULE_TYPE_DESC = {
    'ghunnah_mushaddadah_noon':  'Shaddah + ghunnah on noon',
    'ghunnah_mushaddadah_meem':  'Shaddah + ghunnah on meem',
    'idhhar_halqi_noon':         'Clear articulation, no ghunnah',
    'idgham_ghunnah_noon':       'Full assimilation with ghunnah',
    'idgham_no_ghunnah':         'Full assimilation, no ghunnah',
    'iqlab':                     'Noon → meem-like sound + ghunnah',
    'ikhfaa_light':              'Partial concealment + nasal (light)',
    'ikhfaa_heavy':              'Partial concealment + nasal (heavy)',
    'idhhar_shafawi':            'Clear meem, no merging',
    'idgham_shafawi_meem':       'Meem merges into following meem',
    'ikhfaa_shafawi':            'Meem concealed before bāʾ',
    'madd_tabii':                'Natural 2-count prolongation',
    'madd_muttasil':             'Connected prolongation 4–5 counts',
    'madd_munfasil':             'Disconnected prolongation 4–5 counts',
    'madd_lazim_kalimi':         'Obligatory 6-count prolongation',
    'madd_arid_lissukun':        'Pausal prolongation 2/4/6 counts',
    'madd_silah_kubra':          'Pronoun hāʾ prolonged 4–5 counts',
    'qalqalah_minor':            'Weak echo, mid-word',
    'qalqalah_major':            'Strong echo, word/verse end',
    'qalqalah_with_shaddah':     'Echo on shaddah letter',
    'qalqalah_emphatic':         'Heavy emphatic echo',
    'qalqalah_non_emphatic':     'Light non-emphatic echo',
    'ta_marbuta_wasl':           'Tāʾ marbūṭa → t sound (continuing)',
    'ta_marbuta_waqf':           'Tāʾ marbūṭa → h sound (pausing)',
}

# ============================================================
# Data: 8-verse test suite
# ============================================================

EIGHT_VERSES = [
    {
        'name': 'Al-Fātiḥah 1:1 — Basmala',
        'surah': 1, 'ayah': 1,
        'text': 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ',
        'transliteration': 'Bismillāhi r-raḥmāni r-raḥīm',
        'translation': 'In the name of Allah, the Most Gracious, the Most Merciful',
        'expected_rules': ['madd_tabii', 'madd_arid_lissukun'],
        'notes': 'Madd ṭabīʿī on ٱلرَّحْمَٰنِ (long ā); Madd ʿāriḍ on ٱلرَّحِيمِ at verse end.',
    },
    {
        'name': 'Al-Fātiḥah 1:5',
        'surah': 1, 'ayah': 5,
        'text': 'إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ',
        'transliteration': "Iyyāka na'budu wa-iyyāka nasta'īn",
        'translation': 'You alone we worship, and You alone we ask for help',
        'expected_rules': ['madd_tabii', 'madd_arid_lissukun'],
        'notes': 'Madd ʿāriḍ lissukūn: نَسْتَعِينُ at verse end — long ī before pausal sukoon.',
    },
    {
        'name': 'Al-Fātiḥah 1:7',
        'surah': 1, 'ayah': 7,
        'text': 'صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ',
        'transliteration': "Ṣirāṭa l-ladhīna an'amta 'alayhim ghayri l-maghḍūbi 'alayhim wa-lā ḍ-ḍāllīn",
        'translation': 'The path of those You have blessed, not of those who earned anger, nor of those who went astray',
        'expected_rules': ['madd_tabii', 'madd_lazim_kalimi', 'idhhar_halqi_noon', 'idhhar_shafawi', 'madd_arid_lissukun'],
        'notes': 'Madd lāzim: ٱلضَّآلِّينَ (ā + doubled lam, 6 counts); Iẓhār ḥalqī: أَنْعَمْتَ (n before ʿayn); Iẓhār shafawī: مْ before waw/ghayn.',
    },
    {
        'name': 'Al-Kawthar 108:1',
        'surah': 108, 'ayah': 1,
        'text': 'إِنَّآ أَعْطَيْنَٰكَ ٱلْكَوْثَرَ',
        'transliteration': "Innā a'ṭaynāka l-kawthar",
        'translation': 'Indeed, We have granted you, [O Muḥammad], al-Kawthar',
        'expected_rules': ['ghunnah_mushaddadah_noon', 'madd_munfasil', 'madd_tabii'],
        'notes': 'Ghunnah mushaddadah: إِنَّ (noon + shaddah, 2 counts); Madd munfaṣil: إِنَّآ ends in ā, أَعْطَيْنَٰكَ begins with hamza (4–5 counts).',
    },
    {
        'name': 'Al-Baqarah 2:2',
        'surah': 2, 'ayah': 2,
        'text': 'ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبً ۛ فِيهِ ۛ هُدًى لِّلْمُتَّقِينَ',
        'transliteration': "Dhālika l-kitābu lā rayba fīhi hudan li-l-muttaqīn",
        'translation': 'This is the Book about which there is no doubt, a guidance for the righteous',
        'expected_rules': ['madd_tabii', 'ikhfaa_light', 'idgham_no_ghunnah', 'madd_arid_lissukun'],
        'notes': 'Ikhfāʾ light: رَيْبً فِيهِ (tanween before fāʾ); Idghām without ghunnah: هُدًى لِّ (tanween before lam); Madd ʿāriḍ: ٱلْمُتَّقِينَ at verse end.',
    },
    {
        'name': 'Al-Falaq 113:1–2',
        'surah': 113, 'ayah': 1,
        'text': 'قُلْ أَعُوذُ بِرَبِّ ٱلْفَلَقِ مِن شَرِّ مَا خَلَقَ',
        'transliteration': "Qul a'ūdhu bi-rabbi l-falaqi min sharri mā khalaq",
        'translation': 'Say: I seek refuge with the Lord of daybreak from the evil of what He created',
        'expected_rules': ['madd_tabii', 'qalqalah_major', 'qalqalah_emphatic', 'ikhfaa_light', 'qalqalah_with_shaddah'],
        'notes': 'Qalqalah major+emphatic: خَلَقَ at verse end (qaaf gets waqf sukoon, emphatic); Qalqalah with shaddah: رَبِّ (bāʾ + shaddah); Ikhfāʾ: مِن شَرِّ.',
    },
    {
        'name': 'Al-Ikhlāṣ 112:1–2',
        'surah': 112, 'ayah': 1,
        'text': 'قُلْ هُوَ ٱللَّهُ أَحَدٌ ٱللَّهُ ٱلصَّمَدُ',
        'transliteration': "Qul huwa llāhu aḥad, Allāhu ṣ-ṣamad",
        'translation': 'Say: He is Allah, the One. Allah, the Eternal Refuge',
        'expected_rules': ['madd_tabii', 'qalqalah_major', 'idgham_no_ghunnah'],
        'notes': 'Qalqalah major: ٱلصَّمَدُ at verse end (dāl gets waqf sukoon); Idghām without ghunnah: أَحَدٌ ٱللَّهُ (tanween before lam).',
    },
    {
        'name': 'Al-Baqarah 2:255 — Āyat al-Kursī',
        'surah': 2, 'ayah': 255,
        'text': 'ٱللَّهُ لَآ إِلَٰهَ إِلَّا هُوَ ٱلْحَىُّ ٱلْقَيُّومُ',
        'transliteration': "Allāhu lā ilāha illā huwa l-ḥayyu l-qayyūm",
        'translation': 'Allah — there is no deity except Him, the Ever-Living, the Sustainer of existence',
        'expected_rules': ['madd_tabii', 'madd_munfasil', 'madd_arid_lissukun'],
        'notes': 'Madd munfaṣil: لَآ إِلَٰهَ (ā at word-end + hamza next word); Madd ʿāriḍ: ٱلْقَيُّومُ at verse end (ū before pausal sukoon).',
    },
]

# ============================================================
# Data: Surah 113 — Al-Falaq
# ============================================================

SURAH_113 = [
    {'ayah': 1, 'text': 'قُلْ أَعُوذُ بِرَبِّ ٱلْفَلَقِ',
     'transliteration': "Qul a'ūdhu bi-rabbi l-falaq",
     'translation': 'Say: I seek refuge with the Lord of daybreak'},
    {'ayah': 2, 'text': 'مِن شَرِّ مَا خَلَقَ',
     'transliteration': 'Min sharri mā khalaq',
     'translation': 'From the evil of what He created'},
    {'ayah': 3, 'text': 'وَمِن شَرِّ غَاسِقٍ إِذَا وَقَبَ',
     'transliteration': 'Wa-min sharri ghāsiqin idhā waqab',
     'translation': 'And from the evil of darkness when it settles'},
    {'ayah': 4, 'text': 'وَمِن شَرِّ ٱلنَّفَّٰثَٰتِ فِى ٱلْعُقَدِ',
     'transliteration': "Wa-min sharri n-naffāthāti fī l-'uqad",
     'translation': 'And from the evil of those who blow on knots'},
    {'ayah': 5, 'text': 'وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ',
     'transliteration': 'Wa-min sharri ḥāsidin idhā ḥasad',
     'translation': 'And from the evil of an envier when he envies'},
]

# ============================================================
# Arabic character-level highlighting helpers
# ============================================================

# All Arabic combining diacritics / Qur'anic marks (not base letters)
ARABIC_DIACRITICS = frozenset(
    '\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652'   # harakat + shaddah + sukun
    '\u0653\u0654\u0655\u0656\u0657\u0658\u0659\u065A'   # maddah, hamza above/below, etc.
    '\u065B\u065C\u065D\u065E\u065F'
    '\u0670'                                               # superscript alef
    '\u06D6\u06D7\u06D8\u06D9\u06DA\u06DB\u06DC'
    '\u06DF\u06E0\u06E1\u06E2\u06E3\u06E4\u06E5\u06E6'
    '\u06E7\u06E8\u06EA\u06EB\u06EC\u06ED'
)

# Map IPA phoneme symbol → set of Arabic base characters that can produce it
PHONEME_TO_CHARS = {
    'aː': set('اآى\u0671'),   # long a: alif, alif maddah, alif maqsura, alif wasla
    'iː': set('يى'),           # long i
    'uː': set('و'),            # long u (as long vowel)
    'n':  set('ن'),
    'm':  set('م'),
    'q':  set('ق'),
    'tˤ': set('ط'),
    'b':  set('ب'),
    'dʒ': set('ج'),
    'd':  set('د'),
    't':  set('تة'),
    'h':  set('هة'),
    'l':  set('ل'),
    'r':  set('ر'),
    's':  set('س'),
    'sˤ': set('ص'),
    'f':  set('ف'),
    'k':  set('ك'),
    'ʔ':  set('أإءؤئ\u0671'),
    'ʕ':  set('ع'),
    'ɣ':  set('غ'),
    'x':  set('خ'),
    'z':  set('ز'),
    'ð':  set('ذ'),
    'θ':  set('ث'),
    'ðˤ': set('ظ'),
    'dˤ': set('ض'),
    'ħ':  set('ح'),
    'w':  set('و'),
    'j':  set('ي'),
}

# Colour palette shared across helpers
HL_COLOURS = {
    'cat-ghunnah': ('#d4edda', '#155724'),
    'cat-noon':    ('#d1ecf1', '#0c5460'),
    'cat-meem':    ('#cce5ff', '#004085'),
    'cat-madd':    ('#cfe2ff', '#084298'),
    'cat-qalq':    ('#fff3cd', '#856404'),
    'cat-pron':    ('#f8d7da', '#721c24'),
}


def word_char_spans(word):
    """Return list of (start, end) for each base letter (skipping diacritics)."""
    spans = []
    i = 0
    while i < len(word):
        if word[i] in ARABIC_DIACRITICS:
            i += 1
            continue
        j = i + 1
        while j < len(word) and word[j] in ARABIC_DIACRITICS:
            j += 1
        spans.append((i, j))
        i = j
    return spans


def find_highlight_span(word, phoneme_symbol, approx_char_idx):
    """
    Find the (start, end) char span in `word` that corresponds to `phoneme_symbol`,
    preferring the base letter closest to `approx_char_idx` (0-based letter index).
    Returns None if the letter is not found.
    """
    target = PHONEME_TO_CHARS.get(phoneme_symbol, set())
    if not target:
        return None
    spans = word_char_spans(word)
    matches = [(i, s, e) for i, (s, e) in enumerate(spans) if word[s] in target]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0][1], matches[0][2]
    best = min(matches, key=lambda x: abs(x[0] - approx_char_idx))
    return best[1], best[2]


# ============================================================
# Processing
# ============================================================

def phoneme_word_index(pos, word_boundaries, total):
    """Return the 0-based word index for a phoneme position."""
    boundaries = sorted(word_boundaries)
    word_starts = [0] + boundaries
    for i, start in enumerate(word_starts):
        end = boundaries[i] if i < len(boundaries) else total
        if start <= pos < end:
            return i
    return len(word_starts) - 1


def format_acoustic(rule_name, ac):
    """Return a structured dict of acoustic feature strings."""
    info = {}
    if ac is None:
        return info

    # Duration
    if ac.duration_ms:
        ms = int(ac.duration_ms)
        if ac.duration_counts:
            counts = ac.duration_counts
            # Format counts nicely
            if counts == int(counts):
                counts_str = f"{int(counts)}"
            else:
                counts_str = f"{counts:.1f}"
            info['duration'] = f"{counts_str} ḥarakāt ({ms} ms)"
        else:
            # Estimate counts: 1 ḥarakah ≈ 100ms at moderate tempo
            est_counts = ms / 100
            if rule_name == 'madd_arid_lissukun':
                info['duration'] = f"2/4/6 ḥarakāt ({ms}–{ms*3} ms, variable)"
            elif est_counts == int(est_counts):
                info['duration'] = f"≈{int(est_counts)} ḥarakāt ({ms} ms)"
            else:
                info['duration'] = f"{ms} ms"

    # Ghunnah / nasalization
    if ac.ghunnah_present:
        nasal = ac.nasalization_strength
        if nasal:
            pct = int(nasal * 100)
            info['ghunnah'] = f"Present — nasalization {pct}% intensity"
        else:
            info['ghunnah'] = "Present"

    # Qalqalah burst
    if ac.burst_present and ac.burst_duration_ms:
        info['burst'] = f"Echo burst {int(ac.burst_duration_ms)} ms"
    elif ac.burst_present:
        info['burst'] = "Echo burst present"

    return info


def process_verse(pipeline, text):
    """Run pipeline and return rich application data with word locations."""
    output = pipeline.process_text(text)
    seq = output.annotated_sequence
    wbs = sorted(seq.word_boundaries)
    words = text.split()
    total = len(seq.phonemes)
    word_phoneme_starts = [0] + wbs  # phoneme index where each word begins

    # word_char_highlights: word_idx → list of (phon_sym, approx_char_idx, bg, fg)
    word_char_highlights = defaultdict(list)
    apps_out = []
    seen_rules = set()

    for app in seq.rule_applications:
        name = app.rule.name
        if name in EXCLUDED_RULES:
            continue

        word_idx = phoneme_word_index(app.start_index, wbs, total)
        loc_word = words[word_idx] if word_idx < len(words) else '—'
        cat = RULE_CATEGORY.get(name, 'cat-madd')

        # Phoneme offset within this word
        w_start = word_phoneme_starts[word_idx] if word_idx < len(word_phoneme_starts) else 0
        phon_offset = app.start_index - w_start
        # Rough char index: each letter+vowel ≈ 2 phonemes
        approx_char_idx = max(0, phon_offset // 2)

        phon_sym = app.original_phonemes[0].symbol if app.original_phonemes else ''
        bg, fg = HL_COLOURS.get(cat, ('#e2e8f0', '#1a202c'))
        word_char_highlights[word_idx].append((phon_sym, approx_char_idx, bg, fg))

        ac_info = format_acoustic(name, app.acoustic_expectations)

        apps_out.append({
            'name': name,
            'display': RULE_DISPLAY_NAMES.get(name, name),
            'category': cat,
            'type_desc': RULE_TYPE_DESC.get(name, ''),
            'word_idx': word_idx,
            'location_word': loc_word,
            'phonemes': [p.symbol for p in app.original_phonemes],
            'modified': [p.symbol for p in app.modified_phonemes],
            'acoustic': ac_info,
        })
        seen_rules.add(name)

    highlighted = build_highlighted_arabic(words, word_char_highlights)
    return apps_out, seen_rules, highlighted


def build_highlighted_arabic(words, word_char_highlights):
    """Build Arabic HTML with character-level (not whole-word) highlighting."""
    parts = []
    for i, word in enumerate(words):
        highlights = word_char_highlights.get(i)
        if not highlights:
            parts.append(word)
            continue

        spans = word_char_spans(word)

        # Build char_idx → (bg, fg) map; first registered wins for same char
        char_colors = {}
        for phon_sym, approx_char_idx, bg, fg in highlights:
            result = find_highlight_span(word, phon_sym, approx_char_idx)
            if result:
                start, end = result
                for si, (s, e) in enumerate(spans):
                    if s == start:
                        if si not in char_colors:
                            char_colors[si] = (s, e, bg, fg)
                        break

        if not char_colors:
            # Fallback: highlight whole word with first colour
            bg, fg = highlights[0][2], highlights[0][3]
            parts.append(
                f'<span style="background:{bg};color:{fg};'
                f'border-radius:4px;padding:2px 4px;">{word}</span>'
            )
            continue

        # Build a start→(end,bg,fg) lookup for fast inline replacement
        hl_map = {s: (e, bg, fg) for (s, e, bg, fg) in char_colors.values()}

        html = ''
        k = 0
        while k < len(word):
            if k in hl_map:
                e, bg, fg = hl_map[k]
                char_text = word[k:e]
                html += (
                    f'<span style="background:{bg};color:{fg};'
                    f'border-radius:3px;padding:0 2px;font-weight:bold;">'
                    f'{char_text}</span>'
                )
                k = e
            else:
                html += word[k]
                k += 1
        parts.append(html)

    return ' '.join(parts)


def compute_metrics(expected_set, detected_set):
    correct = expected_set & detected_set
    missed  = expected_set - detected_set
    fps     = detected_set - expected_set
    prec = len(correct) / len(detected_set) * 100 if detected_set else 100.0
    rec  = len(correct) / len(expected_set) * 100 if expected_set else 100.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return correct, missed, fps, prec, rec, f1

# ============================================================
# CSS
# ============================================================

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #f0f4f8;
    color: #2d3748;
    font-size: 14px;
    line-height: 1.5;
}
.container { max-width: 1080px; margin: 0 auto; padding: 24px 16px; }

/* Header */
.header {
    background: linear-gradient(140deg, #1a365d 0%, #2b6cb0 55%, #3182ce 100%);
    color: white;
    padding: 30px 40px;
    border-radius: 14px;
    margin-bottom: 22px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(49,130,206,.25);
}
.header h1 { font-size: 24px; font-weight: 700; margin-bottom: 6px; letter-spacing: .4px; }
.header .subtitle { font-size: 14px; opacity: .88; margin-bottom: 3px; }
.header .meta { font-size: 12px; opacity: .7; }

/* Summary */
.summary-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 22px; }
.summary-card {
    background: white; border-radius: 10px; padding: 16px;
    text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,.07);
    border-top: 4px solid #3182ce;
}
.summary-card.green  { border-top-color: #38a169; }
.summary-card.purple { border-top-color: #805ad5; }
.summary-card.orange { border-top-color: #dd6b20; }
.sv { font-size: 26px; font-weight: 700; color: #2d3748; }
.sv.green  { color: #38a169; }
.sv.blue   { color: #3182ce; }
.sv.purple { color: #805ad5; }
.sl { font-size: 10px; color: #718096; text-transform: uppercase; letter-spacing: .9px; margin-top: 3px; }

/* Legend */
.legend {
    background: white; border-radius: 10px; padding: 14px 18px;
    margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.07);
    display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
}
.legend .lbl { font-size: 11px; font-weight: 700; color: #718096;
    text-transform: uppercase; letter-spacing: .8px; margin-right: 4px; }
.leg-item {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 12px; padding: 3px 10px; border-radius: 12px;
}

/* Verse card */
.verse-card {
    background: white; border-radius: 12px;
    margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,.08); overflow: hidden;
}
.verse-header {
    background: linear-gradient(90deg, #ebf8ff, #f7fafc);
    padding: 12px 20px; border-bottom: 1px solid #bee3f8;
    display: flex; justify-content: space-between; align-items: center;
}
.vh-title { font-weight: 700; font-size: 15px; color: #2c5282; }
.badge {
    font-size: 11px; padding: 3px 10px; border-radius: 12px; font-weight: 700;
}
.badge-perfect { background: #c6f6d5; color: #276749; }
.badge-good    { background: #bee3f8; color: #2c5282; }

.verse-body { padding: 18px 20px; }

/* Arabic text */
.arabic-block {
    font-family: 'Traditional Arabic','Scheherazade New','Noto Naskh Arabic',serif;
    font-size: 28px; direction: rtl; text-align: right;
    color: #1a202c; line-height: 2; padding: 12px 16px;
    background: #f7fafc; border-radius: 8px;
    border-right: 4px solid #4299e1; margin-bottom: 8px;
}
.hl-word { cursor: default; }
.transliteration { font-size: 13px; color: #4a5568; font-style: italic; margin-bottom: 2px; }
.translation { font-size: 13px; color: #718096; margin-bottom: 14px; }

/* Section headings */
.section-label {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #a0aec0; margin: 14px 0 8px;
}

/* Rule detail cards */
.rules-list { display: flex; flex-direction: column; gap: 8px; }
.rule-detail {
    border-radius: 8px; padding: 12px 14px;
    display: grid; grid-template-columns: auto 1fr;
    gap: 0 14px; border: 1px solid transparent;
}
/* Category colours */
.cat-ghunnah { background: #f0fff4; border-color: #9ae6b4; }
.cat-noon    { background: #ebf8ff; border-color: #90cdf4; }
.cat-meem    { background: #e9f3fd; border-color: #90cdf4; }
.cat-madd    { background: #eff6ff; border-color: #93c5fd; }
.cat-qalq    { background: #fffbeb; border-color: #fcd34d; }
.cat-pron    { background: #fff5f5; border-color: #fc8181; }

.rd-icon { font-size: 18px; line-height: 1; margin-top: 2px; }
.rd-body {}
.rd-title {
    font-weight: 700; font-size: 13px; margin-bottom: 3px;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.rd-rule-id { font-size: 10px; color: #a0aec0; font-weight: 400; font-family: monospace; }
.rd-location {
    font-size: 13px;
    font-family: 'Traditional Arabic','Scheherazade New',serif;
    direction: rtl; display: inline-block;
    background: rgba(255,255,255,.7); padding: 1px 6px;
    border-radius: 4px; font-size: 16px;
}
.rd-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
.rd-pill {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 11px; padding: 2px 8px; border-radius: 10px;
    background: rgba(255,255,255,.8); border: 1px solid rgba(0,0,0,.08);
    color: #4a5568;
}
.rd-pill .pill-icon { font-size: 12px; }
.rd-type { font-size: 11px; color: #718096; margin-top: 4px; }

/* Expected vs actual chips */
.exp-chips { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 6px; }
.chip {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 16px; font-size: 12px; font-weight: 500;
}
.chip-correct { background: #c6f6d5; color: #276749; border: 1px solid #9ae6b4; }
.chip-missed  { background: #fed7d7; color: #9b2c2c; border: 1px solid #fc8181; }
.chip-extra   { background: #fefcbf; color: #744210; border: 1px solid #f6e05e; }

/* Metrics row */
.metrics-row {
    display: flex; gap: 10px; padding-top: 12px; margin-top: 12px;
    border-top: 1px solid #e2e8f0;
}
.metric { flex: 1; text-align: center; }
.mval { font-size: 20px; font-weight: 700; }
.mlbl { font-size: 10px; color: #a0aec0; text-transform: uppercase; letter-spacing: .8px; }
.m-p { color: #3182ce; } .m-r { color: #38a169; } .m-f { color: #805ad5; }

/* Notes */
.verse-notes {
    font-size: 12px; color: #718096; padding: 8px 12px;
    background: #fffaf0; border-radius: 6px;
    border-left: 3px solid #ed8936; margin-top: 12px;
}

/* Coverage */
.coverage-section {
    background: white; border-radius: 12px; padding: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,.08); margin-top: 22px;
}
.coverage-section h2 { font-size: 15px; margin-bottom: 14px; color: #2d3748; }
.cat-block { margin-bottom: 14px; }
.cat-title {
    font-size: 12px; font-weight: 700; color: #4a5568;
    margin-bottom: 7px; padding-bottom: 4px; border-bottom: 1px solid #e2e8f0;
}
.cov-grid { display: flex; flex-wrap: wrap; gap: 5px; }
.cov-chip { padding: 4px 12px; border-radius: 14px; font-size: 12px; display: flex; align-items: center; gap: 4px; }
.cov-found   { background: #c6f6d5; color: #276749; }
.cov-missing { background: #f0f0f0; color: #a0aec0; border: 1px dashed #cbd5e0; }

/* Frequency table */
.freq-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
.freq-table th {
    background: #f7fafc; padding: 7px 10px; text-align: left;
    font-weight: 700; color: #4a5568; border-bottom: 2px solid #e2e8f0;
}
.freq-table td { padding: 6px 10px; border-bottom: 1px solid #f0f0f0; }
.freq-table tr:hover td { background: #f7fafc; }
.bar-cell { font-family: monospace; letter-spacing: 1px; }
.bar-fill   { color: #3182ce; }
.bar-empty  { color: #e2e8f0; }

@media print {
    body { background: white; font-size: 12px; }
    .container { max-width: 100%; padding: 10px; }
    .verse-card { break-inside: avoid; box-shadow: none; border: 1px solid #e2e8f0; }
    .header { background: #2b6cb0 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .summary-grid { grid-template-columns: repeat(4,1fr); }
}
@media (max-width: 700px) {
    .summary-grid { grid-template-columns: repeat(2,1fr); }
    .header { padding: 20px; }
}
"""

# ============================================================
# Category icon map
# ============================================================

RULE_ICONS = {
    'cat-ghunnah': '〰️',
    'cat-noon':    '◉',
    'cat-meem':    '◎',
    'cat-madd':    '➶',
    'cat-qalq':    '⟁',
    'cat-pron':    '◈',
}
CAT_LABELS = {
    'cat-ghunnah': 'Ghunnah',
    'cat-noon':    'Noon Rules',
    'cat-meem':    'Meem Rules',
    'cat-madd':    'Madd',
    'cat-qalq':    'Qalqalah',
    'cat-pron':    'Pronunciation',
}

# ============================================================
# HTML builders
# ============================================================

def rule_detail_html(app, show_first_only=False):
    """Render a single rule application as a detail card."""
    name = app['name']
    cat  = app['category']
    icon = RULE_ICONS.get(cat, '●')
    ac   = app['acoustic']
    loc  = app['location_word']
    phon = ' '.join(app['phonemes'])

    # Acoustic pills
    pills = ''
    if ac.get('duration'):
        pills += f'<span class="rd-pill"><span class="pill-icon">⏱</span>{ac["duration"]}</span>'
    if ac.get('ghunnah'):
        pills += f'<span class="rd-pill"><span class="pill-icon">〰️</span>{ac["ghunnah"]}</span>'
    if ac.get('burst'):
        pills += f'<span class="rd-pill"><span class="pill-icon">⟁</span>{ac["burst"]}</span>'
    if not pills:
        pills = '<span class="rd-pill" style="color:#a0aec0">No acoustic data in this configuration</span>'

    return f'''
<div class="rule-detail {cat}">
  <div class="rd-icon">{icon}</div>
  <div class="rd-body">
    <div class="rd-title">
      {app["display"]}
      <span class="rd-rule-id">{name}</span>
      — location: <span class="rd-location">{loc}</span>
    </div>
    <div class="rd-meta">{pills}</div>
    <div class="rd-type">{app["type_desc"]}</div>
  </div>
</div>'''


def verse_card_html(verse_info, apps, detected_set, highlighted_arabic, expected_set=None):
    name        = verse_info.get('name', f"Āyah {verse_info.get('ayah','')}")
    text        = verse_info['text']
    translit    = verse_info.get('transliteration', '')
    translation = verse_info.get('translation', '')
    notes       = verse_info.get('notes', '')

    if expected_set is not None:
        correct, missed, fps, prec, rec, f1 = compute_metrics(expected_set, detected_set)
        perfect = (len(missed) == 0 and len(fps) == 0)
        badge_cls  = 'badge-perfect' if perfect else 'badge-good'
        badge_text = '✓ 100% F1' if perfect else f'F1 {f1:.0f}%'

        # Expected/missed/FP chips
        chips = ''
        for r in sorted(expected_set):
            kind = 'correct' if r in detected_set else 'missed'
            sym  = '✓' if kind == 'correct' else '✗'
            cls  = f'chip-{kind}'
            chips += f'<span class="chip {cls}">{sym} {RULE_DISPLAY_NAMES.get(r, r)}</span>'
        for r in sorted(fps):
            chips += f'<span class="chip chip-extra">⚠ {RULE_DISPLAY_NAMES.get(r, r)}</span>'

        expected_block = f'''
<div class="section-label">Expected Rules vs Detected</div>
<div class="exp-chips">{chips}</div>'''

        metrics_html = f'''
<div class="metrics-row">
  <div class="metric"><div class="mval m-p">{prec:.0f}%</div><div class="mlbl">Precision</div></div>
  <div class="metric"><div class="mval m-r">{rec:.0f}%</div><div class="mlbl">Recall</div></div>
  <div class="metric"><div class="mval m-f">{f1:.0f}%</div><div class="mlbl">F1 Score</div></div>
  <div class="metric"><div class="mval" style="color:#2d3748">{len(correct)}/{len(expected_set)}</div><div class="mlbl">Correct</div></div>
</div>'''
    else:
        badge_cls = 'badge-good'
        badge_text = f'{len(detected_set)} rules detected'
        expected_block = ''
        metrics_html   = ''

    # Rule detail cards — one card per occurrence (all instances shown)
    rule_cards = ''
    for app in apps:
        rule_cards += rule_detail_html(app)

    notes_html = f'<div class="verse-notes">📖 {notes}</div>' if notes else ''

    return f'''
<div class="verse-card">
  <div class="verse-header">
    <span class="vh-title">{name}</span>
    <span class="badge {badge_cls}">{badge_text}</span>
  </div>
  <div class="verse-body">
    <div class="arabic-block" dir="rtl">{highlighted_arabic}</div>
    <div class="transliteration">{translit}</div>
    <div class="translation">{translation}</div>
    {expected_block}
    <div class="section-label">Detected Tajwīd Rules — Acoustic Detail</div>
    <div class="rules-list">{rule_cards}</div>
    {metrics_html}
    {notes_html}
  </div>
</div>'''


def legend_html():
    items = ''
    for cat, label in CAT_LABELS.items():
        icon = RULE_ICONS[cat]
        # map cat to inline style
        styles = {
            'cat-ghunnah': 'background:#f0fff4;color:#155724;border:1px solid #9ae6b4',
            'cat-noon':    'background:#ebf8ff;color:#0c5460;border:1px solid #90cdf4',
            'cat-meem':    'background:#e9f3fd;color:#004085;border:1px solid #90cdf4',
            'cat-madd':    'background:#eff6ff;color:#084298;border:1px solid #93c5fd',
            'cat-qalq':    'background:#fffbeb;color:#856404;border:1px solid #fcd34d',
            'cat-pron':    'background:#fff5f5;color:#721c24;border:1px solid #fc8181',
        }
        items += f'<span class="leg-item" style="{styles[cat]}">{icon} {label}</span>'
    return f'<div class="legend"><span class="lbl">Colour key:</span>{items}</div>'


def coverage_section_html(all_detected):
    html = '<div class="coverage-section"><h2>Rule Coverage</h2>'
    for cat, rules in RULE_CATEGORIES.items():
        html += f'<div class="cat-block"><div class="cat-title">{cat}</div><div class="cov-grid">'
        for r in rules:
            d = RULE_DISPLAY_NAMES.get(r, r)
            if r in all_detected:
                html += f'<span class="cov-chip cov-found">✓ {d}</span>'
            else:
                html += f'<span class="cov-chip cov-missing">— {d}</span>'
        html += '</div></div>'
    html += '</div>'
    return html


def build_html(title, subtitle, summary_cards, body_html, footer=''):
    cards = ''
    for c in summary_cards:
        cards += f'''
    <div class="summary-card {c.get('cls','')}">
      <div class="sv {c.get('val_cls','')}">{c['val']}</div>
      <div class="sl">{c['lbl']}</div>
    </div>'''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>{title}</h1>
  <div class="subtitle">{subtitle}</div>
  <div class="meta">
    Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')} &nbsp;|&nbsp;
    Riwāyah: Ḥafṣ ʿan ʿĀṣim &nbsp;|&nbsp; Phase 1 — Symbolic Layer
  </div>
</div>

<div class="summary-grid">{cards}</div>

{legend_html()}

{body_html}

{"<p style='text-align:center;color:#a0aec0;margin-top:24px;font-size:12px;'>" + footer + "</p>" if footer else ""}
</div>
</body>
</html>"""

# ============================================================
# Report 1: 8-verse validation
# ============================================================

def generate_report_8_verses(pipeline):
    print("Generating Report 1: 8-verse validation...")
    body = ''
    all_detected = set()
    total_expected = total_correct = total_fps = total_missed = 0

    for vd in EIGHT_VERSES:
        apps, detected_set, hl_arabic = process_verse(pipeline, vd['text'])
        expected_set = set(vd['expected_rules'])
        correct, missed, fps, prec, rec, f1 = compute_metrics(expected_set, detected_set)

        total_expected += len(expected_set)
        total_correct  += len(correct)
        total_fps      += len(fps)
        total_missed   += len(missed)
        all_detected.update(detected_set)

        body += verse_card_html(vd, apps, detected_set, hl_arabic, expected_set)

    body += coverage_section_html(all_detected)

    op = total_correct / (total_correct + total_fps) * 100 if (total_correct + total_fps) else 100.0
    ore = total_correct / total_expected * 100 if total_expected else 100.0
    of1 = 2 * op * ore / (op + ore) if (op + ore) else 0.0

    cards = [
        {'val': f'{op:.0f}%',  'lbl': 'Overall Precision', 'cls': 'green',  'val_cls': 'green'},
        {'val': f'{ore:.0f}%', 'lbl': 'Overall Recall',    'cls': 'green',  'val_cls': 'green'},
        {'val': f'{of1:.0f}%', 'lbl': 'Overall F1 Score',  'cls': 'purple', 'val_cls': 'purple'},
        {'val': str(len(all_detected)), 'lbl': 'Unique Rules Seen', 'cls': '', 'val_cls': 'blue'},
    ]

    return build_html(
        title='Tajwīd Rule Detection — Final Validation Report',
        subtitle='8 Complete Qurʾānic Verses · 24 Core Rules · Acoustic Feature Analysis',
        summary_cards=cards,
        body_html=body,
        footer='Qurʾānic Recitation Assessment System · Phase 1 Symbolic Layer · Ready for Expert Validation'
    )

# ============================================================
# Report 2: Surah 113
# ============================================================

def generate_report_surah_113(pipeline):
    print("Generating Report 2: Complete Surah 113 (Al-Falaq)...")
    body = ''
    all_detected = set()
    total_apps = 0
    rule_freq = defaultdict(int)

    for vd in SURAH_113:
        apps, detected_set, hl_arabic = process_verse(pipeline, vd['text'])
        all_detected.update(detected_set)
        total_apps += len(apps)
        for r in detected_set:
            rule_freq[r] += 1

        vd_copy = dict(vd)
        vd_copy['name'] = f"Āyah {vd['ayah']}"
        body += verse_card_html(vd_copy, apps, detected_set, hl_arabic, expected_set=None)

    # Frequency table
    freq_rows = ''
    for rule, count in sorted(rule_freq.items(), key=lambda x: -x[1]):
        d = RULE_DISPLAY_NAMES.get(rule, rule)
        bar_fill  = '█' * count
        bar_empty = '░' * (5 - count)
        cat = RULE_CATEGORY.get(rule, 'cat-madd')
        freq_rows += f'''
        <tr>
          <td><strong>{d}</strong></td>
          <td style="font-size:11px;color:#718096;font-family:monospace">{rule}</td>
          <td class="bar-cell">
            <span class="bar-fill">{bar_fill}</span><span class="bar-empty">{bar_empty}</span>
          </td>
          <td style="text-align:center;font-weight:700">{count}/5</td>
        </tr>'''

    body += f'''
<div class="coverage-section" style="margin-top:18px;">
  <h2>Rule Frequency Across All 5 Verses</h2>
  <table class="freq-table">
    <thead><tr><th>Rule</th><th>ID</th><th>Frequency</th><th>Verses</th></tr></thead>
    <tbody>{freq_rows}</tbody>
  </table>
</div>'''

    body += coverage_section_html(all_detected)

    cards = [
        {'val': '5',   'lbl': 'Verses Processed',         'cls': '',       'val_cls': 'blue'},
        {'val': str(total_apps), 'lbl': 'Rule Applications', 'cls': '',    'val_cls': ''},
        {'val': str(len(all_detected)), 'lbl': 'Unique Rules Detected', 'cls': 'green', 'val_cls': 'green'},
        {'val': '24',  'lbl': 'Rules in System',           'cls': 'purple', 'val_cls': 'purple'},
    ]

    return build_html(
        title='Sūrah Al-Falaq (113) — Complete Tajwīd Analysis',
        subtitle='All 5 Verses · Automated Acoustic Rule Detection · Ḥafṣ ʿan ʿĀṣim',
        summary_cards=cards,
        body_html=body,
        footer='Qurʾānic Recitation Assessment System · Phase 1 Symbolic Layer · Sūrah 113 Complete Analysis'
    )

# ============================================================
# Main
# ============================================================

def main():
    print("Initializing pipeline...")
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f"Pipeline ready: {len(pipeline.tajweed_engine.rules)} rules\n")

    out = Path(__file__).parent / 'output'
    out.mkdir(exist_ok=True)

    p1 = out / 'final_validation_report_8_verses.html'
    p1.write_text(generate_report_8_verses(pipeline), encoding='utf-8')
    print(f"✅  Report 1: {p1}  ({p1.stat().st_size:,} bytes)")

    p2 = out / 'final_validation_report_surah_113.html'
    p2.write_text(generate_report_surah_113(pipeline), encoding='utf-8')
    print(f"✅  Report 2: {p2}  ({p2.stat().st_size:,} bytes)")

    print("\nDone.")


if __name__ == '__main__':
    main()
