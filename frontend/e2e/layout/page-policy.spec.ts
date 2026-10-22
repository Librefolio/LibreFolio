/**
 * The page policy of H-42 in a browser: the web app and the documentation keep working under the three directives the
 * backend enforces on every HTML document, beside `frame-ancestors 'self'` when frame protection is on — the managed
 * profile's default:
 *
 *     Content-Security-Policy: frame-ancestors 'self'; object-src 'none'; base-uri 'self'; form-action 'self'
 *
 * Since H-55 v2 the Content-Security-Policy is enforced in every profile, no switch: a page of the web app also carries
 * `script-src`, `worker-src` and `connect-src` (security_headers.py, `web_app_policy`), the documentation and the API's
 * own HTML only the three directives and, with frame protection, `frame-ancestors`.
 *
 * Why. E's security review, after H-39: no plugin content (`object-src 'none'`), no injected `<base>` retargeting the
 * page's relative URLs (`base-uri 'self'`), no form sending data to another origin (`form-action 'self'`) — three
 * directives that touch no script. The server sets them on documents — the app's pages, the documentation, the API's
 * own HTML — and leaves every other answer with `frame-ancestors 'self'` alone (frame protection on): there they
 * protect nothing and can break something. Chromium counts its built-in PDF viewer as a plugin, so `object-src 'none'`
 * on a PDF's own answer could stop it showing that PDF inline (from a web search, not verifiable here: headless Chromium
 * has no PDF viewer, and no E2E can see it). The server's header is pinned by the backend test
 * `services managed-headers`; this spec proves the other half: under the policy the lane itself sends, nothing in the
 * app or the documentation needs what it forbids — no `<object>`, `<embed>` or `<base>`, no form posted to another
 * origin.
 *
 * The header is the lane's own: nothing is injected, every lane sends the enforced policy (H-55 v2). What a lane may
 * differ in is frame protection, off on a self-hosted lane unless it is started with
 * `--lane-setting LIBREFOLIO_FRAME_PROTECTION=true` (or `LIBREFOLIO_PROFILE=managed`; H-43, `TEST_LANE_SETTABLE`).
 * So the spec reads the lane's header and checks its trio — `object-src 'none'`, `base-uri 'self'`,
 * `form-action 'self'` — whatever the lane, and `frame-ancestors 'self'` exactly when the response says frame
 * protection is on (`X-Frame-Options: SAMEORIGIN`), absent otherwise.
 *
 * How, before the first navigation of every test:
 *   - service workers are blocked: the spec reads the policy of the document the lane sent over the network, and the
 *     app's (`static/sw.js`) answers navigations with `respondWith(fetch(…))`, falling back to its offline page;
 *   - every document the page loads in its main frame is recorded as the browser received it: its path, its status, its
 *     `Content-Security-Policy` fields and its `X-Frame-Options`. A redirect is no document;
 *   - every `securitypolicyviolation` of every document is recorded in that document, in a window array: disposition,
 *     directive, blocked URI. Only `enforce` counts, as a report-only policy reports without blocking. A state read
 *     when the test chooses, never the console.
 *
 * Then, the positive controls declared first, or a clean run could be the policy's absence:
 *   1. on the sign-in page, which no flow uses (and each test has a browser context of its own): the document reached
 *      the browser with the trio; a `<base>` aimed at another origin, a PDF `<object>` on the lane and a form posted
 *      to another origin each raise an enforced violation — `base-uri`, `object-src`, `form-action`. The base URL stays
 *      the lane's, and no request of a control is ever made: the spec refuses them besides, so a control the policy let
 *      through could not take the page away. Nothing but the controls raises one there — the sign-in page is a page of
 *      the web app, so under its `script-src`, `worker-src` and `connect-src` too. Raised on purpose and checked
 *      here, they are not failed by the H-43 CSP collector: this test alone opts out (`cspFailOnUnknown: false`);
 *   2. the documentation: a nested page, the kind docs-offline-math picks, then Material's search finds a word of that
 *      page's own title;
 *   3. the PDF viewer, as files-pdf-offline drives it: a one-page Latin PDF uploaded by the spec and previewed from the
 *      Files page until the viewer has drawn it (`file-preview-pdf` `data-state="ready"`);
 *   4. the app: the Dashboard draws its main view, the overview `/dashboard` opens on.
 * A flow checks first that its page reached the browser with the trio and is the only document the page loaded — so
 * its green never rests on another test, and the violations read at its end are the whole flow's — and it ends with no
 * enforced violation recorded, the list printed on a red.
 *
 * Other origins are not refused, the controls' own aside: online, Mermaid and the CJK fonts may legitimately ask
 * jsDelivr, and the subject is the policy, not working offline (files-pdf-offline and docs-offline-math have that one).
 * The PDF flow's Latin PDF needs no font from there, and the viewer's engine is the app's own copy.
 *
 * Selectors: `data-testid` in the app. The documentation carries none, so there Material's own markup is the contract,
 * as in docs-offline-math: `.md-search__input` (its search field), the header's `.md-header__button[for="__search"]`
 * (which opens the field on a phone), `.md-search-result__item` (a result).
 *
 * Signed in through the API for the PDF and the Dashboard, as files-pdf-offline is: the flow's page is then the first
 * one the browser loads, and its document the one whose violations are read.
 *
 * Waiting: on the states the pages publish — the Files page's and the Dashboard's `data-busy`, the preview's
 * `data-state`, a search result on screen, a violation recorded — never on the clock.
 *
 * Cleanup: the uploaded PDF is the only datum this spec writes. Static files are shared by every user, so it has a
 * unique name and is deleted by its id in afterEach — a time slot of its own, so a test cut by its timeout still
 * deletes it. The control route is removed after each test.
 *
 * Needs: the documentation built (`./dev.py mkdocs build`; the lane's server builds a missing site). An unbuilt site
 * answers «Documentation not generated» on every `/mkdocs/` path: a red precondition here, never a skip.
 */
