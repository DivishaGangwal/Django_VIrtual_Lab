/**
 * Chart Studio
 * Builds a query to /api/chart-data/, receives {labels, datasets} prepared by
 * Python on the server, and draws it with Chart.js.
 */
(() => {
  const { el, fetchJSON, notice } = LabUtils;
  const PALETTE = ['#2c99ce', '#ff6600', '#77bb41', '#3e6389', '#3ec1d5', '#b26100', '#8e44ad', '#5c5c5c', '#c62828', '#288ec8'];
  let chart = null;
  let dataset = null;

  const $ = (id) => document.getElementById(id);

  function option(value, label, selected = false) {
    const o = el('option', { value, text: label || value });
    o.selected = selected;
    return o;
  }

  function columnsOf(kind) {
    return dataset.stats.columns.filter(c => c.kind === kind).map(c => c.name);
  }

  /** Picks sensible defaults for each chart type so the first Plot "just works". */
  function populateSelects() {
    const type = $('chartType').value;
    const cols = dataset.stats.columns;
    const numeric = columnsOf('numeric');
    // Measurements = numeric columns that are not identifiers like Student_ID.
    const measures = cols.filter(c => c.kind === 'numeric' && !c.is_identifier).map(c => c.name);
    const measuresOrAll = measures.length ? measures : numeric;
    const dates = columnsOf('date');
    // Good grouping columns: text/date columns with a manageable number of distinct values.
    const groupable = cols.filter(c => c.kind !== 'numeric' && c.unique <= 30).map(c => c.name);
    const lowCardFirst = groupable.find(n => cols.find(c => c.name === n).unique < dataset.row_count);
    const all = dataset.headers;

    let xChoices = all;
    let xDefault;
    if (type === 'histogram' || type === 'scatter') {
      xChoices = numeric;
      xDefault = type === 'scatter' ? (measuresOrAll[1] ? measuresOrAll[1] : measuresOrAll[0]) : measuresOrAll[0];
    } else if (type === 'pie' || type === 'doughnut') {
      xChoices = groupable.length ? groupable : all;
      xDefault = lowCardFirst || xChoices[0];
    } else if (type === 'line') {
      xDefault = dates[0] || lowCardFirst || cols.find(c => c.kind !== 'numeric')?.name || all[0];
    } else {
      xDefault = lowCardFirst || cols.find(c => c.kind !== 'numeric')?.name || all[0];
    }

    // Keep the user's previous X only if it suits the new chart type.
    const prevX = $('chartX').value;
    const keepX = xChoices.includes(prevX) && !(['bar', 'line', 'pie', 'doughnut'].includes(type) && numeric.includes(prevX) && prevX !== xDefault);
    const xSel = keepX ? prevX : xDefault;
    $('chartX').replaceChildren(...xChoices.map(c => option(c, c, c === xSel)));

    const prevY = [...$('chartY').selectedOptions].map(o => o.value).filter(y => numeric.includes(y) && y !== xSel);
    const yDefault = [measuresOrAll.find(n => n !== xSel) || measuresOrAll[0]];
    // Pie/doughnut default to counting rows per category (a "share of the whole").
    const ySel = ['pie', 'doughnut'].includes(type) ? [] : (prevY.length ? prevY : yDefault);
    $('chartY').replaceChildren(...numeric.map(c => option(c, c, ySel.includes(c))));
    $('chartY').multiple = !['pie', 'doughnut'].includes(type);

    $('chartYField').classList.toggle('is-hidden', type === 'histogram');
    $('chartAggField').classList.toggle('is-hidden', type === 'histogram' || type === 'scatter');
    $('chartBinsField').classList.toggle('is-hidden', type !== 'histogram');

    if (['bar', 'pie', 'doughnut'].includes(type) && $('chartAgg').value === 'none') $('chartAgg').value = 'mean';
    if (type === 'line' && dataset.stats.columns.find(c => c.name === $('chartX').value)?.unique === dataset.row_count) $('chartAgg').value = 'none';
  }

  function buildQuery() {
    const type = $('chartType').value;
    const params = new URLSearchParams({ type, x: $('chartX').value });
    if (type !== 'histogram') [...$('chartY').selectedOptions].forEach(o => params.append('y', o.value));
    if (!['histogram', 'scatter'].includes(type)) params.set('agg', $('chartAgg').value);
    if (type === 'histogram') params.set('bins', $('chartBins').value || '8');
    return params;
  }

  function draw(payload) {
    const multiColour = ['pie', 'doughnut'].includes(payload.chart_type);
    const datasets = payload.datasets.map((ds, i) => {
      const colour = PALETTE[i % PALETTE.length];
      return {
        ...ds,
        backgroundColor: multiColour ? payload.labels.map((_, j) => PALETTE[j % PALETTE.length]) : colour + (payload.chart_type === 'line' ? '33' : 'cc'),
        borderColor: multiColour ? '#ffffff' : colour,
        borderWidth: multiColour ? 2 : (payload.chart_type === 'line' ? 2.5 : 1),
        pointRadius: payload.chart_type === 'scatter' ? 5 : 3,
        tension: 0.25,
        fill: payload.chart_type === 'line' && payload.datasets.length === 1,
        barPercentage: payload.is_histogram ? 1.0 : 0.8,
        categoryPercentage: payload.is_histogram ? 1.0 : 0.8,
      };
    });
    const axes = multiColour ? {} : {
      x: { type: payload.chart_type === 'scatter' ? 'linear' : 'category', title: { display: true, text: payload.x_label } },
      y: { beginAtZero: payload.chart_type !== 'scatter', title: { display: true, text: payload.y_label } },
    };
    if (chart) chart.destroy();
    chart = new Chart($('chartCanvas'), {
      type: payload.chart_type,
      data: { labels: payload.labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 500 },
        plugins: {
          legend: { display: multiColour || datasets.length > 1, position: multiColour ? 'right' : 'top' },
          title: { display: true, text: `${dataset.filename} — ${datasets.map(d => d.label).join(', ')}`, font: { size: 14 } },
        },
        scales: axes,
      },
    });
    $('downloadChartBtn').disabled = false;
  }

  async function plot() {
    const notices = $('chartNotice');
    if (typeof Chart === 'undefined') {
      notice(notices, 'error', '⚠️ Chart.js not loaded', 'Chart.js is loaded from the internet (cdnjs). Check your connection and reload the page.');
      return;
    }
    const type = $('chartType').value;
    if (type !== 'histogram' && !$('chartY').selectedOptions.length && !['pie', 'doughnut', 'bar', 'line'].includes(type)) {
      notice(notices, 'error', '⚠️ Choose a Y column', 'Select at least one numeric column for the Y axis.');
      return;
    }
    const params = buildQuery();
    const url = `${document.getElementById('labApp').dataset.chartUrl}?${params}`;
    $('chartRequestUrl').textContent = `GET ${decodeURIComponent(url)}`;
    try {
      const { ok, data } = await fetchJSON(url);
      if (!ok || data.status !== 'success') {
        notice(notices, 'error', '⚠️ Cannot draw this chart', data.message || 'Unknown error');
        return;
      }
      notices.replaceChildren();
      draw(data);
      window.dispatchEvent(new CustomEvent('lab:chart_plotted', { detail: { payload: data, url: decodeURIComponent(url), chart, filename: dataset.filename } }));
    } catch (err) {
      notice(notices, 'error', '⚠️ Network error', err.message);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('labApp')) return;

    window.addEventListener('lab:explorer_ready', (e) => {
      dataset = e.detail;
      $('chartX').replaceChildren();
      $('chartY').replaceChildren();
      populateSelects();
      plot();
    });
    window.addEventListener('lab:dataset_cleared', () => {
      dataset = null;
      if (chart) { chart.destroy(); chart = null; }
      $('downloadChartBtn').disabled = true;
      window.dispatchEvent(new CustomEvent('lab:chart_cleared'));
    });

    $('chartType').addEventListener('change', () => { if (dataset) { populateSelects(); plot(); } });
    $('plotBtn').addEventListener('click', () => dataset && plot());
    $('downloadChartBtn').addEventListener('click', () => {
      if (!chart) return;
      const a = el('a', { href: chart.toBase64Image('image/png', 1), download: `${dataset.filename.replace(/\.csv$/i, '')}_${$('chartType').value}.png` });
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
  });
})();
