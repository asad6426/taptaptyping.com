import json
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from blog.models import BlogPost

from .content import CONTENT_STATUS, STARTER_PARAGRAPHS, STARTER_WORDS
from .account_views import practice_streak
from .languages import DURATIONS, LANGUAGES
from .models import TestResult, UserPreference


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
        self.assertEqual(CONTENT_STATUS, 'unreviewed')
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
