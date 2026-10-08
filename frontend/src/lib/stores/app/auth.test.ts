import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {AxiosError, AxiosHeaders, isAxiosError, type InternalAxiosRequestConfig} from 'axios';

const loginApi = vi.hoisted(() => vi.fn());
const logoutApi = vi.hoisted(() => vi.fn());
const meApi = vi.hoisted(() => vi.fn());

vi.mock('$app/environment', () => ({browser: false}));
vi.mock('$app/navigation', () => ({goto: vi.fn()}));
vi.mock('$lib/api', () => ({
    zodiosApi: {
        login_api_v1_auth_login_post: loginApi,
        logout_api_v1_auth_logout_post: logoutApi,
        get_me_api_v1_auth_me_get: meApi,
    },
}));
vi.mock('$lib/debug', () => ({
    debug: {
        log: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
    },
}));
vi.mock('$lib/stores/app/language', () => ({
    currentLanguage: {set: vi.fn()},
}));
vi.mock('$lib/stores/app/settings', () => ({
    userSettings: {setDirect: vi.fn()},
}));
vi.mock('$lib/stores/app/donationPopupStore.svelte', () => ({
    donationPopup: {trigger: vi.fn()},
}));

import {auth, getAuthState} from './auth';
import * as authModule from './auth';
import {getClientSessionUserId} from './clientSession';

function user(id: number, username: string) {
    return {
        id,
        username,
        email: `${username}@example.com`,
        is_admin: false,
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
    };
}

/** The config axios attaches to every error it raises. */
const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** The server answered with this status: axios rejects with the response attached. */
function httpError(status: number): AxiosError {
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, REQUEST, {}, {status, statusText: '', headers: {}, config: REQUEST, data: {detail: 'stub'}});
}

/** A signed-in store with an open client session, reached through `login()`. */
async function signIn(id: number, username: string): Promise<void> {
    loginApi.mockResolvedValueOnce({user: user(id, username), user_settings: null, show_donation_popup: false});
    expect(await auth.login(username, 'password'), 'premise: the sign-in succeeds').toBe(true);
    expect(getAuthState().user?.id, 'premise: the store holds the signed-in user').toBe(id);
    expect(getClientSessionUserId(), 'premise: the sign-in opened a client session').toBe(String(id));
}

describe('auth operation ordering', () => {
    beforeEach(() => {
        auth.reset();
        loginApi.mockReset();
        logoutApi.mockReset();
        meApi.mockReset();
    });

    it('ignores a stale checkAuth response that resolves after login', async () => {
        let resolveCheck: (value: unknown) => void = () => undefined;
        meApi.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    resolveCheck = resolve;
                }),
        );
        loginApi.mockResolvedValueOnce({
            user: user(2, 'new-user'),
            user_settings: null,
            show_donation_popup: false,
        });

        const staleCheck = auth.checkAuth();
        expect(await auth.login('new-user', 'password')).toBe(true);

        resolveCheck({user: user(1, 'old-user')});
        expect(await staleCheck).toBe('superseded');
        expect(getAuthState().user?.id).toBe(2);
    });
});

/**
 * checkAuth — only a 401 signs the user out (K, step 19).
 *
 * `checkAuth()` used to answer a boolean, and every failure of `GET /auth/me` was a sign-out: the user
 * and the client session were cleared and the store marked initialized, so the `(app)` layout's reactive
 * redirect sent the user to the login. A server that was slow, down or answering 5xx therefore logged
 * the user out of the page they were on. The approved contract answers one of four outcomes:
 *   - `authenticated`   — a 200: the user is set and the store initialized, as before;
 *   - `unauthenticated` — **only** an HTTP 401: user `null`, store initialized, client session reset, as before;
 *   - `unreachable`     — anything else (5xx, no response, the axios timeout, a failure that is not an
 *     HTTP answer at all): user, client session and `isInitialized` stay exactly as they were, so a
 *     signed-in store keeps its user and a cold one stays uninitialized; only `isLoading` goes back to false;
 *   - `superseded`      — the answer arrived after a newer auth operation, which owns the state.
 *
 * Rejections are built as the errors axios raises (`AxiosError`, with a `response` only when the server
 * answered), so the store's `isAxiosError` sees what it sees in production. A signed-in store is reached
 * through `login()`, whose contract does not change, so the warm-up can never be what turns a case red.
 * In the `unreachable` cases the state is asserted before the outcome: there the state is what changes
 * for the user (today it is a sign-out), and the outcome is only how the layout learns about it. In the
 * other cases the state is today's, and the outcome is what changes.
 */
