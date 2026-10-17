/**
 * The collector of Content-Security-Policy report-only violations (H-43 part B), in the fixture every spec imports.
 *
 * Why. In the managed profile the server sends `Content-Security-Policy-Report-Only` with `CSP_REPORT_ONLY_POLICY`
 * (backend/app/services/platform/security_headers.py) on the HTML pages of the web app, and nobody sees its violations:
 * the browser reports them in its console, and there is no report endpoint. Each one is something a CSP applied tomorrow
 * would block. The collector turns them into reds: an auto fixture of e2e/fixtures/playwright.ts records every
 * `securitypolicyviolation` of every document of the test and, at teardown, fails the test on any violation that
 * e2e/csp-baseline.json does not know. On day one the baseline knows two: the inline scripts of the built index.html —
 * app.html's (the theme before the first paint, the PWA prompt, the service worker) and SvelteKit's bootstrap — which
 * violate `script-src 'self'` until a later lot hashes them. The managed lane's first cloud smoke found two more, recorded
 * as entries owned by the lots that cure them: cheetah-grid's bundled probe of the global object, an `eval` (F1), and the
 * address check of a link, a `connect-src` to whatever address an administrator typed, a nonce in its query (F3).
 *
 * The contract the cure is held to here:
 *   - `cspViolations`, an auto fixture, test-scoped. Unless the kill switch is set it exposes the binding
 *     `__lfCspViolation` to the browser context and registers, in every document, a capture listener of
 *     `securitypolicyviolation` on `document` that sends the binding {directive (the effective one), violatedDirective,
 *     blockedURI, sourceFile, lineNumber, columnNumber, sample, disposition, documentURI}. Its value: `list()`, every
 *     violation received, and `unknown()`, those the baseline does not know;
 *   - `cspFailOnUnknown`, an option, true by default: at teardown an unknown violation fails the test with a readable
 *     list. `test.use({cspFailOnUnknown: false})` keeps the record and fails nothing;
 *   - e2e/fixtures/csp.ts, the pure logic: `cspCollectorEnabled(env)`, `inlineScriptLines(html)`, `isKnown(violation,
 *     baseline, spans)` and `loadBaseline()`. A violation is known when a baseline entry names its directive and what it
 *     blocked and, for an entry with `indexInlineScript`, its line falls within the span — from the line of `<script>` to
 *     the line of `</script>` — of the entry's inline script of index.html. An entry names what was blocked by exactly one
 *     of `blockedURI`, the blocked URI itself, and `blockedPath`, the path of the blocked address
 *     (`new URL(blockedURI).pathname`) whatever its origin and query: a blocked URI that is no absolute URL — `inline`,
 *     `eval`, empty, a bare path — has no path, and no `blockedPath` entry knows it.
 *
 * The tests:
 *   1. the pure logic, on synthetic input, without a page; then the real baseline against the managed lane's findings of
 *      the first cloud smoke (F1, F3);
 *   2. a synthetic document with one inline script, served by this spec under `script-src 'self'` report-only: the
 *      violation is recorded once, field for field as the page itself saw it; the script still ran; it is unknown, and
 *      the test passes all the same (`cspFailOnUnknown: false`);
 *   3. the same kind of unknown violation with the option at its default: the test must fail at teardown. It is marked
 *      with `test.fail()` once its body has checked all it can, so that Playwright reports it passed only if it did fail,
 *      and a red of the body itself stays a red;
 *   4. a navigation: two synthetic documents in a row, both recorded — the binding and the listener come back with every
 *      document;
 *   5. the real app: the lane's `/` — index.html, the sign-in page — under CSP_REPORT_ONLY_POLICY reports its two inline
 *      scripts and nothing else, and the baseline knows both: the managed lane's day one, proven on any lane;
 *   6. the kill switch, below.
 *
 * Lanes. The spec brings the headers it needs, so it runs on a self-hosted lane (`front-utility csp-collector`) as on a
 * managed one (the cloud smoke). The synthetic documents never reach the server. The sign-in page's document passes
 * through a route that adds the policy only when the lane did not send it: on a managed lane the server's own header goes
 * through untouched — never two policies, which would report every inline script twice — and must equal this spec's copy.
 *
 * The kill switch. `E2E_CSP_COLLECTOR=0` in the environment of a run turns the collector off for the whole run: no
 * binding, no listener, a recorder that holds nothing and fails nothing. A test cannot change its worker's environment,
 * so the switch is proven two ways: `cspCollectorEnabled` purely (test 1, in every run), and the last test of this file,
 * which runs only in a run started with the switch — the collector's own tests skip there.
 *
 * Before the cure. The file names the fixture `cspViolations`, which does not exist yet: Playwright refuses the file at
 * load («Test has unknown parameter "cspViolations"») and runs nothing in that invocation. The pure tests import
 * e2e/fixtures/csp.ts at run time, not with the file, so once the fixture exists a missing helper is an assertion that
 * names it, never a load error.
 *
 * Selectors: `data-testid` in the app (`login-page`); the synthetic documents are this spec's own and use a plain id.
 * Waiting: on states, never on the clock — the title an inline script sets, the collector's list polled until it holds
 * what the page dispatched, then one round trip through the page, so that anything sent with it has arrived too.
 * Data: nothing is written; the routes and the record die with the test's browser context.
 * Not asserted here: the `csp-violations` attachment and the readable message of the teardown failure. Both are made
 * after every hook and every other fixture of the test has finished, where no spec can read them; the report shows them.
 */
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {expect, test, type BrowserContext, type Page} from '../fixtures/playwright';
import type {CspViolation} from '../fixtures/csp';
import {uniqueSuffix} from '../fixtures/unique';

