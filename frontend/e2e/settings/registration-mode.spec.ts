/**
 * Who can sign up, chosen from Settings → Users and really saved (release 1.3, workstream A, lot N69c; the real twin of
 * the tab's Vitest, which no longer stands in for the server).
 *
 * `e2e_test_admin` acts through the UI; the server answers for itself. Nothing here stubs the mode: no `page.route` on
 * the bulk PATCH, on `GET /system/instance` or on `GET /settings/global`.
 *   RMOD-E-01  «closed» is saved at the choice (no confirmation, one PATCH, `settings.global.saved`) and read back from
 *              the server, Global settings and the public configuration; «open» asks first and writes nothing until it
 *              is confirmed (cancelled: the select goes back, the server is unchanged); confirmed: the server says `open`.
 *
 * Exclusive, and the reason is the setting itself: `global_settings.registration_mode` is one row shared by every user
 * and every spec of the lane (the lane registers openly: auth.spec.ts, admin-users.spec.ts and auth-links.spec.ts
 * register or invite anonymously). While this test holds it at `disabled` or `invite`, any neighbour would meet the
 * wrong mode. The runner declares it (`exclusive_because` of action `registration-mode`, front-utility) and runs it alone.
 *
 * Restoration. The mode in force is read from the server before anything is touched, through the administrator's own
 * API session; the `registration` fixture writes it back in its `finally` — red or green, whatever state the page was
 * left in — and reads it again. The restore goes through the API, never the UI. A test that dies before it recorded the
 * mode has changed nothing, so there is nothing to restore.
 *
 * Precondition, a red and not a skip: the mode must be changeable. `LIBREFOLIO_REGISTRATION` pins it
 * (`accounts.registration_locked`), and the setting then refuses every write.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `registration-mode` of front-utility.
 */
import {expect, test as base, type APIRequestContext, type Page} from '../fixtures/playwright';
import {eventSeq, waitForEvent} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {INSTANCE_CONFIG_PATH, type RegistrationMode} from '../fixtures/instance-config';
import {openSettingsTab} from '../fixtures/settings-tabs';
import {TEST_ADMIN} from '../fixtures/test-users';

const API = '/api/v1';
const SETTINGS_PATH = `${API}/settings/global`;
const BULK_PATH = `${SETTINGS_PATH}/bulk`;
const KEY = 'registration_mode';

// Budgets: deadlines, never delays.
/** From a navigation to a settled tab: the SPA's load, the auth check and the bootstrap, then GET /users and GET /users/invites. */
const LOAD_MS = 20_000;
/** A save's round trip, and the configuration read that follows it. */
const ACTION_MS = 15_000;
/** The reaction to a click on something already on screen. */
const UI_MS = 5_000;
/** The whole flow: a sign-in, six round trips to the server and two tab changes. */
const TEST_MS = 120_000;

const MODES: readonly RegistrationMode[] = ['open', 'invite', 'disabled'];

/** What a test may use. */
type Registration = {
    /** The administrator's API session: preconditions and read-backs, never the action under test. */
    admin: APIRequestContext;
    /** The mode the lane had when the test began, read from the server. */
    original: RegistrationMode;
    /** A new session with no sign-in: what the public configuration is read with. */
    anonymous(): Promise<APIRequestContext>;
};

function asMode(value: unknown, where: string): RegistrationMode {
    if (!MODES.includes(value as RegistrationMode)) throw new Error(`${where} answered ${JSON.stringify(value)}, not one of ${MODES.join(', ')}`);
    return value as RegistrationMode;
}

/** The mode as the server stores it: the global setting, read through an administrator's session. */
async function modeOnServer(admin: APIRequestContext): Promise<RegistrationMode> {
    const response = await admin.get(SETTINGS_PATH);
    expect(response.status(), `GET ${SETTINGS_PATH}: ${await response.text()}`).toBe(200);
    const {items} = (await response.json()) as {items: Array<{key: string; value: string}>};
    return asMode(items.find((item) => item.key === KEY)?.value, `GET ${SETTINGS_PATH} (${KEY})`);
}

