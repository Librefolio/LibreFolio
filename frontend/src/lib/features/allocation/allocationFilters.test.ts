/**
 * The filters of the Allocazione tab: first opening, memory per page (and its failures), the choices and their chips.
 */
import {describe, expect, it} from 'vitest';
import {
    classState,
    emptyFilters,
    filterChips,
    filtersStorageKey,
    hasFilters,
    isClassOn,
    isTypeOn,
    parseFilters,
    removeChip,
    removeClassChip,
    sameFilters,
    serializeFilters,
    setAssetExcluded,
    setAssetsExcluded,
    setBucketExcluded,
    setClass,
    setEveryClass,
    setType,
    type AllocationFilters,
    type PresentClass,
    focusClass,
} from './allocationFilters';

const PRESENT: PresentClass[] = [
    {asset_class: 'STOCK', types: [{asset_type: 'ETF_STOCK'}, {asset_type: 'STOCK'}]},
    {asset_class: 'BOND', types: [{asset_type: 'BOND'}]},
    {asset_class: 'LIQUIDITY', types: []},
];

describe('first opening', () => {
    it('is the whole portfolio: every class, nothing excluded', () => {
        const filters = emptyFilters();
        expect(filters).toEqual({classes: null, types: [], excludeBuckets: [], excludeAssetIds: []});
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
        const chosen: AllocationFilters = {classes: ['STOCK'], types: [], excludeBuckets: ['Unknown'], excludeAssetIds: [3, 9]};
        expect(parseFilters(serializeFilters(chosen))).toEqual(chosen);
        expect(parseFilters(serializeFilters(emptyFilters()))).toEqual(emptyFilters());
    });

    it.each([[null], [undefined], [''], ['not json'], ['[]'], ['42'], ['"x"'], ['null']])('reads %j as the first opening', (raw) => {
        expect(parseFilters(raw as string | null | undefined)).toEqual(emptyFilters());
    });

    it('keeps what is well formed and drops the rest, field by field', () => {
        const raw = JSON.stringify({classes: ['STOCK', 'STOCK', ''], types: [], excludeBuckets: ['Unknown', 'Liquidity', 'Other', 'Other'], excludeAssetIds: [1, 'x', 2.5, 2, 1]});
        // a class list with an empty name is not a class list: «every class»; the other two keep their valid entries
        expect(parseFilters(raw)).toEqual({classes: null, types: [], excludeBuckets: ['Unknown', 'Other'], excludeAssetIds: [1, 2]});
        expect(parseFilters(JSON.stringify({classes: ['STOCK', 'STOCK']}))).toEqual({classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []});
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
        for (const {asset_class: assetClass} of PRESENT) filters = setClass(filters, assetClass, false, PRESENT);
        expect(filters.classes).toEqual([]);
        expect(isClassOn(filters, 'STOCK')).toBe(false);
        expect(hasFilters(filters)).toBe(true);
    });

    it('keeps a saved class the scope does not hold today, and then «every class» is not claimed', () => {
        const saved: AllocationFilters = {classes: ['STOCK', 'CRYPTO'], types: [], excludeBuckets: [], excludeAssetIds: []};
        const next = setClass(saved, 'BOND', true, PRESENT);
        expect(next.classes).toEqual(['STOCK', 'CRYPTO', 'BOND']);
        expect(setClass(next, 'LIQUIDITY', true, PRESENT).classes, 'CRYPTO is still saved: an explicit list').toEqual(['STOCK', 'CRYPTO', 'BOND', 'LIQUIDITY']);
    });

    it('a chip of the last class left goes back to «every class», never to an empty selection', () => {
        expect(removeClassChip({classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []}, 'STOCK').classes).toBeNull();
        expect(removeClassChip({classes: ['STOCK', 'BOND'], types: [], excludeBuckets: [], excludeAssetIds: []}, 'STOCK').classes).toEqual(['BOND']);
        expect(removeClassChip(emptyFilters(), 'STOCK').classes).toBeNull();
    });
});

