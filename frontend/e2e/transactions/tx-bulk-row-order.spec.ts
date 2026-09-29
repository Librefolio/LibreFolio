/**
 * tx-bulk-row-order.spec.ts — C4: the bulk editor's creation order, and the close
 * guard that has to ignore it.
 *
 * E-order: new rows added on one date keep the order in which the user added them.
 * The bulk editor orders its visible rows by earliest date, latest date and saved
 * id. A new row has no saved id, so between two new rows on the same date the
 * last word went to `tempId` — a random UUID — and a row added second could land
 * above the first. Five rows turn a lucky pass into a 1-in-120 event.
 *
 * E-reset (controls, green before and after the cure): the creation stamp is born
 * again whenever Reset regenerates a saved row, so the close guard's snapshot
 * (`serializeOps`) must ignore it exactly as it ignores `tempId` — or closing the
 * editor after a reset would ask to discard changes that do not exist. One test
 * edits a saved row, resets it and closes; the other opens and closes untouched.
 * The row is an owned, NON-paired DEPOSIT on an owned broker: a pair would get a
 * fresh link_uuid on reset, which is a separate matter.
 *
 * Every row is identified by a description only its test knows: never by
 * position, never by translated text. Nothing is saved — E-order discards the
 * editor through its own guard and checks the ledger for its marker; E-reset
 * deletes exactly the broker and DEPOSIT it created.
 *
 * Mock data contract: e2e_test_user has OWNER/EDITOR on Interactive Brokers.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

test.setTimeout(90_000);

const API = '/api/v1';
const BROKER_NAME = 'Interactive Brokers';
const ROW_COUNT = 5;

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type Owned = {brokerIds: number[]; transactionIds: number[]};
type OwnedDeposit = {brokerId: number; transactionId: number; description: string};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await expect(page.getByTestId('tx-table')).toBeVisible({timeout: 10_000});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** The id the seeded broker has in this database — read, never assumed. */
async function brokerIdByName(page: Page, name: string): Promise<number> {
    const response = await page.request.get(`${API}/brokers`);
    expect(response.ok(), `GET ${API}/brokers: HTTP ${response.status()}`).toBeTruthy();
    const body = (await response.json()) as {items: Array<{id: number; name: string}>};
    const broker = body.items.find((item) => item.name === name);
    if (!broker) throw new Error(`Seeded broker "${name}" is not accessible to ${TEST_USER.username}: see populate_mock_data.py`);
    return broker.id;
}

/**
 * A SearchSelect's option list is torn down when a choice lands, after the
 * cascade that choice triggers has re-rendered: a real barrier, and the proof
 * that the next select's options are not this one's.
 */
async function optionListClosed(page: Page) {
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 5_000});
}

async function selectType(page: Page, typeCode: string) {
    await page.getByTestId('tx-form-type').click();
    await page.getByTestId(`search-select-option-${typeCode}`).click();
    await optionListClosed(page);
}

async function pickBroker(page: Page, brokerId: number) {
    const trigger = page.getByTestId('tx-form-broker-wrap').getByRole('combobox');
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option).toBeVisible({timeout: 5_000});
    await option.click();
    await optionListClosed(page);
}

async function fillCash(page: Page, amount: string) {
    const input = page.getByTestId('tx-form-cash-amount');
    await expect(input).toBeVisible({timeout: 5_000});
    await input.fill(amount);
    await input.blur();
    await expect(input).not.toHaveValue('');
}

/**
 * The description lives in the collapsible optional `<details>`: read its real
 * `open` state rather than clicking blind, which would close an open section.
 */
async function fillDescription(page: Page, text: string) {
    const details = page.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(details).toBeVisible({timeout: 3_000});
    if (!(await details.evaluate((el) => (el as HTMLDetailsElement).open))) await page.getByTestId('tx-form-optional-toggle').click();
    await expect(details).toHaveAttribute('open', '');
    const description = page.getByTestId('tx-form-description');
    await description.fill(text);
    await expect(description).toHaveValue(text);
}

async function applyFormModal(page: Page) {
    const saveBtn = page.getByTestId('tx-form-save');
    await expect(saveBtn).toBeEnabled({timeout: 5_000});
    await saveBtn.click();
    await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: 10_000});
}

