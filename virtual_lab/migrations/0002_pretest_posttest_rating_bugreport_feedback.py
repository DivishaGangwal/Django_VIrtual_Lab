import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("virtual_lab", "0001_initial"),
    ]

    operations = [
        # Existing attempts came from the old single quiz, so they are marked
        # 'legacy_quiz'; new attempts always set pretest/posttest explicitly.
        migrations.AddField(
            model_name="quizattempt",
            name="test_type",
            field=models.CharField(
                choices=[
                    ("pretest", "Pretest"),
                    ("posttest", "Posttest"),
                    ("legacy_quiz", "Quiz (legacy)"),
                ],
                default="legacy_quiz",
                max_length=12,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="quizattempt",
            name="difficulty_levels",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.CreateModel(
            name="Rating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(max_length=40, unique=True)),
                (
                    "stars",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ]
                    ),
                ),
                ("comment", models.TextField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="BugReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("issue_types", models.JSONField(default=list)),
                ("description", models.TextField(max_length=2000)),
                ("page_name", models.CharField(blank=True, max_length=100)),
                ("session_key", models.CharField(blank=True, max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Feedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(blank=True, max_length=100)),
                (
                    "overall_rating",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ]
                    ),
                ),
                ("most_useful", models.TextField(blank=True, max_length=2000)),
                ("to_improve", models.TextField(blank=True, max_length=2000)),
                (
                    "would_recommend",
                    models.CharField(choices=[("yes", "Yes"), ("maybe", "Maybe"), ("no", "No")], max_length=5),
                ),
                ("session_key", models.CharField(blank=True, max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"], "verbose_name_plural": "feedback"},
        ),
    ]
