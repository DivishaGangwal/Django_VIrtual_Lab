from django.contrib import admin

from .models import QuizAttempt


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'score', 'total', 'percentage', 'dataset_filename', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('student_name', 'session_key')
    readonly_fields = ('created_at',)
