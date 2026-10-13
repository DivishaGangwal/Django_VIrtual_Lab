"""
Pretest (Step 3) and Posttest (Step 7) question banks.

Every question is tagged with a difficulty level. Answers and explanations stay
on the server: the browser only receives questions + options, and grading
happens in views.submit_assessment_api for the levels the student selected.
`answer` is the 0-based index of the correct option (A=0 … D=3).
"""

BEGINNER, INTERMEDIATE, ADVANCED = 'beginner', 'intermediate', 'advanced'
LEVELS = [(BEGINNER, 'Beginner'), (INTERMEDIATE, 'Intermediate'), (ADVANCED, 'Advanced')]
LEVEL_KEYS = [key for key, _ in LEVELS]
DEFAULT_LEVELS = [BEGINNER]

PRETEST, POSTTEST = 'pretest', 'posttest'


def _q(qid, level, question, options, answer, explanation):
    return {'id': qid, 'level': level, 'question': question, 'options': options,
            'answer': answer, 'explanation': explanation}


# Basics of CSV, Python and Django needed before starting the experiment.
PRETEST_QUESTIONS = [
    # ---- Beginner ----
    _q('pre_b1', BEGINNER, 'What does CSV stand for?',
       ['Comma-Separated Values', 'Common Spreadsheet Values', 'Computed Statistical Variables', 'Character-Separated Vectors'],
       0, 'CSV means Comma-Separated Values: plain text where each line is a record and fields are separated by a delimiter.'),
    _q('pre_b2', BEGINNER, 'In a typical CSV file, what does the first line usually contain?',
       ['The total number of rows', 'The column names (the header row)', 'The text encoding of the file', 'Only the delimiter character'],
       1, 'The first line is normally a header row that names each column; the data records follow it.'),
    _q('pre_b3', BEGINNER, 'Which Python type stores key → value pairs such as {"Name": "Asha", "Marks": 88}?',
       ['list', 'tuple', 'dict', 'set'],
       2, 'A dict maps keys to values. Lists and tuples are ordered sequences; a set holds unique values without keys.'),
    _q('pre_b4', BEGINNER, 'Which module in the Python standard library reads and writes CSV files?',
       ['json', 'os', 'math', 'csv'],
       3, 'The built-in csv module provides csv.reader, csv.writer, csv.DictReader, csv.DictWriter and csv.Sniffer.'),
    _q('pre_b5', BEGINNER, 'In a Django project, which file normally maps URL paths to view functions?',
       ['urls.py', 'models.py', 'admin.py', 'apps.py'],
       0, 'urls.py holds urlpatterns, a list of path() entries that connect a URL to a view.'),

    # ---- Intermediate ----
    _q('pre_i1', INTERMEDIATE, 'What does csv.reader produce for each row of a CSV file?',
       ['A dict keyed by the header names', 'A list of strings', 'A tuple of numbers', 'One single string for the whole line'],
       1, 'csv.reader yields each row as a list of strings. csv.DictReader is the one that yields dicts. No type conversion happens.'),
    _q('pre_i2', INTERMEDIATE, 'What happens when Python runs int("88.5")?',
       ['It returns 88', 'It returns 89', 'It raises ValueError', 'It returns 88.5'],
       2, 'int() only parses whole-number strings, so "88.5" raises ValueError. Use float("88.5") (and int(float(...)) if you need to truncate).'),
    _q('pre_i3', INTERMEDIATE, 'A Django view function always receives which object as its first argument?',
       ['The template', 'The URL pattern', 'The database connection', 'An HttpRequest object'],
       3, 'Django calls every view with an HttpRequest (usually named request), which carries GET, POST, FILES, session and more.'),
    _q('pre_i4', INTERMEDIATE, 'Which HTTP method should a form use to upload a file to a Django view?',
       ['POST', 'GET', 'HEAD', 'OPTIONS'],
       0, 'File uploads must be sent with POST and multipart/form-data; GET only sends a query string in the URL.'),
    _q('pre_i5', INTERMEDIATE, 'What is the median of [3, 9, 1, 7]?',
       ['4', '5', '7', '5.5'],
       1, 'Sorted: [1, 3, 7, 9]. With an even count the median is the mean of the two middle values: (3 + 7) / 2 = 5.'),

    # ---- Advanced ----
    _q('pre_a1', ADVANCED, 'The Python docs recommend opening a file for the csv module with which open() argument?',
       ["mode='rb'", "newline=''", "encoding='ascii'", 'buffering=0'],
       1, "newline='' lets the csv module handle line endings itself, so newlines inside quoted fields are read correctly."),
    _q('pre_a2', ADVANCED, 'Why is the value "Rao, Aditi" wrapped in double quotes inside a CSV file?',
       ['Quotes make the text bold', 'Quotes mark the value as a number', 'Because the value contains the delimiter (a comma)', 'Every text value must be quoted'],
       2, 'Fields that contain the delimiter, a quote or a newline are quoted so the comma is read as part of the value, not as a separator.'),
    _q('pre_a3', ADVANCED, 'Where must {% csrf_token %} go so that a normal POST form passes Django\'s CSRF check?',
       ['In the <head> of base.html only', 'In settings.py', 'In urls.py', 'Inside the <form> element in the template'],
       3, 'The tag renders a hidden csrfmiddlewaretoken input, so it must be inside the form that is submitted. (JavaScript requests send the X-CSRFToken header instead.)'),
    _q('pre_a4', ADVANCED, 'What does statistics.mean([]) do?',
       ['Raises statistics.StatisticsError', 'Returns 0', 'Returns None', "Returns float('nan')"],
       0, 'mean() needs at least one data point; an empty list raises StatisticsError. Code should check for empty columns first.'),
    _q('pre_a5', ADVANCED, "Which expression turns the bytes b'caf\\xc3\\xa9' into the text 'café'?",
       ["b'caf\\xc3\\xa9'.encode('utf-8')", "b'caf\\xc3\\xa9'.decode('utf-8')", "str(b'caf\\xc3\\xa9')", "bytes.join('utf-8')"],
       1, "bytes.decode() converts bytes to str. Bytes have no encode() method, and str(bytes) just gives the literal text \"b'caf\\xc3\\xa9'\"."),
]

