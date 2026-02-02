import { Page, expect } from '@playwright/test';
import { TEST_USER, type Language } from './test-users';

/**
 * Login as specified user
 */
export async function login(page: Page, user = TEST_USER) {
    await page.goto('/');

    // Wait for login form
    await expect(page.getByPlaceholder(/username|email/i)).toBeVisible();

    // Fill and submit
    await page.getByPlaceholder(/username|email/i).fill(user.username);
    await page.getByPlaceholder(/password/i).fill(user.password);
    await page.getByRole('button', { name: /login|sign in|accedi/i }).click();

    // Wait for dashboard
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 10000 });
}

/**
 * Logout current user
 */
export async function logout(page: Page) {
    await page.getByTestId('user-menu').click();
    await page.getByRole('menuitem', { name: /logout|sign out|esci/i }).click();
    await expect(page).toHaveURL('/');
}

/**
 * Change UI language
 */
export async function setLanguage(page: Page, lang: Language) {
    await page.getByTestId('language-selector').click();
    const langNames: Record<Language, string> = {
        en: 'English',
        it: 'Italiano',
        fr: 'Français',
        es: 'Español',
    };
    await page.getByText(langNames[lang]).click();
    await page.waitForTimeout(300); // Wait for i18n update
}

/**
 * Open mobile menu (burger) if on mobile viewport
 */
export async function openMobileMenu(page: Page) {
    const burger = page.getByTestId('mobile-menu-toggle');
    if (await burger.isVisible()) {
        await burger.click();
        await page.waitForTimeout(300); // Wait for animation
    }
}

/**
 * Navigate to a route, handling mobile menu if needed
 */
export async function navigateTo(page: Page, route: string, menuItem?: string) {
    // If menuItem provided, use sidebar navigation
    if (menuItem) {
        await openMobileMenu(page);
        await page.getByRole('link', { name: new RegExp(menuItem, 'i') }).click();
    } else {
        await page.goto(route);
    }
    await page.waitForLoadState('networkidle');
}
