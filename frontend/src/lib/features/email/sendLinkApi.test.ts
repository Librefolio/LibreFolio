/**
 * sendLinkApi — «send by email» next to a shared link (workstream E, lot E4a; the language of the email, lot E-8): the
 * seam over `POST /email/links`.
 *
 * The contract under test:
 *   - `tokenFromLink(link)`: the `token` parameter of the link's fragment — among other parameters, percent-decoded —,
 *     the first one when there are two; null without a fragment, with a fragment that has no token, or with an empty
 *     token. A token in the query is never read: no link carries one;
 *   - `sendByEmailVisible()`: true only when `GET /system/instance` said `email.links === true` — absent, false, or any
 *     other value is false;
 *   - `sendLinkByEmail({purpose, token, to, language})` posts once, through its alias, `{purpose, token}` — with `to`
 *     only when one is given (an empty one is no `to`), with `language` only when one is given (decision N69: no
 *     `language` key otherwise, not even an undefined one) — and answers `{to, language}` alone, the language being the
 *     one the server answered, not the one asked for; a refusal reaches the caller as raised;
 *   - `readLinkSendFailure(error)`: the `error_code` of a coded refusal — the route's own 422s (`EMAIL_RECIPIENT_REQUIRED`,
 *     `…_NOT_ALLOWED`, `…_INVALID`) included —, with `smtpCode` when `smtp_code` is non-empty text and `retryAfter` when
 *     `retry_after` is a finite number; a 422 without a `detail` object — FastAPI's own validation, a list, as for a `to`
 *     that is not an email address — is `EMAIL_RECIPIENT_INVALID`, the only field the dialog lets anyone type being the
 *     address; any other answer without a `detail` object (a plain-text `detail`, no body) and no answer at all are
 *     `UNKNOWN`; it reads an `AxiosError` (what the generated client rejects with) and an `ApiError` alike;
 *   - through the real client, only the transport faked: the requests reach it as described — an invitation in a
 *     language as `{purpose, token, to, language}`, or `{purpose, token, language}` without an address, a reset link
 *     as `{purpose, token}` — and each refusal of the route is read — FastAPI's validation body for an invalid `to`
 *     included.
 *
 * Mocks: the instance configuration is a fake whose `config` the test sets; the alias is spied on the real generated
 * client (restored after each test); the last block replaces `axiosInstance.defaults.adapter` and puts it back. Node
 * environment: nothing here renders.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {AxiosError, AxiosHeaders, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';

const fake = vi.hoisted(() => ({config: {} as Record<string, unknown>}));

vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    instanceConfig: {
        get config() {
            return fake.config;
        },
    },
}));

import {ApiError, axiosInstance, zodiosApi} from '$lib/api';
import {readLinkSendFailure, sendByEmailVisible, sendLinkByEmail, tokenFromLink, type LinkSendFailure} from './sendLinkApi';

const ALIAS = 'send_link_api_v1_email_links_post';
const TOKEN = 'inv-Token_0123';
const BASE_CONFIG = {profile: 'selfhosted', accounts: {registration_mode: 'invite', registration_locked: false}};

const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

function axiosRefusal(status: number, data: unknown, config: InternalAxiosRequestConfig = REQUEST): AxiosError {
    const response: AxiosResponse = {status, statusText: '', headers: {'content-type': 'application/json'}, config, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, config, {}, response);
}

const CARRIERS: Array<{carrier: string; refuse: (status: number, body?: unknown) => unknown}> = [
    {carrier: 'an AxiosError, as the generated client rejects', refuse: (status, body) => axiosRefusal(status, body)},
    {carrier: 'an ApiError', refuse: (status, body) => new ApiError(status, '', body)},
];

/** Each refusal of `POST /email/links` (backend/app/api/v1/email.py), and what must be read of it. */
const REFUSALS: Array<{label: string; status: number; detail: Record<string, unknown>; failure: LinkSendFailure}> = [
    {label: '409 EMAIL_UNAVAILABLE', status: 409, detail: {error_code: 'EMAIL_UNAVAILABLE', problem: 'SMTP_PORT_INVALID', message: 'Email is off or cannot be used on this instance'}, failure: {errorCode: 'EMAIL_UNAVAILABLE'}},
    {label: '409 EMAIL_LINKS_UNAVAILABLE', status: 409, detail: {error_code: 'EMAIL_LINKS_UNAVAILABLE', problem: 'PUBLIC_URL_MISSING', message: 'Emails cannot carry links'}, failure: {errorCode: 'EMAIL_LINKS_UNAVAILABLE'}},
    {label: '409 EMAIL_LINK_INVALID', status: 409, detail: {error_code: 'EMAIL_LINK_INVALID', status: 'expired', message: 'The link is not a live link of that kind'}, failure: {errorCode: 'EMAIL_LINK_INVALID'}},
    {label: '409 EMAIL_ACCOUNT_INACTIVE', status: 409, detail: {error_code: 'EMAIL_ACCOUNT_INACTIVE', message: 'The account is not active'}, failure: {errorCode: 'EMAIL_ACCOUNT_INACTIVE'}},
    {label: '422 EMAIL_RECIPIENT_REQUIRED', status: 422, detail: {error_code: 'EMAIL_RECIPIENT_REQUIRED', message: 'The address to send the link to is missing or not allowed'}, failure: {errorCode: 'EMAIL_RECIPIENT_REQUIRED'}},
    {label: '422 EMAIL_RECIPIENT_NOT_ALLOWED', status: 422, detail: {error_code: 'EMAIL_RECIPIENT_NOT_ALLOWED', message: 'The address to send the link to is missing or not allowed'}, failure: {errorCode: 'EMAIL_RECIPIENT_NOT_ALLOWED'}},
    {label: '422 EMAIL_RECIPIENT_INVALID', status: 422, detail: {error_code: 'EMAIL_RECIPIENT_INVALID', message: 'The address to send the link to is not a single email address'}, failure: {errorCode: 'EMAIL_RECIPIENT_INVALID'}},
    {label: '429 EMAIL_RATE_LIMITED', status: 429, detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 1800, message: 'The hourly email limit of the instance is reached'}, failure: {errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 1800}},
    {label: '502 EMAIL_DELIVERY_FAILED', status: 502, detail: {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: 'AUTH_FAILED', message: 'The SMTP server did not take the message'}, failure: {errorCode: 'EMAIL_DELIVERY_FAILED', smtpCode: 'AUTH_FAILED'}},
];

