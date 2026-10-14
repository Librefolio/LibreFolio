/**
 * R13.2: how LibreFolio is set up for a pair whose stored rate the FX step did not find,
 * from the configured conversion routes. It decides what the step offers in place:
 * add the pair, download its rates, or (manual rates only) type the rate.
 * The shared `fxRoutesStore` keeps only the pair slugs, not their providers.
 */
import {zodiosApi} from '$lib/api';
import {createPairSlug} from '$lib/stores/fxStoreRegistry';

/** `absent`: no route; `provider`: a route downloads rates; `manual`: every route is MANUAL alone. */
export type PairSetup = 'absent' | 'provider' | 'manual';

const MANUAL = 'MANUAL';

/** Setup of every configured pair, keyed by its slug (`createPairSlug`, alphabetical). */
export async function loadPairSetups(): Promise<ReadonlyMap<string, PairSetup>> {
    const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
    const setups = new Map<string, PairSetup>();
    for (const route of response.items ?? []) {
        const slug = createPairSlug(route.base, route.quote);
        if (route.providers_used.some((code) => code.toUpperCase() !== MANUAL)) setups.set(slug, 'provider');
        else if (!setups.has(slug)) setups.set(slug, 'manual');
    }
    return setups;
}

export function pairSetup(setups: ReadonlyMap<string, PairSetup>, base: string, quote: string): PairSetup {
    return setups.get(createPairSlug(base, quote)) ?? 'absent';
}
