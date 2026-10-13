"""
Run with:  python manage.py test
"""

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from virtual_lab import assessment_bank
from virtual_lab.assessment_bank import POSTTEST_QUESTIONS, PRETEST_QUESTIONS
from virtual_lab.models import BugReport, Feedback, QuizAttempt, Rating
from virtual_lab.services import CSVParserService, SampleLoaderService, build_chart_data, describe_dataset
from virtual_lab.services.chart_builder import ChartBuildError
from virtual_lab.services.stats_engine import infer_column_type


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


PAGE_ORDER = ['aim', 'theory', 'pretest', 'procedure', 'simulation', 'observations',
              'posttest', 'references', 'feedback']


class PageTests(TestCase):
    def test_all_pages_render(self):
        for name in PAGE_ORDER:
            r = self.client.get(reverse(f'virtual_lab:{name}'))
            self.assertEqual(r.status_code, 200, name)
            self.assertNotContains(r, '>None<', msg_prefix=name)

    def test_step_order_in_sidebar(self):
        r = self.client.get(reverse('virtual_lab:aim'))
        html = r.content.decode()
        positions = [html.index(f'href="{reverse(f"virtual_lab:{name}")}"', html.index('id="labSidebar"'))
                     for name in PAGE_ORDER]
        self.assertEqual(positions, sorted(positions))

    def test_progress_ribbon_marks_current_step(self):
        r = self.client.get(reverse('virtual_lab:posttest'))
        self.assertContains(r, 'class="lab-step-item active"', count=1)
        self.assertContains(r, 'class="lab-step-item completed"', count=6)

    def test_prev_next_links(self):
        r = self.client.get(reverse('virtual_lab:pretest'))
        self.assertContains(r, f'href="{reverse("virtual_lab:theory")}"><i class="fa fa-angle-left"')
        self.assertContains(r, 'Next: Procedure')
        r = self.client.get(reverse('virtual_lab:observations'))
        self.assertContains(r, 'Next: Posttest')

    def test_old_quiz_url_redirects_to_posttest(self):
        r = self.client.get('/quiz/')
        self.assertRedirects(r, reverse('virtual_lab:posttest'), status_code=301)

    def test_header_footer_and_logos(self):
        r = self.client.get(reverse('virtual_lab:aim'))
        self.assertContains(r, 'Developed by Divisha')
        self.assertContains(r, 'virtual-labs/ph3-lab-mgmt')
        self.assertContains(r, 'virtual_lab/images/somaiya_logo.png')
        self.assertContains(r, 'virtual_lab/images/vlab_logo.jpg')
        self.assertContains(r, 'alt="Somaiya Vidyavihar University, K J Somaiya School of Engineering logo"')
        self.assertContains(r, 'No ratings yet')
        self.assertContains(r, 'id="rateModal"')
        self.assertContains(r, 'id="bugModal"')

    def test_file_input_accepts_any_type(self):
        r = self.client.get(reverse('virtual_lab:simulation'))
        self.assertContains(r, 'id="csvFileInput"')
        self.assertNotContains(r, 'accept=')
        self.assertContains(r, 'id="resetSimulationBtn"')


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

    def test_non_csv_rejected_with_clear_message(self):
        r = self.upload('photo.png', b'\x89PNG\r\n\x1a\n')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['status'], 'error')
        self.assertEqual(r.json()['message'],
                         "✗ File not accepted: 'photo.png' is not a CSV file. Only .csv files are supported.")
        self.assertEqual(self.client.get(reverse('virtual_lab:api_dataset')).status_code, 404)

    def test_binary_renamed_to_csv_rejected(self):
        r = self.upload('report.csv', b'PK\x03\x04binary')
        self.assertEqual(r.status_code, 400)
        self.assertIn("File not accepted: 'report.csv' is not plain-text CSV", r.json()['message'])

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

    def test_reset_clears_dataset_and_is_post_only(self):
        self.client.get(reverse('virtual_lab:api_load_sample'), {'sample_id': 'student_marks'})
        self.assertEqual(self.client.get(reverse('virtual_lab:api_dataset')).status_code, 200)
        self.assertEqual(self.client.get(reverse('virtual_lab:api_reset_dataset')).status_code, 405)
        r = self.client.post(reverse('virtual_lab:api_reset_dataset'))
        self.assertEqual(r.json(), {'status': 'success'})
        self.assertEqual(self.client.get(reverse('virtual_lab:api_dataset')).status_code, 404)
        self.assertContains(self.client.get(reverse('virtual_lab:simulation')), 'data-has-dataset="0"')
        self.assertContains(self.client.get(reverse('virtual_lab:observations')), 'No dataset loaded yet')
        # Resetting twice (nothing loaded) is harmless.
        self.assertEqual(self.client.post(reverse('virtual_lab:api_reset_dataset')).status_code, 200)

    def test_reset_requires_csrf(self):
        from django.test import Client
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse('virtual_lab:api_reset_dataset')).status_code, 403)