afterEach(() => {
    vi.restoreAllMocks();
});

/** What FastAPI answers on its own, before the route runs, for a `to` that is not an email address (`EmailStr`): a list. */
const FASTAPI_INVALID_TO = {
    detail: [
        {
            type: 'value_error',
            loc: ['body', 'to'],
            msg: 'value is not a valid email address: An email address must have an @-sign.',
            input: 'not-an-address',
            ctx: {reason: 'An email address must have an @-sign.'},
        },
    ],
};

// =====================================================================================================================
describe('tokenFromLink — the token of the fragment', () => {
    it.each<{label: string; link: string; token: string | null}>([
        {label: 'an invitation link', link: `https://folio.example.com/invite#token=${TOKEN}`, token: TOKEN},
        {label: 'a reset link under a path prefix', link: `https://folio.example.com:8443/app/reset-password#token=${TOKEN}`, token: TOKEN},
        {label: 'a bare path', link: `/invite#token=${TOKEN}`, token: TOKEN},
        {label: 'other parameters around it', link: `https://folio.example.com/invite#lang=it&token=${TOKEN}&x=1`, token: TOKEN},
        {label: 'percent-encoded characters', link: 'https://folio.example.com/invite#token=abc%2Ddef%5Fghi', token: 'abc-def_ghi'},
        {label: 'two tokens: the first', link: 'https://folio.example.com/invite#token=first&token=second', token: 'first'},
        {label: 'no fragment', link: 'https://folio.example.com/invite', token: null},
        {label: 'a token in the query only, never read', link: `https://folio.example.com/invite?token=${TOKEN}`, token: null},
        {label: 'a fragment without a token', link: 'https://folio.example.com/invite#lang=it', token: null},
        {label: 'an empty token', link: 'https://folio.example.com/invite#token=', token: null},
        {label: 'a token without a value', link: 'https://folio.example.com/invite#token', token: null},
        {label: 'an empty fragment', link: 'https://folio.example.com/invite#', token: null},
    ])('SLA-01: $label', ({link, token}) => {
        expect(tokenFromLink(link)).toBe(token);
    });
});

