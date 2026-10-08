import { describe, expect, it } from 'vitest';
import { layoutDiff } from './layoutDiff';
import type { Layout } from '../api/storeTypes';

const baseline: Layout = {
  category_slot: { bakery: 'aisle_1', coffee: 'aisle_2', snacks: 'aisle_3', beverages: 'aisle_4' },
  displays: { endcap_a: 'bakery' },
};

describe('layoutDiff', () => {
  it('reports no changes when the candidate is null (no experiment selected)', () => {
    const diff = layoutDiff(baseline, null);
    expect(diff.movedCats.size).toBe(0);
    expect(diff.addedSlots).toEqual({});
    expect(diff.removedSlots).toEqual({});
  });

  it('reports no changes when the candidate is identical to the baseline', () => {
    const identical: Layout = { category_slot: { ...baseline.category_slot }, displays: { ...baseline.displays } };
    const diff = layoutDiff(baseline, identical);
    expect(diff.movedCats.size).toBe(0);
    expect(diff.addedSlots).toEqual({});
    expect(diff.removedSlots).toEqual({});
  });

  it('flags a category whose aisle slot changed', () => {
    const candidate: Layout = { category_slot: { ...baseline.category_slot, snacks: 'aisle_4', beverages: 'aisle_3' }, displays: baseline.displays };
    const diff = layoutDiff(baseline, candidate);
    expect(diff.movedCats).toEqual(new Set(['snacks', 'beverages']));
  });

  it('flags a display slot that gained a category as added', () => {
    const candidate: Layout = { category_slot: baseline.category_slot, displays: { ...baseline.displays, endcap_b: 'snacks' } };
    const diff = layoutDiff(baseline, candidate);
    expect(diff.addedSlots).toEqual({ endcap_b: 'snacks' });
  });

  it('flags a display slot the candidate dropped as removed', () => {
    const candidate: Layout = { category_slot: baseline.category_slot, displays: {} };
    const diff = layoutDiff(baseline, candidate);
    expect(diff.removedSlots).toEqual({ endcap_a: 'bakery' });
  });

  it('flags a display slot whose category changed as added (it reads as a new occupant)', () => {
    const candidate: Layout = { category_slot: baseline.category_slot, displays: { endcap_a: 'coffee' } };
    const diff = layoutDiff(baseline, candidate);
    expect(diff.addedSlots).toEqual({ endcap_a: 'coffee' });
  });
});
