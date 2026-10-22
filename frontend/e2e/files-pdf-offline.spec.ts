/**
 * The PDF preview without internet — gap 7 of the 1.2 end-to-end gaps (plan 46, §12.4; devWiki
 * `decisions/e2e-gaps-of-1-2-before-release`), the 1.2 promise «anteprima PDF solo visore, senza CDN».
 *
 * The preview draws PDFs with EmbedPDF, which runs PDFium compiled to WebAssembly. Out of the box that viewer fetches its
 * engine, the fonts a PDF does not embed, a stamp library and its interface font from jsDelivr and Google Fonts: offline
 * it never drew a page. Since release 2's batch 7 the app serves the engine and the fallback fonts itself
 * (`src/lib/utils/files/pdfViewerAssets.ts`; devWiki `decisions/pdf-preview-viewer-only-local-assets`), and the CDN is
 * asked only when the app's own engine does not answer. `pdfViewerAssets.test.ts` proves that configuration; this spec
 * proves the promise in a browser: with no internet, a user previews a PDF.
 *
 * For the whole test every origin but the lane's is refused, as a machine without internet refuses it, and every request
 * of the browser context is recorded — the page's, its workers' (the engine runs in a module worker made from a blob)
 * and the service worker's. Both start before the first navigation. Then:
 *
 *   1. a one-page PDF whose only text is Latin, set in Helvetica — one of the 14 standard fonts, not embedded, which
 *      PDFium draws with a face of its own — is uploaded as a static file and previewed from the Files list;
 *   2. the preview draws it: `file-preview-pdf` reaches `data-state="ready"`, which `pdfPreviewState.ts` publishes once
 *      the document is open and every tile in view is drawn, at least one. The document has a single page, so the page
 *      drawn is its first: the state says the page is on screen, not merely that the modal opened;
 *   3. the browser asked nothing of another origin, from the first navigation to the end of the test. The list is
 *      printed on a red, also when the page was never drawn: a viewer waiting on an unreachable CDN is this spec's
 *      subject too;
 *   4. positive controls, or that empty list could be the log's silence: the engine's worker fetched the app's own
 *      `pdfium.<hash>.wasm` with a GET (the page itself only probes it, with a HEAD) and the app answered 200, so the
 *      log does see the worker; every viewer font asked for was a 200 from the app (a Latin text needs none: PDFium
 *      has its own faces for the standard fonts); and from the page jsDelivr is out of reach, its refusal recorded.
 *      Under the Content-Security-Policy the backend enforces on every page of the app (H-55 v2, `connect-src`
 *      without jsDelivr: `security_headers.py`; the CJK fonts come from the instance, H-55 wave 4), the browser stops
 *      that fetch itself, before
 *      the network layer and so before this spec's route sees it. The control proves the refusal either way — the
 *      browser's (an enforced `connect-src` violation for exactly that address, recorded by the H-43 collector) or
 *      the route's (the request in `refused`) — and if the policy ever allows the CDN, the route's. The violation is
 *      raised on purpose: this test alone opts out of the collector's failure on an unknown violation
 *      (`cspFailOnUnknown: false`), and checks itself that the probe is the only one the baseline does not know.
 *
 * Chinese, Japanese and Korean are out of scope here (this PDF is Latin), but not exempt: since H-55 wave 4 their fallback
 * fonts come from the app's own `/api/v1/files/pdf-fonts/` route, so no preview asks jsDelivr, whatever it draws.
 *
 * Signed in through the API, not through the login page: a sign-in lands on the Dashboard, which can draw broker icons,
 * and a broker icon falls back on the broker's own site («portal_url → origin + /favicon.ico», `brokerHelpers.ts`) —
 * the seeded brokers have a portal URL and no icon. Those would be requests to other origins outside this spec's
 * subject. Signed in this way, the Files page is the first page the browser loads, and the whole log is the subject's.
 *
 * Precondition: TEST_USER is an ordinary member. An administrator's browser asks GitHub for a newer release after it
 * loads the app (F14, `updateCheck.ts`): another origin by design, outside this subject. Read on the sign-in's answer,
 * before any page is loaded.
 *
 * Waiting: on the states the app publishes — the Files page's `data-busy`, the row of this file, the preview shell's
 * `data-busy`, the stage's `data-state` — never on the clock.
 *
 * Cleanup: static files are shared by every user, so the file has a unique name and is deleted by its id after the
 * test, in afterEach — a time slot of its own, so a test cut by its timeout still deletes it.
 */
