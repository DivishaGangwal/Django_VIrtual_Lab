from django.db import models


class QuizAttempt(models.Model):
    """One submitted Step-6 quiz, graded on the server."""

    student_name = models.CharField(max_length=100, blank=True)
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
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

    def __str__(self) -> str:
        who = self.student_name or 'Anonymous'
        return f'{who}: {self.score}/{self.total} ({self.created_at:%Y-%m-%d %H:%M})'
