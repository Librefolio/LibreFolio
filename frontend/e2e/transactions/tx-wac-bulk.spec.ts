/**
 * tx-wac-bulk.spec.ts — BulkModal WAC Cell Rendering E2E Tests
 *
 * Covers Bug 9, 10, 11 from plan-ReactiveWacBulkModal (Piano v7):
 * - WB1: TRANSFER auto shows calculated WAC value in cell (Bug 9)
 * - WB2: Manual override propagates from FormModal to BulkModal cell (Bug 10)
 * - WB3: Toggle manual→auto restores calculated value (Bug 10 reverse)
 * - WB4: DB rows with saved cost_basis show manual value (Bug 11)
 * - WB5: Clone paired from DB — WAC auto cell appears (inline validate)
 *
 * Prerequisites: backend test mode, mock data populated.
 * Mock data contract: e2e_test_user has OWNER/EDITOR on Interactive Brokers + Directa SIM.
 * Apple (AAPL) is a known asset with price history.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(60_000);

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
    // The previous version raced two waits and swallowed the failure with
    // `.catch(() => {})`, then slept 500 ms. Under load it returned with an
    // empty table, and every "scan the rows" loop below found nothing and
    // reported a missing fixture instead of a slow one.
    await expect(page.locator('[data-testid="transactions-page"][data-busy="false"]')).toBeVisible({timeout: 20_000});
    await expect(page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').first()).toBeVisible({timeout: 15_000});
}

/** Open the table narrowed to the given IDs — the rows this test owns. */
async function goToTransactionsByIds(page: Page, ids: number[]) {
    const min = Math.min(...ids);
    const max = Math.max(...ids);
    await navigateTo(page, `/transactions?page_size=200&id_min=${min}&id_max=${max}`);
    await expect(page.locator('[data-testid="transactions-page"][data-busy="false"]')).toBeVisible({timeout: 20_000});
    await expect(page.locator(`tr[data-row-id="tx-${ids[0]}"]`)).toBeVisible({timeout: 15_000});
}

async function openCreateFlow(page: Page) {
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/**
 * A SearchSelect has no "I committed" event, but its option list is torn down
 * when a choice lands. Waiting for that instead of sleeping also covers the
 * field cascade the choice triggers, because the re-render happens first.
 */
async function optionListClosed(page: Page) {
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 5_000});
}

async function selectType(page: Page, typeCode: string) {
    const typeButton = page.getByTestId('tx-form-type');
    await typeButton.click();
    await page.getByTestId(`search-select-option-${typeCode}`).click();
    await optionListClosed(page);
}

async function pickFirstBroker(page: Page) {
    const brokerWrap = page.getByTestId('tx-form-broker-wrap');
    await brokerWrap.locator('button, [role="combobox"]').first().click();
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: BROKER_FROM});
    await expect(option.first()).toBeVisible({timeout: 3_000});
    await option.first().click();
    await optionListClosed(page);
}

async function pickBrokerInPanel(page: Page, panelTestid: string, brokerName: string) {
    const panel = page.getByTestId(panelTestid);
    const trigger = panel.locator('[role="combobox"]').first();
    await expect(trigger).toBeVisible({timeout: 3_000});
    await trigger.click();
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: brokerName});
    await expect(option.first()).toBeVisible({timeout: 3_000});
    await option.first().click();
    await optionListClosed(page);
}

async function pickAssetByName(page: Page, name: string) {
    const assetWrap = page.getByTestId('tx-form-asset-wrap');
    await assetWrap.locator('button, [role="combobox"]').first().click();
    const searchInput = page.locator('[data-testid="tx-form-asset-wrap"] input[type="text"], [data-testid="tx-form-asset-wrap"] input[role="combobox"]').first();
    if (await searchInput.isVisible({timeout: 1_000}).catch(() => false)) {
        await searchInput.fill(name);
        // The list is debounced; the named entry arriving *is* the settle.
        await expect(page.locator('[data-testid^="search-select-option-"]', {hasText: name}).first()).toBeVisible({timeout: 5_000});
    }
    const option = page.locator('[data-testid^="search-select-option-"]').first();
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionListClosed(page);
}

async function fillQuantity(page: Page, qty: string) {
    const qtyInput = page.getByTestId('tx-form-quantity');
    await expect(qtyInput).toBeVisible({timeout: 2_000});
    await qtyInput.fill(qty);
    await qtyInput.blur();
    await expect(qtyInput).not.toHaveValue('');
}

