/**
 * tx-commit-all-types.spec.ts — Full commit E2E for every transaction type.
 *
 * Ensures POST /transactions/commit succeeds end-to-end (FormModal → BulkModal
 * → API → table refresh) for every transaction type, including paired types.
 * Also covers edit-commit and delete-commit paths.
 *
 * Gap filled: the crash on FX_CONVERSION commit (resp.results[0].ids[0])
 * was never caught because no test exercised the actual commit for paired types.
 *
 * Prerequisites: backend in test mode (port 6041), mock data populated.
 */
import {expect, test, type Page, type Locator} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {trackTransactionWrites, type TransactionWriteTracker} from '../fixtures/db-cleanup';
import {API_BASE} from '../assets/assets-helpers';

// Payload type for commit POST
interface CommitPayload {
    creates?: unknown[];
    updates?: unknown[];
    deletes?: unknown[];
    [key: string]: unknown;
}

/** Shape of TXBatchResponse we care about: per-item results carrying the affected IDs. */
interface CommitResponse {
    committed?: boolean;
    issues?: Array<{error: string}>;
    results?: Array<{operation: string; ids?: number[]; status?: string}>;
}

// ---------------------------------------------------------------------------
// Constants — Known mock data names (stable across re-populate)
// ---------------------------------------------------------------------------

/** Broker names from populate_mock_data.py that the test user has OWNER/EDITOR access to. */
const BROKER_OWNER_A = 'Interactive Brokers'; // OWNER
const BROKER_OWNER_B = 'Directa SIM'; // EDITOR (avoid Coinbase — has pre-existing asset balance issues)
const BROKER_EDITOR = 'Directa SIM'; // EDITOR

/** An asset the mock contract guarantees, held at BROKER_OWNER_A (populate_mock_data.py). */
const ASSET_NAME = 'Apple';

// ---------------------------------------------------------------------------
// Cleanup — whoever commits, cleans up
// ---------------------------------------------------------------------------

/**
 * Nearly every test here commits real rows into TEST_USER's seeded brokers, and
 * `Transaction` is a global table: whatever a test leaves behind shows up in the
 * NAV, positions, counts and pages of every test after it — this file's
 * neighbours and, in a consolidated run, the categories that follow. The
 * txHygiene net does not cover it: that net exists only at one worker. So every
 * test records the rows its own commits created and deletes exactly those, at
 * any worker count.
 *
 * Started right after login (the tracker reads through `page.request`, which
 * needs the session cookie) and so before the first commit; drained in
 * `afterEach`, which runs for a red test too.
 */
let txWrites: TransactionWriteTracker | undefined;

async function trackCommits(page: Page) {
    txWrites = await trackTransactionWrites(page);
}

async function deleteOwnCommits() {
    const tracker = txWrites;
    txWrites = undefined;
    await tracker?.cleanup();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page, query = '') {
    await navigateTo(page, `/transactions${query}`);
    await Promise.race([page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000}), page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 10_000})]).catch(() => {});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/**
 * Open the transactions table narrowed to a single transaction ID.
 *
 * The page exposes `id_min`/`id_max` as URL filters and paginates client-side,
 * so this is the only way to be sure the row under test is on screen: with
 * neighbouring workers creating rows, "it will be near the top" is not true.
 */
async function goToTransactionById(page: Page, txId: number) {
    await goToTransactions(page, `?id_min=${txId}&id_max=${txId}`);
    await expect(page.locator(`tr[data-row-id="tx-${txId}"]`)).toBeVisible({timeout: 10_000});
}

