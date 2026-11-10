/**
 * Documentation diagrams without internet: Mermaid served by the site itself — H6-3, backlog M-22.
 *
 * Mermaid used to be imported (with its ELK layout) from jsDelivr by a module that ran after Material for MkDocs'
 * bundle: offline the diagrams stayed code, online every page called a third party — and, with the CDN out of reach,
 * Material's bundle (which draws as soon as it runs and, when `window.mermaid` is not defined, fetches its own copy
 * from unpkg) asked unpkg instead. Now the site carries `mermaid.min.js` (exact version, pinned by SHA-256 in
 * `scripts/update_js_cache.py`, filled into `javascripts/vendor/mermaid/`) and `overrides/main.html` writes it, then
 * `javascripts/mermaid-early.js` (adds `securityLevel: "loose"` to Material's `initialize`), in `<head>` BEFORE
 * Material's bundle, on the pages that have a diagram.
 *
 * On a page with a diagram, with every origin but the lane's refused — jsDelivr and unpkg included:
 *
 *   1. the page is the built documentation, and it has a Mermaid diagram (`.mermaid`): counted, or everything below
 *      would pass on nothing;
 *   2. the page asked the lane for the copy, `/mkdocs/javascripts/vendor/mermaid/mermaid.min.js`, and got 200 —
 *      every answer is recorded wherever the bundle was asked for, so a red names the place;
 *   3. Material replaced the `<pre class="mermaid">` with its rendered diagram and the SVG is there, visible, with
 *      nodes, and it is not Mermaid's error drawing (`aria-roledescription="error"`);
 *   4. neither jsDelivr nor unpkg was asked at all: not one request left the page for those hosts (recorded from the
 *      `request` event, which fires before any route answers), after a positive control proving the refusal is
 *      recorded — from the page both are out of reach. unpkg is the one Material's own bundle asks when the template
 *      did not define Mermaid first: that was the failure of the first design.
 *
 * Two pages: a diagram without frontmatter, and one whose frontmatter asks for `layout: elk`. ELK is dropped (its ESM
 * build needs ~100 chunks): that diagram must still be drawn, with the default layout, not left as an error.
 *
 * Selectors: `.mermaid`, `svg` — not styling but the contract: the class `mkdocs.yml` gives the custom fence, and the
 * SVG Mermaid draws. Material draws it inside a CLOSED shadow root, unreachable from a test; an init script makes the
 * roots open (same behaviour, observable), so the SVG is read where the user sees it. The documentation carries no
 * data-testid.
 *
 * Waiting: on the answer that is the subject (recorded from before the navigation), then on the SVG becoming visible —
 * Playwright retries both. Never on the clock, never on the console. Public and read-only.
 *
 * Needs: `./dev.py cache js` fetches Mermaid (and MathJax), then `./dev.py mkdocs build`. The lane's server rebuilds a
 * site older than a `.md`, not one older than a script, a template or a vendored file alone: after a change to
 * `mermaid-early.js` or `overrides/main.html`, or with Mermaid cached after the site was built, `./dev.py mkdocs build` first. A site without the
 * vendored file is a red precondition here with a message saying so, never a skip.
 */
import {expect, test, type Page} from '../fixtures/playwright';

/** The site's root, as the backend serves it. */
const SITE_ROOT = '/mkdocs/';
/** Where the template must point to the site's own copy: `<vendor>/<library name>/<target>`, whatever the page. */
const LOCAL_MERMAID_PATH = `${SITE_ROOT}javascripts/vendor/mermaid/mermaid.min.js`;
/** Positive controls: an address on jsDelivr and one on unpkg — not Mermaid ones, so a control cannot be mistaken for a fallback. */
const OFFLINE_PROBE_URL = 'https://cdn.jsdelivr.net/npm/librefolio-e2e-offline-probe/index.js';
const OFFLINE_PROBE_UNPKG_URL = 'https://unpkg.com/librefolio-e2e-offline-probe/index.js';

/** English pages with a diagram: one plain, one asking for the ELK layout in its frontmatter. */
const PAGES = [
    {label: 'a diagram with the default layout', path: `${SITE_ROOT}admin/backup_sealed/`},
    {label: 'a diagram whose frontmatter asks for layout: elk', path: `${SITE_ROOT}developer/test-walkthrough/runner_architecture/`},
];

/** A documentation page with its scripts and styles, on a loaded machine. */
const PAGE_TIMEOUT_MS = 30_000;
/** Mermaid: a ~3 MB bundle fetched, parsed and run, then the diagram laid out — on a loaded machine. */
const DIAGRAM_TIMEOUT_MS = 30_000;

test.setTimeout(90_000);

/** The runner's baseURL, as an origin: the only one this spec lets the browser reach. */
function laneOrigin(baseURL: string | undefined): string {
    if (!baseURL) throw new Error('This spec needs the runner-provided baseURL');
    return new URL(baseURL).origin;
}

