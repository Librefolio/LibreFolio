/**
 * Live prices pause and resume — E2E (Z1, F26, decision 31).
 *
 * The Assets pages ask `POST /api/v1/assets/prices/current` for live prices on a cadence: the list every 60 s, the
 * detail every 30 s with ONE request per tick (the detail page used to run two loops). The cadence pauses while the
 * tab is hidden or after 2 minutes without input (pointer, keyboard, wheel, touch) and resumes by itself — on the
 * next input, or on the return to the tab — with one request at once when a whole interval has gone by. While it is
 * paused for inactivity the page shows a pill (`live-updates-status`); the page root publishes the poller state as
 * `data-live-updates` (`running | paused-idle | paused-hidden | stopped`). A range that ends in the past asks for
 * nothing at all.
 *
 * How time is driven. Minutes of cadence can be neither waited for nor guessed:
 *   1. `page.clock.install()` before the page under test opens, so that its timers are the clock's. Until it is
 *      paused the clock flows with real time, so the page loads exactly as it would without it;
 *   2. once the page has sent the request it sends when it opens, `pauseAt` freezes the page clock two seconds
 *      ahead. From there only the test moves time, with `runFor`, which fires every timer in between, in order;
 *   3. every request is stamped by an init script with the page's own clock (`recordLiveRequests`), so each window
 *      is measured from the request that opened it, to the millisecond, however long the browser took to load or to
 *      answer. The count read in the page right after `runFor` is exact — a request leaves inside the timer that
 *      `runFor` fired — and the stub's own count must agree with it.
 * Before time moves past the next tick, every answer must be back in the page: a run still in flight at a tick is
 * skipped by design (no overlap), and that skip is not what these tests are about. A silent window is proven twice:
 * by the exact count read right after it, and by the exact count after the next expected request (a late request
 * from the silent window would show up there as one too many). If a page timer throws while `runFor` runs, the clock
 * rethrows it once time has advanced: it is attached to the test as a `page timer error` annotation, not swallowed,
 * and not mistaken for a verdict on the cadence.
 *
 * Playwright's own waits run on the browser's native timers (the clock hands them to the injected script before it
 * replaces them), so locator assertions keep retrying while the page clock is frozen.
 *
 * Input. Activity is what the page hears on `window`, so during an idle window nothing may touch the page — a click
 * is also a pointer move. The pointer is parked in a corner of the page left behind before the navigation, and the
 * only input a test makes is a `page.mouse.move`. A hidden tab has no Playwright API: `visibilityState` is redefined
 * on the document and `visibilitychange` dispatched, which is exactly what the page listens to.
 *
 * Offline and read-only. `POST /assets/prices/current` asks the live providers and writes today's candle; here it is
 * answered in the browser — with a schema-valid empty result, in (g) and (h) with a failure or a provider pause, in (j)
 * with a quote — so nothing reaches a third party and nothing is written. The tests create nothing, so there is nothing
 * to clean up (the routes go with the page).
 *
 * Reduced motion. Long asset names scroll as a marquee driven by `requestAnimationFrame`, a loop that never ends while
 * a name overflows; under the clock every frame is a timer `runFor` must fire, thousands per minute of page time.
 * Reduced motion stops the marquee at the source and changes nothing these tests look at.
 *
 * Desktop only: the cadence does not depend on the viewport.
 *
 * Order of assertions: in every test the request counts come first, the published state and the pill after, so a red
 * names the behaviour (a request that left when it should not have, or one that did not) before the attribute.
 *
 * Failures and provider pauses (Z7c-1; decision 34, D-Z7-1, D-Z7-2). A poll that fails pushes the next one away: after
 * k failures in a row the next request waits `interval × 2^k`, never more than 10 minutes, and the first success brings
 * the interval back. An answer in which every asset asked about is `RATE_LIMITED` (HTTP 200, each with its last stored
 * price and `retry_after`, the seconds of the provider's pause) holds the next request until the pause is over,
 * counted from the answer. Neither shows anything new: the state stays `running`, the pill hidden.
 *   (g) the endpoint answers HTTP 500 on the detail page: the requests leave 60, 120, 240, 480, 600 and 600 s apart —
 *       four doublings of 30 s, then the cap twice. The detail page rather than the list: the list would save one
 *       gap (34 minutes of page clock against 35, a handful of clock steps), but it loads every asset and its prices
 *       where the detail loads one, and (h) already holds the list — on the detail page, each page's new lines are
 *       seen by one test.
 *   (h) every asset of the list is answered `RATE_LIMITED` with `retry_after` 300: no request for 300 s after the
 *       answer, then one. The page reads the pause when the answer lands, so the window is measured from the answer:
 *       the record also stamps, on the page clock, when each answer came back (`settledAt`).
 * Both windows outlast the idle pause (2 minutes), so in (g) and (h) the user stays there: a pointer move onto the
 * page at least every 90 s of page clock, alternating between two points so that every move is a move
 * (`runClockWithUserTo`). An input while running asks for nothing by itself — (a) proves it — so the moves add no
 * request. The pause in (h) is the stub's answer, never a real pause of a provider: that would be a state of the
 * lane's shared backend, seen by every other test (X6).
 *
 * The user's calendar (Z-3). «Today» is a day of the user's calendar, so a range is live when it ends today there,
 * wherever the user is, and only then. A page that compares the end of its range with the UTC date is a day off for
 * part of every day: west of Greenwich in the evening the UTC date is already tomorrow — 21:00 in New York is 01:00 UTC
 * of the next day — and a range ending today reads as past (no live request, the summary on the chart's last close);
 * east of Greenwich just after midnight the UTC date is still yesterday — 00:30 in Rome is 22:30 UTC of the day before —
 * and a range that ended yesterday reads as live. Each case sets the browser's time zone and starts its clock at such an
 * instant: `prepareLivePage` passes the instant to its one `page.clock.install`, no test installs a second clock.
 *   (i) /assets and (j) /assets/{id}, America/New_York at 21:00 of 16 October 2026, on a range that ends `max` — which
 *       the page resolves on its own clock, to the 16th: a live request when the page opens, and one more an interval
 *       later; on the detail page the summary shows the quote the stub answers, not the chart's last close.
 *   (k) /assets and (l) /assets/{id}, Europe/Rome at 00:30 of 17 October 2026, on a range that ends the 16th: no live
 *       request over the load and 65 s more, the page `stopped`.
 * Before any request is counted, the page's calendar is read in the page — its time zone, its local date, its UTC date
 * —, because the two dates agree for most of the day: a premise that does not hold fails as such, instead of passing as
 * a green that proves nothing. Then a presence barrier (the page shows the asset), so that a count of live requests is
 * about this page.
 */

