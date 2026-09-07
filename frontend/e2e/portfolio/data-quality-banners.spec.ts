/**
 * DataQualityBanner — E2E Tests
 *
 * Tests the unified DataQualityBanner component across all three contexts:
 * 1. Dashboard (grouped mode)
 * 2. Asset detail (flat mode)
 * 3. FX detail (flat mode)
 *
 * Strategy: tests verify component structure and the absence of legacy markup.
 * Data-conditional checks use `test.info().annotations.push` (not `test.skip`)
 * when the data state is genuinely variable.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage} from '../assets/assets-helpers';
import {goToFxDetailPage} from '../fx/fx-helpers';
import {waitForSettled} from '../fixtures/app-events';

// ============================================================================
// Helpers
// ============================================================================

async function goToDashboard(page: import('@playwright/test').Page) {
    await page.goto('/dashboard');
    await page.waitForSelector('[data-testid="dashboard-page"]', {timeout: 15_000});
    await waitForSettled(page.getByTestId('dashboard-page'), 25_000);
}

async function goToAssetDetail(page: import('@playwright/test').Page, assetId: number) {
    await page.goto(`/assets/${assetId}`);
    await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 15_000});
}

async function goToFirstAssetDetail(page: import('@playwright/test').Page) {
    await goToAssetsPage(page);
    const firstCard = page.locator('[data-testid^="asset-card-"]').first();
    await expect(firstCard).toBeVisible({timeout: 8_000});
    await firstCard.click();
    await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 10_000});
    await waitForSettled(page.getByTestId('asset-detail-page'), 25_000);
}

/**
 * The grouped (dashboard) banner is foldable and collapsed by default — it shows only the
 * "N avviso/i" header until opened. Click the header toggle so issue rows / CTAs become visible.
 */
/**
 * Expand the banner and *stay* expanded.
 *
 * The lenient version below clicks once, which loses a race the injected-issue tests made
 * visible: the dashboard re-renders when the portfolio report lands, so a toggle clicked
 * before that lands is a toggle on a banner that is about to be replaced by a collapsed
 * one. Retrying until `aria-expanded` sticks is the fix.
 */
async function expandDataQualityBannerStrict(page: import('@playwright/test').Page) {
    const toggle = page.getByTestId('data-quality-toggle');
    await expect(toggle).toBeVisible({timeout: 20_000});
    await expect(async () => {
        if ((await toggle.getAttribute('aria-expanded')) !== 'true') {
            await toggle.click();
        }
        expect(await toggle.getAttribute('aria-expanded')).toBe('true');
    }).toPass({timeout: 15_000});
}

async function expandDataQualityBanner(page: import('@playwright/test').Page) {
    const toggle = page.getByTestId('data-quality-toggle');
    if (await toggle.isVisible({timeout: 3000}).catch(() => false)) {
        if ((await toggle.getAttribute('aria-expanded')) !== 'true') {
            await toggle.click();
        }
    }
}

/**
 * Force a data-quality issue into the dashboard's portfolio report.
 *
 * Why injection rather than seeding the database: these four tests used to check
 * `isVisible()` and, when the anomaly happened not to be in the fixture, annotate
 * themselves as "skipped" and report green — a test that verifies nothing is worse than
 * one that fails. Seeding the anomaly for real is the usual answer, but NAV_INCOMPLETE and
 * MISSING_PRICE are portfolio-wide: producing them means committing a transaction, which
 * moves the NAV that every concurrently running spec reads. That trades a silent hole for
 * an intermittent red elsewhere.
 *
 * What these tests actually own is the *rendering* contract — that an issue carrying a date
 * range shows it, that a per-asset issue renders one link per asset. Feeding the issue
 * through the real API response exercises exactly that, deterministically, without touching
 * shared state. Whether the engine emits the issue in the first place is a backend concern
 * and is covered there.
 */
