/**
 * Dashboard page cache — R2 / N, phase 1 («mostra il vecchio, aggiorna in background»).
 *
 * Written RED-FIRST, before the implementation. The developer's note: moving between pages, the
 * Dashboard recomputes what was just on screen. The frontend already caches the report and the risk
 * answers; what defeats it today, measured on the lane (plan §1–§2):
 *
 *   1. even with the cache full, the KPIs count up from 0 on every return (`TweenedValue` starts every
 *      value from `tweened(0)`), which reads as a recompute;
 *   2. the asset page polls `POST /assets/prices/current`, which the mutation filter treats as a write,
 *      so on the way back every answer is thrown away: skeletons, and the report asked again — several
 *      times — and the risk too;
 *   3. back on the Positions tab, the Performance table and the lots panel ask before the owned brokers
 *      are known: no `broker_ids`, so the backend widens the scope to every broker the user can see,
 *      viewer and editor ones included (F2);
 *   4. the currency and the broker filter restart from the defaults, so the return asks another key;
 *   5. «Aggiorna» reloads the report but not the risk.
 *
 * The contract (decision E1 of 06/10 and its follow-ups): an invalidation marks the data stale and
 * keeps it; a page shows what it has at once and refreshes in background, one request per key; the
 * scope is always the owned brokers; currency and broker filter last the session; «Aggiorna» refreshes
 * report, risk and lots.
 *
 * Read-only on the shared database: TEST_USER, nothing written. The one writer on the path, the live
 * price of the asset page (`POST /assets/prices/current` writes today's candle and asks a live
 * provider), is answered in the browser with a schema-valid "no quote" answer: no provider is reached,
 * nothing is written, and the axios interceptor still sees a successful mutation — the trigger under
 * test. Owned brokers are read from `GET /brokers` (`page.request`, which no route intercepts), never
 * hard-coded. Every request the page sends is recorded per test with `page.on('request')`; nothing
 * here counts a request it did not watch the page send.
 *
 * Settled states read: `dashboard-page` / `positions-panel` `data-busy`, `risk-levels-panel`
 * `data-catalog="ready"` and `data-busy`, `risk-l1-cards` visible with no `risk-l1-loading`.
 */

import type {Route} from '@playwright/test';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {optionsClosed} from '../fixtures/probe';
import {TEST_USER} from '../fixtures/test-users';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
const RISK_QUERY_PATH = `${API}/risk/query`;
const LOTS_PATH = `${API}/portfolio/lots/analysis`;
const PAGE_TIMEOUT = 30_000;

type ReportBody = {
    include_summary?: boolean;
    include_history?: boolean;
    include_allocation_history?: boolean;
    include_positions_contribution?: boolean;
    include_breakdown?: boolean;
    broker_ids?: number[];
    target_currency?: string;
    date_range?: {start?: string; end?: string};
};
type RiskBody = {mode?: string; scope?: {kind?: string; broker_ids?: number[]}};
type LotsBody = {asset_id?: number; broker_ids?: number[]; target_currency?: string; requested_analyses?: string[]; selected_lot_ids?: number[]};
type BrokerListItem = {id: number; name: string; user_role?: string | null; user_share_percentage?: string | number | null};

/** Every report, risk query and lots analysis the page sends, in order, as the page sent them. */
interface Traffic {
    reports: ReportBody[];
    riskQueries: RiskBody[];
    lots: LotsBody[];
}

function recordTraffic(page: Page): Traffic {
    const traffic: Traffic = {reports: [], riskQueries: [], lots: []};
    page.on('request', (request) => {
        if (request.method() !== 'POST') return;
        const path = new URL(request.url()).pathname;
        const body = (request.postDataJSON() ?? {}) as Record<string, unknown>;
        if (path === REPORT_PATH) traffic.reports.push(body as ReportBody);
        else if (path === RISK_QUERY_PATH) traffic.riskQueries.push(body as RiskBody);
        else if (path === LOTS_PATH) traffic.lots.push(body as LotsBody);
    });
    return traffic;
}

