export const fmtInt = (n: number | null | undefined): string => (n == null ? '–' : Math.round(n).toLocaleString('en-US'));
export const fmtPeso = (n: number | null | undefined): string => (n == null ? '–' : '₱' + Math.round(n).toLocaleString('en-US'));
export const fmtPct = (x: number | null | undefined, digits = 1): string => (x == null ? '–' : (100 * x).toFixed(digits) + '%');
export const fmtSigned = (p: number | null | undefined, digits = 1): string =>
  p == null ? '–' : (p >= 0 ? '+' : '−') + Math.abs(p).toFixed(digits) + '%';

export const pad2 = (n: number): string => String(n).padStart(2, '0');

/** Seconds since midnight → "HH:MM", wrapping past 24h (store data runs past midnight on some days). */
export function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${pad2(Math.floor(s / 3600) % 24)}:${pad2(Math.floor((s % 3600) / 60))}`;
}

export const CAT_SINGULAR: Record<string, string> = { bakery: 'bakery', coffee: 'coffee', snacks: 'snack', beverages: 'beverage' };
export const CAT_LABEL: Record<string, string> = { bakery: 'Bakery', coffee: 'Coffee', snacks: 'Snacks', beverages: 'Beverages' };
