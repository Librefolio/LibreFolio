/**
 * emailApi — the seam of the Email tab on the generated client (workstream E, lots E2 and E3p).
 *
 * The contract under test:
 *   - `fetchEmailStatus()` asks `GET /email/status` once, through its generated alias, and normalizes the answer into
 *     `EmailStatus`, all six keys always present: `state` as answered; `problem` and `variable` a non-empty string,
 *     else null; `checks` the answered list, else `[]`; `budget` an object, else null; `links` narrowed to
 *     `{ready, base, problem}` — ready only when `ready` is `true` and `base` a non-empty string, `base` null unless
 *     ready, `problem` a non-empty string else null, and `{ready: false, base: null, problem: null}` when `links` is
 *     absent (an older server) or not an object. The generated type of an optional field is wider than its schema (it
 *     admits an array), so a value of the wrong shape is dropped, never carried. A refusal reaches the caller as the
 *     client raised it;
 *   - `issueProbeNonce()` posts `POST /users/address-probe` once, through its alias, with no body, and answers the
 *     nonce alone; a refusal reaches the caller as the client raised it;
 *   - `sendTestEmail()` posts `POST /email/test` once, through its alias, with no body, and answers what it answered;
 *   - `readTestFailure(error)` reads the `detail` of a refused test email — `{error_code, problem | retry_after |
 *     smtp_code, message}`, `backend/app/api/v1/email.py` — carried either by axios's own `AxiosError` (its
 *     `response.data`: what the generated client rejects with) or by an `ApiError` (its `data`): 409
 *     EMAIL_UNAVAILABLE with its problem, 429 EMAIL_RATE_LIMITED with a finite numeric retry_after, 502
 *     EMAIL_DELIVERY_FAILED with its smtp_code, 422 EMAIL_RECIPIENT_INVALID; a field of the wrong type is left out;
 *     a body without a `detail` object, and anything that carries no body (a network error, a plain Error), is
 *     `UNKNOWN`;
 *   - the refusal helpers it is built on, exported for `verificationApi.ts` (lot E5a): `refusalBody` is the body of a
 *     refusal (an `AxiosError`'s `response.data`, an `ApiError`'s `data`, else undefined), `refusalStatus` its HTTP
 *     status (undefined without an answer), `refusalDetail` its `detail` when that is an object — not an array, not
 *     text —, else null, and `retryAfterOf` a `retry_after` that is a finite number, else undefined;
 *   - through the real client, only the transport faked: what a refused `sendTestEmail()` rejects with is read by
 *     `readTestFailure` — the composition the tab performs.
 *
 * On the last block. The generated client is Zodios on axios: on a non-2xx status axios rejects with its own
 * `AxiosError` carrying the response (the fake transport reproduces `axios/lib/core/settle.js`), the response
 * interceptor of `zodios-client.ts` passes it on, and no Zodios plugin converts it; `ApiError` is constructed nowhere
 * in `src/`. This block is what found the defect: while `readTestFailure` read an `ApiError` only, its four refusals
 * were read as UNKNOWN and the tab answered every refusal with its generic message. Its two controls prove the fake
 * transport is the one the client uses (a 200 comes back through the generated schema) and record the method and path
 * it was asked.
 *
 * Mocks: the three aliases are spied on the real generated client (`vi.spyOn`, restored after each test), which also
 * proves they exist on it; `ApiError` is the real class `readTestFailure` tests with `instanceof`. The last block
 * replaces `axiosInstance.defaults.adapter` and puts it back after each test. Axios errors are built with axios's own
 * `AxiosError`, as in `stores/app/auth.test.ts`.
 *
 * Node environment: nothing here renders.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {AxiosError, AxiosHeaders, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {ApiError, axiosInstance, zodiosApi} from '$lib/api';
import {fetchEmailStatus, issueProbeNonce, readTestFailure, refusalBody, refusalDetail, refusalStatus, retryAfterOf, sendTestEmail, type EmailBudget, type EmailCheck, type EmailLinks, type EmailStatus, type EmailTestFailure} from './emailApi';

/** What `GET /email/status` answers, as the generated client types it: wider than its schema. */
type StatusAnswer = Awaited<ReturnType<typeof zodiosApi.get_email_status_api_v1_email_status_get>>;

