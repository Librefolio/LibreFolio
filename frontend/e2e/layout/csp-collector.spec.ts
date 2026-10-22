/**
 * The Content-Security-Policy, enforced on every lane (H-55 v2), and the collector of its violations (H-43, H-52).
 *
 * Why. Since H-55 v2 the server enforces its policy in every profile, with no switch: a web-app page — `text/html`
 * exactly, not under `/mkdocs`, not under `/api` — carries ONE `Content-Security-Policy` field with, beside the three
 * directives every document gets (`object-src 'none'; base-uri 'self'; form-action 'self'`), `script-src 'self'
 * 'wasm-unsafe-eval' 'report-sample'` and the `'sha256-…'` of every inline script of the build, `worker-src 'self' blob:`
 * and `connect-src 'self'` with, where they apply, the origin of `LIBREFOLIO_PUBLIC_URL` and, on a self-hosted instance,
 * `https://api.github.com`; `frame-ancestors 'self'` is added by frame protection (`X-Frame-Options: SAMEORIGIN` goes
 * with it, on by default in the managed profile only). A document under `/mkdocs` gets the three directives and nothing
 * else of the web app's. Never `default-src`, `style-src`, `img-src`, `font-src` or `frame-src`: styles, images, fonts and
 * frames stay free. The managed profile still adds `Content-Security-Policy-Report-Only` with the wider policy, to see what
 * a stricter one would break.
 *
 * What this file holds.
 *   - The collector of `e2e/fixtures/playwright.ts` — an auto fixture that records every `securitypolicyviolation` of every
 *     document of a test, of either disposition, and fails the test at teardown on any violation `e2e/csp-baseline.json`
 *     does not know — and its pure logic, `e2e/fixtures/csp.ts`: tests 1 to 5, on synthetic input and on documents this
 *     spec serves itself, which never reach the server.
 *   - The enforced policy of the lane, read from the server's own answers: every page of the build and one SPA route carry
 *     the one enforced field of the table above, equal to what this spec computes from its own reading of the build (the
 *     hashes of the inline scripts, `scanHtml` and `scriptHash`, nothing of the backend's computation); a documentation
 *     page gets the trio and nothing more; a JSON answer gets no policy, or `frame-ancestors 'self'` alone when frame
 *     protection is on. The lane's profile (`GET /api/v1/system/instance`) and frame protection (`X-Frame-Options`) are
 *     READ, never assumed: the same tests run on a self-hosted lane and on a managed one (`front-utility cloud-smoke`), each
 *     held to its own half of the table. The directives are compared one by one, not as one string: the contract fixes
 *     their content, not their order.
 *   - The real app under it, on any lane: the sign-in page and the offline page, under the policy the SERVER sends — this
 *     spec adds none — load with no violation at all, each page's inline scripts allowed by their hashes. A control then
 *     proves the silence was measured: a script of the lane's origin probes the global object with `new Function` as
 *     cheetah-grid's bundle does, the browser BLOCKS it (an enforced `script-src` violation, an `EvalError`), the
 *     collector records it with F1's sample — known by F1's entry alone — and the app's notice stays silent about it.
 *   - The injected script: a `<script>` added to the HTML of the sign-in page, as a proxy would, is blocked — it does not run,
 *     the collector records an enforced `script-src-elem` violation — and the app says so, once, on the console and in the
 *     tab's `sessionStorage` (`cspNotice.ts`, step 4).
 *   - The baseline: F1 (cheetah-grid's probe of the global object, known by its exact sample) stays, with a reason that no
 *     longer says istanbul probes with `new Function` (it uses `globalThis`); F3, the address check of a link (a `fetch` to
 *     the address an administrator typed, which an enforced `connect-src` would block), is gone — the probe is an image
 *     now (H-55 v2 step 2).
 *
 * The baseline, `e2e/csp-baseline.json`, lists the violations already known and owned. An entry names the directive and the
 * blocked resource: by its blocked URI (`inline`, `eval`, an address), or by the path of the blocked address whatever its
 * origin and query (`blockedPath`). An entry may also name the violation's `sample`, which must then be equal: the policy has
 * `'report-sample'`, so Chromium reports the first 40 characters of a blocked script or eval. A ratchet: an entry is added only
 * by a recorded decision, with its reason and its owner, never to silence a red, and removed by the lot that cures it.
 *
 * The contract the cure is held to here:
 *   - `cspViolations`, an auto fixture, test-scoped. Unless the kill switch is set it exposes the binding
 *     `__lfCspViolation` to the browser context and registers, in every document, a capture listener of
 *     `securitypolicyviolation` on `document` that sends the binding {directive (the effective one), violatedDirective,
 *     blockedURI, sourceFile, lineNumber, columnNumber, sample, disposition, documentURI}. Its value: `list()`, every
 *     violation received, and `unknown()`, those the baseline does not know;
 *   - `cspFailOnUnknown`, an option, true by default: at teardown an unknown violation fails the test with a readable
 *     list. `test.use({cspFailOnUnknown: false})` keeps the record and fails nothing;
 *   - e2e/fixtures/csp.ts, the pure logic: `cspCollectorEnabled(env)`, `isKnown(violation, baseline)` and `loadBaseline()`.
 *     A violation is known when a baseline entry names its directive and what it blocked and, for an entry with `sample`,
 *     its sample is exactly that one. An entry names what was blocked by exactly one of `blockedURI`, the blocked URI itself,
 *     and `blockedPath`, the path of the blocked address (`new URL(blockedURI).pathname`) whatever its origin and query: a
 *     blocked URI that is no absolute URL — `inline`, `eval`, empty, a bare path — has no path, and no `blockedPath` entry
 *     knows it.
 *
 * The tests:
 *   1. the pure logic of the collector, on synthetic input; then the real baseline against the first cloud smoke's findings
 *      — F1 known by its sample, F3 now unknown, an eval of anything else unknown —, and the two corrections of H-55 v2 (F3
 *      gone, F1's reason);
 *   2. this spec's own reading of a page — the text of its inline scripts, their hashes, its inline event handlers — and of a
 *      header, on synthetic input: a known vector, a handler it must find, a policy it must accept and the ones it must
 *      refuse (a second field, a `default-src`, a missing hash, an origin that is no origin);
 *   3. a synthetic document with one inline script, served by this spec under `script-src 'self'` REPORT-ONLY: the violation
 *      is recorded once, field for field as the page itself saw it; the script still ran; it is unknown, and the test passes
 *      all the same (`cspFailOnUnknown: false`) — the collector records both dispositions;
 *   4. the same kind of unknown violation with the option at its default: the test must fail at teardown. It is marked with
 *      `test.fail()` once its body has checked all it can;
 *   5. a navigation: two synthetic documents in a row, both recorded;
 *   6. the enforced headers of the lane: every page of the build and an SPA route (the table above, one field), a
 *      documentation page (the trio), a JSON answer (no policy, or `frame-ancestors` alone), the report-only field wherever
 *      the lane sends one;
 *   7. the real app: the sign-in page under the server's policy reports no violation at all, as the page and the collector
 *      both saw it; the control of the global probe, blocked;
 *   8. the offline page, `/offline.html`, under the server's policy: it loads with no violation, its script allowed by its
 *      hash; no page of the build has an inline event-handler attribute; a click on its retry button loads it again, with no
 *      violation either;
 *   9. the injected inline script, blocked and noticed;
 *   10. the kill switch, below.
 *
 * Lanes. Nothing here depends on the lane's profile: what differs (the `connect-src` of a self-hosted instance, the
 * `frame-ancestors` of frame protection, the report-only field of a managed one) is read from the lane first and held to
 * the half of the table that applies. The synthetic documents never reach the server.
 *
 * The kill switch. `E2E_CSP_COLLECTOR=0` in the environment of a run turns the collector off for the whole run: no binding, no
 * listener, a recorder that holds nothing and fails nothing. A test cannot change its worker's environment, so the switch is
 * proven two ways: `cspCollectorEnabled` purely (test 1, in every run), and the last test of this file, which runs only in a
 * run started with the switch — the tests that use the collector skip there. The headers of the lane (test 6) are the
 * server's, not the collector's: they run in every run.
 *
 * Loading. The pure tests import e2e/fixtures/csp.ts at run time, not with the file: a missing helper is an assertion that
 * names it, never a load error.
 *
 * Selectors: `data-testid` in the app (`login-page`). offline.html is a static page with no testid, whose markup is not this
 * spec's to change: its retry button is the button around `#retry-text`, the page's own handle. The synthetic documents are
 * this spec's own and use a plain id.
 * Waiting: on states, never on the clock — the title an inline script sets, the collector's list polled until it holds what
 * the page dispatched, then one round trip through the page, so that anything sent with it has arrived too; a reload, by a
 * key of the window that the document loaded again no longer has, and the record of the documents the page received.
 * The notice's console line is the one thing read from the console: it is the product's own contract (step 4 of H-55 v2,
 * `console.error` is not compiled out of a production build), armed before the first navigation because a console message is
 * an edge; the state it leaves in `sessionStorage` is polled first, and a round trip through the page orders the two (the
 * collector's listener of the violation runs before the notice's, so the collector's report is on its way before the line is).
 * Data: nothing is written; the routes and the records die with the test's browser context.
 * Not asserted here: the `csp-violations` attachment and the readable message of the teardown failure. Both are made after
 * every hook and every other fixture of the test has finished, where no spec can read them; the report shows them.
 */
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {expect, test, type APIRequestContext, type Page} from '../fixtures/playwright';
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

