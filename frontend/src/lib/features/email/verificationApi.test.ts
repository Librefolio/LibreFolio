/**
 * verificationApi — the seam of the verification of an email address at sign-up (workstream E, lot E5a; developer
 * decision 44) on the generated client.
 *
 * The contract under test:
 *   - `confirmEmailVerification(token)` posts `POST /email/verification/confirm` once, through its generated alias, with
 *     `{token}` alone, and answers `{username}` alone; a refusal reaches the caller as the client raised it;
 *   - `resendEmailVerification(username, password)` posts `POST /email/verification/resend` once, through its alias,
 *     with `{username, password}`, and answers the language of the email; a refusal reaches the caller as raised;
 *   - `readLinkRefusal(error)`: a 400 whose `detail` is `TOKEN_INVALID` is the token's status — `expired`, `consumed`,
 *     `revoked`, `unknown`, and `unknown` for any other or missing status —; anything else but the block's refusal
 *     (below) — another status code, another code, a `detail` that is not an object, no answer at all — is `null`, a
 *     failure that may be tried again;
 *   - on a blocked instance (lot E-10) the confirm is refused before its route, and `readLinkRefusal` reads that
 *     refusal as `blocked`: any 401, whatever its body — the route is public, so its only 401 is the block's, to a
 *     caller without a session — and a 423 whose `detail.code` is `instance_blocked` (workstream H's
 *     `isInstanceBlockedError`), to a signed-in one; a 423 without that code, and that code under another status, are
 *     `null` like any other failure;
 *   - `readResendFailure(error)`: a coded refusal is its `error_code`, with `retryAfter` when `retry_after` is a finite
 *     number; no `detail` object — a validation list, a plain-text `detail` other than a 401's, no answer — is `UNKNOWN`;
 *   - a 401 of «resend» (lot E-11): one whose `detail` object is coded `INVALID_CREDENTIALS` — the route's own refusal of
 *     wrong credentials — is `INVALID_CREDENTIALS` alone; any other 401 — a plain-text `detail` (`Not authenticated`,
 *     `Session expired or invalid`, even `Invalid credentials`), no body, a `detail` object without that code — is
 *     `INSTANCE_BLOCKED` alone: the route is public and outside the block's allow-list (EVA-017 pins it), so its only
 *     other 401 is the block's, to a caller without a session; a 423 whose `detail.code` is `instance_blocked` (workstream
 *     H's `isInstanceBlockedError`), to a signed-in one, is `INSTANCE_BLOCKED` alone too; a 423 without that code, and
 *     that code under another status, are not the block: `UNKNOWN`, like any refusal without an `error_code`;
 *   - both readers read a refusal carried by axios's own `AxiosError` (what the generated client rejects with) or by an
 *     `ApiError`;
 *   - through the real client, only the transport faked: the requests reach it as described, and what a refusal rejects
 *     with is read by the two readers — the composition the page and the notice perform, the block's 401 and 423
 *     included.
 *
 * Mocks: the two aliases are spied on the real generated client (`vi.spyOn`, restored after each test), which also
 * proves they exist on it; the last block replaces `axiosInstance.defaults.adapter` and puts it back after each test
 * (the pattern of `emailApi.test.ts`), and turns off workstream H's block flag, which a 423 `instance_blocked` turns on
 * through the client's response interceptor. Node environment: nothing here renders; `$app/environment` says no
 * browser, so the interceptor's 401 branch (to the sign-in) stays inert.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {AxiosError, AxiosHeaders, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {ApiError, axiosInstance, zodiosApi} from '$lib/api';
import {instanceBlock} from '$lib/features/instance/instanceBlock.svelte';
import {confirmEmailVerification, readLinkRefusal, readResendFailure, resendEmailVerification, type ResendFailure, type VerificationLinkRefusal} from './verificationApi';

const CONFIRM_ALIAS = 'confirm_email_verification_api_v1_email_verification_confirm_post';
const RESEND_ALIAS = 'resend_email_verification_api_v1_email_verification_resend_post';
const TOKEN = 'zq-Verify_Token-0123';

/** What a blocked instance answers a signed-in caller (`refuse_when_blocked`, workstream H): a 423 with this body. */
const BLOCKED_BODY = {detail: {code: 'instance_blocked', message: 'This instance is blocked by its hosting provider'}};

