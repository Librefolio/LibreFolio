/**
 * assetPayload — pure unit tests for the shared save-path builders.
 */
import {describe, expect, it} from 'vitest';
import {normalizeQuoteBaseQuantity, buildClassificationParams, buildClassificationPatch, normalizeDistribution, sameDistribution, buildCreateItem, buildPatchItem, buildProviderAssignItem} from './assetPayload';
import type {AssetFormFields, ClassificationParams, ProviderAssignment} from './assetPayload';
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

describe('buildClassificationParams', () => {
    it('returns undefined when nothing is set', () => {
        expect(buildClassificationParams('', {}, {})).toBeUndefined();
    });

    it('includes only the short_description when only it is set', () => {
        expect(buildClassificationParams('a bond', {}, {})).toEqual({short_description: 'a bond'});
    });

    it('wraps sector and geographic distributions under a distribution key', () => {
        const out = buildClassificationParams('', {Tech: 0.6, Health: 0.4}, {US: 1});
        expect(out).toEqual({
            sector_area: {distribution: {Tech: 0.6, Health: 0.4}},
            geographic_area: {distribution: {US: 1}},
        });
    });

    it('omits an empty distribution but keeps a non-empty sibling', () => {
        const out = buildClassificationParams('', {Tech: 1}, {});
        expect(out).toEqual({sector_area: {distribution: {Tech: 1}}});
        expect(out).not.toHaveProperty('geographic_area');
    });

    it('assembles all three parts together', () => {
        const out = buildClassificationParams('desc', {S: 1}, {G: 1});
        expect(out).toEqual({
            short_description: 'desc',
            sector_area: {distribution: {S: 1}},
            geographic_area: {distribution: {G: 1}},
        });
    });
});

// Root cause E2: a full-block replace silently dropped untouched
// classification_params subfields on the wire. buildClassificationPatch is the
// frontend half of that fix — it must diff previous vs. current per subfield
// (omit unchanged, null only what actually cleared) so the backend's own
// per-field shallow merge (see backend/app/services/assets/crud.py
// patch_assets_bulk) receives exactly the intended keys.
describe('buildClassificationPatch', () => {
    const full: ClassificationParams = {
        short_description: 'a bond',
        sector_area: {distribution: {Tech: 0.4, Health: 0.6}},
        geographic_area: {distribution: {US: 1}},
    };

    it('omits the patch when nothing was ever set (unknown initial state)', () => {
        expect(buildClassificationPatch(undefined, undefined)).toBeUndefined();
    });

    it('omits the patch when current is identical to previous', () => {
        const current: ClassificationParams = {
            short_description: 'a bond',
            sector_area: {distribution: {Tech: 0.4, Health: 0.6}},
            geographic_area: {distribution: {US: 1}},
        };
        expect(buildClassificationPatch(full, current)).toBeUndefined();
    });

    it('treats equal weights under a different key order as no change', () => {
        const current: ClassificationParams = {
            short_description: 'a bond',
            sector_area: {distribution: {Health: 0.6, Tech: 0.4}}, // same pairs, keys reordered
            geographic_area: {distribution: {US: 1}},
        };
        expect(buildClassificationPatch(full, current)).toBeUndefined();
    });

    it('sends a whole-block null when the last remaining field is cleared', () => {
        // previous carries every subfield; current is undefined, i.e. the editor
        // ends up with nothing left at all — this must collapse to a single
        // top-level null, not an object of three null subfields.
        expect(buildClassificationPatch(full, undefined)).toBeNull();
    });

    it('nulls only the cleared subfield, leaving siblings out of the patch entirely', () => {
        // sector_area is dropped, short_description/geographic_area are unchanged
        // and current is still a real object (not undefined) — so this must NOT
        // hit the whole-block-null branch, and must not mention the untouched
        // siblings at all (omission, not a redundant same-value key).
        const current: ClassificationParams = {
            short_description: 'a bond',
            geographic_area: {distribution: {US: 1}},
        };
        const patch = buildClassificationPatch(full, current);
        expect(patch).toEqual({sector_area: null});
        expect(patch).not.toHaveProperty('short_description');
        expect(patch).not.toHaveProperty('geographic_area');
    });

    it('patches only short_description when only the description changed', () => {
        const current: ClassificationParams = {
            short_description: 'an updated bond',
            sector_area: {distribution: {Tech: 0.4, Health: 0.6}},
            geographic_area: {distribution: {US: 1}},
        };
        const patch = buildClassificationPatch(full, current);
        expect(patch).toEqual({short_description: 'an updated bond'});
        expect(patch).not.toHaveProperty('sector_area');
        expect(patch).not.toHaveProperty('geographic_area');
    });
});

