/**
 * tx-fx-implied-rate.spec.ts — FX Implied Rate & Spread E2E Tests.
 *
 * Validates the FX Implied Rate feature:
 * - Scenario A: BulkModal banner shows FX suffix (implied rate badge + tooltip trigger)
 *   when two standalone TX with different currencies match as FX_CONVERSION.
 * - Scenario B: FormModal shows FX info marker between From/To panels
 *   when creating an FX_CONVERSION with both amounts filled.
 *
 * Plan: FxImpliedRateSpread (2026-05-18).
 * Prerequisites: backend test mode (port 8001), mock data populated.
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(30_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await Promise.race([page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000}), page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 10_000})]).catch(() => {});
    await page.waitForTimeout(500);
}

/** Select a transaction type in the FormModal type search-select. */
async function selectType(page: Page, typeRegex: RegExp) {
    const typeButton = page.getByTestId('tx-form-type');
    await typeButton.click();
    await page.waitForTimeout(300);
    const option = page.locator('[data-testid^="search-select-option-"]').filter({hasText: typeRegex}).first();
    await expect(option).toBeVisible({timeout: 2_000});
    await option.click();
    await page.waitForTimeout(300);
}

/** Pick the first available broker in FormModal. */
async function selectFirstBroker(page: Page) {
    const brokerWrap = page.getByTestId('tx-form-broker-wrap');
    await brokerWrap.locator('button, [role="combobox"]').first().click();
    await page.waitForTimeout(300);
    const brokerOption = page.locator('[data-testid^="search-select-option-"]').first();
    await expect(brokerOption).toBeVisible({timeout: 2_000});
    await brokerOption.click();
    await page.waitForTimeout(300);
}

/** Fill cash amount in a cash cell identified by testid. */
async function fillCash(page: Page, testid: string, amount: string, currencyCode?: string) {
    const cashWrap = page.getByTestId(testid);
    await expect(cashWrap).toBeVisible({timeout: 2_000});
    // Change currency FIRST (before amount) so emit picks up the right code
    if (currencyCode) {
        const currencyTrigger = cashWrap.locator('.currency-wrap [role="combobox"]').first();
        await expect(currencyTrigger).toBeVisible({timeout: 2_000});
        await currencyTrigger.click();
        await page.waitForTimeout(300);
        // The dropdown search input appears (inlineSearch mode)
        const searchInput = page.locator('input[placeholder]').filter({hasText: ''}).last();
        const dropdownInput = cashWrap.locator('input[type="text"]').first();
        const inputToUse = (await dropdownInput.isVisible({timeout: 1_000}).catch(() => false)) ? dropdownInput : searchInput;
        await inputToUse.fill(currencyCode);
        await page.waitForTimeout(400);
        const currOption = page.locator('[data-testid^="search-select-option-"]').filter({hasText: currencyCode}).first();
        await expect(currOption).toBeVisible({timeout: 3_000});
        await currOption.click();
        await page.waitForTimeout(300);
    }
    const cashInput = cashWrap.locator('input[type="number"]').first();
    await expect(cashInput).toBeVisible({timeout: 1_000});
    await cashInput.fill(amount);
    await page.waitForTimeout(200);
}

/** Save the FormModal (click save button -> pushes to BulkModal grid). */
async function saveFormModal(page: Page) {
    const saveBtn = page.getByTestId('tx-form-save');
    await expect(saveBtn).toBeVisible({timeout: 3_000});
    await saveBtn.click();
    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 10_000});
}

