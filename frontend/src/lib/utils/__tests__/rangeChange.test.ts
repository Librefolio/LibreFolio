/**
 * rangeChange — the Δ over the range a page shows, read from the backend (workstream Y, lot X-R59 A; decision N80).
 *
 * One home for financial math: the backend (rule 10). The change from the first to the last point of the range on screen
 * — the Assets cards’ Δ, the FX table’s Δ Abs and Δ %, the FX card’s and the pair page’s — stops being computed in the
 * browser, in floats, from the prices or rates it loaded (`computeDerivedPriceState`, `displayFxDelta`). Each item of
 * `POST /assets/prices/period-changes` and `POST /fx/currencies/period-changes` may carry a `range_start` — on or after
 * 0001-01-01 and on or before its `as_of`, or the whole request is a 422 —, and its result then carries a `range_change`:
 * `{reference_date, change_abs, change_ratio}`, plus `inverse_change_abs` and `inverse_change_ratio` for a pair read the
 * other way round. A decimal arrives as a string, a ratio as a fraction (`"0.105"` = +10.5 %); with a `range_start` asked
 * and no usable price (rate), every field is null.
 *
 * The pure module the pages read it through — no Svelte, no API client:
 *   - `rangeStartFor(dateStart, asOf)`: the `range_start` a request sends, the start of the range itself, whatever its
 *     year (X5-6, D-P4 L4: the backend values any day, so nothing is raised to 1900 any more); null — send none — when
 *     either day is not a bare `YYYY-MM-DD` the calendar has, or when the start falls after `asOf`: a refused
 *     `range_start` would take every Δ column of the request down with it;
 *   - `assetRangeDelta(raw)`, `fxRangeDeltas(raw)`: a `range_change` as the page shows it — `abs` in the price’s (the
 *     rate’s) unit, `pct` in percent, read as `ratioToPercent` reads a period’s change —, a pair’s both ways, each
 *     orientation from its own fields; null wherever the backend has nothing usable, never 0, and a zero never −0. Only
 *     strings are read: the generated type of a decimal is wider than what the server sends.
 *
 * Fixtures: `range_change` objects as the backend serialises `FARangeChange` and `FXRangeChange` (commit a8de6b584), and
 * the malformed values a reader of an answer must survive. `$lib/api` is mocked only to observe that importing the module
 * never loads the API client.
 *
 * Red today: the module does not exist, so the file fails to load.
 */
import {describe, expect, it, vi} from 'vitest';

