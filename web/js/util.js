// Shared helpers: escaping (all server/LLM text goes through esc), formatting, tooltip, storage.

export function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export const fmtInt = (n) => (n == null ? '–' : Math.round(n).toLocaleString('en-US'));
export const fmtPeso = (n) => (n == null ? '–' : '₱' + Math.round(n).toLocaleString('en-US'));
export const fmtPct = (x, digits = 1) => (x == null ? '–' : (100 * x).toFixed(digits) + '%');
export const fmtSigned = (p, digits = 1) => (p == null ? '–' : (p >= 0 ? '+' : '−') + Math.abs(p).toFixed(digits) + '%');
export const fmtCompact = (n) => {
  if (n == null) return '–';
  const a = Math.abs(n);
  if (a >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (a >= 1e4) return (n / 1e3).toFixed(1) + 'K';
  return Math.round(n).toLocaleString('en-US');
};
export const pad2 = (n) => String(n).padStart(2, '0');
export function clock(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  return `${pad2(Math.floor(s / 3600) % 24)}:${pad2(Math.floor((s % 3600) / 60))}`;
}

export function h(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

// ------------------------------------------------------------ tooltip
const tip = () => document.getElementById('tooltip');
export function showTip(html, x, y) {
  const el = tip();
  el.innerHTML = html;
  el.hidden = false;
  const r = el.getBoundingClientRect();
  let left = x + 14;
  let top = y + 14;
  if (left + r.width > window.innerWidth - 8) left = x - r.width - 14;
  if (top + r.height > window.innerHeight - 8) top = y - r.height - 14;
  el.style.left = Math.max(8, left) + 'px';
  el.style.top = Math.max(8, top) + 'px';
}
export function hideTip() {
  tip().hidden = true;
}
export function bindTip(el, htmlFn) {
  el.addEventListener('mousemove', (e) => showTip(htmlFn(e), e.clientX, e.clientY));
  el.addEventListener('mouseleave', hideTip);
  el.addEventListener('focus', () => {
    const r = el.getBoundingClientRect();
    showTip(htmlFn(null), r.left + r.width / 2, r.top);
  });
  el.addEventListener('blur', hideTip);
}

// ------------------------------------------------------------ storage (best effort only)
export function saveSession(key, value) {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch (_) { /* storage unavailable or full: the app works without it */ }
}
export function loadSession(key) {
  try {
    const v = sessionStorage.getItem(key);
    return v ? JSON.parse(v) : null;
  } catch (_) {
    return null;
  }
}

export const LANG_LABEL = { en: 'English', ja: '日本語', ko: '한국어', id: 'Bahasa Indonesia', fil: 'Filipino', zh: '中文' };
export const CAT_SINGULAR = { bakery: 'bakery', coffee: 'coffee', snacks: 'snack', beverages: 'beverage' };
export const CAT_LABEL = { bakery: 'Bakery', coffee: 'Coffee', snacks: 'Snacks', beverages: 'Beverages' };
export const METRIC_LABEL = {
  category_revenue: 'sales',
  category_units: 'units',
  category_attachment: 'attachment rate',
  total_revenue: 'store revenue',
  basket_value: 'average basket',
};
