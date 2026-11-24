/**
 * A price provider's attribution line (project 76): «Powered by CoinGecko», linked to CoinGecko's site, lives on
 * CoinGecko's own pages only — its card in Settings › Plugins (P4) and its manual page — and never on the screens that
 * show its prices (TL42, the developer's decision of 23/11: the asset already shows CoinGecko's icon and its link).
 *
 * The provider list `GET /api/v1/assets/provider` carries each provider's `attribution: {text, url} | null`; only
 * CoinGecko has one. The test backend has no CoinGecko key, so no asset can be assigned to it. To put an attributed
 * provider on screen, the page's own read of the provider list is rewritten (`page.route`, this page only, GET only)
 * so that `yfinance` — a seeded provider — carries a synthetic attribution; nothing is written to the backend. The
 * provider list is cached once per document (`ensureAssetProvidersCached`), and every navigation here is a full load
 * (`navigateTo`), so the route is installed before the first one.
 *
 * Cases:
 *   1. the Assets list, yfinance attributed: no attribution link on the page;
 *   2. the Dashboard's positions (Performance × table), yfinance attributed: no attribution link;
 *   3. an asset's detail page (a yfinance asset), yfinance attributed: no attribution link;
 *   4. Settings › Plugins as an administrator, real list: CoinGecko's asset card carries its own line, linked to its site;
 *      justETF's card (yfinance has no settings, so no card) and CoinGecko's settings group carry none.
 *
 * Every absence is asserted behind a presence barrier: the owning screen has settled with the attributed provider's
 * assets on show; the detail page also reads the provider list visibly (the provider's name), and that reading is on
 * show. The Assets list and the Dashboard no longer read the provider list at all (the attribution line was their only
 * reader): no reading there is the point, so no barrier waits for one.
 * Assertions read test ids and `data-*` only; the texts compared are the provider's own brand phrase (CoinGecko's, the
 * same in every language). Nothing is written: live prices and the detail page's price sync are answered empty in the
 * page, so no third-party source is reached. Parallel (the config's default), both projects.
 *
 * Prerequisites (populate_mock_data.py): an active asset assigned to yfinance (the seeded `Apple Inc.`, with stored
 * prices), and positions of the test user on it; test users `e2e_test_user` and `e2e_test_admin`.
 */
import type {Locator, Page, Route} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {expect, test} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';
import {goToAssetDetailPage, goToAssetsPage} from './assets-helpers';

const API = '/api/v1';
const PROVIDER_LIST_PATH = `${API}/assets/provider`;
const ASSETS_QUERY_PATH = `${API}/assets/query`;
const PRICES_SYNC_PATH = `${API}/assets/prices/sync`;
const LIVE_PRICES_PATH = `${API}/assets/prices/current`;

/** The one shipped provider whose terms ask for a line, and that line as the backend serves it. */
const COINGECKO = 'coingecko';
const COINGECKO_ATTRIBUTION = {text: 'Powered by CoinGecko', url: 'https://www.coingecko.com/'};
/** A seeded provider, given a synthetic attribution in the page's own read of the list: an attributed provider on screen. */
const PRICED = 'yfinance';
const E2E_ATTRIBUTION = {text: 'Powered by E2E', url: 'https://example.org/'};
/** The seeded yfinance asset with stored prices (populate_mock_data.populate_assets), found by name and provider. */
const SEEDED_PRICED_ASSET = 'Apple Inc.';
/**
 * A price source with a card on Settings › Plugins and no attribution. yfinance has no settings, so no card there: the
 * tab lists only the plugins with something to set (justETF and Borsa Italiana among the shipped ones).
 */
const UNATTRIBUTED_CARD = 'justetf';
/** CoinGecko's terms: the attribution is never smaller than 10 px. */
const MIN_FONT_PX = 10;
const PAGE_TIMEOUT = 30_000;

interface Attribution {
    text: string;
    url: string;
}
interface ProviderEntry {
    code: string;
    name?: string | null;
    attribution?: Attribution | null;
}
interface AssetRow {
    id: number;
    display_name: string;
    provider_code?: string | null;
    active?: boolean;
}
/** How many times this page read the provider list through its route. */
interface ProviderListTraffic {
    served: number;
}

// =============================================================================
// Routes: the provider list (as served, or rewritten), and the price reads kept offline
// =============================================================================