describe('sameDistribution', () => {
    it('compares own key/value pairs independently of insertion order without mutating either input', () => {
        const left = Object.freeze({Technology: 0.4, Health: 0.6});
        const right = Object.freeze({Health: 0.6, Technology: 0.4});
        expect(sameDistribution(left, right)).toBe(true);
        expect(sameDistribution(right, left)).toBe(true);
        expect(Object.keys(left)).toEqual(['Technology', 'Health']);
        expect(Object.keys(right)).toEqual(['Health', 'Technology']);
    });

    it('treats omitted distributions as empty, but distinguishes missing keys from zero weights', () => {
        expect(sameDistribution()).toBe(true);
        expect(sameDistribution(undefined, {})).toBe(true);
        expect(sameDistribution({}, {Technology: 0})).toBe(false);
        expect(sameDistribution({Technology: 0}, {})).toBe(false);
    });

    it('rejects changed weights and changed keys even when cardinality and totals match', () => {
        expect(sameDistribution({Technology: 0.4, Health: 0.6}, {Technology: 0.6, Health: 0.4})).toBe(false);
        expect(sameDistribution({Technology: 1}, {Health: 1})).toBe(false);
        expect(sameDistribution({toString: 1}, {Technology: 1})).toBe(false);
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
        shortDescription: '',
        sectorDistribution: {},
        geographicDistribution: {},
        identifierRows: [],
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
    shortDescription: 'Consumer electronics',
    sectorDistribution: {Technology: 1},
    geographicDistribution: {USA: 1},
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
            classification_params: {
                short_description: 'Consumer electronics',
                sector_area: {distribution: {Technology: 1}},
                geographic_area: {distribution: {USA: 1}},
            },
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

    it('leaves out an empty user URL, an empty classification and every unset identifier column', () => {
        const item = buildCreateItem(form());
        expect(item.user_url).toBeUndefined();
        expect(item.classification_params).toBeUndefined();
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
        expect(buildPatchItem(42, form(FILLED), undefined)).toStrictEqual({
            asset_id: 42,
            display_name: 'Apple Inc.',
            currency: 'USD',
            asset_type: 'STOCK',
            icon_url: 'https://example.test/aapl.png',
            quote_base_quantity: 10,
            active: false,
            is_benchmark: true,
            user_url: 'https://example.test/quote/AAPL',
            classification_params: {
                short_description: 'Consumer electronics',
                sector_area: {distribution: {Technology: 1}},
                geographic_area: {distribution: {USA: 1}},
            },
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
        expect(buildPatchItem(1, form({iconUrl: null}), undefined).icon_url).toBeNull();
        expect(buildPatchItem(1, form({iconUrl: ''}), undefined).icon_url).toBe('');
    });

    it('trims the name and floors the quote base quantity, like the create item', () => {
        const item = buildPatchItem(1, form({displayName: '  Apple Inc.  ', quoteBaseQuantity: 0}), undefined);
        expect(item.display_name).toBe('Apple Inc.');
        expect(item.quote_base_quantity).toBe(1);
    });

    it('clears, with null, the user URL and the identifier columns the create item would leave out', () => {
        const item = buildPatchItem(1, form({userUrl: ''}), undefined);
        expect(item.user_url).toBeNull();
        expect([item.identifier_isin, item.identifier_ticker, item.identifier_cusip, item.identifier_sedol, item.identifier_figi, item.identifier_uuid, item.identifier_other]).toEqual(Array(7).fill(null));
    });

    describe('classification_params', () => {
        const initial: ClassificationParams = {short_description: 'Consumer electronics', sector_area: {distribution: {Technology: 1}}};

        it('is absent when the classification is the one the modal opened with', () => {
            expect(buildPatchItem(1, form({shortDescription: 'Consumer electronics', sectorDistribution: {Technology: 1}}), initial)).not.toHaveProperty('classification_params');
        });

        it('is absent when there was none and there is none', () => {
            expect(buildPatchItem(1, form(), undefined)).not.toHaveProperty('classification_params');
        });

        it('is null when everything was cleared', () => {
            expect(buildPatchItem(1, form(), initial)).toHaveProperty('classification_params', null);
        });

        it('carries only the parts that changed', () => {
            const item = buildPatchItem(1, form({shortDescription: 'Phones and computers', sectorDistribution: {Technology: 1}, geographicDistribution: {USA: 1}}), initial);
            expect(item).toHaveProperty('classification_params', {short_description: 'Phones and computers', geographic_area: {distribution: {USA: 1}}});
        });
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
