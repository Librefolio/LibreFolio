import {type APIRequestContext, type BrowserContext, expect, type Locator, type Page, type Request, type Response, test} from './fixtures/playwright';
import {login, navigateTo, setLanguage} from './fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from './fixtures/test-users';
import {eventSeq, waitForEvent} from './fixtures/app-events';
import {optionsClosed} from './fixtures/probe';
import {uniqueSuffix} from './fixtures/unique';
import {deleteDisposableUser, type DisposableUser, registerDisposableUser, skipDueFlowsExcept} from './fixtures/onboarding-accounts';
import {ADMINISTRATION_GROUP_ID, ADMINISTRATION_TAB_IDS, openSettingsTab} from './fixtures/settings-tabs';

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

            // A fresh account is gated on /welcome, and its intro tour would then
            // make the shell inert on any route. Skip every flow still due, for this
            // account only, and read it back: skipping welcome, unlike completing
            // it, writes no user settings (this test's subject). Then enter through
            // the gate on a full load: /welcome forwards to returnTo only once the
            // re-read progress says welcome is done, so leaving it is a positive
            // proof. Landing on /settings directly is not: a gated account briefly
            // renders the shell there before the bootstrap redirects it.
            await skipDueFlowsExcept(page, []);
            await navigateTo(page, '/welcome?returnTo=%2Fsettings');
            await expect(page).toHaveURL((url) => url.pathname === '/settings', {timeout: 15_000});
            const shell = page.getByTestId('app-shell');
            await expect(shell).toBeVisible();
            await expect(shell).toHaveAttribute('data-guide-inert', 'false');

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
        await openSettingsTab(page, 'admin');
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
            await openSettingsTab(page, 'admin');
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
            // The top bar a member sees (decision P13 b): «Administration» stands for Global Settings, its one member here,
            // so there is no second bar and no Global Settings tab of its own.
            const topBar = page.getByRole('tablist').filter({has: page.getByTestId('settings-tab-profile')});
            await expect(topBar).toHaveCount(1);
            await expect(topBar.getByTestId('settings-tab-profile')).toBeVisible();
            await expect(topBar.getByTestId('settings-tab-preferences')).toBeVisible();
            await expect(topBar.getByTestId('settings-tab-plugins')).toBeVisible();
            await expect(topBar.getByTestId('settings-tab-about')).toBeVisible();
            await expect(topBar.getByTestId('settings-tab-administration')).toBeVisible();
            await expect(page.getByTestId('settings-tab-admin')).toHaveCount(0);
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

    test.describe('Password change and sessions', () => {
        // POST /api/v1/auth/change-password ends every session of the account except the one that sent it, which it
        // keeps by setting a new `session` cookie in the same response (release 1.3, workstream A, lot A4b). The HTTP
        // tests (backend/test_scripts/test_api/test_session_revocation_api.py) prove that contract with cookies sent by
        // hand from clients without a jar, so nothing there says what a real browser does with the re-issued cookie:
        // whether it stores it (SameSite and Secure must suit this origin), whether it replaces the old one rather than
        // keeping both (same name, path and domain), and whether the app goes on with it — any 401 sends the app to the
        // login, through the axios interceptor and the layout's auth gate. This test is that proof, on two browser
        // contexts signed in to one account:
        // - A, this test's page, changes the password in Settings → Profile and stays signed in. Red when the response
        //   sets no cookie, or one the browser refuses or keeps beside the old: A's jar still holds the old cookie, and
        //   its next request, refused, lands A on the login.
        // - B, a context of its own signed in before the change, is signed out. Red when the old cookie is still
        //   accepted: B's GET /auth/me answers 200 and its app page opens instead of the login.
        // The account is the test's own, deleted in `finally`: changing a shared E2E user's password would sign out every
        // spec running beside it. Both contexts live and die inside the one test, so the block stays parallel.

        /** The values of the `session` cookies a browser context holds: what its pages, and its `request`, send. */
        async function sessionCookies(context: BrowserContext): Promise<string[]> {
            return (await context.cookies()).filter((cookie) => cookie.name === 'session').map((cookie) => cookie.value);
        }

        /** `api` holds a working session of `user`: GET /auth/me answers 200, with the account's id. */
        async function expectSignedInAs(api: APIRequestContext, user: DisposableUser, what: string): Promise<void> {
            const me = await api.get('/api/v1/auth/me');
            expect(me.status(), what).toBe(200);
            expect(((await me.json()) as {user: {id: number}}).user.id, `${what}, as the account this test registered`).toBe(user.id);
        }

        /**
         * Sign the browser in as `user` through the login form and open Settings → Profile. A fresh account is gated
         * on /welcome: every flow still due is skipped over the API, for this account only, and the page enters
         * through the gate, which forwards to returnTo only once it has re-read that welcome is done — so landing on
         * /settings proves the gate let it in.
         */
        async function openProfile(page: Page, user: DisposableUser): Promise<void> {
            await login(page, user);
            await skipDueFlowsExcept(page, []);
            await navigateTo(page, '/welcome?returnTo=%2Fsettings');
            await expect(page).toHaveURL((url) => url.pathname === '/settings', {timeout: 15_000});
            const shell = page.getByTestId('app-shell');
            await expect(shell).toBeVisible();
            await expect(shell).toHaveAttribute('data-guide-inert', 'false');
            const tab = page.getByTestId('settings-tab-profile');
            await tab.click();
            await expect(tab).toHaveAttribute('aria-selected', 'true');
            // The tab shows the account the change will apply to.
            await expect(page.getByTestId('profile-username')).toHaveValue(user.username, {timeout: 10_000});
        }

        test('changing the password keeps this browser signed in and signs every other session out', async ({page, browser, request}) => {
            // A registration, a sign-in through the form, a skip per due flow, five app documents across the two devices
            // and five API sign-ins: about twice what the 45 s of this file's other disposable-account tests holds, so that
            // on a loaded lane a red still ends on its own assertion — and the clean-up in `finally` still runs.
            test.setTimeout(90_000);
            const user = await registerDisposableUser(request, 'pwchange');
            const newPassword = `Changed7#_${uniqueSuffix()}`;
            let deviceB: BrowserContext | undefined;
            try {
                // Device A, this test's page, on the Profile of the account.
                await openProfile(page, user);
                const cookieOfA = await sessionCookies(page.context());
                expect(cookieOfA, 'Premise: device A holds one session cookie').toHaveLength(1);

                // Device B, a browser context of its own, signed in over the API: the cookie lands in B's jar, which
                // its pages send. Its app page opening on the same Profile makes «signed out» below a change of state,
                // not a page that never worked.
                deviceB = await browser.newContext();
                const signedInB = await deviceB.request.post('/api/v1/auth/login', {data: {username: user.username, password: user.password}});
                expect(signedInB.status(), 'Device B signs in').toBe(200);
                await expectSignedInAs(deviceB.request, user, 'Premise: device B is signed in before the change');
                const pageB = await deviceB.newPage();
                await navigateTo(pageB, '/settings');
                await expect(pageB.getByTestId('app-shell'), 'Premise: device B opens the app before the change').toBeVisible({timeout: 15_000});
                await expect(pageB.getByTestId('profile-username')).toHaveValue(user.username, {timeout: 10_000});

                // On A, the change, through the modal.
                await page.getByTestId('change-password-button').click();
                const modal = page.getByTestId('password-change-modal');
                await expect(modal).toBeVisible();
                const current = modal.getByTestId('password-current');
                const fresh = modal.getByTestId('password-new');
                const confirmation = modal.getByTestId('password-confirm');
                await current.fill(user.password);
                await fresh.fill(newPassword);
                await confirmation.fill(newPassword);
                await expect(current).toHaveValue(user.password);
                await expect(fresh).toHaveValue(newPassword);
                await expect(confirmation).toHaveValue(newPassword);
                const submit = modal.getByTestId('password-change-submit');
                await expect(submit, 'Save is armed: the new password meets the rules and the confirmation matches').toBeEnabled();
                // The response is the subject: it is where the new cookie comes from.
                const answer = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v1/auth/change-password');
                await submit.click();
                expect((await answer).status(), 'POST /auth/change-password accepts the change').toBe(200);
                // A success shows its confirmation and closes the modal by itself; a refusal keeps it open, with the reason.
                await expect(modal, 'The modal closes itself once the password has changed').toBeHidden({timeout: 10_000});

                // A stays signed in. Stored: its jar holds the cookie the response set, in place of the old one —
                // still the old one means the response set none or the browser refused it; two, that it landed beside
                // the old one.
                await expect.poll(() => sessionCookies(page.context()), {message: 'Device A stores the session cookie the change re-issued', timeout: 5_000}).not.toEqual(cookieOfA);
                expect(await sessionCookies(page.context()), 'Device A holds one session cookie: the re-issued one replaced the old').toHaveLength(1);
                // Used: A is still in the app, on the page it changed the password from…
                await expect(page).toHaveURL((url) => url.pathname === '/settings');
                await expect(page.getByTestId('app-shell')).toBeVisible();
                // …and a new document, whose requests carry only what the jar holds, opens another app page, not the login.
                await navigateTo(page, '/dashboard');
                await expect(page.getByTestId('dashboard-page'), 'Device A, which changed the password, still opens the app').toBeVisible({timeout: 15_000});
                await expect(page).toHaveURL((url) => url.pathname === '/dashboard');
                await expect(page.getByTestId('login-page')).toBeHidden();
                await expectSignedInAs(page.request, user, 'Device A is still signed in after the change');

                // B is signed out: the server refuses the cookie it still holds…
                expect((await deviceB.request.get('/api/v1/auth/me')).status(), 'Device B is signed out: the cookie it was issued before the change is refused').toBe(401);
                // …and its browser, opening the same app page again, lands on the login, which keeps the page to come back to.
                await navigateTo(pageB, '/settings');
                await expect(pageB.getByTestId('login-page'), 'Device B is sent to the login').toBeVisible({timeout: 15_000});
                await expect(pageB, 'The login carries the page B was on: /?redirect=%2Fsettings').toHaveURL((url) => url.pathname === '/' && url.searchParams.get('redirect') === '/settings');

                // The credentials moved with the change, from the test's own API client.
                const withOld = await request.post('/api/v1/auth/login', {data: {username: user.username, password: user.password}});
                expect(withOld.status(), 'The old password no longer signs in').toBe(401);
                const withNew = await request.post('/api/v1/auth/login', {data: {username: user.username, password: newPassword}});
                expect(withNew.status(), 'The new password signs in').toBe(200);
                expect(((await withNew.json()) as {user: {id: number}}).user.id).toBe(user.id);
            } finally {
                await deviceB?.close();
                // The account ends with one of two passwords, depending on how far the test got: it is deleted with the
                // one that still signs in, through the test's own API client — never through A or B, whose sessions
                // may be the very thing that broke.
                const changed = (await request.post('/api/v1/auth/login', {data: {username: user.username, password: newPassword}})).ok();
                await deleteDisposableUser(request, changed ? {...user, password: newPassword} : user);
            }
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
            // Global Settings is a member of «Administration» (decision P13 b): opened through the group, in its second bar.
            await openSettingsTab(page, 'admin');

            await expect(page.getByTestId('settings-tab-administration')).toHaveAttribute('aria-selected', 'true');
            await expect(page.getByTestId('settings-subtabs').getByTestId('settings-tab-admin')).toHaveAttribute('aria-selected', 'true');
            await expect(page.getByTestId('global-settings-tab')).toBeVisible();
        });

        test('non-admin can view but not edit global settings', async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            // A member's «Administration» has Global Settings alone: the group's tab opens it, with no second bar.
            await openSettingsTab(page, 'admin');

            const tab = page.getByTestId('global-settings-tab');
            await expect(tab).toBeVisible();
            // Read-only mode: where an administrator finds the lock, the header shows the read-only mark (ShieldOff), and
            // there is no lock to open. The mark comes first: it proves the header is drawn, so the absence that follows
            // is about the lock and not about a header still on its way.
            await expect(tab.getByTestId('settings-readonly-indicator')).toBeVisible();
            await expect(tab.getByTestId('settings-lock-toggle')).toHaveCount(0);
        });
    });

    test.describe('Global Settings — Toggle & Number Interaction', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
            await navigateTo(page, '/settings');
            await openSettingsTab(page, 'admin');
            await expect(page.getByTestId('global-settings-tab')).toBeVisible();
            // The tab publishes its load on its root: `data-busy` is 'true' from the first render until the settings
            // are in. Wait for that state, not for a row's CSS class to turn up.
            await expect(page.getByTestId('global-settings-tab')).toHaveAttribute('data-busy', 'false', {timeout: 10_000});
        });

        /** Helper: scope all locators within global-settings-tab */
        function gs(page: import('@playwright/test').Page) {
            return page.getByTestId('global-settings-tab');
        }

        /**
         * The row of `scheduler_enabled` (category «sync»): the bool that is editable on every lane, named by its key.
         * Since A5b turned `enable_registration` into the `registration_mode` select, «the first toggle» of the tab is
         * `require_email_verification`, a «Coming soon» placeholder whose switch is disabled whatever the lock says: it
         * can be neither clicked nor used to prove the lock (its own test is the placeholder case in
         * `SettingControls.test.ts`). The setting is global and shared by every worker on the lane, so these tests flip
         * and undo a local draft and never press Save.
         */
        function schedulerRow(page: Page) {
            return gs(page).getByTestId('global-setting-scheduler_enabled');
        }

        /**
         * The row of `session_ttl_hours` (category «session»), named by its key: «the first number input of the tab» was
         * this row only by the server's insertion order. Like the toggle, it is edited and undone, never saved.
         */
        function sessionTtlRow(page: Page) {
            return gs(page).getByTestId('global-setting-session_ttl_hours');
        }

        /** The tab's lock, by test id: its title is translated. Every mount starts locked, so one click unlocks it. */
        function lockToggle(page: Page) {
            return gs(page).getByTestId('settings-lock-toggle');
        }

        /** What the switch says now, once it says a boolean, and what one click must turn it into. */
        async function checkedState(toggle: Locator): Promise<{initial: string; flipped: string}> {
            await expect(toggle).toHaveAttribute('aria-checked', /^(true|false)$/);
            const initial = (await toggle.getAttribute('aria-checked')) === 'true' ? 'true' : 'false';
            return {initial, flipped: initial === 'true' ? 'false' : 'true'};
        }

        test('admin can unlock global settings for editing', async ({page}) => {
            // The button tells its state only by its translated title, its icon and its colour. The tab tells it too: while
            // unlocked it raises its editing warning (`InfoBanner` publishes its variant as a test id), locked it has none.
            const lock = lockToggle(page);
            const editingWarning = gs(page).getByTestId('info-banner-warning');
            await expect(lock).toBeVisible();
            // Locked on arrival. The lock is on screen, drawn by the same template as the warning, so the warning's
            // absence is the lock's state and not a late render.
            await expect(editingWarning).toHaveCount(0);
            await lock.click();
            await expect(editingWarning).toBeVisible();
        });

        test('toggle switch changes value when clicked (SettingToggle)', async ({page}) => {
            // Unlock
            await lockToggle(page).click();

            const toggle = schedulerRow(page).getByTestId('setting-toggle-switch');
            // The unlock's post-condition, and the premise of the click below.
            await expect(toggle).toBeEnabled();
            const {flipped} = await checkedState(toggle);

            await toggle.click();

            // The retrying assertion *is* the wait.
            await expect(toggle).toHaveAttribute('aria-checked', flipped);
        });

        test('save and undo buttons appear after toggling', async ({page}) => {
            // Unlock
            await lockToggle(page).click();

            const row = schedulerRow(page);
            const toggle = row.getByTestId('setting-toggle-switch');
            await expect(toggle).toBeEnabled();
            const {flipped} = await checkedState(toggle);
            // Control: unlocked and still clean, the row offers nothing to save, so what appears below is the toggle's doing.
            await expect(row.getByTestId('setting-save')).toBeHidden();

            await toggle.click();
            await expect(toggle).toHaveAttribute('aria-checked', flipped);

            // By test id, inside this row: their titles are translated. Save is never pressed, the setting is shared.
            await expect(row.getByTestId('setting-save')).toBeVisible();
            await expect(row.getByTestId('setting-undo')).toBeVisible();
        });

        test('undo reverts toggle to original value', async ({page}) => {
            // Unlock
            await lockToggle(page).click();

            const row = schedulerRow(page);
            const toggle = row.getByTestId('setting-toggle-switch');
            await expect(toggle).toBeEnabled();
            const {initial, flipped} = await checkedState(toggle);

            // Toggle
            await toggle.click();
            await expect(toggle).toHaveAttribute('aria-checked', flipped);

            // Undo
            await row.getByTestId('setting-undo').click();
            await expect(toggle).toHaveAttribute('aria-checked', initial);
            // Reverted, not just redrawn: the draft is gone, so nothing is left to save.
            await expect(row.getByTestId('setting-save')).toBeHidden();
        });

        test('number input can be edited and undone (SettingNumber)', async ({page}) => {
            // Unlock
            await lockToggle(page).click();

            const row = sessionTtlRow(page);
            const numberInput = row.getByRole('spinbutton');
            await expect(numberInput).toBeVisible();
            await expect(numberInput).toBeEnabled();

            // Read once it holds a number (`inputValue()` does not retry), and edit to a value it cannot already hold
            // rather than to a literal the shared setting might carry.
            await expect(numberInput).toHaveValue(/^\d+$/);
            const originalValue = await numberInput.inputValue();
            await numberInput.fill(String(Number(originalValue) + 1));

            // Save button should appear: by test id, inside this row, since its title is translated. Never pressed.
            await expect(row.getByTestId('setting-save')).toBeVisible();

            // Undo
            await row.getByTestId('setting-undo').click();
            await expect(numberInput).toHaveValue(originalValue);
        });

        test('toggles are disabled when locked', async ({page}) => {
            // An editable setting, not the placeholder: that one is disabled locked or not, so it proved nothing here.
            const toggle = schedulerRow(page).getByTestId('setting-toggle-switch');
            await expect(toggle).toBeVisible();
            await expect(toggle).toBeDisabled();

            // Control: the lock is what disabled it, since unlocking brings the same switch to life.
            await lockToggle(page).click();
            await expect(toggle).toBeEnabled();
        });

        test('number inputs are disabled when locked', async ({page}) => {
            const numberInput = sessionTtlRow(page).getByRole('spinbutton');
            await expect(numberInput).toBeVisible();
            await expect(numberInput).toBeDisabled();
        });
    });

    test.describe('Global Settings — Non-Admin Read-Only', () => {
        test('non-admin sees disabled toggles and inputs', async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await openSettingsTab(page, 'admin');
            const gs = page.getByTestId('global-settings-tab');
            await expect(gs).toBeVisible();
            // The tab's load state, not a row's CSS class.
            await expect(gs).toHaveAttribute('data-busy', 'false', {timeout: 10_000});

            // `scheduler_enabled`, an editable bool: the tab's first toggle is now a placeholder, disabled for everyone.
            await expect(gs.getByTestId('global-setting-scheduler_enabled').getByTestId('setting-toggle-switch')).toBeDisabled();
            // `session_ttl_hours` by key, not «the first number input».
            await expect(gs.getByTestId('global-setting-session_ttl_hours').getByRole('spinbutton')).toBeDisabled();
            // Disabled is also what an administrator sees before unlocking. Read-only is that nothing here unlocks them:
            // the read-only mark stands where the lock would, and the lock is not there.
            await expect(gs.getByTestId('settings-readonly-indicator')).toBeVisible();
            await expect(gs.getByTestId('settings-lock-toggle')).toHaveCount(0);
        });
    });

    test.describe('About Tab', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_USER);
            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-about').click();
            // The tab renders its plugin sections only once its parallel reads are all in,
            // and publishes that on its root. Wait for the state, not for a section to turn
            // up within the default 3 s, which under four workers it did not.
            await expect(page.getByTestId('about-tab')).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
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
        // Theme and language are saved per account, and every later login applies them.
        // The two writers below used to save them on the shared TEST_USER and never put
        // them back: one run of the language case left that user Italian for every later
        // session (layout/connection-security presumes English), while the theme case
        // clicked its row container and saved nothing at all. Each writer now owns a
        // disposable account: preferences seeded over the API before the browser signs
        // in, the account deleted with everything it owns in `finally`.
        const DARK_CLASS = /(?:^|\s)dark(?:\s|$)/;
        const isPreferencesPut = (res: Response) => res.request().method() === 'PUT' && new URL(res.url()).pathname === '/api/v1/settings/user';

        type StoredPreferences = {language: string; theme: string};

        /**
         * Sign the test's own API context in as `user` and set the two preferences under
         * test, so the starting point is stated rather than inherited from the instance
         * defaults. Done before the browser signs in, so its login applies them.
         */
        async function seedPreferences(request: APIRequestContext, user: DisposableUser, seed: StoredPreferences): Promise<void> {
            const loggedIn = await request.post('/api/v1/auth/login', {data: {username: user.username, password: user.password}});
            expect(loggedIn.ok(), 'The seed must authenticate as the account it owns').toBe(true);
            expect(((await loggedIn.json()) as {user: {id: number}}).user.id).toBe(user.id);
            const seeded = await request.put('/api/v1/settings/user', {data: seed});
            expect(seeded.ok(), `Seeding the preferences failed (HTTP ${seeded.status()})`).toBe(true);
            expect(await seeded.json()).toMatchObject(seed);
        }

        /** What the server holds for the account `request` is signed in as. */
        async function readStoredPreferences(request: APIRequestContext): Promise<StoredPreferences> {
            const response = await request.get('/api/v1/settings/user');
            expect(response.ok(), `GET /api/v1/settings/user returned ${response.status()}`).toBe(true);
            return (await response.json()) as StoredPreferences;
        }

        /** Open the tab; its rows render only once it has read the account's values. */
        async function openPreferencesTab(page: Page): Promise<void> {
            await page.getByTestId('settings-tab-preferences').click();
            await expect(page.getByTestId('settings-tab-preferences')).toHaveAttribute('aria-selected', 'true');
            await expect(page.getByTestId('settings-layout')).toHaveAttribute('data-busy', 'false', {timeout: 10_000});
            await expect(page.getByTestId('preference-theme')).toBeVisible();
            await expect(page.getByTestId('preference-language')).toBeVisible();
        }

        /**
         * Sign the browser in as `user` and reach the Preferences tab. A fresh account is
         * gated on /welcome: skip every flow still due over the API (skipping welcome,
         * unlike completing it, writes no preference) and enter through the gate on a
         * full load, which forwards to returnTo only once it has re-read that welcome is
         * done.
         */
        async function enterPreferences(page: Page, user: DisposableUser): Promise<void> {
            await login(page, user);
            await skipDueFlowsExcept(page, []);
            await navigateTo(page, '/welcome?returnTo=%2Fsettings');
            await expect(page).toHaveURL((url) => url.pathname === '/settings', {timeout: 15_000});
            const shell = page.getByTestId('app-shell');
            await expect(shell).toBeVisible();
            await expect(shell).toHaveAttribute('data-guide-inert', 'false');
            await openPreferencesTab(page);
        }

        test('theme preference persists after page reload', async ({page, request}) => {
            // A disposable account costs a registration, two logins and a skip per due flow.
            test.setTimeout(45_000);
            const user = await registerDisposableUser(request, 'theme');
            try {
                await seedPreferences(request, user, {language: 'en', theme: 'light'});
                await enterPreferences(page, user);
                // `<html class>` is where the app publishes the theme in force: applyTheme()
                // and app.html's pre-paint script both write it, Tailwind's class strategy
                // reads it. Here it is the contract, not a styling detail.
                const html = page.locator('html');
                const row = page.getByTestId('preference-theme');
                const dark = row.getByTestId('setting-theme-option-dark');
                // Precondition, read back: the seeded light theme is the one in force.
                await expect(row.getByTestId('setting-theme-option-light')).toHaveAttribute('aria-pressed', 'true');
                await expect(dark).toHaveAttribute('aria-pressed', 'false');
                await expect(html).not.toHaveClass(DARK_CLASS);

                await dark.click();
                await expect(dark).toHaveAttribute('aria-pressed', 'true');
                const since = await eventSeq(page);
                const put = page.waitForResponse(isPreferencesPut);
                await row.getByTestId('setting-save').click();
                const saved = await put;
                expect(saved.ok(), `PUT /api/v1/settings/user returned ${saved.status()}`).toBe(true);
                expect(saved.request().postDataJSON()).toEqual({theme: 'dark'});
                expect((await waitForEvent(page, 'settings.preferences.saved', {since})).detail).toMatchObject({field: 'theme', value: 'dark'});
                await expect(row.getByTestId('setting-save')).toBeHidden();
                await expect(html).toHaveClass(DARK_CLASS);

                // Persisted for the account, not just painted on this page.
                expect(await readStoredPreferences(request)).toMatchObject({theme: 'dark'});

                // A new document: dark from its first paint, and the tab shows the value it
                // re-reads from the server.
                await page.reload();
                await expect(html).toHaveAttribute('data-i18n-ready', 'true', {timeout: 15_000});
                await expect(html).toHaveClass(DARK_CLASS);
                await openPreferencesTab(page);
                await expect(dark).toHaveAttribute('aria-pressed', 'true');
                await expect(row.getByTestId('setting-theme-option-light')).toHaveAttribute('aria-pressed', 'false');
                await expect(row.getByTestId('setting-save')).toBeHidden();
            } finally {
                await deleteDisposableUser(request, user);
            }
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

        test('language change persists after page goto', async ({page, request}) => {
            // A disposable account costs a registration, two logins and a skip per due flow.
            test.setTimeout(45_000);
            const user = await registerDisposableUser(request, 'lang');
            try {
                await seedPreferences(request, user, {language: 'en', theme: 'light'});
                await enterPreferences(page, user);
                // `<html lang>` names the language on screen and `data-i18n-ready` says its
                // dictionary is in (root +layout): the published pair, no text is read.
                const html = page.locator('html');
                const row = page.getByTestId('preference-language');
                const trigger = row.getByRole('combobox');
                await expect(html, 'precondition: the seeded language is the one on screen').toHaveAttribute('lang', 'en');

                await trigger.click();
                // Precondition, read back: the seeded language is the selected option.
                await expect(row.getByTestId('setting-select-option-en')).toHaveAttribute('aria-selected', 'true');
                await row.getByTestId('setting-select-option-it').click();
                await expect(trigger).toHaveAttribute('aria-expanded', 'false');
                const since = await eventSeq(page);
                const put = page.waitForResponse(isPreferencesPut);
                await row.getByTestId('setting-save').click();
                const saved = await put;
                expect(saved.ok(), `PUT /api/v1/settings/user returned ${saved.status()}`).toBe(true);
                expect(saved.request().postDataJSON()).toEqual({language: 'it'});
                expect((await waitForEvent(page, 'settings.preferences.saved', {since})).detail).toMatchObject({field: 'language', value: 'it'});
                await expect(row.getByTestId('setting-save')).toBeHidden();
                await expect(html).toHaveAttribute('lang', 'it');
                await expect(html).toHaveAttribute('data-i18n-ready', 'true');

                // Persisted for the account, not just switched on this page.
                expect(await readStoredPreferences(request)).toMatchObject({language: 'it'});

                // Away and back with full loads (goto, not the sidebar): each one is a new
                // document, and each must come up in Italian.
                await navigateTo(page, '/dashboard');
                await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 10_000});
                await expect(html).toHaveAttribute('lang', 'it');
                await navigateTo(page, '/settings');
                await expect(html).toHaveAttribute('lang', 'it');
                await openPreferencesTab(page);
                await expect(row.getByTestId('setting-save')).toBeHidden();
                // And the tab shows the value it re-reads from the server.
                await trigger.click();
                await expect(row.getByTestId('setting-select-option-it')).toHaveAttribute('aria-selected', 'true');
                await trigger.press('Escape');
                await expect(trigger).toHaveAttribute('aria-expanded', 'false');
            } finally {
                await deleteDisposableUser(request, user);
            }
        });
    });
});

