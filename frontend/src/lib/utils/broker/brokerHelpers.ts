/**
 * Broker Helpers — Shared utility functions for broker icon resolution.
 *
 * Priority for all icon lookups (matches `brokerIconChain.svelte.ts`):
 *  1. icon_url — explicitly uploaded by the user (most reliable)
 *  2. portal_url → origin + `/favicon.ico` (external heuristic)
 *  3. default_import_plugin → cached plugin icon (app-hosted, async)
 *
 * For reactive multi-URL fallback with load-error retry, use
 * `createBrokerIconChain` from `brokerIconChain.svelte.ts`.
 *
 * @module utils/brokerHelpers
 */

import type {BrokerLike} from './brokerColors';
import {zodiosApi} from '$lib/api';

/** Minimal shape for broker icon resolution (subset of BrokerLike). */
export interface BrokerIconSource {
    icon_url?: string | null;
    portal_url?: string | null;
    default_import_plugin?: string | null;
}

// ============================================================================
// Plugin icon cache — loaded lazily on first need, shared for the session.
// ============================================================================

let _pluginIconCache: Map<string, string> | null = null;
let _pluginIconLoading: Promise<void> | null = null;

/** Ensure plugin icon cache is populated. Safe to call multiple times. */
export async function ensurePluginIconsLoaded(): Promise<void> {
    if (_pluginIconCache) return;
    if (_pluginIconLoading) return _pluginIconLoading;
    _pluginIconLoading = (async () => {
        try {
            const plugins = await zodiosApi.list_plugins_api_v1_brokers_import_plugins_get();
            _pluginIconCache = new Map();
            for (const p of plugins) {
                const rawIcon = p?.icon_url as string | null | undefined;
                if (rawIcon && p.code) _pluginIconCache.set(p.code, rawIcon);
            }
        } catch {
            _pluginIconCache = new Map(); // don't retry on error
        } finally {
            _pluginIconLoading = null;
        }
    })();
    return _pluginIconLoading;
}

/**
 * Sync lookup — returns the cached plugin icon URL or null.
 * Returns null if the plugin icon cache has not been loaded yet;
 * call `ensurePluginIconsLoaded()` first to populate it.
 */
export function getPluginIconUrl(pluginCode: string | null | undefined): string | null {
    if (!pluginCode || !_pluginIconCache) return null;
    return _pluginIconCache.get(pluginCode) ?? null;
}

/**
 * Build the ordered list of candidate icon URLs for a broker.
 * Priority matches the reactive chain in `brokerIconChain.svelte.ts`:
 *   1. icon_url (custom, most reliable)
 *   2. portal_url/favicon.ico (external heuristic)
 *   3. default_import_plugin → cached plugin icon (app-hosted, async-loaded)
 *
 * For non-reactive contexts (inline HTML renderers). For full fallback
 * chain with load-error retry use `createBrokerIconChain` in components.
 */
export function getBrokerIconCandidates(broker: BrokerIconSource | null | undefined): string[] {
    if (!broker) return [];
    const urls: string[] = [];
    if (broker.icon_url?.trim()) urls.push(broker.icon_url);
    if (broker.portal_url?.trim()) {
        try {
            urls.push(new URL(broker.portal_url).origin + '/favicon.ico');
        } catch {
            /* invalid URL — skip */
        }
    }
    const pluginIcon = getPluginIconUrl(broker.default_import_plugin);
    if (pluginIcon) urls.push(pluginIcon);
    return urls;
}

/**
 * Resolve the best icon URL for a broker using the fallback chain.
 * Returns the first available URL from the candidate list (sync, cache-dependent).
 *
 * NOTE: The returned URL may still fail to load (e.g. favicon 404).
 * Components that support multi-URL fallback should use `getBrokerIconCandidates()`
 * and `BrokerIcon.svelte` instead, which handle load errors reactively.
 */
export function getBrokerIconUrl(broker: BrokerIconSource | null | undefined): string | null {
    const candidates = getBrokerIconCandidates(broker);
    return candidates[0] ?? null;
}

/**
 * Resolve a broker icon URL by id from a list/map of brokers.
 *
 * Accepts both `Map<number, BrokerIconSource>` and `ReadonlyArray<BrokerLike>`.
 */
export function getBrokerIconUrlById(brokerId: number, brokers: Map<number, BrokerIconSource> | ReadonlyArray<BrokerLike>): string | null {
    if (brokers instanceof Map) {
        return getBrokerIconUrl(brokers.get(brokerId));
    }
    return getBrokerIconUrl(brokers.find((b) => b.id === brokerId));
}
