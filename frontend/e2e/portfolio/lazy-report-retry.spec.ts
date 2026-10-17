/**
 * Lazy report retry (backlog Y-24; contract decided by the coordinator of Y, 17/10/2026) — E2E.
 *
 * The P&L candles of the growth chart and the contribution of the positions panel are asked lazily, by the panel's
 * `$effect`, when its view needs them and has none. When `POST /api/v1/portfolio/report` fails, `requestReport` resolves
 * null, the loader's `finally` turns its `loading` flag back to false, and the effect that read the flag runs again:
 * the request leaves again at once, with no pause and no end, each one a full report on the server. The cure
 * (`stores/portfolio/lazyReportRetry.svelte.ts`, pinned on its own by its unit spec) bounds it per scope —
 * brokers|start|end|currency —: after failure n the section may be asked again only once a timer of 2, 4 or 8 s has
 * fired, so four requests at most, the first and three retries; a success forgets; a new scope (a period change) and
 * the page's Refresh ask again. Nothing on screen changes.
 *
 * What is pinned, on the Dashboard and on a broker's page (legacy mode):
 *   (a) Dashboard, P&L → Candles: the failed candles are not asked again while the clock stands still; then once 2 s
 *       after the failure (not 1 ms before), once 4 s after the next, once 8 s after the next — four in all —, and never
 *       again over a minute of page clock; a period change (6M) asks them again, once, for the new period.
 *   (b) Dashboard, P&L → Candles, the first request failed and the next answered: asked again 2 s later, and the candles
 *       of that answer are drawn (read off the ECharts option the chart publishes as `__lfChart`), with no request more.
 *   (c) Dashboard, Positions → Performance: the contribution, bounded the same way; the Refresh button asks it again.
 *   (d) Broker detail, P&L → Candles: bounded the same way; the broker's Refresh asks them again.
 *   (e) Broker detail, Positions → Performance: the contribution, bounded the same way; a period change asks it again.
 *   (f) Broker detail, P&L → Candles, the request held while the period changes (6M) and the new period's overview comes
 *       back, then failed: the candles of the new period are asked, once, and drawn. The held request is the only one
 *       answered 500, so no candles of the old period exist anywhere — on screen or in the report cache —: candles drawn
 *       can only be the new period's, which the request that brought them asked.
 *   (g) Broker detail, P&L → Candles, the request held while the chart leaves Candles for Line and comes back, then
 *       failed: not asked again at once, nor 1 ms before 2 s, and exactly once at 2 s.
 *
 * How time is driven. `page.clock.install()` before the page under test opens, so that all its timers are the
 * clock's; until it is paused the clock flows with real time, and the page loads as it would without it. Once the page
 * has settled — its Refresh button's `data-busy`, and the Dashboard's root's — and before the view that asks is chosen,
 * `pauseAt` freezes the page clock a few seconds ahead. From there only the test moves time, with `runFor`, which fires
 * every timer due on the way, in order, letting the page's microtasks and tasks run after each one. A request a fired
 * timer causes is therefore sent before `runFor` returns: a count read in the page right after `runFor` is exact.
 *
 * Why the page clock holds on these pages, checked in the code they run (no clock-dependent step is left to luck):
 * Playwright's clock fakes the timers, `requestAnimationFrame`, `requestIdleCallback`, `Date`, `performance`, `Intl` and
 * `AbortSignal`, and leaves `queueMicrotask`, `MessageChannel` and XHR alone. Svelte 5 flushes its effects through
 * `queueMicrotask`, so the panels' effects — the storm included — run with the clock frozen; axios answers through the
 * XHR's `onloadend` (no timer in Chromium), so a 500 is handled with the clock frozen too; ECharts' `setOption` merges
 * the option into its model at once (a `lazyUpdate` defers only the drawing), so the candles reach `getOption()` with
 * the clock frozen, and zrender's animation loop sleeps after ten still frames, so a minute of page clock costs a few
 * dozen frames, not thousands. The marquee of a label too long for its box — the candles view has one — is an endless
 * `requestAnimationFrame` loop; it stops under reduced motion, which every case asks for. Playwright's own waits run on
 * the browser's native timers (the clock hands them to its injected script before it replaces them), so locator
 * assertions and clicks keep working while the page clock is frozen. The test server runs with `--no-scheduler`: no
 * price catch-up, so no reload in background, can cut into a count.
 *
 * Counting. A route on the report answers the section under test with a 500 in the browser — every request of it, or
 * in (b) and (f) the first only — and lets every other report through to the real backend; it counts what it answered.
 * In (f) and (g) it also holds the first request of the section, unanswered, until the case releases it; meanwhile the
 * page counts it sent and not back, and a move made then is checked to have asked nothing of its own. An init
 * script counts the reports the page sends by XHR, the transport axios uses, and how many came back: a report counts as
 * back one task after its `loadend`, once the microtasks its answer set off have run — the loader's continuation, and
 * whatever it asked at once. An absence is read only after a presence: the request before it is back and handled in the
 * page, and — for the first one — the page clock is checked to have stood still. The Refresh button is not that
 * barrier: a lazy load on an idle page runs without a token of its own (N55), so the button does not wait for it. Every
 * case first checks that the init script did count the page's own main report, so that a section it never counts is one
 * the page never sent.
 *
 * Red before the cure, each where its defect shows: (a), (c) and (e) at their first «not asked again at once» — a storm,
 * the next request leaving as soon as the 500 is handled, absorbed by the stub without reaching the backend; (b) at the
 * same assertion, the retry leaving at once and answered at once. (d) is red later: on the broker page the candles
 * loader's `pnlCandlesLoading` is a plain `let` of a legacy component that its template never reads, which Svelte 5
 * leaves a plain variable, so nothing runs the chart's effect again after a failure — no storm, and no retry either:
 * red at «asked again exactly once 2 s after failure 1», never sent. The broker page's contribution flag is a signal
 * (its template passes it on), hence the storm of (e).
 *
 * (f) and (g) come from a review of the first cure (17/10), and are red on it: there the broker page's candles loader
 * still keeps `pnlCandlesLoading` a plain `let`, and its guard returns on it before it reads the retry's `canAsk`. So
 * the chart's effect, last run while a request was in flight, depends on neither: the flag falling back to false wakes
 * nothing, and neither does a retry falling due. (f) is red at «the candles of the new period are asked», never sent:
 * the effect ran on the period change and returned on the flag, the late answer — of the old period — is dropped, and
 * nothing asks for the new period's candles, ever. (g) is red at «asked again exactly once 2 s after the failure»: the
 * effect ran on the way back to Candles, returned on the flag without reading `canAsk`, and the retry that falls due
 * wakes nobody. Both are green once the flag is reactive and `canAsk` is read before the other guards.
 *
 * Read-only on the shared database: TEST_USER and the mock's broker with positions, Interactive Brokers (owned, found
 * by name through `page.request`, never by position). The failures are answered in the browser; what goes through is
 * report reads. The growth chart's mode, the positions panel's view and the period live in this context's own
 * localStorage and sessionStorage, and go with it; the stub stays routed until the page closes, so that a storm still
 * running when a red ends the test never reaches the backend, and a held request is released in `finally` — as the 500
 * it was planned to be — so that none outlives its test.
 *
 * Desktop only: the retry schedule does not depend on the viewport.
 */

