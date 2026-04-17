/**
 * Sync Toast Helpers — Standardized toast messages for asset and FX sync operations.
 *
 * Provides consistent formatting across all sync callsites (asset detail, FX detail,
 * signal card sync). Uses inline SVG icons from Lucide for visual consistency with
 * the data editor tab icons (DollarSign for prices, CalendarClock for events).
 *
 * Toast messages use HTML (rendered via {@html} in ToastContainer).
 *
 * @module utils/syncToastHelpers
 */

import {getCurrencyInfo} from '$lib/stores/currencyStore';
import {fxProviderBadgeHtml, parseProviderChain} from '$lib/utils/providerHelpers';

// Inline SVG icons (from Lucide) — small enough to embed in toast HTML strings
const ICON_STYLE = 'display:inline-block;vertical-align:middle;margin-right:4px;width:14px;height:14px';

/** DollarSign icon SVG (matches data editor Prices tab) */
const dollarSignSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="${ICON_STYLE}"><line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`;

/** CalendarClock icon SVG (matches data editor Events tab) */
const calendarClockSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="${ICON_STYLE}"><path d="M21 7.5V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h3.5"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h5"/><path d="M17.5 17.5 16 16.3V14"/><circle cx="16" cy="16" r="6"/></svg>`;

/** ArrowLeftRight SVG (for FX pair display in toast) */
const arrowLrSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;margin:0 2px;width:10px;height:10px"><path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/></svg>`;

/**
 * Format FX pair slug as HTML with flags and ArrowLeftRight icon.
 * e.g. "EUR-USD" → "🇪🇺 EUR ↔ 🇺🇸 USD"
 */
function fxPairHtml(slug: string): string {
    const parts = slug.split('-');
    const base = parts[0] ?? slug;
    const quote = parts[1] ?? '';
    const baseFlag = getCurrencyInfo(base).flag_emoji;
    const quoteFlag = quote ? getCurrencyInfo(quote).flag_emoji : '';
    if (!quote) return `${baseFlag} ${base}`;
    return `${baseFlag} ${base} ${arrowLrSvg} ${quoteFlag} ${quote}`;
}

/**
 * Format FX provider chain as HTML badges (icons with fallback text).
 */
function fxProviderChainHtml(providerUsed: string | null | undefined): string {
    if (!providerUsed) return '';
    const chain = parseProviderChain(providerUsed);
    return chain.map((p) => fxProviderBadgeHtml(p)).join(' <span style="opacity:0.5">→</span> ');
}

export interface SyncToastResult {
    variant: 'success' | 'warning' | 'info' | 'error';
    message: string;
}

/**
 * Build a standardized toast for asset price sync results.
 *
 * @param result - Single result from sync_prices_bulk API response
 * @param label - Display label (e.g. translated "Sync prices" or asset name)
 * @returns Toast variant and HTML message
 */
export function buildAssetSyncToast(result: any, label: string): SyncToastResult {
    if (!result) {
        return {variant: 'error', message: `${label} — no response`};
    }

    const fetched = result.points_fetched ?? 0;
    const changed = result.points_changed ?? 0;
    const evtFetched = result.events_fetched ?? 0;
    const evtChanged = result.events_changed ?? 0;

    const priceLine = `${dollarSignSvg} ${fetched}↓ ${changed}Δ`;
    const eventLine = evtFetched > 0 ? `\n${calendarClockSvg} ${evtFetched}↓ ${evtChanged}Δ` : '';

    if (result.status === 'ok') {
        return {variant: 'success', message: `${label}:\n${priceLine}${eventLine}`};
    } else if (result.status === 'partial') {
        return {variant: 'warning', message: `${label} (partial):\n${priceLine}${eventLine}`};
    } else if (result.status === 'skipped') {
        return {variant: 'info', message: `${label} — skipped`};
    } else {
        return {variant: 'error', message: `${label} — ${result.message || 'failed'}`};
    }
}

/**
 * Build a standardized toast for FX sync results.
 * Uses HTML with flags, ArrowLeftRight icon, and provider badge icons.
 *
 * @param result - Single result from sync_rates API response
 * @param slug - FX pair slug (e.g. "EUR-USD")
 * @param tr - Translation function (from get(t))
 * @param _formatProvider - DEPRECATED (kept for API compat, ignored)
 * @param formatDetail - Optional function to format sync detail (for partial results)
 * @returns Toast variant and HTML message
 */
export function buildFxSyncToast(result: any, slug: string, tr: (key: string, opts?: any) => string, _formatProvider?: (p: any) => string, formatDetail?: (r: any, tr: (key: string, opts?: any) => string) => string): SyncToastResult {
    if (!result) {
        return {variant: 'error', message: `FX sync ${slug} — no response`};
    }

    const pairLabel = fxPairHtml(slug);
    const fetched = result.points_fetched ?? 0;
    const changed = result.points_changed ?? 0;
    const providerHtml = fxProviderChainHtml(result.provider_used);
    const dataLine = `${fetched}↓ ${changed}Δ`;

    if (result.status === 'ok') {
        return {
            variant: 'success',
            message: `Synced:\n${pairLabel}\n${dataLine}${providerHtml ? ' ' + providerHtml : ''}`,
        };
    } else if (result.status === 'partial') {
        let msg = `Partial:\n${pairLabel}\n${dataLine}${providerHtml ? ' ' + providerHtml : ''}`;
        if (formatDetail) msg += formatDetail(result, tr);
        return {variant: 'warning', message: msg};
    } else if (result.status === 'skipped') {
        return {variant: 'info', message: `Skipped:\n${pairLabel}\nmanual only`};
    } else {
        const errDetail = result.message ? ': ' + result.message : '';
        return {variant: 'error', message: `Failed:\n${pairLabel}${errDetail}`};
    }
}
