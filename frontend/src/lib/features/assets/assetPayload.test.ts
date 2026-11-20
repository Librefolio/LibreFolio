/**
 * assetPayload — pure unit tests for the shared save-path builders.
 */
import {describe, expect, it} from 'vitest';
import {normalizeQuoteBaseQuantity, normalizeDistribution, buildCreateItem, buildPatchItem, buildProviderAssignItem} from './assetPayload';
import type {AssetFormFields, ProviderAssignment} from './assetPayload';
import type {IdentifierRow} from './assetIdentifiers';

describe('normalizeQuoteBaseQuantity', () => {
    it('passes a positive quantity through unchanged', () => {
        expect(normalizeQuoteBaseQuantity(1)).toBe(1);
        expect(normalizeQuoteBaseQuantity(100)).toBe(100);
    });

    it('floors a non-positive or falsy quantity to 1', () => {
        expect(normalizeQuoteBaseQuantity(0)).toBe(1);
        expect(normalizeQuoteBaseQuantity(-5)).toBe(1);
        expect(normalizeQuoteBaseQuantity(NaN)).toBe(1);
    });
});

describe('normalizeDistribution', () => {
    it('accepts numeric strings and numbers, coercing both to number', () => {
        expect(normalizeDistribution({Tech: '0.4', Health: 0.6})).toEqual({Tech: 0.4, Health: 0.6});
    });

    it.each([
        ['non-numeric string', 'abc'],
        ['NaN', NaN],
        ['positive Infinity', Infinity],
        ['negative Infinity', -Infinity],
        ['blank/whitespace string', '   '],
    ])('throws on a non-finite weight (%s)', (_label, value) => {
        expect(() => normalizeDistribution({Tech: value as string | number})).toThrow('Invalid distribution weight.');
    });
});

// The request items of the AssetModal save paths, built from a plain copy of the form.
const idRow = (type: string, value: string): IdentifierRow => ({id: `id-${type}-${value}`, type, value});

/** A minimal form: a named USD stock, nothing optional set. Each test overrides what it reads. */
function form(overrides: Partial<AssetFormFields> = {}): AssetFormFields {
    return {
        displayName: 'Apple Inc.',
        currency: 'USD',
        assetType: 'STOCK',
        iconUrl: null,
        quoteBaseQuantity: 1,
        active: true,
        isBenchmark: false,
        userUrl: '',
        identifierRows: [],
        enrichers: {},
        profile: {},
        ...overrides,
    };
}

/** Every optional field set, untrimmed name and ISIN, two OTHER identifiers. */
const FILLED: Partial<AssetFormFields> = {
    displayName: '  Apple Inc.  ',
    iconUrl: 'https://example.test/aapl.png',
    quoteBaseQuantity: 10,
    active: false,
    isBenchmark: true,
    userUrl: 'https://example.test/quote/AAPL',
    identifierRows: [idRow('ISIN', ' US0378331005 '), idRow('OTHER', 'APC.DE'), idRow('OTHER', 'AAPL.MI')],
};

