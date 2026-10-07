// SVG digital-twin floor plan: zones, fixtures, display slots, insight pins, heatmap, animated shoppers.
import { CAT_LABEL, fmtInt, showTip, hideTip } from './util.js';

const NS = 'http://www.w3.org/2000/svg';
const HEAT_BINS = 7;

function s(tag, attrs = {}, parent = null, text = null) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) e.setAttribute(k, v);
  if (text !== null) e.textContent = text;
  if (parent) parent.appendChild(e);
  return e;
}

const rectAttrs = (r, extra = {}) => ({ x: r.x0, y: r.y0, width: r.x1 - r.x0, height: r.y1 - r.y0, ...extra });

export function heatThresholds(grid) {
  const vals = grid.flat().filter((v) => v > 0).sort((a, b) => a - b);
  if (!vals.length) return [];
  const q = [];
  for (let k = 1; k < HEAT_BINS; k++) q.push(vals[Math.min(vals.length - 1, Math.floor((k / HEAT_BINS) * vals.length))]);
  return q;
}

function binOf(v, thresholds) {
  let k = 0;
  while (k < thresholds.length && v > thresholds[k]) k++;
  return k;
}

/** Diff a candidate layout against the baseline. */
export function layoutDiff(base, cand) {
  const out = { addedSlots: {}, removedSlots: {}, movedCats: new Set() };
  if (!cand) return out;
  for (const [slot, cat] of Object.entries(cand.displays || {})) if (base.displays?.[slot] !== cat) out.addedSlots[slot] = cat;
  for (const [slot, cat] of Object.entries(base.displays || {})) if (!(slot in (cand.displays || {}))) out.removedSlots[slot] = cat;
  for (const [cat, slot] of Object.entries(cand.category_slot || {})) if (base.category_slot?.[cat] !== slot) out.movedCats.add(cat);
  return out;
}

/** Ids of shoppers who walk somewhere different (by 1 m floor cells, ignoring timing) between two layouts. */
export function changedRoutes(baseTracks, candTracks, minCells = 3) {
  const cells = (pts) => new Set(pts.map((p) => `${Math.floor(p[1])},${Math.floor(p[2])}`));
  const base = new Map(baseTracks.map((t) => [t.id, cells(t.points)]));
  const out = new Set();
  for (const t of candTracks) {
    const b = base.get(t.id);
    if (!b) { out.add(t.id); continue; }
    const c = cells(t.points);
    let diff = 0;
    for (const k of c) if (!b.has(k)) diff++;
    for (const k of b) if (!c.has(k)) diff++;
    if (diff >= minCells) out.add(t.id);
  }
  return out;
}

/**
 * Render a floor plan.
 * opts: { mini, layout, baseline, target, selected, onZoneClick, title }
 */
