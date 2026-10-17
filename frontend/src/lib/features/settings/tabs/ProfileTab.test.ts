// @vitest-environment jsdom
/**
 * ProfileTab — component test (Vitest + jsdom).
 *
 * The account panel: username, e-mail, avatar, and the two irreversible actions
 * (change password, delete account). It takes no props; everything that decides
 * its behaviour comes from the `currentUser` store, one GET for the avatar, the
 * deletion preview its dialog asks for on opening, and the three writes it
 * issues — all controllable from here.
 *
 * Why a component test and not an E2E. `front-utility settings` already walks the
 * happy path. What it cannot reach is the half of this component that only exists
 * when the server refuses: `saveField` **puts the old value back in the input**
 * on failure, `saveAll` reports saved versus failed fields and reverts refusals,
 * the avatar save reverts, and a refused account deletion has to leave the user
 * signed in, with the deletion dialog still open.
 * Provoking those against a live backend means making it reject a profile PUT on
 * command; here they are four lines of setup. The error banner also disappears on
 * a 5 s timer, which a real clock makes either slow or flaky and fake timers make
 * exact.
 *
 * On not asserting translated text. `$lib/i18n` is mocked with an identity
 * translator, so labels render as their own i18n *key*. The per-row Save/Undo
 * buttons carry `title="common.save"` / `"common.undo"` — a key, stable in
 * EN/IT/FR/ES, never a sentence. Where the component echoes a raw server string
 * (`e.response.data.detail`) the assertion is on that string, because it is the
 * test's own fixture and not a catalogue entry.
 *
 * What it deliberately does NOT assert:
 *   - `PasswordChangeModal` and `ImagePickerWrapper` internals. Each is its own
 *     component with its own lane; here they are only checked for being opened,
 *     and the avatar value is injected through the wrapper's `onchange` contract.
 *   - `AccountDeletionDialog` internals (accounts lot A6b): the preview's lists,
 *     the admin mode and the error codes are `AccountDeletionDialog.test.ts`'s.
 *     Here only what ProfileTab decides: that dialog, in self mode, under the
 *     `profile-delete` prefix, asking for the user's own preview, and a deletion
 *     that ends the session — `auth.logout()`, then `goto('/')`.
 *   - the amber "modified" tint on a row. That is a CSS class, and the observable
 *     half of the same state — the Save button appearing — is asserted instead.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {get, readable, writable} from 'svelte/store';
import {fireEvent, render, screen, waitFor, within} from '$test/component';
import type {SupportedLocale} from '$lib/i18n';

// --- Mocks --------------------------------------------------------------

vi.mock('$lib/i18n', () => {
    const identity = readable((key: string) => key);
    return {
        _: identity,
        t: identity,
        locale: writable('en'),
        date: readable((v: unknown) => String(v)),
        time: readable((v: unknown) => String(v)),
        number: readable((v: unknown) => String(v)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

const notify = vi.fn();
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: (...args: unknown[]) => notify(...args)}));

const checkAuth = vi.fn(async () => undefined);
const logout = vi.fn(async () => undefined);
const user = writable<{username: string; email: string; created_at?: string} | null>(null);
vi.mock('$lib/stores/app/auth', () => ({
    auth: {checkAuth: () => checkAuth(), logout: () => logout()},
    currentUser: {subscribe: (run: (v: unknown) => void) => user.subscribe(run)},
}));

const setDirect = vi.fn();
const storeSnapshot = vi.fn<() => Record<string, unknown> | null>(() => null);
vi.mock('$lib/stores/app/settings', () => ({userSettings: {setDirect: (...a: unknown[]) => setDirect(...a), get: () => storeSnapshot()}}));

const goto = vi.fn(async (_path: string) => undefined);
vi.mock('$app/navigation', () => ({goto: (path: string) => goto(path)}));

// The app's language: `currentLanguage`, the store the rest of the UI writes its dates in.
// Replaced whole, never through `importOriginal`: the real store accepts only `$lib/i18n`'s
// SUPPORTED_LOCALES, which this file mocks as ['en', 'it'], so it would turn 'fr' and 'es' into
// 'en'. Built in `vi.hoisted` because the factory hands the store out as it is, and runs as soon
// as something imports the module — through ProfileTab's own imports, before this file's body.
const appLanguage = await vi.hoisted(async () => (await import('svelte/store')).writable<SupportedLocale>('en'));
vi.mock('$lib/stores/app/language', () => ({currentLanguage: appLanguage}));

import ProfileTab from './ProfileTab.svelte';
import {zodiosApi} from '$lib/api';
// The real interface-locale store, derived from the mocked `currentLanguage` above (`appLanguage`).
import {uiLocaleStore} from '$lib/stores/app/uiLocale';

// --- Helpers ------------------------------------------------------------

const settingsGet = () => vi.mocked(zodiosApi.get_user_settings_endpoint_api_v1_settings_user_get as never) as ReturnType<typeof vi.fn>;
const settingsPut = () => vi.mocked(zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put as never) as ReturnType<typeof vi.fn>;
const profilePut = () => vi.mocked(zodiosApi.update_profile_api_v1_auth_profile_put as never) as ReturnType<typeof vi.fn>;
const deleteMe = () => vi.mocked(zodiosApi.delete_own_account_api_v1_auth_users_me_delete as never) as ReturnType<typeof vi.fn>;
// What the deletion dialog asks on opening (lot A6b), and the administrator's pair it must never use from here.
const previewMe = () => vi.mocked(zodiosApi.preview_own_account_deletion_api_v1_auth_users_me_deletion_preview_get as never) as ReturnType<typeof vi.fn>;
const previewAccount = () => vi.mocked(zodiosApi.preview_account_deletion_api_v1_users__user_id__deletion_preview_get as never) as ReturnType<typeof vi.fn>;
const deleteAccount = () => vi.mocked(zodiosApi.delete_account_api_v1_users__user_id__delete as never) as ReturnType<typeof vi.fn>;

/** What deleting alice's own account would take, as `GET /auth/users/me/deletion-preview` answers. */
const OWN_PREVIEW = {
    user_id: 1,
    username: 'alice',
    brokers_deleted: [{id: 12, name: 'Alice Solo', transactions: 5}],
    brokers_left: [{id: 3, name: 'Family', role: 'VIEWER'}],
    transfers_unpaired: 0,
};

/** An axios-shaped rejection carrying `response.data.detail`. */
function axiosError(detail: unknown, message = 'Request failed with status code 400'): Error {
    return Object.assign(new Error(message), {isAxiosError: true, response: {status: 400, data: {detail}}});
}

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** Mount and wait for the avatar GET issued on mount to have settled. */
async function mount() {
    const utils = render(ProfileTab);
    await waitFor(() => expect(settingsGet()).toHaveBeenCalled());
    return utils;
}

/** Mount and click the pencil, so the two inputs are editable. */
async function mountUnlocked() {
    const utils = await mount();
    await fireEvent.click(screen.getByTestId('profile-edit-toggle'));
    await waitFor(() => expect(screen.getByTestId('profile-username')).toBeEnabled());
    return utils;
}

const username = () => screen.getByTestId('profile-username') as HTMLInputElement;
const email = () => screen.getByTestId('profile-email') as HTMLInputElement;

async function type(input: HTMLInputElement, value: string) {
    await fireEvent.input(input, {target: {value}});
}

/**
 * The current password an e-mail change asks for (lot A6e, contract C4): `profile-email-password`, rendered only
 * while the profile is unlocked and the edit is another address (a change of capitals only is not one: P18, A-25) —
 * null otherwise.
 */
const emailPassword = () => screen.queryByTestId('profile-email-password') as HTMLInputElement | null;

/** What alice types to confirm an e-mail change: the fixture's right password. */
const CURRENT_PASSWORD = 'alice-current-secret';

/** Type into the current-password field of an e-mail change, which must be there: an e-mail is not saved without it (A6e). */
async function typeEmailPassword(value: string) {
    await type(screen.getByTestId('profile-email-password') as HTMLInputElement, value);
}

/**
 * The per-field action button. Both rows render the pair twice — once for the
 * mobile layout and once for the desktop one — so this returns the list and the
 * callers act on the first, which is one *instance of the same control*, not an
 * unfiltered guess.
 */
function fieldButtons(testId: 'profile-username' | 'profile-email', action: 'save' | 'undo'): HTMLElement[] {
    const row = screen.getByTestId(testId).closest('.setting-row') as HTMLElement;
    return within(row).queryAllByTitle(`common.${action}`);
}

function error(): HTMLElement | null {
    return screen.queryByTestId('profile-error');
}

