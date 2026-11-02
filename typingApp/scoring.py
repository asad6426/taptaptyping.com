# A test only counts towards the leaderboard within these limits. No verified
# human has typed above ~220 WPM, matching the check in games.views.
MAX_PLAUSIBLE_WPM = 250
RANKING_MIN_SECONDS = 15
RANKING_MIN_TESTS = 5
RANKING_RECENT_TESTS = 10


def is_plausible_result(wpm, correct_entries, time_taken):
    """False if the submitted speed, or the speed implied by its characters and
    time, is impossible for a human."""
    if time_taken <= 0 or wpm < 0 or correct_entries < 0:
        return False
    implied_wpm = (correct_entries / 5) / (time_taken / 60)
    return wpm <= MAX_PLAUSIBLE_WPM and implied_wpm <= MAX_PLAUSIBLE_WPM


def calculate_marks(wpm, accuracy):
    """
    Calculate marks: 60% WPM + 40% Accuracy.

    Single source of truth for the site's scoring formula, shared by
    TypingTestResult (typingApp) and GameResult (games) so every typing
    feature on the site produces identical marks for identical input.

    WPM Scoring:
    0-20: 0-20 points
    20-40: 20-40 points
    40-60: 40-60 points
    60-80: 60-80 points
    80-100: 80-95 points
    100+: 95-100 points
    """
    if wpm <= 20:
        speed_score = (wpm / 20) * 20
    elif wpm <= 40:
        speed_score = 20 + ((wpm - 20) / 20) * 20
    elif wpm <= 60:
        speed_score = 40 + ((wpm - 40) / 20) * 20
    elif wpm <= 80:
        speed_score = 60 + ((wpm - 60) / 20) * 20
    elif wpm <= 100:
        speed_score = 80 + ((wpm - 80) / 20) * 15
    else:
        speed_score = min(100, 95 + ((wpm - 100) / 20) * 5)

    final_marks = (speed_score * 0.6) + (float(accuracy) * 0.4)
    return round(final_marks, 2)
