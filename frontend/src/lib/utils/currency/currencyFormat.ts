/**
 * Currency Format Helpers — Shared formatting for currency amounts across pages.
 *
 * Used by: TransactionsTable (cash cell), AssetTable (lastPrice cell), FxTable.
 *
 * The number is written in the interface locale (`uiLocale()`, M-18) unless a
 * `locale` is passed: `14.788,01 € 🇪🇺 EUR` under an Italian interface, never
 * the browser's own format.
 *
 * @module utils/currencyFormat
 */

import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {maskable, type AmountSensitivity} from '$lib/utils/privacy/maskable';
import {uiLocale} from '$lib/stores/app/uiLocale';

/**
 * Escape a string for safe inclusion in an HTML attribute / text node.
 */
export interface CurrencyAmountFormatOptions {
    /** Show +/- sign prefix (default: false) */
    showSign?: boolean;
    /** Minimum fraction digits (default: 2) */
    minFraction?: number;
    /** Maximum fraction digits (default: 2) */
    maxFraction?: number;
    /** Omitted ⇒ treated as personal money ⇒ masked while privacy is on. */
    sensitivity?: AmountSensitivity;
    /** The locale the number is written in (default: the interface locale, `uiLocale()`). */
    locale?: string;
}

/**
 * Format a currency amount as plain text (no HTML).
 *
 * Output: `1,000.00 $ 🇺🇸 USD` or `1,000.00 🇺🇸 USD` (no symbol).
 * Suitable for tooltips, title attributes, plain-text contexts.
 */
export function formatCurrencyAmountPlain(amount: number, code: string, opts: CurrencyAmountFormatOptions = {}): string {
    const {showSign = false, minFraction = 2, maxFraction = 2, sensitivity, locale = uiLocale()} = opts;
    const info = getCurrencyInfo(code);
    const symbol = info.symbol ?? '';
    const hasRealSymbol = symbol !== '' && symbol !== code;
    const sign = showSign && amount > 0 ? '+' : '';
    const abs = Math.abs(amount).toLocaleString(locale, {minimumFractionDigits: minFraction, maximumFractionDigits: maxFraction});
    // D8: the sign stays outside the mask on purpose. See `maskable` for what it costs.
    const formatted = `${sign}${amount < 0 ? '-' : ''}${maskable(abs, sensitivity)}`;
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
    const {showSign = false, minFraction = 2, maxFraction = 2, sensitivity, locale = uiLocale()} = opts;
    const info = getCurrencyInfo(code);
    const symbol = info.symbol ?? '';
    const hasRealSymbol = symbol !== '' && symbol !== code;
    const sign = showSign && amount > 0 ? '+' : '';
    const abs = Math.abs(amount).toLocaleString(locale, {minimumFractionDigits: minFraction, maximumFractionDigits: maxFraction});
    // D8: the sign stays outside the mask on purpose. See `maskable` for what it costs.
    const formatted = `${sign}${amount < 0 ? '-' : ''}${maskable(abs, sensitivity)}`;
    const flagHtml = info.flag_emoji && info.flag_emoji !== '🏳️' ? `<span class="emoji-flag">${info.flag_emoji}</span>` : '';
    const codeHtml = `<span class="currency-code">${escapeHtml(code)}</span>`;
    let suffixHtml: string;
    if (hasRealSymbol) {
        suffixHtml = `<span class="currency-symbol">${escapeHtml(symbol)}</span> ${flagHtml} ${codeHtml}`;
    } else {
        suffixHtml = `${flagHtml} ${codeHtml}`;
    }
    return `<span class="currency-amount">${escapeHtml(formatted)}</span> ${suffixHtml}`;
}

/**
 * Format ONLY the currency identifier (no amount): `symbol flag code` —
 * e.g. `$ 🇺🇸 USD`. Used in filter UIs / labels where we need the rich
 * "valuta" representation without an associated amount.
 */
