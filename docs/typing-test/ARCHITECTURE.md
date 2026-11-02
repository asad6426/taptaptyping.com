# Multilingual typing test: architecture and status

## Decisions from the audit (Stage 1)

| Topic | Decision | Reason |
|---|---|---|
| Framework | Keep Django, not Next.js | The brief says to use the existing project. |
| Database | Keep SQLite for now | It is what production runs. Its write limits should be reviewed before public leaderboards launch. |
| Accounts | Reuse `accounts` and allauth | Sign-in already works. |
| Code location | New `typingtest` app | The existing `/taptap/`, lessons and ranking stay untouched. |
| Language list | `typingtest/languages.py` | Routes, selector, metadata and links are generated from it. |
| Routes | No trailing slash, as in the brief | `/x/` would hit the blog's `/<slug>/` route, so each page also has a 301 from the slash form. Blog slugs cannot take these routes. |
| Game subdomain | Not mounted there | These are main-site pages. |
| Sitemap | Left out for now | Starter content is unreviewed. Add the pages in Stage 7, after review. |

## Stage status

| Stage | Implemented | Tested | Needs human review |
|---|---|---|---|
| 1 Audit | This document | Not applicable | The decisions above |
| 2 Engine | Grapheme scoring, IME, partial clusters, timer | Node tests with fixtures for all 20 languages | Real IME and keyboard testing |
| 3 Languages | Registry, 20 main pages, RTL practice text, font fallbacks | Django tests, spot checks in Chrome | Rendering, especially Arabic and Urdu; all word lists |
| 4 Durations and modes | Time, Words, Paragraph, Custom Text and Numbers modes; settings saved in the browser | Engine and Django tests, 15 scenarios in headless Chrome | Real typing on real devices; all content. Limits are listed below |
| 5 Accounts and history | Saved results, personal bests, streak, history, profile, preferences, account deletion | Django tests, Chrome DevTools run | Real sign-in on production |
| 6 Leaderboards | Not started | | Server-side validation is missing |
| 7 Admin and metadata | **Partial**: page metadata only | Django tests | Content admin is not built |
| 8 QA | Not started | | |

## Running the tests

```
python manage.py test typingtest
node --test typingtest/engine.test.js
```

## Stage 4 limits

- Word count and custom text are validated only in the browser, since the text itself never reaches the server. Duration and results are also checked on the server.
- Saving custom text to an account does not exist. It stays in the browser, so no permission prompt is needed.
- Input method and keyboard layout are not recorded yet. Stage 6 needs them to separate leaderboard categories.
- Bengali, Hindi, Arabic, Urdu and Thai offer their own digits in Numbers mode. Decimals keep the `.` separator, which needs review.
- Paragraph mode has one passage for each language. Short, Medium and Long are the first 1, 2 and 4 sentences of it.
- Analytics events (brief section 13) are not implemented.

## Stage 5 notes

- Existing accounts and the older `typingApp` results and scores are not changed or moved. New results go to the new `TestResult` table, and the progress page links to the dashboard for older history.
- The server recalculates speed from units and time and enforces limits, but the units still come from the browser. A carefully faked result inside the limits can be saved, so these results are not ranked. Public leaderboards need Stage 6.
- Pages send `X-Robots-Tag: noindex` until `CONTENT_REVIEWED` is set in `typingtest/content.py`.
- Staff accounts cannot use self-service deletion, because deleting a user also deletes their blog posts.
