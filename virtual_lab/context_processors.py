"""Makes the 6 lab steps available to every template (progress ribbon + prev/next)."""

LAB_STEPS = [
    {'num': 1, 'name': 'Aim', 'url_name': 'virtual_lab:aim'},
    {'num': 2, 'name': 'Theory', 'url_name': 'virtual_lab:theory'},
    {'num': 3, 'name': 'Procedure', 'url_name': 'virtual_lab:procedure'},
    {'num': 4, 'name': 'Simulation', 'url_name': 'virtual_lab:simulation'},
    {'num': 5, 'name': 'Observations', 'url_name': 'virtual_lab:observations'},
    {'num': 6, 'name': 'Quiz', 'url_name': 'virtual_lab:quiz'},
]


def lab_navigation(request):
    return {'lab_steps': LAB_STEPS}
