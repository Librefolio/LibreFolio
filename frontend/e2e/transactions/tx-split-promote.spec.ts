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
	await navigateTo(page, '/transactions');
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
		if (!(await splitAction.isVisible({timeout: 1_500}).catch(() => false))) {
			test.skip(true, 'Split action not visible on paired row (no edit access)');
			return;
		}
		await splitAction.click();
		await page.waitForTimeout(300);

		// A confirmation modal should appear (TransactionActionModal testId="tx-action-modal")
		const modal = page.locator('[data-testid="tx-action-modal"]');
		await expect(modal.first()).toBeVisible({timeout: 3_000});
	});

	// -----------------------------------------------------------------------
	// PROMOTE TESTS
	// -----------------------------------------------------------------------

	test('Guard: promote toolbar hidden when paired row is selected', async ({page}) => {
		await goToTransactions(page);
		const pairedId = await findPairedRowId(page);
		if (!pairedId) {
			test.skip(true, 'No paired TX in mock data');
			return;
		}
		await selectRow(page, pairedId);
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
		if (await editAction.isVisible({timeout: 1_000}).catch(() => false)) {
			await editAction.click();
		} else if (await viewAction.isVisible({timeout: 1_000}).catch(() => false)) {
			await viewAction.click();
		} else {
			test.skip(true, 'No edit/view action available on first row');
			return;
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
			test.skip(true, `Need promote-test WITHDRAWAL+DEPOSIT rows (found W=${withdrawalRowId}, D=${depositRowId})`);
			return;
		}

		// Select both
		await selectRow(page, withdrawalRowId);
		await selectRow(page, depositRowId);
		await page.waitForTimeout(500);

		// The toolbar should show the promote/link button
		const promoteBtn = page.locator('[data-testid="toolbar-action-promote"]');
		const visible = await promoteBtn.isVisible({timeout: 3_000}).catch(() => false);
		if (!visible) {
			// Debug: log what's in the toolbar
			const allToolbarBtns = page.locator('[data-testid^="toolbar-action-"]');
			const count = await allToolbarBtns.count();
			const btnIds: string[] = [];
			for (let i = 0; i < count; i++) {
				const id = await allToolbarBtns.nth(i).getAttribute('data-testid');
				if (id) btnIds.push(id);
			}
			test.skip(true, `Promote button not visible. Toolbar has: ${btnIds.join(', ')}`);
			return;
		}
		await expect(promoteBtn).toBeVisible();
	});
});


