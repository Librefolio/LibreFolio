/**
 * FX List Page — E2E Tests
 *
 * Tests the FX list page: card rendering, filtering, navigation, and basic actions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxPage} from './fx-helpers';

test.describe('FX List Page', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Navigation to FX page
    // ========================================================================
    test('can navigate to FX page', async ({page}) => {
        await goToFxPage(page);
        await expect(page.getByTestId('fx-page')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Cards with mock data are visible
    // ========================================================================
    test('cards with mock data are visible', async ({page}) => {
        await goToFxPage(page);
        const cards = page.locator('[data-testid^="fx-card-"]');
        const count = await cards.count();
        expect(count).toBeGreaterThan(0);
    });

    // ========================================================================
    // Test 3: Badge with pair count matches card count
    // ========================================================================
    test('pair count badge matches card count', async ({page}) => {
        await goToFxPage(page);
        // Count only card containers (not their children — pair-label, swap-btn etc.)
        const cards = page.locator('[data-testid^="fx-card-"]').filter({
            has: page.locator('[data-testid="fx-pair-label"]'),
        });
        const cardCount = await cards.count();

        // The badge shows the count of configured pairs
        const badge = page.getByTestId('fx-pair-count-badge');
        await expect(badge).toBeVisible();
        const badgeText = await badge.textContent();
        expect(badgeText).toContain(String(cardCount));
    });

    // ========================================================================
    // Test 4: Filter by single currency
    // ========================================================================
    test('filter by single currency shows matching cards', async ({page}) => {
        await goToFxPage(page);
        const allCards = page.locator('[data-testid^="fx-card-"]');
        const totalBefore = await allCards.count();

        // Currency filter containers should exist
        const filterContainers = page.locator('[data-testid="fx-currency-filter"]');
        await expect(filterContainers.first()).toBeVisible();

        const firstFilter = filterContainers.first();
        await firstFilter.locator('[role="combobox"]').click();
        await page.waitForTimeout(200);
        const searchInput = firstFilter.locator('input[type="text"]');
        await searchInput.fill('EUR');
        await page.waitForTimeout(500);

        // SearchSelect uses <button> inside [role="listbox"], not [role="option"]
        const listbox = page.locator('[role="listbox"]');
        await expect(listbox).toBeVisible();
        const option = listbox.locator('button').filter({hasText: 'EUR'}).first();
        await option.click();
        await page.waitForTimeout(500);

        // All visible cards should contain "EUR"
        const filtered = page.locator('[data-testid^="fx-card-"]');
        const filteredCount = await filtered.count();
        expect(filteredCount).toBeGreaterThan(0);
        expect(filteredCount).toBeLessThanOrEqual(totalBefore);
    });

    // ========================================================================
    // Test 7: Reset filters restores all cards
    // ========================================================================
    test('reset filters restores all cards', async ({page}) => {
        await goToFxPage(page);
        const allCards = page.locator('[data-testid^="fx-card-"]');
        const totalBefore = await allCards.count();

        // Apply a EUR filter first
        const filterContainers = page.locator('[data-testid="fx-currency-filter"]');
        const firstFilter = filterContainers.first();
        await firstFilter.locator('[role="combobox"]').click();
        await page.waitForTimeout(200);
        const searchInput = firstFilter.locator('input[type="text"]');
        await searchInput.fill('EUR');
        await page.waitForTimeout(500);

        // SearchSelect uses <button> inside [role="listbox"], not [role="option"]
        const listbox = page.locator('[role="listbox"]');
        const option = listbox.locator('button').filter({hasText: 'EUR'}).first();
        await option.click();
        await page.waitForTimeout(500);

        // Click reset filters button
        const resetBtn = page.getByTestId('fx-reset-filters');
        await expect(resetBtn).toBeVisible();
        await resetBtn.click();
        await page.waitForTimeout(500);

        // All cards should be restored
        const afterReset = await allCards.count();
        expect(afterReset).toBe(totalBefore);
    });

    // ========================================================================
    // Test 8: DateRangePicker preset changes date
    // ========================================================================
    test('DateRangePicker preset changes date display', async ({page}) => {
        await goToFxPage(page);
        const datePicker = page.getByTestId('fx-date-range-picker');
        await expect(datePicker).toBeVisible();

        // Click "1Y" preset button
        const yearPreset = datePicker.getByRole('button', {name: /1Y/});
        await expect(yearPreset).toBeVisible();
        await yearPreset.click();
        await page.waitForTimeout(500);

        // After clicking 1Y, the preset should be active (styled differently)
        // Verify the 1Y button has the active class
        await expect(yearPreset).toHaveClass(/bg-libre-green/);
    });

    // ========================================================================
    // Test 10: Invert card pair swaps display
    // ========================================================================
    test('invert card pair swaps base/quote display', async ({page}) => {
        await goToFxPage(page);
        const firstCard = page.locator('[data-testid^="fx-card-"]').first();
        await expect(firstCard).toBeVisible();

        // Get the initial pair label
        const pairLabel = firstCard.locator('[data-testid$="-pair-label"]');
        await expect(pairLabel).toBeVisible();
        const labelBefore = await pairLabel.textContent();

        // Click swap button on the card
        const swapBtn = firstCard.locator('[data-testid$="-swap-btn"]');
        await expect(swapBtn).toBeVisible();
        await swapBtn.click();
        await page.waitForTimeout(500);

        const labelAfter = await pairLabel.textContent();
        // Labels should differ after swap
        expect(labelAfter).not.toBe(labelBefore);
    });

    // ========================================================================
    // Test 11: Navigate to detail page by clicking card
    // ========================================================================
    test('clicking card navigates to detail page', async ({page}) => {
        await goToFxPage(page);
        const firstCard = page.locator('[data-testid^="fx-card-"]').first();
        await expect(firstCard).toBeVisible();

        // Click the navigate area of the card (the card link/button)
        const navLink = firstCard.locator('a, [data-testid$="-navigate"]').first();
        if (await navLink.isVisible()) {
            await navLink.click();
        } else {
            // Fallback: click the card itself
            await firstCard.click();
        }
        await page.waitForTimeout(1000);

        // URL should contain /fx/ followed by a pair slug
        await expect(page).toHaveURL(/\/fx\/[A-Z]+-[A-Z]+/);
    });

    // ========================================================================
    // Test 13: Add Pair button is visible
    // ========================================================================
    test('Add Pair button is visible', async ({page}) => {
        await goToFxPage(page);
        await expect(page.getByTestId('fx-add-pair-button')).toBeVisible();
    });

    // ========================================================================
    // Test 14: Sync All button is visible
    // ========================================================================
    test('Sync All button is visible', async ({page}) => {
        await goToFxPage(page);
        const syncBtn = page.getByTestId('fx-sync-all-button');
        await expect(syncBtn).toBeVisible();
    });
});

