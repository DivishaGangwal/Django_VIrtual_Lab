/**
 * Shared helpers: safe DOM building (no innerHTML with user data), CSRF, notices.
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

  function fmt(value) {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'number') return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 3 });
    return String(value);
  }

  return { el, csrfToken, notice, fetchJSON, fmt };
})();
