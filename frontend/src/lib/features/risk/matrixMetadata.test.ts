/**
 * @vitest-environment node
 *
 * matrixMetadata — the pure half of the module (node env, no jsdom).
 *
 * The module turns two reads into the three maps the correlation matrix groups by:
 * the asset rows give the type, the profile (plan 68, E5: `POST /assets/profile/query`,
 * today, the last step) gives the dominant sector and area. Its two
 * other exports are covered elsewhere: `loadMatrixMetadata` (the read) and
 * `createMatrixMetadata` (the rune factory) run end to end in
 * `e2e/portfolio/risk-lab.spec.ts`, in "the matrix offers type, sector and area
 * orderings from the assets' stored metadata…". This file owns what can be
 * decided without a network or a component: how a stored distribution is read,
 * how rows become maps, and when two id lists are the same set.
 *
 * Nothing is mocked. Importing the module also imports the API client and the
 * country store, and at import time those only build objects, so no request
 * leaves. Nothing tested here calls either of them. The environment is pinned
 * to `node` because no rune runs here: only the factory uses runes, and it is
 * not exercised.
 *
 * Fixtures carry weights as Decimal strings, the way the profile stores a map.
 */
import {describe, expect, it} from 'vitest';

import {assetIdsKey, EMPTY_MATRIX_METADATA, matrixMetadataFromReads, profileDistribution, type MatrixMetadataRow, type MatrixProfileItem} from './matrixMetadata.svelte';

// The profile's stored form of a map (plan 68, E5): weights as Decimal strings, keyed by sector or by ISO country
const TECH_MAP = {Technology: '0.7', 'Health Care': '0.2', Other: '0.1'};
const TECH = {Technology: 0.7, 'Health Care': 0.2, Other: 0.1};
const USA_MAP = {USA: '0.8', Other: '0.2'};
const USA = {USA: 0.8, Other: 0.2};

/** One item of `POST /assets/profile/query` as the matrix reads it: the steps of the two maps, the last one is today's. */
function profile(asset_id: number, voices: {sector?: unknown; geography?: unknown}): MatrixProfileItem {
    const steps = (value: unknown) => [{date: '2026-11-17', through: '2026-11-17', value, source: 'justetf', update_id: 1, opened_on: '2026-11-01'}];
    return {asset_id, voices: Object.fromEntries(Object.entries(voices).map(([key, value]) => [key, steps(value)]))};
}

describe('profileDistribution', () => {
    it.each([
        ['a missing value', undefined],
        ['an emptied value', null],
        ['an empty map', {}],
        ['a list', [TECH_MAP]],
        ['a text', 'Technology'],
    ])('is null for %s', (_case, value) => {
        expect(profileDistribution(value)).toBeNull();
    });

    it.each([
        ['a word', 'n/a'],
        ['an empty string', ''],
        ['null', null],
        ['a boolean', true],
        ['"Infinity"', 'Infinity'],
    ])('is null when one weight is unusable (%s), however good the others are', (_case, weight) => {
        // One bad weight costs the whole distribution: a partial one would put the asset in a group its data never named.
        expect(profileDistribution({Technology: '0.6', Financials: weight})).toBeNull();
    });

    it('reads a stored map key by key, the Decimal strings as numbers, without rescaling', () => {
        expect(profileDistribution(TECH_MAP)).toEqual(TECH);
        expect(profileDistribution({Technology: '0.3', Energy: '0.2'})).toEqual({Technology: 0.3, Energy: 0.2});
    });
});

