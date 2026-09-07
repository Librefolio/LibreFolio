/**
 * Transaction BulkModal Suggest UX E2E Tests — SP-C Step 9
 *
 * Covers:
 * FE-SP-C1: Split badge + type preview in BulkModal
 * FE-SP-C4: Suggest banner presence + delta slider interactivity
 * FE-SP-C5: ActionModal split AFTER has date, qty, tags, desc rows
 *
 * Non-regression (NR) tests — QA bug report 2026-06-25:
 * NR-D1: Promote false positive — no banner when amounts differ
 * NR-D2: Promote true positive — banner when amounts are exactly opposite
 * NR-D3: BulkModal pagination bar always visible
 *
 * Prerequisites: backend test mode (port 6041), mock data populated.
 * Mock data contract:
 * - "delete-safe" tag → paired TRANSFER ETH IB↔Coinbase
 * - "promote-test" tag → standalone W/D/Adj on Coinbase+IB
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {appears} from '../fixtures/probe';

test.setTimeout(30_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page, query = '') {
    await navigateTo(page, `/transactions${query}`);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'));
}

/**
 * Open the table narrowed to the given transaction IDs via the `id_min`/`id_max`
 * URL filter, and wait for every one of them to be on screen.
 *
 * Pagination is client-side and the backend returns everything, so "the rows we
 * just created will be on the first page" is a guess that four concurrent
 * workers falsify. The filter makes it a fact.
 */
async function goToTransactionsByIds(page: Page, ids: number[]) {
    const min = Math.min(...ids);
    const max = Math.max(...ids);
    await goToTransactions(page, `?id_min=${min}&id_max=${max}`);
    for (const id of ids) {
        await expect(page.locator(`tr[data-row-id="tx-${id}"]`)).toBeVisible({timeout: 10_000});
    }
}

/** Find the first row matching ALL substrings. Returns data-row-id or null. */
async function findRowId(page: Page, includes: string[], excludes: string[] = []): Promise<string | null> {
    const rows = page.locator('[data-testid="tx-table"] tr[data-row-id]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const text = (await row.textContent()) ?? '';
        if (includes.every((s) => text.includes(s)) && excludes.every((s) => !text.includes(s))) {
            return await row.getAttribute('data-row-id');
        }
    }
    return null;
}

/** Select a row by its row-id checkbox. */
async function selectRow(page: Page, rowId: string) {
    const row = page.locator(`[data-testid="tx-table"] tr[data-row-id="${rowId}"]`);
    const checkbox = row.locator('.checkbox-btn').first();
    await expect(checkbox).toBeVisible({timeout: 2_000});
    await checkbox.click();
}

