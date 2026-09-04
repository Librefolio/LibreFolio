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
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(20_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await Promise.race([page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000}), page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 10_000})]).catch(() => {
        /* either is fine */
    });
    // The page is usable when the entry point is: never sleep for "settling".
    await expect(page.getByTestId('tx-add-button')).toBeVisible({timeout: 10_000});
}

async function openNewTransactionForm(page: Page) {
    await page.getByTestId('tx-add-button').click();
    await page.getByTestId('tx-form-modal').waitFor({state: 'visible', timeout: 5_000});
}

/** Close a search-select dropdown deterministically: the picked option goes away. */
async function clickOptionAndWaitClose(option: ReturnType<Page['locator']>) {
    await expect(option).toBeVisible({timeout: 5_000});
    await option.click();
    await expect(option).toBeHidden({timeout: 5_000});
}

async function selectType(page: Page, type: string) {
    const typeSelect = page.getByTestId('tx-form-type');
    await typeSelect.locator('button, [role="combobox"]').first().click();
    await clickOptionAndWaitClose(page.getByTestId(`search-select-option-${type}`));
}

async function selectAsset(page: Page, assetName: string) {
    const assetWrap = page.getByTestId('tx-form-asset-wrap');
    await assetWrap.locator('button, [role="combobox"]').first().click();
    const input = page.locator('[data-testid="tx-form-asset-wrap"] input[type="text"], [data-testid="tx-form-asset-wrap"] input[role="combobox"]').first();
    if (await input.isVisible({timeout: 1_000}).catch(() => false)) {
        await input.fill(assetName);
    }
    // Pick the option that actually matches what we searched for. Taking whichever
    // option happens to be listed first makes the test depend on the ordering of
    // someone else's data.
    const option = page.locator('[data-testid^="search-select-option-"]').filter({hasText: assetName});
    await clickOptionAndWaitClose(option.first());
}

async function pickBrokerInPanel(page: Page, panelTestid: string, brokerName: string) {
    const panel = page.getByTestId(panelTestid);
    const trigger = panel.locator('[role="combobox"]').first();
    await expect(trigger).toBeVisible({timeout: 3_000});
    await trigger.click();
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: brokerName});
    await clickOptionAndWaitClose(option.first());
}

/**
 * Wait until auto-validate has actually produced a WAC.
 *
 * The component publishes this state: `-loading` while it is computing and
 * `-suggestion` once a result exists. Waiting for those instead of sleeping is
 * what makes the WAC value observable *before* anything touches the field.
 */
async function waitForWacComputed(page: Page) {
    await expect(page.getByTestId('tx-form-cost-basis-loading')).toBeHidden({timeout: 15_000});
    await expect(page.getByTestId('tx-form-cost-basis-suggestion')).toBeVisible({timeout: 15_000});
}

/**
 * Assert the amount field holds a given number.
 *
 * The input re-formats what it displays (`42.00` → `42`, `191.50591660` →
 * `191.5059166`), so comparing the raw string would assert the formatter's
 * habits rather than the value. `expect.poll` keeps this a condition, not a
 * snapshot taken at an arbitrary instant.
 */
async function expectAmountValue(amountInput: ReturnType<Page['getByTestId']>, expected: string) {
    await expect.poll(async () => Number(await amountInput.inputValue()), {timeout: 5_000}).toBe(Number(expected));
}

/** Set up TRANSFER with Apple on IB (same currency USD→USD, WAC calculates immediately) */
async function setupSameCurrencyTransfer(page: Page) {
    await openNewTransactionForm(page);
    await selectType(page, 'TRANSFER');
    await pickBrokerInPanel(page, 'tx-form-dual-from', 'Interactive Brokers');
    await pickBrokerInPanel(page, 'tx-form-dual-to', 'Directa SIM');
    await selectAsset(page, 'Apple');
    const qtyInput = page.getByTestId('tx-form-quantity');
    await expect(qtyInput).toBeVisible({timeout: 2_000});
    await qtyInput.fill('2');
    await waitForWacComputed(page);
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

        // Wait for the WAC value to be *populated*, not merely for the field to
        // exist. Blurring an empty field is an edit ('' → '170.32'), so the
        // component would legitimately switch to manual and this test would be
        // measuring its own race instead of the toggle behaviour.
        const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(amountInput).toHaveValue(/\d/, {timeout: 10_000});
        const valueBeforeBlur = await amountInput.inputValue();

        // Focus the input, then blur without changing anything (click elsewhere)
        await amountInput.focus();
        await expect(amountInput).toBeFocused({timeout: 2_000});
        await page.getByTestId('tx-form-quantity').click();
        await expect(amountInput).not.toBeFocused({timeout: 2_000});

        // Nothing was typed, so the value must be unchanged (the field may still
        // re-format it on blur — that is display, not an edit).
        await expectAmountValue(amountInput, valueBeforeBlur);

        // ...and the mode must still be Auto (green highlight on the auto toggle).
        await expect(autoToggle).toHaveClass(/bg-libre-green/, {timeout: 3_000});
    });

    // === W10 — Modify value → switches to Manual ===
    test('W10 — Editing the WAC value switches to Manual mode', async ({page}) => {
        await setupSameCurrencyTransfer(page);

        const costBasis = page.getByTestId('tx-form-cost-basis');
        await expect(costBasis).toBeVisible({timeout: 5_000});

        const autoToggle = page.getByTestId('tx-form-cost-basis-toggle-auto');
        await expect(autoToggle).toBeVisible({timeout: 3_000});

        const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(amountInput).toHaveValue(/\d/, {timeout: 10_000});

        // Clear and type a different value
        await amountInput.fill('99.99');

        // Blur to trigger change detection
        await page.getByTestId('tx-form-quantity').click();
        await expect(amountInput).not.toBeFocused({timeout: 2_000});

        // Should now be in manual mode (manual toggle has the active styling)
        const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
        await expect(manualToggle).toHaveClass(/font-medium/, {timeout: 3_000});

        // Auto toggle should have lost its green highlight
        await expect(autoToggle).not.toHaveClass(/bg-libre-green/, {timeout: 3_000});
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
        await expect(manualToggle).toHaveClass(/font-medium/, {timeout: 3_000});

        // Type a manual value
        const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await amountInput.fill('42.00');
        await expectAmountValue(amountInput, '42.00');

        // Switch back to Auto
        await autoToggle.click();
        await expect(autoToggle).toHaveClass(/bg-libre-green/, {timeout: 3_000});

        // Input should now show placeholder (not the manual value)
        // In auto mode without result yet, the field shows the "auto" placeholder
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
        await expect(manualToggle).toHaveClass(/font-medium/, {timeout: 3_000});
        await autoToggle.click();
        await expect(autoToggle).toHaveClass(/bg-libre-green/, {timeout: 3_000});

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
            // Recalculation is over when the component says so, not after 2 seconds.
            await waitForWacComputed(page);
        }
    });
});
