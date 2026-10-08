import * as THREE from 'three';
import type { DesignTokens } from '../theme/tokens';

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.replace('#', ''), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgbToHex(r: number, g: number, b: number): string {
  const c = (v: number) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0');
  return `#${c(r)}${c(g)}${c(b)}`;
}

/** Lightens (amt > 0) or darkens (amt < 0) a hex color toward white/black — derives shelf/grout shades from existing tokens instead of hardcoding new ones. */
export function shade(hex: string, amt: number): string {
  const [r, g, b] = hexToRgb(hex);
  const target = amt > 0 ? 255 : 0;
  const f = Math.abs(amt);
  return rgbToHex(r + (target - r) * f, g + (target - g) * f, b + (target - b) * f);
}

/**
 * A tileable mart-floor texture: square tiles with grout lines and a faint
 * fleck pattern, repeated via UV wrapping across the store footprint — so the
 * floor reads as finished terrazzo/vinyl flooring rather than a flat fill.
 * Colors derive from --color-floor so light/dark theme stays a single source of truth.
 */
export function buildFloorTexture(tokens: DesignTokens): THREE.CanvasTexture {
  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const base = tokens.color.floor;
  const grout = shade(base, -0.1);
  const fleckLight = shade(base, 0.07);
  const fleckDark = shade(base, -0.045);

  ctx.fillStyle = base;
  ctx.fillRect(0, 0, size, size);

  ctx.globalAlpha = 0.3;
  for (let i = 0; i < 140; i++) {
    ctx.fillStyle = Math.random() > 0.5 ? fleckLight : fleckDark;
    const s = 1 + Math.random() * 2.5;
    ctx.fillRect(Math.random() * size, Math.random() * size, s, s);
  }
  ctx.globalAlpha = 1;

  ctx.strokeStyle = grout;
  ctx.lineWidth = 3;
  ctx.strokeRect(1.5, 1.5, size - 3, size - 3);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.anisotropy = 4;
  texture.needsUpdate = true;
  return texture;
}

/** A tileable horizontal-plank texture for shelf boards and the checkout counter — reads as finished millwork, not a flat box. */
export function buildPlankTexture(tokens: DesignTokens): THREE.CanvasTexture {
  const w = 128;
  const h = 64;
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d')!;
  const base = tokens.color.fixture;

  ctx.fillStyle = base;
  ctx.fillRect(0, 0, w, h);

  const plankHeight = 16;
  for (let y = 0; y < h; y += plankHeight) {
    ctx.strokeStyle = shade(base, -0.22);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
    ctx.strokeStyle = shade(base, 0.12);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, y + 2);
    ctx.lineTo(w, y + 2);
    ctx.stroke();
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.needsUpdate = true;
  return texture;
}