import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
const BROKERS_PATH = `${API}/brokers`;
/** The mock's broker with positions, owned by TEST_USER (populate_mock_data.py): found by name, never by position. */
const BROKER_WITH_HOLDINGS = 'Interactive Brokers';

/** The contract's delays, written out: the spec pins the numbers that were decided (the module is a `.svelte.ts`, which Playwright's loader does not run). */
const RETRY_DELAYS_MS = [2_000, 4_000, 8_000] as const;
/** The first request and one retry per delay. */
const MAX_REQUESTS = 1 + RETRY_DELAYS_MS.length;
/** A minute of page clock after the last failure: well past any further doubling (16 s), and nothing may come. */
const LONG_QUIET_MS = 60_000;
/** `pauseAt` refuses a time the page clock has already passed: frozen this far ahead of where it was read. */
const PAUSE_AHEAD_MS = 5_000;
/** A page load, or a round trip to the backend (the report is computed on the spot). A deadline, never a delay. */
const ROUND_TRIP_MS = 30_000;
/** Login, one page load, a dozen clock steps and a round trip to the real backend. */
const TEST_MS = 120_000;
/** The stub fails every request of its section. */
const EVERY_REQUEST = Number.POSITIVE_INFINITY;
/** Where the init script keeps its count, on `window`. */
const RECORD_KEY = '__lfSpecLazyReports';

/** A lazy section of the report, asked alone, with no history. */
type Section = 'candles' | 'contribution';

type ReportBody = {
    include_history?: boolean;
    include_pnl_candles?: boolean;
    include_positions_contribution?: boolean;
    broker_ids?: number[];
    date_range?: {start?: string; end?: string};
    target_currency?: string;
};

/** The section a report asks alone, with no history: the P&L candles (`loadPnlCandles`) or the contribution (`loadContribution`). */
function sectionOf(body: ReportBody | null): Section | null {
    if (body?.include_history !== false) return null;
    if (body.include_pnl_candles === true) return 'candles';
    if (body.include_positions_contribution === true) return 'contribution';
    return null;
}

function periodOf(body: ReportBody): string {
    return `${body.date_range?.start ?? ''}..${body.date_range?.end ?? ''}`;
}

/** The scope the cure keys its failures on: brokers|start|end|currency. */
function scopeOf(body: ReportBody): string {
    return `${(body.broker_ids ?? []).join(',')}|${periodOf(body)}|${body.target_currency ?? ''}`;
}

/** What the stub has answered, in arrival order. */
interface Answered {
    body: ReportBody;
    /** Answered with a 500; otherwise let through to the backend. */
    failed: boolean;
    /** Held unanswered until the case released it. */
    held: boolean;
}

