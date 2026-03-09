from django.urls import path
from . import views

app_name = 'blog_seo'

urlpatterns = [
    # Main pages
    path('', views.blog_posts_list_view, name='list'),
    path('editor/', views.blog_post_editor, name='editor'),
    path('editor/<int:post_id>/', views.blog_post_editor, name='editor_edit'),
    
    # API endpoints
    path('api/save/', views.save_blog_post, name='save_post'),
    path('api/get/<int:post_id>/', views.get_blog_post, name='get_post'),
    path('api/list/', views.list_blog_posts, name='list_posts'),
    path('api/delete/<int:post_id>/', views.delete_blog_post, name='delete_post'),
    
    # Media upload endpoints
    path('api/upload/image/', views.upload_image, name='upload_image'),
    path('api/upload/video/', views.upload_video, name='upload_video'),
    path('api/delete/image/<int:image_id>/', views.delete_image, name='delete_image'),
    path('api/delete/video/<int:video_id>/', views.delete_video, name='delete_video'),
]