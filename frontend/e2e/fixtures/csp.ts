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
 * whatever its origin and query (`blockedPath`, for an address the user typed). An entry may also name the
 * violation's `sample`, which must then be equal: the policy has `'report-sample'`, so Chromium reports the first 40
 * characters of a blocked script or eval. The inline scripts of the app need no entry: the policy allows them by their
 * hashes (H-52). A ratchet: an entry is added only by a recorded decision, with its reason and its owner, never to
 * silence a red, and removed by the lot that cures it.
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
 * `blockedPath` (the path of the blocked address, whatever its origin and query), and, when given, its `sample` (equal).
 */
export type CspBaselineEntry = {
    id: string;
    directive: string;
    blockedURI?: string;
    blockedPath?: string;
    sample?: string;
    reason: string;
    owner: string;
};

export type CspBaseline = {entries: CspBaselineEntry[]};

/** Whether the collector runs: always, unless `E2E_CSP_COLLECTOR` is `0`. */
export function cspCollectorEnabled(env: Record<string, string | undefined>): boolean {
    return env.E2E_CSP_COLLECTOR !== '0';
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

/** Whether `baseline` knows `violation`: an entry names its directive and the resource it blocked, and its sample if any. */
export function isKnown(violation: CspViolation, baseline: CspBaseline): boolean {
    return baseline.entries.some((entry) => entry.directive === violation.directive && namesBlocked(entry, violation) && (entry.sample === undefined || entry.sample === violation.sample));
}

/** The baseline, `e2e/csp-baseline.json`. */
export function loadBaseline(): CspBaseline {
    return JSON.parse(readFileSync(new URL('../csp-baseline.json', import.meta.url), 'utf8')) as CspBaseline;
}