/**
 * Answer this page's `GET /assets/provider` with the backend's own answer, passed through `rewrite` when one is given,
 * and count each answer. The headers describing the body in transit go: the backend gzips from 1 KB up, and a kept
 * `content-encoding` would have the browser decode plain JSON (same as `asset-modal.spec.ts`). Nobody awaits a route
 * callback, so it never throws: a read it leaves unanswered fails the test on its own assertions.
 */
async function serveProviderList(page: Page, rewrite: (entries: ProviderEntry[]) => ProviderEntry[] = (entries) => entries): Promise<ProviderListTraffic> {
    const traffic: ProviderListTraffic = {served: 0};
    await page.route(
        (url) => url.pathname === PROVIDER_LIST_PATH,
        async (route, request) => {
            if (request.method() !== 'GET') return route.fallback();
            try {
                const response = await route.fetch();
                const headers = {...response.headers()};
                delete headers['content-encoding'];
                delete headers['content-length'];
                await route.fulfill({status: response.status(), headers, ...(response.ok() ? {json: rewrite((await response.json()) as ProviderEntry[])} : {body: await response.body()})});
                traffic.served += 1;
            } catch (error) {
                console.warn(`[provider-attribution] left GET ${request.url()} unanswered: ${String(error)}`);
            }
        },
    );
    return traffic;
}

/** The list with yfinance carrying the synthetic attribution; every other entry as served. */
function withPricedAttribution(entries: ProviderEntry[]): ProviderEntry[] {
    return entries.map((entry) => (entry.code === PRICED ? {...entry, attribution: E2E_ATTRIBUTION} : entry));
}

/**
 * Keep the pages off the network: live prices (`POST /assets/prices/current`, polled by the list and the detail page)
 * and the detail page's price sync (`POST /assets/prices/sync`) are answered empty with schema-valid bodies; the page
 * then shows the prices already stored.
 */
async function keepOffline(page: Page): Promise<void> {
    await page.route(
        (url) => url.pathname === LIVE_PRICES_PATH,
        (route: Route) => route.fulfill({status: 200, json: {results: [], success_count: 0, errors: []}}).catch(() => {}),
    );
    await page.route(
        (url) => url.pathname === PRICES_SYNC_PATH,
        (route: Route) => route.fulfill({status: 200, json: schemas.FABulkRefreshResponse.parse({results: [], success_count: 0})}).catch(() => {}),
    );
}

// =============================================================================
// Preconditions, read from the backend (page.request: no page route reaches it)
// =============================================================================

async function realProviderList(page: Page): Promise<ProviderEntry[]> {
    const response = await page.request.get(PROVIDER_LIST_PATH);
    expect(response.ok(), `GET ${PROVIDER_LIST_PATH} → HTTP ${response.status()}`).toBe(true);
    return (await response.json()) as ProviderEntry[];
}

async function allAssets(page: Page): Promise<AssetRow[]> {
    const response = await page.request.get(ASSETS_QUERY_PATH);
    expect(response.ok(), `GET ${ASSETS_QUERY_PATH} → HTTP ${response.status()}`).toBe(true);
    return (await response.json()) as AssetRow[];
}

/** The providers whose real entry carries an attribution: CoinGecko's, checked as the backend serves it. */
async function attributedProviders(page: Page): Promise<Set<string>> {
    const providers = await realProviderList(page);
    const coingecko = providers.find((entry) => entry.code === COINGECKO);
    expect(coingecko, `precondition: ${PROVIDER_LIST_PATH} lists ${COINGECKO}`).toBeTruthy();
    expect(coingecko?.attribution, `precondition: ${COINGECKO}'s attribution as served`).toEqual(COINGECKO_ATTRIBUTION);
    expect(providers.find((entry) => entry.code === PRICED)?.attribution ?? null, `precondition: ${PRICED} has no attribution of its own`).toBeNull();
    return new Set(providers.filter((entry) => entry.attribution).map((entry) => entry.code));
}

/** The seeded yfinance asset with stored prices. */
async function seededPricedAsset(page: Page): Promise<AssetRow> {
    const asset = (await allAssets(page)).find((row) => row.display_name === SEEDED_PRICED_ASSET && row.provider_code === PRICED);
    if (!asset) throw new Error(`No asset "${SEEDED_PRICED_ASSET}" assigned to ${PRICED}: check populate_mock_data.py (populate_assets, populate_asset_provider_assignments).`);
    return asset;
}

