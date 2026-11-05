/**
 * broker-page-banners.spec.ts — the data-quality banner of the broker's page, and what its buttons ask.
 *
 * The page is a shell around `PortfolioView` (scope: broker). Since delivery 4 it shows the same grouped data-quality banner as
 * the Dashboard, to EVERY role, a VIEWER included: the banner's buttons sync shared prices and exchange rates, not the broker,
 * so they ask no permission of their own. This spec pins:
 *
 *   «Sync rates»    a served MISSING_FX_RATES issue shows the banner and its CTA, for the OWNER and for a VIEWER (shared, share 0).
 *                   Pressing it sends exactly one `POST /fx/currencies/sync` for the pair, the page root is `data-busy="true"`
 *                   while the request is held and `data-busy="false"` after, and the event `fx.rates.synced` is recorded.
 *   «Sync prices»   a served STALE_PRICE issue shows its button to a VIEWER; pressing it sends exactly one
 *                   `POST /assets/prices/sync` and the page settles.
 *   report scope    every `POST /portfolio/report` the broker page sends carries `broker_ids` equal to this broker alone.
 *
 * The issues are served (`page.route` on the report) and the syncs are held and answered with a canned success: no provider is
 * reached and no rate or price is written. One test per role, so a red names the role. Owned data: each test registers
 * disposable accounts, creates its own broker and one DEPOSIT through the API, grants the role with the broker-access API, and
 * the world fixture deletes everything by id afterwards. Nothing is found by position, no count of the global database is
 * read, and no translated text is asserted.
 *
 * Key data-testids:
 *   broker-detail-page [data-busy], broker-quota-badge, broker-overview-tab, broker-cash-balances
 *   data-quality-toggle, data-quality-issue-{code}, data-quality-cta-{code}
 */

import {expect, test as base, type APIRequestContext, type Browser, type Page} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {createOwnedBroker, deleteDisposableUser, registerDisposableUser, skipDueFlowsExcept} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, openOwnedAccount, type OwnedAccount} from '../fixtures/owned-pair';

const API = '/api/v1';
const UI_TIMEOUT = 10_000;
const LOAD_TIMEOUT = 20_000;
const SYNC_TIMEOUT = 30_000;

const REPORT_PATH = `${API}/portfolio/report`;
const FX_SYNC_PATH = `${API}/fx/currencies/sync`;
const PRICES_SYNC_PATH = `${API}/assets/prices/sync`;

type Role = 'OWNER' | 'VIEWER';

// ---------------------------------------------------------------------------
// The world: disposable accounts, their broker and row, deleted by id afterwards
// ---------------------------------------------------------------------------

type World = {
    /** The owner's page, signed in past onboarding. */
    page: Page;
    browser: Browser;
    /** The owner account and its brokers (recorded for cleanup the moment they exist). */
    owned: OwnedAccount;
    /** A context of its own that registers and deletes accounts; never signed in by a page. */
    accounts: APIRequestContext;
    /** Undo steps, run last-in first-out; each is attempted and every failure reported. */
    cleanups: Array<() => Promise<void>>;
};

const test = base.extend<{world: World}>({
    world: async ({page, browser}, use) => {
        const accountsContext = await browser.newContext();
        const world: World = {page, browser, owned: emptyOwnedAccount(), accounts: accountsContext.request, cleanups: []};
        try {
            await use(world);
        } finally {
            const failures: unknown[] = [];
            const attempt = async (step: () => Promise<unknown>) => {
                try {
                    await step();
                } catch (error) {
                    failures.push(error);
                }
            };
            for (const undo of [...world.cleanups].reverse()) await attempt(undo);
            // The owner last: its broker goes by `force`, with every row left on it.
            await attempt(() => cleanupOwnedAccount(page, accountsContext.request, world.owned));
            await attempt(() => accountsContext.close());
            if (failures.length > 0) throw new AggregateError(failures, 'broker-page-banners could not delete everything it created');
        }
    },
});

test.setTimeout(90_000);

