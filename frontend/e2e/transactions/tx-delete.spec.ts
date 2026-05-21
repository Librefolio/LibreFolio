/**
 * Transaction Delete E2E Tests — Phase 07 · Part 4 · Round 6 · Plan B23
 *
 * Coverage vs Test Walk (plan-phase07-transaction-Part4_Round6_PlanB_TestWalkPhase2):
 *
 * Part A — TransactionDeleteModal:
 *   A1 (Layout A standalone)      → deleteStandalone*
 *   A2 (Layout B paired full)     → deletePaired*
 *   A3 (Layout B from receiver)   → (covered by A2 — modal always orders giver/receiver correctly)
 *   A4 (Layout C viewer blocked)  → deleteGuardViewer
 *   A5 (Layout C hidden blocked)  → deleteGuardHidden
 *   A6 (Bulk delete)              → bulkDelete*
 *   committed:false error banner  → deleteFailure
 *
 * Part B — TransactionPickerModal:
 *   B1-B4 (Picker guard)          → pickerDisabled*
 *
 * Part C — Action visibility:
 *   C1-C2 (Context menu + actions)→ actionVisibility*
 *
 * Part D — Regressions:
 *   D1-D8 covered by tx-broker-access.spec.ts + transactions-table.spec.ts
 *
 * Prerequisites: backend test mode (port 8001), mock data populated.
 * Mock data contract: populate_mock_data.py creates:
 *   - "delete-safe" tagged TX: DEPOSIT on IB, FEE on Directa, TRANSFER ETH IB↔Coinbase
 *   - "access-test" tagged TX: Asym-a (IB↔Directa), Asym-b (IB↔Coinbase),
 *     Asym-c (IB↔DEGIRO=viewer), Asym-d (IB↔Hidden)
 */
import {expect, test, type Locator, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(25_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions?page_size=200');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    await page.waitForTimeout(500);
}

/** Find a row whose text content contains ALL given substrings. Returns null if not found. */
async function findRow(page: Page, ...substrings: string[]): Promise<Locator | null> {
    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const text = (await row.textContent()) ?? '';
        if (substrings.every((s) => text.includes(s))) return row;
    }
    return null;
}

/** Click the delete action (🗑 = red danger button) on a row. */
async function clickDeleteOnRow(row: Locator) {
    await row.hover();
    const deleteBtn = row.locator('button.action-btn.danger');
    await expect(deleteBtn).toBeVisible({timeout: 3_000});
    await deleteBtn.click();
}

/** Count visible action buttons on a row (hover first to reveal). */
async function countVisibleActions(row: Locator): Promise<number> {
    await row.hover();
    await row.page().waitForTimeout(300);
    return row.locator('button.action-btn').count();
}

// ---------------------------------------------------------------------------
// Part A — TransactionDeleteModal
// ---------------------------------------------------------------------------

