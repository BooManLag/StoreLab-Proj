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

/**
 * Renders the visit-density grid to a canvas texture, one block per cell —
 * deliberately blocky (NearestFilter), not interpolated: this is read data,
 * not a decorative gradient.
 */
export function buildHeatTexture(
  grid: number[][],
  thresholds: number[],
  heatColors: string[],
): THREE.CanvasTexture {
  const rows = grid.length;
  const cols = rows ? grid[0].length : 0;
  const cellPx = Math.max(2, Math.min(16, Math.floor(1024 / Math.max(rows, cols, 1))));
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, cols * cellPx);
  canvas.height = Math.max(1, rows * cellPx);
  const ctx = canvas.getContext('2d')!;
  grid.forEach((row, r) => {
    row.forEach((v, c) => {
      if (v <= 0) return;
      ctx.fillStyle = heatColors[binOf(v, thresholds)] ?? heatColors[heatColors.length - 1];
      ctx.fillRect(c * cellPx, r * cellPx, cellPx, cellPx);
    });
  });
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}