interface LazyStub {
    readonly section: Section;
    readonly seen: Answered[];
    /** How many requests of the section the stub holds now, unanswered. */
    waiting(): number;
    /** Answers the held requests as planned, and holds none from then on. Safe to call twice: a `finally` calls it. */
    release(): void;
}

/**
 * Answers the requests of `section` with a 500 in the browser — the first `failures` of them, the next let through to
 * the backend — and every other report goes through untouched. The first `held` requests of the section are held
 * unanswered until `release()`, then answered as planned. Routed by path and decided by body: the lazy sections are
 * asked on the same path as the page's main report.
 */
async function stubSection(page: Page, section: Section, failures: number, held = 0): Promise<LazyStub> {
    let open!: () => void;
    const gate = new Promise<void>((resolve) => {
        open = resolve;
    });
    let released = false;
    let waiting = 0;
    const seen: Answered[] = [];
    await page.route(
        (url) => url.pathname === REPORT_PATH,
        async (route) => {
            const request = route.request();
            let body: ReportBody | null = null;
            try {
                body = request.method() === 'POST' ? (request.postDataJSON() as ReportBody | null) : null;
            } catch {
                // Not a JSON body: not a report this stub answers.
            }
            if (body === null || sectionOf(body) !== section) {
                await route.fallback().catch(() => undefined);
                return;
            }
            const index = seen.length;
            const answered: Answered = {body, failed: index < failures, held: index < held && !released};
            seen.push(answered);
            if (answered.held) {
                waiting += 1;
                await gate;
                waiting -= 1;
            }
            // A page that went away with the request in flight has nobody to answer.
            if (answered.failed) await route.fulfill({status: 500, json: {detail: 'Internal Server Error'}}).catch(() => undefined);
            else await route.fallback().catch(() => undefined);
        },
    );
    return {
        section,
        seen,
        waiting: () => waiting,
        release: () => {
            released = true;
            open();
        },
    };
}

/** One kind of report, as the init script counts it in the page. */
interface Count {
    sent: number;
    landed: number;
    /** The period each one asked, in the order sent. */
    periods: string[];
}

interface PageRecord {
    /** Every report the page sent: the positive control. */
    all: Count;
    candles: Count;
    contribution: Count;
}

/**
 * Counts, in every document from now on, the reports (`POST /portfolio/report`) the page sends and how many came back:
 * a report is back one task after its `loadend`, once the microtasks its answer set off — the loader that sent it, and
 * what it asked at once — have run. Counted on XHR, the transport axios uses; `expectRecordSeesReports` checks it does.
 */
async function recordReports(page: Page): Promise<void> {
    await page.addInitScript(
        ({key, path}) => {
            type Kind = {sent: number; landed: number; periods: string[]};
            type Body = {include_history?: unknown; include_pnl_candles?: unknown; include_positions_contribution?: unknown; date_range?: {start?: unknown; end?: unknown}} | null;
            const record: {all: Kind; candles: Kind; contribution: Kind} = {
                all: {sent: 0, landed: 0, periods: []},
                candles: {sent: 0, landed: 0, periods: []},
                contribution: {sent: 0, landed: 0, periods: []},
            };
            Object.defineProperty(window, key, {value: record, configurable: true});
            // The rule of `sectionOf`, written again: an init script references nothing outside itself.
            const kindsOf = (payload: unknown): Kind[] => {
                let body: Body = null;
                try {
                    body = typeof payload === 'string' ? (JSON.parse(payload) as Body) : null;
                } catch {
                    body = null;
                }
                const kinds = [record.all];
                if (body?.include_history === false && body.include_pnl_candles === true) kinds.push(record.candles);
                else if (body?.include_history === false && body.include_positions_contribution === true) kinds.push(record.contribution);
                const period = `${String(body?.date_range?.start ?? '')}..${String(body?.date_range?.end ?? '')}`;
                for (const kind of kinds) {
                    kind.sent += 1;
                    kind.periods.push(period);
                }
                return kinds;
            };
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
                    const kinds = kindsOf(args[0]);
                    // Added at the send, after axios's own handler: the answer's microtasks run before the next task.
                    this.addEventListener('loadend', () => {
                        const nextTask = new MessageChannel();
                        nextTask.port1.onmessage = () => {
                            for (const kind of kinds) kind.landed += 1;
                            nextTask.port1.close();
                        };
                        nextTask.port2.postMessage(null);
                    });
                }
                return Reflect.apply(nativeSend, this, args);
            } as XMLHttpRequest['send'];
        },
        {key: RECORD_KEY, path: REPORT_PATH},
    );
}

async function pageRecord(page: Page): Promise<PageRecord> {
    return page.evaluate((key) => {
        const record = (window as unknown as Record<string, PageRecord | undefined>)[key];
        if (!record) throw new Error('No report record in this document: recordReports() must be installed before the navigation');
        return record;
    }, RECORD_KEY);
}

