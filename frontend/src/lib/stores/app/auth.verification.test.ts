/**
 * The sign-in store and email verification (lot E5b, developer decision 44): what `auth.login()` leaves in `authError`
 * when the login answers 403 `EMAIL_NOT_VERIFIED` — the right password of an account waiting for its link.
 *
 * The contract under test:
 *   - a 403 whose `detail` carries `error_code: 'EMAIL_NOT_VERIFIED'` → `{key: 'email.verification.loginRequired'}`,
 *     the key the sign-in card answers with «send the link again» (`features/email/VerificationNotice.svelte`);
 *   - a 403 `ACCOUNT_DISABLED` is still `auth.accountDisabled`, and any other 403 still `auth.loginFailed` — the code on
 *     a 401 still changes nothing: one key for every 401, so that no answer tells which accounts exist;
 *   - the key is a sentence in the four catalogues (E's `email.verification.loginRequired`).
 *
 * Mocks: the generated client's three auth aliases, and the modules the store reaches for at sign-in — as in
 * `auth.test.ts`, which this file leaves to workstream A. Rejections are built as axios raises them.
 *
 * Node environment: nothing here renders. Red until E5b is applied (`AuthErrorKey` and `loginErrorKey`).
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {AxiosError, AxiosHeaders, type InternalAxiosRequestConfig} from 'axios';
import {get} from 'svelte/store';
import type {AuthError, AuthErrorKey} from '$lib/types';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

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
vi.mock('$lib/debug', () => ({debug: {log: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn()}}));
vi.mock('$lib/stores/app/language', () => ({currentLanguage: {set: vi.fn()}}));
vi.mock('$lib/stores/app/settings', () => ({userSettings: {setDirect: vi.fn()}}));
vi.mock('$lib/stores/app/donationPopupStore.svelte', () => ({donationPopup: {trigger: vi.fn()}}));

import {auth, authError} from './auth';

const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** The server answered with this status and body: axios rejects with the response attached. */
function httpError(status: number, data: unknown): AxiosError {
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, REQUEST, {}, {status, statusText: '', headers: {}, config: REQUEST, data});
}

const keyed = (key: AuthErrorKey): AuthError => ({key});

/** The body of the login's 403 for an account waiting for its email verification (`backend/app/api/v1/auth.py`). */
const EMAIL_NOT_VERIFIED = {detail: {error_code: 'EMAIL_NOT_VERIFIED', message: 'Verify your email address first'}};
const ACCOUNT_DISABLED = {detail: {error_code: 'ACCOUNT_DISABLED', message: 'Account is disabled'}};

async function failedSignIn(failure: unknown): Promise<unknown> {
    loginApi.mockRejectedValueOnce(failure);
    expect(await auth.login('zq_vera', 'Hooks-Pass-2026'), 'premise: the sign-in fails').toBe(false);
    return get(authError);
}

beforeEach(() => {
    auth.reset();
    loginApi.mockReset();
    logoutApi.mockReset();
    meApi.mockReset();
});

describe('the sign-in of an account waiting for its email verification', () => {
    it.each([
        ['the contract body, code and message', EMAIL_NOT_VERIFIED],
        ['the code alone', {detail: {error_code: 'EMAIL_NOT_VERIFIED'}}],
    ])('AVR-01: a 403 carrying EMAIL_NOT_VERIFIED (%s) → {key: email.verification.loginRequired}', async (_label, body) => {
        expect(await failedSignIn(httpError(403, body))).toEqual(keyed('email.verification.loginRequired'));
    });

    it('AVR-02: a 403 ACCOUNT_DISABLED is still auth.accountDisabled', async () => {
        expect(await failedSignIn(httpError(403, ACCOUNT_DISABLED))).toEqual(keyed('auth.accountDisabled'));
    });

    it.each([
        ['a plain "Forbidden" detail', {detail: 'Forbidden'}],
        ['another error code', {detail: {error_code: 'OTHER'}}],
        ['the message without the code', {detail: {message: 'Verify your email address first'}}],
        ['a code that is not text', {detail: {error_code: 403}}],
        ['a body with no detail', {}],
    ])('AVR-03: any other 403 (%s) is still auth.loginFailed', async (_label, body) => {
        expect(await failedSignIn(httpError(403, body))).toEqual(keyed('auth.loginFailed'));
    });

    it('AVR-04: the code on a 401 changes nothing — one key for every 401', async () => {
        expect(await failedSignIn(httpError(401, EMAIL_NOT_VERIFIED))).toEqual(keyed('auth.invalidCredentials'));
    });

    it.each(Object.entries({en, it: itCatalogue, fr, es}))('AVR-05: email.verification.loginRequired is a sentence in %s', (_language, catalogue) => {
        const message = (catalogue as {email?: {verification?: {loginRequired?: unknown}}}).email?.verification?.loginRequired;

        expect(typeof message === 'string' && message.trim().length > 0).toBe(true);
    });
});