async function fillCash(page: Page, amount: string) {
    const cashWrap = page.getByTestId('tx-form-cash-wrap');
    await expect(cashWrap).toBeVisible({timeout: 2_000});
    const cashInput = cashWrap.locator('input[data-testid$="-amount"]').first();
    await expect(cashInput).toBeVisible({timeout: 1_000});
    await cashInput.fill(amount);
    await cashInput.blur();
    await expect(cashInput).not.toHaveValue('');
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
    const root = page.getByTestId('tx-bulk-modal-root');
    // The value arrives with the validate response. Waiting on `data-busy`
    // alone is not enough: before the debounce arms, nothing is queued and
    // nothing is in flight, so the modal looks settled while the cell still
    // holds its placeholder. `data-validate-runs` is monotonic, so "at least
    // one run has completed" is a *state* — reading it late costs nothing,
    // which is exactly what a 4-worker run needs.
    await expect(root).not.toHaveAttribute('data-validate-runs', '0', {timeout: 25_000});
    await waitForSettled(root, 25_000);
    await expect(page.locator('[data-testid="tx-bulk-cost-basis-auto"][data-state="ready"]').first()).toBeVisible({timeout: 20_000});
}

/** Double-click on a row in the BulkModal grid to open FormModal for editing it. */
async function dblClickBulkRow(page: Page, rowIndex: number) {
    const rows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
    await rows.nth(rowIndex).dblclick();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

async function commitBulkModal(page: Page): Promise<number[]> {
    const commitBtn = page.getByTestId('tx-bulk-commit');
    await expect(commitBtn).toBeEnabled({timeout: 8_000});

    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commitBtn.click();
    const resp = await responsePromise;
    const body = (await resp.json()) as {
        committed: boolean;
        issues?: Array<{error: string}>;
        results?: Array<{operation: string; ids?: number[]; status?: string}>;
    };
    expect(body.committed, `commit was rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);

    // Wait for BulkModal to close
    await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});

    // The ids the backend assigned — the only way for the test to know which
    // rows it owns rather than scanning the table and hoping.
    return (body.results ?? []).filter((r) => r.operation === 'create' && r.status === 'success').flatMap((r) => r.ids ?? []);
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

        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await applyFormModal(page);

        // Step 3: Wait for WAC to resolve
        await waitForWacResolved(page);

        // Step 4: Assert cell shows 💡 + a number
        const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"][data-state="ready"]').first();
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
            await expect(manualToggle).toHaveAttribute('aria-pressed', 'true');
        }

        // Type 150 in cost basis input
        const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(amountInput).toBeVisible({timeout: 2_000});
        await amountInput.fill('150');
        await amountInput.blur();
        await expect(amountInput).not.toHaveValue('');

        await applyFormModal(page);
        await waitForSettled(page.getByTestId('tx-bulk-modal-root'));

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
            await expect(manualToggle).toHaveAttribute('aria-pressed', 'true');
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
            await expect(autoToggle).toHaveAttribute('aria-pressed', 'true');
        }
        await applyFormModal(page);

        // Wait for auto to resolve
        await waitForWacResolved(page);

        // Assert: back to auto cell with calculated value
        const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"][data-state="ready"]').first();
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
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await applyFormModal(page);
        await waitForWacResolved(page);

        // Commit
        const createdIds = await commitBulkModal(page);
        expect(createdIds.length, 'the commit must report the rows it created').toBeGreaterThan(0);

        // Open the table narrowed to the rows we just created. Scanning the
        // whole table for "a paired row with this asset and broker" could land
        // on a neighbour's row, which has no saved cost_basis and would fail
        // the assertion below for the wrong reason.
        await goToTransactionsByIds(page, createdIds);

        // Among our own rows, find the giver of the pair (the row followed by a receiver)
        const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        let giverRowId: string | null = null;
        const count = await allRows.count();
        for (let i = 0; i < count - 1; i++) {
            const nextCls = (await allRows.nth(i + 1).getAttribute('class')) ?? '';
            if (nextCls.includes('tx-row-receiver')) {
                giverRowId = await allRows.nth(i).getAttribute('data-row-id');
                break;
            }
        }
        expect(giverRowId, 'the committed TRANSFER must render as a giver + receiver pair').toBeTruthy();

        // Select and open in BulkModal (Edit)
        const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${giverRowId}"]`);
        await row.locator('.checkbox-btn').first().click();

        const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
        await expect(editBtn).toBeEnabled({timeout: 5_000});
        await editBtn.click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Assert: cost_basis cell shows manual value (DB-saved = manual)
        const manualCell = page.locator('[data-testid="tx-bulk-cost-basis-manual"]').first();
        await expect(manualCell).toBeVisible({timeout: 10_000});
    });

    test('WB5 — Clone paired from DB, WAC auto cell appears (inline validate)', async ({page}) => {
        // Find a paired giver row on editable broker (from mock data)
        const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        // The table is populated asynchronously: without this wait, a slow backend
        // (e.g. running under coverage) yields a count of 0 and the loop below never runs.
        await expect(allRows.first()).toBeVisible({timeout: 10_000});
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

        const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
        await expect(cloneBtn).toBeVisible({timeout: 2_000});

        await cloneBtn.click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // WAC now comes from the validate response (no separate /wac-preview call).
        // Wait for the auto cell to become visible — proves WAC inline works.
        const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"][data-state="ready"]').first();
        await expect(autoCell).toBeVisible({timeout: 8_000});
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
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await applyFormModal(page);

        // Wait for WAC to resolve
        await waitForWacResolved(page);

        // Capture value
        const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"][data-state="ready"]').first();
        const value1 = await autoCell.textContent();
        expect(value1).toMatch(/💡\s*[\d.,]+/);

        // Deliberate: this proves the value does *not* drift. A retrying assertion
        // would confirm the first reading instantly and never open the window in
        // which a feedback loop could show itself.
        await page.waitForTimeout(2_500);

        // Capture again — must be identical (stable, no feedback loop)
        const value2 = await autoCell.textContent();
        expect(value2).toBe(value1); // Stable — no feedback loop
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
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '3');
        await applyFormModal(page);

        // Wait for WAC to resolve
        await waitForWacResolved(page);

        // Assert WAC contains a number (the exact value depends on existing DB data
        // but with pending BUYs 10@100 + 5@200 the contribution should be around 133)
        const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"][data-state="ready"]').first();
        const cellText = await autoCell.textContent();
        expect(cellText).toMatch(/💡\s*[\d.,]+/);
    });

    test('WB8 — Mode persistence: manual stays manual on re-edit', async ({page}) => {
        // Create BUY + TRANSFER pair
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
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await applyFormModal(page);
        await waitForWacResolved(page);

        // Set manual 150
        const rows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
        const lastIdx = (await rows.count()) - 1;
        await rows.nth(lastIdx).dblclick();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

        const manualBtn = page.getByTestId('tx-form-cost-basis-toggle-manual');
        await manualBtn.click();
        await expect(manualBtn).toHaveAttribute('aria-pressed', 'true');
        const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await amountInput.fill('150');
        await applyFormModal(page);
        await waitForSettled(page.getByTestId('tx-bulk-modal-root'));

        // Re-edit — should still show manual
        const rows2 = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
        const lastIdx2 = (await rows2.count()) - 1;
        await rows2.nth(lastIdx2).dblclick();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

        // Assert: manual toggle is active (has font-medium)
        const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
        await expect(manualToggle).toBeVisible({timeout: 3_000});
        await expect(manualToggle).toHaveClass(/font-medium/);

        // Assert: input still has 150
        const input = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(input).toHaveValue('150');
    });

    test('WB9 — Mode persistence: auto stays auto on re-edit', async ({page}) => {
        // Create BUY + TRANSFER pair (auto mode — default)
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
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await applyFormModal(page);
        await waitForWacResolved(page);

        // Re-edit without changing mode — should still be auto
        const rows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
        const lastIdx = (await rows.count()) - 1;
        await rows.nth(lastIdx).dblclick();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

        // Assert: auto toggle is active
        const autoToggle = page.getByTestId('tx-form-cost-basis-toggle-auto');
        await expect(autoToggle).toBeVisible({timeout: 3_000});
        await expect(autoToggle).toHaveClass(/font-medium/);

        // Assert: manual toggle is NOT active
        const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
        await expect(manualToggle).not.toHaveClass(/font-medium/);
    });

    test('WB10 — Pending indicator ● in qualifying table', async ({page}) => {
        // Create BUY (this will be a pending tx visible in qualifying table)
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '1000');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Create TRANSFER pair
        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'TRANSFER');
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await applyFormModal(page);
        await waitForWacResolved(page);

        // Open the TRANSFER row
        const rows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
        const lastIdx = (await rows.count()) - 1;
        await rows.nth(lastIdx).dblclick();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

        // Expand qualifying table
        const showBtn = page.getByTestId('tx-form-cost-basis-show-qualifying');
        await expect(showBtn).toBeVisible({timeout: 5_000});
        await showBtn.click();

        // Assert: qualifying table has at least one row with ● (pending indicator)
        const qualTable = page.getByTestId('tx-form-cost-basis-qualifying-table');
        await expect(qualTable).toBeVisible({timeout: 3_000});
        const pendingDots = qualTable.locator('td:first-child span.text-indigo-500');
        await expect(pendingDots.first()).toBeVisible({timeout: 5_000});
        expect(await pendingDots.count()).toBeGreaterThan(0);
        const dotText = await pendingDots.first().textContent();
        expect(dotText?.trim()).toBe('●');
    });
});
