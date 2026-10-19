// @vitest-environment jsdom
/**
 * apiErrorConsole — what the browser console says when an API call fails (lot H-60, release 1.3, workstream H:
 * contract §8 and its amendment of 19/10; decisions D3 and D4).
 *
 * Today a failed call is silent, or printed as it came by whoever caught it: a `ZodiosError`'s message quotes the whole
 * response it refused. The developer asked whether what we print exposes sensitive data. This file pins a console that
 * says enough to find the failure in the server's log, and nothing a user typed or the server sent.
 *
 * The contract under test — `src/lib/api/apiErrorConsole.ts`, hooked in `src/lib/api/zodios-client.ts`:
 *
 *   - `setApiConsoleLevel(level)`, `apiConsoleLevel()`: `'error'`, the default, or `'debug'` (D4: the instance
 *     publishes it; `instanceConfig.test.ts` pins that side).
 *   - `requestIdOf(error)`: the `x-request-id` response header, else the body's `request_id`; only a string of 1 to 64
 *     characters among `[A-Za-z0-9_-]`, else null (D3: the UI may show it).
 *   - `apiFailureSummary(error)`: for an Axios error or a `ZodiosError`, an object with only `status` (null when nothing
 *     answered, and always for a `ZodiosError`), `method` (upper case) and `path` (no origin, query or fragment); `code`
 *     (`detail.code`, else `detail.error_code`), `reason_code` and `component_id`, read from a `detail` that is an
 *     object and kept only when they look like codes (`[A-Za-z0-9_.:-]`, at most 100 characters); `request_id`;
 *     `error_type` (the body's, an identifier of at most 100 characters); `network` (Axios's code, when nothing
 *     answered); `schema_issues` (`<path joined by .>:<issue code>`, at most 10, a segment that is neither an identifier
 *     nor an index printed as a star). Null for anything else, and for a canceled request (`ERR_CANCELED`).
 *   - `reportApiFailure(error, level = apiConsoleLevel())`: exactly one `console.error('[API]', head, fields)` when the
 *     failure is reportable — the head `<status> <METHOD> <path>`, with `network` or `schema` for the status; the
 *     fields, the summary's others — and nothing otherwise; it never throws. Reportable at `'error'`: a status of 500 or
 *     more, nothing answered, a schema mismatch; at `'debug'`, every status of 400 or more too.
 *   - Never on the console: the request body, its headers, the query string, the response headers but `x-request-id`,
 *     a `detail` sentence, a 422 `input`, `error.message`, what Zod received or expected.
 *   - The client: the response interceptor's error branch reports every Axios failure; `zodiosApi`'s plugin named
 *     `'zod-validation'`, Zodios's own replaced at its position, validates the responses as before (`validate:
 *     'response'`, `transform: true`) and reports a `ZodiosError` before re-throwing it.
 *
 * How. The pure functions get failures shaped as axios raises them — an `AxiosError` carrying the request it sent
 * (`AxiosHeaders`, a serialised body) and the response it got — and `ZodiosError`s raised by Zodios 10.9.6's own
 * validation plugin, never hand-made. The client cases go through the real `axiosInstance` and `zodiosApi` (the
 * generated client), with a transport per request answering what the case chose, as in `zodios-client.test.ts`. The six
 * console methods that print are spied and silenced around each case; the level, module state the client shares, is
 * put back to what the case found.
 *
 * The leak rule: every value the console must never show carries the word `canary` — a password, a bearer token, a
 * cookie, a query token, a response header, an error message, a `detail` sentence, a 422 `input`, a value Zod received,
 * a record key. The sweep reads every string reachable from every argument of every console call (own properties,
 * enumerable or not, keys included). Before it says «nothing leaked» it proves it can see: it finds what the line
 * legitimately printed, and a canary hidden in an `Error`'s message.
 *
 * One mock, `$lib/debug`: its real logger prints under Vitest (`import.meta.env.DEV`), and the console must hold only
 * what this contract prints. One reach into Zodios's internals, `getAnyEndpointPlugins()`, private in its typings (the
 * version is locked): the only way to see that the plugin was replaced, not added beside Zodios's own.
 *
 * Not pinned, the contract leaves them open: a header that is no valid id while the body holds one; whether a code may
 * be empty; identifiers beyond ASCII; the request id of a schema mismatch; the order of the issues, and which 10 a
 * longer list keeps; what is printed for an Axios error without its config.
 *
 * Red today: `apiErrorConsole.ts` does not exist — each case loads it by a computed specifier and fails on its own, with
 * that in its message — and the client reports nothing: the cases through it fail on their line. Its place in the
 * runner: `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`), next to
 * `zodios-client.test.ts`.
 */
