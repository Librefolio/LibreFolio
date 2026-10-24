/**
 * Data quality on real data — checklist «Costo d'acquisto e P&L», items 21, 22 and 23 of release 1.2 (issue #32).
 *
 * `data-quality-banners.spec.ts` covers how the banners render issues the test injects into the report. Here no
 * issue is injected: every one comes from the engine, on data the test writes through the API, and the
 * assertions follow it from the report to the screen.
 *
 *   E1 — item 21: a missing rate is reported, never counted at zero. An EUR asset is bought and partly sold with
 *        cash in a currency whose pair is served by a real provider but has no rate yet. The report raises
 *        MISSING_FX_RATES with the pair and the two movement days; the banner shows them; P&L, P&L % and average
 *        cost are a dash in the positions; the lots panel reports the same. «Sync rates» asks the provider for
 *        those days a week either side, the rate of the first day is stored as is, the report heals, the figures
 *        come back — and the lots panel that was already open asks again by itself (decision D2). D2 was written
 *        red-first: until «Sync rates» bumps the dashboard's `refreshVersion`, the signal `LotsAnalysisPanel`
 *        already listens to, the open panel keeps the answer it had.
 *   E2 — item 22, the path P-10 closed (decision 27): an ADJUSTMENT linked to a SPLIT is saved in Auto without a
 *        cost of its own; if its event became a PRICE_ADJUSTMENT, the row would be an acquisition of unknown cost.
 *        That retype is refused while the row has no cost — 409 EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST, naming the
 *        split, its date and the row — and nothing changes: 20 shares at an average cost of 50, with figures on
 *        the dashboard and on the broker page, and no unknown cost in the report, the banner or the lots panel.
 *        With a cost of 0 per unit on the row the same retype goes through, and nothing is unknown either. The
 *        banner on units of unknown cost (item 22 itself) is proven on the rows an older version left behind, the
 *        only ones left: `data-quality-legacy.spec.ts`.
 *   E3 — item 23: the tooltip of «Unrealized change» splits the period's change by asset currency into what the
 *        assets did and what the exchange rate did to their cost, in the backend's order and to the cent.
 *
 * Ownership. Each test registers its own account, and the account owns the whole dashboard under test: the issues,
 * positions and tooltip rows asserted on are exactly the ones the test created. Brokers (with their transactions),
 * assets (with their prices and events) and the account are deleted by id in the fixture teardown. FX rates and
 * routes are global tables, so each FX test reserves one currency per Playwright project — sorting after EUR, so
 * the stored MOCKFX rate is exactly 1.2345, and used by no other test, seed or spec — deletes its leftovers first,
 * verifies the pair is empty, and deletes its rates and route at the end.
 *
 * Offline. The provider behind «Sync rates» is MOCKFX, a registered test provider that answers every calendar day
 * with 1.2345 for any currency, so the real sync runs end to end without the network. Nothing is routed or mocked:
 * every request and response asserted on is the application's own. The scheduler is off in test runs, so nothing
 * syncs unless the test asks — and E1 checks that nothing did before the click.
 */

