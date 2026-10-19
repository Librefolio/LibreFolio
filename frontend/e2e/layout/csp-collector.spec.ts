/**
 * The collector of Content-Security-Policy report-only violations (H-43 part B), in the fixture every spec imports, and
 * the policy it watches since H-52: every inline script of the build allowed by its hash, an eval known by its sample.
 *
 * Why. In the managed profile the server sends `Content-Security-Policy-Report-Only` on the HTML pages of the web app,
 * and nobody sees its violations: the browser reports them in its console, and there is no report endpoint. Each one is
 * something a CSP applied tomorrow would block. The collector turns them into reds: an auto fixture of
 * e2e/fixtures/playwright.ts records every `securitypolicyviolation` of every document of the test and, at teardown,
 * fails the test on any violation that e2e/csp-baseline.json does not know.
 *
 * The policy (H-52). `CSP_REPORT_ONLY_POLICY` (backend/app/services/platform/security_headers.py) has
 * `script-src 'self' 'wasm-unsafe-eval' 'report-sample'`. A managed lane sends it with, appended to `script-src` after
 * `'report-sample'`, the `'sha256-<base64>'` of every `<script>` without `src`, of any type, of every top-level page of
 * the build — its text with the newlines the HTML parser leaves (CRLF and a lone CR become LF), in UTF-8 — sorted, each
 * once, computed once when the server starts (D-H52-1). Three pages: index.html (app.html's script — the theme before
 * the first paint, the PWA prompt, the service worker — and SvelteKit's bootstrap), 200.html (the SPA fallback: the
 * same script of app.html, another bootstrap) and offline.html (one script). Their inline scripts report nothing any
 * more, and the line spans of H-43, by which the baseline knew two of them, are gone (D-H52-2). An inline event handler
 * is `script-src-attr`, which no hash of `script-src` covers: offline.html's retry button listens through its script
 * instead (D-H52-3). `'report-sample'` gives the violation of an eval its sample, the first 40 characters of the code.
 *
 * The baseline has two entries, each owned by the lot that cures it: cheetah-grid's bundled probe of the global object,
 * `new Function("return this")()`, an `eval` known by its exact sample (F1, D-H52-4) — istanbul's preamble reports the
 * very same in a build instrumented for coverage — so that any other eval is unknown, and fails the test that meets it;
 * and the address check of a link, a `connect-src` to whatever address an administrator typed, a nonce in its query
 * (F3).
 *
 * The contract the cure is held to here:
 *   - `cspViolations`, an auto fixture, test-scoped. Unless the kill switch is set it exposes the binding
 *     `__lfCspViolation` to the browser context and registers, in every document, a capture listener of
 *     `securitypolicyviolation` on `document` that sends the binding {directive (the effective one), violatedDirective,
 *     blockedURI, sourceFile, lineNumber, columnNumber, sample, disposition, documentURI}. Its value: `list()`, every
 *     violation received, and `unknown()`, those the baseline does not know;
 *   - `cspFailOnUnknown`, an option, true by default: at teardown an unknown violation fails the test with a readable
 *     list. `test.use({cspFailOnUnknown: false})` keeps the record and fails nothing;
 *   - e2e/fixtures/csp.ts, the pure logic: `cspCollectorEnabled(env)`, `isKnown(violation, baseline)` and
 *     `loadBaseline()`; no `inlineScriptLines` any more. A violation is known when a baseline entry names its directive
 *     and what it blocked and, for an entry with `sample`, its sample is exactly that one: an entry without `sample`
 *     reads none. An entry names what was blocked by exactly one of `blockedURI`, the blocked URI itself, and
 *     `blockedPath`, the path of the blocked address (`new URL(blockedURI).pathname`) whatever its origin and query: a
 *     blocked URI that is no absolute URL — `inline`, `eval`, empty, a bare path — has no path, and no `blockedPath`
 *     entry knows it.
 *
 * The tests:
 *   1. the pure logic, on synthetic input, without a page; then the real baseline against the managed lane's findings of
 *      the first cloud smoke — F1 by its sample, F3 by its path — and an eval of anything else, which it must not know;
 *   2. this spec's own reading of a page — the text of its inline scripts, their hashes, its inline event handlers — and
 *      the policy it builds from them, on synthetic input: a known vector, and a handler it must find. Tests 6 and 7
 *      check the backend with it, and import nothing of the backend's computation;
 *   3. a synthetic document with one inline script, served by this spec under `script-src 'self'` report-only: the
 *      violation is recorded once, field for field as the page itself saw it; the script still ran; it is unknown, and
 *      the test passes all the same (`cspFailOnUnknown: false`);
 *   4. the same kind of unknown violation with the option at its default: the test must fail at teardown. It is marked
 *      with `test.fail()` once its body has checked all it can, so that Playwright reports it passed only if it did fail,
 *      and a red of the body itself stays a red;
 *   5. a navigation: two synthetic documents in a row, both recorded — the binding and the listener come back with every
 *      document;
 *   6. the real app: the lane's `/` — index.html, the sign-in page — under the policy this spec computes from the three
 *      pages of the lane reports no violation at all, as the page and the collector both saw it (a build instrumented for
 *      coverage adds istanbul's probes of the global object, which are left out). Then a control proves the silence was
 *      measured: a script of the lane's origin probes the global object as cheetah-grid does, and both record its eval
 *      with F1's sample — `'report-sample'` is in force — known by F1's entry alone;
 *   7. the offline page, `/offline.html`, under the same policy: it loads with no violation, its script allowed by its
 *      hash; no page of the build has an inline event-handler attribute; a click on its retry button loads it again, with
 *      no violation either;
 *   8. the kill switch, below.
 *
 * Lanes. The spec brings the headers it needs, so it runs on a self-hosted lane (`front-utility csp-collector`) as on a
 * managed one (the cloud smoke). The synthetic documents never reach the server. The documents of the app pass through a
 * route that adds the policy this spec computes only when the lane did not send one: on a managed lane the server's own
 * header goes through untouched — never two policies, which would report every violation twice — and must equal this
 * spec's to the letter, on every page of the build: the backend's computation, checked from one end to the other.
 *
 * The kill switch. `E2E_CSP_COLLECTOR=0` in the environment of a run turns the collector off for the whole run: no
 * binding, no listener, a recorder that holds nothing and fails nothing. A test cannot change its worker's environment,
 * so the switch is proven two ways: `cspCollectorEnabled` purely (test 1, in every run), and the last test of this file,
 * which runs only in a run started with the switch — the collector's own tests skip there.
 *
 * Before H-52's cure. Test 1 fails where the contract moved: csp.ts still exports `inlineScriptLines`, `isKnown` reads
 * no sample (so F1's entry knows every eval), and two entries of the baseline still carry `indexInlineScript`. On a
 * managed lane the server still sends the policy without `'report-sample'` and without a hash: tests 6 and 7 fail on its
 * header. On a self-hosted lane this spec injects its own policy: test 6 passes, the sign-in page owing nothing to the
 * cure, and test 7 fails on offline.html's `onclick`. Tests 2 to 5 pass before as after.
 *
 * Loading. The pure tests import e2e/fixtures/csp.ts at run time, not with the file: a missing helper is an assertion
 * that names it, never a load error.
 *
 * Selectors: `data-testid` in the app (`login-page`). offline.html is a static page with no testid, whose markup is not
 * this spec's to change: its retry button is the button around `#retry-text`, the page's own handle. The synthetic
 * documents are this spec's own and use a plain id.
 * Waiting: on states, never on the clock — the title an inline script sets, the collector's list polled until it holds
 * what the page dispatched, then one round trip through the page, so that anything sent with it has arrived too; a
 * reload, by a key of the window that the document loaded again no longer has, and the route's record of that document.
 * Data: nothing is written; the routes and the record die with the test's browser context.
 * Not asserted here: the `csp-violations` attachment and the readable message of the teardown failure. Both are made
 * after every hook and every other fixture of the test has finished, where no spec can read them; the report shows them.
 */
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {expect, test, type APIRequestContext, type BrowserContext, type Page} from '../fixtures/playwright';
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