import {expect, test, type BrowserContext, type Page, type Response} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
/** The window array, in every document of the test, holding the violations that document saw. */
const VIOLATIONS_KEY = '__lfPagePolicyViolations';

/** The other origin of the positive controls: `.invalid` never resolves (RFC 6761), and the spec refuses it besides. */
const CONTROL_ORIGIN = 'https://example.invalid';
/** In every address a control uses: its violations, and any request of a control the policy let through, are known by it. */
const CONTROL_MARKER = 'lf-page-policy-control';
/**
 * The `<object>`'s data: a PDF's address on the lane, so that only `object-src 'none'` can block it, and the `<object>`
 * is typed `application/pdf` — plugin content, what `object-src` exists for. Never requested, so the path need not
 * exist. Not the app's icon: on the sign-in page, Chromium 149 requested the `.png` of an untyped `<object>` as an
 * image, with no `object-src` violation, when a navigation (the form's submission) started in the same task; typed as
 * plugin or document content, the `<object>` is checked in that sequence too.
 */
const CONTROL_OBJECT_PATH = `/${CONTROL_MARKER}.pdf?${CONTROL_MARKER}`;

/** A nested page of the documentation, the kind docs-offline-math picks: three folders below the site's root. */
const DOCS_PAGE = '/mkdocs/financial-theory/fundamentals/day-count/';
/**
 * A word the built search index holds: the last word of that page's own title, «Day Count Conventions» — its H1, and the
 * title of its entry in `search/search_index.json`. The index's pipeline has no stemmer, so the word is typed whole.
 */
const DOCS_QUERY = 'conventions';
/** The PDF's only text: Latin letters, nothing a CJK font is needed for. */
const PDF_TEXT = 'LibreFolio page policy PDF preview';

/** A page of the app or of the documentation, on a loaded machine. */
const PAGE_TIMEOUT_MS = 30_000;
/** Material's search: the index of the four languages fetched, then read into its search worker, before the first result. */
const SEARCH_TIMEOUT_MS = 30_000;
/** A violation: reported once the browser has blocked the control — for an `<object>`, after the next layout. */
const VIOLATION_TIMEOUT_MS = 10_000;

