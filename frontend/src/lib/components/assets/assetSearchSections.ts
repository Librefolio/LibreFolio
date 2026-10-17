/**
 * Where a search result stands in the asset search (F21).
 *
 * Each asset provider has a tier (`premium` | `community`) and a priority, lower first: `GET /assets/provider`
 * answers the effective values, the instance's overrides included. The REST search already lists its results in that
 * order; the streamed search sends them as they arrive, and the dropdown orders them here.
 *
 * - `orderSearchResults`: premium first, then lower priority; a **stable** sort, so ties keep the order of arrival.
 *   With every provider at its defaults the order is the arrival order: a self-hosted instance without a premium
 *   provider searches exactly as before (D-X3).
 * - `hasPremium` / `splitSearchResults`: the dropdown shows a Premium section and a closed community section only
 *   when a premium provider took part in the search.
 */

export type ProviderTier = 'premium' | 'community';

/** A provider of the list, as far as the order of the search is concerned. A missing tier or priority is the default. */
export interface RankedProvider {
    code: string;
    tier?: ProviderTier | null;
    priority?: number | null;
}

/** The priority of a provider that declares none (the backend's DEFAULT_SEARCH_PRIORITY). */
export const DEFAULT_SEARCH_PRIORITY = 100;

function providerOf(code: string, providers: readonly RankedProvider[]): RankedProvider | undefined {
    return providers.find((provider) => provider.code === code);
}

function isPremium(code: string, providers: readonly RankedProvider[]): boolean {
    return providerOf(code, providers)?.tier === 'premium';
}

/** The provider's place in the search: 0 for premium and 1 for community, then its priority. Unknown code = community at the default. */
export function searchRank(code: string, providers: readonly RankedProvider[]): [number, number] {
    const provider = providerOf(code, providers);
    return [provider?.tier === 'premium' ? 0 : 1, provider?.priority ?? DEFAULT_SEARCH_PRIORITY];
}

/** The results in the order of the search: premium first, then lower priority; ties keep the given order. A new array. */
export function orderSearchResults<T extends {provider_code: string}>(results: readonly T[], providers: readonly RankedProvider[]): T[] {
    // Array.prototype.sort is stable (ES2019): ties keep the given order.
    return results
        .map((result) => ({result, rank: searchRank(result.provider_code, providers)}))
        .sort((a, b) => a.rank[0] - b.rank[0] || a.rank[1] - b.rank[1])
        .map(({result}) => result);
}

/** Whether one of `codes` is a premium provider. */
export function hasPremium(codes: readonly string[], providers: readonly RankedProvider[]): boolean {
    return codes.some((code) => isPremium(code, providers));
}

/** The results of premium providers and the others, each in the given order. */
export function splitSearchResults<T extends {provider_code: string}>(results: readonly T[], providers: readonly RankedProvider[]): {premium: T[]; community: T[]} {
    const premium: T[] = [];
    const community: T[] = [];
    for (const result of results) (isPremium(result.provider_code, providers) ? premium : community).push(result);
    return {premium, community};
}
