"""
Acoustic feature data models using Pydantic.

This module defines data structures for representing expected acoustic features
that will be used for verification in the acoustic layer.
"""

from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from .enums import PitchContour, ErrorSeverity, ErrorCategory, ComparisonType


class Duration(BaseModel):
    """Duration expectations for a phoneme."""

    expected_ms: float = Field(..., ge=0, description="Expected duration in milliseconds")
    min_acceptable_ms: Optional[float] = Field(default=None, ge=0)
    max_acceptable_ms: Optional[float] = Field(default=None, ge=0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_rule: Optional[str] = Field(
        default=None,
        description="Tajwīd rule that determined this duration"
    )

    # For Tajwīd counts (1 count ≈ 100ms)
    duration_counts: Optional[float] = None

    def is_acceptable(self, actual_ms: float) -> bool:
        """Check if actual duration is acceptable."""
        if self.min_acceptable_ms and actual_ms < self.min_acceptable_ms:
            return False
        if self.max_acceptable_ms and actual_ms > self.max_acceptable_ms:
            return False
        return True

    def get_deviation(self, actual_ms: float) -> float:
        """Get deviation from expected duration (positive = too long)."""
        return actual_ms - self.expected_ms

    def get_relative_deviation(self, actual_ms: float) -> float:
        """Get relative deviation (as percentage)."""
        if self.expected_ms == 0:
            return 0.0
        return (actual_ms - self.expected_ms) / self.expected_ms * 100


class Pitch(BaseModel):
    """Pitch/F0 expectations for a phoneme."""

    contour_type: PitchContour = PitchContour.LEVEL
    expected_f0_hz: float = Field(..., gt=0, description="Expected fundamental frequency")
    acceptable_range_hz: Tuple[float, float] = Field(
        ...,
        description="Min and max acceptable F0"
    )

    # For emphatic consonants
    emphasis_factor: Optional[float] = Field(
        default=None,
        description="F0 lowering factor for emphatic consonants"
    )

    # Contour parameters
    start_f0: Optional[float] = None
    end_f0: Optional[float] = None
    peak_f0: Optional[float] = None

    def is_acceptable(self, actual_f0: float) -> bool:
        """Check if actual F0 is acceptable."""
        min_f0, max_f0 = self.acceptable_range_hz
        return min_f0 <= actual_f0 <= max_f0

    def get_expected_range(self) -> Tuple[float, float]:
        """Get expected F0 range."""
        return self.acceptable_range_hz


class Formants(BaseModel):
    """Formant frequency expectations for vowels."""

    f1_hz: float = Field(..., gt=0, description="First formant frequency")
    f2_hz: float = Field(..., gt=0, description="Second formant frequency")
    f3_hz: Optional[float] = Field(default=None, gt=0, description="Third formant frequency")

    # Bandwidths
    bandwidth_f1: Optional[float] = None
    bandwidth_f2: Optional[float] = None

    # Acceptable ranges
    acceptable_ranges: Dict[str, Tuple[float, float]] = Field(
        default_factory=dict,
        description="Acceptable ranges for each formant"
    )

    # Emphatic effects
    emphatic_f1_shift: Optional[float] = None  # Hz shift for emphatic context
    emphatic_f2_shift: Optional[float] = None

    def is_acceptable(self, actual_formants: Dict[str, float]) -> bool:
        """Check if actual formants are acceptable."""
        for formant_name, actual_value in actual_formants.items():
            if formant_name in self.acceptable_ranges:
                min_f, max_f = self.acceptable_ranges[formant_name]
                if not (min_f <= actual_value <= max_f):
                    return False
        return True

    def get_formant_vector(self) -> List[float]:
        """Get formant values as a vector."""
        return [self.f1_hz, self.f2_hz, self.f3_hz] if self.f3_hz else [self.f1_hz, self.f2_hz]


class Intensity(BaseModel):
    """Intensity expectations for a phoneme."""

    expected_db: float = Field(..., description="Expected intensity in dB")
    min_db: Optional[float] = None
    max_db: Optional[float] = None

    # Relative to surrounding phonemes
    relative_intensity: Optional[float] = None  # Factor relative to average


class Nasalization(BaseModel):
    """Nasalization expectations (for ghunnah and nasal consonants)."""

    is_nasalized: bool = Field(..., description="Whether nasalization is expected")
    ghunnah_duration_counts: Optional[int] = Field(
        default=None,
        description="Duration of ghunnah in counts (usually 2)"
    )
    nasal_intensity: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Strength of nasal quality"
    )

    # Acoustic parameters
    f1_reduction_factor: float = Field(
        default=1.0,
        description="F1 intensity reduction due to nasalization"
    )
    nasal_formant_hz: Optional[float] = Field(
        default=None,
        description="Expected nasal formant frequency (~300 Hz)"
    )
    nasal_formant_range: Optional[Tuple[float, float]] = None

    # Bandwidth changes
    bandwidth_increase_factor: Optional[float] = None

    def has_ghunnah(self) -> bool:
        """Check if ghunnah is expected."""
        return self.ghunnah_duration_counts is not None and self.ghunnah_duration_counts > 0


