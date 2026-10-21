// @vitest-environment node
/**
 * requestIdMessage — the error code in a message the user sees (lot H-60r, workstream H: contract §4, decision D3).
 *
 * H-60 writes a server line for every 5xx, under the request id its answer carries (`X-Request-Id`, and `request_id` in
 * the body). A user who reports «it failed» gives the administrator nothing to search for; a user who reports the code
 * gives the line. This file pins the one shared helper that puts that code at the end of a generic failure message,
 * which J (AI Export, risk, lots), X (the PAC) and A then apply to their own surfaces.
 *
 * The contract under test — `src/lib/api/requestIdMessage.ts`, new:
 *
 *   - `withRequestId(t, message, error)` returns `t(REQUEST_ID_MESSAGE_KEY, {values: {message, requestId}})` when
 *     `error` holds a failed HTTP answer that is a 5xx with a request id; otherwise `message` as it is, without calling
 *     `t`. It never throws, whatever `error` is.
 *   - The failed answer: the `response` of `error`, or of the first object reached through `originalError` (the AI
 *     Export client's errors) or `cause` (the standard Error cause), step by step, at most 8 steps, never the same
 *     object twice. Read here as: the answer may be 8 steps away from `error`, not 9. The id: `requestIdOf` of the object
 *     holding the answer (`apiErrorConsole.ts`, unchanged): the `X-Request-Id` header, else the body's `request_id`,
 *     and only a valid id.
 *   - Only a 5xx: its id is always in the server log. A 4xx writes no server line, a network failure has no answer, a
 *     5xx from a proxy carries no LibreFolio id.
 *   - `REQUEST_ID_MESSAGE_KEY = 'common.errorWithRequestId'`, in `base`, four languages: the message whole, then the
 *     code in parentheses, at the end, on the same line.
 *   - `type RequestIdTranslate = (key, options?: {values?: Record<string, string>}) => string`: svelte-i18n's
 *     `$_`/`get(_)`, `AiExportTranslate` and the `Translate` aliases of `lib/api/` are all assignable to it.
 *
 * How. `t` is a recording `vi.fn` that answers a sentinel: a composed message is that sentinel, returned as it is, after
 * exactly one call naming the key, the message and the id. Failures are shaped as axios raises them — an `AxiosError`
 * carrying its request and its response, the headers an `AxiosHeaders` instance or a plain object — and the wrappers
 * are the real ones: `new Error(…, {cause})`, the AI Export client's classes, a request axios itself canceled, the
 * `ZodiosError` class. The catalogue cases read the generated catalogues as `src/lib/i18n/catalogIcuLocale.test.ts`
 * does, and format with intl-messageformat as the app runs it (svelte-i18n's class, read from one of its formatters):
 * structure, never wording. The type-level case is proven by `front check`: each translator is passed and assigned as
 * its surface types it, with no cast, and every call in this file is typed against the real module.
 *
 * Barriers. «The message as it is, `t` never called» means something only if the same `t` records and the module does
 * compose: each negative case first composes a 503 through the same `t`, and where the status is what must keep the
 * message, a premise shows the id itself was readable (`requestIdOf`).
 *
 * Not pinned, the contract leaves them open: a status of 600 or more, or not an integer; an object holding both `cause`
 * and `originalError`; an outer answer that is no 5xx in front of an inner one that is; a 5xx holder that is no Axios
 * error (a bare `{response}`); a header that is no valid id while the body holds one (`requestIdOf`'s own); a `t` that
 * throws.
 *
 * Red today: `requestIdMessage.ts` does not exist — each case loads it by a computed specifier and fails on its own,
 * with that in its message — and no generated catalogue holds `common.errorWithRequestId`, so the catalogue cases fail
 * on their line. `front check` fails on the type import until the module exists. Its place in the runner:
 * `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import axios, {AxiosError, AxiosHeaders, isCancel, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {ZodiosError} from '@zodios/core';
import {z} from 'zod';
import {_, getMessageFormatter} from 'svelte-i18n';
import {get, type Readable} from 'svelte/store';
import {describe, expect, it, vi} from 'vitest';
import {AiExportNetworkError, AiExportProblemError, AiExportUnknownError, AiExportValidationError, type AiExportProblemDetail} from '$lib/features/ai-export/aiExportClient';
import type {AiExportTranslate} from '$lib/features/ai-export/ui';
import type {SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {requestIdOf} from './apiErrorConsole';
import type {bulkRefusalMessage} from './bulkRefusal';
import type * as RequestIdMessage from './requestIdMessage';
import type {writeRefusalMessage} from './writeRefusal';

// =============================================================================
//  The module under test
// =============================================================================

/** `src/lib/api/requestIdMessage.ts` as `front check` types it: every call below is checked against its signature. */
type RequestIdMessageModule = typeof RequestIdMessage;
type WithRequestId = RequestIdMessageModule['withRequestId'];
type RequestIdTranslate = RequestIdMessage.RequestIdTranslate;