// ---------------------------------------------------------------------------
// Onboarding replay controls (Preferences tab → OnboardingReplaySection)
// ---------------------------------------------------------------------------
//
// TEST_USER is canonical and grandfathered `completed` on every flow (see
// populate_mock_data's `_grandfather_onboarding_for_test_users`). "Replay" exists
// precisely for this account shape: a user who already finished onboarding but
// wants to see it again. Arming it writes only a client-side localStorage entry
// (`onboardingGuide`/`onboarding.svelte.ts`'s `startReplay`, keyed per account) —
// it never calls a `/settings/onboarding/*` transition endpoint, so it can never
// regress a completed flow back to pending. localStorage is shared by the tabs of
// one browser profile, not across Playwright browser contexts: every test gets its
// own context, whose localStorage starts empty (no storageState is loaded) and is
// isolated from every other context, so two tests sharing TEST_USER in parallel
// never see each other's armed replay.
//
// The Welcome case exercises replay Exit, which only clears this context's replay
// token. None of these tests submits replay Continue: doing so on the shared
// canonical account would overwrite its persisted language/currency settings for
// every other test running against it concurrently. Verifying that explicit
// preference write therefore requires a disposable terminal account, not this
// otherwise cheap replay-control block.
const ONBOARDING_FLOW_IDS = [
    'welcome',
    'intro_tour',
    'transactions_page_guide',
    'transaction_create_guide',
    'transaction_bulk_guide',
    'import_guide',
    'broker_page_guide',
    'broker_guide',
    'broker_detail_guide',
    'fx_page_guide',
    'fx_guide',
    'fx_detail_guide',
    'asset_page_guide',
    'asset_guide',
    'asset_detail_guide',
] as const;
const ONBOARDING_STEP_IDS = {
    transaction_bulk_guide: ['transaction.bulk.workspace', 'transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save'],
    import_guide: ['import.upload', 'import.select', 'import.analyze', 'import.assets', 'import.fix', 'import.duplicates', 'import.review', 'import.gapFix', 'import.bulk'],
} as const;

