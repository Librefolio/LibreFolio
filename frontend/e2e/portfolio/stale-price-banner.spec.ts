/**
 * STALE_PRICE banner on the dashboard — decision D8 (30/09), R2 step 13 item 9.
 *
 * Written RED-FIRST, before the fix. `get_summary` never passes `stale_prices_dto` (not since
 * the engine rewrite 77b976ebc), so a holding whose market price has been carried forward for
 * more than 7 days never reaches the «prezzi non aggiornati» banner. Until the backend half
 * lands this spec stops at the report assertion; the backend contract is specified in
 * `test_portfolio_service.py::TestStalePriceDataQuality`.
 *
 * The contract exercised end to end:
 *   1. the dashboard report flags the seeded asset as STALE_PRICE, CTA `sync_asset_prices`;
 *   2. the grouped banner renders that issue row with its aggregate CTA button;
 *   3. the CTA posts ONE item per affected asset to POST /assets/prices/sync, from `'resume'`
 *      (the backend's "day after the last stored price", the rule every auto-sync uses) to the
 *      dashboard's end date — the date the asset was judged stale at — and stays busy
 *      (disabled) while the sync runs;
 *   4. once the sync answers, the dashboard reloads its report and the CTA is usable again.
 *
 * Ownership. A disposable account owns the whole dashboard under test — its broker, a
 * DEPOSIT and a BUY — so no shared NAV moves under a neighbour, and "exactly one sync item"
 * is a count this spec created. The asset and its prices are global rows: unique name,
 * deleted by the fixture teardown (broker first — an asset with transactions cannot be
 * deleted), then the account itself.
 *
 * Offline. The asset is assigned `mockprov` with `INVALID_TICKER_12345`, the one identifier
 * the mock refuses for a current price. Any concurrent spec that opens /assets polls
 * POST /assets/prices/current for every listed asset, and a successful quote is written back
 * as today's price (`get_current_prices_bulk`, F.2) — an ordinary mockprov ticker would
 * silently turn our 10-day-old quote into a fresh one. The sync the CTA sends is intercepted
 * and answered with a canned FABulkRefreshResponse: no provider is called and no price is
 * written, so the reloaded report still flags the asset. This spec asserts that the dashboard
 * reloads, not what a real provider would have returned.
 */

import {expect, test as base, type APIRequestContext, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
const SYNC_PATH = `${API}/assets/prices/sync`;
/** mockprov.get_current_value raises NOT_FOUND for exactly this identifier: nothing is written back. */
const OFFLINE_IDENTIFIER = 'INVALID_TICKER_12345';
/** Market quotes, oldest first; the newest is 10 days old — past the 7-day threshold. */
const PRICE_DAYS_AGO = [40, 30, 20, 10] as const;
const LAST_PRICE_DAYS_AGO = 10;

type SyncItem = {asset_id: number; date_range: {start: string; end: string}};
type ReportRequestBody = {include_summary?: boolean; date_range?: {start?: string; end?: string}};
type ReportIssue = {code: string; severity: string; cta_action?: string | null; affected_asset_ids?: number[]};
type ReportHolding = {asset_id: number; valuation_source?: string | null; valuation_reference_date?: string | null};
type ReportBody = {summary?: {holdings?: ReportHolding[]; data_quality?: {issues?: ReportIssue[]} | null} | null};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

type Owned = {user: DisposableUser | null; brokerIds: number[]; assetIds: number[]};
type Seeded = {assetId: number; brokerId: number};
type SyncProbe = {
    /** Set just before the CTA click: only then is a sync request held behind `release`. */
    armed: boolean;
    /** Set just before the held sync is answered: every report request after it is a reload. */
    answered: boolean;
    bodies: SyncItem[][];
    unexpected: unknown[];
    release: () => void;
};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** The dashboard's own report load: the one request that carries the summary. */
function isSummaryReport(req: Request): boolean {
    if (req.method() !== 'POST' || new URL(req.url()).pathname !== REPORT_PATH) return false;
    return (req.postDataJSON() as ReportRequestBody | null)?.include_summary === true;
}

/**
 * Delete in dependency order, each step scoped to an id this test recorded.
 *
 * Routes go first: when a test fails while its sync is held, that handler never resumes, and
 * `ignoreErrors` detaches it instead of waiting on it. The dashboard is then unmounted so no
 * in-flight reload reads rows while they go. Broker and asset are deleted by the account that
 * created them (`page.request` shares the browser's session); the account itself is deleted
 * through the standalone `request` context it was registered with, which signs in on its own.
 */
async function cleanupOwned(page: Page, request: APIRequestContext, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    await attempt('detach routes', async () => {
        await page.unrouteAll({behavior: 'ignoreErrors'});
    });
    await attempt('unmount dashboard', async () => {
        await page.goto('about:blank');
    });
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete owned broker and its transactions');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete owned asset, its prices and its provider assignment');
            expect(result.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
        });
    }
    const user = owned.user;
    if (user) {
        await attempt(`account ${user.username}`, async () => {
            await deleteDisposableUser(request, user);
        });
    }
    expect(failures, 'every cleanup step is scoped to rows this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page, request}, use) => {
        const owned: Owned = {user: null, brokerIds: [], assetIds: []};
        try {
            await use(owned);
        } finally {
            await cleanupOwned(page, request, owned);
        }
    },
});