/** Refuses every origin but the lane's, as a machine without internet would. Returns the refused URLs, in order. */
async function keepOffline(page: Page, origin: string): Promise<string[]> {
    const refused: string[] = [];
    await page.route(
        (url) => (url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== origin,
        (route) => {
            refused.push(route.request().url());
            return route.abort('blockedbyclient');
        },
    );
    return refused;
}

/** Every answer the lane gives to the requests `wanted` picks out by path: `<status> <path>`. Armed before the navigation. */
function recordAnswers(page: Page, origin: string, wanted: (path: string) => boolean): string[] {
    const answers: string[] = [];
    page.on('response', (response) => {
        const url = new URL(response.url());
        if (url.origin === origin && wanted(url.pathname)) answers.push(`${response.status()} ${url.pathname}`);
    });
    return answers;
}

/** Every request the page makes to `hostname`, from the `request` event (fired before any route answers). Armed before the navigation. */
function recordRequestsTo(page: Page, hostname: string): string[] {
    const requests: string[] = [];
    page.on('request', (request) => {
        if (new URL(request.url()).hostname === hostname) requests.push(request.url());
    });
    return requests;
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

test.describe('Documentation diagrams without internet: Mermaid from the site’s own copy (M-22)', () => {
    test.afterEach(async ({page}) => {
        await page.unrouteAll({behavior: 'ignoreErrors'});
    });

    for (const target of PAGES) {
        test(`${target.label}: ${target.path} is drawn with every other origin refused, jsDelivr and unpkg never asked`, async ({page, baseURL}) => {
            const origin = laneOrigin(baseURL);
            // Material draws into a closed shadow root: open it, so the SVG is reachable where the user sees it.
            await page.addInitScript(() => {
                const attachShadow = Element.prototype.attachShadow;
                Element.prototype.attachShadow = function (this: Element, init: ShadowRootInit) {
                    return attachShadow.call(this, {...init, mode: 'open'});
                };
            });
            const refused = await keepOffline(page, origin);
            const jsdelivr = recordRequestsTo(page, 'cdn.jsdelivr.net');
            const unpkg = recordRequestsTo(page, 'unpkg.com');
            const bundleAnswers = recordAnswers(page, origin, (path) => path.endsWith('/mermaid.min.js'));

            const response = await page.goto(target.path, {timeout: PAGE_TIMEOUT_MS});
            expect(response?.status(), `precondition: the lane serves ${target.path} (a 404 is a page that moved: point this spec at another English page with a Mermaid diagram)`).toBe(200);
            await expect(page.locator('meta[name="generator"]'), `precondition: ${target.path} is a page of the built documentation — an unbuilt site answers «Documentation not generated» (backend/app/main.py): build it, see this file's header`).toHaveAttribute('content', /\bmkdocs-/);
            const diagrams = page.locator('.mermaid');
            await expect(diagrams, `precondition: ${target.path} has a Mermaid diagram, or every assertion below would pass on nothing`).not.toHaveCount(0);

            await expect
                .poll(() => [...bundleAnswers], {
                    message: `the page asked the lane for the site’s own copy and got 200 — a 404 means the site has no ${LOCAL_MERMAID_PATH}: ./dev.py cache js, then ./dev.py mkdocs build (an empty list: overrides/main.html does not write it, or the site was built before it)`,
                    timeout: DIAGRAM_TIMEOUT_MS,
                })
                .toContain(`200 ${LOCAL_MERMAID_PATH}`);

            const svg = diagrams.locator('svg').first();
            await expect(svg, 'Mermaid drew the diagram: an SVG is on screen').toBeVisible({timeout: DIAGRAM_TIMEOUT_MS});
            await expect(svg.locator('g').first(), 'the SVG holds the drawing, not an empty shell').toBeAttached();
            await expect(diagrams.locator('svg[aria-roledescription="error"]'), 'no diagram ended in Mermaid’s error drawing (a layout it cannot load is one)').toHaveCount(0);
            await expect(page.locator('pre.mermaid'), 'Material replaced every source block with its diagram: none is left as code').toHaveCount(0);

            expect(await canReach(page, OFFLINE_PROBE_URL), 'positive control: from this page jsDelivr is out of reach').toBe(false);
            expect(await canReach(page, OFFLINE_PROBE_UNPKG_URL), 'positive control: from this page unpkg is out of reach').toBe(false);
            expect(refused, 'positive control: the refusal is this spec’s, and it is recorded').toEqual(expect.arrayContaining([OFFLINE_PROBE_URL, OFFLINE_PROBE_UNPKG_URL]));
            // The probes above are the spec's own requests: everything the page asked of these hosts before them is the page's.
            expect(
                jsdelivr.filter((url) => url !== OFFLINE_PROBE_URL),
                'jsDelivr was never asked: not Mermaid, not a layout, not a chunk, not MathJax — the site serves its own copies',
            ).toEqual([]);
            expect(
                unpkg.filter((url) => url !== OFFLINE_PROBE_UNPKG_URL),
                'unpkg was never asked: Material’s own bundle asks it for Mermaid when the template did not define window.mermaid before it',
            ).toEqual([]);
        });
    }
});
