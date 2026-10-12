/**
 * Documentation formulas without internet — M-19, fixed in workstream M's batch 24 and completed in batch 25.
 *
 * Every documentation page loads MathJax through `mkdocs_src/docs/javascripts/lib-loader.js`: the site's own copy first,
 * `javascripts/vendor/mathjax/tex-mml-chtml.js` at the site's root (cached by `scripts/update_js_cache.py`, copied by the
 * docs build), jsDelivr as the fallback. Before the fix the loader looked for the copy in the page's own folder, so only
 * the pages at the site's root found it: on every nested page the copy answered 404 and MathJax came from jsDelivr —
 * online, a call to a third party from every nested page; offline, as in the full image without internet, not one
 * formula drawn. The loader now takes the site's root from its own address (`document.currentScript`): MkDocs links it
 * relative to each page, so it always lands at the root, whatever the page's depth, its language folder or the path the
 * site is served at — `/mkdocs/` here, where backend/app/main.py serves `mkdocs_src/site`.
 *
 * Batch 25 completed the copy. MathJax's CHTML output loads its fonts from beside the bundle
 * (`output/chtml/fonts/woff-v2/`), and the bundle had come alone: the formulas were drawn, but in the page's font —
 * letters upright, fractions clipped, the MJX faces in `error`. `update_js_cache.py` now fetches the `MathJax_*.woff`
 * files the bundle names. And `javascripts/mathjax.js`, which Material's `document$` runs before lib-loader.js has loaded
 * MathJax, calls `MathJax.typesetPromise()` only once it exists: before, that threw a TypeError on every page.
 *
 * On a nested page with formulas, in English (three folders below the root) and in Italian (`it/`, one folder deeper),
 * with every origin but the lane's refused — jsDelivr included:
 *
 *   1. the page is the built documentation, and it has formulas: `.arithmatex` is counted, because on a page without any
 *      every assertion below would pass on nothing;
 *   2. the loader asked the lane for the copy at the site's root, `/mkdocs/javascripts/vendor/mathjax/tex-mml-chtml.js`,
 *      and got 200. Every answer to a request for the bundle is recorded, wherever it was asked for, so a red names the
 *      place: a 404 under the page's own folder is M-19 back, a 404 at the root is a copy the site does not have;
 *   3. MathJax drew them: an `mjx-container` on screen, and inside the formulas at least as many as there are formulas;
 *   4. once the page's fonts have settled, MathJax — its bundle or a font — was never asked of another origin. Asserted
 *      on MathJax, not on the jsDelivr host: `javascripts/mermaid.mjs` imports Mermaid from jsDelivr on every page,
 *      refused here like any other origin and outside M-19 (M-22). A positive control comes first, or this absence could
 *      be the route's silence: from the page, jsDelivr is out of reach, and the refusal is recorded;
 *   5. the fonts came from the site's copy: the lane answered at least one MathJax `.woff`, and every one is a 200 under
 *      `/mkdocs/javascripts/vendor/mathjax/output/chtml/fonts/woff-v2/` — recorded like the bundle, wherever asked for;
 *   6. the faces took them: at least one MJX face `loaded`, none in `error`;
 *   7. no page error names `typesetPromise` — that message only: the spec judges this defect, not every script on the
 *      page.
 *
 * Selectors: `.arithmatex` and `mjx-container` are not styling, they are the contract under test — the class
 * pymdownx.arithmatex writes around every formula, the only one `javascripts/mathjax.js` lets MathJax process
 * (`processHtmlClass`), and the element MathJax draws a formula into. The documentation carries no data-testid. The
 * faces are read from `document.fonts`, where MathJax's CHTML output declares its families — every one starts with `MJX`.
 *
 * Waiting: on the answer that is the subject, recorded from before the navigation, then on what MathJax writes into the
 * page, then on the page's fonts — `document.fonts.ready`, and no MJX face still `loading` — so that the checks on the
 * network and on the faces read a finished state. Never on the clock, never on the console (the loader's «Loaded
 * mathjax from local cache» is an edge); page errors, like answers, are recorded from before the navigation.
 *
 * Public and read-only: the documentation needs no sign-in and nothing is written; the one state a test changes is its
 * own browser context's routes, removed after each test.
 *
 * Needs: `./dev.py cache js` fetches the script and its fonts, then `./dev.py mkdocs build`. The lane's `dev.py server`
 * builds a missing site and rebuilds one older than a `.md`, but not one older than a script or a vendored file alone
 * (M-21): after a change to `lib-loader.js` alone, or with fonts cached after the site was built, `./dev.py mkdocs build`
 * first. An unbuilt site answers «Documentation not generated» on every `/mkdocs/` path: a red precondition here, never
 * a skip.
 */