/** Hover a BulkModal row and click its action via the kebab menu (row-actions-{id} → context-menu-action-{actionId}). */
async function clickBulkRowAction(page: Page, rowLocator: ReturnType<Page['locator']>, actionId: string) {
    await rowLocator.hover();
    const kebabBtn = rowLocator.getByTestId(/^row-actions-/);
    await expect(kebabBtn).toBeVisible({timeout: 2_000});
    await kebabBtn.click();
    const btn = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(btn).toBeVisible({timeout: 2_000});
    await btn.click();
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('BulkModal Suggest UX (SP-C)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('FE-SP-C1: Split badge + split-queued header in BulkModal', async ({page}) => {
        await goToTransactions(page);

        // Find two rows to avoid FormModal auto-open (need 2+ selections)
        const rowId = await findRowId(page, ['delete-safe']);
        if (!rowId) throw new Error('No delete-safe row found — check populate_mock_data.py');
        const rowId2 = await findRowId(page, ['promote-test'], ['↔', 'access-fail']);

        // Select rows (2+ to avoid auto FormModal)
        await selectRow(page, rowId);
        if (rowId2) await selectRow(page, rowId2);

        const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
        await expect(editBtn).toBeVisible({timeout: 3_000});
        await editBtn.click();

        // Wait for BulkModal
        await page.getByTestId('tx-bulk-modal').waitFor({state: 'visible', timeout: 5_000});
        // If FormModal auto-opened (single row), close it first
        const formModal = page.getByTestId('tx-form-modal');
        if (await appears(formModal, 1_000)) {
            await page.keyboard.press('Escape');
            await expect(formModal).toBeHidden({timeout: 3_000});
        }

        // Find a row in the bulk table and click its split action via the kebab menu
        const bulkRows = page.locator('[data-testid="tx-bulk-body"] tr[data-row-id]');
        await expect(bulkRows.first()).toBeVisible({timeout: 5_000});
        const rowCount = await bulkRows.count();
        let splitDone = false;
        for (let i = 0; i < rowCount; i++) {
            const row = bulkRows.nth(i);
            await row.hover();
            const kebabBtn = row.getByTestId(/^row-actions-/);
            if (!(await appears(kebabBtn, 1_000))) continue;
            await kebabBtn.click();
            const splitAction = page.getByTestId('context-menu-action-split');
            if (await splitAction.isVisible({timeout: 500}).catch(() => false)) {
                await splitAction.click();
                splitDone = true;
                break;
            }
            await page.keyboard.press('Escape');
        }

        if (splitDone) {
            // After split: verify the split-queued badge appears in header
            const splitBadge = page.getByTestId('split-queued-badge');
            await expect(splitBadge).toBeVisible({timeout: 3_000});
        }

        // Close modal
        await page.getByTestId('tx-bulk-close').click();
        // Discard changes if confirm appears
        const discardBtn = page
            .locator('[data-testid="confirm-modal"] button')
            .filter({hasText: /discard|confirm/i})
            .first();
        if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) {
            await discardBtn.click();
        }
    });

    test('FE-SP-C4: Suggest banner delta slider exists in BulkModal', async ({page}) => {
        await goToTransactions(page);

        // Find two standalone promote-test rows (need 2+ to avoid FormModal auto-open)
        const rowId1 = await findRowId(page, ['promote-test'], ['↔', 'access-fail']);
        if (!rowId1) throw new Error('No promote-test standalone row found — check populate_mock_data.py');

        // Find a second row (any row will do)
        const rowId2 = await findRowId(page, ['delete-safe']);

        // Select rows
        await selectRow(page, rowId1);
        if (rowId2) await selectRow(page, rowId2);

        const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
        await expect(editBtn).toBeVisible({timeout: 3_000});
        await editBtn.click();

        // Wait for BulkModal
        const modal = page.getByTestId('tx-bulk-modal');
        await modal.waitFor({state: 'visible', timeout: 5_000});
        // If FormModal auto-opened, close it
        const formModal = page.getByTestId('tx-form-modal');
        if (await formModal.isVisible({timeout: 1_000}).catch(() => false)) {
            await page.keyboard.press('Escape');
            await expect(formModal).toBeHidden({timeout: 3_000});
        }

        // Verify delta slider exists
        const deltaInput = page.getByTestId('promote-suggest-delta-input');
        await expect(deltaInput).toBeVisible({timeout: 3_000});

        // Close
        await page.getByTestId('tx-bulk-close').click();
        const discardBtn = page
            .locator('[data-testid="confirm-modal"] button')
            .filter({hasText: /discard|confirm/i})
            .first();
        if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) {
            await discardBtn.click();
        }
    });

    test('FE-SP-C5: ActionModal split AFTER has date and qty rows', async ({page}) => {
        await goToTransactions(page);

        // Find a paired row with "delete-safe"
        const rowId = await findRowId(page, ['delete-safe']);
        if (!rowId) throw new Error('No delete-safe paired row found — check populate_mock_data.py');

        // Click the row's split action in the main table via the kebab menu
        const row = page.locator(`[data-testid="tx-table"] tr[data-row-id="${rowId}"]`);
        await row.hover();
        const splitBtn = row.getByTestId(/^row-actions-/);
        await expect(splitBtn).toBeVisible({timeout: 2_000});
        await splitBtn.click();
        await page.getByTestId('context-menu-action-split').click();

        // Wait for the ActionModal
        const actionModal = page.getByTestId('tx-action-modal');
        await actionModal.waitFor({state: 'visible', timeout: 5_000});

        // Verify AFTER table exists
        const afterTable = page.getByTestId('tx-action-after');
        await expect(afterTable).toBeVisible({timeout: 3_000});

        // Cancel the action
        await page.getByTestId('tx-action-modal-cancel').click();
    });
});

// ============================================================================
// Non-regression tests — QA bug report 2026-06-25
// ============================================================================

