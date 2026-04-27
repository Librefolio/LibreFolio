/**
 * Currency Format Helpers — Shared formatting for currency amounts across pages.
 *
 * Used by: TransactionsTable (cash cell), AssetTable (lastPrice cell), FxTable.
 *
 * @module utils/currencyFormat
 */

import {getCurrencyInfo} from '$lib/stores/currencyStore';

/**
 * Escape a string for safe inclusion in an HTML attribute / text node.
 */
function escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

export interface CurrencyAmountFormatOptions {
    /** Show +/- sign prefix (default: false) */
    showSign?: boolean;
    /** Minimum fraction digits (default: 2) */
    minFraction?: number;
    /** Maximum fraction digits (default: 2) */
    maxFraction?: number;
}

/**
 * Format a currency amount as HTML string: `amount symbol flag` or `amount flag code`.
 *
 * Rules:
 * - If symbol exists and differs from code → show `amount symbol flag` (no code)
 * - Otherwise → show `amount flag code` (no duplication)
 * - White flag 🏳️ (fallback) is omitted
 *
 * @returns HTML string ready for HtmlCell rendering
 */
export function formatCurrencyAmountHtml(amount: number, code: string, opts: CurrencyAmountFormatOptions = {}): string {
    const {showSign = false, minFraction = 2, maxFraction = 2} = opts;
    const info = getCurrencyInfo(code);
    const symbol = info.symbol ?? '';
    const hasRealSymbol = symbol !== '' && symbol !== code;
    const sign = showSign && amount > 0 ? '+' : '';
    const abs = Math.abs(amount).toLocaleString(undefined, {minimumFractionDigits: minFraction, maximumFractionDigits: maxFraction});
    const formatted = `${sign}${amount < 0 ? '-' : ''}${abs}`;
    const flagHtml = info.flag_emoji && info.flag_emoji !== '🏳️' ? `<span class="emoji-flag">${info.flag_emoji}</span>` : '';
    let suffixHtml: string;
    if (hasRealSymbol) {
        suffixHtml = `<span class="currency-symbol">${escapeHtml(symbol)}</span> ${flagHtml}`;
    } else {
        suffixHtml = `${flagHtml}<span class="currency-code">${escapeHtml(code)}</span>`;
    }
    return `<span class="currency-amount">${escapeHtml(formatted)}</span> ${suffixHtml}`;
}
