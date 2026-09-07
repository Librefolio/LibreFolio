/**
 * assetIdentifiers — pure unit tests.
 *
 * Every branch of the column↔row conversion, exercised directly instead of
 * through the modal: the OTHER-is-a-list special case, the defensive coercion of
 * a non-string element, the "reset then fill" column baseline, and the
 * next-free-type pick. Row ids are opaque (generateUUID), so we assert on
 * `type`/`value` and on uniqueness, never on a specific id.
 */
import {describe, expect, it} from 'vitest';
import {columnsToIdentifierRows, identifierRowsToColumns, nextAvailableIdentifierType, fieldToIdType, type IdentifierRow} from './assetIdentifiers';

const row = (type: string, value: string): IdentifierRow => ({id: `id-${type}-${value}`, type, value});

describe('columnsToIdentifierRows', () => {
    it('emits one row per set single-valued column, and none for empty ones', () => {
        const rows = columnsToIdentifierRows({identifier_isin: 'IE00B4L5Y983', identifier_ticker: '', identifier_cusip: null});
        expect(rows.map((r) => [r.type, r.value])).toEqual([['ISIN', 'IE00B4L5Y983']]);
    });

    it('preserves IDENTIFIER_TYPES order regardless of input order', () => {
        const rows = columnsToIdentifierRows({identifier_uuid: 'u1', identifier_isin: 'i1', identifier_ticker: 't1'});
        // ISIN, TICKER come before UUID in the canonical order.
        expect(rows.map((r) => r.type)).toEqual(['ISIN', 'TICKER', 'UUID']);
    });

    it('expands identifier_other (a JSON list) into one OTHER row per element', () => {
        const rows = columnsToIdentifierRows({identifier_other: ['a', 'b', 'c']});
        expect(rows.map((r) => [r.type, r.value])).toEqual([
            ['OTHER', 'a'],
            ['OTHER', 'b'],
            ['OTHER', 'c'],
        ]);
    });

    it('tolerates a legacy scalar string in identifier_other', () => {
        const rows = columnsToIdentifierRows({identifier_other: 'solo'});
        expect(rows).toEqual([expect.objectContaining({type: 'OTHER', value: 'solo'})]);
    });

    it('treats a null/undefined/empty identifier_other as no OTHER rows', () => {
        expect(columnsToIdentifierRows({identifier_other: null})).toEqual([]);
        expect(columnsToIdentifierRows({identifier_other: undefined})).toEqual([]);
        expect(columnsToIdentifierRows({identifier_other: ''})).toEqual([]);
        expect(columnsToIdentifierRows({identifier_other: []})).toEqual([]);
    });

    it('skips blank/whitespace OTHER elements and coerces a non-string element', () => {
        // 42 is not a string → coerced via String(); '   ' is dropped by the trim guard.
        const rows = columnsToIdentifierRows({identifier_other: ['keep', '   ', 42 as unknown as string]});
        expect(rows.map((r) => r.value)).toEqual(['keep', '42']);
    });

    it('coerces a null/undefined element to "" (dropped by the trim guard)', () => {
        // Exercises the `?? ''` fallback: null/undefined → '' → skipped.
        const rows = columnsToIdentifierRows({identifier_other: [null as unknown as string, undefined as unknown as string, 'stay']});
        expect(rows.map((r) => r.value)).toEqual(['stay']);
    });

    it('mints a unique id per row', () => {
        const rows = columnsToIdentifierRows({identifier_isin: 'i', identifier_ticker: 't', identifier_other: ['a', 'b']});
        const ids = rows.map((r) => r.id);
        expect(new Set(ids).size).toBe(ids.length);
    });

    it('returns no rows for an object with no identifier columns at all', () => {
        expect(columnsToIdentifierRows({})).toEqual([]);
    });
});

describe('identifierRowsToColumns', () => {
    it('resets every single-valued column to undefined, then fills from rows', () => {
        const cols = identifierRowsToColumns([row('ISIN', 'i1'), row('TICKER', 't1')]);
        expect(cols.identifier_isin).toBe('i1');
        expect(cols.identifier_ticker).toBe('t1');
        // The untouched ones are present-but-undefined (so a cleared row clears the column).
        expect(cols.identifier_cusip).toBeUndefined();
        expect('identifier_cusip' in cols).toBe(true);
    });

    it('trims values and drops blank rows', () => {
        const cols = identifierRowsToColumns([row('ISIN', '  spaced  '), row('TICKER', '   ')]);
        expect(cols.identifier_isin).toBe('spaced');
        expect(cols.identifier_ticker).toBeUndefined();
    });

    it('collects OTHER rows into a trimmed JSON list', () => {
        const cols = identifierRowsToColumns([row('OTHER', 'x'), row('OTHER', ' y '), row('OTHER', '')]);
        expect(cols.identifier_other).toEqual(['x', 'y']);
    });

    it('sets identifier_other to undefined when there is no OTHER row', () => {
        const cols = identifierRowsToColumns([row('ISIN', 'i1')]);
        expect(cols.identifier_other).toBeUndefined();
    });

    it('coerces a non-string row value instead of throwing', () => {
        const cols = identifierRowsToColumns([{id: 'x', type: 'ISIN', value: 123 as unknown as string}]);
        expect(cols.identifier_isin).toBe('123');
    });

    it('coerces a null row value to "" and drops it (the `?? ""` fallback)', () => {
        const cols = identifierRowsToColumns([{id: 'x', type: 'ISIN', value: null as unknown as string}]);
        expect(cols.identifier_isin).toBeUndefined();
    });

    it('round-trips columns → rows → columns for a mixed payload', () => {
        const original = {identifier_isin: 'i1', identifier_figi: 'f1', identifier_other: ['o1', 'o2']};
        const back = identifierRowsToColumns(columnsToIdentifierRows(original));
        expect(back.identifier_isin).toBe('i1');
        expect(back.identifier_figi).toBe('f1');
        expect(back.identifier_other).toEqual(['o1', 'o2']);
    });
});

describe('nextAvailableIdentifierType', () => {
    it('returns the first canonical type when nothing is used', () => {
        expect(nextAvailableIdentifierType([])).toBe('ISIN');
    });

    it('skips already-used types and returns the next free one', () => {
        expect(nextAvailableIdentifierType([row('ISIN', 'x')])).toBe('TICKER');
        expect(nextAvailableIdentifierType([row('ISIN', 'x'), row('TICKER', 'y')])).toBe('CUSIP');
    });

    it('never offers OTHER, and OTHER rows do not consume a fixed slot', () => {
        const result = nextAvailableIdentifierType([row('OTHER', 'z')]);
        expect(result).toBe('ISIN');
    });

    it('returns null when every single-valued type is taken', () => {
        const all = ['ISIN', 'TICKER', 'CUSIP', 'SEDOL', 'FIGI', 'UUID'].map((t) => row(t, 'v'));
        expect(nextAvailableIdentifierType(all)).toBeNull();
    });
});

describe('fieldToIdType', () => {
    it('maps a column name to the upper-case identifier type', () => {
        expect(fieldToIdType('identifier_isin')).toBe('ISIN');
        expect(fieldToIdType('identifier_other')).toBe('OTHER');
    });
});