beforeEach(() => {
    vi.clearAllMocks();
    user.set({username: 'alice', email: 'alice@example.com', created_at: '2024-03-05T10:00:00Z'});
    appLanguage.set('en');
    settingsGet().mockResolvedValue({avatar_url: null} as never);
    settingsPut().mockResolvedValue({} as never);
    profilePut().mockResolvedValue({} as never);
    deleteMe().mockResolvedValue({} as never);
    previewMe().mockResolvedValue(OWN_PREVIEW as never);
    storeSnapshot.mockReturnValue(null);
});

afterEach(() => {
    vi.useRealTimers();
});

// =========================================================================
describe('ProfileTab — the edit lock', () => {
    it('starts locked, with both fields read-only', async () => {
        await mount();

        expect(username()).toBeDisabled();
        expect(email()).toBeDisabled();
    });

    it('unlocks both fields on the pencil', async () => {
        await mountUnlocked();

        expect(username()).toBeEnabled();
        expect(email()).toBeEnabled();
    });

    it('re-locks straight away when nothing was changed', async () => {
        await mountUnlocked();

        await fireEvent.click(screen.getByTestId('profile-edit-toggle'));

        await waitFor(() => expect(username()).toBeDisabled());
        // No confirmation was needed, because there was nothing to lose.
        expect(screen.queryByRole('dialog')).toBeNull();
    });

    it('asks before locking over a pending edit', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');

        await fireEvent.click(screen.getByTestId('profile-edit-toggle'));

        expect(screen.getByRole('dialog')).toBeInTheDocument();
        // Still unlocked and still holding the edit: nothing was decided yet.
        expect(username()).toBeEnabled();
        expect(username()).toHaveValue('alice2');
    });

    it('keeps the edit when the user chooses to carry on editing', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');
        await fireEvent.click(screen.getByTestId('profile-edit-toggle'));

        await fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', {name: 'common.continueEditing'}));

        await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
        expect(username()).toHaveValue('alice2');
        expect(username()).toBeEnabled();
    });

    it('throws the edit away and locks when the user confirms', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');
        await type(email(), 'other@example.com');
        await fireEvent.click(screen.getByTestId('profile-edit-toggle'));

        await fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', {name: 'settings.discardAndLock'}));

        await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
        expect(username()).toHaveValue('alice');
        expect(email()).toHaveValue('alice@example.com');
        expect(username()).toBeDisabled();
        expect(profilePut()).not.toHaveBeenCalled();
    });

    it('closes the confirmation on Escape without deciding anything', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');
        await fireEvent.click(screen.getByTestId('profile-edit-toggle'));

        await fireEvent.keyDown(screen.getByRole('dialog'), {key: 'Escape'});

        await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
        expect(username()).toHaveValue('alice2');
        expect(username()).toBeEnabled();
    });

    it('hides the avatar upload target while locked and shows it once unlocked', async () => {
        await mount();
        expect(screen.queryByTestId('profile-avatar-trigger')).toBeNull();

        await fireEvent.click(screen.getByTestId('profile-edit-toggle'));

        await waitFor(() => expect(screen.queryByTestId('profile-avatar-trigger')).not.toBeNull());
    });
});

// =========================================================================
describe('ProfileTab — per-field save and undo', () => {
    it('offers nothing until the value actually differs', async () => {
        await mountUnlocked();

        expect(fieldButtons('profile-username', 'save')).toHaveLength(0);
    });

    it('offers save and undo once the username differs', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');

        expect(fieldButtons('profile-username', 'save').length).toBeGreaterThan(0);
        expect(fieldButtons('profile-username', 'undo').length).toBeGreaterThan(0);
        // The e-mail row is untouched, so it offers nothing.
        expect(fieldButtons('profile-email', 'save')).toHaveLength(0);
    });

    it('sends only the field that changed', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');

        await fireEvent.click(fieldButtons('profile-username', 'save')[0]);

        await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(1));
        expect(profilePut()).toHaveBeenCalledWith({username: 'alice2'});
    });

    it('sends the e-mail with the current password — and no username — from the e-mail row', async () => {
        await mountUnlocked();
        await type(email(), 'new@example.com');
        // Lot A6e: an e-mail is not saved without the current password, which goes in the same request.
        await typeEmailPassword(CURRENT_PASSWORD);

        await fireEvent.click(fieldButtons('profile-email', 'save')[0]);

        await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(1));
        expect(profilePut()).toHaveBeenCalledWith({email: 'new@example.com', current_password: CURRENT_PASSWORD});
    });

    it('re-reads the session so the rest of the app sees the new identity', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');

        await fireEvent.click(fieldButtons('profile-username', 'save')[0]);

        await waitFor(() => expect(checkAuth).toHaveBeenCalledTimes(1));
    });

    it('publishes a saved event naming the field key and a success toast', async () => {
        await mountUnlocked();
        await type(email(), 'new@example.com');
        // A6e: no e-mail save without the current password.
        await typeEmailPassword(CURRENT_PASSWORD);

        await fireEvent.click(fieldButtons('profile-email', 'save')[0]);

        await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
        const event = notify.mock.calls[0][0];
        expect(event.name).toBe('settings.profile.saved');
        // The field name is `$_('auth.email')`, which the identity translator
        // renders as the key: stable in every language.
        expect(event.detail).toEqual({fields: 1, field: 'auth.email'});
        expect(event.toast.variant).toBe('success');
    });

    it('puts the stored value back on undo without touching the server', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');

        await fireEvent.click(fieldButtons('profile-username', 'undo')[0]);

        await waitFor(() => expect(username()).toHaveValue('alice'));
        expect(profilePut()).not.toHaveBeenCalled();
    });

    it('locks the inputs while the request is in flight', async () => {
        const pending = deferred<never>();
        profilePut().mockReturnValue(pending.promise as never);
        await mountUnlocked();
        await type(username(), 'alice2');

        await fireEvent.click(fieldButtons('profile-username', 'save')[0]);

        await waitFor(() => expect(username()).toBeDisabled());
        expect(email()).toBeDisabled();

        pending.resolve(undefined as never);
        await waitFor(() => expect(username()).toBeEnabled());
    });
});

// =========================================================================
describe('ProfileTab — when a per-field save is refused', () => {
    it("shows the server's own explanation", async () => {
        profilePut().mockRejectedValue(axiosError('Username already taken'));
        await mountUnlocked();
        await type(username(), 'bob');

        await fireEvent.click(fieldButtons('profile-username', 'save')[0]);

        await waitFor(() => expect(error()).not.toBeNull());
        expect(error()!).toHaveTextContent('Username already taken');
    });

    it('puts the rejected value back, so the input never lies about the account', async () => {
        // This is the behaviour that makes the failure honest: after the banner,
        // the field shows what the server still holds, not what the user typed.
        profilePut().mockRejectedValue(axiosError('Username already taken'));
        await mountUnlocked();
        await type(username(), 'bob');

        await fireEvent.click(fieldButtons('profile-username', 'save')[0]);

        await waitFor(() => expect(username()).toHaveValue('alice'));
        expect(fieldButtons('profile-username', 'save')).toHaveLength(0);
        expect(notify).not.toHaveBeenCalled();
    });

    it('reverts the e-mail row on its own failure', async () => {
        profilePut().mockRejectedValue(axiosError('Email already registered'));
        await mountUnlocked();
        await type(email(), 'taken@example.com');
        // A6e: no e-mail save without the current password.
        await typeEmailPassword(CURRENT_PASSWORD);

        await fireEvent.click(fieldButtons('profile-email', 'save')[0]);

        await waitFor(() => expect(email()).toHaveValue('alice@example.com'));
    });

    it("falls back to the error's message when the body carries no detail", async () => {
        profilePut().mockRejectedValue(axiosError(undefined, 'Request failed with status code 500'));
        await mountUnlocked();
        await type(username(), 'bob');

        await fireEvent.click(fieldButtons('profile-username', 'save')[0]);

        await waitFor(() => expect(error()).not.toBeNull());
        expect(error()!).toHaveTextContent('Request failed with status code 500');
    });

    it("falls back to the error's message when the failure never reached axios", async () => {
        profilePut().mockRejectedValue(new Error('Network Error'));
        await mountUnlocked();
        await type(username(), 'bob');

        await fireEvent.click(fieldButtons('profile-username', 'save')[0]);

        await waitFor(() => expect(error()).not.toBeNull());
        expect(error()!).toHaveTextContent('Network Error');
    });

    it('falls back to a translated failure when the rejection is not an Error at all', async () => {
        profilePut().mockRejectedValue('just a string');
        await mountUnlocked();
        await type(username(), 'bob');

        await fireEvent.click(fieldButtons('profile-username', 'save')[0]);

        await waitFor(() => expect(error()).not.toBeNull());
        expect(error()!).toHaveTextContent('settings.updateFailed');
    });

    it('takes the banner away by itself after five seconds', async () => {
        vi.useFakeTimers();
        profilePut().mockRejectedValue(axiosError('Username already taken'));
        render(ProfileTab);
        await fireEvent.click(screen.getByTestId('profile-edit-toggle'));
        await type(username(), 'bob');
        await fireEvent.click(fieldButtons('profile-username', 'save')[0]);
        await vi.waitFor(() => expect(error()).not.toBeNull());

        // Four seconds is not enough — the timer, not the machine, decides.
        await vi.advanceTimersByTimeAsync(4_000);
        expect(error()).not.toBeNull();

        await vi.advanceTimersByTimeAsync(1_000);
        await vi.waitFor(() => expect(error()).toBeNull());
    });
});

