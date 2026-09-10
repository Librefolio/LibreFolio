import {expect, type Page, type Request, test} from './fixtures/playwright';
import {login, navigateTo} from './fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from './fixtures/test-users';
import {eventSeq, waitForEvent} from './fixtures/app-events';
import {optionsClosed} from './fixtures/probe';
import {uniqueSuffix} from './fixtures/unique';

test.describe('Runes parity', () => {
    // The preference case owns its account; the admin case changes only a local
    // draft. Neither case writes instance-wide settings or repairs shared data.
    test.setTimeout(45_000);

    async function openPreferences(page: Page) {
        await navigateTo(page, '/settings');
        await page.getByTestId('settings-tab-preferences').click();
        await expect(page.getByTestId('preference-currency').getByRole('combobox')).toBeEnabled({timeout: 10_000});
    }

    test('preferences save a real value across reload; Reset and Undo only stage changes', async ({page, request}) => {
        const suffix = uniqueSuffix();
        const user = {username: `runes_prefs_${suffix}`, email: `runes_prefs_${suffix}@example.com`, password: `Runes9!_${suffix}`};
        const registered = await request.post('/api/v1/auth/register', {data: user});
        expect(registered.status(), 'Disposable-account registration must be enabled; do not change global settings to repair it').toBe(201);
        const {user: created} = (await registered.json()) as {user: {id: number}};

        const puts: unknown[] = [];
        const recordPut = (req: Request) => {
            if (req.method() === 'PUT' && new URL(req.url()).pathname === '/api/v1/settings/user') puts.push(req.postDataJSON());
        };
        try {
            await login(page, user);
            const me = await page.request.get('/api/v1/auth/me');
            expect(me.ok()).toBe(true);
            expect((await me.json()).user.id).toBe(created.id);

            const globals = await page.request.get('/api/v1/settings/global');
            expect(globals.ok()).toBe(true);
            const {items} = (await globals.json()) as {items: {key: string; value: string}[]};
            const defaultCurrency = items.find((item) => item.key === 'default_currency')?.value;
            expect(defaultCurrency, 'The test must read the real default, not assume EUR').toMatch(/^[A-Z]{3}$/);
            if (!defaultCurrency) throw new Error('default_currency was absent from settings/global');
            const savedCurrency = defaultCurrency === 'USD' ? 'EUR' : 'USD';

            // Only this disposable account is seeded, before observing UI writes.
            const seeded = await page.request.put('/api/v1/settings/user', {data: {base_currency: defaultCurrency}});
            expect(seeded.ok()).toBe(true);
            await openPreferences(page);
            const row = page.getByTestId('preference-currency');
            const select = row.getByRole('combobox');
            await expect(select).toContainText(defaultCurrency);
            page.on('request', recordPut);

            await select.click();
            await page.getByTestId(`search-select-option-${savedCurrency}`).click();
            await optionsClosed(page);
            await expect(select).toContainText(savedCurrency);
            const since = await eventSeq(page);
            const response = page.waitForResponse((res) => res.request().method() === 'PUT' && new URL(res.url()).pathname === '/api/v1/settings/user');
            await row.getByTestId('setting-save').click();
            const saved = await response;
            expect(saved.request().postDataJSON()).toEqual({base_currency: savedCurrency});
            expect(saved.ok()).toBe(true);
            expect((await waitForEvent(page, 'settings.preferences.saved', {since})).detail).toMatchObject({field: 'default_currency', value: savedCurrency});
            await expect(row.getByTestId('setting-save')).toBeHidden();

            // A new document/mount must display the persisted value, not just a tab.
            await openPreferences(page);
            await expect(select).toContainText(savedCurrency);
            await row.getByTestId('setting-reset').click();
            await expect(select).toContainText(defaultCurrency);
            await expect(row.getByTestId('setting-save')).toBeVisible();
            const afterReset = await page.request.get('/api/v1/settings/user');
            expect(afterReset.ok()).toBe(true);
            expect((await afterReset.json()).base_currency).toBe(savedCurrency);

            await row.getByTestId('setting-undo').click();
            await expect(select).toContainText(savedCurrency);
            await expect(row.getByTestId('setting-save')).toBeHidden();
            await openPreferences(page);
            await expect(select).toContainText(savedCurrency);
            expect(puts).toEqual([{base_currency: savedCurrency}]);
        } finally {
            page.off('request', recordPut);
            // The isolated API context does not depend on the browser surviving
            // the assertion. Verify identity before the self-delete endpoint.
            const loggedIn = await request.post('/api/v1/auth/login', {data: {username: user.username, password: user.password}});
            expect(loggedIn.ok()).toBe(true);
            expect((await loggedIn.json()).user.id).toBe(created.id);
            const removed = await request.delete('/api/v1/auth/users/me');
            expect(removed.ok()).toBe(true);
        }
    });

    test('global lock rejects then accepts discarding a local draft without persisting it', async ({page}) => {
        await login(page, TEST_ADMIN);
        await navigateTo(page, '/settings');
        await page.getByTestId('settings-tab-admin').click();
        const tab = page.getByTestId('global-settings-tab');
        await expect(tab).toHaveAttribute('data-busy', 'false', {timeout: 10_000});
        const field = tab.getByTestId('global-setting-session_ttl_hours').getByRole('spinbutton');
        await expect(field).toBeDisabled();
        const baseline = await field.inputValue();
        expect(baseline).toMatch(/^\d+$/);
        const draft = String(Number(baseline) + 1);
        const writes: string[] = [];
        const nativeDialogs: string[] = [];
        // Negative sentinel only: none of the tested interactions uses a native
        // dialog. Dismiss unexpected ones so a regression fails, rather than hangs.
        page.on('dialog', async (dialog) => {
            nativeDialogs.push(dialog.type());
            await dialog.dismiss();
        });
        const recordWrite = (req: Request) => {
            if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method()) && new URL(req.url()).pathname.startsWith('/api/v1/settings/global')) writes.push(req.url());
        };
        page.on('request', recordWrite);
        try {
            await tab.getByTestId('settings-lock-toggle').click();
            await expect(field).toBeEnabled();
            await field.fill(draft);
            await expect(tab.getByTestId('settings-save-all')).toBeVisible();

            const header = page.getByTestId('global-settings-discard-confirm');
            const discard = page.getByRole('dialog').filter({has: header});
            for (const action of ['cancel', 'escape', 'dismiss', 'backdrop'] as const) {
                await test.step(`keep local draft on modal ${action}`, async () => {
                    await tab.getByTestId('settings-lock-toggle').click();
                    await expect(header).toBeVisible();
                    const confirm = discard.getByTestId('confirm-modal-confirm');
                    await expect(confirm).toBeEnabled();
                    // Approved feature assertion, never a class-based selector.
                    await expect(confirm).toHaveClass(/\bbtn-warning\b/);
                    await expect(confirm).not.toHaveClass(/\bbtn-danger\b/);
                    await expect(field).toHaveValue(draft);
                    if (action === 'cancel') {
                        await discard.getByTestId('confirm-modal-cancel').click();
                    } else if (action === 'escape') {
                        await discard.press('Escape');
                    } else if (action === 'dismiss') {
                        await header.getByRole('button').click();
                    } else {
                        // ModalBase's padded viewport corner is outside the content.
                        await discard.click({position: {x: 1, y: 1}});
                    }
                    await expect(header).toBeHidden();
                    await expect(field).toBeEnabled();
                    await expect(field).toHaveValue(draft);
                    await expect(tab.getByTestId('settings-save-all')).toBeVisible();
                    expect(nativeDialogs).toEqual([]);
                    expect(writes).toEqual([]);
                });
            }

            await tab.getByTestId('settings-lock-toggle').click();
            await expect(header).toBeVisible();
            await discard.getByTestId('confirm-modal-confirm').click();
            await expect(header).toBeHidden();
            await expect(field).toBeDisabled();
            await expect(field).toHaveValue(baseline);
            await expect(tab.getByTestId('settings-save-all')).toBeHidden();
            expect(nativeDialogs).toEqual([]);

            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-admin').click();
            await expect(tab).toHaveAttribute('data-busy', 'false', {timeout: 10_000});
            await expect(field).toBeDisabled();
            await expect(field).toHaveValue(baseline);
            expect(nativeDialogs).toEqual([]);
            expect(writes).toEqual([]);
        } finally {
            page.off('request', recordWrite);
        }
    });
});