/** An owned broker (unique name) and one owned, non-paired DEPOSIT on it; every id is recorded for cleanup as soon as it exists. */
async function createOwnedDeposit(page: Page, owned: Owned, label: string, suffix: string): Promise<OwnedDeposit> {
    const name = `E-reset ${label} ${suffix}`;
    const created = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01'}]}), 'create owned broker');
    const broker = created.results.find((item) => item.name === name);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(created)}`);
    owned.brokerIds.push(broker.broker_id);

    const description = `E-reset ${label} saved ${suffix}`;
    const committed = await jsonFrom<{committed: boolean; issues?: unknown; results: Array<{operation: string; ids: number[]}>}>(
        await page.request.post(`${API}/transactions/commit`, {data: {creates: [{broker_id: broker.broker_id, type: 'DEPOSIT', date: '2024-01-02', cash: {code: 'EUR', amount: '100'}, description}]}}),
        'commit owned DEPOSIT',
    );
    expect(committed.committed, `owned DEPOSIT rolled back: ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
    const ids = committed.results.filter((result) => result.operation === 'create').flatMap((result) => result.ids);
    owned.transactionIds.push(...ids);
    expect(ids, 'the commit created exactly the one owned DEPOSIT').toHaveLength(1);
    return {brokerId: broker.broker_id, transactionId: ids[0], description};
}

/** Delete exactly the ids this test created, and say what could not be deleted. */
async function cleanupOwned(page: Page, owned: Owned): Promise<string[]> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Leave the page first: an editor still open on the row goes with it, unsaved.
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
    return failures;
}

/** Run `body` on an owned DEPOSIT, then delete it and its broker whatever the outcome. */
async function withOwnedDeposit(page: Page, label: string, body: (deposit: OwnedDeposit) => Promise<void>): Promise<void> {
    const owned: Owned = {brokerIds: [], transactionIds: []};
    let passed = false;
    try {
        await body(await createOwnedDeposit(page, owned, label, uniqueSuffix()));
        passed = true;
    } finally {
        const failures = await cleanupOwned(page, owned);
        // A red keeps its own error; on a green, a cleanup that failed is a red of its own.
        if (passed) expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
        else if (failures.length > 0) console.warn(`[E-reset] cleanup after a failure left behind: ${failures.join('; ')}`);
    }
}

/**
 * Open the owned row in the bulk editor the way a user does: select it in the
 * table, then the toolbar's Edit. One selected row makes the editor open that
 * row's FormModal by itself (autoForm 'edit'), so this ends with both on screen.
 */