/** A description no other test or worker can produce — the identity marker this test owns. */
function ownedMarker(prefix: string): string {
    return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

/**
 * Select one row of the main table by its id, ending on the checked state.
 *
 * The checkbox is a toggle, so it is clicked only when it is not already checked,
 * and `data-state` — what the component says — is the proof, not a CSS class.
 */
async function selectTableRow(page: Page, txId: number) {
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${txId}`);
    await expect(checkbox).toBeVisible({timeout: 5_000});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
}

/** Click a row's action via its kebab menu (row-actions-{id} → context-menu-action-{actionId}). */
async function clickKebabRowAction(row: Locator, actionId: string) {
    const page = row.page();
    await row.hover();
    const kebabBtn = row.getByTestId(/^row-actions-/);
    await expect(kebabBtn).toBeVisible({timeout: 2_000});
    await kebabBtn.click();
    const btn = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(btn).toBeVisible({timeout: 2_000});
    await btn.click();
}

async function openCreateFlow(page: Page) {
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/** Select a transaction type in the FormModal type dropdown by code (e.g. 'DEPOSIT'). */
/**
 * A SearchSelect has no "I committed" event, but its option list is torn down
 * when a choice lands — and the field cascade the choice triggers re-renders
 * before that. Waiting for the list to go is therefore a real barrier.
 */
async function optionListClosed(page: Page) {
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 5_000});
}

async function selectType(page: Page, typeCode: string) {
    const typeButton = page.getByTestId('tx-form-type');
    await typeButton.click();
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionListClosed(page);
}

/** Pick the OWNER broker of the mock contract, by name. */
async function pickOwnerBroker(page: Page) {
    const brokerWrap = page.getByTestId('tx-form-broker-wrap');
    await brokerWrap.locator('button, [role="combobox"]').first().click();
    // Awaited, never counted: `count()` answers about one instant, so a list still
    // opening read as "no such broker" and the old fallback clicked whatever option
    // sorted first — a neighbour's broker, under concurrency.
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: BROKER_OWNER_A}).first();
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionListClosed(page);
}

/** Pick a broker inside a specific dual-form panel (From/To) by known name. */
async function pickBrokerInPanel(page: Page, panelTestid: string, brokerName: string) {
    const panel = page.getByTestId(panelTestid);
    const trigger = panel.locator('[role="combobox"]').first();
    await expect(trigger).toBeVisible({timeout: 3_000});
    await trigger.click();
    // Select by visible broker name — stable across re-populate
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: brokerName});
    await expect(option.first()).toBeVisible({timeout: 3_000});
    await option.first().click();
    await optionListClosed(page);
}

/** Fill the cash amount in the standard (non-dual) cash wrapper. */
async function fillCash(page: Page, amount: string) {
    const cashWrap = page.getByTestId('tx-form-cash-wrap');
    await expect(cashWrap).toBeVisible({timeout: 2_000});
    const cashInput = cashWrap.locator('input[data-testid$="-amount"]').first();
    await expect(cashInput).toBeVisible({timeout: 1_000});
    await cashInput.fill(amount);
    await cashInput.blur();
    await expect(cashInput).not.toHaveValue('');
}

/** Fill the dual-form "From" cash amount (click + fill + blur). */
async function fillCashFrom(page: Page, amount: string) {
    const input = page.getByTestId('tx-form-cash-from-amount');
    await expect(input).toBeVisible({timeout: 2_000});
    await input.click();
    await input.fill(amount);
    await input.press('Tab');
    await expect(input).not.toHaveValue('');
}

/** Fill the dual-form "To" cash amount (click + fill + blur). */
async function fillCashTo(page: Page, amount: string) {
    const input = page.getByTestId('tx-form-cash-to-amount');
    await expect(input).toBeVisible({timeout: 2_000});
    await input.click();
    await input.fill(amount);
    await input.press('Tab');
    await expect(input).not.toHaveValue('');
}

/** Fill the quantity field. */
async function fillQuantity(page: Page, qty: string) {
    const qtyInput = page.getByTestId('tx-form-quantity');
    await expect(qtyInput).toBeVisible({timeout: 2_000});
    await qtyInput.fill(qty);
    await qtyInput.blur();
    await expect(qtyInput).not.toHaveValue('');
}

/** Pick a specific asset by searching for its name (e.g. "Apple"). */
async function pickAssetByName(page: Page, name: string) {
    const assetWrap = page.getByTestId('tx-form-asset-wrap');
    await assetWrap.locator('button, [role="combobox"]').first().click();
    // The asset select searches inline: its search box is the open trigger itself, so
    // it is always there. (The old probe for it fell back to "the first asset" when it
    // expired, and "the first asset" is whatever sorts first — a neighbour's, under
    // concurrency. `pickFirstAsset` did that on purpose; it is gone for the same reason.)
    const searchInput = page.getByTestId('tx-form-asset-search');
    await expect(searchInput).toBeVisible({timeout: 3_000});
    await searchInput.fill(name);
    // The list is debounced; the named entry arriving *is* the settle.
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: name}).first();
    await expect(option).toBeVisible({timeout: 5_000});
    await option.click();
    await optionListClosed(page);
}

/**
 * Fill the free-text description — used to stamp a row with a marker the test owns.
 *
 * The field lives inside the collapsible "optional" `<details>` section, so we
 * read the element's real `open` state rather than probing for visibility with a
 * timeout: a slow render would otherwise make us toggle a section that was
 * already open and close it.
 */
async function fillDescription(page: Page, text: string) {
    const section = page.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(section).toBeVisible({timeout: 5_000});
    if (!(await section.evaluate((el) => (el as HTMLDetailsElement).open))) {
        await page.getByTestId('tx-form-optional-toggle').click();
    }
    const descInput = page.getByTestId('tx-form-description');
    await expect(descInput).toBeVisible({timeout: 5_000});
    await descInput.fill(text);
}

/**
 * Assert a transaction is gone — by its ID, and by the description this test owns.
 *
 * Transaction ids are never reused: the table has carried `AUTOINCREMENT` since
 * plan 34, so a deleted row's id is not handed to the next insert, and an id names
 * one row for good. `?ids=<id>` coming back empty therefore proves that *this* row
 * is gone. The marker is a second, independent witness that the row which
 * disappeared was ours.
 */
async function expectTransactionGone(page: Page, txId: number, marker: string) {
    // Authoritative check: ask the backend. `page.request` shares the browser
    // context's cookies, so this is the same authenticated session.
    await expect
        .poll(
            async () => {
                const resp = await page.request.get(`${API_BASE}/transactions?ids=${txId}`);
                if (!resp.ok()) return -1;
                return ((await resp.json()) as unknown[]).length;
            },
            {timeout: 10_000, message: `transaction ${txId} should no longer exist in the backend`},
        )
        .toBe(0);
    await expect
        .poll(
            async () => {
                const resp = await page.request.get(`${API_BASE}/transactions`);
                if (!resp.ok()) return -1;
                const rows = (await resp.json()) as Array<{description?: string | null}>;
                return rows.filter((t) => t.description === marker).length;
            },
            {timeout: 10_000, message: `no transaction should still carry "${marker}"`},
        )
        .toBe(0);

    // And it must be gone from the table too: reload the view narrowed to that ID.
    // Nothing else can hold that id, so the table must render its empty state — the
    // presence barrier that keeps "no such row" from also meaning "not rendered yet".
    await goToTransactions(page, `?id_min=${txId}&id_max=${txId}`);
    await expect(page.getByTestId('tx-table').getByTestId('dt-empty')).toBeVisible({timeout: 10_000});
    await expect(page.locator(`[data-testid="tx-table"] tr[data-row-id="tx-${txId}"]`)).toHaveCount(0);
}

/** Click "Apply" in FormModal to push draft to BulkModal. */
async function applyFormModal(page: Page) {
    const saveBtn = page.getByTestId('tx-form-save');
    await expect(saveBtn).toBeVisible({timeout: 3_000});
    // Wait for button to become enabled (form validation may take a moment)
    await expect(saveBtn).toBeEnabled({timeout: 5_000});
    await saveBtn.click();
    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 10_000});
}

/**
 * Click "Save All" in BulkModal, intercept the /commit request,
 * and verify the response is committed: true.
 */
async function commitBulkModal(page: Page): Promise<{payload: CommitPayload; createdIds: number[]}> {
    const commitBtn = page.getByTestId('tx-bulk-commit');
    await expect(commitBtn).toBeEnabled({timeout: 8_000});

    // Set up request interception BEFORE clicking
    const commitPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    // The response carries the IDs the backend assigned — the only way for a
    // test to know which rows it owns. It is required, not hoped for: when a
    // missing answer meant "skip the check", a commit could go unverified and
    // the test still pass.
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});

    await commitBtn.click();

    const req = await commitPromise;
    const payload = req.postDataJSON() as CommitPayload;

    const body = (await (await responsePromise).json()) as CommitResponse;
    // A rolled-back batch still answers 200 and still reports the ids the rows
    // *would* have had, with per-item status "simulated". Only "success" rows
    // exist in the database.
    expect(body.committed, `commit was rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const createdIds = (body.results ?? []).filter((r) => r.operation === 'create' && r.status === 'success').flatMap((r) => r.ids ?? []);

    // Wait for BulkModal to close (= commit succeeded)
    await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});

    return {payload, createdIds};
}

