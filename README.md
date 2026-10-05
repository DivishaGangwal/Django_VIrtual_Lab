# Virtual Lab — Reading & Visualizing CSV Data in Django

A 6-step Computer Engineering virtual lab (**Aim → Theory → Procedure → Simulation → Observations → Quiz**).
Students upload a CSV (or load a sample). Django parses it with Python's built-in `csv` module and computes
statistics with the `statistics` module (no pandas). Chart.js then draws charts from JSON prepared by the server.

## Quick start

Requires **Python 3.10+** (3.12+ recommended; Django 6 needs 3.12).

```bash
cd Django_Virtual_Lab
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test              # 40 tests, should all pass
python manage.py runserver
```

Open http://127.0.0.1:8000/. To see saved quiz attempts, run `python manage.py createsuperuser` and open `/admin/`.

> Chart.js and the web fonts load from the internet (cdnjs / Google Fonts). Everything else works offline.

## Project layout

```
lab_csv_visualizer/        settings, root urls
virtual_lab/
  services/
    csv_parser.py          decode bytes → text, sniff delimiter, parse rows, count missing values
    stats_engine.py        type inference (int/float/date/str) + descriptive statistics
    chart_builder.py       grouping/aggregation → {labels, datasets} for Chart.js
    sample_loader.py       built-in sample datasets
  data_samples/            4 sample CSVs (one with missing values + ; delimiter)
  models.py                QuizAttempt (saved quiz scores)
  quiz_bank.py             10 MCQs, graded on the server
  context_processors.py    the 6 lab steps (progress ribbon, prev/next)
  views.py / urls.py       6 pages + JSON APIs
  forms.py                 upload validation (extension, size, empty, binary/xlsx)
  templates/virtual_lab/   base.html + pages/1_aim … 6_quiz
  static/virtual_lab/
    css/                   design_system, lab_layout, simulation, pages
    js/                    lab_utils, csv_uploader, pipeline_visualizer,
                           dataset_explorer, chart_studio, quiz, lab_navigator
  tests/                   test_lab.py (parser, stats, charts, pages, APIs, quiz) + test_csv_parser.py
```

## API

| Method | URL | Purpose |
|---|---|---|
| POST | `/api/upload-csv/` | multipart `csv_file` → parsed summary + stats (stored in session) |
| GET | `/api/load-sample/?sample_id=` | load a built-in sample |
| GET | `/api/dataset/` | current session dataset summary |
| POST | `/api/dataset/reset/` | clear the dataset |
| GET | `/api/chart-data/?type=&x=&y=&agg=&bins=` | chart payload (`type`: bar/line/pie/doughnut/scatter/histogram; `agg`: none/sum/mean/count/min/max) |
| POST | `/api/quiz/submit/` | JSON `{student_name, answers:{q1:0,…}}` → graded result, saved to DB |
| GET | `/observations/export.csv` | per-column statistics as CSV |

## Production notes

Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0` and `DJANGO_ALLOWED_HOSTS`, then run `python manage.py collectstatic`.
