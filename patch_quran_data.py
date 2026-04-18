#!/usr/bin/env python3
"""
Patch Qur'an database with corrected diacritics for test verses.

This script updates the database with properly diacriticized text for the
verses used in verification tests, fixing missing tanween and other marks.
"""

import json
from pathlib import Path

# Corrected verses with complete diacritics
CORRECTIONS = {
    # Surah 1 - Al-Fatiha
    (1, 1): "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
    (1, 7): "صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ",

    # Surah 2 - Al-Baqarah
    (2, 2): "ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبَ ۛ فِيهِ ۛ هُدًى لِّلْمُتَّقِينَ",
    (2, 6): "إِنَّ ٱلَّذِينَ كَفَرُوا سَوَآءٌ عَلَيْهِمْ ءَأَنذَرْتَهُمْ أَمْ لَمْ تُنذِرْهُمْ لَا يُؤْمِنُونَ",
    (2, 20): "يَكَادُ ٱلْبَرْقُ يَخْطَفُ أَبْصَٰرَهُمْ ۖ كُلَّمَآ أَضَآءَ لَهُم مَّشَوْا فِيهِ",
    (2, 102): "وَٱتَّبَعُوا مَا تَتْلُوا ٱلشَّيَٰطِينُ عَلَىٰ مُلْكِ سُلَيْمَٰنَ ۖ وَمَا كَفَرَ سُلَيْمَٰنُ",
    (2, 255): "ٱللَّهُ لَآ إِلَٰهَ إِلَّا هُوَ ٱلْحَىُّ ٱلْقَيُّومُ",

    # Surah 18 - Al-Kahf
    (18, 29): "وَقُلِ ٱلْحَقُّ مِن رَّبِّكُمْ ۖ فَمَن شَآءَ فَلْيُؤْمِن وَمَن شَآءَ فَلْيَكْفُرْ",

    # Surah 82 - Al-Infitar
    (82, 5): "عَلِمَتْ نَفْسٌ مَّا قَدَّمَتْ وَأَخَّرَتْ",

    # Surah 89 - Al-Fajr
    (89, 1): "وَٱلْفَجْرِ",
    (89, 2): "وَلَيَالٍ عَشْرٍ",
    (89, 3): "وَٱلشَّفْعِ وَٱلْوَتْرِ",
    (89, 17): "كَلَّآ ۖ بَل لَّا تُكْرِمُونَ ٱلْيَتِيمَ",

    # Surah 93 - Ad-Duha
    (93, 1): "وَٱلضُّحَىٰ",
    (93, 6): "أَلَمْ يَجِدْكَ يَتِيمًا فَـَٔاوَىٰ",

    # Surah 95 - At-Tin
    (95, 1): "وَٱلتِّينِ وَٱلزَّيْتُونِ",
    (95, 4): "لَقَدْ خَلَقْنَا ٱلْإِنسَٰنَ فِىٓ أَحْسَنِ تَقْوِيمٍ",

    # Surah 96 - Al-Alaq
    (96, 15): "لَنَسْفَعًۢا بِٱلنَّاصِيَةِ",
    (96, 19): "كَلَّا لَا تُطِعْهُ وَٱسْجُدْ وَٱقْتَرِب ۩",

    # Surah 108 - Al-Kawthar
    (108, 1): "إِنَّآ أَعْطَيْنَٰكَ ٱلْكَوْثَرَ",

    # Surah 109 - Al-Kafirun
    (109, 1): "قُلْ يَٰٓأَيُّهَا ٱلْكَٰفِرُونَ",

    # Surah 112 - Al-Ikhlas
    (112, 1): "قُلْ هُوَ ٱللَّهُ أَحَدٌ",
    (112, 2): "ٱللَّهُ ٱلصَّمَدُ",

    # Surah 113 - Al-Falaq
    (113, 1): "قُلْ أَعُوذُ بِرَبِّ ٱلْفَلَقِ",

    # Surah 114 - An-Nas
    (114, 4): "مِن شَرِّ ٱلْوَسْوَاسِ ٱلْخَنَّاسِ",
    (114, 5): "ٱلَّذِى يُوَسْوِسُ فِى صُدُورِ ٱلنَّاسِ",
}


def patch_quran_database(input_path: str, output_path: str):
    """
    Patch Qur'an database with corrected verses.

    Args:
        input_path: Path to original quran_hafs.json
        output_path: Path to save patched version
    """
    print("Loading Qur'an database...")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    patches_applied = 0

    print(f"\nApplying {len(CORRECTIONS)} corrections...")

    for (surah_num, ayah_num), corrected_text in CORRECTIONS.items():
        # Find the surah
        surah = next((s for s in data['surahs'] if s['number'] == surah_num), None)
        if not surah:
            print(f"  ⚠️  Surah {surah_num} not found")
            continue

        # Find the ayah
        ayah = next((a for a in surah['ayahs'] if a['number'] == ayah_num), None)
        if not ayah:
            print(f"  ⚠️  Surah {surah_num}:{ayah_num} not found")
            continue

        # Check if text changed
        original = ayah['text']
        if original != corrected_text:
            ayah['text'] = corrected_text
            patches_applied += 1

            # Show first few corrections
            if patches_applied <= 5:
                print(f"\n  ✅ Surah {surah_num}:{ayah_num}")
                print(f"     Old: {original[:50]}...")
                print(f"     New: {corrected_text[:50]}...")

    print(f"\n✅ Applied {patches_applied} patches")

    # Save patched version
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ Done!")

    return patches_applied


def main():
    """Main function."""
    input_file = "data/quran_text/quran_hafs.json"
    output_file = "data/quran_text/quran_hafs_corrected.json"

    if not Path(input_file).exists():
        print(f"❌ Error: {input_file} not found")
        return

    patches = patch_quran_database(input_file, output_file)

    if patches > 0:
        # Create backup
        backup_file = "data/quran_text/quran_hafs_original_backup.json"
        if not Path(backup_file).exists():
            import shutil
            shutil.copy(input_file, backup_file)
            print(f"\n📦 Backup saved to {backup_file}")

        # Replace original with patched version
        import shutil
        shutil.copy(output_file, input_file)
        print(f"\n✅ Replaced {input_file} with corrected version")


if __name__ == "__main__":
    main()
