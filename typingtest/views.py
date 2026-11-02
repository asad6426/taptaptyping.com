from django.http import Http404
from django.middleware.csrf import get_token
from django.shortcuts import render

from .account_views import SCORING_VERSION
from .competition import FIXED_DURATIONS
from .content_store import content_for, is_language_reviewed
from .models import UserPreference
from .languages import (
    CUSTOM_DURATION_MAX,
    CUSTOM_DURATION_MIN,
    DURATIONS,
    LANGUAGES,
    LANGUAGES_BY_CODE,
    MODES,
    WORD_COUNTS,
    UNIT_COUNTS,
)


def get_language(code):
    language = LANGUAGES_BY_CODE.get(code)
    if language is None:
        raise Http404('Unknown language')
    return language


def render_test(request, language, *, mode, h1, title, description, seconds=60, duration=None):
    is_main_page = mode == 'time' and duration is None
    get_token(request)  # Saving a result needs the CSRF cookie
    content = content_for(language.code)
    reviewed = is_language_reviewed(language.code)
    server_preferences = {}
    if request.user.is_authenticated:
        preference = UserPreference.objects.filter(user=request.user).first()
        server_preferences = preference.settings if preference else {}
    response = render(request, 'typingtest/language_page.html', {
        'language': language,
        'languages': LANGUAGES,
        'other_languages': [other for other in LANGUAGES if other != language],
        'durations': [
            {'slug': slug, 'minutes': value, 'path': f'{language.path}/{slug}', 'current': slug == duration}
            for slug, _, value in DURATIONS
        ],
        'modes': [
            {
                'label': label,
                'path': f'{language.path}/{slug}' if slug else language.path,
                'current': key == mode,
            }
            for key, slug, label in MODES
        ],
        'mode': mode,
        'h1': h1,
        'page_title': title,
        'description': description,
        'is_main_page': is_main_page,
        'custom_min': CUSTOM_DURATION_MIN,
        'custom_max': CUSTOM_DURATION_MAX,
        'duration_label': f'{seconds // 60}:{seconds % 60:02d}',
        'word_counts': WORD_COUNTS if language.word_boundary == 'spaces' else UNIT_COUNTS,
        'unit_name': 'Words' if language.word_boundary == 'spaces' else 'Characters',
        'practice_direction': 'ltr' if mode == 'numbers' else language.direction,
        'content_reviewed': reviewed,
        'config': {
            'language': language.code,
            'locale': language.locale,
            'joiner': language.joiner,
            'mode': mode,
            'durationSec': seconds,
            'wordBoundary': language.word_boundary,
            'words': content['words'],
            'paragraphs': content['paragraph'],
            'rankedDurations': sorted(FIXED_DURATIONS),
            'comma': language.comma,
            'end': language.end,
            'cased': language.cased,
            'customMin': CUSTOM_DURATION_MIN,
            'customMax': CUSTOM_DURATION_MAX,
            'contentVersion': content['version'],
            'contentStatus': 'approved' if reviewed else 'unreviewed',
            'digits': language.digits,
            'scoringVersion': SCORING_VERSION,
            'signedIn': request.user.is_authenticated,
            'serverPreferences': server_preferences,
        },
    })
    # Stay out of search results until native speakers have reviewed the text
    if not reviewed:
        response['X-Robots-Tag'] = 'noindex'
    return response


def language_page(request, language, duration=None):
    language = get_language(language)
    if duration is None:
        return render_test(
            request, language, mode='time',
            h1=f'{language.name} Typing Test',
            title=f'{language.name} Typing Test – Check Your Speed | TapTapTyping',
            description=(
                f'Practice {language.name} typing with 1, 2, 3, 5, and 10-minute tests. '
                'Check your speed and accuracy, practice paragraphs, or use your own custom text.'
            ),
        )

    match = next((d for d in DURATIONS if d[0] == duration), None)
    if match is None:
        raise Http404('Unknown duration')
    _, seconds, minutes = match
    return render_test(
        request, language, mode='time', seconds=seconds, duration=duration,
        h1=f'{minutes} Minute {language.name} Typing Test',
        title=f'{minutes} Minute {language.name} Typing Test | TapTapTyping',
        description=(
            f'Take a {minutes}-minute {language.name} typing test. The timer starts with '
            'your first character, and you see your speed and accuracy when time runs out.'
        ),
    )


def words_page(request, language):
    language = get_language(language)
    if language.word_boundary == 'spaces':
        h1 = f'{language.name} Word Typing Test'
        description = f'Type a set number of {language.name} words, from 10 to 200, and see how fast and accurately you finish.'
    else:
        # This language does not separate words with spaces, so length is counted in characters
        h1 = f'{language.name} Text Length Typing Test'
        description = f'Type a set length of {language.name} text, measured in characters, and see how fast and accurately you finish.'
    return render_test(
        request, language, mode='words', h1=h1, title=f'{h1} | TapTapTyping', description=description,
    )


def paragraph_page(request, language):
    language = get_language(language)
    h1 = f'{language.name} Paragraph Typing Test'
    return render_test(
        request, language, mode='paragraph', h1=h1, title=f'{h1} | TapTapTyping',
        description=f'Type a short, medium or long {language.name} paragraph with natural punctuation and check your result when you finish.',
    )


def custom_text_page(request, language):
    language = get_language(language)
    h1 = f'{language.name} Custom Text Typing Test'
    return render_test(
        request, language, mode='custom', h1=h1, title=f'{h1} | TapTapTyping',
        description=f'Paste or upload your own {language.name} text and practice typing it. Your text stays in your browser.',
    )


def numbers_page(request, language):
    language = get_language(language)
    h1 = f'{language.name} Numbers Typing Practice'
    return render_test(
        request, language, mode='numbers', h1=h1, title=f'{h1} | TapTapTyping',
        description='Practice typing whole numbers, decimals, and numbers mixed with symbols.',
    )