/** Sign-in, upload, the Files page, the preview's fetch, then the viewer's engine (4.6 MB of WebAssembly) — on a loaded machine. */
test.setTimeout(90_000);

/** The spec reads the policy of the document the lane sent over the network: the app's service worker answers navigations itself, and falls back to its offline page. */
test.use({serviceWorkers: 'block'});

/** One `securitypolicyviolation`, as a document recorded it. */
interface Violation {
    disposition: string;
    effectiveDirective: string;
    violatedDirective: string;
    blockedURI: string;
    documentURI: string;
    sourceFile: string;
    lineNumber: number;
}

/** A violation, with the frame whose document recorded it. */
interface RecordedViolation extends Violation {
    frame: string;
}

/** A document the page loaded in its main frame, as the browser received it: the header fields its policy is read from. */
interface MainDocument {
    path: string;
    status: number;
    /** Every `Content-Security-Policy` field of the answer, apart: the lane sends exactly one. */
    policies: string[];
    /** `X-Frame-Options`: `SAMEORIGIN` exactly when frame protection is on. */
    frameOptions: string | null;
}

/** What the spec saw of the policy during one test. */
interface PolicyLog {
    /** The documents the page loaded, in the order their responses arrived; filled by `settleDocuments`, never read before it. */
    mainDocuments: MainDocument[];
}

/**
 * A response's headers are read asynchronously (`headersArray()` returns a Promise), so a listener can only start the
 * read: the pending ones are kept here, in the order of the responses, beside the log and out of its JSON.
 */
const pendingDocuments = new WeakMap<PolicyLog, Array<Promise<MainDocument>>>();

/** An empty log, for one test. */
function newLog(): PolicyLog {
    const log: PolicyLog = {mainDocuments: []};
    pendingDocuments.set(log, []);
    return log;
}

/** Waits for every document read started so far and puts them, in the order of the responses, in `log.mainDocuments`. A read that failed fails here. */
async function settleDocuments(log: PolicyLog): Promise<void> {
    log.mainDocuments = await Promise.all(pendingDocuments.get(log) ?? []);
}

/** The runner's baseURL, as an origin: the lane. */
function laneOrigin(baseURL: string | undefined): string {
    if (!baseURL) throw new Error('This spec needs the runner-provided baseURL');
    return new URL(baseURL).origin;
}

/** A response's header fields, every field of its name apart: `headersArray()` keeps repeated fields from being joined. */
function fieldsOf(headers: ReadonlyArray<{name: string; value: string}>, wanted: string): string[] {
    return headers.filter(({name}) => name.toLowerCase() === wanted).map(({value}) => value);
}

/** The document `response` answers, as the browser received it. */
async function documentOf(response: Response): Promise<MainDocument> {
    const headers = await response.headersArray();
    return {path: new URL(response.url()).pathname, status: response.status(), policies: fieldsOf(headers, 'content-security-policy'), frameOptions: fieldsOf(headers, 'x-frame-options')[0] ?? null};
}

/** A policy as the browser reads it: directives split on `;`, a name in lower case, its sources the rest; a directive named twice counts once, the first. */
function parsePolicy(policy: string): Map<string, string> {
    const directives = new Map<string, string>();
    for (const part of policy.split(';')) {
        const [name, ...sources] = part.trim().split(/\s+/);
        if (name && !directives.has(name.toLowerCase())) directives.set(name.toLowerCase(), sources.join(' '));
    }
    return directives;
}

/**
 * What is wrong with the policy a document reached the browser with, read from the lane's own header (H-55 v2): exactly
 * one `Content-Security-Policy` field, its trio — `object-src 'none'`, `base-uri 'self'`, `form-action 'self'` — and
 * `frame-ancestors 'self'` exactly when the response says frame protection is on (`X-Frame-Options: SAMEORIGIN`),
 * no `frame-ancestors` otherwise. The trio is `DOCUMENT_DIRECTIVES` in backend/app/services/platform/security_headers.py,
 * which the backend test `services managed-headers` pins. Empty when nothing is wrong.
 */