// =========================================================================
describe('ProfileTab — save all', () => {
    const saveAll = () => screen.queryByTestId('profile-save-all');
    const undoAll = () => screen.queryByTestId('profile-undo-all');

    it('is not offered while locked, even with a pending edit', async () => {
        // The bulk buttons are gated on `!isLocked && hasAnyChanges`; a locked tab
        // cannot have changes anyway, so the absence is the whole assertion.
        await mount();

        expect(saveAll()).toBeNull();
    });

    it('appears as soon as one field differs', async () => {
        await mountUnlocked();
        expect(saveAll()).toBeNull();

        await type(username(), 'alice2');

        await waitFor(() => expect(saveAll()).not.toBeNull());
        expect(undoAll()).not.toBeNull();
    });

    it('sends one request per changed field and nothing for the rest', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');

        await fireEvent.click(saveAll()!);

        await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(1));
        expect(profilePut()).toHaveBeenCalledWith({username: 'alice2'});
    });

    it('sends both fields as two separate requests when both changed', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');
        await type(email(), 'new@example.com');
        // A6e: the e-mail's request carries the current password; the username's never does.
        await typeEmailPassword(CURRENT_PASSWORD);

        await fireEvent.click(saveAll()!);

        await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(2));
        expect(profilePut().mock.calls.map((c) => c[0])).toEqual([{username: 'alice2'}, {email: 'new@example.com', current_password: CURRENT_PASSWORD}]);
        const event = notify.mock.calls[0][0];
        expect(event.name).toBe('settings.profile.saved');
        expect(event.detail).toMatchObject({fields: 2, saved: ['username', 'email'], failed: []});
    });

    it('tries every field, keeps what saved, and reverts what failed', async () => {
        profilePut()
            .mockRejectedValueOnce(axiosError('Username already taken'))
            .mockResolvedValueOnce({} as never);
        await mountUnlocked();
        await type(username(), 'alice2');
        await type(email(), 'new@example.com');
        // A6e: no e-mail save without the current password.
        await typeEmailPassword(CURRENT_PASSWORD);

        await fireEvent.click(saveAll()!);

        await waitFor(() => expect(error()).not.toBeNull());
        expect(profilePut()).toHaveBeenCalledTimes(2);
        expect(profilePut().mock.calls.map((c) => c[0])).toEqual([{username: 'alice2'}, {email: 'new@example.com', current_password: CURRENT_PASSWORD}]);
        expect(username()).toHaveValue('alice');
        expect(email()).toHaveValue('new@example.com');
        expect(checkAuth).toHaveBeenCalledTimes(1);
        const event = notify.mock.calls[0][0];
        expect(event.name).toBe('settings.profile.save.partial');
        expect(event.detail).toMatchObject({fields: 1, saved: ['email'], failed: ['username'], reasons: {username: 'Username already taken'}});
        expect(event.toast.variant).toBe('warning');
    });

    it('reverts every rejected field when the bulk save fails completely', async () => {
        profilePut().mockRejectedValue(axiosError('Username already taken'));
        await mountUnlocked();
        await type(username(), 'alice2');
        await type(email(), 'new@example.com');
        // A6e: no e-mail save without the current password.
        await typeEmailPassword(CURRENT_PASSWORD);

        await fireEvent.click(saveAll()!);

        await waitFor(() => expect(error()).not.toBeNull());
        expect(profilePut()).toHaveBeenCalledTimes(2);
        expect(checkAuth).not.toHaveBeenCalled();
        expect(username()).toHaveValue('alice');
        expect(email()).toHaveValue('alice@example.com');
        expect(saveAll()).toBeNull();
        const event = notify.mock.calls[0][0];
        expect(event.name).toBe('settings.profile.save.failed');
        expect(event.detail).toMatchObject({fields: 0, saved: [], failed: ['username', 'email']});
        expect(event.toast.variant).toBe('error');
    });

    it('puts both fields back on undo all', async () => {
        await mountUnlocked();
        await type(username(), 'alice2');
        await type(email(), 'new@example.com');

        await fireEvent.click(undoAll()!);

        await waitFor(() => expect(username()).toHaveValue('alice'));
        expect(email()).toHaveValue('alice@example.com');
        expect(saveAll()).toBeNull();
    });
});

// =========================================================================
describe('ProfileTab — the avatar', () => {
    it('reads the stored avatar on mount and shows it', async () => {
        settingsGet().mockResolvedValue({avatar_url: 'https://example.test/a.png'} as never);
        await mount();

        await waitFor(() => expect(within(screen.getByTestId('profile-avatar')).getByRole('img')).toHaveAttribute('src', 'https://example.test/a.png'));
    });

    it('shows the placeholder when the account has no avatar', async () => {
        await mount();

        expect(within(screen.getByTestId('profile-avatar')).queryByRole('img')).toBeNull();
    });

    it('ignores an avatar_url that is not a string', async () => {
        // The endpoint is loosely typed; anything but a string must land on the
        // placeholder rather than being handed to <img src>.
        settingsGet().mockResolvedValue({avatar_url: {url: 'nope'}} as never);
        await mount();

        expect(within(screen.getByTestId('profile-avatar')).queryByRole('img')).toBeNull();
    });

    it('survives the avatar GET failing, leaving the rest of the tab usable', async () => {
        settingsGet().mockRejectedValue(new Error('offline'));
        await mount();

        expect(screen.getByTestId('profile-tab')).toBeInTheDocument();
        expect(within(screen.getByTestId('profile-avatar')).queryByRole('img')).toBeNull();
        // The failure is swallowed on purpose: no banner, because nothing the user
        // did has failed yet.
        expect(error()).toBeNull();
    });
});

// =========================================================================
/**
 * Lot A6b: the inline dialog gave way to `AccountDeletionDialog`, the one the Users
 * tab shares, opened in self mode under the `profile-delete` prefix. It is found by
 * those testids — the same ones `e2e/brokers/account-deletion.spec.ts` drives, and
 * through the dialog — and no longer by role, element id or button label, which
 * belonged to the dialog it replaced. The error of a refused deletion now lives in
 * the dialog (`profile-delete-error`), not in the tab's banner.
 */
