I'm continuing a Django project called "lab_csv_visualizer" (app: "virtual_lab"). It's a 6-step Computer Engineering virtual lab: Aim → Theory → Procedure → Simulation → Observations → Quiz. Students upload a CSV (or load a built-in sample). Django parses it with Python's built-in csv module (no pandas), computes statistics with the statistics module, and Chart.js (from the cdnjs CDN) draws charts from JSON that Django prepares.

The project in this folder is complete and was tested on another machine (29 automated tests passing, and every page checked in a browser). I've just moved it to this laptop. README.md describes the structure and the API.

Please do the following, in order, and tell me what happened at each step:

1. Check my Python version. The project needs Python 3.10+ (3.12+ recommended because the latest Django needs it). If it's too old, tell me how to install a newer Python on this computer before going further. Don't do it silently.
2. Create a virtual environment in `.venv`, activate it, and run `pip install -r requirements.txt`.
3. Run `python manage.py migrate` and then `python manage.py test`. All tests should pass. If any fail, show me the failure and explain the cause before changing anything.
4. Start the server with `python manage.py runserver` and tell me the URL to open. Give me a short manual checklist to verify it in my browser:
   - all 6 pages open, and the progress bar highlights the current step;
   - on Simulation, "Load Sample" works for all 4 samples, the preview table, type tags and statistics appear, and bar/line/pie/scatter/histogram charts draw;
   - uploading my own .csv works, and uploading a .txt, an empty file or a renamed .xlsx is rejected with a clear message;
   - Observations shows the report, "Print / Save as PDF" works, and the statistics CSV downloads;
   - the Quiz grades my answers and the attempt appears in /admin/ (help me run `python manage.py createsuperuser`).
5. Explain the project to me file by file at a beginner-friendly level, so that I can present it in my viva/lab evaluation. Cover the request flow for an upload, from the browser through views.py, forms.py, csv_parser.py, stats_engine.py and the session, back to the JSON response and the chart.

Rules:
- Don't rewrite or "improve" working code unless I ask. If you spot a real bug, explain it and ask before fixing it.
- Don't assume anything. If something is unclear or a decision is mine to make, ask me first.
- Keep the zero-pandas design: only the Python standard library on the server, and Django as the only pip dependency.