/** The header fields of a response a policy is read from, every field of its name kept: «one policy per response» is a count. */
interface HeaderFields {
    /** The value of every `Content-Security-Policy` field, in the order sent. */
    csp: string[];
    /** The value of every `Content-Security-Policy-Report-Only` field. */
    reportOnly: string[];
    /** `X-Frame-Options`, when sent. */
    frameOptions: string | null;
}

/** A top-level page of the build, as the lane serves it: what this spec computes the policy from, and the policy it came with. */
interface BuildPage extends HeaderFields {
    path: string;
    file: string;
    html: string;
}

/** What the lane is, read from it: the profile of its instance and whether frame protection is on (`X-Frame-Options` is sent). */
interface LaneFacts {
    profile: 'selfhosted' | 'managed';
    frameProtection: boolean;
}

/** A policy read as the browser reads it: the first value of each directive; a name met twice is listed, its second value ignored. */
interface ParsedPolicy {
    directives: Map<string, string>;
    duplicates: string[];
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
 * The report-only policy of the web app's pages in the managed profile, before its hashes and its extra connect sources:
 * `CSP_REPORT_ONLY_POLICY` in backend/app/services/platform/security_headers.py, copied, not read. The managed profile sends it
 * BESIDE the enforced one, with, after `'report-sample'`, the hashes of the build's inline scripts and, in `connect-src`, the
 * enforced policy's extra sources (reportOnlyProblems()). It reports what a stricter policy would break; it blocks nothing.
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

/** The field of the enforced policy, and the frame option frame protection sends with its `frame-ancestors`. */
const ENFORCED_HEADER = 'content-security-policy';
const FRAME_OPTIONS_HEADER = 'x-frame-options';
/** `GET /api/v1/system/instance` (public): its `profile` is `selfhosted` on a lane by default and `managed` on one started with `--lane-setting LIBREFOLIO_PROFILE=managed`. */
const INSTANCE_PATH = '/api/v1/system/instance';
/** An SPA route: no file of the build is named so, and the server answers its fallback page (`200.html`). */
const SPA_ROUTE = '/dashboard';
/** A page of the built documentation, the kind page-policy.spec.ts and docs-offline-math.spec.ts open. An unbuilt site answers «Documentation not generated» on every path. */
const DOCS_PAGE = '/mkdocs/financial-theory/fundamentals/day-count/';
/** A JSON answer of the API: no document, whatever the profile. */
const JSON_PATH = '/api/v1/system/health';
/** What a self-hosted instance may always ask: the changelog's update check. */
const GITHUB_ORIGIN = 'https://api.github.com';
/** The directives the enforced policy never names: styles, images, fonts and frames stay free (embedding the app is a legitimate self-hosted use). */
const NEVER_ENFORCED = ['default-src', 'style-src', 'img-src', 'font-src', 'frame-src'] as const;
/** The origin of `LIBREFOLIO_PUBLIC_URL` as the server writes it: `scheme://host[:port]`, lower case, without the default port, no path. */
const CANONICAL_ORIGIN = /^https?:\/\/(?:[a-z0-9-]+(?:\.[a-z0-9-]+)*|\[[0-9a-f:]+\])(?::\d{1,5})?$/;
/** The tab's note of the sources of the scripts the policy blocked (`cspNotice.ts`): a JSON array of distinct strings. */
const NOTICE_KEY = 'librefolio-csp-blocked';
/** The one console line of the notice, `(<source>)` captured; the guide's address is the docs', its path the contract's. */
const NOTICE_LINE = /^LibreFolio blocked a script it did not send \((.+)\): a proxy, a CDN or a browser extension adds it\. Guide: \S*\/admin\/configuration\/#csp$/;
/** The first 40 characters of the injected script of test 9, which `'report-sample'` puts in the violation. */
const INJECTED_MARK = 'window.__lfInjected';

/**
 * The top-level pages of the build, as the lane serves them: the sign-in page, the SPA fallback that answers every other
 * route, and the offline page. The policy holds the hash of every inline script of each. A fourth page needs its line
 * here: the server hashes every top-level page of the build, and its header would no longer equal this spec's.
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

/** The JSON route of the address check (`GET <the address an administrator typed>/api/v1/auth/address-probe?nonce=…`), kept for curl and older clients: the probe the first cloud smoke recorded as F3 fetched it. Since H-55 v2 the browser loads an image instead. */
const ADDRESS_PROBE_PATH = '/api/v1/auth/address-probe';
/** The managed lane whose first cloud smoke found F1 and F3: the origin its pages were served at. */
const SMOKE_LANE = 'http://localhost:6181';
/**
 * The sample of the probe of the global object of cheetah-grid's bundle: under `'report-sample'`, Chromium (149, H-52's
 * probe) reports `new Function("return this")()` with the source it evaluates, whole — 39 characters, under the 40 a sample
 * keeps.
 */
const GLOBAL_PROBE_SAMPLE = '(function anonymous(\n) {\nreturn this\n})';
/** The key the control of test 7 sets on its window: true when the eval was REFUSED (an `EvalError`), false when it ran. */
const PROBE_BLOCKED_KEY = '__lfCspCollectorSpecProbeBlocked';
/** The control of test 7: a script of the lane's origin that probes the global object as cheetah-grid's bundle does, in a try/catch, and says whether the browser refused it. */
const GLOBAL_PROBE_SCRIPT = `try { new Function("return this")(); window.${PROBE_BLOCKED_KEY} = false; } catch (error) { window.${PROBE_BLOCKED_KEY} = error instanceof EvalError; }\n`;

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
/** The entry recorded for F3, the address check of a link — `connect-src`, the path of the blocked address — which H-55 v2 removed from the baseline: the probe is an image now. */
const F3_ENTRY = 'address-probe-other-origin';

/** The kill switch as this spec reads it to choose its tests: the rule of `cspCollectorEnabled`, which test 1 holds to it. */
const KILL_SWITCH_ON = process.env.E2E_CSP_COLLECTOR === '0';
const COLLECTOR_OFF = 'E2E_CSP_COLLECTOR=0: the collector is off for this whole run, and the kill-switch test at the end of this file covers it';

/** A violation: dispatched by the browser in a task after the parser's, then carried to the test by the binding. */
const VIOLATION_TIMEOUT_MS = 10_000;
/** A page of the lane: the app's chunks, its session check, then its first drawing — on a loaded machine. */
const PAGE_TIMEOUT_MS = 30_000;

/** The app's service worker answers navigations itself, and a request it answers never reaches a route of this spec (the injected script of test 9 is added by one). */
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
 * The pages of the build, fetched from the lane as it serves them — the input of this spec's own computation of the policy —
 * each with the policy fields it came with. Each must be the build's HTML: an unbuilt frontend answers JSON at `/`, and a 503
 * elsewhere.
 */
async function fetchBuildPages(request: APIRequestContext): Promise<BuildPage[]> {
    const pages: BuildPage[] = [];
    for (const {path, file} of BUILD_PAGES) {
        const response = await request.get(path);
        const html = isHtml(response.headers()['content-type'] ?? '') ? await response.text() : null;
        expect({path, status: response.status(), html: html !== null}, `precondition: the lane serves the build’s ${file} at ${path}, as HTML`).toEqual({path, status: 200, html: true});
        pages.push({path, file, html: html ?? '', ...headerFields(response.headersArray())});
    }
    return pages;
}

/** The page of the build at `path`. */
function pageAt(pages: readonly BuildPage[], path: string): BuildPage {
    const page = pages.find((candidate) => candidate.path === path);
    if (!page) throw new Error(`no page of the build at ${path}: BUILD_PAGES names it`);
    return page;
}

/** The header fields a policy is read from, every field of its name: `headersArray()` keeps repeated fields apart, `headers()` joins them. */
function headerFields(headers: ReadonlyArray<{name: string; value: string}>): HeaderFields {
    const values = (wanted: string) => headers.filter(({name}) => name.toLowerCase() === wanted).map(({value}) => value);
    return {csp: values(ENFORCED_HEADER), reportOnly: values(REPORT_ONLY_HEADER), frameOptions: values(FRAME_OPTIONS_HEADER)[0] ?? null};
}

/** A policy as the browser reads it: directives split on `;`, a name in lower case, its sources the rest; a directive named twice counts once, the first. */
function parsePolicy(policy: string): ParsedPolicy {
    const directives = new Map<string, string>();
    const duplicates: string[] = [];
    for (const part of policy.split(';')) {
        const [name, ...sources] = part.trim().split(/\s+/);
        if (!name) continue;
        const key = name.toLowerCase();
        if (directives.has(key)) duplicates.push(key);
        else directives.set(key, sources.join(' '));
    }
    return {directives, duplicates};
}

/** Whether the response says frame protection is on: `X-Frame-Options: SAMEORIGIN`. */
function frameProtectionOf(fields: HeaderFields): boolean {
    return fields.frameOptions?.trim().toUpperCase() === 'SAMEORIGIN';
}

/**
 * What is wrong with the `connect-src` of an enforced policy: it starts with `'self'`; then, at most one origin that is
 * `LIBREFOLIO_PUBLIC_URL`'s — the lane may or may not have one, this spec cannot know — written canonically; then, on a
 * self-hosted instance, `https://api.github.com`, last; on a managed one, never. Returns the problems and the sources after
 * `'self'`, GitHub included, which the report-only field must repeat: it carries the same connect sources.
 */
function connectSourcesOf(value: string | undefined, profile: LaneFacts['profile']): {problems: string[]; sources: string[]} {
    if (value === undefined) return {problems: ['connect-src: missing'], sources: []};
    const problems: string[] = [];
    const [first, ...rest] = value.split(/\s+/).filter(Boolean);
    if (first !== "'self'") problems.push(`connect-src: starts with ${first ?? 'nothing'}, not 'self'`);
    const github = rest.filter((source) => source === GITHUB_ORIGIN);
    const extra = rest.filter((source) => source !== GITHUB_ORIGIN);
    if (profile === 'selfhosted') {
        if (github.length !== 1 || rest.at(-1) !== GITHUB_ORIGIN) problems.push(`connect-src: a self-hosted instance ends it with ${GITHUB_ORIGIN}, once (${value})`);
    } else if (github.length > 0) {
        problems.push(`connect-src: a managed instance never names ${GITHUB_ORIGIN} (${value})`);
    }
    if (extra.length > 1) problems.push(`connect-src: at most one origin besides 'self' and GitHub — LIBREFOLIO_PUBLIC_URL's (${value})`);
    for (const source of extra) if (!CANONICAL_ORIGIN.test(source)) problems.push(`connect-src: ${source} is no canonical origin (scheme://host[:port], lower case, no path)`);
    return {problems, sources: rest};
}

/**
 * What is wrong with the enforced policy of a web-app page, from this spec's own reading of the build: ONE field; exactly the
 * directives of the contract, each with its content — the three of every document, `script-src` with `'self'
 * 'wasm-unsafe-eval' 'report-sample'` and the sorted hashes, `worker-src 'self' blob:`, `connect-src` (connectSourcesOf),
 * `frame-ancestors 'self'` exactly when frame protection is on — and none of NEVER_ENFORCED. The directives are compared
 * one by one: the contract fixes their content, not their order.
 */
function enforcedProblems(fields: HeaderFields, hashes: readonly string[], facts: LaneFacts): string[] {
    if (fields.csp.length !== 1) return [`${fields.csp.length} Content-Security-Policy fields, exactly one is sent`];
    const {directives, duplicates} = parsePolicy(fields.csp[0]);
    const problems = duplicates.map((name) => `${name}: named twice`);
    const expected = new Map<string, string>([
        ['object-src', "'none'"],
        ['base-uri', "'self'"],
        ['form-action', "'self'"],
        ['script-src', ["'self'", "'wasm-unsafe-eval'", "'report-sample'", ...hashes].join(' ')],
        ['worker-src', "'self' blob:"],
    ]);
    if (facts.frameProtection) expected.set('frame-ancestors', "'self'");
    for (const [name, value] of expected) if (directives.get(name) !== value) problems.push(`${name}: ${JSON.stringify(directives.get(name) ?? null)}, expected ${JSON.stringify(value)}`);
    problems.push(...connectSourcesOf(directives.get('connect-src'), facts.profile).problems);
    for (const name of directives.keys()) {
        if (!expected.has(name) && name !== 'connect-src') problems.push(`${name}: not a directive of the enforced policy${(NEVER_ENFORCED as readonly string[]).includes(name) ? ' (styles, images, fonts and frames stay free)' : ''}`);
    }
    return problems;
}

/**
 * What is wrong with the policy of a document that is no page of the web app — a documentation page: ONE field, the trio and
 * nothing else (`frame-ancestors 'self'` too when frame protection is on), and no report-only field.
 */
function trioProblems(fields: HeaderFields): string[] {
    if (fields.csp.length !== 1) return [`${fields.csp.length} Content-Security-Policy fields, exactly one is sent`];
    const {directives, duplicates} = parsePolicy(fields.csp[0]);
    const expected = new Map<string, string>([
        ['object-src', "'none'"],
        ['base-uri', "'self'"],
        ['form-action', "'self'"],
    ]);
    if (frameProtectionOf(fields)) expected.set('frame-ancestors', "'self'");
    const problems = duplicates.map((name) => `${name}: named twice`);
    for (const [name, value] of expected) if (directives.get(name) !== value) problems.push(`${name}: ${JSON.stringify(directives.get(name) ?? null)}, expected ${JSON.stringify(value)}`);
    for (const name of directives.keys()) if (!expected.has(name)) problems.push(`${name}: a document that is no page of the web app gets the trio only`);
    if (fields.reportOnly.length > 0) problems.push(`a ${REPORT_ONLY_HEADER} field: the wider policy is the web app's pages' only`);
    return problems;
}

/** What is wrong with the policy of a response that is no document: no policy at all, or — frame protection on — `frame-ancestors 'self'` alone. */
function nonDocumentProblems(fields: HeaderFields): string[] {
    const problems: string[] = [];
    if (fields.reportOnly.length > 0) problems.push(`a ${REPORT_ONLY_HEADER} field`);
    if (frameProtectionOf(fields)) {
        if (fields.csp.length !== 1 || fields.csp[0].trim() !== "frame-ancestors 'self'") problems.push(`frame protection is on: the policy is ${JSON.stringify(fields.csp)}, expected ["frame-ancestors 'self'"]`);
    } else if (fields.csp.length > 0) {
        problems.push(`frame protection is off and the answer is no document: no policy expected, got ${JSON.stringify(fields.csp)}`);
    }
    return problems;
}

/** `policy` with the `connect-src` of its sources replaced by `sources`: the report-only policy carries the enforced one's extra connect sources. */
function withConnectSources(policy: string, sources: readonly string[]): string {
    return policy
        .split('; ')
        .map((directive) => (directive.split(' ')[0] === 'connect-src' ? ['connect-src', "'self'", ...sources].join(' ') : directive))
        .join('; ');
}

/**
 * What is wrong with the report-only field of a web-app page: none, where the lane sends none (the self-hosted default);
 * else ONE, equal to CSP_REPORT_ONLY_POLICY with the build's hashes in its `script-src` and the same extra `connect-src`
 * sources as the enforced policy — the managed profile's wider policy, to the letter.
 */
function reportOnlyProblems(fields: HeaderFields, hashes: readonly string[], extraConnect: readonly string[]): string[] {
    if (fields.reportOnly.length === 0) return [];
    if (fields.reportOnly.length > 1) return [`${fields.reportOnly.length} ${REPORT_ONLY_HEADER} fields, at most one is sent`];
    const expected = withConnectSources(withHashes(CSP_REPORT_ONLY_POLICY, hashes), extraConnect);
    return fields.reportOnly[0] === expected ? [] : [`${REPORT_ONLY_HEADER}: ${fields.reportOnly[0]}\n    expected: ${expected}`];
}

/** The sorted, distinct `'sha256-…'` sources of every inline script of the pages: the hashes the enforced `script-src` carries. */
function scriptHashes(pages: readonly BuildPage[]): string[] {
    return [...new Set(pages.flatMap(({html}) => scanHtml(html).inlineScripts.map(scriptHash)))].sort();
}

/** Every protection of the lane, read from its first page: its profile and frame protection — the same on every page of the build. */
async function laneFacts(request: APIRequestContext, pages: readonly BuildPage[]): Promise<LaneFacts> {
    const response = await request.get(INSTANCE_PATH);
    const body = (await response.json()) as {profile?: unknown};
    expect({status: response.status(), profile: body.profile}, `precondition: the lane answers GET ${INSTANCE_PATH} with the profile of its instance, 'selfhosted' or 'managed'`).toEqual({status: 200, profile: expect.stringMatching(/^(selfhosted|managed)$/)});
    const frame = pages.map((page) => frameProtectionOf(page));
    expect(new Set(frame).size, `frame protection is a setting of the whole instance: X-Frame-Options is sent on every page of the build or on none (${pages.map((page, index) => `${page.path}: ${frame[index]}`).join(', ')})`).toBe(1);
    test.info().annotations.push({type: 'lane-profile', description: `${body.profile as string}, frame protection ${frame[0] ? 'on' : 'off'}`});
    return {profile: body.profile as LaneFacts['profile'], frameProtection: frame[0]};
}

/** The pages of the build and the SPA route as the lane serves them, each with the policy it came with. */
async function fetchWebAppPages(request: APIRequestContext): Promise<{pages: BuildPage[]; spa: BuildPage}> {
    const pages = await fetchBuildPages(request);
    const response = await request.get(SPA_ROUTE);
    const contentType = response.headers()['content-type'] ?? '';
    expect({path: SPA_ROUTE, status: response.status(), html: isHtml(contentType)}, `precondition: the lane answers the SPA route ${SPA_ROUTE} with the fallback page, as HTML`).toEqual({path: SPA_ROUTE, status: 200, html: true});
    return {pages, spa: {path: SPA_ROUTE, file: '200.html', html: await response.text(), ...headerFields(response.headersArray())}};
}

/** The console lines of the notice of step 4 that `page` writes, in order: armed before the first navigation, a console message being an edge. */
function noticeLinesOf(page: Page): string[] {
    const lines: string[] = [];
    page.on('console', (message) => {
        if (message.type() === 'error' && NOTICE_LINE.test(message.text())) lines.push(message.text());
    });
    return lines;
}

/** What the tab noted of the scripts the policy blocked: the JSON array of `sessionStorage[NOTICE_KEY]`, `null` while nothing is noted. */
async function notedSources(page: Page): Promise<string[] | null> {
    const raw = await page.evaluate((key) => window.sessionStorage.getItem(key), NOTICE_KEY);
    return raw === null ? null : (JSON.parse(raw) as string[]);
}

/** One document the page received at `path`: its status and the policy it carried. */
interface ReceivedDocument extends HeaderFields {
    status: number;
}

/** Records every document response of `page` at `path`, from now on: a state read when the test chooses, never an edge. */
function documentsAt(page: Page, path: string): Promise<ReceivedDocument>[] {
    const received: Promise<ReceivedDocument>[] = [];
    page.on('response', (response) => {
        if (response.request().resourceType() === 'document' && new URL(response.url()).pathname === path) {
            received.push(response.headersArray().then((headers) => ({status: response.status(), ...headerFields(headers)})));
        }
    });
    return received;
}

/**
 * Runs GLOBAL_PROBE_SCRIPT in the page's document as a script of the lane's origin, served by this spec at an address only
 * the current test serves: `script-src 'self'` lets it load, so only its eval is blocked and reported. Resolves once it has run, with
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

    test('the baseline knows the first cloud smoke’s cheetah-grid probe (F1) by its exact sample — and nothing else: not the address check of a link (F3, gone since the probe is an image), not another eval', async () => {
        const {isKnown, loadBaseline} = await cspHelpers();
        const baseline = loadBaseline();
        // F1 from files.spec.ts (the BRIM table preview), as the managed lane recorded it with the sample 'report-sample' gives
        // it, and F3's three addresses from admin-users.spec.ts AUSR-E-07, as that lane recorded them: since H-55 v2 the check is
        // an image, which no connect-src governs, and F3 is no finding any more. Then two evals no entry may know: other code,
        // and F1's own probe as the first smoke recorded it, before 'report-sample' — with no sample.
        const findings: Array<{finding: string; violation: CspViolation; entry: string | null}> = [
            {finding: 'F1', violation: syntheticViolation(SMOKE_GLOBAL_PROBE), entry: F1_ENTRY},
            ...SMOKE_ADDRESS_CHECKS.map((blockedURI) => ({finding: 'F3, the address check of a link', violation: addressCheck(blockedURI), entry: null})),
            {finding: 'an eval of other code', violation: syntheticViolation(OTHER_EVAL), entry: null},
            {finding: 'F1 with no sample', violation: syntheticViolation({...SMOKE_GLOBAL_PROBE, sample: ''}), entry: null},
        ];

        const verdicts = findings.map(({finding, violation}) => ({finding, blockedURI: violation.blockedURI, sample: violation.sample, known: isKnown(violation, baseline), knownBy: knownBy(isKnown, baseline, violation)}));
        const decided = findings.map(({finding, violation, entry}) => ({finding, blockedURI: violation.blockedURI, sample: violation.sample, known: entry !== null, knownBy: entry === null ? [] : [entry]}));
        const ids = (baseline.entries as unknown as BaselineEntry[]).map((entry) => entry.id).join(', ');
        const ratchet = 'A ratchet: an entry is removed by the lot that cures it, which updates this test — F1 when cheetah-grid stops probing with eval; F3 left with the probe by image (H-55 v2 step 2)';
        expect(verdicts, `e2e/csp-baseline.json knows F1 by equality on script-src, eval and its sample — an eval of anything else is unknown, and fails the test that meets it — and the address check of a link no more (entries: ${ids}). ${ratchet}`).toEqual(decided);
    });

    test('H-55 v2: F3, the address check of a link, has left the baseline; F1 stays, and its reason no longer says istanbul probes with new Function — istanbul uses globalThis', async () => {
        const {loadBaseline} = await cspHelpers();
        const entries = loadBaseline().entries as unknown as BaselineEntry[];

        expect(
            entries.map((entry) => entry.id),
            'the probe is an image: under an enforced connect-src no fetch to another origin is made, so no entry covers one',
        ).not.toContain(F3_ENTRY);
        const f1 = entries.find((entry) => entry.id === F1_ENTRY);
        expect(f1, `cheetah-grid’s probe of the global object stays: ${F1_ENTRY}`).toBeDefined();
        // A sentence that speaks of istanbul says what it uses, globalThis — or the reason does not speak of istanbul at all
        const sentences = (f1?.reason ?? '').split(/(?<=[.:;])\s+/);
        expect(
            sentences.filter((sentence) => /istanbul/i.test(sentence) && !/globalThis/.test(sentence)),
            'istanbul’s coverage preamble reads the global object through globalThis, not through new Function: a reason that links it to F1’s probe (“the same probe”) says what is not so',
        ).toEqual([]);
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

test.describe('H-55 v2, this spec’s own reading of a policy, on synthetic input: what it checks the server with', () => {
    const HASHES = ["'sha256-AAAA='", "'sha256-BBBB='"];
    const SELF_HOSTED: LaneFacts = {profile: 'selfhosted', frameProtection: false};
    const MANAGED: LaneFacts = {profile: 'managed', frameProtection: true};
    const SCRIPT_SRC = ["script-src 'self' 'wasm-unsafe-eval' 'report-sample'", ...HASHES].join(' ');
    /** The self-hosted lane's policy as the contract's table writes it, one directive per entry, in an order of the test's own. */
    const SELF_HOSTED_DIRECTIVES = ["object-src 'none'", "base-uri 'self'", "form-action 'self'", SCRIPT_SRC, "worker-src 'self' blob:", `connect-src 'self' ${GITHUB_ORIGIN}`];
    const MANAGED_DIRECTIVES = ["object-src 'none'", "base-uri 'self'", "form-action 'self'", SCRIPT_SRC, "worker-src 'self' blob:", "connect-src 'self'", "frame-ancestors 'self'"];
    const fields = (policies: string[], extra: Partial<HeaderFields> = {}): HeaderFields => ({csp: policies, reportOnly: [], frameOptions: null, ...extra});
    const swap = (directives: readonly string[], name: string, replacement: string | null): string => directives.flatMap((directive) => (directive.split(' ')[0] === name ? (replacement === null ? [] : [replacement]) : [directive])).join('; ');
    const problemsOf = (policy: string, facts: LaneFacts) => enforcedProblems(fields([policy]), HASHES, facts);