/** What «resend» answers wrong credentials since lot E-11 (`api/v1/email.py`): its own 401, coded like E's other refusals. */
const INVALID_CREDENTIALS_BODY = {detail: {error_code: 'INVALID_CREDENTIALS', message: 'Invalid credentials'}};

/** The config axios attaches to an error raised outside a request. */
const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** What axios rejects with when the server answers `status` (lib/core/settle.js): an AxiosError carrying the response. */
function axiosRefusal(status: number, data: unknown, config: InternalAxiosRequestConfig = REQUEST): AxiosError {
    const response: AxiosResponse = {status, statusText: '', headers: {'content-type': 'application/json'}, config, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, config, {}, response);
}

/** The two shapes a refusal reaches the readers in. */
const CARRIERS: Array<{carrier: string; refuse: (status: number, body?: unknown) => unknown}> = [
    {carrier: 'an AxiosError, as the generated client rejects', refuse: (status, body) => axiosRefusal(status, body)},
    {carrier: 'an ApiError', refuse: (status, body) => new ApiError(status, '', body)},
];

/** What carries no answer at all. */
const NO_ANSWER: Array<{label: string; make: () => unknown}> = [
    {label: 'a request that reached no server', make: () => new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {})},
    {label: 'a request that timed out', make: () => new AxiosError('timeout of 30000ms exceeded', AxiosError.ECONNABORTED, REQUEST, {})},
    {label: 'a plain Error', make: () => new Error('boom')},
    {label: 'a thrown string', make: () => 'boom'},
    {label: 'undefined', make: () => undefined},
    {label: 'null', make: () => null},
];

afterEach(() => {
    vi.restoreAllMocks();
});

// =====================================================================================================================
describe('confirmEmailVerification and resendEmailVerification — through their aliases', () => {
    it('VFA-01: confirm posts {token} alone, once, and answers {username} alone', async () => {
        const alias = vi.spyOn(zodiosApi, CONFIRM_ALIAS).mockResolvedValueOnce({username: 'zq_alice'});

        await expect(confirmEmailVerification(TOKEN)).resolves.toStrictEqual({username: 'zq_alice'});
        expect(alias).toHaveBeenCalledTimes(1);
        expect(alias.mock.calls[0][0]).toStrictEqual({token: TOKEN});
    });

    it('VFA-02: resend posts {username, password}, once, and answers the language alone', async () => {
        const alias = vi.spyOn(zodiosApi, RESEND_ALIAS).mockResolvedValueOnce({language: 'it'});

        await expect(resendEmailVerification('zq_alice', 'Pass-2026')).resolves.toBe('it');
        expect(alias).toHaveBeenCalledTimes(1);
        expect(alias.mock.calls[0][0]).toStrictEqual({username: 'zq_alice', password: 'Pass-2026'});
    });

    it('VFA-03: a refusal of either reaches the caller as the client raised it', async () => {
        const refusedLink = axiosRefusal(400, {detail: {error_code: 'TOKEN_INVALID', status: 'expired'}});
        const refusedResend = axiosRefusal(401, INVALID_CREDENTIALS_BODY);
        vi.spyOn(zodiosApi, CONFIRM_ALIAS).mockRejectedValueOnce(refusedLink);
        vi.spyOn(zodiosApi, RESEND_ALIAS).mockRejectedValueOnce(refusedResend);

        await expect(confirmEmailVerification(TOKEN)).rejects.toBe(refusedLink);
        await expect(resendEmailVerification('zq_alice', 'wrong')).rejects.toBe(refusedResend);
    });
});

