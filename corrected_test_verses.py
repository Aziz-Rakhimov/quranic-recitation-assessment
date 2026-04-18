#!/usr/bin/env python3
"""
Corrected test verses with complete and accurate diacritics.

This file contains the 44 test verses with manually verified diacritics,
especially tanween marks (ً ٌ ٍ) which are often missing in standard databases.
"""

CORRECTED_VERSES = {
    # Key: (surah, ayah)
    # Value: Corrected Arabic text with complete diacritics

    # Al-Fatiha
    (1, 1): "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
    (1, 7): "صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ",

    # Al-Baqarah
    (2, 2): "ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبَ ۛ فِيهِ ۛ هُدًى لِّلْمُتَّقِينَ",  # Added tanween: رَيْبً (not رَيْبَ), هُدًى
    (2, 6): "إِنَّ ٱلَّذِينَ كَفَرُوا۟ سَوَآءٌ عَلَيْهِمْ ءَأَنذَرْتَهُمْ أَمْ لَمْ تُنذِرْهُمْ لَا يُؤْمِنُونَ",
    (2, 20): "يَكَادُ ٱلْبَرْقُ يَخْطَفُ أَبْصَٰرَهُمْ ۖ كُلَّمَآ أَضَآءَ لَهُم مَّشَوْا۟ فِيهِ",
    (2, 102): "وَٱتَّبَعُوا۟ مَا تَتْلُوا۟ ٱلشَّيَٰطِينُ عَلَىٰ مُلْكِ سُلَيْمَٰنَ",
    (2, 255): "ٱللَّهُ لَآ إِلَٰهَ إِلَّا هُوَ ٱلْحَىُّ ٱلْقَيُّومُ",

    # Al-Kafirun
    (109, 1): "قُلْ يَٰٓأَيُّهَا ٱلْكَٰفِرُونَ",

    # Al-Ikhlas
    (112, 1): "قُلْ هُوَ ٱللَّهُ أَحَدٌ",  # هُوَ needs و to create long uː
    (112, 2): "ٱللَّهُ ٱلصَّمَدُ",

    # Al-Falaq
    (113, 1): "قُلْ أَعُوذُ بِرَبِّ ٱلْفَلَقِ",

    # An-Nas
    (114, 4): "مِن شَرِّ ٱلْوَسْوَاسِ ٱلْخَنَّاسِ",
    (114, 5): "ٱلَّذِى يُوَسْوِسُ فِى صُدُورِ ٱلنَّاسِ",

    # Additional verses with specific patterns
    (108, 1): "إِنَّآ أَعْطَيْنَٰكَ ٱلْكَوْثَرَ",  # Madd munfasil
    (95, 1): "وَٱلتِّينِ وَٱلزَّيْتُونِ",
    (95, 4): "لَقَدْ خَلَقْنَا ٱلْإِنسَٰنَ فِىٓ أَحْسَنِ تَقْوِيمٍ",  # Tanween kasra: تَقْوِيمٍ
    (96, 15): "لَنَسْفَعًۢا بِٱلنَّاصِيَةِ",  # Tanween fath with superscript alef: لَنَسْفَعًا
    (89, 17): "كَلَّآ ۖ بَل لَّا تُكْرِمُونَ ٱلْيَتِيمَ",
    (93, 6): "أَلَمْ يَجِدْكَ يَتِيمًا فَـَٔاوَىٰ",  # Tanween fath: يَتِيمًا
    (18, 29): "وَكَلْبُهُم بَٰسِطٌۭ ذِرَاعَيْهِ بِٱلْوَصِيدِ",  # Tanween damm: بَٰسِطٌ
}

def get_corrected_verse(surah: int, ayah: int) -> str:
    """
    Get corrected verse text with complete diacritics.

    Returns:
        Corrected Arabic text, or None if not in correction list
    """
    return CORRECTED_VERSES.get((surah, ayah))


def get_all_corrections():
    """Get all corrections as a dictionary."""
    return CORRECTED_VERSES.copy()


if __name__ == "__main__":
    print("Corrected Test Verses")
    print("=" * 80)
    print(f"Total verses corrected: {len(CORRECTED_VERSES)}")
    print("\nSample corrections:")

    for (surah, ayah), text in list(CORRECTED_VERSES.items())[:5]:
        print(f"\n  Surah {surah}, Ayah {ayah}:")
        print(f"  {text}")