function policyProblems(document: MainDocument): string[] {
    if (document.policies.length !== 1) return [`${document.policies.length} Content-Security-Policy fields, one expected: ${JSON.stringify(document.policies)}`];
    const directives = parsePolicy(document.policies[0]);
    const frameProtection = document.frameOptions?.trim().toUpperCase() === 'SAMEORIGIN';
    const expected: Array<[string, string | undefined]> = [
        ['object-src', "'none'"],
        ['base-uri', "'self'"],
        ['form-action', "'self'"],
        ['frame-ancestors', frameProtection ? "'self'" : undefined],
    ];
    return expected.filter(([name, sources]) => directives.get(name) !== sources).map(([name, sources]) => `${name}: ${sources === undefined ? 'absent (frame protection is off)' : sources} expected, got ${directives.get(name) ?? 'absent'}`);
}

/**
 * Records every `securitypolicyviolation` of every document of the browser context, in every frame, in a window array
 * of that document: a state the spec reads when it chooses, never an edge it must be armed for. Before the first
 * navigation, so that a document's first violation is recorded too.
 */
async function recordViolations(context: BrowserContext): Promise<void> {
    await context.addInitScript((key: string) => {
        if (key in window) return;
        const recorded: unknown[] = [];
        Object.defineProperty(window, key, {value: recorded});
        // On the window, capturing: a violation fired at an element, in a shadow root or not, or at the document reaches it first.
        window.addEventListener(
            'securitypolicyviolation',
            (event) => {
                recorded.push({disposition: event.disposition, effectiveDirective: event.effectiveDirective, violatedDirective: event.violatedDirective, blockedURI: event.blockedURI, documentURI: event.documentURI, sourceFile: event.sourceFile, lineNumber: event.lineNumber});
            },
            true,
        );
    }, VIOLATIONS_KEY);
}

/** Whether `response` answers a navigation of the page's main frame: a document the page loaded, or a redirect to one. */
function isMainFrameNavigation(page: Page, response: Response): boolean {
    const request = response.request();
    if (!request.isNavigationRequest()) return false;
    try {
        return request.frame() === page.mainFrame();
    } catch {
        // A request no frame made: never the page's own document.
        return false;
    }
}

/** Records, as the browser received it, every document the page loads in its main frame and the header fields its policy is read from. A redirect is no document. */
function recordMainDocuments(page: Page, log: PolicyLog): void {
    page.on('response', (response) => {
        const status = response.status();
        if (!isMainFrameNavigation(page, response) || (status >= 300 && status < 400)) return;
        const read = documentOf(response);
        // A read nobody awaited (the test ended first) must not surface as an unhandled rejection; the real one is awaited by `settleDocuments`
        read.catch(() => undefined);
        pendingDocuments.get(log)?.push(read);
    });
}

/**
 * Every violation the page's documents recorded: its main frame's, and every child frame's still on the page. The main
 * frame must hold the recorder — without it, «no violation» would be the recorder's absence, not the page's compliance.
 */
async function readViolations(page: Page): Promise<RecordedViolation[]> {
    const main = page.mainFrame();
    const perFrame = await Promise.all(
        page.frames().map(async (frame): Promise<RecordedViolation[]> => {
            const recorded: unknown = await frame.evaluate((key) => (window as unknown as Record<string, unknown>)[key] ?? null, VIOLATIONS_KEY).catch(() => null);
            if (Array.isArray(recorded)) return (recorded as Violation[]).map((violation) => ({...violation, frame: frame.url()}));
            if (frame === main) throw new Error(`no violation recorder in the page's document (${frame.url()}): the init script did not run there`);
            return [];
        }),
    );
    return perFrame.flat();
}

