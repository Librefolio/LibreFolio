/**
 * FX Sync Modal — E2E Tests
 *
 * Tests the sync modal functionality from both list and detail pages.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated
 */

import {expect, test} from '../fixtures/playwright';
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

        const modal = page.getByTestId('fx-sync-modal');
        await expect(modal).toBeVisible({timeout: 3000});

        // Close via Escape or close button
        await page.keyboard.press('Escape');
        await expect(modal).not.toBeVisible();
    });

    // ========================================================================
    // Test 7: Sync from detail page triggers toast
    // ========================================================================
    test('sync from detail page triggers action', async ({page}) => {
        // A real provider round-trip for every pair on the page; the default 30s
        // budget is spent before the sync answers.
        test.setTimeout(120_000);
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-sync-btn').click();
        // The detail page opens the *page* sync modal (assets + FX for this page);
        // `fx-sync-modal` is the list page's.
        const syncModal = page.getByTestId('page-sync-modal');
        await expect(syncModal).toBeVisible({timeout: 10_000});

        // "Still enabled" is true before the click too, so it cannot be the
        // barrier. The summary banner is what marks the end of the sync — the
        // modal reports in place and raises no toast.
        await syncModal.getByTestId('sync-modal-start').click();
        await expect(syncModal.getByTestId('sync-modal-results')).toBeVisible({timeout: 60_000});

        await syncModal.getByTestId('sync-modal-close').click();
        const syncBtn = page.getByTestId('fx-detail-sync-btn');
        await expect(syncBtn).toBeEnabled({timeout: 10_000});
    });
});
