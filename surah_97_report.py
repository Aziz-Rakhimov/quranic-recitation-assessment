#!/usr/bin/env python3
"""
Tajweed Analysis Report — Surah 97 (Al-Qadr)

Runs all 5 verses through the symbolic pipeline and renders a clean
per-verse HTML report: highlighted Arabic, detected rules sorted by
position, acoustic features, and short English definitions.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from symbolic_layer.pipeline import SymbolicLayerPipeline

sys.path.insert(0, str(Path(__file__).parent))
from systematic_validation import (
    process_verse,
    RULE_DISPLAY, RULE_COLOURS, RULE_DEFINITIONS,
    EXCLUDED_RULES,
)

# ── Surah 97 verse data ────────────────────────────────────────────
SURAH_97 = {
    'number': 97,
    'name': 'Al-Qadr',
    'arabic_name': 'القدر',
    'meaning': 'The Night of Decree',
    'verses': [
        {
            'ayah': 1,
            'text': 'إِنَّآ أَنزَلْنَٰهُ فِى لَيْلَةِ ٱلْقَدْرِ',
            'transliteration': 'Innā anzalnāhu fī laylati l-qadr',
            'translation': 'Indeed, We sent it down on the Night of Decree',
        },
        {
            'ayah': 2,
            'text': 'وَمَآ أَدْرَىٰكَ مَا لَيْلَةُ ٱلْقَدْرِ',
            'transliteration': 'Wa-mā adrāka mā laylatu l-qadr',
            'translation': 'And what can make you know what the Night of Decree is?',
        },
        {
            'ayah': 3,
            'text': 'لَيْلَةُ ٱلْقَدْرِ خَيْرٌ مِّنْ أَلْفِ شَهْرٍ',
            'transliteration': 'Laylatu l-qadri khayrun min alfi shahr',
            'translation': 'The Night of Decree is better than a thousand months',
        },
        {
            'ayah': 4,
            'text': 'تَنَزَّلُ ٱلْمَلَٰٓئِكَةُ وَٱلرُّوحُ فِيهَا بِإِذْنِ رَبِّهِم مِّن كُلِّ أَمْرٍ',
            'transliteration': "Tanazzalu l-malāʾikatu wa-r-rūḥu fīhā bi-idhni rabbihim min kulli amr",
            'translation': 'The angels and the Spirit descend therein, by the permission of their Lord, for every matter',
        },
        {
            'ayah': 5,
            'text': 'سَلَٰمٌ هِىَ حَتَّىٰ مَطْلَعِ ٱلْفَجْرِ',
            'transliteration': "Salāmun hiya ḥattā maṭlaʿi l-fajr",
            'translation': 'Peace it is until the emergence of dawn',
        },
    ],
}

WAQF_MARKS = '\u06DA\u06D6\u06D7\u06D8\u06D9\u06DE'


def strip_waqf(text: str) -> str:
    for m in WAQF_MARKS:
        text = text.replace(m + ' ', '').replace(' ' + m, '').replace(m, '')
    return text


# ── HTML generation ────────────────────────────────────────────────

def generate_html(surah_info, verse_results):
    now = datetime.now().strftime('%B %d, %Y at %H:%M')
    total_rules = sum(len(r['detected']) for r in verse_results)

    verse_cards = ''
    for r in verse_results:
        v = r['verse']
        detected_sorted = sorted(r['detected'], key=lambda d: d['phoneme_idx'])

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

        n_rules = len(detected_sorted)
        transliteration = v.get('transliteration', '')
        translation = v.get('translation', '')

        verse_cards += f'''
<div style="background:white;border-radius:10px;padding:20px;margin:16px 0;
            box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:4px solid #2563eb">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div>
      <span style="font-weight:700;font-size:15px;color:#1e3a5f">
        Āyah {v['ayah']}
      </span>
      <span style="color:#64748b;font-size:12px;margin-left:10px;font-style:italic">
        {transliteration}
      </span>
    </div>
    <span style="background:#dbeafe;color:#1e40af;padding:2px 10px;border-radius:12px;font-size:12px">
      {n_rules} rule{'s' if n_rules != 1 else ''}
    </span>
  </div>
  <div style="font-family:'Traditional Arabic','Scheherazade New',serif;font-size:30px;
              line-height:2;text-align:right;padding:12px 18px;background:#f8fafc;
              border-radius:8px;margin-bottom:8px" dir="rtl">{r['highlighted_text']}</div>
  <div style="font-size:12px;color:#64748b;margin-bottom:12px;padding:0 4px">
    {translation}
  </div>
  {'<table style="width:100%;border-collapse:collapse;font-size:13px"><tr style="background:#f1f5f9"><th style="padding:6px 8px;text-align:left">Rule</th><th style="padding:6px 8px;text-align:left;width:140px">Word</th><th style="padding:6px 8px;text-align:left;width:130px">Acoustics</th><th style="padding:6px 8px;text-align:left">Definition</th></tr>' + rule_rows + '</table>' if rule_rows else '<div style="color:#94a3b8;font-size:12px;padding:4px">No tajweed rules detected in this verse.</div>'}
</div>'''

    # Legend
    seen_rules = set()
    for r in verse_results:
        for det in r['detected']:
            seen_rules.add(det['rule'])
    legend_items = ''
    for rule in sorted(seen_rules):
        bg, fg = RULE_COLOURS.get(rule, ('#e2e8f0', '#1a202c'))
        display = RULE_DISPLAY.get(rule, rule)
        legend_items += (f'<span style="display:inline-flex;align-items:center;'
                         f'margin:3px 6px 3px 0">'
                         f'<span style="display:inline-block;width:10px;height:10px;'
                         f'border-radius:2px;background:{bg};border:1px solid {fg};'
                         f'margin-right:4px"></span>'
                         f'<span style="font-size:11px;color:{fg};background:{bg};'
                         f'padding:1px 5px;border-radius:3px">{display}</span></span>')

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Surah {surah_info["number"]} — Tajweed Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f1f5f9; margin: 0; padding: 20px; color: #1e293b; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
</style></head><body><div class="container">

<div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);color:white;
            padding:24px 32px;border-radius:12px;margin-bottom:20px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div style="font-size:13px;opacity:.7;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">
        Surah {surah_info["number"]}
      </div>
      <h1 style="margin:0;font-size:26px">
        {surah_info["name"]}
        <span style="font-family:'Traditional Arabic',serif;font-size:30px;margin-left:10px;opacity:.9">
          {surah_info["arabic_name"]}
        </span>
      </h1>
      <div style="font-size:14px;opacity:.75;margin-top:4px">{surah_info["meaning"]}</div>
    </div>
    <div style="text-align:right;font-size:12px;opacity:.7">
      Generated: {now}
    </div>
  </div>
  <div style="display:flex;gap:20px;margin-top:16px">
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 18px;text-align:center">
      <div style="font-size:22px;font-weight:700">{len(verse_results)}</div>
      <div style="font-size:11px;opacity:.8">Verses</div>
    </div>
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 18px;text-align:center">
      <div style="font-size:22px;font-weight:700">{total_rules}</div>
      <div style="font-size:11px;opacity:.8">Rules Detected</div>
    </div>
    <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 18px;text-align:center">
      <div style="font-size:22px;font-weight:700">{len(seen_rules)}</div>
      <div style="font-size:11px;opacity:.8">Unique Rule Types</div>
    </div>
  </div>
</div>

<!-- ── Colour Legend ── -->
<div style="background:white;border-radius:10px;padding:16px 20px;margin-bottom:16px;
            box-shadow:0 1px 3px rgba(0,0,0,.06)">
  <div style="font-size:12px;font-weight:600;color:#64748b;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em">
    Rule Colour Legend
  </div>
  <div style="display:flex;flex-wrap:wrap">{legend_items}</div>
</div>

<!-- ── Verse Cards ── -->
{verse_cards}

</div></body></html>'''


# ── Main ───────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print('SURAH 97 (AL-QADR) — TAJWEED ANALYSIS REPORT')
    print('=' * 60)

    print('\nInitializing pipeline...')
    pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
    print(f'Pipeline ready: {len(pipeline.tajweed_engine.rules)} rules\n')

    verse_results = []
    for verse in SURAH_97['verses']:
        text = strip_waqf(verse['text'])
        print(f"  Processing ayah {verse['ayah']}: {text[:40]}...")
        try:
            detected, output, highlighted_text = process_verse(pipeline, text)
            verse_results.append({
                'verse': verse,
                'detected': detected,
                'highlighted_text': highlighted_text,
            })
            print(f"    → {len(detected)} rule(s) detected")
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

    html = generate_html(SURAH_97, verse_results)
    out_dir = Path(__file__).parent / 'output'
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / 'surah_97_report.html'
    out_file.write_text(html, encoding='utf-8')

    total = sum(len(r['detected']) for r in verse_results)
    print(f'\nTotal rules detected: {total}')
    print(f'Report: {out_file}')
    print('=' * 60)


if __name__ == '__main__':
    main()
