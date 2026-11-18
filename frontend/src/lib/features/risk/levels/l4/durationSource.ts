/**
 * The name of the source a bond's duration was read from (RN-25), as the rates box says it.
 *
 * The duration is a voice of the asset's profile, so its source is an enricher (`borsa_italiana`), the user's own
 * value (`user`) or the copy of the old classification (`legacy`) — never a price provider: the asset-provider cache of
 * `providerHelpers` does not know them. An enricher is named as it declares itself (`GET /assets/enrichers`, read
 * once); `user` and `legacy` take the Profile's own words; any other code stands as it is.
 */
import {writable} from 'svelte/store';

import {zodiosApi} from '$lib/api';

let enricherNames: Map<string, string> | null = null;
let pending: Promise<void> | null = null;

/** Bumped once the enrichers' names are in: a component that names a source reads it to redraw. */
export const enricherNamesVersion = writable(0);

/** Read the enrichers' names once (deduplicated); a failed read leaves the codes standing in. */
export async function ensureEnricherNames(): Promise<void> {
    if (enricherNames) return;
    if (pending) return pending;
    pending = (async () => {
        const loaded = new Map<string, string>();
        try {
            const catalogue = await zodiosApi.list_enrichers_api_v1_assets_enrichers_get();
            for (const enricher of catalogue.enrichers) loaded.set(enricher.code, enricher.name);
        } catch {
            // The API client already logs the failure (H-60); the source then shows its code.
        } finally {
            enricherNames = loaded;
            pending = null;
            enricherNamesVersion.update((version) => version + 1);
        }
    })();
    return pending;
}

/** The source's name: the Profile's words for `user` and `legacy`, an enricher's declared name, else the code. */
export function durationSourceName(code: string, translate: (key: string) => string): string {
    if (code === 'user') return translate('assets.profile.edit.sourceUser');
    if (code === 'legacy') return translate('assets.profile.edit.sourceLegacy');
    return enricherNames?.get(code) ?? code;
}
