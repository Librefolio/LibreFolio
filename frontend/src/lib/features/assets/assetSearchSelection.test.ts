/**
 * assetSearchSelection — pure unit tests.
 *
 * What choosing a provider search result writes into AssetModal, decided without
 * mounting it: the asset type the result maps to, what its typed identifier does
 * to the form's rows (nothing, a "which code leads" conflict, or the rows with the
 * code written in) and the provider params carried over. Inputs are deep-frozen,
 * so any in-place write throws; minted row ids are opaque (generateUUID), so we
 * assert on their freshness, never on a value.
 */
import {describe, expect, it} from 'vitest';
import {ASSET_TYPES} from '$lib/utils/assetTypes';
import {searchResultAssetType, searchResultAssignmentType, searchResultIdentifier, searchResultProviderParams, type SearchIdentifierOutcome} from './assetSearchSelection';
import type {IdentifierRow} from './assetIdentifiers';

const row = (type: string, value: string): IdentifierRow => ({id: `id-${type}-${value}`, type, value});

/** Freezes `value` and everything inside it, so an in-place write throws (ES modules run in strict mode). */
function deepFreeze<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const nested of Object.values(value as Record<string, unknown>)) deepFreeze(nested);
        Object.freeze(value);
    }
    return value;
}

/** The rows of a `rows` outcome; any other outcome is a failure. */
function rowsOf(outcome: SearchIdentifierOutcome): IdentifierRow[] {
    if (outcome.kind !== 'rows') throw new Error(`expected a 'rows' outcome, got '${outcome.kind}'`);
    return outcome.rows;
}

describe('searchResultAssetType', () => {
    it('upper-cases a known type', () => {
        expect(searchResultAssetType('etf')).toBe('ETF');
        expect(searchResultAssetType('Etf_Stock')).toBe('ETF_STOCK');
        expect(searchResultAssetType('BOND')).toBe('BOND');
    });

    it('recognises every type of the generated enum, whatever its case', () => {
        expect(ASSET_TYPES.map((type) => searchResultAssetType(type.toLowerCase()))).toEqual([...ASSET_TYPES]);
    });

    it('maps a type the enum does not know to OTHER', () => {
        expect(searchResultAssetType('warrant')).toBe('OTHER');
        expect(searchResultAssetType('')).toBe('OTHER');
    });
});

describe('searchResultIdentifier', () => {
    it.each<[string, string | null | undefined]>([
        ['null', null],
        ['undefined', undefined],
        ['empty', ''],
    ])('does nothing when the identifier type is %s', (_label, identifierType) => {
        expect(searchResultIdentifier([row('ISIN', '')], identifierType, 'IT0005557006')).toEqual({kind: 'none'});
    });

    it.each<[string, unknown]>([
        ['empty', ''],
        ['null', null],
        ['undefined', undefined],
        ['0', 0],
    ])('does nothing when the identifier is %s', (_label, identifier) => {
        expect(searchResultIdentifier([], 'ISIN', identifier)).toEqual({kind: 'none'});
    });

    it('appends a row, upper-cased type and trimmed code, when the form has none of that type', () => {
        const rows = deepFreeze([row('TICKER', 'BTP')]);
        const next = rowsOf(searchResultIdentifier(rows, 'isin', '  IT0005557006 '));
        // Typed by the search, not auto-filled by the provider: no autoFilled flag.
        expect(next).toStrictEqual([row('TICKER', 'BTP'), {id: expect.any(String), type: 'ISIN', value: 'IT0005557006'}]);
        expect(next[0]).toBe(rows[0]);
        expect(typeof next[1].id === 'string' && next[1].id.length > 0).toBe(true);
        expect(next[1].id).not.toBe(rows[0].id);
    });

    it.each<[string, string]>([
        ['an empty', ''],
        ['a blank', '   '],
    ])('writes the code into %s row of the type, keeping its id', (_label, value) => {
        const rows = deepFreeze([{id: 'isin', type: 'ISIN', value}, row('TICKER', 'BTP')]);
        const next = rowsOf(searchResultIdentifier(rows, 'ISIN', ' IT0005557006 '));
        expect(next).toStrictEqual([{id: 'isin', type: 'ISIN', value: 'IT0005557006'}, row('TICKER', 'BTP')]);
        expect(next[1]).toBe(rows[1]);
    });

    it('takes the incoming spelling when the row holds the same code in another case', () => {
        const rows = deepFreeze([{id: 'isin', type: 'ISIN', value: ' it0005557006 '}]);
        expect(searchResultIdentifier(rows, 'ISIN', 'IT0005557006')).toStrictEqual({kind: 'rows', rows: [{id: 'isin', type: 'ISIN', value: 'IT0005557006'}]});
    });

    it('reports a conflict, both codes trimmed, when the row holds a different code', () => {
        const rows = deepFreeze([{id: 'isin', type: 'ISIN', value: '  IT0005556990 '}]);
        expect(searchResultIdentifier(rows, 'isin', ' IT0005557006  ')).toStrictEqual({kind: 'conflict', type: 'ISIN', incoming: 'IT0005557006', current: 'IT0005556990'});
    });

    it('stringifies a non-string identifier, for the new row and for the comparison', () => {
        expect(rowsOf(searchResultIdentifier([], 'ticker', 12345))).toStrictEqual([{id: expect.any(String), type: 'TICKER', value: '12345'}]);
        expect(searchResultIdentifier([row('TICKER', '12345')], 'TICKER', 12345)).toStrictEqual({kind: 'rows', rows: [row('TICKER', '12345')]});
        expect(searchResultIdentifier([row('TICKER', '999')], 'TICKER', 12345)).toStrictEqual({kind: 'conflict', type: 'TICKER', incoming: '12345', current: '999'});
    });

    it('never writes into the rows it is given', () => {
        const rows = [{id: 'isin', type: 'ISIN', value: ''}, row('TICKER', 'BTP')];
        const next = rowsOf(searchResultIdentifier(rows, 'ISIN', 'IT0005557006'));
        expect(next).not.toBe(rows);
        expect(next[0]).not.toBe(rows[0]);
        expect(rows).toStrictEqual([{id: 'isin', type: 'ISIN', value: ''}, row('TICKER', 'BTP')]);
    });
});