import {expect, test} from '../fixtures/playwright';
import type {Locator, Page} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetDetailPage, goToAssetsPage} from './assets-helpers';

/** Decision 31, written out rather than imported: the spec pins the numbers that were decided, it does not follow the code. */
const LIST_INTERVAL_MS = 60_000;
const DETAIL_INTERVAL_MS = 30_000;
const IDLE_MS = 120_000;
/** Half-width of the window around each expected request: room for the page's own scheduling, far below any interval. */
const SLACK_MS = 1_000;
/** `pauseAt` refuses a time the page clock has already passed: it is frozen this far ahead of where it was read. */
const PAUSE_AHEAD_MS = 2_000;
/** Login, one page load and a few dozen clock steps: the page-clock minutes themselves cost little real time. */
const TEST_TIMEOUT_MS = 90_000;
/** D-Z7-1, written out: after k failures in a row the next request waits `interval × 2^k`, at most 10 minutes. */
const MAX_BACKOFF_MS = 600_000;
/** What that gives on the detail page (30 s) when every request fails: four doublings, then the cap, held. */
const DETAIL_FAILURE_GAPS_MS = [60_000, 120_000, 240_000, 480_000, MAX_BACKOFF_MS, MAX_BACKOFF_MS];
/** The provider pause of (h): `retry_after`, in seconds, as the API answers it. */
const PROVIDER_PAUSE_S = 300;
/** Input at least this often, in page time, keeps the idle pause (2 minutes) away in the long windows of (g) and (h). */
const ACTIVE_STEP_MS = 90_000;
/** (g) runs 35 minutes of page clock in steps of at most 90 s: some forty clock steps where the others take a dozen. */
const LONG_TEST_TIMEOUT_MS = 150_000;

const LIVE_PRICES_ROUTE = '**/api/v1/assets/prices/current*';
const LIVE_PRICES_PATH = '/api/v1/assets/prices/current';
/** The suite's known asset with a provider (populate_mock_data.populate_assets), found by name and provider, never by position. */
const SEEDED_PRICED_ASSET = {displayName: 'Apple Inc.', providerCode: 'yfinance'};
/** A range that ends long before today. */
const PAST_RANGE = {start: '2024-01-02', end: '2024-06-28'};
/**
 * Z-3: a moment where the user's date and the UTC date differ. Written as an instant with its offset, so that the page
 * clock starts there whatever the time zone of the machine that runs the suite.
 */
interface CalendarMoment {
    timeZone: string;
    at: string;
    /** The date on the user's calendar. */
    localDate: string;
    /** The UTC date: the one `toISOString()` gives. */
    utcDate: string;
}
/** West of Greenwich: 21:00 on 16 October 2026 in New York (EDT, UTC−4) is 01:00 UTC on the 17th. */
const NEW_YORK_EVENING: CalendarMoment = {timeZone: 'America/New_York', at: '2026-10-16T21:00:00-04:00', localDate: '2026-10-16', utcDate: '2026-10-17'};
/** East of Greenwich: 00:30 on 17 October 2026 in Rome (CEST, UTC+2) is 22:30 UTC on the 16th. */
const ROME_AFTER_MIDNIGHT: CalendarMoment = {timeZone: 'Europe/Rome', at: '2026-10-17T00:30:00+02:00', localDate: '2026-10-17', utcDate: '2026-10-16'};
/** In New York, a range that ends today: `max` is resolved by the page itself, on its own clock. Three months, as the default range. */
const RANGE_ENDING_TODAY = 'start=2026-07-16&end=max';
/** In Rome, a range that ended yesterday: the 16th, which is still today in UTC. */
const RANGE_ENDING_YESTERDAY = 'start=2026-07-16&end=2026-10-16';
/** (j): the quote the stub answers, in the currency of the seeded asset (Apple, USD). */
const LIVE_QUOTE = {value: '123.45', currency: 'USD'} as const;
/** How the summary writes it: two decimals, a dot or a comma by the interface language (`formatFixed`). */
const LIVE_QUOTE_SHOWN = /^\s*123[.,]45\s*$/;

