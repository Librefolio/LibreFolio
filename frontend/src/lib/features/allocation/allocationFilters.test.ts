/**
 * The filters of the Allocazione tab: first opening, memory per page (and its failures), the choices and their chips.
 */
import {describe, expect, it} from 'vitest';
import {emptyFilters, filterChips, filtersStorageKey, hasFilters, isClassOn, parseFilters, removeChip, removeClassChip, sameFilters, serializeFilters, setAssetExcluded, setAssetsExcluded, setBucketExcluded, setClass, type AllocationFilters, focusClass} from './allocationFilters';

const PRESENT = ['STOCK', 'BOND', 'LIQUIDITY'];

describe('first opening', () => {
    it('is the whole portfolio: every class, nothing excluded', () => {
        const filters = emptyFilters();
        expect(filters).toEqual({classes: null, excludeBuckets: [], excludeAssetIds: []});
        expect(hasFilters(filters)).toBe(false);
        expect(filterChips(filters)).toEqual([]);
        expect(isClassOn(filters, 'ANYTHING')).toBe(true);
    });
});

describe('memory per page', () => {
    it('has one key for the Dashboard and one per broker', () => {
        expect(filtersStorageKey({kind: 'portfolio'})).toBe('allocation-filters:dashboard');
        expect(filtersStorageKey({kind: 'broker', brokerId: 7})).toBe('allocation-filters:broker:7');
    });

    it('round-trips what was chosen', () => {
        const chosen: AllocationFilters = {classes: ['STOCK'], excludeBuckets: ['Unknown'], excludeAssetIds: [3, 9]};
        expect(parseFilters(serializeFilters(chosen))).toEqual(chosen);
        expect(parseFilters(serializeFilters(emptyFilters()))).toEqual(emptyFilters());
    });

    it.each([[null], [undefined], [''], ['not json'], ['[]'], ['42'], ['"x"'], ['null']])('reads %j as the first opening', (raw) => {
        expect(parseFilters(raw as string | null | undefined)).toEqual(emptyFilters());
    });

    it('keeps what is well formed and drops the rest, field by field', () => {
        const raw = JSON.stringify({classes: ['STOCK', 'STOCK', ''], excludeBuckets: ['Unknown', 'Liquidity', 'Other', 'Other'], excludeAssetIds: [1, 'x', 2.5, 2, 1]});
        // a class list with an empty name is not a class list: «every class»; the other two keep their valid entries
        expect(parseFilters(raw)).toEqual({classes: null, excludeBuckets: ['Unknown', 'Other'], excludeAssetIds: [1, 2]});
        expect(parseFilters(JSON.stringify({classes: ['STOCK', 'STOCK']}))).toEqual({classes: ['STOCK'], excludeBuckets: [], excludeAssetIds: []});
        expect(parseFilters(JSON.stringify({classes: 'STOCK', excludeBuckets: 'Unknown', excludeAssetIds: {}}))).toEqual(emptyFilters());
    });
});

