/**
 * assetIdentifiers — pure unit tests.
 *
 * Every branch of the column↔row conversion, exercised directly instead of
 * through the modal: the OTHER-is-a-list special case, the defensive coercion of
 * a non-string element, the "reset then fill" column baseline, and the
 * next-free-type pick. Row ids are opaque (generateUUID), so we assert on
 * `type`/`value` and on uniqueness, never on a specific id.
 *
 * Also the row edits AssetModal applies (identifierValue, withIdentifier,
 * mergeOtherIdentifierValues, withElectedPrimary): their inputs are deep-frozen,
 * so any in-place write throws instead of passing unnoticed.
 */
import {describe, expect, it} from 'vitest';
import {columnsToIdentifierRows, identifierRowsToColumns, nextAvailableIdentifierType, fieldToIdType, identifierValue, withIdentifier, mergeOtherIdentifierValues, withElectedPrimary, type IdentifierRow} from './assetIdentifiers';

const row = (type: string, value: string): IdentifierRow => ({id: `id-${type}-${value}`, type, value});

/** Freezes `value` and everything inside it, so an in-place write throws (ES modules run in strict mode). */
function deepFreeze<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const nested of Object.values(value as Record<string, unknown>)) deepFreeze(nested);
        Object.freeze(value);
    }
    return value;
}

/** Rows minted by generateUUID carry opaque ids: non-empty strings, distinct from each other and from `existing`. */
function expectFreshIds(minted: IdentifierRow[], existing: IdentifierRow[] = []) {
    const ids = minted.map((r) => r.id);
    expect(ids.every((id) => typeof id === 'string' && id.length > 0)).toBe(true);
    expect(new Set([...ids, ...existing.map((r) => r.id)]).size).toBe(ids.length + existing.length);
}

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

describe('identifierValue', () => {
    it('returns the value of the first row of the type', () => {
        const rows = [row('TICKER', 'AAPL'), {id: 'isin-1', type: 'ISIN', value: 'US0378331005'}, {id: 'isin-2', type: 'ISIN', value: 'IE00B4L5Y983'}];
        expect(identifierValue(rows, 'ISIN')).toBe('US0378331005');
        expect(identifierValue(rows, 'TICKER')).toBe('AAPL');
    });

    it('returns "" when no row has the type', () => {
        expect(identifierValue([row('TICKER', 'AAPL')], 'ISIN')).toBe('');
        expect(identifierValue([], 'ISIN')).toBe('');
    });

    it('matches the type exactly: rows carry the upper-case type', () => {
        expect(identifierValue([row('ISIN', 'US0378331005')], 'isin')).toBe('');
    });
});

describe('withIdentifier', () => {
    it('writes the value into the row of the type, keeping its id, and marks it auto-filled', () => {
        const rows = deepFreeze([row('ISIN', 'OLD'), row('TICKER', 'AAPL')]);
        const next = withIdentifier(rows, 'ISIN', 'US0378331005');
        expect(next).toStrictEqual([{id: 'id-ISIN-OLD', type: 'ISIN', value: 'US0378331005', autoFilled: true}, row('TICKER', 'AAPL')]);
        // A new array; the rows of other types are carried over as they are.
        expect(next).not.toBe(rows);
        expect(next[1]).toBe(rows[1]);
    });

    it('rewrites every row of the type, not only the first', () => {
        const rows = deepFreeze([{id: 'a', type: 'OTHER', value: 'x'}, row('ISIN', 'I'), {id: 'b', type: 'OTHER', value: 'y'}]);
        expect(withIdentifier(rows, 'OTHER', 'z')).toStrictEqual([{id: 'a', type: 'OTHER', value: 'z', autoFilled: true}, row('ISIN', 'I'), {id: 'b', type: 'OTHER', value: 'z', autoFilled: true}]);
    });

    it('appends an auto-filled row with a fresh id when the type is absent', () => {
        const rows = deepFreeze([row('TICKER', 'AAPL')]);
        const next = withIdentifier(rows, 'ISIN', 'US0378331005');
        expect(next).toStrictEqual([row('TICKER', 'AAPL'), {id: expect.any(String), type: 'ISIN', value: 'US0378331005', autoFilled: true}]);
        expect(next[0]).toBe(rows[0]);
        expectFreshIds(next.slice(1), rows);
        expect(rows).toHaveLength(1);
    });
});