// =====================================================================================================================
describe('sendByEmailVisible — only when emails with a link can go out', () => {
    it.each<{label: string; email: unknown; visible: boolean}>([
        {label: 'no email part (an older server)', email: undefined, visible: false},
        {label: 'email unavailable', email: {available: false, links: false}, visible: false},
        {label: 'email available, links not', email: {available: true, links: false}, visible: false},
        {label: 'links ready', email: {available: true, links: true}, visible: true},
        {label: 'links said as text', email: {available: true, links: 'true'}, visible: false},
        {label: 'an email part that is not an object', email: null, visible: false},
    ])('SLA-02: $label → $visible', ({email, visible}) => {
        fake.config = email === undefined ? {...BASE_CONFIG} : {...BASE_CONFIG, email};

        expect(sendByEmailVisible()).toBe(visible);
    });
});

// =====================================================================================================================
describe('sendLinkByEmail — through its alias', () => {
    const ANSWER = {purpose: 'invite' as const, to: 'zq-guest@example.com', language: 'it' as const};

    it.each<{label: string; request: Parameters<typeof sendLinkByEmail>[0]; body: Record<string, unknown>}>([
        {label: 'an invitation to an address', request: {purpose: 'invite', token: TOKEN, to: 'zq-guest@example.com'}, body: {purpose: 'invite', token: TOKEN, to: 'zq-guest@example.com'}},
        {label: 'an invitation without an address', request: {purpose: 'invite', token: TOKEN}, body: {purpose: 'invite', token: TOKEN}},
        {label: 'an invitation with an empty address', request: {purpose: 'invite', token: TOKEN, to: ''}, body: {purpose: 'invite', token: TOKEN}},
        {label: 'a reset link', request: {purpose: 'password_reset', token: TOKEN}, body: {purpose: 'password_reset', token: TOKEN}},
    ])('SLA-03: $label — posts exactly its body, once', async ({request, body}) => {
        const alias = vi.spyOn(zodiosApi, ALIAS).mockResolvedValueOnce(ANSWER);

        await sendLinkByEmail(request);

        expect(alias).toHaveBeenCalledTimes(1);
        expect(alias.mock.calls[0][0]).toStrictEqual(body);
    });

    it('SLA-04: answers {to, language} alone, and a refusal reaches the caller as raised', async () => {
        vi.spyOn(zodiosApi, ALIAS).mockResolvedValueOnce(ANSWER);
        await expect(sendLinkByEmail({purpose: 'invite', token: TOKEN})).resolves.toStrictEqual({to: 'zq-guest@example.com', language: 'it'});

        const refusal = axiosRefusal(409, {detail: {error_code: 'EMAIL_LINK_INVALID', status: 'expired'}});
        vi.spyOn(zodiosApi, ALIAS).mockRejectedValueOnce(refusal);
        await expect(sendLinkByEmail({purpose: 'invite', token: TOKEN})).rejects.toBe(refusal);
    });

    it.each<{label: string; request: Parameters<typeof sendLinkByEmail>[0]; body: Record<string, unknown>}>([
        {
            label: 'an invitation to an address, in a language',
            request: {purpose: 'invite', token: TOKEN, to: 'zq-guest@example.com', language: 'it'},
            body: {purpose: 'invite', token: TOKEN, to: 'zq-guest@example.com', language: 'it'},
        },
        {label: 'an invitation in a language, without an address', request: {purpose: 'invite', token: TOKEN, language: 'fr'}, body: {purpose: 'invite', token: TOKEN, language: 'fr'}},
        {label: 'an invitation in a language, with an empty address', request: {purpose: 'invite', token: TOKEN, to: '', language: 'es'}, body: {purpose: 'invite', token: TOKEN, language: 'es'}},
        {
            label: 'an invitation whose language is undefined: no language key',
            request: {purpose: 'invite', token: TOKEN, to: 'zq-guest@example.com', language: undefined},
            body: {purpose: 'invite', token: TOKEN, to: 'zq-guest@example.com'},
        },
    ])('SLA-15: $label — posts exactly its body, language only when one is given, once', async ({request, body}) => {
        const alias = vi.spyOn(zodiosApi, ALIAS).mockResolvedValueOnce(ANSWER);

        await sendLinkByEmail(request);

        expect(alias).toHaveBeenCalledTimes(1);
        expect(alias.mock.calls[0][0]).toStrictEqual(body);
    });
});

