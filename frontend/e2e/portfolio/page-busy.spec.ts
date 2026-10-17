/**
 * Page busy (Y11, developer decision 48 / P3): a page's Refresh button waits for the «big» requests of that page.
 *
 * The first wiring: the Dashboard's `sync-button` and the Files page's `files-refresh-button` are disabled, and publish
 * `data-busy="true"`, while a request the page decided to make is pending — a period change, a Refresh, a tab change —
 * with no click on the button needed; and only the requests of the page on screen: a route change drops the old page's
 * (`onNavigate` → `pageBusy.reset()`, `routes/(app)/+layout.svelte`). Then a broker's page (`broker-refresh`), the list
 * of brokers (`brokers-refresh`) and Transactions (`tx-refresh-button`): each Refresh holds its own button until what it
 * asked again is back — the broker's overview report, the list of brokers, the list of transactions.
 *
 * A localhost answer lands before an assertion can look, so every busy state here is made observable by holding the
 * request that causes it (`page.route`, let through with `route.fallback()` when the test decides): the state belongs
 * to the test instead of a race. A hold picks its request by method, path and body — the one the trigger sends, checked
 * rather than assumed — and lets every other request through; its `held` list is the presence barrier, so a trigger
 * that never reaches the network fails by name instead of leaving a button that was never asked to wait. Every hold is
 * released and unrouted in `finally`: no request outlives its test.
 *
 * And a request the button must not wait for (P3): the reload in background of the Dashboard or of a broker's page
 * once the server has caught up on prices (Z5, Z-13: `notifyPricesCaughtUp()` sends `{kind: 'prices'}`, and the
 * page's `reloadAfterPriceCatchUp()` asks its report again without `pageBusy`). The catch-up is a stub's, on the
 * mechanism of price-refresh-reload.spec.ts: one route on every API path answers the status route in the browser and
 * gives every other answer back from the real backend with the header the case sets — or with none, a real one removed
 * too, so that a catch-up the lane really runs cannot reach the case. Every value the button's `data-busy` takes is
 * recorded in the page meanwhile, so «it never waited» means never, not «it was not waiting when the test looked»; the
 * period change that follows in the same page is the control that the button, and the recording, do move. Neither page's
 * root says that the reload is back: a broker's page publishes no `data-busy` on its root, and the Dashboard's keeps it
 * `false` through the reload in background (Z-18: nobody asked for that load, and a screen reader must not announce
 * «busy» for it), checked while the reload is held. On both the landing is read from a count of the reports, kept in the
 * page.
 *
 * And what such a reload cascades into (N55, `pageBusy.join`). The reload's report drops what a panel loaded lazily —
 * the P&L candles of the growth chart, the contribution of the positions panel — and a panel left on that view (saved
 * per user in this context's localStorage, set here through the panel's own toggles) asks it again at once. Such a load
 * joins with a token only when the page is waiting already: after a reload in background it runs alone, and the button
 * stays idle while it is held too; after a period change it joins the period's token, and the button waits for it once
 * the period's own report is back. Each cascaded request is held by its body (the section it asks alone, no history),
 * and its sameness with the one on screen is checked.
 *
 * And what the N55 case on the Dashboard takes for granted, pinned on its own (Y-16): a saved candles view loaded from
 * scratch asks its candles as the chart mounts, before the owned brokers are known, and is refused (F2). The ask is
 * re-armed by the brokers themselves: with their list held no candles are asked, and once it is let through they are
 * asked, and drawn.
 *
 * And the asset pages, the last lot of Y11. An asset's detail page (`asset-detail-refresh-btn`): Refresh and a period
 * change hold its button until the chart's prices they asked are back; the reload that follows the page's own Sync does
 * not (P3) — from the chart's prices to the asset's metadata, every value of the button recorded as above, with a period
 * change in the same page as the control. On the price chart of the Overview tab: on the Risk tab the risk panel reloads
 * under a token of its own after a sync, as the Dashboard's panels do after its banner's. The Assets list on its
 * Correlation tab: «Reload All» (`risk-reload-button`), the page's Refresh there, holds its button until the section it
 * asked again is back — the correlation section's base wave, held by its shape. Each of these buttons is first checked to
 * publish a `data-busy` at all, so that a button that follows nothing says so instead of timing out on an absent value.
 *
 * Busy or idle is read only from `data-busy` and `disabled`: no class (the spin is one), no colour, no text.
 *
 * Read-only on the shared database: TEST_USER, nothing written. «Aggiorna» re-reads and syncs nothing
 * (`requestPortfolioRefresh` is a client-side mark); the period and the Files tab live in this context's own
 * sessionStorage and localStorage, and the filters the Transactions Refresh clears in this page's URL. The broker is the
 * mock's broker with positions, found by name through `page.request`, never by position. On the asset pages nothing
 * reaches a provider either: the live-price poll, a write (it stores today's candle), is refused at the network; the
 * page's Sync is answered in the browser — accepted, nothing written — and so is the provider catalogue its dialog asks,
 * empty; the laboratory's selection lives in this context's localStorage. The asset is the mock's Apple, found by name
 * through `page.request`.
 */

import type {APIResponse, Route} from '@playwright/test';
import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
const UPLOADS_PATH = `${API}/uploads`;
const BROKER_REPORTS_PATH = `${API}/brokers/import/files`;
const BROKERS_PATH = `${API}/brokers`;
const TRANSACTIONS_PATH = `${API}/transactions`;
/** The mock's broker with positions, shared with TEST_USER (populate_mock_data.py): found by name, never by position. */
const BROKER_WITH_HOLDINGS = 'Interactive Brokers';
/**
 * The price catch-up's status route, header and notice (`lib/features/price-refresh/priceRefresh.ts`), written out as
 * price-refresh-reload.spec.ts writes them: that module imports `$lib` aliases and runes, which Playwright's loader does
 * not run, and a spec pins the contract rather than following the code.
 */
const CATCH_UP_STATUS_PATH = `${API}/system/price-refresh`;
const CATCH_UP_HEADER = 'x-librefolio-price-refresh';
const CATCH_UP_NOTICE = '[data-testid="instance-notice"][data-notice-id="liveUpdates.priceRefresh"]';

/** A page load, or a round trip to the backend (the report is computed on the spot). A deadline, never a delay. */
const ROUND_TRIP_MS = 30_000;
/** Login, a full page load and a held round trip; the route-change case pays two pages. */
const TEST_MS = 120_000;

type ReportBody = {
    include_history?: boolean;
    include_pnl_candles?: boolean;
    include_positions_contribution?: boolean;
    broker_ids?: number[];
    date_range?: {start?: string; end?: string};
};

/**
 * The report that draws the Dashboard, or a broker's overview: history on. The contribution and the P&L candles ask
 * without it.
 */
function isMainReport(request: Request): boolean {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== REPORT_PATH) return false;
    return (request.postDataJSON() as ReportBody | null)?.include_history === true;
}

/** The overview of broker `brokerId` (`loadOverview` on its page): a main report, for that broker alone. */
function isBrokerOverview(brokerId: number): (request: Request) => boolean {
    return (request) => {
        if (!isMainReport(request)) return false;
        const ids = (request.postDataJSON() as ReportBody | null)?.broker_ids ?? [];
        return ids.length === 1 && ids[0] === brokerId;
    };
}

/** A report that asks one lazy section alone, with no history: the P&L candles, or the contribution. */
function isReportOf(request: Request, section: 'include_pnl_candles' | 'include_positions_contribution'): boolean {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== REPORT_PATH) return false;
    const body = request.postDataJSON() as ReportBody | null;
    return body?.[section] === true && body.include_history === false;
}

/** The P&L candles the growth chart asks in its candles view (`loadPnlCandles` on the Dashboard). */
function isPnlCandles(request: Request): boolean {
    return isReportOf(request, 'include_pnl_candles');
}

/** Any report that asks the P&L candles, whatever else it asks: the lazy load of `isPnlCandles`, or one that would carry them beside the history. */
function asksPnlCandles(request: Request): boolean {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== REPORT_PATH) return false;
    return (request.postDataJSON() as ReportBody | null)?.include_pnl_candles === true;
}

/** The contribution the positions panel of broker `brokerId` asks in its Performance view (`loadContribution` on its page), for that broker alone. */
function isBrokerContribution(brokerId: number): (request: Request) => boolean {
    return (request) => {
        if (!isReportOf(request, 'include_positions_contribution')) return false;
        const ids = (request.postDataJSON() as ReportBody | null)?.broker_ids ?? [];
        return ids.length === 1 && ids[0] === brokerId;
    };
}

/** The period a report asks for, as one comparable string. */
function periodOf(request: Request): string {
    const range = (request.postDataJSON() as ReportBody | null)?.date_range;
    return `${range?.start ?? ''}..${range?.end ?? ''}`;
}

/** Every report `picks` chooses — a main report unless told otherwise — that the page sends from now on, in order. */
function recordMainReports(page: Page, picks: (request: Request) => boolean = isMainReport): Request[] {
    const sent: Request[] = [];
    page.on('request', (request) => {
        if (picks(request)) sent.push(request);
    });
    return sent;
}

const isGet = (request: Request): boolean => request.method() === 'GET';

/** The list of brokers (`refreshAllBrokers`, brokerStore): always asked with the inaccessible ones included. */
function isBrokerList(request: Request): boolean {
    return isGet(request) && new URL(request.url()).searchParams.get('include_inaccessible') === 'true';
}

/**
 * The list of transactions (`loadMainRows`): every transaction the user sees, asked with no query — the filters are
 * client-side (W28). The partner rows and a highlighted row are asked by `ids`, and are not it.
 */
