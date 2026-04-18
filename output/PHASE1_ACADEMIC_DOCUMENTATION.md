# Phase 1 Academic Documentation: Symbolic Layer
## Qur'anic Recitation Assessment System — Ḥafṣ ʿan ʿĀṣim Riwāyah

**Phase:** Phase 1 — Symbolic Layer
**Status:** Complete (100% rule verification, 24/24 rules)
**Date:** 2026-02-12
**Riwāyah:** Ḥafṣ ʿan ʿĀṣim

---

## Table of Contents

1. [System Architecture Diagram](#1-system-architecture-diagram)
2. [Core Algorithms Table](#2-core-algorithms-table)
3. [Tajwīd Rule Detection Table](#3-tajwīd-rule-detection-table)
4. [Pseudocode for Key Algorithms](#4-pseudocode-for-key-algorithms)
5. [Code Snippets (Actual Python)](#5-code-snippets-actual-python)
6. [Data Structures (Pydantic Models)](#6-data-structures-pydantic-models)

---

## 1. System Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    QUR'ANIC RECITATION ASSESSMENT SYSTEM                     ║
║                         Phase 1: Symbolic Layer                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

INPUT: Qur'anic Arabic Text (with full diacritics / tashkīl)
       Example: "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"

         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: TEXT NORMALIZATION (QuranTextProcessor)            │
│                                                             │
│  • Unicode normalization (NFC/NFD)                          │
│  • Whitespace & encoding standardization                    │
│  • Diacritic validation (require full tashkīl)              │
│  • Word segmentation                                        │
│                                                             │
│  Input:  Raw Unicode string                                 │
│  Output: Normalized string, word list                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: PHONEMIZATION / G2P CONVERSION (QuranPhonemizer)   │
│                                                             │
│  For each word → for each letter:                           │
│    • Extract diacritics (fatha/damma/kasra/sukoon/shaddah)  │
│    • Apply letter-specific rules:                           │
│        ─ Hamza forms (أ إ ء ؤ ئ)  → [ʔ] + vowel           │
│        ─ Alif + fatha-before       → [aː] (long aa)        │
│        ─ Waaw + damma-before       → [uː] (long uu)        │
│        ─ Yaa + kasra-before        → [iː] (long ii)        │
│        ─ Tāʾ marbūṭa (ة)          → [t] (context default) │
│        ─ Shaddah                   → duplicate consonant    │
│        ─ Tanween (ً ٍ ٌ)           → vowel + [n]            │
│    • Mark word boundaries                                   │
│                                                             │
│  Input:  Normalized Arabic text                             │
│  Output: PhonemeSequence (38-phoneme IPA inventory)         │
│                                                             │
│  Phoneme inventory (38 total):                              │
│    Consonants: b d dʒ f ɣ h ħ j k l m n q r s sˤ ʃ t tˤ  │
│                θ ð w x z zˤ ʔ ʕ                            │
│    Vowels:     a i u aː iː uː                               │
│    Other:      n (tanween noon)                             │
└──────────────────────────────┬──────────────────────────────┘
                               │  PhonemeSequence
                               ▼  [word_boundaries, verse_boundaries]
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: TAJWĪD RULE ENGINE (TajweedEngine)                 │
│                                                             │
│  Load rules (YAML) → Sort by priority (descending)          │
│                                                             │
│  For each rule (priority order):                            │
│    Scan phoneme sequence left→right:                        │
│      1. Match target phoneme pattern                        │
│      2. Check context conditions:                           │
│           ─ Position (word-start/end, verse-end)            │
│           ─ Following phoneme (pattern matching)            │
│           ─ Preceding phoneme (pattern matching)            │
│           ─ Structural (has_sukoon, has_shaddah, etc.)      │
│           ─ Cross-word (hamza in next word, etc.)           │
│      3. If matched → apply action:                          │
│           REPLACE    : swap phoneme(s)                      │
│           DELETE     : remove phoneme (full assimilation)   │
│           MODIFY_FEATURES: extend duration (madd)           │
│           INSERT     : add vowel (madd silah)               │
│           KEEP_ORIGINAL: mark but don't change              │
│      4. Record RuleApplication                              │
│                                                             │
│  Rule categories (24 rules total):                          │
│    • Noon/Meem Sākinah  (11 rules, priority 90–105)         │
│    • Madd/Prolongation  ( 6 rules, priority 50–88)          │
│    • Qalqalah           ( 5 rules, priority 70–75)          │
│    • Pronunciation      ( 2 rules, priority 94–95)          │
│                                                             │
│  Input:  PhonemeSequence                                    │
│  Output: AnnotatedPhonemeSequence + RuleApplications[]      │
└──────────────────────────────┬──────────────────────────────┘
                               │  AnnotatedPhonemeSequence
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: ACOUSTIC FEATURE GENERATION (AcousticFeatureGen)   │
│                                                             │
│  For each phoneme in annotated sequence:                    │
│    • Duration: base_ms × tajweed_multiplier × position_mult  │
│        Short vowel: ~100ms, Long vowel: ~200ms              │
│        Madd ṭabīʿī:     200ms  (2 counts)                  │
│        Madd muttaṣil:   450ms  (4–5 counts)                 │
│        Madd munfaṣil:   350ms  (2–5 counts)                 │
│        Madd lāzim:      1200ms (6 counts)                   │
│        Madd ʿāriḍ:      200ms  (2/4/6 counts)              │
│    • Pitch (F0): baseline (male:120Hz) ± emphatic/contour   │
│    • Formants (F1/F2/F3): vowel-specific ± emphatic shift   │
│    • Nasalization: ghunnah rules → intensity + duration     │
│                                                             │
│  Input:  AnnotatedPhonemeSequence                           │
│  Output: AcousticFeatures (per-phoneme feature vectors)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
OUTPUT: SymbolicOutput
  • original_text       — input Arabic text
  • normalized_text     — after Unicode normalization
  • phoneme_sequence    — IPA phoneme list with boundaries
  • annotated_sequence  — phonemes + applied rules
  • acoustic_features   — expected duration/pitch/formants/
                          nasalization per phoneme

═══════════════════════════════════════════════════════════════

FUTURE PHASES:

  Phase 2: ALIGNMENT LAYER
  ┌────────────────────────┐
  │ Montreal Forced Aligner│ ← Audio WAV input
  │ Phoneme-level timing   │
  │ Time synchronization   │
  └────────────┬───────────┘
               │
  Phase 2: ACOUSTIC VERIFICATION
  ┌────────────────────────┐
  │ Duration verification  │
  │ Nasalization detection │
  │ Formant analysis       │
  │ Error classification   │
  └────────────────────────┘

  Phase 3: ADVANCED WAQ F
  ┌────────────────────────┐
  │ Mid-verse pause detect │
  │ Dynamic rule variants  │
  │ Tanween dropping       │
  └────────────────────────┘
```

---

## 2. Core Algorithms Table

| Algorithm Name | Purpose | Input | Output | Time Complexity | Implementation File |
|---|---|---|---|---|---|
| **Text Normalization** | Unicode standardization, diacritic validation, word segmentation | Raw Arabic Unicode string | Normalized string + word list | O(n) where n = text length | `src/symbolic_layer/text_processor.py` |
| **G2P Phonemization** | Grapheme-to-phoneme conversion with diacritic-driven rules | Normalized Arabic text (with diacritics) | `PhonemeSequence` (IPA symbols + word boundaries) | O(n·d) where d = avg diacritics per letter | `src/symbolic_layer/phonemizer.py` |
| **Hamza Disambiguation** | Distinguish 5 hamza forms (أ إ ء ؤ ئ) from regular alif | Letter + Unicode codepoint | IPA `ʔ` phoneme + following vowel | O(1) per letter | `src/symbolic_layer/phonemizer.py` — `_convert_letter()` |
| **Long Vowel Construction** | Detect waaw/yaa as long-vowel markers vs. consonants | Current letter + previous vowel diacritic | `aː` / `iː` / `uː` or consonant `w`/`j` | O(1) per letter | `src/symbolic_layer/phonemizer.py` — `_handle_waaw_yaa()` |
| **Tāʾ Marbūṭa Detection** | Identify ة in phoneme stream for context-sensitive pronunciation | Phoneme stream + position | `is_ta_marbuta` flag + waqf/waṣl context | O(1) per phoneme | `src/symbolic_layer/tajweed_engine.py` — `_build_context()` |
| **Context Building** | Build per-position context dict for rule matching | Phoneme list + position + boundaries | Context dictionary (20+ boolean/value keys) | O(1) per phoneme | `src/symbolic_layer/tajweed_engine.py` — `_build_context()` |
| **Pattern Matching** | Match phoneme against target pattern (exact / set / negated set) | Phoneme symbol + pattern string | Boolean match | O(k) where k = pattern set size | `src/symbolic_layer/tajweed_engine.py` — `_matches_pattern()` |
| **Rule Application (Engine)** | Apply all 24+ Tajwīd rules to phoneme sequence in priority order | `PhonemeSequence` + sorted rules | `AnnotatedPhonemeSequence` | O(R·n) where R = rules, n = phonemes | `src/symbolic_layer/tajweed_engine.py` — `apply_rules()` |
| **Cross-Word Hamza Detection** | Detect hamza at start of following word for Madd Munfaṣil | Long vowel phoneme + word boundaries | `hamza_follows_in_next_word` boolean | O(1) per long vowel | `src/symbolic_layer/tajweed_engine.py` — `_build_context()` |
| **Geminate Detection** | Detect shaddah (doubled consonant) from consecutive identical phonemes | Phoneme + next phoneme | `has_shaddah` boolean | O(1) | `src/symbolic_layer/tajweed_engine.py` — `_build_context()` |
| **Acoustic Duration Calculation** | Compute expected duration in ms based on phoneme type + Tajwīd modifications | Phoneme + rule applications + context | `Duration(expected_ms, min, max, confidence)` | O(R) where R = rules at position | `src/symbolic_layer/acoustic_features.py` — `_calculate_duration()` |
| **Ghunnah Detection** | Generate nasalization parameters from Tajwīd rule acoustic expectations | Rule application list | `Nasalization(intensity, duration_counts, nasal_formant)` | O(R) | `src/symbolic_layer/acoustic_features.py` — `_calculate_nasalization()` |
| **Formant Estimation** | Predict F1/F2/F3 for vowels with emphatic context adjustment | Phoneme + preceding/following consonants | `Formants(f1, f2, f3, ranges)` | O(1) | `src/symbolic_layer/acoustic_features.py` — `_calculate_formants()` |

---

## 3. Tajwīd Rule Detection Table

### Category A: Noon/Meem Sākinah (نون و ميم ساكنة) — 11 Rules

| # | Rule Name (English) | Arabic Name | IPA Target | Key Detection Condition | Following Context | Acoustic Output | Priority | YAML File |
|---|---|---|---|---|---|---|---|---|
| 1 | Ghunnah Mushaddadah (Noon) | غنة مشددة | `n` | `has_shaddah=True` (n+n geminate) | — | Nasalization 2 counts, ~200ms | 105 | `noon_meem_rules.yaml` |
| 2 | Ghunnah Mushaddadah (Meem) | غنة مشددة | `m` | `has_shaddah=True` (m+m geminate) | — | Nasalization 2 counts, ~200ms | 105 | `noon_meem_rules.yaml` |
| 3 | Iẓhār Ḥalqī | إظهار حلقي | `n` | `has_sukoon=True` | `[ʔ h ʕ ħ ɣ x]` (throat letters) | No nasalization; clear /n/ | 100 | `noon_meem_rules.yaml` |
| 4 | Idghām with Ghunnah | إدغام بغنة | `n` | `has_sukoon=True` | `[j w n m]` (yaa/waaw/noon/meem) | REPLACE→deleted, nasalization 2 counts | 95 | `noon_meem_rules.yaml` |
| 5 | Idghām without Ghunnah | إدغام بغير غنة | `n` | `has_sukoon=True` | `[l r]` (lam/raa) | DELETE phoneme (full assimilation) | 95 | `noon_meem_rules.yaml` |
| 6 | Iqlāb | إقلاب | `n` | `has_sukoon=True` | `b` | REPLACE: `n` → `m` + nasalization | 98 | `noon_meem_rules.yaml` |
| 7 | Ikhfāʾ (Light) | إخفاء (خفيف) | `n` | `has_sukoon=True` | 15 ikhfāʾ letters (non-emphatic) | Partial nasalization, partial concealment | 90 | `noon_meem_rules.yaml` |
| 8 | Ikhfāʾ (Heavy) | إخفاء (ثقيل) | `n` | `has_sukoon=True` | `[sˤ dˤ tˤ ðˤ]` (emphatic) | Partial nasalization, emphatic coloring | 92 | `noon_meem_rules.yaml` |
| 9 | Iẓhār Shafawī | إظهار شفوي | `m` | `has_sukoon=True` | `![m b]` (NOT meem or baa) | No nasalization; clear /m/ | 100 | `noon_meem_rules.yaml` |
| 10 | Idghām Shafawī (Meem) | إدغام شفوي | `m` | `has_shaddah=True` (m+m) | `m` | Merge into single prolonged /m/ | 95 | `noon_meem_rules.yaml` |
| 11 | Ikhfāʾ Shafawī | إخفاء شفوي | `m` | `has_sukoon=True` | `b` | Partial concealment of /m/ before /b/ | 93 | `noon_meem_rules.yaml` |

### Category B: Madd / Prolongation (مد) — 6 Rules

| # | Rule Name (English) | Arabic Name | IPA Target | Key Detection Condition | Duration | Prolongation Counts | Priority | YAML File |
|---|---|---|---|---|---|---|---|---|
| 12 | Madd Ṭabīʿī (Natural) | مد طبيعي | `[aː iː uː]` | `is_long_vowel=True`, `no_sukoon_following=True`, `no_hamza_following=True` | 200ms | 2 counts | 50 | `madd_rules.yaml` |
| 13 | Madd Muttaṣil (Connected) | مد متصل | `[aː iː uː]` | `is_long_vowel=True`, `hamza_follows=True` (same word) | 450ms | 4–5 counts | 80 | `madd_rules.yaml` |
| 14 | Madd Munfaṣil (Disconnected) | مد منفصل | `[aː iː uː]` | `is_long_vowel=True`, `hamza_follows_in_next_word=True`, `word_boundary_between=True` | 350ms | 2–5 counts | 75 | `madd_rules.yaml` |
| 15 | Madd Lāzim Kalimī (Obligatory) | مد لازم كلمي | `[aː iː uː]` | `is_long_vowel=True`, `following_has_shaddah=True` | 1200ms | 6 counts | 88 | `madd_rules.yaml` |
| 16 | Madd ʿĀriḍ Lissukūn (Accidental) | مد عارض للسكون | `[aː iː uː]` | `is_long_vowel=True`, `follows_sukoon=True`, `at_verse_end_or_pause=True` | 200–600ms | 2/4/6 counts | 60 | `madd_rules.yaml` |
| 17 | Madd Ṣilah Kubrā (Major Connection) | مد صلة كبرى | `h` (pronoun hāʾ) | `is_pronoun_haa=True`, `hamza_follows=True` (next word) | 450ms | 4–5 counts | 70 | `madd_rules.yaml` |

### Category C: Qalqalah / Echo (قلقلة) — 5 Rules

| # | Rule Name (English) | Arabic Name | IPA Target | Key Detection Condition | Echo Strength | Priority | YAML File |
|---|---|---|---|---|---|---|---|
| 18 | Qalqalah Minor | قلقلة صغرى | `[q tˤ b dʒ d]` | `has_sukoon=True`, `position_mid_word=True`, `not_at_word_end=True` | Weak (burst: 30ms, strength 0.6) | 70 | `qalqalah_rules.yaml` |
| 19 | Qalqalah Major | قلقلة كبرى | `[q tˤ b dʒ d]` | `has_sukoon=True`, `position_word_end_or_verse_end=True` | Strong (burst: 60ms, strength 1.0) | 75 | `qalqalah_rules.yaml` |
| 20 | Qalqalah with Shaddah | قلقلة مع الشدة | `[q tˤ b dʒ d]` | `has_shaddah=True` (first of geminate pair) | First component only | 72 | `qalqalah_rules.yaml` |
| 21 | Qalqalah Emphatic | قلقلة مفخمة | `[q tˤ b dʒ d]` | `has_sukoon=True`, `near_emphatic_letter=True` | Heavy quality, F2 lowered −150Hz | 73 | `qalqalah_rules.yaml` |
| 22 | Qalqalah Non-Emphatic | قلقلة مرققة | `[b dʒ d]` | `has_sukoon=True`, `near_light_letter=True` | Light quality | 73 | `qalqalah_rules.yaml` |

### Category D: Pronunciation (نطق) — 2 Rules

| # | Rule Name (English) | Arabic Name | IPA Target | Key Detection Condition | Action | Duration | Priority | YAML File |
|---|---|---|---|---|---|---|---|---|
| 23 | Tāʾ Marbūṭa Waqf | تاء مربوطة - وقف | `t` | `is_ta_marbuta=True`, `at_verse_end_or_pause=True` | REPLACE: `t` → `h` | 80ms | 95 | `pronunciation_rules.yaml` |
| 24 | Tāʾ Marbūṭa Waṣl | تاء مربوطة - وصل | `t` | `is_ta_marbuta=True`, `not_at_verse_end=True` | KEEP_ORIGINAL: keep `t` | 70ms | 94 | `pronunciation_rules.yaml` |

---

## 4. Pseudocode for Key Algorithms

### 4.1 Text Normalization Pipeline

```
ALGORITHM TextNormalization(raw_text):
  INPUT:  raw_text  — raw Unicode Arabic string
  OUTPUT: normalized_text, word_list

  1. Apply Unicode NFC normalization
       (combines combining characters, standardizes hamza forms)

  2. Remove zero-width non-joiners (U+200C) and similar invisible chars
       EXCEPT Qur'anic marks (U+06D6..U+06FF)

  3. Validate encoding:
       IF text contains non-Arabic non-diacritic characters THEN
           raise ValidationError("Non-Arabic characters found")

  4. Validate diacritics:
       FOR each Arabic letter in text:
           IF letter has no following diacritic THEN
               raise ValidationError("Missing diacritic on letter")

  5. Segment into words:
       word_list ← split(text, delimiter=SPACE | ARABIC_TATWEEL)
       FILTER empty strings from word_list

  6. RETURN normalized_text, word_list
```

### 4.2 Phonemization (G2P Conversion)

```
ALGORITHM Phonemize(normalized_text):
  INPUT:  normalized_text — Unicode Arabic with full tashkīl
  OUTPUT: PhonemeSequence(phonemes[], word_boundaries[], original_text)

  word_list ← segment_by_word(normalized_text)
  all_phonemes ← []
  word_boundaries ← []

  FOR word_idx, word IN enumerate(word_list):
      IF word_idx > 0 THEN
          word_boundaries.append(|all_phonemes|)   // mark boundary

      letter_list ← remove_diacritics(word)         // Arabic letters only

      FOR position, letter IN enumerate(letter_list):
          diacritics    ← get_diacritics(word, position)
          vowel         ← get_vowel_type(diacritics)    // FATHA/KASRA/DAMMA/TANWEEN*
          has_sukoon    ← SUKOON ∈ diacritics
          has_shaddah   ← SHADDAH ∈ diacritics
          has_dagger_alif ← DAGGER_ALIF ∈ diacritics
          prev_letter   ← letter_list[position-1]   // or None
          prev_vowel    ← vowel of prev_letter

          phonemes ← convert_letter(letter, vowel, has_sukoon, has_shaddah,
                                    prev_letter, prev_vowel, has_dagger_alif)

          all_phonemes.extend(phonemes)

      ENDFOR
  ENDFOR

  RETURN PhonemeSequence(all_phonemes, word_boundaries, normalized_text)


FUNCTION convert_letter(letter, vowel, has_sukoon, has_shaddah,
                         prev_letter, prev_vowel, has_dagger_alif):
  // Hamza forms → /ʔ/ + vowel
  IF letter IN {ء, أ, إ, ؤ, ئ} THEN
      RETURN [ʔ, vowel_phoneme(vowel)]

  // Alif → long /aː/ when previous had fatha
  IF letter = ا AND prev_vowel = FATHA THEN
      RETURN [aː]

  // Waaw → /uː/ when previous had damma; else consonant /w/
  IF letter = و THEN
      IF prev_vowel = DAMMA THEN RETURN [uː]
      ELSE IF vowel ≠ None THEN RETURN [w, vowel_phoneme(vowel)]
      ELSE RETURN [w]

  // Yaa → /iː/ when previous had kasra; else consonant /j/
  IF letter = ي THEN
      IF prev_vowel = KASRA THEN RETURN [iː]
      ELSE IF vowel ≠ None THEN RETURN [j, vowel_phoneme(vowel)]
      ELSE RETURN [j]

  // Tāʾ Marbūṭa → default /t/ (engine will handle waqf → /h/)
  IF letter = ة THEN
      RETURN [t, vowel_phoneme(vowel)]

  // Dagger alif → append long /aː/
  IF has_dagger_alif THEN
      base ← [consonant_map[letter]]
      RETURN base ++ [aː]

  // Regular consonant
  phoneme ← consonant_map[letter]
  result ← []
  IF has_shaddah THEN result.append(phoneme)   // gemination: add twice
  result.append(phoneme)
  IF vowel = TANWEEN_* THEN
      result.extend([vowel_short, n])           // tanween = vowel + noon
  ELSE IF vowel AND NOT has_sukoon THEN
      result.append(vowel_phoneme(vowel))
  RETURN result
```

### 4.3 Tajwīd Rule Detection Engine

```
ALGORITHM ApplyTajweedRules(phoneme_sequence):
  INPUT:  phoneme_sequence — PhonemeSequence with word/verse boundaries
  OUTPUT: AnnotatedPhonemeSequence with RuleApplications[]

  // Load and sort rules by priority (descending)
  rules ← load_rules_from_yaml()
  sort(rules, key=priority, order=DESCENDING)

  current_phonemes ← copy(phoneme_sequence.phonemes)
  applications ← []

  FOR rule IN rules:
      i ← 0
      WHILE i < |current_phonemes|:
          ctx ← build_context(current_phonemes, i,
                               word_boundaries, verse_boundaries)

          IF matches(rule, current_phonemes[i], ctx) THEN
              app ← apply_action(rule, current_phonemes, i, ctx)

              IF app ≠ None THEN
                  applications.append(app)

                  // Replace phonemes in sequence
                  current_phonemes[app.start : app.end+1] ← app.modified_phonemes

                  i ← app.start + |app.modified_phonemes|
                  CONTINUE

          i ← i + 1
      ENDWHILE
  ENDFOR

  RETURN AnnotatedPhonemeSequence(current_phonemes, applications)


FUNCTION build_context(phonemes, i, word_boundaries, verse_boundaries):
  ctx ← {}

  is_word_end    ← (i+1) ∈ word_boundaries OR (i+1) ≥ |phonemes|
  is_verse_end   ← (i+1) ∈ verse_boundaries OR
                   (|verse_boundaries|=0 AND (i+1) ≥ |phonemes|)

  ctx.position_mid_word             ← NOT word_start AND NOT is_word_end
  ctx.position_word_end_or_verse_end← is_word_end OR is_verse_end
  ctx.at_verse_end_or_pause         ← is_verse_end
  ctx.not_at_verse_end              ← NOT is_verse_end

  p ← phonemes[i]
  IF i+1 < |phonemes| THEN
      next ← phonemes[i+1]
      ctx.has_sukoon      ← NOT next.is_vowel()
      ctx.has_shaddah     ← (p.symbol = next.symbol)   // geminate detection
      ctx.is_geminate     ← ctx.has_shaddah
      ctx.following_is_baa← next.symbol = 'b'
      ctx.following_is_throat_letter ← next.symbol ∈ {ʔ,h,ʕ,ħ,ɣ,x}
      ctx.hamza_follows   ← next.symbol = 'ʔ'

  IF p.is_long() THEN
      // Cross-word hamza for Madd Munfasil
      IF (i+1) ∈ word_boundaries AND i+1 < |phonemes| THEN
          ctx.hamza_follows_in_next_word ← phonemes[i+1].symbol = 'ʔ'
          ctx.word_boundary_between ← True
      // Shaddah after long vowel for Madd Lazim
      IF i+1 < |phonemes| AND i+2 < |phonemes| THEN
          ctx.following_has_shaddah ← phonemes[i+1].symbol = phonemes[i+2].symbol
      // Pausal form detection for Madd Arid
      IF i+1 < |phonemes| AND phonemes[i+1].is_consonant() THEN
          IF (i+2) ≥ (|phonemes| - 1) THEN
              ctx.follows_sukoon      ← True
              ctx.at_verse_end_or_pause ← True

  // Pronoun hāʾ for Madd Silah Kubra
  IF p.symbol = 'h' AND phonemes[i+1].symbol ∈ {i,u} THEN
      IF (i+2) ∈ word_boundaries AND phonemes[i+2].symbol = 'ʔ' THEN
          ctx.is_pronoun_haa ← True
          ctx.hamza_follows  ← True

  // Tāʾ Marbūṭa detection
  IF p.symbol = 't' THEN
      ctx.is_ta_marbuta ← detect_ta_marbuta(phonemes, i, word_boundaries)

  RETURN ctx


FUNCTION matches(rule, phoneme, ctx):
  // 1. Target phoneme pattern
  IF NOT rule.pattern.matches_target(phoneme.symbol) THEN RETURN False

  // 2. All conditions must hold
  FOR (key, expected_value) IN rule.pattern.conditions:
      IF key NOT IN ctx THEN CONTINUE   // unknown condition → skip
      IF ctx[key] ≠ expected_value THEN RETURN False

  // 3. Following context
  IF rule.pattern.following_context ≠ None THEN
      IF NOT matches_pattern(next_phoneme.symbol, rule.pattern.following_context) THEN
          RETURN False

  // 4. Preceding context
  IF rule.pattern.preceding_context ≠ None THEN
      IF NOT matches_pattern(prev_phoneme.symbol, rule.pattern.preceding_context) THEN
          RETURN False

  RETURN True


FUNCTION matches_pattern(symbol, pattern):
  IF pattern starts with "!["  THEN  // Negation: "![m b]" = NOT m or b
      invalid ← parse_set(pattern)
      RETURN symbol NOT IN invalid
  ELSE IF pattern starts with "[" THEN  // Set: "[l r]" = l or r
      valid ← parse_set(pattern)
      RETURN symbol IN valid
  ELSE                                  // Exact match
      RETURN symbol = pattern
```

### 4.4 Acoustic Feature Generation

```
ALGORITHM GenerateAcousticFeatures(annotated_sequence):
  INPUT:  annotated_sequence — AnnotatedPhonemeSequence
  OUTPUT: AcousticFeatures (per-phoneme feature vectors)

  phoneme_features ← []

  FOR i, phoneme IN enumerate(annotated_sequence.phonemes):
      rules_here ← [app FOR app IN applications IF app.start ≤ i ≤ app.end]
      ctx ← build_acoustic_context(annotated_sequence, i)

      // Duration
      IF phoneme.is_vowel() THEN
          base_ms ← 200 IF phoneme.is_long() ELSE 100
      ELSE
          base_ms ← 160 IF phoneme.is_geminate() ELSE 80

      multiplier ← 1.0
      FOR rule IN rules_here:
          IF rule.acoustic_expectations.duration_ms THEN
              base_ms ← rule.acoustic_expectations.duration_ms
          multiplier ← multiplier × rule.action.duration_multiplier

      IF ctx.is_word_final  THEN multiplier ← multiplier × 1.3
      IF ctx.is_verse_final THEN multiplier ← multiplier × 1.5

      duration ← Duration(expected_ms = base_ms × multiplier,
                           tolerance    = 25–100ms)

      // Pitch
      f0 ← baseline_f0[speaker_type]   // male:120, female:220, child:280
      IF phoneme.is_emphatic()  THEN f0 ← f0 × 0.9
      IF ctx.is_verse_final THEN contour ← FALLING (Δf0 = −50Hz)

      // Formants (vowels only)
      IF phoneme.is_vowel() THEN
          f1, f2, f3 ← base_formants[phoneme.symbol]
          IF emphatic_context THEN f2 ← f2 − 200

      // Nasalization (ghunnah)
      has_ghunnah ← any(rule.acoustic.ghunnah_present FOR rule IN rules_here)
      IF has_ghunnah THEN
          nasalization ← Nasalization(
              intensity      = 0.8,
              duration_counts= rule.acoustic.ghunnah_duration_counts,
              nasal_formant  = 300Hz)

      phoneme_features.append(PhonemeAcousticFeatures(
          duration, pitch, formants, nasalization))
  ENDFOR

  RETURN AcousticFeatures(phoneme_features, total_duration_ms, sequence_length)
```

---

## 5. Code Snippets (Actual Python)

### 5.1 Noon/Meem Rule — Iqlāb (إقلاب): Noon Before Baa

**YAML Rule Definition** (`data/tajweed_rules/noon_meem_rules.yaml`):
```yaml
- name: iqlab
  category: noon_meem_sakinah
  priority: 98
  description: Noon sākinah/tanween before baa converts to meem with ghunnah
  arabic_name: إقلاب
  pattern:
    target: n
    conditions:
      has_sukoon: true
    following_context: b
  action:
    type: replace
    replacement: [m]
    notes: Noon converts to meem before baa
  acoustic_expectations:
    ghunnah_present: true
    ghunnah_duration_counts: 2
    nasalization_strength: 0.8
    duration_ms: 200
```

**Engine: Pattern Matching** (`src/symbolic_layer/tajweed_engine.py`):
```python
def _check_rule_match(
    self,
    rule: TajweedRule,
    phonemes: List[Phoneme],
    index: int,
    context: Dict[str, Any]
) -> bool:
    """Check if a rule matches at the given position."""
    if index >= len(phonemes):
        return False

    target_phoneme = phonemes[index]

    # 1. Check target phoneme pattern (e.g., 'n' for iqlab)
    if not rule.pattern.matches_target(target_phoneme.symbol):
        return False

    # 2. Check structural conditions (e.g., has_sukoon=True)
    for condition_key, condition_value in rule.pattern.conditions.items():
        if condition_key not in context:
            continue  # unknown condition → skip (permissive matching)
        if context[condition_key] != condition_value:
            return False

    # 3. Check following context (e.g., following 'b' for iqlab)
    if rule.pattern.following_context:
        if index + 1 >= len(phonemes):
            return False
        next_phoneme = phonemes[index + 1]
        if not self._matches_pattern(next_phoneme.symbol,
                                     rule.pattern.following_context):
            return False

    return True


def _matches_pattern(self, symbol: str, pattern: str) -> bool:
    """Check if a symbol matches a pattern (supports sets and negation)."""
    if pattern.startswith('![') and pattern.endswith(']'):
        # Negation pattern: "![m b]" → NOT m or b (used in iẓhār shafawī)
        invalid_symbols = pattern.strip('![]').split()
        return symbol not in invalid_symbols
    elif pattern.startswith('[') and pattern.endswith(']'):
        # Set pattern: "[l r]" → l or r (used in idghām without ghunnah)
        valid_symbols = pattern.strip('[]').split()
        return symbol in valid_symbols
    else:
        # Exact match: "b" → only 'b' (used in iqlab, ikhfāʾ shafawī)
        return symbol == pattern
```

**Usage example:**
```python
from src.symbolic_layer.pipeline import SymbolicLayerPipeline

pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
output = pipeline.process_text("مِن بَعْدِ مِيثَٰقِهِۦ")  # Surah 2:27

for app in output.annotated_sequence.rule_applications:
    if app.rule.name == 'iqlab':
        orig = [p.symbol for p in app.original_phonemes]  # ['n']
        mod  = [p.symbol for p in app.modified_phonemes]  # ['m']
        print(f"Iqlāb at pos {app.start_index}: {orig} → {mod}")
        # Output: "Iqlāb at pos 2: ['n'] → ['m']"
```

---

### 5.2 Madd Rule — Madd Muttaṣil (مد متصل): Long Vowel Before Hamza in Same Word

**YAML Rule Definition** (`data/tajweed_rules/madd_rules.yaml`):
```yaml
- name: madd_muttasil
  category: madd
  priority: 80
  description: Connected prolongation - long vowel followed by hamza in same word (4-5 counts)
  arabic_name: مد متصل
  pattern:
    target: '[aː iː uː]'
    conditions:
      is_long_vowel: true
      hamza_follows: true
      word_boundary_between: false
  action:
    type: modify_features
    duration_multiplier: 2.25    # 4.5 counts (2.25 × 200ms base = 450ms)
  acoustic_expectations:
    duration_ms: 450
    duration_counts: 4.5
    duration_tolerance: 100
    prolonged: true
```

**Context building for Madd rules** (`src/symbolic_layer/tajweed_engine.py`):
```python
# In _build_context(), for long vowel phonemes:
if phoneme.is_long():
    is_at_word_end = (index + 1) in word_boundaries

    if is_at_word_end and index + 1 < len(phonemes):
        # Long vowel at word end → check for cross-word hamza (Madd Munfaṣil)
        next_phoneme = phonemes[index + 1]
        context['hamza_follows_in_next_word'] = next_phoneme.symbol == 'ʔ'
        context['word_boundary_between'] = True
    else:
        # Not at word end → check for same-word hamza (Madd Muttaṣil)
        context['hamza_follows_in_next_word'] = False
        context['word_boundary_between'] = False

    # Detect Madd Lāzim Kalimī: long vowel followed by geminate
    if index + 1 < len(phonemes):
        next_p = phonemes[index + 1]
        if next_p.is_consonant() and index + 2 < len(phonemes):
            phoneme_after = phonemes[index + 2]
            # Shaddah in phoneme stream = two consecutive identical consonants
            context['following_has_shaddah'] = (next_p.symbol == phoneme_after.symbol)
        else:
            context['following_has_shaddah'] = False
```

**Acoustic feature output:**
```python
# Duration calculation for Madd Muttaṣil
# Rule acoustic_expectations.duration_ms = 450ms overrides base
# base_ms = 200ms (long vowel default)
# duration_multiplier = 2.25 → 200 × 2.25 = 450ms

output = pipeline.process_text("أَوْ كَصَيِّبٍ مِّنَ ٱلسَّمَآءِ")  # 2:19

features = output.acoustic_features
for i, feat in enumerate(features.phoneme_features):
    phoneme = output.annotated_sequence.phonemes[i]
    if phoneme.is_long():
        print(f"Pos {i}: /{phoneme.symbol}/ duration={feat.duration.expected_ms:.0f}ms")
# Example output for 'aː' in ٱلسَّمَآءِ:
# Pos 9: /aː/ duration=450ms  (Madd Muttaṣil applied)
```

---

### 5.3 Qalqalah Detection — Rule Application for Mid-Word and Word-End

**YAML Rule Definitions** (`data/tajweed_rules/qalqalah_rules.yaml`):
```yaml
# Minor Qalqalah (mid-word)
- name: qalqalah_minor
  category: qalqalah
  priority: 70
  pattern:
    target: '[q tˤ b dʒ d]'
    conditions:
      has_sukoon: true
      position_mid_word: true
      not_at_word_end: true
  action:
    type: modify_features
    modifier: Q

# Major Qalqalah (word/verse end)
- name: qalqalah_major
  category: qalqalah
  priority: 75
  pattern:
    target: '[q tˤ b dʒ d]'
    conditions:
      has_sukoon: true
      position_word_end_or_verse_end: true
  action:
    type: modify_features
    modifier: QQ

# Qalqalah with Shaddah (geminate qalqalah letter)
- name: qalqalah_with_shaddah
  category: qalqalah
  priority: 72
  pattern:
    target: '[q tˤ b dʒ d]'
    conditions:
      has_shaddah: true    # Fixed: was missing in context; now aliased from is_geminate
  action:
    type: modify_features
    notes: Only the first (sākin) component exhibits qalqalah
```

**Context setup for shaddah detection** (fixed in Phase 1):
```python
# In _build_context(): geminate = shaddah in phoneme stream representation
if index + 1 < len(phonemes):
    next_phoneme = phonemes[index + 1]
    context['has_sukoon'] = not next_phoneme.is_vowel()

    # Shaddah = consecutive identical consonants (gemination)
    # e.g., تَبَّتْ → [t, a, b, b, a, t] → b at pos 2 has has_shaddah=True
    context['is_geminate'] = phoneme.symbol == next_phoneme.symbol
    context['has_shaddah'] = context['is_geminate']   # alias for rule matching
else:
    context['has_sukoon'] = True
    context['is_geminate'] = False
    context['has_shaddah'] = False
```

**Usage demonstrating all three qalqalah variants:**
```python
pipeline = SymbolicLayerPipeline(enable_raa_rules=False)

test_cases = [
    ("وَٱللَّهُ يَقْبِضُ وَيَبْسُطُ", "Minor: qaaf mid-word in يَقْبِضُ"),
    ("قَدْ جَآءَكُمْ",               "Major: daal word-end in قَدْ"),
    ("تَبَّتْ يَدَآ أَبِى لَهَبٍ",  "Shaddah: baa geminate in تَبَّتْ"),
]

for text, description in test_cases:
    output = pipeline.process_text(text)
    qalqalah_apps = [
        app for app in output.annotated_sequence.rule_applications
        if app.rule.category.value == 'qalqalah'
    ]
    print(f"\n{description}")
    for app in qalqalah_apps:
        print(f"  Rule: {app.rule.name} | Phoneme: {app.original_phonemes[0].symbol}"
              f" at pos {app.start_index}")

# Output:
# Minor: qaaf mid-word in يَقْبِضُ
#   Rule: qalqalah_minor | Phoneme: q at pos 3
#
# Major: daal word-end in قَدْ
#   Rule: qalqalah_major | Phoneme: d at pos 2
#
# Shaddah: baa geminate in تَبَّتْ
#   Rule: qalqalah_with_shaddah | Phoneme: b at pos 2
```

---

## 6. Data Structures (Pydantic Models)

### Core Phoneme Models (`src/symbolic_layer/models/phoneme.py`)

| Model | Key Fields | Purpose |
|---|---|---|
| **`PhoneticFeatures`** | `manner: ArticulationManner`, `place: ArticulationPlace`, `voicing: bool`, `emphatic: bool`, `height: VowelHeight`, `backness: VowelBackness`, `length: VowelLength`, `nasalized: bool`, `geminated: bool` | Stores articulatory/acoustic properties of a phoneme |
| **`Phoneme`** | `symbol: str` (IPA), `category: PhonemeCategory`, `features: PhoneticFeatures`, `duration_factor: float`, `arabic_letter: str`, `formants: dict` | Single phoneme with methods: `is_vowel()`, `is_consonant()`, `is_long()`, `is_emphatic()`, `is_geminate()`, `is_nasal()` |
| **`TextPosition`** | `text_index: int`, `grapheme: str`, `word_index: int` | Maps each phoneme back to its source grapheme position in the original Arabic text |
| **`PhonemeSequence`** | `phonemes: List[Phoneme]`, `positions: List[TextPosition]`, `word_boundaries: List[int]`, `verse_boundaries: List[int]`, `original_text: str` | Complete phoneme sequence for a text with boundary metadata. Methods: `get_words()`, `to_ipa_string()`, `get_context()` |
| **`PhonemeInventory`** | `consonants: List[Phoneme]`, `vowels: List[Phoneme]`, `tajweed_phonemes: List[Phoneme]` | Loaded phoneme inventory (38 phonemes total). Method: `get_by_symbol(symbol)` |

### Rule Models (`src/symbolic_layer/models/rule.py`)

| Model | Key Fields | Purpose |
|---|---|---|
| **`RulePattern`** | `target: str` (phoneme or set), `preceding_context: str`, `following_context: str`, `conditions: Dict[str, Any]` | Defines what to match: target phoneme, adjacent phoneme patterns, and context booleans. Method: `matches_target(symbol)` |
| **`RuleAction`** | `type: ActionType` (REPLACE/DELETE/MODIFY_FEATURES/INSERT/KEEP_ORIGINAL), `replacement: List[str]`, `duration_multiplier: float`, `notes: str` | Defines what to do when matched |
| **`AcousticEffect`** | `duration_ms: float`, `duration_counts: float`, `duration_tolerance: float`, `ghunnah_present: bool`, `ghunnah_duration_counts: int`, `nasalization_strength: float`, `f2_lowering_hz: float`, `f0_lowering_factor: float`, `prolonged: bool` | Expected acoustic outcome for verification in Phase 2 |
| **`VerificationCriterion`** | `feature: str`, `expected_ms: float`, `min_ms: float`, `max_ms: float`, `description: str` | Phase 2 acoustic verification thresholds per rule |
| **`TajweedRule`** | `name: str`, `category: RuleCategory`, `priority: int`, `description: str`, `arabic_name: str`, `pattern: RulePattern`, `action: RuleAction`, `acoustic_effect: AcousticEffect`, `verification_criteria: List[VerificationCriterion]`, `error_types: List[ErrorDefinition]` | Complete rule definition loaded from YAML |
| **`RuleApplication`** | `rule: TajweedRule`, `start_index: int`, `end_index: int`, `original_phonemes: List[Phoneme]`, `modified_phonemes: List[Phoneme]`, `acoustic_expectations: AcousticEffect` | Records one instance of a rule being applied at a position in a sequence |
| **`AnnotatedPhonemeSequence`** | `phonemes: List[Phoneme]`, `word_boundaries: List[int]`, `verse_boundaries: List[int]`, `original_text: str`, `rule_applications: List[RuleApplication]` | The phoneme sequence after all rules are applied, with full application history |

### Acoustic Feature Models (`src/symbolic_layer/models/features.py`)

| Model | Key Fields | Purpose |
|---|---|---|
| **`Duration`** | `expected_ms: float`, `min_acceptable_ms: float`, `max_acceptable_ms: float`, `confidence: float` | Expected phoneme duration range for acoustic verification |
| **`Pitch`** | `contour_type: PitchContour`, `expected_f0_hz: float`, `f0_start_hz: float`, `f0_end_hz: float`, `acceptable_range_hz: Tuple[float,float]`, `confidence: float` | Expected F0 contour and range |
| **`Formants`** | `f1_hz: float`, `f2_hz: float`, `f3_hz: float`, `f1_range_hz: Tuple`, `f2_range_hz: Tuple`, `f3_range_hz: Tuple`, `confidence: float` | Expected formant values and tolerances for vowel verification |
| **`Nasalization`** | `is_nasalized: bool`, `ghunnah_duration_counts: int`, `nasal_intensity: float`, `nasal_formant_hz: float`, `f1_reduction_factor: float`, `confidence: float` | Ghunnah (nasalization) expectations for applicable rules |
| **`PhonemeAcousticFeatures`** | `phoneme_index: int`, `phoneme_symbol: str`, `duration: Duration`, `pitch: Pitch`, `formants: Optional[Formants]`, `nasalization: Optional[Nasalization]`, `in_emphatic_context: bool`, `in_word_boundary: bool`, `in_verse_boundary: bool` | Complete acoustic feature vector for a single phoneme |
| **`AcousticFeatures`** | `phoneme_features: List[PhonemeAcousticFeatures]`, `total_duration_ms: float`, `sequence_length: int` | Full acoustic feature output for an entire text segment |

### Output Model (`src/symbolic_layer/models/output.py`)

| Model | Key Fields | Purpose |
|---|---|---|
| **`SymbolicOutput`** | `original_text: str`, `normalized_text: str`, `phoneme_sequence: PhonemeSequence`, `annotated_sequence: AnnotatedPhonemeSequence`, `acoustic_features: AcousticFeatures`, `surah: Optional[int]`, `ayah: Optional[int]`, `processing_timestamp: str` | Final output object from the Symbolic Layer pipeline, carrying all intermediate and final results for downstream phases |

### Enumerations (`src/symbolic_layer/models/enums.py`)

| Enum | Values | Used In |
|---|---|---|
| **`PhonemeCategory`** | `CONSONANT`, `VOWEL`, `TAJWEED` | `Phoneme.category` |
| **`RuleCategory`** | `noon_meem_sakinah`, `madd`, `qalqalah`, `general` | `TajweedRule.category` |
| **`ActionType`** | `REPLACE`, `DELETE`, `MODIFY_FEATURES`, `INSERT`, `KEEP_ORIGINAL` | `RuleAction.type` |
| **`ErrorSeverity`** | `critical`, `major`, `minor` | `ErrorDefinition.severity` |
| **`ArticulationManner`** | `stop`, `fricative`, `nasal`, `approximant`, `lateral`, `trill`, `affricate` | `PhoneticFeatures.manner` |
| **`ArticulationPlace`** | `bilabial`, `labiodental`, `dental`, `alveolar`, `postalveolar`, `palatal`, `velar`, `uvular`, `pharyngeal`, `glottal` | `PhoneticFeatures.place` |
| **`VowelLength`** | `SHORT`, `LONG` | `PhoneticFeatures.length` |
| **`PitchContour`** | `LEVEL`, `RISING`, `FALLING`, `RISE_FALL` | `Pitch.contour_type` |

---

## Summary Statistics

| Metric | Value |
|---|---|
| **Total Tajwīd rules implemented** | 24 (Phase 1 core) |
| **IPA phoneme inventory** | 38 phonemes |
| **Rule verification rate** | 100% (24/24) |
| **Test cases** | 48 (2 per rule) |
| **Rule categories** | 4 |
| **YAML rule files** | 5 (noon_meem, madd, qalqalah, emphatic_backing, pronunciation) |
| **Python source files** | ~12 (pipeline, phonemizer, engine, features, models, utils) |
| **Priority range** | 50 (madd_tabii) → 105 (ghunnah_mushaddadah) |
| **Action types** | 5 (REPLACE, DELETE, MODIFY_FEATURES, INSERT, KEEP_ORIGINAL) |
| **Context keys** | 20+ per position |
| **Speaker types** | male (F0=120Hz), female (F0=220Hz), child (F0=280Hz) |
| **Waqf support** | Verse-boundary only (mid-verse deferred to Phase 3) |
| **Rāʾ rules** | Deferred to Phase 2 |

---

*This documentation covers Phase 1 (Symbolic Layer) of the Qur'anic Recitation Assessment System.*
*Riwāyah: Ḥafṣ ʿan ʿĀṣim — the most widely recited transmission worldwide.*
