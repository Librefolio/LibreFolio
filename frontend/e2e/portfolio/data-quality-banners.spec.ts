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

import {expect, test, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage} from '../assets/assets-helpers';
import {goToFxDetailPage} from '../fx/fx-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, todayIso} from '../fixtures/dates';

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
 *
 * Real issues sharing a code with an injected one are dropped before the append, as in
 * `serveMissingFxRates`: the rows a test asserts on must be unique. The banner keys its rows by
 * `code + group_key` and its test ids carry the code alone, so a real twin would either collide
 * with the injected row in the keyed list or leave `data-quality-issue-{code}` naming two rows.
 */
async function injectDashboardIssues(page: import('@playwright/test').Page, issues: Array<{code: string; [field: string]: unknown}>) {
    const injectedCodes = new Set(issues.map((issue) => issue.code));
    await page.route('**/api/v1/portfolio/report', async (route) => {
        const response = await route.fetch();
        const body = await response.json();
        const summary = body?.summary;
        if (summary) {
            summary.data_quality = summary.data_quality ?? {issues: []};
            const kept = ((summary.data_quality.issues ?? []) as Array<{code?: string}>).filter((existing) => !injectedCodes.has(existing.code ?? ''));
            summary.data_quality.issues = [...kept, ...issues];
        }
        await route.fulfill({response, json: body});
    });
}

// ----------------------------------------------------------------------------
// MISSING_FX_RATES «Sync rates» — what the dashboard CTA asks the provider for
// ----------------------------------------------------------------------------

const REPORT_PATH = '/api/v1/portfolio/report';
const FX_SYNC_PATH = '/api/v1/fx/currencies/sync';

type FxSyncBody = {pairs: string[]; start: string; end: string};

/**
 * The issue portfolio_engine emits for a configured real-provider pair whose rates are missing
 * on some dates: `date_from`/`date_to` span every missing date of every affected pair.
 */
function missingFxRatesIssue(dateFrom: string, dateTo: string, datesCount: number) {
    return {
        domain: 'portfolio',
        code: 'MISSING_FX_RATES',
        severity: 'warning',
        message_i18n_key: 'dataQuality.missingFxRates',
        message_params: {count: 1, date_from: dateFrom, date_to: dateTo, dates_count: datesCount},
        count: 1,
        affected_fx_pairs: ['EUR-USD'],
        cta_action: 'sync_fx_pair',
        cta_target: 'EUR-USD',
        group_key: 'missing_fx_rates',
    };
}

type FxSyncProbe = {
    bodies: FxSyncBody[];
    /** Set just before the held sync is answered: a report requested after it is the reload. */
    answered: boolean;
    release: () => void;
};

/**
 * Hold every FX sync this page sends until `release()`, then answer it with a canned success.
 *
 * No provider is ever reached and no rate is written: the dashboard is shared, and what is
 * under test is the request the CTA builds and what the page does with the answer. Holding
 * the request is what makes the busy state observable without a clock.
 */
async function holdFxSync(page: Page): Promise<FxSyncProbe> {
    let open: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
        open = resolve;
    });
    const probe: FxSyncProbe = {bodies: [], answered: false, release: () => open()};
    await page.route(`**${FX_SYNC_PATH}`, async (route) => {
        const body = route.request().postDataJSON() as FxSyncBody;
        probe.bodies.push(body);
        await gate;
        const answer = {
            results: [{pair: 'EUR-USD', status: 'ok', points_fetched: 5, points_changed: 5, provider_used: 'ECB'}],
            success_count: 1,
            date_range: {start: body.start, end: body.end},
            total_points_changed: 5,
        };
        schemas.FXSyncBulkResponse.parse(answer);
        probe.answered = true;
        await route.fulfill({json: answer});
    });
    return probe;
}

