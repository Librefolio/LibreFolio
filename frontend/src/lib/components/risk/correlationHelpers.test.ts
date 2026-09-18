/**
 * @vitest-environment node
 *
 * correlationHelpers — pure unit tests (node env, no jsdom).
 *
 * These are the decisions the correlation view makes *before* ECharts exists:
 * how a coefficient is read in words, how a symmetric payload is indexed, how
 * assets are reordered so redundancy shows up as a square, and which half of
 * the matrix is actually drawn. `CorrelationHeatmap.svelte` mounts a canvas and
 * subscribes to i18n, so none of this is reachable from a component test — the
 * branch-dense parts (unknown cells, half-populated pairs, ties, shuffled
 * orders) are asserted here instead.
 *
 * The environment is pinned to `node` explicitly: the file lives under
 * `components/`, where a reader is entitled to assume jsdom, and there is
 * nothing here that needs a DOM.
 *
 * Two invariants drive almost every case below, both taken from the module's
 * own contract:
 *
 *  - the payload is the **full N×N matrix, diagonal included**, never a
 *    pre-triangulated one, so fixtures are built that way;
 *  - a cell whose `status` is not `ok` is **unknown, not zero**. "Unknown" and
 *    "uncorrelated" are opposite findings and the tests keep them apart — and
 *    unknown stays *visible*: every pair in the rendered order gets its square,
 *    holding a null, even when the payload never mentioned the pair at all.
 */
import {describe, expect, it} from 'vitest';

import {NEAR_IDENTICAL, PAIR_LIST_THRESHOLD, buildLookup, clusterOrder, correlationBand, correlationDistance, lowerTrianglePoints, topPairs, type CorrelationCell, type CorrelationLookup, type CorrelationPair, type HeatmapPoint} from './correlationHelpers';

/** One matrix cell. `ok` is the only status that carries a usable number. */
function cell(row: number, column: number, value: number | null, status: string | null = 'ok'): CorrelationCell {
    return {row_asset_id: row, column_asset_id: column, value, observations: 24, coverage: 1, status};
}

/** ρ for an unordered pair, from a table written once per pair. */
function pairTable(entries: ReadonlyArray<readonly [number, number, number]>): (a: number, b: number) => number | null {
    const key = (a: number, b: number) => (a < b ? `${a}|${b}` : `${b}|${a}`);
    const table = new Map(entries.map(([a, b, value]) => [key(a, b), value]));
    return (a, b) => table.get(key(a, b)) ?? null;
}

/**
 * A full N×N payload, diagonal included — the shape `correlation.py` emits.
 * A pair the table has no value for becomes an `insufficient` cell, which is
 * what the backend sends when two series share too little history.
 */
function fullMatrix(ids: readonly number[], rho: (a: number, b: number) => number | null): CorrelationCell[] {
    const cells: CorrelationCell[] = [];
    for (const row of ids) {
        for (const column of ids) {
            const value = row === column ? 1 : rho(row, column);
            cells.push(value == null ? cell(row, column, null, 'insufficient') : cell(row, column, value));
        }
    }
    return cells;
}

/** The production path: index a full payload, then ask it questions. */
function lookupOf(ids: readonly number[], rho: (a: number, b: number) => number | null): CorrelationLookup {
    return buildLookup(fullMatrix(ids, rho));
}

const byId = (ids: readonly number[]): number[] => [...ids].sort((left, right) => left - right);

/** Unordered key, so a pair listed as (a,b) and one listed as (b,a) collide. */
const unorderedKey = (a: number, b: number): string => (a < b ? `${a}|${b}` : `${b}|${a}`);

/** True when every member of `group` sits in one uninterrupted run of `order`. */
function isContiguous(order: readonly number[], group: readonly number[]): boolean {
    const positions = group.map((id) => order.indexOf(id)).sort((left, right) => left - right);
    if (positions.some((position) => position < 0)) return false;
    return positions.every((position, index) => index === 0 || position === positions[index - 1] + 1);
}

/** The single point drawn for an unordered pair; throws rather than guessing. */
function pointFor(points: readonly HeatmapPoint[], a: number, b: number): HeatmapPoint {
    const found = points.filter((point) => unorderedKey(point.rowAssetId, point.columnAssetId) === unorderedKey(a, b));
    if (found.length !== 1) throw new Error(`expected exactly one point for (${a},${b}), found ${found.length}`);
    return found[0];
}

