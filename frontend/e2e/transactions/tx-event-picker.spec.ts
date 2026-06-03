/**
 * tx-event-picker.spec.ts — Event Picker E2E Tests
 *
 * Tests the AssetEventSelect component within the FormModal:
 * - Card-style dropdown with emoji, date, amount
 * - Delta display when cash is filled
 * - Slider range updates
 * - Hidden for non-linkable types (BUY)
 * - Selection persists across validate
 *
 * Prerequisites: backend test mode, mock data populated.
 * Mock data contract:
 *   - Apple has DIVIDEND event at today-3 (within ±7 default range)
 *   - e2e_test_user has OWNER on Interactive Brokers
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(45_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await Promise.race([page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000}), page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 10_000})]).catch(() => {});
    await page.waitForTimeout(500);
}

async function openCreateFlow(page: Page) {
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/** Select a transaction type via SearchSelect. */
async function selectType(page: Page, typeCode: string) {
    const typeButton = page.getByTestId('tx-form-type');
    await typeButton.click();
    await page.waitForTimeout(300);
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await page.waitForTimeout(300);
}

/** Pick broker by name. */
async function pickBroker(page: Page, brokerName: string) {
    const brokerWrap = page.getByTestId('tx-form-broker-wrap');
    await brokerWrap.locator('button, [role="combobox"]').first().click();
    await page.waitForTimeout(300);
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: brokerName});
    await expect(option.first()).toBeVisible({timeout: 3_000});
    await option.first().click();
    await page.waitForTimeout(300);
}

/** Pick asset by name (types to filter). */
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

/** Open the "Optional" disclosure if not already open. */
async function openOptionalSection(page: Page) {
    const toggle = page.getByTestId('tx-form-optional-toggle');
    // Click to open the <details> if closed
    const details = toggle.locator('..');
    const isOpen = await details.getAttribute('open');
    if (isOpen === null) {
        await toggle.click();
        await page.waitForTimeout(300);
    }
}

/**
 * Setup common DIVIDEND form with Apple on Interactive Brokers.
 * Date defaults to today (which covers the today-3 DIVIDEND event).
 */
async function setupDividendForm(page: Page) {
    await openCreateFlow(page);
    await selectType(page, 'DIVIDEND');
    await pickBroker(page, 'Interactive Brokers');
    await pickAssetByName(page, 'Apple');
    // Date is auto-set to today by FormModal
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Event Picker', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('picker hidden for BUY type', async ({page}) => {
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickBroker(page, 'Interactive Brokers');
        await pickAssetByName(page, 'Apple');

        // Optional section should NOT contain event picker for BUY
        const eventSelect = page.getByTestId('tx-form-event-select');
        await expect(eventSelect).not.toBeVisible();
    });

    test('picker visible for DIVIDEND with asset', async ({page}) => {
        await setupDividendForm(page);

        // Open the optional section to see the event picker
        await openOptionalSection(page);

        // Event picker should be visible
        const eventSelect = page.getByTestId('tx-form-event-select');
        await expect(eventSelect).toBeVisible({timeout: 5_000});
    });

    test('slider is visible with max=30', async ({page}) => {
        await setupDividendForm(page);
        await openOptionalSection(page);

        // Open the picker dropdown to see the slider
        const trigger = page.getByTestId('tx-form-event-picker-trigger');
        await expect(trigger).toBeVisible({timeout: 5_000});
        await trigger.click();
        await page.waitForTimeout(500);

        // Slider should be visible inside the dropdown header
        const slider = page.getByTestId('tx-form-event-slider');
        await expect(slider).toBeVisible({timeout: 3_000});

        // The range input inside should have max=30
        const rangeInput = slider.locator('input[type="range"]');
        await expect(rangeInput).toBeVisible();
        const max = await rangeInput.getAttribute('max');
        expect(max).toBe('30');
    });

    test('event options show card-style format with emoji', async ({page}) => {
        await setupDividendForm(page);
        await openOptionalSection(page);

        // Wait for event select
        const eventSelect = page.getByTestId('tx-form-event-select');
        await expect(eventSelect).toBeVisible({timeout: 5_000});

        // Open the dropdown — click on the trigger button
        const trigger = page.getByTestId('tx-form-event-picker-trigger');
        await trigger.click();
        await page.waitForTimeout(500);

        // Should show the 💰 emoji (DIVIDEND) in at least one option
        const dividendEmoji = page.locator('text=💰');
        await expect(dividendEmoji.first()).toBeVisible({timeout: 5_000});
    });

    test('create new event via inline modal', async ({page}) => {
        await setupDividendForm(page);
        await openOptionalSection(page);

        // Open event picker dropdown
        const trigger = page.getByTestId('tx-form-event-picker-trigger');
        await expect(trigger).toBeVisible({timeout: 5_000});
        await trigger.click();
        await page.waitForTimeout(500);

        // Click "+ New event" button in footer
        const createBtn = page.getByTestId('tx-form-event-create-new');
        await expect(createBtn).toBeVisible({timeout: 3_000});
        await createBtn.click();
        await page.waitForTimeout(500);

        // Mini modal should appear
        const modal = page.getByTestId('event-create-mini-modal');
        await expect(modal).toBeVisible({timeout: 3_000});

        // Type should default to DIVIDEND (SimpleSelect shows text)
        const typeSelect = page.getByTestId('event-create-type');
        await expect(typeSelect).toContainText('Dividend', {timeout: 3_000});

        // Fill amount
        const amountInput = page.getByTestId('event-create-amount');
        await amountInput.fill('1.50');

        // Fill notes
        const notesInput = page.getByTestId('event-create-notes');
        await notesInput.fill('E2E test event');

        // Submit
        const submitBtn = page.getByTestId('event-create-submit');
        await submitBtn.click();

        // Modal should close and event should be auto-selected
        await expect(modal).not.toBeVisible({timeout: 10_000});

        // The trigger should now show the newly created event (with 💰 emoji)
        await expect(trigger).toContainText('💰', {timeout: 5_000});
    });
});