/**
 * Own the MISSING_FX_RATES rows of every dashboard report this page receives.
 *
 * Whatever the backend reported under that code is stripped first. The grouped banner keys its
 * rows by code + group_key, so a second row with our key would crash the list; and the CTA test
 * id carries the code alone, so a second MISSING_FX_RATES row (the MANUAL group) would make the
 * CTA ambiguous. `issue` is then appended to every report requested before the sync was answered
 * — and to the reload too when `keepAfterSync`: the provider had nothing for those dates.
 */
async function serveMissingFxRates(page: Page, issue: ReturnType<typeof missingFxRatesIssue>, sync: FxSyncProbe, keepAfterSync: boolean): Promise<void> {
    await page.route(`**${REPORT_PATH}`, async (route) => {
        // Decided when the request leaves the page, not when its answer comes back.
        const inject = !sync.answered || keepAfterSync;
        const response = await route.fetch();
        const body = await response.json();
        const summary = body?.summary;
        if (summary) {
            summary.data_quality = summary.data_quality ?? {issues: []};
            const kept = ((summary.data_quality.issues ?? []) as Array<{code?: string}>).filter((existing) => existing.code !== issue.code);
            summary.data_quality.issues = inject ? [...kept, issue] : kept;
        }
        await route.fulfill({response, json: body});
    });
}

/** The dashboard's own report load: the one request that carries the summary (and its issues). */
function isSummaryReport(req: Request): boolean {
    if (req.method() !== 'POST' || new URL(req.url()).pathname !== REPORT_PATH) return false;
    return (req.postDataJSON() as {include_summary?: boolean} | null)?.include_summary === true;
}

