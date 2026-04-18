"""
Script to download Qur'anic text from Tanzil.net and format it for the symbolic layer.

Downloads the Uthmani script version with diacritics (Ḥafṣ ʿan ʿĀṣim riwāyah).
"""

import json
import requests
from pathlib import Path


def download_quran_text():
    """Download Qur'anic text from Tanzil.net API."""

    # Tanzil.net API endpoint for Uthmani script with diacritics
    url = "https://api.alquran.cloud/v1/quran/quran-uthmani"

    print("Downloading Qur'anic text from Tanzil API...")
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Failed to download: {response.status_code}")

    data = response.json()

    if data['code'] != 200 or 'data' not in data:
        raise Exception("Invalid API response")

    return data['data']


def format_quran_data(raw_data):
    """Format the raw API data into our desired structure."""

    formatted = {
        "metadata": {
            "source": "AlQuran Cloud API",
            "edition": "Hafs an Asim",
            "text_type": "Uthmani with diacritics",
            "version": "1.0"
        },
        "surahs": []
    }

    for surah in raw_data['surahs']:
        surah_data = {
            "number": surah['number'],
            "name": surah['englishName'],
            "name_arabic": surah['name'],
            "revelation_type": surah['revelationType'],
            "ayahs": []
        }

        for ayah in surah['ayahs']:
            # Remove the ayah number marker (٦, ٧, etc.) from the text
            text = ayah['text']

            ayah_data = {
                "number": ayah['numberInSurah'],
                "text": text,
                "juz": ayah.get('juz', None),
                "manzil": ayah.get('manzil', None),
                "page": ayah.get('page', None)
            }

            surah_data['ayahs'].append(ayah_data)

        formatted['surahs'].append(surah_data)
        print(f"Processed Surah {surah['number']}: {surah['englishName']} ({len(surah['ayahs'])} ayahs)")

    return formatted


def save_quran_data(data, output_path):
    """Save formatted Qur'anic data to JSON file."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nSaved Qur'anic text to: {output_path}")
    print(f"Total surahs: {len(data['surahs'])}")
    print(f"Total ayahs: {sum(len(s['ayahs']) for s in data['surahs'])}")


def main():
    """Main function to download and format Qur'anic text."""

    output_path = Path(__file__).parent.parent / "data" / "quran_text" / "quran_hafs.json"

    try:
        # Download raw data
        raw_data = download_quran_text()

        # Format data
        formatted_data = format_quran_data(raw_data)

        # Save to file
        save_quran_data(formatted_data, output_path)

        print("\n✅ Successfully downloaded and formatted Qur'anic text!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
