"""
Output models for the Symbolic Layer.

This module defines the SymbolicOutput model which encapsulates all results
from the symbolic layer processing pipeline.
"""

import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .phoneme import PhonemeSequence
from .rule import AnnotatedPhonemeSequence, RuleApplication
from .features import AcousticFeatures


class VerificationTarget(BaseModel):
    """
    Verification target for acoustic layer.

    Represents expected acoustic properties that should be verified
    in the recorded recitation.
    """

    phoneme_index: int
    phoneme_symbol: str

    # Duration verification
    expected_duration_ms: float
    duration_tolerance_ms: float

    # Pitch verification (if applicable)
    expected_f0_hz: Optional[float] = None
    f0_tolerance_hz: Optional[float] = None

    # Formant verification (for vowels)
    expected_f1_hz: Optional[float] = None
    expected_f2_hz: Optional[float] = None
    expected_f3_hz: Optional[float] = None
    formant_tolerance_hz: Optional[float] = None

    # Nasalization verification
    expected_nasalization: bool = False
    nasalization_intensity: Optional[float] = None

    # Rule context
    applied_rules: List[str] = Field(default_factory=list)
    rule_categories: List[str] = Field(default_factory=list)

    # Verification priority
    priority: float = Field(default=1.0, ge=0.0, le=1.0)

    # Error definitions
    error_on_mismatch: str = "duration_mismatch"
    error_severity: str = "minor"


