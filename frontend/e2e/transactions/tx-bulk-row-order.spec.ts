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
 * The row is an owned, NON-paired DEPOSIT on an owned broker; a saved pair is
 * E-reset-pair's subject.
 *
 * E-reset-pair (step 23, 6a): the same promise on a SAVED pair, an owned
 * FX_CONVERSION. Reset regenerates its rows, and re-pairing them gives both
 * halves a fresh link_uuid and points the hidden half at the new visible row:
 * none of that is a change. Reset all after an edit through the pair's form;
 * the row's own Reset after marking the row for deletion, a change the visible
 * row holds alone; and an untouched control, which tells the pair itself apart
 * from the reset.
 *
 * E-reset-pair-*-edited (6c): an edit through the pair's form reaches the hidden
 * half too, so resetting the row — from its ⋮ menu or through the selection —
 * must rebuild both halves: afterwards the editor validates no change, offers
 * nothing to reset and closes without asking.
 *
 * Every row is identified by a description only its test knows: never by
 * position, never by translated text. Nothing is saved — E-order discards the
 * editor through its own guard and checks the ledger for its marker; E-reset and
 * E-reset-pair delete exactly the broker and transactions they created.
 *
 * Mock data contract: e2e_test_user has OWNER/EDITOR on Interactive Brokers.
 */
import {randomUUID} from 'crypto';
import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';
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
/** A saved FX_CONVERSION: `mainId` the paying EUR half, the row the editor shows; `partnerId` the USD half it hides. */
type OwnedFxPair = {brokerId: number; mainId: number; partnerId: number; description: string};
type SavedTx = {id: number; description?: string | null; related_transaction_id?: number | null; cash?: {code: string; amount: string} | null};
/** The body of a `/transactions/validate` request: empty lists are left out. */
type BatchPayload = {creates?: unknown[]; updates?: unknown[]; deletes?: unknown[]};

/** What a validation would change in the ledger, empty lists spelled out. */
const pendingChanges = (sent: BatchPayload) => ({creates: sent.creates ?? [], updates: sent.updates ?? [], deletes: sent.deletes ?? []});
const NO_CHANGES = {creates: [], updates: [], deletes: []};

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

/** An owned broker under a unique name; its id is recorded for cleanup as soon as it exists. */
async function createOwnedBroker(page: Page, owned: Owned, name: string): Promise<number> {
    const created = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01'}]}), 'create owned broker');
    const broker = created.results.find((item) => item.name === name);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(created)}`);
    owned.brokerIds.push(broker.broker_id);
    return broker.broker_id;
}

/** Commit `creates` as one batch; the ids are recorded for cleanup before anything is asserted on them. */
async function commitOwnedCreates(page: Page, owned: Owned, creates: Array<Record<string, unknown>>, purpose: string): Promise<number[]> {
    const committed = await jsonFrom<{committed: boolean; issues?: unknown; results: Array<{operation: string; ids: number[]}>}>(await page.request.post(`${API}/transactions/commit`, {data: {creates}}), purpose);
    expect(committed.committed, `${purpose} rolled back: ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
    const ids = committed.results.filter((result) => result.operation === 'create').flatMap((result) => result.ids);
    owned.transactionIds.push(...ids);
    return ids;
}

/** The saved rows with these ids, in this order. */
async function readTransactions(page: Page, ids: number[], purpose: string): Promise<SavedTx[]> {
    return jsonFrom<SavedTx[]>(await page.request.get(`${API}/transactions?${ids.map((id) => `ids=${id}`).join('&')}`), purpose);
}

