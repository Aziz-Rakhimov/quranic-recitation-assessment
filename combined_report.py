#!/usr/bin/env python3
"""
Combined Tajweed Analysis Report
Surahs: 93, 97, 103, 106, 109  +  Surah 1:7
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from symbolic_layer.pipeline import SymbolicLayerPipeline

sys.path.insert(0, str(Path(__file__).parent))
from systematic_validation import process_verse
from surah_97_report import (
    SURAH_97, strip_waqf,
    RULE_DISPLAY, RULE_COLOURS, RULE_DEFINITIONS,
)
from surah_93_report import SURAH_93
from surah_106_report import SURAH_106
from surah_109_report import SURAH_109, VERSE_1_7

# ── Surah 103 verse data ────────────────────────────────────────────
SURAH_103 = {
    'number': 103,
    'name': 'Al-ʿAṣr',
    'arabic_name': 'العصر',
    'meaning': 'The Declining Day',
    'verses': [
        {
            'ayah': 1,
            'text': 'وَٱلْعَصْرِ',
            'transliteration': 'Wa-l-ʿaṣr',
            'translation': 'By time,',
        },
        {
            'ayah': 2,
            'text': 'إِنَّ ٱلْإِنسَٰنَ لَفِى خُسْرٍ',
            'transliteration': 'Inna l-insāna la-fī khusr',
            'translation': 'Indeed, mankind is in loss,',
        },
        {
            'ayah': 3,
            'text': 'إِلَّا ٱلَّذِينَ ءَامَنُوا۟ وَعَمِلُوا۟ ٱلصَّٰلِحَٰتِ وَتَوَاصَوْا۟ بِٱلْحَقِّ وَتَوَاصَوْا۟ بِٱلصَّبْرِ',
            'transliteration': "Illā lladhīna āmanū wa-ʿamilū ṣ-ṣāliḥāti wa-tawāṣaw bi-l-ḥaqqi wa-tawāṣaw bi-ṣ-ṣabr",
            'translation': 'Except for those who have believed and done righteous deeds and advised each other to truth and advised each other to patience.',
        },
    ],
}

# ── Ordered list of sections ────────────────────────────────────────
# Each entry: (surah_info, list_of_verse_dicts)
SECTIONS = [
    (SURAH_93,  SURAH_93['verses']),
    (SURAH_97,  SURAH_97['verses']),
    (SURAH_103, SURAH_103['verses']),
    (SURAH_106, SURAH_106['verses']),
    (SURAH_109, SURAH_109['verses'] + [VERSE_1_7]),
]

# Label override for the last section (includes 1:7 addendum)
SECTION_SUBTITLES = {
    109: 'Al-Kāfirūn · with Al-Fātiḥah 1:7',
}


# ── HTML generation ─────────────────────────────────────────────────

def _verse_card(v, r):
    """Render a single verse card."""
    detected_sorted = sorted(r['detected'], key=lambda d: d['phoneme_idx'])
    n_rules = len(detected_sorted)
    transliteration = v.get('transliteration', '')
    translation = v.get('translation', '')

    rule_rows = ''
    for det in detected_sorted:
        rule = det['rule']
        bg, fg = RULE_COLOURS.get(rule, ('#e2e8f0', '#1a202c'))
        display = RULE_DISPLAY.get(rule, rule)
        definition = RULE_DEFINITIONS.get(rule, '')
        word = det['word']
        acoustic_parts = []
        if det.get('counts'):
            acoustic_parts.append(f"{det['counts']} ḥarakāt")
        if det.get('duration'):
            acoustic_parts.append(f"{det['duration']} ms")
        if det.get('ghunnah'):
            acoustic_parts.append('ghunnah ✓')
        acoustic_str = ' · '.join(acoustic_parts) if acoustic_parts else '—'
        swatch = (f'<span style="display:inline-block;width:10px;height:10px;'
                  f'border-radius:2px;background:{bg};border:1px solid {fg};'
                  f'margin-right:5px"></span>')
        rule_rows += f'''<tr>
<td style="padding:5px 8px">{swatch}<b style="color:{fg};background:{bg};padding:1px 6px;border-radius:3px;font-size:11px">{display}</b></td>
<td style="padding:5px 8px;font-family:'Traditional Arabic',serif;font-size:17px" dir="rtl">{word}</td>
<td style="padding:5px 8px;font-size:11px;color:#475569">{acoustic_str}</td>
<td style="padding:5px 8px;font-size:11px;color:#64748b">{definition}</td>
</tr>'''

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

    return f'''
<div style="background:white;border-radius:10px;padding:20px;margin:12px 0;
            box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:4px solid #2563eb">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div>
      <span style="font-weight:700;font-size:15px;color:#1e3a5f">Āyah {v['ayah']}</span>
      <span style="color:#64748b;font-size:12px;margin-left:10px;font-style:italic">{transliteration}</span>
    </div>
    <span style="background:#dbeafe;color:#1e40af;padding:2px 10px;border-radius:12px;font-size:12px">
      {n_rules} rule{'s' if n_rules != 1 else ''}
    </span>
  </div>
  <div style="font-family:'Traditional Arabic','Scheherazade New',serif;font-size:30px;
              line-height:2;text-align:right;padding:12px 18px;background:#f8fafc;
              border-radius:8px;margin-bottom:8px" dir="rtl">{r['highlighted_text']}</div>
  <div style="font-size:12px;color:#64748b;margin-bottom:12px;padding:0 4px">{translation}</div>
  {table}
</div>'''


def _surah_header(surah_info, verse_results):
    """Render the surah section header."""
    n = surah_info['number']
    total = sum(len(r['detected']) for r in verse_results)
    subtitle = SECTION_SUBTITLES.get(n, surah_info['meaning'])
    return f'''
<div id="s{n}" style="background:linear-gradient(135deg,#1e3a5f,#2563eb);color:white;
            padding:18px 28px;border-radius:10px;margin:28px 0 4px">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div>
      <div style="font-size:12px;opacity:.7;text-transform:uppercase;letter-spacing:.05em">
        Surah {n}
      </div>
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


def generate_combined_html(sections_data):
    """
    sections_data: list of (surah_info, verse_results) tuples in display order.
    """
    now = datetime.now().strftime('%B %d, %Y at %H:%M')

    grand_total_rules = sum(
        sum(len(r['detected']) for r in vr)
        for _, vr in sections_data
    )
    grand_total_verses = sum(len(vr) for _, vr in sections_data)

    # Collect all rule types seen across all sections
    all_seen_rules = set()
    for _, vr in sections_data:
        for r in vr:
            for det in r['detected']:
                all_seen_rules.add(det['rule'])

    # Navigation bar
    nav_items = ''
    for si, _ in sections_data:
        n = si['number']
        nav_items += (
            f'<a href="#s{n}" style="color:#1e40af;text-decoration:none;'
            f'padding:4px 10px;border-radius:6px;background:#dbeafe;'
            f'font-size:12px;font-weight:600;white-space:nowrap">'
            f'{n} · {si["name"]}</a> '
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

    # Build all section HTML
    body = ''
    for si, vr in sections_data:
        body += _surah_header(si, vr)
        for result in vr:
            body += _verse_card(result['verse'], result)

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Combined Tajweed Report — Surahs 93, 97, 103, 106, 109 + 1:7</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f1f5f9; margin: 0; padding: 20px; color: #1e293b; }}
  .container {{ max-width: 980px; margin: 0 auto; }}
  a {{ color: inherit; }}
</style></head><body><div class="container">

<!-- ── Top header ── -->
<div style="background:linear-gradient(135deg,#0f2744,#1e3a5f,#2563eb);color:white;
            padding:28px 36px;border-radius:14px;margin-bottom:20px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div style="font-size:12px;opacity:.7;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">
        Tajweed Analysis · Combined Report
      </div>
      <h1 style="margin:0;font-size:26px;font-weight:800">
        Surahs 93 · 97 · 103 · 106 · 109
        <span style="font-size:15px;font-weight:400;opacity:.75;margin-left:10px">+ Al-Fātiḥah 1:7</span>
      </h1>
      <div style="font-size:13px;opacity:.7;margin-top:6px">
        Ad-Duḥā · Al-Qadr · Al-ʿAṣr · Quraysh · Al-Kāfirūn
      </div>
    </div>
    <div style="text-align:right;font-size:12px;opacity:.65">{now}</div>
  </div>
  <div style="display:flex;gap:16px;margin-top:20px">
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 20px;text-align:center">
      <div style="font-size:24px;font-weight:700">{grand_total_verses}</div>
      <div style="font-size:11px;opacity:.8">Total Verses</div>
    </div>
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 20px;text-align:center">
      <div style="font-size:24px;font-weight:700">{grand_total_rules}</div>
      <div style="font-size:11px;opacity:.8">Rules Detected</div>
    </div>
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 20px;text-align:center">
      <div style="font-size:24px;font-weight:700">{len(all_seen_rules)}</div>
      <div style="font-size:11px;opacity:.8">Unique Rule Types</div>
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
{body}

</div></body></html>'''


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print('=' * 65)
    print('COMBINED TAJWEED REPORT — Surahs 93, 97, 103, 106, 109 + 1:7')
    print('=' * 65)

    print('\nInitializing pipeline...')
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f'Pipeline ready: {len(pipeline.tajweed_engine.rules)} rules\n')

    sections_data = []
    for surah_info, verses in SECTIONS:
        n = surah_info['number']
        label = SECTION_SUBTITLES.get(n, surah_info['name'])
        print(f"── Surah {n}: {surah_info['name']} ({label}) ──")
        verse_results = []
        for verse in verses:
            text = strip_waqf(verse['text'])
            print(f"  Ayah {verse['ayah']}: {text[:50]}...")
            try:
                detected, output, highlighted_text = process_verse(pipeline, text)
                verse_results.append({
                    'verse': verse,
                    'detected': detected,
                    'highlighted_text': highlighted_text,
                })
                print(f"    → {len(detected)} rule(s)")
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
        total = sum(len(r['detected']) for r in verse_results)
        print(f'  → Surah {n} total: {total} rules\n')
        sections_data.append((surah_info, verse_results))

    html = generate_combined_html(sections_data)
    out_dir = Path(__file__).parent / 'output'
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / 'combined_report.html'
    out_file.write_text(html, encoding='utf-8')

    grand_total = sum(
        sum(len(r['detected']) for r in vr)
        for _, vr in sections_data
    )
    print(f'Grand total rules detected: {grand_total}')
    print(f'Report: {out_file}')
    print('=' * 65)


if __name__ == '__main__':
    main()