/** Add another row to the open BulkModal; the FormModal opens for it. */
async function addBulkRow(page: Page) {
    await page.getByTestId('tx-bulk-add-row').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/**
 * Full create-and-commit flow for a standalone (non-paired) type.
 * Opens FormModal → fills fields → Apply → BulkModal → Commit → verify.
 */ async function createAndCommitStandalone(page: Page, opts: {type: string; needsAsset: boolean; needsQuantity: boolean; amount?: string; quantity?: string}) {
    await openCreateFlow(page);
    await selectType(page, opts.type);
    await pickOwnerBroker(page);

    if (opts.needsAsset) {
        await pickAssetByName(page, ASSET_NAME);
    }
    if (opts.needsQuantity) {
        await fillQuantity(page, opts.quantity ?? '1');
    }
    if (opts.amount) {
        await fillCash(page, opts.amount);
    }

    await applyFormModal(page);

    // BulkModal should be visible with the new row
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

    const {payload} = await commitBulkModal(page);
    expect((payload.creates as unknown[])?.length).toBeGreaterThanOrEqual(1);
}

// ---------------------------------------------------------------------------
// Tests — CREATE + COMMIT for every standalone type
// ---------------------------------------------------------------------------

test.describe('Create + Commit — Standalone Types', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await trackCommits(page);
        await goToTransactions(page);
    });

    test.afterEach(async () => {
        await deleteOwnCommits();
    });

    test('DEPOSIT create → commit', async ({page}) => {
        await createAndCommitStandalone(page, {type: 'DEPOSIT', needsAsset: false, needsQuantity: false, amount: '100'});
    });

    test('WITHDRAWAL create → commit', async ({page}) => {
        await createAndCommitStandalone(page, {type: 'WITHDRAWAL', needsAsset: false, needsQuantity: false, amount: '50'});
    });

    test('BUY create → commit', async ({page}) => {
        await createAndCommitStandalone(page, {type: 'BUY', needsAsset: true, needsQuantity: true, amount: '100', quantity: '5'});
    });

    test('SELL create → commit', async ({page}) => {
        // A SELL needs a position to sell. The old version relied on the
        // fixture's holdings and a "small quantity" — which is relying on
        // nobody else having sold them first. Under concurrency that is false,
        // the batch is rolled back with "Asset N quantity goes negative", and
        // before the `committed` assertion existed the test believed it had
        // succeeded. The batch now funds itself: DEPOSIT → BUY → SELL, all
        // committed together.
        await openCreateFlow(page);
        await selectType(page, 'DEPOSIT');
        await pickOwnerBroker(page);
        await fillCash(page, '1000');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        await addBulkRow(page);
        await selectType(page, 'BUY');
        await pickOwnerBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await fillCash(page, '100');
        await applyFormModal(page);

        await addBulkRow(page);
        await selectType(page, 'SELL');
        await pickOwnerBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '1');
        await fillCash(page, '50');
        await applyFormModal(page);

        const {payload} = await commitBulkModal(page);
        expect((payload.creates as unknown[])?.length).toBe(3);
    });

    test('DIVIDEND create → commit', async ({page}) => {
        await createAndCommitStandalone(page, {type: 'DIVIDEND', needsAsset: true, needsQuantity: false, amount: '10'});
    });

    test('INTEREST create → commit', async ({page}) => {
        await createAndCommitStandalone(page, {type: 'INTEREST', needsAsset: false, needsQuantity: false, amount: '5'});
    });

    test('FEE create → commit', async ({page}) => {
        await createAndCommitStandalone(page, {type: 'FEE', needsAsset: false, needsQuantity: false, amount: '3'});
    });

    test('TAX create → commit', async ({page}) => {
        await createAndCommitStandalone(page, {type: 'TAX', needsAsset: false, needsQuantity: false, amount: '7'});
    });

    test('ADJUSTMENT create → commit', async ({page}) => {
        await createAndCommitStandalone(page, {type: 'ADJUSTMENT', needsAsset: true, needsQuantity: true, quantity: '1'});
    });
});

