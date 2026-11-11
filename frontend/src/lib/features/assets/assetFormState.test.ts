/**
 * assetFormState — pure unit tests for the AssetModal form derivations.
 *
 * The quote base ladder (Z-32 d) replaces the bond seed (`shouldSeedBondQuoteBase`): the plugin's explicit suggestion
 * for the line, else the asset type's default — 100 for a BOND, 1 for every other type — and the note that says where
 * the proposal comes from, as an i18n key with its values (never the text). RED until the three functions and the
 * defaults table exist: today the imports below are undefined and each case throws «is not a function».
 */
import {describe, expect, it} from 'vitest';
import {ASSET_TYPES} from '$lib/utils/assetTypes';
import {isQuoteBaseQuantityInvalid, quoteBaseQuantityErrorKey, QUOTE_BASE_TYPE_DEFAULTS, defaultQuoteBaseQuantity, proposeQuoteBase, quoteBaseNote, type QuoteBaseSource, computeHasProvider, computeProviderDirty, groupImportNotices} from './assetFormState';

describe('isQuoteBaseQuantityInvalid', () => {
    it('accepts a positive integer', () => {
        expect(isQuoteBaseQuantityInvalid(1)).toBe(false);
        expect(isQuoteBaseQuantityInvalid(100)).toBe(false);
    });

    it('rejects non-finite, sub-1 and fractional values', () => {
        expect(isQuoteBaseQuantityInvalid(NaN)).toBe(true);
        expect(isQuoteBaseQuantityInvalid(Infinity)).toBe(true);
        expect(isQuoteBaseQuantityInvalid(0)).toBe(true);
        expect(isQuoteBaseQuantityInvalid(-3)).toBe(true);
        expect(isQuoteBaseQuantityInvalid(1.5)).toBe(true);
    });
});

describe('quoteBaseQuantityErrorKey', () => {
    it('returns the min message for non-finite or sub-1 values', () => {
        expect(quoteBaseQuantityErrorKey(0)).toBe('assets.modal.quoteBaseMin');
        expect(quoteBaseQuantityErrorKey(-1)).toBe('assets.modal.quoteBaseMin');
        expect(quoteBaseQuantityErrorKey(NaN)).toBe('assets.modal.quoteBaseMin');
    });

    it('returns the integer message for a finite ≥1 non-integer', () => {
        expect(quoteBaseQuantityErrorKey(2.5)).toBe('assets.modal.quoteBaseInteger');
    });
});

// =========================================================================
// The quote base ladder (Z-32 d) — replaces the bond seed. RED: none of these exports exists yet.
// =========================================================================

describe('QUOTE_BASE_TYPE_DEFAULTS', () => {
    it('lists the one type not quoted per unit: a BOND, per 100 nominal', () => {
        expect(QUOTE_BASE_TYPE_DEFAULTS).toEqual({BOND: 100});
    });
});

describe('defaultQuoteBaseQuantity', () => {
    it('is 100 for a BOND, whatever the case of its code', () => {
        expect(defaultQuoteBaseQuantity('BOND')).toBe(100);
        expect(defaultQuoteBaseQuantity('bond')).toBe(100);
        expect(defaultQuoteBaseQuantity('Bond')).toBe(100);
    });

    it('is 1 for every other asset type — a bond ETF included, which is quoted per share', () => {
        const others = ASSET_TYPES.filter((type) => type !== 'BOND');
        // Premise: the enum still holds BOND and the neighbours this case is about.
        expect(ASSET_TYPES).toContain('BOND');
        expect(others).toEqual(expect.arrayContaining(['STOCK', 'ETF', 'ETF_BOND', 'FUND', 'CRYPTO', 'OTHER']));
        expect(Object.fromEntries(others.map((type) => [type, defaultQuoteBaseQuantity(type)]))).toEqual(Object.fromEntries(others.map((type) => [type, 1])));
    });

    it('is 1 for an empty or unknown type', () => {
        expect(defaultQuoteBaseQuantity('')).toBe(1);
        expect(defaultQuoteBaseQuantity('NOT_A_TYPE')).toBe(1);
    });
});

