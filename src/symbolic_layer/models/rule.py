"""
Tajwīd rule data models using Pydantic.

This module defines data structures for representing Tajwīd rules, rule patterns,
actions, and rule applications.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from .enums import (
    RuleCategory,
    ActionType,
    ErrorSeverity,
    ErrorCategory,
    ComparisonType
)
from .phoneme import Phoneme


class RulePattern(BaseModel):
    """Pattern specification for matching Tajwīd rules."""

    target: str = Field(..., description="Target phoneme(s) or pattern")

    # Context patterns (regex-like)
    preceding_context: Optional[str] = Field(
        default=None,
        description="Pattern for preceding phonemes (lookbehind)"
    )
    following_context: Optional[str] = Field(
        default=None,
        description="Pattern for following phonemes (lookahead)"
    )

    # Conditions
    conditions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional conditions (e.g., has_sukoon, at_word_end)"
    )

    # Arabic context (for reference)
    following_arabic: Optional[List[str]] = None
    preceding_arabic: Optional[List[str]] = None

    def matches_target(self, phoneme_symbol: str) -> bool:
        """Check if a phoneme symbol matches the target pattern."""
        # Simple matching - can be extended with regex
        if '[' in self.target:
            # Pattern like "[q tˤ b dʒ d]" - match any of these
            phonemes = self.target.strip('[]').split()
            return phoneme_symbol in phonemes
        return self.target == phoneme_symbol


class FeatureModification(BaseModel):
    """Specification for modifying phoneme features."""

    feature_name: str
    new_value: Any
    operation: str = "set"  # set, add, multiply


class RuleAction(BaseModel):
    """Action to perform when a rule matches."""

    type: ActionType
    replacement: Optional[List[str]] = Field(
        default=None,
        description="Replacement phoneme symbols (for REPLACE action)"
    )
    feature_modifications: List[FeatureModification] = Field(
        default_factory=list,
        description="Modifications to phoneme features"
    )
    duration_multiplier: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Duration modification factor"
    )
    notes: Optional[str] = None


class AcousticEffect(BaseModel):
    """Expected acoustic effects of a Tajwīd rule."""

    # Duration
    duration_ms: Optional[float] = None
    duration_counts: Optional[float] = None  # For Tajwīd counts
    duration_tolerance: Optional[float] = None

    # Nasalization
    ghunnah_present: bool = False
    ghunnah_duration_counts: Optional[int] = None
    nasalization_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Emphasis
    emphatic: Optional[bool] = None
    f0_lowering_factor: Optional[float] = None
    f2_lowering_hz: Optional[float] = None

    # Qalqalah
    burst_present: bool = False
    burst_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    burst_duration_ms: Optional[float] = None
    echo_duration_ms: Optional[float] = None

    # Other
    spectral_features: Optional[Dict[str, Any]] = None


class VerificationCriterion(BaseModel):
    """Single verification criterion for acoustic verification."""

    feature: str = Field(..., description="Feature name to verify")
    comparison: ComparisonType = ComparisonType.THRESHOLD
    expected_value: Optional[float] = None
    threshold: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    tolerance: Optional[float] = None
    weight: float = Field(default=1.0, ge=0.0, description="Importance weight")
    description: Optional[str] = None


class ErrorDefinition(BaseModel):
    """Definition of a specific error type."""

    code: str = Field(..., description="Error code (e.g., E001, M101)")
    description: str
    severity: ErrorSeverity
    category: ErrorCategory


class TajweedRule(BaseModel):
    """Complete specification of a Tajwīd rule."""

    # Basic information
    name: str = Field(..., description="Unique rule name")
    category: RuleCategory
    priority: int = Field(..., description="Application priority (higher = earlier)")
    description: str
    arabic_name: Optional[str] = None

    # Pattern and action
    pattern: RulePattern
    action: RuleAction

    # Acoustic expectations
    acoustic_effect: Optional[AcousticEffect] = None
    verification_criteria: List[VerificationCriterion] = Field(default_factory=list)

    # Examples and errors
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    error_types: List[ErrorDefinition] = Field(default_factory=list)

    def matches(
        self,
        target_phoneme: str,
        preceding_phonemes: List[str],
        following_phonemes: List[str],
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if this rule matches the given context.

        Args:
            target_phoneme: The phoneme symbol to check
            preceding_phonemes: List of preceding phoneme symbols
            following_phonemes: List of following phoneme symbols
            context: Additional context information

        Returns:
            True if rule matches, False otherwise
        """
        # Check target
        if not self.pattern.matches_target(target_phoneme):
            return False

        # Check conditions
        for condition_key, condition_value in self.pattern.conditions.items():
            if condition_key not in context:
                return False
            if context[condition_key] != condition_value:
                return False

        # Check following context if specified
        if self.pattern.following_context and following_phonemes:
            next_phoneme = following_phonemes[0] if following_phonemes else None
            if not next_phoneme:
                return False

            # Simple pattern matching
            if '[' in self.pattern.following_context:
                valid_phonemes = self.pattern.following_context.strip('[]').split()
                if next_phoneme not in valid_phonemes:
                    return False
            elif self.pattern.following_context != next_phoneme:
                return False

        # Check preceding context if specified
        if self.pattern.preceding_context and preceding_phonemes:
            prev_phoneme = preceding_phonemes[-1] if preceding_phonemes else None
            if not prev_phoneme:
                return False

            if '[' in self.pattern.preceding_context:
                valid_phonemes = self.pattern.preceding_context.strip('[]').split()
                if prev_phoneme not in valid_phonemes:
                    return False
            elif self.pattern.preceding_context != prev_phoneme:
                return False

        return True

    class Config:
        frozen = False  # Allow modification for loading from YAML


