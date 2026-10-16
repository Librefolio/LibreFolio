/**
 * «Updating prices…» end to end, and the open page that catches up after it without saying it is busy (release 1.3,
 * workstream Z, lots Z5, Z-13 and Z-18).
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
 * and the routes and the init script go with the page.
 *
 * Desktop only: the tracker and the reload do not depend on the viewport, and (c) moves through the sidebar.
 *
 * Expected. (a)–(c) pin Z5 and Z-13, green (before Z-13 they were red at the reload, (c) at its control — its two
 * absences are green with or without Z-13, and the control is what keeps them from being vacuous). Before the code of
 * Z-18: (e) green, a regression pin of Y11; (d) red at its last assertion only — the Dashboard's root says busy through
 * the reload, `loadAll()` setting `reportLoading` — with its premises, its button pin and its control green before it;
 * (f) the same, its root raised by `contributionRefreshing` too (`loadContribution()`, on the stale cached contribution).
 */

import type {APIResponse} from '@playwright/test';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

const API = '/api/v1';
const API_ROUTE = '**/api/v1/**';
const REPORT_PATH = `${API}/portfolio/report`;
/** Written out rather than imported: the spec pins the contract of Z5, it does not follow the code. */
const STATUS_PATH = `${API}/system/price-refresh`;
const HEADER = 'x-librefolio-price-refresh';
const NOTICE_SELECTOR = '[data-testid="instance-notice"][data-notice-id="liveUpdates.priceRefresh"]';
/** The elements whose `data-busy` the record follows (Z-18, Y11): the Dashboard's root and the Refresh button of each page. */
const BUSY_TEST_IDS = ['dashboard-page', 'sync-button', 'broker-refresh'] as const;
type BusyTestId = (typeof BUSY_TEST_IDS)[number];
/** The tracker's cadence (PRICE_REFRESH_POLL_MS). */
const POLL_MS = 3_000;
/** A wait on the tracker: three polls — the one in flight, the next, and the answer's way back. */
const POLL_BUDGET_MS = 3 * POLL_MS;
/** A page load or an in-app navigation, with the report it asks for. */
const PAGE_TIMEOUT = 30_000;
/** The mock's broker with positions (populate_mock_data.py), found by name, never by position. */
const BROKER_WITH_HOLDINGS = 'Interactive Brokers';

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

/** The record the init script keeps on `window` (see the header). */
interface PageRecord {
    seq: number;
    reports: Array<{seq: number; body: ReportBody | null}>;
    reportsSettled: number;
    statusRead: Array<{seq: number; state: string}>;
    noticeShown: number[];
    busy: BusyEntry[];
    /** Each click, with the test id of the nearest marked element (the target's own, or an ancestor's). */
    clicks: Array<{seq: number; testId: string | null}>;
}

/** Arms the record for every document this page opens from now on: call it before the page under test loads. */
async function recordPage(page: Page): Promise<void> {
    await page.addInitScript(
        ({reportPath, statusPath, noticeSelector, busyTestIds}: {reportPath: string; statusPath: string; noticeSelector: string; busyTestIds: string[]}) => {
            const record = {
                seq: 0,
                reports: [] as Array<{seq: number; body: unknown}>,
                reportsSettled: 0,
                statusRead: [] as Array<{seq: number; state: string}>,
                noticeShown: [] as number[],
                busy: [] as Array<{seq: number; testId: string; kind: 'mount' | 'change'; value: string | null}>,
                clicks: [] as Array<{seq: number; testId: string | null}>,
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

            // XHR: what axios, and so `fetchReport`, uses today.
            const reportXhrs = new WeakSet<XMLHttpRequest>();
            const nativeOpen = XMLHttpRequest.prototype.open;
            const nativeSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function (this: XMLHttpRequest, ...args: unknown[]) {
                if (String(args[0]).toUpperCase() === 'POST' && pathOf(String(args[1])) === reportPath) reportXhrs.add(this);
                else reportXhrs.delete(this);
                return Reflect.apply(nativeOpen, this, args);
            } as XMLHttpRequest['open'];
            XMLHttpRequest.prototype.send = function (this: XMLHttpRequest, ...args: unknown[]) {
                if (reportXhrs.has(this)) {
                    record.reports.push({seq: ++record.seq, body: parsed(args[0])});
                    this.addEventListener('loadend', () => {
                        record.reportsSettled += 1;
                    });
                }
                return Reflect.apply(nativeSend, this, args);
            } as XMLHttpRequest['send'];

            // fetch: what the tracker uses for the status. A report sent with fetch is recorded too, so that a change of
            // transport cannot hide one.
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
                let response: Response;
                try {
                    response = await nativeFetch.call(window, input, init);
                } finally {
                    if (isReport) record.reportsSettled += 1;
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
        {reportPath: REPORT_PATH, statusPath: STATUS_PATH, noticeSelector: NOTICE_SELECTOR, busyTestIds: [...BUSY_TEST_IDS]},
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