# Deeper questions about this experiment (upload → decode → parse → stats → chart).
POSTTEST_QUESTIONS = [
    # ---- Beginner ----
    _q('post_b1', BEGINNER, 'In this lab, where does Django place the uploaded CSV file?',
       ['request.FILES', 'request.POST', 'request.GET', 'request.session'],
       0, 'Uploaded files arrive in request.FILES as UploadedFile objects; ordinary form fields are in request.POST.'),
    _q('post_b2', BEGINNER, 'Which chart best shows the relationship between Attendance_Pct and Marks?',
       ['Pie chart', 'Scatter plot', 'Doughnut chart', 'Histogram of one column'],
       1, 'A scatter plot places one numeric variable against another, so a trend (correlation) becomes visible.'),
    _q('post_b3', BEGINNER, 'What keeps your parsed dataset available when you move from Simulation to Observations?',
       ['Static files', 'URL namespaces', 'Django sessions (request.session)', "The browser's file picker"],
       2, 'The parsed dataset is stored in request.session, which persists across requests from the same browser.'),
    _q('post_b4', BEGINNER, 'Which chart shows the distribution of one numeric column by counting values in equal ranges?',
       ['Line chart', 'Pie chart', 'Scatter plot', 'Histogram'],
       3, 'A histogram splits the numeric range into bins and counts how many values fall into each bin.'),
    _q('post_b5', BEGINNER, 'In this lab, which part does the grouping and aggregation (e.g. mean Marks per Department)?',
       ['Django (Python on the server)', 'Chart.js in the browser', 'An SQL GROUP BY in SQLite', 'The CSV file itself'],
       0, 'build_chart_data() in Python groups and aggregates the rows; Chart.js only draws the {labels, datasets} JSON it receives.'),

    # ---- Intermediate ----
    _q('post_i1', INTERMEDIATE, 'A CSV saved by Excel starts with the bytes EF BB BF. Which codec removes them while decoding?',
       ['ascii', 'utf-8-sig', 'utf-16', 'latin-1'],
       1, "'utf-8-sig' strips the UTF-8 Byte Order Mark. Plain 'utf-8' keeps it as \\ufeff at the start of the first header."),
    _q('post_i2', INTERMEDIATE, 'What does csv.Sniffer().sniff(sample).delimiter tell the parser?',
       ['How many rows the file has', 'The text encoding of the file', 'The character that separates the fields', 'Whether the first row is a header'],
       2, 'sniff() guesses the dialect, including the delimiter (, ; tab |). Header detection is a separate method, has_header().'),
    _q('post_i3', INTERMEDIATE, 'Why is the decoded text wrapped in io.StringIO before it is given to csv.reader?',
       ['To compress the text', 'To save the text to disk', 'To encrypt the data', 'To give the csv module a file-like object in memory'],
       3, 'csv.reader needs an iterable of lines such as a text file; io.StringIO provides one in memory without writing to disk.'),
    _q('post_i4', INTERMEDIATE, 'For the values [10, 20, 30, 1000], which statistic is least affected by the outlier 1000?',
       ['Median', 'Mean', 'Sum', 'Range'],
       0, 'The median (25) depends only on the middle values; mean, sum and range are all pulled up by 1000.'),
    _q('post_i5', INTERMEDIATE, 'A fetch() POST from the Simulation page to a Django view returns 403 Forbidden. What is most likely missing?',
       ['A Content-Length header', 'The CSRF token (X-CSRFToken header)', 'A trailing ? in the URL', 'An Accept: image/png header'],
       1, 'CsrfViewMiddleware rejects unsafe requests (POST, PUT, DELETE) without a valid CSRF token with 403 Forbidden.'),

    # ---- Advanced ----
    _q('post_a1', ADVANCED, 'A column contains "12", "15", "NA", "18". How does this lab classify it?',
       ['As text, because "NA" is not a number', 'As a date column', 'The upload is rejected', 'As int: "NA" is counted as a missing value and every other value is a whole number'],
       3, 'Tokens such as "", NA, null, NaN and - are treated as missing. Type inference only looks at the non-missing values, which are all integers.'),
    _q('post_a2', ADVANCED, "Why is line.split(',') the wrong way to parse a CSV line?",
       ['It is slower than csv.reader', 'It cannot handle numbers', 'It also splits inside quoted fields such as "Rao, Aditi"', 'It deletes the header row'],
       2, 'str.split() knows nothing about quoting, so a quoted comma breaks one field into two. csv.reader follows the quoting rules.'),
    _q('post_a3', ADVANCED, 'This lab uses the database session backend. Where is the parsed dataset physically stored?',
       ['In the django_session table; the browser cookie only holds the session key', 'Inside the browser cookie', "In the browser's localStorage", 'In a CSV file under media/'],
       0, "With SESSION_ENGINE = 'django.contrib.sessions.backends.db' the session data is saved server-side; the sessionid cookie just identifies it."),
    _q('post_a4', ADVANCED, 'The lab reports statistics.stdev(). How does it differ from statistics.pstdev()?',
       ['stdev divides by n and pstdev by n − 1', 'stdev is the sample standard deviation (divides by n − 1); pstdev is the population one (divides by n)', 'stdev ignores outliers', 'There is no difference'],
       1, 'stdev() estimates the spread from a sample using n − 1 (Bessel\'s correction); pstdev() treats the data as the whole population and uses n.'),
    _q('post_a5', ADVANCED, 'On an HTML canvas y grows downward. On a normal Chart.js y-axis, a LARGER data value is drawn at…',
       ['the same y-pixel as a smaller value', 'a negative y-pixel', 'a smaller y-pixel (higher on the screen)', 'a larger y-pixel (lower on the screen)'],
       2, 'The scale maps the axis maximum to the top of the plot area (small y) and the minimum to the bottom (large y), so bigger values sit higher.'),
]

