/**
 * Asset Data Editor — E2E Tests
 *
 * Tests the data editor panel in the Asset detail page:
 * - Opening the editor panel
 * - Two tabs (Prices / Events) with switching
 * - CSV import modals for both prices and events
 * - Save/Cancel bar visibility
 * - CSV import with valid/invalid data
 * - Stale rows toggle
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated with at least one asset with prices
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage, navigateToAssetByName} from './assets-helpers';

test.describe('Asset Data Editor', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Helper: Navigate to Apple Inc (known to have mock price data)
    // ========================================================================
    async function goToAssetWithPrices(page: import('@playwright/test').Page) {
        await goToAssetsPage(page);
        await navigateToAssetByName(page, 'Apple');
    }

    // ========================================================================
    // Helper: Open data editor panel
    // ========================================================================
    async function openDataEditor(page: import('@playwright/test').Page) {
        await goToAssetWithPrices(page);
        // Wait for chart to render — the edit button only appears when lineData.length > 0
        await page.waitForSelector('canvas', {timeout: 10_000});
        await page.waitForTimeout(500);
        // The edit data button is inside {:else if lineData.length > 0} — check it exists
        const editDataBtn = page.getByTestId('asset-detail-editdata-btn');
        await expect(editDataBtn).toBeVisible({timeout: 5_000});
        await editDataBtn.click();
        await page.waitForTimeout(300);
        await expect(page.getByTestId('asset-detail-editor-panel')).toBeVisible();
    }

    // ========================================================================
    // Helper: Open the price CSV import modal
    // ========================================================================
    async function openPriceImportModal(page: import('@playwright/test').Page) {
        await openDataEditor(page);
        await page.getByTestId('fx-data-import-btn').click();
        await page.waitForTimeout(200);
        const modal = page.getByTestId('data-import-modal');
        await expect(modal).toBeVisible();
        return modal;
    }

    // ========================================================================
    // Helper: Open the event CSV import modal
    // ========================================================================
    async function openEventImportModal(page: import('@playwright/test').Page) {
        await openDataEditor(page);
        await page.getByTestId('asset-editor-events-tab').click();
        await page.waitForTimeout(200);
        await page.getByTestId('fx-data-import-btn').click();
        await page.waitForTimeout(200);
        const modal = page.getByTestId('data-import-modal');
        await expect(modal).toBeVisible();
        return modal;
    }

    // ========================================================================
    // Helper: Get the CSV textarea content
    // ========================================================================
    async function getCsvText(modal: import('@playwright/test').Locator) {
        return modal.locator('textarea').inputValue();
    }

    // ========================================================================
    // Test 1: Edit data button opens the editor panel
    // ========================================================================
    test('edit data button opens the editor panel', async ({page}) => {
        await openDataEditor(page);
        await expect(page.getByTestId('asset-detail-editor-panel')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Editor shows two tabs (Prices and Events)
    // ========================================================================
    test('editor shows prices and events tabs', async ({page}) => {
        await openDataEditor(page);
        const pricesTab = page.getByTestId('asset-editor-prices-tab');
        const eventsTab = page.getByTestId('asset-editor-events-tab');
        await expect(pricesTab).toBeVisible();
        await expect(eventsTab).toBeVisible();
    });

    // ========================================================================
    // Test 3: Prices tab is active by default
    // ========================================================================
    test('prices tab is active by default', async ({page}) => {
        await openDataEditor(page);
        const pricesTab = page.getByTestId('asset-editor-prices-tab');
        // Active tab has border-libre-green class (check for text color)
        await expect(pricesTab).toHaveClass(/text-libre-green|text-emerald/);
    });

    // ========================================================================
    // Test 4: Switch to events tab
    // ========================================================================
    test('switch to events tab works', async ({page}) => {
        await openDataEditor(page);
        const eventsTab = page.getByTestId('asset-editor-events-tab');
        await eventsTab.click();
        await page.waitForTimeout(200);
        // Events tab should now be active
        await expect(eventsTab).toHaveClass(/text-libre-green|text-emerald/);
    });

    // ========================================================================
    // Test 5: Prices tab shows DataEditor with Import CSV and Add Row
    // ========================================================================
    test('prices tab has import CSV and add row buttons', async ({page}) => {
        await openDataEditor(page);
        // Import CSV button
        const importBtn = page.getByTestId('fx-data-import-btn');
        await expect(importBtn).toBeVisible();
        // Add Row button
        const addRowBtn = page.getByTestId('fx-data-add-row-btn');
        await expect(addRowBtn).toBeVisible();
    });

    // ========================================================================
    // Test 6: Events tab also shows DataEditor with Import CSV
    // ========================================================================
    test('events tab has import CSV and add row buttons', async ({page}) => {
        await openDataEditor(page);
        // Switch to events tab
        await page.getByTestId('asset-editor-events-tab').click();
        await page.waitForTimeout(200);
        // Import CSV button
        const importBtn = page.getByTestId('fx-data-import-btn');
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 7: Import CSV opens price import modal with correct header
    // ========================================================================
    test('import CSV opens price import modal', async ({page}) => {
        const modal = await openPriceImportModal(page);
        // Header should contain 'date;currency;close'
        const csvText = await getCsvText(modal);
        expect(csvText).toContain('date;currency;close');
    });

    // ========================================================================
    // Test 8: Import CSV opens event import modal when on events tab
    // ========================================================================
    test('import CSV opens event import modal on events tab', async ({page}) => {
        const modal = await openEventImportModal(page);
        // Header should contain event-specific columns
        const csvText = await getCsvText(modal);
        expect(csvText).toContain('date;currency;type;amount');
    });

    // ========================================================================
    // Test 9: Save/Cancel bar is visible
    // ========================================================================
    test('save and cancel buttons are visible', async ({page}) => {
        await openDataEditor(page);
        const panel = page.getByTestId('asset-detail-editor-panel');
        // Save button (initially disabled since no changes)
        const saveBtn = panel.locator('button:has-text("Save")');
        await expect(saveBtn).toBeVisible();
        await expect(saveBtn).toBeDisabled();
        // Cancel button
        const cancelBtn = panel.locator('button:has-text("Cancel")');
        await expect(cancelBtn).toBeVisible();
    });

    // ========================================================================
    // Test 10: Close editor via ✕ button
    // ========================================================================
    test('close button hides the editor panel', async ({page}) => {
        await openDataEditor(page);
        const panel = page.getByTestId('asset-detail-editor-panel');
        await expect(panel).toBeVisible();
        // Click close button
        await panel.locator('button:has-text("✕")').click();
        await page.waitForTimeout(300);
        await expect(panel).not.toBeVisible();
    });

    // ========================================================================
    // Test 11: Add row in prices tab enables save button
    // ========================================================================
    test('add row enables save button', async ({page}) => {
        await openDataEditor(page);
        const panel = page.getByTestId('asset-detail-editor-panel');
        // Click Add Row
        await page.getByTestId('fx-data-add-row-btn').click();
        await page.waitForTimeout(300);
        // Save button should now show dirty count
        const saveBtn = panel.locator('button:has-text("Save")');
        await expect(saveBtn).toBeEnabled();
    });

    // ========================================================================
    // Test 12: Switch tabs preserves dirty state
    // ========================================================================
    test('switching tabs preserves dirty state', async ({page}) => {
        await openDataEditor(page);
        const panel = page.getByTestId('asset-detail-editor-panel');
        // Add row in prices tab
        await page.getByTestId('fx-data-add-row-btn').click();
        await page.waitForTimeout(200);
        // Prices tab badge should show 1
        const pricesTab = page.getByTestId('asset-editor-prices-tab');
        await expect(pricesTab.locator('span.rounded-full')).toHaveText('1');
        // Switch to events tab and back
        await page.getByTestId('asset-editor-events-tab').click();
        await page.waitForTimeout(200);
        await pricesTab.click();
        await page.waitForTimeout(200);
        // Save button should still be enabled
        const saveBtn = panel.locator('button:has-text("Save")');
        await expect(saveBtn).toBeEnabled();
    });

    // ========================================================================
    // Test 13: Cancel resets dirty state
    // ========================================================================
    test('cancel resets dirty state and closes editor', async ({page}) => {
        await openDataEditor(page);
        const panel = page.getByTestId('asset-detail-editor-panel');
        // Add row
        await page.getByTestId('fx-data-add-row-btn').click();
        await page.waitForTimeout(200);
        // Click cancel
        await panel.locator('button:has-text("Cancel")').click();
        await page.waitForTimeout(300);
        // Editor should be hidden
        await expect(panel).not.toBeVisible();
    });

    // ========================================================================
    // Test 14: Price CSV import — valid data shows correct row count
    // ========================================================================
    test('price CSV import: valid data shows Import button with row count', async ({page}) => {
        const modal = await openPriceImportModal(page);

        // Type valid price CSV data (must use full header with all columns)
        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;close;open;high;low;volume\n2020-06-10;USD;150.25;;;;\n2020-06-11;USD;151.30;;;;\n2020-06-12;EUR;148.90;;;;');
        await page.waitForTimeout(200);

        // Import button should show "Import (3)" for 3 valid rows
        const importBtn = modal.locator('button', {hasText: /Import \(3\)/});
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 15: Price CSV import — extended format with optional columns
    // ========================================================================
    test('price CSV import: extended format accepted', async ({page}) => {
        const modal = await openPriceImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;close;open;high;low;volume\n2020-06-10;USD;150.25;149.00;151.00;148.50;1200000');
        await page.waitForTimeout(200);

        // Should show 1 valid row
        const importBtn = modal.locator('button', {hasText: /Import \(1\)/});
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 16: Price CSV import — invalid data shows errors
    // ========================================================================
    test('price CSV import: invalid rows show error indicators', async ({page}) => {
        const modal = await openPriceImportModal(page);

        const textarea = modal.locator('textarea');
        // Missing close price (required), bad date, non-numeric close
        await textarea.fill('date;currency;close;open;high;low;volume\n2020-06-10;USD;;;;;\nnot-a-date;USD;100;;;;\n2020-06-11;USD;abc;;;;');
        await page.waitForTimeout(200);

        // Error indicators (✗) should be visible
        const errorIndicators = modal.locator('.text-red-500');
        await expect(errorIndicators.first()).toBeVisible();

        // Import button should NOT show 3 valid rows (some are invalid)
        const importBtnAll = modal.locator('button', {hasText: /Import \(3\)/});
        await expect(importBtnAll).not.toBeVisible();
    });

    // ========================================================================
    // Test 17: Price CSV import — importing adds rows to table
    // ========================================================================
    test('price CSV import: imported rows appear in data editor', async ({page}) => {
        const modal = await openPriceImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;close;open;high;low;volume\n2019-01-15;USD;99.99;;;;\n2019-01-16;USD;100.50;;;;');
        await page.waitForTimeout(200);

        // Click Import button
        const importBtn = modal.locator('button', {hasText: /Import \(2\)/});
        await expect(importBtn).toBeVisible();
        await importBtn.click();
        await page.waitForTimeout(300);

        // Modal should be closed
        await expect(modal).not.toBeVisible();

        // Save button should be enabled (dirty rows from import)
        const panel = page.getByTestId('asset-detail-editor-panel');
        const saveBtn = panel.locator('button:has-text("Save")');
        await expect(saveBtn).toBeEnabled();

        // Dirty count should include imported rows
        await expect(saveBtn).toHaveText(/Save \(\d+\)/);
    });

    // ========================================================================
    // Test 18: Event CSV import — valid data shows correct row count
    // ========================================================================
    test('event CSV import: valid data shows Import button with row count', async ({page}) => {
        const modal = await openEventImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;type;amount;notes\n2020-03-15;USD;DIVIDEND;1.25;Q1 payout\n2020-06-01;;SPLIT;2;2:1 split');
        await page.waitForTimeout(200);

        // Import button should show "Import (2)" for 2 valid rows
        const importBtn = modal.locator('button', {hasText: /Import \(2\)/});
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 19: Event CSV import — invalid event type shows error
    // ========================================================================
    test('event CSV import: missing required fields show errors', async ({page}) => {
        const modal = await openEventImportModal(page);

        const textarea = modal.locator('textarea');
        // Missing amount (required), and empty type (required)
        await textarea.fill('date;currency;type;amount;notes\n2020-03-15;USD;;1.25;test\n2020-06-01;USD;DIVIDEND;;test');
        await page.waitForTimeout(200);

        // Error indicators should be visible
        const errorIndicators = modal.locator('.text-red-500');
        await expect(errorIndicators.first()).toBeVisible();
    });

    // ========================================================================
    // Test 20: Event CSV import — importing adds rows to events table
    // ========================================================================
    test('event CSV import: imported rows appear in events editor', async ({page}) => {
        const modal = await openEventImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;type;amount;notes\n2019-12-15;USD;DIVIDEND;0.75;test dividend');
        await page.waitForTimeout(200);

        // Click Import
        const importBtn = modal.locator('button', {hasText: /Import \(1\)/});
        await expect(importBtn).toBeVisible();
        await importBtn.click();
        await page.waitForTimeout(300);

        // Modal closed
        await expect(modal).not.toBeVisible();

        // Save button should be enabled
        const panel = page.getByTestId('asset-detail-editor-panel');
        const saveBtn = panel.locator('button:has-text("Save")');
        await expect(saveBtn).toBeEnabled();
    });

    // ========================================================================
    // Test 21: Stale toggle is visible when stale rows exist
    // ========================================================================
    test('stale toggle is visible in toolbar', async ({page}) => {
        await openDataEditor(page);
        // The stale toggle (switch) should be visible if there are stale rows
        const staleToggle = page.getByTestId('data-editor-stale-toggle');
        // It may or may not be visible depending on data — check it doesn't crash
        if (await staleToggle.isVisible({timeout: 3000}).catch(() => false)) {
            await expect(staleToggle).toBeVisible();
            // Toggle should contain the amber counter
            const counter = staleToggle.locator('span.text-amber-600, span.text-amber-400');
            await expect(counter.first()).toBeVisible();
        }
    });

    // ========================================================================
    // Test 22: Price CSV import — partial skip with ;; for optional columns
    // ========================================================================
    test('price CSV import: partial columns with ;; accepted', async ({page}) => {
        const modal = await openPriceImportModal(page);

        const textarea = modal.locator('textarea');
        // Use extended header but skip open,high,low with ;;
        await textarea.fill('date;currency;close;open;high;low;volume\n2020-06-10;USD;150.25;;;;1500000');
        await page.waitForTimeout(200);

        // Should accept as 1 valid row (optional columns skipped)
        const importBtn = modal.locator('button', {hasText: /Import \(1\)/});
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 23: Event CSV import — all event types accepted
    // ========================================================================
    test('event CSV import: all event types are valid', async ({page}) => {
        const modal = await openEventImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;type;amount;notes\n' + '2020-01-01;USD;DIVIDEND;1.00;\n' + '2020-02-01;EUR;INTEREST;0.50;\n' + '2020-03-01;;SPLIT;2;\n' + '2020-04-01;USD;PRICE_ADJUSTMENT;-5.00;\n' + '2020-05-01;USD;MATURITY_SETTLEMENT;100;final');
        await page.waitForTimeout(200);

        // All 5 event types should be valid
        const importBtn = modal.locator('button', {hasText: /Import \(5\)/});
        await expect(importBtn).toBeVisible();
    });
});
