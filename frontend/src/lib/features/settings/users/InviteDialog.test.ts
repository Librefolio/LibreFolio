// @vitest-environment jsdom
/**
 * InviteDialog — component test (Vitest + jsdom). Accounts lot A6b, workstream A (plan A6b.1, «Invite dialog»).
 *
 * How an administrator invites someone: a small form — an optional e-mail, kept for reference and not enforced, and
 * whether the account will be an administrator — then the link the server returned, shown once through `LinkShare`.
 *
 * Why a component test. The two refusals that matter here — registration closed, no place left — are server states a
 * shared E2E lane cannot set on cue without rewriting `registration_mode`, or filling the instance, under every other
 * spec; here each is one `mockRejectedValue`. `e2e/settings/admin-users.spec.ts` walks the happy path for real.
 *
 * The contract (A6b.1):
 *   - props `{open, onClose, onCreated?}`; root `users-invite-dialog` (ModalBase, trapFocus);
 *   - the form: `users-invite-email` (optional), `users-invite-admin` (checkbox or switch → `grants_admin`),
 *     `users-invite-create`, `users-invite-cancel`;
 *   - create → `zodiosApi.create_invite_api_v1_users_invites_post({grants_admin, email?})`, no `email` key when the
 *     field is empty;
 *   - a 409 REGISTRATION_DISABLED or USER_LIMIT_REACHED (`response.data.detail.error_code`) is shown inline in
 *     `users-invite-error` with `data-error-code`, and the dialog stays on its form;
 *   - success → the link step: `LinkShare` (`purpose="invite"`, `path`/`url` from the response, `expiresAt` =
 *     `invite.expires_at`) and `accounts.invite.created` `{invite_id}`, without a toast; `users-invite-done` closes
 *     (`onClose`) and the tab reloads (`onCreated(response)`).
 *
 * Held still: the API (the `$lib/api` Proxy mock, each alias a lazily created `vi.fn`), `notify`, and `$lib/i18n` (an
 * identity translator: nothing here reads a label). `LinkShare` is the real one — what the dialog hands it is observed
 * as LinkShare draws it — and it asks nothing by itself while its address is untouched, so no `fetch` is stubbed.
 *
 * Not asserted: the expiry handed to LinkShare (`link-share-expires` publishes no machine-readable value); the wording
 * of an error; what a refusal other than these two shows; the order `onClose` and `onCreated` are called in, and
 * whether `onCreated` comes at creation or at «done» — only that both have come once «done» is pressed.
 *
 * Red today: `./InviteDialog.svelte` does not exist (nor do `./LinkShare.svelte` and `./accountErrors.ts`), so the
 * import fails and every case is red on that.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

// --- Mocks --------------------------------------------------------------

// The identity translator: a label renders as its own key, in no language at all.
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
        SUPPORTED_LOCALES: ['en', 'it', 'fr', 'es'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano', fr: 'Français', es: 'Español'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT', fr: 'FR', es: 'ES'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

// The language dates are written in (`formatDateTime` → `uiLocale` → `currentLanguage`), held at English.
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));

vi.mock('$lib/api', () => {
    const cache = new Map<string, unknown>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, prop: string) {
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

import InviteDialog from './InviteDialog.svelte';
import {zodiosApi} from '$lib/api';

// --- Fixtures -----------------------------------------------------------

/** The path the server returns: the page that takes the token, the token in the fragment (`token_service.token_path`). */
const TOKEN = 'aW52aXRlLWNyZWF0ZWQtdG9rZW4';
const INVITE_PATH = `/invite#token=${TOKEN}`;
/** `LIBREFOLIO_PUBLIC_URL` followed by the path, behind a reverse proxy's sub-path. */
const PUBLIC_URL = `https://lf.example/librefolio${INVITE_PATH}`;
const EMAIL = 'x@example.com';

const INVITE = {id: 31, grants_admin: false, email: null, created_at: '2026-10-15T15:00:00Z', expires_at: '2026-10-22T15:00:00Z', created_by_user_id: 1};