const SMTP_OK: EmailCheck = {check_id: 'email.smtp', severity: 'ok', i18n_key: 'email.checks.smtp.ok', detail: {}};
const SMTP_INVALID: EmailCheck = {check_id: 'email.smtp', severity: 'error', i18n_key: 'email.checks.smtp.invalid', detail: {problem: 'SMTP_PORT_INVALID', variable: 'LIBREFOLIO_SMTP_PORT'}};
const ENCRYPTION_OK: EmailCheck = {check_id: 'email.smtp_encryption', severity: 'ok', i18n_key: 'email.checks.smtpEncryption.ok', detail: {}};
const ENCRYPTION_PLAIN: EmailCheck = {check_id: 'email.smtp_encryption', severity: 'warning', i18n_key: 'email.checks.smtpEncryption.plain', detail: {}};
const BUDGET: EmailBudget = {max_per_hour: 20, remaining: 17, retry_after_seconds: 0};
/** `links` when the answer carries none (an older server), or nothing usable: emails cannot carry links. */
const NO_LINKS: EmailLinks = {ready: false, base: null, problem: null};
const PUBLIC_URL = 'https://folio.example.com:8443/app';

/** The config axios attaches to an error raised outside a request. */
const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** What axios rejects with when the server answers `status` (lib/core/settle.js): an AxiosError carrying the response. */
function axiosRefusal(status: number, statusText: string, data: unknown, config: InternalAxiosRequestConfig = REQUEST): AxiosError {
    const response: AxiosResponse = {status, statusText, headers: {'content-type': 'application/json'}, config, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, config, {}, response);
}

/** Each refusal of `POST /email/test` (backend/app/api/v1/email.py), and what the tab must read of it. */
const REFUSALS: Array<{label: string; status: number; statusText: string; detail: Record<string, unknown>; failure: EmailTestFailure}> = [
    {
        label: '409 EMAIL_UNAVAILABLE',
        status: 409,
        statusText: 'Conflict',
        detail: {error_code: 'EMAIL_UNAVAILABLE', problem: 'SMTP_PORT_INVALID', message: 'Email is off or cannot be used on this instance'},
        failure: {errorCode: 'EMAIL_UNAVAILABLE', problem: 'SMTP_PORT_INVALID'},
    },
    {
        label: '429 EMAIL_RATE_LIMITED',
        status: 429,
        statusText: 'Too Many Requests',
        detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 1800, message: 'The hourly email limit of the instance is reached'},
        failure: {errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 1800},
    },
    {
        label: '502 EMAIL_DELIVERY_FAILED',
        status: 502,
        statusText: 'Bad Gateway',
        detail: {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: 'AUTH_FAILED', message: 'The SMTP server did not take the message'},
        failure: {errorCode: 'EMAIL_DELIVERY_FAILED', smtpCode: 'AUTH_FAILED'},
    },
    {
        label: '422 EMAIL_RECIPIENT_INVALID',
        status: 422,
        statusText: 'Unprocessable Entity',
        detail: {error_code: 'EMAIL_RECIPIENT_INVALID', message: 'The address of this account is not a single email address'},
        failure: {errorCode: 'EMAIL_RECIPIENT_INVALID'},
    },
];

afterEach(() => {
    vi.restoreAllMocks();
});