/** The collector's pure logic as its module types it. Only the types are read with the file: see cspHelpers(). */
type CspHelpers = typeof import('../fixtures/csp');
/** The baseline as `isKnown` takes it: e2e/csp-baseline.json, as `loadBaseline()` reads it. */
type CspBaseline = Parameters<CspHelpers['isKnown']>[1];

/** The value of the `cspViolations` fixture: what the collector holds for the current test. */
interface CspRecorder {
    /** Every violation the documents of the test sent the collector, in the order received. */
    list(): readonly CspViolation[];
    /** Those the baseline does not know: what fails the test at teardown while `cspFailOnUnknown` is on. */
    unknown(): readonly CspViolation[];
}

/** The lines of an inline script in a document, 1-based and inclusive, from its `<script>` tag to its `</script>`. */
interface LineSpan {
    first: number;
    last: number;
}

/** An entry of e2e/csp-baseline.json, as the contract writes it. It names what was blocked by exactly one of blockedURI and blockedPath. */
interface BaselineEntry {
    id: string;
    directive: string;
    /** The blocked URI itself, compared whole: `inline`, `eval`, an address. */
    blockedURI?: string;
    /** The path of the blocked address, `new URL(blockedURI).pathname`, whatever its origin and query. */
    blockedPath?: string;
    /** The 0-based index of an inline script of index.html, in document order. */
    indexInlineScript?: number;
    reason: string;
    owner: string;
}

/** A violation as the page itself saw it, through this spec's own recorder: the browser's word, which the collector is held to. */
interface SeenViolation {
    directive: string;
    blockedURI: string;
    lineNumber: number;
    documentURI: string;
    disposition: string;
}

/** A document of the lane the route answered, and where its report-only policy came from. */
interface ServedDocument {
    path: string;
    status: number;
    contentType: string;
    /** The report-only policy the lane sent itself: none on a self-hosted lane, CSP_REPORT_ONLY_POLICY on a managed one. */
    lanePolicy: string | null;
    /** Whether the spec added CSP_REPORT_ONLY_POLICY: an HTML answer the lane sent without a report-only policy. */
    injected: boolean;
    /** The HTML as served — the document whose inline scripts the baseline names; null for any other answer. */
    html: string | null;
    /** Why the route could not fetch it: the document was refused, never let through without the policy. */
    failure: string | null;
}

/**
 * The report-only policy of the web app's pages in the managed profile: `CSP_REPORT_ONLY_POLICY` in
 * backend/app/services/platform/security_headers.py, copied, not read. A self-hosted lane never sends it, so the spec adds
 * it to the sign-in page; a managed lane sends it, and then its header must equal this copy.
 */
const CSP_REPORT_ONLY_POLICY = [
    "default-src 'self'",
    "script-src 'self' 'wasm-unsafe-eval'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "worker-src 'self' blob:",
    "frame-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'self'",
].join('; ');
const REPORT_ONLY_HEADER = 'content-security-policy-report-only';

/** The policy of the synthetic documents: their inline script is reported, and nothing else of theirs is concerned. */
const SYNTHETIC_POLICY = "script-src 'self'";
/**
 * The line of a synthetic document's inline script, the whole element on it, so that any reading of «its line» gives this
 * one. Far above the first inline script of the built index.html (line 14 today), so the baseline does not know it.
 */
const SYNTHETIC_SCRIPT_LINE = 5;
/** The binding the collector exposes to every browser context, by the contract: what the kill switch leaves out. */
const BINDING = '__lfCspViolation';
/** The window array where this spec's own recorder keeps what each document dispatched. */
const SEEN_KEY = '__lfCspCollectorSpecSeen';
/** e2e/csp-baseline.json, the baseline `loadBaseline()` reads. */
const BASELINE_FILE = fileURLToPath(new URL('../csp-baseline.json', import.meta.url));
/** What e2e/fixtures/csp.ts exports, by the contract. */
const HELPERS = ['cspCollectorEnabled', 'inlineScriptLines', 'isKnown', 'loadBaseline'] as const;

/** The path of the address check of a link (`PROBE_PATH`, settings/users/addressProbe.ts), copied: `GET <the address an administrator typed>/api/v1/auth/address-probe?nonce=…`. */
const ADDRESS_PROBE_PATH = '/api/v1/auth/address-probe';
/** The managed lane whose first cloud smoke found F1 and F3: the origin its pages were served at. */
const SMOKE_LANE = 'http://localhost:6181';
/**
 * F1 as that smoke recorded it, in files.spec.ts's BRIM table preview: cheetah-grid's bundled webpack probe of the global
 * object, `new Function("return this")()` in a try/catch that falls back to `window` — `script-src`, `eval`, from its chunk.
 */
const SMOKE_GLOBAL_PROBE: Partial<CspViolation> = {directive: 'script-src', violatedDirective: 'script-src', blockedURI: 'eval', sourceFile: `${SMOKE_LANE}/_app/immutable/chunks/Cn5CY6Wr.js`, lineNumber: 758, documentURI: `${SMOKE_LANE}/files?tab=brim`};
/**
 * F3 as that smoke recorded it, in admin-users.spec.ts AUSR-E-07, which types other origins on purpose: the address check of
 * a link sent to the lane's other loopback origin, to a closed port, to a stranger. Origins and path as recorded; each nonce
 * — 75 base64url characters, a new one per check — begins as recorded, and the rest of it is made up.
 */