test.describe('Onboarding replay controls', () => {
    async function openOnboardingSection(page: Page) {
        await navigateTo(page, '/settings');
        await page.getByTestId('settings-tab-preferences').click();
        const section = page.getByTestId('onboarding-replay-section');
        await expect(section).toBeVisible({timeout: 10_000});
        await expect(page.getByTestId('onboarding-flow-welcome')).toBeVisible({timeout: 10_000});
        for (const group of ['transactions', 'broker', 'fx', 'asset'] as const) {
            await section.getByTestId(`onboarding-group-${group}`).evaluate((element) => {
                (element as HTMLDetailsElement).open = true;
            });
        }
        return section;
    }

    function trackOnboardingRequests(page: Page): {requests: string[]; stop: () => void} {
        const requests: string[] = [];
        const record = (req: Request) => {
            const path = new URL(req.url()).pathname;
            if (/^\/api\/v1\/settings\/onboarding(?:\/|$)/.test(path)) requests.push(`${req.method()} ${path}`);
        };
        page.on('request', record);
        return {requests, stop: () => page.off('request', record)};
    }

    test('shows all 15 terminal onboarding flows and the Import/Bulk step detail', async ({page}) => {
        await login(page, TEST_USER);
        await openOnboardingSection(page);

        for (const flow of ONBOARDING_FLOW_IDS) {
            const row = page.getByTestId(`onboarding-flow-${flow}`);
            await expect(row).toBeVisible();
            await expect(row).toHaveAttribute('data-status', 'completed');
            await expect(row).toHaveAttribute('data-version', /^\d+$/);
            await expect(row).toHaveAttribute('data-current-version', /^\d+$/);
            // Grandfathered at the current content version: nothing to update, and
            // this fresh browser context has armed no replay yet.
            const [version, currentVersion] = await Promise.all([row.getAttribute('data-version'), row.getAttribute('data-current-version')]);
            expect(version).toBe(currentVersion);
            await expect(page.getByTestId(`onboarding-flow-${flow}-update`)).toHaveCount(0);
            await expect(page.getByTestId(`onboarding-flow-${flow}-armed`)).toHaveCount(0);
        }
        for (const [flow, stepIds] of Object.entries(ONBOARDING_STEP_IDS)) {
            const details = page.getByTestId(`onboarding-flow-${flow}-steps`);
            await details.evaluate((element) => {
                (element as HTMLDetailsElement).open = true;
            });
            for (const stepId of stepIds) {
                await expect(page.getByTestId(`onboarding-step-${flow}-${stepId}`)).toBeVisible();
            }
        }
        await expect(page.getByTestId('onboarding-flow-transaction_bulk_validation_guide')).toHaveCount(0);
        await expect(page.getByTestId('onboarding-flow-transaction_bulk_selection_guide')).toHaveCount(0);
        await expect(page.getByTestId('onboarding-flow-transaction_bulk_save_guide')).toHaveCount(0);
    });

    test('replay welcome Exit clears client-side state and returns without a terminal mutation', async ({page}) => {
        await login(page, TEST_USER);
        await openOnboardingSection(page);
        const tracker = trackOnboardingRequests(page);

        try {
            await page.getByTestId('onboarding-replay-welcome').click();
            await expect(page).toHaveURL(/\/welcome/, {timeout: 10_000});
            await expect(page.getByTestId('welcome-shell')).toBeVisible();
            // The real, pre-filled form — never the "completed"/"skipped" outcome
            // banner — because this account was never actually re-submitted.
            await expect(page.getByTestId('welcome-page')).toHaveAttribute('data-outcome', 'pending');
            await expect(page.getByTestId('welcome-form')).toBeVisible({timeout: 10_000});

            await page.getByTestId('welcome-skip').click();
            await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/, {timeout: 10_000});
            await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 10_000});
        } finally {
            tracker.stop();
        }
        expect(tracker.requests, 'Arming and exiting a Welcome replay must call no onboarding endpoint').toEqual([]);

        const section = await openOnboardingSection(page);
        const welcome = section.getByTestId('onboarding-flow-welcome');
        await expect(welcome).toHaveAttribute('data-status', 'completed');
        await expect(page.getByTestId('onboarding-flow-welcome-armed')).toHaveCount(0);
    });

    test('replay import arms the next import without navigating or mutating anything', async ({page}) => {
        await login(page, TEST_USER);
        await openOnboardingSection(page);
        const tracker = trackOnboardingRequests(page);

        try {
            await expect(page.getByTestId('onboarding-flow-import_guide-armed')).toHaveCount(0);
            await page.getByTestId('onboarding-replay-import_guide').click();
            await expect(page.getByTestId('onboarding-flow-import_guide-armed')).toBeVisible({timeout: 5_000});
            // Unlike welcome, arming the import guide never navigates: it only
            // takes effect the next time an Import Wizard is opened.
            await expect(page).toHaveURL(/\/settings/);
            await expect(page.getByTestId('onboarding-flow-welcome-armed')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-flow-intro_tour-armed')).toHaveCount(0);
        } finally {
            expect(tracker.requests, 'Arming a replay must never call an onboarding endpoint').toEqual([]);
            tracker.stop();
        }
    });

    test('Replay all starts from a clean 15-flow state and routes to /welcome without a terminal mutation', async ({page}) => {
        // Seam, stated rather than faked: this proves the button arms *something*
        // (the observable, safe-to-verify effect — routing to /welcome without a
        // terminal call) and that all per-flow "-armed" badges are absent
        // beforehand. Once armed, `resolveDestination` keeps redirecting any route
        // back to /welcome for as long as the replay stays armed, so there is no
        // way to return to Settings from inside *this* test and read the
        // intro_tour/import_guide badges without either (a) actually completing or
        // skipping welcome — which would overwrite TEST_USER's persisted language/
        // currency for every other concurrent test — or (b) reaching past the
        // testid surface into localStorage directly, which this suite's rules
        // treat as fabrication. The component test verifies every armReplay call
        // and its source order; this browser case verifies the real navigation
        // and no-terminal-write boundary.
        await login(page, TEST_USER);
        await openOnboardingSection(page);
        for (const flow of ONBOARDING_FLOW_IDS) {
            await expect(page.getByTestId(`onboarding-flow-${flow}-armed`)).toHaveCount(0);
        }
        const tracker = trackOnboardingRequests(page);

        try {
            await expect(page.getByTestId('onboarding-replay-all')).toBeEnabled();
            await page.getByTestId('onboarding-replay-all').click();
            await expect(page).toHaveURL(/\/welcome/, {timeout: 10_000});
            await expect(page.getByTestId('welcome-page')).toHaveAttribute('data-outcome', 'pending');
        } finally {
            expect(tracker.requests, 'Arming every replay must never call an onboarding endpoint').toEqual([]);
            tracker.stop();
        }
    });
});

