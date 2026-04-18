#!/usr/bin/env python3
"""
Extended Tajweed Analysis Report
Surahs: 67 (×5), 78 (×5), 93, 97, 109, 112, 113, 114  +  8-verse validation test suite
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from symbolic_layer.pipeline import SymbolicLayerPipeline

sys.path.insert(0, str(Path(__file__).parent))
from systematic_validation import (
    process_verse, compare,
    RULE_DISPLAY, RULE_COLOURS, RULE_DEFINITIONS, EXCLUDED_RULES,
)
from surah_97_report import SURAH_97, strip_waqf
from surah_93_report import SURAH_93
from surah_109_report import SURAH_109, VERSE_1_7

# ── Surah 67 (first 5 ayahs) ──────────────────────────────────────────
SURAH_67 = {
    'number': 67,
    'name': 'Al-Mulk',
    'arabic_name': 'الملك',
    'meaning': 'The Sovereignty',
    'verses': [
        {
            'ayah': 1,
            'text': 'تَبَٰرَكَ ٱلَّذِى بِيَدِهِ ٱلْمُلْكُ وَهُوَ عَلَىٰ كُلِّ شَىْءٍ قَدِيرٌ',
            'transliteration': 'Tabāraka lladhī bi-yadihi l-mulku wa-huwa ʿalā kulli shayʾin qadīr',
            'translation': 'Blessed is He in whose hand is dominion, and He is over all things competent',
        },
        {
            'ayah': 2,
            'text': 'ٱلَّذِى خَلَقَ ٱلْمَوْتَ وَٱلْحَيَوٰةَ لِيَبْلُوَكُمْ أَيُّكُمْ أَحْسَنُ عَمَلًا وَهُوَ ٱلْعَزِيزُ ٱلْغَفُورُ',
            'transliteration': "Alladhī khalaqa l-mawta wa-l-ḥayāta li-yabluwakum ayyukum aḥsanu ʿamalan wa-huwa l-ʿazīzu l-ghafūr",
            'translation': 'He who created death and life to test you as to which of you is best in deed — and He is the Exalted in Might, the Forgiving',
        },
        {
            'ayah': 3,
            'text': 'ٱلَّذِى خَلَقَ سَبْعَ سَمَٰوَٰتٍ طِبَاقًا مَّا تَرَىٰ فِى خَلْقِ ٱلرَّحْمَٰنِ مِن تَفَٰوُتٍ فَٱرْجِعِ ٱلْبَصَرَ هَلْ تَرَىٰ مِن فُطُورٍ',
            'transliteration': "Alladhī khalaqa sabʿa samāwātin ṭibāqan mā tarā fī khalqi r-raḥmāni min tafāwutin fa-rjiʿi l-baṣara hal tarā min fuṭūr",
            'translation': 'He who created seven heavens in layers. You do not see in the creation of the Most Merciful any inconsistency. So return your vision; do you see any breaks?',
        },
        {
            'ayah': 4,
            'text': 'ثُمَّ ٱرْجِعِ ٱلْبَصَرَ كَرَّتَيْنِ يَنقَلِبْ إِلَيْكَ ٱلْبَصَرُ خَاسِئًا وَهُوَ حَسِيرٌ',
            'transliteration': "Thumma rjiʿi l-baṣara karratayni yanqalib ilayka l-baṣaru khāsiʾan wa-huwa ḥasīr",
            'translation': 'Then return your vision twice again. Your vision will return to you humbled while it is fatigued',
        },
        {
            'ayah': 5,
            'text': 'وَلَقَدْ زَيَّنَّا ٱلسَّمَآءَ ٱلدُّنْيَا بِمَصَٰبِيحَ وَجَعَلْنَٰهَا رُجُومًا لِّلشَّيَٰطِينِ وَأَعْتَدْنَا لَهُمْ عَذَابَ ٱلسَّعِيرِ',
            'transliteration': "Wa-laqad zayyannā s-samāʾa d-dunyā bi-maṣābīḥa wa-jaʿalnāhā rujūman li-sh-shayāṭīni wa-aʿtadnā lahum ʿadhāba s-saʿīr",
            'translation': 'And We have certainly beautified the nearest heaven with stars and have made from them what is thrown at the devils and have prepared for them the punishment of the Blaze',
        },
    ],
}

# ── Surah 78 (first 5 ayahs) ──────────────────────────────────────────
SURAH_78 = {
    'number': 78,
    'name': 'An-Nabaʾ',
    'arabic_name': 'النبأ',
    'meaning': 'The Tidings',
    'verses': [
        {
            'ayah': 1,
            'text': 'عَمَّ يَتَسَآءَلُونَ',
            'transliteration': 'ʿAmma yatasāʾalūn',
            'translation': 'About what are they asking one another?',
        },
        {
            'ayah': 2,
            'text': 'عَنِ ٱلنَّبَإِ ٱلْعَظِيمِ',
            'transliteration': "ʿAni n-nabaʾi l-ʿaẓīm",
            'translation': 'About the great news',
        },
        {
            'ayah': 3,
            'text': 'ٱلَّذِى هُمْ فِيهِ مُخْتَلِفُونَ',
            'transliteration': 'Alladhī hum fīhi mukhtalifūn',
            'translation': 'That over which they are in disagreement',
        },
        {
            'ayah': 4,
            'text': 'كَلَّا سَيَعْلَمُونَ',
            'transliteration': 'Kallā sayaʿlamūn',
            'translation': 'No! They are going to know.',
        },
        {
            'ayah': 5,
            'text': 'ثُمَّ كَلَّا سَيَعْلَمُونَ',
            'transliteration': 'Thumma kallā sayaʿlamūn',
            'translation': 'Then, no! They are going to know.',
        },
    ],
}

# ── Surah 112 ─────────────────────────────────────────────────────────
SURAH_112 = {
    'number': 112,
    'name': 'Al-Ikhlāṣ',
    'arabic_name': 'الإخلاص',
    'meaning': 'Sincerity / The Purity',
    'verses': [
        {
            'ayah': 1,
            'text': 'قُلْ هُوَ ٱللَّهُ أَحَدٌ',
            'transliteration': 'Qul huwa llāhu aḥad',
            'translation': 'Say, "He is Allah, [who is] One,"',
        },
        {
            'ayah': 2,
            'text': 'ٱللَّهُ ٱلصَّمَدُ',
            'transliteration': 'Allāhu ṣ-ṣamad',
            'translation': 'Allah, the Eternal Refuge.',
        },
        {
            'ayah': 3,
            'text': 'لَمْ يَلِدْ وَلَمْ يُولَدْ',
            'transliteration': "Lam yalid wa-lam yūlad",
            'translation': 'He neither begets nor is born,',
        },
        {
            'ayah': 4,
            'text': 'وَلَمْ يَكُن لَّهُۥ كُفُوًا أَحَدٌ',
            'transliteration': "Wa-lam yakun lahū kufuwan aḥad",
            'translation': 'Nor is there to Him any equivalent.',
        },
    ],
}

# ── Surah 113 ─────────────────────────────────────────────────────────
SURAH_113 = {
    'number': 113,
    'name': 'Al-Falaq',
    'arabic_name': 'الفلق',
    'meaning': 'The Daybreak',
    'verses': [
        {
            'ayah': 1,
            'text': 'قُلْ أَعُوذُ بِرَبِّ ٱلْفَلَقِ',
            'transliteration': 'Qul aʿūdhu bi-rabbi l-falaq',
            'translation': 'Say, "I seek refuge in the Lord of daybreak"',
        },
        {
            'ayah': 2,
            'text': 'مِن شَرِّ مَا خَلَقَ',
            'transliteration': 'Min sharri mā khalaq',
            'translation': 'From the evil of that which He created',
        },
        {
            'ayah': 3,
            'text': 'وَمِن شَرِّ غَاسِقٍ إِذَا وَقَبَ',
            'transliteration': 'Wa-min sharri ghāsiqin idhā waqab',
            'translation': 'And from the evil of darkness when it settles',
        },
        {
            'ayah': 4,
            'text': 'وَمِن شَرِّ ٱلنَّفَّٰثَٰتِ فِى ٱلْعُقَدِ',
            'transliteration': 'Wa-min sharri n-naffāthāti fī l-ʿuqad',
            'translation': 'And from the evil of the blowers in knots',
        },
        {
            'ayah': 5,
            'text': 'وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ',
            'transliteration': 'Wa-min sharri ḥāsidin idhā ḥasad',
            'translation': 'And from the evil of an envier when he envies.',
        },
    ],
}

# ── Surah 114 ─────────────────────────────────────────────────────────
SURAH_114 = {
    'number': 114,
    'name': 'An-Nās',
    'arabic_name': 'الناس',
    'meaning': 'Mankind',
    'verses': [
        {
            'ayah': 1,
            'text': 'قُلْ أَعُوذُ بِرَبِّ ٱلنَّاسِ',
            'transliteration': 'Qul aʿūdhu bi-rabbi n-nās',
            'translation': 'Say, "I seek refuge in the Lord of mankind,"',
        },
        {
            'ayah': 2,
            'text': 'مَلِكِ ٱلنَّاسِ',
            'transliteration': 'Maliki n-nās',
            'translation': 'The Sovereign of mankind.',
        },
        {
            'ayah': 3,
            'text': 'إِلَٰهِ ٱلنَّاسِ',
            'transliteration': 'Ilāhi n-nās',
            'translation': 'The God of mankind,',
        },
        {
            'ayah': 4,
            'text': 'مِن شَرِّ ٱلْوَسْوَاسِ ٱلْخَنَّاسِ',
            'transliteration': 'Min sharri l-waswāsi l-khannās',
            'translation': 'From the evil of the retreating whisperer',
        },
        {
            'ayah': 5,
            'text': 'ٱلَّذِى يُوَسْوِسُ فِى صُدُورِ ٱلنَّاسِ',
            'transliteration': 'Alladhī yuwaswisu fī ṣudūri n-nās',
            'translation': 'Who whispers [evil] into the breasts of mankind',
        },
        {
            'ayah': 6,
            'text': 'مِنَ ٱلْجِنَّةِ وَٱلنَّاسِ',
            'transliteration': 'Mina l-jinnati wa-n-nās',
            'translation': 'From among the jinn and mankind.',
        },
    ],
}

# ── 8-Verse validation test suite ─────────────────────────────────────
TEST_SUITE = [
    {
        'ref': '1:1',
        'name': 'Al-Fātiḥah — Basmala',
        'text': 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ',
        'expected': [
            ('madd_tabii',       'ٱلرَّحْمَٰنِ', 'dagger alif = long aː'),
            ('madd_arid_lissukun','ٱلرَّحِيمِ',  'verse-end long iː'),
        ],
    },
    {
        'ref': '1:7',
        'name': 'Al-Fātiḥah — Final Verse',
        'text': 'صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ',
        'expected': [
            ('madd_tabii',        'صِرَٰطَ',         'dagger alif = long aː'),
            ('madd_tabii',        'ٱلَّذِينَ',        'yaa after kasra = long iː'),
            ('idhhar_halqi_noon', 'أَنْعَمْتَ',       'noon sakinah before ع'),
            ('idhhar_shafawi',    'أَنْعَمْتَ',       'meem sakinah before ت'),
            ('idhhar_shafawi',    'عَلَيْهِمْ',       'meem sakinah before غ'),
            ('madd_tabii',        'ٱلْمَغْضُوبِ',     'waw after damma = long uː'),
            ('idhhar_shafawi',    'عَلَيْهِمْ',       'meem sakinah before و'),
            ('madd_lazim_kalimi', 'ٱلضَّآلِّينَ',     'long aː before shaddah-laam'),
            ('madd_arid_lissukun','ٱلضَّآلِّينَ',     'verse-end long iː'),
        ],
    },
    {
        'ref': '108:1',
        'name': 'Al-Kawthar',
        'text': 'إِنَّآ أَعْطَيْنَٰكَ ٱلْكَوْثَرَ',
        'expected': [
            ('ghunnah_mushaddadah_noon', 'إِنَّآ',       'noon with shaddah'),
            ('madd_munfasil',            'إِنَّآ',       'long aː, next word starts with hamza'),
            ('madd_tabii',               'أَعْطَيْنَٰكَ','dagger alif on noon = long aː'),
        ],
    },
    {
        'ref': '112:3',
        'name': 'Al-Ikhlāṣ v3',
        'text': 'لَمْ يَلِدْ وَلَمْ يُولَدْ',
        'expected': [
            ('idhhar_shafawi',    'لَمْ',      'meem sakinah before yaa (1st)'),
            ('qalqalah_major',    'يَلِدْ',    'daal-sukoon at word-end'),
            ('qalqalah_non_emphatic','يَلِدْ', 'daal is non-emphatic'),
            ('idhhar_shafawi',    'وَلَمْ',    'meem sakinah before yaa (2nd)'),
            ('madd_tabii',        'يُولَدْ',   'waw after damma = long uː'),
            ('qalqalah_major',    'يُولَدْ',   'daal-sukoon at verse-end'),
        ],
    },
    {
        'ref': '114:1',
        'name': 'An-Nās v1',
        'text': 'قُلْ أَعُوذُ بِرَبِّ ٱلنَّاسِ',
        'expected': [
            ('madd_tabii',              'أَعُوذُ',    'waw after damma = long uː'),
            ('qalqalah_with_shaddah',   'بِرَبِّ',    'baa with shaddah'),
            ('ghunnah_mushaddadah_noon', 'ٱلنَّاسِ',  'noon with shaddah'),
            ('madd_arid_lissukun',      'ٱلنَّاسِ',  'verse-end long aː'),
        ],
    },
    {
        'ref': '114:5',
        'name': 'An-Nās v5',
        'text': 'ٱلَّذِى يُوَسْوِسُ فِى صُدُورِ ٱلنَّاسِ',
        'expected': [
            ('madd_tabii', 'ٱلَّذِى',  'alif maqsura = long iː'),
            ('madd_tabii', 'فِى',      'alif maqsura = long iː'),
            ('madd_tabii', 'صُدُورِ',  'waw after damma = long uː'),
            ('ghunnah_mushaddadah_noon','ٱلنَّاسِ', 'noon with shaddah'),
            ('madd_arid_lissukun',     'ٱلنَّاسِ', 'verse-end long aː'),
        ],
    },
    {
        'ref': '110:1',
        'name': 'An-Naṣr v1',
        'text': 'إِذَا جَآءَ نَصْرُ ٱللَّهِ وَٱلْفَتْحُ',
        'expected': [
            ('madd_tabii',    'إِذَا',  'alif after fatha = long aː'),
            ('madd_muttasil', 'جَآءَ', 'long aː + hamza in same word'),
        ],
    },
    {
        'ref': '112:4',
        'name': 'Al-Ikhlāṣ v4',
        'text': 'وَلَمْ يَكُن لَّهُۥ كُفُوًا أَحَدٌۢ',
        'expected': [
            ('idhhar_shafawi',    'وَلَمْ',  'meem sakinah before yaa'),
            ('idgham_no_ghunnah', 'يَكُن',   'noon sakinah before laam'),
            ('madd_tabii',        'لَّهُۥ',  'superscript waw = long uː'),
            ('idhhar_halqi_noon', 'كُفُوًا', 'tanween before hamza'),
            ('qalqalah_major',    'أَحَدٌۢ', 'daal at verse-end'),
        ],
    },
]

# ── Surah sections to render (numerical order) ────────────────────────
SURAH_SECTIONS = [
    (SURAH_67,  SURAH_67['verses']),
    (SURAH_78,  SURAH_78['verses']),
    (SURAH_93,  SURAH_93['verses']),
    (SURAH_97,  SURAH_97['verses']),
    (SURAH_109, SURAH_109['verses'] + [VERSE_1_7]),
    (SURAH_112, SURAH_112['verses']),
    (SURAH_113, SURAH_113['verses']),
    (SURAH_114, SURAH_114['verses']),
]

SURAH_SUBTITLES = {
    67:  'Al-Mulk · Ayahs 1–5',
    78:  'An-Nabaʾ · Ayahs 1–5',
    109: 'Al-Kāfirūn · with Al-Fātiḥah 1:7',
}


# ── Shared HTML helpers ────────────────────────────────────────────────

def _verse_card(v, r, border_color='#2563eb'):
    detected_sorted = sorted(r['detected'], key=lambda d: d['phoneme_idx'])
    n_rules = len(detected_sorted)
    rule_rows = ''
    for det in detected_sorted:
        rule = det['rule']
        bg, fg = RULE_COLOURS.get(rule, ('#e2e8f0', '#1a202c'))
        display = RULE_DISPLAY.get(rule, rule)
        definition = RULE_DEFINITIONS.get(rule, '')
        word = det['word']
        parts = []
        if det.get('counts'):
            parts.append(f"{det['counts']} ḥarakāt")
        if det.get('duration'):
            parts.append(f"{det['duration']} ms")
        if det.get('ghunnah'):
            parts.append('ghunnah ✓')
        acoustic = ' · '.join(parts) if parts else '—'
        swatch = (f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
                  f'background:{bg};border:1px solid {fg};margin-right:5px"></span>')
        rule_rows += (
            f'<tr>'
            f'<td style="padding:5px 8px">{swatch}'
            f'<b style="color:{fg};background:{bg};padding:1px 6px;border-radius:3px;font-size:11px">{display}</b></td>'
            f'<td style="padding:5px 8px;font-family:\'Traditional Arabic\',serif;font-size:17px" dir="rtl">{word}</td>'
            f'<td style="padding:5px 8px;font-size:11px;color:#475569">{acoustic}</td>'
            f'<td style="padding:5px 8px;font-size:11px;color:#64748b">{definition}</td>'
            f'</tr>'
        )
    table = (
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        '<tr style="background:#f1f5f9">'
        '<th style="padding:6px 8px;text-align:left">Rule</th>'
        '<th style="padding:6px 8px;text-align:left;width:140px">Word</th>'
        '<th style="padding:6px 8px;text-align:left;width:130px">Acoustics</th>'
        '<th style="padding:6px 8px;text-align:left">Definition</th>'
        '</tr>' + rule_rows + '</table>'
        if rule_rows else
        '<div style="color:#94a3b8;font-size:12px;padding:4px">No tajweed rules detected.</div>'
    )
    tlit = v.get('transliteration', '')
    tran = v.get('translation', '')
    return f'''
<div style="background:white;border-radius:10px;padding:20px;margin:12px 0;
            box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:4px solid {border_color}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div>
      <span style="font-weight:700;font-size:15px;color:#1e3a5f">Āyah {v["ayah"]}</span>
      <span style="color:#64748b;font-size:12px;margin-left:10px;font-style:italic">{tlit}</span>
    </div>
    <span style="background:#dbeafe;color:#1e40af;padding:2px 10px;border-radius:12px;font-size:12px">
      {n_rules} rule{"s" if n_rules != 1 else ""}
    </span>
  </div>
  <div style="font-family:'Traditional Arabic','Scheherazade New',serif;font-size:30px;
              line-height:2;text-align:right;padding:12px 18px;background:#f8fafc;
              border-radius:8px;margin-bottom:8px" dir="rtl">{r["highlighted_text"]}</div>
  <div style="font-size:12px;color:#64748b;margin-bottom:12px;padding:0 4px">{tran}</div>
  {table}
</div>'''


def _surah_header(surah_info, verse_results):
    n = surah_info['number']
    total = sum(len(r['detected']) for r in verse_results)
    subtitle = SURAH_SUBTITLES.get(n, surah_info['meaning'])
    return f'''
<div id="s{n}" style="background:linear-gradient(135deg,#1e3a5f,#2563eb);color:white;
            padding:18px 28px;border-radius:10px;margin:28px 0 4px">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div>
      <div style="font-size:12px;opacity:.7;text-transform:uppercase;letter-spacing:.05em">Surah {n}</div>
      <div style="font-size:22px;font-weight:700;margin-top:2px">
        {surah_info["name"]}
        <span style="font-family:'Traditional Arabic',serif;font-size:26px;margin-left:8px;opacity:.9">
          {surah_info["arabic_name"]}
        </span>
      </div>
      <div style="font-size:13px;opacity:.75;margin-top:2px">{subtitle}</div>
    </div>
    <div style="display:flex;gap:14px">
      <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:8px 16px;text-align:center">
        <div style="font-size:20px;font-weight:700">{len(verse_results)}</div>
        <div style="font-size:11px;opacity:.8">Verses</div>
      </div>
      <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:8px 16px;text-align:center">
        <div style="font-size:20px;font-weight:700">{total}</div>
        <div style="font-size:11px;opacity:.8">Rules</div>
      </div>
    </div>
  </div>
</div>'''


def _test_verse_card(verse, detected, tp, fp, fn, highlighted_text):
    """Render one test-suite verse card with TP/FP/FN table."""
    n_tp, n_fp, n_fn = len(tp), len(fp), len(fn)
    badge_bg = '#22c55e' if n_fp == 0 and n_fn == 0 else '#ef4444'
    detected_sorted = sorted(detected, key=lambda d: d['phoneme_idx'])

    rule_rows = ''
    for det in detected_sorted:
        rule = det['rule']
        bg, fg = RULE_COLOURS.get(rule, ('#e2e8f0', '#1a202c'))
        display = RULE_DISPLAY.get(rule, rule)
        swatch = (f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
                  f'background:{bg};border:1px solid {fg};margin-right:5px"></span>')
        rule_rows += (
            f'<tr>'
            f'<td style="padding:5px 8px">{swatch}'
            f'<b style="color:{fg};background:{bg};padding:1px 6px;border-radius:3px;font-size:11px">{display}</b></td>'
            f'<td style="padding:5px 8px;font-family:\'Traditional Arabic\',serif;font-size:17px" dir="rtl">{det["word"]}</td>'
            f'</tr>'
        )

    mismatch_rows = ''
    for item in fn:
        display = RULE_DISPLAY.get(item['rule'], item['rule'])
        mismatch_rows += (
            f'<tr style="background:#fef2f2">'
            f'<td style="color:#dc2626;padding:4px 8px;font-size:12px">&#x274C; FN</td>'
            f'<td style="padding:4px 8px;font-size:12px">{display}</td>'
            f'<td style="padding:4px 8px;font-family:\'Traditional Arabic\',serif;font-size:15px" dir="rtl">{item["word"]}</td>'
            f'<td style="padding:4px 8px;font-size:11px;color:#dc2626">{item["reason"]}</td>'
            f'</tr>'
        )
    for item in fp:
        display = RULE_DISPLAY.get(item['rule'], item['rule'])
        det_info = item.get('details') or {}
        mismatch_rows += (
            f'<tr style="background:#fffbeb">'
            f'<td style="color:#d97706;padding:4px 8px;font-size:12px">&#x26A0; FP</td>'
            f'<td style="padding:4px 8px;font-size:12px">{display}</td>'
            f'<td style="padding:4px 8px;font-family:\'Traditional Arabic\',serif;font-size:15px" dir="rtl">{item["word"]}</td>'
            f'<td style="padding:4px 8px;font-size:11px;color:#d97706">phonemes: {det_info.get("phonemes","")}</td>'
            f'</tr>'
        )

    mismatch_section = ''
    if mismatch_rows:
        mismatch_section = f'''
<div style="margin-top:8px">
  <table style="width:100%;border-collapse:collapse;font-size:12px;border:1px solid #fee2e2;border-radius:6px">
    <tr style="background:#fef2f2">
      <th colspan="4" style="padding:4px 8px;text-align:left;font-size:11px;color:#991b1b">MISMATCHES</th>
    </tr>
    {mismatch_rows}
  </table>
</div>'''

    detected_table = (
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        '<tr style="background:#f1f5f9">'
        '<th style="padding:6px 8px;text-align:left">Rule Detected</th>'
        '<th style="padding:6px 8px;text-align:left">Word</th>'
        '</tr>' + rule_rows + '</table>'
        if rule_rows else
        '<div style="color:#94a3b8;font-size:12px;padding:4px">No tajweed rules detected.</div>'
    )

    return f'''
<div style="background:white;border-radius:10px;padding:20px;margin:12px 0;
            box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:4px solid {badge_bg}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div>
      <span style="font-weight:700;font-size:14px;color:#1e3a5f">{verse["ref"]}</span>
      <span style="color:#64748b;font-size:13px;margin-left:8px">{verse["name"]}</span>
    </div>
    <span style="background:{badge_bg};color:white;padding:2px 12px;border-radius:12px;font-size:12px;font-weight:600">
      TP:{n_tp} FP:{n_fp} FN:{n_fn}
    </span>
  </div>
  <div style="font-family:'Traditional Arabic','Scheherazade New',serif;font-size:28px;
              line-height:2;text-align:right;padding:10px 16px;background:#f8fafc;
              border-radius:8px;margin-bottom:12px" dir="rtl">{highlighted_text}</div>
  {detected_table}
  {mismatch_section}
</div>'''


# ── Master HTML builder ────────────────────────────────────────────────

def generate_html(surah_results, test_suite_results, all_rule_stats):
    now = datetime.now().strftime('%B %d, %Y at %H:%M')

    grand_total_rules = sum(
        sum(len(r['detected']) for r in vr)
        for _, vr in surah_results
    )
    grand_total_verses = sum(len(vr) for _, vr in surah_results)

    # Collect all rule types seen across surah sections
    all_seen_rules = set()
    for _, vr in surah_results:
        for r in vr:
            for det in r['detected']:
                all_seen_rules.add(det['rule'])

    # Test suite totals
    ts_tp = sum(r['n_tp'] for r in test_suite_results)
    ts_fp = sum(r['n_fp'] for r in test_suite_results)
    ts_fn = sum(r['n_fn'] for r in test_suite_results)
    precision = ts_tp / (ts_tp + ts_fp) if (ts_tp + ts_fp) else 0
    recall    = ts_tp / (ts_tp + ts_fn) if (ts_tp + ts_fn) else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    # Navigation
    nav_items = ''
    for si, _ in surah_results:
        n = si['number']
        nav_items += (
            f'<a href="#s{n}" style="color:#1e40af;text-decoration:none;'
            f'padding:4px 10px;border-radius:6px;background:#dbeafe;'
            f'font-size:12px;font-weight:600;white-space:nowrap">'
            f'{n} · {si["name"]}</a> '
        )
    nav_items += (
        '<a href="#test-suite" style="color:#0f766e;text-decoration:none;'
        'padding:4px 10px;border-radius:6px;background:#ccfbf1;'
        'font-size:12px;font-weight:600;white-space:nowrap">Validation Suite</a>'
    )

    # Legend
    legend_items = ''
    for rule in sorted(all_seen_rules):
        bg, fg = RULE_COLOURS.get(rule, ('#e2e8f0', '#1a202c'))
        display = RULE_DISPLAY.get(rule, rule)
        legend_items += (
            f'<span style="display:inline-flex;align-items:center;margin:3px 6px 3px 0">'
            f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
            f'background:{bg};border:1px solid {fg};margin-right:4px"></span>'
            f'<span style="font-size:11px;color:{fg};background:{bg};'
            f'padding:1px 5px;border-radius:3px">{display}</span></span>'
        )

    # Per-rule stats table for test suite
    stats_rows = ''
    for rule in sorted(all_rule_stats.keys()):
        s = all_rule_stats[rule]
        rp = s['tp'] / (s['tp'] + s['fp']) if (s['tp'] + s['fp']) else 0
        rr = s['tp'] / (s['tp'] + s['fn']) if (s['tp'] + s['fn']) else 0
        rf = 2 * rp * rr / (rp + rr) if (rp + rr) else 0
        ok = s['fn'] == 0 and s['fp'] == 0
        icon = '&#x2705;' if ok else '&#x274C;'
        row_bg = '#f0fdf4' if ok else '#fef2f2'
        display = RULE_DISPLAY.get(rule, rule)
        bg, fg = RULE_COLOURS.get(rule, ('#e2e8f0', '#1a202c'))
        swatch = (f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
                  f'background:{bg};border:1px solid {fg};margin-right:5px;vertical-align:middle"></span>')
        stats_rows += (
            f'<tr style="background:{row_bg}">'
            f'<td style="padding:5px 8px">{icon}</td>'
            f'<td style="padding:5px 8px;font-size:12px">{swatch}{display}</td>'
            f'<td style="padding:5px 8px;color:#16a34a;font-weight:600">{s["tp"]}</td>'
            f'<td style="padding:5px 8px;color:#dc2626">{s["fp"]}</td>'
            f'<td style="padding:5px 8px;color:#dc2626">{s["fn"]}</td>'
            f'<td style="padding:5px 8px">{rp:.0%}</td>'
            f'<td style="padding:5px 8px">{rr:.0%}</td>'
            f'<td style="padding:5px 8px"><b>{rf:.0%}</b></td>'
            f'</tr>'
        )

    # Surah section bodies
    surah_body = ''
    for si, vr in surah_results:
        surah_body += _surah_header(si, vr)
        for result in vr:
            surah_body += _verse_card(result['verse'], result)

    # Test suite cards
    test_cards = ''
    for r in test_suite_results:
        test_cards += _test_verse_card(
            r['verse'], r['detected'],
            r['tp'], r['fp'], r['fn'],
            r['highlighted_text'],
        )

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Extended Tajweed Report — Surahs 67 · 78 · 93 · 97 · 109 · 112 · 113 · 114</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f1f5f9; margin: 0; padding: 20px; color: #1e293b; }}
  .container {{ max-width: 980px; margin: 0 auto; }}
</style></head><body><div class="container">

<!-- ── Top header ── -->
<div style="background:linear-gradient(135deg,#0f2744,#1e3a5f,#2563eb);color:white;
            padding:28px 36px;border-radius:14px;margin-bottom:20px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div style="font-size:12px;opacity:.7;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">
        Tajweed Analysis · Extended Report
      </div>
      <h1 style="margin:0;font-size:26px;font-weight:800">
        Surahs 67 · 78 · 93 · 97 · 109 · 112 · 113 · 114
      </h1>
      <div style="font-size:13px;opacity:.7;margin-top:6px">
        Al-Mulk · An-Nabaʾ · Ad-Duḥā · Al-Qadr · Al-Kāfirūn · Al-Ikhlāṣ · Al-Falaq · An-Nās
      </div>
    </div>
    <div style="text-align:right;font-size:12px;opacity:.65">{now}</div>
  </div>
  <div style="display:flex;gap:14px;margin-top:20px;flex-wrap:wrap">
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 20px;text-align:center">
      <div style="font-size:24px;font-weight:700">{grand_total_verses}</div>
      <div style="font-size:11px;opacity:.8">Surah Verses</div>
    </div>
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 20px;text-align:center">
      <div style="font-size:24px;font-weight:700">{grand_total_rules}</div>
      <div style="font-size:11px;opacity:.8">Rules Detected</div>
    </div>
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 20px;text-align:center">
      <div style="font-size:24px;font-weight:700">{len(all_seen_rules)}</div>
      <div style="font-size:11px;opacity:.8">Rule Types</div>
    </div>
    <div style="background:rgba(255,255,255,.2);border-radius:8px;padding:10px 20px;text-align:center;border:1px solid rgba(255,255,255,.3)">
      <div style="font-size:24px;font-weight:700">{f1:.0%}</div>
      <div style="font-size:11px;opacity:.8">Suite F1</div>
    </div>
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 20px;text-align:center">
      <div style="font-size:24px;font-weight:700">{precision:.0%}</div>
      <div style="font-size:11px;opacity:.8">Precision</div>
    </div>
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 20px;text-align:center">
      <div style="font-size:24px;font-weight:700">{recall:.0%}</div>
      <div style="font-size:11px;opacity:.8">Recall</div>
    </div>
  </div>
</div>

<!-- ── Navigation ── -->
<div style="background:white;border-radius:10px;padding:14px 20px;margin-bottom:14px;
            box-shadow:0 1px 3px rgba(0,0,0,.06);display:flex;flex-wrap:wrap;gap:8px;align-items:center">
  <span style="font-size:12px;font-weight:600;color:#64748b;margin-right:6px">Jump to:</span>
  {nav_items}
</div>

<!-- ── Colour Legend ── -->
<div style="background:white;border-radius:10px;padding:16px 20px;margin-bottom:10px;
            box-shadow:0 1px 3px rgba(0,0,0,.06)">
  <div style="font-size:12px;font-weight:600;color:#64748b;margin-bottom:8px;
              text-transform:uppercase;letter-spacing:.05em">Rule Colour Legend</div>
  <div style="display:flex;flex-wrap:wrap">{legend_items}</div>
</div>

<!-- ── Surah Sections ── -->
{surah_body}

<!-- ── Validation Test Suite ── -->
<div id="test-suite" style="margin-top:40px">
  <div style="background:linear-gradient(135deg,#134e4a,#0f766e);color:white;
              padding:20px 28px;border-radius:10px;margin-bottom:16px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <div style="font-size:12px;opacity:.7;text-transform:uppercase;letter-spacing:.05em">Ground Truth Comparison</div>
        <h2 style="margin:4px 0 0;font-size:22px;font-weight:700">8-Verse Validation Suite</h2>
        <div style="font-size:13px;opacity:.75;margin-top:4px">
          Surahs 1, 108, 110, 112, 114 · per-rule accuracy
        </div>
      </div>
      <div style="display:flex;gap:12px">
        <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:8px 16px;text-align:center">
          <div style="font-size:20px;font-weight:700;color:#86efac">{ts_tp}</div>
          <div style="font-size:11px;opacity:.8">TP</div>
        </div>
        <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:8px 16px;text-align:center">
          <div style="font-size:20px;font-weight:700;color:#fca5a5">{ts_fp}</div>
          <div style="font-size:11px;opacity:.8">FP</div>
        </div>
        <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:8px 16px;text-align:center">
          <div style="font-size:20px;font-weight:700;color:#fca5a5">{ts_fn}</div>
          <div style="font-size:11px;opacity:.8">FN</div>
        </div>
        <div style="background:rgba(255,255,255,.2);border-radius:8px;padding:8px 16px;text-align:center;border:1px solid rgba(255,255,255,.3)">
          <div style="font-size:20px;font-weight:700">{f1:.0%}</div>
          <div style="font-size:11px;opacity:.8">F1</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Per-rule accuracy table -->
  <div style="background:white;border-radius:10px;padding:20px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
    <div style="font-size:14px;font-weight:600;color:#1e293b;margin-bottom:12px">Per-Rule Accuracy</div>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tr style="background:#f1f5f9">
        <th style="padding:6px 8px"></th>
        <th style="padding:6px 8px;text-align:left">Rule</th>
        <th style="padding:6px 8px;text-align:center">TP</th>
        <th style="padding:6px 8px;text-align:center">FP</th>
        <th style="padding:6px 8px;text-align:center">FN</th>
        <th style="padding:6px 8px;text-align:center">Prec</th>
        <th style="padding:6px 8px;text-align:center">Rec</th>
        <th style="padding:6px 8px;text-align:center">F1</th>
      </tr>
      {stats_rows}
    </table>
  </div>

  <!-- Per-verse cards -->
  {test_cards}
</div>

</div></body></html>'''


# ── Main ──────────────────────────────────────────────────────────────

def main():
    print('=' * 65)
    print('EXTENDED TAJWEED REPORT — Surahs 67,78,93,97,109,112,113,114 + Test Suite')
    print('=' * 65)

    print('\nInitializing pipeline...')
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f'Pipeline ready: {len(pipeline.tajweed_engine.rules)} rules\n')

    # ── Process surah sections ─────────────────────────────────────
    surah_results = []
    for surah_info, verses in SURAH_SECTIONS:
        n = surah_info['number']
        sub = SURAH_SUBTITLES.get(n, surah_info['name'])
        print(f'── Surah {n}: {surah_info["name"]} ──')
        verse_results = []
        for verse in verses:
            text = strip_waqf(verse['text'])
            print(f'  Ayah {verse["ayah"]}: {text[:50]}...')
            try:
                detected, output, highlighted = process_verse(pipeline, text)
                verse_results.append({
                    'verse': verse,
                    'detected': detected,
                    'highlighted_text': highlighted,
                })
                print(f'    → {len(detected)} rule(s)')
            except Exception as e:
                import traceback; traceback.print_exc()
                verse_results.append({
                    'verse': verse, 'detected': [], 'highlighted_text': verse['text'],
                })
        total = sum(len(r['detected']) for r in verse_results)
        print(f'  → total: {total} rules\n')
        surah_results.append((surah_info, verse_results))

    # ── Process test suite ─────────────────────────────────────────
    print('── 8-Verse Validation Test Suite ──')
    test_suite_results = []
    all_rule_stats = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0})
    waqf_marks = '\u06DA\u06D6\u06D7\u06D8\u06D9\u06DE'

    for verse in TEST_SUITE:
        text = verse['text']
        for m in waqf_marks:
            text = text.replace(m + ' ', '').replace(' ' + m, '').replace(m, '')
        print(f'  {verse["ref"]:8s} {verse["name"]}')
        try:
            detected, output, highlighted = process_verse(pipeline, text)
            tp, fp, fn = compare(verse['expected'], detected)
            status = 'PASS' if not fp and not fn else 'FAIL'
            print(f'    {status}  TP={len(tp)} FP={len(fp)} FN={len(fn)}')
            for item in fn:
                print(f'      FN: {item["rule"]:30s}  {item["word"]}')
            for item in fp:
                print(f'      FP: {item["rule"]:30s}  {item["word"]}')
            for item in tp:
                all_rule_stats[item['rule']]['tp'] += 1
            for item in fp:
                all_rule_stats[item['rule']]['fp'] += 1
            for item in fn:
                all_rule_stats[item['rule']]['fn'] += 1
            test_suite_results.append({
                'verse': verse, 'detected': detected,
                'highlighted_text': highlighted,
                'tp': tp, 'fp': fp, 'fn': fn,
                'n_tp': len(tp), 'n_fp': len(fp), 'n_fn': len(fn),
            })
        except Exception as e:
            import traceback; traceback.print_exc()
            test_suite_results.append({
                'verse': verse, 'detected': [],
                'highlighted_text': verse['text'],
                'tp': [], 'fp': [],
                'fn': [{'rule': r, 'word': w, 'reason': reason}
                       for r, w, reason in verse['expected']],
                'n_tp': 0, 'n_fp': 0, 'n_fn': len(verse['expected']),
            })

    # ── Build & write HTML ─────────────────────────────────────────
    html = generate_html(surah_results, test_suite_results, all_rule_stats)
    out_dir = Path(__file__).parent / 'output'
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / 'extended_report.html'
    out_file.write_text(html, encoding='utf-8')

    ts_tp = sum(r['n_tp'] for r in test_suite_results)
    ts_fp = sum(r['n_fp'] for r in test_suite_results)
    ts_fn = sum(r['n_fn'] for r in test_suite_results)
    precision = ts_tp / (ts_tp + ts_fp) if (ts_tp + ts_fp) else 0
    recall    = ts_tp / (ts_tp + ts_fn) if (ts_tp + ts_fn) else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    print(f'\nTest Suite  TP={ts_tp} FP={ts_fp} FN={ts_fn}')
    print(f'Precision={precision:.1%}  Recall={recall:.1%}  F1={f1:.1%}')
    print(f'Report: {out_file}')
    print('=' * 65)


if __name__ == '__main__':
    main()
