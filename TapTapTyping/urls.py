"""
URL configuration for TapTapTyping project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from accounts import views


# ── Inline Sitemaps ──────────────────────────────────────────
class StaticViewSitemap(Sitemap):
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


sitemaps = {
    'static': StaticViewSitemap,
}


# ── robots.txt ───────────────────────────────────────────────
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /login/",
        "Disallow: /signup/",
        "Disallow: /dashboard/",
        "Disallow: /typing/save/",
        "",
        "Sitemap: https://taptaptyping.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


# ── URL Patterns ─────────────────────────────────────────────
urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password_view, name='reset_password'),
    path('blog/', include('blog.urls')),
    path('jobpost/', include('jobpost.urls')),
    path('certificate/', include('certificate.urls')),
    path('accounts/', include('allauth.urls')),     # Google OAuth URLs
    # SEO
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('', include('typingApp.urls')),
]

from django.views.static import serve as _serve_static
from django.urls import re_path as _re_path
# static() helper itself no-ops when DEBUG=False, so wire django.views.static.serve directly
urlpatterns += [
    _re_path(r'^media/(?P<path>.*)$', _serve_static, {'document_root': settings.MEDIA_ROOT}),
]