/**
 * «Can't find it? Let us know» (P20): the report of a search that found nothing useful, and where it goes.
 *
 * The report leaves from the user's own client, never from the server:
 * - the instance's support address is `mailto:` and one address → a `mailto:` link with the subject and the body;
 * - it is an http(s) page → the page opens with the report as `title` and `body` in its address, as for a GitHub
 *   issue (N61-form), and the report also goes to the clipboard, for a page that does not read them;
 * - it is not set, or not valid → on a self-hosted instance, a prefilled GitHub issue, public, that the user reviews
 *   before sending it; on a managed instance, or when the configuration could not be read, no link at all (N61): a
 *   public issue would publish the profile, the provider codes and the identifiers.
 *
 * `LIBREFOLIO_SUPPORT_URL` reaches the app through `GET /system/instance` (`support_url`), already validated by the
 * backend; `supportChannel` checks it again on the parsed address, so that nothing but http(s) and `mailto:` ever
 * becomes a link, and an address with a user name or a password counts as missing.
 *
 * What the report carries: the text searched, the providers queried with their outcome (codes only), the form's
 * currency, type and identifiers when the caller gives them, the app's version, profile and language. Never the user,
 * an email address, the instance's address or any portfolio data: the input has no field for them.
 */

/** Where the report goes. */
export type SupportChannel = {kind: 'mailto'; address: string} | {kind: 'page'; url: string} | {kind: 'github'; url: string};

/** A new issue in the project's repository: the channel when the instance names no support address. */
export const GITHUB_NEW_ISSUE_URL = 'https://github.com/Librefolio/LibreFolio/issues/new';

/** What one provider answered to the search. `no_answer`: the search ended (a timeout) before it answered. */
export type ProviderOutcome = {code: string; status: 'results'; count: number} | {code: string; status: 'error'; errorCode: string | null} | {code: string; status: 'no_answer'};

/** The asset form, as far as the report is concerned: what the user had already filled in. */
export interface SearchReportContext {
    currency?: string | null;
    assetType?: string | null;
    identifiers?: ReadonlyArray<{type: string; value: string}> | null;
}

export interface SearchReportInput {
    query: string;
    /** The providers queried, in the order the report lists them. */
    providers: readonly ProviderOutcome[];
    context?: SearchReportContext | null;
    appVersion: string;
    profile: string;
    language: string;
}

export interface SearchReport {
    subject: string;
    body: string;
}

/** The query's length in the subject, in characters (code points: an emoji is never cut in two). */
const SUBJECT_QUERY_MAX = 80;

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

function outcomeLine(outcome: ProviderOutcome): string {
    switch (outcome.status) {
        case 'results':
            return `- ${outcome.code}: ${outcome.count} ${outcome.count === 1 ? 'result' : 'results'}`;
        case 'error':
            return `- ${outcome.code}: ${outcome.errorCode ? `error ${outcome.errorCode}` : 'error'}`;
        case 'no_answer':
            return `- ${outcome.code}: no answer`;
    }
}

function formParts(context: SearchReportContext | null | undefined): string[] {
    if (!context) return [];
    const parts: string[] = [];
    const currency = context.currency?.trim();
    if (currency) parts.push(`currency ${currency}`);
    const assetType = context.assetType?.trim();
    if (assetType) parts.push(`type ${assetType}`);
    for (const identifier of context.identifiers ?? []) {
        const value = identifier.value.trim();
        if (value) parts.push(`${identifier.type} ${value}`);
    }
    return parts;
}

/** The report of a search, in English: a subject and a plain-text body. */
export function buildSearchReport(input: SearchReportInput): SearchReport {
    const shortQuery = Array.from(input.query.trim().replace(/\s+/g, ' '));
    const subjectQuery = shortQuery.length > SUBJECT_QUERY_MAX ? `${shortQuery.slice(0, SUBJECT_QUERY_MAX).join('')}…` : shortQuery.join('');
    const lines = ['I searched LibreFolio for an asset and could not find it.', '', `Search: ${input.query.trim()}`];
    if (input.providers.length === 0) lines.push('Providers: none');
    else lines.push('Providers:', ...input.providers.map(outcomeLine));
    const form = formParts(input.context);
    if (form.length > 0) lines.push(`In the form: ${form.join(', ')}`);
    lines.push(`LibreFolio ${input.appVersion}, ${input.profile}, language ${input.language}`, '', "Anything else that helps (the exchange, a link to the asset's page):");
    return {subject: `LibreFolio: asset not found — ${subjectQuery}`, body: lines.join('\n')};
}

/**
 * A support page with the report in its address (N61-form): `title` and `body`, encoded as for a GitHub issue
 * (`encodeURIComponent`: a space is `%20`, a line break `%0A`), so a support form can fill itself in. They follow the
 * page's own query, a `title` or `body` already there replaced, and come before its fragment.
 */
function pageWithReport(url: string, report: SearchReport): string {
    const page = new URL(url);
    const kept = page.search
        .slice(1)
        .split('&')
        .filter((part) => part !== '' && !/^(title|body)(=|$)/.test(part));
    const query = [...kept, `title=${encodeURIComponent(report.subject)}`, `body=${encodeURIComponent(report.body)}`].join('&');
    return `${page.origin}${page.pathname}?${query}${page.hash}`;
}

/** The link that sends `report` through `channel`: `mailto:` with subject and body, the page with the report, or a new GitHub issue. */
export function reportHref(channel: SupportChannel, report: SearchReport): string {
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