const SMOKE_ADDRESS_CHECKS = [
    'http://127.0.0.1:6181/api/v1/auth/address-probe?nonce=4YOdZ1b0xQIkTD0qSeV6u8AV1LCC9nWAbfpqNmZ38AnaxmWClYgkaJoAP44W1wd8bCfv0tdHygs',
    'http://127.0.0.1:1/api/v1/auth/address-probe?nonce=T0zv5EK5C1LZ-nEWE9tDoeBAoRs-spRCrLAUpOjkekaCgZMHbkTSXycrgKZ4F4IgubsZAazNhjw',
    'http://probe-mismatch.invalid/api/v1/auth/address-probe?nonce=OSCYQG-j5-GxpGCGPD6KU0N6vBLIu-lyOmnejUHLLe6noEOsJPP4LS1it2amI8zHxRXO4Vaaz1o',
];
/** The entry of e2e/csp-baseline.json recorded for F1: equality on `script-src` and `eval`. */
const F1_ENTRY = 'cheetah-grid-global-probe';
/** The entry recorded for F3: `connect-src`, and the path of the blocked address. */
const F3_ENTRY = 'address-probe-other-origin';

/** The kill switch as this spec reads it to choose its tests: the rule of `cspCollectorEnabled`, which test 1 holds to it. */
const KILL_SWITCH_ON = process.env.E2E_CSP_COLLECTOR === '0';
const COLLECTOR_OFF = 'E2E_CSP_COLLECTOR=0: the collector is off for this whole run, and the kill-switch test at the end of this file covers it';

/** A violation: dispatched by the browser in a task after the parser's, then carried to the test by the binding. */
const VIOLATION_TIMEOUT_MS = 10_000;
/** The sign-in page: the app's chunks, its session check, then its first drawing — on a loaded machine. */
const PAGE_TIMEOUT_MS = 30_000;

/** The app's service worker answers navigations itself, and a request it answers never reaches the route that sets the policy. */
test.use({serviceWorkers: 'block'});

/** The runner's baseURL, as an origin: the lane. */
function laneOrigin(baseURL: string | undefined): string {
    if (!baseURL) throw new Error('This spec needs the runner-provided baseURL');
    return new URL(baseURL).origin;
}

/** A directory of the lane's origin that only the current test serves: its synthetic documents never reach the server. */
function syntheticDir(baseURL: string | undefined): string {
    return `${laneOrigin(baseURL)}/__lf-csp-collector/${uniqueSuffix()}/`;
}

/**
 * A synthetic document: one inline script, the whole element on line SYNTHETIC_SCRIPT_LINE, which sets the title to
 * `token` — the proof that it ran — and, given `next`, a link to that address.
 */
function syntheticDocument(token: string, next?: string): string {
    return [
        '<!doctype html>', // 1
        '<html lang="en">', // 2
        '<head><meta charset="utf-8" /><title>pending</title></head>', // 3
        '<body>', // 4
        `<script>document.title = ${JSON.stringify(token)};</script>`, // 5: SYNTHETIC_SCRIPT_LINE
        next ? `<a id="next" href="${next}">next</a>` : '', // 6
        '</body>', // 7
        '</html>', // 8
    ].join('\n');
}

/** Serves `html` at `url` to the page, under SYNTHETIC_POLICY report-only: the browser reports the inline script, and runs it. */
async function serveSynthetic(page: Page, url: string, html: string): Promise<void> {
    await page.route(
        (candidate) => candidate.href === url,
        (route) => route.fulfill({status: 200, contentType: 'text/html; charset=utf-8', headers: {[REPORT_ONLY_HEADER]: SYNTHETIC_POLICY}, body: html}),
    );
}

/**
 * Records, in every document of the page, every `securitypolicyviolation` it dispatches: the browser's word, which the
 * collector is held to. A capture listener on `document`, where the collector listens; registered before the first
 * navigation, so that a document's first violation is recorded too. A state read when the test chooses, never an edge.
 */
async function recordWhatThePageSees(page: Page): Promise<void> {
    await page.addInitScript((key: string) => {
        if (key in window) return;
        const seen: unknown[] = [];
        Object.defineProperty(window, key, {value: seen});
        document.addEventListener(
            'securitypolicyviolation',
            (event) => {
                seen.push({directive: event.effectiveDirective, blockedURI: event.blockedURI, lineNumber: event.lineNumber, documentURI: event.documentURI, disposition: event.disposition});
            },
            true,
        );
    }, SEEN_KEY);
}

/** What the page's current document saw. Its recorder must be there: without it, «nothing seen» would be the recorder's absence. */
async function seenByPage(page: Page): Promise<SeenViolation[]> {
    const seen: unknown = await page.evaluate((key) => (window as unknown as Record<string, unknown>)[key] ?? null, SEEN_KEY);
    if (!Array.isArray(seen)) throw new Error(`no recorder of this spec in the page’s document (${page.url()}): recordWhatThePageSees() runs before the navigation`);
    return seen as SeenViolation[];
}

/** The fields the page and the collector both know, to hold one against the other. */
function asSeen(violation: SeenViolation): SeenViolation {
    return {directive: violation.directive, blockedURI: violation.blockedURI, lineNumber: violation.lineNumber, documentURI: violation.documentURI, disposition: violation.disposition};
}

/** The type of the collector's binding in the page's document: 'function' while the collector is on. */
async function bindingType(page: Page): Promise<string> {
    return page.evaluate((name) => typeof (window as unknown as Record<string, unknown>)[name], BINDING);
}

/**
 * The violations the collector holds for one document, once it holds `count` of them: polled, since a violation reaches
 * the test through the binding after the page dispatched it; then read again after one round trip through the page, so
 * that a copy the page sent with it — a listener registered twice — has arrived too, and fails the caller's comparison.
 */
async function collectedFor(page: Page, csp: CspRecorder, documentURI: string, count: number, what: string): Promise<CspViolation[]> {
    const ofDocument = () => csp.list().filter((violation) => violation.documentURI === documentURI);
    await expect.poll(ofDocument, {message: `${what}: the collector received ${count} violation(s) of ${documentURI}`, timeout: VIOLATION_TIMEOUT_MS}).toHaveLength(count);
    await page.evaluate(() => undefined);
    return ofDocument();
}