/** A computed specifier: Vite does not resolve it when it transforms this file, so while the module is missing each case fails on its own. */
const MODULE = './requestIdMessage';

/** The module, loaded by the running case. */
async function requestIdMessage(): Promise<RequestIdMessageModule> {
    let loaded: Record<string, unknown>;
    try {
        loaded = (await import(/* @vite-ignore */ MODULE)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`src/lib/api/requestIdMessage.ts cannot be loaded (red until H-60r §4: it does not exist yet), so no message carries the error code — ${String(error)}`, {cause: error});
    }
    expect(typeof loaded.withRequestId, 'requestIdMessage.ts exports no withRequestId()').toBe('function');
    return loaded as unknown as RequestIdMessageModule;
}

// =============================================================================
//  What the cases pass, and what they expect of t
// =============================================================================

/** The key the contract names, written once: the module exports it, the catalogues hold it. */
const KEY = 'common.errorWithRequestId';

/** Ids as the backend mints them (`secrets.token_hex(8)`): 16 lowercase hex characters. */
const REQUEST_ID = '5f2b9c0e7d1a4386';
const BODY_REQUEST_ID = 'b04c6e2f9a7d1358';

/** The surface's own message, as a caller passes it: an apostrophe and braces, which reach `t` untouched. */
const MESSAGE = "The surface's own message, {whole}.";

/** What the recording `t` answers: a composed message is this, returned as it is. */
const COMPOSED = '‹composed by t›';

/** The calls `t` gets when the message gets its code: one, with the key, the message whole and the id. */
const askedFor = (requestId: string): unknown[][] => [[KEY, {values: {message: MESSAGE, requestId}}]];

/** A recording `t`, typed as the helper takes it. */
function recordingTranslate() {
    return vi.fn<RequestIdTranslate>(() => COMPOSED);
}

type RecordingTranslate = ReturnType<typeof recordingTranslate>;

/**
 * Barrier before a negative: through the same `t`, a 503 whose `X-Request-Id` is REQUEST_ID is composed. A «message as
 * it is, `t` never called» that follows is then the helper's verdict, not a module that composes nothing or a `t` that
 * records nothing. The barrier's call is forgotten.
 */
function expectComposesA503(withRequestId: WithRequestId, t: RecordingTranslate): void {
    expect(withRequestId(t, MESSAGE, serverError()), 'Barrier: a 503 with an id is composed').toBe(COMPOSED);
    expect(t.mock.calls, 'Barrier: t was asked once, for its id').toEqual(askedFor(REQUEST_ID));
    t.mockClear();
}

/** `withRequestId(t, MESSAGE, error)` returns — it never throws — and returns MESSAGE as it is. */
function expectMessageKept(withRequestId: WithRequestId, t: RecordingTranslate, error: unknown, label: string): void {
    let result: unknown;
    try {
        result = withRequestId(t, MESSAGE, error);
    } catch (thrown) {
        throw new Error(`${label}: withRequestId threw, and it must never throw — ${String(thrown)}`, {cause: thrown});
    }
    expect(result, `${label}: the message, as it is`).toBe(MESSAGE);
}

// =============================================================================
//  Failures, as axios raises them
// =============================================================================

/** The request a failure was, as axios keeps it on the error. */
function sentRequest(): InternalAxiosRequestConfig {
    return {method: 'post', url: '/api/v1/ai-export/snapshot', headers: AxiosHeaders.from({'Content-Type': 'application/json'})} as InternalAxiosRequestConfig;
}