export function renderFloor(container, store, opts = {}) {
  const mini = !!opts.mini;
  const layout = opts.layout || store.baseline_layout;
  const base = opts.baseline || store.baseline_layout;
  const diff = layoutDiff(base, opts.layout && opts.layout !== base ? opts.layout : null);
  const slotCat = {};
  for (const [cat, slot] of Object.entries(layout.category_slot)) slotCat[slot] = cat;
  const pad = 0.35;
  const W = store.width, H = store.height;
  container.innerHTML = '';
  const svg = s('svg', {
    viewBox: `${-pad} ${-pad} ${W + 2 * pad} ${H + 2 * pad}`,
    class: 'floor-svg' + (mini ? ' mini' : ''), role: 'img', 'aria-label': opts.title || `Floor plan of ${store.name}`,
  });
  container.appendChild(svg);
  const fs = mini ? { cat: 0.95, small: 0, slot: 0.62 } : { cat: 0.62, small: 0.32, slot: 0.3 };

  s('rect', { x: 0, y: 0, width: W, height: H, class: 'fp-floor' }, svg);
  const gZones = s('g', {}, svg);
  const gHeat = s('g', { class: 'fp-heat' }, svg);
  const gFix = s('g', {}, svg);
  const gSlots = s('g', {}, svg);
  const gLabels = s('g', {}, svg);
  const gPart = s('g', {}, svg);
  const gPins = s('g', {}, svg);
  s('rect', { x: 0, y: 0, width: W, height: H, class: 'fp-wall' }, svg);

  const zoneEls = {};   // by slot / area id
  const catEls = {};    // by category
  const centers = {};
  for (const key of ['entrance', 'checkout', 'exit']) {
    const r = store.areas[key];
    zoneEls[key] = s('rect', rectAttrs(r, { class: 'fp-area', rx: 0.15 }), gZones);
    centers[key] = key === 'checkout' ? [r.x1 - 1.0, (r.y0 + r.y1) / 2 - 0.1] : [(r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2];
  }
  for (const a of store.aisles) {
    const cat = slotCat[a.id];
    const cls = ['fp-zone'];
    if (opts.onZoneClick) cls.push('clickable');
    if (cat && cat === opts.target) cls.push('target');
    if (cat && diff.movedCats.has(cat)) cls.push('swapped');
    const z = s('rect', rectAttrs(a, { class: cls.join(' '), rx: 0.12, tabindex: opts.onZoneClick ? 0 : null }), gZones);
    if (opts.onZoneClick && cat) {
      z.setAttribute('role', 'button');
      z.setAttribute('aria-label', `${CAT_LABEL[cat]} aisle`);
      z.addEventListener('click', () => opts.onZoneClick(cat));
      z.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); opts.onZoneClick(cat); } });
    }
    zoneEls[a.id] = z;
    if (cat) catEls[cat] = z;
    const cx = (a.x0 + a.x1) / 2, cy = (a.y0 + a.y1) / 2;
    centers[a.id] = [cx, a.y0 + 1.35];
    if (cat) {
      const label = (CAT_LABEL[cat] || cat).toUpperCase() + (diff.movedCats.has(cat) ? ' ⇄' : '');
      s('text', mini
        ? { x: cx, y: cy, 'text-anchor': 'middle', 'dominant-baseline': 'middle', 'font-size': fs.cat, transform: `rotate(-90 ${cx} ${cy})` }
        : { x: cx, y: cy + 0.3, 'text-anchor': 'middle', 'dominant-baseline': 'middle', 'font-size': fs.cat },
      gLabels, label).setAttribute('class', diff.movedCats.has(cat) ? 'fp-label-change' : 'fp-label');
    }
    if (fs.small) {
      s('text', { x: cx, y: a.y1 - 0.45, 'text-anchor': 'middle', 'font-size': fs.small, class: 'fp-label-muted' }, gLabels,
        a.label.toUpperCase());
    }
  }
  for (const f of store.fixtures) s('rect', rectAttrs(f, { class: 'fp-fixture' + (f.kind === 'cooler' ? ' cooler' : ''), rx: 0.08 }), gFix);
  s('rect', rectAttrs(store.areas.entrance_door, { class: 'fp-door' }), gFix);
  s('rect', rectAttrs(store.areas.exit_door, { class: 'fp-door' }), gFix);
  if (fs.small) {
    const lab = (r, text, dy = 0) => s('text', { x: (r.x0 + r.x1) / 2, y: (r.y0 + r.y1) / 2 + dy, 'text-anchor': 'middle',
      'dominant-baseline': 'middle', 'font-size': fs.small + 0.04, class: 'fp-label-muted' }, gLabels, text);
    lab(store.areas.entrance, 'ENTRANCE', 0.9);
    lab(store.areas.exit, 'EXIT', 0.6);
    const co = store.areas.checkout;
    s('text', { x: co.x0 + 0.4, y: co.y0 + 0.55, 'font-size': fs.small + 0.04, class: 'fp-label-muted' }, gLabels, 'CHECKOUT');
  }
  for (const d of store.displays) {
    const cat = layout.displays[d.id];
    const added = diff.addedSlots[d.id];
    const removed = diff.removedSlots[d.id];
    let cls = 'fp-slot';
    if (added) cls += ' changed';
    else if (removed) cls += ' removed';
    else if (cat) cls += ' occupied';
    else if (d.restricted) cls += ' restricted';
    const r = s('rect', rectAttrs(d, { class: cls, rx: 0.06 }), gSlots);
    s('title', {}, r).textContent = `${d.label}${cat ? ` · ${CAT_LABEL[cat]} promo` : ''}${d.restricted ? ' · keep clear (emergency exit)' : ''}`;
    if (added) s('circle', { cx: (d.x0 + d.x1) / 2, cy: (d.y0 + d.y1) / 2, r: mini ? 1.05 : 0.85, class: 'fp-ring' }, gSlots);
    const showLabel = (!mini && (cat || added || removed)) || (mini && (added || removed));
    if (showLabel) {
      const cx = (d.x0 + d.x1) / 2;
      let y = d.y0 > 11 ? d.y0 - 0.25 : d.y1 + (mini ? 0.8 : 0.45);
      if (d.y1 <= 2.6) y = d.y0 - 0.22;
      const text = added ? `+ ${CAT_LABEL[added]}` : removed ? `− ${CAT_LABEL[removed]}` : `${CAT_LABEL[cat]} promo`;
      s('text', { x: cx, y, 'text-anchor': 'middle', 'font-size': fs.slot, class: added || removed ? 'fp-label-change' : 'fp-label-2' },
        gLabels, text);
    }
  }

  const api = {
    svg,
    setSelected(cat) {
      for (const [c, el] of Object.entries(catEls)) el.classList.toggle('selected', c === cat);
    },
    highlight(ids, kind) {
      for (const el of Object.values(zoneEls)) el.classList.remove('hl-opportunity', 'hl-friction', 'hl-pattern');
      for (const id of ids || []) zoneEls[id]?.classList.add('hl-' + kind);
    },
    pins(list) {
      gPins.innerHTML = '';
      for (const p of list) {
        const c = centers[p.zone];
        if (!c) continue;
        const g = s('g', { class: `fp-pin ${p.kind}`, tabindex: 0, role: 'button', 'aria-label': p.label }, gPins);
        s('circle', { cx: c[0], cy: c[1], r: 0.62 }, g);
        s('text', { x: c[0], y: c[1] + 0.02, 'text-anchor': 'middle', 'dominant-baseline': 'middle', 'font-size': 0.62 }, g, String(p.n));
        if (p.onClick) {
          g.addEventListener('click', p.onClick);
          g.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); p.onClick(); } });
        }
        if (p.onHover) {
          g.addEventListener('mouseenter', () => p.onHover(true));
          g.addEventListener('mouseleave', () => p.onHover(false));
        }
      }
    },
    setHeat(grid, thresholds, units = 'shopper-seconds per day') {
      gHeat.innerHTML = '';
      svg.classList.toggle('heat-on', !!grid);
      svg.onmousemove = null;
      svg.onmouseleave = null;
      if (!grid) return;
      const th = thresholds || heatThresholds(grid);
      const cell = store.cell_m || 0.5;
      grid.forEach((row, r) => row.forEach((v, c) => {
        if (v > 0) s('rect', { x: c * cell, y: r * cell, width: cell + 0.01, height: cell + 0.01, class: 'h' + binOf(v, th), opacity: 0.85 }, gHeat);
      }));
      svg.onmousemove = (e) => {
        const pt = svg.createSVGPoint();
        pt.x = e.clientX; pt.y = e.clientY;
        const p = pt.matrixTransform(svg.getScreenCTM().inverse());
        const v = grid[Math.floor(p.y / cell)]?.[Math.floor(p.x / cell)];
        if (v === undefined) { hideTip(); return; }
        showTip(`<b>${fmtInt(v)}</b> ${units}`, e.clientX, e.clientY);
      };
      svg.onmouseleave = hideTip;
    },
    particles(tracks, o = {}) {
      return new Particles(gPart, tracks, { radius: mini ? 0.4 : 0.26, ...o });
    },
  };
  if (opts.selected) api.setSelected(opts.selected);
  return api;
}

