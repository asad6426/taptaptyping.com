import json
import re
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from blog.models import BlogPost
from games.registry import GAMES
from jobpost.models import JobPost

from .models import LessonProgress, Score, TypingTestResult
from .scoring import LESSON_SLUGS
from .urls import urlpatterns as typing_urlpatterns
from .views import PUBLIC_USER_COUNT_MIN, build_leaderboard, public_user_count


class PublicUserCountTests(TestCase):
    def setUp(self):
        cache.clear()

    def add_users(self, count):
        User = get_user_model()
        User.objects.bulk_create(User(username=f'user{i}') for i in range(count))

    def test_hidden_below_minimum(self):
        self.add_users(PUBLIC_USER_COUNT_MIN - 1)
        self.assertIsNone(public_user_count())
        response = self.client.get('/')
        self.assertNotContains(response, 'registered users')
        self.assertNotContains(response, 'million')

    def test_shown_at_minimum(self):
        self.add_users(PUBLIC_USER_COUNT_MIN)
        self.assertEqual(public_user_count(), '1,000+')
        self.assertContains(self.client.get('/'), '1,000+ registered users')
        self.assertContains(self.client.get('/leaderboard/'), 'Registered Users')

    def test_rounds_down_to_nearest_hundred(self):
        self.add_users(1250)
        self.assertEqual(public_user_count(), '1,200+')

    def test_inactive_users_not_counted(self):
        self.add_users(PUBLIC_USER_COUNT_MIN)
        get_user_model().objects.filter(username='user0').update(is_active=False)
        self.assertIsNone(public_user_count())


class LeaderboardClaimsTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_unverified_claims_removed(self):
        response = self.client.get('/leaderboard/')
        for text in ('10K+', '50K+', '95%', '300%', 'Verified', 'Customer Reviews',
                     'Happy Families', 'Success Rate', 'Registered Users'):
            self.assertNotContains(response, text)


class HomepageTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_home_is_the_typing_test_page(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'home2.html')
        self.assertContains(response, '<title>TapTapTyping - Free Online Typing Speed Test')
        self.assertContains(response, 'Test Your Typing Speed in <span id="durationHeading">60 Seconds</span></h1>')
        self.assertNotContains(response, 'GLOBAL LEADERBOARD')

    def test_form_only_offers_options_the_test_supports(self):
        response = self.client.get('/')
        self.assertNotContains(response, 'value="180"')
        for level in ('Easy', 'Medium', 'Hard'):
            self.assertContains(response, f'<option value="{level}"')
        test_page = self.client.get('/taptap/')
        for seconds in (30, 60, 120, 300, 600):
            self.assertContains(response, f'<option value="{seconds}"')
            self.assertContains(test_page, f'data-time="{seconds}"')

    def test_home_links_to_every_section(self):
        response = self.client.get('/')
        for path in ('/taptap/', '/typing-lessons/', '/typingGames/', '/leaderboard/',
                     '/dashboard/', '/certificate/', '/blogs/'):
            self.assertContains(response, f'class="home-card" href="{path}"')

    def test_added_text_uses_the_chosen_text_type(self):
        self.assertContains(self.client.get('/taptap/'), 'const additionalText = applyTextType(')

    def test_leaderboard_has_its_own_url(self):
        response = self.client.get('/leaderboard/')
        self.assertContains(response, 'GLOBAL LEADERBOARD')
        self.assertContains(response, 'href="https://taptaptyping.com/leaderboard/"')

    def test_old_start_url_redirects_permanently(self):
        response = self.client.get('/s/?ref=x')
        self.assertRedirects(response, '/?ref=x', status_code=301)

    def test_sitemap_lists_leaderboard(self):
        self.assertContains(self.client.get('/sitemap.xml'), '/leaderboard/')


