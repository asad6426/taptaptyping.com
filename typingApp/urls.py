from django.urls import path
from .views import *

urlpatterns = [
    # ==========================================
    # TYPING TEST & LESSONS
    # ==========================================
    path('s/', start_test, name='start_test'),
    path('taptap/', taptap, name='taptap'),
    path('lession_SL/', SL, name='SL'),
    path('lession_S/', S, name='S'),
    path('lession_C/', C, name='C'),
    path('lession_V/', V, name='V'),
    path('lession_ZN/', ZN, name='ZN'),
    path('lession_XM/', XM, name='XM'),
    path('lession_RI/', RI, name='RI'),
    path('lession_EO/', EO, name='EO'),
    path('lession_WP/', WP, name='WP'),
    path('lession_QU/', QU, name='QU'),
    path('lession_DL/', DL, name='DL'),
    path('lession_FK/', FK, name='FK'),
    path('lession_AJ/', AJ, name='AJ'),
    path('lession_homeRowPractice/', homeRowPractice, name='homeRowPractice'),
    path('lession_A;/', A, name='A'),
    path('lession_X,/', X, name='X'),
    path('lession_M,/', M, name='M'),
    path('lession_Z./', Z, name='Z'),
    path('lession_RU/', RU, name='RU'),
    path('lession_BottomRowPractce/', BottomRowPractce, name='BottomRowPractce'),
    path('lession_CM/', CM, name='CM'),
    path('lession_BB/', BB, name='BB'),
    path('lession_VN/', VN, name='VN'),
    path('lession_topRowPractice/', topRowPractice, name='topRowPractice'),
    path('lession_QP/', QP, name='QP'),
    path('lession_WO/', WO, name='WO'),
    path('lession_EI/', EI, name='EI'),
    path('lession_TY/', TY, name='TY'),
    path('lession_DK/', DK, name='DK'),
    path('lession_GH/', GH, name='GH'),
    path('lession_FJ/', FJ, name='FJ'),
    
    # ==========================================
    # TYPING RESULTS & DASHBOARD
    # ==========================================
    path('typing/save/', save_result, name='save_result'),
    path('leaderboard/', leaderboard, name='leaderboard'),
    path('dashboard/', dashboard_view, name='dashboard'),
    
    # ==========================================
    # GENERAL PAGES
    # ==========================================
    path('FAQ/', FAQ, name='FAQ'),
    path('base/', base, name='base'),
    path('aboutus/', aboutus, name='aboutus'),
    path('policy/', policy, name='policy'),
    path('typingGames/', typingGame, name='typingGame'),
    path('typingLession/', typingLession, name='typingLession'),
    
    # ==========================================
    # JOB POSTS
    # ==========================================
    path('jobs/', jobs, name='jobs'),
    path('job_details/<str:pk>/', job_details, name='job_details'),
    path('reza/', JobpostForm, name='JobpostForm'),
    
    # ==========================================
    # BLOG - SEO CREATOR
    # ==========================================
    path('rezablog/', blogpostForm, name='blogpostForm'),  # Renders SEO creator HTML
    path('submit-ajax/', submit_blog_post, name='submit_blog_ajax'),  # AJAX submission
    
    # ==========================================
    # BLOG - ADMIN MANAGEMENT (by ID)
    # ==========================================
    path('blogs_list/', blog_list, name='blogs_list'),
    path('blogs/<int:pk>/', blog_detail_admin, name='blog_detail_admin'),
    path('blogs/<int:pk>/edit/', blog_update, name='blog_update'),
    path('blogs/<int:pk>/delete/', blog_delete, name='blog_delete'),
    
    # ==========================================
    # BLOG - OLD VIEWS (for compatibility)
    # ==========================================
    path('blogs/', blogs, name='blogs'),
    path('blog_details/<str:pk>/', blog_details, name='blog_details'),
    
    # ==========================================
    # BLOG - CATEGORY
    # ==========================================
    path('category/<slug:slug>/', category_posts, name='category_posts'),
    
    # ==========================================
    # HOME (leaderboard)
    # ==========================================
    path('', leaderboard, name='leaderboard'),
    
    # ==========================================
    # CATCH-ALL - MUST BE LAST!
    # ==========================================
    path('<slug:slug>/', blog_detail, name='blog_detail'),  # SEO-friendly blog URLs
]