/** The single listed entry for an unordered pair; throws rather than guessing. */
function pairFor(pairs: readonly CorrelationPair[], a: number, b: number): CorrelationPair {
    const found = pairs.filter((pair) => unorderedKey(pair.rowAssetId, pair.columnAssetId) === unorderedKey(a, b));
    if (found.length !== 1) throw new Error(`expected exactly one pair for (${a},${b}), found ${found.length}`);
    return found[0];
}

describe('correlationBand', () => {
    it('reads a strong positive coefficient as high', () => {
        expect(correlationBand(0.95)).toBe('high');
        expect(correlationBand(1)).toBe('high');
    });

    it('treats 0.7 itself as moderate — the high band is open below', () => {
        expect(correlationBand(0.7)).toBe('moderate');
        expect(correlationBand(0.71)).toBe('high');
    });

    it('treats 0.3 itself as moderate — the moderate band is closed below', () => {
        expect(correlationBand(0.3)).toBe('moderate');
        expect(correlationBand(0.29)).toBe('low');
    });

    it('reads a weak positive coefficient as low', () => {
        expect(correlationBand(0)).toBe('low');
        expect(correlationBand(0.1)).toBe('low');
    });

    it('reads negative zero as zero rather than as inverse', () => {
        // −0 is zero, and zero is "no relationship" — not a compensating one.
        // JS answers `-0 < 0` with false, which lands on the right side here.
        expect(correlationBand(-0)).toBe('low');
    });

    it('calls any negative coefficient inverse, however strong it is', () => {
        // The sign is the finding: -0.95 is a hedge, not a redundancy, and
        // calling it "high" would invert the advice the panel gives.
        expect(correlationBand(-0.95)).toBe('inverse');
        expect(correlationBand(-0.95)).not.toBe('high');
        expect(correlationBand(-0.5)).toBe('inverse');
        expect(correlationBand(-0.01)).toBe('inverse');
        expect(correlationBand(-1)).toBe('inverse');
    });

    it('has no band for an unknown value, so the caller cannot say "low"', () => {
        expect(correlationBand(null)).toBeNull();
        expect(correlationBand(undefined)).toBeNull();
    });

    it('has no band for a non-finite value', () => {
        expect(correlationBand(Number.NaN)).toBeNull();
        expect(correlationBand(Number.POSITIVE_INFINITY)).toBeNull();
        expect(correlationBand(Number.NEGATIVE_INFINITY)).toBeNull();
    });
});

