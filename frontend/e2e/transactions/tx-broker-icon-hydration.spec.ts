/**
 * C3 — the Transactions page asks `GET /api/v1/brokers/{id}` at most once per broker per cache
 * generation, including for a broker that has no icon field at all.
 *
 * The user-reported defect: with the Transactions page open, 40–60 requests a second of
 * `GET /api/v1/brokers/1`, for a broker with none of `icon_url`, `portal_url`,
 * `default_import_plugin`. Each broker badge re-ran its icon effect at every broker-store bump, the
 * store read "no icon field" as "not hydrated yet", and merging the answer bumped the store again.
 *
 * E1: an owned broker created with a name and an opening date only, and one owned DEPOSIT on it.
 *     Once the page has settled and the answer to its detail request has arrived, the broker has
 *     been asked for at most once — and still at most once after a second round trip of the page.
 * E2: the control — the same for an owned broker that has a `portal_url`: never asked for at all.
 *
 * The second round trip is the Refresh button, the one control on this page that re-queries the
 * transaction list (filtering, sorting and paging are client-side, W28). While it works the page
 * shows its loading state instead of the table, so the table and its badges are mounted anew; it
 * also clears the URL filters, so the owned row is brought back through the broker column filter,
 * client-side, which mounts the badge once more. Neither step touches the broker cache: the cache
 * generation is the same, so the answer is the same — no new request.
 *
 * Counting. `page.on('request')` counts what reached the network for the exact detail path. It
 * cannot say *when* to look, and a count read too early is a bet: a looping page re-asks one network
 * round trip after each answer, so "the badge is visible" alone can come before the second request.
 * The page therefore also keeps its own ledger of those XHRs (`sent`, `answered`), installed before
 * the app boots, and each check is taken once the badge is on screen and the answer to the request
 * it sent — if it sent one — has arrived. The app's reaction to an answer — merge, version bump,
 * effect, next request — runs in microtasks, so a ledger read from any later task sees its whole
 * outcome. The network counter is then brought level with the ledger (request interception, on for
 * the onboarding view below, can deliver it later than the page reports) and asserted.
 *
 * Owned data: each test creates its broker (unique name) and its DEPOSIT, and deletes exactly those
 * ids in its own cleanup — after leaving the page, so a looping page has stopped asking first.
 *
 * The transactions-page guide is not under test, and its coachmark can sit over the controls
 * clicked here, so the page gets a terminal onboarding view (the `tx-import-flow.spec.ts` pattern):
 * page-scoped, it never writes TEST_USER's onboarding rows.
 *
 * Key data-testids used:
 *   transactions-page [data-busy]            — the page's own "every load wave is in"
 *   tr[data-row-id="tx-{id}"]                — the owned DEPOSIT row
 *   broker-badge-{brokerId}                  — the owned broker's badge in that row
 *   tx-refresh-button                        — re-queries the list, remounts the table
 *   col-filter-trigger-broker / column-filter / filter-enum-search / filter-enum-option-{brokerId}
 */

import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const TEST_PORT = process.env.TEST_PORT || '6041';
const UI_TIMEOUT = 10_000;