// Project 76, P3 (the consultant's rule, corrected 18/11): a provider that accepts COINGECKO_ID (CoinGecko) has its own
// code typed OTHER in a search row. For such a provider only, OTHER is a list that grows: the code is written as
// `<provider>:<code>` (`coingecko:bitcoin`), never in conflict, and the assignment takes COINGECKO_ID. Every other
// provider's OTHER row stays exactly as before (Borsa Italiana's fallback: one OTHER row, the server reads OTHER as URL).
const COINGECKO = {code: 'coingecko', acceptedTypes: ['COINGECKO_ID']};
const BORSA_ITALIANA = {code: 'borsa_italiana', acceptedTypes: ['ISIN']};

describe("searchResultIdentifier — a provider's own code (OTHER, COINGECKO_ID)", () => {
    it('adds `<provider>:<code>` beside the OTHER rows already there, with no conflict, the ticker row untouched', () => {
        const rows = deepFreeze([row('TICKER', 'BTC'), row('OTHER', 'broker-label')]);
        const next = rowsOf(searchResultIdentifier(rows, 'OTHER', ' bitcoin ', COINGECKO));
        expect(next).toStrictEqual([row('TICKER', 'BTC'), row('OTHER', 'broker-label'), {id: expect.any(String), type: 'OTHER', value: 'coingecko:bitcoin'}]);
    });

    it('adds nothing when the list already holds it, in any case', () => {
        const rows = deepFreeze([row('OTHER', 'CoinGecko:Bitcoin')]);
        expect(rowsOf(searchResultIdentifier(rows, 'other', 'bitcoin', COINGECKO))).toStrictEqual([row('OTHER', 'CoinGecko:Bitcoin')]);
    });

    it('writes into an empty OTHER row instead of adding one', () => {
        const rows = deepFreeze([{id: 'other', type: 'OTHER', value: '  '}]);
        expect(rowsOf(searchResultIdentifier(rows, 'OTHER', 'bitcoin', COINGECKO))).toStrictEqual([{id: 'other', type: 'OTHER', value: 'coingecko:bitcoin'}]);
    });

    it("leaves Borsa Italiana's fallback row (a fund's internal code, typed OTHER) as before: no prefix, a conflict with another OTHER code", () => {
        expect(rowsOf(searchResultIdentifier([], 'OTHER', '2FADB', BORSA_ITALIANA))).toStrictEqual([{id: expect.any(String), type: 'OTHER', value: '2FADB'}]);
        expect(searchResultIdentifier(deepFreeze([row('OTHER', 'broker-label')]), 'OTHER', '2FADB', BORSA_ITALIANA)).toStrictEqual({kind: 'conflict', type: 'OTHER', incoming: '2FADB', current: 'broker-label'});
    });

    it('keeps the behaviour of before when the provider is not known', () => {
        expect(rowsOf(searchResultIdentifier([], 'OTHER', 'bitcoin'))).toStrictEqual([{id: expect.any(String), type: 'OTHER', value: 'bitcoin'}]);
    });
});

