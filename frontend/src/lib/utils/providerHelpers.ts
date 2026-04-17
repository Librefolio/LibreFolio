/**
 * Provider helpers — shared by FX and Asset sync/table components.
 *
 * Structure:
 *  1. Shared (colours, chain parsing)
 *  2. FX Provider (icon lookup from currencyGraphStore, badge HTML)
 *  3. Asset Provider (lazy cache from API, icon lookup, badge HTML)
 *  4. FX-specific formatting (toast text, per-leg breakdown)
 */

import {getCachedFxProviders} from '$lib/stores/currencyGraphStore';
import {zodiosApi} from '$lib/api';
import {writable} from 'svelte/store';

// =========================================================================
// 1. SHARED — colours, chain parsing
// =========================================================================

export const PROVIDER_COLORS: Record<string, string> = {
    ECB: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    FRANKFURTER: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400',
    FIXED_RATE: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
    MANUAL: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
};
export const DEFAULT_PROVIDER_COLOR = 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400';

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
// 2. FX PROVIDER — icon from currencyGraphStore cache, badge HTML
// =========================================================================

/** Get FX provider icon_url from the FX provider cache (currencyGraphStore). */
export function getFxProviderIconUrl(code: string): string | null {
    const fxProviders = getCachedFxProviders();
    return fxProviders.find((p) => p.code === code)?.icon_url ?? null;
}

/** Build a single FX provider badge as HTML (icon or 2-char initials). */
export function fxProviderBadgeHtml(providerCode: string): string {
    const providers = getCachedFxProviders();
    const info = providers.find((p) => p.code === providerCode);
    const cls = PROVIDER_COLORS[providerCode] ?? DEFAULT_PROVIDER_COLOR;
    if (info?.icon_url) {
        return `<span class="inline-flex items-center px-1 py-0.5 rounded ${cls}" title="${providerCode}"><img src="${info.icon_url}" alt="${providerCode}" class="w-3.5 h-3.5 rounded-sm object-contain" onerror="this.parentElement.textContent='${providerCode.slice(0, 2)}'" /></span>`;
    }
    return `<span class="inline-flex items-center px-1 py-0.5 text-[9px] font-medium rounded ${cls}">${providerCode}</span>`;
}

// =========================================================================
// 3. ASSET PROVIDER — lazy cache from API, icon, badge HTML
// =========================================================================

/**
 * In-memory cache for asset provider icons.
 * Populated lazily via ensureAssetProvidersCached().
 * Kept separate from FX providers to avoid registry key collisions.
 */
let assetProviderIcons: Map<string, string | null> = new Map();
let assetProviderNames: Map<string, string> = new Map();
let assetProvidersFetched = false;
let assetProvidersFetchPromise: Promise<void> | null = null;

/**
 * Reactive version counter — incremented when asset providers are cached.
 * Subscribe in Svelte components to trigger re-evaluation when provider icons load.
 */
export const assetProvidersVersion = writable(0);

/**
 * Ensure asset provider info is cached (lazy, one-shot).
 * Safe to call multiple times — deduplicates concurrent calls.
 */
export async function ensureAssetProvidersCached(): Promise<void> {
    if (assetProvidersFetched) return;
    if (assetProvidersFetchPromise) return assetProvidersFetchPromise;
    assetProvidersFetchPromise = (async () => {
        try {
            const providers = await zodiosApi.list_providers_api_v1_assets_provider_get();
            for (const p of providers as any[]) {
                assetProviderIcons.set(p.code, p.icon_url ?? null);
                assetProviderNames.set(p.code, p.name ?? p.code);
            }
        } catch {
            // Fail silently — icon lookup will just return null
        } finally {
            assetProvidersFetched = true;
            assetProvidersFetchPromise = null;
            assetProvidersVersion.update((v) => v + 1);
        }
    })();
    return assetProvidersFetchPromise;
}

/** Get asset provider icon_url from the asset provider cache. */
export function getAssetProviderIconUrl(code: string): string | null {
    return assetProviderIcons.get(code) ?? null;
}

/** Get asset provider display name from the asset provider cache. */
export function getAssetProviderName(code: string): string {
    return assetProviderNames.get(code) ?? code;
}

/** Build an asset provider badge as HTML (icon + name). */
export function assetProviderBadgeHtml(providerCode: string): string {
    const iconUrl = assetProviderIcons.get(providerCode);
    const name = assetProviderNames.get(providerCode) ?? providerCode;
    const cls = PROVIDER_COLORS[providerCode] ?? DEFAULT_PROVIDER_COLOR;
    if (iconUrl) {
        return `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${cls}" title="${providerCode}"><img src="${iconUrl}" alt="${providerCode}" class="w-3.5 h-3.5 rounded-sm object-contain" onerror="this.style.display='none'" /><span class="text-[10px] font-medium">${name}</span></span>`;
    }
    return `<span class="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded ${cls}">${name}</span>`;
}

// =========================================================================
// 4. FX-SPECIFIC — text formatting for toasts, per-leg breakdown
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

export interface LegDetail {
    provider: string;
    leg: string;
    dates_available: number;
    error?: string | null;
}

/**
 * Format per-leg detail from a sync response into a human-readable text string.
 * Uses the provided translation function for UI strings.
 */
export function formatSyncDetail(r: {detail?: LegDetail[] | null; message?: string | null}, tr: (key: string, opts?: Record<string, unknown>) => string): string {
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