import axios, {AxiosError, AxiosHeaders, isAxiosError, isCancel, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {makeApi, ZodiosError, zodValidationPlugin, type ZodiosPlugin} from '@zodios/core';
import {z} from 'zod';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {axiosInstance, zodiosApi} from './zodios-client';
import {schemas} from './generated';

vi.mock('$lib/debug', () => ({debug: {log: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn(), group: vi.fn(), groupEnd: vi.fn(), time: vi.fn(), timeEnd: vi.fn()}, isDebugEnabled: () => false}));

// =============================================================================
//  The module under test
// =============================================================================

type ConsoleLevel = 'error' | 'debug';

/** `src/lib/api/apiErrorConsole.ts`, as the cases call it. */
interface ApiErrorConsole {
    setApiConsoleLevel(level: ConsoleLevel): void;
    apiConsoleLevel(): ConsoleLevel;
    requestIdOf(error: unknown): string | null;
    apiFailureSummary(error: unknown): Record<string, unknown> | null;
    reportApiFailure(error: unknown, level?: ConsoleLevel): void;
}

/** A computed specifier: Vite does not resolve it when it transforms this file, so while the module is missing each case fails on its own. */
const CONSOLE_MODULE = './apiErrorConsole';
const CONSOLE_EXPORTS = ['setApiConsoleLevel', 'apiConsoleLevel', 'requestIdOf', 'apiFailureSummary', 'reportApiFailure'] as const;

/** The module as the running case opened it, and the level it found there: `afterEach` puts that level back. */
let opened: {api: ApiErrorConsole; levelBefore: ConsoleLevel} | null = null;

async function apiErrorConsole(): Promise<ApiErrorConsole> {
    let loaded: Record<string, unknown>;
    try {
        loaded = (await import(/* @vite-ignore */ CONSOLE_MODULE)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`src/lib/api/apiErrorConsole.ts cannot be loaded (red until H-60: it does not exist yet), so no API failure reaches the browser console — ${String(error)}`);
    }
    for (const name of CONSOLE_EXPORTS) expect(typeof loaded[name], `apiErrorConsole.ts exports no ${name}()`).toBe('function');
    const api = loaded as unknown as ApiErrorConsole;
    opened ??= {api, levelBefore: api.apiConsoleLevel()};
    return api;
}

// =============================================================================
//  The console, spied
// =============================================================================

/** Every console method that prints: a leak through any of them is seen. */
const CONSOLE_METHODS = ['error', 'warn', 'log', 'info', 'debug', 'trace'] as const;
type ConsoleMethod = (typeof CONSOLE_METHODS)[number];

interface ConsoleSpy {
    mock: {calls: unknown[][]};
    mockClear(): unknown;
    mockRestore(): void;
}

let consoleSpies: Record<ConsoleMethod, ConsoleSpy>;

beforeEach(() => {
    // Silenced: each case reads what was printed from the spies.
    consoleSpies = {
        error: vi.spyOn(console, 'error').mockImplementation(() => {}),
        warn: vi.spyOn(console, 'warn').mockImplementation(() => {}),
        log: vi.spyOn(console, 'log').mockImplementation(() => {}),
        info: vi.spyOn(console, 'info').mockImplementation(() => {}),
        debug: vi.spyOn(console, 'debug').mockImplementation(() => {}),
        trace: vi.spyOn(console, 'trace').mockImplementation(() => {}),
    };
});

afterEach(() => {
    for (const method of CONSOLE_METHODS) consoleSpies[method].mockRestore();
    // The level is module state the client shares: what the case found is put back.
    if (opened) opened.api.setApiConsoleLevel(opened.levelBefore);
    opened = null;
});

/** Every console call of the case so far. */
function consoleCalls(): Array<{method: ConsoleMethod; args: unknown[]}> {
    return CONSOLE_METHODS.flatMap((method) => consoleSpies[method].mock.calls.map((args) => ({method, args})));
}

/** Forgets the calls so far: after a barrier, the case reads only what follows. */
function clearConsole(): void {
    for (const method of CONSOLE_METHODS) consoleSpies[method].mockClear();
}

// =============================================================================
//  What a summary and a line may hold
// =============================================================================

/** Every field a summary may hold. */
const SUMMARY_FIELDS: readonly string[] = ['status', 'method', 'path', 'code', 'reason_code', 'component_id', 'request_id', 'error_type', 'network', 'schema_issues'];
/** The fields of the line's third argument: the summary's, less those its head says. */
const LINE_FIELDS: readonly string[] = SUMMARY_FIELDS.filter((field) => !['status', 'method', 'path'].includes(field));

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** `record` without its empty fields (absent, null and undefined are one answer here), `schema_issues` sorted: the contract fixes no order. */
function comparable(record: Record<string, unknown>): Record<string, unknown> {
    const filled = Object.entries(record).filter(([, value]) => value !== null && value !== undefined);
    return Object.fromEntries(filled.map(([key, value]) => [key, key === 'schema_issues' && Array.isArray(value) ? [...value].sort() : value]));
}

/** The fields of `summary` a line repeats beside its head. */
function lineFieldsOf(summary: unknown): Record<string, unknown> {
    return isRecord(summary) ? Object.fromEntries(Object.entries(summary).filter(([key]) => LINE_FIELDS.includes(key))) : {};
}

/** `summary` holds exactly `expected`: no field outside the contract's, `status` as given (null when nothing answered), the rest equal. */
function expectSummary(summary: unknown, expected: {status: number | null} & Record<string, unknown>): void {
    expect(isRecord(summary), `a summary is an object; got ${String(summary)}`).toBe(true);
    const fields = summary as Record<string, unknown>;
    expect(
        Object.keys(fields).filter((key) => !SUMMARY_FIELDS.includes(key)),
        'fields the contract does not allow in a summary',
    ).toEqual([]);
    expect(fields.status, 'status: the HTTP status, null when nothing answered').toBe(expected.status);
    expect(comparable(fields)).toEqual(comparable(expected));
}

/** The case printed one thing, `console.error('[API]', head, fields)`: the fields, checked against the contract's list. */
function expectLineHead(head: string): Record<string, unknown> {
    const calls = consoleCalls();
    expect(
        calls.map(({method, args}) => [method, ...args.slice(0, 2)]),
        "exactly one console call: console.error('[API]', head, fields)",
    ).toEqual([['error', '[API]', head]]);
    const {args} = calls[0];
    expect(args.length, 'three arguments: the tag, the head, the other fields').toBe(3);
    expect(isRecord(args[2]), 'the third argument is an object of fields').toBe(true);
    const fields = args[2] as Record<string, unknown>;
    expect(
        Object.keys(fields).filter((key) => !LINE_FIELDS.includes(key)),
        'fields the contract does not allow on the line',
    ).toEqual([]);
    return fields;
}

/** The case printed exactly `console.error('[API]', head, fields)`. */
function expectLine(head: string, fields: Record<string, unknown>): void {
    expect(comparable(expectLineHead(head)), `the fields of «${head}»`).toEqual(comparable(fields));
}

// =============================================================================
//  The leak sweep
// =============================================================================

/** The word in every value the console must never show: a printed string that holds it is a leak. */
const CANARY = 'canary';

/** Every string reachable from `values`: own properties, enumerable or not (an Error's message), their keys too. */
function stringsIn(values: unknown[]): string[] {
    const found: string[] = [];
    const seen = new WeakSet<object>();
    const visit = (value: unknown, depth: number): void => {
        if (typeof value === 'string') {
            found.push(value);
            return;
        }
        if (typeof value === 'number' || typeof value === 'bigint' || typeof value === 'boolean') {
            found.push(String(value));
            return;
        }
        if (typeof value !== 'object' || value === null || seen.has(value) || depth > 12) return;
        seen.add(value);
        let keys: Array<string | symbol>;
        try {
            keys = Reflect.ownKeys(value);
        } catch {
            return;
        }
        for (const key of keys) {
            if (typeof key === 'string') found.push(key);
            let child: unknown;
            try {
                child = Reflect.get(value, key);
            } catch {
                continue;
            }
            visit(child, depth + 1);
        }
        try {
            if (value instanceof Map) value.forEach((child, key) => [key, child].forEach((item) => visit(item, depth + 1)));
            if (value instanceof Set) value.forEach((child) => visit(child, depth + 1));
        } catch {
            // A hostile object: what could be read was read.
        }
    };
    for (const value of values) visit(value, 0);
    return found;
}

/** Every string the console received during the case. */
function printedStrings(): string[] {
    return stringsIn(consoleCalls().flatMap(({args}) => args));
}

/**
 * Nothing printed carries a canary. Before it says so, the sweep proves it can see: it finds each of `shown`, what the
 * line legitimately printed, and a canary hidden in an Error's message, which is not enumerable.
 */
function expectNoCanaryPrinted(shown: string[]): void {
    expect(
        stringsIn([new Error(`${CANARY}-probe`)]).some((text) => text.includes(CANARY)),
        "Barrier: the sweep reads an Error's message",
    ).toBe(true);
    const printed = printedStrings();
    for (const text of shown)
        expect(
            printed.some((line) => line.includes(text)),
            `Barrier: the sweep sees what was printed (${text})`,
        ).toBe(true);
    expect(
        printed.filter((text) => text.includes(CANARY)),
        'printed: a value the console must never show',
    ).toEqual([]);
}

// =============================================================================
//  Failures, as axios raises them
// =============================================================================

/** Ids as the backend mints them (`secrets.token_hex(8)`): 16 lowercase hex characters. */
const REQUEST_ID = '5f2b9c0e7d1a4386';
const BODY_REQUEST_ID = 'b04c6e2f9a7d1358';

const SECRET = {
    password: 'canary-password',
    bearer: 'canary-bearer-token',
    cookie: 'canary-session-cookie',
    queryToken: 'canary-query-token',
    fragment: 'canary-fragment',
    param: 'canary-param-token',
    setCookie: 'canary-set-cookie',
    responseHeader: 'canary-response-header',
    message: 'canary-error-message',
    detailMessage: 'canary-detail',
    detailExtra: 'canary-extra',
    detailSentence: 'canary: the detail of the error, a sentence',
    input: 'canary-422-input',
    proxyPage: 'canary-proxy-page',
};

/** The request a failure was: a JSON body with a password, credentials in its headers, a token in its query string and in its params. */
function sentRequest(method: string, url: string): InternalAxiosRequestConfig {
    const headers = AxiosHeaders.from({'Content-Type': 'application/json', 'Accept-Language': 'en', Authorization: `Bearer ${SECRET.bearer}`, Cookie: `lf_session=${SECRET.cookie}`});
    return {method, url, baseURL: '/', headers, params: {token: SECRET.param}, data: JSON.stringify({username: 'h60-user', password: SECRET.password}), timeout: 30_000, withCredentials: true} as InternalAxiosRequestConfig;
}

/** A failed response as axios raises it: an `AxiosError` carrying the request and the response, its message a canary. */
function answered(status: number, body: unknown, options: {method?: string; url?: string; headers?: Record<string, string>} = {}): AxiosError {
    const config = sentRequest(options.method ?? 'post', options.url ?? `/api/v1/h60/probe?token=${SECRET.queryToken}#${SECRET.fragment}`);
    const headers = AxiosHeaders.from({'content-type': 'application/json', 'set-cookie': [`lf_session=${SECRET.setCookie}`], 'x-libre-canary': SECRET.responseHeader, ...options.headers});
    const response = {status, statusText: String(status), headers, config, request: {}, data: body} as AxiosResponse;
    return new AxiosError(`${SECRET.message} ${status}`, status >= 500 ? AxiosError.ERR_BAD_RESPONSE : AxiosError.ERR_BAD_REQUEST, config, {}, response);
}

/** A request nothing answered, with Axios's code: a network failure, a timeout. */
function unanswered(code: string): AxiosError {
    return new AxiosError(`${SECRET.message} ${code}`, code, sentRequest('get', `/api/v1/assets?token=${SECRET.queryToken}`), {});
}

/** What axios raises for a request its AbortController canceled before it left: a CanceledError, ERR_CANCELED, no response. */
function canceledRequest(): Promise<unknown> {
    const controller = new AbortController();
    controller.abort();
    const transport: AxiosAdapter = () => Promise.reject(new Error('premise: a canceled request never reaches the transport'));
    return rejection(axios.create().get(`/api/v1/assets?token=${SECRET.queryToken}`, {signal: controller.signal, adapter: transport}));
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

/** The AI Export failure of the brief: a 503 whose detail is coded, with a sentence and an extra field beside its codes. */
const SNAPSHOT_BODY = {
    detail: {code: 'snapshot_source_failure', component_id: 'portfolio.technical_prices', reason_code: 'x', message: SECRET.detailMessage, extra: SECRET.detailExtra},
    request_id: REQUEST_ID,
    error_type: 'KeyError',
};
const snapshotFailure = (): AxiosError => answered(503, SNAPSHOT_BODY, {url: `/api/v1/ai-export/snapshot?token=${SECRET.queryToken}#${SECRET.fragment}`, headers: {'x-request-id': REQUEST_ID}});
/** A 500 whose detail is a sentence, codes at the top of the body that are not the detail's, its id in the body only. */
const sentenceFailure = (): AxiosError => answered(500, {detail: SECRET.detailSentence, code: 'top_level_code', reason_code: 'top_level_reason', component_id: 'top.level', request_id: REQUEST_ID, error_type: 'KeyError'}, {method: 'get', url: `/api/v1/brokers/7/summary?token=${SECRET.queryToken}`});
/** A 502 from a proxy in front of the server: an HTML page, no id. */
const proxyFailure = (): AxiosError => answered(502, `<html><body>${SECRET.proxyPage}</body></html>`, {method: 'get', url: '/api/v1/fx/rates', headers: {'content-type': 'text/html'}});
const unauthenticated = (): AxiosError => answered(401, {detail: SECRET.detailSentence}, {method: 'get', url: '/api/v1/auth/me', headers: {'x-request-id': REQUEST_ID}});
const notFound = (): AxiosError => answered(404, {detail: {code: 'asset_not_found', message: SECRET.detailMessage}}, {method: 'get', url: '/api/v1/assets/999999', headers: {'x-request-id': REQUEST_ID}});
const conflict = (): AxiosError => answered(409, {detail: {code: 'broker_name_taken', reason_code: 'duplicate_name', component_id: 'brokers.name', message: SECRET.detailMessage}}, {url: '/api/v1/brokers', headers: {'x-request-id': REQUEST_ID}});
/** A 422 of request validation (FastAPI): a list of issues, each echoing in `input` the value it refused. */
const invalidRequest = (): AxiosError => answered(422, {detail: [{type: 'string_too_short', loc: ['body', 'password'], msg: SECRET.detailSentence, input: SECRET.input, ctx: {min_length: 12}}]}, {url: '/api/v1/auth/register', headers: {'x-request-id': REQUEST_ID}});

type FailureCase = [label: string, failure: () => AxiosError, head: string, fields: Record<string, unknown>];

/** Printed at both levels. */
const SERVER_FAILURES: FailureCase[] = [
    ['the AI Export 503', snapshotFailure, '503 POST /api/v1/ai-export/snapshot', {code: 'snapshot_source_failure', reason_code: 'x', component_id: 'portfolio.technical_prices', request_id: REQUEST_ID, error_type: 'KeyError'}],
    ['a 500 whose detail is a sentence', sentenceFailure, '500 GET /api/v1/brokers/7/summary', {request_id: REQUEST_ID, error_type: 'KeyError'}],
    ['a 502 from a proxy, an HTML page', proxyFailure, '502 GET /api/v1/fx/rates', {}],
    ['a network error', () => unanswered(AxiosError.ERR_NETWORK), 'network GET /api/v1/assets', {network: 'ERR_NETWORK'}],
    ['a timeout', () => unanswered(AxiosError.ECONNABORTED), 'network GET /api/v1/assets', {network: 'ECONNABORTED'}],
];
/** Silent at `'error'`, printed at `'debug'`. */
const CLIENT_FAILURES: FailureCase[] = [
    ['a 401', unauthenticated, '401 GET /api/v1/auth/me', {request_id: REQUEST_ID}],
    ['a 404 with a coded detail', notFound, '404 GET /api/v1/assets/999999', {code: 'asset_not_found', request_id: REQUEST_ID}],
    ['a 409 with every code', conflict, '409 POST /api/v1/brokers', {code: 'broker_name_taken', reason_code: 'duplicate_name', component_id: 'brokers.name', request_id: REQUEST_ID}],
    ['a 422 of request validation, whose issue echoes the input', invalidRequest, '422 POST /api/v1/auth/register', {request_id: REQUEST_ID}],
];

// =============================================================================
//  A response that breaks its schema, refused by Zodios itself
// =============================================================================

type PluginApi = Parameters<NonNullable<ZodiosPlugin['response']>>[0];
type PluginConfig = Parameters<NonNullable<ZodiosPlugin['response']>>[1];

const PROBE_PATH = '/api/v1/h60/schema-probe';
/** One of each segment an issue's path can hold: a key, a nested key, a list index, a record key. */
const PROBE_SCHEMA = z.object({
    profile: z.enum(['selfhosted', 'managed']),
    accounts: z.object({registration_locked: z.boolean()}),
    items: z.array(z.object({quantity: z.number()})),
    totals: z.record(z.string(), z.number()),
});
const PROBE_API = makeApi([{method: 'get', path: PROBE_PATH, alias: 'h60_schema_probe', response: PROBE_SCHEMA}]);
/** A record key is data: this one is neither an identifier nor an index, so the line prints it as a star. */
const RECORD_KEY = 'IT0005 canary/€';
/** Breaks PROBE_SCHEMA at each kind of segment, each time with a value Zod quotes. */
const BROKEN_BODY = {
    profile: 'canary-profile',
    accounts: {registration_locked: 'canary-locked'},
    items: [{quantity: 1}, {quantity: 'canary-quantity'}],
    totals: {[RECORD_KEY]: 'canary-total'},
};
/** Its issues as the line prints them. */
const BROKEN_ISSUES = ['profile:invalid_enum_value', 'accounts.registration_locked:invalid_type', 'items.1.quantity:invalid_type', 'totals.*:invalid_type'];

/** A JSON answer as Zodios's validation reads it: `content-type` in lower case, as axios hands it over. */
function jsonResponse(status: number, data: unknown): AxiosResponse {
    return {data, status, statusText: String(status), headers: AxiosHeaders.from({'content-type': 'application/json'}), config: {headers: new AxiosHeaders()}, request: {}} as AxiosResponse;
}

/** The ZodiosError Zodios 10.9.6 raises for `body`, answered 200 to GET PROBE_PATH: its own validation plugin, as the client runs it. */
async function schemaMismatch(body: unknown): Promise<ZodiosError> {
    const validation = zodValidationPlugin({validate: 'response', transform: true, sendDefaults: false});
    const request = {method: 'get', url: PROBE_PATH, queries: {token: SECRET.queryToken}, headers: {Authorization: `Bearer ${SECRET.bearer}`}} as unknown as PluginConfig;
    const refusal = await rejection(validation.response!(PROBE_API as unknown as PluginApi, request, jsonResponse(200, body)));
    expect(refusal, 'premise: Zodios refused the body with its own error').toBeInstanceOf(ZodiosError);
    return refusal as ZodiosError;
}

// =============================================================================
//  The real client
// =============================================================================

/** A transport answering `status` with `body`: resolved for 2xx, otherwise rejected with the response, as axios's own adapters do. */
function answering(status: number, body: unknown, headers: Record<string, string> = {}): AxiosAdapter {
    return (config) => {
        const response = {data: body, status, statusText: String(status), headers: {'content-type': 'application/json', ...headers}, config, request: {}} as AxiosResponse;
        if (status >= 200 && status < 300) return Promise.resolve(response);
        return Promise.reject(new AxiosError(`${SECRET.message} ${status}`, status >= 500 ? AxiosError.ERR_BAD_RESPONSE : AxiosError.ERR_BAD_REQUEST, config, {}, response));
    };
}

/** `GET /api/v1/system/instance` breaking `InstanceConfigResponse`: a profile the schema does not know, which Zodios's message quotes. */
const BROKEN_INSTANCE = {profile: 'canary-profile', accounts: {registration_mode: 'open', registration_locked: false}};
/** The same answer, matching: the schema fills a default in (`accounts.first_account_open`) and drops a key it does not know. */
const MATCHING_INSTANCE = {profile: 'managed', accounts: {registration_mode: 'invite', registration_locked: true}, h60_unknown_key: 'dropped by the schema'};

/**
 * The plugins Zodios runs for every endpoint, from `getAnyEndpointPlugins()`: private in Zodios 10.9.6's typings (the
 * version is locked), read only to see that the plugin named `'zod-validation'` was replaced, not added beside its own.
 */
function pluginsOfEveryEndpoint(): Array<ZodiosPlugin | undefined> {
    const client = zodiosApi as unknown as {getAnyEndpointPlugins?: () => {plugins?: Array<ZodiosPlugin | undefined>}};
    expect(typeof client.getAnyEndpointPlugins, 'premise: Zodios 10.9.6 keeps the plugins of every endpoint behind getAnyEndpointPlugins()').toBe('function');
    const plugins = client.getAnyEndpointPlugins?.()?.plugins;
    expect(Array.isArray(plugins), 'premise: that registry lists its plugins').toBe(true);
    return plugins ?? [];
}

// =============================================================================
//  The cases
// =============================================================================

describe('apiErrorConsole — the level (D4)', () => {
    // red until H-60: the module does not exist
    it('is error until set, and setApiConsoleLevel switches it both ways', async () => {
        const {apiConsoleLevel, setApiConsoleLevel} = await apiErrorConsole();

        expect(apiConsoleLevel(), 'the default, which every case puts back').toBe('error');
        setApiConsoleLevel('debug');
        expect(apiConsoleLevel()).toBe('debug');
        setApiConsoleLevel('error');
        expect(apiConsoleLevel()).toBe('error');
    });

    // red until H-60
    it('is what reportApiFailure follows without a level: a 404 prints at debug, and not at error', async () => {
        const {setApiConsoleLevel, reportApiFailure} = await apiErrorConsole();

        setApiConsoleLevel('debug');
        reportApiFailure(notFound());
        expectLine('404 GET /api/v1/assets/999999', {code: 'asset_not_found', request_id: REQUEST_ID});

        clearConsole();
        setApiConsoleLevel('error');
        reportApiFailure(notFound());
        expect(consoleCalls(), 'at error, a 404 prints nothing').toEqual([]);
    });
});

describe('apiFailureSummary — what a failure may say', () => {
    // red until H-60
    it('reads the AI Export 503: status, method, path, the codes of its detail, the request id, the error type — nothing else', async () => {
        const {apiFailureSummary} = await apiErrorConsole();

        expectSummary(apiFailureSummary(snapshotFailure()), {status: 503, method: 'POST', path: '/api/v1/ai-export/snapshot', code: 'snapshot_source_failure', reason_code: 'x', component_id: 'portfolio.technical_prices', request_id: REQUEST_ID, error_type: 'KeyError'});
    });

    // red until H-60
    it('takes the path alone: no origin, no query string, no fragment', async () => {
        const {apiFailureSummary} = await apiErrorConsole();
        const failure = answered(500, {}, {method: 'get', url: `https://librefolio.example:8443/api/v1/fx/rates?token=${SECRET.queryToken}&base=EUR#${SECRET.fragment}`});

        expectSummary(apiFailureSummary(failure), {status: 500, method: 'GET', path: '/api/v1/fx/rates'});
    });

    // red until H-60
    it('reads no code from a detail that is a sentence nor from the top of the body, and keeps the id and the error type', async () => {
        const {apiFailureSummary} = await apiErrorConsole();

        expectSummary(apiFailureSummary(sentenceFailure()), {status: 500, method: 'GET', path: '/api/v1/brokers/7/summary', request_id: REQUEST_ID, error_type: 'KeyError'});
    });

    const CODE_SOURCES: Array<[label: string, body: unknown, codes: Record<string, string>]> = [
        ['detail.code, which wins over detail.error_code', {detail: {code: 'snapshot_source_failure', error_code: 'legacy_failure'}}, {code: 'snapshot_source_failure'}],
        ['detail.error_code, when there is no detail.code', {detail: {error_code: 'legacy_failure'}}, {code: 'legacy_failure'}],
        ['nowhere in a detail that is a list (a 422 of request validation)', {detail: [{code: 'listed_code', reason_code: 'listed_reason'}]}, {}],
        ['nowhere in a detail that is null', {detail: null}, {}],
        ['nowhere at the top of a body without a detail', {code: 'top_level_code', reason_code: 'top_level_reason', component_id: 'top.level'}, {}],
        ['nowhere in a body that is text', 'snapshot_source_failure', {}],
    ];

    // red until H-60
    it.each(CODE_SOURCES)('reads code from %s', async (_label, body, codes) => {
        const {apiFailureSummary} = await apiErrorConsole();

        expectSummary(apiFailureSummary(answered(503, body, {url: '/api/v1/ai-export/snapshot'})), {status: 503, method: 'POST', path: '/api/v1/ai-export/snapshot', ...codes});
    });

    const CODE_SHAPES: Array<[label: string, detail: Record<string, unknown>, printed: Record<string, string>]> = [
        ['letters, digits and _ . : -', {code: 'snapshot_source_failure', reason_code: 'provider:rate-limited', component_id: 'portfolio.technical_prices'}, {code: 'snapshot_source_failure', reason_code: 'provider:rate-limited', component_id: 'portfolio.technical_prices'}],
        ['100 characters', {code: 'c'.repeat(100), reason_code: 'r'.repeat(100), component_id: 'i'.repeat(100)}, {code: 'c'.repeat(100), reason_code: 'r'.repeat(100), component_id: 'i'.repeat(100)}],
        ['101 characters: left out', {code: 'c'.repeat(101), reason_code: 'r'.repeat(101), component_id: 'i'.repeat(101)}, {}],
        ['free text: left out', {code: 'Snapshot failed: canary text', reason_code: 'canary reason', component_id: 'canary/component'}, {}],
        ['a line break: left out', {code: 'snapshot_source_failure\ncanary', reason_code: 'x\ncanary', component_id: 'portfolio\ncanary'}, {}],
        ['not strings: left out', {code: 42, reason_code: true, component_id: {id: 'portfolio.technical_prices'}}, {}],
    ];

    // red until H-60 (amendment of 19/10: a free text in those keys is never printed)
    it.each(CODE_SHAPES)('keeps code, reason_code and component_id only when they look like codes — %s', async (_label, detail, printed) => {
        const {apiFailureSummary} = await apiErrorConsole();

        expectSummary(apiFailureSummary(answered(503, {detail}, {url: '/api/v1/ai-export/snapshot'})), {status: 503, method: 'POST', path: '/api/v1/ai-export/snapshot', ...printed});
    });

    const ERROR_TYPES: Array<[label: string, errorType: unknown, printed: Record<string, string>]> = [
        ['a class name', 'KeyError', {error_type: 'KeyError'}],
        ['the class of a response that broke its model', 'ResponseValidationError', {error_type: 'ResponseValidationError'}],
        ['an identifier of 100 characters', 'E'.repeat(100), {error_type: 'E'.repeat(100)}],
        ['an identifier of 101 characters: left out', 'E'.repeat(101), {}],
        ['a sentence: left out', 'KeyError: canary', {}],
        ['a name with a space: left out', 'Key Error', {}],
        ['a number: left out', 42, {}],
    ];

    // red until H-60
    it.each(ERROR_TYPES)('keeps error_type only when it is an identifier of at most 100 characters — %s', async (_label, errorType, printed) => {
        const {apiFailureSummary} = await apiErrorConsole();

        expectSummary(apiFailureSummary(answered(500, {detail: 'Internal Server Error', error_type: errorType}, {method: 'get', url: '/api/v1/assets'})), {status: 500, method: 'GET', path: '/api/v1/assets', ...printed});
    });

    // red until H-60
    it.each([
        ['a network error', AxiosError.ERR_NETWORK],
        ['a timeout', AxiosError.ECONNABORTED],
        ['a timeout told apart (transitional.clarifyTimeoutError)', AxiosError.ETIMEDOUT],
    ])('says of a request nothing answered, %s: status null, network its Axios code', async (_label, code) => {
        const {apiFailureSummary} = await apiErrorConsole();

        expectSummary(apiFailureSummary(unanswered(code)), {status: null, method: 'GET', path: '/api/v1/assets', network: code});
    });

    // red until H-60 (amendment of 19/10: an abort is no failure)
    it('has no summary for a canceled request, and reportApiFailure prints nothing for it at either level', async () => {
        const {apiFailureSummary, reportApiFailure} = await apiErrorConsole();
        const canceled = await canceledRequest();
        expect(isCancel(canceled), 'premise: axios rejected the request as canceled').toBe(true);
        const {code, response} = canceled as AxiosError;
        expect([isAxiosError(canceled), code, response], 'premise: an Axios error, ERR_CANCELED, no response — what a network failure looks like too').toEqual([true, 'ERR_CANCELED', undefined]);
        reportApiFailure(unanswered(AxiosError.ERR_NETWORK), 'error');
        expect(consoleCalls().length, 'Barrier: a request nothing answered does print').toBe(1);
        clearConsole();

        expect(apiFailureSummary(canceled)).toBeNull();
        reportApiFailure(canceled, 'error');
        reportApiFailure(canceled, 'debug');
        expect(consoleCalls(), 'an abort prints nothing').toEqual([]);
    });

    const NOT_FAILURES: Array<[label: string, value: unknown]> = [
        ['null', null],
        ['undefined', undefined],
        ['a string', 'Request failed with status code 503'],
        ['a number', 503],
        ['an empty object', {}],
        ['an Error', new Error(SECRET.message)],
        ['an object shaped like a failure, without the Axios flag', {response: {status: 503, data: SNAPSHOT_BODY}, config: {method: 'post', url: '/api/v1/ai-export/snapshot'}}],
    ];

    // red until H-60
    it('is null for what is neither an Axios error nor a ZodiosError, and reportApiFailure prints nothing for it', async () => {
        const {apiFailureSummary, reportApiFailure} = await apiErrorConsole();
        reportApiFailure(snapshotFailure(), 'error');
        expect(consoleCalls().length, 'Barrier: the capture is live, and an Axios failure prints').toBe(1);
        clearConsole();

        for (const [label, value] of NOT_FAILURES) {
            expect(apiFailureSummary(value), label).toBeNull();
            reportApiFailure(value, 'error');
            reportApiFailure(value, 'debug');
        }

        expect(consoleCalls(), 'nothing printed for what is not an API failure').toEqual([]);
    });
});

describe('reportApiFailure — one line, when the level asks for it', () => {
    // red until H-60
    it.each(SERVER_FAILURES)('prints %s at error as one line: [API], its head, the other fields of its summary', async (_label, failure, head, fields) => {
        const {reportApiFailure, apiFailureSummary} = await apiErrorConsole();
        const once = failure();

        reportApiFailure(once, 'error');

        expectLine(head, fields);
        expect(comparable(lineFieldsOf(apiFailureSummary(once))), 'the line says what the summary says').toEqual(comparable(fields));
    });

    // red until H-60
    it('prints no 401, 404, 409 or 422 at error, though it summarises each', async () => {
        const {reportApiFailure, apiFailureSummary} = await apiErrorConsole();
        reportApiFailure(snapshotFailure(), 'error');
        expect(consoleCalls().length, 'Barrier: at this level, through this capture, a 503 prints').toBe(1);
        clearConsole();

        for (const [label, failure] of CLIENT_FAILURES) {
            const once = failure();
            expect(apiFailureSummary(once), `premise: ${label} is a failure the module reads`).not.toBeNull();
            reportApiFailure(once, 'error');
        }

        expect(consoleCalls(), 'a 4xx is not printed at error').toEqual([]);
    });

    // red until H-60
    it.each(CLIENT_FAILURES)('prints %s at debug, with the other fields of its summary and nothing of its body beside them', async (_label, failure, head, fields) => {
        const {reportApiFailure, apiFailureSummary} = await apiErrorConsole();
        const once = failure();

        reportApiFailure(once, 'debug');

        expectLine(head, fields);
        expect(comparable(lineFieldsOf(apiFailureSummary(once))), 'the line says what the summary says').toEqual(comparable(fields));
        expectNoCanaryPrinted([head]);
    });
});

describe("the console never shows what a failure carries (the developer's question)", () => {
    // red until H-60
    it('prints no request body, request header, query string, response header but x-request-id, error message, detail sentence nor 422 input — at either level', async () => {
        const {reportApiFailure} = await apiErrorConsole();
        const failures = [...SERVER_FAILURES, ...CLIENT_FAILURES];

        for (const level of ['error', 'debug'] as const) for (const [, failure] of failures) reportApiFailure(failure(), level);

        expect(consoleCalls().length, 'Barrier: the server failures printed at both levels, the others at debug').toBe(2 * SERVER_FAILURES.length + CLIENT_FAILURES.length);
        expectNoCanaryPrinted([REQUEST_ID, '/api/v1/ai-export/snapshot', 'portfolio.technical_prices']);
    });
});

describe('a ZodiosError — a response that breaks its schema', () => {
    // red until H-60
    it('is summarised as status null, its method and path, and its issues as path:code, a record key printed as a star', async () => {
        const {apiFailureSummary} = await apiErrorConsole();
        const refusal = await schemaMismatch(BROKEN_BODY);

        expectSummary(apiFailureSummary(refusal), {status: null, method: 'GET', path: PROBE_PATH, schema_issues: BROKEN_ISSUES});
    });

    // red until H-60
    it.each(['error', 'debug'] as const)('prints at %s as one line headed schema, without the body its message quotes', async (level) => {
        const {reportApiFailure} = await apiErrorConsole();
        const refusal = await schemaMismatch(BROKEN_BODY);
        expect(refusal.message, 'premise: the message of the error quotes the body it refused').toContain('canary-quantity');

        reportApiFailure(refusal, level);

        expectLine(`schema GET ${PROBE_PATH}`, {schema_issues: BROKEN_ISSUES});
        expectNoCanaryPrinted(['totals.*:invalid_type']);
    });

    // red until H-60
    it('lists at most 10 issues', async () => {
        const {apiFailureSummary} = await apiErrorConsole();
        const refusal = await schemaMismatch({...BROKEN_BODY, items: Array.from({length: 15}, () => ({quantity: 'canary-quantity'}))});
        expect((refusal.cause as z.ZodError).issues.length, 'premise: Zod found more than 10').toBeGreaterThan(10);

        const issues = apiFailureSummary(refusal)?.schema_issues;

        expect(Array.isArray(issues) ? issues.length : issues, 'ten issues listed').toBe(10);
        const known = /^(profile:invalid_enum_value|accounts\.registration_locked:invalid_type|items\.\d+\.quantity:invalid_type|totals\.\*:invalid_type)$/;
        expect(
            (issues as unknown[]).filter((issue) => typeof issue !== 'string' || !known.test(issue)),
            'each one an issue of the body, as path:code',
        ).toEqual([]);
    });
});

describe('requestIdOf — the id the server gave the request (D3)', () => {
    // red until H-60
    it("reads the x-request-id header first, and the body's request_id when no header says it", async () => {
        const {requestIdOf} = await apiErrorConsole();

        expect(requestIdOf(answered(500, {request_id: BODY_REQUEST_ID}, {headers: {'x-request-id': REQUEST_ID}})), 'the header, before the body').toBe(REQUEST_ID);
        expect(requestIdOf(answered(500, {detail: 'Internal Server Error'}, {headers: {'x-request-id': REQUEST_ID}})), 'the header alone').toBe(REQUEST_ID);
        expect(requestIdOf(answered(500, {request_id: BODY_REQUEST_ID})), 'the body, without a header').toBe(BODY_REQUEST_ID);
        expect(requestIdOf(answered(500, {detail: 'Internal Server Error'})), 'neither').toBeNull();
        expect(requestIdOf(unanswered(AxiosError.ERR_NETWORK)), 'no response').toBeNull();
    });

    // red until H-60
    it('takes an id of 1 to 64 characters among A-Z a-z 0-9 _ -', async () => {
        const {requestIdOf} = await apiErrorConsole();

        for (const id of ['a', 'A-z_09', 'f'.repeat(64), REQUEST_ID]) {
            expect(requestIdOf(answered(500, {}, {headers: {'x-request-id': id}})), `${id} in the header`).toBe(id);
            expect(requestIdOf(answered(500, {request_id: id})), `${id} in the body`).toBe(id);
        }
    });

    // red until H-60
    it.each([
        ['an empty string', ''],
        ['65 characters', 'f'.repeat(65)],
        ['a space', `${REQUEST_ID} canary`],
        ['a dot', 'abc.def'],
        ['a slash', 'abc/def'],
        ['a line break', 'abc\ncanary'],
        ['a letter outside ASCII', 'ïd'],
    ])('is null for an id with %s, in the header or in the body, and the summary carries none', async (_label, id) => {
        const {requestIdOf, apiFailureSummary} = await apiErrorConsole();

        for (const failure of [answered(500, {}, {headers: {'x-request-id': id}}), answered(500, {request_id: id})]) {
            expect(requestIdOf(failure)).toBeNull();
            expect(apiFailureSummary(failure)?.request_id ?? null, 'the summary carries no request_id').toBeNull();
        }
    });

    // red until H-60
    it('is null for a request_id that is not a string, and for what is not a failure', async () => {
        const {requestIdOf} = await apiErrorConsole();

        for (const value of [42, null, [REQUEST_ID], {id: REQUEST_ID}]) expect(requestIdOf(answered(500, {request_id: value})), `request_id ${JSON.stringify(value)}`).toBeNull();
        for (const value of [null, undefined, REQUEST_ID, {}]) expect(requestIdOf(value), String(value)).toBeNull();
    });
});

describe('reportApiFailure — never throws', () => {
    // red until H-60
    it('takes junk and hostile objects without throwing, at either level and at its own', async () => {
        const {reportApiFailure} = await apiErrorConsole();
        const revocable = Proxy.revocable({}, {});
        revocable.revoke();
        const hostile = {
            get isAxiosError(): boolean {
                throw new Error('a getter that throws');
            },
        };
        const withoutConfig = new AxiosError(SECRET.message, AxiosError.ERR_BAD_RESPONSE, undefined, {}, {status: 500, statusText: '500', headers: {}, data: {}} as AxiosResponse);
        const junk: Array<[label: string, value: unknown]> = [
            ['null', null],
            ['a string', 'Request failed'],
            ['an object without config', {response: {status: 500}}],
            ['an object flagged isAxiosError and nothing else', {isAxiosError: true}],
            ['an Axios error without its config', withoutConfig],
            ['an Axios error whose URL does not parse', answered(500, {}, {method: 'get', url: 'http://['})],
            ['a ZodiosError with neither config nor cause', new ZodiosError(SECRET.message)],
            ['an object whose getter throws', hostile],
            ['a revoked proxy', revocable.proxy],
        ];

        for (const [label, value] of junk) {
            expect(() => reportApiFailure(value), `${label}, at the module's level`).not.toThrow();
            for (const level of ['error', 'debug'] as const) expect(() => reportApiFailure(value, level), `${label}, at ${level}`).not.toThrow();
        }
    });
});

describe('through the real client (zodios-client.ts)', () => {
    // red until H-60: the response interceptor reports nothing
    it('the response interceptor reports a 500 once, its path without the query string', async () => {
        const failure = await rejection(axiosInstance.get(`/api/v1/h60/probe?token=${SECRET.queryToken}`, {adapter: answering(500, {detail: SECRET.detailSentence, request_id: REQUEST_ID, error_type: 'KeyError'}, {'x-request-id': REQUEST_ID})}));

        expect((failure as AxiosError).response?.status, 'Barrier: the 500 reached the caller').toBe(500);
        expectLine('500 GET /api/v1/h60/probe', {request_id: REQUEST_ID, error_type: 'KeyError'});
    });

    // red until H-60
    it('the response interceptor follows the console level: a 404 prints at debug, and not at error', async () => {
        const {setApiConsoleLevel} = await apiErrorConsole();
        const notFoundThroughTheClient = () => rejection(axiosInstance.get('/api/v1/assets/999999', {adapter: answering(404, {detail: {code: 'asset_not_found', message: SECRET.detailMessage}}, {'x-request-id': REQUEST_ID})}));

        setApiConsoleLevel('debug');
        await notFoundThroughTheClient();
        expectLine('404 GET /api/v1/assets/999999', {code: 'asset_not_found', request_id: REQUEST_ID});

        clearConsole();
        setApiConsoleLevel('error');
        await notFoundThroughTheClient();
        expect(consoleCalls(), 'at error, a 404 prints nothing').toEqual([]);
    });

    // red until H-60 (amendment of 19/10)
    it('a request its AbortController canceled is not reported, at either level', async () => {
        const {setApiConsoleLevel} = await apiErrorConsole();
        await rejection(axiosInstance.get('/api/v1/assets', {adapter: answering(503, {detail: 'Service Unavailable'})}));
        expect(consoleCalls().length, 'Barrier: the interceptor reports, and the capture sees it').toBe(1);
        clearConsole();

        for (const level of ['debug', 'error'] as const) {
            setApiConsoleLevel(level);
            const controller = new AbortController();
            controller.abort();
            const canceled = await rejection(axiosInstance.get('/api/v1/assets', {signal: controller.signal, adapter: answering(200, {})}));
            expect(isCancel(canceled), `premise: axios rejected the request as canceled (${level})`).toBe(true);
        }

        expect(consoleCalls(), 'an abort prints nothing').toEqual([]);
    });

    // red until H-60: the plugin reports nothing
    it('a zodiosApi call answered 200 with a body that breaks its schema rejects with a ZodiosError, reported once as a schema mismatch', async () => {
        const refusal = await rejection(zodiosApi.get_instance_config_api_v1_system_instance_get({adapter: answering(200, BROKEN_INSTANCE, {'x-request-id': REQUEST_ID})}));

        expect(refusal, 'the call still rejects with the ZodiosError').toBeInstanceOf(ZodiosError);
        expect((refusal as ZodiosError).message, 'premise: its message quotes the body it refused').toContain('canary-profile');
        expect(expectLineHead('schema GET /api/v1/system/instance').schema_issues, 'the issue, as path:code').toContain('profile:invalid_enum_value');
        expectNoCanaryPrinted(['profile:invalid_enum_value']);
    });

    // red until H-60: the plugin under that name is still Zodios's own, which reports nothing
    it("the plugin named zod-validation is the one that reports, and the only one: it replaced Zodios's own, at its position", async () => {
        const named = pluginsOfEveryEndpoint().flatMap((plugin, index) => (plugin !== undefined && plugin.name === 'zod-validation' ? [{plugin, index}] : []));
        expect(
            named.map(({index}) => index),
            'one plugin named zod-validation, first, where Zodios registers its own',
        ).toEqual([0]);
        const [{plugin}] = named;
        expect(typeof plugin.response, 'it validates the responses').toBe('function');

        const refusal = await rejection(plugin.response!(zodiosApi.api as unknown as PluginApi, {method: 'get', url: '/api/v1/system/instance'} as unknown as PluginConfig, jsonResponse(200, BROKEN_INSTANCE)));

        expect(refusal, 'it raises the ZodiosError of the validation it delegates to').toBeInstanceOf(ZodiosError);
        expect(expectLineHead('schema GET /api/v1/system/instance').schema_issues, 'and reports it').toContain('profile:invalid_enum_value');
    });

    // red until H-60
    it('a zodiosApi call answered 200 with a body that matches prints nothing, even at debug, and resolves to the parsed value as before', async () => {
        const {setApiConsoleLevel} = await apiErrorConsole();
        setApiConsoleLevel('debug');
        await rejection(zodiosApi.get_instance_config_api_v1_system_instance_get({adapter: answering(200, BROKEN_INSTANCE)}));
        expectLineHead('schema GET /api/v1/system/instance');
        clearConsole();
        const parsed = schemas.InstanceConfigResponse.parse(JSON.parse(JSON.stringify(MATCHING_INSTANCE)));
        expect(parsed, 'premise: parsing changes this body, so the parsed value and the raw one differ').not.toEqual(MATCHING_INSTANCE);

        const answer = await zodiosApi.get_instance_config_api_v1_system_instance_get({adapter: answering(200, MATCHING_INSTANCE, {'x-request-id': REQUEST_ID})});

        expect(answer, 'the parsed value, as before (transform: true)').toEqual(parsed);
        expect(consoleCalls(), 'a success prints nothing').toEqual([]);
    });

    // red until H-60
    it('a zodiosApi call answered 503 is reported once, by the interceptor: the plugin reports a schema mismatch only', async () => {
        const failure = await rejection(zodiosApi.get_instance_config_api_v1_system_instance_get({adapter: answering(503, {detail: SECRET.detailSentence, request_id: REQUEST_ID, error_type: 'OperationalError'}, {'x-request-id': REQUEST_ID})}));

        expect([isAxiosError(failure), (failure as AxiosError).response?.status], 'Barrier: the caller received the AxiosError of the 503').toEqual([true, 503]);
        expectLine('503 GET /api/v1/system/instance', {request_id: REQUEST_ID, error_type: 'OperationalError'});
    });

    // red until H-60: nothing is printed, so the line and the sweep's barrier fail
    it('shows none of what the request carried, nor what the response held beside its fields', async () => {
        const transport = answering(503, SNAPSHOT_BODY, {'x-request-id': REQUEST_ID, 'set-cookie': `lf_session=${SECRET.setCookie}`, 'x-libre-canary': SECRET.responseHeader});
        const credentials = {Authorization: `Bearer ${SECRET.bearer}`, Cookie: `lf_session=${SECRET.cookie}`};

        const failure = await rejection(axiosInstance.post(`/api/v1/h60/probe?token=${SECRET.queryToken}`, {username: 'h60-user', password: SECRET.password}, {headers: credentials, params: {token: SECRET.param}, adapter: transport}));

        const carried = stringsIn([failure]);
        for (const secret of [SECRET.password, SECRET.bearer, SECRET.cookie, SECRET.queryToken, SECRET.param, SECRET.setCookie, SECRET.responseHeader, SECRET.message, SECRET.detailMessage]) {
            expect(
                carried.some((text) => text.includes(secret)),
                `premise: the failure the interceptor received carries ${secret}`,
            ).toBe(true);
        }
        expectLine('503 POST /api/v1/h60/probe', {code: 'snapshot_source_failure', reason_code: 'x', component_id: 'portfolio.technical_prices', request_id: REQUEST_ID, error_type: 'KeyError'});
        expectNoCanaryPrinted([REQUEST_ID, '/api/v1/h60/probe']);
    });
});