// =====================================================================================================================
describe('fetchEmailStatus — GET /email/status, normalized into EmailStatus', () => {
    it.each<{label: string; answer: StatusAnswer; status: EmailStatus}>([
        {
            label: 'ready, with its checks, its budget and its links',
            answer: {state: 'ready', problem: null, variable: null, checks: [SMTP_OK, ENCRYPTION_PLAIN], budget: BUDGET, links: {ready: true, base: PUBLIC_URL, problem: null}},
            status: {state: 'ready', problem: null, variable: null, checks: [SMTP_OK, ENCRYPTION_PLAIN], budget: BUDGET, links: {ready: true, base: PUBLIC_URL, problem: null}},
        },
        {
            label: 'invalid, with the problem and the variable at fault, and no links',
            answer: {state: 'invalid', problem: 'SMTP_PORT_INVALID', variable: 'LIBREFOLIO_SMTP_PORT', checks: [SMTP_INVALID, ENCRYPTION_OK], budget: null, links: {ready: false, base: null, problem: 'PUBLIC_URL_MISSING'}},
            status: {state: 'invalid', problem: 'SMTP_PORT_INVALID', variable: 'LIBREFOLIO_SMTP_PORT', checks: [SMTP_INVALID, ENCRYPTION_OK], budget: null, links: {ready: false, base: null, problem: 'PUBLIC_URL_MISSING'}},
        },
    ])('a full answer ($label) is kept as answered, asked once through its alias', async ({answer, status}) => {
        const alias = vi.spyOn(zodiosApi, 'get_email_status_api_v1_email_status_get').mockResolvedValueOnce(answer);

        await expect(fetchEmailStatus()).resolves.toStrictEqual(status);
        expect(alias).toHaveBeenCalledTimes(1);
        expect(alias).toHaveBeenCalledWith();
    });

    it('a minimal answer ({state: off}) gets every key: problem, variable and budget null, no checks, no links', async () => {
        vi.spyOn(zodiosApi, 'get_email_status_api_v1_email_status_get').mockResolvedValueOnce({state: 'off'});

        await expect(fetchEmailStatus()).resolves.toStrictEqual({state: 'off', problem: null, variable: null, checks: [], budget: null, links: NO_LINKS});
    });

    it('an empty problem or variable names nothing: null', async () => {
        vi.spyOn(zodiosApi, 'get_email_status_api_v1_email_status_get').mockResolvedValueOnce({state: 'invalid', problem: '', variable: '', checks: [SMTP_OK], budget: null});

        await expect(fetchEmailStatus()).resolves.toStrictEqual({state: 'invalid', problem: null, variable: null, checks: [SMTP_OK], budget: null, links: NO_LINKS});
    });

    it.each<{label: string; answer: StatusAnswer; status: EmailStatus}>([
        {
            label: 'an array in problem',
            answer: {state: 'invalid', problem: ['SMTP_PORT_INVALID'], variable: 'LIBREFOLIO_SMTP_PORT'},
            status: {state: 'invalid', problem: null, variable: 'LIBREFOLIO_SMTP_PORT', checks: [], budget: null, links: NO_LINKS},
        },
        {
            label: 'an array in variable',
            answer: {state: 'invalid', problem: 'SMTP_PORT_INVALID', variable: ['LIBREFOLIO_SMTP_PORT']},
            status: {state: 'invalid', problem: 'SMTP_PORT_INVALID', variable: null, checks: [], budget: null, links: NO_LINKS},
        },
        {
            label: 'an array in budget',
            answer: {state: 'ready', checks: [SMTP_OK], budget: [BUDGET]},
            status: {state: 'ready', problem: null, variable: null, checks: [SMTP_OK], budget: null, links: NO_LINKS},
        },
        {
            label: 'an empty array in budget',
            answer: {state: 'ready', checks: [SMTP_OK], budget: []},
            status: {state: 'ready', problem: null, variable: null, checks: [SMTP_OK], budget: null, links: NO_LINKS},
        },
    ])('$label — the generated type admits it, the schema does not — is dropped: null', async ({answer, status}) => {
        vi.spyOn(zodiosApi, 'get_email_status_api_v1_email_status_get').mockResolvedValueOnce(answer);

        await expect(fetchEmailStatus()).resolves.toStrictEqual(status);
    });

    it('a refusal reaches the caller as the client raised it', async () => {
        const refusal = axiosRefusal(403, 'Forbidden', {detail: 'Admin privileges required'});
        vi.spyOn(zodiosApi, 'get_email_status_api_v1_email_status_get').mockRejectedValueOnce(refusal);

        await expect(fetchEmailStatus()).rejects.toBe(refusal);
    });
});

