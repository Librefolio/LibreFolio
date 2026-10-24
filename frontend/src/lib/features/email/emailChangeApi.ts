/**
 * The change of the paying administrator's email address, started by the hosting provider (lot A5-1b): spend the link
 * the instance emailed to the NEW address.
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
