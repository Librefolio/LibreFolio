/**
 * «Updating prices…» end to end, the open page that catches up after it without saying it is busy, and the price pages
 * that ask their prices again after it (release 1.3, workstream Z, lots Z5, Z-13, Z-18, Z-14 and Z-14b/Z-15).
 *
 * Z5. While the server catches up on prices, every `/api/` answer carries `X-LibreFolio-Price-Refresh: starting|running`.
 * The axios interceptor hands the headers to `priceRefresh.observe()`; from the first one the tracker asks
 * `GET /api/v1/system/price-refresh` every 3 s (with `fetch`, same origin), shows the instance notice
 * `[data-testid="instance-notice"][data-notice-id="liveUpdates.priceRefresh"]` while a job runs, and at `idle` hides it.
 * Z-13. At that `idle`, when it saw a job run and the catch-up updated something (`last_refreshed`), the tracker sends the
 * portfolio bus's `{kind: 'prices'}` (`notifyPricesCaughtUp`): the caches turn stale, and the page on screen — the
 * Dashboard, a broker's page — asks for its report again in background, without force, with no navigation and without
 * anyone pressing «Aggiorna». Until Z-13 the tracker sent «Aggiorna»'s `{kind: 'refresh'}`, which only marks the caches:
 * the open page kept the figures of before the catch-up until it was reloaded.
 * Z-18, and the Refresh spinner of Y11 (P3). That reload is the page's own, not a load the user asked for, and the page
 * must not say otherwise: the Dashboard's root (`dashboard-page`) keeps `data-busy` — and `aria-busy`, bound to the same
 * flags — false through it (a screen reader announced «busy» for a price refresh nobody asked for), and neither page's
 * Refresh button (`sync-button`, `broker-refresh`: `pageBusy`) spins. A Refresh the user asks for still says busy, on both.
 *
 *   (a) Dashboard: a catch-up runs (the notice comes), ends having updated something (the notice goes), and the
 *       Dashboard asks for its main report again — once, the very question it showed — with no navigation.
 *   (b) A broker's page (Interactive Brokers, the mock's broker with positions): the same, on its overview report.
 *   (c) Dashboard, catch-ups that must not reload it: one whose job this page never saw run (`starting` → `idle`, with
 *       `last_refreshed` true even: no notice at any moment), then one that updated nothing (`running` → `idle` with
 *       `last_refreshed` false: the notice comes and goes). Then, in the same page, the control that gives the two
 *       absences their teeth: a catch-up that must reload it, and does, once.
 *   (d) Dashboard: from the end of a catch-up that updated something to the user's next click — the whole reload in it —
 *       neither the root nor its Refresh button says busy at any moment. Then the control, in the same page and under the
 *       same record: the user's Refresh says busy on both, and both come back to idle.
 *   (e) A broker's page: the same for its Refresh button (the root publishes no `data-busy`), with the same control.
 *   (f) Dashboard on its Positions tab, with the Performance view saved: the same as (d), with a contribution on screen —
 *       cached at load, turned stale by the catch-up, and asked again by the reload beside the main report.
 *
 * Z-14. The asset charts and the FX charts keep caches of their own for the session (`assetPriceStoreRegistry`,
 * `fxStoreRegistry`), and the price and rate answers fill backward the days without a value: a range once loaded holds a
 * point for every day, and was never asked again — not after a catch-up either. The end of a catch-up that updated
 * something (`{kind: 'prices'}`) turns those caches stale as well, and a page that loads a range it loaded before asks
 * it again. Each case leaves the page for the Dashboard through the sidebar, presses the Dashboard's Refresh there, and
 * comes back with the browser's Back: an in-app navigation, which the caches survive (a document load would empty them
 * and prove nothing — the document's time origin is checked at every return). The Refresh is the catch-up's trigger,
 * made explicit: the tracker hears the header only on an answer, and a Dashboard whose report is cached and fresh asks
 * nothing when it opens — after the FX page, which writes nothing, it is. The Refresh asks the main report with force,
 * and that answer is checked before the notice is awaited. It is pressed on the control's round trip too, so that the
 * catch-up is the only difference between the two returns — and the control proves as well that a user's Refresh alone
 * (`{kind: 'refresh'}`) leaves the price caches alone. The range ends today: it is the one a catch-up changes.
 *   (g) Asset detail, the mock's asset with a provider. The control first: back without a catch-up, the page asks
 *       nothing — no `POST /assets/prices/query` about the asset at all, events included (N64: its prices, events and
 *       signals come from the client caches) — although the live poll on the way (`POST /assets/prices/current`, a
 *       portfolio mutation for the bus) and the Dashboard's Refresh ran. The absence is read once the page's load has
 *       ended (root and Refresh button idle, chart drawn): a cache hit applies in the tick the load runs. Then a
 *       catch-up that updated something ends on the Dashboard, and back on the asset the page asks the prices again:
 *       the item carries `include_price: true`.
 *   (h) FX detail, a configured pair, without backend signals (with them the page asks its whole range at every load,
 *       cached or not; the first load's request shows it has none). The control: back without a catch-up, no
 *       `POST /fx/currencies/convert` for the pair at all once the page is settled. After the catch-up, back on the pair,
 *       one whose ranges cover the page's.
 *
 * The catch-up is the stub's, never the lane's. Nothing real runs on the shared backend, and nothing a real catch-up of
 * that backend (its startup, say) says can reach a case. One route on `**​/api/v1/**`, installed after the sign-in and
 * before the page under test loads:
 *   - the status route is answered in the browser with what the case scripts — `starting`, `running` with a job,
 *     `idle` with `last_finished_at` and `last_refreshed` — and each answer is counted;
 *   - every other API request goes to the real backend (`route.fetch()`) and comes back with its real body and the
 *     header the case has set, or with none: a real header is removed as well. The headers that described the body in
 *     transit (compression, length, chunking) are dropped, as fixtures/instance-config.ts explains.
 * The sign-in runs before the route, untouched (its `set-cookie` is the one answer here that sets a cookie), and the page
 * under test is then opened with a full load: the tracker of that document has heard nothing but the stub.
 *
 * Time: real timers, no page clock. The cadence is not under test here (priceRefresh.test.ts pins it with a fake poller,
 * and asset-live-pause.spec.ts the poller itself); what is under test is what the page does once the tracker has read
 * an answer. Each step waits on a positive count — a status answer the page has read — within a few polls, never on a
 * duration. The page clock would bound a window in page time, but under a frozen clock every timer of the Dashboard
 * (debounces, count-ups, chart animations) would have to be driven too, for a cadence nobody asserts here.
 *
 * The record, kept inside the page by an init script, every entry stamped with one sequence number:
 *   - each `POST /api/v1/portfolio/report` the page sends (`fetchReport`, portfolioStore), with its body, at `send()`,
 *     and how many of them are back;
 *   - each price or rate query a chart sends (`POST /api/v1/assets/prices/query`, `POST /api/v1/fx/currencies/convert`,
 *     Z-14), with its body, at `send()`; once its answer is back, the seq then, the HTTP status and what the answer held
 *     (the prices per asset, the number of rates);
 *   - each status answer the tracker has read, stamped ONE TASK LATER (a `MessageChannel` message). The tracker reads
 *     the answer and, in the same task, hides the notice and sends the signal; the page's listener reloads in a
 *     microtask, and the report leaves through axios in microtasks too. So when the record says an `idle` was read,
 *     a reload that answer caused is already recorded before it: the absence read at that moment is exact, not a bet
 *     on how long the page takes;
 *   - each time the notice element is put on screen (a `MutationObserver`): "no notice" means never, not "not now";
 *   - every value `data-busy` takes on the Dashboard's root and on the two Refresh buttons (a `MutationObserver` on the
 *     whole document): the value an element is put on screen with, then each change. A mutation record carries only the
 *     value before it, so a batch is read back value by value — the value after a record is the old value of the
 *     element's next record, or the value it has now — and a flag raised and dropped within one tick is still a `true`;
 *   - each click, stamped before the page handles it (a capture listener on the document): what the user's Refresh
 *     caused and what came before it are split by a seq, not by the moment the spec happened to look.
 * The record lives on `window`: it survives the in-app navigations of (c) and dies with a full load — the report it
 * still holds after a reload proves the reload came without one. A reaction deferred by a timer would escape the
 * one-task barrier; in (c) it would still be caught by the window, which stays open over two round trips through
 * Transactions until the control's reload, and is checked whole at the end.
 *
 * Which report. The Dashboard sends its main report (`loadAll`: history included, no contribution, no candles) and may
 * send the Performance contribution or the P&L candles beside it; the broker page its overview. Only the main report —
 * `include_history` true, `include_positions_contribution` and `include_pnl_candles` not — is counted, and the reload
 * must ask exactly the question the page showed: the same body, keys and broker ids in any order. In (f) the
 * contribution — `include_positions_contribution` true, no history — is told apart by its body too, never by its order.
 *
 * The silence of (d), (e) and (f). The window opens on the record before the stub says idle and closes on the control's
 * click, which comes once the reload has landed (every report back, the Dashboard's root settled); it is asserted after
 * the control, which therefore runs whatever the silence says: a red there is the page saying busy, never a blind record.
 * A silence also needs the flag down when the window opens — a flag already up needs no change to stay up — so the first
 * load's hold on the button is let go before, and the record must say so at the mark.
 *
 * Isolation: read-only on the lane's shared backend, safe beside any neighbour. TEST_USER signs in; the pages read
 * (`GET`s, and the report, a computation), and so does the control's Refresh (`requestPortfolioRefresh()` is a
 * client-side mark); the broker id is read with `page.request` (which no route intercepts), by name. The status route is
 * answered in the browser and the header is added in the browser, per page: no other test sees either. Nothing is
 * written on the backend, so there is nothing to clean up: the view (f) saves lives in this context's own localStorage,
 * and the routes and the init script go with the page. (g) and (h) read as well — the asset and the pair are found with
 * `page.request`, by name and provider, by route; the Dashboard's Refresh they press asks a report, a computation, and
 * marks client-side — and the one writer on their path, the live poll of the asset page
 * (`POST /assets/prices/current` writes today's candle), is answered in the browser with an empty result, as
 * asset-live-pause.spec.ts answers it.
 *
 * Desktop only: the tracker and the reload do not depend on the viewport, and (c), (g) and (h) move through the sidebar.
 *
 * Expected. (a)–(c) pin Z5 and Z-13, green (before Z-13 they were red at the reload, (c) at its control — its two
 * absences are green with or without Z-13, and the control is what keeps them from being vacuous). Before the code of
 * Z-18: (e) green, a regression pin of Y11; (d) red at its last assertion only — the Dashboard's root says busy through
 * the reload, `loadAll()` setting `reportLoading` — with its premises, its button pin and its control green before it;
 * (f) the same, its root raised by `contributionRefreshing` too (`loadContribution()`, on the stale cached contribution).
 * Before the code of Z-14: (g) and (h) red at the return after the catch-up — the page takes the range it had loaded from
 * its caches again (in (g) an item with `include_price: false`, or since N64 no prices query at all; in (h) no convert at
 * all) — with their premises and controls green.
 *
 * Z-14b + Z-15 (lot Y5-1). The views already on screen — the risk panel, the lots panel, the price pages, the lists —
 * reload by themselves after a catch-up that updated something, in silence (no navigation, no spinner, no `data-busy`,
 * the old figures staying): (i)–(m), and (g') and (h') for the pages that come back in-app. Their docblocks, below, say
 * what each protects; they were written before the code of Y5-1 and are red until it lands.
 */

import type {APIResponse, Route} from '@playwright/test';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {TEST_USER} from '../fixtures/test-users';

const API = '/api/v1';
const API_ROUTE = '**/api/v1/**';
const REPORT_PATH = `${API}/portfolio/report`;
/** Written out rather than imported: the spec pins the contract of Z5, it does not follow the code. */
const STATUS_PATH = `${API}/system/price-refresh`;
const HEADER = 'x-librefolio-price-refresh';
const NOTICE_SELECTOR = '[data-testid="instance-notice"][data-notice-id="liveUpdates.priceRefresh"]';
/**
 * The elements whose `data-busy` the record follows (Z-18, Y11, Z-15): the root of each page the cases watch and the Refresh
 * button of each, and the root of the Dashboard's risk panel (its `data-busy` is its first load).
 */
const BUSY_TEST_IDS = ['dashboard-page', 'sync-button', 'broker-refresh', 'risk-levels-panel', 'asset-detail-page', 'asset-detail-refresh-btn', 'fx-detail-page', 'fx-detail-refresh-btn', 'assets-page', 'assets-refresh-button', 'fx-page', 'fx-refresh-all-button'] as const;
type BusyTestId = (typeof BUSY_TEST_IDS)[number];
/** The tracker's cadence (PRICE_REFRESH_POLL_MS). */
const POLL_MS = 3_000;
/** A wait on the tracker: three polls — the one in flight, the next, and the answer's way back. */
const POLL_BUDGET_MS = 3 * POLL_MS;
/** A page load or an in-app navigation, with the report it asks for. */
const PAGE_TIMEOUT = 30_000;
/** The mock's broker with positions (populate_mock_data.py), found by name, never by position. */
const BROKER_WITH_HOLDINGS = 'Interactive Brokers';
/** Z-14: the query each chart sends for its range — the asset detail's prices, the FX detail's rates. */
const PRICES_QUERY_PATH = `${API}/assets/prices/query`;
const CONVERT_PATH = `${API}/fx/currencies/convert`;
/** Z-15: the questions of the risk panels and of the lots panel, recorded as the charts' queries are. */
const RISK_QUERY_PATH = `${API}/risk/query`;
const LOTS_PATH = `${API}/portfolio/lots/analysis`;
/**
 * Z-15: the elements whose REMOVAL the record follows — the figures a reload in background must leave on screen until the
 * new ones land. A skeleton in their place, or an unmount, is the page saying it is loading again.
 */