describe('mergeOtherIdentifierValues', () => {
    it('adds each element of a list as an auto-filled OTHER row with a fresh id', () => {
        const rows = deepFreeze([row('ISIN', 'US0378331005')]);
        const merged = mergeOtherIdentifierValues(rows, ['AAPL.MI', 'APC.DE']);
        expect(merged.added).toBe(2);
        expect(merged.rows).toStrictEqual([row('ISIN', 'US0378331005'), {id: expect.any(String), type: 'OTHER', value: 'AAPL.MI', autoFilled: true}, {id: expect.any(String), type: 'OTHER', value: 'APC.DE', autoFilled: true}]);
        expect(merged.rows).not.toBe(rows);
        expect(merged.rows[0]).toBe(rows[0]);
        expectFreshIds(merged.rows.slice(1), rows);
    });

    it('takes a non-array, non-null value as a single element', () => {
        expect(mergeOtherIdentifierValues([], 'AAPL.MI').rows.map((r) => r.value)).toEqual(['AAPL.MI']);
        expect(mergeOtherIdentifierValues([], 12345).rows.map((r) => r.value)).toEqual(['12345']);
        // `!= null`, not truthiness: a 0 is a value like any other, stringified.
        expect(mergeOtherIdentifierValues([], 0).rows.map((r) => r.value)).toEqual(['0']);
    });

    it.each<[string, unknown]>([
        ['null', null],
        ['undefined', undefined],
        ['an empty list', []],
    ])('adds nothing for %s and hands back the same rows', (_label, raw) => {
        const rows = [row('OTHER', 'kept')];
        const merged = mergeOtherIdentifierValues(rows, raw);
        expect(merged.added).toBe(0);
        expect(merged.rows).toBe(rows);
    });

    it('stringifies and trims each element, skipping those left empty', () => {
        const merged = mergeOtherIdentifierValues([], ['  AAPL.MI  ', 42, null, undefined, '   ', '']);
        expect(merged.rows.map((r) => r.value)).toEqual(['AAPL.MI', '42']);
        expect(merged.added).toBe(2);
    });

    it('dedups against the OTHER rows already there: trimmed, but case-sensitive', () => {
        const rows = deepFreeze([{id: 'o1', type: 'OTHER', value: '  apc.de '}]);
        const merged = mergeOtherIdentifierValues(rows, ['apc.de', 'APC.DE']);
        expect(merged.added).toBe(1);
        expect(merged.rows.map((r) => r.value)).toEqual(['  apc.de ', 'APC.DE']);
    });

    it('dedups within the incoming batch', () => {
        const merged = mergeOtherIdentifierValues([], ['AAPL.MI', ' AAPL.MI ', 'AAPL.MI']);
        expect(merged.rows.map((r) => r.value)).toEqual(['AAPL.MI']);
        expect(merged.added).toBe(1);
    });

    it('dedups against OTHER rows only, not against the typed ones', () => {
        const merged = mergeOtherIdentifierValues([row('TICKER', 'AAPL')], ['AAPL']);
        expect(merged.added).toBe(1);
        expect(merged.rows.map((r) => [r.type, r.value])).toEqual([
            ['TICKER', 'AAPL'],
            ['OTHER', 'AAPL'],
        ]);
    });

    it('reads a non-string value on an existing OTHER row instead of throwing', () => {
        const rows = [
            {id: 'n', type: 'OTHER', value: 42 as unknown as string},
            {id: 'u', type: 'OTHER', value: undefined as unknown as string},
        ];
        const merged = mergeOtherIdentifierValues(rows, ['42', 'new']);
        expect(merged.added).toBe(1);
        expect(merged.rows.slice(2).map((r) => r.value)).toEqual(['new']);
    });

    it('hands back the same rows when every element is already known', () => {
        const rows = deepFreeze([row('OTHER', 'AAPL.MI')]);
        const merged = mergeOtherIdentifierValues(rows, ['AAPL.MI', ' AAPL.MI']);
        expect(merged.added).toBe(0);
        expect(merged.rows).toBe(rows);
    });
});

