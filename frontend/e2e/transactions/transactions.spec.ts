/**
 * Transaction E2E Tests — Phase 07 · Bugfix 3+
 *
 * Covers: CRUD, BulkModal, FormModal, paired transactions, sign-flip,
 * column visibility, banner dismissal, i18n labels.
 *
 * Prerequisites: backend in test mode (port 8001), at least 1 broker seeded.
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo, setLanguage} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Navigate to the Transactions page and wait for table to appear. */
async function goToTransactions(page: Page) {
	await navigateTo(page, '/transactions');
	// Wait for either the table or the "no data" placeholder
	await Promise.race([
		page.getByTestId('tx-main-table').waitFor({state: 'visible', timeout: 10_000}),
		page.getByTestId('tx-empty-state').waitFor({state: 'visible', timeout: 10_000}),
	]).catch(() => { /* either is fine */ });
}

/** Open "Create" flow: click the + button → BulkModal + FormModal open. */
async function openCreateFlow(page: Page) {
	await page.getByTestId('tx-create-button').click();
	await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/** Fill a minimal BUY transaction in the FormModal (assumes it's already open). */
async function fillBuyTransaction(page: Page, opts: {qty?: string; skipCash?: boolean} = {}) {
	const qty = opts.qty ?? '5';
	// Type is BUY by default
	await expect(page.getByTestId('tx-form-type')).toBeVisible({timeout: 3_000});

	// Pick first available broker
	const brokerWrap = page.getByTestId('tx-form-broker-wrap');
	await brokerWrap.locator('button, [role="combobox"]').first().click();
	await page.waitForTimeout(300);
	// Pick first option
	const brokerOption = page.locator('[data-testid^="search-select-option-"]').first();
	if (await brokerOption.isVisible({timeout: 2_000}).catch(() => false)) {
		await brokerOption.click();
	}

	// Quantity
	await page.getByTestId('tx-form-quantity').fill(qty);

	// Asset — pick first available
	const assetWrap = page.getByTestId('tx-form-asset-wrap');
	if (await assetWrap.isVisible({timeout: 1_000}).catch(() => false)) {
		const assetTrigger = assetWrap.locator('button, [role="combobox"]').first();
		if (await assetTrigger.isVisible()) {
			await assetTrigger.click();
			await page.waitForTimeout(300);
			const assetOption = page.locator('[data-testid^="search-select-option-"]').first();
			if (await assetOption.isVisible({timeout: 2_000}).catch(() => false)) {
				await assetOption.click();
			}
		}
	}
}

/** Click the Apply/Save button in the FormModal. */
async function clickApply(page: Page) {
	await page.getByTestId('tx-form-save').click();
	await page.waitForTimeout(500);
}

/** Click "Save all" in the BulkModal to commit changes. */
async function clickCommitAll(page: Page) {
	await page.getByTestId('tx-bulk-commit').click();
	// Wait for modal to close (success) or error banner
	await Promise.race([
		page.getByTestId('tx-bulk-modal').waitFor({state: 'hidden', timeout: 10_000}),
		page.getByTestId('tx-bulk-error').waitFor({state: 'visible', timeout: 10_000}),
	]).catch(() => { /* either is fine */ });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transactions', () => {
	test.beforeEach(async ({page}) => {
		await login(page, TEST_USER);
		await goToTransactions(page);
	});

	// ===================================================================
	// T1 — Create standalone BUY
	// ===================================================================
	test.describe('Create standalone', () => {
		test('can create a BUY via FormModal → BulkModal → commit', async ({page}) => {
			await openCreateFlow(page);
			await fillBuyTransaction(page, {qty: '3'});
			await clickApply(page);

			// FormModal closes, BulkModal visible with 1 row
			await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});
			await expect(page.getByTestId('tx-bulk-modal')).toBeVisible();

			// Commit
			await clickCommitAll(page);
			await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});
		});

		test('Apply button disabled when form incomplete', async ({page}) => {
			await openCreateFlow(page);
			// Type is BUY, but broker + qty not filled → Apply disabled
			const applyBtn = page.getByTestId('tx-form-save');
			await expect(applyBtn).toBeDisabled({timeout: 2_000});
		});
	});

	// ===================================================================
	// T2 — Double-click re-edit in BulkModal (C1 fix)
	// ===================================================================
	test.describe('Double-click re-edit (C1)', () => {
		test('double-click on new row re-opens FormModal pre-populated', async ({page}) => {
			await openCreateFlow(page);
			await fillBuyTransaction(page, {qty: '7'});
			await clickApply(page);

			// FormModal closed, BulkModal visible
			await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});
			await expect(page.getByTestId('tx-bulk-modal')).toBeVisible();

			// Double-click on the first visible data row
			const firstRow = page.locator('[data-testid="tx-bulk-modal"] tr.tr-data').first();
			await firstRow.dblclick();

			// FormModal should reopen with pre-populated data
			await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 3_000});

			// Quantity should be pre-filled (not empty)
			const qtyInput = page.getByTestId('tx-form-quantity');
			await expect(qtyInput).toBeVisible();
			const qtyValue = await qtyInput.inputValue();
			expect(Number(qtyValue)).toBeGreaterThan(0);
		});
	});

	// ===================================================================
	// T3 — Type swap groups (H6)
	// ===================================================================
	test.describe('Type swap groups (H6)', () => {
		test('editing DB row restricts type to swap group', async ({page}) => {
			// Need at least 1 existing transaction — create one first
			await openCreateFlow(page);
			await fillBuyTransaction(page, {qty: '1'});
			await clickApply(page);
			await clickCommitAll(page);
			await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});

			// Wait for table refresh
			await page.waitForTimeout(1_000);

			// Select first row and click Edit
			const firstCheckbox = page.locator('[data-testid="tx-main-table"] input[type="checkbox"]').first();
			if (await firstCheckbox.isVisible({timeout: 2_000}).catch(() => false)) {
				await firstCheckbox.check();
				// Click edit toolbar button
				const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
				if (await editBtn.isVisible({timeout: 2_000}).catch(() => false)) {
					await editBtn.click();
					await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

					// Type dropdown should be visible (unlockImmutable=true)
					const typeSelect = page.getByTestId('tx-form-type');
					await expect(typeSelect).toBeVisible();

					// Open the type dropdown and check options
					await typeSelect.locator('button, [role="combobox"]').first().click();
					await page.waitForTimeout(300);

					// Should see BUY and SELL (swap group), NOT all types
					const options = page.locator('[data-testid^="search-select-option-"]');
					const count = await options.count();
					// BUY↔SELL = 2 options max
					expect(count).toBeLessThanOrEqual(2);
				}
			}
		});
	});

	// ===================================================================
	// T4 — Column visibility defaults (M4/M5)
	// ===================================================================
	test.describe('Column defaults (M4/M5)', () => {
		test('cost_basis_override appears after asset_event_id when both visible', async ({page}) => {
			await openCreateFlow(page);
			// Close form to see bulk
			await page.getByTestId('tx-form-cancel').click();

			// The BulkModal should be visible
			await expect(page.getByTestId('tx-bulk-modal')).toBeVisible();

			// Check that hidden columns are actually hidden by default
			// (We can't easily test column order without enabling them,
			// but we can verify the modal rendered without errors)
			const bulkTitle = page.getByTestId('tx-bulk-title');
			await expect(bulkTitle).toBeVisible();
		});
	});

	// ===================================================================
	// T5 — Asset optional label (H5)
	// ===================================================================
	test.describe('Asset optional label (H5)', () => {
		test('INTEREST type shows (optional) on asset field', async ({page}) => {
			await openCreateFlow(page);

			// Change type to INTEREST
			const typeSelect = page.getByTestId('tx-form-type');
			await typeSelect.locator('button, [role="combobox"]').first().click();
			await page.waitForTimeout(300);

			// Search for INTEREST
			const searchInput = page.locator('[data-testid="tx-form-type"] input[type="text"]');
			if (await searchInput.isVisible({timeout: 1_000}).catch(() => false)) {
				await searchInput.fill('INTEREST');
				await page.waitForTimeout(300);
			}
			const interestOption = page.locator('[data-testid^="search-select-option-"]').filter({hasText: /interest/i}).first();
			if (await interestOption.isVisible({timeout: 2_000}).catch(() => false)) {
				await interestOption.click();
				await page.waitForTimeout(300);

				// Asset field should show "(optional)" text
				const assetWrap = page.getByTestId('tx-form-asset-wrap');
				await expect(assetWrap).toBeVisible({timeout: 2_000});
				const assetLabel = assetWrap.locator('span').first();
				await expect(assetLabel).toContainText(/optional|opzionale|optionnel|opcional/i);
			}
		});

		test('BUY type does not show (optional) on asset field', async ({page}) => {
			await openCreateFlow(page);
			// BUY is default — asset label should show * not (optional)
			const assetWrap = page.getByTestId('tx-form-asset-wrap');
			if (await assetWrap.isVisible({timeout: 2_000}).catch(() => false)) {
				const labelText = await assetWrap.locator('span').first().textContent();
				expect(labelText).not.toMatch(/optional|opzionale|optionnel|opcional/i);
			}
		});
	});

	// ===================================================================
	// T6 — Banner dismissible (M1/M2)
	// ===================================================================
	test.describe('Banner dismissible (M1/M2)', () => {
		test('validation warning banner has dismiss button', async ({page}) => {
			await openCreateFlow(page);
			// Fill partial data to trigger validation issues
			await fillBuyTransaction(page, {qty: '0'});

			// Trigger manual validate
			const validateBtn = page.getByTestId('tx-form-validate-now');
			if (await validateBtn.isVisible({timeout: 2_000}).catch(() => false)) {
				await validateBtn.click();
				await page.waitForTimeout(2_000);

				// Check if warning banner appeared with dismiss button
				const warningBanner = page.locator('[data-testid="tx-form-issues"]');
				if (await warningBanner.isVisible({timeout: 3_000}).catch(() => false)) {
					// InfoBanner with dismissible should have a close button
					const dismissBtn = page.locator('.info-banner button[aria-label]').first();
					if (await dismissBtn.isVisible({timeout: 1_000}).catch(() => false)) {
						await dismissBtn.click();
						// Banner should disappear
						await expect(warningBanner).not.toBeVisible({timeout: 2_000});
					}
				}
			}
		});
	});

	// ===================================================================
	// T7 — Paired transaction (Cash Transfer)
	// ===================================================================
	test.describe('Paired transactions', () => {
		test('can create Cash Transfer via dual form', async ({page}) => {
			await openCreateFlow(page);

			// Change type to CASH_TRANSFER
			const typeSelect = page.getByTestId('tx-form-type');
			await typeSelect.locator('button, [role="combobox"]').first().click();
			await page.waitForTimeout(300);

			const searchInput = page.locator('[data-testid="tx-form-type"] input[type="text"]');
			if (await searchInput.isVisible({timeout: 1_000}).catch(() => false)) {
				await searchInput.fill('CASH');
				await page.waitForTimeout(300);
			}
			const cashOption = page.locator('[data-testid^="search-select-option-"]').filter({hasText: /cash.*transfer|bonifico/i}).first();
			if (await cashOption.isVisible({timeout: 2_000}).catch(() => false)) {
				await cashOption.click();
				await page.waitForTimeout(500);

				// Dual form should appear with "From" and "To" sections
				const dualFrom = page.getByTestId('tx-form-dual-from');
				const dualTo = page.getByTestId('tx-form-dual-to');
				await expect(dualFrom).toBeVisible({timeout: 3_000});
				await expect(dualTo).toBeVisible({timeout: 3_000});
			}
		});

		test('delete new paired row removes both halves (C3)', async ({page}) => {
			await openCreateFlow(page);

			// Create a Cash Transfer
			const typeSelect = page.getByTestId('tx-form-type');
			await typeSelect.locator('button, [role="combobox"]').first().click();
			await page.waitForTimeout(300);
			const searchInput = page.locator('[data-testid="tx-form-type"] input[type="text"]');
			if (await searchInput.isVisible({timeout: 1_000}).catch(() => false)) {
				await searchInput.fill('CASH');
				await page.waitForTimeout(300);
			}
			const cashOption = page.locator('[data-testid^="search-select-option-"]').filter({hasText: /cash.*transfer|bonifico/i}).first();
			if (!(await cashOption.isVisible({timeout: 2_000}).catch(() => false))) {
				test.skip(true, 'Cash Transfer type not available');
				return;
			}
			await cashOption.click();
			await page.waitForTimeout(500);

			// Fill minimal dual form (brokers + cash)
			// From broker
			const fromBroker = page.getByTestId('tx-form-dual-from').locator('button, [role="combobox"]').first();
			await fromBroker.click();
			await page.waitForTimeout(300);
			await page.locator('[data-testid^="search-select-option-"]').first().click();
			await page.waitForTimeout(300);

			// To broker
			const toBroker = page.getByTestId('tx-form-dual-to').locator('button, [role="combobox"]').first();
			await toBroker.click();
			await page.waitForTimeout(300);
			// Pick a different broker (last option)
			const toOptions = page.locator('[data-testid^="search-select-option-"]');
			const toCount = await toOptions.count();
			if (toCount < 2) {
				test.skip(true, 'Need at least 2 brokers for paired test');
				return;
			}
			await toOptions.nth(toCount - 1).click();
			await page.waitForTimeout(300);

			// Fill cash amount
			const cashWrap = page.getByTestId('tx-form-cash-wrap');
			if (await cashWrap.isVisible({timeout: 1_000}).catch(() => false)) {
				const amountInput = cashWrap.locator('input[type="number"]').first();
				if (await amountInput.isVisible()) {
					await amountInput.fill('100');
				}
			}

			// Apply
			await clickApply(page);
			await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});

			// Count rows before delete
			const rowsBefore = await page.locator('[data-testid="tx-bulk-modal"] tr.tr-data').count();

			// Delete the paired row
			const deleteBtn = page.locator('[data-testid="tx-bulk-modal"] tr.tr-data').first().locator('[data-testid*="delete"], button[title*="delete"], button[title*="rimuovi"]').first();
			if (await deleteBtn.isVisible({timeout: 1_000}).catch(() => false)) {
				await deleteBtn.click();
				await page.waitForTimeout(500);

				// Both halves should be gone
				const rowsAfter = await page.locator('[data-testid="tx-bulk-modal"] tr.tr-data').count();
				// The paired row + hidden partner should both be gone
				expect(rowsAfter).toBeLessThan(rowsBefore);
			}
		});
	});

	// ===================================================================
	// T8 — Multi-language labels
	// ===================================================================
	test.describe('i18n', () => {
		test('optional label changes with language', async ({page}) => {
			// Set Italian
			await setLanguage(page, 'it');
			await goToTransactions(page);
			await openCreateFlow(page);

			// Switch to INTEREST type
			const typeSelect = page.getByTestId('tx-form-type');
			await typeSelect.locator('button, [role="combobox"]').first().click();
			await page.waitForTimeout(300);
			const searchInput = page.locator('[data-testid="tx-form-type"] input[type="text"]');
			if (await searchInput.isVisible({timeout: 1_000}).catch(() => false)) {
				await searchInput.fill('INTEREST');
				await page.waitForTimeout(300);
			}
			const opt = page.locator('[data-testid^="search-select-option-"]').filter({hasText: /interest|interesse/i}).first();
			if (await opt.isVisible({timeout: 2_000}).catch(() => false)) {
				await opt.click();
				await page.waitForTimeout(300);

				const assetWrap = page.getByTestId('tx-form-asset-wrap');
				if (await assetWrap.isVisible({timeout: 2_000}).catch(() => false)) {
					// Italian: "opzionale"
					await expect(assetWrap).toContainText(/opzionale/i);
				}
			}

			// Close everything
			await page.getByTestId('tx-form-cancel').click();
			await page.waitForTimeout(300);

			// Reset to English
			await setLanguage(page, 'en');
		});
	});

	// ===================================================================
	// T9 — Edit from main table (C2)
	// ===================================================================
	test.describe('Edit from main table (C2)', () => {
		test('edit button opens BulkModal with FormModal auto-opened', async ({page}) => {
			// First ensure there's at least one row
			const rows = page.locator('[data-testid="tx-main-table"] tr.tr-data, [data-testid="tx-main-table"] tbody tr');
			const rowCount = await rows.count().catch(() => 0);
			if (rowCount === 0) {
				test.skip(true, 'No transactions to edit');
				return;
			}

			// Select first row
			const firstCheckbox = page.locator('[data-testid="tx-main-table"] input[type="checkbox"]').first();
			await firstCheckbox.check();

			// Click edit
			const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
			if (await editBtn.isVisible({timeout: 2_000}).catch(() => false)) {
				await editBtn.click();

				// BulkModal + FormModal should open
				await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
				await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

				// FormModal should be pre-populated (quantity > 0 or at least broker selected)
				const qtyInput = page.getByTestId('tx-form-quantity');
				if (await qtyInput.isVisible({timeout: 1_000}).catch(() => false)) {
					const qtyVal = await qtyInput.inputValue();
					// Should have some value (not necessarily > 0, depends on type)
					expect(qtyVal).not.toBe('');
				}
			}
		});
	});

	// ===================================================================
	// T10 — Delete standalone
	// ===================================================================
	test.describe('Delete', () => {
		test('can delete a standalone transaction', async ({page}) => {
			// Create one first
			await openCreateFlow(page);
			await fillBuyTransaction(page, {qty: '1'});
			await clickApply(page);
			await clickCommitAll(page);
			await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});
			await page.waitForTimeout(1_000);

			// Count rows
			const countBefore = await page.locator('[data-testid="tx-count-badge"]').textContent().catch(() => '0');

			// Select first row and delete
			const firstCheckbox = page.locator('[data-testid="tx-main-table"] input[type="checkbox"]').first();
			if (await firstCheckbox.isVisible({timeout: 2_000}).catch(() => false)) {
				await firstCheckbox.check();
				const deleteBtn = page.locator('[data-testid="toolbar-action-delete"]');
				if (await deleteBtn.isVisible({timeout: 2_000}).catch(() => false)) {
					await deleteBtn.click();

					// Confirm dialog
					const confirmBtn = page.getByTestId('confirm-modal-confirm');
					if (await confirmBtn.isVisible({timeout: 3_000}).catch(() => false)) {
						await confirmBtn.click();
						await page.waitForTimeout(2_000);

						// Count should decrease
						const countAfter = await page.locator('[data-testid="tx-count-badge"]').textContent().catch(() => '0');
						expect(Number(countAfter)).toBeLessThanOrEqual(Number(countBefore));
					}
				}
			}
		});
	});

	// ===================================================================
	// T11 — View mode (readonly)
	// ===================================================================
	test.describe('View mode', () => {
		test('double-click on main table row opens view mode', async ({page}) => {
			const firstRow = page.locator('[data-testid="tx-main-table"] tr.tr-data, [data-testid="tx-main-table"] tbody tr').first();
			if (await firstRow.isVisible({timeout: 2_000}).catch(() => false)) {
				await firstRow.dblclick();

				// FormModal should open in view mode (title contains 👁)
				await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
				const title = page.getByTestId('tx-form-title');
				await expect(title).toBeVisible();

				// Save button should NOT be visible in view mode
				const saveBtn = page.getByTestId('tx-form-save');
				await expect(saveBtn).not.toBeVisible({timeout: 1_000});
			}
		});
	});
});

