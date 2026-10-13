/**
 * Simulation Stepper — "How does Django read a CSV?"
 *
 * Simple walkthrough: one stage at a time, one sentence of explanation,
 * one small thing to try, and an optional "Show the Python code" toggle.
 *
 * Events in:  lab:ingest_ready {data, gated}, lab:pipeline_goto, lab:pipeline_reset, lab:pipeline_error,
 *             lab:simulation_reset (also forgets puzzle answers)
 * Events out: lab:pipeline_step {step,name}, lab:dataset_loaded (when results are revealed)
 */
(() => {
  const { el, text } = LabUtils;
  const LAST = 6;
  const $ = (id) => document.getElementById(id);

  // The guided walkthrough is always on; "Skip to results" bypasses it.
  window.LabSimMode = { get: () => 'stepper', set: () => {} };

  const freshState = () => ({ data: null, trace: null, step: 1, revealed: false, showCode: false, showChallenge: false, attempts: {} });
  const state = freshState();

  /* ---------- small DOM helpers ---------- */
  const chip = (value, cls = '') => el('span', { class: `sim-chip ${cls}`.trim(), text: text(value) });
  const pre = (text) => el('pre', { class: 'sim-pre', text });
  const note = (text, cls = '') => el('p', { class: `sim-note ${cls}`.trim(), text });
  const kv = (rows) => el('table', { class: 'sim-kv' }, rows.map(([k, v]) =>
    el('tr', {}, [el('th', { text: k }), el('td', {}, v instanceof Node ? v : text(v))])));
  const btn = (text, onClick, cls = 'btn btn-secondary btn-sm', extra = {}) => {
    const b = el('button', { type: 'button', class: cls, text, ...extra });
    b.addEventListener('click', onClick);
    return b;
  };
  const tokens = (arr, cls = '') => el('div', { class: 'sim-tokens' },
    arr.map((t) => chip(t === '' ? '(empty)' : t, `${cls}${t === '' ? ' sim-chip-empty' : ''}`)));
  const tryIt = (...kids) => el('div', { class: 'sim-try' }, [el('div', { class: 'sim-try-label', text: 'Try it' }), ...kids]);

  /* ---------- stage views (kept deliberately small) ---------- */

  function viewUpload(t) {
    const u = t.upload;
    const out = el('div', { class: 'sim-result' });
    const slider = el('input', { type: 'range', min: '1', max: '6000', value: String(Math.max(1, Math.round(u.size / 1024))), 'aria-label': 'File size in KB' });
    const update = () => {
      const kb = Number(slider.value);
      const mem = kb * 1024 <= u.in_memory_limit;
      out.replaceChildren(chip(`${kb} KB`, 'sim-chip-blue'), document.createTextNode(' is kept '),
        el('strong', { text: mem ? 'in memory' : 'in a temporary file on disk' }),
        document.createTextNode(kb > 5120 ? '. This lab would reject it (limit 5 MB).' : '.'));
    };
    slider.addEventListener('input', update);
    update();
    return el('div', {}, [
      kv([['Name', u.filename], ['Size', `${u.size.toLocaleString()} bytes`], ['Django object', u.class_name]]),
      tryIt(note('Drag to change the file size:'), slider, out),
    ]);
  }

  function viewBytes(t) {
    const b = t.bytes;
    const hex = el('div', { class: 'sim-hex' }, b.hex.split(' ').slice(0, 24).map((h, i) =>
      el('span', { class: `sim-hex-byte${b.has_bom && i < 3 ? ' sim-hex-bom' : ''}`, text: h })));
    const result = el('div', { class: 'sim-result' });
    const row = el('div', { class: 'sim-btn-row' });
    const pick = (enc) => {
      row.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.enc === enc)));
      const bad = enc !== 'utf-8-sig' && b.has_bom;
      const header = enc === 'utf-8-sig' ? b.first_header_utf8sig : (enc === 'utf-8' ? b.first_header_utf8 : (b.has_bom ? `'ï»¿' + ${b.first_header_utf8sig}` : b.first_header_utf8sig));
      result.replaceChildren(el('div', {}, ['First column name becomes: ', el('code', { text: header })]),
        note(bad ? 'Hidden junk characters are stuck to the name, so looking up this column would fail.' : 'Clean name.', bad ? 'sim-bad' : 'sim-ok'));
    };
    ['utf-8-sig', 'utf-8', 'cp1252'].forEach((enc) =>
      row.appendChild(btn(enc, () => pick(enc), 'btn btn-secondary btn-sm', { 'data-enc': enc, 'aria-pressed': 'false' })));
    pick('utf-8-sig');
    return el('div', {}, [
      note('First bytes of your file (hex):'), hex,
      note(b.has_bom ? 'The yellow bytes (EF BB BF) are an invisible Excel marker called a BOM.' : 'No BOM marker in this file.'),
      tryIt(note('Decode with different encodings:'), row, result),
    ]);
  }

  function viewSniff(t) {
    const s = t.sniff;
    const lines = s.sample.split('\n');
    const names = Object.fromEntries(s.candidates.map((c) => [c.char, c.name]));
    let forced = s.delimiter;
    const out = el('div');
    const row = el('div', { class: 'sim-btn-row' });
    const draw = () => {
      row.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.ch === forced)));
      const counts = lines.map((ln) => ln.split(forced).length);
      const ok = counts.every((c) => c === counts[0]) && counts[0] > 1;
      out.replaceChildren(
        ...lines.map((ln) => tokens(ln.split(forced), ok ? '' : 'sim-chip-bad')),
        note(ok ? `Every line splits into ${counts[0]} columns. This is the right delimiter.` : 'The lines split unevenly. This is the wrong delimiter.', ok ? 'sim-ok' : 'sim-bad'));
    };
    s.candidates.forEach((c) => row.appendChild(btn(c.name, () => { forced = c.char; draw(); }, 'btn btn-secondary btn-sm', { 'data-ch': c.char, 'aria-pressed': 'false' })));
    draw();
    return el('div', {}, [
      note(`Python picked the ${names[s.delimiter]} as the separator. The text is then placed in memory (io.StringIO) so it can be read line by line.`),
      tryIt(note('Choose a separator and see how the first lines split:'), row, out),
    ]);
  }

  function viewTokenize(t) {
    const rows = t.tokenize.rows;
    const viewer = el('div');
    const slider = el('input', { type: 'range', min: '1', max: String(Math.max(1, rows.length)), value: '1', 'aria-label': 'Row number' });
    const draw = () => {
      const r = rows[Number(slider.value) - 1];
      if (!r) { viewer.replaceChildren(note('No rows to show.')); return; }
      const bad = r.naive_split.length !== r.tokens.length;
      viewer.replaceChildren(
        el('div', { class: 'sim-step-line' }, [el('strong', { text: '1. Line in the file' }), pre(r.raw_line)]),
        el('div', { class: 'sim-step-line' }, [el('strong', { text: '2. Python splits it into cells' }), tokens(r.tokens, 'sim-chip-ok'),
          bad ? note('A plain split would have cut a quoted cell in the wrong place. The csv module does not.', 'sim-bad') : null]),
        el('div', { class: 'sim-step-line' }, [el('strong', { text: '3. Cells are matched with column names' }),
          el('table', { class: 'sim-kv' }, Object.entries(r.row).map(([h, v]) => el('tr', {}, [
            el('th', { text: h }), el('td', { class: r.missing.includes(h) ? 'sim-missing' : '', text: r.missing.includes(h) ? `${v || '(empty)'}  (missing)` : v })])))]),
      );
    };
    slider.addEventListener('input', draw);
    draw();
    return tryIt(note('Drag to look at each row:'), slider, viewer);
  }

  function viewTypes(t) {
    const ty = t.types;
    const body = [el('div', { class: 'sim-tokens' }, ty.columns.map((c) =>
      el('span', { class: 'sim-chip' }, [`${c.name} `, el('span', { class: `type-tag type-tag-${c.type}`, text: c.type })])))];
    const ex = ty.example;
    if (ex) {
      const result = el('div', { class: 'sim-result' });
      const forms = {
        Mean: ['statistics.fmean(values)', `${ex.sum} / ${ex.n} = ${ex.mean}`],
        Median: ['statistics.median(values)', `${ex.median}`],
        Min: ['min(values)', `${ex.min}`],
        Max: ['max(values)', `${ex.max}`],
      };
      const row = el('div', { class: 'sim-btn-row' });
      const choose = (n) => {
        row.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.n === n)));
        result.replaceChildren(el('code', { text: forms[n][0] }), document.createTextNode('  gives  '), el('strong', { text: forms[n][1] }));
      };
      Object.keys(forms).forEach((n) => row.appendChild(btn(n, () => choose(n), 'btn btn-secondary btn-sm', { 'data-n': n, 'aria-pressed': 'false' })));
      choose('Mean');
      body.push(note(`Example column "${ex.column}" has ${ex.n} numbers:`), pre(`[${ex.first_values.join(', ')}${ex.n > ex.first_values.length ? ', ...' : ''}]`),
        tryIt(note('Calculate a statistic:'), row, result));
    }
    return el('div', {}, body);
  }

  function viewSession(t) {
    const s = t.session.payload;
    return el('div', {}, [
      pre(`request.session["active_dataset"] = {\n  filename: "${s.filename}",\n  headers: [${s.headers.slice(0, 4).map((h) => `"${h}"`).join(', ')}${s.headers.length > 4 ? ', ...' : ''}],\n  rows: ${s.row_count} rows,\n  stats: ...\n}`),
      state.revealed ? note('Results are shown below.', 'sim-ok') : note('Now press "Show results" to see your data and charts.'),
    ]);
  }

  /* ---------- stage content ---------- */
  const code = (...lines) => lines.map((l) => (l.startsWith('>') ? [l.slice(1), true] : [l, false]));
  const STAGES = [
    { name: 'HTTP Upload', title: 'The file reaches Django', view: viewUpload,
      text: 'Your browser sends the file in a POST request. Django gives it to the view as request.FILES.',
      file: 'views.py', code: code('form = CSVUploadForm(request.POST, request.FILES)', '>uploaded_file = form.cleaned_data["csv_file"]') },
    { name: 'Bytes → Text', title: 'Bytes become text', view: viewBytes,
      text: 'A file is just bytes. Python must decode them into text first. "utf-8-sig" is tried first because it removes the hidden Excel marker.',
      file: 'csv_parser.py', code: code('raw_data = file_obj.read()', '>return raw_data.decode("utf-8-sig")') },
    { name: 'Sniff + Stream', title: 'Find the separator', view: viewSniff,
      text: 'CSV files may separate columns with commas, semicolons, tabs or pipes. Python guesses which one is used.',
      file: 'csv_parser.py', code: code('>delimiter = csv.Sniffer().sniff(sample).delimiter', 'stream = io.StringIO(text)') },
    { name: 'Tokenize', title: 'Split rows into cells', view: viewTokenize,
      text: 'Python reads the text line by line, splits each line into cells and stores every row as a dictionary: column name → value.',
      file: 'csv_parser.py', code: code('>reader = csv.reader(stream, delimiter=delimiter)', 'for cells in reader:', '>    row = dict(zip(headers, cells))') },
    { name: 'Types + Stats', title: 'Detect types and calculate statistics', view: viewTypes,
      text: 'Every cell starts as text. If a whole column converts to numbers, it is numeric. Then Python\'s statistics module does the maths (no pandas).',
      file: 'stats_engine.py', code: code('>mean = statistics.fmean(numbers)', '>median = statistics.median(numbers)') },
    { name: 'Session + JSON', title: 'Save it and reply', view: viewSession,
      text: 'The parsed data is saved in the Django session so other pages can reuse it. Django then replies to the browser with JSON.',
      file: 'views.py', code: code('>request.session["active_dataset"] = dataset', '>return JsonResponse(summary)') },
  ];

  /* ---------- code challenges: drag-and-drop / click-to-place options ---------- */
  const ex = (t) => t.types.example;
  const CHALLENGES = [
    { file: 'views.py', fn: 'upload_csv_api', before: 'uploaded_file = request.', after: '["csv_file"]', obj: "'WSGIRequest' object", kind: 'attr',
      options: ['FILES', 'POST', 'GET', 'data'],
      right: ['FILES'], hint: 'Django keeps uploaded files in a special attribute of request. It is written in capital letters.',
      special: {
        POST: { error: "KeyError: 'csv_file'", hint: 'request.POST only holds normal form text fields. Files are stored in request.FILES.' },
        GET: { error: "KeyError: 'csv_file'", hint: 'request.GET holds the URL query string, not uploaded files.' },
        data: { error: "AttributeError: 'WSGIRequest' object has no attribute 'data'", hint: 'Django standard requests use request.FILES for file uploads, not request.data.' },
      },
      ok: (t) => [`>>> uploaded_file.name`, `'${t.upload.filename}'`, `>>> uploaded_file.size`, `${t.upload.size} bytes`, `>>> type(uploaded_file).__name__`, `'${t.upload.class_name}'`] },
    { file: 'csv_parser.py', fn: 'decode_file_stream', before: 'text = raw_data.', after: "('utf-8-sig')", obj: "'bytes' object", kind: 'attr',
      options: ['decode', 'encode', 'read', 'str'],
      right: ['decode'], hint: 'We want to turn raw bytes into text string. Which bytes method does that? (encode turns str into bytes.)',
      special: {
        encode: { error: "AttributeError: 'bytes' object has no attribute 'encode'", hint: 'encode() is for string → bytes. To convert bytes → string, use decode().' },
        read: { error: "AttributeError: 'bytes' object has no attribute 'read'", hint: 'raw_data is already bytes in memory, not a file stream. Use .decode().' },
        str: { error: "AttributeError: 'bytes' object has no attribute 'str'", hint: 'Call the .decode() method on the bytes object.' },
      },
      ok: (t) => [`>>> text[:35]`, `'${t.bytes.decoded_preview.slice(0, 35).replace(/\r?\n/g, '\\n')}'`, `>>> text.split()[0]  # first header`, t.bytes.first_header_utf8sig] },
    { file: 'csv_parser.py', fn: '_detect_delimiter', before: 'delimiter = csv.', after: '().sniff(sample).delimiter', obj: "module 'csv'", kind: 'attr',
      options: ['Sniffer', 'reader', 'sniffer', 'DictReader'],
      right: ['Sniffer'], hint: 'The csv module has a class that analyzes a text sample to guess the delimiter. It starts with a capital letter.',
      special: {
        sniffer: { error: "AttributeError: module 'csv' has no attribute 'sniffer'", hint: 'Python class names use PascalCase: Sniffer with a capital S.' },
        reader: { error: "AttributeError: '_csv.reader' object has no attribute 'sniff'", hint: 'reader is for reading rows. The delimiter detector class is Sniffer.' },
        DictReader: { error: "AttributeError: 'DictReader' object has no attribute 'sniff'", hint: 'DictReader maps rows to dicts. Delimiter detection is done by Sniffer.' },
      },
      ok: (t) => [`>>> delimiter`, JSON.stringify(t.sniff.delimiter), `>>> f"Detected separator: '{delimiter}'"`] },
    { file: 'csv_parser.py', fn: 'parse_csv_content', before: 'reader = csv.', after: '(stream, delimiter=delimiter)', obj: "module 'csv'", kind: 'attr',
      options: ['reader', 'writer', 'parser', 'split'],
      right: ['reader', 'DictReader'], hint: 'We want to READ rows from the stream. Which csv module object reads line tokens?',
      special: {
        writer: { error: "TypeError: '_csv.writer' object is not iterable", hint: 'A writer WRITES csv data. We need reader to read incoming data.' },
        parser: { error: "AttributeError: module 'csv' has no attribute 'parser'", hint: 'Python built-in csv module has reader and DictReader.' },
        split: { error: "AttributeError: module 'csv' has no attribute 'split'", hint: 'The csv module does not have a split function. Use csv.reader().' },
      },
      ok: (t) => [`>>> next(reader)`, JSON.stringify((t.tokenize.rows[0] || { tokens: [] }).tokens)] },
    { file: 'stats_engine.py', fn: 'describe_dataset', before: 'average = statistics.', after: '(numbers)', obj: "module 'statistics'", kind: 'attr',
      options: ['fmean', 'median', 'stdev', 'mode'],
      right: ['fmean', 'mean'], hint: 'We want the arithmetic average. The statistics module has fmean() and mean().',
      special: {
        median: { logic: (t) => `It ran and returned ${ex(t) ? ex(t).median : '?'}, but that is the MEDIAN (middle value), not the average!`, hint: 'Pick the function that adds everything up and divides by the count: fmean.' },
        stdev: { logic: (t) => `It ran and returned ${ex(t) && ex(t).std_dev !== null ? ex(t).std_dev : '?'}, but that is the STANDARD DEVIATION, not the average!`, hint: 'Pick fmean for arithmetic average.' },
        mode: { logic: () => 'mode() returns the most frequent value, not the average.', hint: 'Use fmean for calculating column average.' },
      },
      ok: (t) => (ex(t) ? [`>>> numbers  # column "${ex(t).column}"`, `[${ex(t).first_values.slice(0, 5).join(', ')}, ...]`, `>>> average`, `${ex(t).mean}`] : ['(this dataset has no numeric column to average)']) },
    { file: 'views.py', fn: '_store_dataset', before: 'request.session["active_dataset"] = ', after: '', obj: '', kind: 'name',
      options: ['dataset', 'rows', 'headers', 'stats'],
      right: ['dataset'], hint: 'The dictionary that holds the complete parsed dataset (headers, rows, and stats) is called dataset.',
      special: {
        rows: { logic: () => 'It saved, but only the rows. The Chart Studio needs headers and stats too, causing a KeyError!', hint: 'Store the whole dataset dictionary so other views have headers and stats.' },
        headers: { logic: () => 'Saving only headers misses all the data rows and computed statistics!', hint: 'Store the whole dataset.' },
        stats: { logic: () => 'Saving only stats misses the raw rows needed for filtering and charting!', hint: 'Store the full dataset dictionary.' },
      },
      ok: (t) => [`>>> len(request.session["active_dataset"]["rows"])`, `${t.session.payload.row_count}`, `>>> "stats" in request.session["active_dataset"]`, 'True'] },
  ];

  /** Returns {status:'ok'|'error'|'logic', lines:[...], hint?} */
  function judge(ch, raw, t, line) {
    const s = (raw || '').trim();
    const tb = (msg) => ['Traceback (most recent call last):', `  File "${ch.file}", in ${ch.fn}`, `    ${line(s)}`, msg];
    if (!s) return { status: 'error', lines: tb('SyntaxError: invalid syntax (blank is empty)'), hint: 'Drag or click an option to fill the blank.' };
    if (ch.right.includes(s)) return { status: 'ok', lines: ['>>> ' + line(s), ...ch.ok(t)] };
    const sp = ch.special && ch.special[s];
    if (sp && sp.error) return { status: 'error', lines: tb(sp.error), hint: sp.hint };
    if (sp && sp.logic) return { status: 'logic', lines: ['>>> ' + line(s), sp.logic(t)], hint: sp.hint };
    const msg = ch.kind === 'name' ? `NameError: name '${s}' is not defined` : `AttributeError: ${ch.obj} has no attribute '${s}'`;
    return { status: 'error', lines: tb(msg), hint: ch.hint };
  }

  const passedCount = () => Object.values(state.attempts).filter((a) => a.passed).length;
  const updateCount = () => {
    const cnt = document.getElementById('simChallengeCount');
    if (cnt) cnt.textContent = `${passedCount()} of ${CHALLENGES.length} correct`;
  };

  function challengeBox(i) {
    const ch = CHALLENGES[i - 1];
    const at = state.attempts[i] || (state.attempts[i] = { value: '', fails: 0, passed: false, last: null });
    const line = (s) => `${ch.before}${s || '____'}${ch.after}`;

    const term = el('pre', { class: 'sim-terminal' });
    const hintBox = el('p', { class: 'sim-hintbox' });
    const badge = el('span', { class: 'sim-verdict is-hidden', role: 'status', 'aria-live': 'polite' });
    const slotWrap = el('span', { class: 'sim-drop-slot-wrap' });
    const optionsPalette = el('div', { class: 'sim-chip-palette' });

    function runValue(val) {
      at.value = val;
      const r = judge(ch, at.value, state.trace, line);
      at.last = r;
      at.passed = r.status === 'ok';
      if (!at.passed) at.fails += 1;
      paint(true);
      updateCount();
    }

    function clearSlot() {
      at.value = '';
      at.last = null;
      at.passed = false;
      paint();
      updateCount();
    }

    const paint = (fresh = false) => {
      const r = at.last;
      const val = at.value;

      // Render Drop Slot
      slotWrap.replaceChildren();
      const slot = el('span', {
        class: `sim-drop-slot ${val ? 'is-filled' : 'is-empty'} ${r ? (r.status === 'ok' ? 'is-ok' : r.status === 'logic' ? 'is-warn' : 'is-err') : ''}`,
        tabindex: '0',
        role: 'button',
        'aria-label': val ? `Filled with ${val}, click to clear` : 'Drop blank: drag or click an option below',
      });

      if (val) {
        slot.appendChild(el('span', { class: 'sim-slot-val', text: val }));
        const clearBtn = el('span', { class: 'sim-slot-clear', text: '✕', title: 'Clear' });
        clearBtn.addEventListener('click', (e) => { e.stopPropagation(); clearSlot(); });
        slot.appendChild(clearBtn);
        slot.addEventListener('click', clearSlot);
      } else {
        slot.appendChild(el('span', { class: 'sim-slot-placeholder', text: '____ (drop here)' }));
      }

      // Drag over / drop handlers on the slot
      slot.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        slot.classList.add('is-dragover');
      });
      slot.addEventListener('dragleave', () => slot.classList.remove('is-dragover'));
      slot.addEventListener('drop', (e) => {
        e.preventDefault();
        slot.classList.remove('is-dragover');
        const droppedVal = e.dataTransfer.getData('text/plain');
        if (droppedVal) runValue(droppedVal);
      });
      slotWrap.appendChild(slot);

      // Render Options Chips
      optionsPalette.replaceChildren();
      ch.options.forEach((opt) => {
        const isChosen = val === opt;
        const chipBtn = el('button', {
          type: 'button',
          draggable: 'true',
          class: `sim-drag-chip ${isChosen ? 'is-active' : ''}`,
          text: opt,
          title: `Drag or click to choose ${opt}`,
        });

        // Click to place
        chipBtn.addEventListener('click', () => runValue(opt));

        // Drag handlers
        chipBtn.addEventListener('dragstart', (e) => {
          e.dataTransfer.setData('text/plain', opt);
          e.dataTransfer.effectAllowed = 'copy';
          chipBtn.classList.add('is-dragging');
        });
        chipBtn.addEventListener('dragend', () => chipBtn.classList.remove('is-dragging'));

        optionsPalette.appendChild(chipBtn);
      });

      // Terminal output
      term.replaceChildren();
      term.classList.toggle('is-hidden', !r);
      if (r) {
        r.lines.forEach((l, k) => {
          const isErr = r.status !== 'ok' && k === r.lines.length - 1;
          const isCmd = l.startsWith('>>> ');
          term.appendChild(el('div', {
            class: isErr ? (r.status === 'logic' ? 'sim-term-warn' : 'sim-term-err') : isCmd ? 'sim-term-cmd' : 'sim-term-out',
            text: l,
          }));
        });
      }

      const showHint = r && r.status !== 'ok' && r.hint;
      hintBox.classList.toggle('is-hidden', !showHint);
      hintBox.textContent = showHint ? '💡 ' + r.hint : '';

      // Verdict for the latest attempt: green ✓ or red ✗ (wrong answers, errors and logic mistakes).
      const verdict = r ? (r.status === 'ok' ? 'ok' : 'wrong') : null;
      badge.textContent = verdict === 'ok' ? '✓ Correct!' : verdict === 'wrong' ? '✗ Incorrect' : '';
      badge.classList.toggle('is-hidden', !verdict);
      badge.classList.toggle('is-ok', verdict === 'ok');
      badge.classList.toggle('is-wrong', verdict === 'wrong');
      if (fresh && verdict) { // replay the pop animation so repeated attempts are visible
        badge.classList.remove('is-flash');
        void badge.offsetWidth;
        badge.classList.add('is-flash');
      }
    };

    paint();

    return el('div', { class: 'sim-challenge' }, [
      el('div', { class: 'sim-challenge-header' }, [
        el('div', { class: 'sim-try-label', text: 'Interactive Code Puzzle' }),
        badge,
      ]),
      el('p', { class: 'sim-challenge-sub', text: 'Drag a chip or click it to complete the Python code:' }),
      el('div', { class: 'sim-challenge-code' }, [
        el('span', { text: ch.before }),
        slotWrap,
        el('span', { text: ch.after }),
      ]),
      el('div', { class: 'sim-palette-wrap' }, [
        el('span', { class: 'sim-palette-label', text: 'Options:' }),
        optionsPalette,
      ]),
      term,
      hintBox,
    ]);
  }

  /* ---------- rendering ---------- */
  function emitStep() {
    window.dispatchEvent(new CustomEvent('lab:pipeline_step', { detail: { step: state.step, name: STAGES[state.step - 1].name } }));
  }
  function goto(step) { state.step = Math.max(1, Math.min(LAST, step)); emitStep(); render(); }
  function reveal() {
    if (!state.revealed) {
      state.revealed = true;
      window.dispatchEvent(new CustomEvent('lab:dataset_loaded', { detail: state.data }));
    }
    state.step = LAST; emitStep(); render();
    $('datasetWorkspace')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function render() {
    const box = $('pipelineInspector');
    if (!box) return;
    if (!state.data || !state.trace) { box.classList.add('is-hidden'); box.replaceChildren(); return; }
    box.classList.remove('is-hidden');
    const st = STAGES[state.step - 1];
    const atLast = state.step === LAST;

    const codeBlock = state.showCode ? el('div', {}, [
      el('div', { class: 'sim-codefile', text: st.file }),
      el('pre', { class: 'sim-code' }, st.code.map(([line, hl]) => el('div', { class: `sim-code-line${hl ? ' sim-code-hl' : ''}`, text: line }))),
    ]) : null;

    // Optional parts are null when hidden; replaceChildren() would print them as
    // the text "null", so they are filtered out first.
    box.replaceChildren(...[
      el('div', { class: 'sim-insp-head' }, [
        el('span', { class: 'sim-step-count', text: `Step ${state.step} of ${LAST}` }),
        el('h4', { class: 'sim-insp-title', text: st.title }),
      ]),
      el('p', { class: 'sim-concept', text: st.text }),
      el('div', { class: 'sim-insp-body' }, st.view(state.trace, state.data)),
      state.showChallenge ? challengeBox(state.step) : null,
      el('div', { class: 'sim-footer' }, [
        el('div', { class: 'sim-footer-left' }, [
          btn(state.showChallenge ? 'Hide code exercise' : 'Try the code', () => { state.showChallenge = !state.showChallenge; render(); }, 'btn btn-secondary btn-sm'),
          el('span', { id: 'simChallengeCount', class: 'sim-count', text: `${passedCount()} of ${CHALLENGES.length} correct` }),
          btn(state.showCode ? 'Hide Python code' : 'Show Python code', () => { state.showCode = !state.showCode; render(); }, 'sim-link'),
        ]),
        el('div', { class: 'sim-controls' }, [
          state.step > 1 ? btn('Back', () => goto(state.step - 1)) : null,
          atLast
            ? btn(state.revealed ? 'Results shown' : 'Show results', reveal, 'btn btn-primary btn-sm', state.revealed ? { disabled: true } : {})
            : btn('Next', () => goto(state.step + 1), 'btn btn-primary btn-sm'),
          state.revealed ? null : btn('Skip to results', reveal, 'sim-link'),
        ]),
      ]),
      codeBlock,
    ].filter(Boolean));
  }

  /* ---------- wiring ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    if (!$('pipelineInspector')) return;

    window.addEventListener('lab:ingest_ready', (e) => {
      const { data, gated } = e.detail;
      Object.assign(state, { data, trace: data.trace || null, step: 1, revealed: !gated, showCode: false });
      if (gated) { $('datasetWorkspace')?.classList.add('is-hidden'); emitStep(); }
      render();
    });
    window.addEventListener('lab:pipeline_goto', (e) => { if (state.trace) goto(e.detail.step); });
    const clear = () => { state.data = null; state.trace = null; render(); };
    window.addEventListener('lab:pipeline_reset', clear);
    window.addEventListener('lab:pipeline_error', clear);
    window.addEventListener('lab:simulation_reset', () => { Object.assign(state, freshState()); render(); });
  });
})();
