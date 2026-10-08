import type { Layout } from '../api/storeTypes';

export interface LayoutDiff {
  addedSlots: Record<string, string>;
  removedSlots: Record<string, string>;
  movedCats: Set<string>;
}

/** Diff a candidate layout against the baseline — which display slots changed occupant, which categories moved aisle. */
export function layoutDiff(base: Layout, candidate: Layout | null): LayoutDiff {
  const out: LayoutDiff = { addedSlots: {}, removedSlots: {}, movedCats: new Set() };
  if (!candidate) return out;
  for (const [slot, cat] of Object.entries(candidate.displays)) {
    if (base.displays[slot] !== cat) out.addedSlots[slot] = cat;
  }
  for (const [slot, cat] of Object.entries(base.displays)) {
    if (!(slot in candidate.displays)) out.removedSlots[slot] = cat;
  }
  for (const [cat, slot] of Object.entries(candidate.category_slot)) {
    if (base.category_slot[cat] !== slot) out.movedCats.add(cat);
  }
  return out;
}
