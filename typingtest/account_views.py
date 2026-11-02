"""Saved results, progress and account controls for signed-in users."""
import json
from datetime import timedelta

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from typingApp.scoring import MAX_PLAUSIBLE_WPM

from .scoring import score_typed_text
from .languages import CUSTOM_DURATION_MAX, CUSTOM_DURATION_MIN, DURATIONS, LANGUAGES, LANGUAGES_BY_CODE, MODES
from .models import TestResult, TestSession, UserPreference

SCORING_VERSION = '1'
RESULTS_PER_MINUTE = 20
HISTORY_LIMIT = 50
INPUT_CATEGORIES = {'desktop', 'ime', 'mobile'}
RANKED_MIN_SECONDS = 15
RANKED_MIN_CORRECT = 20
CLOCK_TOLERANCE_SECONDS = 3
FLAG_SPEED_WPM = 180
FLAG_ACCURATE_WPM = 120
FLAG_ACCURATE_PERCENT = 99.5
MODE_KEYS = {key for key, _, _ in MODES}
MODE_LABELS = {key: label for key, _, label in MODES}
DIFFICULTIES = {'', 'beginner', 'intermediate', 'advanced'}
TEXT_SIZE_MAX = 20
ALLOWED_PREFERENCES = {
    'difficulty': {'beginner', 'intermediate', 'advanced'},
    'theme': {'system', 'light', 'dark'},
    'fontSize': {'small', 'medium', 'large'},
    'lineSpacing': {'compact', 'normal', 'wide'},
    'caret': {'box', 'underline', 'bar'},
    'digitStyle': {'western', 'native'},
    'punctuation': {True, False},
    'numbers': {True, False},
    'capitalization': {True, False},
    'allowCorrections': {True, False},
    'stopOnError': {True, False},
    'strictAccuracy': {True, False},
    'reducedMotion': {True, False},
}


def number(data, key):
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        raise ValueError(key)
    return value


def validated_result(data):
    """Returns the fields to save. Raises ValueError for anything impossible."""
    language = data.get('language')
    mode = data.get('mode')
    if language not in LANGUAGES_BY_CODE or mode not in MODE_KEYS:
        raise ValueError('configuration')
    if data.get('scoringVersion') != SCORING_VERSION:
        raise ValueError('scoring version')

    difficulty = data.get('difficulty', '')
    text_size = str(data.get('textSize', ''))
    if difficulty not in DIFFICULTIES or len(text_size) > TEXT_SIZE_MAX:
        raise ValueError('configuration')

    duration = data.get('durationSec')
    if duration is not None:
        if isinstance(duration, bool) or not isinstance(duration, int):
            raise ValueError('duration')
        if not CUSTOM_DURATION_MIN <= duration <= CUSTOM_DURATION_MAX:
            raise ValueError('duration')
    elif mode == 'time':
        raise ValueError('duration')

    correct = number(data, 'correctUnits')
    incorrect = number(data, 'incorrectUnits')
    corrections = number(data, 'corrections')
    attempts = number(data, 'attempts')
    elapsed = number(data, 'elapsedSec')
    accuracy = number(data, 'accuracy')
    if not all(isinstance(value, int) and value >= 0 for value in (correct, incorrect, corrections, attempts)):
        raise ValueError('counts')
    if elapsed <= 0 or not 0 <= accuracy <= 100:
        raise ValueError('figures')
    if duration is not None and elapsed > duration + 1:
        raise ValueError('elapsed')

    # Speed always comes from the server's own calculation
    cpm = correct / (elapsed / 60)
    wpm = cpm / 5
    if wpm > MAX_PLAUSIBLE_WPM:
        raise ValueError('speed')

    return {
        'language': language,
        'mode': mode,
        'duration_sec': duration,
        'text_size': text_size,
        'difficulty': difficulty,
        'correct_units': correct,
        'incorrect_units': incorrect,
        'corrections': corrections,
        'attempts': attempts,
        'elapsed_sec': elapsed,
        'accuracy': accuracy,
        'cpm': round(cpm, 2),
        'wpm': round(wpm, 2),
        'scoring_version': SCORING_VERSION,
        'content_version': str(data.get('contentVersion', ''))[:30],
    }


