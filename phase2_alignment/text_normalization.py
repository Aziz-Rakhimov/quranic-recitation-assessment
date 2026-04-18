"""
Arabic text normalization for word-level comparison.

Strips diacritics, normalizes letter variants, and removes non-Arabic characters
so that two renderings of the same word (e.g. diacritized Uthmani vs. plain Whisper
output) can be compared reliably.
"""

import re


# ---------------------------------------------------------------------------
# 1. Diacritics (harakat) to strip
#    U+0610–U+061A : Quranic annotation signs
#    U+064B–U+065F : Standard Arabic diacritics
#      (fatha, damma, kasra, sukun, shadda, tanwin, etc.)
#    U+0670         : SUPERSCRIPT ALEF (common in Uthmani script)
# ---------------------------------------------------------------------------
_DIACRITICS_RE = re.compile(r'[\u0610-\u061A\u064B-\u065F\u0670]')

# ---------------------------------------------------------------------------
# 2. Alef variant mapping  →  plain alef (U+0627)
# ---------------------------------------------------------------------------
_ALEF_VARIANTS = {
    '\u0623': '\u0627',  # أ  ALEF WITH HAMZA ABOVE
    '\u0625': '\u0627',  # إ  ALEF WITH HAMZA BELOW
    '\u0622': '\u0627',  # آ  ALEF WITH MADDA ABOVE
    '\u0671': '\u0627',  # ٱ  ALEF WASLA
    '\u0675': '\u0627',  # ٵ  HIGH HAMZA ALEF
}
_ALEF_RE = re.compile(r'[\u0623\u0625\u0622\u0671\u0675]')

# ---------------------------------------------------------------------------
# 3. Taa marbuta  →  haa
# ---------------------------------------------------------------------------
_TAA_MARBUTA = '\u0629'   # ة
_HAA          = '\u0647'   # ه

# ---------------------------------------------------------------------------
# 4. Alef maqsura  →  yaa
# ---------------------------------------------------------------------------
_ALEF_MAQSURA = '\u0649'  # ى
_YAA           = '\u064A'  # ي

# ---------------------------------------------------------------------------
# 5. Tatweel / kashida
# ---------------------------------------------------------------------------
_TATWEEL = '\u0640'  # ـ

# ---------------------------------------------------------------------------
# 6. Non-Arabic filter — keep only U+0600–U+06FF and whitespace
# ---------------------------------------------------------------------------
_NON_ARABIC_RE = re.compile(r'[^\u0600-\u06FF\s]')


def normalize(text: str) -> str:
    """Apply all Arabic normalization steps and return the cleaned string."""

    # 1. Strip diacritics
    text = _DIACRITICS_RE.sub('', text)

    # 2. Normalize alef variants
    text = _ALEF_RE.sub(lambda m: _ALEF_VARIANTS[m.group()], text)

    # 3. Taa marbuta → haa
    text = text.replace(_TAA_MARBUTA, _HAA)

    # 4. Alef maqsura → yaa
    text = text.replace(_ALEF_MAQSURA, _YAA)

    # 5. Strip tatweel
    text = text.replace(_TATWEEL, '')

    # 6. Strip non-Arabic characters
    text = _NON_ARABIC_RE.sub('', text)

    return text


# ===================================================================
# Quick manual verification
# ===================================================================
if __name__ == '__main__':

    tests = [
        (
            'Diacritics (harakat)',
            'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ',
        ),
        (
            'Alef variants (أ إ آ ٱ)',
            'أحمد إبراهيم آمن ٱلرحمن',
        ),
        (
            'Taa marbuta (ة → ه)',
            'رحمة بسملة فاتحة',
        ),
        (
            'Alef maqsura (ى → ي)',
            'موسى عيسى هدى',
        ),
        (
            'Tatweel / kashida',
            'الرّحمـــن الرّحيـــم',
        ),
        (
            'Non-Arabic characters',
            'سورة123 الفاتحة — verse (1)',
        ),
        (
            'Combined',
            'بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ',
        ),
    ]

    for label, sample in tests:
        result = normalize(sample)
        print(f'--- {label} ---')
        print(f'  before: {sample}')
        print(f'  after:  {result}')
        print()
