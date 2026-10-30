/**
 * broker-transactions-actions.spec.ts — FB-17: the broker page's Transactions tab edits like the Transactions page.
 *
 * Who can edit a broker (OWNER or EDITOR) gets, on the tab `broker-transactions`:
 *   - the selection bar (`selection-toolbar`, `data-selected-count`) as soon as one row is ticked, in the commands row
 *     of the tab (`broker-transactions-actions`), with exactly Edit / Clone / Delete;
 *   - the actions column, with Edit / Clone / Delete on the rows they may edit, and no Split — the tab wires no
 *     handler for it, and an action nobody listens to is not drawn;
 *   - Edit, Clone and Delete (from the bar or from a row) open the bulk workspace on the selected transactions with
 *     the matching intent, reading the originals from the transactions store the page fills (so the row shows the
 *     real type, date and amount, not an empty or broken row);
 *   - after a commit the selection is empty and the table shows the saved value.
 * A row the user cannot edit (a pair whose other half is on a broker the user only reads) is left out of Edit and
 * Delete with a warning, and a selection made only of such rows opens nothing and says so (error).
 * Who only views the broker (VIEWER) gets neither the bar nor the actions column, though the rows can be ticked.
 * The shortcuts around them do not change: the link to the Transactions page, Import and New transaction.
 *
 * Owned data. Every test registers disposable accounts (an owner; a viewer or a second editor when the case needs
 * one), creates its own broker(s) and rows through the API, and the world fixture deletes them by id afterwards: the
 * rows are found by id or by a description only the test knows, never by position, and no count of the global
 * database is read. Nothing a test commits touches a shared row.
 *
 * Nothing here reads translated text. Intent of the workspace: `tx-bulk-row-status[data-status]`
 * (`original` = edit, `new` = clone, `delete`); the data of a row: the id cell, `tx-bulk-date[data-date]`, the digits
 * of the cash cell and the type icon's file. Warnings and errors: the toast variant (`toast-warning`, `toast-error`).
 *
 * Key data-testids:
 *   broker-detail-page, broker-tab-transazioni, broker-transactions-tab, broker-transactions-actions
 *   broker-transactions (the tab's table), tx-table, dt-row-checkbox-tx-{id}, dt-actions-header, row-actions-tx-{id}
 *   selection-toolbar [data-selected-count], toolbar-action-edit|clone|delete
 *   context-menu, context-menu-action-{view|edit|clone|split|delete}
 *   tx-bulk-modal, tx-bulk-body, tx-bulk-modal-root, tx-bulk-close, tx-bulk-commit, tx-bulk-row-status, tx-bulk-date
 *   tx-form-modal, tx-form-optional-toggle, tx-form-description, tx-form-save, tx-desc-{id}
 *   broker-view-in-transactions, broker-import-transactions, broker-new-transaction
 */

import {expect, test as base, type APIRequestContext, type Browser, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {createOwnedBroker, deleteDisposableUser, registerDisposableUser, skipDueFlowsExcept, type DisposableUser} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, jsonFrom, openOwnedAccount, readTransactions, type OwnedAccount} from '../fixtures/owned-pair';

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;
const UI_TIMEOUT = 10_000;
const LOAD_TIMEOUT = 20_000;

// ---------------------------------------------------------------------------
// The world: disposable accounts, their brokers and rows, deleted by id afterwards
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
    /** A value every name of this test carries. */
    tag: string;
};

type OwnedTx = {id: number; description: string; date: string; amount: string; type: 'DEPOSIT' | 'WITHDRAWAL'};

const test = base.extend<{world: World}>({
    world: async ({page, browser}, use, testInfo) => {
        const accountsContext = await browser.newContext();
        const world: World = {page, browser, owned: emptyOwnedAccount(), accounts: accountsContext.request, cleanups: [], tag: `w${testInfo.workerIndex}${Math.random().toString(36).slice(2, 7)}`};
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
            // The owner last: its brokers go by `force`, with every row left on them.
            await attempt(() => cleanupOwnedAccount(page, accountsContext.request, world.owned));
            await attempt(() => accountsContext.close());
            if (failures.length > 0) throw new AggregateError(failures, 'broker-transactions-actions could not delete everything it created');
        }
    },
});