describe('ProfileTab — deleting the account', () => {
    const dialog = () => screen.getByTestId('profile-delete-dialog');
    const confirmInput = () => within(dialog()).getByTestId('profile-delete-confirm-input') as HTMLInputElement;
    const confirmButton = () => within(dialog()).getByTestId('profile-delete-confirm');
    const deleteError = () => within(dialog()).queryByTestId('profile-delete-error');

    /**
     * Opens the dialog and waits for the preview it asks for on opening to have been
     * answered: a call made after the click, settled, and the dialog no longer busy.
     * The count is sampled before the click, so a second opening waits for its own
     * request and not for the first one's.
     */
    const openDelete = async () => {
        const asked = previewMe().mock.calls.length;
        await fireEvent.click(screen.getByTestId('delete-account-button'));
        await waitFor(() => {
            expect(previewMe().mock.calls.length).toBeGreaterThan(asked);
            expect(previewMe().mock.settledResults.at(-1)?.type).not.toBe('incomplete');
            expect(dialog()).toHaveAttribute('data-busy', 'false');
        });
        return dialog();
    };

    it('asks nothing about a deletion until the dialog is opened', async () => {
        // `mount` waits for the avatar GET of `onMount`: a request made on mount would already be on record.
        await mount();

        expect(screen.getByTestId('delete-account-button')).toBeInTheDocument();
        expect(screen.queryByTestId('profile-delete-dialog')).toBeNull();
        expect(previewMe()).not.toHaveBeenCalled();
    });

    it("opens the shared dialog for the signed-in user's own account, which asks for its own preview", async () => {
        await mount();

        await openDelete();

        expect(previewMe()).toHaveBeenCalledTimes(1);
        expect(previewAccount()).not.toHaveBeenCalled();
        // The answer reached the dialog: the broker that would go is listed under this tab's prefix.
        expect(
            within(dialog())
                .getAllByTestId('profile-delete-broker-deleted')
                .map((item) => item.getAttribute('data-broker-id')),
        ).toEqual(['12']);
        // Self mode: nobody is offered to deactivate their own account instead.
        expect(within(dialog()).queryByTestId('profile-delete-deactivate')).toBeNull();
    });

    it('refuses until the username is typed exactly', async () => {
        await mount();
        await openDelete();

        expect(confirmButton()).toBeDisabled();

        await type(confirmInput(), 'alic');
        expect(confirmButton()).toBeDisabled();

        await type(confirmInput(), 'Alice');
        expect(confirmButton()).toBeDisabled();

        await type(confirmInput(), 'alice');
        await waitFor(() => expect(confirmButton()).toBeEnabled());
    });

    it('deletes, logs out and leaves the app once confirmed', async () => {
        await mount();
        await openDelete();
        await type(confirmInput(), 'alice');
        await waitFor(() => expect(confirmButton()).toBeEnabled());

        await fireEvent.click(confirmButton());

        await waitFor(() => expect(goto).toHaveBeenCalledWith('/'));
        expect(deleteMe()).toHaveBeenCalledTimes(1);
        expect(deleteAccount()).not.toHaveBeenCalled();
        expect(logout).toHaveBeenCalledTimes(1);
        // The session ends before the app is left: logout first, then the navigation.
        expect(logout.mock.invocationCallOrder[0]).toBeLessThan(goto.mock.invocationCallOrder[0]);
    });

    it('keeps the user logged in and explains itself when the deletion is refused', async () => {
        // The server's own refusal: the only active administrator stays (400, a sentence, no error_code).
        deleteMe().mockRejectedValue(axiosError('Cannot delete account: you are the only administrator'));
        await mount();
        await openDelete();
        await type(confirmInput(), 'alice');
        await waitFor(() => expect(confirmButton()).toBeEnabled());

        await fireEvent.click(confirmButton());

        await waitFor(() => expect(deleteError()).not.toBeNull());
        // The explanation is in the dialog, which stays open — and the user is still signed in, still here.
        expect(dialog()).toBeInTheDocument();
        expect(logout).not.toHaveBeenCalled();
        expect(goto).not.toHaveBeenCalled();
        // Nothing was deleted and the name is still typed: the button is usable again for a retry.
        await waitFor(() => expect(confirmButton()).toBeEnabled());
    });

    it('still explains itself when the rejection carries nothing usable', async () => {
        deleteMe().mockRejectedValue('opaque');
        await mount();
        await openDelete();
        await type(confirmInput(), 'alice');
        await waitFor(() => expect(confirmButton()).toBeEnabled());

        await fireEvent.click(confirmButton());

        await waitFor(() => expect(deleteError()).not.toBeNull());
        expect(dialog()).toBeInTheDocument();
        expect(logout).not.toHaveBeenCalled();
    });

    it('forgets what was typed when the dialog is dismissed', async () => {
        await mount();
        await openDelete();
        await type(confirmInput(), 'alice');

        await fireEvent.click(within(dialog()).getByTestId('profile-delete-cancel'));

        await waitFor(() => expect(screen.queryByTestId('profile-delete-dialog')).toBeNull());
        await openDelete();
        // A fresh, empty confirmation: the arming does not survive a cancel.
        expect(confirmInput()).toHaveValue('');
        expect(confirmButton()).toBeDisabled();
        expect(deleteMe()).not.toHaveBeenCalled();
        // Each opening asks again: what a deletion would take may have changed in between.
        expect(previewMe()).toHaveBeenCalledTimes(2);
    });

    it('closes on Escape as well as on Cancel', async () => {
        await mount();
        await openDelete();

        await fireEvent.keyDown(dialog(), {key: 'Escape'});

        await waitFor(() => expect(screen.queryByTestId('profile-delete-dialog')).toBeNull());
        expect(deleteMe()).not.toHaveBeenCalled();
    });

    it('disables the confirmation while the deletion is in flight, and ends the session only once it is done', async () => {
        const pending = deferred<never>();
        deleteMe().mockReturnValue(pending.promise as never);
        await mount();
        await openDelete();
        await type(confirmInput(), 'alice');
        await waitFor(() => expect(confirmButton()).toBeEnabled());

        await fireEvent.click(confirmButton());

        await waitFor(() => {
            expect(deleteMe()).toHaveBeenCalledTimes(1);
            expect(confirmButton()).toBeDisabled();
        });
        expect(logout).not.toHaveBeenCalled();

        pending.resolve(undefined as never);

        await waitFor(() => expect(goto).toHaveBeenCalledWith('/'));
        expect(logout).toHaveBeenCalledTimes(1);
    });
});

// =========================================================================
describe('ProfileTab — the read-only corners', () => {
    it('shows a dash when the account has no creation date', async () => {
        user.set({username: 'alice', email: 'alice@example.com'});
        await mount();

        expect(screen.getByText('settings.accountCreated').closest('.setting-row')).toHaveTextContent('-');
    });

    it('opens the password modal from the security section', async () => {
        await mount();

        await fireEvent.click(screen.getByTestId('change-password-button'));

        await waitFor(() => expect(screen.queryByTestId('password-change-modal')).not.toBeNull());
    });

    it('follows the session when the user is renamed elsewhere', async () => {
        // `$: {const user = $currentUser; ...}` re-reads the stored values whenever
        // the auth store moves, which is what makes the row stop looking modified
        // after a successful rename.
        await mountUnlocked();
        await type(username(), 'alice2');
        expect(fieldButtons('profile-username', 'save').length).toBeGreaterThan(0);

        user.set({username: 'alice2', email: 'alice@example.com', created_at: '2024-03-05T10:00:00Z'});

        await waitFor(() => expect(fieldButtons('profile-username', 'save')).toHaveLength(0));
    });

    it('starts from empty strings when there is no session at all', async () => {
        user.set(null);
        await mount();

        expect(username()).toHaveValue('');
        expect(email()).toHaveValue('');
    });
});

// =========================================================================
/**
 * The creation date is written in the app's language, like the rest of the UI
 * (`LotCustodyModal` writes the same long date with
 * `toLocaleDateString($currentLanguage || undefined, …)`), not in the browser's
 * locale — here, the test process's.
 *
 * The expected text is Intl's own output for the language, computed here and
 * never written down: a date format is not a catalogue string, but it is not
 * this test's to spell either.
 *
 * What keeps it from passing vacuously: a language the environment already
 * writes the same way cannot tell the two apart, so the first case proves that
 * at least one of the four can, on the machine it runs on, and names that
 * machine's locale.
 */
describe('ProfileTab — the creation date, in the app language', () => {
    /** Midday UTC: the same calendar day from UTC−11 to UTC+11 — and the expectation goes through the same `new Date(…)`, so the two agree everywhere. */
    const CREATED_AT = '2024-03-05T12:00:00Z';
    /** What `formatDate` asks `toLocaleDateString` for: a long date, no time. */
    const LONG_DATE: Intl.DateTimeFormatOptions = {year: 'numeric', month: 'long', day: 'numeric'};
    /** `currentLanguage`'s values, written out because this file mocks `$lib/i18n`'s SUPPORTED_LOCALES as ['en', 'it']. */
    const APP_LANGUAGES: SupportedLocale[] = ['en', 'it', 'fr', 'es'];

    /** The long date in `lang`; `undefined` is the environment's locale, what the browser's would be. */
    const longDate = (lang: SupportedLocale | undefined) => new Date(CREATED_AT).toLocaleDateString(lang, LONG_DATE);
    const ENV_LOCALE = new Intl.DateTimeFormat().resolvedOptions().locale;
    const ENV_DATE = longDate(undefined);

    /**
     * jest-dom collapses the whitespace of the element's text, not of the
     * expected string, and Intl may separate with a no-break space (U+00A0,
     * U+202F): the expectation is collapsed the same way.
     */
    const squash = (text: string) => text.replace(/\s+/g, ' ').trim();

    /**
     * The row has no `data-testid`: it is found the way the read-only-corners
     * test finds it, by its label — the identity translator renders the key
     * `settings.accountCreated` — and the `.setting-row` around it, this file's
     * established pattern (see `fieldButtons`).
     */
    const createdRow = () => screen.getByText('settings.accountCreated').closest('.setting-row') as HTMLElement;

    /** The row shows `lang`'s long date — and not the environment's, where the two differ. */
    function expectDateIn(row: HTMLElement, lang: SupportedLocale) {
        expect(row).toHaveTextContent(squash(longDate(lang)));
        if (longDate(lang) !== ENV_DATE) expect(row).not.toHaveTextContent(squash(ENV_DATE));
    }

    beforeEach(() => {
        user.set({username: 'alice', email: 'alice@example.com', created_at: CREATED_AT});
    });

    it(`can tell the app language from the environment's on this machine (environment locale: ${ENV_LOCALE})`, () => {
        const discriminating = APP_LANGUAGES.filter((lang) => longDate(lang) !== ENV_DATE);

        expect(discriminating, `the environment (${ENV_LOCALE}) writes "${ENV_DATE}" exactly like every app language: no case below could fail`).not.toHaveLength(0);
    });

    it.each(APP_LANGUAGES)('writes it in the app language set before mount: %s', async (lang) => {
        appLanguage.set(lang);

        await mount();

        expectDateIn(createdRow(), lang);
    });

    it('rewrites it in place when the app language changes after mount', async () => {
        // Two languages that write the date differently, or the change would be invisible.
        expect(longDate('fr'), 'it and fr write the date alike here').not.toBe(longDate('it'));
        appLanguage.set('it');
        await mount();
        const row = createdRow();
        // Soft: a row that already ignores the language at mount must still show whether it ignores the change too.
        expect.soft(row, 'at mount').toHaveTextContent(squash(longDate('it')));

        appLanguage.set('fr');

        // On the node captured before the change: rewritten in place, no remount. In this
        // legacy component only a store the template expression reads is tracked; read
        // inside `formatDate`'s body, it would freeze at mount.
        await waitFor(() => expectDateIn(row, 'fr'));
        expect(row).not.toHaveTextContent(squash(longDate('it')));
    });
});

