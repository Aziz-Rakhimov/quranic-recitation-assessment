# Rāʾ Rules Configuration

## Overview

The Symbolic Layer Pipeline supports configurable Rāʾ (ر) tafkhīm/tarqīq rules through the `enable_raa_rules` flag. This allows you to toggle the complex Rāʾ pronunciation rules on or off depending on your assessment needs.

## Why Disable Rāʾ Rules?

Rāʾ tafkhīm (heavy) and tarqīq (light) rules are among the most complex Tajwīd rules because:

1. **Context-dependent**: Whether rāʾ is heavy or light depends on:
   - The vowel it carries (fatha, damma, kasra, sukoon)
   - Preceding and following phonemes
   - Proximity to emphatic letters
   - Word boundaries and special cases

2. **10 different rules**: The system implements 10 distinct rāʾ rules covering various contexts

3. **Phase-based approach**: For initial deployment (Phase 1), focusing on core rules provides:
   - Simpler assessment criteria
   - Fewer false positives
   - Better user experience for beginners

## Configuration

### Default (Phase 1): Rāʾ Rules Disabled

```python
from symbolic_layer.pipeline import SymbolicLayerPipeline

# Default configuration - Rāʾ rules disabled
pipeline = SymbolicLayerPipeline(
    speaker_type="male",
    enable_raa_rules=False  # This is the default
)

# Or simply:
pipeline = SymbolicLayerPipeline()  # enable_raa_rules defaults to False
```

**Result:**
- 28 active rules (11 noon/meem + 6 madd + 5 qalqalah + 6 emphasis)
- Focus on core Tajwīd rules
- No rāʾ assessment

### Phase 2+: Rāʾ Rules Enabled

```python
from symbolic_layer.pipeline import SymbolicLayerPipeline

# Enable comprehensive analysis including Rāʾ
pipeline = SymbolicLayerPipeline(
    speaker_type="male",
    enable_raa_rules=True  # Explicitly enable
)
```

**Result:**
- 38 active rules (28 core + 10 rāʾ rules)
- Comprehensive Tajwīd analysis
- Full rāʾ tafkhīm/tarqīq assessment

## Rules Breakdown

### Core Rules (Always Active - 28 rules)

| Category | Count | Rules |
|----------|-------|-------|
| **Noon/Meem Sākinah** | 11 | Ghunnah mushaddadah (2), Iẓhār (2), Idghām (3), Iqlāb (1), Ikhfāʾ (3) |
| **Madd** | 6 | Ṭabīʿī, Muttaṣil, Munfaṣil, Lāzim, ʿĀriḍ, Ṣilah Kubrā |
| **Qalqalah** | 5 | Minor, Major, With Shaddah, Emphatic, Non-emphatic |
| **Emphasis** | 6 | Vowel backing (4), Blocking (1), Cross-word (1) |

### Rāʾ Rules (Optional - 10 rules)

| Rule Name | Context | Description |
|-----------|---------|-------------|
| `raa_tafkheem_with_fatha` | ر with fatha | Heavy rāʾ (rˤ) |
| `raa_tafkheem_with_damma` | ر with damma | Heavy rāʾ (rˤ) |
| `raa_tarqeeq_with_kasra` | ر with kasra | Light rāʾ (r) |
| `raa_tafkheem_sakinah_after_fatha` | رْ after fatha | Heavy sākin rāʾ |
| `raa_tafkheem_sakinah_after_damma` | رْ after damma | Heavy sākin rāʾ |
| `raa_tarqeeq_sakinah_after_kasra` | رْ after kasra | Light sākin rāʾ |
| `raa_after_yaa_sakinah` | ر after يْ | Usually light |
| `raa_misr_exception` | Word مِصْر | Both valid |
| `raa_after_hamzat_wasl_kasra` | ر after ٱ with kasra | Light |
| `raa_emphatic_context_override` | ر near emphatics | Heavy override |

## Impact on Assessment

### Phase 1 (Rāʾ Disabled)

**Focus Areas:**
- ✅ Noon sākinah rules (Iẓhār, Idghām, Iqlāb, Ikhfāʾ)
- ✅ Ghunnah detection and duration
- ✅ Qalqalah (echo sound on ق ط ب ج د)
- ✅ Madd prolongation (2, 4-5, 6 counts)
- ✅ Emphatic vowel backing

**Not Assessed:**
- ❌ Rāʾ tafkhīm vs tarqīq
- ❌ Rāʾ context rules