describe('buildCreateItem', () => {
    it('builds the create item from a filled form, identifier columns from the rows', () => {
        expect(buildCreateItem(form(FILLED))).toStrictEqual({
            display_name: 'Apple Inc.',
            currency: 'USD',
            asset_type: 'STOCK',
            icon_url: 'https://example.test/aapl.png',
            quote_base_quantity: 10,
            active: false,
            is_benchmark: true,
            user_url: 'https://example.test/quote/AAPL',
            identifier_isin: 'US0378331005',
            identifier_ticker: undefined,
            identifier_cusip: undefined,
            identifier_sedol: undefined,
            identifier_figi: undefined,
            identifier_uuid: undefined,
            identifier_other: ['APC.DE', 'AAPL.MI'],
        });
    });

    it.each<[string, string | null]>([
        ['an empty', ''],
        ['a null', null],
    ])('leaves out %s icon', (_label, iconUrl) => {
        expect(buildCreateItem(form({iconUrl})).icon_url).toBeUndefined();
    });

    it('leaves out an empty user URL and every unset identifier column, and never sends a classification (plan 68, E9)', () => {
        const item = buildCreateItem(form());
        expect(item.user_url).toBeUndefined();
        // Description, sectors and countries are the profile's: they leave as `profile`, never as `classification_params`
        expect(item).not.toHaveProperty('classification_params');
        // The inferred item type drops the index signature of the spread identifier columns: read them through a string-keyed view.
        const columns: Record<string, unknown> = item;
        expect([columns.identifier_isin, columns.identifier_ticker, columns.identifier_cusip, columns.identifier_sedol, columns.identifier_figi, columns.identifier_uuid, columns.identifier_other]).toEqual(Array(7).fill(undefined));
    });

    it.each([[0], [-2], [NaN]])('floors a quote base quantity of %s to 1', (quoteBaseQuantity) => {
        expect(buildCreateItem(form({quoteBaseQuantity})).quote_base_quantity).toBe(1);
    });
});

describe('buildPatchItem', () => {
    it('builds the patch item from a filled form', () => {
        expect(buildPatchItem(42, form(FILLED))).toStrictEqual({
            asset_id: 42,
            display_name: 'Apple Inc.',
            currency: 'USD',
            asset_type: 'STOCK',
            icon_url: 'https://example.test/aapl.png',
            quote_base_quantity: 10,
            active: false,
            is_benchmark: true,
            user_url: 'https://example.test/quote/AAPL',
            identifier_isin: 'US0378331005',
            identifier_ticker: null,
            identifier_cusip: null,
            identifier_sedol: null,
            identifier_figi: null,
            identifier_uuid: null,
            identifier_other: ['APC.DE', 'AAPL.MI'],
        });
    });

    it('passes the icon as it is, null and empty included', () => {
        expect(buildPatchItem(1, form({iconUrl: null})).icon_url).toBeNull();
        expect(buildPatchItem(1, form({iconUrl: ''})).icon_url).toBe('');
    });

    it('puts a removed icon on the wire as an explicit null, never as a missing key (T-2)', () => {
        // The picker's red x then «Use selected» leaves iconUrl null. The backend clears the column only when the key is
        // present: an undefined would vanish from the JSON body and the removal would answer success and change nothing.
        const wire = JSON.parse(JSON.stringify([buildPatchItem(7, form({...FILLED, iconUrl: null}))]));
        expect(wire[0]).toHaveProperty('icon_url', null);
        expect(wire[0]).toHaveProperty('user_url', 'https://example.test/quote/AAPL');
    });

    it('trims the name and floors the quote base quantity, like the create item', () => {
        const item = buildPatchItem(1, form({displayName: '  Apple Inc.  ', quoteBaseQuantity: 0}));
        expect(item.display_name).toBe('Apple Inc.');
        expect(item.quote_base_quantity).toBe(1);
    });

    it('clears, with null, the user URL and the identifier columns the create item would leave out', () => {
        const item = buildPatchItem(1, form({userUrl: ''}));
        expect(item.user_url).toBeNull();
        expect([item.identifier_isin, item.identifier_ticker, item.identifier_cusip, item.identifier_sedol, item.identifier_figi, item.identifier_uuid]).toEqual(Array(6).fill(null));
    });

    it('sends the OTHER identifiers as an empty list when the last OTHER row is gone, never null', () => {
        // The backend reads `identifier_other: null` as "leave unchanged": only `[]` clears the list. A blank OTHER row
        // counts as no row.
        const noOther = [idRow('ISIN', 'US0378331005'), idRow('OTHER', '   ')];
        const wire = JSON.parse(JSON.stringify([buildPatchItem(7, form({...FILLED, identifierRows: noOther}))]));
        expect(wire[0]).toHaveProperty('identifier_other', []);
        expect(wire[0]).toHaveProperty('identifier_isin', 'US0378331005');
        expect(buildPatchItem(7, form(FILLED)).identifier_other).toEqual(['APC.DE', 'AAPL.MI']);
    });

    it('never sends a classification: the description, the sectors and the countries are the profile’s (plan 68, E9)', () => {
        expect(buildPatchItem(1, form(FILLED))).not.toHaveProperty('classification_params');
    });
});

