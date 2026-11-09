/**
 * UI preferences are kept on the server, per user (lot UIP): the theme and the line shape of the charts follow the account
 * into another browser, and each one is told apart from a value that merely follows the instance's default.
 *
 * ONE disposable user, two browser contexts (two «browsers»), signed in one after the other:
 *   - A sees both Preferences rows following the global default (`preference-line-shape-badge-global`,
 *     `preference-theme-badge-global`, and `preference-theme-badge-auto`: the instance's default theme is auto), picks the
 *     shape `steps` and the theme `dark`: both are drafts (the row shows Save) and only reach the server on each row's Save (UIP-2);
 *   - B, a fresh sign-in, finds the same account preferences: the picker on `steps`, dark pressed, no global badge, `<html>`
 *     dark from the login on; B resets the line shape (`setting-reset` of its row, a draft: the badge is back, the picker
 *     `segments`) and saves the row;
 *   - A reloads Preferences and finds the reset (picker `segments`, badge) while its theme is still its own dark: the reset
 *     removed one key only.
 * Nothing reads a translated word. The user is created and deleted here; no global setting is touched, so the spec runs in
 * parallel with the rest.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `ui-preferences` of front-utility.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {completeWelcome, deleteDisposableUser, registerDisposableUser, skipDueFlowsExcept, type DisposableUser} from '../fixtures/onboarding-accounts';

test.setTimeout(120_000);

const DARK_CLASS = /(^|\s)dark(\s|$)/;

/** The write of the user's preferences: PUT /api/v1/settings/user. */
const isPreferencesPut = (r: {url(): string; request(): {method(): string}}) => r.url().includes('/api/v1/settings/user') && r.request().method() === 'PUT';

async function openPreferences(page: Page): Promise<void> {
    await page.goto('/settings/preferences');
    await expect(page.getByTestId('preference-line-shape')).toBeVisible({timeout: 20_000});
    await expect(page.getByTestId('preference-theme')).toBeVisible();
}

test('theme and line shape follow the account into another browser, and a reset removes one key only', async ({page, browser, baseURL, request}) => {
    const user: DisposableUser = await registerDisposableUser(request, 'uipref');
    const contextB = await browser.newContext({baseURL: baseURL ?? undefined});
    try {
        // ---- A: a new account, nothing of its own
        await login(page, user);
        await completeWelcome(page);
        await page.getByTestId('onboarding-intro-close').click();
        await skipDueFlowsExcept(page, []);
        await openPreferences(page);

        const shapeRow = page.getByTestId('preference-line-shape');
        const themeRow = page.getByTestId('preference-theme');
        await expect(shapeRow.getByTestId('preference-line-shape-badge-global')).toBeVisible();
        await expect(page.getByTestId('preference-line-shape-picker')).toHaveAttribute('data-value', 'segments');
        await expect(themeRow.getByTestId('preference-theme-badge-global')).toBeVisible();
        await expect(themeRow.getByTestId('preference-theme-badge-auto')).toBeVisible();

        await page.getByTestId('preference-line-shape-picker-steps').click();
        await expect(page.getByTestId('preference-line-shape-picker')).toHaveAttribute('data-value', 'steps');
        await expect(shapeRow.getByTestId('preference-line-shape-badge-global')).toHaveCount(0);
        await expect(shapeRow.getByTestId('setting-save')).toBeVisible();
        const shapePut = page.waitForResponse(isPreferencesPut);
        await shapeRow.getByTestId('setting-save').click();
        expect((await shapePut).request().postDataJSON()).toEqual({ui_preferences: {chart_line_shape: 'steps'}});
        await expect(shapeRow.getByTestId('setting-save')).toBeHidden();

        await themeRow.getByTestId('setting-theme-option-dark').click();
        const themePut = page.waitForResponse(isPreferencesPut);
        await themeRow.getByTestId('setting-save').click();
        expect((await themePut).request().postDataJSON()).toEqual({ui_preferences: {theme: 'dark'}});
        await expect(themeRow.getByTestId('setting-save')).toBeHidden();
        await expect(page.locator('html')).toHaveClass(DARK_CLASS);
        await expect(themeRow.getByTestId('preference-theme-badge-global')).toHaveCount(0);

        // ---- B: another browser, the same account
        const pageB = await contextB.newPage();
        await login(pageB, user);
        await expect(pageB.getByTestId('app-shell')).toBeVisible({timeout: 20_000});
        await expect(pageB.locator('html')).toHaveClass(DARK_CLASS);
        await openPreferences(pageB);
        const shapeRowB = pageB.getByTestId('preference-line-shape');
        const themeRowB = pageB.getByTestId('preference-theme');
        await expect(pageB.getByTestId('preference-line-shape-picker')).toHaveAttribute('data-value', 'steps');
        await expect(themeRowB.getByTestId('setting-theme-option-dark')).toHaveAttribute('aria-pressed', 'true');
        await expect(pageB.getByTestId('preference-line-shape-badge-global')).toHaveCount(0);
        await expect(pageB.getByTestId('preference-theme-badge-global')).toHaveCount(0);

        await shapeRowB.getByTestId('setting-reset').click();
        await expect(pageB.getByTestId('preference-line-shape-picker')).toHaveAttribute('data-value', 'segments');
        await expect(shapeRowB.getByTestId('preference-line-shape-badge-global')).toBeVisible();
        const resetPut = pageB.waitForResponse(isPreferencesPut);
        await shapeRowB.getByTestId('setting-save').click();
        expect((await resetPut).request().postDataJSON()).toEqual({ui_preferences: {chart_line_shape: null}});
        await expect(shapeRowB.getByTestId('setting-save')).toBeHidden();

        // ---- A again: the reset reached the server, and only that key
        await openPreferences(page);
        await expect(page.getByTestId('preference-line-shape-picker')).toHaveAttribute('data-value', 'segments');
        await expect(shapeRow.getByTestId('preference-line-shape-badge-global')).toBeVisible();
        await expect(themeRow.getByTestId('setting-theme-option-dark')).toHaveAttribute('aria-pressed', 'true');
        await expect(themeRow.getByTestId('preference-theme-badge-global')).toHaveCount(0);
        await expect(page.locator('html')).toHaveClass(DARK_CLASS);
    } finally {
        await contextB.close();
        await deleteDisposableUser(request, user);
    }
});
