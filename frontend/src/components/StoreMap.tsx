import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import { StoreScene, type HighlightKind, type PinSpec } from '../three/StoreScene';
import type { JourneyTrack, Layout, StoreGeometry } from '../api/storeTypes';

export interface StoreMapHandle {
  toggleParticles: () => boolean;
}

export interface StoreMapProps {
  store: StoreGeometry;
  /** The layout to render — a candidate experiment, or omit/null for the baseline. */
  layout?: Layout | null;
  selectedCat?: string | null;
  onZoneClick?: (cat: string) => void;
  heatGrid?: number[][] | null;
  onCellHover?: (info: { value: number; clientX: number; clientY: number } | null) => void;
  highlight?: { ids: string[]; kind: HighlightKind };
  pins?: PinSpec[];
  tracks?: JourneyTrack[];
  tracksWindowS?: number;
  /** Shopper ids to color as "changed" (route differs from the baseline) — see lib/changedRoutes.ts. */
  changed?: Set<JourneyTrack['id']>;
  onTick?: (t: number) => void;
}

const NO_HIGHLIGHT = { ids: [], kind: '' as HighlightKind };
const NO_PINS: PinSpec[] = [];
const NO_TRACKS: JourneyTrack[] = [];

/**
 * Owns the vanilla Three.js StoreScene's whole lifecycle: one construction on
 * mount, one dispose on unmount. Everything reactive goes through StoreScene's
 * imperative methods in effects below, never a re-construction — rebuilding
 * the WebGL context on every prop change would be both wrong and slow.
 *
 * Every prop past `store` is optional: the Store screen uses the full set
 * (heatmap, pins, traffic particles); a lighter embedding — e.g. the
 * before/after toggle in the Experiments hero — can pass just `layout`.
 */
export const StoreMap = forwardRef<StoreMapHandle, StoreMapProps>(function StoreMap(
  {
    store, layout = null, selectedCat = null, onZoneClick, heatGrid = null, onCellHover,
    highlight = NO_HIGHLIGHT, pins = NO_PINS, tracks = NO_TRACKS, tracksWindowS = 0, changed, onTick,
  },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<StoreScene | null>(null);

  // Keep the latest callbacks without re-running the mount effect.
  const onZoneClickRef = useRef(onZoneClick);
  onZoneClickRef.current = onZoneClick;
  const onCellHoverRef = useRef(onCellHover);
  onCellHoverRef.current = onCellHover;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const scene = new StoreScene(container, store, {
      onZoneClick: (cat) => onZoneClickRef.current?.(cat),
      onCellHover: (info) => onCellHoverRef.current?.(info),
    });
    sceneRef.current = scene;
    return () => {
      scene.dispose();
      sceneRef.current = null;
    };
    // store geometry is fixed for the life of this screen; only mount/unmount should rebuild the scene.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { sceneRef.current?.setLayout(layout); }, [layout]);
  useEffect(() => { sceneRef.current?.setSelected(selectedCat); }, [selectedCat]);
  useEffect(() => { sceneRef.current?.highlight(highlight.ids, highlight.kind); }, [highlight]);
  useEffect(() => { sceneRef.current?.setPins(pins); }, [pins]);
  useEffect(() => { sceneRef.current?.setHeat(heatGrid); }, [heatGrid]);

  const particlesRef = useRef<ReturnType<StoreScene['loadParticles']> | null>(null);
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !tracks.length) return;
    particlesRef.current = scene.loadParticles(tracks, { window: tracksWindowS, changed, onTick });
    // Respect the OS reduced-motion setting: don't autoplay continuous motion the viewer didn't ask for.
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) particlesRef.current.start();
    return () => { particlesRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tracks, changed]);

  useImperativeHandle(ref, () => ({
    toggleParticles: () => particlesRef.current?.toggle() ?? false,
  }), []);

  return <div ref={containerRef} style={{ position: 'relative', width: '100%', height: '100%' }} />;
});
