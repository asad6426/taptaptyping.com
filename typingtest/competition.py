"""Ranked test sessions and public leaderboards."""
import json
import random
import secrets
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .content_store import content_for
from .languages import DURATIONS, LANGUAGES, LANGUAGES_BY_CODE, UNIT_COUNTS, WORD_COUNTS
from .models import ContentItem, ContentReport, TestResult, TestSession
from .scoring import split_units

SESSIONS_PER_MINUTE = 30
SESSION_LIFETIME = timedelta(hours=2)
REPORTS_PER_HOUR = 5
UNITS_PER_SECOND = 22
NUMBER_TOKENS = 40
LEADERBOARD_SIZE = 100
PARAGRAPH_SIZES = {'short': 1, 'medium': 2, 'long': 4}
NUMBER_KINDS = ('whole', 'decimal', 'mixed')
DIFFICULTIES = ('beginner', 'intermediate', 'advanced')
INPUT_CATEGORIES = {
    'desktop': 'Desktop keyboard',
    'ime': 'Input method (IME)',
    'mobile': 'Mobile or touch keyboard',
}
RANKED_MODES = {'time': 'Time', 'words': 'Words', 'paragraph': 'Paragraph', 'numbers': 'Numbers'}
PERIODS = {'all': 'All Time', 'weekly': 'Weekly', 'daily': 'Daily'}
FIXED_DURATIONS = {seconds for _, seconds, _ in DURATIONS}


def filter_by_difficulty(words, difficulty):
    if difficulty not in ('beginner', 'advanced'):
        return words
    ordered = sorted(words, key=lambda word: len(split_units(word)))
    middle = (len(ordered) + 1) // 2
    return ordered[:middle] if difficulty == 'beginner' else ordered[len(ordered) - middle:]


def random_words(words, joiner, min_units=None, max_words=None):
    pieces = []
    units = 0
    previous = None
    while (units < min_units) if max_words is None else (len(pieces) < max_words):
        options = [word for word in words if word != previous] or words
        previous = random.choice(options)
        pieces.append(previous)
        units += len(split_units(previous)) + len(joiner)
    return joiner.join(pieces)


def numbers_text(kind, digits):
    symbols = '+-=%$#*/'
    tokens = []
    for index in range(NUMBER_TOKENS):
        whole = str(random.randrange(10000))
        if kind == 'decimal':
            tokens.append(f'{whole}.{random.randrange(100):02d}')
        elif kind == 'mixed':
            symbol = random.choice(symbols)
            tokens.append(f'{whole}{symbol}' if index % 2 == 0 else f'{symbol}{whole}')
        else:
            tokens.append(whole)
    text = ' '.join(tokens)
    return text.translate({ord(str(i)): digit for i, digit in enumerate(digits)}) if digits else text


def build_session_text(language, mode, duration, text_size, difficulty):
    """The practice text for a ranked session. Raises ValueError for anything unranked."""
    content = content_for(language.code)
    joiner = language.joiner

    if mode == 'time':
        if duration not in FIXED_DURATIONS or difficulty not in DIFFICULTIES:
            raise ValueError('configuration')
        words = filter_by_difficulty(content['words'], difficulty)
        return random_words(words, joiner, min_units=duration * UNITS_PER_SECOND), ''

    if mode == 'words':
        counts = WORD_COUNTS if language.word_boundary == 'spaces' else UNIT_COUNTS
        if text_size not in {str(count) for count in counts} or difficulty not in DIFFICULTIES:
            raise ValueError('configuration')
        words = filter_by_difficulty(content['words'], difficulty)
        if language.word_boundary == 'spaces':
            return random_words(words, joiner, max_words=int(text_size)), text_size
        text = random_words(words, joiner, min_units=int(text_size))
        return ''.join(split_units(text)[:int(text_size)]), text_size

    if mode == 'paragraph':
        if text_size not in PARAGRAPH_SIZES or not content['paragraph']:
            raise ValueError('configuration')
        separator = ' ' if language.word_boundary == 'spaces' else ''
        return separator.join(content['paragraph'][:PARAGRAPH_SIZES[text_size]]), text_size

    if mode == 'numbers':
        kind, _, style = text_size.partition('-')
        if kind not in NUMBER_KINDS or style not in ('western', 'native'):
            raise ValueError('configuration')
        if style == 'native' and not language.digits:
            raise ValueError('configuration')
        return numbers_text(kind, language.digits if style == 'native' else ''), text_size

    raise ValueError('configuration')


