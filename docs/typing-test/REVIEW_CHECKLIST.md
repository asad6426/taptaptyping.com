# Human review checklist

## Content

- [ ] Native speaker reviews the word list for each of the 20 languages in `typingtest/content.py`. All are AI-drafted and unreviewed.
- [ ] Decide how Thai and Japanese practice text should be segmented. Both currently run words together.
- [ ] Decide whether Japanese should stay hiragana only for the first release.
- [ ] Native speaker reviews the four sentences for each language in `STARTER_PARAGRAPHS`. All are AI-drafted and unreviewed.
- [ ] Add more than one passage per language. There is only one today, so regular users will memorize it.
- [ ] Decide whether punctuation marks in `languages.py` are right for each language, and how Thai should handle them.

## Input

- [ ] Bengali: Avro, Bijoy and the system keyboard.
- [ ] Hindi: InScript and phonetic input.
- [ ] Japanese and Korean: real IMEs on Windows, macOS, Android and iOS.
- [ ] Vietnamese: Telex and VNI, which change letters after they are typed.
- [ ] Arabic and Urdu: rendering, caret position and mixed-direction text.
- [ ] Confirm cluster boundaries in `typingtest/fixtures_scoring.json` with native speakers.

## Before leaderboards are promoted

- [ ] Review flagged results in the admin regularly.
- [ ] Decide whether the 180 WPM and 120 WPM with 99.5% flag limits suit each language. They were chosen without real data.
- [ ] Decide whether a cookie consent tool is needed. See PRIVACY.md.
- [ ] Test on Safari, Firefox and real phones, with a screen reader.

## Before launch

- [ ] Confirm the mobile and assisted-input policy: they have separate boards today, based on what the browser reports.
- [ ] Review the FAQ and page text on each language page.