/** What the stub has seen. */
interface LiveTraffic {
    /** Requests answered, counted once the answer has been handed back to the browser. */
    served: number;
    /** The asset ids each request asked about, in order. */
    askedFor: number[][];
}

/** What the page itself has seen, read from the init script's record. */
interface LiveRecord {
    /** The page-clock time each request left at. */
    sentAt: number[];
    /** How many of them are back in the page (load, error or abort). */
    settled: number;
    /** The page-clock time each of them came back at, in the order they came back. */
    settledAt: number[];
}

interface LiveSession {
    traffic: LiveTraffic;
    /** Page-clock time of the request the page sent when it opened. */
    opened: number;
}

/** How the stub answers a live-price request. */
type LiveAnswer =
    /** HTTP 200 and no item: a healthy endpoint, (a)–(f). */
    | {kind: 'empty'}
    /** HTTP 500 and FastAPI's error body: every poll fails, (g). */
    | {kind: 'server-error'}
    /** HTTP 200, every asset asked about paused — its last stored price, RATE_LIMITED, the seconds of the pause — (h). */
    | {kind: 'rate-limited'; retryAfterSeconds: number}
    /** HTTP 200, every asset asked about quoted `value` by its provider, dated `asOf`: (j). */
    | {kind: 'quote'; value: string; currency: string; asOf: string};

/** The asset ids a live-price request asks about: its body is a JSON array of ids. Anything else asks about none. */
function askedIds(body: string | null): number[] {
    try {
        const ids: unknown = JSON.parse(body ?? 'null');
        return Array.isArray(ids) ? ids.filter((id): id is number => typeof id === 'number') : [];
    } catch {
        return [];
    }
}

/** Answer every live-price request in the browser as `answer` says — by default a schema-valid empty result — and count them. */
async function stubLivePrices(page: Page, answer: LiveAnswer = {kind: 'empty'}): Promise<LiveTraffic> {
    const traffic: LiveTraffic = {served: 0, askedFor: []};
    await page.route(LIVE_PRICES_ROUTE, async (route) => {
        const asked = askedIds(route.request().postData());
        traffic.askedFor.push(asked);
        if (answer.kind === 'server-error') {
            await route.fulfill({status: 500, json: {detail: 'Internal Server Error'}});
        } else if (answer.kind === 'rate-limited') {
            // What the backend answers for a paused provider (price_query.get_current_prices_bulk): HTTP 200, the last
            // stored price from the database, the error code and the seconds left of the pause.
            const results = asked.map((assetId) => ({asset_id: assetId, value: '100.00', currency: 'EUR', as_of_date: null, source: 'db:last_known', error: null, error_code: 'RATE_LIMITED', retry_after: answer.retryAfterSeconds}));
            await route.fulfill({json: {results, success_count: results.length, errors: []}});
        } else if (answer.kind === 'quote') {
            // A provider's quote, the shape of `FACurrentPriceItem`: nothing written, nothing paused.
            const results = asked.map((assetId) => ({asset_id: assetId, value: answer.value, currency: answer.currency, as_of_date: answer.asOf, source: 'provider:spec-stub', error: null, error_code: null, retry_after: null}));
            await route.fulfill({json: {results, success_count: results.length, errors: []}});
        } else {
            await route.fulfill({json: {results: [], success_count: 0, errors: []}});
        }
        traffic.served += 1;
    });
    return traffic;
}

/**
 * Stamp every live-price request, inside the page, with the page's own clock — the one this spec drives — when it leaves
 * and when its answer is back. XHR is what the pages use today (axios); `fetch` is covered too, so that a change of
 * transport cannot hide a request.
 */
async function recordLiveRequests(page: Page): Promise<void> {
    await page.addInitScript((path: string) => {
        const record: {sentAt: number[]; settled: number; settledAt: number[]} = {sentAt: [], settled: 0, settledAt: []};
        Object.defineProperty(window, '__lfSpecLivePrices', {value: record});
        const isLive = (url: string): boolean => {
            try {
                return new URL(url, window.location.href).pathname === path;
            } catch {
                return false;
            }
        };
        const tracked = new WeakSet<XMLHttpRequest>();
        const nativeOpen = XMLHttpRequest.prototype.open;
        const nativeSend = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.open = function (this: XMLHttpRequest, ...args: unknown[]) {
            if (isLive(String(args[1]))) tracked.add(this);
            else tracked.delete(this);
            return Reflect.apply(nativeOpen, this, args);
        } as XMLHttpRequest['open'];
        XMLHttpRequest.prototype.send = function (this: XMLHttpRequest, ...args: unknown[]) {
            if (tracked.has(this)) {
                record.sentAt.push(Date.now());
                this.addEventListener('loadend', () => {
                    record.settled += 1;
                    record.settledAt.push(Date.now());
                });
            }
            return Reflect.apply(nativeSend, this, args);
        } as XMLHttpRequest['send'];
        const nativeFetch = window.fetch;
        window.fetch = function (input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
            if (!isLive(input instanceof Request ? input.url : String(input))) return nativeFetch.call(window, input, init);
            record.sentAt.push(Date.now());
            return nativeFetch.call(window, input, init).finally(() => {
                record.settled += 1;
                record.settledAt.push(Date.now());
            });
        };
    }, LIVE_PRICES_PATH);
}

