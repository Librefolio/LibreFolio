/**
 * @vitest-environment node
 *
 * matrixMetadata — the pure half of the module (node env, no jsdom).
 *
 * The module turns one bulk read of the asset metadata into the three maps the
 * correlation matrix groups by — type, dominant sector, dominant area. Its two
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
 * Fixtures carry weights as Decimal strings, the way the backend serialises them
 * (`FASectorArea_Output` types a weight as a string), plus one numeric case,
 * because the input schema accepts both.
 */
import {describe, expect, it} from 'vitest';

import {assetIdsKey, distributionOf, EMPTY_MATRIX_METADATA, matrixMetadataFromRows, type MatrixMetadataRow} from './matrixMetadata.svelte';

const TECH_AREA = {distribution: {Technology: '0.7000', 'Health Care': '0.2000', Other: '0.1000'}};
const TECH = {Technology: 0.7, 'Health Care': 0.2, Other: 0.1};
const USA_AREA = {distribution: {USA: '0.8000', Other: '0.2000'}};
const USA = {USA: 0.8, Other: 0.2};

describe('distributionOf', () => {
    it.each([
        ['a missing area', undefined],
        ['a null area', null],
        ['an area without a distribution', {}],
        ['a null distribution', {distribution: null}],
        ['an empty distribution', {distribution: {}}],
        ['an empty list', []],
        ['a list holding null', [null]],
    ])('is null for %s', (_case, area) => {
        expect(distributionOf(area)).toBeNull();
    });

    it.each([
        ['a word', 'n/a'],
        ['an empty string', ''],
        ['a blank string', '   '],
        ['null', null],
        ['a boolean', true],
        ['NaN', Number.NaN],
        ['an infinite number', Number.POSITIVE_INFINITY],
        ['"Infinity"', 'Infinity'],
    ])('is null when one weight is unusable (%s), however good the others are', (_case, weight) => {
        // One bad weight costs the whole distribution: a partial one would put the
        // asset in a group its stored data never named.
        expect(distributionOf({distribution: {Technology: '0.6000', Financials: weight}})).toBeNull();
    });

    it('reads a valid distribution key by key, the stored Decimal strings as numbers', () => {
        expect(distributionOf(TECH_AREA)).toEqual(TECH);
    });

    it('takes numeric weights as they are', () => {
        expect(distributionOf({distribution: {USA: 1}})).toEqual({USA: 1});
    });

    it('does not rescale: the weights stay the stored ones, whatever they sum to', () => {
        // Dominance is `dominantExposure`'s question and the tooltip prints these
        // shares as they are, so they must not be scaled to 1 here.
        expect(distributionOf({distribution: {Technology: '0.3000', Energy: '0.2000'}})).toEqual({Technology: 0.3, Energy: 0.2});
    });

    it('reads a list-wrapped area through safeScalar, that is its first entry', () => {
        expect(distributionOf([USA_AREA])).toEqual(USA);
    });

    it('reads position 0 only: a list whose first entry is null holds no distribution', () => {
        expect(distributionOf([null, USA_AREA])).toBeNull();
    });
});