/**
 * An entry of e2e/csp-baseline.json, as the contract writes it: it names what was blocked by exactly one of blockedURI
 * and blockedPath, and may narrow itself to one sample.
 */
interface BaselineEntry {
    id: string;
    directive: string;
    /** The blocked URI itself, compared whole: `inline`, `eval`, an address. */
    blockedURI?: string;
    /** The path of the blocked address, `new URL(blockedURI).pathname`, whatever its origin and query. */
    blockedPath?: string;
    /** The violation's sample, compared whole: the first 40 characters of the code it concerns, which `'report-sample'` reports. */
    sample?: string;
    reason: string;
    owner: string;
}

/**
 * The keys an entry may have, by the contract: what `isKnown` reads, and the human decision behind it. A key nobody reads
 * makes an entry look narrower than it is — `indexInlineScript`, the line spans of H-43, among them since H-52.
 */
const ENTRY_KEYS: ReadonlySet<string> = new Set(['id', 'directive', 'blockedURI', 'blockedPath', 'sample', 'reason', 'owner']);

/** A violation as the page itself saw it, through this spec's own recorder: the browser's word, which the collector is held to. */
interface SeenViolation {
    directive: string;
    blockedURI: string;
    lineNumber: number;
    documentURI: string;
    disposition: string;
    sample: string;
    sourceFile: string;
}

/** The fields by which a violation of the page's record and one of the collector's are held against each other: asSeen(). */
type SeenFields = Pick<SeenViolation, 'directive' | 'blockedURI' | 'lineNumber' | 'documentURI' | 'disposition'>;

/** What tells istanbul's probe of the global object apart (isIstanbulProbe), in this spec's record as in the collector's. */
type Sampled = Pick<SeenViolation, 'directive' | 'blockedURI' | 'sample' | 'sourceFile'>;

/** A document of the lane the route answered, and where its report-only policy came from. */
interface ServedDocument {
    path: string;
    status: number;
    contentType: string;
    /** The report-only policy the lane sent itself: none on a self-hosted lane, CSP_REPORT_ONLY_POLICY with the hashes on a managed one. */
    lanePolicy: string | null;
    /** Whether the spec added its policy: an HTML answer the lane sent without a report-only policy. */
    injected: boolean;
    /** The HTML as served — the document whose inline scripts the policy hashes; null for any other answer. */
    html: string | null;
    /** Why the route could not fetch it: the document was refused, never let through without the policy. */
    failure: string | null;
}

/** A top-level page of the build, as the lane serves it: what this spec computes the policy from. */
interface BuildPage {
    path: string;
    file: string;
    html: string;
    /** The report-only policy the lane sent with it: none on a self-hosted lane. */
    lanePolicy: string | null;
}

/** A start tag, as this spec reads it: its name and the names of its attributes, lowercase. */
interface ScannedTag {
    name: string;
    attributes: string[];
}

/** An HTML document, as this spec reads it: its start tags, and the text of each of its inline scripts. */
interface ScannedHtml {
    tags: ScannedTag[];
    inlineScripts: string[];
}

/**
 * The report-only policy of the web app's pages in the managed profile, before its hashes: `CSP_REPORT_ONLY_POLICY` in
 * backend/app/services/platform/security_headers.py, copied, not read. A managed lane sends it with, after
 * `'report-sample'`, the hashes of the build's inline scripts. This spec computes the same — expectedPolicy() — adds it to
 * the app's documents on a self-hosted lane, which sends none, and holds a managed lane's header to it, to the letter.
 */
