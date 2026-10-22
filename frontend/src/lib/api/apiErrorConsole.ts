/**
 * The browser console of failed API calls (lot H-60): one line per unexpected failure, in production too.
 *
 * The developer's rule (19/10/2026): when something fails, the useful information is printed, in the server log and in
 * the browser console. `zodios-client.ts` calls `reportApiFailure` from the Axios response interceptor (an HTTP error,
 * a network failure, a timeout) and from its `zod-validation` plugin (an answer that breaks its schema).
 *
 * A line holds these and nothing else: the status (`network` without an answer, `schema` for a schema mismatch), the
 * method, the path without its query string (a query can carry a token), the problem's `code`, `reason_code` and
 * `component_id`, the `request_id` that finds the request in the server log, the `error_type` of a 5xx, the Axios code
 * of a network failure, the paths of the schema issues. Never the request body, a header but `X-Request-Id`, the response
 * body beyond those fields (no `detail` text, no 422 `input`), `error.message` (a `ZodiosError` message embeds the whole
 * answer), a value Zod received.
 *
 * How much is written follows the instance: `client_log_level` of `GET /system/instance`, from the backend's
 * `LOG_LEVEL`. `error`: server errors, network failures, schema mismatches. `debug`: every 4xx too.
 */

import {isAxiosError} from 'axios';
import {ZodiosError} from '@zodios/core';

export type ApiConsoleLevel = 'error' | 'debug';

export interface ApiFailureSummary {
    status: number | null;
    method: string;
    path: string;
    code?: string;
    reason_code?: string;
    component_id?: string;
    request_id?: string;
    error_type?: string;
    network?: string;
    schema_issues?: string[];
}

type Loose = Record<string, unknown>;

const REQUEST_ID = /^[A-Za-z0-9_-]{1,64}$/;
const CODE = /^[A-Za-z0-9_.:-]{1,100}$/;
const ERROR_TYPE = /^[A-Za-z_][A-Za-z0-9_]{0,99}$/;
const SEGMENT = /^[A-Za-z_][A-Za-z0-9_]{0,63}$/;
const MAX_ISSUES = 10;

let consoleLevel: ApiConsoleLevel = 'error';

/** Set how much the console gets: `instanceConfig` calls it with the instance's `client_log_level`. */
export function setApiConsoleLevel(level: ApiConsoleLevel): void {
    consoleLevel = level === 'debug' ? 'debug' : 'error';
}

/** How much the console gets: `error` until the instance says otherwise. */
export function apiConsoleLevel(): ApiConsoleLevel {
    return consoleLevel;
}

function loose(value: unknown): Loose | null {
    return typeof value === 'object' && value !== null ? (value as Loose) : null;
}

function matching(value: unknown, pattern: RegExp): string | undefined {
    return typeof value === 'string' && pattern.test(value) ? value : undefined;
}

function header(headers: unknown, name: string): unknown {
    const found = loose(headers);
    if (!found) return undefined;
    if (typeof found.get === 'function') {
        try {
            const value = (found.get as (key: string) => unknown).call(headers, name);
            if (value !== undefined && value !== null) return value;
        } catch {
            // a headers object that cannot answer: read it as a plain object
        }
    }
    return found[name];
}

/**
 * The request id of a failed call: the `X-Request-Id` of its answer, else the `request_id` of its body; null when there
 * is none, or when it is not an id (1–64 characters among letters, digits, `_` and `-`). For the messages that show it
 * to the user (D3).
 */
export function requestIdOf(error: unknown): string | null {
    const response = loose(loose(error)?.response);
    if (!response) return null;
    return matching(header(response.headers, 'x-request-id'), REQUEST_ID) ?? matching(loose(response.data)?.request_id, REQUEST_ID) ?? null;
}

function methodOf(method: unknown): string {
    return typeof method === 'string' && method.length > 0 && method.length <= 16 ? method.toUpperCase() : 'GET';
}

/** The path of a request URL: no query string (it can carry a token), no fragment, no origin. */
export function requestPath(url: unknown): string {
    if (typeof url !== 'string' || url.length === 0) return '?';
    const bare = url.split('#', 1)[0].split('?', 1)[0];
    if (/^[a-z][a-z0-9+.-]*:\/\//i.test(bare)) {
        try {
            return new URL(bare).pathname;
        } catch {
            return '?';
        }
    }
    return bare || '/';
}

function issueOf(issue: unknown): string {
    const found = loose(issue);
    const path = Array.isArray(found?.path) ? found.path : [];
    const segments = path.map((segment) => (typeof segment === 'number' && Number.isInteger(segment) ? String(segment) : (matching(segment, SEGMENT) ?? '*')));
    return `${segments.join('.')}:${matching(found?.code, CODE) ?? '?'}`;
}

/**
 * What can be said of a failed API call without a word of its data, or null when `error` is not one (and for a canceled
 * request: an abort is not a failure).
 */
export function apiFailureSummary(error: unknown): ApiFailureSummary | null {
    if (error instanceof ZodiosError) {
        const config = loose(error.config);
        const issues = loose(error.cause)?.issues;
        return {
            status: null,
            method: methodOf(config?.method),
            path: requestPath(config?.url),
            schema_issues: Array.isArray(issues) ? issues.slice(0, MAX_ISSUES).map(issueOf) : [],
        };
    }
    if (!isAxiosError(error) || error.code === 'ERR_CANCELED') return null;
    const response = error.response;
    const summary: ApiFailureSummary = {status: response?.status ?? null, method: methodOf(error.config?.method), path: requestPath(error.config?.url)};
    if (!response) {
        const network = matching(error.code, CODE);
        if (network) summary.network = network;
        return summary;
    }
    const body = loose(response.data);
    const detail = loose(body?.detail);
    if (detail) {
        const code = matching(detail.code, CODE) ?? matching(detail.error_code, CODE);
        const reasonCode = matching(detail.reason_code, CODE);
        const componentId = matching(detail.component_id, CODE);
        if (code) summary.code = code;
        if (reasonCode) summary.reason_code = reasonCode;
        if (componentId) summary.component_id = componentId;
    }
    const requestId = requestIdOf(error);
    if (requestId) summary.request_id = requestId;
    const errorType = matching(body?.error_type, ERROR_TYPE);
    if (errorType) summary.error_type = errorType;
    return summary;
}

function reportable(summary: ApiFailureSummary, level: ApiConsoleLevel): boolean {
    if (summary.schema_issues !== undefined || summary.status === null || summary.status >= 500) return true;
    return level === 'debug' && summary.status >= 400;
}

/** Write one console line for a failed API call when its level asks for it (see the module's comment); never throws. */
export function reportApiFailure(error: unknown, level: ApiConsoleLevel = consoleLevel): void {
    try {
        const summary = apiFailureSummary(error);
        if (!summary || !reportable(summary, level)) return;
        const {status, method, path, ...fields} = summary;
        const head = summary.schema_issues !== undefined ? 'schema' : (status ?? 'network');
        console.error('[API]', `${head} ${method} ${path}`, fields);
    } catch {
        // the console line is a help, never a new failure
    }
}
