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

/** What the change page shows: the statuses of a verification link's page, `signin` (D10) and `otheraccount` (the link
 * clicked with another account's session). Its own type, so that `/verify-email`, which shares `VerifyPageStatus`, needs no
 * text for a state it never reaches. */
export type EmailChangePageStatus = VerifyPageStatus | 'signin' | 'otheraccount';

/** What the page shows on opening a live link (lots E2, E3), read without spending it: `ready` for the click, `signin` (no
 * session of the account that asked), `otheraccount` (another account's session). A dead link is refused as its click
 * would be (`readEmailChangeRefusal`). The answer never names the account. */
export type EmailChangeLinkCheck = 'ready' | 'signin' | 'otheraccount';

/** Ask the server what the link's page shows, before any click: `POST /email/email-change/check`, which spends nothing. */
export async function checkEmailChangeLink(token: string): Promise<{status: EmailChangeLinkCheck; newEmail: string | null}> {
    const answer = await zodiosApi.check_email_change_link_api_v1_email_email_change_check_post({token});
    // The address the click would confirm comes only with `ready` (81 U46): the page shows it as a double check.
    return {status: answer.status === 'other_account' ? 'otheraccount' : answer.status, newEmail: answer.status === 'ready' ? (answer.new_email ?? null) : null};
}

/** Spend the link: the address of the account is the new one now. `sessionKept`: the browser that confirmed is still
 * signed in (a link asked from Profile, lot E1); false when every session ended (the owner's link): sign in again. */
export async function confirmOwnerEmailChange(token: string): Promise<{username: string; sessionKept: boolean}> {
    const answer = await zodiosApi.confirm_owner_email_change_api_v1_email_email_change_confirm_post({token});
    return {username: answer.username, sessionKept: answer.session_kept};
}

/** Why the change page cannot use the link, or null for a failure that may be tried again. `signin` only for the 403
 * whose `detail.error_code` is `EMAIL_CHANGE_SIGN_IN_REQUIRED` — a live link of a change asked from Profile, clicked
 * without a session — and `otheraccount` for `EMAIL_CHANGE_OTHER_ACCOUNT`, the same link clicked with another account's; any other answer reads as on `/verify-email` (a 401 or a 423 `instance_blocked`
 * is the instance's block, a 400 `TOKEN_INVALID` the token's status). */
export function readEmailChangeRefusal(error: unknown): VerificationLinkRefusal | 'blocked' | 'signin' | 'otheraccount' | null {
    if (refusalStatus(error) === 403) {
        const code = refusalDetail(error)?.error_code;
        if (code === 'EMAIL_CHANGE_SIGN_IN_REQUIRED') return 'signin';
        // Another account is signed in here: the server says only that the link is not for it, never whose it is.
        if (code === 'EMAIL_CHANGE_OTHER_ACCOUNT') return 'otheraccount';
    }
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
