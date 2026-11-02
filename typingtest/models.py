from django.conf import settings
from django.db import models


class ContentItem(models.Model):
    """A word list or passage. Nothing is treated as reviewed until a person approves it."""
    WORD_LIST = 'word_list'
    PARAGRAPH = 'paragraph'
    TYPES = ((WORD_LIST, 'Word list'), (PARAGRAPH, 'Paragraph'))
    UNREVIEWED = 'unreviewed'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUSES = ((UNREVIEWED, 'Unreviewed'), (APPROVED, 'Approved'), (REJECTED, 'Rejected'))

    language = models.CharField(max_length=30, db_index=True)
    content_type = models.CharField(max_length=20, choices=TYPES)
    difficulty = models.CharField(max_length=20, blank=True)
    text = models.TextField(help_text='Word list: words separated by spaces. Paragraph: one sentence per line.')
    source_or_license = models.CharField(max_length=200)
    review_status = models.CharField(max_length=20, choices=STATUSES, default=UNREVIEWED, db_index=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['language', 'content_type', 'pk']

    def __str__(self):
        return f'{self.language} {self.content_type} v{self.version}'


class ContentReport(models.Model):
    """A visitor's report of a mistake in practice text."""
    language = models.CharField(max_length=30)
    mode = models.CharField(max_length=20)
    excerpt = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    reporter = models.CharField(max_length=60)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.language}: {self.message[:40]}'


class TestSession(models.Model):
    """One ranked attempt. The server keeps the text and its own clock here."""
    token = models.CharField(max_length=40, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='language_test_sessions')
    language = models.CharField(max_length=30)
    mode = models.CharField(max_length=20)
    duration_sec = models.IntegerField(null=True, blank=True)
    text_size = models.CharField(max_length=20, blank=True)
    difficulty = models.CharField(max_length=20, blank=True)
    target_text = models.TextField()
    content_version = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.user} {self.language} {self.mode}'


class TestResult(models.Model):
    """One finished multilingual test. The older typingApp results are separate and unchanged."""
    CLEAN = 'clean'
    FLAGGED = 'flagged'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    REVIEW_STATUSES = ((CLEAN, 'Clean'), (FLAGGED, 'Flagged'), (APPROVED, 'Approved'), (REJECTED, 'Rejected'))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='language_test_results')

    # Configuration. Results are only compared when these match.
    language = models.CharField(max_length=30)
    mode = models.CharField(max_length=20)
    duration_sec = models.IntegerField(null=True, blank=True)
    text_size = models.CharField(max_length=20, blank=True)
    difficulty = models.CharField(max_length=20, blank=True)
    script_variant = models.CharField(max_length=20, blank=True)
    keyboard_layout = models.CharField(max_length=30, default='unspecified')
    input_method = models.CharField(max_length=30, default='unspecified')
    input_category = models.CharField(max_length=20, default='unspecified')

    # Leaderboard state. Only results validated through a TestSession can be ranked.
    is_ranked = models.BooleanField(default=False, db_index=True)
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUSES, default=CLEAN, db_index=True)
    flag_reason = models.CharField(max_length=100, blank=True)

    # Figures sent by the browser, within limits checked by the server
    correct_units = models.IntegerField()
    incorrect_units = models.IntegerField()
    corrections = models.IntegerField()
    attempts = models.IntegerField()
    elapsed_sec = models.FloatField()
    accuracy = models.FloatField()

    # Calculated by the server
    cpm = models.FloatField()
    wpm = models.FloatField()

    scoring_version = models.CharField(max_length=10)
    content_version = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['user', 'language', 'mode', 'duration_sec', 'text_size', 'difficulty'], name='tt_result_config'),
        ]

    def __str__(self):
        return f'{self.user} {self.language} {self.mode} {self.wpm} WPM'


class UserPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='typing_preference')
    display_name = models.CharField(max_length=40, blank=True)
    default_language = models.CharField(max_length=30, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Preferences for {self.user}'
