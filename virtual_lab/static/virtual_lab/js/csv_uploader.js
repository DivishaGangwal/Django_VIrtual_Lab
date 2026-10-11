/**
 * CSV Uploader & Ingestion Client Controller
 * Drag-and-drop / file-picker uploads and sample loading.
 * On success it dispatches `lab:dataset_loaded` with the server's JSON summary.
 *
 * Fixes vs. the earlier version:
 *  - Status messages are built with textContent (filenames/server messages can
 *    no longer inject HTML → no XSS).
 *  - API URLs come from data-* attributes rendered by {% url %}, not hardcoded.
 *  - Re-selecting the same file works (input value is reset).
 *  - The dropzone is keyboard accessible (Enter/Space).
 *  - Non-JSON server errors (e.g. 403 CSRF, 500) show a readable message.
 */
class CSVUploader {
  constructor(root) {
    this.root = root;
    this.urls = { upload: root.dataset.uploadUrl, sample: root.dataset.sampleUrl };
    this.dropzone = document.getElementById('csvDropzone');
    this.fileInput = document.getElementById('csvFileInput');
    this.sampleSelect = document.getElementById('sampleDatasetSelect');
    this.sampleDescription = document.getElementById('sampleDescription');
    this.loadSampleBtn = document.getElementById('loadSampleBtn');
    this.statusContainer = document.getElementById('uploadStatusNotice');
    this.busy = false;
    this.initEventListeners();
  }

  initEventListeners() {
    const dz = this.dropzone;
    if (dz) {
      ['dragenter', 'dragover'].forEach(evt => dz.addEventListener(evt, (e) => {
        e.preventDefault();
        dz.classList.add('dragover');
      }));
      ['dragleave', 'drop'].forEach(evt => dz.addEventListener(evt, (e) => {
        e.preventDefault();
        dz.classList.remove('dragover');
      }));
      dz.addEventListener('drop', (e) => {
        const files = e.dataTransfer?.files;
        if (files && files.length > 0) this.handleFileUpload(files[0]);
      });
      dz.addEventListener('click', () => this.fileInput?.click());
      dz.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.fileInput?.click(); }
      });
    }

    this.fileInput?.addEventListener('change', (e) => {
      const file = e.target.files?.[0];
      if (file) this.handleFileUpload(file);
      e.target.value = ''; // allow picking the same file again
    });

    this.sampleSelect?.addEventListener('change', () => {
      const opt = this.sampleSelect.selectedOptions[0];
      if (this.sampleDescription && opt) this.sampleDescription.textContent = opt.dataset.description || '';
    });

    this.loadSampleBtn?.addEventListener('click', () => this.loadSampleDataset(this.sampleSelect.value));
  }

  showStatus(type, message) {
    const titles = { error: '⚠️ Validation Notice', success: '✓ Ingestion Successful', info: '⏳ Working…' };
    LabUtils.notice(this.statusContainer, type, titles[type], message);
  }

  setBusy(busy) {
    this.busy = busy;
    if (this.loadSampleBtn) this.loadSampleBtn.disabled = busy;
    this.dropzone?.setAttribute('aria-busy', String(busy));
  }

  step(step, name) {
    window.dispatchEvent(new CustomEvent('lab:pipeline_step', { detail: { step, name } }));
  }

  async finishPipeline(data) {
    const wait = (ms) => new Promise(r => setTimeout(r, ms));
    const stepper = (window.LabSimMode?.get() === 'stepper') && !!data.trace;
    // The stepper (simulation_stepper.js) owns the teaching walkthrough. In
    // step-by-step mode it reveals the results itself when the student finishes.
    window.dispatchEvent(new CustomEvent('lab:ingest_ready', { detail: { data, gated: stepper } }));
    if (stepper) return;
    for (const [n, name] of [[2, 'Bytes → Text'], [3, 'Sniff + Stream'], [4, 'Tokenize'], [5, 'Types + Stats']]) {
      this.step(n, name); await wait(150);
    }
    this.step(6, 'Session + JSON');
    window.dispatchEvent(new CustomEvent('lab:dataset_loaded', { detail: data }));
  }

  fail(message) {
    this.showStatus('error', message);
    window.dispatchEvent(new CustomEvent('lab:pipeline_error', { detail: { message } }));
  }

  async handleFileUpload(file) {
    if (this.busy) return;

    // Client-side checks are for quick feedback only; the server re-validates everything.
    if (!file.name.toLowerCase().endsWith('.csv')) {
      return this.fail('Invalid file format. Please select a .csv (Comma-Separated Values) file.');
    }
    if (file.size === 0) return this.fail('The selected file is empty (0 bytes).');
    const maxBytes = 5 * 1024 * 1024;
    if (file.size > maxBytes) {
      return this.fail(`File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the 5 MB limit.`);
    }

    window.dispatchEvent(new CustomEvent('lab:pipeline_reset'));
    this.step(1, 'HTTP Upload');
    const formData = new FormData();
    formData.append('csv_file', file);

    this.setBusy(true);
    try {
      this.showStatus('info', `Uploading ${file.name} and parsing it with Python's csv module…`);
      const { ok, data } = await LabUtils.fetchJSON(this.urls.upload, {
        method: 'POST',
        headers: { 'X-CSRFToken': LabUtils.csrfToken() },
        body: formData,
      });
      if (ok && data.status === 'success') {
        this.showStatus('success', `Parsed ${data.filename}: ${data.row_count} rows × ${data.col_count} columns.`);
        await this.finishPipeline(data);
      } else {
        this.fail(data.message || 'Error processing CSV file.');
      }
    } catch (err) {
      this.fail('Could not reach the Django server: ' + err.message);
    } finally {
      this.setBusy(false);
    }
  }

  async loadSampleDataset(sampleId) {
    if (this.busy) return;
    window.dispatchEvent(new CustomEvent('lab:pipeline_reset'));
    this.step(1, 'Sample request');
    this.setBusy(true);
    try {
      this.showStatus('info', 'Loading sample dataset from the server…');
      const url = `${this.urls.sample}?sample_id=${encodeURIComponent(sampleId)}`;
      const { ok, data } = await LabUtils.fetchJSON(url);
      if (ok && data.status === 'success') {
        this.showStatus('success', `Loaded ${data.sample_info?.name || sampleId}: ${data.row_count} rows × ${data.col_count} columns.`);
        await this.finishPipeline(data);
      } else {
        this.fail(data.message || 'Failed to load sample.');
      }
    } catch (err) {
      this.fail('Could not reach the Django server: ' + err.message);
    } finally {
      this.setBusy(false);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('labApp');
  if (root) window.csvUploader = new CSVUploader(root);
});