// =========================================================================
/**
 * M-18 CP2 — the creation date in the interface locale, the browser's region included.
 *
 * The rule (the developer's, 2026-10-12): every figure is written in the interface locale — the UI
 * language, with the browser's region when the browser speaks that language, else the language's own
 * default: `en-GB` for English, the bare language for the others (uiLocale.test.ts). The block above
 * proves the date follows the language; it cannot see the region, because jsdom's browser is en-US and
 * an English UI on it writes like a bare `en`. On an Italian browser they part: ProfileTab passes
 * `$currentLanguage`, so the English UI writes the American long date `en` means to Intl
 * (`March 5, 2024`), where the rule says British (`5 March 2024`). The cure: the template passes
 * `$uiLocaleStore`.
 *
 * The browser. `navigator.language` is spied to `it-IT` for each test, before anything subscribes to the
 * locale, and restored after it. A control reads the resolved interface locale through the real
 * `uiLocaleStore` (derived from this file's `appLanguage`), so a red below is about ProfileTab, not the
 * stub.
 *
 * ProfileTab is a legacy component: only a store read in the template expression is tracked, so the
 * in-place switch tells `$uiLocaleStore` from a read inside `formatDate`'s body, which a mount passes
 * either way. Expectations are Intl's output for the locale, never typed, collapsed like jest-dom
 * collapses the text it reads.
 */
describe('ProfileTab — the creation date in the interface locale, the browser’s region included (M-18 CP2)', () => {
    /** Midday UTC: the same calendar day from UTC−11 to UTC+11. */
    const CREATED_AT = '2024-03-05T12:00:00Z';
    const LONG_DATE: Intl.DateTimeFormatOptions = {year: 'numeric', month: 'long', day: 'numeric'};
    /** The long date in `locale`, as Intl writes it in this runtime. */
    const longDate = (locale: string) => new Date(CREATED_AT).toLocaleDateString(locale, LONG_DATE);
    const squash = (text: string) => text.replace(/\s+/g, ' ').trim();
    /** Found by its label, as the block above finds it: the identity translator renders the key. */
    const createdRow = () => screen.getByText('settings.accountCreated').closest('.setting-row') as HTMLElement;

    let restoreBrowser: () => void = () => undefined;

    beforeEach(() => {
        const browserLanguage = vi.spyOn(navigator, 'language', 'get').mockReturnValue('it-IT');
        restoreBrowser = () => browserLanguage.mockRestore();
        user.set({username: 'alice', email: 'alice@example.com', created_at: CREATED_AT});
    });

    afterEach(() => {
        restoreBrowser();
    });

    it('control: on an Italian browser the English UI resolves to en-GB, the Italian UI to it-IT', () => {
        expect(navigator.language, 'the browser is Italian').toBe('it-IT');
        expect(get(uiLocaleStore), 'English UI').toBe('en-GB');
        appLanguage.set('it');
        expect(get(uiLocaleStore), 'Italian UI').toBe('it-IT');
        expect(longDate('en-GB'), 'British and American long dates differ').not.toBe(longDate('en'));
    });

    it('English UI on an Italian browser: the British long date, not the American one a bare `en` writes', async () => {
        expect(get(uiLocaleStore), 'control: the interface locale is British').toBe('en-GB');

        await mount();

        const row = createdRow();
        expect(row).toHaveTextContent(squash(longDate('en-GB')));
        expect(row).not.toHaveTextContent(squash(longDate('en')));
    });

    it('follows an in-place switch of the UI language, en → it → en, with the browser’s region', async () => {
        await mount();
        const row = createdRow();
        // Soft: a row that ignores the region at mount must still show whether it follows the switch.
        expect.soft(row, 'en, mount — British').toHaveTextContent(squash(longDate('en-GB')));

        appLanguage.set('it');
        await waitFor(() => expect(row, 'en → it in place — it-IT').toHaveTextContent(squash(longDate('it-IT'))));

        appLanguage.set('en');
        await waitFor(() => expect(row, 'it → en in place — British again').toHaveTextContent(squash(longDate('en-GB'))));
        expect(row).not.toHaveTextContent(squash(longDate('en')));
    });
});

// =========================================================================
/**
 * Lot A6e (release 1.3, workstream A) — changing the e-mail asks for the current password.
 *
 * Why. `PUT /auth/profile` moved the address on the session cookie alone: with the «forgotten password» mail, a few
 * minutes at somebody else's unlocked session became the account for good. The server now wants `current_password`
 * beside a new `email` — 400 `{error_code: CURRENT_PASSWORD_REQUIRED}` without it, `CURRENT_PASSWORD_INVALID` when it
 * is wrong — and once the address has changed it signs the account's other sessions out. This block is the tab's half
 * of the contract (C4):
 *   - the field `profile-email-password` (`type="password"`, `autocomplete="current-password"`) and its hint
 *     `profile-email-password-hint`: there exactly while the profile is unlocked and the edit is another address (a
 *     change of capitals only is not one: P18, A-25, the block «a change of capitals only (P18)» below); gone once it
 *     is the stored one again (typed back, its undo, undo all), and empty when it comes back;
 *   - no e-mail save without it: while it is empty, the e-mail row's two Saves (the mobile and the desktop variant)
 *     and save-all are off; a username change alone never asks for it;
 *   - the request: `{email, current_password}` from the row and from save-all; the username's stays `{username}`;
 *   - afterwards: emptied once the e-mail is saved; on a refusal with one of the two codes the banner carries
 *     `data-error-code`, the new address stays for a retry and the password is emptied; a refusal without a code is
 *     today's (the server's sentence, the address put back); a code the tab does not know is a generic text, never
 *     «[object Object]».
 *
 * The cases of the blocks above that save an e-mail type the password first, for the same reason.
 *
 * Choices this block makes where the contract leaves room:
 *   - a coded refusal is worded by the tab, from its code: the server's English sentence must not stand in for it (the
 *     contract keeps the server's sentence for the refusal without a code);
 *   - `data-error-code` names only a refusal the tab knows how to word. A code it does not know publishes none, like a
 *     refusal without a code — the attribute absent or empty — as the accounts dialogs already do
 *     (`data-error-code={error.code ?? ''}`, where `describeAccountError` reads an unknown code as `null`). Whoever reads
 *     a code can then trust that the tab understood it; the unknown code itself is the server log's to keep.
 *
 * The real `auth.checkAuth()` re-reads /auth/me into the session store after a save. The mock does nothing, so a case
 * about what follows a saved address has it store that address, as the real one would.
 *
 * Not asserted: the words of the hint and of the errors (catalogue entries — the code is the contract), and where in
 * the e-mail row the field sits.
 */