/** The public configuration's `accounts` block, read without a session. */
async function publicAccounts(anonymous: APIRequestContext): Promise<{registration_mode: RegistrationMode; registration_locked: boolean}> {
    const response = await anonymous.get(INSTANCE_CONFIG_PATH);
    expect(response.status(), `GET ${INSTANCE_CONFIG_PATH}: ${await response.text()}`).toBe(200);
    const accounts = ((await response.json()) as {accounts?: {registration_mode?: unknown; registration_locked?: boolean}}).accounts;
    return {registration_mode: asMode(accounts?.registration_mode, `GET ${INSTANCE_CONFIG_PATH} (accounts.registration_mode)`), registration_locked: accounts?.registration_locked === true};
}

/** Write the mode through the API, as the administrator. Setup and restore only: the action under test goes through the UI. */
async function writeModeOnServer(admin: APIRequestContext, mode: RegistrationMode): Promise<void> {
    const response = await admin.patch(BULK_PATH, {data: {items: [{key: KEY, value: mode}]}});
    expect(response.status(), `PATCH ${BULK_PATH} (${mode}): ${await response.text()}`).toBe(200);
}

const test = base.extend<{registration: Registration}>({
    registration: async ({playwright, baseURL}, use) => {
        const contexts: APIRequestContext[] = [];
        const open = async (): Promise<APIRequestContext> => {
            const context = await playwright.request.newContext({baseURL});
            contexts.push(context);
            return context;
        };
        let admin: APIRequestContext | undefined;
        let original: RegistrationMode | undefined;
        let restoreFailure: string | null = null;
        try {
            admin = await open();
            const signedIn = await admin.post(`${API}/auth/login`, {data: {username: TEST_ADMIN.username, password: TEST_ADMIN.password}});
            expect(signedIn.status(), `Sign-in of ${TEST_ADMIN.username}, whose API session reads and restores the mode`).toBe(200);
            expect(((await signedIn.json()) as {user: {is_superuser: boolean}}).user.is_superuser, `${TEST_ADMIN.username} must be an administrator`).toBe(true);

            const accounts = await publicAccounts(await open());
            expect(accounts.registration_locked, `The mode must be changeable: LIBREFOLIO_REGISTRATION pins the lane's registration to ${accounts.registration_mode}, and a pinned setting refuses every write. Run this spec on a lane that does not set it`).toBe(false);
            original = await modeOnServer(admin);
            expect(original, 'The public configuration and the stored setting agree on the mode in force').toBe(accounts.registration_mode);
            await use({admin, original, anonymous: open});
        } finally {
            if (admin && original) {
                try {
                    await writeModeOnServer(admin, original);
                    const back = await modeOnServer(admin);
                    if (back !== original) restoreFailure = `the mode was ${original}, the restore wrote it back and the server reads ${back}`;
                    else console.log(`[registration-mode] restored: ${original} (the server reads ${back})`);
                } catch (error) {
                    restoreFailure = `the mode was ${original} and could not be restored: ${String(error)}`;
                }
            }
            await Promise.all(contexts.map((context) => context.dispose()));
        }
        if (restoreFailure) base.info().annotations.push({type: 'registration_mode NOT restored', description: restoreFailure});
        expect(restoreFailure, 'The mode of the lane is put back as the test found it').toBeNull();
    },
});

/** Sign the administrator in through the form and open Settings → Users by its address. Ends on the tab settled. */
async function openUsersTab(page: Page): Promise<void> {
    await login(page, TEST_ADMIN);
    await navigateTo(page, '/settings?tab=users');
    await settledUsersTab(page);
}

async function settledUsersTab(page: Page): Promise<void> {
    await expect(page.getByTestId('settings-tab-users'), `${TEST_ADMIN.username} sees the Users tab, and it is the one open`).toHaveAttribute('aria-selected', 'true', {timeout: LOAD_MS});
    await expect(page.getByTestId('users-tab'), 'The tab settles: its reads are in').toHaveAttribute('data-busy', 'false', {timeout: LOAD_MS});
}

