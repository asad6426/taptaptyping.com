import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from .models import BlogPost


class BlogSlugTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('admin', 'a@example.com', 'x')
        self.client.force_login(self.admin)

    def save(self, **overrides):
        data = dict(title='Typing Tips', content='<p>Body</p>', published=True)
        data.update(overrides)
        response = self.client.post('/blog/api/save/', json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_typed_slug_with_spaces_can_be_viewed(self):
        result = self.save(slug='typing speed test Check WPM and Accuracy')
        self.assertEqual(result['slug'], 'typing-speed-test-check-wpm-and-accuracy')
        self.assertEqual(self.client.get(result['public_url']).status_code, 200)

    def test_empty_slug_uses_the_title(self):
        self.assertEqual(self.save()['slug'], 'typing-tips')

    def test_title_without_latin_letters_can_be_viewed(self):
        result = self.save(title='টাইপিং শেখার উপায়')
        self.assertEqual(result['slug'], 'post')
        self.assertEqual(self.client.get(result['public_url']).status_code, 200)

    def test_duplicate_slug_gets_a_suffix_instead_of_failing(self):
        self.assertEqual(self.save(slug='same')['slug'], 'same')
        self.assertEqual(self.save(slug='same')['slug'], 'same-2')

    def test_editing_keeps_the_slug(self):
        first = self.save(slug='keep-me')
        self.assertEqual(self.save(id=first['post_id'], slug='keep-me')['slug'], 'keep-me')

    def test_slug_cannot_hide_another_page(self):
        result = self.save(slug='blogs')
        self.assertEqual(result['slug'], 'blogs-2')
        self.assertEqual(self.client.get(result['public_url']).status_code, 200)
        self.assertTemplateUsed(self.client.get('/blogs/'), 'blogs.html')

    def test_absolute_url_and_list_view_link_work(self):
        result = self.save()
        post = BlogPost.objects.get(pk=result['post_id'])
        self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 200)
        self.assertContains(self.client.get('/blog/'), f'https://taptaptyping.com{post.get_absolute_url()}')

    def test_repair_command_fixes_only_broken_slugs(self):
        good = BlogPost.objects.create(title='Good', slug='good-post', author=self.admin, published=True)
        bad = BlogPost.objects.create(title='Bad', slug='bad slug here', author=self.admin, published=True)

        call_command('fix_blog_slugs', stdout=StringIO())
        bad.refresh_from_db()
        self.assertEqual(bad.slug, 'bad slug here')

        call_command('fix_blog_slugs', '--apply', stdout=StringIO())
        bad.refresh_from_db()
        good.refresh_from_db()
        self.assertEqual((bad.slug, good.slug), ('bad-slug-here', 'good-post'))
        self.assertEqual(self.client.get('/bad-slug-here/').status_code, 200)


class BlogListTests(TestCase):
    def test_only_all_posts_filter_remains(self):
        author = get_user_model().objects.create_user('writer', password='x')
        BlogPost.objects.create(title='One', slug='one', author=author, published=True, category='Typing, typingtest')
        response = self.client.get('/blogs/')
        self.assertContains(response, 'All Posts')
        self.assertContains(response, 'class="filter-btn', count=1)
