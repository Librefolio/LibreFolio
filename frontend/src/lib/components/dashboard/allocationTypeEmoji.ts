/**
 * Emoji for the Type dimension of the allocation history chart.
 *
 * The engine groups holdings by their raw `asset_type` value, so any `AssetType` value
 * can arrive here, plus two synthetic buckets: `Liquidity` (cash) and `Unknown` (an
 * asset without a type). Every one of them has an explicit entry.
 *
 * An unmapped value gets no emoji rather than a borrowed one. The previous fallback was
 * the ETF emoji, which drew COMMODITY, REAL_ESTATE and Unknown as if they were ETFs.
 *
 * @module components/dashboard/allocationTypeEmoji
 */

const ETF_EMOJI = '📊';
const CROWDFUND_EMOJI = '🤝';

export const ASSET_TYPE_EMOJI: Readonly<Record<string, string>> = {
    STOCK: '📈',
    ETF: ETF_EMOJI,
    BOND: '🏛️',
    // Bitcoin sign (₿, U+20BF) is a currency symbol, not an emoji — it renders as a
    // thin system-font glyph (no color-emoji font coverage), making it nearly invisible
    // against the chart's pale area fill. 🪙 is a genuine color emoji with the same
    // bold visual weight as the rest.
    CRYPTO: '🪙',
    FUND: '💼',
    HOLD: '⏸️',
    CROWDFUND: CROWDFUND_EMOJI,
    COMMODITY: '🛢️',
    REAL_ESTATE: '🏠',
    INDEX: '📉',
    OTHER: '📦',
    // A subtype shares the emoji of its family (ETF, CROWDFUND): the emoji says what the
    // instrument is, the label says what it holds.
    ETF_STOCK: ETF_EMOJI,
    ETF_BOND: ETF_EMOJI,
    ETF_COMMODITY: ETF_EMOJI,
    ETF_REAL_ESTATE: ETF_EMOJI,
    ETF_CRYPTO: ETF_EMOJI,
    ETF_MONETARY: ETF_EMOJI,
    CROWDFUND_REAL_ESTATE: CROWDFUND_EMOJI,
    LIQUIDITY: '💰',
    // Same glyph as an unknown sector, so "unknown" reads the same in both dimensions.
    UNKNOWN: '❓',
};

/** Emoji for a Type bucket name, case-insensitive; `''` when the value is not mapped. */
export function getAssetTypeEmoji(rawName: string): string {
    return ASSET_TYPE_EMOJI[rawName.toUpperCase()] ?? '';
}
