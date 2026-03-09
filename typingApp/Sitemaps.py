from django.contrib.sitemaps import Sitemap
from .models import BlogPost


class BlogPostSitemap(Sitemap):
    """Sitemap for blog posts"""
    changefreq = "weekly"
    priority = 0.8
    protocol = 'https'  # Change to 'http' if your site doesn't use HTTPS
    
    def items(self):
        # Only include posts that are not marked as noindex
        return BlogPost.objects.filter(noindex=False).order_by('-posted_date')
    
    def lastmod(self, obj):
        return obj.updated_date
    
    def location(self, obj):
        return f'/blog/{obj.slug}/'


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 0.5
    changefreq = 'monthly'
    protocol = 'https'
    
    def items(self):
        return ['home', 'about', 'contact']  # Add your static page names
    
    def location(self, item):
        if item == 'home':
            return '/'
        return f'/{item}/'