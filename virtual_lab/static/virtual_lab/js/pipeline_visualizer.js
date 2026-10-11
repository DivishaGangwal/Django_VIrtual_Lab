/**
 * Animates the 6-node pipeline tracker in response to `lab:pipeline_step`
 * events ({step: 1..6}) and `lab:pipeline_error`. Clicking a node asks the
 * stepper to jump to that stage (`lab:pipeline_goto`).
 */
document.addEventListener('DOMContentLoaded', () => {
  const nodes = [...document.querySelectorAll('.pipeline-node')];
  const status = document.getElementById('pipelineStatus');
  if (!nodes.length) return;
  const LAST = nodes.length;

  const setStep = (step, label) => {
    nodes.forEach(node => {
      const n = Number(node.dataset.node);
      node.classList.toggle('completed', n < step || (step === LAST && n === LAST));
      node.classList.toggle('active', n === step && step !== LAST);
    });
    if (status) status.textContent = label;
  };

  nodes.forEach(node => node.addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('lab:pipeline_goto', { detail: { step: Number(node.dataset.node) } }));
  }));

  window.addEventListener('lab:pipeline_reset', () => setStep(0, 'Idle'));
  window.addEventListener('lab:pipeline_step', (e) => {
    const { step, name } = e.detail;
    setStep(step, step === LAST ? 'Complete' : name || `Stage ${step}`);
  });
  window.addEventListener('lab:pipeline_error', (e) => {
    nodes.forEach(node => node.classList.remove('active'));
    if (status) status.textContent = 'Stopped: ' + (e.detail?.message || 'error');
  });
});