// =====================================================================================================================
describe.each(CARRIERS)('readLinkRefusal — a refusal carried by $carrier', ({refuse}) => {
    it.each<VerificationLinkRefusal>(['expired', 'consumed', 'revoked', 'unknown'])('VFA-04: 400 TOKEN_INVALID %s is %s', (status) => {
        expect(readLinkRefusal(refuse(400, {detail: {error_code: 'TOKEN_INVALID', status, message: 'This verification link is not valid'}}))).toBe(status);
    });

    it.each<{label: string; status: unknown}>([
        {label: 'valid', status: 'valid'},
        {label: 'a status no link has', status: 'weird'},
        {label: 'an empty status', status: ''},
        {label: 'a status that is not text', status: 42},
        {label: 'no status', status: undefined},
        {label: 'an inherited name', status: 'constructor'},
    ])('VFA-05: 400 TOKEN_INVALID with $label is unknown', ({status}) => {
        expect(readLinkRefusal(refuse(400, {detail: {error_code: 'TOKEN_INVALID', status}}))).toBe('unknown');
    });

    it.each<{label: string; status: number; body: unknown}>([
        {label: 'a 400 with another code', status: 400, body: {detail: {error_code: 'SOMETHING_ELSE', status: 'expired'}}},
        {label: 'a 400 with a plain-text detail', status: 400, body: {detail: 'Bad request'}},
        {label: 'a 422 validation list', status: 422, body: {detail: [{loc: ['body', 'token'], msg: 'Field required', type: 'missing'}]}},
        {label: 'TOKEN_INVALID with a 409', status: 409, body: {detail: {error_code: 'TOKEN_INVALID', status: 'expired'}}},
        {label: 'TOKEN_INVALID with a 500', status: 500, body: {detail: {error_code: 'TOKEN_INVALID', status: 'expired'}}},
        {label: 'a 502 without a body', status: 502, body: undefined},
    ])('VFA-06: $label is null — a failure to try again', ({status, body}) => {
        expect(readLinkRefusal(refuse(status, body))).toBeNull();
    });
});

describe('readLinkRefusal — what carries no answer is null', () => {
    it.each(NO_ANSWER)('VFA-07: $label', ({make}) => {
        expect(readLinkRefusal(make())).toBeNull();
    });
});

// =====================================================================================================================
describe.each(CARRIERS)('readLinkRefusal — the refusal of a blocked instance (lot E-10), carried by $carrier', ({refuse}) => {
    it.each<{label: string; body: unknown}>([
        {label: 'the plain-text detail of a caller without a session', body: {detail: 'Not authenticated'}},
        {label: 'the plain-text detail of a stale session', body: {detail: 'Session expired or invalid'}},
        {label: 'the block’s own body', body: BLOCKED_BODY},
        {label: 'a TOKEN_INVALID detail: the status decides, not the body', body: {detail: {error_code: 'TOKEN_INVALID', status: 'expired'}}},
        {label: 'no body', body: undefined},
    ])('VFA-19: any 401 — $label — is blocked: on this public route only the block answers 401', ({body}) => {
        expect(readLinkRefusal(refuse(401, body))).toBe('blocked');
    });

    it.each<{label: string; body: unknown}>([
        {label: 'with its message', body: BLOCKED_BODY},
        {label: 'the code alone', body: {detail: {code: 'instance_blocked'}}},
    ])('VFA-20: a 423 instance_blocked — $label — is blocked: the refusal a signed-in caller gets', ({body}) => {
        expect(readLinkRefusal(refuse(423, body))).toBe('blocked');
    });

    it.each<{label: string; status: number; body: unknown}>([
        {label: 'a 423 with another code', status: 423, body: {detail: {code: 'locked'}}},
        {label: 'a 423 with the code outside detail', status: 423, body: {code: 'instance_blocked'}},
        {label: 'a 423 with a plain-text detail', status: 423, body: {detail: 'instance_blocked'}},
        {label: 'a 423 TOKEN_INVALID', status: 423, body: {detail: {error_code: 'TOKEN_INVALID', status: 'expired'}}},
        {label: 'a 423 without a body', status: 423, body: undefined},
        {label: 'the block’s body with a 403', status: 403, body: BLOCKED_BODY},
        {label: 'the block’s body with a 500', status: 500, body: BLOCKED_BODY},
    ])('VFA-21: $label is null — not the block’s refusal: a failure to try again', ({status, body}) => {
        expect(readLinkRefusal(refuse(status, body))).toBeNull();
    });
});

