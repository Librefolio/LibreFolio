/**
 * FX Add Pair Modal — E2E Tests
 *
 * Tests for FX pair creation modal: currency selection, route discovery, save.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxPage, openAddPairModal, selectCurrency} from './fx-helpers';

test.describe('FX Add Pair Modal', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Open modal
    // ========================================================================
    test('can open add pair modal', async ({page}) => {
        await goToFxPage(page);
        await openAddPairModal(page);
        await expect(page.getByTestId('fx-add-pair-modal')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Two currency selects visible
    // ========================================================================
    test('modal has two currency selects', async ({page}) => {
        await goToFxPage(page);
        await openAddPairModal(page);
        const modal = page.getByTestId('fx-add-pair-modal');
        const comboboxes = modal.locator('[role="combobox"]');
        const count = await comboboxes.count();
        expect(count).toBeGreaterThanOrEqual(2);
    });

    // ========================================================================
    // Test 3: Save disabled without currencies
    // ========================================================================
    test('save button is disabled without currencies selected', async ({page}) => {
        await goToFxPage(page);
        await openAddPairModal(page);
        const saveBtn = page.getByTestId('fx-add-pair-save');
        await expect(saveBtn).toBeDisabled();
    });

    // ========================================================================
    // Test 4: Close via Escape (no dirty state)
    // ========================================================================
    test('escape closes modal when not dirty', async ({page}) => {
        await goToFxPage(page);
        await openAddPairModal(page);
        await page.keyboard.press('Escape');
        await expect(page.getByTestId('fx-add-pair-modal')).not.toBeVisible();
    });

    // ========================================================================
    // Test 5: Selecting currencies shows route section
    // ========================================================================
    test('selecting currencies shows route section', async ({page}) => {
        await goToFxPage(page);
        await openAddPairModal(page);
        const modal = page.getByTestId('fx-add-pair-modal');

        // Select EUR as base
        const baseContainer = modal.locator('[data-testid="fx-add-pair-base"]');
        if (await baseContainer.isVisible()) {
            await selectCurrency(page, baseContainer, 'EUR');
        }

        // Select CAD as quote (should have ECB route)
        const quoteContainer = modal.locator('[data-testid="fx-add-pair-quote"]');
        if (await quoteContainer.isVisible()) {
            await selectCurrency(page, quoteContainer, 'CAD');
            await page.waitForTimeout(1000);

            // Route section should appear
            const routeSection = page.getByTestId('fx-route-select');
            await expect(routeSection).toBeVisible({timeout: 5000});
        }
    });
});

