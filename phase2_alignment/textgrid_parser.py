"""
TextGrid parser for MFA alignment output.

Parses Praat TextGrid files and extracts word-level and phone-level
timestamps, grouping phones under their parent words.
"""

import re
from dataclasses import dataclass, field


@dataclass
class PhoneInterval:
    """A single phone with its time boundaries."""
    phone: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 4)


@dataclass
class WordInterval:
    """A word with its time boundaries and constituent phones."""
    word: str
    start: float
    end: float
    phones: list[PhoneInterval] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 4)


@dataclass
class AlignedUtterance:
    """Complete alignment for one utterance (one audio file)."""
    file_id: str  # e.g. "001_001"
    duration: float
    words: list[WordInterval] = field(default_factory=list)

    @property
    def num_words(self) -> int:
        return len(self.words)

    @property
    def num_phones(self) -> int:
        return sum(len(w.phones) for w in self.words)


def parse_textgrid(filepath: str) -> AlignedUtterance:
    """Parse a Praat TextGrid file into an AlignedUtterance.

    Args:
        filepath: Path to the .TextGrid file.

    Returns:
        AlignedUtterance with word and phone intervals.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract file_id from filename
    import os
    file_id = os.path.splitext(os.path.basename(filepath))[0]

    # Get total duration
    xmax_match = re.search(r'^xmax = ([\d.]+)', content, re.MULTILINE)
    total_duration = float(xmax_match.group(1)) if xmax_match else 0.0

    # Split into tiers
    tier_pattern = r'item \[\d+\]:\s*class = "IntervalTier"\s*name = "(\w+)".*?(?=item \[\d+\]:|$)'
    tiers = re.findall(tier_pattern, content, re.DOTALL)

    # Parse intervals from each tier
    words_intervals = []
    phones_intervals = []

    # Parse word tier
    word_tier_match = re.search(
        r'name = "words".*?intervals: size = \d+(.*?)(?=item \[\d+\]:|$)',
        content, re.DOTALL
    )
    if word_tier_match:
        words_intervals = _parse_intervals(word_tier_match.group(1))

    # Parse phone tier
    phone_tier_match = re.search(
        r'name = "phones".*?intervals: size = \d+(.*?)$',
        content, re.DOTALL
    )
    if phone_tier_match:
        phones_intervals = _parse_intervals(phone_tier_match.group(1))

    # Build word intervals with grouped phones
    words = []
    phone_idx = 0

    for w_start, w_end, w_text in words_intervals:
        if not w_text:  # skip silence intervals
            # Advance phone index past silence phones
            while phone_idx < len(phones_intervals):
                p_start, p_end, p_text = phones_intervals[phone_idx]
                if p_start >= w_end:
                    break
                phone_idx += 1
            continue

        word = WordInterval(word=w_text, start=w_start, end=w_end)

        # Collect phones that fall within this word's boundaries
        while phone_idx < len(phones_intervals):
            p_start, p_end, p_text = phones_intervals[phone_idx]
            if p_start >= w_end:
                break
            if p_text:  # skip empty/silence phones
                word.phones.append(PhoneInterval(
                    phone=p_text, start=p_start, end=p_end
                ))
            phone_idx += 1

        words.append(word)

    return AlignedUtterance(
        file_id=file_id,
        duration=total_duration,
        words=words
    )


def _parse_intervals(text: str) -> list[tuple[float, float, str]]:
    """Extract (xmin, xmax, text) tuples from TextGrid interval block."""
    pattern = r'xmin = ([\d.]+)\s*\n\s*xmax = ([\d.]+)\s*\n\s*text = "(.*?)"'
    matches = re.findall(pattern, text)
    return [(float(m[0]), float(m[1]), m[2]) for m in matches]


def parse_all_textgrids(output_dir: str) -> list[AlignedUtterance]:
    """Parse all TextGrid files in a directory.

    Args:
        output_dir: Directory containing .TextGrid files.

    Returns:
        List of AlignedUtterance objects, sorted by file_id.
    """
    import os
    utterances = []
    for fname in sorted(os.listdir(output_dir)):
        if fname.endswith('.TextGrid'):
            filepath = os.path.join(output_dir, fname)
            utterances.append(parse_textgrid(filepath))
    return utterances


if __name__ == '__main__':
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else 'phase2_alignment/output'
    utterances = parse_all_textgrids(output_dir)

    for utt in utterances:
        print(f"\n{'='*60}")
        print(f"File: {utt.file_id} | Duration: {utt.duration:.2f}s | "
              f"Words: {utt.num_words} | Phones: {utt.num_phones}")
        print(f"{'='*60}")
        for word in utt.words:
            print(f"  [{word.start:.2f} - {word.end:.2f}] {word.word} "
                  f"({word.duration:.2f}s, {len(word.phones)} phones)")
            for phone in word.phones:
                print(f"    [{phone.start:.2f} - {phone.end:.2f}] "
                      f"{phone.phone} ({phone.duration*1000:.0f}ms)")
