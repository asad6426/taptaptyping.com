from django.contrib import admin
from django.utils import timezone

from .models import ContentItem, ContentReport, TestResult, TestSession, UserPreference


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    list_display = ('language', 'content_type', 'difficulty', 'review_status', 'reviewed_by', 'version', 'updated_at')
    list_filter = ('review_status', 'content_type', 'language')
    search_fields = ('text', 'source_or_license')
    readonly_fields = ('reviewed_by', 'reviewed_at', 'version', 'created_at', 'updated_at')
    actions = ('approve', 'reject', 'mark_unreviewed')

    def save_model(self, request, obj, form, change):
        if change and 'text' in form.changed_data:
            obj.version += 1
            # Changed text needs reviewing again
            if 'review_status' not in form.changed_data:
                obj.review_status = ContentItem.UNREVIEWED
                obj.reviewed_by = None
                obj.reviewed_at = None
        if 'review_status' in form.changed_data:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    def set_status(self, request, queryset, status):
        for item in queryset:
            item.review_status = status
            item.reviewed_by = request.user
            item.reviewed_at = timezone.now()
            item.save()

    @admin.action(description='Approve: reviewed by a native speaker')
    def approve(self, request, queryset):
        self.set_status(request, queryset, ContentItem.APPROVED)

    @admin.action(description='Reject: stop showing this text')
    def reject(self, request, queryset):
        self.set_status(request, queryset, ContentItem.REJECTED)

    @admin.action(description='Mark as unreviewed')
    def mark_unreviewed(self, request, queryset):
        self.set_status(request, queryset, ContentItem.UNREVIEWED)


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ('language', 'mode', 'message', 'resolved', 'created_at')
    list_filter = ('resolved', 'language')
    search_fields = ('message', 'excerpt')
    readonly_fields = ('language', 'mode', 'excerpt', 'message', 'reporter', 'created_at')


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'language', 'mode', 'duration_sec', 'text_size', 'input_category', 'wpm', 'accuracy', 'is_ranked', 'review_status', 'flag_reason', 'created_at')
    list_filter = ('review_status', 'is_ranked', 'language', 'mode', 'input_category')
    search_fields = ('user__username',)
    readonly_fields = [field.name for field in TestResult._meta.fields if field.name != 'review_status']
    actions = ('approve_flagged', 'reject_flagged')

    @admin.action(description='Approve: allow on the leaderboard')
    def approve_flagged(self, request, queryset):
        queryset.update(review_status=TestResult.APPROVED)

    @admin.action(description='Reject: keep off the leaderboard')
    def reject_flagged(self, request, queryset):
        queryset.update(review_status=TestResult.REJECTED)


@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'language', 'mode', 'created_at', 'started_at', 'used_at')
    list_filter = ('language', 'mode')
    readonly_fields = [field.name for field in TestSession._meta.fields]


admin.site.register(UserPreference)