// ---------------------------------------------------------------------------
// G-15: the tab bars keep every tab reachable (workstream A, release 1.3)
// ---------------------------------------------------------------------------
//
// The defect, found by workstream G. The Settings page draws its TabBar inside a card with `overflow-hidden`. From
// `sm` (640 px) up the tabs keep their natural width (`flex-1 sm:flex-none`) and the row did not scroll, so the seven
// tabs of an administrator could be wider than the card: at 1280 px in Spanish the last one, `email`, was pushed past
// the card's edge — only its first letter showed, even while it was the active tab — and between 640 and ~1200 px the
// same happened in the other languages. A clipped tab is reachable only through `?tab=` or the keyboard.
//
// The cure (TabBar's opt-in `scrollable`, which the page passes) wraps the row in a sideways scroll container and keeps
// the active tab scrolled whole into view. Since lot A8b (decision P13 b) the page has two bars, both scrollable: the
// top one — Profile, Preferences, Plugins, About, and «Administration» standing for its members — and, while a member is
// open, the group's own inside `settings-subtabs` — Global Settings, Users, Backup, Email and Security. These cases do
// not depend on that markup: they measure the tab against everything that can hide it — the viewport, the card around
// the bars, and every ancestor that clips (the card, and the scroller of the tab's own bar) — with 1 px of rounding. The
// scroller's own testid and layout are pinned by the component test (`TabBar.test.ts`, G-15).
//
// Why the second case reads the bar before it clicks. Playwright scrolls a target into view before clicking it, and
// it scrolls an `overflow: hidden` box as readily as a scroll container: a script can, a user cannot. A click alone
// would therefore reach every tab, and prove nothing. What tells the two apart is the reading taken first: a tab is
// whole inside its bar, or some container between it and the card scrolls sideways (`overflow-x: auto | scroll`) and
// has more to show — something a user can scroll. Without the cure neither held for a clipped tab: that was the red, at
// the first clipped tab in bar order, before any click had scrolled the card.
//
// The fades (the designer's point 33). A side of a bar that hides tabs fades out over its outer 1.5rem — TabBar's
// `FADE_CLASSES`, `mask-l-from-[calc(100%-1.5rem)]` and `mask-r-from-[calc(100%-1.5rem)]` — and the bar's scroller says
// which sides do in `data-fade` (none, start, end or both). A picked tab must not lie under an active fade: once picked,
// its edge on a faded side lies at least the fade's width inside the scroller's edge, with the same 1 px of rounding.
// Read on the scroller of the tab's own bar (`tab-bar-scroller`), after the pick. Soft: one run lists every pick that
// lies under a fade, with its numbers, and goes on to the next; reaching a tab and seeing it whole stay hard.
//
// Nothing is written. The language goes through the header's selector, which writes `librefolio-locale` in this
// context's localStorage and nothing on the server (the account's saved language is applied only at login, which is
// over by then); opening a tab only reads. `e2e_test_admin`, shared by the whole lane, is left as it was found.

