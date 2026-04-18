"""
Qur'anic Arabic Phonemizer.

This module converts Qur'anic Arabic text (graphemes) to IPA phoneme sequences
using rule-based grapheme-to-phoneme (G2P) conversion.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from .models.phoneme import (
    Phoneme,
    PhonemeSequence,
    TextPosition,
    PhoneticFeatures,
    PhonemeInventory
)
from .models.enums import (
    PhonemeCategory,
    ArticulationManner,
    ArticulationPlace,
    VowelHeight,
    VowelBackness,
    VowelLength
)
from .text_processor import QuranTextProcessor
from .utils.diacritic_utils import (
    get_diacritics_for_letter,
    get_vowel_type,
    has_sukoon,
    has_shaddah,
    DiacriticType
)
from .utils.unicode_utils import (
    is_arabic_letter,
    remove_diacritics,
    ARABIC_ALIF,
    ARABIC_ALIF_WASLA,
    ARABIC_ALIF_MADDA,
    ARABIC_HAMZA,  # Standalone hamza ء
    ARABIC_ALIF_HAMZA_ABOVE,
    ARABIC_ALIF_HAMZA_BELOW,
    ARABIC_WAW_HAMZA,
    ARABIC_YEH_HAMZA,
    ARABIC_TEH_MARBUTA,
    FATHA,
    DAMMA,
    KASRA,
    SUKOON
)


# Sun letters (al-ḥurūf al-shamsiyya): the lam of ٱلْ assimilates into these.
# Orthographic evidence: the sun letter carries a shaddah in the written text.
_SUN_LETTERS = frozenset('تثدذرزسشصضطظلن')


# ── Muqaṭṭaʿāt (Disjoined Letters) ────────────────────────────────────────
# The 14 letters that open 29 sūrahs (الم، يس، كهيعص …). Each must be
# pronounced by its full LETTER NAME (alif, laam, meem, …) — not as ordinary
# Arabic graphemes — and each carries a specific madd category in Tajwīd.
#
# Detection happens at the WORD level in phonemize_word(), before
# _convert_letter() is reached. The trigger is the maddah mark U+0653 (ٓ),
# which the Hafṣ rasm places above each Muqaṭṭaʿāt letter that requires
# 6-count madd lāzim ḥarfī. The three single-letter sūrah openers ص (38:1),
# ق (50:1) and ن (68:1) may appear without the maddah mark in some editions
# and are matched by surah:position when surah/ayah context is supplied.
MADDAH_MARK = '\u0653'  # ٓ Arabic Maddah Above (combining)

# Letter-name → (IPA phonemes, madd rule, count). Counts: 6 = madd lāzim
# ḥarfī, 2 = madd ṭabīʿī, 0 = no madd at all (alif). Letters whose madd
# rule is 'madd_tabii' are left to the engine's existing madd_tabii rule,
# which fires automatically on the long vowel; only madd_lazim cases need
# to be injected via muqattaat_rule_specs because the engine cannot infer
# Muqaṭṭaʿāt context from the phoneme stream.
MUQATTAAT_LETTER_NAMES = {
    'ا': (['ʔ', 'a', 'l', 'i', 'f'], None,         0),  # alif — no madd
    'ح': (['h', 'aː'],                'madd_tabii', 2),  # ha
    'ي': (['j', 'aː'],                'madd_tabii', 2),  # ya
    'ط': (['tˤ', 'aː'],               'madd_tabii', 2),  # ta
    'ه': (['h', 'aː'],                'madd_tabii', 2),  # ha
    'ر': (['r', 'aː'],                'madd_tabii', 2),  # ra
    'ل': (['l', 'aː', 'm'],           'madd_lazim', 6),  # lam
    'م': (['m', 'iː', 'm'],           'madd_lazim', 6),  # mim
    'ك': (['k', 'aː', 'f'],           'madd_lazim', 6),  # kaf
    'ع': (['ʕ', 'aj', 'n'],           'madd_lazim', 6),  # ayn — 6 counts
    'س': (['s', 'iː', 'n'],           'madd_lazim', 6),  # sin
    'ن': (['n', 'uː', 'n'],           'madd_lazim', 6),  # nun
    'ق': (['q', 'aː', 'f'],           'madd_lazim', 6),  # qaf
    'ص': (['sˤ', 'aː', 'd'],          'madd_lazim', 6),  # sad
}

# Surah:ayah positions where a single Muqaṭṭaʿāt letter may appear without
# the maddah mark in some rasm editions. Used as a fallback for detection
# when surah/ayah context is provided.
MUQATTAAT_UNMARKED = {
    (38, 1): 'ص',  # Sūrat Ṣād
    (50, 1): 'ق',  # Sūrat Qāf
    (68, 1): 'ن',  # Sūrat al-Qalam (Nūn)
}

# Qalqalah letter symbols — used to identify which phoneme inside a
# Muqaṭṭaʿāt letter-name should carry qalqalah_major.
_QALQALAH_PHONEME_SYMBOLS = frozenset({'q', 'tˤ', 'b', 'dʒ', 'd'})


class QuranPhonemizer:
    """
    Converts Qur'anic Arabic text to phoneme sequences.

    Loads phoneme inventories and G2P rules from YAML files and performs
    context-aware grapheme-to-phoneme conversion.
    """

    def __init__(
        self,
        base_phonemes_path: Optional[str] = None,
        tajweed_phonemes_path: Optional[str] = None,
        g2p_rules_path: Optional[str] = None
    ):
        """
        Initialize the phonemizer.

        Args:
            base_phonemes_path: Path to base phonemes YAML file
            tajweed_phonemes_path: Path to Tajweed phonemes YAML file
            g2p_rules_path: Path to G2P rules YAML file
        """
        # Default paths
        if base_phonemes_path is None:
            base_phonemes_path = "data/pronunciation_dict/base_phonemes.yaml"
        if tajweed_phonemes_path is None:
            tajweed_phonemes_path = "data/pronunciation_dict/tajweed_phonemes.yaml"
        if g2p_rules_path is None:
            g2p_rules_path = "data/pronunciation_dict/g2p_rules.yaml"

        # Load configurations
        self.phoneme_inventory = self._load_phoneme_inventory(
            base_phonemes_path,
            tajweed_phonemes_path
        )
        self.g2p_rules = self._load_g2p_rules(g2p_rules_path)

        # Text processor for normalization (use NFC to preserve combined hamza characters)
        self.text_processor = QuranTextProcessor(normalization_form="NFC")

        # Build lookup tables
        self._build_lookup_tables()

    def _load_phoneme_inventory(
        self,
        base_path: str,
        tajweed_path: str
    ) -> PhonemeInventory:
        """Load phoneme inventory from YAML files."""
        consonants = []
        vowels = []
        tajweed_phonemes = []

        # Load base phonemes
        with open(base_path, 'r', encoding='utf-8') as f:
            base_data = yaml.safe_load(f)

        # Parse consonants
        for cons_data in base_data.get('consonants', []):
            phoneme = self._create_phoneme_from_yaml(cons_data, PhonemeCategory.CONSONANT)
            consonants.append(phoneme)

        # Parse vowels
        for vowel_data in base_data.get('vowels', []):
            phoneme = self._create_phoneme_from_yaml(vowel_data, PhonemeCategory.VOWEL)
            vowels.append(phoneme)

        # Load Tajweed phonemes
        with open(tajweed_path, 'r', encoding='utf-8') as f:
            tajweed_data = yaml.safe_load(f)

        for tj_data in tajweed_data.get('tajweed_phonemes', []):
            phoneme = self._create_phoneme_from_yaml(tj_data, PhonemeCategory.TAJWEED)
            tajweed_phonemes.append(phoneme)

        return PhonemeInventory(
            consonants=consonants,
            vowels=vowels,
            tajweed_phonemes=tajweed_phonemes
        )

    def _create_phoneme_from_yaml(
        self,
        data: Dict,
        category: PhonemeCategory
    ) -> Phoneme:
        """Create a Phoneme object from YAML data."""
        features_data = data.get('features', {})

        # Create phonetic features
        features = PhoneticFeatures(
            manner=ArticulationManner(features_data.get('manner')) if features_data.get('manner') else None,
            place=ArticulationPlace(features_data.get('place')) if features_data.get('place') else None,
            voicing=features_data.get('voicing'),
            emphatic=features_data.get('emphatic', False),
            height=VowelHeight(features_data.get('height')) if features_data.get('height') else None,
            backness=VowelBackness(features_data.get('backness')) if features_data.get('backness') else None,
            rounding=features_data.get('rounding'),
            length=VowelLength(features_data.get('length')) if features_data.get('length') else None,
            nasalized=features_data.get('nasalized', False),
            geminated=features_data.get('geminated', False)
        )

        return Phoneme(
            symbol=data['symbol'],
            category=category,
            features=features,
            duration_factor=data.get('duration_factor', 1.0),
            arabic_letter=data.get('arabic'),
            description=data.get('description'),
            formants=data.get('formants')
        )

    def _load_g2p_rules(self, path: str) -> Dict:
        """Load G2P rules from YAML file."""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_lookup_tables(self):
        """Build lookup tables for fast G2P conversion."""
        # Consonant mappings
        self.consonant_map = {}
        for symbol, arabic in self.g2p_rules.get('consonant_mappings', {}).items():
            self.consonant_map[symbol] = arabic

        # Diacritic mappings
        self.diacritic_map = {}
        for symbol, phoneme in self.g2p_rules.get('diacritic_mappings', {}).items():
            self.diacritic_map[symbol] = phoneme

    def phonemize(
        self,
        text: str,
        surah: Optional[int] = None,
        ayah: Optional[int] = None,
    ) -> PhonemeSequence:
        """
        Convert Arabic text to phoneme sequence.

        Args:
            text: Qur'anic Arabic text with diacritics
            surah: Optional sūrah number — used to recognise unmarked
                Muqaṭṭaʿāt openings (ص at 38:1, ق at 50:1, ن at 68:1).
            ayah: Optional āyah number, paired with ``surah``.

        Returns:
            PhonemeSequence object
        """
        # Normalize text
        text = self.text_processor.normalize(text)

        # Validate. Muqaṭṭaʿāt-only text would otherwise fail the strict
        # diacritic validator because it carries the maddah mark instead
        # of fatha/damma/kasra (e.g. "الٓمٓ"), or — for the three single
        # letter sūrah openers ص (38:1), ق (50:1), ن (68:1) — may carry
        # no marks at all. Skip the strict check in either of these cases:
        #   • the text contains the maddah mark anywhere, OR
        #   • a (surah, ayah) pair was supplied that matches one of the
        #     unmarked Muqaṭṭaʿāt positions.
        is_unmarked_muqattaat = (
            surah is not None and ayah is not None
            and (surah, ayah) in MUQATTAAT_UNMARKED
        )
        if MADDAH_MARK not in text and not is_unmarked_muqattaat:
            is_valid, message = self.text_processor.validate_text(text, require_diacritics=True)
            if not is_valid:
                raise ValueError(f"Invalid text for phonemization: {message}")

        # Get words
        words = self.text_processor.segment_by_word(text)

        # Phonemize each word
        all_phonemes = []
        all_positions = []
        word_boundaries = []
        word_texts = []
        muqattaat_rule_specs: List[Dict[str, Any]] = []
        current_position = 0

        for word_idx, word in enumerate(words):
            is_verse_initial = (word_idx == 0)
            word_phonemes, word_positions, word_specs = self.phonemize_word(
                word,
                is_verse_initial=is_verse_initial,
                surah=surah,
                ayah=ayah,
            )

            # Re-base muqattaat rule specs from word-local phoneme indices to
            # global indices in the assembled sequence.
            base = len(all_phonemes)
            for spec in word_specs:
                muqattaat_rule_specs.append({
                    'phoneme_index': spec['phoneme_index'] + base,
                    'rule_name': spec['rule_name'],
                })

            # If this word starts with ٱ (hamza wasla, U+0671), mark the first
            # phoneme so the engine can suppress madd_tabii on the preceding
            # word's final long vowel (wasla is silent, not a true hamza).
            if word_phonemes:
                first_arabic_char = next(
                    (c for c in word if is_arabic_letter(c) or c == ARABIC_ALIF_WASLA),
                    None
                )
                if first_arabic_char == ARABIC_ALIF_WASLA:
                    word_phonemes[0] = word_phonemes[0].model_copy(
                        update={'arabic_letter': ARABIC_ALIF_WASLA}
                    )

            # Mark word boundary
            if word_idx > 0:
                word_boundaries.append(len(all_phonemes))

            # Track original word text
            word_texts.append(word)

            # Add to global lists
            all_phonemes.extend(word_phonemes)
            all_positions.extend(word_positions)
            current_position += len(word)

        return PhonemeSequence(
            phonemes=all_phonemes,
            positions=all_positions,
            word_boundaries=word_boundaries,
            word_texts=word_texts,
            original_text=text,
            muqattaat_rule_specs=muqattaat_rule_specs,
        )

    def phonemize_word(
        self,
        word: str,
        is_verse_initial: bool = False,
        surah: Optional[int] = None,
        ayah: Optional[int] = None,
    ) -> Tuple[List[Phoneme], List[TextPosition], List[Dict[str, Any]]]:
        """
        Phonemize a single word.

        Args:
            word: Single Arabic word with diacritics
            is_verse_initial: True if this is the first word of the verse
                (ibtidāʾ context). Affects Hamzat al-Wasl (ٱ) pronunciation:
                - ibtidāʾ: ٱ → ʔ + vowel (pronounced)
                - waṣl:    ٱ → silent (default, current behavior)
            surah, ayah: Optional verse coordinates. Only used to detect the
                three single-letter Muqaṭṭaʿāt openings (ص at 38:1, ق at
                50:1, ن at 68:1) when they appear without the maddah mark.

        Returns:
            Tuple of (phonemes, positions, muqattaat_rule_specs). The rule
            specs are word-local — `phonemize` rebases them to global indices.
        """
        word = self.text_processor.normalize(word)

        # ── Muqaṭṭaʿāt fast path ──────────────────────────────────────────
        # If the word is a disjoined-letter sequence, every letter must be
        # pronounced by its full name from MUQATTAAT_LETTER_NAMES, not by
        # the ordinary G2P pipeline. Detection happens here, BEFORE the
        # main letter loop, so _convert_letter() is bypassed entirely.
        if self._is_muqattaat_word(word, surah=surah, ayah=ayah):
            return self._phonemize_muqattaat_word(word)

        phonemes = []
        positions = []

        # ── Hamzat al-Wasl ibtidāʾ handling ─────────────────────────────────
        # U+0671 (ٱ) is filtered out by is_arabic_letter(), so it never reaches
        # _convert_letter(). Handle it here as a pre-pass before the main loop.
        #
        # Hafs ʿan ʿĀṣim ibtidāʾ vowel rules:
        #   • ٱللَّهِ (the word Allāh)  → fatha  (a): [ʔ a l l aː h i]
        #   • All other ٱل forms       → fatha  (a): [ʔ a l ...]
        #   • Verb/maṣdar forms        → damma (u) if 3rd letter has damma,
        #                                 kasra (i) otherwise
        if is_verse_initial and word and word[0] == ARABIC_ALIF_WASLA:
            stripped = remove_diacritics(word)
            is_definite_article = stripped.startswith('\u0671\u0644')  # ٱل…

            # The 7 fixed nouns with hamzat al-wasl always take kasra.
            # Check stripped (no-diacritics) form against known stems.
            _FIXED_NOUN_STEMS = ('ٱسم', 'ٱبن', 'ٱمرأ', 'ٱمرؤ', 'ٱثن')
            is_fixed_noun = any(
                stripped.startswith(stem) for stem in _FIXED_NOUN_STEMS
            )

            if is_definite_article:
                ibtidar_vowel = 'a'
            elif is_fixed_noun:
                ibtidar_vowel = 'i'
            else:
                # Verb / maṣdar: check diacritic on the 3rd base letter.
                # Scan the raw word (with diacritics) to find the character
                # index of the 3rd base letter (skipping ٱ which is not in
                # is_arabic_letter range, and skipping diacritic characters).
                third_letter_char_idx = None
                base_count = 0
                for ci, ch in enumerate(word):
                    if is_arabic_letter(ch):
                        base_count += 1
                        if base_count == 2:  # 2nd base letter = 3rd letter of word
                            third_letter_char_idx = ci
                            break

                if third_letter_char_idx is not None:
                    third_vowel = get_vowel_type(word, third_letter_char_idx)
                    ibtidar_vowel = 'u' if third_vowel == DiacriticType.DAMMA else 'i'
                else:
                    ibtidar_vowel = 'i'  # fallback

            phonemes.append(self._get_phoneme('ʔ'))
            phonemes.append(self._get_phoneme(ibtidar_vowel))
            # Both phonemes map to the wasla character at text_index=0
            positions.append(TextPosition(text_index=0, grapheme=ARABIC_ALIF_WASLA, word_index=0))
            positions.append(TextPosition(text_index=0, grapheme=ARABIC_ALIF_WASLA, word_index=0))

        # Get letters without diacritics for iteration
        letters_only = remove_diacritics(word)
        letter_list = [c for c in letters_only if is_arabic_letter(c)]

        text_index = 0
        prev_vowel = None  # Track previous letter's vowel for long vowel creation

        for letter_idx, letter in enumerate(letter_list):
            # Find letter position in original word
            while text_index < len(word) and word[text_index] != letter:
                text_index += 1

            if text_index >= len(word):
                break

            # Get context
            prev_letter = letter_list[letter_idx - 1] if letter_idx > 0 else None
            next_letter = letter_list[letter_idx + 1] if letter_idx < len(letter_list) - 1 else None

            # Get diacritics for this letter
            diacritics = get_diacritics_for_letter(word, text_index)
            vowel = get_vowel_type(word, text_index)
            has_sukoon_mark = has_sukoon(word, text_index)
            has_shaddah_mark = has_shaddah(word, text_index)
            has_dagger_alif = DiacriticType.DAGGER_ALIF in diacritics  # Check for ٰ

            # Check for superscript wāw (ۥ) - indicates long ū in Qur'anic text
            # Import the constant
            from .utils.unicode_utils import SUPERSCRIPT_WAW
            has_superscript_waw = SUPERSCRIPT_WAW in word[text_index:text_index+5]  # Check nearby chars

            # ── Shamsiyya (lam assimilation) ──────────────────────────────────
            # The lam of the definite article ٱلْ has no explicit vowel in
            # shamsiyya words (the shaddah on the sun letter is the orthographic
            # evidence of assimilation). When this pattern is detected, suppress
            # the lam completely — the sun letter's shaddah produces the geminate.
            #
            # Conditions: current letter is ل, no vowel on it, next letter is a
            # sun letter, and that next letter carries a shaddah.
            if letter == 'ل' and vowel is None and next_letter in _SUN_LETTERS:
                nxt_idx = text_index + 1
                while nxt_idx < len(word) and not is_arabic_letter(word[nxt_idx]):
                    nxt_idx += 1
                if nxt_idx < len(word) and has_shaddah(word, nxt_idx):
                    # Lam assimilates: emit nothing, advance and continue.
                    prev_vowel = vowel  # = None
                    text_index += 1
                    continue

            # Convert letter to phoneme(s)
            letter_phonemes = self._convert_letter(
                letter,
                vowel,
                has_sukoon_mark,
                has_shaddah_mark,
                prev_letter,
                prev_vowel,  # NEW: Pass previous letter's vowel
                next_letter,
                letter_idx,
                len(letter_list),
                has_dagger_alif,  # NEW: Pass dagger alif flag
                has_superscript_waw  # NEW: Pass superscript waw flag
            )

            # Update prev_vowel for next iteration
            prev_vowel = vowel

            # Add phonemes with positions
            for phoneme in letter_phonemes:
                phonemes.append(phoneme)
                positions.append(TextPosition(
                    text_index=text_index,
                    grapheme=letter,
                    word_index=0  # Will be set by caller
                ))

            text_index += 1

        return (phonemes, positions, [])

    # ── Muqaṭṭaʿāt helpers ────────────────────────────────────────────────
    def _is_muqattaat_word(
        self,
        word: str,
        surah: Optional[int] = None,
        ayah: Optional[int] = None,
    ) -> bool:
        """
        Decide whether a word is a Muqaṭṭaʿāt (disjoined-letter) sequence.

        Two detection paths:
        1. The word contains the maddah mark U+0653 AND every Arabic letter
           in the word is in MUQATTAAT_LETTER_NAMES. This is the common
           case in the Hafṣ rasm (الٓمٓ, يسٓ, كٓهيعٓصٓ, صٓ, قٓ, نٓ).
        2. The (surah, ayah) pair is one of the three positions where a
           single Muqaṭṭaʿāt letter may appear without the maddah mark
           (38:1, 50:1, 68:1) AND the word's only base letter matches.
        """
        if MADDAH_MARK in word:
            letter_list = [c for c in remove_diacritics(word) if is_arabic_letter(c)]
            if letter_list and all(c in MUQATTAAT_LETTER_NAMES for c in letter_list):
                return True

        if surah is not None and ayah is not None:
            unmarked = MUQATTAAT_UNMARKED.get((surah, ayah))
            if unmarked:
                bare = [c for c in remove_diacritics(word) if is_arabic_letter(c)]
                if len(bare) == 1 and bare[0] == unmarked:
                    return True

        return False

    def _phonemize_muqattaat_word(
        self,
        word: str,
    ) -> Tuple[List[Phoneme], List[TextPosition], List[Dict[str, Any]]]:
        """
        Build phonemes and rule specs for a Muqaṭṭaʿāt word.

        Each Arabic letter is replaced by its full LETTER NAME phonemes from
        MUQATTAAT_LETTER_NAMES (e.g. ل → [l, aː, m]). For each letter we
        also record any rule specs that the engine cannot infer from the
        phoneme stream alone:

          • madd_lazim — for letters whose name carries 6-count madd lāzim
            ḥarfī. Attached to the long vowel / diphthong inside the
            letter-name. The engine's conflict resolver will then suppress
            the duplicate madd_tabii that the standard rules would fire on
            the same long vowel.
          • qalqalah_major — only for ق, whose 'q' is the qalqalah letter
            but is not at sukoon in the letter-name pronunciation, so the
            standard qalqalah_major rule (which requires has_sukoon) does
            not fire on it. For ص the standard rule already fires on the
            final 'd' (which IS at sukoon at word end), so no spec is
            needed there.
          • ghunnah — at the lām→mīm junction inside الم-style sequences.
            Recorded on the first phoneme of the following mīm letter-name.
        """
        phonemes: List[Phoneme] = []
        positions: List[TextPosition] = []
        rule_specs: List[Dict[str, Any]] = []

        # Map text indices for each letter so positions point at something
        # the user could highlight back in the original word.
        letters: List[Tuple[int, str]] = []
        for ti, ch in enumerate(word):
            if is_arabic_letter(ch) and ch in MUQATTAAT_LETTER_NAMES:
                letters.append((ti, ch))

        prev_letter: Optional[str] = None
        for letter_text_index, letter in letters:
            symbols, madd_rule, _count = MUQATTAAT_LETTER_NAMES[letter]

            # Where this letter-name's phonemes start in the word's phoneme list.
            letter_phoneme_start = len(phonemes)

            for sym in symbols:
                phoneme = self._get_phoneme(sym)
                phonemes.append(phoneme)
                positions.append(TextPosition(
                    text_index=letter_text_index,
                    grapheme=letter,
                    word_index=0,  # set by caller
                ))

            # madd_lazim: attach to the second phoneme of the letter-name,
            # which is always the long vowel (or diphthong for ʿayn) per
            # MUQATTAAT_LETTER_NAMES.
            if madd_rule == 'madd_lazim' and len(symbols) >= 2:
                rule_specs.append({
                    'phoneme_index': letter_phoneme_start + 1,
                    'rule_name': 'madd_lazim',
                })

            # qalqalah_major on ق's initial 'q' — the standard engine rule
            # cannot fire here because 'q' is followed by a long vowel (no
            # sukoon). For ص the engine fires it automatically on the final
            # 'd' at word end, so no manual spec is required.
            if letter == 'ق':
                for offset, sym in enumerate(symbols):
                    if sym in _QALQALAH_PHONEME_SYMBOLS:
                        rule_specs.append({
                            'phoneme_index': letter_phoneme_start + offset,
                            'rule_name': 'qalqalah_major',
                        })
                        break

            # ghunnah at lām→mīm junction (idgham bi-ghunnah on the meem
            # at the start of the مٓ letter-name immediately following لٓ).
            if prev_letter == 'ل' and letter == 'م':
                rule_specs.append({
                    'phoneme_index': letter_phoneme_start,
                    'rule_name': 'ghunnah',
                })

            prev_letter = letter

        return (phonemes, positions, rule_specs)

    def _convert_letter(
        self,
        letter: str,
        vowel: Optional[DiacriticType],
        has_sukoon: bool,
        has_shaddah: bool,
        prev_letter: Optional[str],
        prev_vowel: Optional[DiacriticType],  # NEW: Previous letter's vowel
        next_letter: Optional[str],
        position: int,
        word_length: int,
        has_dagger_alif: bool = False,  # NEW: Dagger alif (ٰ) indicates long aː
        has_superscript_waw: bool = False  # NEW: Superscript wāw (ۥ) indicates long ū
    ) -> List[Phoneme]:
        """
        Convert a single letter with its diacritics to phoneme(s).

        Args:
            prev_vowel: Vowel diacritic of previous letter (for long vowel creation)
            has_dagger_alif: True if letter has dagger alif (ٰ), creates long aː
            has_superscript_waw: True if letter has superscript wāw (ۥ), creates long ū

        Returns:
            List of phonemes (can be multiple for shaddah)
        """
        phonemes = []

        # Handle hamza first (standalone hamza ء)
        if letter == ARABIC_HAMZA:
            phonemes.append(self._get_phoneme('ʔ'))
            if vowel:
                vowel_phonemes = self._vowel_to_phoneme(vowel)
                phonemes.extend(vowel_phonemes)
            return phonemes

        # Handle special letters
        if letter == ARABIC_ALIF:
            alif_phonemes = self._handle_alif(letter, vowel, prev_letter, prev_vowel, position)
            phonemes.extend(alif_phonemes)
        elif letter == ARABIC_ALIF_WASLA:
            # Hamzat al-wasl - silent in continuation
            if position == 0:
                phonemes.append(self._get_phoneme('ʔ'))  # Pronounced as hamza at start
        elif letter == ARABIC_ALIF_MADDA:
            # آ = hamza + long aa
            phonemes.append(self._get_phoneme('ʔ'))
            phonemes.append(self._get_phoneme('aː'))
        elif letter == ARABIC_ALIF_HAMZA_ABOVE:
            # أ = hamza + short a
            phonemes.append(self._get_phoneme('ʔ'))
            if vowel:
                vowel_phonemes = self._vowel_to_phoneme(vowel)
                phonemes.extend(vowel_phonemes)
        elif letter == ARABIC_ALIF_HAMZA_BELOW:
            # إ = hamza + short i
            phonemes.append(self._get_phoneme('ʔ'))
            if vowel:
                vowel_phonemes = self._vowel_to_phoneme(vowel)
                phonemes.extend(vowel_phonemes)
        elif letter == ARABIC_WAW_HAMZA:
            # ؤ = hamza on waaw
            phonemes.append(self._get_phoneme('ʔ'))
            phonemes.append(self._get_phoneme('u'))
        elif letter == ARABIC_YEH_HAMZA:
            # ئ = hamza on yaa-seat; the seat is purely orthographic (does not
            # contribute a kasra).  Use whatever diacritic is actually written.
            # Examples: خَاسِئًا → ʔ + a + n (tanween fath), ئِفًّا → ʔ + i + …
            phonemes.append(self._get_phoneme('ʔ'))
            if vowel:
                vowel_phonemes = self._vowel_to_phoneme(vowel)
                phonemes.extend(vowel_phonemes)
        elif letter == ARABIC_TEH_MARBUTA:
            # ة - Tāʾ Marbūṭa pronunciation depends on context
            # In continuing (waṣl): pronounced as 't' (taa)
            # In stopping (waqf): pronounced as 'h' (haa)
            if position == word_length - 1:
                # At word end - will be determined by context (waṣl vs waqf)
                # For now, default to 't' (continuing pronunciation)
                # The Tajweed engine will detect when to use 'h' (stopping)
                # Tag the phoneme with arabic_letter='ة' so engine can identify it precisely
                base_phoneme = self._get_phoneme('t')
                ta_marbuta_phoneme = base_phoneme.model_copy(update={'arabic_letter': ARABIC_TEH_MARBUTA})
                phonemes.append(ta_marbuta_phoneme)
                if vowel:
                    vowel_phonemes = self._vowel_to_phoneme(vowel)
                    phonemes.extend(vowel_phonemes)
            else:
                # Mid-word - always pronounced as 't'
                phonemes.append(self._get_consonant_phoneme(letter))
                if vowel:
                    vowel_phonemes = self._vowel_to_phoneme(vowel)
                    phonemes.extend(vowel_phonemes)
        elif letter in ['و', 'ي', 'ى']:  # Waaw, Yaa, and Alif Maqsura
            waaw_yaa_phonemes = self._handle_waaw_yaa(
                letter, vowel, has_sukoon, prev_letter, prev_vowel, has_dagger_alif
            )
            phonemes.extend(waaw_yaa_phonemes)
        else:
            # Regular consonant
            cons_phoneme = self._get_consonant_phoneme(letter)
            if cons_phoneme:
                # Handle shaddah (gemination)
                if has_shaddah:
                    # Full gemination: consonant is doubled.
                    # Note: for the ٱللَّهِ / shamsiyya case, the article lam is
                    # already suppressed before this point, so the shaddah letter
                    # correctly produces exactly two copies here.
                    phonemes.append(cons_phoneme)
                    phonemes.append(cons_phoneme)
                else:
                    phonemes.append(cons_phoneme)

                # Add vowel if present (including tanween which adds vowel + noon)
                # Note: Tanween should be added even if has_sukoon is True
                # because tanween is a vowel+noon, not a sukoon
                if vowel:
                    # Skip vowel only if there's an explicit sukoon (not tanween)
                    if has_sukoon and vowel not in [DiacriticType.TANWEEN_FATH,
                                                      DiacriticType.TANWEEN_DAMM,
                                                      DiacriticType.TANWEEN_KASR]:
                        pass  # Skip vowel when sukoon is present
                    else:
                        vowel_phonemes = self._vowel_to_phoneme(vowel)
                        phonemes.extend(vowel_phonemes)

                # Handle dagger alif (alif khanjariyah) - creates long aː
                # Example: ٱلرَّحْمَٰنِ - the م has dagger alif creating long aː
                if has_dagger_alif:
                    phonemes.append(self._get_phoneme('aː'))

                # Handle superscript wāw - creates long ū
                # Example: لَّهُۥٓ - the ه has damma + superscript wāw creating long ū
                # IMPORTANT: Mark with SUPERSCRIPT_WAW so it's not treated as waṣl mater lectionis
                if has_superscript_waw:
                    from .utils.unicode_utils import SUPERSCRIPT_WAW
                    base_phoneme = self._get_phoneme('uː')
                    # Set arabic_letter to superscript wāw to distinguish from regular و
                    superscript_phoneme = base_phoneme.model_copy(update={'arabic_letter': SUPERSCRIPT_WAW})
                    phonemes.append(superscript_phoneme)

        return phonemes

    def _handle_alif(
        self,
        letter: str,
        vowel: Optional[DiacriticType],
        prev_letter: Optional[str],
        prev_vowel: Optional[DiacriticType],  # NEW: Previous letter's vowel
        position: int
    ) -> List[Phoneme]:
        """
        Handle alif which is context-dependent.

        Alif creates long 'aː' when previous letter has fatha.
        """
        phonemes = []

        # Alif after fatha = long aa
        if prev_letter and prev_vowel == DiacriticType.FATHA and position > 0:
            # Previous consonant has fatha → alif creates long 'aː'
            # Example: قَالَ → [q, a, aː, l, a]
            phonemes.append(self._get_phoneme('aː'))
        elif position == 0:
            # Word-initial alif is often silent (e.g., في ٱسْمِ ٱللهِ)
            # Or it's part of hamza (handled in _convert_letter)
            pass

        return phonemes

    def _handle_waaw_yaa(
        self,
        letter: str,
        vowel: Optional[DiacriticType],
        has_sukoon: bool,
        prev_letter: Optional[str],
        prev_vowel: Optional[DiacriticType],
        has_dagger_alif: bool = False
    ) -> List[Phoneme]:
        """
        Handle waaw/yaa which can be consonant or long vowel marker.

        Long vowel rules:
        - و creates uː when previous letter has damma (e.g., هُوَ → [h, uː])
        - ي creates iː when previous letter has kasra (e.g., فِيهِ → [f, iː, h, i])
        """
        phonemes = []

        if letter == 'و':  # Waaw
            if prev_vowel == DiacriticType.DAMMA:
                if vowel:
                    # Waw has its own vowel → consonant 'w' + that vowel
                    # Examples: هُوَ (huwa) → h u w a, كُفُوًا (kufuwan) → k u f u w a n
                    phonemes.append(self._get_phoneme('w'))
                    vowel_phonemes = self._vowel_to_phoneme(vowel)
                    phonemes.extend(vowel_phonemes)
                else:
                    # Waw has no vowel after damma → long vowel uː
                    # Examples: أَعُوذُ → ʕ u uː ð u, صُدُورِ → d u uː r i
                    phonemes.append(self._get_phoneme('uː'))
            elif has_sukoon or (not vowel):
                # Waaw with sukoon or no vowel (without damma before)
                # Could be consonantal w with implicit vowel
                phonemes.append(self._get_phoneme('w'))
            elif vowel:
                # Consonant waaw with following vowel
                # Examples: وَلَد (walad), يَوْم (yawm)
                phonemes.append(self._get_phoneme('w'))
                if has_dagger_alif and vowel == DiacriticType.FATHA:
                    # Dagger alif extends the fatha to long aː
                    # Example: وَٰحِدَةٍ → [w, aː, ħ, i, d, ...]
                    phonemes.append(self._get_phoneme('aː'))
                else:
                    vowel_phonemes = self._vowel_to_phoneme(vowel)
                    phonemes.extend(vowel_phonemes)

        elif letter in ('ي', 'ى'):  # Yaa and Alif Maqsura (ى acts as yaa)
            if prev_vowel == DiacriticType.KASRA:
                if vowel:
                    # Yaa has its own vowel → consonant 'j' + that vowel
                    phonemes.append(self._get_phoneme('j'))
                    vowel_phonemes = self._vowel_to_phoneme(vowel)
                    phonemes.extend(vowel_phonemes)
                else:
                    # Yaa has no vowel after kasra → long vowel iː
                    # Examples: فِيهِ (fiihi) → f iː h i, فِى (fī) → f iː
                    phonemes.append(self._get_phoneme('iː'))
            elif prev_vowel == DiacriticType.FATHA and not vowel and not has_sukoon:
                # Alif maqsura (ى) after fatha with no explicit vowel → long aː
                # Examples: عَلَى → [ʕ, a, aː], حَتَّىٰ → [..., t, t, aː]
                #            أَدْرَىٰ → [..., d, r, aː], مَتَى → [..., t, aː]
                phonemes.append(self._get_phoneme('aː'))
            elif has_sukoon or (not vowel):
                # Yaa with sukoon or no vowel in other contexts → consonant j
                # Examples: عَلَيْهِمْ (yaa + sukoon), يَوْم (yaa + own vowel)
                phonemes.append(self._get_phoneme('j'))
            elif vowel:
                # Consonant yaa with following vowel
                # Examples: يَوْم (yawm), أَيْن (ayna)
                phonemes.append(self._get_phoneme('j'))
                if has_dagger_alif and vowel == DiacriticType.FATHA:
                    # Dagger alif extends the fatha to long aː
                    # Example: يَٰٓأَيُّهَا → [j, aː, ʔ, ...] → madd_muttasil
                    phonemes.append(self._get_phoneme('aː'))
                else:
                    vowel_phonemes = self._vowel_to_phoneme(vowel)
                    phonemes.extend(vowel_phonemes)

        return phonemes

    def _get_consonant_phoneme(self, letter: str) -> Optional[Phoneme]:
        """Get phoneme for a consonant letter."""
        # Lookup in consonant mappings
        mappings = self.g2p_rules.get('consonant_mappings', {})
        symbol = mappings.get(letter)

        if symbol:
            return self._get_phoneme(symbol)
        return None

    def _vowel_to_phoneme(self, vowel: DiacriticType) -> List[Phoneme]:
        """
        Convert vowel diacritic to phoneme(s).

        Returns:
            List of phonemes (2 for tanween: vowel + noon, 1 for regular vowels)
        """
        vowel_map = {
            DiacriticType.FATHA: 'a',
            DiacriticType.DAMMA: 'u',
            DiacriticType.KASRA: 'i',
            DiacriticType.TANWEEN_FATH: 'an',
            DiacriticType.TANWEEN_DAMM: 'un',
            DiacriticType.TANWEEN_KASR: 'in',
        }

        symbol = vowel_map.get(vowel)
        if symbol:
            # Handle tanween specially - returns TWO phonemes: vowel + noon
            if vowel in [DiacriticType.TANWEEN_FATH, DiacriticType.TANWEEN_DAMM, DiacriticType.TANWEEN_KASR]:
                base_vowel = symbol[0]  # 'a', 'u', or 'i'
                vowel_phoneme = self._get_phoneme(base_vowel)
                noon_phoneme = self._get_phoneme('n')
                return [vowel_phoneme, noon_phoneme]

            # Regular vowel - return single phoneme in a list
            return [self._get_phoneme(symbol)]

        return []

    def _get_phoneme(self, symbol: str) -> Phoneme:
        """Get phoneme object by symbol."""
        phoneme = self.phoneme_inventory.get_by_symbol(symbol)
        if phoneme:
            return phoneme

        # If not found, create a basic phoneme
        # This is a fallback and should ideally not happen
        return Phoneme(
            symbol=symbol,
            category=PhonemeCategory.CONSONANT,
            features=PhoneticFeatures(),
            duration_factor=1.0
        )

    def get_phoneme_inventory(self) -> PhonemeInventory:
        """Get the loaded phoneme inventory."""
        return self.phoneme_inventory

    def __repr__(self) -> str:
        return f"QuranPhonemizer(phonemes={len(self.phoneme_inventory.get_all_phonemes())})"