describe('checkAuth — only a 401 signs the user out', () => {
    /** Nothing came back: axios rejects without a response. */
    function networkError(): AxiosError {
        return new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {});
    }

    /** The client gave up waiting (the shared axios instance times out at 30 s): no response either. */
    function timeoutError(): AxiosError {
        return new AxiosError('timeout of 30000ms exceeded', AxiosError.ECONNABORTED, REQUEST, {});
    }

    /** Every failure of `GET /auth/me` that is not a 401, as [label, error]. */
    const NOT_A_401: [string, () => unknown][] = [
        ['a 500', () => httpError(500)],
        ['a 503', () => httpError(503)],
        ['a network error (no response)', networkError],
        ['an axios timeout (ECONNABORTED)', timeoutError],
        ['a failure that is not an HTTP answer', () => new Error('the response did not match the schema')],
    ];

    beforeEach(() => {
        auth.reset();
        loginApi.mockReset();
        logoutApi.mockReset();
        meApi.mockReset();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('premise: the fixtures are the errors axios raises — a response only when the server answered', () => {
        expect(isAxiosError(httpError(401))).toBe(true);
        expect(httpError(401).response?.status).toBe(401);
        expect(isAxiosError(networkError())).toBe(true);
        expect(networkError().response).toBeUndefined();
        expect(isAxiosError(timeoutError())).toBe(true);
        expect(timeoutError().code).toBe('ECONNABORTED');
        expect(timeoutError().response).toBeUndefined();
    });

    it('200 → authenticated: the user is set and the store initialized', async () => {
        meApi.mockResolvedValueOnce({user: user(1, 'alice')});

        const outcome = await auth.checkAuth();

        expect(outcome).toBe('authenticated');
        expect(getAuthState()).toMatchObject({isInitialized: true, isLoading: false});
        expect(getAuthState().user?.id).toBe(1);
        expect(getClientSessionUserId()).toBe('1');
    });

    it('a slow 200 is still authenticated: the store keeps no clock of its own (the 5 s panel is the layout’s)', async () => {
        vi.useFakeTimers();
        let answer: (value: unknown) => void = () => undefined;
        meApi.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    answer = resolve;
                }),
        );

        const check = auth.checkAuth();
        await vi.advanceTimersByTimeAsync(6_000);

        expect(getAuthState(), 'nothing is decided while the answer is on its way').toMatchObject({user: null, isLoading: true, isInitialized: false});

        answer({user: user(1, 'alice')});

        expect(await check).toBe('authenticated');
        expect(getAuthState()).toMatchObject({isInitialized: true, isLoading: false});
        expect(getAuthState().user?.id).toBe(1);
    });

    it('401 at app start → unauthenticated: the store is initialized without a user', async () => {
        meApi.mockRejectedValueOnce(httpError(401));

        const outcome = await auth.checkAuth();

        expect(outcome).toBe('unauthenticated');
        expect(getAuthState()).toMatchObject({user: null, isInitialized: true, isLoading: false});
        expect(getClientSessionUserId()).toBeNull();
    });

    it('401 on a signed-in store → unauthenticated: the user and the client session are cleared', async () => {
        await signIn(1, 'alice');
        meApi.mockRejectedValueOnce(httpError(401));

        const outcome = await auth.checkAuth();

        expect(outcome).toBe('unauthenticated');
        expect(getAuthState()).toMatchObject({user: null, isInitialized: true, isLoading: false});
        expect(getClientSessionUserId(), 'a 401 ends the client session').toBeNull();
    });

    it.each(NOT_A_401)('%s at app start → unreachable: the store stays uninitialized, so nothing reads it as signed out', async (_label, failure) => {
        meApi.mockRejectedValueOnce(failure());

        const outcome = await auth.checkAuth();

        expect(getAuthState().isInitialized, 'an unanswered check must leave a cold store uninitialized: initialized-and-signed-out is what sends the layout to the login').toBe(false);
        expect(getAuthState()).toMatchObject({user: null, isLoading: false});
        expect(getClientSessionUserId()).toBeNull();
        expect(outcome).toBe('unreachable');
    });

    it.each(NOT_A_401)('%s on a signed-in store → unreachable: the user and the client session stay', async (_label, failure) => {
        await signIn(1, 'alice');
        meApi.mockRejectedValueOnce(failure());

        const outcome = await auth.checkAuth();

        expect(getAuthState().user?.id, 'an unanswered check is not a sign-out: the signed-in user stays').toBe(1);
        expect(getClientSessionUserId(), 'an unanswered check is not a sign-out: the client session stays').toBe('1');
        expect(getAuthState()).toMatchObject({isInitialized: true, isLoading: false});
        expect(outcome).toBe('unreachable');
    });

    it('a 401 overtaken by a newer sign-in → superseded: the user who just signed in stays signed in', async () => {
        let fail: (reason: unknown) => void = () => undefined;
        meApi.mockImplementationOnce(
            () =>
                new Promise((_resolve, reject) => {
                    fail = reject;
                }),
        );

        const staleCheck = auth.checkAuth();
        await signIn(2, 'new-user');
        fail(httpError(401));

        expect(await staleCheck).toBe('superseded');
        expect(getAuthState().user?.id).toBe(2);
        expect(getAuthState().isInitialized).toBe(true);
        expect(getClientSessionUserId(), 'the stale 401 must not end the new session').toBe('2');
    });
});

