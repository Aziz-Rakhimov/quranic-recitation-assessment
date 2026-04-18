"""
Acoustic Feature Generator.

This module generates expected acoustic features (duration, pitch, formants,
nasalization) from annotated phoneme sequences for verification against
recorded recitations.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from .models.phoneme import Phoneme, PhonemeSequence
from .models.rule import AnnotatedPhonemeSequence, RuleApplication
from .models.features import (
    Duration,
    Pitch,
    Formants,
    Nasalization,
    PhonemeAcousticFeatures,
    AcousticFeatures
)
from .models.enums import PitchContour


class AcousticFeatureGenerator:
    """
    Generates expected acoustic features for phoneme sequences.

    Uses default parameters from feature_defaults.yaml and applies
    context-aware adjustments based on Tajwīd rules and phonological context.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        speaker_type: str = "male"
    ):
        """
        Initialize the acoustic feature generator.

        Args:
            config_path: Path to feature_defaults.yaml
            speaker_type: "male", "female", or "child" for F0 baseline
        """
        if config_path is None:
            config_path = "data/acoustic_features/feature_defaults.yaml"

        self.config_path = Path(config_path)
        self.speaker_type = speaker_type
        self.config = self._load_config()

        # Extract commonly used parameters
        self.durations = self.config.get('durations', {})
        self.pitch_params = self.config.get('pitch', {})
        self.formant_params = self.config.get('formants', {})
        self.nasalization_params = self.config.get('nasalization', {})
        self.qalqalah_params = self.config.get('qalqalah', {})
        self.emphasis_params = self.config.get('emphasis', {})

        # Get baseline F0
        self.baseline_f0 = self.pitch_params.get('baseline', {}).get(speaker_type, 120)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
            return {}

    def generate_features(
        self,
        annotated_sequence: AnnotatedPhonemeSequence
    ) -> AcousticFeatures:
        """
        Generate acoustic features for entire annotated sequence.

        Args:
            annotated_sequence: Phoneme sequence with applied Tajwīd rules

        Returns:
            AcousticFeatures with all phoneme-level features
        """
        phoneme_features = []

        for i, phoneme in enumerate(annotated_sequence.phonemes):
            # Get rule applications for this phoneme
            rules_at_position = [
                app for app in annotated_sequence.rule_applications
                if app.start_index <= i <= app.end_index
            ]

            # Build context
            context = self._build_context(annotated_sequence, i)

            # Generate features for this phoneme
            features = self._generate_phoneme_features(
                phoneme,
                rules_at_position,
                context
            )

            phoneme_features.append(features)

        return AcousticFeatures(
            phoneme_features=phoneme_features,
            total_duration_ms=sum(f.duration.expected_ms for f in phoneme_features),
            sequence_length=len(phoneme_features)
        )

    def _build_context(
        self,
        sequence: AnnotatedPhonemeSequence,
        index: int
    ) -> Dict[str, Any]:
        """Build context information for a phoneme."""
        context = {
            'position': index,
            'total_phonemes': len(sequence.phonemes),
            'is_word_boundary': index in sequence.word_boundaries,
            'is_verse_boundary': index in sequence.verse_boundaries,
            'is_word_final': (index + 1) in sequence.word_boundaries or (index + 1) >= len(sequence.phonemes),
            'is_verse_final': (index + 1) in sequence.verse_boundaries or (index + 1) >= len(sequence.phonemes),
        }

        # Get preceding and following phonemes
        if index > 0:
            context['preceding_phoneme'] = sequence.phonemes[index - 1]
        if index < len(sequence.phonemes) - 1:
            context['following_phoneme'] = sequence.phonemes[index + 1]

        return context

    def _generate_phoneme_features(
        self,
        phoneme: Phoneme,
        rules: List[RuleApplication],
        context: Dict[str, Any]
    ) -> PhonemeAcousticFeatures:
        """
        Generate acoustic features for a single phoneme.

        Args:
            phoneme: The phoneme
            rules: Tajwīd rules applied to this phoneme
            context: Context information

        Returns:
            Complete acoustic features for the phoneme
        """
        # Calculate each feature type
        duration = self._calculate_duration(phoneme, rules, context)
        pitch = self._calculate_pitch(phoneme, rules, context)
        formants = self._calculate_formants(phoneme, rules, context)
        nasalization = self._calculate_nasalization(phoneme, rules, context)

        return PhonemeAcousticFeatures(
            phoneme_index=context['position'],
            phoneme_symbol=phoneme.symbol,
            duration=duration,
            pitch=pitch,
            formants=formants,
            nasalization=nasalization,
            in_emphatic_context=context.get('preceding_phoneme') and context['preceding_phoneme'].is_emphatic() if context.get('preceding_phoneme') else False,
            in_word_boundary=context.get('is_word_boundary', False),
            in_verse_boundary=context.get('is_verse_boundary', False)
        )

    def _calculate_duration(
        self,
        phoneme: Phoneme,
        rules: List[RuleApplication],
        context: Dict[str, Any]
    ) -> Duration:
        """Calculate expected duration for a phoneme."""
        base_durations = self.durations.get('base', {})
        tajweed_durations = self.durations.get('tajweed', {})
        context_multipliers = self.durations.get('context_multipliers', {})
        tolerances = self.durations.get('tolerance', {})

        # Get base duration
        if phoneme.is_vowel():
            if phoneme.is_long():
                base_ms = base_durations.get('long_vowel', 200)
                tolerance = tolerances.get('long_vowel', 50)
            else:
                base_ms = base_durations.get('short_vowel', 100)
                tolerance = tolerances.get('short_vowel', 25)
        else:
            if phoneme.is_geminate():
                base_ms = base_durations.get('geminate', 160)
            else:
                base_ms = base_durations.get('consonant', 80)
            tolerance = tolerances.get('consonant', 20)

        # Apply Tajwīd rule modifications
        multiplier = 1.0
        for rule in rules:
            if rule.rule.action.duration_multiplier:
                multiplier *= rule.rule.action.duration_multiplier

            # Check for specific Tajwīd durations
            if rule.acoustic_expectations:
                if rule.acoustic_expectations.duration_ms:
                    base_ms = rule.acoustic_expectations.duration_ms
                if rule.acoustic_expectations.duration_counts:
                    # Convert counts to ms (1 count ≈ 200ms)
                    base_ms = rule.acoustic_expectations.duration_counts * 200
                if rule.acoustic_expectations.duration_tolerance:
                    tolerance = rule.acoustic_expectations.duration_tolerance

        # Apply context multipliers
        if context.get('is_word_final'):
            multiplier *= context_multipliers.get('word_final', 1.3)
        if context.get('is_verse_final'):
            multiplier *= context_multipliers.get('verse_final', 1.5)

        expected_ms = base_ms * multiplier

        return Duration(
            expected_ms=expected_ms,
            min_acceptable_ms=expected_ms - tolerance,
            max_acceptable_ms=expected_ms + tolerance,
            confidence=0.9
        )

    def _calculate_pitch(
        self,
        phoneme: Phoneme,
        rules: List[RuleApplication],
        context: Dict[str, Any]
    ) -> Pitch:
        """Calculate expected pitch for a phoneme."""
        # Start with baseline F0
        expected_f0 = self.baseline_f0

        # Apply phoneme-specific modifications
        if phoneme.is_emphatic():
            expected_f0 *= self.pitch_params.get('emphatic_factor', 0.9)

        if phoneme.features.place in ['pharyngeal', 'uvular']:
            expected_f0 *= self.pitch_params.get('pharyngeal_factor', 0.85)

        if phoneme.is_vowel() and phoneme.symbol in ['i', 'iː', 'u', 'uː']:
            expected_f0 *= self.pitch_params.get('high_vowel_factor', 1.1)

        # Determine contour based on context
        contour_type = PitchContour.LEVEL
        f0_delta = 0

        if context.get('is_verse_final'):
            contour_type = PitchContour.FALLING
            f0_delta = self.pitch_params.get('contours', {}).get('final_fall', {}).get('f0_delta', -50)
        elif context.get('is_word_final'):
            contour_type = PitchContour.FALLING
            f0_delta = self.pitch_params.get('contours', {}).get('falling', {}).get('f0_delta', -30)

        # Apply rule-specific modifications
        for rule in rules:
            if rule.acoustic_expectations and rule.acoustic_expectations.f0_lowering_factor:
                expected_f0 *= rule.acoustic_expectations.f0_lowering_factor

        tolerance = self.pitch_params.get('tolerance', {}).get('max_deviation', 30)

        return Pitch(
            contour_type=contour_type,
            expected_f0_hz=expected_f0,
            f0_start_hz=expected_f0,
            f0_end_hz=expected_f0 + f0_delta,
            acceptable_range_hz=(expected_f0 - tolerance, expected_f0 + tolerance),
            confidence=0.8
        )

    def _calculate_formants(
        self,
        phoneme: Phoneme,
        rules: List[RuleApplication],
        context: Dict[str, Any]
    ) -> Optional[Formants]:
        """Calculate expected formants for a phoneme."""
        if not phoneme.is_vowel():
            return None  # Consonants don't have clear formant structure

        # Get base formants for vowel
        vowel_formants = self.formant_params.get('vowels', {})
        base_formants = vowel_formants.get(phoneme.symbol, {})

        if not base_formants:
            return None

        f1 = base_formants.get('f1', 500)
        f2 = base_formants.get('f2', 1500)
        f3 = base_formants.get('f3', 2500)

        # Check for emphatic context
        preceding = context.get('preceding_phoneme')
        following = context.get('following_phoneme')

        is_emphatic_context = False
        if preceding and preceding.is_emphatic():
            is_emphatic_context = True
        if following and following.is_emphatic():
            is_emphatic_context = True

        # Apply emphatic effects
        if is_emphatic_context:
            emphatic_effects = self.formant_params.get('emphatic_effects', {})
            f1 += emphatic_effects.get('f1_shift', 50)
            f2 += emphatic_effects.get('f2_shift', -200)
            f3 += emphatic_effects.get('f3_shift', 0)

        # Apply rule-specific modifications
        for rule in rules:
            if rule.acoustic_expectations:
                if rule.acoustic_expectations.f2_lowering_hz:
                    f2 -= rule.acoustic_expectations.f2_lowering_hz

        tolerances = self.formant_params.get('tolerance', {})

        return Formants(
            f1_hz=f1,
            f2_hz=f2,
            f3_hz=f3,
            f1_range_hz=(f1 - tolerances.get('f1', 50), f1 + tolerances.get('f1', 50)),
            f2_range_hz=(f2 - tolerances.get('f2', 100), f2 + tolerances.get('f2', 100)),
            f3_range_hz=(f3 - tolerances.get('f3', 150), f3 + tolerances.get('f3', 150)),
            confidence=0.85
        )

    def _calculate_nasalization(
        self,
        phoneme: Phoneme,
        rules: List[RuleApplication],
        context: Dict[str, Any]
    ) -> Optional[Nasalization]:
        """Calculate nasalization features if applicable."""
        # Check if any rules apply ghunnah
        has_ghunnah = False
        ghunnah_type = None
        intensity = 0.0
        duration_counts = 0

        for rule in rules:
            if rule.acoustic_expectations and rule.acoustic_expectations.ghunnah_present:
                has_ghunnah = True
                intensity = max(intensity, rule.acoustic_expectations.nasalization_strength or 0.8)
                duration_counts = rule.acoustic_expectations.ghunnah_duration_counts or 2

                # Determine ghunnah type from rule name
                rule_name_lower = rule.rule.name.lower()
                if 'idgham' in rule_name_lower:
                    ghunnah_type = "idgham"
                elif 'iqlab' in rule_name_lower:
                    ghunnah_type = "iqlab"
                elif 'ikhfaa' in rule_name_lower:
                    ghunnah_type = "ikhfaa"

        if not has_ghunnah:
            # Check if phoneme is inherently nasal
            if phoneme.features.manner == 'nasal':
                has_ghunnah = True
                intensity = 0.6
                duration_counts = 1

        if not has_ghunnah:
            return None

        # Get type-specific parameters
        types_params = self.nasalization_params.get('types', {})
        type_info = types_params.get(ghunnah_type, {})
        if type_info:
            intensity = type_info.get('intensity', intensity)

        markers = self.nasalization_params.get('markers', {})

        return Nasalization(
            is_nasalized=True,
            ghunnah_duration_counts=duration_counts,
            nasal_intensity=intensity,
            nasal_formant_hz=markers.get('nasal_formant_hz', 300),
            f1_reduction_factor=markers.get('f1_reduction_factor', 0.7),
            confidence=0.9
        )

    def get_statistics(self, features: AcousticFeatures) -> Dict[str, Any]:
        """Get statistics about generated acoustic features."""
        return {
            'total_phonemes': features.sequence_length,
            'total_duration_ms': features.total_duration_ms,
            'average_duration_ms': features.total_duration_ms / features.sequence_length if features.sequence_length > 0 else 0,
            'num_nasalized': sum(1 for f in features.phoneme_features if f.nasalization and f.nasalization.is_nasalized),
            'num_vowels': sum(1 for f in features.phoneme_features if f.formants is not None),
            'pitch_range_hz': (
                min(f.pitch.expected_f0_hz for f in features.phoneme_features if f.pitch),
                max(f.pitch.expected_f0_hz for f in features.phoneme_features if f.pitch)
            ) if features.phoneme_features else (0, 0)
        }

    def __repr__(self) -> str:
        return f"AcousticFeatureGenerator(speaker={self.speaker_type}, baseline_f0={self.baseline_f0}Hz)"
