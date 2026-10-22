/**
 * The API's documentation pages, Swagger UI and ReDoc, as the lane serves them (H-55 R5, backend/app/api/api_docs.py):
 * they render under the policy the backend sends them (`api_docs_policy`, security_headers.py), and the only thing they
 * fetch from another origin is the pinned jsDelivr files, each protected by its Subresource Integrity hash.
 *
 * Why. FastAPI's own pages load `swagger-ui-dist@5` / `redoc@2` from jsDelivr at a moving version, with no integrity, and
 * start them with an inline script. The pages are ours now: exact versions, `integrity` + `crossorigin="anonymous"` on
 * every tag, start scripts served by the instance, so that the page runs under `script-src 'self' https://cdn.jsdelivr.net`.
 * The backend tests pin the HTML and the header; this spec proves the other half, in a browser: the policy lets the page
 * work, the browser accepts the files (they match their hashes), and a file that does not match is refused.
 *
 * A test lane has the documentation on: test mode switches it on (`config.api_docs_enabled()`). Off, the pages answer 404
 * and this spec fails on its first assertion, naming the precondition.
 *
 * What is read, per page:
 *   - the document as the browser received it: 200, `text/html`, exactly one `Content-Security-Policy` field, with
 *     `script-src 'self' https://cdn.jsdelivr.net`, `worker-src 'self' blob:`, `connect-src 'self'`, the trio
 *     (`object-src 'none'`, `base-uri 'self'`, `form-action 'self'`) and `frame-ancestors 'self'` exactly when the response
 *     says frame protection is on (`X-Frame-Options: SAMEORIGIN`), as page-policy.spec.ts reads a lane's header;
 *   - every request of the browser context, recorded from before the first navigation: the only ones leaving the lane's
 *     origin are GETs to exactly the pinned URLs of that page, each answered 200 — nothing for `fonts.googleapis.com`,
 *     nothing for `validator.swagger.io`;
 *   - the pinned files were *used*, not only fetched: a fetched file the browser refused (a wrong hash) would still show
 *     as a 200. Swagger UI draws operations of the lane's own API — at least a few, each one's `data-path` a key of the
 *     `paths` of the OpenAPI document the page itself fetched (its response body, read from the request log: no second
 *     request of the spec's own) — and ReDoc its menu;
 *   - the OpenAPI document was fetched from the lane (`/api/v1/openapi.json`, 200);
 *   - the H-43 collector (`cspViolations`, fixtures/playwright.ts) saw no enforced violation.
 *
 * The tamper test: the Swagger bundle's URL is answered with another body (a lone comment), with a CORS header so that the
 * only thing the browser can object to is the hash. The page must not draw operations and nothing of the library may have
 * run: `window.SwaggerUIBundle` is undefined and the instance's own start script fails on it (that failure is the
 * presence barrier: the start script ran, after the refused bundle, and had nothing to start).
 *
 * Needs the internet: the libraries come from `cdn.jsdelivr.net`. A lane on a machine that cannot reach it is a red
 * precondition — a network error on a request to another origin fails the test naming that, never a skip, never a bare
 * timeout on «Swagger did not render». The tamper test needs no network: its bundle is answered by the spec.
 *
 * Selectors: Swagger UI and ReDoc carry no `data-testid`, so their own markup is the contract, as the documentation's
 * Material markup is in page-policy.spec.ts: Swagger's `#swagger-ui` container and its operations' `.opblock` with the
 * `data-path` of their summary; ReDoc's `#redoc` container and its menu (`[role=menu]`, `.menu-content`). No translated text.
 * Swagger UI 5.33 draws its operations in a virtualized list: only those in or near the viewport are in the DOM, in the
 * order of the document's tags. So no named operation is waited for (one far down the document is never mounted without
 * a scroll): whichever operations are drawn, each must be one of the document's.
 *
 * Waiting: on the states the pages produce (an operation drawn, a menu drawn, an error raised), never on the clock.
 * Desktop only: ReDoc's menu is a drawer on a phone. Nothing is written to the lane.
 */
import {expect, test, type BrowserContext, type Page, type Request, type Response} from '../fixtures/playwright';

