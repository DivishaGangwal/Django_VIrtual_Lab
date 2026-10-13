/**
 * Dataset Explorer
 * Listens for `lab:dataset_loaded` and renders: metadata badges, preview table
 * with type tags and missing-value highlighting, and per-column statistics.
 * Also restores the session's dataset when the page is reopened, and empties
 * everything again on `lab:simulation_reset`.
 */
(() => {
  const { el, fmt, fetchJSON } = LabUtils;
  const MISSING = new Set(['', 'na', 'n/a', 'null', 'nan', 'none', '-']);
  const isMissing = (v) => v === null || v === undefined || MISSING.has(String(v).trim().toLowerCase());

  let current = null;

  function typeTag(type) {
    return el('span', { class: `type-tag type-tag-${type}`, text: type });
  }

  function renderMeta(data) {
    const meta = document.getElementById('datasetMeta');
    const delimNames = { ',': 'comma', ';': 'semicolon', '\t': 'tab', '|': 'pipe' };
    const badges = [
      ['badge-primary', `${data.row_count} rows`],
      ['badge-primary', `${data.col_count} columns`],
      ['badge-slate', `delimiter: ${delimNames[data.delimiter] || data.delimiter}`],
      [data.missing_values_count ? 'badge-warning' : 'badge-success', `${data.missing_values_count} missing cells`],
      ['badge-slate', `${data.stats.completeness_pct}% complete`],
    ];
    if (data.ragged_rows_count) badges.push(['badge-warning', `${data.ragged_rows_count} irregular rows fixed`]);
    if (data.truncated) badges.push(['badge-danger', 'truncated']);
    meta.replaceChildren(...badges.map(([cls, text]) => el('span', { class: `badge ${cls}`, text })));
  }

  function renderPreview(data) {
    const types = Object.fromEntries(data.stats.columns.map(c => [c.name, c.type]));
    const table = document.getElementById('previewTable');
    const thead = el('thead', {}, el('tr', {}, data.headers.map(h => el('th', {}, [h, typeTag(types[h])]))));
    const tbody = el('tbody', {}, data.preview_rows.map(row => el('tr', {}, data.headers.map(h => {
      const v = row[h];
      const missing = isMissing(v);
      const numeric = types[h] === 'int' || types[h] === 'float';
      return el('td', {
        class: missing ? 'cell-missing' : (numeric ? 'num' : null),
        text: missing ? (v ? v : 'missing') : v,
      });
    }))));
    table.replaceChildren(thead, tbody);
  }

  function statChip(label, value, fn) {
    return el('div', { class: 'stat-chip' }, [
      el('div', { class: 'stat-chip-label', text: label }),
      el('div', { class: 'stat-chip-val', text: fmt(value) }),
      el('div', { class: 'stat-chip-fn', text: fn }),
    ]);
  }

  function renderColumnStats(col) {
    const box = document.getElementById('columnStats');
    const header = el('p', {}, [el('strong', { text: col.name }), ' ', typeTag(col.type),
      ` — ${col.count} values, ${col.missing} missing, ${col.unique} unique`]);
    let body;
    if (col.kind === 'numeric') {
      body = el('div', { class: 'stats-grid' }, [
        statChip('Mean', col.mean, 'statistics.fmean'),
        statChip('Median', col.median, 'statistics.median'),
        statChip('Std. dev.', col.std_dev, 'statistics.stdev'),
        statChip('Min', col.min, 'min()'),
        statChip('Max', col.max, 'max()'),
        statChip('Range', col.range, 'max - min'),
        statChip('Q1', col.q1, 'quantiles(n=4)'),
        statChip('Q3', col.q3, 'quantiles(n=4)'),
        statChip('Sum', col.sum, 'sum()'),
      ]);
    } else if (col.kind === 'date') {
      body = el('div', { class: 'stats-grid' }, [
        statChip('Earliest', col.min, 'min(dates)'),
        statChip('Latest', col.max, 'max(dates)'),
        statChip('Span (days)', col.span_days, 'timedelta.days'),
      ]);
    } else {
      const maxCount = Math.max(1, ...col.top_values.map(t => t.count));
      body = el('div', {}, [
        el('div', { class: 'stats-grid' }, [
          statChip('Mode', col.mode, 'Counter.most_common'),
          statChip('Unique', col.unique, 'len(set())'),
        ]),
        el('h4', { text: 'Most frequent values' }),
        el('ul', { class: 'top-values' }, col.top_values.map(t => el('li', {}, [
          el('span', { text: t.value }),
          el('span', { class: 'bar-track' }, el('span', { class: 'bar', style: `display:block;width:${(100 * t.count / maxCount).toFixed(1)}%` })),
          el('span', { class: 'num', text: String(t.count) }),
        ]))),
      ]);
    }
    box.replaceChildren(header, body);
  }

  function renderPicker(data) {
    const picker = document.getElementById('columnPicker');
    const buttons = data.stats.columns.map((col, i) => {
      const b = el('button', { type: 'button', class: 'column-pill', 'aria-pressed': i === 0 ? 'true' : 'false', text: col.name });
      b.addEventListener('click', () => {
        picker.querySelectorAll('.column-pill').forEach(p => p.setAttribute('aria-pressed', 'false'));
        b.setAttribute('aria-pressed', 'true');
        renderColumnStats(col);
      });
      return b;
    });
    picker.replaceChildren(...buttons);
    if (data.stats.columns.length) renderColumnStats(data.stats.columns[0]);
  }

  function show(data) {
    current = data;
    document.getElementById('noDatasetState').classList.add('is-hidden');
    document.getElementById('datasetWorkspace').classList.remove('is-hidden');
    document.getElementById('datasetFilename').textContent = data.filename;
    renderMeta(data);
    renderPreview(data);
    renderPicker(data);
    window.dispatchEvent(new CustomEvent('lab:explorer_ready', { detail: data }));
  }

  function hide() {
    current = null;
    document.getElementById('noDatasetState').classList.remove('is-hidden');
    document.getElementById('datasetWorkspace').classList.add('is-hidden');
    ['datasetFilename', 'datasetMeta', 'previewTable', 'columnPicker', 'columnStats']
      .forEach(id => document.getElementById(id)?.replaceChildren());
    window.dispatchEvent(new CustomEvent('lab:dataset_cleared'));
  }

  document.addEventListener('DOMContentLoaded', async () => {
    const root = document.getElementById('labApp');
    if (!root) return;

    window.addEventListener('lab:dataset_loaded', (e) => show(e.detail));
    window.addEventListener('lab:simulation_reset', hide);

    // Restore the dataset already stored in the session (e.g. after visiting Theory).
    if (root.dataset.hasDataset === '1') {
      try {
        const { ok, data } = await fetchJSON(root.dataset.datasetUrl);
        if (ok && data.status === 'success') show(data);
      } catch { /* ignore — user can reload a dataset */ }
    }
  });

  window.DatasetExplorer = { get current() { return current; } };
})();
