/**
 * Transaction BulkModal — promote EXECUTION and restore-and-edit (D2 coverage).
 *
 * The sibling `tx-bulk-suggest-ux.spec.ts` proves the promote *surfaces appear*
 * (banner + toolbar button) but stops there: it never clicks promote, never
 * commits, and never restores a delete-marked row. This spec drives those flows
 * to the end, which are the largest uncovered region of `TransactionBulkModal`:
 *
 *   - `handlePromoteSelected`  → direct (matching fields) vs merge (divergent)
 *   - `executePromote`         → all three branches: edit+edit, create+create, mixed
 *   - `onBulkPromoteMergeConfirm` (confirm a divergent-field merge)
 *   - `triggerPromoteFromSuggestion` (the banner-link entry point) → direct + merge
 *   - `handleEditRowClick` (delete branch) + `confirmRestoreAndEdit`
 *
 * ## Concurrency & cleanup
 *
 * `Transaction` is a GLOBAL table (no `user_id`): what one spec commits, every
 * later spec sees. Every promote here really writes. So:
 *
 *   - setup rows created via `page.request` are tracked in `setupIds` and deleted
 *     in afterEach (guarded — a row may already be gone via a linked partner);
 *   - rows created by the UI commit are caught by `trackTransactionWrites`, which
 *     listens on `page.on('response')` — that fires for the browser's fetch but
 *     NOT for `page.request`, which is exactly why setup rows need the manual list.
 *
 * Each Playwright test gets an isolated browser context, so a modal left open by
 * a no-commit test cannot bleed into the next; only the API rows must be undone.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {trackTransactionWrites, type TransactionWriteTracker} from '../fixtures/db-cleanup';
import {uniqueSuffix} from '../fixtures/unique';

test.setTimeout(30_000);

const API = '/api/v1';
const TEST_DATE = '2026-06-25';

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page, query = '') {
    await navigateTo(page, `/transactions${query}`);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    // Visible ≠ loaded: the table renders empty then fills. The page publishes
    // data-busy, so wait on that rather than on a duration.
    await waitForSettled(page.getByTestId('transactions-page'));
}

/**
 * Open the table narrowed to the given ids via the `id_min`/`id_max` URL filter,
 * and wait for every one to be on screen. Pagination is client-side and returns
 * everything, so "my rows are on page 1" is a guess four workers falsify.
 */
async function goToTransactionsByIds(page: Page, ids: number[]) {
    const min = Math.min(...ids);
    const max = Math.max(...ids);
    await goToTransactions(page, `?id_min=${min}&id_max=${max}`);
    for (const id of ids) {
        await expect(page.locator(`tr[data-row-id="tx-${id}"]`)).toBeVisible({timeout: 10_000});
    }
}

// ---------------------------------------------------------------------------
// Backend setup / teardown (via page.request — shares the login cookie jar)
// ---------------------------------------------------------------------------

interface CommitResult {
    committed: boolean;
    issues?: Array<{error: string}>;
    results: Array<{operation: string; ids: number[]}>;
}

