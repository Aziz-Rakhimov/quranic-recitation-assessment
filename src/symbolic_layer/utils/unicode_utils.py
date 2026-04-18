"""
Unicode utilities for Arabic text processing.

This module provides functions for normalizing Arabic text, handling Unicode
combining characters, and managing diacritics.
"""

import unicodedata
import re
from typing import List, Tuple


# Unicode ranges for Arabic characters
ARABIC_LETTER_RANGE = (0x0621, 0x064A)  # Arabic letters
ARABIC_DIACRITIC_RANGE = (0x064B, 0x0652)  # Diacritics
ARABIC_EXTENDED_RANGE = (0x0653, 0x065F)  # Extended marks
ARABIC_SUPPLEMENT_RANGE = (0x0750, 0x077F)  # Arabic Supplement

# Specific Arabic characters
ARABIC_TATWEEL = '\u0640'  # ـ Tatweel/Kashida
ARABIC_HAMZA = '\u0621'  # ء
ARABIC_ALIF = '\u0627'  # ا
ARABIC_ALIF_WASLA = '\u0671'  # ٱ Alif wasla
ARABIC_ALIF_MADDA = '\u0622'  # آ Alif with madda
ARABIC_ALIF_HAMZA_ABOVE = '\u0623'  # أ Alif with hamza above
ARABIC_ALIF_HAMZA_BELOW = '\u0625'  # إ Alif with hamza below
ARABIC_WAW_HAMZA = '\u0624'  # ؤ Waw with hamza
ARABIC_YEH_HAMZA = '\u0626'  # ئ Yeh with hamza
ARABIC_TEH_MARBUTA = '\u0629'  # ة Teh marbuta

# Diacritics
FATHA = '\u064E'  # َ
DAMMA = '\u064F'  # ُ
KASRA = '\u0650'  # ِ
SUKOON = '\u0652'  # ْ
SHADDAH = '\u0651'  # ّ
TANWEEN_FATH = '\u064B'  # ً
TANWEEN_DAMM = '\u064C'  # ٌ
TANWEEN_KASR = '\u064D'  # ٍ
DAGGER_ALIF = '\u0670'  # ٰ Alif khanjariyah
HAMZA_ABOVE = '\u0654'  # ٔ
HAMZA_BELOW = '\u0655'  # ٕ
SUPERSCRIPT_WAW = '\u06E5'  # ۥ Small wāw (indicates long ū in Qur'anic text)

# Quranic waqf (stop/pause) signs — recitation markers, not phonemic content
QURANIC_WAQF_SIGNS = {
    '\u06D6',  # ۖ ARABIC SMALL HIGH LIGATURE SAD WITH LAM WITH ALEF MAKSURA
    '\u06D7',  # ۗ ARABIC SMALL HIGH LIGATURE QAF WITH LAM WITH ALEF MAKSURA
    '\u06D8',  # ۘ ARABIC SMALL HIGH MEEM INITIAL FORM
    '\u06D9',  # ۙ ARABIC SMALL HIGH LAM ALEF
    '\u06DA',  # ۚ ARABIC SMALL HIGH JEEM
    '\u06DB',  # ۛ ARABIC SMALL HIGH THREE DOTS
    '\u06DC',  # ۜ ARABIC SMALL HIGH SEEN
    '\u06DD',  # ۝ ARABIC END OF AYAH
    '\u06DE',  # ۞ ARABIC START OF RUB EL HIZB
    '\u06DF',  # ۟ ARABIC SMALL HIGH ROUNDED ZERO
    '\u06E0',  # ۠ ARABIC SMALL HIGH UPRIGHT RECTANGULAR ZERO
    '\u06E2',  # ۢ ARABIC SMALL HIGH MEEM ISOLATED FORM
    '\u06ED',  # ۭ ARABIC SMALL LOW MEEM
}

# All diacritics
ALL_DIACRITICS = {
    FATHA, DAMMA, KASRA, SUKOON, SHADDAH,
    TANWEEN_FATH, TANWEEN_DAMM, TANWEEN_KASR,
    DAGGER_ALIF, HAMZA_ABOVE, HAMZA_BELOW, SUPERSCRIPT_WAW
}


