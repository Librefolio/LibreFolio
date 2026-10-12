/**
 * brokerIconChain.svelte.ts — Shared reactive broker icon fallback chain.
 *
 * Single source of truth for broker icon resolution across ALL components
 * (BrokerIcon, BrokerBadge, and any future consumers).
 *
 * Fallback priority (invariant):
 *   1. icon_url          — custom icon explicitly uploaded by the user
 *   2. default_import_plugin icon — the plugin's icon (async, shared cache), when the plugin is made for a broker
 *   3. portal_url/favicon.ico — favicon heuristic (external, may fail)
 *   4. default_import_plugin icon — when the plugin is a generic fallback (`isFallbackPlugin`, the generic CSV),
 *      whose icon is the same for every broker
 *   5. (caller renders its ultimate UI fallback, the briefcase)
 *
 * Usage — call at component init level (not inside if/for):
 * ```svelte
 * const chain = createBrokerIconChain(() => ({
 *     icon_url: iconUrl,
 *     portal_url: portalUrl,
 *     default_import_plugin: pluginCode,
 * }));
 * // then use chain.currentDisplayUrl, chain.imageLoaded, and give
 * // chain.handleLoad / chain.handleError to the <img> as its onload / onerror
 * ```
 *
 * @module utils/broker/brokerIconChain
 */

import {ensurePluginIconsLoaded, getPluginIconUrl, isFallbackPluginCode, normalizeBrokerIconField, type BrokerIconSource} from './brokerHelpers';

export type {BrokerIconSource};

export interface BrokerIconChain {
    readonly currentDisplayUrl: string | null;
    readonly imageLoaded: boolean;
    /** The <img>'s `load` listener: only a load of the current URL hides the caller's fallback. */
    handleLoad: (event?: Event) => void;
    /** The <img>'s `error` listener: fails the URL of the <img> that raised it, the current one without an event. */
    handleError: (event?: Event) => void;
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

    // Seeded from the cache when the plugin list is already loaded: the first render then orders the
    // candidates as they stay, and with a plugin made for the broker no request goes to the favicon first.
    const initialPluginCode = getSource().default_import_plugin;
    const initialPluginIconUrl = getPluginIconUrl(initialPluginCode);
    let pluginIconUrl = $state<string | null>(initialPluginIconUrl);
    /** A generic fallback plugin's icon comes after the portal's favicon. */
    let pluginIsGeneric = $state(initialPluginIconUrl !== null && isFallbackPluginCode(initialPluginCode));

    $effect(() => {
        const code = normalizeBrokerIconField(getSource().default_import_plugin);
        if (!code) {
            pluginIconUrl = null;
            pluginIsGeneric = false;
            return;
        }
        // Synchronous cache hit (populated by ensureBrokersLoaded / refreshAllBrokers)
        const cached = getPluginIconUrl(code);
        if (cached !== null) {
            pluginIconUrl = cached;
            pluginIsGeneric = isFallbackPluginCode(code);
            return;
        }
        // Cache miss — trigger load (idempotent, shared across all callers).
        // After resolution, update local state so candidateUrls recomputes.
        ensurePluginIconsLoaded().then(() => {
            pluginIconUrl = getPluginIconUrl(code);
            pluginIsGeneric = isFallbackPluginCode(code);
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
        // 2. Icon of a plugin made for this broker (arrives async — added when ready)
        if (pluginIconUrl && !pluginIsGeneric) urls.push(pluginIconUrl);
        // 3. Portal favicon (external heuristic — may 404 or CORS-block)
        if (portalUrl) {
            try {
                urls.push(new URL(portalUrl).origin + '/favicon.ico');
            } catch {
                /* invalid URL — skip */
            }
        }
        // 4. Icon of a generic fallback plugin, the same for every broker
        if (pluginIconUrl && pluginIsGeneric) urls.push(pluginIconUrl);
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

    /**
     * The URL an <img> event is about: the `src` of the <img> that raised it. Svelte never removes
     * `onload` / `onerror` from an <img> swapped out by `{#key}`, so a request still in flight reports
     * after the swap, about a URL that is no longer the current one. `getAttribute`, not `.src`, which
     * resolves the URL against the page. Without an event, the current URL.
     */
    function eventUrl(event?: Event): string | null {
        const target = event?.currentTarget as Element | null | undefined;
        if (target && typeof target.getAttribute === 'function') return target.getAttribute('src');
        return currentDisplayUrl;
    }

    function handleLoad(event?: Event) {
        if (eventUrl(event) === currentDisplayUrl) imageLoaded = true;
    }

    function handleError(event?: Event) {
        const url = eventUrl(event);
        if (url) failedUrls = new Set([...failedUrls, url]);
        if (url === currentDisplayUrl) imageLoaded = false;
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