def ranked_result(user, data, fields):
    """Rescores a result from its TestSession using the server's text and clock.
    Returns (fields, reason). A reason means the result counts as practice only.
    Raises ValueError if the session or result is impossible."""
    token = data.get('sessionToken')
    now = timezone.now()
    # One use only, even if two requests arrive together
    claimed = TestSession.objects.filter(token=token, user=user, used_at__isnull=True).update(used_at=now)
    if not claimed:
        raise ValueError('session')
    session = TestSession.objects.get(token=token)

    typed = data.get('typedText')
    if not isinstance(typed, str) or len(typed) > len(session.target_text) * 2 + 100:
        raise ValueError('typed text')
    if session.started_at is None:
        raise ValueError('session not started')

    server_elapsed = (now - session.started_at).total_seconds()
    if fields['elapsed_sec'] > server_elapsed + CLOCK_TOLERANCE_SECONDS:
        raise ValueError('clock')

    score = score_typed_text(session.target_text, typed)
    timed = session.duration_sec is not None
    elapsed = min(server_elapsed, session.duration_sec) if timed else server_elapsed
    if elapsed <= 0 or fields['attempts'] < score['correct'] + score['incorrect']:
        raise ValueError('figures')

    cpm = score['correct'] / (elapsed / 60)
    wpm = cpm / 5
    if wpm > MAX_PLAUSIBLE_WPM:
        raise ValueError('speed')

    accuracy = round(min(fields['accuracy'], score['correct'] / fields['attempts'] * 100), 2) if fields['attempts'] else 0
    category = data.get('inputCategory')
    fields.update(
        language=session.language,
        mode=session.mode,
        duration_sec=session.duration_sec,
        text_size=session.text_size,
        difficulty=session.difficulty,
        correct_units=score['correct'],
        incorrect_units=score['incorrect'],
        elapsed_sec=round(elapsed, 2),
        accuracy=accuracy,
        cpm=round(cpm, 2),
        wpm=round(wpm, 2),
        content_version=session.content_version,
        input_category=category if category in INPUT_CATEGORIES else 'unspecified',
    )

    if category not in INPUT_CATEGORIES:
        return fields, 'The input type was not recognized.'
    if data.get('pasteAttempted'):
        return fields, 'Paste was used during this test.'
    if elapsed < RANKED_MIN_SECONDS or score['correct'] < RANKED_MIN_CORRECT:
        return fields, f'Tests need at least {RANKED_MIN_SECONDS} seconds and {RANKED_MIN_CORRECT} correct units.'
    if timed and server_elapsed < session.duration_sec - CLOCK_TOLERANCE_SECONDS:
        return fields, 'The test did not run for its full time.'
    if not timed and score['typed'] < score['target']:
        return fields, 'The text was not finished.'

    fields['is_ranked'] = True
    if wpm > FLAG_SPEED_WPM:
        fields.update(review_status=TestResult.FLAGGED, flag_reason=f'Above {FLAG_SPEED_WPM} WPM')
    elif wpm > FLAG_ACCURATE_WPM and accuracy >= FLAG_ACCURATE_PERCENT:
        fields.update(review_status=TestResult.FLAGGED, flag_reason='Very fast and almost no mistakes')
    return fields, ''


def same_configuration(user, fields):
    return TestResult.objects.filter(
        user=user,
        input_category=fields.get('input_category', 'unspecified'),
        language=fields['language'],
        mode=fields['mode'],
        duration_sec=fields['duration_sec'],
        text_size=fields['text_size'],
        difficulty=fields['difficulty'],
        scoring_version=fields['scoring_version'],
    )


