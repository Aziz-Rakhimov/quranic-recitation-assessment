"""Load Phase 2 JSON output into typed models."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from phase3_assessment.models import SurahData, Verse

# Default paths
VALIDATION_DIR = Path(__file__).resolve().parent.parent.parent / "phase2_alignment" / "validation"
AUDIO_BASE = Path.home() / "Desktop" / "quran_vc_dataset" / "reciter_2"


def load_surah(surah_num: int, json_dir: Optional[Path] = None) -> SurahData:
    """Load aligned JSON for an entire surah."""
    if json_dir is None:
        json_dir = VALIDATION_DIR / f"surah_{surah_num}"
    path = json_dir / f"surah_{surah_num}_aligned.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return SurahData.from_dict(data)


def audio_path(surah_num: int, ayah_num: int, audio_base: Optional[Path] = None) -> Path:
    """Return the WAV path for a given surah/ayah."""
    if audio_base is None:
        audio_base = AUDIO_BASE
    return audio_base / f"surah_{surah_num}_wav16k" / f"{surah_num:03d}_{ayah_num:03d}.wav"
