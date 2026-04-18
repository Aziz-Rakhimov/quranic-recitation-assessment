# Diagnostic Findings - Root Cause Analysis

**Date:** 2026-02-09
**Status:** ✅ Root causes identified

---

## Executive Summary

The comprehensive diagnostic revealed **THREE CRITICAL ISSUES** preventing rule detection:

1. ❌ **Long vowels mostly not created** - Only 1 out of 4 test cases produced long vowels
2. ⚠️ **Tanween inconsistently phonemized** - Sometimes produces [vowel, n], sometimes doesn't
3. ✅ **Sukoon detection works** - Has_sukoon context is correct
4. ✅ **Word boundaries work** - Cross-word detection is possible

---

## Issue 1: Long Vowel Detection 🚨 CRITICAL

### Test Results

| Text | Expected Long Vowel | Result | Status |
|------|--------------------|---------| -------|
| بِسْمِ ٱللَّهِ | [aː] in ٱللَّهِ | `['b', 'i', 's', 'm', 'i', 'l', 'l', 'l', 'a', 'h', 'i']` | ❌ No long vowels |
| ٱلرَّحْمَٰنِ | [aː] in ٱلرَّحْمَٰنِ | `['l', 'r', 'r', 'a', 'ħ', 'm', 'a', 'n', 'i']` | ❌ No long vowels |
| قُلْ هُوَ | [uː] in هُوَ | `['q', 'u', 'l', 'h', 'u', 'w', 'a']` | ❌ No long vowels |
| ٱلضَّآلِّينَ | [aː] before لّ | `['l', 'dˤ', 'dˤ', 'a', 'aː', 'l', 'l', 'i', 'j', 'n', 'a']` | ✅ **ONE long vowel!** |

### Analysis

**Success Rate:** 25% (1 out of 4 cases)

The ONE case that works: ٱلضَّآلِّينَ with آ (alif with madda ◌ٓ)
- Text: ٱلضَّآلِّينَ
- Phonemes include: `'aː'` ✅
- **This suggests:** The phonemizer recognizes آ (alif with madda) but NOT regular long vowels

**Cases that FAIL:**
1. **ٱللَّهِ** (اللَّهِ) - Has long alif ا after ل, but phonemizer outputs: `'l', 'a', 'h'` (short vowel)
2. **ٱلرَّحْمَٰنِ** - Has alif + fatha, but outputs: `'a'` (short vowel)
3. **هُوَ** - Has wāw + damma (should be [uː]), but outputs: `'h', 'u', 'w', 'a'` (short u)

### Root Cause

The phonemizer is NOT creating long vowels for:
- Alif (ا) + fatha → should be [aː]
- Yāʾ (ي) + kasra → should be [iː]
- Wāw (و) + damma → should be [uː]

**Location:** `src/symbolic_layer/phonemizer.py` - G2P rules

**Impact:** ALL 6 Madd rules fail because they require `is_long_vowel: true` condition

---

## Issue 2: Tanween Phonemization ⚠️ INCONSISTENT

### Test Results

| Text | Tanween Type | Expected | Actual Phonemes | Status |
|------|--------------|----------|-----------------|--------|
| كِتَابٌ | Damm (ٌ) | [u, n] | `['k', 'i', 't', 'a', 'aː', 'b', 'u', 'n']` | ✅ Noon at [7] |
| رَيْبَ | Fath (ً) | [a, n] | `['r', 'a', 'iː', 'b', 'a']` | ❌ **NO NOON!** |
| أَلِيمٌۢ | Damm (ٌۢ) | [u, n] | `['l', 'i', 'j', 'm', 'u', 'n', 'b', ...]` | ✅ Noon at [5] |

### Analysis

**Tanween Fath (ً) is NOT producing noon phoneme!**

- كِتَابٌ (damm) → Works ✅
- أَلِيمٌۢ (damm) → Works ✅
- رَيْبَ (fath) → FAILS ❌

### Root Cause

In `phonemizer.py`, tanween handling might be:
1. Only handling tanween damm and kasr, but not tanween fath
2. Or: Tanween fath is being handled differently
3. Or: The diacritic detection is failing for fath tanween

**Location:** `src/symbolic_layer/phonemizer.py` lines 449-476 (the tanween fix we did earlier)

**Impact:** Many noon/meem sākinah rules fail when triggered by tanween fath

---

## Issue 3: Sukoon Detection ✅ WORKING

### Test Results

| Text | Should Have Sukoon | Actual Result | Status |
|------|-------------------|---------------|--------|
| ذَٰلِكَ | دْ mid-word | Detected: `'l'` at [0] has sukoon | ⚠️ Partial |
| قَدْ | دْ at end | Detected: `'d'` at [2] has sukoon | ✅ Works |
| ٱلْكِتَٰبُ | لْ | Detected: `'l'` at [0] has sukoon | ✅ Works |
| مِنْ شَرِّ | نْ | Detected: `'n'` at [2] has sukoon | ✅ Works |

### Analysis

✅ **Sukoon detection WORKS correctly!**

The `has_sukoon` context condition is being set properly:
- Consonant without following vowel → `has_sukoon: True`
- Example: In مِنْ شَرِّ, position [2] (noon) correctly has `has_sukoon: True`

**However:** Qalqalah rules still fail because they have additional conditions that aren't met.

### Why Qalqalah Still Fails

