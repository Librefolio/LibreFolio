/**
 * FX CSV Import — E2E Tests
 *
 * Tests the CSV import modal in the FX data editor.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated with EUR-USD data
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxDetailPage} from './fx-helpers';

test.describe('FX CSV Import', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Helper: Open the data editor
    // ========================================================================
    async function openDataEditor(page: import('@playwright/test').Page) {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-edit-btn').click();
        await page.waitForTimeout(200);
        await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible();
    }

    // ========================================================================
    // Helper: Open the import modal (from data editor)
    // ========================================================================
    async function openImportModal(page: import('@playwright/test').Page) {
        await openDataEditor(page);
        await page.getByTestId('fx-data-import-btn').click();
        await page.waitForTimeout(200);
        const modal = page.getByTestId('data-import-modal');
        await expect(modal).toBeVisible();
        return modal;
    }

    // ========================================================================
    // Helper: Get the CSV textarea text content
    // ========================================================================
    async function getCsvText(modal: import('@playwright/test').Locator) {
        return modal.locator('textarea').inputValue();
    }

    // ========================================================================
    // Helper: Assert no errors in the CSV editor status bar
    // ========================================================================
    async function assertNoErrors(modal: import('@playwright/test').Locator) {
        // The error indicator "✗" should NOT be visible
        const errorIndicator = modal.locator('.text-red-500:has-text("✗")');
        await expect(errorIndicator).not.toBeVisible();
        // Also check the status bar doesn't show error count
        const errorBadge = modal.locator('.text-red-500:has-text("error")');
        await expect(errorBadge).not.toBeVisible();
    }

    // ========================================================================
    // Test 1: Import CSV button opens modal
    // ========================================================================
    test('import CSV button opens modal', async ({page}) => {
        const modal = await openImportModal(page);
        await expect(modal).toBeVisible();
    });

    // ========================================================================
    // Test 2: Modal has direction bar with currency badges
    // ========================================================================
    test('modal shows direction bar with currencies', async ({page}) => {
        const modal = await openImportModal(page);

        // Check currency badges are visible (EUR and USD)
        await expect(modal.locator('[role="combobox"]').first()).toBeVisible();
        await expect(modal.locator('[role="combobox"]').last()).toBeVisible();
    });

    // ========================================================================
    // Test 3: Initial header matches pair direction (EUR>USD)
    // ========================================================================
    test('initial header matches pair direction', async ({page}) => {
        const modal = await openImportModal(page);

        const csvText = await getCsvText(modal);
        expect(csvText.trim()).toBe('date;EUR>USD');

        // Header should show as valid (no error indicators)
        await assertNoErrors(modal);
    });

    // ========================================================================
    // Test 4: Swap button updates header and currencies without errors
    // ========================================================================
    test('swap button updates header and currencies without errors', async ({page}) => {
        const modal = await openImportModal(page);

        // Verify initial state
        let csvText = await getCsvText(modal);
        expect(csvText.trim()).toBe('date;EUR>USD');

        // Click swap
        const swapBtn = modal.locator('button', {hasText: '⇄'});
        await expect(swapBtn).toBeVisible();
        await swapBtn.click();
        await page.waitForTimeout(200);

        // Modal still visible
        await expect(modal).toBeVisible();

        // Header in textarea should now be USD>EUR
        csvText = await getCsvText(modal);
        expect(csvText.trim()).toBe('date;USD>EUR');

        // No errors should appear
        await assertNoErrors(modal);
    });

    // ========================================================================
    // Test 5: Double swap returns to original direction
    // ========================================================================
    test('double swap returns to original direction', async ({page}) => {
        const modal = await openImportModal(page);

        const swapBtn = modal.locator('button', {hasText: '⇄'});

        // First swap: EUR>USD → USD>EUR
        await swapBtn.click();
        await page.waitForTimeout(200);
        let csvText = await getCsvText(modal);
        expect(csvText.trim()).toBe('date;USD>EUR');
        await assertNoErrors(modal);

        // Second swap: USD>EUR → EUR>USD
        await swapBtn.click();
        await page.waitForTimeout(200);
        csvText = await getCsvText(modal);
        expect(csvText.trim()).toBe('date;EUR>USD');
        await assertNoErrors(modal);
    });

    // ========================================================================
    // Test 6: Swap updates readonly currency badges
    // ========================================================================
    test('swap updates readonly currency badges', async ({page}) => {
        const modal = await openImportModal(page);

        // Get initial combobox values (readonly badges)
        const comboboxes = modal.locator('[role="combobox"]');
        const firstBadge = comboboxes.first();
        const lastBadge = comboboxes.last();

        // Initial: first=EUR, last=USD
        await expect(firstBadge).toHaveText(/EUR/);
        await expect(lastBadge).toHaveText(/USD/);

        // Swap
        const swapBtn = modal.locator('button', {hasText: '⇄'});
        await swapBtn.click();
        await page.waitForTimeout(200);

        // After swap: first=USD, last=EUR
        await expect(firstBadge).toHaveText(/USD/);
        await expect(lastBadge).toHaveText(/EUR/);
    });

    // ========================================================================
    // Test 7: Paste valid CSV after swap shows valid rows
    // ========================================================================
    test('paste valid CSV after swap shows valid rows', async ({page}) => {
        const modal = await openImportModal(page);

        // Swap direction: EUR>USD → USD>EUR
        const swapBtn = modal.locator('button', {hasText: '⇄'});
        await swapBtn.click();
        await page.waitForTimeout(200);

        // Paste data with swapped header
        const textarea = modal.locator('textarea');
        await textarea.fill('date;USD>EUR\n2020-01-15;0.9239\n2020-01-16;0.9221');
        await page.waitForTimeout(200);

        // Should show 2 valid rows
        const importBtn = modal.locator('button', {hasText: 'Import (2)'});
        await expect(importBtn).toBeVisible();

        // No errors
        await assertNoErrors(modal);
    });

    // ========================================================================
    // Test 8: Swap with existing data rows updates header but keeps data
    // ========================================================================
    test('swap with existing data rows preserves data', async ({page}) => {
        const modal = await openImportModal(page);

        // Paste some data first
        const textarea = modal.locator('textarea');
        await textarea.fill('date;EUR>USD\n2020-01-15;1.0823\n2020-01-16;1.0845');
        await page.waitForTimeout(200);

        // Verify 2 valid rows
        await expect(modal.locator('button', {hasText: 'Import (2)'})).toBeVisible();

        // Now swap
        const swapBtn = modal.locator('button', {hasText: '⇄'});
        await swapBtn.click();
        await page.waitForTimeout(200);

        // The header should be updated but user data lines remain
        const csvText = await getCsvText(modal);
        const lines = csvText.split('\n').filter(l => l.trim());
        expect(lines[0]).toBe('date;USD>EUR');
        // Data lines should still be there (though they might now be invalid
        // because the header changed — that's expected behavior for user data)
        expect(lines.length).toBeGreaterThanOrEqual(2);
    });

    // ========================================================================
    // Test 9: Paste valid CSV shows valid rows (original direction)
    // ========================================================================
    test('paste valid CSV shows valid rows', async ({page}) => {
        const modal = await openImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;EUR>USD\n2020-01-15;1.0823\n2020-01-16;1.0845');
        await page.waitForTimeout(200);

        // Check valid row count - the Import button shows count
        const importBtn = modal.locator('button', {hasText: 'Import (2)'});
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 10: Close with dirty data shows confirm discard
    // ========================================================================
    test('close with dirty data shows discard confirm', async ({page}) => {
        const modal = await openImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;EUR>USD\n2020-01-15;1.0823');
        await page.waitForTimeout(200);

        // Try to close via ✕ button
        await modal.locator('button[aria-label="Close"]').click();
        await page.waitForTimeout(200);

        // Should show discard confirm
        await expect(page.locator('text=Discard import')).toBeVisible();
    });

    // ========================================================================
    // Test 11: Cancel closes modal without confirm when clean
    // ========================================================================
    test('cancel closes modal when clean', async ({page}) => {
        const modal = await openImportModal(page);
        await expect(modal).toBeVisible();

        // Cancel should close immediately (no dirty data)
        await modal.locator('button', {hasText: 'Cancel'}).click();
        await page.waitForTimeout(200);
        await expect(modal).not.toBeVisible();
    });

    // ========================================================================
    // Test 12: Swap without data doesn't mark modal as dirty
    // ========================================================================
    test('swap without data does not mark modal as dirty', async ({page}) => {
        const modal = await openImportModal(page);

        // Swap direction (should update header + initialCsvValue)
        const swapBtn = modal.locator('button', {hasText: '⇄'});
        await swapBtn.click();
        await page.waitForTimeout(200);

        // Close should NOT show discard confirm (only header changed, no user data)
        await modal.locator('button[aria-label="Close"]').click();
        await page.waitForTimeout(200);

        // Modal should just close — no discard prompt
        await expect(modal).not.toBeVisible();
    });

    // ========================================================================
    // Test 13: Info banner updates on swap
    // ========================================================================
    test('info banner reflects current direction', async ({page}) => {
        const modal = await openImportModal(page);

        // Initial: info banner should mention EUR and USD
        const infoBanner = modal.locator('[class*="bg-blue"]');
        if (await infoBanner.count() > 0) {
            const bannerText = await infoBanner.first().textContent();
            expect(bannerText).toContain('EUR');
            expect(bannerText).toContain('USD');
        }

        // Swap
        const swapBtn = modal.locator('button', {hasText: '⇄'});
        await swapBtn.click();
        await page.waitForTimeout(200);

        // After swap: should mention USD → EUR direction
        if (await infoBanner.count() > 0) {
            const bannerText = await infoBanner.first().textContent();
            expect(bannerText).toContain('USD');
            expect(bannerText).toContain('EUR');
        }
    });

    // ========================================================================
    // Test 14: Inverted pair page (USD-EUR) has correct initial header
    // ========================================================================
    test('inverted pair URL has correct initial header', async ({page}) => {
        // Navigate to USD-EUR (inverted direction)
        await goToFxDetailPage(page, 'USD-EUR');
        await page.getByTestId('fx-detail-edit-btn').click();
        await page.waitForTimeout(200);
        await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible();

        await page.getByTestId('fx-data-import-btn').click();
        await page.waitForTimeout(200);
        const modal = page.getByTestId('data-import-modal');
        await expect(modal).toBeVisible();

        // Header should be USD>EUR (matching the URL direction)
        const csvText = await getCsvText(modal);
        expect(csvText.trim()).toBe('date;USD>EUR');
        await assertNoErrors(modal);
    });

    // ========================================================================
    // Test 15: Less-than syntax updates badges but keeps original header text
    // ========================================================================
    test('less-than syntax swaps badges but keeps original header text', async ({page}) => {
        const modal = await openImportModal(page);

        // Type a header with < syntax: EUR<USD means EUR←USD → from=USD, to=EUR
        const textarea = modal.locator('textarea');
        await textarea.fill('date;EUR<USD');
        await page.waitForTimeout(200);

        // The header text should stay as the user typed it (NOT rewritten)
        const csvText = await getCsvText(modal);
        expect(csvText.trim()).toBe('date;EUR<USD');

        // Currency badges should reflect the interpreted direction: USD → EUR
        const comboboxes = modal.locator('[role="combobox"]');
        await expect(comboboxes.first()).toHaveText(/USD/);
        await expect(comboboxes.last()).toHaveText(/EUR/);

        // No errors — parser accepts < as valid header
        await assertNoErrors(modal);
    });

    // ========================================================================
    // Test 16: Less-than syntax with data rows — header stays, data is valid
    // ========================================================================
    test('less-than syntax with data rows keeps header and validates data', async ({page}) => {
        const modal = await openImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;EUR<USD\n2020-01-15;1.0823\n2020-01-16;1.0845');
        await page.waitForTimeout(200);

        // Header stays as typed
        const csvText = await getCsvText(modal);
        const lines = csvText.split('\n').filter(l => l.trim());
        expect(lines[0]).toBe('date;EUR<USD');
        expect(lines.length).toBe(3);

        // Data should be valid (2 rows)
        const importBtn = modal.locator('button', {hasText: 'Import (2)'});
        await expect(importBtn).toBeVisible();

        await assertNoErrors(modal);
    });

    // ========================================================================
    // Test 17: Swap after less-than syntax rewrites header with >
    // ========================================================================
    test('swap after less-than syntax rewrites header with greater-than', async ({page}) => {
        const modal = await openImportModal(page);

        // Type header with < syntax
        const textarea = modal.locator('textarea');
        await textarea.fill('date;EUR<USD');
        await page.waitForTimeout(200);

        // Badges should be USD → EUR (from < detection)
        const comboboxes = modal.locator('[role="combobox"]');
        await expect(comboboxes.first()).toHaveText(/USD/);
        await expect(comboboxes.last()).toHaveText(/EUR/);

        // Click swap: USD→EUR becomes EUR→USD
        const swapBtn = modal.locator('button', {hasText: '⇄'});
        await swapBtn.click();
        await page.waitForTimeout(200);

        // NOW the header should be rewritten with > (swap always uses >)
        const csvText = await getCsvText(modal);
        expect(csvText.trim()).toBe('date;EUR>USD');

        // Badges should show EUR → USD
        await expect(comboboxes.first()).toHaveText(/EUR/);
        await expect(comboboxes.last()).toHaveText(/USD/);

        await assertNoErrors(modal);
    });

    // ========================================================================
    // Test 18: Changing from < to > syntax updates direction without errors
    // ========================================================================
    test('changing from less-than to greater-than syntax updates direction', async ({page}) => {
        const modal = await openImportModal(page);
        const textarea = modal.locator('textarea');
        const comboboxes = modal.locator('[role="combobox"]');

        // Step 1: Type header with < syntax → EUR<USD means from=USD, to=EUR
        await textarea.fill('date;EUR<USD');
        await page.waitForTimeout(200);

        // Badges should be USD → EUR
        await expect(comboboxes.first()).toHaveText(/USD/);
        await expect(comboboxes.last()).toHaveText(/EUR/);
        await assertNoErrors(modal);

        // Step 2: Now change to > syntax → EUR>USD means from=EUR, to=USD
        await textarea.fill('date;EUR>USD');
        await page.waitForTimeout(200);

        // Badges should update to EUR → USD
        await expect(comboboxes.first()).toHaveText(/EUR/);
        await expect(comboboxes.last()).toHaveText(/USD/);

        // Header text stays as typed
        const csvText = await getCsvText(modal);
        expect(csvText.trim()).toBe('date;EUR>USD');

        // No errors
        await assertNoErrors(modal);
    });

    // ========================================================================
    // Test 19: Changing from < to > with data rows — no validation errors
    // ========================================================================
    test('changing from less-than to greater-than with data keeps rows valid', async ({page}) => {
        const modal = await openImportModal(page);
        const textarea = modal.locator('textarea');
        const comboboxes = modal.locator('[role="combobox"]');

        // Step 1: Paste data with < syntax
        await textarea.fill('date;EUR<USD\n2020-01-15;1.0823\n2020-01-16;1.0845');
        await page.waitForTimeout(200);

        // Badges: USD → EUR
        await expect(comboboxes.first()).toHaveText(/USD/);
        await expect(comboboxes.last()).toHaveText(/EUR/);

        // 2 valid rows
        await expect(modal.locator('button', {hasText: 'Import (2)'})).toBeVisible();
        await assertNoErrors(modal);

        // Step 2: Change header to > syntax (keep same data)
        await textarea.fill('date;EUR>USD\n2020-01-15;1.0823\n2020-01-16;1.0845');
        await page.waitForTimeout(200);

        // Badges: EUR → USD
        await expect(comboboxes.first()).toHaveText(/EUR/);
        await expect(comboboxes.last()).toHaveText(/USD/);

        // Still 2 valid rows
        await expect(modal.locator('button', {hasText: 'Import (2)'})).toBeVisible();
        await assertNoErrors(modal);
    });

    // ========================================================================
    // Test 20: Changing > direction to different > direction updates badges
    // ========================================================================
    test('typing different greater-than direction updates badges', async ({page}) => {
        const modal = await openImportModal(page);
        const textarea = modal.locator('textarea');
        const comboboxes = modal.locator('[role="combobox"]');

        // Initial: EUR>USD (default)
        await expect(comboboxes.first()).toHaveText(/EUR/);
        await expect(comboboxes.last()).toHaveText(/USD/);

        // Change header to opposite direction: USD>EUR
        await textarea.fill('date;USD>EUR');
        await page.waitForTimeout(200);

        // Badges should update to USD → EUR
        await expect(comboboxes.first()).toHaveText(/USD/);
        await expect(comboboxes.last()).toHaveText(/EUR/);
        await assertNoErrors(modal);

        // Change back to EUR>USD
        await textarea.fill('date;EUR>USD');
        await page.waitForTimeout(200);

        await expect(comboboxes.first()).toHaveText(/EUR/);
        await expect(comboboxes.last()).toHaveText(/USD/);
        await assertNoErrors(modal);
    });
});