function isTransactionList(request: Request): boolean {
    return isGet(request) && new URL(request.url()).search === '';
}

/** Requests the test holds, and owns until it lets them through. */
interface Hold {
    /** Every request held so far, in arrival order, the released ones included. */
    readonly held: Request[];
    /** How many are held still. */
    pending(): number;
    /** Lets every held request through, on to the page's other routes as if it had never been held; from then on the hold lets everything through. */
    release(): Promise<void>;
    /** `release()`, then the route goes: for `finally`. Safe to call twice. */
    dispose(): Promise<void>;
}

/** Holds the requests to `path` that `picks` chooses, from now until `release()`; every other request goes through untouched. */
async function hold(page: Page, path: string, picks: (request: Request) => boolean): Promise<Hold> {
    const held: Request[] = [];
    const waiting: Route[] = [];
    let open = false;
    let routed = true;
    const matches = (url: URL): boolean => url.pathname === path;
    const handler = async (route: Route): Promise<void> => {
        if (open || !picks(route.request())) {
            await route.fallback();
            return;
        }
        held.push(route.request());
        waiting.push(route);
    };
    await page.route(matches, handler);
    const release = async (): Promise<void> => {
        open = true;
        // `fallback()`, not `continue()`: a released request goes on through the page's other routes (the catch-up stub
        // below, which decides its header) exactly as if it had never been held. A request whose page went away cannot
        // be let through any more, and there is nothing left to deliver it to.
        await Promise.all(waiting.splice(0).map((route) => route.fallback().catch(() => undefined)));
    };
    return {
        held,
        pending: () => waiting.length,
        release,
        dispose: async () => {
            await release();
            if (!routed) return;
            routed = false;
            await page.unroute(matches, handler);
        },
    };
}

/** The first request `gate` held: the trigger did reach the network. */
async function heldRequest(gate: Hold, what: string): Promise<Request> {
    await expect.poll(() => gate.held.length, {message: `${what} never reached the network`, timeout: ROUND_TRIP_MS}).toBeGreaterThan(0);
    return gate.held[0];
}

/** Busy, as the user meets it: the button says it is waiting, and cannot be pressed. */
async function expectBusy(button: Locator, why: string): Promise<void> {
    await expect(button, why).toHaveAttribute('data-busy', 'true');
    await expect(button, why).toBeDisabled();
}

/** Idle: nothing of this page is pending, and the button can be pressed again. A round trip away at most. */
async function expectIdle(button: Locator, why: string): Promise<void> {
    await expect(button, why).toHaveAttribute('data-busy', 'false', {timeout: ROUND_TRIP_MS});
    await expect(button, why).toBeEnabled();
}

/**
 * The Dashboard, loaded from scratch and settled: its first report in (the root's `data-busy`), and nothing of the page
 * pending (the button's). On the overview tab, where no risk or lots panel adds loads of its own to the button.
 */
async function openDashboard(page: Page): Promise<Locator> {
    await navigateTo(page, '/dashboard?tab=panoramica');
    await waitForSettled(page.getByTestId('dashboard-page'), ROUND_TRIP_MS);
    const refresh = page.getByTestId('sync-button');
    await expectIdle(refresh, 'the Dashboard settled with its Refresh button still waiting');
    return refresh;
}

/** The Files page on `tab`, loaded from scratch and settled: its list in, and nothing of the page pending. */
async function openFiles(page: Page, tab: 'static' | 'brim'): Promise<Locator> {
    await navigateTo(page, `/files?tab=${tab}`);
    await waitForSettled(page.getByTestId('files-page'), ROUND_TRIP_MS);
    await expect(page.getByTestId(`files-tab-${tab}`), `the Files page did not open on its ${tab} tab`).toHaveAttribute('aria-selected', 'true');
    const refresh = page.getByTestId('files-refresh-button');
    await expectIdle(refresh, 'the Files page settled with its Refresh button still waiting');
    return refresh;
}

/** The id of a broker TEST_USER sees, by name, read with `page.request`: no route of the page intercepts it. */
async function brokerIdByName(page: Page, name: string): Promise<number> {
    const response = await page.request.get(BROKERS_PATH);
    expect(response.ok(), `GET ${BROKERS_PATH} → HTTP ${response.status()}`).toBe(true);
    const items = ((await response.json()) as {items?: Array<{id: number; name: string}>}).items ?? [];
    const broker = items.find((item) => item.name === name);
    if (!broker) throw new Error(`${name} is the mock's broker with positions, shared with ${TEST_USER.username}: check populate_mock_data.py (brokers seen: ${items.map((item) => item.name).join(', ') || 'none'})`);
    return broker.id;
}

/**
 * A broker's page on `tab`, loaded from scratch and settled. Its root publishes no `data-busy`: the button's is the
 * barrier, held by the first load (`broker-first-load`) until the broker, its overview and the broker and asset caches
 * are all in. On the overview tab, where no risk or lots panel adds loads of its own to the button — or on the
 * positions tab, whose lots panel stays closed.
 */
async function openBrokerDetail(page: Page, brokerId: number, tab: 'panoramica' | 'posizioni' = 'panoramica'): Promise<Locator> {
    await navigateTo(page, `/brokers/${brokerId}?tab=${tab}`);
    await expect(page.getByTestId('broker-name'), `the page of broker ${brokerId} did not load its broker`).toBeVisible({timeout: ROUND_TRIP_MS});
    const refresh = page.getByTestId('broker-refresh');
    await expectIdle(refresh, "the broker's page settled with its Refresh button still waiting");
    return refresh;
}

/**
 * The list of brokers, loaded from scratch and settled: the brokers and the report of their cards in (the root's
 * `data-busy`), and nothing of the page pending (the button's).
 */
async function openBrokers(page: Page): Promise<Locator> {
    await navigateTo(page, '/brokers');
    await waitForSettled(page.getByTestId('brokers-page'), ROUND_TRIP_MS);
    const refresh = page.getByTestId('brokers-refresh');
    await expectIdle(refresh, 'the list of brokers settled with its Refresh button still waiting');
    return refresh;
}

/**
 * Transactions with no filter, loaded from scratch and settled: the reference lists and the transactions in (the root's
 * `data-busy`), and nothing of the page pending (the button's).
 */
async function openTransactions(page: Page): Promise<Locator> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), ROUND_TRIP_MS);
    const refresh = page.getByTestId('tx-refresh-button');
    await expectIdle(refresh, 'Transactions settled with its Refresh button still waiting');
    return refresh;
}

/** `GET /api/v1/system/price-refresh` (backend/app/schemas/sleep_wake.py, PriceRefreshResponse). */
interface CatchUpStatus {
    state: 'idle' | 'starting' | 'running';
    reason: 'startup' | 'return' | 'wake' | null;
    job: string | null;
    since: string | null;
    last_finished_at: string | null;
    last_refreshed: boolean;
}

/** What the catch-up stub says — changed by the case as it goes — and the states it has served, in order. */
interface CatchUp {
    /** On every other API answer; null: none, a real one removed too. */
    header: 'running' | null;
    status: CatchUpStatus;
    served: Array<CatchUpStatus['state']>;
}

/** A catch-up running its live-price job. */
function catchUpRunning(): CatchUpStatus {
    return {state: 'running', reason: 'return', job: 'current_price', since: new Date().toISOString(), last_finished_at: null, last_refreshed: false};
}

/** The catch-up is over and updated something: the answer on which the tracker sends `{kind: 'prices'}`. */
function catchUpOverWithUpdates(): CatchUpStatus {
    return {state: 'idle', reason: null, job: null, since: null, last_finished_at: new Date().toISOString(), last_refreshed: true};
}

/** Not passed on: what described the real body in transit (`route.fetch()` hands it over decoded), and any real catch-up header. */
const NOT_PASSED_ON = new Set(['content-encoding', 'content-length', 'transfer-encoding', CATCH_UP_HEADER]);

/**
 * A running catch-up as the page sees it, on the mechanism of price-refresh-reload.spec.ts (`simulateCatchUp`): the
 * status route answered in the browser with `catchUp.status`; every other API request sent to the real backend and given
 * back with its real body and `catchUp.header`. Install it after the sign-in, before the page under test loads, and
 * before any hold: a hold registered later sees a request first, and a request it lets through comes on here.
 */
async function simulateCatchUp(page: Page): Promise<CatchUp> {
    const catchUp: CatchUp = {header: 'running', status: catchUpRunning(), served: []};
    await page.route('**/api/v1/**', async (route) => {
        if (new URL(route.request().url()).pathname === CATCH_UP_STATUS_PATH) {
            const status = catchUp.status;
            // Counted before it leaves: whatever the page sends because of this answer finds it counted already.
            catchUp.served.push(status.state);
            await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(status)}).catch(() => undefined);
            return;
        }
        let response: APIResponse;
        try {
            response = await route.fetch();
        } catch {
            // The page went away with the request in flight: there is nobody to answer.
            await route.abort().catch(() => undefined);
            return;
        }
        // Read when the answer leaves, not when the request came: an answer that lands after the case switched carries the new value.
        const headers = Object.fromEntries(Object.entries(response.headers()).filter(([name]) => !NOT_PASSED_ON.has(name.toLowerCase())));
        if (catchUp.header !== null) headers[CATCH_UP_HEADER] = catchUp.header;
        await route.fulfill({response, headers}).catch(() => undefined);
    });
    return catchUp;
}

/**
 * Every value `data-busy` takes on `testId` from now on, kept in the page by a MutationObserver: «it never waited» then
 * means never in the window, not «it was not waiting when the test looked». Returns a reader of the values seen so far.
 */
