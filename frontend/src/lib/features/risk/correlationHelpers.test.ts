/**
 * @vitest-environment node
 *
 * correlationHelpers — pure unit tests (node env, no jsdom).
 *
 * These are the decisions the correlation view makes *before* ECharts exists:
 * how a coefficient is read in words, how a symmetric payload is indexed, how
 * assets are reordered so redundancy shows up as a square, which half of the
 * matrix is actually drawn, and how large the canvas must be for it to stay
 * legible. `CorrelationHeatmap.svelte` mounts a canvas and
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

import {
    DOMINANT_SHARE,
    HEATMAP_CELL,
    NEAR_IDENTICAL,
    OTHER_EXPOSURE,
    PAIR_LIST_THRESHOLD,
    buildLookup,
    clusterOrder,
    correlationBand,
    correlationDistance,
    dominantExposure,
    exposureOrder,
    heatmapLayout,
    lowerTrianglePoints,
    nameOrder,
    pairKey,
    plainName,
    topPairs,
    typeOrder,
    type CorrelationBand,
    type CorrelationCell,
    type CorrelationLookup,
    type CorrelationPair,
    type ExposureGroup,
    type HeatmapPoint,
} from './correlationHelpers';

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
        // It lies well inside the low band (−0.3, 0.3), whichever sign it carries.
        expect(correlationBand(-0)).toBe('low');
    });

    it('calls a coefficient inverse only from −0.3 down, however strong it is', () => {
        // A strong negative is a hedge, not a redundancy: calling −0.95 "high"
        // would invert the advice the panel gives. The band is closed at −0.3,
        // the mirror of the moderate band's closed 0.3.
        expect(correlationBand(-0.95)).toBe('inverse');
        expect(correlationBand(-0.95)).not.toBe('high');
        expect(correlationBand(-0.5)).toBe('inverse');
        expect(correlationBand(-0.3)).toBe('inverse');
        expect(correlationBand(-1)).toBe('inverse');
    });

    it('reads a weak negative coefficient as low, like its positive mirror', () => {
        // Calling −0.01 "inverse" told the reader that two unrelated assets offset
        // each other (F-3b, V8). Inside (−0.3, 0.3) a pair is low whatever its sign.
        expect(correlationBand(-0.29)).toBe('low');
        expect(correlationBand(-0.01)).toBe('low');
        for (const magnitude of [0.01, 0.1, 0.29]) {
            expect(correlationBand(-magnitude), `ρ = ±${magnitude}`).toBe(correlationBand(magnitude));
        }
    });

    it('puts each value on the documented side of every symmetric boundary', () => {
        // The whole rule in one table: inverse ≤ −0.3 < low < 0.3 ≤ moderate ≤ 0.7 < high.
        const cases: ReadonlyArray<readonly [number, CorrelationBand]> = [
            [-1, 'inverse'],
            [-0.3, 'inverse'],
            [-0.29, 'low'],
            [-0.01, 'low'],
            [-0, 'low'],
            [0, 'low'],
            [0.29, 'low'],
            [0.3, 'moderate'],
            [0.7, 'moderate'],
            [0.71, 'high'],
        ];
        for (const [value, band] of cases) {
            expect(correlationBand(value), `ρ = ${Object.is(value, -0) ? '-0' : value}`).toBe(band);
        }
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

describe('pairKey', () => {
    it('names a pair with one key, whichever way round it is given', () => {
        expect(pairKey(3, 7)).toBe(pairKey(7, 3));
        expect(pairKey(120, 45)).toBe(pairKey(45, 120));
    });

    it('gives distinct unordered pairs distinct keys, even when their digits run together', () => {
        // Concatenated without a separator, (1, 234) and (12, 34) would both read "1234".
        expect(pairKey(1, 234)).not.toBe(pairKey(12, 34));
        const ids = [1, 2, 3, 4, 12, 23, 34, 123, 234];
        const keys = new Set<string>();
        for (const a of ids) {
            for (const b of ids) {
                if (a !== b) keys.add(pairKey(a, b));
            }
        }
        // Both orders of every pair went in: one key per unordered pair, none shared.
        expect(keys.size).toBe((ids.length * (ids.length - 1)) / 2);
    });

    it('joins the ranking and the matrix, which name the same pair in opposite orders', () => {
        // The ranking walks the payload order, the matrix the order on screen. Here
        // the two disagree, so each holds the pair the other way round — and the key
        // is what lets a click in one select the same pair in the other.
        const payload = [1, 2, 3];
        const lookup = lookupOf(payload, pairTable([[1, 3, 0.8]]));
        const [listed] = topPairs(payload, lookup, 100).correlated;
        const drawn = pointFor(lowerTrianglePoints([3, 2, 1], lookup), 1, 3);
        expect([listed.rowAssetId, listed.columnAssetId]).toEqual([3, 1]);
        expect([drawn.rowAssetId, drawn.columnAssetId]).toEqual([1, 3]);
        expect(pairKey(listed.rowAssetId, listed.columnAssetId)).toBe(pairKey(drawn.rowAssetId, drawn.columnAssetId));
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

describe('plainName', () => {
    // Invisible glue is written as escapes, so the reader can see what each
    // fixture holds; visible glyphs are left as a user would type them.

    it('drops flags and markers from either end of a name', () => {
        expect(plainName('🇪🇺👑 Amundi MSCI')).toBe('Amundi MSCI');
        expect(plainName("Btp Piu' Sc Fb33 Eur 🇮🇹")).toBe("Btp Piu' Sc Fb33 Eur");
    });

    it('keeps the digit of a keycap and drops only its marks', () => {
        // Keycap one is "1" + VARIATION SELECTOR-16 + COMBINING ENCLOSING KEYCAP:
        // the digit is text the user typed, the two marks after it are decoration.
        expect(plainName('1\uFE0F\u20E3 Uno')).toBe('1 Uno');
    });

    it('drops a skin tone with its emoji, and a ZWJ sequence with its joiners', () => {
        // Thumbs up + medium skin tone; then man, woman, girl held together by two
        // ZERO WIDTH JOINERs — one family glyph on screen, five code points here.
        expect(plainName('\u{1F44D}\u{1F3FD} Bravo')).toBe('Bravo');
        expect(plainName('\u{1F468}\u200D\u{1F469}\u200D\u{1F467} Family Fund')).toBe('Family Fund');
    });

    it('drops the invisible tags of a subdivision flag', () => {
        // The Scottish flag: a black flag, tag characters spelling "gbsct", CANCEL TAG.
        expect(plainName('\u{1F3F4}\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F} Scottish Mortgage')).toBe('Scottish Mortgage');
    });

    it('collapses the whitespace an emoji leaves behind, and trims the ends', () => {
        expect(plainName('Amundi 🇪🇺 MSCI')).toBe('Amundi MSCI');
        expect(plainName('  Amundi \t\n MSCI  ')).toBe('Amundi MSCI');
    });

    it('leaves letters, digits, accents and punctuation alone', () => {
        // `#` and the digits are keycap *bases*, not pictographs: a filter on the
        // wider Emoji property would eat them, and with them real text.
        expect(plainName('Société Générale')).toBe('Société Générale');
        expect(plainName('S&P 500 #1')).toBe('S&P 500 #1');
    });

    it('keeps text symbols that can be emoji but are not drawn as one', () => {
        // ®, © and ™ are pictographs to Unicode, but text by default: they belong to
        // the name. The sun is written as an escape so it is plain no VS16 follows.
        expect(plainName('SPDR® S&P 500® ETF Trust')).toBe('SPDR® S&P 500® ETF Trust');
        expect(plainName('Fondo© Test™')).toBe('Fondo© Test™');
        expect(plainName('Solar \u2600 Fund')).toBe('Solar \u2600 Fund');
    });

    it('drops a text pictograph that VS16 turns into an emoji, selector and all', () => {
        // The red heart is U+2764 + VARIATION SELECTOR-16. The same sun as above goes
        // too once it carries the selector: the selector decides, not the symbol.
        expect(plainName('\u2764\uFE0F Love ETF')).toBe('Love ETF');
        expect(plainName('Solar \u2600\uFE0F Fund')).toBe('Solar Fund');
    });

    it('returns a name made only of emoji unchanged, rather than an empty string', () => {
        expect(plainName('🇮🇹')).toBe('🇮🇹');
        expect(plainName('🇪🇺👑')).toBe('🇪🇺👑');
    });
});

describe('nameOrder', () => {
    // The locale is pinned in every case: `Intl.Collator` otherwise follows the
    // host, and a collation test that passes on one machine's locale and not on
    // another's is testing the machine.
    const LOCALE = 'en';

    /** Names as the heatmap's `nameOf` resolves them: the label, or `#id` when there is none. */
    function namesOf(table: Record<number, string>): (assetId: number) => string {
        return (assetId) => table[assetId] ?? `#${assetId}`;
    }

    it('orders by the name the reader sees, not by id', () => {
        // Ids ascend while the names do not, so the two orders disagree here —
        // which is the only kind of fixture that can tell them apart.
        expect(nameOrder([1, 2, 3], namesOf({1: 'Tesla', 2: 'Apple', 3: 'Microsoft'}), LOCALE)).toEqual([2, 3, 1]);
    });

    it('files names regardless of case and accents, as the reader does', () => {
        // A code-point sort would put every capital first and `É` after `z`
        // ([4, 3, 1, 2] here); base sensitivity reads the letters.
        expect(nameOrder([1, 2, 3, 4], namesOf({1: 'zeta', 2: 'Éclair', 3: 'apple', 4: 'Delta'}), LOCALE)).toEqual([3, 4, 2, 1]);
    });

    it('treats names that differ only in case or accent as equal, and settles them by id', () => {
        expect(nameOrder([9, 4, 7], namesOf({9: 'Été', 4: 'ete', 7: 'ETE'}), LOCALE)).toEqual([4, 7, 9]);
    });

    it('reads the numbers inside a name as numbers', () => {
        // "ETF 2" before "ETF 10": a plain string sort reverses them.
        expect(nameOrder([1, 2, 3], namesOf({1: 'ETF 10', 2: 'ETF 2', 3: 'ETF 1'}), LOCALE)).toEqual([3, 2, 1]);
    });

    it('breaks a tie between equal names by id, so the order is stable across renders', () => {
        expect(nameOrder([30, 10, 20], namesOf({30: 'Same', 10: 'Same', 20: 'Same'}), LOCALE)).toEqual([10, 20, 30]);
    });

    it('sorts the `#id` fallback of an unnamed asset like any other name', () => {
        // `#3` before `#12` numerically, and both before a letter.
        expect(nameOrder([12, 5, 3], namesOf({5: 'Bond'}), LOCALE)).toEqual([3, 12, 5]);
    });

    it('ignores the emoji in a name, so a decorated name does not file ahead of a plain one', () => {
        // Flags and markers typed into user names. Collated raw, every decorated
        // name files first ([1, 4, 2, 3] here); the reader sees Amundi, Btp,
        // iShares, Xtrackers.
        const names = namesOf({1: '🇪🇺 iShares Healthcare', 2: '🇪🇺👑 Amundi Semiconductors', 3: "Btp Piu' Sc Fb33 Eur 🇮🇹", 4: '🇪🇺 Xtrackers World'});
        expect(nameOrder([1, 2, 3, 4], names, LOCALE)).toEqual([2, 3, 1, 4]);
    });

    it('compares a name made only of emoji as itself, not as an empty string', () => {
        // The collator files punctuation before emoji, and emoji before letters.
        // Emptied, both flags would read as '' — first, and tied, so [1, 2, 3].
        // Kept whole, they file after the bracketed name, and by their own
        // letters: 🇪🇺 before 🇮🇹.
        expect(nameOrder([1, 2, 3], namesOf({1: '🇮🇹', 2: '🇪🇺', 3: '(Bravo)'}), LOCALE)).toEqual([3, 2, 1]);
    });

    it('lets names that differ only in their emoji tie, and settles them by id', () => {
        // Collated raw, the flag would decide ([30, 20, 10]); stripped, all three
        // read "Amundi" and the id breaks the tie, as for any equal names.
        expect(nameOrder([30, 10, 20], namesOf({30: '🇪🇺 Amundi', 10: 'Amundi 🇮🇹', 20: 'Amundi'}), LOCALE)).toEqual([10, 20, 30]);
    });

    it('returns a new array and leaves the one it was given alone', () => {
        // The heatmap hands over the payload's own `asset_ids`, which the similarity
        // ordering reads too: sorting it in place would change that input behind
        // its back.
        const ids = [3, 1, 2];
        const result = nameOrder(ids, namesOf({1: 'C', 2: 'B', 3: 'A'}), LOCALE);
        expect(result).toEqual([3, 2, 1]);
        expect(ids).toEqual([3, 1, 2]);
        expect(result).not.toBe(ids);
    });
});

