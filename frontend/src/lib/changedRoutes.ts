import type { JourneyTrack } from '../api/storeTypes';

/** The 1m floor cells a track passes through, ignoring timing — for comparing paths, not schedules. */
function cells(points: JourneyTrack['points']): Set<string> {
  return new Set(points.map(([, x, y]) => `${Math.floor(x)},${Math.floor(y)}`));
}

/** Ids of shoppers who walk somewhere meaningfully different between two layouts (by floor cell, not timing). */
export function changedRoutes(baseTracks: JourneyTrack[], candidateTracks: JourneyTrack[], minCells = 3): Set<JourneyTrack['id']> {
  const base = new Map(baseTracks.map((t) => [t.id, cells(t.points)]));
  const out = new Set<JourneyTrack['id']>();
  for (const t of candidateTracks) {
    const b = base.get(t.id);
    if (!b) { out.add(t.id); continue; }
    const c = cells(t.points);
    let diff = 0;
    for (const k of c) if (!b.has(k)) diff++;
    for (const k of b) if (!c.has(k)) diff++;
    if (diff >= minCells) out.add(t.id);
  }
  return out;
}