// =====================================================================================================================
describe('fetchEmailStatus — links narrowed to what the tab can trust (lot E3p)', () => {
    it.each<{label: string; links: unknown; expected: EmailLinks}>([
        {label: 'ready with a base', links: {ready: true, base: PUBLIC_URL, problem: null}, expected: {ready: true, base: PUBLIC_URL, problem: null}},
        {label: 'missing, with its problem', links: {ready: false, base: null, problem: 'PUBLIC_URL_MISSING'}, expected: {ready: false, base: null, problem: 'PUBLIC_URL_MISSING'}},
        {label: 'invalid, with its problem', links: {ready: false, base: null, problem: 'PUBLIC_URL_INVALID'}, expected: {ready: false, base: null, problem: 'PUBLIC_URL_INVALID'}},
        {label: 'absent (an older server)', links: undefined, expected: NO_LINKS},
        {label: 'an empty object', links: {}, expected: NO_LINKS},
        {label: 'ready without a base', links: {ready: true, base: null, problem: null}, expected: NO_LINKS},
        {label: 'ready with an empty base', links: {ready: true, base: '', problem: null}, expected: NO_LINKS},
        {label: 'ready with a base that is not a string', links: {ready: true, base: [PUBLIC_URL], problem: null}, expected: NO_LINKS},
        {label: 'a base while not ready', links: {ready: false, base: PUBLIC_URL, problem: 'PUBLIC_URL_INVALID'}, expected: {ready: false, base: null, problem: 'PUBLIC_URL_INVALID'}},
        {label: 'a base without ready', links: {base: PUBLIC_URL}, expected: NO_LINKS},
        {label: 'ready written as a string', links: {ready: 'true', base: PUBLIC_URL}, expected: NO_LINKS},
        {label: 'ready written as a number', links: {ready: 1, base: PUBLIC_URL}, expected: NO_LINKS},
        {label: 'an empty problem', links: {ready: false, base: null, problem: ''}, expected: NO_LINKS},
        {label: 'a problem that is not a string', links: {ready: false, base: null, problem: 42}, expected: NO_LINKS},
        {label: 'null', links: null, expected: NO_LINKS},
        {label: 'an array', links: [{ready: true, base: PUBLIC_URL}], expected: NO_LINKS},
        {label: 'a string', links: PUBLIC_URL, expected: NO_LINKS},
    ])('EAP-01: links $label', async ({links, expected}) => {
        // Through the spied alias, past the generated schema: what the narrowing must survive is a shape the schema refuses.
        vi.spyOn(zodiosApi, 'get_email_status_api_v1_email_status_get').mockResolvedValueOnce({state: 'ready', checks: [SMTP_OK], budget: BUDGET, links} as unknown as StatusAnswer);

        const status = await fetchEmailStatus();

        expect(status.links).toStrictEqual(expected);
        expect(status.links.ready === (status.links.base !== null), 'ready exactly when there is a base').toBe(true);
    });
});

// =====================================================================================================================
describe('issueProbeNonce — POST /users/address-probe (lot E3p)', () => {
    it('EAP-02: posts once, through its alias, with no body, and answers the nonce alone', async () => {
        const alias = vi.spyOn(zodiosApi, 'issue_address_probe_api_v1_users_address_probe_post').mockResolvedValueOnce({nonce: 'zq-nonce_0123', expires_at: '2026-10-15T20:00:00Z'});

        await expect(issueProbeNonce()).resolves.toBe('zq-nonce_0123');
        expect(alias).toHaveBeenCalledTimes(1);
        expect(alias.mock.calls[0][0], 'the nonce needs no body').toBeUndefined();
    });

    it('EAP-03: a refusal reaches the caller as the client raised it', async () => {
        const refusal = axiosRefusal(403, 'Forbidden', {detail: 'Admin privileges required'});
        vi.spyOn(zodiosApi, 'issue_address_probe_api_v1_users_address_probe_post').mockRejectedValueOnce(refusal);

        await expect(issueProbeNonce()).rejects.toBe(refusal);
    });
});

// =====================================================================================================================
describe('sendTestEmail — POST /email/test', () => {
    it('posts once, through its alias, with no body, and answers what the client answered', async () => {
        const answer = {language: 'it' as const, message: 'Test email sent'};
        const alias = vi.spyOn(zodiosApi, 'send_test_api_v1_email_test_post').mockResolvedValueOnce(answer);

        await expect(sendTestEmail()).resolves.toBe(answer);
        expect(alias).toHaveBeenCalledTimes(1);
        expect(alias.mock.calls[0][0], 'the test email goes to the caller’s own address: there is no body').toBeUndefined();
    });

    it('a refusal reaches the caller as the client raised it', async () => {
        const refusal = axiosRefusal(429, 'Too Many Requests', {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 1800}});
        vi.spyOn(zodiosApi, 'send_test_api_v1_email_test_post').mockRejectedValueOnce(refusal);

        await expect(sendTestEmail()).rejects.toBe(refusal);
    });
});

