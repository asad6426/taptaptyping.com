import json
import re
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from TapTapTyping import middleware
from blog.models import BlogPost

from .content import STARTER_PARAGRAPHS, STARTER_WORDS
from .content_store import content_for, is_language_reviewed
from .account_views import practice_streak
from .languages import DURATIONS, LANGUAGES
from .models import ContentItem, ContentReport, TestResult, TestSession, UserPreference
from .scoring import score_typed_text, split_units


def tearDownModule():
    # These tests send enough requests to reach the site-wide limit per IP
    middleware._request_counts.clear()
    middleware._blocked_until.clear()


class LanguagePageTests(TestCase):
    def test_registry_has_all_twenty_languages_with_content(self):
        self.assertEqual(len(LANGUAGES), 20)
        self.assertEqual({language.code for language in LANGUAGES}, set(STARTER_WORDS))

    def test_every_main_page(self):
        for language in LANGUAGES:
            response = self.client.get(language.path)
            self.assertContains(response, f'<h1>{language.name} Typing Test</h1>', html=False)
            self.assertEqual(response.content.decode().count('<h1'), 1, language.name)
            self.assertContains(response, f'<title>{language.name} Typing Test – Check Your Speed | TapTapTyping</title>')
            self.assertContains(response, f'<link rel="canonical" href="https://taptaptyping.com{language.path}">')
            for heading in ('Choose Your Test Duration', 'Choose Your Practice Mode', 'Understanding Your Results',
                            'Frequently Asked Questions', 'Explore Other Languages',
                            f'How to Take the {language.name} Typing Test'):
                self.assertContains(response, f'<h2>{heading}</h2>')

    def test_every_duration_page(self):
        for language in LANGUAGES:
            for slug, seconds, minutes in DURATIONS:
                response = self.client.get(f'{language.path}/{slug}')
                self.assertContains(response, f'<h1>{minutes} Minute {language.name} Typing Test</h1>')
                self.assertContains(response, f'<title>{minutes} Minute {language.name} Typing Test | TapTapTyping</title>')
                self.assertEqual(response.context['config']['durationSec'], seconds)

    def test_unknown_routes_are_not_found(self):
        self.assertEqual(self.client.get('/klingon-typing-test', follow=True).status_code, 404)
        self.assertEqual(self.client.get('/english-typing-test/7-minutes', follow=True).status_code, 404)

    def test_trailing_slash_redirects_to_the_canonical_page(self):
        response = self.client.get('/english-typing-test/')
        self.assertRedirects(response, '/english-typing-test', status_code=301)
        response = self.client.get('/bengali-typing-test/3-minutes/')
        self.assertRedirects(response, '/bengali-typing-test/3-minutes', status_code=301)

    def test_practice_text_direction_follows_the_language(self):
        for code, direction in (('arabic', 'rtl'), ('urdu', 'rtl'), ('english', 'ltr'), ('thai', 'ltr')):
            response = self.client.get(f'/{code}-typing-test')
            self.assertContains(response, f'id="practiceText" dir="{direction}"')
            self.assertNotContains(response, '<html lang="ar"')

    def test_languages_without_spaces_join_words_directly(self):
        self.assertEqual(self.client.get('/japanese-typing-test').context['config']['joiner'], '')
        self.assertEqual(self.client.get('/thai-typing-test').context['config']['joiner'], '')
        self.assertEqual(self.client.get('/korean-typing-test').context['config']['joiner'], ' ')

    def test_selector_comes_from_the_registry(self):
        options = re.findall(r'<option value="(/[a-z]+-typing-test)"', self.client.get('/english-typing-test').content.decode())
        self.assertEqual(options, [language.path for language in LANGUAGES])

    def test_no_login_is_needed(self):
        response = self.client.get('/hindi-typing-test')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['config']['signedIn'])

    def test_pages_stay_out_of_search_until_reviewed(self):
        response = self.client.get('/hindi-typing-test')
        self.assertEqual(response['X-Robots-Tag'], 'noindex')
        self.assertContains(response, 'has not yet been reviewed by native speakers')

    def test_native_digits_are_offered_where_they_exist(self):
        self.assertContains(self.client.get('/bengali-typing-test/numbers'), 'name="digitStyle" value="native"')
        self.assertNotContains(self.client.get('/english-typing-test/numbers'), 'name="digitStyle"')

    def test_every_mode_page(self):
        for language in LANGUAGES:
            spaced = language.word_boundary == 'spaces'
            pages = {
                'words': f'{language.name} Word Typing Test' if spaced else f'{language.name} Text Length Typing Test',
                'paragraph': f'{language.name} Paragraph Typing Test',
                'custom-text': f'{language.name} Custom Text Typing Test',
                'numbers': f'{language.name} Numbers Typing Practice',
            }
            for slug, h1 in pages.items():
                response = self.client.get(f'{language.path}/{slug}')
                self.assertContains(response, f'<h1>{h1}</h1>')
                self.assertContains(response, f'<title>{h1} | TapTapTyping</title>')
                self.assertEqual(response.content.decode().count('<h1'), 1, slug)
                self.assertEqual(response.client.get(f'{language.path}/{slug}/').status_code, 301)

    def test_words_mode_uses_characters_without_word_boundaries(self):
        self.assertContains(self.client.get('/japanese-typing-test/words'), '<legend>Characters</legend>')
        self.assertContains(self.client.get('/english-typing-test/words'), '<legend>Words</legend>')

    def test_paragraphs_exist_and_are_marked_unreviewed(self):
        self.assertEqual({language.code for language in LANGUAGES}, set(STARTER_PARAGRAPHS))
        for code, sentences in STARTER_PARAGRAPHS.items():
            self.assertEqual(len(sentences), 4, code)
        self.assertFalse(ContentItem.objects.exclude(review_status=ContentItem.UNREVIEWED).exists())
        config = self.client.get('/bengali-typing-test/paragraph').context['config']
        self.assertEqual(config['contentStatus'], 'unreviewed')

    def test_numbers_practice_runs_left_to_right_in_rtl_languages(self):
        response = self.client.get('/arabic-typing-test/numbers')
        self.assertContains(response, 'id="practiceText" dir="ltr"')

    def test_custom_text_page_promises_local_only(self):
        response = self.client.get('/hindi-typing-test/custom-text')
        self.assertContains(response, 'Your text stays in this browser.')
        for control in ('Paste Text', 'Upload TXT', 'Clear Text', 'Start Practice', 'Restart Practice',
                        'Timed Practice', 'Complete Full Text', 'Preserve Capitalization',
                        'Preserve Punctuation', 'Normalize Extra Spaces', 'Repeat Text Until Timer Ends'):
            self.assertContains(response, control)

    def test_settings_match_the_language(self):
        thai = self.client.get('/thai-typing-test').content.decode()
        self.assertRegex(thai, r'id="optPunctuation" disabled')
        self.assertRegex(thai, r'id="optCapitalization" disabled')
        english = self.client.get('/english-typing-test').content.decode()
        self.assertNotRegex(english, r'id="optCapitalization" disabled')

    def test_difficulty_and_content_only_show_where_they_apply(self):
        hidden = '<fieldset class="tt-choice" data-scoring hidden>'
        self.assertNotContains(self.client.get('/english-typing-test'), hidden)
        self.assertNotContains(self.client.get('/english-typing-test/words'), hidden)
        for slug in ('paragraph', 'numbers', 'custom-text'):
            self.assertContains(self.client.get(f'/english-typing-test/{slug}'), hidden, count=2)

    def test_every_language_can_be_chosen_from_the_homepage_and_menu(self):
        home = self.client.get('/').content.decode()
        options = re.findall(r'<option value="(/[a-z]+-typing-test)"', home)
        self.assertEqual(options, [language.path for language in LANGUAGES])
        for language in LANGUAGES:
            self.assertIn(f'<a class="dropdown-item" href="https://taptaptyping.com{language.path}">{language.name}</a>', home)

    def test_classic_test_page_has_a_language_choice(self):
        page = self.client.get('/taptap/').content.decode()
        options = re.findall(r'<option value="(/[a-z]+-typing-test)"', page)
        self.assertEqual(options, [language.path for language in LANGUAGES])
        self.assertLess(page.index('id="testLanguage"'), page.index('id="text-display"'))

    def test_menu_works_on_other_pages_and_the_game_site(self):
        for path, host in (('/blogs/', 'testserver'), ('/typing-lessons/', 'testserver'), ('/', 'game.taptaptyping.com')):
            response = self.client.get(path, HTTP_HOST=host)
            self.assertContains(response, 'https://taptaptyping.com/urdu-typing-test')
            self.assertContains(response, "Typing Speed Test")

    def test_a_blog_post_cannot_take_a_language_route(self):
        post = BlogPost(title='English Typing Test')
        self.assertEqual(post.build_slug(), 'english-typing-test-2')


