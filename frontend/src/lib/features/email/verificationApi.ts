/**
 * The verification of an email address at sign-up (workstream E, lot E5; developer decision 44): spend the link of
 * the verification email, or ask for it again with the credentials of the sign-in.
 *
 * Thin wrappers over the generated client, so that the pages and their tests share one seam.
 */
import {zodiosApi} from '$lib/api';
import {isInstanceBlockedError} from '$lib/features/instance/instanceBlock.svelte';
import {refusalBody, refusalDetail, refusalStatus, retryAfterOf} from './emailApi';

/** Why a verification link was refused (400 `TOKEN_INVALID`): the status of its token. */
export type VerificationLinkRefusal = 'expired' | 'consumed' | 'revoked' | 'unknown';

const LINK_REFUSALS: ReadonlySet<string> = new Set<VerificationLinkRefusal>(['expired', 'consumed', 'revoked', 'unknown']);

/** Spend a verification link: its account is active now; its username fills in the sign-in. */
export async function confirmEmailVerification(token: string): Promise<{username: string}> {
    const answer = await zodiosApi.confirm_email_verification_api_v1_email_verification_confirm_post({token});
    return {username: answer.username};
}

/** Why the page cannot use the link, or null for any other failure (no answer, a server error), which may be tried
 * again: the status of its token (400 `TOKEN_INVALID`), or `blocked` while the hosting provider blocks the instance —
 * the 423 `instance_blocked` a signed-in browser gets (workstream H's `isInstanceBlockedError`), or the 401 an anonymous
 * one gets, the only 401 of this public route (lot E-10, from H's review of A7b). */
export function readLinkRefusal(error: unknown): VerificationLinkRefusal | 'blocked' | null {
    const status = refusalStatus(error);
    if (status === 401 || isInstanceBlockedError(status, refusalBody(error))) return 'blocked';
    const fields = refusalDetail(error);
    if (status !== 400 || fields === null || fields.error_code !== 'TOKEN_INVALID') return null;
    return typeof fields.status === 'string' && LINK_REFUSALS.has(fields.status) ? (fields.status as VerificationLinkRefusal) : 'unknown';
}

/** Ask again for the verification link of an account waiting for it; returns the language of the email. */
export async function resendEmailVerification(username: string, password: string): Promise<string> {
    const answer = await zodiosApi.resend_email_verification_api_v1_email_verification_resend_post({username, password});
    return answer.language;
}

/** Why the link could not be sent again. */
export interface ResendFailure {
    /** `INVALID_CREDENTIALS` (the route's own 401), `INSTANCE_BLOCKED` (any other 401, or the 423 `instance_blocked`),
     * the API's `error_code`, or `UNKNOWN` without an answer. */
    errorCode: string;
    /** `EMAIL_RATE_LIMITED`: seconds until a new request may go. */
    retryAfter?: number;
}

/** Why «send the link again» failed. The route answers its own 401 with `INVALID_CREDENTIALS`; it is a public route
 * outside the block's allow-list, so any other 401 is the one an anonymous caller gets while the hosting provider blocks
 * the instance, and the 423 `instance_blocked` the one a signed-in browser gets (workstream H; lot E-11). */
export function readResendFailure(error: unknown): ResendFailure {
    const status = refusalStatus(error);
    const fields = refusalDetail(error);
    if (status === 401) return {errorCode: fields?.error_code === 'INVALID_CREDENTIALS' ? 'INVALID_CREDENTIALS' : 'INSTANCE_BLOCKED'};
    if (isInstanceBlockedError(status, refusalBody(error))) return {errorCode: 'INSTANCE_BLOCKED'};
    if (fields === null) return {errorCode: 'UNKNOWN'};
    return {errorCode: typeof fields.error_code === 'string' && fields.error_code ? fields.error_code : 'UNKNOWN', retryAfter: retryAfterOf(fields)};
}