import {expect, test, type Page} from '../fixtures/playwright';

/** The site's root, as the backend serves it. */
const SITE_ROOT = '/mkdocs/';
/** The site's copy of MathJax: the bundle, and beside it the fonts the bundle asks for. */
const LOCAL_MATHJAX_DIR = `${SITE_ROOT}javascripts/vendor/mathjax/`;
/** The bundle lib-loader.js loads: the same file name in the site's copy and on jsDelivr. */
const MATHJAX_BUNDLE = 'tex-mml-chtml.js';
/** Where the loader must find the site's own copy: at the root, whatever the page. */
const LOCAL_MATHJAX_PATH = `${LOCAL_MATHJAX_DIR}${MATHJAX_BUNDLE}`;
/** Where MathJax's CHTML output asks for its fonts: `[mathjax]/output/chtml/fonts/woff-v2/`, `[mathjax]` being the bundle's folder. */
const LOCAL_FONT_DIR = `${LOCAL_MATHJAX_DIR}output/chtml/fonts/woff-v2/`;
/** Positive control: an address on jsDelivr, the loader's fallback host — not a MathJax one, so it never counts as a request for MathJax. */
const OFFLINE_PROBE_URL = 'https://cdn.jsdelivr.net/npm/librefolio-e2e-offline-probe/index.js';

/** A nested page with formulas, in English and in Italian: the Italian one is a folder deeper. */
const NESTED_PAGES = [
    {label: 'English, three folders below the root', path: `${SITE_ROOT}financial-theory/fundamentals/day-count/`},
    {label: 'Italian, four folders below the root', path: `${SITE_ROOT}it/financial-theory/fundamentals/day-count/`},
];

/** A documentation page with its scripts and styles, on a loaded machine. */
const PAGE_TIMEOUT_MS = 30_000;
/** MathJax: a 1.2 MB bundle fetched, parsed and run, then the page typeset — on a loaded machine. */
const MATH_TIMEOUT_MS = 20_000;
/** MathJax's fonts: a few small files from the lane, asked for as the formulas are laid out — on a loaded machine. */
const FONT_TIMEOUT_MS = 15_000;

test.setTimeout(60_000);

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

/**
 * Every answer the lane gives to the requests `wanted` picks out by path, wherever they were asked for: `<status> <path>`.
 * Armed before the navigation — a response is an event, and one that has gone by is not replayed.
 */
function recordAnswers(page: Page, origin: string, wanted: (path: string) => boolean): string[] {
    const answers: string[] = [];
    page.on('response', (response) => {
        const url = new URL(response.url());
        if (url.origin === origin && wanted(url.pathname)) answers.push(`${response.status()} ${url.pathname}`);
    });
    return answers;
}