describe('the types of a class (86, D-13)', () => {
    const whole = emptyFilters();
    const part = setType(whole, 'STOCK', 'STOCK', false, PRESENT);

    it('one type turned off leaves the class in part: out of the classes, its other types kept on their own', () => {
        expect(part).toEqual({classes: ['BOND', 'LIQUIDITY'], types: ['ETF_STOCK'], excludeBuckets: [], excludeAssetIds: []});
        expect(classState(part, PRESENT[0])).toBe('mixed');
        expect([isTypeOn(part, 'STOCK', 'ETF_STOCK'), isTypeOn(part, 'STOCK', 'STOCK'), isTypeOn(part, 'BOND', 'BOND')]).toEqual([true, false, true]);
        expect(isClassOn(part, 'STOCK')).toBe(false);
    });

    it('the last type turned back on is the whole class again, and every class «every class»', () => {
        expect(setType(part, 'STOCK', 'STOCK', true, PRESENT)).toEqual(emptyFilters());
    });

    it('the last type turned off is the class off', () => {
        const off = setType(part, 'STOCK', 'ETF_STOCK', false, PRESENT);
        expect(off).toEqual({classes: ['BOND', 'LIQUIDITY'], types: [], excludeBuckets: [], excludeAssetIds: []});
        expect(classState(off, PRESENT[0])).toBe('off');
    });

    it('a class of one type turned off by its type is off, never mixed', () => {
        const off = setType(whole, 'BOND', 'BOND', false, PRESENT);
        expect(off.classes).toEqual(['STOCK', 'LIQUIDITY']);
        expect(classState(off, PRESENT[1])).toBe('off');
    });

    it('the class switch from mixed: all of it on, or none, and its types are no longer kept on their own', () => {
        expect(setClass(part, 'STOCK', true, PRESENT)).toEqual(emptyFilters());
        expect(setClass(part, 'STOCK', false, PRESENT)).toEqual({classes: ['BOND', 'LIQUIDITY'], types: [], excludeBuckets: [], excludeAssetIds: []});
    });

    it('keeps a saved type of a class the scope does not hold', () => {
        const saved: AllocationFilters = {classes: ['BOND'], types: ['ETF_CRYPTO'], excludeBuckets: [], excludeAssetIds: []};
        expect(setType(saved, 'STOCK', 'STOCK', true, PRESENT).types).toEqual(['ETF_CRYPTO', 'STOCK']);
        expect(setClass(saved, 'STOCK', true, PRESENT).types).toEqual(['ETF_CRYPTO']);
    });

    it('every class at once, on and off', () => {
        expect(setEveryClass(part, true)).toEqual(emptyFilters());
        expect(setEveryClass(part, false)).toEqual({classes: [], types: [], excludeBuckets: [], excludeAssetIds: []});
    });

    it('has a chip per type kept on its own; the last choice taken away goes back to every class', () => {
        expect(filterChips(part).map((chip) => [chip.kind, chip.value])).toEqual([
            ['class', 'BOND'],
            ['class', 'LIQUIDITY'],
            ['type', 'ETF_STOCK'],
        ]);
        expect(removeChip(part, {kind: 'type', value: 'ETF_STOCK'})).toEqual({classes: ['BOND', 'LIQUIDITY'], types: [], excludeBuckets: [], excludeAssetIds: []});
        const only: AllocationFilters = {classes: [], types: ['ETF_STOCK'], excludeBuckets: [], excludeAssetIds: []};
        expect(removeChip(only, {kind: 'type', value: 'ETF_STOCK'})).toEqual(emptyFilters());
        expect(removeClassChip({...only, classes: ['BOND']}, 'BOND').classes, 'a type is still kept').toEqual([]);
    });

    it('is remembered; what an older version stored has no types, and types without classes say nothing', () => {
        expect(parseFilters(serializeFilters(part))).toEqual(part);
        expect(parseFilters(JSON.stringify({classes: ['STOCK'], excludeBuckets: [], excludeAssetIds: []})).types).toEqual([]);
        expect(parseFilters(JSON.stringify({classes: null, types: ['ETF_STOCK']})).types).toEqual([]);
        expect(parseFilters(JSON.stringify({classes: [], types: ['ETF_STOCK', 3, '', 'ETF_STOCK']})).types).toEqual(['ETF_STOCK']);
    });

    it('a click on the matrix keeps the class whole and drops the types', () => {
        expect(focusClass(part, 'STOCK')).toMatchObject({classes: ['STOCK'], types: []});
        expect(focusClass({...part, classes: ['BOND']}, 'BOND'), 'not alone while a type is kept').toMatchObject({classes: ['BOND'], types: []});
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
    const filters: AllocationFilters = {classes: ['STOCK'], types: [], excludeBuckets: ['Unknown'], excludeAssetIds: [8]};

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
        expect(sameFilters({classes: ['A', 'B'], types: [], excludeBuckets: ['Other', 'Unknown'], excludeAssetIds: [2, 1]}, {classes: ['B', 'A'], types: [], excludeBuckets: ['Unknown', 'Other'], excludeAssetIds: [1, 2]})).toBe(true);
        expect(sameFilters(emptyFilters(), {classes: [], types: [], excludeBuckets: [], excludeAssetIds: []}), '[] is nothing, null is everything').toBe(false);
    });
});

describe('focusClass (a click on the matrix)', () => {
    it('keeps only that class', () => {
        expect(focusClass(emptyFilters(), 'STOCK').classes).toEqual(['STOCK']);
        expect(focusClass({classes: ['STOCK', 'BOND'], types: [], excludeBuckets: ['Unknown'], excludeAssetIds: [3]}, 'BOND')).toEqual({classes: ['BOND'], types: [], excludeBuckets: ['Unknown'], excludeAssetIds: [3]});
    });

    it('on the class that is already alone goes back to every class', () => {
        expect(focusClass({classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []}, 'STOCK').classes).toBeNull();
    });
});