describe('ProfileTab — changing the e-mail asks for the current password (A6e)', () => {
    /** The two controls that save an e-mail change: the e-mail row's Save (its first variant, see `fieldButtons`), and save-all, which with the e-mail alone changed sends the e-mail's request alone. */
    const EMAIL_SAVES = [
        {via: "the e-mail row's Save", save: () => fieldButtons('profile-email', 'save')[0]},
        {via: 'save all', save: () => screen.getByTestId('profile-save-all')},
    ];

    /** The refusals of a wrong or a missing current password, each with a sentence of the server's that the tab must not show in place of its own words. */
    const PASSWORD_REFUSALS = [
        {code: 'CURRENT_PASSWORD_INVALID', message: 'Current password is incorrect'},
        {code: 'CURRENT_PASSWORD_REQUIRED', message: 'Current password is required to change the email'},
    ];

    const hint = () => screen.queryByTestId('profile-email-password-hint');
    const saveAllButton = () => screen.getByTestId('profile-save-all');

    /** The e-mail row's Saves, checked as a pair (mobile, desktop), so that «every one is off» never passes on an empty list. */
    function emailSaves(): HTMLElement[] {
        const saves = fieldButtons('profile-email', 'save');
        expect(saves, "the e-mail row's Save, in its mobile and its desktop variant").toHaveLength(2);
        return saves;
    }

    /** What the real `auth.checkAuth()` does once `address` is saved: the session store holds it. */
    function storeAddressOnCheckAuth(address: string) {
        checkAuth.mockImplementation(async () => {
            user.set({username: 'alice', email: address, created_at: '2024-03-05T10:00:00Z'});
            return undefined;
        });
    }

    afterEach(() => {
        // What a case left on the mocks and never consumed — a stored address, a queued refusal — must not reach the next one.
        checkAuth.mockReset();
        checkAuth.mockImplementation(async () => undefined);
        profilePut().mockReset();
    });

    describe('the field', () => {
        it('is not there while locked, nor once unlocked with nothing changed', async () => {
            await mount();
            expect(emailPassword()).toBeNull();

            await fireEvent.click(screen.getByTestId('profile-edit-toggle'));
            await waitFor(() => expect(email()).toBeEnabled());

            expect(emailPassword()).toBeNull();
            expect(hint()).toBeNull();
        });

        it('appears once the edit is another address: an empty password input the browser fills with the current password, and its hint', async () => {
            await mountUnlocked();

            await type(email(), 'new@example.com');

            await waitFor(() => expect(emailPassword(), 'an e-mail change asks for the current password').not.toBeNull());
            const field = emailPassword();
            expect(field).toHaveAttribute('type', 'password');
            expect(field).toHaveAttribute('autocomplete', 'current-password');
            expect(field).toHaveValue('');
            expect(field).toBeEnabled();
            expect(hint()).toBeInTheDocument();
        });

        const BACK_TO_STORED = [
            {how: 'typed back', act: () => type(email(), 'alice@example.com')},
            {how: "the e-mail's undo", act: () => fireEvent.click(fieldButtons('profile-email', 'undo')[0])},
            {how: 'undo all', act: () => fireEvent.click(screen.getByTestId('profile-undo-all'))},
        ];

        it.each(BACK_TO_STORED)('goes once the e-mail is the stored one again ($how), and comes back empty', async ({act}) => {
            await mountUnlocked();
            await type(email(), 'new@example.com');
            await typeEmailPassword(CURRENT_PASSWORD);
            expect(emailPassword()).toHaveValue(CURRENT_PASSWORD);

            await act();

            await waitFor(() => expect(emailPassword()).toBeNull());
            expect(email()).toHaveValue('alice@example.com');
            expect(hint()).toBeNull();

            await type(email(), 'other@example.com');

            await waitFor(() => expect(emailPassword()).not.toBeNull());
            // What was typed before the e-mail went back did not stay behind the scenes.
            expect(emailPassword()).toHaveValue('');
        });
    });

    describe('no e-mail save without it', () => {
        it('keeps both e-mail Saves and save-all off while it is empty, turns them on once it is typed, and off again once emptied', async () => {
            await mountUnlocked();
            await type(email(), 'new@example.com');

            for (const save of emailSaves()) expect(save).toBeDisabled();
            expect(saveAllButton()).toBeDisabled();
            // Only saving waits for the password: going back never does.
            for (const undo of fieldButtons('profile-email', 'undo')) expect(undo).toBeEnabled();
            expect(screen.getByTestId('profile-undo-all')).toBeEnabled();

            await typeEmailPassword(CURRENT_PASSWORD);

            await waitFor(() => expect(saveAllButton()).toBeEnabled());
            for (const save of emailSaves()) expect(save).toBeEnabled();

            await typeEmailPassword('');

            await waitFor(() => expect(saveAllButton()).toBeDisabled());
            for (const save of emailSaves()) expect(save).toBeDisabled();
        });

        it('with both fields changed and no password, save-all waits, while the username row still saves alone — without a password', async () => {
            await mountUnlocked();
            await type(username(), 'alice2');
            await type(email(), 'new@example.com');

            expect(saveAllButton()).toBeDisabled();
            const usernameSaves = fieldButtons('profile-username', 'save');
            expect(usernameSaves).toHaveLength(2);
            for (const save of usernameSaves) expect(save).toBeEnabled();

            await fireEvent.click(usernameSaves[0]);

            await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(1));
            expect(profilePut()).toHaveBeenCalledWith({username: 'alice2'});
        });

        it('asks nothing of a username change alone: no field, and its Saves and save-all are on', async () => {
            await mountUnlocked();
            await type(username(), 'alice2');

            // The edit registered — its Saves are there — and still no password is asked for.
            const usernameSaves = fieldButtons('profile-username', 'save');
            expect(usernameSaves).toHaveLength(2);
            for (const save of usernameSaves) expect(save).toBeEnabled();
            expect(saveAllButton()).toBeEnabled();
            expect(emailPassword()).toBeNull();
            expect(hint()).toBeNull();
        });
    });

    describe('what an e-mail save sends', () => {
        // The e-mail row's request is pinned in «per-field save and undo» above, the request of both fields in «save all».
        it('save all sends the e-mail with the current password', async () => {
            await mountUnlocked();
            await type(email(), 'new@example.com');
            await typeEmailPassword(CURRENT_PASSWORD);

            await fireEvent.click(saveAllButton());

            await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(1));
            expect(profilePut()).toHaveBeenCalledWith({email: 'new@example.com', current_password: CURRENT_PASSWORD});
        });

        it("never puts the password in the username's request, even once it is typed", async () => {
            await mountUnlocked();
            await type(username(), 'alice2');
            await type(email(), 'new@example.com');
            await typeEmailPassword(CURRENT_PASSWORD);

            await fireEvent.click(fieldButtons('profile-username', 'save')[0]);

            await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(1));
            expect(profilePut()).toHaveBeenCalledWith({username: 'alice2'});
        });
    });

    describe('after an e-mail save, accepted or refused', () => {
        it.each(EMAIL_SAVES)('empties the password once the e-mail is saved through $via: the field goes, and comes back empty', async ({save}) => {
            storeAddressOnCheckAuth('new@example.com');
            await mountUnlocked();
            await type(email(), 'new@example.com');
            await typeEmailPassword(CURRENT_PASSWORD);

            await fireEvent.click(save());

            await waitFor(() => expect(checkAuth).toHaveBeenCalled());
            // Saved: the address is the stored one, so the field is gone…
            await waitFor(() => expect(emailPassword()).toBeNull());
            expect(email()).toHaveValue('new@example.com');
            expect(error()).toBeNull();
            await waitFor(() => expect(email()).toBeEnabled());

            // …and the password did not outlive the save: the next change asks for it afresh.
            await type(email(), 'newer@example.com');

            await waitFor(() => expect(emailPassword()).not.toBeNull());
            expect(emailPassword()).toHaveValue('');
            expect(saveAllButton()).toBeDisabled();
        });

        const PASSWORD_REFUSAL_CASES = PASSWORD_REFUSALS.flatMap((refusal) => EMAIL_SAVES.map(({via, save}) => ({...refusal, via, save})));

        it.each(PASSWORD_REFUSAL_CASES)('$code through $via: the banner carries the code, the new e-mail stays for a retry, the password is emptied', async ({code, message, save}) => {
            profilePut().mockRejectedValue(axiosError({error_code: code, message}));
            await mountUnlocked();
            await type(email(), 'new@example.com');
            await typeEmailPassword('not-the-password');

            await fireEvent.click(save());

            await waitFor(() => expect(error()).not.toBeNull());
            expect(error()).toHaveAttribute('data-error-code', code);
            // Worded by the tab from the code: neither the object itself nor the server's English sentence.
            expect(error()).not.toHaveTextContent('[object Object]');
            expect(error()).not.toHaveTextContent(message);
            // Only the password has to be typed again: the address stays, and the field with it, emptied.
            expect(email()).toHaveValue('new@example.com');
            expect(emailPassword()).not.toBeNull();
            expect(emailPassword()).toHaveValue('');
            for (const button of emailSaves()) expect(button).toBeDisabled();
            expect(saveAllButton()).toBeDisabled();
        });

        it('after a refused password, the retry sends the same e-mail with the password typed again', async () => {
            profilePut()
                .mockRejectedValueOnce(axiosError({error_code: 'CURRENT_PASSWORD_INVALID', message: 'Current password is incorrect'}))
                .mockResolvedValueOnce({} as never);
            await mountUnlocked();
            await type(email(), 'new@example.com');
            await typeEmailPassword('not-the-password');
            await fireEvent.click(fieldButtons('profile-email', 'save')[0]);
            await waitFor(() => expect(error()).toHaveAttribute('data-error-code', 'CURRENT_PASSWORD_INVALID'));
            await waitFor(() => expect(email()).toBeEnabled());

            await typeEmailPassword(CURRENT_PASSWORD);
            await fireEvent.click(fieldButtons('profile-email', 'save')[0]);

            await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(2));
            expect(profilePut().mock.calls.map((c) => c[0])).toEqual([
                {email: 'new@example.com', current_password: 'not-the-password'},
                {email: 'new@example.com', current_password: CURRENT_PASSWORD},
            ]);
        });

        it.each(EMAIL_SAVES)("a refusal without a code, through $via, is today's: the server's sentence, no code, the e-mail put back and the field gone", async ({save}) => {
            profilePut().mockRejectedValue(axiosError('Email already registered'));
            await mountUnlocked();
            await type(email(), 'taken@example.com');
            await typeEmailPassword(CURRENT_PASSWORD);

            await fireEvent.click(save());

            await waitFor(() => expect(error()).not.toBeNull());
            expect(error()).toHaveTextContent('Email already registered');
            expect(error()!.getAttribute('data-error-code') ?? '', 'a sentence without a code publishes no code').toBe('');
            await waitFor(() => expect(email()).toHaveValue('alice@example.com'));
            // Back at the stored address: no password is asked for any more.
            expect(emailPassword()).toBeNull();
            expect(hint()).toBeNull();
        });

        it.each(EMAIL_SAVES)('a code the tab does not know, through $via: a generic text, never «[object Object]», and no code published', async ({save}) => {
            profilePut().mockRejectedValue(axiosError({error_code: 'SOMETHING_NEW', message: 'Something the tab has never heard of'}));
            await mountUnlocked();
            await type(email(), 'new@example.com');
            await typeEmailPassword(CURRENT_PASSWORD);

            await fireEvent.click(save());

            await waitFor(() => expect(error()).not.toBeNull());
            expect(error()).not.toHaveTextContent('[object Object]');
            expect(error()).toHaveTextContent(/\S/);
            // Only a code the tab can word is published (see this block's comment): an unknown one reads as a generic failure.
            expect(error()!.getAttribute('data-error-code') ?? '', 'an unknown code publishes no code').toBe('');
        });
    });
});

