/**
 * The Content-Security-Policy violations a page reports, and the baseline of those already known (H-43).
 *
 * The collector of `fixtures/playwright.ts` records every `securitypolicyviolation` event of the pages of a test —
 * enforced or report-only — and fails the test on one this module does not know. A managed instance sends the
 * report-only policy of `security_headers.py` (`CSP_REPORT_ONLY_POLICY`) on the app's pages, so a run on a managed lane
 * (`--lane-setting LIBREFOLIO_PROFILE=managed`) shows what an enforced policy would break. A self-hosted lane sends no
 * such policy: the collector then records nothing.
 *
 * The baseline, `e2e/csp-baseline.json`, lists the violations already known and owned. An entry names the directive
 * and the blocked resource: by its blocked URI (`inline`, `eval`, an address), or by the path of the blocked address
 * whatever its origin and query (`blockedPath`, for an address the user typed). An entry with `indexInlineScript: n`
 * stands for the n-th inline `<script>` of the app's `index.html`, located by its lines in the document the lane
 * serves, so an edit of `app.html` that moves it keeps it known. A ratchet: an entry is added only by a recorded
 * decision, with its reason and its owner, never to silence a red, and removed by the lot that cures it.
 *
 * `E2E_CSP_COLLECTOR=0` turns the collector off for a whole run (the kill switch).
 */
import {readFileSync} from 'node:fs';

/** One violation, as the page's `securitypolicyviolation` event describes it, with the URL of the page it came from. */
export type CspViolation = {
    directive: string;
    violatedDirective: string;
    blockedURI: string;
    sourceFile: string;
    lineNumber: number;
    columnNumber: number;
    sample: string;
    disposition: string;
    documentURI: string;
    page: string | null;
};

/**
 * A known violation: its directive and the blocked resource, named by exactly one of `blockedURI` (equal) and
 * `blockedPath` (the path of the blocked address, whatever its origin and query), and for an inline script of
 * `index.html` its position among them.
 */
export type CspBaselineEntry = {
    id: string;
    directive: string;
    blockedURI?: string;
    blockedPath?: string;
    indexInlineScript?: number;
    reason: string;
    owner: string;
};

export type CspBaseline = {entries: CspBaselineEntry[]};

/** The lines of a `<script>` element of a document, 1-based and inclusive: the tag's line to the closing tag's. */
export type LineSpan = {first: number; last: number};

/** Whether the collector runs: always, unless `E2E_CSP_COLLECTOR` is `0`. */
export function cspCollectorEnabled(env: Record<string, string | undefined>): boolean {
    return env.E2E_CSP_COLLECTOR !== '0';
}

/** The line spans of the inline scripts of `html` — every `<script>` without a `src` attribute — in document order. */
export function inlineScriptLines(html: string): LineSpan[] {
    const spans: LineSpan[] = [];
    for (const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)) {
        if (/\bsrc\s*=/i.test(match[1])) continue;
        const first = html.slice(0, match.index ?? 0).split('\n').length;
        spans.push({first, last: first + match[0].split('\n').length - 1});
    }
    return spans;
}

/** The path of `blockedURI` read as an absolute address; `null` for `inline`, `eval`, an empty or a relative one. */
function blockedPathOf(blockedURI: string): string | null {
    try {
        return new URL(blockedURI).pathname;
    } catch {
        return null;
    }
}

/** Whether `entry` names the resource `violation` blocked: its path when the entry gives one, else its URI, equal. */
function namesBlocked(entry: CspBaselineEntry, violation: CspViolation): boolean {
    return entry.blockedPath !== undefined ? blockedPathOf(violation.blockedURI) === entry.blockedPath : entry.blockedURI === violation.blockedURI;
}

/** Whether `baseline` knows `violation`; `indexInlineScripts` are the inline scripts of the app's `index.html`. */
export function isKnown(violation: CspViolation, baseline: CspBaseline, indexInlineScripts: LineSpan[]): boolean {
    return baseline.entries.some((entry) => {
        if (entry.directive !== violation.directive || !namesBlocked(entry, violation)) return false;
        if (entry.indexInlineScript === undefined) return true;
        const span = indexInlineScripts[entry.indexInlineScript];
        return span !== undefined && violation.lineNumber >= span.first && violation.lineNumber <= span.last;
    });
}

/** The baseline, `e2e/csp-baseline.json`. */
export function loadBaseline(): CspBaseline {
    return JSON.parse(readFileSync(new URL('../csp-baseline.json', import.meta.url), 'utf8')) as CspBaseline;
}