/** «2026-07-17..2026-10-17 ×4»: the periods asked, each with how many times. */
function describePeriods(periods: string[]): string {
    const times = new Map<string, number>();
    for (const period of periods) times.set(period, (times.get(period) ?? 0) + 1);
    return [...times].map(([period, count]) => `${period} ×${count}`).join(', ') || 'none';
}

function describeSeen(stub: LazyStub): string {
    return stub.seen.map((answered, index) => `#${index + 1}${answered.held ? ' held, then' : ''} ${answered.failed ? '500' : 'let through'} ${scopeOf(answered.body)}`).join('; ') || 'none';
}

/** The answer to request `n` of the stub's section is back in the page and handled: one task after its `loadend`. */
async function expectLanded(page: Page, stub: LazyStub, n: number, what: string): Promise<void> {
    await expect.poll(async () => (await pageRecord(page))[stub.section].landed, {message: `${what} — the answer to ${stub.section} request ${n} never came back to the page`, timeout: ROUND_TRIP_MS}).toBeGreaterThanOrEqual(n);
}

/**
 * Exactly `expected` requests of the stub's section so far: request `expected` was sent and is back and handled in the
 * page (a request its answer would cause at once is sent by then), the page sent no other, and the stub saw the same
 * ones. With `expected` already reached it is an absence read at once: right after `runFor`, or after a presence.
 */
async function expectRequests(page: Page, stub: LazyStub, expected: number, what: string): Promise<void> {
    const section = stub.section;
    await expect.poll(async () => (await pageRecord(page))[section].sent, {message: `${what} — the page never sent ${section} request ${expected}`, timeout: ROUND_TRIP_MS}).toBeGreaterThanOrEqual(expected);
    await expectLanded(page, stub, expected, what);
    const record = (await pageRecord(page))[section];
    expect(record.sent, `${what} — the page sent ${record.sent} ${section} requests: ${describePeriods(record.periods)}`).toBe(expected);
    expect(stub.seen.length, `${what} — the stub saw ${describeSeen(stub)}`).toBe(expected);
}

/**
 * The first request of the stub's section is held at the network, and is the only one of its section: the stub holds
 * it, and the page counts it sent and not back. Read after a presence barrier — the move that would have asked again
 * is on screen —, it is also the absence of a second request.
 */
async function expectHeld(page: Page, stub: LazyStub, what: string): Promise<void> {
    await expect.poll(() => stub.waiting(), {message: `${what} — the ${stub.section} request never reached the network to be held`, timeout: ROUND_TRIP_MS}).toBe(1);
    const record = (await pageRecord(page))[stub.section];
    expect(record.sent, `${what} — the page sent ${record.sent} ${stub.section} requests: ${describePeriods(record.periods)}`).toBe(1);
    expect(record.landed, `${what} — the held ${stub.section} request came back to the page`).toBe(0);
    expect(stub.seen.length, `${what} — the stub saw ${describeSeen(stub)}`).toBe(1);
}

/** Positive control of the init script: it counted the page's own main report, sent and back. */
async function expectRecordSeesReports(page: Page): Promise<void> {
    const {all} = await pageRecord(page);
    expect(all.sent, 'the init script counted none of the reports the page sent (is the report still sent by XHR?): an absence it reads would prove nothing').toBeGreaterThan(0);
    expect(all.landed, 'the init script saw none of the reports come back').toBeGreaterThan(0);
}

async function pageNow(page: Page): Promise<number> {
    return page.evaluate(() => Date.now());
}

/** Freezes the page clock a little ahead of where it is; returns the page time it froze at. */
async function pauseClock(page: Page): Promise<number> {
    const at = (await pageNow(page)) + PAUSE_AHEAD_MS;
    await page.clock.pauseAt(at);
    expect(await pageNow(page), 'the page clock froze where it was asked to').toBe(at);
    return at;
}

/** Runs the frozen page clock `ms` on, firing every timer due on the way. */
async function runClock(page: Page, ms: number): Promise<void> {
    const target = (await pageNow(page)) + ms;
    try {
        await page.clock.runFor(ms);
    } catch (error) {
        // The clock rethrows the first exception a page timer threw, once every timer up to the target has run. A page
        // error is not the subject here: it is reported with the test, never swallowed — and the clock must still have
        // reached its target, or what follows would be read on the wrong time.
        const firstLine = String(error).split('\n')[0];
        test.info().annotations.push({type: 'page timer error', description: firstLine});
    }
    expect(await pageNow(page), `the page clock did not run ${ms} ms`).toBe(target);
}

/**
 * Everything in place before the page under test opens: reduced motion (the marquee of a label that does not fit is an
 * endless `requestAnimationFrame` loop, each frame a timer `runFor` would fire), the stub of the section — failing the
 * first `failures` requests, holding the first `held` —, the count in the page, and the clock — installed, flowing with
 * real time until `pauseClock`.
 */
async function preparePage(page: Page, section: Section, failures: number, held = 0): Promise<LazyStub> {
    await page.emulateMedia({reducedMotion: 'reduce'});
    const stub = await stubSection(page, section, failures, held);
    await recordReports(page);
    await page.clock.install();
    return stub;
}

