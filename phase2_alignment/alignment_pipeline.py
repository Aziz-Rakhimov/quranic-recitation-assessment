"""
Phase 2 Alignment Pipeline — Integration Module

Orchestrates: Phase 1 (symbolic) → MFA (forced alignment) → Phase 3-ready JSON.

Usage:
    from phase2_alignment.alignment_pipeline import AlignmentPipeline

    pipeline = AlignmentPipeline()

    # Process a single verse (TextGrid must already exist)
    result = pipeline.process_verse(surah=1, ayah=3)

    # Process all verses for a surah
    results = pipeline.process_surah(surah=1, num_ayahs=7)

    # Run full pipeline: generate dict/labs, run MFA, parse results
    results = pipeline.run_full_pipeline(
        surah=1, num_ayahs=7,
        corpus_dir='phase2_alignment/corpus',
        output_dir='phase2_alignment/output'
    )
"""

import json
import os
import sys
import unicodedata
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Optional

# Add Phase 1 source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from symbolic_layer.pipeline import SymbolicLayerPipeline
from phase2_alignment.textgrid_parser import (
    parse_textgrid, parse_all_textgrids, AlignedUtterance, WordInterval, PhoneInterval
)

# Phone mapping: IPA (Phase 1) ↔ MFA Arabic acoustic model
IPA_TO_MFA = {
    'ʔ': 'Q',    # hamza (glottal stop)
    'ħ': 'H',    # ح (voiceless pharyngeal fricative)
    'ʕ': 'Hq',   # ع (voiced pharyngeal fricative)
    'ɣ': 'G',    # غ (voiced velar fricative)
    'ð': 'z',    # ذ (voiced interdental → merged with z in model)
    'θ': 's',    # ث (voiceless interdental → merged with s in model)
    'ʃ': 'C',    # ش (voiceless postalveolar fricative)
    'dʒ': 'j',   # ج (voiced postalveolar affricate → closest in model)
    'sˤ': 'S',   # ص (emphatic s)
    'dˤ': 'D',   # ض (emphatic d)
    'tˤ': 'T',   # ط (emphatic t)
    'ðˤ': 'Z',   # ظ (emphatic ð / pharyngealized dental fricative)
    'aː': 'al',  # long a
    'iː': 'il',  # long i
    'uː': 'ul',  # long u
}

MFA_TO_IPA = {v: k for k, v in IPA_TO_MFA.items()}


def mfa_phone_to_ipa(mfa_phone: str) -> str:
    """Convert MFA phone symbol back to IPA."""
    return MFA_TO_IPA.get(mfa_phone, mfa_phone)


def ipa_phone_to_mfa(ipa_phone: str) -> str:
    """Convert IPA phone symbol to MFA model phone."""
    return IPA_TO_MFA.get(ipa_phone, ipa_phone)


@dataclass
class AlignedPhone:
    """A phone with timing and both IPA/MFA representations."""
    ipa: str
    mfa: str
    start: float
    end: float
    duration_ms: float
    tajweed_rules: list[str] = field(default_factory=list)
    # Issue 3: Geminate pair info
    geminate_pair: bool = False
    geminate_total_ms: float = 0.0
    geminate_position: str = ''  # 'first' or 'second'
    # Issue 4: Verse-final silence trimming
    is_verse_final: bool = False
    verse_final_silence_trimmed: bool = False
    original_duration_ms: float = 0.0
    trimmed_duration_ms: float = 0.0
    # Issue 5 & 6: Confidence and assessment flags
    alignment_confidence: str = 'high'  # 'high', 'low', 'failed'
    skip_assessment: bool = False


@dataclass
class AlignedWord:
    """A word with timing, phonemes, and tajweed annotations."""
    text: str
    start: float
    end: float
    duration_ms: float
    phones: list[AlignedPhone] = field(default_factory=list)
    word_index: int = 0


