# Surah 36 (Ya-Sin) — Phase 2 Stress Test Validation Report

## Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Ayahs aligned | 83 (1 basmalah + 82 content) | 84 | PASS* |
| Total unique words | 521 | — | — |
| Total phones | 5,220 | — | — |
| OOV count | 0 | 0 | PASS |
| Failed alignments | 0 | 0 | PASS |
| Duration issues | 0 | 0 | PASS |
| Phone count mismatches | 2 | 0 | WARN |
| Segmented ayahs | 42 of 83 | — | — |
| Total audio duration | 866s (14.4m) | — | — |
| MFA alignment time | 108s (1.8m) | — | — |
| Alignment coverage | 91.3% | >80% | PASS |

*Note: Ayah count is 83 not 84 because basmalah + "يسٓ" (muqatta'at) 
are merged into a single verse entry. The basmalah IS separately aligned.

## Known Issues

### 1. Muqatta'at letters (يسٓ)
Ayah 1 content after basmalah removal is just "يسٓ" — two disconnected 
letters without diacritics. Phase 1 pipeline cannot process these. 
The audio alignment still works (MFA aligns acoustically) but tajweed 
annotations are missing for this one ayah. This will require a dedicated 
muqatta'at handler in Phase 1.

### 2. Phone count mismatches (2 ayahs)
Two ayahs have a mismatch between Phase 1 expected phone count and 
TextGrid phone count. These are caused by hamzat al-wasl offset 
differences in segmented files — the merge code handles these gracefully.

## Tajweed Coverage

| Category | Annotations | % |
|----------|-------------|---|
| Emphasis/Backing | 2,458 | 72.1% |
| Madd | 457 | 13.4% |
| Noon/Meem Sakinah | 395 | 11.6% |
| Qalqalah | 74 | 2.2% |
| Pronunciation | 24 | 0.7% |
| **Total** | **3,408 on 2,007 phones (38.4%)** | |

### Notable: New rules triggered
- **iqlab**: 6x (first appearance in validation — not present in short surahs)
- **ikhfaa_shafawi**: 3x (also first appearance)
- **madd_munfasil**: 34x (much more frequent in longer text)

### vowel_backing by consonant (including خ/غ/ظ)
| Consonant | Count |
|-----------|-------|
| q (ق) | 76x |
| x (خ) | 34x |
| sˤ (ص) | 20x |
| tˤ (ط) | 17x |
| dˤ (ض) | 12x |
| ɣ (غ) | 10x |
| ðˤ (ظ) | 1x |

## ظ (ðˤ → Z) Mapping Verification

All 5 words containing ظ aligned correctly:

| Ayah | Word | MFA Phone |
|------|------|-----------|
| 36:37 | مُّظْلِمُونَ | Z |
| 36:49 | يَنظُرُونَ | Z |
| 36:54 | تُظْلَمُ | Z |
| 36:56 | ظِلَٰلٍ | Z |
| 36:78 | ٱلْعِظَٰمَ | Z |

## Top 5 Longest Ayahs

| Ayah | Duration | Words | Phones | Segments |
|------|----------|-------|--------|----------|
| 36:47 | 36.5s | 24 | 159 | 5 |
| 36:18 | 18.0s | 12 | 99 | 3 |
| 36:12 | 16.6s | 14 | 100 | 3 |
| 36:14 | 16.6s | 11 | 98 | 3 |
| 36:23 | 16.6s | 15 | 105 | 3 |

## 30ms Phone Analysis

22.5% of phones are at 30ms duration (1,172 of 5,220). 
42 ayahs exceed the 20% threshold. The highest rates are in:
- Basmalah (74%) — short audio, inherent MFA quantization
- Rapid-speech ayahs where reciter speaks connecting words quickly
- This is consistent with the acoustic model's minimum resolution