/** Commit a batch of `creates` and return the created ids. Fails loud on rollback. */
async function commitCreates(page: Page, creates: unknown[]): Promise<number[]> {
    const resp = await page.request.post(`${API}/transactions/commit`, {
        data: {creates, updates: [], deletes: [], splits: [], promotes: []},
    });
    expect(resp.ok(), `setup commit HTTP ${resp.status()}`).toBeTruthy();
    const body = (await resp.json()) as CommitResult;
    // 200 does not mean "created": a business-rule violation rolls the whole batch
    // back and still answers 200.
    expect(body.committed, `setup commit rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    return body.results.flatMap((r) => r.ids ?? []);
}

/** A cash DEPOSIT create payload. */
function depositPayload(brokerId: number, amount: string, description: string) {
    return {broker_id: brokerId, type: 'DEPOSIT', date: TEST_DATE, quantity: '0', cash: {code: 'EUR', amount}, tags: [], description};
}

/** A cash WITHDRAWAL create payload (amount must be negative). */
function withdrawalPayload(brokerId: number, amount: string, description: string) {
    return {broker_id: brokerId, type: 'WITHDRAWAL', date: TEST_DATE, quantity: '0', cash: {code: 'EUR', amount}, tags: [], description};
}

/**
 * Create a saved DEPOSIT+WITHDRAWAL pair that exactly cancels across two brokers,
 * plus a funding deposit so the withdrawal broker never goes negative (the backend
 * refuses that atomically). Descriptions are caller-controlled so a test can make
 * the pair "matching" (→ direct promote) or "divergent" (→ merge modal).
 */
async function createSavedPair(page: Page, depositBrokerId: number, withdrawalBrokerId: number, descDeposit: string, descWithdrawal: string): Promise<{fundId: number; depositId: number; withdrawalId: number; all: number[]}> {
    const ids = await commitCreates(page, [depositPayload(withdrawalBrokerId, '1011.00', `fund ${descWithdrawal}`), depositPayload(depositBrokerId, '11.00', descDeposit), withdrawalPayload(withdrawalBrokerId, '-11.00', descWithdrawal)]);
    expect(ids, 'setup pair must create exactly three rows').toHaveLength(3);
    return {fundId: ids[0], depositId: ids[1], withdrawalId: ids[2], all: ids};
}

/** Delete the given ids that still exist. Guarded: a linked partner delete may
 *  have already removed one. */
async function deleteIdsIfPresent(page: Page, ids: number[]) {
    if (ids.length === 0) return;
    const res = await page.request.get(`${API}/transactions`);
    if (!res.ok()) return;
    const rows = (await res.json()) as Array<{id: number}>;
    const present = new Set(rows.map((r) => r.id));
    const deletes = ids.filter((id) => present.has(id));
    if (deletes.length === 0) return;
    await page.request.post(`${API}/transactions/commit`, {data: {creates: [], updates: [], deletes, splits: [], promotes: []}});
}

/** Two distinct editable broker ids. The fixture guarantees several. */
async function findTwoBrokerIds(page: Page): Promise<[number, number]> {
    const resp = await page.request.get(`${API}/brokers`);
    expect(resp.ok(), `GET ${API}/brokers returned ${resp.status()}`).toBe(true);
    const data = (await resp.json()) as {items: Array<{id: number; user_role: string | null}>};
    const editable = data.items.filter((b) => b.user_role === 'OWNER' || b.user_role === 'EDITOR');
    expect(editable.length, 'the fixture must provide at least 2 editable brokers').toBeGreaterThanOrEqual(2);
    return [editable[0].id, editable[1].id];
}

/** GET the read model and index it by id — the strong proof that a promote persisted. */
async function fetchTxById(page: Page): Promise<Map<number, {type: string; related_transaction_id: number | null}>> {
    const res = await page.request.get(`${API}/transactions`);
    expect(res.ok(), `GET ${API}/transactions returned ${res.status()}`).toBe(true);
    const rows = (await res.json()) as Array<{id: number; type: string; related_transaction_id: number | null}>;
    return new Map(rows.map((r) => [r.id, {type: r.type, related_transaction_id: r.related_transaction_id}]));
}

// ---------------------------------------------------------------------------
// FormModal / BulkModal driving. Every wait is a wait for a CONDITION, never a
// duration — the parallel suite punishes clock waits.
// ---------------------------------------------------------------------------

async function selectType(page: Page, typeCode: string) {
    await page.getByTestId('tx-form-type').click();
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await expect(option).not.toBeVisible({timeout: 3_000});
}

async function pickBrokerById(page: Page, brokerId: number) {
    const brokerWrap = page.getByTestId('tx-form-broker-wrap');
    await brokerWrap.locator('button, [role="combobox"]').first().click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await expect(option).not.toBeVisible({timeout: 3_000});
}

async function fillCash(page: Page, amount: string) {
    const cashWrap = page.getByTestId('tx-form-cash-wrap');
    await expect(cashWrap).toBeVisible({timeout: 3_000});
    const cashInput = cashWrap.locator('input[data-testid$="-amount"]').first();
    await expect(cashInput).toBeVisible({timeout: 3_000});
    await cashInput.fill(amount);
    await cashInput.press('Tab');
}

/**
 * Open the FormModal's "optional" disclosure, which holds tags + description.
 * It defaults to closed (`initialOptionalOpen=false`), so the description textarea
 * is present-but-hidden until the `<details>` is opened. Assert the end state
 * rather than clicking blind (the toggle would close an already-open section).
 */
async function ensureOptionalOpen(page: Page) {
    const details = page.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(details).toBeVisible({timeout: 3_000});
    const alreadyOpen = await details.evaluate((el) => (el as HTMLDetailsElement).open);
    if (!alreadyOpen) await page.getByTestId('tx-form-optional-toggle').click();
    await expect(details).toHaveAttribute('open', '');
}

/** Set the FormModal description, ending on the value the helper promises. */
async function fillDescription(page: Page, text: string) {
    await ensureOptionalOpen(page);
    const desc = page.getByTestId('tx-form-description');
    await expect(desc).toBeVisible({timeout: 3_000});
    await desc.fill(text);
    await expect(desc).toHaveValue(text);
}

async function applyFormModal(page: Page) {
    const saveBtn = page.getByTestId('tx-form-save');
    await expect(saveBtn).toBeEnabled({timeout: 5_000});
    await saveBtn.click();
    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 10_000});
}

/** Add one cash-only row (DEPOSIT/WITHDRAWAL) to the open BulkModal. */
async function addCashRow(page: Page, type: string, brokerId: number, amount: string, description?: string) {
    await page.getByTestId('tx-bulk-add-row').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
    await selectType(page, type);
    await pickBrokerById(page, brokerId);
    await fillCash(page, amount);
    if (description !== undefined) await fillDescription(page, description);
    await applyFormModal(page);
}

/** Open the very first cash-only row via the table's add button (auto-opens the form). */
async function startBulkWithCashRow(page: Page, type: string, brokerId: number, amount: string, description?: string) {
    await goToTransactions(page); // the add button lives on the transactions page
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
    await selectType(page, type);
    await pickBrokerById(page, brokerId);
    await fillCash(page, amount);
    if (description !== undefined) await fillDescription(page, description);
    await applyFormModal(page);
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
}

/** Select saved rows in the TABLE, then open the BulkModal via the edit toolbar. */
async function openBulkEditFor(page: Page, ids: number[]) {
    await goToTransactionsByIds(page, ids);
    for (const id of ids) {
        await ensureChecked(page.getByTestId(`dt-row-checkbox-tx-${id}`));
    }
    const editBtn = page.getByTestId('toolbar-action-edit');
    await expect(editBtn).toBeEnabled({timeout: 5_000});
    await editBtn.click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
}

const modalRowsOf = (page: Page) => page.locator('[data-testid="tx-bulk-modal"] tr[data-row-id]');

/**
 * Bring a checkbox to `checked`, whatever state it starts in.
 *
 * A blind `.click()` is a toggle, so it *deselects* anything that arrived already
 * selected — and rows do arrive selected here: a linked partner is auto-selected
 * with its twin. The button publishes `data-state`, so ask before acting and
 * assert the end state, rather than betting on the starting one.
 */
async function ensureChecked(checkbox: ReturnType<Page['locator']>) {
    await expect(checkbox).toBeVisible({timeout: 5_000});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked', {timeout: 5_000});
}

/** Check the checkbox of every row in an ALREADY-FILTERED locator. */
async function checkAll(rows: ReturnType<Page['locator']>, count: number) {
    await expect(rows).toHaveCount(count, {timeout: 5_000});
    for (let i = 0; i < count; i++) {
        await ensureChecked(rows.nth(i).locator('[data-testid^="dt-row-checkbox-"]'));
    }
}

/**
 * Commit the BulkModal, wait for the commit response (the commit IS the subject
 * here, so waiting on the network is correct), assert success + the modal closes,
 * and return the deduped resulting ids.
 */
async function commitAndCapture(page: Page): Promise<number[]> {
    const root = page.getByTestId('tx-bulk-modal-root');
    await waitForSettled(root); // validation must settle before commit is meaningful
    const commitBtn = page.getByTestId('tx-bulk-commit');
    await expect(commitBtn).toBeEnabled({timeout: 10_000});
    const respP = page.waitForResponse((r) => r.url().includes('/transactions/commit') && r.request().method() === 'POST', {timeout: 15_000});
    await commitBtn.click();
    const resp = await respP;
    const body = (await resp.json()) as CommitResult;
    expect(body.committed, `commit rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: 10_000});
    return [...new Set(body.results.flatMap((r) => r.ids ?? []))];
}

