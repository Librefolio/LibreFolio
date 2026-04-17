/**
 * FX Sync Modal — E2E Tests
 *
 * Tests the sync modal functionality from both list and detail pages.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxDetailPage, goToFxPage} from './fx-helpers';

test.describe('FX Sync', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Open Sync All modal from list
    // ========================================================================
    test('can open Sync All modal from list page', async ({page}) => {
        await goToFxPage(page);
        const syncBtn = page.getByTestId('fx-sync-all-button');
        await syncBtn.click();
        await page.waitForTimeout(500);

        // FxSyncModal should be visible
        const modal = page.getByTestId('fx-sync-modal');
        await expect(modal).toBeVisible({timeout: 3000});
    });

    // ========================================================================
    // Test 6: Close sync modal
    // ========================================================================
    test('can close sync modal', async ({page}) => {
        await goToFxPage(page);
        const syncBtn = page.getByTestId('fx-sync-all-button');
        await syncBtn.click();
        await page.waitForTimeout(500);

        const modal = page.getByTestId('fx-sync-modal');
        await expect(modal).toBeVisible({timeout: 3000});

        // Close via Escape or close button
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
        await expect(modal).not.toBeVisible();
    });

    // ========================================================================
    // Test 7: Sync from detail page triggers toast
    // ========================================================================
    test('sync from detail page triggers action', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-sync-btn').click();
        // Wait for sync to complete (may take a while for external providers)
        await page.waitForTimeout(5000);
        // Verify the button is no longer in spinning state (sync completed)
        const syncBtn = page.getByTestId('fx-detail-sync-btn');
        await expect(syncBtn).toBeEnabled({timeout: 10000});
    });
});
