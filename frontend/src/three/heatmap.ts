import * as THREE from 'three';

const HEAT_BINS = 7;

/** Same quantile-binning as the old SVG floorplan (floorplan.js) — 7 bins, computed from the data itself. */
export function heatThresholds(grid: number[][]): number[] {
  const vals = grid.flat().filter((v) => v > 0).sort((a, b) => a - b);
  if (!vals.length) return [];
  const q: number[] = [];
  for (let k = 1; k < HEAT_BINS; k++) q.push(vals[Math.min(vals.length - 1, Math.floor((k / HEAT_BINS) * vals.length))]);
  return q;
}

function binOf(v: number, thresholds: number[]): number {
  let k = 0;
  while (k < thresholds.length && v > thresholds[k]) k++;
  return k;
}

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.replace('#', ''), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/**
 * Renders the visit-density grid to a canvas texture as a proper density
 * heatmap: each populated cell is a soft radial blob (same quantile bin/color
 * as before — no fabricated values), not a hard block or a globally-blurred
 * haze. Cells are painted coolest-first so hot spots stay as visible peaks
 * instead of smearing into their neighbors.
 */
export function buildHeatTexture(
  grid: number[][],
  thresholds: number[],
  heatColors: string[],
): THREE.CanvasTexture {
  const rows = grid.length;
  const cols = rows ? grid[0].length : 0;
  const cellPx = Math.max(6, Math.min(28, Math.floor(1024 / Math.max(rows, cols, 1))));
  const w = Math.max(1, cols * cellPx);
  const h = Math.max(1, rows * cellPx);

  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d')!;

  const cells: { r: number; c: number; v: number }[] = [];
  grid.forEach((row, r) => row.forEach((v, c) => { if (v > 0) cells.push({ r, c, v }); }));
  cells.sort((a, b) => a.v - b.v); // hottest painted last, so peaks stay on top

  const radius = cellPx * 1.4;
  for (const { r, c, v } of cells) {
    const cx = c * cellPx + cellPx / 2;
    const cy = r * cellPx + cellPx / 2;
    const [cr, cg, cb] = hexToRgb(heatColors[binOf(v, thresholds)] ?? heatColors[heatColors.length - 1]);
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    grad.addColorStop(0, `rgba(${cr},${cg},${cb},0.95)`);
    grad.addColorStop(0.5, `rgba(${cr},${cg},${cb},0.55)`);
    grad.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}
