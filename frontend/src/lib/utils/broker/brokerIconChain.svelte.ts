/**
 * brokerIconChain.svelte.ts — Shared reactive broker icon fallback chain.
 *
 * Single source of truth for broker icon resolution across ALL components
 * (BrokerIcon, BrokerBadge, and any future consumers).
 *
 * Fallback priority (invariant):
 *   1. icon_url          — custom icon explicitly uploaded by the user
 *   2. portal_url/favicon.ico — favicon heuristic (external, may fail)
 *   3. default_import_plugin icon — app-hosted plugin icon (async, shared cache)
 *   4. (caller renders initial letter as ultimate UI fallback)
 *
 * Usage — call at component init level (not inside if/for):
 * ```svelte
 * const chain = createBrokerIconChain(() => ({
 *     icon_url: iconUrl,
 *     portal_url: portalUrl,
 *     default_import_plugin: pluginCode,
 * }));
 * // then use chain.currentDisplayUrl, chain.imageLoaded,
 * //           chain.handleLoad(), chain.handleError()
 * ```
 *
 * @module utils/broker/brokerIconChain
 */

import {ensurePluginIconsLoaded, getPluginIconUrl, normalizeBrokerIconField, type BrokerIconSource} from './brokerHelpers';

export type {BrokerIconSource};

export interface BrokerIconChain {
    readonly currentDisplayUrl: string | null;
    readonly imageLoaded: boolean;
    handleLoad: () => void;
    handleError: () => void;
}

/**
 * Create a reactive icon fallback chain for a broker.
 *
 * @param getSource - Reactive accessor returning the broker's icon-relevant fields.
 *   Must be a function (not a plain object) so that $derived tracks reactivity.
 * @returns Reactive handles for use in the component template.
 */
export function createBrokerIconChain(getSource: () => BrokerIconSource): BrokerIconChain {
    // =========================================================================
    // Plugin icon — loaded async via shared module-level cache
    // =========================================================================

    let pluginIconUrl = $state<string | null>(null);

    $effect(() => {
        const code = normalizeBrokerIconField(getSource().default_import_plugin);
        if (!code) {
            pluginIconUrl = null;
            return;
        }
        // Synchronous cache hit (populated by ensureBrokersLoaded / refreshAllBrokers)
        const cached = getPluginIconUrl(code);
        if (cached !== null) {
            pluginIconUrl = cached;
            return;
        }
        // Cache miss — trigger load (idempotent, shared across all callers).
        // After resolution, update local state so candidateUrls recomputes.
        ensurePluginIconsLoaded().then(() => {
            pluginIconUrl = getPluginIconUrl(code);
        });
    });

    // =========================================================================
    // Candidate URL list — ordered per the invariant priority
    // =========================================================================

    let candidateUrls = $derived.by(() => {
        const src = getSource();
        const urls: string[] = [];
        const iconUrl = normalizeBrokerIconField(src.icon_url);
        const portalUrl = normalizeBrokerIconField(src.portal_url);
        // 1. Custom uploaded icon (most reliable — user chose it)
        if (iconUrl) urls.push(iconUrl);
        // 2. Portal favicon (external heuristic — may 404 or CORS-block)
        if (portalUrl) {
            try {
                urls.push(new URL(portalUrl).origin + '/favicon.ico');
            } catch {
                /* invalid URL — skip */
            }
        }
        // 3. Plugin icon (app-hosted, arrives async — added when ready)
        if (pluginIconUrl) urls.push(pluginIconUrl);
        return urls;
    });

    // =========================================================================
    // Failure tracking — drives fallback to next candidate
    // =========================================================================

    let failedUrls = $state(new Set<string>());

    // Reset failure state when the broker identity changes (props swap).
    let srcKey = $derived(() => {
        const s = getSource();
        return `${s.icon_url ?? ''}|${s.portal_url ?? ''}|${s.default_import_plugin ?? ''}`;
    });
    let prevKey = '';
    $effect(() => {
        const key = srcKey();
        if (key !== prevKey) {
            prevKey = key;
            failedUrls = new Set();
        }
    });

    /** First candidate not yet failed, or null → caller renders initial letter. */
    let currentDisplayUrl = $derived(candidateUrls.find((u) => !failedUrls.has(u)) ?? null);

    // =========================================================================
    // Image load state — drives opacity transition
    // =========================================================================

    let imageLoaded = $state(false);

    let prevDisplayUrl = '';
    $effect(() => {
        const url = currentDisplayUrl ?? '';
        if (url !== prevDisplayUrl) {
            prevDisplayUrl = url;
            // data: URIs are decoded synchronously — no onload race.
            imageLoaded = url.startsWith('data:');
        }
    });

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleLoad() {
        imageLoaded = true;
    }

    function handleError() {
        if (currentDisplayUrl) {
            failedUrls = new Set([...failedUrls, currentDisplayUrl]);
        }
        imageLoaded = false;
    }

    return {
        get currentDisplayUrl() {
            return currentDisplayUrl;
        },
        get imageLoaded() {
            return imageLoaded;
        },
        handleLoad,
        handleError,
    };
}