describe('matrixMetadataFromReads', () => {
    it('reads the type through safeString from the asset rows: a string, a one-element list, and null for anything else', () => {
        const {types} = matrixMetadataFromReads([{asset_id: 1, asset_type: 'stock'}, {asset_id: 2, asset_type: ['etf']}, {asset_id: 3}, {asset_id: 4, asset_type: null}, {asset_id: 6, asset_type: 42}], []);
        expect(types).toEqual(
            new Map<number, string | null>([
                [1, 'stock'],
                [2, 'etf'],
                [3, null],
                [4, null],
                [6, null],
            ]),
        );
    });

    it("reads each asset's sectors and countries from its profile, today's step, and null for the one it lacks", () => {
        const rows: MatrixMetadataRow[] = [{asset_id: 10}, {asset_id: 11}, {asset_id: 12}, {asset_id: 13}];
        const {sectors, regions} = matrixMetadataFromReads(rows, [profile(10, {sector: TECH_MAP, geography: USA_MAP}), profile(11, {sector: TECH_MAP}), profile(12, {sector: null, geography: USA_MAP})]);
        expect(sectors.get(10)).toEqual(TECH);
        expect(regions.get(10)).toEqual(USA);
        expect(sectors.get(11)).toEqual(TECH);
        expect(regions.get(11)).toBeNull();
        expect(sectors.get(12)).toBeNull();
        expect(regions.get(12)).toEqual(USA);
        // No profile item at all: present as null, like every other asset the read answered for
        expect(sectors.has(13)).toBe(true);
        expect(sectors.get(13)).toBeNull();
        expect(regions.get(13)).toBeNull();
    });

    it('takes the last step of a voice', () => {
        // The steps as the API answers them, whole; the module reads only their values
        const steps = [
            {date: '2026-01-01', through: '2026-06-30', value: {Energy: '1'}, source: 'legacy', update_id: 1, opened_on: '2026-01-01'},
            {date: '2026-07-01', through: '2026-11-17', value: TECH_MAP, source: 'justetf', update_id: 2, opened_on: '2026-07-01'},
        ];
        const item: MatrixProfileItem = {asset_id: 20, voices: {sector: steps}};
        expect(matrixMetadataFromReads([{asset_id: 20}], [item]).sectors.get(20)).toEqual(TECH);
    });

    it('keys all three maps by asset id, never by position, and gives them the same keys', () => {
        const rows: MatrixMetadataRow[] = [{asset_id: 42, asset_type: 'stock'}, {asset_id: 7}, {asset_id: 19, asset_type: ['etf']}];
        const {types, sectors, regions} = matrixMetadataFromReads(rows, [profile(19, {geography: USA_MAP}), profile(42, {sector: TECH_MAP})]);
        const ids = new Set([42, 7, 19]);
        expect(new Set(types.keys())).toEqual(ids);
        expect(new Set(sectors.keys())).toEqual(ids);
        expect(new Set(regions.keys())).toEqual(ids);
        expect(sectors.get(42)).toEqual(TECH);
        expect(regions.get(19)).toEqual(USA);
        expect(types.get(7)).toBeNull();
    });

    it('ignores a profile item that answered an error, and one for an asset the rows do not hold', () => {
        const {sectors} = matrixMetadataFromReads([{asset_id: 30}], [{asset_id: 30, error: 'Asset not found'}, profile(31, {sector: TECH_MAP})]);
        expect(sectors).toEqual(new Map([[30, null]]));
    });

    it('gives three empty maps for no rows, the same shape as EMPTY_MATRIX_METADATA', () => {
        const metadata = matrixMetadataFromReads([], []);
        for (const map of [metadata.types, metadata.sectors, metadata.regions, EMPTY_MATRIX_METADATA.types, EMPTY_MATRIX_METADATA.sectors, EMPTY_MATRIX_METADATA.regions]) {
            expect(map.size).toBe(0);
        }
    });
});

describe('assetIdsKey', () => {
    it('is the same key for the same set, whatever the order', () => {
        expect(assetIdsKey([3, 1, 2])).toBe('1,2,3');
        expect(assetIdsKey([2, 3, 1])).toBe(assetIdsKey([1, 2, 3]));
    });

    it('ignores duplicates', () => {
        expect(assetIdsKey([2, 2, 1, 2])).toBe('1,2');
        expect(assetIdsKey([2, 2, 1, 2])).toBe(assetIdsKey([1, 2]));
    });

    it('sorts numerically, not as strings', () => {
        expect(assetIdsKey([100, 9, 10])).toBe('9,10,100');
    });

    it('tells different sets apart, the separator included', () => {
        expect(assetIdsKey([1, 2])).not.toBe(assetIdsKey([1, 2, 3]));
        // Joined without a separator both would read "123".
        expect(assetIdsKey([1, 2, 3])).not.toBe(assetIdsKey([1, 23]));
    });

    it('reads back as the sorted, de-duplicated ids, which is how the factory uses it', () => {
        expect(assetIdsKey([40, 5, 3, 5]).split(',').map(Number)).toEqual([3, 5, 40]);
    });

    it('is the empty string for no ids', () => {
        expect(assetIdsKey([])).toBe('');
    });

    it("leaves the caller's array as it was", () => {
        const ids = [3, 1, 2, 1];
        assetIdsKey(ids);
        expect(ids).toEqual([3, 1, 2, 1]);
    });
});
