/**
 * forgotPasswordApi — «forgot password» by email (workstream E, lot E4a): the seam over `POST /email/password-reset`.
 *
 * The contract under test:
 *   - `requestPasswordResetEmail(identifier)` posts `{identifier}` once, through its generated alias, and resolves with
 *     nothing on the 202 — the same answer for everyone, which says nothing about the accounts; a refusal reaches the
 *     caller as raised;
 *   - `readForgotFailure(error)`: any 422 is `INVALID`; a coded refusal is its `error_code` — `EMAIL_UNAVAILABLE`,
 *     `EMAIL_LINKS_UNAVAILABLE`, `EMAIL_RATE_LIMITED` with `retryAfter` when `retry_after` is a finite number (the
 *     route has had no hold since lot E4b: no `FORGOT_PASSWORD_DISABLED`) —; no `detail` object (no answer, a
 *     plain-text `detail`) is `UNKNOWN`; it reads an `AxiosError` and an `ApiError` alike;
 *   - through the real client, only the transport faked: the 202 resolves, and each refusal of the route is read.
 *
 * Mocks: the alias is spied on the real generated client (restored after each test); the last block replaces
 * `axiosInstance.defaults.adapter` and puts it back. Node environment: nothing here renders.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {spyOnApi} from '$test/spyOnApi';
import {AxiosError, AxiosHeaders, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {ApiError, axiosInstance, zodiosApi} from '$lib/api';
import {readForgotFailure, requestPasswordResetEmail, type ForgotFailure} from './forgotPasswordApi';

const ALIAS = 'request_password_reset_email_api_v1_email_password_reset_post';
const ACCEPTED = {message: 'If an active account matches, its owner gets an email with a link to choose a new password'};

const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

function axiosRefusal(status: number, data: unknown, config: InternalAxiosRequestConfig = REQUEST): AxiosError {
    const response: AxiosResponse = {status, statusText: '', headers: {'content-type': 'application/json'}, config, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, config, {}, response);
}

const CARRIERS: Array<{carrier: string; refuse: (status: number, body?: unknown) => unknown}> = [
    {carrier: 'an AxiosError, as the generated client rejects', refuse: (status, body) => axiosRefusal(status, body)},
    {carrier: 'an ApiError', refuse: (status, body) => new ApiError(status, '', body)},
];

/** Each refusal of `POST /email/password-reset` (backend/app/api/v1/email.py), and what must be read of it. */
const REFUSALS: Array<{label: string; status: number; body: unknown; failure: ForgotFailure}> = [
    {label: '409 EMAIL_UNAVAILABLE', status: 409, body: {detail: {error_code: 'EMAIL_UNAVAILABLE', message: 'This instance cannot send emails'}}, failure: {errorCode: 'EMAIL_UNAVAILABLE'}},
    {label: '409 EMAIL_LINKS_UNAVAILABLE', status: 409, body: {detail: {error_code: 'EMAIL_LINKS_UNAVAILABLE', message: 'This instance cannot send emails with a link'}}, failure: {errorCode: 'EMAIL_LINKS_UNAVAILABLE'}},
    {label: '429 EMAIL_RATE_LIMITED', status: 429, body: {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 840, message: 'Too many requests: try again later'}}, failure: {errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 840}},
    {label: '422, a validation list', status: 422, body: {detail: [{loc: ['body', 'identifier'], msg: 'String should have at least 1 character', type: 'string_too_short'}]}, failure: {errorCode: 'INVALID'}},
];

afterEach(() => {
    vi.restoreAllMocks();
});

// =====================================================================================================================
describe('requestPasswordResetEmail — through its alias', () => {
    it('FPA-01: posts {identifier} alone, once, and resolves with nothing', async () => {
        const alias = spyOnApi(zodiosApi, ALIAS).mockResolvedValueOnce(ACCEPTED);

        await expect(requestPasswordResetEmail('zq_alice')).resolves.toBeUndefined();
        expect(alias).toHaveBeenCalledTimes(1);
        expect(alias.mock.calls[0][0]).toStrictEqual({identifier: 'zq_alice'});
    });

    it('FPA-02: a refusal reaches the caller as raised', async () => {
        const refusal = axiosRefusal(409, {detail: {error_code: 'EMAIL_UNAVAILABLE'}});
        spyOnApi(zodiosApi, ALIAS).mockRejectedValueOnce(refusal);

        await expect(requestPasswordResetEmail('zq_alice')).rejects.toBe(refusal);
    });
});