describe('topPairs', () => {
    // A ranking takes only the pairs that clear its band: `high` (ρ > 0.7) for
    // the correlated list, `inverse` (ρ ≤ −0.3) for the offsetting one. Every
    // band is represented here, and the walk meets each ranking's pairs weakest
    // first, so neither sort can go missing unnoticed.
    const ids = [1, 2, 3, 4];
    const rho = pairTable([
        [1, 2, 0.75], // high
        [1, 3, 0.55], // moderate: in neither ranking
        [1, 4, -0.33], // inverse
        [2, 3, 0.91], // high
        [2, 4, -0.72], // inverse
        [3, 4, -0.2], // low, although negative: in neither ranking
    ]);

    it('lists each pair that clears a band once, and never an asset against itself', () => {
        // Every pair here clears a band, so the two rankings together must hold
        // all six and no more. The payload's diagonal is ρ = 1, which would clear
        // the high band too: a walk that visited it, or both halves of the
        // matrix, would change the count.
        const cleared = [1, 2, 3, 4];
        const table = pairTable([
            [1, 2, 0.95],
            [1, 3, -0.6],
            [1, 4, 0.8],
            [2, 3, 0.75],
            [2, 4, -0.9],
            [3, 4, -0.45],
        ]);
        const {correlated, offsetting} = topPairs(cleared, lookupOf(cleared, table), 100);
        const all = [...correlated, ...offsetting];
        // 4 assets → 6 unordered pairs, from a payload of 16 cells.
        expect(all).toHaveLength(6);
        expect(all.some((pair) => pair.rowAssetId === pair.columnAssetId)).toBe(false);
        const keys = new Set(all.map((pair) => unorderedKey(pair.rowAssetId, pair.columnAssetId)));
        expect(keys.size).toBe(all.length);
    });

    it('sorts the correlated list from the strongest down', () => {
        // 0.55 is positive but only moderate: listing it under "most similar"
        // claimed a redundancy the number does not support.
        const {correlated} = topPairs(ids, lookupOf(ids, rho), 100);
        expect(correlated.map((pair) => pair.value)).toEqual([0.91, 0.75]);
    });

    it('sorts the offsetting list with the most negative first', () => {
        // −0.2 is negative but low: it stays out.
        const {offsetting} = topPairs(ids, lookupOf(ids, rho), 100);
        expect(offsetting.map((pair) => pair.value)).toEqual([-0.72, -0.33]);
    });

    it('admits a pair only once it clears a band: above 0.7, or at −0.3 and below', () => {
        // One pair on each side of each threshold. 0.7 is still moderate and
        // −0.29 still low, so both stay out — as do 0.55 and −0.01, which the
        // rankings used to list as "most similar" and "offsetting" (F-3b, V8).
        const edges = [1, 2, 3, 4];
        const table = pairTable([
            [1, 2, 0.71],
            [1, 3, 0.7],
            [1, 4, 0.55],
            [2, 3, -0.3],
            [2, 4, -0.29],
            [3, 4, -0.01],
        ]);
        const {correlated, offsetting} = topPairs(edges, lookupOf(edges, table), 100);
        expect(correlated.map((pair) => pair.value)).toEqual([0.71]);
        expect(offsetting.map((pair) => pair.value)).toEqual([-0.3]);
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
        // Three pairs clear each band, so a limit of 2 really cuts both lists; and
        // the walk meets the weakest first, so the cut must come after the ranking.
        const many = [1, 2, 3, 4];
        const table = pairTable([
            [1, 2, 0.75],
            [1, 3, 0.8],
            [1, 4, -0.7],
            [2, 3, 0.9],
            [2, 4, -0.8],
            [3, 4, -0.9],
        ]);
        const lookup = lookupOf(many, table);
        const uncut = topPairs(many, lookup, 100);
        expect([uncut.correlated.length, uncut.offsetting.length]).toEqual([3, 3]);
        const {correlated, offsetting} = topPairs(many, lookup, 2);
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
        // Negative is not enough: −0.29 and −0.01 sit in the low band. A
        // near-zero coefficient says two assets are unrelated, not that one
        // hedges the other.
        const unhedged = [1, 2, 3];
        const table = pairTable([
            [1, 2, 0.8],
            [1, 3, -0.29],
            [2, 3, -0.01],
        ]);
        const {correlated, offsetting} = topPairs(unhedged, lookupOf(unhedged, table), 100);
        expect(correlated.map((pair) => pair.value)).toEqual([0.8]);
        expect(offsetting).toEqual([]);
    });

    it('returns two empty lists when no pair is usable at all', () => {
        const unknown = [1, 2, 3];
        const {correlated, offsetting} = topPairs(unknown, lookupOf(unknown, pairTable([])), 100);
        expect(correlated).toEqual([]);
        expect(offsetting).toEqual([]);
    });

    it('returns two empty lists when every pair sits between the thresholds', () => {
        // Unlike the case above, every pair here is known: the matrix is complete
        // and simply holds nothing strong enough to rank.
        const between = [1, 2, 3, 4];
        const table = pairTable([
            [1, 2, 0.7],
            [1, 3, 0.55],
            [1, 4, 0.29],
            [2, 3, 0],
            [2, 4, -0.01],
            [3, 4, -0.29],
        ]);
        const lookup = lookupOf(between, table);
        expect(lowerTrianglePoints(between, lookup).every((point) => point.value[2] !== null)).toBe(true);
        const {correlated, offsetting} = topPairs(between, lookup, 100);
        expect(correlated).toEqual([]);
        expect(offsetting).toEqual([]);
    });

    it('breaks a tie by asset id rather than by the order the pairs were walked', () => {
        // The ids are walked as [4, 2, 3, 1], so in each ranking the tied pair
        // discovered first is the one with the *higher* rowAssetId. Sorting must
        // still settle each tie by rowAssetId, or two equal coefficients would be
        // listed in whatever order the walk happened to meet them.
        const tied = [4, 2, 3, 1];
        const table = pairTable([
            [2, 4, 0.8],
            [1, 3, 0.8],
            [3, 4, -0.6],
            [1, 2, -0.6],
            [1, 4, 0.1],
            [2, 3, 0.1],
        ]);
        const {correlated, offsetting} = topPairs(tied, lookupOf(tied, table), 100);
        const rowThenColumn = (pair: CorrelationPair) => [pair.rowAssetId, pair.columnAssetId];
        expect(correlated.map(rowThenColumn)).toEqual([
            [1, 3],
            [2, 4],
        ]);
        expect(offsetting.map(rowThenColumn)).toEqual([
            [1, 2],
            [3, 4],
        ]);
    });

    it('leaves a perfectly uncorrelated pair out of both lists', () => {
        // ρ = 0 is a real finding ("these two are unrelated") that neither
        // ranking reports: it sits in the low band, which feeds neither list.
        const zeroed = [1, 2];
        const {correlated, offsetting} = topPairs(zeroed, lookupOf(zeroed, pairTable([[1, 2, 0]])), 100);
        expect(correlated).toEqual([]);
        expect(offsetting).toEqual([]);
    });
});

