/**
 * Transaction Split & Promote E2E Tests — Plan D2 Step F14
 *
 * Covers:
 * 1. Split from Main Table → confirm modal appears
 * 2. Guard: split hidden on standalone
 * 3. Guard: promote hidden on paired
 * 4. Promote from Main Table → select 2 promote-test rows
 * 5. BulkModal open after page refresh (NR-1 non-regression for F6)
 *
 * Prerequisites: backend test mode (port 8001), mock data populated.
 * Mock data contract: populate_mock_data.py creates tagged transactions:
 * - "promote-test" tag on standalone DEPOSIT/WITHDRAWAL for promote candidates
 *   (Coinbase/EDITOR + IB/OWNER — both editable by e2e_test_user)
 * - "promote-test-access-fail" tag on DEPOSIT/WITHDRAWAL where one broker is VIEWER
 * - "delete-safe" tag on pairs suitable for split tests
 *
 * DOM patterns (DataTable + TransactionsTable):
 * - Table wrapper: [data-testid="tx-table"]
 * - Row: tr[data-row-id="tx-{id}"] or tr[data-row-id="ghost-{id}"]
 * - Checkbox: .checkbox-btn inside td.td-select
 * - Link indicator: button.tx-link-icon[data-tx-link="{id}"]
 * - Row actions: button[data-action-id="split"], button[data-action-id="edit"], etc.
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(30_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions?page_size=200');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    await page.waitForTimeout(400);
}

/** Find the first row matching ALL substrings (and NOT matching any excludes). Returns data-row-id or null. */
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
    await page.waitForTimeout(200);
}

/** Find a paired row (has link icon). Returns row-id or null. */
async function findPairedRowId(page: Page): Promise<string | null> {
    const rows = page.locator('[data-testid="tx-table"] tr[data-row-id^="tx-"]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const link = row.locator('.tx-link-icon');
        if ((await link.count()) > 0) {
            return await row.getAttribute('data-row-id');
        }
    }
    return null;
}

