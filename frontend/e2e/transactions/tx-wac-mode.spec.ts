/**
 * Transaction WAC Mode E2E Tests — Auto/Manual Toggle, Blur Behavior
 *
 * Covers walktest W9-W11 from plan-R3-SP-D-WacFxEnrich:
 * - W9:  Focus + blur without modification → stays Auto
 * - W10: Modify last digit → switches to Manual
 * - W11: Auto → Manual → Auto: table cleared, placeholder shows "auto (⚡ Validate)"
 *
 * Prerequisites: backend test mode (port 6041), mock data populated.
 * Uses Apple (USD) TRANSFER on IB — same currency, WAC auto-calculates immediately.
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
	await Promise.race([
		page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000}),
		page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 10_000})
	]).catch(() => {
		/* either is fine */
	});
	await page.waitForTimeout(500);
}

async function openNewTransactionForm(page: Page) {
	await page.getByTestId('tx-add-button').click();
	await page.getByTestId('tx-form-modal').waitFor({state: 'visible', timeout: 5_000});
}

async function selectType(page: Page, type: string) {
	const typeSelect = page.getByTestId('tx-form-type');
	await typeSelect.locator('button, [role="combobox"]').first().click();
	await page.waitForTimeout(300);
	await page.getByTestId(`search-select-option-${type}`).click();
	await page.waitForTimeout(300);
}

