/**
 * The Dashboard follows the current prices — E2E (FB-28; decision 31's pause rules, the cadence of MF's analysis).
 *
 * A minute after the report is on screen, and every minute while the page is used, the Dashboard asks the current price
 * of the assets it holds (`POST /assets/prices/current`, which writes today's quote) and then the summary alone
 * (`POST /portfolio/report` with `include_summary` and every other section off): the figures — net worth, KPIs, positions,
 * allocation — move with the prices without the user pressing Refresh. The full report (history, returns) is not polled.
 * It pauses while the tab is hidden and after two minutes without input, and resumes by itself (`activePolling.ts`); after a
 * failure the next poll waits twice as long; a period that ended before today has nothing to follow.
 *
 * How time is driven: as `assets/asset-live-pause.spec.ts` does it (read its header). `page.clock.install()` before the page
 * opens; once the main report is on screen, `pauseAt` freezes the page clock and only the test moves it, with `runFor`,
 * which fires every timer in between. Every request is stamped inside the page with the page's own clock, so each window
 * is measured from the moment the main report settled — the poller starts when it is applied — and not from the machine's.
 * A silent window is proven twice: by the exact count read right after it, and by the exact count after the next expected
 * request (a late request from the silent window would show up there as one too many).
 *
 * Offline and read-only. The current-price request writes today's candle and asks the live providers: it is answered in the
 * browser with a schema-valid empty result (or a failure), so nothing reaches a third party and nothing is written. The
 * summary request is the backend's own answer (the engine is read-only); the one case that shows the figures moving
 * rewrites its net worth in the browser.
 *
 * The page root publishes the poller's state as `data-live-updates` (`running | paused-idle | paused-hidden | stopped`), and the
 * toolbar's Refresh button takes the look of the «Updates paused» pill (the same button, `data-live-state="paused-idle"`, F-4) only
 * while it is paused for inactivity. In every case the
 * request counts come first and the published state after, so a red names the behaviour before the attribute.
 *
 * Desktop only: the cadence does not depend on the viewport.
 */

import {expect, test} from '../fixtures/playwright';
import type {Page} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

/** MF's analysis of 3/11, written out rather than imported: the spec pins the numbers that were decided. */
const INTERVAL_MS = 60_000;
const IDLE_MS = 120_000;
/** Half-width of the window around each expected request: room for the page's own scheduling, far below any interval. */
const SLACK_MS = 1_500;
const PAUSE_AHEAD_MS = 2_000;
const TEST_TIMEOUT_MS = 120_000;

const PRICES_PATH = '/api/v1/assets/prices/current';
const REPORT_PATH = '/api/v1/portfolio/report';

type Exchange = {path: string; body: string | null; sentAt: number; settledAt: number | null};
type Held = {summary?: {holdings?: Array<{asset_id: number}>; net_worth?: {amount: string}} | null};
type ReportBody = {include_summary?: boolean; include_history?: boolean; include_allocation_history?: boolean; include_positions_contribution?: boolean; include_pnl_candles?: boolean; broker_ids?: number[]; apply_ownership_share?: boolean};

/** What the stub of the price route has seen. */
interface PriceTraffic {
    served: number;
    askedFor: number[][];
}

/** How the stub answers the price route. */
type PriceAnswer = 'empty' | 'server-error';

async function stubPrices(page: Page, answer: PriceAnswer): Promise<PriceTraffic> {
    const traffic: PriceTraffic = {served: 0, askedFor: []};
    await page.route('**/api/v1/assets/prices/current*', async (route) => {
        const ids: unknown = JSON.parse(route.request().postData() ?? 'null');
        traffic.askedFor.push(Array.isArray(ids) ? ids.filter((id): id is number => typeof id === 'number') : []);
        if (answer === 'server-error') await route.fulfill({status: 500, json: {detail: 'Internal Server Error'}});
        else await route.fulfill({json: {results: [], success_count: 0, errors: []}});
        traffic.served += 1;
    });
    return traffic;
}

