// How an experiment is presented to a manager: impact range, risk level, cost — derived from the numbers.
import { fmtPeso } from './util.js';

const r0 = (x) => Math.round(x);
const signed = (x) => (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(r0(x));

/** "+14–19%" (or "−1% to +4%" when the range crosses zero). */
export function rangeText(lo, hi) {
  const a = r0(lo), b = r0(hi);
  if (a === b) return `${signed(a)}%`;
  if (a >= 0 && b >= 0) return `+${a}–${b}%`;
  if (a <= 0 && b <= 0) return `−${Math.abs(b)}–${Math.abs(a)}%`;
  return `${signed(a)}% to ${signed(b)}%`;
}

export function pointText(x, digits = 1) {
  return (x >= 0 ? '+' : '−') + Math.abs(x).toFixed(digits) + '%';
}

/** Risk is derived, never asserted: constraint breach > congestion range touching the limit > low. */
export function risk(c, tolerance) {
  if (!c.valid) return { cls: 'bad', icon: '✕', text: 'Not allowed', detail: (c.errors || [])[0] || '' };
  if (c.status === 'rejected') return { cls: 'bad', icon: '✕', text: 'Breaks a limit', detail: c.verdict_reason || '' };
  const cong = c.simulation?.deltas?.congestion;
  if (c.gate?.at_risk || (cong && cong.ci_high_pct > tolerance)) {
    return { cls: 'risk', icon: '▲', text: 'Watch checkout queue', detail: `Congestion could reach ${pointText(cong.ci_high_pct)} (limit +${tolerance}%).` };
  }
  return { cls: 'good', icon: '✓', text: 'Low risk', detail: cong ? `Checkout congestion ${pointText(cong.relative_pct)} (limit +${tolerance}%).` : '' };
}

export function impact(c) {
  const p = c.simulation?.deltas?.primary;
  if (!p) return null;
  return { label: p.label, point: p.relative_pct, range: rangeText(p.ci_low_pct, p.ci_high_pct), lo: p.ci_low_pct, hi: p.ci_high_pct };
}

export const costText = (c) => fmtPeso(c.cost);

export function tagHTML(r) {
  return `<span class="tag ${r.cls}"><span class="ico" aria-hidden="true">${r.icon}</span>${r.text}</span>`;
}
