/**
 * Virtual Lab Navigator
 * The active/completed state of the progress ribbon is rendered by Django
 * (base.html uses `current_step`), so it is correct even without JavaScript.
 * This script only adds the pulse animation and keyboard shortcuts.
 *
 * (The previous version matched URLs with endsWith('/'), which matched every
 *  page, so the ribbon always showed Step 1 as active.)
 */
document.addEventListener('DOMContentLoaded', () => {
  const active = document.querySelector('.lab-step-item.active .lab-step-node');
  if (active) active.classList.add('pulse-active');

  // Alt + ← / → moves between steps.
  document.addEventListener('keydown', (e) => {
    if (!e.altKey || ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
    const items = [...document.querySelectorAll('.lab-step-item')];
    const idx = items.findIndex(i => i.classList.contains('active'));
    if (e.key === 'ArrowRight' && idx < items.length - 1) window.location = items[idx + 1].href;
    if (e.key === 'ArrowLeft' && idx > 0) window.location = items[idx - 1].href;
  });
});