/** One line per violation, for a red: disposition, directive, what it blocked, where, and in which document. */
function listed(violations: readonly CspViolation[]): string {
    if (violations.length === 0) return '  (none)';
    return violations.map((violation) => `  ${violation.disposition} ${violation.directive}: blocked ${violation.blockedURI || '(no URI)'} at ${violation.sourceFile || '(no source)'}:${violation.lineNumber} in ${violation.documentURI}`).join('\n');
}

/**
 * The collector's pure logic, e2e/fixtures/csp.ts, imported by the test that needs it rather than with the file: without
 * the module the test fails on an assertion that names what is missing, and the file still loads.
 */
async function cspHelpers(): Promise<CspHelpers> {
    let loaded: Record<string, unknown> | null = null;
    let failure = '';
    try {
        loaded = (await import('../fixtures/csp')) as unknown as Record<string, unknown>;
    } catch (error) {
        failure = `: ${error instanceof Error ? error.message : String(error)}`;
    }
    expect(loaded, `e2e/fixtures/csp.ts, the collector’s pure logic (H-43 part B), can be imported${failure}`).not.toBeNull();
    const missing = HELPERS.filter((name) => typeof loaded?.[name] !== 'function');
    expect(missing, `e2e/fixtures/csp.ts exports the helpers of the contract: ${HELPERS.join(', ')}`).toEqual([]);
    return loaded as unknown as CspHelpers;
}

/** A violation as the collector records it: by default, the first inline script of the lane's `/`, at its `<script>` tag. */
function syntheticViolation(overrides: Partial<CspViolation>): CspViolation {
    const documentURI = 'http://localhost:6041/';
    return {directive: 'script-src-elem', violatedDirective: 'script-src-elem', blockedURI: 'inline', sourceFile: documentURI, lineNumber: 14, columnNumber: 0, sample: '', disposition: 'report', documentURI, ...overrides} as CspViolation;
}

/**
 * F3's kind of violation, the address check of a link sent to `blockedURI`: `connect-src`, reported, from an app chunk — its
 * name made up — on Settings › Users. Its line is immaterial: an entry that names no inline script reads none.
 */
function addressCheck(blockedURI: string, overrides: Partial<CspViolation> = {}): CspViolation {
    return syntheticViolation({directive: 'connect-src', violatedDirective: 'connect-src', blockedURI, sourceFile: `${SMOKE_LANE}/_app/immutable/chunks/DkQ7v2Xa.js`, lineNumber: 1, documentURI: `${SMOKE_LANE}/settings?tab=users`, ...overrides});
}

/**
 * An entry a ratchet can trust: an id, a directive, what was blocked — by exactly one of a blocked URI and a blocked path,
 * written as a URL's pathname is, from its leading `/` — and the human decision behind it, a reason and an owner.
 */
function wellFormed(entry: Partial<BaselineEntry>): boolean {
    const named = (value: unknown) => typeof value === 'string' && value.trim() !== '';
    const index = entry.indexInlineScript;
    const blocked = entry.blockedPath === undefined ? named(entry.blockedURI) : entry.blockedURI === undefined && typeof entry.blockedPath === 'string' && entry.blockedPath.startsWith('/');
    return named(entry.id) && named(entry.directive) && blocked && named(entry.reason) && named(entry.owner) && (index === undefined || (Number.isInteger(index) && index >= 0));
}

/** The index of the inline script whose span holds the violation, when it is a reported inline script's; -1 otherwise. */
function inlineScriptOf(violation: CspViolation, spans: readonly LineSpan[]): number {
    if (violation.disposition !== 'report' || violation.directive !== 'script-src-elem' || violation.blockedURI !== 'inline') return -1;
    return spans.findIndex((span) => span.first <= violation.lineNumber && violation.lineNumber <= span.last);
}

/** An HTML answer: a Content-Type starting with `text/html`, in any case. */
function isHtml(contentType: string): boolean {
    return contentType.toLowerCase().startsWith('text/html');
}

/**
 * Gives every HTML document of the lane the managed profile's report-only policy, once: a document request — a navigation
 * or a frame — is fetched by the spec and answered with the lane's own answer, CSP_REPORT_ONLY_POLICY added only when the
 * lane sent no report-only policy itself. A managed lane's header goes through untouched: two policies would report every
 * inline script twice. Every other request passes. Before the first navigation.
 */
async function underTheReportOnlyPolicy(context: BrowserContext, origin: string, served: ServedDocument[]): Promise<void> {
    await context.route(
        (url) => url.origin === origin,
        async (route) => {
            const request = route.request();
            if (request.resourceType() !== 'document') {
                await route.fallback();
                return;
            }
            const path = new URL(request.url()).pathname;
            try {
                // A redirect is passed back as it came, and the browser asks for its target through this route again.
                const response = await route.fetch({maxRedirects: 0});
                const headers = response.headers();
                const contentType = headers['content-type'] ?? '';
                const lanePolicy = headers[REPORT_ONLY_HEADER] ?? null;
                const injected = isHtml(contentType) && lanePolicy === null;
                served.push({path, status: response.status(), contentType, lanePolicy, injected, html: isHtml(contentType) ? await response.text() : null, failure: null});
                await route.fulfill(injected ? {response, headers: {...headers, [REPORT_ONLY_HEADER]: CSP_REPORT_ONLY_POLICY}} : {response});
            } catch (error) {
                // Refused, never let through without the policy: the test's precondition names it.
                served.push({path, status: 0, contentType: '', lanePolicy: null, injected: false, html: null, failure: error instanceof Error ? error.message : String(error)});
                await route.abort('failed').catch(() => undefined);
            }
        },
    );
}

/** The documents the route answered, for a message: each HTML by its length only. */
function described(served: readonly ServedDocument[]): string {
    return JSON.stringify(served.map((document) => ({...document, html: document.html === null ? null : `${document.html.length} characters`})));
}

