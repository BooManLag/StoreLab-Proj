import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import type { StoreGeometry, JourneyTrack, Layout } from '../api/storeTypes';
import { readDesignTokens } from '../theme/tokens';
import { heatThresholds, buildHeatTexture } from './heatmap';
import { ShopperParticles } from './particles';
import { layoutDiff } from '../lib/layoutDiff';
import './storeScene.css';

export type HighlightKind = 'opportunity' | 'friction' | 'pattern' | '';

export interface PinSpec {
  id: string;
  zone: string;
  n: number;
  kind: HighlightKind;
  label: string;
  onClick?: () => void;
  onHover?: (hovering: boolean) => void;
}

export interface StoreSceneOptions {
  onZoneClick?: (category: string) => void;
  onCellHover?: (info: { value: number; clientX: number; clientY: number } | null) => void;
}

const EMISSIVE = { opportunity: 'insight', pattern: 'insight', friction: 'amber', selected: 'ink' } as const;

/**
 * The Store screen's 3D floorplan — vanilla Three.js, lifecycle owned entirely by this
 * class (construct in useEffect, dispose() on unmount; see StoreMap.tsx). Mirrors the
 * old SVG floorplan's API shape (setSelected/highlight/setHeat/particles) so the
 * surrounding screen logic barely has to change shape, just its renderer.
 */
export class StoreScene {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly labelRenderer: CSS2DRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera: THREE.PerspectiveCamera;
  private readonly controls: OrbitControls;
  private readonly clock = new THREE.Clock();
  private readonly raycaster = new THREE.Raycaster();
  private readonly pointer = new THREE.Vector2();
  private readonly container: HTMLElement;
  private readonly tokens = readDesignTokens();

  private readonly aisleMeshes: THREE.Mesh[] = [];
  private readonly catMesh = new Map<string, THREE.Mesh>();
  private readonly centers = new Map<string, [number, number]>();
  private readonly pinLayer: CSS2DObject[] = [];
  private readonly aisleLabels: CSS2DObject[] = [];
  private readonly displayMeshes: THREE.Mesh[] = [];
  private currentLayout: Layout;
  private heatMesh: THREE.Mesh | null = null;
  private heatGrid: number[][] | null = null;
  private heatThresholdsCache: number[] = [];
  private particlesInstance: ShopperParticles | null = null;
  private selectedCat: string | null = null;
  private highlighted: { ids: string[]; kind: HighlightKind } = { ids: [], kind: '' };

  private readonly resizeObserver: ResizeObserver;
  private disposed = false;
  private rafId = 0;

  private readonly store: StoreGeometry;
  private readonly opts: StoreSceneOptions;
  private readonly W: number;
  private readonly H: number;

  constructor(container: HTMLElement, store: StoreGeometry, opts: StoreSceneOptions = {}) {
    this.container = container;
    this.store = store;
    this.opts = opts;
    this.W = store.width;
    this.H = store.height;
    this.currentLayout = store.baseline_layout;

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.NoToneMapping; // tokens are exact brand hex — no filmic hue shift
    this.renderer.domElement.style.display = 'block';
    container.appendChild(this.renderer.domElement);

    this.labelRenderer = new CSS2DRenderer();
    this.labelRenderer.domElement.style.position = 'absolute';
    this.labelRenderer.domElement.style.top = '0';
    this.labelRenderer.domElement.style.left = '0';
    this.labelRenderer.domElement.style.pointerEvents = 'none';
    container.appendChild(this.labelRenderer.domElement);

    const diag = Math.hypot(this.W, this.H);
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    this.camera.position.set(0, diag * 0.62, diag * 0.5);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.set(0, 0, 0);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.enablePan = false;
    this.controls.minDistance = diag * 0.35;
    this.controls.maxDistance = diag * 1.3;
    this.controls.minPolarAngle = Math.PI * 0.12;
    this.controls.maxPolarAngle = Math.PI * 0.48;
    this.controls.autoRotate = false; // interaction thesis: user-driven only, never an auto-rotating showroom sweep

    this.buildLighting();
    this.buildFloor();
    this.buildAreas();
    this.buildAisles();
    this.buildFixturesAndDoors();
    this.buildDisplaySlots();

    this.resize();
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);

