/**
 * Documentation diagrams, full screen with zoom — H6-4.
 *
 * A click (or Enter, or Space) on a Mermaid diagram of the documentation opens it full screen: the wheel or a pinch
 * zooms around the pointer, a drag pans, a double click or `0` fits it to the screen, `+` and `-` zoom, Esc or a click
 * outside the diagram closes it, and the focus goes back to the diagram. The code is
 * `mkdocs_src/docs/javascripts/diagram-zoom.js` and `stylesheets/diagram-zoom.css`, written in `<head>` by
 * `overrides/main.html` ahead of Material's bundle, on the pages that have a diagram (not by `extra_javascript`).
 *
 * Material for MkDocs draws each diagram into a CLOSED shadow root of its `div.mermaid`, where no script reaches the
 * SVG. The script replaces `Element.prototype.attachShadow` so those roots are open: this spec does NOT do that for
 * itself — the siblings do, with an init script, to read the SVG; here the patch is the subject (test a), and every
 * other test reads the page as the user's browser gets it.
 *
 * What is pinned, on an English flowchart page, an English page with a sequence diagram, and an Italian page:
 *
 *   a. the patch works: `div.mermaid` has a `shadowRoot` after load;
 *   b. every diagram is reachable by keyboard and says what a click does: `tabindex=0`, `role=button`, a non-empty
 *      `aria-label` and `title`, in the language of `<html lang>` (English on an English page, Italian on an Italian one);
 *   c. a click opens the overlay (`role=dialog`) with the SVG in the stage, for a flowchart and for a sequence diagram;
 *   d. the wheel zooms the stage around the pointer (the point under it stays still), `+` and `-` zoom, `0` and a double
 *      click restore the fitted scale;
 *   e. a drag pans and does not close; a plain click on the diagram does not close; a click on the backdrop does;
 *   f. Esc closes and the focus is back on the diagram;
 *   g. keyboard: Enter or Space on the focused diagram opens it, Tab and Shift+Tab stay on the overlay's four buttons
 *      (wrapping), the close button closes;
 *   h. light and dark: the overlay opens in both, the stage takes the page's `--md-default-bg-color` of that scheme, and
 *      the diagram still opens after Material's palette toggle re-draws it (the patch holds);
 *   i. every test ends clean: no console error, no page error, no failed request to the lane, and every request to
 *      another origin was refused and is recorded, expected to be only what the list below tolerates.
 *
 * Selectors: `.mermaid`, `.dz-overlay`, `.dz-viewport`, `.dz-stage`, `[data-dz=…]`, `role=dialog`, and the SVG Mermaid
 * draws are not styling, they are the contract under test — the class `mkdocs.yml` gives the custom fence, and the
 * names `diagram-zoom.js` writes. The documentation carries no data-testid. The text of a label is asserted only in
 * test b, where the language of the label IS the subject. The scale and the translation are read from the stage's
 * computed `transform` matrix.
 *
 * Waiting: on conditions — Playwright's retrying assertions and `expect.poll` on a number — never on the clock.
 * Public and read-only: the documentation needs no sign-in and nothing is written; the one state a test changes is its
 * own browser context's routes and the palette stored in its own context.
 *
 * Needs: the docs site built with the script and the stylesheet in (`./dev.py mkdocs build`): the lane's server rebuilds
 * a site older than a `.md`, not one older than a script, a template or a stylesheet alone. A site without them is a red
 * precondition here (test a fails at the shadow root), never a skip.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';

/** The site's root, as the backend serves it. */
const SITE_ROOT = '/mkdocs/';
/** English page with a flowchart. */
const FLOWCHART_PATH = `${SITE_ROOT}admin/backup_restore/`;
/** English page with two diagrams (a flowchart and more), used for the count of reachable diagrams. */
const TWO_DIAGRAMS_PATH = `${SITE_ROOT}developer/test-walkthrough/runner_architecture/`;
/** English page with a sequence diagram. */
const SEQUENCE_PATH = `${SITE_ROOT}developer/backend/assets/events/`;
/** Italian page with a diagram. */
const ITALIAN_PATH = `${SITE_ROOT}it/admin/docker_advanced/`;

/** What `diagram-zoom.js` says in each language for the diagram itself (its `TEXTS[lang].diagram`). */
const LABEL_EN = 'Diagram: open full screen, with zoom';
const LABEL_IT = 'Diagramma: apri a schermo intero, con lo zoom';

