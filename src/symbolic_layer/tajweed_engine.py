"""
Tajwīd Rule Engine.

This module loads Tajwīd rules from YAML files and applies them to phoneme
sequences to generate annotated sequences with rule applications.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Optional, Any
from .models.phoneme import Phoneme, PhonemeSequence, PhonemeInventory
from .models.rule import (
    TajweedRule,
    RulePattern,
    RuleAction,
    AcousticEffect,
    VerificationCriterion,
    ErrorDefinition,
    AnnotatedPhonemeSequence,
    RuleApplication
)
from .models.enums import RuleCategory, ActionType, ErrorSeverity, ErrorCategory
from .utils.unicode_utils import ARABIC_ALIF_WASLA


# Rules that may only be applied via the muqattaat injection path
# (PhonemeSequence.muqattaat_rule_specs). These rules have triggers that
# are letter-name level and cannot be detected from the raw phoneme stream
# — e.g. madd lāzim ḥarfī fires only on long vowels inside Muqaṭṭaʿāt
# letter-name spellings, and the bare `ghunnah` rule fires only at the
# lām→mīm junction inside الٓمٓ-style sequences. The engine's normal pattern
# scanner must skip these names so it does not over-fire on every long
# vowel or every 'm' phoneme in the sequence.
MUQATTAAT_INJECTION_ONLY_RULES = frozenset({'madd_lazim', 'ghunnah'})


class TajweedEngine:
    """
    Engine for applying Tajwīd rules to phoneme sequences.

    Loads rule definitions from YAML files and applies them in priority order
    to modify phoneme sequences according to Tajwīd pronunciation rules.
    """

    def __init__(
        self,
        rule_config_dir: Optional[str] = None,
        phoneme_inventory: Optional[PhonemeInventory] = None,
        enable_raa_rules: bool = False
    ):
        """
        Initialize the Tajwīd engine.

        Args:
            rule_config_dir: Directory containing rule YAML files
            phoneme_inventory: Phoneme inventory for looking up phonemes
            enable_raa_rules: Whether to enable Rāʾ tafkhīm/tarqīq rules (default: False)
        """
        if rule_config_dir is None:
            rule_config_dir = "data/tajweed_rules"

        self.rule_config_dir = Path(rule_config_dir)
        self.phoneme_inventory = phoneme_inventory
        self.enable_raa_rules = enable_raa_rules
        self.rules: List[TajweedRule] = []

        # Load all rule files
        self._load_all_rules()

        # Sort by priority (higher priority first)
        self._sort_rules_by_priority()

    def _load_all_rules(self):
        """Load all rule files from the config directory."""
        rule_files = [
            'noon_meem_rules.yaml',
            'madd_rules.yaml',
            'qalqalah_rules.yaml',
            'emphatic_backing_rules.yaml',
            'pronunciation_rules.yaml',
            'muqattaat_rules.yaml',
        ]

        # Only load raa rules if enabled
        if self.enable_raa_rules:
            rule_files.append('raa_rules.yaml')

        for rule_file in rule_files:
            rule_path = self.rule_config_dir / rule_file
            if rule_path.exists():
                self._load_rules_from_file(rule_path)

    def _load_rules_from_file(self, file_path: Path):
        """Load rules from a single YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            rules_data = data.get('rules', [])
            for rule_data in rules_data:
                rule = self._parse_rule(rule_data)
                if rule:
                    self.rules.append(rule)

        except Exception as e:
            print(f"Warning: Failed to load rules from {file_path}: {e}")

    def _parse_rule(self, rule_data: Dict) -> Optional[TajweedRule]:
        """Parse a rule from YAML data."""
        try:
            # Parse pattern
            pattern_data = rule_data.get('pattern', {})
            pattern = RulePattern(
                target=pattern_data.get('target', ''),
                preceding_context=pattern_data.get('preceding_context'),
                following_context=pattern_data.get('following_context'),
                conditions=pattern_data.get('conditions', {}),
                following_arabic=pattern_data.get('following_arabic'),
                preceding_arabic=pattern_data.get('preceding_arabic')
            )

            # Parse action
            action_data = rule_data.get('action', {})

            # Handle both 'replacement' (list) and 'replacement_phoneme' (single)
            replacement = action_data.get('replacement')
            if not replacement and action_data.get('replacement_phoneme'):
                replacement = [action_data.get('replacement_phoneme')]

            action = RuleAction(
                type=ActionType(action_data.get('type', 'keep_original')),
                replacement=replacement,
                duration_multiplier=action_data.get('duration_multiplier', 1.0),
                notes=action_data.get('notes')
            )

            # Parse acoustic effect
            acoustic_data = rule_data.get('acoustic_expectations') or rule_data.get('acoustic_effect')
            acoustic_effect = None
            if acoustic_data:
                acoustic_effect = AcousticEffect(**acoustic_data)

            # Parse verification criteria
            criteria = []
            for crit_data in rule_data.get('verification_criteria', []):
                criterion = VerificationCriterion(**crit_data)
                criteria.append(criterion)

            # Parse error types
            error_types = []
            for error_data in rule_data.get('error_types', []):
                error_def = ErrorDefinition(
                    code=error_data.get('code', ''),
                    description=error_data.get('description', ''),
                    severity=ErrorSeverity(error_data.get('severity', 'minor')),
                    category=ErrorCategory(rule_data.get('category', 'tajweed'))
                )
                error_types.append(error_def)

            # Create rule
            rule = TajweedRule(
                name=rule_data.get('name', ''),
                category=RuleCategory(rule_data.get('category', 'general')),
                priority=rule_data.get('priority', 50),
                description=rule_data.get('description', ''),
                arabic_name=rule_data.get('arabic_name'),
                pattern=pattern,
                action=action,
                acoustic_effect=acoustic_effect,
                verification_criteria=criteria,
                examples=rule_data.get('examples', []),
                error_types=error_types
            )

            return rule

        except Exception as e:
            print(f"Warning: Failed to parse rule {rule_data.get('name', 'unknown')}: {e}")
            return None

    def _sort_rules_by_priority(self):
        """Sort rules by priority (higher priority first)."""
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def apply_rules(
        self,
        phoneme_sequence: PhonemeSequence
    ) -> AnnotatedPhonemeSequence:
        """
        Apply all Tajwīd rules to a phoneme sequence.

        Args:
            phoneme_sequence: Input phoneme sequence

        Returns:
            AnnotatedPhonemeSequence with rule applications
        """
        # Start with original phonemes
        current_phonemes = list(phoneme_sequence.phonemes)
        rule_applications = []

        # Apply each rule in priority order
        for rule in self.rules:
            # Skip rules that may only fire via the muqattaat injection
            # path. They have no normal-phoneme-stream trigger; allowing
            # the scanner to match them would over-fire on every long
            # vowel / 'm' / etc. (see MUQATTAAT_INJECTION_ONLY_RULES).
            if rule.name in MUQATTAAT_INJECTION_ONLY_RULES:
                continue
            # Scan through sequence looking for matches
            i = 0
            while i < len(current_phonemes):
                # Build context for rule matching
                context = self._build_context(
                    current_phonemes,
                    i,
                    phoneme_sequence.word_boundaries,
                    phoneme_sequence.verse_boundaries
                )

                # Check if rule matches at this position
                if self._check_rule_match(rule, current_phonemes, i, context):
                    # Apply the rule
                    application = self._apply_single_rule(
                        rule,
                        current_phonemes,
                        i,
                        context
                    )

                    if application:
                        rule_applications.append(application)

                        # IMPORTANT: For assessment, we keep original phonemes intact
                        # Modified phonemes are stored in RuleApplication for reference
                        # This ensures:
                        # 1. MFA alignment works with original phoneme sequence
                        # 2. We can compare expected vs actual pronunciation
                        # 3. Consistent indexing throughout pipeline

                        # Skip ahead to avoid re-processing same phonemes
                        i = application.end_index + 1
                        continue

                i += 1

        # ── Muqaṭṭaʿāt rule injection ────────────────────────────────────
        # The phonemizer detects Muqaṭṭaʿāt letter-names (الٓمٓ, يسٓ, …) at the
        # word level and emits letter-name phonemes from a lookup table. It
        # also records (phoneme_index, rule_name) specs for rules whose
        # triggers are letter-name level (madd lāzim ḥarfī, ghunnah at the
        # lām→mīm junction, qalqalah on the qāf in "qaaf"). Here we look up
        # each spec's rule by name and create a RuleApplication for it.
        muqattaat_specs = getattr(phoneme_sequence, 'muqattaat_rule_specs', None) or []
        if muqattaat_specs:
            rules_by_name = {r.name: r for r in self.rules}
            existing_app_keys = {
                (app.rule.name, app.start_index) for app in rule_applications
            }
            for spec in muqattaat_specs:
                rule_name = spec.get('rule_name')
                idx = spec.get('phoneme_index')
                if rule_name is None or idx is None:
                    continue
                rule = rules_by_name.get(rule_name)
                if rule is None:
                    continue
                if not (0 <= idx < len(current_phonemes)):
                    continue
                # Skip if an identical rule application already exists at this
                # position (e.g. existing qalqalah_major fired automatically
                # for the dāl in ṣād — no need to add a duplicate from spec).
                if (rule_name, idx) in existing_app_keys:
                    continue
                target_phoneme = current_phonemes[idx]
                rule_applications.append(RuleApplication(
                    rule=rule,
                    start_index=idx,
                    end_index=idx,
                    original_phonemes=[target_phoneme],
                    modified_phonemes=[target_phoneme],
                    acoustic_expectations=rule.acoustic_effect,
                ))
                existing_app_keys.add((rule_name, idx))

        # Resolve madd conflicts: specific madd types suppress madd_tabii
        # at the same position (madd_tabii is the base case, overridden by
        # madd_arid, madd_muttasil, madd_munfasil, madd_lazim, madd_silah).
        # 'madd_lazim' here is the Muqaṭṭaʿāt-specific 6-count harfī rule
        # injected via muqattaat_rule_specs above; it must suppress the
        # tabii that the engine would otherwise fire on the same long vowel.
        specific_madd_rules = {
            'madd_arid_lissukun', 'madd_muttasil', 'madd_munfasil',
            'madd_lazim_kalimi', 'madd_silah_kubra',
            'madd_lazim',
        }
        specific_madd_positions = {
            app.start_index for app in rule_applications
            if app.rule.name in specific_madd_rules
        }
        if specific_madd_positions:
            rule_applications = [
                app for app in rule_applications
                if not (app.rule.name == 'madd_tabii'
                        and app.start_index in specific_madd_positions)
            ]

        # Create annotated sequence
        return AnnotatedPhonemeSequence(
            phonemes=current_phonemes,
            word_boundaries=phoneme_sequence.word_boundaries,
            verse_boundaries=phoneme_sequence.verse_boundaries,
            original_text=phoneme_sequence.original_text,
            word_texts=phoneme_sequence.word_texts,
            rule_applications=rule_applications
        )

    def _build_context(
        self,
        phonemes: List[Phoneme],
        index: int,
        word_boundaries: List[int],
        verse_boundaries: List[int]
    ) -> Dict[str, Any]:
        """Build context dictionary for rule matching."""
        # Pre-calculate boundary conditions for reuse
        is_word_start = index in word_boundaries or index == 0
        is_word_end = (index + 1) in word_boundaries or (index + 1) >= len(phonemes)

        # Calculate verse-end detection
        is_at_sequence_end = (index + 1) >= len(phonemes)
        is_verse_end_marked = (index + 1) in verse_boundaries

        # If no verse boundaries defined, treat sequence end as verse end
        if len(verse_boundaries) == 0:
            # Standalone text or single verse - end of sequence IS verse end
            is_verse_end = is_at_sequence_end
        else:
            # Multiple verses - use explicit boundaries
            is_verse_end = is_verse_end_marked

        context = {
            'position': index,
            'total_phonemes': len(phonemes),
            'is_word_boundary': index in word_boundaries,
            'is_verse_boundary': index in verse_boundaries,
            'is_word_start': is_word_start,
            'is_word_end': is_word_end,
            # Position conditions for qalqalah and other rules
            'position_mid_word': not is_word_start and not is_word_end,
            'not_at_word_end': not is_word_end,
            'not_at_verse_end': not is_verse_end,
            'position_word_end_or_verse_end': is_word_end or is_verse_end,
            'at_verse_end_or_pause': is_verse_end,
        }

        # Add phoneme-specific context
        if index < len(phonemes):
            phoneme = phonemes[index]
            context['is_vowel'] = phoneme.is_vowel()
            context['is_consonant'] = phoneme.is_consonant()
            context['is_emphatic'] = phoneme.is_emphatic()
            context['is_long_vowel'] = phoneme.is_long()  # For Madd rules

            # Check for Madd Munfasil (cross-word hamza detection)
            if phoneme.is_long():
                is_at_word_end = (index + 1) in word_boundaries

                if is_at_word_end and index + 1 < len(phonemes):
                    # Long vowel at word end - check first phoneme of next word
                    next_phoneme = phonemes[index + 1]
                    context['hamza_follows_in_next_word'] = next_phoneme.symbol == 'ʔ'
                    context['word_boundary_between'] = True

                    # Suppress madd_tabii when next word starts with ٱ (hamza wasla).
                    # Hamza wasla is silent/connecting — it's not a true hamza, so
                    # no prolongation applies to the preceding word-final long vowel.
                    # Examples: وَلَا ٱلضَّآلِّينَ, أَيُّهَا ٱلْكَٰفِرُونَ, هَٰذَا ٱلْبَيْتِ
                    next_starts_wasla = (next_phoneme.arabic_letter == ARABIC_ALIF_WASLA)
                    context['not_wasl_mater_lectionis'] = not next_starts_wasla
                else:
                    context['hamza_follows_in_next_word'] = False
                    context['word_boundary_between'] = False
                    context['not_wasl_mater_lectionis'] = True  # Not word-final, always apply madd

                # For Madd Arid Lissukun - check if long vowel follows a sukoon
                if index > 0:
                    prev_phoneme = phonemes[index - 1]
                    # Check if previous consonant had sukoon (no vowel between)
                    if prev_phoneme.is_consonant():
                        context['follows_sukoon'] = True
                    else:
                        context['follows_sukoon'] = False
                else:
                    context['follows_sukoon'] = False

                # Verse-final long vowel with no following phoneme: the pausal form
                # (waqf) applies a virtual sukoon to the long vowel itself.
                # E.g. سَجَىٰ, فَـَٔاوَىٰ, فَهَدَىٰ — all end in a bare long aː.
                # This is sufficient to trigger Madd ʿĀriḍ Lissukūn.
                if context.get('at_verse_end_or_pause') and (index + 1) >= len(phonemes):
                    context['follows_sukoon'] = True

                # Special handling for Madd Arid Lissukun at verse-end in pausal form
                # In pausal form, final vowel drops to sukoon: نَسْتَعِينُ → نَسْتَعِينْ
                # Pattern: [long vowel][consonant][short vowel at end] → pausal [long vowel][consonant with sukoon]
                # Check if long vowel is near the end of the sequence (would be at verse-end in recitation)
                if index + 1 < len(phonemes):
                    next_p = phonemes[index + 1]

                    # Check if next phoneme is a consonant near sequence end
                    if next_p.is_consonant():
                        # In pausal form, if this consonant is followed by a final vowel (or is at end),
                        # it would have sukoon. Check if consonant is within 2 positions of end.
                        consonant_near_end = (index + 2 >= len(phonemes) - 1)

                        if consonant_near_end:
                            # This matches pausal pattern: long vowel + consonant (with sukoon in pausal form) at verse-end
                            context['follows_sukoon'] = True
                            context['at_verse_end_or_pause'] = True

                # For Madd Lazim Kalimi - check if shaddah follows long vowel
                # Must be within the SAME word (no word boundary between long vowel and doubled consonant)
                if index + 1 < len(phonemes) and (index + 1) not in word_boundaries:
                    next_p = phonemes[index + 1]
                    if next_p.is_consonant() and index + 2 < len(phonemes) and (index + 2) not in word_boundaries:
                        phoneme_after = phonemes[index + 2]
                        # Shaddah detected if same consonant repeated within the same word
                        context['following_has_shaddah'] = next_p.symbol == phoneme_after.symbol
                    else:
                        context['following_has_shaddah'] = False
                else:
                    context['following_has_shaddah'] = False

            # Check for sukoon (no vowel following)
            if index + 1 < len(phonemes):
                next_phoneme = phonemes[index + 1]
                context['has_sukoon'] = not next_phoneme.is_vowel()

                # Waqf sukoon: in pausing at verse end, the final short vowel/tanween is dropped.
                # A qalqalah letter followed by short vowel(s) at verse end effectively gets sukoon
                # Examples: خَلَقَ → خَلَقْ, ٱلصَّمَدُ → ٱلصَّمَدْ, أَحَدٌ → أَحَدْ
                # Restricted to qalqalah letters to avoid triggering other rules (idhhar_shafawi etc.)
                QALQALAH_LETTERS = {'q', 'tˤ', 'b', 'dʒ', 'd'}
                if not context['has_sukoon'] and phoneme.symbol in QALQALAH_LETTERS:
                    SHORT_VOWELS = {'a', 'i', 'u', 'ɑ'}
                    is_short_vowel = next_phoneme.symbol in SHORT_VOWELS
                    if is_short_vowel:
                        # Check if followed by just vowel at verse end (e.g. خَلَقَ)
                        is_vowel_at_verse_end = (index + 2) >= len(phonemes) or (index + 2) in verse_boundaries

                        # Check if followed by tanween (vowel + n) at verse end (e.g. أَحَدٌ)
                        # IMPORTANT: tanween fath (a+n) keeps fatha+alif at waqf — NOT sukoon.
                        # Only tanween damm (u+n) and tanween kasr (i+n) convert to sukoon.
                        # Example: أَفْوَاجًا → waqf form afwājā (fatha), NOT afwāj (sukoon)
                        is_tanween_at_verse_end = False
                        if index + 2 < len(phonemes):
                            phoneme_after_vowel = phonemes[index + 2]
                            if phoneme_after_vowel.symbol == 'n':
                                is_tanween_damm_or_kasr = next_phoneme.symbol in ('u', 'i')
                                if is_tanween_damm_or_kasr:
                                    is_tanween_at_verse_end = (index + 3) >= len(phonemes) or (index + 3) in verse_boundaries

                        if is_vowel_at_verse_end or is_tanween_at_verse_end:
                            context['has_sukoon'] = True
                            context['position_word_end_or_verse_end'] = True
                            context['not_at_verse_end'] = False  # block qalqalah_minor

                # Check if this is a geminate (doubled consonant - shaddah)
                context['is_geminate'] = phoneme.symbol == next_phoneme.symbol
                context['has_shaddah'] = context['is_geminate']

                # Set following_is_* conditions for rule matching
                context['following_is_baa'] = next_phoneme.symbol == 'b'
                context['following_is_meem'] = next_phoneme.symbol == 'm'
                context['following_is_lam_or_raa'] = next_phoneme.symbol in ['l', 'r']
                context['following_is_idgham_letter'] = next_phoneme.symbol in ['j', 'w', 'n', 'm']  # ي و ن م
                context['following_is_throat_letter'] = next_phoneme.symbol in ['ʔ', 'h', 'ʕ', 'ħ', 'ɣ', 'x']  # ء ه ع ح غ خ
                # ikhfaa_heavy letters: ص ض ط ظ ق (IPA: sˤ dˤ tˤ ðˤ q)
                # is_emphatic() uses IPA pharyngealization (ˤ) and returns False for q
                # because q is uvular, not pharyngealized — but tajweed classifies ق
                # as an ikhfaa-heavy letter alongside ص ض ط ظ.
                _IKHFAA_HEAVY = {'sˤ', 'dˤ', 'tˤ', 'ðˤ', 'q'}
                _is_emphatic_for_ikhfaa = next_phoneme.is_emphatic() or next_phoneme.symbol in _IKHFAA_HEAVY
                context['following_is_emphatic'] = _is_emphatic_for_ikhfaa

                # Negated following conditions (for idhhar_shafawi, ikhfaa rules)
                context['following_not_meem'] = next_phoneme.symbol != 'm'
                context['following_not_baa'] = next_phoneme.symbol != 'b'
                context['following_not_emphatic'] = not _is_emphatic_for_ikhfaa

                # Exclusion conditions for ikhfaa rules (not idhhar, not idgham, not iqlab letters)
                IDHHAR_LETTERS = {'ʔ', 'h', 'ʕ', 'ħ', 'ɣ', 'x'}   # ء ه ع ح غ خ
                IDGHAM_LETTERS = {'j', 'w', 'n', 'm', 'l', 'r'}     # ي و ن م ل ر
                IQLAB_LETTER = {'b'}                                   # ب
                context['not_idhhar_letter'] = next_phoneme.symbol not in IDHHAR_LETTERS
                context['not_idgham_letter'] = next_phoneme.symbol not in IDGHAM_LETTERS
                context['not_iqlab_letter'] = next_phoneme.symbol not in IQLAB_LETTER

                # Qalqalah environment detection
                # near_emphatic_letter: current phoneme OR any neighbour within 1 position is emphatic
                emphatic_symbols = {'q', 'tˤ', 'sˤ', 'dˤ', 'ðˤ'}  # ق ط ص ض ظ
                neighbour_before = phonemes[index - 1] if index > 0 else None
                neighbour_after = phonemes[index + 1] if index + 1 < len(phonemes) else None
                near_emphatic = (
                    phoneme.is_emphatic() or
                    phoneme.symbol in emphatic_symbols or
                    (neighbour_before is not None and (neighbour_before.is_emphatic() or neighbour_before.symbol in emphatic_symbols)) or
                    (neighbour_after is not None and (neighbour_after.is_emphatic() or neighbour_after.symbol in emphatic_symbols))
                )
                context['near_emphatic_letter'] = near_emphatic
                context['near_light_letter'] = not near_emphatic

                # Madd Muttasil: hamza in same word (no word boundary between long vowel and hamza)
                is_next_word_boundary = (index + 1) in word_boundaries
                hamza_in_same_word = (next_phoneme.symbol == 'ʔ') and not is_next_word_boundary
                context['hamza_follows_in_same_word'] = hamza_in_same_word
                context['no_word_boundary_between'] = not is_next_word_boundary

                # Madd rule conditions
                context['no_hamza_following'] = next_phoneme.symbol != 'ʔ'
                context['hamza_follows'] = next_phoneme.symbol == 'ʔ'

                # Check if there's sukoon after the long vowel
                # At word boundaries, consider no sukoon following for current word
                if (index + 1) in word_boundaries:
                    # Word-final long vowel - no sukoon in current word context
                    context['no_sukoon_following'] = True
                elif next_phoneme.is_consonant() and index + 2 < len(phonemes):
                    # Long vowel followed by consonant - check if consonant has vowel
                    phoneme_after_next = phonemes[index + 2]
                    context['no_sukoon_following'] = phoneme_after_next.is_vowel()
                else:
                    # Next is a vowel or at end - no sukoon following
                    context['no_sukoon_following'] = next_phoneme.is_vowel() or (index + 2 >= len(phonemes))
            else:
                # At end of phoneme sequence
                context['has_sukoon'] = True
                context['is_geminate'] = False
                context['has_shaddah'] = False
                # Set Madd conditions for end of sequence
                context['no_hamza_following'] = True  # No phoneme follows
                context['no_sukoon_following'] = True  # No sukoon at end (pausal form)
                # Negated/exclusion conditions default to True (nothing follows)
                context['following_not_meem'] = True
                context['following_not_baa'] = True
                context['following_not_emphatic'] = True
                context['not_idhhar_letter'] = True
                context['not_idgham_letter'] = True
                context['not_iqlab_letter'] = True
                context['near_emphatic_letter'] = False
                context['near_light_letter'] = True
                context['hamza_follows_in_same_word'] = False
                context['no_word_boundary_between'] = True

            # Detect pronoun haa for Madd Silah Kubra
            # Pronoun haa (هُ/هِ meaning "him/his") appears as 'h' + vowel at word-end
            # A genuine pronoun suffix هُ/هِ has at most 2 consonants in its word
            # (e.g., بِهِ = b+h, لَهُ = l+h). Words like اللَّهُ have 4 consonants → NOT pronoun.
            if phoneme.symbol == 'h' and index + 1 < len(phonemes):
                next_p = phonemes[index + 1]
                # Check if haa has kasra (i) or damma (u) vowel
                if next_p.symbol in ['i', 'u']:
                    # Check if this h+vowel is at word boundary
                    is_at_word_boundary = (index + 2) in word_boundaries

                    if is_at_word_boundary and index + 2 < len(phonemes):
                        # Check if next word starts with hamza
                        phoneme_after_boundary = phonemes[index + 2]
                        if phoneme_after_boundary.symbol == 'ʔ':
                            # Count consonants in the current word to distinguish pronoun haa from root haa
                            # Find start of current word
                            word_start = 0
                            for wb in sorted(word_boundaries):
                                if wb <= index:
                                    word_start = wb
                                else:
                                    break
                            consonants_in_word = sum(
                                1 for p in phonemes[word_start:index + 1]
                                if p.is_consonant()
                            )
                            # Pronoun haa: word has ≤ 2 consonants (b+h, l+h, etc.)
                            # Root haa (Allah, etc.): word has 3+ consonants
                            if consonants_in_word <= 2:
                                context['is_pronoun_haa'] = True
                                context['has_kasra_or_damma'] = True
                                context['hamza_follows'] = True
                            else:
                                context['is_pronoun_haa'] = False
                        else:
                            context['is_pronoun_haa'] = False
                    else:
                        context['is_pronoun_haa'] = False
                else:
                    context['is_pronoun_haa'] = False
            else:
                context['is_pronoun_haa'] = False

            # Detect Tāʾ Marbūṭa (ة) for pronunciation rules
            # The phonemizer tags ة-sourced phonemes with arabic_letter='ة' (U+0629)
            # This is the precise check - no structural inference needed
            if phoneme.symbol == 't':
                is_likely_ta_marbuta = (phoneme.arabic_letter == '\u0629')  # ة
                context['is_ta_marbuta'] = is_likely_ta_marbuta

                # For tāʾ marbūṭa, check if word is at verse/sequence end (for waqf detection)
                if is_likely_ta_marbuta:
                    # Find where this word ends (after 't' + vowel + optional tanween)
                    word_end_position = index + 1  # Start after 't'
                    if index + 1 < len(phonemes) and phonemes[index + 1].is_vowel():
                        word_end_position = index + 2  # After vowel
                        if index + 2 < len(phonemes) and phonemes[index + 2].symbol == 'n':
                            word_end_position = index + 3  # After tanween 'n'

                    # Check if word ends at sequence/verse end
                    word_at_verse_end = False
                    if len(verse_boundaries) == 0:
                        # Standalone text - check if word ends at sequence end
                        word_at_verse_end = word_end_position >= len(phonemes)
                    else:
                        # Multiple verses - check if word ends at verse boundary
                        word_at_verse_end = word_end_position in verse_boundaries

                    # Override at_verse_end_or_pause for tāʾ marbūṭa if word is at end
                    if word_at_verse_end:
                        context['at_verse_end_or_pause'] = True

                # Check if there's a following word (for waṣl vs waqf)
                if is_likely_ta_marbuta and index + 1 < len(phonemes):
                    # Find the next word boundary
                    next_word_starts = False
                    for i in range(index + 1, len(phonemes)):
                        if i in word_boundaries:
                            # Found word boundary, check if there's more content
                            next_word_starts = i < len(phonemes) - 1
                            break
                    context['has_following_word'] = next_word_starts
                else:
                    context['has_following_word'] = False
            else:
                context['is_ta_marbuta'] = False
                context['has_following_word'] = False

        return context

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

        # Check target pattern
        if not rule.pattern.matches_target(target_phoneme.symbol):
            return False

        # Check conditions
        for condition_key, condition_value in rule.pattern.conditions.items():
            if condition_key not in context:
                continue
            if context[condition_key] != condition_value:
                return False

        # Check following context
        if rule.pattern.following_context:
            if index + 1 >= len(phonemes):
                return False
            next_phoneme = phonemes[index + 1]
            if not self._matches_pattern(next_phoneme.symbol, rule.pattern.following_context):
                return False

        # Check preceding context
        if rule.pattern.preceding_context:
            if index <= 0:
                return False
            prev_phoneme = phonemes[index - 1]
            if not self._matches_pattern(prev_phoneme.symbol, rule.pattern.preceding_context):
                return False

        return True

    def _matches_pattern(self, symbol: str, pattern: str) -> bool:
        """Check if a symbol matches a pattern."""
        if pattern.startswith('![') and pattern.endswith(']'):
            # Negation pattern: "![m b]" means NOT m or b
            invalid_symbols = pattern.strip('![]').split()
            return symbol not in invalid_symbols
        elif pattern.startswith('[') and pattern.endswith(']'):
            # Pattern like "[q tˤ b]" - match any
            valid_symbols = pattern.strip('[]').split()
            return symbol in valid_symbols
        else:
            # Exact match
            return symbol == pattern

    def _apply_single_rule(
        self,
        rule: TajweedRule,
        phonemes: List[Phoneme],
        index: int,
        context: Dict[str, Any]
    ) -> Optional[RuleApplication]:
        """Apply a single rule at the given position."""
        original_phoneme = phonemes[index]

        # Determine what phonemes to modify based on action type
        if rule.action.type == ActionType.REPLACE:
            # Replace with new phoneme(s)
            if rule.action.replacement:
                modified_phonemes = []
                for symbol in rule.action.replacement:
                    new_phoneme = self._get_phoneme(symbol)
                    if new_phoneme:
                        modified_phonemes.append(new_phoneme)

                return RuleApplication(
                    rule=rule,
                    start_index=index,
                    end_index=index,
                    original_phonemes=[original_phoneme],
                    modified_phonemes=modified_phonemes,
                    acoustic_expectations=rule.acoustic_effect
                )

        elif rule.action.type == ActionType.KEEP_ORIGINAL:
            # No modification, just record the rule application
            return RuleApplication(
                rule=rule,
                start_index=index,
                end_index=index,
                original_phonemes=[original_phoneme],
                modified_phonemes=[original_phoneme],
                acoustic_expectations=rule.acoustic_effect
            )

        elif rule.action.type == ActionType.MODIFY_FEATURES:
            # Modify acoustic features (duration, etc.) but keep phoneme
            # Used for Madd rules that extend vowel duration
            return RuleApplication(
                rule=rule,
                start_index=index,
                end_index=index,
                original_phonemes=[original_phoneme],
                modified_phonemes=[original_phoneme],  # Phoneme stays same, features change
                acoustic_expectations=rule.acoustic_effect
            )

        elif rule.action.type == ActionType.DELETE:
            # Delete the phoneme (for complete assimilation)
            # Used for idgham without ghunnah where noon assimilates into lam/raa
            return RuleApplication(
                rule=rule,
                start_index=index,
                end_index=index,
                original_phonemes=[original_phoneme],
                modified_phonemes=[],  # Empty - phoneme deleted
                acoustic_expectations=rule.acoustic_effect
            )

        elif rule.action.type == ActionType.INSERT:
            # Insert a vowel after the consonant (for Madd Silah)
            # Used for pronoun haa (هِ/هُ) before hamza - inserts connecting vowel
            # The vowel is already in the sequence, so we just mark the prolongation
            return RuleApplication(
                rule=rule,
                start_index=index,
                end_index=index,
                original_phonemes=[original_phoneme],
                modified_phonemes=[original_phoneme],  # Keep phoneme, prolong following vowel
                acoustic_expectations=rule.acoustic_effect
            )

        return None

    def _get_phoneme(self, symbol: str) -> Optional[Phoneme]:
        """Get a phoneme by symbol from inventory."""
        if self.phoneme_inventory:
            return self.phoneme_inventory.get_by_symbol(symbol)

        # Fallback: create basic phoneme
        from .models.phoneme import PhoneticFeatures
        from .models.enums import PhonemeCategory

        return Phoneme(
            symbol=symbol,
            category=PhonemeCategory.CONSONANT,
            features=PhoneticFeatures(),
            duration_factor=1.0
        )

    def get_rules_by_category(self, category: RuleCategory) -> List[TajweedRule]:
        """Get all rules of a specific category."""
        return [r for r in self.rules if r.category == category]

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded rules."""
        return {
            'total_rules': len(self.rules),
            'rules_by_category': {
                cat.value: len(self.get_rules_by_category(cat))
                for cat in RuleCategory
            },
            'priority_range': (
                min(r.priority for r in self.rules) if self.rules else 0,
                max(r.priority for r in self.rules) if self.rules else 0
            )
        }

    def __repr__(self) -> str:
        return f"TajweedEngine(rules={len(self.rules)})"