class RuleApplication(BaseModel):
    """Record of a rule application to a phoneme sequence."""

    rule: TajweedRule
    start_index: int = Field(..., description="Start position in phoneme sequence")
    end_index: int = Field(..., description="End position in phoneme sequence")

    # Original and modified phonemes
    original_phonemes: List[Phoneme]
    modified_phonemes: List[Phoneme]

    # Confidence and metadata
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    applied_at: Optional[str] = None  # Timestamp
    context: Dict[str, Any] = Field(default_factory=dict)

    # Acoustic expectations for verification
    acoustic_expectations: Optional[AcousticEffect] = None

    def get_affected_range(self) -> range:
        """Get range of affected phoneme indices."""
        return range(self.start_index, self.end_index + 1)

    def get_rule_name(self) -> str:
        """Get the name of the applied rule."""
        return self.rule.name

    def get_category(self) -> RuleCategory:
        """Get the category of the applied rule."""
        return self.rule.category

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rule_name": self.rule.name,
            "rule_category": self.rule.category.value,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "original": [p.symbol for p in self.original_phonemes],
            "modified": [p.symbol for p in self.modified_phonemes],
            "confidence": self.confidence,
            "acoustic_expectations": self.acoustic_expectations.model_dump() if self.acoustic_expectations else None
        }


class AnnotatedPhonemeSequence(BaseModel):
    """Phoneme sequence with applied Tajwīd rules and annotations."""

    # Base sequence
    phonemes: List[Phoneme]
    word_boundaries: List[int] = Field(default_factory=list)
    verse_boundaries: List[int] = Field(default_factory=list)
    original_text: Optional[str] = None
    word_texts: List[str] = Field(default_factory=list)

    # Rule applications
    rule_applications: List[RuleApplication] = Field(default_factory=list)

    # Index to rules mapping (for quick lookup)
    _position_to_rules: Optional[Dict[int, List[RuleApplication]]] = None

    def model_post_init(self, __context: Any) -> None:
        """Build index after initialization."""
        self._build_position_index()

    def _build_position_index(self):
        """Build index of phoneme positions to rule applications."""
        self._position_to_rules = {}
        for rule_app in self.rule_applications:
            for pos in rule_app.get_affected_range():
                if pos not in self._position_to_rules:
                    self._position_to_rules[pos] = []
                self._position_to_rules[pos].append(rule_app)

    def get_rules_at_position(self, index: int) -> List[RuleApplication]:
        """Get all rules affecting a specific position."""
        if self._position_to_rules is None:
            self._build_position_index()
        return self._position_to_rules.get(index, [])

    def get_rules_by_category(self, category: RuleCategory) -> List[RuleApplication]:
        """Get all rule applications of a specific category."""
        return [r for r in self.rule_applications if r.get_category() == category]

    def to_ipa_string(self, separator: str = " ") -> str:
        """Convert to IPA string."""
        return separator.join(p.symbol for p in self.phonemes)

    def to_annotated_format(self) -> str:
        """
        Export with inline annotations.

        Format: phoneme[rule1,rule2] phoneme phoneme[rule3]
        """
        result = []
        for i, phoneme in enumerate(self.phonemes):
            rules = self.get_rules_at_position(i)
            if rules:
                rule_names = ','.join(r.get_rule_name() for r in rules)
                result.append(f"{phoneme.symbol}[{rule_names}]")
            else:
                result.append(phoneme.symbol)
        return " ".join(result)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about rule applications."""
        return {
            "total_phonemes": len(self.phonemes),
            "total_rules_applied": len(self.rule_applications),
            "rules_by_category": {
                cat.value: len(self.get_rules_by_category(cat))
                for cat in RuleCategory
            },
            "modified_phonemes": sum(
                len(r.get_affected_range())
                for r in self.rule_applications
            )
        }
