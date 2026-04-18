"""
Symbolic Layer Pipeline Orchestrator.

This module provides the main SymbolicLayerPipeline class that orchestrates
all components of the symbolic layer into a single, unified processing pipeline.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from .text_processor import QuranTextProcessor
from .phonemizer import QuranPhonemizer
from .tajweed_engine import TajweedEngine
from .acoustic_features import AcousticFeatureGenerator
from .models.output import SymbolicOutput
from .models.phoneme import PhonemeInventory


class SymbolicLayerPipeline:
    """
    Main pipeline for the Symbolic Layer.

    Coordinates all processing steps:
    1. Text normalization and validation
    2. Phonemization (G2P conversion)
    3. Tajwīd rule application
    4. Acoustic feature generation
    5. Output formatting
    """

    def __init__(
        self,
        quran_text_path: Optional[str] = None,
        base_phonemes_path: Optional[str] = None,
        tajweed_phonemes_path: Optional[str] = None,
        g2p_rules_path: Optional[str] = None,
        tajweed_rules_dir: Optional[str] = None,
        acoustic_config_path: Optional[str] = None,
        speaker_type: str = "male",
        enable_raa_rules: bool = False
    ):
        """
        Initialize the symbolic layer pipeline.

        Args:
            quran_text_path: Path to Qur'anic text JSON file
            base_phonemes_path: Path to base_phonemes.yaml
            tajweed_phonemes_path: Path to tajweed_phonemes.yaml
            g2p_rules_path: Path to g2p_rules.yaml
            tajweed_rules_dir: Directory containing Tajwīd rule YAML files
            acoustic_config_path: Path to feature_defaults.yaml
            speaker_type: "male", "female", or "child" for F0 baseline
            enable_raa_rules: Whether to enable Rāʾ tafkhīm/tarqīq rules (default: False)
        """
        # Set default paths
        if quran_text_path is None:
            quran_text_path = "data/quran_text/quran_hafs.json"
        if base_phonemes_path is None:
            base_phonemes_path = "data/pronunciation_dict/base_phonemes.yaml"
        if tajweed_phonemes_path is None:
            tajweed_phonemes_path = "data/pronunciation_dict/tajweed_phonemes.yaml"
        if g2p_rules_path is None:
            g2p_rules_path = "data/pronunciation_dict/g2p_rules.yaml"
        if tajweed_rules_dir is None:
            tajweed_rules_dir = "data/tajweed_rules"
        if acoustic_config_path is None:
            acoustic_config_path = "data/acoustic_features/feature_defaults.yaml"

        self.quran_text_path = Path(quran_text_path)
        self.speaker_type = speaker_type
        self.enable_raa_rules = enable_raa_rules

        # Load Qur'anic text if available
        self.quran_text = self._load_quran_text() if self.quran_text_path.exists() else None

        # Initialize components
        print("Initializing Symbolic Layer Pipeline...")

        print("  - Loading phoneme inventory...")
        self.phoneme_inventory = PhonemeInventory.from_yaml_files(
            base_phonemes_path=base_phonemes_path,
            tajweed_phonemes_path=tajweed_phonemes_path
        )

        print("  - Initializing text processor...")
        self.text_processor = QuranTextProcessor(normalization_form="NFD")

        print("  - Initializing phonemizer...")
        self.phonemizer = QuranPhonemizer(
            base_phonemes_path=base_phonemes_path,
            tajweed_phonemes_path=tajweed_phonemes_path,
            g2p_rules_path=g2p_rules_path
        )

        print("  - Loading Tajweed engine...")
        self.tajweed_engine = TajweedEngine(
            rule_config_dir=tajweed_rules_dir,
            phoneme_inventory=self.phoneme_inventory,
            enable_raa_rules=enable_raa_rules
        )

        print("  - Initializing acoustic feature generator...")
        self.acoustic_generator = AcousticFeatureGenerator(
            config_path=acoustic_config_path,
            speaker_type=speaker_type
        )

        print(f"✅ Pipeline initialized successfully!")
        print(f"   - Phoneme inventory: {len(self.phoneme_inventory.phonemes)} phonemes")
        print(f"   - Tajweed rules: {len(self.tajweed_engine.rules)} rules")
        if not enable_raa_rules:
            print(f"   ⚠️  Rāʾ rules disabled (Phase 1 - focusing on core rules)")
        print(f"   - Speaker type: {speaker_type}")

    def _load_quran_text(self) -> Dict[str, Any]:
        """Load Qur'anic text from JSON file."""
        try:
            with open(self.quran_text_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load Qur'anic text from {self.quran_text_path}: {e}")
            return {}

    def _get_verse_text(self, surah: int, ayah: int) -> Optional[str]:
        """Get text for a specific verse."""
        if not self.quran_text:
            return None

        try:
            # Find surah
            surahs = self.quran_text.get('surahs', [])
            for surah_data in surahs:
                if surah_data.get('number') == surah:
                    # Find ayah (ayah parameter is 1-indexed, array is 0-indexed)
                    ayahs = surah_data.get('ayahs', [])
                    if 0 < ayah <= len(ayahs):
                        return ayahs[ayah - 1].get('text', '')
            return None
        except Exception as e:
            print(f"Error getting verse {surah}:{ayah}: {e}")
            return None

    def process_text(
        self,
        text: str,
        surah: Optional[int] = None,
        ayah: Optional[int] = None
    ) -> SymbolicOutput:
        """
        Process arbitrary Arabic text through the complete pipeline.

        Args:
            text: Arabic text to process
            surah: Optional surah number (for metadata)
            ayah: Optional ayah number (for metadata)

        Returns:
            SymbolicOutput with all processing results
        """
        # Step 1: Text processing
        normalized_text = self.text_processor.normalize(text)

        # Validate
        is_valid, message = self.text_processor.validate_text(normalized_text)
        if not is_valid:
            raise ValueError(f"Invalid text: {message}")

        # Step 2: Phonemization
        phoneme_sequence = self.phonemizer.phonemize(normalized_text)

        # Step 3: Apply Tajweed rules
        annotated_sequence = self.tajweed_engine.apply_rules(phoneme_sequence)

        # Step 4: Generate acoustic features
        acoustic_features = self.acoustic_generator.generate_features(annotated_sequence)

        # Create output
        output = SymbolicOutput(
            original_text=text,
            normalized_text=normalized_text,
            phoneme_sequence=phoneme_sequence,
            annotated_sequence=annotated_sequence,
            acoustic_features=acoustic_features,
            surah=surah,
            ayah=ayah,
            processing_timestamp=datetime.now().isoformat()
        )

        return output

    def process_verse(self, surah: int, ayah: int) -> SymbolicOutput:
        """
        Process a specific verse from the Qur'an.

        Args:
            surah: Surah number (1-114)
            ayah: Ayah number

        Returns:
            SymbolicOutput with all processing results

        Raises:
            ValueError: If verse not found or invalid
        """
        # Get verse text
        text = self._get_verse_text(surah, ayah)

        if text is None:
            raise ValueError(f"Verse {surah}:{ayah} not found in Qur'anic text database")

        # Process using main pipeline
        return self.process_text(text, surah=surah, ayah=ayah)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the pipeline components."""
        return {
            "pipeline": {
                "speaker_type": self.speaker_type,
                "quran_text_loaded": self.quran_text is not None,
                "enable_raa_rules": self.enable_raa_rules,
            },
            "phoneme_inventory": self.phoneme_inventory.get_statistics(),
            "tajweed_engine": self.tajweed_engine.get_statistics(),
            "text_processor": {
                "normalization_form": self.text_processor.normalization_form,
            }
        }

    def __repr__(self) -> str:
        return f"SymbolicLayerPipeline(speaker={self.speaker_type}, rules={len(self.tajweed_engine.rules)})"