/** A `POST /users/invites` answer (`InviteCreateResponse`). */
function created(url: string | null = PUBLIC_URL) {
    return {invite: {...INVITE}, token: TOKEN, path: INVITE_PATH, url};
}

/** The create endpoint, as the Proxy mock hands it out. */
const createInvite = () => vi.mocked(zodiosApi.create_invite_api_v1_users_invites_post as never) as ReturnType<typeof vi.fn>;

/** A structured refusal, axios-shaped: `{detail: {error_code, message, …}}` with its status. */
function refusal(status: number, detail: Record<string, unknown>): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, name: 'AxiosError', response: {status, data: {detail}}});
}

/**
 * The body as it reaches the server: what JSON sends. A key holding `undefined` is not sent; a `null`, or an empty
 * string, is — and would tell the server "an e-mail, empty" instead of "no e-mail".
 */
function sentBody(): unknown {
    expect(createInvite()).toHaveBeenCalledTimes(1);
    const [body] = createInvite().mock.calls[0];
    return JSON.parse(JSON.stringify(body ?? null));
}

// --- Helpers ------------------------------------------------------------

interface Notified {
    name: string;
    detail?: Record<string, unknown>;
    toast?: {variant: string; message: string; duration?: number};
}

/** Every notification of `name`, in order. */
function notified(name: string): Notified[] {
    return notify.mock.calls.map(([options]) => options as Notified).filter((options) => options.name === name);
}

function mount(props: {open?: boolean} = {}) {
    const onClose = vi.fn();
    const onCreated = vi.fn();
    const utils = render(InviteDialog, {props: {open: true, onClose, onCreated, ...props}});
    return {...utils, onClose, onCreated};
}

const dialog = () => screen.getByTestId('users-invite-dialog');
const inDialog = (testId: string) => within(dialog()).getByTestId(testId);
const emailField = () => inDialog('users-invite-email') as HTMLInputElement;

async function typeEmail(value: string): Promise<void> {
    await fireEvent.input(emailField(), {target: {value}});
}

async function pressCreate(): Promise<void> {
    await fireEvent.click(inDialog('users-invite-create'));
}

// --- Lifecycle ----------------------------------------------------------

beforeAll(async () => {
    // Only a component importing svelte-i18n directly would need it: `$lib/i18n` is mocked above.
    await setupI18n();
});

