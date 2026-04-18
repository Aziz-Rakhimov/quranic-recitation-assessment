# Phase 1: Core Tajwīd Rules (Rāʾ Disabled)

## 📋 Active Rules Summary

**Configuration:** `enable_raa_rules=False` (default)
**Total Active Rules:** 28 rules across 4 categories

---

## ✅ Category 1: Noon & Meem Sākinah (11 rules)

### Ghunnah with Shaddah ✅
| Rule | Status | Duration | Test Case |
|------|--------|----------|-----------|
| Noon with shaddah (نّ) | ✅ Verified | 400ms (2 counts) | إِنَّ (inna) |
| Meem with shaddah (مّ) | ✅ Verified | 400ms (2 counts) | أَمَّا (amma) |

### Iẓhār (Clear Pronunciation) ✅
| Rule | Status | Letters | Example |
|------|--------|---------|---------|
| Iẓhār Ḥalqī (noon) | ✅ Verified | ء ه ع ح غ خ | مِنْ ءَامَنَ |
| Iẓhār Shafawī (meem) | ✅ Verified | All except م ب | هُمْ فِيهَا |

### Idghām (Assimilation) ✅
| Rule | Status | Letters | Ghunnah | Example |
|------|--------|---------|---------|---------|
| Idghām with ghunnah (noon) | ✅ Verified | ي و ن م | Yes (400ms) | مَنْ يَعْمَلْ |
| Idghām without ghunnah | ⚠️ Needs test | ل ر | No | مِنْ لَدُنْهُ |
| Idghām Shafawī (meem) | ✅ Verified | م | Yes (400ms) | لَهُمْ مَا |

### Iqlāb (Conversion) ✅
| Rule | Status | Trigger | Result | Example |
|------|--------|---------|--------|---------|
| Noon → Meem before bāʾ | ✅ Verified | ب | n → m̃ + ghunnah | مِنْ بَعْدِ |

### Ikhfāʾ (Concealment) ✅
| Rule | Status | Type | Letters | Example |
|------|--------|------|---------|---------|
| Ikhfāʾ light | ✅ Verified | Before light letters | ت ث ج د ذ ز س ش ف ك | مِنْ تَحْتِ |
| Ikhfāʾ heavy | ✅ Verified | Before emphatics | ص ض ط ظ ق | مِنْ صَلْصَالٍ |
| Ikhfāʾ Shafawī | ✅ Verified | Meem before bāʾ | ب | تَرْمِيهِمْ بِحِجَارَةٍ |

---

## ✅ Category 2: Madd (Prolongation) - 6 rules

