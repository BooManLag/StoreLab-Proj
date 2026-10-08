// How an experiment is presented to a manager: impact range, risk level, cost — derived from the numbers, never asserted.
import { fmtPeso, fmtSigned } from './format';
import type { Candidate } from '../api/labTypes';

const r0 = (x: number) => Math.round(x);

/** "+14–19%" (or "−1% to +4%" when the range crosses zero). */
export function rangeText(lo: number, hi: number): string {
  const a = r0(lo), b = r0(hi);
  if (a === b) return fmtSigned(a, 0);
  if (a >= 0 && b >= 0) return `+${a}–${b}%`;
  if (a <= 0 && b <= 0) return `−${Math.abs(b)}–${Math.abs(a)}%`;
  return `${fmtSigned(a, 0)} to ${fmtSigned(b, 0)}`;
}

export interface Risk {
  cls: 'bad' | 'risk' | 'good';
  icon: string;
  text: string;
  detail: string;
}

/** Risk is derived, never asserted: a constraint breach outranks a congestion range touching the limit outranks low risk. */
export function risk(c: Candidate, tolerance: number): Risk {
  if (!c.valid) return { cls: 'bad', icon: '✕', text: 'Not allowed', detail: c.errors[0] ?? '' };
  if (c.status === 'rejected') return { cls: 'bad', icon: '✕', text: 'Breaks a limit', detail: c.verdict_reason ?? '' };
  const cong = c.simulation?.deltas.congestion;
  if (c.gate?.at_risk || (cong && cong.ci_high_pct > tolerance)) {
    return { cls: 'risk', icon: '▲', text: 'Watch checkout queue', detail: `Congestion could reach ${fmtSigned(cong?.ci_high_pct ?? 0)} (limit +${tolerance}%).` };
  }
  return { cls: 'good', icon: '✓', text: 'Low risk', detail: cong ? `Checkout congestion ${fmtSigned(cong.relative_pct)} (limit +${tolerance}%).` : '' };
}

export interface Impact {
  label: string;
  point: number;
  range: string;
}

export function impact(c: Candidate): Impact | null {
  const p = c.simulation?.deltas.primary;
  if (!p) return null;
  return { label: p.label, point: p.relative_pct, range: rangeText(p.ci_low_pct, p.ci_high_pct) };
}

export const costText = (c: Candidate): string => fmtPeso(c.cost);

/** A plain-language reason a rejected candidate didn't make it. */
export function plainReason(c: Candidate): string {
  if (!c.valid) return 'Not allowed in this store: ' + (c.errors[0] ?? '');
  const d = c.simulation?.deltas;
  if (c.gate && !c.gate.passed && d && /congestion/i.test(c.gate.reason)) {
    const allowed = c.gate.reason.match(/\+([\d.]+)% allowed/)?.[1] ?? '';
    return `Would make the checkout queue ${fmtSigned(d.congestion.relative_pct)} busier (your limit is +${allowed}%), even though it lifts ${d.primary.label.toLowerCase()} ${fmtSigned(d.primary.relative_pct)}.`;
  }
  if (d && d.primary.relative_pct <= 0) return `Didn't improve ${d.primary.label.toLowerCase()} (${fmtSigned(d.primary.relative_pct)}).`;
  return c.verdict_reason ?? 'Rejected.';
}