beforeEach(() => {
    vi.clearAllMocks();
    createInvite().mockReset();
    createInvite().mockResolvedValue(created());
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

// --- The form -------------------------------------------------------------

describe('InviteDialog — the form', () => {
    it('INV-C-01: renders nothing while closed, and opens on its form without asking the server anything', async () => {
        const {rerender} = mount({open: false});
        expect(screen.queryByTestId('users-invite-dialog')).toBeNull();

        await rerender({open: true});

        expect(dialog()).toBeVisible();
        for (const testId of ['users-invite-email', 'users-invite-admin', 'users-invite-create', 'users-invite-cancel']) {
            expect(inDialog(testId)).toBeInTheDocument();
        }
        expect(emailField().value).toBe('');
        expect(within(dialog()).queryByTestId('users-invite-error')).toBeNull();
        expect(within(dialog()).queryByTestId('link-share')).toBeNull();
        expect(createInvite()).not.toHaveBeenCalled();
    });

    it('INV-C-02: with nothing filled in, create sends {grants_admin: false} — and no email key at all', async () => {
        mount();

        await pressCreate();

        await waitFor(() => expect(createInvite()).toHaveBeenCalled());
        expect(sentBody()).toEqual({grants_admin: false});
    });

    it('INV-C-03: with an e-mail and the administrator control turned on, create sends {grants_admin: true, email}', async () => {
        mount();

        await typeEmail(EMAIL);
        await fireEvent.click(inDialog('users-invite-admin'));
        await pressCreate();

        await waitFor(() => expect(createInvite()).toHaveBeenCalled());
        expect(sentBody()).toEqual({grants_admin: true, email: EMAIL});
    });

    it.each([
        {code: 'REGISTRATION_DISABLED', detail: {error_code: 'REGISTRATION_DISABLED', message: 'Registration is disabled: invitations cannot be created'}},
        {code: 'USER_LIMIT_REACHED', detail: {error_code: 'USER_LIMIT_REACHED', message: 'The instance has reached its maximum number of users', limit: 5, used: 5, billing_url: 'https://billing.example/manage'}},
    ])('INV-C-04: a 409 $code is shown in users-invite-error with its code, and the dialog stays on its form, as filled in', async ({code, detail}) => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        createInvite().mockRejectedValue(refusal(409, detail));
        const {onClose, onCreated} = mount();
        expect(within(dialog()).queryByTestId('users-invite-error')).toBeNull();

        await typeEmail(EMAIL);
        await pressCreate();

        await waitFor(() => expect(inDialog('users-invite-error')).toHaveAttribute('data-error-code', code));
        expect(inDialog('users-invite-create')).toBeInTheDocument();
        expect(emailField().value).toBe(EMAIL);
        expect(within(dialog()).queryByTestId('link-share')).toBeNull();
        expect(notified('accounts.invite.created')).toEqual([]);
        expect(onClose).not.toHaveBeenCalled();
        expect(onCreated).not.toHaveBeenCalled();
    });

    it('INV-C-05: cancel closes without asking the server anything, whatever was filled in', async () => {
        const {onClose, onCreated} = mount();
        await typeEmail(EMAIL);
        await fireEvent.click(inDialog('users-invite-admin'));

        await fireEvent.click(inDialog('users-invite-cancel'));

        expect(onClose).toHaveBeenCalledTimes(1);
        expect(createInvite()).not.toHaveBeenCalled();
        expect(onCreated).not.toHaveBeenCalled();
    });
});

// --- The link step ----------------------------------------------------------

describe('InviteDialog — the link step', () => {
    it.each([
        {source: 'the public url the server returned', url: PUBLIC_URL as string | null, expected: () => PUBLIC_URL},
        {source: "this page's origin, the server knowing no public address", url: null, expected: () => `${window.location.origin}${INVITE_PATH}`},
    ])('INV-C-06: once created, LinkShare (purpose invite) shows the link built from $source — and create is no longer offered', async ({url, expected}) => {
        createInvite().mockResolvedValue(created(url));
        const {onClose} = mount();

        await pressCreate();

        const share = await waitFor(() => within(dialog()).getByTestId('link-share'));
        expect(share).toBeVisible();
        expect(share).toHaveAttribute('data-purpose', 'invite');
        expect((within(share).getByTestId('link-share-link') as HTMLInputElement).value).toBe(expected());
        // The link is shown once, and a second invitation would take a second place.
        expect(within(dialog()).queryByTestId('users-invite-create')).toBeNull();
        // The dialog does not close by itself: the administrator has not copied the link yet.
        expect(onClose).not.toHaveBeenCalled();
    });

    it('INV-C-07: a created invitation is notified as accounts.invite.created with its invite_id, without a toast', async () => {
        mount();

        await pressCreate();

        await waitFor(() => expect(notified('accounts.invite.created')).toHaveLength(1));
        const [event] = notified('accounts.invite.created');
        expect(event.detail).toEqual(expect.objectContaining({invite_id: INVITE.id}));
        // The link on screen is the outcome: no toast is owed.
        expect(event.toast).toBeUndefined();
    });

    it('INV-C-08: done closes the dialog and hands the response to onCreated, for the tab to reload', async () => {
        const response = created();
        createInvite().mockResolvedValue(response);
        const {onClose, onCreated} = mount();
        await pressCreate();

        await fireEvent.click(await waitFor(() => inDialog('users-invite-done')));

        expect(onClose).toHaveBeenCalledTimes(1);
        expect(onCreated).toHaveBeenCalledTimes(1);
        expect(onCreated).toHaveBeenCalledWith(response);
    });
});