/** Where each list stands now: what is sent after it is what an action caused. */
function mark(traffic: Traffic): {reports: number; riskQueries: number; lots: number} {
    return {reports: traffic.reports.length, riskQueries: traffic.riskQueries.length, lots: traffic.lots.length};
}

/**
 * The live price, answered in the browser: a schema-valid "no quote" for every asked id. Nothing is
 * fabricated (no value) and nothing is written; the response is still a 2xx, so the axios interceptor
 * notifies the portfolio mutation listeners exactly as a real quote would.
 */
async function stubLivePrice(page: Page): Promise<{served: number}> {
    const live = {served: 0};
    await page.route('**/api/v1/assets/prices/current', async (route) => {
        const ids = (route.request().postDataJSON() as number[] | null) ?? [];
        const body = {
            results: ids.map((asset_id) => ({asset_id, value: null, currency: null, as_of_date: null, source: null, error: 'Synthetic offline boundary: no live quote requested'})),
            success_count: 0,
            errors: [],
        };
        schemas.FACurrentPriceResponse.parse(body);
        live.served += 1;
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
    });
    return live;
}

/** Holds every report and risk query until `release()`: the refresh in background, kept in flight. */
async function holdRefreshes(page: Page): Promise<{release: () => void; held: {reports: number; riskQueries: number}}> {
    let release!: () => void;
    const released = new Promise<void>((resolve) => {
        release = resolve;
    });
    const held = {reports: 0, riskQueries: 0};
    const hold = (kind: keyof typeof held) => async (route: Route) => {
        held[kind] += 1;
        await released;
        await route.continue().catch(() => undefined);
    };
    await page.route('**/api/v1/portfolio/report', hold('reports'));
    await page.route('**/api/v1/risk/query', hold('riskQueries'));
    return {release, held};
}

/** The brokers the Dashboard counts as the user's own: OWNER with a share unset or above zero, as `getOwnedBrokers()` keeps them. */
async function ownedBrokerIds(page: Page): Promise<number[]> {
    const response = await page.request.get(`${API}/brokers`);
    expect(response.ok(), `GET ${API}/brokers → HTTP ${response.status()}`).toBe(true);
    const items = ((await response.json()) as {items?: BrokerListItem[]}).items ?? [];
    return items
        .filter((broker) => broker.user_role === 'OWNER' && (broker.user_share_percentage == null || Number(broker.user_share_percentage) > 0))
        .map((broker) => broker.id)
        .sort((left, right) => left - right);
}

function dashboard(page: Page): Locator {
    return page.getByTestId('dashboard-page');
}

/** Card 1's hero: the Period P&L figure. */
function periodPnlHero(page: Page): Locator {
    return dashboard(page).getByTestId('kpi-period-pnl').getByTestId('kpi-value');
}

const HERO_SELECTOR = '[data-testid="dashboard-page"] [data-testid="kpi-period-pnl"] [data-testid="kpi-value"]';

/**
 * The hero's text once its count-up is over: two reads in a row, 400 ms apart, agree. The count-up lasts
 * 900 ms (cubicOut), and its last 400 ms still move any figure above a few cents.
 */
async function settledHeroText(page: Page): Promise<string> {
    const hero = periodPnlHero(page);
    await expect(hero).toBeVisible({timeout: PAGE_TIMEOUT});
    let previous = '';
    let current = '';
    await expect
        .poll(
            async () => {
                previous = current;
                current = (await hero.innerText()).trim();
                return current !== '' && current === previous;
            },
            {message: 'the Period P&L hero never stopped moving', intervals: [400], timeout: 15_000},
        )
        .toBe(true);
    return current;
}

/**
 * Arms a probe that reads the hero ONCE, in the first animation frame where it is visible (rendered and
 * not `visibility: hidden` — the skeleton hides it with `invisible`). Armed before the navigation that
 * mounts it; SPA navigations keep the window, so the probe sees the mount.
 */
