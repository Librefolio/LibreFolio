/**
 * FX Routes Store — Session-level cache for configured FX conversion routes.
 *
 * Loads once per session from GET /fx/providers/routes and derives:
 *  - the set of currency pair slugs that are configured (backend truth)
 *  - the set of currencies that are "reachable" via a configured route, i.e. every
 *    currency that appears at least once in any leg/step of a configured conversion
 *    (base, quote, or any chain step's `from`/`to`).
 *
 * This is the authoritative source of configured pairs/currencies — unlike
 * `fxStoreRegistry.getRegisteredPairs()`, which only reflects the in-memory
 * TimeSeriesStores lazily created during the current session.
 *
 * Used by target/display currency selectors (dashboard display currency,
 * asset-detail conversion currency) to restrict the list to currencies the user
 * can actually convert to.
 *
 * @module stores/reference/fxRoutesStore
 */
import {zodiosApi} from '$lib/api';
import {writable} from 'svelte/store';
import {createPairSlug} from '$lib/stores/fxStoreRegistry';

// ============================================================================
// INTERNAL STATE
// ============================================================================

let configuredCurrencies: string[] = [];
let configuredCurrencySet: Set<string> = new Set();
let configuredPairSlugs: Set<string> = new Set();
let loaded = false;
let loading = false;
let loadPromise: Promise<void> | null = null;

/**
 * Reactive version counter — incremented whenever the routes data changes.
 * Subscribe in components (`void $fxRoutesVersion`) to retrigger derived
 * computations that call `getConfiguredCurrencySet()`.
 */
export const fxRoutesVersion = writable(0);

function bumpVersion() {
    fxRoutesVersion.update((v) => v + 1);
}

// ============================================================================
// PUBLIC API
// ============================================================================

/**
 * Ensure configured FX routes are loaded (idempotent — safe to call from any component).
 * First call triggers the API request; subsequent calls resolve immediately or share
 * the in-flight promise.
 */
export async function ensureFxRoutesLoaded(): Promise<void> {
    if (loaded) return;
    if (loadPromise) return loadPromise;

    loadPromise = (async () => {
        loading = true;
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            const items = ((response as any)?.items ?? []) as Array<{
                base: string;
                quote: string;
                chain_steps?: Array<{from: string; to: string; provider: string}> | null;
            }>;

            const currencies = new Set<string>();
            const slugs = new Set<string>();
            for (const item of items) {
                if (item.base) currencies.add(item.base.toUpperCase());
                if (item.quote) currencies.add(item.quote.toUpperCase());
                if (item.base && item.quote) slugs.add(createPairSlug(item.base, item.quote));
                for (const step of item.chain_steps ?? []) {
                    if (step.from) currencies.add(step.from.toUpperCase());
                    if (step.to) currencies.add(step.to.toUpperCase());
                }
            }

            configuredCurrencySet = currencies;
            configuredCurrencies = Array.from(currencies).sort();
            configuredPairSlugs = slugs;
            loaded = true;
            bumpVersion();
        } catch (e) {
            console.error('Failed to load FX routes:', e);
        } finally {
            loading = false;
            loadPromise = null;
        }
    })();

    return loadPromise;
}

/** Invalidate the cache so the next `ensureFxRoutesLoaded()` refetches (e.g. after creating a pair). */
export function invalidateFxRoutes(): void {
    loaded = false;
    loadPromise = null;
    bumpVersion();
}

/** Set of currencies reachable via a configured route. */
export function getConfiguredCurrencySet(): Set<string> {
    return configuredCurrencySet;
}

/** Set of configured pair slugs (alphabetical "BASE-QUOTE"). */
export function getConfiguredPairSlugs(): Set<string> {
    return configuredPairSlugs;
}
