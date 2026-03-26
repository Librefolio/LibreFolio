/**
 * Shared FX sync helpers — used by FxSyncModal, FxTable, fx/+page, fx/[pair]/+page.
 *
 * Centralises:
 *  - Provider chain parsing (CHAIN:ECB+BOE → ['ECB','BOE'])
 *  - Provider badge rendering (HTML for DataTable cells / Svelte innerHTML)
 *  - Per-leg breakdown text formatting (for toasts)
 *  - Provider text formatting for toasts (CHAIN:ECB+BOE → "ECB + BOE")
 */

import {getCachedProviders} from '$lib/stores/currencyGraphStore';

// =========================================================================
// Provider badge colours — shared constant
// =========================================================================

export const PROVIDER_COLORS: Record<string, string> = {
    ECB: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    FRANKFURTER: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400',
    FIXED_RATE: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
    MANUAL: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
};
export const DEFAULT_PROVIDER_COLOR = 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400';

// =========================================================================
// Provider chain parsing
// =========================================================================

/**
 * Parse a `provider_used` string into individual provider codes.
 * "CHAIN:ECB+BOE" → ['ECB', 'BOE']
 * "ECB"           → ['ECB']
 */
export function parseProviderChain(providerUsed: string | null | undefined): string[] {
    if (!providerUsed) return [];
    if (providerUsed.startsWith('CHAIN:')) {
        return providerUsed.slice(6).split('+');
    }
    return [providerUsed];
}

// =========================================================================
// Provider icon URL lookup
// =========================================================================

/** Get provider icon_url from the in-memory provider cache. */
export function getProviderIconUrl(code: string): string | null {
    const providers = getCachedProviders();
    return providers.find(p => p.code === code)?.icon_url ?? null;
}

// =========================================================================
// Provider badge HTML (for DataTable innerHTML / tooltip)
// =========================================================================

/** Build a single provider badge as an HTML string (icon or 2-char initials). */
export function providerBadgeHtml(providerCode: string): string {
    const providers = getCachedProviders();
    const info = providers.find(p => p.code === providerCode);
    const cls = PROVIDER_COLORS[providerCode] ?? DEFAULT_PROVIDER_COLOR;
    if (info?.icon_url) {
        return `<span class="inline-flex items-center px-1 py-0.5 rounded ${cls}" title="${providerCode}"><img src="${info.icon_url}" alt="${providerCode}" class="w-3.5 h-3.5 rounded-sm object-contain" onerror="this.parentElement.textContent='${providerCode.slice(0, 2)}'" /></span>`;
    }
    return `<span class="inline-flex items-center px-1 py-0.5 text-[9px] font-medium rounded ${cls}">${providerCode}</span>`;
}

// =========================================================================
// Provider text formatting (for toasts — plain text, no HTML)
// =========================================================================

/**
 * Format a `provider_used` string for text-only display (toasts).
 * "CHAIN:ECB+BOE" → "ECB + BOE"
 * "ECB"           → "ECB"
 */
export function formatProviderText(providerUsed: string | null | undefined): string {
    if (!providerUsed) return '?';
    const chain = parseProviderChain(providerUsed);
    return chain.join(' + ');
}

// =========================================================================
// Per-leg breakdown formatting (for toasts)
// =========================================================================

export interface LegDetail {
    provider: string;
    leg: string;
    dates_available: number;
    error?: string | null;
}

/**
 * Format per-leg detail from a sync response into a human-readable text string.
 * Uses the provided translation function for UI strings.
 *
 * @param r      - sync result item with optional `detail[]` and `message`
 * @param tr     - translation function `(key, opts?) => string`
 * @returns multi-line string to append to the toast message (starts with \n)
 */
export function formatSyncDetail(
    r: { detail?: LegDetail[] | null; message?: string | null },
    tr: (key: string, opts?: Record<string, unknown>) => string,
): string {
    if (!r.detail?.length) return r.message ? '\n' + r.message : '';
    let out = '\n── ' + tr('fx.sync.legBreakdown') + ' ──';
    for (const leg of r.detail) {
        if (leg.error) {
            out += `\n• ${leg.leg} (${leg.provider}): ❌ ${leg.error}`;
        } else if (leg.dates_available === 0) {
            out += `\n• ${leg.leg} (${leg.provider}): ${tr('fx.sync.legNoData')}`;
        } else {
            out += `\n• ${leg.leg} (${leg.provider}): ${leg.dates_available} ${tr('fx.sync.legDates')}`;
        }
    }
    return out;
}

