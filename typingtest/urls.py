from django.urls import path
from django.views.generic import RedirectView

from . import account_views, competition, views
from .languages import DURATIONS, LANGUAGES

app_name = 'typingtest'

MODE_VIEWS = (
    ('words', views.words_page),
    ('paragraph', views.paragraph_page),
    ('custom-text', views.custom_text_page),
    ('numbers', views.numbers_page),
)


def page_routes(route, view, kwargs, name):
    """The page itself, plus a redirect from the trailing-slash form. The blog's
    /<slug>/ route would otherwise answer that form with a 404."""
    return [
        path(route, view, kwargs, name=name),
        path(f'{route}/', RedirectView.as_view(url=f'/{route}', permanent=True)),
    ]


urlpatterns = [
    path('typing-test/api/results', account_views.save_result, name='save_result'),
    path('typing-test/api/preferences', account_views.save_preferences, name='save_preferences'),
    path('typing-test/api/sessions', competition.create_session, name='create_session'),
    path('typing-test/api/sessions/<str:token>/start', competition.start_session, name='start_session'),
    path('typing-test/api/report', competition.report_text, name='report_text'),
    path('typing-test/leaderboard', competition.leaderboard_page, name='leaderboard'),
    path('typing-test/review', competition.review_page, name='review'),
    path('typing-test/progress', account_views.progress_page, name='progress'),
    path('typing-test/account/delete', account_views.delete_account, name='delete_account'),
]
for language in LANGUAGES:
    urlpatterns += page_routes(language.slug, views.language_page, {'language': language.code}, language.code)
    for slug, _, _ in DURATIONS:
        urlpatterns += page_routes(
            f'{language.slug}/{slug}',
            views.language_page,
            {'language': language.code, 'duration': slug},
            f'{language.code}-{slug}',
        )
    for slug, view in MODE_VIEWS:
        urlpatterns += page_routes(
            f'{language.slug}/{slug}',
            view,
            {'language': language.code},
            f'{language.code}-{slug}',
        )
