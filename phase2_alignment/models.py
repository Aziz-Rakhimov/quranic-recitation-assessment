"""
Shared data classes for the word verification layer.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class WordError:
    error_type: str                  # "missing" | "wrong" | "added"
    expected_word: Optional[str]     # from quran_hafs.json — None if error_type is "added"
    detected_word: Optional[str]     # from Whisper — None if error_type is "missing"
    word_position: Optional[int]     # position in expected ayah word list — None if "added"
    ayah: int


@dataclass
class VerifiedAyah:
    surah: int
    ayah: int
    word_errors: List[WordError] = field(default_factory=list)
    verified_word_indices: Set[int] = field(default_factory=set)
    skipped_word_indices: Set[int] = field(default_factory=set)


@dataclass
class WordVerificationReport:
    surah: int
    start_ayah: int
    end_ayah: int
    ayahs: List[VerifiedAyah] = field(default_factory=list)
    total_word_errors: int = 0

    def get_skipped_indices_for_ayah(self, ayah: int) -> Set[int]:
        for verified in self.ayahs:
            if verified.ayah == ayah:
                return verified.skipped_word_indices
        return set()

    def get_word_errors_for_ayah(self, ayah: int) -> List[WordError]:
        for verified in self.ayahs:
            if verified.ayah == ayah:
                return verified.word_errors
        return []