@require_POST
def save_result(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Sign in to save results.'}, status=401)

    minute_ago = timezone.now() - timedelta(minutes=1)
    if TestResult.objects.filter(user=request.user, created_at__gte=minute_ago).count() >= RESULTS_PER_MINUTE:
        return JsonResponse({'success': False, 'error': 'Too many results. Try again in a minute.'}, status=429)

    reason = 'This test was practice only.'
    try:
        data = json.loads(request.body)
        fields = validated_result(data)
        if data.get('sessionToken'):
            fields, reason = ranked_result(request.user, data, fields)
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({'success': False, 'error': 'This result could not be accepted.'}, status=400)

    previous_best = same_configuration(request.user, fields).order_by('-wpm').values_list('wpm', flat=True).first()
    TestResult.objects.create(user=request.user, **fields)
    return JsonResponse({
        'success': True,
        'wpm': fields['wpm'],
        'cpm': fields['cpm'],
        'personalBest': max(fields['wpm'], previous_best or 0),
        'isNewBest': previous_best is not None and fields['wpm'] > previous_best,
        'ranked': fields.get('is_ranked', False),
        'underReview': fields.get('review_status') == TestResult.FLAGGED,
        'reason': reason,
    })


def clean_preferences(data):
    return {
        key: value for key, value in data.items()
        if key in ALLOWED_PREFERENCES and not isinstance(value, (list, dict)) and value in ALLOWED_PREFERENCES[key]
    }


@require_POST
def save_preferences(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False}, status=401)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError
    except ValueError:
        return JsonResponse({'success': False}, status=400)
    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    preference.settings = clean_preferences(data)
    preference.save()
    return JsonResponse({'success': True})


def practice_streak(user, today=None):
    """Days in a row with a saved test, ending today or yesterday."""
    today = today or timezone.localdate()
    days = {timezone.localdate(value) for value in TestResult.objects.filter(user=user).values_list('created_at', flat=True)}
    day = today if today in days else today - timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def describe(language, mode, duration, text_size, difficulty):
    language_item = LANGUAGES_BY_CODE.get(language)
    parts = [language_item.name if language_item else language, MODE_LABELS.get(mode, mode)]
    if duration:
        parts.append(f'{duration} s')
    if text_size:
        parts.append(text_size)
    if difficulty:
        parts.append(difficulty.capitalize())
    return ' · '.join(parts)


@login_required
def progress_page(request):
    results = TestResult.objects.filter(user=request.user)
    bests = {}
    for result in results.order_by('-wpm', '-id'):
        key = (result.language, result.mode, result.duration_sec, result.text_size, result.difficulty, result.scoring_version)
        if key not in bests:
            bests[key] = {'label': describe(*key[:5]), 'wpm': result.wpm, 'accuracy': result.accuracy, 'date': result.created_at}

    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    notice = ''
    if request.method == 'POST':
        preference.display_name = request.POST.get('display_name', '').strip()[:40]
        language = request.POST.get('default_language', '')
        preference.default_language = language if language in LANGUAGES_BY_CODE else ''
        preference.save()
        notice = 'Saved.'

    history = [
        {'label': describe(r.language, r.mode, r.duration_sec, r.text_size, r.difficulty),
         'wpm': r.wpm, 'accuracy': r.accuracy, 'date': r.created_at}
        for r in results[:HISTORY_LIMIT]
    ]
    response = render(request, 'typingtest/progress.html', {
        'total_tests': results.count(),
        'streak': practice_streak(request.user),
        'bests': sorted(bests.values(), key=lambda item: item['label']),
        'history': history,
        'preference': preference,
        'languages': LANGUAGES,
        'notice': notice,
        'can_delete': not (request.user.is_staff or request.user.is_superuser),
    })
    response['X-Robots-Tag'] = 'noindex'
    return response


@login_required
@require_http_methods(['POST'])
def delete_account(request):
    """Deletes the account and everything linked to it, after the user types their username."""
    user = request.user
    if user.is_staff or user.is_superuser:
        return redirect('typingtest:progress')
    if request.POST.get('confirm_username') != user.username:
        return redirect('/typing-test/progress?delete=mismatch')
    logout(request)
    user.delete()
    return redirect('/')
