from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class BlogPost(models.Model):
    # Basic Information
    title = models.CharField(max_length=500)
    seo_title = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=200, unique=True)
    
    # Content
    content = models.TextField()
    meta_description = models.CharField(max_length=320, blank=True)
    
    # SEO Settings
    focus_keyword = models.CharField(max_length=200, blank=True)
    
    # SEO Scores (calculated and stored)
    overall_seo_score = models.IntegerField(default=0)
    title_score = models.IntegerField(default=0)
    content_score = models.IntegerField(default=0)
    readability_score = models.IntegerField(default=0)
    
    # Metadata
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)
    
    # SEO Metrics (JSON stored)
    seo_metrics = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'
    
    def __str__(self):
        return self.title or 'Untitled Post'
    
    def get_absolute_url(self):
        return f'/blog/{self.slug}/'


class BlogPostImage(models.Model):
    """Store multiple images for a blog post"""
    blog_post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='blog_images/%Y/%m/%d/')
    alt_text = models.CharField(max_length=200, blank=True)
    caption = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name = 'Blog Post Image'
        verbose_name_plural = 'Blog Post Images'
    
    def __str__(self):
        return f"{self.blog_post.title} - Image {self.id}"


class BlogPostVideo(models.Model):
    """Store videos for a blog post"""
    blog_post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='videos')
    video = models.FileField(upload_to='blog_videos/%Y/%m/%d/')
    thumbnail = models.ImageField(upload_to='blog_video_thumbnails/%Y/%m/%d/', blank=True, null=True)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    duration = models.IntegerField(blank=True, null=True, help_text='Duration in seconds')
    order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name = 'Blog Post Video'
        verbose_name_plural = 'Blog Post Videos'
    
    def __str__(self):
        return f"{self.blog_post.title} - Video {self.id}"


class SEOAnalysis(models.Model):
    """Store historical SEO analysis for tracking improvements"""
    blog_post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='analyses')
    
    # Scores
    overall_score = models.IntegerField()
    title_score = models.IntegerField()
    content_score = models.IntegerField()
    readability_score = models.IntegerField()
    
    # Detailed metrics
    metrics = models.JSONField()
    
    # Timestamp
    analyzed_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-analyzed_at']
        verbose_name = 'SEO Analysis'
        verbose_name_plural = 'SEO Analyses'
    
    def __str__(self):
        return f'{self.blog_post.title} - {self.analyzed_at.strftime("%Y-%m-%d %H:%M")}'