/** A documentation page with its scripts and styles, on a loaded machine. */
const PAGE_TIMEOUT_MS = 30_000;
/** Mermaid: a ~3 MB bundle fetched, parsed and run, then the diagram laid out — on a loaded machine. */
const DIAGRAM_TIMEOUT_MS = 30_000;
/** Pixels of play when comparing positions that went through a transform. */
const PX_TOLERANCE = 1.5;

test.setTimeout(90_000);

/** The runner's baseURL, as an origin: the only one this spec lets the browser reach. */
function laneOrigin(baseURL: string | undefined): string {
    if (!baseURL) throw new Error('This spec needs the runner-provided baseURL');
    return new URL(baseURL).origin;
}

/** Console errors the page is known to raise and this spec does not judge. Each entry needs its reason. */
const HARMLESS_CONSOLE: {pattern: RegExp; reason: string}[] = [];

/** What a test records from before the navigation, and judges at its end. */
interface Diagnostics {
    /** URLs of the requests to another origin, refused. */
    refused: string[];
    consoleErrors: string[];
    pageErrors: string[];
    /** Requests to the lane that failed or got a 4xx/5xx: `<status> <path>`. */
    laneFailures: string[];
    /** Every answer the lane gave: `<status> <path>`. */
    served: string[];
}