    this.renderer.domElement.addEventListener('click', this.handleClick);
    this.renderer.domElement.addEventListener('pointermove', this.handlePointerMove);
    this.renderer.domElement.addEventListener('pointerleave', this.handlePointerLeave);

    this.animate();
  }

  // ---------------------------------------------------------------- coordinate mapping
  private toWorldXZ = (x: number, y: number): [number, number] => [x - this.W / 2, y - this.H / 2];

  // ---------------------------------------------------------------- scene construction
  private buildLighting() {
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const sun = new THREE.DirectionalLight(0xffffff, 0.8);
    const diag = Math.hypot(this.W, this.H);
    sun.position.set(diag * 0.3, diag * 0.6, diag * 0.2);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    sun.shadow.camera.left = -this.W;
    sun.shadow.camera.right = this.W;
    sun.shadow.camera.top = this.H;
    sun.shadow.camera.bottom = -this.H;
    sun.shadow.camera.near = 0.5;
    sun.shadow.camera.far = diag * 2;
    sun.shadow.bias = -0.0005;
    this.scene.add(sun);
  }

  private buildFloor() {
    const geo = new THREE.PlaneGeometry(this.W, this.H);
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.MeshStandardMaterial({ color: this.tokens.color.floor, roughness: 0.95, metalness: 0 });
    const floor = new THREE.Mesh(geo, mat);
    floor.receiveShadow = true;
    this.scene.add(floor);

    const [hw, hh] = [this.W / 2, this.H / 2];
    const pts = [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh], [-hw, -hh]].map(([x, z]) => new THREE.Vector3(x, 0.01, z));
    const wall = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: this.tokens.color['ink-muted'] }));
    this.scene.add(wall);
  }

  private flatRect(x0: number, y0: number, x1: number, y1: number, color: string, yPos: number, opacity = 1): THREE.Mesh {
    const w = x1 - x0, h = y1 - y0;
    const geo = new THREE.PlaneGeometry(w, h);
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.MeshBasicMaterial({ color, transparent: opacity < 1, opacity });
    const mesh = new THREE.Mesh(geo, mat);
    const [cx, cz] = this.toWorldXZ((x0 + x1) / 2, (y0 + y1) / 2);
    mesh.position.set(cx, yPos, cz);
    this.scene.add(mesh);
    return mesh;
  }

  private addLabel(text: string, x: number, z: number, y: number, className = 'sl-label'): CSS2DObject {
    const el = document.createElement('div');
    el.className = className;
    el.textContent = text;
    const obj = new CSS2DObject(el);
    obj.position.set(x, y, z);
    this.scene.add(obj);
    return obj;
  }

  /** Removes a mesh/line from the scene and disposes its geometry + material(s) + any texture map. */
  private disposeObject(obj: THREE.Mesh | THREE.Line) {
    this.scene.remove(obj);
    obj.geometry?.dispose();
    const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
    for (const m of mats) { (m as THREE.MeshBasicMaterial).map?.dispose(); m.dispose(); }
  }

  private buildAreas() {
    const s = this.store;
    for (const key of ['entrance', 'checkout', 'exit'] as const) {
      const r = s.areas[key];
      this.flatRect(r.x0, r.y0, r.x1, r.y1, this.tokens.color.zone, 0.004, 0.6);
      const center = key === 'checkout'
        ? this.toWorldXZ(r.x1 - 1.0, (r.y0 + r.y1) / 2 - 0.1)
        : this.toWorldXZ((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2);
      this.centers.set(key, center);
      this.addLabel(key.toUpperCase(), center[0], center[1], 0.1, 'sl-label area');
    }
  }

  /** (Re)builds the aisle meshes for `layout`, tinting any category whose slot differs from the baseline. */
  private buildAisles(layout: Layout = this.currentLayout) {
    for (const mesh of this.aisleMeshes) this.disposeObject(mesh);
    this.aisleMeshes.length = 0;
    this.catMesh.clear();
    for (const label of this.aisleLabels) label.element.remove();
    this.aisleLabels.length = 0;

    const diff = layoutDiff(this.store.baseline_layout, layout === this.store.baseline_layout ? null : layout);
    const slotCat: Record<string, string> = {};
    for (const [cat, slot] of Object.entries(layout.category_slot)) slotCat[slot] = cat;

    for (const a of this.store.aisles) {
      const cat = slotCat[a.id];
      const swapped = !!cat && diff.movedCats.has(cat);
      const w = a.x1 - a.x0, h = a.y1 - a.y0;
      const geo = new THREE.BoxGeometry(w, 0.04, h);
      const mat = new THREE.MeshStandardMaterial({
        color: this.tokens.color.zone, roughness: 0.9,
        emissive: swapped ? this.tokens.color.change : 0x000000, emissiveIntensity: 0.5,
      });
      const mesh = new THREE.Mesh(geo, mat);
      const [cx, cz] = this.toWorldXZ((a.x0 + a.x1) / 2, (a.y0 + a.y1) / 2);
      mesh.position.set(cx, 0.02, cz);
      mesh.receiveShadow = true;
      mesh.userData.category = cat ?? null;
      mesh.userData.aisleId = a.id;
      this.scene.add(mesh);
      this.aisleMeshes.push(mesh);
      if (cat) this.catMesh.set(cat, mesh);

      const labelCenter = this.toWorldXZ((a.x0 + a.x1) / 2, a.y0 + 1.35);
      this.centers.set(a.id, labelCenter);
      if (cat) this.aisleLabels.push(this.addLabel(`${cat.toUpperCase()}${swapped ? ' ⇄' : ''}`, labelCenter[0], labelCenter[1], 0.12));
    }
  }

  private buildFixturesAndDoors() {
    for (const f of this.store.fixtures) {
      const w = f.x1 - f.x0, d = f.y1 - f.y0;
      const isCooler = f.kind === 'cooler';
      const geo = new THREE.BoxGeometry(w, 0.9, d);
      const mat = new THREE.MeshStandardMaterial({
        color: this.tokens.color.fixture, roughness: 0.75,
        transparent: isCooler, opacity: isCooler ? 0.85 : 1,
      });
      const mesh = new THREE.Mesh(geo, mat);
      const [cx, cz] = this.toWorldXZ((f.x0 + f.x1) / 2, (f.y0 + f.y1) / 2);
      mesh.position.set(cx, 0.45, cz);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      this.scene.add(mesh);
    }
    const s = this.store;
    this.flatRect(s.areas.entrance_door.x0, s.areas.entrance_door.y0, s.areas.entrance_door.x1, s.areas.entrance_door.y1, this.tokens.color['ink-muted'], 0.006);
    this.flatRect(s.areas.exit_door.x0, s.areas.exit_door.y0, s.areas.exit_door.x1, s.areas.exit_door.y1, this.tokens.color['ink-muted'], 0.006);
  }

  /** (Re)builds the display-slot meshes for `layout`: added slots are a solid "change" tint, removed ones a faded ghost. */
  private buildDisplaySlots(layout: Layout = this.currentLayout) {
    for (const mesh of this.displayMeshes) this.disposeObject(mesh);
    this.displayMeshes.length = 0;

    const diff = layoutDiff(this.store.baseline_layout, layout === this.store.baseline_layout ? null : layout);
    for (const d of this.store.displays) {
      const occupied = layout.displays[d.id];
      const added = diff.addedSlots[d.id];
      const removed = diff.removedSlots[d.id];
      let color = d.restricted ? this.tokens.color.red : occupied ? this.tokens.color['ink-muted'] : this.tokens.color['surface-3'];
      let opacity = d.restricted ? 0.5 : 1;
      if (added) { color = this.tokens.color.change; opacity = 1; }
      else if (removed) { color = this.tokens.color.change; opacity = 0.3; }
      this.displayMeshes.push(this.flatRect(d.x0, d.y0, d.x1, d.y1, color, 0.015, opacity));
    }
  }

  /**
   * Shows a different layout on the same scene — baseline or a candidate experiment — rather than
   * spinning up a second WebGL context. Pass null to go back to the baseline.
   */
  setLayout(layout: Layout | null) {
    this.currentLayout = layout ?? this.store.baseline_layout;
    this.buildAisles(this.currentLayout);
    this.buildDisplaySlots(this.currentLayout);
  }

  // ---------------------------------------------------------------- public API (mirrors the old floorplan.js shape)
  setSelected(cat: string | null) {
    if (this.selectedCat) this.applyEmphasis(this.selectedCat, false, 'selected');
    this.selectedCat = cat;
    if (cat) this.applyEmphasis(cat, true, 'selected');
  }

  highlight(ids: string[], kind: HighlightKind) {
    for (const id of this.highlighted.ids) {
      const mesh = this.catMesh.get(id) ?? this.aisleMeshes.find((m) => m.userData.aisleId === id);
      if (mesh) (mesh.material as THREE.MeshStandardMaterial).emissive.set(0x000000);
    }
    this.highlighted = { ids, kind };
    if (!kind) return;
    for (const id of ids) {
      const mesh = this.catMesh.get(id) ?? this.aisleMeshes.find((m) => m.userData.aisleId === id);
      if (mesh) (mesh.material as THREE.MeshStandardMaterial).emissive.set(this.tokens.color[EMISSIVE[kind]]);
    }
  }

  private applyEmphasis(cat: string, on: boolean, which: 'selected') {
    const mesh = this.catMesh.get(cat);
    if (!mesh) return;
    const mat = mesh.material as THREE.MeshStandardMaterial;
    mat.emissive.set(on ? this.tokens.color[EMISSIVE[which]] : 0x000000);
    mat.emissiveIntensity = 0.5;
  }

  setPins(list: PinSpec[]) {
    for (const obj of this.pinLayer) { obj.element.remove(); obj.removeFromParent(); }
    this.pinLayer.length = 0;
    for (const p of list) {
      const center = this.centers.get(p.zone);
      if (!center) continue;
      const el = document.createElement('div');
      el.className = `sl-pin${p.kind === 'friction' ? ' friction' : ''}`;
      el.textContent = String(p.n);
      el.setAttribute('role', 'button');
      el.setAttribute('tabindex', '0');
      el.setAttribute('aria-label', p.label);
      if (p.onClick) {
        el.addEventListener('click', p.onClick);
        el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); p.onClick!(); } });
      }
      if (p.onHover) {
        el.addEventListener('mouseenter', () => p.onHover!(true));
        el.addEventListener('mouseleave', () => p.onHover!(false));
      }
      const obj = new CSS2DObject(el);
      obj.position.set(center[0], 0.5, center[1]);
      this.scene.add(obj);
      this.pinLayer.push(obj);
    }
  }

  setHeat(grid: number[][] | null) {
    if (this.heatMesh) {
      this.scene.remove(this.heatMesh);
      (this.heatMesh.material as THREE.MeshBasicMaterial).map?.dispose();
      (this.heatMesh.material as THREE.Material).dispose();
      this.heatMesh.geometry.dispose();
      this.heatMesh = null;
    }
    this.heatGrid = grid;
    if (!grid) return;
    this.heatThresholdsCache = heatThresholds(grid);
    const heatColors = [0, 1, 2, 3, 4, 5, 6].map((i) => this.tokens.color[`heat-${i}` as keyof typeof this.tokens.color]);
    const texture = buildHeatTexture(grid, this.heatThresholdsCache, heatColors);
    const geo = new THREE.PlaneGeometry(this.W, this.H);
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.MeshBasicMaterial({ map: texture, transparent: true, opacity: 0.85 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(0, 0.03, 0);
    mesh.name = 'heat-plane';
    this.scene.add(mesh);
    this.heatMesh = mesh;
  }

  loadParticles(tracks: JourneyTrack[], opts: { speed?: number; window?: number; changed?: Set<JourneyTrack['id']>; onTick?: (t: number) => void }): ShopperParticles {
    this.particlesInstance?.dispose();
    this.particlesInstance = null;
    const particles = new ShopperParticles(tracks, {
      toWorldXZ: this.toWorldXZ,
      colors: { buyer: this.tokens.color['particle-buyer'], browser: this.tokens.color['particle-browser'], changed: this.tokens.color.change },
      ...opts,
    });
    this.scene.remove(...this.scene.children.filter((c) => c.userData.isParticles));
    particles.points.userData.isParticles = true;
    this.scene.add(particles.points);
    this.particlesInstance = particles;
    return particles;
  }

  // ---------------------------------------------------------------- interaction
  private updatePointer(event: PointerEvent) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  }

  private handleClick = (event: MouseEvent) => {
    this.updatePointer(event as PointerEvent);
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObjects(this.aisleMeshes, false)[0];
    const cat = hit?.object.userData.category as string | undefined;
    if (cat) this.opts.onZoneClick?.(cat);
  };

  private handlePointerMove = (event: PointerEvent) => {
    this.updatePointer(event);
    this.raycaster.setFromCamera(this.pointer, this.camera);

    const aisleHit = this.raycaster.intersectObjects(this.aisleMeshes, false)[0];
    this.renderer.domElement.style.cursor = aisleHit?.object.userData.category ? 'pointer' : 'default';

    if (!this.heatMesh || !this.heatGrid || !this.opts.onCellHover) return;
    const hit = this.raycaster.intersectObject(this.heatMesh, false)[0];
    if (!hit) { this.opts.onCellHover(null); return; }
    const cell = this.store.cell_m || 0.5;
    const localX = hit.point.x + this.W / 2;
    const localZ = hit.point.z + this.H / 2;
    const row = Math.floor(localZ / cell), col = Math.floor(localX / cell);
    const value = this.heatGrid[row]?.[col];
    if (value === undefined) { this.opts.onCellHover(null); return; }
    this.opts.onCellHover({ value, clientX: event.clientX, clientY: event.clientY });
  };

  private handlePointerLeave = () => {
    this.renderer.domElement.style.cursor = 'default';
    this.opts.onCellHover?.(null);
  };

  // ---------------------------------------------------------------- lifecycle
  resize() {
    const w = this.container.clientWidth || 1;
    const h = this.container.clientHeight || 1;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.labelRenderer.setSize(w, h);
  }

  private animate = () => {
    if (this.disposed) return;
    this.rafId = requestAnimationFrame(this.animate);
    const dt = this.clock.getDelta();
    this.controls.update();
    this.particlesInstance?.update(dt, this.toWorldXZ);
    this.renderer.render(this.scene, this.camera);
    this.labelRenderer.render(this.scene, this.camera);
  };

  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.rafId);
    this.resizeObserver.disconnect();
    this.renderer.domElement.removeEventListener('click', this.handleClick);
    this.renderer.domElement.removeEventListener('pointermove', this.handlePointerMove);
    this.renderer.domElement.removeEventListener('pointerleave', this.handlePointerLeave);
    this.controls.dispose();
    this.particlesInstance?.dispose();
    this.scene.traverse((obj) => {
      if (obj instanceof THREE.Mesh || obj instanceof THREE.Line) {
        obj.geometry?.dispose();
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
        for (const m of mats) { (m as THREE.MeshBasicMaterial).map?.dispose(); m.dispose(); }
      }
      if (obj instanceof CSS2DObject) obj.element.remove();
    });
    this.renderer.dispose();
    this.renderer.domElement.remove();
    this.labelRenderer.domElement.remove();
  }
}
