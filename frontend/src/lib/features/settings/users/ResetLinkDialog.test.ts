// @vitest-environment jsdom
/**
 * ResetLinkDialog — component test (Vitest + jsdom). Accounts lot A6b, workstream A (plan A6b.1, «Reset dialog»).
 *
 * How an administrator gets a password-reset link for an account: a confirmation first — issuing a link makes every
 * link issued before for that account stop working — then the link, shown once through `LinkShare`.
 *
 * Why a component test. The failure path (the account deleted meanwhile, the network gone) cannot be provoked on cue in
 * a shared E2E lane; here it is one `mockRejectedValue`. `e2e/settings/admin-users.spec.ts` walks the happy path for
 * real, on a disposable account.
 *
 * The contract (A6b.1):
 *   - props `{open, account: {id, username}, onClose}`; root `users-reset-dialog`;
 *   - it opens on the confirmation; `users-reset-create` →
 *     `zodiosApi.create_password_reset_link_api_v1_users__user_id__password_reset_link_post` with
 *     `{params: {user_id}}` (the call convention of a body-less mutation: `(undefined, {params})`);
 *   - success → `LinkShare` (`purpose="password_reset"`) and `accounts.reset-link.created` `{user_id}`, with a toast;
 *     `users-reset-close` → `onClose`;
 *   - failure → `accounts.action.failed` `{action, code, user_id}` with an error toast; the code is the one
 *     `accountErrors.ts` maps: HTTP 404 → `NOT_FOUND`, anything it does not know → `null`.
 *
 * Held still: the API (the `$lib/api` Proxy mock, each alias a lazily created `vi.fn`), `notify`, and `$lib/i18n` (an
 * identity translator: nothing here reads a label). `LinkShare` is the real one — what the dialog hands it is observed
 * as LinkShare draws it — and it asks nothing by itself while its address is untouched, so no `fetch` is stubbed.
 *
 * Not asserted: the variant of the success toast (the contract says only that there is one), the value of
 * `detail.action` (only that it names an action), the wording of anything, whether a failure keeps the dialog open.
 *
 * Red today: `./ResetLinkDialog.svelte` does not exist (nor do `./LinkShare.svelte` and `./accountErrors.ts`), so the
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

import ResetLinkDialog from './ResetLinkDialog.svelte';
import {zodiosApi} from '$lib/api';

// --- Fixtures -----------------------------------------------------------

/** The account whose password is reset. */
const ACCOUNT = {id: 42, username: 'bob'};

/** The path the server returns: the page that takes the token, the token in the fragment (`token_service.token_path`). */
const TOKEN = 'cmVzZXQtbGluay10b2tlbg';
const RESET_PATH = `/reset-password#token=${TOKEN}`;
/** `LIBREFOLIO_PUBLIC_URL` followed by the path, behind a reverse proxy's sub-path. */
const PUBLIC_URL = `https://lf.example/librefolio${RESET_PATH}`;

/** A `POST /users/{id}/password-reset-link` answer (`LinkTokenResponse`). */
function issuedLink(url: string | null = PUBLIC_URL) {
    return {token: TOKEN, path: RESET_PATH, url, expires_at: '2026-10-16T15:00:00Z'};
}

/** The reset-link endpoint, as the Proxy mock hands it out. */
const createLink = () => vi.mocked(zodiosApi.create_password_reset_link_api_v1_users__user_id__password_reset_link_post as never) as ReturnType<typeof vi.fn>;

/** A refusal with a status, axios-shaped; the 404 of this endpoint carries a plain-string detail. */
function refusal(status: number, detail: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, name: 'AxiosError', response: {status, data: {detail}}});
}

/** A request that never got an answer: axios-shaped, without a `response`. */
function networkFailure(): Error {
    return Object.assign(new Error('Network Error'), {isAxiosError: true, name: 'AxiosError', code: 'ERR_NETWORK'});
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
    const utils = render(ResetLinkDialog, {props: {open: true, account: {...ACCOUNT}, onClose, ...props}});
    return {...utils, onClose};
}

const dialog = () => screen.getByTestId('users-reset-dialog');
const inDialog = (testId: string) => within(dialog()).getByTestId(testId);

async function confirmCreate(): Promise<void> {
    await fireEvent.click(inDialog('users-reset-create'));
}

// --- Lifecycle ----------------------------------------------------------

