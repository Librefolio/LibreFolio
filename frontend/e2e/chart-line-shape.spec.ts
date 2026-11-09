import {expect, test, type Page} from './fixtures/playwright';
import {login} from './fixtures/auth-helpers';
import {completeWelcome, deleteDisposableUser, registerDisposableUser, type DisposableUser} from './fixtures/onboarding-accounts';
import {TEST_USER} from './fixtures/test-users';
import {waitForSettled} from './fixtures/app-events';
import {goToAssetsPage} from './assets/assets-helpers';
import {installLocalUiPreferences} from './fixtures/local-ui-preferences';

/**
 * The shape of the lines of the charts (Y2 FB-3): segments (the default), steps, a smooth curve.
 *
 * The welcome page offers it with a live example; Settings → Preferences changes it for every chart; the chart settings of an
 * asset detail page give that one chart its own. Nothing here reads a translated word: the pickers' `data-value` and the charts'
 * `data-line-shape` are the contract. The global shape is a server-side preference of the user (lot UIP): the cases that write it
 * either own a disposable user, or (the asset-page case, which needs the seeded Apple asset of TEST_USER) keep the choice inside
 * their browser context (`fixtures/local-ui-preferences.ts`: the settings reads carry it, the PUT never reaches the server), so
 * the shared user's preference is never written by a parallel worker.
 */

test.setTimeout(90_000);

async function openPreferences(page: Page): Promise<void> {
    await page.goto('/settings');
    await page.getByTestId('settings-tab-preferences').click();
    await expect(page.getByTestId('preference-line-shape')).toBeVisible({timeout: 15_000});
}

async function openSeededAssetDetail(page: Page): Promise<void> {
    await goToAssetsPage(page);
    const card = page.locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i}).first();
    await expect(card, 'the seeded Apple asset must be on the list').toBeVisible({timeout: 10_000});
    await card.click();
    await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 30_000});
    await waitForSettled(page.getByTestId('asset-detail-page'), 20_000);
}

test.describe('Line shape of the charts (FB-3)', () => {
    test('the welcome page changes its example as the shape is picked, and the choice stays for every chart', async ({page, request}) => {
        const user: DisposableUser = await registerDisposableUser(request, 'lineshape');
        try {
            await login(page, user);
            await expect(page).toHaveURL(/\/welcome(?:[/?#]|$)/, {timeout: 15_000});
            const picker = page.getByTestId('welcome-line-shape-picker');
            await expect(picker).toHaveAttribute('data-value', 'segments');
            const example = page.getByTestId('line-shape-preview').locator('[data-line-shape]');
            await expect(example).toHaveAttribute('data-line-shape', 'segments');

            await page.getByTestId('welcome-line-shape-picker-spline').click();
            await expect(picker).toHaveAttribute('data-value', 'spline');
            await expect(example).toHaveAttribute('data-line-shape', 'spline');
            await page.getByTestId('welcome-line-shape-picker-steps').click();
            await expect(example).toHaveAttribute('data-line-shape', 'steps');

            await completeWelcome(page);
            await page.getByTestId('onboarding-intro-close').click();
            await openPreferences(page);
            await expect(page.getByTestId('preference-line-shape-picker')).toHaveAttribute('data-value', 'steps');
            // a shape picked is the user's own: the row no longer says it follows the global default
            await expect(page.getByTestId('preference-line-shape-badge-global')).toHaveCount(0);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('a user who never picks a shape follows the global default, and the Preferences row says so', async ({page, request}) => {
        const user: DisposableUser = await registerDisposableUser(request, 'lineshape');
        try {
            await login(page, user);
            await completeWelcome(page); // the defaults: the picker is never clicked
            await page.getByTestId('onboarding-intro-close').click();
            await openPreferences(page);
            await expect(page.getByTestId('preference-line-shape-picker')).toHaveAttribute('data-value', 'segments');
            await expect(page.getByTestId('preference-line-shape-badge-global')).toBeVisible();
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('Preferences changes every chart; an asset page can give its chart a shape of its own', async ({page, context}) => {
        // Why not a disposable user: the seeded Apple asset (with its prices) belongs to TEST_USER's data, and the shape is now
        // stored on the server per user. The context keeps its own preferences instead, so nothing shared is written.
        await installLocalUiPreferences(context);
        await login(page, TEST_USER);
        await openPreferences(page);
        await page.getByTestId('preference-line-shape-picker-spline').click();
        await expect(page.getByTestId('preference-line-shape-picker')).toHaveAttribute('data-value', 'spline');

        await openSeededAssetDetail(page);
        const chart = page.getByTestId('asset-detail-chart').locator('[data-line-shape]');
        await expect(chart).toHaveAttribute('data-line-shape', 'spline', {timeout: 10_000});

        await page.getByTestId('asset-detail-aesthetics-toggle').click();
        const row = page.getByTestId('chart-aesthetic-line-shape-row');
        await expect(row).toBeVisible();
        await expect(page.getByTestId('chart-aesthetic-line-shape')).toHaveAttribute('data-value', 'spline');
        await page.getByTestId('chart-aesthetic-line-shape-steps').click();
        await expect(chart).toHaveAttribute('data-line-shape', 'steps');

        // The chart's own choice survives a reload; the global one is not touched by it.
        await page.reload();
        await waitForSettled(page.getByTestId('asset-detail-page'), 20_000);
        await expect(page.getByTestId('asset-detail-chart').locator('[data-line-shape]')).toHaveAttribute('data-line-shape', 'steps', {timeout: 10_000});
        await openPreferences(page);
        await expect(page.getByTestId('preference-line-shape-picker')).toHaveAttribute('data-value', 'spline');
    });
});