async function liveRecord(page: Page): Promise<LiveRecord> {
    return page.evaluate(() => {
        const record = (window as unknown as {__lfSpecLivePrices?: {sentAt: number[]; settled: number; settledAt: number[]}}).__lfSpecLivePrices;
        if (!record) throw new Error('No live-price record in this document: recordLiveRequests() must be installed before the navigation');
        return {sentAt: [...record.sentAt], settled: record.settled, settledAt: [...record.settledAt]};
    });
}

async function pageNow(page: Page): Promise<number> {
    return page.evaluate(() => Date.now());
}

function seconds(at: number, origin: number): string {
    return `${at >= origin ? '+' : '-'}${(Math.abs(at - origin) / 1000).toFixed(1)} s`;
}

function offsets(times: number[], origin: number): string {
    return times.length === 0 ? 'none' : times.map((at) => seconds(at, origin)).join(', ');
}

/**
 * Exactly `expected` live requests so far, read in the page; the stub answered each of them and every answer is back
 * in the page. Returns their page-clock send times.
 */
async function expectLiveRequests(page: Page, traffic: LiveTraffic, expected: number, what: string, origin?: number): Promise<number[]> {
    const {sentAt} = await liveRecord(page);
    expect(sentAt, `${what} — the page sent live requests at ${offsets(sentAt, origin ?? sentAt[0] ?? 0)}`).toHaveLength(expected);
    await expect.poll(() => traffic.served, {message: `${what} — the stub answered every live request the page sent`, timeout: 10_000}).toBe(expected);
    await expect.poll(async () => (await liveRecord(page)).settled, {message: `${what} — every answer is back in the page before its clock moves on`, timeout: 10_000}).toBe(expected);
    return sentAt;
}

/** Freeze the page clock a little ahead of where it is; returns the page time it froze at. */
async function pauseClock(page: Page): Promise<number> {
    const at = (await pageNow(page)) + PAUSE_AHEAD_MS;
    await page.clock.pauseAt(at);
    expect(await pageNow(page), 'the page clock froze where it was asked to').toBe(at);
    return at;
}

/** Run the frozen page clock to `target`, firing every timer on the way. */
async function runClockTo(page: Page, target: number): Promise<void> {
    const now = await pageNow(page);
    expect(target, 'the spec only moves the page clock forward').toBeGreaterThanOrEqual(now);
    try {
        await page.clock.runFor(target - now);
    } catch (error) {
        // The clock rethrows the first exception a page timer threw, once every timer up to `target` has run. A page
        // error is not the subject of this spec: it is reported with the test, never swallowed — and the clock must
        // still have reached its target, or what follows would be measured on the wrong time.
        const firstLine = String(error).split('\n')[0];
        test.info().annotations.push({type: 'page timer error', description: firstLine});
        expect(await pageNow(page), `the page clock reached its target although a page timer threw: ${firstLine}`).toBe(target);
    }
}

/**
 * Everything that must be in place before the page under test opens: the stub, the page-side record, reduced motion,
 * the pointer parked, the clock installed (flowing until `pauseClock`) — from the real time, or from `clockAt` for a test
 * that needs another instant (Z-3). This is the test's one install: a time is passed in here, never installed twice.
 */
async function prepareLivePage(page: Page, answer: LiveAnswer = {kind: 'empty'}, clockAt?: string): Promise<LiveTraffic> {
    const traffic = await stubLivePrices(page, answer);
    await recordLiveRequests(page);
    await page.emulateMedia({reducedMotion: 'reduce'});
    // Parked in a corner of the page being left: the page under test must hear no input but the ones a test makes.
    await page.mouse.move(1, 1);
    // Without `clockAt` no time is given, and the clock starts at the real time, as it always did.
    await page.clock.install(clockAt === undefined ? {} : {time: clockAt});
    return traffic;
}

/** The page has sent the request it sends when it opens: freeze the clock and prove it sent that one only. */
async function freezeAfterOpening(page: Page, traffic: LiveTraffic, interval: number): Promise<LiveSession> {
    await expect.poll(async () => (await liveRecord(page)).sentAt.length, {message: 'the page asks for live prices once when it opens', timeout: 15_000}).toBeGreaterThan(0);
    const pausedAt = await pauseClock(page);
    const [opened] = await expectLiveRequests(page, traffic, 1, 'exactly one live request when the page opens');
    expect(pausedAt - opened, `the clock froze ${((pausedAt - opened) / 1000).toFixed(1)} s after the opening request: too late to watch the first ${interval / 1000} s window`).toBeLessThan(interval - SLACK_MS);
    return {traffic, opened};
}

