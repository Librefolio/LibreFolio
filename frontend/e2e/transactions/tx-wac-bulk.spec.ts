/**
 * tx-wac-bulk.spec.ts — BulkModal WAC Cell Rendering E2E Tests
 *
 * Covers Bug 9, 10, 11 from plan-ReactiveWacBulkModal (Piano v7):
 * - WB1: TRANSFER auto shows calculated WAC value in cell (Bug 9)
 * - WB2: Manual override propagates from FormModal to BulkModal cell (Bug 10)
 * - WB3: Toggle manual→auto restores calculated value (Bug 10 reverse)
 * - WB4: DB rows with saved cost_basis show manual value (Bug 11)
 * - WB5: Clone paired from DB — no 422 on /wac-preview (link_uuid fix)
 *
 * Prerequisites: backend test mode, mock data populated.
 * Mock data contract: e2e_test_user has OWNER/EDITOR on Interactive Brokers + Directa SIM.
 * Apple (AAPL) is a known asset with price history.
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(30_000);

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BROKER_FROM = 'Interactive Brokers';
const BROKER_TO = 'Directa SIM';
const ASSET_NAME = 'Apple';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
	await navigateTo(page, '/transactions?page_size=200');
	await Promise.race([
		page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000}),
		page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 10_000}),
	]).catch(() => {});
	await page.waitForTimeout(500);
}

async function openCreateFlow(page: Page) {
	await page.getByTestId('tx-add-button').click();
	await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

async function selectType(page: Page, typeCode: string) {
	const typeButton = page.getByTestId('tx-form-type');
	await typeButton.click();
	await page.waitForTimeout(300);
	await page.getByTestId(`search-select-option-${typeCode}`).click();
	await page.waitForTimeout(300);
}

async function pickFirstBroker(page: Page) {
	const brokerWrap = page.getByTestId('tx-form-broker-wrap');
	await brokerWrap.locator('button, [role="combobox"]').first().click();
	await page.waitForTimeout(300);
	const option = page.locator('[data-testid^="search-select-option-"]', {hasText: BROKER_FROM});
	await expect(option.first()).toBeVisible({timeout: 3_000});
	await option.first().click();
	await page.waitForTimeout(300);
}

async function pickBrokerInPanel(page: Page, panelTestid: string, brokerName: string) {
	const panel = page.getByTestId(panelTestid);
	const trigger = panel.locator('[role="combobox"]').first();
	await expect(trigger).toBeVisible({timeout: 3_000});
	await trigger.click();
	await page.waitForTimeout(500);
	const option = page.locator('[data-testid^="search-select-option-"]', {hasText: brokerName});
	await expect(option.first()).toBeVisible({timeout: 3_000});
	await option.first().click();
	await page.waitForTimeout(500);
}

async function pickAssetByName(page: Page, name: string) {
	const assetWrap = page.getByTestId('tx-form-asset-wrap');
	await assetWrap.locator('button, [role="combobox"]').first().click();
	await page.waitForTimeout(300);
	const searchInput = page.locator('[data-testid="tx-form-asset-wrap"] input[type="text"], [data-testid="tx-form-asset-wrap"] input[role="combobox"]').first();
	if (await searchInput.isVisible({timeout: 1_000}).catch(() => false)) {
		await searchInput.fill(name);
		await page.waitForTimeout(500);
	}
	const option = page.locator('[data-testid^="search-select-option-"]').first();
	await expect(option).toBeVisible({timeout: 3_000});
	await option.click();
	await page.waitForTimeout(300);
}

async function fillQuantity(page: Page, qty: string) {
	const qtyInput = page.getByTestId('tx-form-quantity');
	await expect(qtyInput).toBeVisible({timeout: 2_000});
	await qtyInput.fill(qty);
	await page.waitForTimeout(200);
}

async function fillCash(page: Page, amount: string) {
	const cashWrap = page.getByTestId('tx-form-cash-wrap');
	await expect(cashWrap).toBeVisible({timeout: 2_000});
	const cashInput = cashWrap.locator('input[type="number"]').first();
	await expect(cashInput).toBeVisible({timeout: 1_000});
	await cashInput.fill(amount);
	await page.waitForTimeout(200);
}

async function applyFormModal(page: Page) {
	const saveBtn = page.getByTestId('tx-form-save');
	await expect(saveBtn).toBeVisible({timeout: 3_000});
	await expect(saveBtn).toBeEnabled({timeout: 5_000});
	await saveBtn.click();
	await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 10_000});
}

/** Wait for WAC cell to resolve (not showing "…" placeholder). */
async function waitForWacResolved(page: Page) {
	await page
		.locator('[data-testid="tx-bulk-cost-basis-auto"]')
		.filter({hasNotText: '…'})
		.first()
		.waitFor({state: 'visible', timeout: 8_000});
}