class SymbolicOutput(BaseModel):
    """
    Complete output from the Symbolic Layer pipeline.

    Contains all intermediate and final results from text processing,
    phonemization, rule application, and acoustic feature generation.
    """

    # Original input
    original_text: str
    normalized_text: str

    # Phoneme sequence
    phoneme_sequence: PhonemeSequence
    annotated_sequence: AnnotatedPhonemeSequence

    # Acoustic features
    acoustic_features: AcousticFeatures

    # Metadata
    surah: Optional[int] = None
    ayah: Optional[int] = None
    processing_timestamp: Optional[str] = None

    def to_ipa_string(self, separator: str = " ") -> str:
        """Get IPA string representation."""
        return self.annotated_sequence.to_ipa_string(separator)

    def to_mfa_dict(self) -> str:
        """
        Export in Montreal Forced Aligner dictionary format.

        Format: word TAB phoneme1 phoneme2 phoneme3

        Returns:
            MFA dictionary string
        """
        lines = []

        # Get words from phoneme sequence
        words = self.phoneme_sequence.get_words()

        for word_seq in words:
            if word_seq.original_text:
                word_text = word_seq.original_text.strip()
                # Get phonemes for this word
                phonemes_str = " ".join(p.symbol for p in word_seq.phonemes)
                lines.append(f"{word_text}\t{phonemes_str}")

        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        """
        Export as JSON.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string
        """
        output_dict = {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "phonemes": {
                "ipa_string": self.to_ipa_string(),
                "phoneme_count": len(self.phoneme_sequence.phonemes),
                "phonemes": [
                    {
                        "symbol": p.symbol,
                        "category": p.category.value,
                        "duration_factor": p.duration_factor,
                        "is_vowel": p.is_vowel(),
                        "is_consonant": p.is_consonant(),
                        "is_emphatic": p.is_emphatic()
                    }
                    for p in self.phoneme_sequence.phonemes
                ]
            },
            "tajweed_rules": {
                "total_applications": len(self.annotated_sequence.rule_applications),
                "applications": [
                    {
                        "rule_name": app.rule.name,
                        "rule_category": app.rule.category.value,
                        "arabic_name": app.rule.arabic_name,
                        "start_index": app.start_index,
                        "end_index": app.end_index,
                        "original_phonemes": [p.symbol for p in app.original_phonemes],
                        "modified_phonemes": [p.symbol for p in app.modified_phonemes],
                        "confidence": app.confidence
                    }
                    for app in self.annotated_sequence.rule_applications
                ]
            },
            "acoustic_features": {
                "total_duration_ms": self.acoustic_features.total_duration_ms,
                "sequence_length": self.acoustic_features.sequence_length,
                "phoneme_features": [
                    {
                        "phoneme_symbol": pf.phoneme_symbol,
                        "phoneme_index": pf.phoneme_index,
                        "duration_ms": pf.duration.expected_ms,
                        "pitch_hz": pf.pitch.expected_f0_hz if pf.pitch else None,
                        "formants": {
                            "f1": pf.formants.f1_hz,
                            "f2": pf.formants.f2_hz,
                            "f3": pf.formants.f3_hz
                        } if pf.formants else None,
                        "nasalized": pf.nasalization.is_nasalized if pf.nasalization else False
                    }
                    for pf in self.acoustic_features.phoneme_features
                ]
            },
            "metadata": {
                "surah": self.surah,
                "ayah": self.ayah,
                "timestamp": self.processing_timestamp
            }
        }

        return json.dumps(output_dict, ensure_ascii=False, indent=indent)

    def to_textgrid(self) -> str:
        """
        Export as Praat TextGrid format.

        TextGrid format is used by Praat and Montreal Forced Aligner.

        Returns:
            TextGrid string
        """
        # Calculate time points from durations
        time_points = [0.0]
        for pf in self.acoustic_features.phoneme_features:
            time_points.append(time_points[-1] + pf.duration.expected_ms / 1000.0)

        total_duration = time_points[-1]

        # Build TextGrid
        lines = [
            'File type = "ooTextFile"',
            'Object class = "TextGrid"',
            '',
            f'xmin = 0',
            f'xmax = {total_duration:.6f}',
            'tiers? <exists>',
            'size = 2',  # Two tiers: phonemes and words
            'item []:',
            '    item [1]:',
            '        class = "IntervalTier"',
            '        name = "phonemes"',
            f'        xmin = 0',
            f'        xmax = {total_duration:.6f}',
            f'        intervals: size = {len(self.acoustic_features.phoneme_features)}',
        ]

        # Add phoneme intervals
        for i, pf in enumerate(self.acoustic_features.phoneme_features):
            lines.extend([
                f'        intervals [{i + 1}]:',
                f'            xmin = {time_points[i]:.6f}',
                f'            xmax = {time_points[i + 1]:.6f}',
                f'            text = "{pf.phoneme_symbol}"'
            ])

        # Add word tier (simplified - one word for entire text)
        lines.extend([
            '    item [2]:',
            '        class = "IntervalTier"',
            '        name = "words"',
            f'        xmin = 0',
            f'        xmax = {total_duration:.6f}',
            '        intervals: size = 1',
            '        intervals [1]:',
            f'            xmin = 0',
            f'            xmax = {total_duration:.6f}',
            f'            text = "{self.original_text}"'
        ])

        return '\n'.join(lines)

    def get_verification_targets(self) -> List[VerificationTarget]:
        """
        Generate verification targets for acoustic layer.

        Returns:
            List of verification targets with expected values
        """
        targets = []

        for i, pf in enumerate(self.acoustic_features.phoneme_features):
            # Get applied rules for this phoneme
            applied_rules = []
            rule_categories = []

            for app in self.annotated_sequence.rule_applications:
                if app.start_index <= i <= app.end_index:
                    applied_rules.append(app.rule.name)
                    rule_categories.append(app.rule.category.value)

            # Create verification target
            target = VerificationTarget(
                phoneme_index=i,
                phoneme_symbol=pf.phoneme_symbol,
                expected_duration_ms=pf.duration.expected_ms,
                duration_tolerance_ms=pf.duration.expected_ms - pf.duration.min_acceptable_ms,
                expected_f0_hz=pf.pitch.expected_f0_hz if pf.pitch else None,
                f0_tolerance_hz=30.0 if pf.pitch else None,
                expected_f1_hz=pf.formants.f1_hz if pf.formants else None,
                expected_f2_hz=pf.formants.f2_hz if pf.formants else None,
                expected_f3_hz=pf.formants.f3_hz if pf.formants else None,
                formant_tolerance_hz=100.0 if pf.formants else None,
                expected_nasalization=pf.nasalization.is_nasalized if pf.nasalization else False,
                nasalization_intensity=pf.nasalization.nasal_intensity if pf.nasalization else None,
                applied_rules=applied_rules,
                rule_categories=rule_categories,
                priority=1.0 if applied_rules else 0.7,
                error_on_mismatch="duration_mismatch" if not applied_rules else f"{rule_categories[0]}_error",
                error_severity="major" if applied_rules else "minor"
            )

            targets.append(target)

        return targets

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the output."""
        return {
            "text": {
                "original_length": len(self.original_text),
                "normalized_length": len(self.normalized_text),
            },
            "phonemes": {
                "total": len(self.phoneme_sequence.phonemes),
                "vowels": sum(1 for p in self.phoneme_sequence.phonemes if p.is_vowel()),
                "consonants": sum(1 for p in self.phoneme_sequence.phonemes if p.is_consonant()),
                "emphatic": sum(1 for p in self.phoneme_sequence.phonemes if p.is_emphatic()),
            },
            "tajweed_rules": {
                "total_applications": len(self.annotated_sequence.rule_applications),
                "by_category": self._count_rules_by_category(),
            },
            "acoustic_features": {
                "total_duration_ms": self.acoustic_features.total_duration_ms,
                "average_phoneme_duration_ms": self.acoustic_features.total_duration_ms / self.acoustic_features.sequence_length if self.acoustic_features.sequence_length > 0 else 0,
                "nasalized_phonemes": sum(1 for pf in self.acoustic_features.phoneme_features if pf.nasalization and pf.nasalization.is_nasalized),
            }
        }

    def _count_rules_by_category(self) -> Dict[str, int]:
        """Count rule applications by category."""
        counts = {}
        for app in self.annotated_sequence.rule_applications:
            category = app.rule.category.value
            counts[category] = counts.get(category, 0) + 1
        return counts

    def __repr__(self) -> str:
        return f"SymbolicOutput(text='{self.original_text[:30]}...', phonemes={len(self.phoneme_sequence.phonemes)}, rules={len(self.annotated_sequence.rule_applications)})"