import {expect, test as base, type APIRequestContext, type Locator, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
const LOTS_PATH = `${API}/portfolio/lots/analysis`;
const FX_SYNC_PATH = `${API}/fx/currencies/sync`;
const FX_RATE_PATH = `${API}/fx/currencies/rate`;
const FX_CONVERT_PATH = `${API}/fx/currencies/convert`;
const FX_ROUTES_PATH = `${API}/fx/providers/routes`;

/** The dashboard period of every test: it starts before the first movement and ends today. */
const PERIOD_START_DAYS_AGO = 90;
/** The positions cells that must read a dash, never a zero, while the cost they derive from is unknown. */
const COST_COLUMNS = ['pnl', 'pnl-percent', 'pmc'] as const;
/** What ExposureTable renders for a null figure. */
const DASH = '—';
/** How long, from the click on «Sync rates», the open lots panel has to ask again (D2). */
const LOTS_REFRESH_TIMEOUT_MS = 45_000;

/**
 * Currencies reserved for this spec, one per Playwright project, because FX rates and routes are global rows.
 * Each sorts after EUR, so the pair is stored as EUR-X and the MOCKFX rate (1 EUR = 1.2345 X) is kept exactly,
 * with no inversion; none is used by any other test, seed or spec. The runner runs the desktop project only;
 * the mobile codes exist so that a manual run of both projects never shares a pair.
 */
const RESERVED_CURRENCIES = {
    missingRate: {desktop: 'MKD', mobile: 'RSD'},
    breakdown: {desktop: 'KZT', mobile: 'UAH'},
} as const;

type Money = {code: string; amount: string};
type ReportIssue = {
    code: string;
    severity: string;
    message_params?: Record<string, unknown> | null;
    affected_fx_pairs?: string[] | null;
    affected_asset_ids?: number[] | null;
    affected_asset_names?: string[] | null;
    cta_action?: string | null;
};
type ReportHolding = {asset_id: number; broker_id?: number | null; quantity?: string | null; wac_per_unit?: string | null; gain_loss?: string | null; gain_loss_percent?: string | null};
type BreakdownRow = {kind: string; asset_currency: string; period_delta: Money};
type ReportBody = {
    metadata?: {target_currency?: string} | null;
    summary?: {
        holdings?: ReportHolding[];
        data_quality?: {issues?: ReportIssue[]} | null;
        period_unrealized_breakdown?: BreakdownRow[];
        period_unrealized_gain_loss_delta?: Money | null;
    } | null;
};
type ReportRequestBody = {include_summary?: boolean; date_range?: {start?: string; end?: string} | null};
type LotsRequestBody = {asset_id?: number; requested_analyses?: string[]};
type LotsBody = {lots?: Array<{lot_id: number}> | null; data_quality?: {issues?: ReportIssue[]} | null};
type CommitBody = {committed: boolean; issues?: unknown[]; results?: Array<{operation: string; index: number; ids: number[]}>};
type TransactionRead = {id: number; asset_event_id?: number | null; cost_basis_override?: Money | null};
/** A refused events save: the code and where it is, never only a sentence (decision 22). */
type EventRefusalBody = {detail?: {error_code?: string; message?: string; params?: Record<string, unknown> | null} | null};
type ConvertBody = {results: Array<{conversion_date: string; to_amount: Money; backward_fill_info?: unknown}>};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

type Owned = {user: DisposableUser | null; brokerIds: number[]; assetIds: number[]; fxQuotes: string[]};
type DashboardLoad = {range: ReportRequestBody['date_range']; report: ReportBody; lots: LotsBody | null};
type SyncWatch = {
    /** «Sync rates» requests sent before the click: there must be none. */
    sentBeforeClick: number;
    /** Set just before the click. */
    clicked: boolean;
    /** Set when the sync's answer reaches the page: every request sent after it is a consequence of the sync. */
    answered: boolean;
};

/**
 * A wait armed before the action and awaited later. If the test fails in between, the pending wait would reject
 * unobserved when the page closes, and that noise would be reported beside the real failure; awaiting the
 * returned promise still throws as usual.
 */
function armed<T>(wait: Promise<T>): Promise<T> {
    wait.catch(() => undefined);
    return wait;
}

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** The dashboard's own report load: the one request that carries the summary. */
function isSummaryReport(req: Request): boolean {
    if (req.method() !== 'POST' || new URL(req.url()).pathname !== REPORT_PATH) return false;
    return (req.postDataJSON() as ReportRequestBody | null)?.include_summary === true;
}

/** The lots panel's main analysis of `assetId`: the answer its lots and its data-quality banner come from. */
function isMainLotsRequest(req: Request, assetId: number): boolean {
    if (req.method() !== 'POST' || new URL(req.url()).pathname !== LOTS_PATH) return false;
    const body = req.postDataJSON() as LotsRequestBody | null;
    return body?.asset_id === assetId && (body.requested_analyses ?? []).includes('LOT_SUMMARY');
}

function isFxSync(req: Request): boolean {
    return req.method() === 'POST' && new URL(req.url()).pathname === FX_SYNC_PATH;
}

function reportIssues(report: ReportBody): ReportIssue[] {
    return report.summary?.data_quality?.issues ?? [];
}

function lotIssues(lots: LotsBody | null): ReportIssue[] {
    return lots?.data_quality?.issues ?? [];
}

function numberOrNull(value: string | number | null | undefined): number | null {
    return value == null ? null : Number(value);
}

function digitsOf(text: string | null): string {
    return (text ?? '').replace(/\D/g, '');
}

function holdingOf(report: ReportBody, assetId: number, brokerId: number): ReportHolding {
    const holdings = report.summary?.holdings ?? [];
    const holding = holdings.find((item) => item.asset_id === assetId && item.broker_id === brokerId);
    if (!holding) throw new Error(`The report lists no holding for asset ${assetId} on broker ${brokerId}; it lists ${JSON.stringify(holdings.map((item) => [item.asset_id, item.broker_id]))}`);
    return holding;
}

/** The three figures a missing cost must leave unknown, as numbers (null stays null). */
function costFigures(holding: ReportHolding): {wac_per_unit: number | null; gain_loss: number | null; gain_loss_percent: number | null} {
    return {wac_per_unit: numberOrNull(holding.wac_per_unit), gain_loss: numberOrNull(holding.gain_loss), gain_loss_percent: numberOrNull(holding.gain_loss_percent)};
}

function reservedCurrency(purpose: keyof typeof RESERVED_CURRENCIES): string {
    const project = test.info().project.name;
    const byProject: Readonly<Record<string, string>> = RESERVED_CURRENCIES[purpose];
    const code = byProject[project];
    if (!code) throw new Error(`No currency is reserved for "${purpose}" on project "${project}": reserve one that sorts after EUR and that no other test, seed or spec uses`);
    return code;
}

// ---------------------------------------------------------------------------
// FX pair: reset, configure, probe
// ---------------------------------------------------------------------------

/** Delete every rate and every route of EUR-`quote`. Both deletions succeed (with a count of 0) when there is nothing. */
async function deleteReservedPair(page: Page, quote: string): Promise<void> {
    const rates = await jsonFrom<{results: Array<{base: string; quote: string; success: boolean}>}>(await page.request.delete(FX_RATE_PATH, {data: [{from: 'EUR', to: quote, delete_all: true}]}), `delete every EUR-${quote} rate`);
    expect(rates.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `delete every EUR-${quote} rate`).toBe(true);
    const routes = await jsonFrom<{results: Array<{base: string; quote: string; success: boolean}>}>(await page.request.delete(FX_ROUTES_PATH, {data: [{base: 'EUR', quote}]}), `delete the EUR-${quote} routes`);
    expect(routes.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `delete the EUR-${quote} routes`).toBe(true);
}

function convertOnDay(page: Page, from: string, amount: string, to: string, day: string) {
    return page.request.post(FX_CONVERT_PATH, {data: [{from_amount: {code: from, amount}, to, date_range: {start: day}}]});
}

/** Start from an empty reserved pair — leftovers of an interrupted run deleted — and verify it, not infer it. */
async function resetReservedPair(page: Page, quote: string): Promise<void> {
    await deleteReservedPair(page, quote);
    const routes = await jsonFrom<{items?: Array<{base: string; quote: string}>}>(await page.request.get(FX_ROUTES_PATH), 'list the FX routes');
    expect(
        (routes.items ?? []).filter((route) => route.base === 'EUR' && route.quote === quote),
        `precondition: no EUR-${quote} route is configured`,
    ).toEqual([]);
    const probe = await convertOnDay(page, quote, '1', 'EUR', todayIso());
    expect(probe.status(), `precondition: no EUR-${quote} rate exists, so converting ${quote} today must fail — got ${await probe.text()}`).toBe(404);
}

/** EUR-`quote` served by MOCKFX alone: a real provider, so the dashboard offers «Sync rates» for it. */
async function createMockFxRoute(page: Page, quote: string): Promise<void> {
    const route = {base: 'EUR', quote, priority: 1, chain_steps: [{from: 'EUR', to: quote, provider: 'MOCKFX'}]};
    schemas.FXConversionRouteItem.parse(route);
    const response = await page.request.post(FX_ROUTES_PATH, {data: [route]});
    expect(response.status(), `create the EUR-${quote} MOCKFX route: ${await response.text()}`).toBe(201);
    const body = (await response.json()) as {results: Array<{base: string; quote: string; success: boolean}>};
    expect(body.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `the EUR-${quote} route is stored`).toBe(true);
}

/** Rates typed in by hand (source MANUAL), as the user would: EUR sorts first, so they are stored as given. */
async function storeManualRates(page: Page, quote: string, points: Array<{date: string; rate: string}>): Promise<void> {
    const rates = points.map((point) => ({date: point.date, base: 'EUR', quote, rate: point.rate}));
    for (const rate of rates) schemas.FXUpsertItem.parse(rate);
    const stored = await jsonFrom<{results: Array<{success: boolean; date: string; base: string; quote: string; rate: string}>}>(await page.request.post(FX_RATE_PATH, {data: rates}), `store the EUR-${quote} rates`);
    expect(
        stored.results.map((item) => ({success: item.success, date: item.date, base: item.base, quote: item.quote, rate: Number(item.rate)})),
        `every EUR-${quote} rate is stored as given`,
    ).toEqual(rates.map((rate) => ({success: true, date: rate.date, base: 'EUR', quote, rate: Number(rate.rate)})));
}

// ---------------------------------------------------------------------------
// Owned rows: seeding and cleanup
// ---------------------------------------------------------------------------

/** Every id is recorded for cleanup before it is checked. */
async function createBroker(page: Page, owned: Owned, name: string, options: {allow_cash_overdraft?: boolean} = {}): Promise<number> {
    const brokers = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: daysAgoIso(400), ...options}]}), 'create an owned broker');
    const broker = brokers.results.find((item) => item.name === name);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);
    return broker.broker_id;
}

