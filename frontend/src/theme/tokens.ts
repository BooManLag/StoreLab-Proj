/**
 * Reads src/styles/tokens.css custom properties at runtime, for the one
 * place that can't use `var(...)` directly: Three.js materials/lights,
 * which need resolved values, not CSS strings. Reading live (rather than
 * hardcoding a second copy of the palette here) means light/dark and any
 * `data-theme` override stay a single source of truth in the CSS file.
 */

const COLOR_KEYS = [
  'paper', 'surface', 'surface-2', 'surface-3',
  'ink', 'ink-muted', 'subtle', 'grid', 'axis',
  'insight', 'insight-text', 'proof', 'proof-text', 'amber', 'amber-text', 'red', 'red-text',
  'change',
  'floor', 'zone', 'fixture', 'particle-buyer', 'particle-browser',
  'heat-0', 'heat-1', 'heat-2', 'heat-3', 'heat-4', 'heat-5', 'heat-6',
] as const;

type ColorKey = (typeof COLOR_KEYS)[number];

export interface DesignTokens {
  color: Record<ColorKey, string>;
  durationMicroMs: number;
  durationMeaningfulMs: number;
}

function cssMs(value: string): number {
  const v = value.trim();
  return v.endsWith('ms') ? parseFloat(v) : parseFloat(v) * 1000;
}

/** Call after the stylesheet is loaded and any theme attribute is set — typically once, on scene setup. */
export function readDesignTokens(root: HTMLElement = document.documentElement): DesignTokens {
  const style = getComputedStyle(root);
  const color = {} as Record<ColorKey, string>;
  for (const key of COLOR_KEYS) {
    color[key] = style.getPropertyValue(`--color-${key}`).trim();
  }
  return {
    color,
    durationMicroMs: cssMs(style.getPropertyValue('--duration-micro')),
    durationMeaningfulMs: cssMs(style.getPropertyValue('--duration-meaningful')),
  };
}