async function armHeroProbe(page: Page): Promise<void> {
    await page.evaluate((selector) => {
        const probe = window as unknown as {__dashboardCacheHero?: string | null};
        probe.__dashboardCacheHero = null;
        const look = () => {
            const hero = document.querySelector<HTMLElement>(selector);
            if (hero && hero.getClientRects().length > 0 && getComputedStyle(hero).visibility !== 'hidden') {
                probe.__dashboardCacheHero = hero.innerText.trim();
                return;
            }
            requestAnimationFrame(look);
        };
        requestAnimationFrame(look);
    }, HERO_SELECTOR);
}

/** What the probe read on the hero's first visible frame. */
async function heroAtFirstSight(page: Page): Promise<string> {
    const handle = await page.waitForFunction(() => (window as unknown as {__dashboardCacheHero?: string | null}).__dashboardCacheHero ?? null, undefined, {timeout: PAGE_TIMEOUT});
    return (await handle.jsonValue()) as string;
}

/** The risk levels have answered: catalog ready, first load over, L1's cards on screen and no skeleton. */
async function riskSettled(page: Page): Promise<Locator> {
    const panel = page.getByTestId('risk-levels-panel');
    await expect(panel).toHaveAttribute('data-catalog', 'ready', {timeout: PAGE_TIMEOUT});
    await expect(panel).toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
    await expect(panel.getByTestId('risk-l1-cards')).toBeVisible({timeout: PAGE_TIMEOUT});
    await expect(panel.getByTestId('risk-l1-loading')).toHaveCount(0);
    return panel;
}

function contributionRows(page: Page): Locator {
    return page.getByTestId('contribution-table').locator('tbody tr[data-row-id^="pos-"]');
}

/** `pos-{brokerId}-{assetId}`, the Performance table's row id. */
function parseRowId(rowId: string): {brokerId: number; assetId: number} {
    const match = /^pos-(\d+)-(\d+)$/.exec(rowId);
    if (!match) throw new Error(`unexpected Performance row id "${rowId}" (expected pos-{brokerId}-{assetId})`);
    return {brokerId: Number(match[1]), assetId: Number(match[2])};
}

async function contributionRowIds(page: Page): Promise<string[]> {
    await expect.poll(() => contributionRows(page).count(), {message: 'the Performance table shows no position', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);
    return contributionRows(page).evaluateAll((rows) => rows.map((row) => row.getAttribute('data-row-id') ?? ''));
}

/** Positions → Performance → table, settled. */
async function openPerformanceTable(page: Page): Promise<void> {
    await page.getByTestId('dashboard-tab-posizioni').click();
    const positions = page.getByTestId('positions-panel');
    await expect(positions).toBeVisible({timeout: PAGE_TIMEOUT});
    await page.getByTestId('positions-toggle-performance').click();
    await page.getByTestId('positions-toggle-table').click();
    await waitForSettled(positions, PAGE_TIMEOUT);
    await expect(page.getByTestId('contribution-table')).toBeVisible({timeout: PAGE_TIMEOUT});
}

/** A Performance row on a broker the user owns — checked, not inferred from the row being there. */
async function ownedPerformanceRow(page: Page, owned: readonly number[]): Promise<{rowId: string; brokerId: number; assetId: number}> {
    const rowIds = await contributionRowIds(page);
    const rowId = rowIds.find((id) => owned.includes(parseRowId(id).brokerId));
    if (!rowId) throw new Error(`No Performance row on an owned broker (owned: ${owned.join(', ') || 'none'}; rows: ${rowIds.join(', ')}). Check populate_mock_data.py.`);
    return {rowId, ...parseRowId(rowId)};
}

/** The row's «Analizza lotti», the way a user opens it: right click, then the menu action. Ends on the panel loaded. */
async function analyzeLots(page: Page, rowId: string): Promise<Locator> {
    await page.getByTestId('contribution-table').locator(`tbody tr[data-row-id="${rowId}"]`).click({button: 'right'});
    await page.getByTestId('context-menu-action-analyze-lots').click();
    const panel = page.getByTestId('lots-analysis-panel');
    await expect(panel).toBeVisible({timeout: PAGE_TIMEOUT});
    await expect(panel.getByTestId('lots-analysis-panel-loading')).toHaveCount(0, {timeout: PAGE_TIMEOUT});
    return panel;
}

/** Leaves the Dashboard through the sidebar and waits for Transactions to be the page. */
async function goToTransactions(page: Page): Promise<void> {
    await page.getByTestId('nav-transactions').click();
    const transactions = page.getByTestId('transactions-page');
    await expect(transactions).toBeVisible({timeout: PAGE_TIMEOUT});
    await waitForSettled(transactions, PAGE_TIMEOUT);
}

/** A body as a key: object keys and `broker_ids` sorted. Two equal keys are the same question. */
function canonical(body: object): string {
    const sortKeys = (value: unknown): unknown =>
        Array.isArray(value)
            ? value.map(sortKeys)
            : value !== null && typeof value === 'object'
              ? Object.fromEntries(
                    Object.entries(value)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([key, entry]) => [key, sortKeys(entry)]),
                )
              : value;
    const copy = {...(body as Record<string, unknown>)};
    if (Array.isArray(copy.broker_ids)) copy.broker_ids = [...(copy.broker_ids as number[])].sort((left, right) => left - right);
    return JSON.stringify(sortKeys(copy));
}