describe('searchResultAssignmentType', () => {
    it('keeps a type the assignment accepts (a ProviderInputType), upper-cased', () => {
        expect(searchResultAssignmentType('isin', ['ISIN'])).toBe('ISIN');
        expect(searchResultAssignmentType('TICKER', ['TICKER', 'ISIN'])).toBe('TICKER');
    });

    it('gives OTHER the COINGECKO_ID of a provider that accepts it', () => {
        expect(searchResultAssignmentType('OTHER', ['COINGECKO_ID'])).toBe('COINGECKO_ID');
        expect(searchResultAssignmentType('other', ['TICKER', 'COINGECKO_ID'])).toBe('COINGECKO_ID');
    });

    it('leaves OTHER as it is for any other provider (Borsa Italiana), or an unknown one: the server reads it as URL, as before', () => {
        expect(searchResultAssignmentType('OTHER', ['ISIN'])).toBe('OTHER');
        expect(searchResultAssignmentType('OTHER', [])).toBe('OTHER');
    });
});

// Project 76, P3: the result's currency joins the params only when the provider's params schema has a `currency`
// field (justETF, the CSS scraper); CoinGecko's `vs_currency` and Yahoo's empty schema get none. With the schema not
// known, as before.
describe('searchResultProviderParams — only a provider with a currency param gets it', () => {
    it('adds it when the schema has a currency field', () => {
        expect(searchResultProviderParams({language: 'it'}, 'EUR', ['currency', 'language'])).toStrictEqual({language: 'it', currency: 'EUR'});
    });

    it('adds nothing when the schema has none (CoinGecko, a provider with no params)', () => {
        expect(searchResultProviderParams({vs_currency: 'EUR'}, 'EUR', ['vs_currency'])).toStrictEqual({vs_currency: 'EUR'});
        expect(searchResultProviderParams(null, 'USD', [])).toBeNull();
    });

    it('adds it as before when the schema is not known', () => {
        expect(searchResultProviderParams({vs_currency: 'EUR'}, 'EUR', null)).toStrictEqual({vs_currency: 'EUR', currency: 'EUR'});
    });
});

describe('searchResultProviderParams', () => {
    it('copies the provider params and adds the result currency when the provider set none', () => {
        const params = deepFreeze({language: 'it'});
        const merged = searchResultProviderParams(params, 'USD');
        expect(merged).toEqual({language: 'it', currency: 'USD'});
        expect(merged).not.toBe(params);
        expect(params).toEqual({language: 'it'});
    });

    it("keeps the provider's own currency, even when the result says otherwise", () => {
        expect(searchResultProviderParams(deepFreeze({currency: 'EUR', language: 'it'}), 'USD')).toEqual({currency: 'EUR', language: 'it'});
    });

    it('treats a currency key the provider set to null as its own choice (key presence, not truthiness)', () => {
        expect(searchResultProviderParams({currency: null}, 'USD')).toEqual({currency: null});
    });

    it.each<[string, string | null | undefined]>([
        ['empty', ''],
        ['null', null],
        ['undefined', undefined],
    ])('adds no currency when the result currency is %s', (_label, currency) => {
        expect(searchResultProviderParams({language: 'it'}, currency)).toEqual({language: 'it'});
    });

    it('builds the params from the result currency alone when the provider sent none', () => {
        expect(searchResultProviderParams(null, 'USD')).toEqual({currency: 'USD'});
        expect(searchResultProviderParams(undefined, 'USD')).toEqual({currency: 'USD'});
        expect(searchResultProviderParams({}, 'USD')).toEqual({currency: 'USD'});
    });

    it.each<[string, Record<string, any> | null | undefined, string | null | undefined]>([
        ['null params, null currency', null, null],
        ['undefined params, empty currency', undefined, ''],
        ['empty params, undefined currency', {}, undefined],
    ])('returns null when nothing remains (%s)', (_label, params, currency) => {
        expect(searchResultProviderParams(params, currency)).toBeNull();
    });

    it('returns a copy, never the provider object itself, even when nothing is added', () => {
        const params = deepFreeze({language: 'it', currency: 'EUR'});
        const merged = searchResultProviderParams(params, 'USD');
        expect(merged).toEqual({language: 'it', currency: 'EUR'});
        expect(merged).not.toBe(params);
    });
});
