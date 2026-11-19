/**
 * profileSources.ts — the name of a source of the asset profile (plan 68, E6a): an enricher as it declares itself
 * (`GET /assets/enrichers`, read once per session), `user` and `legacy` in the profile's own words, any other code as it
 * is. The «Ultime variazioni» panel and the «Storia del dato» window name their sources with it.
 *
 * A failed read is not kept: the next caller asks again, and meanwhile a source shows its code.
 */
import {zodiosApi} from '$lib/api';

let names: Promise<Record<string, string>> | null = null;

/** The enrichers' declared names, by code; asked once per session. */
export function loadEnricherNames(): Promise<Record<string, string>> {
    if (names === null) {
        names = zodiosApi.list_enrichers_api_v1_assets_enrichers_get().then(
            (catalogue) => Object.fromEntries(catalogue.enrichers.map((enricher) => [enricher.code, enricher.name])),
            () => {
                names = null;
                return {};
            },
        );
    }
    return names;
}

/** A source's name: the profile's words for `user` and `legacy`, an enricher's declared name, else the code. */
export function profileSourceName(code: string, translate: (key: string) => string, enricherNames: Record<string, string>): string {
    if (code === 'user') return translate('assets.profile.edit.sourceUser');
    if (code === 'legacy') return translate('assets.profile.edit.sourceLegacy');
    return enricherNames[code] ?? code;
}

/** Forget the names (sign-out, tests). */
export function clearEnricherNames(): void {
    names = null;
}
