/**
 * profileSources.ts — the sources of the asset profile (plan 68, E6a; 87, A2): an enricher's name and icon as it declares
 * them (`GET /assets/enrichers`, read once per session), `user` and `legacy` in the profile's own words, any other code
 * as it is. The «Ultime variazioni» panel and the «Storia del dato» window name and draw their sources with it.
 *
 * A failed read is not kept: the next caller asks again, and meanwhile a source shows its code.
 */
import {zodiosApi} from '$lib/api';

/** An enricher as the profile shows it: its declared name, and its icon (an address, a list of candidates, or none). */
export interface ProfileSource {
    name: string;
    icon: string | (string | null)[] | null;
}

let sources: Promise<Record<string, ProfileSource>> | null = null;

/** The enrichers' declared names and icons, by code; asked once per session. */
export function loadProfileSources(): Promise<Record<string, ProfileSource>> {
    if (sources === null) {
        sources = zodiosApi.list_enrichers_api_v1_assets_enrichers_get().then(
            (catalogue) => Object.fromEntries(catalogue.enrichers.map((enricher) => [enricher.code, {name: enricher.name, icon: enricher.icon ?? null}])),
            () => {
                sources = null;
                return {};
            },
        );
    }
    return sources;
}

/** A source's name: the profile's words for `user` and `legacy`, an enricher's declared name, else the code. */
export function profileSourceName(code: string, translate: (key: string) => string, known: Record<string, ProfileSource>): string {
    if (code === 'user') return translate('assets.profile.edit.sourceUser');
    if (code === 'legacy') return translate('assets.profile.edit.sourceLegacy');
    return known[code]?.name ?? code;
}

/** Forget the sources (sign-out, tests). */
export function clearProfileSources(): void {
    sources = null;
}