// =====================================================================================================================
describe.each(CARRIERS)('readLinkSendFailure — a refusal carried by $carrier', ({refuse}) => {
    it.each(REFUSALS)('SLA-05: $label', ({status, detail, failure}) => {
        expect(readLinkSendFailure(refuse(status, {detail}))).toEqual(failure);
    });

    it.each<{label: string; detail: Record<string, unknown>; failure: LinkSendFailure}>([
        {label: 'an smtp_code that is not text', detail: {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: 7}, failure: {errorCode: 'EMAIL_DELIVERY_FAILED'}},
        {label: 'an empty smtp_code', detail: {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: ''}, failure: {errorCode: 'EMAIL_DELIVERY_FAILED'}},
        {label: 'a retry_after that is text', detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: '1800'}, failure: {errorCode: 'EMAIL_RATE_LIMITED'}},
        {label: 'a retry_after that is not finite', detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: Number.POSITIVE_INFINITY}, failure: {errorCode: 'EMAIL_RATE_LIMITED'}},
        {label: 'no error_code', detail: {message: 'no code'}, failure: {errorCode: 'UNKNOWN'}},
        {label: 'an empty error_code', detail: {error_code: ''}, failure: {errorCode: 'UNKNOWN'}},
    ])('SLA-06: $label is left out', ({detail, failure}) => {
        const read = readLinkSendFailure(refuse(409, {detail}));

        expect(read).toEqual(failure);
        expect(read.smtpCode).toBeUndefined();
        expect(read.retryAfter).toBeUndefined();
    });

    it.each<{label: string; status: number; body: unknown}>([
        {label: 'a plain-text detail', status: 403, body: {detail: 'Admin privileges required'}},
        {label: 'no detail', status: 500, body: {}},
        {label: 'no body', status: 503, body: undefined},
        {label: 'a validation list with another status than 422', status: 400, body: {detail: [{loc: ['body', 'to'], msg: 'invalid', type: 'value_error'}]}},
    ])('SLA-07: $label is UNKNOWN', ({status, body}) => {
        expect(readLinkSendFailure(refuse(status, body))).toStrictEqual({errorCode: 'UNKNOWN'});
    });

    it.each<{label: string; body: unknown}>([
        {label: 'FastAPI’s validation list for a to that is not an email address', body: FASTAPI_INVALID_TO},
        {label: 'a plain-text detail', body: {detail: 'Unprocessable'}},
        {label: 'no body', body: undefined},
    ])('SLA-12: a 422 without a detail object — $label — is EMAIL_RECIPIENT_INVALID', ({body}) => {
        expect(readLinkSendFailure(refuse(422, body))).toStrictEqual({errorCode: 'EMAIL_RECIPIENT_INVALID'});
    });

    it('SLA-12: a 422 with a detail object keeps what it says: its code, or UNKNOWN without one', () => {
        expect(readLinkSendFailure(refuse(422, {detail: {error_code: 'EMAIL_RECIPIENT_NOT_ALLOWED'}}))).toEqual({errorCode: 'EMAIL_RECIPIENT_NOT_ALLOWED'});
        expect(readLinkSendFailure(refuse(422, {detail: {message: 'no code'}}))).toEqual({errorCode: 'UNKNOWN'});
    });
});