describe('withElectedPrimary', () => {
    it('writes the primary into the row of the type and demotes the other choice to a plain OTHER row', () => {
        const rows = deepFreeze([{id: 'isin', type: 'ISIN', value: 'IT0005556990'}, row('TICKER', 'BTP')]);
        const next = withElectedPrimary(rows, 'ISIN', 'IT0005557006', ['IT0005557006', 'IT0005556990']);
        // Neither the primary row nor the demoted one is flagged auto-filled: the user chose them.
        expect(next).toStrictEqual([{id: 'isin', type: 'ISIN', value: 'IT0005557006'}, row('TICKER', 'BTP'), {id: expect.any(String), type: 'OTHER', value: 'IT0005556990'}]);
        expect(next[1]).toBe(rows[1]);
        expectFreshIds(next.slice(2), rows);
    });

    it('keeps whatever else the primary row carried', () => {
        const rows = deepFreeze([{id: 'isin', type: 'ISIN', value: 'IT0005556990', autoFilled: true}]);
        expect(withElectedPrimary(rows, 'ISIN', 'IT0005557006', ['IT0005557006'])).toStrictEqual([{id: 'isin', type: 'ISIN', value: 'IT0005557006', autoFilled: true}]);
    });

    it('does not demote a choice equal to the primary in another case', () => {
        const next = withElectedPrimary([row('ISIN', 'x')], 'ISIN', 'IT0005557006', ['it0005557006', 'IT0005556990']);
        expect(next.filter((r) => r.type === 'OTHER').map((r) => r.value)).toEqual(['IT0005556990']);
    });

    it('does not demote a choice already among the OTHER rows (trimmed, case-insensitive)', () => {
        const rows = deepFreeze([row('ISIN', 'IT0005557006'), {id: 'o', type: 'OTHER', value: '  it0005556990 '}]);
        expect(withElectedPrimary(rows, 'ISIN', 'IT0005557006', ['IT0005557006', 'IT0005556990'])).toStrictEqual([row('ISIN', 'IT0005557006'), {id: 'o', type: 'OTHER', value: '  it0005556990 '}]);
    });

    it('demotes a choice once, even when it is offered twice in different cases', () => {
        const next = withElectedPrimary([row('ISIN', 'A')], 'ISIN', 'A', ['A', 'IT0005556990', 'it0005556990']);
        expect(next.filter((r) => r.type === 'OTHER').map((r) => r.value)).toEqual(['IT0005556990']);
    });

    it('never writes into its inputs', () => {
        const rows = deepFreeze([row('ISIN', 'IT0005556990'), row('OTHER', 'BTP-VALORE')]);
        const choices = deepFreeze(['IT0005557006', 'IT0005556990']);
        const next = withElectedPrimary(rows, 'ISIN', 'IT0005557006', choices);
        expect(next).not.toBe(rows);
        expect(rows).toEqual([row('ISIN', 'IT0005556990'), row('OTHER', 'BTP-VALORE')]);
        expect(choices).toEqual(['IT0005557006', 'IT0005556990']);
    });

    it('writes no primary when no row of the type exists (the chooser only opens on a conflict, i.e. over an existing row)', () => {
        const next = withElectedPrimary([row('TICKER', 'BTP')], 'ISIN', 'IT0005557006', ['IT0005557006', 'IT0005556990']);
        expect(next.map((r) => [r.type, r.value])).toEqual([
            ['TICKER', 'BTP'],
            ['OTHER', 'IT0005556990'],
        ]);
    });
});