describe('classes', () => {
    it('turning one off from «every class» lists the others', () => {
        expect(setClass(emptyFilters(), 'BOND', false, PRESENT).classes).toEqual(['STOCK', 'LIQUIDITY']);
    });

    it('turning them all back on is «every class» again', () => {
        const some = setClass(emptyFilters(), 'BOND', false, PRESENT);
        expect(setClass(some, 'BOND', true, PRESENT).classes).toBeNull();
    });

    it('can turn every class off: an empty selection, which the backend reads as nothing', () => {
        let filters = emptyFilters();
        for (const assetClass of PRESENT) filters = setClass(filters, assetClass, false, PRESENT);
        expect(filters.classes).toEqual([]);
        expect(isClassOn(filters, 'STOCK')).toBe(false);
        expect(hasFilters(filters)).toBe(true);
    });

    it('keeps a saved class the scope does not hold today, and then «every class» is not claimed', () => {
        const saved: AllocationFilters = {classes: ['STOCK', 'CRYPTO'], excludeBuckets: [], excludeAssetIds: []};
        const next = setClass(saved, 'BOND', true, PRESENT);
        expect(next.classes).toEqual(['STOCK', 'CRYPTO', 'BOND']);
        expect(setClass(next, 'LIQUIDITY', true, PRESENT).classes, 'CRYPTO is still saved: an explicit list').toEqual(['STOCK', 'CRYPTO', 'BOND', 'LIQUIDITY']);
    });

    it('a chip of the last class left goes back to «every class», never to an empty selection', () => {
        expect(removeClassChip({classes: ['STOCK'], excludeBuckets: [], excludeAssetIds: []}, 'STOCK').classes).toBeNull();
        expect(removeClassChip({classes: ['STOCK', 'BOND'], excludeBuckets: [], excludeAssetIds: []}, 'STOCK').classes).toEqual(['BOND']);
        expect(removeClassChip(emptyFilters(), 'STOCK').classes).toBeNull();
    });
});

describe('exclusions', () => {
    it('adds and takes back a bucket once', () => {
        const out = setBucketExcluded(setBucketExcluded(emptyFilters(), 'Unknown', true), 'Unknown', true);
        expect(out.excludeBuckets).toEqual(['Unknown']);
        expect(setBucketExcluded(out, 'Unknown', false).excludeBuckets).toEqual([]);
    });

    it('adds and takes back an asset, one or many', () => {
        const one = setAssetExcluded(emptyFilters(), 4, true);
        expect(one.excludeAssetIds).toEqual([4]);
        const many = setAssetsExcluded(one, [4, 5, 6], true);
        expect(many.excludeAssetIds.sort()).toEqual([4, 5, 6]);
        expect(setAssetsExcluded(many, [5, 6], false).excludeAssetIds).toEqual([4]);
    });
});

describe('chips', () => {
    const filters: AllocationFilters = {classes: ['STOCK'], excludeBuckets: ['Unknown'], excludeAssetIds: [8]};

    it('are one per choice, classes then buckets then assets', () => {
        expect(filterChips(filters)).toEqual([
            {kind: 'class', value: 'STOCK'},
            {kind: 'bucket', value: 'Unknown'},
            {kind: 'asset', value: 8},
        ]);
    });

    it('take their choice away', () => {
        expect(removeChip(filters, {kind: 'bucket', value: 'Unknown'}).excludeBuckets).toEqual([]);
        expect(removeChip(filters, {kind: 'asset', value: 8}).excludeAssetIds).toEqual([]);
        expect(removeChip(filters, {kind: 'class', value: 'STOCK'}).classes).toBeNull();
    });
});

describe('sameFilters', () => {
    it('ignores the order of the lists', () => {
        expect(sameFilters({classes: ['A', 'B'], excludeBuckets: ['Other', 'Unknown'], excludeAssetIds: [2, 1]}, {classes: ['B', 'A'], excludeBuckets: ['Unknown', 'Other'], excludeAssetIds: [1, 2]})).toBe(true);
        expect(sameFilters(emptyFilters(), {classes: [], excludeBuckets: [], excludeAssetIds: []}), '[] is nothing, null is everything').toBe(false);
    });
});

describe('focusClass (a click on the matrix)', () => {
    it('keeps only that class', () => {
        expect(focusClass(emptyFilters(), 'STOCK').classes).toEqual(['STOCK']);
        expect(focusClass({classes: ['STOCK', 'BOND'], excludeBuckets: ['Unknown'], excludeAssetIds: [3]}, 'BOND')).toEqual({classes: ['BOND'], excludeBuckets: ['Unknown'], excludeAssetIds: [3]});
    });

    it('on the class that is already alone goes back to every class', () => {
        expect(focusClass({classes: ['STOCK'], excludeBuckets: [], excludeAssetIds: []}, 'STOCK').classes).toBeNull();
    });
});