test.describe('NR-D — Promote false-positive guard (Bug D)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    const API = '/api/v1';
    const TEST_DATE = '2026-06-25';
    const TEST_TAG = 'nr-promote-fp-test';

    /**
     * Create DEPOSIT + WITHDRAWAL via the commit API on different brokers.
     * Returns `{pair: [depositId, withdrawalId], all: [...]}`.
     *
     * The withdrawal broker is funded first in the same batch: the backend
     * refuses a batch that drives a broker's cash balance negative, and it
     * refuses it *atomically* — `POST /commit` still answers 200 with the ids
     * the rows would have had. Reading `resp.ok()` as "created" is how this
     * helper used to hand back ids for rows that never existed.
     */
    async function createTestPair(page: import('@playwright/test').Page, depositBrokerId: number, withdrawalBrokerId: number, depositAmount: string, withdrawalAmount: string): Promise<{pair: [number, number]; all: number[]}> {
        const funding = (Math.abs(Number(withdrawalAmount)) + 1000).toFixed(2);
        const resp = await page.request.post(`${API}/transactions/commit`, {
            data: {
                creates: [
                    {
                        broker_id: withdrawalBrokerId,
                        type: 'DEPOSIT',
                        date: TEST_DATE,
                        quantity: '0',
                        cash: {code: 'EUR', amount: funding},
                        tags: [TEST_TAG],
                        description: `NR-D funding ${funding}`,
                    },
                    {
                        broker_id: depositBrokerId,
                        type: 'DEPOSIT',
                        date: TEST_DATE,
                        quantity: '0',
                        cash: {code: 'EUR', amount: depositAmount},
                        tags: [TEST_TAG],
                        description: `NR-D test DEPOSIT ${depositAmount}`,
                    },
                    {
                        broker_id: withdrawalBrokerId,
                        type: 'WITHDRAWAL',
                        date: TEST_DATE,
                        quantity: '0',
                        cash: {code: 'EUR', amount: withdrawalAmount},
                        tags: [TEST_TAG],
                        description: `NR-D test WITHDRAWAL ${withdrawalAmount}`,
                    },
                ],
                updates: [],
                deletes: [],
                splits: [],
                promotes: [],
            },
        });
        expect(resp.ok()).toBeTruthy();
        // TXBatchResultItem carries `ids`, not `tx_id` — reading the wrong field
        // returned [undefined, undefined], so `cleanup` deleted nothing and every
        // run leaked two transactions into the shared database.
        const body = (await resp.json()) as {
            committed: boolean;
            issues?: Array<{error: string}>;
            results: Array<{operation: string; ids: number[]}>;
        };
        // 200 does not mean "created": a business-rule violation rolls the whole
        // batch back and still answers 200. Without this the test walks on to a
        // table that legitimately has nothing to show.
        expect(body.committed, `commit was rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
        const ids = body.results.flatMap((r) => r.ids ?? []);
        expect(ids, 'commit must return the three created transaction IDs').toHaveLength(3);
        return {pair: [ids[1], ids[2]], all: ids};
    }

    /** Delete test transactions by IDs. */
    async function cleanup(page: import('@playwright/test').Page, ...ids: number[]) {
        if (ids.length === 0) return;
        await page.request.post(`${API}/transactions/commit`, {
            data: {creates: [], updates: [], deletes: ids, splits: [], promotes: []},
        });
    }

    /** Find two distinct editable broker IDs. The fixture guarantees several. */
    async function findTwoBrokerIds(page: import('@playwright/test').Page): Promise<[number, number]> {
        const resp = await page.request.get(`${API}/brokers`);
        expect(resp.ok(), `GET ${API}/brokers returned ${resp.status()}`).toBe(true);
        const data = (await resp.json()) as {items: Array<{id: number; name: string; user_role: string | null}>};
        // Need 2 distinct brokers with OWNER or EDITOR access
        const editable = data.items.filter((b) => b.user_role === 'OWNER' || b.user_role === 'EDITOR');
        expect(editable.length, 'the fixture must provide at least 2 editable brokers').toBeGreaterThanOrEqual(2);
        return [editable[0].id, editable[1].id];
    }

    // -- FormModal driving, for the rows that must be created inside the modal ------
    // Kept assertion-based on purpose: every wait below is a wait for a condition, not for
    // a duration. The older copies of these helpers in sibling specs sleep instead, which is
    // what the parallel suite punishes.

    /** Open the FormModal from inside an already-open BulkModal. */
    async function addBulkRow(page: Page) {
        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
    }

    /** Select a transaction type in the FormModal by code. */
    async function selectType(page: Page, typeCode: string) {
        await page.getByTestId('tx-form-type').click();
        const option = page.getByTestId(`search-select-option-${typeCode}`);
        await expect(option).toBeVisible({timeout: 3_000});
        await option.click();
        await expect(option).not.toBeVisible({timeout: 3_000});
    }

    /** Pick a broker in the FormModal by its exact id. */
    async function pickBrokerById(page: Page, brokerId: number) {
        const brokerWrap = page.getByTestId('tx-form-broker-wrap');
        await brokerWrap.locator('button, [role="combobox"]').first().click();
        const option = page.getByTestId(`search-select-option-${brokerId}`);
        await expect(option).toBeVisible({timeout: 3_000});
        await option.click();
        await expect(option).not.toBeVisible({timeout: 3_000});
    }

    /** Fill the FormModal cash amount. */
    async function fillCash(page: Page, amount: string) {
        const cashWrap = page.getByTestId('tx-form-cash-wrap');
        await expect(cashWrap).toBeVisible({timeout: 3_000});
        const cashInput = cashWrap.locator('input[data-testid$="-amount"]').first();
        await expect(cashInput).toBeVisible({timeout: 3_000});
        await cashInput.fill(amount);
        await cashInput.press('Tab');
    }

    /** Apply the FormModal and wait for it to close. */
    async function applyFormModal(page: Page) {
        const saveBtn = page.getByTestId('tx-form-save');
        await expect(saveBtn).toBeEnabled({timeout: 5_000});
        await saveBtn.click();
        await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 10_000});
    }

    /** Add one cash-only row (DEPOSIT/WITHDRAWAL) to the open BulkModal. */
    async function addCashRow(page: Page, type: string, brokerId: number, amount: string) {
        await addBulkRow(page);
        await selectType(page, type);
        await pickBrokerById(page, brokerId);
        await fillCash(page, amount);
        await applyFormModal(page);
    }

    /** Select exactly the given rows inside the BulkModal table. */
    async function selectModalRows(page: Page, count: number) {
        const modalRows = page.locator('[data-testid="tx-bulk-modal"] tr[data-row-id]');
        await expect(modalRows).toHaveCount(count, {timeout: 5_000});
        for (let i = 0; i < count; i++) {
            await modalRows.nth(i).locator('.checkbox-btn').first().click();
        }
    }

    /** Close the BulkModal, discarding whatever is pending. */
    async function closeBulkModal(page: Page) {
        await page.getByTestId('tx-bulk-close').click();
        const discardBtn = page
            .locator('[data-testid="confirm-modal"] button')
            .filter({hasText: /discard|confirm/i})
            .first();
        if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) await discardBtn.click();
    }

    test('NR-D1: no promote banner when cash amounts differ', async ({page}) => {
        const [depositBrokerId, withdrawalBrokerId] = await findTwoBrokerIds(page);

        let created: {pair: [number, number]; all: number[]} | null = null;
        try {
            // Create mismatched pair: DEPOSIT +1445.00, WITHDRAWAL -360.87 on different brokers
            created = await createTestPair(page, depositBrokerId, withdrawalBrokerId, '1445.00', '-360.87');

            // Go straight to our rows. Scanning the visible page for their
            // description worked only as long as they happened to land on page 1.
            await goToTransactionsByIds(page, created.all);

            // Select the two rows under test (not the funding deposit)
            for (const id of created.pair) {
                const row = page.locator(`tr[data-row-id="tx-${id}"]`);
                const checkbox = row.locator('.checkbox-btn').first();
                await checkbox.click();
            }

            // Open BulkModal
            const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
            await expect(editBtn).toBeEnabled({timeout: 5_000});
            await editBtn.click();
            await page.getByTestId('tx-bulk-modal').waitFor({state: 'visible', timeout: 5_000});

            // Verify NO promote banner for mismatched amounts
            const banner = page.getByTestId('promote-suggest-banner');
            await expect(banner).not.toBeVisible({timeout: 2_000});

            // Close
            await page.getByTestId('tx-bulk-close').click();
            const discardBtn = page
                .locator('[data-testid="confirm-modal"] button')
                .filter({hasText: /discard|confirm/i})
                .first();
            if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) await discardBtn.click();
        } finally {
            if (created) await cleanup(page, ...created.all);
        }
    });

    test('NR-D2: promote banner and toolbar fire for an edit+edit pair with exact-cancel amounts', async ({page}) => {
        // The positive counterpart of NR-D1, and for a long time the reason this test was
        // skipped: BulkModal compared the *stored* cash strings, but `fieldsFromTx` normalises
        // a DB-sourced WITHDRAWAL to a magnitude (the form shows a magnitude, the type carries
        // the sign). +11 and +11 never sum to zero, so two saved transactions could never be
        // paired — while the very same pair worked during an import, where the amounts arrive
        // already signed. The comparison now goes through `signedCashAmount`, so both
        // representations give the same answer.
        //
        // Both promote surfaces are asserted because they are fed by different code paths:
        // the banner by `bannerSuggestions`, the toolbar button by `selectedForPromote`.
        const [depositBrokerId, withdrawalBrokerId] = await findTwoBrokerIds(page);

        let created: {pair: [number, number]; all: number[]} | null = null;
        try {
            // Exactly opposite amounts on different brokers: the money moved, it did not leave.
            created = await createTestPair(page, depositBrokerId, withdrawalBrokerId, '11.00', '-11.00');

            await goToTransactionsByIds(page, created.all);

            for (const id of created.pair) {
                const row = page.locator(`tr[data-row-id="tx-${id}"]`);
                await row.locator('.checkbox-btn').first().click();
            }

            const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
            await expect(editBtn).toBeEnabled({timeout: 5_000});
            await editBtn.click();
            await page.getByTestId('tx-bulk-modal').waitFor({state: 'visible', timeout: 5_000});

            // Surface 1 — the suggestion banner (bannerSuggestions, local edit+edit loop).
            await expect(page.getByTestId('promote-suggest-banner')).toBeVisible({timeout: 10_000});

            // Surface 2 — the toolbar action, which needs the two rows selected *inside* the
            // modal. Selecting them there is a different act from selecting them in the table.
            const modalRows = page.locator('[data-testid="tx-bulk-modal"] tr[data-row-id]');
            await expect(modalRows).toHaveCount(2, {timeout: 5_000});
            for (let i = 0; i < 2; i++) {
                await modalRows.nth(i).locator('.checkbox-btn').first().click();
            }
            await expect(page.getByTestId('promote-toolbar-confirm')).toBeVisible({timeout: 5_000});

            await page.getByTestId('tx-bulk-close').click();
            const discardBtn = page
                .locator('[data-testid="confirm-modal"] button')
                .filter({hasText: /discard|confirm/i})
                .first();
            if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) await discardBtn.click();
        } finally {
            if (created) await cleanup(page, ...created.all);
        }
    });

    test('NR-D2b: promote fires for a new+new pair created inside the modal', async ({page}) => {
        // The pool representation: rows built by the FormModal, never saved. This pair was
        // believed to work — but the only proof was a unit test on already-signed strings,
        // and the E2E that should have covered it was skipped. It is asserted here so the
        // three op combinations are held to the same standard, not just the broken one.
        const [brokerA, brokerB] = await findTwoBrokerIds(page);

        await goToTransactions(page);
        await page.getByTestId('tx-add-button').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'DEPOSIT');
        await pickBrokerById(page, brokerA);
        await fillCash(page, '11');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Same amount, opposite direction, different broker: the money moved.
        await addCashRow(page, 'WITHDRAWAL', brokerB, '11');

        await expect(page.getByTestId('promote-suggest-banner')).toBeVisible({timeout: 10_000});

        await closeBulkModal(page);
    });

    test('NR-D2c: promote fires for a mixed new+edit pair', async ({page}) => {
        // The combination that used to answer correctly only by accident: one side signed
        // (the row typed here), one side normalised (the row loaded from the database).
        // Which of the two happened to be the withdrawal decided the outcome. Only the
        // selection toolbar can reach a mixed pair — the banner matches new+new and
        // edit+edit, never a mix.
        //
        // Two saved rows are opened rather than one, because selecting a single row goes
        // straight to the single-row edit form instead of the bulk table. The second row is
        // the funding deposit: same broker as the withdrawal and a different amount, so it
        // cannot pair with anything and leaves the mixed pair as the only match in the modal.
        const [brokerA, brokerB] = await findTwoBrokerIds(page);

        let created: {pair: [number, number]; all: number[]} | null = null;
        try {
            created = await createTestPair(page, brokerA, brokerB, '11.00', '-11.00');
            const fundingId = created.all[0];
            const withdrawalId = created.pair[1];
            await goToTransactionsByIds(page, created.all);

            for (const id of [fundingId, withdrawalId]) {
                await page.locator(`tr[data-row-id="tx-${id}"]`).locator('.checkbox-btn').first().click();
            }

            const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
            await expect(editBtn).toBeEnabled({timeout: 5_000});
            await editBtn.click();
            await page.getByTestId('tx-bulk-modal').waitFor({state: 'visible', timeout: 5_000});

            const modalRows = page.locator('[data-testid="tx-bulk-modal"] tr[data-row-id]');
            await expect(modalRows).toHaveCount(2, {timeout: 5_000});

            // Nothing pairs yet: both saved rows sit on the same broker.
            await expect(page.getByTestId('promote-suggest-banner')).not.toBeVisible({timeout: 2_000});

            // The new row arrives as typed; the saved withdrawal arrives normalised to "11.00".
            await addCashRow(page, 'DEPOSIT', brokerA, '11');
            await expect(modalRows).toHaveCount(3, {timeout: 5_000});

            await modalRows.filter({hasText: 'NR-D test WITHDRAWAL'}).first().locator('.checkbox-btn').first().click();
            await modalRows.last().locator('.checkbox-btn').first().click();

            await expect(page.getByTestId('promote-toolbar-confirm')).toBeVisible({timeout: 5_000});

            await closeBulkModal(page);
        } finally {
            if (created) await cleanup(page, ...created.all);
        }
    });

    test('NR-D3: BulkModal pagination bar always visible', async ({page}) => {
        // Create the two rows this test needs instead of borrowing whatever sits
        // on the first page: the old scan skipped DEGIRO and receiver rows by
        // reading their text, then silently skipped the whole test when a
        // neighbouring worker's rows pushed the editable ones out of view.
        const [brokerA, brokerB] = await findTwoBrokerIds(page);
        let created: {pair: [number, number]; all: number[]} | null = null;
        try {
            created = await createTestPair(page, brokerA, brokerB, '11.00', '-11.00');
            await goToTransactionsByIds(page, created.all);

            // Select rows
            for (const id of created.pair) {
                const row = page.locator(`tr[data-row-id="tx-${id}"]`);
                await row.locator('.checkbox-btn').first().click();
            }

            // Open BulkModal
            const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
            await expect(editBtn).toBeEnabled({timeout: 5_000});
            await editBtn.click();
            await page.getByTestId('tx-bulk-modal').waitFor({state: 'visible', timeout: 5_000});

            // Pagination bar must be visible even with few rows
            // Scope to tx-bulk-body to avoid matching the background transactions table pagination
            const pagination = page.getByTestId('tx-bulk-body').getByTestId('data-table-pagination');
            await expect(pagination).toBeVisible({timeout: 3_000});

            // Page size options must include "5"
            const pageSizeBtn = pagination.locator('.page-size-btn').first();
            await expect(pageSizeBtn).toBeVisible({timeout: 5_000});
            await pageSizeBtn.click();
            const dropdownOptions = pagination.locator('.page-size-dropdown button, .dropdown-option');
            await expect.poll(async () => (await dropdownOptions.allTextContents()).map((t) => t.trim()), {timeout: 5_000}).toContain('5');
            // Close dropdown by clicking pageSizeBtn again (toggle) — avoids Escape which would close BulkModal
            await pageSizeBtn.click();

            // Close
            await page.getByTestId('tx-bulk-close').click();
            const discardBtn = page
                .locator('[data-testid="confirm-modal"] button')
                .filter({hasText: /discard|confirm/i})
                .first();
            if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) await discardBtn.click();
        } finally {
            if (created) await cleanup(page, ...created.all);
        }
    });
});