describe('typeOrder', () => {
    // Pinned for the same reason as in nameOrder: the names go through a collator.
    const LOCALE = 'en';
    // The test's own menu, in the app's relative order for these three types.
    // typeOrder takes the order as a parameter, which keeps the module — and so
    // this test — free of the taxonomy.
    const RANK = ['STOCK', 'BOND', 'ETF'];

    /** `typeOf` and `nameOf` from one table; an entry without `type` answers `undefined`. */
    function assets(table: Record<number, {type?: string | null; name: string}>) {
        return {
            typeOf: (assetId: number) => table[assetId]?.type,
            nameOf: (assetId: number) => table[assetId]?.name ?? `#${assetId}`,
        };
    }

    it('groups assets by the rank of their type, then orders each group by name', () => {
        // By name alone this would be Amundi, Apple, Btp, Tesla, Vanguard.
        const {typeOf, nameOf} = assets({
            1: {type: 'ETF', name: 'Amundi MSCI'},
            2: {type: 'STOCK', name: 'Tesla'},
            3: {type: 'BOND', name: 'Btp 2030'},
            4: {type: 'ETF', name: 'Vanguard FTSE'},
            5: {type: 'STOCK', name: 'Apple'},
        });
        expect(typeOrder([1, 2, 3, 4, 5], typeOf, nameOf, RANK, LOCALE)).toEqual([5, 2, 3, 1, 4]);
    });

    it('files unknown, null and undefined types together, after every known type', () => {
        // The known types lead although their names sort last. The rest share one
        // rank, so they interleave by name — an unmapped type, a null, another
        // unmapped type, an undefined — instead of forming one group per kind.
        const {typeOf, nameOf} = assets({
            1: {type: 'WARRANT', name: 'Alpha Warrant'},
            2: {type: 'ETF', name: 'Xtrackers World'},
            3: {type: null, name: 'Beta'},
            4: {name: 'Gamma'},
            5: {type: 'CERTIFICATE', name: 'Delta'},
            6: {type: 'STOCK', name: 'Zeta'},
        });
        expect(typeOrder([1, 2, 3, 4, 5, 6], typeOf, nameOf, RANK, LOCALE)).toEqual([6, 2, 1, 3, 5, 4]);
    });

    it('orders the names within a type without their emoji', () => {
        // Collated raw, both flagged names would file ahead of iShares.
        const {typeOf, nameOf} = assets({
            1: {type: 'ETF', name: '🇪🇺 Xtrackers World'},
            2: {type: 'ETF', name: 'iShares Core'},
            3: {type: 'ETF', name: '🇪🇺👑 Amundi Semiconductors'},
        });
        expect(typeOrder([1, 2, 3], typeOf, nameOf, RANK, LOCALE)).toEqual([3, 2, 1]);
    });

    it('settles equal names within a type by id, whatever order they arrive in', () => {
        // Case and emoji aside the three names are one, so only the id can order
        // them. Kept in arrival order they would read [11, 12, 10]; collated raw,
        // the flag would put 12 first.
        const {typeOf, nameOf} = assets({
            10: {type: 'ETF', name: 'Same'},
            11: {type: 'ETF', name: 'same'},
            12: {type: 'ETF', name: '🇪🇺 Same'},
        });
        expect(typeOrder([11, 12, 10], typeOf, nameOf, RANK, LOCALE)).toEqual([10, 11, 12]);
    });

    it('returns a new array and leaves the one it was given alone', () => {
        const ids = [3, 1, 2];
        const {typeOf, nameOf} = assets({
            1: {type: 'ETF', name: 'A'},
            2: {type: 'BOND', name: 'B'},
            3: {type: 'STOCK', name: 'C'},
        });
        const result = typeOrder(ids, typeOf, nameOf, RANK, LOCALE);
        expect(result).toEqual([3, 2, 1]);
        expect(ids).toEqual([3, 1, 2]);
        expect(result).not.toBe(ids);
    });
});