type ResponseHeaders = AxiosHeaders | Record<string, string>;

/** Response headers as axios hands them over, an `AxiosHeaders` instance; with `X-Request-Id` when an id is given. */
function headersWith(requestId?: string): AxiosHeaders {
    return AxiosHeaders.from(requestId === undefined ? {'content-type': 'application/json'} : {'content-type': 'application/json', 'X-Request-Id': requestId});
}

/** The same headers as a plain object, their names in lower case as axios normalises them. */
function plainHeadersWith(requestId: string): Record<string, string> {
    return {'content-type': 'application/json', 'x-request-id': requestId};
}

/** A failed answer as axios raises it: an `AxiosError` carrying its request and its response. `status` is unknown so that a case can break it. */
function answered(status: unknown, body: unknown, headers: ResponseHeaders = headersWith()): AxiosError {
    const config = sentRequest();
    const response = {status, statusText: String(status), headers, config, request: {}, data: body} as unknown as AxiosResponse;
    const code = typeof status === 'number' && status >= 500 ? AxiosError.ERR_BAD_RESPONSE : AxiosError.ERR_BAD_REQUEST;
    return new AxiosError(`Request failed with status code ${String(status)}`, code, config, {}, response);
}

/** A 5xx body as the backend writes it, without its id: where a case uses it, the header alone carries the id. */
const SERVER_BODY = {detail: 'Internal Server Error', error_type: 'KeyError'};

/** A 503 whose `X-Request-Id` is REQUEST_ID. */
function serverError(): AxiosError {
    return answered(503, SERVER_BODY, headersWith(REQUEST_ID));
}

/** A request nothing answered, with Axios's code: a network failure, a timeout. */
function unanswered(code: string): AxiosError {
    return new AxiosError(`Request failed: ${code}`, code, sentRequest(), {});
}

/** The rejection of `pending`; the case fails if it resolves. */
async function rejection(pending: Promise<unknown>): Promise<unknown> {
    try {
        await pending;
    } catch (error) {
        return error;
    }
    throw new Error('premise: this call was meant to fail, and it succeeded');
}

/** What axios raises for a request its AbortController canceled before it left: a CanceledError, `ERR_CANCELED`, no response. */
function canceledRequest(): Promise<unknown> {
    const controller = new AbortController();
    controller.abort();
    const transport: AxiosAdapter = () => Promise.reject(new Error('premise: a canceled request never reaches the transport'));
    return rejection(axios.create().get('/api/v1/assets', {signal: controller.signal, adapter: transport}));
}

/** A 200 whose body broke its schema, as Zodios refuses it: a `ZodiosError` holding the body and the `ZodError`, and no answer. Its body holds a `request_id`, which is no failed answer's. */
function schemaMismatch(): ZodiosError {
    const body = {profile: 'unknown', request_id: REQUEST_ID};
    const refusal = new ZodiosError('Zodios: Invalid response from endpoint', {method: 'get', url: '/api/v1/system/instance'}, body, z.object({profile: z.enum(['selfhosted', 'managed'])}).safeParse(body).error);
    expect('response' in refusal, 'premise: a ZodiosError holds no answer object').toBe(false);
    return refusal;
}

/** The same refusal, as the AI Export client wraps it (`normalizeAiExportClientError`). */
function wrappedSchemaMismatch(): AiExportValidationError {
    const refusal = schemaMismatch();
    return new AiExportValidationError('response', undefined, refusal, refusal);
}

/** The detail of the AI Export 503, as the client keeps it in an `AiExportProblemError`. */
const SNAPSHOT_PROBLEM: AiExportProblemDetail = {
    code: 'snapshot_source_failure',
    message: 'A source of the snapshot failed',
    domain: 'portfolio',
    selection_kind: 'dataset',
    selection_id: 'portfolio.overview',
    detail_level: 'standard',
    component_id: 'portfolio.technical_prices',
    retryable: true,
};

/** `answer` bare, and behind each kind of wrapper. */
function bareAndWrapped(answer: AxiosError): Array<[label: string, error: unknown]> {
    return [
        ['bare', answer],
        ["as an Error's cause", new Error('wrapped', {cause: answer})],
        ['as an originalError', {originalError: answer}],
    ];
}

