/**
 * «Forgot password» by email (workstream E, lot E4): ask for a reset link with a username or an email address,
 * without signing in (`POST /email/password-reset`).
 *
 * The answer never says whether an account matches: 202, the same for everyone. A thin seam over the generated client.
 */
import {zodiosApi} from '$lib/api';
import {refusalDetail, refusalStatus, retryAfterOf} from './emailApi';

export async function requestPasswordResetEmail(identifier: string): Promise<void> {
    await zodiosApi.request_password_reset_email_api_v1_email_password_reset_post({identifier});
}

/** Why the request was refused. */
export interface ForgotFailure {
    /** `EMAIL_UNAVAILABLE`, `EMAIL_LINKS_UNAVAILABLE`, `EMAIL_RATE_LIMITED`, `INVALID` (422) or `UNKNOWN`. */
    errorCode: string;
    /** `EMAIL_RATE_LIMITED`: seconds until a new request may go. */
    retryAfter?: number;
}

export function readForgotFailure(error: unknown): ForgotFailure {
    if (refusalStatus(error) === 422) return {errorCode: 'INVALID'};
    const fields = refusalDetail(error);
    if (fields === null) return {errorCode: 'UNKNOWN'};
    return {errorCode: typeof fields.error_code === 'string' && fields.error_code ? fields.error_code : 'UNKNOWN', retryAfter: retryAfterOf(fields)};
}
