/**
 * Chart Explainer — "How does Django visualize data?"
 *
 * After each plot, shows 4 interactive stages using the server's chart trace:
 *   V1 HTTP query  ·  V2 Python grouping/aggregation  ·  V3 Chart.js JSON  ·  V4 canvas pixel mapping
 */
(() => {
  const { el } = LabUtils;
  const $ = (id) => document.getElementById(id);
  const openState = { 1: false, 2: false, 3: false, 4: false };
  let openOuter = false;
  let ctx = null; // {payload, url, chart, filename}

  const pre = (text) => el('pre', { class: 'sim-pre', text });
  const note = (text, cls = '') => el('p', { class: `sim-note ${cls}`.trim(), text });
  const chip = (text, cls = '') => el('span', { class: `sim-chip ${cls}`.trim(), text: String(text) });
  const table = (head, rows) => el('div', { class: 'lab-table-container' }, el('table', { class: 'sim-table' }, [
    el('thead', {}, el('tr', {}, head.map((h) => el('th', { text: h })))),
    el('tbody', {}, rows.map((r) => el('tr', {}, r.map((c) => el('td', {}, c instanceof Node ? c : String(c)))))),
  ]));
  const list = (arr, n = 8) => `[${arr.slice(0, n).join(', ')}${arr.length > n ? ', …' : ''}]`;

  /* highlight a data point on the real chart */
  function highlight(index) {
    const chart = ctx?.chart;
    if (!chart) return;
    try {
      const active = index === null ? [] : [{ datasetIndex: 0, index }];
      chart.setActiveElements(active);
      chart.tooltip?.setActiveElements(active, { x: 0, y: 0 });
      chart.update('none');
    } catch { /* chart destroyed meanwhile */ }
  }

  /* ---------- V1: request ---------- */
  function v1() {
    const t = ctx.payload.trace;
    const p = t.params;
    const lines = [`chart_type = request.GET.get('type', 'bar')   # ${JSON.stringify(p.type)}`,
      `x          = request.GET.get('x', '')            # ${JSON.stringify(p.x)}`];
    if (p.y) lines.push(`y_columns  = request.GET.getlist('y')          # ${JSON.stringify(p.y)}`);
    if (p.agg !== undefined) lines.push(`agg        = request.GET.get('agg', 'none')      # ${JSON.stringify(p.agg)}`);
    if (p.bins !== undefined) lines.push(`bins       = int(request.GET.get('bins', 8))     # ${p.bins}`);
    return el('div', {}, [
      note('Your dropdown choices were turned into a query string and sent to Django with fetch():'),
      pre(`GET ${ctx.url} HTTP/1.1`),
      note('chart_data_api() in views.py reads them back out of request.GET:'),
      pre(lines.join('\n')),
      note('It then loads the dataset saved in request.session (from Stage 6 of the reading pipeline) and calls build_chart_data().'),
    ]);
  }

  /* ---------- V2: grouping / aggregation ---------- */
  function v2() {
    const t = ctx.payload.trace;
    const hover = (node, i) => {
      node.addEventListener('mouseenter', () => highlight(i));
      node.addEventListener('mouseleave', () => highlight(null));
      return node;
    };
    const rowsWith = (head, rows) => {
      const tbl = table(head, rows.map((r) => r.cells));
      tbl.querySelectorAll('tbody tr').forEach((tr, i) => hover(tr, rows[i].idx));
      return tbl;
    };
    const tip = note('Hover a row to highlight the matching bar/point on the chart above.');

    if (t.mode === 'grouped') {
      const expr = {
        mean: (g) => `sum(vals) / len(vals) = ${g.values.length === g.n_values ? `sum(${list(g.values)}) / ${g.n_values}` : `… / ${g.n_values}`}`,
        sum: () => 'sum(vals)', count: () => 'len(vals)', min: () => 'min(vals)', max: () => 'max(vals)',
      }[t.agg] || (() => t.agg);
      return el('div', {}, [
        note(`Python grouped the rows by “${t.params.x}” using an OrderedDict, collected “${t.y}” per group, then applied ${t.agg}():`),
        pre(`groups = OrderedDict()\nfor row in rows:\n    groups.setdefault(row[${JSON.stringify(t.params.x)}], []).append(row)\n# ${t.n_groups} groups found\nfor key, group in groups.items():\n    vals = [to_number(r[${JSON.stringify(t.y || '')}]) for r in group]\n    result = ${t.agg}(vals)`),
        rowsWith(['Category (X)', 'Rows', `Values of ${t.y || '—'} (first 8)`, 'Expression', 'Result (Y)'],
          t.groups.map((g, i) => ({ idx: i, cells: [g.key, g.count, list(g.values), expr(g), el('strong', { text: g.result ?? '—' })] }))),
        t.n_groups > t.groups.length ? note(`Showing the first ${t.groups.length} of ${t.n_groups} groups.`) : null, tip,
      ]);
    }
    if (t.mode === 'category_count') {
      return el('div', {}, [
        note('With no Y column, a pie/doughnut counts how often each category occurs using collections.Counter:'),
        pre(`counts = Counter(r[${JSON.stringify(t.params.x)}] for r in rows if not is_missing(r[...]))\ntop = counts.most_common(30)`),
        rowsWith(['Category', 'Count'], t.groups.map((g, i) => ({ idx: i, cells: [g.key, el('strong', { text: g.result })] }))), tip,
      ]);
    }
    if (t.mode === 'histogram') {
      return el('div', {}, [
        note('A histogram splits the numeric range into equal-width bins and counts how many values fall in each:'),
        pre(`lo, hi = min(nums), max(nums)      # ${t.lo}, ${t.hi}\nwidth  = (hi - lo) / bins           # (${t.hi} - ${t.lo}) / ${t.bins} = ${t.width}\nfor n in nums:\n    counts[min(int((n - lo) / width), bins - 1)] += 1`),
        rowsWith(['Bin (range)', 'Count'], t.groups.map((g, i) => ({ idx: i, cells: [g.key, el('strong', { text: g.count })] }))),
        note(`${t.n} numeric values were binned; missing/non-numeric cells are skipped.`), tip,
      ]);
    }
    if (t.mode === 'scatter') {
      return el('div', {}, [
        note('A scatter plot needs no grouping: each row with a valid X and Y number becomes one {x, y} point.'),
        pre('points = [{"x": to_number(r[x]), "y": to_number(r[y])}\n          for r in rows if both are numbers]'),
        table(['#', 'x', 'y'], t.points.map((p, i) => [i + 1, p.x, p.y])),
        note(`${t.total_points} points plotted${t.skipped ? `; ${t.skipped} rows skipped (missing or non-numeric)` : ''}.`),
      ]);
    }
    return el('div', {}, [
      note('Aggregation “none” sends the raw rows through unchanged (up to 500), converting Y cells with to_number():'),
      rowsWith(['X label', 'Y value'], t.groups.map((g, i) => ({ idx: i, cells: [g.key, g.result ?? '—'] }))),
      note(`${t.total_rows} rows in the dataset; first few shown.`), tip,
    ]);
  }

  /* ---------- V3: JSON contract ---------- */
  function v3() {
    const p = ctx.payload;
    const N = 12;
    const isScatter = p.chart_type === 'scatter';
    const ds = p.datasets[0] || { data: [], label: '' };
    const item = (text, i) => {
      const s = el('span', { class: 'sim-json-item', text, tabindex: '0' });
      s.addEventListener('mouseenter', () => highlight(i));
      s.addEventListener('focus', () => highlight(i));
      s.addEventListener('mouseleave', () => highlight(null));
      s.addEventListener('blur', () => highlight(null));
      return s;
    };
    const seq = (arr, fmt) => {
      const out = [];
      arr.slice(0, N).forEach((v, i) => { if (i) out.push(', '); out.push(item(fmt(v), i)); });
      if (arr.length > N) out.push(`, … (${arr.length - N} more)`);
      return out;
    };
    const line = (indent, ...parts) => el('div', { class: 'sim-json-line', style: `padding-left:${indent}rem` }, parts);
    return el('div', {}, [
      note('Django returns this JSON. Chart.js needs nothing else. Hover a value to highlight it on the chart.'),
      el('div', { class: 'sim-json' }, [
        line(0, '{'),
        line(1, `"chart_type": ${JSON.stringify(p.chart_type)},`),
        line(1, '"labels": [', ...(isScatter ? ['(none for scatter)'] : seq(p.labels, (v) => JSON.stringify(v))), '],'),
        line(1, '"datasets": [{'),
        line(2, `"label": ${JSON.stringify(ds.label)},`),
        line(2, '"data": [', ...seq(ds.data, (v) => (isScatter ? `{x:${v.x}, y:${v.y}}` : String(v))), ']'),
        line(1, '}],'),
        line(1, `"x_label": ${JSON.stringify(p.x_label)}, "y_label": ${JSON.stringify(p.y_label)}`),
        line(0, '}'),
      ]),
      note('Chart.js (in the browser) only draws this; all grouping and maths happened in Python.'),
    ]);
  }

  /* ---------- V4: canvas mapping ---------- */
  function v4() {
    const chart = ctx.chart;
    const p = ctx.payload;
    const ds = p.datasets[0];
    const n = ds ? ds.data.length : 0;
    if (!chart || !n) return note('Nothing to map.');
    const isRound = ['pie', 'doughnut'].includes(p.chart_type);
    const isScatter = p.chart_type === 'scatter';
    const out = el('div', { class: 'sim-result' });
    const slider = el('input', { type: 'range', min: '1', max: String(Math.min(n, 200)), value: '1', 'aria-label': 'Data point number' });

    const draw = () => {
      const i = Number(slider.value) - 1;
      highlight(i);
      const v = ds.data[i];
      const area = chart.chartArea;
      const rows = [];
      if (isRound) {
        const total = ds.data.reduce((a, b) => a + b, 0);
        const deg = (v / total) * 360;
        rows.push(['label', p.labels[i]], ['value', v], ['total', total],
          ['share', `${v} / ${total} = ${(100 * v / total).toFixed(1)}%`], ['slice angle', `${v} / ${total} × 360° = ${deg.toFixed(1)}°`]);
      } else {
        const ys = chart.scales.y;
        const xs = chart.scales.x;
        const yv = isScatter ? v.y : v;
        const px = Math.round(xs.getPixelForValue(isScatter ? v.x : i));
        const py = Math.round(ys.getPixelForValue(yv));
        const lin = area.bottom - ((yv - ys.min) / (ys.max - ys.min)) * (area.bottom - area.top);
        rows.push(
          [isScatter ? 'x value' : 'label', isScatter ? v.x : p.labels[i]], ['y value', yv],
          ['y-axis range', `${ys.min} … ${ys.max}`], ['plot area (px)', `top ${Math.round(area.top)}, bottom ${Math.round(area.bottom)}`],
          ['formula', `y_px = bottom − (value − min) / (max − min) × (bottom − top)`],
          ['y_px', `${Math.round(area.bottom)} − (${yv} − ${ys.min}) / (${ys.max} − ${ys.min}) × ${Math.round(area.bottom - area.top)} = ${Math.round(lin)}`],
          ['Chart.js says', `scale.getPixelForValue(${yv}) = ${py}`], ['x_px', `${px}`]);
      }
      out.replaceChildren(el('table', { class: 'sim-kv' }, rows.map(([k, val]) => el('tr', {}, [el('th', { text: k }), el('td', { text: String(val) })]))));
    };
    slider.addEventListener('input', draw);
    slider.addEventListener('change', () => highlight(null));
    draw();
    highlight(null);
    return el('div', {}, [
      note('Chart.js draws on an HTML5 <canvas>, where (0, 0) is the TOP-left corner and y grows downward. It linearly maps your data values onto pixels:'),
      slider, out,
      note(isRound ? 'Pie slices are drawn as arcs whose angle is proportional to each value\'s share of the total.'
        : 'Drag the slider: the matching point is highlighted on the chart above, and the numbers come straight from Chart.js\'s own scales.'),
    ]);
  }

  /* ---------- assemble ---------- */
  const PANELS = [
    [1, 'Step 1 · Your choices are sent to Django', v1],
    [2, 'Step 2 · Python groups the rows and calculates', v2],
    [3, 'Step 3 · Django replies with JSON', v3],
    [4, 'Step 4 · Chart.js draws it on a canvas', v4],
  ];

  function render() {
    const box = $('chartExplainer');
    if (!box) return;
    if (!ctx || !ctx.payload.trace) { box.classList.add('is-hidden'); box.replaceChildren(); return; }
    box.classList.remove('is-hidden');
    const details = PANELS.map(([id, title, fn]) => {
      const d = el('details', { class: 'sim-acc' }, [el('summary', { text: title })]);
      d.open = openState[id];
      let built = false;
      const build = () => {
        if (built) return;
        built = true;
        try { d.appendChild(el('div', { class: 'sim-acc-body' }, fn())); }
        catch (err) { d.appendChild(note('Could not explain this chart: ' + err.message, 'sim-bad')); }
      };
      if (d.open) build();
      d.addEventListener('toggle', () => { openState[id] = d.open; if (d.open) build(); });
      return d;
    });
    const outer = el('details', { class: 'sim-acc sim-acc-main' }, [
      el('summary', { text: 'How was this chart made? (4 short steps)' }),
      el('div', { class: 'sim-acc-body' }, [note('Click a step to open it.'), ...details]),
    ]);
    outer.open = openOuter;
    outer.addEventListener('toggle', () => { openOuter = outer.open; });
    box.replaceChildren(outer);
  }

  document.addEventListener('DOMContentLoaded', () => {
    window.addEventListener('lab:chart_plotted', (e) => { ctx = e.detail; render(); });
    window.addEventListener('lab:chart_cleared', () => { ctx = null; render(); });
  });
})();
