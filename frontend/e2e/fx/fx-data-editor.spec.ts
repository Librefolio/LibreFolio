/**
 * FX Data Editor — E2E Tests
 *
 * Tests the data editor section in the FX detail page.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated with EUR-USD data
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxDetailPage} from './fx-helpers';

test.describe('FX Data Editor', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Open editor via edit button
    // ========================================================================
    test('can open data editor', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-edit-btn').click();
        await page.waitForTimeout(500);
        await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Data table has rows
    // ========================================================================
    test('data editor table has rows', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-edit-btn').click();
        await page.waitForTimeout(1000);
        const editorPanel = page.getByTestId('fx-detail-editor-panel');
        await expect(editorPanel).toBeVisible();

        // Look for table rows within the editor
        const rows = editorPanel.locator('table tbody tr, [data-testid*="editor-row"]');
        const count = await rows.count();
        expect(count).toBeGreaterThan(0);
    });

    // ========================================================================
    // Test 7: Close editor (cancel) resets state
    // ========================================================================
    test('closing editor hides the panel', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-edit-btn').click();
        await page.waitForTimeout(500);
        await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible();

        // Click the edit button again to close (toggle)
        await page.getByTestId('fx-detail-edit-btn').click();
        await page.waitForTimeout(500);
        await expect(page.getByTestId('fx-detail-editor-panel')).not.toBeVisible();
    });
});
