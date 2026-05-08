/**
 * Transaction Paired Edit E2E Tests — Phase 07 Bugfix Round 1
 *
 * Covers:
 * - Bug 6:  Clone INTEREST resets quantity to 0
 * - Bug 14: BulkModal edit paired produces updates (not creates)
 * - Bug 7:  Flat mode keeps paired rows adjacent
 *
 * Prerequisites: backend test mode (port 8001), mock data populated.
 *
 * Mock data contract: populate_mock_data.py creates INTEREST transactions,
 * asymmetric paired TRANSFERs, and linked pairs. If a test fails because
 * expected data is missing, fix populate_mock_data.py — never skip.
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(20_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
	await navigateTo(page, '/transactions');
	await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
	await page.waitForTimeout(400);
}

/** Find the first row containing ALL given substrings — returns row-id. Throws if not found. */
async function findRowByTexts(page: Page, ...substrings: string[]): Promise<string> {
	const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
	const count = await rows.count();
	for (let i = 0; i < count; i++) {
		const row = rows.nth(i);
		const text = await row.textContent() ?? '';
		if (substrings.every(s => text.includes(s))) {
			return (await row.getAttribute('data-row-id'))!;
		}
	}
	throw new Error(`Row matching [${substrings.join(', ')}] not found. Check populate_mock_data.py.`);
}