describe('readLinkSendFailure — what carries no answer is UNKNOWN', () => {
    it.each<{label: string; make: () => unknown}>([
        {label: 'a request that reached no server', make: () => new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {})},
        {label: 'a plain Error', make: () => new Error('boom')},
        {label: 'undefined', make: () => undefined},
    ])('SLA-08: $label', ({make}) => {
        expect(readLinkSendFailure(make())).toStrictEqual({errorCode: 'UNKNOWN'});
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
            if (status >= 200 && status < 300) return {status, statusText: 'OK', headers: {'content-type': 'application/json'}, config, request: {}, data};
            throw axiosRefusal(status, data, config);
        };
        axiosInstance.defaults.adapter = adapter;
    }

    function sentBody(): unknown {
        const data = received[0]?.data;
        return typeof data === 'string' ? JSON.parse(data) : data;
    }

    it('SLA-09: an invitation to an address reaches POST /api/v1/email/links with {purpose, token, to}, and {to, language} comes back', async () => {
        serverAnswers(200, {purpose: 'invite', to: 'zq-guest@example.com', language: 'fr'});

        await expect(sendLinkByEmail({purpose: 'invite', token: TOKEN, to: 'zq-guest@example.com'})).resolves.toStrictEqual({to: 'zq-guest@example.com', language: 'fr'});
        expect(received.map(({method, url}) => `${method} ${url}`)).toEqual(['post /api/v1/email/links']);
        expect(sentBody()).toStrictEqual({purpose: 'invite', token: TOKEN, to: 'zq-guest@example.com'});
    });

    it('SLA-10: a reset link reaches the transport without a to', async () => {
        serverAnswers(200, {purpose: 'password_reset', to: 'zq-alice@example.com', language: 'en'});

        await expect(sendLinkByEmail({purpose: 'password_reset', token: TOKEN})).resolves.toStrictEqual({to: 'zq-alice@example.com', language: 'en'});
        expect(sentBody()).toStrictEqual({purpose: 'password_reset', token: TOKEN});
    });

    it.each<{label: string; request: Parameters<typeof sendLinkByEmail>[0]; body: Record<string, unknown>; answer: {purpose: 'invite'; to: string; language: string}}>([
        {
            label: 'an invitation to an address in Italiano: {purpose, token, to, language}',
            request: {purpose: 'invite', token: TOKEN, to: 'zq-guest@example.com', language: 'it'},
            body: {purpose: 'invite', token: TOKEN, to: 'zq-guest@example.com', language: 'it'},
            answer: {purpose: 'invite', to: 'zq-guest@example.com', language: 'it'},
        },
        {
            label: 'an invitation in Español without an address: {purpose, token, language}; written in Français, the answer’s language comes back',
            request: {purpose: 'invite', token: TOKEN, language: 'es'},
            body: {purpose: 'invite', token: TOKEN, language: 'es'},
            answer: {purpose: 'invite', to: 'zq-written-in-the-invitation@example.com', language: 'fr'},
        },
    ])('SLA-16: $label', async ({request, body, answer}) => {
        serverAnswers(200, answer);

        await expect(sendLinkByEmail(request)).resolves.toStrictEqual({to: answer.to, language: answer.language});
        expect(received.map(({method, url}) => `${method} ${url}`)).toEqual(['post /api/v1/email/links']);
        expect(sentBody(), 'exactly that body: the language asked for, the address only when given').toStrictEqual(body);
    });

    it.each(REFUSALS)('SLA-11: $label, as the client raises it, is read', async ({status, detail, failure}) => {
        serverAnswers(status, {detail});

        const read = await sendLinkByEmail({purpose: 'invite', token: TOKEN}).then(() => null, readLinkSendFailure);

        expect(received, 'premise: the request reached the transport').toHaveLength(1);
        expect(read).toEqual(failure);
    });

    it('SLA-13: FastAPI’s own 422 for a to that is not an email address, as the client raises it, is EMAIL_RECIPIENT_INVALID', async () => {
        serverAnswers(422, FASTAPI_INVALID_TO);

        const read = await sendLinkByEmail({purpose: 'invite', token: TOKEN, to: 'not-an-address'}).then(() => null, readLinkSendFailure);

        expect(sentBody(), 'premise: the address went as typed, and the server refused it').toStrictEqual({purpose: 'invite', token: TOKEN, to: 'not-an-address'});
        expect(read).toStrictEqual({errorCode: 'EMAIL_RECIPIENT_INVALID'});
    });

    it('SLA-14: a request that reaches no server stays UNKNOWN', async () => {
        axiosInstance.defaults.adapter = async (config) => {
            received.push(config);
            throw new AxiosError('Network Error', AxiosError.ERR_NETWORK, config, {});
        };

        await expect(sendLinkByEmail({purpose: 'invite', token: TOKEN, to: 'not-an-address'}).then(() => null, readLinkSendFailure)).resolves.toStrictEqual({errorCode: 'UNKNOWN'});
    });
});