/** Refuses every origin but the lane's, as a machine without internet would, and records what the page does. Armed before the navigation. */
async function watch(page: Page, origin: string): Promise<Diagnostics> {
    const diag: Diagnostics = {refused: [], consoleErrors: [], pageErrors: [], laneFailures: [], served: []};
    await page.route(
        (url) => (url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== origin,
        (route) => {
            diag.refused.push(route.request().url());
            return route.abort('blockedbyclient');
        },
    );
    page.on('console', (message) => {
        if (message.type() !== 'error') return;
        const text = message.text();
        if (HARMLESS_CONSOLE.some((known) => known.pattern.test(text))) return;
        diag.consoleErrors.push(`${text} (${message.location().url})`);
    });
    page.on('pageerror', (error) => diag.pageErrors.push(error.message));
    page.on('response', (response) => {
        const url = new URL(response.url());
        if (url.origin === origin) diag.served.push(`${response.status()} ${url.pathname}`);
        if (url.origin === origin && response.status() >= 400) diag.laneFailures.push(`${response.status()} ${url.pathname}`);
    });
    page.on('requestfailed', (request) => {
        const url = new URL(request.url());
        if (url.origin === origin) diag.laneFailures.push(`failed ${url.pathname}: ${request.failure()?.errorText ?? ''}`);
    });
    return diag;
}

/** Hosts the documentation's own pages ask for (fonts, GitHub, a donation button, the sitemap of the published site), refused here: not this spec's subject. Anything else is. */
const THIRD_PARTY_TOLERATED = /^https:\/\/(fonts\.googleapis\.com|api\.github\.com|cdn\.buymeacoffee\.com|librefolio\.github\.io)\//;

/** What every test must end with (i). */
function expectClean(diag: Diagnostics): void {
    expect(diag.pageErrors, 'no uncaught error on the page').toEqual([]);
    expect(diag.laneFailures, 'no request to the lane failed or was answered 4xx/5xx').toEqual([]);
    // The page's own links to the outside (fonts, GitHub, the donation button, the published sitemap) are refused and each
    // raises a «Failed to load resource: net::ERR_BLOCKED_BY_CLIENT» console error — the refusal's own echo, not a defect of
    // this feature. So: a console error is harmless only if it is that echo for a refused URL; any other one is a failure.
    const echoes = diag.consoleErrors.filter((text) => /net::ERR_BLOCKED_BY_CLIENT/.test(text) && diag.refused.some((url) => text.includes(url)));
    expect(
        diag.consoleErrors.filter((text) => !echoes.includes(text)),
        'no console error on the page but the echo of a refused request',
    ).toEqual([]);
    // The scripts of this feature and of Mermaid come from the site: nothing is asked of a CDN, and the third parties above
    // are the only other origins the page reaches for.
    expect(
        diag.refused.filter((url) => !THIRD_PARTY_TOLERATED.test(url)),
        'the page asked no origin beyond the documentation’s own links (a CDN would be a regression: Mermaid and the zoom are served by the site)',
    ).toEqual([]);
}

let diagnostics: Diagnostics | undefined;

test.describe('Documentation diagrams: full screen with zoom and pan (H6-4)', () => {
    test.afterEach(async ({page}) => {
        // The judgement of (i), for every test, after the test's own steps; skipped when the test failed already.
        const diag = diagnostics;
        diagnostics = undefined;
        await page.unrouteAll({behavior: 'ignoreErrors'});
        if (diag && test.info().status === 'passed') expectClean(diag);
    });

    /** Opens a documentation page, checks it is the built site with at least one drawn diagram, and returns the drawn hosts. */
    async function gotoDocs(page: Page, baseURL: string | undefined, path: string, setup?: () => Promise<void>): Promise<Locator> {
        diagnostics = await watch(page, laneOrigin(baseURL));
        if (setup) await setup();
        const response = await page.goto(path, {timeout: PAGE_TIMEOUT_MS});
        expect(response?.status(), `precondition: the lane serves ${path} (a 404 is a page that moved: point this spec at another page with that diagram)`).toBe(200);
        await expect(page.locator('meta[name="generator"]'), `precondition: ${path} is a page of the built documentation — an unbuilt site answers «Documentation not generated»`).toHaveAttribute('content', /\bmkdocs-/);
        const hosts = page.locator('div.mermaid');
        await expect(hosts, `precondition: ${path} has a Mermaid diagram, or every assertion below would pass on nothing`).not.toHaveCount(0);
        await expect(page.locator('pre.mermaid'), 'precondition: Material drew every diagram, none is left as code').toHaveCount(0, {timeout: DIAGRAM_TIMEOUT_MS});
        // The feature's own files come from the lane, with 200 (and, by expectClean, nothing was asked of another origin for them).
        await expect
            .poll(() => [...diagnostics!.served], {
                message: `the lane served the zoom script and its stylesheet with 200 (an empty list: overrides/main.html does not write them, or the site was built before them: ./dev.py mkdocs build)`,
                timeout: PAGE_TIMEOUT_MS,
            })
            .toEqual(expect.arrayContaining([`200 ${SITE_ROOT}javascripts/diagram-zoom.js`, `200 ${SITE_ROOT}stylesheets/diagram-zoom.css`]));
        return hosts;
    }

    /** The diagram host of a kind (`flowchart`, `sequence`): Mermaid names it in `aria-roledescription`, Playwright looks into the open shadow root. */
    function hostOf(hosts: Locator, kind: 'flowchart' | 'sequence'): Locator {
        const selector = kind === 'flowchart' ? 'svg[aria-roledescription^="flowchart"]' : 'svg[aria-roledescription="sequence"]';
        return hosts.filter({has: hosts.page().locator(selector)}).first();
    }

    /** The scale and translation of the stage, from its computed transform. */
    async function view(page: Page): Promise<{k: number; x: number; y: number}> {
        return page.locator('.dz-stage').evaluate((stage) => {
            const m = new DOMMatrixReadOnly(getComputedStyle(stage).transform);
            return {k: m.a, x: m.e, y: m.f};
        });
    }

    /** Opens a diagram with a click and waits for the overlay with its drawing; returns the fitted scale. */
    async function openByClick(page: Page, host: Locator): Promise<number> {
        await expect(host.locator('svg').first(), 'the diagram is drawn').toBeVisible({timeout: DIAGRAM_TIMEOUT_MS});
        await expect(host, 'the script made the diagram clickable').toHaveAttribute('tabindex', '0');
        await host.click();
        return opened(page);
    }

    /** The overlay is open, with a dialog role and the SVG with nodes in the stage; returns the fitted scale. */
    async function opened(page: Page): Promise<number> {
        const overlay = page.locator('.dz-overlay');
        await expect(overlay, 'the overlay is open').toBeVisible();
        // The search of the header is a dialog too: the overlay is the one that is also `.dz-overlay`.
        await expect(overlay.and(page.getByRole('dialog')), 'the overlay is a dialog').toBeVisible();
        await expect(overlay).toHaveAttribute('aria-modal', 'true');
        const svg = page.locator('.dz-stage svg');
        await expect(svg, 'the diagram is in the stage').toBeVisible();
        await expect(svg.locator('g').first(), 'the SVG holds the drawing, not an empty shell').toBeAttached();
        await expect(svg.locator('[class*="node"], [class*="actor"]').first(), 'the drawing has nodes').toBeAttached();
        const {k} = await view(page);
        expect(k, 'the diagram is fitted to the screen').toBeGreaterThan(0);
        return k;
    }

    // -------------------------------------------------------------------------------------------------------------
    // a, b
    // -------------------------------------------------------------------------------------------------------------

    test('a. the shadow root of a diagram is open: the patch of attachShadow works', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, FLOWCHART_PATH);
        await expect.poll(() => hosts.first().evaluate((host) => host.shadowRoot !== null), {message: 'Material draws into a shadow root that diagram-zoom.js made open (it is closed otherwise: null)', timeout: DIAGRAM_TIMEOUT_MS}).toBe(true);
        await expect.poll(() => hosts.first().evaluate((host) => host.shadowRoot?.querySelector('svg') !== null), {timeout: DIAGRAM_TIMEOUT_MS}).toBe(true);
    });

    test('b. every diagram is a focusable button with a label, in the language of the page (English)', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, TWO_DIAGRAMS_PATH);
        await expect(hosts.first().locator('svg').first()).toBeVisible({timeout: DIAGRAM_TIMEOUT_MS});
        await expect(page.locator('html')).toHaveAttribute('lang', 'en');
        // Every diagram, not the first: the count is the page's own.
        await expect
            .poll(
                () =>
                    hosts.evaluateAll((all) =>
                        all.map((host) => ({
                            tabindex: host.getAttribute('tabindex'),
                            role: host.getAttribute('role'),
                            label: host.getAttribute('aria-label') ?? '',
                            title: host.getAttribute('title') ?? '',
                            drawn: host.shadowRoot?.querySelector('svg') != null,
                        })),
                    ),
                {message: 'every diagram of the page is drawn, focusable, a button, and has a label and a title', timeout: DIAGRAM_TIMEOUT_MS},
            )
            .toEqual(expect.arrayContaining([expect.objectContaining({tabindex: '0', role: 'button', label: LABEL_EN, drawn: true})]));
        const all = await hosts.evaluateAll((list) => list.map((host) => ({tabindex: host.getAttribute('tabindex'), role: host.getAttribute('role'), label: host.getAttribute('aria-label') ?? '', title: host.getAttribute('title') ?? ''})));
        expect(all.length, 'the page has two diagrams or more').toBeGreaterThanOrEqual(2);
        for (const host of all) {
            expect(host.tabindex).toBe('0');
            expect(host.role).toBe('button');
            expect(host.label.length, 'a label').toBeGreaterThan(0);
            expect(host.title.length, 'a title').toBeGreaterThan(0);
            expect(host.label, 'an English page says it in English').toBe(LABEL_EN);
        }
    });

    test('b. the label follows the page’s language (Italian)', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, ITALIAN_PATH);
        await expect(page.locator('html'), 'precondition: the Italian page says so in <html lang>').toHaveAttribute('lang', /^it/);
        await expect(hosts.first().locator('svg').first()).toBeVisible({timeout: DIAGRAM_TIMEOUT_MS});
        await expect(hosts.first()).toHaveAttribute('aria-label', LABEL_IT);
        expect(LABEL_IT).not.toBe(LABEL_EN);
        await expect(hosts.first()).toHaveAttribute('role', 'button');
        await expect(hosts.first()).toHaveAttribute('tabindex', '0');
        await expect(hosts.first()).not.toHaveAttribute('title', '');
    });

    // -------------------------------------------------------------------------------------------------------------
    // c
    // -------------------------------------------------------------------------------------------------------------

    test('c. a click on a flowchart opens it full screen', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, FLOWCHART_PATH);
        const host = hostOf(hosts, 'flowchart');
        await openByClick(page, host);
        await expect(page.locator('.dz-stage svg[aria-roledescription^="flowchart"]')).toBeVisible();
        await expect(page.locator('.dz-bar [data-dz]'), 'the four controls').toHaveCount(4);
    });

    test('c. a click on a sequence diagram opens it full screen', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, SEQUENCE_PATH);
        const host = hostOf(hosts, 'sequence');
        await expect(host, 'precondition: the page has a sequence diagram').toBeAttached({timeout: DIAGRAM_TIMEOUT_MS});
        await openByClick(page, host);
        await expect(page.locator('.dz-stage svg[aria-roledescription="sequence"]')).toBeVisible();
    });

    // -------------------------------------------------------------------------------------------------------------
    // d
    // -------------------------------------------------------------------------------------------------------------

    test('d. the wheel zooms around the pointer, + and - zoom, 0 and a double click fit', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, FLOWCHART_PATH);
        const fitK = await openByClick(page, hostOf(hosts, 'flowchart'));
        const stage = page.locator('.dz-stage');

        // A pointer that is not the centre of the screen, on the diagram: a quarter in from the left, a third down.
        const box = await stage.boundingBox();
        if (!box) throw new Error('the stage has no box');
        const px = box.x + box.width * 0.25;
        const py = box.y + box.height * 0.33;
        const before = await view(page);
        const underPointer = {x: (px - before.x) / before.k, y: (py - before.y) / before.k}; // in the diagram's own units

        await page.mouse.move(px, py);
        await page.mouse.wheel(0, -400);
        await expect.poll(async () => (await view(page)).k, {message: 'the wheel up zooms in'}).toBeGreaterThan(before.k * 1.3);
        const zoomed = await view(page);
        expect(Math.abs(zoomed.x + underPointer.x * zoomed.k - px), 'the point under the pointer stays still (x)').toBeLessThan(PX_TOLERANCE);
        expect(Math.abs(zoomed.y + underPointer.y * zoomed.k - py), 'the point under the pointer stays still (y)').toBeLessThan(PX_TOLERANCE);

        await page.mouse.wheel(0, 400);
        await expect.poll(async () => (await view(page)).k, {message: 'the wheel down zooms out'}).toBeLessThan(zoomed.k * 0.8);
        const back = await view(page);
        expect(Math.abs(back.x + underPointer.x * back.k - px), 'and still around the pointer (x)').toBeLessThan(PX_TOLERANCE);
        expect(Math.abs(back.y + underPointer.y * back.k - py), 'and still around the pointer (y)').toBeLessThan(PX_TOLERANCE);

        // 0 fits.
        await page.keyboard.press('0');
        await expect.poll(async () => (await view(page)).k, {message: '0 fits'}).toBeCloseTo(fitK, 5);

        // + and - zoom, around the centre of the screen.
        await page.keyboard.press('+');
        await expect.poll(async () => (await view(page)).k, {message: '+ zooms in'}).toBeGreaterThan(fitK * 1.1);
        const plus = (await view(page)).k;
        await page.keyboard.press('-');
        await expect.poll(async () => (await view(page)).k, {message: '- zooms out'}).toBeLessThan(plus * 0.9);
        await page.keyboard.press('-');
        await expect.poll(async () => (await view(page)).k, {message: '- again, below the fitted scale'}).toBeLessThan(fitK * 0.9);

        // A double click fits, after a zoom.
        await page.keyboard.press('+');
        await page.keyboard.press('+');
        await expect.poll(async () => (await view(page)).k).toBeGreaterThan(fitK * 1.1);
        const centre = page.viewportSize();
        if (!centre) throw new Error('no viewport size');
        await page.mouse.dblclick(centre.width / 2, centre.height / 2);
        await expect.poll(async () => (await view(page)).k, {message: 'a double click fits'}).toBeCloseTo(fitK, 5);
        await expect(page.locator('.dz-overlay'), 'neither the zoom nor the double click closed it').toBeVisible();
    });

    // -------------------------------------------------------------------------------------------------------------
    // e
    // -------------------------------------------------------------------------------------------------------------

    test('e. a drag pans and does not close; a click on the diagram does not close; a click on the backdrop does', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, FLOWCHART_PATH);
        await openByClick(page, hostOf(hosts, 'flowchart'));
        const overlay = page.locator('.dz-overlay');
        const stage = page.locator('.dz-stage');
        const box = await stage.boundingBox();
        if (!box) throw new Error('the stage has no box');
        const cx = box.x + box.width / 2;
        const cy = box.y + box.height / 2;

        const before = await view(page);
        await page.mouse.move(cx, cy);
        await page.mouse.down();
        await page.mouse.move(cx + 60, cy + 30, {steps: 6});
        await page.mouse.move(cx + 90, cy + 50, {steps: 6});
        await page.mouse.up();
        await expect.poll(async () => (await view(page)).x, {message: 'the drag moved the stage to the right'}).toBeCloseTo(before.x + 90, 0);
        const dragged = await view(page);
        expect(dragged.y, 'and down').toBeCloseTo(before.y + 50, 0);
        expect(dragged.k, 'a drag does not zoom').toBeCloseTo(before.k, 8);
        await expect(overlay, 'the drag did not close it').toBeVisible();

        // A plain click on the diagram (inside the stage) does not close it.
        const moved = await stage.boundingBox();
        if (!moved) throw new Error('the stage has no box');
        await page.mouse.click(moved.x + moved.width / 2, moved.y + moved.height / 2);
        await expect(overlay, 'a click on the diagram keeps it open').toBeVisible();
        expect((await view(page)).x, 'and does not move it').toBeCloseTo(dragged.x, 8);

        // Back to the fitted view, so the corner of the screen is the backdrop.
        await page.keyboard.press('0');
        await expect.poll(async () => (await view(page)).x).toBeCloseTo(before.x, 5);
        const fitted = await stage.boundingBox();
        if (!fitted) throw new Error('the stage has no box');
        expect(fitted.x, 'precondition: the corner point is outside the stage').toBeGreaterThan(8);
        await page.mouse.click(4, 4);
        await expect(overlay, 'a click on the backdrop closes it').toBeHidden();
    });

    // -------------------------------------------------------------------------------------------------------------
    // f
    // -------------------------------------------------------------------------------------------------------------

    test('f. Esc closes and the focus is back on the diagram', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, FLOWCHART_PATH);
        const host = hostOf(hosts, 'flowchart');
        await openByClick(page, host);
        await page.keyboard.press('Escape');
        await expect(page.locator('.dz-overlay')).toBeHidden();
        await expect(host, 'the focus is back on the diagram that was opened').toBeFocused();
        expect(await page.evaluate(() => document.activeElement?.matches('div.mermaid') ?? false), 'and it is a diagram host').toBe(true);
        await expect(page.locator('.dz-stage svg'), 'the stage is emptied').toHaveCount(0);
    });

    // -------------------------------------------------------------------------------------------------------------
    // g
    // -------------------------------------------------------------------------------------------------------------

    test('g. keyboard: Enter and Space open, Tab stays on the four buttons and wraps, the close button closes', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, FLOWCHART_PATH);
        const host = hostOf(hosts, 'flowchart');
        await expect(host.locator('svg').first()).toBeVisible({timeout: DIAGRAM_TIMEOUT_MS});
        await expect(host).toHaveAttribute('tabindex', '0');
        const active = () => page.evaluate(() => document.activeElement?.getAttribute('data-dz') ?? `outside:${document.activeElement?.tagName}`);

        await host.focus();
        await page.keyboard.press('Enter');
        await opened(page);
        await expect.poll(active, {message: 'the focus goes to the close button'}).toBe('close');

        // Tab walks the four buttons and wraps: close → in → out → fit → close; never to the page behind.
        for (const next of ['in', 'out', 'fit', 'close']) {
            await page.keyboard.press('Tab');
            await expect.poll(active, {message: `Tab goes to «${next}»`}).toBe(next);
        }
        // Shift+Tab wraps backwards: close → fit → out → in → close.
        for (const next of ['fit', 'out', 'in', 'close']) {
            await page.keyboard.press('Shift+Tab');
            await expect.poll(active, {message: `Shift+Tab goes to «${next}»`}).toBe(next);
        }
        expect(await active()).not.toMatch(/^outside:/);

        // The buttons work from the keyboard: «in» zooms, «fit» fits.
        const fitK = (await view(page)).k;
        await page.keyboard.press('Tab'); // in
        await expect.poll(active).toBe('in');
        await page.keyboard.press('Enter');
        await expect.poll(async () => (await view(page)).k, {message: 'the zoom-in button zooms in'}).toBeGreaterThan(fitK * 1.1);
        await page.keyboard.press('Tab'); // out
        await page.keyboard.press('Tab'); // fit
        await expect.poll(active).toBe('fit');
        await page.keyboard.press('Enter');
        await expect.poll(async () => (await view(page)).k, {message: 'the fit button fits'}).toBeCloseTo(fitK, 5);
        await expect(page.locator('.dz-overlay'), 'none of them closed it').toBeVisible();

        // The close button closes, and the focus returns to the diagram.
        await page.locator('[data-dz="close"]').click();
        await expect(page.locator('.dz-overlay')).toBeHidden();
        await expect(host).toBeFocused();

        // Space opens too.
        await page.keyboard.press('Space');
        await opened(page);
        await page.keyboard.press('Escape');
        await expect(page.locator('.dz-overlay')).toBeHidden();
        await expect(host).toBeFocused();
    });

    // -------------------------------------------------------------------------------------------------------------
    // h
    // -------------------------------------------------------------------------------------------------------------

    /** The colour `--md-default-bg-color` resolves to on the body, as the browser computes a background-color. */
    async function pageBackground(page: Page): Promise<string> {
        return page.evaluate(() => {
            const probe = document.createElement('div');
            probe.style.backgroundColor = 'var(--md-default-bg-color)';
            document.body.appendChild(probe);
            const colour = getComputedStyle(probe).backgroundColor;
            probe.remove();
            return colour;
        });
    }

    /** Opens the first flowchart, checks the overlay against the page's scheme, closes it. Returns the stage's background. */
    async function openAndCheckScheme(page: Page, scheme: 'default' | 'slate'): Promise<string> {
        await expect(page.locator('body'), 'the page is in that scheme').toHaveAttribute('data-md-color-scheme', scheme);
        // Re-read the host: Material draws the diagram again when the palette changes.
        const host = hostOf(page.locator('div.mermaid'), 'flowchart');
        await openByClick(page, host);
        const stage = page.locator('.dz-stage');
        await expect(stage).toBeVisible();
        const expected = await pageBackground(page);
        await expect.poll(() => stage.evaluate((el) => getComputedStyle(el).backgroundColor), {message: `the stage takes the page's --md-default-bg-color of the «${scheme}» scheme`}).toBe(expected);
        await expect(page.locator('.dz-stage svg')).toBeVisible();
        await expect(page.locator('.dz-bar [data-dz="close"]')).toBeVisible();
        await page.keyboard.press('Escape');
        await expect(page.locator('.dz-overlay')).toBeHidden();
        return expected;
    }

    /** Clicks Material's palette toggle (the one label that is shown: it switches to the other scheme). */
    async function togglePalette(page: Page, to: 'default' | 'slate'): Promise<void> {
        const toggle = page.locator('form[data-md-component="palette"] label.md-header__button').filter({visible: true});
        await expect(toggle, 'the header offers exactly one palette toggle').toHaveCount(1);
        await toggle.click();
        await expect(page.locator('body')).toHaveAttribute('data-md-color-scheme', to);
        // The diagram is drawn again in the new scheme, with the script's attributes.
        const host = hostOf(page.locator('div.mermaid'), 'flowchart');
        await expect(host.locator('svg').first()).toBeVisible({timeout: DIAGRAM_TIMEOUT_MS});
        await expect(host).toHaveAttribute('tabindex', '0');
    }

    test('h. light then dark: the overlay opens in both and the diagram still opens after the palette toggle', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, FLOWCHART_PATH, () => page.emulateMedia({colorScheme: 'light'}));
        await expect(hosts.first().locator('svg').first()).toBeVisible({timeout: DIAGRAM_TIMEOUT_MS});
        const light = await openAndCheckScheme(page, 'default');
        await togglePalette(page, 'slate');
        const dark = await openAndCheckScheme(page, 'slate');
        expect(dark, 'the two schemes have two backgrounds: the stage follows the theme, it is not a constant').not.toBe(light);
    });

    test('h. dark then light: the same, the other way round', async ({page, baseURL}) => {
        const hosts = await gotoDocs(page, baseURL, FLOWCHART_PATH, () => page.emulateMedia({colorScheme: 'dark'}));
        await expect(hosts.first().locator('svg').first()).toBeVisible({timeout: DIAGRAM_TIMEOUT_MS});
        const dark = await openAndCheckScheme(page, 'slate');
        await togglePalette(page, 'default');
        const light = await openAndCheckScheme(page, 'default');
        expect(light).not.toBe(dark);
    });
});
