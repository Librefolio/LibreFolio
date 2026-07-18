/**
 * E2E Tests for the Cost Basis Override "Total/Per unit" display toggle.
 *
 * Background: `cost_basis_override` is always PER-UNIT at rest (DB, API,
 * FIFO Lot Engine, WAC engine, Portfolio Engine all multiply by quantity
 * wherever a total is needed — see wac_utils.py, lots_analysis_service.py,
 * portfolio_engine.py). This toggle only changes how the amount is
 * displayed/typed in WacPreviewSection — the underlying per-unit contract
 * never changes. Default is "Per unit" (legacy/unchanged behavior); "Total"
 * is opt-in and persisted per-user in localStorage.
 *
 * The critical correctness property tested here: typing a TOTAL while the
 * toggle is on "Total" must persist as total/quantity (per-unit) in the
 * actual commit payload — never the raw typed number.
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

interface CommitPayload {
    creates?: Record<string, unknown>[];
    updates?: Record<string, unknown>[];
    deletes?: unknown[];
    [key: string]: unknown;
}

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await Promise.race([page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000}), page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 10_000})]).catch(() => {});
    await page.waitForTimeout(500);
}

async function openAdjustmentWithCostBasis(page: Page, quantity: string) {
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

    await page.getByTestId('tx-form-type').click();
    await page.waitForTimeout(300);
    await page.getByTestId('search-select-option-ADJUSTMENT').click();
    await page.waitForTimeout(300);

    const brokerWrap = page.getByTestId('tx-form-broker-wrap');
    await brokerWrap.locator('button, [role="combobox"]').first().click();
    await page.waitForTimeout(300);
    await page.locator('[data-testid^="search-select-option-"]').first().click();
    await page.waitForTimeout(300);

    const assetWrap = page.getByTestId('tx-form-asset-wrap');
    await assetWrap.locator('button, [role="combobox"]').first().click();
    await page.waitForTimeout(300);
    await page.locator('[data-testid^="search-select-option-"]').first().click();
    await page.waitForTimeout(300);

    const qtyInput = page.getByTestId('tx-form-quantity');
    await qtyInput.fill(quantity);
    await page.waitForTimeout(400);

    await expect(page.getByTestId('tx-form-cost-basis-inline')).toBeVisible({timeout: 3_000});
}

async function applyFormModal(page: Page) {
    const saveBtn = page.getByTestId('tx-form-save');
    await expect(saveBtn).toBeEnabled({timeout: 5_000});
    await saveBtn.click();
    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 10_000});
}

async function commitBulkModal(page: Page): Promise<{payload: CommitPayload}> {
    const commitBtn = page.getByTestId('tx-bulk-commit');
    await expect(commitBtn).toBeEnabled({timeout: 8_000});
    const commitPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    await commitBtn.click();
    const req = await commitPromise;
    const payload = req.postDataJSON() as CommitPayload;
    await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});
    return {payload};
}

test.describe('Cost Basis Override — Total/Per unit toggle', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('toggle is visible with "Per unit" selected by default', async ({page}) => {
        await openAdjustmentWithCostBasis(page, '5');

        await expect(page.getByTestId('tx-form-cost-basis-unit-toggle')).toBeVisible();
        const unitBtn = page.getByTestId('tx-form-cost-basis-unit-toggle-unit');
        const totalBtn = page.getByTestId('tx-form-cost-basis-unit-toggle-total');
        await expect(unitBtn).toBeVisible();
        await expect(totalBtn).toBeVisible();
        // Default state: "Per unit" visually active (bg-gray-200 class applied by the component)
        await expect(unitBtn).toHaveClass(/bg-gray-200/);
    });

    test('manual entry round-trips correctly between Total and Per unit for a qty=5 lot', async ({page}) => {
        await openAdjustmentWithCostBasis(page, '5');
        await page.getByTestId('tx-form-cost-basis-toggle-manual').click();

        const cbInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await cbInput.fill('100');
        await page.waitForTimeout(200);

        // Switch to Total — per-unit 100 x qty 5 = 500
        await page.getByTestId('tx-form-cost-basis-unit-toggle-total').click();
        await page.waitForTimeout(200);
        await expect(cbInput).toHaveValue('500');

        // Type a new TOTAL (600) then switch back to Per unit — expect 120 (600 / 5)
        await cbInput.fill('600');
        await page.waitForTimeout(200);
        await page.getByTestId('tx-form-cost-basis-unit-toggle-unit').click();
        await page.waitForTimeout(200);
        await expect(cbInput).toHaveValue('120');
    });

    test('typing a Total for a qty=4 ADJUSTMENT persists the per-unit value in the commit payload', async ({page}) => {
        await openAdjustmentWithCostBasis(page, '4');
        await page.getByTestId('tx-form-cost-basis-toggle-manual').click();
        await page.getByTestId('tx-form-cost-basis-unit-toggle-total').click();
        await page.waitForTimeout(200);

        // Total cost basis for the whole 4-unit adjustment: 200 → per-unit must be 50.
        const cbInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await cbInput.fill('200');
        await page.waitForTimeout(200);
        await expect(cbInput).toHaveValue('200');

        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        const {payload} = await commitBulkModal(page);
        const creates = payload.creates as Record<string, unknown>[];
        expect(creates?.length).toBeGreaterThanOrEqual(1);

        const withCostBasis = creates.find((c) => c.cost_basis_override != null && typeof c.cost_basis_override === 'object');
        expect(withCostBasis, 'A create item should carry a cost_basis_override object').toBeTruthy();
        const cbo = withCostBasis?.cost_basis_override as {code: string; amount: string};
        // Persisted amount must be per-unit (200 / 4 = 50), never the raw typed total (200).
        expect(Number(cbo.amount)).toBeCloseTo(50, 5);
    });

    test('toggle choice persists across closing and reopening the form (localStorage)', async ({page}) => {
        await openAdjustmentWithCostBasis(page, '3');
        await page.getByTestId('tx-form-cost-basis-unit-toggle-total').click();
        await page.waitForTimeout(200);
        await expect(page.getByTestId('tx-form-cost-basis-unit-toggle-total')).toHaveClass(/bg-libre-green/);

        // Cancel the form (discards this draft) — a "Discard changes?" confirm appears
        // since fields were filled; confirm it, then close the underlying BulkModal too,
        // so the next tx-add-button click opens a completely fresh FormModal.
        await page.getByTestId('tx-form-cancel').click();
        const discardConfirm = page.getByTestId('confirm-modal-confirm');
        if (await discardConfirm.isVisible({timeout: 1_500}).catch(() => false)) {
            await discardConfirm.click();
        }
        await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 5_000});
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
        await page.getByTestId('tx-bulk-close').click();
        // The BulkModal itself may also ask to discard its (empty) pending row.
        const confirmDiscard = page.getByTestId('confirm-modal-confirm');
        if (await confirmDiscard.isVisible({timeout: 1_500}).catch(() => false)) {
            await confirmDiscard.click();
        }
        await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 5_000});

        await openAdjustmentWithCostBasis(page, '3');
        await expect(page.getByTestId('tx-form-cost-basis-unit-toggle-total')).toHaveClass(/bg-libre-green/);
    });
});