Looking at the YAML for qalqalah_minor:
```yaml
pattern:
  target: '[q tˤ b dʒ d]'
  conditions:
    has_sukoon: true
    position_mid_word: true          # ← This condition
    not_at_word_end: true             # ← And this
    not_at_verse_end: true            # ← And this
```

The context builder does NOT set:
- `position_mid_word`
- `not_at_word_end`
- `not_at_verse_end`

**Location:** `src/symbolic_layer/tajweed_engine.py` line 231-274 (`_build_context()`)

**Fix:** Add these position-based conditions to context dictionary

---

## Issue 4: Word Boundaries ✅ WORKING

### Test Results

✅ **Word boundaries work perfectly!**

Example: مِنْ شَرِّ
```
Phonemes: ['m', 'i', 'n', 'ʃ', 'a', 'r', 'r', 'i']
Word boundaries at indices: [3]

Cross-boundary access:
[2] n → [3] ʃ (crosses word boundary)
```

The noon at position [2] CAN access the following ش at position [3], even across the word boundary.

**Rule Detection:** ikhfaa_light WAS detected at position 2! ✅

This proves:
- Word boundaries are preserved
- Cross-word rule matching works
- The rule engine can access phonemes across boundaries

---

## Summary of Findings

| Issue | Status | Impact | Priority |
|-------|--------|--------|----------|
| **Long vowel creation** | ❌ Failing 75% | All 6 Madd rules fail | 🔥 **CRITICAL** |
| **Tanween fath** | ❌ Not producing noon | Many noon rules fail | 🔥 **CRITICAL** |
| **Qalqalah position conditions** | ❌ Not set | All 5 Qalqalah rules fail | ⚠️ **HIGH** |
| **Sukoon detection** | ✅ Working | N/A | ✓ OK |
| **Word boundaries** | ✅ Working | N/A | ✓ OK |

---

## Recommended Fixes

### Fix 1: Phonemizer - Long Vowels 🔥 CRITICAL

**File:** `src/symbolic_layer/phonemizer.py`

**Issue:** Not creating long vowels for most cases

**What to check:**
1. G2P rules for long vowels:
   - ا (alif) + fatha → should create 'aː'
   - ي (yaa) + kasra → should create 'iː'
   - و (waaw) + damma → should create 'uː'

2. Currently only آ (alif with madda) works

**Expected behavior:**
- بِسْمِ ٱللَّهِ should have ['l', 'l', 'aː', 'h'] not ['l', 'l', 'a', 'h']
- هُوَ should have ['h', 'uː'] not ['h', 'u', 'w', 'a']

---

### Fix 2: Phonemizer - Tanween Fath 🔥 CRITICAL

**File:** `src/symbolic_layer/phonemizer.py` lines 449-476

**Issue:** Tanween fath (ً) not producing noon phoneme

**Current behavior:**
- رَيْبَ → `['r', 'a', 'iː', 'b', 'a']` ❌ (no noon)

**Expected behavior:**
- رَيْبَ → `['r', 'a', 'iː', 'b', 'a', 'n']` ✅ (with noon)

**Check:**
- Is tanween fath being detected?
- Is it calling `_vowel_to_phoneme()` correctly?
- Does the diacritic type match `DiacriticType.TANWEEN_FATH`?

---

### Fix 3: Rule Engine - Position Conditions ⚠️ HIGH

**File:** `src/symbolic_layer/tajweed_engine.py` lines 231-274

**Issue:** Context doesn't include position-based conditions

**Add to context:**
```python
context['position_mid_word'] = not context['is_word_start'] and not context['is_word_end']
context['not_at_word_end'] = not context['is_word_end']
context['not_at_verse_end'] = index not in verse_boundaries
context['position_word_end_or_verse_end'] = context['is_word_end'] or index in verse_boundaries
```

This will fix all 5 Qalqalah rules.

---

## Expected Improvements After Fixes

| Fix | Rules Fixed | Verification Rate Improvement |
|-----|-------------|------------------------------|
| **Long vowels** | +6 Madd rules | +27% (6/22) |
| **Tanween fath** | +4 noon rules | +18% (4/22) |
| **Position conditions** | +5 Qalqalah rules | +23% (5/22) |
| **Total** | **+15 rules** | **+68% → 72.5% total** |

With these 3 fixes, we should go from **4.5%** to **~72.5%** verification rate!

---

## Good News ✅

Several components work perfectly:
1. ✅ **Sukoon detection** - Works correctly
2. ✅ **Word boundaries** - Cross-word matching works
3. ✅ **Idhhar Halqi** - Fully working (noon before throat letters)
4. ✅ **Shaddah detection** - Partially working (noon with shaddah)
5. ✅ **Cross-word rules** - ikhfaa_light detected across word boundary

The rule engine architecture is sound - we just need to fix the phonemizer and add missing context conditions!

---

## Next Steps

1. **Fix phonemizer long vowels** (Priority 1)
   - Test: Verify all 4 test cases create long vowels
   - Expected: 25% → 100% success rate

2. **Fix tanween fath** (Priority 2)
   - Test: Verify رَيْبَ produces noon
   - Expected: 67% → 100% tanween success rate

3. **Add position conditions** (Priority 3)
   - Test: Verify qalqalah rules match
   - Expected: All 5 qalqalah rules start working

4. **Re-run comprehensive verification**
   - Target: 70%+ verification rate before expert review
   - Goal: 90%+ before production

---

**Estimated Time:** 1-2 days to implement fixes and re-verify