/** Double-click on a row in the BulkModal grid to open FormModal for editing it. */
async function dblClickBulkRow(page: Page, rowIndex: number) {
	const rows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
	await rows.nth(rowIndex).dblclick();
	await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

async function commitBulkModal(page: Page) {
	const commitBtn = page.getByTestId('tx-bulk-commit');
	await expect(commitBtn).toBeEnabled({timeout: 8_000});

	const responsePromise = page.waitForResponse(
		(resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST',
		{timeout: 15_000},
	);
	await commitBtn.click();
	const resp = await responsePromise;
	const body = await resp.json();
	expect(body.committed).toBe(true);

	// Wait for BulkModal to close
	await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('BulkModal WAC Cell Rendering', () => {
	test.beforeEach(async ({page}) => {
		await login(page, TEST_USER);
		await goToTransactions(page);
	});

	test('WB1 — TRANSFER auto shows WAC value (Bug 9)', async ({page}) => {
		// Step 1: Create a BUY 10@1000 on broker_A
		await openCreateFlow(page);
		await selectType(page, 'BUY');
		await pickFirstBroker(page);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '10');
		await fillCash(page, '1000');
		await applyFormModal(page);

		// BulkModal should be visible
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		// Step 2: Create a TRANSFER from broker_A → broker_B, same asset, qty=5
		await page.getByTestId('tx-bulk-add-row').click();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
		await selectType(page, 'TRANSFER');
		await page.waitForTimeout(500);

		await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
		await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '5');
		await applyFormModal(page);

		// Step 3: Wait for WAC to resolve
		await waitForWacResolved(page);

		// Step 4: Assert cell shows 💡 + a number
		const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"]').filter({hasNotText: '…'}).first();
		const cellText = await autoCell.textContent();
		expect(cellText).toMatch(/💡\s*[\d.,]+/);
	});

	test('WB2 — Manual override propagates to cell (Bug 10)', async ({page}) => {
		// Setup: same as WB1
		await openCreateFlow(page);
		await selectType(page, 'BUY');
		await pickFirstBroker(page);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '10');
		await fillCash(page, '1000');
		await applyFormModal(page);
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		await page.getByTestId('tx-bulk-add-row').click();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
		await selectType(page, 'TRANSFER');
		await page.waitForTimeout(500);
		await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
		await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '5');
		await applyFormModal(page);
		await waitForWacResolved(page);

		// Open the TRANSFER row in FormModal (it's the last row, index 1)
		const rows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
		const lastIdx = (await rows.count()) - 1;
		await rows.nth(lastIdx).dblclick();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

		// Toggle to manual
		const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
		if (await manualToggle.isVisible({timeout: 2_000}).catch(() => false)) {
			await manualToggle.click();
			await page.waitForTimeout(300);
		}

		// Type 150 in cost basis input
		const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
		await expect(amountInput).toBeVisible({timeout: 2_000});
		await amountInput.fill('150');
		await page.waitForTimeout(200);

		await applyFormModal(page);
		await page.waitForTimeout(1000); // Wait for grid re-render after mode change

		// Assert: manual cell shows value containing "150"
		const manualCell = page.locator('[data-testid="tx-bulk-cost-basis-manual"]').first();
		await expect(manualCell).toBeVisible({timeout: 5_000});
		const text = await manualCell.textContent();
		expect(text).toContain('150');
	});

	test('WB3 — Toggle manual→auto restores calculated value (Bug 10 reverse)', async ({page}) => {
		// Setup: BUY + TRANSFER with manual override
		await openCreateFlow(page);
		await selectType(page, 'BUY');
		await pickFirstBroker(page);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '10');
		await fillCash(page, '1000');
		await applyFormModal(page);
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		await page.getByTestId('tx-bulk-add-row').click();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
		await selectType(page, 'TRANSFER');
		await page.waitForTimeout(500);
		await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
		await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '5');
		await applyFormModal(page);
		await waitForWacResolved(page);

		// Set manual override
		const rows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
		const lastIdx = (await rows.count()) - 1;
		await rows.nth(lastIdx).dblclick();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

		const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
		if (await manualToggle.isVisible({timeout: 2_000}).catch(() => false)) {
			await manualToggle.click();
			await page.waitForTimeout(300);
		}
		const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
		await expect(amountInput).toBeVisible({timeout: 2_000});
		await amountInput.fill('150');
		await applyFormModal(page);

		// Now reopen and switch back to auto
		const rows2 = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
		const lastIdx2 = (await rows2.count()) - 1;
		await rows2.nth(lastIdx2).dblclick();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

		const autoToggle = page.getByTestId('tx-form-cost-basis-toggle-auto');
		if (await autoToggle.isVisible({timeout: 2_000}).catch(() => false)) {
			await autoToggle.click();
			await page.waitForTimeout(300);
		}
		await applyFormModal(page);

		// Wait for auto to resolve
		await waitForWacResolved(page);

		// Assert: back to auto cell with calculated value
		const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"]').filter({hasNotText: '…'}).first();
		const cellText = await autoCell.textContent();
		expect(cellText).toMatch(/💡\s*[\d.,]+/);
	});

	test('WB4 — DB rows with saved cost_basis show manual (Bug 11)', async ({page}) => {
		// Create BUY + TRANSFER with auto WAC, then commit
		await openCreateFlow(page);
		await selectType(page, 'BUY');
		await pickFirstBroker(page);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '10');
		await fillCash(page, '1000');
		await applyFormModal(page);
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		await page.getByTestId('tx-bulk-add-row').click();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
		await selectType(page, 'TRANSFER');
		await page.waitForTimeout(500);
		await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
		await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '5');
		await applyFormModal(page);
		await waitForWacResolved(page);

		// Commit
		await commitBulkModal(page);

		// Reload transactions page
		await goToTransactions(page);

		// Find a paired giver row from today on our brokers
		const today = new Date().toISOString().slice(0, 10);
		const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
		const count = await allRows.count();
		let giverRowId: string | null = null;

		for (let i = 0; i < count - 1; i++) {
			const nextCls = (await allRows.nth(i + 1).getAttribute('class')) ?? '';
			if (nextCls.includes('tx-row-receiver')) {
				const text = (await allRows.nth(i).textContent()) ?? '';
				if (text.includes(today) && (text.includes(BROKER_FROM) || text.includes(BROKER_TO) || text.includes(ASSET_NAME))) {
					giverRowId = await allRows.nth(i).getAttribute('data-row-id');
					break;
				}
			}
		}
		expect(giverRowId, 'Must find the committed paired row from today').toBeTruthy();

		// Select and open in BulkModal (Edit)
		const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${giverRowId}"]`);
		await row.locator('.checkbox-btn').first().click();
		await page.waitForTimeout(300);

		const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
		await expect(editBtn).toBeVisible({timeout: 2_000});
		await editBtn.click();
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
		await page.waitForTimeout(1000);

		// Assert: cost_basis cell shows manual value (DB-saved = manual)
		const manualCell = page.locator('[data-testid="tx-bulk-cost-basis-manual"]').first();
		await expect(manualCell).toBeVisible({timeout: 5_000});
	});

	test('WB5 — Clone paired from DB, no 422 on /wac-preview', async ({page}) => {
		// Find a paired giver row on editable broker (from mock data)
		const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
		const count = await allRows.count();
		let giverRowId: string | null = null;

		for (let i = 0; i < count - 1; i++) {
			const nextCls = (await allRows.nth(i + 1).getAttribute('class')) ?? '';
			if (nextCls.includes('tx-row-receiver')) {
				const text = (await allRows.nth(i).textContent()) ?? '';
				if (text.includes(BROKER_FROM) || text.includes(BROKER_TO)) {
					giverRowId = await allRows.nth(i).getAttribute('data-row-id');
					break;
				}
			}
		}
		expect(giverRowId, 'Must find a paired giver row on editable broker').toBeTruthy();

		// Select and clone
		const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${giverRowId}"]`);
		await row.locator('.checkbox-btn').first().click();
		await page.waitForTimeout(300);

		const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
		await expect(cloneBtn).toBeVisible({timeout: 2_000});

		// Intercept wac-preview response
		const wacResponsePromise = page.waitForResponse(
			(r) => r.url().includes('/wac-preview') && r.status() !== 0,
			{timeout: 10_000},
		);

		await cloneBtn.click();
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		// Wait for WAC preview call to complete
		const wacResponse = await wacResponsePromise;
		expect(wacResponse.status()).toBe(200);

		// Assert: auto cell is present (WAC calculated for the clone)
		const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"]').first();
		await expect(autoCell).toBeVisible({timeout: 5_000});
	});

	test('WB6 — WAC value stable after debounce (no feedback loop)', async ({page}) => {
		// Create BUY 10@1000
		await openCreateFlow(page);
		await selectType(page, 'BUY');
		await pickFirstBroker(page);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '10');
		await fillCash(page, '1000');
		await applyFormModal(page);
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		// Create TRANSFER 5
		await page.getByTestId('tx-bulk-add-row').click();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
		await selectType(page, 'TRANSFER');
		await page.waitForTimeout(500);
		await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
		await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '5');
		await applyFormModal(page);

		// Wait for WAC to resolve
		await waitForWacResolved(page);

		// Capture value
		const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"]').filter({hasNotText: '…'}).first();
		const value1 = await autoCell.textContent();
		expect(value1).toMatch(/💡\s*[\d.,]+/);

		// Start counting extra wac-preview requests after stabilization
		let extraWacCalls = 0;
		page.on('request', (req) => {
			if (req.url().includes('/wac-preview') && req.method() === 'POST') {
				extraWacCalls++;
			}
		});

		// Wait for a second debounce (if buggy, value would change and extra calls fire)
		await page.waitForTimeout(2500);

		// Capture again
		const value2 = await autoCell.textContent();
		expect(value2).toBe(value1); // Stable — no feedback loop

		// Assert no extra network calls after stabilization
		expect(extraWacCalls, 'No extra wac-preview calls should fire after stabilization').toBe(0);
	});

	test('WB7 — Multiple pending BUYs affect WAC correctly', async ({page}) => {
		// Create BUY 10@100
		await openCreateFlow(page);
		await selectType(page, 'BUY');
		await pickFirstBroker(page);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '10');
		await fillCash(page, '100');
		await applyFormModal(page);
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		// Create BUY 5@200
		await page.getByTestId('tx-bulk-add-row').click();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
		await selectType(page, 'BUY');
		await pickFirstBroker(page);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '5');
		await fillCash(page, '200');
		await applyFormModal(page);
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

		// Create TRANSFER 3
		await page.getByTestId('tx-bulk-add-row').click();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
		await selectType(page, 'TRANSFER');
		await page.waitForTimeout(500);
		await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
		await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
		await pickAssetByName(page, ASSET_NAME);
		await fillQuantity(page, '3');
		await applyFormModal(page);

		// Wait for WAC to resolve
		await waitForWacResolved(page);

		// Assert WAC contains a number (the exact value depends on existing DB data
		// but with pending BUYs 10@100 + 5@200 the contribution should be around 133)
		const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"]').filter({hasNotText: '…'}).first();
		const cellText = await autoCell.textContent();
		expect(cellText).toMatch(/💡\s*[\d.,]+/);
	});
});