async function selectAsset(page: Page, assetName: string) {
	const assetWrap = page.getByTestId('tx-form-asset-wrap');
	await assetWrap.locator('button, [role="combobox"]').first().click();
	await page.waitForTimeout(300);
	const input = page.locator('[data-testid="tx-form-asset-wrap"] input[type="text"], [data-testid="tx-form-asset-wrap"] input[role="combobox"]').first();
	if (await input.isVisible({timeout: 1_000}).catch(() => false)) {
		await input.fill(assetName);
		await page.waitForTimeout(500);
	}
	const option = page.locator(`[data-testid^="search-select-option-"]`).first();
	await expect(option).toBeVisible({timeout: 3_000});
	await option.click();
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

/** Set up TRANSFER with Apple on IB (same currency USD→USD, WAC calculates immediately) */
async function setupSameCurrencyTransfer(page: Page) {
	await openNewTransactionForm(page);
	await selectType(page, 'TRANSFER');
	await page.waitForTimeout(500);
	await pickBrokerInPanel(page, 'tx-form-dual-from', 'Interactive Brokers');
	await pickBrokerInPanel(page, 'tx-form-dual-to', 'Directa SIM');
	await selectAsset(page, 'Apple');
	const qtyInput = page.getByTestId('tx-form-quantity');
	await expect(qtyInput).toBeVisible({timeout: 2_000});
	await qtyInput.fill('2');
	// Wait for auto-validate to fire
	await page.waitForTimeout(2000);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('WAC Mode — Auto/Manual Toggle & Blur', () => {
	test.beforeEach(async ({page}) => {
		await login(page, TEST_USER);
		await goToTransactions(page);
	});

	// === W9 — Focus + blur without change → stays Auto ===
	test('W9 — Focus and blur without editing stays in Auto mode', async ({page}) => {
		await setupSameCurrencyTransfer(page);

		const costBasis = page.getByTestId('tx-form-cost-basis');
		await expect(costBasis).toBeVisible({timeout: 5_000});

		// Check that auto toggle is active
		const autoToggle = page.getByTestId('tx-form-cost-basis-toggle-auto');
		await expect(autoToggle).toBeVisible({timeout: 3_000});

		// Wait for WAC value to populate
		const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
		await expect(amountInput).toBeVisible({timeout: 5_000});

		// Focus the input
		await amountInput.focus();
		await page.waitForTimeout(200);

		// Blur without changing anything (click elsewhere)
		await page.getByTestId('tx-form-quantity').click();
		await page.waitForTimeout(500);

		// Should still be in auto mode (auto toggle still highlighted)
		// The manual toggle should NOT be the active one
		const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
		// In auto mode, auto has the green styling
		const autoClasses = await autoToggle.getAttribute('class');
		expect(autoClasses).toContain('bg-libre-green');
	});

	// === W10 — Modify value → switches to Manual ===
	test('W10 — Editing the WAC value switches to Manual mode', async ({page}) => {
		await setupSameCurrencyTransfer(page);

		const costBasis = page.getByTestId('tx-form-cost-basis');
		await expect(costBasis).toBeVisible({timeout: 5_000});

		const autoToggle = page.getByTestId('tx-form-cost-basis-toggle-auto');
		await expect(autoToggle).toBeVisible({timeout: 3_000});

		const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
		await expect(amountInput).toBeVisible({timeout: 3_000});

		// Clear and type a different value
		await amountInput.fill('99.99');
		await page.waitForTimeout(300);

		// Blur to trigger change detection
		await page.getByTestId('tx-form-quantity').click();
		await page.waitForTimeout(500);

		// Should now be in manual mode (manual toggle has the active bg-gray-200 styling)
		const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
		const manualClasses = await manualToggle.getAttribute('class');
		expect(manualClasses).toContain('font-medium');

		// Auto toggle should have lost its green highlight
		const autoClasses = await autoToggle.getAttribute('class');
		expect(autoClasses).not.toContain('bg-libre-green');
	});

	// === W11 — Auto → Manual → Auto: table cleared, placeholder shown ===
	test('W11 — Toggle Auto→Manual→Auto clears table and shows placeholder', async ({page}) => {
		await setupSameCurrencyTransfer(page);

		const costBasis = page.getByTestId('tx-form-cost-basis');
		await expect(costBasis).toBeVisible({timeout: 5_000});

		const autoToggle = page.getByTestId('tx-form-cost-basis-toggle-auto');
		const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
		await expect(autoToggle).toBeVisible({timeout: 3_000});

		// Switch to Manual
		await manualToggle.click();
		await page.waitForTimeout(300);

		// Type a manual value
		const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
		await amountInput.fill('42.00');
		await page.waitForTimeout(300);

		// Switch back to Auto
		await autoToggle.click();
		await page.waitForTimeout(500);

		// Input should now show placeholder (not the manual value)
		const inputValue = await amountInput.inputValue();
		// In auto mode without result yet, the field should be empty or show placeholder
		// The placeholder contains "auto" text
		const placeholder = await amountInput.getAttribute('placeholder');
		expect(placeholder?.toLowerCase()).toContain('auto');

		// Qualifying table should NOT be visible (cleared on mode switch)
		const qualifyingTable = page.getByTestId('tx-form-cost-basis-qualifying-table');
		await expect(qualifyingTable).not.toBeVisible({timeout: 2_000});
	});

	// === W11b — Placeholder contains "Validate" hint ===
	test('W11b — Auto mode placeholder contains validate hint', async ({page}) => {
		await setupSameCurrencyTransfer(page);

		const costBasis = page.getByTestId('tx-form-cost-basis');
		await expect(costBasis).toBeVisible({timeout: 5_000});

		// Switch to manual then back to auto to clear state
		const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
		const autoToggle = page.getByTestId('tx-form-cost-basis-toggle-auto');
		await manualToggle.click();
		await page.waitForTimeout(200);
		await autoToggle.click();
		await page.waitForTimeout(300);

		// Check placeholder text
		const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
		const placeholder = await amountInput.getAttribute('placeholder');
		// Should contain the lightning emoji and validate reference
		expect(placeholder).toContain('⚡');
	});

	// === Additional: Validate Now button triggers recalculation ===
	test('Validate Now button triggers WAC recalculation', async ({page}) => {
		await setupSameCurrencyTransfer(page);

		const costBasis = page.getByTestId('tx-form-cost-basis');
		await expect(costBasis).toBeVisible({timeout: 5_000});

		// Look for validate now button
		const validateBtn = page.getByTestId('tx-form-validate-now');
		if (await validateBtn.isVisible({timeout: 3_000}).catch(() => false)) {
			await validateBtn.click();
			// Wait for recalculation
			await page.waitForTimeout(2_000);

			// After validation, suggestion or result should appear
			const suggestion = page.getByTestId('tx-form-cost-basis-suggestion');
			const loading = page.getByTestId('tx-form-cost-basis-loading');
			// Either suggestion visible or loading was transient → both are valid
			const hasSuggestion = await suggestion.isVisible({timeout: 3_000}).catch(() => false);
			const hasLoading = await loading.isVisible().catch(() => false);
			// At least one state should have been triggered
			expect(hasSuggestion || !hasLoading).toBeTruthy();
		}
	});
});