test.setTimeout(90_000);

/** Register the owner and sign `world.page` in as it. */
async function openOwner(world: World): Promise<DisposableUser> {
    await openOwnedAccount(world.page, world.accounts, world.owned, 'fb17');
    if (!world.owned.user) throw new Error('the owner account was not recorded');
    return world.owned.user;
}

/** One deposit or withdrawal described by `label`, as the API takes it. */
function txSpec(brokerId: number, kind: OwnedTx['type'], daysAgo: number, amount: string, description: string) {
    return {broker_id: brokerId, type: kind, date: daysAgoIso(daysAgo), cash: {code: 'EUR', amount}, description};
}

/**
 * Three standalone rows on one new broker of the owner: two deposits and a withdrawal. Amounts are distinct with
 * distinct digit strings, so a row's cash cell can be told from another's without reading a formatted number.
 */
async function ownRows(world: World): Promise<{brokerId: number; d1: OwnedTx; d2: OwnedTx; w3: OwnedTx}> {
    const broker = await createOwnedBroker(world.page, 'fb17', world.owned.brokerIds);
    const mk = (kind: OwnedTx['type'], daysAgo: number, amount: string, label: string): OwnedTx => ({id: 0, type: kind, date: daysAgoIso(daysAgo), amount, description: `FB17 ${label} ${world.tag}`});
    const [d1, d2, w3] = [mk('DEPOSIT', 30, '1234.56', 'd1'), mk('DEPOSIT', 29, '2345.67', 'd2'), mk('WITHDRAWAL', 10, '-345.67', 'w3')];
    const ids = await commitCreates(
        world.page,
        [d1, d2, w3].map((tx) => ({broker_id: broker.id, type: tx.type, date: tx.date, cash: {code: 'EUR', amount: tx.amount}, description: tx.description})),
        'own the rows of the broker',
    );
    [d1.id, d2.id, w3.id] = ids;
    return {brokerId: broker.id, d1, d2, w3};
}

// ---------------------------------------------------------------------------
// The page
// ---------------------------------------------------------------------------

const detail = (page: Page) => page.getByTestId('broker-detail-page');
const commandsRow = (page: Page) => page.getByTestId('broker-transactions-actions');
const txTable = (page: Page) => page.getByTestId('broker-transactions');
const tableRow = (page: Page, id: number) => txTable(page).locator(`tr[data-row-id="tx-${id}"]`);
const rowCheckbox = (page: Page, id: number) => txTable(page).getByTestId(`dt-row-checkbox-tx-${id}`);
const bar = (page: Page) => commandsRow(page).getByTestId('selection-toolbar');
const bulkModal = (page: Page) => page.getByTestId('tx-bulk-modal');
const bulkRows = (page: Page) => page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');

/** The broker's page on the Transactions tab; ends with the table drawn and every given row on screen. */
async function openTransactionsTab(page: Page, brokerId: number, rows: Array<{id: number; description: string}>): Promise<void> {
    await navigateTo(page, `/brokers/${brokerId}`);
    await expect(detail(page)).toBeVisible({timeout: LOAD_TIMEOUT});
    await page.getByTestId('broker-tab-transazioni').click();
    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: UI_TIMEOUT});
    await expect(txTable(page).getByTestId('tx-table')).toBeVisible({timeout: LOAD_TIMEOUT});
    for (const row of rows) await expect(tableRow(page, row.id), `${row.description} is on screen`).toBeVisible({timeout: UI_TIMEOUT});
}

/** Tick a row; ends with its checkbox checked. */
async function tick(page: Page, id: number): Promise<void> {
    const checkbox = rowCheckbox(page, id);
    await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
    await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
}

/** The bar's count as a string, `absent` when there is no bar. One-shot: callers poll it. */
async function barCount(page: Page): Promise<string> {
    const toolbar = bar(page);
    if ((await toolbar.count()) === 0) return 'absent';
    return (await toolbar.getAttribute('data-selected-count')) ?? 'no-count';
}

