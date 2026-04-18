"""
Base rule class for Tajwīd rules.

All specific Tajwīd rule implementations inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..models.phoneme import Phoneme, PhonemeSequence
from ..models.rule import TajweedRule, RuleApplication


class BaseRule(ABC):
    """
    Abstract base class for Tajwīd rules.

    All specific rule implementations (Iẓhār, Idghām, Madd, etc.) must
    inherit from this class and implement the abstract methods.
    """

    def __init__(self, rule_definition: TajweedRule):
        """
        Initialize the rule with its definition.

        Args:
            rule_definition: TajweedRule object loaded from YAML
        """
        self.rule = rule_definition

    @abstractmethod
    def matches(
        self,
        sequence: PhonemeSequence,
        index: int,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if the rule matches at the given position.

        Args:
            sequence: The phoneme sequence
            index: Position to check
            context: Additional context information

        Returns:
            True if rule matches, False otherwise
        """
        pass

    @abstractmethod
    def apply(
        self,
        sequence: PhonemeSequence,
        index: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[RuleApplication]:
        """
        Apply the rule at the given position.

        Args:
            sequence: The phoneme sequence
            index: Position to apply rule
            context: Additional context information

        Returns:
            RuleApplication object if rule was applied, None otherwise
        """
        pass

    def _check_context(
        self,
        sequence: PhonemeSequence,
        index: int,
        context_pattern: str,
        direction: str = "following"
    ) -> bool:
        """
        Check if context pattern matches.

        Args:
            sequence: Phoneme sequence
            index: Current position
            context_pattern: Pattern to match (e.g., "[q tˤ b]")
            direction: "following" or "preceding"

        Returns:
            True if pattern matches
        """
        if not context_pattern:
            return True

        # Get the phoneme to check
        if direction == "following":
            if index + 1 >= len(sequence):
                return False
            check_index = index + 1
        elif direction == "preceding":
            if index <= 0:
                return False
            check_index = index - 1
        else:
            return False

        target_phoneme = sequence[check_index]

        # Parse pattern
        if context_pattern.startswith('[') and context_pattern.endswith(']'):
            # Pattern like "[q tˤ b dʒ d]" - match any of these
            valid_symbols = context_pattern.strip('[]').split()
            return target_phoneme.symbol in valid_symbols
        else:
            # Exact match
            return target_phoneme.symbol == context_pattern

    def _get_preceding_phonemes(
        self,
        sequence: PhonemeSequence,
        index: int,
        count: int = 1
    ) -> List[Phoneme]:
        """Get preceding phonemes."""
        start = max(0, index - count)
        return list(sequence.phonemes[start:index])

    def _get_following_phonemes(
        self,
        sequence: PhonemeSequence,
        index: int,
        count: int = 1
    ) -> List[Phoneme]:
        """Get following phonemes."""
        end = min(len(sequence), index + count + 1)
        return list(sequence.phonemes[index + 1:end])

    def _has_sukoon(
        self,
        sequence: PhonemeSequence,
        index: int
    ) -> bool:
        """
        Check if phoneme at index has sukoon (no vowel following).

        This is a simplified check - looks for absence of vowel phoneme
        immediately following the consonant.
        """
        if index + 1 >= len(sequence):
            return True  # End of sequence = implicit sukoon

        next_phoneme = sequence[index + 1]
        return not next_phoneme.is_vowel()

    def _is_word_boundary(
        self,
        sequence: PhonemeSequence,
        index: int
    ) -> bool:
        """Check if position is at a word boundary."""
        return sequence.is_word_boundary(index)

    def _is_verse_boundary(
        self,
        sequence: PhonemeSequence,
        index: int
    ) -> bool:
        """Check if position is at a verse boundary."""
        return sequence.is_verse_boundary(index)

    def _is_word_end(
        self,
        sequence: PhonemeSequence,
        index: int
    ) -> bool:
        """Check if position is at end of word."""
        # Next position is word boundary or end of sequence
        return (
            index + 1 >= len(sequence) or
            self._is_word_boundary(sequence, index + 1)
        )

    def _is_emphatic_consonant(self, phoneme: Phoneme) -> bool:
        """Check if phoneme is an emphatic consonant."""
        emphatic_symbols = ['sˤ', 'dˤ', 'tˤ', 'ðˤ', 'q', 'rˤ', 'lˤ']
        return phoneme.symbol in emphatic_symbols

    def _create_rule_application(
        self,
        sequence: PhonemeSequence,
        start_index: int,
        end_index: int,
        original_phonemes: List[Phoneme],
        modified_phonemes: List[Phoneme],
        confidence: float = 1.0
    ) -> RuleApplication:
        """
        Create a RuleApplication object.

        Args:
            sequence: The phoneme sequence
            start_index: Start position of rule application
            end_index: End position of rule application
            original_phonemes: Original phonemes before rule
            modified_phonemes: Phonemes after rule application
            confidence: Confidence score (0-1)

        Returns:
            RuleApplication object
        """
        return RuleApplication(
            rule=self.rule,
            start_index=start_index,
            end_index=end_index,
            original_phonemes=original_phonemes,
            modified_phonemes=modified_phonemes,
            confidence=confidence,
            acoustic_expectations=self.rule.acoustic_effect
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.rule.name})"