const API = '/api/v1';
const DOCS_PATH = `${API}/docs`;
const REDOC_PATH = `${API}/redoc`;
const OPENAPI_PATH = `${API}/openapi.json`;
/** Swagger UI's first screen holds at least this many operations: the start of the virtualized list, whatever its first tag. */
const MIN_DRAWN_OPERATIONS = 3;

/** The origin of the libraries: the only third party the pages may ask. */
const LIBRARY_ORIGIN = 'https://cdn.jsdelivr.net';
/** The pinned files, as `LIBRARIES` in backend/app/api/api_docs.py names them. A new version of a library is a new line here, with the backend's. */
const SWAGGER_JS = `${LIBRARY_ORIGIN}/npm/swagger-ui-dist@5.33.1/swagger-ui-bundle.js`;
const SWAGGER_CSS = `${LIBRARY_ORIGIN}/npm/swagger-ui-dist@5.33.1/swagger-ui.css`;
const REDOC_JS = `${LIBRARY_ORIGIN}/npm/redoc@2.5.4/bundles/redoc.standalone.js`;

/** Hosts no page may ask: Swagger's validator badge and Google Fonts (the pages set `validatorUrl: null` and carry no font link). */
const FORBIDDEN_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com', 'validator.swagger.io'];

/** A page of the documentation, with a slow CDN on a loaded machine. */
const PAGE_TIMEOUT_MS = 30_000;
/** The library fetched, parsed, the OpenAPI document fetched and drawn. */
const RENDER_TIMEOUT_MS = 30_000;
/** The tampered bundle refused and the start script run after it: both happen before the `load` event, so this is a round trip. */
const REFUSAL_TIMEOUT_MS = 10_000;

test.setTimeout(90_000);

/** The spec reads the documents the lane sent over the network: no service worker answers for them. */
test.use({serviceWorkers: 'block'});

/** One page under test: its path, the pinned files it loads, and what «rendered» means for it. */
interface DocsPage {
    name: string;
    path: string;
    /** The pinned files of this page: each is requested once, with its hash. */
    libraries: string[];
    /** Resolves once the library has drawn the lane's API; the wait fails on its own timeout. */
    rendered(page: Page, lane: Lane): Promise<void>;
}

/** The lane under test, as `rendered` reads it: its origin and the requests the context made. */
interface Lane {
    origin: string;
    log: RequestLog;
}