class SpectralFeatures(BaseModel):
    """Spectral characteristics beyond formants."""

    # Spectral tilt (for emphatic vs non-emphatic)
    spectral_tilt: Optional[float] = Field(
        default=None,
        description="Spectral slope (negative for darker sounds)"
    )

    # Antiformants (for nasals)
    zero_frequencies: List[float] = Field(
        default_factory=list,
        description="Antiformant frequencies"
    )

    # Formant peaks
    pole_frequencies: List[float] = Field(
        default_factory=list,
        description="Formant peak frequencies"
    )

    # Burst characteristics (for qalqalah)
    burst_frequency_center: Optional[float] = None
    burst_frequency_range: Optional[Tuple[float, float]] = None
    burst_duration_ms: Optional[float] = None
    burst_amplitude: Optional[float] = None

    # Spectral moments
    spectral_centroid: Optional[float] = None
    spectral_spread: Optional[float] = None


class PhonemeAcousticFeatures(BaseModel):
    """Complete set of acoustic features for a single phoneme."""

    phoneme_index: int = Field(..., description="Index in phoneme sequence")
    phoneme_symbol: str

    # Core acoustic features
    duration: Duration
    pitch: Optional[Pitch] = None  # Not applicable for all phonemes
    formants: Optional[Formants] = None  # Mainly for vowels
    intensity: Optional[Intensity] = None
    nasalization: Optional[Nasalization] = None
    spectral_features: Optional[SpectralFeatures] = None

    # Context
    in_emphatic_context: bool = False
    in_word_boundary: bool = False
    in_verse_boundary: bool = False

    # Verification metadata
    verification_priority: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: Optional[str] = None


class GlobalFeatures(BaseModel):
    """Global features for the entire sequence."""

    # Speech rate
    average_phoneme_duration_ms: float
    speech_rate_phonemes_per_second: float

    # Pitch statistics
    mean_f0_hz: float
    f0_range_hz: Tuple[float, float]
    f0_std_dev: float

    # Intensity statistics
    mean_intensity_db: float
    intensity_range_db: Tuple[float, float]


