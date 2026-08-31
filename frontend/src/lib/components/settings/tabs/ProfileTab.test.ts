// @vitest-environment jsdom
/**
 * ProfileTab — component test (Vitest + jsdom).
 *
 * The account panel: username, e-mail, avatar, and the two irreversible actions
 * (change password, delete account). It takes no props; everything that decides
 * its behaviour comes from the `currentUser` store, one GET for the avatar, and
 * the three writes it issues — all controllable from here.
 *
 * Why a component test and not an E2E. `front-utility settings` already walks the
 * happy path. What it cannot reach is the half of this component that only exists
 * when the server refuses: `saveField` **puts the old value back in the input**
 * on failure, `saveAll` reports a partial list, the avatar save reverts, and
 * `handleDeleteAccount` has to survive a rejection without logging the user out.
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
 *   - the amber "modified" tint on a row. That is a CSS class, and the observable
 *     half of the same state — the Save button appearing — is asserted instead.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import {fireEvent, render, screen, waitFor, within} from '$test/component';

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

import ProfileTab from './ProfileTab.svelte';
import {zodiosApi} from '$lib/api';

// --- Helpers ------------------------------------------------------------

const settingsGet = () => vi.mocked(zodiosApi.get_user_settings_endpoint_api_v1_settings_user_get as never) as ReturnType<typeof vi.fn>;
const settingsPut = () => vi.mocked(zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put as never) as ReturnType<typeof vi.fn>;
const profilePut = () => vi.mocked(zodiosApi.update_profile_api_v1_auth_profile_put as never) as ReturnType<typeof vi.fn>;
const deleteMe = () => vi.mocked(zodiosApi.delete_own_account_api_v1_auth_users_me_delete as never) as ReturnType<typeof vi.fn>;

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
    settingsGet().mockResolvedValue({avatar_url: null} as never);
    settingsPut().mockResolvedValue({} as never);
    profilePut().mockResolvedValue({} as never);
    deleteMe().mockResolvedValue({} as never);
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

    it('sends the e-mail alone from the e-mail row', async () => {
        await mountUnlocked();
        await type(email(), 'new@example.com');

        await fireEvent.click(fieldButtons('profile-email', 'save')[0]);

        await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(1));
        expect(profilePut()).toHaveBeenCalledWith({email: 'new@example.com'});
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

        await fireEvent.click(saveAll()!);

        await waitFor(() => expect(profilePut()).toHaveBeenCalledTimes(2));
        expect(profilePut().mock.calls.map((c) => c[0])).toEqual([{username: 'alice2'}, {email: 'new@example.com'}]);
        const event = notify.mock.calls[0][0];
        expect(event.name).toBe('settings.profile.saved');
        expect(event.detail).toEqual({fields: 2});
    });

    it('stops at the first rejection and leaves the second field unsaved', async () => {
        profilePut().mockRejectedValue(axiosError('Username already taken'));
        await mountUnlocked();
        await type(username(), 'alice2');
        await type(email(), 'new@example.com');

        await fireEvent.click(saveAll()!);

        await waitFor(() => expect(error()).not.toBeNull());
        expect(profilePut()).toHaveBeenCalledTimes(1);
        expect(notify).not.toHaveBeenCalled();
        // Unlike the per-field path, saveAll does NOT revert: both edits are still
        // on screen, which is what lets the user fix the username and retry.
        expect(username()).toHaveValue('alice2');
        expect(email()).toHaveValue('new@example.com');
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
describe('ProfileTab — deleting the account', () => {
    const openDelete = async () => {
        await fireEvent.click(screen.getByTestId('delete-account-button'));
        return screen.getByRole('dialog');
    };
    const confirmInput = () => document.getElementById('delete-confirm-input') as HTMLInputElement;
    const confirmButton = (dialog: HTMLElement) => within(dialog).getByRole('button', {name: 'settings.deleteAccountPermanently'});

    it('refuses until the username is typed exactly', async () => {
        await mount();
        const dialog = await openDelete();

        expect(confirmButton(dialog)).toBeDisabled();

        await type(confirmInput(), 'alic');
        expect(confirmButton(dialog)).toBeDisabled();

        await type(confirmInput(), 'Alice');
        expect(confirmButton(dialog)).toBeDisabled();

        await type(confirmInput(), 'alice');
        await waitFor(() => expect(confirmButton(dialog)).toBeEnabled());
    });

    it('deletes, logs out and leaves the app once confirmed', async () => {
        await mount();
        const dialog = await openDelete();
        await type(confirmInput(), 'alice');

        await fireEvent.click(confirmButton(dialog));

        await waitFor(() => expect(deleteMe()).toHaveBeenCalledTimes(1));
        expect(logout).toHaveBeenCalledTimes(1);
        expect(goto).toHaveBeenCalledWith('/');
    });

    it('keeps the user logged in and explains itself when the deletion is refused', async () => {
        deleteMe().mockRejectedValue(axiosError('Cannot delete the last administrator'));
        await mount();
        const dialog = await openDelete();
        await type(confirmInput(), 'alice');

        await fireEvent.click(confirmButton(dialog));

        await waitFor(() => expect(error()).not.toBeNull());
        expect(error()!).toHaveTextContent('Cannot delete the last administrator');
        expect(logout).not.toHaveBeenCalled();
        expect(goto).not.toHaveBeenCalled();
        // `deleting` is cleared, so the button is usable again for a retry.
        await waitFor(() => expect(confirmButton(dialog)).toBeEnabled());
    });

    it('falls back to a translated failure when the rejection carries nothing usable', async () => {
        deleteMe().mockRejectedValue('opaque');
        await mount();
        const dialog = await openDelete();
        await type(confirmInput(), 'alice');

        await fireEvent.click(confirmButton(dialog));

        await waitFor(() => expect(error()).not.toBeNull());
        expect(error()!).toHaveTextContent('settings.deleteAccountFailed');
    });

    it('forgets what was typed when the dialog is dismissed', async () => {
        await mount();
        const dialog = await openDelete();
        await type(confirmInput(), 'alice');

        await fireEvent.click(within(dialog).getByRole('button', {name: 'common.cancel'}));

        await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
        await openDelete();
        // A fresh, empty confirmation: the arming does not survive a cancel.
        expect(confirmInput()).toHaveValue('');
        expect(deleteMe()).not.toHaveBeenCalled();
    });

    it('closes on Escape as well as on Cancel', async () => {
        await mount();
        const dialog = await openDelete();

        await fireEvent.keyDown(dialog, {key: 'Escape'});

        await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    });

    it('says "deleting" instead of inviting a second click', async () => {
        const pending = deferred<never>();
        deleteMe().mockReturnValue(pending.promise as never);
        await mount();
        const dialog = await openDelete();
        await type(confirmInput(), 'alice');

        await fireEvent.click(confirmButton(dialog));

        await waitFor(() => expect(within(dialog).getByRole('button', {name: 'common.deleting'})).toBeDisabled());
        pending.resolve(undefined as never);
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