// =====================================================================================================================
describe.each(CARRIERS)('readResendFailure — a refusal carried by $carrier', ({refuse}) => {
    it.each<{label: string; body: unknown}>([
        {label: 'with its message', body: INVALID_CREDENTIALS_BODY},
        {label: 'the code alone', body: {detail: {error_code: 'INVALID_CREDENTIALS'}}},
    ])('VFA-08: a 401 coded INVALID_CREDENTIALS — $label — is INVALID_CREDENTIALS alone: the route’s own refusal of wrong credentials (lot E-11)', ({body}) => {
        expect(readResendFailure(refuse(401, body)), 'the route’s own coded 401 says the credentials are wrong').toStrictEqual({errorCode: 'INVALID_CREDENTIALS'});
    });

    it.each<{status: number; detail: Record<string, unknown>; failure: ResendFailure}>([
        {status: 403, detail: {error_code: 'ACCOUNT_DISABLED', message: 'Account is disabled'}, failure: {errorCode: 'ACCOUNT_DISABLED'}},
        {status: 409, detail: {error_code: 'EMAIL_VERIFICATION_NOT_NEEDED', message: 'This account is active: sign in'}, failure: {errorCode: 'EMAIL_VERIFICATION_NOT_NEEDED'}},
        {status: 409, detail: {error_code: 'EMAIL_UNAVAILABLE', message: 'This instance cannot send emails'}, failure: {errorCode: 'EMAIL_UNAVAILABLE'}},
        {status: 409, detail: {error_code: 'EMAIL_LINKS_UNAVAILABLE', message: 'This instance cannot send emails with a link'}, failure: {errorCode: 'EMAIL_LINKS_UNAVAILABLE'}},
        {status: 409, detail: {error_code: 'USER_LIMIT_REACHED', message: 'The instance has reached its maximum number of users'}, failure: {errorCode: 'USER_LIMIT_REACHED'}},
        {status: 429, detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 180, message: 'Too many requests: try again later'}, failure: {errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 180}},
        {status: 502, detail: {error_code: 'EMAIL_DELIVERY_FAILED', message: 'The email could not be sent'}, failure: {errorCode: 'EMAIL_DELIVERY_FAILED'}},
        {status: 422, detail: {error_code: 'EMAIL_RECIPIENT_INVALID', message: 'The address of this account is not a single email address'}, failure: {errorCode: 'EMAIL_RECIPIENT_INVALID'}},
    ])('VFA-09: $status $detail.error_code is read', ({status, detail, failure}) => {
        expect(readResendFailure(refuse(status, {detail}))).toEqual(failure);
    });

    it.each<{label: string; retryAfter: unknown}>([
        {label: 'a numeric string', retryAfter: '180'},
        {label: 'NaN', retryAfter: Number.NaN},
        {label: 'Infinity', retryAfter: Number.POSITIVE_INFINITY},
        {label: 'null', retryAfter: null},
    ])('VFA-10: a retry_after that is $label is left out, the code kept', ({retryAfter}) => {
        const failure = readResendFailure(refuse(429, {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: retryAfter}}));

        expect(failure.errorCode).toBe('EMAIL_RATE_LIMITED');
        expect(failure.retryAfter).toBeUndefined();
    });

    it.each<{label: string; status: number; body: unknown}>([
        {label: 'no error_code', status: 409, body: {detail: {message: 'no code'}}},
        {label: 'an empty error_code', status: 409, body: {detail: {error_code: ''}}},
        {label: 'an error_code that is not text', status: 409, body: {detail: {error_code: 409}}},
        {label: 'a plain-text detail other than a 401', status: 403, body: {detail: 'Forbidden'}},
        {label: 'a validation list', status: 422, body: {detail: [{loc: ['body', 'password'], msg: 'Field required', type: 'missing'}]}},
        {label: 'no detail', status: 500, body: {}},
        {label: 'a body that is not JSON (a proxy page)', status: 502, body: '<html><body>502 Bad Gateway</body></html>'},
    ])('VFA-11: $label is UNKNOWN', ({status, body}) => {
        expect(readResendFailure(refuse(status, body)).errorCode).toBe('UNKNOWN');
    });
});

describe('readResendFailure — what carries no answer is UNKNOWN', () => {
    it.each(NO_ANSWER)('VFA-12: $label', ({make}) => {
        expect(readResendFailure(make())).toStrictEqual({errorCode: 'UNKNOWN'});
    });
});