/** Assert two ids form a linked pair of the expected type, pointing at each other. */
async function expectLinkedPair(page: Page, ids: number[], expectedType = 'CASH_TRANSFER') {
    expect(ids, 'a promote must yield exactly two linked ids').toHaveLength(2);
    const byId = await fetchTxById(page);
    const a = byId.get(ids[0]);
    const b = byId.get(ids[1]);
    expect(a, `row ${ids[0]} must exist after commit`).toBeTruthy();
    expect(b, `row ${ids[1]} must exist after commit`).toBeTruthy();
    expect(a!.type).toBe(expectedType);
    expect(b!.type).toBe(expectedType);
    expect(a!.related_transaction_id).toBe(ids[1]);
    expect(b!.related_transaction_id).toBe(ids[0]);
}

// ===========================================================================
// Promote execution
// ===========================================================================

test.describe('BulkModal promote execution', () => {
    let tracker: TransactionWriteTracker;
    let setupIds: number[];

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        // Snapshot BEFORE any setup writes so UI-created ids are recognised as ours.
        tracker = await trackTransactionWrites(page);
        setupIds = [];
    });

    test.afterEach(async ({page}) => {
        await tracker.cleanup(); // rows the UI committed (create/promote)
        await deleteIdsIfPresent(page, setupIds); // rows page.request created (funding, saved side)
    });

    test('PE1: edit+edit with matching fields promotes directly and persists a linked pair', async ({page}) => {
        const [brokerA, brokerB] = await findTwoBrokerIds(page);
        const marker = `pe1-${uniqueSuffix()}`;
        // Same description on both sides + empty tags on both → no divergence → direct.
        const pair = await createSavedPair(page, brokerA, brokerB, marker, marker);
        setupIds.push(...pair.all);

        await openBulkEditFor(page, [pair.depositId, pair.withdrawalId]);

        // Two standalone rows in the modal; select both to arm the toolbar.
        const rows = modalRowsOf(page);
        await checkAll(rows, 2);

        // Matching fields → the toolbar promotes without opening the merge modal.
        await page.getByTestId('promote-toolbar-confirm').click();
        await expect(page.getByTestId('promote-merge-confirm')).toBeHidden({timeout: 2_000});

        // Two rows collapse into one paired row (structural, non-translated proof).
        await expect(rows).toHaveCount(1, {timeout: 5_000});

        const ids = await commitAndCapture(page);
        // edit+edit keeps ids: the promote must be the two we started with.
        expect(new Set(ids)).toEqual(new Set([pair.depositId, pair.withdrawalId]));
        await expectLinkedPair(page, [pair.depositId, pair.withdrawalId]);
    });

    test('PE2: edit+edit with divergent description opens the merge modal, then persists', async ({page}) => {
        const [brokerA, brokerB] = await findTwoBrokerIds(page);
        const s = uniqueSuffix();
        // Divergent descriptions → handlePromoteSelected must route through the merge modal.
        const pair = await createSavedPair(page, brokerA, brokerB, `pe2-dep-${s}`, `pe2-wd-${s}`);
        setupIds.push(...pair.all);

        await openBulkEditFor(page, [pair.depositId, pair.withdrawalId]);
        const rows = modalRowsOf(page);
        await checkAll(rows, 2);

        await page.getByTestId('promote-toolbar-confirm').click();

        // Divergence → the merge modal must appear; confirming it runs onBulkPromoteMergeConfirm.
        // `promote-merge-modal` is stamped on two nested nodes (ModalBase + inner div), so key
        // the open/closed state off the unambiguous confirm button instead.
        const mergeConfirm = page.getByTestId('promote-merge-confirm');
        await expect(mergeConfirm).toBeVisible({timeout: 5_000});
        await mergeConfirm.click();
        await expect(mergeConfirm).toBeHidden({timeout: 5_000});

        await expect(rows).toHaveCount(1, {timeout: 5_000});

        const ids = await commitAndCapture(page);
        expect(new Set(ids)).toEqual(new Set([pair.depositId, pair.withdrawalId]));
        await expectLinkedPair(page, [pair.depositId, pair.withdrawalId]);
    });

    test('PE3: cancelling the merge modal leaves the two rows unpromoted', async ({page}) => {
        const [brokerA, brokerB] = await findTwoBrokerIds(page);
        const s = uniqueSuffix();
        const pair = await createSavedPair(page, brokerA, brokerB, `pe3-dep-${s}`, `pe3-wd-${s}`);
        setupIds.push(...pair.all);

        await openBulkEditFor(page, [pair.depositId, pair.withdrawalId]);
        const rows = modalRowsOf(page);
        await checkAll(rows, 2);

        await page.getByTestId('promote-toolbar-confirm').click();
        const mergeConfirm = page.getByTestId('promote-merge-confirm');
        await expect(mergeConfirm).toBeVisible({timeout: 5_000});

        // Escape → ModalBase.onRequestClose → the inline onCancel (promoteMergeOpen=false).
        await page.keyboard.press('Escape');
        await expect(mergeConfirm).toBeHidden({timeout: 5_000});

        // No promote happened: both rows are still present and distinct.
        await expect(rows).toHaveCount(2, {timeout: 5_000});
        // And nothing was persisted — the saved pair is still two standalone rows.
        const byId = await fetchTxById(page);
        expect(byId.get(pair.depositId)?.related_transaction_id ?? null).toBeNull();
        expect(byId.get(pair.withdrawalId)?.related_transaction_id ?? null).toBeNull();
    });

    test('PE4: create+create promotes via the toolbar and persists a new linked pair', async ({page}) => {
        const [brokerA, brokerB] = await findTwoBrokerIds(page);
        // Fund the withdrawal broker so the new WITHDRAWAL row validates.
        const [fundId] = await commitCreates(page, [depositPayload(brokerB, '1000.00', `pe4-fund-${uniqueSuffix()}`)]);
        setupIds.push(fundId);

        // Two new rows, both empty description → matching → direct promote.
        await startBulkWithCashRow(page, 'DEPOSIT', brokerA, '11');
        await addCashRow(page, 'WITHDRAWAL', brokerB, '11');

        const rows = modalRowsOf(page);
        await checkAll(rows, 2);
        await page.getByTestId('promote-toolbar-confirm').click();
        await expect(page.getByTestId('promote-merge-confirm')).toBeHidden({timeout: 2_000});
        await expect(rows).toHaveCount(1, {timeout: 5_000});

        const ids = await commitAndCapture(page);
        await expectLinkedPair(page, ids);
    });

    test('PE5: mixed new+edit promotes via the toolbar and persists a linked pair', async ({page}) => {
        // One saved side, one typed side — the branch that used to answer correctly
        // only by accident (one amount signed, one normalised).
        const [brokerA, brokerB] = await findTwoBrokerIds(page);
        const marker = `pe5-${uniqueSuffix()}`;
        // Saved side: fund brokerB (distractor — its description must NOT contain `marker`,
        // or the hasText filter below would match three rows) + a WITHDRAWAL on brokerB
        // carrying the shared marker so it matches the typed row → direct promote.
        const ids = await commitCreates(page, [depositPayload(brokerB, '1011.00', `distractor-${uniqueSuffix()}`), withdrawalPayload(brokerB, '-11.00', marker)]);
        const fundId = ids[0];
        const withdrawalId = ids[1];
        setupIds.push(fundId, withdrawalId);

        await openBulkEditFor(page, [fundId, withdrawalId]);
        const rows = modalRowsOf(page);
        // Nothing pairs yet: both saved rows sit on the same broker.
        await expect(rows).toHaveCount(2, {timeout: 5_000});
        await expect(page.getByTestId('promote-suggest-banner')).toBeHidden({timeout: 2_000});

        // Typed DEPOSIT on brokerA with the SAME marker → matches the saved withdrawal.
        await addCashRow(page, 'DEPOSIT', brokerA, '11', marker);
        await expect(rows).toHaveCount(3, {timeout: 5_000});

        // Select exactly the two marker-bearing rows (withdrawal + new deposit); the
        // funding deposit carries a different description and is excluded.
        const markerRows = rows.filter({hasText: marker});
        await checkAll(markerRows, 2);

        await page.getByTestId('promote-toolbar-confirm').click();
        await expect(page.getByTestId('promote-merge-confirm')).toBeHidden({timeout: 2_000});
        await expect(rows).toHaveCount(2, {timeout: 5_000}); // 3 rows → 2 (pair collapsed, funding remains)

        const committed = await commitAndCapture(page);
        // The linked pair is the saved withdrawal + the freshly created deposit; the
        // funding row is committed too but stands alone.
        const byId = await fetchTxById(page);
        const wd = byId.get(withdrawalId);
        expect(wd, 'the saved withdrawal must survive as the promoted row').toBeTruthy();
        expect(wd!.type).toBe('CASH_TRANSFER');
        const partnerId = wd!.related_transaction_id;
        expect(partnerId, 'the withdrawal must now point at its promoted partner').not.toBeNull();
        expect(committed).toContain(partnerId!);
        await expectLinkedPair(page, [withdrawalId, partnerId!]);
    });

    test('PE6: banner link promotes a matching new+new pair directly', async ({page}) => {
        const [brokerA, brokerB] = await findTwoBrokerIds(page);
        const [fundId] = await commitCreates(page, [depositPayload(brokerB, '1000.00', `pe6-fund-${uniqueSuffix()}`)]);
        setupIds.push(fundId);

        await startBulkWithCashRow(page, 'DEPOSIT', brokerA, '11');
        await addCashRow(page, 'WITHDRAWAL', brokerB, '11');

        // The banner is fed by bannerSuggestions (new+new local loop).
        await expect(page.getByTestId('promote-suggest-banner')).toBeVisible({timeout: 10_000});
        const rows = modalRowsOf(page);
        await expect(rows).toHaveCount(2, {timeout: 5_000});

        // The banner link routes through triggerPromoteFromSuggestion; empty descriptions
        // on both → its direct branch (no merge modal).
        await page.getByTestId('promote-suggest-link-0').click();
        await expect(page.getByTestId('promote-merge-confirm')).toBeHidden({timeout: 2_000});
        await expect(rows).toHaveCount(1, {timeout: 5_000});

        const ids = await commitAndCapture(page);
        await expectLinkedPair(page, ids);
    });

    test('PE6b: banner link on a divergent new+new pair opens the merge modal', async ({page}) => {
        const [brokerA, brokerB] = await findTwoBrokerIds(page);
        const s = uniqueSuffix();
        const [fundId] = await commitCreates(page, [depositPayload(brokerB, '1000.00', `pe6b-fund-${s}`)]);
        setupIds.push(fundId);

        // Distinct descriptions → triggerPromoteFromSuggestion must take its divergent branch.
        await startBulkWithCashRow(page, 'DEPOSIT', brokerA, '11', `pe6b-dep-${s}`);
        await addCashRow(page, 'WITHDRAWAL', brokerB, '11', `pe6b-wd-${s}`);

        await expect(page.getByTestId('promote-suggest-banner')).toBeVisible({timeout: 10_000});
        const rows = modalRowsOf(page);
        await page.getByTestId('promote-suggest-link-0').click();

        const mergeConfirm = page.getByTestId('promote-merge-confirm');
        await expect(mergeConfirm).toBeVisible({timeout: 5_000});
        await mergeConfirm.click();
        await expect(mergeConfirm).toBeHidden({timeout: 5_000});
        await expect(rows).toHaveCount(1, {timeout: 5_000});

        const ids = await commitAndCapture(page);
        await expectLinkedPair(page, ids);
    });
});