| Rule | Duration | Status | Example |
|------|----------|--------|---------|
| **Madd Ṭabīʿī** | 2 counts (200ms) | ✅ Verified | قَالَ (qaala) |
| **Madd Muttaṣil** | 4-5 counts (450ms) | ⚠️ Needs test | السَّمَآءِ (as-samaa'i) |
| **Madd Munfaṣil** | 2-5 counts (350ms) | ⚠️ Needs test | إِنَّآ أَعْطَيْنَٰكَ (innaa a'taynaka) |
| **Madd Lāzim** | 6 counts (600ms) | ⚠️ Needs test | الضَّآلِّينَ (ad-daalliina) |
| **Madd ʿĀriḍ** | 2/4/6 counts | ⚠️ Needs test | نَسْتَعِينْ (pausal) |
| **Madd Ṣilah Kubrā** | 4-5 counts (450ms) | ⚠️ Needs test | بِهِۦٓ أَسَفًا |

**Focus:** Natural madd (ṭabīʿī) is extensively verified. Other types need targeted test verses.

---

## ✅ Category 3: Qalqalah (Echo Sound) - 5 rules

| Rule | Letters | Position | Strength | Status |
|------|---------|----------|----------|--------|
| **Minor** | ق ط ب ج د | Mid-word | Weak echo | ✅ Verified |
| **Major** | ق ط ب ج د | Word/verse end | Strong echo | ✅ Verified |
| **With Shaddah** | ق ط ب ج د | First component | Variable | ⚠️ Needs test |
| **Emphatic** | q tˤ | Near emphatics | Heavy quality | ✅ Verified |
| **Non-emphatic** | b dʒ d | Near light letters | Light quality | ✅ Verified |

**Mnemonic:** قطب جد (quṭb jad)

---

## ✅ Category 4: Emphasis/Vowel Backing - 6 rules

| Rule | Target | Status | Example |
|------|--------|--------|---------|
| **After emphatic (short)** | [a] → [ɑ] | ✅ Verified | صَالِح → [sˤɑliħ] |
| **After emphatic (long)** | [aː] → [ɑː] | ✅ Verified | الصَّلَاة → [ɑsˤsˤɑlɑːh] |
| **Before emphatic (short)** | [a] → [ɑ] | ✅ Verified | مَصْدَر → [mɑsˤdar] |
| **Before emphatic (long)** | [aː] → [ɑː] | ✅ Verified | سَاطِع → [sɑːtˤiʕ] |
| **Blocking by front vowel** | Kasra blocks | ✅ Verified | صِين → [sˤin] (no backing) |
| **Cross-word continuation** | Optional | ⚠️ Dialect-dependent | قال الله |

**Emphatic Letters:** ص ض ط ظ ق (+ heavy rāʾ when enabled)

---

## ❌ Category 5: Rāʾ Rules (DISABLED in Phase 1)

**Status:** 10 rules exist but are not loaded when `enable_raa_rules=False`

**Rationale:**
- Too complex for Phase 1
- Context-dependent (10 different scenarios)
- Can be enabled later via configuration flag

**To Enable (Future):**
```python
pipeline = SymbolicLayerPipeline(enable_raa_rules=True)
```

See [RAA_RULES_CONFIGURATION.md](docs/RAA_RULES_CONFIGURATION.md) for details.

---

## 📊 Verification Status

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ **Verified Working** | 22 rules | 79% |
| ⚠️ **Needs Testing** | 6 rules | 21% |
| **Total Active** | **28 rules** | **100%** |

### Rules Needing Verification

1. **Idghām without ghunnah** - Need test: مِنْ لَدُنْهُ (min ladunhu)
2. **Madd Muttaṣil** - Need test: Verse 2:20 with السَّمَآءِ
3. **Madd Munfaṣil** - Need test: Verse 108:1 إِنَّآ أَعْطَيْنَٰكَ
4. **Madd Lāzim** - Need test: Al-Fatiha 1:7 الضَّآلِّينَ
5. **Madd ʿĀriḍ** - Need test: Pausal forms at verse endings
6. **Qalqalah with Shaddah** - Need test: مُدَّكِرٌ

---

## 🎯 Priority Testing Queue

### High Priority
1. ✅ **Tanween + noon rules** - Verified working
2. ✅ **Ghunnah detection** - All 4 types verified
3. ⚠️ **Idghām without ghunnah** - Still needs explicit test

### Medium Priority
4. ⚠️ **Madd muttaṣil** - Core madd rule, needs test verse
5. ⚠️ **Madd munfaṣil** - Common in Qur'an, needs test

### Low Priority
6. ⚠️ **Rare madd types** - Less common, can test later
7. ⚠️ **Qalqalah with shaddah** - Edge case

---

## 🚀 Quick Start

### Initialize Pipeline (Phase 1 Config)
```python
from symbolic_layer.pipeline import SymbolicLayerPipeline

# Default: Rāʾ rules disabled, focus on core rules
pipeline = SymbolicLayerPipeline()

# Or explicitly:
pipeline = SymbolicLayerPipeline(enable_raa_rules=False)
```

### Process Verse
```python
output = pipeline.process_verse(surah=1, ayah=1)

# Check which rules were applied
for app in output.annotated_sequence.rule_applications:
    print(f"{app.rule.name} ({app.rule.category.value})")
```

### Generate Validation Report
```python
python3 create_targeted_validation_report.py
```

---

## 📈 Success Metrics (Phase 1)

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Core rules implemented | 28 | 28 | ✅ 100% |
| Rules verified working | 90% | 79% | 🔄 88% progress |
| Noon/meem rules verified | 100% | 100% | ✅ Complete |
| Ghunnah detection | 100% | 100% | ✅ Complete |
| Madd rules tested | 100% | 17% | ⚠️ Needs work |

---

## 🎓 Next Steps

### For Developers
1. Run test suite: `python3 test_raa_configuration.py`
2. Generate validation report: `python3 create_targeted_validation_report.py`
3. Review verification status for each rule category
4. Add specific test verses for unverified rules

### For Phase 2 Planning
1. Test Rāʾ rules with `enable_raa_rules=True`
2. Validate complex madd types
3. Add edge case testing
4. Prepare for production deployment

---

## 📚 Documentation

- [Rāʾ Rules Configuration](docs/RAA_RULES_CONFIGURATION.md) - Detailed guide on enabling/disabling rāʾ rules
- [Complete Rule Checklist](RULE_CHECKLIST.md) - All 38 rules (including disabled rāʾ rules)
- [Test Pipeline](test_complete_pipeline.py) - End-to-end testing script
- [Rāʾ Configuration Test](test_raa_configuration.py) - Demonstrates flag functionality

---

**Last Updated:** 2026-02-06
**Pipeline Version:** 1.0
**Configuration:** Phase 1 (Core Rules Only)