/** Open BulkModal by selecting 2 editable rows + clicking toolbar edit. */
async function openBulkModal(page: Page) {
    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
    const count = await rows.count();
    let selected = 0;
    for (let i = 0; i < count && selected < 2; i++) {
        const row = rows.nth(i);
        const cls = (await row.getAttribute('class')) ?? '';
        if (cls.includes('tx-row-receiver')) continue; // skip paired secondary rows
        const text = (await row.textContent()) ?? '';
        if (text.includes('DEGIRO')) continue; // skip viewer rows
        const checkbox = row.locator('.checkbox-btn').first();
        await checkbox.click();
        await page.waitForTimeout(200);
        selected++;
    }
    const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
    await expect(editBtn).toBeVisible({timeout: 3_000});
    await editBtn.click();
    await page.waitForTimeout(500);
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('FX Implied Rate & Spread', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // =====================================================================
    // Scenario A: BulkModal Banner — FX suffix appears for FX_CONVERSION
    // =====================================================================

    test('Scenario A: BulkModal banner shows FX implied rate suffix', async ({page}) => {
        await goToTransactions(page);
        await openBulkModal(page);

        const addRowBtn = page.getByTestId('tx-bulk-add-row');

        // Add WITHDRAWAL EUR
        await addRowBtn.click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, /withdrawal/i);
        await selectFirstBroker(page);
        await fillCash(page, 'tx-form-cash-wrap', '1000');
        await saveFormModal(page);

        // Add DEPOSIT USD
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
        await addRowBtn.click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, /deposit/i);
        await selectFirstBroker(page);
        await fillCash(page, 'tx-form-cash-wrap', '1100', 'USD');
        await saveFormModal(page);

        // Wait for suggest detection
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 3_000});
        await page.waitForTimeout(1_500);

        // The promote-suggest banner should appear
        const banner = page.getByTestId('promote-suggest-banner');
        await expect(banner).toBeVisible({timeout: 5_000});

        // The FX info suffix should be visible
        const fxInfo = page.getByTestId('promote-suggest-fx-info-0');
        await expect(fxInfo).toBeVisible({timeout: 3_000});

        // Verify implied rate (1100/1000 = 1.1000)
        await expect(fxInfo).toContainText('1.1000');
        await expect(fxInfo).toContainText('EUR');
        await expect(fxInfo).toContainText('USD');
    });

    // =====================================================================
    // Scenario A2: Semantic ordering — negative (from) shown first
    // =====================================================================

    test('Scenario A2: Banner shows from-side (negative) first', async ({page}) => {
        await goToTransactions(page);
        await openBulkModal(page);

        const addRowBtn = page.getByTestId('tx-bulk-add-row');

        // Create DEPOSIT FIRST (positive), then WITHDRAWAL (negative)
        await addRowBtn.click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, /deposit/i);
        await selectFirstBroker(page);
        await fillCash(page, 'tx-form-cash-wrap', '1100', 'USD');
        await saveFormModal(page);

        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
        await addRowBtn.click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, /withdrawal/i);
        await selectFirstBroker(page);
        await fillCash(page, 'tx-form-cash-wrap', '1000');
        await saveFormModal(page);

        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 3_000});
        await page.waitForTimeout(1_500);

        const banner = page.getByTestId('promote-suggest-banner');
        await expect(banner).toBeVisible({timeout: 5_000});

        // First item: withdrawal icon (from/negative) before deposit icon (to/positive)
        const item = page.getByTestId('promote-suggest-item-0');
        await expect(item).toBeVisible({timeout: 2_000});
        const imgs = item.locator('img[src*="/icons/transactions/"]');
        const firstSrc = await imgs.nth(0).getAttribute('src');
        const secondSrc = await imgs.nth(1).getAttribute('src');
        expect(firstSrc).toContain('withdrawal');
        expect(secondSrc).toContain('deposit');
    });

    // =====================================================================
    // Scenario B: FormModal — FX info marker shows between From/To panels
    // =====================================================================

    test('Scenario B: FormModal shows FX info marker for FX_CONVERSION', async ({page}) => {
        await goToTransactions(page);

        // Open create flow
        await page.getByTestId('tx-add-button').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

        // Select FX_CONVERSION type
        await selectType(page, /fx.conversion|cambio.valuta|conversion/i);
        await page.waitForTimeout(500);

        // Dual form should appear
        const dualSplit = page.getByTestId('tx-form-dual-split');
        await expect(dualSplit).toBeVisible({timeout: 3_000});

        // Pick broker
        const brokerWrap = page.getByTestId('tx-form-broker-wrap');
        if (await brokerWrap.isVisible({timeout: 2_000}).catch(() => false)) {
            await brokerWrap.locator('button, [role="combobox"]').first().click();
            await page.waitForTimeout(300);
            const brokerOption = page.locator('[data-testid^="search-select-option-"]').first();
            if (await brokerOption.isVisible({timeout: 2_000}).catch(() => false)) {
                await brokerOption.click();
            }
            await page.waitForTimeout(300);
        }

        // Fill "From" cash (EUR, 1000)
        await fillCash(page, 'tx-form-cash-from', '1000');

        // Fill "To" cash (USD, 1085)
        await fillCash(page, 'tx-form-cash-to', '1085', 'USD');

        // FX info marker should appear
        const fxInfoMarker = page.getByTestId('tx-form-fx-info');
        await expect(fxInfoMarker).toBeVisible({timeout: 3_000});

        // Verify implied rate (1085/1000 = 1.0850)
        await expect(fxInfoMarker).toContainText('1.0850');
    });
});
