from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from .views import PUBLIC_USER_COUNT_MIN, public_user_count


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
        self.assertContains(response, '<h1 class="header-title">Free Typing Speed Test</h1>')
        self.assertNotContains(response, 'GLOBAL LEADERBOARD')

    def test_form_only_offers_options_the_test_supports(self):
        response = self.client.get('/')
        self.assertNotContains(response, 'text_type')
        self.assertNotContains(response, 'value="180"')
        test_page = self.client.get('/taptap/')
        for seconds in (30, 60, 120, 300, 600):
            self.assertContains(response, f'<option value="{seconds}"')
            self.assertContains(test_page, f'data-time="{seconds}"')

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
