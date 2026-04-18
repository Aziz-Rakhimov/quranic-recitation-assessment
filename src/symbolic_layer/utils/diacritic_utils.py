"""
Diacritic utilities for Arabic text processing.

This module provides functions for extracting, classifying, and analyzing
Arabic diacritics (harakat and other marks).
"""

from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from ..models.enums import DiacriticType
from .unicode_utils import (
    FATHA, DAMMA, KASRA, SUKOON, SHADDAH,
    TANWEEN_FATH, TANWEEN_DAMM, TANWEEN_KASR,
    DAGGER_ALIF, HAMZA_ABOVE, HAMZA_BELOW,
    is_arabic_letter, is_arabic_diacritic,
    normalize_unicode
)


@dataclass
class DiacriticInfo:
    """Information about a diacritic mark."""
    position: int  # Position in text
    character: str  # The diacritic character
    type: DiacriticType  # Type of diacritic
    base_char: str  # The base letter it modifies
    text_index: int  # Index in original text


# Mapping of Unicode characters to diacritic types
DIACRITIC_TYPE_MAP: Dict[str, DiacriticType] = {
    FATHA: DiacriticType.FATHA,
    DAMMA: DiacriticType.DAMMA,
    KASRA: DiacriticType.KASRA,
    SUKOON: DiacriticType.SUKOON,
    SHADDAH: DiacriticType.SHADDAH,
    TANWEEN_FATH: DiacriticType.TANWEEN_FATH,
    TANWEEN_DAMM: DiacriticType.TANWEEN_DAMM,
    TANWEEN_KASR: DiacriticType.TANWEEN_KASR,
    DAGGER_ALIF: DiacriticType.DAGGER_ALIF,
    HAMZA_ABOVE: DiacriticType.HAMZA_ABOVE,
    HAMZA_BELOW: DiacriticType.HAMZA_BELOW,
}


def classify_diacritic(char: str) -> Optional[DiacriticType]:
    """
    Classify a diacritic character.

    Args:
        char: Single character to classify

    Returns:
        DiacriticType if character is a known diacritic, None otherwise
    """
    return DIACRITIC_TYPE_MAP.get(char)


def is_vowel_diacritic(diacritic_type: DiacriticType) -> bool:
    """
    Check if diacritic type represents a vowel.

    Args:
        diacritic_type: Type to check

    Returns:
        True if vowel diacritic (fatha, damma, kasra, tanween)
    """
    return diacritic_type in {
        DiacriticType.FATHA,
        DiacriticType.DAMMA,
        DiacriticType.KASRA,
        DiacriticType.TANWEEN_FATH,
        DiacriticType.TANWEEN_DAMM,
        DiacriticType.TANWEEN_KASR,
    }


def is_tanween(diacritic_type: DiacriticType) -> bool:
    """Check if diacritic type is tanween."""
    return diacritic_type in {
        DiacriticType.TANWEEN_FATH,
        DiacriticType.TANWEEN_DAMM,
        DiacriticType.TANWEEN_KASR,
    }


def extract_diacritics(text: str) -> List[DiacriticInfo]:
    """
    Extract all diacritics from text with their positions.

    Args:
        text: Arabic text (should be NFD normalized)

    Returns:
        List of DiacriticInfo objects
    """
    text = normalize_unicode(text, 'NFD')
    diacritics = []
    current_base_char = ''
    base_char_index = -1

    for i, char in enumerate(text):
        if is_arabic_letter(char):
            current_base_char = char
            base_char_index = i
        elif is_arabic_diacritic(char):
            diacritic_type = classify_diacritic(char)
            if diacritic_type:
                info = DiacriticInfo(
                    position=len(diacritics),
                    character=char,
                    type=diacritic_type,
                    base_char=current_base_char,
                    text_index=i
                )
                diacritics.append(info)

    return diacritics


def get_diacritics_for_letter(
    text: str,
    letter_index: int
) -> List[DiacriticType]:
    """
    Get all diacritics for a specific letter.

    Args:
        text: Normalized Arabic text (should be NFC to preserve hamza characters)
        letter_index: Index of the letter

    Returns:
        List of diacritic types for that letter
    """
    # Note: text should already be normalized (NFC recommended to preserve combined hamza)
    # Do NOT convert to NFD here as it causes index mismatches
    if letter_index >= len(text):
        return []

    diacritics = []
    i = letter_index + 1

    while i < len(text) and is_arabic_diacritic(text[i]):
        diacritic_type = classify_diacritic(text[i])
        if diacritic_type:
            diacritics.append(diacritic_type)
        i += 1

    return diacritics


def has_sukoon(text: str, letter_index: int) -> bool:
    """
    Check if letter has sukoon.

    Args:
        text: Arabic text
        letter_index: Index of letter to check

    Returns:
        True if letter has sukoon
    """
    diacritics = get_diacritics_for_letter(text, letter_index)
    return DiacriticType.SUKOON in diacritics


def has_shaddah(text: str, letter_index: int) -> bool:
    """Check if letter has shaddah (gemination)."""
    diacritics = get_diacritics_for_letter(text, letter_index)
    return DiacriticType.SHADDAH in diacritics


def has_vowel(text: str, letter_index: int) -> bool:
    """Check if letter has a vowel diacritic."""
    diacritics = get_diacritics_for_letter(text, letter_index)
    return any(is_vowel_diacritic(d) for d in diacritics)