// =====================================================================================================================
describe.each(CARRIERS)('readResendFailure — the refusal of a blocked instance (lot E-11), carried by $carrier', ({refuse}) => {
    it.each<{label: string; body: unknown}>([
        {label: 'the plain-text detail of a caller without a session', body: {detail: 'Not authenticated'}},
        {label: 'the plain-text detail of a stale session', body: {detail: 'Session expired or invalid'}},
        {label: 'the login’s plain-text detail, which this route no longer sends', body: {detail: 'Invalid credentials'}},
        {label: 'the code as a plain-text detail', body: {detail: 'INVALID_CREDENTIALS'}},
        {label: 'no body', body: undefined},
        {label: 'an empty body', body: ''},
        {label: 'no detail', body: {}},
        {label: 'a detail object without a code', body: {detail: {message: 'Invalid credentials'}}},
        {label: 'another code, its retry_after not read', body: {detail: {error_code: 'SOMETHING_ELSE', retry_after: 30}}},
        {label: 'the code in another case', body: {detail: {error_code: 'invalid_credentials'}}},
        {label: 'the code outside detail', body: {error_code: 'INVALID_CREDENTIALS'}},
        {label: 'the block’s own body', body: BLOCKED_BODY},
    ])('VFA-23: any other 401 — $label — is INSTANCE_BLOCKED alone: on this public route outside the allow-list only the block answers another 401', ({body}) => {
        expect(readResendFailure(refuse(401, body)), 'a 401 that is not the route’s own is the instance’s block, not wrong credentials').toStrictEqual({errorCode: 'INSTANCE_BLOCKED'});
    });

    it.each<{label: string; body: unknown}>([
        {label: 'with its message', body: BLOCKED_BODY},
        {label: 'the code alone', body: {detail: {code: 'instance_blocked'}}},
    ])('VFA-24: a 423 instance_blocked — $label — is INSTANCE_BLOCKED alone: the refusal a signed-in caller gets', ({body}) => {
        expect(readResendFailure(refuse(423, body)), 'the 423 that isInstanceBlockedError recognises is the instance’s block').toStrictEqual({errorCode: 'INSTANCE_BLOCKED'});
    });

    it.each<{label: string; status: number; body: unknown}>([
        {label: 'a 423 with another code', status: 423, body: {detail: {code: 'locked'}}},
        {label: 'a 423 with the code outside detail', status: 423, body: {code: 'instance_blocked'}},
        {label: 'a 423 with a plain-text detail', status: 423, body: {detail: 'instance_blocked'}},
        {label: 'a 423 without a body', status: 423, body: undefined},
        {label: 'the block’s body with a 403', status: 403, body: BLOCKED_BODY},
        {label: 'the block’s body with a 500', status: 500, body: BLOCKED_BODY},
    ])('VFA-25: $label is UNKNOWN — not the block’s refusal', ({status, body}) => {
        expect(readResendFailure(refuse(status, body)).errorCode, 'only a 401 or the 423 isInstanceBlockedError recognises is the block').toBe('UNKNOWN');
    });
});

