import {type APIRequestContext, type BrowserContext, expect, type Locator, type Page, type Request, type Response, test} from './fixtures/playwright';
import {login, navigateTo} from './fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from './fixtures/test-users';
import {eventSeq, waitForEvent} from './fixtures/app-events';
import {optionsClosed} from './fixtures/probe';
import {uniqueSuffix} from './fixtures/unique';
import {deleteDisposableUser, type DisposableUser, registerDisposableUser, skipDueFlowsExcept} from './fixtures/onboarding-accounts';

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

        /**
         * The row of `scheduler_enabled` (category «sync»): the bool that is editable on every lane, named by its key.
         * Since A5b turned `enable_registration` into the `registration_mode` select, «the first toggle» of the tab is
         * `require_email_verification`, a «Coming soon» placeholder whose switch is disabled whatever the lock says: it
         * can be neither clicked nor used to prove the lock. The setting is global and shared by every worker on the
         * lane, so these tests flip and undo a local draft and never press Save.
         */
        function schedulerRow(page: Page) {
            return gs(page).getByTestId('global-setting-scheduler_enabled');
        }

        /** What the switch says now, once it says a boolean, and what one click must turn it into. */
        async function checkedState(toggle: Locator): Promise<{initial: string; flipped: string}> {
            await expect(toggle).toHaveAttribute('aria-checked', /^(true|false)$/);
            const initial = (await toggle.getAttribute('aria-checked')) === 'true' ? 'true' : 'false';
            return {initial, flipped: initial === 'true' ? 'false' : 'true'};
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
            await gs(page).locator('button[title="Click to unlock and edit"]').click();

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
            await gs(page).locator('button[title="Click to unlock and edit"]').click();

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
            // An editable setting, not the placeholder: that one is disabled locked or not, so it proved nothing here.
            const toggle = schedulerRow(page).getByTestId('setting-toggle-switch');
            await expect(toggle).toBeVisible();
            await expect(toggle).toBeDisabled();

            // Control: the lock is what disabled it, since unlocking brings the same switch to life.
            await gs(page).locator('button[title="Click to unlock and edit"]').click();
            await expect(toggle).toBeEnabled();
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
            // `scheduler_enabled`, an editable bool: the tab's first toggle is now a placeholder, disabled for everyone.
            await expect(gs.getByTestId('global-setting-scheduler_enabled').getByTestId('setting-toggle-switch')).toBeDisabled();
            await expect(gs.locator('.setting-row input[type="number"]').first()).toBeDisabled();
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