BANKS = {PRETEST: PRETEST_QUESTIONS, POSTTEST: POSTTEST_QUESTIONS}


def clean_levels(levels) -> list:
    """Valid, de-duplicated levels in canonical order. Empty if none are valid."""
    if not isinstance(levels, (list, tuple)):
        return []
    chosen = {str(level) for level in levels}
    return [key for key in LEVEL_KEYS if key in chosen]


def public_questions_by_level(test_type: str) -> list:
    """[{key, label, questions:[...]}] without answers/explanations — safe to send to the browser."""
    bank = BANKS[test_type]
    return [{
        'key': key,
        'label': label,
        'questions': [{'id': q['id'], 'question': q['question'], 'options': q['options']}
                      for q in bank if q['level'] == key],
    } for key, label in LEVELS]


def grade(test_type: str, levels: list, answers: dict) -> dict:
    """Grades only the questions of the selected levels. Unanswered counts as incorrect."""
    results, score = [], 0
    questions = [q for q in BANKS[test_type] if q['level'] in levels]
    for q in questions:
        chosen = answers.get(q['id'])
        try:
            chosen = int(chosen) if chosen is not None else None
        except (TypeError, ValueError):
            chosen = None
        correct = chosen == q['answer']
        score += int(correct)
        results.append({
            'id': q['id'],
            'level': q['level'],
            'chosen': chosen,
            'correct_option': q['answer'],
            'is_correct': correct,
            'explanation': q['explanation'],
        })
    return {'score': score, 'total': len(questions), 'results': results}
