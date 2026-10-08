/**
 * Starting currency: the Default Currency of the user first, the instance setting only as a fallback (R2 / N).
 *
 * Written RED-FIRST, before the fix. The developer's decision («Dalla Default Currency dell'utente: è un difetto»): a
 * page that opens on a display currency takes the user's Default Currency (`userSettings.base_currency`), and the
 * instance setting (`globalSettings.default_currency`, «Default currency for new users») only when the user has none.
 * At HEAD every site below reads the instance setting directly. One test per site:
 *
 *   (a) Dashboard: the initial `targetCurrency` and the `baseCurrency` it follows until a pick (`dashboard/+page.svelte`);
 *   (b) Dashboard, the guard: a currency picked by hand lasts the session (`dashboardViewStore`, sessionStorage) and
 *       still wins over the Default Currency. Green before the fix and after it;
 *   (c) Broker list (`brokers/+page.svelte`);
 *   (d) Broker detail (`brokers/[id]/+page.svelte`);
 *   (e) Assets, asset-set risk panel: the `targetCurrency` the page hands `AssetSetRiskPanel`, as it reaches
 *       `POST /risk/eligibility` (`assets/+page.svelte`);
 *   (f) FX detail: the `target_currency` of its AI Export (`fx/[pair]/+page.svelte`).
 *
 * Hermetic by interception, never by writing settings: TEST_USER is shared by every worker, and the instance settings by
 * every user, so writing either changes what every concurrent spec sees. Both reads are answered in this browser only,
 * from the real response with one field changed — `GET /settings/user` gives `base_currency: USD`, `GET /settings/global`
 * gives `default_currency: GBP` — and any other method on those URLs falls through. Two currencies that differ from each
 * other and from EUR (the seed's, and the last fallback), both with seeded pairs: a page that reads the instance setting
 * starts in GBP, and only the contract starts in USD.
 *
 * The routes are installed before the login, and every page under test is a full document load: the app bootstrap
 * (`appBootstrap.load()`) reads both settings before any page renders, and each load is checked to have read them
 * through the stub. Asserted: the body of the request a page sends, armed before what triggers it, and the ISO code on
 * a currency selector's trigger — never an amount, never translated text. Nothing here writes to the database: the one
 * writer on these paths, the live-price poll of `/assets`, is held unanswered as `risk-lab.spec.ts` holds it.
 */

import {expect, test, type Page, type Request} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {gotoFx, isSnapshotPost, openAiExportPanel, selectAiExportSelection, UI_TIMEOUT} from '../ai-export/helpers';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
const ELIGIBILITY_PATH = `${API}/risk/eligibility`;

/** The Default Currency of the user, as the stub answers `GET /settings/user` (`base_currency`). */
const USER_CURRENCY = 'USD';
/** The instance setting «Default currency for new users», as the stub answers `GET /settings/global` (`default_currency`). */
const INSTANCE_CURRENCY = 'GBP';
/** The currency test (b) picks by hand: neither of the two above, so a page that opens in it can only have kept the pick. */
const PICKED_CURRENCY = 'EUR';
/**
 * The FX pair of test (f), one the seed has (`ai-export-memory.spec.ts` opens it). Not EUR-USD: the FX page falls back
 * to the pair's quote currency (`data.canonicalQuote`), which on EUR-USD is USD — the expected answer — so a page
 * reading the pair instead of the user would pass there. On EUR-GBP neither the instance nor the pair says USD.
 */
const FX_PAIR = 'EUR-GBP';
/** The FX dataset `ai-export-contract.spec.ts` exports from this page: an exposure, which is what the currency is for. */
const FX_DATASET = 'fx.market_and_exposure';

/**
 * How long a page under test may take, from the start of its load, to send the request asserted on: boot, sign-in
 * check, bootstrap, then its own lists (the Dashboard asks only once it knows the owned brokers). A budget for the chain,
 * not a performance assertion.
 */
const REQUEST_TIMEOUT = 45_000;
const PAGE_TIMEOUT = 30_000;
const SELECTOR_TIMEOUT = 15_000;

