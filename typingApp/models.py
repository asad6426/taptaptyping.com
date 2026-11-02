from django.db import models
from datetime import datetime
from django.utils import timezone
from tinymce.models import HTMLField
class JobPost(models.Model):
    title = models.CharField(max_length=200)
    description = HTMLField()
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    posted_date = models.DateTimeField(default=timezone.now)
    image = models.ImageField(upload_to='job_images/', blank=True, null=True)  # New image field

    def __str__(self):
        return self.title
    
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from tinymce.models import HTMLField
from django.urls import reverse


class BlogPost(models.Model):
    # Basic fields
    title = models.CharField(max_length=200, verbose_name="Blog Title")
    description = HTMLField(verbose_name="Blog Content")
    posted_date = models.DateTimeField(default=timezone.now, verbose_name="Published Date")
    updated_date = models.DateTimeField(auto_now=True, verbose_name="Last Updated")
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True, verbose_name="Featured Image")
    
    # SEO Fields (Rank Math style)
    slug = models.SlugField(
        max_length=220, 
        unique=True, 
        blank=True,
        verbose_name="URL Slug",
        help_text="Leave blank to auto-generate from title"
    )
    
    meta_title = models.CharField(
        max_length=60, 
        blank=True, 
        null=True,
        verbose_name="SEO Title",
        help_text="Recommended: 50-60 characters. Leave blank to use post title."
    )
    
    meta_description = models.CharField(
        max_length=160, 
        blank=True, 
        null=True,
        verbose_name="Meta Description",
        help_text="Recommended: 150-160 characters. Appears in search results."
    )
    
    focus_keyword = models.CharField(
        max_length=80, 
        blank=True, 
        null=True,
        verbose_name="Focus Keyword",
        help_text="Primary keyword for this post (e.g., 'django blog tutorial')"
    )
    
    # Additional SEO fields
    canonical_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name="Canonical URL",
        help_text="Optional: Use if this content exists elsewhere"
    )
    
    noindex = models.BooleanField(
        default=False,
        verbose_name="No Index",
        help_text="Check to prevent search engines from indexing this post"
    )
    
    nofollow = models.BooleanField(
        default=False,
        verbose_name="No Follow",
        help_text="Check to prevent search engines from following links in this post"
    )
    
    # Social Media (Open Graph)
    og_title = models.CharField(
        max_length=95, 
        blank=True, 
        null=True,
        verbose_name="Facebook/OG Title",
        help_text="Optional: Custom title for social media sharing"
    )
    
    og_description = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name="Facebook/OG Description",
        help_text="Optional: Custom description for social media"
    )
    
    og_image = models.ImageField(
        upload_to='blog_og_images/', 
        blank=True, 
        null=True,
        verbose_name="Social Media Image",
        help_text="Recommended size: 1200x630px"
    )
    
    # Analytics
    views = models.IntegerField(default=0, verbose_name="View Count")
    is_featured = models.BooleanField(default=False, verbose_name="Featured Post")
    
    class Meta:
        ordering = ['-posted_date']
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if not provided
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            
            # Ensure unique slug
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        
        # Auto-generate meta_title if not provided
        if not self.meta_title:
            self.meta_title = self.title[:60]
        
        # Auto-generate meta_description from content if not provided
        if not self.meta_description:
            # Strip HTML tags and get first 155 characters
            import re
            clean_text = re.sub('<.*?>', '', self.description)
            self.meta_description = clean_text[:155] + "..." if len(clean_text) > 155 else clean_text
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('blog_detail', kwargs={'slug': self.slug})
    
    def get_meta_title(self):
        """Return SEO title or post title"""
        return self.meta_title if self.meta_title else self.title
    
    def get_meta_description(self):
        """Return meta description or auto-generated one"""
        return self.meta_description if self.meta_description else self.title
    
    def get_og_title(self):
        """Return OG title or meta title or post title"""
        return self.og_title or self.meta_title or self.title
    
    def get_og_description(self):
        """Return OG description or meta description"""
        return self.og_description or self.meta_description or self.title
    
    def get_og_image(self):
        """Return OG image or featured image"""
        return self.og_image if self.og_image else self.image
    
    def increment_views(self):
        """Increment view count"""
        self.views += 1
        self.save(update_fields=['views'])
    
    def __str__(self):
        return self.title


