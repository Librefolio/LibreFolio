/**
 * Gallery, `settings/cache-panel` (G-23): the memory caches of the server, answered from a fixture.
 *
 * The panel lists every named cache of the backend (`GET /api/v1/settings/cache/status`, theine registry) with how many
 * entries it holds. The sizes depend on what the other tests of the run did before on the same server, and which caches
 * exist at all depends on which modules were imported: the same commit gave a row more or fewer, and a page 31 px
 * shorter. So the shot reads this list instead, in the shape of `CacheStatusResponse` (checked against the generated
 * schema once, at registration): the names, the sizes limit and the lifetimes are the ones the backend declares
 * (`get_ttl_cache(...)` calls under `backend/app/services`), the current sizes are invented and fixed. A cache added
 * to the backend later is missing here until it is written in; that only matters to this picture.
 *
 * Only `GET` is answered. A clear (`POST`) falls back to the routes registered before this one, then to the backend; the
 * shot never clicks it.
 */
import {schemas} from '../../src/lib/api/generated';
import type {Page} from './playwright';

/** The path the panel reads (`CachePanel.svelte`). */
const CACHE_STATUS_PATH = '/api/v1/settings/cache/status';

type CacheStatusResponse = ReturnType<typeof schemas.CacheStatusResponse.parse>;

const GALLERY_CACHE_STATUS = {
    items: [
        {name: 'asset_current_fetch', current_size: 12, maxsize: 300, ttl_seconds: 120},
        {name: 'asset_history_fetch', current_size: 27, maxsize: 500, ttl_seconds: 900},
        {name: 'asset_metadata_fetch', current_size: 9, maxsize: 200, ttl_seconds: 1800},
        {name: 'fx_provider_currencies', current_size: 4, maxsize: 32, ttl_seconds: 86400},
        {name: 'fx_provider_responses', current_size: 6, maxsize: 200, ttl_seconds: 300},
        {name: 'justetf_chart', current_size: 3, maxsize: 500, ttl_seconds: 3600},
        {name: 'justetf_etf_list', current_size: 1, maxsize: 100, ttl_seconds: 3600},
        {name: 'justetf_overview', current_size: 5, maxsize: 500, ttl_seconds: 3600},
        {name: 'portfolio_blob', current_size: 2, maxsize: 30, ttl_seconds: 86400},
        {name: 'portfolio_layer2', current_size: 4, maxsize: 20, ttl_seconds: 1800},
        {name: 'portfolio_wac', current_size: 18, maxsize: 200, ttl_seconds: 3600},
        {name: 'risk_optimization', current_size: 0, maxsize: 32, ttl_seconds: 1800},
        {name: 'risk_simulation', current_size: 1, maxsize: 32, ttl_seconds: 1800},
        {name: 'scheduled_investment', current_size: 7, maxsize: 256, ttl_seconds: 172800},
        {name: 'search_queries', current_size: 14, maxsize: 500, ttl_seconds: 900},
        {name: 'search_results', current_size: 63, maxsize: 5000, ttl_seconds: 86400},
        {name: 'upload_metadata', current_size: 8, maxsize: 500, ttl_seconds: 3600},
        {name: 'yfinance_currency', current_size: 10, maxsize: 2000, ttl_seconds: 86400},
    ],
} satisfies CacheStatusResponse;

/**
 * Answer the panel's read of the cache status on `page` with {@link GALLERY_CACHE_STATUS}. Call it inside the test, before
 * the first navigation to the Memory category; the gallery's outer afterEach drops the route once the page has left.
 */
export async function serveGalleryCacheStatus(page: Page): Promise<void> {
    // Checked once, here: a schema that moved fails the test now, with Zod's own message.
    const body = schemas.CacheStatusResponse.parse(GALLERY_CACHE_STATUS);
    await page.route(
        (url) => url.pathname === CACHE_STATUS_PATH,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            await route.fulfill({json: body});
        },
    );
}
