/**
 * broker-transactions-period.spec.ts — the broker page's Transactions tab keeps to the period chosen in the toolbar.
 *
 * The tab used to list the broker's whole history whatever the toolbar said; since delivery 4 it follows the period, as the
 * Dashboard's does. This spec pins, on a broker the test owns with two DEPOSITs (one 400 days ago, one 5 days ago):
 *
 *   rows      with 1M chosen the recent row is in the table and the old one is not; widening to 2Y brings the old one in too.
 *   request   the tab's `GET /transactions` carries `broker_id` of the broker and a `date_start` and `date_end`.
 *   link      «view in Transactions» carries `broker_id` and the period (`date_start`, `date_end`), and follows it when it moves.
 *
 * The period lives in a global store (`dateRangeStore`, persisted in the sessionStorage of the tab); every Playwright test has a
 * browser context of its own, so a period chosen here reaches no other spec. Owned data: each test registers a disposable
 * account, creates its own broker and rows through the API, and the world fixture deletes them by id afterwards. Rows are found by
 * the id the commit returned (`tx-{id}`), the description only this test knows is read back from `tx-desc-{id}`; no count of the
 * global database is read and no translated text is asserted.
 *
 * Key data-testids:
 *   broker-detail-page [data-busy], broker-quota-badge, broker-overview-tab
 *   date-preset-1m, date-preset-2y [data-active]
 *   broker-tab-transazioni, broker-transactions-tab, broker-transactions, tx-table, tx-desc-{id}
 *   broker-transactions-actions, broker-view-in-transactions
 */

import {expect, test as base, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, openOwnedAccount, type OwnedAccount} from '../fixtures/owned-pair';

const UI_TIMEOUT = 10_000;
const LOAD_TIMEOUT = 20_000;

// ---------------------------------------------------------------------------
// The world: a disposable account, its broker and two rows, deleted by id afterwards
// ---------------------------------------------------------------------------

type World = {
    page: Page;
    /** The owner account and its broker (recorded for cleanup the moment they exist). */
    owned: OwnedAccount;
    /** A context of its own that registers and deletes accounts; never signed in by a page. */
    accounts: APIRequestContext;
};

const test = base.extend<{world: World}>({
    world: async ({page, browser}, use) => {
        const accountsContext = await browser.newContext();
        const world: World = {page, owned: emptyOwnedAccount(), accounts: accountsContext.request};
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
            // The broker goes by `force`, with every row left on it; the account last.
            await attempt(() => cleanupOwnedAccount(page, accountsContext.request, world.owned));
            await attempt(() => accountsContext.close());
            if (failures.length > 0) throw new AggregateError(failures, 'broker-transactions-period could not delete everything it created');
        }
    },
});

test.setTimeout(90_000);

type PeriodBroker = {
    brokerId: number;
    /** The deposit 5 days ago, and the description only this test knows. */
    recent: {id: number; description: string};
    /** The deposit 400 days ago. */
    old: {id: number; description: string};
};

/** A broker of the signed-in disposable owner with a DEPOSIT 400 days ago and one 5 days ago. */
async function createPeriodBroker(world: World): Promise<PeriodBroker> {
    await openOwnedAccount(world.page, world.accounts, world.owned, 'fbper');
    const broker = await createOwnedBroker(world.page, 'fbper', world.owned.brokerIds);
    const marker = uniqueSuffix();
    const recent = `period recent ${marker}`;
    const old = `period old ${marker}`;
    const [recentId, oldId] = await commitCreates(
        world.page,
        [
            {broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(5), cash: {code: 'EUR', amount: '100'}, description: recent},
            {broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(400), cash: {code: 'EUR', amount: '200'}, description: old},
        ],
        'give the broker a recent and an old deposit',
    );
    return {brokerId: broker.id, recent: {id: recentId, description: recent}, old: {id: oldId, description: old}};
}

// ---------------------------------------------------------------------------
// The page, its period and its requests
// ---------------------------------------------------------------------------