/** A manual asset: no provider, so nothing ever prices it but the quotes this test stores. */
async function createManualAsset(page: Page, owned: Owned, name: string, currency: string): Promise<number> {
    const item = {display_name: name, currency, asset_type: 'ETF', quote_base_quantity: 1, active: true};
    schemas.FAAssetCreateItem.parse(item);
    const assets = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>}>(await page.request.post(`${API}/assets`, {data: [item]}), 'create an owned asset');
    const asset = assets.results.find((result) => result.display_name === name);
    if (typeof asset?.asset_id === 'number') owned.assetIds.push(asset.asset_id);
    if (!asset?.success || typeof asset.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(assets)}`);
    return asset.asset_id;
}

async function seedPrices(page: Page, assetId: number, prices: Array<{date: string; close: number; currency: string}>): Promise<void> {
    const seeded = await jsonFrom<{results: Array<{asset_id: number; count: number}>}>(await page.request.post(`${API}/assets/prices`, {data: [{asset_id: assetId, prices}]}), 'seed the asset prices');
    expect(seeded.results.find((item) => item.asset_id === assetId)?.count, 'every price is stored').toBe(prices.length);
}

async function commitTransactions(page: Page, batch: {creates?: unknown[]; updates?: unknown[]}, purpose: string): Promise<CommitBody> {
    const committed = await jsonFrom<CommitBody>(await page.request.post(`${API}/transactions/commit`, {data: batch}), purpose);
    expect(committed.committed, `${purpose}: rolled back — ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
    return committed;
}

function createdId(committed: CommitBody, index: number): number {
    const id = committed.results?.find((item) => item.operation === 'create' && item.index === index)?.ids[0];
    if (typeof id !== 'number') throw new Error(`The commit returned no id for create #${index}: ${JSON.stringify(committed.results)}`);
    return id;
}

async function readTransaction(page: Page, id: number): Promise<TransactionRead> {
    const rows = await jsonFrom<TransactionRead[]>(await page.request.get(`${API}/transactions?ids=${id}`), `read transaction ${id}`);
    const row = rows.find((candidate) => candidate.id === id);
    if (!row) throw new Error(`GET /transactions?ids=${id} did not return the transaction: ${JSON.stringify(rows)}`);
    return row;
}

async function eventsOn(page: Page, assetId: number, day: string): Promise<Array<{id: number; type: string}>> {
    const body = await jsonFrom<{items: Array<{asset_id: number; events: Array<{id: number; type: string}>}>}>(await page.request.post(`${API}/assets/events/query`, {data: [{asset_id: assetId, date_range: {start: day, end: day}}]}), `query the events of asset ${assetId} on ${day}`);
    const item = body.items.find((candidate) => candidate.asset_id === assetId);
    return (item?.events ?? []).map((event) => ({id: event.id, type: event.type}));
}

/** A SPLIT carries its ratio in `value`; its currency is the asset's and means nothing. */
async function createSplitEvent(page: Page, assetId: number, day: string, ratio: string): Promise<number> {
    await jsonFrom(await page.request.post(`${API}/assets/events`, {data: [{asset_id: assetId, events: [{date: day, type: 'SPLIT', value: {code: 'EUR', amount: ratio}}]}]}), 'create the SPLIT event');
    const events = await eventsOn(page, assetId, day);
    const splits = events.filter((event) => event.type === 'SPLIT');
    expect(splits, `exactly one SPLIT on ${day}: ${JSON.stringify(events)}`).toHaveLength(1);
    return splits[0].id;
}

/** An event edited in place, by id, as the event editor saves it: the application's answer, whatever it is. */
function editEvent(page: Page, assetId: number, eventId: number, day: string, type: string, amount: string) {
    return page.request.post(`${API}/assets/events`, {data: [{asset_id: assetId, events: [{id: eventId, date: day, type, value: {code: 'EUR', amount}}]}]});
}

/** Edit an event in place, by id, as the event editor does: the save must be accepted. */
async function retypeEvent(page: Page, assetId: number, eventId: number, day: string, type: string, amount: string): Promise<void> {
    await jsonFrom(await editEvent(page, assetId, eventId, day, type, amount), `retype event ${eventId} to ${type}`);
}

/**
 * Delete in dependency order, each step scoped to an id this test recorded.
 *
 * The page is unmounted first, so no reload of the dashboard reads rows while they go. Brokers go before assets
 * (an asset with transactions cannot be deleted; `force` takes the broker's transactions with it), the reserved FX
 * pair after them, the account last. Broker, asset and FX rows are deleted by the account that created them
 * (`page.request` shares the browser's session); the account itself through the standalone `request` context it
 * was registered with, which signs in on its own.
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
    await attempt('unmount the dashboard', async () => {
        await page.goto('about:blank');
    });
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete an owned broker and its transactions');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete an owned asset, its prices and its events');
            expect(result.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
        });
    }
    for (const quote of owned.fxQuotes) {
        await attempt(`fx pair EUR-${quote}`, async () => {
            await deleteReservedPair(page, quote);
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
        const owned: Owned = {user: null, brokerIds: [], assetIds: [], fxQuotes: []};
        try {
            await use(owned);
        } finally {
            await cleanupOwned(page, request, owned);
        }
    },
});

/**
 * A disposable account that owns the whole dashboard, its guides skipped so no overlay covers the banner.
 * Registered through the standalone `request` context, like the guide specs: the browser signs in through the
 * real login form.
 */
async function openAccount(page: Page, request: APIRequestContext, owned: Owned, tag: string): Promise<void> {
    const user = await registerDisposableUser(request, tag);
    owned.user = user;
    await prepareOnboardingAccount(page, user, []);
}

// ---------------------------------------------------------------------------
// The dashboard
// ---------------------------------------------------------------------------

function dashboardUrl(options: {tab?: 'posizioni'; assetId?: number} = {}): string {
    const params = new URLSearchParams();
    if (options.tab) params.set('tab', options.tab);
    if (options.assetId != null) params.set('asset', String(options.assetId));
    params.set('start', daysAgoIso(PERIOD_START_DAYS_AGO));
    params.set('end', todayIso());
    return `/dashboard?${params.toString()}`;
}

/**
 * A full load of the dashboard, with the report it asked for and, when `lotsAssetId` is set, the first answer of
 * the lots panel the URL opens. Read-only: both are the application's own responses, captured, never routed.
 */
