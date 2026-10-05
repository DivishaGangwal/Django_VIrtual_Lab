"""
Django Views for Virtual Lab.
Page views for the 6 lab steps + JSON APIs for upload, samples, statistics,
chart data and quiz grading.
"""

import csv
import json

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .forms import CSVUploadForm
from .models import QuizAttempt
from .quiz_bank import grade, public_questions
from .services import (
    ChartBuildError,
    CSVParserService,
    SampleLoaderService,
    build_chart_data,
    describe_dataset,
)

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


# ==========================================
# PAGE VIEWS (Step 1 to Step 6)
# ==========================================

def aim_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'virtual_lab/pages/1_aim.html', {'current_step': 1})


def theory_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'virtual_lab/pages/2_theory.html', {'current_step': 2})


def procedure_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'virtual_lab/pages/3_procedure.html', {'current_step': 3})


@ensure_csrf_cookie
def simulation_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'virtual_lab/pages/4_simulation.html', {
        'current_step': 4,
        'samples': SampleLoaderService.get_sample_list(),
        'upload_form': CSVUploadForm(),
        'has_dataset': _get_dataset(request) is not None,
    })


def observations_view(request: HttpRequest) -> HttpResponse:
    dataset = _get_dataset(request)
    context = {'current_step': 5, 'dataset': None}
    if dataset:
        context.update({
            'dataset': dataset,
            'stats': dataset['stats'],
            'preview_rows': dataset['rows'][:PREVIEW_ROWS],
            'delimiter_label': _delimiter_label(dataset['delimiter']),
        })
    return render(request, 'virtual_lab/pages/5_observations.html', context)


@ensure_csrf_cookie
def quiz_view(request: HttpRequest) -> HttpResponse:
    recent = []
    if request.session.session_key:
        recent = QuizAttempt.objects.filter(session_key=request.session.session_key)[:5]
    return render(request, 'virtual_lab/pages/6_quiz.html', {
        'current_step': 6,
        'questions': public_questions(),
        'recent_attempts': recent,
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
    decoded_text = CSVParserService.decode_file_stream(uploaded_file)
    parse_result = CSVParserService.parse_csv_content(decoded_text, max_rows=settings.LAB_MAX_ROWS)
    if parse_result.get('status') != 'success':
        return JsonResponse(parse_result, status=400)

    dataset = _store_dataset(request, uploaded_file.name, parse_result, source='upload')
    return JsonResponse(_dataset_summary(dataset))


@require_GET
def load_sample_api(request: HttpRequest) -> JsonResponse:
    sample_id = request.GET.get('sample_id', '')
    parse_result = SampleLoaderService.load_sample_dataset(sample_id, max_rows=settings.LAB_MAX_ROWS)
    if parse_result.get('status') != 'success':
        return JsonResponse(parse_result, status=400)

    dataset = _store_dataset(request, parse_result['sample_info']['filename'], parse_result, source='sample')
    payload = _dataset_summary(dataset)
    payload['sample_info'] = parse_result['sample_info']
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
    return JsonResponse(payload)


@require_POST
def submit_quiz_api(request: HttpRequest) -> JsonResponse:
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body.'}, status=400)

    answers = body.get('answers') or {}
    if not isinstance(answers, dict):
        return JsonResponse({'status': 'error', 'message': 'answers must be an object.'}, status=400)

    student_name = str(body.get('student_name', '')).strip()[:100]
    result = grade(answers)

    if not request.session.session_key:
        request.session.save()
    dataset = _get_dataset(request)
    attempt = QuizAttempt.objects.create(
        student_name=student_name,
        session_key=request.session.session_key or '',
        score=result['score'],
        total=result['total'],
        answers={k: v for k, v in answers.items() if isinstance(k, str)},
        dataset_filename=dataset['filename'] if dataset else '',
    )
    result.update({'status': 'success', 'attempt_id': attempt.id, 'percentage': attempt.percentage})
    return JsonResponse(result)