const CSP_REPORT_ONLY_POLICY = [
    "default-src 'self'",
    "script-src 'self' 'wasm-unsafe-eval' 'report-sample'",
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

/**
 * The top-level pages of the build, as the lane serves them: the sign-in page, the SPA fallback that answers every other
 * route, and the offline page. The policy holds the hash of every inline script of each. A fourth page needs its line
 * here: a managed lane hashes every top-level page of the build, and its header would no longer equal this spec's.
 */
const BUILD_PAGES = [
    {path: '/', file: 'index.html'},
    {path: '/200.html', file: '200.html'},
    {path: '/offline.html', file: 'offline.html'},
] as const;
const SIGN_IN_PATH = '/';
const OFFLINE_PATH = '/offline.html';
/** offline.html's own check of the server, every ten seconds (`tryReconnect`): once the server answers, the page loads itself again. */
const OFFLINE_HEALTH_PATH = '/api/v1/system/health';
/** A key this spec defines on offline.html's window before its retry: a document without it is a new one. */
const RELOAD_MARKER = '__lfCspCollectorSpecBeforeRetry';
/** The elements whose content the HTML tokenizer reads as text, up to their end tag: no tag and no comment inside one. */
const TEXT_ELEMENTS: ReadonlySet<string> = new Set(['script', 'style', 'textarea', 'title', 'xmp', 'iframe', 'noembed', 'noframes', 'noscript']);

/** The policy of the synthetic documents: their inline script is reported, and nothing else of theirs is concerned. */
const SYNTHETIC_POLICY = "script-src 'self'";
/**
 * The line of a synthetic document's inline script, the whole element on it, so that any reading of «its line» gives this
 * one. Unknown wherever it sits: since H-52 the baseline knows no inline script.
 */
const SYNTHETIC_SCRIPT_LINE = 5;
/** The binding the collector exposes to every browser context, by the contract: what the kill switch leaves out. */
const BINDING = '__lfCspViolation';
/** The window array where this spec's own recorder keeps what each document dispatched. */
const SEEN_KEY = '__lfCspCollectorSpecSeen';
/** e2e/csp-baseline.json, the baseline `loadBaseline()` reads. */
const BASELINE_FILE = fileURLToPath(new URL('../csp-baseline.json', import.meta.url));
/** What e2e/fixtures/csp.ts exports, by the contract. */
const HELPERS = ['cspCollectorEnabled', 'isKnown', 'loadBaseline'] as const;
/** The owner of this spec's synthetic baseline entries. */
const OWNER = 'layout/csp-collector.spec.ts';

/** The path of the address check of a link (`PROBE_PATH`, settings/users/addressProbe.ts), copied: `GET <the address an administrator typed>/api/v1/auth/address-probe?nonce=…`. */
const ADDRESS_PROBE_PATH = '/api/v1/auth/address-probe';
/** The managed lane whose first cloud smoke found F1 and F3: the origin its pages were served at. */
const SMOKE_LANE = 'http://localhost:6181';
/**
 * The sample of the probe of the global object of cheetah-grid's bundle, and of istanbul's preamble: under
 * `'report-sample'`, Chromium (149, H-52's probe) reports `new Function("return this")()` with the source it evaluates,
 * whole — 39 characters, under the 40 a sample keeps.
 */
const GLOBAL_PROBE_SAMPLE = '(function anonymous(\n) {\nreturn this\n})';
/** The control of test 6: a script of the lane's origin that probes the global object as cheetah-grid's bundle does. */
const GLOBAL_PROBE_SCRIPT = 'new Function("return this")();\n';
/**
 * F1 as that smoke recorded it, in files.spec.ts's BRIM table preview: cheetah-grid's bundled webpack probe of the global
 * object, `new Function("return this")()` in a try/catch that falls back to `window` — `script-src`, `eval`, from its
 * chunk — with the sample `'report-sample'` gives it, which that smoke's policy did not have yet: it recorded none.
 */
const SMOKE_GLOBAL_PROBE: Partial<CspViolation> = {directive: 'script-src', violatedDirective: 'script-src', blockedURI: 'eval', sourceFile: `${SMOKE_LANE}/_app/immutable/chunks/Cn5CY6Wr.js`, lineNumber: 758, sample: GLOBAL_PROBE_SAMPLE, documentURI: `${SMOKE_LANE}/files?tab=brim`};
/** An eval of other code, in another chunk of the app — its name made up — sampled: what F1's entry knew too, until H-52 narrowed it to its sample. */
const OTHER_EVAL: Partial<CspViolation> = {...SMOKE_GLOBAL_PROBE, sourceFile: `${SMOKE_LANE}/_app/immutable/chunks/Bq7rT2Lx.js`, lineNumber: 12, sample: '1 + 1'};
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
/** The entry of e2e/csp-baseline.json recorded for F1: equality on `script-src`, `eval` and its sample. */
const F1_ENTRY = 'cheetah-grid-global-probe';
/** The entry recorded for F3: `connect-src`, and the path of the blocked address. */
const F3_ENTRY = 'address-probe-other-origin';

/** The kill switch as this spec reads it to choose its tests: the rule of `cspCollectorEnabled`, which test 1 holds to it. */
const KILL_SWITCH_ON = process.env.E2E_CSP_COLLECTOR === '0';
const COLLECTOR_OFF = 'E2E_CSP_COLLECTOR=0: the collector is off for this whole run, and the kill-switch test at the end of this file covers it';

/** A violation: dispatched by the browser in a task after the parser's, then carried to the test by the binding. */
const VIOLATION_TIMEOUT_MS = 10_000;
/** A page of the lane: the app's chunks, its session check, then its first drawing — on a loaded machine. */
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
                seen.push({directive: event.effectiveDirective, blockedURI: event.blockedURI, lineNumber: event.lineNumber, documentURI: event.documentURI, disposition: event.disposition, sample: event.sample, sourceFile: event.sourceFile});
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
function asSeen(violation: SeenFields): SeenFields {
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

/**
 * The violations the collector holds that came from the script at `sourceFile`, once it holds `count` of them: polled,
 * then read again after one round trip through the page, as collectedFor() reads those of a document.
 */
async function collectedFrom(page: Page, csp: CspRecorder, sourceFile: string, count: number, what: string): Promise<CspViolation[]> {
    const fromScript = () => csp.list().filter((violation) => violation.sourceFile === sourceFile);
    await expect.poll(fromScript, {message: `${what}: the collector received ${count} violation(s) from ${sourceFile}`, timeout: VIOLATION_TIMEOUT_MS}).toHaveLength(count);
    await page.evaluate(() => undefined);
    return fromScript();
}

/** One line per violation, for a red: disposition, directive, what it blocked, its sample, where, and in which document. */
function listed(violations: readonly CspViolation[]): string {
    if (violations.length === 0) return '  (none)';
    return violations
        .map((violation) => `  ${violation.disposition} ${violation.directive}: blocked ${violation.blockedURI || '(no URI)'}${violation.sample ? `, sample ${JSON.stringify(violation.sample)}` : ''} at ${violation.sourceFile || '(no source)'}:${violation.lineNumber} in ${violation.documentURI}`)
        .join('\n');
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

/** A violation as the collector records it: by default, an inline script of the lane's `/` — script-src-elem, inline, reported, on line 14, no sample. */
function syntheticViolation(overrides: Partial<CspViolation>): CspViolation {
    const documentURI = 'http://localhost:6041/';
    return {directive: 'script-src-elem', violatedDirective: 'script-src-elem', blockedURI: 'inline', sourceFile: documentURI, lineNumber: 14, columnNumber: 0, sample: '', disposition: 'report', documentURI, ...overrides} as CspViolation;
}

/**
 * F3's kind of violation, the address check of a link sent to `blockedURI`: `connect-src`, reported, from an app chunk — its
 * name made up — on Settings › Users. Its line is immaterial: no entry reads one.
 */
function addressCheck(blockedURI: string, overrides: Partial<CspViolation> = {}): CspViolation {
    return syntheticViolation({directive: 'connect-src', violatedDirective: 'connect-src', blockedURI, sourceFile: `${SMOKE_LANE}/_app/immutable/chunks/DkQ7v2Xa.js`, lineNumber: 1, documentURI: `${SMOKE_LANE}/settings?tab=users`, ...overrides});
}

/** A baseline of `entries`, as `isKnown` takes it. */
function baselineOf(...entries: BaselineEntry[]): CspBaseline {
    return {entries} as unknown as CspBaseline;
}

/** The ids of the entries of `baseline` that know `violation`, each entry read alone: the decisions that cover it. */
function knownBy(isKnown: CspHelpers['isKnown'], baseline: CspBaseline, violation: CspViolation): string[] {
    const entries = baseline.entries as unknown as BaselineEntry[];
    return entries.filter((entry) => isKnown(violation, baselineOf(entry))).map((entry) => entry.id);
}

/**
 * An entry a ratchet can trust: an id, a directive, what was blocked — by exactly one of a blocked URI and a blocked path,
 * written as a URL's pathname is, from its leading `/` — a sample only as a real one, a string of at least one character,
 * the human decision behind it, a reason and an owner, and no key the contract does not name.
 */
function wellFormed(entry: Partial<BaselineEntry>): boolean {
    const named = (value: unknown) => typeof value === 'string' && value.trim() !== '';
    const blocked = entry.blockedPath === undefined ? named(entry.blockedURI) : entry.blockedURI === undefined && typeof entry.blockedPath === 'string' && entry.blockedPath.startsWith('/');
    const sampled = entry.sample === undefined || (typeof entry.sample === 'string' && entry.sample.length > 0);
    const contractKeys = Object.keys(entry).every((key) => ENTRY_KEYS.has(key));
    return named(entry.id) && named(entry.directive) && blocked && sampled && named(entry.reason) && named(entry.owner) && contractKeys;
}

/** An HTML answer: a Content-Type starting with `text/html`, in any case. */
function isHtml(contentType: string): boolean {
    return contentType.toLowerCase().startsWith('text/html');
}

/**
 * Gives every HTML document of the lane `policy` as its report-only policy, once: a document request — a navigation or a
 * frame — is fetched by the spec and answered with the lane's own answer, `policy` added only when the lane sent no
 * report-only policy itself. A managed lane's header goes through untouched: two policies would report every violation
 * twice, and the caller holds the lane's own to `policy`. Every other request passes. Before the first navigation.
 */
async function underTheReportOnlyPolicy(context: BrowserContext, origin: string, policy: string, served: ServedDocument[]): Promise<void> {
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
                await route.fulfill(injected ? {response, headers: {...headers, [REPORT_ONLY_HEADER]: policy}} : {response});
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

/**
 * This spec's own reading of an HTML document — nothing shared with the backend, whose computation it checks: its start
 * tags with the names of their attributes, lowercase, and the text of every inline script — every `<script>` without a
 * `src` attribute, of any type — as written. A comment is skipped, and so is the content of an element the tokenizer
 * reads as text (TEXT_ELEMENTS): a `<script>` in a comment or in a `<style>` is none, an `onclick` in a script's code is
 * no attribute. A quoted attribute value may hold a `>`.
 */
function scanHtml(html: string): ScannedHtml {
    const tags: ScannedTag[] = [];
    const inlineScripts: string[] = [];
    const startTag = /<([a-zA-Z][^\s/>]*)/y;
    const separator = /[\s/]*/y;
    const attribute = /([^\s/>][^\s/>=]*)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]*))?/y;
    let at = html.indexOf('<');
    while (at !== -1) {
        if (html.startsWith('<!--', at)) {
            const close = html.indexOf('-->', at + 4);
            at = close === -1 ? -1 : html.indexOf('<', close + 3);
            continue;
        }
        startTag.lastIndex = at;
        const open = startTag.exec(html);
        if (open === null) {
            // An end tag, a doctype, a `<` of the text: nothing this spec reads.
            at = html.indexOf('<', at + 1);
            continue;
        }
        const name = open[1].toLowerCase();
        const attributes: string[] = [];
        let cursor = startTag.lastIndex;
        for (;;) {
            separator.lastIndex = cursor;
            separator.exec(html);
            cursor = separator.lastIndex;
            if (cursor >= html.length || html[cursor] === '>') break;
            attribute.lastIndex = cursor;
            const match = attribute.exec(html);
            if (match === null) {
                cursor += 1;
                continue;
            }
            attributes.push(match[1].toLowerCase());
            cursor = attribute.lastIndex;
        }
        tags.push({name, attributes});
        let next = cursor + 1;
        if (TEXT_ELEMENTS.has(name)) {
            // Its content is text up to its end tag: `</` and its name, then a space, a `/` or a `>`, in any case.
            const end = new RegExp(`</${name}[\\s/>]`, 'gi');
            end.lastIndex = next;
            const closing = end.exec(html);
            const contentEnd = closing === null ? html.length : closing.index;
            if (name === 'script' && !attributes.includes('src')) inlineScripts.push(html.slice(next, contentEnd));
            next = contentEnd;
        }
        at = html.indexOf('<', next);
    }
    return {tags, inlineScripts};
}

/** The inline event-handler attributes of an HTML document — an `on<name>` attribute of a start tag — each as `<tag> <attribute>`. */
function inlineEventHandlers(html: string): string[] {
    return scanHtml(html).tags.flatMap(({name, attributes}) => attributes.filter((attribute) => /^on[a-z]+$/.test(attribute)).map((attribute) => `${name} ${attribute}`));
}

/**
 * The hash source of an inline script, as the browser compares it: its text with the newlines the HTML parser leaves —
 * CRLF and a lone CR become LF, and nothing else changes — in UTF-8, SHA-256, base64. Node's own, not the backend's.
 */
function scriptHash(text: string): string {
    return `'sha256-${createHash('sha256').update(text.replace(/\r\n?/g, '\n'), 'utf8').digest('base64')}'`;
}

/** `policy` with `hashes` appended to its `script-src`, after what it holds: sorted, each once. Every other directive as it was. */
function withHashes(policy: string, hashes: readonly string[]): string {
    const sources = [...new Set(hashes)].sort();
    return policy
        .split('; ')
        .map((directive) => (directive.split(' ')[0] === 'script-src' ? [directive, ...sources].join(' ') : directive))
        .join('; ');
}

/**
 * The pages of the build, fetched from the lane as it serves them — the input of this spec's own computation of the
 * policy — each with the report-only policy the lane sent with it. Each must be the build's HTML: an unbuilt frontend
 * answers JSON at `/`, and a 503 elsewhere.
 */
async function fetchBuildPages(request: APIRequestContext): Promise<BuildPage[]> {
    const pages: BuildPage[] = [];
    for (const {path, file} of BUILD_PAGES) {
        const response = await request.get(path);
        const headers = response.headers();
        const html = isHtml(headers['content-type'] ?? '') ? await response.text() : null;
        expect({path, status: response.status(), html: html !== null}, `precondition: the lane serves the build’s ${file} at ${path}, as HTML`).toEqual({path, status: 200, html: true});
        pages.push({path, file, html: html ?? '', lanePolicy: headers[REPORT_ONLY_HEADER] ?? null});
    }
    return pages;
}

/** The policy of a managed lane, as this spec computes it: CSP_REPORT_ONLY_POLICY with the hash of every inline script of every page of the build. */
function expectedPolicy(pages: readonly BuildPage[]): string {
    return withHashes(
        CSP_REPORT_ONLY_POLICY,
        pages.flatMap(({html}) => scanHtml(html).inlineScripts.map(scriptHash)),
    );
}

/** The page of the build at `path`. */
function pageAt(pages: readonly BuildPage[], path: string): BuildPage {
    const page = pages.find((candidate) => candidate.path === path);
    if (!page) throw new Error(`no page of the build at ${path}: BUILD_PAGES names it`);
    return page;
}

/**
 * Runs GLOBAL_PROBE_SCRIPT in the page's document as a script of the lane's origin, served by this spec at an address only
 * the current test serves: `script-src 'self'` lets it load, so only its eval is reported. Resolves once it has run, with
 * its address — the `sourceFile` of its violation.
 */
async function probeTheGlobalObject(page: Page, baseURL: string | undefined): Promise<string> {
    const url = `${syntheticDir(baseURL)}global-probe.js`;
    await page.route(
        (candidate) => candidate.href === url,
        (route) => route.fulfill({status: 200, contentType: 'text/javascript; charset=utf-8', body: GLOBAL_PROBE_SCRIPT}),
    );
    await page.evaluate(
        (src) =>
            new Promise<void>((resolve, reject) => {
                const script = document.createElement('script');
                script.src = src;
                script.addEventListener('load', () => resolve());
                script.addEventListener('error', () => reject(new Error(`the control script did not load: ${src}`)));
                document.head.append(script);
            }),
        url,
    );
    return url;
}

/**
 * In a build instrumented for JS coverage (`--coverage js`), istanbul's preamble: every instrumented module probes the
 * global object as cheetah-grid's bundle does — F1's eval, F1's sample — from a chunk of the app. F1's entry knows it,
 * and it is none of the page's own: test 6 leaves it out when the page says it is instrumented (`window.__coverage__`).
 */
function isIstanbulProbe(violation: Sampled, origin: string): boolean {
    return violation.directive === 'script-src' && violation.blockedURI === 'eval' && violation.sample === GLOBAL_PROBE_SAMPLE && violation.sourceFile.startsWith(`${origin}/_app/`);
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

    test('isKnown: known when an entry names the violation’s directive and its blocked URI, both equal, on whatever line — nothing else is: the line spans of H-43 are gone', async () => {
        const helpers = await cspHelpers();
        expect('inlineScriptLines' in helpers, 'e2e/fixtures/csp.ts exports no inlineScriptLines any more: no entry names an inline script by its lines (D-H52-2)').toBe(false);
        const {isKnown} = helpers;
        const byInlineScript = baselineOf({id: 'inline-script', directive: 'script-src-elem', blockedURI: 'inline', reason: 'synthetic', owner: OWNER});
        const known = (overrides: Partial<CspViolation>, baseline: CspBaseline = byInlineScript) => isKnown(syntheticViolation(overrides), baseline);

        // Known: its directive and its blocked URI, on any line — isKnown takes no span, and reads no line.
        for (const lineNumber of [1, 14, 116, 9_999]) expect(known({lineNumber}), `an inline script on line ${lineNumber}: script-src-elem, inline`).toBe(true);

        // Not known: another directive.
        expect(known({directive: 'style-src-elem', violatedDirective: 'style-src-elem'}), 'an inline <style>: style-src-elem').toBe(false);
        expect(known({directive: 'script-src-attr', violatedDirective: 'script-src-attr'}), 'an inline event handler: script-src-attr, not the inline script').toBe(false);
        // Not known: a blocked URI other than inline.
        expect(known({blockedURI: 'https://cdn.example.invalid/x.js'}), 'an external script: its address, not inline').toBe(false);
        expect(known({directive: 'script-src', violatedDirective: 'script-src', blockedURI: 'eval'}), 'an eval: script-src, eval').toBe(false);
        // Not known, and no exception: an empty baseline.
        expect(known({}, baselineOf()), 'an empty baseline knows nothing').toBe(false);
    });

    test('isKnown: an entry with blockedPath knows a violation of its directive whose blocked address has that path, whatever its origin and query — nothing else', async () => {
        const {isKnown} = await cspHelpers();
        const byPath = baselineOf({id: 'address-probe-other-origin', directive: 'connect-src', blockedPath: ADDRESS_PROBE_PATH, reason: 'synthetic', owner: OWNER});
        const known = (blockedURI: string, overrides: Partial<CspViolation> = {}, baseline: CspBaseline = byPath) => isKnown(addressCheck(blockedURI, overrides), baseline);
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
        expect(known(SMOKE_ADDRESS_CHECKS[0], {}, baselineOf()), 'an empty baseline knows nothing').toBe(false);
    });

    test('isKnown: an entry with a sample knows only the violation whose sample is exactly that one — not another, not an empty one, not one that merely begins the same; an entry without a sample ignores it', async () => {
        const {isKnown} = await cspHelpers();
        const narrowed = baselineOf({id: 'global-probe', directive: 'script-src', blockedURI: 'eval', sample: GLOBAL_PROBE_SAMPLE, reason: 'synthetic', owner: OWNER});
        const everyEval = baselineOf({id: 'every-eval', directive: 'script-src', blockedURI: 'eval', reason: 'synthetic', owner: OWNER});
        const sampled = (sample: string, overrides: Partial<CspViolation> = {}) => syntheticViolation({...SMOKE_GLOBAL_PROBE, sample, ...overrides});

        // Known: the entry's sample, exactly.
        expect(isKnown(sampled(GLOBAL_PROBE_SAMPLE), narrowed), 'new Function("return this")(): the entry’s sample, exactly').toBe(true);

        // Not known: another sample, or none.
        expect(isKnown(sampled('1 + 1'), narrowed), 'eval("1 + 1"): another sample').toBe(false);
        expect(isKnown(sampled(''), narrowed), "an empty sample: the same eval, reported under a policy without 'report-sample'").toBe(false);
        // Not known: a sample that merely begins as the entry's, or that the entry's begins with — compared whole, either way.
        expect(isKnown(sampled('(function anonymous(\n) {\nreturn this.x\n}'), narrowed), 'new Function("return this.x")(): its first 40 characters begin as the entry’s sample').toBe(false);
        expect(isKnown(sampled(`${GLOBAL_PROBE_SAMPLE};`), narrowed), 'the entry’s sample, and more').toBe(false);
        expect(isKnown(sampled(GLOBAL_PROBE_SAMPLE.slice(0, 20)), narrowed), 'the beginning of the entry’s sample').toBe(false);
        expect(isKnown(sampled(GLOBAL_PROBE_SAMPLE.replace(/\n/g, '\r\n')), narrowed), 'the same lines ended by CRLF: compared as they are, never normalized').toBe(false);
        // Not known: the very sample under another directive and blocked URI — a sample narrows an entry, it never widens one.
        expect(isKnown(sampled(GLOBAL_PROBE_SAMPLE, {directive: 'script-src-elem', violatedDirective: 'script-src-elem', blockedURI: 'inline'}), narrowed), 'an inline script whose first characters are those').toBe(false);

        // An entry without a sample reads none: it knows every eval, whatever its sample.
        for (const sample of [GLOBAL_PROBE_SAMPLE, '1 + 1', '']) expect(isKnown(sampled(sample), everyEval), `an entry with no sample, an eval sampled ${JSON.stringify(sample)}`).toBe(true);
    });

    test('loadBaseline: e2e/csp-baseline.json, read as written — every entry has an id of its own, a directive, a blocked URI or a blocked path, a sample only as a real one, a reason and an owner, and no other key', async () => {
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
            `every entry names a directive and a blocked URI or a blocked path (exactly one of them; a path starts with /), a sample only as a string of at least one character, and — a ratchet entry is a human decision — a reason and an owner: an entry without a reason is indistinguishable from an oversight. No key but ${[...ENTRY_KEYS].join(', ')}: one that isKnown does not read makes an entry look narrower than it is — indexInlineScript, the line spans of H-43, is gone (D-H52-2)`,
        ).toEqual([]);
    });

    test('the baseline knows the managed lane’s findings of the first cloud smoke — cheetah-grid’s global probe (F1) by its exact sample, the address check of a link (F3) by its path — and no other eval', async () => {
        const {isKnown, loadBaseline} = await cspHelpers();
        const baseline = loadBaseline();
        // F1 from files.spec.ts (the BRIM table preview) and F3's three addresses from admin-users.spec.ts AUSR-E-07, as the
        // managed lane recorded them, F1 with the sample 'report-sample' gives it. Then two evals no entry may know: other
        // code, and F1's own probe as the first smoke recorded it, before 'report-sample' — with no sample.
        const findings: Array<{finding: string; violation: CspViolation; entry: string | null}> = [
            {finding: 'F1', violation: syntheticViolation(SMOKE_GLOBAL_PROBE), entry: F1_ENTRY},
            ...SMOKE_ADDRESS_CHECKS.map((blockedURI) => ({finding: 'F3', violation: addressCheck(blockedURI), entry: F3_ENTRY})),
            {finding: 'an eval of other code', violation: syntheticViolation(OTHER_EVAL), entry: null},
            {finding: 'F1 with no sample', violation: syntheticViolation({...SMOKE_GLOBAL_PROBE, sample: ''}), entry: null},
        ];

        const verdicts = findings.map(({finding, violation}) => ({finding, blockedURI: violation.blockedURI, sample: violation.sample, known: isKnown(violation, baseline), knownBy: knownBy(isKnown, baseline, violation)}));
        const decided = findings.map(({finding, violation, entry}) => ({finding, blockedURI: violation.blockedURI, sample: violation.sample, known: entry !== null, knownBy: entry === null ? [] : [entry]}));
        const ids = (baseline.entries as unknown as BaselineEntry[]).map((entry) => entry.id).join(', ');
        const ratchet = 'A ratchet: an entry is removed by the lot that cures it, which updates this test — F1 when cheetah-grid stops probing with eval; A and the enforcement lot cure F3';
        expect(
            verdicts,
            `e2e/csp-baseline.json knows each finding by the entry recorded for it, and by no other: F1 by equality on script-src, eval and its sample — an eval of anything else is unknown, and fails the test that meets it — F3 by the path of the blocked address, whatever its origin and nonce (entries: ${ids}). ${ratchet}`,
        ).toEqual(decided);
    });
});

