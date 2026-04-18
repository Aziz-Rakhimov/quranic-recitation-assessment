"""
Enumerations for the Symbolic Layer.

This module defines all enum types used throughout the symbolic layer for
type safety and clear categorization.
"""

from enum import Enum


class PhonemeCategory(str, Enum):
    """Category of phoneme."""
    CONSONANT = "consonant"
    VOWEL = "vowel"
    GEMINATE = "geminate"
    TAJWEED = "tajweed"  # Special Tajwīd-specific phonemes
    DIPHTHONG = "diphthong"


class DiacriticType(str, Enum):
    """Type of Arabic diacritic mark."""
    FATHA = "fatha"           # َ - short 'a'
    DAMMA = "damma"           # ُ - short 'u'
    KASRA = "kasra"           # ِ - short 'i'
    SUKOON = "sukoon"         # ْ - no vowel
    SHADDAH = "shaddah"       # ّ - gemination
    TANWEEN_FATH = "tanween_fath"  # ً - 'an'
    TANWEEN_DAMM = "tanween_damm"  # ٌ - 'un'
    TANWEEN_KASR = "tanween_kasr"  # ٍ - 'in'
    MADDA = "madda"           # آ - extended alif
    DAGGER_ALIF = "dagger_alif"    # ٰ - alif khanjariyah
    HAMZA_ABOVE = "hamza_above"    # ٔ
    HAMZA_BELOW = "hamza_below"    # ٕ


class RuleCategory(str, Enum):
    """Category of Tajwīd rule."""
    NOON_MEEM_SAKINAH = "noon_meem_sakinah"
    MADD = "madd"
    QALQALAH = "qalqalah"
    RAA = "raa"
    LAM = "lam"  # For lām shamsiyyah/qamariyyah
    GENERAL = "general"


class ActionType(str, Enum):
    """Type of action when applying a Tajwīd rule."""
    KEEP_ORIGINAL = "keep_original"
    REPLACE = "replace"
    MODIFY_FEATURES = "modify_features"
    DELETE = "delete"
    INSERT = "insert"
    MERGE = "merge"
    ADD_MARKER = "add_marker"


class PitchContour(str, Enum):
    """Type of pitch contour."""
    LEVEL = "level"
    RISING = "rising"
    FALLING = "falling"
    RISING_FALLING = "rising_falling"
    FALLING_RISING = "falling_rising"


class ArticulationManner(str, Enum):
    """Manner of articulation for consonants."""
    STOP = "stop"
    FRICATIVE = "fricative"
    AFFRICATE = "affricate"
    NASAL = "nasal"
    LATERAL = "lateral"
    TRILL = "trill"
    TAP = "tap"
    APPROXIMANT = "approximant"


class ArticulationPlace(str, Enum):
    """Place of articulation for consonants."""
    BILABIAL = "bilabial"
    LABIODENTAL = "labiodental"
    DENTAL = "dental"
    ALVEOLAR = "alveolar"
    POSTALVEOLAR = "postalveolar"
    PALATAL = "palatal"
    VELAR = "velar"
    UVULAR = "uvular"
    PHARYNGEAL = "pharyngeal"
    GLOTTAL = "glottal"
    LABIO_VELAR = "labio_velar"
    CONTEXTUAL = "contextual"  # For Tajweed phonemes whose place varies by context


class VowelHeight(str, Enum):
    """Vowel height (vertical tongue position)."""
    HIGH = "high"
    MID = "mid"
    LOW = "low"


class VowelBackness(str, Enum):
    """Vowel backness (horizontal tongue position)."""
    FRONT = "front"
    CENTRAL = "central"
    BACK = "back"


class VowelLength(str, Enum):
    """Vowel length."""
    SHORT = "short"
    LONG = "long"


class ComparisonType(str, Enum):
    """Type of comparison for verification criteria."""
    RANGE = "range"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    THRESHOLD = "threshold"
    EXACT = "exact"


class ErrorSeverity(str, Enum):
    """Severity level of recitation error."""
    CRITICAL = "critical"  # Major Tajwīd violation
    MAJOR = "major"        # Significant error
    MINOR = "minor"        # Small deviation
    WARNING = "warning"    # Debatable or stylistic


class ErrorCategory(str, Enum):
    """Category of recitation error."""
    DURATION = "duration"
    PRONUNCIATION = "pronunciation"
    TAJWEED = "tajweed"
    GHUNNAH = "ghunnah"
    MADD = "madd"
    EMPHASIS = "emphasis"
    NASALIZATION = "nasalization"
    QALQALAH = "qalqalah"
    NOON_MEEM_SAKINAH = "noon_meem_sakinah"
    RAA = "raa"
    GENERAL = "general"


class SegmentLevel(str, Enum):
    """Level of text segmentation."""
    PHONEME = "phoneme"
    SYLLABLE = "syllable"
    WORD = "word"
    VERSE = "verse"
    SURAH = "surah"


class BoundaryType(str, Enum):
    """Type of boundary in text."""
    PHONEME = "phoneme"
    SYLLABLE = "syllable"
    WORD = "word"
    VERSE = "verse"
    PAUSE = "pause"


class OutputFormat(str, Enum):
    """Output format for symbolic layer results."""
    JSON = "json"
    MFA_DICT = "mfa_dict"
    TEXTGRID = "textgrid"
    CSV = "csv"
    XML = "xml"


class QalqalahStrength(str, Enum):
    """Strength of qalqalah echoing."""
    MINOR = "minor"  # Weak - mid-word
    MAJOR = "major"  # Strong - word/verse end


class MaddType(str, Enum):
    """Type of madd (prolongation)."""
    TABII = "tabii"              # Natural - 2 counts
    MUTTASIL = "muttasil"        # Connected - 4-5 counts
    MUNFASIL = "munfasil"        # Disconnected - 2-5 counts
    LAZIM = "lazim"              # Necessary - 6 counts
    ARID = "arid"                # Due to pause - variable
    SILAH = "silah"              # Connecting haa - variable
    LIN = "lin"                  # Softening - 2, 4, or 6 counts
    IWAD = "iwad"                # Replacement - 2 counts


class RaaQuality(str, Enum):
    """Quality of rāʾ pronunciation."""
    TAFKHEEM = "tafkheem"  # Heavy/thick/emphatic
    TARQEEQ = "tarqeeq"    # Light/thin


class NoonMeemRule(str, Enum):
    """Specific nūn/mīm sākinah rule."""
    IDHHAR = "idhhar"      # Clear pronunciation
    IDGHAM = "idgham"      # Assimilation
    IQLAB = "iqlab"        # Conversion
    IKHFAA = "ikhfaa"      # Concealment