async function openDashboard(page: Page, url: string, lotsAssetId: number | null): Promise<DashboardLoad> {
    const reportResponse = armed(page.waitForResponse((response) => isSummaryReport(response.request()), {timeout: 30_000}));
    const lotsResponse = lotsAssetId == null ? null : armed(page.waitForResponse((response) => isMainLotsRequest(response.request(), lotsAssetId), {timeout: 30_000}));
    await page.goto(url);
    const reportAnswer = await reportResponse;
    const range = (reportAnswer.request().postDataJSON() as ReportRequestBody).date_range;
    const report = await jsonFrom<ReportBody>(reportAnswer, 'dashboard report');
    const lots = lotsResponse ? await jsonFrom<LotsBody>(await lotsResponse, 'first answer of the lots panel') : null;
    return {range, report, lots};
}

function expectDashboardPreconditions(load: DashboardLoad): void {
    expect(load.range, 'precondition: the URL seeds the dashboard period').toMatchObject({start: daysAgoIso(PERIOD_START_DAYS_AGO), end: todayIso()});
    expect(load.report.metadata?.target_currency, 'precondition: the dashboard reports in EUR, the currency every amount here is checked in').toBe('EUR');
}

/**
 * Open a collapsed data-quality banner and make sure it *stays* open.
 *
 * Both banners are collapsed by default, and a banner mounted again by a report that lands later starts collapsed:
 * a single click can land on a banner about to be replaced. Toggle only when collapsed, until `aria-expanded`
 * sticks — never a blind click.
 */
async function expandStrict(toggle: Locator): Promise<void> {
    await expect(toggle).toBeVisible({timeout: 20_000});
    await expect(async () => {
        if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
        expect(await toggle.getAttribute('aria-expanded')).toBe('true');
    }).toPass({timeout: 15_000});
}

/** The position's row in the holdings table of the positions panel inside `scope` (dashboard or broker page). */
function positionRow(scope: Locator, assetId: number, brokerId: number): Locator {
    return scope.getByTestId('positions-panel').getByTestId('exposure-table').locator(`tbody tr[data-row-id="${assetId}-${brokerId}"]`);
}

function costCell(row: Locator, columnId: (typeof COST_COLUMNS)[number]): Locator {
    return row.locator(`td[data-column-id="${columnId}"]`);
}

/**
 * Show a column the holdings table hides by default (the average cost is one), through the panel's own column
 * menu. A fresh context starts from the defaults, but the layout is remembered: the header's absence — read once
 * the table is on screen, when the layout is settled — is the state to change, and its presence the proof it did.
 */
async function revealColumn(page: Page, panel: Locator, table: Locator, columnId: string): Promise<void> {
    const header = table.getByTestId(`dt-header-${columnId}`);
    if ((await header.count()) === 0) {
        const menuScope = panel.getByTestId('positions-column-visibility-toggle');
        await menuScope.getByTestId('column-visibility-toggle').click();
        const menu = menuScope.getByTestId('column-visibility-dropdown');
        await expect(menu).toBeVisible({timeout: 5_000});
        await menu.getByTestId(`column-visibility-item-${columnId}`).click();
        await expect(header).toBeVisible({timeout: 5_000});
        // The menu closes on a click outside it, which lands on its own full-screen backdrop; the menu keeps at
        // least 8px from every edge, so the corner is always outside it.
        await page.mouse.click(2, 2);
        await expect(menu).toBeHidden({timeout: 5_000});
    }
    await expect(header).toBeVisible();
}

/** The holdings × table view of the positions panel in `scope`, loaded, with the row on screen and the cost columns shown. */
async function showCostColumns(page: Page, scope: Locator, row: Locator): Promise<void> {
    const panel = scope.getByTestId('positions-panel');
    await waitForSettled(panel, 25_000);
    // Setters, not toggles: a click on the view already shown changes nothing.
    await panel.getByTestId('positions-toggle-holdings').click();
    await panel.getByTestId('positions-toggle-table').click();
    await expect(row, 'the position this test created is listed').toBeVisible({timeout: 15_000});
    await revealColumn(page, panel, panel.getByTestId('exposure-table'), 'pmc');
}

/**
 * «← Portfolio»: the lot detail replaced the portfolio view (Y5-2), so pressing it takes the lots panel off the page and
 * puts the positions panel back. Ends on both facts.
 */
async function backToPortfolio(page: Page): Promise<void> {
    await page.getByTestId('positions-back-to-portfolio').click();
    await expect(page.getByTestId('lots-analysis-panel')).toBeHidden({timeout: 15_000});
    await expect(page.getByTestId('positions-panel')).toBeVisible({timeout: 15_000});
}

/**
 * The lot detail of the position, opened the way a user does it: right click on its row of the holdings table, then the
 * menu action. The positions panel goes, the lots panel comes (Y5-2): ends on the lots panel visible, the asset in the URL.
 */
async function openLotDetail(page: Page, row: Locator, assetId: number): Promise<void> {
    await row.click({button: 'right'});
    await page.getByTestId('context-menu-action-analyze-lots').click();
    await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 15_000});
    await expect(page).toHaveURL(new RegExp(`[?&]asset=${assetId}(?:&|$)`));
    await expect(page.getByTestId('positions-panel'), 'the lot detail replaces the portfolio view: no positions panel beside it').toHaveCount(0);
}

/**
 * The lots panel the URL opened shows the issue `code`.
 *
 * The panel publishes no busy state and starts with `loading` false, so the lots of the answer are the witness
 * that an answer is on screen: its banner comes from the same response.
 */
async function expectLotIssue(page: Page, code: string): Promise<void> {
    const panel = page.getByTestId('lots-analysis-panel');
    await expect(panel).toBeVisible({timeout: 15_000});
    await expect(panel.getByTestId('unified-lots-table').locator('tbody tr[data-row-id]').first(), 'witness: the lots of the answer are on screen').toBeVisible({timeout: 20_000});
    const banner = panel.getByTestId('lot-data-quality-banner');
    await expect(banner).toBeVisible();
    await expandStrict(banner.getByTestId('lot-data-quality-toggle'));
    await expect(banner.getByTestId(`lot-data-quality-issue-${code}`)).toBeVisible();
}

/**
 * No cost is unknown on the dashboard the URL opened, nor in the lots panel it opened on `assetId` (E2).
 *
 * The report and the lots answer say what there is; the page must show exactly that. The position's figures — 20
 * shares at an average cost of 50, quoted 55 — come from the same report and are the presence barrier of the
 * banner's absence, the lots of the answer that of the lots banner's. Both banners are unmounted when there is
 * nothing to report, so an absence is a count of 0.
 */
