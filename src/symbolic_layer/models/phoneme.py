"""
Phoneme data models using Pydantic.

This module defines data structures for representing phonemes, phonetic features,
and phoneme sequences with positional information.
"""

from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, field_validator
from .enums import (
    PhonemeCategory,
    ArticulationManner,
    ArticulationPlace,
    VowelHeight,
    VowelBackness,
    VowelLength,
    BoundaryType
)


class PhoneticFeatures(BaseModel):
    """Phonetic features of a phoneme."""

    # Consonant features
    manner: Optional[ArticulationManner] = None
    place: Optional[ArticulationPlace] = None
    voicing: Optional[bool] = None
    emphatic: bool = False  # Pharyngealized/velarized

    # Vowel features
    height: Optional[VowelHeight] = None
    backness: Optional[VowelBackness] = None
    rounding: Optional[bool] = None
    length: Optional[VowelLength] = None

    # Special features
    nasalized: bool = False
    geminated: bool = False
    syllabic: bool = False

    class Config:
        frozen = True  # Make immutable


class Phoneme(BaseModel):
    """Individual phoneme with metadata."""

    symbol: str = Field(..., description="IPA symbol for the phoneme")
    category: PhonemeCategory
    features: PhoneticFeatures
    duration_factor: float = Field(default=1.0, ge=0.1, le=10.0)

    # Optional metadata
    arabic_letter: Optional[str] = None
    description: Optional[str] = None

    # Acoustic parameters (base values)
    base_duration_ms: Optional[float] = Field(default=None, ge=0)
    formants: Optional[Dict[str, float]] = None  # F1, F2, F3

    def __str__(self) -> str:
        return self.symbol

    def __repr__(self) -> str:
        return f"Phoneme('{self.symbol}', {self.category.value})"

    def is_vowel(self) -> bool:
        """Check if phoneme is a vowel."""
        return self.category in [PhonemeCategory.VOWEL, PhonemeCategory.DIPHTHONG]

    def is_consonant(self) -> bool:
        """Check if phoneme is a consonant."""
        return self.category in [PhonemeCategory.CONSONANT, PhonemeCategory.GEMINATE]

    def is_nasal(self) -> bool:
        """Check if phoneme is a nasal consonant."""
        return (
            self.features.manner == ArticulationManner.NASAL or
            self.features.nasalized
        )

    def is_emphatic(self) -> bool:
        """Check if phoneme is emphatic (pharyngealized)."""
        return self.features.emphatic

    def is_geminate(self) -> bool:
        """Check if phoneme is geminated (doubled)."""
        return self.category == PhonemeCategory.GEMINATE or self.features.geminated

    def is_long(self) -> bool:
        """Check if phoneme is a long vowel."""
        if not self.is_vowel():
            return False
        # Long vowels typically have 'ː' in their symbol
        return 'ː' in self.symbol or self.duration_factor > 1.5

    class Config:
        frozen = True  # Make immutable


class TextPosition(BaseModel):
    """Maps a phoneme back to its position in original text."""

    text_index: int = Field(..., description="Character index in original text")
    grapheme: str = Field(..., description="Original grapheme(s)")
    word_index: Optional[int] = None
    verse_index: Optional[int] = None

    class Config:
        frozen = True


