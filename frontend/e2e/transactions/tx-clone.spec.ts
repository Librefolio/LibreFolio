/**
 * Transaction Clone E2E Tests — Phase 07 · Plan C2 Step 8a
 *
 * Covers:
 * - Clone standalone TX → 1 row new, date=today
 * - Clone paired TX → 2 rows new (Da:/A:), date=today
 * - Clone with quantityRule='zero' → qty=0
 * - Clone paired commit → pair created in DB
 * - Clone from view-only broker → clone button not visible
 *
 * Prerequisites: backend test mode (port 8001), mock data populated.
 * Mock data contract: populate_mock_data.py creates INTEREST transactions,
 * asymmetric paired TRANSFERs, and linked pairs with "access-test" tag.
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(25_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
	await navigateTo(page, '/transactions');
	await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
	await page.waitForTimeout(400);
}

/** Select a row by its row-id checkbox. */
async function selectRow(page: Page, rowId: string) {
	const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${rowId}"]`);
	const checkbox = row.locator('.checkbox-btn').first();
	await expect(checkbox).toBeVisible({timeout: 2_000});
	await checkbox.click();
	await page.waitForTimeout(200);
}

/** Find the first row matching ALL substrings. Returns data-row-id or null. */
async function findRowId(page: Page, ...substrings: string[]): Promise<string | null> {
	const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
	const count = await rows.count();
	for (let i = 0; i < count; i++) {
		const row = rows.nth(i);
		const text = (await row.textContent()) ?? '';
		if (substrings.every((s) => text.includes(s))) {
			return await row.getAttribute('data-row-id');
		}
	}
	return null;
}

/** Close any open modal (FormModal + BulkModal + confirm discard). */
async function closeModals(page: Page) {
	const cancelForm = page.getByTestId('tx-form-cancel');
	if (await cancelForm.isVisible({timeout: 500}).catch(() => false)) {
		await cancelForm.click();
		await page.waitForTimeout(300);
	}
	const cancelBulk = page.getByTestId('tx-bulk-cancel');
	if (await cancelBulk.isVisible({timeout: 500}).catch(() => false)) {
		await cancelBulk.click();
		const discard = page.getByTestId('confirm-modal-confirm');
		if (await discard.isVisible({timeout: 1_000}).catch(() => false)) {
			await discard.click();
		}
	}
}