async function openList(page: Page, answer?: LiveAnswer): Promise<LiveSession> {
    const traffic = await prepareLivePage(page, answer);
    await goToAssetsPage(page);
    return freezeAfterOpening(page, traffic, LIST_INTERVAL_MS);
}

async function openDetail(page: Page, answer?: LiveAnswer): Promise<LiveSession> {
    const assetId = await seededPricedAssetId(page);
    const traffic = await prepareLivePage(page, answer);
    await goToAssetDetailPage(page, String(assetId));
    return freezeAfterOpening(page, traffic, DETAIL_INTERVAL_MS);
}

async function seededPricedAssetId(page: Page): Promise<number> {
    const response = await page.request.get(`/api/v1/assets/query?search=${encodeURIComponent(SEEDED_PRICED_ASSET.displayName)}`);
    expect(response.ok(), `asset lookup failed (HTTP ${response.status()})`).toBe(true);
    const matches = ((await response.json()) as Array<{id: number; display_name: string; provider_code: string | null}>).filter((asset) => asset.display_name === SEEDED_PRICED_ASSET.displayName && asset.provider_code === SEEDED_PRICED_ASSET.providerCode);
    expect(matches, `${SEEDED_PRICED_ASSET.displayName} (${SEEDED_PRICED_ASSET.providerCode}) must be one seeded asset ${TEST_USER.username} can read — populate_mock_data.populate_assets`).toHaveLength(1);
    return matches[0].id;
}

/**
 * The page's own calendar, read in the page off its clock: its time zone, today's date there, and the UTC date — the one
 * a page reading `toISOString()` takes for today.
 */
async function pageCalendar(page: Page): Promise<{timeZone: string; localDate: string; utcDate: string}> {
    return page.evaluate(() => {
        const now = new Date();
        const pad = (value: number): string => String(value).padStart(2, '0');
        return {
            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            localDate: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
            utcDate: now.toISOString().slice(0, 10),
        };
    });
}

/**
 * Z-3: open `target` (a path with its query) with the page clock started at `moment` — passed through to
 * `prepareLivePage`'s one install —, and wait for it to settle. Then, before any request is counted, the premise — the
 * page's own calendar is `moment`'s, its two dates apart — and a presence barrier, `present`: a count of live requests
 * can then be about neither the wrong day nor a page that is not there.
 */
async function openAtMoment(page: Page, moment: CalendarMoment, target: string, root: Locator, present: Locator, answer?: LiveAnswer): Promise<LiveTraffic> {
    const traffic = await prepareLivePage(page, answer, moment.at);
    await navigateTo(page, target);
    await waitForSettled(root, 20_000);
    expect(await pageCalendar(page), `premise: the page lives at ${moment.at}, the ${moment.localDate} in ${moment.timeZone} and the ${moment.utcDate} in UTC`).toEqual({
        timeZone: moment.timeZone,
        localDate: moment.localDate,
        utcDate: moment.utcDate,
    });
    await expect(present, `presence barrier: ${target} shows ${SEEDED_PRICED_ASSET.displayName}`).toBeVisible();
    return traffic;
}

/** Z-3, west: `path` on RANGE_ENDING_TODAY at NEW_YORK_EVENING asks for a live price when it opens; then frozen as `openList`/`openDetail` do. */
async function openOnUserCalendar(page: Page, path: string, root: Locator, present: Locator, interval: number, answer?: LiveAnswer): Promise<LiveSession> {
    const traffic = await openAtMoment(page, NEW_YORK_EVENING, `${path}?${RANGE_ENDING_TODAY}`, root, present, answer);
    await expect
        .poll(async () => (await liveRecord(page)).sentAt.length, {
            message: `Z-3: the range ends ${NEW_YORK_EVENING.localDate}, today on the user's calendar though already ${NEW_YORK_EVENING.utcDate} in UTC: ${path} must ask for a live price when it opens`,
            timeout: 15_000,
        })
        .toBeGreaterThan(0);
    return freezeAfterOpening(page, traffic, interval);
}

/** Z-3, east: the page, open at ROME_AFTER_MIDNIGHT on RANGE_ENDING_YESTERDAY, asks for nothing over its load and 65 s more, and says it is stopped. */
async function expectNoLiveRequestOnYesterday(page: Page, traffic: LiveTraffic, root: Locator): Promise<void> {
    const pausedAt = await pauseClock(page);
    await runClockTo(page, pausedAt + 65_000);
    await expectLiveRequests(page, traffic, 0, `Z-3: the range ended ${ROME_AFTER_MIDNIGHT.utcDate}, yesterday on the user's calendar though still today in UTC: no live request over the load and 65 s more`, pausedAt);
    await expect(root).toHaveAttribute('data-live-updates', 'stopped');
    await expect(pill(root)).toBeHidden();
}

/**
 * The next live request leaves one `interval` after `from`, and not before: none by `from + interval - SLACK_MS`,
 * exactly one more by `from + interval + SLACK_MS`. Returns the page time it left at.
 */