/** The widths of the defect: a desktop in Spanish, and `sm`, the first width at which the tabs show their labels. */
const G15_VIEWPORTS = [
    {width: 1280, height: 800},
    {width: 640, height: 800},
] as const;
/** Boxes are fractional: a tab up to this far past an edge is rounding, not a cut label. */
const G15_TOLERANCE_PX = 1;
/** The group's tab, in the top bar: picked last, since its pick opens the second bar. */
const G15_GROUP_TAB = `settings-tab-${ADMINISTRATION_GROUP_ID}`;
/** The top bar of an administrator, in the registry's order (`settingsTabs.ts`): the group stands where its first member would. */
const G15_TOP_BAR_TABS = ['settings-tab-profile', 'settings-tab-preferences', 'settings-tab-plugins', 'settings-tab-about', G15_GROUP_TAB];
/** The second bar: the members of «Administration» an administrator sees, in the same order — `security` is the last. */
const G15_GROUP_BAR_TABS = ADMINISTRATION_TAB_IDS.map((id) => `settings-tab-${id}`);
/** How far a fade reaches into its bar, in rem: `calc(100%-1.5rem)` in TabBar.svelte's `FADE_CLASSES`, 24 px at a 16 px root. */
const G15_FADE_REM = 1.5;
/** A tab is revealed a frame or two after its change: a deadline on a loaded lane, never a delay. */
const G15_REVEAL_MS = 5_000;
/** What {@link g15WholeInView} returns when nothing hides the tab. */
const G15_WHOLE = 'whole inside the bar';
/** What {@link g15Reachable} returns when the tab is inside the bar, or the user can scroll the bar to it. */
const G15_REACHABLE = 'reachable';
/** What {@link g15ClearOfFades} returns when no active fade covers the tab. */
const G15_CLEAR = 'clear of the fades';

