# Leaderboard eligibility and validation

## How a ranked test works

1. A signed-in user with standard settings starts a test. The server creates a one-use `TestSession` and supplies the practice text.
2. At the first typed character, the browser tells the server. The server records its own start time.
3. At the end, the browser sends the typed text. The server splits it into units with `typingtest/scoring.py`, compares it with its stored text, measures the time, and calculates the score. Scores sent by the browser are ignored.
4. Results outside the limits are rejected. Unusual results are stored but hidden until staff review them.

## Eligibility

A result is ranked only if all of these are true:

- Signed in, with a valid and unused session belonging to that user
- Mode is Time, Words, Paragraph or Numbers, never Custom Text
- Fixed duration or preset length; custom lengths are not ranked
- Corrections allowed, Stop on Error and Strict Accuracy off, and no added punctuation, numbers or capitals
- No paste attempt
- At least 15 seconds and 20 correct units
- Timed tests ran for their full duration on the server's clock, and other tests were finished
- At most 250 WPM

A result is flagged for review if it is above 180 WPM, or above 120 WPM with at least 99.5% accuracy.

## Categories

Desktop keyboard, IME and mobile keyboard results are on separate boards. The browser reports the category, based on composition events and touch hardware, so a user could misreport it. Keyboard layout is stored as `unspecified` for now, because the browser cannot detect it reliably.

## What this does not stop

These checks make cheating slower and harder, but they do not prevent it:

- A script can type at a believable speed in real time.
- A person can use text expansion or assistive tools in ways that look like typing.
- Accuracy still depends on the attempt count the browser sends, though it cannot claim more correct units than the server counted.

Staff should review flagged results and remove anything suspicious in the admin.
