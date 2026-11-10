/**
 * Every Settings tab has an address (release 1.3, lot B10), and «Open the settings» leads to the space limit in the
 * Global Settings tab.
 *
 * - `/settings/<tab>` and `/settings/admin/<tab>` open that tab (`settingsPaths.ts`); choosing a tab writes its address,
 *   and Back returns to the tab before; an address the registry does not know goes back to `/settings`, the first tab;
 *   a member asking for an administrator's tab gets the same; the `?tab=` of 1.2 opens its tab and is replaced by the
 *   tab's address.
 * - The space limit is a row of Global Settings (`global-setting-storage_limit_mb`). A refusal of the limit in Files, for
 *   an administrator, carries «Open the settings» (`storage-limit-open-settings`): it opens
 *   `/settings/admin/global?setting=storage_limit_mb`, the row in view and highlighted (`data-highlighted`), the tab still
 *   locked — the administrator opens the lock by hand (the developer's choice).
 *
 * Read-only on the lane: nothing is saved. The refusal is simulated on the page's own route (the limit is one value for
 * the whole instance, never changed from a parallel test), with the numbers of a real refusal.
 */
import type {Route} from '@playwright/test';
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';
import {eventSeq, waitForEvent} from '../fixtures/app-events';
import {uniqueSuffix} from '../fixtures/unique';

/** From a navigation to the bars drawn: the app's auth check and bootstrap, then the page's first render. */
const PAGE_MS = 20_000;
/** A click on something already on screen, and what it changes. */
const UI_MS = 5_000;

/** The pathname of the page, read from the address bar. */
const pathname = (page: Page): string => new URL(page.url()).pathname;

/** Wait until tab `id` reads selected, in either bar. */
async function expectSelected(page: Page, id: string, timeout = PAGE_MS): Promise<void> {
    await expect(page.getByTestId(`settings-tab-${id}`), `settings-tab-${id} is the open tab`).toHaveAttribute('aria-selected', 'true', {timeout});
}

test.describe('Settings addresses — an administrator', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_ADMIN);
    });

    test('an address opens its tab, a click writes the address of the tab, Back returns to the tab before', async ({page}) => {
        await navigateTo(page, '/settings/admin/backup');
        await expectSelected(page, 'backup');
        await expectSelected(page, 'administration', UI_MS);

        await page.getByTestId('settings-subtabs').getByTestId('settings-tab-users').click();
        await expect.poll(() => pathname(page), {message: 'the Users tab writes its address', timeout: UI_MS}).toBe('/settings/admin/users');
        await expectSelected(page, 'users', UI_MS);

        await page.getByTestId('settings-tab-preferences').click();
        await expect.poll(() => pathname(page), {message: 'and Preferences its own', timeout: UI_MS}).toBe('/settings/preferences');

        await page.goBack();
        await expect.poll(() => pathname(page), {message: 'Back goes to the address before', timeout: UI_MS}).toBe('/settings/admin/users');
        await expectSelected(page, 'users', UI_MS);
    });

    test('an address the registry does not know goes back to /settings, the first tab', async ({page}) => {
        await navigateTo(page, `/settings/nope-${uniqueSuffix()}`);

        await expect.poll(() => pathname(page), {message: 'the unknown address is replaced by /settings', timeout: PAGE_MS}).toBe('/settings');
        await expectSelected(page, 'profile', UI_MS);
    });

    test('the ?tab= address of 1.2 opens its tab and becomes the tab’s own', async ({page}) => {
        await navigateTo(page, '/settings?tab=email');

        await expectSelected(page, 'email');
        await expect.poll(() => pathname(page), {message: '?tab=email becomes /settings/admin/email', timeout: UI_MS}).toBe('/settings/admin/email');
    });

    test('«Open the settings» on a refusal of the space limit opens the limit in Global Settings, highlighted, the lock closed', async ({page}) => {
        const refusal = {detail: {code: 'storage_limit_exceeded', message: 'The space limit would be passed', limit_mb: 100, used_bytes: 90 * 1024 * 1024, required_bytes: 120 * 1024 * 1024, required_mb: 120, disk_missing_bytes: 0, limit_locked: false}};
        const isUpload = (url: URL) => url.pathname === '/api/v1/uploads';
        const refuse = (route: Route) => (route.request().method() === 'POST' ? route.fulfill({status: 507, contentType: 'application/json', body: JSON.stringify(refusal)}) : route.fallback());

        await navigateTo(page, '/files?tab=static');
        await page.getByTestId('upload-button').click();
        await page.getByTestId('file-input').setInputFiles({name: `space-limit-${uniqueSuffix()}.txt`, mimeType: 'text/plain', buffer: Buffer.from('x')});
        await page.route(isUpload, refuse);
        try {
            const since = await eventSeq(page);
            await page.getByTestId('file-upload-submit').click();
            await waitForEvent(page, 'file.upload.failed', {since, timeout: PAGE_MS});
        } finally {
            await page.unroute(isUpload, refuse);
        }
        const open = page.getByTestId('storage-limit-refusal').getByTestId('storage-limit-open-settings');
        await expect(open, 'an administrator is offered «Open the settings»').toBeVisible({timeout: UI_MS});

        await open.click();

        await expect.poll(() => page.url(), {message: 'Global Settings, at the field of the limit', timeout: PAGE_MS}).toMatch(/\/settings\/admin\/global\?setting=storage_limit_mb$/);
        await expectSelected(page, 'admin');
        const row = page.getByTestId('global-setting-storage_limit_mb');
        await expect(row, 'the row of the limit is highlighted').toHaveAttribute('data-highlighted', 'true', {timeout: PAGE_MS});
        await expect(row, 'and in view').toBeInViewport();
        const field = row.getByRole('spinbutton');
        await expect(field, 'the lock stays closed: the field is read-only until the administrator opens it').toBeDisabled();
        await expect(row, 'precondition: the lane does not pin the limit (LIBREFOLIO_STORAGE_LIMIT_MB unset)').toHaveAttribute('data-locked', 'false', {timeout: UI_MS});

        await page.getByTestId('settings-lock-toggle').click();
        await expect(field, 'opened by hand, the limit can be changed').toBeEnabled({timeout: UI_MS});
    });
});

test.describe('Settings addresses — a member', () => {
    test('an administrator’s tab address opens Profile and goes back to /settings', async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/settings/admin/users');

        await expect.poll(() => pathname(page), {message: 'a member has no Users tab: the address becomes /settings', timeout: PAGE_MS}).toBe('/settings');
        await expectSelected(page, 'profile', UI_MS);
        await expect(page.getByTestId('settings-tab-administration'), 'and no «Administration» group').toHaveCount(0);
    });
});