describe('dominantExposure', () => {
    it('names the entry that holds most of the classified weight once it reaches half of it', () => {
        // The share is measured on what is classified. The catch-all is left out of
        // the total, so beside it Technology is all of it.
        expect(dominantExposure({Technology: 0.75, Health: 0.25})).toEqual({key: 'Technology', share: 0.75});
        expect(dominantExposure({Technology: 0.95, Other: 0.05})).toEqual({key: 'Technology', share: 1});
    });

    it('counts exactly half as dominant, and anything below as diversified', () => {
        // Inclusive, on the classified weight. Without the catch-all, A and B hold
        // half each, and the tie goes to A.
        expect(dominantExposure({Other: 0.8, A: 0.1, B: 0.1})).toEqual({key: 'A', share: 0.5});
        expect(dominantExposure({USA: 0.5, JPN: 0.25, CHN: 0.25})).toEqual({key: 'USA', share: 0.5});
        expect(dominantExposure({USA: 0.45, JPN: 0.3, CHN: 0.25})).toEqual({key: null, share: expect.closeTo(0.45, 12)});
    });

    it('calls an asset diversified when no entry reaches half, and still reports the largest share', () => {
        expect(dominantExposure({A: 0.34, B: 0.33, C: 0.33})).toEqual({key: null, share: 0.34});
    });

    it('weighs the classified entries among themselves: the catch-all neither wins nor counts', () => {
        // "Other" is the largest weight here and names nothing. Financials holds a
        // quarter of the whole, but 0.25 / 0.35 of what is classified — enough.
        const withOther = dominantExposure({Other: 0.65, Financials: 0.25, Utilities: 0.1});
        expect(withOther).toEqual({key: 'Financials', share: expect.closeTo(0.25 / 0.35, 12)});
        // Taking the catch-all away changes nothing.
        expect(withOther).toEqual(dominantExposure({Financials: 0.25, Utilities: 0.1}));
    });

    it('falls back to the catch-all only when nothing classified is left', () => {
        // An asset known solely through "Other" still gets a group, the last named
        // one. Unusable entries beside it are not classified weight; and the
        // catch-all itself needs a usable weight, or there is nothing at all.
        expect(OTHER_EXPOSURE).toBe('Other');
        expect(dominantExposure({Other: 1})).toEqual({key: 'Other', share: 1});
        expect(dominantExposure({Other: 0.3, '': 0.5, Broken: Number.NaN, Short: -0.2})).toEqual({key: 'Other', share: 1});
        expect(dominantExposure({Other: 0})).toBeNull();
    });

    it('has no group at all for a missing or empty distribution', () => {
        // Unclassified, not diversified: nothing was measured, so nothing is claimed.
        expect(dominantExposure(null)).toBeNull();
        expect(dominantExposure(undefined)).toBeNull();
        expect(dominantExposure({})).toBeNull();
    });

    it('ignores non-finite, zero and negative weights', () => {
        // Left in, the infinity would win outright, and the NaN, the infinity or the
        // −0.8 in the classified total would bend the share: Energy is all that counts.
        // With nothing usable at all the asset is unclassified, not diversified.
        expect(dominantExposure({Unknown: Number.POSITIVE_INFINITY, Broken: Number.NaN, Short: -0.8, Empty: 0, Energy: 0.6})).toEqual({key: 'Energy', share: 1});
        expect(dominantExposure({Broken: Number.NaN, Short: -1, Empty: 0, Unknown: Number.NEGATIVE_INFINITY})).toBeNull();
    });

    it('ignores an empty key, which names no group', () => {
        // An empty key would open a group without a label. It is left out of the race
        // and of the total alike, so A is all of what is classified; nor can it win a
        // tie, where it would otherwise sort before every other key.
        expect(dominantExposure({'': 0.9, A: 0.1})).toEqual({key: 'A', share: 1});
        expect(dominantExposure({A: 0.5, '': 0.5})).toEqual({key: 'A', share: 1});
        expect(dominantExposure({'': 1})).toBeNull();
    });

    it('settles a tie on the largest weight by the key that sorts first, whatever the insertion order', () => {
        expect(dominantExposure({USA: 0.5, JPN: 0.5})).toEqual({key: 'JPN', share: 0.5});
        expect(dominantExposure({JPN: 0.5, USA: 0.5})).toEqual({key: 'JPN', share: 0.5});
    });

    it('respects the threshold it is given, and defaults to DOMINANT_SHARE, one half', () => {
        const split = {Technology: 0.6, Health: 0.4};
        expect(DOMINANT_SHARE).toBe(0.5);
        expect(dominantExposure(split)).toEqual({key: 'Technology', share: 0.6});
        expect(dominantExposure(split, 0.7)).toEqual({key: null, share: 0.6});
        expect(dominantExposure(split, 0.6)).toEqual({key: 'Technology', share: 0.6});
        expect(dominantExposure({A: 0.34, B: 0.33, C: 0.33}, 1 / 3)).toEqual({key: 'A', share: 0.34});
    });
});