describe('matrixMetadataFromRows', () => {
    it('reads the type through safeString: a string, a one-element list, and null for anything else', () => {
        const {types} = matrixMetadataFromRows([{asset_id: 1, asset_type: 'stock'}, {asset_id: 2, asset_type: ['etf']}, {asset_id: 3}, {asset_id: 4, asset_type: null}, {asset_id: 5, asset_type: []}, {asset_id: 6, asset_type: 42}]);
        expect(types).toEqual(
            new Map<number, string | null>([
                [1, 'stock'],
                [2, 'etf'],
                [3, null],
                [4, null],
                [5, null],
                [6, null],
            ]),
        );
    });

    it("reads each row's sector and area on their own, and null for the one a row lacks", () => {
        const {sectors, regions} = matrixMetadataFromRows([
            {asset_id: 10, classification_params: {sector_area: TECH_AREA, geographic_area: USA_AREA}},
            {asset_id: 11, classification_params: {sector_area: TECH_AREA}},
            {asset_id: 12, classification_params: {sector_area: null, geographic_area: USA_AREA}},
            {asset_id: 13, classification_params: {short_description: 'described, never classified'}},
        ]);
        expect(sectors.get(10)).toEqual(TECH);
        expect(regions.get(10)).toEqual(USA);
        expect(sectors.get(11)).toEqual(TECH);
        expect(regions.get(11)).toBeNull();
        expect(sectors.get(12)).toBeNull();
        expect(regions.get(12)).toEqual(USA);
        expect(sectors.get(13)).toBeNull();
        expect(regions.get(13)).toBeNull();
    });

    it.each([
        ['missing', {asset_id: 20, asset_type: 'stock'}],
        ['null', {asset_id: 20, asset_type: 'stock', classification_params: null}],
        ['a list holding null', {asset_id: 20, asset_type: 'stock', classification_params: [null]}],
    ])('maps a row whose classification_params is %s to null in both maps, and keeps its type', (_case, row) => {
        const {types, sectors, regions} = matrixMetadataFromRows([row]);
        expect(types.get(20)).toBe('stock');
        // Present as null, like every other row: the read answered for this asset, and it has no areas.
        expect(sectors.has(20)).toBe(true);
        expect(sectors.get(20)).toBeNull();
        expect(regions.has(20)).toBe(true);
        expect(regions.get(20)).toBeNull();
    });

    it('reads a list-wrapped classification through its first entry', () => {
        const {sectors, regions} = matrixMetadataFromRows([{asset_id: 30, classification_params: [{sector_area: TECH_AREA, geographic_area: USA_AREA}]}]);
        expect(sectors.get(30)).toEqual(TECH);
        expect(regions.get(30)).toEqual(USA);
    });

    it('drops an unusable distribution to null and leaves the rest of the row alone', () => {
        const {types, sectors, regions} = matrixMetadataFromRows([{asset_id: 40, asset_type: 'etf', classification_params: {sector_area: {distribution: {Technology: 'n/a'}}, geographic_area: USA_AREA}}]);
        expect(types.get(40)).toBe('etf');
        expect(sectors.get(40)).toBeNull();
        expect(regions.get(40)).toEqual(USA);
    });

    it('keys all three maps by asset id, never by position, and gives them the same keys', () => {
        // Ids out of order, and rows with and without each part: every map must
        // still hold every row, since the matrix looks all three up by id.
        const rows: MatrixMetadataRow[] = [{asset_id: 42, asset_type: 'stock', classification_params: {sector_area: TECH_AREA}}, {asset_id: 7}, {asset_id: 19, asset_type: ['etf'], classification_params: {geographic_area: USA_AREA}}];
        const {types, sectors, regions} = matrixMetadataFromRows(rows);
        const ids = new Set([42, 7, 19]);
        expect(new Set(types.keys())).toEqual(ids);
        expect(new Set(sectors.keys())).toEqual(ids);
        expect(new Set(regions.keys())).toEqual(ids);
        expect(types.get(42)).toBe('stock');
        expect(sectors.get(42)).toEqual(TECH);
        expect(types.get(19)).toBe('etf');
        expect(regions.get(19)).toEqual(USA);
        expect(types.get(7)).toBeNull();
    });

    it('keeps the last reading of a row the read repeats', () => {
        const {types, sectors, regions} = matrixMetadataFromRows([
            {asset_id: 50, asset_type: 'stock', classification_params: {sector_area: TECH_AREA}},
            {asset_id: 50, asset_type: 'etf', classification_params: {geographic_area: USA_AREA}},
        ]);
        expect(types).toEqual(new Map([[50, 'etf']]));
        expect(sectors).toEqual(new Map([[50, null]]));
        expect(regions).toEqual(new Map([[50, USA]]));
    });

    it('gives three empty maps for no rows, the same shape as EMPTY_MATRIX_METADATA', () => {
        const metadata = matrixMetadataFromRows([]);
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