describe('the enrichers on the asset (plan 68, E8a)', () => {
    const JUSTETF = {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'};
    const YAHOO = {identifier_type: 'TICKER', identifier: 'VWCE.DE'};

    it('creates the asset with the enrichers chosen, in their order, and without the key when there are none', () => {
        const item = buildCreateItem(form({enrichers: {yahoo_finance: YAHOO, justetf: JUSTETF}}));
        expect(Object.keys(item.enrichers ?? {})).toEqual(['yahoo_finance', 'justetf']);
        expect(item.enrichers).toEqual({yahoo_finance: YAHOO, justetf: JUSTETF});
        expect(buildCreateItem(form())).not.toHaveProperty('enrichers');
    });

    it('leaves the enrichers out of an edit that did not change them: absent means unchanged', () => {
        const initial = {justetf: JUSTETF, yahoo_finance: YAHOO};
        expect(buildPatchItem(1, form({enrichers: {justetf: {...JUSTETF}, yahoo_finance: {...YAHOO}}}), initial)).not.toHaveProperty('enrichers');
    });

    it('sends the whole list when the order, a binding or the set changed; {} to clear them all', () => {
        const initial = {justetf: JUSTETF, yahoo_finance: YAHOO};
        expect(buildPatchItem(1, form({enrichers: {yahoo_finance: YAHOO, justetf: JUSTETF}}), initial).enrichers).toEqual({yahoo_finance: YAHOO, justetf: JUSTETF});
        expect(buildPatchItem(1, form({enrichers: {justetf: JUSTETF, yahoo_finance: {...YAHOO, identifier: 'VWRA.L'}}}), initial)).toHaveProperty('enrichers');
        expect(buildPatchItem(1, form({enrichers: {}}), initial).enrichers).toEqual({});
    });
});

describe('the profile on the asset (plan 68, E8b)', () => {
    const PROFILE = {ter: '0.002', fund_provider: {from: 'justetf', seen: 'Vanguard'}, withholding_tax: null};

    it('creates the asset with the pending changes of the profile, and without the key when there are none', () => {
        expect(buildCreateItem(form({profile: PROFILE})).profile).toEqual(PROFILE);
        expect(buildCreateItem(form())).not.toHaveProperty('profile');
    });

    it('sends the profile on an edit only when a change waits: absent leaves every voice untouched', () => {
        expect(buildPatchItem(1, form({profile: PROFILE})).profile).toEqual(PROFILE);
        expect(buildPatchItem(1, form())).not.toHaveProperty('profile');
    });
});

describe('buildProviderAssignItem', () => {
    it('maps the provider onto the assignment request item', () => {
        const provider: ProviderAssignment = {code: 'yfinance', identifier: 'AAPL', identifierType: 'TICKER', params: {currency: 'USD'}};
        expect(buildProviderAssignItem(7, provider)).toStrictEqual({asset_id: 7, provider_code: 'yfinance', identifier: 'AAPL', identifier_type: 'TICKER', provider_params: {currency: 'USD'}});
    });

    it('keeps null provider params as null', () => {
        const provider: ProviderAssignment = {code: 'justetf', identifier: 'IE00B4L5Y983', identifierType: 'ISIN', params: null};
        expect(buildProviderAssignItem(7, provider)).toStrictEqual({asset_id: 7, provider_code: 'justetf', identifier: 'IE00B4L5Y983', identifier_type: 'ISIN', provider_params: null});
    });
});
