from django.contrib import admin

from typingApp.models import JobPost,BlogPost,TypingTestResult,Score

# Register your models here.
admin.site.register(JobPost)

admin.site.register(TypingTestResult)
admin.site.register(Score)
from django.contrib import admin
from .models import BlogPost, Category


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'posted_date', 'views', 'is_featured', 'noindex']
    list_filter = ['posted_date', 'is_featured', 'noindex']
    search_fields = ['title', 'description', 'meta_title', 'focus_keyword']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['posted_date', 'updated_date', 'views']
    date_hierarchy = 'posted_date'
    
    fieldsets = (
        ('📝 Basic Information', {
            'fields': ('title', 'description', 'image', 'is_featured')
        }),
        ('🔗 URL & Slug', {
            'fields': ('slug',),
            'description': 'Auto-generated from title if left blank'
        }),
        ('🎯 SEO Settings (Rank Math Style)', {
            'fields': ('meta_title', 'meta_description', 'focus_keyword'),
            'description': 'Optimize your post for search engines'
        }),
        ('🌐 Social Media (Open Graph)', {
            'fields': ('og_title', 'og_description', 'og_image'),
            'classes': ('collapse',),
            'description': 'How your post appears when shared on social media'
        }),
        ('⚙️ Advanced SEO', {
            'fields': ('canonical_url', 'noindex', 'nofollow'),
            'classes': ('collapse',),
            'description': 'Advanced search engine optimization options'
        }),
        ('📊 Analytics', {
            'fields': ('views', 'posted_date', 'updated_date'),
            'classes': ('collapse',),
        }),
    )
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('SEO Settings', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',),
        }),
    )