import { test, expect } from '@playwright/test';
import { login, logout, setLanguage } from './fixtures/auth-helpers';
import { TEST_USER, TEST_ADMIN } from './fixtures/test-users';

test.describe('Authentication', () => {

    test('login page renders correctly', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByPlaceholder(/username|email/i)).toBeVisible();
        await expect(page.getByPlaceholder(/password/i)).toBeVisible();
        await expect(page.getByRole('button', { name: /login|sign in/i })).toBeVisible();
    });

    test('successful login redirects to dashboard', async ({ page }) => {
        await login(page, TEST_USER);
        await expect(page).toHaveURL(/.*dashboard.*/);
        await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    });

    test('invalid credentials show error', async ({ page }) => {
        await page.goto('/');
        await page.getByPlaceholder(/username|email/i).fill('wronguser');
        await page.getByPlaceholder(/password/i).fill('wrongpass');
        await page.getByRole('button', { name: /login|sign in/i }).click();
        await expect(page.getByText(/invalid|incorrect|failed|error/i)).toBeVisible();
    });

    test('logout returns to login page', async ({ page }) => {
        await login(page, TEST_USER);
        await logout(page);
        await expect(page.getByPlaceholder(/username|email/i)).toBeVisible();
    });

    test('language selector changes UI', async ({ page }) => {
        await page.goto('/');
        await setLanguage(page, 'it');
        await expect(page.getByRole('button', { name: /accedi/i })).toBeVisible();
    });

    test('admin can login', async ({ page }) => {
        await login(page, TEST_ADMIN);
        await expect(page).toHaveURL(/.*dashboard.*/);
    });
});