@require_POST
def create_session(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Sign in to enter leaderboards.'}, status=401)

    minute_ago = timezone.now() - timedelta(minutes=1)
    if TestSession.objects.filter(user=request.user, created_at__gte=minute_ago).count() >= SESSIONS_PER_MINUTE:
        return JsonResponse({'success': False, 'error': 'Too many tests started. Try again in a minute.'}, status=429)

    try:
        data = json.loads(request.body)
        language = LANGUAGES_BY_CODE[data['language']]
        mode = data['mode']
        duration = data.get('durationSec')
        difficulty = data.get('difficulty', '') if mode in ('time', 'words') else ''
        text, text_size = build_session_text(language, mode, duration, str(data.get('textSize', '')), difficulty)
    except (ValueError, KeyError, TypeError, AttributeError):
        return JsonResponse({'success': False, 'error': 'This test setup is not ranked.'}, status=400)

    TestSession.objects.filter(user=request.user, created_at__lt=timezone.now() - SESSION_LIFETIME).delete()
    session = TestSession.objects.create(
        token=secrets.token_urlsafe(24),
        user=request.user,
        language=language.code,
        mode=mode,
        duration_sec=duration if mode == 'time' else None,
        text_size=text_size,
        difficulty=difficulty,
        target_text=text,
        content_version=content_for(language.code)['version'],
    )
    return JsonResponse({'success': True, 'token': session.token, 'target': text})


@require_POST
def start_session(request, token):
    """Marks the first typed character. The server's elapsed time starts here."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False}, status=401)
    updated = TestSession.objects.filter(
        token=token, user=request.user, started_at__isnull=True, used_at__isnull=True,
    ).update(started_at=timezone.now())
    return JsonResponse({'success': bool(updated)}, status=200 if updated else 404)


def leaderboard_rows(language, mode, duration, text_size, difficulty, category, period):
    results = TestResult.objects.filter(
        is_ranked=True,
        language=language,
        mode=mode,
        input_category=category,
        review_status__in=(TestResult.CLEAN, TestResult.APPROVED),
    ).select_related('user', 'user__typing_preference')
    if mode == 'time':
        results = results.filter(duration_sec=duration, difficulty=difficulty)
    elif mode == 'words':
        results = results.filter(text_size=text_size, difficulty=difficulty)
    else:
        results = results.filter(text_size=text_size)
    if period == 'daily':
        results = results.filter(created_at__gte=timezone.now() - timedelta(days=1))
    elif period == 'weekly':
        results = results.filter(created_at__gte=timezone.now() - timedelta(days=7))

    rows = []
    seen = set()
    for result in results.order_by('-wpm', '-accuracy', 'created_at')[:5000]:
        if result.user_id in seen:
            continue
        seen.add(result.user_id)
        preference = getattr(result.user, 'typing_preference', None)
        rows.append({
            'rank': len(rows) + 1,
            'name': (preference.display_name if preference else '') or result.user.username,
            'wpm': result.wpm,
            'cpm': result.cpm,
            'accuracy': result.accuracy,
            'date': result.created_at,
        })
        if len(rows) == LEADERBOARD_SIZE:
            break
    return rows


def choice(value, allowed, default):
    return value if value in allowed else default


def leaderboard_page(request):
    query = request.GET
    language = choice(query.get('language'), LANGUAGES_BY_CODE, 'english')
    mode = choice(query.get('mode'), RANKED_MODES, 'time')
    language_item = LANGUAGES_BY_CODE[language]
    counts = WORD_COUNTS if language_item.word_boundary == 'spaces' else UNIT_COUNTS

    durations = [(str(seconds), f'{minutes} Minute{"s" if minutes > 1 else ""}') for _, seconds, minutes in DURATIONS]
    if mode == 'words':
        sizes = [(str(count), str(count)) for count in counts]
    elif mode == 'paragraph':
        sizes = [(key, key.capitalize()) for key in PARAGRAPH_SIZES]
    elif mode == 'numbers':
        styles = ['western'] + (['native'] if language_item.digits else [])
        sizes = [(f'{kind}-{style}', f'{kind.capitalize()} ({style.capitalize()})') for kind in NUMBER_KINDS for style in styles]
    else:
        sizes = []

    duration = int(choice(query.get('duration'), {key for key, _ in durations}, '60'))
    size_keys = [key for key, _ in sizes]
    text_size = choice(query.get('size'), size_keys, size_keys[0] if size_keys else '')
    difficulty = choice(query.get('difficulty'), DIFFICULTIES, 'intermediate')
    category = choice(query.get('category'), INPUT_CATEGORIES, 'desktop')
    period = choice(query.get('period'), PERIODS, 'all')

    response = render(request, 'typingtest/leaderboard.html', {
        'rows': leaderboard_rows(language, mode, duration, text_size, difficulty, category, period),
        'languages': LANGUAGES,
        'modes': RANKED_MODES.items(),
        'durations': durations,
        'sizes': sizes,
        'difficulties': [(item, item.capitalize()) for item in DIFFICULTIES],
        'categories': INPUT_CATEGORIES.items(),
        'periods': PERIODS.items(),
        'selected': {
            'language': language, 'mode': mode, 'duration': str(duration), 'size': text_size,
            'difficulty': difficulty, 'category': category, 'period': period,
        },
        'show_duration': mode == 'time',
        'show_size': bool(sizes),
        'show_difficulty': mode in ('time', 'words'),
        'language_name': language_item.name,
        'min_seconds': 15,
    })
    # Filter combinations stay out of search results
    if query:
        response['X-Robots-Tag'] = 'noindex'
    return response


@require_POST
def report_text(request):
    """Reports a mistake in practice text. Custom text can never be reported."""
    if not request.session.session_key:
        request.session.save()
    reporter = f'user-{request.user.pk}' if request.user.is_authenticated else request.session.session_key
    hour_ago = timezone.now() - timedelta(hours=1)
    if ContentReport.objects.filter(reporter=reporter, created_at__gte=hour_ago).count() >= REPORTS_PER_HOUR:
        return JsonResponse({'success': False, 'error': 'Too many reports. Try again later.'}, status=429)
    try:
        data = json.loads(request.body)
        language = LANGUAGES_BY_CODE[data['language']].code
        mode = data['mode']
        message = str(data['message']).strip()[:500]
        if mode not in RANKED_MODES or not message:
            raise ValueError
    except (ValueError, KeyError, TypeError, AttributeError):
        return JsonResponse({'success': False, 'error': 'Describe the mistake first.'}, status=400)
    ContentReport.objects.create(
        language=language,
        mode=mode,
        excerpt=str(data.get('excerpt', ''))[:200],
        message=message,
        reporter=reporter,
    )
    return JsonResponse({'success': True})


@login_required
def review_page(request):
    """Staff overview of content review, reports and flagged results."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Staff only'}, status=403)
    rows = []
    counts = ContentItem.objects.values('language').annotate(
        approved=Count('pk', filter=Q(review_status=ContentItem.APPROVED)),
        unreviewed=Count('pk', filter=Q(review_status=ContentItem.UNREVIEWED)),
        rejected=Count('pk', filter=Q(review_status=ContentItem.REJECTED)),
    )
    by_language = {row['language']: row for row in counts}
    for language in LANGUAGES:
        row = by_language.get(language.code, {})
        rows.append({
            'name': language.name,
            'code': language.code,
            'approved': row.get('approved', 0),
            'unreviewed': row.get('unreviewed', 0),
            'rejected': row.get('rejected', 0),
            'open_reports': ContentReport.objects.filter(language=language.code, resolved=False).count(),
        })
    response = render(request, 'typingtest/review.html', {
        'rows': rows,
        'flagged': TestResult.objects.filter(review_status=TestResult.FLAGGED).count(),
    })
    response['X-Robots-Tag'] = 'noindex'
    return response