/**
 * The owner's broker with one deposit on it, and the page of the account that holds `role` on it: the owner's own page for
 * OWNER; for VIEWER a second disposable account, granted the role with no share, in a browser context of its own.
 */
async function openBrokerAs(world: World, role: Role): Promise<{brokerId: number; page: Page}> {
    await openOwnedAccount(world.page, world.accounts, world.owned, 'fbbann');
    const owner = world.owned.user;
    if (!owner) throw new Error('the owner account was not recorded');
    const broker = await createOwnedBroker(world.page, 'fbbann', world.owned.brokerIds);
    await commitCreates(world.page, [{broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'EUR', amount: '1234.56'}, description: 'banner page deposit'}], 'give the broker something to load');
    if (role === 'OWNER') return {brokerId: broker.id, page: world.page};

    const sharedWith = await registerDisposableUser(world.accounts, 'fbbannv');
    world.cleanups.push(async () => deleteDisposableUser(world.accounts, sharedWith));
    const grant = await world.page.request.put(`${API}/brokers/${broker.id}/access`, {
        data: [
            {user_id: owner.id, role: 'OWNER', share_percentage: 1},
            {user_id: sharedWith.id, role, share_percentage: 0},
        ],
    });
    expect(grant.ok(), `grant ${role}: HTTP ${grant.status()} ${await grant.text()}`).toBe(true);

    const context = await world.browser.newContext();
    world.cleanups.push(async () => context.close());
    const page = await context.newPage();
    await login(page, sharedWith);
    await skipDueFlowsExcept(page, []);
    return {brokerId: broker.id, page};
}

/** The broker's page, loaded: the header is drawn, the root says every load wave is in, and the Overview shows its cash block. */
async function openBrokerPage(page: Page, brokerId: number): Promise<void> {
    await navigateTo(page, `/brokers/${brokerId}`);
    const root = page.getByTestId('broker-detail-page');
    await expect(root).toBeVisible({timeout: LOAD_TIMEOUT});
    // The header is drawn from the loaded broker: it is the barrier before `data-busy` can mean "finished".
    await expect(page.getByTestId('broker-quota-badge')).toBeVisible({timeout: LOAD_TIMEOUT});
    await waitForSettled(root, LOAD_TIMEOUT);
    await expect(page.getByTestId('broker-overview-tab')).toBeVisible({timeout: UI_TIMEOUT});
    await expect(page.getByTestId('broker-cash-balances')).toBeVisible({timeout: UI_TIMEOUT});
}

/**
 * Expand the grouped banner and *stay* expanded: the page renders the banner again each time a report lands, so a toggle
 * clicked once can land on a banner about to be replaced by a collapsed one. Retried until `aria-expanded` sticks.
 */
async function expandBanner(page: Page): Promise<void> {
    const toggle = page.getByTestId('data-quality-toggle');
    await expect(toggle).toBeVisible({timeout: LOAD_TIMEOUT});
    await expect(async () => {
        if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
        expect(await toggle.getAttribute('aria-expanded')).toBe('true');
    }).toPass({timeout: 15_000});
}

// ---------------------------------------------------------------------------
// Served issues and held syncs
// ---------------------------------------------------------------------------

type ReportBody = {broker_ids?: number[]; include_summary?: boolean} | null;

type IssueProbe = {
    /** The body of every report the page asked, in order. */
    reports: ReportBody[];
};

type HeldSync<B> = {
    bodies: B[];
    /** Set just before the held request is answered: a report requested after it is the reload. */
    answered: boolean;
    release: () => void;
};

/**
 * Hold every POST to `path` this page sends until `release()`, then answer it with `answer(body)`.
 *
 * Nothing reaches a provider and nothing is written: what is under test is the request the button builds and what the page
 * does with the answer. Holding the request is what makes the busy state observable without a clock.
 */
async function holdPost<B>(page: Page, path: string, answer: (body: B) => unknown): Promise<HeldSync<B>> {
    let open: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
        open = resolve;
    });
    const held: HeldSync<B> = {bodies: [], answered: false, release: () => open()};
    await page.route(`**${path}`, async (route) => {
        if (route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        const body = route.request().postDataJSON() as B;
        held.bodies.push(body);
        await gate;
        const canned = answer(body);
        held.answered = true;
        await route.fulfill({json: canned});
    });
    return held;
}