test.describe('H-43 part B, the CSP report-only collector: its pure logic, e2e/fixtures/csp.ts', () => {
    test('cspCollectorEnabled: off only with E2E_CSP_COLLECTOR=0, the kill switch of a whole run', async () => {
        const {cspCollectorEnabled} = await cspHelpers();
        expect(cspCollectorEnabled({}), 'no E2E_CSP_COLLECTOR in the environment: on').toBe(true);
        expect(cspCollectorEnabled({E2E_CSP_COLLECTOR: undefined}), 'E2E_CSP_COLLECTOR undefined: on').toBe(true);
        expect(cspCollectorEnabled({E2E_CSP_COLLECTOR: '1'}), 'E2E_CSP_COLLECTOR=1: on').toBe(true);
        expect(cspCollectorEnabled({E2E_CSP_COLLECTOR: '0'}), 'E2E_CSP_COLLECTOR=0: off, the kill switch').toBe(false);
        expect(cspCollectorEnabled(process.env), `this run (E2E_CSP_COLLECTOR ${process.env.E2E_CSP_COLLECTOR ?? 'unset'}): the reading this spec makes to choose its tests`).toBe(!KILL_SWITCH_ON);
    });

    test('inlineScriptLines: one 1-based span per inline script, from its <script> tag to its </script>, in document order — a script with a src is not inline', async () => {
        const {inlineScriptLines} = await cspHelpers();
        const html = [
            '<!doctype html>', // 1
            '<html lang="en">', // 2
            '    <head>', // 3
            '        <script>window.one = 1;</script>', // 4: inline, the whole element on one line
            '        <script src="/_app/immutable/entry/start.js"></script>', // 5: external
            '        <script type="module" src="/module.js" defer></script>', // 6: external, among other attributes
            '        <script>', // 7: inline over several lines, its tags alone on their lines — the shape of app.html's
            '            window.two = 2;', // 8
            '', // 9
            '            window.three = 3;', // 10
            '        </script>', // 11
            '    </head>', // 12
            '    <body>', // 13
            '        <div style="display: contents">', // 14
            '            <script type="module">', // 15: inline with an attribute — no src, so inline
            '                window.four = 4;', // 16
            '            </script>', // 17
            '        </div>', // 18
            '    </body>', // 19
            '</html>', // 20
        ].join('\n');
        expect(inlineScriptLines(html), 'the three inline scripts, each from the line of its <script> tag to the line of its </script>; the two with a src skipped').toEqual([
            {first: 4, last: 4},
            {first: 7, last: 11},
            {first: 15, last: 17},
        ]);
        expect(inlineScriptLines('<!doctype html><html><head><script src="/a.js"></script></head><body></body></html>'), 'external scripts only: no span').toEqual([]);
        expect(inlineScriptLines(''), 'an empty document: no span').toEqual([]);
    });

    test('isKnown: known when an entry names the violation’s directive and blocked URI and its line falls in the span of the entry’s inline script — nothing else is', async () => {
        const {isKnown} = await cspHelpers();
        const owner = 'layout/csp-collector.spec.ts';
        const dayOne: CspBaseline = {
            entries: [
                {id: 'index-inline-script-0', directive: 'script-src-elem', blockedURI: 'inline', indexInlineScript: 0, reason: 'synthetic', owner},
                {id: 'index-inline-script-1', directive: 'script-src-elem', blockedURI: 'inline', indexInlineScript: 1, reason: 'synthetic', owner},
            ],
        };
        // The spans of the built index.html today: app.html's script, then SvelteKit's bootstrap.
        const spans: LineSpan[] = [
            {first: 14, last: 38},
            {first: 116, last: 131},
        ];
        const known = (overrides: Partial<CspViolation>, baseline: CspBaseline = dayOne, indexSpans: LineSpan[] = spans) => isKnown(syntheticViolation(overrides), baseline, indexSpans);

        // Known: each entry's inline script, at its <script> tag — the line Chromium reports — inside it, and at its </script>.
        expect(known({lineNumber: 14}), 'the first inline script, at its <script> tag').toBe(true);
        expect(known({lineNumber: 20}), 'the first inline script, inside its span').toBe(true);
        expect(known({lineNumber: 38}), 'the first inline script, at its </script>').toBe(true);
        expect(known({lineNumber: 116}), 'the second inline script, at its <script> tag').toBe(true);
        expect(known({lineNumber: 131}), 'the second inline script, at its </script>').toBe(true);

        // Not known: another directive on the very same line.
        expect(known({directive: 'style-src-elem', violatedDirective: 'style-src-elem'}), 'an inline <style> on that line: style-src-elem').toBe(false);
        expect(known({directive: 'script-src-attr', violatedDirective: 'script-src-attr'}), 'an inline event handler on that line: script-src-attr, not the inline script').toBe(false);
        // Not known: a blocked URI other than inline.
        expect(known({blockedURI: 'https://cdn.example.invalid/x.js'}), 'an external script: its address, not inline').toBe(false);
        expect(known({directive: 'script-src', violatedDirective: 'script-src', blockedURI: 'eval'}), 'an eval: script-src, eval').toBe(false);
        // Not known: a line outside every span.
        for (const lineNumber of [1, 13, 39, 115, 132]) expect(known({lineNumber}), `line ${lineNumber}: outside both inline scripts`).toBe(false);
        // Not known, and no exception: an entry whose inline script the document does not have; an empty baseline.
        expect(known({lineNumber: 116}, dayOne, [spans[0]]), 'an index.html with a single inline script: the second entry knows nothing').toBe(false);
        expect(known({lineNumber: 14}, {entries: []} as unknown as CspBaseline), 'an empty baseline knows nothing').toBe(false);
    });

    test('isKnown: an entry with blockedPath knows a violation of its directive whose blocked address has that path, whatever its origin and query — nothing else', async () => {
        const {isKnown} = await cspHelpers();
        const entry: BaselineEntry = {id: 'address-probe-other-origin', directive: 'connect-src', blockedPath: ADDRESS_PROBE_PATH, reason: 'synthetic', owner: 'layout/csp-collector.spec.ts'};
        const byPath = {entries: [entry]} as unknown as CspBaseline;
        // The entry names no inline script of index.html: it needs no span, so the index.html here has none.
        const known = (blockedURI: string, overrides: Partial<CspViolation> = {}, baseline: CspBaseline = byPath) => isKnown(addressCheck(blockedURI, overrides), baseline, []);
        // A recorded address check with its path replaced: the same origin, the same nonce, only the path differs.
        const withPath = (pathname: string) => SMOKE_ADDRESS_CHECKS[1].replace(ADDRESS_PROBE_PATH, pathname);

        // Known: the address checks the managed lane's first cloud smoke recorded — three origins, three nonces.
        for (const blockedURI of SMOKE_ADDRESS_CHECKS) expect(known(blockedURI), `the address check of a link sent to ${new URL(blockedURI).origin}, as the smoke recorded it`).toBe(true);
        // Known: whatever the origin and the query.
        expect(known('https://folio.example/api/v1/auth/address-probe'), 'an https origin, and no query at all').toBe(true);
        expect(known('http://[::1]:6182/api/v1/auth/address-probe?nonce=x'), 'an IPv6 origin').toBe(true);

        // Not known: another path at the same origin, with the same nonce — the entry's path, whole, and nothing else.
        expect(known(withPath('/api/v1/auth/address-probe/x')), 'a path below it: the entry’s path is no prefix').toBe(false);
        expect(known(withPath('/api/v1/auth/address-probes')), 'a longer name that begins with it').toBe(false);
        expect(known(withPath('/api/v1/auth/')), 'a path it begins with').toBe(false);
        expect(known(withPath('/librefolio/api/v1/auth/address-probe')), 'a path that ends with it — the check of an address with a base path, /librefolio: the entry’s path is no suffix either').toBe(false);
        // Not known: the very same address under another directive.
        expect(known(SMOKE_ADDRESS_CHECKS[1], {directive: 'img-src', violatedDirective: 'img-src'}), 'the same address under img-src: the entry names connect-src').toBe(false);
        // Not known, and no exception: a blocked URI that is no absolute URL has no path to compare.
        for (const blockedURI of ['inline', 'eval', '', '/api/v1/auth/address-probe']) expect(known(blockedURI), `connect-src, blocked ${JSON.stringify(blockedURI)}: no absolute URL, so no path`).toBe(false);
        // Not known: an empty baseline.
        expect(known(SMOKE_ADDRESS_CHECKS[0], {}, {entries: []} as unknown as CspBaseline), 'an empty baseline knows nothing').toBe(false);
    });

    test('loadBaseline: e2e/csp-baseline.json, read as written — every entry has an id of its own, a directive, a blocked URI or a blocked path, a reason and an owner', async () => {
        const {loadBaseline} = await cspHelpers();
        const onDisk = JSON.parse(await readFile(BASELINE_FILE, 'utf8')) as {entries?: unknown};
        expect(loadBaseline(), 'loadBaseline() returns e2e/csp-baseline.json as written, read synchronously').toEqual(onDisk);
        expect(Array.isArray(onDisk.entries), 'e2e/csp-baseline.json is {"entries": [...]}').toBe(true);

        const entries = (Array.isArray(onDisk.entries) ? onDisk.entries : []) as Array<Partial<BaselineEntry>>;
        const ids = entries.map((entry) => entry.id);
        expect(
            ids.filter((id, index) => ids.indexOf(id) !== index),
            'every entry has an id of its own',
        ).toEqual([]);
        const malformed = entries.filter((entry) => !wellFormed(entry));
        expect(
            malformed,
            'every entry names a directive and a blocked URI or a blocked path (exactly one of them; a path starts with /), and — a ratchet entry is a human decision — a reason and an owner: an entry without a reason is indistinguishable from an oversight. indexInlineScript, when present, is a 0-based index',
        ).toEqual([]);
    });

    test('the baseline knows the managed lane’s findings of the first cloud smoke: cheetah-grid’s global probe (F1) and the address check of a link (F3), by the decision recorded in their entries', async () => {
        const {isKnown, loadBaseline} = await cspHelpers();
        const baseline = loadBaseline();
        const entries = baseline.entries as unknown as BaselineEntry[];
        // Neither entry names an inline script of index.html: they know their violations without a single span.
        const spans: LineSpan[] = [];
        /** The ids of the entries that know `violation`, each entry read alone: the decisions that cover it. */
        const knownBy = (violation: CspViolation) => entries.filter((entry) => isKnown(violation, {entries: [entry]} as unknown as CspBaseline, spans)).map((entry) => entry.id);
        // F1 from files.spec.ts (the BRIM table preview) and F3's three addresses from admin-users.spec.ts AUSR-E-07, as the managed lane recorded them.
        const findings = [{finding: 'F1', violation: syntheticViolation(SMOKE_GLOBAL_PROBE), entry: F1_ENTRY}, ...SMOKE_ADDRESS_CHECKS.map((blockedURI) => ({finding: 'F3', violation: addressCheck(blockedURI), entry: F3_ENTRY}))];

        const verdicts = findings.map(({finding, violation}) => ({finding, blockedURI: violation.blockedURI, known: isKnown(violation, baseline, spans), knownBy: knownBy(violation)}));
        const decided = findings.map(({finding, violation, entry}) => ({finding, blockedURI: violation.blockedURI, known: true, knownBy: [entry]}));
        const ids = entries.map((entry) => entry.id).join(', ');
        const ratchet = "A ratchet: an entry is removed by the lot that cures it, which updates this test — D4 narrows F1 with 'report-sample'; A and the enforcement lot cure F3";
        expect(verdicts, `e2e/csp-baseline.json knows each finding by the entry recorded for it, and by no other: F1 by equality on script-src and eval, F3 by the path of the blocked address, whatever its origin and nonce (entries: ${ids}). ${ratchet}`).toEqual(decided);
    });
});