async function expectNoUnknownCost(page: Page, load: DashboardLoad, assetId: number, brokerId: number): Promise<void> {
    expectDashboardPreconditions(load);
    const issues = reportIssues(load.report);
    expect(
        issues.filter((issue) => issue.code === 'MISSING_COST_BASIS'),
        `no cost is unknown; the report carries ${JSON.stringify(issues)}`,
    ).toEqual([]);
    const holding = holdingOf(load.report, assetId, brokerId);
    expect({quantity: numberOrNull(holding.quantity), ...costFigures(holding)}, '20 shares at an average cost of 50 (1000 EUR over 20), quoted 55: a P&L of 100, +10 %').toEqual({quantity: 20, wac_per_unit: 50, gain_loss: 100, gain_loss_percent: 0.1});

    const dashboard = page.getByTestId('dashboard-page');
    await waitForSettled(dashboard, 25_000);
    // The URL opened the lot detail alone (Y5-2): the lots panel first, then «← Portfolio» for the positions and the banner.
    const lotIssuesNow = lotIssues(load.lots);
    expect(
        lotIssuesNow.filter((issue) => issue.code === 'MISSING_COST_BASIS'),
        `the lots analysis knows every cost too; it carries ${JSON.stringify(lotIssuesNow)}`,
    ).toEqual([]);
    const lotIds = (load.lots?.lots ?? []).map((lot) => lot.lot_id);
    expect(lotIds.length, 'precondition: the purchase opened at least one lot').toBeGreaterThan(0);
    const lotsPanel = page.getByTestId('lots-analysis-panel');
    await expect(lotsPanel).toBeVisible({timeout: 15_000});
    // The witness: the lots of this very answer are on screen, so the panel shows it — and its banner with it.
    for (const lotId of lotIds) await expect(lotsPanel.getByTestId('unified-lots-table').locator(`tbody tr[data-row-id="${lotId}"]`), `lot ${lotId} of the answer is on screen`).toBeVisible({timeout: 20_000});
    // Decided by that answer, not by a probe of the page.
    if (lotIssuesNow.length === 0) {
        await expect(lotsPanel.getByTestId('lot-data-quality-banner'), 'nothing to report in the lots panel: no banner').toHaveCount(0);
    } else {
        await expandStrict(lotsPanel.getByTestId('lot-data-quality-toggle'));
        await expect(lotsPanel.getByTestId('lot-data-quality-issue-MISSING_COST_BASIS'), 'no lots row for a cost nobody knows').toHaveCount(0);
    }

    await backToPortfolio(page);
    const row = positionRow(dashboard, assetId, brokerId);
    await showCostColumns(page, dashboard, row);
    for (const columnId of COST_COLUMNS) await expect(costCell(row, columnId), `${columnId}: a figure, never a dash`).toHaveText(/\d/);
    // Decided by the report, not by a probe; the figures above prove that report is on screen.
    if (issues.length === 0) {
        await expect(page.getByTestId('data-quality-banner'), 'nothing to report: no banner').toHaveCount(0);
    } else {
        await expandStrict(page.getByTestId('data-quality-toggle'));
        await expect(page.getByTestId('data-quality-issue-MISSING_COST_BASIS'), 'no row for a cost nobody knows').toHaveCount(0);
    }
}

/** Watch the «Sync rates» requests of this page from now on: how many left before the click, and when the answer came. */
function watchFxSync(page: Page): SyncWatch {
    const watch: SyncWatch = {sentBeforeClick: 0, clicked: false, answered: false};
    page.on('request', (req) => {
        if (isFxSync(req) && !watch.clicked) watch.sentBeforeClick += 1;
    });
    page.on('response', (res) => {
        if (isFxSync(res.request())) watch.answered = true;
    });
    return watch;
}

