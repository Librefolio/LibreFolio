/**
 * The line under a dead setup link, and the support link beside it (A5-6).
 *
 * A setup link that expired on a managed instance is not the end of the road: the hosting provider sends the next one
 * by itself. The page says it neutrally, so the line covers an automatic resend and a manual one: «If you did not
 * receive a new one by email, contact support.» (`auth.setup.expiredManagedHint`, the one place to change it), with a
 * link to the instance's support address (`support_url`, `LIBREFOLIO_SUPPORT_URL`) when it has one.
 *
 * Every other case — a used, withdrawn or unknown link, no token, a self-hosted instance — keeps the generic line.
 */
import {supportChannel} from '$lib/components/assets/assetSearchReport';

export interface SetupLinkNotice {
    /** The i18n key of the line under the message. */
    hintKey: string;
    /** Where the support link goes, or null for no link. */
    supportHref: string | null;
}

const GENERIC_HINT = 'auth.setup.newLinkHint';

/** The href of the instance's support address: a mailto or an http(s) page, nothing else (never a GitHub page). */
function supportHref(value: string | null | undefined): string | null {
    const channel = supportChannel(value, {githubFallback: false});
    if (channel === null) return null;
    return channel.kind === 'mailto' ? `mailto:${channel.address}` : channel.url;
}

/** What `/setup` shows under a link that cannot be used: `status` is the link's, `managed` whether the server confirmed a managed instance (`managedConfirmed()`: the profile is compared in `profile.ts` only). */
export function setupLinkNotice(status: string, managed: boolean, supportUrl: string | null | undefined): SetupLinkNotice {
    if (status !== 'expired' || !managed) return {hintKey: GENERIC_HINT, supportHref: null};
    return {hintKey: 'auth.setup.expiredManagedHint', supportHref: supportHref(supportUrl)};
}
