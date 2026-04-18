"""Phase 3 data models — mirrors Phase 2 JSON input + defines assessment output."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


# ── Phase 2 input models ──────────────────────────────────────────────

@dataclass
class Phone:
    ipa: str
    mfa: str
    start: float          # seconds
    end: float            # seconds
    duration_ms: float
    tajweed_rules: List[str] = field(default_factory=list)
    alignment_confidence: str = "high"
    geminate_pair: bool = False
    geminate_total_ms: Optional[float] = None
    geminate_position: Optional[str] = None   # "first" | "second"
    is_verse_final: bool = False
    skip_assessment: bool = False
    verse_final_silence_trimmed: bool = False
    original_duration_ms: Optional[float] = None
    trimmed_duration_ms: Optional[float] = None

    @classmethod
    def from_dict(cls, d: dict) -> Phone:
        return cls(
            ipa=d["ipa"],
            mfa=d["mfa"],
            start=d["start"],
            end=d["end"],
            duration_ms=d["duration_ms"],
            tajweed_rules=d.get("tajweed_rules", []),
            alignment_confidence=d.get("alignment_confidence", "high"),
            geminate_pair=d.get("geminate_pair", False),
            geminate_total_ms=d.get("geminate_total_ms"),
            geminate_position=d.get("geminate_position"),
            is_verse_final=d.get("is_verse_final", False),
            skip_assessment=d.get("skip_assessment", False),
            verse_final_silence_trimmed=d.get("verse_final_silence_trimmed", False),
            original_duration_ms=d.get("original_duration_ms"),
            trimmed_duration_ms=d.get("trimmed_duration_ms"),
        )


@dataclass
class Word:
    text: str
    word_index: int
    start: float
    end: float
    duration_ms: float
    phones: List[Phone] = field(default_factory=list)
    skip_tajwid: bool = False
    word_error_type: Optional[str] = None   # "missing" | "wrong" | "added" | None

    @classmethod
    def from_dict(cls, d: dict) -> Word:
        return cls(
            text=d["text"],
            word_index=d["word_index"],
            start=d["start"],
            end=d["end"],
            duration_ms=d["duration_ms"],
            phones=[Phone.from_dict(p) for p in d.get("phones", [])],
        )


@dataclass
class Verse:
    surah: int
    ayah: int
    text: str
    file_id: str
    duration: float
    words: List[Word] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> Verse:
        return cls(
            surah=d["surah"],
            ayah=d["ayah"],
            text=d["text"],
            file_id=d["file_id"],
            duration=d["duration"],
            words=[Word.from_dict(w) for w in d.get("words", [])],
        )

    def all_phones(self) -> List[tuple]:
        """Yield (word, phone) pairs for every phone in the verse."""
        result = []
        for w in self.words:
            for p in w.phones:
                result.append((w, p))
        return result


@dataclass
class SurahData:
    surah: int
    num_ayahs: int
    verses: List[Verse] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> SurahData:
        return cls(
            surah=d["surah"],
            num_ayahs=d["num_ayahs"],
            verses=[Verse.from_dict(v) for v in d.get("verses", [])],
        )


# ── Phase 3 output models ─────────────────────────────────────────────

@dataclass
class AssessmentError:
    word: str
    phone: str
    phone_index: int
    timestamp_ms: float
    rule: str
    assessment: str        # "duration" | "formant" | "energy" | "nasalization"
    expected: float
    actual: float
    unit: str              # "counts" | "hz" | "bool"
    severity: str          # "major" | "minor" | "style"
    description: str

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "phone": self.phone,
            "phone_index": self.phone_index,
            "timestamp_ms": self.timestamp_ms,
            "rule": self.rule,
            "assessment": self.assessment,
            "expected": self.expected,
            "actual": self.actual,
            "unit": self.unit,
            "severity": self.severity,
            "description": self.description,
        }


@dataclass
class AyahReport:
    surah: int
    ayah: int
    reciter: str
    harakah_ms: float
    errors: List[AssessmentError] = field(default_factory=list)
    total_phones_assessed: int = 0
    phones_skipped: int = 0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def score(self) -> float:
        if self.total_phones_assessed == 0:
            return 100.0
        n_major = sum(1 for e in self.errors if e.severity == "major")
        n_minor = sum(1 for e in self.errors if e.severity == "minor")
        weighted = n_major + 0.5 * n_minor
        return max(0.0, 100.0 * (1 - weighted / self.total_phones_assessed))

    @property
    def score_reliability(self) -> str:
        """'high' if >= 10 phones assessed, 'low' otherwise.

        Small surahs/ayahs have few madd phones — a single error has
        outsized score impact. Flag these so the user can interpret
        the score with appropriate caution.
        """
        return "high" if self.total_phones_assessed >= 10 else "low"

    def to_dict(self) -> dict:
        return {
            "surah": self.surah,
            "ayah": self.ayah,
            "reciter": self.reciter,
            "harakah_ms": round(self.harakah_ms, 1),
            "errors": [e.to_dict() for e in self.errors],
            "score": round(self.score, 1),
            "score_reliability": self.score_reliability,
            "total_phones_assessed": self.total_phones_assessed,
            "phones_skipped": self.phones_skipped,
            "error_count": self.error_count,
        }


@dataclass
class CalibrationResult:
    harakah_ms: float
    short_vowel_median_ms: float
    madd_tabii_median_ms: float  # 0.0 if no madd_tabii available
    short_vowel_count: int
    madd_tabii_count: int
    ratio: float                 # madd_tabii / short_vowel — should be ~2.0
    short_vowel_std_ms: float
    madd_tabii_std_ms: float
    is_default: bool = False     # True if fell back to 107ms default
    tolerance_factor: float = 1.0  # 1.0 = standard ±25%, 1.6 = wide ±40%