const KEPT_TEST_IDS = ['asset-detail-chart', 'fx-detail-chart', 'risk-l1-cards', 'unified-lots-table'] as const;
/** The asset detail's live poll, answered in the browser in (g): the endpoint writes today's candle. */
const LIVE_PRICES_ROUTE = '**/api/v1/assets/prices/current*';
/** The mock's asset with a provider (populate_mock_data.py: populate_assets, populate_asset_provider_assignments), found by name and provider, never by position. */
const PRICED_ASSET = {displayName: 'Apple Inc.', providerCode: 'yfinance'} as const;
/** A pair the mock configures a route for (populate_mock_data.populate_fx_currency_pair_sources), checked through the routes, never assumed. */
const CONFIGURED_PAIR = {base: 'EUR', quote: 'USD'} as const;
/** How far back the range of (g) and (h) starts: well inside the mock's prices and rates, which run to today. */
const RANGE_DAYS = 60;

type CatchUpHeader = 'starting' | 'running' | null;
type PriceRefreshState = 'idle' | 'starting' | 'running';

/** `GET /api/v1/system/price-refresh` (backend/app/schemas/sleep_wake.py, PriceRefreshResponse). */
interface StatusBody {
    state: PriceRefreshState;
    reason: 'startup' | 'return' | 'wake' | null;
    job: string | null;
    since: string | null;
    last_finished_at: string | null;
    last_refreshed: boolean;
}

/** A catch-up announced, no job running yet. */
function starting(): StatusBody {
    return {state: 'starting', reason: 'return', job: null, since: new Date().toISOString(), last_finished_at: null, last_refreshed: false};
}

/** A catch-up running its live-price job. */
function running(): StatusBody {
    return {state: 'running', reason: 'return', job: 'current_price', since: new Date().toISOString(), last_finished_at: null, last_refreshed: false};
}

/** The catch-up is over, having updated something or not. */
function idle(lastRefreshed: boolean): StatusBody {
    return {state: 'idle', reason: null, job: null, since: null, last_finished_at: new Date().toISOString(), last_refreshed: lastRefreshed};
}

/** What the stub says, changed by the case as it goes, and what it has served. */
interface CatchUp {
    /** The value of the header on every API answer from now on; null: none (a real one is removed too). */
    header: CatchUpHeader;
    /** The answer of the status route from now on. */
    status: StatusBody;
    /** The state of every status answer served, in order. */
    served: PriceRefreshState[];
}

/** The real answer's headers with the case's catch-up header in place of any real one, without the three that described the body in transit. */
function withCatchUpHeader(response: APIResponse, value: CatchUpHeader): Record<string, string> {
    const dropped = new Set(['content-encoding', 'content-length', 'transfer-encoding', HEADER]);
    const headers = Object.fromEntries(Object.entries(response.headers()).filter(([name]) => !dropped.has(name.toLowerCase())));
    if (value !== null) headers[HEADER] = value;
    return headers;
}

/** The catch-up as the page will see it: the status route answered in the browser, the header on every other API answer. */
async function simulateCatchUp(page: Page, initial: {header: CatchUpHeader; status: StatusBody}): Promise<CatchUp> {
    const catchUp: CatchUp = {header: initial.header, status: initial.status, served: []};
    await page.route(API_ROUTE, async (route) => {
        if (new URL(route.request().url()).pathname === STATUS_PATH) {
            const body = catchUp.status;
            await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
            catchUp.served.push(body.state);
            return;
        }
        let response: APIResponse;
        try {
            response = await route.fetch();
        } catch {
            // Only when the page went away with the request in flight (the end of a test): there is no one to answer.
            await route.abort().catch(() => undefined);
            return;
        }
        // The header is read when the answer leaves, not when the request came: an answer that lands after the case
        // switched carries the new value, as a real answer would.
        await route.fulfill({response, headers: withCatchUpHeader(response, catchUp.header)}).catch(() => undefined);
    });
    return catchUp;
}

type ReportBody = Record<string, unknown> & {broker_ids?: number[]};

/** A value `data-busy` took on an element of BUSY_TEST_IDS: the one it was put on screen with (`mount`), or a change. */
interface BusyEntry {
    seq: number;
    testId: string;
    kind: 'mount' | 'change';
    value: string | null;
}

/** A price or rate query a chart sent (Z-14), or a risk or lots question (Z-15): its body at `send()`, then what came back. */
interface QueryEntry {
    seq: number;
    path: string;
    body: unknown;
    /** The seq at which its answer was back (load, error or abort); null while it is in flight. */
    settled: number | null;
    status: number | null;
    /** `prices/query`: the prices per asset of the answer; `convert`: how many results. Null in flight, unreadable, or a risk or lots question (their answers are not summarised). */
    answer: {items?: Array<{asset_id: unknown; prices: number}>; results?: number} | null;
}

/** The record the init script keeps on `window` (see the header). */
interface PageRecord {
    seq: number;
    reports: Array<{seq: number; body: ReportBody | null}>;
    reportsSettled: number;
    queries: QueryEntry[];
    statusRead: Array<{seq: number; state: string}>;
    noticeShown: number[];
    busy: BusyEntry[];
    /** Each click, with the test id of the nearest marked element (the target's own, or an ancestor's). */
    clicks: Array<{seq: number; testId: string | null}>;
    /** Z-15: each element whose test id ends in `-loading` or `-refreshing` put on screen — the skeletons and the spinning icons. */
    appeared: Array<{seq: number; testId: string}>;
    /** Z-15: each element of KEPT_TEST_IDS taken off the screen. */
    removed: Array<{seq: number; testId: string}>;
}

/** Arms the record for every document this page opens from now on: call it before the page under test loads. */
async function recordPage(page: Page): Promise<void> {
    await page.addInitScript(
        ({reportPath, statusPath, queryPaths, noticeSelector, busyTestIds, keptTestIds}: {reportPath: string; statusPath: string; queryPaths: {prices: string; convert: string; risk: string; lots: string}; noticeSelector: string; busyTestIds: string[]; keptTestIds: string[]}) => {
            const record = {
                seq: 0,
                reports: [] as Array<{seq: number; body: unknown}>,
                reportsSettled: 0,
                queries: [] as Array<{seq: number; path: string; body: unknown; settled: number | null; status: number | null; answer: unknown}>,
                statusRead: [] as Array<{seq: number; state: string}>,
                noticeShown: [] as number[],
                busy: [] as Array<{seq: number; testId: string; kind: 'mount' | 'change'; value: string | null}>,
                clicks: [] as Array<{seq: number; testId: string | null}>,
                appeared: [] as Array<{seq: number; testId: string}>,
                removed: [] as Array<{seq: number; testId: string}>,
            };
            Object.defineProperty(window, '__lfSpecPriceRefresh', {value: record});
            const pathOf = (url: string): string => {
                try {
                    return new URL(url, window.location.href).pathname;
                } catch {
                    return '';
                }
            };
            const parsed = (body: unknown): unknown => {
                try {
                    return typeof body === 'string' ? JSON.parse(body) : null;
                } catch {
                    return null;
                }
            };

            // The price and rate queries of the charts (Z-14): the body when it leaves, then what its answer held.
            const isQueryPath = (path: string): boolean => path === queryPaths.prices || path === queryPaths.convert || path === queryPaths.risk || path === queryPaths.lots;
            const summary = (path: string, text: string): unknown => {
                // The risk and lots answers are not summarised: the cases read their questions, not their figures.
                if (path !== queryPaths.prices && path !== queryPaths.convert) return null;
                let data: {items?: unknown; results?: unknown} | null;
                try {
                    data = JSON.parse(text) as {items?: unknown; results?: unknown} | null;
                } catch {
                    return null;
                }
                if (data === null || typeof data !== 'object') return null;
                if (path === queryPaths.prices) {
                    const items = Array.isArray(data.items) ? (data.items as Array<{asset_id?: unknown; prices?: unknown} | null>) : [];
                    return {
                        items: items.map((item) => {
                            const prices = item?.prices;
                            return {asset_id: item?.asset_id ?? null, prices: Array.isArray(prices) ? prices.length : 0};
                        }),
                    };
                }
                return {results: Array.isArray(data.results) ? data.results.length : 0};
            };
            /** Records a query as it leaves; the function returned records its answer. */
            const sendQuery = (path: string, body: unknown): ((status: number, text: string) => void) => {
                const entry = {seq: ++record.seq, path, body: parsed(body), settled: null as number | null, status: null as number | null, answer: null as unknown};
                record.queries.push(entry);
                return (status, text) => {
                    entry.status = status;
                    entry.answer = summary(path, text);
                    entry.settled = ++record.seq;
                };
            };

            // XHR: what axios, and so `fetchReport` and the two charts' queries, uses today.
            const reportXhrs = new WeakSet<XMLHttpRequest>();
            const queryXhrs = new WeakMap<XMLHttpRequest, string>();
            const nativeOpen = XMLHttpRequest.prototype.open;
            const nativeSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function (this: XMLHttpRequest, ...args: unknown[]) {
                const isPost = String(args[0]).toUpperCase() === 'POST';
                const path = pathOf(String(args[1]));
                if (isPost && path === reportPath) reportXhrs.add(this);
                else reportXhrs.delete(this);
                if (isPost && isQueryPath(path)) queryXhrs.set(this, path);
                else queryXhrs.delete(this);
                return Reflect.apply(nativeOpen, this, args);
            } as XMLHttpRequest['open'];
            XMLHttpRequest.prototype.send = function (this: XMLHttpRequest, ...args: unknown[]) {
                if (reportXhrs.has(this)) {
                    record.reports.push({seq: ++record.seq, body: parsed(args[0])});
                    this.addEventListener('loadend', () => {
                        record.reportsSettled += 1;
                    });
                }
                const queryPath = queryXhrs.get(this);
                if (queryPath !== undefined) {
                    const answered = sendQuery(queryPath, args[0]);
                    // axios leaves `responseType` empty for JSON and parses the text itself.
                    this.addEventListener('loadend', () => answered(this.status, this.responseType === '' || this.responseType === 'text' ? this.responseText : ''));
                }
                return Reflect.apply(nativeSend, this, args);
            } as XMLHttpRequest['send'];

            // fetch: what the tracker uses for the status. A report or a chart query sent with fetch is recorded too, so
            // that a change of transport cannot hide one.
            const nativeFetch = window.fetch;
            const nextTask = new MessageChannel();
            const queued: Array<() => void> = [];
            nextTask.port1.onmessage = () => queued.shift()?.();
            window.fetch = async function (input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
                const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
                const method = (init?.method ?? (input instanceof Request ? input.method : 'GET')).toUpperCase();
                const path = pathOf(url);
                const isReport = method === 'POST' && path === reportPath;
                if (isReport) record.reports.push({seq: ++record.seq, body: parsed(init?.body)});
                const answered = method === 'POST' && isQueryPath(path) ? sendQuery(path, init?.body) : null;
                let response: Response;
                try {
                    response = await nativeFetch.call(window, input, init);
                } catch (error) {
                    answered?.(0, '');
                    throw error;
                } finally {
                    if (isReport) record.reportsSettled += 1;
                }
                if (answered !== null) {
                    const copy = response.clone();
                    answered(response.status, await copy.text().catch(() => ''));
                }
                if (path !== statusPath) return response;
                const read = response.json.bind(response);
                response.json = async () => {
                    const data = (await read()) as {state?: unknown} | null;
                    // One task later: the tracker has read this answer, and everything it set off in microtasks — the
                    // notice hidden, the signal sent, the page's reload sent — is already in the record.
                    queued.push(() => record.statusRead.push({seq: ++record.seq, state: String(data?.state)}));
                    nextTask.port2.postMessage(null);
                    return data;
                };
                return response;
            };

            // The notice, each time it is put on screen.
            new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    for (const node of Array.from(mutation.addedNodes)) {
                        if (node instanceof Element && (node.matches(noticeSelector) || node.querySelector(noticeSelector) !== null)) record.noticeShown.push(++record.seq);
                    }
                }
            }).observe(document, {childList: true, subtree: true});

            // The busy flags, every value they take: the one an element is put on screen with, then each change — on the
            // whole document, so an element that mounts after the navigation (or again, after an in-app return) is
            // followed from its insertion. A mutation record carries only the value before it, so a batch is read back
            // value by value: the value after a record is the old value of the element's next record in the batch or,
            // after its last one, the value it has now. A flag raised and dropped within one tick is still a `true` here.
            const watched = new Set(busyTestIds);
            const kept = new Set(keptTestIds);
            const keptSelector = keptTestIds.map((testId) => `[data-testid="${testId}"]`).join(', ');
            const watchedSelector = busyTestIds.map((testId) => `[data-testid="${testId}"]`).join(', ');
            const watchedTestId = (node: Node): string | null => {
                const testId = node instanceof Element ? node.getAttribute('data-testid') : null;
                return testId !== null && watched.has(testId) ? testId : null;
            };
            new MutationObserver((mutations) => {
                // The entries of this batch still waiting for their value, per element.
                const waiting = new Map<Element, Array<{value: string | null}>>();
                const settle = (element: Element, value: string | null): void => {
                    for (const entry of waiting.get(element) ?? []) entry.value = value;
                    waiting.delete(element);
                };
                const note = (element: Element, testId: string, kind: 'mount' | 'change'): void => {
                    const entry = {seq: ++record.seq, testId, kind, value: null as string | null};
                    record.busy.push(entry);
                    waiting.set(element, [...(waiting.get(element) ?? []), entry]);
                };
                for (const mutation of mutations) {
                    const target = mutation.target;
                    if (mutation.type === 'attributes') {
                        const testId = watchedTestId(target);
                        if (testId === null || !(target instanceof Element)) continue;
                        settle(target, mutation.oldValue);
                        note(target, testId, 'change');
                        continue;
                    }
                    for (const node of Array.from(mutation.addedNodes)) {
                        if (!(node instanceof Element)) continue;
                        for (const element of [node, ...Array.from(node.querySelectorAll(watchedSelector))]) {
                            const testId = watchedTestId(element);
                            if (testId !== null) note(element, testId, 'mount');
                        }
                        // The skeletons and spinning icons (Z-15): a reload in background must put none on screen.
                        for (const element of [node, ...Array.from(node.querySelectorAll('[data-testid]'))]) {
                            const testId = element.getAttribute('data-testid');
                            if (testId !== null && (testId.endsWith('-loading') || testId.endsWith('-refreshing'))) record.appeared.push({seq: ++record.seq, testId});
                        }
                    }
                    // The figures a reload in background must leave on screen (Z-15).
                    for (const node of Array.from(mutation.removedNodes)) {
                        if (!(node instanceof Element)) continue;
                        for (const element of [node, ...Array.from(node.querySelectorAll(keptSelector))]) {
                            const testId = element.getAttribute('data-testid');
                            if (testId !== null && kept.has(testId)) record.removed.push({seq: ++record.seq, testId});
                        }
                    }
                }
                for (const element of Array.from(waiting.keys())) settle(element, element.getAttribute('data-busy'));
            }).observe(document, {childList: true, subtree: true, attributes: true, attributeFilter: ['data-busy'], attributeOldValue: true});

            // Each click, stamped before the page handles it: a capture listener on the document runs before the page's
            // own (on the button or, delegated, on the app's root, both bubbling). What the click caused comes after its seq.
            document.addEventListener(
                'click',
                (event) => {
                    const marked = event.target instanceof Element ? event.target.closest('[data-testid]') : null;
                    record.clicks.push({seq: ++record.seq, testId: marked?.getAttribute('data-testid') ?? null});
                },
                true,
            );
        },
        {reportPath: REPORT_PATH, statusPath: STATUS_PATH, queryPaths: {prices: PRICES_QUERY_PATH, convert: CONVERT_PATH, risk: RISK_QUERY_PATH, lots: LOTS_PATH}, noticeSelector: NOTICE_SELECTOR, busyTestIds: [...BUSY_TEST_IDS], keptTestIds: [...KEPT_TEST_IDS]},
    );
}

