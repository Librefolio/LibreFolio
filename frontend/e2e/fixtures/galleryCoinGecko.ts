/**
 * Gallery, `assets/coingecko-search` (project 76, P7 — the CoinGecko key guide, `user/settings/coingecko-key`): Search Online
 * in the asset dialog with CoinGecko's results for «bitcoin», as an instance with its key would show them.
 *
 * The lane's backend has CoinGecko UNCONFIGURED, and stays so: no key or plugin setting is ever written (the backend is
 * shared, and a key would send the search to the real CoinGecko). The configured state lives in the page's own routes,
 * installed before it loads, as galleryAssetSearch.ts routes the premium search:
 * - `GET /api/v1/assets/provider`: the backend's own list (`route.fetch()`), `coingecko` marked configured — nothing missing,
 *   nothing invalid —, every other provider as the lane lists it (their chips show, as on a real instance);
 * - `GET /api/v1/system/instance`: the backend's own answer with `support_url` null and the self-hosted profile, so that the
 *   «Can't find it? Let us know» row is the one of a plain instance (as the premium shot);
 * - `GET /api/v1/assets/provider/search/stream`: a canned stream, as `services/assets/search.py` sends it — `coingecko` with
 *   its three rows, every other provider asked with none, then `done`. The search never reaches the backend, so nothing
 *   reaches CoinGecko; any request to a `coingecko.com` host is aborted and recorded ({@link CoinGeckoSearch.coingeckoHosts}),
 *   except the provider's icon ({@link COINGECKO_ICON_URL}, P1b-b): an image CoinGecko serves to every page that shows it,
 *   as Yahoo's and justETF's icons, and no API request.
 * Registered after the gallery's offline guard, so tried before it. The routes stay with the page until the gallery's outer
 * afterEach drops them (`leaveGalleryPage`).
 */
import {schemas} from '../../src/lib/api/generated';
import {expect, type Page} from './playwright';
import {INSTANCE_CONFIG_PATH} from './instance-config';

const API = '/api/v1';
const PROVIDER_LIST_PATH = `${API}/assets/provider`;
const SEARCH_STREAM_PATH = `${API}/assets/provider/search/stream`;

/** The provider of the shot. */
export const COINGECKO = 'coingecko';
/** What Search Online is typed: the query of the shot. */
export const GALLERY_COINGECKO_QUERY = 'bitcoin';
/** The provider's icon: CoinGecko's favicon by URL (`get_icon`, P1b-b), let through so the shot shows it. */
export const COINGECKO_ICON_URL = 'https://www.coingecko.com/favicon.ico';

/** The icon's request, whatever its query: the gallery writes favicon URLs with `?lf-gallery` (galleryReportSets.ts). */
function isCoinGeckoIcon(url: URL): boolean {
    const icon = new URL(COINGECKO_ICON_URL);
    return url.origin === icon.origin && url.pathname === icon.pathname;
}
/** CoinGecko's three answers, by their CoinGecko id, in the order the stream sends them. */
export const GALLERY_COINGECKO_IDS = ['bitcoin', 'wrapped-bitcoin', 'bitcoin-cash'] as const;

/** What the routes saw: the providers each search asked, and any request that went for a CoinGecko host (each one a red). */
export type CoinGeckoSearch = {asked: string[][]; coingeckoHosts: string[]};

function coinHit(identifier: string, name: string) {
    return schemas.FAProviderSearchResultItem.parse({
        identifier,
        identifier_type: 'OTHER',
        display_name: name,
        provider_code: COINGECKO,
        currency: 'EUR',
        asset_type: 'CRYPTO',
        provider_params: {vs_currency: 'EUR'},
        via_web: false,
    });
}

// The coin's name alone, as the plugin names a row (TL40)
const HITS = [coinHit('bitcoin', 'Bitcoin'), coinHit('wrapped-bitcoin', 'Wrapped Bitcoin'), coinHit('bitcoin-cash', 'Bitcoin Cash')];

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

/** Install the routes on `page`, before it loads. Returns the record the test reads at the end. */
export async function serveGalleryCoinGeckoSearch(page: Page): Promise<CoinGeckoSearch> {
    // The real list, through `page.request`, which no page route reaches: CoinGecko is there, searchable, and still to
    // configure — the proof that the lane holds no key, so the configured chip of the shot is this simulation's.
    const listed = await page.request.get(PROVIDER_LIST_PATH);
    expect(listed.ok(), `GET ${PROVIDER_LIST_PATH} answered ${listed.status()}`).toBe(true);
    const real = ((await listed.json()) as Array<{code: string; supports_search?: boolean; configured?: boolean}>).find((provider) => provider.code === COINGECKO);
    expect(real, `precondition: ${PROVIDER_LIST_PATH} lists ${COINGECKO}`).toBeTruthy();
    expect(real?.supports_search, `precondition: ${COINGECKO} searches`).toBe(true);
    expect(real?.configured, `precondition: the lane's ${COINGECKO} has no key (configured false)`).toBe(false);

    const record: CoinGeckoSearch = {asked: [], coingeckoHosts: []};
    await page.route(
        (url) => (url.hostname === 'coingecko.com' || url.hostname.endsWith('.coingecko.com')) && !isCoinGeckoIcon(url),
        async (route) => {
            record.coingeckoHosts.push(`${route.request().method()} ${route.request().url()}`);
            await route.abort();
        },
    );
    await serveRewritten(page, INSTANCE_CONFIG_PATH, (body) => ({...(body as Record<string, unknown>), support_url: null, profile: 'selfhosted'}));
    await serveRewritten(page, PROVIDER_LIST_PATH, (body) => (body as Array<{code: string}>).map((provider) => (provider.code === COINGECKO ? {...provider, configured: true, missing_settings: [], missing_reason: null, invalid_variables: []} : provider)));
    await page.route(
        (url) => url.pathname === SEARCH_STREAM_PATH,
        async (route, request) => {
            if (request.method() !== 'GET') return route.fallback();
            const asked = (new URL(request.url()).searchParams.get('providers') ?? '').split(',').filter((code) => code !== '');
            record.asked.push(asked);
            // Every provider asked answers, CoinGecko last: the others with nothing.
            const answers = [...asked.filter((code) => code !== COINGECKO), ...asked.filter((code) => code === COINGECKO)].map((code) => ({event: 'provider_results', provider_code: code, results: code === COINGECKO ? HITS : []}));
            const done = {event: 'done', total_results: answers.reduce((total, answer) => total + answer.results.length, 0), providers_queried: asked, providers_with_errors: []};
            await route.fulfill({status: 200, contentType: 'text/event-stream', body: [...answers, done].map((event) => `data: ${JSON.stringify(event)}\n\n`).join('')});
        },
    );
    return record;
}
