"""
Run with:  python manage.py test
"""

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import QuizAttempt
from .quiz_bank import QUIZ_QUESTIONS
from .services import CSVParserService, SampleLoaderService, build_chart_data, describe_dataset
from .services.chart_builder import ChartBuildError
from .services.stats_engine import infer_column_type


class CSVParserTests(TestCase):
    def parse(self, text, **kw):
        return CSVParserService.parse_csv_content(text, **kw)

    def test_basic_comma(self):
        r = self.parse('a,b\n1,2\n3,4\n')
        self.assertEqual(r['status'], 'success')
        self.assertEqual(r['headers'], ['a', 'b'])
        self.assertEqual(r['row_count'], 2)
        self.assertEqual(r['rows'][1], {'a': '3', 'b': '4'})

    def test_headers_with_spaces_keep_values(self):
        # Regression: the old parser looked up stripped names in un-stripped
        # DictReader keys, so every value under ' Marks' became empty.
        r = self.parse('Name, Marks\nA, 90\nB, 80\n')
        self.assertEqual(r['headers'], ['Name', 'Marks'])
        self.assertEqual([row['Marks'] for row in r['rows']], ['90', '80'])
        self.assertEqual(r['missing_values_count'], 0)

    def test_duplicate_and_blank_headers(self):
        r = self.parse('id,,id\n1,x,2\n')
        self.assertEqual(r['headers'], ['id', 'Column_2', 'id_2'])
        self.assertEqual(r['rows'][0], {'id': '1', 'Column_2': 'x', 'id_2': '2'})

    def test_semicolon_and_tab(self):
        self.assertEqual(self.parse('a;b\n1;2\n3;4\n')['delimiter'], ';')
        self.assertEqual(self.parse('a\tb\n1\t2\n3\t4\n')['delimiter'], '\t')

    def test_quoted_commas(self):
        r = self.parse('name,city\n"Rao, Aditi",Pune\n')
        self.assertEqual(r['rows'][0]['name'], 'Rao, Aditi')

    def test_missing_values_counted(self):
        r = self.parse('a,b\n1,\nNA,2\nnull,-\n')
        self.assertEqual(r['missing_values_count'], 4)

    def test_ragged_rows_padded(self):
        r = self.parse('a,b,c\n1,2\n1,2,3,4\n')
        self.assertEqual(r['ragged_rows_count'], 2)
        self.assertEqual(r['rows'][0], {'a': '1', 'b': '2', 'c': ''})

    def test_errors(self):
        self.assertEqual(self.parse('')['status'], 'error')
        self.assertEqual(self.parse('a,b\n')['status'], 'error')

    def test_max_rows(self):
        r = self.parse('a\n1\n2\n3\n', max_rows=2)
        self.assertTrue(r['truncated'])
        self.assertEqual(r['row_count'], 2)

    def test_decode_bom_and_cp1252(self):
        self.assertEqual(CSVParserService.decode_file_stream(b'\xef\xbb\xbfa,b'), 'a,b')
        self.assertEqual(CSVParserService.decode_file_stream('café'.encode('cp1252')), 'café')


class StatsTests(TestCase):
    def test_type_inference(self):
        self.assertEqual(infer_column_type(['1', '2', '']), 'int')
        self.assertEqual(infer_column_type(['1.5', '2']), 'float')
        self.assertEqual(infer_column_type(['2026-01-01', '2026-02-01']), 'date')
        self.assertEqual(infer_column_type(['a', '1']), 'str')

    def test_numeric_stats(self):
        rows = [{'x': v} for v in ['10', '20', '30', '1000']]
        col = describe_dataset(['x'], rows)['columns'][0]
        self.assertEqual(col['mean'], 265.0)
        self.assertEqual(col['median'], 25.0)
        self.assertEqual(col['min'], 10.0)
        self.assertEqual(col['max'], 1000.0)

    def test_all_samples_load(self):
        for s in SampleLoaderService.get_sample_list():
            r = SampleLoaderService.load_sample_dataset(s['id'])
            self.assertEqual(r['status'], 'success', s['id'])
            describe_dataset(r['headers'], r['rows'])

    def test_unknown_sample(self):
        self.assertEqual(SampleLoaderService.load_sample_dataset('nope')['status'], 'error')


