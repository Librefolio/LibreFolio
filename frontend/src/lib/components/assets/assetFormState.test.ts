/**
 * assetFormState — pure unit tests for the AssetModal form derivations.
 */
import {describe, expect, it} from 'vitest';
import {isQuoteBaseQuantityInvalid, quoteBaseQuantityErrorKey, shouldSeedBondQuoteBase, computeHasProvider, computeProviderDirty, groupImportNotices} from './assetFormState';

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

describe('shouldSeedBondQuoteBase', () => {
    it('seeds only a fresh, untouched BOND still at 1', () => {
        expect(shouldSeedBondQuoteBase('BOND', 1, false)).toBe(true);
    });

    it('does not seed a non-bond, an already-set base, or a user-touched field', () => {
        expect(shouldSeedBondQuoteBase('STOCK', 1, false)).toBe(false);
        expect(shouldSeedBondQuoteBase('BOND', 100, false)).toBe(false);
        expect(shouldSeedBondQuoteBase('BOND', 1, true)).toBe(false);
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
