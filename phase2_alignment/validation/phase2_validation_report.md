# Phase 2 Alignment — Validation Report

**Status: FAIL**

Generated: 2026-03-25 09:46:19

## Overall Summary

| Metric | Value |
|--------|-------|
| Test surahs | 8 |
| Total ayahs | 127 |
| Total words aligned | 961 |
| Total phones aligned | 6843 |
| OOV words | 0 |
| Failed alignments | 0 |
| Phone count mismatches | 2 |
| Phone duration issues | 0 |
| Phones with tajweed rules | 2637/6843 (38.5%) |
| Total audio duration | 1167.7s |
| Total aligned span | 1051.3s |
| Alignment coverage | 90.0% |
| Total MFA time | 658.9s |

## Per-Surah Results

| Surah | Name | Ayahs | Words | Phones | OOV | Failed | Duration Issues | Phone Mismatches | Tajweed % | Coverage % | MFA Time |
|-------|------|-------|-------|--------|-----|--------|-----------------|------------------|-----------|------------|----------|
| 1 | Al-Faatiha | 1-7 | 29 | 224 | 0 | 0 | 0 | 0 | 33.0% | 78.8% | 85.8s |
| 93 | Ad-Dhuhaa | 1-11 | 40 | 288 | 0 | 0 | 0 | 0 | 46.5% | 83.8% | 80.1s |
| 97 | Al-Qadr | 1-5 | 34 | 222 | 0 | 0 | 0 | 0 | 36.0% | 87.7% | 79.4s |
| 113 | Al-Falaq | 1-5 | 23 | 131 | 0 | 0 | 0 | 0 | 38.9% | 86.5% | 78.6s |
| 114 | An-Naas | 1-6 | 24 | 154 | 0 | 0 | 0 | 0 | 31.2% | 81.8% | 79.1s |
| 67 | Al-Mulk (1-5) | 1-5 | 64 | 459 | 0 | 0 | 0 | 0 | 37.3% | 93.1% | 79.8s |
| 56 | Al-Waaqia (1-5) | 1-5 | 19 | 145 | 0 | 0 | 0 | 0 | 33.8% | 83.9% | 78.3s |
| 36 | Ya-Sin | 1-83 | 728 | 5220 | 0 | 0 | 0 | 2 | 38.9% | 91.3% | 98.0s |

## Critical Checks

### 1. OOV Words (must be 0)

PASS: No OOV words found across all test surahs.

### 2. Failed Alignments (must be 0)

PASS: All ayahs aligned successfully.

### 3. Phone Count Consistency

**FAIL: 2 mismatches.**

- 036_021: "ٱتَّبِعُوا" expected=10 actual=8
- 036_082: "شَئًْا" expected=5 actual=1

### 4. Phone Duration Sanity

PASS: No phones outside expected duration range.

### 5. Tajweed Rule Coverage

Phones with at least one tajweed annotation: 2637/6843 (38.5%)

| Rule | Occurrences |
|------|-------------|
| emphasis_blocking_by_front_vowel | 1522 |
| cross_word_emphasis_continuation | 1522 |
| madd_tabii | 458 |
| vowel_backing_after_emphatic_short | 123 |
| madd_arid_lissukun | 96 |
| idhhar_shafawi | 91 |
| vowel_backing_before_emphatic_short | 79 |
| ikhfaa_light | 71 |
| ghunnah_mushaddadah_meem | 65 |
| idgham_shafawi_meem | 65 |
| ghunnah_mushaddadah_noon | 48 |
| idgham_ghunnah_noon | 48 |
| idhhar_halqi_noon | 36 |
| qalqalah_minor | 36 |
| madd_munfasil | 36 |
| vowel_backing_before_emphatic_long | 33 |
| ta_marbuta_wasl | 33 |
| qalqalah_with_shaddah | 29 |
| qalqalah_non_emphatic | 28 |
| idgham_no_ghunnah | 20 |
| qalqalah_emphatic | 19 |
| madd_muttasil | 14 |
| qalqalah_major | 11 |
| ikhfaa_heavy | 8 |
| iqlab | 6 |
| ta_marbuta_waqf | 3 |
| ikhfaa_shafawi | 3 |
| madd_lazim_kalimi | 2 |

### 6. Audio Coverage

Ratio of aligned speech span to total audio duration (lower values indicate more silence/padding).

| Surah | Audio Duration | Aligned Span | Coverage |
|-------|---------------|--------------|----------|
| 1 (Al-Faatiha) | 41.8s | 32.9s | 78.8% |
| 93 (Ad-Dhuhaa) | 59.5s | 49.9s | 83.8% |
| 97 (Al-Qadr) | 36.9s | 32.3s | 87.7% |
| 113 (Al-Falaq) | 24.5s | 21.2s | 86.5% |
| 114 (An-Naas) | 30.5s | 24.9s | 81.8% |
| 67 (Al-Mulk (1-5)) | 86.9s | 80.9s | 93.1% |
| 56 (Al-Waaqia (1-5)) | 21.5s | 18.1s | 83.9% |
| 36 (Ya-Sin) | 866.1s | 791.0s | 91.3% |

## Errors & Warnings

- Surah 36: Merge error ayah 1: Invalid text: Text lacks required diacritics for Qur'anic processing

## Appendix: IPA ↔ MFA Phone Mapping

| IPA | MFA | Arabic Letter |
|-----|-----|---------------|
| aː | al | long a (ا) |
| dʒ | j |  |
| dˤ | D | ض |
| iː | il | long i (ي) |
| sˤ | S | ص |
| tˤ | T | ط |
| uː | ul | long u (و) |
| ð | z | ذ |
| ðˤ | Z |  |
| ħ | H | ح |
| ɣ | G | غ |
| ʃ | C |  |
| ʔ | Q | ء (hamza) |
| ʕ | Hq | ع |
| θ | s |  |