async function recordBusy(page: Page, testId: string): Promise<() => Promise<string[]>> {
    const key = `__lfSpecBusy:${testId}`;
    await page.evaluate(
        ({key, selector}) => {
            const seen: string[] = [];
            Object.defineProperty(window, key, {value: seen, configurable: true});
            const note = (element: Element): void => {
                seen.push(element.getAttribute('data-busy') ?? '');
            };
            new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.type === 'attributes' && mutation.target instanceof Element && mutation.target.matches(selector)) note(mutation.target);
                    for (const node of Array.from(mutation.addedNodes)) {
                        if (!(node instanceof Element)) continue;
                        if (node.matches(selector)) note(node);
                        for (const inner of Array.from(node.querySelectorAll(selector))) note(inner);
                    }
                }
            }).observe(document, {subtree: true, childList: true, attributes: true, attributeFilter: ['data-busy']});
        },
        {key, selector: `[data-testid="${testId}"]`},
    );
    return () => page.evaluate((key) => [...((window as unknown as Record<string, string[] | undefined>)[key] ?? [])], key);
}

/** The reports the page has sent since `countReports`, and how many of them have landed. */
interface ReportCount {
    sent: number;
    landed: number;
}

/**
 * Every report (`POST /portfolio/report`) the page sends from now on, and how many of them have landed — in the page,
 * not only on the network: a report counts as landed one task after its `loadend`, once the microtasks its answer set
 * off (axios, the store, the page's own load, the DOM it redraws) have run. How a test knows that a report it let
 * through is back, on a page whose root publishes no `data-busy`. Counted on XHR, the transport axios uses: a test
 * checks that its report is counted in flight before it believes a landing.
 */
async function countReports(page: Page): Promise<() => Promise<ReportCount>> {
    const key = '__lfSpecReports';
    await page.evaluate(
        ({key, path}) => {
            const count = {sent: 0, landed: 0};
            Object.defineProperty(window, key, {value: count, configurable: true});
            const reports = new WeakSet<XMLHttpRequest>();
            const nativeOpen = XMLHttpRequest.prototype.open;
            const nativeSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function (this: XMLHttpRequest, ...args: unknown[]) {
                let pathname = '';
                try {
                    pathname = new URL(String(args[1]), window.location.href).pathname;
                } catch {
                    // Not a URL a report could have gone to.
                }
                if (String(args[0]).toUpperCase() === 'POST' && pathname === path) reports.add(this);
                else reports.delete(this);
                return Reflect.apply(nativeOpen, this, args);
            } as XMLHttpRequest['open'];
            XMLHttpRequest.prototype.send = function (this: XMLHttpRequest, ...args: unknown[]) {
                if (reports.has(this)) {
                    count.sent += 1;
                    // Added at the send, so after axios's own handler, set before it: the answer's microtasks run in between.
                    this.addEventListener('loadend', () => {
                        const nextTask = new MessageChannel();
                        nextTask.port1.onmessage = () => {
                            count.landed += 1;
                            nextTask.port1.close();
                        };
                        nextTask.port2.postMessage(null);
                    });
                }
                return Reflect.apply(nativeSend, this, args);
            } as XMLHttpRequest['send'];
        },
        {key, path: REPORT_PATH},
    );
    return () =>
        page.evaluate((key) => {
            const count = (window as unknown as Record<string, ReportCount | undefined>)[key];
            if (count === undefined) throw new Error('the report count is gone: a full load since countReports() started a fresh document');
            return {...count};
        }, key);
}

/**
 * Waits until every report the page has sent since `reports` started counting has landed in the page, but the ones
 * still held: what was let through is back, and its answer's microtasks — the page's own load, a panel's cascade, the
 * tokens they begin and end — have run.
 */
async function landedAllBut(reports: () => Promise<ReportCount>, held: () => number, what: string): Promise<void> {
    await expect
        .poll(
            async () => {
                const count = await reports();
                return count.sent - count.landed - held();
            },
            {message: `${what} never landed in the page`, timeout: ROUND_TRIP_MS},
        )
        .toBe(0);
}

/** P3: the button is idle and can be pressed now, and no value it took since `busySeen` started recording was busy. */
async function expectNeverWaited(button: Locator, busySeen: () => Promise<string[]>, what: string): Promise<void> {
    await expect(button, `the Refresh button waits for ${what}`).toHaveAttribute('data-busy', 'false');
    await expect(button, `the Refresh button cannot be pressed during ${what}`).toBeEnabled();
    expect(await busySeen(), `the Refresh button waited at some moment of ${what}`).not.toContain('true');
}

/** A toggle that publishes `aria-pressed`, pressed unless it is already: the state is asked first, the end state asserted. */
async function pressToggle(button: Locator, why: string): Promise<void> {
    await expect(button, why).toBeVisible({timeout: ROUND_TRIP_MS});
    if ((await button.getAttribute('aria-pressed')) !== 'true') await button.click();
    await expect(button, why).toHaveAttribute('aria-pressed', 'true');
}

/**
 * Saves the growth chart's view as P&L → Candles the way a user does, through its toggles: GrowthChart writes the mode
 * and the submode per user in this context's localStorage on the click, and reads them back when it mounts.
 */
async function saveCandlesView(page: Page): Promise<void> {
    await openDashboard(page);
    const chart = page.getByTestId('growth-chart');
    await pressToggle(chart.getByTestId('growth-toggle-pnl'), 'the P&L mode of the growth chart could not be chosen');
    await pressToggle(chart.getByTestId('growth-pnl-submode-candles'), 'the candles submode of the growth chart could not be chosen');
}

/**
 * How many candles the growth chart draws with a real body: 0 until its candles are in, every bucket being the `'-'`
 * gap sentinel until then. Read from the ECharts instance the chart publishes as `__lfChart`, as dashboard.spec.ts reads it.
 */
async function candleBodies(chart: Locator): Promise<number> {
    return chart.locator('[data-chart-ready]').evaluate((node) => {
        const option = (node as unknown as {__lfChart?: {getOption?: () => {series?: unknown} | undefined}}).__lfChart?.getOption?.();
        const drawn: unknown = option?.series;
        const series = Array.isArray(drawn) ? (drawn as Array<{type?: unknown; data?: unknown} | null>) : [];
        let bodies = 0;
        for (const one of series) {
            if (one?.type !== 'candlestick' || !Array.isArray(one.data)) continue;
            bodies += one.data.filter((point) => point != null && point !== '-').length;
        }
        return bodies;
    });
}

/**
 * Saves the positions panel's view as Performance the way a user does, on the broker's positions tab: PositionsPanel
 * writes its mode per user in this context's localStorage, and reads it back when it mounts. Its toggle sets the mode
 * rather than flipping it, and publishes no pressed state: the end state is the view itself, the contribution table.
 */
async function savePerformanceView(page: Page, brokerId: number): Promise<void> {
    await openBrokerDetail(page, brokerId, 'posizioni');
    const panel = page.getByTestId('positions-panel');
    await panel.getByTestId('positions-toggle-performance').click();
    await expect(panel.getByTestId('contribution-table'), `the Performance view of broker ${brokerId} shows no contribution: check populate_mock_data.py`).toBeVisible({timeout: ROUND_TRIP_MS});
}

/**
 * Two page loads (the one that saves the view, the one under test) and up to four held requests: one load and two
 * holds more than the P3 cases the describe's budget was sized for.
 */
const CASCADE_TEST_MS = TEST_MS + 2 * ROUND_TRIP_MS;

