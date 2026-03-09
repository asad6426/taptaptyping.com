from django.shortcuts import render, redirect, get_object_or_404
from .models import JobPost, BlogPost, TypingTestResult, Score, Category
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
import json

# ============================================
# TYPING TEST VIEWS
# ============================================

@login_required
def dashboard_view(request):
    """Personal dashboard for logged-in user"""
    user = request.user
    
    try:
        score = Score.objects.get(user=user)
    except Score.DoesNotExist:
        score = None
    
    rank = None
    total_users = Score.objects.count()
    if score:
        all_scores = Score.objects.order_by('-total_score')
        for i, s in enumerate(all_scores, start=1):
            if s.user == user:
                rank = i
                break
    
    recent_tests = TypingTestResult.objects.filter(user=user).order_by('-created_at')[:10]
    all_tests = TypingTestResult.objects.filter(user=user).order_by('created_at')
    
    chart_labels = []
    chart_wpm = []
    chart_accuracy = []
    chart_marks = []
    
    for test in all_tests:
        chart_labels.append(test.created_at.strftime('%d %b'))
        chart_wpm.append(test.wpm)
        chart_accuracy.append(float(test.accuracy))
        chart_marks.append(float(test.marks))
    
    wpm_improvement = 0
    accuracy_improvement = 0
    
    if all_tests.count() >= 2:
        first_test = all_tests.first()
        last_test = all_tests.last()
        wpm_improvement = last_test.wpm - first_test.wpm
        accuracy_improvement = round(float(last_test.accuracy) - float(first_test.accuracy), 2)
    
    context = {
        'score': score,
        'rank': rank,
        'total_users': total_users,
        'recent_tests': recent_tests,
        'wpm_improvement': wpm_improvement,
        'accuracy_improvement': accuracy_improvement,
        'total_tests_count': all_tests.count(),
        'chart_labels': json.dumps(chart_labels),
        'chart_wpm': json.dumps(chart_wpm),
        'chart_accuracy': json.dumps(chart_accuracy),
        'chart_marks': json.dumps(chart_marks),
    }
    
    return render(request, 'dashboard.html', context)


def leaderboard(request):
    """Get top scores and pass to template"""
    all_scores = Score.objects.select_related('user').order_by('-total_score')
    
    top_3 = list(all_scores[:3])
    first = top_3[0] if len(top_3) > 0 else None
    second = top_3[1] if len(top_3) > 1 else None
    third = top_3[2] if len(top_3) > 2 else None
    
    leaderboard = []
    for rank, score in enumerate(all_scores, start=1):
        leaderboard.append({
            'rank': rank,
            'score': score,
            'is_current_user': request.user.is_authenticated and score.user == request.user
        })
    
    current_user_rank = None
    if request.user.is_authenticated:
        for item in leaderboard:
            if item['is_current_user']:
                current_user_rank = item['rank']
                break
    
    context = {
        'first': first,
        'second': second,
        'third': third,
        'leaderboard': leaderboard,
        'current_user_rank': current_user_rank,
    }
    
    return render(request, 'leaderboard.html', context)