describe('proposeQuoteBase', () => {
    it('takes the plugin’s suggestion — a whole number of 1 or more — with its quote currency as the provider wrote it', () => {
        expect(proposeQuoteBase({quantity: 100, quote_currency: 'GBp'}, 'STOCK')).toEqual({kind: 'suggestion', quantity: 100, quoteCurrency: 'GBp'});
    });

    it('reads a missing or null quote currency as null', () => {
        expect(proposeQuoteBase({quantity: 10}, 'STOCK')).toEqual({kind: 'suggestion', quantity: 10, quoteCurrency: null});
        expect(proposeQuoteBase({quantity: 10, quote_currency: null}, 'STOCK')).toEqual({kind: 'suggestion', quantity: 10, quoteCurrency: null});
    });

    it('lets a suggestion win over the type: 1 for a BOND is a suggestion too, and so is 1000', () => {
        expect(proposeQuoteBase({quantity: 1}, 'BOND')).toEqual({kind: 'suggestion', quantity: 1, quoteCurrency: null});
        expect(proposeQuoteBase({quantity: 1000, quote_currency: 'EUR'}, 'BOND')).toEqual({kind: 'suggestion', quantity: 1000, quoteCurrency: 'EUR'});
    });

    it('without a suggestion, proposes the type’s default and names the type', () => {
        expect(proposeQuoteBase(null, 'BOND')).toEqual({kind: 'typeDefault', assetType: 'BOND', quantity: 100});
        expect(proposeQuoteBase(undefined, 'STOCK')).toEqual({kind: 'typeDefault', assetType: 'STOCK', quantity: 1});
    });

    it.each<{label: string; suggestion: unknown}>([
        {label: 'zero', suggestion: {quantity: 0}},
        {label: 'negative', suggestion: {quantity: -100}},
        {label: 'fractional', suggestion: {quantity: 2.5}},
        {label: 'NaN', suggestion: {quantity: Number.NaN}},
        {label: 'infinite', suggestion: {quantity: Number.POSITIVE_INFINITY}},
        {label: 'a numeric string', suggestion: {quantity: '100', quote_currency: 'GBp'}},
        {label: 'null', suggestion: {quantity: null}},
        {label: 'missing', suggestion: {quote_currency: 'GBp'}},
    ])('counts a suggestion whose quantity is $label as none: the type’s default', ({suggestion}) => {
        // The backend validates the suggestion; the form does not trust that to keep a division by zero out of a price.
        expect(proposeQuoteBase(suggestion as never, 'BOND')).toEqual({kind: 'typeDefault', assetType: 'BOND', quantity: 100});
        expect(proposeQuoteBase(suggestion as never, 'STOCK')).toEqual({kind: 'typeDefault', assetType: 'STOCK', quantity: 1});
    });
});

describe('quoteBaseNote', () => {
    const suggestion = (quantity: number, quoteCurrency: string | null): QuoteBaseSource => ({kind: 'suggestion', quantity, quoteCurrency});
    const typeDefault = (assetType: string, quantity: number): QuoteBaseSource => ({kind: 'typeDefault', assetType, quantity});

    it('names the provider, the quote currency and the quantity of a suggestion that has a currency', () => {
        expect(quoteBaseNote(suggestion(100, 'GBp'), 'Yahoo Finance')).toEqual({key: 'assets.modal.quoteBaseSuggested', values: {provider: 'Yahoo Finance', currency: 'GBp', quantity: 100}});
    });

    it('takes the plain message, with no currency among its values, for a suggestion without one', () => {
        expect(quoteBaseNote(suggestion(10, null), 'Owned source')).toEqual({key: 'assets.modal.quoteBaseSuggestedPlain', values: {provider: 'Owned source', quantity: 10}});
    });

    it('gives a BOND’s default the bond hint, which has no values', () => {
        expect(quoteBaseNote(typeDefault('BOND', 100), 'Owned source')).toEqual({key: 'assets.modal.bondQuoteBaseHint', values: {}});
    });

    it.each([{type: 'STOCK'}, {type: 'ETF'}, {type: 'ETF_BOND'}, {type: 'FUND'}, {type: ''}])('says nothing about the default of «$type»', ({type}) => {
        expect(quoteBaseNote(typeDefault(type, 1), 'Owned source')).toBeNull();
    });
});