/** The page errors whose message names `typesetPromise`: what `mathjax.js` threw on every page before batch 25. Armed before the navigation. */
function recordTypesetErrors(page: Page): string[] {
    const errors: string[] = [];
    page.on('pageerror', (error) => {
        if (error.message.includes('typesetPromise')) errors.push(error.message);
    });
    return errors;
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

/** A request for MathJax, on whatever host: jsDelivr today, any CDN the loader may fall back to tomorrow. */
function isMathJaxRequest(url: string): boolean {
    return /mathjax/i.test(new URL(url).pathname);
}

/** A MathJax font: a `.woff` whose path names MathJax — by its folder in the copy, or by its own `MathJax_*.woff` name. */
function isMathJaxFont(path: string): boolean {
    return /\.woff$/i.test(path) && /mathjax/i.test(path);
}

/** A font face, as the page's `document.fonts` reports it. */
interface FaceState {
    family: string;
    style: string;
    weight: string;
    status: 'unloaded' | 'loading' | 'loaded' | 'error';
}

/** MathJax's font faces — the families starting with `MJX` — and where each one stands. */
async function readMathJaxFaces(page: Page): Promise<FaceState[]> {
    return page.evaluate(() => {
        const faces: FaceState[] = [];
        document.fonts.forEach((face) => {
            const family = face.family.replace(/^["']|["']$/g, '');
            if (family.startsWith('MJX')) faces.push({family, style: face.style, weight: face.weight, status: face.status});
        });
        return faces;
    });
}

test.describe('Documentation formulas without internet: MathJax and its fonts from the site’s own copy (M-19)', () => {
    test.afterEach(async ({page}) => {
        await page.unrouteAll({behavior: 'ignoreErrors'});
    });

    for (const target of NESTED_PAGES) {
        test(`${target.label}: ${target.path} draws its formulas in MathJax’s own fonts, every other origin refused`, async ({page, baseURL}) => {
            const origin = laneOrigin(baseURL);
            const refused = await keepOffline(page, origin);
            const bundleAnswers = recordAnswers(page, origin, (path) => path.endsWith(`/${MATHJAX_BUNDLE}`));
            const fontAnswers = recordAnswers(page, origin, isMathJaxFont);
            const typesetErrors = recordTypesetErrors(page);

            const response = await page.goto(target.path, {timeout: PAGE_TIMEOUT_MS});
            expect(response?.status(), `precondition: the lane serves ${target.path} (a 404 is a page that moved: point this spec at another nested page with formulas)`).toBe(200);
            await expect(page.locator('meta[name="generator"]'), `precondition: ${target.path} is a page of the built documentation — an unbuilt site answers «Documentation not generated» (backend/app/main.py): build it, see this file's header`).toHaveAttribute('content', /\bmkdocs-/);
            const formulas = page.locator('.arithmatex');
            await expect(formulas, `precondition: ${target.path} has formulas, or every assertion below would pass on nothing`).not.toHaveCount(0);
            const formulaCount = await formulas.count();

            await expect
                .poll(() => [...bundleAnswers], {
                    message: 'the loader asked the lane for the copy at the site’s root and got 200 — a 404 under the page’s own folder is M-19 back (or a site built before the fix: M-21), a 404 at the root is a copy the site does not have',
                    timeout: MATH_TIMEOUT_MS,
                })
                .toContain(`200 ${LOCAL_MATHJAX_PATH}`);

            const drawn = formulas.locator('mjx-container');
            await expect(drawn.first(), 'MathJax drew the formulas: one is on screen').toBeVisible({timeout: MATH_TIMEOUT_MS});
            await expect.poll(() => drawn.count(), {message: `MathJax drew every formula: at least ${formulaCount} mjx-container inside the ${formulaCount} formulas`, timeout: MATH_TIMEOUT_MS}).toBeGreaterThanOrEqual(formulaCount);

            // The fonts settle first, so that what follows reads a finished state: every font the layout asked for has its answer.
            await expect.poll(() => page.evaluate(async () => (await document.fonts.ready).status), {message: 'the page’s fonts are ready: document.fonts.ready', timeout: FONT_TIMEOUT_MS}).toBe('loaded');
            await expect.poll(async () => (await readMathJaxFaces(page)).filter((face) => face.status === 'loading'), {message: 'no MJX face is still loading', timeout: FONT_TIMEOUT_MS}).toEqual([]);

            expect(await canReach(page, OFFLINE_PROBE_URL), 'positive control: from this page jsDelivr is out of reach').toBe(false);
            expect(refused, 'positive control: the refusal is this spec’s, and it is recorded').toContain(OFFLINE_PROBE_URL);
            expect(refused.filter(isMathJaxRequest), 'MathJax, its bundle or a font, was never asked of another origin: the loader did not fall back to jsDelivr').toEqual([]);

            await expect.poll(() => fontAnswers.length, {message: 'MathJax asked the lane for its fonts', timeout: FONT_TIMEOUT_MS}).toBeGreaterThan(0);
            expect(
                fontAnswers.filter((answer) => !answer.startsWith(`200 ${LOCAL_FONT_DIR}`)),
                `every MathJax font the lane answered is a 200 under ${LOCAL_FONT_DIR} — a 404 there is a font the site does not have: ./dev.py cache js, then ./dev.py mkdocs build`,
            ).toEqual([]);

            const faces = await readMathJaxFaces(page);
            expect(faces, 'MathJax drew in its own fonts: at least one MJX face loaded').toContainEqual(expect.objectContaining({status: 'loaded'}));
            expect(
                faces.filter((face) => face.status === 'error'),
                'no MJX face ended in error: a font that did not arrive, or a body that is not a font',
            ).toEqual([]);

            expect(typesetErrors, 'no page error names typesetPromise: mathjax.js calls it only once MathJax has loaded').toEqual([]);
        });
    }
});
