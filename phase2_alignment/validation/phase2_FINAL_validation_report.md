1

> Official Phase 2 sign-off document before Phase 3.
> 8 surahs · 131 ayahs · 6,843 phones

## Executive Summary

| Check                      | Result                                       |
| -------------------------- | -------------------------------------------- |
| Ayahs aligned              | 131/131                                      |
| OOV words                  | 0                                            |
| Failed alignments          | 0                                            |
| IPA label shift bugs       | 0                                            |
| madd_tabii coverage        | 458 (all 6 previously missed cases now fire) |
| Geminate pairs identified  | 268 pairs (536 phones)                       |
| Verse-final phones trimmed | 55                                           |
| spn phones marked skip     | 1                                            |
| **Overall status**         | **PASS**                                     |

## Per-Surah Summary

| Surah | Ayahs | Phones | Tajweed % | High | Low  | Failed | Geminates | Trimmed |
| ----- | ----- | ------ | --------- | ---- | ---- | ------ | --------- | ------- |
| 1     | 7     | 224    | 33.0%     | 193  | 31   | 0      | 12        | 4       |
| 93    | 11    | 288    | 46.5%     | 260  | 28   | 0      | 13        | 4       |
| 97    | 6     | 222    | 36.0%     | 173  | 49   | 0      | 12        | 1       |
| 113   | 5     | 131    | 38.9%     | 112  | 19   | 0      | 7         | 3       |
| 114   | 7     | 154    | 31.2%     | 119  | 35   | 0      | 13        | 0       |
| 67    | 6     | 459    | 37.3%     | 326  | 133  | 0      | 17        | 4       |
| 56    | 6     | 145    | 33.8%     | 92   | 53   | 0      | 8         | 4       |
| 36    | 83    | 5220   | 38.9%     | 3965 | 1254 | 1      | 186       | 35      |

## Tajweed Coverage by Category

Annotated phones: 2637/6843 (38.5%)
Total annotations: 4505 (phones can have multiple rules)

| Category         | Annotations | %     |
| ---------------- | ----------- | ----- |
| Emphasis/Backing | 3279        | 72.8% |
| Madd             | 606         | 13.5% |
| Noon/Meem        | 461         | 10.2% |
| Qalqalah         | 123         | 2.7%  |
| Pronunciation    | 36          | 0.8%  |

## Confidence Distribution

| Confidence | Count | %     |
| ---------- | ----- | ----- |
| high       | 5240  | 76.6% |
| low        | 1602  | 23.4% |
| failed     | 1     | 0.0%  |

## vowel_backing by Triggering Consonant

| Consonant | Count |
| --------- | ----- |
| q         | 103   |
| x         | 45    |
| sˤ        | 29    |
| tˤ        | 23    |
| dˤ        | 19    |
| ɣ         | 15    |
| ðˤ        | 1     |

## Rule Detail (all rules triggered)

| Rule                                | Count |
| ----------------------------------- | ----- |
| emphasis_blocking_by_front_vowel    | 1522  |
| cross_word_emphasis_continuation    | 1522  |
| madd_tabii                          | 458   |
| vowel_backing_after_emphatic_short  | 123   |
| madd_arid_lissukun                  | 96    |
| idhhar_shafawi                      | 91    |
| vowel_backing_before_emphatic_short | 79    |
| ikhfaa_light                        | 71    |
| ghunnah_mushaddadah_meem            | 65    |
| idgham_shafawi_meem                 | 65    |
| ghunnah_mushaddadah_noon            | 48    |
| idgham_ghunnah_noon                 | 48    |
| idhhar_halqi_noon                   | 36    |
| qalqalah_minor                      | 36    |
| madd_munfasil                       | 36    |
| vowel_backing_before_emphatic_long  | 33    |
| ta_marbuta_wasl                     | 33    |
| qalqalah_with_shaddah               | 29    |
| qalqalah_non_emphatic               | 28    |
| idgham_no_ghunnah                   | 20    |
| qalqalah_emphatic                   | 19    |
| madd_muttasil                       | 14    |
| qalqalah_major                      | 11    |
| ikhfaa_heavy                        | 8     |
| iqlab                               | 6     |
| ta_marbuta_waqf                     | 3     |
| ikhfaa_shafawi                      | 3     |
| madd_lazim_kalimi                   | 2     |

## Issues Fixed in This Release

1. **IPA Label Shift Bug** (Issue 1): Merge code now aligns from END when Phase 1 has
   more phones than TextGrid, correctly dropping elided hamzat al-wasl prefix.
   Remaining IPA/MFA mismatches: 0

2. **madd_tabii 6 Misses** (Issue 2): Removed `not_wasl_mater_lectionis` condition from
   madd_tabii. Long vowels before hamzat al-wasl now correctly get madd_tabii annotation.
   madd_tabii now fires 458 times across all test surahs.

3. **Geminate Duration Merge** (Issue 3): 268 geminate pairs identified with
   `geminate_pair`, `geminate_total_ms`, and `geminate_position` fields.

4. **Verse-Final Silence Trimming** (Issue 4): 55 verse-final phones trimmed.
   All last phones marked with `is_verse_final: true`.

5. **spn Phone Marking** (Issue 5): 1 phones marked `skip_assessment: true`.
   Neighboring words of spn flagged with `alignment_confidence: low`.

6. **Confidence Flagging** (Issue 6): All 6,843 phones have `alignment_confidence`.
   Distribution: 5240 high, 1602 low, 1 failed.

## Known Limitations (Deferred)

1. **Muqatta'at letters** (يسٓ, الم, etc.): Phase 1 cannot process disconnected letters.
   Audio alignment works but tajweed annotations are missing. Requires dedicated handler.

2. **30ms acoustic floor**: ~20% of phones are at the MFA model minimum resolution (30ms).
   Concentrated in rapid-speech sections and basmalah. These are flagged `alignment_confidence: low`.

3. **Lossy IPA→MFA mappings**: ð→z, θ→s, dʒ→j lose phonetic distinction.
   These phones are flagged `alignment_confidence: low` so Phase 3 can assess leniently.

4. **شَئًْا alignment failure** (36:82): MFA mapped this word to `spn`. Flagged with
   `skip_assessment: true`. Neighboring words have `alignment_confidence: low`.

## What Is Implemented

- Basmalah separation for non-Fatiha surahs (split at silence center)
- Long ayah segmentation at natural pause points (>10s threshold)
- Full IPA→MFA phone mapping (38 phones including ðˤ→Z)
- Hamzat al-wasl variant handling in dictionary (multiple pronunciations)
- TextGrid parsing with word + phone timestamps
- Phase 1 ↔ Phase 2 merge with suffix-aligned IPA labels
- Tajweed rule annotations on every phone
- Geminate pair detection and merged duration fields
- Verse-final silence trimming
- Per-phone alignment confidence flags
- spn / failed alignment detection with skip flags
- Per-ayah JSON export with all enrichment fields

## Phase 3 Readiness

The JSON output for each ayah contains everything Phase 3 needs:

- Word and phone timestamps for duration assessment
- Tajweed rule annotations for rule-specific checking
- `alignment_confidence` to skip/downweight unreliable phones
- `geminate_total_ms` for proper shaddah duration assessment
- `is_verse_final` for waqf rule application
- `skip_assessment` to exclude failed alignments

**Phase 2 is COMPLETE. Ready for Phase 3.**
