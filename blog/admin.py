from django.contrib import admin
from .models import BlogPost, SEOAnalysis, BlogPostImage, BlogPostVideo


class BlogPostImageInline(admin.TabularInline):
    model = BlogPostImage
    extra = 1
    fields = ['image', 'alt_text', 'caption', 'order']


class BlogPostVideoInline(admin.TabularInline):
    model = BlogPostVideo
    extra = 1
    fields = ['video', 'thumbnail', 'title', 'description', 'order']


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'focus_keyword', 'overall_seo_score', 'image_count', 'video_count', 'created_at', 'published']
    list_filter = ['published', 'created_at', 'updated_at']
    search_fields = ['title', 'content', 'focus_keyword', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at', 'overall_seo_score', 'title_score', 'content_score', 'readability_score']
    inlines = [BlogPostImageInline, BlogPostVideoInline]
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'content', 'author', 'published')
        }),
        ('SEO Settings', {
            'fields': ('focus_keyword', 'seo_title', 'meta_description')
        }),
        ('SEO Scores', {
            'fields': ('overall_seo_score', 'title_score', 'content_score', 'readability_score'),
            'classes': ('collapse',)
        }),
        ('Advanced', {
            'fields': ('seo_metrics', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = 'Images'
    
    def video_count(self, obj):
        return obj.videos.count()
    video_count.short_description = 'Videos'


@admin.register(BlogPostImage)
class BlogPostImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'blog_post', 'alt_text', 'order', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['blog_post__title', 'alt_text', 'caption']
    readonly_fields = ['uploaded_at']
    
    fieldsets = (
        ('Image', {
            'fields': ('blog_post', 'image', 'order')
        }),
        ('SEO', {
            'fields': ('alt_text', 'caption')
        }),
        ('Metadata', {
            'fields': ('uploaded_at',)
        }),
    )


@admin.register(BlogPostVideo)
class BlogPostVideoAdmin(admin.ModelAdmin):
    list_display = ['id', 'blog_post', 'title', 'duration', 'order', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['blog_post__title', 'title', 'description']
    readonly_fields = ['uploaded_at']
    
    fieldsets = (
        ('Video', {
            'fields': ('blog_post', 'video', 'thumbnail', 'order')
        }),
        ('Details', {
            'fields': ('title', 'description', 'duration')
        }),
        ('Metadata', {
            'fields': ('uploaded_at',)
        }),
    )


@admin.register(SEOAnalysis)
class SEOAnalysisAdmin(admin.ModelAdmin):
    list_display = ['blog_post', 'overall_score', 'analyzed_at']
    list_filter = ['analyzed_at']
    readonly_fields = ['blog_post', 'overall_score', 'title_score', 'content_score', 'readability_score', 'metrics', 'analyzed_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False