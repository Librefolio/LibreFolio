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
 * Format a currency amount as plain text (no HTML).
 *
 * Output: `1,000.00 $ 🇺🇸 USD` or `1,000.00 🇺🇸 USD` (no symbol).
 * Suitable for tooltips, title attributes, plain-text contexts.
 */
export function formatCurrencyAmountPlain(amount: number, code: string, opts: CurrencyAmountFormatOptions = {}): string {
    const {showSign = false, minFraction = 2, maxFraction = 2} = opts;
    const info = getCurrencyInfo(code);
    const symbol = info.symbol ?? '';
    const hasRealSymbol = symbol !== '' && symbol !== code;
    const sign = showSign && amount > 0 ? '+' : '';
    const abs = Math.abs(amount).toLocaleString(undefined, {minimumFractionDigits: minFraction, maximumFractionDigits: maxFraction});
    const formatted = `${sign}${amount < 0 ? '-' : ''}${abs}`;
    const flag = info.flag_emoji && info.flag_emoji !== '🏳️' ? info.flag_emoji : '';
    const parts = [formatted];
    if (hasRealSymbol) parts.push(symbol);
    if (flag) parts.push(flag);
    parts.push(code);
    return parts.join(' ');
}

/**
 * Format a currency amount as HTML string: `amount symbol flag code`.
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
    const codeHtml = `<span class="currency-code">${escapeHtml(code)}</span>`;
    let suffixHtml: string;
    if (hasRealSymbol) {
        suffixHtml = `<span class="currency-symbol">${escapeHtml(symbol)}</span> ${flagHtml}${codeHtml}`;
    } else {
        suffixHtml = `${flagHtml}${codeHtml}`;
    }
    return `<span class="currency-amount">${escapeHtml(formatted)}</span> ${suffixHtml}`;
}