/**
 * Serve `issue` in the summary of every report this page receives, until the held sync is answered; the reload that follows
 * it no longer carries the issue (the sync fixed it). Issues the backend reported under the same code are dropped first, so
 * the row a test asserts on is the one it served. Every request body is recorded.
 */
async function serveIssue(page: Page, issue: {code: string; [field: string]: unknown}, sync: HeldSync<unknown>): Promise<IssueProbe> {
    const probe: IssueProbe = {reports: []};
    await page.route(`**${REPORT_PATH}`, async (route) => {
        probe.reports.push(route.request().postDataJSON() as ReportBody);
        // Decided when the request leaves the page, not when its answer comes back.
        const inject = !sync.answered;
        const response = await route.fetch();
        const body = await response.json();
        const summary = body?.summary;
        if (summary) {
            summary.data_quality = summary.data_quality ?? {issues: []};
            const kept = ((summary.data_quality.issues ?? []) as Array<{code?: string}>).filter((existing) => existing.code !== issue.code);
            summary.data_quality.issues = inject ? [...kept, issue] : kept;
        }
        await route.fulfill({response, json: body});
    });
    return probe;
}

type FxSyncBody = {pairs: string[]; start: string; end: string};

/** The issue the engine emits for a configured real-provider pair whose rates are missing on some dates. */
function missingFxRatesIssue() {
    return {
        domain: 'portfolio',
        code: 'MISSING_FX_RATES',
        severity: 'warning',
        message_i18n_key: 'dataQuality.missingFxRates',
        message_params: {count: 1, date_from: daysAgoIso(60), date_to: daysAgoIso(30), dates_count: 4},
        count: 1,
        affected_fx_pairs: ['EUR-USD'],
        cta_action: 'sync_fx_pair',
        cta_target: 'EUR-USD',
        group_key: 'missing_fx_rates',
    };
}

/** An asset id no row of the database is expected to hold: the price sync is answered by the stub, never by the backend. */
const STALE_ASSET_ID = 987_654;

function stalePriceIssue() {
    return {
        domain: 'portfolio',
        code: 'STALE_PRICE',
        severity: 'warning',
        message_i18n_key: 'dataQuality.stalePrice',
        message_params: {count: 1},
        count: 1,
        affected_asset_ids: [STALE_ASSET_ID],
        affected_asset_names: ['Banner stub asset'],
        cta_action: 'sync_asset_prices',
        cta_target: String(STALE_ASSET_ID),
        group_key: 'stale_price',
    };
}

// ---------------------------------------------------------------------------
// What each role sees and does
// ---------------------------------------------------------------------------

async function checkFxSync(world: World, role: Role): Promise<void> {
    const {brokerId, page} = await openBrokerAs(world, role);
    const sync = await holdPost<FxSyncBody>(page, FX_SYNC_PATH, (body) => {
        const answer = {
            results: [{pair: 'EUR-USD', status: 'ok', points_fetched: 5, points_changed: 5, provider_used: 'ECB'}],
            success_count: 1,
            date_range: {start: body.start, end: body.end},
            total_points_changed: 5,
        };
        schemas.FXSyncBulkResponse.parse(answer);
        return answer;
    });
    await serveIssue(page, missingFxRatesIssue(), sync);
    try {
        await openBrokerPage(page, brokerId);
        await expandBanner(page);
        const row = page.getByTestId('data-quality-issue-MISSING_FX_RATES');
        await expect(row, 'every other MISSING_FX_RATES row is stripped: this one is ours').toHaveCount(1);
        const cta = row.getByTestId('data-quality-cta-MISSING_FX_RATES');
        await expect(cta).toBeEnabled();
        expect(sync.bodies, 'nothing syncs before the user asks').toEqual([]);

        const root = page.getByTestId('broker-detail-page');
        const since = await eventSeq(page);
        await cta.click();
        await expect.poll(() => sync.bodies.length).toBe(1);
        expect(sync.bodies[0]?.pairs).toEqual(['EUR-USD']);
        await expect(cta, 'the CTA is busy while its sync runs').toBeDisabled();
        await expect(root, 'the page says it is busy while the sync is held').toHaveAttribute('data-busy', 'true');

        sync.release();
        const synced = await waitForEvent(page, 'fx.rates.synced', {since, timeout: SYNC_TIMEOUT});
        expect(synced.detail).toMatchObject({origin: 'dashboard-banner', pairs: ['EUR-USD'], outcome: 'ok', stillMissing: false});
        await waitForSettled(root, SYNC_TIMEOUT);
        await expect(root).toHaveAttribute('data-busy', 'false');
        expect(sync.bodies, 'one click, one sync').toHaveLength(1);
    } finally {
        sync.release();
        await page.unrouteAll({behavior: 'ignoreErrors'});
    }
}