/** A `GET /transactions` of the tab: the one that asks a broker's rows (the partner lookups ask by ids). */
type TabRequest = {brokerId: string; dateStart: string | null; dateEnd: string | null};

/** Record the broker-scoped transaction lists this page asks, from now on. */
function recordTabRequests(page: Page): TabRequest[] {
    const asked: TabRequest[] = [];
    page.on('request', (request) => {
        if (request.method() !== 'GET') return;
        const url = new URL(request.url());
        if (url.pathname !== '/api/v1/transactions') return;
        const brokerId = url.searchParams.get('broker_id');
        if (brokerId === null) return;
        asked.push({brokerId, dateStart: url.searchParams.get('date_start'), dateEnd: url.searchParams.get('date_end')});
    });
    return asked;
}

/** The broker's page, loaded and on its Transactions tab: the table is drawn. */
async function openTransactionsTab(page: Page, brokerId: number): Promise<void> {
    await navigateTo(page, `/brokers/${brokerId}`);
    const root = page.getByTestId('broker-detail-page');
    await expect(root).toBeVisible({timeout: LOAD_TIMEOUT});
    // The header is drawn from the loaded broker: it is the barrier before `data-busy` can mean "finished".
    await expect(page.getByTestId('broker-quota-badge')).toBeVisible({timeout: LOAD_TIMEOUT});
    await waitForSettled(root, LOAD_TIMEOUT);
    await page.getByTestId('broker-tab-transazioni').click();
    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: UI_TIMEOUT});
    await expect(page.getByTestId('broker-transactions').getByTestId('tx-table')).toBeVisible({timeout: LOAD_TIMEOUT});
}

/** Choose a preset of the toolbar and wait until it is the one marked active. Idempotent: a preset already in force stays. */
async function choosePreset(page: Page, preset: '1m' | '2y'): Promise<void> {
    const button = page.getByTestId(`date-preset-${preset}`);
    await expect(button).toBeVisible({timeout: UI_TIMEOUT});
    if ((await button.getAttribute('data-active')) !== 'true') await button.click();
    await expect(button).toHaveAttribute('data-active', 'true', {timeout: UI_TIMEOUT});
}

const table = (page: Page): Locator => page.getByTestId('broker-transactions');
const rowOf = (page: Page, id: number): Locator => table(page).locator(`tr[data-row-id="tx-${id}"]`);

/** The row of `id` is in the table, and says the description this test gave it. */
async function expectRowInTable(page: Page, row: {id: number; description: string}): Promise<void> {
    await expect(rowOf(page, row.id)).toHaveCount(1, {timeout: LOAD_TIMEOUT});
    await expect(table(page).getByTestId(`tx-desc-${row.id}`)).toHaveText(row.description, {timeout: UI_TIMEOUT});
}

/** The period «view in Transactions» carries, read from its `href`. */
async function linkPeriod(page: Page): Promise<{brokerId: string | null; dateStart: string | null; dateEnd: string | null}> {
    const href = await page.getByTestId('broker-transactions-actions').getByTestId('broker-view-in-transactions').getAttribute('href');
    if (href === null) throw new Error('the link to the Transactions page has no href');
    const url = new URL(href, 'http://librefolio.invalid');
    return {brokerId: url.searchParams.get('broker_id'), dateStart: url.searchParams.get('date_start'), dateEnd: url.searchParams.get('date_end')};
}

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

// ---------------------------------------------------------------------------
// The tests
// ---------------------------------------------------------------------------

