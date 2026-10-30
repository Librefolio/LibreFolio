/**
 * Where a report to the instance's support goes, and the link that carries it (P20 for the asset search, FB-27 for the
 * checks and the interrupted restore).
 *
 * The report leaves from the user's own client, never from the server:
 * - the instance's support address is `mailto:` and one address → a `mailto:` link with the subject and the body;
 * - it is an http(s) page → the page opens with the report as `title` and `body` in its address, as for a GitHub
 *   issue (N61-form);
 * - it is not set, or not valid → with `githubFallback` (a self-hosted instance, a report that is safe to publish), a
 *   prefilled GitHub issue, public, that the user reviews before sending it; without it, no channel at all (N61): a
 *   public issue would publish what the report carries.
 *
 * `LIBREFOLIO_SUPPORT_URL` reaches the app through `GET /system/instance` (`support_url`), already validated by the
 * backend; `supportChannel` checks it again on the parsed address, so that nothing but http(s) and `mailto:` ever
 * becomes a link, and an address with a user name or a password counts as missing.
 */

/** Where the report goes. */
export type SupportChannel = {kind: 'mailto'; address: string} | {kind: 'page'; url: string} | {kind: 'github'; url: string};

/** A new issue in the project's repository: the channel when the instance names no support address. */
export const GITHUB_NEW_ISSUE_URL = 'https://github.com/Librefolio/LibreFolio/issues/new';

/** A report: a subject and a plain-text body, in English. */
export interface SupportReport {
    subject: string;
    body: string;
}

/** What the backend refuses in a mailto address (`config/platform.py`), checked again: `?` or `#` would add headers. */
const MAILTO_FORBIDDEN = /[\s?#%,;<>"/]/;

export interface SupportChannelOptions {
    /** Whether a missing or unusable address falls back to a new GitHub issue: on a self-hosted instance only (N61). */
    githubFallback: boolean;
}

/**
 * The channel for the instance's support address (`support_url`), checked again: a mailto with one address, or an
 * http(s) page without user info, given back normalized. Anything else counts as missing: a new GitHub issue with
 * `githubFallback`, otherwise null (no link).
 */
export function supportChannel(value: string | null | undefined, {githubFallback}: SupportChannelOptions): SupportChannel | null {
    const missing = (): SupportChannel | null => (githubFallback ? {kind: 'github', url: GITHUB_NEW_ISSUE_URL} : null);
    const raw = (value ?? '').trim();
    if (raw === '') return missing();
    if (/^mailto:/i.test(raw)) {
        const address = raw.slice('mailto:'.length);
        const [local, domain, ...rest] = address.split('@');
        if (MAILTO_FORBIDDEN.test(address) || rest.length > 0 || !local || !domain) return missing();
        return {kind: 'mailto', address};
    }
    let url: URL;
    try {
        url = new URL(raw);
    } catch {
        return missing();
    }
    // A user name or a password would be shown to every user and sent to the page: not a support address.
    if ((url.protocol !== 'http:' && url.protocol !== 'https:') || url.hostname === '' || url.username !== '' || url.password !== '') return missing();
    // The normalized absolute address: a spelling such as `https:host` would otherwise resolve, as an href, on this instance.
    return {kind: 'page', url: url.href};
}

/**
 * A support page with the report in its address (N61-form): `title` and `body`, encoded as for a GitHub issue
 * (`encodeURIComponent`: a space is `%20`, a line break `%0A`), so a support form can fill itself in. They follow the
 * page's own query, a `title` or `body` already there replaced, and come before its fragment.
 */
function pageWithReport(url: string, report: SupportReport): string {
    const page = new URL(url);
    const kept = page.search
        .slice(1)
        .split('&')
        .filter((part) => part !== '' && !/^(title|body)(=|$)/.test(part));
    const query = [...kept, `title=${encodeURIComponent(report.subject)}`, `body=${encodeURIComponent(report.body)}`].join('&');
    return `${page.origin}${page.pathname}?${query}${page.hash}`;
}

/** The link that sends `report` through `channel`: `mailto:` with subject and body, the page with the report, or a new GitHub issue. */
export function reportHref(channel: SupportChannel, report: SupportReport): string {
    switch (channel.kind) {
        case 'mailto':
            // RFC 6068: line breaks in a mailto body are CRLF.
            return `mailto:${channel.address}?subject=${encodeURIComponent(report.subject)}&body=${encodeURIComponent(report.body.replace(/\r?\n/g, '\r\n'))}`;
        case 'github':
            return `${channel.url}?title=${encodeURIComponent(report.subject)}&body=${encodeURIComponent(report.body)}`;
        case 'page':
            return pageWithReport(channel.url, report);
    }
}