// =====================================================================================================================
describe.each(CARRIERS)('readForgotFailure — a refusal carried by $carrier', ({refuse}) => {
    it.each(REFUSALS)('FPA-03: $label', ({status, body, failure}) => {
        expect(readForgotFailure(refuse(status, body))).toEqual(failure);
    });

    it('FPA-04: any 422 is INVALID, whatever its body', () => {
        expect(readForgotFailure(refuse(422, {detail: {error_code: 'SOMETHING_ELSE'}}))).toStrictEqual({errorCode: 'INVALID'});
        expect(readForgotFailure(refuse(422, undefined))).toStrictEqual({errorCode: 'INVALID'});
    });

    it.each<{label: string; detail: Record<string, unknown>}>([
        {label: 'a retry_after that is text', detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: '840'}},
        {label: 'a retry_after that is NaN', detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: Number.NaN}},
    ])('FPA-05: $label is left out, the code kept', ({detail}) => {
        const failure = readForgotFailure(refuse(429, {detail}));

        expect(failure.errorCode).toBe('EMAIL_RATE_LIMITED');
        expect(failure.retryAfter).toBeUndefined();
    });

    it.each<{label: string; status: number; body: unknown}>([
        {label: 'no error_code', status: 409, body: {detail: {message: 'no code'}}},
        {label: 'a plain-text detail', status: 403, body: {detail: 'Forbidden'}},
        {label: 'no detail', status: 500, body: {}},
        {label: 'a body that is not JSON (a proxy page)', status: 502, body: '<html><body>502 Bad Gateway</body></html>'},
    ])('FPA-06: $label is UNKNOWN', ({status, body}) => {
        expect(readForgotFailure(refuse(status, body)).errorCode).toBe('UNKNOWN');
    });
});

describe('readForgotFailure — what carries no answer is UNKNOWN', () => {
    it.each<{label: string; make: () => unknown}>([
        {label: 'a request that reached no server', make: () => new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {})},
        {label: 'a request that timed out', make: () => new AxiosError('timeout of 30000ms exceeded', AxiosError.ECONNABORTED, REQUEST, {})},
        {label: 'a plain Error', make: () => new Error('boom')},
        {label: 'null', make: () => null},
    ])('FPA-07: $label', ({make}) => {
        expect(readForgotFailure(make())).toStrictEqual({errorCode: 'UNKNOWN'});
    });
});

// =====================================================================================================================
describe('through the real client, only the transport faked', () => {
    const received: InternalAxiosRequestConfig[] = [];
    let realAdapter: typeof axiosInstance.defaults.adapter;

    beforeEach(() => {
        realAdapter = axiosInstance.defaults.adapter;
        received.length = 0;
    });

    afterEach(() => {
        axiosInstance.defaults.adapter = realAdapter;
    });

    function serverAnswers(status: number, data: unknown): void {
        const adapter: AxiosAdapter = async (config) => {
            received.push(config);
            if (status >= 200 && status < 300) return {status, statusText: 'Accepted', headers: {'content-type': 'application/json'}, config, request: {}, data};
            throw axiosRefusal(status, data, config);
        };
        axiosInstance.defaults.adapter = adapter;
    }

    it('FPA-08: the 202 of POST /api/v1/email/password-reset resolves with nothing; the body is {identifier}', async () => {
        serverAnswers(202, ACCEPTED);

        await expect(requestPasswordResetEmail('zq_alice@example.com')).resolves.toBeUndefined();
        expect(received.map(({method, url}) => `${method} ${url}`)).toEqual(['post /api/v1/email/password-reset']);
        const data = received[0]?.data;
        expect(typeof data === 'string' ? JSON.parse(data) : data).toStrictEqual({identifier: 'zq_alice@example.com'});
    });

    it.each(REFUSALS)('FPA-09: $label, as the client raises it, is read', async ({status, body, failure}) => {
        serverAnswers(status, body);

        const read = await requestPasswordResetEmail('zq_alice').then(() => null, readForgotFailure);

        expect(received, 'premise: the request reached the transport').toHaveLength(1);
        expect(read).toEqual(failure);
    });

    it('FPA-10: a request that reaches no server is UNKNOWN', async () => {
        axiosInstance.defaults.adapter = async (config) => {
            received.push(config);
            throw new AxiosError('Network Error', AxiosError.ERR_NETWORK, config, {});
        };

        await expect(requestPasswordResetEmail('zq_alice').then(() => null, readForgotFailure)).resolves.toStrictEqual({errorCode: 'UNKNOWN'});
    });
});