/** Where one Settings tab sits against everything that can hide it. Crosses `evaluate`, so plain data only. */
interface G15Placement {
    /** Whole inside the viewport, the card around the bar and every ancestor that clips, within the tolerance. */
    inside: boolean;
    /** The edge the tab runs furthest past, and by how much: '' when it is inside. */
    past: string;
    /** A container between the tab and the card (included) scrolls sideways and has more to show: a user can scroll it. */
    userScrollable: boolean;
    /** That container and its widths, or why none qualifies. */
    scroll: string;
}

/** Runs inside the page: serialised by `evaluate`, so it references nothing outside itself. */
function g15PlaceInPage(tab: Element, tolerancePx: number): G15Placement {
    const name = (element: Element): string => {
        const testId = element.getAttribute('data-testid');
        if (testId) return `[data-testid="${testId}"]`;
        const role = element.getAttribute('role');
        return `<${element.tagName.toLowerCase()}${role ? ` role="${role}"` : ''}>`;
    };
    const settingsPage = tab.closest('[data-testid="settings-page"]');
    if (!settingsPage) return {inside: false, past: 'the tab is not inside [data-testid="settings-page"]', userScrollable: false, scroll: 'no card around it'};
    // The card: the child of the page that holds the bar, whatever the bar's own markup inside it.
    let card: Element = tab;
    while (card.parentElement && card.parentElement !== settingsPage) card = card.parentElement;

    const box = tab.getBoundingClientRect();
    let worstPx = Number.NEGATIVE_INFINITY;
    let worst = '';
    const against = (what: string, left: number, right: number, top: number, bottom: number): void => {
        const overruns: Array<[number, string]> = [
            [left - box.left, 'left'],
            [box.right - right, 'right'],
            [top - box.top, 'top'],
            [box.bottom - bottom, 'bottom'],
        ];
        for (const [px, edge] of overruns) {
            if (px <= worstPx) continue;
            worstPx = px;
            worst = `${px.toFixed(1)} px past the ${edge} edge of ${what} (the tab spans ${box.left.toFixed(1)}–${box.right.toFixed(1)} px)`;
        }
    };
    against('the viewport', 0, window.innerWidth, 0, window.innerHeight);
    const cardBox = card.getBoundingClientRect();
    against('the card around the bar', cardBox.left, cardBox.right, cardBox.top, cardBox.bottom);

    let scroller: Element | null = null;
    const idle: string[] = [];
    for (let element = tab.parentElement; element && element !== document.body; element = element.parentElement) {
        const style = getComputedStyle(element);
        if (card.contains(element) && (style.overflowX === 'auto' || style.overflowX === 'scroll')) {
            if (element.scrollWidth > element.clientWidth) {
                if (!scroller) scroller = element;
            } else {
                idle.push(`${name(element)} scrolls sideways but holds ${element.scrollWidth} px in ${element.clientWidth} px`);
            }
        }
        const clipsX = style.overflowX !== 'visible';
        const clipsY = style.overflowY !== 'visible';
        if (!clipsX && !clipsY) continue;
        // What a clipping box shows: its padding box, less any scrollbar.
        const clip = element.getBoundingClientRect();
        const left = clip.left + element.clientLeft;
        const top = clip.top + element.clientTop;
        const what = `${element === card ? 'the card around the bar' : name(element)}, which clips (overflow-x: ${style.overflowX})`;
        against(what, clipsX ? left : Number.NEGATIVE_INFINITY, clipsX ? left + element.clientWidth : Number.POSITIVE_INFINITY, clipsY ? top : Number.NEGATIVE_INFINITY, clipsY ? top + element.clientHeight : Number.POSITIVE_INFINITY);
    }
    const inside = worstPx <= tolerancePx;
    return {
        inside,
        past: inside ? '' : worst,
        userScrollable: scroller !== null,
        scroll: scroller ? `${name(scroller)} scrolls sideways: ${scroller.scrollWidth} px of tabs in ${scroller.clientWidth} px` : ['nothing between the tab and the card scrolls sideways', ...idle].join('; '),
    };
}

async function g15Place(page: Page, testId: string): Promise<G15Placement> {
    return page.getByTestId(testId).evaluate(g15PlaceInPage, G15_TOLERANCE_PX);
}

/** {@link G15_WHOLE}, or the edge the tab runs past: a plain value `expect.poll` can retry and print. */
async function g15WholeInView(page: Page, testId: string): Promise<string> {
    const placement = await g15Place(page, testId);
    return placement.inside ? G15_WHOLE : placement.past;
}

/** {@link G15_REACHABLE} when the tab is inside the bar or the user can scroll to it; otherwise what hides it, and why. */
async function g15Reachable(page: Page, testId: string): Promise<string> {
    const placement = await g15Place(page, testId);
    return placement.inside || placement.userScrollable ? G15_REACHABLE : `${placement.past}, and the user cannot scroll to it: ${placement.scroll}`;
}

/**
 * Runs inside the page: {@link G15_CLEAR}, or the active fade of the tab's own bar that covers the tab, in pixels.
 * Serialised by `evaluate`, so it references nothing outside itself.
 */
function g15FadesInPage(tab: Element, args: {fadeRem: number; tolerancePx: number; clear: string}): string {
    const scroller = tab.closest('[data-testid="tab-bar-scroller"]');
    if (!scroller) return 'the tab is not inside a [data-testid="tab-bar-scroller"]';
    const fade = scroller.getAttribute('data-fade');
    if (fade !== 'none' && fade !== 'start' && fade !== 'end' && fade !== 'both') return `its scroller publishes data-fade=${JSON.stringify(fade)}, where none, start, end or both is expected`;
    // The fade's width as the page draws it: 1.5rem at the page's own root font size.
    const fadePx = args.fadeRem * parseFloat(getComputedStyle(document.documentElement).fontSize);
    const bar = scroller.getBoundingClientRect();
    const box = tab.getBoundingClientRect();
    const covered: string[] = [];
    if (fade === 'start' || fade === 'both') {
        const inset = box.left - bar.left;
        if (inset < fadePx - args.tolerancePx) covered.push(`its left edge lies ${inset.toFixed(1)} px inside the scroller's left edge, under the start fade of ${fadePx.toFixed(1)} px`);
    }
    if (fade === 'end' || fade === 'both') {
        const inset = bar.right - box.right;
        if (inset < fadePx - args.tolerancePx) covered.push(`its right edge lies ${inset.toFixed(1)} px inside the scroller's right edge, under the end fade of ${fadePx.toFixed(1)} px`);
    }
    if (covered.length === 0) return args.clear;
    const scrolled = `scrolled ${scroller.scrollLeft.toFixed(1)} of ${scroller.scrollWidth - scroller.clientWidth} px`;
    return `data-fade="${fade}": ${covered.join('; ')} (the tab spans ${box.left.toFixed(1)}–${box.right.toFixed(1)} px, the scroller ${bar.left.toFixed(1)}–${bar.right.toFixed(1)} px, ${scrolled})`;
}

/** {@link G15_CLEAR}, or the fade that covers the tab and by how much: a plain value `expect.poll` can retry and print. */
async function g15ClearOfFades(page: Page, testId: string): Promise<string> {
    return page.getByTestId(testId).evaluate(g15FadesInPage, {fadeRem: G15_FADE_REM, tolerancePx: G15_TOLERANCE_PX, clear: G15_CLEAR});
}

