/**
 * Gallery, `assets/search-premium`: Search Online in the asset dialog, with a provider made premium and its results in a
 * section of their own.
 *
 * As `assets/asset-modal.spec.ts` («Asset search — premium first…») routes it, and in the same order of steps, offline:
 * - `GET /api/v1/assets/provider`: the backend's own list (`route.fetch()`), one searchable provider made premium (the first,
 *   in code order, `mockprov` aside — the dropdown never shows it), every other one community at the default priority;
 * - `GET /api/v1/system/instance`: the backend's own answer with `support_url` null and the self-hosted profile, so that the
 *   «Can't find it? Let us know» row is the one of a plain instance (a link to a new issue, read from its href, never followed);
 * - `GET /api/v1/assets/provider/search/stream`: a canned stream, as `services/assets/search.py` sends it — one event per
 *   provider the search asked, the premium one last, then `done`. No provider is reached. The two premium results and the
 *   community one are invented (no real instrument): `SMPL-…` identifiers, `Sample …` names.
 * Registered after the gallery's offline guard, so tried before it; the guard's own answer to a search never runs. The routes
 * stay with the page until the gallery's outer afterEach drops them (`leaveGalleryPage`).
 */
import {schemas} from '../../src/lib/api/generated';
import {expect, type Page} from './playwright';
import {INSTANCE_CONFIG_PATH} from './instance-config';

const API = '/api/v1';
const PROVIDER_LIST_PATH = `${API}/assets/provider`;
const SEARCH_STREAM_PATH = `${API}/assets/provider/search/stream`;

/** What Search Online is typed: the query of the shot. */
export const GALLERY_PREMIUM_QUERY = 'sample world equity';

export type PremiumSearch = {premium: string; community: string};

function searchHit(provider: string, identifier: string, name: string) {
    return schemas.FAProviderSearchResultItem.parse({identifier, identifier_type: 'TICKER', display_name: name, provider_code: provider, currency: 'EUR', asset_type: 'ETF', provider_url: null, provider_params: null, via_web: false});
}

/** Answer this page's `GET <path>` — that path only — with the backend's own answer, rewritten (the headers of the transit dropped). */
async function serveRewritten(page: Page, path: string, rewrite: (body: unknown) => unknown): Promise<void> {
    await page.route(
        (url) => url.pathname === path,
        async (route, request) => {
            if (request.method() !== 'GET') return route.fallback();
            const response = await route.fetch();
            const headers = {...response.headers()};
            delete headers['content-encoding'];
            delete headers['content-length'];
            await route.fulfill({status: response.status(), headers, ...(response.ok() ? {json: rewrite(await response.json())} : {body: await response.body()})});
        },
    );
}

/** Install the three routes on `page`, before it loads. Returns the providers the shot made premium and community. */
export async function serveGalleryPremiumSearch(page: Page): Promise<PremiumSearch> {
    // The real list, through `page.request`, which no page route reaches.
    const listed = await page.request.get(PROVIDER_LIST_PATH);
    expect(listed.ok(), `GET ${PROVIDER_LIST_PATH} answered ${listed.status()}`).toBe(true);
    const searchable = ((await listed.json()) as Array<{code: string; supports_search?: boolean}>)
        .filter((provider) => provider.supports_search === true && provider.code !== 'mockprov')
        .map((provider) => provider.code)
        .sort();
    if (searchable.length < 2) throw new Error(`the premium search needs two searchable providers besides mockprov; this backend lists ${JSON.stringify(searchable)}`);
    const [premium, community] = searchable;
    const hits: Record<string, unknown[]> = {
        [premium]: [searchHit(premium, 'SMPL-WEQ', 'Sample World Equity UCITS ETF'), searchHit(premium, 'SMPL-WEQ2', 'Sample World Equity Hedged ETF')],
        [community]: [searchHit(community, 'SMPL-CWE', 'Sample Community World Equity Fund')],
    };
    await serveRewritten(page, INSTANCE_CONFIG_PATH, (body) => ({...(body as Record<string, unknown>), support_url: null, profile: 'selfhosted'}));
    await serveRewritten(page, PROVIDER_LIST_PATH, (body) => (body as Array<{code: string}>).map((provider) => ({...provider, ...(provider.code === premium ? {tier: 'premium', priority: 0} : {tier: 'community', priority: 100})})));
    await page.route(
        (url) => url.pathname === SEARCH_STREAM_PATH,
        async (route, request) => {
            if (request.method() !== 'GET') return route.fallback();
            const asked = (new URL(request.url()).searchParams.get('providers') ?? '').split(',').filter((code) => code !== '');
            // The premium provider answers last: its results lead by their tier, not by their arrival.
            const answers = [...asked.filter((code) => code !== premium), ...asked.filter((code) => code === premium)].map((code) => ({event: 'provider_results', provider_code: code, results: hits[code] ?? []}));
            const done = {event: 'done', total_results: answers.reduce((total, answer) => total + answer.results.length, 0), providers_queried: asked, providers_with_errors: []};
            await route.fulfill({status: 200, contentType: 'text/event-stream', body: [...answers, done].map((event) => `data: ${JSON.stringify(event)}\n\n`).join('')});
        },
    );
    return {premium, community};
}
