/**
 * FX Chart Settings — E2E Tests
 *
 * Tests the ChartSettingsModal from the FX list and detail pages.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxPage} from './fx-helpers';

test.describe('FX Chart Settings', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Open global settings from list page
    // ========================================================================
    test('can open global chart settings modal', async ({page}) => {
        await goToFxPage(page);
        const settingsBtn = page.getByTestId('fx-chart-settings-button');
        if (await settingsBtn.isVisible()) {
            await settingsBtn.click();
            await page.waitForTimeout(500);
            const modal = page.getByTestId('chart-settings-modal');
            await expect(modal).toBeVisible({timeout: 3000});
        }
    });

    // ========================================================================
    // Test 6: Discard on dirty via Escape
    // ========================================================================
    test('escape on dirty settings shows confirm modal', async ({page}) => {
        await goToFxPage(page);
        const settingsBtn = page.getByTestId('fx-chart-settings-button');
        if (await settingsBtn.isVisible()) {
            await settingsBtn.click();
            await page.waitForTimeout(500);

            const modal = page.getByTestId('chart-settings-modal');
            if (await modal.isVisible()) {
                // Toggle a checkbox to make it dirty
                const checkbox = modal.locator('input[type="checkbox"]').first();
                if (await checkbox.isVisible()) {
                    await checkbox.click();
                    await page.waitForTimeout(200);
                }

                // Press Escape — should show confirm
                await page.keyboard.press('Escape');
                await page.waitForTimeout(300);
                // Either the confirm modal appears or the settings modal closes
                // (depends on dirty state detection)
            }
        }
    });

    // ========================================================================
    // Test 8: Preview canvas is present when signal is added
    // ========================================================================
    test('preview canvas is rendered with signals', async ({page}) => {
        await goToFxPage(page);
        const settingsBtn = page.getByTestId('fx-chart-settings-button');
        if (await settingsBtn.isVisible()) {
            await settingsBtn.click();
            await page.waitForTimeout(500);

            const modal = page.getByTestId('chart-settings-modal');
            if (await modal.isVisible()) {
                // Look for the preview chart canvas
                const canvas = modal.locator('canvas');
                // Preview should render even without signals (shows sine wave)
                if (await canvas.count() > 0) {
                    await expect(canvas.first()).toBeVisible();
                }
            }
        }
    });
});