/** The test ids of the tabs `bar` holds, in bar order, read at once: a bar's tabs are drawn together. */
async function g15TabIds(bar: Locator): Promise<string[]> {
    return bar.getByRole('tab').evaluateAll((tabs) => tabs.map((tab) => tab.getAttribute('data-testid') ?? '(a tab without a data-testid)'));
}

/**
 * Pick each of `testIds`, in order, as a user would: reachable before its click — read first, since the click would
 * scroll even a box that only clips (see above) —, then selected, whole inside its bar, and clear of its bar's fades.
 */
async function g15PickEach(page: Page, at: string, testIds: readonly string[]): Promise<void> {
    for (const testId of testIds) {
        await test.step(testId, async () => {
            await expect
                .poll(() => g15Reachable(page, testId), {
                    message: `G-15 (${at}): ${testId} lies whole inside its bar, or a container of the bar scrolls sideways to it — received: what hides it`,
                    timeout: G15_REVEAL_MS,
                })
                .toBe(G15_REACHABLE);
            const tab = page.getByTestId(testId);
            await tab.click();
            await expect(tab).toHaveAttribute('aria-selected', 'true');
            await expect
                .poll(() => g15WholeInView(page, testId), {
                    message: `G-15 (${at}): ${testId}, once picked, lies whole inside the visible box of its bar — received: the edge it runs past`,
                    timeout: G15_REVEAL_MS,
                })
                .toBe(G15_WHOLE);
            await expect.soft
                .poll(() => g15ClearOfFades(page, testId), {
                    message: `G-15 (${at}), the designer's point 33: ${testId}, once picked, lies clear of its bar's active fades — received: the fade that covers it`,
                    timeout: G15_REVEAL_MS,
                })
                .toBe(G15_CLEAR);
        });
    }
}

/**
 * Sign the administrator in, switch the interface to Spanish, and open `/settings?tab=email` at `viewport`. Returns once
 * Email is the open tab — «Administration» selected in the top bar, Email in the second —, the Spanish dictionary is in
 * and the fonts are loaded.
 */
async function g15OpenEmailTabInSpanish(page: Page, viewport: {width: number; height: number}): Promise<void> {
    await login(page, TEST_ADMIN);
    // At the project's own viewport, on the app shell login() lands on: its header holds the selector.
    await setLanguage(page, 'es');
    // Loaded at the width under test: the content column's margin transition across 1024 px never runs.
    await page.setViewportSize(viewport);
    await navigateTo(page, '/settings?tab=email');
    const html = page.locator('html');
    await expect(html, 'precondition: Settings renders in Spanish').toHaveAttribute('lang', 'es');
    await expect(html, 'precondition: the Spanish dictionary has landed').toHaveAttribute('data-i18n-ready', 'true');
    // ?tab= is applied once the tab is visible, that is once the page knows an administrator is signed in.
    await expect(page.getByTestId(G15_GROUP_TAB), 'precondition: ?tab=email selects its group in the top bar').toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
    await expect(page.getByTestId('settings-subtabs').getByTestId('settings-tab-email'), 'precondition: ?tab=email opened Email, in the second bar of an administrator').toHaveAttribute('aria-selected', 'true');
    // The labels are measured in their own font, not in a fallback about to swap.
    await page.evaluate(() => document.fonts.ready.then(() => undefined));
}

test.describe('G-15: the tab bars keep every tab reachable', () => {
    test.skip(({isMobile}) => isMobile, 'Desktop widths, set by each case: the mobile project emulates a phone (touch, DPR 3), where the bar shows icons only and fills its row');
    // A sign-in on a loaded lane can take most of the default 30 s by itself (login()'s ARRIVAL_MS, V-27); the second
    // case then picks the ten tabs of both bars, and a pick under a fade spends its 5 s poll before the run goes on.
    test.setTimeout(90_000);

    for (const viewport of G15_VIEWPORTS) {
        const at = `es, ${viewport.width}x${viewport.height}`;

        test(`the tabs selected by ?tab=email lie whole inside their bars (${at})`, async ({page}) => {
            await g15OpenEmailTabInSpanish(page, viewport);

            // Each bar reveals its own selection, without a click: «Administration» in the top bar, Email in the second.
            for (const testId of [G15_GROUP_TAB, 'settings-tab-email']) {
                await expect
                    .poll(() => g15WholeInView(page, testId), {
                        message: `G-15 (${at}): ${testId}, selected by ?tab=email, lies whole inside the visible box of its bar — received: the edge it runs past`,
                        timeout: G15_REVEAL_MS,
                    })
                    .toBe(G15_WHOLE);
            }
        });

        test(`every tab of both bars fits its bar or the bar scrolls to it, and a picked tab lies whole in view, clear of the fades (${at})`, async ({page}) => {
            await g15OpenEmailTabInSpanish(page, viewport);

            const topBar = page.getByRole('tablist').filter({has: page.getByTestId(G15_GROUP_TAB)});
            await expect(topBar, 'precondition: one tab bar holds «Administration»').toHaveCount(1);
            const topIds = await g15TabIds(topBar);
            expect(topIds, 'precondition: the top bar holds every top tab an administrator sees').toEqual(expect.arrayContaining(G15_TOP_BAR_TABS));
            expect(
                topIds.filter((id) => G15_GROUP_BAR_TABS.includes(id)),
                'precondition: the members of «Administration» stand in its own bar, not in the top one',
            ).toEqual([]);
            // In bar order, the group last: its pick opens the second bar, on its first member.
            await g15PickEach(page, at, [...topIds.filter((id) => id !== G15_GROUP_TAB), G15_GROUP_TAB]);

            const groupBar = page.getByTestId('settings-subtabs').getByRole('tablist');
            await expect(groupBar, 'picking «Administration» draws its second bar').toHaveCount(1);
            await expect(groupBar.getByTestId('settings-tab-admin'), 'the group opens on its first member, Global Settings').toHaveAttribute('aria-selected', 'true');
            const groupIds = await g15TabIds(groupBar);
            expect(groupIds, 'precondition: the second bar holds every member of «Administration» an administrator sees').toEqual(expect.arrayContaining(G15_GROUP_BAR_TABS));
            await g15PickEach(page, at, groupIds);
        });
    }
});