async function pageRecord(page: Page): Promise<PageRecord> {
    return page.evaluate(() => {
        const record = (window as unknown as {__lfSpecPriceRefresh?: unknown}).__lfSpecPriceRefresh;
        if (record === undefined) throw new Error('the record is missing: recordPage() must run before the page under test loads, and a full load since then started a fresh one');
        return JSON.parse(JSON.stringify(record)) as PageRecord;
    });
}

/** The page's main report: history included, no contribution, no candles (Dashboard `loadAll`, broker `loadOverview`). */
function isMainReport(body: ReportBody | null): body is ReportBody {
    return body !== null && body.include_history === true && body.include_positions_contribution !== true && body.include_pnl_candles !== true;
}

/** The main reports sent after `since`. */
function mainReportsSince(record: PageRecord, since: number): ReportBody[] {
    return record.reports.filter((report) => report.seq > since && isMainReport(report.body)).map((report) => report.body as ReportBody);
}

/** The contribution of the Performance view (Dashboard `loadContribution`): the positions' contribution alone, no history. */
function isContributionReport(body: ReportBody | null): body is ReportBody {
    return body !== null && body.include_positions_contribution === true && body.include_history === false;
}

/** The contribution requests sent after `since`. */
function contributionsSince(record: PageRecord, since: number): ReportBody[] {
    return record.reports.filter((report) => report.seq > since && isContributionReport(report.body)).map((report) => report.body as ReportBody);
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

/** Waits until the page has read a status answer in `state` after `since`, and returns the seq of that reading. */
async function statusRead(page: Page, since: number, state: PriceRefreshState, message: string): Promise<number> {
    let seq = -1;
    await expect
        .poll(
            async () => {
                seq = (await pageRecord(page)).statusRead.find((read) => read.seq > since && read.state === state)?.seq ?? -1;
                return seq;
            },
            {message, timeout: POLL_BUDGET_MS},
        )
        .toBeGreaterThan(since);
    return seq;
}

/** Waits until a main report has been sent and every report sent so far is back; returns the last main report. */
async function mainReportLanded(page: Page, message: string, matches: (body: ReportBody) => boolean = () => true): Promise<{seq: number; body: ReportBody}> {
    let landed: {seq: number; body: ReportBody} | null = null;
    await expect
        .poll(
            async () => {
                const record = await pageRecord(page);
                const mains = record.reports.filter((report) => isMainReport(report.body) && matches(report.body as ReportBody));
                const last = mains[mains.length - 1];
                landed = last !== undefined && record.reportsSettled >= record.reports.length ? {seq: last.seq, body: last.body as ReportBody} : null;
                return landed !== null;
            },
            {message, timeout: PAGE_TIMEOUT},
        )
        .toBe(true);
    return landed!;
}

/** Waits until every report the page has sent is back: nothing of the case is left in flight. */
async function reportsSettled(page: Page): Promise<void> {
    await expect
        .poll(
            async () => {
                const record = await pageRecord(page);
                return record.reportsSettled >= record.reports.length;
            },
            {message: 'a report the page sent never came back', timeout: PAGE_TIMEOUT},
        )
        .toBe(true);
}

/** The value `data-busy` of `testId` had at `seq` by the record; undefined when the record had not seen it put on screen yet. */
function busyAt(record: PageRecord, testId: BusyTestId, seq: number): string | null | undefined {
    let value: string | null | undefined;
    for (const entry of record.busy) if (entry.testId === testId && entry.seq <= seq) value = entry.value;
    return value;
}

/** Each moment `testId` said busy after `since` and before `until`: put on screen with `data-busy="true"`, or switched to it. */
function busyRaised(record: PageRecord, testId: BusyTestId, since: number, until = Number.POSITIVE_INFINITY): BusyEntry[] {
    return record.busy.filter((entry) => entry.testId === testId && entry.seq > since && entry.seq < until && entry.value === 'true');
}

function notice(page: Page): Locator {
    return page.locator(NOTICE_SELECTOR);
}

function dashboard(page: Page): Locator {
    return page.getByTestId('dashboard-page');
}

/** The id of a broker TEST_USER sees, by name, read with `page.request` (no route intercepts it). */
async function brokerIdByName(page: Page, name: string): Promise<number> {
    const response = await page.request.get(`${API}/brokers`);
    expect(response.ok(), `GET ${API}/brokers → HTTP ${response.status()}`).toBe(true);
    const items = ((await response.json()) as {items?: Array<{id: number; name: string}>}).items ?? [];
    const broker = items.find((item) => item.name === name);
    if (!broker) throw new Error(`${name} is the broker the mock gives positions to, shared with TEST_USER — check populate_mock_data.py (brokers seen: ${items.map((item) => item.name).join(', ') || 'none'})`);
    return broker.id;
}

/** Through the sidebar to Transactions and back, each page settled: the Dashboard is destroyed and mounted again, and the API answers on the way carry the header the case has set. */
async function roundTripThroughTransactions(page: Page): Promise<void> {
    await page.getByTestId('nav-transactions').click();
    const transactions = page.getByTestId('transactions-page');
    await expect(transactions).toBeVisible({timeout: PAGE_TIMEOUT});
    await waitForSettled(transactions, PAGE_TIMEOUT);
    await page.getByTestId('nav-dashboard').click();
    await expect(dashboard(page)).toBeVisible({timeout: PAGE_TIMEOUT});
    await waitForSettled(dashboard(page), PAGE_TIMEOUT);
}

/**
 * The end of a running catch-up that updated something, on the page on screen: the notice is on and the tracker has
 * read a `running` answer (both checked, not assumed); the stub then stops adding the header and answers `idle` with
 * `last_refreshed`. Returns where the record stood before the switch and the seq at which the page had read the idle.
 */
async function endRunningCatchUp(page: Page, catchUp: CatchUp, since: number, lastRefreshed: boolean): Promise<{mark: number; idleRead: number}> {
    await expect(notice(page), 'a running catch-up shows the notice (Z5)').toBeVisible({timeout: POLL_BUDGET_MS});
    await expect(notice(page)).toHaveAttribute('data-severity', 'info');
    await statusRead(page, since, 'running', 'the tracker never read a running answer: it did not start on the header, or it does not ask the status route');

    const mark = (await pageRecord(page)).seq;
    catchUp.header = null;
    catchUp.status = idle(lastRefreshed);
    const idleRead = await statusRead(page, mark, 'idle', 'the page never read the idle answer: the tracker stopped asking before the catch-up was over');
    await expect(notice(page), 'the notice outlived the catch-up (Z5)').toHaveCount(0);
    return {mark, idleRead};
}

/**
 * The end of a running catch-up that updated something, and the reload in background it causes, up to its landing. The
 * reload is checked, not assumed — a main report sent after the mark — and its landing is every report back, then
 * `settled`. Returns the mark: from there to the next click the record spans the whole reload.
 */
async function backgroundReloadLanded(page: Page, catchUp: CatchUp, settled: () => Promise<void>): Promise<number> {
    const {mark} = await endRunningCatchUp(page, catchUp, 0, true);
    await expect
        .poll(async () => mainReportsSince(await pageRecord(page), mark).length, {
            message: 'the catch-up updated the prices and the page did not ask for its report again: there is no reload in background to watch (Z-13)',
            timeout: POLL_BUDGET_MS,
        })
        .toBeGreaterThan(0);
    await reportsSettled(page);
    await settled();
    return mark;
}

/**
 * The control of a silence (Y11, Z-18): a Refresh the user asks for, in the same page and under the same record. Clicks
 * the button `refresh` names and returns the seq of that click, stamped in the page before the page handled it. After it
 * the record must see each of `says` say busy and the Refresh must ask the main report again; the page is then left
 * settled — the button idle, every report back, `settled` — and the record must end where the page is, idle: it follows
 * the flag both ways. A record that missed any of this would be blind, and its silence through the reload worthless.
 */
async function userRefreshSaysBusy(page: Page, refresh: 'sync-button' | 'broker-refresh', says: readonly BusyTestId[], settled: () => Promise<void>): Promise<number> {
    const button = page.getByTestId(refresh);
    const before = (await pageRecord(page)).seq;
    await expect(button, 'the Refresh button cannot be pressed: a load of the page is still pending').toBeEnabled({timeout: PAGE_TIMEOUT});
    await button.click();
    let clicked = -1;
    await expect
        .poll(
            async () => {
                clicked = (await pageRecord(page)).clicks.find((click) => click.seq > before && click.testId === refresh)?.seq ?? -1;
                return clicked;
            },
            {message: 'the click on the Refresh button never reached the page', timeout: POLL_BUDGET_MS},
        )
        .toBeGreaterThan(before);
    for (const testId of says) {
        await expect
            .poll(async () => busyRaised(await pageRecord(page), testId, clicked).length, {
                message: `the control: the user asked for a Refresh and the record never saw ${testId} say busy — the record is blind to it, or the page no longer says busy for a load the user asked for; either way its silence through the reload proves nothing`,
                timeout: PAGE_TIMEOUT,
            })
            .toBeGreaterThan(0);
    }
    await expect.poll(async () => mainReportsSince(await pageRecord(page), clicked).length, {message: 'the control: the Refresh did not ask the main report again', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);
    await expect(button, 'the control: the Refresh never let go of its button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
    await reportsSettled(page);
    await settled();
    const record = await pageRecord(page);
    for (const testId of says) expect(busyAt(record, testId, record.seq), `the record does not end where the page is: ${testId} is idle on screen`).toBe('false');
    return clicked;
}

/** A toggle that publishes `aria-pressed`, pressed unless it is already: the state is asked first, the end state asserted. */
async function pressToggle(button: Locator, why: string): Promise<void> {
    await expect(button, why).toBeVisible({timeout: PAGE_TIMEOUT});
    if ((await button.getAttribute('aria-pressed')) !== 'true') await button.click();
    await expect(button, why).toHaveAttribute('aria-pressed', 'true');
}

/**
 * Saves the Dashboard's positions view as Performance × table the way a user does, through the panel's toggles:
 * PositionsPanel writes both modes per user in this context's localStorage on the click, and reads them back when it
 * mounts. Ends on the view itself, its contribution on screen: a view with nothing to show would leave the case without
 * a contribution to cache.
 */
async function saveDashboardPerformanceView(page: Page): Promise<void> {
    await navigateTo(page, '/dashboard?tab=posizioni');
    const panel = page.getByTestId('positions-panel');
    await pressToggle(panel.getByTestId('positions-toggle-performance'), 'the Performance view of the positions panel could not be chosen');
    await pressToggle(panel.getByTestId('positions-toggle-table'), 'the table view of the positions panel could not be chosen');
    await expect(panel.getByTestId('contribution-table'), "the Dashboard's Performance view shows no contribution: check populate_mock_data.py").toBeVisible({timeout: PAGE_TIMEOUT});
}

// Z-14: the caches of the price charts, (g) and (h).

type DateRange = {start: string; end: string};
type Pair = {slug: string; base: string; quote: string};
/** An item of a `POST /assets/prices/query` body, as the asset page writes it. */
type PriceQueryItem = {asset_id?: unknown; date_range?: DateRange; include_price?: unknown; include_events?: unknown};
/** An item of a `POST /fx/currencies/convert` body, as the FX page writes it. */
type ConvertItem = {from_amount?: {code?: unknown}; to?: unknown; date_range?: DateRange; signals?: unknown[]};

/** The range of (g) and (h), written in the URL: two months ending today — the days a catch-up changes. */
function rangeEndingToday(): DateRange {
    return {start: daysAgoIso(RANGE_DAYS), end: todayIso()};
}

/** The id of the mock's asset with a provider, by name and provider through `GET /assets/query` (`page.request`, which no route intercepts). */
async function pricedAssetId(page: Page): Promise<number> {
    const response = await page.request.get(`${API}/assets/query?search=${encodeURIComponent(PRICED_ASSET.displayName)}`);
    expect(response.ok(), `GET ${API}/assets/query → HTTP ${response.status()}`).toBe(true);
    const matches = ((await response.json()) as Array<{id: number; display_name: string; provider_code: string | null}>).filter((asset) => asset.display_name === PRICED_ASSET.displayName && asset.provider_code === PRICED_ASSET.providerCode);
    if (matches.length !== 1) throw new Error(`${PRICED_ASSET.displayName} with its ${PRICED_ASSET.providerCode} provider must be one asset ${TEST_USER.username} can read — check populate_mock_data.py (populate_assets, populate_asset_provider_assignments); found ${matches.length}`);
    return matches[0].id;
}

/** `base`/`quote` as a pair with a configured route, in canonical order, checked through `GET /fx/providers/routes` (`page.request`). */
async function configuredPair(page: Page, base: string, quote: string): Promise<Pair> {
    const canonicalBase = base < quote ? base : quote;
    const canonicalQuote = base < quote ? quote : base;
    const slug = `${canonicalBase}-${canonicalQuote}`;
    const response = await page.request.get(`${API}/fx/providers/routes`);
    expect(response.ok(), `GET ${API}/fx/providers/routes → HTTP ${response.status()}`).toBe(true);
    const items = ((await response.json()) as {items?: Array<{base: string; quote: string}>}).items ?? [];
    const slugs = [...new Set(items.map((item) => [item.base, item.quote].sort().join('-')))];
    if (!slugs.includes(slug)) throw new Error(`${slug} has no configured route — check populate_mock_data.populate_fx_currency_pair_sources (pairs seen: ${slugs.join(', ') || 'none'})`);
    return {slug, base: canonicalBase, quote: canonicalQuote};
}

/**
 * `POST /assets/prices/current` — the asset page's live poll — answered in the browser with a schema-valid empty result, as
 * asset-live-pause.spec.ts answers it: the endpoint asks a live provider and writes today's candle, and nothing here may
 * write. For the axios interceptor each answer is still a successful mutation: `{kind: 'mutation'}` on the bus. Registered
 * after `simulateCatchUp`, so that it answers before that route sees the request. Counts its answers.
 */
async function stubLivePrices(page: Page): Promise<{served: number}> {
    const live = {served: 0};
    await page.route(LIVE_PRICES_ROUTE, async (route) => {
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({results: [], success_count: 0, errors: []})});
        live.served += 1;
    });
    return live;
}

function assetDetail(page: Page): Locator {
    return page.getByTestId('asset-detail-page');
}

function fxDetail(page: Page): Locator {
    return page.getByTestId('fx-detail-page');
}

/** The time origin of the document on screen: an in-app navigation keeps it; a document load — which empties every cache of the page — changes it. */
async function documentOrigin(page: Page): Promise<number> {
    return page.evaluate(() => performance.timeOrigin);
}

/** Through the sidebar to the Dashboard, settled, every report back: the chart page is destroyed, the caches it filled — module singletons — stay. */
async function leaveForDashboard(page: Page): Promise<void> {
    await page.getByTestId('nav-dashboard').click();
    await expect(dashboard(page)).toBeVisible({timeout: PAGE_TIMEOUT});
    await waitForSettled(dashboard(page), PAGE_TIMEOUT);
    await reportsSettled(page);
}

/** The Dashboard at rest: every report back, its root settled, its Refresh idle — nothing of it in flight. */
async function dashboardSettled(page: Page): Promise<void> {
    await reportsSettled(page);
    await waitForSettled(dashboard(page), PAGE_TIMEOUT);
    await expect(page.getByTestId('sync-button'), 'the Dashboard never let go of its Refresh button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
}

/**
 * The Dashboard's Refresh (`sync-button`), pressed once the page lets it be, and checked: the click reached the page, and
 * the main report it asks with force (`loadAll(true)`) was sent after it and is back — `message` says what its absence
 * means where it is pressed. Read-only on the server, the report being a computation; on the client «Aggiorna»'s
 * `{kind: 'refresh'}`, which Z-14 leaves the price caches alone on. No history entry: one Back still returns to the chart
 * page. Ends on the Dashboard at rest.
 */
async function refreshDashboard(page: Page, message: string): Promise<void> {
    const button = page.getByTestId('sync-button');
    const before = (await pageRecord(page)).seq;
    await expect(button, 'the Refresh button cannot be pressed: a load of the Dashboard is still pending').toBeEnabled({timeout: PAGE_TIMEOUT});
    await button.click();
    let clicked = -1;
    await expect
        .poll(
            async () => {
                clicked = (await pageRecord(page)).clicks.find((click) => click.seq > before && click.testId === 'sync-button')?.seq ?? -1;
                return clicked;
            },
            {message: 'the click on the Refresh button never reached the page', timeout: POLL_BUDGET_MS},
        )
        .toBeGreaterThan(before);
    await expect
        .poll(
            async () => {
                const record = await pageRecord(page);
                return mainReportsSince(record, clicked).length > 0 && record.reportsSettled >= record.reports.length;
            },
            {message, timeout: PAGE_TIMEOUT},
        )
        .toBe(true);
    await dashboardSettled(page);
}

/** Back to the chart page with the browser's own Back, an in-app navigation; returns where the record stood before it. */
async function backInApp(page: Page, root: Locator): Promise<number> {
    const mark = (await pageRecord(page)).seq;
    await page.goBack();
    await expect(root, 'Back did not return to the chart page').toBeVisible({timeout: PAGE_TIMEOUT});
    return mark;
}

/** The items of a `prices/query` body that ask about `assetId`. */
function assetItems(entry: QueryEntry, assetId: number): PriceQueryItem[] {
    if (!Array.isArray(entry.body)) return [];
    return (entry.body as Array<PriceQueryItem | null>).filter((item): item is PriceQueryItem => item !== null && typeof item === 'object' && item.asset_id === assetId);
}

/** How many prices of `assetId` the answer of a `prices/query` carried. */
function pricesOf(entry: QueryEntry, assetId: number): number {
    return entry.answer?.items?.find((item) => item.asset_id === assetId)?.prices ?? 0;
}

/** Waits until the page has sent a `prices/query` asking about `assetId` after `since` and its answer is back; returns the first such query and the asset's item. */
async function assetQueryLanded(page: Page, assetId: number, since: number, message: string): Promise<{entry: QueryEntry; item: PriceQueryItem}> {
    let landed: {entry: QueryEntry; item: PriceQueryItem} | null = null;
    await expect
        .poll(
            async () => {
                const entry = (await pageRecord(page)).queries.find((query) => query.seq > since && query.path === PRICES_QUERY_PATH && assetItems(query, assetId).length > 0);
                landed = entry !== undefined && entry.settled !== null ? {entry, item: assetItems(entry, assetId)[0]} : null;
                return landed !== null;
            },
            {message, timeout: PAGE_TIMEOUT},
        )
        .toBe(true);
    return landed!;
}

/** The items of a `convert` body that ask about `pair`, whichever way round. */
function pairItems(entry: QueryEntry, pair: Pair): ConvertItem[] {
    if (!Array.isArray(entry.body)) return [];
    return (entry.body as Array<ConvertItem | null>).filter((item): item is ConvertItem => item !== null && typeof item === 'object' && [String(item.from_amount?.code), String(item.to)].sort().join('-') === pair.slug);
}

/** The `convert` requests sent after `since` that ask about `pair`. */
function pairConvertsSince(record: PageRecord, pair: Pair, since: number): QueryEntry[] {
    return record.queries.filter((query) => query.seq > since && query.path === CONVERT_PATH && pairItems(query, pair).length > 0);
}

/** Waits until the page has sent a `convert` asking about `pair` after `since` and its answer is back; returns the first such request. */
async function pairConvertLanded(page: Page, pair: Pair, since: number, message: string): Promise<QueryEntry> {
    let landed: QueryEntry | null = null;
    await expect
        .poll(
            async () => {
                const entry = pairConvertsSince(await pageRecord(page), pair, since)[0];
                landed = entry !== undefined && entry.settled !== null ? entry : null;
                return landed !== null;
            },
            {message, timeout: PAGE_TIMEOUT},
        )
        .toBe(true);
    return landed!;
}

/**
 * The FX page has finished loading, on `pair`, with a rate on screen: its chart (the root's `data-busy`, `loading`) and the
 * rest of its first load (the Refresh button's, `pageBusy`). A rate request the load needed has left and come back by
 * then — on a miss the root stays busy until the answer —, so what the record holds of this load is all of it.
 */
async function fxDetailSettled(page: Page, pair: Pair): Promise<void> {
    const root = fxDetail(page);
    await waitForSettled(root, PAGE_TIMEOUT);
    await expect(page.getByTestId('fx-detail-refresh-btn'), 'the load of the FX page never let go of its Refresh button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
    await expect(root).toHaveAttribute('data-chart-pair', pair.slug);
    await expect(root, `the page of ${pair.slug} shows no rate: nothing is cached for a catch-up to turn stale — check populate_mock_data.populate_fx_rates`).toHaveAttribute('data-chart-last-rate', /\d/);
}

/** `YYYY-MM-DD` of a UTC midnight. */
function isoDay(day: Date): string {
    return `${day.getUTCFullYear()}-${String(day.getUTCMonth() + 1).padStart(2, '0')}-${String(day.getUTCDate()).padStart(2, '0')}`;
}

/** The days of [start, end] that none of `ranges` covers, bounds inclusive. */
function daysNotCovered(ranges: ReadonlyArray<DateRange | undefined>, start: string, end: string): string[] {
    const missing: string[] = [];
    for (const day = new Date(`${start}T00:00:00Z`); day <= new Date(`${end}T00:00:00Z`); day.setUTCDate(day.getUTCDate() + 1)) {
        const iso = isoDay(day);
        if (!ranges.some((range) => range !== undefined && range.start <= iso && iso <= range.end)) missing.push(iso);
    }
    return missing;
}

/**
 * A catch-up that updated something, run and ended on the Dashboard. The header goes on every API answer from before the
 * sidebar is clicked, but the tracker hears it only on an answer, and the Dashboard may ask nothing when it opens: its
 * report cached and fresh — after the FX page of (h), which writes nothing, it is. So the trigger is explicit, the
 * Dashboard's Refresh, pressed as on the control's round trip: it asks the main report with force, and that answer,
 * carrying the header, starts the tracker. Checked before the notice is awaited — a main report sent after the click,
 * so after the header was set, is back —, so that a red names the cause. Then the end, awaited as in (a), and the reload
 * in background it causes there (Z-13), up to the Dashboard at rest: nothing of it is in flight when the case goes back.
 */
async function catchUpEndsOnDashboard(page: Page, catchUp: CatchUp): Promise<void> {
    const since = (await pageRecord(page)).seq;
    catchUp.header = 'running';
    catchUp.status = running();
    await leaveForDashboard(page);
    await refreshDashboard(page, 'premise: no API answer after the header was set: nothing could start the tracker — the Refresh on the Dashboard asked no main report, or its answer never came back');
    await endRunningCatchUp(page, catchUp, since, true);
    await dashboardSettled(page);
}

// Z-14b + Z-15: the views already on screen reload by themselves after a catch-up, in silence.

/** The catch-up the next document will see: a job running, the header on every answer. Set before the page loads. */
function armRunning(catchUp: CatchUp): void {
    catchUp.header = 'running';
    catchUp.status = running();
}

/** The queries of `path` sent after `since`. */
function queriesSince(record: PageRecord, path: string, since: number): QueryEntry[] {
    return record.queries.filter((query) => query.seq > since && query.path === path);
}

/** Waits until every query the page has sent is back: nothing of the case is left in flight. */
async function queriesBack(page: Page): Promise<void> {
    await expect.poll(async () => (await pageRecord(page)).queries.every((query) => query.settled !== null), {message: 'a price, rate, risk or lots question the page sent never came back', timeout: PAGE_TIMEOUT}).toBe(true);
}

/** The questions (risk, lots) of a path sent up to `until`, as keys: the questions the page had asked when the catch-up ended. */
function questionsUntil(record: PageRecord, path: string, until: number): Set<string> {
    return new Set(record.queries.filter((query) => query.seq <= until && query.path === path && query.body !== null && typeof query.body === 'object' && !Array.isArray(query.body)).map((query) => canonical(query.body as object)));
}

/** The items of a `prices/query` entry, whoever they ask about. */
function priceItems(entry: QueryEntry): PriceQueryItem[] {
    if (!Array.isArray(entry.body)) return [];
    return (entry.body as Array<PriceQueryItem | null>).filter((item): item is PriceQueryItem => item !== null && typeof item === 'object');
}

/** The Dashboard at rest, and nothing the page asked still in flight. */
async function dashboardAtRest(page: Page): Promise<void> {
    await dashboardSettled(page);
    await queriesBack(page);
}

/** What a view must not do while it reloads in background (Z-15). */
interface Silence {
    /** The flags of BUSY_TEST_IDS the view must never raise, and must not be put on screen again for. */
    busy: readonly BusyTestId[];
    /** The skeletons (`*-loading` test ids) that must not appear; any `*-refreshing` icon is excluded as well. */
    skeletons?: readonly string[];
    /** The figures of KEPT_TEST_IDS that must stay on screen. */
    kept?: readonly (typeof KEPT_TEST_IDS)[number][];
}

/**
 * The silence of a reload in background, read on the whole record from `mark` — the moment the page read the idle answer —
 * to now. The premise comes first and is hard: each flag was seen on screen and idle at the mark (a flag already up needs
 * no change to stay up, and its silence would prove nothing). The rest is soft, so that a red lists everything the page
 * said: a flag raised, an element put on screen again (a navigation, a remount), a skeleton or a spinning icon shown, a
 * figure taken off the screen.
 */
function expectSilent(record: PageRecord, mark: number, silence: Silence): void {
    for (const testId of silence.busy) {
        expect(busyAt(record, testId, mark), `premise: when the catch-up ended the record had not seen ${testId} put on screen, or saw it busy — a flag already up needs no change to stay up, and its silence would prove nothing`).toBe('false');
    }
    for (const testId of silence.busy) {
        expect.soft(busyRaised(record, testId, mark), `${testId} said busy while the view reloaded after a price catch-up: the reload is the page's own, not a load the user asked for, and a screen reader would announce «busy» for it (Z-15)`).toEqual([]);
        expect
            .soft(
                record.busy.filter((entry) => entry.testId === testId && entry.kind === 'mount' && entry.seq > mark),
                `${testId} was put on screen again after the catch-up: the view was remounted or navigated, not reloaded in place (Z-15)`,
            )
            .toEqual([]);
    }
    const skeletons = silence.skeletons ?? [];
    expect
        .soft(
            record.appeared.filter((shown) => shown.seq > mark && (shown.testId.endsWith('-refreshing') || skeletons.includes(shown.testId))).map((shown) => shown.testId),
            'a skeleton or a spinning icon was shown for the reload in background: the old figures must stay, in silence (Z-15)',
        )
        .toEqual([]);
    expect
        .soft(
            record.removed.filter((gone) => gone.seq > mark && (silence.kept ?? []).includes(gone.testId as (typeof KEPT_TEST_IDS)[number])).map((gone) => gone.testId),
            'the figures on screen were taken away for the reload in background: they must stay until the new ones land (Z-15)',
        )
        .toEqual([]);
}

/** A view the cases of Z-15 reload after a catch-up: how to open it, what a reload of it asks, what it must not say. */
interface ReloadView {
    /** What the view is, for the messages. */
    what: string;
    /** Opens the view with a full load and returns once it is at rest: its first load in, every question back, its flags idle. */
    open: () => Promise<void>;
    /** The view at rest again, after a reload. */
    settled: () => Promise<void>;
    /** What a reload of this view asks, among the questions sent after `since`. */
    asked: (record: PageRecord, since: number) => QueryEntry[];
    /** Further checks on the reload that was asked, once it has landed. */
    check?: (context: {page: Page; record: PageRecord; mark: number; asked: QueryEntry[]}) => Promise<void> | void;
    silence: Silence;
}

/**
 * The two halves of every case of Z-15, each on its own document and its own catch-up:
 *   - the control: the catch-up runs and ends having updated nothing (`last_refreshed` false) — the view asks nothing;
 *   - the case: the catch-up ends having updated something — the view asks again by itself, within a few polls, without
 *     navigation, and through the reload it never says busy, shows no skeleton or spinning icon and keeps its figures.
 * The absence of the control is read at the page's reading of the idle answer, one task after it (the reaction of a view
 * is a microtask) and then once the view is at rest again; the case after it is what keeps it from being vacuous.
 */
async function viewReloadsInSilence(page: Page, catchUp: CatchUp, view: ReloadView): Promise<void> {
    await test.step(`control: ${view.what}, a catch-up that updated nothing asks nothing`, async () => {
        armRunning(catchUp);
        await view.open();
        const {mark} = await endRunningCatchUp(page, catchUp, 0, false);
        await view.settled();
        expect(
            view.asked(await pageRecord(page), mark).map((entry) => entry.path),
            `a catch-up that updated nothing made ${view.what} ask again`,
        ).toEqual([]);
    });

    await test.step(`${view.what}: a catch-up that updated something is over, the view asks again by itself, in silence`, async () => {
        armRunning(catchUp);
        await view.open();
        const url = page.url();
        const origin = await documentOrigin(page);
        const {mark} = await endRunningCatchUp(page, catchUp, 0, true);

        await expect
            .poll(async () => view.asked(await pageRecord(page), mark).length, {
                message: `the catch-up updated the prices and ${view.what} did not ask for what it shows again: the open view keeps the figures of before until the user navigates (Z-15)`,
                timeout: POLL_BUDGET_MS,
            })
            .toBeGreaterThan(0);
        await queriesBack(page);
        await view.settled();

        const record = await pageRecord(page);
        const asked = view.asked(record, mark);
        expect(page.url(), 'the reload came with a navigation').toBe(url);
        expect(await documentOrigin(page), 'the reload was a document load').toBe(origin);
        await view.check?.({page, record, mark, asked});
        expectSilent(record, mark, view.silence);
    });
}

/**
 * The control of a silence on a page whose Refresh the case does not watch for the reload: press the button, and the record
 * must see it say busy and let go. A record that missed it would be blind, and the silence of the case worthless there.
 */
async function buttonSaysBusy(page: Page, testId: BusyTestId): Promise<void> {
    const button = page.getByTestId(testId);
    const before = (await pageRecord(page)).seq;
    await expect(button, 'the Refresh button cannot be pressed: a load of the page is still pending').toBeEnabled({timeout: PAGE_TIMEOUT});
    await button.click();
    let clicked = -1;
    await expect
        .poll(
            async () => {
                clicked = (await pageRecord(page)).clicks.find((click) => click.seq > before && click.testId === testId)?.seq ?? -1;
                return clicked;
            },
            {message: 'the click on the Refresh button never reached the page', timeout: POLL_BUDGET_MS},
        )
        .toBeGreaterThan(before);
    await expect
        .poll(async () => busyRaised(await pageRecord(page), testId, clicked).length, {
            message: `the control: the user asked for a Refresh and the record never saw ${testId} say busy — the record is blind to it, or the page no longer says busy for a load the user asked for; either way its silence proves nothing`,
            timeout: PAGE_TIMEOUT,
        })
        .toBeGreaterThan(0);
    await expect(button, 'the control: the Refresh never let go of its button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
}

/** Requests the case holds in flight, and owns until it lets them through. */
interface QueryGate {
    /** How many are held still. */
    pending: () => number;
    /** Lets every held request through, on to the page's other routes (the catch-up stub) as if it had never been held. */
    release: () => Promise<void>;
    /** `release()`, then the route goes: for `finally`. Safe to call twice. */
    dispose: () => Promise<void>;
}

/**
 * Holds, from now until `release()`, the `POST path` requests whose body `picks` chooses; every other request goes through.
 * Registered after the catch-up stub, so it sees a request first and a released one goes on to the stub (`fallback()`).
 */
async function holdQuery(page: Page, path: string, picks: (body: unknown) => boolean): Promise<QueryGate> {
    const waiting: Route[] = [];
    let open = false;
    let routed = true;
    const matches = (url: URL): boolean => url.pathname === path;
    const handler = async (route: Route): Promise<void> => {
        let body: unknown = null;
        try {
            body = route.request().postDataJSON();
        } catch {
            body = null;
        }
        if (open || route.request().method() !== 'POST' || !picks(body)) {
            await route.fallback();
            return;
        }
        waiting.push(route);
    };
    await page.route(matches, handler);
    const release = async (): Promise<void> => {
        open = true;
        await Promise.all(waiting.splice(0).map((route) => route.fallback().catch(() => undefined)));
    };
    return {
        pending: () => waiting.length,
        release,
        dispose: async () => {
            await release();
            if (!routed) return;
            routed = false;
            await page.unroute(matches, handler).catch(() => undefined);
        },
    };
}

/**
 * The part of (g') and (h') after the return: the request for the prices or rates is HELD in flight, and the page's root
 * must read `data-busy="false"` while it is — proof that the stale points are on screen and that the request in background
 * does not keep the page busy. Released, the request lands; from the first `false` on the root never goes back to `true`.
 * The root is allowed to say busy before that first `false`: the page decides its cache at the return (`loading`).
 */
async function staleThenSilent(page: Page, gate: QueryGate, root: Locator, rootId: 'asset-detail-page' | 'fx-detail-page', chart: Locator, landed: () => Promise<unknown>, mark: number): Promise<void> {
    await expect.poll(() => gate.pending(), {message: 'back on the page after the catch-up, it never sent the request for its prices or rates (Z-14), or the gate did not hold it', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);
    await expect(root, 'with the request held in flight the root still says busy: the stale points are not on screen yet, or the request in background keeps the page busy (Z-15, D3)').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
    await expect(chart, 'the stale points are not on screen while the request is held').toBeVisible();
    expect(gate.pending(), 'the request was not in flight when the root read false').toBeGreaterThan(0);
    const record = await pageRecord(page);
    const firstFalse = record.busy.find((entry) => entry.testId === rootId && entry.seq > mark && entry.value === 'false')?.seq;
    expect(firstFalse, `premise: the record never saw ${rootId} read false after the return — it is blind to its flag`).toBeDefined();

    await gate.release();
    await landed();
    await waitForSettled(root, PAGE_TIMEOUT);
    const after = await pageRecord(page);
    expect(busyRaised(after, rootId, firstFalse!), `${rootId} went back to busy after the stale points were on screen: the request in background must not raise the flag again (Z-15, D3)`).toEqual([]);
}

// The views.

/** The Dashboard's risk tab, loaded: the panel's catalogue in, its first load over, its first level's cards on screen. */
function dashboardRiskView(page: Page): ReloadView {
    return {
        what: "the Dashboard's risk panel",
        open: async () => {
            await navigateTo(page, '/dashboard?tab=rischio');
            await expect(dashboard(page)).toBeVisible({timeout: PAGE_TIMEOUT});
            const panel = page.getByTestId('risk-levels-panel');
            await expect(panel).toHaveAttribute('data-catalog', 'ready', {timeout: PAGE_TIMEOUT});
            await expect(panel).toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
            await expect(panel.getByTestId('risk-l1-cards'), 'precondition: the risk panel shows no figures: nothing is cached for a catch-up to turn stale').toBeVisible({timeout: PAGE_TIMEOUT});
            await dashboardAtRest(page);
            expect(queriesSince(await pageRecord(page), RISK_QUERY_PATH, 0).length, 'precondition: the risk panel asked no question in this document').toBeGreaterThan(0);
        },
        settled: () => dashboardAtRest(page),
        asked: (record, since) => queriesSince(record, RISK_QUERY_PATH, since),
        check: ({record, mark, asked}) => {
            const known = questionsUntil(record, RISK_QUERY_PATH, mark);
            expect(known.size, 'premise: the panel had asked no question before the catch-up ended').toBeGreaterThan(0);
            const fresh = asked.map((entry) => canonical(entry.body as object)).filter((question) => !known.has(question));
            expect(fresh, 'the reload asked a question the panel had not asked before: it must ask the same ones, with no navigation (Z-15)').toEqual([]);
        },
        silence: {busy: ['dashboard-page', 'sync-button', 'risk-levels-panel'], skeletons: ['risk-l1-loading', 'risk-l2-loading', 'risk-l3-loading'], kept: ['risk-l1-cards']},
    };
}

/** The lots analysis panel of the Dashboard, open on `assetId` through the URL as a link to it opens it, loaded with its lots on screen. */
function dashboardLotsView(page: Page, assetId: number): ReloadView {
    const ofAsset = (record: PageRecord, since: number): QueryEntry[] => queriesSince(record, LOTS_PATH, since).filter((entry) => (entry.body as {asset_id?: unknown} | null)?.asset_id === assetId);
    return {
        what: `the lots analysis panel of asset ${assetId}`,
        open: async () => {
            await navigateTo(page, `/dashboard?tab=posizioni&asset=${assetId}`);
            await expect(dashboard(page)).toBeVisible({timeout: PAGE_TIMEOUT});
            const panel = page.getByTestId('lots-analysis-panel');
            await expect(panel).toBeVisible({timeout: PAGE_TIMEOUT});
            await expect(panel.getByTestId('lots-analysis-panel-loading')).toHaveCount(0, {timeout: PAGE_TIMEOUT});
            await expect(panel.getByTestId('unified-lots-table'), 'precondition: the lots panel shows no lots: nothing is cached for a catch-up to turn stale').toBeVisible({timeout: PAGE_TIMEOUT});
            await dashboardAtRest(page);
            expect(ofAsset(await pageRecord(page), 0).length, `precondition: the lots panel asked no analysis of asset ${assetId} in this document`).toBeGreaterThan(0);
        },
        settled: () => dashboardAtRest(page),
        asked: ofAsset,
        check: ({record, mark, asked}) => {
            const known = questionsUntil(record, LOTS_PATH, mark);
            const fresh = asked.map((entry) => canonical(entry.body as object)).filter((question) => !known.has(question));
            expect(fresh, 'the reload asked a lots question the panel had not asked before: it must ask the same ones, with no navigation (Z-15)').toEqual([]);
        },
        silence: {busy: ['dashboard-page', 'sync-button'], skeletons: ['lots-analysis-panel-loading'], kept: ['unified-lots-table']},
    };
}

/** The asset detail with a range ending today, loaded: its prices in the cache, its chart drawn, its live poll answered by the stub. */
function assetDetailView(page: Page, assetId: number, range: DateRange): ReloadView {
    const ofAsset = (record: PageRecord, since: number): QueryEntry[] => queriesSince(record, PRICES_QUERY_PATH, since).filter((entry) => assetItems(entry, assetId).length > 0);
    return {
        what: `the detail page of asset ${assetId}`,
        open: async () => {
            await navigateTo(page, `/assets/${assetId}?start=${range.start}&end=${range.end}`);
            const root = assetDetail(page);
            await expect(root).toBeVisible({timeout: PAGE_TIMEOUT});
            const first = await assetQueryLanded(page, assetId, 0, `the page of asset ${assetId} never asked for its prices, or the answer never came back`);
            await waitForSettled(root, PAGE_TIMEOUT);
            await expect(page.getByTestId('asset-detail-refresh-btn'), 'the load of the asset page never let go of its Refresh button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
            await expect(root.getByTestId('asset-detail-chart'), `the chart of asset ${assetId} shows no series: nothing is cached for a catch-up to turn stale`).toHaveAttribute('data-series-state', 'ready', {timeout: PAGE_TIMEOUT});
            expect(pricesOf(first.entry, assetId), `premise: the first answer carried no price of asset ${assetId}, so nothing was cached — check populate_mock_data.populate_price_history`).toBeGreaterThan(0);
            await queriesBack(page);
        },
        settled: async () => {
            await waitForSettled(assetDetail(page), PAGE_TIMEOUT);
            await queriesBack(page);
        },
        asked: ofAsset,
        check: async ({page: current, asked}) => {
            const items = asked.flatMap((entry) => assetItems(entry, assetId));
            expect(
                items.map((item) => item.include_price),
                'the reload must ask the prices again (include_price true): an item without them leaves the days the catch-up filled as they were (Z-15)',
            ).toContain(true);
            expect(
                items.map((item) => item.date_range),
                'the reload must ask the range on screen',
            ).toContainEqual(range);
            await expect(current.getByTestId('asset-detail-chart'), 'the chart is gone after the reload').toBeVisible();
            await expect(assetDetail(current).getByTestId('asset-detail-chart')).toHaveAttribute('data-series-state', 'ready');
        },
        silence: {busy: ['asset-detail-page', 'asset-detail-refresh-btn'], kept: ['asset-detail-chart']},
    };
}

/** The FX detail of `pair` with a range ending today, loaded: its rates in the cache. */
function fxDetailView(page: Page, pair: Pair, range: DateRange): ReloadView {
    return {
        what: `the detail page of ${pair.slug}`,
        open: async () => {
            await navigateTo(page, `/fx/${pair.slug}?start=${range.start}&end=${range.end}`);
            await expect(fxDetail(page)).toBeVisible({timeout: PAGE_TIMEOUT});
            const first = await pairConvertLanded(page, pair, 0, `the page of ${pair.slug} never asked for its rates, or the answer never came back`);
            await fxDetailSettled(page, pair);
            expect(first.answer?.results ?? 0, `premise: the first answer carried no rate of ${pair.slug}, so nothing was cached — check populate_mock_data.populate_fx_rates`).toBeGreaterThan(0);
            await queriesBack(page);
        },
        settled: async () => {
            await fxDetailSettled(page, pair);
            await queriesBack(page);
        },
        asked: (record, since) => pairConvertsSince(record, pair, since),
        check: async ({page: current, asked}) => {
            const ranges = asked.flatMap((entry) => pairItems(entry, pair).map((item) => item.date_range));
            expect(daysNotCovered(ranges, range.start, range.end), 'the rates asked again after the catch-up must cover the whole range on screen: every day of it was loaded before (Z-15)').toEqual([]);
            await expect(current.getByTestId('fx-detail-chart'), 'the chart is gone after the reload').toBeVisible();
        },
        silence: {busy: ['fx-detail-page', 'fx-detail-refresh-btn'], kept: ['fx-detail-chart']},
    };
}

/** The assets list, loaded: its rows and the prices of its cards in, its flags idle. */
function assetsListView(page: Page): ReloadView {
    return {
        what: 'the assets list',
        open: async () => {
            await navigateTo(page, '/assets');
            const root = page.getByTestId('assets-page');
            await expect(root).toBeVisible({timeout: PAGE_TIMEOUT});
            await waitForSettled(root, PAGE_TIMEOUT);
            await expect(page.getByTestId('assets-refresh-button'), 'the load of the assets list never let go of its Refresh button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
            expect(queriesSince(await pageRecord(page), PRICES_QUERY_PATH, 0).length, 'precondition: the assets list asked no prices in this document: nothing is cached for a catch-up to turn stale').toBeGreaterThan(0);
            await queriesBack(page);
        },
        settled: async () => {
            await waitForSettled(page.getByTestId('assets-page'), PAGE_TIMEOUT);
            await queriesBack(page);
        },
        asked: (record, since) => queriesSince(record, PRICES_QUERY_PATH, since),
        check: ({asked}) => {
            expect(
                asked.flatMap(priceItems).map((item) => item.include_price),
                'the reload of the list asked no prices (include_price true): the cards keep the figures of before the catch-up (Z-15)',
            ).toContain(true);
        },
        silence: {busy: ['assets-page', 'assets-refresh-button']},
    };
}

/** The FX list, loaded: its cards' rates in, its flags idle. */
function fxListView(page: Page): ReloadView {
    return {
        what: 'the FX list',
        open: async () => {
            await navigateTo(page, '/fx');
            const root = page.getByTestId('fx-page');
            await expect(root).toBeVisible({timeout: PAGE_TIMEOUT});
            await waitForSettled(root, PAGE_TIMEOUT);
            await expect(page.getByTestId('fx-refresh-all-button'), 'the load of the FX list never let go of its Refresh button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
            expect(queriesSince(await pageRecord(page), CONVERT_PATH, 0).length, 'precondition: the FX list asked no rates in this document: nothing is cached for a catch-up to turn stale').toBeGreaterThan(0);
            await queriesBack(page);
        },
        settled: async () => {
            await waitForSettled(page.getByTestId('fx-page'), PAGE_TIMEOUT);
            await queriesBack(page);
        },
        asked: (record, since) => queriesSince(record, CONVERT_PATH, since),
        silence: {busy: ['fx-page', 'fx-refresh-all-button']},
    };
}

/** The brokers TEST_USER owns, as the Dashboard counts them (`getOwnedBrokers`): OWNER with a share unset or above zero. */
async function ownedBrokerIds(page: Page): Promise<number[]> {
    const response = await page.request.get(`${API}/brokers`);
    expect(response.ok(), `GET ${API}/brokers → HTTP ${response.status()}`).toBe(true);
    const items = ((await response.json()) as {items?: Array<{id: number; user_role?: string | null; user_share_percentage?: string | number | null}>}).items ?? [];
    return items.filter((broker) => broker.user_role === 'OWNER' && (broker.user_share_percentage == null || Number(broker.user_share_percentage) > 0)).map((broker) => broker.id);
}

/**
 * An asset the Dashboard's Performance table lists on a broker TEST_USER owns, found the way a user would see it: the view
 * saved through the panel's toggles, then the rows (`pos-{brokerId}-{assetId}`). Both are checked, neither inferred.
 */
async function ownedPositionAssetId(page: Page): Promise<number> {
    const owned = await ownedBrokerIds(page);
    await saveDashboardPerformanceView(page);
    const rows = page.getByTestId('contribution-table').locator('tbody tr[data-row-id^="pos-"]');
    await expect(rows, 'the Performance table lists no position: check populate_mock_data.py').not.toHaveCount(0, {timeout: PAGE_TIMEOUT});
    const rowIds = await rows.evaluateAll((elements) => elements.map((element) => element.getAttribute('data-row-id') ?? ''));
    for (const rowId of rowIds) {
        const match = /^pos-(\d+)-(\d+)$/.exec(rowId);
        if (match && owned.includes(Number(match[1]))) return Number(match[2]);
    }
    throw new Error(`No Performance row on a broker ${TEST_USER.username} owns (owned: ${owned.join(', ') || 'none'}; rows: ${rowIds.join(', ')}) — check populate_mock_data.py`);
}

test.beforeEach(async ({page}, testInfo) => {
    test.skip(testInfo.project.name !== 'desktop', 'Desktop only: the tracker and the reload do not depend on the viewport');
    test.setTimeout(90_000);
    // Before the route: the sign-in's answer is the one that sets the session cookie, and it passes untouched.
    await login(page, TEST_USER);
    await recordPage(page);
});

test.describe('An open page catches up after the server did (Z5, Z-13)', () => {
    test('(a) Dashboard: when a catch-up that updated something is over, the notice goes and the main report is asked again, with no navigation', async ({page}) => {
        const catchUp = await simulateCatchUp(page, {header: 'running', status: running()});
        await navigateTo(page, '/dashboard');
        await expect(dashboard(page)).toBeVisible({timeout: PAGE_TIMEOUT});
        await waitForSettled(dashboard(page), PAGE_TIMEOUT);
        const shown = await mainReportLanded(page, 'the Dashboard never sent its main report, or it never came back');
        const url = page.url();

        const {mark, idleRead} = await endRunningCatchUp(page, catchUp, 0, true);

        await expect
            .poll(async () => mainReportsSince(await pageRecord(page), mark).length, {
                message: 'the catch-up updated the prices and the Dashboard did not ask for its report again: the open page keeps the figures of before until it is reloaded (Z-13)',
                timeout: POLL_BUDGET_MS,
            })
            .toBeGreaterThan(0);
        const record = await pageRecord(page);
        const reloads = record.reports.filter((report) => report.seq > mark && isMainReport(report.body));
        expect(
            reloads.map((report) => canonical(report.body as ReportBody)),
            'the reload must ask the question on screen — the same scope, period, currency and options — once',
        ).toEqual([canonical(shown.body)]);
        expect(reloads[0].seq, 'the reload left after the page read the idle answer: it was not caused by it').toBeLessThan(idleRead);
        expect(
            record.reports.some((report) => report.seq === shown.seq),
            'the record of the first load is gone: the page was reloaded, not refreshed in place',
        ).toBe(true);
        expect(page.url(), 'the reload came with a navigation').toBe(url);
        await reportsSettled(page);
        await waitForSettled(dashboard(page), PAGE_TIMEOUT);
    });

    test('(b) broker page: when a catch-up that updated something is over, the notice goes and the overview report is asked again, with no navigation', async ({page}) => {
        const brokerId = await brokerIdByName(page, BROKER_WITH_HOLDINGS);
        const catchUp = await simulateCatchUp(page, {header: 'running', status: running()});
        await navigateTo(page, `/brokers/${brokerId}`);
        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: PAGE_TIMEOUT});
        await expect(page.getByTestId('broker-name')).toBeVisible({timeout: PAGE_TIMEOUT});
        // This page publishes no data-busy: its overview report sent and back is the barrier.
        const isThisBroker = (body: ReportBody): boolean => canonical({broker_ids: body.broker_ids ?? []}) === canonical({broker_ids: [brokerId]});
        const shown = await mainReportLanded(page, `the page of broker ${brokerId} never sent its overview report, or it never came back`, isThisBroker);
        const url = page.url();

        const {mark, idleRead} = await endRunningCatchUp(page, catchUp, 0, true);

        await expect
            .poll(async () => mainReportsSince(await pageRecord(page), mark).length, {
                message: 'the catch-up updated the prices and the broker page did not ask for its overview again: it keeps the figures of before until it is reloaded (Z-13)',
                timeout: POLL_BUDGET_MS,
            })
            .toBeGreaterThan(0);
        const record = await pageRecord(page);
        const reloads = record.reports.filter((report) => report.seq > mark && isMainReport(report.body));
        expect(
            reloads.map((report) => canonical(report.body as ReportBody)),
            'the reload must ask the overview on screen — this broker only, the same period, currency and options — once',
        ).toEqual([canonical(shown.body)]);
        expect(reloads[0].seq, 'the reload left after the page read the idle answer: it was not caused by it').toBeLessThan(idleRead);
        expect(
            record.reports.some((report) => report.seq === shown.seq),
            'the record of the first load is gone: the page was reloaded, not refreshed in place',
        ).toBe(true);
        expect(page.url(), 'the reload came with a navigation').toBe(url);
        await reportsSettled(page);
    });

    test('(c) Dashboard: no job seen, or nothing updated — no reload; the notice only while a job runs; then a catch-up that did update reloads it once', async ({page}) => {
        test.setTimeout(150_000);
        const catchUp = await simulateCatchUp(page, {header: 'starting', status: starting()});
        await navigateTo(page, '/dashboard');
        await expect(dashboard(page)).toBeVisible({timeout: PAGE_TIMEOUT});
        await waitForSettled(dashboard(page), PAGE_TIMEOUT);
        const shown = await mainReportLanded(page, 'the Dashboard never sent its main report, or it never came back');

        // 1. `starting` → `idle`: this page never saw the job run. Even `last_refreshed` true does not reload it.
        const windowStart = await test.step('starting → idle, no job seen: no notice at any moment, no reload', async () => {
            await statusRead(page, 0, 'starting', 'the tracker never read a starting answer: it did not start on the header, or it does not ask the status route');
            const mark = (await pageRecord(page)).seq;
            catchUp.header = null;
            catchUp.status = idle(true);
            await statusRead(page, mark, 'idle', 'the page never read the idle answer');
            const record = await pageRecord(page);
            expect(mainReportsSince(record, mark), 'a catch-up whose job this page never saw run reloaded the Dashboard').toEqual([]);
            expect(record.noticeShown, 'the notice was put on screen during a catch-up that only ever said starting').toEqual([]);
            await expect(notice(page)).toHaveCount(0);
            return mark;
        });

        // 2. `running` → `idle` with `last_refreshed` false: the catch-up updated nothing.
        await test.step('running → idle, nothing updated: the notice comes and goes, no reload', async () => {
            const since = (await pageRecord(page)).seq;
            catchUp.header = 'running';
            catchUp.status = running();
            // The Dashboard is quiet once loaded: the round trip makes the API answers that carry the header.
            await roundTripThroughTransactions(page);
            const {mark} = await endRunningCatchUp(page, catchUp, since, false);
            expect(mainReportsSince(await pageRecord(page), mark), 'a catch-up that updated nothing reloaded the Dashboard').toEqual([]);
        });

        // 3. The control, in the same page: the reload exists, and the window above saw none.
        await test.step('control: running → idle, something updated: exactly one reload, and none since the first idle', async () => {
            const since = (await pageRecord(page)).seq;
            catchUp.header = 'running';
            catchUp.status = running();
            await roundTripThroughTransactions(page);
            const {mark} = await endRunningCatchUp(page, catchUp, since, true);

            await expect
                .poll(async () => mainReportsSince(await pageRecord(page), mark).length, {
                    message: 'the control: a catch-up that updated the prices did not reload the Dashboard, so the two absences above prove nothing (Z-13)',
                    timeout: POLL_BUDGET_MS,
                })
                .toBeGreaterThan(0);
            const record = await pageRecord(page);
            const reloads = record.reports.filter((report) => report.seq > mark && isMainReport(report.body));
            expect(
                reloads.map((report) => canonical(report.body as ReportBody)),
                'the control reload must ask the question on screen, once',
            ).toEqual([canonical(shown.body)]);
            const quiet = record.reports.filter((report) => report.seq > windowStart && report.seq <= mark && isMainReport(report.body));
            expect(
                quiet.map((report) => report.seq),
                'a main report was sent between the first idle and the control: one of the catch-ups that must not reload did, late, or a return to the Dashboard asked a report that was still fresh',
            ).toEqual([]);
            expect(record.noticeShown.length, 'the notice came once for each of the two running catch-ups, and never for the starting one').toBe(2);
        });

        await reportsSettled(page);
        await waitForSettled(dashboard(page), PAGE_TIMEOUT);
        expect(catchUp.served.length, 'premise: the status route was answered by the stub').toBeGreaterThan(0);
    });
});

test.describe('The reload in background is not a load the user asked for (Z-18, Y11)', () => {
    test('(d) Dashboard: through the reload in background neither the page nor its Refresh button says busy, while a Refresh the user asks for says it on both', async ({page}) => {
        const catchUp = await simulateCatchUp(page, {header: 'running', status: running()});
        await navigateTo(page, '/dashboard');
        await expect(dashboard(page)).toBeVisible({timeout: PAGE_TIMEOUT});
        const settled = (): Promise<void> => waitForSettled(dashboard(page), PAGE_TIMEOUT);
        await settled();
        await mainReportLanded(page, 'the Dashboard never sent its main report, or it never came back');
        // The first load holds the button (Y11): the window opens once it has let go, so that a spin in it is a change.
        await expect(page.getByTestId('sync-button'), 'the first load never let go of the Refresh button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});

        const mark = await backgroundReloadLanded(page, catchUp, settled);
        const clicked = await test.step('control: a Refresh the user asks for says busy on the page and on its button', () => userRefreshSaysBusy(page, 'sync-button', ['dashboard-page', 'sync-button'], settled));

        // The window — from before the stub said idle to the control's click, the whole reload in it — read whole now and
        // asserted last: the control above ran whatever it holds. The root's silence last of all: the one red before Z-18.
        const record = await pageRecord(page);
        for (const testId of ['dashboard-page', 'sync-button'] as const) {
            expect(busyAt(record, testId, mark), `premise: when the catch-up ended the record had not seen ${testId} put on screen, or saw it busy — a flag already up needs no change to stay up, and its silence would prove nothing`).toBe('false');
        }
        expect(busyRaised(record, 'sync-button', mark, clicked), 'the Refresh button spun for the reload in background after a price catch-up: it waits for the loads the user asks for, and this one is not (Y11, P3)').toEqual([]);
        expect(busyRaised(record, 'dashboard-page', mark, clicked), 'the Dashboard said it was busy through the reload in background after a price catch-up: a screen reader announces «busy» for a price refresh nobody asked for (Z-18)').toEqual([]);
    });

    test('(e) broker page: the reload in background does not spin the Refresh button, while a Refresh the user asks for does', async ({page}) => {
        const brokerId = await brokerIdByName(page, BROKER_WITH_HOLDINGS);
        const catchUp = await simulateCatchUp(page, {header: 'running', status: running()});
        await navigateTo(page, `/brokers/${brokerId}`);
        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: PAGE_TIMEOUT});
        await expect(page.getByTestId('broker-name')).toBeVisible({timeout: PAGE_TIMEOUT});
        const isThisBroker = (body: ReportBody): boolean => canonical({broker_ids: body.broker_ids ?? []}) === canonical({broker_ids: [brokerId]});
        await mainReportLanded(page, `the page of broker ${brokerId} never sent its overview report, or it never came back`, isThisBroker);
        // The first load holds the button (Y11): the window opens once it has let go, so that a spin in it is a change.
        await expect(page.getByTestId('broker-refresh'), 'the first load never let go of the Refresh button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
        // This page publishes no data-busy on its root: every report back is the landing.
        const settled = (): Promise<void> => Promise.resolve();

        const mark = await backgroundReloadLanded(page, catchUp, settled);
        const clicked = await test.step('control: a Refresh the user asks for spins the button', () => userRefreshSaysBusy(page, 'broker-refresh', ['broker-refresh'], settled));

        // The window, read whole now and asserted last: the control above ran whatever it holds.
        const record = await pageRecord(page);
        expect(busyAt(record, 'broker-refresh', mark), 'premise: when the catch-up ended the record had not seen broker-refresh put on screen, or saw it busy — a flag already up needs no change to stay up, and its silence would prove nothing').toBe('false');
        expect(busyRaised(record, 'broker-refresh', mark, clicked), "the broker page's Refresh button spun for the reload in background after a price catch-up: it waits for the loads the user asks for, and this one is not (Y11, P3)").toEqual([]);
    });

    test('(f) Dashboard on the Positions tab with the Performance view: through the reload in background neither the page nor its Refresh button says busy, while the contribution is asked again', async ({page}) => {
        // Two page loads: the visit that saves the view, and the page under test.
        test.setTimeout(120_000);
        // Saved before the stub, the way a user saves it: the page under test opens on the view and asks its contribution
        // at load, and that cached contribution is what the catch-up turns stale.
        await saveDashboardPerformanceView(page);
        const catchUp = await simulateCatchUp(page, {header: 'running', status: running()});
        await navigateTo(page, '/dashboard?tab=posizioni');
        await expect(dashboard(page)).toBeVisible({timeout: PAGE_TIMEOUT});
        const settled = (): Promise<void> => waitForSettled(dashboard(page), PAGE_TIMEOUT);
        const panel = page.getByTestId('positions-panel');
        await expect(panel.getByTestId('positions-toggle-performance'), 'precondition: the Positions tab did not open on the saved Performance view').toHaveAttribute('aria-pressed', 'true', {timeout: PAGE_TIMEOUT});
        await expect(panel.getByTestId('contribution-table'), 'precondition: the saved Performance view never showed its contribution').toBeVisible({timeout: PAGE_TIMEOUT});
        await settled();
        await mainReportLanded(page, 'the Dashboard never sent its main report, or it never came back');
        expect(contributionsSince(await pageRecord(page), 0).length, 'precondition: the Performance view on screen asked no contribution in this document, so none is cached for the catch-up to turn stale').toBeGreaterThan(0);
        // The first load holds the button (Y11), the contribution it joins included: the window opens once it has let go.
        await expect(page.getByTestId('sync-button'), 'the first load never let go of the Refresh button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});

        // The catch-up ends having updated something. The reload asks the main report and — the cached contribution being
        // stale — the contribution: both told by their bodies, and both back before the control.
        const {mark} = await endRunningCatchUp(page, catchUp, 0, true);
        await expect
            .poll(
                async () => {
                    const record = await pageRecord(page);
                    return {main: mainReportsSince(record, mark).length > 0, contribution: contributionsSince(record, mark).length > 0};
                },
                {message: 'the reload in background did not ask both the main report and the contribution of the Performance view on screen: there is no contribution refresh to watch (Z-13)', timeout: POLL_BUDGET_MS},
            )
            .toEqual({main: true, contribution: true});
        await reportsSettled(page);
        await settled();
        const clicked = await test.step('control: a Refresh the user asks for says busy on the page and on its button', () => userRefreshSaysBusy(page, 'sync-button', ['dashboard-page', 'sync-button'], settled));

        // The window — from before the stub said idle to the control's click, the report and the contribution in it — read
        // whole now and asserted last: the control above ran whatever it holds. The root's silence last of all: the red.
        const record = await pageRecord(page);
        for (const testId of ['dashboard-page', 'sync-button'] as const) {
            expect(busyAt(record, testId, mark), `premise: when the catch-up ended the record had not seen ${testId} put on screen, or saw it busy — a flag already up needs no change to stay up, and its silence would prove nothing`).toBe('false');
        }
        expect(busyRaised(record, 'sync-button', mark, clicked), 'the Refresh button spun for the reload in background after a price catch-up, or for the contribution it asks again: it waits for the loads the user asks for, and these are not (Y11, P3)').toEqual([]);
        expect(
            busyRaised(record, 'dashboard-page', mark, clicked),
            'the Dashboard said it was busy through the reload in background after a price catch-up — for its report (`reportLoading`) or for the contribution of the Performance view (`contributionRefreshing`): a screen reader announces «busy» for a price refresh nobody asked for (Z-18)',
        ).toEqual([]);
    });
});

test.describe('A price page asks its prices again after a catch-up (Z-14)', () => {
    test('(g) asset detail: back in-app after a catch-up that updated something, the page asks again the prices of the range it had loaded — without a catch-up the cache answers', async ({page}) => {
        // A load, two round trips through the Dashboard — its Refresh pressed on each — and a catch-up of a few polls.
        test.setTimeout(120_000);
        const assetId = await pricedAssetId(page);
        const range = rangeEndingToday();
        const catchUp = await simulateCatchUp(page, {header: null, status: idle(false)});
        const live = await stubLivePrices(page);
        await navigateTo(page, `/assets/${assetId}?start=${range.start}&end=${range.end}`);
        const root = assetDetail(page);
        await expect(root).toBeVisible({timeout: PAGE_TIMEOUT});

        // The first load: a fresh document has nothing cached. Settled, its answer is in the cache.
        const first = await assetQueryLanded(page, assetId, 0, `the page of asset ${assetId} never asked for its prices, or the answer never came back`);
        await waitForSettled(root, PAGE_TIMEOUT);
        const origin = await documentOrigin(page);
        expect(first.item, 'premise: the first load asks the prices of the range in the URL').toMatchObject({include_price: true, date_range: range});
        expect(pricesOf(first.entry, assetId), `premise: the first answer carried no price of asset ${assetId} from ${range.start} to ${range.end}, so nothing was cached — check populate_mock_data.populate_price_history`).toBeGreaterThan(0);
        await expect.poll(() => live.served, {message: 'premise: the live poll of the asset page never answered — the range ends today and the asset has a provider, so it asks when the page opens (Z-8, Z-3)', timeout: PAGE_TIMEOUT}).toBeGreaterThan(0);

        await test.step('control: through the Dashboard and its Refresh, back without a catch-up, the caches answer and the page asks nothing', async () => {
            await leaveForDashboard(page);
            await refreshDashboard(page, 'the control: the Refresh on the Dashboard asked no main report, or its answer never came back — the control would not walk the path the catch-up walks');
            const mark = await backInApp(page, root);
            // The barrier comes first, so that the absence below is read after the load has decided. The root's `data-busy` is
            // `loading` (true from the page's mount, a new instance, until its chart load applies — on a cache hit in the tick
            // the load runs, with no await in it) and the Refresh button's the page's first load under its busy token, which
            // lets go only once `reloadPage()` has returned — the chart load's request, if it asks one, sent and answered
            // (`loading` alone drops when a request leaves). And the chart is drawn from the series. So a request this return
            // asks has been sent and answered by now, and "none is in the record" is not "none yet".
            await waitForSettled(root, PAGE_TIMEOUT);
            await expect(page.getByTestId('asset-detail-refresh-btn'), 'the load of the asset page never let go of its Refresh button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
            await expect(root.getByTestId('asset-detail-chart'), `back on asset ${assetId} the chart shows no series: the load ended without the prices of the range on screen`).toHaveAttribute('data-series-state', 'ready', {timeout: PAGE_TIMEOUT});
            expect(await documentOrigin(page), 'the return was a document load, which empties every cache: nothing can be proved through it').toBe(origin);
            const asked = (await pageRecord(page)).queries
                .filter((query) => query.seq > mark && query.path === PRICES_QUERY_PATH)
                .flatMap((query) => assetItems(query, assetId))
                .map((item) => ({include_price: item.include_price, include_events: item.include_events, date_range: item.date_range}));
            expect(
                asked,
                `premise: back on asset ${assetId} without a catch-up the page asked its prices query again (the items listed, with their include_price) although nothing changed — its caches must answer, prices, events and signals, and nothing leave (N64): the cache did not survive the in-app navigation, or the portfolio mutation of the live poll or the Dashboard's Refresh ({kind: 'refresh'}) turned it stale, which Z-14 and N64 rule out; either way what follows proves nothing`,
            ).toEqual([]);
        });

        // The live poll's mutations left the Dashboard's report stale, so its opening asks it again and that answer could
        // start the tracker by itself; the Refresh is pressed all the same, as on the control's round trip (see
        // catchUpEndsOnDashboard).
        await test.step('a catch-up that updated something ends on the Dashboard', () => catchUpEndsOnDashboard(page, catchUp));

        const mark = await backInApp(page, root);
        const after = await assetQueryLanded(page, assetId, mark, `back on asset ${assetId} after the catch-up, the page never asked for its prices, or the answer never came back`);
        await waitForSettled(root, PAGE_TIMEOUT);
        expect(await documentOrigin(page), 'the return was a document load, which empties every cache: nothing can be proved through it').toBe(origin);
        expect(after.item.date_range, 'premise: back on the asset the page asks the same range').toEqual(range);
        expect(after.item.include_price, 'the server caught up on prices and the asset page took the range it had loaded before from its session cache (include_price false): the days the catch-up filled show the prices of before until the page is reloaded (Z-14)').toBe(true);
    });

    test('(h) FX detail: back in-app after a catch-up that updated something, the page asks again the rates of the range it had loaded — without a catch-up it asks nothing', async ({page}) => {
        // A load, two round trips through the Dashboard — its Refresh pressed on each — and a catch-up of a few polls.
        test.setTimeout(120_000);
        const pair = await configuredPair(page, CONFIGURED_PAIR.base, CONFIGURED_PAIR.quote);
        const range = rangeEndingToday();
        const catchUp = await simulateCatchUp(page, {header: null, status: idle(false)});
        await navigateTo(page, `/fx/${pair.slug}?start=${range.start}&end=${range.end}`);
        const root = fxDetail(page);
        await expect(root).toBeVisible({timeout: PAGE_TIMEOUT});

        // The first load: a fresh document has nothing cached. Settled, its answer is in the cache.
        const first = await pairConvertLanded(page, pair, 0, `the page of ${pair.slug} never asked for its rates, or the answer never came back`);
        await fxDetailSettled(page, pair);
        const origin = await documentOrigin(page);
        const firstItems = pairItems(first, pair);
        const firstRanges = firstItems.map((item) => item.date_range);
        expect(
            firstItems.flatMap((item) => item.signals ?? []),
            'premise: the page runs without backend signals — the chart settings start with none and this context saved none. With them the page asks its whole range at every load, cached or not, and could not tell the cache from a catch-up',
        ).toEqual([]);
        expect(daysNotCovered(firstRanges, range.start, range.end), 'premise: the first load asks the whole range of the URL').toEqual([]);
        expect(first.answer?.results ?? 0, `premise: the first answer carried no rate of ${pair.slug}, so nothing was cached — check populate_mock_data.populate_fx_rates`).toBeGreaterThan(0);

        await test.step('control: through the Dashboard and its Refresh, back without a catch-up, the rates come from the cache and no convert leaves', async () => {
            await leaveForDashboard(page);
            await refreshDashboard(page, 'the control: the Refresh on the Dashboard asked no main report, or its answer never came back — the control would not walk the path the catch-up walks');
            const mark = await backInApp(page, root);
            await fxDetailSettled(page, pair);
            expect(await documentOrigin(page), 'the return was a document load, which empties every cache: nothing can be proved through it').toBe(origin);
            expect(
                pairConvertsSince(await pageRecord(page), pair, mark),
                `premise: back on ${pair.slug} without a catch-up the cached range must answer and no convert leave — the cache did not survive the in-app navigation, the Dashboard's Refresh ({kind: 'refresh'}) turned it stale, which Z-14 rules out, or the page asks its whole range anyway; either way what follows proves nothing`,
            ).toEqual([]);
        });

        // The FX page writes nothing, so the Dashboard's report is still fresh here and its opening asks nothing: the Refresh
        // is what starts the tracker (see catchUpEndsOnDashboard).
        await test.step('a catch-up that updated something ends on the Dashboard', () => catchUpEndsOnDashboard(page, catchUp));

        const mark = await backInApp(page, root);
        await fxDetailSettled(page, pair);
        expect(await documentOrigin(page), 'the return was a document load, which empties every cache: nothing can be proved through it').toBe(origin);
        const asked = pairConvertsSince(await pageRecord(page), pair, mark).flatMap((entry) => pairItems(entry, pair).map((item) => item.date_range));
        expect(asked.length, `the server caught up on rates and the page of ${pair.slug} took the range it had loaded before from its session cache — no convert left: the days the catch-up filled show the rates of before until the page is reloaded (Z-14)`).toBeGreaterThan(0);
        expect(daysNotCovered(asked, range.start, range.end), 'the rates asked again after the catch-up must cover the whole range on screen: every day of it was loaded before').toEqual([]);
    });
});

/**
 * The views already on screen reload by themselves after a catch-up, in silence (Z-14b + Z-15, lot Y5-1).
 *
 * Until Y5-1 only the Dashboard (a) and the broker page (b) listened to the portfolio bus's `{kind: 'prices'}`. The risk
 * panels, the lots panel and the price pages stayed on the figures of before the catch-up until the user navigated or
 * pressed «Aggiorna». The developer's decision of 22/10: a catch-up that UPDATED something makes every view on screen ask
 * again for what it shows, in silence — no navigation, no spinner, no `data-busy`/`aria-busy` on the page's root, no
 * skeleton, the old figures staying until the new ones land (`features/price-refresh/onPricesCaughtUp.ts`). The user's
 * own «Aggiorna» (`refreshVersion`, `{kind: 'refresh'}`) is not involved and keeps saying busy (d, e, f); a catch-up that
 * updated nothing asks nothing (c).
 *
 * Each case runs on a view opened with a full load, twice, each time on its own document and its own catch-up (the stub's
 * `running` from the first answer, then `idle`, see `viewReloadsInSilence`):
 *   - the control: the catch-up updated nothing (`last_refreshed` false) — the view asks nothing;
 *   - the case: it updated something — the view asks again within a few polls, the same questions, with no navigation;
 *     through the reload the roots and the Refresh buttons the view owns never say busy, nothing is put on screen again,
 *     no skeleton or spinning icon appears, and the figures stay.
 *   (i)   the Dashboard's risk panel (`POST /risk/query`; the panel's own spinning icon, `<testId>-refreshing`, never shown);
 *   (j)   the lots analysis panel, open on a position (`POST /portfolio/lots/analysis`);
 *   (k)   the asset detail (`POST /assets/prices/query`, `include_price: true`, the chart still there);
 *   (l)   the FX pair detail (`POST /fx/currencies/convert`, the chart still there);
 *   (m)   the assets list and the FX list.
 *
 * The record, the stub and the busy log are the ones of the cases above: `recordPage` also follows, for these cases, the
 * risk and lots questions (as the price and rate queries), every `*-loading` and `*-refreshing` element put on screen, and
 * the removal of the figures a reload must leave (`KEPT_TEST_IDS`).
 *
 * Read-only on the lane's shared backend, like the cases above: the risk, lots, price and rate queries are computations
 * and reads; the live price poll of the asset page and of the assets list, which writes today's candle, is answered in the
 * browser (`stubLivePrices`). The position of (j) is found through the Dashboard's Performance view, a row of a broker
 * the user owns, never assumed.
 *
 * Expected: red until Y5-1 lands, for the right reason — the control green, the case red at its first assertion on the
 * view: no request after the catch-up (the poll "asked again" times out). When the views ask but still say busy, the
 * assertions of `expectSilent` fail instead: the root's `data-busy` raised, or a skeleton shown.
 */
test.describe('The views on screen reload by themselves after a catch-up that updated something (Z-15)', () => {
    test('(i) Dashboard, risk panel open: after a catch-up that updated something the panel asks its questions again, in silence; one that updated nothing asks nothing', async ({page}) => {
        // Two page loads, each with the risk questions the backend computes, and two catch-ups of a few polls.
        test.setTimeout(180_000);
        const catchUp = await simulateCatchUp(page, {header: 'running', status: running()});
        await viewReloadsInSilence(page, catchUp, dashboardRiskView(page));
    });

    test('(j) Dashboard, lots analysis panel open on a position: after a catch-up that updated something the panel asks its analysis again, in silence; one that updated nothing asks nothing', async ({page}) => {
        // The visit that finds the position and saves the view, then two page loads and two catch-ups.
        test.setTimeout(180_000);
        const assetId = await ownedPositionAssetId(page);
        const catchUp = await simulateCatchUp(page, {header: 'running', status: running()});
        await viewReloadsInSilence(page, catchUp, dashboardLotsView(page, assetId));
    });

    test('(k) asset detail: after a catch-up that updated something the page asks its prices again without navigating, and neither its root nor its chart says busy; one that updated nothing asks nothing', async ({page}) => {
        test.setTimeout(180_000);
        const assetId = await pricedAssetId(page);
        const range = rangeEndingToday();
        const catchUp = await simulateCatchUp(page, {header: 'running', status: running()});
        await stubLivePrices(page);
        await viewReloadsInSilence(page, catchUp, assetDetailView(page, assetId, range));
    });

    test('(l) FX detail: after a catch-up that updated something the page asks its rates again without navigating, and neither its root nor its chart says busy; one that updated nothing asks nothing', async ({page}) => {
        test.setTimeout(180_000);
        const pair = await configuredPair(page, CONFIGURED_PAIR.base, CONFIGURED_PAIR.quote);
        const range = rangeEndingToday();
        const catchUp = await simulateCatchUp(page, {header: 'running', status: running()});
        await viewReloadsInSilence(page, catchUp, fxDetailView(page, pair, range));
    });

    test('(m) assets list and FX list: after a catch-up that updated something each asks its prices or conversions again, and its root never says busy; one that updated nothing asks nothing', async ({page}) => {
        // Two lists, each with its control and its case: four page loads and four catch-ups.
        test.setTimeout(240_000);
        const catchUp = await simulateCatchUp(page, {header: 'running', status: running()});
        await stubLivePrices(page);
        await test.step('the assets list', () => viewReloadsInSilence(page, catchUp, assetsListView(page)));
        await test.step('the FX list', () => viewReloadsInSilence(page, catchUp, fxListView(page)));
    });
});

/**
 * Back in-app after a catch-up, the price pages show the stale points at once (Z-14b + Z-15, lot Y5-1).
 *
 * (g) and (h) pin that a page which comes back after a catch-up asks its prices or rates again (Z-14). Y5-1 adds how: not
 * as a load the user asked for. The page may say busy for a moment at the return (`reloadPage()` sets `loading` while it
 * decides its cache), but as soon as the stale points are on screen its root stops saying so, and the request that goes
 * out in background does not raise the flag again (D3). (g) and (h) stay as they are; these two walk the same path once,
 * without their control, with the request for the prices or rates HELD in flight by a gate (`holdQuery`): the root must
 * read `data-busy="false"` while the request is still held, with the chart visible; the request is then let through and,
 * from the first `false` in the record on, the root never reads `true` again. The Refresh button is not part of the
 * silence: the page's own first load holds it. After them, in the same page and under the same record, the control: the
 * user's own Refresh makes the button say busy.
 *   (g') asset detail   (h') FX detail
 *
 * Red until Y5-1 for the right reason: with the request held the root keeps saying busy (`loading` until the answer lands).
 */
test.describe('A price page back after a catch-up draws the stale points at once and asks in background (Z-15)', () => {
    test("(g') asset detail: back in-app after a catch-up that updated something, the stale points are on screen while the prices are asked in background, and the root stops saying busy", async ({page}) => {
        // A load, one round trip through the Dashboard with its Refresh and a catch-up of a few polls, the user's Refresh.
        test.setTimeout(120_000);
        const assetId = await pricedAssetId(page);
        const range = rangeEndingToday();
        const catchUp = await simulateCatchUp(page, {header: null, status: idle(false)});
        await stubLivePrices(page);
        await navigateTo(page, `/assets/${assetId}?start=${range.start}&end=${range.end}`);
        const root = assetDetail(page);
        await expect(root).toBeVisible({timeout: PAGE_TIMEOUT});
        const first = await assetQueryLanded(page, assetId, 0, `the page of asset ${assetId} never asked for its prices, or the answer never came back`);
        await waitForSettled(root, PAGE_TIMEOUT);
        const origin = await documentOrigin(page);
        expect(pricesOf(first.entry, assetId), `premise: the first answer carried no price of asset ${assetId}, so nothing was cached — check populate_mock_data.populate_price_history`).toBeGreaterThan(0);

        await catchUpEndsOnDashboard(page, catchUp);

        // Held from here: the page asks the prices of the range with include_price true as soon as it is back.
        const gate = await holdQuery(page, PRICES_QUERY_PATH, (body) => Array.isArray(body) && body.some((item) => item?.asset_id === assetId && item?.include_price === true));
        try {
            const mark = await backInApp(page, root);
            await staleThenSilent(
                page,
                gate,
                root,
                'asset-detail-page',
                root.getByTestId('asset-detail-chart'),
                async () => {
                    const after = await assetQueryLanded(page, assetId, mark, `back on asset ${assetId} after the catch-up, the request for its prices never came back once let through`);
                    expect(after.item.include_price, 'premise (Z-14): back on the asset after the catch-up the page asks the prices again').toBe(true);
                },
                mark,
            );
        } finally {
            await gate.dispose();
        }
        await expect(page.getByTestId('asset-detail-refresh-btn'), 'the load of the asset page never let go of its Refresh button').toHaveAttribute('data-busy', 'false', {timeout: PAGE_TIMEOUT});
        expect(await documentOrigin(page), 'the return was a document load, which empties every cache: nothing can be proved through it').toBe(origin);
        await expect(root.getByTestId('asset-detail-chart')).toHaveAttribute('data-series-state', 'ready');

        await test.step('control: a Refresh the user asks for says busy on the button', () => buttonSaysBusy(page, 'asset-detail-refresh-btn'));
    });

    test("(h') FX detail: back in-app after a catch-up that updated something, the stale points are on screen while the rates are asked in background, and the root stops saying busy", async ({page}) => {
        // A load, one round trip through the Dashboard with its Refresh and a catch-up of a few polls, the user's Refresh.
        test.setTimeout(120_000);
        const pair = await configuredPair(page, CONFIGURED_PAIR.base, CONFIGURED_PAIR.quote);
        const range = rangeEndingToday();
        const catchUp = await simulateCatchUp(page, {header: null, status: idle(false)});
        await navigateTo(page, `/fx/${pair.slug}?start=${range.start}&end=${range.end}`);
        const root = fxDetail(page);
        await expect(root).toBeVisible({timeout: PAGE_TIMEOUT});
        const first = await pairConvertLanded(page, pair, 0, `the page of ${pair.slug} never asked for its rates, or the answer never came back`);
        await fxDetailSettled(page, pair);
        const origin = await documentOrigin(page);
        expect(first.answer?.results ?? 0, `premise: the first answer carried no rate of ${pair.slug}, so nothing was cached — check populate_mock_data.populate_fx_rates`).toBeGreaterThan(0);

        await catchUpEndsOnDashboard(page, catchUp);

        // Held from here: the page asks the rates of the pair as soon as it is back.
        const gate = await holdQuery(page, CONVERT_PATH, (body) => pairItems({body} as QueryEntry, pair).length > 0);
        try {
            const mark = await backInApp(page, root);
            await staleThenSilent(page, gate, root, 'fx-detail-page', root.getByTestId('fx-detail-chart'), () => pairConvertLanded(page, pair, mark, `back on ${pair.slug} after the catch-up, the request for its rates never came back once let through`), mark);
        } finally {
            await gate.dispose();
        }
        await fxDetailSettled(page, pair);
        expect(await documentOrigin(page), 'the return was a document load, which empties every cache: nothing can be proved through it').toBe(origin);

        await test.step('control: a Refresh the user asks for says busy on the button', () => buttonSaysBusy(page, 'fx-detail-refresh-btn'));
    });
});
