/**
 * Currency Graph Store — Session-level cache for the FX currency graph.
 *
 * Builds the graph once from GET /fx/providers + GET /utilities/currencies,
 * then caches it for the entire session. Both API responses are stable
 * (providers are registered at startup, currencies don't change).
 *
 * Usage:
 *   const graph = await getCurrencyGraph();
 *   const paths = findAllPaths(graph, 'RON', 'USD');
 *
 * @module stores/currencyGraphStore
 */

import type MultiDirectedGraph from 'graphology';
import {buildCurrencyGraph, type ChainStep, type EdgeAttributes, findAllPaths, type ProviderInfo} from '$lib/utils/currencyGraph';
import {zodiosApi} from '$lib/api';
import {ensureCurrenciesLoaded, getAllCurrencies, isCurrenciesLoaded} from '$lib/stores/currencyStore';
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

/** Hash of provider codes used to build the cached graph (for invalidation) */
let cachedProvidersHash: string | null = null;

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
            const currenciesReady = isCurrenciesLoaded()
                ? Promise.resolve()
                : ensureCurrenciesLoaded();

            // Fetch providers and currencies in parallel
            const [providersResponse] = await Promise.all([
                zodiosApi.list_providers_api_v1_fx_providers_get(),
                currenciesReady,
            ]);

            // Map API response to ProviderInfo
            const providers: ProviderInfo[] = (providersResponse as any[]).map((p: any) => ({
                code: p.code,
                name: p.name,
                base_currency: p.base_currency,
                base_currencies: p.base_currencies ?? [p.base_currency],
                target_currencies: p.target_currencies ?? [],
                icon_url: p.icon_url ?? null,
                description: p.description ?? '',
                description_i18n: p.description_i18n ?? {},
                warning_i18n: p.warning_i18n ?? {},
                docs_url: p.docs_url ?? null,
            }));

            // Get all currency codes
            const allCurrencyCodes = getAllCurrencies().map(c => c.code);

            // Build the graph
            const graph = buildCurrencyGraph(providers, allCurrencyCodes);

            // Cache
            cachedFxProviders = providers;
            cachedProvidersHash = JSON.stringify(providers.map(p => p.code).sort());
            cachedGraph = graph;
            fxProvidersVersion.update(v => v + 1);

            return graph;
        } finally {
            buildPromise = null;
        }
    })();

    return buildPromise;
}

/**
 * Get cached FX provider info (available after getCurrencyGraph() resolves).
 * Returns empty array if graph hasn't been built yet.
 */
export function getCachedFxProviders(): ProviderInfo[] {
    return cachedFxProviders;
}

/**
 * Find all conversion paths between two currencies.
 * Convenience wrapper that ensures the graph is built first.
 *
 * @param source - Source currency code (e.g. "RON")
 * @param target - Target currency code (e.g. "USD")
 * @param maxDepth - Maximum chain length (default 4)
 * @returns Array of paths sorted by length (shortest first)
 */
export async function findConversionPaths(
    source: string,
    target: string,
    maxDepth: number = 4,
): Promise<ChainStep[][]> {
    const graph = await getCurrencyGraph();
    return findAllPaths(graph as Parameters<typeof findAllPaths>[0], source, target, maxDepth);
}

/**
 * Invalidate the cached graph (force rebuild on next access).
 * Normally not needed — the graph is stable for the session.
 */
export function invalidateCurrencyGraph(): void {
    cachedGraph = null;
    cachedProvidersHash = null;
    cachedFxProviders = [];
    buildPromise = null;
}

