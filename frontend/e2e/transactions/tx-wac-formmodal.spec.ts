/**
 * tx-wac-formmodal.spec.ts — FormModal WAC Payload E2E Tests (FM1-FM9)
 *
 * Tests WAC cost_basis_mode propagation from FormModal to validate/commit payload.
 * Covers Bug F2 partner rows + Bug 9-10-11 resolution validation.
 *
 * FM1: BUY via FormModal → validate → cost_basis_mode ABSENT
 * FM2: SELL via FormModal → validate → cost_basis_mode ABSENT
 * FM3: TRANSFER pair via FormModal → validate → receiver has cost_basis_mode: "auto"
 * FM4: ADJUSTMENT+ via FormModal → validate → cost_basis_mode: "auto"
 * FM5: ADJUSTMENT- via FormModal → validate → cost_basis_mode ABSENT
 * FM6: DB rows with saved cost_basis_override → BulkModal cell shows manual value
 * FM7: Toggle Auto→Manual on TRANSFER receiver → payload has cost_basis_override, no mode
 * FM8: DEPOSIT via FormModal → validate → no cost_basis_mode
 * FM9: BUY via FormModal → validate OK → no costBasisModeIncompatible issue
 *
 * Prerequisites: backend test mode, mock data populated.
 * Mock data contract: e2e_test_user has OWNER/EDITOR on Interactive Brokers + Directa SIM.
 * Apple (AAPL) is a known asset with price history and existing BUY transactions.
 */
import {expect, test, type Page, type Request} from '@playwright/test';
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
    await Promise.race([page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000}), page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 10_000})]).catch(() => {});
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
    await page.locator('[data-testid="tx-bulk-cost-basis-auto"]').filter({hasNotText: '…'}).first().waitFor({state: 'visible', timeout: 8_000});
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

    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commitBtn.click();
    const resp = await responsePromise;
    const body = await resp.json();
    expect(body.committed).toBe(true);

    await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});
}

/** Intercept the next validate request and return the parsed JSON body. */
async function captureValidatePayload(page: Page, action: () => Promise<void>): Promise<Record<string, unknown>> {
    const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/validate') && req.method() === 'POST', {timeout: 10_000});
    await action();
    const req = await requestPromise;
    return req.postDataJSON();
}