describe('exposureOrder', () => {
    // Pinned for the same reason as in nameOrder: names and labels go through a collator.
    const LOCALE = 'en';

    /** `exposureOf` and `nameOf` from one table. */
    function exposures(table: Record<number, {group: ExposureGroup | null; name: string}>) {
        return {
            exposureOf: (assetId: number) => table[assetId]?.group ?? null,
            nameOf: (assetId: number) => table[assetId]?.name ?? `#${assetId}`,
        };
    }

    /** A group label as the reader sees it; an unknown key is shown as it is. */
    function labelsOf(table: Record<string, string>): (key: string) => string {
        return (key) => table[key] ?? key;
    }

    it('puts named groups first, then diversified assets, then unclassified ones', () => {
        // The names alone would give the exact reverse.
        const {exposureOf, nameOf} = exposures({
            1: {group: null, name: 'Alpha Bond'},
            2: {group: {key: null, share: 0.4}, name: 'Beta World'},
            3: {group: {key: 'Energy', share: 0.6}, name: 'Zeta Energy'},
        });
        expect(exposureOrder([1, 2, 3], exposureOf, nameOf, labelsOf({}), LOCALE)).toEqual([3, 2, 1]);
    });

    it('orders four tiers: named, diversified, the catch-all fallback, unclassified', () => {
        // Name order would put the unclassified asset first and the named one last.
        // The two "Other"-only assets go by name between themselves; their label,
        // "Altro", would file them ahead of Energy were they compared as a named group.
        const {exposureOf, nameOf} = exposures({
            1: {group: null, name: 'Alpha Unclassified'},
            2: {group: {key: OTHER_EXPOSURE, share: 1}, name: 'Omega Other'},
            3: {group: {key: null, share: 0.4}, name: 'Gamma World'},
            4: {group: {key: 'Energy', share: 0.6}, name: 'Zeta Energy'},
            5: {group: {key: OTHER_EXPOSURE, share: 1}, name: 'Beta Other'},
        });
        expect(exposureOrder([1, 2, 3, 4, 5], exposureOf, nameOf, labelsOf({Other: 'Altro'}), LOCALE)).toEqual([4, 3, 5, 2, 1]);
    });

    it('orders the named groups by their label without its emoji, not by key', () => {
        // Keys run CHE, DEU, ESP, and so do the raw labels — flags collate by their
        // letters, ahead of any word. The reader sees Germany, Spain, Switzerland.
        const {exposureOf, nameOf} = exposures({
            1: {group: {key: 'CHE', share: 0.9}, name: 'Alpha Swiss'},
            2: {group: {key: 'DEU', share: 0.9}, name: 'Beta German'},
            3: {group: {key: 'ESP', share: 0.9}, name: 'Gamma Spanish'},
        });
        const groupLabel = labelsOf({CHE: '🇨🇭 Switzerland', DEU: '🇩🇪 Germany', ESP: 'Spain'});
        expect(exposureOrder([1, 2, 3], exposureOf, nameOf, groupLabel, LOCALE)).toEqual([2, 3, 1]);
    });

    it('leads each named group with its most concentrated asset, then goes by name', () => {
        // Share first: by name alone Omega would follow both Betas. Equal shares fall
        // back to the emoji-insensitive name order — collated raw, the flag would put
        // Zulu first — and equal names to the id, whatever order the ids arrive in.
        const technology = (share: number): ExposureGroup => ({key: 'Technology', share});
        const {exposureOf, nameOf} = exposures({
            1: {group: technology(0.7), name: 'Beta Tech'},
            2: {group: technology(0.95), name: 'Omega Tech'},
            3: {group: technology(0.7), name: '🇺🇸 Zulu Tech'},
            4: {group: technology(0.7), name: 'Beta Tech'},
        });
        expect(exposureOrder([3, 4, 1, 2], exposureOf, nameOf, labelsOf({Technology: '💻 Technology'}), LOCALE)).toEqual([2, 1, 4, 3]);
    });

    it('orders the diversified and the unclassified tiers by name alone', () => {
        // Share plays no part outside a named group: the 0.45 fund does not lead the
        // 0.3 one. Names are compared without their emoji, so Kiwi precedes Mango.
        const {exposureOf, nameOf} = exposures({
            1: {group: {key: null, share: 0.45}, name: 'Zed World'},
            2: {group: {key: null, share: 0.3}, name: 'Alpha World'},
            3: {group: null, name: '🇪🇺 Mango'},
            4: {group: null, name: 'Kiwi'},
        });
        expect(exposureOrder([1, 2, 3, 4], exposureOf, nameOf, labelsOf({}), LOCALE)).toEqual([2, 1, 4, 3]);
    });

    it('gives one order whatever the input order, even for a named group with an empty key', () => {
        // dominantExposure no longer yields an empty key, so the fixture hands one
        // over directly. Its group used to skip the label comparison and fall back to
        // names, which closed a cycle — 1 before 2 by group (A, B), 2 before 3 by
        // name (Alpha, Mid), 3 before 1 by name (Mid, Zed) — so the output followed
        // the input order. Compared by label like any named group, the empty label
        // simply collates first.
        const {exposureOf, nameOf} = exposures({
            1: {group: {key: 'A', share: 0.9}, name: 'Zed'},
            2: {group: {key: 'B', share: 0.9}, name: 'Alpha'},
            3: {group: {key: '', share: 0.9}, name: 'Mid'},
        });
        const inputs = [
            [1, 2, 3],
            [1, 3, 2],
            [2, 1, 3],
            [2, 3, 1],
            [3, 1, 2],
            [3, 2, 1],
        ];
        for (const ids of inputs) {
            expect(exposureOrder(ids, exposureOf, nameOf, labelsOf({}), LOCALE), `input [${ids.join(', ')}]`).toEqual([3, 1, 2]);
        }
    });

    it('returns a new array and leaves the one it was given alone', () => {
        const ids = [3, 1, 2];
        const {exposureOf, nameOf} = exposures({
            1: {group: null, name: 'A'},
            2: {group: {key: null, share: 0.4}, name: 'B'},
            3: {group: {key: 'Energy', share: 0.8}, name: 'C'},
        });
        const result = exposureOrder(ids, exposureOf, nameOf, labelsOf({}), LOCALE);
        expect(result).toEqual([3, 2, 1]);
        expect(ids).toEqual([3, 1, 2]);
        expect(result).not.toBe(ids);
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

describe('heatmapLayout', () => {
    // The owner's reference card, on the heatmap's real constants: seven assets
    // (six rows and six columns, once the empty first row and last column are
    // dropped), both label widths at their caps of 200 and 150, 14 px text.
    const REFERENCE = {columns: 6, rows: 6, yLabelWidth: 200, xLabelWidth: 150, labelHeight: 14};

    it('works from the published cell bounds, which every reference below assumes', () => {
        // Each figure below was worked out by hand from these bounds: if they move
        // on purpose, this names the cause before the geometry cases fail.
        expect(HEATMAP_CELL).toEqual({minWidth: 44, maxWidth: 88, minHeight: 34, maxHeight: 52, aspect: 0.7});
    });

    it('sizes the reference matrix in a 729 px card to the owner-computed geometry', () => {
        // 729 − 212 − 12 leaves 505 px for six columns: 84 px cells, 58.8 px tall
        // by aspect and capped at 52. The chart follows its cells, so it comes out
        // a pixel narrower than the card rather than stretching to fill it.
        expect(heatmapLayout({...REFERENCE, availableWidth: 729})).toEqual({
            width: 728,
            height: 448,
            cellWidth: 84,
            cellHeight: 52,
            grid: {left: 212, right: 12, top: 8, bottom: 128},
        });
    });

    it('stops the cells at the maximum when the card is wider than they need', () => {
        // 1100 px would allow 146 px cells. They stop at the 88 × 52 maximum, and
        // the chart stays narrower than the card instead of turning into posters.
        expect(heatmapLayout({...REFERENCE, availableWidth: 1100})).toMatchObject({cellWidth: 88, cellHeight: 52, width: 752, height: 448});
    });

    it('holds the cells at the minimum and lets the chart outgrow a narrow card', () => {
        // 420 px would leave 32 px cells, too narrow for a value: they stay at the
        // 44 × 34 minimum and the chart comes out wider than the card, which scrolls.
        const narrow = heatmapLayout({...REFERENCE, availableWidth: 420});
        expect(narrow).toMatchObject({cellWidth: 44, cellHeight: 34, width: 488, height: 340});
        expect(narrow.width).toBeGreaterThan(420);
        // A long selection in the reference card: 505 px over 14 columns is 36 each.
        expect(heatmapLayout({...REFERENCE, columns: 14, rows: 14, availableWidth: 729})).toMatchObject({cellWidth: 44, cellHeight: 34, width: 840, height: 612});
    });

    it('derives the cell height from its width at 0.7 between the clamps', () => {
        // Every case above hits a height clamp (52 or 34), so none would notice the
        // aspect changing. 584 px leaves 360 for six columns: 60 px cells, 42 px
        // tall, and a chart exactly as wide as the card.
        expect(heatmapLayout({...REFERENCE, availableWidth: 584})).toEqual({
            width: 584,
            height: 388,
            cellWidth: 60,
            cellHeight: 42,
            grid: {left: 212, right: 12, top: 8, bottom: 128},
        });
    });

    it('outgrows the card exactly when a column would get less than the minimum', () => {
        // Six minimum columns need 264 px between margins of 212 and 12: a 488 px
        // card holds them to the pixel; one pixel less and the chart spills by one.
        const fits = heatmapLayout({...REFERENCE, availableWidth: 488});
        const spills = heatmapLayout({...REFERENCE, availableWidth: 487});
        expect([fits.cellWidth, fits.width]).toEqual([44, 488]);
        expect([spills.cellWidth, spills.width]).toEqual([44, 488]);
        // The same rule at every width, for a short and a long selection: wider
        // than the card ⇔ the room between the margins is below columns × minimum,
        // i.e. the fitted cell, floor(room / columns), is under 44.
        for (const columns of [1, 6, 14]) {
            for (let availableWidth = 200; availableWidth <= 1400; availableWidth += 1) {
                const layout = heatmapLayout({...REFERENCE, columns, rows: columns, availableWidth});
                const room = availableWidth - layout.grid.left - layout.grid.right;
                expect(layout.width > availableWidth, `${columns} columns in ${availableWidth} px`).toBe(room < columns * HEATMAP_CELL.minWidth);
            }
        }
    });

    it('reserves below the plot the depth of the rotated column labels', () => {
        // A label w wide and h tall, turned 45°, reaches (w + h)·sin 45° down:
        // rounded up, plus a 12 px gap.
        const bottom = (xLabelWidth: number, labelHeight: number) => heatmapLayout({...REFERENCE, availableWidth: 729, xLabelWidth, labelHeight}).grid.bottom;
        expect(bottom(150, 14)).toBe(128); // 115.97 → 116
        expect(bottom(100, 14)).toBe(93); // 80.61 → 81
        expect(bottom(200, 14)).toBe(164); // 151.32 → 152
        expect(bottom(0, 0)).toBe(12); // no label: the gap alone
        // Rows, columns, card and row labels do not move it.
        expect(heatmapLayout({columns: 14, rows: 14, availableWidth: 420, yLabelWidth: 40, xLabelWidth: 150, labelHeight: 14}).grid.bottom).toBe(128);
    });

    it('widens the left margin for a long first column label when the row labels are short', () => {
        // The first rotated label hangs left of its tick, which sits half a minimum
        // cell into the plot: (200 + 14)·sin 45° − 22 = 129.3 → 130, plus the gap.
        expect(heatmapLayout({...REFERENCE, availableWidth: 729, yLabelWidth: 40, xLabelWidth: 200}).grid.left).toBe(142);
        // Against the reference's 200 px row labels, the row labels are the wider claim.
        expect(heatmapLayout({...REFERENCE, availableWidth: 729, xLabelWidth: 200}).grid.left).toBe(212);
    });

    it('survives a matrix with no columns, the one-asset case', () => {
        // One asset draws no row and no column. In a card exactly as wide as the
        // margins, dividing the room by zero columns would give 0 / 0 = NaN and
        // poison every size; the cell falls back to the minimum instead.
        const empty = {...REFERENCE, columns: 0, rows: 0, availableWidth: 224};
        expect(() => heatmapLayout(empty)).not.toThrow();
        expect(heatmapLayout(empty)).toEqual({
            width: 224,
            height: 136,
            cellWidth: 44,
            cellHeight: 34,
            grid: {left: 212, right: 12, top: 8, bottom: 128},
        });
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