/** Idle: nothing of this page is pending, and the button can be pressed. A round trip away at most. */
async function expectIdle(button: Locator, why: string): Promise<void> {
    await expect(button, why).toHaveAttribute('data-busy', 'false', {timeout: ROUND_TRIP_MS});
    await expect(button, why).toBeEnabled();
}

/** The Dashboard on `tab`, loaded from scratch and settled: its report in (the root's `data-busy`), nothing of the page pending (the button's). */
async function openDashboard(page: Page, tab: 'panoramica' | 'posizioni'): Promise<Locator> {
    await navigateTo(page, `/dashboard?tab=${tab}`);
    await waitForSettled(page.getByTestId('dashboard-page'), ROUND_TRIP_MS);
    const refresh = page.getByTestId('sync-button');
    await expectIdle(refresh, 'the Dashboard settled with its Refresh button still waiting');
    return refresh;
}

/** The id of a broker TEST_USER sees, by name, read with `page.request`: no route of the page intercepts it. */
async function brokerIdByName(page: Page, name: string): Promise<number> {
    const response = await page.request.get(BROKERS_PATH);
    expect(response.ok(), `GET ${BROKERS_PATH} → HTTP ${response.status()}`).toBe(true);
    const items = ((await response.json()) as {items?: Array<{id: number; name: string}>}).items ?? [];
    const broker = items.find((item) => item.name === name);
    if (!broker) throw new Error(`${name} is the mock's broker with positions, owned by ${TEST_USER.username}: check populate_mock_data.py (brokers seen: ${items.map((item) => item.name).join(', ') || 'none'})`);
    return broker.id;
}

/**
 * A broker's page on `tab`, loaded from scratch and settled. Its root publishes no `data-busy`: the Refresh button's is
 * the barrier, held by the first load until the broker, its overview and the reference lists are in.
 */
async function openBrokerDetail(page: Page, brokerId: number, tab: 'panoramica' | 'posizioni'): Promise<Locator> {
    await navigateTo(page, `/brokers/${brokerId}?tab=${tab}`);
    await expect(page.getByTestId('broker-name'), `the page of broker ${brokerId} did not load its broker`).toBeVisible({timeout: ROUND_TRIP_MS});
    const refresh = page.getByTestId('broker-refresh');
    await expectIdle(refresh, "the broker's page settled with its Refresh button still waiting");
    return refresh;
}

/**
 * P&L, then Candles, the way a user chooses them: the candles submode asks its candles as it is chosen. Both start
 * unpressed — this context saved no view —, which the case checks rather than assumes: a chart opening on candles
 * would have asked them while the clock still flowed.
 */
async function chooseCandles(chart: Locator): Promise<void> {
    const pnl = chart.getByTestId('growth-toggle-pnl');
    await expect(pnl, 'precondition: the growth chart opens on another mode (this context saved no view)').toHaveAttribute('aria-pressed', 'false', {timeout: ROUND_TRIP_MS});
    await pnl.click();
    await expect(pnl).toHaveAttribute('aria-pressed', 'true');
    const candles = chart.getByTestId('growth-pnl-submode-candles');
    await expect(candles, 'precondition: the P&L mode opens on another submode (this context saved no view)').toHaveAttribute('aria-pressed', 'false');
    await candles.click();
    await expect(candles).toHaveAttribute('aria-pressed', 'true');
}

/** Performance, the way a user chooses it: the view asks its contribution as it is chosen. It starts unpressed — this context saved no view —, checked. */
async function choosePerformance(panel: Locator): Promise<void> {
    const performance = panel.getByTestId('positions-toggle-performance');
    await expect(performance, 'precondition: the positions panel opens on Holdings (this context saved no view)').toHaveAttribute('aria-pressed', 'false', {timeout: ROUND_TRIP_MS});
    await performance.click();
    await expect(performance).toHaveAttribute('aria-pressed', 'true');
}

/**
 * The first request of the section left when its view was chosen, its 500 is back and handled in the page, and — the
 * page clock frozen since — nothing asked it again. Today the next one leaves as soon as the 500 is handled (Y-24).
 */
async function expectNotAskedAgainAtOnce(page: Page, stub: LazyStub, pausedAt: number, what: string): Promise<void> {
    await expectRequests(page, stub, 1, `${what}: the request failed and the page clock stands still, yet it was asked again at once (Y-24)`);
    expect(await pageNow(page), 'premise: the page clock stood still meanwhile').toBe(pausedAt);
}

/**
 * The schedule: after failure n the section is asked again RETRY_DELAYS_MS[n − 1] after it — not a millisecond before,
 * exactly once at it — and after the fourth failure never again, however long the page waits. Starts with the first
 * request failed and handled, the clock frozen since.
 */