/** The summary-only question: sections off, summary on. */
function isLight(body: ReportBody | null): boolean {
    return body?.include_summary === true && body.include_history === false && body.include_allocation_history === false && !body.include_positions_contribution && !body.include_pnl_candles;
}

/** The page's own clock stamps the requests to the two routes, with the body, when they leave and when they come back. */
async function recordExchanges(page: Page): Promise<void> {
    await page.addInitScript(
        ({prices, report}: {prices: string; report: string}) => {
            const record: Exchange[] = [];
            Object.defineProperty(window, '__lfSpecExchanges', {value: record});
            const pathOf = (url: string): string | null => {
                try {
                    const path = new URL(url, window.location.href).pathname;
                    return path === prices || path === report ? path : null;
                } catch {
                    return null;
                }
            };
            const tracked = new WeakMap<XMLHttpRequest, string>();
            const nativeOpen = XMLHttpRequest.prototype.open;
            const nativeSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function (this: XMLHttpRequest, ...args: unknown[]) {
                const path = pathOf(String(args[1]));
                if (path) tracked.set(this, path);
                else tracked.delete(this);
                return Reflect.apply(nativeOpen, this, args);
            } as XMLHttpRequest['open'];
            XMLHttpRequest.prototype.send = function (this: XMLHttpRequest, ...args: unknown[]) {
                const path = tracked.get(this);
                if (path) {
                    const entry: Exchange = {path, body: typeof args[0] === 'string' ? args[0] : null, sentAt: Date.now(), settledAt: null};
                    record.push(entry);
                    this.addEventListener('loadend', () => {
                        entry.settledAt = Date.now();
                    });
                }
                return Reflect.apply(nativeSend, this, args);
            } as XMLHttpRequest['send'];
        },
        {prices: PRICES_PATH, report: REPORT_PATH},
    );
}

async function exchanges(page: Page): Promise<Exchange[]> {
    return page.evaluate(() => {
        const record = (window as unknown as {__lfSpecExchanges?: Exchange[]}).__lfSpecExchanges;
        if (!record) throw new Error('No exchange record in this document: recordExchanges() must be installed before the navigation');
        return record.map((entry) => ({...entry}));
    });
}

const root = (page: Page) => page.getByTestId('dashboard-page');
/** The «Updates paused» pill is the toolbar's Refresh button while the prices are paused for inactivity (F-4): one button, no extra element. */
const pill = (page: Page) => page.locator('[data-testid="sync-button"][data-live-state="paused-idle"]');

const bodyOf = (entry: Exchange): ReportBody | null => {
    try {
        return entry.body ? (JSON.parse(entry.body) as ReportBody) : null;
    } catch {
        return null;
    }
};

async function livePricesSent(page: Page): Promise<Exchange[]> {
    return (await exchanges(page)).filter((entry) => entry.path === PRICES_PATH);
}

async function summariesSent(page: Page): Promise<Exchange[]> {
    return (await exchanges(page)).filter((entry) => entry.path === REPORT_PATH && isLight(bodyOf(entry)));
}

async function pageNow(page: Page): Promise<number> {
    return page.evaluate(() => Date.now());
}

async function pauseClock(page: Page): Promise<number> {
    const at = (await pageNow(page)) + PAUSE_AHEAD_MS;
    await page.clock.pauseAt(at);
    expect(await pageNow(page), 'the page clock froze where it was asked to').toBe(at);
    return at;
}

async function runClockTo(page: Page, target: number): Promise<void> {
    const now = await pageNow(page);
    expect(target, 'the spec only moves the page clock forward').toBeGreaterThanOrEqual(now);
    try {
        await page.clock.runFor(target - now);
    } catch (error) {
        const firstLine = String(error).split('\n')[0];
        test.info().annotations.push({type: 'page timer error', description: firstLine});
        expect(await pageNow(page), `the page clock reached its target although a page timer threw: ${firstLine}`).toBe(target);
    }
}

