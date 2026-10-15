/**
 * The verification of an email address at sign-up (workstream E, lot E5; developer decision 44): spend the link of
 * the verification email, or ask for it again with the credentials of the sign-in.
 *
 * Thin wrappers over the generated client, so that the pages and their tests share one seam.
 */
import {zodiosApi} from '$lib/api';
import {refusalDetail, refusalStatus, retryAfterOf} from './emailApi';

/** Why a verification link was refused (400 `TOKEN_INVALID`): the status of its token. */
export type VerificationLinkRefusal = 'expired' | 'consumed' | 'revoked' | 'unknown';

const LINK_REFUSALS: ReadonlySet<string> = new Set<VerificationLinkRefusal>(['expired', 'consumed', 'revoked', 'unknown']);

/** Spend a verification link: its account is active now; its username fills in the sign-in. */
export async function confirmEmailVerification(token: string): Promise<{username: string}> {
    const answer = await zodiosApi.confirm_email_verification_api_v1_email_verification_confirm_post({token});
    return {username: answer.username};
}

/** The status of a refused link, or null for any other failure (no answer, a server error), which may be tried again. */
export function readLinkRefusal(error: unknown): VerificationLinkRefusal | null {
    const fields = refusalDetail(error);
    if (refusalStatus(error) !== 400 || fields === null || fields.error_code !== 'TOKEN_INVALID') return null;
    return typeof fields.status === 'string' && LINK_REFUSALS.has(fields.status) ? (fields.status as VerificationLinkRefusal) : 'unknown';
}

/** Ask again for the verification link of an account waiting for it; returns the language of the email. */
export async function resendEmailVerification(username: string, password: string): Promise<string> {
    const answer = await zodiosApi.resend_email_verification_api_v1_email_verification_resend_post({username, password});
    return answer.language;
}

/** Why the link could not be sent again. */
export interface ResendFailure {
    /** `INVALID_CREDENTIALS` (401), the API's `error_code`, or `UNKNOWN` without an answer. */
    errorCode: string;
    /** `EMAIL_RATE_LIMITED`: seconds until a new request may go. */
    retryAfter?: number;
}

export function readResendFailure(error: unknown): ResendFailure {
    if (refusalStatus(error) === 401) return {errorCode: 'INVALID_CREDENTIALS'};
    const fields = refusalDetail(error);
    if (fields === null) return {errorCode: 'UNKNOWN'};
    return {errorCode: typeof fields.error_code === 'string' && fields.error_code ? fields.error_code : 'UNKNOWN', retryAfter: retryAfterOf(fields)};
}