/** The enforced ones: a report-only policy reports without blocking. */
function enforced(violations: RecordedViolation[]): RecordedViolation[] {
    return violations.filter((violation) => violation.disposition === 'enforce');
}

/** The directive a violation names: `effectiveDirective`, or the first word of `violatedDirective` where only that is filled. */
function directiveOf(violation: Violation): string {
    return violation.effectiveDirective || violation.violatedDirective.split(' ')[0];
}

/** A violation of a positive control: its blocked address is on the control origin, or carries the control marker. */
function isControl(violation: Violation): boolean {
    return violation.blockedURI.startsWith(CONTROL_ORIGIN) || violation.blockedURI.includes(CONTROL_MARKER);
}

/** One line per violation, for a red: disposition, directive, what it blocked, and where. */
function listed(violations: RecordedViolation[]): string {
    return violations.map((violation) => `  ${violation.disposition} ${directiveOf(violation)}: blocked ${violation.blockedURI || '(no URI)'} in ${violation.documentURI}${violation.sourceFile ? ` (${violation.sourceFile}:${violation.lineNumber})` : ''}, frame ${violation.frame}`).join('\n');
}

/** The page's enforced violations by directive and blocked address: what the controls are matched against. */
async function enforcedByDirective(page: Page): Promise<Array<{directive: string; blockedURI: string}>> {
    return enforced(await readViolations(page)).map((violation) => ({directive: directiveOf(violation), blockedURI: violation.blockedURI}));
}

/**
 * Two frames of the page: its last state laid out, then what that layout checks run — an `<object>` is checked against
 * the policy once laid out, and the browser reports after. Read after this, the record holds the end state's violations.
 */
async function framesDrawn(page: Page): Promise<void> {
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
}

/**
 * The page loaded one document in its main frame, at `path`, and it reached the browser with the lane's own policy and
 * its trio (`policyProblems`). The violations it holds are then the whole flow's: a document loaded since would have
 * taken the earlier ones away with it.
 */
async function expectOneDocumentUnderPolicy(log: PolicyLog, path: string, what: string): Promise<void> {
    await settleDocuments(log);
    expect(
        log.mainDocuments.map((loaded) => loaded.path),
        `${what}: the page loaded one document, ${path} — so the violations read are the whole flow's (documents: ${JSON.stringify(log.mainDocuments)})`,
    ).toEqual([path]);
    expect(policyProblems(log.mainDocuments[0]), `${what}: the document reached the browser with the lane's enforced policy and its trio (${JSON.stringify(log.mainDocuments[0])})`).toEqual([]);
}

/** The flow raised no enforced violation of the policy, in any document still on the page; the list is printed on a red. */
async function expectNoEnforcedViolation(page: Page, log: PolicyLog, path: string, what: string): Promise<void> {
    await framesDrawn(page);
    await expectOneDocumentUnderPolicy(log, path, what);
    const raised = enforced(await readViolations(page));
    expect(raised, `${what} raised enforced violations of the page policy:\n${listed(raised)}`).toEqual([]);
}

/**
 * Refuses, and records, every request a control would make if the policy let it through: anything for the control
 * origin — the form's navigation, an address resolved against the `<base>` — and the `<object>`'s data on the lane.
 * Under the policy none is ever made. Refused, never answered, so a control let through cannot take the page away.
 */
async function refuseControlRequests(context: BrowserContext): Promise<string[]> {
    const reached: string[] = [];
    await context.route(
        (url) => url.origin === CONTROL_ORIGIN || url.href.includes(CONTROL_MARKER),
        (route) => {
            reached.push(`${route.request().method()} ${route.request().url()}`);
            return route.abort('aborted');
        },
    );
    return reached;
}

/**
 * A one-page PDF whose only text is `text`, set in Helvetica: a standard font, not embedded, with WinAnsiEncoding —
 * Latin, and nothing for the viewer to fetch. Written with an exact cross-reference table, so the engine reads the file
 * as it is rather than repairing it. `text` must be ASCII without parentheses or backslashes. files-pdf-offline's own
 * builder, copied: it is exported nowhere, and a spec cannot import another spec.
 */