class ChartBuilderTests(TestCase):
    headers = ['Dept', 'Marks', 'Att']
    rows = [
        {'Dept': 'CS', 'Marks': '80', 'Att': '90'},
        {'Dept': 'CS', 'Marks': '90', 'Att': '95'},
        {'Dept': 'IT', 'Marks': '70', 'Att': ''},
    ]

    def test_bar_mean(self):
        p = build_chart_data(self.headers, self.rows, 'bar', 'Dept', ['Marks'], 'mean')
        self.assertEqual(p['labels'], ['CS', 'IT'])
        self.assertEqual(p['datasets'][0]['data'], [85.0, 70.0])

    def test_pie_counts(self):
        p = build_chart_data(self.headers, self.rows, 'pie', 'Dept', [], 'none')
        self.assertEqual(p['datasets'][0]['data'], [2, 1])

    def test_scatter_skips_missing(self):
        p = build_chart_data(self.headers, self.rows, 'scatter', 'Att', ['Marks'])
        self.assertEqual(len(p['datasets'][0]['data']), 2)

    def test_histogram(self):
        p = build_chart_data(self.headers, self.rows, 'histogram', 'Marks', [], bins=2)
        self.assertEqual(sum(p['datasets'][0]['data']), 3)

    def test_bad_column(self):
        with self.assertRaises(ChartBuildError):
            build_chart_data(self.headers, self.rows, 'bar', 'Nope', ['Marks'])


class PageTests(TestCase):
    def test_all_pages_render(self):
        for name in ['aim', 'theory', 'procedure', 'simulation', 'observations', 'quiz']:
            r = self.client.get(reverse(f'virtual_lab:{name}'))
            self.assertEqual(r.status_code, 200, name)

    def test_progress_ribbon_marks_current_step(self):
        r = self.client.get(reverse('virtual_lab:quiz'))
        self.assertContains(r, 'class="lab-step-item active"', count=1)
        self.assertContains(r, 'class="lab-step-item completed"', count=5)


class ApiTests(TestCase):
    def upload(self, name, content):
        return self.client.post(reverse('virtual_lab:api_upload_csv'),
                                {'csv_file': SimpleUploadedFile(name, content, content_type='text/csv')})

    def test_upload_flow_and_observations(self):
        r = self.upload('t.csv', b'Dept,Marks\nCS,80\nIT,70\n')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['row_count'], 2)
        self.assertIn('stats', data)

        self.assertEqual(self.client.get(reverse('virtual_lab:api_dataset')).status_code, 200)
        obs = self.client.get(reverse('virtual_lab:observations'))
        self.assertContains(obs, 't.csv')
        csv_export = self.client.get(reverse('virtual_lab:export_observations'))
        self.assertEqual(csv_export['Content-Type'], 'text/csv')

        chart = self.client.get(reverse('virtual_lab:api_chart_data'), {'type': 'bar', 'x': 'Dept', 'y': 'Marks', 'agg': 'mean'})
        self.assertEqual(chart.json()['labels'], ['CS', 'IT'])

        self.client.post(reverse('virtual_lab:api_reset_dataset'))
        self.assertEqual(self.client.get(reverse('virtual_lab:api_dataset')).status_code, 404)

    def test_upload_rejections(self):
        self.assertEqual(self.upload('x.txt', b'a,b\n1,2').status_code, 400)
        self.assertEqual(self.upload('x.csv', b'').status_code, 400)
        self.assertEqual(self.upload('x.csv', b'PK\x03\x04binary').status_code, 400)
        self.assertEqual(self.upload('x.csv', b'a,b\n').status_code, 400)

    def test_upload_requires_post(self):
        self.assertEqual(self.client.get(reverse('virtual_lab:api_upload_csv')).status_code, 405)

    def test_csrf_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse('virtual_lab:api_upload_csv'), {'csv_file': SimpleUploadedFile('t.csv', b'a\n1\n')})
        self.assertEqual(r.status_code, 403)

    def test_sample_api(self):
        r = self.client.get(reverse('virtual_lab:api_load_sample'), {'sample_id': 'lab_sensor_log'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['delimiter'], ';')
        self.assertGreater(r.json()['missing_values_count'], 0)
        self.assertEqual(self.client.get(reverse('virtual_lab:api_load_sample'), {'sample_id': 'bad'}).status_code, 400)

    def test_chart_without_dataset(self):
        self.assertEqual(self.client.get(reverse('virtual_lab:api_chart_data'), {'x': 'a'}).status_code, 400)

    def test_quiz_grading_saves_attempt(self):
        answers = {q['id']: q['answer'] for q in QUIZ_QUESTIONS}
        answers['q1'] = (QUIZ_QUESTIONS[0]['answer'] + 1) % 4
        r = self.client.post(reverse('virtual_lab:api_submit_quiz'),
                             data=json.dumps({'student_name': 'Test', 'answers': answers}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['score'], 9)
        self.assertEqual(QuizAttempt.objects.get().score, 9)

    def test_quiz_page_hides_answers(self):
        r = self.client.get(reverse('virtual_lab:quiz'))
        self.assertNotContains(r, QUIZ_QUESTIONS[0]['explanation'])
