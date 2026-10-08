import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import type { JourneyTrack } from '../api/storeTypes';

const HIDDEN_SCALE = 0.0001; // Effectively invisible while outside the track's time window, without touching material/visible state per-instance.
const BOB_FREQ = 7; // steps/sec read as a walk cadence at the default 30x replay speed.
const BOB_AMOUNT = 0.035;
const LEAN_MAX = 0.12; // radians of forward lean at full stride — subtle, not a cartoon wobble.
const MOVE_EPS = 0.01; // m/s² (already scaled by dt) below which a shopper reads as "standing", not walking.

/** A low-poly standing figure — capsule body + sphere head, base at y=0. ~1.5 m tall, one merged geometry so each instance is a single draw-call unit. */
function buildPersonGeometry(): THREE.BufferGeometry {
  const bodyRadius = 0.16;
  const bodyLength = 0.9;
  const body = new THREE.CapsuleGeometry(bodyRadius, bodyLength, 4, 8);
  const bodyHalf = bodyRadius + bodyLength / 2;
  body.translate(0, bodyHalf, 0);

  const headRadius = 0.13;
  const head = new THREE.SphereGeometry(headRadius, 10, 8);
  head.translate(0, bodyHalf * 2 + headRadius + 0.03, 0);

  return mergeGeometries([body, head], false) ?? body;
}

/** A small carried basket — only instanced for shoppers who bought, so "who converted" reads at a glance, not just by dot color. */
function buildBasketGeometry(): THREE.BufferGeometry {
  return new THREE.BoxGeometry(0.16, 0.12, 0.11);
}

export interface ShopperParticlesOptions {
  /** Store-meters → world (x, z). Keeps the coordinate convention in one place (StoreScene). */
  toWorldXZ: (x: number, y: number) => [number, number];
  /** Playback speed multiplier — the old app replays at 30x so a 40-minute window is watchable. */
  speed?: number;
  window?: number;
  changed?: Set<JourneyTrack['id']>;
  colors: { buyer: THREE.ColorRepresentation; browser: THREE.ColorRepresentation; changed: THREE.ColorRepresentation };
  basketColor?: THREE.ColorRepresentation;
  onTick?: (t: number) => void;
}

/** Animated anonymous shoppers, replaying real recorded trajectories as little standing figures — not a procedural loop. */
export class ShopperParticles {
  /** Added to / removed from the scene as one unit (person mesh + basket mesh). */
  readonly object: THREE.Group;
  private tracks: JourneyTrack[];
  private readonly duration: number;
  private readonly speed: number;
  private readonly onTick?: (t: number) => void;
  private readonly cursor: number[];
  private t = 0;
  running = false;

  private readonly personGeometry: THREE.BufferGeometry;
  private readonly personMaterial: THREE.MeshStandardMaterial;
  private readonly personMesh: THREE.InstancedMesh;

  private readonly basketGeometry: THREE.BufferGeometry;
  private readonly basketMaterial: THREE.MeshStandardMaterial;
  private readonly basketMesh: THREE.InstancedMesh;
  /** Index into `tracks` for each basket instance — baskets are a sparse subset (bought-only). */
  private readonly basketOwner: number[];

  private readonly phase: Float32Array; // per-track bob-cycle offset, desyncs the crowd
  private readonly scale: Float32Array; // per-track height variance
  private readonly heading: Float32Array; // last known facing angle, held steady while standing still

  private readonly dummy = new THREE.Object3D();
  private readonly quat = new THREE.Quaternion();
  private readonly euler = new THREE.Euler();