/**
 * isSignOutRequested — a sign-out the user asked for is not a session that ended (K, step 19).
 *
 * The `(app)` layout's reactive redirect now sends a store that turns initialized and signed out to
 * `loginUrl(path + query)`, so that a session ending on a 401 brings the user back to the page that was
 * open. `auth.logout()` flips the store the same way, before its own `goto('/')`, and the reactive redirect
 * acted first: a deliberate sign-out landed on `/?redirect=%2Fdashboard` (`e2e/auth.spec.ts`: `logout returns
 * to login page`, 3a, 3b), and the next person to sign in would have landed on the previous user's page.
 * The approved contract: `auth.ts` exports `isSignOutRequested(): boolean`, which the layout reads to tell
 * the two apart —
 *   - `true` from the moment `auth.logout()` is called, so it is already set when the store flips;
 *   - `false` again after the next successful `auth.login()`, or a `checkAuth()` that answers `authenticated`;
 *   - never set by a `checkAuth()` 401: that sign-out was not requested, and it keeps the page;
 *   - cleared by `auth.reset()`.
 * The export is read through the module namespace: while it does not exist, each case fails on a message
 * naming it, instead of the whole file failing to import.
 */
describe('isSignOutRequested — a sign-out the user asked for is not a session that ended', () => {
    /** `isSignOutRequested()` of this instance of `auth.ts`: a missing export fails the case here, on this message. */
    function signOutRequested(module: typeof authModule = authModule): boolean {
        expect(module.isSignOutRequested, 'auth.ts exports isSignOutRequested(): boolean').toBeTypeOf('function');
        return module.isSignOutRequested();
    }

    /** `auth.logout()` with a server that answers it (`browser` is false here: the store navigates nowhere). */
    async function signOut(): Promise<void> {
        logoutApi.mockResolvedValueOnce(undefined);
        await auth.logout();
        expect(getAuthState(), 'premise: the logout left the store initialized and signed out').toMatchObject({user: null, isInitialized: true, isLoading: false});
    }

    beforeEach(() => {
        auth.reset();
        loginApi.mockReset();
        logoutApi.mockReset();
        meApi.mockReset();
    });

    it('false before anything happened: a freshly loaded store has not been asked to sign out', async () => {
        // A fresh instance of the module, so that this is its initial value and not the one `auth.reset()` leaves.
        vi.resetModules();
        const fresh = await import('./auth');

        expect(signOutRequested(fresh)).toBe(false);
    });

    it('auth.logout() → true from the moment it is called, so it is already set when the store flips to signed out', async () => {
        await signIn(1, 'alice');
        expect(signOutRequested(), 'premise: a signed-in user has not asked to sign out').toBe(false);
        let answerLogout: (value: unknown) => void = () => undefined;
        logoutApi.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    answerLogout = resolve;
                }),
        );
        // What the layout's reactive redirect reads: the flag at the moment the store turns initialized and signed out.
        const readAtFlip: boolean[] = [];
        const unsubscribe = auth.subscribe((state) => {
            if (state.isInitialized && state.user === null) readAtFlip.push(signOutRequested());
        });

        try {
            const loggingOut = auth.logout();
            expect(signOutRequested(), 'requested as soon as logout() is called, while the server is still answering').toBe(true);
            answerLogout(undefined);
            await loggingOut;
        } finally {
            unsubscribe();
        }

        expect(getAuthState(), 'premise: the logout flipped the store to initialized and signed out').toMatchObject({user: null, isInitialized: true});
        expect(readAtFlip, 'whoever reacts to the flip reads a requested sign-out').toEqual([true]);
        expect(signOutRequested(), 'and it stays requested once the logout is done').toBe(true);
    });

    it('a successful auth.login() after a logout → false: whoever signs in next starts afresh', async () => {
        await signIn(1, 'alice');
        await signOut();
        expect(signOutRequested(), 'premise: the logout is a requested sign-out').toBe(true);

        await signIn(2, 'bob');

        expect(signOutRequested(), 'a successful sign-in ends the requested sign-out').toBe(false);
    });

    it('a checkAuth() 200 after a logout → false: the session is authenticated again', async () => {
        await signIn(1, 'alice');
        await signOut();
        expect(signOutRequested(), 'premise: the logout is a requested sign-out').toBe(true);
        meApi.mockResolvedValueOnce({user: user(2, 'bob')});

        expect(await auth.checkAuth(), 'premise: the check answers authenticated').toBe('authenticated');

        expect(signOutRequested(), 'an authenticated check ends the requested sign-out').toBe(false);
    });

    it('a checkAuth() 401 after a login → still false: a session that ended is not a sign-out the user asked for', async () => {
        await signIn(1, 'alice');
        expect(signOutRequested(), 'premise: a signed-in user has not asked to sign out').toBe(false);
        meApi.mockRejectedValueOnce(httpError(401));

        expect(await auth.checkAuth(), 'premise: the check answers unauthenticated').toBe('unauthenticated');
        expect(getAuthState(), 'premise: the 401 flipped the store to initialized and signed out').toMatchObject({user: null, isInitialized: true});

        expect(signOutRequested(), 'a 401 does not request a sign-out: the layout must keep the page for the login').toBe(false);
    });

    it('auth.reset() → false', async () => {
        await signIn(1, 'alice');
        await signOut();
        expect(signOutRequested(), 'premise: the logout is a requested sign-out').toBe(true);

        auth.reset();

        expect(signOutRequested(), 'a reset clears the requested sign-out').toBe(false);
    });
});