test.describe('Broker page — data-quality banner', () => {
    test('OWNER: a missing exchange rate shows «Sync rates»; one click sends one sync and the page is busy meanwhile', async ({world}) => {
        await checkFxSync(world, 'OWNER');
    });

    test('VIEWER (shared, share 0): the banner and «Sync rates» are offered too, and work the same', async ({world}) => {
        await checkFxSync(world, 'VIEWER');
    });

    test('VIEWER (shared, share 0): a stale price shows «Sync prices»; one click sends one price sync and the page settles', async ({world}) => {
        const {brokerId, page} = await openBrokerAs(world, 'VIEWER');
        const sync = await holdPost<Array<{asset_id: number; date_range: {start: string; end: string}}>>(page, PRICES_SYNC_PATH, (body) => {
            const answer = {
                results: body.map((item) => ({asset_id: item.asset_id, status: 'ok', points_fetched: 0, points_changed: 0, provider_used: 'MOCK'})),
                success_count: body.length,
            };
            schemas.FABulkRefreshResponse.parse(answer);
            return answer;
        });
        await serveIssue(page, stalePriceIssue(), sync);
        try {
            await openBrokerPage(page, brokerId);
            await expandBanner(page);
            const row = page.getByTestId('data-quality-issue-STALE_PRICE');
            await expect(row, 'every other STALE_PRICE row is stripped: this one is ours').toHaveCount(1);
            const cta = row.getByTestId('data-quality-cta-STALE_PRICE');
            await expect(cta).toBeEnabled();
            expect(sync.bodies, 'nothing syncs before the user asks').toEqual([]);

            const root = page.getByTestId('broker-detail-page');
            await cta.click();
            await expect.poll(() => sync.bodies.length).toBe(1);
            // The assets the issue flags, from the day after their last stored price ('resume').
            expect(sync.bodies[0]).toMatchObject([{asset_id: STALE_ASSET_ID, date_range: {start: 'resume'}}]);
            await expect(cta, 'the CTA is busy while its sync runs').toBeDisabled();
            await expect(root, 'the page says it is busy while the sync is held').toHaveAttribute('data-busy', 'true');

            sync.release();
            // The sync fixed the issue: the reload no longer carries it, and the page is finished.
            await expect(row).toHaveCount(0, {timeout: SYNC_TIMEOUT});
            await waitForSettled(root, SYNC_TIMEOUT);
            expect(sync.bodies, 'one click, one sync').toHaveLength(1);
        } finally {
            sync.release();
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });

    test('OWNER: every report the broker page asks carries this broker alone', async ({world}) => {
        const {brokerId, page} = await openBrokerAs(world, 'OWNER');
        const reports: ReportBody[] = [];
        await page.route(`**${REPORT_PATH}`, async (route) => {
            reports.push(route.request().postDataJSON() as ReportBody);
            await route.fallback();
        });
        try {
            await openBrokerPage(page, brokerId);
            expect(
                reports.some((body) => body?.include_summary === true),
                'the page asked a report with its summary',
            ).toBe(true);
            for (const body of reports) {
                expect(body?.broker_ids, `report body ${JSON.stringify(body)}`).toEqual([brokerId]);
            }
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });
});
