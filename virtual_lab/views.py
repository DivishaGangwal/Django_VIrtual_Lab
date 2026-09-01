"""
Django Views for Virtual Lab.
Provides full-stack controllers for educational pages and CSV upload APIs.
"""

from django.shortcuts import render
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

from .forms import CSVUploadForm
from .services.csv_parser import CSVParserService
from .services.sample_loader import SampleLoaderService


# ==========================================
# PAGE VIEWS (Step 1 to Step 6)
# ==========================================

@ensure_csrf_cookie
def aim_view(request: HttpRequest) -> HttpResponse:
    """Page 1: AIM & Learning Objectives."""
    return render(request, 'virtual_lab/pages/1_aim.html', {
        'current_step': 1,
    })


def theory_view(request: HttpRequest) -> HttpResponse:
    """Page 2: Theoretical Foundations & Architecture."""
    return render(request, 'virtual_lab/pages/2_theory.html', {
        'current_step': 2,
    })


def procedure_view(request: HttpRequest) -> HttpResponse:
    """Page 3: Vertical Laboratory Timeline Procedure."""
    return render(request, 'virtual_lab/pages/3_procedure.html', {
        'current_step': 3,
    })


@ensure_csrf_cookie
def simulation_view(request: HttpRequest) -> HttpResponse:
    """Page 4: Main Interactive Simulation Workbench."""
    samples = SampleLoaderService.get_sample_list()
    return render(request, 'virtual_lab/pages/4_simulation.html', {
        'current_step': 4,
        'samples': samples,
        'upload_form': CSVUploadForm(),
    })


def observations_view(request: HttpRequest) -> HttpResponse:
    """Page 5: Auto-Generated Observation Sheet & Printable Report."""
    return render(request, 'virtual_lab/pages/5_observations.html', {
        'current_step': 5,
    })


def quiz_view(request: HttpRequest) -> HttpResponse:
    """Page 6: 10-Question MCQ Assessment & Practical Exercises."""
    return render(request, 'virtual_lab/pages/6_quiz.html', {
        'current_step': 6,
    })


# ==========================================
# API ENDPOINTS (Developer 1 Ingestion Pipeline)
# ==========================================

@require_http_methods(["POST"])
def upload_csv_api(request: HttpRequest) -> JsonResponse:
    """
    API endpoint handling CSV file upload.
    Validates form, decodes byte stream with io.StringIO,
    parses rows with csv.DictReader, and stores dataset in session.
    """
    form = CSVUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = [str(err) for err_list in form.errors.values() for err in err_list]
        return JsonResponse({
            'status': 'error',
            'message': ' '.join(errors)
        }, status=400)

    uploaded_file = form.cleaned_data['csv_file']

    try:
        # Step 1: Decode raw byte stream
        decoded_text = CSVParserService.decode_file_stream(uploaded_file)

        # Step 2: Parse CSV using pure-Python csv module
        parse_result = CSVParserService.parse_csv_content(decoded_text)

        if parse_result.get('status') != 'success':
            return JsonResponse(parse_result, status=400)

        # Step 3: Cache active dataset in session for Developer 2 & 3
        request.session['active_dataset'] = {
            'filename': uploaded_file.name,
            'headers': parse_result['headers'],
            'rows': parse_result['rows'],
            'row_count': parse_result['row_count'],
            'col_count': parse_result['col_count'],
            'missing_values_count': parse_result['missing_values_count'],
        }

        # Response payload
        return JsonResponse({
            'status': 'success',
            'filename': uploaded_file.name,
            'headers': parse_result['headers'],
            'row_count': parse_result['row_count'],
            'col_count': parse_result['col_count'],
            'delimiter': parse_result['delimiter'],
            'preview_rows': parse_result['preview_rows'],
            'missing_values_count': parse_result['missing_values_count'],
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Server stream processing failure: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def load_sample_api(request: HttpRequest) -> JsonResponse:
    """
    API endpoint to load one of the built-in educational sample CSV files.
    """
    sample_id = request.GET.get('sample_id', 'student_marks')
    parse_result = SampleLoaderService.load_sample_dataset(sample_id)

    if parse_result.get('status') == 'success':
        # Store in session
        request.session['active_dataset'] = {
            'filename': parse_result['sample_info']['filename'],
            'headers': parse_result['headers'],
            'rows': parse_result['rows'],
            'row_count': parse_result['row_count'],
            'col_count': parse_result['col_count'],
            'missing_values_count': parse_result['missing_values_count'],
        }

        return JsonResponse({
            'status': 'success',
            'filename': parse_result['sample_info']['filename'],
            'sample_info': parse_result['sample_info'],
            'headers': parse_result['headers'],
            'row_count': parse_result['row_count'],
            'col_count': parse_result['col_count'],
            'delimiter': parse_result['delimiter'],
            'preview_rows': parse_result['preview_rows'],
            'missing_values_count': parse_result['missing_values_count'],
        })

    return JsonResponse(parse_result, status=400)