/** `answer` behind `steps` wrappers, from the answer outwards: an Error's `cause`, then an object's `originalError`, and so on. */
function behind(answer: unknown, steps: number): unknown {
    let error = answer;
    for (let step = 1; step <= steps; step++) error = step % 2 === 1 ? new Error(`wrapper ${step}`, {cause: error}) : {originalError: error};
    return error;
}

/** An object whose `name` getter throws: reading it is the failure. */
function throwingOn(name: string): object {
    return Object.defineProperty({}, name, {
        enumerable: true,
        get(): never {
            throw new Error(`hostile ${name}`);
        },
    });
}

// =============================================================================
//  The generated catalogues
// =============================================================================

/** The leaf behind a dotted key in one catalogue. */
function leaf(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** How many times `part` occurs in `text`. */
function occurrences(text: string, part: string): number {
    return text.split(part).length - 1;
}

type RuntimeFormatter = ReturnType<typeof getMessageFormatter>;
type RuntimeFormatterClass = new (message: string, locales?: string, overrideFormats?: undefined, options?: {ignoreTag?: boolean}) => RuntimeFormatter;

/** The class svelte-i18n compiles a message with — intl-messageformat, the copy the app runs — read from one of its formatters rather than imported beside it. */
function runtimeMessageFormat(): RuntimeFormatterClass {
    return getMessageFormatter('text').constructor as unknown as RuntimeFormatterClass;
}

// =============================================================================
//  The translators the surfaces hold
// =============================================================================

/** svelte-i18n's formatter, the value of its `_` store: `$_` in a component, `get(_)` in a module. The library does not export its type by name. */
type SvelteI18nFormatter = typeof _ extends Readable<infer Formatter> ? Formatter : never;
/** The `Translate` aliases of `lib/api/`, read from the functions that take them: neither module exports its alias. */
type BulkRefusalTranslate = Parameters<typeof bulkRefusalMessage>[1];
type WriteRefusalTranslate = Parameters<typeof writeRefusalMessage>[1];

// =============================================================================
//  The cases
// =============================================================================

describe('withRequestId — a 5xx with its request id: the code follows the message', () => {
    // red until H-60r §4: the module does not exist
    it('exports REQUEST_ID_MESSAGE_KEY, the key the catalogues hold: common.errorWithRequestId', async () => {
        const {REQUEST_ID_MESSAGE_KEY} = await requestIdMessage();

        expect(REQUEST_ID_MESSAGE_KEY).toBe(KEY);
    });

    const WITH_A_HEADER: Array<[status: number, shape: string, headers: (requestId: string) => ResponseHeaders]> = [
        [500, 'an AxiosHeaders instance', headersWith],
        [500, 'a plain object', plainHeadersWith],
        [503, 'an AxiosHeaders instance', headersWith],
        [503, 'a plain object', plainHeadersWith],
    ];

    // red until H-60r §4
    it.each(WITH_A_HEADER)('returns t(common.errorWithRequestId, {values: {message, requestId}}) for a %i whose X-Request-Id comes in %s', async (status, _shape, headers) => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        const failure = answered(status, SERVER_BODY, headers(REQUEST_ID));
        expect(requestIdOf(failure), 'premise: requestIdOf reads the id from the header').toBe(REQUEST_ID);

        expect(withRequestId(t, MESSAGE, failure), 'what t composed, as it is').toBe(COMPOSED);
        expect(t.mock.calls, 'one call: the key, the message whole, the id').toEqual(askedFor(REQUEST_ID));
    });

    // red until H-60r §4
    it("uses the body's request_id when no header carries one", async () => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        const failure = answered(500, {...SERVER_BODY, request_id: BODY_REQUEST_ID});
        expect(requestIdOf(failure), 'premise: no header, the id in the body').toBe(BODY_REQUEST_ID);

        expect(withRequestId(t, MESSAGE, failure), 'what t composed, as it is').toBe(COMPOSED);
        expect(t.mock.calls, "the body's id").toEqual(askedFor(BODY_REQUEST_ID));
    });

    // red until H-60r §4
    it("prefers the X-Request-Id header to the body's request_id", async () => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();

        expect(withRequestId(t, MESSAGE, answered(503, {...SERVER_BODY, request_id: BODY_REQUEST_ID}, headersWith(REQUEST_ID))), 'what t composed, as it is').toBe(COMPOSED);
        expect(t.mock.calls, "the header's id, not the body's").toEqual(askedFor(REQUEST_ID));
    });
});

