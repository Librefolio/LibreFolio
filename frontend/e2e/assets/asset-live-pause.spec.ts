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
 * answered in the browser with a schema-valid empty result, so nothing reaches a third party and nothing is written.
 * The tests create nothing, so there is nothing to clean up (the routes go with the page).
 *
 * Reduced motion. Long asset names scroll as a marquee driven by `requestAnimationFrame`, a loop that never ends while
 * a name overflows; under the clock every frame is a timer `runFor` must fire, thousands per minute of page time.
 * Reduced motion stops the marquee at the source and changes nothing these tests look at.
 *
 * Desktop only: the cadence does not depend on the viewport.
 *
 * Order of assertions: in every test the request counts come first, the published state and the pill after, so a red
 * names the behaviour (a request that left when it should not have, or one that did not) before the attribute.
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

const LIVE_PRICES_ROUTE = '**/api/v1/assets/prices/current';
const LIVE_PRICES_PATH = '/api/v1/assets/prices/current';
/** The suite's known asset with a provider (populate_mock_data.populate_assets), found by name and provider, never by position. */
const SEEDED_PRICED_ASSET = {displayName: 'Apple Inc.', providerCode: 'yfinance'};
/** A range that ends long before today. */
const PAST_RANGE = {start: '2024-01-02', end: '2024-06-28'};

/** What the stub has seen. */
interface LiveTraffic {
    /** Requests answered, counted once the answer has been handed back to the browser. */
    served: number;
}

/** What the page itself has seen, read from the init script's record. */
interface LiveRecord {
    /** The page-clock time each request left at. */
    sentAt: number[];
    /** How many of them are back in the page (load, error or abort). */
    settled: number;
}

interface LiveSession {
    traffic: LiveTraffic;
    /** Page-clock time of the request the page sent when it opened. */
    opened: number;
}

/** Answer every live-price request in the browser with a schema-valid empty result, and count them. */
async function stubLivePrices(page: Page): Promise<LiveTraffic> {
    const traffic: LiveTraffic = {served: 0};
    await page.route(LIVE_PRICES_ROUTE, async (route) => {
        await route.fulfill({json: {results: [], success_count: 0, errors: []}});
        traffic.served += 1;
    });
    return traffic;
}

/**
 * Stamp every live-price request, inside the page, with the page's own clock — the one this spec drives. XHR is what
 * the pages use today (axios); `fetch` is covered too, so that a change of transport cannot hide a request.
 */
async function recordLiveRequests(page: Page): Promise<void> {
    await page.addInitScript((path: string) => {
        const record: {sentAt: number[]; settled: number} = {sentAt: [], settled: 0};
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
            });
        };
    }, LIVE_PRICES_PATH);
}

async function liveRecord(page: Page): Promise<LiveRecord> {
    return page.evaluate(() => {
        const record = (window as unknown as {__lfSpecLivePrices?: {sentAt: number[]; settled: number}}).__lfSpecLivePrices;
        if (!record) throw new Error('No live-price record in this document: recordLiveRequests() must be installed before the navigation');
        return {sentAt: [...record.sentAt], settled: record.settled};
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
 * the pointer parked, the clock installed (flowing until `pauseClock`).
 */
async function prepareLivePage(page: Page): Promise<LiveTraffic> {
    const traffic = await stubLivePrices(page);
    await recordLiveRequests(page);
    await page.emulateMedia({reducedMotion: 'reduce'});
    // Parked in a corner of the page being left: the page under test must hear no input but the ones a test makes.
    await page.mouse.move(1, 1);
    await page.clock.install();
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

async function openList(page: Page): Promise<LiveSession> {
    const traffic = await prepareLivePage(page);
    await goToAssetsPage(page);
    return freezeAfterOpening(page, traffic, LIST_INTERVAL_MS);
}

async function openDetail(page: Page): Promise<LiveSession> {
    const assetId = await seededPricedAssetId(page);
    const traffic = await prepareLivePage(page);
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