  constructor(tracks: JourneyTrack[], opts: ShopperParticlesOptions) {
    this.tracks = tracks.filter((t) => t.points.length >= 2);
    this.speed = opts.speed ?? 30;
    this.onTick = opts.onTick;
    this.duration = opts.window || Math.max(60, ...this.tracks.map((t) => t.points[t.points.length - 1][0]));
    this.cursor = this.tracks.map(() => 0);

    const n = this.tracks.length;
    this.phase = new Float32Array(n).map(() => Math.random() * Math.PI * 2);
    this.scale = new Float32Array(n).map(() => 0.88 + Math.random() * 0.28);
    this.heading = new Float32Array(n);

    this.personGeometry = buildPersonGeometry();
    this.personMaterial = new THREE.MeshStandardMaterial({ roughness: 0.65, metalness: 0.05 });
    this.personMesh = new THREE.InstancedMesh(this.personGeometry, this.personMaterial, Math.max(1, n));
    this.personMesh.castShadow = true;
    this.personMesh.receiveShadow = false;

    const color = new THREE.Color();
    this.tracks.forEach((t, i) => {
      const kind = opts.changed?.has(t.id) ? 'changed' : t.bought ? 'buyer' : 'browser';
      color.set(opts.colors[kind]);
      this.personMesh.setColorAt(i, color);
    });
    if (this.personMesh.instanceColor) this.personMesh.instanceColor.needsUpdate = true;

    this.basketOwner = this.tracks.reduce<number[]>((acc, t, i) => { if (t.bought) acc.push(i); return acc; }, []);
    this.basketGeometry = buildBasketGeometry();
    this.basketMaterial = new THREE.MeshStandardMaterial({
      color: opts.basketColor ?? opts.colors.buyer, roughness: 0.5, metalness: 0.1,
    });
    this.basketMesh = new THREE.InstancedMesh(this.basketGeometry, this.basketMaterial, Math.max(1, this.basketOwner.length));
    this.basketMesh.castShadow = true;

    this.object = new THREE.Group();
    this.object.add(this.personMesh, this.basketMesh);

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
    let basketIdx = 0;
    this.tracks.forEach((tr, i) => {
      const p = tr.points;
      if (t < p[0][0] || t > p[p.length - 1][0]) {
        this.dummy.position.set(0, -2, 0);
        this.dummy.quaternion.identity();
        this.dummy.scale.setScalar(HIDDEN_SCALE);
        this.dummy.updateMatrix();
        this.personMesh.setMatrixAt(i, this.dummy.matrix);
        if (tr.bought) {
          this.basketMesh.setMatrixAt(basketIdx, this.dummy.matrix);
          basketIdx++;
        }
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

      const dx = b[1] - a[1], dz = b[2] - a[2];
      const moving = dx * dx + dz * dz > MOVE_EPS * MOVE_EPS;
      if (moving) this.heading[i] = Math.atan2(dx, dz);

      const phase = t * BOB_FREQ * 0.2 + this.phase[i];
      const bobY = moving ? Math.abs(Math.sin(phase)) * BOB_AMOUNT : 0;
      const lean = moving ? Math.sin(phase * 2) * LEAN_MAX : 0;

      this.euler.set(lean, this.heading[i], 0, 'YXZ');
      this.quat.setFromEuler(this.euler);
      this.dummy.position.set(wx, bobY, wz);
      this.dummy.quaternion.copy(this.quat);
      this.dummy.scale.setScalar(this.scale[i]);
      this.dummy.updateMatrix();
      this.personMesh.setMatrixAt(i, this.dummy.matrix);

      if (tr.bought) {
        const hipOffset = new THREE.Vector3(0.24, 0.55, 0).applyQuaternion(this.quat);
        this.dummy.position.set(wx + hipOffset.x, bobY + hipOffset.y, wz + hipOffset.z);
        this.dummy.updateMatrix();
        this.basketMesh.setMatrixAt(basketIdx, this.dummy.matrix);
        basketIdx++;
      }
    });
    this.personMesh.instanceMatrix.needsUpdate = true;
    this.basketMesh.instanceMatrix.needsUpdate = true;
    this.onTick?.(t);
  }

  dispose() {
    this.personGeometry.dispose();
    this.personMaterial.dispose();
    this.basketGeometry.dispose();
    this.basketMaterial.dispose();
  }
}