const DOCS_PAGES: DocsPage[] = [
    {
        name: 'Swagger UI',
        path: DOCS_PATH,
        libraries: [SWAGGER_JS, SWAGGER_CSS],
        async rendered(page, lane) {
            const operations = page.locator('#swagger-ui .opblock [data-path]');
            // Any operation will do — the list is virtualized and ordered by tag — so .first() names no position the test relies on: what it is gets checked below.
            await expect(operations.first(), `Swagger UI drew an operation: the bundle ran, read ${OPENAPI_PATH} and rendered it`).toBeVisible({timeout: RENDER_TIMEOUT_MS});
            await expect.poll(() => operations.count(), {message: `Swagger UI drew at least ${MIN_DRAWN_OPERATIONS} operations`, timeout: RENDER_TIMEOUT_MS}).toBeGreaterThanOrEqual(MIN_DRAWN_OPERATIONS);
            // Read once the barriers above hold: the operations drawn are the document's, not a placeholder or another API's.
            const drawn = [...new Set(await operations.evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-path') ?? '')))].sort();
            const paths = await servedOpenApiPaths(lane);
            expect(
                drawn.filter((path) => !paths.has(path)),
                `every operation Swagger UI drew (${drawn.join(', ')}) is a path of the ${OPENAPI_PATH} the page fetched`,
            ).toEqual([]);
        },
    },
    {
        name: 'ReDoc',
        path: REDOC_PATH,
        libraries: [REDOC_JS],
        async rendered(page) {
            const redoc = page.locator('#redoc');
            // A menu or its content: whichever ReDoc's build names it, the union is one thing, drawn from the OpenAPI document.
            const menu = redoc.locator('[role="menu"]').or(redoc.locator('.menu-content'));
            await expect(menu.first(), `ReDoc drew its menu: the standalone bundle ran, read ${OPENAPI_PATH} and rendered it`).toBeVisible({timeout: RENDER_TIMEOUT_MS});
        },
    },
];

/** A request of the browser context, as it ended. */
interface SeenRequest {
    method: string;
    url: string;
    /** The HTTP status, once answered. */
    status: number | null;
    /** The network error, once failed (`net::ERR_…`). */
    failure: string | null;
}

/** Everything the context asked, in the order the requests started; the map keeps each `Request` apart, redirects included. */
type RequestLog = Map<Request, SeenRequest>;

/**
 * The keys of `paths` of the OpenAPI document the page fetched from the lane: the body of the browser's own response,
 * found in the request log — the spec asks the lane nothing itself, so the request accounting stays the page's alone.
 */
async function servedOpenApiPaths({origin, log}: Lane): Promise<Set<string>> {
    const request = [...log.entries()].find(([, seen]) => seen.url === `${origin}${OPENAPI_PATH}` && seen.method === 'GET' && seen.status === 200)?.[0];
    if (!request) throw new Error(`${OPENAPI_PATH}: the page fetched no 200 from the lane, so there is no document to compare the drawn operations with`);
    const response = await request.response();
    if (!response) throw new Error(`${OPENAPI_PATH}: the request has no response`);
    const document = (await response.json()) as {paths?: Record<string, unknown>};
    const paths = new Set(Object.keys(document.paths ?? {}));
    if (paths.size === 0) throw new Error(`${OPENAPI_PATH}: the document the page fetched has no paths`);
    return paths;
}

/** Records every request of every page of the context, from before the first navigation: a state read when the test chooses. */
function recordRequests(context: BrowserContext): RequestLog {
    const log: RequestLog = new Map();
    context.on('request', (request) => {
        log.set(request, {method: request.method(), url: request.url(), status: null, failure: null});
    });
    context.on('response', (response: Response) => {
        const seen = log.get(response.request());
        if (seen) seen.status = response.status();
    });
    context.on('requestfailed', (request) => {
        const seen = log.get(request);
        if (seen) seen.failure = request.failure()?.errorText ?? 'failed';
    });
    return log;
}

/** The runner's baseURL, as an origin: the lane. */
function laneOrigin(baseURL: string | undefined): string {
    if (!baseURL) throw new Error('This spec needs the runner-provided baseURL');
    return new URL(baseURL).origin;
}

/** The requests that left the lane's origin over HTTP(S): `data:` and `blob:` URLs never reach a network. */
function offOrigin(log: RequestLog, origin: string): SeenRequest[] {
    return [...log.values()].filter((seen) => {
        const url = new URL(seen.url);
        return (url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== origin;
    });
}

/** A failure that is not the network's: the policy or an extension refusing the request, or the page cancelling it. */
const NOT_A_NETWORK_FAILURE = /BLOCKED_BY_CSP|BLOCKED_BY_CLIENT|BLOCKED_BY_RESPONSE|ERR_ABORTED/;

/**
 * The precondition of the spec: the lane's machine reaches the CDN. A request to another origin that failed in the
 * network (offline, no DNS, no route, refused connection, TLS) is that precondition missing, and says so.
 */
function assertCdnReachable(log: RequestLog, origin: string): void {
    const unreachable = offOrigin(log, origin).filter((seen) => seen.failure !== null && !NOT_A_NETWORK_FAILURE.test(seen.failure));
    if (unreachable.length > 0) {
        throw new Error(
            `PRECONDITION: this spec needs internet access to ${LIBRARY_ORIGIN} (the pages load Swagger UI and ReDoc from there, pinned with SRI) and the machine did not reach it:\n${unreachable.map((seen) => `  ${seen.method} ${seen.url}: ${seen.failure}`).join('\n')}\nRun the lane on a machine with internet, or fix the network; this is not a product failure.`,
        );
    }
}

/** Runs `wait` (a render wait); a failure of it with the CDN unreachable is the precondition's red, not a timeout on the library. */
async function orPreconditionRed(log: RequestLog, origin: string, wait: () => Promise<void>): Promise<void> {
    try {
        await wait();
    } catch (error) {
        assertCdnReachable(log, origin);
        throw error;
    }
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

/** A response's header fields, every field of its name apart: `headersArray()` keeps repeated fields from being joined. */
function fieldsOf(headers: ReadonlyArray<{name: string; value: string}>, wanted: string): string[] {
    return headers.filter(({name}) => name.toLowerCase() === wanted).map(({value}) => value);
}

/**
 * What is wrong with the policy the documentation page reached the browser with (`api_docs_policy`): exactly one
 * Content-Security-Policy field, the scripts of the instance and of jsDelivr only, a worker from a blob, connections to
 * the instance, the document trio, and `frame-ancestors 'self'` exactly when frame protection is on. Empty when nothing is wrong.
 */
async function policyProblems(response: Response): Promise<string[]> {
    const headers = await response.headersArray();
    const policies = fieldsOf(headers, 'content-security-policy');
    if (policies.length !== 1) return [`${policies.length} Content-Security-Policy fields, one expected: ${JSON.stringify(policies)}`];
    const directives = parsePolicy(policies[0]);
    const frameProtection = fieldsOf(headers, 'x-frame-options')[0]?.trim().toUpperCase() === 'SAMEORIGIN';
    const expected: Array<[string, string | undefined]> = [
        ['script-src', `'self' ${LIBRARY_ORIGIN}`],
        ['worker-src', "'self' blob:"],
        ['connect-src', "'self'"],
        ['object-src', "'none'"],
        ['base-uri', "'self'"],
        ['form-action', "'self'"],
        ['frame-ancestors', frameProtection ? "'self'" : undefined],
    ];
    return expected.filter(([name, sources]) => directives.get(name) !== sources).map(([name, sources]) => `${name}: ${sources === undefined ? 'absent (frame protection is off)' : sources} expected, got ${directives.get(name) ?? 'absent'}`);
}

/** The violations the H-43 collector saw that were enforced: a report-only policy reports without blocking. */
function enforcedViolations(list: ReadonlyArray<{disposition: string; directive: string; blockedURI: string; documentURI: string}>): string[] {
    return list.filter((violation) => violation.disposition === 'enforce').map((violation) => `${violation.directive} blocked ${violation.blockedURI || '(nothing)'} in ${violation.documentURI}`);
}

/** Every `<script src>` and `<link href>` of the page to `url` carries its hash and `crossorigin="anonymous"`: what lets the browser refuse a changed file. */
async function expectIntegrity(page: Page, url: string): Promise<void> {
    const tag = page.locator(`script[src="${url}"], link[href="${url}"]`);
    await expect(tag, `the page loads ${url} with a Subresource Integrity hash`).toHaveAttribute('integrity', /^sha384-[A-Za-z0-9+/]+=*$/);
    await expect(tag, `the page loads ${url} with crossorigin="anonymous"`).toHaveAttribute('crossorigin', 'anonymous');
}

test.describe('The API documentation pages of H-55 R5: the policy lets the pinned libraries work, and the integrity hash refuses a changed one', () => {
    let log: RequestLog = new Map();

    test.beforeEach(async ({context, isMobile}) => {
        test.skip(isMobile, 'desktop only: ReDoc draws its menu as a drawer on a phone');
        log = recordRequests(context);
    });

    test.afterEach(async ({}, testInfo) => {
        await testInfo.attach('requests.json', {body: JSON.stringify([...log.values()], null, 1), contentType: 'application/json'});
    });

    for (const docs of DOCS_PAGES) {
        test(`${docs.name} (${docs.path}): 200 text/html under the documentation policy, renders the lane's API from the pinned files only, no enforced CSP violation`, async ({page, baseURL, cspViolations}) => {
            const origin = laneOrigin(baseURL);

            const response = await page.goto(docs.path, {timeout: PAGE_TIMEOUT_MS});
            if (!response) throw new Error(`${docs.path}: goto returned no response`);
            expect(response.status(), `precondition: the lane serves ${docs.path} — the documentation is on in test mode; a 404 is a lane (or a build) with LIBREFOLIO_API_DOCS and test mode both off`).toBe(200);
            expect(response.headers()['content-type'] ?? '', `${docs.path} answers text/html`).toMatch(/^text\/html\b/);
            expect(new URL(page.url()).pathname, `${docs.path} did not redirect`).toBe(docs.path);
            expect(await policyProblems(response), `${docs.path} reached the browser with the documentation policy (api_docs_policy)`).toEqual([]);

            // The `load` event waits for the synchronous library scripts: a CDN that cannot be reached has failed by now.
            assertCdnReachable(log, origin);
            for (const url of docs.libraries) await expectIntegrity(page, url);
            await orPreconditionRed(log, origin, () => docs.rendered(page, {origin, log}));

            // The requests: what left the lane is exactly the pinned files, GETs, each answered 200.
            const left = offOrigin(log, origin);
            expect([...new Set(left.map((seen) => `${seen.method} ${seen.url}`))].sort(), `the only requests leaving the lane are GETs to the pinned files of ${docs.path}`).toEqual(docs.libraries.map((url) => `GET ${url}`).sort());
            expect(
                left.filter((seen) => seen.status !== 200),
                'every request to another origin was answered 200 (and none failed)',
            ).toEqual([]);
            const hosts = [...log.values()].map((seen) => new URL(seen.url).hostname);
            for (const host of FORBIDDEN_HOSTS) expect(hosts, `no request to ${host}`).not.toContain(host);

            // The OpenAPI document came from the lane: it is what the library drew.
            const openapi = [...log.values()].filter((seen) => seen.url === `${origin}${OPENAPI_PATH}`);
            expect(
                openapi.map((seen) => `${seen.method} ${seen.status}`),
                `${OPENAPI_PATH} was fetched from the lane and answered 200`,
            ).toContainEqual('GET 200');

            // Nothing enforced was breached: a report that is still on its way is one round trip behind.
            await page.evaluate(() => 0);
            expect(enforcedViolations(cspViolations.list()), `${docs.path} raised enforced Content-Security-Policy violations`).toEqual([]);
        });
    }

    test(`a changed Swagger bundle is refused by its integrity hash: ${DOCS_PATH} draws no operation and nothing of the library runs`, async ({page, context, baseURL, cspViolations}) => {
        const origin = laneOrigin(baseURL);
        let served = 0;
        // CORS allowed on purpose: the page asks with crossorigin="anonymous", and without this header the refusal would be CORS's, not the hash's.
        await context.route(SWAGGER_JS, (route) => {
            served += 1;
            return route.fulfill({status: 200, contentType: 'text/javascript', headers: {'access-control-allow-origin': '*'}, body: '/*tampered*/'});
        });
        const errors: string[] = [];
        page.on('pageerror', (error) => errors.push(error.message));

        const response = await page.goto(DOCS_PATH, {timeout: PAGE_TIMEOUT_MS});
        expect(response?.status(), `precondition: the lane serves ${DOCS_PATH}`).toBe(200);
        await expectIntegrity(page, SWAGGER_JS);

        // Barriers: the browser was given the changed body, and the instance's start script ran after it and found no library.
        await expect.poll(() => served, {message: 'the browser asked for the Swagger bundle and the spec answered with the changed body', timeout: REFUSAL_TIMEOUT_MS}).toBeGreaterThan(0);
        await expect
            .poll(() => errors.some((message) => message.includes('SwaggerUIBundle')), {
                message: `the start script ran and failed on the missing library — pageerrors: ${JSON.stringify(errors)}`,
                timeout: REFUSAL_TIMEOUT_MS,
            })
            .toBe(true);
        await expect(page.locator('#swagger-ui'), 'the page itself is there: the container the library would have drawn into').toBeAttached();

        // The refusal: nothing of the changed file ran, and nothing was drawn.
        expect(await page.evaluate(() => typeof (window as unknown as {SwaggerUIBundle?: unknown}).SwaggerUIBundle), 'the changed bundle did not execute: SwaggerUIBundle is undefined').toBe('undefined');
        expect(await page.evaluate(() => typeof (window as unknown as {ui?: unknown}).ui), 'the start script started no UI: window.ui is undefined').toBe('undefined');
        await expect(page.locator('#swagger-ui .opblock'), 'no operation was drawn').toHaveCount(0);

        // The OpenAPI document was never fetched: the only thing that asks for it is the library. And the refusal is the hash's, not the policy's.
        expect(
            [...log.values()].filter((seen) => seen.url === `${origin}${OPENAPI_PATH}`),
            `${OPENAPI_PATH} was never requested: no library ran to ask for it`,
        ).toEqual([]);
        await page.evaluate(() => 0);
        expect(enforcedViolations(cspViolations.list()), 'the refusal came from the integrity hash: the policy raised no enforced violation').toEqual([]);
    });
});