// ============================================================================
// The stub
// ============================================================================

/** The settings reads the stub has answered so far, by endpoint: a live tally, compared across a load. */
interface SettingsReads {
    user: number;
    global: number;
}

type RouteHandler = Parameters<Page['route']>[1];

/**
 * `page.route` with a callback that absorbs its own failure (`routeQuietly` of `risk-lab.spec.ts`, copied).
 *
 * Nobody awaits a route callback, so what it throws is an unhandled rejection, pinned on whatever the worker runs at that
 * moment. `route.fetch()` rejects once the context closes under it: a read still in flight when a test ends would fail
 * whatever comes next. Absorbed, not hidden: the read is left unanswered, and the test that needed it fails on its own
 * barrier — the tally of `loadThroughStub`, or the request it waits for.
 */
async function routeQuietly(page: Page, url: string | RegExp, handler: RouteHandler): Promise<void> {
    await page.route(url, async (route, request) => {
        try {
            await handler(route, request);
        } catch (error) {
            console.warn(`[default-currency] left ${request.method()} ${request.url()} unanswered: its route callback failed with ${String(error)}`);
        }
    });
}

/**
 * Answer both settings reads with the currencies of this file, in this browser only.
 *
 * The real response is fetched and one field changed, so everything else the app reads there (language, theme, the other
 * instance settings) stays what the backend says. A non-2xx answer passes through untouched and is not counted. Any other
 * method on these URLs falls through: nothing here writes a setting.
 */
async function stubDefaultCurrencies(page: Page): Promise<SettingsReads> {
    const reads: SettingsReads = {user: 0, global: 0};
    await routeQuietly(page, `**${API}/settings/user`, async (route, request) => {
        if (request.method() !== 'GET') {
            await route.fallback();
            return;
        }
        const response = await route.fetch();
        if (!response.ok()) {
            await route.fulfill({response});
            return;
        }
        const body = (await response.json()) as Record<string, unknown>;
        await route.fulfill({response, json: {...body, base_currency: USER_CURRENCY}});
        reads.user += 1;
    });
    await routeQuietly(page, `**${API}/settings/global`, async (route, request) => {
        if (request.method() !== 'GET') {
            await route.fallback();
            return;
        }
        const response = await route.fetch();
        if (!response.ok()) {
            await route.fulfill({response});
            return;
        }
        const body = (await response.json()) as {items?: Array<Record<string, unknown>>};
        const items = (body.items ?? []).map((item) => (item.key === 'default_currency' ? {...item, value: INSTANCE_CURRENCY} : item));
        if (!items.some((item) => item.key === 'default_currency')) items.push({key: 'default_currency', value: INSTANCE_CURRENCY, value_type: 'string'});
        await route.fulfill({response, json: {...body, items}});
        reads.global += 1;
    });
    return reads;
}

// ============================================================================
// Loading a page under test
// ============================================================================

/**
 * A full document load, then proof that the new document read both settings through the stub and started on them.
 *
 * Counted, not assumed: a stub that stopped matching would leave the real settings in place, and every test here would
 * go red over currencies nobody chose. The caller makes sure the document open before the load reads no settings any
 * more: `beforeEach` unloads the login's Dashboard once its bootstrap is over, and test (b) leaves from a settled page.
 */
async function loadThroughStub(page: Page, reads: SettingsReads, load: () => Promise<unknown>): Promise<void> {
    const before = {...reads};
    await load();
    await expect.poll(() => reads.user > before.user && reads.global > before.global, {message: 'the page did not read both /settings/user and /settings/global through the stub: it is not running on the currencies of this file', timeout: PAGE_TIMEOUT}).toBe(true);
    await expect(page.getByTestId('app-shell'), 'the app did not start on the stubbed settings').toBeVisible({timeout: PAGE_TIMEOUT});
}