// ---------------------------------------------------------------------------
// Tests — CREATE + COMMIT for paired types
// ---------------------------------------------------------------------------

test.describe('Create + Commit — Paired Types', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await trackCommits(page);
        await goToTransactions(page);
    });

    test.afterEach(async () => {
        await deleteOwnCommits();
    });

    test('FX_CONVERSION create → commit (dual form)', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'FX_CONVERSION');

        // Dual form should be visible
        const dualTo = page.getByTestId('tx-form-dual-to');
        await expect(dualTo).toBeVisible({timeout: 3_000});

        await pickOwnerBroker(page);
        await fillCashFrom(page, '100');
        await fillCashTo(page, '90');

        await applyFormModal(page);

        // Verify BulkModal shows the FX row with both sides
        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});
        await waitForSettled(page.getByTestId('tx-bulk-modal-root'));

        // The pair is staged (shown as a single row: its other leg rides hidden behind it)
        await expect(bulkModal.locator('tbody tr[data-row-id]')).not.toHaveCount(0, {timeout: 3_000});

        // The commit itself is the subject. This test exists because the FX commit
        // once crashed on its own answer (resp.results[0].ids[0]); the version that
        // accepted "no commit happened" — blaming Svelte event delegation — could
        // never have caught that again.
        const {payload, createdIds} = await commitBulkModal(page);
        expect((payload.creates as unknown[])?.length, 'the FX pair is sent as its two legs').toBe(2);
        expect(createdIds, 'an FX_CONVERSION commit creates both legs').toHaveLength(2);
    });

    test('CASH_TRANSFER create → commit (dual brokers + shared cash)', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'CASH_TRANSFER');

        // Dual form: From/To have broker selectors, shared cash outside
        const dualFrom = page.getByTestId('tx-form-dual-from');
        const dualTo = page.getByTestId('tx-form-dual-to');
        await expect(dualFrom).toBeVisible({timeout: 3_000});
        await expect(dualTo).toBeVisible({timeout: 3_000});

        // Pick DIFFERENT brokers by name (R3-B6: stable, not nth-dependent)
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_OWNER_A);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_OWNER_B);

        // Fill shared cash amount
        await fillCash(page, '50');

        await applyFormModal(page);

        // BulkModal should be visible with the paired row
        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});
        await waitForSettled(page.getByTestId('tx-bulk-modal-root'));

        const {payload} = await commitBulkModal(page);
        // CASH_TRANSFER creates 2 linked TX (Withdrawal + Deposit)
        expect((payload.creates as unknown[])?.length).toBeGreaterThanOrEqual(1);
    });

    test('TRANSFER (asset) create → commit (dual brokers + asset + qty)', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'TRANSFER');

        const dualFrom = page.getByTestId('tx-form-dual-from');
        const dualTo = page.getByTestId('tx-form-dual-to');
        await expect(dualFrom).toBeVisible({timeout: 3_000});
        await expect(dualTo).toBeVisible({timeout: 3_000});

        // Pick DIFFERENT brokers by name (R3-B6: stable, not nth-dependent)
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_OWNER_A);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_OWNER_B);

        // Fill shared asset + quantity (use Apple — known to be held at IB)
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '1');

        await applyFormModal(page);

        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});
        await waitForSettled(page.getByTestId('tx-bulk-modal-root'));

        const {payload} = await commitBulkModal(page);
        // TRANSFER creates 2 linked TX (TRANSFER_OUT + TRANSFER_IN)
        expect((payload.creates as unknown[])?.length).toBeGreaterThanOrEqual(1);
    });
});

