# Typing test scoring (version 1)

Every result carries `scoringVersion`. Change the version whenever a rule below changes, so old and new results are never mixed. The code is `static/typingtest/engine.js`, and the fixtures are `typingtest/fixtures_scoring.json`.

## Rules

| Question | Rule |
|---|---|
| What is an input unit? | One extended grapheme cluster after NFC normalization, split by `Intl.Segmenter` using the language's locale. A base letter with its vowel signs or accents is one unit. |
| Normalization | Both the target and the input are NFC normalized. Nothing else is changed: accents, vowel marks and tone marks are never removed. |
| When is IME text counted? | Only when committed, at `compositionend`. Text still being composed is not scored and does not start the timer. |
| Composition when time expires | Uncommitted text is discarded. |
| Building a unit | If the last typed unit can still become the target unit, comparing decomposed forms, it is shown as partial and not scored. Examples are `क` for `क्ष`, and `e` then `ê` for `ế` with Telex. Once the next unit is typed, it is scored as it stands. |
| Enter | Ignored unless the practice text has a line break at that point. An IME can still use it to confirm a composition. |
| Do spaces and punctuation count? | Yes. Each is one unit. |
| Corrections | Each deleted unit adds one correction. A retyped position counts as a new attempt. |
| Accuracy | Correct attempts divided by all attempts, as a percentage. A corrected mistake still lowers accuracy. |
| Unfinished text | Only typed units count. Untyped text is ignored. |
| Elapsed time | From the first committed unit to the end. A timed test always uses its full duration. It comes from a monotonic clock, so a tab switch neither pauses nor extends it. |
| CPM | Units correct in the final text, divided by elapsed minutes. |
| WPM | CPM divided by 5, labelled "5-unit WPM". It is a shared measure, not a count of natural words, so it does not compare equally across languages. |

## Settings that change scoring

| Setting | Rule |
|---|---|
| Allow Corrections off | Deleting an already scored unit is rejected, and the input is restored. |
| Stop on Error | Typing past a wrong unit is rejected until it is fixed. This turns corrections on, because a fix needs them. Rejected input is not counted as an attempt. |
| Strict Accuracy | The first wrong scored unit ends the test. |

These settings lock once a test starts and can change again after a restart.

## Practice text settings

| Setting | Rule |
|---|---|
| Difficulty | Beginner uses the shorter half of the word list, Advanced the longer half, and Intermediate all of it. Length is measured in text units. Time and Words modes only. |
| Content | Punctuation, Numbers and Capitalization add to generated text. Time and Words modes only. |
| Custom text | Options apply only if the user chooses them. Removing punctuation removes Unicode punctuation and symbols, never accents or vowel signs. |

## Worked example

250 correct units in a 60-second test give CPM 250 and WPM 50.

## Known limits

- **Different browsers may split clusters differently.** `Intl.Segmenter` depends on the ICU version, most visibly for Indic conjuncts such as `क्ष`. Stage 6 needs one fixed algorithm on the server before any result can be ranked.
- **Results are local.** Nothing here is sent to a server, so none of it is protection against cheating yet.
- **Cluster boundaries in the fixtures** were checked against Node 22 and still need native review.