/** Whether any module loaded `$lib/api`: the mock’s factory runs only when one imports it. */
const apiClient = vi.hoisted(() => ({loaded: false}));
vi.mock('$lib/api', () => {
    apiClient.loaded = true;
    return {zodiosApi: {post: vi.fn()}, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

import * as rangeChangeModule from '../rangeChange';
import {assetRangeDelta, fxRangeDeltas, rangeStartFor, type RangeDelta} from '../rangeChange';

/** The anchor day of the ranges here: the end of the range on screen. */
const AS_OF = '2026-10-17';
/** The start of that range, a year before: the reference day of the changes below. */
const RANGE_START = '2025-10-17';
/** No change: what the page shows where the backend has nothing usable. */
const NONE: RangeDelta = {abs: null, pct: null};

/** An asset’s `range_change` as the backend serialises `FARangeChange`; its fields `unknown`, for the values it never sends. */
function assetChange(changeAbs: unknown, changeRatio: unknown, referenceDate: string | null = RANGE_START) {
    return {reference_date: referenceDate, change_abs: changeAbs, change_ratio: changeRatio};
}

/** A pair’s `range_change` as the backend serialises `FXRangeChange`: the direct change, then the inverse one. */
function fxChange(changeAbs: unknown, changeRatio: unknown, inverseChangeAbs: unknown, inverseChangeRatio: unknown, referenceDate: string | null = RANGE_START) {
    return {reference_date: referenceDate, change_abs: changeAbs, change_ratio: changeRatio, inverse_change_abs: inverseChangeAbs, inverse_change_ratio: inverseChangeRatio};
}

// X5-6 (D-P4 L4): the backend values any day, so the module no longer knows a first day to raise a start to.
describe('rangeChange exports — no earliest range start any more', () => {
    it('does not export EARLIEST_RANGE_START: the start of a range is never raised', () => {
        expect(Object.keys(rangeChangeModule)).not.toContain('EARLIEST_RANGE_START');
    });
});

describe('rangeStartFor — the range_start a request sends', () => {
    // X5-5 (D-P4): a year before 100 is read as typed, not as 19xx (`Date.UTC(24, …)` is 1924).
    // X5-6 (D-P4 L4): a start before 1900 is sent as it is, not raised to 1900-01-01.
    it.each([
        {case: 'a year on screen sends its first day', start: RANGE_START, asOf: AS_OF, sent: RANGE_START},
        {case: 'a 29 February sends itself, in a leap year', start: '2024-02-29', asOf: AS_OF, sent: '2024-02-29'},
        {case: 'a range of one day sends its day: the start may be as_of', start: AS_OF, asOf: AS_OF, sent: AS_OF},
        {case: 'a start on 1900-01-01 sends itself', start: '1900-01-01', asOf: AS_OF, sent: '1900-01-01'},
        {case: 'a start the day before 1900-01-01 sends itself', start: '1899-12-31', asOf: AS_OF, sent: '1899-12-31'},
        {case: 'a start in 1850 sends itself', start: '1850-03-01', asOf: AS_OF, sent: '1850-03-01'},
        {case: 'a start in the year 999 sends itself', start: '0999-12-31', asOf: AS_OF, sent: '0999-12-31'},
        {case: 'a start before 1900 with as_of on 1900-01-01 sends itself', start: '1850-06-01', asOf: '1900-01-01', sent: '1850-06-01'},
        {case: 'a start and an as_of both before 1900, in order, send the start', start: '1850-06-01', asOf: '1899-12-31', sent: '1850-06-01'},
        {case: 'a start on as_of, both before 1900: a range of one day', start: '1899-12-31', asOf: '1899-12-31', sent: '1899-12-31'},
    ])('$case ($start … $asOf)', ({start, asOf, sent}) => {
        expect(rangeStartFor(start, asOf)).toBe(sent);
    });

    it.each([
        {case: 'a start the day after as_of', start: '2026-10-18', asOf: AS_OF},
        {case: 'a start a year after as_of', start: '2027-10-17', asOf: AS_OF},
        {case: 'a start the day after as_of, both before 1900', start: '1850-06-02', asOf: '1850-06-01'},
        {case: 'a start in 1900 after an as_of before 1900', start: '1900-01-01', asOf: '1899-12-31'},
    ])('sends none for $case ($start … $asOf): the backend would refuse it, every Δ column with it', ({start, asOf}) => {
        expect(rangeStartFor(start, asOf)).toBeNull();
    });

    // X5-5 (D-P4): the year is read as typed; X5-6 (D-P4 L4): and the start is sent as typed, never raised to 1900-01-01.
    it.each([
        {case: 'a start in the year 24 is a real day, sent as it is', start: '0024-03-01'},
        {case: 'a start on 1 January of the year 1 is a real day, sent as it is', start: '0001-01-01'},
    ])('$case ($start … 2026-10-25)', ({start}) => {
        expect(rangeStartFor(start, '2026-10-25')).toBe(start);
    });

    // X5-5 (D-P4): guards that stay null, before and after the fix: the calendar still refuses, and a start still may not pass as_of.
    it.each([
        {case: '29 February of the year 1, which is not leap', start: '0001-02-29', asOf: '2026-10-25'},
        {case: '30 February of the year 24', start: '0024-02-30', asOf: '2026-10-25'},
        {case: 'a thirteenth month in the year 24', start: '0024-13-01', asOf: '2026-10-25'},
        {case: 'as_of in the year 24 and a start the day after it', start: '0024-03-02', asOf: '0024-03-01'},
        // X5-6 (D-P4 L4): the backend takes year >= 1, so a year-0 start (even the leap 29 February) would be a 422 on the wire.
        {case: 'the year 0 does not exist for the backend (year >= 1): 1 January', start: '0000-01-01', asOf: '2026-10-25'},
        {case: 'the year 0 does not exist for the backend (year >= 1): 29 February, though year 0 is leap in the proleptic calendar', start: '0000-02-29', asOf: '2026-10-25'},
        {case: 'the year 0 does not exist for the backend (year >= 1): as_of on 1 January of the year 0', start: '0000-01-01', asOf: '0000-01-01'},
    ])('sends none for $case ($start … $asOf)', ({start, asOf}) => {
        expect(rangeStartFor(start, asOf)).toBeNull();
    });

    // X5-6 (D-P4 L4): an as_of in the first years is a real day too, and a start in the year 1 reaches it.
    it('sends a start in the year 1 for an as_of in the year 24: the range is read from where it starts', () => {
        expect(rangeStartFor('0001-01-01', '0024-03-01')).toBe('0001-01-01');
    });

    // Each of these but "min" comes before as_of as text, so only the shape of the day can refuse it.
    it.each([
        {case: 'an empty start', start: ''},
        {case: 'the "min" sentinel, not yet resolved to a day', start: 'min'},
        {case: 'a month and a day without their zero', start: '2026-1-1'},
        {case: 'a date and time', start: '2026-01-01T00:00'},
        {case: 'a day padded with a space', start: ' 2026-01-01'},
    ])('sends none for $case: not a bare YYYY-MM-DD', ({start}) => {
        expect(rangeStartFor(start, AS_OF)).toBeNull();
    });

    // Each comes before as_of as text, so only the calendar can refuse it.
    it.each([
        {case: '30 February', start: '2026-02-30'},
        {case: '29 February of a year that is not leap', start: '2026-02-29'},
        {case: '29 February 1900, a century year that is not leap', start: '1900-02-29'},
        {case: '31 April', start: '2026-04-31'},
        {case: 'a thirteenth month', start: '2025-13-01'},
        {case: 'a month 00', start: '2026-00-10'},
        {case: 'a day 00', start: '2026-01-00'},
        {case: '30 February 1850: refused, whatever the year', start: '1850-02-30'},
    ])('sends none for a start the calendar does not have: $case ($start)', ({start}) => {
        expect(rangeStartFor(start, AS_OF)).toBeNull();
    });

    // Each but the empty one comes after the start as text, so only the shape of the day or the calendar can refuse it.
    it.each([
        {case: 'an empty as_of', asOf: ''},
        {case: 'the "max" sentinel, not yet resolved to a day', asOf: 'max'},
        {case: 'a date and time', asOf: '2026-10-17T00:00'},
        {case: 'a thirteenth month', asOf: '2026-13-01'},
        {case: '30 February', asOf: '2026-02-30'},
    ])('sends none for an as_of that is not a day the calendar has: $case ($asOf)', ({asOf}) => {
        expect(rangeStartFor(RANGE_START, asOf)).toBeNull();
    });
});

describe('assetRangeDelta — an asset’s range_change, as the page shows it', () => {
    it.each([
        {case: 'a gain', raw: assetChange('10.500000', '0.105'), delta: {abs: 10.5, pct: 10.5}},
        {case: 'a loss', raw: assetChange('-3.2', '-0.032'), delta: {abs: -3.2, pct: -3.2}},
        {case: 'a total loss: −100 %', raw: assetChange('-50', '-1'), delta: {abs: -50, pct: -100}},
        {case: 'a gain of more than 100 %', raw: assetChange('150.25', '1.5'), delta: {abs: 150.25, pct: 150}},
        {case: 'exponent forms', raw: assetChange('1E-7', '2.5E-2'), delta: {abs: 1e-7, pct: 2.5}},
        {case: 'negative exponent forms', raw: assetChange('-4.2e+3', '-1E-3'), delta: {abs: -4200, pct: -0.1}},
        {case: 'values with spaces around them', raw: assetChange(' 10.5 ', ' 0.105 '), delta: {abs: 10.5, pct: 10.5}},
    ])('reads $case', ({raw, delta}) => {
        expect(assetRangeDelta(raw)).toEqual(delta);
    });

    it('reads a ratio by moving its decimal point, as ratioToPercent does: 0.07 is 7 %, not 7.000000000000001', () => {
        expect(assetRangeDelta(assetChange('7', '0.07')).pct).toBe(7);
    });

    it.each([
        {case: '0', value: '0'},
        {case: '-0', value: '-0'},
        {case: '-0.000000', value: '-0.000000'},
        {case: '-0E-7', value: '-0E-7'},
    ])('reads a zero change ($case) as 0, never −0: no “−0.00” on screen', ({value}) => {
        const delta = assetRangeDelta(assetChange(value, value));

        expect(delta.abs, 'abs').toBe(0);
        expect(delta.pct, 'pct').toBe(0);
    });

    it('reads a range_change with no usable price — every field null — as no change', () => {
        expect(assetRangeDelta(assetChange(null, null, null))).toEqual(NONE);
    });

    it('reads each field on its own', () => {
        expect(assetRangeDelta(assetChange('10.5', null)), 'an absolute change without a ratio').toEqual({abs: 10.5, pct: null});
        expect(assetRangeDelta(assetChange(null, '0.105')), 'a ratio without an absolute change').toEqual({abs: null, pct: 10.5});
    });

    it('reads a missing field as null', () => {
        expect(assetRangeDelta({}), 'an empty object').toEqual(NONE);
        expect(assetRangeDelta({reference_date: RANGE_START}), 'a reference day only').toEqual(NONE);
        expect(assetRangeDelta({reference_date: RANGE_START, change_ratio: '0.105'}), 'no change_abs').toEqual({abs: null, pct: 10.5});
        expect(assetRangeDelta({reference_date: RANGE_START, change_abs: '10.5'}), 'no change_ratio').toEqual({abs: 10.5, pct: null});
    });

    it.each([
        {case: 'an empty string', value: ''},
        {case: 'spaces only', value: '   '},
        {case: 'a number followed by letters', value: '12abc'},
        {case: 'a word', value: 'abc'},
        {case: 'a decimal comma', value: '10,5'},
        {case: 'NaN', value: 'NaN'},
        {case: 'Infinity', value: 'Infinity'},
        {case: '-Infinity', value: '-Infinity'},
        {case: 'a number past the largest float', value: '1e999'},
    ])('reads $case in either field as null, never 0', ({value}) => {
        expect(assetRangeDelta(assetChange(value, value))).toEqual(NONE);
    });

    it.each([
        {case: 'a number', value: 10.5},
        {case: 'a zero number', value: 0},
        {case: 'a boolean', value: true},
        {case: 'an object', value: {value: '10.5'}},
        {case: 'an array holding a decimal string', value: ['10.5']},
    ])('reads $case in place of a decimal string as null: only strings are read', ({value}) => {
        expect(assetRangeDelta(assetChange(value, value))).toEqual(NONE);
    });

    it.each([
        {case: 'null: the item asked no range change', raw: null},
        {case: 'undefined: a result without the field', raw: undefined},
        {case: 'an array', raw: [assetChange('10.5', '0.105')]},
        {case: 'a number', raw: 0.105},
        {case: 'a string', raw: '0.105'},
    ])('reads $case as no change', ({raw}) => {
        expect(assetRangeDelta(raw)).toEqual(NONE);
    });
});

describe('fxRangeDeltas — a pair’s range_change, both ways', () => {
    it('reads the direct change from change_abs and change_ratio, the inverse one from inverse_change_abs and inverse_change_ratio', () => {
        // 0.5 → 0.625 quote per base. The inverse figures are not the inversion of the direct ones (that would be −0.4
        // and −20 %): each orientation is the answer’s own, read and never derived.
        expect(fxRangeDeltas(fxChange('0.125', '0.25', '-0.0375', '-0.3'))).toEqual({direct: {abs: 0.125, pct: 25}, inverse: {abs: -0.0375, pct: -30}});
    });

    it('gives an inverted pair the backend’s inverse change, never the negated direct one (bug B1)', () => {
        // Raw 0.8 → 1.0 quote per base reads 1.25 → 1.0 base per quote when inverted: −20 %, where negating the direct
        // +25 % would show −25 %.
        expect(fxRangeDeltas(fxChange('0.2', '0.25', '-0.25', '-0.2'))).toEqual({direct: {abs: 0.2, pct: 25}, inverse: {abs: -0.25, pct: -20}});
    });

    it('reads a range_change with no usable rate — every field null — as no change, both ways', () => {
        expect(fxRangeDeltas(fxChange(null, null, null, null, null))).toEqual({direct: NONE, inverse: NONE});
    });

    it('reads each orientation on its own', () => {
        expect(fxRangeDeltas(fxChange('-1.25', '-1', null, null)), 'a total loss, whose inverse the backend cannot give').toEqual({direct: {abs: -1.25, pct: -100}, inverse: NONE});
        expect(fxRangeDeltas(assetChange('0.125', '0.25')), 'no inverse field at all').toEqual({direct: {abs: 0.125, pct: 25}, inverse: NONE});
        expect(fxRangeDeltas({reference_date: RANGE_START, inverse_change_abs: '-0.0375', inverse_change_ratio: '-0.3'}), 'no direct field at all').toEqual({direct: NONE, inverse: {abs: -0.0375, pct: -30}});
    });

    it('reads exponent forms both ways', () => {
        expect(fxRangeDeltas(fxChange('1E-7', '2.5E-2', '-4E-5', '-1E-3'))).toEqual({direct: {abs: 1e-7, pct: 2.5}, inverse: {abs: -4e-5, pct: -0.1}});
    });

    it.each([
        {case: '0', value: '0'},
        {case: '-0.000000', value: '-0.000000'},
    ])('reads a zero change ($case) as 0 both ways, never −0', ({value}) => {
        const {direct, inverse} = fxRangeDeltas(fxChange(value, value, value, value));

        expect(direct.abs, 'direct abs').toBe(0);
        expect(direct.pct, 'direct pct').toBe(0);
        expect(inverse.abs, 'inverse abs').toBe(0);
        expect(inverse.pct, 'inverse pct').toBe(0);
    });

    it.each([
        {case: 'an empty string', value: ''},
        {case: 'a number followed by letters', value: '12abc'},
        {case: 'Infinity', value: 'Infinity'},
        {case: 'a number', value: 0.25},
        {case: 'a boolean', value: false},
        {case: 'an object', value: {}},
    ])('reads $case in place of a decimal string as null both ways, never 0', ({value}) => {
        expect(fxRangeDeltas(fxChange(value, value, value, value))).toEqual({direct: NONE, inverse: NONE});
    });

    it.each([
        {case: 'null: the pair asked no range change', raw: null},
        {case: 'undefined: a result without the field', raw: undefined},
        {case: 'an array', raw: [fxChange('0.125', '0.25', '-0.0375', '-0.3')]},
        {case: 'a number', raw: 0.25},
    ])('reads $case as no change, both ways', ({raw}) => {
        expect(fxRangeDeltas(raw)).toEqual({direct: NONE, inverse: NONE});
    });
});

describe('rangeChange is pure', () => {
    it('loads no API client, directly or through a module it imports', () => {
        expect(apiClient.loaded, 'importing rangeChange.ts loaded $lib/api: a pure module carries no API client (periodChanges.ts, the home of ratioToPercent today, imports it)').toBe(false);
    });
});