async function injectDashboardIssues(page: import('@playwright/test').Page, issues: unknown[]) {
    await page.route('**/api/v1/portfolio/report', async (route) => {
        const response = await route.fetch();
        const body = await response.json();
        const summary = body?.summary;
        if (summary) {
            summary.data_quality = summary.data_quality ?? {issues: []};
            summary.data_quality.issues = [...(summary.data_quality.issues ?? []), ...issues];
        }
        await route.fulfill({response, json: body});
    });
}

/** First active asset, with its currency — the anchor for the event-currency FX branch. */
type ListedAsset = {id: number; currency: string; active: boolean; display_name?: string};

/**
 * Assets that the fixture seeds and that therefore have prices, events and a settled
 * detail page. Taking "the first active asset" instead is what took these tests red at
 * four workers: the listing is shared, so the first entry is whichever asset a
 * neighbouring spec created a second earlier — usually one with no data at all, whose
 * detail page has no event to attach an FX issue to.
 */
const SEEDED_ASSET_NAMES = [/apple/i, /microsoft/i, /nvidia/i];

function preferSeeded(assets: ListedAsset[], extra: (a: ListedAsset) => boolean = () => true): ListedAsset | undefined {
    const usable = assets.filter((a) => a.active && !!a.currency && extra(a));
    for (const pattern of SEEDED_ASSET_NAMES) {
        const hit = usable.find((a) => pattern.test(a.display_name ?? ''));
        if (hit) return hit;
    }
    return usable[0];
}

async function pickActiveAsset(page: import('@playwright/test').Page): Promise<{id: number; currency: string}> {
    const res = await page.request.get('/api/v1/assets/query');
    expect(res.ok(), 'asset listing must be reachable').toBeTruthy();
    const items = (await res.json()) as ListedAsset[];
    const asset = preferSeeded(items);
    expect(asset, 'fixture must contain at least one active asset with a currency').toBeTruthy();
    return {id: asset!.id, currency: asset!.currency};
}

/** An asset plus a currency it has a *configured* FX route with — the "no-data" precondition. */
async function pickAssetWithConfiguredCounterCurrency(page: import('@playwright/test').Page): Promise<{assetId: number; counterCurrency: string}> {
    const [assetsRes, routesRes] = await Promise.all([page.request.get('/api/v1/assets/query'), page.request.get('/api/v1/fx/providers/routes')]);
    expect(assetsRes.ok() && routesRes.ok(), 'assets and fx routes must be reachable').toBeTruthy();
    const assets = (await assetsRes.json()) as ListedAsset[];
    const routes = (((await routesRes.json()) as {items?: Array<{base: string; quote: string}>}).items ?? []).filter((r) => r.base && r.quote);
    expect(routes.length, 'fixture must configure at least one FX route').toBeGreaterThan(0);

    const asset = preferSeeded(assets, (a) => routes.some((r) => r.base === a.currency || r.quote === a.currency));
    if (!asset) throw new Error('no active asset shares a currency with a configured FX route');
    const route = routes.find((r) => r.base === asset.currency || r.quote === asset.currency)!;
    return {assetId: asset.id, counterCurrency: route.base === asset.currency ? route.quote : route.base};
}

/** Replace the configured FX routes seen by this page only. */
async function stubFxRoutes(page: import('@playwright/test').Page, items: Array<{base: string; quote: string}>) {
    await page.route('**/api/v1/fx/providers/routes*', async (route) => {
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({items})});
    });
}

/**
 * Append an unconverted event in `currency` to every price-query result.
 *
 * `original_value` is deliberately absent: that is exactly how the backend reports "conversion
 * was requested and failed" (schemas/prices.py:326), which is what `hasFailedConversion`
 * (assets/[id]/+page.svelte:501) reads.
 */
async function injectForeignEvent(page: import('@playwright/test').Page, currency: string) {
    await page.route('**/api/v1/assets/prices/query*', async (route) => {
        const response = await route.fetch();
        const body = await response.json();
        for (const item of body?.items ?? []) {
            item.events = [
                ...(item.events ?? []),
                {
                    date: '2024-06-03',
                    type: 'DIVIDEND',
                    value: {code: currency, amount: '12.34'},
                    id: 9_000_001,
                    is_auto: false,
                },
            ];
        }
        await route.fulfill({response, json: body});
    });
}