// =====================================================================================================================
/** The two shapes a refusal reaches `readTestFailure` in: axios's own error, what the generated client rejects with, and ApiError. */
const CARRIERS: Array<{carrier: string; refuse: (status: number, statusText: string, body?: unknown) => unknown}> = [
    {carrier: 'an AxiosError, as the generated client rejects', refuse: (status, statusText, body) => axiosRefusal(status, statusText, body)},
    {carrier: 'an ApiError', refuse: (status, statusText, body) => new ApiError(status, statusText, body)},
];

describe.each(CARRIERS)('readTestFailure — a refusal carried by $carrier', ({refuse}) => {
    it.each(REFUSALS)('$label', ({status, statusText, detail, failure}) => {
        expect(readTestFailure(refuse(status, statusText, {detail}))).toEqual(failure);
    });

    it.each<{label: string; retryAfter: unknown}>([
        {label: 'a numeric string', retryAfter: '1800'},
        {label: 'NaN', retryAfter: Number.NaN},
        {label: 'Infinity', retryAfter: Number.POSITIVE_INFINITY},
        {label: 'null', retryAfter: null},
        {label: 'a boolean', retryAfter: true},
    ])('a retry_after that is $label is left out, the code kept', ({retryAfter}) => {
        const failure = readTestFailure(refuse(429, 'Too Many Requests', {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: retryAfter}}));

        expect(failure.errorCode).toBe('EMAIL_RATE_LIMITED');
        expect(failure.retryAfter).toBeUndefined();
    });

    it('a field of the wrong type, or empty, is left out', () => {
        expect(readTestFailure(refuse(409, 'Conflict', {detail: {error_code: 'EMAIL_UNAVAILABLE', problem: 42}}))).toEqual({errorCode: 'EMAIL_UNAVAILABLE'});
        expect(readTestFailure(refuse(409, 'Conflict', {detail: {error_code: 'EMAIL_UNAVAILABLE', problem: ''}}))).toEqual({errorCode: 'EMAIL_UNAVAILABLE'});
        expect(readTestFailure(refuse(502, 'Bad Gateway', {detail: {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: 7}}))).toEqual({errorCode: 'EMAIL_DELIVERY_FAILED'});
        expect(readTestFailure(refuse(502, 'Bad Gateway', {detail: {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: ''}}))).toEqual({errorCode: 'EMAIL_DELIVERY_FAILED'});
    });

    it.each<{label: string; detail: Record<string, unknown>}>([
        {label: 'no error_code', detail: {problem: 'SMTP_PORT_INVALID'}},
        {label: 'an empty error_code', detail: {error_code: ''}},
        {label: 'an error_code that is not a string', detail: {error_code: 409}},
    ])('a detail with $label is UNKNOWN', ({detail}) => {
        expect(readTestFailure(refuse(409, 'Conflict', {detail})).errorCode).toBe('UNKNOWN');
    });

    it.each<{label: string; status: number; statusText: string; body: unknown}>([
        {label: 'a string detail (a plain HTTPException)', status: 403, statusText: 'Forbidden', body: {detail: 'Admin privileges required'}},
        {label: 'a validation list', status: 422, statusText: 'Unprocessable Entity', body: {detail: [{loc: ['body'], msg: 'Field required', type: 'missing'}]}},
        {label: 'no detail', status: 500, statusText: 'Internal Server Error', body: {}},
        {label: 'a null detail', status: 500, statusText: 'Internal Server Error', body: {detail: null}},
        {label: 'a body that is not JSON (a proxy page)', status: 502, statusText: 'Bad Gateway', body: '<html><body>502 Bad Gateway</body></html>'},
        {label: 'no body at all', status: 503, statusText: 'Service Unavailable', body: undefined},
    ])('a body with $label is UNKNOWN', ({status, statusText, body}) => {
        expect(readTestFailure(refuse(status, statusText, body))).toEqual({errorCode: 'UNKNOWN'});
    });
});

// =====================================================================================================================
describe('readTestFailure — what carries no body is UNKNOWN', () => {
    it.each<{label: string; make: () => unknown}>([
        {label: 'a request that reached no server (an AxiosError without a response)', make: () => new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {})},
        {label: 'a request that timed out (an AxiosError without a response)', make: () => new AxiosError('timeout of 30000ms exceeded', AxiosError.ECONNABORTED, REQUEST, {})},
        {label: 'a plain Error', make: () => new Error('boom')},
        {label: 'a thrown string', make: () => 'boom'},
        {label: 'undefined', make: () => undefined},
        {label: 'null', make: () => null},
    ])('$label', ({make}) => {
        expect(readTestFailure(make())).toEqual({errorCode: 'UNKNOWN'});
    });
});