async function expectNextTick(page: Page, session: LiveSession, from: number, interval: number, sentSoFar: number): Promise<number> {
    const early = from + interval - SLACK_MS;
    const late = from + interval + SLACK_MS;
    await runClockTo(page, early);
    await expectLiveRequests(page, session.traffic, sentSoFar, `no live request before ${seconds(early, session.opened)}`, session.opened);
    await runClockTo(page, late);
    const sentAt = await expectLiveRequests(page, session.traffic, sentSoFar + 1, `exactly one live request between ${seconds(early, session.opened)} and ${seconds(late, session.opened)}`, session.opened);
    return sentAt[sentSoFar];
}

/** No live request until `until` (page clock). */
async function expectQuietUntil(page: Page, session: LiveSession, until: number, sentSoFar: number, what: string): Promise<void> {
    await runClockTo(page, until);
    await expectLiveRequests(page, session.traffic, sentSoFar, `${what} (page clock at ${seconds(until, session.opened)})`, session.opened);
}

/** One user input: a pointer move onto the page under test, away from where the pointer was parked. */
async function moveThePointer(page: Page, root: Locator): Promise<void> {
    const box = await root.boundingBox();
    if (!box) throw new Error('the page under test has no box to move the pointer onto');
    await page.mouse.move(box.x + 8, box.y + 8);
}

/** What the browser does when the tab changes visibility: the properties first, then the event on the document. */
async function setTabVisibility(page: Page, state: 'hidden' | 'visible'): Promise<void> {
    await page.evaluate((next) => {
        Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => next});
        Object.defineProperty(document, 'hidden', {configurable: true, get: () => next === 'hidden'});
        document.dispatchEvent(new Event('visibilitychange'));
    }, state);
}

/** How many pointer moves `runClockWithUserTo` has made on each page, so that the next one lands somewhere else. */
const pointerMoves = new WeakMap<Page, number>();

/**
 * Run the frozen page clock to `target` with the user there: a pointer move onto the page under test, then at most
 * ACTIVE_STEP_MS of page time, and again. The first move comes before the clock moves at all, and the moves alternate
 * between two points, so that each one is a move the page hears.
 */
async function runClockWithUserTo(page: Page, root: Locator, target: number): Promise<void> {
    const box = await root.boundingBox();
    if (!box) throw new Error('the page under test has no box to move the pointer onto');
    for (let now = await pageNow(page); now < target; now = await pageNow(page)) {
        const moves = pointerMoves.get(page) ?? 0;
        pointerMoves.set(page, moves + 1);
        await page.mouse.move(box.x + 8 + (moves % 2) * 8, box.y + 8);
        await runClockTo(page, Math.min(target, now + ACTIVE_STEP_MS));
    }
}

/**
 * With the user there, the next live request leaves `gap` after `from`, and not before: none by `from + gap - SLACK_MS`,
 * exactly one more by `from + gap + SLACK_MS`. Returns the page time it left at.
 */
async function expectNextRequestWithUser(page: Page, session: LiveSession, root: Locator, from: number, gap: number, sentSoFar: number): Promise<number> {
    const early = from + gap - SLACK_MS;
    const late = from + gap + SLACK_MS;
    await runClockWithUserTo(page, root, early);
    await expectLiveRequests(page, session.traffic, sentSoFar, `no live request before ${seconds(early, session.opened)}, ${gap / 1000} s after the one at ${seconds(from, session.opened)}`, session.opened);
    await runClockWithUserTo(page, root, late);
    const sentAt = await expectLiveRequests(page, session.traffic, sentSoFar + 1, `exactly one live request between ${seconds(early, session.opened)} and ${seconds(late, session.opened)}`, session.opened);
    return sentAt[sentSoFar];
}

const listRoot = (page: Page): Locator => page.getByTestId('assets-page');
const detailRoot = (page: Page): Locator => page.getByTestId('asset-detail-page');
const pill = (root: Locator): Locator => root.getByTestId('live-updates-status');

test.beforeEach(async ({page}, testInfo) => {
    test.skip(testInfo.project.name !== 'desktop', 'Desktop only: the cadence and its pauses do not depend on the viewport');
    // Set before the login, which shares the budget: minutes of page clock cost little real time, the login and the
    // first load cost the most.
    test.setTimeout(TEST_TIMEOUT_MS);
    await login(page, TEST_USER);
});

