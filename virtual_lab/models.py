from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

STAR_VALIDATORS = [MinValueValidator(1), MaxValueValidator(5)]


class QuizAttempt(models.Model):
    """One submitted Pretest/Posttest, graded on the server."""

    PRETEST = 'pretest'
    POSTTEST = 'posttest'
    LEGACY_QUIZ = 'legacy_quiz'  # attempts saved by the old single 10-question quiz
    TEST_TYPE_CHOICES = [
        (PRETEST, 'Pretest'),
        (POSTTEST, 'Posttest'),
        (LEGACY_QUIZ, 'Quiz (legacy)'),
    ]

    student_name = models.CharField(max_length=100, blank=True)
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    test_type = models.CharField(max_length=12, choices=TEST_TYPE_CHOICES)
    difficulty_levels = models.JSONField(default=list, blank=True)
    score = models.PositiveSmallIntegerField()
    total = models.PositiveSmallIntegerField()
    answers = models.JSONField(default=dict)
    dataset_filename = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def percentage(self) -> float:
        return round(100 * self.score / self.total, 1) if self.total else 0.0

    @property
    def levels_display(self) -> str:
        return ', '.join(level.capitalize() for level in self.difficulty_levels) or '—'

    def __str__(self) -> str:
        who = self.student_name or 'Anonymous'
        return f'{who} · {self.get_test_type_display()}: {self.score}/{self.total} ({self.created_at:%Y-%m-%d %H:%M})'


class Rating(models.Model):
    """'Rate me' in the header. One per browser session; re-rating updates it."""

    session_key = models.CharField(max_length=40, unique=True)
    stars = models.PositiveSmallIntegerField(validators=STAR_VALIDATORS)
    comment = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f'{self.stars}★ ({self.updated_at:%Y-%m-%d %H:%M})'


class BugReport(models.Model):
    """'Report bug' in the header."""

    ISSUE_TYPE_CHOICES = [
        ('content_error', 'Content error'),
        ('simulation_not_working', 'Simulation not working'),
        ('ui_problem', 'UI problem'),
        ('other', 'Other'),
    ]

    issue_types = models.JSONField(default=list)
    description = models.TextField(max_length=2000)
    page_name = models.CharField(max_length=100, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def issue_types_display(self) -> str:
        labels = dict(self.ISSUE_TYPE_CHOICES)
        return ', '.join(labels.get(t, t) for t in self.issue_types)

    def __str__(self) -> str:
        return f'{self.issue_types_display} on {self.page_name or "?"} ({self.created_at:%Y-%m-%d %H:%M})'


class Feedback(models.Model):
    """Step 9 feedback form."""

    RECOMMEND_CHOICES = [('yes', 'Yes'), ('maybe', 'Maybe'), ('no', 'No')]

    name = models.CharField(max_length=100, blank=True)
    overall_rating = models.PositiveSmallIntegerField(validators=STAR_VALIDATORS)
    most_useful = models.TextField(max_length=2000, blank=True)
    to_improve = models.TextField(max_length=2000, blank=True)
    would_recommend = models.CharField(max_length=5, choices=RECOMMEND_CHOICES)
    session_key = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'feedback'

    def __str__(self) -> str:
        return f'{self.name or "Anonymous"}: {self.overall_rating}★ ({self.created_at:%Y-%m-%d %H:%M})'