// =====================================================================================================================
describe('the refusal helpers — exported for verificationApi (lot E5a)', () => {
    const DETAIL = {error_code: 'EMAIL_RATE_LIMITED', retry_after: 180};

    it('EAP-08: refusalBody is the body of the answer, whichever carries it, else undefined', () => {
        const body = {detail: DETAIL};
        expect(refusalBody(axiosRefusal(429, 'Too Many Requests', body))).toBe(body);
        expect(refusalBody(new ApiError(429, 'Too Many Requests', body))).toBe(body);
        expect(refusalBody(new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {}))).toBeUndefined();
        for (const other of [new Error('boom'), 'boom', null, undefined, {response: {data: body}}]) expect(refusalBody(other)).toBeUndefined();
    });

    it('EAP-09: refusalStatus is the status of the answer, whichever carries it, else undefined', () => {
        expect(refusalStatus(axiosRefusal(401, 'Unauthorized', {detail: 'Invalid credentials'}))).toBe(401);
        expect(refusalStatus(new ApiError(409, 'Conflict', {detail: DETAIL}))).toBe(409);
        expect(refusalStatus(new AxiosError('timeout of 30000ms exceeded', AxiosError.ECONNABORTED, REQUEST, {}))).toBeUndefined();
        for (const other of [new Error('boom'), 'boom', null, undefined, {status: 401}]) expect(refusalStatus(other)).toBeUndefined();
    });

    it.each<{label: string; body: unknown; read: Record<string, unknown> | null}>([
        {label: 'an object detail', body: {detail: DETAIL}, read: DETAIL},
        {label: 'a plain-text detail', body: {detail: 'Invalid credentials'}, read: null},
        {label: 'a validation list', body: {detail: [{loc: ['body'], msg: 'Field required'}]}, read: null},
        {label: 'a null detail', body: {detail: null}, read: null},
        {label: 'no detail', body: {}, read: null},
        {label: 'a body that is text', body: '<html>502</html>', read: null},
        {label: 'no body', body: undefined, read: null},
    ])('EAP-10: refusalDetail of $label', ({body, read}) => {
        expect(refusalDetail(axiosRefusal(409, 'Conflict', body))).toEqual(read);
        expect(refusalDetail(new ApiError(409, 'Conflict', body))).toEqual(read);
    });

    it('EAP-10: refusalDetail of what carries no answer is null', () => {
        for (const other of [new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {}), new Error('boom'), 'boom', null, undefined]) expect(refusalDetail(other)).toBeNull();
    });

    it.each<{label: string; fields: Record<string, unknown>; read: number | undefined}>([
        {label: 'a whole number', fields: {retry_after: 180}, read: 180},
        {label: 'zero', fields: {retry_after: 0}, read: 0},
        {label: 'a fraction', fields: {retry_after: 0.5}, read: 0.5},
        {label: 'a numeric string', fields: {retry_after: '180'}, read: undefined},
        {label: 'NaN', fields: {retry_after: Number.NaN}, read: undefined},
        {label: 'Infinity', fields: {retry_after: Number.POSITIVE_INFINITY}, read: undefined},
        {label: 'null', fields: {retry_after: null}, read: undefined},
        {label: 'nothing', fields: {}, read: undefined},
    ])('EAP-11: retryAfterOf $label', ({fields, read}) => {
        expect(retryAfterOf(fields)).toBe(read);
    });
});

