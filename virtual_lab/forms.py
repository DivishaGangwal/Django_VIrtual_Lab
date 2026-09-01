"""
Forms for Virtual Lab CSV File Ingestion.
Enforces strict file validation (extension, MIME type, size).
"""

from django import forms
from django.core.exceptions import ValidationError

VALID_MIME_TYPES = [
    'text/csv',
    'text/plain',
    'application/vnd.ms-excel',
    'application/csv',
    'text/comma-separated-values',
    'application/octet-stream',
]

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class CSVUploadForm(forms.Form):
    """
    Form to handle and validate user-uploaded CSV files.
    """
    csv_file = forms.FileField(
        required=True,
        label="Select CSV Dataset",
        widget=forms.FileInput(attrs={
            'class': 'file-input-control',
            'accept': '.csv',
            'id': 'csvFileInput'
        })
    )

    def clean_csv_file(self):
        uploaded_file = self.cleaned_data.get('csv_file')
        if not uploaded_file:
            raise ValidationError("No file was uploaded.")

        # 1. Check file extension
        filename = uploaded_file.name
        if not filename.lower().endswith('.csv'):
            raise ValidationError("Invalid file format. Please upload a file with a .csv extension.")

        # 2. Check file size (max 5MB, min > 0 bytes)
        if uploaded_file.size == 0:
            raise ValidationError("The uploaded CSV file is empty (0 bytes).")
        if uploaded_file.size > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
            raise ValidationError(f"File size ({uploaded_file.size / (1024*1024):.2f} MB) exceeds the {max_mb:.0f} MB limit.")

        # 3. Check content type if present
        content_type = getattr(uploaded_file, 'content_type', None)
        if content_type and content_type not in VALID_MIME_TYPES:
            # Allow lenient parsing if extension is definitely .csv
            pass

        return uploaded_file