const TERMINAL_ONBOARDING_AT = '2026-01-01T00:00:00Z';
const TERMINAL_ONBOARDING_FLOW_STEPS = [
    {flow: 'welcome', steps: []},
    {
        flow: 'intro_tour',
        steps: ['intro.scene', 'intro.navigation', 'intro.dashboard', 'intro.transactions_nav', 'intro.brokers_nav', 'intro.fx_nav', 'intro.assets_nav', 'intro.tools_nav', 'intro.settings_nav'],
    },
    {flow: 'transactions_page_guide', steps: ['transactions.page.overview', 'transactions.page.add', 'transactions.page.import', 'transactions.page.columns']},
    {flow: 'transaction_create_guide', steps: ['transaction.create.basics', 'transaction.create.amounts', 'transaction.create.details', 'transaction.create.save']},
    {flow: 'transaction_bulk_guide', steps: ['transaction.bulk.workspace', 'transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save']},
    {flow: 'import_guide', steps: ['import.upload', 'import.select', 'import.analyze', 'import.assets', 'import.fix', 'import.duplicates', 'import.review', 'import.bulk']},
    {flow: 'broker_page_guide', steps: ['broker.page.overview', 'broker.page.currency', 'broker.page.views', 'broker.page.add']},
    {flow: 'broker_guide', steps: ['broker.overview', 'broker.plugin', 'broker.icon']},
    {flow: 'broker_detail_guide', steps: ['broker.detail.header', 'broker.detail.overview', 'broker.detail.positions', 'broker.detail.transactions', 'broker.detail.info']},
    {flow: 'fx_page_guide', steps: ['fx.page.overview', 'fx.page.filters', 'fx.page.sync', 'fx.page.add']},
    {flow: 'fx_guide', steps: ['fx.currencies', 'fx.providers']},
    {flow: 'fx_detail_guide', steps: ['fx.detail.header', 'fx.detail.provider', 'fx.detail.chart', 'fx.detail.editor']},
    {flow: 'asset_page_guide', steps: ['asset.page.overview', 'asset.page.filters', 'asset.page.sync', 'asset.page.add']},
    {flow: 'asset_guide', steps: ['asset.search', 'asset.identity', 'asset.provider']},
    {flow: 'asset_detail_guide', steps: ['asset.detail.header', 'asset.detail.chart', 'asset.detail.editor', 'asset.detail.metadata', 'asset.detail.risk']},
] as const;
const TERMINAL_ONBOARDING_PROGRESS = {
    flows: TERMINAL_ONBOARDING_FLOW_STEPS.map(({flow, steps}) => ({
        flow,
        status: 'completed',
        version: 1,
        current_version: 1,
        update_available: false,
        created_at: TERMINAL_ONBOARDING_AT,
        updated_at: TERMINAL_ONBOARDING_AT,
        completed_at: TERMINAL_ONBOARDING_AT,
        ...(steps.length > 0
            ? {
                  steps: steps.map((stepId) => ({
                      step_id: stepId,
                      status: 'completed',
                      version: 1,
                      current_version: 1,
                      update_available: false,
                      created_at: TERMINAL_ONBOARDING_AT,
                      updated_at: TERMINAL_ONBOARDING_AT,
                      completed_at: TERMINAL_ONBOARDING_AT,
                  })),
              }
            : {}),
    })),
} as const;

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

type Owned = {suffix: string; brokerIds: number[]; transactionIds: number[]};

/** The page's own account of the detail requests for one broker (`performance.now()` stamps). */
type Ledger = {sent: number; answered: number; sentAt: number[]; answeredAt: number[]};

type OwnedBroker = {
    brokerId: number;
    name: string;
    transactionId: number;
    /** `page.on('request')`: every GET of the exact detail path that reached the network. */
    networkRequests: string[];
};

type IconFields = {icon_url?: string; portal_url?: string; default_import_plugin?: string};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** Installed before login, so the app's very first onboarding read already sees a terminal state. */
async function installTerminalOnboardingProgress(page: Page): Promise<void> {
    await page.route(
        (url) => url.pathname === `${API}/settings/onboarding` && url.search === '',
        async (route) => {
            if (route.request().method() !== 'GET') {
                await route.continue();
                return;
            }
            await route.fulfill({status: 200, contentType: 'application/json', json: TERMINAL_ONBOARDING_PROGRESS});
        },
    );
}

/**
 * Keep, inside the page, a ledger of the XHR GETs to one exact path: `sent` when the app sends one,
 * `answered` when its answer has arrived — `readyState` DONE, success or error, which fires before
 * the `load`/`loadend` handlers through which the app receives it. Applies from the next navigation
 * on, before any app script runs. The app's HTTP client is axios, whose browser adapter is XHR.
 */