test.setTimeout(120_000);

/**
 * One EUR asset held by the signed-in account: priced by `mockprov` (offline), quoted until
 * 10 days ago, bought 40 days ago. Every id is recorded for cleanup before it is checked.
 */
async function seedStaleHolding(page: Page, owned: Owned): Promise<Seeded> {
    const suffix = uniqueSuffix();

    const brokerName = `stale-price-broker-${suffix}`;
    const brokers = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name: brokerName, opened_at: daysAgoIso(400)}]}), 'create owned broker');
    const broker = brokers.results.find((item) => item.name === brokerName);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);
    const brokerId = broker.broker_id;

    const assetName = `Stale price E2E ${suffix}`;
    const assetItem = {display_name: assetName, currency: 'EUR', asset_type: 'ETF', quote_base_quantity: 1, active: true};
    schemas.FAAssetCreateItem.parse(assetItem);
    const assets = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>}>(await page.request.post(`${API}/assets`, {data: [assetItem]}), 'create owned asset');
    const asset = assets.results.find((item) => item.display_name === assetName);
    if (typeof asset?.asset_id === 'number') owned.assetIds.push(asset.asset_id);
    if (!asset?.success || typeof asset.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(assets)}`);
    const assetId = asset.asset_id;

    const assignment = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(
        await page.request.post(`${API}/assets/provider`, {data: [{asset_id: assetId, provider_code: 'mockprov', identifier: OFFLINE_IDENTIFIER, identifier_type: 'TICKER', provider_params: null}]}),
        'assign the offline mock provider',
    );
    expect(assignment.results.find((item) => item.asset_id === assetId)?.success).toBe(true);

    const prices = PRICE_DAYS_AGO.map((days, index) => ({date: daysAgoIso(days), close: 100 + index, currency: 'EUR'}));
    const seededPrices = await jsonFrom<{results: Array<{asset_id: number; count: number}>}>(await page.request.post(`${API}/assets/prices`, {data: [{asset_id: assetId, prices}]}), 'seed market prices ending 10 days ago');
    expect(seededPrices.results.find((item) => item.asset_id === assetId)?.count).toBe(prices.length);

    const committed = await jsonFrom<{committed: boolean; issues?: unknown[]; results?: Array<{operation: string; ids: number[]}>}>(
        await page.request.post(`${API}/transactions/commit`, {
            data: {
                creates: [
                    {broker_id: brokerId, type: 'DEPOSIT', date: daysAgoIso(45), cash: {code: 'EUR', amount: '10000'}, description: `stale-price funding ${suffix}`},
                    {broker_id: brokerId, asset_id: assetId, type: 'BUY', date: daysAgoIso(40), quantity: '10', cash: {code: 'EUR', amount: '-1000'}, description: `stale-price purchase ${suffix}`},
                ],
            },
        }),
        'commit the owned DEPOSIT and BUY',
    );
    expect(committed.committed, `the owned transactions were rolled back: ${JSON.stringify(committed.issues ?? [])}`).toBe(true);

    return {assetId, brokerId};
}

/** A response of the real FABulkRefreshResponse shape. `ok` claims ten fresh quotes; nothing is written. */
function cannedSync(items: SyncItem[], status: 'ok' | 'failed') {
    const ok = status === 'ok';
    return {
        results: items.map(({asset_id}) => ({
            asset_id,
            status,
            provider_used: ok ? 'mockprov' : null,
            points_fetched: ok ? 10 : 0,
            points_changed: ok ? 10 : 0,
            inserted_count: ok ? 10 : 0,
            updated_count: 0,
            events_fetched: 0,
            events_changed: 0,
            message: null,
            errors: ok ? [] : ['Synthetic offline boundary: no sync performed'],
            elapsed_ms: 1,
            changed_points: null,
        })),
        success_count: ok ? items.length : 0,
        errors: [],
        date_range: items[0]?.date_range ?? null,
        total_points_changed: ok ? 10 * items.length : 0,
    };
}

/**
 * Intercept every asset sync this page sends, so no provider is ever reached.
 *
 * Before `armed` a sync is not the CTA's: it is answered at once as failed and recorded as
 * unexpected. Once armed, the request is held until `release()` — that window is what makes
 * the busy state observable without a clock.
 */
async function interceptAssetSync(page: Page): Promise<SyncProbe> {
    let open: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
        open = resolve;
    });
    const probe: SyncProbe = {armed: false, answered: false, bodies: [], unexpected: [], release: () => open()};
    await page.route(`**${SYNC_PATH}`, async (route) => {
        const items = route.request().postDataJSON() as SyncItem[];
        if (!probe.armed) {
            probe.unexpected.push(items);
            await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(cannedSync(items, 'failed'))});
            return;
        }
        probe.bodies.push(items);
        await gate;
        const body = cannedSync(items, 'ok');
        schemas.FABulkRefreshResponse.parse(body);
        probe.answered = true;
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
    });
    return probe;
}

/**
 * Open the grouped banner and make sure it *stays* open.
 *
 * It is collapsed by default, and the dashboard re-renders when its report lands, so a single
 * click can land on a banner that is about to be replaced. Toggle only when collapsed, until
 * `aria-expanded` sticks — never a blind click.
 */
async function expandBanner(page: Page): Promise<void> {
    const toggle = page.getByTestId('data-quality-toggle');
    await expect(toggle).toBeVisible({timeout: 20_000});
    await expect(async () => {
        if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
        expect(await toggle.getAttribute('aria-expanded')).toBe('true');
    }).toPass({timeout: 15_000});
}

test.describe('STALE_PRICE banner — dashboard (D8)', () => {
    test('a provider-priced holding last quoted 10 days ago is flagged, and its CTA syncs that asset and reloads', async ({page, request, owned}) => {
        // The account owns the whole dashboard; its guides are skipped so no overlay covers the
        // banner. Registered through the standalone `request` context, like the guide specs:
        // the browser signs in through the real login form.
        const user = await registerDisposableUser(request, 'stale');
        owned.user = user;
        await prepareOnboardingAccount(page, user, []);
        const seeded = await seedStaleHolding(page, owned);
        const sync = await interceptAssetSync(page);

        // Full load: the URL range seeds the dashboard's date store; the load is a fresh
        // document, so its report cannot come from a client cache.
        const firstReport = page.waitForResponse((response) => isSummaryReport(response.request()), {timeout: 30_000});
        await page.goto(`/dashboard?start=${daysAgoIso(90)}&end=${todayIso()}`);
        const reportResponse = await firstReport;
        const range = (reportResponse.request().postDataJSON() as ReportRequestBody).date_range;
        expect(range?.end, 'precondition: the dashboard range ends today').toBe(todayIso());
        const report = await jsonFrom<ReportBody>(reportResponse, 'dashboard report');

        // Precondition, verified rather than inferred: the dashboard values the holding at the
        // seeded market quote of 10 days ago — nothing refreshed it in the meantime.
        const holding = report.summary?.holdings?.find((item) => item.asset_id === seeded.assetId);
        expect(holding, 'precondition: the dashboard lists the seeded holding').toBeTruthy();
        expect(holding).toMatchObject({valuation_source: 'MARKET_PRICE', valuation_reference_date: daysAgoIso(LAST_PRICE_DAYS_AGO)});

        // 1. D8 — red until get_summary passes stale_prices_dto.
        const issues = report.summary?.data_quality?.issues ?? [];
        const staleIssue = issues.find((issue) => issue.code === 'STALE_PRICE');
        expect(staleIssue, `D8: the report must flag the seeded asset as STALE_PRICE; it carries ${JSON.stringify(issues.map((issue) => issue.code))}`).toBeTruthy();
        expect(staleIssue).toMatchObject({severity: 'warning', cta_action: 'sync_asset_prices', affected_asset_ids: [seeded.assetId]});

        // 2. The banner renders the issue with the aggregate CTA (not per-asset links).
        const dashboard = page.getByTestId('dashboard-page');
        await waitForSettled(dashboard, 25_000);
        await expandBanner(page);
        const row = page.getByTestId('data-quality-issue-STALE_PRICE');
        await expect(row).toBeVisible({timeout: 10_000});
        await expect(row).toHaveAttribute('data-severity', 'warning');
        const cta = row.getByTestId('data-quality-cta-STALE_PRICE');
        await expect(cta).toBeVisible();
        await expect(cta).toBeEnabled();
        expect(sync.unexpected, 'nothing may sync before the user asks').toEqual([]);

        // 3. The CTA syncs exactly the affected asset, from the day after its last stored price
        //    ('resume') to the dashboard's end date, and is busy meanwhile.
        sync.armed = true;
        const syncRequest = page.waitForRequest((req) => req.method() === 'POST' && new URL(req.url()).pathname === SYNC_PATH, {timeout: 10_000});
        const reloadRequest = page.waitForRequest((req) => sync.answered && isSummaryReport(req), {timeout: 30_000});
        await cta.click();
        const sent = (await syncRequest).postDataJSON() as SyncItem[];
        for (const item of sent) schemas.FARefreshItem.parse(item);
        expect(sent).toEqual([{asset_id: seeded.assetId, date_range: {start: 'resume', end: range?.end}}]);
        await expect(cta, 'the CTA is busy while its sync runs').toBeDisabled();

        // 4. Once the sync answers, the dashboard reloads and the CTA is usable again.
        sync.release();
        await reloadRequest;
        await waitForSettled(dashboard, 25_000);
        await expandBanner(page);
        await expect(cta, 'the busy state ends with the sync').toBeEnabled({timeout: 10_000});
        expect(sync.bodies, 'one click, one sync').toHaveLength(1);
        expect(sync.unexpected).toEqual([]);
    });
});
