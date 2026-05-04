/**
 * Broker Helpers — Shared utility functions for broker icon resolution.
 *
 * Centralizes the icon_url → portal_url/favicon.ico → plugin_icon → null
 * fallback chain previously duplicated across FilesTable, TransactionsTable,
 * BrokerBadge, etc.
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

/** Sync lookup — returns the cached plugin icon URL or null. */
function getPluginIconUrl(pluginCode: string | null | undefined): string | null {
    if (!pluginCode || !_pluginIconCache) return null;
    return _pluginIconCache.get(pluginCode) ?? null;
}

/**
 * Resolve the best icon URL for a broker using the fallback chain:
 *  1. `icon_url` (custom uploaded icon)
 *  2. `portal_url` → origin + `/favicon.ico`
 *  3. `default_import_plugin` → cached plugin icon
 *  4. `null` (caller should render a colored dot or other fallback)
 */
export function getBrokerIconUrl(broker: BrokerIconSource | null | undefined): string | null {
    if (!broker) return null;
    if (broker.icon_url?.trim()) return broker.icon_url;
    if (broker.portal_url?.trim()) {
        try {
            return new URL(broker.portal_url).origin + '/favicon.ico';
        } catch {
            /* invalid URL — skip */
        }
    }
    // Fallback 3: plugin icon from cache
    const pluginIcon = getPluginIconUrl(broker.default_import_plugin);
    if (pluginIcon) return pluginIcon;
    return null;
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