test.describe('/assets — live prices every 60 s, paused when nobody is there', () => {
    test('(a) asks once every 60 s while the user is around', async ({page}) => {
        const session = await openList(page);
        const root = listRoot(page);

        const first = await expectNextTick(page, session, session.opened, LIST_INTERVAL_MS, 1);
        // The user is there: an input while running asks for nothing by itself (a run inside the input would show
        // here, a run from a timer in the next window), and it keeps the cadence going past the two minutes counted
        // from the opening.
        await moveThePointer(page, root);
        await expectLiveRequests(page, session.traffic, 2, 'an input while running asks for nothing by itself', session.opened);
        await expectNextTick(page, session, first, LIST_INTERVAL_MS, 2);

        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();
    });

    test('(b) pauses after 2 minutes without input, says so, and asks again at once on the next pointer move', async ({page}) => {
        const session = await openList(page);
        const root = listRoot(page);

        await expectNextTick(page, session, session.opened, LIST_INTERVAL_MS, 1);
        await expectQuietUntil(page, session, session.opened + IDLE_MS - 5_000, 2, 'nothing between the 60 s request and the idle threshold');
        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();

        // 120 s without input: the request due there does not leave, nor any other for two more minutes.
        await expectQuietUntil(page, session, session.opened + IDLE_MS + 2 * LIST_INTERVAL_MS + SLACK_MS, 2, 'no live request for two minutes after the idle threshold');
        await expect(root).toHaveAttribute('data-live-updates', 'paused-idle');
        await expect(pill(root)).toBeVisible();
        await expect(pill(root)).toHaveAttribute('data-state', 'paused-idle');

        const movedAt = await pageNow(page);
        await moveThePointer(page, root);
        await runClockTo(page, movedAt + SLACK_MS);
        await expectLiveRequests(page, session.traffic, 3, `exactly one live request at once on the pointer move at ${seconds(movedAt, session.opened)}`, session.opened);
        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();
    });

    test('(c) pauses while the tab is hidden and asks again at once when it is visible', async ({page}) => {
        const session = await openList(page);
        const root = listRoot(page);

        await setTabVisibility(page, 'hidden');
        await expectQuietUntil(page, session, session.opened + 2 * LIST_INTERVAL_MS + 30_000, 1, 'no live request while the tab is hidden');
        await expect(root).toHaveAttribute('data-live-updates', 'paused-hidden');
        await expect(pill(root)).toBeHidden();

        const shownAt = await pageNow(page);
        await setTabVisibility(page, 'visible');
        await runClockTo(page, shownAt + SLACK_MS);
        const sentAt = await expectLiveRequests(page, session.traffic, 2, `exactly one live request at once on the return to the tab at ${seconds(shownAt, session.opened)}`, session.opened);
        // The cadence starts again from that request.
        await expectNextTick(page, session, sentAt[1], LIST_INTERVAL_MS, 2);

        await expect(root).toHaveAttribute('data-live-updates', 'running');
    });
});

test.describe('/assets/{id} — one live request every 30 s, paused when nobody is there, none on a past range', () => {
    test('(d) sends exactly one live request per 30 s window', async ({page}) => {
        const session = await openDetail(page);
        const root = detailRoot(page);

        let tick = session.opened;
        for (let sent = 1; sent <= 3; sent++) tick = await expectNextTick(page, session, tick, DETAIL_INTERVAL_MS, sent);

        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();
    });

    test('(e) pauses after 2 minutes without input, says so, and asks again at once on the next pointer move', async ({page}) => {
        const session = await openDetail(page);
        const root = detailRoot(page);

        let tick = session.opened;
        for (let sent = 1; sent <= 3; sent++) tick = await expectNextTick(page, session, tick, DETAIL_INTERVAL_MS, sent);
        await expectQuietUntil(page, session, session.opened + IDLE_MS - 5_000, 4, 'nothing between the 90 s request and the idle threshold');
        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();

        // 120 s without input: the request due there does not leave, nor any other for two more minutes.
        await expectQuietUntil(page, session, session.opened + IDLE_MS + 4 * DETAIL_INTERVAL_MS + SLACK_MS, 4, 'no live request for two minutes after the idle threshold');
        await expect(root).toHaveAttribute('data-live-updates', 'paused-idle');
        await expect(pill(root)).toBeVisible();
        await expect(pill(root)).toHaveAttribute('data-state', 'paused-idle');

        const movedAt = await pageNow(page);
        await moveThePointer(page, root);
        await runClockTo(page, movedAt + SLACK_MS);
        await expectLiveRequests(page, session.traffic, 5, `exactly one live request at once on the pointer move at ${seconds(movedAt, session.opened)}`, session.opened);
        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();
    });

    test('(f) never asks for a live price on a range that ends in the past', async ({page}) => {
        const assetId = await seededPricedAssetId(page);
        const traffic = await prepareLivePage(page);
        await navigateTo(page, `/assets/${assetId}?start=${PAST_RANGE.start}&end=${PAST_RANGE.end}`);
        const root = detailRoot(page);
        await waitForSettled(root, 20_000);
        // Presence barrier: the asset is on screen, so "no request" cannot mean "no page".
        await expect(root.getByTestId('asset-detail-info')).toBeVisible();

        const pausedAt = await pauseClock(page);
        await runClockTo(page, pausedAt + 65_000);
        await expectLiveRequests(page, traffic, 0, `no live request on ${PAST_RANGE.start}…${PAST_RANGE.end}, over the load and 65 s more`, pausedAt);

        await expect(root).toHaveAttribute('data-live-updates', 'stopped');
        await expect(pill(root)).toBeHidden();
    });
});

