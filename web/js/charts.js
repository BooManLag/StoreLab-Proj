// Small, quiet SVG charts: single-series columns and bars with hover tooltips and a table view.
import { esc, bindTip } from './util.js';

const NS = 'http://www.w3.org/2000/svg';

function s(tag, attrs = {}, parent = null, text = null) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) e.setAttribute(k, v);
  if (text !== null) e.textContent = text;
  if (parent) parent.appendChild(e);
  return e;
}

function niceMax(v) {
  if (v <= 0) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * p >= v) return m * p;
  return 10 * p;
}

/** Path for a bar with a 4px-style rounded data end and a square baseline. */
function colPath(x, yTop, w, yBase, r) {
  const rr = Math.max(0, Math.min(r, w / 2, yBase - yTop));
  return `M${x},${yBase}V${yTop + rr}Q${x},${yTop} ${x + rr},${yTop}H${x + w - rr}Q${x + w},${yTop} ${x + w},${yTop + rr}V${yBase}Z`;
}

function rowPath(xBase, y, xEnd, h, r) {
  const rr = Math.max(0, Math.min(r, h / 2, xEnd - xBase));
  return `M${xBase},${y}H${xEnd - rr}Q${xEnd},${y} ${xEnd},${y + rr}V${y + h - rr}Q${xEnd},${y + h} ${xEnd - rr},${y + h}H${xBase}Z`;
}

function tableView(headers, rows) {
  const d = document.createElement('details');
  d.className = 'table-view';
  d.innerHTML = `<summary>View as table</summary><div class="table-scroll"><table class="data"><thead><tr>${headers
    .map((h, i) => `<th class="${i ? 'n' : ''}">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows
    .map((r) => `<tr>${r.map((c, i) => `<td class="${i ? 'n' : ''}">${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  return d;
}

/** Draw at the container's real pixel width (so text stays legible) and redraw on resize. */
function responsive(container, table, draw) {
  container.innerHTML = '';
  container.classList.add('chart');
  const plot = document.createElement('div');
  container.appendChild(plot);
  if (table) container.appendChild(tableView(table.headers, table.rows));
  let last = 0;
  const paint = () => {
    const w = Math.round(plot.clientWidth);
    if (w > 0 && Math.abs(w - last) > 4) {
      last = w;
      plot.innerHTML = '';
      draw(plot, Math.max(260, w));
    }
  };
  new ResizeObserver(paint).observe(plot);
  paint();
}

/**
 * Vertical columns, one series. rows: [{label, value, emphasis, tip}]
 */
export function columnChart(container, rows, opts = {}) {
  responsive(container, opts.table, (plot, W) => drawColumns(plot, W, rows, opts));
}

function drawColumns(container, W, rows, { valueFmt = (v) => v.toFixed(2), axisLabel = '', xEvery = 1 } = {}) {
  const H = 200, m = { l: 36, r: 8, t: 10, b: 24 };
  const pw = W - m.l - m.r, ph = H - m.t - m.b;
  const max = niceMax(Math.max(...rows.map((r) => r.value)));
  const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': axisLabel }, container);
  const ticks = 4;
  for (let i = 0; i <= ticks; i++) {
    const v = (max * i) / ticks;
    const y = m.t + ph - (v / max) * ph;
    s('line', { x1: m.l, x2: W - m.r, y1: y, y2: y, class: i === 0 ? 'baseline' : 'gridline' }, svg);
    s('text', { x: m.l - 6, y: y + 3.5, 'text-anchor': 'end', class: 'num' }, svg, valueFmt(v));
  }
  const band = pw / rows.length;
  const bw = Math.min(24, band * 0.62);
  rows.forEach((r, i) => {
    const x = m.l + i * band + (band - bw) / 2;
    const yTop = m.t + ph - (r.value / max) * ph;
    const bar = s('path', { d: colPath(x, yTop, bw, m.t + ph, 4), class: 'bar' + (r.emphasis === false ? ' muted' : '') }, svg);
    if (i % xEvery === 0) s('text', { x: x + bw / 2, y: H - 6, 'text-anchor': 'middle' }, svg, r.label);
    const hit = s('rect', { x: m.l + i * band, y: m.t, width: band, height: ph, class: 'hit', tabindex: 0,
      'aria-label': `${r.label}: ${valueFmt(r.value)}` }, svg);
    bindTip(hit, () => r.tip || `<b>${esc(r.label)}</b>: ${esc(valueFmt(r.value))}`);
    hit.addEventListener('mouseenter', () => bar.classList.add('hover'));
    hit.addEventListener('mouseleave', () => bar.classList.remove('hover'));
  });
}

/**
 * Horizontal bars, one series (funnels, ranked lists). rows: [{label, value, display, tip}]
 */
export function barList(container, rows, opts = {}) {
  responsive(container, opts.table, (plot, W) => drawBars(plot, W, rows));
}

function drawBars(container, W, rows) {
  const rowH = 30, labelW = Math.min(118, Math.round(W * 0.34)), valueW = 104;
  const H = rows.length * rowH + 4;
  const max = Math.max(...rows.map((r) => r.value), 1);
  const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img' }, container);
  const pw = W - labelW - valueW;
  s('line', { x1: labelW, x2: labelW, y1: 0, y2: H, class: 'baseline' }, svg);
  rows.forEach((r, i) => {
    const y = i * rowH + 6;
    const h = Math.min(18, rowH - 10);
    const xEnd = labelW + Math.max(2, (r.value / max) * pw);
    s('text', { x: labelW - 8, y: y + h / 2 + 4, 'text-anchor': 'end', class: 'cat-label' }, svg, r.label);
    s('path', { d: rowPath(labelW, y, xEnd, h, 4), class: 'bar' }, svg);
    s('text', { x: xEnd + 6, y: y + h / 2 + 4, class: 'value-label num' }, svg, r.display ?? String(r.value));
    const hit = s('rect', { x: 0, y: i * rowH, width: W, height: rowH, class: 'hit', tabindex: 0,
      'aria-label': `${r.label}: ${r.display ?? r.value}` }, svg);
    bindTip(hit, () => r.tip || `<b>${esc(r.label)}</b>: ${esc(r.display ?? r.value)}`);
  });
}