async function installDetailLedger(page: Page, detailPath: string): Promise<void> {
    await page.addInitScript((path: string) => {
        const ledger = {sent: 0, answered: 0, sentAt: [] as number[], answeredAt: [] as number[]};
        (window as unknown as {__lfBrokerDetailLedger: typeof ledger}).__lfBrokerDetailLedger = ledger;
        const tracked = new WeakSet<XMLHttpRequest>();
        const open = XMLHttpRequest.prototype.open as (this: XMLHttpRequest, ...args: unknown[]) => void;
        const send = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.open = function (this: XMLHttpRequest, ...args: unknown[]) {
            const [method, url] = args as [string, string | URL];
            if (String(method).toUpperCase() === 'GET' && new URL(String(url), location.href).pathname === path) tracked.add(this);
            else tracked.delete(this);
            return open.apply(this, args);
        } as typeof XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.send = function (this: XMLHttpRequest, body?: Document | XMLHttpRequestBodyInit | null) {
            if (tracked.has(this)) {
                ledger.sent += 1;
                ledger.sentAt.push(performance.now());
                const onReadyStateChange = () => {
                    if (this.readyState !== XMLHttpRequest.DONE) return;
                    this.removeEventListener('readystatechange', onReadyStateChange);
                    ledger.answered += 1;
                    ledger.answeredAt.push(performance.now());
                };
                this.addEventListener('readystatechange', onReadyStateChange);
            }
            return send.call(this, body);
        };
    }, detailPath);
}

async function readLedger(page: Page): Promise<Ledger> {
    return page.evaluate(() => {
        const ledger = (window as unknown as {__lfBrokerDetailLedger?: {sent: number; answered: number; sentAt: number[]; answeredAt: number[]}}).__lfBrokerDetailLedger;
        if (!ledger) throw new Error('the detail-request ledger is not installed in this document');
        return {sent: ledger.sent, answered: ledger.answered, sentAt: [...ledger.sentAt], answeredAt: [...ledger.answeredAt]};
    });
}

/**
 * The page has done all it will do about this broker for now. Called once the badge is on screen:
 * the mount — and any request it sends, which leaves in microtasks — is over. If a request left,
 * wait for its answer; the ledger is then read from a later task, so the app's reaction to that
 * answer (merge, bump, effect, next request) is complete too. If none left there is nothing to wait
 * for: "at most one" includes zero. The branch reads a settled state, not a race.
 */
async function hydrationSettled(page: Page): Promise<void> {
    const {sent} = await readLedger(page);
    if (sent === 0) return;
    await page.waitForFunction(() => ((window as unknown as {__lfBrokerDetailLedger?: {answered: number}}).__lfBrokerDetailLedger?.answered ?? 0) >= 1, undefined, {timeout: UI_TIMEOUT});
}

/** The network count for the detail path, once it has caught up with every request the page reports having sent. */
async function detailRequestsSoFar(page: Page, broker: OwnedBroker): Promise<{network: number; ledger: Ledger}> {
    const ledger = await readLedger(page);
    await expect.poll(() => broker.networkRequests.length, {message: `the network witness catches up with the page ledger (sent ${ledger.sent})`, timeout: UI_TIMEOUT}).toBeGreaterThanOrEqual(ledger.sent);
    return {network: broker.networkRequests.length, ledger};
}

/**
 * The failure message. When a second request exists it also says when it left: right after the first
 * answer arrived, and one round trip after the first request — i.e. a loop paced by the network.
 */
function describeCount(moment: string, broker: OwnedBroker, seen: {network: number; ledger: Ledger}): string {
    const {ledger} = seen;
    const base = `GET ${API}/brokers/${broker.brokerId} ${moment}: ${seen.network} on the network (page ledger: sent ${ledger.sent}, answered ${ledger.answered})`;
    if (ledger.sentAt.length < 2 || ledger.answeredAt.length < 1) return base;
    const roundTrip = ledger.answeredAt[0] - ledger.sentAt[0];
    const reaction = ledger.sentAt[1] - ledger.answeredAt[0];
    return `${base}; the 2nd request left ${reaction.toFixed(1)} ms after the 1st answer arrived, whose round trip took ${roundTrip.toFixed(1)} ms`;
}

