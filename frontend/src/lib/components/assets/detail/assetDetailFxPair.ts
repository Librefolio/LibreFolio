/**
 * The FX pair the asset detail page offers to create, and what creating it changes on the page.
 *
 * The page opens the «add FX pair» modal in two ways:
 * - from the warning that the asset's currency cannot be converted to the one shown: the pair is
 *   the asset's currency against the one shown, and the page fixes its base;
 * - for one specific pair (`slug`, `BASE-QUOTE`), such as a comparison peer's: both sides come
 *   from the slug.
 *
 * @module components/assets/detail/assetDetailFxPair
 */

/** The sides the «add FX pair» modal starts with. */
export interface FxPairCreateDefaults {
    base: string;
    quote: string;
}

/**
 * The sides the modal starts with.
 *
 * - A `slug` of exactly two parts gives both sides.
 * - Otherwise the base is the asset's currency, and the quote is the currency shown, or empty when
 *   it is the asset's own.
 */
export function fxPairCreateDefaults(slug: string, assetCurrency: string, displayCurrency: string): FxPairCreateDefaults {
    const parts = slug ? slug.split('-') : [];
    if (parts.length === 2) return {base: parts[0], quote: parts[1]};
    return {base: assetCurrency, quote: displayCurrency !== assetCurrency ? displayCurrency : ''};
}

/**
 * The currency to show once the pair `base`/`quote` of the asset's own currency exists: its other
 * side, or `null` to keep the current one, when that side is the asset's currency too.
 */
export function displayCurrencyAfterFxPairCreated(pair: {base: string; quote: string}, assetCurrency: string): string | null {
    const otherSide = assetCurrency === pair.base ? pair.quote : pair.base;
    return otherSide !== assetCurrency ? otherSide : null;
}
