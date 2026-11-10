/**
 * «Can't find it? Let us know» (P20): the report of a search that found nothing useful.
 *
 * Where it goes (the instance's support address, or a GitHub issue) and the link that carries it are
 * `features/support/supportChannel.ts`, shared with the other reports. `LIBREFOLIO_SUPPORT_URL` reaches the app through
 * `GET /system/instance` (`support_url`).
 *
 * What the report carries: the text searched, the providers queried with their outcome (codes only), the form's
 * currency, type and identifiers when the caller gives them, the app's version, profile and language. Never the user,
 * an email address, the instance's address or any portfolio data: the input has no field for them.
 */
import type {SupportReport} from '$lib/features/support/supportChannel';

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

/** The query's length in the subject, in characters (code points: an emoji is never cut in two). */
const SUBJECT_QUERY_MAX = 80;

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
export function buildSearchReport(input: SearchReportInput): SupportReport {
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