def normalize_unicode(text: str, form: str = "NFD") -> str:
    """
    Normalize Unicode text.

    Args:
        text: Input text
        form: Normalization form - 'NFD', 'NFC', 'NFKD', or 'NFKC'
              NFD is preferred for Arabic as it decomposes combined characters

    Returns:
        Normalized text
    """
    if form not in ['NFD', 'NFC', 'NFKD', 'NFKC']:
        raise ValueError(f"Invalid normalization form: {form}")
    return unicodedata.normalize(form, text)


def remove_diacritics(text: str) -> str:
    """
    Remove all Arabic diacritics from text.

    Args:
        text: Arabic text with diacritics

    Returns:
        Text without diacritics
    """
    # Remove all combining marks (including diacritics)
    return ''.join(char for char in text if char not in ALL_DIACRITICS)


def remove_tatweel(text: str) -> str:
    """
    Remove tatweel (kashida) characters.

    Args:
        text: Arabic text

    Returns:
        Text without tatweel
    """
    return text.replace(ARABIC_TATWEEL, '')


def is_arabic_letter(char: str) -> bool:
    """
    Check if a character is an Arabic letter.

    Args:
        char: Single character

    Returns:
        True if Arabic letter, False otherwise
    """
    if not char:
        return False
    code = ord(char)
    return (
        ARABIC_LETTER_RANGE[0] <= code <= ARABIC_LETTER_RANGE[1] or
        ARABIC_SUPPLEMENT_RANGE[0] <= code <= ARABIC_SUPPLEMENT_RANGE[1]
    )


def is_arabic_diacritic(char: str) -> bool:
    """
    Check if a character is an Arabic diacritic.

    Args:
        char: Single character

    Returns:
        True if Arabic diacritic, False otherwise
    """
    return char in ALL_DIACRITICS


def is_arabic_text(text: str) -> bool:
    """
    Check if text contains Arabic characters.

    Args:
        text: Text to check

    Returns:
        True if text contains Arabic letters, False otherwise
    """
    return any(is_arabic_letter(char) for char in text)


def get_base_letter(text: str, position: int) -> Tuple[str, List[str]]:
    """
    Get the base letter and its diacritics at a position.

    Args:
        text: Normalized Arabic text (NFD)
        position: Character position

    Returns:
        Tuple of (base_letter, list_of_diacritics)
    """
    if position >= len(text):
        return ('', [])

    base_letter = text[position]
    diacritics = []

    # Collect following diacritics
    i = position + 1
    while i < len(text) and is_arabic_diacritic(text[i]):
        diacritics.append(text[i])
        i += 1

    return (base_letter, diacritics)


def separate_letters_and_diacritics(text: str) -> List[Tuple[str, List[str]]]:
    """
    Separate text into base letters with their diacritics.

    Args:
        text: Normalized Arabic text (NFD)

    Returns:
        List of (base_letter, diacritics) tuples
    """
    text = normalize_unicode(text, 'NFD')
    result = []
    i = 0

    while i < len(text):
        if is_arabic_letter(text[i]) or text[i] == ' ':
            base, diacritics = get_base_letter(text, i)
            result.append((base, diacritics))
            i += 1 + len(diacritics)
        else:
            # Skip non-Arabic characters
            i += 1

    return result


def has_diacritic(text: str, position: int, diacritic: str) -> bool:
    """
    Check if a letter at position has a specific diacritic.

    Args:
        text: Normalized Arabic text
        position: Position of base letter
        diacritic: Diacritic to check for

    Returns:
        True if letter has the diacritic, False otherwise
    """
    _, diacritics = get_base_letter(text, position)
    return diacritic in diacritics


def has_sukoon(text: str, position: int) -> bool:
    """Check if letter at position has sukoon."""
    return has_diacritic(text, position, SUKOON)


def has_shaddah(text: str, position: int) -> bool:
    """Check if letter at position has shaddah."""
    return has_diacritic(text, position, SHADDAH)


def has_fatha(text: str, position: int) -> bool:
    """Check if letter at position has fatha."""
    return has_diacritic(text, position, FATHA)