/** `page.waitForRequest`, armed now; awaited later through `capturedRequest`. */
function armRequest(page: Page, predicate: (request: Request) => boolean, timeout = REQUEST_TIMEOUT): Promise<Request> {
    const armed = page.waitForRequest(predicate, {timeout});
    // Awaited by the caller; the empty catch only keeps a failure in between from also surfacing as an unhandled rejection.
    void armed.catch(() => undefined);
    return armed;
}

/** The request `armed` waited for, or a failure that names what never came. */
async function capturedRequest(armed: Promise<Request>, what: string): Promise<Request> {
    try {
        return await armed;
    } catch (error) {
        throw new Error(`${what} (${error instanceof Error ? error.message : String(error)})`);
    }
}

/**
 * Load `path` as a new document with `predicate` armed before the load starts, and return the first request it matches.
 * The document open when this is called must send no such request any more: see `loadThroughStub`.
 */
async function loadCapturing(page: Page, reads: SettingsReads, path: string, predicate: (request: Request) => boolean, what: string): Promise<Request> {
    const armed = armRequest(page, predicate);
    await loadThroughStub(page, reads, () => page.goto(path));
    return capturedRequest(armed, what);
}

// ============================================================================
// What the pages send
// ============================================================================

/** A request's JSON body, or null when it carries none that parses. */
function jsonBody(request: Request): Record<string, unknown> | null {
    try {
        return request.postDataJSON() as Record<string, unknown> | null;
    } catch {
        return null;
    }
}

/** A portfolio report that carries its summary: what the Dashboard and both broker pages ask on load. Copied from `data-quality-banners.spec.ts`. */
function isSummaryReport(req: Request): boolean {
    if (req.method() !== 'POST' || new URL(req.url()).pathname !== REPORT_PATH) return false;
    return (req.postDataJSON() as {include_summary?: boolean} | null)?.include_summary === true;
}

function isEligibilityPost(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === ELIGIBILITY_PATH;
}

/** The currency a request asks in: `target_currency`, the name the report, the eligibility engine and the AI Export all give it. */
function askedCurrency(request: Request): unknown {
    return jsonBody(request)?.target_currency;
}

// ============================================================================
// Preconditions and the one writer
// ============================================================================

interface BrokerListItem {
    id: number;
    user_role?: string | null;
}

/** The brokers TEST_USER can see, as the API lists them: `page.request` carries the login and goes around the page's routes. */
async function visibleBrokers(page: Page): Promise<BrokerListItem[]> {
    const response = await page.request.get(`${API}/brokers`);
    expect(response.ok(), `GET ${API}/brokers → HTTP ${response.status()}`).toBe(true);
    return ((await response.json()) as {items?: BrokerListItem[]}).items ?? [];
}

/**
 * A broker TEST_USER owns. Any one satisfies the precondition; the lowest id is taken because neighbouring specs create
 * their brokers after the seed, so it is the one least likely to be another test's, and to vanish under this one.
 */
async function ownedBrokerId(page: Page): Promise<number> {
    const owned = (await visibleBrokers(page)).filter((broker) => broker.user_role === 'OWNER').map((broker) => broker.id);
    if (owned.length === 0) throw new Error(`${TEST_USER.username} owns no broker, so no broker detail can be opened as its owner. Check populate_mock_data.py seeding.`);
    return Math.min(...owned);
}

/**
 * Hold the live-price poll of `/assets` unanswered for the whole test (`holdLivePricePoll` of `risk-lab.spec.ts`, where
 * the reasons are written out): an answered `POST /assets/prices/current` writes today's prices into the shared database.
 * Never unrouted, by this file or at teardown: removing the route would release the held poll to the backend.
 */
async function holdLivePricePoll(page: Page): Promise<void> {
    await page.route(/\/api\/v1\/assets\/prices\/current(?:\?|$)/, () => {
        // Deliberately neither fulfilled nor continued: see above.
    });
}

// ============================================================================
// Tests
// ============================================================================