// ---------------------------------------------------------------------------
// Tests — EDIT + COMMIT
// ---------------------------------------------------------------------------

test.describe('Edit + Commit', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await trackCommits(page);
        await goToTransactions(page);
    });

    test.afterEach(async () => {
        await deleteOwnCommits();
    });

    test('edit standalone → change description → commit', async ({page}) => {
        // Edit a transaction this test created. Picking "the first editable row"
        // means editing a row that belongs to a neighbouring test, which under
        // concurrency either corrupts its expectations or 404s when it deletes it.
        const marker = ownedMarker('E2E-EDIT');
        await openCreateFlow(page);
        await selectType(page, 'DEPOSIT');
        await pickOwnerBroker(page);
        await fillCash(page, '1');
        await fillDescription(page, marker);
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        const {createdIds} = await commitBulkModal(page);
        expect(createdIds.length).toBeGreaterThanOrEqual(1);
        const targetId = createdIds[0];

        await goToTransactionById(page, targetId);
        await selectTableRow(page, targetId);

        const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
        await expect(editBtn).toBeEnabled({timeout: 5_000});
        await editBtn.click();

        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // BulkModal auto-opens FormModal when editing a single TX
        const formModal = page.getByTestId('tx-form-modal');
        await expect(formModal).toBeVisible({timeout: 5_000});

        // Changing the description *is* the test. Probing for the fields with a
        // short timeout and carrying on when they "aren't there" turns slow into
        // absent: under four workers both probes expired, nothing was edited, and
        // the test then demanded that Save be enabled on a form it never dirtied.
        const edited = `${marker}-edited`;
        await fillDescription(page, edited);

        await applyFormModal(page);

        const {payload} = await commitBulkModal(page);
        expect(payload.updates as Array<{id?: number}>).toContainEqual(expect.objectContaining({id: targetId}));

        // The edit must survive a reload — this is the point of committing.
        await goToTransactionById(page, targetId);
        await expect(page.getByTestId(`tx-desc-${targetId}`)).toHaveText(edited);
    });
});