test.describe('H-52, this spec’s own reading of a page, on synthetic input: what it checks the backend with', () => {
    test('the text of every inline script, of any type; its sha256 source; every inline event-handler attribute; and the policy built from the hashes', () => {
        const html = [
            '<!doctype html>',
            '<html lang="en">',
            '<head>',
            '<!-- <script>commented()</script> <b onclick="commented()"> -->',
            '<title>a <script>titled()</script></title>',
            '<script>window.one = 1;</script>',
            '<script src="/_app/external.js"></script>',
            '<script type="module" src="/module.js" defer></script>',
            '<script type="application/json" id="data">{"a": 1}</script>',
            "<style>.x::after { content: '<script>styled()</script>'; }</style>",
            '</head>',
            '<body>',
            '<a title="a > b" onmouseover="hover()">x</a>',
            '<button class="btn" ONCLICK="location.reload()"><span id="retry-text">Retry</span></button>',
            '<div data-onclick="data()"></div>',
            '<script>\r\n  el.onclick = () => "<i onload=scripted()>";\r\n</SCRIPT >',
            '</body>',
            '</html>',
        ].join('\n');
        expect(scanHtml(html).inlineScripts, 'the text of every <script> without src, of any type — a data block too — as written; none in a comment, a <title> or a <style>').toEqual(['window.one = 1;', '{"a": 1}', '\r\n  el.onclick = () => "<i onload=scripted()>";\r\n']);
        expect(inlineEventHandlers(html), 'every on<name> attribute of a start tag, in any case, past a quoted > — not data-onclick, not one in a comment or in a script’s code').toEqual(['a onmouseover', 'button onclick']);

        expect(scriptHash("alert('Hello, world.');"), "CSP Level 2's own example (W3C): the SHA-256 of alert('Hello, world.'); is qznLcsROx4GACP2dm0UCKCzCG+HiZ1guq6ZZDob/Tng=").toBe("'sha256-qznLcsROx4GACP2dm0UCKCzCG+HiZ1guq6ZZDob/Tng='");
        expect(scriptHash('\r\none\r\ntwo\rthree\n'), 'CRLF and a lone CR are hashed as the LF the HTML parser leaves').toBe(scriptHash('\none\ntwo\nthree\n'));
        expect(scriptHash('\n  x  \n'), 'and nothing else changes: the text is not trimmed').not.toBe(scriptHash('x'));

        expect(withHashes(CSP_REPORT_ONLY_POLICY, ["'sha256-b'", "'sha256-a'", "'sha256-b'"]), "the hashes appended to script-src after 'report-sample', sorted, each once; every other directive as it was").toBe(
            CSP_REPORT_ONLY_POLICY.replace("'report-sample'", "'report-sample' 'sha256-a' 'sha256-b'"),
        );
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
            expect(cspViolations.unknown(), 'unknown — the baseline knows no inline script — and the test passes all the same: cspFailOnUnknown is false').toEqual(mine);
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
        expect(cspViolations.unknown(), 'precondition: the baseline does not know it — an inline script of a synthetic document').toEqual(mine);

        // Up to here every red is a real one: the test is still expected to pass. From here on it is expected to fail — at
        // teardown, where the collector finds the unknown violation above with cspFailOnUnknown on. Playwright then reports
        // it passed only if it did fail; «Expected to fail, but passed» means the collector let an unknown violation through.
        test.fail(true, 'H-43: the collector fails this test at teardown, on the unknown violation recorded above');
    });
});

