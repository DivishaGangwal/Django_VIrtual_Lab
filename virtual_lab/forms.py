"""
Forms for Virtual Lab.
Server-side validation is the real security boundary; the JS checks in
csv_uploader.js / feedback_widgets.js only exist to give faster feedback.
The rating, bug-report and feedback forms validate JSON bodies (form(data=dict)).
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import BugReport, Feedback

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def not_csv_message(filename: str) -> str:
    """Same wording as csv_uploader.js so browser and server errors match."""
    name = filename if len(filename) <= 80 else filename[:77] + '…'
    return f"✗ File not accepted: '{name}' is not a CSV file. Only .csv files are supported."


class CSVUploadForm(forms.Form):
    # No `accept` attribute: the picker shows every file type so that choosing
    # a wrong file produces a clear error message instead of being greyed out.
    csv_file = forms.FileField(
        required=True,
        label="Select CSV Dataset",
        widget=forms.FileInput(attrs={
            'class': 'file-input-control',
            'id': 'csvFileInput',
            'hidden': True,
        }),
    )

    def clean_csv_file(self):
        uploaded_file = self.cleaned_data.get('csv_file')
        if not uploaded_file:
            raise ValidationError("No file was uploaded.")

        if not uploaded_file.name.lower().endswith('.csv'):
            raise ValidationError(not_csv_message(uploaded_file.name))

        if uploaded_file.size == 0:
            raise ValidationError("The uploaded CSV file is empty (0 bytes).")
        if uploaded_file.size > MAX_FILE_SIZE_BYTES:
            raise ValidationError(
                f"File size ({uploaded_file.size / (1024 * 1024):.2f} MB) exceeds the "
                f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit."
            )

        # Content sniff: a real CSV is text. Reject binary files renamed to .csv
        # (e.g. an .xlsx, which is a ZIP archive, or an image).
        head = uploaded_file.read(1024)
        uploaded_file.seek(0)
        if b'\x00' in head or head.startswith(b'PK\x03\x04'):
            raise ValidationError(
                f"✗ File not accepted: '{uploaded_file.name}' is not plain-text CSV (it looks like a "
                "binary/Excel file renamed to .csv). In Excel use File → Save As → CSV."
            )

        return uploaded_file


class RatingForm(forms.Form):
    stars = forms.IntegerField(min_value=1, max_value=5)
    comment = forms.CharField(required=False, max_length=1000)


class BugReportForm(forms.Form):
    issue_types = forms.MultipleChoiceField(choices=BugReport.ISSUE_TYPE_CHOICES)
    description = forms.CharField(max_length=2000)
    page_name = forms.CharField(required=False, max_length=100)

    def clean_description(self):
        text = self.cleaned_data['description'].strip()
        if len(text) < 5:
            raise ValidationError("Please describe the problem in a few words.")
        return text


class FeedbackForm(forms.Form):
    name = forms.CharField(required=False, max_length=100)
    overall_rating = forms.IntegerField(min_value=1, max_value=5)
    most_useful = forms.CharField(required=False, max_length=2000)
    to_improve = forms.CharField(required=False, max_length=2000)
    would_recommend = forms.ChoiceField(choices=Feedback.RECOMMEND_CHOICES)