// ---------------------------------------------------------------------------
// Tests — DELETE + COMMIT
// ---------------------------------------------------------------------------

test.describe('Delete + Commit', () => {
    // The rows these tests delete are rows they created themselves; the tracker
    // only matters when a test goes red between its create and its delete.
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await trackCommits(page);
        await goToTransactions(page);
    });

    test.afterEach(async () => {
        await deleteOwnCommits();
    });

    test('delete via BulkModal mark-delete → commit', async ({page}) => {
        // Create the row this test will delete. Two markers matter: the ID the
        // backend assigns (to find the row) and a description only this test can
        // produce (to prove the row that disappeared was ours).
        const marker = ownedMarker('E2E-BULKDEL');
        await openCreateFlow(page);
        await selectType(page, 'DEPOSIT');
        await pickOwnerBroker(page);
        await fillCash(page, '1');
        await fillDescription(page, marker);
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        const {createdIds} = await commitBulkModal(page);
        expect(createdIds.length).toBeGreaterThanOrEqual(1);
        const targetId = createdIds[0];

        // Narrow the table to our own row — never "the first row with an edit
        // action", which under concurrency belongs to somebody else.
        await goToTransactionById(page, targetId);
        const targetRow = page.locator(`tr[data-row-id="tx-${targetId}"]`);
        await expect(targetRow.getByTestId(`tx-desc-${targetId}`)).toHaveText(marker);

        await selectTableRow(page, targetId);

        const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
        await expect(editBtn).toBeEnabled({timeout: 5_000});
        await editBtn.click();

        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // A single-row edit always auto-opens the FormModal (the workspace's 'edit'
        // intent): close it first. It is asserted, not probed — a probe that expired
        // left the form opening on top of the kebab menu clicked below.
        const formModal = page.getByTestId('tx-form-modal');
        await expect(formModal).toBeVisible({timeout: 5_000});
        await page.getByTestId('tx-form-close').click();
        await expect(formModal).not.toBeVisible({timeout: 3_000});

        // Mark for deletion. The BulkModal keys its rows by a client-side
        // `tempId`, not by the database id, so matching on the transaction id
        // never resolves. We selected exactly one row: assert that, and act on
        // it.
        const bulkRows = page.locator('[data-testid="tx-bulk-body"] tr[data-row-id]');
        await expect(bulkRows, 'the modal must hold exactly the row we selected').toHaveCount(1, {timeout: 5_000});
        await clickKebabRowAction(bulkRows, 'mark-delete');
        // The action staged a delete — the row's published status says so before the commit does.
        await expect(bulkRows.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'delete');

        const {payload} = await commitBulkModal(page);
        expect(payload.deletes as number[]).toContain(targetId);

        await expectTransactionGone(page, targetId, marker);
    });

    test('delete via main table row action button → bulk workspace pre-marked → commit', async ({page}) => {
        // T4: the dedicated DeleteModal is gone — a single-row delete opens the
        // bulk workspace with the row pre-marked for deletion, and the commit
        // goes through POST /transactions/commit like every other write.
        const marker = ownedMarker('E2E-ROWDEL');
        await openCreateFlow(page);
        await selectType(page, 'DEPOSIT');
        await pickOwnerBroker(page);
        await fillCash(page, '1');
        await fillDescription(page, marker);
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        const {createdIds} = await commitBulkModal(page);
        expect(createdIds.length).toBeGreaterThanOrEqual(1);
        const targetId = createdIds[0];

        await goToTransactionById(page, targetId);
        const targetRow = page.locator(`tr[data-row-id="tx-${targetId}"]`);
        await expect(targetRow.getByTestId(`tx-desc-${targetId}`)).toHaveText(marker);

        // Click the delete action via the row's kebab menu
        await clickKebabRowAction(targetRow, 'delete');

        // The bulk workspace opens with exactly this row staged as a delete. The
        // workspace publishes each row's status (`data-status` on its status cell):
        // read what the component says, not the colour class it paints.
        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});
        const stagedRows = bulkModal.locator('tbody tr[data-row-id]');
        await expect(stagedRows, 'the workspace must stage exactly the row we deleted').toHaveCount(1, {timeout: 5_000});
        await expect(stagedRows.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'delete');

        // Commit through the workspace: the payload must carry our id in deletes.
        const {payload} = await commitBulkModal(page);
        expect(payload.deletes as number[]).toContain(targetId);

        await expectTransactionGone(page, targetId, marker);
    });
});