function latinPdf(text: string): Buffer {
    const content = `BT /F1 24 Tf 36 140 Td (${text}) Tj ET`;
    const objects = [
        '<< /Type /Catalog /Pages 2 0 R >>',
        '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 420 300] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
        `<< /Length ${Buffer.byteLength(content, 'latin1')} >>\nstream\n${content}\nendstream`,
    ];
    let pdf = '%PDF-1.4\n';
    const offsets: number[] = [];
    for (const [index, object] of objects.entries()) {
        offsets.push(Buffer.byteLength(pdf, 'latin1'));
        pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
    }
    const xref = Buffer.byteLength(pdf, 'latin1');
    // Each entry is exactly 20 bytes: ten digits, five digits, the type, and a two-byte end of line.
    pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')}`;
    pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
    return Buffer.from(pdf, 'latin1');
}

/** Signs the browser context in through the API, no page loaded yet: the flow's page is then the first the browser loads. */
async function signInThroughApi(page: Page): Promise<void> {
    const response = await page.request.post(`${API}/auth/login`, {data: {username: TEST_USER.username, password: TEST_USER.password}});
    expect(response.ok(), `POST ${API}/auth/login as ${TEST_USER.username}: HTTP ${response.status()}`).toBe(true);
}

/** Uploads `content` as a static file this test owns, and returns its id. */
async function uploadStaticPdf(page: Page, filename: string, content: Buffer): Promise<string> {
    const response = await page.request.post(`${API}/uploads`, {multipart: {file: {name: filename, mimeType: 'application/pdf', buffer: content}}});
    expect(response.ok(), `POST ${API}/uploads ${filename}: HTTP ${response.status()}`).toBe(true);
    return ((await response.json()) as {file: {id: string}}).file.id;
}

/** Deletes a static file the test uploaded. Soft, so a red the test already holds stays the first one reported. */
async function deleteStaticFile(page: Page, fileId: string): Promise<void> {
    const response = await page.request.delete(`${API}/uploads/${fileId}`);
    expect.soft(response.ok(), `delete the static file ${fileId}: HTTP ${response.status()}`).toBe(true);
    if (response.ok()) console.log(`owned static file ${fileId} deleted`);
}

/**
 * From the Files page, already narrowed to `filename` by its own URL filter — one row, on the table's first page,
 * whatever else the lane stores — opens the preview of `fileId` and ends on the page drawn: files-pdf-offline's sequence.
 */