// =========================================================================
/**
 * Lot A-25 (release 1.3, workstream A) — a change of capitals only is no change of address (decision P18).
 *
 * Why. P18, now in the backend: an address is the same whatever the case of its letters A–Z, and of those only —
 * letters outside A–Z compare as written, so `émile@` and `Émile@` are two addresses. One's own address written in
 * other A–Z capitals is therefore no change of address: `PUT /auth/profile` takes it without `current_password`, ends
 * no session and keeps the verification; the new form is stored (its local part as typed: `EmailStr` lowers the
 * domain). The tab still compares exactly (`editedEmail !== originalEmail`): for such a change it shows the
 * current-password field and its hint, which announces a sign-out that never comes, and keeps every Save off until a
 * password the server will not read is typed.
 *
 * The contract (plan-phase01Accounts, «A-25 — contratto»), the tab's half:
 *   - C2: a change of capitals only is still a change, saved as typed: the row offers Save and Undo, and save all is
 *     there;
 *   - C3: the field `profile-email-password` and its hint `profile-email-password-hint` only while the address really
 *     changes, and only then does every Save wait for the password; a password typed for a real change is dropped once
 *     the edit is back to capitals only;
 *   - C4: capitals only → the request is exactly `{email}`, with no `current_password` key — not even an empty one,
 *     which the server's schema (`min_length=1`) refuses with a 422 — from the row and from save all; a real change →
 *     `{email, current_password}`, as before;
 *   - C5: the ASCII limit: a letter outside A–Z in another case makes another address, and the password is asked.
 * The rule itself (C1) is `$lib/features/auth/emailCase`, pinned by `emailCase.test.ts`. This block does not import it:
 * it reads the tab through its DOM and its requests — and the import of a module that does not exist yet would turn
 * this whole file red, not only these cases.
 *
 * Red until A-25: the cases of capitals only (C2–C4). Guard, green today and to stay so: the ASCII limit (C5). The
 * guard «a real change still asks for the password, every Save off until it is typed» is already the A6e block's
 * («the field › appears once the edit is another address…», «no e-mail save without it › keeps both e-mail Saves
 * and save-all off while it is empty…») and is not repeated here.
 *
 * The stored addresses keep their domain in small letters, as `EmailStr` leaves it. Not asserted: the amber tint of a
 * modified row (a CSS class: the Save appearing is its observable half), and the words of the hint.
 */
describe('ProfileTab — a change of capitals only (P18)', () => {
    const passwordHint = () => screen.queryByTestId('profile-email-password-hint');
    const saveAllButton = () => screen.getByTestId('profile-save-all');

    /** The e-mail row's Saves, checked as a pair (mobile, desktop), so that «every one is on» never passes on an empty list. */
    function emailSaves(): HTMLElement[] {
        const saves = fieldButtons('profile-email', 'save');
        expect(saves, "the e-mail row's Save, in its mobile and its desktop variant").toHaveLength(2);
        return saves;
    }

    /** The e-mail row's Undos, the same pair. */
    function emailUndos(): HTMLElement[] {
        const undos = fieldButtons('profile-email', 'undo');
        expect(undos, "the e-mail row's Undo, in its mobile and its desktop variant").toHaveLength(2);
        return undos;
    }

    /** The two controls that save an e-mail change alone: the row's Save (its first variant, see `fieldButtons`) and save all. */
    const EMAIL_SAVES = [
        {via: "the e-mail row's Save", save: () => emailSaves()[0]},
        {via: 'save all', save: () => saveAllButton()},
    ];

    /** The body of the profile request number `index`, as the tab handed it to the client. */
    const sentBody = (index: number) => profilePut().mock.calls[index][0] as Record<string, unknown>;

    /** Mount, unlocked, for an account whose stored address is `address`. */
    async function mountUnlockedAt(address: string) {
        user.set({username: 'alice', email: address, created_at: '2024-03-05T10:00:00Z'});
        return mountUnlocked();
    }

    /** One's own address, and the same address in other A–Z capitals (P18). */
    const CAPITALS_ONLY = [
        {why: 'capitals added, in the local part and in the domain', stored: 'alice@example.com', typed: 'Alice@Example.COM'},
        {why: 'the capital of the stored form taken away', stored: 'Alice@example.com', typed: 'alice@example.com'},
        {why: 'A–Z capitals around an é, which stays as written', stored: 'émile@example.com', typed: 'éMILE@EXAMPLE.COM'},
    ];

    /** One's own address with a letter outside A–Z in another case: another address (C5), whatever its A–Z do. */
    const OUTSIDE_A_Z = [
        {why: 'É for é', stored: 'émile@example.com', typed: 'Émile@example.com'},
        {why: 'é for É', stored: 'Émile@example.com', typed: 'émile@example.com'},
        {why: 'every A–Z folds back, the É does not', stored: 'émile@example.com', typed: 'ÉMILE@EXAMPLE.COM'},
    ];

    describe('the field and the Saves (C2, C3)', () => {
        // red until A-25
        it.each(CAPITALS_ONLY)('$why ($stored → $typed): a change all the same — Save, Undo and save all, every one on — with no password field and no hint', async ({stored, typed}) => {
            await mountUnlockedAt(stored);

            await type(email(), typed);

            // C2: still a change, to be saved as typed — the row offers its pair and save all is there: the edit registered.
            const saves = emailSaves();
            for (const undo of emailUndos()) expect(undo).toBeEnabled();
            expect(saveAllButton()).toBeInTheDocument();
            // C3: …but not a change of address: nothing to confirm, nobody to sign out.
            expect(emailPassword(), 'a change of capitals only asks for no password').toBeNull();
            expect(passwordHint(), 'and announces no sign-out').toBeNull();
            for (const save of saves) expect(save).toBeEnabled();
            expect(saveAllButton()).toBeEnabled();
        });
    });

    describe('what is sent (C4)', () => {
        // red until A-25
        it.each(EMAIL_SAVES)('through $via: exactly {email} as typed — no current_password key, not even an empty one', async ({save}) => {
            await mountUnlocked();
            await type(email(), 'Alice@Example.COM');
            expect(save(), 'nothing to type first: the Save is on').toBeEnabled();

            await fireEvent.click(save());

            await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(1));
            const body = sentBody(0);
            expect(body).toStrictEqual({email: 'Alice@Example.COM'});
            expect('current_password' in body, 'a change of capitals only carries no current_password key').toBe(false);
        });
    });

    describe('from a real change back to capitals only (C3, C4)', () => {
        // red until A-25
        it('the field goes with its hint, and the password typed for the real change with it: the next real change asks afresh', async () => {
            await mountUnlocked();
            await type(email(), 'Alice@Example.org');
            // The way in, as today: another domain is another address, whatever its capitals — the password is asked.
            expect(emailPassword(), 'a real change, even in other capitals, asks for the password').not.toBeNull();
            await typeEmailPassword(CURRENT_PASSWORD);
            expect(emailPassword()).toHaveValue(CURRENT_PASSWORD);

            await type(email(), 'Alice@Example.com');

            await waitFor(() => expect(emailPassword(), 'back to capitals only: the field goes').toBeNull());
            expect(passwordHint()).toBeNull();
            // Still a change: its Saves are there, and on.
            for (const save of emailSaves()) expect(save).toBeEnabled();

            await type(email(), 'Alice@Example.net');

            await waitFor(() => expect(emailPassword()).not.toBeNull());
            // What was typed for the first real change did not stay behind the scenes.
            expect(emailPassword()).toHaveValue('');
            for (const save of emailSaves()) expect(save).toBeDisabled();
        });

        // red until A-25
        it.each(EMAIL_SAVES)('through $via, the request is {email} alone — never the password typed for the real change', async ({save}) => {
            await mountUnlocked();
            await type(email(), 'Alice@Example.org');
            await typeEmailPassword(CURRENT_PASSWORD);
            await type(email(), 'Alice@Example.com');
            expect(save()).toBeEnabled();

            await fireEvent.click(save());

            await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(1));
            const body = sentBody(0);
            expect(body).toStrictEqual({email: 'Alice@Example.com'});
            expect('current_password' in body, 'the password typed for another change does not ride along').toBe(false);
        });
    });

    describe('the ASCII limit (C5)', () => {
        // guard
        it.each(OUTSIDE_A_Z)('$why ($stored → $typed) is another address: the field and its hint, every Save off until the password is typed, and the request carries it', async ({stored, typed}) => {
            expect(
                [stored, typed].map((address) => address.normalize('NFC')),
                'premise: written precomposed, as a keyboard types it',
            ).toEqual([stored, typed]);
            await mountUnlockedAt(stored);

            await type(email(), typed);

            expect(emailPassword(), 'a letter outside A–Z compares as written: the password is asked').not.toBeNull();
            expect(passwordHint()).not.toBeNull();
            for (const save of emailSaves()) expect(save).toBeDisabled();
            expect(saveAllButton()).toBeDisabled();

            await typeEmailPassword(CURRENT_PASSWORD);

            await waitFor(() => expect(saveAllButton()).toBeEnabled());
            for (const save of emailSaves()) expect(save).toBeEnabled();

            await fireEvent.click(emailSaves()[0]);

            await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(1));
            expect(sentBody(0)).toStrictEqual({email: typed, current_password: CURRENT_PASSWORD});
        });
    });
});