// =============================================================================
// Screens and the line
// =============================================================================

/** The provider list reached this page through its route: the cache the line reads is filled, or about to be. */
async function expectProviderListServed(traffic: ProviderListTraffic): Promise<void> {
    await expect.poll(() => traffic.served, {message: 'the page read the provider list', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);
}

/** No attribution link anywhere on the page (TL42): the screens that show prices carry none, whatever the provider asks. */
async function expectNoAttributionLink(page: Page): Promise<void> {
    await expect(page.getByTestId('provider-attribution-link')).toHaveCount(0);
}

/** One line, drawn for `provider` alone, with its one link: address, new tab, no opener, never under 10 px. */
async function expectOneLine(note: Locator, provider: string, attribution: Attribution): Promise<void> {
    await expect(note).toBeVisible({timeout: PAGE_TIMEOUT});
    await expect(note).toHaveAttribute('data-providers', provider);
    await expect(note.getByTestId('provider-attribution-link')).toHaveCount(1);
    const link = note.locator(`[data-testid="provider-attribution-link"][data-provider="${provider}"]`);
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute('href', attribution.url);
    await expect(link).toHaveAttribute('target', '_blank');
    await expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    await expect(link).toHaveText(attribution.text);
    const fontPx = await link.evaluate((element) => Number.parseFloat(getComputedStyle(element).fontSize));
    expect(fontPx, `the attribution's font size (${fontPx}px) is at least ${MIN_FONT_PX}px`).toBeGreaterThanOrEqual(MIN_FONT_PX);
}

/** Dashboard › Positions › Performance × table, settled; returns the asset ids of the rows it draws (`pos-{broker}-{asset}`). */
async function openPerformanceTable(page: Page): Promise<number[]> {
    await navigateTo(page, '/dashboard?tab=posizioni');
    const positions = page.getByTestId('positions-panel');
    await expect(positions).toBeVisible({timeout: PAGE_TIMEOUT});
    await page.getByTestId('positions-toggle-performance').click();
    await page.getByTestId('positions-toggle-table').click();
    await waitForSettled(positions, PAGE_TIMEOUT);
    const table = page.getByTestId('contribution-table');
    await expect(table).toBeVisible({timeout: PAGE_TIMEOUT});
    const rows = table.locator('tbody tr[data-row-id^="pos-"]');
    await expect.poll(() => rows.count(), {message: 'the Performance table shows positions', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);
    const rowIds = await rows.evaluateAll((elements) => elements.map((element) => element.getAttribute('data-row-id') ?? ''));
    return rowIds.map((rowId) => {
        const match = /^pos-(\d+)-(\d+)$/.exec(rowId);
        if (!match) throw new Error(`unexpected Performance row id "${rowId}" (expected pos-{brokerId}-{assetId})`);
        return Number(match[2]);
    });
}

/** The positions drawn include a yfinance asset: the precondition of the Dashboard's line. */
async function expectPricedPosition(page: Page, shownAssetIds: readonly number[]): Promise<void> {
    const priced = new Set((await allAssets(page)).filter((asset) => asset.provider_code === PRICED).map((asset) => asset.id));
    const shown = shownAssetIds.filter((id) => priced.has(id));
    if (shown.length === 0) throw new Error(`The test user's Performance table shows no ${PRICED} asset (assets shown: ${[...new Set(shownAssetIds)].join(', ')}): check populate_mock_data.py (populate_transactions).`);
}

/** The asset detail page, its price on show: the line sits inside the price block. */
async function openPricedDetail(page: Page, asset: AssetRow): Promise<void> {
    await goToAssetDetailPage(page, String(asset.id));
    await expect(page.getByTestId('asset-detail-live-price'), `precondition: ${asset.display_name} shows a stored price`).toBeVisible({timeout: PAGE_TIMEOUT});
}

/**
 * The detail header names the provider from the same cache the line reads (`assetProviderName`, the raw code until the
 * cache lands): its name on show means the provider list has landed in the page.
 */
async function expectProviderNameShown(page: Page): Promise<void> {
    const name = (await realProviderList(page)).find((entry) => entry.code === PRICED)?.name;
    if (!name || name === PRICED) throw new Error(`${PRICED}'s listed name (${String(name)}) does not tell the cache apart from the raw code: the barrier needs another reading`);
    await expect(page.getByTestId('asset-detail-provider-badge')).toContainText(name, {timeout: PAGE_TIMEOUT});
}

// =============================================================================
// 1. The Assets list
// =============================================================================

test.describe('Provider attribution — the Assets list', () => {
    test('TL42: yfinance attributed in the page, its assets listed: no attribution link', async ({page}) => {
        await serveProviderList(page, withPricedAttribution);
        await keepOffline(page);
        await login(page, TEST_USER);
        const asset = await seededPricedAsset(page); // an asset of the attributed provider, listed (active, seeded)

        await goToAssetsPage(page);
        await expect(page.getByTestId('assets-page')).toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
        // The grid (the page's default view) shows the attributed provider's asset
        await expect(page.getByTestId(`asset-card-${asset.id}`)).toBeVisible({timeout: PAGE_TIMEOUT});
        await expectNoAttributionLink(page);
    });
});

// =============================================================================
// 2. The Dashboard's positions
// =============================================================================

test.describe('Provider attribution — the Dashboard positions', () => {
    test('TL42: yfinance attributed in the page, its position shown: no attribution link', async ({page}) => {
        await serveProviderList(page, withPricedAttribution);
        await keepOffline(page);
        await login(page, TEST_USER);

        const shown = await openPerformanceTable(page);
        await expectPricedPosition(page, shown);
        await expectNoAttributionLink(page);
    });
});

// =============================================================================
// 3. An asset's detail page
// =============================================================================

test.describe('Provider attribution — the asset detail page', () => {
    test('TL42: yfinance attributed in the page, a yfinance asset: no attribution link under the price', async ({page}) => {
        const traffic = await serveProviderList(page, withPricedAttribution);
        await keepOffline(page);
        await login(page, TEST_USER);
        const asset = await seededPricedAsset(page);

        await openPricedDetail(page, asset);
        await expectProviderListServed(traffic);
        await expectProviderNameShown(page);
        await expectNoAttributionLink(page);
    });
});

// =============================================================================
// 4. Settings › Plugins
// =============================================================================

test.describe('Provider attribution — Settings › Plugins', () => {
    test('an administrator: CoinGecko’s asset card carries its line; justETF’s card and CoinGecko’s group none', async ({page}) => {
        await login(page, TEST_ADMIN);
        await attributedProviders(page);
        const unattributed = (await realProviderList(page)).find((entry) => entry.code === UNATTRIBUTED_CARD);
        expect(unattributed, `precondition: ${PROVIDER_LIST_PATH} lists ${UNATTRIBUTED_CARD}`).toBeTruthy();
        expect(unattributed?.attribution ?? null, `precondition: ${UNATTRIBUTED_CARD} has no attribution`).toBeNull();

        await navigateTo(page, '/settings?tab=plugins');
        await expect(page.getByTestId('settings-tab-plugins'), '?tab=plugins selects the Plugins tab').toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
        const tab = page.getByTestId('plugin-settings-tab');
        await waitForSettled(tab);
        const assetFamily = tab.locator('[data-testid="plugin-settings-family"][data-family="asset"]');
        const groupFamily = tab.locator('[data-testid="plugin-settings-family"][data-family="group"]');

        // CoinGecko's price source: its own line, as the backend serves it — also the barrier that the cache has landed
        const coingeckoCard = assetFamily.getByTestId(`plugin-settings-form-${COINGECKO}`);
        await expect(coingeckoCard, `${COINGECKO} is listed among the price sources`).toBeVisible({timeout: PAGE_TIMEOUT});
        await expectOneLine(coingeckoCard.getByTestId('plugin-settings-attribution'), COINGECKO, COINGECKO_ATTRIBUTION);

        // justETF's card is there, and carries none
        const otherCard = assetFamily.getByTestId(`plugin-settings-form-${UNATTRIBUTED_CARD}`);
        await expect(otherCard, `${UNATTRIBUTED_CARD} is listed among the price sources`).toBeVisible();
        await expect(otherCard.getByTestId('plugin-settings-attribution')).toHaveCount(0);

        // CoinGecko's settings group (the key) is not a price source: no line there either
        const coingeckoGroup = groupFamily.getByTestId(`plugin-settings-form-${COINGECKO}`);
        await expect(coingeckoGroup, `${COINGECKO}'s settings group is listed`).toBeVisible();
        await expect(coingeckoGroup.getByTestId('plugin-settings-attribution')).toHaveCount(0);
    });
});