beforeAll(async () => {
    // Only a component importing svelte-i18n directly would need it: `$lib/i18n` is mocked above.
    await setupI18n();
});

beforeEach(() => {
    vi.clearAllMocks();
    createLink().mockReset();
    createLink().mockResolvedValue(issuedLink());
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

// --- The confirmation -------------------------------------------------------

describe('ResetLinkDialog — the confirmation', () => {
    it('RST-C-01: renders nothing while closed, and opens on the confirmation — no link is issued before it is confirmed', async () => {
        const {rerender} = mount({open: false});
        expect(screen.queryByTestId('users-reset-dialog')).toBeNull();

        await rerender({open: true});

        expect(dialog()).toBeVisible();
        expect(inDialog('users-reset-create')).toBeInTheDocument();
        expect(within(dialog()).queryByTestId('link-share')).toBeNull();
        // Issuing a link revokes the ones issued before: merely opening the dialog must not do it.
        expect(createLink()).not.toHaveBeenCalled();
    });

    it('RST-C-02: confirming asks for one link, for this account — params.user_id in the config, after the (absent) body', async () => {
        mount();

        await confirmCreate();

        await waitFor(() => expect(createLink()).toHaveBeenCalledTimes(1));
        const [, config] = createLink().mock.calls[0];
        expect(config).toEqual(expect.objectContaining({params: {user_id: ACCOUNT.id}}));
    });
});

// --- The link step ----------------------------------------------------------

describe('ResetLinkDialog — the link step', () => {
    it.each([
        {source: 'the public url the server returned', url: PUBLIC_URL as string | null, expected: () => PUBLIC_URL},
        {source: "this page's origin, the server knowing no public address", url: null, expected: () => `${window.location.origin}${RESET_PATH}`},
    ])('RST-C-03: once issued, LinkShare (purpose password_reset) shows the link built from $source — and the confirmation is gone', async ({url, expected}) => {
        createLink().mockResolvedValue(issuedLink(url));
        const {onClose} = mount();

        await confirmCreate();

        const share = await waitFor(() => within(dialog()).getByTestId('link-share'));
        expect(share).toBeVisible();
        expect(share).toHaveAttribute('data-purpose', 'password_reset');
        expect((within(share).getByTestId('link-share-link') as HTMLInputElement).value).toBe(expected());
        // A second link would revoke the one on screen.
        expect(within(dialog()).queryByTestId('users-reset-create')).toBeNull();
        // The dialog does not close by itself: the administrator has not copied the link yet.
        expect(onClose).not.toHaveBeenCalled();
    });

    it('RST-C-04: an issued link is notified as accounts.reset-link.created with the user_id, with a toast', async () => {
        mount();

        await confirmCreate();

        await waitFor(() => expect(notified('accounts.reset-link.created')).toHaveLength(1));
        const [event] = notified('accounts.reset-link.created');
        expect(event.detail).toEqual(expect.objectContaining({user_id: ACCOUNT.id}));
        expect(event.toast).toEqual(expect.objectContaining({variant: expect.any(String), message: expect.any(String)}));
    });

    it('RST-C-05: close, on the link step, closes the dialog', async () => {
        const {onClose} = mount();
        await confirmCreate();

        await fireEvent.click(await waitFor(() => inDialog('users-reset-close')));

        expect(onClose).toHaveBeenCalledTimes(1);
    });
});

// --- Failure ------------------------------------------------------------------

describe('ResetLinkDialog — when no link can be issued', () => {
    it.each([
        {why: 'the account is gone (404)', error: () => refusal(404, 'User not found'), code: 'NOT_FOUND' as string | null},
        {why: 'the request got no answer', error: () => networkFailure(), code: null},
    ])('RST-C-06: when $why, accounts.action.failed is notified with the action, the code ($code) and the user_id, with an error toast — and no link is shown', async ({error, code}) => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        createLink().mockRejectedValue(error());
        mount();

        await confirmCreate();

        await waitFor(() => expect(notified('accounts.action.failed')).toHaveLength(1));
        const [failed] = notified('accounts.action.failed');
        expect(failed.detail).toEqual(expect.objectContaining({action: expect.stringMatching(/\S/), code, user_id: ACCOUNT.id}));
        expect(failed.toast).toEqual(expect.objectContaining({variant: 'error', message: expect.any(String)}));
        expect(screen.queryByTestId('link-share')).toBeNull();
        expect(notified('accounts.reset-link.created')).toEqual([]);
    });
});
