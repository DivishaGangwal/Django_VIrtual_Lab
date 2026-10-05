"""
10-question MCQ bank for Step 6. Answers stay on the server; the browser only
receives questions + options, and grading happens in views.submit_quiz_api.
"""

QUIZ_QUESTIONS = [
    {
        'id': 'q1',
        'question': 'Where does Django place a file uploaded through a form with enctype="multipart/form-data"?',
        'options': ['request.POST', 'request.FILES', 'request.GET', 'request.body only'],
        'answer': 1,
        'explanation': 'Uploaded files arrive in request.FILES as UploadedFile objects; ordinary fields are in request.POST.',
    },
    {
        'id': 'q2',
        'question': 'Which Python class reads each CSV row as a dictionary keyed by the header row?',
        'options': [
            'csv.reader',
            'csv.writer',
            'csv.DictReader',
            'csv.Sniffer',
        ],
        'answer': 2,
        'explanation': 'csv.DictReader maps every row to {header: value}. csv.reader returns plain lists.',
    },
    {
        'id': 'q3',
        'question': 'Why is the uploaded byte stream wrapped in io.StringIO before parsing?',
        'options': [
            'To compress the file',
            'To save the file to disk',
            'To encrypt the data',
            'To let the csv module read decoded text from memory as if it were a file',
        ],
        'answer': 3,
        'explanation': 'The csv module needs a text file-like object; io.StringIO provides one in memory without touching disk.',
    },
    {
        'id': 'q4',
        'question': 'What does csv.Sniffer help with in this lab?',
        'options': ['Detecting the delimiter (, ; tab |)', 'Removing duplicate rows', 'Drawing charts', 'Validating file size'],
        'answer': 0,
        'explanation': 'Sniffer inspects a sample of the text and guesses the dialect, including the delimiter.',
    },
    {
        'id': 'q5',
        'question': 'A CSV file saved by Excel starts with invisible bytes EF BB BF. Which encoding removes them when decoding?',
        'options': ['ascii', 'utf-16', 'utf-8-sig', 'base64'],
        'answer': 2,
        'explanation': "'utf-8-sig' strips the UTF-8 Byte Order Mark (BOM); plain 'utf-8' would leave \\ufeff in the first header.",
    },
    {
        'id': 'q6',
        'question': 'Which Django feature keeps the parsed dataset available as the student moves from Simulation to Observations?',
        'options': [
            'Sessions (request.session)',
            'Middleware ordering',
            'Static files',
            'URL namespaces',
        ],
        'answer': 0,
        'explanation': 'The parsed dataset is stored in request.session, which persists across requests for the same browser.',
    },
    {
        'id': 'q7',
        'question': 'Which chart is the best fit for showing the relationship between Attendance_Pct and Marks?',
        'options': [
            'Pie chart',
            'Histogram of one column',
            'Scatter plot',
            'Doughnut chart',
        ],
        'answer': 2,
        'explanation': 'A scatter plot places one numeric variable against another, revealing correlation.',
    },
    {
        'id': 'q8',
        'question': 'Why must a fetch() POST to a Django view include the X-CSRFToken header?',
        'options': [
            'To make the request faster',
            'To set the file encoding',
            'Because CsrfViewMiddleware rejects unsafe requests without a valid token',
            'It is optional and has no effect',
        ],
        'answer': 2,
        'explanation': 'CSRF protection blocks POST/PUT/DELETE requests that lack the token, returning 403 Forbidden.',
    },
    {
        'id': 'q9',
        'question': 'For the values [10, 20, 30, 1000], which statistic is least affected by the outlier 1000?',
        'options': [
            'Median',
            'Mean',
            'Sum',
            'Range',
        ],
        'answer': 0,
        'explanation': 'The median (25) depends on the middle values, while mean, sum and range are pulled up by the outlier.',
    },
    {
        'id': 'q10',
        'question': 'Why should file validation happen on the server even if JavaScript already checks the file?',
        'options': [
            'Server checks are faster',
            'JavaScript cannot read file names',
            'Django requires duplicate checks to start',
            'Browser checks can be bypassed, so the server is the real security boundary',
        ],
        'answer': 3,
        'explanation': 'Anyone can send a request directly with curl or devtools; client-side checks are only for user convenience.',
    },
]


def public_questions():
    """Questions without answers/explanations — safe to send to the browser."""
    return [{'id': q['id'], 'question': q['question'], 'options': q['options']} for q in QUIZ_QUESTIONS]


def grade(answers: dict) -> dict:
    results, score = [], 0
    for q in QUIZ_QUESTIONS:
        chosen = answers.get(q['id'])
        try:
            chosen = int(chosen) if chosen is not None else None
        except (TypeError, ValueError):
            chosen = None
        correct = chosen == q['answer']
        score += int(correct)
        results.append({
            'id': q['id'],
            'chosen': chosen,
            'correct_option': q['answer'],
            'is_correct': correct,
            'explanation': q['explanation'],
        })
    return {'score': score, 'total': len(QUIZ_QUESTIONS), 'results': results}
