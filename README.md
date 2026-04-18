# Qur'anic Recitation Assessment System

An automated assessment system for evaluating Qur'anic recitation according to the Ḥafṣ ʿan ʿĀṣim riwāyah.

## Project Overview

This system provides automated evaluation of Qur'anic recitations by analyzing audio recordings against the standardized text and pronunciation rules of the Ḥafṣ ʿan ʿĀṣim transmission. The system identifies recitation errors, provides feedback on Tajweed rules, and assesses overall recitation quality.

## System Architecture

The assessment system is built on three complementary layers:

### 1. Symbolic Layer
Processes the Qur'anic text and applies Tajweed rules at the symbolic level. This layer handles:
- Text normalization and diacritical mark processing
- Rule-based Tajweed analysis (Idghām, Iqlāb, Ikhfāʾ, Madd, etc.)
- Generation of expected pronunciation sequences

### 2. Alignment Layer
Aligns the audio recitation with the expected text sequence. This layer performs:
- Audio-to-text synchronization
- Phoneme-level alignment
- Temporal segmentation of recited verses

### 3. Acoustic Verification Layer
Verifies the acoustic realization of Tajweed rules and pronunciation. This layer includes:
- Acoustic feature extraction
- Pronunciation verification against expected phonetic targets
- Detection of common recitation errors

## Current Status & Assumptions

### Phase 1: Symbolic Layer (Complete ✅)
- **24 Tajweed rules implemented** (100% verification)
- **Rule categories:** Noon/Meem Sākinah (11), Madd (6), Qalqalah (5), Pronunciation (2)
- **Rāʾ rules:** Deferred to Phase 2

### Waqf (Pausing) Assumption
**Important:** The system currently assumes **continuous recitation within verses**, with pauses (waqf) occurring only at **verse boundaries**. This matches the most common recitation pattern and is sufficient for verse-level assessment.

**Supported waqf contexts:**
- ✅ Verse-end pausing (waqf) - Fully supported
- ❌ Mid-verse pausing - Deferred to Phase 3

**Affected rules:**
- Tāʾ Marbūṭa (ة): 't' vs 'h' pronunciation ✅
- Madd ʿĀriḍ Lissukūn: Prolongation at verse-end ✅
- Cross-word rules: Correctly handle verse boundaries ✅

Mid-verse pause handling (including tanween dropping, final vowel conversion) will be implemented in Phase 3 with acoustic pause detection. See [WAQF_DESIGN_DECISION.md](WAQF_DESIGN_DECISION.md) for details.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd quranic-recitation-assessment

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```python
from src.symbolic_layer import TajweedAnalyzer
from src.alignment import RecitationAligner
from src.acoustic_verification import AcousticVerifier

# Initialize the assessment pipeline
analyzer = TajweedAnalyzer()
aligner = RecitationAligner()
verifier = AcousticVerifier()

# Assess a recitation
results = assess_recitation(
    audio_path="path/to/recitation.wav",
    surah=1,
    ayah=1
)

print(results)
```