test.describe("H-43 part B, the collector on synthetic documents served under script-src 'self' report-only", () => {
    test.skip(KILL_SWITCH_ON, COLLECTOR_OFF);

    test.describe('with cspFailOnUnknown: false — recorded, never failed for', () => {
        test.use({cspFailOnUnknown: false});

        test('report-only: one inline script is recorded once — script-src-elem, inline, reported, at its line — and still runs; unknown, and the test passes all the same', async ({page, baseURL, cspViolations}) => {
            const url = `${syntheticDir(baseURL)}one.html`;
            const token = `csp-collector ${uniqueSuffix()} one`;
            await recordWhatThePageSees(page);
            await serveSynthetic(page, url, syntheticDocument(token));

            await page.goto(url);
            await expect(page, 'the inline script ran: a report-only policy reports, it never blocks').toHaveTitle(token);
            expect(await bindingType(page), `the collector’s binding, ${BINDING}, is in the page`).toBe('function');

            const mine = await collectedFor(page, cspViolations, url, 1, 'the synthetic document');
            expect(mine, `one violation: the inline script — script-src-elem, inline, reported — at line ${SYNTHETIC_SCRIPT_LINE}, its own, with the document as its source`).toEqual([
                expect.objectContaining({
                    directive: 'script-src-elem',
                    violatedDirective: expect.stringContaining('script-src'),
                    blockedURI: 'inline',
                    disposition: 'report',
                    documentURI: url,
                    sourceFile: url,
                    lineNumber: SYNTHETIC_SCRIPT_LINE,
                    columnNumber: expect.any(Number),
                    sample: expect.any(String),
                }),
            ]);
            expect(cspViolations.list(), 'and nothing else: the test loaded one document, with one inline script').toEqual(mine);
            expect(mine.map(asSeen), 'the collector holds what the page dispatched, field for field').toEqual((await seenByPage(page)).map(asSeen));
            expect(cspViolations.unknown(), `unknown — line ${SYNTHETIC_SCRIPT_LINE} is in no inline script of index.html — and the test passes all the same: cspFailOnUnknown is false`).toEqual(mine);
        });

        test('a navigation: two documents in a row, the violations of both recorded — the binding and the listener come back with each document', async ({page, baseURL, cspViolations}) => {
            const dir = syntheticDir(baseURL);
            const first = `${dir}one.html`;
            const second = `${dir}two.html`;
            const suffix = uniqueSuffix();
            const firstToken = `csp-collector ${suffix} one`;
            const secondToken = `csp-collector ${suffix} two`;
            await serveSynthetic(page, first, syntheticDocument(firstToken, 'two.html'));
            await serveSynthetic(page, second, syntheticDocument(secondToken));

            await page.goto(first);
            await expect(page, 'the first document’s inline script ran').toHaveTitle(firstToken);
            await collectedFor(page, cspViolations, first, 1, 'the first document');

            // The page navigates itself: a link of the first document, a new document in the same page.
            await page.locator('#next').click();
            await page.waitForURL((address) => address.href === second);
            await expect(page, 'the second document’s inline script ran').toHaveTitle(secondToken);
            await collectedFor(page, cspViolations, second, 1, 'the second document, after the navigation');

            const recordedPerDocument = cspViolations.list().map((recorded) => ({documentURI: recorded.documentURI, directive: recorded.directive, blockedURI: recorded.blockedURI, lineNumber: recorded.lineNumber}));
            expect(recordedPerDocument, 'one violation per document, in the order they were loaded, and nothing else').toEqual([
                {documentURI: first, directive: 'script-src-elem', blockedURI: 'inline', lineNumber: SYNTHETIC_SCRIPT_LINE},
                {documentURI: second, directive: 'script-src-elem', blockedURI: 'inline', lineNumber: SYNTHETIC_SCRIPT_LINE},
            ]);
        });
    });

    test('an unknown violation fails the test at teardown, cspFailOnUnknown at its default — an expected failure: Playwright reports this test passed only if it did fail', async ({page, baseURL, cspViolations, cspFailOnUnknown}) => {
        expect(cspFailOnUnknown, 'precondition: cspFailOnUnknown at its default, true').toBe(true);
        const url = `${syntheticDir(baseURL)}one.html`;
        const token = `csp-collector ${uniqueSuffix()} unknown`;
        await serveSynthetic(page, url, syntheticDocument(token));

        await page.goto(url);
        await expect(page, 'the inline script ran').toHaveTitle(token);
        const mine = await collectedFor(page, cspViolations, url, 1, 'the synthetic document');
        expect(cspViolations.unknown(), `precondition: the baseline does not know it — line ${SYNTHETIC_SCRIPT_LINE} of a synthetic document`).toEqual(mine);

        // Up to here every red is a real one: the test is still expected to pass. From here on it is expected to fail — at
        // teardown, where the collector finds the unknown violation above with cspFailOnUnknown on. Playwright then reports
        // it passed only if it did fail; «Expected to fail, but passed» means the collector let an unknown violation through.
        test.fail(true, 'H-43: the collector fails this test at teardown, on the unknown violation recorded above');
    });
});

