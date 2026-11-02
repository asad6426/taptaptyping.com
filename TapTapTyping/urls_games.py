"""
Alternate root URLconf, used ONLY for requests with Host: game.taptaptyping.com
(see TapTapTyping.middleware.GameSubdomainURLConfMiddleware).

Same WSGI app / codebase / database as the main site — this just gives the
game subdomain its own URL space (the `games` app owns '/') while re-mounting
every other named route the shared base2.html/navigationbar.html/footer.html
templates reference via {% url %}, so those templates keep working unmodified
here. Three typingApp routes are deliberately excluded:
  - 'blog_detail'  -> the greedy <slug:slug>/ catch-all: must never exist here
  - 'start_test'   -> registered at '' in typingApp.urls, which would shadow
                      the games hub at '/' on this host; re-mounted below at
                      's/' instead.
  - 'leaderboard'  -> re-mounted below at 'typing-leaderboard/'.

TapTapTyping/urls.py (the main site's urlconf) is completely untouched.
"""
from django.contrib import admin
from django.conf import settings
from django.urls import path, include, re_path
from django.http import HttpResponse
from django.views.static import serve as _serve_static

from accounts import views as accounts_views
from typingApp import views as typing_views
from typingApp.urls import urlpatterns as _typing_urlpatterns

_EXCLUDED_NAMES = {'blog_detail', 'start_test', 'leaderboard'}
_shared_typing_patterns = [
    p for p in _typing_urlpatterns if getattr(p, 'name', None) not in _EXCLUDED_NAMES
]


def games_robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /login/",
        "Disallow: /signup/",
        "",
        "Sitemap: https://game.taptaptyping.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('signup/', accounts_views.signup_view, name='signup'),
    path('login/', accounts_views.login_view, name='login'),
    path('logout/', accounts_views.logout_view, name='logout'),
    path('forgot-password/', accounts_views.forgot_password_view, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', accounts_views.reset_password_view, name='reset_password'),
    path('blog/', include('blog.urls')),
    path('jobpost/', include('jobpost.urls')),
    path('certificate/', include('certificate.urls')),
    path('accounts/', include('allauth.urls')),
    path('s/', typing_views.start_test, name='start_test'),
    path('typing-leaderboard/', typing_views.leaderboard, name='leaderboard'),
    path('robots.txt', games_robots_txt, name='games_robots_txt'),
    # Blog post images (uploaded to MEDIA_ROOT) render on this host too, since
    # the blog list view is re-mounted here — mirrors TapTapTyping/urls.py's
    # media route, which lives outside typingApp.urls so _shared_typing_patterns
    # never picks it up on its own.
    re_path(r'^media/(?P<path>.*)$', _serve_static, {'document_root': settings.MEDIA_ROOT}),
    *_shared_typing_patterns,
    path('', include('games.urls')),
]