async function openPdfPreview(page: Page, fileId: string, filename: string): Promise<void> {
    // The page loads its lists after the app's session check and bootstrap; it publishes that load as data-busy.
    await waitForSettled(page.getByTestId('files-page'), 20_000);
    await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true');
    // The list view, set rather than assumed: this button sets the mode, it does not flip it.
    const listView = page.getByTestId('view-mode-list');
    await expect(listView).toBeVisible({timeout: 10_000});
    await listView.click();
    const row = page.locator(`[data-row-id="${fileId}"]`);
    await expect(row, `the Files list, filtered to ${filename}, shows that file`).toBeVisible({timeout: 10_000});
    await row.dblclick();

    const modal = page.getByTestId('file-preview-modal');
    await expect(modal).toBeVisible({timeout: 10_000});
    // The preview's own fetch first, then the viewer: its engine fetched and compiled, the document opened, the page drawn.
    await expect(modal.getByTestId('file-preview-shell')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
    await expect(modal.getByTestId('file-preview-pdf'), 'the viewer drew the page: the document is open and every tile in view is drawn').toHaveAttribute('data-state', 'ready', {timeout: 30_000});
}

test.describe('The page policy of H-42, as the lane itself sends it: the app and the documentation need nothing it forbids', () => {
    /** What the spec saw of the policy in the current test: a new one first thing, so a failed start never shows the previous test's. */
    let log: PolicyLog = newLog();
    /** Static files this test uploaded, deleted after it. */
    let ownedStaticFiles: string[] = [];

    test.beforeEach(async ({context, page}) => {
        ownedStaticFiles = [];
        log = newLog();
        await recordViolations(context);
        recordMainDocuments(page, log);
    });

    test.afterEach(async ({page, context}, testInfo) => {
        for (const fileId of ownedStaticFiles) await deleteStaticFile(page, fileId);
        const violations = await readViolations(page).catch((error: unknown) => `unreadable: ${error instanceof Error ? error.message : String(error)}`);
        await context.unrouteAll({behavior: 'ignoreErrors'});
        await settleDocuments(log).catch(() => undefined);
        await testInfo.attach('page-policy.json', {body: JSON.stringify({...log, violations}, null, 1), contentType: 'application/json'});
    });

    test.describe('with cspFailOnUnknown: false — the controls raise their violations on purpose, and the test checks them itself', () => {
        // This test raises enforced violations on purpose and checks them itself: the H-43 collector of
        // fixtures/playwright.ts still records them and attaches them to the report, but does not fail the test for them.
        test.use({cspFailOnUnknown: false});

        test('positive controls, on the sign-in page: the policy reaches the browser and is enforced — a <base> and a form aimed at another origin and an <object> each raise an enforced violation, and nothing else does', async ({page, context, baseURL}) => {
            const origin = laneOrigin(baseURL);
            const reached = await refuseControlRequests(context);

            const response = await page.goto('/', {timeout: PAGE_TIMEOUT_MS});
            if (!response) throw new Error('the sign-in page: goto returned no response');
            expect(policyProblems(await documentOf(response)), 'the sign-in page reached the browser with the lane’s enforced policy and its trio: without it, every green of this spec would be the policy’s absence').toEqual([]);
            await expect(page.getByTestId('login-page'), 'the app drew its sign-in page under the policy').toBeVisible({timeout: PAGE_TIMEOUT_MS});

            // One breach per directive, at absolute addresses, so that each control stands alone whatever the <base> does.
            const controls = {controlOrigin: CONTROL_ORIGIN, marker: CONTROL_MARKER, objectUrl: `${origin}${CONTROL_OBJECT_PATH}`};
            await page.evaluate(({controlOrigin, marker, objectUrl}) => {
                const base = document.createElement('base');
                base.href = `${controlOrigin}/${marker}/`;
                document.head.append(base);

                const object = document.createElement('object');
                // Plugin content, not an image: see CONTROL_OBJECT_PATH.
                object.type = 'application/pdf';
                object.data = objectUrl;
                object.width = '16';
                object.height = '16';
                document.body.append(object);

                const form = document.createElement('form');
                form.method = 'post';
                form.action = `${controlOrigin}/${marker}`;
                document.body.append(form);
                form.submit();
            }, controls);

            const directives = () => enforcedByDirective(page);
            await expect
                .poll(directives, {
                    message: 'base-uri: the <base> aimed at another origin raised an enforced violation',
                    timeout: VIOLATION_TIMEOUT_MS,
                })
                .toContainEqual(expect.objectContaining({directive: 'base-uri', blockedURI: expect.stringContaining(CONTROL_ORIGIN)}));
            await expect
                .poll(directives, {
                    message: 'object-src: the <object> on the lane raised an enforced violation',
                    timeout: VIOLATION_TIMEOUT_MS,
                })
                .toContainEqual(expect.objectContaining({directive: 'object-src', blockedURI: expect.stringContaining(CONTROL_MARKER)}));
            await expect
                .poll(directives, {
                    message: 'form-action: the form posted to another origin raised an enforced violation',
                    timeout: VIOLATION_TIMEOUT_MS,
                })
                .toContainEqual(expect.objectContaining({directive: 'form-action', blockedURI: expect.stringContaining(CONTROL_ORIGIN)}));

            // Blocked, not merely reported: the page kept the lane as its base URL, never left, and no control's request was made.
            expect(new URL(await page.evaluate(() => document.baseURI)).origin, 'the blocked <base> retargeted nothing: the page’s base URL is still on the lane').toBe(origin);
            expect(reached, 'no request of a control was made: the policy stopped each one before it left').toEqual([]);
            await expectOneDocumentUnderPolicy(log, '/', 'the sign-in page');
            // And nothing else: the sign-in page itself needs nothing the policy forbids.
            const others = enforced(await readViolations(page)).filter((violation) => !isControl(violation));
            expect(others, `the sign-in page raised enforced violations of its own under the policy:\n${listed(others)}`).toEqual([]);
        });
    });

    test('the documentation: a nested page, then Material’s search finds a word of the page’s own title — no enforced violation', async ({page, isMobile}) => {
        const response = await page.goto(DOCS_PAGE, {timeout: PAGE_TIMEOUT_MS});
        expect(response?.status(), `precondition: the lane serves ${DOCS_PAGE} (a 404 is a page that moved: point this spec at another nested page)`).toBe(200);
        await expect(page.locator('meta[name="generator"]'), `precondition: ${DOCS_PAGE} is a page of the built documentation — an unbuilt site answers «Documentation not generated»: build it, see this file's header`).toHaveAttribute('content', /\bmkdocs-/);
        await expectOneDocumentUnderPolicy(log, DOCS_PAGE, 'the documentation page');

        const query = page.locator('.md-search__input');
        // Material's own way in: the field itself, in a desktop header; on a phone, the header's search button, which opens the field and focuses it.
        await (isMobile ? page.locator('.md-header__button[for="__search"]') : query).click();
        await expect(query, 'Material opened its search: the field has the focus').toBeFocused();
        // Key by key: Material reads the query on keyup, and again once its index is ready — never on an input event alone.
        await query.pressSequentially(DOCS_QUERY);
        // Any result will do: the first is simply the one that is surely there.
        await expect(page.locator('.md-search-result__item').first(), `Material's search found «${DOCS_QUERY}» under the policy: its index fetched, read by its worker, a result drawn`).toBeVisible({timeout: SEARCH_TIMEOUT_MS});

        await expectNoEnforcedViolation(page, log, DOCS_PAGE, 'the documentation page and its search');
    });

    test('the PDF viewer: a one-page Latin PDF, previewed from the Files page until the viewer has drawn it — no enforced violation', async ({page}) => {
        await signInThroughApi(page);
        const filename = `page-policy-${uniqueSuffix()}.pdf`;
        const fileId = await uploadStaticPdf(page, filename, latinPdf(PDF_TEXT));
        ownedStaticFiles.push(fileId);
        console.log(`owned static file ${fileId} uploaded: ${filename}`);

        await navigateTo(page, `/files?tab=static&filename=${encodeURIComponent(filename)}`);
        await expectOneDocumentUnderPolicy(log, '/files', 'the Files page');
        await openPdfPreview(page, fileId, filename);

        await expectNoEnforcedViolation(page, log, '/files', 'the Files page and the PDF preview');
    });

    test('the app: the Dashboard draws its main view — no enforced violation', async ({page}) => {
        await signInThroughApi(page);
        await navigateTo(page, '/dashboard');
        await expectOneDocumentUnderPolicy(log, '/dashboard', 'the Dashboard');

        const dashboard = page.getByTestId('dashboard-page');
        await expect(dashboard, `precondition: ${TEST_USER.username} lands on the Dashboard, an account with no onboarding due`).toBeVisible({timeout: PAGE_TIMEOUT_MS});
        // Its report, its contribution and its sync loaded: the page publishes them as data-busy.
        await waitForSettled(dashboard, PAGE_TIMEOUT_MS);
        await expect(dashboard.getByTestId('dashboard-overview-tab'), 'the Dashboard drew its main view: the overview, the tab /dashboard opens on with no ?tab=').toBeVisible();

        await expectNoEnforcedViolation(page, log, '/dashboard', 'the app shell and the Dashboard');
    });
});