import {expect, test, type BrowserContext, type Page, type Request} from './fixtures/playwright';
import {navigateTo} from './fixtures/auth-helpers';
import type {CspViolation} from './fixtures/csp';
import {TEST_USER} from './fixtures/test-users';
import {waitForSettled} from './fixtures/app-events';
import {uniqueSuffix} from './fixtures/unique';

const API = '/api/v1';
/** The app's own engine as the build names it: `/_app/immutable/assets/pdfium.<hash>.wasm` (`LOCAL_PDF_ENGINE`). */
const LOCAL_ENGINE_PATH = /^\/_app\/immutable\/assets\/pdfium\.[^/]+\.wasm$/;
/** The viewer's fallback fonts the app ships — the Noto files of `LOCAL_FONT_FILES` — as build assets. */
const LOCAL_VIEWER_FONT_PATH = /^\/_app\/immutable\/assets\/Noto[^/]+\.ttf$/;
/** Positive control: an address on jsDelivr, the viewer's fallback host, that nothing in the app asks for. */
const OFFLINE_PROBE_URL = 'https://cdn.jsdelivr.net/npm/librefolio-e2e-offline-probe/index.js';
/** How long the browser's or the route's refusal of the probe may take to be recorded: a violation is reported to the collector by a binding call. */
const PROBE_REFUSAL_TIMEOUT_MS = 10_000;
/** The PDF's only text: Latin letters, nothing a CJK font is needed for. */
const PDF_TEXT = 'LibreFolio offline PDF preview';

/** Sign-in, upload, the Files page, the preview's fetch, then the viewer's engine (4.6 MB of WebAssembly) — on a loaded machine. */
test.setTimeout(90_000);

/** One request of the browser context, as it was made. */
interface Recorded {
    method: string;
    url: URL;
    request: Request;
}

/** What the browser asked for while it had no internet. */
interface OfflineNetwork {
    /** Every request of the browser context, in order: the page's, its workers', the service worker's. */
    requests: Recorded[];
    /** `<method> <url>` of every request the route refused: each one was to another origin. */
    refused: string[];
}

/** The runner's baseURL, as an origin: the only one this spec lets the browser reach. */
function laneOrigin(baseURL: string | undefined): string {
    if (!baseURL) throw new Error('This spec needs the runner-provided baseURL');
    return new URL(baseURL).origin;
}

/** Served by another origin than the lane's. `data:` and `about:` ask no one; a `blob:` URL carries the origin that made it. */
function isOtherOrigin(url: URL, origin: string): boolean {
    return url.protocol !== 'data:' && url.protocol !== 'about:' && url.origin !== origin;
}

/**
 * Cuts the browser context off from every origin but the lane's, as a machine without internet would be — refused, not
 * answered: nothing under test is faked — and records every request it makes. Before the first navigation, so nothing
 * goes unseen.
 */
async function goOffline(context: BrowserContext, origin: string): Promise<OfflineNetwork> {
    const network: OfflineNetwork = {requests: [], refused: []};
    context.on('request', (request) => {
        network.requests.push({method: request.method(), url: new URL(request.url()), request});
    });
    await context.route(
        (url) => isOtherOrigin(url, origin),
        (route) => {
            network.refused.push(`${route.request().method()} ${route.request().url()}`);
            return route.abort('internetdisconnected');
        },
    );
    return network;
}

/** `<method> <url>` of every request the browser made to another origin, refused or not. */
function askedOfOtherOrigins(network: OfflineNetwork, origin: string): string[] {
    return network.requests.filter(({url}) => isOtherOrigin(url, origin)).map(({method, url}) => `${method} ${url.href}`);
}

/** The requests to the lane whose path matches `path`. */
function laneRequests(network: OfflineNetwork, origin: string, path: RegExp): Recorded[] {
    return network.requests.filter(({url}) => url.origin === origin && path.test(url.pathname));
}

/** `<status> <method> <path>` of each request, once answered — `no answer` for one that failed. */
async function answers(requests: Recorded[]): Promise<string[]> {
    return Promise.all(requests.map(async ({method, url, request}) => `${(await request.response())?.status() ?? 'no answer'} ${method} ${url.pathname}`));
}

/**
 * Whether `violation` is the probe's: `connect-src`, blocked address exactly the probe's (its fragment, if the browser
 * keeps one, aside). Either disposition: a lane that also sends the report-only policy (`LIBREFOLIO_CSP_REPORT_ONLY`, on
 * in the managed profile) records the same block twice, once `enforce` and once `report`.
 */
function isProbeViolation(violation: CspViolation): boolean {
    return violation.directive === 'connect-src' && violation.blockedURI.split('#')[0] === OFFLINE_PROBE_URL;
}