**Benefits:**
- Simpler for beginners
- Fewer assessment criteria
- More reliable error detection
- Clear feedback on core rules

### Phase 2+ (Rāʾ Enabled)

**Additional Assessment:**
- ✅ All Phase 1 rules
- ✅ Rāʾ heaviness (tafkhīm) when appropriate
- ✅ Rāʾ lightness (tarqīq) when appropriate
- ✅ Context-dependent rāʾ pronunciation

**Benefits:**
- Comprehensive Tajwīd analysis
- Advanced reciter assessment
- Full rule coverage

## Testing

Run the test script to see both configurations:

```bash
python3 test_raa_configuration.py
```

Output shows:
- Rule counts for each configuration
- Example processing with both settings
- Demonstration of rule application differences

## Example Usage in Scripts

### Validation Report (Phase 1)

```python
from symbolic_layer.pipeline import SymbolicLayerPipeline

# Initialize without rāʾ rules
pipeline = SymbolicLayerPipeline()  # enable_raa_rules=False by default

# Process verses
output = pipeline.process_verse(surah=1, ayah=1)

# Rāʾ rules won't appear in the report
print(f"Rules applied: {len(output.annotated_sequence.rule_applications)}")
```

### Research/Analysis (Full Rules)

```python
from symbolic_layer.pipeline import SymbolicLayerPipeline

# Initialize with all rules
pipeline = SymbolicLayerPipeline(enable_raa_rules=True)

# Comprehensive analysis
output = pipeline.process_verse(surah=1, ayah=1)

# Includes rāʾ rule applications
print(f"Rules applied: {len(output.annotated_sequence.rule_applications)}")
```

## Implementation Details

### TajweedEngine

The `TajweedEngine` conditionally loads `raa_rules.yaml`:

```python
def _load_all_rules(self):
    """Load all rule files from the config directory."""
    rule_files = [
        'noon_meem_rules.yaml',
        'madd_rules.yaml',
        'qalqalah_rules.yaml',
        'emphatic_backing_rules.yaml'
    ]

    # Only load raa rules if enabled
    if self.enable_raa_rules:
        rule_files.append('raa_rules.yaml')

    for rule_file in rule_files:
        # Load rules...
```

### Pipeline

The `SymbolicLayerPipeline` accepts and passes the flag:

```python
def __init__(
    self,
    # ... other parameters
    enable_raa_rules: bool = False  # Default: disabled
):
    # ...
    self.tajweed_engine = TajweedEngine(
        rule_config_dir=tajweed_rules_dir,
        phoneme_inventory=self.phoneme_inventory,
        enable_raa_rules=enable_raa_rules  # Pass through
    )
```

## Rule Files

All rule YAML files remain in the codebase:
- ✅ `data/tajweed_rules/noon_meem_rules.yaml` - Always loaded
- ✅ `data/tajweed_rules/madd_rules.yaml` - Always loaded
- ✅ `data/tajweed_rules/qalqalah_rules.yaml` - Always loaded
- ✅ `data/tajweed_rules/emphatic_backing_rules.yaml` - Always loaded
- ⚠️ `data/tajweed_rules/raa_rules.yaml` - **Conditionally loaded**

The rāʾ rules file is kept in the repository for:
- Future phases when ready to enable
- Research and development
- Testing and validation
- Comprehensive documentation

## Roadmap

### Phase 1 (Current)
- ✅ Core rules implemented and validated
- ✅ Rāʾ rules disabled by default
- ✅ Configuration flag functional
- 🎯 Focus: noon/meem, ghunnah, qalqalah, madd

### Phase 2 (Future)
- 🔄 Enable rāʾ rules gradually
- 🔄 Test rāʾ assessment accuracy
- 🔄 Collect user feedback
- 🎯 Goal: Full Tajwīd coverage

### Phase 3+ (Advanced)
- 🔄 Additional complex rules (lām shamsiyyah/qamariyyah variants)
- 🔄 Context-aware assessment
- 🔄 Personalized difficulty levels
- 🎯 Goal: Adaptive assessment system

## Summary

| Configuration | Rules | Use Case |
|--------------|-------|----------|
| **Default** (`enable_raa_rules=False`) | 28 | Phase 1 assessment, beginner-friendly |
| **Full** (`enable_raa_rules=True`) | 38 | Research, advanced assessment, comprehensive analysis |

The flexible configuration allows the system to grow with user needs while maintaining stability and reliability in early phases.