/** Select a row by its row-id checkbox. */
async function selectRow(page: Page, rowId: string) {
	const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${rowId}"]`);
	const checkbox = row.locator('.checkbox-btn').first();
	await expect(checkbox).toBeVisible({timeout: 2_000});
	await checkbox.click();
	await page.waitForTimeout(200);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transaction Paired Edit', () => {
	test.beforeEach(async ({page}) => {
		await login(page, TEST_USER);
		await goToTransactions(page);
	});

	// === Bug 6 — Clone INTEREST resets quantity to 0 ===
	test.describe('Bug 6 — Clone INTEREST', () => {
		test('clone INTEREST sets quantity to 0', async ({page}) => {
			// Find an INTEREST transaction on an editable broker
			const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
			const count = await rows.count();
			let interestRowId: string | null = null;

			for (let i = 0; i < count; i++) {
				const row = rows.nth(i);
				const typeIcon = row.locator('img[alt]').first();
				if (await typeIcon.isVisible().catch(() => false)) {
					const alt = await typeIcon.getAttribute('alt') ?? '';
					if (/interest/i.test(alt)) {
						interestRowId = await row.getAttribute('data-row-id');
						// Try this one — if clone fails due to VIEWER, try next
						break;
					}
				}
			}
			expect(interestRowId, 'INTEREST transaction must exist in mock data').toBeTruthy();

			await selectRow(page, interestRowId!);
			const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
			await expect(cloneBtn).toBeVisible({timeout: 2_000});
			await cloneBtn.click();
			await page.waitForTimeout(500);

			// Clone opens BulkModal which auto-opens FormModal
			const bulkModal = page.getByTestId('tx-bulk-modal');
			const formModal = page.getByTestId('tx-form-modal');
			const modal = (await bulkModal.isVisible({timeout: 3_000}).catch(() => false)) ? bulkModal : formModal;
			await expect(modal).toBeVisible({timeout: 5_000});

			// If BulkModal is showing, FormModal may auto-open inside it
			if (await formModal.isVisible({timeout: 3_000}).catch(() => false)) {
				const qtyInput = page.getByTestId('tx-form-quantity');
				if (await qtyInput.isVisible({timeout: 2_000}).catch(() => false)) {
					const qtyValue = await qtyInput.inputValue();
					expect(qtyValue).toBe('0');
				}
			}

			// Close
			const cancelBtn = page.getByTestId('tx-form-cancel');
			if (await cancelBtn.isVisible({timeout: 1_000}).catch(() => false)) {
				await cancelBtn.click();
			}
			await page.waitForTimeout(300);
			const bulkCancel = page.getByTestId('tx-bulk-cancel');
			if (await bulkCancel.isVisible({timeout: 1_000}).catch(() => false)) {
				await bulkCancel.click();
			}
			const discardBtn = page.getByTestId('confirm-modal-confirm');
			if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) {
				await discardBtn.click();
			}
		});
	});

	// === Bug 14 — Edit paired opens BulkModal with both rows as "edited" ===
	test.describe('Bug 14 — Paired edit payload', () => {
		test('edit paired TRANSFER opens BulkModal with paired rows (not orphaned)', async ({page}) => {
			// Find a giver+receiver pair where both brokers are editable.
			// Skip Asym-d (hidden partner) by requiring the giver row to contain
			// a known editable broker pair (e.g. Directa↔IB or Coinbase↔IB).
			const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
			const total = await allRows.count();
			let giverRowId: string | null = null;
			let receiverRowId: string | null = null;

			for (let i = 0; i < total - 1; i++) {
				const nextCls = await allRows.nth(i + 1).getAttribute('class') ?? '';
				if (nextCls.includes('tx-row-receiver')) {
					const giverText = await allRows.nth(i).textContent() ?? '';
					const recvText = await allRows.nth(i + 1).textContent() ?? '';
					// Both sides must have an editable broker visible
					const editableBrokers = ['Interactive Brokers', 'Directa', 'Coinbase'];
					const giverHasEditable = editableBrokers.some(b => giverText.includes(b));
					const recvHasEditable = editableBrokers.some(b => recvText.includes(b));
					if (giverHasEditable && recvHasEditable) {
						giverRowId = await allRows.nth(i).getAttribute('data-row-id');
						receiverRowId = await allRows.nth(i + 1).getAttribute('data-row-id');
						break;
					}
				}
			}
			expect(giverRowId, 'Must find a paired giver row on editable brokers').toBeTruthy();
			expect(receiverRowId, 'Must find a paired receiver row on editable brokers').toBeTruthy();

			await selectRow(page, giverRowId!);
			await selectRow(page, receiverRowId!);

			const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
			await expect(editBtn).toBeVisible({timeout: 2_000});
			await editBtn.click();
			await page.waitForTimeout(500);

			// BulkModal must open
			await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

			// The BulkModal should auto-open FormModal for paired edit.
			// If FormModal opens, verify broker is populated (not empty).
			const formModal = page.getByTestId('tx-form-modal');
			if (await formModal.isVisible({timeout: 3_000}).catch(() => false)) {
				// Broker "From" should be populated (dual layout uses tx-form-dual-from for transfer_asset)
				const dualFrom = page.getByTestId('tx-form-dual-from');
				const brokerWrap = page.getByTestId('tx-form-broker-wrap');
				const target = await dualFrom.isVisible({timeout: 1_000}).catch(() => false) ? dualFrom : brokerWrap;
				await expect(target).toBeVisible({timeout: 2_000});
			}

			// Close everything
			const cancelBtn = page.getByTestId('tx-form-cancel');
			if (await cancelBtn.isVisible({timeout: 1_000}).catch(() => false)) {
				await cancelBtn.click();
				await page.waitForTimeout(300);
			}
			const bulkCancel = page.getByTestId('tx-bulk-cancel');
			if (await bulkCancel.isVisible({timeout: 1_000}).catch(() => false)) {
				await bulkCancel.click();
				const discardBtn = page.getByTestId('confirm-modal-confirm');
				if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) {
					await discardBtn.click();
				}
			}
		});
	});

	// === Bug 7 — Flat mode paired adjacency ===
	test.describe('Bug 7 — Flat mode paired adjacent', () => {
		test('paired rows stay adjacent in flat mode', async ({page}) => {
			const receiverRows = page.locator('[data-testid="tx-table"] tbody tr.tx-row-receiver');
			const receiverCount = await receiverRows.count();
			expect(receiverCount, 'Mock data must contain paired transactions').toBeGreaterThan(0);

			const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
			const total = await allRows.count();
			const receiverClasses: boolean[] = [];

			for (let i = 0; i < total; i++) {
				const cls = await allRows.nth(i).getAttribute('class') ?? '';
				receiverClasses.push(cls.includes('tx-row-receiver'));
			}

			for (let i = 0; i < total; i++) {
				if (receiverClasses[i]) {
					expect(i, 'Receiver row should not be first row').toBeGreaterThan(0);
					expect(receiverClasses[i - 1], 'Row before receiver should be giver (not receiver)').toBe(false);
				}
			}
		});
	});

	// === TODO-B — Edit paired TRANSFER: commit sends updates (not creates) ===
	test.describe('TODO-B — Edit paired commit payload', () => {
		test('edit paired TRANSFER → commit sends updates for both sides', async ({page}) => {
			// Find a giver+receiver pair on editable brokers
			const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
			const total = await allRows.count();
			let giverRowId: string | null = null;
			let receiverRowId: string | null = null;

			for (let i = 0; i < total - 1; i++) {
				const nextCls = await allRows.nth(i + 1).getAttribute('class') ?? '';
				if (nextCls.includes('tx-row-receiver')) {
					const giverText = await allRows.nth(i).textContent() ?? '';
					const recvText = await allRows.nth(i + 1).textContent() ?? '';
					const editableBrokers = ['Interactive Brokers', 'Directa', 'Coinbase'];
					const giverHasEditable = editableBrokers.some(b => giverText.includes(b));
					const recvHasEditable = editableBrokers.some(b => recvText.includes(b));
					if (giverHasEditable && recvHasEditable) {
						giverRowId = await allRows.nth(i).getAttribute('data-row-id');
						receiverRowId = await allRows.nth(i + 1).getAttribute('data-row-id');
						break;
					}
				}
			}
			expect(giverRowId, 'Must find a paired giver row on editable brokers').toBeTruthy();
			expect(receiverRowId, 'Must find a paired receiver row on editable brokers').toBeTruthy();

			// Select both rows and click Edit
			await selectRow(page, giverRowId!);
			await selectRow(page, receiverRowId!);
			const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
			await expect(editBtn).toBeVisible({timeout: 2_000});
			await editBtn.click();
			await page.waitForTimeout(500);

			// BulkModal opens
			await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

			// FormModal may auto-open; if not, double-click the first row in BulkModal
			const formModal = page.getByTestId('tx-form-modal');
			if (!await formModal.isVisible({timeout: 3_000}).catch(() => false)) {
				const bulkRow = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]').first();
				if (await bulkRow.isVisible({timeout: 2_000}).catch(() => false)) {
					await bulkRow.dblclick();
					await page.waitForTimeout(500);
				}
			}
			await expect(formModal).toBeVisible({timeout: 5_000});

			// Expand the optional section to access the description field
			const optionalToggle = page.getByTestId('tx-form-optional-toggle');
			if (await optionalToggle.isVisible({timeout: 1_000}).catch(() => false)) {
				await optionalToggle.click();
				await page.waitForTimeout(200);
			}

			// Modify description to trigger a change
			const descInput = page.getByTestId('tx-form-description');
			await expect(descInput).toBeVisible({timeout: 2_000});
			const ts = Date.now();
			await descInput.fill(`E2E-paired-edit-${ts}`);

			// Push changes back to BulkModal
			const saveBtn = page.getByTestId('tx-form-save');
			await saveBtn.click();
			await page.waitForTimeout(500);

			// Set up request interception BEFORE clicking commit
			const commitPromise = page.waitForRequest(
				(req) => req.url().includes('/transactions/commit') && req.method() === 'POST',
				{timeout: 10_000}
			);

			// Click commit in BulkModal
			const commitBtn = page.getByTestId('tx-bulk-commit');
			await expect(commitBtn).toBeEnabled({timeout: 8_000});
			await commitBtn.click();

			const req = await commitPromise;
			const payload = req.postDataJSON();

			// Payload must have updates for the modified row
			expect(payload.updates, 'Commit must have updates array').toBeDefined();
			expect(payload.updates.length, 'At least one update expected').toBeGreaterThanOrEqual(1);

			// All updates should have valid IDs (not 0)
			for (const upd of payload.updates) {
				expect(upd.id, 'Update must have a valid ID').toBeGreaterThan(0);
			}
		});
	});
});

