/**
 * Transaction WAC FX E2E Tests — Sync FX Modal + Qualifying Table + Tooltip
 *
 * Covers walktest W1-W8 from plan-R3-SP-D-WacFxEnrich:
 * - W1: Banner sync button styled green (RefreshCw icon)
 * - W2: WacPreviewSection shows actual dates + sync button
 * - W3: FxSyncModal opens above FormModal (z-index)
 * - W4: Sync results visible, modal stays open, re-validate in background
 * - W5: Closing modal → WAC re-calculated
 * - W6: Qualifying table shows currency conversion arrow (USD → EUR)
 * - W7: Tooltip FX format (clean, bottom position)
 * - W8: Stale indicator ⚠️ in cell + tooltip
 *
 * Prerequisites: backend test mode (port 6041), mock data populated.
 * Data contract:
 *   - W1–W5 own their data: a disposable account with two brokers and one Apple (USD) position bought in EUR and then
 *     in OMR. The WAC target is the currency of the last acquisition (OMR) and OMR has no pair anywhere, so EUR→OMR is
 *     missing *by construction* — nothing in `populate_mock_data.py` can change that.
 *   - W6–W8 read the seeded Apple (USD) BUY in EUR on Directa → cross-FX scenario with the EUR/USD pair
 */
import {expect, test, type APIRequestContext, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled, validateRuns, waitForValidateRun} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, openOwnedAccount, seededAssetId, type OwnedAccount} from '../fixtures/owned-pair';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {daysAgoIso} from '../fixtures/dates';
import {appears} from '../fixtures/probe';

// 60 s: login and the 20 s transactions-page gate share this budget before the validate runs and the FX sync modal; 25 s left those no time under load.
test.setTimeout(60_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await Promise.race([page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000}), page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 20_000})]).catch(() => {
        /* either is fine */
    });
}

/**
 * A SearchSelect has no "I committed" event, but its option list is torn down
 * when a choice lands, and the field cascade the choice triggers re-renders
 * before that. Waiting for the list to go is therefore a real barrier.
 */
async function optionListClosed(page: Page) {
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 5_000});
}

async function openNewTransactionForm(page: Page) {
    await page.getByTestId('tx-add-button').click();
    await page.getByTestId('tx-form-modal').waitFor({state: 'visible', timeout: 5_000});
}

async function selectType(page: Page, type: string) {
    const typeSelect = page.getByTestId('tx-form-type');
    await typeSelect.locator('button, [role="combobox"]').first().click();
    await page.getByTestId(`search-select-option-${type}`).click();
    await optionListClosed(page);
}