// ---------------------------------------------------------------------------
// Tests — COST_BASIS_OVERRIDE (R3-B7)
// ---------------------------------------------------------------------------

test.describe('Cost Basis Override', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await trackCommits(page);
        await goToTransactions(page);
    });

    test.afterEach(async () => {
        await deleteOwnCommits();
    });

    test('TRANSFER with cost_basis_override → commit → verify saved value', async ({page}) => {
        const costBasis = '42.50';
        await openCreateFlow(page);
        await selectType(page, 'TRANSFER');

        // Pick different brokers for From/To
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_OWNER_A);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_OWNER_B);

        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '1');

        // Fill cost_basis_override (CompactCashCell — target the amount input inside)
        const cbInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(cbInput).toBeVisible({timeout: 2_000});
        await cbInput.fill(costBasis);
        await cbInput.blur();
        await expect(cbInput).not.toHaveValue('');

        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Intercept commit payload and verify cost_basis_override is present
        const {payload} = await commitBulkModal(page);
        const creates = payload.creates as Record<string, unknown>[];
        expect(creates?.length).toBeGreaterThanOrEqual(1);

        // At least one create should have cost_basis_override = "42.50" (or 42.5)
        const hasCostBasis = creates.some((c) => c.cost_basis_override !== undefined && c.cost_basis_override !== null && c.cost_basis_override !== '');
        expect(hasCostBasis).toBe(true);
    });

    test('ADJUSTMENT shows cost_basis field + tooltip icon visible', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'ADJUSTMENT');

        // Pick broker and asset
        await pickOwnerBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');

        // Cost basis field should be visible inline for ADJUSTMENT (no toggle needed)
        const cbInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(cbInput).toBeVisible({timeout: 3_000});

        // The help tooltip's trigger — the info icon — published by WacPreviewSection as
        // `<section testid>-help`: no CSS class, no walking up the DOM.
        const help = page.getByTestId('tx-form-cost-basis-help');
        await expect(help).toBeVisible({timeout: 2_000});
        await expect(help.locator('svg')).toBeVisible();
    });

    test('ADJUSTMENT empty cost_basis → payload sends null (not empty object)', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'ADJUSTMENT');

        await pickOwnerBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '2');

        // Do NOT fill cost_basis — leave empty
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        const {payload} = await commitBulkModal(page);
        const creates = payload.creates as Record<string, unknown>[];
        expect(creates?.length).toBeGreaterThanOrEqual(1);

        // Verify cost_basis_override is null or absent (not {amount: "", code: "..."})
        for (const c of creates) {
            if (c.cost_basis_override != null) {
                // If present, amount must NOT be empty
                const cbo = c.cost_basis_override as {amount?: string};
                expect(cbo.amount?.trim()).not.toBe('');
            }
        }
    });

    test('ADJUSTMENT with cost_basis_override → value persists in payload', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'ADJUSTMENT');

        await pickOwnerBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '3');

        // Cost basis is inline for ADJUSTMENT — fill it directly
        const cbInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(cbInput).toBeVisible({timeout: 3_000});
        await cbInput.click();
        await cbInput.fill('99.99');
        await cbInput.press('Tab'); // ensure blur fires and mode switches
        await expect(cbInput).not.toHaveValue('');

        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        const {payload} = await commitBulkModal(page);
        const creates = payload.creates as Record<string, unknown>[];
        expect(creates?.length).toBeGreaterThanOrEqual(1);

        // At least one create should have cost_basis_override with amount "99.99"
        const hasCostBasis = creates.some((c) => {
            const cbo = c.cost_basis_override as {amount?: string} | null;
            return cbo != null && cbo.amount === '99.99';
        });
        expect(hasCostBasis).toBe(true);
    });
});
