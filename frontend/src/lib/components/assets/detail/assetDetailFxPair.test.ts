/**
 * Contract tests for the FX pair the asset detail page offers to create, and for the currency it shows once
 * the pair exists (FE5c).
 *
 * Both functions replace a few lines of the page. Besides the contract, each case is checked against those
 * lines, copied here verbatim but for the names, so the move is proven equivalent on every input of the
 * tables, odd ones included.
 */
import {describe, expect, it} from 'vitest';
import {displayCurrencyAfterFxPairCreated, fxPairCreateDefaults} from './assetDetailFxPair';

/** The page's former `{@const}` lines of the «add FX pair» modal, verbatim but for the names. */
function formerCreateDefaults(fxPairCreateSlug: string, assetCurrency: string, displayCurrency: string): {base: string; quote: string} {
    const createParts = fxPairCreateSlug ? fxPairCreateSlug.split('-') : [];
    const createBase = createParts.length === 2 ? createParts[0] : assetCurrency;
    const createQuote = createParts.length === 2 ? createParts[1] : displayCurrency !== assetCurrency ? displayCurrency : '';
    return {base: createBase, quote: createQuote};
}

/** The page's former update of the shown currency once the pair exists, verbatim but for the names: `null` when it kept the current one. */
function formerDisplayCurrencyAfterCreated({base, quote}: {base: string; quote: string}, assetCurrency: string): string | null {
    let displayCurrency: string | null = null;
    const newQuote = assetCurrency === base ? quote : base;
    if (newQuote !== assetCurrency) {
        displayCurrency = newQuote;
    }
    return displayCurrency;
}

/** `[slug, asset currency, shown currency]`. */
const CREATE_CASES: Array<[string, string, string]> = [
    ['', 'USD', 'EUR'],
    ['', 'USD', 'USD'],
    ['', 'USD', ''],
    ['CHF-EUR', 'USD', 'EUR'],
    ['EUR-USD', 'USD', 'USD'],
    ['EUR', 'USD', 'EUR'],
    ['EUR-USD-GBP', 'USD', 'EUR'],
    ['-EUR', 'USD', 'EUR'],
    ['EUR-', 'USD', 'GBP'],
];

/** `[base, quote, asset currency]`. */
const CREATED_CASES: Array<[string, string, string]> = [
    ['USD', 'EUR', 'USD'],
    ['EUR', 'USD', 'USD'],
    ['USD', 'USD', 'USD'],
    ['CHF', 'EUR', 'USD'],
    ['', 'EUR', 'USD'],
    ['USD', '', 'USD'],
];

describe('fxPairCreateDefaults: both sides from a slug of exactly two parts, else the asset currency against the one shown', () => {
    it('takes both sides from a slug of two parts, whatever the asset and the shown currency', () => {
        expect(fxPairCreateDefaults('CHF-EUR', 'USD', 'GBP')).toEqual({base: 'CHF', quote: 'EUR'});
        expect(fxPairCreateDefaults('EUR-USD', 'USD', 'USD')).toEqual({base: 'EUR', quote: 'USD'});
    });

    it('starts from the asset currency against the shown one when there is no slug', () => {
        expect(fxPairCreateDefaults('', 'USD', 'EUR')).toEqual({base: 'USD', quote: 'EUR'});
    });

    it('leaves the quote empty when the shown currency is the asset’s own', () => {
        expect(fxPairCreateDefaults('', 'USD', 'USD')).toEqual({base: 'USD', quote: ''});
    });

    it.each(['EUR', 'EUR-USD-GBP'])('ignores the slug %j, which does not have two parts', (slug) => {
        expect(fxPairCreateDefaults(slug, 'USD', 'EUR')).toEqual({base: 'USD', quote: 'EUR'});
    });

    it.each(CREATE_CASES)('matches the page’s former lines for slug %j, asset %j, shown %j', (slug, assetCurrency, displayCurrency) => {
        expect(fxPairCreateDefaults(slug, assetCurrency, displayCurrency)).toEqual(formerCreateDefaults(slug, assetCurrency, displayCurrency));
    });
});

describe('displayCurrencyAfterFxPairCreated: the side of the new pair that is not the asset currency, or null to keep the shown one', () => {
    it('shows the quote of a pair based on the asset currency', () => {
        expect(displayCurrencyAfterFxPairCreated({base: 'USD', quote: 'EUR'}, 'USD')).toBe('EUR');
    });

    it('shows the base of a pair quoted in the asset currency', () => {
        expect(displayCurrencyAfterFxPairCreated({base: 'EUR', quote: 'USD'}, 'USD')).toBe('EUR');
    });

    it('keeps the shown currency when both sides are the asset’s own', () => {
        expect(displayCurrencyAfterFxPairCreated({base: 'USD', quote: 'USD'}, 'USD')).toBeNull();
    });

    it('shows the base of a pair without the asset currency, as the page did', () => {
        expect(displayCurrencyAfterFxPairCreated({base: 'CHF', quote: 'EUR'}, 'USD')).toBe('CHF');
    });

    it.each(CREATED_CASES)('matches the page’s former lines for base %j, quote %j, asset %j', (base, quote, assetCurrency) => {
        expect(displayCurrencyAfterFxPairCreated({base, quote}, assetCurrency)).toBe(formerDisplayCurrencyAfterCreated({base, quote}, assetCurrency));
    });
});