// =========================================================================
/**
 * Lot A8b (release 1.3, workstream A, contract C11) — the server's limit on failed passwords, met by an e-mail change.
 *
 * Why. Since A8a, `PUT /auth/profile` checks the `current_password` of a change of address under the sign-in's limit
 * (F15): past 10 wrong passwords in 15 minutes for the account, or 50 from the address, it refuses with a 429
 * `{detail: {error_code: "TOO_MANY_ATTEMPTS", message}}` and a `Retry-After`, before it reads the password — the right
 * one included. `describeRefusal` knows two codes, so this one reads as a failed update (`settings.updateFailed`) with
 * no code published, and the tab puts the old address back: the user loses what they typed and is not told to wait.
 *
 * The contract, the tab's half: that 429 → `describeRefusal` yields
 * `{code: 'TOO_MANY_ATTEMPTS', text: $_('settings.tooManyPasswordAttempts')}`, shown the way the A6e block shows
 * `CURRENT_PASSWORD_INVALID` — the code on `profile-error` as `data-error-code`, the words inside it — and the new
 * address and the typed password stay as they were. Unlike a wrong password, which the A6e block sees emptied: this one
 * was never read.
 *
 * Red until A8b: the limit's refusal, through the row's Save and through save all. Guard, green today and to stay so:
 * a 429 that is not the limit's — another code, a sentence, a proxy's page — is today's refusal: its words, no code,
 * the address put back, never the new key.
 *
 * Not pinned: whether the tab reads the status beside the code (`describeRefusal` keys its refusals on the code alone);
 * the `Retry-After`, in the fixture because the server sends it; the Saves after the refusal; the five seconds the
 * banner lives, as for every refusal.
 */
describe("ProfileTab — the server's limit on failed passwords, met by an e-mail change (A8b, C11)", () => {
    /** The key the contract adds for the limit's refusal. */
    const LIMIT_KEY = 'settings.tooManyPasswordAttempts';
    /** The server's own sentence for it (`_refuse_too_many_failures`, `backend/app/api/v1/auth.py`): never on screen. */
    const LIMIT_MESSAGE = 'Too many failed attempts: try again later';

    /** A rejection as axios raises it once the server has answered: its status, its headers, its body. */
    function answered(status: number, body: unknown, headers: Record<string, string> = {}): Error {
        return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, response: {status, headers, data: body}});
    }

    /** The limit's refusal, as A8a sends it. */
    const limitRefusal = () => answered(429, {detail: {error_code: 'TOO_MANY_ATTEMPTS', message: LIMIT_MESSAGE}}, {'retry-after': '900'});

    /** The two controls that save an e-mail change alone: the row's Save (its first variant, see `fieldButtons`) and save all. */
    const EMAIL_SAVES = [
        {via: "the e-mail row's Save", save: () => fieldButtons('profile-email', 'save')[0]},
        {via: 'save all', save: () => screen.getByTestId('profile-save-all')},
    ];

    /** A change of address with its password, saved through `save` against `failure`: waits for the refusal on screen and the save over. */
    async function emailChangeRefused(failure: Error, save: () => HTMLElement): Promise<void> {
        profilePut().mockRejectedValue(failure);
        await mountUnlocked();
        await type(email(), 'new@example.com');
        await typeEmailPassword(CURRENT_PASSWORD);

        await fireEvent.click(save());

        await waitFor(() => {
            expect(error()).not.toBeNull();
            expect(screen.getByTestId('profile-tab')).toHaveAttribute('data-busy', 'false');
        });
        // The request that met the refusal: the change of address, with its password.
        expect(profilePut()).toHaveBeenCalledTimes(1);
        expect(profilePut()).toHaveBeenCalledWith({email: 'new@example.com', current_password: CURRENT_PASSWORD});
    }

    // red until A8b (C11)
    it.each(EMAIL_SAVES)('TOO_MANY_ATTEMPTS through $via: the key and its code on the banner, the new e-mail and the typed password as they were', async ({save}) => {
        await emailChangeRefused(limitRefusal(), save);

        expect(error()).toHaveAttribute('data-error-code', 'TOO_MANY_ATTEMPTS');
        expect(error()).toHaveTextContent(LIMIT_KEY);
        expect(error(), "nothing of the server's English").not.toHaveTextContent(LIMIT_MESSAGE);
        // Nothing to type again: the address stays, and the field with the password in it.
        expect(email()).toHaveValue('new@example.com');
        expect(emailPassword(), 'the current-password field stays').not.toBeNull();
        expect(emailPassword()).toHaveValue(CURRENT_PASSWORD);
    });

    /** 429s that are not the limit's, with the words today's refusal shows for each. */
    const NOT_THE_LIMIT = [
        {what: 'a 429 with another code', failure: () => answered(429, {detail: {error_code: 'RATE_LIMITED', message: 'Slow down: rate limited'}}), words: 'settings.updateFailed'},
        {what: 'a 429 whose detail is a sentence', failure: () => answered(429, {detail: 'Too many requests'}), words: 'Too many requests'},
        {what: 'a 429 from a proxy, its own page for a body', failure: () => answered(429, '<html><body><h1>429 Too Many Requests</h1></body></html>'), words: 'Request failed with status code 429'},
    ];

    // guard
    it.each(NOT_THE_LIMIT.flatMap((refusal) => EMAIL_SAVES.map((via) => ({...refusal, ...via}))))("$what, through $via, is today's refusal: its words, no code, the e-mail put back — never the new key", async ({failure, words, save}) => {
        await emailChangeRefused(failure(), save);

        expect(error()).toHaveTextContent(words);
        expect(error()).not.toHaveTextContent(LIMIT_KEY);
        expect(error()!.getAttribute('data-error-code') ?? '', 'no code published').toBe('');
        expect(email()).toHaveValue('alice@example.com');
        expect(emailPassword()).toBeNull();
    });
});