@login_required
@require_http_methods(["POST"])
def save_result(request):
    """Receive typing test data from JavaScript and save to database"""
    try:
        data = json.loads(request.body)
        
        result = TypingTestResult.objects.create(
            user=request.user,
            test_duration=data.get('test_duration'),
            time_taken=data.get('time_taken'),
            time_taken_formatted=data.get('time_taken_formatted'),
            wpm=data.get('wpm'),
            accuracy=data.get('accuracy'),
            correct_entries=data.get('correct_entries'),
            incorrect_entries=data.get('incorrect_entries'),
            fixed_mistakes=data.get('fixed_mistakes'),
            total_entries=data.get('total_entries'),
            error_rate=data.get('error_rate'),
            raw_speed=data.get('raw_speed'),
            key_speed=data.get('key_speed'),
            complete_words=data.get('complete_words'),
            fastest_chars=data.get('fastest_chars'),
            slowest_chars=data.get('slowest_chars'),
            most_missed=data.get('most_missed'),
            most_inaccurate=data.get('most_inaccurate')
        )
        
        score, created = Score.objects.get_or_create(user=request.user)
        
        old_total_tests = score.total_tests
        old_avg_wpm = float(score.average_wpm)
        old_avg_accuracy = float(score.average_accuracy)
        
        new_wpm = result.wpm
        new_accuracy = float(result.accuracy)
        new_marks = float(result.marks)
        
        score.total_score = Decimal(str(score.total_score)) + Decimal(str(new_marks))
        score.total_tests += 1
        new_total_tests = score.total_tests
        
        if old_total_tests == 0:
            score.average_wpm = Decimal(str(new_wpm))
        else:
            score.average_wpm = Decimal(str(round(((old_avg_wpm * old_total_tests) + new_wpm) / new_total_tests, 2)))
        
        if old_total_tests == 0:
            score.average_accuracy = Decimal(str(new_accuracy))
        else:
            score.average_accuracy = Decimal(str(round(((old_avg_accuracy * old_total_tests) + new_accuracy) / new_total_tests, 2)))
        
        if new_wpm > score.best_wpm:
            score.best_wpm = new_wpm
        
        if new_accuracy > float(score.best_accuracy):
            score.best_accuracy = Decimal(str(new_accuracy))
        
        score.save()
        
        return JsonResponse({
            'success': True,
            'result_id': result.id,
            'marks': float(result.marks),
            'message': 'Result saved successfully!'
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON format',
            'details': str(e)
        }, status=400)
        
    except KeyError as e:
        return JsonResponse({
            'success': False,
            'error': f'Missing required field: {str(e)}'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Server error',
            'details': str(e)
        }, status=500)


# ============================================
# TYPING LESSON VIEWS
# ============================================

def start_test(request):
    return render(request, 'home2.html')

def taptap(request):
    if request.method == 'GET':
        test_duration = request.GET.get('test_duration')
        text_type = request.GET.get('text_type')
    else:
        test_duration = request.session.get('test_duration', 60)
        text_type = request.session.get('text_type', 'Easy')
    return render(request, "taptapmain.html", {'test_duration': test_duration, 'text_type': text_type})

def GH(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "GH.html", {'test_duration': test_duration, 'text_type': text_type})

def S(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "S.html", {'test_duration': test_duration, 'text_type': text_type})

def C(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "C.html", {'test_duration': test_duration, 'text_type': text_type})

def V(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "V.html", {'test_duration': test_duration, 'text_type': text_type})

def ZN(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "ZN.html", {'test_duration': test_duration, 'text_type': text_type})

def XM(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "XM.html", {'test_duration': test_duration, 'text_type': text_type})

def RI(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "RI.html", {'test_duration': test_duration, 'text_type': text_type})

def EO(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "EO.html", {'test_duration': test_duration, 'text_type': text_type})

def WP(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "WP.html", {'test_duration': test_duration, 'text_type': text_type})

def QU(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "QU.html", {'test_duration': test_duration, 'text_type': text_type})

def DL(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "DL.html", {'test_duration': test_duration, 'text_type': text_type})

def FK(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "FK.html", {'test_duration': test_duration, 'text_type': text_type})

def AJ(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "AJ.html", {'test_duration': test_duration, 'text_type': text_type})

def BottomRowPractce(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "BottomRowPractce.html", {'test_duration': test_duration, 'text_type': text_type})

def X(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "X.html", {'test_duration': test_duration, 'text_type': text_type})

def M(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "M.html", {'test_duration': test_duration, 'text_type': text_type})

def Z(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "Z.html", {'test_duration': test_duration, 'text_type': text_type})

def CM(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "CM.html", {'test_duration': test_duration, 'text_type': text_type})

