/**
 * A change of email address, confirmed from the NEW address: spend the link the instance emailed there. Two flows use it:
 * the paying administrator's, started by the hosting provider (lot A5-1b), and the one of any account that asked for a
 * new address from its profile (release 1.4, project 71). The route tells them apart, not this wrapper.
 *
 * A thin wrapper over the generated client, so that the page and its tests share one seam. The refusals are the
 * verification link's: `readLinkRefusal` of `verificationApi.ts` reads them.
 */
import {zodiosApi} from '$lib/api';

/** Spend the link: the address of the account is the new one now; its username fills nothing, the sessions have ended. */
export async function confirmOwnerEmailChange(token: string): Promise<{username: string}> {
    const answer = await zodiosApi.confirm_owner_email_change_api_v1_email_email_change_confirm_post({token});
    return {username: answer.username};
}

export {readLinkRefusal} from './verificationApi';