def payload(**overrides):
    data = dict(
        language='bengali', mode='time', durationSec=60, textSize='', difficulty='intermediate',
        scoringVersion='1', contentVersion='starter-1', correctUnits=250, incorrectUnits=3,
        corrections=2, attempts=255, elapsedSec=60, accuracy=98.04, cpm=9999, wpm=9999,
    )
    data.update(overrides)
    return data


class SaveResultTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('typist', password='x')
        self.client.force_login(self.user)

    def post(self, **overrides):
        return self.client.post('/typing-test/api/results', json.dumps(payload(**overrides)), content_type='application/json')

    def test_guests_cannot_save(self):
        response = Client().post('/typing-test/api/results', json.dumps(payload()), content_type='application/json')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(TestResult.objects.exists())

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post('/typing-test/api/results', json.dumps(payload()), content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_server_calculates_the_speed_itself(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        result = TestResult.objects.get()
        self.assertEqual((result.cpm, result.wpm), (250, 50))

    def test_invalid_submissions_are_rejected(self):
        for overrides in (
            {'language': 'klingon'}, {'mode': 'cheat'}, {'scoringVersion': '0'},
            {'durationSec': 14}, {'durationSec': 1801}, {'durationSec': '60'}, {'durationSec': None},
            {'correctUnits': -1}, {'correctUnits': 1.5}, {'correctUnits': '250'}, {'correctUnits': True},
            {'accuracy': 101}, {'accuracy': -1}, {'elapsedSec': 0}, {'elapsedSec': -3}, {'elapsedSec': 70},
            {'correctUnits': 2000}, {'correctUnits': 1000, 'elapsedSec': 3}, {'difficulty': 'god'},
            {'textSize': 'x' * 21},
        ):
            self.assertEqual(self.post(**overrides).status_code, 400, overrides)
        self.assertFalse(TestResult.objects.exists())

    def test_rejects_broken_json(self):
        response = self.client.post('/typing-test/api/results', '{', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/typing-test/api/results', '[1]', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_rate_limit(self):
        for _ in range(20):
            self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.post().status_code, 429)
        self.assertEqual(TestResult.objects.count(), 20)

    def test_personal_best_only_compares_the_same_configuration(self):
        self.assertEqual(self.post().json()['personalBest'], 50)
        response = self.post(correctUnits=300).json()
        self.assertEqual((response['personalBest'], response['isNewBest']), (60, True))
        self.assertEqual(self.post(correctUnits=100).json()['personalBest'], 60)
        self.assertEqual(self.post(language='hindi', correctUnits=100).json()['personalBest'], 20)
        self.assertEqual(self.post(durationSec=120, elapsedSec=120, correctUnits=100).json()['personalBest'], 10)
        self.assertEqual(self.post(mode='paragraph', durationSec=None, textSize='short', correctUnits=100).json()['personalBest'], 20)

    def test_old_history_is_not_touched(self):
        from typingApp.models import Score, TypingTestResult
        Score.objects.create(user=self.user, total_score=500, total_tests=7, best_wpm=88)
        self.post()
        score = Score.objects.get(user=self.user)
        self.assertEqual((score.total_tests, score.best_wpm), (7, 88))
        self.assertEqual(TypingTestResult.objects.count(), 0)


class PreferenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('typist', password='x')
        self.client.force_login(self.user)

    def test_saved_and_returned_to_the_page(self):
        response = self.client.post('/typing-test/api/preferences', json.dumps({'theme': 'dark', 'stopOnError': True}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        config = self.client.get('/english-typing-test').context['config']
        self.assertEqual(config['serverPreferences'], {'theme': 'dark', 'stopOnError': True})

    def test_unknown_values_are_dropped(self):
        self.client.post('/typing-test/api/preferences', json.dumps({'theme': '<script>', 'evil': 1, 'caret': ['x'], 'fontSize': 'large'}), content_type='application/json')
        self.assertEqual(UserPreference.objects.get(user=self.user).settings, {'fontSize': 'large'})

    def test_guests_cannot_save(self):
        response = Client().post('/typing-test/api/preferences', '{}', content_type='application/json')
        self.assertEqual(response.status_code, 401)


class ProgressTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('typist', password='x')
        self.other = get_user_model().objects.create_user('other', password='x')
        self.client.force_login(self.user)

    def add(self, user=None, wpm=50, **fields):
        return TestResult.objects.create(
            user=user or self.user, language='bengali', mode='time', duration_sec=60, correct_units=250,
            incorrect_units=0, corrections=0, attempts=250, elapsed_sec=60, accuracy=99, cpm=wpm * 5, wpm=wpm,
            scoring_version='1', **fields,
        )

    def test_guests_are_sent_to_login_and_page_is_not_indexed(self):
        self.assertEqual(Client().get('/typing-test/progress').status_code, 302)
        self.assertEqual(self.client.get('/typing-test/progress')['X-Robots-Tag'], 'noindex')

    def test_only_your_own_results_show(self):
        self.add(wpm=61)
        self.add(user=self.other, wpm=99)
        response = self.client.get('/typing-test/progress')
        self.assertEqual([item['wpm'] for item in response.context['bests']], [61])
        self.assertEqual(response.context['total_tests'], 1)

    def test_best_is_kept_for_each_configuration(self):
        self.add(wpm=40)
        self.add(wpm=70)
        self.add(wpm=30, text_size='short')
        self.assertEqual(sorted(item['wpm'] for item in self.client.get('/typing-test/progress').context['bests']), [30, 70])

    def test_streak(self):
        today = timezone.localdate()
        for days_ago in (0, 1, 2, 4):
            result = self.add()
            TestResult.objects.filter(pk=result.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
        self.assertEqual(practice_streak(self.user, today), 3)
        self.assertEqual(practice_streak(self.user, today + timedelta(days=1)), 3)
        self.assertEqual(practice_streak(self.user, today + timedelta(days=2)), 0)

    def test_profile_is_saved(self):
        self.client.post('/typing-test/progress', {'display_name': 'Asad', 'default_language': 'bengali'})
        preference = UserPreference.objects.get(user=self.user)
        self.assertEqual((preference.display_name, preference.default_language), ('Asad', 'bengali'))
        self.client.post('/typing-test/progress', {'display_name': 'A', 'default_language': 'nope'})
        self.assertEqual(UserPreference.objects.get(user=self.user).default_language, '')


class DeleteAccountTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('typist', password='x')
        self.client.force_login(self.user)
        TestResult.objects.create(user=self.user, language='bengali', mode='time', correct_units=1, incorrect_units=0,
                                  corrections=0, attempts=1, elapsed_sec=60, accuracy=100, cpm=1, wpm=0.2, scoring_version='1')

    def test_wrong_username_deletes_nothing(self):
        self.client.post('/typing-test/account/delete', {'confirm_username': 'nope'})
        self.assertTrue(get_user_model().objects.filter(username='typist').exists())

    def test_get_does_nothing(self):
        self.assertEqual(self.client.get('/typing-test/account/delete').status_code, 405)
        self.assertTrue(get_user_model().objects.filter(username='typist').exists())

    def test_correct_username_deletes_account_and_results(self):
        self.client.post('/typing-test/account/delete', {'confirm_username': 'typist'})
        self.assertFalse(get_user_model().objects.filter(username='typist').exists())
        self.assertFalse(TestResult.objects.exists())

    def test_staff_cannot_delete_this_way(self):
        admin = get_user_model().objects.create_superuser('boss', 'b@example.com', 'x')
        self.client.force_login(admin)
        self.client.post('/typing-test/account/delete', {'confirm_username': 'boss'})
        self.assertTrue(get_user_model().objects.filter(username='boss').exists())
        self.assertNotContains(self.client.get('/typing-test/progress'), 'Delete my account')


class ServerUnitTests(TestCase):
    def test_units_match_the_shared_fixtures(self):
        fixtures = json.loads((Path(__file__).parent / 'fixtures_scoring.json').read_text(encoding='utf-8'))
        for language, item in fixtures['languages'].items():
            self.assertEqual(split_units(''.join(item['units'])), item['units'], language)

    def test_scoring(self):
        self.assertEqual(score_typed_text('abc', 'axc'), {'correct': 2, 'incorrect': 1, 'typed': 3, 'target': 3})
        self.assertEqual(score_typed_text('tiếng', 'tie')['incorrect'], 0)
        self.assertEqual(score_typed_text('क्ष', 'क')['incorrect'], 0)
        self.assertEqual(score_typed_text('école', 'ec')['incorrect'], 1)
        self.assertEqual(score_typed_text('ab', 'abcd')['incorrect'], 2)
        self.assertEqual(score_typed_text('মি', 'মা')['incorrect'], 1)

    def test_composed_and_decomposed_text_compare_equal(self):
        self.assertEqual(score_typed_text('é', 'é')['correct'], 1)


class RankedSessionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('typist', password='x')
        self.client.force_login(self.user)

    def api(self, url, body):
        return self.client.post(url, json.dumps(body), content_type='application/json')

    def session(self, language='english', mode='words', **fields):
        fields.setdefault('textSize', '50')
        fields.setdefault('difficulty', 'intermediate')
        response = self.api('/typing-test/api/sessions', {'language': language, 'mode': mode, **fields})
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def started(self, seconds_ago=60, **fields):
        data = self.session(**fields)
        self.assertEqual(self.client.post(f"/typing-test/api/sessions/{data['token']}/start").status_code, 200)
        TestSession.objects.filter(token=data['token']).update(started_at=timezone.now() - timedelta(seconds=seconds_ago))
        return data

    def submit(self, data, typed=None, **overrides):
        typed = data['target'] if typed is None else typed
        units = split_units(typed)
        body = dict(payload(language='english', mode='words', durationSec=None, textSize='50'))
        body.update(sessionToken=data['token'], typedText=typed, attempts=len(units), correctUnits=len(units),
                    elapsedSec=30, accuracy=100, inputCategory='desktop', pasteAttempted=False)
        body.update(overrides)
        return self.api('/typing-test/api/results', body)

    def test_guests_get_no_session(self):
        response = Client().post('/typing-test/api/sessions', json.dumps({'language': 'english', 'mode': 'words', 'textSize': '50'}), content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_unranked_setups_get_no_session(self):
        for body in ({'language': 'english', 'mode': 'custom'}, {'language': 'nope', 'mode': 'words', 'textSize': '50'},
                     {'language': 'english', 'mode': 'words', 'textSize': '37', 'difficulty': 'intermediate'},
                     {'language': 'english', 'mode': 'time', 'durationSec': 75, 'difficulty': 'intermediate'},
                     {'language': 'english', 'mode': 'numbers', 'textSize': 'whole-native'}):
            self.assertEqual(self.api('/typing-test/api/sessions', body).status_code, 400, body)

    def test_valid_result_is_ranked_and_scored_by_the_server(self):
        data = self.started()
        response = self.submit(data, correctUnits=1, wpm=9999, cpm=9999).json()
        self.assertTrue(response['ranked'])
        result = TestResult.objects.get()
        self.assertEqual(result.correct_units, len(split_units(data['target'])))
        self.assertAlmostEqual(result.wpm, result.correct_units / 5, delta=2)

    def test_wrong_text_scores_lower_whatever_the_browser_claims(self):
        data = self.started()
        self.submit(data, typed='x' * len(split_units(data['target'])), correctUnits=500, accuracy=100)
        result = TestResult.objects.get()
        self.assertEqual(result.correct_units, 0)
        self.assertFalse(result.is_ranked)

    def test_session_works_only_once(self):
        data = self.started()
        self.assertEqual(self.submit(data).status_code, 200)
        self.assertEqual(self.submit(data).status_code, 400)
        self.assertEqual(TestResult.objects.count(), 1)

    def test_another_users_session_is_refused(self):
        data = self.started()
        other = get_user_model().objects.create_user('other', password='x')
        self.client.force_login(other)
        self.assertEqual(self.submit(data).status_code, 400)
        self.assertEqual(self.client.post(f"/typing-test/api/sessions/{data['token']}/start").status_code, 404)

    def test_not_started_or_too_fast_is_refused(self):
        self.assertEqual(self.submit(self.session()).status_code, 400)
        self.assertEqual(self.submit(self.started(seconds_ago=20), elapsedSec=30).status_code, 400)
        fast = self.started(seconds_ago=20)
        self.assertEqual(self.submit(fast, elapsedSec=20).status_code, 400 if len(split_units(fast['target'])) / 5 / (20 / 60) > 250 else 200)

    def test_impossible_speed_on_the_server_clock_is_refused(self):
        data = self.started(seconds_ago=1, textSize='200')
        self.assertEqual(self.submit(data, elapsedSec=1).status_code, 400)
        self.assertFalse(TestResult.objects.exists())

    def test_fast_results_are_flagged_and_hidden(self):
        data = self.started(seconds_ago=15, textSize='50')
        units = len(split_units(data['target']))
        seconds = units / 5 / 200 * 60
        TestSession.objects.filter(token=data['token']).update(started_at=timezone.now() - timedelta(seconds=seconds))
        response = self.submit(data, elapsedSec=seconds).json()
        result = TestResult.objects.get()
        if seconds >= 15:
            self.assertEqual(result.review_status, TestResult.FLAGGED)
            self.assertTrue(response['underReview'])
        self.assertEqual(self.client.get('/typing-test/leaderboard?size=50&mode=words').context['rows'], [])

    def test_practice_only_reasons(self):
        cases = (({'pasteAttempted': True}, 'Paste'), ({'inputCategory': 'robot'}, 'input type'))
        for overrides, reason in cases:
            response = self.submit(self.started(), **overrides).json()
            self.assertFalse(response['ranked'])
            self.assertIn(reason, response['reason'])
        response = self.submit(self.started(), typed='the').json()
        self.assertFalse(response['ranked'])
        self.assertFalse(TestResult.objects.filter(is_ranked=True).exists())

    def test_timed_test_must_run_its_full_time(self):
        data = self.started(seconds_ago=30, mode='time', durationSec=60, textSize='')
        typed = ''.join(split_units(data['target'])[:100])
        response = self.submit(data, typed=typed, durationSec=60, mode='time', textSize='', elapsedSec=30).json()
        self.assertFalse(response['ranked'])
        data = self.started(seconds_ago=61, mode='time', durationSec=60, textSize='')
        typed = ''.join(split_units(data['target'])[:100])
        response = self.submit(data, typed=typed, durationSec=60, mode='time', textSize='', elapsedSec=60).json()
        self.assertTrue(response['ranked'])
        self.assertEqual(TestResult.objects.filter(is_ranked=True).get().elapsed_sec, 60)

    def test_results_without_a_session_are_never_ranked(self):
        self.api('/typing-test/api/results', payload(is_ranked=True, ranked=True))
        self.assertFalse(TestResult.objects.get().is_ranked)

    def test_session_rate_limit(self):
        for _ in range(30):
            self.session()
        response = self.api('/typing-test/api/sessions', {'language': 'english', 'mode': 'words', 'textSize': '50', 'difficulty': 'intermediate'})
        self.assertEqual(response.status_code, 429)

    def test_every_language_and_mode_can_start_a_session(self):
        TestSession.objects.all().delete()
        for language in LANGUAGES:
            counts = '50' if language.word_boundary == 'spaces' else '100'
            bodies = [
                {'mode': 'time', 'durationSec': 60, 'difficulty': 'beginner'},
                {'mode': 'words', 'textSize': counts, 'difficulty': 'advanced'},
                {'mode': 'paragraph', 'textSize': 'long'},
                {'mode': 'numbers', 'textSize': 'mixed-western'},
            ]
            for body in bodies:
                TestSession.objects.all().delete()
                response = self.api('/typing-test/api/sessions', {'language': language.code, **body})
                self.assertEqual(response.status_code, 200, (language.code, body))
                self.assertTrue(response.json()['target'])

    def test_native_digit_session(self):
        data = self.session(language='bengali', mode='numbers', textSize='whole-native')
        self.assertRegex(data['target'], r'^[০-৯ ]+$')


class LeaderboardTests(TestCase):
    def add(self, username, wpm, display='', **fields):
        user, _ = get_user_model().objects.get_or_create(username=username)
        if display:
            UserPreference.objects.update_or_create(user=user, defaults={'display_name': display})
        defaults = dict(language='english', mode='time', duration_sec=60, difficulty='intermediate', input_category='desktop',
                        is_ranked=True, correct_units=100, incorrect_units=0, corrections=0, attempts=100, elapsed_sec=60,
                        accuracy=99, cpm=wpm * 5, wpm=wpm, scoring_version='1')
        defaults.update(fields)
        return TestResult.objects.create(user=user, **defaults)

    def rows(self, query=''):
        return self.client.get('/typing-test/leaderboard' + query).context['rows']

    def test_empty_state(self):
        response = self.client.get('/typing-test/leaderboard')
        self.assertContains(response, 'No validated results for this board yet')
        self.assertContains(response, 'Competition Rules')

    def test_each_person_once_best_first(self):
        self.add('a', 50)
        self.add('a', 70)
        self.add('b', 60)
        self.assertEqual([(r['name'], r['wpm']) for r in self.rows()], [('a', 70), ('b', 60)])

    def test_unranked_and_hidden_results_stay_off(self):
        self.add('practice', 90, is_ranked=False)
        self.add('flagged', 90, review_status=TestResult.FLAGGED)
        self.add('rejected', 90, review_status=TestResult.REJECTED)
        self.add('approved', 40, review_status=TestResult.APPROVED)
        self.assertEqual([r['name'] for r in self.rows()], ['approved'])

    def test_unlike_results_stay_apart(self):
        self.add('en', 50)
        self.add('bn', 50, language='bengali')
        self.add('two', 50, duration_sec=120)
        self.add('hard', 50, difficulty='advanced')
        self.add('phone', 50, input_category='mobile')
        self.add('ime', 50, input_category='ime')
        self.add('words', 50, mode='words', duration_sec=None, text_size='50')
        self.add('num', 50, mode='numbers', duration_sec=None, text_size='whole-western', difficulty='')
        self.assertEqual([r['name'] for r in self.rows()], ['en'])
        self.assertEqual([r['name'] for r in self.rows('?language=bengali')], ['bn'])
        self.assertEqual([r['name'] for r in self.rows('?duration=120')], ['two'])
        self.assertEqual([r['name'] for r in self.rows('?difficulty=advanced')], ['hard'])
        self.assertEqual([r['name'] for r in self.rows('?category=mobile')], ['phone'])
        self.assertEqual([r['name'] for r in self.rows('?category=ime')], ['ime'])
        self.assertEqual([r['name'] for r in self.rows('?mode=words&size=50')], ['words'])
        self.assertEqual([r['name'] for r in self.rows('?mode=numbers&size=whole-western')], ['num'])

    def test_periods(self):
        old = self.add('old', 90)
        TestResult.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=3))
        ancient = self.add('ancient', 99)
        TestResult.objects.filter(pk=ancient.pk).update(created_at=timezone.now() - timedelta(days=30))
        self.add('new', 50)
        self.assertEqual([r['name'] for r in self.rows('?period=daily')], ['new'])
        self.assertEqual([r['name'] for r in self.rows('?period=weekly')], ['old', 'new'])
        self.assertEqual([r['name'] for r in self.rows()], ['ancient', 'old', 'new'])

    def test_names_are_escaped_and_display_name_is_used(self):
        self.add('plainname', 50, display='<script>alert(1)</script>')
        response = self.client.get('/typing-test/leaderboard')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, 'plainname')

    def test_bad_filters_fall_back_and_filter_pages_are_not_indexed(self):
        response = self.client.get('/typing-test/leaderboard?language=<x>&mode=custom&duration=1&period=zzz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Robots-Tag'], 'noindex')
        self.assertEqual(response.context['selected']['mode'], 'time')
        self.assertNotIn('X-Robots-Tag', self.client.get('/typing-test/leaderboard'))


class ContentReviewTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser('boss', 'b@example.com', 'x')

    def approve(self, code):
        ContentItem.objects.filter(language=code).update(review_status=ContentItem.APPROVED)

    def test_seed_content_is_loaded_and_unreviewed(self):
        self.assertEqual(ContentItem.objects.count(), 40)
        for language in LANGUAGES:
            self.assertEqual(content_for(language.code)['words'], STARTER_WORDS[language.code])
            self.assertEqual(content_for(language.code)['paragraph'], STARTER_PARAGRAPHS[language.code])
            self.assertFalse(is_language_reviewed(language.code))
        self.assertIn('Not native-reviewed', ContentItem.objects.first().source_or_license)

    def test_approving_a_language_opens_it_to_search(self):
        self.assertEqual(self.client.get('/bengali-typing-test')['X-Robots-Tag'], 'noindex')
        self.assertNotIn('/bengali-typing-test<', self.client.get('/sitemap.xml').content.decode())
        ContentItem.objects.filter(language='bengali', content_type=ContentItem.WORD_LIST).update(review_status=ContentItem.APPROVED)
        self.assertFalse(is_language_reviewed('bengali'))
        self.approve('bengali')
        response = self.client.get('/bengali-typing-test')
        self.assertNotIn('X-Robots-Tag', response)
        self.assertNotContains(response, 'has not yet been reviewed')
        sitemap = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('https://taptaptyping.com/bengali-typing-test/3-minutes<', sitemap)
        self.assertNotIn('hindi-typing-test', sitemap)

    def test_editing_approved_text_needs_review_again(self):
        self.approve('hindi')
        item = ContentItem.objects.filter(language='hindi', content_type=ContentItem.WORD_LIST).first()
        self.client.force_login(self.staff)
        response = self.client.post(f'/admin/typingtest/contentitem/{item.pk}/change/', {
            'language': item.language, 'content_type': item.content_type, 'difficulty': '', 'text': item.text + ' नया',
            'source_or_license': item.source_or_license, 'review_status': item.review_status,
        })
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual((item.version, item.review_status), (2, ContentItem.UNREVIEWED))

    def test_admin_action_records_the_reviewer(self):
        self.client.force_login(self.staff)
        item = ContentItem.objects.first()
        self.client.post('/admin/typingtest/contentitem/', {'action': 'approve', '_selected_action': [item.pk]})
        item.refresh_from_db()
        self.assertEqual((item.review_status, item.reviewed_by), (ContentItem.APPROVED, self.staff))

    def test_rejected_text_stops_showing(self):
        ContentItem.objects.filter(language='french', content_type=ContentItem.PARAGRAPH).update(review_status=ContentItem.REJECTED)
        self.assertEqual(content_for('french')['paragraph'], [])
        self.assertFalse(is_language_reviewed('french'))

    def test_review_page_is_staff_only(self):
        self.assertEqual(self.client.get('/typing-test/review').status_code, 302)
        user = get_user_model().objects.create_user('user', password='x')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/typing-test/review').status_code, 403)
        self.client.force_login(self.staff)
        response = self.client.get('/typing-test/review')
        self.assertEqual(len(response.context['rows']), 20)
        self.assertEqual(response['X-Robots-Tag'], 'noindex')

    def test_admin_pages_open(self):
        self.client.force_login(self.staff)
        for name in ('contentitem', 'contentreport', 'testresult', 'testsession', 'userpreference'):
            self.assertEqual(self.client.get(f'/admin/typingtest/{name}/').status_code, 200, name)

    def test_flagged_result_can_be_approved_in_admin(self):
        user = get_user_model().objects.create_user('fast', password='x')
        result = TestResult.objects.create(user=user, language='english', mode='time', duration_sec=60, difficulty='intermediate',
                                           input_category='desktop', is_ranked=True, review_status=TestResult.FLAGGED, correct_units=1,
                                           incorrect_units=0, corrections=0, attempts=1, elapsed_sec=60, accuracy=100, cpm=1, wpm=200, scoring_version='1')
        self.client.force_login(self.staff)
        self.client.post('/admin/typingtest/testresult/', {'action': 'approve_flagged', '_selected_action': [result.pk]})
        result.refresh_from_db()
        self.assertEqual(result.review_status, TestResult.APPROVED)


class ReportTests(TestCase):
    def post(self, **overrides):
        body = {'language': 'bengali', 'mode': 'words', 'message': 'A word is misspelled', 'excerpt': 'আমি'}
        body.update(overrides)
        return self.client.post('/typing-test/api/report', json.dumps(body), content_type='application/json')

    def test_guest_can_report(self):
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(ContentReport.objects.get().language, 'bengali')

    def test_bad_reports_and_custom_text_are_refused(self):
        self.assertEqual(self.post(message='   ').status_code, 400)
        self.assertEqual(self.post(language='nope').status_code, 400)
        self.assertEqual(self.post(mode='custom').status_code, 400)
        self.assertNotContains(self.client.get('/english-typing-test/custom-text'), 'reportForm')

    def test_rate_limit(self):
        for _ in range(5):
            self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.post().status_code, 429)