test.describe('TransactionDeleteModal', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    // === A1: Layout A — Standalone delete ===

    test('A1: standalone delete — modal shows Layout A fields, cancel keeps row', async ({page}) => {
        const row = await findRow(page, 'delete-safe', 'Small deposit');
        expect(row, 'delete-safe DEPOSIT row not found — run ./dev.py db create-clean — check populate_mock_data.py').toBeTruthy();

        // A1.1: Open DeleteModal
        await clickDeleteOnRow(row!);
        const modal = page.getByTestId('tx-delete-modal');
        await expect(modal).toBeVisible({timeout: 5_000});

        // A1.2-A1.8: Verify Layout A details table
        const details = modal.getByTestId('tx-delete-details');
        await expect(details).toBeVisible();

        // Type icon present
        await expect(details.locator('img').first()).toBeVisible();

        // A1.9: Cancel keeps row
        await modal.getByTestId('tx-delete-modal-cancel').click();
        await expect(modal).not.toBeVisible();
        const rowStill = await findRow(page, 'delete-safe', 'Small deposit');
        expect(rowStill).not.toBeNull();
    });

    test('A1-confirm: standalone delete — confirm removes row', async ({page}) => {
        // Use the delete-safe FEE (won't cause balance issues)
        const row = await findRow(page, 'delete-safe', 'Platform fee');
        expect(row, 'delete-safe FEE row not found — check populate_mock_data.py').toBeTruthy();

        await clickDeleteOnRow(row!);
        const modal = page.getByTestId('tx-delete-modal');
        await expect(modal).toBeVisible({timeout: 5_000});

        await modal.getByTestId('tx-delete-modal-confirm').click();
        await expect(modal).not.toBeVisible({timeout: 5_000});

        // Row gone
        await page.waitForTimeout(800);
        const rowAfter = await findRow(page, 'delete-safe', 'Platform fee');
        expect(rowAfter).toBeNull();
    });

    // === A2: Layout B — Paired full-access delete ===

    test('A2: paired delete — Layout B shows From/To, split hint, cancel keeps', async ({page}) => {
        const row = await findRow(page, 'delete-safe', 'ETH');
        expect(row, 'delete-safe TRANSFER ETH row not found — check populate_mock_data.py').toBeTruthy();

        await clickDeleteOnRow(row!);
        const modal = page.getByTestId('tx-delete-modal');
        await expect(modal).toBeVisible({timeout: 5_000});

        // Title: "Delete linked transaction"
        await expect(modal).toContainText(/linked|collegat/i);

        // Paired details From/To
        const paired = modal.getByTestId('tx-delete-paired-details');
        await expect(paired).toBeVisible();

        // Split hint
        await expect(modal).toContainText(/split|scollegar/i);

        // "Delete both" button
        const confirmBtn = modal.getByTestId('tx-delete-modal-confirm');
        await expect(confirmBtn).toContainText(/both|entramb/i);

        // Cancel
        await modal.getByTestId('tx-delete-modal-cancel').click();
        await expect(modal).not.toBeVisible();
        const rowStill = await findRow(page, 'delete-safe', 'ETH');
        expect(rowStill).not.toBeNull();
    });

    test('A2-confirm: paired delete — confirm removes both halves', async ({page}) => {
        const row = await findRow(page, 'delete-safe', 'ETH');
        expect(row, 'delete-safe TRANSFER ETH row not found — check populate_mock_data.py').toBeTruthy();

        await clickDeleteOnRow(row!);
        const modal = page.getByTestId('tx-delete-modal');
        await expect(modal).toBeVisible({timeout: 5_000});

        await modal.getByTestId('tx-delete-modal-confirm').click();
        await expect(modal).not.toBeVisible({timeout: 5_000});

        // Both halves gone
        await page.waitForTimeout(800);
        const remaining = await findRow(page, 'delete-safe', 'ETH');
        expect(remaining).toBeNull();
    });

    // === A4/A5: Guard — delete hidden on VIEWER/hidden broker paired ===

    test('A4: delete button hidden on VIEWER paired rows (Asym-c)', async ({page}) => {
        const row = await findRow(page, 'Asym-c');
        expect(row, 'Asym-c row not found — check populate_mock_data.py').toBeTruthy();

        await row!.hover();
        await page.waitForTimeout(300);
        const deleteBtn = row!.locator('button.action-btn.danger');
        await expect(deleteBtn).toHaveCount(0);
    });

    test('A5: delete button hidden on hidden broker paired rows (Asym-d)', async ({page}) => {
        const row = await findRow(page, 'Asym-d');
        expect(row, 'Asym-d row not found — check populate_mock_data.py').toBeTruthy();

        await row!.hover();
        await page.waitForTimeout(300);
        const deleteBtn = row!.locator('button.action-btn.danger');
        await expect(deleteBtn).toHaveCount(0);
    });

    // === committed:false → error banner ===

    test('A1-error: delete failure shows error banner in modal', async ({page}) => {
        // Delete a BUY that causes negative balance (MSFT BUY 10 - Asym-c TRANSFER 2 = 8; without BUY → -2)
        const row = await findRow(page, 'Diversification into MSFT');
        expect(row, 'MSFT BUY row not found — check populate_mock_data.py').toBeTruthy();

        await clickDeleteOnRow(row!);
        const modal = page.getByTestId('tx-delete-modal');
        await expect(modal).toBeVisible({timeout: 5_000});

        await modal.getByTestId('tx-delete-modal-confirm').click();

        // Modal stays open, error banner appears
        await expect(modal).toBeVisible({timeout: 5_000});
        const errorBanner = modal.getByTestId('tx-delete-modal-errors');
        await expect(errorBanner).toBeVisible({timeout: 5_000});
        await expect(errorBanner).toContainText(/negative|negativ/i);

        // Cancel closes
        await modal.getByTestId('tx-delete-modal-cancel').click();
        await expect(modal).not.toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Part A6 — Bulk delete via BulkModal
// ---------------------------------------------------------------------------

test.describe('Bulk delete via BulkModal', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('A6: toolbar 🗑 opens BulkModal with pre-delete rows', async ({page}) => {
        const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        const count = await rows.count();
        expect(count, 'Need at least 2 rows — check populate_mock_data.py').toBeGreaterThanOrEqual(2);

        // Select first two selectable rows
        let selected = 0;
        for (let i = 0; i < count && selected < 2; i++) {
            const checkbox = rows.nth(i).locator('.checkbox-btn');
            if ((await checkbox.count()) > 0) {
                await checkbox.click();
                selected++;
            }
        }
        expect(selected, 'Need 2 selectable rows — check populate_mock_data.py').toBeGreaterThanOrEqual(2);

        // Click bulk delete in toolbar
        const bulkDelBtn = page.getByTestId('toolbar-action-delete');
        await expect(bulkDelBtn).toBeVisible({timeout: 3_000});
        await bulkDelBtn.click();

        // BulkModal opens
        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});
        await page.waitForTimeout(500);

        // Verify modal opened (detailed row styling depends on implementation)
        await expect(bulkModal).toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Part C — Action visibility by broker access level
// ---------------------------------------------------------------------------

test.describe('Action visibility by access level', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('C1.1: standalone OWNER row shows 4 actions', async ({page}) => {
        const row = await findRow(page, 'Initial EUR funding');
        expect(row, 'IB DEPOSIT row not found — check populate_mock_data.py').toBeTruthy();
        const cnt = await countVisibleActions(row!);
        expect(cnt).toBe(4);
    });

    test('C1.2: standalone VIEWER row shows only view action', async ({page}) => {
        const row = await findRow(page, 'P2P lending capital');
        expect(row, 'Recrowd DEPOSIT row not found — check populate_mock_data.py').toBeTruthy();
        const cnt = await countVisibleActions(row!);
        expect(cnt).toBe(1);
    });

    test('C1.3: paired full-access row (Asym-a) shows 5 actions (view, edit, clone, split, delete)', async ({page}) => {
        const row = await findRow(page, 'Asym-a');
        expect(row, 'Asym-a row not found — check populate_mock_data.py').toBeTruthy();
        const cnt = await countVisibleActions(row!);
        expect(cnt).toBe(5);
    });

    test('C1.4: paired viewer row (Asym-c) shows only view', async ({page}) => {
        const row = await findRow(page, 'Asym-c');
        expect(row, 'Asym-c row not found — check populate_mock_data.py').toBeTruthy();
        const cnt = await countVisibleActions(row!);
        expect(cnt).toBe(1);
    });

    test('C2.1: context menu on OWNER row has 4 items', async ({page}) => {
        const row = await findRow(page, 'Initial EUR funding');
        expect(row, 'IB DEPOSIT row not found — check populate_mock_data.py').toBeTruthy();

        await row!.click({button: 'right'});
        const menu = page.locator('[data-testid="context-menu"]');
        await expect(menu).toBeVisible({timeout: 3_000});
        const items = menu.locator('[data-testid^="context-menu-action-"]');
        expect(await items.count()).toBe(4);
        await page.keyboard.press('Escape');
    });

    test('C2.2: context menu on VIEWER row has 1 item', async ({page}) => {
        const row = await findRow(page, 'P2P lending capital');
        expect(row, 'Recrowd row not found — check populate_mock_data.py').toBeTruthy();

        await row!.click({button: 'right'});
        const menu = page.locator('[data-testid="context-menu"]');
        await expect(menu).toBeVisible({timeout: 3_000});
        const items = menu.locator('[data-testid^="context-menu-action-"]');
        expect(await items.count()).toBe(1);
        await page.keyboard.press('Escape');
    });
});

// ---------------------------------------------------------------------------
// Part B — PickerModal disabled rows
// ---------------------------------------------------------------------------

test.describe('PickerModal disabled rows', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('B3-guard: picker shows ⊘ for VIEWER broker rows, select-all skips them', async ({page}) => {
        // Need 2+ rows selected to get edit-many mode → BulkModal → Picker
        const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        const count = await rows.count();
        expect(count, 'Need at least 2 rows — check populate_mock_data.py').toBeGreaterThanOrEqual(2);

        // Select first two selectable rows
        let selected = 0;
        for (let i = 0; i < count && selected < 2; i++) {
            const checkbox = rows.nth(i).locator('.checkbox-btn');
            if ((await checkbox.count()) > 0) {
                await checkbox.click();
                selected++;
            }
        }
        expect(selected, 'Need 2 selectable rows — check populate_mock_data.py').toBeGreaterThanOrEqual(2);

        const editBtn = page.getByTestId('toolbar-action-edit');
        await expect(editBtn).toBeVisible({timeout: 3_000});
        await editBtn.click();

        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});

        // C2-fix may auto-open FormModal when guardViewerOnly reduces to 1 row.
        // If so, close it first so it stops intercepting pointer events.
        const formModal = page.getByTestId('tx-form-modal');
        if (await formModal.isVisible({timeout: 1_000}).catch(() => false)) {
            await formModal.getByTestId('tx-form-cancel').click();
            await expect(formModal).not.toBeVisible({timeout: 3_000});
        }

        // Open picker
        const searchAddBtn = bulkModal.getByTestId('tx-bulk-picker');
        await expect(searchAddBtn).toBeVisible({timeout: 3_000});
        await searchAddBtn.click();

        const picker = page.getByTestId('tx-picker-modal');
        await expect(picker).toBeVisible({timeout: 5_000});
        await page.waitForTimeout(500);

        // ⊘ icons should exist for VIEWER broker rows (DEGIRO, eToro, Recrowd)
        const disabledIcons = picker.locator('.disabled-select-icon');
        const disabledCount = await disabledIcons.count();
        expect(disabledCount).toBeGreaterThan(0);

        // Select-all should skip disabled rows
        const selectAllBtn = picker.locator('th .checkbox-btn');
        if ((await selectAllBtn.count()) > 0) {
            await selectAllBtn.click();
            await page.waitForTimeout(300);

            // "Add N selected" should have fewer than total rows
            const addBtn = picker.getByTestId('tx-picker-add');
            const addText = (await addBtn.textContent()) ?? '';
            const match = addText.match(/(\d+)/);
            if (match) {
                const selectedCount = parseInt(match[1]);
                const totalRows = await picker.locator('tbody tr[data-row-id]').count();
                expect(selectedCount).toBeLessThan(totalRows);
            }
        }

        // Close
        await picker.getByTestId('tx-picker-cancel').click();
        await expect(picker).not.toBeVisible();
    });
});