// =====================================================================================================================
describe('through the real client, only the transport faked', () => {
    /** The requests the fake transport received. */
    const received: InternalAxiosRequestConfig[] = [];
    let realAdapter: typeof axiosInstance.defaults.adapter;

    beforeEach(() => {
        realAdapter = axiosInstance.defaults.adapter;
        received.length = 0;
    });

    afterEach(() => {
        axiosInstance.defaults.adapter = realAdapter;
        // A 423 instance_blocked through the real client turns workstream H's block flag on (its response interceptor).
        instanceBlock.clear();
    });

    /** The server answers `status` with `data`, settled as axios's own adapters settle it: a 2xx resolves, any other status rejects. */
    function serverAnswers(status: number, data: unknown): void {
        const adapter: AxiosAdapter = async (config) => {
            received.push(config);
            if (status >= 200 && status < 300) return {status, statusText: 'OK', headers: {'content-type': 'application/json'}, config, request: {}, data};
            throw axiosRefusal(status, data, config);
        };
        axiosInstance.defaults.adapter = adapter;
    }

    function noServer(): void {
        const adapter: AxiosAdapter = async (config) => {
            received.push(config);
            throw new AxiosError('Network Error', AxiosError.ERR_NETWORK, config, {});
        };
        axiosInstance.defaults.adapter = adapter;
    }

    /** The JSON body of the request the transport received. */
    function sentBody(): unknown {
        const data = received[0]?.data;
        return typeof data === 'string' ? JSON.parse(data) : data;
    }

    it('VFA-13: confirm reaches POST /api/v1/email/verification/confirm with {token}, and its answer comes back as {username} alone', async () => {
        serverAnswers(200, {username: 'zq_alice', note: 'a field the schema does not know'});

        await expect(confirmEmailVerification(TOKEN)).resolves.toStrictEqual({username: 'zq_alice'});
        expect(received.map(({method, url}) => `${method} ${url}`)).toEqual(['post /api/v1/email/verification/confirm']);
        expect(sentBody()).toStrictEqual({token: TOKEN});
    });

    it('VFA-14: resend reaches POST /api/v1/email/verification/resend with {username, password}, and the language comes back', async () => {
        serverAnswers(200, {language: 'fr'});

        await expect(resendEmailVerification('zq_alice', 'Pass-2026')).resolves.toBe('fr');
        expect(received.map(({method, url}) => `${method} ${url}`)).toEqual(['post /api/v1/email/verification/resend']);
        expect(sentBody()).toStrictEqual({username: 'zq_alice', password: 'Pass-2026'});
    });

    it.each<VerificationLinkRefusal>(['expired', 'consumed', 'revoked', 'unknown'])('VFA-15: a refused link (%s), as the client raises it, is read by readLinkRefusal', async (status) => {
        serverAnswers(400, {detail: {error_code: 'TOKEN_INVALID', status, message: 'This verification link is not valid'}});

        await expect(confirmEmailVerification(TOKEN).then(() => 'resolved', readLinkRefusal)).resolves.toBe(status);
    });

    it('VFA-16: a confirm that reaches no server is null — tried again', async () => {
        noServer();

        await expect(confirmEmailVerification(TOKEN).then(() => 'resolved', readLinkRefusal)).resolves.toBeNull();
        expect(received, 'premise: the request reached the transport').toHaveLength(1);
    });

    it.each<{label: string; status: number; body: unknown; failure: ResendFailure}>([
        {label: '401 INVALID_CREDENTIALS, the route’s own refusal', status: 401, body: INVALID_CREDENTIALS_BODY, failure: {errorCode: 'INVALID_CREDENTIALS'}},
        {label: '403 ACCOUNT_DISABLED', status: 403, body: {detail: {error_code: 'ACCOUNT_DISABLED', message: 'Account is disabled'}}, failure: {errorCode: 'ACCOUNT_DISABLED'}},
        {label: '409 EMAIL_UNAVAILABLE', status: 409, body: {detail: {error_code: 'EMAIL_UNAVAILABLE', message: 'This instance cannot send emails'}}, failure: {errorCode: 'EMAIL_UNAVAILABLE'}},
        {label: '429 EMAIL_RATE_LIMITED', status: 429, body: {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 840, message: 'Too many requests: try again later'}}, failure: {errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 840}},
        {label: '502 EMAIL_DELIVERY_FAILED', status: 502, body: {detail: {error_code: 'EMAIL_DELIVERY_FAILED', message: 'The email could not be sent'}}, failure: {errorCode: 'EMAIL_DELIVERY_FAILED'}},
    ])('VFA-17: $label, as the client raises it, is read by readResendFailure', async ({status, body, failure}) => {
        serverAnswers(status, body);

        const read = await resendEmailVerification('zq_alice', 'Pass-2026').then(() => null, readResendFailure);

        expect(received, 'premise: the request reached the transport').toHaveLength(1);
        expect(read).toEqual(failure);
    });

    it('VFA-18: a resend that reaches no server is UNKNOWN', async () => {
        noServer();

        await expect(resendEmailVerification('zq_alice', 'Pass-2026').then(() => null, readResendFailure)).resolves.toStrictEqual({errorCode: 'UNKNOWN'});
    });

    it.each<{label: string; status: number; body: unknown}>([
        {label: 'the 401 of a caller without a session', status: 401, body: {detail: 'Not authenticated'}},
        {label: 'the 423 instance_blocked of a signed-in caller', status: 423, body: BLOCKED_BODY},
    ])('VFA-22: on a blocked instance, $label, as the client raises it, is read by readLinkRefusal as blocked', async ({status, body}) => {
        serverAnswers(status, body);

        await expect(confirmEmailVerification(TOKEN).then(() => 'resolved', readLinkRefusal)).resolves.toBe('blocked');
        expect(received, 'premise: the request reached the transport').toHaveLength(1);
    });

    it.each<{label: string; status: number; body: unknown}>([
        {label: 'the 401 of a caller without a session', status: 401, body: {detail: 'Not authenticated'}},
        {label: 'the 423 instance_blocked of a signed-in caller', status: 423, body: BLOCKED_BODY},
    ])('VFA-26: on a blocked instance (lot E-11), $label, as the client raises it, is read by readResendFailure as INSTANCE_BLOCKED', async ({status, body}) => {
        serverAnswers(status, body);

        const read = await resendEmailVerification('zq_alice', 'Pass-2026').then(() => null, readResendFailure);

        expect(received, 'premise: the request reached the transport').toHaveLength(1);
        expect(read, 'the block’s refusal says the instance is blocked, never that the credentials are wrong').toStrictEqual({errorCode: 'INSTANCE_BLOCKED'});
    });
});
