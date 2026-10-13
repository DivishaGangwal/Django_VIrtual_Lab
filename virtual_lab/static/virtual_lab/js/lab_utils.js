/**
 * Shared helpers: safe DOM building (no innerHTML with user data), CSRF, notices,
 * toasts and JSON POSTs. Loaded on every page by base.html.
 */
window.LabUtils = (() => {
  /** el('div', {class: 'x', text: 'hi'}, [children]) — text is always set via textContent. */
  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (value === null || value === undefined || value === false) continue;
      if (key === 'text') node.textContent = value;
      else if (key === 'class') node.className = value;
      else if (key === 'style') node.style.cssText = value;
      else node.setAttribute(key, value === true ? '' : value);
    }
    for (const child of [].concat(children)) {
      if (child === null || child === undefined) continue;
      node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
    }
    return node;
  }

  function getCookie(name) {
    const match = document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith(name + '='));
    return match ? decodeURIComponent(match.slice(name.length + 1)) : '';
  }

  function csrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');
  }

  /** Renders a callout into container. type: 'info' | 'success' | 'error'. */
  function notice(container, type, title, message) {
    if (!container) return;
    const cls = type === 'error' ? 'callout callout-warning' : type === 'success' ? 'callout callout-success' : 'callout';
    container.replaceChildren(
      el('div', { class: cls, role: type === 'error' ? 'alert' : 'status' }, [
        el('div', { class: 'callout-title', text: title }),
        el('div', { class: 'callout-content', text: message }),
      ])
    );
  }

  async function fetchJSON(url, options = {}) {
    const response = await fetch(url, { credentials: 'same-origin', ...options });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(`Server returned ${response.status} ${response.statusText} (not JSON).`);
    }
    return { ok: response.ok, status: response.status, data };
  }

  /** POSTs a JSON body with the CSRF token. Resolves to {ok, status, data}. */
  function postJSON(url, body) {
    return fetchJSON(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify(body),
    });
  }

  /** Bootstrap toast in the bottom-right corner. type: 'success' | 'error'. */
  function toast(type, message) {
    const area = document.getElementById('toastArea');
    if (!area) return;
    const box = el('div', {
      class: `toast vl-toast vl-toast-${type === 'error' ? 'error' : 'success'}`,
      role: type === 'error' ? 'alert' : 'status', 'aria-live': type === 'error' ? 'assertive' : 'polite', 'aria-atomic': 'true',
    }, el('div', { class: 'd-flex' }, [
      el('div', { class: 'toast-body', text: `${type === 'error' ? '✗' : '✓'} ${message}` }),
      el('button', { type: 'button', class: 'btn-close me-2 m-auto', 'data-bs-dismiss': 'toast', 'aria-label': 'Close' }),
    ]));
    area.appendChild(box);
    box.addEventListener('hidden.bs.toast', () => box.remove());
    if (window.bootstrap) bootstrap.Toast.getOrCreateInstance(box, { delay: 4500 }).show();
    else box.classList.add('show');
  }

  /** Display text for a raw value: null/undefined/'' become '—', never "null"/"undefined". */
  function text(value) {
    return value === null || value === undefined || value === '' ? '—' : String(value);
  }

  function fmt(value) {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'number') return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 3 });
    return String(value);
  }

  return { el, csrfToken, notice, fetchJSON, postJSON, toast, fmt, text };
})();
