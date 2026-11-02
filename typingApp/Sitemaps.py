from django.contrib.sitemaps import Sitemap


class BlogPostSitemap(Sitemap):
    """Sitemap for blog posts from blog app"""
    changefreq = "weekly"
    priority = 0.8
    protocol = 'https'

    def items(self):
        try:
            from blog.models import Post
            return Post.objects.all().order_by('-created_at')
        except Exception:
            return []

    def location(self, obj):
        return f'/{obj.slug}/'


class StaticViewSitemap(Sitemap):
    """Sitemap for static/important pages"""
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return [
            ('/', 1.0),
            ('/taptap/', 0.9),
            ('/typing-lessons/', 0.9),
            ('/typingGames/', 0.8),
            ('/blogs/', 0.8),
            ('/jobs/', 0.7),
            ('/FAQ/', 0.6),
            ('/aboutus/', 0.5),
        ]

    def location(self, item):
        return item[0]

    def priority(self, item):
        return item[1]