async function openInBulkEditor(page: Page, deposit: OwnedDeposit) {
    await navigateTo(page, `/transactions?broker_id=${deposit.brokerId}`);
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: 10_000});
    await waitForSettled(transactionsPage, 20_000);
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${deposit.transactionId}`);
    await expect(checkbox).toBeVisible({timeout: 10_000});
    await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    const edit = page.getByTestId('toolbar-action-edit');
    await expect(edit).toBeEnabled({timeout: 5_000});
    await edit.click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/**
 * Close the editor and prove its discard guard stayed silent.
 *
 * `requestClose()` is either/or: it opens the guard and returns, or it closes the
 * editor — only a click on the guard's confirm, which never happens here, closes
 * it afterwards. So the editor gone after one click on its close button is the
 * proof the guard did not fire, and no confirm in the DOM at that point is the
 * proof none is waiting on screen. The editor is settled first, so the verdict
 * is the rows against the opening snapshot and nothing else.
 */
async function closeEditorWithoutGuard(page: Page) {
    await waitForSettled(page.getByTestId('tx-bulk-modal-root'));
    await page.getByTestId('tx-bulk-close').click();
    await expect(page.getByTestId('tx-bulk-modal'), 'the editor closes on the first click: its discard guard did not fire').toBeHidden({timeout: 5_000});
    await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Bulk editor row order', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('E-order — five new rows on one date keep the order they were added in', async ({page}) => {
        const suffix = uniqueSuffix();
        const created = Array.from({length: ROW_COUNT}, (_, i) => ({label: `r${i + 1}`, description: `E-order r${i + 1} ${suffix}`}));
        const brokerId = await brokerIdByName(page, BROKER_NAME);
        const bulk = page.getByTestId('tx-bulk-modal');
        const body = page.getByTestId('tx-bulk-body');
        const rows = body.locator('tbody tr[data-row-id]');

        for (const [index, row] of created.entries()) {
            // The first row opens the editor from the page, the others come from its own Add row.
            await page.getByTestId(index === 0 ? 'tx-add-button' : 'tx-bulk-add-row').click();
            await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
            await selectType(page, 'DEPOSIT');
            await pickBroker(page, brokerId);
            await fillCash(page, String(101 + index));
            await fillDescription(page, row.description);
            await applyFormModal(page);
            await expect(bulk).toBeVisible({timeout: 5_000});
            // Each row is in the grid before the next one is born: "added before" is unambiguous.
            await expect(rows.filter({hasText: row.description})).toHaveCount(1, {timeout: 5_000});
        }

        // The editor opened empty, so every row in it is one this test added.
        await expect(rows).toHaveCount(ROW_COUNT);
        const labelById = new Map<string, string>();
        for (const row of created) {
            const id = await rows.filter({hasText: row.description}).getAttribute('data-row-id');
            if (!id) throw new Error(`${row.label} has no workspace row id`);
            labelById.set(id, row.label);
        }

        // Precondition: the subject is the tie-break, so there must be a tie — one
        // date, no pair, and the default (ascending, unsorted header) order.
        const dateCells = await body.getByTestId('tx-bulk-date').evaluateAll((cells) => cells.map((cell) => ({date: cell.getAttribute('data-date'), partner: cell.getAttribute('data-partner-date')})));
        expect(new Set(dateCells.map((cell) => cell.date)).size, `all ${ROW_COUNT} rows share one date: ${JSON.stringify(dateCells)}`).toBe(1);
        expect(
            dateCells.map((cell) => cell.partner),
            'no row is half of a pair',
        ).toEqual(Array(ROW_COUNT).fill(''));
        await expect(body.getByTestId('dt-header-date')).toHaveAttribute('data-sort', 'none');

        // The visible order, top to bottom, read by content. Every row is present
        // (barriers above) and the order is derived synchronously from them.
        const observedIds = await rows.evaluateAll((trs) => trs.map((tr) => tr.getAttribute('data-row-id') ?? ''));
        const observed = observedIds.map((id) => labelById.get(id) ?? `unknown:${id}`);

        // Discard before judging, so the editor goes through its own guard whatever the verdict.
        await page.getByTestId('tx-bulk-cancel').click();
        const discard = page.getByTestId('confirm-modal-confirm');
        await expect(discard).toBeVisible({timeout: 5_000});
        await discard.click();
        await expect(bulk).toBeHidden({timeout: 5_000});

        // Nothing reached the ledger: validate is a dry run and the editor was never saved.
        const ledger = await page.request.get(`${API}/transactions`, {params: {broker_id: brokerId, types: 'DEPOSIT'}});
        expect(ledger.ok(), `GET ${API}/transactions: HTTP ${ledger.status()}`).toBeTruthy();
        const leaked = ((await ledger.json()) as Array<{id: number; description?: string | null}>).filter((tx) => (tx.description ?? '').includes(suffix));
        expect(leaked, 'a discarded editor must not have saved any row').toEqual([]);

        expect(observed, `same-date new rows must read top to bottom in the order they were added (row ids top to bottom: ${observedIds.join(', ')})`).toEqual(created.map((row) => row.label));
    });
});

test.describe('Bulk editor close guard', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('E-reset — edit a saved row, Reset all, close: nothing is left to discard, so the editor closes without asking', async ({page}) => {
        await withOwnedDeposit(page, 'edit', async (deposit) => {
            await openInBulkEditor(page, deposit);
            const rows = page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
            const changed = deposit.description.replace(' saved ', ' changed ');

            // Change the description through the form the editor opened, and push it back to the grid.
            await fillDescription(page, changed);
            await applyFormModal(page);
            await expect(rows.filter({hasText: changed})).toHaveCount(1, {timeout: 5_000});
            // Reset all exists only while a saved row differs from the ledger: the edit registered.
            const resetAll = page.getByTestId('tx-bulk-reset-all');
            await expect(resetAll).toBeVisible({timeout: 5_000});

            // Reset regenerates the row from the saved transaction — a new row object, the old content.
            await resetAll.click();
            await expect(rows.filter({hasText: deposit.description})).toHaveCount(1, {timeout: 5_000});
            await expect(rows.filter({hasText: changed})).toHaveCount(0);
            await expect(resetAll).toBeHidden();

            await closeEditorWithoutGuard(page);

            // Closing wrote nothing: the ledger still holds the description the test committed.
            const saved = await jsonFrom<Array<{id: number; description?: string | null}>>(await page.request.get(`${API}/transactions`, {params: {ids: deposit.transactionId}}), 'read owned DEPOSIT');
            expect(saved.map((tx) => tx.description)).toEqual([deposit.description]);
        });
    });

    test('E-reset (no edit) — open a saved row, close: the editor closes without asking', async ({page}) => {
        await withOwnedDeposit(page, 'noedit', async (deposit) => {
            await openInBulkEditor(page, deposit);
            const rows = page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');

            // Leave the form the editor opened untouched: it closes without a guard of its own.
            await page.getByTestId('tx-form-cancel').click();
            await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: 5_000});
            await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);
            // The grid shows the saved row as the ledger has it, and nothing counts as edited.
            await expect(rows.filter({hasText: deposit.description})).toHaveCount(1, {timeout: 5_000});
            await expect(page.getByTestId('tx-bulk-reset-all')).toBeHidden();

            await closeEditorWithoutGuard(page);
        });
    });
});
