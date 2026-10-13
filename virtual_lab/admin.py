from django.contrib import admin

from .models import BugReport, Feedback, QuizAttempt, Rating


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'test_type', 'levels_display', 'score', 'total', 'percentage',
                    'dataset_filename', 'created_at')
    list_filter = ('test_type', 'created_at')
    search_fields = ('student_name', 'session_key')
    readonly_fields = ('created_at',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('stars', 'comment', 'updated_at', 'created_at')
    list_filter = ('stars',)
    search_fields = ('comment', 'session_key')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = ('issue_types_display', 'page_name', 'description', 'created_at')
    list_filter = ('page_name', 'created_at')
    search_fields = ('description', 'page_name')
    readonly_fields = ('created_at',)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'overall_rating', 'would_recommend', 'created_at')
    list_filter = ('overall_rating', 'would_recommend', 'created_at')
    search_fields = ('name', 'most_useful', 'to_improve')
    readonly_fields = ('created_at',)
