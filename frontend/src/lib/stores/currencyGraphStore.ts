/**
 * Currency Graph Store — Session-level cache for the FX currency graph.
 *
 * Builds the graph from GET /fx/providers + GET /utilities/currencies,
 * then keeps it for the rest of the page session. The backend keeps each
 * provider's currency list for 24 h (and the last known one when the provider
 * fails), so the answers are stable for a session in practice, not by contract:
 * a provider's list that changes later is seen after a reload.
 *
 * There is deliberately no invalidation API: the graph is built only from
 * provider capabilities — the MANUAL sentinel is skipped and user FX
 * routes/rates are not graph inputs — so the user's own changes never make a
 * complete graph stale.
 *
 * One exception: a provider whose currency list the backend could not read
 * (`currencies_unavailable`, e.g. ECB slow right after a restart) has no
 * edges, so the graph built from it is incomplete. That graph is returned but
 * not cached: the next call asks the backend again, which retries the list.
 *
 * Usage:
 *   const paths = await findConversionPaths('RON', 'USD');  // the routes of a pair, found in a Web Worker
 *
 * @module stores/currencyGraphStore
 */

import type MultiDirectedGraph from 'graphology';
import {buildCurrencyGraph, type ChainStep, type EdgeAttributes, type ProviderInfo} from '$lib/utils/currency/currencyGraph';
import {findRoutePathsOffThread} from '$lib/workers/currencyRoutesPool';
import {zodiosApi} from '$lib/api';
import {ensureCurrenciesLoaded, getAllCurrencies, isCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
/**
 * Reactive version counter — incremented when FX providers are cached.
 * Subscribe in Svelte components to trigger re-evaluation when providers load.
 */
import {writable} from 'svelte/store';

// ============================================================================
// INTERNAL STATE
// ============================================================================

/** Type alias for the concrete graph type */
type CurrencyGraph = MultiDirectedGraph<Record<string, never>, EdgeAttributes>;

/** Cached graph instance */
let cachedGraph: CurrencyGraph | null = null;

/** Cached provider info list */
let cachedFxProviders: ProviderInfo[] = [];

/** Loading promise to avoid duplicate concurrent builds */
let buildPromise: Promise<CurrencyGraph> | null = null;

export const fxProvidersVersion = writable(0);

// ============================================================================
// PUBLIC API
// ============================================================================

/**
 * Get or build the currency graph.
 *
 * First call triggers API requests for providers + currencies, builds the graph.
 * Subsequent calls return the cached graph immediately.
 * Safe to call concurrently — uses a shared promise.
 *
 * Note: The graph only uses currency CODES (not localized names), so language
 * is irrelevant. If currencies are already loaded (in any language), we reuse them.
 *
 * @returns The MultiDirectedGraph instance
 */
export async function getCurrencyGraph(): Promise<CurrencyGraph> {
    if (cachedGraph) return cachedGraph;
    if (buildPromise) return buildPromise;

    buildPromise = (async () => {
        try {
            // Ensure currencies are loaded (any language is fine — we only need codes)
            const currenciesReady = isCurrenciesLoaded() ? Promise.resolve() : ensureCurrenciesLoaded();

            // Fetch providers and currencies in parallel
            const [providersResponse] = await Promise.all([zodiosApi.list_providers_api_v1_fx_providers_get(), currenciesReady]);

            // Map API response to ProviderInfo
            const providers: ProviderInfo[] = (providersResponse as any[]).map((p: any) => ({
                code: p.code,
                name: p.name,
                base_currency: p.base_currency,
                base_currencies: p.base_currencies ?? [p.base_currency],
                target_currencies: p.target_currencies ?? [],
                currencies_unavailable: p.currencies_unavailable ?? false,
                icon_url: p.icon_url ?? null,
                description: p.description ?? '',
                description_i18n: p.description_i18n ?? {},
                warning_i18n: p.warning_i18n ?? {},
                warning_level: p.warning_level ?? 'warning',
                docs_url: p.docs_url ?? null,
                ...readinessOf(p),
            }));

            // Get all currency codes
            const allCurrencyCodes = getAllCurrencies().map((c) => c.code);

            // Build the graph
            const graph = buildCurrencyGraph(providers, allCurrencyCodes);

            // Cache — unless a provider came without its currencies: that graph is incomplete, the next call rebuilds it
            cachedFxProviders = providers;
            if (!providers.some((p) => p.currencies_unavailable)) cachedGraph = graph;
            fxProvidersVersion.update((v) => v + 1);

            return graph;
        } finally {
            buildPromise = null;
        }
    })();

    return buildPromise;
}

/** The readiness fields of one provider of the list (plan 76, N1/N2b); a list without them reads as configured. */
function readinessOf(p: any): Pick<ProviderInfo, 'configured' | 'missing_settings' | 'missing_reason' | 'invalid_variables'> {
    return {
        configured: p.configured !== false,
        missing_settings: Array.isArray(p.missing_settings) ? p.missing_settings.filter((key: unknown) => typeof key === 'string') : [],
        missing_reason: typeof p.missing_reason === 'string' ? p.missing_reason : null,
        invalid_variables: Array.isArray(p.invalid_variables) ? p.invalid_variables.filter((name: unknown) => typeof name === 'string') : [],
    };
}

/**
 * Read the provider list again for the readiness only (plan 76, N3c: a save in «Configure» switches a provider on):
 * the cached providers' `configured` and its companions are updated in place of the old ones, and
 * `fxProvidersVersion` moves so the pickers redraw. The graph, built from the currencies, is not rebuilt. A failed read
 * leaves the cache as it was and never throws.
 */
export async function refreshFxProviderReadiness(): Promise<void> {
    try {
        const response = (await zodiosApi.list_providers_api_v1_fx_providers_get()) as any[];
        const fresh = new Map((Array.isArray(response) ? response : []).map((p: any) => [p.code, readinessOf(p)]));
        cachedFxProviders = cachedFxProviders.map((provider) => (fresh.has(provider.code) ? {...provider, ...fresh.get(provider.code)} : provider));
        fxProvidersVersion.update((v) => v + 1);
    } catch {
        // The API client logs the failed read; the pickers keep the state they had.
    }
}

/**
 * Get cached FX provider info (available after getCurrencyGraph() resolves).
 * Returns empty array if graph hasn't been built yet.
 */
export function getCachedFxProviders(): ProviderInfo[] {
    return cachedFxProviders;
}

/**
 * The conversion routes of a pair, as the route picker offers them (lane 75, L20b, decision Q6): the depth rule of
 * `routeSearchDepth` on the configured providers, then every chain up to that depth. The search runs in a Web Worker
 * (`workers/currencyRoutesPool.ts`); the providers are sent with their current readiness, so a provider just configured
 * counts at the next search.
 *
 * @param source - Source currency code (e.g. "RON")
 * @param target - Target currency code (e.g. "USD")
 * @param maxDepth - The longest chain searched (default 4, the cap of the rule)
 * @returns Array of paths sorted by length (shortest first)
 */
export async function findConversionPaths(source: string, target: string, maxDepth: number = 4): Promise<ChainStep[][]> {
    await getCurrencyGraph();
    const currencyCodes = getAllCurrencies().map((currency) => currency.code);
    const providers = cachedFxProviders.map(({code, name, base_currency, base_currencies, target_currencies, configured}) => ({code, name, base_currency, base_currencies, target_currencies, configured}));
    return findRoutePathsOffThread({providers, currencyCodes, source, target, cap: maxDepth});
}