test.describe('Broker page — Transactions tab keeps to the period', () => {
    test('the rows follow the period: 1M holds the recent deposit and not the old one, 2Y holds both', async ({world}) => {
        const {brokerId, recent, old} = await createPeriodBroker(world);
        const page = world.page;
        await openTransactionsTab(page, brokerId);

        await choosePreset(page, '1m');
        // The recent row is the presence barrier: the old one is absent from the same answer, not from a table still loading.
        await expectRowInTable(page, recent);
        await expect(rowOf(page, old.id), 'a deposit 400 days ago is outside a one-month period').toHaveCount(0);

        // Widened to two years the old deposit comes in; the recent one stays.
        await choosePreset(page, '2y');
        await expectRowInTable(page, old);
        await expectRowInTable(page, recent);

        // And back: the period is a filter, not a one-way expansion.
        await choosePreset(page, '1m');
        await expect(rowOf(page, old.id)).toHaveCount(0, {timeout: LOAD_TIMEOUT});
        await expectRowInTable(page, recent);
    });

    test('the request carries the broker and the period, no longer the broker alone', async ({world}) => {
        const {brokerId, recent} = await createPeriodBroker(world);
        const page = world.page;
        const asked = recordTabRequests(page);
        await openTransactionsTab(page, brokerId);
        await expectRowInTable(page, recent);

        const own = () => asked.filter((request) => request.brokerId === String(brokerId));
        await expect.poll(() => own().length, {message: 'the tab asked the broker’s transactions'}).toBeGreaterThan(0);
        expect(
            asked.map((request) => request.brokerId),
            'the tab asks for this broker alone',
        ).toEqual(asked.map(() => String(brokerId)));
        for (const request of own()) {
            expect(request.dateStart, `a start date: ${JSON.stringify(request)}`).toMatch(ISO_DAY);
            expect(request.dateEnd, `an end date: ${JSON.stringify(request)}`).toMatch(ISO_DAY);
            expect(Date.parse(request.dateStart ?? '') <= Date.parse(request.dateEnd ?? ''), 'the period runs forward').toBe(true);
        }

        // Moving the period asks again with the new start, the broker still alone.
        const before = own().length;
        await choosePreset(page, '2y');
        await expect.poll(() => own().length, {message: 'widening the period asked the rows again'}).toBeGreaterThan(before);
        const widened = own().at(-1);
        const firstStart = own()[0]?.dateStart;
        expect(widened?.dateStart, 'the wider period starts earlier').toMatch(ISO_DAY);
        expect(Date.parse(widened?.dateStart ?? '') < Date.parse(firstStart ?? ''), 'the 2Y request starts before the opening one').toBe(true);
    });

    test('«view in Transactions» carries the broker and the period, and follows it', async ({world}) => {
        const {brokerId, recent} = await createPeriodBroker(world);
        const page = world.page;
        const asked = recordTabRequests(page);
        await openTransactionsTab(page, brokerId);

        await choosePreset(page, '1m');
        await expectRowInTable(page, recent);
        await expect(page.getByTestId('broker-transactions-actions').getByTestId('broker-view-in-transactions')).toBeVisible({timeout: UI_TIMEOUT});

        const narrow = await linkPeriod(page);
        expect(narrow.brokerId, 'the link filters to this broker').toBe(String(brokerId));
        expect(narrow.dateStart, 'the link carries the start of the period').toMatch(ISO_DAY);
        expect(narrow.dateEnd, 'the link carries the end of the period').toMatch(ISO_DAY);
        // The same period the tab asks the rows for. Polled: the recent row is also in the answer to the opening, wider period.
        const lastAsked = () => asked.filter((request) => request.brokerId === String(brokerId)).at(-1);
        await expect.poll(() => lastAsked()?.dateStart, {message: 'the tab asked the rows of the period the link carries'}).toBe(narrow.dateStart);
        expect(lastAsked()?.dateEnd).toBe(narrow.dateEnd);

        // The link follows the period: a wider one starts earlier.
        await choosePreset(page, '2y');
        await expect.poll(async () => Date.parse((await linkPeriod(page)).dateStart ?? ''), {message: 'the link follows the period to 2Y'}).toBeLessThan(Date.parse(narrow.dateStart ?? ''));
        const wide = await linkPeriod(page);
        expect(wide.brokerId).toBe(String(brokerId));
        expect(wide.dateEnd, 'the end of the period stays').toMatch(ISO_DAY);
    });
});
