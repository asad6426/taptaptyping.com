import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from .models import Score, TypingTestResult
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
        self.assertNotContains(response, 'Completed')

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
