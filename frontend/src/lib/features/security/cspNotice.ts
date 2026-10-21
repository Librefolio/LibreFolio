/**
 * The notice of a script the browser blocked and this instance did not send (lot H-55 v2, step 4).
 *
 * The Content-Security-Policy LibreFolio enforces on its pages (`backend/app/services/platform/security_headers.py`)
 * allows only the scripts the instance sends. A script added on the way — a proxy that injects one, a CDN that
 * rewrites the page, a browser extension — is blocked, and the page goes on without it. This module makes that
 * visible where a developer or an administrator looks, and nowhere else:
 *
 * - one line of the browser console per page load, naming what was blocked and the guide;
 * - its source (the origin of the blocked address, or `inline`, or `eval`) noted once in the tab's `sessionStorage`
 *   (`CSP_BLOCKED_STORAGE_KEY`), which the Security tab of Settings reads (`platform.blockedScript`).
 *
 * No report endpoint, no request of any kind: the browser's report never leaves the browser. The violations come from
 * `window.__lfCspViolations`, which `app.html` fills from its head before any bundle loads (enforced ones only), from a
 * listener of `securitypolicyviolation` for what comes next, and, where the browser has one, from a `ReportingObserver`
 * of `csp-violation` reports with `buffered: true`. A report-only violation (the managed profile's wider policy) is
 * not this notice's business. `KNOWN_CSP_VIOLATIONS` are never reported: cheetah-grid's probe of the global object.
 */

import {checkGuidePath} from '$lib/features/instance/checkGuides';

/** Where the sources of the blocked scripts are noted for the tab: a JSON array of distinct strings. */
export const CSP_BLOCKED_STORAGE_KEY = 'librefolio-csp-blocked';
/** The guide of the policy, the Security tab's for the same finding (`checkGuides.json`): one place for both. */
export const CSP_GUIDE_PATH = `/mkdocs/${checkGuidePath('platform.blockedScript') ?? 'admin/configuration/'}`;

/** A violation the instance knows and causes itself: never reported. */
export interface KnownCspViolation {
    directive: string;
    blockedURI: string;
    sample: string;
}

/**
 * cheetah-grid 1.16.7 bundles webpack's probe of the global object, `new Function("return this")()`, in a try/catch
 * that falls back to `window`: harmless when blocked. Chromium reports the source the Function constructor builds.
 * The same entry as `frontend/e2e/csp-baseline.json` F1.
 */
export const KNOWN_CSP_VIOLATIONS: readonly KnownCspViolation[] = Object.freeze([{directive: 'script-src', blockedURI: 'eval', sample: '(function anonymous(\n) {\nreturn this\n})'}]);

interface Violation {
    directive: string;
    blockedURI: string;
    sample: string;
}

interface NoticeStorage {
    getItem(key: string): string | null;
    setItem(key: string, value: string): void;
}

interface NoticeWindow {
    document?: {addEventListener(type: string, listener: (event: unknown) => void): void};
    location?: {origin?: string};
    ReportingObserver?: new (callback: (reports: unknown[]) => void, options: unknown) => {observe(): void};
    sessionStorage?: NoticeStorage;
    __lfCspViolations?: unknown;
}

export interface CspNoticeOptions {
    /** The window: `window` when absent. */
    win?: unknown;
    /** The tab's storage: `win.sessionStorage` when absent. */
    storage?: unknown;
    /** Where the line goes: `console.error` when absent. */
    log?: (message: string) => void;
}

function text(value: unknown): string {
    return typeof value === 'string' ? value : '';
}

function isKnown({directive, blockedURI, sample}: Violation): boolean {
    return KNOWN_CSP_VIOLATIONS.some((known) => known.directive === directive && known.blockedURI === blockedURI && known.sample === sample);
}

/** What was blocked, as the line and the storage name it: the origin of an address, or `inline`, or `eval`. */
function sourceOf(blockedURI: string): string {
    if (blockedURI === 'inline' || blockedURI === 'eval') {
        return blockedURI;
    }
    try {
        return new URL(blockedURI).origin;
    } catch {
        return blockedURI || 'inline';
    }
}

function noteSource(storage: NoticeStorage | undefined, source: string): void {
    if (!storage) {
        return;
    }
    try {
        let sources: string[] = [];
        try {
            const parsed: unknown = JSON.parse(storage.getItem(CSP_BLOCKED_STORAGE_KEY) ?? '[]');
            sources = Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : [];
        } catch {
            sources = [];
        }
        if (!sources.includes(source)) {
            storage.setItem(CSP_BLOCKED_STORAGE_KEY, JSON.stringify([...sources, source]));
        }
    } catch {
        // Blocked site data, a private window: the console line is enough
    }
}

/** Start the notice for this page load: drain the early buffer, then listen. Never throws. */
export function startCspNotice({win, storage, log}: CspNoticeOptions = {}): void {
    const target = (win ?? (typeof window === 'undefined' ? undefined : window)) as NoticeWindow | undefined;
    if (!target) {
        return;
    }
    let tabStorage = storage as NoticeStorage | undefined;
    if (storage === undefined) {
        try {
            tabStorage = target.sessionStorage;
        } catch {
            tabStorage = undefined;
        }
    }
    const write = log ?? ((message: string) => console.error(message));
    const guide = `${target.location?.origin ?? ''}${CSP_GUIDE_PATH}`;
    let logged = false;

    const handle = (violation: Violation): void => {
        if (isKnown(violation)) {
            return;
        }
        const source = sourceOf(violation.blockedURI);
        noteSource(tabStorage, source);
        if (!logged) {
            logged = true;
            write(`LibreFolio blocked a script it did not send (${source}): a proxy, a CDN or a browser extension adds it. Guide: ${guide}`);
        }
    };

    const buffered = target.__lfCspViolations;
    if (Array.isArray(buffered)) {
        for (const item of buffered) {
            const entry = (item ?? {}) as Record<string, unknown>;
            handle({directive: text(entry.directive), blockedURI: text(entry.blockedURI), sample: text(entry.sample)});
        }
        buffered.length = 0;
    }

    // At the document only: the event bubbles to the window, and a second listener there would see it twice
    target.document?.addEventListener('securitypolicyviolation', (event: unknown) => {
        const live = (event ?? {}) as Record<string, unknown>;
        if (live.disposition === 'enforce') {
            handle({directive: text(live.effectiveDirective), blockedURI: text(live.blockedURI), sample: text(live.sample)});
        }
    });

    if (typeof target.ReportingObserver === 'function') {
        try {
            const observer = new target.ReportingObserver(
                (reports: unknown[]) => {
                    for (const report of reports) {
                        const {type, body} = (report ?? {}) as {type?: unknown; body?: Record<string, unknown>};
                        if (type === 'csp-violation' && body && body.disposition === 'enforce') {
                            handle({directive: text(body.effectiveDirective), blockedURI: text(body.blockedURL), sample: text(body.sample)});
                        }
                    }
                },
                {types: ['csp-violation'], buffered: true},
            );
            observer.observe();
        } catch {
            // A browser whose observer refuses the options: the buffer and the listener do the work
        }
    }
}

/** The sources of the scripts blocked in this tab, as the notice noted them; `[]` when none or unreadable. */
export function readBlockedScripts(storage?: NoticeStorage): string[] {
    try {
        const tab = storage ?? (typeof window === 'undefined' ? undefined : window.sessionStorage);
        const parsed: unknown = JSON.parse(tab?.getItem(CSP_BLOCKED_STORAGE_KEY) ?? '[]');
        return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : [];
    } catch {
        return [];
    }
}