describe('buildLookup', () => {
    it('answers the same for (a,b) and for (b,a)', () => {
        const lookup = buildLookup([cell(1, 2, 0.42), cell(2, 1, 0.42)]);
        expect(lookup.get(1, 2)).toBe(0.42);
        expect(lookup.get(2, 1)).toBe(0.42);
        expect(lookup.get(1, 2)).toBe(lookup.get(2, 1));
    });

    it('returns the cell itself in either order, for observations and coverage', () => {
        const lookup = buildLookup([{row_asset_id: 3, column_asset_id: 9, value: 0.5, observations: 120, coverage: 0.8, status: 'ok'}]);
        expect(lookup.cell(3, 9)?.observations).toBe(120);
        expect(lookup.cell(9, 3)?.coverage).toBe(0.8);
    });

    it('has no value for a pair the payload never mentions', () => {
        const lookup = buildLookup([cell(1, 2, 0.42)]);
        expect(lookup.get(1, 7)).toBeNull();
        expect(lookup.cell(1, 7)).toBeUndefined();
    });

    it('refuses the number of a cell the backend did not stand behind', () => {
        // A number next to a non-ok status is leftover, not a measurement.
        const lookup = buildLookup([cell(1, 2, 0.99, 'insufficient')]);
        expect(lookup.get(1, 2)).toBeNull();
        expect(lookup.get(1, 2)).not.toBe(0.99);
    });

    it('still exposes the unusable cell, so the caller can explain the gap', () => {
        const lookup = buildLookup([cell(1, 2, null, 'undefined')]);
        expect(lookup.cell(1, 2)?.status).toBe('undefined');
    });

    it('prefers the usable half when the ok cell arrives first', () => {
        const lookup = buildLookup([cell(1, 2, 0.6, 'ok'), cell(2, 1, null, 'insufficient')]);
        expect(lookup.get(1, 2)).toBe(0.6);
        expect(lookup.get(2, 1)).toBe(0.6);
    });

    it('prefers the usable half when the ok cell arrives last', () => {
        // Same payload, opposite insertion order: the answer must not depend on it.
        const lookup = buildLookup([cell(1, 2, null, 'insufficient'), cell(2, 1, 0.6, 'ok')]);
        expect(lookup.get(1, 2)).toBe(0.6);
        expect(lookup.get(2, 1)).toBe(0.6);
    });

    it('refuses a non-finite number even when the status says ok', () => {
        expect(buildLookup([cell(1, 2, Number.NaN)]).get(1, 2)).toBeNull();
        expect(buildLookup([cell(1, 2, Number.POSITIVE_INFINITY)]).get(1, 2)).toBeNull();
    });

    it('treats an absent number as unknown even when the status says ok', () => {
        expect(buildLookup([cell(1, 2, null)]).get(1, 2)).toBeNull();
        expect(buildLookup([{row_asset_id: 1, column_asset_id: 2, status: 'ok'}]).get(1, 2)).toBeNull();
    });

    it('narrows a value the generated client widened into an array', () => {
        // The client types this field as `number | (number|null)[] | null` while
        // its own Zod schema parses a scalar. The narrowing is explicit so that
        // the day the API really does return a window, it is visible here
        // rather than hidden behind a cast.
        expect(buildLookup([{row_asset_id: 1, column_asset_id: 2, value: [0.44, 0.9], status: 'ok'}]).get(1, 2)).toBe(0.44);
    });

    it('treats a widened value with nothing usable in it as unknown', () => {
        expect(buildLookup([{row_asset_id: 1, column_asset_id: 2, value: [], status: 'ok'}]).get(1, 2)).toBeNull();
        expect(buildLookup([{row_asset_id: 1, column_asset_id: 2, value: [null], status: 'ok'}]).get(1, 2)).toBeNull();
        expect(buildLookup([{row_asset_id: 1, column_asset_id: 2, value: [Number.NaN], status: 'ok'}]).get(1, 2)).toBeNull();
    });

    it('survives a missing cell list instead of making the panel unrenderable', () => {
        for (const empty of [null, undefined, []]) {
            const lookup = buildLookup(empty);
            expect(lookup.get(1, 2)).toBeNull();
            expect(lookup.cell(1, 2)).toBeUndefined();
        }
    });
});

describe('correlationDistance', () => {
    it('puts an unknown pair at the maximum distance, never at zero', () => {
        // Dropping the unknown pair, or scoring it 0, would pull two assets
        // that were never compared into the same block.
        expect(correlationDistance(null)).toBe(1);
    });

    it('is 1 − |ρ|', () => {
        expect(correlationDistance(0.8)).toBeCloseTo(0.2, 10);
        expect(correlationDistance(0.25)).toBeCloseTo(0.75, 10);
    });

    it('ignores the sign: mirrored movement is still movement', () => {
        expect(correlationDistance(-0.8)).toBeCloseTo(correlationDistance(0.8), 10);
    });

    it('is zero for a perfect relationship and one for no relationship', () => {
        expect(correlationDistance(1)).toBe(0);
        expect(correlationDistance(-1)).toBe(0);
        expect(correlationDistance(0)).toBe(1);
    });

    it('clamps a coefficient outside [-1, 1] rather than returning a negative distance', () => {
        expect(correlationDistance(1.5)).toBe(0);
        expect(correlationDistance(-1.5)).toBe(0);
    });
});