/** Input: the page hears it on `window` (a click would also move the pointer). Alternating points, so every move is one. */
let pointerSide = 0;
async function userMoves(page: Page): Promise<void> {
    pointerSide = 1 - pointerSide;
    await page.mouse.move(40 + pointerSide * 30, 40 + pointerSide * 30);
}

async function setVisibility(page: Page, state: 'hidden' | 'visible'): Promise<void> {
    await page.evaluate((next) => {
        Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => next});
        document.dispatchEvent(new Event('visibilitychange'));
    }, state);
}

/**
 * The counts of the two live requests so far, read in the page, and — once the stub has answered them and the answers are
 * back in the page — the requests. `expected` of each.
 */
async function expectPolls(page: Page, traffic: PriceTraffic, expected: number, what: string): Promise<{prices: Exchange[]; summaries: Exchange[]}> {
    const prices = await livePricesSent(page);
    const summaries = await summariesSent(page);
    expect({prices: prices.length, summaries: summaries.length}, `${what} — the page sent`).toEqual({prices: expected, summaries: expected});
    await expect.poll(() => traffic.served, {message: `${what} — the stub answered every price request`, timeout: 10_000}).toBe(expected);
    await expect
        .poll(async () => [...(await livePricesSent(page)), ...(await summariesSent(page))].every((entry) => entry.settledAt !== null), {message: `${what} — every answer is back in the page before its clock moves on`, timeout: 15_000})
        .toBe(true);
    return {prices, summaries};
}

interface Opened {
    traffic: PriceTraffic;
    /** The page-clock time the main report settled at: the poller starts when it is applied. */
    reported: number;
    /** The asset ids the main report holds. */
    held: number[];
    /** The brokers the page asks about. */
    brokerIds: number[] | undefined;
}

/** Open the Dashboard on `query`, wait for its main report, and freeze the page clock shortly after it. */
async function openDashboard(page: Page, query: string, answer: PriceAnswer = 'empty'): Promise<Opened> {
    const traffic = await stubPrices(page, answer);
    await recordExchanges(page);
    await page.emulateMedia({reducedMotion: 'reduce'});
    await page.mouse.move(1, 1);
    await page.clock.install({});
    await login(page, TEST_USER);
    const mainReport = page.waitForResponse((response) => response.url().endsWith(REPORT_PATH) && response.request().method() === 'POST' && (response.request().postDataJSON() as ReportBody).include_history !== false, {timeout: 30_000});
    await page.goto(`/dashboard?${query}`);
    const answered = await mainReport;
    expect(answered.ok(), `the main report: HTTP ${answered.status()}`).toBe(true);
    const report = (await answered.json()) as Held;
    const held = [...new Set((report.summary?.holdings ?? []).map((holding) => holding.asset_id))].sort((a, b) => a - b);
    await waitForSettled(page.getByTestId('dashboard-page'), 30_000);
    const main = (await exchanges(page)).find((entry) => entry.path === REPORT_PATH && bodyOf(entry)?.include_history !== false);
    expect(main?.settledAt, 'the page stamped the main report').not.toBeNull();
    await pauseClock(page);
    return {traffic, reported: main!.settledAt!, held, brokerIds: (answered.request().postDataJSON() as ReportBody).broker_ids};
}

