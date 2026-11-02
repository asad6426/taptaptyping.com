from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class SiteSitemap(Sitemap):
    """Writes this site's own domain, whatever the django_site table says"""
    protocol = 'https'
    domain = 'taptaptyping.com'

    def get_domain(self, site=None):
        return self.domain


class StaticViewSitemap(SiteSitemap):
    """Public pages. Redirects and login-only pages are left out on purpose."""
    changefreq = 'weekly'

    def items(self):
        return [
            ('/', 1.0),
            ('/taptap/', 0.9),
            ('/typing-lessons/', 0.9),
            ('/blogs/', 0.8),
            ('/leaderboard/', 0.7),
            ('/jobpost/', 0.7),
            ('/jobs/', 0.6),
            ('/FAQ/', 0.6),
            ('/aboutus/', 0.5),
            ('/policy/', 0.3),
        ]

    def location(self, item):
        return item[0]

    def priority(self, item):
        return item[1]


class LessonSitemap(SiteSitemap):
    """Every lesson page, by url name"""
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return [
            'FJ', 'GH', 'DK', 'SL', 'A', 'homeRowPractice',
            'RU', 'TY', 'EI', 'WO', 'QP', 'topRowPractice',
            'VN', 'BB', 'CM', 'X', 'Z', 'BottomRowPractce',
            'S', 'C', 'V', 'ZN', 'XM', 'RI', 'EO', 'WP', 'QU', 'DL', 'FK', 'AJ', 'M',
        ]

    def location(self, item):
        return reverse(item)


class BlogPostSitemap(SiteSitemap):
    """Published posts from the blog editor"""
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        from blog.models import BlogPost
        return BlogPost.objects.filter(published=True).order_by('-created_at')

    def location(self, post):
        return post.get_absolute_url()

    def lastmod(self, post):
        return post.updated_at


class JobPostSitemap(SiteSitemap):
    """Published job posts"""
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        from jobpost.models import JobPost
        return JobPost.objects.filter(published=True).order_by('-updated_date')

    def location(self, job):
        return reverse('jobpost:detail', args=[job.pk])

    def lastmod(self, job):
        return job.updated_date


class GamesSitemap(SiteSitemap):
    """The games hub and every game, for game.taptaptyping.com"""
    domain = 'game.taptaptyping.com'
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        from games.registry import GAMES
        return ['/'] + [f"/play/{game['slug']}/" for game in GAMES]

    def location(self, path):
        return path