describe('clusterOrder', () => {
    it('returns an input too short to cluster unchanged, as a copy', () => {
        const lookup = buildLookup([]);
        for (const ids of [[], [7], [7, 3]]) {
            const result = clusterOrder(ids, lookup);
            expect(result).toEqual(ids);
            // A copy, so the caller's payload order survives a later reorder.
            expect(result).not.toBe(ids);
        }
    });

    it('is a permutation of the ids it was given', () => {
        const cases: ReadonlyArray<readonly number[]> = [
            [1, 2, 3],
            [4, 9, 2, 7],
            [10, 20, 30, 40, 50, 60],
        ];
        const rho = pairTable([
            [1, 2, 0.9],
            [4, 9, -0.6],
            [2, 7, 0.1],
            [10, 20, 0.95],
            [30, 40, 0.8],
        ]);
        for (const ids of cases) {
            const result = clusterOrder(ids, lookupOf(ids, rho));
            expect(byId(result)).toEqual(byId(ids));
            expect(result).toHaveLength(ids.length);
        }
    });

    it('puts two tight blocks next to each other', () => {
        // Deliberately interleaved on input, so the identity order would fail.
        const ids = [1, 3, 2, 4];
        const rho = pairTable([
            [1, 2, 0.98],
            [3, 4, 0.97],
            [1, 3, 0.05],
            [1, 4, 0.05],
            [2, 3, 0.05],
            [2, 4, 0.05],
        ]);
        const order = clusterOrder(ids, lookupOf(ids, rho));
        expect(isContiguous(order, [1, 2])).toBe(true);
        expect(isContiguous(order, [3, 4])).toBe(true);
    });

    it('keeps an asset that correlates with nothing without breaking the block', () => {
        const ids = [1, 2, 3, 99];
        const rho = pairTable([
            [1, 2, 0.96],
            [1, 3, 0.94],
            [2, 3, 0.95],
        ]);
        const order = clusterOrder(ids, lookupOf(ids, rho));
        expect(byId(order)).toEqual(byId(ids));
        expect(isContiguous(order, [1, 2, 3])).toBe(true);
    });

    it('is deterministic: the same matrix always draws the same picture', () => {
        // Ties resolved by the lower slot index — the asset's position in the
        // payload — never by Map order. A reload that reshuffles the matrix
        // reads as new information when it is not.
        const ids = [5, 6, 7, 8, 9];
        const rho = pairTable([
            [5, 6, 0.5],
            [7, 8, 0.5],
            [5, 7, 0.5],
            [6, 8, 0.5],
            [8, 9, 0.5],
        ]);
        const lookup = lookupOf(ids, rho);
        expect(clusterOrder(ids, lookup)).toEqual(clusterOrder(ids, lookup));
    });

    it('keeps every asset, exactly once, on a matrix the size the API allows', () => {
        // The merge loop tracks live clusters by slot and empties the
        // right-hand one; a bookkeeping slip would drop or duplicate an asset,
        // and at four assets it would not show. Sixty is nearer the size D19
        // deliberately permits.
        const many = Array.from({length: 60}, (_, index) => index + 1);
        const entries: Array<readonly [number, number, number]> = [];
        for (let index = 0; index < 20; index += 1) entries.push([many[index], many[index + 20], 0.9 - index / 100]);
        const order = clusterOrder(many, lookupOf(many, pairTable(entries)));
        expect(byId(order)).toEqual(many);
        expect(new Set(order).size).toBe(many.length);
    });

    it('still returns every id when not one pair is usable', () => {
        // Every distance is the maximum; the merge loop must still terminate.
        // This test completing at all is the "does not hang" assertion.
        const ids = [1, 2, 3, 4, 5, 6];
        const cells = ids.flatMap((row) => ids.map((column) => cell(row, column, null, 'insufficient')));
        const order = clusterOrder(ids, buildLookup(cells));
        expect(byId(order)).toEqual(byId(ids));
    });
});