describe('withRequestId — only a 5xx carries the code', () => {
    // red until H-60r §4
    it.each([400, 401, 404, 409, 422])('keeps the message of a %i with a valid id, bare or wrapped, and never asks t', async (status) => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        expectComposesA503(withRequestId, t);
        const failure = answered(status, {detail: {code: 'asset_not_found'}, request_id: REQUEST_ID}, headersWith(REQUEST_ID));
        expect(requestIdOf(failure), 'premise: the 4xx carries an id requestIdOf reads').toBe(REQUEST_ID);

        for (const [label, error] of bareAndWrapped(failure)) expectMessageKept(withRequestId, t, error, `a ${status} ${label}`);
        expect(t, 'a 4xx: t is never asked').not.toHaveBeenCalled();
    });

    // red until H-60r §4
    it.each([500, 502, 503, 504])('composes a %i with an id', async (status) => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();

        expect(withRequestId(t, MESSAGE, answered(status, SERVER_BODY, headersWith(REQUEST_ID))), 'what t composed, as it is').toBe(COMPOSED);
        expect(t.mock.calls, 'one call: the key, the message whole, the id').toEqual(askedFor(REQUEST_ID));
    });

    // red until H-60r §4
    it('keeps the message of a 5xx without any id: a page from a proxy, a body without request_id', async () => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        expectComposesA503(withRequestId, t);
        const proxyPage = answered(502, '<html><body>502 Bad Gateway</body></html>', AxiosHeaders.from({'content-type': 'text/html'}));
        const noId = answered(500, SERVER_BODY);
        expect(requestIdOf(proxyPage), 'premise: no id in the page of the proxy').toBeNull();
        expect(requestIdOf(noId), 'premise: no id in a header nor in the body').toBeNull();

        expectMessageKept(withRequestId, t, proxyPage, 'a 502 page from a proxy');
        expectMessageKept(withRequestId, t, noId, 'a 500 without an id');
        expect(t, 'no id: t is never asked').not.toHaveBeenCalled();
    });
});