test.describe('Z7c — a failing endpoint or a paused provider slows the live prices down, and the page shows nothing new', () => {
    test('(g) /assets/{id}: on a failing endpoint the gaps double from 60 s up to the 10-minute cap, and hold it', async ({page}) => {
        // 35 minutes of page clock, in steps short enough to keep the user there.
        test.setTimeout(LONG_TEST_TIMEOUT_MS);
        const session = await openDetail(page, {kind: 'server-error'});
        const root = detailRoot(page);

        let from = session.opened;
        for (let index = 0; index < DETAIL_FAILURE_GAPS_MS.length; index++) from = await expectNextRequestWithUser(page, session, root, from, DETAIL_FAILURE_GAPS_MS[index], index + 1);

        // Every gap side by side, for the record of a red: four doublings of 30 s, then the cap twice in a row.
        const {sentAt} = await liveRecord(page);
        const gaps = sentAt.slice(1).map((at, index) => at - sentAt[index]);
        expect(
            gaps.map((gap, index) => Math.abs(gap - DETAIL_FAILURE_GAPS_MS[index]) <= SLACK_MS),
            `the live requests left ${gaps.map((gap) => `${(gap / 1000).toFixed(1)} s`).join(', ')} apart`,
        ).toEqual(DETAIL_FAILURE_GAPS_MS.map(() => true));

        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();
    });

    test('(h) /assets: while every provider is paused no request leaves, until the pause ends 300 s after the answer', async ({page}) => {
        const session = await openList(page, {kind: 'rate-limited', retryAfterSeconds: PROVIDER_PAUSE_S});
        const root = listRoot(page);
        expect(session.traffic.askedFor[0], 'premise: the list asked about its assets, so every one of them was answered RATE_LIMITED').not.toHaveLength(0);

        // The page reads the pause when the answer lands: the window is counted from there, not from the request.
        const [answeredAt] = (await liveRecord(page)).settledAt;
        const pauseEnds = answeredAt + PROVIDER_PAUSE_S * 1000;
        await runClockWithUserTo(page, root, pauseEnds - SLACK_MS);
        await expectLiveRequests(page, session.traffic, 1, `no live request while every provider is paused — the answer came back at ${seconds(answeredAt, session.opened)} with ${PROVIDER_PAUSE_S} s of pause; the 60 s cadence alone would have asked at +60 s`, session.opened);
        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();

        await runClockWithUserTo(page, root, pauseEnds + SLACK_MS);
        await expectLiveRequests(page, session.traffic, 2, `exactly one live request when the pause ends, between ${seconds(pauseEnds - SLACK_MS, session.opened)} and ${seconds(pauseEnds + SLACK_MS, session.opened)}`, session.opened);
        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();
    });
});

test.describe('Z-3 — west of Greenwich in the evening, a range that ends today is still live', () => {
    // The whole context lives in New York: at 21:00 there the UTC date is already the next day.
    test.use({timezoneId: NEW_YORK_EVENING.timeZone});

    test('(i) /assets: at 21:00 in New York a range ending today asks for live prices when it opens, and again 60 s later', async ({page}) => {
        const assetId = await seededPricedAssetId(page);
        const root = listRoot(page);
        const session = await openOnUserCalendar(page, '/assets', root, page.getByTestId(`asset-card-${assetId}`), LIST_INTERVAL_MS);
        expect(session.traffic.askedFor[0], `the list asked about the assets it shows, ${SEEDED_PRICED_ASSET.displayName} among them`).toContain(assetId);

        await expectNextTick(page, session, session.opened, LIST_INTERVAL_MS, 1);

        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();
    });

    test('(j) /assets/{id}: at 21:00 in New York a range ending today asks for the live price when it opens and again 30 s later, and the summary shows it', async ({page}) => {
        const assetId = await seededPricedAssetId(page);
        const root = detailRoot(page);
        const session = await openOnUserCalendar(page, `/assets/${assetId}`, root, root.getByTestId('asset-detail-info'), DETAIL_INTERVAL_MS, {kind: 'quote', ...LIVE_QUOTE, asOf: NEW_YORK_EVENING.localDate});
        expect(session.traffic.askedFor[0], 'the detail asked about its asset').toEqual([assetId]);

        await expectNextTick(page, session, session.opened, DETAIL_INTERVAL_MS, 1);

        await expect(root).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(root)).toBeHidden();
        // The quote, not the chart's last close: a page that took the range for a past one would show the close.
        await expect(root.getByTestId('asset-detail-live-price')).toHaveText(LIVE_QUOTE_SHOWN);
    });
});

test.describe('Z-3 — east of Greenwich after midnight, a range that ended yesterday is not live', () => {
    // The whole context lives in Rome: at 00:30 there the UTC date is still the day before.
    test.use({timezoneId: ROME_AFTER_MIDNIGHT.timeZone});

    test('(k) /assets: at 00:30 in Rome a range that ended yesterday asks for no live price, over the load and 65 s more', async ({page}) => {
        const assetId = await seededPricedAssetId(page);
        const root = listRoot(page);
        const traffic = await openAtMoment(page, ROME_AFTER_MIDNIGHT, `/assets?${RANGE_ENDING_YESTERDAY}`, root, page.getByTestId(`asset-card-${assetId}`));
        await expectNoLiveRequestOnYesterday(page, traffic, root);
    });

    test('(l) /assets/{id}: at 00:30 in Rome a range that ended yesterday asks for no live price, over the load and 65 s more', async ({page}) => {
        const assetId = await seededPricedAssetId(page);
        const root = detailRoot(page);
        const traffic = await openAtMoment(page, ROME_AFTER_MIDNIGHT, `/assets/${assetId}?${RANGE_ENDING_YESTERDAY}`, root, root.getByTestId('asset-detail-info'));
        await expectNoLiveRequestOnYesterday(page, traffic, root);
    });
});