def get_vowel_type(text: str, letter_index: int) -> Optional[DiacriticType]:
    """
    Get the vowel diacritic type for a letter.

    Args:
        text: Arabic text
        letter_index: Index of letter

    Returns:
        DiacriticType of vowel if present, None otherwise
    """
    diacritics = get_diacritics_for_letter(text, letter_index)
    for d in diacritics:
        if is_vowel_diacritic(d):
            return d
    return None


def is_sakin(text: str, letter_index: int) -> bool:
    """
    Check if a letter is sākin (has sukoon or no vowel).

    Args:
        text: Arabic text
        letter_index: Index of letter

    Returns:
        True if letter is sākin
    """
    diacritics = get_diacritics_for_letter(text, letter_index)

    # Has explicit sukoon
    if DiacriticType.SUKOON in diacritics:
        return True

    # No vowel diacritic (implicitly sākin at end of word)
    has_any_vowel = any(is_vowel_diacritic(d) for d in diacritics)
    return not has_any_vowel


def get_shaddah_and_vowel(
    text: str,
    letter_index: int
) -> Tuple[bool, Optional[DiacriticType]]:
    """
    Get both shaddah status and vowel for a letter.

    Args:
        text: Arabic text
        letter_index: Index of letter

    Returns:
        Tuple of (has_shaddah, vowel_type)
    """
    diacritics = get_diacritics_for_letter(text, letter_index)

    has_shaddah_mark = DiacriticType.SHADDAH in diacritics
    vowel = None

    for d in diacritics:
        if is_vowel_diacritic(d):
            vowel = d
            break

    return (has_shaddah_mark, vowel)


def count_diacritics(text: str) -> Dict[DiacriticType, int]:
    """
    Count occurrences of each diacritic type.

    Args:
        text: Arabic text

    Returns:
        Dictionary mapping diacritic types to counts
    """
    diacritics = extract_diacritics(text)
    counts: Dict[DiacriticType, int] = {}

    for info in diacritics:
        counts[info.type] = counts.get(info.type, 0) + 1

    return counts


def validate_diacritics(text: str) -> Tuple[bool, str]:
    """
    Validate that text has proper diacritics for Qur'anic processing.

    Args:
        text: Arabic text to validate

    Returns:
        Tuple of (is_valid, message)
    """
    diacritics = extract_diacritics(text)

    if not diacritics:
        return (False, "No diacritics found in text")

    # Check for basic vowel marks
    counts = count_diacritics(text)
    has_vowels = any(
        counts.get(t, 0) > 0
        for t in [DiacriticType.FATHA, DiacriticType.DAMMA, DiacriticType.KASRA]
    )

    if not has_vowels:
        return (False, "No vowel diacritics (fatha, damma, kasra) found")

    return (True, "Text has valid diacritics")


def get_diacritic_sequence(text: str) -> str:
    """
    Get sequence of diacritics as a string.

    Args:
        text: Arabic text

    Returns:
        String representing diacritic sequence (e.g., "FaDuKa" for فَتُحَ)
    """
    diacritics = extract_diacritics(text)
    mapping = {
        DiacriticType.FATHA: 'a',
        DiacriticType.DAMMA: 'u',
        DiacriticType.KASRA: 'i',
        DiacriticType.SUKOON: '0',
        DiacriticType.SHADDAH: '~',
        DiacriticType.TANWEEN_FATH: 'an',
        DiacriticType.TANWEEN_DAMM: 'un',
        DiacriticType.TANWEEN_KASR: 'in',
    }

    return ''.join(mapping.get(d.type, '?') for d in diacritics)


def find_letters_with_diacritic(
    text: str,
    diacritic_type: DiacriticType
) -> List[int]:
    """
    Find all letter positions that have a specific diacritic.

    Args:
        text: Arabic text
        diacritic_type: Type of diacritic to find

    Returns:
        List of letter indices
    """
    text = normalize_unicode(text, 'NFD')
    positions = []
    letter_index = 0

    for i, char in enumerate(text):
        if is_arabic_letter(char):
            diacritics = get_diacritics_for_letter(text, i)
            if diacritic_type in diacritics:
                positions.append(letter_index)
            letter_index += 1

    return positions


def find_sukoon_letters(text: str) -> List[int]:
    """Find all letters with sukoon."""
    return find_letters_with_diacritic(text, DiacriticType.SUKOON)


def find_shaddah_letters(text: str) -> List[int]:
    """Find all letters with shaddah."""
    return find_letters_with_diacritic(text, DiacriticType.SHADDAH)


def get_diacritic_statistics(text: str) -> Dict[str, any]:
    """
    Get comprehensive statistics about diacritics in text.

    Args:
        text: Arabic text

    Returns:
        Dictionary with various statistics
    """
    diacritics = extract_diacritics(text)
    counts = count_diacritics(text)

    return {
        "total_diacritics": len(diacritics),
        "counts_by_type": {t.value: c for t, c in counts.items()},
        "has_vowels": any(
            counts.get(t, 0) > 0
            for t in [DiacriticType.FATHA, DiacriticType.DAMMA, DiacriticType.KASRA]
        ),
        "has_sukoon": counts.get(DiacriticType.SUKOON, 0) > 0,
        "has_shaddah": counts.get(DiacriticType.SHADDAH, 0) > 0,
        "has_tanween": any(counts.get(t, 0) > 0 for t in [
            DiacriticType.TANWEEN_FATH,
            DiacriticType.TANWEEN_DAMM,
            DiacriticType.TANWEEN_KASR
        ]),
        "sukoon_positions": find_sukoon_letters(text),
        "shaddah_positions": find_shaddah_letters(text),
    }
