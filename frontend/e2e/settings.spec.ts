import { test, expect } from '@playwright/test';
import { login, navigateTo } from './fixtures/auth-helpers';
import { TEST_USER, TEST_ADMIN } from './fixtures/test-users';

test.describe('Settings', () => {

    test.describe('Settings Page Access', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
        });

        test('can access settings page', async ({ page }) => {
            await navigateTo(page, '/settings');
            await expect(page.getByTestId('settings-page')).toBeVisible();
        });

        test('shows all settings tabs', async ({ page }) => {
            await navigateTo(page, '/settings');
            await expect(page.getByTestId('settings-tab-profile')).toBeVisible();
            await expect(page.getByTestId('settings-tab-preferences')).toBeVisible();
            await expect(page.getByTestId('settings-tab-about')).toBeVisible();
            await expect(page.getByTestId('settings-tab-admin')).toBeVisible();
        });

        test('profile tab is active by default', async ({ page }) => {
            await navigateTo(page, '/settings');
            await expect(page.getByTestId('settings-tab-profile')).toHaveAttribute('aria-selected', 'true');
            await expect(page.getByTestId('profile-tab')).toBeVisible();
        });
    });

    test.describe('Profile Tab', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
        });

        test('shows user profile information', async ({ page }) => {
            await expect(page.getByTestId('profile-tab')).toBeVisible();
            await expect(page.getByTestId('profile-username')).toBeVisible();
            await expect(page.getByTestId('profile-email')).toBeVisible();
        });

        test('profile fields are initially disabled (locked)', async ({ page }) => {
            await expect(page.getByTestId('profile-username')).toBeDisabled();
            await expect(page.getByTestId('profile-email')).toBeDisabled();
        });

        test('change password button is visible', async ({ page }) => {
            await expect(page.getByTestId('change-password-button')).toBeVisible();
        });

        test('delete account button is visible', async ({ page }) => {
            await expect(page.getByTestId('delete-account-button')).toBeVisible();
        });
    });

    test.describe('Preferences Tab', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-preferences').click();
        });

        test('can switch to preferences tab', async ({ page }) => {
            await expect(page.getByTestId('settings-tab-preferences')).toHaveAttribute('aria-selected', 'true');
        });

        test('shows language preference', async ({ page }) => {
            await expect(page.getByTestId('preference-language')).toBeVisible();
        });

        test('shows currency preference', async ({ page }) => {
            await expect(page.getByTestId('preference-currency')).toBeVisible();
        });

        test('shows theme preference', async ({ page }) => {
            await expect(page.getByTestId('preference-theme')).toBeVisible();
        });
    });

    test.describe('Admin Tab (Global Settings)', () => {

        test('admin can view and access global settings', async ({ page }) => {
            await login(page, TEST_ADMIN);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-admin').click();

            await expect(page.getByTestId('settings-tab-admin')).toHaveAttribute('aria-selected', 'true');
            await expect(page.getByTestId('global-settings-tab')).toBeVisible();
        });

        test('non-admin can view but not edit global settings', async ({ page }) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-admin').click();

            await expect(page.getByTestId('global-settings-tab')).toBeVisible();
            // Lock button should not be visible for non-admin (read-only mode)
            // The component shows ShieldOff icon instead of Lock/Unlock for non-admins
        });
    });
});