test.describe('Dashboard — the figures follow the current prices (FB-28)', () => {
    test.use({viewport: {width: 1280, height: 900}});

    test('a minute after the report, and every minute: the prices of the held assets, then the summary alone', async ({page}) => {
        test.setTimeout(TEST_TIMEOUT_MS);
        const {traffic, reported, held, brokerIds} = await openDashboard(page, 'tab=panoramica');
        expect(held.length, 'precondition: the test user holds assets on the Dashboard').toBeGreaterThan(0);

        await runClockTo(page, reported + INTERVAL_MS - SLACK_MS);
        await expectPolls(page, traffic, 0, 'the first minute is silent');

        await userMoves(page);
        await runClockTo(page, reported + INTERVAL_MS + SLACK_MS);
        const first = await expectPolls(page, traffic, 1, 'a minute after the report: one poll');
        expect(traffic.askedFor[0].slice().sort((a, b) => a - b), 'the poll asks the held assets, once each').toEqual(held);
        expect(first.prices[0].sentAt, 'the prices are asked before the summary').toBeLessThanOrEqual(first.summaries[0].sentAt);
        const summary = bodyOf(first.summaries[0]);
        expect(summary, 'the summary is the same scope as the report, with every section off').toMatchObject({include_summary: true, include_history: false, include_allocation_history: false, broker_ids: brokerIds});
        expect(summary?.apply_ownership_share, 'the Dashboard keeps the owner’s share').not.toBe(false);

        await userMoves(page);
        await runClockTo(page, reported + 2 * INTERVAL_MS + SLACK_MS);
        await expectPolls(page, traffic, 2, 'and another a minute later');
        await expect(root(page)).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(page), 'nothing is paused: no pill').toBeHidden();
    });

    test('the figures move: the net worth on screen is the summary the poll brought', async ({page}) => {
        test.setTimeout(TEST_TIMEOUT_MS);
        const bump = 1234.56;
        let mainNetWorth = NaN;
        await page.route(`**${REPORT_PATH}`, async (route) => {
            const body = route.request().postDataJSON() as ReportBody | null;
            const response = await route.fetch();
            if (!isLight(body)) {
                const json = (await response.json()) as Held;
                if (Number.isNaN(mainNetWorth) && json.summary?.net_worth) mainNetWorth = Number(json.summary.net_worth.amount);
                await route.fulfill({response, json});
                return;
            }
            const json = (await response.json()) as Held;
            if (json.summary?.net_worth) json.summary.net_worth.amount = String(Number(json.summary.net_worth.amount) + bump);
            await route.fulfill({response, json});
        });
        const {traffic, reported} = await openDashboard(page, 'tab=panoramica');
        const netWorth = page.getByTestId('kpi-net-worth').getByTestId('kpi-value');
        const digits = (text: string | null): string => (text ?? '').replace(/\D/g, '');
        const before = digits(await netWorth.textContent());
        expect(before, `precondition: the net worth is on screen (${mainNetWorth})`).not.toBe('');

        await userMoves(page);
        await runClockTo(page, reported + INTERVAL_MS + SLACK_MS);
        await expectPolls(page, traffic, 1, 'one poll');
        // The figure counts up to its new value (`TweenedValue`, on animation frames): the frozen page clock lets it finish.
        await runClockTo(page, (await pageNow(page)) + 3_000);
        const expected = digits((mainNetWorth + bump).toFixed(2));
        await expect.poll(async () => digits(await netWorth.textContent()), {message: 'the net worth shows the summary the poll brought (the main report’s plus the stub’s bump)', timeout: 10_000}).toBe(expected);
        expect(digits(await netWorth.textContent())).not.toBe(before);
    });

    test('a hidden tab polls nothing; when it is visible again a poll that fell due runs at once', async ({page}) => {
        test.setTimeout(TEST_TIMEOUT_MS);
        const {traffic, reported} = await openDashboard(page, 'tab=panoramica');
        await userMoves(page);
        await setVisibility(page, 'hidden');
        await runClockTo(page, reported + 3 * INTERVAL_MS);
        await expectPolls(page, traffic, 0, 'three minutes hidden: nothing');
        await expect(root(page)).toHaveAttribute('data-live-updates', 'paused-hidden');
        await expect(pill(page), 'a hidden tab shows no pill: nobody sees it').toBeHidden();

        await setVisibility(page, 'visible');
        await runClockTo(page, (await pageNow(page)) + SLACK_MS);
        await expectPolls(page, traffic, 1, 'visible again: one poll at once, not three');
        await expect(root(page)).toHaveAttribute('data-live-updates', 'running');
    });

    test('two minutes without input pause the polls; the next input resumes them with one at once', async ({page}) => {
        test.setTimeout(TEST_TIMEOUT_MS);
        const {traffic, reported} = await openDashboard(page, 'tab=panoramica');
        // One input, a few seconds after the report: the page is idle from about `reported + 2 min`, after the second poll.
        await userMoves(page);
        await runClockTo(page, reported + INTERVAL_MS + SLACK_MS);
        await expectPolls(page, traffic, 1, 'used: the first poll');
        await runClockTo(page, reported + 2 * INTERVAL_MS + SLACK_MS);
        await expectPolls(page, traffic, 2, 'used: a poll a minute');

        // The last input was a few seconds after `reported`; the page is idle from `reported + 2 min` and a bit, so the third poll never leaves.
        await runClockTo(page, reported + IDLE_MS + 4 * INTERVAL_MS);
        await expectPolls(page, traffic, 2, 'four more minutes without input: paused, nothing sent');
        await expect(root(page)).toHaveAttribute('data-live-updates', 'paused-idle');
        await expect(pill(page), 'paused for inactivity: the pill says so').toBeVisible();

        await userMoves(page);
        await runClockTo(page, (await pageNow(page)) + SLACK_MS);
        await expectPolls(page, traffic, 3, 'an input: one poll at once');
        await expect(root(page)).toHaveAttribute('data-live-updates', 'running');
        await expect(pill(page), 'resumed: the pill goes away').toBeHidden();
    });

    test('the paused button is the Refresh button in its place; a click on it restarts the updates by hand (F-4)', async ({page}) => {
        test.setTimeout(TEST_TIMEOUT_MS);
        const {reported} = await openDashboard(page, 'tab=panoramica');
        await userMoves(page);
        await runClockTo(page, reported + IDLE_MS + 4 * INTERVAL_MS);
        await expect(root(page)).toHaveAttribute('data-live-updates', 'paused-idle');
        await expect(pill(page), 'paused for inactivity: the Refresh button wears the pause look').toBeVisible();
        await expect(page.getByTestId('sync-button'), 'one button, never two: no second element for the pause').toHaveCount(1);
        await expect(page.getByTestId('live-updates-status'), 'no separate pill any more').toHaveCount(0);

        await page.getByTestId('sync-button').click();
        await expect(root(page)).toHaveAttribute('data-live-updates', 'running', {timeout: 15_000});
        await expect(pill(page), 'clicked: the updates run again, the button is the Refresh one').toBeHidden();
    });

    test('a period that ended before today has no current price to follow', async ({page}) => {
        test.setTimeout(TEST_TIMEOUT_MS);
        const {traffic, reported} = await openDashboard(page, 'tab=panoramica&start=2024-01-02&end=2024-06-28');
        await userMoves(page);
        await runClockTo(page, reported + 2 * INTERVAL_MS + SLACK_MS);
        await expectPolls(page, traffic, 0, 'a past period: no poll over two minutes');
        await expect(root(page)).toHaveAttribute('data-live-updates', 'stopped');
        await expect(pill(page)).toBeHidden();
    });

    test('a poll whose prices failed still asks the summary, and the next one waits twice as long', async ({page}) => {
        test.setTimeout(TEST_TIMEOUT_MS);
        const {traffic, reported} = await openDashboard(page, 'tab=panoramica', 'server-error');
        await userMoves(page);
        await runClockTo(page, reported + INTERVAL_MS + SLACK_MS);
        await expectPolls(page, traffic, 1, 'the first poll: the prices fail, the summary is asked');

        // After a failure the next poll waits 2 × the interval from the start of the failed one, not one.
        await userMoves(page);
        await runClockTo(page, reported + 2 * INTERVAL_MS + SLACK_MS);
        await expectPolls(page, traffic, 1, 'a minute after the failure: still silent');
        await userMoves(page);
        await runClockTo(page, reported + 3 * INTERVAL_MS + SLACK_MS);
        await expectPolls(page, traffic, 2, 'two minutes after the failed poll: the next one');
    });
});