function repeated(bodies: readonly object[]): string[] {
    const counts = new Map<string, number>();
    for (const body of bodies) counts.set(canonical(body), (counts.get(canonical(body)) ?? 0) + 1);
    return [...counts].filter(([, count]) => count > 1).map(([key, count]) => `${count}× ${key}`);
}

/** Every body asks a non-empty broker scope inside the owned set. */
function scopeViolations(bodies: readonly {broker_ids?: number[]}[], allowed: ReadonlySet<number>): string[] {
    return bodies.filter((body) => !Array.isArray(body.broker_ids) || body.broker_ids.length === 0 || body.broker_ids.some((id) => !allowed.has(id))).map((body) => JSON.stringify(body));
}

/**
 * Every risk body that is not a portfolio question over exactly the brokers the user owns, `broker_ids` compared as a
 * set. `readings` are the owned set as the backend listed it on both sides of the page's own read: a neighbour may
 * create or delete a broker of this user in between, so the scope must equal one of them — the one set, when they
 * agree. A reading that came back empty matches nothing: to the backend an empty `broker_ids`, like a missing one, is
 * every broker the user can access.
 */
function ownedScopeViolations(bodies: readonly RiskBody[], readings: readonly (readonly number[])[]): string[] {
    const owned = new Set(readings.filter((ids) => ids.length > 0).map((ids) => canonical({broker_ids: ids})));
    return bodies
        .filter((body) => {
            const ids = body.scope?.broker_ids;
            return body.scope?.kind !== 'portfolio' || !Array.isArray(ids) || !owned.has(canonical({broker_ids: ids}));
        })
        .map((body) => JSON.stringify(body.scope ?? null));
}