export class Particles {
  constructor(group, tracks, { radius = 0.26, speed = 30, onTick = null, window = null, changed = null } = {}) {
    this.g = group;
    this.tracks = tracks.filter((t) => t.points.length >= 2);
    this.speed = speed;
    this.onTick = onTick;
    this.duration = window || Math.max(60, ...this.tracks.map((t) => t.points[t.points.length - 1][0]));
    this.t = 0;
    this.running = false;
    this.last = null;
    this.g.innerHTML = '';
    this.dots = this.tracks.map((t) => {
      const kind = changed && changed.has(t.id) ? 'changed' : t.bought ? 'buyer' : 'browser';
      return s('circle', { r: kind === 'changed' ? radius * 1.15 : radius, class: 'particle ' + kind, visibility: 'hidden' }, this.g);
    });
    this.idx = this.tracks.map(() => 0);
    this.frame = this.frame.bind(this);
    this.render();
  }
  start() {
    if (this.running) return;
    this.running = true;
    this.last = null;
    requestAnimationFrame(this.frame);
  }
  stop() { this.running = false; }
  toggle() { this.running ? this.stop() : this.start(); return this.running; }
  frame(ts) {
    if (!this.running) return;
    if (!this.g.isConnected) { this.running = false; return; }
    if (this.last !== null) {
      this.t += ((ts - this.last) / 1000) * this.speed;
      if (this.t > this.duration) { this.t = 0; this.idx.fill(0); }
    }
    this.last = ts;
    this.render();
    requestAnimationFrame(this.frame);
  }
  render() {
    const t = this.t;
    this.tracks.forEach((tr, k) => {
      const p = tr.points;
      const dot = this.dots[k];
      if (t < p[0][0] || t > p[p.length - 1][0]) { dot.setAttribute('visibility', 'hidden'); return; }
      let i = this.idx[k];
      if (p[i][0] > t) i = 0;
      while (i < p.length - 2 && p[i + 1][0] < t) i++;
      this.idx[k] = i;
      const a = p[i], b = p[i + 1];
      const f = b[0] > a[0] ? (t - a[0]) / (b[0] - a[0]) : 0;
      dot.setAttribute('cx', (a[1] + (b[1] - a[1]) * f).toFixed(2));
      dot.setAttribute('cy', (a[2] + (b[2] - a[2]) * f).toFixed(2));
      dot.setAttribute('visibility', 'visible');
    });
    if (this.onTick) this.onTick(t);
  }
}