class AssessmentBankTests(TestCase):
    def test_each_test_has_five_questions_per_level(self):
        for bank in (PRETEST_QUESTIONS, POSTTEST_QUESTIONS):
            for level in assessment_bank.LEVEL_KEYS:
                self.assertGreaterEqual(sum(q['level'] == level for q in bank), 5)

    def test_questions_are_well_formed(self):
        ids = [q['id'] for q in PRETEST_QUESTIONS + POSTTEST_QUESTIONS]
        self.assertEqual(len(ids), len(set(ids)))
        for q in PRETEST_QUESTIONS + POSTTEST_QUESTIONS:
            self.assertEqual(len(q['options']), 4, q['id'])
            self.assertEqual(len(set(q['options'])), 4, q['id'])
            self.assertIn(q['answer'], range(4), q['id'])
            self.assertTrue(q['explanation'])

    def test_answers_spread_across_a_to_d(self):
        for bank in (PRETEST_QUESTIONS, POSTTEST_QUESTIONS):
            counts = [sum(q['answer'] == i for q in bank) for i in range(4)]
            self.assertTrue(all(c >= 3 for c in counts), counts)


class AssessmentApiTests(TestCase):
    url = reverse('virtual_lab:api_submit_assessment')

    def submit(self, test_type, levels, answers, name=''):
        return self.client.post(self.url, data=json.dumps(
            {'test_type': test_type, 'levels': levels, 'answers': answers, 'student_name': name}),
            content_type='application/json')

    @staticmethod
    def correct_answers(bank, levels):
        return {q['id']: q['answer'] for q in bank if q['level'] in levels}

    def test_pretest_grades_only_selected_level(self):
        answers = self.correct_answers(PRETEST_QUESTIONS, ['beginner'])
        answers['pre_b1'] = 3  # wrong (correct is 0)
        r = self.submit('pretest', ['beginner'], answers, 'Asha')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual((data['score'], data['total']), (4, 5))
        self.assertEqual({res['level'] for res in data['results']}, {'beginner'})
        wrong = next(res for res in data['results'] if res['id'] == 'pre_b1')
        self.assertFalse(wrong['is_correct'])
        self.assertEqual(wrong['correct_option'], 0)
        self.assertTrue(wrong['explanation'])

        attempt = QuizAttempt.objects.get()
        self.assertEqual(attempt.test_type, QuizAttempt.PRETEST)
        self.assertEqual(attempt.difficulty_levels, ['beginner'])
        self.assertEqual((attempt.score, attempt.total, attempt.student_name), (4, 5, 'Asha'))

    def test_posttest_multiple_levels(self):
        levels = ['advanced', 'intermediate']  # any order, saved in canonical order
        r = self.submit('posttest', levels, self.correct_answers(POSTTEST_QUESTIONS, levels))
        data = r.json()
        self.assertEqual((data['score'], data['total']), (10, 10))
        self.assertEqual(data['levels'], ['intermediate', 'advanced'])
        attempt = QuizAttempt.objects.get()
        self.assertEqual(attempt.test_type, 'posttest')
        self.assertEqual(attempt.difficulty_levels, ['intermediate', 'advanced'])

    def test_all_levels_and_ignores_answers_outside_levels(self):
        all_levels = assessment_bank.LEVEL_KEYS
        answers = self.correct_answers(POSTTEST_QUESTIONS, all_levels)
        self.assertEqual(self.submit('posttest', all_levels, answers).json()['total'], 15)
        # Answers for unselected levels are not graded or stored.
        r = self.submit('posttest', ['beginner'], answers)
        self.assertEqual(r.json()['total'], 5)
        self.assertTrue(all(k.startswith('post_b') for k in QuizAttempt.objects.first().answers))

    def test_unanswered_counts_as_wrong(self):
        r = self.submit('pretest', ['advanced'], {})
        self.assertEqual((r.json()['score'], r.json()['total']), (0, 5))

    def test_validation(self):
        self.assertEqual(self.submit('quiz', ['beginner'], {}).status_code, 400)
        self.assertEqual(self.submit('pretest', [], {}).status_code, 400)
        self.assertEqual(self.submit('pretest', ['expert'], {}).status_code, 400)
        self.assertEqual(self.submit('pretest', 'beginner', {}).status_code, 400)
        self.assertEqual(self.submit('pretest', ['beginner'], ['a']).status_code, 400)
        bad_json = self.client.post(self.url, data='not json', content_type='application/json')
        self.assertEqual(bad_json.status_code, 400)
        self.assertEqual(QuizAttempt.objects.count(), 0)

    def test_pages_hide_answers_and_default_to_beginner(self):
        for name, bank in (('pretest', PRETEST_QUESTIONS), ('posttest', POSTTEST_QUESTIONS)):
            r = self.client.get(reverse(f'virtual_lab:{name}'))
            self.assertContains(r, 'Choose difficulty:')
            self.assertContains(r, 'name="levels" value="beginner" checked')
            self.assertContains(r, 'name="levels" value="advanced">')
            self.assertContains(r, 'class="assessment-level is-hidden" data-level="advanced"')
            for q in bank:
                self.assertContains(r, f'data-qid="{q["id"]}"')
                self.assertNotContains(r, q['explanation'])

    def test_recent_attempts_are_per_test_type(self):
        self.submit('pretest', ['beginner'], {})
        self.assertContains(self.client.get(reverse('virtual_lab:pretest')), 'Your recent pretest attempts')
        self.assertNotContains(self.client.get(reverse('virtual_lab:posttest')), 'Your recent posttest attempts')