async function expectBoundedRetries(page: Page, stub: LazyStub, what: string): Promise<void> {
    for (const [index, delay] of RETRY_DELAYS_MS.entries()) {
        const failure = index + 1;
        await runClock(page, delay - 1);
        await expectRequests(page, stub, failure, `${what}: ${delay - 1} ms after failure ${failure}, not asked again yet`);
        await runClock(page, 1);
        await expectRequests(page, stub, failure + 1, `${what}: ${delay} ms after failure ${failure}, asked again exactly once`);
    }
    await runClock(page, LONG_QUIET_MS);
    await expectRequests(page, stub, MAX_REQUESTS, `${what}: after the fourth failure, never asked again over ${LONG_QUIET_MS / 1000} s of page clock`);
    expect(
        stub.seen.map((answered) => answered.failed),
        `${what}: the stub did not answer every request with its 500`,
    ).toEqual(Array<boolean>(MAX_REQUESTS).fill(true));
    expect(new Set(stub.seen.map((answered) => scopeOf(answered.body))).size, `${what}: the requests did not all ask one scope — ${describeSeen(stub)}`).toBe(1);
}

/**
 * After a period change (6M after 3M): request `index` of the stub's section asks the new period — one that starts
 * earlier than the first request's — of the same brokers and currency. The end is not compared: it is the page's
 * today, and in the cases that run the clock it has moved a minute and more since the first request, past midnight on
 * some runs.
 */
function expectNewPeriod(stub: LazyStub, index: number, what: string): void {
    const before = stub.seen[0].body;
    const after = stub.seen[index].body;
    expect((after.date_range?.start ?? '') < (before.date_range?.start ?? ''), `${what}: asked for ${periodOf(after)}, not the longer period after ${periodOf(before)}`).toBe(true);
    expect(after.broker_ids, `${what}: asked for other brokers`).toEqual(before.broker_ids);
    expect(after.target_currency, `${what}: asked in another currency`).toBe(before.target_currency);
}

/**
 * The chart leaves Candles for Line and comes back, the way a user does: each toggle's state is asserted before its
 * click and after it — Line is unpressed while Candles is pressed —, so each click is a move. The chart's request effect
 * runs on both moves, and the last one asks for candles again, while a request may still be in flight.
 */
async function leaveCandlesAndComeBack(chart: Locator): Promise<void> {
    const line = chart.getByTestId('growth-pnl-submode-line');
    const candles = chart.getByTestId('growth-pnl-submode-candles');
    await expect(candles, 'precondition: the chart is on Candles').toHaveAttribute('aria-pressed', 'true');
    await expect(line, 'precondition: the chart is not on Line').toHaveAttribute('aria-pressed', 'false');
    await line.click();
    await expect(line, 'the chart did not move to Line').toHaveAttribute('aria-pressed', 'true');
    await expect(candles, 'the chart did not leave Candles').toHaveAttribute('aria-pressed', 'false');
    await candles.click();
    await expect(candles, 'the chart did not come back to Candles').toHaveAttribute('aria-pressed', 'true');
    await expect(line).toHaveAttribute('aria-pressed', 'false');
}