/** Intercept the next validate response and return the parsed JSON body. */
async function captureValidateResponse(page: Page, action: () => Promise<void>): Promise<Record<string, unknown>> {
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/validate') && resp.request().method() === 'POST', {timeout: 10_000});
    await action();
    const resp = await responsePromise;
    return resp.json();
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('FormModal WAC Payload Tests', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('FM1 — BUY via FormModal → cost_basis_mode ABSENT', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '500');

        // Intercept validate payload when saving FormModal
        const payload = await captureValidatePayload(page, async () => {
            await applyFormModal(page);
        });

        // BUY does not send cost_basis_mode
        const creates = (payload.creates ?? []) as Record<string, unknown>[];
        expect(creates.length).toBeGreaterThan(0);
        for (const item of creates) {
            expect(item).not.toHaveProperty('cost_basis_mode');
        }
    });

    test('FM2 — SELL via FormModal → cost_basis_mode ABSENT', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'SELL');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '1');
        await fillCash(page, '100');

        const payload = await captureValidatePayload(page, async () => {
            await applyFormModal(page);
        });

        const creates = (payload.creates ?? []) as Record<string, unknown>[];
        expect(creates.length).toBeGreaterThan(0);
        for (const item of creates) {
            expect(item).not.toHaveProperty('cost_basis_mode');
        }
    });

    test('FM3 — TRANSFER pair via FormModal → receiver has cost_basis_mode: "auto"', async ({page}) => {
        // First create a BUY so WAC pool exists
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '1000');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Now add a TRANSFER row; intercept the validate that fires after apply
        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'TRANSFER');
        await page.waitForTimeout(500);
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');

        const payload = await captureValidatePayload(page, async () => {
            await applyFormModal(page);
        });

        // Payload should contain creates for the TRANSFER pair
        const creates = (payload.creates ?? []) as Record<string, unknown>[];
        // Find the receiver item (positive quantity)
        const receiver = creates.find((c) => Number(c.quantity) > 0 && c.type === 'TRANSFER');
        expect(receiver, 'Must find TRANSFER receiver in creates').toBeTruthy();
        expect(receiver!.cost_basis_mode).toBe('auto-detail');

        // Wait for WAC to resolve in BulkModal
        await waitForWacResolved(page);

        // WAC auto cell should show a calculated value
        const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"]').filter({hasNotText: '…'}).first();
        const cellText = await autoCell.textContent();
        expect(cellText).toMatch(/💡\s*[\d.,]+/);
    });

    test('FM4 — ADJUSTMENT+ via FormModal → cost_basis_mode: "auto"', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'ADJUSTMENT');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');

        // ADJUSTMENT shows the cost basis inline section — default mode is auto
        const costBasisSection = page.getByTestId('tx-form-cost-basis-inline');
        await expect(costBasisSection).toBeVisible({timeout: 3_000});

        const payload = await captureValidatePayload(page, async () => {
            await applyFormModal(page);
        });

        const creates = (payload.creates ?? []) as Record<string, unknown>[];
        expect(creates.length).toBeGreaterThan(0);
        // ADJUSTMENT+ (positive qty) with auto mode should send cost_basis_mode
        const adjItem = creates.find((c) => c.type === 'ADJUSTMENT');
        expect(adjItem, 'Must find ADJUSTMENT in creates').toBeTruthy();
        expect(adjItem!.cost_basis_mode).toBe('auto-detail');
    });

    test('FM5 — ADJUSTMENT- via FormModal → cost_basis_mode ABSENT', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'ADJUSTMENT');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '-3');

        const payload = await captureValidatePayload(page, async () => {
            await applyFormModal(page);
        });

        const creates = (payload.creates ?? []) as Record<string, unknown>[];
        expect(creates.length).toBeGreaterThan(0);
        // ADJUSTMENT- (negative qty) should NOT send cost_basis_mode
        const adjItem = creates.find((c) => c.type === 'ADJUSTMENT');
        expect(adjItem, 'Must find ADJUSTMENT in creates').toBeTruthy();
        expect(adjItem).not.toHaveProperty('cost_basis_mode');
    });

    test('FM6 — DB rows with saved cost_basis show manual value in BulkModal', async ({page}) => {
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

        // Commit to DB
        await commitBulkModal(page);

        // Reload and find the committed paired row (newest rows at top, search by ASSET_NAME)
        await goToTransactions(page);
        const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        const count = await allRows.count();
        let giverRowId: string | null = null;

        for (let i = 0; i < count - 1; i++) {
            const nextCls = (await allRows.nth(i + 1).getAttribute('class')) ?? '';
            if (nextCls.includes('tx-row-receiver')) {
                const text = (await allRows.nth(i).textContent()) ?? '';
                if (text.includes(ASSET_NAME) && (text.includes(BROKER_FROM) || text.includes(BROKER_TO))) {
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

        // DB-saved cost_basis → cell should show manual value (not "—")
        const manualCell = page.locator('[data-testid="tx-bulk-cost-basis-manual"]').first();
        await expect(manualCell).toBeVisible({timeout: 5_000});
    });

    test('FM7 — Toggle Auto→Manual on TRANSFER receiver propagates override', async ({page}) => {
        // Create BUY + TRANSFER
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

        // Open the TRANSFER row in FormModal for editing
        const rows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
        const lastIdx = (await rows.count()) - 1;
        await rows.nth(lastIdx).dblclick();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

        // Toggle to manual mode
        const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
        if (await manualToggle.isVisible({timeout: 2_000}).catch(() => false)) {
            await manualToggle.click();
            await page.waitForTimeout(300);
        }

        // Fill manual cost basis amount
        const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(amountInput).toBeVisible({timeout: 2_000});
        await amountInput.fill('250');
        await page.waitForTimeout(200);

        // Save and intercept validate payload
        const payload = await captureValidatePayload(page, async () => {
            await applyFormModal(page);
        });

        // The receiver item should have cost_basis_override and NOT cost_basis_mode: "auto"
        const creates = (payload.creates ?? []) as Record<string, unknown>[];
        const receiver = creates.find((c) => Number(c.quantity) > 0 && c.type === 'TRANSFER');
        expect(receiver, 'Must find TRANSFER receiver in creates').toBeTruthy();
        expect(receiver).not.toHaveProperty('cost_basis_mode');
        // cost_basis_override should contain 250
        const cbo = receiver!.cost_basis_override as {amount?: string} | undefined;
        expect(cbo, 'cost_basis_override should be set').toBeTruthy();
        expect(cbo!.amount).toContain('250');

        // BulkModal cell should now show manual value
        await page.waitForTimeout(1000);
        const manualCell = page.locator('[data-testid="tx-bulk-cost-basis-manual"]').first();
        await expect(manualCell).toBeVisible({timeout: 5_000});
        const text = await manualCell.textContent();
        expect(text).toContain('250');
    });

    test('FM8 — DEPOSIT via FormModal → no cost_basis_mode', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'DEPOSIT');
        await pickFirstBroker(page);
        await fillCash(page, '1000');

        const payload = await captureValidatePayload(page, async () => {
            await applyFormModal(page);
        });

        const creates = (payload.creates ?? []) as Record<string, unknown>[];
        expect(creates.length).toBeGreaterThan(0);
        for (const item of creates) {
            expect(item).not.toHaveProperty('cost_basis_mode');
        }
    });

    test('FM9 — BUY via FormModal → validate OK, no costBasisModeIncompatible issue', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await fillCash(page, '250');

        const body = await captureValidateResponse(page, async () => {
            await applyFormModal(page);
        });

        // Response should not contain costBasisModeIncompatible issues
        const issues = (body as any).issues ?? [];
        for (const issue of issues) {
            expect(issue.code).not.toBe('costBasisModeIncompatible');
        }
    });

    test('FM10 — ADJUSTMENT mode persist: manual stays manual on re-edit', async ({page}) => {
        // Step 1: Create ADJUSTMENT+ with auto mode (default)
        await openCreateFlow(page);
        await selectType(page, 'ADJUSTMENT');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Wait for auto-validate to complete
        await page.waitForTimeout(2000);

        // Step 2: Re-edit and switch to manual with value 50
        const rows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
        const lastIdx = (await rows.count()) - 1;
        await rows.nth(lastIdx).dblclick();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

        const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
        await expect(manualToggle).toBeVisible({timeout: 3_000});
        await manualToggle.click();
        await page.waitForTimeout(300);

        const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(amountInput).toBeVisible({timeout: 2_000});
        await amountInput.fill('50');
        await applyFormModal(page);
        await page.waitForTimeout(1000);

        // Step 3: Re-edit again — should show manual mode with value 50
        const rows2 = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
        const lastIdx2 = (await rows2.count()) - 1;
        await rows2.nth(lastIdx2).dblclick();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

        // Assert: manual toggle active
        const manualToggle2 = page.getByTestId('tx-form-cost-basis-toggle-manual');
        await expect(manualToggle2).toBeVisible({timeout: 3_000});
        await expect(manualToggle2).toHaveClass(/font-medium/);

        // Assert: input still has 50
        const input = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(input).toHaveValue('50');
    });
});