/** Open the dashboard on its own banner, and return the one MISSING_FX_RATES CTA this test owns. */
async function openMissingFxRatesCta(page: Page) {
    await goToDashboard(page);
    await expandDataQualityBannerStrict(page);
    const row = page.getByTestId('data-quality-issue-MISSING_FX_RATES');
    await expect(row, 'every other MISSING_FX_RATES row is stripped: this one is ours').toHaveCount(1);
    const cta = row.getByTestId('data-quality-cta-MISSING_FX_RATES');
    await expect(cta).toBeEnabled();
    return cta;
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
            // A sibling navigate_asset issue under another code: its link shares the page and the
            // test-id prefix with MISSING_PRICE's, so the scoping below is proven against a
            // neighbour this test owns rather than against whatever the seed happens to report.
            {
                domain: 'portfolio',
                code: 'TRANSACTION_IMPLIED',
                severity: 'warning',
                message_i18n_key: 'dataQuality.transactionImplied',
                message_params: {count: 1, as_of_date: '2024-06-28'},
                count: 1,
                affected_asset_ids: [901236],
                affected_asset_names: ['E2E Priceless Three'],
                cta_action: 'navigate_asset',
                cta_target: '901236',
                group_key: 'transaction_implied',
            },
        ]);
        await goToDashboard(page);
        await expandDataQualityBannerStrict(page);

        const row = page.getByTestId('data-quality-issue-MISSING_PRICE');
        await expect(row).toBeVisible({timeout: 10_000});
        // navigate_asset issues render one "go to asset" link per affected asset — the count is
        // the assertion, because a single link for two assets was the original bug. It is taken
        // inside this row: every navigate_asset issue renders its links under the same test-id
        // prefix, and other issues' links share the page (the seed's MISSING_COST_BASIS is one).
        const navLinks = row.getByTestId('data-quality-nav-assets-MISSING_PRICE').locator('[data-testid^="data-quality-nav-asset-"]');
        await expect(navLinks).toHaveCount(2);
        await expect(row.getByTestId('data-quality-nav-asset-901234')).toBeVisible();
        await expect(row.getByTestId('data-quality-nav-asset-901235')).toBeVisible();

        // Another issue's link is on the page too, in its own row: the count above left it out
        // by scope, not because the page had nothing else to count.
        await expect(page.getByTestId('data-quality-issue-TRANSACTION_IMPLIED').getByTestId('data-quality-nav-asset-901236')).toBeVisible();
    });

    // «Sync rates» on MISSING_FX_RATES. The missing dates all precede the first stored rate of
    // the pair (the conversion backfills without limit, so a date is missing only when nothing
    // exists before it), which is why syncing the period on screen never reached them. The CTA
    // syncs the dates the issue carries instead, a week either side so a weekend or a holiday
    // at an edge resolves to the previous working day, and never past today (the backend
    // rejects a future end with a 400).

    test('MISSING_FX_RATES «Sync rates» syncs the missing dates a week either side, then reloads and reports', async ({page}) => {
        test.setTimeout(90_000);
        const sync = await holdFxSync(page);
        await serveMissingFxRates(page, missingFxRatesIssue('2022-11-03', '2023-06-27', 9), sync, false);
        try {
            const cta = await openMissingFxRatesCta(page);
            expect(sync.bodies, 'nothing syncs before the user asks').toEqual([]);

            const since = await eventSeq(page);
            await cta.click();
            await expect.poll(() => sync.bodies.length).toBe(1);
            expect(sync.bodies[0]).toEqual({pairs: ['EUR-USD'], start: '2022-10-27', end: '2023-07-04'});
            await expect(cta, 'the CTA is busy while its sync runs').toBeDisabled();
            await expect(page.getByTestId('dashboard-page')).toHaveAttribute('data-busy', 'true');

            const reload = page.waitForRequest((req) => sync.answered && isSummaryReport(req), {timeout: 30_000});
            sync.release();
            await reload;
            const synced = await waitForEvent(page, 'fx.rates.synced', {since, timeout: 30_000});
            expect(synced.detail).toMatchObject({origin: 'dashboard-banner', pairs: ['EUR-USD'], start: '2022-10-27', end: '2023-07-04', outcome: 'ok', stillMissing: false});
            await waitForSettled(page.getByTestId('dashboard-page'), 25_000);
            expect(sync.bodies, 'one click, one sync').toHaveLength(1);
        } finally {
            sync.release();
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    test('MISSING_FX_RATES «Sync rates» caps a recent last missing date at today', async ({page}) => {
        test.setTimeout(90_000);
        const sync = await holdFxSync(page);
        await serveMissingFxRates(page, missingFxRatesIssue(daysAgoIso(30), daysAgoIso(2), 2), sync, false);
        try {
            const cta = await openMissingFxRatesCta(page);

            const since = await eventSeq(page);
            await cta.click();
            await expect.poll(() => sync.bodies.length).toBe(1);
            const expected = {pairs: ['EUR-USD'], start: daysAgoIso(37), end: todayIso()};
            expect(sync.bodies[0]).toEqual(expected);

            sync.release();
            const synced = await waitForEvent(page, 'fx.rates.synced', {since, timeout: 30_000});
            expect(synced.detail).toMatchObject({origin: 'dashboard-banner', ...expected, outcome: 'ok', stillMissing: false});
        } finally {
            sync.release();
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    test('MISSING_FX_RATES dates still missing after the sync are reported, with a warning', async ({page}) => {
        test.setTimeout(90_000);
        const sync = await holdFxSync(page);
        // The reload still carries the issue: the provider published nothing for those dates.
        await serveMissingFxRates(page, missingFxRatesIssue('2022-11-03', '2023-06-27', 9), sync, true);
        try {
            const cta = await openMissingFxRatesCta(page);

            const since = await eventSeq(page);
            await cta.click();
            await expect.poll(() => sync.bodies.length).toBe(1);
            expect(sync.bodies[0]?.pairs).toEqual(['EUR-USD']);

            const reload = page.waitForRequest((req) => sync.answered && isSummaryReport(req), {timeout: 30_000});
            sync.release();
            await reload;
            const synced = await waitForEvent(page, 'fx.rates.synced', {since, timeout: 30_000});
            expect(synced.detail).toMatchObject({origin: 'dashboard-banner', pairs: ['EUR-USD'], outcome: 'ok', stillMissing: true});
            // The variant is the contract, not the sentence. Any warning will do: a per-pair
            // toast may be on screen beside it.
            await expect(page.getByTestId('toast-warning').first()).toBeVisible();
        } finally {
            sync.release();
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
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
