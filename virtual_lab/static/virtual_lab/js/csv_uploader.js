/**
 * CSV Uploader & Ingestion Client Controller
 * Manages drag-and-drop file uploads, sample dataset loading, and dispatches dataset events.
 */

class CSVUploader {
  constructor() {
    this.dropzone = document.getElementById('csvDropzone');
    this.fileInput = document.getElementById('csvFileInput');
    this.sampleSelect = document.getElementById('sampleDatasetSelect');
    this.loadSampleBtn = document.getElementById('loadSampleBtn');
    this.statusContainer = document.getElementById('uploadStatusNotice');

    this.initEventListeners();
  }

  initEventListeners() {
    if (this.dropzone) {
      // Drag events
      ['dragenter', 'dragover'].forEach(eventName => {
        this.dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          this.dropzone.classList.add('dragover');
        });
      });

      ['dragleave', 'drop'].forEach(eventName => {
        this.dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          this.dropzone.classList.remove('dragover');
        });
      });

      this.dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
          this.handleFileUpload(files[0]);
        }
      });

      this.dropzone.addEventListener('click', () => {
        if (this.fileInput) this.fileInput.click();
      });
    }

    if (this.fileInput) {
      this.fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
          this.handleFileUpload(e.target.files[0]);
        }
      });
    }

    if (this.loadSampleBtn && this.sampleSelect) {
      this.loadSampleBtn.addEventListener('click', () => {
        const sampleId = this.sampleSelect.value;
        this.loadSampleDataset(sampleId);
      });
    }
  }

  showStatus(message, type = 'info') {
    if (!this.statusContainer) return;
    this.statusContainer.innerHTML = `
      <div class="callout ${type === 'error' ? 'callout-warning' : 'callout-success'}" style="margin: 1rem 0;">
        <div class="callout-title">${type === 'error' ? '⚠️ Validation Notice' : '✓ Ingestion Successful'}</div>
        <div class="callout-content">${message}</div>
      </div>
    `;
  }

  async handleFileUpload(file) {
    // 1. Client-Side Validation
    if (!file.name.toLowerCase().endsWith('.csv')) {
      this.showStatus('Invalid file format. Please select a valid Comma-Separated Values (.csv) file.', 'error');
      return;
    }

    const maxBytes = 5 * 1024 * 1024;
    if (file.size > maxBytes) {
      this.showStatus(`File size (${(file.size / (1024*1024)).toFixed(2)} MB) exceeds the 5 MB limit.`, 'error');
      return;
    }

    if (file.size === 0) {
      this.showStatus('The selected file is empty (0 bytes).', 'error');
      return;
    }

    // Trigger pipeline visualizer animation stage 1 & 2
    window.dispatchEvent(new CustomEvent('lab:pipeline_step', { detail: { step: 1, name: 'Browser Upload' } }));

    const formData = new FormData();
    formData.append('csv_file', file);

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    try {
      this.showStatus('Uploading and parsing CSV stream with Python csv.DictReader...', 'info');
      window.dispatchEvent(new CustomEvent('lab:pipeline_step', { detail: { step: 2, name: 'Django request.FILES' } }));

      const response = await fetch('/api/upload-csv/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
        },
        body: formData,
      });

      const data = await response.json();

      if (data.status === 'success') {
        window.dispatchEvent(new CustomEvent('lab:pipeline_step', { detail: { step: 3, name: 'csv.DictReader' } }));
        this.showStatus(`Successfully parsed <strong>${data.filename}</strong> (${data.row_count} rows, ${data.col_count} columns) using pure Python!`, 'success');
        
        // Dispatch global event for Dev 2 (Preview/Stats) and Dev 3 (Charts)
        window.dispatchEvent(new CustomEvent('lab:dataset_loaded', { detail: data }));
      } else {
        this.showStatus(data.message || 'Error processing CSV file.', 'error');
      }
    } catch (err) {
      this.showStatus('Network error connecting to Django backend: ' + err.message, 'error');
    }
  }

  async loadSampleDataset(sampleId) {
    try {
      window.dispatchEvent(new CustomEvent('lab:pipeline_step', { detail: { step: 1, name: 'Sample Load' } }));
      this.showStatus('Loading sample dataset from disk...', 'info');

      const response = await fetch(`/api/load-sample/?sample_id=${encodeURIComponent(sampleId)}`);
      const data = await response.json();

      if (data.status === 'success') {
        window.dispatchEvent(new CustomEvent('lab:pipeline_step', { detail: { step: 3, name: 'csv.DictReader' } }));
        this.showStatus(`Loaded built-in dataset: <strong>${data.sample_info?.name || sampleId}</strong> (${data.row_count} rows, ${data.col_count} columns).`, 'success');
        
        // Dispatch global event
        window.dispatchEvent(new CustomEvent('lab:dataset_loaded', { detail: data }));
      } else {
        this.showStatus(data.message || 'Failed to load sample.', 'error');
      }
    } catch (err) {
      this.showStatus('Network error loading sample dataset: ' + err.message, 'error');
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.csvUploader = new CSVUploader();
});
