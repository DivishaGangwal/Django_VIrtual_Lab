"""
Forms for Virtual Lab CSV File Ingestion.
Server-side validation is the real security boundary; the JS checks in
csv_uploader.js only exist to give faster feedback.
"""

from django import forms
from django.core.exceptions import ValidationError

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        required=True,
        label="Select CSV Dataset",
        widget=forms.FileInput(attrs={
            'class': 'file-input-control',
            'accept': '.csv,text/csv',
            'id': 'csvFileInput',
            'hidden': True,
        }),
    )

    def clean_csv_file(self):
        uploaded_file = self.cleaned_data.get('csv_file')
        if not uploaded_file:
            raise ValidationError("No file was uploaded.")

        if not uploaded_file.name.lower().endswith('.csv'):
            raise ValidationError("Invalid file format. Please upload a file with a .csv extension.")

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
                "This file is not plain-text CSV (it looks like a binary/Excel file). "
                "In Excel use File → Save As → CSV."
            )

        return uploaded_file

