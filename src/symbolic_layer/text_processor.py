"""
Qur'anic text processor.

This module provides the main QuranTextProcessor class for normalizing,
validating, and segmenting Qur'anic Arabic text.
"""

from typing import List, Dict, Optional, Tuple
from .models.enums import DiacriticType, SegmentLevel
from .utils.unicode_utils import (
    normalize_unicode,
    clean_arabic_text,
    is_arabic_text,
    validate_arabic_text,
    count_arabic_letters,
    extract_arabic_words,
    ARABIC_ALIF_WASLA,
    ARABIC_TEH_MARBUTA
)
from .utils.diacritic_utils import (
    DiacriticInfo,
    extract_diacritics,
    validate_diacritics,
    get_diacritic_statistics,
    has_sukoon,
    has_shaddah,
    get_vowel_type
)


class TextSegment:
    """Represents a segment of text."""

    def __init__(
        self,
        text: str,
        start_pos: int,
        end_pos: int,
        segment_type: SegmentLevel,
        metadata: Optional[Dict] = None
    ):
        self.text = text
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.segment_type = segment_type
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"TextSegment('{self.text[:20]}...', {self.segment_type.value})"

    def __len__(self) -> int:
        return len(self.text)


class QuranTextProcessor:
    """
    Processor for Qur'anic Arabic text.

    Handles normalization, validation, diacritic extraction, and segmentation
    of Qur'anic text for phonemization.
    """

    def __init__(self, normalization_form: str = "NFD"):
        """
        Initialize the text processor.

        Args:
            normalization_form: Unicode normalization form (NFD or NFC)
                              NFD is preferred for Arabic diacritic processing
        """
        self.normalization_form = normalization_form

    def normalize(self, text: str, remove_tatweel: bool = True) -> str:
        """
        Normalize Qur'anic text.

        Args:
            text: Raw Arabic text
            remove_tatweel: Whether to remove tatweel (kashida) characters

        Returns:
            Normalized text
        """
        # Clean the text
        text = clean_arabic_text(text, remove_tatweel_chars=remove_tatweel)

        # Apply Unicode normalization
        text = normalize_unicode(text, self.normalization_form)

        return text

    def validate_text(self, text: str, require_diacritics: bool = True) -> Tuple[bool, str]:
        """
        Validate Qur'anic text for processing.

        Args:
            text: Text to validate
            require_diacritics: Whether diacritics are required

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check basic Arabic text validity
        is_valid, message = validate_arabic_text(text, require_diacritics=require_diacritics)
        if not is_valid:
            return (False, message)

        # Check diacritics if required
        if require_diacritics:
            is_valid, message = validate_diacritics(text)
            if not is_valid:
                return (False, message)

        return (True, "")

    def extract_diacritics(self, text: str) -> List[DiacriticInfo]:
        """
        Extract all diacritics from text.

        Args:
            text: Normalized Arabic text

        Returns:
            List of diacritic information
        """
        text = self.normalize(text)
        return extract_diacritics(text)

    def segment_by_word(self, text: str) -> List[str]:
        """
        Segment text into words.

        Args:
            text: Arabic text

        Returns:
            List of words
        """
        text = self.normalize(text)

        # Split on whitespace
        words = text.split()

        # Filter out empty strings
        words = [w for w in words if w.strip()]

        return words

    def segment_by_verse(self, text: str, verse_separator: str = '\n') -> List[str]:
        """
        Segment text into verses.

        Args:
            text: Arabic text with verses
            verse_separator: Character(s) separating verses

        Returns:
            List of verses
        """
        text = self.normalize(text)

        # Split on verse separator
        verses = text.split(verse_separator)

        # Filter and clean
        verses = [v.strip() for v in verses if v.strip()]

        return verses

    def segment(
        self,
        text: str,
        level: SegmentLevel = SegmentLevel.WORD
    ) -> List[TextSegment]:
        """
        Segment text at specified level.

        Args:
            text: Arabic text
            level: Segmentation level

        Returns:
            List of TextSegment objects
        """
        text = self.normalize(text)
        segments = []

        if level == SegmentLevel.WORD:
            words = self.segment_by_word(text)
            pos = 0
            for word in words:
                # Find word position in original text
                start = text.find(word, pos)
                if start == -1:
                    continue
                end = start + len(word)

                segment = TextSegment(
                    text=word,
                    start_pos=start,
                    end_pos=end,
                    segment_type=SegmentLevel.WORD
                )
                segments.append(segment)
                pos = end

        elif level == SegmentLevel.VERSE:
            verses = self.segment_by_verse(text)
            pos = 0
            for i, verse in enumerate(verses):
                segment = TextSegment(
                    text=verse,
                    start_pos=pos,
                    end_pos=pos + len(verse),
                    segment_type=SegmentLevel.VERSE,
                    metadata={"verse_number": i + 1}
                )
                segments.append(segment)
                pos += len(verse) + 1  # +1 for separator

        return segments

    def get_letter_with_context(
        self,
        text: str,
        position: int,
        context_size: int = 2
    ) -> Tuple[str, str, str]:
        """
        Get a letter with its surrounding context.

        Args:
            text: Normalized text
            position: Letter position
            context_size: Number of letters before/after

        Returns:
            Tuple of (left_context, letter, right_context)
        """
        text = self.normalize(text)

        # Get only Arabic letters (skip diacritics for context)
        from .utils.unicode_utils import is_arabic_letter
        letters = [c for c in text if is_arabic_letter(c)]

        if position < 0 or position >= len(letters):
            return ('', '', '')

        left_start = max(0, position - context_size)
        left = ''.join(letters[left_start:position])

        letter = letters[position]

        right_end = min(len(letters), position + context_size + 1)
        right = ''.join(letters[position + 1:right_end])

        return (left, letter, right)

    def analyze_word(self, word: str) -> Dict:
        """
        Analyze a single word for phonemization.

        Args:
            word: Single Arabic word

        Returns:
            Dictionary with analysis information
        """
        word = self.normalize(word)

        # Extract letters (without diacritics for counting)
        from .utils.unicode_utils import remove_diacritics, is_arabic_letter
        letters_only = remove_diacritics(word)
        letters = [c for c in letters_only if is_arabic_letter(c)]

        # Extract diacritics
        diacritics = self.extract_diacritics(word)

        # Find special features
        sukoon_positions = []
        shaddah_positions = []
        vowel_pattern = []

        for i, letter in enumerate(letters):
            # Find letter position in original word
            # (This is simplified - real implementation needs better mapping)
            if has_sukoon(word, i):
                sukoon_positions.append(i)
            if has_shaddah(word, i):
                shaddah_positions.append(i)

            vowel = get_vowel_type(word, i)
            vowel_pattern.append(vowel.value if vowel else 'none')

        return {
            "word": word,
            "letters": letters,
            "letter_count": len(letters),
            "diacritics": diacritics,
            "diacritic_count": len(diacritics),
            "sukoon_positions": sukoon_positions,
            "shaddah_positions": shaddah_positions,
            "vowel_pattern": vowel_pattern,
            "has_alif_wasla": ARABIC_ALIF_WASLA in word,
            "has_teh_marbuta": ARABIC_TEH_MARBUTA in word,
        }

    def get_statistics(self, text: str) -> Dict:
        """
        Get comprehensive statistics about the text.

        Args:
            text: Arabic text

        Returns:
            Dictionary with statistics
        """
        text = self.normalize(text)

        # Basic counts
        letter_count = count_arabic_letters(text)
        words = self.segment_by_word(text)
        word_count = len(words)

        # Diacritic statistics
        diacritic_stats = get_diacritic_statistics(text)

        return {
            "character_count": len(text),
            "letter_count": letter_count,
            "word_count": word_count,
            "average_word_length": letter_count / word_count if word_count > 0 else 0,
            "diacritic_statistics": diacritic_stats,
            "is_valid": self.validate_text(text)[0]
        }

    def prepare_for_phonemization(self, text: str) -> str:
        """
        Prepare text for phonemization by normalizing and validating.

        Args:
            text: Raw Qur'anic text

        Returns:
            Normalized and validated text ready for phonemization

        Raises:
            ValueError: If text is invalid for phonemization
        """
        # Normalize
        text = self.normalize(text)

        # Validate
        is_valid, message = self.validate_text(text, require_diacritics=True)
        if not is_valid:
            raise ValueError(f"Invalid text for phonemization: {message}")

        return text

    def split_into_phoneme_units(self, text: str) -> List[Tuple[str, List[str]]]:
        """
        Split text into phoneme units (base letters with their diacritics).

        Args:
            text: Normalized Arabic text

        Returns:
            List of (base_letter, diacritics) tuples
        """
        from .utils.unicode_utils import separate_letters_and_diacritics

        text = self.normalize(text)
        return separate_letters_and_diacritics(text)

    def __repr__(self) -> str:
        return f"QuranTextProcessor(normalization={self.normalization_form})"
