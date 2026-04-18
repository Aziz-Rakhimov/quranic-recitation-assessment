"""
Data models for the Symbolic Layer.

This package contains all Pydantic models used throughout the symbolic layer:
- Enums: Type definitions and categories
- Phoneme: Phoneme representations and sequences
- Rule: Tajwīd rules and rule applications
- Features: Acoustic features and verification structures
"""

# Enums
from .enums import (
    PhonemeCategory,
    DiacriticType,
    RuleCategory,
    ActionType,
    PitchContour,
    ArticulationManner,
    ArticulationPlace,
    VowelHeight,
    VowelBackness,
    VowelLength,
    ComparisonType,
    ErrorSeverity,
    ErrorCategory,
    SegmentLevel,
    BoundaryType,
    OutputFormat,
    QalqalahStrength,
    MaddType,
    RaaQuality,
    NoonMeemRule
)

# Phoneme models
from .phoneme import (
    PhoneticFeatures,
    Phoneme,
    TextPosition,
    PhonemeSequence,
    AnnotatedPhoneme,
    PhonemeInventory
)

# Rule models
from .rule import (
    RulePattern,
    FeatureModification,
    RuleAction,
    AcousticEffect,
    VerificationCriterion,
    ErrorDefinition,
    TajweedRule,
    RuleApplication,
    AnnotatedPhonemeSequence
)

# Feature models
from .features import (
    Duration,
    Pitch,
    Formants,
    Intensity,
    Nasalization,
    SpectralFeatures,
    PhonemeAcousticFeatures,
    GlobalFeatures,
    AcousticFeatures,
    VerificationTarget as FeatureVerificationTarget,
    VerificationResult,
    SequenceVerificationResult
)

# Output models
from .output import (
    VerificationTarget,
    SymbolicOutput
)

__all__ = [
    # Enums
    "PhonemeCategory",
    "DiacriticType",
    "RuleCategory",
    "ActionType",
    "PitchContour",
    "ArticulationManner",
    "ArticulationPlace",
    "VowelHeight",
    "VowelBackness",
    "VowelLength",
    "ComparisonType",
    "ErrorSeverity",
    "ErrorCategory",
    "SegmentLevel",
    "BoundaryType",
    "OutputFormat",
    "QalqalahStrength",
    "MaddType",
    "RaaQuality",
    "NoonMeemRule",
    # Phoneme models
    "PhoneticFeatures",
    "Phoneme",
    "TextPosition",
    "PhonemeSequence",
    "AnnotatedPhoneme",
    "PhonemeInventory",
    # Rule models
    "RulePattern",
    "FeatureModification",
    "RuleAction",
    "AcousticEffect",
    "VerificationCriterion",
    "ErrorDefinition",
    "TajweedRule",
    "RuleApplication",
    "AnnotatedPhonemeSequence",
    # Feature models
    "Duration",
    "Pitch",
    "Formants",
    "Intensity",
    "Nasalization",
    "SpectralFeatures",
    "PhonemeAcousticFeatures",
    "GlobalFeatures",
    "AcousticFeatures",
    "FeatureVerificationTarget",
    "VerificationResult",
    "SequenceVerificationResult",
    # Output models
    "VerificationTarget",
    "SymbolicOutput",
]