/** Nothing is selected: no bar (or a bar counting 0) and every given row unchecked. */
async function expectNothingSelected(page: Page, rows: Array<{id: number}>): Promise<void> {
    await expect.poll(() => barCount(page), {message: 'the selection bar is gone (or counts 0)', timeout: UI_TIMEOUT}).toMatch(/^(absent|0)$/);
    for (const row of rows) await expect(rowCheckbox(page, row.id), `tx-${row.id} is unchecked`).toHaveAttribute('data-state', 'unchecked');
}

type Intent = 'original' | 'new' | 'delete';

/**
 * The workspace opened on `tx` with the given intent and showing the real data of the transaction — read from the
 * store, not an empty draft: the row's own status, the id (edit and delete), the date, the digits of the amount and
 * the type icon. Ends with the workspace settled.
 */
async function expectWorkspaceRow(page: Page, tx: OwnedTx, intent: Intent): Promise<void> {
    await expect(bulkModal(page)).toBeVisible({timeout: UI_TIMEOUT});
    const row = bulkRows(page).filter({hasText: tx.description});
    await expect(row, `${tx.description} is in the workspace once`).toHaveCount(1, {timeout: UI_TIMEOUT});
    await expect(row.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', intent);
    // A clone keeps the original's date (tx-clone.spec.ts, T3), so the stored date is expected for every intent.
    await expect(row.getByTestId('tx-bulk-date')).toHaveAttribute('data-date', tx.date);
    await expect(row.locator('td[data-column-id="type"] img')).toHaveAttribute('src', new RegExp(`/${tx.type.toLowerCase()}\\.png$`));
    const digits = tx.amount.replace(/\D/g, '');
    await expect.poll(async () => ((await row.locator('td[data-column-id="cash"]').innerText()) ?? '').replace(/\D/g, ''), {message: `the cash cell carries the digits ${digits}`}).toContain(digits);
    if (intent !== 'new') await expect(row.locator('td[data-column-id="id"]')).toContainText(`#${tx.id}`);
}

/**
 * Close the workspace without saving; it was not touched, so one click closes it.
 *
 * A workspace opened on exactly ONE transaction to edit or clone puts the transaction's form on top of it (the same
 * on the Transactions page): `withForm` says that case, and the form is cancelled first.
 */
async function closeWorkspace(page: Page, opts: {withForm?: boolean} = {}): Promise<void> {
    if (opts.withForm) {
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'a single-row edit or clone opens the form on top of the workspace').toBeVisible({timeout: UI_TIMEOUT});
        await form.getByTestId('tx-form-cancel').click();
        await expect(form).toBeHidden({timeout: UI_TIMEOUT});
    } else {
        await expect(page.getByTestId('tx-form-modal'), 'a workspace on several rows or a delete opens no form').toHaveCount(0);
    }
    await waitForSettled(page.getByTestId('tx-bulk-modal-root'), 25_000);
    await page.getByTestId('tx-bulk-close').click();
    await expect(bulkModal(page), 'an untouched workspace closes on the first click').toBeHidden({timeout: UI_TIMEOUT});
}

/** A row's own menu → one action; ends with the action clicked. */
async function clickRowAction(page: Page, id: number, action: 'view' | 'edit' | 'clone' | 'split' | 'delete'): Promise<void> {
    await txTable(page).getByTestId(`row-actions-tx-${id}`).click();
    const menu = page.getByTestId('context-menu');
    await expect(menu).toBeVisible({timeout: UI_TIMEOUT});
    await menu.getByTestId(`context-menu-action-${action}`).click();
}

/** A row's own menu, left open; returns the menu. */
async function openRowMenu(page: Page, id: number): Promise<Locator> {
    await txTable(page).getByTestId(`row-actions-tx-${id}`).click();
    const menu = page.getByTestId('context-menu');
    await expect(menu).toBeVisible({timeout: UI_TIMEOUT});
    return menu;
}

// ---------------------------------------------------------------------------
// The workspace's form (to change a description) and its Save All
// ---------------------------------------------------------------------------

/** The description lives in the collapsible optional `<details>`: read its real `open` state, never click blind. */
async function fillDescription(page: Page, text: string): Promise<void> {
    const details = page.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(details).toBeVisible({timeout: UI_TIMEOUT});
    if (!(await details.evaluate((element) => (element as HTMLDetailsElement).open))) await page.getByTestId('tx-form-optional-toggle').click();
    await expect(details).toHaveAttribute('open', '');
    const description = page.getByTestId('tx-form-description');
    await description.fill(text);
    await expect(description).toHaveValue(text);
}