describe('computeHasProvider', () => {
    it('is false when the provider is explicitly removed', () => {
        expect(computeHasProvider(true, 'yahoo', 'AAPL', 'TICKER')).toBe(false);
    });

    it('is false when there is no provider code', () => {
        expect(computeHasProvider(false, '', 'AAPL', 'TICKER')).toBe(false);
    });

    it('needs an identifier unless the type is AUTO_GENERATED', () => {
        expect(computeHasProvider(false, 'yahoo', '', 'TICKER')).toBe(false);
        expect(computeHasProvider(false, 'yahoo', '', 'AUTO_GENERATED')).toBe(true);
        expect(computeHasProvider(false, 'yahoo', 'AAPL', 'TICKER')).toBe(true);
    });
});

describe('computeProviderDirty', () => {
    const initial = {code: 'yahoo', identifier: 'AAPL', identifierType: 'TICKER'};

    it('in create mode equals hasProvider (no snapshot)', () => {
        expect(computeProviderDirty(false, true, {code: '', identifier: '', identifierType: '', params: null}, '', initial)).toBe(true);
        expect(computeProviderDirty(false, false, {code: '', identifier: '', identifierType: '', params: null}, '', initial)).toBe(false);
    });

    it('in edit mode is false when nothing changed', () => {
        const cur = {...initial, params: {a: 1}};
        expect(computeProviderDirty(true, true, cur, JSON.stringify({a: 1}), initial)).toBe(false);
    });

    it('in edit mode detects each field change', () => {
        expect(computeProviderDirty(true, true, {...initial, code: 'justetf', params: null}, 'null', initial)).toBe(true);
        expect(computeProviderDirty(true, true, {...initial, identifier: 'MSFT', params: null}, 'null', initial)).toBe(true);
        expect(computeProviderDirty(true, true, {...initial, identifierType: 'ISIN', params: null}, 'null', initial)).toBe(true);
    });

    it('in edit mode detects a params change via canonical JSON', () => {
        expect(computeProviderDirty(true, true, {...initial, params: {a: 2}}, JSON.stringify({a: 1}), initial)).toBe(true);
    });

    it('treats an absent initial params snapshot as the string "null"', () => {
        // current params null → JSON 'null'; empty initial snapshot → 'null' → equal → not dirty.
        expect(computeProviderDirty(true, true, {...initial, params: null}, '', initial)).toBe(false);
    });
});

describe('groupImportNotices', () => {
    it('returns [] for null/undefined/empty input', () => {
        expect(groupImportNotices(null)).toEqual([]);
        expect(groupImportNotices(undefined)).toEqual([]);
        expect(groupImportNotices([])).toEqual([]);
    });

    it('drops null notices and notices without a reason', () => {
        expect(groupImportNotices([null, {kind: 'x'}, {kind: 'x', reason: ''}])).toEqual([]);
    });

    it('buckets by kind and defaults a missing kind to generic', () => {
        const out = groupImportNotices([{reason: 'r1'}, {kind: 'fx', reason: 'r2'}]);
        expect(out).toEqual([
            {kind: 'generic', reasons: ['r1']},
            {kind: 'fx', reasons: ['r2']},
        ]);
    });

    it('dedupes identical reasons within a kind, preserving order', () => {
        const out = groupImportNotices([
            {kind: 'fx', reason: 'a'},
            {kind: 'fx', reason: 'a'},
            {kind: 'fx', reason: 'b'},
        ]);
        expect(out).toEqual([{kind: 'fx', reasons: ['a', 'b']}]);
    });
});