describe('topPairs', () => {
    const ids = [1, 2, 3, 4];
    const rho = pairTable([
        [1, 2, 0.91],
        [1, 3, 0.55],
        [1, 4, -0.72],
        [2, 3, 0.2],
        [2, 4, -0.33],
        [3, 4, 0.44],
    ]);

    it('lists every unordered pair once, and never an asset against itself', () => {
        const {correlated, offsetting} = topPairs(ids, lookupOf(ids, rho), 100);
        const all = [...correlated, ...offsetting];
        // 4 assets → 6 unordered pairs, from a payload of 16 cells.
        expect(all).toHaveLength(6);
        expect(all.some((pair) => pair.rowAssetId === pair.columnAssetId)).toBe(false);
        const keys = new Set(all.map((pair) => unorderedKey(pair.rowAssetId, pair.columnAssetId)));
        expect(keys.size).toBe(all.length);
    });

    it('sorts the correlated list from the strongest down', () => {
        const {correlated} = topPairs(ids, lookupOf(ids, rho), 100);
        expect(correlated.map((pair) => pair.value)).toEqual([0.91, 0.55, 0.44, 0.2]);
    });

    it('sorts the offsetting list with the most negative first', () => {
        const {offsetting} = topPairs(ids, lookupOf(ids, rho), 100);
        expect(offsetting.map((pair) => pair.value)).toEqual([-0.72, -0.33]);
    });

    it('bands each pair exactly as the band helper would', () => {
        const {correlated, offsetting} = topPairs(ids, lookupOf(ids, rho), 100);
        for (const pair of [...correlated, ...offsetting]) {
            expect(pair.band).toBe(correlationBand(pair.value));
        }
    });

    it('flags a pair sitting exactly on the near-identical threshold', () => {
        // The threshold is inclusive: a pair *at* it is already two names for
        // one bet, and the constant is used rather than retyped as 0.9.
        const threshold = [1, 2, 3];
        const table = pairTable([
            [1, 2, NEAR_IDENTICAL],
            [1, 3, NEAR_IDENTICAL - 0.01],
            [2, 3, 0.1],
        ]);
        const {correlated} = topPairs(threshold, lookupOf(threshold, table), 100);
        expect(pairFor(correlated, 1, 2).nearIdentical).toBe(true);
        expect(pairFor(correlated, 1, 3).nearIdentical).toBe(false);
    });

    it('truncates each list to the limit it was given', () => {
        const many = [1, 2, 3, 4];
        const table = pairTable([
            [1, 2, 0.9],
            [1, 3, 0.8],
            [1, 4, -0.9],
            [2, 3, 0.7],
            [2, 4, -0.8],
            [3, 4, -0.7],
        ]);
        const {correlated, offsetting} = topPairs(many, lookupOf(many, table), 2);
        expect(correlated.map((pair) => pair.value)).toEqual([0.9, 0.8]);
        expect(offsetting.map((pair) => pair.value)).toEqual([-0.9, -0.8]);
    });

    it('skips the pairs the backend could not compute', () => {
        const partial = [1, 2, 3];
        const table = pairTable([[1, 2, 0.8]]); // (1,3) and (2,3) come back insufficient
        const {correlated, offsetting} = topPairs(partial, lookupOf(partial, table), 100);
        const keys = [...correlated, ...offsetting].map((pair) => unorderedKey(pair.rowAssetId, pair.columnAssetId));
        expect(keys).toEqual([unorderedKey(1, 2)]);
    });

    it('returns an empty offsetting list when nothing offsets anything', () => {
        const positive = [1, 2, 3];
        const table = pairTable([
            [1, 2, 0.8],
            [1, 3, 0.6],
            [2, 3, 0.4],
        ]);
        const {correlated, offsetting} = topPairs(positive, lookupOf(positive, table), 100);
        expect(correlated).toHaveLength(3);
        expect(offsetting).toEqual([]);
    });

    it('returns two empty lists when no pair is usable at all', () => {
        const unknown = [1, 2, 3];
        const {correlated, offsetting} = topPairs(unknown, lookupOf(unknown, pairTable([])), 100);
        expect(correlated).toEqual([]);
        expect(offsetting).toEqual([]);
    });

    it('breaks a tie by asset id rather than by the order the pairs were walked', () => {
        // The ids are walked as [4, 2, 3, 1], so the tied pair discovered first
        // is the one with the *higher* rowAssetId. Sorting must still put 1
        // before 2, or the list reshuffles whenever the payload order changes.
        const tied = [4, 2, 3, 1];
        const table = pairTable([
            [2, 4, 0.5],
            [1, 3, 0.5],
            [1, 2, 0.1],
            [1, 4, 0.1],
            [2, 3, 0.1],
            [3, 4, 0.1],
        ]);
        const {correlated} = topPairs(tied, lookupOf(tied, table), 2);
        expect(correlated.map((pair: CorrelationPair) => pair.rowAssetId)).toEqual([1, 2]);
    });

    it('leaves a perfectly uncorrelated pair out of both lists', () => {
        // Documented consequence of the `> 0` / `< 0` split: ρ = 0 is a real
        // finding ("these two are unrelated") that neither list reports.
        const zeroed = [1, 2];
        const {correlated, offsetting} = topPairs(zeroed, lookupOf(zeroed, pairTable([[1, 2, 0]])), 100);
        expect(correlated).toEqual([]);
        expect(offsetting).toEqual([]);
    });
});