describe('withRequestId — the answer behind a wrapper: cause and originalError', () => {
    const WRAPPERS: Array<[label: string, status: number, wrap: (answer: AxiosError) => unknown]> = [
        ["an Error's cause", 503, (answer) => new Error('The export failed', {cause: answer})],
        ['a plain object, as its originalError', 503, (answer) => ({originalError: answer})],
        ['two levels: a cause, then an originalError', 503, (answer) => new Error('The page failed', {cause: {originalError: answer}})],
        ['two levels: an originalError, then a cause', 503, (answer) => ({originalError: new Error('The load failed', {cause: answer})})],
        ['AiExportProblemError(503, problem, answer), as the AI Export client raises it', 503, (answer) => new AiExportProblemError(503, SNAPSHOT_PROBLEM, answer)],
        ["AiExportUnknownError('m', 500, answer), as the AI Export client raises it", 500, (answer) => new AiExportUnknownError('m', 500, answer)],
    ];

    // red until H-60r §4
    it.each(WRAPPERS)('finds the answer and its id behind %s', async (_label, status, wrap) => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        const answer = answered(status, SERVER_BODY, headersWith(REQUEST_ID));

        expect(withRequestId(t, MESSAGE, wrap(answer)), 'what t composed, as it is').toBe(COMPOSED);
        expect(t.mock.calls, 'the id of the answer behind the wrapper').toEqual(askedFor(REQUEST_ID));
    });

    // red until H-60r §4 — «at most 8 steps», read as: the answer may be 8 steps away from the error passed, not 9
    it('reads the answer up to 8 steps away, at each depth from 1 to 8', async () => {
        const {withRequestId} = await requestIdMessage();

        for (let steps = 1; steps <= 8; steps++) {
            const t = recordingTranslate();
            expect(withRequestId(t, MESSAGE, behind(serverError(), steps)), `the answer ${steps} steps away`).toBe(COMPOSED);
            expect(t.mock.calls, `${steps} steps away: the id of the answer`).toEqual(askedFor(REQUEST_ID));
        }
    });

    // red until H-60r §4
    it('keeps the message when the answer is more than 8 steps away: 9, and 20', async () => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        expect(withRequestId(t, MESSAGE, behind(serverError(), 7)), 'Barrier: 7 steps away, the walk reaches the answer').toBe(COMPOSED);
        expect(t.mock.calls, 'Barrier: and its id').toEqual(askedFor(REQUEST_ID));
        t.mockClear();

        expectMessageKept(withRequestId, t, behind(serverError(), 9), 'the answer 9 steps away');
        expectMessageKept(withRequestId, t, behind(serverError(), 20), 'the answer 20 steps away');
        expect(t, 'too far: t is never asked').not.toHaveBeenCalled();
    });

    // red until H-60r §4
    it('keeps the message for a cycle, and returns: a.cause = b and b.cause = a, an object its own originalError, two Errors each the cause of the other', async () => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        expectComposesA503(withRequestId, t);
        const a: {cause?: unknown} = {};
        const b: {cause?: unknown} = {cause: a};
        a.cause = b;
        const itself: {originalError?: unknown} = {};
        itself.originalError = itself;
        const first = new Error('first');
        const second = new Error('second', {cause: first});
        first.cause = second;
        const mixed: {originalError?: unknown} = {};
        mixed.originalError = new Error('mixed', {cause: mixed});

        expectMessageKept(withRequestId, t, a, 'a.cause = b, b.cause = a');
        expectMessageKept(withRequestId, t, itself, 'an object that is its own originalError');
        expectMessageKept(withRequestId, t, first, 'two Errors, each the cause of the other');
        expectMessageKept(withRequestId, t, mixed, 'an originalError whose cause leads back');
        expect(t, 'no answer in a cycle: t is never asked').not.toHaveBeenCalled();
    });
});