/** Change one grid row's description through its form; ends with the grid showing the new text. */
async function editDescriptionInGrid(page: Page, from: string, to: string): Promise<void> {
    const row = bulkRows(page).filter({hasText: from});
    await expect(row).toHaveCount(1);
    await row.dblclick();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: UI_TIMEOUT});
    await fillDescription(page, to);
    const save = page.getByTestId('tx-form-save');
    await expect(save).toBeEnabled({timeout: UI_TIMEOUT});
    await save.click();
    await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: UI_TIMEOUT});
    await expect(bulkRows(page).filter({hasText: to})).toHaveCount(1, {timeout: UI_TIMEOUT});
}

type CommitBody = {committed: boolean; issues?: unknown[]; results?: Array<{operation: string; status?: string; ids?: number[]}>};

/** Save All; ends with the batch committed and the workspace closed. */
async function saveAll(page: Page): Promise<CommitBody> {
    const commit = page.getByTestId('tx-bulk-commit');
    await expect(commit).toBeEnabled({timeout: UI_TIMEOUT});
    const [response] = await Promise.all([page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === COMMIT_PATH, {timeout: 20_000}), commit.click()]);
    const body = await jsonFrom<CommitBody>(response, 'Save All');
    expect(body.committed, `Save All rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    await expect(bulkModal(page)).toBeHidden({timeout: UI_TIMEOUT});
    return body;
}

const succeeded = (body: CommitBody, operation: string): number[] => (body.results ?? []).filter((r) => r.operation === operation && r.status === 'success').flatMap((r) => r.ids ?? []);

// ---------------------------------------------------------------------------
// Who can edit: owner
// ---------------------------------------------------------------------------

test.describe('Broker Transactions tab — who can edit gets the selection bar and the row actions', () => {
    test('ticking rows shows the bar with Edit, Clone and Delete in the commands row; it counts the rows and clears them', async ({world}) => {
        const {page} = world;
        await openOwner(world);
        const {brokerId, d1, d2, w3} = await ownRows(world);
        await openTransactionsTab(page, brokerId, [d1, d2, w3]);

        // Nothing ticked: no bar. The actions column is there (hideActions off for who can edit).
        await expect(bar(page)).toHaveCount(0);
        await expect(txTable(page).getByTestId('dt-actions-header')).toBeVisible();

        await tick(page, d1.id);
        // The bar sits in the commands row of the tab, next to Import and New transaction, and counts one.
        await expect(bar(page)).toBeVisible({timeout: UI_TIMEOUT});
        await expect(bar(page)).toHaveAttribute('data-selected-count', '1');
        // Exactly the three actions, in this order: no Link-as-pair on this page.
        const ids = bar(page).locator('[data-testid^="toolbar-action-"]');
        await expect(ids).toHaveCount(3);
        await expect(ids.nth(0)).toHaveAttribute('data-testid', 'toolbar-action-edit');
        await expect(ids.nth(1)).toHaveAttribute('data-testid', 'toolbar-action-clone');
        await expect(ids.nth(2)).toHaveAttribute('data-testid', 'toolbar-action-delete');
        // The commands around it have not moved.
        await expect(commandsRow(page).getByTestId('broker-import-transactions')).toBeVisible();
        await expect(commandsRow(page).getByTestId('broker-new-transaction')).toBeVisible();
        await expect(commandsRow(page).getByTestId('broker-view-in-transactions')).toHaveAttribute('href', new RegExp(`broker_id=${brokerId}`));

        await tick(page, d2.id);
        await expect(bar(page)).toHaveAttribute('data-selected-count', '2');

        // Unticking the rows takes the bar away with the last one (its count button has no handle to click).
        await rowCheckbox(page, d1.id).click();
        await expect(bar(page)).toHaveAttribute('data-selected-count', '1');
        await rowCheckbox(page, d2.id).click();
        await expectNothingSelected(page, [d1, d2, w3]);
    });

    test('the bar opens the workspace on the selected rows: Edit in edit, Clone in clone, Delete in delete, with the real data of each', async ({world}) => {
        const {page} = world;
        await openOwner(world);
        const {brokerId, d1, d2, w3} = await ownRows(world);
        await openTransactionsTab(page, brokerId, [d1, d2, w3]);
        await tick(page, d1.id);
        await tick(page, w3.id);

        // Edit: the originals come from the transactions store the page fills on load.
        await bar(page).getByTestId('toolbar-action-edit').click();
        await expectWorkspaceRow(page, d1, 'original');
        await expectWorkspaceRow(page, w3, 'original');
        // The row left unticked is not in the workspace (presence of the two above makes this absence meaningful).
        await expect(bulkRows(page).filter({hasText: d2.description})).toHaveCount(0);
        await closeWorkspace(page);
        // Closing without saving keeps the selection.
        await expect(bar(page)).toHaveAttribute('data-selected-count', '2');

        await bar(page).getByTestId('toolbar-action-clone').click();
        await expectWorkspaceRow(page, d1, 'new');
        await expectWorkspaceRow(page, w3, 'new');
        await closeWorkspace(page);
        await expect(bar(page)).toHaveAttribute('data-selected-count', '2');

        // Delete is opened, never saved here.
        await bar(page).getByTestId('toolbar-action-delete').click();
        await expectWorkspaceRow(page, d1, 'delete');
        await expectWorkspaceRow(page, w3, 'delete');
        await closeWorkspace(page);
        await expect(bar(page)).toHaveAttribute('data-selected-count', '2');
        // Nothing was written.
        const rows = await readTransactions(page, {broker_id: brokerId});
        expect(rows.map((r) => r.id).sort()).toEqual([d1.id, d2.id, w3.id].sort());
    });

    test("a row's own menu offers Edit, Clone and Delete and each opens the workspace on that row", async ({world}) => {
        const {page} = world;
        await openOwner(world);
        const {brokerId, d1, d2, w3} = await ownRows(world);
        await openTransactionsTab(page, brokerId, [d1, d2, w3]);

        const menu = await openRowMenu(page, d2.id);
        for (const action of ['view', 'edit', 'clone', 'delete']) await expect(menu.getByTestId(`context-menu-action-${action}`), `${action} is offered`).toBeVisible();
        // A standalone row has no pair to split (and the tab wires no Split anyway).
        await expect(menu.getByTestId('context-menu-action-split')).toHaveCount(0);
        await page.keyboard.press('Escape');
        await expect(menu).toBeHidden();

        await clickRowAction(page, d2.id, 'edit');
        await expectWorkspaceRow(page, d2, 'original');
        // Only that row.
        await expect(bulkRows(page).filter({hasText: d1.description})).toHaveCount(0);
        await closeWorkspace(page, {withForm: true});

        await clickRowAction(page, d2.id, 'clone');
        await expectWorkspaceRow(page, d2, 'new');
        await closeWorkspace(page, {withForm: true});

        await clickRowAction(page, d2.id, 'delete');
        await expectWorkspaceRow(page, d2, 'delete');
        await closeWorkspace(page);
        // Opening and closing wrote nothing.
        await expect(tableRow(page, d2.id)).toBeVisible();
    });

    test('a saved edit empties the selection and the table shows the saved value', async ({world}) => {
        const {page} = world;
        await openOwner(world);
        const {brokerId, d1, d2, w3} = await ownRows(world);
        await openTransactionsTab(page, brokerId, [d1, d2, w3]);
        await tick(page, d1.id);
        await tick(page, d2.id);
        await expect(bar(page)).toHaveAttribute('data-selected-count', '2');

        await bar(page).getByTestId('toolbar-action-edit').click();
        await expectWorkspaceRow(page, d1, 'original');
        await expectWorkspaceRow(page, d2, 'original');
        const edited = `FB17 d1 edited ${world.tag}`;
        await editDescriptionInGrid(page, d1.description, edited);
        const body = await saveAll(page);
        expect(succeeded(body, 'update'), 'the edit reached the ledger, for the edited row only').toEqual([d1.id]);

        // The tab reloads with the saved value, and the selection — bar and checkboxes — is empty.
        await expect(txTable(page).getByTestId(`tx-desc-${d1.id}`)).toHaveText(edited, {timeout: UI_TIMEOUT});
        await expectNothingSelected(page, [d1, d2, w3]);
        const saved = (await readTransactions(page, {broker_id: brokerId})).find((r) => r.id === d1.id);
        expect(saved?.description, 'the server holds the new description').toBe(edited);
    });

    test('a saved delete from the bar removes the row from the table and empties the selection', async ({world}) => {
        const {page} = world;
        await openOwner(world);
        const {brokerId, d1, d2, w3} = await ownRows(world);
        await openTransactionsTab(page, brokerId, [d1, d2, w3]);
        await tick(page, w3.id);

        await bar(page).getByTestId('toolbar-action-delete').click();
        await expectWorkspaceRow(page, w3, 'delete');
        const body = await saveAll(page);
        expect(succeeded(body, 'delete'), 'the delete reached the ledger').toEqual([w3.id]);

        // The survivors stay (presence), the deleted row is gone, nothing is selected.
        await expect(tableRow(page, d1.id)).toBeVisible({timeout: UI_TIMEOUT});
        await expect(tableRow(page, w3.id)).toHaveCount(0, {timeout: UI_TIMEOUT});
        await expectNothingSelected(page, [d1, d2]);
    });

    test('a linked pair offers Edit, Clone and Delete on its row and no Split', async ({world}) => {
        const {page} = world;
        const owner = await openOwner(world);
        // Two brokers of the owner and a cash transfer between them, linked by the backend's own promote.
        const from = await createOwnedBroker(page, 'fb17-from', world.owned.brokerIds);
        const to = await createOwnedBroker(page, 'fb17-to', world.owned.brokerIds);
        const description = `FB17 transfer ${world.tag}`;
        const date = daysAgoIso(5);
        const [fundId, outId, inId] = await commitCreates(
            page,
            [
                {broker_id: from.id, type: 'DEPOSIT', date: daysAgoIso(20), cash: {code: 'EUR', amount: '500'}, description: `FB17 fund ${world.tag}`},
                {broker_id: from.id, type: 'WITHDRAWAL', date, cash: {code: 'EUR', amount: '-100'}, description},
                {broker_id: to.id, type: 'DEPOSIT', date, cash: {code: 'EUR', amount: '100'}, description},
            ],
            'own a transfer',
        );
        const linked = await jsonFrom<CommitBody>(await page.request.post(COMMIT_PATH, {data: {promotes: [{id_a: outId, id_b: inId}]}}), 'link the transfer');
        expect(linked.committed, `transfer not linked: ${JSON.stringify(linked.issues ?? [])}`).toBe(true);
        const halves = await readTransactions(page, {broker_id: from.id});
        const out = halves.find((r) => r.id === outId);
        expect(out?.related_transaction_id, `premise: the transfer's sending half points at its receiving half (${owner.username})`).toBe(inId);

        await openTransactionsTab(page, from.id, [
            {id: fundId, description: 'fund'},
            {id: outId, description},
        ]);
        const menu = await openRowMenu(page, outId);
        // Presence first: the pair row's menu is open and complete…
        for (const action of ['view', 'edit', 'clone', 'delete']) await expect(menu.getByTestId(`context-menu-action-${action}`), `${action} is offered on the pair`).toBeVisible();
        // …so the missing Split means "not drawn", not "menu not ready".
        await expect(menu.getByTestId('context-menu-action-split')).toHaveCount(0);
        await page.keyboard.press('Escape');
        await expect(menu).toBeHidden();

        // And Edit on the pair opens the workspace on the pair (the partner on the other broker comes along).
        await clickRowAction(page, outId, 'edit');
        await expect(bulkModal(page)).toBeVisible({timeout: UI_TIMEOUT});
        await expect(bulkRows(page).filter({hasText: description}), 'the pair is one row of the workspace').toHaveCount(1, {timeout: UI_TIMEOUT});
        await closeWorkspace(page, {withForm: true});
    });
});

