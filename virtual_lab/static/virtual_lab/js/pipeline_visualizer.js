/**
 * Animates the 6-node pipeline tracker in response to `lab:pipeline_step`
 * events ({step: 1..6}) and `lab:pipeline_error`. Clicking a node asks the
 * stepper to jump to that stage (`lab:pipeline_goto`).
 * `lab:pipeline_reset` / `lab:simulation_reset` return it to Idle.
 */
document.addEventListener('DOMContentLoaded', () => {
  const nodes = [...document.querySelectorAll('.pipeline-node')];
  const status = document.getElementById('pipelineStatus');
  if (!nodes.length) return;
  const LAST = nodes.length;

  const setStatus = (label, cls = 'badge-slate', title = '') => {
    if (!status) return;
    status.textContent = label;
    status.className = `badge ${cls}`;
    if (title) status.title = title; else status.removeAttribute('title');
  };

  const setStep = (step, label) => {
    nodes.forEach(node => {
      const n = Number(node.dataset.node);
      node.classList.remove('error');
      node.classList.toggle('completed', n < step || (step === LAST && n === LAST));
      node.classList.toggle('active', n === step && step !== LAST);
    });
    setStatus(label, step === LAST ? 'badge-success' : 'badge-slate');
  };

  nodes.forEach(node => node.addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('lab:pipeline_goto', { detail: { step: Number(node.dataset.node) } }));
  }));

  const reset = () => setStep(0, 'Idle');
  window.addEventListener('lab:pipeline_reset', reset);
  window.addEventListener('lab:simulation_reset', reset);
  window.addEventListener('lab:pipeline_step', (e) => {
    const { step, name } = e.detail;
    setStep(step, step === LAST ? 'Complete' : name || `Stage ${step}`);
  });
  window.addEventListener('lab:pipeline_error', (e) => {
    // Mark the stage that failed (the one in progress, or Upload if nothing started) in red.
    const failed = nodes.find(n => n.classList.contains('active')) || nodes[0];
    nodes.forEach(node => node.classList.remove('active'));
    failed.classList.add('error');
    setStatus('✗ Stopped: error', 'badge-danger', e.detail?.message || '');
  });
});