class Category(models.Model):
    """Optional: Blog categories for better organization"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)
    meta_title = models.CharField(max_length=60, blank=True, null=True)
    meta_description = models.CharField(max_length=160, blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


# Add to BlogPost model if using categories:
# category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class TypingTestResult(models.Model):
    """
    Store typing test results with automatic marking system
    """
    # User (logged in user)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='typing_results',
        verbose_name="User"
    )
    
    # Test Configuration
    test_duration = models.IntegerField(
        verbose_name="Test Duration (seconds)"
    )
    time_taken = models.IntegerField(
        verbose_name="Time Taken (seconds)"
    )
    time_taken_formatted = models.CharField(
        max_length=20,
        verbose_name="Time Taken"
    )
    
    # Main Statistics
    wpm = models.IntegerField(
        verbose_name="WPM",
        validators=[MinValueValidator(0)]
    )
    accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Accuracy (%)",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Entry Statistics
    correct_entries = models.IntegerField(
        validators=[MinValueValidator(0)]
    )
    incorrect_entries = models.IntegerField(
        validators=[MinValueValidator(0)]
    )
    fixed_mistakes = models.IntegerField(
        validators=[MinValueValidator(0)]
    )
    total_entries = models.IntegerField(
        validators=[MinValueValidator(0)]
    )
    error_rate = models.IntegerField(
        validators=[MinValueValidator(0)]
    )
    
    # Speed Statistics
    raw_speed = models.IntegerField(
        verbose_name="Raw Speed (WPM)",
        validators=[MinValueValidator(0)]
    )
    key_speed = models.IntegerField(
        verbose_name="Key Speed (KPM)",
        validators=[MinValueValidator(0)]
    )
    complete_words = models.IntegerField(
        validators=[MinValueValidator(0)]
    )
    
    # Character Analysis
    fastest_chars = models.JSONField(null=True, blank=True)
    slowest_chars = models.JSONField(null=True, blank=True)
    most_missed = models.JSONField(null=True, blank=True)
    most_inaccurate = models.JSONField(null=True, blank=True)
    
    # MARKS (Calculated automatically)
    marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Marks (out of 100)",
        null=True,
        blank=True
    )
    
    # Timestamp
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = "Typing Test Result"
        verbose_name_plural = "Typing Test Results"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.wpm} WPM - {self.marks} marks"
    
    def save(self, *args, **kwargs):
        """Auto-calculate marks before saving"""
        if self.marks is None:
            self.marks = self.calculate_marks()
        super().save(*args, **kwargs)
    
    def calculate_marks(self):
        """Calculate marks: 60% WPM + 40% Accuracy (delegates to the shared formula
        in typingApp.scoring so this and every game in the `games` app score identically)."""
        from .scoring import calculate_marks
        return calculate_marks(self.wpm, self.accuracy)
    
# models.py - Updated Score Model

class Score(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='score',
        verbose_name="User"
    )
    
    # Total accumulated score (keeps adding)
    total_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Total Score"
    )
    
    # Total tests completed
    total_tests = models.IntegerField(
        default=0,
        verbose_name="Total Tests"
    )
    
    # ═══════════════════════════════════════════════════
    # 👇 NEW FIELDS - Add these 👇
    # ═══════════════════════════════════════════════════
    
    # Average WPM
    average_wpm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        verbose_name="Average WPM"
    )
    
    # Average Accuracy
    average_accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Average Accuracy"
    )
    
    # Best WPM (optional - nice to have)
    best_wpm = models.IntegerField(
        default=0,
        verbose_name="Best WPM"
    )
    
    # Best Accuracy (optional - nice to have)
    best_accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Best Accuracy"
    )
    
    # ═══════════════════════════════════════════════════
    
    # Last updated
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Last Updated"
    )
    
    class Meta:
        verbose_name = "Score"
        verbose_name_plural = "Scores"
        ordering = ['-total_score']
    
    def __str__(self):
        return f"{self.user.username} - {self.total_score} points"
    
    def get_badge(self):
        if self.total_score >= 1000:
            return 'MYTHIC FINGERS'
        elif self.total_score >= 500:
            return 'DIAMOND'
        elif self.total_score >= 250:
            return 'GOLD'
        elif self.total_score >= 100:
            return 'SILVER'
        elif self.total_score >= 50:
            return 'BRONZE'
        else:
            return 'BEGINNER'


class LessonProgress(models.Model):
    """A user's best result in one lesson on the lesson map"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
    )
    lesson = models.CharField(max_length=40)
    attempts = models.IntegerField(default=0)
    best_accuracy = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    best_wpm = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'lesson'], name='unique_user_lesson'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.lesson} - {self.best_accuracy}%"