describe('lowerTrianglePoints', () => {
    const ids = [10, 20, 30, 40, 50];
    const rho = pairTable([
        [10, 20, 0.8],
        [10, 30, 0.2],
        [10, 40, -0.4],
        [10, 50, 0.6],
        [20, 30, 0.35],
        [20, 40, 0.1],
        [20, 50, -0.15],
        [30, 40, 0.5],
        [30, 50, 0.05],
        [40, 50, 0.7],
    ]);

    it('emits one point per unordered pair, dropping the diagonal and the mirror', () => {
        const points = lowerTrianglePoints(ids, lookupOf(ids, rho));
        // 5 assets: 25 payload cells in, 10 points out.
        expect(points).toHaveLength((ids.length * (ids.length - 1)) / 2);
        expect(points.some((point) => point.rowAssetId === point.columnAssetId)).toBe(false);
        const keys = new Set(points.map((point) => unorderedKey(point.rowAssetId, point.columnAssetId)));
        expect(keys.size).toBe(points.length);
    });

    it('indexes each point as [column, row, value] against the order it was given', () => {
        const three = [10, 20, 30];
        const points = lowerTrianglePoints(three, lookupOf(three, rho));
        expect(pointFor(points, 20, 10).value).toEqual([0, 1, 0.8]);
        expect(pointFor(points, 30, 10).value).toEqual([0, 2, 0.2]);
        expect(pointFor(points, 30, 20).value).toEqual([1, 2, 0.35]);
    });

    it('moves the indices when the clustering hands it a different order', () => {
        // Same payload, order reshuffled by clusterOrder: the pairs are the
        // same facts, but each one must land on its new square.
        const three = [10, 20, 30];
        const lookup = lookupOf(three, rho);
        const points = lowerTrianglePoints([30, 10, 20], lookup);
        expect(pointFor(points, 10, 30).value).toEqual([0, 1, 0.2]);
        expect(pointFor(points, 20, 30).value).toEqual([0, 2, 0.35]);
        expect(pointFor(points, 20, 10).value).toEqual([1, 2, 0.8]);
    });

    it('agrees with the lookup on every value it draws, present or absent', () => {
        // The point and the tooltip must not be able to disagree: both read the
        // number through the same lookup. The payload here is deliberately
        // mixed — computed, uncomputable, and never sent — so the agreement is
        // asserted over nulls too, not only over numbers.
        const mixed = buildLookup([cell(10, 20, 0.8), cell(20, 10, 0.8), cell(10, 30, null, 'insufficient'), cell(30, 10, null, 'insufficient')]);
        const points = lowerTrianglePoints([10, 20, 30], mixed);
        expect(points).toHaveLength(3);
        for (const point of points) {
            expect(point.value[2]).toBe(mixed.get(point.rowAssetId, point.columnAssetId));
        }
    });

    it('draws no number for a NaN the backend called ok', () => {
        // The lookup refuses a non-finite number whatever the status claims,
        // and the chart reads the value through the lookup — so the square is
        // blank rather than carrying a NaN into ECharts.
        const lookup = buildLookup([cell(1, 2, Number.NaN), cell(2, 1, Number.NaN)]);
        const points = lowerTrianglePoints([1, 2], lookup);
        expect(points).toHaveLength(1);
        expect(points[0].value[2]).toBeNull();
        expect(points[0].value[2]).toBe(lookup.get(1, 2));
        // The cell itself is still reported as ok: it exists, its number does not.
        expect(points[0].status).toBe('ok');
    });

    it('keeps an uncomputable cell on the chart, with no number in it', () => {
        // The square must stay visible as "unknown"; a hole would read as a
        // pair nobody asked about.
        const points = lowerTrianglePoints([1, 2], buildLookup([cell(1, 2, null, 'insufficient'), cell(2, 1, null, 'insufficient')]));
        expect(points).toHaveLength(1);
        expect(points[0].value[2]).toBeNull();
        expect(points[0].status).toBe('insufficient');
    });

    it('reports a cell with no status as the backend undefined status', () => {
        const points = lowerTrianglePoints([1, 2], buildLookup([{row_asset_id: 2, column_asset_id: 1, value: 0.3}]));
        expect(points[0].status).toBe('undefined');
        expect(points[0].value[2]).toBeNull();
    });

    it('defaults absent observations and coverage to zero', () => {
        const points = lowerTrianglePoints([1, 2], buildLookup([{row_asset_id: 2, column_asset_id: 1, value: 0.3, status: 'ok'}]));
        expect(points[0].observations).toBe(0);
        expect(points[0].coverage).toBe(0);
        expect(points[0].value[2]).toBe(0.3);
    });

    it('keeps the square of a pair the payload never mentioned at all', () => {
        // The axes come from `asset_ids`, so both assets are on the chart
        // whatever the cells say. A pair the backend never sent must occupy its
        // square as an unknown rather than leave a hole nothing explains.
        const three = [1, 2, 3];
        const points = lowerTrianglePoints(three, buildLookup([cell(2, 1, 0.5), cell(1, 2, 0.5), cell(3, 2, 0.4), cell(2, 3, 0.4)]));
        expect(points).toHaveLength((three.length * (three.length - 1)) / 2);
        const missing = pointFor(points, 1, 3);
        expect(missing.value[2]).toBeNull();
        expect(missing.status).toBe('undefined');
        expect(missing.observations).toBe(0);
        expect(missing.coverage).toBe(0);
    });

    it('emits n(n-1)/2 points whatever the payload contains, down to nothing', () => {
        // The count is a property of the rendered order alone. An empty payload
        // draws a complete, entirely unknown triangle.
        const order = [1, 2, 3, 4, 5];
        const points = lowerTrianglePoints(order, buildLookup([]));
        expect(points).toHaveLength((order.length * (order.length - 1)) / 2);
        expect(points.every((point) => point.value[2] === null)).toBe(true);
        expect(points.every((point) => point.status === 'undefined')).toBe(true);
        const keys = new Set(points.map((point) => unorderedKey(point.rowAssetId, point.columnAssetId)));
        expect(keys.size).toBe(points.length);
    });

    it('emits nothing for an order too short to have a pair', () => {
        const lookup = lookupOf(ids, rho);
        expect(lowerTrianglePoints([], lookup)).toEqual([]);
        expect(lowerTrianglePoints([10], lookup)).toEqual([]);
    });
});