/** One line per violation: disposition, directive, what it blocked, and where. */
function describeViolations(violations: CspViolation[]): string[] {
    return violations.map((violation) => `${violation.disposition} ${violation.directive} blocked ${violation.blockedURI || '(nothing)'} at ${violation.sourceFile || violation.documentURI}:${violation.lineNumber}`);
}

/** Whether the page can fetch `url`: a `no-cors` fetch resolves on any answer, and rejects only when none came back. */
async function canReach(page: Page, url: string): Promise<boolean> {
    return page.evaluate(async (target) => {
        try {
            await fetch(target, {mode: 'no-cors'});
            return true;
        } catch {
            return false;
        }
    }, url);
}

/**
 * A one-page PDF whose only text is `text`, set in Helvetica: a standard font, not embedded, with WinAnsiEncoding —
 * Latin, and nothing for the viewer to fetch. Written with an exact cross-reference table, so the engine reads the
 * file as it is rather than repairing it. `text` must be ASCII without parentheses or backslashes.
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

/** Signs the browser context in through the API — no page loaded yet — and returns the user it signed in. */
async function signInThroughApi(page: Page): Promise<{username: string; is_superuser: boolean}> {
    const response = await page.request.post(`${API}/auth/login`, {data: {username: TEST_USER.username, password: TEST_USER.password}});
    expect(response.ok(), `POST ${API}/auth/login as ${TEST_USER.username}: HTTP ${response.status()}`).toBe(true);
    return ((await response.json()) as {user: {username: string; is_superuser: boolean}}).user;
}

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
 * Opens the preview of `fileId` from the Files list, and ends on the page drawn. The list is narrowed to the file by the
 * page's own URL filter: one row, on the table's first page, whatever else the lane stores.
 */
