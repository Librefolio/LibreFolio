/**
 * priceProcessingPool.test.ts — Unit tests for the balanced-by-weight chunk splitting
 * used to distribute bulk price-query items across the shared worker pool.
 *
 * @module workers/__tests__/priceProcessingPool.test
 */
import {describe, expect, it} from 'vitest';

import {itemWeight, splitBalanced} from '../priceProcessingPool';

describe('itemWeight', () => {
    it('returns the price array length when present', () => {
        expect(itemWeight({asset_id: 1, prices: [1, 2, 3]})).toBe(3);
    });

    it('defaults to 1 for an item with no prices', () => {
        expect(itemWeight({asset_id: 1, prices: []})).toBe(1);
        expect(itemWeight({asset_id: 1})).toBe(1);
        expect(itemWeight(null)).toBe(1);
    });
});

describe('splitBalanced', () => {
    it('balances a mix of a very long history and several short ones by total weight, not item count', () => {
        // One 26-year asset (~6700 points) alongside several 1-year assets (~250 points
        // each) — naive per-item chunking (e.g. round-robin) would put the huge asset
        // alone in one chunk and several small ones in another, leaving one worker with
        // ~27x more work than the rest. Balanced-by-weight should even this out.
        const items = [
            {asset_id: 1, prices: new Array(6700).fill(0)},
            {asset_id: 2, prices: new Array(250).fill(0)},
            {asset_id: 3, prices: new Array(250).fill(0)},
            {asset_id: 4, prices: new Array(250).fill(0)},
            {asset_id: 5, prices: new Array(250).fill(0)},
        ];

        const groups = splitBalanced(items, 2);
        expect(groups.length).toBe(2);

        const totalWeights = groups.map((g) => g.reduce((sum: number, item) => sum + itemWeight(item), 0));
        // The single huge asset (6700) should end up alone in one group, with all 4
        // small ones (1000 total) in the other -- the closest possible balance given
        // this weight distribution.
        expect(totalWeights.sort((a: number, b: number) => a - b)).toEqual([1000, 6700]);
    });

    it('never produces more groups than requested, and drops empty groups', () => {
        const items = [{asset_id: 1, prices: [1]}];
        const groups = splitBalanced(items, 4);
        expect(groups.length).toBe(1);
        expect(groups[0]).toHaveLength(1);
    });

    it('distributes evenly-weighted items round-robin-like across groups', () => {
        const items = Array.from({length: 6}, (_, i) => ({asset_id: i, prices: [1, 2, 3]}));
        const groups = splitBalanced(items, 3);
        expect(groups.length).toBe(3);
        for (const g of groups) expect(g.length).toBe(2);
    });
});
