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

    test.describe('Register Modal', () => {

        test('can open register modal from login', async ({ page }) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await page.getByTestId('goto-register').click();
            await expect(page.getByTestId('register-modal')).toBeVisible();
        });

        test('register form has all required fields', async ({ page }) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await page.getByTestId('goto-register').click();
            await expect(page.getByTestId('register-modal')).toBeVisible();

            // Check all form fields
            await expect(page.getByTestId('register-username')).toBeVisible();
            await expect(page.getByTestId('register-email')).toBeVisible();
            await expect(page.getByTestId('register-password')).toBeVisible();
            await expect(page.getByTestId('register-confirm-password')).toBeVisible();
            await expect(page.getByTestId('register-submit')).toBeVisible();
        });

        test('password strength meter shows when typing', async ({ page }) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await page.getByTestId('goto-register').click();
            await expect(page.getByTestId('register-modal')).toBeVisible();

            // Password strength should not be visible initially
            await expect(page.getByTestId('password-strength-meter')).not.toBeVisible();

            // Type a password
            await page.getByTestId('register-password').fill('Test123!');

            // Password strength meter should appear
            await expect(page.getByTestId('password-strength-meter')).toBeVisible();
        });

        test('can navigate back to login from register', async ({ page }) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await page.getByTestId('goto-register').click();
            await expect(page.getByTestId('register-modal')).toBeVisible();

            // Click back to login
            await page.getByTestId('goto-login').click();
            await expect(page.getByTestId('login-modal')).toBeVisible();
        });
    });

    test.describe('Forgot Password Modal', () => {

        test('can open forgot password modal from login', async ({ page }) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await page.getByTestId('goto-forgot').click();
            await expect(page.getByTestId('forgot-modal')).toBeVisible();
        });

        test('can navigate back to login from forgot password', async ({ page }) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await page.getByTestId('goto-forgot').click();
            await expect(page.getByTestId('forgot-modal')).toBeVisible();

            // Click back to login
            await page.getByTestId('forgot-back-to-login').click();
            await expect(page.getByTestId('login-modal')).toBeVisible();
        });
    });

    test.describe('Language Selector', () => {

        test('language selector is visible and clickable', async ({ page }) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await expect(page.getByTestId('language-selector')).toBeVisible();
            await page.getByTestId('language-selector-button').click();
            // Dropdown should open with language options (use menuitem role to be specific)
            for (const lang of SUPPORTED_LANGUAGES) {
                const info = LANGUAGE_INFO[lang];
                if (info) {
                    await expect(page.getByRole('menuitem', { name: new RegExp(info.name) })).toBeVisible();
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