    test('parsePolicy: names in lower case, the first value of a directive, a repeat listed, empty parts and spaces ignored', () => {
        const {directives, duplicates} = parsePolicy("  Object-Src 'none' ;; script-src  'self'   'sha256-x=' ; object-src 'self';");

        expect([...directives.entries()], 'the first value of each directive, in the order met').toEqual([
            ['object-src', "'none'"],
            ['script-src', "'self' 'sha256-x='"],
        ]);
        expect(duplicates, 'a name met twice is listed: the browser ignores the second').toEqual(['object-src']);
    });

    test('enforcedProblems: accepts the table’s policy — self-hosted (GitHub last, a public origin before it, any order of directives) and managed (frame-ancestors, no GitHub)', () => {
        expect(problemsOf(SELF_HOSTED_DIRECTIVES.join('; '), SELF_HOSTED), 'self-hosted, as the table writes it').toEqual([]);
        expect(problemsOf([...SELF_HOSTED_DIRECTIVES].reverse().join('; '), SELF_HOSTED), 'the same directives in another order: the contract fixes their content, not their order').toEqual([]);
        expect(problemsOf(swap(SELF_HOSTED_DIRECTIVES, 'connect-src', `connect-src 'self' https://folio.example.com:8443 ${GITHUB_ORIGIN}`), SELF_HOSTED), 'self-hosted with a LIBREFOLIO_PUBLIC_URL, before GitHub').toEqual([]);
        expect(problemsOf(MANAGED_DIRECTIVES.join('; '), MANAGED), 'managed, frame protection on').toEqual([]);
        expect(problemsOf(swap(MANAGED_DIRECTIVES, 'connect-src', "connect-src 'self' https://folio.example.com"), MANAGED), 'managed with a public origin').toEqual([]);
        expect(problemsOf(swap(MANAGED_DIRECTIVES, 'frame-ancestors', null), {...MANAGED, frameProtection: false}), 'managed, frame protection switched off: no frame-ancestors').toEqual([]);
    });