def BB(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "BB.html", {'test_duration': test_duration, 'text_type': text_type})

def VN(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "VN.html", {'test_duration': test_duration, 'text_type': text_type})

def topRowPractice(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "topRowPractice.html", {'test_duration': test_duration, 'text_type': text_type})

def QP(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "QP.html", {'test_duration': test_duration, 'text_type': text_type})

def WO(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "WO.html", {'test_duration': test_duration, 'text_type': text_type})

def EI(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "EI.html", {'test_duration': test_duration, 'text_type': text_type})

def RU(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "RU.html", {'test_duration': test_duration, 'text_type': text_type})

def TY(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "TY.html", {'test_duration': test_duration, 'text_type': text_type})

def homeRowPractice(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "homeRowPractice.html", {'test_duration': test_duration, 'text_type': text_type})

def A(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "A.html", {'test_duration': test_duration, 'text_type': text_type})

def SL(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "SL.html", {'test_duration': test_duration, 'text_type': text_type})

def DK(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "DK.html", {'test_duration': test_duration, 'text_type': text_type})

def FJ(request):
    test_duration = request.GET.get('test_duration', 60)
    text_type = request.GET.get('text_type', 'Easy')
    return render(request, "FJ.html", {'test_duration': test_duration, 'text_type': text_type})


# ============================================
# GENERAL PAGES
# ============================================

def FAQ(request):
    return render(request, 'FAQ.html')

def typingGame(request):
    return render(request, 'typingGame.html')

def policy(request):
    return render(request, 'policy.html')

def aboutus(request):
    return render(request, 'aboutus.html')

def base(request):
    return render(request, "base2.html")

def typingLession(request):
    return render(request, 'typingL.html')


# ============================================
# JOB POST VIEWS
# ============================================

def jobs(request):
    jobposts = JobPost.objects.all()
    return render(request, "jobPost.html", {'jobposts': jobposts})

def job_details(request, pk):
    job = JobPost.objects.get(id=pk)
    return render(request, "jobs.html", {'job_details': job})

from .forms import JobPostForm, BlogPostForm

@login_required
def JobpostForm(request):
    if request.method == 'POST':
        form = JobPostForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('jobs')
    else:
        form = JobPostForm()
    return render(request, 'jobPostform.html', {'form': form})


# ============================================
# BLOG VIEWS - SEO OPTIMIZED
# ============================================

def blog_list(request):
    """Display all blog posts with pagination"""
    posts = BlogPost.objects.filter(noindex=False).order_by('-posted_date')
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'posts': page_obj,
        'page_obj': page_obj,
        'meta_title': 'Blog - Latest Articles and Tutorials',
        'meta_description': 'Read our latest blog posts, tutorials, and articles on various topics.',
    }
    return render(request, 'blog/blog_list.html', context)


def blog_detail(request, slug):
    """Display single blog post with SEO optimization"""
    post = get_object_or_404(BlogPost, slug=slug)
    
    # Increment view count
    post.increment_views()
    
    # Get related posts
    related_posts = BlogPost.objects.filter(
        noindex=False
    ).exclude(id=post.id).order_by('-posted_date')[:3]
    
    context = {
        'post': post,
        'related_posts': related_posts,
    }
    return render(request, 'blog_detail.html', context)


def category_posts(request, slug):
    """Display posts by category"""
    category = get_object_or_404(Category, slug=slug)
    posts = BlogPost.objects.filter(
        noindex=False
    ).order_by('-posted_date')
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'posts': page_obj,
        'page_obj': page_obj,
        'meta_title': category.meta_title or f'{category.name} - Blog Category',
        'meta_description': category.meta_description or category.description,
    }
    return render(request, 'blog/category_posts.html', context)


# ============================================
# ADMIN BLOG VIEWS (Old style - by ID)
# ============================================

def blogs(request):
    """Old blog list view"""
    blogposts = BlogPost.objects.all()
    return render(request, "blogsPost.html", {'blogposts': blogposts})

