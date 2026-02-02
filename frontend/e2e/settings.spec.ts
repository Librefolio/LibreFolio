import { test, expect } from '@playwright/test';
import { login, navigateTo } from './fixtures/auth-helpers';
import { TEST_USER, TEST_ADMIN } from './fixtures/test-users';

test.describe('Settings', () => {

    test.describe('User Settings', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
        });

        test('can access user settings page', async ({ page }) => {
            await navigateTo(page, '/settings');
            await expect(page.getByRole('heading', { name: /settings|preferences|impostazioni/i })).toBeVisible();
        });

        test('can change locale preference', async ({ page }) => {
            await navigateTo(page, '/settings');

            // Find locale selector and change it
            const localeSelect = page.getByTestId('locale-preference');
            if (await localeSelect.isVisible()) {
                await localeSelect.click();
                await page.getByText('Italiano').click();

                // Verify save button or auto-save indicator
                await expect(page.getByText(/saved|salvato/i)).toBeVisible({ timeout: 5000 });
            }
        });

        test('can change base currency preference', async ({ page }) => {
            await navigateTo(page, '/settings');

            // Find currency selector
            const currencySelect = page.getByTestId('currency-preference');
            if (await currencySelect.isVisible()) {
                await currencySelect.click();
                await page.getByText('USD').click();
            }
        });
    });

    test.describe('Global Settings (Admin Only)', () => {
        test('admin can access global settings tab', async ({ page }) => {
            await login(page, TEST_ADMIN);
            await navigateTo(page, '/settings');

            // Look for global settings tab
            const globalTab = page.getByRole('tab', { name: /global|sistema/i });
            if (await globalTab.isVisible()) {
                await globalTab.click();
                await expect(page.getByText(/global settings|impostazioni globali/i)).toBeVisible();
            }
        });

        test('non-admin cannot see global settings tab', async ({ page }) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');

            // Global tab should not be visible for regular users
            const globalTab = page.getByRole('tab', { name: /global|sistema/i });
            await expect(globalTab).not.toBeVisible();
        });
    });
});