// A6e (release 1.3, workstream A): changing the email asks for the current password.
//
// PUT /api/v1/auth/profile moved the address on the session cookie alone: with the «forgotten password» mail, a few minutes
// at somebody else's unlocked session became the account for good. The server now wants `current_password` beside a new
// email, checked before anything else — 400 with detail.error_code CURRENT_PASSWORD_REQUIRED without it,
// CURRENT_PASSWORD_INVALID when it is wrong — and once the address has changed it ends every other session of the
// account, while this one gets a new `session` cookie in the same response, as POST /auth/change-password does. The
// Profile tab asks for the password while the email differs from the stored one. Its states, field by field, are the
// component test's (ProfileTab.test.ts); what only a browser on the real backend can show is here:
// - the refusal as the backend really answers it, reaching the tab: `profile-error` with its data-error-code, the new
//   address still typed — and nothing changed on the server, nobody signed out;
// - the change: the request carries the password, the address moves (GET /auth/me), this browser stores the re-issued
//   cookie and opens the Profile again on a new document, and a device signed in before the change is signed out.
// The per-row Save buttons carry no data-testid, only a translated title: the email is saved through `profile-save-all`,
// which, with the email alone changed, sends exactly the email's request.
// The account is the test's own, deleted in `finally`: changing a shared E2E user's email would sign out every spec
// running beside it. Both contexts live and die inside the one test, so the block stays parallel.
test.describe('A6e: changing the email asks for the current password', () => {
    const PROFILE_URL = '/settings?tab=profile';

    /** The values of the `session` cookies a browser context holds: what its pages, and its `request`, send. */
    async function sessionCookies(context: BrowserContext): Promise<string[]> {
        return (await context.cookies()).filter((cookie) => cookie.name === 'session').map((cookie) => cookie.value);
    }

    /** GET /auth/me through `api`: its status, and the account it answers for when it answers 200. */
    async function whoAmI(api: APIRequestContext): Promise<{status: number; user: {id: number; email: string} | null}> {
        const me = await api.get('/api/v1/auth/me');
        if (me.status() !== 200) return {status: me.status(), user: null};
        return {status: 200, user: ((await me.json()) as {user: {id: number; email: string}}).user};
    }

    /** The answer to the tab's PUT /api/v1/auth/profile. */
    function isProfilePut(response: Response): boolean {
        return response.request().method() === 'PUT' && new URL(response.url()).pathname === '/api/v1/auth/profile';
    }

    /**
     * Sign the browser in as `user` through the login form and open Settings → Profile by its URL. A fresh account is
     * gated on /welcome: every flow still due is skipped over the API, for this account only, and the page enters
     * through the gate, which forwards to returnTo only once it has re-read that welcome is done — so landing on the
     * Profile proves the gate let it in.
     */
    async function openProfile(page: Page, user: DisposableUser): Promise<void> {
        await login(page, user);
        await skipDueFlowsExcept(page, []);
        await navigateTo(page, `/welcome?returnTo=${encodeURIComponent(PROFILE_URL)}`);
        await expect(page).toHaveURL((url) => url.pathname === '/settings' && url.searchParams.get('tab') === 'profile', {timeout: 15_000});
        const shell = page.getByTestId('app-shell');
        await expect(shell).toBeVisible();
        await expect(shell).toHaveAttribute('data-guide-inert', 'false');
        await expect(page.getByTestId('settings-tab-profile')).toHaveAttribute('aria-selected', 'true');
        // The tab shows the account the change will apply to.
        await expect(page.getByTestId('profile-username')).toHaveValue(user.username, {timeout: 10_000});
        await expect(page.getByTestId('profile-email')).toHaveValue(user.email);
    }

    test('a wrong password is refused and the new address stays typed; the right one moves it, keeps this browser signed in and signs the other device out', async ({page, browser, request}) => {
        // A registration, a sign-in through the form, a skip per due flow, two app documents, two saves, and API sign-ins
        // and reads across two devices: as much as the password-change test above, so that on a loaded lane a red still
        // ends on its own assertion — and the clean-up in `finally` still runs.
        test.setTimeout(90_000);
        const user = await registerDisposableUser(request, 'a6email');
        const newEmail = `a6e_${uniqueSuffix()}@example.com`;
        const wrongPassword = `${user.password}-wrong`;
        let deviceB: BrowserContext | undefined;
        try {
            // Device A, this test's page, on the Profile of the account.
            await openProfile(page, user);
            const tab = page.getByTestId('profile-tab');
            await expect(tab).toHaveAttribute('data-busy', 'false');
            const cookieOfA = await sessionCookies(page.context());
            expect(cookieOfA, 'Premise: device A holds one session cookie').toHaveLength(1);

            // Device B, a browser context of its own, signed in over the API before any change: the cookie lands in B's jar.
            deviceB = await browser.newContext();
            const signedInB = await deviceB.request.post('/api/v1/auth/login', {data: {username: user.username, password: user.password}});
            expect(signedInB.status(), 'Device B signs in').toBe(200);
            expect((await whoAmI(deviceB.request)).status, 'Premise: device B is signed in before the change').toBe(200);

            // A new address: the tab asks for the current password, and the save waits for it.
            await page.getByTestId('profile-edit-toggle').click();
            const emailInput = page.getByTestId('profile-email');
            await expect(emailInput).toBeEnabled();
            await emailInput.fill(newEmail);
            await expect(emailInput).toHaveValue(newEmail);
            const password = page.getByTestId('profile-email-password');
            await expect(password, 'An email change asks for the current password').toBeVisible();
            await expect(password).toHaveAttribute('type', 'password');
            await expect(password).toHaveAttribute('autocomplete', 'current-password');
            await expect(password).toHaveValue('');
            await expect(page.getByTestId('profile-email-password-hint')).toBeVisible();
            const saveAll = page.getByTestId('profile-save-all');
            await expect(saveAll, 'No email save without the current password').toBeDisabled();

            // A wrong password: refused with its code; the new address stays typed for a retry, the password is emptied.
            await password.fill(wrongPassword);
            await expect(password).toHaveValue(wrongPassword);
            await expect(saveAll).toBeEnabled();
            const refusal = page.waitForResponse(isProfilePut);
            await saveAll.click();
            const refused = await refusal;
            expect(refused.request().postDataJSON(), 'The email goes with the password typed beside it').toEqual({email: newEmail, current_password: wrongPassword});
            expect(refused.status(), 'PUT /auth/profile refuses a wrong current password').toBe(400);
            expect(((await refused.json()) as {detail?: {error_code?: string}}).detail?.error_code, 'The refusal names its reason').toBe('CURRENT_PASSWORD_INVALID');
            const banner = page.getByTestId('profile-error');
            await expect(banner, 'The tab shows the refusal with its code').toHaveAttribute('data-error-code', 'CURRENT_PASSWORD_INVALID');
            await expect(tab).toHaveAttribute('data-busy', 'false');
            await expect(emailInput, 'The new address stays typed: only the password has to be typed again').toHaveValue(newEmail);
            await expect(password, 'The wrong password is emptied').toHaveValue('');
            await expect(saveAll).toBeDisabled();
            // Nothing changed on the server, and nobody was signed out.
            const afterRefusal = await whoAmI(page.request);
            expect(afterRefusal.status, 'Device A is still signed in after the refusal').toBe(200);
            expect(afterRefusal.user?.email, 'A refused change leaves the address as it was').toBe(user.email);
            expect((await whoAmI(deviceB.request)).status, 'A refused change signs no device out').toBe(200);

            // The right password: the address moves.
            await password.fill(user.password);
            await expect(password).toHaveValue(user.password);
            await expect(saveAll).toBeEnabled();
            const change = page.waitForResponse(isProfilePut);
            await saveAll.click();
            const changed = await change;
            expect(changed.request().postDataJSON(), 'The email goes with the password typed beside it').toEqual({email: newEmail, current_password: user.password});
            expect(changed.status(), 'PUT /auth/profile accepts the right current password').toBe(200);
            // The save is over once the tab is no longer busy: the request, then the session read again.
            await expect(tab).toHaveAttribute('data-busy', 'false', {timeout: 10_000});
            await expect(emailInput).toHaveValue(newEmail);
            // The address is the stored one now: the field it asked for, there a moment ago, is gone, and no error shows.
            await expect(password).toBeHidden();
            await expect(banner).toBeHidden();

            // A stays signed in. Stored: its jar holds the cookie the response set, in place of the old one…
            await expect.poll(() => sessionCookies(page.context()), {message: 'Device A stores the session cookie the change re-issued', timeout: 5_000}).not.toEqual(cookieOfA);
            expect(await sessionCookies(page.context()), 'Device A holds one session cookie: the re-issued one replaced the old').toHaveLength(1);
            // …used: GET /auth/me through the same browser session answers for the account, at its new address…
            const afterChange = await whoAmI(page.request);
            expect(afterChange.status, 'Device A is still signed in after the change').toBe(200);
            expect(afterChange.user?.id, 'GET /auth/me answers for the account this test registered').toBe(user.id);
            expect(afterChange.user?.email, 'The address moved').toBe(newEmail);
            // …and a new document, whose requests carry only what the jar holds, opens the Profile again, not the login.
            await navigateTo(page, PROFILE_URL);
            await expect(page.getByTestId('profile-tab'), 'Device A, which changed the email, still opens the app').toBeVisible({timeout: 15_000});
            await expect(page).toHaveURL((url) => url.pathname === '/settings');
            await expect(page.getByTestId('login-page')).toBeHidden();
            await expect(page.getByTestId('profile-email')).toHaveValue(newEmail, {timeout: 10_000});

            // B, signed in before the change, is signed out: the server refuses the cookie it still holds.
            expect((await whoAmI(deviceB.request)).status, 'Device B is signed out: the cookie it was issued before the change is refused').toBe(401);
        } finally {
            await deviceB?.close();
            // The username and the password never change here: the account is deleted through the test's own API client,
            // never through A or B, whose sessions may be the very thing that broke.
            await deleteDisposableUser(request, user);
        }
    });
});