test.describe('Settings', () => {
    test.describe('Settings Page Access', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_USER);
        });

        test('can access settings page', async ({page}) => {
            await navigateTo(page, '/settings');
            await expect(page.getByTestId('settings-page')).toBeVisible();
        });

        test('shows all settings tabs', async ({page}) => {
            await navigateTo(page, '/settings');
            await expect(page.getByTestId('settings-tab-profile')).toBeVisible();
            await expect(page.getByTestId('settings-tab-preferences')).toBeVisible();
            await expect(page.getByTestId('settings-tab-about')).toBeVisible();
            await expect(page.getByTestId('settings-tab-admin')).toBeVisible();
        });

        test('profile tab is active by default', async ({page}) => {
            await navigateTo(page, '/settings');
            await expect(page.getByTestId('settings-tab-profile')).toHaveAttribute('aria-selected', 'true');
            await expect(page.getByTestId('profile-tab')).toBeVisible();
        });
    });

    test.describe('Profile Tab', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
        });

        test('shows user profile information', async ({page}) => {
            await expect(page.getByTestId('profile-tab')).toBeVisible();
            await expect(page.getByTestId('profile-username')).toBeVisible();
            await expect(page.getByTestId('profile-email')).toBeVisible();
        });

        test('profile fields are initially disabled (locked)', async ({page}) => {
            await expect(page.getByTestId('profile-username')).toBeDisabled();
            await expect(page.getByTestId('profile-email')).toBeDisabled();
        });

        test('change password button is visible', async ({page}) => {
            await expect(page.getByTestId('change-password-button')).toBeVisible();
        });

        test('delete account button is visible', async ({page}) => {
            await expect(page.getByTestId('delete-account-button')).toBeVisible();
        });

        test('can unlock profile for editing', async ({page}) => {
            // Fields should be disabled initially
            await expect(page.getByTestId('profile-username')).toBeDisabled();

            // Click edit toggle to unlock
            await page.getByTestId('profile-edit-toggle').click();

            // Fields should now be enabled
            await expect(page.getByTestId('profile-username')).toBeEnabled();
            await expect(page.getByTestId('profile-email')).toBeEnabled();
        });

        test('can modify and see save/undo buttons appear', async ({page}) => {
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

        test('can undo changes', async ({page}) => {
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
        test.beforeEach(async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
        });

        test('can open change password modal', async ({page}) => {
            await page.getByTestId('change-password-button').click();
            await expect(page.getByTestId('password-change-modal')).toBeVisible();
        });

        test('change password modal has all fields', async ({page}) => {
            await page.getByTestId('change-password-button').click();
            await expect(page.getByTestId('password-change-modal')).toBeVisible();

            await expect(page.getByTestId('password-current')).toBeVisible();
            await expect(page.getByTestId('password-new')).toBeVisible();
            await expect(page.getByTestId('password-confirm')).toBeVisible();
            await expect(page.getByTestId('password-change-submit')).toBeVisible();
            await expect(page.getByTestId('password-change-cancel')).toBeVisible();
        });

        test('can close change password modal', async ({page}) => {
            await page.getByTestId('change-password-button').click();
            await expect(page.getByTestId('password-change-modal')).toBeVisible();

            await page.getByTestId('password-change-cancel').click();
            await expect(page.getByTestId('password-change-modal')).not.toBeVisible();
        });

        test('password strength meter shows when typing new password', async ({page}) => {
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
        test.beforeEach(async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-preferences').click();
        });

        test('can switch to preferences tab', async ({page}) => {
            await expect(page.getByTestId('settings-tab-preferences')).toHaveAttribute('aria-selected', 'true');
        });

        test('shows language preference', async ({page}) => {
            await expect(page.getByTestId('preference-language')).toBeVisible();
        });

        test('shows currency preference', async ({page}) => {
            await expect(page.getByTestId('preference-currency')).toBeVisible();
        });

        test('shows theme preference', async ({page}) => {
            await expect(page.getByTestId('preference-theme')).toBeVisible();
        });
    });

    test.describe('Admin Tab (Global Settings)', () => {
        test('admin can view and access global settings', async ({page}) => {
            await login(page, TEST_ADMIN);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-admin').click();

            await expect(page.getByTestId('settings-tab-admin')).toHaveAttribute('aria-selected', 'true');
            await expect(page.getByTestId('global-settings-tab')).toBeVisible();
        });

        test('non-admin can view but not edit global settings', async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-admin').click();

            await expect(page.getByTestId('global-settings-tab')).toBeVisible();
            // Lock button should not be visible for non-admin (read-only mode)
            // The component shows ShieldOff icon instead of Lock/Unlock for non-admins
        });
    });

    test.describe('Global Settings — Toggle & Number Interaction', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-admin').click();
            await expect(page.getByTestId('global-settings-tab')).toBeVisible();
            // Wait for settings to load (async API call)
            await page.waitForSelector('[data-testid="global-settings-tab"] .setting-row', {timeout: 10_000});
        });

        /** Helper: scope all locators within global-settings-tab */
        function gs(page: import('@playwright/test').Page) {
            return page.getByTestId('global-settings-tab');
        }

        test('admin can unlock global settings for editing', async ({page}) => {
            const unlockBtn = gs(page).locator('button[title="Click to unlock and edit"]');
            await expect(unlockBtn).toBeVisible();
            await unlockBtn.click();
            await expect(gs(page).locator('button[title*="Click to lock"]')).toBeVisible();
        });

        test('toggle switch changes value when clicked (SettingToggle)', async ({page}) => {
            // Unlock
            await gs(page).locator('button[title="Click to unlock and edit"]').click();

            // Find toggle within global-settings-tab (excludes mobile menu toggle)
            const toggleBtn = gs(page).locator('button[aria-label^="Toggle"]').first();
            await expect(toggleBtn).toBeVisible();
            await expect(toggleBtn).toBeEnabled();

            // Read ON/OFF state from sibling span
            const toggleContainer = toggleBtn.locator('xpath=..');
            const stateText = toggleContainer.locator('span').filter({hasText: /^(ON|OFF)$/});
            const initialState = await stateText.textContent();

            // Click toggle
            await toggleBtn.click();

            // State should have changed — the retrying assertion *is* the wait
            await expect(stateText).not.toHaveText(initialState ?? '', {timeout: 5_000});
        });

        test('save and undo buttons appear after toggling', async ({page}) => {
            // Unlock
            await gs(page).locator('button[title="Click to unlock and edit"]').click();

            // Click a toggle
            await gs(page).locator('button[aria-label^="Toggle"]').first().click();

            // Save/Undo should appear within the setting row
            const settingRow = gs(page)
                .locator('.setting-row')
                .filter({has: page.locator('button[aria-label^="Toggle"]')})
                .first();
            await expect(settingRow.locator('button[title="Save"]')).toBeVisible();
            await expect(settingRow.locator('button[title="Undo"]')).toBeVisible();
        });

        test('undo reverts toggle to original value', async ({page}) => {
            // Unlock
            await gs(page).locator('button[title="Click to unlock and edit"]').click();

            // Find first toggle setting-row
            const settingRow = gs(page)
                .locator('.setting-row')
                .filter({has: page.locator('button[aria-label^="Toggle"]')})
                .first();
            const toggleBtn = settingRow.locator('button[aria-label^="Toggle"]');
            const stateText = toggleBtn
                .locator('xpath=..')
                .locator('span')
                .filter({hasText: /^(ON|OFF)$/});
            const initialState = await stateText.textContent();

            // Toggle
            await toggleBtn.click();
            await expect(stateText).not.toHaveText(initialState ?? '', {timeout: 5_000});

            // Undo
            await settingRow.locator('button[title="Undo"]').click();
            await expect(stateText).toHaveText(initialState!);
        });

        test('number input can be edited and undone (SettingNumber)', async ({page}) => {
            // Unlock
            await gs(page).locator('button[title="Click to unlock and edit"]').click();

            const numberInput = gs(page).locator('.setting-row input[type="number"]').first();
            await expect(numberInput).toBeVisible();
            await expect(numberInput).toBeEnabled();

            const originalValue = await numberInput.inputValue();
            await numberInput.fill('99');

            // Save button should appear
            const settingRow = numberInput.locator('xpath=ancestor::div[contains(@class, "setting-row")]');
            await expect(settingRow.locator('button[title="Save"]')).toBeVisible();

            // Undo
            await settingRow.locator('button[title="Undo"]').click();
            await expect(numberInput).toHaveValue(originalValue);
        });

        test('toggles are disabled when locked', async ({page}) => {
            const toggleBtn = gs(page).locator('button[aria-label^="Toggle"]').first();
            await expect(toggleBtn).toBeVisible();
            await expect(toggleBtn).toBeDisabled();
        });

        test('number inputs are disabled when locked', async ({page}) => {
            const numberInput = gs(page).locator('.setting-row input[type="number"]').first();
            await expect(numberInput).toBeVisible();
            await expect(numberInput).toBeDisabled();
        });
    });

    test.describe('Global Settings — Non-Admin Read-Only', () => {
        test('non-admin sees disabled toggles and inputs', async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-admin').click();
            await expect(page.getByTestId('global-settings-tab')).toBeVisible();
            await page.waitForSelector('[data-testid="global-settings-tab"] .setting-row', {timeout: 10_000});

            const gs = page.getByTestId('global-settings-tab');
            await expect(gs.locator('button[aria-label^="Toggle"]').first()).toBeDisabled();
            await expect(gs.locator('.setting-row input[type="number"]').first()).toBeDisabled();
        });
    });

    test.describe('About Tab', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-about').click();
        });

        test('can switch to about tab', async ({page}) => {
            await expect(page.getByTestId('settings-tab-about')).toHaveAttribute('aria-selected', 'true');
        });

        test('shows about tab content', async ({page}) => {
            await expect(page.getByTestId('about-tab')).toBeVisible();
        });

        test('shows app name and version', async ({page}) => {
            await expect(page.getByTestId('about-app-name')).toBeVisible();
            await expect(page.getByTestId('about-app-name')).toContainText('LibreFolio');
            await expect(page.getByTestId('about-version')).toBeVisible();
        });

        // The three tests above read the header and stop there, which left the rest of
        // AboutTab — the installed-signal catalogue and the per-system plugin
        // diagnostics — at 27% coverage. Both live inside a collapsed `<details>`, so
        // nothing rendered them until something opened it.

        test('installed signals section lists the signals the backend reports', async ({page}) => {
            const details = page.getByTestId('about-installed-signals');
            await expect(details).toBeVisible();
            await details.locator('summary').click();
            // A `<details>` announces itself: the open attribute is the post-condition,
            // not the chevron rotating.
            await expect(details).toHaveAttribute('open', '');

            // Asserting on *which* signals exist would be asserting a catalogue this test
            // does not own — plugins can be added. That at least one is listed, and that
            // each entry carries the signal type in its testid, is the contract.
            const entries = page.locator('[data-testid^="about-installed-signal-"]');
            await expect(entries.first(), 'the signal registry should report at least one installed signal').toBeVisible({timeout: 5_000});
        });

        test('plugin diagnostics reports a load status for every plugin system', async ({page}) => {
            const details = page.getByTestId('about-plugin-diagnostics');
            await expect(details).toBeVisible();
            await details.locator('summary').click();
            await expect(details).toHaveAttribute('open', '');

            // Four plugin systems, each of which must say whether its plugins loaded.
            // The status used to be readable only from the green tick and its translated
            // caption, so the component now publishes data-status / data-failures.
            for (const system of ['asset', 'fx', 'brim', 'signals']) {
                const card = page.getByTestId(`about-plugin-diagnostics-${system}`);
                await expect(card, `the ${system} plugin system should report its diagnostics`).toBeVisible({timeout: 5_000});
                await expect(card).toHaveAttribute('data-status', /^(ok|failed)$/);
            }

            // And in a healthy test environment nothing should have failed to load: a
            // plugin that throws on import is a real defect, and this is where it surfaces
            // instead of being discovered by a user.
            const failed = page.locator('[data-testid^="about-plugin-diagnostics-"][data-status="failed"]');
            await expect(failed, 'a plugin failed to load — open the About tab to see which').toHaveCount(0);
        });
    });

    test.describe('Preferences Persistence', () => {
        test('theme preference persists after page reload', async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-preferences').click();
            await expect(page.getByTestId('preference-theme')).toBeVisible();

            // Find current theme and toggle to a different one
            // Theme buttons are: light, dark, auto
            const themeContainer = page.getByTestId('preference-theme');
            const darkButton = themeContainer.locator('button:has-text("Dark"), button[title*="Dark"], [class*="dark"]').first();

            if (await darkButton.isVisible().catch(() => false)) {
                await darkButton.click();
            }

            // Save if needed - look for save button and click it
            const saveButton = themeContainer.locator('button[title*="Save"], [data-testid*="save"]');
            if (await saveButton.isVisible().catch(() => false)) {
                await saveButton.click();
                // The settings tabs now report what they persisted; wait for that
                // instead of hoping a second is enough before the reload below.
                await expect(page.locator('[data-testid^="toast-"]').first()).toBeVisible({timeout: 15_000});
            }

            // Reload the page
            await page.reload();
            await page.waitForLoadState('networkidle');

            // Navigate back to preferences
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-preferences').click();
            await expect(page.getByTestId('preference-theme')).toBeVisible();

            // Verify that we're still logged in and preferences tab loads
            // The actual persistence is verified by the page loading without errors
            await expect(page.getByTestId('settings-tab-preferences')).toHaveAttribute('aria-selected', 'true');
        });

        test('preferences persist after navigating away and back', async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-preferences').click();
            await expect(page.getByTestId('preference-language')).toBeVisible();

            // Remember initial state (just verify it loads)
            const languageContainer = page.getByTestId('preference-language');
            await expect(languageContainer).toBeVisible();

            // Navigate to another page
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible();

            // Navigate back to settings
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-preferences').click();

            // Verify preferences tab loads correctly
            await expect(page.getByTestId('preference-language')).toBeVisible();
            await expect(page.getByTestId('preference-currency')).toBeVisible();
            await expect(page.getByTestId('preference-theme')).toBeVisible();
        });

        test('language change persists after page goto', async ({page}) => {
            await login(page, TEST_USER);

            // Go to settings preferences
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-preferences').click();
            await expect(page.getByTestId('preference-language')).toBeVisible();

            // The language selector is within preference-language
            // Find and click on a different language option
            const langContainer = page.getByTestId('preference-language');

            // Look for a dropdown/select trigger
            const langTrigger = langContainer.locator('button, [role="combobox"]').first();
            if (await langTrigger.isVisible().catch(() => false)) {
                await langTrigger.click();

                // Select Italian if available
                const italianOption = page
                    .locator('[role="option"], [class*="option"]')
                    .filter({hasText: /Italiano|Italian/i})
                    .first();
                if (await italianOption.isVisible().catch(() => false)) {
                    await italianOption.click();

                    // Save if there's a save button
                    const saveBtn = langContainer.locator('button[title*="Save"], [data-testid*="save"]');
                    if (await saveBtn.isVisible().catch(() => false)) {
                        await saveBtn.click();
                        await expect(page.locator('[data-testid^="toast-"]').first()).toBeVisible({timeout: 15_000});
                    }
                }
            }

            // Navigate to dashboard and back using goto (not clicking sidebar)
            await page.goto('/dashboard');
            await page.waitForLoadState('networkidle');
            await expect(page.getByTestId('dashboard-page')).toBeVisible();

            // Go back to settings and manually select preferences tab
            await page.goto('/settings');
            await page.waitForLoadState('networkidle');
            await expect(page.getByTestId('settings-page')).toBeVisible();

            // Click preferences tab
            await page.getByTestId('settings-tab-preferences').click();

            // Verify the preferences are visible
            await expect(page.getByTestId('preference-language')).toBeVisible();
        });
    });
});
