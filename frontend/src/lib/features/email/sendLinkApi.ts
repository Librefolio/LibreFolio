/**
 * «Send by email» next to a shared link (workstream E, lot E4): an administrator emails the invitation or the
 * password-reset link that the share dialog shows (`POST /email/links`).
 *
 * The email's link is built by the backend from `LIBREFOLIO_PUBLIC_URL` alone (developer decision 45), whatever address
 * the dialog shows: only the token travels from here. A thin seam over the generated client, plus what the action needs
 * to know: the token of a link, and whether emails with a link can go out.
 */
import {zodiosApi} from '$lib/api';
import type {SupportedLocale} from '$lib/i18n';
import type {LinkPurpose} from '$lib/features/auth/linkToken';
import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {refusalDetail, refusalStatus, retryAfterOf} from './emailApi';

/** The token of a shared link, from its `#token=` fragment; null when the link has none. */
export function tokenFromLink(link: string): string | null {
    const hash = link.indexOf('#');
    if (hash < 0) return null;
    const token = new URLSearchParams(link.slice(hash + 1)).get('token');
    return token ? token : null;
}

/** Whether emails with a link can go out now (`GET /system/instance` → `email.links`): the action shows only then. */
export function sendByEmailVisible(): boolean {
    return instanceConfig.config.email?.links === true;
}

export interface LinkEmailRequest {
    purpose: LinkPurpose;
    token: string;
    /** An invitation only: where to send it; without it, the address written in the invitation. */
    to?: string;
    /** An invitation only: the language of the email; without it, the instance's default language (decision N69). */
    language?: SupportedLocale;
}

export interface LinkEmailSent {
    to: string;
    language: string;
}

export async function sendLinkByEmail({purpose, token, to, language}: LinkEmailRequest): Promise<LinkEmailSent> {
    const answer = await zodiosApi.send_link_api_v1_email_links_post({purpose, token, ...(to ? {to} : {}), ...(language ? {language} : {})});
    return {to: answer.to, language: answer.language};
}

/** Why a link could not be emailed, read from the API's `detail`. */
export interface LinkSendFailure {
    /** The API's `error_code`; `EMAIL_RECIPIENT_INVALID` for a 422 of the request's validation (the typed address); `UNKNOWN` without an answer. */
    errorCode: string;
    /** `EMAIL_DELIVERY_FAILED`: why the SMTP server did not take the message. */
    smtpCode?: string;
    /** `EMAIL_RATE_LIMITED`: seconds until an email fits again. */
    retryAfter?: number;
}

export function readLinkSendFailure(error: unknown): LinkSendFailure {
    const fields = refusalDetail(error);
    // A 422 without an error code is the request's own validation: the only field typed in the dialog is the address
    if (fields === null) return {errorCode: refusalStatus(error) === 422 ? 'EMAIL_RECIPIENT_INVALID' : 'UNKNOWN'};
    const code = typeof fields.error_code === 'string' && fields.error_code ? fields.error_code : 'UNKNOWN';
    const smtpCode = typeof fields.smtp_code === 'string' && fields.smtp_code ? fields.smtp_code : undefined;
    return {errorCode: code, smtpCode, retryAfter: retryAfterOf(fields)};
}