test.describe('Data quality on real data — items 21, 22, 23 (issue #32)', () => {
    test('E1 — item 21: a missing rate is reported, not counted at zero, and «Sync rates» downloads it', async ({page, request, owned}) => {
        test.setTimeout(180_000);
        const quote = reservedCurrency('missingRate');
        const pair = `EUR-${quote}`;
        const d1 = daysAgoIso(40);
        const d2 = daysAgoIso(20);
        // The issue's dates a week either side, the end never past today: what the CTA must ask for.
        const syncStart = daysAgoIso(47);
        const syncEnd = daysAgoIso(13);

        const {brokerId, assetId} = await test.step(`seed: an EUR asset bought and partly sold with ${quote} cash, on a MOCKFX route without rates`, async () => {
            await openAccount(page, request, owned, 'dqfx');
            owned.fxQuotes.push(quote);
            await resetReservedPair(page, quote);
            await createMockFxRoute(page, quote);
            const suffix = uniqueSuffix();
            const brokerId = await createBroker(page, owned, `dq-fx-broker-${suffix}`, {allow_cash_overdraft: true});
            const assetId = await createManualAsset(page, owned, `DQ missing rate ${suffix}`, 'EUR');
            await seedPrices(page, assetId, [
                {date: d1, close: 100, currency: 'EUR'},
                {date: d2, close: 110, currency: 'EUR'},
            ]);
            // The cash in `quote` nets to zero at the end of each day: the only conversions the engine needs are
            // the movements', on d1 and d2. At 1 EUR = 1.2345: 10 bought for 1000 EUR, 4 sold for 500 EUR.
            await commitTransactions(
                page,
                {
                    creates: [
                        {broker_id: brokerId, type: 'DEPOSIT', date: d1, cash: {code: quote, amount: '1234.5'}, description: `dq-real funding ${suffix}`},
                        {broker_id: brokerId, asset_id: assetId, type: 'BUY', date: d1, quantity: '10', cash: {code: quote, amount: '-1234.5'}, description: `dq-real purchase ${suffix}`},
                        {broker_id: brokerId, asset_id: assetId, type: 'SELL', date: d2, quantity: '-4', cash: {code: quote, amount: '617.25'}, description: `dq-real sale ${suffix}`},
                        {broker_id: brokerId, type: 'WITHDRAWAL', date: d2, cash: {code: quote, amount: '-617.25'}, description: `dq-real withdrawal ${suffix}`},
                    ],
                },
                `commit the ${quote}-funded purchase and partial sale`,
            );
            return {brokerId, assetId};
        });

        const sync = watchFxSync(page);
        const load = await openDashboard(page, dashboardUrl({tab: 'posizioni', assetId}), assetId);
        const dashboard = page.getByTestId('dashboard-page');
        const fxRow = page.getByTestId('data-quality-issue-MISSING_FX_RATES');
        const row = positionRow(dashboard, assetId, brokerId);
        const lotsPanel = page.getByTestId('lots-analysis-panel');

        await test.step('before the sync: the report names the pair and the two days, and leaves the cost unknown', async () => {
            expectDashboardPreconditions(load);
            const issues = reportIssues(load.report);
            const fxIssues = issues.filter((issue) => issue.code === 'MISSING_FX_RATES');
            expect(fxIssues, `exactly one MISSING_FX_RATES issue for this account; the report carries ${JSON.stringify(issues)}`).toHaveLength(1);
            expect(fxIssues[0], 'the issue names the pair and offers the sync').toMatchObject({severity: 'warning', affected_fx_pairs: [pair], cta_action: 'sync_fx_pair'});
            expect(fxIssues[0].message_params, `the missing dates are the two movement days — observed ${JSON.stringify(fxIssues[0])}`).toEqual({count: 1, date_from: d1, date_to: d2, dates_count: 2});
            expect(costFigures(holdingOf(load.report, assetId, brokerId)), 'a cost paid in a currency without a rate is unknown, not zero').toEqual({wac_per_unit: null, gain_loss: null, gain_loss_percent: null});
        });

        await test.step('before the sync: the banner shows the pair and the days, the positions a dash, the lots panel the issue', async () => {
            await waitForSettled(dashboard, 25_000);
            await expandStrict(page.getByTestId('data-quality-toggle'));
            await expect(fxRow).toBeVisible({timeout: 10_000});
            await expect(fxRow).toHaveAttribute('data-severity', 'warning');
            for (const text of ['EUR', quote, d1, d2]) await expect(fxRow, `the banner row shows ${text}`).toContainText(text);

            // The URL opened the lot detail alone (Y5-2): the lots panel first, then «← Portfolio» for the positions.
            expect(
                lotIssues(load.lots).map((issue) => issue.code),
                'precondition: the lots analysis reports the missing rate too',
            ).toContain('MISSING_FX_RATES');
            await expectLotIssue(page, 'MISSING_FX_RATES');

            await backToPortfolio(page);
            await showCostColumns(page, dashboard, row);
            for (const columnId of COST_COLUMNS) await expect(costCell(row, columnId), `${columnId}: a dash, never a zero`).toHaveText(DASH);

            // The detail is opened again and left open: D2 below is about a lots panel already open when «Sync rates» answers.
            await openLotDetail(page, row, assetId);
            await expectLotIssue(page, 'MISSING_FX_RATES');
        });

        // Armed before the click. `answered` flips when the sync's answer reaches the page, so a request that
        // passes these filters was sent because of the sync — the panel's own first load cannot count (D2).
        expect(sync.sentBeforeClick, 'nothing may sync before the user asks').toBe(0);
        const since = await eventSeq(page);
        sync.clicked = true;
        const syncRequest = armed(page.waitForRequest((req) => isFxSync(req), {timeout: 15_000}));
        const syncResponse = armed(page.waitForResponse((res) => isFxSync(res.request()), {timeout: 60_000}));
        const reloadRequest = armed(page.waitForRequest((req) => sync.answered && isSummaryReport(req), {timeout: 60_000}));
        // Null when the panel never asks again: the D2 step turns that into its own failure message.
        const lotsRefresh = page.waitForRequest((req) => sync.answered && isMainLotsRequest(req, assetId), {timeout: LOTS_REFRESH_TIMEOUT_MS}).catch(() => null);

        await test.step('«Sync rates» asks MOCKFX for the missing days, a week either side, and says it worked', async () => {
            await fxRow.getByTestId('data-quality-cta-MISSING_FX_RATES').click();
            expect((await syncRequest).postDataJSON(), 'the sync covers the issue dates a week either side').toEqual({pairs: [pair], start: syncStart, end: syncEnd});
            const answer = schemas.FXSyncBulkResponse.parse(await jsonFrom(await syncResponse, 'the sync answer'));
            expect(
                answer.results.find((item) => item.pair === pair),
                `the sync answer for ${pair}: ${JSON.stringify(answer.results)}`,
            ).toMatchObject({status: 'ok', provider_used: 'MOCKFX'});
            const synced = await waitForEvent(page, 'fx.rates.synced', {since, timeout: 60_000});
            expect(synced.detail).toMatchObject({origin: 'dashboard-banner', pairs: [pair], start: syncStart, end: syncEnd, outcome: 'ok', stillMissing: false});
        });

        await test.step('after the sync: the rate of d1 is stored, the report heals, the figures come back', async () => {
            const conversion = await jsonFrom<ConvertBody>(await convertOnDay(page, quote, '1234.5', 'EUR', d1), `convert 1234.5 ${quote} on ${d1}`);
            const converted = conversion.results.find((item) => item.conversion_date === d1);
            expect(converted, `a conversion on ${d1}: ${JSON.stringify(conversion.results)}`).toBeTruthy();
            expect({code: converted?.to_amount.code, amount: numberOrNull(converted?.to_amount.amount)}, 'at 1 EUR = 1.2345, exactly 1000 EUR').toEqual({code: 'EUR', amount: 1000});
            expect(converted?.backward_fill_info ?? null, `the rate is ${d1}'s own, not carried from an earlier day`).toBeNull();

            const reloadAnswer = await (await reloadRequest).response();
            if (!reloadAnswer) throw new Error('The report the dashboard asked again after the sync got no answer');
            const reloaded = await jsonFrom<ReportBody>(reloadAnswer, 'report reloaded after the sync');
            const left = reportIssues(reloaded);
            expect(
                left.filter((issue) => issue.code === 'MISSING_FX_RATES'),
                `no rate is missing any more; the report carries ${JSON.stringify(left)}`,
            ).toEqual([]);
            expect(costFigures(holdingOf(reloaded, assetId, brokerId)), '6 left at an average of 100 EUR, quoted 110').toEqual({wac_per_unit: 100, gain_loss: 60, gain_loss_percent: 0.1});

            await waitForSettled(dashboard, 25_000);
            // Decided by the reloaded report, not by a probe of the page.
            if (left.length === 0) {
                await expect(page.getByTestId('data-quality-banner'), 'nothing is left to report: the banner goes').toHaveCount(0, {timeout: 15_000});
            } else {
                await expandStrict(page.getByTestId('data-quality-toggle'));
                await expect(fxRow, 'the missing-rate row goes').toHaveCount(0, {timeout: 15_000});
            }
        });

        await test.step('D2: the lots panel already open asks again by itself, without a reload, and drops the issue', async () => {
            const refreshed = await lotsRefresh;
            expect(refreshed, 'the open lots panel did not ask again after «Sync rates»: no POST /portfolio/lots/analysis for this asset once the sync had answered').not.toBeNull();
            const refreshedAnswer = await refreshed!.response();
            if (!refreshedAnswer) throw new Error('The lots analysis asked again after the sync got no answer');
            const lotsAfter = await jsonFrom<LotsBody>(refreshedAnswer, 'lots analysis asked again after the sync');
            const lotIssuesAfter = lotIssues(lotsAfter);
            expect(
                lotIssuesAfter.filter((issue) => issue.code === 'MISSING_FX_RATES'),
                `the lots answer has no missing rate any more; it carries ${JSON.stringify(lotIssuesAfter)}`,
            ).toEqual([]);
            // Decided by that answer, not by a probe of the page.
            if (lotIssuesAfter.length === 0) {
                await expect(lotsPanel.getByTestId('lot-data-quality-banner'), 'nothing is left to report in the lots panel: its banner goes').toHaveCount(0, {timeout: 15_000});
            } else {
                await expandStrict(lotsPanel.getByTestId('lot-data-quality-toggle'));
                await expect(lotsPanel.getByTestId('lot-data-quality-issue-MISSING_FX_RATES'), 'the missing-rate row of the lots panel goes').toHaveCount(0, {timeout: 15_000});
            }
        });

        await test.step('after the sync, back on the portfolio: the positions show a figure again where they showed a dash', async () => {
            await backToPortfolio(page);
            await showCostColumns(page, dashboard, row);
            for (const columnId of COST_COLUMNS) await expect(costCell(row, columnId), `${columnId} is a figure again`).toHaveText(/\d/, {timeout: 15_000});
        });
    });

    test('E2 — item 22 (P-10): a SPLIT whose incoming adjustment has no cost cannot be retyped, so no unknown cost reaches the dashboard — with a cost of 0 it can', async ({page, request, owned}) => {
        test.setTimeout(150_000);
        const d0 = daysAgoIso(60);
        const d1 = daysAgoIso(50);
        const d2 = daysAgoIso(30);

        const {brokerId, assetId, eventId, adjustmentId} = await test.step('seed: 10 shares bought for 1000 EUR, a SPLIT of 2, and its ADJUSTMENT +10 saved in Auto, which stores no cost on a split-linked row', async () => {
            await openAccount(page, request, owned, 'dqcost');
            const suffix = uniqueSuffix();
            const brokerId = await createBroker(page, owned, `dq-cost-broker-${suffix}`);
            const assetId = await createManualAsset(page, owned, `DQ split ${suffix}`, 'EUR');
            await seedPrices(page, assetId, [
                {date: d1, close: 100, currency: 'EUR'},
                {date: d2, close: 55, currency: 'EUR'},
            ]);
            await commitTransactions(
                page,
                {
                    creates: [
                        {broker_id: brokerId, type: 'DEPOSIT', date: d0, cash: {code: 'EUR', amount: '10000'}, description: `dq-real funding ${suffix}`},
                        {broker_id: brokerId, asset_id: assetId, type: 'BUY', date: d1, quantity: '10', cash: {code: 'EUR', amount: '-1000'}, description: `dq-real purchase ${suffix}`},
                    ],
                },
                'commit the funding and the purchase',
            );
            const eventId = await createSplitEvent(page, assetId, d2, '2');
            const adjustment = await commitTransactions(
                page,
                {creates: [{broker_id: brokerId, asset_id: assetId, type: 'ADJUSTMENT', date: d2, quantity: '10', asset_event_id: eventId, cost_basis_mode: 'auto', description: `dq-real split shares ${suffix}`}]},
                'commit the ADJUSTMENT linked to the split, in Auto',
            );
            const adjustmentId = createdId(adjustment, 0);
            const saved = await readTransaction(page, adjustmentId);
            expect(saved.asset_event_id, 'the ADJUSTMENT is linked to the split').toBe(eventId);
            expect(saved.cost_basis_override ?? null, 'precondition (P-10): a split-linked ADJUSTMENT in Auto is saved without a cost').toBeNull();
            return {brokerId, assetId, eventId, adjustmentId};
        });

        await test.step('the retype to PRICE_ADJUSTMENT is refused (409), naming the split, its date and the ADJUSTMENT without a cost — and nothing changes', async () => {
            const refused = await editEvent(page, assetId, eventId, d2, 'PRICE_ADJUSTMENT', '2');
            expect(refused.status(), `the retype of SPLIT ${eventId} must be refused while ADJUSTMENT ${adjustmentId} has no cost — got ${await refused.text()}`).toBe(409);
            const detail = ((await refused.json()) as EventRefusalBody).detail;
            expect({error_code: detail?.error_code, params: detail?.params}, 'the refusal says why, and where').toEqual({
                error_code: 'EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST',
                // R13-SEC7: the caller owns the broker and sees every adjustment, so none is hidden.
                params: {asset_id: assetId, item_index: 0, event_id: eventId, date: d2, transaction_ids: [adjustmentId], hidden_transactions_count: 0},
            });
            expect(await eventsOn(page, assetId, d2), 'the event is still the SPLIT, under its id').toEqual([{id: eventId, type: 'SPLIT'}]);
            const kept = await readTransaction(page, adjustmentId);
            expect({asset_event_id: kept.asset_event_id, cost_basis_override: kept.cost_basis_override ?? null}, 'the ADJUSTMENT is still linked to the split, still without a cost').toEqual({asset_event_id: eventId, cost_basis_override: null});
        });

        await test.step('no unknown cost anywhere: 20 shares at an average cost of 50 with figures on the dashboard, nothing of the kind in the banner or the lots panel', async () => {
            // A fresh document: no report the page had already asked for can be taken for the one awaited here.
            await page.goto('about:blank');
            await expectNoUnknownCost(page, await openDashboard(page, dashboardUrl({tab: 'posizioni', assetId}), assetId), assetId, brokerId);
        });

        await test.step('the broker page shows the same figures', async () => {
            await page.goto(`/brokers/${brokerId}?tab=posizioni`);
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 15_000});
            // Disabled while the broker or its report is loading: the page's busy state.
            await expect(page.getByTestId('broker-refresh')).toBeEnabled({timeout: 25_000});
            const holdings = page.getByTestId('broker-holdings');
            const brokerRow = positionRow(holdings, assetId, brokerId);
            await showCostColumns(page, holdings, brokerRow);
            for (const columnId of COST_COLUMNS) await expect(costCell(brokerRow, columnId), `broker page, ${columnId}: a figure, never a dash`).toHaveText(/\d/);
        });

        await test.step('with a cost of 0 per unit on the ADJUSTMENT the same retype goes through, and no cost is unknown either', async () => {
            await commitTransactions(page, {updates: [{id: adjustmentId, cost_basis_override: {code: 'EUR', amount: '0'}, cost_basis_mode: 'manual'}]}, 'set a purchase cost of 0 per unit on the ADJUSTMENT');
            const costed = await readTransaction(page, adjustmentId);
            expect({asset_event_id: costed.asset_event_id, code: costed.cost_basis_override?.code, amount: numberOrNull(costed.cost_basis_override?.amount)}, 'precondition: still linked to the split, with a cost of 0 stored').toEqual({asset_event_id: eventId, code: 'EUR', amount: 0});

            await retypeEvent(page, assetId, eventId, d2, 'PRICE_ADJUSTMENT', '2');
            expect(await eventsOn(page, assetId, d2), 'the event keeps its id and is now a PRICE_ADJUSTMENT').toEqual([{id: eventId, type: 'PRICE_ADJUSTMENT'}]);
            expect((await readTransaction(page, adjustmentId)).asset_event_id, 'the ADJUSTMENT keeps its link').toBe(eventId);

            // No longer a split: the 10 shares are an acquisition at a known cost of 0, so the average is still 1000 EUR
            // over 20 shares.
            await page.goto('about:blank');
            await expectNoUnknownCost(page, await openDashboard(page, dashboardUrl({tab: 'posizioni', assetId}), assetId), assetId, brokerId);
        });
    });

    test('E3 — item 23: the «Unrealized change» tooltip splits the period by currency into asset and exchange-rate effect', async ({page, request, owned}) => {
        test.setTimeout(120_000);
        const quote = reservedCurrency('breakdown');
        const d1 = daysAgoIso(50);
        const d2 = daysAgoIso(20);

        await test.step(`seed: EUR-${quote} going from 2 to 2.5, one asset priced in ${quote} and one in EUR, both bought with EUR`, async () => {
            await openAccount(page, request, owned, 'dqkpi');
            owned.fxQuotes.push(quote);
            await resetReservedPair(page, quote);
            await storeManualRates(page, quote, [
                {date: d1, rate: '2'},
                {date: d2, rate: '2.5'},
            ]);
            const suffix = uniqueSuffix();
            const brokerId = await createBroker(page, owned, `dq-kpi-broker-${suffix}`);
            const foreignId = await createManualAsset(page, owned, `DQ ${quote} asset ${suffix}`, quote);
            const domesticId = await createManualAsset(page, owned, `DQ EUR asset ${suffix}`, 'EUR');
            await seedPrices(page, foreignId, [
                {date: d1, close: 20, currency: quote},
                {date: d2, close: 30, currency: quote},
            ]);
            await seedPrices(page, domesticId, [
                {date: d1, close: 20, currency: 'EUR'},
                {date: d2, close: 25, currency: 'EUR'},
            ]);
            // 10 × 20 = 200 in `quote` = 100 EUR at 2, now 10 × 30 / 2.5 = 120 EUR: +40 from the asset at today's
            // rate, −20 from the rate on its cost (200 at 2.5 is 80, it cost 100). 5 × 20 EUR = 100, now 125: +25.
            await commitTransactions(
                page,
                {
                    creates: [
                        {broker_id: brokerId, type: 'DEPOSIT', date: d1, cash: {code: 'EUR', amount: '1000'}, description: `dq-real funding ${suffix}`},
                        {broker_id: brokerId, asset_id: foreignId, type: 'BUY', date: d1, quantity: '10', cash: {code: 'EUR', amount: '-100'}, description: `dq-real ${quote} purchase ${suffix}`},
                        {broker_id: brokerId, asset_id: domesticId, type: 'BUY', date: d1, quantity: '5', cash: {code: 'EUR', amount: '-100'}, description: `dq-real EUR purchase ${suffix}`},
                    ],
                },
                'commit the funding and the two purchases',
            );
        });

        const load = await openDashboard(page, dashboardUrl(), null);

        await test.step(`the report splits the change: +25 asset EUR, +40 asset ${quote}, −20 exchange rate ${quote}`, async () => {
            expectDashboardPreconditions(load);
            const summary = load.report.summary;
            const rows = (summary?.period_unrealized_breakdown ?? []).map((item) => ({kind: item.kind, asset_currency: item.asset_currency, code: item.period_delta.code, amount: Number(item.period_delta.amount)}));
            expect(rows, `the breakdown rows, in the backend's order — observed ${JSON.stringify(summary?.period_unrealized_breakdown)}`).toEqual([
                {kind: 'asset', asset_currency: 'EUR', code: 'EUR', amount: 25},
                {kind: 'asset', asset_currency: quote, code: 'EUR', amount: 40},
                {kind: 'fx', asset_currency: quote, code: 'EUR', amount: -20},
            ]);
            const delta = summary?.period_unrealized_gain_loss_delta;
            expect({code: delta?.code, amount: numberOrNull(delta?.amount)}, 'the rows add up to the unrealized change').toEqual({code: 'EUR', amount: 45});
            const issues = reportIssues(load.report);
            expect(
                issues.filter((issue) => issue.code.startsWith('MISSING_FX')),
                `every rate is there; the report carries ${JSON.stringify(issues)}`,
            ).toEqual([]);
        });

        await test.step('the tooltip shows the same three rows, in that order, to the cent', async () => {
            await waitForSettled(page.getByTestId('dashboard-page'), 25_000);
            const bar = page.getByTestId('kpi-unrealized-delta');
            await expect(bar).toBeVisible({timeout: 15_000});
            // The value is tweened: it reaches the figure, it does not start there.
            await expect.poll(async () => digitsOf(await bar.getByTestId('kpi-unrealized-delta-value').textContent()), {timeout: 10_000, message: 'the bar reads the unrealized change, 45.00'}).toBe('4500');

            const trigger = bar.locator('[role="button"]');
            await expect(trigger, 'the bar has one tooltip trigger, around its label').toHaveCount(1);
            // The keyboard path opens the same tooltip as a hover, pinned, without the hover delay.
            await trigger.press('Enter');
            const tooltip = page.getByTestId('tooltip-content').filter({has: page.locator('[data-testid^="kpi-unrealized-breakdown-"]')});
            await expect(tooltip, 'the tooltip of the bar is open, with its breakdown').toBeVisible({timeout: 5_000});

            const expected = [
                {id: 'kpi-unrealized-breakdown-asset-EUR', digits: '2500', negative: false},
                {id: `kpi-unrealized-breakdown-asset-${quote}`, digits: '4000', negative: false},
                {id: `kpi-unrealized-breakdown-fx-${quote}`, digits: '2000', negative: true},
            ];
            await expect
                .poll(() => tooltip.locator('[data-testid^="kpi-unrealized-breakdown-"]').evaluateAll((elements) => elements.map((element) => element.getAttribute('data-testid'))), {
                    timeout: 5_000,
                    message: 'exactly the backend rows, in its order: no fx row for EUR, no unsplit row',
                })
                .toEqual(expected.map((item) => item.id));
            for (const item of expected) {
                // The value is the row's last cell; separators and the currency sign are ignored, the digits are not.
                const value = tooltip.getByTestId(item.id).locator('td').last();
                await expect.poll(async () => digitsOf(await value.textContent()), {timeout: 5_000, message: `${item.id} reads ${item.digits} once separators are dropped`}).toBe(item.digits);
                if (item.negative) await expect(value, `${item.id} is a loss and says so`).toHaveText(/[-−]/);
                else await expect(value, `${item.id} is a gain and carries no minus`).not.toHaveText(/[-−]/);
            }
        });
    });
});