// ============================================================================
// Dashboard Banner Tests (grouped mode)
// ============================================================================

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('DataQualityBanner — Dashboard (grouped mode)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('dashboard loads without JS errors', async ({page}) => {
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await goToDashboard(page);
        expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
    });

    test('dashboard page structure is intact after banner migration', async ({page}) => {
        await goToDashboard(page);
        await expect(page.getByTestId('dashboard-page')).toBeVisible();
        await expect(page.getByTestId('kpi-row')).toBeVisible();
    });

    test('legacy inline banners are removed after migration', async ({page}) => {
        await goToDashboard(page);
        // Old testids that no longer exist
        await expect(page.getByTestId('dashboard-missing-prices-banner')).toHaveCount(0);
        await expect(page.getByTestId('dashboard-missing-fx-banner')).toHaveCount(0);
    });

    test('when data quality banner is present it is grouped with issue rows', async ({page}) => {
        await goToDashboard(page);
        const banner = page.getByTestId('data-quality-banner');
        const hasBanner = await banner.isVisible({timeout: 3000}).catch(() => false);

        if (hasBanner) {
            // Grouped mode: single container
            await expect(banner).toHaveCount(1);
            // Foldable: reveal the rows, then at least one issue row must be visible
            await expandDataQualityBanner(page);
            const issueRows = page.locator('[data-testid^="data-quality-issue-"]');
            await expect(issueRows.first()).toBeVisible();
        } else {
            test.info().annotations.push({type: 'info', description: 'No data quality issues in test DB — banner hidden (expected)'});
        }
    });

    test('header does not show "0 errors, 0 warnings" when only info issues present', async ({page}) => {
        await goToDashboard(page);
        const banner = page.getByTestId('data-quality-banner');
        const hasBanner = await banner.isVisible({timeout: 3000}).catch(() => false);

        if (hasBanner) {
            const headerText = await banner.locator('.font-medium').first().textContent();
            // Must not say "0 error" or "0 warning"
            expect(headerText ?? '').not.toMatch(/0 error/i);
            expect(headerText ?? '').not.toMatch(/0 warning/i);
        } else {
            test.info().annotations.push({type: 'info', description: 'No banner to check — skipped header test'});
        }
    });

    test('NAV incomplete issue renders the date range it carries', async ({page}) => {
        await injectDashboardIssues(page, [
            {
                domain: 'portfolio',
                code: 'NAV_INCOMPLETE',
                severity: 'info',
                message_i18n_key: 'dataQuality.navIncomplete',
                message_params: {count: 3, date_from: '2019-03-04', date_to: '2019-03-06'},
                count: 3,
                group_key: 'nav_incomplete',
            },
        ]);
        await goToDashboard(page);
        await expandDataQualityBannerStrict(page);

        const navIssue = page.getByTestId('data-quality-issue-NAV_INCOMPLETE');
        await expect(navIssue).toBeVisible({timeout: 10_000});
        // The dates come from message_params, so the banner has to interpolate them rather
        // than print the raw i18n key.
        await expect(navIssue).toContainText('2019-03-04');
        await expect(navIssue).toContainText('2019-03-06');
    });

    test('missing price issue renders one navigate link per affected asset', async ({page}) => {
        await injectDashboardIssues(page, [
            {
                domain: 'portfolio',
                code: 'MISSING_PRICE',
                severity: 'error',
                message_i18n_key: 'dataQuality.missingPrice',
                message_params: {count: 2},
                count: 2,
                affected_asset_ids: [901234, 901235],
                affected_asset_names: ['E2E Priceless One', 'E2E Priceless Two'],
                cta_action: 'navigate_asset',
                cta_target: '901234',
                group_key: 'missing_price',
            },
        ]);
        await goToDashboard(page);
        await expandDataQualityBannerStrict(page);

        await expect(page.getByTestId('data-quality-issue-MISSING_PRICE')).toBeVisible({timeout: 10_000});
        // navigate_asset issues render one "go to asset" link per affected asset — the count
        // is the assertion, because a single link for two assets was the original bug.
        const navLinks = page.locator('[data-testid^="data-quality-nav-asset-"]');
        await expect(navLinks).toHaveCount(2);
        await expect(navLinks.first()).toBeVisible();
    });
});