async function openPdfPreview(page: Page, fileId: string, filename: string): Promise<void> {
    await navigateTo(page, `/files?tab=static&filename=${encodeURIComponent(filename)}`);
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

test.describe('PDF preview without internet (1.2 gap 7)', () => {
    // The positive control below fetches jsDelivr on purpose, and the policy blocks it with an enforced connect-src
    // violation the baseline does not (and must not) know: the collector records it and attaches it, but does not fail
    // the test for it. The test checks itself that it is the only unknown violation. This describe holds this one test.
    test.use({cspFailOnUnknown: false});

    let network: OfflineNetwork | undefined;
    /** Static files this test uploaded, deleted after it. */
    let ownedStaticFiles: string[] = [];

    test.beforeEach(async ({context, baseURL}) => {
        ownedStaticFiles = [];
        // Reset first: a start that fails must not leave the previous test's log to this test's afterEach.
        network = undefined;
        network = await goOffline(context, laneOrigin(baseURL));
    });

    test.afterEach(async ({page, context}, testInfo) => {
        for (const fileId of ownedStaticFiles) await deleteStaticFile(page, fileId);
        await context.unrouteAll({behavior: 'ignoreErrors'});
        if (network) {
            const requests = network.requests.map(({method, url, request}) => `${method} ${url.href}${request.failure() ? ` — ${request.failure()?.errorText}` : ''}`);
            await testInfo.attach('requests.json', {body: JSON.stringify({refused: network.refused, requests}, null, 1), contentType: 'application/json'});
        }
    });

    test('a one-page Latin PDF is drawn with every other origin refused: its engine from the app, nothing asked of a CDN', async ({page, baseURL, cspViolations}) => {
        const origin = laneOrigin(baseURL);
        const offline = network;
        if (!offline) throw new Error('beforeEach did not cut the browser off from other origins');

        const user = await signInThroughApi(page);
        expect(user.is_superuser, `precondition: ${user.username} is an ordinary member — an administrator's browser asks GitHub for a newer release once the app loads (F14, updateCheck.ts), another origin outside this spec's subject`).toBe(false);

        const filename = `pdf-offline-${uniqueSuffix()}.pdf`;
        const fileId = await uploadStaticPdf(page, filename, latinPdf(PDF_TEXT));
        ownedStaticFiles.push(fileId);
        console.log(`owned static file ${fileId} uploaded: ${filename}`);

        try {
            await openPdfPreview(page, fileId, filename);
        } catch (error) {
            // Never drawn: name what the browser asked of other origins meanwhile — a viewer waiting on an unreachable
            // CDN is exactly what this spec looks for.
            const asked = askedOfOtherOrigins(offline, origin);
            expect.soft(asked, `the page was not drawn, and meanwhile the browser asked other origins:\n${asked.join('\n')}`).toEqual([]);
            // The collector does not fail for the probe's violation here, so what else it saw is named now: a viewer blocked by
            // the policy is as much this spec's subject as one waiting on an unreachable CDN.
            expect.soft(describeViolations(cspViolations.unknown()), 'the page was not drawn, and meanwhile the policy blocked').toEqual([]);
            throw error;
        }

        // The subject: from the first navigation to the page drawn, nothing asked of another origin.
        const asked = askedOfOtherOrigins(offline, origin);
        expect(asked, `the browser asked other origins while previewing the PDF (${offline.refused.length} refused):\n${asked.join('\n')}`).toEqual([]);

        // Not jsDelivr, in particular, by any request of the context (the page's, the worker's, the service worker's), whether
        // the route refused it or not: the engine, the fonts and the fallback all come from the app (H-55 wave 4). The only
        // address of that host the log may hold is the positive control's own probe, fetched below on purpose.
        const cdnRequests = offline.requests.filter(({url}) => url.hostname === 'cdn.jsdelivr.net' && url.href !== OFFLINE_PROBE_URL).map(({method, url}) => `${method} ${url.href}`);
        expect(cdnRequests, `the browser asked cdn.jsdelivr.net while previewing the PDF:\n${cdnRequests.join('\n')}`).toEqual([]);

        // Positive control: the log sees the engine's worker. The page only probes the engine with a HEAD
        // (pdfViewerAssets.ts); the GET is the worker fetching it. Without that GET in the log, the list above could be
        // empty because the worker's requests went unseen.
        const engine = laneRequests(offline, origin, LOCAL_ENGINE_PATH);
        expect(
            engine.filter(({method}) => method === 'GET').map(({url}) => url.pathname),
            "the engine's worker fetched the app's own pdfium.wasm: if this is empty, the log no longer sees the worker's requests",
        ).not.toEqual([]);
        const engineAnswers = await answers(engine);
        expect(
            engineAnswers.filter((answer) => !answer.startsWith('200 ')),
            `the app answered every request for its engine with a 200: ${engineAnswers.join(', ')}`,
        ).toEqual([]);
        const fontAnswers = await answers(laneRequests(offline, origin, LOCAL_VIEWER_FONT_PATH));
        expect(
            fontAnswers.filter((answer) => !answer.startsWith('200 ')),
            `every fallback font the viewer asked for came from the app with a 200: ${fontAnswers.join(', ')}`,
        ).toEqual([]);

        // Positive control: the browser really has no internet. From the page, jsDelivr is out of reach — the fetch rejects —
        // and the refusal is recorded, by whoever made it: the policy (an enforced connect-src violation for exactly the
        // probe's address, as the page's own collector saw it; the fetch never reaches the route) or, if the policy allows
        // the CDN, the spec's route (the request in `refused`). Polled: the violation is reported by a binding call.
        expect(await canReach(page, OFFLINE_PROBE_URL), 'positive control: from the page, jsDelivr is out of reach').toBe(false);
        const refusal = () => (cspViolations.list().some((violation) => violation.disposition === 'enforce' && isProbeViolation(violation)) ? 'policy' : offline.refused.includes(`GET ${OFFLINE_PROBE_URL}`) ? 'route' : 'none');
        await expect.poll(refusal, {message: 'positive control: the probe was refused by the policy (connect-src violation) or by the route (refused), and the refusal is recorded', timeout: PROBE_REFUSAL_TIMEOUT_MS}).not.toBe('none');
        console.log(`offline probe refused by the ${refusal()}`);
        // The probe's violation is the only one the baseline does not know: the collector no longer fails for the others,
        // so the test does. Nothing else was blocked by the policy while the viewer drew the page.
        expect(describeViolations(cspViolations.unknown().filter((violation) => !isProbeViolation(violation))), 'violations of the Content-Security-Policy the baseline does not know, other than the probe').toEqual([]);
        // And since the page was drawn, nothing but that probe went to another origin (when the browser's own check
        // stopped it before the network layer, it may not be in the log at all).
        expect(
            askedOfOtherOrigins(offline, origin).filter((entry) => entry !== `GET ${OFFLINE_PROBE_URL}`),
            'after the page was drawn, the browser asked other origins',
        ).toEqual([]);

        const fileAnswers = await answers(offline.requests.filter(({url}) => url.origin === origin && url.pathname.includes(fileId)));
        console.log(`offline preview: ${offline.requests.length} requests, none to another origin but the probe; engine ${engineAnswers.join(', ')}; viewer fonts ${fontAnswers.join(', ') || 'none asked'}; this file ${fileAnswers.join(', ')}`);
    });
});