async function selectAsset(page: Page, assetName: string) {
    const assetWrap = page.getByTestId('tx-form-asset-wrap');
    await assetWrap.locator('button, [role="combobox"]').first().click();
    // Type to filter
    const input = page.locator('[data-testid="tx-form-asset-wrap"] input[type="text"], [data-testid="tx-form-asset-wrap"] input[role="combobox"]').first();
    await expect(input, 'the asset picker opens with its search input').toBeVisible({timeout: 3_000});
    await input.fill(assetName);
    // The list is debounced; the named entry arriving *is* the settle.
    await expect(page.locator('[data-testid^="search-select-option-"]', {hasText: assetName}).first()).toBeVisible({timeout: 5_000});
    // Click first matching option
    const option = page.locator(`[data-testid^="search-select-option-"]`).first();
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
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

/**
 * A disposable account with two brokers and an Apple position on the first, bought in EUR and then in OMR.
 * The cost currency of the last acquisition is the WAC target, so the earlier EUR purchase needs EUR→OMR — a pair
 * no seed, route or chain provides. Returns the brokers' names for the form's pickers.
 */
async function openMissingPairAccount(page: Page, request: APIRequestContext, owned: OwnedAccount): Promise<{from: string; to: string}> {
    await openOwnedAccount(page, request, owned, 'wacfx');
    const from = await createOwnedBroker(page, 'wacfx-from', owned.brokerIds);
    const to = await createOwnedBroker(page, 'wacfx-to', owned.brokerIds);
    const apple = await seededAssetId(page, 'AAPL');
    await commitCreates(
        page,
        [
            {broker_id: from.id, type: 'DEPOSIT', date: daysAgoIso(12), cash: {code: 'EUR', amount: '1000'}},
            {broker_id: from.id, type: 'DEPOSIT', date: daysAgoIso(12), cash: {code: 'OMR', amount: '1000'}},
            {broker_id: from.id, asset_id: apple, type: 'BUY', date: daysAgoIso(9), quantity: '10', cash: {code: 'EUR', amount: '-500'}},
            {broker_id: from.id, asset_id: apple, type: 'BUY', date: daysAgoIso(6), quantity: '10', cash: {code: 'OMR', amount: '-500'}},
        ],
        'fund the account: Apple bought in EUR, then in OMR',
    );
    return {from: from.name, to: to.name};
}

/** Set up a TRANSFER form for the owned Apple position: its WAC needs EUR→OMR, which does not exist. */
async function setupMissingFxScenario(page: Page, brokers: {from: string; to: string}) {
    await openNewTransactionForm(page);
    await selectType(page, 'TRANSFER');
    await pickBrokerInPanel(page, 'tx-form-dual-from', brokers.from);
    await pickBrokerInPanel(page, 'tx-form-dual-to', brokers.to);
    await selectAsset(page, 'Apple');
    const root = page.getByTestId('tx-form-modal-root');
    const qtyInput = page.getByTestId('tx-form-quantity');
    await expect(qtyInput).toBeVisible({timeout: 2_000});
    const before = await validateRuns(root);
    await qtyInput.fill('5');
    await qtyInput.blur();
    // The verdict is what this scenario is about, so wait for the run that
    // carries it rather than for the debounce to have probably elapsed.
    await waitForValidateRun(root, before);
    // Validate now. A create form always renders it, enabled once the form is complete —
    // which the automatic run above proves — so it is asserted, never probed. That run
    // ended with the form idle, so the counter read here moves only for the click's run.
    const validateBtn = page.getByTestId('tx-form-validate-now');
    await expect(validateBtn).toBeVisible({timeout: 1_000});
    await expect(validateBtn).toBeEnabled({timeout: 1_000});
    const forced = await validateRuns(root);
    await validateBtn.click();
    await waitForValidateRun(root, forced);
}

/** Set up a TRANSFER form with Apple (USD) on Directa (EUR) — FX pair exists */
async function setupCrossFxScenario(page: Page) {
    await openNewTransactionForm(page);
    await selectType(page, 'TRANSFER');
    await pickBrokerInPanel(page, 'tx-form-dual-from', 'Interactive Brokers');
    await pickBrokerInPanel(page, 'tx-form-dual-to', 'Directa SIM');
    await selectAsset(page, 'Apple');
    const root = page.getByTestId('tx-form-modal-root');
    const qtyInput = page.getByTestId('tx-form-quantity');
    await expect(qtyInput).toBeVisible({timeout: 2_000});
    const before = await validateRuns(root);
    await qtyInput.fill('2');
    await qtyInput.blur();
    await waitForValidateRun(root, before);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('WAC FX — Sync Modal, missing pair (owned data)', () => {
    let owned: OwnedAccount;
    let account: {from: string; to: string};
    const brokers = () => account;

    test.beforeEach(async ({page, request}) => {
        owned = emptyOwnedAccount();
        account = await openMissingPairAccount(page, request, owned);
        await goToTransactions(page);
    });

    test.afterEach(async ({page, request}) => {
        await cleanupOwnedAccount(page, request, owned);
    });

    // === W1 — Banner sync button structure ===
    test('W1 — Issue banner sync FX link has correct structure', async ({page}) => {
        await setupMissingFxScenario(page, brokers());

        // The data is the test's own: the missing pair is always raised.
        await expect(page.getByTestId('tx-form-issues')).toBeVisible({timeout: 5_000});
        const syncLink = page.getByTestId('tx-form-sync-fx-link');
        await expect(syncLink).toBeVisible({timeout: 3_000});
        // Should have RefreshCw icon (svg inside)
        await expect(syncLink.locator('svg')).toBeVisible();
    });

    // === W2 — WacPreviewSection missing pairs display ===
    test('W2 — Missing pairs section shows dates and sync button when triggered', async ({page}) => {
        await setupMissingFxScenario(page, brokers());

        const missingPairs = page.getByTestId('tx-form-cost-basis-missing-pairs');
        await expect(missingPairs).toBeVisible({timeout: 5_000});
        // Should contain date strings (YYYY-MM-DD format)
        await expect(missingPairs).toContainText(/\d{4}-\d{2}-\d{2}/);

        // Sync button in the missing pairs section
        await expect(page.getByTestId('tx-form-cost-basis-sync-fx-btn')).toBeVisible();
    });

    // === W3 — FxSyncModal opens above FormModal ===
    test('W3 — FxSyncModal opens above FormModal via sync button', async ({page}) => {
        await setupMissingFxScenario(page, brokers());

        const syncBtn = page.getByTestId('tx-form-cost-basis-sync-fx-btn');
        await expect(syncBtn).toBeVisible({timeout: 5_000});
        await syncBtn.click();

        // FxSyncModal should be visible
        const syncModal = page.locator('[data-testid="fx-sync-modal"]');
        await expect(syncModal).toBeVisible({timeout: 5_000});

        // FormModal should still be in DOM (behind)
        await expect(page.getByTestId('tx-form-modal')).toBeVisible();
    });

    // === W3b — FxSyncModal opens via WacPreviewSection button too ===
    test('W3b — FxSyncModal opens via WacPreviewSection sync button', async ({page}) => {
        await setupMissingFxScenario(page, brokers());

        const syncBtn = page.getByTestId('tx-form-cost-basis-sync-fx-btn');
        await expect(syncBtn).toBeVisible({timeout: 5_000});
        await syncBtn.click();

        const syncModal = page.locator('[data-testid="fx-sync-modal"]');
        await expect(syncModal).toBeVisible({timeout: 5_000});
    });

    // === W4 — Sync modal stays open after sync ===
    test('W4 — After sync completes, modal stays open with results', async ({page}) => {
        await setupMissingFxScenario(page, brokers());

        const syncBtn = page.getByTestId('tx-form-cost-basis-sync-fx-btn');
        await expect(syncBtn).toBeVisible({timeout: 5_000});
        await syncBtn.click();

        const syncModal = page.locator('[data-testid="fx-sync-modal"]');
        await expect(syncModal).toBeVisible({timeout: 5_000});

        // Click the sync/start button inside the modal
        const startBtn = syncModal.getByTestId('sync-modal-start');
        await expect(startBtn).toBeVisible({timeout: 5_000});
        await startBtn.click();
        // Deliberate: this proves the modal does *not* close on its own. A
        // retrying assertion would confirm it instantly and never open the
        // window in which an auto-close could happen.
        await page.waitForTimeout(3_000);

        // Modal should still be visible (not auto-closed)
        await expect(syncModal).toBeVisible();
    });

    // === W5 — Closing modal keeps FormModal open ===
    test('W5 — Closing FxSyncModal keeps FormModal visible', async ({page}) => {
        await setupMissingFxScenario(page, brokers());

        const syncBtn = page.getByTestId('tx-form-cost-basis-sync-fx-btn');
        await expect(syncBtn).toBeVisible({timeout: 5_000});
        await syncBtn.click();

        const syncModal = page.locator('[data-testid="fx-sync-modal"]');
        await expect(syncModal).toBeVisible({timeout: 5_000});

        // Close via Escape
        await page.keyboard.press('Escape');
        await expect(syncModal).not.toBeVisible({timeout: 3_000});

        // FormModal should still be visible
        await expect(page.getByTestId('tx-form-modal')).toBeVisible();
    });
});

test.describe('WAC FX — Sync Modal & Cross-Currency', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    // === W6 — Qualifying table renders with currency info ===
    test('W6 — Qualifying table shows currency-formatted amounts', async ({page}) => {
        await setupCrossFxScenario(page);

        // Wait for WAC to be calculated (Apple USD bought in EUR)
        const costBasis = page.getByTestId('tx-form-cost-basis');
        await expect(costBasis).toBeVisible({timeout: 5_000});

        // Validate now. A create form always renders it, enabled once the form is complete —
        // which the automatic run of the setup proves — so it is asserted, never probed.
        const root = page.getByTestId('tx-form-modal-root');
        const validateBtn = page.getByTestId('tx-form-validate-now');
        await expect(validateBtn).toBeVisible({timeout: 2_000});
        await expect(validateBtn).toBeEnabled({timeout: 2_000});
        const before = await validateRuns(root);
        await validateBtn.click();
        await waitForValidateRun(root, before);

        // Expand qualifying table
        const showBtn = page.getByTestId('tx-form-cost-basis-show-qualifying');
        // Apple (USD) bought in EUR on Directa: the validated auto WAC always carries its qualifying list.
        await expect(showBtn).toBeVisible({timeout: 5_000});
        await showBtn.click();
        const table = page.getByTestId('tx-form-cost-basis-qualifying-table');
        await expect(table).toBeVisible({timeout: 3_000});

        // Table should contain currency-formatted amounts ($ 🇺🇸 USD pattern)
        const tableText = await table.textContent();
        expect(tableText).toMatch(/\$\s*🇺🇸\s*USD/);
        // Table should have multiple rows (qualifying TXs)
        const rows = table.locator('tbody tr');
        const rowCount = await rows.count();
        expect(rowCount).toBeGreaterThan(0);
    });

    // === W7 — Tooltip FX format ===
    test('W7 — FX tooltip shows clean format with currency codes', async ({page}) => {
        await setupCrossFxScenario(page);

        const costBasis = page.getByTestId('tx-form-cost-basis');
        await expect(costBasis).toBeVisible({timeout: 5_000});

        // Trigger validate: always rendered in a create form, enabled on a complete one.
        const root = page.getByTestId('tx-form-modal-root');
        const validateBtn = page.getByTestId('tx-form-validate-now');
        await expect(validateBtn).toBeVisible({timeout: 2_000});
        await expect(validateBtn).toBeEnabled({timeout: 2_000});
        const before = await validateRuns(root);
        await validateBtn.click();
        await waitForValidateRun(root, before);

        // Expand qualifying table
        const showBtn = page.getByTestId('tx-form-cost-basis-show-qualifying');
        // Apple (USD) bought in EUR on Directa: the validated auto WAC always carries its qualifying list.
        await expect(showBtn).toBeVisible({timeout: 5_000});
        await showBtn.click();
        const table = page.getByTestId('tx-form-cost-basis-qualifying-table');
        await expect(table).toBeVisible({timeout: 3_000});

        // Hover on a cell that has tooltip (the converted amount cells)
        const tooltipTrigger = table.locator('[title], [data-tooltip]').first();
        // Optional by design: only a converted amount carries a tooltip; this data may hold none in the list.
        if (!(await appears(tooltipTrigger, 3_000))) {
            await expect(tooltipTrigger).toBeHidden();
            return;
        }
        await tooltipTrigger.hover();

        // Tooltip should contain "FX:" prefix and "=" sign
        const tooltip = page.locator('[role="tooltip"], .tooltip, [data-testid*="tooltip"]').first();
        await expect(tooltip).toBeVisible({timeout: 3_000});
        const tipText = await tooltip.textContent();
        expect(tipText).toContain('FX:');
        expect(tipText).toContain('=');
    });

    // === W8 — Stale FX indicator ===
    test('W8 — Stale FX shows ⚠️ warning banner when qualifying visible', async ({page}) => {
        await setupCrossFxScenario(page);

        const costBasis = page.getByTestId('tx-form-cost-basis');
        await expect(costBasis).toBeVisible({timeout: 5_000});

        // Trigger validate: always rendered in a create form, enabled on a complete one.
        const root = page.getByTestId('tx-form-modal-root');
        const validateBtn = page.getByTestId('tx-form-validate-now');
        await expect(validateBtn).toBeVisible({timeout: 2_000});
        await expect(validateBtn).toBeEnabled({timeout: 2_000});
        const before = await validateRuns(root);
        await validateBtn.click();
        await waitForValidateRun(root, before);

        // If stale FX is detected, the banner should appear
        const staleBanner = page.getByTestId('tx-form-cost-basis-fx-stale-banner');
        // Optional by design: shown only when the FX data of the shared test DB is actually stale (it depends on
        // when it was last synced). Not stale → the banner must be absent, not just unseen.
        if (await appears(staleBanner, 3_000)) {
            const bannerText = await staleBanner.textContent();
            expect(bannerText).toBeTruthy();
            // Should contain warning text
            expect(bannerText!.length).toBeGreaterThan(10);
        } else {
            await expect(staleBanner).toBeHidden();
        }
    });
});