/**
 * How many candles the growth chart draws with a real body: 0 until its candles are in, every bucket being the `'-'`
 * gap sentinel until then. Read from the ECharts instance the chart publishes as `__lfChart`, as page-busy.spec.ts reads it.
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

test.describe('Lazy report retry (Y-24): a failed candles or contribution request is asked again 2, 4 and 8 s after each failure, four times at most', () => {
    test.describe.configure({timeout: TEST_MS});

    test.beforeEach(async ({page}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', 'Desktop only: the retry schedule does not depend on the viewport');
        await login(page, TEST_USER);
    });

    test('Dashboard, P&L candles: a failed request is not asked again at once, then once 2, 4 and 8 s after each failure — four at most —, and a period change asks again', async ({page}) => {
        const candles = await preparePage(page, 'candles', EVERY_REQUEST);
        const refresh = await openDashboard(page, 'panoramica');
        await expectRecordSeesReports(page);
        await expectRequests(page, candles, 0, 'precondition: no candles asked before the candles view is chosen');
        const pausedAt = await pauseClock(page);

        await chooseCandles(page.getByTestId('growth-chart'));
        await expectNotAskedAgainAtOnce(page, candles, pausedAt, 'the candles');
        await expectBoundedRetries(page, candles, 'the candles');

        // A period change is another scope: asked again, once — the clock still frozen.
        const sixMonths = page.getByTestId('date-preset-6m');
        await expect(sixMonths, 'precondition: 6M is a change of period (the Dashboard opens on 3M)').toHaveAttribute('data-active', 'false');
        await sixMonths.click();
        await expect(sixMonths).toHaveAttribute('data-active', 'true');
        await expectRequests(page, candles, MAX_REQUESTS + 1, 'the candles: a period change asks them again');
        await expectIdle(refresh, 'the report of the new period is back, and the Refresh button still waits');
        await expectRequests(page, candles, MAX_REQUESTS + 1, 'the candles: asked once for the new period, its report back');
        expectNewPeriod(candles, MAX_REQUESTS, 'the candles after the period change');
    });

    test('Dashboard, P&L candles: a request that fails once is asked again 2 s later, and the candles of that answer are drawn', async ({page}) => {
        const candles = await preparePage(page, 'candles', 1);
        await openDashboard(page, 'panoramica');
        await expectRecordSeesReports(page);
        await expectRequests(page, candles, 0, 'precondition: no candles asked before the candles view is chosen');
        const chart = page.getByTestId('growth-chart');
        const pausedAt = await pauseClock(page);

        await chooseCandles(chart);
        await expectNotAskedAgainAtOnce(page, candles, pausedAt, 'the candles');
        expect(await candleBodies(chart), 'precondition: the chart draws candles although their only request failed').toBe(0);

        const [firstDelay] = RETRY_DELAYS_MS;
        await runClock(page, firstDelay - 1);
        await expectRequests(page, candles, 1, `the candles: ${firstDelay - 1} ms after the failure, not asked again yet`);
        await runClock(page, 1);
        await expectRequests(page, candles, 2, `the candles: ${firstDelay} ms after the failure, asked again exactly once, and answered`);
        expect(
            candles.seen.map((answered) => answered.failed),
            'the stub fails the first request and lets the second through',
        ).toEqual([true, false]);
        await expect.poll(() => candleBodies(chart), {message: 'the candles of the answered retry never reached the chart', timeout: ROUND_TRIP_MS}).toBeGreaterThan(0);
        await expectRequests(page, candles, 2, 'the candles: drawn, and not asked again');
    });

    test('Dashboard, Performance: a failed contribution is not asked again at once, four requests at most, and Refresh asks it again', async ({page}) => {
        const contribution = await preparePage(page, 'contribution', EVERY_REQUEST);
        const refresh = await openDashboard(page, 'posizioni');
        const panel = page.getByTestId('positions-panel');
        await waitForSettled(panel, ROUND_TRIP_MS);
        await expectRecordSeesReports(page);
        await expectRequests(page, contribution, 0, 'precondition: no contribution asked before the Performance view is chosen');
        const pausedAt = await pauseClock(page);

        await choosePerformance(panel);
        await expectNotAskedAgainAtOnce(page, contribution, pausedAt, 'the contribution');
        await expectBoundedRetries(page, contribution, 'the contribution');

        // Refresh forgets the failures (reset): asked again, once — the clock still frozen.
        await expectIdle(refresh, 'precondition: the Refresh button can be pressed');
        await refresh.click();
        await expectRequests(page, contribution, MAX_REQUESTS + 1, 'the contribution: Refresh asks it again');
        await expectIdle(refresh, 'what Refresh asked is back, and the Refresh button still waits');
        await expectRequests(page, contribution, MAX_REQUESTS + 1, 'the contribution: asked once by Refresh, its report back');
    });

    test('Broker detail, P&L candles: a failed request is asked again once 2, 4 and 8 s after each failure — four at most —, and Refresh asks again', async ({page}) => {
        const brokerId = await brokerIdByName(page, BROKER_WITH_HOLDINGS);
        const candles = await preparePage(page, 'candles', EVERY_REQUEST);
        const refresh = await openBrokerDetail(page, brokerId, 'panoramica');
        await expectRecordSeesReports(page);
        await expectRequests(page, candles, 0, 'precondition: no candles asked before the candles view is chosen');
        const pausedAt = await pauseClock(page);

        await chooseCandles(page.getByTestId('growth-chart'));
        await expectNotAskedAgainAtOnce(page, candles, pausedAt, "the broker's candles");
        expect(candles.seen[0].body.broker_ids, "the candles of a broker's page ask that broker alone").toEqual([brokerId]);
        await expectBoundedRetries(page, candles, "the broker's candles");

        // Refresh forgets the failures (reset): asked again, once — the clock still frozen.
        await expectIdle(refresh, 'precondition: the Refresh button can be pressed');
        await refresh.click();
        await expectRequests(page, candles, MAX_REQUESTS + 1, "the broker's candles: Refresh asks them again");
        await expectIdle(refresh, 'what Refresh asked is back, and the Refresh button still waits');
        await expectRequests(page, candles, MAX_REQUESTS + 1, "the broker's candles: asked once by Refresh, its overview back");
    });

    test('Broker detail, Performance: a failed contribution is not asked again at once, four requests at most, and a period change asks it again', async ({page}) => {
        const brokerId = await brokerIdByName(page, BROKER_WITH_HOLDINGS);
        const contribution = await preparePage(page, 'contribution', EVERY_REQUEST);
        const refresh = await openBrokerDetail(page, brokerId, 'posizioni');
        const panel = page.getByTestId('positions-panel');
        await waitForSettled(panel, ROUND_TRIP_MS);
        await expectRecordSeesReports(page);
        await expectRequests(page, contribution, 0, 'precondition: no contribution asked before the Performance view is chosen');
        const pausedAt = await pauseClock(page);

        await choosePerformance(panel);
        await expectNotAskedAgainAtOnce(page, contribution, pausedAt, "the broker's contribution");
        expect(contribution.seen[0].body.broker_ids, "the contribution of a broker's page asks that broker alone").toEqual([brokerId]);
        await expectBoundedRetries(page, contribution, "the broker's contribution");

        // A period change is another scope: asked again, once — the clock still frozen.
        const sixMonths = page.getByTestId('date-preset-6m');
        await expect(sixMonths, "precondition: 6M is a change of period (the broker's page opens on 3M)").toHaveAttribute('data-active', 'false');
        await sixMonths.click();
        await expect(sixMonths).toHaveAttribute('data-active', 'true');
        await expectRequests(page, contribution, MAX_REQUESTS + 1, "the broker's contribution: a period change asks it again");
        await expectIdle(refresh, 'the overview of the new period is back, and the Refresh button still waits');
        await expectRequests(page, contribution, MAX_REQUESTS + 1, "the broker's contribution: asked once for the new period, its overview back");
        expectNewPeriod(contribution, MAX_REQUESTS, "the broker's contribution after the period change");
    });

    test('Broker detail, P&L candles: a period change while the candles request is in flight asks the candles of the new period once that request has failed, and draws them (Y-24 review)', async ({page}) => {
        const brokerId = await brokerIdByName(page, BROKER_WITH_HOLDINGS);
        // The first candles request is held, then answered 500; the next ones go to the backend.
        const candles = await preparePage(page, 'candles', 1, 1);
        try {
            const refresh = await openBrokerDetail(page, brokerId, 'panoramica');
            await expectRecordSeesReports(page);
            await expectRequests(page, candles, 0, 'precondition: no candles asked before the candles view is chosen');
            const chart = page.getByTestId('growth-chart');
            // Frozen throughout: nothing here waits on a timer, and no timer may ask behind the case's back.
            await pauseClock(page);

            await chooseCandles(chart);
            await expectHeld(page, candles, 'the candles of the period on screen');

            // The period changes while that request is in flight, and the overview of the new period comes back.
            const sixMonths = page.getByTestId('date-preset-6m');
            await expect(sixMonths, "precondition: 6M is a change of period (the broker's page opens on 3M)").toHaveAttribute('data-active', 'false');
            await sixMonths.click();
            await expect(sixMonths).toHaveAttribute('data-active', 'true');
            await expectIdle(refresh, 'the overview of the new period is back, and the Refresh button still waits');
            expect(candles.waiting(), 'precondition: the candles request of the old period is still held').toBe(1);

            // The request of the old period fails, and its page has moved on: the new period's candles are asked.
            candles.release();
            await expectLanded(page, candles, 1, 'the held candles request of the old period, answered 500');
            await expectRequests(page, candles, 2, "the candles of the new period: asked once the old period's request has failed (Y-24 review, (f))");
            expect(
                candles.seen.map((answered) => answered.failed),
                'the stub fails the held request only, and lets the next through',
            ).toEqual([true, false]);
            expectNewPeriod(candles, 1, 'the candles asked after the period change');
            await expect.poll(() => candleBodies(chart), {message: 'the candles of the new period never reached the chart', timeout: ROUND_TRIP_MS}).toBeGreaterThan(0);
            await expectRequests(page, candles, 2, 'the candles of the new period: drawn, and not asked again');
        } finally {
            candles.release();
        }
    });

    test('Broker detail, P&L candles: leaving Candles and coming back while the request is in flight, its failure is still asked again 2 s later, once (Y-24 review)', async ({page}) => {
        const brokerId = await brokerIdByName(page, BROKER_WITH_HOLDINGS);
        // Every candles request fails; the first is held until the chart has left Candles and come back.
        const candles = await preparePage(page, 'candles', EVERY_REQUEST, 1);
        try {
            await openBrokerDetail(page, brokerId, 'panoramica');
            await expectRecordSeesReports(page);
            await expectRequests(page, candles, 0, 'precondition: no candles asked before the candles view is chosen');
            const chart = page.getByTestId('growth-chart');
            const pausedAt = await pauseClock(page);

            await chooseCandles(chart);
            await expectHeld(page, candles, 'the candles');

            // Away from Candles and back, the request in flight: the chart's effect runs on both moves.
            await leaveCandlesAndComeBack(chart);
            await expectHeld(page, candles, 'the candles, the chart back on Candles: still the one request, held');

            candles.release();
            await expectNotAskedAgainAtOnce(page, candles, pausedAt, 'the candles, failed after the chart left Candles and came back');
            const [firstDelay] = RETRY_DELAYS_MS;
            await runClock(page, firstDelay - 1);
            await expectRequests(page, candles, 1, `the candles: ${firstDelay - 1} ms after the failure, not asked again yet`);
            await runClock(page, 1);
            await expectRequests(page, candles, 2, `the candles: ${firstDelay} ms after the failure, asked again exactly once, though the chart's effect last ran while the request was in flight (Y-24 review, (g))`);
            expect(scopeOf(candles.seen[1].body), 'the retry asks the scope that failed').toBe(scopeOf(candles.seen[0].body));
        } finally {
            candles.release();
        }
    });
});