/** An owned broker (unique name) and one owned, non-paired DEPOSIT on it; every id is recorded for cleanup as soon as it exists. */
async function createOwnedDeposit(page: Page, owned: Owned, label: string, suffix: string): Promise<OwnedDeposit> {
    const brokerId = await createOwnedBroker(page, owned, `E-reset ${label} ${suffix}`);
    const description = `E-reset ${label} saved ${suffix}`;
    const ids = await commitOwnedCreates(page, owned, [{broker_id: brokerId, type: 'DEPOSIT', date: '2024-01-02', cash: {code: 'EUR', amount: '100'}, description}], 'commit owned DEPOSIT');
    expect(ids, 'the commit created exactly the one owned DEPOSIT').toHaveLength(1);
    return {brokerId, transactionId: ids[0], description};
}

/**
 * An owned broker holding one SAVED FX_CONVERSION, EUR → USD, under a description
 * only this test knows. The broker is funded the day before, so the paying half
 * never takes it below zero (overdraft stays off); the pair then goes out the
 * way the app sends one — both halves in one batch, one link_uuid, the same
 * description — and is read back: two halves pointing at each other.
 */
async function createOwnedFxPair(page: Page, owned: Owned, label: string, suffix: string): Promise<OwnedFxPair> {
    const brokerId = await createOwnedBroker(page, owned, `E-reset ${label} ${suffix}`);
    const funding = await commitOwnedCreates(page, owned, [{broker_id: brokerId, type: 'DEPOSIT', date: '2024-01-02', cash: {code: 'EUR', amount: '1000'}, description: `E-reset ${label} funding ${suffix}`}], 'fund owned broker');
    expect(funding, 'the commit created exactly the one funding DEPOSIT').toHaveLength(1);

    const description = `E-reset ${label} saved ${suffix}`;
    const linkUuid = randomUUID();
    const half = (code: string, amount: string) => ({broker_id: brokerId, type: 'FX_CONVERSION', date: '2024-01-03', quantity: '0', cash: {code, amount}, link_uuid: linkUuid, description});
    const ids = await commitOwnedCreates(page, owned, [half('EUR', '-400'), half('USD', '440')], 'commit owned FX_CONVERSION pair');
    expect(ids, 'the commit created both halves of the pair').toHaveLength(2);

    const halves = await readTransactions(page, ids, 'read owned FX_CONVERSION pair');
    const main = halves.find((tx) => tx.cash?.code === 'EUR');
    const partner = halves.find((tx) => tx.cash?.code === 'USD');
    if (!main || !partner) throw new Error(`The owned pair is missing a half: ${JSON.stringify(halves)}`);
    expect([main.related_transaction_id, partner.related_transaction_id], 'premise: the two halves are linked to each other').toEqual([partner.id, main.id]);
    return {brokerId, mainId: main.id, partnerId: partner.id, description};
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
            const result = await jsonFrom<{committed: boolean}>(await page.request.post(`${API}/transactions/commit`, {data: {creates: [], updates: [], deletes: owned.transactionIds}}), 'delete owned transactions');
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

/** Run `body` on what `create` makes, then delete exactly that, whatever the outcome. */
async function withOwned<T>(page: Page, create: (owned: Owned, suffix: string) => Promise<T>, body: (made: T) => Promise<void>): Promise<void> {
    const owned: Owned = {brokerIds: [], transactionIds: []};
    let passed = false;
    try {
        await body(await create(owned, uniqueSuffix()));
        passed = true;
    } finally {
        const failures = await cleanupOwned(page, owned);
        // A red keeps its own error; on a green, a cleanup that failed is a red of its own.
        if (passed) expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
        else if (failures.length > 0) console.warn(`[E-reset] cleanup after a failure left behind: ${failures.join('; ')}`);
    }
}

/** Run `body` on an owned DEPOSIT, then delete it and its broker whatever the outcome. */
async function withOwnedDeposit(page: Page, label: string, body: (deposit: OwnedDeposit) => Promise<void>): Promise<void> {
    await withOwned(page, (owned, suffix) => createOwnedDeposit(page, owned, label, suffix), body);
}

/** Run `body` on an owned FX_CONVERSION pair, then delete it, its funding and its broker whatever the outcome. */
async function withOwnedFxPair(page: Page, label: string, body: (pair: OwnedFxPair) => Promise<void>): Promise<void> {
    await withOwned(page, (owned, suffix) => createOwnedFxPair(page, owned, label, suffix), body);
}

/**
 * Open the owned row in the bulk editor the way a user does: select it in the
 * table, then the toolbar's Edit. One selected row makes the editor open that
 * row's FormModal by itself (autoForm 'edit'), so this ends with both on screen.
 */
async function openInBulkEditor(page: Page, saved: {brokerId: number; transactionId: number}) {
    await navigateTo(page, `/transactions?broker_id=${saved.brokerId}`);
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: 10_000});
    await waitForSettled(transactionsPage, 20_000);
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${saved.transactionId}`);
    await expect(checkbox).toBeVisible({timeout: 10_000});
    await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    const edit = page.getByTestId('toolbar-action-edit');
    await expect(edit).toBeEnabled({timeout: 5_000});
    await edit.click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/** The editor's grid row showing `text`, a description only its test knows. */
function bulkRow(page: Page, text: string): Locator {
    return page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]').filter({hasText: text});
}

/** The editor's grid row of the owned pair, as the ledger describes it. */
function pairRow(page: Page, pair: OwnedFxPair): Locator {
    return bulkRow(page, pair.description);
}

/**
 * Open the owned pair the way a user does: select its paying half in the table,
 * then Edit. The editor brings the other half along, shows the pair as one grid
 * row and opens the pair's form by itself, both halves in it.
 */
async function openPairInBulkEditor(page: Page, pair: OwnedFxPair) {
    await openInBulkEditor(page, {brokerId: pair.brokerId, transactionId: pair.mainId});
    await expect(page.getByTestId('tx-form-dual-split'), 'the form holds both halves: the editor opened the pair').toBeVisible({timeout: 5_000});
    await expect(pairRow(page, pair), 'the pair is one row of the grid').toHaveCount(1, {timeout: 5_000});
}

/**
 * Change the pair's description through the form the editor opened — both halves
 * take it — and push it back to the grid; returns the new description. Reset all
 * appearing is the proof the edit registered.
 */
async function editPairDescription(page: Page, pair: OwnedFxPair): Promise<string> {
    const changed = pair.description.replace(' saved ', ' changed ');
    await fillDescription(page, changed);
    await applyFormModal(page);
    await expect(bulkRow(page, changed)).toHaveCount(1, {timeout: 5_000});
    await expect(page.getByTestId('tx-bulk-reset-all')).toBeVisible({timeout: 5_000});
    return changed;
}

/** Leave the form the editor opened untouched: it closes without a guard of its own. */
async function closeFormUntouched(page: Page) {
    await page.getByTestId('tx-form-cancel').click();
    await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: 5_000});
    await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);
}

/** One of a grid row's own actions, from the ⋮ menu the row carries; ends with the menu gone. */
async function runRowAction(page: Page, row: Locator, action: string) {
    await row.locator('[data-testid^="row-actions-"]').click();
    const item = page.getByTestId(`context-menu-action-${action}`);
    await expect(item).toBeVisible({timeout: 5_000});
    await item.click();
    await expect(page.getByTestId('context-menu')).toHaveCount(0);
}

/** Select a grid row through its own checkbox, then reset the selection from the editor's toolbar. */
async function resetThroughSelection(page: Page, row: Locator) {
    const checkbox = row.locator('[data-testid^="dt-row-checkbox-"]');
    await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    await page.getByTestId('tx-bulk-reset-selected').click();
}

/**
 * The last validation the editor sends after `action`, read once it has settled.
 *
 * The editor validates again whenever its rows change (debounced), and that
 * request is the ledger it would commit. `data-validate-runs` is read before the
 * action and must grow after it — a delta, so a run from before cannot pass for
 * one after — and the editor is settled before and after, so the last request
 * recorded is the one behind the verdict on screen.
 */
async function lastValidationAfter(page: Page, action: () => Promise<void>): Promise<BatchPayload> {
    const root = page.getByTestId('tx-bulk-modal-root');
    await waitForSettled(root);
    const runsBefore = Number(await root.getAttribute('data-validate-runs'));
    const sent: BatchPayload[] = [];
    const record = (request: Request) => {
        if (request.method() === 'POST' && request.url().includes('/transactions/validate')) sent.push((request.postDataJSON() ?? {}) as BatchPayload);
    };
    page.on('request', record);
    try {
        await action();
        await expect.poll(async () => Number(await root.getAttribute('data-validate-runs')), {message: 'the editor validates again after the action', timeout: 10_000}).toBeGreaterThan(runsBefore);
        await waitForSettled(root);
    } finally {
        page.off('request', record);
    }
    const last = sent.at(-1);
    if (!last) throw new Error('the editor counted a validation after the action, yet no /transactions/validate request was sent');
    return last;
}

/** Closing wrote nothing: both halves are in the ledger as the test saved them, still linked. */
async function expectPairAsSaved(page: Page, pair: OwnedFxPair) {
    const halves = await readTransactions(page, [pair.mainId, pair.partnerId], 'read owned FX_CONVERSION pair');
    expect(halves.map((tx) => [tx.id, tx.description, tx.related_transaction_id])).toEqual([
        [pair.mainId, pair.description, pair.partnerId],
        [pair.partnerId, pair.description, pair.mainId],
    ]);
}

/**
 * Close the editor and prove its discard guard stayed silent.
 *
 * `requestClose()` is either/or: it opens the guard and returns, or it closes the
 * editor — only a click on the guard's confirm, which never happens here, closes
 * it afterwards. So one click on its close button has two outcomes, and this waits
 * for whichever comes and names it: `closed` is the pass, `guard` is a «Discard
 * changes?» where nothing should be left to discard, and a click that brought
 * neither stays `open` until the deadline — three verdicts, never one generic
 * red. No confirm in the DOM after `closed` is the proof none is waiting on
 * screen. The editor is settled first, so the verdict is the rows against the
 * opening snapshot and nothing else.
 */
async function closeEditorWithoutGuard(page: Page) {
    await waitForSettled(page.getByTestId('tx-bulk-modal-root'));
    await page.getByTestId('tx-bulk-close').click();
    const editor = page.getByTestId('tx-bulk-modal');
    const guard = page.getByTestId('confirm-modal-confirm');
    const outcome = async () => ((await guard.isVisible()) ? 'guard' : (await editor.isVisible()) ? 'open' : 'closed');
    await expect.poll(outcome, {message: 'one click on close either closes the editor or opens its guard', timeout: 5_000}).not.toBe('open');
    expect(await outcome(), 'the editor closes on the first click: its discard guard did not fire').toBe('closed');
    await expect(guard).toHaveCount(0);
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

    test('E-reset-pair-all — edit a saved FX pair, Reset all, close: nothing is left to discard, so the editor closes without asking', async ({page}) => {
        await withOwnedFxPair(page, 'pair-all', async (pair) => {
            await openPairInBulkEditor(page, pair);
            const changed = await editPairDescription(page, pair);
            const resetAll = page.getByTestId('tx-bulk-reset-all');

            // Reset all regenerates both halves from the ledger and pairs them again — new row objects, the old content.
            await resetAll.click();
            await expect(pairRow(page, pair)).toHaveCount(1, {timeout: 5_000});
            await expect(bulkRow(page, changed)).toHaveCount(0);
            await expect(resetAll).toBeHidden();

            await closeEditorWithoutGuard(page);
            await expectPairAsSaved(page, pair);
        });
    });

    test("E-reset-pair-row — mark a saved FX pair's row for deletion, reset that row, close: nothing is left to discard, so the editor closes without asking", async ({page}) => {
        await withOwnedFxPair(page, 'pair-row', async (pair) => {
            await openPairInBulkEditor(page, pair);
            await closeFormUntouched(page);
            const resetAll = page.getByTestId('tx-bulk-reset-all');
            await expect(resetAll).toBeHidden();

            // A change the visible row holds alone: marked for deletion. Reset all appears, so it registered.
            await runRowAction(page, pairRow(page, pair), 'mark-delete');
            await expect(resetAll).toBeVisible({timeout: 5_000});

            // The row's own Reset regenerates it from the ledger and pairs it again — a new row object, the old content.
            await runRowAction(page, pairRow(page, pair), 'reset');
            await expect(resetAll).toBeHidden({timeout: 5_000});
            await expect(pairRow(page, pair)).toHaveCount(1);

            await closeEditorWithoutGuard(page);
            await expectPairAsSaved(page, pair);
        });
    });

    test('E-reset-pair-untouched (control) — open a saved FX pair, close: the editor closes without asking', async ({page}) => {
        await withOwnedFxPair(page, 'pair-untouched', async (pair) => {
            await openPairInBulkEditor(page, pair);
            await closeFormUntouched(page);
            await expect(page.getByTestId('tx-bulk-reset-all')).toBeHidden();

            await closeEditorWithoutGuard(page);
        });
    });

    // (a) and (b) are soft: a red names every symptom of a half-reset pair before the close is judged.
    test('E-reset-pair-row-edited — edit a saved FX pair through its form, then reset its row: both halves are as saved, so the editor validates no change, offers nothing to reset and closes without asking', async ({page}) => {
        await withOwnedFxPair(page, 'pair-row-edited', async (pair) => {
            await openPairInBulkEditor(page, pair);
            const changed = await editPairDescription(page, pair);

            // The row's own Reset, from its ⋮ menu; the validation that follows is the ledger the editor would commit.
            const sent = await lastValidationAfter(page, () => runRowAction(page, bulkRow(page, changed), 'reset'));
            // Premise: the visible half shows the ledger again — what follows is about the half the row hides.
            await expect(pairRow(page, pair)).toHaveCount(1);
            await expect(bulkRow(page, changed)).toHaveCount(0);

            // (a) No change to validate: the hidden half was rebuilt from the ledger too.
            expect.soft(pendingChanges(sent), `the validation after the row's Reset carries no change (visible half ${pair.mainId}, hidden half ${pair.partnerId})`).toEqual(NO_CHANGES);
            // (b) Nothing to reset: Reset all exists only while a saved row differs from the ledger, its hidden half included.
            await expect.soft(page.getByTestId('tx-bulk-reset-all'), 'after the row reset nothing is left to reset').toBeHidden();
            // (c) Nothing to discard.
            await closeEditorWithoutGuard(page);
            await expectPairAsSaved(page, pair);
        });
    });

    test('E-reset-pair-selected-edited — edit a saved FX pair through its form, then reset it through the selection: the editor validates no change and closes without asking', async ({page}) => {
        await withOwnedFxPair(page, 'pair-selected-edited', async (pair) => {
            await openPairInBulkEditor(page, pair);
            const changed = await editPairDescription(page, pair);

            // The pair's row selected through its checkbox, then the toolbar's Reset for the selection.
            const sent = await lastValidationAfter(page, () => resetThroughSelection(page, bulkRow(page, changed)));
            // Premise: the visible half shows the ledger again — what follows is about the half the row hides.
            await expect(pairRow(page, pair)).toHaveCount(1);
            await expect(bulkRow(page, changed)).toHaveCount(0);

            // (a) No change to validate: the hidden half was rebuilt from the ledger too.
            expect.soft(pendingChanges(sent), `the validation after the selection's Reset carries no change (visible half ${pair.mainId}, hidden half ${pair.partnerId})`).toEqual(NO_CHANGES);
            // (c) Nothing to discard.
            await closeEditorWithoutGuard(page);
            await expectPairAsSaved(page, pair);
        });
    });
});