    const REFUSED: Array<[string, string, LaneFacts]> = [
        ['a missing hash', swap(SELF_HOSTED_DIRECTIVES, 'script-src', `script-src 'self' 'wasm-unsafe-eval' 'report-sample' ${HASHES[0]}`), SELF_HOSTED],
        ['a hash of nobody’s script', swap(SELF_HOSTED_DIRECTIVES, 'script-src', `${SCRIPT_SRC} 'sha256-CCCC='`), SELF_HOSTED],
        ['hashes out of order', swap(SELF_HOSTED_DIRECTIVES, 'script-src', `script-src 'self' 'wasm-unsafe-eval' 'report-sample' ${HASHES[1]} ${HASHES[0]}`), SELF_HOSTED],
        ['unsafe-inline in script-src', swap(SELF_HOSTED_DIRECTIVES, 'script-src', `${SCRIPT_SRC} 'unsafe-inline'`), SELF_HOSTED],
        ['no worker-src', swap(SELF_HOSTED_DIRECTIVES, 'worker-src', null), SELF_HOSTED],
        ['no object-src', swap(SELF_HOSTED_DIRECTIVES, 'object-src', null), SELF_HOSTED],
        ['a default-src', `${SELF_HOSTED_DIRECTIVES.join('; ')}; default-src 'self'`, SELF_HOSTED],
        ['a style-src', `${SELF_HOSTED_DIRECTIVES.join('; ')}; style-src 'self' 'unsafe-inline'`, SELF_HOSTED],
        ['an img-src', `${SELF_HOSTED_DIRECTIVES.join('; ')}; img-src 'self' data: https:`, SELF_HOSTED],
        ['a font-src', `${SELF_HOSTED_DIRECTIVES.join('; ')}; font-src 'self'`, SELF_HOSTED],
        ['a frame-src', `${SELF_HOSTED_DIRECTIVES.join('; ')}; frame-src 'self' blob:`, SELF_HOSTED],
        ['no frame-ancestors with frame protection on', swap(MANAGED_DIRECTIVES, 'frame-ancestors', null), MANAGED],
        ['a frame-ancestors with frame protection off', `${SELF_HOSTED_DIRECTIVES.join('; ')}; frame-ancestors 'self'`, SELF_HOSTED],
        ['GitHub on a managed instance', swap(MANAGED_DIRECTIVES, 'connect-src', `connect-src 'self' ${GITHUB_ORIGIN}`), MANAGED],
        ['no GitHub on a self-hosted instance', swap(SELF_HOSTED_DIRECTIVES, 'connect-src', "connect-src 'self'"), SELF_HOSTED],
        ['a connect-src that does not start with self', swap(SELF_HOSTED_DIRECTIVES, 'connect-src', `connect-src https://folio.example.com ${GITHUB_ORIGIN}`), SELF_HOSTED],
        ['an origin in capitals', swap(SELF_HOSTED_DIRECTIVES, 'connect-src', `connect-src 'self' https://Folio.Example.com ${GITHUB_ORIGIN}`), SELF_HOSTED],
        ['an origin with a path', swap(SELF_HOSTED_DIRECTIVES, 'connect-src', `connect-src 'self' https://folio.example.com/app ${GITHUB_ORIGIN}`), SELF_HOSTED],
        ['an origin with a trailing slash', swap(SELF_HOSTED_DIRECTIVES, 'connect-src', `connect-src 'self' https://folio.example.com/ ${GITHUB_ORIGIN}`), SELF_HOSTED],
        ['two public origins', swap(SELF_HOSTED_DIRECTIVES, 'connect-src', `connect-src 'self' https://a.example https://b.example ${GITHUB_ORIGIN}`), SELF_HOSTED],
        ['a wildcard', swap(SELF_HOSTED_DIRECTIVES, 'connect-src', `connect-src 'self' * ${GITHUB_ORIGIN}`), SELF_HOSTED],
        ['a directive named twice', `${SELF_HOSTED_DIRECTIVES.join('; ')}; object-src 'self'`, SELF_HOSTED],
    ];

