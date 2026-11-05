/**
 * broker-page-roles.spec.ts — what the broker's page shows to each ROLE of the signed-in user.
 *
 * The page is a shell around `PortfolioView` (scope: broker). Three roles open it, and this spec pins what each sees:
 *
 *   header          broker-quota-badge and broker-share-button for every role; broker-edit-button only for OWNER and EDITOR.
 *                   The share button opens the Info tab.
 *   overview        a broker only SHARED with the user (EDITOR or VIEWER, share 0) opens on its own page and loads: the page
 *                   root settles (`data-busy="false"`) and the Overview tab shows the cash block. The Dashboard never lists
 *                   such a broker; the broker page must open it.
 *   Transactions    Import and New transaction only for OWNER and EDITOR; the import history and the link to the
 *                   Transactions page for every role. New transaction opens the bulk workspace.
 *   Info            the sharing section is visible to every role (editing it is not under test here).
 *
 * One test per role, so a red names the role. Owned data: each test registers disposable accounts (the owner, and for the
 * shared roles a second one), creates its own broker and one DEPOSIT through the API, grants the role with the broker-access
 * API, and the world fixture deletes everything by id afterwards. Nothing is found by position, no count of the global
 * database is read, and no translated text is asserted.
 *
 * Key data-testids:
 *   broker-detail-page [data-busy], broker-quota-badge, broker-edit-button, broker-share-button
 *   broker-overview-tab, broker-cash-balances
 *   broker-tab-transazioni, broker-transactions-tab, broker-transactions-actions, broker-transactions, tx-table
 *   broker-import-transactions, broker-new-transaction, broker-show-import-history, broker-view-in-transactions
 *   tx-bulk-modal
 *   broker-info-tab, broker-sharing-section
 */

import {expect, test as base, type APIRequestContext, type Browser, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {createOwnedBroker, deleteDisposableUser, registerDisposableUser, skipDueFlowsExcept} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, openOwnedAccount, type OwnedAccount} from '../fixtures/owned-pair';

const API = '/api/v1';
const UI_TIMEOUT = 10_000;
const LOAD_TIMEOUT = 20_000;

type Role = 'OWNER' | 'EDITOR' | 'VIEWER';

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
            if (failures.length > 0) throw new AggregateError(failures, 'broker-page-roles could not delete everything it created');
        }
    },
});

test.setTimeout(90_000);

/**
 * The owner's broker with one deposit on it, and the page of the account that holds `role` on it: the owner's own page for
 * OWNER; for EDITOR and VIEWER a second disposable account, granted the role with no share, in a browser context of its own.
 */
async function openBrokerAs(world: World, role: Role): Promise<{brokerId: number; page: Page}> {
    await openOwnedAccount(world.page, world.accounts, world.owned, 'fbrole');
    const owner = world.owned.user;
    if (!owner) throw new Error('the owner account was not recorded');
    const broker = await createOwnedBroker(world.page, 'fbrole', world.owned.brokerIds);
    await commitCreates(world.page, [{broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'EUR', amount: '1234.56'}, description: 'role page deposit'}], 'give the broker something to load');
    if (role === 'OWNER') return {brokerId: broker.id, page: world.page};

    const sharedWith = await registerDisposableUser(world.accounts, `fbrole${role === 'EDITOR' ? 'e' : 'v'}`);
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

// ---------------------------------------------------------------------------
// What each role sees
// ---------------------------------------------------------------------------

const canEdit = (role: Role): boolean => role === 'OWNER' || role === 'EDITOR';

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

async function checkRole(world: World, role: Role): Promise<void> {
    const {brokerId, page} = await openBrokerAs(world, role);
    const edits = canEdit(role);

    // A broker only shared with the user opens on its own page, and loads.
    await openBrokerPage(page, brokerId);

    // Header. The badge and the share button are drawn (presence barrier), so an absent edit button is "not offered".
    await expect(page.getByTestId('broker-quota-badge')).toBeVisible();
    await expect(page.getByTestId('broker-share-button')).toBeVisible();
    if (edits) await expect(page.getByTestId('broker-edit-button')).toBeVisible();
    else await expect(page.getByTestId('broker-edit-button')).toHaveCount(0);

    // Transactions tab: the table has loaded the broker's row before the bar is read.
    await page.getByTestId('broker-tab-transazioni').click();
    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: UI_TIMEOUT});
    await expect(page.getByTestId('broker-transactions').getByTestId('tx-table')).toBeVisible({timeout: LOAD_TIMEOUT});
    const bar = page.getByTestId('broker-transactions-actions');
    await expect(bar).toBeVisible({timeout: UI_TIMEOUT});
    // For every role.
    await expect(bar.getByTestId('broker-show-import-history')).toBeVisible();
    await expect(bar.getByTestId('broker-view-in-transactions')).toBeVisible();
    // Only for who can edit.
    if (edits) {
        await expect(bar.getByTestId('broker-import-transactions')).toBeVisible();
        await expect(bar.getByTestId('broker-new-transaction')).toBeVisible();
    } else {
        await expect(bar.getByTestId('broker-import-transactions')).toHaveCount(0);
        await expect(bar.getByTestId('broker-new-transaction')).toHaveCount(0);
    }

    // Share button: opens the Info tab, whose sharing section every role sees.
    await page.getByTestId('broker-share-button').click();
    await expect(page.getByTestId('broker-info-tab')).toBeVisible({timeout: UI_TIMEOUT});
    await expect(page.getByTestId('broker-sharing-section')).toBeVisible({timeout: UI_TIMEOUT});

    // New transaction opens the bulk workspace. Last: nothing else on the page is touched afterwards.
    if (edits) {
        await page.getByTestId('broker-tab-transazioni').click();
        await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: UI_TIMEOUT});
        await page.getByTestId('broker-new-transaction').click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: UI_TIMEOUT});
    }
}

test.describe('Broker page — what each role sees', () => {
    test('OWNER: edit, share, import and new transaction; the overview loads', async ({world}) => {
        await checkRole(world, 'OWNER');
    });

    test('EDITOR (shared, share 0): the page opens and loads; edit, import and new transaction are offered', async ({world}) => {
        await checkRole(world, 'EDITOR');
    });

    test('VIEWER (shared, share 0): the page opens and loads; no edit, import or new transaction, but share and history', async ({world}) => {
        await checkRole(world, 'VIEWER');
    });
});
