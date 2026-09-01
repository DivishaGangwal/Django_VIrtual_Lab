"""
Unit tests for Pure-Python CSV Parser and Sample Loader Services (Developer 1).
"""

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from virtual_lab.services.csv_parser import CSVParserService
from virtual_lab.services.sample_loader import SampleLoaderService


class CSVParserServiceTestCase(TestCase):
    """
    Tests pure-Python CSV stream decoding, sniffer dialect handling, and error edge cases.
    """

    def test_parse_valid_comma_csv(self):
        csv_data = "ID,Name,Marks\n101,Alice,88.5\n102,Bob,72.0\n103,Charlie,94.0"
        result = CSVParserService.parse_csv_content(csv_data)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['row_count'], 3)
        self.assertEqual(result['col_count'], 3)
        self.assertEqual(result['headers'], ['ID', 'Name', 'Marks'])
        self.assertEqual(result['delimiter'], ',')
        self.assertEqual(result['rows'][0]['Name'], 'Alice')
        self.assertEqual(result['rows'][2]['Marks'], '94.0')

    def test_parse_semicolon_delimited_csv(self):
        csv_data = "Month;Temp;Rainfall\nJan;14.5;12.0\nFeb;17.2;18.5\nMar;23.0;15.2\nApr;29.4;24.0"
        result = CSVParserService.parse_csv_content(csv_data)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['row_count'], 4)
        self.assertEqual(result['headers'], ['Month', 'Temp', 'Rainfall'])
        self.assertEqual(result['delimiter'], ';')

    def test_parse_quoted_fields_with_commas(self):
        csv_data = 'ID,Student_Name,Remarks\n1,"Doe, John","Excellent, hard worker"\n2,"Smith, Jane","Good"'
        result = CSVParserService.parse_csv_content(csv_data)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['row_count'], 2)
        self.assertEqual(result['rows'][0]['Student_Name'], 'Doe, John')
        self.assertEqual(result['rows'][0]['Remarks'], 'Excellent, hard worker')

    def test_parse_empty_content(self):
        result = CSVParserService.parse_csv_content("")
        self.assertEqual(result['status'], 'error')

    def test_decode_byte_stream_utf8(self):
        raw_bytes = b"ColA,ColB\n1,2\n3,4"
        decoded = CSVParserService.decode_file_stream(raw_bytes)
        self.assertIn("ColA,ColB", decoded)

    def test_sample_loader_student_marks(self):
        result = SampleLoaderService.load_sample_dataset('student_marks')
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['row_count'], 10)
        self.assertIn('Marks', result['headers'])

    def test_sample_loader_weather(self):
        result = SampleLoaderService.load_sample_dataset('monthly_weather')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['row_count'], 12)
        self.assertIn('Month', result['headers'])

    def test_sample_loader_server_metrics(self):
        result = SampleLoaderService.load_sample_dataset('server_metrics')
        self.assertEqual(result['status'], 'success')
        self.assertIn('CPU_Utilization_Pct', result['headers'])


class IngestionAPITestCase(TestCase):
    """
    Tests Django API upload and sample load endpoints.
    """

    def setUp(self):
        self.client = Client()

    def test_upload_csv_api_success(self):
        csv_content = b"ID,Name,Marks\n1,Alice,90\n2,Bob,85"
        uploaded_file = SimpleUploadedFile("test_marks.csv", csv_content, content_type="text/csv")

        response = self.client.post(reverse('virtual_lab:api_upload_csv'), {
            'csv_file': uploaded_file
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['row_count'], 2)
        self.assertEqual(data['col_count'], 3)
        self.assertEqual(data['headers'], ['ID', 'Name', 'Marks'])

    def test_upload_invalid_file_extension(self):
        uploaded_file = SimpleUploadedFile("test.txt", b"some text", content_type="text/plain")

        response = self.client.post(reverse('virtual_lab:api_upload_csv'), {
            'csv_file': uploaded_file
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')

    def test_load_sample_api(self):
        response = self.client.get(reverse('virtual_lab:api_load_sample') + '?sample_id=monthly_weather')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['row_count'], 12)