test.describe('Page busy: the Refresh button waits for the big requests of its own page (Y11)', () => {
    test.describe.configure({timeout: TEST_MS});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('Dashboard: a period change holds the Refresh button until the report of the new period is back, with no click on it', async ({page}) => {
        const reports = recordMainReports(page);
        const refresh = await openDashboard(page);
        const asked = new Set(reports.map(periodOf));
        expect(asked.size, 'precondition: the Dashboard asked a report for the period it opened on').toBeGreaterThan(0);
        const sixMonths = page.getByTestId('date-preset-6m');
        await expect(sixMonths, 'precondition: 6M is a change of period (the Dashboard opens on 3M)').toHaveAttribute('data-active', 'false');

        // Only a report for a period the page had not asked yet: the one the click sends.
        const gate = await hold(page, REPORT_PATH, (request) => isMainReport(request) && !asked.has(periodOf(request)));
        try {
            await sixMonths.click();
            await expect(sixMonths).toHaveAttribute('data-active', 'true');
            await heldRequest(gate, 'the report of the new period');
            await expectBusy(refresh, 'the report of the new period is pending, and the Refresh button does not wait for it');

            await gate.release();
            await expectIdle(refresh, 'the report of the new period is back, and the Refresh button still waits');
        } finally {
            await gate.dispose();
        }
    });

    test('Dashboard: Refresh holds its button until the report it asked again is back', async ({page}) => {
        const refresh = await openDashboard(page);
        const gate = await hold(page, REPORT_PATH, isMainReport);
        try {
            await refresh.click();
            await heldRequest(gate, 'the report Refresh asks again');
            await expectBusy(refresh, 'Refresh asked the report again, and its button does not wait for it');

            await gate.release();
            await expectIdle(refresh, 'the refreshed report is back, and the Refresh button still waits');
        } finally {
            await gate.dispose();
        }
    });

    test('Files: Refresh holds its button until the list is back', async ({page}) => {
        const refresh = await openFiles(page, 'static');
        const gate = await hold(page, UPLOADS_PATH, isGet);
        try {
            await refresh.click();
            await heldRequest(gate, 'the list of files Refresh asks again');
            await expectBusy(refresh, 'Refresh asked the list again, and its button does not wait for it');

            await gate.release();
            await expectIdle(refresh, 'the list is back, and the Refresh button still waits');
        } finally {
            await gate.dispose();
        }
    });

    test('Files: a tab change holds the Refresh button until the list of the tab is back, with no click on it', async ({page}) => {
        const refresh = await openFiles(page, 'static');
        const brokerReports = page.getByTestId('files-tab-brim');
        const gate = await hold(page, BROKER_REPORTS_PATH, isGet);
        try {
            await brokerReports.click();
            await expect(brokerReports).toHaveAttribute('aria-selected', 'true');
            await heldRequest(gate, 'the list of broker reports the tab asks');
            await expectBusy(refresh, 'the list of the new tab is pending, and the Refresh button does not wait for it');

            await gate.release();
            await expectIdle(refresh, 'the list of the new tab is back, and the Refresh button still waits');
        } finally {
            await gate.dispose();
        }
    });

    test("a route change leaves the old page's requests behind: Files settles idle while the Dashboard's report is still held", async ({page}) => {
        const dashboardRefresh = await openDashboard(page);
        const report = await hold(page, REPORT_PATH, isMainReport);
        let list: Hold | null = null;
        try {
            await dashboardRefresh.click();
            const pendingReport = await heldRequest(report, 'the report Refresh asks again');
            await expectBusy(dashboardRefresh, "precondition: the Dashboard's Refresh button waits for its held report");

            // The Files page's own first load is held too: its button is seen waiting for its own page first, so the
            // idle reading below is the button's answer, not a button that never moves.
            list = await hold(page, UPLOADS_PATH, isGet);
            // The sidebar link: a client-side navigation, the one `onNavigate` sees. A document load would empty the
            // store by itself and prove nothing.
            await page.getByTestId('nav-files').click();
            await expect(page).toHaveURL(/\/files(?:[?#]|$)/, {timeout: ROUND_TRIP_MS});
            const filesRefresh = page.getByTestId('files-refresh-button');
            await heldRequest(list, "the Files page's first load");
            await expectBusy(filesRefresh, "the Files page's own first load is pending, and its Refresh button does not wait for it");

            await list.release();
            await waitForSettled(page.getByTestId('files-page'), ROUND_TRIP_MS);
            await expectIdle(filesRefresh, "the Files page is loaded, and its Refresh button still waits — for the Dashboard's report");
            // The reading above was taken with the Dashboard's report still held, and still alive in the page.
            expect(report.pending(), "the Dashboard's report was let through before the reading").toBe(1);
            expect(pendingReport.failure(), "the Dashboard's report failed before the reading, which would have ended its wait by itself").toBeNull();
        } finally {
            await list?.dispose();
            await report.dispose();
        }
    });

    test('Dashboard: the reload in background after a price catch-up never makes the Refresh button wait, while a period change in the same page does', async ({page}) => {
        const reports = recordMainReports(page);
        // After the sign-in, before the page loads: the document under test hears no catch-up but the stub's.
        const catchUp = await simulateCatchUp(page);
        const holds: Hold[] = [];
        try {
            const refresh = await openDashboard(page);
            const dashboard = page.getByTestId('dashboard-page');
            // The tracker saw the job run (the notice is put up by the call that notes it) and asks the status route: an
            // idle answer that updated something now sends `{kind: 'prices'}`.
            await expect(page.locator(CATCH_UP_NOTICE), 'precondition: the running catch-up shows its notice (Z5)').toBeVisible({timeout: ROUND_TRIP_MS});
            await expect.poll(() => catchUp.served.includes('running'), {message: 'precondition: the tracker never asked the status route', timeout: ROUND_TRIP_MS}).toBe(true);
            expect(reports.length, 'precondition: the Dashboard asked its main report').toBeGreaterThan(0);
            const onScreen = reports[reports.length - 1];
            const busySeen = await recordBusy(page, 'sync-button');
            // The root says nothing of the reload in background either (Z-18): the reports are counted in the page, and the
            // count says when it is back.
            const count = await countReports(page);
            const held = (): number => holds.reduce((sum, gate) => sum + gate.pending(), 0);

            // 1. The catch-up ends having updated something. Held: a main report sent once the stub has said so — nothing
            //    else on the settled page asks one.
            const reload = await hold(page, REPORT_PATH, (request) => isMainReport(request) && catchUp.served.includes('idle'));
            holds.push(reload);
            catchUp.header = null;
            catchUp.status = catchUpOverWithUpdates();
            const sent = await heldRequest(reload, 'the reload in background after the catch-up');
            expect(sent.postDataJSON(), 'the held report is not the question on screen asked again').toEqual(onScreen.postDataJSON());
            const inFlight = await count();
            expect(inFlight.sent - inFlight.landed, 'the page does not count the held reload in flight (is a report still sent by XHR?): its landing could not be read').toBeGreaterThan(0);
            await expect(refresh, 'the Refresh button waits for the reload in background after a price catch-up (P3)').toHaveAttribute('data-busy', 'false');
            await expect(refresh, 'the Refresh button cannot be pressed during the reload in background after a price catch-up (P3)').toBeEnabled();
            expect(await busySeen(), 'the Refresh button waited at some moment since the catch-up ended (P3)').not.toContain('true');
            // The reload is held in flight: a page that says busy for it says so now, and keeps saying it until the release.
            await expect(dashboard, 'the page says it is busy for the reload in background after a price catch-up, a load nobody asked for: a screen reader announces «busy» for a price refresh (Z-18)').toHaveAttribute('data-busy', 'false');

            await reload.release();
            await landedAllBut(count, held, 'the reload in background');
            expect(await busySeen(), 'the Refresh button waited at some moment of the reload, from its send to its landing (P3)').not.toContain('true');

            // 2. The control, in the same page and under the same recording: a request the page waits for moves the
            //    button, and the recording sees it move.
            const asked = new Set(reports.map(periodOf));
            const sixMonths = page.getByTestId('date-preset-6m');
            await expect(sixMonths, 'precondition: 6M is a change of period (the Dashboard opens on 3M)').toHaveAttribute('data-active', 'false');
            const period = await hold(page, REPORT_PATH, (request) => isMainReport(request) && !asked.has(periodOf(request)));
            holds.push(period);
            await sixMonths.click();
            await heldRequest(period, 'the report of the new period');
            await expectBusy(refresh, 'the control: the report of the new period is pending, and the Refresh button does not wait for it');
            expect(await busySeen(), 'the control: the recording missed the button waiting, so its silence above proves nothing').toContain('true');
            await period.release();
            await expectIdle(refresh, 'the control: the report of the new period is back, and the Refresh button still waits');
        } finally {
            for (const gate of holds) await gate.dispose();
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    test('Broker detail: the reload in background after a price catch-up never makes the Refresh button wait, while a period change in the same page does', async ({page}) => {
        const brokerId = await brokerIdByName(page, BROKER_WITH_HOLDINGS);
        const isOverview = isBrokerOverview(brokerId);
        const overviews = recordMainReports(page, isOverview);
        // After the sign-in, before the page loads: the document under test hears no catch-up but the stub's.
        const catchUp = await simulateCatchUp(page);
        const holds: Hold[] = [];
        try {
            const refresh = await openBrokerDetail(page, brokerId);
            // The tracker saw the job run (the notice is put up by the call that notes it) and asks the status route: an
            // idle answer that updated something now sends `{kind: 'prices'}`.
            await expect(page.locator(CATCH_UP_NOTICE), 'precondition: the running catch-up shows its notice (Z5)').toBeVisible({timeout: ROUND_TRIP_MS});
            await expect.poll(() => catchUp.served.includes('running'), {message: 'precondition: the tracker never asked the status route', timeout: ROUND_TRIP_MS}).toBe(true);
            expect(overviews.length, "precondition: the broker's page asked its overview").toBeGreaterThan(0);
            const onScreen = overviews[overviews.length - 1];
            const busySeen = await recordBusy(page, 'broker-refresh');
            // The page's root says nothing of the reload: the reports are counted in the page, and the count says when it is back.
            const reports = await countReports(page);

            // 1. The catch-up ends having updated something. Held: this broker's overview sent once the stub has said so —
            //    nothing else on the settled overview tab asks one.
            const reload = await hold(page, REPORT_PATH, (request) => isOverview(request) && catchUp.served.includes('idle'));
            holds.push(reload);
            catchUp.header = null;
            catchUp.status = catchUpOverWithUpdates();
            const sent = await heldRequest(reload, 'the reload in background after the catch-up');
            expect(sent.postDataJSON(), 'the held report is not the overview on screen asked again').toEqual(onScreen.postDataJSON());
            const inFlight = await reports();
            expect(inFlight.sent - inFlight.landed, 'the page does not count the held reload in flight (is a report still sent by XHR?): its landing could not be read').toBeGreaterThan(0);
            await expect(refresh, 'the Refresh button waits for the reload in background after a price catch-up (P3)').toHaveAttribute('data-busy', 'false');
            await expect(refresh, 'the Refresh button cannot be pressed during the reload in background after a price catch-up (P3)').toBeEnabled();
            expect(await busySeen(), 'the Refresh button waited at some moment since the catch-up ended (P3)').not.toContain('true');

            await reload.release();
            await expect
                .poll(
                    async () => {
                        const count = await reports();
                        return count.sent - count.landed;
                    },
                    {message: 'the reload in background never landed in the page', timeout: ROUND_TRIP_MS},
                )
                .toBe(0);
            expect(await busySeen(), 'the Refresh button waited at some moment of the reload, from its send to its landing (P3)').not.toContain('true');

            // 2. The control, in the same page and under the same recording: a request the page waits for moves the
            //    button, and the recording sees it move.
            const asked = new Set(overviews.map(periodOf));
            const sixMonths = page.getByTestId('date-preset-6m');
            await expect(sixMonths, "precondition: 6M is a change of period (the broker's page opens on 3M)").toHaveAttribute('data-active', 'false');
            const period = await hold(page, REPORT_PATH, (request) => isOverview(request) && !asked.has(periodOf(request)));
            holds.push(period);
            await sixMonths.click();
            await expect(sixMonths).toHaveAttribute('data-active', 'true');
            await heldRequest(period, 'the overview of the new period');
            await expectBusy(refresh, 'the control: the overview of the new period is pending, and the Refresh button does not wait for it');
            expect(await busySeen(), 'the control: the recording missed the button waiting, so its silence above proves nothing').toContain('true');
            await period.release();
            await expectIdle(refresh, 'the control: the overview of the new period is back, and the Refresh button still waits');
        } finally {
            for (const gate of holds) await gate.dispose();
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    test('Dashboard on a saved P&L candles view: the candles the reload in background cascades into never make the Refresh button wait, while those a period change cascades into do (N55)', async ({page}) => {
        test.setTimeout(CASCADE_TEST_MS);
        await saveCandlesView(page);
        const reports = recordMainReports(page);
        const candles = recordMainReports(page, isPnlCandles);
        // After the sign-in and the visit that saved the view, before the page under test loads: the document under
        // test hears no catch-up but the stub's.
        const catchUp = await simulateCatchUp(page);
        const holds: Hold[] = [];
        const held = (): number => holds.reduce((sum, gate) => sum + gate.pending(), 0);
        try {
            const refresh = await openDashboard(page);
            const dashboard = page.getByTestId('dashboard-page');
            const chart = page.getByTestId('growth-chart');
            await expect(chart.getByTestId('growth-toggle-pnl'), 'precondition: the Dashboard opened on the saved P&L mode').toHaveAttribute('aria-pressed', 'true');
            await expect(chart.getByTestId('growth-pnl-submode-candles'), 'precondition: the Dashboard opened on the saved candles submode').toHaveAttribute('aria-pressed', 'true');
            await expect.poll(() => candleBodies(chart), {message: 'precondition: the saved candles view never drew its candles', timeout: ROUND_TRIP_MS}).toBeGreaterThan(0);
            expect(candles.length, 'precondition: the saved candles view asked its candles at load').toBeGreaterThan(0);
            await expect(page.locator(CATCH_UP_NOTICE), 'precondition: the running catch-up shows its notice (Z5)').toBeVisible({timeout: ROUND_TRIP_MS});
            await expect.poll(() => catchUp.served.includes('running'), {message: 'precondition: the tracker never asked the status route', timeout: ROUND_TRIP_MS}).toBe(true);
            expect(reports.length, 'precondition: the Dashboard asked its main report').toBeGreaterThan(0);
            const onScreen = reports[reports.length - 1];
            const candlesOnScreen = candles[candles.length - 1];
            const busySeen = await recordBusy(page, 'sync-button');
            const count = await countReports(page);

            // 1. The catch-up ends having updated something. Held: the main report the reload sends, and the candles its
            //    landing cascades into — the report drops them, and the chart, still on candles, asks again. Both sent
            //    once the stub has said so; nothing else on the settled page asks either.
            const reload = await hold(page, REPORT_PATH, (request) => isMainReport(request) && catchUp.served.includes('idle'));
            holds.push(reload);
            const cascade = await hold(page, REPORT_PATH, (request) => isPnlCandles(request) && catchUp.served.includes('idle'));
            holds.push(cascade);
            catchUp.header = null;
            catchUp.status = catchUpOverWithUpdates();
            const sent = await heldRequest(reload, 'the reload in background after the catch-up');
            expect(sent.postDataJSON(), 'the held report is not the question on screen asked again').toEqual(onScreen.postDataJSON());
            await expectNeverWaited(refresh, busySeen, 'the reload in background after a price catch-up (P3)');
            // The reload is held in flight: a page that says busy for it says so now, and keeps saying it until the release.
            await expect(dashboard, 'the page says it is busy for the reload in background after a price catch-up, a load nobody asked for: a screen reader announces «busy» for a price refresh (Z-18)').toHaveAttribute('data-busy', 'false');

            await reload.release();
            const cascaded = await heldRequest(cascade, 'the candles the landed reload cascades into (the chart, still on candles, did not ask them again)');
            expect(cascaded.postDataJSON(), 'the held candles are not the candles on screen asked again').toEqual(candlesOnScreen.postDataJSON());
            await landedAllBut(count, held, 'the reload in background');
            // A settle, not the landing (the count above is): the root keeps quiet through a reload in background (Z-18).
            await waitForSettled(dashboard, ROUND_TRIP_MS);
            await expectNeverWaited(refresh, busySeen, 'the candles the reload in background cascades into (N55: alone, with no token)');

            await cascade.release();
            await landedAllBut(count, held, 'the candles the reload in background cascades into');
            await expect.poll(() => candleBodies(chart), {message: 'the candles the reload cascades into never reached the chart', timeout: ROUND_TRIP_MS}).toBeGreaterThan(0);
            await expectNeverWaited(refresh, busySeen, 'the reload in background and the candles it cascades into, from the send of one to the landing of the other (P3, N55)');

            // 2. The control, in the same page and under the same recording: a period change waits for its report, and
            //    then for the candles that report cascades into — they join the period's token (N55).
            const asked = new Set(reports.map(periodOf));
            const askedCandles = new Set(candles.map(periodOf));
            const sixMonths = page.getByTestId('date-preset-6m');
            await expect(sixMonths, 'precondition: 6M is a change of period (the Dashboard opens on 3M)').toHaveAttribute('data-active', 'false');
            const period = await hold(page, REPORT_PATH, (request) => isMainReport(request) && !asked.has(periodOf(request)));
            holds.push(period);
            const periodCandles = await hold(page, REPORT_PATH, (request) => isPnlCandles(request) && !askedCandles.has(periodOf(request)));
            holds.push(periodCandles);
            await sixMonths.click();
            await expect(sixMonths).toHaveAttribute('data-active', 'true');
            await heldRequest(period, 'the report of the new period');
            await expectBusy(refresh, 'the control: the report of the new period is pending, and the Refresh button does not wait for it');
            expect(await busySeen(), 'the control: the recording missed the button waiting, so its silence above proves nothing').toContain('true');

            await period.release();
            await heldRequest(periodCandles, 'the candles the report of the new period cascades into (the chart, still on candles, did not ask them)');
            await landedAllBut(count, held, 'the report of the new period');
            await expectBusy(refresh, 'the control (N55): the report of the new period is back, and the Refresh button does not wait for the candles it cascades into — they did not join its token');

            await periodCandles.release();
            await expectIdle(refresh, 'the control: the candles of the new period are back, and the Refresh button still waits');
            await landedAllBut(count, held, 'the candles of the new period');
        } finally {
            for (const gate of holds) await gate.dispose();
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    /**
     * Y-16, the explicit pin of what the N55 case above takes only as a precondition («the saved candles view asked its
     * candles at load»). On a saved candles view the chart asks for its candles as it mounts (GrowthChart's request
     * `$effect`), before the Dashboard knows the owned brokers, and `loadPnlCandles` refuses while `canAsk` is false (F2).
     * The ask is re-armed by the brokers themselves: `loadPnlCandles` reads `canAsk` synchronously inside that effect, so
     * the effect depends on it and runs again when the brokers land. Read untracked, nothing would ask again: no candles
     * request, and a chart of empty candles. The list of brokers is held from before the page loads, so that the refused
     * ask is certainly the chart's first, and the one that goes out the re-armed one.
     */
    test('Dashboard loaded from scratch on a saved P&L candles view: the candles are asked, and drawn, once the brokers are known, though the chart first asks for them before (Y-16)', async ({page}) => {
        test.setTimeout(CASCADE_TEST_MS);
        await saveCandlesView(page);
        // The visit that saved the view is closed first: every report recorded below belongs to the document under test,
        // never a late one of that visit (its own candles, or those a reload in background there cascades into).
        await page.goto('about:blank');
        const candles = recordMainReports(page, asksPnlCandles);
        // Held from before the page loads: the list of brokers the Dashboard asks as it mounts (`ensureBrokersLoaded`), and
        // with it `brokersReady` — F2: nothing is asked before the owned brokers are known.
        const brokers = await hold(page, BROKERS_PATH, isBrokerList);
        try {
            await navigateTo(page, '/dashboard?tab=panoramica');
            const chart = page.getByTestId('growth-chart');
            const brokerList = await heldRequest(brokers, 'the list of brokers the Dashboard asks as it mounts');
            await expectBusy(page.getByTestId('sync-button'), 'precondition: the first load of the Dashboard does not wait for the held list of brokers');
            // The chart asks for its candles in the flush that mounts it: once its toggles show the saved view, that ask has
            // been made — and, the brokers unknown, refused. «No candles asked» below is the refusal, not a chart that has
            // not asked yet.
            await expect(chart.getByTestId('growth-toggle-pnl'), 'precondition: the Dashboard opened on the saved P&L mode').toHaveAttribute('aria-pressed', 'true');
            await expect(chart.getByTestId('growth-pnl-submode-candles'), 'precondition: the Dashboard opened on the saved candles submode').toHaveAttribute('aria-pressed', 'true');
            // Read with the list of brokers still held, and still alive in the page: the brokers are not known yet.
            expect(brokers.pending(), 'the list of brokers was let through before the reading').toBeGreaterThan(0);
            expect(brokerList.failure(), 'the list of brokers failed before the reading').toBeNull();
            expect(
                candles.map((request) => request.postDataJSON() as ReportBody | null),
                'F2: the Dashboard asked its candles before it knew the owned brokers',
            ).toEqual([]);

            await brokers.release();
            await expect.poll(() => candles.length, {message: 'Y-16: the brokers are known, and the candles the chart asked before them are never asked — the refused ask was not re-armed when the brokers landed', timeout: ROUND_TRIP_MS}).toBeGreaterThan(0);
            const asked = candles[0].postDataJSON() as ReportBody | null;
            expect(asked?.broker_ids?.length ?? 0, 'F2: the candles were asked without the owned brokers, a scope the backend widens to every broker the user can see').toBeGreaterThan(0);
            await waitForSettled(page.getByTestId('dashboard-page'), ROUND_TRIP_MS);
            await expect.poll(() => candleBodies(chart), {message: 'the candles asked once the brokers were known never reached the chart', timeout: ROUND_TRIP_MS}).toBeGreaterThan(0);
        } finally {
            await brokers.dispose();
        }
    });

    test('Broker detail on a saved Performance view: the contribution the reload in background cascades into never makes the Refresh button wait, while the one a period change cascades into does (N55)', async ({page}) => {
        test.setTimeout(CASCADE_TEST_MS);
        const brokerId = await brokerIdByName(page, BROKER_WITH_HOLDINGS);
        const isOverview = isBrokerOverview(brokerId);
        const isContribution = isBrokerContribution(brokerId);
        await savePerformanceView(page, brokerId);
        const overviews = recordMainReports(page, isOverview);
        const contributions = recordMainReports(page, isContribution);
        // After the sign-in and the visit that saved the view, before the page under test loads: the document under
        // test hears no catch-up but the stub's.
        const catchUp = await simulateCatchUp(page);
        const holds: Hold[] = [];
        const held = (): number => holds.reduce((sum, gate) => sum + gate.pending(), 0);
        try {
            const refresh = await openBrokerDetail(page, brokerId, 'posizioni');
            const panel = page.getByTestId('positions-panel');
            const contributionTable = panel.getByTestId('contribution-table');
            await expect(contributionTable, 'precondition: the positions tab opened on the saved Performance view, its contribution in').toBeVisible({timeout: ROUND_TRIP_MS});
            await expect(panel, 'precondition: the Performance view settled').toHaveAttribute('data-busy', 'false');
            expect(contributions.length, 'precondition: the saved Performance view asked its contribution at load').toBeGreaterThan(0);
            await expect(page.locator(CATCH_UP_NOTICE), 'precondition: the running catch-up shows its notice (Z5)').toBeVisible({timeout: ROUND_TRIP_MS});
            await expect.poll(() => catchUp.served.includes('running'), {message: 'precondition: the tracker never asked the status route', timeout: ROUND_TRIP_MS}).toBe(true);
            expect(overviews.length, "precondition: the broker's page asked its overview").toBeGreaterThan(0);
            const onScreen = overviews[overviews.length - 1];
            const contributionOnScreen = contributions[contributions.length - 1];
            const busySeen = await recordBusy(page, 'broker-refresh');
            // The page's root says nothing of the reload: the reports are counted in the page, and the count says when it is back.
            const reports = await countReports(page);

            // 1. The catch-up ends having updated something. Held: this broker's overview the reload sends, and the
            //    contribution it cascades into — the reload shows the cached overview first, which carries none, and
            //    the panel, still on Performance, asks again at once. Both sent once the stub has said so; nothing else
            //    on the settled positions tab asks either.
            const reload = await hold(page, REPORT_PATH, (request) => isOverview(request) && catchUp.served.includes('idle'));
            holds.push(reload);
            const cascade = await hold(page, REPORT_PATH, (request) => isContribution(request) && catchUp.served.includes('idle'));
            holds.push(cascade);
            catchUp.header = null;
            catchUp.status = catchUpOverWithUpdates();
            const sent = await heldRequest(reload, 'the reload in background after the catch-up');
            expect(sent.postDataJSON(), 'the held report is not the overview on screen asked again').toEqual(onScreen.postDataJSON());
            const cascaded = await heldRequest(cascade, 'the contribution the reload cascades into (the panel, still on Performance, did not ask it again)');
            expect(cascaded.postDataJSON(), 'the held contribution is not the contribution on screen asked again').toEqual(contributionOnScreen.postDataJSON());
            const inFlight = await reports();
            expect(inFlight.sent - inFlight.landed, 'the page does not count the held reports in flight (is a report still sent by XHR?): their landing could not be read').toBeGreaterThanOrEqual(held());
            await expect(panel, 'the panel does not show its own loading for the contribution it asked again (N55)').toHaveAttribute('data-busy', 'true');
            await expectNeverWaited(refresh, busySeen, 'the reload in background after a price catch-up and the contribution it cascades into (P3, N55: alone, with no token)');

            await reload.release();
            await landedAllBut(reports, held, 'the reload in background');
            await expectNeverWaited(refresh, busySeen, 'the contribution the reload in background cascades into, once the reload is back (N55)');

            await cascade.release();
            await landedAllBut(reports, held, 'the contribution the reload in background cascades into');
            await expect(contributionTable, 'the contribution the reload cascades into never reached the Performance view').toBeVisible({timeout: ROUND_TRIP_MS});
            await expect(panel).toHaveAttribute('data-busy', 'false');
            await expectNeverWaited(refresh, busySeen, 'the reload in background and the contribution it cascades into, from their send to their landing (P3, N55)');

            // 2. The control, in the same page and under the same recording: a period change waits for its overview, and
            //    then for the contribution that overview cascades into — it joins the period's token (N55).
            const asked = new Set(overviews.map(periodOf));
            const askedContributions = new Set(contributions.map(periodOf));
            const sixMonths = page.getByTestId('date-preset-6m');
            await expect(sixMonths, "precondition: 6M is a change of period (the broker's page opens on 3M)").toHaveAttribute('data-active', 'false');
            const period = await hold(page, REPORT_PATH, (request) => isOverview(request) && !asked.has(periodOf(request)));
            holds.push(period);
            const periodContribution = await hold(page, REPORT_PATH, (request) => isContribution(request) && !askedContributions.has(periodOf(request)));
            holds.push(periodContribution);
            await sixMonths.click();
            await expect(sixMonths).toHaveAttribute('data-active', 'true');
            await heldRequest(period, 'the overview of the new period');
            await expectBusy(refresh, 'the control: the overview of the new period is pending, and the Refresh button does not wait for it');
            expect(await busySeen(), 'the control: the recording missed the button waiting, so its silence above proves nothing').toContain('true');

            await period.release();
            await heldRequest(periodContribution, 'the contribution the overview of the new period cascades into (the panel, still on Performance, did not ask it)');
            await landedAllBut(reports, held, 'the overview of the new period');
            await expectBusy(refresh, "the control (N55): the overview of the new period is back, and the Refresh button does not wait for the contribution it cascades into — it did not join the period's token");

            await periodContribution.release();
            await expectIdle(refresh, 'the control: the contribution of the new period is back, and the Refresh button still waits');
            await landedAllBut(reports, held, 'the contribution of the new period');
            await expect(contributionTable, 'the contribution of the new period never reached the Performance view').toBeVisible({timeout: ROUND_TRIP_MS});
        } finally {
            for (const gate of holds) await gate.dispose();
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    test('Broker detail: Refresh holds its button until the overview it asked again is back', async ({page}) => {
        const brokerId = await brokerIdByName(page, BROKER_WITH_HOLDINGS);
        const refresh = await openBrokerDetail(page, brokerId);
        // The overview only: the broker's summary, asked again beside it, goes through.
        const gate = await hold(page, REPORT_PATH, isBrokerOverview(brokerId));
        try {
            await refresh.click();
            await heldRequest(gate, 'the overview Refresh asks again');
            await expectBusy(refresh, 'Refresh asked the overview again, and its button does not wait for it');

            await gate.release();
            await expectIdle(refresh, 'the overview is back, and the Refresh button still waits');
        } finally {
            await gate.dispose();
        }
    });

    test('Brokers list: Refresh holds its button until the list of brokers is back', async ({page}) => {
        const refresh = await openBrokers(page);
        const gate = await hold(page, BROKERS_PATH, isBrokerList);
        try {
            await refresh.click();
            await heldRequest(gate, 'the list of brokers Refresh asks again');
            await expectBusy(refresh, 'Refresh asked the list of brokers again, and its button does not wait for it');

            await gate.release();
            await expectIdle(refresh, 'the list of brokers is back, and the Refresh button still waits');
        } finally {
            await gate.dispose();
        }
    });

    test('Transactions: Refresh holds its button until the list of transactions is back', async ({page}) => {
        const refresh = await openTransactions(page);
        const gate = await hold(page, TRANSACTIONS_PATH, isTransactionList);
        try {
            // The click clears the column and URL filters too: a page opened with none has none to clear.
            await refresh.click();
            await heldRequest(gate, 'the list of transactions Refresh asks again');
            await expectBusy(refresh, 'Refresh asked the list of transactions again, and its button does not wait for it');

            await gate.release();
            await expectIdle(refresh, 'the list of transactions is back, and the Refresh button still waits');
        } finally {
            await gate.dispose();
        }
    });
});

// ── The asset pages: an asset's detail page, and the Assets list on its Correlation tab ──────────────────────────────

const ASSETS_QUERY_PATH = `${API}/assets/query`;
const PRICE_QUERY_PATH = `${API}/assets/prices/query`;
const LIVE_PRICES_PATH = `${API}/assets/prices/current`;
const ASSET_SYNC_PATH = `${API}/assets/prices/sync`;
const FX_SYNC_PATH = `${API}/fx/currencies/sync`;
const FX_PROVIDERS_PATH = `${API}/fx/providers`;
const ASSIGNMENTS_PATH = `${API}/assets/provider/assignments`;
const RISK_QUERY_PATH = `${API}/risk/query`;
/**
 * The mock's asset with a price history and a provider, the one the asset specs open (asset-detail.spec.ts,
 * `goToSeededAssetDetail`): found by name through `page.request`, never by position.
 */
const ASSET_WITH_PRICES = 'Apple Inc.';

/** An asset as the list answers it: its id, and the provider that prices it — its page offers a Sync only with one. */
interface ListedAsset {
    id: number;
    provider: string | null;
}

/** An asset TEST_USER sees, by name, read with `page.request`: no route of the page intercepts it. */
async function assetByName(page: Page, name: string): Promise<ListedAsset> {
    const response = await page.request.get(ASSETS_QUERY_PATH);
    expect(response.ok(), `GET ${ASSETS_QUERY_PATH} → HTTP ${response.status()}`).toBe(true);
    const items = (await response.json()) as Array<{id: number; display_name: string; provider_code?: string | null}>;
    const asset = items.find((item) => item.display_name === name);
    if (!asset) throw new Error(`${name} is the mock's asset with a price history: check populate_mock_data.py (populate_assets)`);
    return {id: asset.id, provider: asset.provider_code ?? null};
}

/**
 * Every live-price poll the page sends, refused at the network from now until the context closes. A poll is a write —
 * `POST /assets/prices/current` asks the provider and stores today's candle — and an answer, even an empty one, goes
 * through the client's interceptor as a portfolio mutation that marks the caches stale. A refused poll writes nothing,
 * calls no provider and marks nothing: the poller notes the failure and waits longer before the next try. No button
 * waits for it either way (P3: the live poller holds no token). Never unrouted: the next poll would reach the backend.
 */
async function refuseLivePrices(page: Page): Promise<void> {
    await page.route(
        (url) => url.pathname === LIVE_PRICES_PATH,
        (route) => route.abort().catch(() => undefined),
    );
}

/**
 * The exchange-rate provider catalogue (`GET /fx/providers`), answered in the browser with an empty list. The page's
 * sync dialog asks it when it opens, for provider icons (`getCurrencyGraph()`), and the backend builds it by asking the
 * providers, some of them over the network (risk-lab.spec.ts, `answerFxProviderCatalog`). An empty list is valid for
 * the client's schema, and the dialog here has no exchange-rate pair to draw an icon for. The bare path only:
 * `/fx/providers/routes` is a read of the database the page needs.
 */
async function answerFxProviderCatalog(page: Page): Promise<void> {
    await page.route(
        (url) => url.pathname === FX_PROVIDERS_PATH,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            await route.fulfill({status: 200, contentType: 'application/json', body: '[]'}).catch(() => undefined);
        },
    );
}

/** What the page's own Sync sent, as the stub answered it. */
interface SyncStub {
    /** The asset ids of every `POST /assets/prices/sync`, one list per request, counted before its answer leaves. */
    assets: number[][];
    /** Every exchange-rate sync the page tried, refused: the page under test has no pair to sync. */
    fx: Request[];
}

/**
 * The page's own Sync, answered in the browser: every asset it asks for is `ok`, nothing fetched and nothing changed —
 * a run that was accepted (`PageSyncModal` reports `{accepted: true}`) and wrote nothing. No provider is called and the
 * shared database is not touched: the request never leaves the browser. An exchange-rate sync is refused at the network,
 * and recorded.
 */
async function stubPageSync(page: Page): Promise<SyncStub> {
    const stub: SyncStub = {assets: [], fx: []};
    await page.route(
        (url) => url.pathname === ASSET_SYNC_PATH,
        async (route) => {
            const body: unknown = route.request().postDataJSON();
            const items = Array.isArray(body) ? (body as Array<{asset_id?: unknown}>) : [];
            const ids = items.flatMap((item) => (typeof item?.asset_id === 'number' ? [item.asset_id] : []));
            // Counted before the answer leaves: whatever the page sends because of it finds it counted already.
            stub.assets.push(ids);
            const results = ids.map((id) => ({asset_id: id, status: 'ok', provider_used: null, points_fetched: 0, points_changed: 0, errors: []}));
            await route.fulfill({json: {results, success_count: results.length, errors: []}}).catch(() => undefined);
        },
    );
    await page.route(
        (url) => url.pathname === FX_SYNC_PATH,
        async (route) => {
            stub.fx.push(route.request());
            await route.abort().catch(() => undefined);
        },
    );
    return stub;
}

type PriceQueryItem = {asset_id?: number; date_range?: {start?: string; end?: string}};

/** What a price query (`POST /assets/prices/query`) asks about asset `assetId`, if it asks about it at all. */
function priceItemOf(request: Request, assetId: number): PriceQueryItem | undefined {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== PRICE_QUERY_PATH) return undefined;
    const body = request.postDataJSON() as PriceQueryItem[] | null;
    return Array.isArray(body) ? body.find((item) => item?.asset_id === assetId) : undefined;
}

/** The chart of asset `assetId`'s page (`loadChartData`): a price query about that asset, with its prices or without. */
function isChartOf(assetId: number): (request: Request) => boolean {
    return (request) => priceItemOf(request, assetId) !== undefined;
}

/** The period a chart query asks for asset `assetId`, as one comparable string. */
function chartPeriodOf(request: Request, assetId: number): string {
    const range = priceItemOf(request, assetId)?.date_range;
    return `${range?.start ?? ''}..${range?.end ?? ''}`;
}

/** Every request `picks` chooses that the page sends from now on, in order, the held ones included. */
function recordRequests(page: Page, picks: (request: Request) => boolean): Request[] {
    const sent: Request[] = [];
    page.on('request', (request) => {
        if (picks(request)) sent.push(request);
    });
    return sent;
}

type RiskQueryBody = {
    scope?: {kind?: string; asset_ids?: number[]};
    date_range?: {start?: string; end?: string | null};
    target_currency?: string;
    mode?: string;
    analytics?: Array<{analytic_code?: string}>;
};

/**
 * The correlation section's base wave on the Correlation tab (`POST /risk/query`): an asset-set question, historical,
 * that asks the correlation alone. The replay section asks the very same wave, which `queryRisk` serves from one flight;
 * the two levels ask their own codes beside it (risk-lab.spec.ts, `correlationRequestsFor`).
 */
function isCorrelationWave(request: Request): boolean {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== RISK_QUERY_PATH) return false;
    const body = request.postDataJSON() as RiskQueryBody | null;
    const codes = new Set((body?.analytics ?? []).map((analytic) => analytic.analytic_code));
    return body?.scope?.kind === 'asset_set' && body.mode === 'historical' && codes.size === 1 && codes.has('correlation');
}

/** What a risk wave asks about — its selection, its period, its currency — as one comparable value. */
function riskQuestionOf(request: Request): unknown {
    const body = request.postDataJSON() as RiskQueryBody | null;
    return {scope: body?.scope, date_range: body?.date_range, target_currency: body?.target_currency};
}

/**
 * The button says whether it waits: a `data-busy` is there, `true` or `false`. One that publishes none follows no busy
 * state at all, and every reading of it would time out on a value that is not there.
 */
async function expectPublishesBusy(button: Locator, what: string): Promise<void> {
    await expect(button, `${what} publishes no data-busy: it does not follow the big requests of its page (Y11)`).toHaveAttribute('data-busy', /^(?:true|false)$/);
}

/**
 * An asset's detail page, loaded from scratch and settled: its chart in (the root's `data-busy`), and nothing of the
 * page pending (the button's) — the first load holds the button until the asset, its chart, its classification and any
 * comparison are all in. On the price chart of the Overview tab, where no risk panel adds loads of its own to the button.
 */
async function openAssetDetail(page: Page, assetId: number): Promise<Locator> {
    await navigateTo(page, `/assets/${assetId}`);
    await waitForSettled(page.getByTestId('asset-detail-page'), ROUND_TRIP_MS);
    await expect(page.getByTestId('asset-detail-tab-overview'), `the page of asset ${assetId} did not open on its Overview tab`).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('asset-detail-chart'), `the page of asset ${assetId} did not open on its price chart`).toHaveAttribute('data-primary-mode', 'price');
    const refresh = page.getByTestId('asset-detail-refresh-btn');
    await expectPublishesBusy(refresh, "The asset's Refresh button");
    await expectIdle(refresh, "the asset's page settled with its Refresh button still waiting");
    return refresh;
}

/**
 * The Assets list on its Correlation tab, loaded from scratch and settled: the laboratory's opening selection analysed
 * — on a first visit, what TEST_USER holds — the correlation section's first base wave in (its own `data-busy`), the
 * list's two waves in (the root's), and nothing of the page pending (the button's). «Reload All» is the page's Refresh
 * on this tab: it takes the place of the list's in the toolbar.
 */
async function openCorrelationLab(page: Page): Promise<Locator> {
    await navigateTo(page, '/assets?tab=correlation');
    const correlation = page.getByTestId('asset-global-risk-panel').getByTestId('risk-correlation-content');
    await expect(correlation, `the laboratory analyses nothing: on a first visit it opens on what ${TEST_USER.username} holds — check populate_mock_data.py`).toBeVisible({timeout: ROUND_TRIP_MS});
    await expect(correlation, "the correlation section's capability catalogue never came").toHaveAttribute('data-catalog', 'ready', {timeout: ROUND_TRIP_MS});
    await waitForSettled(correlation, ROUND_TRIP_MS);
    await waitForSettled(page.getByTestId('assets-page'), ROUND_TRIP_MS);
    const reload = page.getByTestId('assets-controls').getByTestId('risk-reload-button');
    await expectPublishesBusy(reload, "The Correlation tab's «Reload All» button");
    await expectIdle(reload, 'the laboratory settled with its «Reload All» button still waiting');
    return reload;
}

test.describe("Page busy on the asset pages: the Refresh button waits for its own page's big requests, never for a sync's reload (Y11)", () => {
    test.describe.configure({timeout: TEST_MS});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test("Asset detail: Refresh holds its button until the chart's prices it asked again are back", async ({page}) => {
        const asset = await assetByName(page, ASSET_WITH_PRICES);
        // After the sign-in, before the page loads: no poll of the document under test reaches the backend.
        await refuseLivePrices(page);
        const isChart = isChartOf(asset.id);
        const charts = recordRequests(page, isChart);
        const refresh = await openAssetDetail(page, asset.id);
        expect(charts.length, "precondition: the asset's page asked its chart").toBeGreaterThan(0);
        const onScreen = charts[charts.length - 1];

        // Any chart query: nothing else on the settled page asks one.
        const gate = await hold(page, PRICE_QUERY_PATH, isChart);
        try {
            await refresh.click();
            const sent = await heldRequest(gate, "the chart's prices Refresh asks again");
            expect(chartPeriodOf(sent, asset.id), 'Refresh asked the chart for another period than the one on screen').toBe(chartPeriodOf(onScreen, asset.id));
            await expectBusy(refresh, "Refresh asked the chart's prices again, and its button does not wait for them");

            await gate.release();
            await expectIdle(refresh, "the chart's prices are back, and the Refresh button still waits");
        } finally {
            await gate.dispose();
        }
    });

    test('Asset detail: a period change holds the Refresh button until the chart of the new period is back, with no click on it', async ({page}) => {
        const asset = await assetByName(page, ASSET_WITH_PRICES);
        await refuseLivePrices(page);
        const isChart = isChartOf(asset.id);
        const charts = recordRequests(page, isChart);
        const refresh = await openAssetDetail(page, asset.id);
        const asked = new Set(charts.map((request) => chartPeriodOf(request, asset.id)));
        expect(asked.size, "precondition: the asset's page asked its chart for the period it opened on").toBeGreaterThan(0);
        const sixMonths = page.getByTestId('asset-detail-filter-bar').getByTestId('date-preset-6m');
        await expect(sixMonths, "precondition: 6M is a change of period (the asset's page opens on 3M)").toHaveAttribute('data-active', 'false');

        // Only a chart query for a period the page had not asked yet: the one the click sends, with the prices or, on a
        // cache hit, the events alone.
        const gate = await hold(page, PRICE_QUERY_PATH, (request) => isChart(request) && !asked.has(chartPeriodOf(request, asset.id)));
        try {
            await sixMonths.click();
            await expect(sixMonths).toHaveAttribute('data-active', 'true');
            await heldRequest(gate, 'the chart of the new period');
            await expectBusy(refresh, 'the chart of the new period is pending, and the Refresh button does not wait for it');

            await gate.release();
            await expectIdle(refresh, 'the chart of the new period is back, and the Refresh button still waits');
        } finally {
            await gate.dispose();
        }
    });

    test("Asset detail: the reload after the page's own Sync never makes the Refresh button wait, while a period change in the same page does", async ({page}) => {
        const asset = await assetByName(page, ASSET_WITH_PRICES);
        if (asset.provider === null) throw new Error(`${ASSET_WITH_PRICES} has no provider, so its page offers no Sync: check populate_mock_data.py (populate_asset_provider_assignments)`);
        // After the sign-in, before the page loads: nothing the document under test syncs or polls reaches the backend.
        await refuseLivePrices(page);
        await answerFxProviderCatalog(page);
        const sync = await stubPageSync(page);
        const isChart = isChartOf(asset.id);
        const charts = recordRequests(page, isChart);
        const holds: Hold[] = [];
        try {
            const refresh = await openAssetDetail(page, asset.id);
            // The Edit button waits for the asset's metadata (`classificationLoaded`), which the reload after a sync asks
            // again last: its state says where that reload is.
            const edit = page.getByTestId('asset-detail-edit-btn');
            await expect(edit, "precondition: the asset's metadata is in").toBeEnabled();
            expect(charts.length, "precondition: the asset's page asked its chart").toBeGreaterThan(0);
            const onScreen = charts[charts.length - 1];
            const busySeen = await recordBusy(page, 'asset-detail-refresh-btn');

            // 1. The page's own Sync, accepted. Held, once the stub has answered: the chart the reload asks again, then the
            //    provider assignment its metadata reload asks once that chart is back — nothing else on the settled page
            //    asks either.
            const synced = (): boolean => sync.assets.length > 0;
            const reload = await hold(page, PRICE_QUERY_PATH, (request) => isChart(request) && synced());
            holds.push(reload);
            const metadata = await hold(page, ASSIGNMENTS_PATH, (request) => isGet(request) && synced());
            holds.push(metadata);
            const syncButton = page.getByTestId('asset-detail-sync-btn');
            await expect(syncButton, `precondition: ${ASSET_WITH_PRICES} has a provider and can be synced from its page`).toBeEnabled();
            await syncButton.click();
            const dialog = page.getByTestId('page-sync-modal');
            await expect(dialog).toBeVisible();
            const scope = dialog.getByTestId('sync-modal-count');
            await expect(scope, 'precondition: the dialog syncs this asset alone').toHaveAttribute('data-item-count', '1');
            await expect(scope, 'precondition: the dialog has no exchange-rate section to run').toHaveAttribute('data-section-count', '1');
            await dialog.getByTestId('sync-modal-start').click();

            const sent = await heldRequest(reload, "the reload after the page's own Sync");
            expect(sync.assets, 'the dialog synced something else than this asset').toEqual([[asset.id]]);
            expect(sent.postDataJSON(), 'the held query is not the chart on screen asked again').toEqual(onScreen.postDataJSON());
            await expectNeverWaited(refresh, busySeen, "the reload after the page's own Sync (P3)");

            await reload.release();
            await heldRequest(metadata, "the asset's metadata the reload asks again once its chart is back");
            await expect(edit, 'precondition: the metadata is being asked again, and the Edit button does not wait for it').toBeDisabled();
            await expectNeverWaited(refresh, busySeen, "the metadata the reload after the page's own Sync asks again (P3)");

            await metadata.release();
            await expect(edit, "the asset's metadata, asked again after the Sync, never landed").toBeEnabled({timeout: ROUND_TRIP_MS});
            await waitForSettled(page.getByTestId('asset-detail-page'), ROUND_TRIP_MS);
            await expectNeverWaited(refresh, busySeen, "the reload after the page's own Sync, from the send of its chart to the landing of its metadata (P3)");
            expect(sync.fx, 'the page tried an exchange-rate sync').toEqual([]);
            // Closed before the control: its backdrop covers the toolbar.
            await dialog.getByTestId('sync-modal-close').click();
            await expect(dialog).toBeHidden();

            // 2. The control, in the same page and under the same recording: a request the page waits for moves the
            //    button, and the recording sees it move.
            const asked = new Set(charts.map((request) => chartPeriodOf(request, asset.id)));
            const sixMonths = page.getByTestId('asset-detail-filter-bar').getByTestId('date-preset-6m');
            await expect(sixMonths, "precondition: 6M is a change of period (the asset's page opens on 3M)").toHaveAttribute('data-active', 'false');
            const period = await hold(page, PRICE_QUERY_PATH, (request) => isChart(request) && !asked.has(chartPeriodOf(request, asset.id)));
            holds.push(period);
            await sixMonths.click();
            await expect(sixMonths).toHaveAttribute('data-active', 'true');
            await heldRequest(period, 'the chart of the new period');
            await expectBusy(refresh, 'the control: the chart of the new period is pending, and the Refresh button does not wait for it');
            expect(await busySeen(), 'the control: the recording missed the button waiting, so its silence above proves nothing').toContain('true');
            await period.release();
            await expectIdle(refresh, 'the control: the chart of the new period is back, and the Refresh button still waits');
        } finally {
            for (const gate of holds) await gate.dispose();
        }
    });

    test('Assets list, Correlation tab: «Reload All» holds its button until the sections it asked again are back', async ({page}) => {
        // After the sign-in, before the page loads: the list polls live prices while its period ends today.
        await refuseLivePrices(page);
        const waves = recordRequests(page, isCorrelationWave);
        const reload = await openCorrelationLab(page);
        expect(waves.length, 'precondition: the correlation section asked its base wave, of the shape held below').toBeGreaterThan(0);
        const onScreen = waves[waves.length - 1];

        // The correlation section's base wave, which the replay section shares: nothing else on the settled tab asks it.
        const gate = await hold(page, RISK_QUERY_PATH, isCorrelationWave);
        try {
            await reload.click();
            const sent = await heldRequest(gate, "the correlation section's base wave «Reload All» asks again");
            expect(riskQuestionOf(sent), 'the reload asked about another selection, period or currency than the one on screen').toEqual(riskQuestionOf(onScreen));
            await expectBusy(reload, '«Reload All» asked the correlation section again, and its button does not wait for it');

            await gate.release();
            await expectIdle(reload, 'the correlation section is back, and «Reload All» still waits');
        } finally {
            await gate.dispose();
        }
    });
});
