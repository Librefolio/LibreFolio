/**
 * Page busy (Y11, developer decision 48 / P3): a page's Refresh button waits for the «big» requests of that page.
 *
 * The first wiring: the Dashboard's `sync-button` and the Files page's `files-refresh-button` are disabled, and publish
 * `data-busy="true"`, while a request the page decided to make is pending — a period change, a Refresh, a tab change —
 * with no click on the button needed; and only the requests of the page on screen: a route change drops the old page's
 * (`onNavigate` → `pageBusy.reset()`, `routes/(app)/+layout.svelte`).
 *
 * A localhost answer lands before an assertion can look, so every busy state here is made observable by holding the
 * request that causes it (`page.route`, let through with `route.continue()` when the test decides): the state belongs
 * to the test instead of a race. A hold picks its request by method, path and body — the one the trigger sends, checked
 * rather than assumed — and lets every other request through; its `held` list is the presence barrier, so a trigger
 * that never reaches the network fails by name instead of leaving a button that was never asked to wait. Every hold is
 * released and unrouted in `finally`: no request outlives its test.
 *
 * Busy or idle is read only from `data-busy` and `disabled`: no class (the spin is one), no colour, no text.
 *
 * Read-only on the shared database: TEST_USER, nothing written. «Aggiorna» re-reads and syncs nothing
 * (`requestPortfolioRefresh` is a client-side mark); the period and the Files tab live in this context's own
 * sessionStorage and localStorage.
 */

import type {Route} from '@playwright/test';
import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
const UPLOADS_PATH = `${API}/uploads`;
const BROKER_REPORTS_PATH = `${API}/brokers/import/files`;

/** A page load, or a round trip to the backend (the report is computed on the spot). A deadline, never a delay. */
const ROUND_TRIP_MS = 30_000;
/** Login, a full page load and a held round trip; the route-change case pays two pages. */
const TEST_MS = 120_000;

type ReportBody = {include_history?: boolean; date_range?: {start?: string; end?: string}};

/** The report that draws the Dashboard: history on. The contribution and the P&L candles ask without it. */
function isMainReport(request: Request): boolean {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== REPORT_PATH) return false;
    return (request.postDataJSON() as ReportBody | null)?.include_history === true;
}

/** The period a report asks for, as one comparable string. */
function periodOf(request: Request): string {
    const range = (request.postDataJSON() as ReportBody | null)?.date_range;
    return `${range?.start ?? ''}..${range?.end ?? ''}`;
}

/** Every main report the page sends from now on, in order. */
function recordMainReports(page: Page): Request[] {
    const sent: Request[] = [];
    page.on('request', (request) => {
        if (isMainReport(request)) sent.push(request);
    });
    return sent;
}

const isGet = (request: Request): boolean => request.method() === 'GET';

/** Requests the test holds, and owns until it lets them through. */
interface Hold {
    /** Every request held so far, in arrival order, the released ones included. */
    readonly held: Request[];
    /** How many are held still. */
    pending(): number;
    /** Lets every held request through; from then on the hold lets everything through. */
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
        // A request whose page went away cannot be continued any more, and there is nothing left to deliver it to.
        await Promise.all(waiting.splice(0).map((route) => route.continue().catch(() => undefined)));
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
});
