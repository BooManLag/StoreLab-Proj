import { describe, expect, it } from 'vitest';
import { changedRoutes } from './changedRoutes';
import type { JourneyTrack } from '../api/storeTypes';

const track = (id: string, points: [number, number, number][]): JourneyTrack => ({ id, bought: false, points });

describe('changedRoutes', () => {
  it('flags nothing when every shopper walks the identical path', () => {
    const base = [track('S1', [[0, 1, 1], [10, 2, 2], [20, 3, 3]])];
    const cand = [track('S1', [[0, 1, 1], [10, 2, 2], [20, 3, 3]])];
    expect(changedRoutes(base, cand).size).toBe(0);
  });

  it('ignores a path that only shifts by less than the minimum cell count', () => {
    const base = [track('S1', [[0, 1, 1], [10, 2, 2]])];
    const cand = [track('S1', [[0, 1.2, 1.1], [10, 2, 2]])]; // same floor cells, sub-cell jitter
    expect(changedRoutes(base, cand, 3).size).toBe(0);
  });

  it('flags a shopper whose path visits enough different floor cells', () => {
    const base = [track('S1', [[0, 1, 1], [10, 5, 5], [20, 9, 9]])];
    const cand = [track('S1', [[0, 1, 1], [10, 15, 15], [20, 19, 19]])];
    expect(changedRoutes(base, cand, 3)).toEqual(new Set(['S1']));
  });

  it('flags a candidate shopper with no baseline counterpart', () => {
    const base: JourneyTrack[] = [];
    const cand = [track('NEW1', [[0, 1, 1], [10, 2, 2]])];
    expect(changedRoutes(base, cand)).toEqual(new Set(['NEW1']));
  });

  it('leaves an unrelated shopper alone when only another one re-routes', () => {
    const base = [track('S1', [[0, 1, 1], [10, 2, 2]]), track('S2', [[0, 5, 5], [10, 6, 6], [20, 7, 7]])];
    const cand = [track('S1', [[0, 1, 1], [10, 2, 2]]), track('S2', [[0, 15, 15], [10, 16, 16], [20, 17, 17]])];
    expect(changedRoutes(base, cand, 3)).toEqual(new Set(['S2']));
  });
});