/** Find a standalone row (no link icon). Returns row-id or null. */
async function findStandaloneRowId(page: Page): Promise<string | null> {
    const rows = page.locator('[data-testid="tx-table"] tr[data-row-id^="tx-"]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const link = row.locator('.tx-link-icon');
        if ((await link.count()) === 0) {
            return await row.getAttribute('data-row-id');
        }
    }
    return null;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Split & Promote', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // -----------------------------------------------------------------------
    // SPLIT TESTS
    // -----------------------------------------------------------------------

    test('Guard: split action hidden on standalone TX', async ({page}) => {
        await goToTransactions(page);
        const standaloneRowId = await findStandaloneRowId(page);
        expect(standaloneRowId, 'Need at least 1 standalone TX in mock data').toBeTruthy();

        // Hover row to make actions visible
        const row = page.locator(`[data-testid="tx-table"] tr[data-row-id="${standaloneRowId}"]`);
        await row.hover();
        await page.waitForTimeout(200);

        // Split action should NOT be visible (visible function filters paired-only)
        const splitAction = row.locator('button[data-action-id="split"]');
        await expect(splitAction).not.toBeVisible({timeout: 1_000});
    });

    test('Split from Main Table → confirm modal appears', async ({page}) => {
        await goToTransactions(page);

        // Find a paired row — prefer delete-safe tagged ones
        let pairedRowId = await findRowId(page, ['delete-safe'], []);
        if (!pairedRowId) {
            pairedRowId = await findPairedRowId(page);
        }
        expect(pairedRowId, 'Need at least 1 paired TX for split test').toBeTruthy();

        // Hover to show actions, click split
        const row = page.locator(`[data-testid="tx-table"] tr[data-row-id="${pairedRowId}"]`);
        await row.hover();
        await page.waitForTimeout(200);

        const splitAction = row.locator('button[data-action-id="split"]');
        await expect(splitAction).toBeVisible({timeout: 2_000});
        await splitAction.click();
        await page.waitForTimeout(300);

        // A confirmation modal should appear (TransactionActionModal testId="tx-action-modal")
        const modal = page.locator('[data-testid="tx-action-modal"]');
        await expect(modal.first()).toBeVisible({timeout: 3_000});

        // Verify sticky structure: header, scrollable body, footer all visible
        const content = modal.first().getByTestId('tx-action-modal-content');
        await expect(content).toBeVisible();

        // Footer buttons always visible (sticky)
        const confirmBtn = modal.first().getByTestId('tx-action-modal-confirm');
        const cancelBtn = modal.first().getByTestId('tx-action-modal-cancel');
        await expect(confirmBtn).toBeVisible();
        await expect(cancelBtn).toBeVisible();

        // Quantity cells should contain emoji (📈 or 📉) or — for zero
        const beforeTable = modal.first().getByTestId('tx-action-before');
        const qtyText = await beforeTable.textContent();
        const hasQtyIndicator = qtyText?.includes('📈') || qtyText?.includes('📉') || qtyText?.includes('—');
        expect(hasQtyIndicator, 'Quantity should show emoji or — for zero').toBeTruthy();

        // Tag badges should be colored (have style with --badge-bg)
        const tagBadges = modal.first().locator('.action-tag-badge');
        const tagCount = await tagBadges.count();
        if (tagCount > 0) {
            const style = await tagBadges.first().getAttribute('style');
            expect(style, 'Tag badge should have badge-bg CSS variable').toContain('--badge-bg');
        }
    });

    // -----------------------------------------------------------------------
    // PROMOTE TESTS
    // -----------------------------------------------------------------------

    test('Guard: promote toolbar hidden when paired row is selected', async ({page}) => {
        await goToTransactions(page);
        const pairedId = await findPairedRowId(page);
        expect(pairedId, 'Paired TX must exist — check populate_mock_data.py').toBeTruthy();
        await selectRow(page, pairedId!);
        await page.waitForTimeout(300);
        // The promote/link button should NOT appear for paired rows
        const promoteBtn = page.locator('[data-testid="toolbar-action-promote"]');
        const visible = await promoteBtn.isVisible({timeout: 1_000}).catch(() => false);
        expect(visible).toBeFalsy();
    });

    // -----------------------------------------------------------------------
    // BULKMODAL NON-REGRESSION (F6 / NR-1)
    // -----------------------------------------------------------------------

    test('NR-1: BulkModal renders correctly after page refresh', async ({page}) => {
        await goToTransactions(page);
        const rows = page.locator('[data-testid="tx-table"] tr[data-row-id^="tx-"]');
        await expect(rows.first()).toBeVisible({timeout: 8_000});
        const firstRowId = await rows.first().getAttribute('data-row-id');
        expect(firstRowId).toBeTruthy();

        // Refresh the page
        await page.reload();
        await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
        await page.waitForTimeout(400);

        // Try row action: hover + click edit or view
        const row = page.locator(`[data-testid="tx-table"] tr[data-row-id="${firstRowId}"]`);
        await row.hover();
        await page.waitForTimeout(200);

        const editAction = row.locator('button[data-action-id="edit"]');
        const viewAction = row.locator('button[data-action-id="view"]');
        const editVisible = await editAction.isVisible({timeout: 1_000}).catch(() => false);
        const viewVisible = await viewAction.isVisible({timeout: 1_000}).catch(() => false);
        expect(editVisible || viewVisible, 'First row must have edit or view action — check populate_mock_data.py').toBeTruthy();
        if (editVisible) {
            await editAction.click();
        } else {
            await viewAction.click();
        }
        await page.waitForTimeout(500);

        // A modal should open (BulkModal or FormModal)
        const anyModal = page.locator('[data-testid="tx-bulk-modal"], [data-testid="tx-form-modal"], .modal-base');
        await expect(anyModal.first()).toBeVisible({timeout: 3_000});
    });

    // -----------------------------------------------------------------------
    // PROMOTE from promote-test MOCK DATA
    // -----------------------------------------------------------------------

    test('Promote: select 2 promote-test WITHDRAWAL+DEPOSIT rows → toolbar shows link button', async ({page}) => {
        await goToTransactions(page);
        // Find promote-test WITHDRAWAL and DEPOSIT rows (exclude access-fail)
        // These should be: Coinbase(EDITOR) WITHDRAWAL -500 EUR + IB(OWNER) DEPOSIT +500 EUR
        const withdrawalRowId = await findRowId(page, ['promote-test', 'Withdrawal'], ['access-fail']);
        const depositRowId = await findRowId(page, ['promote-test', 'Deposit'], ['access-fail']);

        if (!withdrawalRowId || !depositRowId) {
            throw new Error(`Need promote-test WITHDRAWAL+DEPOSIT rows (found W=${withdrawalRowId}, D=${depositRowId}) — check populate_mock_data.py`);
        }

        // Select both
        await selectRow(page, withdrawalRowId);
        await selectRow(page, depositRowId);
        await page.waitForTimeout(500);

        // The toolbar should show the promote/link button
        const promoteBtn = page.locator('[data-testid="toolbar-action-promote"]');
        await expect(promoteBtn).toBeVisible({timeout: 3_000});
    });

    // -----------------------------------------------------------------------
    // C3 REGRESSION: Split + Edit → commit includes splits AND updates (no type in update)
    // -----------------------------------------------------------------------

    test('C3: Split + edit quantity → commit payload has splits + updates without type', async ({page}) => {
        await goToTransactions(page);

        // Find a paired "delete-safe" row (Asset Transfer)
        const pairedRowId = await findRowId(page, ['delete-safe'], []);
        expect(pairedRowId, 'delete-safe paired TX must exist — check populate_mock_data.py').toBeTruthy();

        // Select the row and open BulkModal via Edit toolbar
        await selectRow(page, pairedRowId!);
        const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
        await expect(editBtn).toBeVisible({timeout: 2_000});
        await editBtn.click();
        await page.waitForTimeout(500);

        // BulkModal should be open
        const bulkModal = page.locator('[data-testid="tx-bulk-modal"]');
        await expect(bulkModal).toBeVisible({timeout: 3_000});

        // Dismiss FormModal if it auto-opened (single row selection triggers it)
        const formModalInit = page.locator('[data-testid="tx-form-modal"]');
        if (await formModalInit.isVisible({timeout: 1_000}).catch(() => false)) {
            await page.keyboard.press('Escape');
            await expect(formModalInit).not.toBeVisible({timeout: 2_000});
            await page.waitForTimeout(300);
        }

        // Click Split on the row — need to hover to reveal row actions
        const bulkRow = bulkModal.locator('tr[data-row-id]').first();
        await bulkRow.hover();
        await page.waitForTimeout(300);
        const splitBtn = bulkModal.locator('button[data-action-id="split"]').first();
        await expect(splitBtn).toBeVisible({timeout: 2_000});
        await splitBtn.click();
        await page.waitForTimeout(500);

        // Verify split-queued badge appears in the header summary
        const splitBadge = bulkModal.locator('[data-testid="split-queued-badge"]');
        await expect(splitBadge).toBeVisible({timeout: 2_000});

        // Double-click first row to open FormModal (triggers handleEditRowClick)
        const firstRow = bulkModal.locator('tr[data-row-id]').first();
        await firstRow.dblclick();
        await page.waitForTimeout(500);

        // FormModal should open
        const formModal = page.locator('[data-testid="tx-form-modal"]');
        await expect(formModal).toBeVisible({timeout: 3_000});

        // Change quantity value in the FormModal
        const qtyInput = formModal.getByTestId('tx-form-quantity');
        await expect(qtyInput).toBeVisible({timeout: 2_000});
        await qtyInput.fill('0.123');
        await page.waitForTimeout(200);

        // Save the FormModal
        const saveBtn = formModal.locator('button[data-testid="tx-form-save"], button:has-text("Save"), button:has-text("Apply")').first();
        await saveBtn.click();
        await page.waitForTimeout(500);

        // FormModal should close
        await expect(formModal).not.toBeVisible({timeout: 2_000});

        // Now intercept the commit request and verify payload
        const commitPromise = page.waitForResponse((res) => res.url().includes('/api/v1/transactions/commit') && res.request().method() === 'POST', {timeout: 10_000});

        // Click Commit
        const commitBtn = bulkModal.getByTestId('tx-bulk-commit');
        await expect(commitBtn).toBeVisible({timeout: 2_000});
        await commitBtn.click();

        const response = await commitPromise;
        const requestBody = JSON.parse(response.request().postData() ?? '{}');
        const responseBody = await response.json();

        // CRITICAL ASSERTIONS:
        // 1. Payload must include splits
        expect(requestBody.splits, 'Payload must include splits[]').toBeDefined();
        expect(requestBody.splits.length).toBeGreaterThan(0);

        // 2. Payload must include updates with description change
        expect(requestBody.updates, 'Payload must include updates[]').toBeDefined();
        expect(requestBody.updates.length).toBeGreaterThan(0);

        // 3. Updates must NOT include 'type' field (split handles type change)
        for (const upd of requestBody.updates) {
            expect(upd.type, `Update for id=${upd.id} must NOT have type — split handles it`).toBeUndefined();
        }

        // 4. Update should contain the quantity we set
        const qtyUpdate = requestBody.updates.find((u: any) => u.quantity != null);
        expect(qtyUpdate, 'Should find our quantity update').toBeTruthy();

        // 5. Backend should accept it (no type error, no balance error with fixed mock data)
        expect(responseBody.committed, `Commit should succeed. Issues: ${JSON.stringify(responseBody.issues)}`).toBe(true);
    });
});
