/**
 * A change of email address, confirmed from the NEW address: spend the link the instance emailed there. Two flows use it:
 * the paying administrator's, started by the hosting provider (lot A5-1b), and the one of any account that asked for a
 * new address from its profile (release 1.4, project 71). The route tells them apart, not this wrapper.
 *
 * A thin wrapper over the generated client, so that the page and its tests share one seam. The refusals are the
 * verification link's (`readLinkRefusal` of `verificationApi.ts`), plus one of this page alone: a link asked from Profile
 * confirms only with the session of its account (decision D10), so the page must also be able to say «sign in».
 */
import {zodiosApi} from '$lib/api';
import {refusalDetail, refusalStatus} from './emailApi';
import type {VerifyPageStatus} from './emailText';
import {readLinkRefusal, type VerificationLinkRefusal} from './verificationApi';

/** What the change page shows: the statuses of a verification link's page, and `signin` (D10). Its own type, so that
 * `/verify-email`, which shares `VerifyPageStatus`, needs no text for a state it never reaches. */
export type EmailChangePageStatus = VerifyPageStatus | 'signin';

/** Spend the link: the address of the account is the new one now; its username fills nothing, the sessions have ended. */
export async function confirmOwnerEmailChange(token: string): Promise<{username: string}> {
    const answer = await zodiosApi.confirm_owner_email_change_api_v1_email_email_change_confirm_post({token});
    return {username: answer.username};
}

/** Why the change page cannot use the link, or null for a failure that may be tried again. `signin` only for the 403
 * whose `detail.error_code` is `EMAIL_CHANGE_SIGN_IN_REQUIRED` — a live link of a change asked from Profile, clicked
 * without the session of its account; any other answer reads as on `/verify-email` (a 401 or a 423 `instance_blocked`
 * is the instance's block, a 400 `TOKEN_INVALID` the token's status). */
export function readEmailChangeRefusal(error: unknown): VerificationLinkRefusal | 'blocked' | 'signin' | null {
    if (refusalStatus(error) === 403 && refusalDetail(error)?.error_code === 'EMAIL_CHANGE_SIGN_IN_REQUIRED') return 'signin';
    return readLinkRefusal(error);
}

/** End the session of this browser, whoever it is, before the sign-in: with a live session the sign-in page jumps to its
 * `redirect` at once, so another account signed in here would bring the page back to the same 403. `POST /auth/logout`
 * only clears the cookie; it never navigates, unlike the store's `auth.logout()`, which would lose the way back. A
 * failure is no reason to stay: without a session there was nothing to end. */
export async function endSessionBeforeSignIn(): Promise<void> {
    try {
        await zodiosApi.logout_api_v1_auth_logout_post(undefined);
    } catch {
        // No session, or no answer: the sign-in page reads the session again by itself.
    }
}