    test('enforcedProblems: refuses every policy that departs from the table — a hash missing, extra or out of order, unsafe-inline, a directive missing or one the policy never names, frame-ancestors out of step with frame protection, GitHub on the wrong profile, a connect-src that is not self then canonical origins', () => {
        expect(REFUSED.length, 'premise: the table of departures is not empty').toBeGreaterThan(0);
        const accepted = REFUSED.filter(([, policy, facts]) => problemsOf(policy, facts).length === 0).map(([label]) => label);
        expect(accepted, 'a departure the reading accepts is a check with no teeth').toEqual([]);
    });

    test('enforcedProblems: refuses two Content-Security-Policy fields — the browser would enforce both — and none', () => {
        expect(enforcedProblems(fields([SELF_HOSTED_DIRECTIVES.join('; '), "frame-ancestors 'self'"]), HASHES, SELF_HOSTED).length, 'two fields').toBeGreaterThan(0);
        expect(enforcedProblems(fields([]), HASHES, SELF_HOSTED).length, 'no field').toBeGreaterThan(0);
    });

    test('trioProblems and nonDocumentProblems: a documentation page gets the trio and nothing of the web app’s; a JSON answer none, or frame-ancestors alone', () => {
        const trio = ["object-src 'none'", "base-uri 'self'", "form-action 'self'"];
        expect(trioProblems(fields([trio.join('; ')])), 'the trio').toEqual([]);
        expect(trioProblems(fields([[...trio, "frame-ancestors 'self'"].join('; ')], {frameOptions: 'SAMEORIGIN'})), 'the trio and frame-ancestors, with frame protection').toEqual([]);
        for (const [label, policy, extra] of [
            ['a script-src', `${trio.join('; ')}; ${SCRIPT_SRC}`, {}],
            ['a connect-src', `${trio.join('; ')}; connect-src 'self'`, {}],
            ['no form-action', trio.slice(0, 2).join('; '), {}],
            ['frame-ancestors with frame protection off', `${trio.join('; ')}; frame-ancestors 'self'`, {}],
            ['no frame-ancestors with frame protection on', trio.join('; '), {frameOptions: 'SAMEORIGIN'}],
            ['a report-only field', trio.join('; '), {reportOnly: ["default-src 'self'"]}],
        ] as Array<[string, string, Partial<HeaderFields>]>) {
            expect(trioProblems(fields([policy], extra)).length, label).toBeGreaterThan(0);
        }

        expect(nonDocumentProblems(fields([])), 'a JSON answer with frame protection off: no policy').toEqual([]);
        expect(nonDocumentProblems(fields(["frame-ancestors 'self'"], {frameOptions: 'SAMEORIGIN'})), 'with it on: frame-ancestors alone').toEqual([]);
        expect(nonDocumentProblems(fields(["object-src 'none'"])).length, 'a policy where there should be none').toBeGreaterThan(0);
        expect(nonDocumentProblems(fields([`${trio.join('; ')}; frame-ancestors 'self'`], {frameOptions: 'SAMEORIGIN'})).length, 'more than frame-ancestors on a JSON answer').toBeGreaterThan(0);
    });