// =====================================================================================================================
describe('through the real client, only the transport faked: the status with its links, the probe nonce, and what a refused sendTestEmail() rejects with are read', () => {
    /** The requests the fake transport received. */
    const received: InternalAxiosRequestConfig[] = [];
    let realAdapter: typeof axiosInstance.defaults.adapter;

    beforeEach(() => {
        realAdapter = axiosInstance.defaults.adapter;
        received.length = 0;
    });

    afterEach(() => {
        axiosInstance.defaults.adapter = realAdapter;
    });

    /** The server answers `status` with `data`, settled as axios's own adapters settle it: a 2xx resolves, any other status rejects. */
    function serverAnswers(status: number, data: unknown): void {
        const adapter: AxiosAdapter = async (config) => {
            received.push(config);
            if (status >= 200 && status < 300) return {status, statusText: 'OK', headers: {'content-type': 'application/json'}, config, request: {}, data};
            throw axiosRefusal(status, '', data, config);
        };
        axiosInstance.defaults.adapter = adapter;
    }

    /** No server answers: the request fails before any response. */
    function noServer(): void {
        const adapter: AxiosAdapter = async (config) => {
            received.push(config);
            throw new AxiosError('Network Error', AxiosError.ERR_NETWORK, config, {});
        };
        axiosInstance.defaults.adapter = adapter;
    }

    it('control: GET /email/status reaches the transport, and its answer comes back through the generated schema, normalized', async () => {
        serverAnswers(200, {state: 'ready', problem: null, variable: null, checks: [SMTP_OK, ENCRYPTION_PLAIN], budget: BUDGET});

        await expect(fetchEmailStatus()).resolves.toStrictEqual({state: 'ready', problem: null, variable: null, checks: [SMTP_OK, ENCRYPTION_PLAIN], budget: BUDGET, links: NO_LINKS});
        expect(received.map(({method, url}) => `${method} ${url}`)).toEqual(['get /api/v1/email/status']);
    });

    it('EAP-04: links ready come back through the generated schema, their base kept as answered', async () => {
        serverAnswers(200, {state: 'ready', problem: null, variable: null, checks: [SMTP_OK], budget: BUDGET, links: {ready: true, base: PUBLIC_URL, problem: null}});

        await expect(fetchEmailStatus()).resolves.toStrictEqual({state: 'ready', problem: null, variable: null, checks: [SMTP_OK], budget: BUDGET, links: {ready: true, base: PUBLIC_URL, problem: null}});
    });

    it('EAP-05: links missing come back with their problem, and no base', async () => {
        serverAnswers(200, {state: 'ready', problem: null, variable: null, checks: [SMTP_OK], budget: BUDGET, links: {ready: false, base: null, problem: 'PUBLIC_URL_MISSING'}});

        await expect(fetchEmailStatus()).resolves.toMatchObject({links: {ready: false, base: null, problem: 'PUBLIC_URL_MISSING'}});
    });

    it('EAP-06: issueProbeNonce — POST /users/address-probe reaches the transport with no body, and the nonce comes back', async () => {
        serverAnswers(200, {nonce: 'zq-nonce_0123', expires_at: '2026-10-15T20:00:00Z'});

        await expect(issueProbeNonce()).resolves.toBe('zq-nonce_0123');
        expect(received.map(({method, url}) => `${method} ${url}`)).toEqual(['post /api/v1/users/address-probe']);
        expect(received[0]?.data, 'no body').toBeUndefined();
    });

    it('EAP-07: issueProbeNonce — a 403, as the client raises it, rejects: no nonce is made up', async () => {
        serverAnswers(403, {detail: 'Admin privileges required'});

        await expect(issueProbeNonce()).rejects.toBeInstanceOf(AxiosError);
        expect(received, 'premise: the request reached the transport').toHaveLength(1);
    });

    it('control: POST /email/test reaches the transport with no body, and its answer comes back', async () => {
        serverAnswers(200, {language: 'fr', message: 'Test email sent'});

        await expect(sendTestEmail()).resolves.toStrictEqual({language: 'fr', message: 'Test email sent'});
        expect(received.map(({method, url}) => `${method} ${url}`)).toEqual(['post /api/v1/email/test']);
        expect(received[0]?.data, 'no body').toBeUndefined();
    });

    it('a request that reaches no server is UNKNOWN', async () => {
        noServer();

        await expect(sendTestEmail().then(() => null, readTestFailure)).resolves.toEqual({errorCode: 'UNKNOWN'});
        expect(received, 'premise: the request reached the transport').toHaveLength(1);
    });

    it.each(REFUSALS)('$label, as the client raises it, is read — not UNKNOWN', async ({status, detail, failure}) => {
        serverAnswers(status, {detail});

        const read = await sendTestEmail().then(() => null, readTestFailure);

        expect(received, 'premise: the request reached the transport').toHaveLength(1);
        expect(read, 'UNKNOWN here makes the tab answer this refusal with its generic message').toEqual(failure);
    });
});
