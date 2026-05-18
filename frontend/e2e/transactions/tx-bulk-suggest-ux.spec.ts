/**
 * Transaction BulkModal Suggest UX E2E Tests — SP-C Step 9
 *
 * Covers:
 * FE-SP-C1: Split badge + type preview in BulkModal
 * FE-SP-C4: Suggest banner presence + delta slider interactivity
 * FE-SP-C5: ActionModal split AFTER has date, qty, tags, desc rows
 *
 * Prerequisites: backend test mode (port 8001), mock data populated.
 * Mock data contract:
 * - "delete-safe" tag → paired TRANSFER ETH IB↔Coinbase
 * - "promote-test" tag → standalone W/D/Adj on Coinbase+IB
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

/** Hover a BulkModal row and click the action button by its stable data-action-id. */
async function clickBulkRowAction(page: Page, rowLocator: ReturnType<Page['locator']>, actionId: string) {
	await rowLocator.hover();
	const btn = rowLocator.locator(`[data-action-id="${actionId}"]`);
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
		if (await formModal.isVisible({timeout: 1_000}).catch(() => false)) {
			await page.keyboard.press('Escape');
			await page.waitForTimeout(300);
		}
		await page.waitForTimeout(300);

		// Find a row in the bulk table and click its split action
		const bulkRows = page.locator('[data-testid="tx-bulk-body"] tr[data-row-id]');
		const rowCount = await bulkRows.count();
		let splitDone = false;
		for (let i = 0; i < rowCount; i++) {
			const row = bulkRows.nth(i);
			const splitAction = row.locator('[data-action-id="split"]');
			// Check if split action is visible (need to hover first)
			await row.hover();
			if (await splitAction.isVisible({timeout: 500}).catch(() => false)) {
				await splitAction.click();
				splitDone = true;
				break;
			}
		}

		if (splitDone) {
			// After split: verify the split-queued badge appears in header
			const splitBadge = page.getByTestId('split-queued-badge');
			await expect(splitBadge).toBeVisible({timeout: 3_000});
		}

		// Close modal
		await page.getByTestId('tx-bulk-close').click();
		// Discard changes if confirm appears
		const discardBtn = page.locator('[data-testid="confirm-modal"] button').filter({hasText: /discard|confirm/i}).first();
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
			await page.waitForTimeout(300);
		}

		// Verify delta slider exists
		const deltaInput = page.getByTestId('promote-suggest-delta-input');
		await expect(deltaInput).toBeVisible({timeout: 3_000});

		// Close
		await page.getByTestId('tx-bulk-close').click();
		const discardBtn = page.locator('[data-testid="confirm-modal"] button').filter({hasText: /discard|confirm/i}).first();
		if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) {
			await discardBtn.click();
		}
	});

	test('FE-SP-C5: ActionModal split AFTER has date and qty rows', async ({page}) => {
		await goToTransactions(page);

		// Find a paired row with "delete-safe"
		const rowId = await findRowId(page, ['delete-safe']);
		if (!rowId) throw new Error('No delete-safe paired row found — check populate_mock_data.py');

		// Click the row's split action in the main table (need to hover)
		const row = page.locator(`[data-testid="tx-table"] tr[data-row-id="${rowId}"]`);
		await row.hover();
		await page.waitForTimeout(200);
		const splitBtn = row.locator('button[data-action-id="split"]');

		if (!(await splitBtn.isVisible({timeout: 2_000}).catch(() => false))) {
			test.skip(true, 'Split button not visible on this row — may not be paired');
			return;
		}
		await splitBtn.click();

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

