/**
 * Virtual Lab Navigator
 * The current page is highlighted by Django (base.html uses `current_step`),
 * so the menu is correct even without JavaScript. This script adds:
 *  - the menu button: on wide screens it shows/hides the left sidebar; below
 *    992px (where the sidebar is hidden) it opens the pop-up menu instead,
 *    like the Virtual Labs experiment pages;
 *  - keyboard shortcuts: Alt + ← / → moves between steps;
 *  - hides a header logo whose image file is missing (instead of a broken icon).
 */
document.addEventListener('DOMContentLoaded', () => {
  const BREAKPOINT_LG = 992;
  const toggleBtn = document.getElementById('menuToggle');
  const sidebar = document.getElementById('labSidebar');
  const popup = document.getElementById('popupMenu');

  document.querySelectorAll('img.vl-logo').forEach((img) => {
    const hide = () => img.classList.add('is-hidden');
    if (img.complete && img.naturalWidth === 0) hide();
    img.addEventListener('error', hide);
  });

  toggleBtn?.addEventListener('click', () => {
    if (window.innerWidth < BREAKPOINT_LG) {
      if (popup && window.bootstrap) bootstrap.Modal.getOrCreateInstance(popup).toggle();
    } else if (sidebar) {
      const hidden = sidebar.classList.toggle('vlabs-hidden');
      toggleBtn.setAttribute('aria-expanded', String(!hidden));
    }
  });

  document.addEventListener('keydown', (e) => {
    if (!e.altKey || ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
    const items = [...document.querySelectorAll('.lab-step-item')];
    const idx = items.findIndex(i => i.classList.contains('active'));
    if (e.key === 'ArrowRight' && idx < items.length - 1) window.location = items[idx + 1].href;
    if (e.key === 'ArrowLeft' && idx > 0) window.location = items[idx - 1].href;
  });
});
