/**
 * Animates the 5-node pipeline tracker in response to `lab:pipeline_step`
 * events ({step: 1..5}) and `lab:pipeline_error`.
 */
document.addEventListener('DOMContentLoaded', () => {
  const nodes = [...document.querySelectorAll('.pipeline-node')];
  const status = document.getElementById('pipelineStatus');
  if (!nodes.length) return;

  const setStep = (step, label) => {
    nodes.forEach(node => {
      const n = Number(node.dataset.node);
      node.classList.toggle('completed', n < step || (step === 5 && n === 5));
      node.classList.toggle('active', n === step && step !== 5);
    });
    if (status) status.textContent = label;
  };

  window.addEventListener('lab:pipeline_reset', () => setStep(0, 'Idle'));
  window.addEventListener('lab:pipeline_step', (e) => {
    const { step, name } = e.detail;
    setStep(step, step === 5 ? 'Complete' : name || `Stage ${step}`);
  });
  window.addEventListener('lab:pipeline_error', (e) => {
    nodes.forEach(node => node.classList.remove('active'));
    if (status) status.textContent = 'Stopped: ' + (e.detail?.message || 'error');
  });
});
