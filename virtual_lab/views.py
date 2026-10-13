"""
Django Views for Virtual Lab.
Page views for the 9 lab steps + JSON APIs for upload, samples, statistics,
chart data, pretest/posttest grading, ratings, bug reports and feedback.
"""

import csv
import json

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from . import assessment_bank
from .context_processors import STEP_NUMBERS, rating_summary
from .forms import BugReportForm, CSVUploadForm, FeedbackForm, RatingForm
from .models import BugReport, Feedback, QuizAttempt, Rating
from .services import (
    ChartBuildError,
    CSVParserService,
    SampleLoaderService,
    build_chart_data,
    build_chart_trace,
    build_ingest_trace,
    describe_dataset,
)
from .services.sample_loader import AVAILABLE_SAMPLES, DATA_SAMPLES_DIR

SESSION_KEY = 'active_dataset'
PREVIEW_ROWS = 10


# ==========================================
# Helpers
# ==========================================

def _store_dataset(request: HttpRequest, filename: str, parse_result: dict, source: str) -> dict:
    """Computes statistics once and caches the dataset in the session."""
    stats = describe_dataset(parse_result['headers'], parse_result['rows'])
    dataset = {
        'filename': filename,
        'source': source,  # 'upload' | 'sample'
        'headers': parse_result['headers'],
        'rows': parse_result['rows'],
        'row_count': parse_result['row_count'],
        'col_count': parse_result['col_count'],
        'delimiter': parse_result['delimiter'],
        'missing_values_count': parse_result['missing_values_count'],
        'ragged_rows_count': parse_result.get('ragged_rows_count', 0),
        'truncated': parse_result.get('truncated', False),
        'stats': stats,
    }
    request.session[SESSION_KEY] = dataset
    return dataset


def _dataset_summary(dataset: dict) -> dict:
    """Everything the browser needs, minus the full row list."""
    return {
        'status': 'success',
        'filename': dataset['filename'],
        'source': dataset.get('source', 'upload'),
        'headers': dataset['headers'],
        'row_count': dataset['row_count'],
        'col_count': dataset['col_count'],
        'delimiter': dataset['delimiter'],
        'missing_values_count': dataset['missing_values_count'],
        'ragged_rows_count': dataset.get('ragged_rows_count', 0),
        'truncated': dataset.get('truncated', False),
        'preview_rows': dataset['rows'][:PREVIEW_ROWS],
        'stats': dataset['stats'],
    }


def _get_dataset(request: HttpRequest):
    return request.session.get(SESSION_KEY)


def _delimiter_label(delim: str) -> str:
    return {',': 'Comma (,)', ';': 'Semicolon (;)', '\t': 'Tab (\\t)', '|': 'Pipe (|)'}.get(delim, repr(delim))


def _session_key(request: HttpRequest) -> str:
    """The session key, creating the session first if this browser has none yet."""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key or ''


def _json_body(request: HttpRequest):
    """Parsed JSON object, or None if the body is not a JSON object."""
    try:
        body = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return body if isinstance(body, dict) else None


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({'status': 'error', 'message': message}, status=status)


def _form_errors(form) -> str:
    return ' '.join(f'{field.replace("_", " ").capitalize()}: {err}' if field != '__all__' else str(err)
                    for field, errs in form.errors.items() for err in errs)


# ==========================================
# PAGE VIEWS (Step 1 to Step 9)
# ==========================================

def aim_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'virtual_lab/pages/1_aim.html', {'current_step': STEP_NUMBERS['aim']})


def theory_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'virtual_lab/pages/2_theory.html', {'current_step': STEP_NUMBERS['theory']})


def _assessment_view(request: HttpRequest, test_type: str) -> HttpResponse:
    recent = []
    if request.session.session_key:
        recent = QuizAttempt.objects.filter(session_key=request.session.session_key, test_type=test_type)[:5]
    return render(request, 'virtual_lab/pages/assessment.html', {
        'current_step': STEP_NUMBERS[test_type],
        'test_type': test_type,
        'test_title': 'Pretest' if test_type == assessment_bank.PRETEST else 'Posttest',
        'levels': assessment_bank.public_questions_by_level(test_type),
        'default_levels': assessment_bank.DEFAULT_LEVELS,
        'recent_attempts': recent,
    })


@ensure_csrf_cookie
def pretest_view(request: HttpRequest) -> HttpResponse:
    return _assessment_view(request, assessment_bank.PRETEST)


def procedure_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'virtual_lab/pages/4_procedure.html', {'current_step': STEP_NUMBERS['procedure']})


@ensure_csrf_cookie
def simulation_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'virtual_lab/pages/5_simulation.html', {
        'current_step': STEP_NUMBERS['simulation'],
        'samples': SampleLoaderService.get_sample_list(),
        'upload_form': CSVUploadForm(),
        'has_dataset': _get_dataset(request) is not None,
    })