/** Create an owned broker with only the given icon fields, and one owned DEPOSIT on it; arm both witnesses for its detail path. */
async function ownBrokerWithDeposit(page: Page, owned: Owned, label: string, iconFields: IconFields): Promise<OwnedBroker> {
    const name = `C3 ${label} ${owned.suffix}`;
    const created = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01', ...iconFields}]}), 'create owned broker');
    const broker = created.results.find((item) => item.name === name);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(created)}`);
    owned.brokerIds.push(broker.broker_id);
    const brokerId = broker.broker_id;

    // Verify the precondition instead of inferring it from the payload: exactly these icon fields, the others null.
    const detail = await jsonFrom<Record<string, unknown>>(await page.request.get(`${API}/brokers/${brokerId}`), 'read owned broker');
    expect(detail, 'the owned broker carries exactly the icon fields this test gave it').toMatchObject({id: brokerId, icon_url: null, portal_url: null, default_import_plugin: null, ...iconFields});

    const description = `C3 deposit ${label} ${owned.suffix}`;
    const committed = await jsonFrom<{committed: boolean; issues?: unknown; results: Array<{operation: string; ids: number[]}>}>(
        await page.request.post(`${API}/transactions/commit`, {data: {creates: [{broker_id: brokerId, type: 'DEPOSIT', date: '2024-01-02', cash: {code: 'EUR', amount: '100'}, description}]}}),
        'commit owned DEPOSIT',
    );
    expect(committed.committed, `owned DEPOSIT rolled back: ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
    const ids = committed.results.filter((result) => result.operation === 'create').flatMap((result) => result.ids);
    owned.transactionIds.push(...ids);
    expect(ids, 'the commit created exactly the one owned DEPOSIT').toHaveLength(1);

    // Both witnesses are armed before the page that renders the badge is opened.
    const detailPath = `${API}/brokers/${brokerId}`;
    const networkRequests: string[] = [];
    page.on('request', (request) => {
        if (request.method() === 'GET' && new URL(request.url()).pathname === detailPath) networkRequests.push(request.url());
    });
    await installDetailLedger(page, detailPath);
    return {brokerId, name, transactionId: ids[0], networkRequests};
}