// ---------------------------------------------------------------------------
// Who only views: viewer
// ---------------------------------------------------------------------------

test.describe('Broker Transactions tab — who only views gets no bar and no actions column', () => {
    test('a VIEWER can tick rows but sees no selection bar and no actions column; the shortcuts stay as they were', async ({world}) => {
        const {page, browser} = world;
        const owner = await openOwner(world);
        const {brokerId, d1, d2, w3} = await ownRows(world);

        // A second account that only views the owner's broker.
        const viewer = await registerDisposableUser(world.accounts, 'fb17v');
        world.cleanups.push(async () => deleteDisposableUser(world.accounts, viewer));
        const grant = await page.request.put(`${API}/brokers/${brokerId}/access`, {
            data: [
                {user_id: owner.id, role: 'OWNER', share_percentage: 1},
                {user_id: viewer.id, role: 'VIEWER', share_percentage: 0},
            ],
        });
        expect(grant.ok(), `grant VIEWER: HTTP ${grant.status()} ${await grant.text()}`).toBe(true);

        const viewerContext = await browser.newContext();
        world.cleanups.push(async () => viewerContext.close());
        const viewerPage = await viewerContext.newPage();
        await login(viewerPage, viewer);
        await skipDueFlowsExcept(viewerPage, []);

        await openTransactionsTab(viewerPage, brokerId, [d1, d2, w3]);
        // The page knows the role: a VIEWER has no broker edit button (the rows above are the presence barrier).
        await expect(viewerPage.getByTestId('broker-edit-button'), 'a VIEWER has no broker edit button').toHaveCount(0);

        // The rows can be ticked…
        await tick(viewerPage, d1.id);
        await tick(viewerPage, w3.id);
        // …and nothing offers to act on them: no bar, no actions column, no kebab on a row.
        await expect(bar(viewerPage)).toHaveCount(0);
        await expect(txTable(viewerPage).getByTestId('dt-actions-header')).toHaveCount(0);
        await expect(txTable(viewerPage).getByTestId(`row-actions-tx-${d1.id}`)).toHaveCount(0);
        // Import and New transaction need edit rights: still absent. The link to the Transactions page is for everyone.
        await expect(commandsRow(viewerPage).getByTestId('broker-import-transactions')).toHaveCount(0);
        await expect(commandsRow(viewerPage).getByTestId('broker-new-transaction')).toHaveCount(0);
        await expect(commandsRow(viewerPage).getByTestId('broker-view-in-transactions')).toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// A row the user cannot edit
// ---------------------------------------------------------------------------

test.describe('Broker Transactions tab — a row the user cannot edit is left out, with a word', () => {
    test('a pair whose other half sits on a broker the user only views is left out of Edit with a warning; alone, it opens nothing and says so', async ({world}) => {
        const {page, browser} = world;
        const owner = await openOwner(world);
        const {brokerId: brokerA, d1, d2} = await ownRows(world);

        // A second editor, X, who owns broker B and lets the owner only view it.
        const x = await registerDisposableUser(world.accounts, 'fb17x');
        const xContext = await browser.newContext();
        const brokerBName = `fb17-b-${world.tag}`;
        let brokerB = 0;
        let pair: number[] = [];
        // Undo steps: X's rows first, then its context, then its broker and account (pushed in the reverse order).
        world.cleanups.push(async () => {
            await deleteDisposableUser(world.accounts, x, brokerB > 0 ? [brokerB] : []);
        });
        world.cleanups.push(async () => xContext.close());
        world.cleanups.push(async () => {
            if (pair.length === 0) return;
            const removed = await jsonFrom<CommitBody>(await xContext.request.post(COMMIT_PATH, {data: {creates: [], updates: [], deletes: pair}}), 'delete the shared pair');
            expect(removed.committed, JSON.stringify(removed.issues ?? [])).toBe(true);
        });

        const xLogin = await xContext.request.post(`${API}/auth/login`, {data: {username: x.username, password: x.password}});
        expect(xLogin.ok(), `X signs in: HTTP ${xLogin.status()}`).toBe(true);
        // The owner lets X edit broker A (X must write on both halves of the pair)…
        const grantA = await page.request.put(`${API}/brokers/${brokerA}/access`, {
            data: [
                {user_id: owner.id, role: 'OWNER', share_percentage: 1},
                {user_id: x.id, role: 'EDITOR', share_percentage: 0},
            ],
        });
        expect(grantA.ok(), `grant EDITOR on A: HTTP ${grantA.status()} ${await grantA.text()}`).toBe(true);
        // …X creates broker B and lets the owner only view it.
        const createdB = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null}>}>(await xContext.request.post(`${API}/brokers`, {data: [{name: brokerBName, opened_at: '2025-01-01'}]}), 'X creates broker B');
        const idB = createdB.results.find((r) => r.name === brokerBName && r.success)?.broker_id;
        if (typeof idB !== 'number') throw new Error(`broker B was not created: ${JSON.stringify(createdB)}`);
        brokerB = idB;
        const grantB = await xContext.request.put(`${API}/brokers/${brokerB}/access`, {
            data: [
                {user_id: x.id, role: 'OWNER', share_percentage: 1},
                {user_id: owner.id, role: 'VIEWER', share_percentage: 0},
            ],
        });
        expect(grantB.ok(), `grant VIEWER on B: HTTP ${grantB.status()} ${await grantB.text()}`).toBe(true);

        // X moves cash from A (funded by d1 and d2) to B and links the two halves.
        const description = `FB17 shared transfer ${world.tag}`;
        const date = daysAgoIso(5);
        const created = await jsonFrom<CommitBody>(
            await xContext.request.post(COMMIT_PATH, {
                data: {
                    creates: [
                        {broker_id: brokerA, type: 'WITHDRAWAL', date, cash: {code: 'EUR', amount: '-100'}, description},
                        {broker_id: brokerB, type: 'DEPOSIT', date, cash: {code: 'EUR', amount: '100'}, description},
                    ],
                },
            }),
            'X creates the two halves',
        );
        expect(created.committed, JSON.stringify(created.issues ?? [])).toBe(true);
        const [legA, legB] = (created.results ?? []).filter((r) => r.operation === 'create').flatMap((r) => r.ids ?? []);
        pair = [legA, legB];
        const linked = await jsonFrom<CommitBody>(await xContext.request.post(COMMIT_PATH, {data: {promotes: [{id_a: legA, id_b: legB}]}}), 'X links the pair');
        expect(linked.committed, JSON.stringify(linked.issues ?? [])).toBe(true);
        const leg = (await readTransactions(page, {broker_id: brokerA})).find((r) => r.id === legA);
        expect(leg?.related_transaction_id, 'premise: the owner sees the A half linked to the B half').toBe(legB);

        await openTransactionsTab(page, brokerA, [d1, d2, {id: legA, description}]);

        // Both ticked → Edit: the standalone row opens, the pair is left out, and a warning says so.
        await tick(page, d1.id);
        await tick(page, legA);
        await expect(bar(page)).toHaveAttribute('data-selected-count', '2');
        await bar(page).getByTestId('toolbar-action-edit').click();
        await expect(page.getByTestId('toast-warning'), 'some rows were left out: a warning').toBeVisible({timeout: UI_TIMEOUT});
        await expect(bulkModal(page)).toBeVisible({timeout: UI_TIMEOUT});
        await expect(bulkRows(page).filter({hasText: d1.description})).toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(bulkRows(page).filter({hasText: description}), 'the pair the owner cannot edit is not in the workspace').toHaveCount(0);
        // One editable row is left, so the workspace opens on a single transaction to edit: its form comes on top.
        await closeWorkspace(page, {withForm: true});

        // Only the pair ticked → Edit: nothing opens, and an error says why.
        await rowCheckbox(page, d1.id).click();
        await expect(rowCheckbox(page, d1.id)).toHaveAttribute('data-state', 'unchecked');
        await expect(bar(page)).toHaveAttribute('data-selected-count', '1');
        await bar(page).getByTestId('toolbar-action-edit').click();
        await expect(page.getByTestId('toast-error'), 'nothing editable in the selection: an error').toBeVisible({timeout: UI_TIMEOUT});
        await expect(bulkModal(page)).toBeHidden();

        // Delete follows the same rule.
        await bar(page).getByTestId('toolbar-action-delete').click();
        await expect(bulkModal(page)).toBeHidden();
    });
});
