# Multilingual typing test: architecture and status

## Decisions from the audit (Stage 1)

| Topic | Decision | Reason |
|---|---|---|
| Framework | Keep Django, not Next.js | The brief says to use the existing project. |
| Database | Keep SQLite for now | It is what production runs. Its write limits should be reviewed before public leaderboards launch. |
| Accounts | Reuse `accounts` and allauth | Sign-in already works. |
| Code location | New `typingtest` app | The existing `/taptap/`, lessons and ranking stay untouched. |
| Language list | `typingtest/languages.py` | Routes, selectors, the site menu, the homepage form, metadata and links are generated from it. |
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
| 6 Leaderboards | Server sessions, server scoring and clock, filters, rules, flagging, rate limits | Django tests, Chrome DevTools run | Flagged results; thresholds. See LEADERBOARD.md |
| 7 Admin and metadata | Content in the database, review workflow, reports, per-language search opening, sitemap | Django tests | All content review |
| 8 QA | axe accessibility scan, security tests, language QA in Chrome | See the Stage 8 section | Real keyboards and devices, screen readers |

## Running the tests

```
python manage.py test typingtest
node --test typingtest/engine.test.js
```

## Stage 4 limits

- Word count and custom text are validated only in the browser, since the text itself never reaches the server. Duration and results are also checked on the server.
- Saving custom text to an account does not exist. It stays in the browser, so no permission prompt is needed.
- Keyboard layout is not recorded, because a browser cannot detect it reliably. Input category is recorded.
- Bengali, Hindi, Arabic, Urdu and Thai offer their own digits in Numbers mode. Decimals keep the `.` separator, which needs review.
- Paragraph mode has one passage for each language. Short, Medium and Long are the first 1, 2 and 4 sentences of it.
- `signup_completed` and `leaderboard_viewed` analytics events are not sent; the others are. See PRIVACY.md.

## Stage 5 notes

- Existing accounts and the older `typingApp` results and scores are not changed or moved. New results go to the new `TestResult` table, and the progress page links to the dashboard for older history.
- The server recalculates speed from units and time and enforces limits, but the units still come from the browser. A carefully faked result inside the limits can be saved, so these results are not ranked. Public leaderboards need Stage 6.
- Each language sends `X-Robots-Tag: noindex` until all of its content is approved in the admin.
- Staff accounts cannot use self-service deletion, because deleting a user also deletes their blog posts.

## Stage 8 results (2026-11-02, local)

| Check | Result |
|---|---|
| Server units against `Intl.Segmenter` on all 481 starter words and sentences | No differences |
| axe-core 4.10 on 11 page states, including dark theme, RTL, results and leaderboard | Two serious issues found and fixed. No serious or critical issues remain |
| Real Chrome through DevTools: key events, IME composition, Enter, Telex rewriting, Tab order, paste | Pass |
| Ranked test through the real page, then shown on the matching board only | Pass |
| Offline: test still runs, result stays on screen and says it was not saved | Pass |
| Security tests: CSRF, other users' sessions, session reuse, impossible results, escaped names, staff-only pages | Pass |

## What this QA did not cover

- Real keyboards and input methods: Avro, Bijoy, InScript, Unikey, Microsoft IME, and phone keyboards. DevTools simulates composition, which is not the same.
- Screen readers. axe checks the code, not the experience of using one.
- Browsers other than Chrome. `Intl.Segmenter` and IME events differ in Safari and Firefox.
- Native review of any text, and of how Arabic and Urdu read and render.
- Load: SQLite handles one write at a time, so a busy leaderboard may need PostgreSQL.