def has_damma(text: str, position: int) -> bool:
    """Check if letter at position has damma."""
    return has_diacritic(text, position, DAMMA)


def has_kasra(text: str, position: int) -> bool:
    """Check if letter at position has kasra."""
    return has_diacritic(text, position, KASRA)


def get_vowel_diacritic(text: str, position: int) -> str:
    """
    Get the vowel diacritic at a position.

    Args:
        text: Normalized Arabic text
        position: Position of base letter

    Returns:
        Vowel diacritic (fatha, damma, kasra) or empty string if none
    """
    _, diacritics = get_base_letter(text, position)
    vowel_diacritics = {FATHA, DAMMA, KASRA}

    for d in diacritics:
        if d in vowel_diacritics:
            return d

    return ''


def normalize_hamza(char: str) -> str:
    """
    Normalize various hamza forms to basic hamza.

    Args:
        char: Character to normalize

    Returns:
        Normalized character
    """
    hamza_forms = {
        ARABIC_ALIF_HAMZA_ABOVE: ARABIC_HAMZA,
        ARABIC_ALIF_HAMZA_BELOW: ARABIC_HAMZA,
        ARABIC_WAW_HAMZA: ARABIC_HAMZA,
        ARABIC_YEH_HAMZA: ARABIC_HAMZA,
    }
    return hamza_forms.get(char, char)


def is_hamza_carrier(char: str) -> bool:
    """
    Check if character is a hamza carrier (أ إ ؤ ئ).

    Args:
        char: Character to check

    Returns:
        True if hamza carrier, False otherwise
    """
    return char in {
        ARABIC_ALIF_HAMZA_ABOVE,
        ARABIC_ALIF_HAMZA_BELOW,
        ARABIC_WAW_HAMZA,
        ARABIC_YEH_HAMZA
    }


def clean_arabic_text(text: str, remove_tatweel_chars: bool = True) -> str:
    """
    Clean Arabic text by normalizing and optionally removing tatweel.

    Args:
        text: Input Arabic text
        remove_tatweel_chars: Whether to remove tatweel characters

    Returns:
        Cleaned text
    """
    # Normalize to NFD
    text = normalize_unicode(text, 'NFD')

    # Remove tatweel if requested
    if remove_tatweel_chars:
        text = remove_tatweel(text)

    # Remove zero-width characters
    text = text.replace('\u200B', '')  # Zero-width space
    text = text.replace('\u200C', '')  # Zero-width non-joiner
    text = text.replace('\u200D', '')  # Zero-width joiner
    text = text.replace('\uFEFF', '')  # Zero-width no-break space (BOM)

    # Remove Quranic waqf (stop) signs — recitation markers, not phonemic
    text = ''.join(c for c in text if c not in QURANIC_WAQF_SIGNS)

    return text


def extract_arabic_words(text: str) -> List[str]:
    """
    Extract Arabic words from text.

    Args:
        text: Mixed text with Arabic content

    Returns:
        List of Arabic words
    """
    # Pattern to match Arabic letters and diacritics
    arabic_pattern = r'[\u0621-\u064A\u064B-\u0652\u0670\u0671]+'
    words = re.findall(arabic_pattern, text)
    return words


def count_arabic_letters(text: str) -> int:
    """
    Count Arabic letters in text (excluding diacritics).

    Args:
        text: Arabic text

    Returns:
        Number of Arabic letters
    """
    text_without_diacritics = remove_diacritics(text)
    return sum(1 for char in text_without_diacritics if is_arabic_letter(char))


def validate_arabic_text(text: str, require_diacritics: bool = True) -> Tuple[bool, str]:
    """
    Validate Arabic text for processing.

    Args:
        text: Text to validate
        require_diacritics: Whether to require diacritics

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text or not text.strip():
        return (False, "Text is empty")

    if not is_arabic_text(text):
        return (False, "Text contains no Arabic characters")

    if require_diacritics:
        has_any_diacritic = any(is_arabic_diacritic(char) for char in text)
        if not has_any_diacritic:
            return (False, "Text lacks required diacritics for Qur'anic processing")

    return (True, "")