export function formatCurrencyCodeHtml(code: string): string {
    const info = getCurrencyInfo(code);
    const symbol = info.symbol ?? '';
    const hasRealSymbol = symbol !== '' && symbol !== code;
    const flagHtml = info.flag_emoji && info.flag_emoji !== '🏳️' ? `<span class="emoji-flag">${info.flag_emoji}</span>` : '';
    const codeHtml = `<span class="currency-code">${escapeHtml(code)}</span>`;
    if (hasRealSymbol) {
        return `<span class="currency-symbol">${escapeHtml(symbol)}</span> ${flagHtml} ${codeHtml}`;
    }
    return `${flagHtml} ${codeHtml}`;
}

/**
 * The two forms of a currency pair: `conversion` (`→`: something is converted from one currency to the other — an amount, the
 * rate a conversion used, the Yield on Cost, an import) and `pair` (`/`: the forex pair in itself — the banners of a missing or
 * old rate, a list of pairs). The default is `pair`.
 */
export type CurrencyPairForm = 'pair' | 'conversion';

const pairSeparator = (form: CurrencyPairForm): string => (form === 'conversion' ? '→' : '/');

/**
 * A currency pair, in the direction of the conversion, as HTML: `$ 🇺🇸 USD / EUR 🇪🇺 €` (form `pair`) or `$ 🇺🇸 USD → EUR 🇪🇺 €`
 * (form `conversion`) for USD → EUR.
 *
 * The currency a conversion starts from is written as `formatCurrencyCodeHtml` writes it (symbol, flag, code); the one it
 * arrives in is its mirror (code, flag, symbol), so the two read as one line pointing from left to right. A currency with no
 * symbol of its own (the symbol is its code) leaves the symbol out on its side. The flag stays in `.emoji-flag`.
 * `EUR → USD` is `€ 🇪🇺 EUR / USD 🇺🇸 $`: the order is the direction, never alphabetical.
 */
export function formatCurrencyPairHtml(from: string, to: string, form: CurrencyPairForm = 'pair'): string {
    const arrival = currencyParts(to);
    const arrivalHtml = [`<span class="currency-code">${escapeHtml(to)}</span>`, arrival.flag ? `<span class="emoji-flag">${arrival.flag}</span>` : '', arrival.symbol ? `<span class="currency-symbol">${escapeHtml(arrival.symbol)}</span>` : ''].filter(Boolean).join(' ');
    return `${formatCurrencyCodeHtml(from).trim()} ${pairSeparator(form)} ${arrivalHtml}`;
}

/** `formatCurrencyPairHtml` as plain text (tooltips, titles): `$ 🇺🇸 USD / EUR 🇪🇺 €`, or with `→` for a `conversion`. */
export function formatCurrencyPairPlain(from: string, to: string, form: CurrencyPairForm = 'pair'): string {
    const start = currencyParts(from);
    const arrival = currencyParts(to);
    return `${[start.symbol, start.flag, from].filter(Boolean).join(' ')} ${pairSeparator(form)} ${[to, arrival.flag, arrival.symbol].filter(Boolean).join(' ')}`;
}

/** The pair of a `FROM/TO` slug (`USD/EUR`, also `USD-EUR`), as `formatCurrencyPairHtml`; the text itself, escaped, when it is no pair. */
export function formatPairSlugHtml(slug: string, form: CurrencyPairForm = 'pair'): string {
    const codes = slugCodes(slug);
    return codes ? formatCurrencyPairHtml(codes[0], codes[1], form) : escapeHtml(slug);
}

/** `formatPairSlugHtml` as plain text. */
export function formatPairSlugPlain(slug: string, form: CurrencyPairForm = 'pair'): string {
    const codes = slugCodes(slug);
    return codes ? formatCurrencyPairPlain(codes[0], codes[1], form) : slug;
}

function slugCodes(slug: string): [string, string] | null {
    const parts = slug.includes('/') ? slug.split('/') : slug.split('-');
    const [from, to] = [parts[0]?.trim().toUpperCase(), parts[1]?.trim().toUpperCase()];
    return from && to && parts.length === 2 ? [from, to] : null;
}

/** The symbol (none when it is the code itself) and the flag (none for the white flag) of a currency. */
function currencyParts(code: string): {symbol: string; flag: string} {
    const info = getCurrencyInfo(code);
    const symbol = info.symbol ?? '';
    return {symbol: symbol !== '' && symbol !== code ? symbol : '', flag: info.flag_emoji && info.flag_emoji !== '🏳️' ? info.flag_emoji : ''};
}