class PhonemeSequence(BaseModel):
    """Sequence of phonemes with alignment information."""

    phonemes: List[Phoneme]
    positions: Optional[List[TextPosition]] = None

    # Boundary markers
    word_boundaries: List[int] = Field(default_factory=list, description="Indices where words begin")
    verse_boundaries: List[int] = Field(default_factory=list, description="Indices where verses begin")
    syllable_boundaries: Optional[List[int]] = None

    # Original text reference
    original_text: Optional[str] = None
    word_texts: List[str] = Field(default_factory=list, description="Original Arabic text for each word")

    # Muqatta'at (disjoined letter) rule specs.
    # Each entry: {'phoneme_index': int, 'rule_name': str}.
    # Populated by the phonemizer when it detects Muqatta'at letter-names; the
    # Tajwīd engine consumes these in apply_rules() to inject RuleApplications
    # for rules whose triggers are letter-name level (not detectable from the
    # phoneme stream alone — e.g. madd lāzim ḥarfī, qalqalah on Muqatta'at qāf).
    muqattaat_rule_specs: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator('phonemes')
    @classmethod
    def phonemes_not_empty(cls, v):
        """Ensure phoneme list is not empty."""
        if not v:
            raise ValueError("Phoneme sequence cannot be empty")
        return v

    @field_validator('word_boundaries', 'verse_boundaries')
    @classmethod
    def boundaries_valid(cls, v, info):
        """Ensure boundary indices are sorted and valid."""
        if v and v != sorted(v):
            raise ValueError(f"{info.field_name} must be sorted")
        return v

    def __len__(self) -> int:
        """Return number of phonemes."""
        return len(self.phonemes)

    def __getitem__(self, index: int) -> Phoneme:
        """Get phoneme at index."""
        return self.phonemes[index]

    def __iter__(self):
        """Iterate over phonemes."""
        return iter(self.phonemes)

    def to_ipa_string(self, separator: str = " ") -> str:
        """Convert phoneme sequence to IPA string."""
        return separator.join(p.symbol for p in self.phonemes)

    def to_symbols_list(self) -> List[str]:
        """Get list of phoneme symbols."""
        return [p.symbol for p in self.phonemes]

    def get_phoneme_at_position(self, index: int) -> Phoneme:
        """Get phoneme at specific position with bounds checking."""
        if not 0 <= index < len(self.phonemes):
            raise IndexError(f"Phoneme index {index} out of range")
        return self.phonemes[index]

    def get_context(
        self,
        index: int,
        left_context: int = 1,
        right_context: int = 1
    ) -> Tuple[List[Phoneme], Phoneme, List[Phoneme]]:
        """
        Get phoneme with surrounding context.

        Returns:
            Tuple of (left_phonemes, target_phoneme, right_phonemes)
        """
        target = self.phonemes[index]

        left_start = max(0, index - left_context)
        left = self.phonemes[left_start:index]

        right_end = min(len(self.phonemes), index + right_context + 1)
        right = self.phonemes[index + 1:right_end]

        return (left, target, right)

    def get_words(self) -> List['PhonemeSequence']:
        """Split sequence into word-level subsequences."""
        if not self.word_boundaries:
            return [self]

        words = []
        boundaries = [0] + self.word_boundaries + [len(self.phonemes)]

        for i in range(len(boundaries) - 1):
            start, end = boundaries[i], boundaries[i + 1]
            word_phonemes = self.phonemes[start:end]
            word_text = self.word_texts[i] if i < len(self.word_texts) else None

            word_seq = PhonemeSequence(
                phonemes=word_phonemes,
                positions=self.positions[start:end] if self.positions else None,
                word_boundaries=[],
                verse_boundaries=[],
                original_text=word_text
            )
            words.append(word_seq)

        return words

    def is_word_boundary(self, index: int) -> bool:
        """Check if position is at a word boundary."""
        return index in self.word_boundaries

    def is_verse_boundary(self, index: int) -> bool:
        """Check if position is at a verse boundary."""
        return index in self.verse_boundaries

    def get_phonemes_in_range(self, start: int, end: int) -> List[Phoneme]:
        """Get phonemes in a specific range."""
        return self.phonemes[start:end]

    def to_mfa_format(self) -> str:
        """
        Export in Montreal Forced Aligner dictionary format.

        Format: word TAB phoneme1 phoneme2 phoneme3
        """
        # For MFA, we need word-level representations
        words = self.get_words()
        lines = []

        for word_seq in words:
            if word_seq.original_text:
                word_text = word_seq.original_text.strip()
                phonemes_str = " ".join(p.symbol for p in word_seq.phonemes)
                lines.append(f"{word_text}\t{phonemes_str}")

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the phoneme sequence."""
        return {
            "total_phonemes": len(self.phonemes),
            "num_words": len(self.word_boundaries) + 1 if self.word_boundaries else 1,
            "num_verses": len(self.verse_boundaries) + 1 if self.verse_boundaries else 1,
            "num_vowels": sum(1 for p in self.phonemes if p.is_vowel()),
            "num_consonants": sum(1 for p in self.phonemes if p.is_consonant()),
            "num_nasals": sum(1 for p in self.phonemes if p.is_nasal()),
            "num_emphatics": sum(1 for p in self.phonemes if p.is_emphatic()),
            "ipa_string": self.to_ipa_string()
        }


class AnnotatedPhoneme(BaseModel):
    """Phoneme with additional annotations from Tajwīd rules."""

    phoneme: Phoneme
    index: int  # Position in sequence

    # Tajwīd annotations
    tajweed_rules: List[str] = Field(default_factory=list, description="Names of applied Tajwīd rules")
    modified: bool = False  # Whether phoneme was modified by rules
    original_phoneme: Optional[Phoneme] = None  # If modified, store original

    # Acoustic modifications
    duration_multiplier: float = 1.0
    pitch_modifier: Optional[float] = None
    emphasis_factor: Optional[float] = None

    # Context information
    in_word_boundary: bool = False
    in_verse_boundary: bool = False

    class Config:
        frozen = True


class PhonemeInventory(BaseModel):
    """
    Complete inventory of phonemes for the system.

    Loaded from base_phonemes.yaml and tajweed_phonemes.yaml.
    """

    consonants: List[Phoneme] = Field(default_factory=list)
    vowels: List[Phoneme] = Field(default_factory=list)
    tajweed_phonemes: List[Phoneme] = Field(default_factory=list)

    # Lookup dictionaries
    _symbol_to_phoneme: Optional[Dict[str, Phoneme]] = None
    _arabic_to_phoneme: Optional[Dict[str, List[Phoneme]]] = None

    def model_post_init(self, __context: Any) -> None:
        """Build lookup dictionaries after initialization."""
        self._build_lookup_tables()

    def _build_lookup_tables(self):
        """Build lookup dictionaries for fast access."""
        self._symbol_to_phoneme = {}
        self._arabic_to_phoneme = {}

        all_phonemes = self.consonants + self.vowels + self.tajweed_phonemes

        for phoneme in all_phonemes:
            # Symbol lookup
            self._symbol_to_phoneme[phoneme.symbol] = phoneme

            # Arabic letter lookup
            if phoneme.arabic_letter:
                if phoneme.arabic_letter not in self._arabic_to_phoneme:
                    self._arabic_to_phoneme[phoneme.arabic_letter] = []
                self._arabic_to_phoneme[phoneme.arabic_letter].append(phoneme)

    def get_by_symbol(self, symbol: str) -> Optional[Phoneme]:
        """Get phoneme by IPA symbol."""
        if self._symbol_to_phoneme is None:
            self._build_lookup_tables()
        return self._symbol_to_phoneme.get(symbol)

    def get_by_arabic_letter(self, letter: str) -> List[Phoneme]:
        """Get possible phonemes for an Arabic letter."""
        if self._arabic_to_phoneme is None:
            self._build_lookup_tables()
        return self._arabic_to_phoneme.get(letter, [])

    def get_all_phonemes(self) -> List[Phoneme]:
        """Get all phonemes in inventory."""
        return self.consonants + self.vowels + self.tajweed_phonemes

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about the phoneme inventory."""
        return {
            "num_consonants": len(self.consonants),
            "num_vowels": len(self.vowels),
            "num_tajweed_phonemes": len(self.tajweed_phonemes),
            "total_phonemes": len(self.get_all_phonemes())
        }

    def get_consonants(self) -> List[Phoneme]:
        """Get all consonants."""
        return self.consonants

    def get_vowels(self) -> List[Phoneme]:
        """Get all vowels."""
        return self.vowels

    def get_tajweed_phonemes(self) -> List[Phoneme]:
        """Get all Tajweed-specific phonemes."""
        return self.tajweed_phonemes

    @property
    def phonemes(self) -> List[Phoneme]:
        """Get all phonemes as a list."""
        return self.get_all_phonemes()

    @classmethod
    def from_yaml_files(
        cls,
        base_phonemes_path: str,
        tajweed_phonemes_path: str
    ) -> "PhonemeInventory":
        """
        Load phoneme inventory from YAML files.

        Args:
            base_phonemes_path: Path to base_phonemes.yaml
            tajweed_phonemes_path: Path to tajweed_phonemes.yaml

        Returns:
            PhonemeInventory with loaded phonemes
        """
        import yaml
        from pathlib import Path

        # Load base phonemes
        with open(Path(base_phonemes_path), 'r', encoding='utf-8') as f:
            base_data = yaml.safe_load(f)

        # Load tajweed phonemes
        with open(Path(tajweed_phonemes_path), 'r', encoding='utf-8') as f:
            tajweed_data = yaml.safe_load(f)

        consonants = []
        vowels = []
        tajweed_phonemes = []

        # Parse base phonemes
        if 'consonants' in base_data:
            for c_data in base_data['consonants']:
                consonants.append(cls._parse_phoneme_from_yaml(c_data))

        if 'vowels' in base_data:
            for v_data in base_data['vowels']:
                vowels.append(cls._parse_phoneme_from_yaml(v_data))

        # Parse tajweed phonemes
        if 'phonemes' in tajweed_data:
            for t_data in tajweed_data['phonemes']:
                tajweed_phonemes.append(cls._parse_phoneme_from_yaml(t_data))

        return cls(
            consonants=consonants,
            vowels=vowels,
            tajweed_phonemes=tajweed_phonemes
        )

    @staticmethod
    def _parse_phoneme_from_yaml(data: Dict[str, Any]) -> Phoneme:
        """Parse a phoneme from YAML data."""
        from .enums import PhonemeCategory

        # Parse phonetic features
        features_data = data.get('features', {})
        features = PhoneticFeatures(
            manner=features_data.get('manner'),
            place=features_data.get('place'),
            voicing=features_data.get('voicing'),
            emphatic=features_data.get('emphatic', False),
            nasalized=features_data.get('nasalized', False),
            aspirated=features_data.get('aspirated', False),
            geminated=features_data.get('geminated', False),
            additional_features=features_data.get('additional_features', {})
        )

        # Determine category
        category_str = data.get('category', 'consonant')
        if category_str == 'vowel':
            category = PhonemeCategory.VOWEL
        elif category_str == 'geminate':
            category = PhonemeCategory.GEMINATE
        elif category_str == 'tajweed':
            category = PhonemeCategory.TAJWEED
        else:
            category = PhonemeCategory.CONSONANT

        return Phoneme(
            symbol=data['symbol'],
            category=category,
            features=features,
            duration_factor=data.get('duration_factor', 1.0),
            ipa_symbol=data.get('ipa_symbol', data['symbol']),
            description=data.get('description', ''),
            arabic_letter=data.get('arabic_letter'),
            example_arabic=data.get('example_arabic'),
            example_transliteration=data.get('example_transliteration')
        )