def observations_view(request: HttpRequest) -> HttpResponse:
    dataset = _get_dataset(request)
    context = {'current_step': STEP_NUMBERS['observations'], 'dataset': None}
    if dataset:
        context.update({
            'dataset': dataset,
            'stats': dataset['stats'],
            'preview_rows': dataset['rows'][:PREVIEW_ROWS],
            'delimiter_label': _delimiter_label(dataset['delimiter']),
        })
    return render(request, 'virtual_lab/pages/6_observations.html', context)


@ensure_csrf_cookie
def posttest_view(request: HttpRequest) -> HttpResponse:
    return _assessment_view(request, assessment_bank.POSTTEST)


def quiz_redirect_view(request: HttpRequest) -> HttpResponse:
    """The old single Quiz step became the Posttest; keep old links working."""
    return redirect('virtual_lab:posttest', permanent=True)


def references_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'virtual_lab/pages/8_references.html', {'current_step': STEP_NUMBERS['references']})


@ensure_csrf_cookie
def feedback_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'virtual_lab/pages/9_feedback.html', {
        'current_step': STEP_NUMBERS['feedback'],
        'recommend_choices': Feedback.RECOMMEND_CHOICES,
    })


@require_GET
def export_observations_csv(request: HttpRequest) -> HttpResponse:
    """Downloads the per-column statistics table as a CSV (written with csv.writer)."""
    dataset = _get_dataset(request)
    if not dataset:
        return HttpResponse('No dataset loaded. Load one on the Simulation page first.', status=404,
                            content_type='text/plain')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="observation_statistics.csv"'
    fields = ['name', 'type', 'count', 'missing', 'unique', 'mean', 'median', 'min', 'max', 'std_dev', 'mode']
    writer = csv.DictWriter(response, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for col in dataset['stats']['columns']:
        writer.writerow(col)
    return response


# ==========================================
# JSON API ENDPOINTS
# ==========================================

@require_POST
def upload_csv_api(request: HttpRequest) -> JsonResponse:
    """
    1. Validate the form (extension, size, not binary)
    2. Decode bytes -> text
    3. Parse with the csv module
    4. Compute statistics and cache everything in the session
    """
    form = CSVUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = [str(err) for err_list in form.errors.values() for err in err_list]
        return JsonResponse({'status': 'error', 'message': ' '.join(errors)}, status=400)

    uploaded_file = form.cleaned_data['csv_file']
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()  # kept only to explain the byte-level stage
    uploaded_file.seek(0)
    decoded_text = CSVParserService.decode_file_stream(uploaded_file)
    parse_result = CSVParserService.parse_csv_content(decoded_text, max_rows=settings.LAB_MAX_ROWS)
    if parse_result.get('status') != 'success':
        return JsonResponse(parse_result, status=400)

    dataset = _store_dataset(request, uploaded_file.name, parse_result, source='upload')
    payload = _dataset_summary(dataset)
    payload['trace'] = build_ingest_trace(
        raw_bytes, uploaded_file.name, getattr(uploaded_file, 'content_type', '') or 'text/csv',
        'upload', decoded_text, parse_result, dataset['stats'], request.session.session_key)
    return JsonResponse(payload)


@require_GET
def load_sample_api(request: HttpRequest) -> JsonResponse:
    sample_id = request.GET.get('sample_id', '')
    parse_result = SampleLoaderService.load_sample_dataset(sample_id, max_rows=settings.LAB_MAX_ROWS)
    if parse_result.get('status') != 'success':
        return JsonResponse(parse_result, status=400)

    dataset = _store_dataset(request, parse_result['sample_info']['filename'], parse_result, source='sample')
    payload = _dataset_summary(dataset)
    payload['sample_info'] = parse_result['sample_info']
    raw_bytes = (DATA_SAMPLES_DIR / AVAILABLE_SAMPLES[sample_id]['filename']).read_bytes()
    payload['trace'] = build_ingest_trace(
        raw_bytes, parse_result['sample_info']['filename'], 'text/csv', 'sample',
        CSVParserService.decode_file_stream(raw_bytes), parse_result, dataset['stats'],
        request.session.session_key)
    return JsonResponse(payload)


@require_GET
def dataset_api(request: HttpRequest) -> JsonResponse:
    """Returns the dataset currently stored in the session (used to restore the page)."""
    dataset = _get_dataset(request)
    if not dataset:
        return JsonResponse({'status': 'empty', 'message': 'No dataset loaded yet.'}, status=404)
    return JsonResponse(_dataset_summary(dataset))


@require_POST
def reset_dataset_api(request: HttpRequest) -> JsonResponse:
    request.session.pop(SESSION_KEY, None)
    return JsonResponse({'status': 'success'})


@require_GET
def chart_data_api(request: HttpRequest) -> JsonResponse:
    """
    /api/chart-data/?type=bar&x=Department&y=Marks&agg=mean
    Multiple Y columns: &y=Marks&y=Attendance_Pct
    """
    dataset = _get_dataset(request)
    if not dataset:
        return JsonResponse({'status': 'error', 'message': 'Load a dataset first.'}, status=400)

    chart_type = request.GET.get('type', 'bar')
    x = request.GET.get('x', '')
    y_columns = [y for y in request.GET.getlist('y') if y]
    agg = request.GET.get('agg', 'none')
    try:
        bins = int(request.GET.get('bins', 8))
    except ValueError:
        bins = 8

    if not x:
        return JsonResponse({'status': 'error', 'message': 'Choose an X-axis column.'}, status=400)

    try:
        payload = build_chart_data(dataset['headers'], dataset['rows'], chart_type, x, y_columns, agg, bins)
    except ChartBuildError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    payload['status'] = 'success'
    payload['trace'] = build_chart_trace(dataset['rows'], payload, chart_type, x, y_columns, agg, bins)
    return JsonResponse(payload)


@require_POST
def submit_assessment_api(request: HttpRequest) -> JsonResponse:
    """
    Body: {"test_type": "pretest"|"posttest", "levels": ["beginner", ...],
           "answers": {"pre_b1": 0, ...}, "student_name": "..."}
    Only the questions of the chosen levels are graded.
    """
    body = _json_body(request)
    if body is None:
        return _json_error('Invalid JSON body.')

    test_type = body.get('test_type')
    if test_type not in assessment_bank.BANKS:
        return _json_error('test_type must be "pretest" or "posttest".')

    levels = assessment_bank.clean_levels(body.get('levels'))
    if not levels:
        return _json_error('Choose at least one difficulty level (Beginner, Intermediate or Advanced).')

    answers = body.get('answers') or {}
    if not isinstance(answers, dict):
        return _json_error('answers must be an object.')

    student_name = str(body.get('student_name', '')).strip()[:100]
    result = assessment_bank.grade(test_type, levels, answers)

    dataset = _get_dataset(request)
    graded_ids = {r['id'] for r in result['results']}
    attempt = QuizAttempt.objects.create(
        student_name=student_name,
        session_key=_session_key(request),
        test_type=test_type,
        difficulty_levels=levels,
        score=result['score'],
        total=result['total'],
        answers={k: v for k, v in answers.items() if k in graded_ids},
        dataset_filename=dataset['filename'] if dataset else '',
    )
    result.update({'status': 'success', 'attempt_id': attempt.id, 'percentage': attempt.percentage,
                   'test_type': test_type, 'levels': levels})
    return JsonResponse(result)


@require_POST
def submit_rating_api(request: HttpRequest) -> JsonResponse:
    """Body: {"stars": 1-5, "comment": "..."}. One rating per session: re-rating updates it."""
    body = _json_body(request)
    if body is None:
        return _json_error('Invalid JSON body.')
    form = RatingForm(data=body)
    if not form.is_valid():
        return _json_error(_form_errors(form))

    rating, created = Rating.objects.update_or_create(
        session_key=_session_key(request),
        defaults={'stars': form.cleaned_data['stars'], 'comment': form.cleaned_data['comment'].strip()},
    )
    return JsonResponse({'status': 'success', 'created': created, 'stars': rating.stars,
                         'summary': rating_summary()})


@require_POST
def submit_bug_report_api(request: HttpRequest) -> JsonResponse:
    """Body: {"issue_types": ["ui_problem", ...], "description": "...", "page_name": "Simulation"}"""
    body = _json_body(request)
    if body is None:
        return _json_error('Invalid JSON body.')
    form = BugReportForm(data=body)
    if not form.is_valid():
        return _json_error(_form_errors(form))

    report = BugReport.objects.create(
        issue_types=form.cleaned_data['issue_types'],
        description=form.cleaned_data['description'],
        page_name=form.cleaned_data['page_name'].strip(),
        session_key=_session_key(request),
    )
    return JsonResponse({'status': 'success', 'report_id': report.id})


@require_POST
def submit_feedback_api(request: HttpRequest) -> JsonResponse:
    """Body: {"name", "overall_rating": 1-5, "most_useful", "to_improve", "would_recommend": "yes"|"maybe"|"no"}"""
    body = _json_body(request)
    if body is None:
        return _json_error('Invalid JSON body.')
    form = FeedbackForm(data=body)
    if not form.is_valid():
        return _json_error(_form_errors(form))

    data = form.cleaned_data
    feedback = Feedback.objects.create(
        name=data['name'].strip(),
        overall_rating=data['overall_rating'],
        most_useful=data['most_useful'].strip(),
        to_improve=data['to_improve'].strip(),
        would_recommend=data['would_recommend'],
        session_key=_session_key(request),
    )
    return JsonResponse({'status': 'success', 'feedback_id': feedback.id})
