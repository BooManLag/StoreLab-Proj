import * as THREE from 'three';
import type { JourneyTrack } from '../api/storeTypes';

const HIDDEN_Y = -50; // below the floor, outside the camera's shallow downward view — cheap "hide" without touching material state

/** A soft circular sprite so shopper dots read as dots, not squares. */
function dotSprite(): THREE.CanvasTexture {
  const size = 64;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, 'rgba(255,255,255,1)');
  gradient.addColorStop(0.8, 'rgba(255,255,255,1)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

export interface ShopperParticlesOptions {
  /** Store-meters → world (x, z). Keeps the coordinate convention in one place (StoreScene). */
  toWorldXZ: (x: number, y: number) => [number, number];
  radius?: number;
  /** Playback speed multiplier — the old app replays at 30x so a 40-minute window is watchable. */
  speed?: number;
  window?: number;
  changed?: Set<JourneyTrack['id']>;
  colors: { buyer: THREE.ColorRepresentation; browser: THREE.ColorRepresentation; changed: THREE.ColorRepresentation };
  onTick?: (t: number) => void;
}

/** Animated anonymous shopper dots, replaying real recorded trajectories — not a procedural loop. */
export class ShopperParticles {
  readonly points: THREE.Points;
  private tracks: JourneyTrack[];
  private readonly duration: number;
  private readonly speed: number;
  private readonly onTick?: (t: number) => void;
  private readonly cursor: number[];
  private t = 0;
  running = false;
  private readonly positions: Float32Array;
  private readonly geometry: THREE.BufferGeometry;
  private readonly material: THREE.PointsMaterial;
  private readonly sprite: THREE.CanvasTexture;

  constructor(tracks: JourneyTrack[], opts: ShopperParticlesOptions) {
    this.tracks = tracks.filter((t) => t.points.length >= 2);
    this.speed = opts.speed ?? 30;
    this.onTick = opts.onTick;
    this.duration = opts.window || Math.max(60, ...this.tracks.map((t) => t.points[t.points.length - 1][0]));
    this.cursor = this.tracks.map(() => 0);

    const n = this.tracks.length;
    this.positions = new Float32Array(n * 3);
    const colors = new Float32Array(n * 3);
    const color = new THREE.Color();
    this.tracks.forEach((t, i) => {
      const kind = opts.changed?.has(t.id) ? 'changed' : t.bought ? 'buyer' : 'browser';
      color.set(opts.colors[kind]);
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
      this.positions[i * 3 + 1] = HIDDEN_Y;
    });

    this.geometry = new THREE.BufferGeometry();
    this.geometry.setAttribute('position', new THREE.BufferAttribute(this.positions, 3));
    this.geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    this.sprite = dotSprite();
    this.material = new THREE.PointsMaterial({
      size: (opts.radius ?? 0.26) * 2,
      map: this.sprite,
      vertexColors: true,
      transparent: true,
      depthWrite: false,
      sizeAttenuation: true,
    });

    this.points = new THREE.Points(this.geometry, this.material);
    this.render(opts.toWorldXZ);
  }

  start() { this.running = true; }
  stop() { this.running = false; }
  toggle(): boolean { this.running = !this.running; return this.running; }

  /** Called once per frame from the scene's own render loop — no independent rAF here. */
  update(deltaSeconds: number, toWorldXZ: (x: number, y: number) => [number, number]) {
    if (!this.running) return;
    this.t += deltaSeconds * this.speed;
    if (this.t > this.duration) { this.t = 0; this.cursor.fill(0); }
    this.render(toWorldXZ);
  }

  private render(toWorldXZ: (x: number, y: number) => [number, number]) {
    const t = this.t;
    this.tracks.forEach((tr, i) => {
      const p = tr.points;
      if (t < p[0][0] || t > p[p.length - 1][0]) {
        this.positions[i * 3 + 1] = HIDDEN_Y;
        return;
      }
      let idx = this.cursor[i];
      if (p[idx][0] > t) idx = 0;
      while (idx < p.length - 2 && p[idx + 1][0] < t) idx++;
      this.cursor[i] = idx;
      const a = p[idx], b = p[idx + 1];
      const f = b[0] > a[0] ? (t - a[0]) / (b[0] - a[0]) : 0;
      const x = a[1] + (b[1] - a[1]) * f;
      const y = a[2] + (b[2] - a[2]) * f;
      const [wx, wz] = toWorldXZ(x, y);
      this.positions[i * 3] = wx;
      this.positions[i * 3 + 1] = 0.3; // a shopper-height dot, just above fixtures' shadow catch
      this.positions[i * 3 + 2] = wz;
    });
    this.geometry.attributes.position.needsUpdate = true;
    this.onTick?.(t);
  }

  dispose() {
    this.geometry.dispose();
    this.material.dispose();
    this.sprite.dispose();
  }
}
