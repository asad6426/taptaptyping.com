from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from functools import wraps
import json
from datetime import datetime
import os

from .models import BlogPost, SEOAnalysis, BlogPostImage, BlogPostVideo


# ============================================
# SUPERUSER AUTHENTICATION DECORATOR
# ============================================
def superuser_required(view_func):
    """Decorator to require superuser access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect('/admin/login/?next=' + request.path)
        
        # Check if user is superuser
        if not request.user.is_superuser:
            return HttpResponse(
                '<html><body style="font-family: Arial; padding: 50px; text-align: center;">'
                '<h1>🔒 Access Denied</h1>'
                '<p style="font-size: 18px;">Only superusers can access the blog management system.</p>'
                '<p style="color: #666;">Current user: <strong>' + request.user.username + '</strong></p>'
                '<p><a href="/admin/logout/" style="color: #0066cc;">Logout</a> | '
                '<a href="/" style="color: #0066cc;">Go Home</a></p>'
                '</body></html>',
                status=403
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================
# BLOG POST EDITOR
# ============================================
@superuser_required
def blog_post_editor(request, post_id=None):
    """Main editor view - Superuser only"""
    print(f"📝 Editor accessed by: {request.user.username} - Post ID: {post_id}")
    
    post = None
    images = []
    videos = []
    
    if post_id:
        post = get_object_or_404(BlogPost, id=post_id)
        images = list(post.images.all().values('id', 'image', 'alt_text', 'caption', 'order'))
        videos = list(post.videos.all().values('id', 'video', 'thumbnail', 'title', 'description', 'order'))
        print(f"✅ Post loaded: {post.title}")
        print(f"📷 Images: {len(images)}, 🎥 Videos: {len(videos)}")
    
    context = {
        'post': post,
        'post_json': json.dumps({
            'id': post.id if post else None,
            'title': post.title if post else '',
            'seo_title': post.seo_title if post else '',
            'slug': post.slug if post else '',
            'content': post.content if post else '',
            'meta_description': post.meta_description if post else '',
            'focus_keyword': post.focus_keyword if post else '',
            'images': images,
            'videos': videos,
        }) if post else 'null'
    }
    
    return render(request, 'blog_post_editor.html', context)


# ============================================
# BLOG POSTS LIST VIEW
# ============================================
@superuser_required
def blog_posts_list_view(request):
    """Display all blog posts - Superuser only"""
    print(f"📋 List view accessed by: {request.user.username}")
    
    posts = BlogPost.objects.all()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Blog Posts - Admin</title>
        <style>
            body { font-family: Arial; margin: 0; background: #f0f0f0; }
            .topbar { background: #333; color: white; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; }
            .topbar a { color: white; text-decoration: none; margin-left: 15px; }
            .container { max-width: 1200px; margin: 20px auto; background: white; padding: 20px; }
            h1 { color: #333; margin: 0; }
            .user-info { font-size: 14px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th { background: #333; color: white; padding: 12px; border: 1px solid #ddd; text-align: left; }
            td { padding: 10px; border: 1px solid #ddd; }
            tr:nth-child(even) { background: #f9f9f9; }
            tr:hover { background: #f0f0f0; }
            .btn { padding: 8px 15px; text-decoration: none; border-radius: 4px; border: none; cursor: pointer; display: inline-block; }
            .btn-create { background: #0066cc; color: white; }
            .btn-edit { background: #28a745; color: white; font-size: 13px; }
            .btn-delete { background: #dc3545; color: white; font-size: 13px; }
            .btn-logout { background: #666; color: white; padding: 6px 12px; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="topbar">
            <h1>📝 Blog Management System</h1>
            <div class="user-info">
                <span>👤 ''' + request.user.username + ''' (Superuser)</span>
                <a href="/admin/" class="btn-logout">Admin Panel</a>
                <a href="/admin/logout/" class="btn-logout">Logout</a>
            </div>
        </div>
        <div class="container">
            <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                <h2>All Blog Posts (''' + str(posts.count()) + ''')</h2>
                <a href="/blog/editor/" class="btn btn-create">+ Create New Post</a>
            </div>
            
            <table>
                <tr>
                    <th>ID</th><th>Title</th><th>Slug</th><th>SEO</th><th>Images</th><th>Videos</th><th>Status</th><th>Created</th><th>Actions</th>
                </tr>
    '''
    
    for post in posts:
        html += f'''
                <tr>
                    <td>{post.id}</td>
                    <td><strong>{post.title or "Untitled"}</strong></td>
                    <td>{post.slug}</td>
                    <td>{post.overall_seo_score}%</td>
                    <td>{post.images.count()}</td>
                    <td>{post.videos.count()}</td>
                    <td>{'Published' if post.published else 'Draft'}</td>
                    <td>{post.created_at.strftime("%Y-%m-%d %H:%M")}</td>
                    <td>
                        <a href="/blog/editor/{post.id}/" class="btn btn-edit">Edit</a>
                        <button class="btn btn-delete" onclick="del({post.id}, '{post.title}')">Delete</button>
                    </td>
                </tr>
        '''
    
    html += '''
            </table>
        </div>
        <script>
            function del(id, title) {
                if (confirm('Delete "' + title + '"?\\n\\nThis will delete all images and videos!')) {
                    fetch('/blog/api/delete/' + id + '/', { 
                        method: 'POST',
                        headers: { 'X-Requested-With': 'XMLHttpRequest' }
                    })
                        .then(r => r.json())
                        .then(d => { 
                            if (d.success) { 
                                alert('✅ Deleted successfully!'); 
                                location.reload(); 
                            } else {
                                alert('❌ Error: ' + d.error);
                            }
                        })
                        .catch(e => alert('❌ Error: ' + e));
                }
            }
        </script>
    </body>
    </html>
    '''
    
    return HttpResponse(html)


# ============================================
# IMAGE UPLOAD
# ============================================
@csrf_exempt
@superuser_required
@require_http_methods(["POST"])
def upload_image(request):
    """Upload images - Superuser only"""
    print(f"\n{'='*50}")
    print(f"📷 IMAGE UPLOAD by {request.user.username}")
    print("="*50)
    
    try:
        post_id = request.POST.get('post_id')
        files = request.FILES.getlist('images')
        
        print(f"📦 Files: {len(files)}, Post ID: {post_id}")
        
        if not files:
            return JsonResponse({'success': False, 'error': 'No images'}, status=400)
        
        if post_id:
            try:
                post = BlogPost.objects.get(id=post_id)
            except BlogPost.DoesNotExist:
                post = BlogPost.objects.create(
                    title='Untitled Post',
                    slug=f'untitled-{int(timezone.now().timestamp())}',
                    author=request.user
                )
        else:
            post = BlogPost.objects.create(
                title='Untitled Post',
                slug=f'untitled-{int(timezone.now().timestamp())}',
                author=request.user
            )
        
        uploaded_images = []
        
        for idx, file in enumerate(files):
            alt_text = request.POST.get(f'alt_text_{idx}', '')
            caption = request.POST.get(f'caption_{idx}', '')
            
            image = BlogPostImage.objects.create(
                blog_post=post,
                image=file,
                alt_text=alt_text or file.name,
                caption=caption,
                order=idx
            )
            
            uploaded_images.append({
                'id': image.id,
                'url': image.image.url,
                'name': file.name,
                'size': file.size,
                'alt_text': image.alt_text,
                'caption': image.caption
            })
        
        print(f"✅ Uploaded {len(uploaded_images)} images")
        
        return JsonResponse({
            'success': True,
            'post_id': post.id,
            'images': uploaded_images,
            'message': f'{len(uploaded_images)} image(s) uploaded!'
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================
# VIDEO UPLOAD
# ============================================
@csrf_exempt
@superuser_required
@require_http_methods(["POST"])
def upload_video(request):
    """Upload video - Superuser only"""
    print(f"\n{'='*50}")
    print(f"🎥 VIDEO UPLOAD by {request.user.username}")
    print("="*50)
    
    try:
        post_id = request.POST.get('post_id')
        video_file = request.FILES.get('video')
        thumbnail_file = request.FILES.get('thumbnail')
        
        if not video_file:
            return JsonResponse({'success': False, 'error': 'No video'}, status=400)
        
        if post_id:
            try:
                post = BlogPost.objects.get(id=post_id)
            except BlogPost.DoesNotExist:
                post = BlogPost.objects.create(
                    title='Untitled Post',
                    slug=f'untitled-{int(timezone.now().timestamp())}',
                    author=request.user
                )
        else:
            post = BlogPost.objects.create(
                title='Untitled Post',
                slug=f'untitled-{int(timezone.now().timestamp())}',
                author=request.user
            )
        
        title = request.POST.get('title', '')
        description = request.POST.get('description', '')
        
        video = BlogPostVideo.objects.create(
            blog_post=post,
            video=video_file,
            thumbnail=thumbnail_file if thumbnail_file else None,
            title=title or video_file.name,
            description=description,
            order=post.videos.count()
        )
        
        print(f"✅ Video uploaded: {video.id}")
        
        return JsonResponse({
            'success': True,
            'post_id': post.id,
            'video': {
                'id': video.id,
                'url': video.video.url,
                'thumbnail_url': video.thumbnail.url if video.thumbnail else None,
                'title': video.title,
                'description': video.description,
                'size': video_file.size
            },
            'message': 'Video uploaded!'
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================
# DELETE IMAGE
# ============================================
@csrf_exempt
@superuser_required
@require_http_methods(["POST"])
def delete_image(request, image_id):
    """Delete image - Superuser only"""
    print(f"🗑️  DELETE Image {image_id} by {request.user.username}")
    
    try:
        image = get_object_or_404(BlogPostImage, id=image_id)
        
        if os.path.exists(image.image.path):
            os.remove(image.image.path)
        
        image.delete()
        print(f"✅ Image deleted")
        
        return JsonResponse({'success': True, 'message': 'Image deleted!'})
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================
# DELETE VIDEO
# ============================================
@csrf_exempt
@superuser_required
@require_http_methods(["POST"])
def delete_video(request, video_id):
    """Delete video - Superuser only"""
    print(f"🗑️  DELETE Video {video_id} by {request.user.username}")
    
    try:
        video = get_object_or_404(BlogPostVideo, id=video_id)
        
        if os.path.exists(video.video.path):
            os.remove(video.video.path)
        
        if video.thumbnail and os.path.exists(video.thumbnail.path):
            os.remove(video.thumbnail.path)
        
        video.delete()
        print(f"✅ Video deleted")
        
        return JsonResponse({'success': True, 'message': 'Video deleted!'})
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================
# SAVE BLOG POST
# ============================================
@csrf_exempt
@superuser_required
@require_http_methods(["POST"])
def save_blog_post(request):
    """Save blog post - Superuser only"""
    print(f"\n{'='*50}")
    print(f"💾 SAVE by {request.user.username}")
    print("="*50)
    
    try:
        data = json.loads(request.body)
        post_id = data.get('id')
        
        if post_id:
            try:
                post = BlogPost.objects.get(id=post_id)
                print(f"✏️  Updating: {post.title}")
            except BlogPost.DoesNotExist:
                post = BlogPost(author=request.user)
        else:
            post = BlogPost(author=request.user)
        
        post.title = data.get('title', '')
        post.seo_title = data.get('seo_title', '')
        post.content = data.get('content', '')
        post.meta_description = data.get('meta_description', '')
        post.focus_keyword = data.get('focus_keyword', '')
        
        slug = data.get('slug', '')
        if not slug and post.title:
            slug = slugify(post.title)
        post.slug = slug
        
        post.overall_seo_score = data.get('overall_seo_score', 0)
        post.title_score = data.get('title_score', 0)
        post.content_score = data.get('content_score', 0)
        post.readability_score = data.get('readability_score', 0)
        post.seo_metrics = data.get('seo_metrics', {})
        
        post.save()
        print(f"✅ SAVED! ID: {post.id}")
        
        SEOAnalysis.objects.create(
            blog_post=post,
            overall_score=post.overall_seo_score,
            title_score=post.title_score,
            content_score=post.content_score,
            readability_score=post.readability_score,
            metrics=post.seo_metrics
        )
        
        return JsonResponse({
            'success': True,
            'post_id': post.id,
            'message': 'Saved successfully!',
            'total_posts': BlogPost.objects.count()
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================
# GET BLOG POST
# ============================================
@superuser_required
@require_http_methods(["GET"])
def get_blog_post(request, post_id):
    """Get blog post - Superuser only"""
    print(f"📖 GET Post {post_id} by {request.user.username}")
    
    try:
        post = get_object_or_404(BlogPost, id=post_id)
        images = list(post.images.all().values('id', 'image', 'alt_text', 'caption', 'order'))
        videos = list(post.videos.all().values('id', 'video', 'thumbnail', 'title', 'description', 'order'))
        
        return JsonResponse({
            'success': True,
            'post': {
                'id': post.id,
                'title': post.title,
                'seo_title': post.seo_title,
                'slug': post.slug,
                'content': post.content,
                'meta_description': post.meta_description,
                'focus_keyword': post.focus_keyword,
                'overall_seo_score': post.overall_seo_score,
                'title_score': post.title_score,
                'content_score': post.content_score,
                'readability_score': post.readability_score,
                'seo_metrics': post.seo_metrics,
                'created_at': post.created_at.isoformat(),
                'updated_at': post.updated_at.isoformat(),
                'images': images,
                'videos': videos,
            }
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=404)


# ============================================
# LIST BLOG POSTS (API)
# ============================================
@superuser_required
@require_http_methods(["GET"])
def list_blog_posts(request):
    """List posts API - Superuser only"""
    posts = BlogPost.objects.all()
    
    posts_data = [{
        'id': post.id,
        'title': post.title,
        'slug': post.slug,
        'overall_seo_score': post.overall_seo_score,
        'created_at': post.created_at.isoformat(),
        'updated_at': post.updated_at.isoformat(),
        'image_count': post.images.count(),
        'video_count': post.videos.count(),
    } for post in posts]
    
    return JsonResponse({'success': True, 'posts': posts_data})


# ============================================
# DELETE BLOG POST
# ============================================
@csrf_exempt
@superuser_required
@require_http_methods(["POST"])
def delete_blog_post(request, post_id):
    """Delete blog post - Superuser only"""
    print(f"\n🗑️  DELETE POST {post_id} by {request.user.username}")
    
    try:
        post = get_object_or_404(BlogPost, id=post_id)
        title = post.title
        
        image_count = post.images.count()
        video_count = post.videos.count()
        
        for image in post.images.all():
            if image.image and os.path.exists(image.image.path):
                os.remove(image.image.path)
        
        for video in post.videos.all():
            if video.video and os.path.exists(video.video.path):
                os.remove(video.video.path)
            if video.thumbnail and os.path.exists(video.thumbnail.path):
                os.remove(video.thumbnail.path)
        
        post.delete()
        
        print(f"✅ DELETED: {title}")
        
        return JsonResponse({
            'success': True,
            'message': f'Post "{title}" deleted!',
            'deleted_images': image_count,
            'deleted_videos': video_count
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)