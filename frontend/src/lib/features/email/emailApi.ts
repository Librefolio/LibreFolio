/**
 * The email administration API (workstream E, lots E2 and E3): the state of the instance's email, the test email, and
 * the nonce of the check of the emailed links' base.
 *
 * Thin wrappers over the generated client, so that the Email tab and its tests share one seam. The SMTP configuration
 * never reaches the browser: `GET /email/status` answers with the state, the problem and the variable at fault, the
 * configuration checks, the hourly budget and the links' base only.
 */
import {isAxiosError} from 'axios';
import type {z} from 'zod';
import {ApiError, zodiosApi} from '$lib/api';
import type {schemas} from '$lib/api/generated';

export type EmailCheck = z.infer<typeof schemas.EmailCheckRead>;
export type EmailBudget = z.infer<typeof schemas.EmailBudgetRead>;
export type EmailTestResult = z.infer<typeof schemas.EmailTestResponse>;

/**
 * The state of the instance's email, as the tab reads it. The generated type of an optional field is wider than its
 * runtime schema (`string | null` also admits an array there), so `fetchEmailStatus()` narrows each one here, once.
 */
export interface EmailStatus {
    state: z.infer<typeof schemas.EmailStatusResponse>['state'];
    /** `invalid` only: the code of the problem. */
    problem: string | null;
    /** `invalid` only: the variable at fault. */
    variable: string | null;
    checks: EmailCheck[];
    /** `ready` only: the hourly budget. */
    budget: EmailBudget | null;
    /** Whether emails can carry links (`LIBREFOLIO_PUBLIC_URL`). */
    links: EmailLinks;
}

/** Whether emails can carry links: every one starts with `base`, `LIBREFOLIO_PUBLIC_URL` (developer decision 45). */
export interface EmailLinks {
    /** True only with a `base`. */
    ready: boolean;
    /** The base of every emailed link; null when not ready. */
    base: string | null;
    /** Why no link can be emailed: `PUBLIC_URL_MISSING` or `PUBLIC_URL_INVALID`. */
    problem: string | null;
}

function textOrNull(value: unknown): string | null {
    return typeof value === 'string' && value ? value : null;
}

function budgetOrNull(value: unknown): EmailBudget | null {
    return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as EmailBudget) : null;
}

/** `links` as the tab trusts it: ready only with a base, never a base when not ready; not ready when absent. */
function linksOf(value: unknown): EmailLinks {
    const fields = typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
    const base = textOrNull(fields.base);
    const ready = fields.ready === true && base !== null;
    return {ready, base: ready ? base : null, problem: textOrNull(fields.problem)};
}

export async function fetchEmailStatus(): Promise<EmailStatus> {
    const answer = await zodiosApi.get_email_status_api_v1_email_status_get();
    return {
        state: answer.state,
        problem: textOrNull(answer.problem),
        variable: textOrNull(answer.variable),
        checks: answer.checks ?? [],
        budget: budgetOrNull(answer.budget),
        links: linksOf(answer.links),
    };
}

/** A nonce of this instance for the address check (`POST /users/address-probe`, administrators only). */
export async function issueProbeNonce(): Promise<string> {
    const issued = await zodiosApi.issue_address_probe_api_v1_users_address_probe_post(undefined);
    return issued.nonce;
}

export function sendTestEmail(): Promise<EmailTestResult> {
    return zodiosApi.send_test_api_v1_email_test_post(undefined);
}

/** Why a test email failed, read from the API's `detail`: its code and what goes with it. */
export interface EmailTestFailure {
    /** `EMAIL_UNAVAILABLE`, `EMAIL_RATE_LIMITED`, `EMAIL_DELIVERY_FAILED`, `EMAIL_RECIPIENT_INVALID`, or `UNKNOWN`. */
    errorCode: string;
    /** `EMAIL_UNAVAILABLE`: the problem of the configuration. */
    problem?: string;
    /** `EMAIL_DELIVERY_FAILED`: why the SMTP server did not take the message. */
    smtpCode?: string;
    /** `EMAIL_RATE_LIMITED`: seconds until the next email fits. */
    retryAfter?: number;
}

function text(value: unknown): string | undefined {
    return typeof value === 'string' && value ? value : undefined;
}

/** The body of a refused request: the generated client rejects with axios's own error (`AxiosError`, whose response
 * carries it); an `ApiError` carries it in `data`. */
export function refusalBody(error: unknown): unknown {
    if (isAxiosError(error)) return error.response?.data;
    return error instanceof ApiError ? error.data : undefined;
}

/** The HTTP status of a refused request; undefined for a failure without an answer (network, timeout). */
export function refusalStatus(error: unknown): number | undefined {
    if (isAxiosError(error)) return error.response?.status;
    return error instanceof ApiError ? error.status : undefined;
}

/** The `detail` object of a refusal, or null when the answer has none (a network error, a plain-text `detail`). */
export function refusalDetail(error: unknown): Record<string, unknown> | null {
    const body = refusalBody(error);
    const detail = typeof body === 'object' && body !== null ? (body as {detail?: unknown}).detail : undefined;
    return typeof detail === 'object' && detail !== null && !Array.isArray(detail) ? (detail as Record<string, unknown>) : null;
}

/** Seconds from a refusal's `retry_after`, when it is a finite number. */
export function retryAfterOf(fields: Record<string, unknown>): number | undefined {
    return typeof fields.retry_after === 'number' && Number.isFinite(fields.retry_after) ? fields.retry_after : undefined;
}

/** The failure of `sendTestEmail()`: the fields of the API's `detail`; `UNKNOWN` when there is no such `detail` (a
 * network error, an answer without a `detail` object). */
export function readTestFailure(error: unknown): EmailTestFailure {
    const fields = refusalDetail(error);
    if (fields === null) return {errorCode: 'UNKNOWN'};
    return {errorCode: text(fields.error_code) ?? 'UNKNOWN', problem: text(fields.problem), smtpCode: text(fields.smtp_code), retryAfter: retryAfterOf(fields)};
}
