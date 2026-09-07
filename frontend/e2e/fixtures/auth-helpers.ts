import {expect, type Page} from './playwright';
import {type Language, TEST_USER} from './test-users';

/**
 * Login as specified user
 */
export async function login(page: Page, user = TEST_USER) {
    await page.goto('/');

    // Wait for auth check to complete — either login form appears or we're already logged in
    const loginPage = page.getByTestId('login-page');
    const appLayout = page.getByTestId('logout-button');

    // Race: login page vs app layout (already authenticated)
    const visible = await Promise.race([loginPage.waitFor({state: 'visible', timeout: 10_000}).then(() => 'login' as const), appLayout.waitFor({state: 'visible', timeout: 10_000}).then(() => 'app' as const)]).catch(() => 'timeout' as const);

    if (visible === 'app') {
        // Already logged in — nothing to do
        return;
    }

    if (visible === 'timeout') {
        // Neither appeared — force a retry with a fresh context
        await page.goto('/');
        await expect(loginPage).toBeVisible({timeout: 10_000});
    }

    await expect(page.getByTestId('login-form')).toBeVisible();

    // Fill and submit using data-testid
    await page.getByTestId('login-username').fill(user.username);
    await page.getByTestId('login-password').fill(user.password);
    await page.getByTestId('login-submit').click();

    // Wait for login to complete: login form disappears and app layout loads
    // (more robust than checking URL, which varies by redirect timing)
    await expect(loginPage).not.toBeVisible({timeout: 20_000});
    await page.waitForLoadState('domcontentloaded');
}

/**
 * Logout current user
 */
export async function logout(page: Page) {
    // Sidebar is visible on desktop, click logout button directly
    await page.getByTestId('logout-button').click();
    await expect(page).toHaveURL('/');
}

/**
 * Change UI language
 */
export async function setLanguage(page: Page, lang: Language) {
    // Wait for language selector to be visible (needs longer timeout for SvelteKit hydration after fresh navigation)
    await expect(page.getByTestId('language-selector-button')).toBeVisible({timeout: 5000});
    await page.getByTestId('language-selector-button').click();

    // Click the menu item specifically (not any element with that text)
    const langNames: Record<Language, string> = {
        en: 'English',
        it: 'Italiano',
        fr: 'Français',
        es: 'Español',
    };
    // Use role='menuitem' to be specific and avoid conflicts with other dropdowns
    await page.getByRole('menuitem', {name: new RegExp(langNames[lang])}).click();
    // The app publishes both halves: `lang` flips to the chosen language, and
    // data-i18n-ready goes true only once that dictionary has actually landed.
    // Asserting both is what makes this helper's promise ("when I return, the UI
    // speaks `lang`") true instead of merely likely.
    await expect(page.locator('html')).toHaveAttribute('lang', lang);
    await expect(page.locator('html')).toHaveAttribute('data-i18n-ready', 'true');
}

/**
 * Open mobile menu (burger) if on mobile viewport
 */
export async function openMobileMenu(page: Page) {
    const burger = page.getByTestId('mobile-menu-toggle');
    if (await burger.isVisible()) {
        await burger.click();
        // No sleep for the slide-in animation: Playwright's click() already refuses
        // to act on an element that is still moving, so whatever is clicked next
        // waits for the sidebar to settle on its own.
    }
}

/**
 * Navigate to a route, handling mobile menu if needed
 */
export async function navigateTo(page: Page, route: string, menuItem?: string) {
    // If menuItem provided, use sidebar navigation
    if (menuItem) {
        await openMobileMenu(page);
        await page.getByRole('link', {name: new RegExp(menuItem, 'i')}).click();
    } else {
        await page.goto(route);
    }
    // Wait for page to be fully loaded.
    await page.waitForLoadState('domcontentloaded');
    // `data-i18n-ready` is written by the root +layout, so the attribute does not
    // exist at all until the client has hydrated — waiting for it IS the hydration
    // barrier, and it also guarantees the translations are in. This replaced a flat
    // 100ms "buffer for Svelte hydration" which, at 112 call sites, was both ~11s of
    // dead time and a guess that got worse under parallel load.
    await page.waitForSelector('html[data-i18n-ready="true"]', {timeout: 15_000});
}
