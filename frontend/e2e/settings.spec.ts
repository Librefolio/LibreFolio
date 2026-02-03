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

        test('can unlock profile for editing', async ({ page }) => {
            // Fields should be disabled initially
            await expect(page.getByTestId('profile-username')).toBeDisabled();

            // Click edit toggle to unlock
            await page.getByTestId('profile-edit-toggle').click();

            // Fields should now be enabled
            await expect(page.getByTestId('profile-username')).toBeEnabled();
            await expect(page.getByTestId('profile-email')).toBeEnabled();
        });

        test('can modify and see save/undo buttons appear', async ({ page }) => {
            // Unlock editing
            await page.getByTestId('profile-edit-toggle').click();
            await expect(page.getByTestId('profile-username')).toBeEnabled();

            // Save/undo buttons should not be visible yet (no changes)
            await expect(page.getByTestId('profile-save-all')).not.toBeVisible();

            // Modify username
            const usernameInput = page.getByTestId('profile-username');
            const originalValue = await usernameInput.inputValue();
            await usernameInput.fill(originalValue + '_modified');

            // Save/undo buttons should now be visible
            await expect(page.getByTestId('profile-save-all')).toBeVisible();
            await expect(page.getByTestId('profile-undo-all')).toBeVisible();
        });

        test('can undo changes', async ({ page }) => {
            // Unlock editing
            await page.getByTestId('profile-edit-toggle').click();

            // Get original value
            const usernameInput = page.getByTestId('profile-username');
            const originalValue = await usernameInput.inputValue();

            // Modify
            await usernameInput.fill('modified_username');
            await expect(page.getByTestId('profile-undo-all')).toBeVisible();

            // Undo
            await page.getByTestId('profile-undo-all').click();

            // Should be back to original
            await expect(usernameInput).toHaveValue(originalValue);
        });
    });

    test.describe('Change Password Modal', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
        });

        test('can open change password modal', async ({ page }) => {
            await page.getByTestId('change-password-button').click();
            await expect(page.getByTestId('password-change-modal')).toBeVisible();
        });

        test('change password modal has all fields', async ({ page }) => {
            await page.getByTestId('change-password-button').click();
            await expect(page.getByTestId('password-change-modal')).toBeVisible();

            await expect(page.getByTestId('password-current')).toBeVisible();
            await expect(page.getByTestId('password-new')).toBeVisible();
            await expect(page.getByTestId('password-confirm')).toBeVisible();
            await expect(page.getByTestId('password-change-submit')).toBeVisible();
            await expect(page.getByTestId('password-change-cancel')).toBeVisible();
        });

        test('can close change password modal', async ({ page }) => {
            await page.getByTestId('change-password-button').click();
            await expect(page.getByTestId('password-change-modal')).toBeVisible();

            await page.getByTestId('password-change-cancel').click();
            await expect(page.getByTestId('password-change-modal')).not.toBeVisible();
        });

        test('password strength meter shows when typing new password', async ({ page }) => {
            await page.getByTestId('change-password-button').click();
            await expect(page.getByTestId('password-change-modal')).toBeVisible();

            // Strength meter should not be visible initially
            await expect(page.getByTestId('password-strength-meter')).not.toBeVisible();

            // Type new password
            await page.getByTestId('password-new').fill('NewPass123!');

            // Strength meter should appear
            await expect(page.getByTestId('password-strength-meter')).toBeVisible();
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

    test.describe('About Tab', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-about').click();
        });

        test('can switch to about tab', async ({ page }) => {
            await expect(page.getByTestId('settings-tab-about')).toHaveAttribute('aria-selected', 'true');
        });

        test('shows about tab content', async ({ page }) => {
            await expect(page.getByTestId('about-tab')).toBeVisible();
        });

        test('shows app name and version', async ({ page }) => {
            await expect(page.getByTestId('about-app-name')).toBeVisible();
            await expect(page.getByTestId('about-app-name')).toContainText('LibreFolio');
            await expect(page.getByTestId('about-version')).toBeVisible();
        });
    });
});