class LessonPageTests(TestCase):
    def test_new_url_has_no_hardcoded_progress(self):
        response = self.client.get('/typing-lessons/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lesson 1')
        self.assertNotContains(response, '45%')
        self.assertNotContains(response, '100% Completed')

    def test_old_url_redirects_permanently(self):
        response = self.client.get('/typingLession/?ref=x')
        self.assertRedirects(response, '/typing-lessons/?ref=x', status_code=301)


def add_result(user, wpm, accuracy=95, time_taken=60, correct_entries=None):
    if correct_entries is None:
        correct_entries = int(wpm * 5 * time_taken / 60)
    Score.objects.get_or_create(user=user)
    return TypingTestResult.objects.create(
        user=user, test_duration=time_taken, time_taken=time_taken, time_taken_formatted='',
        wpm=wpm, accuracy=accuracy, correct_entries=correct_entries, incorrect_entries=0,
        fixed_mistakes=0, total_entries=correct_entries, error_rate=0, raw_speed=wpm,
        key_speed=wpm * 5, complete_words=0,
    )


class RankingTests(TestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.fast = User.objects.create_user('fast', password='x')
        self.slow = User.objects.create_user('slow', password='x')

    def test_more_tests_do_not_beat_better_tests(self):
        for _ in range(100):
            add_result(self.slow, 20)
        for _ in range(5):
            add_result(self.fast, 80)
        self.assertEqual([s.user for s in build_leaderboard()], [self.fast, self.slow])

    def test_needs_minimum_counted_tests(self):
        for _ in range(4):
            add_result(self.fast, 80)
        self.assertEqual(build_leaderboard(), [])

    def test_only_last_ten_tests_count(self):
        for _ in range(10):
            add_result(self.fast, 20)
        for _ in range(10):
            add_result(self.fast, 80)
        self.assertEqual(build_leaderboard()[0].ranked_wpm, 80)

    def test_implausible_and_short_tests_are_ignored(self):
        for _ in range(5):
            add_result(self.fast, 60)
        add_result(self.fast, 4000, time_taken=30)
        add_result(self.fast, 60, time_taken=5)
        add_result(self.fast, 60, time_taken=30, correct_entries=1000)
        self.assertEqual(build_leaderboard()[0].ranked_wpm, 60)

    def test_rank_and_rules_are_shown(self):
        for _ in range(5):
            add_result(self.fast, 80)
            add_result(self.slow, 20)
        self.client.force_login(self.slow)
        response = self.client.get('/leaderboard/')
        self.assertContains(response, '<span class="rank-number-large">#2</span>')
        self.assertContains(response, 'How ranking works')
        self.assertContains(response, 'FAST')


class GameSubdomainTests(TestCase):
    host = 'game.taptaptyping.com'

    def setUp(self):
        cache.clear()

    def test_home_is_the_games_hub(self):
        response = self.client.get('/', HTTP_HOST=self.host)
        self.assertTemplateUsed(response, 'games/hub.html')
        self.assertNotContains(response, 'durationHeading')

    def test_every_game_opens(self):
        for game in GAMES:
            response = self.client.get(f"/play/{game['slug']}/", HTTP_HOST=self.host)
            self.assertEqual(response.status_code, 200, game['slug'])

    def test_shared_routes_still_work(self):
        self.assertTemplateUsed(self.client.get('/s/', HTTP_HOST=self.host), 'home2.html')
        self.assertTemplateUsed(self.client.get('/typing-leaderboard/', HTTP_HOST=self.host), 'leaderboard.html')

    def test_home_links_leave_the_game_site(self):
        response = self.client.get('/', HTTP_HOST=self.host)
        self.assertContains(response, '<a class="nav-link" href="https://taptaptyping.com/">Home</a>')
        self.assertNotContains(response, 'href="/s/"')

    def test_main_site_home_is_unchanged(self):
        self.assertTemplateUsed(self.client.get('/'), 'home2.html')


class SitemapTests(TestCase):
    def setUp(self):
        cache.clear()
        author = get_user_model().objects.create_user('writer', password='x')
        BlogPost.objects.create(title='Live', slug='live-post', author=author, published=True)
        BlogPost.objects.create(title='Draft', slug='draft-post', author=author, published=False)
        JobPost.objects.create(title='Open job', published=True)
        JobPost.objects.create(title='Closed job', published=False)

    def locations(self, **extra):
        response = self.client.get('/sitemap.xml', **extra)
        self.assertEqual(response.status_code, 200)
        return re.findall(r'<loc>([^<]+)</loc>', response.content.decode())

    def test_uses_the_real_domain_whatever_the_site_table_says(self):
        Site.objects.update_or_create(id=1, defaults={'domain': 'example.com', 'name': 'example.com'})
        for location in self.locations():
            self.assertTrue(location.startswith('https://taptaptyping.com/'), location)

    def test_lists_lessons_and_published_content_only(self):
        paths = {location.replace('https://taptaptyping.com', '') for location in self.locations()}
        self.assertLessEqual({'/', '/taptap/', '/typing-lessons/', '/blogs/', '/live-post/'}, paths)
        self.assertLessEqual({reverse(slug) for slug in LESSON_SLUGS}, paths)
        self.assertEqual(len([p for p in paths if p.startswith('/lession_')]), 31)
        self.assertNotIn('/draft-post/', paths)
        self.assertEqual(len([p for p in paths if p.startswith('/jobpost/') and p != '/jobpost/']), 1)

    def test_every_listed_page_opens_without_a_redirect(self):
        for location in self.locations():
            path = location.replace('https://taptaptyping.com', '')
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_lesson_routes_are_all_listed(self):
        routes = {f'/{p.pattern}' for p in typing_urlpatterns if str(p.pattern).startswith('lession_')}
        paths = {location.replace('https://taptaptyping.com', '') for location in self.locations()}
        self.assertEqual(routes, paths & routes)

    def test_game_site_has_its_own_sitemap(self):
        locations = self.locations(HTTP_HOST='game.taptaptyping.com')
        self.assertEqual(len(locations), len(GAMES) + 1)
        for location in locations:
            self.assertTrue(location.startswith('https://game.taptaptyping.com/'), location)
            path = location.replace('https://game.taptaptyping.com', '')
            self.assertEqual(self.client.get(path, HTTP_HOST='game.taptaptyping.com').status_code, 200, path)


class DashboardRankTests(TestCase):
    def test_dashboard_uses_leaderboard_rank(self):
        User = get_user_model()
        fast = User.objects.create_user('fast', password='x')
        slow = User.objects.create_user('slow', password='x')
        for _ in range(5):
            add_result(fast, 80)
            add_result(slow, 20)
        self.client.force_login(slow)
        response = self.client.get('/dashboard/')
        self.assertEqual(response.context['rank'], 2)
        self.assertEqual(response.context['total_users'], 2)


class FakeResultTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cheater = User.objects.create_user('cheater', password='x')
        self.honest = User.objects.create_user('honest', password='x')
        add_result(self.cheater, 50)
        add_result(self.cheater, 70)
        add_result(self.cheater, 4000, time_taken=3)
        add_result(self.honest, 40)
        Score.objects.filter(user=self.cheater).update(total_tests=3, best_wpm=4000, average_wpm=1373.33)
        Score.objects.filter(user=self.honest).update(total_tests=1, best_wpm=99)

    def test_dashboard_hides_impossible_results(self):
        self.client.force_login(self.cheater)
        response = self.client.get('/dashboard/')
        self.assertEqual([t.wpm for t in response.context['recent_tests']], [70, 50])
        self.assertEqual(json.loads(response.context['chart_wpm']), [50, 70])
        self.assertEqual(response.context['wpm_improvement'], 20)

    def test_dry_run_changes_nothing(self):
        call_command('rebuild_scores', stdout=StringIO())
        self.assertEqual(Score.objects.get(user=self.cheater).best_wpm, 4000)

    def test_apply_fixes_only_affected_users_and_keeps_results(self):
        call_command('rebuild_scores', '--apply', stdout=StringIO())
        score = Score.objects.get(user=self.cheater)
        self.assertEqual((score.total_tests, score.best_wpm, float(score.average_wpm)), (2, 70, 60.0))
        self.assertEqual(Score.objects.get(user=self.honest).best_wpm, 99)
        self.assertEqual(TypingTestResult.objects.filter(user=self.cheater).count(), 3)


class LessonProgressTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('learner', password='x')
        self.client.force_login(self.user)

    def post(self, **overrides):
        data = dict(
            lesson='FJ', test_duration=60, time_taken=60, time_taken_formatted='1:00', wpm=30, accuracy=80,
            correct_entries=150, incorrect_entries=5, fixed_mistakes=0, total_entries=155,
            error_rate=2, raw_speed=31, key_speed=155, complete_words=30,
        )
        data.update(overrides)
        response = self.client.post('/typing/save/', json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_keeps_the_best_result(self):
        self.post(accuracy=85, wpm=20)
        self.post(accuracy=70, wpm=35)
        progress = LessonProgress.objects.get(user=self.user, lesson='FJ')
        self.assertEqual((progress.attempts, float(progress.best_accuracy), progress.best_wpm, progress.completed),
                         (2, 85.0, 35, False))

    def test_completed_at_pass_mark_and_stays_completed(self):
        self.post(accuracy=90)
        self.post(accuracy=60)
        self.assertTrue(LessonProgress.objects.get(user=self.user, lesson='FJ').completed)

    def test_too_few_characters_do_not_count(self):
        self.post(accuracy=100, correct_entries=5)
        self.assertFalse(LessonProgress.objects.exists())

    def test_unknown_lesson_and_plain_tests_do_not_count(self):
        self.post(lesson='nope')
        self.post(lesson=None)
        self.assertFalse(LessonProgress.objects.exists())
        self.assertEqual(TypingTestResult.objects.count(), 2)

    def test_every_lesson_page_names_itself_and_is_on_the_map(self):
        lesson_map = self.client.get('/typing-lessons/')
        for slug in LESSON_SLUGS:
            self.assertContains(self.client.get(reverse(slug)), f"lesson: '{slug}',")
            self.assertContains(lesson_map, f'data-lesson="{slug}"')

    def test_map_only_shows_your_own_progress(self):
        self.post(accuracy=95)
        response = self.client.get('/typing-lessons/')
        self.assertEqual(response.context['lesson_progress'], {'FJ': {'best_accuracy': 95.0, 'completed': True}})
        other = get_user_model().objects.create_user('other', password='x')
        self.client.force_login(other)
        self.assertEqual(self.client.get('/typing-lessons/').context['lesson_progress'], {})
        self.client.logout()
        self.assertEqual(self.client.get('/typing-lessons/').context['lesson_progress'], {})


class SaveResultTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('typist', password='x')
        self.client.force_login(self.user)

    def post(self, **overrides):
        data = dict(
            test_duration=60, time_taken=60, time_taken_formatted='1:00', wpm=60, accuracy=95,
            correct_entries=300, incorrect_entries=5, fixed_mistakes=0, total_entries=305,
            error_rate=2, raw_speed=61, key_speed=305, complete_words=60,
        )
        data.update(overrides)
        return self.client.post('/typing/save/', json.dumps(data), content_type='application/json')

    def test_normal_result_is_saved(self):
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(TypingTestResult.objects.count(), 1)

    def test_impossible_results_are_rejected(self):
        for overrides in ({'wpm': 360}, {'correct_entries': 1000, 'time_taken': 3}, {'time_taken': 0},
                          {'wpm': -5}, {'wpm': None}, {'wpm': 'fast'}):
            self.assertEqual(self.post(**overrides).status_code, 400, overrides)
        self.assertEqual(TypingTestResult.objects.count(), 0)
        self.assertFalse(Score.objects.filter(user=self.user).exists())
