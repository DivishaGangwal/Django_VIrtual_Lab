"""Makes the 9 lab steps (sidebar + prev/next) and the header rating summary available to every template."""

from django.db.models import Avg, Count

from .models import BugReport, Rating

LAB_STEPS = [
    {'num': 1, 'name': 'Aim', 'url_name': 'virtual_lab:aim'},
    {'num': 2, 'name': 'Theory', 'url_name': 'virtual_lab:theory'},
    {'num': 3, 'name': 'Pretest', 'url_name': 'virtual_lab:pretest'},
    {'num': 4, 'name': 'Procedure', 'url_name': 'virtual_lab:procedure'},
    {'num': 5, 'name': 'Simulation', 'url_name': 'virtual_lab:simulation'},
    {'num': 6, 'name': 'Observations', 'url_name': 'virtual_lab:observations'},
    {'num': 7, 'name': 'Posttest', 'url_name': 'virtual_lab:posttest'},
    {'num': 8, 'name': 'References', 'url_name': 'virtual_lab:references'},
    {'num': 9, 'name': 'Feedback', 'url_name': 'virtual_lab:feedback'},
]
STEP_NUMBERS = {step['url_name'].split(':')[1]: step['num'] for step in LAB_STEPS}


def rating_summary() -> dict:
    """{'average': 4.3 | None, 'count': 12} — None (not 0) when nobody has rated yet."""
    agg = Rating.objects.aggregate(average=Avg('stars'), count=Count('id'))
    average = round(agg['average'], 1) if agg['average'] is not None else None
    return {'average': average, 'count': agg['count']}


def lab_navigation(request):
    return {
        'lab_steps': LAB_STEPS,
        'lab_step_total': len(LAB_STEPS),
        'rating_summary': rating_summary(),
        'bug_issue_types': BugReport.ISSUE_TYPE_CHOICES,
    }
