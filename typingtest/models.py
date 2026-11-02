from django.conf import settings
from django.db import models


class TestResult(models.Model):
    """One finished multilingual test. The older typingApp results are separate and unchanged."""
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