describe('withRequestId — never throws; without a 5xx and its id, the message as it is', () => {
    const NO_CODE: Array<[label: string, error: () => unknown]> = [
        ['null', () => null],
        ['undefined', () => undefined],
        ['a string', () => 'Request failed with status code 503'],
        ['a string that is an id', () => REQUEST_ID],
        ['a number', () => 503],
        ['a symbol', () => Symbol(REQUEST_ID)],
        ['an Error', () => new Error('x')],
        ['an Error whose message names a 503', () => new Error('Request failed with status code 503')],
        ['an object with a status and an id but no response', () => ({status: 503, request_id: REQUEST_ID, headers: plainHeadersWith(REQUEST_ID)})],
        ['a response that is not an object', () => ({response: 503})],
        ['an Axios network error: nothing answered', () => unanswered(AxiosError.ERR_NETWORK)],
        ['an Axios timeout: nothing answered', () => unanswered(AxiosError.ECONNABORTED)],
        ['a network error, as the AI Export client wraps it', () => new AiExportNetworkError('Network Error', AxiosError.ERR_NETWORK, unanswered(AxiosError.ERR_NETWORK))],
        ['an AiExportProblemError(503) that kept no original error', () => new AiExportProblemError(503, SNAPSHOT_PROBLEM, null)],
        ['a ZodiosError: a 200 that broke its schema, no answer object', schemaMismatch],
        ['a ZodiosError, as the AI Export client wraps it', wrappedSchemaMismatch],
    ];

    // red until H-60r §4
    it.each(NO_CODE)('keeps the message for %s, and never asks t', async (label, make) => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        expectComposesA503(withRequestId, t);

        expectMessageKept(withRequestId, t, make(), label);
        expect(t, `${label}: t is never asked`).not.toHaveBeenCalled();
    });

    // red until H-60r §4
    it('keeps the message for a request axios canceled', async () => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        expectComposesA503(withRequestId, t);
        const canceled = await canceledRequest();
        expect(isCancel(canceled), 'premise: axios rejected the request as canceled').toBe(true);
        expect((canceled as AxiosError).response, 'premise: nothing answered').toBeUndefined();

        expectMessageKept(withRequestId, t, canceled, 'a canceled request');
        expect(t, 'a canceled request: t is never asked').not.toHaveBeenCalled();
    });

    const INVALID_IDS: Array<[label: string, requestId: string]> = [
        ['a space', '5f2b9c0e 7d1a4386'],
        ['65 characters', 'f'.repeat(65)],
    ];

    // red until H-60r §4
    it.each(INVALID_IDS)('keeps the message of a 503 whose only id has %s, in the header or in the body: requestIdOf takes no such id', async (label, requestId) => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        const longest = 'f'.repeat(64);
        expect(withRequestId(t, MESSAGE, answered(503, SERVER_BODY, headersWith(longest))), 'Barrier: 64 characters make an id').toBe(COMPOSED);
        expect(t.mock.calls, 'Barrier: composed with it').toEqual(askedFor(longest));
        t.mockClear();
        const inHeader = answered(503, SERVER_BODY, headersWith(requestId));
        const inBody = answered(503, {...SERVER_BODY, request_id: requestId});
        expect([requestIdOf(inHeader), requestIdOf(inBody)], 'premise: requestIdOf reads no id').toEqual([null, null]);

        expectMessageKept(withRequestId, t, inHeader, `an id with ${label}, in the header`);
        expectMessageKept(withRequestId, t, inBody, `an id with ${label}, in the body`);
        expect(t, 'no valid id: t is never asked').not.toHaveBeenCalled();
    });

    const NOT_NUMBERS: Array<[label: string, status: unknown]> = [
        ['the string "503"', '503'],
        ['null', null],
        ['undefined', undefined],
        ['an array holding 503', [503]],
        ['an object worth 503', {valueOf: () => 503}],
    ];

    // red until H-60r §4
    it.each(NOT_NUMBERS)('keeps the message when the status of the answer is %s, not a number', async (label, status) => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        expectComposesA503(withRequestId, t);
        const failure = answered(status, SERVER_BODY, headersWith(REQUEST_ID));
        expect(requestIdOf(failure), 'premise: the id itself is readable').toBe(REQUEST_ID);

        expectMessageKept(withRequestId, t, failure, `a status that is ${label}`);
        expect(t, 'no numeric 5xx: t is never asked').not.toHaveBeenCalled();
    });

    // red until H-60r §4
    it('never throws on hostile objects, and keeps the message: getters that throw, a revoked proxy', async () => {
        const {withRequestId} = await requestIdMessage();
        const t = recordingTranslate();
        expectComposesA503(withRequestId, t);
        const revocable = Proxy.revocable({}, {});
        revocable.revoke();
        const hostile: Array<[label: string, error: unknown]> = [
            ['an object whose response getter throws', throwingOn('response')],
            ['an object whose cause getter throws', throwingOn('cause')],
            ['an object whose originalError getter throws', throwingOn('originalError')],
            ["an Error whose cause's originalError getter throws", new Error('wrapped', {cause: throwingOn('originalError')})],
            ['an answer whose status getter throws, an id in its header', {response: Object.assign(throwingOn('status'), {headers: plainHeadersWith(REQUEST_ID), data: SERVER_BODY})}],
            ['a 503 whose headers getter throws, no id in its body', {response: Object.assign(throwingOn('headers'), {status: 503, data: SERVER_BODY})}],
            ['a revoked proxy', revocable.proxy],
            ['an Error whose cause is a revoked proxy', new Error('wrapped', {cause: revocable.proxy})],
        ];

        for (const [label, error] of hostile) expectMessageKept(withRequestId, t, error, label);
        expect(t, 'nothing readable: t is never asked').not.toHaveBeenCalled();
    });
});