class AcousticFeatures(BaseModel):
    """Complete acoustic feature set for verification."""

    # Per-phoneme features
    phoneme_features: List[PhonemeAcousticFeatures]

    # Global features
    global_features: Optional[GlobalFeatures] = None

    # Metadata
    sequence_length: int = Field(..., description="Number of phonemes")
    total_duration_ms: Optional[float] = None

    def get_feature_at_index(self, index: int) -> PhonemeAcousticFeatures:
        """Get acoustic features for phoneme at index."""
        return self.phoneme_features[index]

    def get_features_in_range(self, start: int, end: int) -> List[PhonemeAcousticFeatures]:
        """Get acoustic features for a range of phonemes."""
        return self.phoneme_features[start:end + 1]

    def get_durations(self) -> List[float]:
        """Get list of expected durations."""
        return [f.duration.expected_ms for f in self.phoneme_features]

    def get_total_expected_duration(self) -> float:
        """Calculate total expected duration."""
        return sum(self.get_durations())

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about acoustic features."""
        return {
            "num_phonemes": self.sequence_length,
            "total_duration_ms": self.get_total_expected_duration(),
            "num_with_pitch": sum(1 for f in self.phoneme_features if f.pitch is not None),
            "num_with_formants": sum(1 for f in self.phoneme_features if f.formants is not None),
            "num_nasalized": sum(
                1 for f in self.phoneme_features
                if f.nasalization and f.nasalization.is_nasalized
            ),
            "num_with_ghunnah": sum(
                1 for f in self.phoneme_features
                if f.nasalization and f.nasalization.has_ghunnah()
            )
        }


class VerificationCriterion(BaseModel):
    """Criterion for verifying acoustic features."""

    feature_name: str = Field(..., description="Name of feature to verify")
    comparison_type: ComparisonType
    expected_value: Optional[float] = None
    threshold: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    tolerance: Optional[float] = None
    weight: float = Field(default=1.0, ge=0.0, description="Weight for scoring")
    description: Optional[str] = None


class VerificationTarget(BaseModel):
    """Target for acoustic verification."""

    phoneme_index: int
    phoneme_symbol: str
    time_start_ms: Optional[float] = None  # From MFA alignment
    time_end_ms: Optional[float] = None

    # Expected features
    expected_features: PhonemeAcousticFeatures
    verification_criteria: List[VerificationCriterion]

    # Error definitions
    error_definitions: Dict[str, 'ErrorDefinition'] = Field(
        default_factory=dict,
        description="Map criteria to error types"
    )

    # Tajwīd rule context
    applied_rules: List[str] = Field(default_factory=list)


class ErrorDefinition(BaseModel):
    """Definition of a verification error."""

    error_code: str
    category: ErrorCategory
    description: str
    severity: ErrorSeverity
    criterion: Optional[str] = None  # Which criterion failed


class VerificationResult(BaseModel):
    """Result of verifying a single phoneme."""

    phoneme_index: int
    phoneme_symbol: str
    is_correct: bool

    # Feature-level results
    feature_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Score for each verified feature (0-1)"
    )
    overall_score: float = Field(..., ge=0.0, le=1.0)

    # Errors found
    errors: List[ErrorDefinition] = Field(default_factory=list)

    # Detailed comparisons
    expected_vs_actual: Dict[str, Tuple[float, float]] = Field(
        default_factory=dict,
        description="Map of feature_name -> (expected, actual)"
    )

    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return len(self.errors) > 0

    def get_critical_errors(self) -> List[ErrorDefinition]:
        """Get only critical errors."""
        return [e for e in self.errors if e.severity == ErrorSeverity.CRITICAL]

    def get_errors_by_category(self, category: ErrorCategory) -> List[ErrorDefinition]:
        """Get errors of a specific category."""
        return [e for e in self.errors if e.category == category]


class SequenceVerificationResult(BaseModel):
    """Result of verifying an entire phoneme sequence."""

    # Per-phoneme results
    phoneme_results: List[VerificationResult]

    # Overall metrics
    total_phonemes: int
    correct_phonemes: int
    accuracy: float = Field(..., ge=0.0, le=1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0)

    # Error summary
    total_errors: int
    errors_by_category: Dict[ErrorCategory, int]
    errors_by_severity: Dict[ErrorSeverity, int]

    # Categorical error types
    categorical_errors: List[str] = Field(
        default_factory=list,
        description="List of specific error types (e.g., 'missing_ghunnah', 'short_madd')"
    )

    def is_passing(self, threshold: float = 0.7) -> bool:
        """Check if verification passes a threshold."""
        return self.accuracy >= threshold

    def get_failed_phonemes(self) -> List[VerificationResult]:
        """Get all phonemes that failed verification."""
        return [r for r in self.phoneme_results if not r.is_correct]

    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics."""
        return {
            "total_phonemes": self.total_phonemes,
            "correct": self.correct_phonemes,
            "incorrect": self.total_phonemes - self.correct_phonemes,
            "accuracy": self.accuracy,
            "overall_score": self.overall_score,
            "total_errors": self.total_errors,
            "errors_by_category": {k.value: v for k, v in self.errors_by_category.items()},
            "errors_by_severity": {k.value: v for k, v in self.errors_by_severity.items()},
            "categorical_errors": self.categorical_errors
        }