test.describe('H-43 part B, the baseline against the real app: the sign-in page under the managed profile’s report-only policy', () => {
    test.skip(KILL_SWITCH_ON, COLLECTOR_OFF);

    test('index.html, the sign-in page, reports its two inline scripts and nothing else, and the baseline knows both — the managed lane’s day one, proven on any lane', async ({page, context, baseURL, cspViolations}, testInfo) => {
        // The app's chunks, its session check and its first drawing, then the collector's reads: more than the 30 s default.
        test.setTimeout(2 * PAGE_TIMEOUT_MS);
        const {inlineScriptLines, isKnown, loadBaseline} = await cspHelpers();
        const served: ServedDocument[] = [];
        await underTheReportOnlyPolicy(context, laneOrigin(baseURL), served);
        await recordWhatThePageSees(page);

        const response = await page.goto('/', {timeout: PAGE_TIMEOUT_MS});
        const signIn = served.find((document) => document.path === '/');
        expect(signIn?.html ?? null, `precondition: the lane served the web app’s index.html at /, as HTML, through this spec’s route — an unbuilt frontend answers JSON there (documents served: ${described(served)})`).not.toBeNull();
        const policySource = signIn?.injected ? 'added by this spec: a self-hosted lane' : 'sent by the lane itself, a managed lane: this spec’s copy of CSP_REPORT_ONLY_POLICY must equal security_headers.py’s';
        expect(response?.headers()[REPORT_ONLY_HEADER], `the sign-in page reached the browser under the report-only policy of the managed profile, once (${policySource})`).toBe(CSP_REPORT_ONLY_POLICY);
        await expect(page.getByTestId('login-page'), 'the app booted under the policy and drew its sign-in page').toBeVisible({timeout: PAGE_TIMEOUT_MS});

        const spans = inlineScriptLines(signIn?.html ?? '');
        expect(spans, 'premise: the built index.html has two inline scripts — app.html’s (theme, PWA prompt, service worker) and SvelteKit’s bootstrap. A third needs a baseline entry, or a hash').toHaveLength(2);

        await expect.poll(() => cspViolations.list().length, {message: 'the violations of the inline scripts reached the collector', timeout: VIOLATION_TIMEOUT_MS}).toBeGreaterThanOrEqual(spans.length);
        // The page's own record first — a round trip through the page — then the collector's: what the page had dispatched has arrived.
        const seen = await seenByPage(page);
        const collected = [...cspViolations.list()];
        const collectorUnknown = [...cspViolations.unknown()];
        const baseline = loadBaseline();
        await testInfo.attach('csp-collector-sign-in.json', {body: JSON.stringify({policy: response?.headers()[REPORT_ONLY_HEADER] ?? null, policySource, spans, seen, collected, unknown: collectorUnknown}, null, 1), contentType: 'application/json'});

        expect(collected.map(asSeen), `the collector holds what the page dispatched, no more and no less — it holds:\n${listed(collected)}`).toEqual(seen.map(asSeen));
        const others = collected.filter((recorded) => inlineScriptOf(recorded, spans) === -1);
        expect(others, `the sign-in page reported violations beyond its inline scripts (spans ${JSON.stringify(spans)}):\n${listed(others)}`).toEqual([]);
        const perInlineScript = spans.map((_, index) => collected.filter((recorded) => inlineScriptOf(recorded, spans) === index).length);
        expect(perInlineScript, `one violation per inline script — script-src-elem, inline, reported, at a line of its span ${JSON.stringify(spans)}:\n${listed(collected)}`).toEqual(spans.map(() => 1));
        const notKnown = collected.filter((recorded) => !isKnown(recorded, baseline, spans));
        expect(notKnown, `e2e/csp-baseline.json knows both inline scripts:\n${listed(notKnown)}`).toEqual([]);
        expect(collectorUnknown, `and the collector agrees, so its teardown fails nothing:\n${listed(collectorUnknown)}`).toEqual([]);

        const entries = baseline.entries as unknown as BaselineEntry[];
        const stale = entries.filter((entry) => typeof entry.indexInlineScript === 'number' && !collected.some((recorded) => isKnown(recorded, {entries: [entry]} as unknown as CspBaseline, spans)));
        expect(
            stale.map((entry) => entry.id),
            'every entry naming an inline script of index.html matches one the sign-in page reported: the baseline is a ratchet, and a stale entry is dropped',
        ).toEqual([]);
    });
});

