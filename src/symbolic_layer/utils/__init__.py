"""
Utility functions for the Symbolic Layer.

This package contains utility modules for:
- Unicode normalization and Arabic text handling
- Diacritic extraction and classification
- Format conversion (MFA, TextGrid, etc.)
"""

from .unicode_utils import (
    normalize_unicode,
    remove_diacritics,
    remove_tatweel,
    is_arabic_letter,
    is_arabic_diacritic,
    is_arabic_text,
    clean_arabic_text,
    validate_arabic_text,
    count_arabic_letters,
    extract_arabic_words,
    has_sukoon,
    has_shaddah,
    has_fatha,
    has_damma,
    has_kasra,
    get_vowel_diacritic,
    separate_letters_and_diacritics,
    FATHA,
    DAMMA,
    KASRA,
    SUKOON,
    SHADDAH,
    TANWEEN_FATH,
    TANWEEN_DAMM,
    TANWEEN_KASR,
    ARABIC_ALIF_WASLA,
    ARABIC_TEH_MARBUTA,
)

from .diacritic_utils import (
    DiacriticInfo,
    classify_diacritic,
    is_vowel_diacritic,
    is_tanween,
    extract_diacritics,
    get_diacritics_for_letter,
    get_vowel_type,
    is_sakin,
    get_shaddah_and_vowel,
    count_diacritics,
    validate_diacritics,
    get_diacritic_statistics,
    find_sukoon_letters,
    find_shaddah_letters,
)

__all__ = [
    # Unicode utilities
    "normalize_unicode",
    "remove_diacritics",
    "remove_tatweel",
    "is_arabic_letter",
    "is_arabic_diacritic",
    "is_arabic_text",
    "clean_arabic_text",
    "validate_arabic_text",
    "count_arabic_letters",
    "extract_arabic_words",
    "has_sukoon",
    "has_shaddah",
    "has_fatha",
    "has_damma",
    "has_kasra",
    "get_vowel_diacritic",
    "separate_letters_and_diacritics",
    # Constants
    "FATHA",
    "DAMMA",
    "KASRA",
    "SUKOON",
    "SHADDAH",
    "TANWEEN_FATH",
    "TANWEEN_DAMM",
    "TANWEEN_KASR",
    "ARABIC_ALIF_WASLA",
    "ARABIC_TEH_MARBUTA",
    # Diacritic utilities
    "DiacriticInfo",
    "classify_diacritic",
    "is_vowel_diacritic",
    "is_tanween",
    "extract_diacritics",
    "get_diacritics_for_letter",
    "get_vowel_type",
    "is_sakin",
    "get_shaddah_and_vowel",
    "count_diacritics",
    "validate_diacritics",
    "get_diacritic_statistics",
    "find_sukoon_letters",
    "find_shaddah_letters",
]
