# Privacy notes for the typing test

| Data | Where it goes |
|---|---|
| Custom text | Stays in the browser. It is never sent to the server or to analytics, and there is no option to save it. |
| Ranked typed text | Sent once at the end of a ranked test so the server can score it. It is compared and discarded, not stored. It is only ever site-supplied practice text. |
| Results | Saved for signed-in users. Guests' results stay in the browser. |
| Practice text in a session | Stored with the session and deleted after 2 hours, the next time that user starts a ranked test. |
| Preferences | In the browser for guests, in the account for signed-in users. |
| Text error reports | The message, a short excerpt of site text, and a reporter key to limit abuse. Custom text pages have no report form. |

## Analytics

The events in the brief go to the site's existing Google Analytics with only language, mode, duration, difficulty, device category, input category and scoring version. They never include typed text or keystrokes. They are skipped when the browser sends Global Privacy Control.

The site has no cookie consent tool. Google Analytics and AdSense already load on every page without one. **This needs a decision from the site owner, particularly for visitors in the EU and UK.**

## Deleting an account

The Progress page deletes the account and everything linked to it, including test results, scores and certificates. Staff accounts are excluded, because deleting a user also deletes their blog posts.

Public leaderboards show the display name, or the username if none is set.