@dataclass
class AlignedVerse:
    """Complete alignment result for one verse."""
    surah: int
    ayah: int
    text: str
    file_id: str
    duration: float
    words: list[AlignedWord] = field(default_factory=list)
    tajweed_summary: list[dict] = field(default_factory=list)
    alignment_quality: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to a plain dict for JSON serialization."""
        return {
            'surah': self.surah,
            'ayah': self.ayah,
            'text': self.text,
            'file_id': self.file_id,
            'duration': self.duration,
            'words': [
                {
                    'text': w.text,
                    'word_index': w.word_index,
                    'start': w.start,
                    'end': w.end,
                    'duration_ms': w.duration_ms,
                    'phones': [self._phone_to_dict(p) for p in w.phones],
                }
                for w in self.words
            ],
            'tajweed_summary': self.tajweed_summary,
            'alignment_quality': self.alignment_quality,
        }

    @staticmethod
    def _phone_to_dict(p: 'AlignedPhone') -> dict:
        """Convert a phone to dict, including optional enrichment fields."""
        d = {
            'ipa': p.ipa,
            'mfa': p.mfa,
            'start': p.start,
            'end': p.end,
            'duration_ms': p.duration_ms,
            'tajweed_rules': p.tajweed_rules,
            'alignment_confidence': p.alignment_confidence,
        }
        if p.skip_assessment:
            d['skip_assessment'] = True
        if p.is_verse_final:
            d['is_verse_final'] = True
        if p.verse_final_silence_trimmed:
            d['verse_final_silence_trimmed'] = True
            d['original_duration_ms'] = p.original_duration_ms
            d['trimmed_duration_ms'] = p.trimmed_duration_ms
        if p.geminate_pair:
            d['geminate_pair'] = True
            d['geminate_total_ms'] = p.geminate_total_ms
            d['geminate_position'] = p.geminate_position
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class AlignmentPipeline:
    """Integrates Phase 1 symbolic analysis with MFA forced alignment."""

    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_root = project_root
        self.phase1 = SymbolicLayerPipeline()

    def process_verse(
        self,
        surah: int,
        ayah: int,
        textgrid_path: str = None,
        output_dir: str = None,
    ) -> AlignedVerse:
        """Process a single verse: merge Phase 1 analysis with MFA alignment.

        Args:
            surah: Surah number.
            ayah: Ayah number.
            textgrid_path: Path to the TextGrid file. If None, auto-detected.
            output_dir: Directory containing TextGrid files. Used if textgrid_path is None.

        Returns:
            AlignedVerse with full timing and tajweed data.
        """
        # Resolve TextGrid path
        if textgrid_path is None:
            if output_dir is None:
                output_dir = os.path.join(self.project_root, 'phase2_alignment', 'output')
            file_id = f'{surah:03d}_{ayah:03d}'
            textgrid_path = os.path.join(output_dir, f'{file_id}.TextGrid')

        if not os.path.exists(textgrid_path):
            raise FileNotFoundError(f'TextGrid not found: {textgrid_path}')

        # Phase 1: symbolic analysis
        phase1_output = self.phase1.process_verse(surah=surah, ayah=ayah)
        ps = phase1_output.phoneme_sequence
        ann = phase1_output.annotated_sequence

        # Build per-phoneme tajweed rule index
        rule_index = self._build_rule_index(ann)

        # Phase 2: parse TextGrid
        alignment = parse_textgrid(textgrid_path)

        # Merge: match Phase 1 words to TextGrid words
        aligned_verse = self._merge(
            surah=surah,
            ayah=ayah,
            phase1_seq=ps,
            annotated_seq=ann,
            alignment=alignment,
            rule_index=rule_index,
        )

        return aligned_verse

    def process_verse_from_text(
        self,
        text: str,
        surah: int,
        ayah: int,
        textgrid_path: str = None,
        output_dir: str = None,
        file_id: str = None,
    ) -> AlignedVerse:
        """Process arbitrary text against a TextGrid (for basmalah / stripped ayah).

        Uses Phase 1's process_text() instead of process_verse().
        """
        if textgrid_path is None:
            if output_dir is None:
                output_dir = os.path.join(self.project_root, 'phase2_alignment', 'output')
            if file_id is None:
                file_id = f'{surah:03d}_{ayah:03d}'
            textgrid_path = os.path.join(output_dir, f'{file_id}.TextGrid')

        if not os.path.exists(textgrid_path):
            raise FileNotFoundError(f'TextGrid not found: {textgrid_path}')

        # Phase 1: process raw text
        phase1_output = self.phase1.process_text(text, surah=surah, ayah=ayah)
        ps = phase1_output.phoneme_sequence
        ann = phase1_output.annotated_sequence
        rule_index = self._build_rule_index(ann)

        # Parse TextGrid
        alignment = parse_textgrid(textgrid_path)

        # Merge
        return self._merge(
            surah=surah,
            ayah=ayah,
            phase1_seq=ps,
            annotated_seq=ann,
            alignment=alignment,
            rule_index=rule_index,
        )

    def process_verse_segments(
        self,
        surah: int,
        ayah: int,
        segment_infos: list,
        output_dir: str,
        original_duration: float = None,
    ) -> AlignedVerse:
        """Process a segmented verse by merging multiple TextGrids.

        Args:
            segment_infos: list of {'file_id': str, 'offset': float, 'duration': float}
            output_dir: Directory containing segment TextGrid files.
            original_duration: Total duration of the original unsplit audio.
        """
        # Phase 1 on full verse text
        phase1_output = self.phase1.process_verse(surah=surah, ayah=ayah)
        ps = phase1_output.phoneme_sequence
        ann = phase1_output.annotated_sequence
        rule_index = self._build_rule_index(ann)

        # Parse each segment TextGrid and adjust timestamps
        merged_words = []
        for seg in segment_infos:
            tg_path = os.path.join(output_dir, f'{seg["file_id"]}.TextGrid')
            if not os.path.exists(tg_path):
                print(f'  WARNING: Segment TextGrid not found: {tg_path}')
                continue
            tg = parse_textgrid(tg_path)
            offset = seg['offset']
            padding = seg.get('padding', 0.0)
            for word in tg.words:
                # Shift: subtract padding (MFA sees padded audio),
                # then add real-world offset
                word.start = word.start - padding + offset
                word.end = word.end - padding + offset
                for phone in word.phones:
                    phone.start = phone.start - padding + offset
                    phone.end = phone.end - padding + offset
                merged_words.append(word)

        # Build synthetic AlignedUtterance
        if original_duration is None:
            seg_last = segment_infos[-1]
            original_duration = seg_last['offset'] + seg_last['duration']

        file_id = f'{surah:03d}_{ayah:03d}'
        synthetic = AlignedUtterance(
            file_id=file_id,
            duration=original_duration,
            words=merged_words,
        )

        return self._merge(
            surah=surah,
            ayah=ayah,
            phase1_seq=ps,
            annotated_seq=ann,
            alignment=synthetic,
            rule_index=rule_index,
        )

    def process_verse_segments_from_text(
        self,
        text: str,
        surah: int,
        ayah: int,
        segment_infos: list,
        output_dir: str,
        original_duration: float = None,
    ) -> AlignedVerse:
        """Process segmented verse using raw text (for stripped ayah 1 content)."""
        phase1_output = self.phase1.process_text(text, surah=surah, ayah=ayah)
        ps = phase1_output.phoneme_sequence
        ann = phase1_output.annotated_sequence
        rule_index = self._build_rule_index(ann)

        merged_words = []
        for seg in segment_infos:
            tg_path = os.path.join(output_dir, f'{seg["file_id"]}.TextGrid')
            if not os.path.exists(tg_path):
                print(f'  WARNING: Segment TextGrid not found: {tg_path}')
                continue
            tg = parse_textgrid(tg_path)
            offset = seg['offset']
            padding = seg.get('padding', 0.0)
            for word in tg.words:
                word.start = word.start - padding + offset
                word.end = word.end - padding + offset
                for phone in word.phones:
                    phone.start = phone.start - padding + offset
                    phone.end = phone.end - padding + offset
                merged_words.append(word)

        if original_duration is None:
            seg_last = segment_infos[-1]
            original_duration = seg_last['offset'] + seg_last['duration']

        file_id = f'{surah:03d}_{ayah:03d}'
        synthetic = AlignedUtterance(
            file_id=file_id,
            duration=original_duration,
            words=merged_words,
        )

        return self._merge(
            surah=surah,
            ayah=ayah,
            phase1_seq=ps,
            annotated_seq=ann,
            alignment=synthetic,
            rule_index=rule_index,
        )

    def process_surah(
        self,
        surah: int,
        num_ayahs: int,
        output_dir: str = None,
    ) -> list[AlignedVerse]:
        """Process all ayahs of a surah."""
        results = []
        for ayah in range(1, num_ayahs + 1):
            try:
                result = self.process_verse(surah=surah, ayah=ayah, output_dir=output_dir)
                results.append(result)
            except Exception as e:
                print(f'  Error processing {surah}:{ayah}: {e}')
        return results

    def run_full_pipeline(
        self,
        surah: int,
        num_ayahs: int,
        corpus_dir: str,
        dict_path: str = None,
        output_dir: str = None,
        acoustic_model: str = 'arabic',
    ) -> list[AlignedVerse]:
        """Run the complete pipeline: generate dict → generate labs → MFA → parse.

        Requires: WAV files in corpus_dir, conda 'aligner' env with MFA.
        """
        if dict_path is None:
            dict_path = os.path.join(self.project_root, 'phase2_alignment', 'dictionary',
                                     f'surah_{surah}.dict')
        if output_dir is None:
            output_dir = os.path.join(self.project_root, 'phase2_alignment', 'output')

        os.makedirs(os.path.dirname(dict_path), exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Generate dictionary
        print(f'[1/4] Generating dictionary for surah {surah}...')
        self._generate_dictionary(surah, num_ayahs, dict_path)

        # Step 2: Generate .lab files
        print(f'[2/4] Generating .lab files...')
        self._generate_labs(surah, num_ayahs, corpus_dir)

        # Step 3: Run MFA alignment
        print(f'[3/4] Running MFA alignment...')
        self._run_mfa(corpus_dir, dict_path, acoustic_model, output_dir)

        # Step 4: Process all verses
        print(f'[4/4] Merging Phase 1 + alignment data...')
        return self.process_surah(surah, num_ayahs, output_dir)

    def _build_rule_index(self, annotated_seq) -> dict[int, list[str]]:
        """Build index: phoneme position → list of tajweed rule names."""
        index = {}
        for rule_app in annotated_seq.rule_applications:
            rule_name = rule_app.rule.name if hasattr(rule_app.rule, 'name') else str(rule_app.rule)
            for pos in range(rule_app.start_index, rule_app.end_index + 1):
                if pos not in index:
                    index[pos] = []
                index[pos].append(rule_name)
        return index

    def _merge(
        self,
        surah: int,
        ayah: int,
        phase1_seq,
        annotated_seq,
        alignment: AlignedUtterance,
        rule_index: dict[int, list[str]],
    ) -> AlignedVerse:
        """Merge Phase 1 phoneme sequence with MFA alignment timestamps."""
        word_texts = phase1_seq.word_texts
        word_boundaries = phase1_seq.word_boundaries  # indices where words split
        ipa_phonemes = [p.symbol for p in phase1_seq.phonemes]

        # Split IPA phonemes into per-word lists using word_boundaries
        ipa_by_word = []
        positions_by_word = []
        start = 0
        for boundary in word_boundaries:
            ipa_by_word.append(ipa_phonemes[start:boundary])
            positions_by_word.append(list(range(start, boundary)))
            start = boundary
        ipa_by_word.append(ipa_phonemes[start:])
        positions_by_word.append(list(range(start, len(ipa_phonemes))))

        # Match Phase 1 words to TextGrid words (NFC-normalized matching)
        aligned_words = []
        tg_word_idx = 0

        for word_idx, (word_text, ipa_phones, positions) in enumerate(
            zip(word_texts, ipa_by_word, positions_by_word)
        ):
            word_nfc = unicodedata.normalize('NFC', word_text)

            # Find matching TextGrid word
            tg_word = None
            while tg_word_idx < len(alignment.words):
                tg_nfc = unicodedata.normalize('NFC', alignment.words[tg_word_idx].word)
                if tg_nfc == word_nfc:
                    tg_word = alignment.words[tg_word_idx]
                    tg_word_idx += 1
                    break
                tg_word_idx += 1

            if tg_word is None:
                print(f'  WARNING: No TextGrid match for word "{word_text}" in {alignment.file_id}')
                continue

            # Build aligned phones
            # Handle mismatched phone counts between Phase 1 and TextGrid.
            # When counts differ, align from the END (suffix matching):
            #   - TG has more phones → extra leading TG phones are hamzat al-wasl prefix
            #   - Phase 1 has more phones → Phase 1's leading phones were elided in MFA
            aligned_phones = []
            tg_phones = tg_word.phones
            offset = len(tg_phones) - len(ipa_phones)

            if offset >= 0:
                # TextGrid has more or equal phones — skip leading TG phones
                tg_start = offset
                ipa_start = 0
            else:
                # Phase 1 has more phones — skip leading IPA phones (elided hamzat al-wasl)
                tg_start = 0
                ipa_start = -offset

            num_to_align = min(len(ipa_phones) - ipa_start, len(tg_phones) - tg_start)
            for i in range(num_to_align):
                ipa = ipa_phones[ipa_start + i]
                pos = positions[ipa_start + i]
                tg_phone = tg_phones[tg_start + i]
                rules = rule_index.get(pos, [])
                aligned_phones.append(AlignedPhone(
                    ipa=ipa,
                    mfa=tg_phone.phone,
                    start=round(tg_phone.start, 4),
                    end=round(tg_phone.end, 4),
                    duration_ms=round(tg_phone.duration * 1000, 1),
                    tajweed_rules=rules,
                ))

            aligned_words.append(AlignedWord(
                text=word_text,
                start=round(tg_word.start, 4),
                end=round(tg_word.end, 4),
                duration_ms=round(tg_word.duration * 1000, 1),
                phones=aligned_phones,
                word_index=word_idx,
            ))

        # Build tajweed summary
        tajweed_summary = []
        for rule_app in annotated_seq.rule_applications:
            rule_name = rule_app.rule.name if hasattr(rule_app.rule, 'name') else str(rule_app.rule)
            tajweed_summary.append({
                'rule': rule_name,
                'position': rule_app.start_index,
                'confidence': rule_app.confidence,
            })

        # Compute quality metrics
        total_phones_expected = len(ipa_phonemes)
        total_phones_aligned = sum(len(w.phones) for w in aligned_words)
        quality = {
            'words_expected': len(word_texts),
            'words_aligned': len(aligned_words),
            'phones_expected': total_phones_expected,
            'phones_aligned': total_phones_aligned,
            'coverage': round(total_phones_aligned / total_phones_expected, 4)
                        if total_phones_expected > 0 else 0.0,
        }

        verse = AlignedVerse(
            surah=surah,
            ayah=ayah,
            text=phase1_seq.original_text,
            file_id=alignment.file_id,
            duration=round(alignment.duration, 4),
            words=aligned_words,
            tajweed_summary=tajweed_summary,
            alignment_quality=quality,
        )

        # Post-processing enrichment (Issues 3-6)
        self._enrich_geminates(verse)
        self._enrich_verse_final(verse)
        self._enrich_spn(verse)
        self._enrich_confidence(verse)

        return verse

    # ── Post-processing enrichment methods (Issues 3-6) ──

    SHADDAH_RULES = {
        'ghunnah_mushaddadah_noon', 'ghunnah_mushaddadah_meem',
        'qalqalah_with_shaddah',
    }

    # Lossy MFA mappings where IPA phone differs acoustically from MFA phone
    LOSSY_IPA = {'ð', 'θ', 'dʒ'}

    def _enrich_geminates(self, verse: AlignedVerse):
        """Issue 3: Detect geminate pairs and add merged duration info."""
        for word in verse.words:
            phones = word.phones
            for i in range(len(phones) - 1):
                p1, p2 = phones[i], phones[i + 1]
                if p1.ipa != p2.ipa:
                    continue
                # Check: is this a consonant pair? (vowels aː/iː/uː are not geminates)
                if p1.ipa in ('a', 'i', 'u', 'aː', 'iː', 'uː'):
                    continue
                # It's a geminate: two consecutive identical consonants
                total = round(p1.duration_ms + p2.duration_ms, 1)
                p1.geminate_pair = True
                p1.geminate_total_ms = total
                p1.geminate_position = 'first'
                p2.geminate_pair = True
                p2.geminate_total_ms = total
                p2.geminate_position = 'second'

    def _enrich_verse_final(self, verse: AlignedVerse):
        """Issue 4: Mark verse-final phone and trim absorbed silence."""
        all_phones = [p for w in verse.words for p in w.phones]
        if not all_phones:
            return

        last = all_phones[-1]
        last.is_verse_final = True

        # Compute average phone duration (excluding the last phone)
        if len(all_phones) > 1:
            avg_dur = sum(p.duration_ms for p in all_phones[:-1]) / (len(all_phones) - 1)
        else:
            avg_dur = last.duration_ms

        # If last phone is > 3x average, trim it
        if last.duration_ms > avg_dur * 3 and avg_dur > 0:
            last.verse_final_silence_trimmed = True
            last.original_duration_ms = last.duration_ms
            last.trimmed_duration_ms = round(avg_dur, 1)
            last.duration_ms = round(avg_dur, 1)

    def _enrich_spn(self, verse: AlignedVerse):
        """Issue 5: Mark spn (spoken noise) phones and flag neighbors."""
        words = verse.words
        spn_word_indices = set()

        # First pass: find spn words
        for wi, word in enumerate(words):
            for phone in word.phones:
                if phone.mfa == 'spn':
                    phone.alignment_confidence = 'failed'
                    phone.skip_assessment = True
                    spn_word_indices.add(wi)

        # Second pass: flag neighboring words as low confidence
        for spn_idx in spn_word_indices:
            for neighbor_idx in (spn_idx - 1, spn_idx + 1):
                if 0 <= neighbor_idx < len(words) and neighbor_idx not in spn_word_indices:
                    for phone in words[neighbor_idx].phones:
                        if phone.alignment_confidence != 'failed':
                            phone.alignment_confidence = 'low'

    def _enrich_confidence(self, verse: AlignedVerse):
        """Issue 6: Set alignment_confidence on all phones.

        Rules (applied in order, first match wins):
          - 'failed' if mfa == 'spn' (already set by _enrich_spn)
          - 'low' if neighbor of spn word (already set by _enrich_spn)
          - 'low' if duration_ms == 30 (acoustic model floor)
          - 'low' if verse_final_silence_trimmed
          - 'low' if IPA is a lossy mapping (ð, θ, dʒ)
          - 'high' otherwise
        """
        for word in verse.words:
            for phone in word.phones:
                # Skip phones already set by _enrich_spn
                if phone.alignment_confidence in ('failed', 'low'):
                    continue
                if abs(phone.duration_ms - 30.0) < 0.5:
                    phone.alignment_confidence = 'low'
                elif phone.verse_final_silence_trimmed:
                    phone.alignment_confidence = 'low'
                elif phone.ipa in self.LOSSY_IPA:
                    phone.alignment_confidence = 'low'
                # else: stays 'high' (default)

    def _generate_dictionary(self, surah: int, num_ayahs: int, dict_path: str):
        """Generate MFA dictionary from Phase 1 pipeline.

        Supports multiple pronunciations per word (e.g. hamzat al-wasl
        pronounced verse-initially but elided mid-verse).
        """
        all_entries: dict[str, set[str]] = {}
        for ayah_num in range(1, num_ayahs + 1):
            output = self.phase1.process_verse(surah=surah, ayah=ayah_num)
            for line in output.to_mfa_dict().strip().split('\n'):
                if '\t' in line:
                    word, phonemes = line.split('\t', 1)
                    word = unicodedata.normalize('NFC', word.strip())
                    phonemes = phonemes.strip()
                    if word and phonemes:
                        converted = ' '.join(
                            IPA_TO_MFA.get(p, p) for p in phonemes.split()
                        )
                        if word not in all_entries:
                            all_entries[word] = set()
                        all_entries[word].add(converted)

        os.makedirs(os.path.dirname(dict_path), exist_ok=True)
        with open(dict_path, 'w', encoding='utf-8') as f:
            for word in sorted(all_entries.keys()):
                for phonemes in sorted(all_entries[word]):
                    f.write(f'{word}\t{phonemes}\n')
        total = sum(len(v) for v in all_entries.values())
        print(f'  Dictionary: {len(all_entries)} words, {total} variants → {dict_path}')

    def _generate_labs(self, surah: int, num_ayahs: int, corpus_dir: str):
        """Generate .lab files for MFA from quran_hafs.json."""
        quran_json = os.path.join(self.project_root, 'data', 'quran_text', 'quran_hafs.json')
        with open(quran_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        lookup = {}
        for s in data['surahs']:
            for a in s['ayahs']:
                lookup[(s['number'], a['number'])] = a['text']

        count = 0
        for ayah_num in range(1, num_ayahs + 1):
            key = (surah, ayah_num)
            if key not in lookup:
                print(f'  WARNING: surah {surah}, ayah {ayah_num} not in JSON')
                continue
            file_id = f'{surah:03d}_{ayah_num:03d}'
            lab_path = os.path.join(corpus_dir, f'{file_id}.lab')
            text = unicodedata.normalize('NFC', lookup[key])
            # Strip kashida and waqf signs to match Phase 1 output
            text = text.replace('\u0640', '')
            WAQF = set('\u06D6\u06D7\u06D8\u06D9\u06DA\u06DB\u06DC\u06DD\u06DE\u06DF\u06E0\u06E2\u06ED')
            text = ''.join(c for c in text if c not in WAQF)
            with open(lab_path, 'w', encoding='utf-8') as f:
                f.write(text)
            count += 1
        print(f'  Generated {count} .lab files')

    def _run_mfa(self, corpus_dir: str, dict_path: str, acoustic_model: str, output_dir: str):
        """Run MFA alignment (requires conda 'aligner' environment)."""
        cmd = [
            'mfa', 'align',
            corpus_dir, dict_path, acoustic_model, output_dir,
            '--clean'
        ]
        print(f'  Running: {" ".join(cmd)}')
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f'MFA alignment failed:\n{result.stderr}')
        print(f'  MFA alignment complete')


def export_surah_json(results: list[AlignedVerse], output_path: str):
    """Export all aligned verses to a single JSON file."""
    data = {
        'surah': results[0].surah if results else 0,
        'num_ayahs': len(results),
        'verses': [r.to_dict() for r in results],
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Exported {len(results)} verses to {output_path}')


if __name__ == '__main__':
    pipeline = AlignmentPipeline()

    # Process all 7 ayahs of Al-Fatiha
    results = pipeline.process_surah(surah=1, num_ayahs=7)

    # Print summary
    for verse in results:
        q = verse.alignment_quality
        print(f'\nAyah {verse.ayah}: {verse.text}')
        print(f'  Duration: {verse.duration:.2f}s | '
              f'Words: {q["words_aligned"]}/{q["words_expected"]} | '
              f'Phones: {q["phones_aligned"]}/{q["phones_expected"]} | '
              f'Coverage: {q["coverage"]:.0%}')
        for w in verse.words:
            print(f'  [{w.start:.2f}-{w.end:.2f}] {w.text}')
            for p in w.phones:
                rules = f' ← {", ".join(p.tajweed_rules)}' if p.tajweed_rules else ''
                print(f'    [{p.start:.2f}-{p.end:.2f}] {p.ipa} ({p.mfa}) '
                      f'{p.duration_ms:.0f}ms{rules}')

    # Export to JSON
    output_path = os.path.join(
        os.path.dirname(__file__), 'output', 'al_fatiha_aligned.json'
    )
    export_surah_json(results, output_path)