def blog_details(request, pk):
    """Old blog detail view by ID"""
    blog = BlogPost.objects.get(id=pk)
    return render(request, "blogs.html", {'blog_details': blog})

@login_required
def blog_detail_admin(request, pk):
    """Admin view to see blog post by ID"""
    if not request.user.is_staff:
        return redirect('login')
    post = get_object_or_404(BlogPost, pk=pk)
    return render(request, 'blog_detail.html', {'post': post})

@login_required
def blog_update(request, pk):
    """Update existing blog post"""
    post = get_object_or_404(BlogPost, pk=pk)
    if not request.user.is_staff:
        return redirect('login')
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog_detail_admin', pk=pk)
    else:
        form = BlogPostForm(instance=post)
    return render(request, 'blogPostform.html', {'form': form, 'update': True})

@login_required
def blog_delete(request, pk):
    """Delete blog post"""
    post = get_object_or_404(BlogPost, pk=pk)
    if not request.user.is_staff:
        return redirect('login')
    if request.method == 'POST':
        post.delete()
        return redirect('blog_list')
    return render(request, 'blog_confirm_delete.html', {'post': post})


# ============================================
# SEO BLOG CREATOR
# ============================================

@login_required
def blogpostForm(request):
    """Render the SEO blog post creator HTML"""
    if not request.user.is_staff:
        return redirect('login')
    return render(request, 'creator.html')
@require_http_methods(["POST"])
def submit_blog_post(request):
    """AJAX handler - Save blog post with images from SEO creator"""
    try:
        # ✅ Get form data (not JSON anymore)
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        slug = request.POST.get('slug', '').strip()
        meta_title = request.POST.get('metaTitle', '').strip()
        meta_description = request.POST.get('metaDescription', '').strip()
        focus_keyword = request.POST.get('focusKeyword', '').strip()
        
        # ✅ Get uploaded files
        featured_image = request.FILES.get('featuredImage')
        content_images = request.FILES.getlist('contentImages')
        
        # Validation
        if not title:
            return JsonResponse({
                'success': False,
                'message': 'Title is required'
            }, status=400)
        
        if not content:
            return JsonResponse({
                'success': False,
                'message': 'Content is required'
            }, status=400)
        
        # Check if slug already exists
        if slug and BlogPost.objects.filter(slug=slug).exists():
            return JsonResponse({
                'success': False,
                'message': f'A post with slug "{slug}" already exists'
            }, status=400)
        
        print(f"=== CREATING POST ===")
        print(f"Featured Image: {featured_image}")
        print(f"Content Images: {len(content_images)} files")
        
        # ✅ Create the blog post with image
        post = BlogPost.objects.create(
            title=title,
            description=content,
            slug=slug if slug else '',
            meta_title=meta_title if meta_title else None,
            meta_description=meta_description if meta_description else None,
            focus_keyword=focus_keyword if focus_keyword else None,
            image=featured_image if featured_image else None,  # ✅ Save featured image
        )
        
        print(f"=== POST CREATED: {post.id} ===")
        
        # ✅ Handle content images (save them and provide URLs)
        content_image_urls = []
        if content_images:
            for img in content_images:
                # Save to media folder
                from django.core.files.storage import default_storage
                file_name = default_storage.save(f'blog_content_images/{img.name}', img)
                file_url = default_storage.url(file_name)
                content_image_urls.append(file_url)
                print(f"Saved content image: {file_url}")
        
        # Return success
        return JsonResponse({
            'success': True,
            'message': f'Blog post "{post.title}" saved successfully!',
            'post_id': post.id,
            'post_url': f'/{post.slug}/',
            'featured_image_url': post.image.url if post.image else None,
            'content_image_urls': content_image_urls
        })
        
    except Exception as e:
        import traceback
        print(f"=== ERROR: {e} ===")
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)