test.describe('H-43 part B, the kill switch: a run started with E2E_CSP_COLLECTOR=0', () => {
    test.skip(!KILL_SWITCH_ON, 'Runs only in a run started with E2E_CSP_COLLECTOR=0: the collector is on in this one, and the tests above cover it');

    test('the collector records nothing and fails nothing: no binding in the page, an empty record, and an unknown violation the page did raise goes unseen', async ({page, baseURL, cspViolations, cspFailOnUnknown}) => {
        expect(cspFailOnUnknown, 'precondition: cspFailOnUnknown at its default, true — a collector that did record would fail this test').toBe(true);
        const url = `${syntheticDir(baseURL)}one.html`;
        const token = `csp-collector ${uniqueSuffix()} kill switch`;
        await recordWhatThePageSees(page);
        await serveSynthetic(page, url, syntheticDocument(token));

        await page.goto(url);
        await expect(page, 'the inline script ran').toHaveTitle(token);
        await expect.poll(async () => (await seenByPage(page)).length, {message: 'the page raised its violation: there was something to collect', timeout: VIOLATION_TIMEOUT_MS}).toBe(1);
        expect(await bindingType(page), `no ${BINDING} in the page: with the switch, the collector exposes no binding`).toBe('undefined');
        // Those reads were round trips through the page: anything it had sent a collector has arrived by now.
        expect(cspViolations.list(), 'the record holds nothing').toEqual([]);
        expect(cspViolations.unknown(), 'nothing unknown either: this test passes, and its teardown fails nothing').toEqual([]);
    });
});