class RatingBugFeedbackApiTests(TestCase):
    def post(self, name, body):
        return self.client.post(reverse(f'virtual_lab:{name}'), data=json.dumps(body), content_type='application/json')

    def test_rating_created_then_updated_per_session(self):
        r = self.post('api_submit_rating', {'stars': 4, 'comment': 'Nice'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['created'])
        self.assertEqual(r.json()['summary'], {'average': 4.0, 'count': 1})
        r = self.post('api_submit_rating', {'stars': 2})
        self.assertFalse(r.json()['created'])
        self.assertEqual(Rating.objects.get().stars, 2)

        other = self.client_class()
        other.post(reverse('virtual_lab:api_submit_rating'), data=json.dumps({'stars': 5}), content_type='application/json')
        self.assertEqual(Rating.objects.count(), 2)
        self.assertContains(self.client.get(reverse('virtual_lab:aim')), '3.5')

    def test_rating_validation(self):
        for body in ({}, {'stars': 0}, {'stars': 6}, {'stars': 'abc'}, {'stars': 3, 'comment': 'x' * 1001}):
            r = self.post('api_submit_rating', body)
            self.assertEqual(r.status_code, 400, body)
            self.assertEqual(r.json()['status'], 'error')
        self.assertEqual(Rating.objects.count(), 0)

    def test_bug_report(self):
        r = self.post('api_submit_bug_report', {'issue_types': ['ui_problem', 'other'],
                                                'description': 'Chart overlaps the legend', 'page_name': 'Simulation'})
        self.assertEqual(r.status_code, 200)
        report = BugReport.objects.get()
        self.assertEqual(report.issue_types, ['ui_problem', 'other'])
        self.assertEqual(report.page_name, 'Simulation')
        self.assertEqual(report.issue_types_display, 'UI problem, Other')

    def test_bug_report_validation(self):
        for body in ({'issue_types': [], 'description': 'Something broke'},
                     {'issue_types': ['made_up'], 'description': 'Something broke'},
                     {'issue_types': ['other'], 'description': '   '},
                     {'issue_types': ['other']}):
            self.assertEqual(self.post('api_submit_bug_report', body).status_code, 400, body)
        self.assertEqual(BugReport.objects.count(), 0)

    def test_feedback(self):
        r = self.post('api_submit_feedback', {'name': '', 'overall_rating': 5, 'most_useful': 'Pipeline',
                                              'to_improve': '', 'would_recommend': 'yes'})
        self.assertEqual(r.status_code, 200)
        fb = Feedback.objects.get()
        self.assertEqual((fb.overall_rating, fb.would_recommend, fb.name), (5, 'yes', ''))

    def test_feedback_validation(self):
        for body in ({'would_recommend': 'yes'}, {'overall_rating': 3},
                     {'overall_rating': 3, 'would_recommend': 'definitely'}, {'overall_rating': 9, 'would_recommend': 'no'}):
            self.assertEqual(self.post('api_submit_feedback', body).status_code, 400, body)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_apis_require_post_and_csrf(self):
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        for name in ('api_submit_rating', 'api_submit_bug_report', 'api_submit_feedback', 'api_submit_assessment'):
            self.assertEqual(self.client.get(reverse(f'virtual_lab:{name}')).status_code, 405, name)
            self.assertEqual(strict.post(reverse(f'virtual_lab:{name}'), data='{}',
                                         content_type='application/json').status_code, 403, name)

    def test_admin_lists_new_models(self):
        from django.contrib.auth.models import User
        User.objects.create_superuser('admin', 'a@example.com', 'pw')
        self.client.login(username='admin', password='pw')
        self.post('api_submit_rating', {'stars': 5})
        self.post('api_submit_bug_report', {'issue_types': ['other'], 'description': 'Typo on Theory'})
        self.post('api_submit_feedback', {'overall_rating': 4, 'would_recommend': 'maybe'})
        self.post('api_submit_assessment', {'test_type': 'pretest', 'levels': ['beginner'], 'answers': {}})
        for model in ('rating', 'bugreport', 'feedback', 'quizattempt'):
            r = self.client.get(reverse(f'admin:virtual_lab_{model}_changelist'))
            self.assertEqual(r.status_code, 200, model)


class TraceTests(TestCase):
    """The educational 'trace' added to API responses must describe, not change, results."""

    def test_upload_trace_with_bom_and_quotes(self):
        data = b'\xef\xbb\xbfName;Marks\r\n"Rao; Aditi";80\r\nB;\r\n'
        r = self.client.post(reverse('virtual_lab:api_upload_csv'),
                             {'csv_file': SimpleUploadedFile('t.csv', data, content_type='text/csv')})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body['headers'], ['Name', 'Marks'])  # unchanged behaviour
        t = body['trace']
        self.assertTrue(t['bytes']['has_bom'])
        self.assertEqual(t['bytes']['encoding_used'], 'utf-8-sig')
        self.assertEqual(t['upload']['class_name'], 'InMemoryUploadedFile')
        self.assertEqual(t['sniff']['delimiter'], ';')
        self.assertEqual(t['tokenize']['rows'][0]['tokens'], ['Rao; Aditi', '80'])
        self.assertIn('Marks', t['tokenize']['rows'][1]['missing'])
        self.assertEqual(len(t['types']['columns']), 2)

    def test_sample_trace(self):
        r = self.client.get(reverse('virtual_lab:api_load_sample'), {'sample_id': 'lab_sensor_log'})
        t = r.json()['trace']
        self.assertEqual(t['sniff']['delimiter'], ';')
        self.assertEqual(t['upload']['source'], 'sample')
        self.assertIsNotNone(t['types']['example'])

    def test_chart_trace_grouped(self):
        self.client.post(reverse('virtual_lab:api_upload_csv'),
                         {'csv_file': SimpleUploadedFile('t.csv', b'Dept,Marks\nCS,80\nCS,90\nIT,70\n')})
        r = self.client.get(reverse('virtual_lab:api_chart_data'), {'type': 'bar', 'x': 'Dept', 'y': 'Marks', 'agg': 'mean'})
        body = r.json()
        self.assertEqual(body['datasets'][0]['data'], [85.0, 70.0])
        tr = body['trace']
        self.assertEqual(tr['mode'], 'grouped')
        self.assertEqual(tr['groups'][0]['values'], [80.0, 90.0])
        self.assertEqual(tr['groups'][0]['result'], 85.0)

    def test_chart_trace_other_modes(self):
        self.client.post(reverse('virtual_lab:api_upload_csv'),
                         {'csv_file': SimpleUploadedFile('t.csv', b'Dept,Marks,Att\nCS,80,9\nCS,90,8\nIT,70,\n')})
        url = reverse('virtual_lab:api_chart_data')
        self.assertEqual(self.client.get(url, {'type': 'histogram', 'x': 'Marks', 'bins': 2}).json()['trace']['mode'], 'histogram')
        self.assertEqual(self.client.get(url, {'type': 'scatter', 'x': 'Att', 'y': 'Marks'}).json()['trace']['mode'], 'scatter')
        self.assertEqual(self.client.get(url, {'type': 'pie', 'x': 'Dept'}).json()['trace']['mode'], 'category_count')
        self.assertEqual(self.client.get(url, {'type': 'line', 'x': 'Dept', 'y': 'Marks', 'agg': 'none'}).json()['trace']['mode'], 'raw')