test.describe('Starting currency: the Default Currency of the user (R2 / N)', () => {
    // Parallel: every test owns its browser context, its routes and nothing else, and none writes to the backend.
    test.describe.configure({mode: 'parallel', timeout: 120_000});
    // The app registers an offline-fallback service worker. Blocked here, so every request of this file meets
    // `page.route` and none can be answered from outside the stub; local to this spec, the shared config is untouched.
    test.use({serviceWorkers: 'block'});

    let reads: SettingsReads;

    test.beforeEach(async ({page}) => {
        reads = await stubDefaultCurrencies(page);
        await login(page, TEST_USER);
        // `login` returns as the login card hides, while its bootstrap is still reading the settings through the stub.
        // The app shell is the end of that bootstrap: past it no read of the login is left to land in a test's tally.
        await expect(page.getByTestId('app-shell'), 'the app did not start on the stubbed settings after the login').toBeVisible({timeout: PAGE_TIMEOUT});
        // The login lands on a live Dashboard that is already asking for its report. Unloaded before any test loads its
        // page, so that nothing it still has in flight can pass for the request of the page under test.
        await page.goto('about:blank');
    });

    test('(a) the Dashboard opens in the Default Currency of the user', async ({page}) => {
        const report = await loadCapturing(page, reads, '/dashboard', isSummaryReport, 'the Dashboard never asked for its report');
        expect(askedCurrency(report), 'the first report of the Dashboard is not in the Default Currency of the user').toBe(USER_CURRENCY);
        await expect(page.getByTestId('dashboard-target-currency-trigger'), 'the currency selector of the Dashboard does not show the Default Currency of the user').toContainText(USER_CURRENCY, {timeout: SELECTOR_TIMEOUT});
    });

    test('(b) a currency picked on the Dashboard outlasts a trip away and still wins over the Default Currency', async ({page}) => {
        const dashboard = page.getByTestId('dashboard-page');
        const trigger = page.getByTestId('dashboard-target-currency-trigger');

        // Whatever the Dashboard opens in — the instance setting today, the Default Currency after the fix — it is not
        // the currency about to be picked, or the pick would ask nothing new and the test would wait for nothing.
        const opening = await loadCapturing(page, reads, '/dashboard', isSummaryReport, 'the Dashboard never asked for its report');
        expect(askedCurrency(opening), `precondition: the Dashboard opens in another currency than ${PICKED_CURRENCY}`).not.toBe(PICKED_CURRENCY);
        await waitForSettled(dashboard, PAGE_TIMEOUT);

        const picked = armRequest(page, (request) => isSummaryReport(request) && askedCurrency(request) === PICKED_CURRENCY);
        await trigger.click();
        const option = page.getByTestId('dashboard-target-currency').getByTestId(`search-select-option-${PICKED_CURRENCY}`);
        await expect(option, `${PICKED_CURRENCY} is not offered by the currency selector of the Dashboard`).toBeVisible({timeout: SELECTOR_TIMEOUT});
        await option.click();
        await expect(trigger).toContainText(PICKED_CURRENCY, {timeout: SELECTOR_TIMEOUT});
        await capturedRequest(picked, `picking ${PICKED_CURRENCY} on the Dashboard asked no report in it`);
        await waitForSettled(dashboard, PAGE_TIMEOUT);

        // Away and back, each a document of its own in the same tab and origin: the session storage the pick is kept in
        // (`writeDashboardView` / `readDashboardView`) comes along, as it does for a user who leaves through the sidebar.
        // `/files` asks neither a report nor the settings itself (its bootstrap has read them by the time it renders),
        // and it is settled before the way back is armed.
        await page.goto('/files');
        await waitForSettled(page.getByTestId('files-page'), PAGE_TIMEOUT);

        const back = await loadCapturing(page, reads, '/dashboard', isSummaryReport, 'back on the Dashboard, it never asked for its report');
        expect(askedCurrency(back), 'back on the Dashboard, its first report is not in the currency picked in this session').toBe(PICKED_CURRENCY);
        await expect(trigger, 'back on the Dashboard, its currency selector does not show the currency picked in this session').toContainText(PICKED_CURRENCY, {timeout: SELECTOR_TIMEOUT});
        // The page follows its base currency until a pick (the `$effect` on `baseCurrency`): settled, the pick still stands.
        await waitForSettled(dashboard, PAGE_TIMEOUT);
        await expect(trigger, 'the Dashboard dropped the remembered pick once it settled').toContainText(PICKED_CURRENCY);
    });

    test('(c) the broker list opens in the Default Currency of the user', async ({page}) => {
        if ((await visibleBrokers(page)).length === 0) throw new Error(`${TEST_USER.username} sees no broker, and the broker list asks a report only for brokers it shows. Check populate_mock_data.py seeding.`);
        const report = await loadCapturing(page, reads, '/brokers', isSummaryReport, 'the broker list never asked for its report');
        expect(askedCurrency(report), 'the report of the broker list is not in the Default Currency of the user').toBe(USER_CURRENCY);
        await expect(page.getByTestId('broker-page-target-currency-trigger'), 'the currency selector of the broker list does not show the Default Currency of the user').toContainText(USER_CURRENCY, {timeout: SELECTOR_TIMEOUT});
    });

    test('(d) the detail of a broker opens in the Default Currency of the user', async ({page}) => {
        const brokerId = await ownedBrokerId(page);
        const report = await loadCapturing(page, reads, `/brokers/${brokerId}`, isSummaryReport, `the detail of broker ${brokerId} never asked for its overview report`);
        expect(jsonBody(report)?.broker_ids, `premise: the first report of the page is the overview of broker ${brokerId}`).toEqual([brokerId]);
        expect(askedCurrency(report), 'the overview report of the broker detail is not in the Default Currency of the user').toBe(USER_CURRENCY);
        await expect(page.getByTestId('broker-detail-target-currency-trigger'), 'the currency selector of the broker detail does not show the Default Currency of the user').toContainText(USER_CURRENCY, {timeout: SELECTOR_TIMEOUT});
    });

    test('(e) the asset-set risk panel asks the eligibility engine in the Default Currency of the user', async ({page}) => {
        await holdLivePricePoll(page);
        const question = await loadCapturing(page, reads, '/assets?tab=correlation', isEligibilityPost, 'the asset-set risk panel never asked the eligibility engine (it asks once the page has its asset list: check populate_mock_data.py seeding)');
        // Opened the way risk-lab.spec.ts opens it, and checked the same way: the lab's frame is the one asking.
        await expect(page.getByTestId('asset-global-risk-panel')).toBeVisible({timeout: PAGE_TIMEOUT});
        await expect(page.getByTestId('risk-asset-set-controls')).toBeVisible({timeout: PAGE_TIMEOUT});
        expect(askedCurrency(question), 'the asset-set risk panel asks the eligibility engine in another currency than the Default Currency of the user').toBe(USER_CURRENCY);
    });

    test('(f) the AI Export of an FX pair asks for its snapshot in the Default Currency of the user', async ({page, context}) => {
        // The export copies its prompt once the snapshot is in: granted as every AI Export spec grants it, so the click
        // starts the flow a user's does. What is asserted leaves the page before the clipboard is touched.
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        await loadThroughStub(page, reads, () => gotoFx(page, FX_PAIR));

        await openAiExportPanel(page);
        await selectAiExportSelection(page, 'dataset', FX_DATASET);
        const compact = page.getByTestId('ai-export-detail-compact');
        await compact.click();
        await expect(compact).toHaveAttribute('aria-pressed', 'true');

        const armed = armRequest(page, isSnapshotPost, UI_TIMEOUT);
        await page.getByTestId('ai-export-copy-button').click();
        const snapshot = jsonBody(await capturedRequest(armed, 'the AI Export of the FX page sent no snapshot request'));
        expect(snapshot?.domain, 'premise: the snapshot asked is the one of the FX page').toBe('fx');
        expect(snapshot?.target_currency, 'the AI Export of the FX page asks in another currency than the Default Currency of the user').toBe(USER_CURRENCY);
    });
});