test.describe('Who can sign up, really saved from the Users tab (N69c)', () => {
    test('RMOD-E-01: «closed» is saved at the choice, «open» asks first and writes nothing until confirmed; the server, Global settings and the public configuration agree', async ({page, registration}) => {
        test.setTimeout(TEST_MS);
        const {admin, anonymous} = registration;

        // The test needs to be able to *close* the registration: a lane that began closed is moved to «invite» first,
        // through the API. The fixture still restores the mode it found.
        let start = registration.original;
        if (start === 'disabled') {
            await writeModeOnServer(admin, 'invite');
            start = 'invite';
        }
        expect(await modeOnServer(admin), 'Precondition: the registration is not closed yet').toBe(start);

        await openUsersTab(page);
        const control = page.getByTestId('users-registration');
        await expect(control, 'The control shows the mode in force').toHaveAttribute('data-mode', start, {timeout: LOAD_MS});
        await expect(control).toHaveAttribute('data-locked', 'false', {timeout: UI_MS});
        await expect(control).toHaveAttribute('data-shown', start, {timeout: UI_MS});
        const confirmation = page.getByTestId('users-confirm');
        const choose = async (value: RegistrationMode) => {
            await page.getByTestId('users-registration-mode-button').click();
            await page.getByTestId(`users-registration-option-${value}`).click();
        };
        const isBulkPatch = (request: {url(): string; method(): string}) => new URL(request.url()).pathname === BULK_PATH && request.method() === 'PATCH';

        await test.step('closed: saved at the choice, with no confirmation, and the invitation goes off', async () => {
            const since = await eventSeq(page);
            const sent = page.waitForRequest(isBulkPatch, {timeout: ACTION_MS});
            await choose('disabled');
            expect((await sent).postDataJSON(), 'one bulk PATCH, carrying that mode').toEqual({items: [{key: KEY, value: 'disabled'}]});
            await waitForEvent(page, 'settings.global.saved', {since, timeout: ACTION_MS});
            await expect(confirmation, '«closed» lets nobody in: no confirmation').toHaveCount(0);
            await expect(control, 'the configuration is read again').toHaveAttribute('data-mode', 'disabled', {timeout: ACTION_MS});
            await expect(page.getByTestId('users-invite-button')).toHaveAttribute('data-disabled-reason', 'registration-disabled', {timeout: UI_MS});
            expect(await modeOnServer(admin), 'the server stores it').toBe('disabled');
        });

        await test.step('the public configuration and Global settings read the same mode', async () => {
            expect((await publicAccounts(await anonymous())).registration_mode, 'GET /system/instance, without a session').toBe('disabled');
            await openSettingsTab(page, 'admin');
            await expect(page.getByTestId(`global-setting-${KEY}`), 'Global settings reads the mode just saved').toHaveAttribute('data-value', 'disabled', {timeout: LOAD_MS});
            await openSettingsTab(page, 'users');
            await settledUsersTab(page);
            await expect(control).toHaveAttribute('data-mode', 'disabled', {timeout: UI_MS});
        });

        await test.step('open, cancelled: asked first, nothing written, the select goes back', async () => {
            await choose('open');
            await expect(confirmation, '«open» lets in anyone: asked first').toBeVisible({timeout: UI_MS});
            expect(await modeOnServer(admin), 'nothing is written while the question is open').toBe('disabled');
            await page.getByTestId('confirm-modal-cancel').click();
            await expect(confirmation).toHaveCount(0, {timeout: UI_MS});
            await expect(control, 'the select shows the mode in force again').toHaveAttribute('data-shown', 'disabled', {timeout: UI_MS});
            await expect(control).toHaveAttribute('data-mode', 'disabled', {timeout: UI_MS});
            expect(await modeOnServer(admin), 'cancelling wrote nothing').toBe('disabled');
        });

        await test.step('open, confirmed: saved', async () => {
            const since = await eventSeq(page);
            await choose('open');
            await expect(confirmation).toBeVisible({timeout: UI_MS});
            const sent = page.waitForRequest(isBulkPatch, {timeout: ACTION_MS});
            await page.getByTestId('confirm-modal-confirm').click();
            expect((await sent).postDataJSON(), 'one bulk PATCH, carrying open').toEqual({items: [{key: KEY, value: 'open'}]});
            await waitForEvent(page, 'settings.global.saved', {since, timeout: ACTION_MS});
            await expect(control).toHaveAttribute('data-mode', 'open', {timeout: ACTION_MS});
            await expect(confirmation, 'the confirmation closes').toHaveCount(0, {timeout: UI_MS});
            expect(await modeOnServer(admin), 'the server stores it').toBe('open');
        });

        await test.step('the public configuration and Global settings read open', async () => {
            expect((await publicAccounts(await anonymous())).registration_mode, 'GET /system/instance, without a session').toBe('open');
            await openSettingsTab(page, 'admin');
            await expect(page.getByTestId(`global-setting-${KEY}`), 'Global settings reads the mode just saved').toHaveAttribute('data-value', 'open', {timeout: LOAD_MS});
        });
    });
});