test.describe('Dashboard page cache (R2 / N, phase 1)', () => {
    test('a return with nothing changed asks nothing again, and the KPI shows its value at once', async ({page}) => {
        test.setTimeout(120_000);
        const traffic = recordTraffic(page);
        await stubLivePrice(page);
        try {
            await login(page, TEST_USER);
            await navigateTo(page, '/dashboard');
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            const noted = await settledHeroText(page);
            await page.getByTestId('dashboard-tab-risk').click();
            await riskSettled(page);

            await goToTransactions(page);
            const before = mark(traffic);
            await armHeroProbe(page);
            await page.getByTestId('nav-dashboard').click();

            await expect(periodPnlHero(page), 'the Period P&L hero never became visible after the return').toBeVisible({timeout: PAGE_TIMEOUT});
            const firstSight = await heroAtFirstSight(page);
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            expect(traffic.reports.slice(before.reports), 'a return with nothing changed asked for the report again').toEqual([]);
            expect(firstSight, 'the cached KPI counted up from zero instead of appearing at its value').toBe(noted);

            await page.getByTestId('dashboard-tab-risk').click();
            await riskSettled(page);
            expect(traffic.riskQueries.slice(before.riskQueries), 'a return with nothing changed asked the risk again').toEqual([]);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    test('back from an asset whose live price ticked: the old figures are on screen while the refresh is held, one request per key', async ({page}) => {
        test.setTimeout(180_000);
        const traffic = recordTraffic(page);
        const live = await stubLivePrice(page);
        let gate: Awaited<ReturnType<typeof holdRefreshes>> | null = null;
        try {
            await login(page, TEST_USER);
            await navigateTo(page, '/dashboard');
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            const noted = await settledHeroText(page);
            await page.getByTestId('dashboard-tab-risk').click();
            await riskSettled(page);

            // The developer's path: Positions → Performance → row → «Analizza lotti» → «Vedi asset».
            await openPerformanceTable(page);
            const owned = await ownedBrokerIds(page);
            const {rowId, assetId} = await ownedPerformanceRow(page, owned);
            const lotsPanel = await analyzeLots(page, rowId);
            await expect(page).toHaveURL(new RegExp(`[?&]asset=${assetId}(?:&|$)`));
            await lotsPanel.getByTestId('lots-analysis-panel-asset-link').click();
            const detail = page.getByTestId('asset-detail-page');
            await expect(detail).toBeVisible({timeout: PAGE_TIMEOUT});
            await waitForSettled(detail, PAGE_TIMEOUT);
            await expect.poll(() => live.served, {message: 'the asset page never asked the live price: the trigger of this path did not happen', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);

            gate = await holdRefreshes(page);
            const before = mark(traffic);
            await page.getByTestId('asset-detail-back-btn').click();
            await expect(page.getByTestId('dashboard-positions-tab'), 'the ‹ arrow did not return to the Positions tab').toBeVisible({timeout: PAGE_TIMEOUT});

            // While the refresh is held: the cached Performance rows, not a skeleton…
            await expect(page.getByTestId('contribution-table').locator(`tbody tr[data-row-id="${rowId}"]`), 'the Performance table shows a skeleton while its refresh is held, instead of the rows it had').toBeVisible({timeout: 10_000});
            expect(repeated(traffic.reports.slice(before.reports)), 'the same report was asked more than once: the refresh is not shared per key').toEqual([]);

            // …the cached KPI at its pre-trip value, on its first visible frame…
            await armHeroProbe(page);
            await page.getByTestId('dashboard-tab-panoramica').click();
            await expect(periodPnlHero(page), 'the KPIs show a skeleton while the refresh is held').toBeVisible({timeout: 10_000});
            expect(await heroAtFirstSight(page), 'the KPI is not the cached figure on its first frame (a skeleton, or a count from zero)').toBe(noted);

            // …and the cached risk cards, one refresh per question at most.
            await page.getByTestId('dashboard-tab-risk').click();
            const riskPanel = page.getByTestId('risk-levels-panel');
            await expect(riskPanel.getByTestId('risk-l1-cards'), 'the risk levels show a skeleton while their refresh is held').toBeVisible({timeout: 10_000});
            await expect(riskPanel.getByTestId('risk-l1-loading')).toHaveCount(0);
            const modes = traffic.riskQueries.slice(before.riskQueries).map((body) => body.mode ?? '(no mode)');
            expect(
                modes.filter((mode, index) => modes.indexOf(mode) !== index),
                `a risk question was asked more than once (${modes.join(', ')})`,
            ).toEqual([]);

            gate.release();
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            await riskSettled(page);
        } finally {
            gate?.release();
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    test('back on the Positions tab, the Performance table and the lots ask only for the brokers the user owns', async ({page}) => {
        test.setTimeout(120_000);
        const traffic = recordTraffic(page);
        await stubLivePrice(page);
        try {
            await login(page, TEST_USER);
            await navigateTo(page, '/dashboard');
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            await openPerformanceTable(page);
            const ownedBefore = await ownedBrokerIds(page);
            const {rowId, assetId} = await ownedPerformanceRow(page, ownedBefore);
            await analyzeLots(page, rowId);
            await expect(page).toHaveURL(new RegExp(`[?&]asset=${assetId}(?:&|$)`));

            // Out through the sidebar, back with the browser's own Back.
            await goToTransactions(page);
            const before = mark(traffic);
            await page.goBack();
            await expect(page.getByTestId('dashboard-positions-tab'), 'Back did not return to the Positions tab').toBeVisible({timeout: PAGE_TIMEOUT});
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            await waitForSettled(page.getByTestId('positions-panel'), PAGE_TIMEOUT);
            const lotsPanel = page.getByTestId('lots-analysis-panel');
            await expect(lotsPanel).toBeVisible({timeout: PAGE_TIMEOUT});
            await expect(lotsPanel.getByTestId('lots-analysis-panel-loading')).toHaveCount(0, {timeout: PAGE_TIMEOUT});

            // Owned now or when the test began: a neighbour may create or delete a broker of this user meanwhile.
            const allowed = new Set([...ownedBefore, ...(await ownedBrokerIds(page))]);
            const foreignRows = (await contributionRowIds(page)).filter((id) => !allowed.has(parseRowId(id).brokerId));
            expect(foreignRows, `the Performance table shows positions on brokers the user does not own (owned: ${[...allowed].join(', ')})`).toEqual([]);
            expect(scopeViolations(traffic.reports.slice(before.reports), allowed), 'a report asked after the return has no broker_ids, or brokers the user does not own: the backend widens it to every broker the user can see').toEqual([]);
            expect(scopeViolations(traffic.lots.slice(before.lots), allowed), 'a lots analysis asked after the return has no broker_ids, or brokers the user does not own').toEqual([]);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    test('the currency and the broker filter are restored on return, and «Aggiorna» refreshes under them', async ({page}) => {
        test.setTimeout(120_000);
        const traffic = recordTraffic(page);
        await stubLivePrice(page);
        try {
            await login(page, TEST_USER);
            await navigateTo(page, '/dashboard');
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            const owned = await ownedBrokerIds(page);
            if (owned.length < 2) throw new Error(`${TEST_USER.username} owns ${owned.length} broker(s): a broker filter needs two to differ from "all". Check populate_mock_data.py.`);
            const brokerId = owned[0];

            const currency = page.getByTestId('dashboard-target-currency-trigger');
            await expect(currency, 'precondition: the Dashboard does not open in USD already').not.toContainText('USD');
            await currency.click();
            await page.getByTestId('dashboard-target-currency').getByTestId('search-select-option-USD').click();
            await optionsClosed(page);
            await expect.poll(() => traffic.reports.some((body) => body.target_currency === 'USD'), {message: 'choosing USD asked no report in USD', timeout: PAGE_TIMEOUT}).toBe(true);
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);

            await page.getByTestId('broker-filter-trigger').click();
            const item = page.getByTestId(`broker-filter-item-${brokerId}`);
            await item.click();
            await page.getByTestId('broker-filter-trigger').click();
            await expect(item).toBeHidden();
            await expect
                .poll(() => traffic.reports.some((body) => body.target_currency === 'USD' && canonical({broker_ids: body.broker_ids}) === canonical({broker_ids: [brokerId]})), {
                    message: 'the broker filter never asked its report (USD, one broker)',
                    timeout: PAGE_TIMEOUT,
                })
                .toBe(true);
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);

            await goToTransactions(page);
            await page.getByTestId('nav-dashboard').click();
            await expect(dashboard(page)).toBeVisible({timeout: PAGE_TIMEOUT});
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            await expect(currency, 'the currency restarted from the base currency on return').toContainText('USD');

            const before = mark(traffic);
            await page.getByTestId('sync-button').click();
            await expect.poll(() => traffic.reports.length - before.reports, {message: '«Aggiorna» asked no report', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);
            const refreshed = traffic.reports[before.reports];
            expect(refreshed.target_currency, '«Aggiorna» refreshed in another currency than the one restored').toBe('USD');
            expect(refreshed.broker_ids, '«Aggiorna» refreshed another broker scope than the filter restored').toEqual([brokerId]);
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    test('«Aggiorna» on the Risk tab asks the risk again', async ({page}) => {
        test.setTimeout(120_000);
        const traffic = recordTraffic(page);
        await stubLivePrice(page);
        try {
            await login(page, TEST_USER);
            await navigateTo(page, '/dashboard');
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            await page.getByTestId('dashboard-tab-risk').click();
            await riskSettled(page);

            const before = mark(traffic);
            await page.getByTestId('sync-button').click();

            await expect.poll(() => traffic.riskQueries.length - before.riskQueries, {message: '«Aggiorna» on the Risk tab reloaded the report and left the risk as it was cached', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            await riskSettled(page);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    /**
     * The risk scope, decided on 07/10 («Solo i broker posseduti, come il resto della Dashboard»): the Risk tab asks over
     * every broker the user owns, as the rest of the Dashboard does, and never with no `broker_ids`, which the backend
     * widens to every broker the user can see, viewer and editor ones included. All of them whatever the broker filter:
     * the filter narrows the report, while the risk stays the whole portfolio, as the panel's subtitle says.
     *
     * A document load starts with every store empty, so the panel may ask only once the owned brokers are known. The
     * owned set is read before that load and again once the page has asked (`ownedScopeViolations` says why both).
     */
    test('the Risk tab asks for exactly the brokers the user owns: on a cold load, and still all of them with a broker filter on', async ({page}) => {
        test.setTimeout(120_000);
        const traffic = recordTraffic(page);
        await stubLivePrice(page);
        try {
            await login(page, TEST_USER);
            const readings = [await ownedBrokerIds(page)];
            if (readings[0].length < 2) throw new Error(`${TEST_USER.username} owns ${readings[0].length} broker(s): a broker filter needs two to differ from "all". Check populate_mock_data.py.`);
            const brokerId = readings[0][0];
            const ownedText = () => readings.map((ids) => `[${ids.join(', ')}]`).join(' or ');

            // The cold load, straight onto the Risk tab.
            await navigateTo(page, '/dashboard?tab=rischio');
            await expect.poll(() => traffic.riskQueries.length, {message: 'the cold load of the Risk tab asked no risk', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);
            readings.push(await ownedBrokerIds(page));
            const panel = await riskSettled(page);
            expect(ownedScopeViolations(traffic.riskQueries, readings), `on a cold load, a risk question is not over exactly the brokers the user owns (owned: ${ownedText()})`).toEqual([]);

            // A broker filter on one owned broker: the report follows it…
            await expect(panel.getByTestId('risk-levels-title')).toBeVisible();
            await expect(panel.getByTestId('risk-scope-label'), 'precondition: no broker filter is on yet').toHaveCount(0);
            const beforeFilter = mark(traffic);
            await page.getByTestId('broker-filter-trigger').click();
            const item = page.getByTestId(`broker-filter-item-${brokerId}`);
            await item.click();
            await page.getByTestId('broker-filter-trigger').click();
            await expect(item).toBeHidden();
            await expect
                .poll(() => traffic.reports.slice(beforeFilter.reports).some((body) => canonical({broker_ids: body.broker_ids}) === canonical({broker_ids: [brokerId]})), {
                    message: 'the broker filter never asked its report (one broker)',
                    timeout: PAGE_TIMEOUT,
                })
                .toBe(true);
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            await expect(panel.getByTestId('risk-scope-label'), 'with the filter on, the risk panel does not say it still reads the whole portfolio').toBeVisible();

            // …and «Aggiorna» asks the risk again, still over every broker the user owns.
            const before = mark(traffic);
            await page.getByTestId('sync-button').click();
            await expect.poll(() => traffic.riskQueries.length - before.riskQueries, {message: '«Aggiorna» on the Risk tab asked no risk', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);
            await expect(panel.getByTestId('risk-refresh-button'), 'the risk asked again by «Aggiorna» never landed').toBeEnabled({timeout: PAGE_TIMEOUT});
            await riskSettled(page);
            await waitForSettled(dashboard(page), PAGE_TIMEOUT);
            readings.push(await ownedBrokerIds(page));
            // Every question since the filter went on, the refresh's among them: the filter must not narrow the risk either.
            expect(ownedScopeViolations(traffic.riskQueries.slice(beforeFilter.riskQueries), readings), `with a broker filter on, a risk question is not over every broker the user owns (owned: ${ownedText()})`).toEqual([]);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });
});