test.describe('H-52, the real app under the policy of a managed lane: CSP_REPORT_ONLY_POLICY with the hashes of the build’s inline scripts', () => {
    test.skip(KILL_SWITCH_ON, COLLECTOR_OFF);

    test('index.html, the sign-in page, under that policy reports no violation at all, as the page and the collector both saw it — then a control proves the silence was measured', async ({page, context, request, baseURL, cspViolations}, testInfo) => {
        // Three pages fetched, the app's chunks, its session check and its first drawing, then the control: more than the 30 s default.
        test.setTimeout(2 * PAGE_TIMEOUT_MS);
        const {isKnown, loadBaseline} = await cspHelpers();
        const origin = laneOrigin(baseURL);
        const pages = await fetchBuildPages(request);
        const policy = expectedPolicy(pages);
        // One policy on every page of the build, or none at all: a managed lane sends this spec's, to the letter, on each —
        // the backend's computation, checked from one end to the other — and a self-hosted lane none, so this spec adds it.
        const lanePolicies = pages.map(({path, lanePolicy}) => ({path, lanePolicy}));
        const managed = lanePolicies.some(({lanePolicy}) => lanePolicy !== null);
        expect(
            lanePolicies,
            managed
                ? "a managed lane: on every page of the build, CSP_REPORT_ONLY_POLICY with, after 'report-sample', the hash of every inline script of the build, sorted, each once — security_headers.py's own computation must equal this spec's to the letter"
                : 'a self-hosted lane: no report-only policy on any page of the build',
        ).toEqual(pages.map(({path}) => ({path, lanePolicy: managed ? policy : null})));

        const served: ServedDocument[] = [];
        await underTheReportOnlyPolicy(context, origin, policy, served);
        await recordWhatThePageSees(page);

        const response = await page.goto(SIGN_IN_PATH, {timeout: PAGE_TIMEOUT_MS});
        const signIn = served.find((document) => document.path === SIGN_IN_PATH);
        expect(signIn?.html ?? null, `precondition: the lane served the web app’s index.html at ${SIGN_IN_PATH}, as HTML, through this spec’s route — an unbuilt frontend answers JSON there (documents served: ${described(served)})`).not.toBeNull();
        expect(signIn?.html === pageAt(pages, SIGN_IN_PATH).html, 'precondition: the browser got the very document whose inline scripts this spec hashed').toBe(true);
        const policySource = signIn?.injected ? 'added by this spec: a self-hosted lane' : 'sent by the lane itself, a managed lane: security_headers.py’s own computation';
        expect(response?.headers()[REPORT_ONLY_HEADER], `the sign-in page reached the browser under the policy, once (${policySource})`).toBe(policy);
        await expect(page.getByTestId('login-page'), 'the app booted under the policy and drew its sign-in page').toBeVisible({timeout: PAGE_TIMEOUT_MS});
        expect(await bindingType(page), `the collector listens in this document: its binding, ${BINDING}, is there`).toBe('function');

        // The page's own record first — a round trip through the page — then the collector's: what the page had dispatched
        // has arrived. A build instrumented for coverage adds istanbul's probes of the global object: left out, none of the page's own.
        const instrumented = await page.evaluate(() => '__coverage__' in window);
        const notIstanbul = (violation: Sampled) => !(instrumented && isIstanbulProbe(violation, origin));
        const seen = (await seenByPage(page)).filter(notIstanbul);
        const collected = cspViolations.list().filter(notIstanbul);
        const unknown = [...cspViolations.unknown()];
        await testInfo.attach('csp-collector-sign-in.json', {body: JSON.stringify({policy, policySource, lanePolicies, instrumented, seen, collected, unknown}, null, 1), contentType: 'application/json'});
        expect(seen, 'the sign-in page dispatched no violation: its inline scripts allowed by their hashes, and nothing else of it concerned').toEqual([]);
        expect(collected, `nor did the collector receive any:\n${listed(collected)}`).toEqual([]);
        expect(unknown, `nor does it hold an unknown one:\n${listed(unknown)}`).toEqual([]);

        // The control. A script of the lane's origin probes the global object as cheetah-grid's bundle does: under the very
        // policy of this document the browser reports its eval — script-src, eval, the sample 'report-sample' gives it — and
        // the page and the collector both record it, known by F1's entry alone. Without it, the silence above could be a
        // policy the browser never applied, or a recorder deaf in this document.
        const controlUrl = await probeTheGlobalObject(page, baseURL);
        const control = await collectedFrom(page, cspViolations, controlUrl, 1, 'the control, a probe of the global object');
        expect(control, 'the control’s eval, reported: script-src, eval, F1’s sample exactly, from the control’s script').toEqual([expect.objectContaining({directive: 'script-src', blockedURI: 'eval', sample: GLOBAL_PROBE_SAMPLE, disposition: 'report', sourceFile: controlUrl})]);
        expect(knownBy(isKnown, loadBaseline(), control[0]), `known by F1’s entry, ${F1_ENTRY}, and by no other`).toEqual([F1_ENTRY]);
        expect(cspViolations.list().filter(notIstanbul), `the collector holds the control and nothing else:\n${listed(cspViolations.list())}`).toEqual(control);
        expect((await seenByPage(page)).filter(notIstanbul).map(asSeen), 'the page saw the control too, and nothing else').toEqual(control.map(asSeen));
        expect(cspViolations.unknown(), `nothing unknown, so the collector’s teardown fails nothing:\n${listed(cspViolations.unknown())}`).toEqual([]);
    });

    test('offline.html, the offline page, under the same policy: it loads with no violation, its script allowed by its hash; no page of the build has an inline event handler; its retry button loads it again, with no violation either', async ({page, context, request, baseURL, cspViolations}) => {
        // Three pages fetched and the offline page loaded twice, on a loaded machine: more than the 30 s default.
        test.setTimeout(2 * PAGE_TIMEOUT_MS);
        const origin = laneOrigin(baseURL);
        const pages = await fetchBuildPages(request);
        const policy = expectedPolicy(pages);

        // The page as a user meets it: the server out of reach. Its own check of the server, every ten seconds, is refused,
        // so the page never loads itself again: the only reload is the one its retry button asks for.
        await page.route(
            (url) => url.origin === origin && url.pathname === OFFLINE_HEALTH_PATH,
            (route) => route.abort('connectionrefused'),
        );
        const served: ServedDocument[] = [];
        await underTheReportOnlyPolicy(context, origin, policy, served);
        await recordWhatThePageSees(page);

        const response = await page.goto(OFFLINE_PATH, {timeout: PAGE_TIMEOUT_MS});
        const offline = served.find((document) => document.path === OFFLINE_PATH);
        expect(offline?.html ?? null, `precondition: the lane served offline.html at ${OFFLINE_PATH}, as HTML, through this spec’s route (documents served: ${described(served)})`).not.toBeNull();
        expect(offline?.html === pageAt(pages, OFFLINE_PATH).html, 'precondition: the browser got the very document whose inline script this spec hashed').toBe(true);
        const policySource = offline?.injected ? 'added by this spec: a self-hosted lane' : 'sent by the lane itself, a managed lane: security_headers.py’s own computation';
        expect(response?.headers()[REPORT_ONLY_HEADER], `offline.html reached the browser under the policy, once (${policySource})`).toBe(policy);
        expect(await bindingType(page), `the collector listens in this document: its binding, ${BINDING}, is there`).toBe('function');
        // Loaded — the navigation waited for its load event — so its inline script was checked against the policy, and ran.
        expect(await seenByPage(page), 'offline.html dispatched no violation as it loaded: its inline script allowed by its hash').toEqual([]);
        expect(cspViolations.list(), `nor did the collector receive any:\n${listed(cspViolations.list())}`).toEqual([]);

        // No page of the build has an inline event handler: an on<name> attribute is script-src-attr, which no hash of
        // script-src covers, so the retry button listens through offline.html's script (D-H52-3). What makes the absence
        // mean something first: this spec's reading found each page's tags, and its inline scripts.
        const readings = pages.map(({path, html}) => {
            const {tags, inlineScripts} = scanHtml(html);
            const names = new Set(tags.map(({name}) => name));
            return {path, missingTags: ['html', 'head', 'body', 'script'].filter((name) => !names.has(name)), inlineScripts: inlineScripts.length > 0};
        });
        expect(readings, 'precondition: this spec read every page of the build — its html, head, body and script tags — and found inline scripts in each').toEqual(pages.map(({path}) => ({path, missingTags: [], inlineScripts: true})));
        const handlers = pages.flatMap(({path, html}) => inlineEventHandlers(html).map((handler) => `${path}: <${handler}=…>`));
        expect(handlers, 'no page of the build has an inline event-handler attribute: script-src-attr, which no hash covers — a page’s handlers listen through its scripts').toEqual([]);

        // The retry: a key defined on the window first, which the document loaded again no longer has.
        const retry = page.locator('button', {has: page.locator('#retry-text')});
        await expect(retry, 'offline.html’s retry button: the button around #retry-text').toHaveCount(1);
        await page.evaluate((key) => {
            Object.defineProperty(window, key, {value: true});
        }, RELOAD_MARKER);
        await retry.click();
        await page.waitForFunction((key) => !(key in window) && document.readyState === 'complete', RELOAD_MARKER, {timeout: PAGE_TIMEOUT_MS});
        const offlineDocuments = served.filter((document) => document.path === OFFLINE_PATH).map((document) => ({status: document.status, policy: document.injected ? policy : document.lanePolicy}));
        expect(offlineDocuments, 'the click loaded offline.html again: a second document, through the route, under the policy too').toEqual([
            {status: 200, policy},
            {status: 200, policy},
        ]);
        expect(new URL(page.url()).pathname, 'the page is offline.html still').toBe(OFFLINE_PATH);

        // The new document's own record — a round trip through it — then the collector's, which holds both documents'.
        expect(await seenByPage(page), 'offline.html, loaded again, dispatched no violation').toEqual([]);
        const collected = cspViolations.list();
        expect(
            collected.filter(({directive}) => directive === 'script-src-attr'),
            `no script-src-attr: the click ran no inline event handler:\n${listed(collected)}`,
        ).toEqual([]);
        expect(collected, `and no violation at all, in either document:\n${listed(collected)}`).toEqual([]);
        expect(cspViolations.unknown(), 'nothing unknown, so the collector’s teardown fails nothing').toEqual([]);
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