async function cleanupOwned(page: Page, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Leave the page first: a page that is still asking stops only when it is gone.
    await attempt('leave the page', async () => {
        await page.goto('about:blank');
    });
    if (owned.transactionIds.length > 0) {
        await attempt(`transactions ${owned.transactionIds.join(', ')}`, async () => {
            const result = await jsonFrom<{committed: boolean}>(await page.request.post(`${API}/transactions/commit`, {data: {creates: [], updates: [], deletes: owned.transactionIds}}), 'delete owned DEPOSIT');
            expect(result.committed).toBe(true);
        });
    }
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete owned broker');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use, testInfo) => {
        const baseURL = testInfo.project.use.baseURL;
        if (!baseURL || new URL(baseURL).port !== TEST_PORT || !['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname)) {
            throw new Error(`C3 broker icon hydration checks may only use the shared local test backend on port ${TEST_PORT}`);
        }
        const owned: Owned = {suffix: `w${testInfo.workerIndex}-${uniqueSuffix()}`, brokerIds: [], transactionIds: []};
        try {
            await installTerminalOnboardingProgress(page);
            await login(page, TEST_USER);
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

test.setTimeout(60_000);

/** The owned broker's badge inside the owned DEPOSIT row. */
function ownedBadge(page: Page, broker: OwnedBroker): Locator {
    return page.getByTestId('tx-table').locator(`tr[data-row-id="tx-${broker.transactionId}"]`).getByTestId(`broker-badge-${broker.brokerId}`);
}

/** First round trip: the page opened on the owned broker's rows, settled, the owned badge on screen. */
async function openTransactionsFilteredTo(page: Page, broker: OwnedBroker): Promise<void> {
    await navigateTo(page, `/transactions?broker_id=${broker.brokerId}`);
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(transactionsPage);
    await expect(ownedBadge(page, broker)).toBeVisible({timeout: UI_TIMEOUT});
}

/**
 * Second round trip, without leaving the page: Refresh re-queries the transaction list — waited on
 * by its own response — and remounts the table; then the broker column filter, client-side, brings
 * the owned row back, and its badge is mounted anew. Ends with the popover closed and the badge on
 * screen.
 */
async function refreshAndRefilter(page: Page, broker: OwnedBroker): Promise<void> {
    const transactionsPage = page.getByTestId('transactions-page');
    const refresh = page.getByTestId('tx-refresh-button');
    await expect(refresh).toBeEnabled({timeout: UI_TIMEOUT});
    const [listResponse] = await Promise.all([
        page.waitForResponse(
            (response) => {
                const url = new URL(response.url());
                return response.request().method() === 'GET' && url.pathname === `${API}/transactions` && url.search === '';
            },
            {timeout: UI_TIMEOUT},
        ),
        refresh.click(),
    ]);
    expect(listResponse.ok(), `transaction list re-query: HTTP ${listResponse.status()}`).toBeTruthy();
    await waitForSettled(transactionsPage);

    const trigger = page.getByTestId('col-filter-trigger-broker');
    await trigger.click();
    const popover = page.getByTestId('column-filter');
    await expect(popover).toHaveAttribute('data-filter-type', 'enum');
    await popover.getByTestId('filter-enum-search').fill(broker.name);
    const option = popover.getByTestId(`filter-enum-option-${broker.brokerId}`);
    await option.click();
    await expect(option).toHaveAttribute('data-checked', 'true');
    // The popover has no Escape handler: its own trigger toggles it closed.
    await trigger.click();
    await expect(popover).toBeHidden();
    await expect(ownedBadge(page, broker)).toBeVisible({timeout: UI_TIMEOUT});
}

test.describe('Transactions page — broker icon hydration (C3)', () => {
    test('E1: a broker without icon fields is asked for at most once — after the first load and after a second round trip of the page', async ({page, owned}) => {
        const broker = await ownBrokerWithDeposit(page, owned, 'no-icons', {});

        await openTransactionsFilteredTo(page, broker);
        await hydrationSettled(page);
        const afterLoad = await detailRequestsSoFar(page, broker);
        expect(afterLoad.network, describeCount('after the first load', broker, afterLoad)).toBeLessThanOrEqual(1);

        await refreshAndRefilter(page, broker);
        await hydrationSettled(page);
        const afterRoundTrip = await detailRequestsSoFar(page, broker);
        expect(afterRoundTrip.network, describeCount('after a second round trip', broker, afterRoundTrip)).toBeLessThanOrEqual(1);
    });

    test('E2 (control): a broker with a portal_url is never asked for — after the first load and after a second round trip of the page', async ({page, owned, baseURL}) => {
        // A portal on the lane's own origin: its favicon candidate never leaves the machine.
        const broker = await ownBrokerWithDeposit(page, owned, 'portal', {portal_url: `${baseURL}/e2e-c3-broker-portal`});

        // The visible badge is the presence barrier: a request, if any, is sent while it mounts.
        await openTransactionsFilteredTo(page, broker);
        await hydrationSettled(page);
        const afterLoad = await detailRequestsSoFar(page, broker);
        expect(afterLoad.network, describeCount('after the first load', broker, afterLoad)).toBe(0);

        await refreshAndRefilter(page, broker);
        await hydrationSettled(page);
        const afterRoundTrip = await detailRequestsSoFar(page, broker);
        expect(afterRoundTrip.network, describeCount('after a second round trip', broker, afterRoundTrip)).toBe(0);
    });
});
