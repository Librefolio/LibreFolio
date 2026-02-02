import { test, expect } from '@playwright/test';
import { login, logout, setLanguage } from './fixtures/auth-helpers';
import { TEST_USER, TEST_ADMIN } from './fixtures/test-users';
import { SUPPORTED_LANGUAGES, LANGUAGE_INFO, t } from './fixtures/i18n-data';

test.describe('Authentication', () => {

    test.describe('Core Auth Flow (language-agnostic)', () => {

        test('login page renders correctly', async ({ page }) => {
            await page.goto('/');
            // Wait for auth check to complete (3s timeout for localhost)
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            // Then check login form elements
            await expect(page.getByTestId('login-modal')).toBeVisible();
            await expect(page.getByTestId('login-form')).toBeVisible();
            await expect(page.getByTestId('login-username')).toBeVisible();
            await expect(page.getByTestId('login-submit')).toBeVisible();
        });

        test('successful login redirects to dashboard', async ({ page }) => {
            await login(page, TEST_USER);
            await expect(page).toHaveURL(/.*dashboard.*/);
            await expect(page.getByTestId('dashboard-page')).toBeVisible();
        });

        test('invalid credentials show error', async ({ page }) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await page.getByTestId('login-username').fill('wronguser');
            await page.getByTestId('login-password').fill('wrongpass');
            await page.getByTestId('login-submit').click();
            // Error message should appear (any language)
            await expect(page.getByTestId('login-error')).toBeVisible({ timeout: 3000 });
        });

        test('logout returns to login page', async ({ page }) => {
            await login(page, TEST_USER);
            await logout(page);
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await expect(page.getByTestId('login-modal')).toBeVisible();
        });

        test('admin can login', async ({ page }) => {
            await login(page, TEST_ADMIN);
            await expect(page).toHaveURL(/.*dashboard.*/);
            await expect(page.getByTestId('dashboard-page')).toBeVisible();
        });
    });

    test.describe('Language Selector', () => {

        test('language selector is visible and clickable', async ({ page }) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await expect(page.getByTestId('language-selector')).toBeVisible();
            await page.getByTestId('language-selector-button').click();
            // Dropdown should open with language options
            for (const lang of SUPPORTED_LANGUAGES) {
                const info = LANGUAGE_INFO[lang];
                if (info) {
                    await expect(page.getByText(info.name)).toBeVisible();
                }
            }
        });

        // Dynamic tests for each supported language
        for (const lang of SUPPORTED_LANGUAGES) {
            const info = LANGUAGE_INFO[lang];
            if (!info) continue;

            test(`switching to ${info.name} (${lang}) updates login button text`, async ({ page }) => {
                await page.goto('/');
                await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
                await setLanguage(page, lang as any);

                // Get expected login button text for this language
                const expectedText = t(lang, 'auth.login');
                await expect(page.getByTestId('login-submit')).toContainText(expectedText);
            });
        }
    });
});
