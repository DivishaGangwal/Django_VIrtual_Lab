/**
 * Reset Simulation
 * "Reset Simulation" (and "Clear dataset") open an in-page confirm panel. On
 * "Yes, reset" the dataset is removed from the Django session (reset API), then
 * `lab:simulation_reset` tells every module to return to its fresh-page state:
 *   dataset_explorer → preview + statistics, chart_studio → chart + controls,
 *   chart_explainer, simulation_stepper → "Try it" stages + code puzzles,
 *   pipeline_visualizer → Idle, csv_uploader → file input + status messages.
 */
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('labApp');
  const panel = document.getElementById('resetConfirm');
  if (!root || !panel) return;
  const { csrfToken, toast } = LabUtils;
  const openBtn = document.getElementById('resetSimulationBtn');
  const yesBtn = document.getElementById('resetConfirmYes');
  const noBtn = document.getElementById('resetConfirmNo');
  const errorBox = document.getElementById('resetConfirmError');

  function showError(message) {
    errorBox.textContent = message ? `✗ ${message}` : '';
    errorBox.classList.toggle('is-hidden', !message);
  }

  function openPanel() {
    showError('');
    panel.classList.remove('is-hidden');
    openBtn.setAttribute('aria-expanded', 'true');
    panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    yesBtn.focus({ preventScroll: true });
  }

  function closePanel() {
    panel.classList.add('is-hidden');
    openBtn.setAttribute('aria-expanded', 'false');
  }

  async function confirmReset() {
    yesBtn.disabled = true;
    try {
      const response = await fetch(root.dataset.resetUrl, {
        method: 'POST', headers: { 'X-CSRFToken': csrfToken() }, credentials: 'same-origin',
      });
      if (!response.ok) throw new Error(`Server returned ${response.status} ${response.statusText}.`);
    } catch (err) {
      showError(`Could not reset: ${err.message}`);
      return;
    } finally {
      yesBtn.disabled = false;
    }
    window.dispatchEvent(new CustomEvent('lab:simulation_reset'));
    closePanel();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    openBtn.focus({ preventScroll: true });
    toast('success', 'Simulation reset. Load a dataset to start again.');
  }

  openBtn.addEventListener('click', () => (panel.classList.contains('is-hidden') ? openPanel() : closePanel()));
  document.getElementById('resetDatasetBtn')?.addEventListener('click', openPanel);
  noBtn.addEventListener('click', () => { closePanel(); openBtn.focus(); });
  yesBtn.addEventListener('click', confirmReset);
  panel.addEventListener('keydown', (e) => { if (e.key === 'Escape') { closePanel(); openBtn.focus(); } });
});