describe('thresholds', () => {
    it('places near-identical inside the high band', () => {
        // Otherwise a pair could be flagged as "the same bet" while the legend
        // beside it reads "moderate".
        expect(correlationBand(NEAR_IDENTICAL)).toBe('high');
    });

    it('hands the matrix over to the pair list only past a readable size', () => {
        // Consumed by CorrelationHeatmap, which promotes the pair list ahead of
        // the matrix above this size. ECharts already drops the in-cell numbers
        // past 12; promoting earlier would displace a chart nobody had trouble
        // reading.
        expect(PAIR_LIST_THRESHOLD).toBeGreaterThanOrEqual(12);
    });
});

/**
 * The premise the E2E ordering test rests on.
 *
 * `risk-lab.spec.ts` proves the similarity toggle by asserting that a twin pair
 * planted *far apart* in payload order becomes adjacent once clustered. That
 * assertion is only honest if the stubbed topology really does permute — and an
 * earlier version of the stub did not: with the twin at position 1 the pair was
 * already adjacent, `clusterOrder` returned the input unchanged, and the E2E
 * would have compared a value with itself. This pins the corrected topology so
 * the E2E premise cannot rot silently.
 */
describe('clusterOrder — the E2E stub topology', () => {
    const stubRho =
        (ids: readonly number[]) =>
        (a: number, b: number): number => {
            const i = ids.indexOf(a);
            const j = ids.indexOf(b);
            const [low, high] = i < j ? [i, j] : [j, i];
            if (low === 0 && high === 3) return 0.97;
            if (low === 0 && high === 2) return -0.82;
            return 0.12;
        };

    // The spec floors the selection at 4 and caps the drawn matrix at 8, so every
    // size in between has to behave.
    it('pulls a distant twin adjacent, and never returns the payload order, for every size the spec can reach', () => {
        for (let size = 4; size <= 8; size += 1) {
            const ids = Array.from({length: size}, (_, index) => 101 + index);
            const order = clusterOrder(ids, lookupOf(ids, stubRho(ids)));

            expect(byId(order), `size ${size} must stay a permutation`).toEqual(byId(ids));
            // Positions 0 and 3 are three apart on input and must end up touching.
            expect(isContiguous(order, [ids[0], ids[3]]), `size ${size} must cluster the twins`).toBe(true);
            expect(isContiguous(ids, [ids[0], ids[3]]), `size ${size} must NOT already be clustered on input`).toBe(false);
            expect(order, `size ${size} must differ from the payload order`).not.toEqual([...ids]);
        }
    });
});
