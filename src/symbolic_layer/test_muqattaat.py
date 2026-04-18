#!/usr/bin/env python3
"""
Targeted test for Muqaṭṭaʿāt (disjoined-letter) handling.

Walks the six canonical Muqaṭṭaʿāt openings through the phonemizer +
Tajwīd engine and verifies:

  1. The IPA phoneme stream matches the spelled-out letter-name table
     in `phonemizer.MUQATTAAT_LETTER_NAMES`.
  2. The expected Tajwīd rules fire on each letter-name range:
       - madd_lazim   on letters whose name carries 6-count harfī madd
       - madd_tabii   on letters whose name carries 2-count natural madd
       - qalqalah_major on ص and ق letter-names
       - ghunnah      at the lām→mīm junction inside الٓمٓ
       - none         on the alif of الٓمٓ (no madd, just a glottal+a+l+i+f)

Usage (from project root):
    python src/symbolic_layer/test_muqattaat.py

The script does not silently fix failures: each case prints PASS/FAIL with
a diff between expected and actual values, and the process exits non-zero
if any case fails.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Make `symbolic_layer` importable when run as a standalone script.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from symbolic_layer.phonemizer import (  # noqa: E402
    QuranPhonemizer,
    MUQATTAAT_LETTER_NAMES,
)
from symbolic_layer.tajweed_engine import TajweedEngine  # noqa: E402


# ── Test cases ───────────────────────────────────────────────────────────
# Each case lists, per Arabic letter in the Muqaṭṭaʿāt word:
#   - the letter itself
#   - the IPA symbols expected (from MUQATTAAT_LETTER_NAMES)
#   - the set of rule names that MUST fire somewhere on this letter's
#     phoneme range. madd_tabii is the engine's existing rule; the rest
#     come from the muqattaat injection path.
#
# Notes on individual letters:
#   • alif (ا) in الم has NO madd at all — its phonemes are just
#     [ʔ a l i f], no long vowel. Expected rules = empty set.
#   • ه, ي, ح carry 2-count madd ṭabīʿī (their letter-names are 2-letter
#     spellings haa/yaa/haa). The engine's existing madd_tabii rule fires
#     automatically on the long vowel — no muqattaat injection needed.
#   • ك, ل, م, ع, س, ن, ق, ص carry 6-count madd lāzim ḥarfī, injected
#     via muqattaat_rule_specs. The engine then suppresses madd_tabii at
#     the same long-vowel position (specific_madd_rules conflict resolver).
#   • ع → diphthong 'aj' is NOT in [aː iː uː], so madd_tabii would not
#     fire there anyway; only madd_lazim is injected.
#   • ق → qalqalah_major is injected on the initial 'q' because the
#     standard qalqalah_major rule needs a sukoon-bearing q at word end,
#     which is not the case in "qaaf" (q is followed by aː).
#   • ص → qalqalah_major fires automatically on the final 'd' (qalqalah
#     letter at word end → sukoon). The muqattaat path does NOT inject a
#     duplicate spec for ص — we rely on the standard rule.
#   • ل → م junction in الم triggers ghunnah (idgham bi-ghunnah), injected
#     on the initial 'm' of the مٓ letter-name.
TEST_CASES = [
    {
        "name": "2:1 الٓمٓ (alif-laam-meem)",
        "text": "الٓمٓ",
        "surah": 2,
        "ayah": 1,
        "letters": [
            ("ا", ["ʔ", "a", "l", "i", "f"], set()),
            ("ل", ["l", "aː", "m"],          {"madd_lazim"}),
            ("م", ["m", "iː", "m"],          {"madd_lazim", "ghunnah"}),
        ],
    },
    {
        "name": "36:1 يسٓ (yaa-seen)",
        "text": "يسٓ",
        "surah": 36,
        "ayah": 1,
        "letters": [
            ("ي", ["j", "aː"],     {"madd_tabii"}),
            ("س", ["s", "iː", "n"], {"madd_lazim"}),
        ],
    },
    {
        "name": "19:1 كٓهيعٓصٓ (kaaf-haa-yaa-ayn-saad)",
        "text": "كٓهيعٓصٓ",
        "surah": 19,
        "ayah": 1,
        "letters": [
            ("ك", ["k", "aː", "f"],   {"madd_lazim"}),
            ("ه", ["h", "aː"],        {"madd_tabii"}),
            ("ي", ["j", "aː"],        {"madd_tabii"}),
            ("ع", ["ʕ", "aj", "n"],   {"madd_lazim"}),
            ("ص", ["sˤ", "aː", "d"],  {"madd_lazim", "qalqalah_major"}),
        ],
    },
    {
        # Bare ص — no maddah mark — must be detected via surah:ayah.
        "name": "38:1 ص (saad, unmarked)",
        "text": "ص",
        "surah": 38,
        "ayah": 1,
        "letters": [
            ("ص", ["sˤ", "aː", "d"], {"madd_lazim", "qalqalah_major"}),
        ],
    },
    {
        # Bare ق — no maddah mark — must be detected via surah:ayah.
        "name": "50:1 ق (qaaf, unmarked)",
        "text": "ق",
        "surah": 50,
        "ayah": 1,
        "letters": [
            ("ق", ["q", "aː", "f"], {"madd_lazim", "qalqalah_major"}),
        ],
    },
    {
        # Bare ن — no maddah mark — must be detected via surah:ayah.
        "name": "68:1 ن (nuun, unmarked)",
        "text": "ن",
        "surah": 68,
        "ayah": 1,
        "letters": [
            ("ن", ["n", "uː", "n"], {"madd_lazim"}),
        ],
    },
]


def _letter_phoneme_ranges(
    expected_letters: List[Tuple[str, List[str], Set[str]]],
) -> List[Tuple[str, range]]:
    """
    Compute the (start, end_exclusive) phoneme range for each letter,
    based on the expected IPA symbols. Used to slice rule applications
    by letter so we can check rules on a per-letter basis.
    """
    ranges: List[Tuple[str, range]] = []
    cursor = 0
    for letter, symbols, _rules in expected_letters:
        start = cursor
        end = cursor + len(symbols)
        ranges.append((letter, range(start, end)))
        cursor = end
    return ranges


def _format_diff(label: str, expected, actual) -> str:
    return f"      {label}:\n        expected: {expected}\n        actual:   {actual}"


def _run_case(
    phonemizer: QuranPhonemizer,
    engine: TajweedEngine,
    case: Dict,
) -> bool:
    """Run a single test case. Returns True on PASS, False on FAIL."""
    name = case["name"]
    text = case["text"]
    surah = case.get("surah")
    ayah = case.get("ayah")
    expected_letters = case["letters"]

    print(f"\n──────────────────────────────────────────────────────────────")
    print(f" {name}")
    print(f"   text   = {text!r}")
    print(f"   surah  = {surah}, ayah = {ayah}")

    # 1. Phonemize.
    try:
        seq = phonemizer.phonemize(text, surah=surah, ayah=ayah)
    except Exception as e:
        print(f"   FAIL — phonemize() raised: {type(e).__name__}: {e}")
        return False

    actual_symbols = [p.symbol for p in seq.phonemes]
    expected_symbols: List[str] = []
    for _letter, syms, _rules in expected_letters:
        expected_symbols.extend(syms)

    print(f"   IPA    = {actual_symbols}")
    print(f"   specs  = {seq.muqattaat_rule_specs}")

    case_passed = True

    if actual_symbols != expected_symbols:
        print("   FAIL — phoneme symbols differ from expected")
        print(_format_diff("phonemes", expected_symbols, actual_symbols))
        case_passed = False

    # 2. Apply Tajwīd rules.
    try:
        annotated = engine.apply_rules(seq)
    except Exception as e:
        print(f"   FAIL — engine.apply_rules() raised: {type(e).__name__}: {e}")
        return False

    # Build a per-position map of fired rule names.
    position_to_rules: Dict[int, Set[str]] = {}
    for app in annotated.rule_applications:
        for pos in app.get_affected_range():
            position_to_rules.setdefault(pos, set()).add(app.rule.name)

    print(f"   rules  = {[(app.rule.name, app.start_index, app.end_index) for app in annotated.rule_applications]}")

    # 3. Check rules per letter range.
    ranges = _letter_phoneme_ranges(expected_letters)
    for (letter, expected_symbols_for_letter, expected_rules), (_letter2, rng) in zip(
        expected_letters, ranges
    ):
        # Sanity check: the actual symbols in this range should match the
        # expected ones (already covered by the global comparison, but
        # report which letter is wrong if they differ).
        if rng.stop <= len(actual_symbols):
            actual_symbols_for_letter = actual_symbols[rng.start:rng.stop]
        else:
            actual_symbols_for_letter = actual_symbols[rng.start:]

        if actual_symbols_for_letter != expected_symbols_for_letter:
            print(f"   FAIL [{letter}] — phonemes for letter wrong")
            print(_format_diff(
                f"{letter} phonemes",
                expected_symbols_for_letter,
                actual_symbols_for_letter,
            ))
            case_passed = False

        # Collect rules that fired anywhere in this letter's range.
        fired: Set[str] = set()
        for pos in rng:
            fired |= position_to_rules.get(pos, set())

        missing = expected_rules - fired
        # We don't insist that no other rules fire (the engine may legally
        # fire qalqalah_minor, idhhar etc. on subsequent phonemes), but we
        # do insist that the expected ones are present.
        if missing:
            print(f"   FAIL [{letter}] — missing expected rule(s): {sorted(missing)}")
            print(_format_diff(
                f"{letter} rules",
                sorted(expected_rules),
                sorted(fired),
            ))
            case_passed = False

    if case_passed:
        print("   PASS")
    return case_passed


def main() -> int:
    print("=" * 70)
    print("Muqaṭṭaʿāt test suite")
    print("=" * 70)

    # Sanity-check that the lookup table is loaded.
    print(f"\nLoaded {len(MUQATTAAT_LETTER_NAMES)} letter-name entries from "
          f"phonemizer.MUQATTAAT_LETTER_NAMES")

    # Build phonemizer + engine using project defaults.
    phonemizer = QuranPhonemizer(
        base_phonemes_path=str(PROJECT_ROOT / "data/pronunciation_dict/base_phonemes.yaml"),
        tajweed_phonemes_path=str(PROJECT_ROOT / "data/pronunciation_dict/tajweed_phonemes.yaml"),
        g2p_rules_path=str(PROJECT_ROOT / "data/pronunciation_dict/g2p_rules.yaml"),
    )
    engine = TajweedEngine(rule_config_dir=str(PROJECT_ROOT / "data/tajweed_rules"))
    print(f"Engine loaded with {len(engine.rules)} rules\n")

    # Verify that the muqattaat rules are present in the engine.
    rule_names = {r.name for r in engine.rules}
    for required in ("madd_lazim", "ghunnah", "madd_tabii", "qalqalah_major"):
        if required not in rule_names:
            print(f"FATAL — required rule '{required}' not found in engine")
            return 2

    # Run cases.
    results: List[Tuple[str, bool]] = []
    for case in TEST_CASES:
        passed = _run_case(phonemizer, engine, case)
        results.append((case["name"], passed))

    # Summary.
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    n_pass = sum(1 for _, ok in results if ok)
    n_fail = len(results) - n_pass
    for name, ok in results:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
    print(f"\n{n_pass}/{len(results)} cases passed, {n_fail} failed.")

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