// ============================================================================
// Asset Detail Banner Tests (flat mode)
// ============================================================================

test.describe('DataQualityBanner — Asset Detail (flat mode)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('asset detail loads without JS errors after banner migration', async ({page}) => {
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await goToFirstAssetDetail(page);
        expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
    });

    test('legacy archived banner testid removed from asset detail', async ({page}) => {
        await goToFirstAssetDetail(page);
        // Old testid from pre-migration inline banner
        await expect(page.getByTestId('asset-archived-banner')).toHaveCount(0);
    });

    test('asset detail uses flat mode: no grouped banner container', async ({page}) => {
        await goToFirstAssetDetail(page);
        // Flat mode never renders a grouped "data-quality-banner" container
        await expect(page.getByTestId('data-quality-banner')).toHaveCount(0);
    });

    test('FX pair missing issue has add-fx-pair CTA in flat mode', async ({page}) => {
        // Reached through the *event currency* branch (assets/[id]/+page.svelte:483): an event
        // denominated in a currency other than the displayed one requires that FX pair. This is
        // the only branch drivable without the currency selector — `displayCurrency` starts
        // equal to the asset currency (:1052), and the selector only offers currencies that
        // already have a configured route, so "no route exists" is unreachable through it.
        const asset = await pickActiveAsset(page);
        const eventCurrency = asset.currency === 'USD' ? 'GBP' : 'USD';

        // No route configured at all => the required pair is missing.
        await stubFxRoutes(page, []);
        await injectForeignEvent(page, eventCurrency);

        await goToAssetDetail(page, asset.id);

        await expect(page.getByTestId('data-quality-issue-FX_PAIR_MISSING')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('data-quality-cta-FX_PAIR_MISSING')).toBeVisible();
    });

    test('FX pair no-data issue has navigate-fx CTA in flat mode', async ({page}) => {
        // Same branch, opposite half: the pair *is* configured but the event came back
        // unconverted (`original_value` absent). Picking the counter-currency from a real
        // configured route is what separates "no-data" from "missing".
        const pick = await pickAssetWithConfiguredCounterCurrency(page);
        await injectForeignEvent(page, pick.counterCurrency);

        await goToAssetDetail(page, pick.assetId);

        await expect(page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('data-quality-cta-FX_PAIR_NO_DATA')).toBeVisible();
    });
});

// ============================================================================
// FX Detail Banner Tests (flat mode)
// ============================================================================

test.describe('DataQualityBanner — FX Detail (flat mode)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('FX detail loads without JS errors after banner migration', async ({page}) => {
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await goToFxDetailPage(page, 'EUR-USD');
        await waitForSettled(page.getByTestId('fx-detail-page'), 25_000);
        expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
    });

    test('FX detail uses flat mode: no grouped banner container', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        // Flat mode never renders a grouped "data-quality-banner" container
        await expect(page.getByTestId('data-quality-banner')).toHaveCount(0);
    });

    test('range-before-data issue appears when URL date precedes first data', async ({page}) => {
        // Navigate with a very early date range to trigger the issue
        await page.goto('/fx/EUR-USD?start=2000-01-01&end=2000-12-31');
        await page.waitForSelector('[data-testid="fx-detail-page"]', {timeout: 15_000});
        await waitForSettled(page.getByTestId('fx-detail-page'), 25_000);

        const issue = page.getByTestId('data-quality-issue-RANGE_BEFORE_FIRST_DATA');
        const isVisible = await issue.isVisible({timeout: 3000}).catch(() => false);

        if (isVisible) {
            const text = await issue.textContent();
            // Message should contain a year (date of first available data)
            expect(text).toMatch(/\d{4}/);
        } else {
            test.info().annotations.push({type: 'info', description: 'EUR-USD data starts before 2000 — range issue not triggered'});
        }
    });
});