// ===========================================================================
// Restore-and-edit on a delete-marked row
// ===========================================================================

test.describe('BulkModal restore-and-edit', () => {
    let setupIds: number[];

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        setupIds = [];
    });

    test.afterEach(async ({page}) => {
        await deleteIdsIfPresent(page, setupIds);
    });

    /** Open a bulk modal on two independent saved DEPOSITs (they never auto-pair). */
    async function openTwoSavedDeposits(page: Page, markerA: string, markerB: string): Promise<[number, number]> {
        const [brokerA] = await findTwoBrokerIds(page);
        const ids = await commitCreates(page, [depositPayload(brokerA, '50.00', markerA), depositPayload(brokerA, '60.00', markerB)]);
        setupIds.push(...ids);
        await openBulkEditFor(page, ids);
        return [ids[0], ids[1]];
    }

    test('RE1: editing a delete-marked row prompts to restore, then opens the form', async ({page}) => {
        const marker = `re1-${uniqueSuffix()}`;
        await openTwoSavedDeposits(page, marker, `re1b-${uniqueSuffix()}`);

        const row = modalRowsOf(page).filter({hasText: marker});
        await expect(row).toHaveCount(1, {timeout: 5_000});

        // Mark it for deletion via the kebab.
        await row.locator('[data-testid^="row-actions-"]').click();
        await page.getByTestId('context-menu-action-mark-delete').click();

        // Editing a delete-marked row must NOT open the form directly — it prompts first.
        await row.locator('[data-testid^="row-actions-"]').click();
        await page.getByTestId('context-menu-action-edit-single').click();
        const confirm = page.getByTestId('confirm-modal-confirm');
        await expect(confirm).toBeVisible({timeout: 5_000});

        // Confirm restore-and-edit → the row is un-deleted and the form opens.
        await confirm.click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

        // Nothing is committed; the isolated context is discarded after the test.
    });

    test('RE2: cancelling the restore prompt keeps the row deletion pending', async ({page}) => {
        const marker = `re2-${uniqueSuffix()}`;
        await openTwoSavedDeposits(page, marker, `re2b-${uniqueSuffix()}`);

        const row = modalRowsOf(page).filter({hasText: marker});
        await expect(row).toHaveCount(1, {timeout: 5_000});

        await row.locator('[data-testid^="row-actions-"]').click();
        await page.getByTestId('context-menu-action-mark-delete').click();

        await row.locator('[data-testid^="row-actions-"]').click();
        await page.getByTestId('context-menu-action-edit-single').click();
        const cancel = page.getByTestId('confirm-modal-cancel');
        await expect(cancel).toBeVisible({timeout: 5_000});

        // Cancel → the prompt closes and the form never opens.
        await cancel.click();
        await expect(page.getByTestId('confirm-modal-confirm')).toBeHidden({timeout: 5_000});
        await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: 2_000});
    });
});
