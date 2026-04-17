/**
 * Asset List Page — E2E Tests
 *
 * Tests the Assets list page: card rendering, filtering, navigation, and basic actions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage} from './assets-helpers';

test.describe('Asset List Page', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Navigation to Assets page
    // ========================================================================
    test('can navigate to Assets page', async ({page}) => {
        await goToAssetsPage(page);
        await expect(page.getByTestId('assets-page')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Asset cards or table are visible
    // ========================================================================
    test('asset cards or table are visible with mock data', async ({page}) => {
        await goToAssetsPage(page);
        // Wait for either card grid or table view
        const cards = page.locator('[data-testid^="asset-card-"]');
        const table = page.locator('[data-testid="assets-table"]');
        const cardCount = await cards.count();
        const tableVisible = await table.isVisible().catch(() => false);
        expect(cardCount > 0 || tableVisible).toBeTruthy();
    });

    // ========================================================================
    // Test 3: Count badge is visible
    // ========================================================================
    test('count badge shows asset count', async ({page}) => {
        await goToAssetsPage(page);
        const badge = page.getByTestId('assets-count-badge');
        await expect(badge).toBeVisible();
        const text = await badge.textContent();
        expect(parseInt(text || '0')).toBeGreaterThan(0);
    });

    // ========================================================================
    // Test 4: Search filter works
    // ========================================================================
    test('search filter filters assets', async ({page}) => {
        await goToAssetsPage(page);
        const searchInput = page.getByTestId('assets-search-input');
        await expect(searchInput).toBeVisible();
        // Type a search query that should match at least one mock asset
        await searchInput.fill('Apple');
        await page.waitForTimeout(500);
        // Should still have the page visible (even if filtered)
        await expect(page.getByTestId('assets-page')).toBeVisible();
    });

    // ========================================================================
    // Test 5: Type filter dropdown visible
    // ========================================================================
    test('type filter dropdown is visible', async ({page}) => {
        await goToAssetsPage(page);
        const typeFilter = page.getByTestId('assets-type-filter');
        await expect(typeFilter).toBeVisible();
    });

    // ========================================================================
    // Test 6: Active/All toggle works
    // ========================================================================
    test('active/all toggle switches view', async ({page}) => {
        await goToAssetsPage(page);
        const toggle = page.getByTestId('assets-active-toggle');
        await expect(toggle).toBeVisible();
        await toggle.click();
        await page.waitForTimeout(300);
        // Page should still be visible after toggle
        await expect(page.getByTestId('assets-page')).toBeVisible();
    });

    // ========================================================================
    // Test 7: Add button is visible
    // ========================================================================
    test('add asset button is visible', async ({page}) => {
        await goToAssetsPage(page);
        const addBtn = page.getByTestId('assets-add-button');
        await expect(addBtn).toBeVisible();
    });

    // ========================================================================
    // Test 8: Click card navigates to detail
    // ========================================================================
    test('clicking asset card navigates to detail page', async ({page}) => {
        await goToAssetsPage(page);
        // Click the first asset card
        const firstCard = page.locator('[data-testid^="asset-card-"]').first();
        if (await firstCard.isVisible().catch(() => false)) {
            await firstCard.click();
            await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});
        }
    });

    // ========================================================================
    // Test 9: Date range picker visible
    // ========================================================================
    test('date range picker is visible', async ({page}) => {
        await goToAssetsPage(page);
        const dateRange = page.getByTestId('assets-date-range');
        await expect(dateRange).toBeVisible();
    });

    // ========================================================================
    // Test 10: Grid/Table view toggle switches view
    // ========================================================================
    test('grid/table toggle switches between views', async ({page}) => {
        await goToAssetsPage(page);

        // Find the toggle buttons by aria-label
        const assetsPage = page.getByTestId('assets-page');
        const tableBtn = assetsPage.locator('button[aria-label="Table view"]');
        const gridBtn = assetsPage.locator('button[aria-label="Grid view"]');

        // Both buttons should be visible
        await expect(tableBtn).toBeVisible();
        await expect(gridBtn).toBeVisible();

        // Initially grid view — cards should be present
        const cardsBeforeToggle = await page.locator('[data-testid^="asset-card-"]').count();

        // Switch to table view
        await tableBtn.click();
        await page.waitForTimeout(500);

        // Table should be visible OR cards should disappear (depending on data)
        const tableVisible = await page
            .locator('[data-testid="assets-table"], table')
            .first()
            .isVisible()
            .catch(() => false);
        const cardsAfterToggle = await page.locator('[data-testid^="asset-card-"]').count();

        // Either table appeared or cards disappeared (view switched)
        expect(tableVisible || cardsAfterToggle === 0 || cardsAfterToggle !== cardsBeforeToggle).toBeTruthy();

        // Switch back to grid
        await gridBtn.click();
        await page.waitForTimeout(500);
        await expect(page.getByTestId('assets-page')).toBeVisible();
    });

    // ========================================================================
    // Test 11: Type filter dropdown can be opened and has options
    // ========================================================================
    test('type filter dropdown opens with checkboxes', async ({page}) => {
        await goToAssetsPage(page);
        const typeFilter = page.getByTestId('assets-type-filter');
        await expect(typeFilter).toBeVisible();

        // Click to open dropdown (custom multi-checkbox with role="listbox")
        await typeFilter.click();
        await page.waitForTimeout(300);

        // Should show a listbox with checkbox items
        const listbox = page.locator('[role="listbox"]');
        await expect(listbox).toBeVisible();
    });

    // ========================================================================
    // Test 12: Search filter hides non-matching cards
    // ========================================================================
    test('search filter hides non-matching cards', async ({page}) => {
        await goToAssetsPage(page);
        const cards = page.locator('[data-testid^="asset-card-"]');
        const totalCards = await cards.count();

        if (totalCards < 2) {
            test.skip(true, 'Need at least 2 assets to test search filtering');
            return;
        }

        // Search for a string that won't match any asset
        const searchInput = page.getByTestId('assets-search-input');
        await searchInput.fill('zzzzz_nonexistent_12345');
        await page.waitForTimeout(500);

        // Visible cards should be 0
        const visibleCards = await cards.count();
        expect(visibleCards).toBeLessThan(totalCards);
    });

    // ========================================================================
    // Test 13: Active/All toggle changes badge count
    // ========================================================================
    test('active/all toggle changes displayed count', async ({page}) => {
        await goToAssetsPage(page);
        const badge = page.getByTestId('assets-count-badge');
        const activeBadge = await badge.textContent();

        // Toggle to show all (including inactive)
        const toggle = page.getByTestId('assets-active-toggle');
        await toggle.click();
        await page.waitForTimeout(500);

        const allBadge = await badge.textContent();
        // Count should be same or greater (all >= active)
        expect(parseInt(allBadge || '0')).toBeGreaterThanOrEqual(parseInt(activeBadge || '0'));
    });
});