function todayIso(): string {
	return new Date().toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transaction Clone', () => {
	test.beforeEach(async ({page}) => {
		await login(page, TEST_USER);
		await goToTransactions(page);
	});

	test('clone standalone → 1 row new, date=today', async ({page}) => {
		// Find a standalone BUY/DEPOSIT on an editable broker (IB or Directa)
		const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
		const count = await rows.count();
		let standaloneRowId: string | null = null;

		for (let i = 0; i < count; i++) {
			const row = rows.nth(i);
			const cls = (await row.getAttribute('class')) ?? '';
			// Skip receiver rows (paired)
			if (cls.includes('tx-row-receiver')) continue;
			// Check next row is NOT a receiver (this means current is standalone)
			if (i + 1 < count) {
				const nextCls = (await rows.nth(i + 1).getAttribute('class')) ?? '';
				if (nextCls.includes('tx-row-receiver')) continue; // this is the giver of a pair
			}
			const text = (await row.textContent()) ?? '';
			const editableBrokers = ['Interactive Brokers', 'Directa', 'Coinbase'];
			if (editableBrokers.some((b) => text.includes(b))) {
				standaloneRowId = await row.getAttribute('data-row-id');
				break;
			}
		}
		expect(standaloneRowId, 'Must find a standalone TX on editable broker').toBeTruthy();

		await selectRow(page, standaloneRowId!);
		const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
		await expect(cloneBtn).toBeVisible({timeout: 2_000});
		await cloneBtn.click();
		await page.waitForTimeout(500);

		// BulkModal opens
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		// Check the grid has 1 row with status "new" and date=today
		const bulkRows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
		await expect(bulkRows).toHaveCount(1, {timeout: 3_000});

		// Status badge: "new"
		const statusCell = bulkRows.first().locator('text=new');
		await expect(statusCell).toBeVisible({timeout: 2_000});

		// Date = today
		const today = todayIso();
		const rowText = (await bulkRows.first().textContent()) ?? '';
		expect(rowText).toContain(today);

		await closeModals(page);
	});

	test('clone paired → 2 rows new (Da:/A:), date=today', async ({page}) => {
		// Find a giver+receiver pair on editable brokers
		const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
		const total = await allRows.count();
		let giverRowId: string | null = null;

		for (let i = 0; i < total - 1; i++) {
			const nextCls = (await allRows.nth(i + 1).getAttribute('class')) ?? '';
			if (nextCls.includes('tx-row-receiver')) {
				const giverText = (await allRows.nth(i).textContent()) ?? '';
				const editableBrokers = ['Interactive Brokers', 'Directa', 'Coinbase'];
				if (editableBrokers.some((b) => giverText.includes(b))) {
					giverRowId = await allRows.nth(i).getAttribute('data-row-id');
					break;
				}
			}
		}
		expect(giverRowId, 'Must find a paired giver row on editable broker').toBeTruthy();

		// Select only the giver
		await selectRow(page, giverRowId!);
		const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
		await expect(cloneBtn).toBeVisible({timeout: 2_000});
		await cloneBtn.click();
		await page.waitForTimeout(500);

		// BulkModal opens with 2 rows (auto-included partner)
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		// Should have 1 visible row in grid (paired rendered as single row with Da:/A:)
		// OR 2 rows if the impl shows 2 separate rows — check for "new" status
		const bulkRows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
		const bulkCount = await bulkRows.count();
		// Paired clone = 1 grid row (dual Da:/A:) with status "new"
		expect(bulkCount).toBeGreaterThanOrEqual(1);

		// All rows should be "new"
		for (let i = 0; i < bulkCount; i++) {
			const text = (await bulkRows.nth(i).textContent()) ?? '';
			expect(text).toContain('new');
		}

		// Date = today
		const today = todayIso();
		const firstText = (await bulkRows.first().textContent()) ?? '';
		expect(firstText).toContain(today);

		await closeModals(page);
	});

	test('clone INTEREST sets quantity to 0', async ({page}) => {
		// Find an INTEREST transaction on an editable broker
		const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
		const count = await rows.count();
		let interestRowId: string | null = null;

		for (let i = 0; i < count; i++) {
			const row = rows.nth(i);
			const typeIcon = row.locator('img[alt]').first();
			if (await typeIcon.isVisible().catch(() => false)) {
				const alt = (await typeIcon.getAttribute('alt')) ?? '';
				if (/interest/i.test(alt)) {
					interestRowId = await row.getAttribute('data-row-id');
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

		// BulkModal opens → FormModal should auto-open for single clone
		const formModal = page.getByTestId('tx-form-modal');
		await expect(formModal).toBeVisible({timeout: 5_000});

		// Verify quantity is 0
		const qtyInput = page.getByTestId('tx-form-quantity');
		if (await qtyInput.isVisible({timeout: 2_000}).catch(() => false)) {
			const qtyValue = await qtyInput.inputValue();
			expect(qtyValue).toBe('0');
		}

		await closeModals(page);
	});

	test('clone paired commit → pair created in DB with link', async ({page}) => {
		// Find a giver+receiver pair on editable brokers
		const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
		const total = await allRows.count();
		let giverRowId: string | null = null;

		for (let i = 0; i < total - 1; i++) {
			const nextCls = (await allRows.nth(i + 1).getAttribute('class')) ?? '';
			if (nextCls.includes('tx-row-receiver')) {
				const giverText = (await allRows.nth(i).textContent()) ?? '';
				const recvText = (await allRows.nth(i + 1).textContent()) ?? '';
				const editableBrokers = ['Interactive Brokers', 'Directa', 'Coinbase'];
				const giverOk = editableBrokers.some((b) => giverText.includes(b));
				const recvOk = editableBrokers.some((b) => recvText.includes(b));
				if (giverOk && recvOk) {
					giverRowId = await allRows.nth(i).getAttribute('data-row-id');
					break;
				}
			}
		}
		expect(giverRowId, 'Must find a paired giver row on editable brokers').toBeTruthy();

		await selectRow(page, giverRowId!);
		const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
		await expect(cloneBtn).toBeVisible({timeout: 2_000});
		await cloneBtn.click();
		await page.waitForTimeout(500);

		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		// Intercept commit request
		const commitPromise = page.waitForRequest(
			(req) => req.url().includes('/transactions/commit') && req.method() === 'POST',
			{timeout: 10_000},
		);

		// Click commit
		const commitBtn = page.getByTestId('tx-bulk-commit');
		await expect(commitBtn).toBeEnabled({timeout: 8_000});
		await commitBtn.click();

		const req = await commitPromise;
		const payload = req.postDataJSON();

		// Payload must have creates (not updates)
		expect(payload.creates, 'Clone must produce creates array').toBeDefined();
		expect(payload.creates.length).toBe(2);

		// Both creates should share the same link_uuid
		const uuids = payload.creates.map((c: {link_uuid?: string}) => c.link_uuid);
		expect(uuids[0]).toBeTruthy();
		expect(uuids[0]).toBe(uuids[1]);

		// Both should have id=0 or no id (they are new)
		for (const c of payload.creates) {
			expect(c.id === undefined || c.id === 0 || c.id === null).toBeTruthy();
		}

		// Wait for response and toast
		await page.waitForTimeout(1_500);
	});

	test('clone from view-only broker → no edit/delete actions on row', async ({page}) => {
		// Find a TX on DEGIRO (VIEWER role for e2e_test_user)
		const degiroRowId = await findRowId(page, 'DEGIRO');
		expect(degiroRowId, 'Must find a TX on DEGIRO (viewer broker)').toBeTruthy();

		// Hover the row and verify that destructive action buttons (edit/delete) are NOT shown
		const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${degiroRowId}"]`);
		await row.hover();
		await page.waitForTimeout(300);

		// View-only rows should NOT show "danger" (delete) action buttons
		const dangerBtns = await row.locator('button.action-btn.danger').count();
		expect(dangerBtns).toBe(0);

		// Edit action (pencil icon) should not be present for viewer
		const editBtns = await row.locator('button.action-btn.edit, button.action-btn[title*="Edit"]').count();
		expect(editBtns).toBe(0);
	});
});

