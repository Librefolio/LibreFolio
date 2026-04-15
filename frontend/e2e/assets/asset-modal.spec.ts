/**
 * Asset Modal — E2E Tests
 *
 * Tests the AssetModal: create, edit, search, provider section, distributions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage, openCreateAssetModal} from './assets-helpers';

test.describe('Asset Modal', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Create modal opens and closes
    // ========================================================================
    test('create modal opens and closes', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        await expect(page.getByTestId('asset-modal-form')).toBeVisible();
        // Close with cancel
        await page.getByTestId('asset-modal-cancel').click();
        await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 3000});
    });

    // ========================================================================
    // Test 2: Display name input accepts text
    // ========================================================================
    test('display name input accepts text', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        const nameInput = page.getByTestId('asset-modal-display-name');
        await expect(nameInput).toBeVisible();
        await nameInput.fill('Test Asset E2E');
        await expect(nameInput).toHaveValue('Test Asset E2E');
    });

    // ========================================================================
    // Test 3: Save button disabled when form invalid
    // ========================================================================
    test('save button disabled when name is empty', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        const saveBtn = page.getByTestId('asset-modal-save');
        // Clear display name (should be empty initially for create)
        const nameInput = page.getByTestId('asset-modal-display-name');
        await nameInput.fill('');
        await expect(saveBtn).toBeDisabled();
    });

    // ========================================================================
    // Test 4: Create basic asset (name + currency)
    // ========================================================================
    test('can create basic asset with name and currency', async ({page}) => {
        await goToAssetsPage(page);
        const countBefore = await page.getByTestId('assets-count-badge').textContent();

        await openCreateAssetModal(page);
        const nameInput = page.getByTestId('asset-modal-display-name');
        await nameInput.fill(`E2E Test Asset ${Date.now()}`);

        // Save
        const saveBtn = page.getByTestId('asset-modal-save');
        await expect(saveBtn).toBeEnabled({timeout: 3000});
        await saveBtn.click();

        // Modal should close
        await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 10_000});

        // Page should still be visible
        await expect(page.getByTestId('assets-page')).toBeVisible();
    });

    // ========================================================================
    // Test 5: Edit modal shows pre-populated fields
    // ========================================================================
    test('edit modal shows pre-populated display name', async ({page}) => {
        await goToAssetsPage(page);
        // Navigate to first asset detail
        const firstCard = page.locator('[data-testid^="asset-card-"]').first();
        if (!await firstCard.isVisible({timeout: 5000}).catch(() => false)) {
            test.skip(true, 'No assets available');
            return;
        }
        await firstCard.click();
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});

        // Open edit modal
        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});

        // Display name should be pre-filled (not empty)
        const nameInput = page.getByTestId('asset-modal-display-name');
        const value = await nameInput.inputValue();
        expect(value.length).toBeGreaterThan(0);

        // Close
        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 6: Modal has save and cancel buttons
    // ========================================================================
    test('modal has save and cancel buttons', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        await expect(page.getByTestId('asset-modal-save')).toBeVisible();
        await expect(page.getByTestId('asset-modal-cancel')).toBeVisible();
        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 7: Smart search input is visible in create modal
    // ========================================================================
    test('smart search input is visible in create modal', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);

        // Search input with placeholder "Search by name, ticker, ISIN..."
        const searchInput = page.locator('input[placeholder*="Search by name"]');
        await expect(searchInput).toBeVisible();

        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 8: Smart search triggers on typing (shows loading or results)
    // ========================================================================
    test('smart search triggers on typing', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);

        const searchInput = page.locator('input[placeholder*="Search by name"]');
        await searchInput.fill('Apple');
        await page.waitForTimeout(1500);

        // Should show either results dropdown, loading spinner, or "no results"
        const form = page.getByTestId('asset-modal-form');
        const hasDropdown = await form.locator('.shadow-lg, [class*="shadow-lg"]').first().isVisible().catch(() => false);
        const hasLoading = await form.locator('.animate-spin').first().isVisible().catch(() => false);

        // At least one of: results dropdown appeared or loading showed
        expect(hasDropdown || hasLoading).toBeTruthy();

        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 9: Edit modal has more fields than create
    // ========================================================================
    test('edit modal shows additional fields (currency, type)', async ({page}) => {
        await goToAssetsPage(page);
        const firstCard = page.locator('[data-testid^="asset-card-"]').first();
        if (!await firstCard.isVisible({timeout: 5000}).catch(() => false)) {
            test.skip(true, 'No assets available');
            return;
        }
        await firstCard.click();
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});

        // Open edit modal
        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});

        const form = page.getByTestId('asset-modal-form');

        // Should have display name pre-filled
        const nameInput = page.getByTestId('asset-modal-display-name');
        const value = await nameInput.inputValue();
        expect(value.length).toBeGreaterThan(0);

        // Should have currency selector (combobox or select with currency code)
        const hasCurrency = await form.locator('[role="combobox"], select').first().isVisible().catch(() => false);
        expect(hasCurrency).toBeTruthy();

        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 10: Modal scrolls without layout break
    // ========================================================================
    test('modal form is scrollable', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);

        const form = page.getByTestId('asset-modal-form');
        await expect(form).toBeVisible();

        // Form should have overflow-y-auto (scrollable when content exceeds max-height)
        const overflowY = await form.evaluate(el => getComputedStyle(el).overflowY);
        expect(overflowY).toBe('auto');

        await page.getByTestId('asset-modal-cancel').click();
    });
});