describe('common.errorWithRequestId — the generated catalogues (src/lib/i18n/<lang>.json)', () => {
    /** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
    const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};
    const LOCALES = Object.keys(CATALOGUES) as SupportedLocale[];
    /** A message, and an id as the backend mints them. */
    const SAMPLE = {message: 'M.', requestId: '0123456789abcdef'};

    // red until common.errorWithRequestId is added to src/lib/i18n/base/<lang>.json: no catalogue holds it
    it.each(LOCALES)('%s: holds the key with {message} and {requestId} once each, and formats to the message, then the code in parentheses at the end of the line', (code) => {
        const text = leaf(CATALOGUES[code], KEY);
        expect(typeof text, `${code}: no ${KEY} in src/lib/i18n/${code}.json — it comes from src/lib/i18n/base/${code}.json`).toBe('string');
        const message = String(text);
        expect([occurrences(message, '{message}'), occurrences(message, '{requestId}')], `${code}: {message} and {requestId}, once each, in ${JSON.stringify(message)}`).toEqual([1, 1]);

        const MessageFormat = runtimeMessageFormat();
        const formatted = new MessageFormat(message, code, undefined, {ignoreTag: true}).format(SAMPLE);
        expect(typeof formatted, `${code}: the runtime formats it to a text`).toBe('string');
        const line = String(formatted);
        expect(line.startsWith(SAMPLE.message), `${code}: the message first, whole — ${JSON.stringify(line)}`).toBe(true);
        expect(line, `${code}: on one line`).not.toMatch(/[\r\n]/);
        const tail = /\(([^()]*)\)$/.exec(line);
        expect(tail, `${code}: parentheses end the line — ${JSON.stringify(line)}`).not.toBeNull();
        expect(tail?.[1] ?? '', `${code}: the code inside them — ${JSON.stringify(line)}`).toContain(SAMPLE.requestId);
    });

    // red until common.errorWithRequestId is added to src/lib/i18n/base/<lang>.json
    it('is translated: the four texts are not all the same', () => {
        const missing = LOCALES.filter((code) => typeof leaf(CATALOGUES[code], KEY) !== 'string');
        expect(missing, `premise: ${KEY} in every catalogue`).toEqual([]);

        expect(new Set(LOCALES.map((code) => leaf(CATALOGUES[code], KEY))).size, 'not one text copied into every language').toBeGreaterThan(1);
    });
});

describe('type-level — what the surfaces hold is taken as it is (front check)', () => {
    // red until H-60r §4; `front check` fails on the type import until the module exists, then proves each assignment and call below
    it("takes svelte-i18n's formatter, AiExportTranslate and the Translate aliases of lib/api, with no cast", async () => {
        const {withRequestId} = await requestIdMessage();
        const svelteI18nMock = vi.fn<SvelteI18nFormatter>(() => COMPOSED);
        const aiExportMock = vi.fn<AiExportTranslate>(() => COMPOSED);
        const bulkRefusalMock = vi.fn<BulkRefusalTranslate>(() => COMPOSED);
        const writeRefusalMock = vi.fn<WriteRefusalTranslate>(() => COMPOSED);
        // Each one typed as its surface holds it.
        const svelteI18n: SvelteI18nFormatter = svelteI18nMock;
        const aiExport: AiExportTranslate = aiExportMock;
        const bulkRefusal: BulkRefusalTranslate = bulkRefusalMock;
        const writeRefusal: WriteRefusalTranslate = writeRefusalMock;

        const composed: string = withRequestId(aiExport, MESSAGE, serverError());
        expect(composed, 'AiExportTranslate').toBe(COMPOSED);
        expect(withRequestId(svelteI18n, MESSAGE, serverError()), "svelte-i18n's formatter type").toBe(COMPOSED);
        expect(withRequestId(bulkRefusal, MESSAGE, serverError()), 'the Translate of bulkRefusal.ts').toBe(COMPOSED);
        expect(withRequestId(writeRefusal, MESSAGE, serverError()), 'the Translate of writeRefusal.ts').toBe(COMPOSED);

        // svelte-i18n's own value, and the type the module exports, which takes them all. Nothing answered, so none is asked and no locale is needed.
        const formatter = get(_);
        const translators: RequestIdTranslate[] = [formatter, svelteI18n, aiExport, bulkRefusal, writeRefusal];
        for (const translate of translators) expect(withRequestId(translate, MESSAGE, null), 'nothing answered: the message as it is').toBe(MESSAGE);
        for (const mock of [svelteI18nMock, aiExportMock, bulkRefusalMock, writeRefusalMock]) expect(mock.mock.calls, 'asked once, for the 503 alone').toEqual(askedFor(REQUEST_ID));
    });
});