    test('reportOnlyProblems: none where the lane sends none; else CSP_REPORT_ONLY_POLICY with the hashes and the enforced policy’s extra connect sources, once', () => {
        const wider = withHashes(CSP_REPORT_ONLY_POLICY, HASHES);
        expect(reportOnlyProblems(fields([]), HASHES, []), 'a self-hosted default: none sent').toEqual([]);
        expect(reportOnlyProblems(fields([], {reportOnly: [wider]}), HASHES, []), 'the wider policy with the hashes').toEqual([]);
        expect(reportOnlyProblems(fields([], {reportOnly: [withConnectSources(wider, ['https://folio.example.com'])]}), HASHES, ['https://folio.example.com']), 'with the public origin, as the enforced one').toEqual([]);
        expect(reportOnlyProblems(fields([], {reportOnly: [wider]}), HASHES, ['https://folio.example.com']).length, 'the public origin missing from it').toBeGreaterThan(0);
        expect(reportOnlyProblems(fields([], {reportOnly: [CSP_REPORT_ONLY_POLICY]}), HASHES, []).length, 'no hashes').toBeGreaterThan(0);
        expect(reportOnlyProblems(fields([], {reportOnly: [wider, wider]}), HASHES, []).length, 'two fields').toBeGreaterThan(0);
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

test.describe('H-55 v2, the enforced policy of the lane, as the server sends it: every profile enforces', () => {
    test('every page of the build and an SPA route carry ONE enforced policy — the contract’s table, the hashes from this spec’s own reading of the build — and the report-only field, where the lane sends one, the wider policy', async ({request}) => {
        const {pages, spa} = await fetchWebAppPages(request);
        const all = [...pages, spa];
        const facts = await laneFacts(request, all);
        const hashes = scriptHashes(pages);
        expect(hashes.length, 'precondition: the build has inline scripts, each with its hash').toBeGreaterThan(0);
        expect(spa.html === pageAt(pages, '/200.html').html, `precondition: ${SPA_ROUTE} is answered with the fallback page, 200.html, whose inline scripts the hashes cover`).toBe(true);

        for (const page of all) {
            expect(enforcedProblems(page, hashes, facts), `${page.path}: the enforced policy of a web-app page on a ${facts.profile} lane, frame protection ${facts.frameProtection ? 'on' : 'off'}. Sent: ${JSON.stringify(page.csp)}`).toEqual([]);
        }
        const connect = new Set(all.map((page) => parsePolicy(page.csp[0] ?? '').directives.get('connect-src')));
        expect([...connect], 'every page of the instance has the same connect-src: the settings are read once, when the server starts').toHaveLength(1);
        const {sources} = connectSourcesOf([...connect][0], facts.profile);
        for (const page of all) {
            expect(reportOnlyProblems(page, hashes, sources), `${page.path}: the report-only field, where there is one`).toEqual([]);
        }
    });

    test('a documentation page, under /mkdocs, gets the three directives that touch no script, and nothing of the web app’s', async ({request}) => {
        const {pages} = await fetchWebAppPages(request);
        const facts = await laneFacts(request, pages);

        const response = await request.get(DOCS_PAGE);
        const body = await response.text();
        expect({status: response.status(), built: /content="mkdocs-/.test(body)}, `precondition: ${DOCS_PAGE} is a page of the built documentation — an unbuilt site answers «Documentation not generated»: build it (./dev.py mkdocs build)`).toEqual({status: 200, built: true});

        const fields = headerFields(response.headersArray());
        expect(frameProtectionOf(fields), 'frame protection is the instance’s: the same on a documentation page').toBe(facts.frameProtection);
        expect(trioProblems(fields), `the policy of ${DOCS_PAGE}: object-src, base-uri and form-action — and frame-ancestors with frame protection — and no script-src, connect-src or worker-src. Sent: ${JSON.stringify(fields.csp)}`).toEqual([]);
    });

    test('a JSON answer of the API is no document: no policy, or — frame protection on — frame-ancestors alone', async ({request}) => {
        const {pages} = await fetchWebAppPages(request);
        const facts = await laneFacts(request, pages);

        const response = await request.get(JSON_PATH);
        expect({status: response.status(), json: (response.headers()['content-type'] ?? '').startsWith('application/json')}, `precondition: GET ${JSON_PATH} answers JSON`).toEqual({status: 200, json: true});

        const fields = headerFields(response.headersArray());
        expect(frameProtectionOf(fields), 'frame protection is the instance’s: the same on an API answer').toBe(facts.frameProtection);
        expect(nonDocumentProblems(fields), `the policy of GET ${JSON_PATH}. Sent: ${JSON.stringify(fields.csp)}`).toEqual([]);
    });
});

test.describe('H-55 v2, the real app under the policy the server sends: nothing of its own is blocked', () => {
    test.skip(KILL_SWITCH_ON, COLLECTOR_OFF);

    test('index.html, the sign-in page, loads with no violation at all, as the page and the collector both saw it — then a control proves the silence was measured: the global probe is BLOCKED, recorded as F1, and not noticed', async ({page, request, baseURL, cspViolations}, testInfo) => {
        // Three pages fetched, the app's chunks, its session check and its first drawing, then the control: more than the 30 s default.
        test.setTimeout(2 * PAGE_TIMEOUT_MS);
        const {isKnown, loadBaseline} = await cspHelpers();
        const pages = await fetchBuildPages(request);
        const facts = await laneFacts(request, pages);
        const hashes = scriptHashes(pages);
        const noticeLines = noticeLinesOf(page);
        await recordWhatThePageSees(page);

        const response = await page.goto(SIGN_IN_PATH, {timeout: PAGE_TIMEOUT_MS});
        expect(response, 'the sign-in page answered').not.toBeNull();
        const reached = headerFields(await (response as NonNullable<typeof response>).headersArray());
        expect(enforcedProblems(reached, hashes, facts), `the sign-in page reached the browser under the enforced policy, once, as the server sends it — this spec adds none. Sent: ${JSON.stringify(reached.csp)}`).toEqual([]);
        expect((await (response as NonNullable<typeof response>).text()) === pageAt(pages, SIGN_IN_PATH).html, 'precondition: the browser got the very document whose inline scripts this spec hashed').toBe(true);
        await expect(page.getByTestId('login-page'), 'the app booted under the policy and drew its sign-in page').toBeVisible({timeout: PAGE_TIMEOUT_MS});
        expect(await bindingType(page), `the collector listens in this document: its binding, ${BINDING}, is there`).toBe('function');

        // The page's own record first — a round trip through the page — then the collector's: what the page had dispatched has arrived.
        const seen = await seenByPage(page);
        const collected = cspViolations.list();
        const unknown = [...cspViolations.unknown()];
        await testInfo.attach('csp-collector-sign-in.json', {body: JSON.stringify({facts, hashes, reached, seen, collected, unknown, noticeLines}, null, 1), contentType: 'application/json'});
        expect(seen, 'the sign-in page dispatched no violation, of either disposition: its inline scripts allowed by their hashes, its scripts and workers and requests by self').toEqual([]);
        expect(collected, `nor did the collector receive any:\n${listed(collected)}`).toEqual([]);
        expect(unknown, `nor does it hold an unknown one:\n${listed(unknown)}`).toEqual([]);
        expect(noticeLines, 'the app’s notice has nothing to say: nothing was blocked').toEqual([]);
        expect(await notedSources(page), 'and the tab noted nothing').toBeNull();

        // The control. A script of the lane's origin probes the global object as cheetah-grid's bundle does, in a try/catch: the
        // browser BLOCKS its eval — script-src, eval, the sample 'report-sample' gives it, enforced — and the page and the
        // collector both record it, known by F1's entry alone. Without it, the silence above could be a policy the browser never
        // applied, or a recorder deaf in this document.
        const controlUrl = await probeTheGlobalObject(page, baseURL);
        const control = await collectedFrom(page, cspViolations, controlUrl, 1, 'the control, a probe of the global object');
        expect(control, 'the control’s eval, enforced: script-src, eval, F1’s sample exactly, from the control’s script').toEqual([expect.objectContaining({directive: 'script-src', blockedURI: 'eval', sample: GLOBAL_PROBE_SAMPLE, disposition: 'enforce', sourceFile: controlUrl})]);
        expect(await page.evaluate((key) => (window as unknown as Record<string, unknown>)[key], PROBE_BLOCKED_KEY), 'the browser refused the eval — an EvalError — and did not merely report it: the policy is ENFORCED').toBe(true);
        expect(knownBy(isKnown, loadBaseline(), control[0]), `known by F1’s entry, ${F1_ENTRY}, and by no other`).toEqual([F1_ENTRY]);
        expect(cspViolations.list(), `the collector holds the control and nothing else:\n${listed(cspViolations.list())}`).toEqual(control);
        expect((await seenByPage(page)).map(asSeen), 'the page saw the control too, and nothing else').toEqual(control.map(asSeen));
        // The round trip of collectedFrom() orders what came before it: the collector's listener of the violation runs first, so
        // its report precedes any console line the notice would write for it. None: F1 is a known violation, never reported.
        expect(noticeLines, 'the known probe of cheetah-grid is never noticed').toEqual([]);
        expect(await notedSources(page), 'nor noted').toBeNull();
        expect(cspViolations.unknown(), `nothing unknown, so the collector’s teardown fails nothing:\n${listed(cspViolations.unknown())}`).toEqual([]);
    });

    test('offline.html, the offline page, under the server’s policy: it loads with no violation, its script allowed by its hash; no page of the build has an inline event handler; its retry button loads it again, with no violation either', async ({page, request, cspViolations}) => {
        // Three pages fetched and the offline page loaded twice, on a loaded machine: more than the 30 s default.
        test.setTimeout(2 * PAGE_TIMEOUT_MS);
        const pages = await fetchBuildPages(request);
        const facts = await laneFacts(request, pages);
        const hashes = scriptHashes(pages);

        // The page as a user meets it: the server out of reach. Its own check of the server, every ten seconds, is refused,
        // so the page never loads itself again: the only reload is the one its retry button asks for.
        await page.route(
            (url) => url.pathname === OFFLINE_HEALTH_PATH,
            (route) => route.abort('connectionrefused'),
        );
        const received = documentsAt(page, OFFLINE_PATH);
        await recordWhatThePageSees(page);

        const response = await page.goto(OFFLINE_PATH, {timeout: PAGE_TIMEOUT_MS});
        expect(response, 'offline.html answered').not.toBeNull();
        const reached = headerFields(await (response as NonNullable<typeof response>).headersArray());
        expect(enforcedProblems(reached, hashes, facts), `offline.html reached the browser under the enforced policy, once, as the server sends it. Sent: ${JSON.stringify(reached.csp)}`).toEqual([]);
        expect((await (response as NonNullable<typeof response>).text()) === pageAt(pages, OFFLINE_PATH).html, 'precondition: the browser got the very document whose inline script this spec hashed').toBe(true);
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
        const documents = await Promise.all(received);
        expect(
            documents.map((document) => ({status: document.status, problems: enforcedProblems(document, hashes, facts)})),
            'the click loaded offline.html again: a second document, under the enforced policy too, once',
        ).toEqual([
            {status: 200, problems: []},
            {status: 200, problems: []},
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

test.describe('H-55 v2, a script the instance did not send: blocked, recorded, and noticed', () => {
    test.skip(KILL_SWITCH_ON, COLLECTOR_OFF);
    // The violation this block raises on purpose is unknown to the baseline, and is the subject: no failure at teardown
    test.use({cspFailOnUnknown: false});

    test('an inline script added to the sign-in page, as a proxy would, does not run; the collector records an enforced script-src-elem violation; the app says so once, on the console and in the tab’s sessionStorage — and still boots', async ({page, request, baseURL, cspViolations}) => {
        test.setTimeout(2 * PAGE_TIMEOUT_MS);
        const origin = laneOrigin(baseURL);
        const token = `csp-injected ${uniqueSuffix()}`;
        const injected = `<script>${INJECTED_MARK} = true; document.title = ${JSON.stringify(token)};</script>`;
        const pages = await fetchBuildPages(request);
        const facts = await laneFacts(request, pages);
        const hashes = scriptHashes(pages);
        const noticeLines = noticeLinesOf(page);
        await recordWhatThePageSees(page);

        // The document of the sign-in page, fetched by this spec with the server's own headers and the script added to its head:
        // the policy the browser meets is the server's, and the script is none of the build's — its hash is in no policy.
        let rewritten = 0;
        await page.route(
            (url) => url.origin === origin && url.pathname === SIGN_IN_PATH,
            async (route) => {
                if (route.request().resourceType() !== 'document') {
                    await route.fallback();
                    return;
                }
                const response = await route.fetch();
                const html = await response.text();
                const headers = {...response.headers()};
                // The body changes: its length and its encoding are no longer the original's
                delete headers['content-length'];
                delete headers['content-encoding'];
                if (html.includes('</head>')) rewritten += 1;
                await route.fulfill({status: response.status(), headers, body: html.replace('</head>', `${injected}</head>`)});
            },
        );

        const response = await page.goto(SIGN_IN_PATH, {timeout: PAGE_TIMEOUT_MS});
        expect(response, 'the sign-in page answered').not.toBeNull();
        const reached = headerFields(await (response as NonNullable<typeof response>).headersArray());
        expect(rewritten, 'precondition: this spec’s route added the script to the sign-in page’s head, once').toBe(1);
        expect(await (response as NonNullable<typeof response>).text(), 'precondition: the document the browser got carries the injected script').toContain(injected);
        expect(enforcedProblems(reached, hashes, facts), `precondition: the document carries the server’s enforced policy, which has no hash for the injected script. Sent: ${JSON.stringify(reached.csp)}`).toEqual([]);
        expect(
            scriptHashes([{...pages[0], html: injected}]).every((hash) => !reached.csp[0].includes(hash)),
            'precondition: the injected script’s hash is in no source of the policy',
        ).toBe(true);

        await expect(page.getByTestId('login-page'), 'the app booted all the same: a script it did not send is refused, the page goes on').toBeVisible({timeout: PAGE_TIMEOUT_MS});
        expect(await page.evaluate((mark) => ({ran: mark in window, title: document.title}), INJECTED_MARK), 'the injected script did not run: the policy blocked it').toEqual({ran: false, title: expect.not.stringContaining(token)});
        // The early buffer of app.html is drained by cspNotice.ts at startup and the global set to null (R3): so app.html's early
        // listener, which pushes only into an array, stops collecting. Exactly null, not undefined: present, and drained.
        expect(await page.evaluate(() => (window as unknown as {__lfCspViolations?: unknown}).__lfCspViolations), 'app.html’s early buffer was drained by cspNotice.ts at startup (R3): null once the bundle runs').toBeNull();

        // The collector: one enforced script-src-elem violation of the document, an inline script, whose sample is its first characters
        const url = new URL(SIGN_IN_PATH, origin).href;
        const mine = await collectedFor(page, cspViolations, url, 1, 'the sign-in page with a script injected');
        expect(mine, 'one violation: an inline script blocked — script-src-elem, inline, enforced — its sample the first characters of the script').toEqual([
            expect.objectContaining({directive: 'script-src-elem', violatedDirective: expect.stringContaining('script-src'), blockedURI: 'inline', disposition: 'enforce', documentURI: url, sample: expect.stringContaining(INJECTED_MARK)}),
        ]);
        expect(cspViolations.list(), 'and nothing else: the app’s own scripts are all allowed').toEqual(mine);
        expect(mine.map(asSeen), 'the collector holds what the page dispatched, field for field').toEqual((await seenByPage(page)).map(asSeen));
        expect(cspViolations.unknown(), 'unknown to the baseline — and the test passes all the same: cspFailOnUnknown is false').toEqual(mine);

        // The notice: the state first — the tab's note —, then the one console line, then one more round trip to see it stay one
        await expect.poll(() => notedSources(page), {message: 'the tab noted the blocked script’s source: inline, once', timeout: VIOLATION_TIMEOUT_MS}).toEqual(['inline']);
        await expect.poll(() => noticeLines.length, {message: 'the app wrote its line on the console', timeout: VIOLATION_TIMEOUT_MS}).toBe(1);
        await page.evaluate(() => undefined);
        expect(noticeLines, 'one console.error per page load: LibreFolio blocked a script it did not send (inline), the guide at its end').toHaveLength(1);
        expect(NOTICE_LINE.exec(noticeLines[0])?.[1], 'the line names the source: inline').toBe('inline');
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
