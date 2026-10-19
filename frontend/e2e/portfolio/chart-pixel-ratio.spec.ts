import type {CDPSession} from '@playwright/test';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

/**
 * The Dashboard's charts at the density of the screen (workstream DV): blurred no more after the window moves to a
 * denser screen, or the browser zooms.
 *
 * ## What it protects
 *
 * ECharts draws on canvases whose backing store is their CSS size times a density. zrender reads that density once,
 * when its module loads, and fixes it for a chart at `init`; no public API changes it. So a tab loaded on a 1× screen
 * drew every chart at 1× — the ones opened later too — until a reload. `chartPixelRatio.ts` gives every chart
 * `echarts.init(el, CHART_INIT_THEME, chartInitOptions(el))`: born at the density of its moment, and followed — one
 * `matchMedia` resolution query, re-armed at each change, brings every live chart to the new density in place.
 * `chartPixelRatio.test.ts` pins the mechanism in jsdom on the real zrender; this spec checks it in Chromium.
 *
 * ## How
 *
 * - TEST_USER's Dashboard, overview tab, with the allocation panel on its «now» view and its «type» dimension (both
 *   persist per user in this context's storage: chosen, never assumed). Its charts are the growth chart and the
 *   allocation pie — and the allocation history when it has drawn: every one created through `chartInitOptions`.
 *   `PriceChartFull` and `CandlestickChart`, still exempt from the rule (`PIXEL_RATIO_PENDING`, `chartFlagFont.test.ts`),
 *   live on the asset and FX pages only: the hosts are read under `growth-chart` and `allocation-panel`, nowhere else.
 * - A host is an ECharts root that has drawn: `[_echarts_instance_]` (emptied on dispose) with `data-chart-ready="true"`.
 *   Each canvas is measured as `canvas.width / its CSS width` (and the same for the height): 1 at the desktop project's
 *   deviceScaleFactor 1, asserted first so that the 2 after the change means something.
 * - The density changes at runtime through the test's own CDP session: `Emulation.setDeviceMetricsOverride`, the same
 *   viewport and screen, deviceScaleFactor 2 — what moving the window to a Retina screen does to the page. No reload:
 *   the page keeps the zrender it loaded at 1.
 * - The page hears a change of density only through a `resolution` media query's `change`, which the browser fires on a
 *   query whose match flipped, in the «update the rendering» step. A probe of the test's own, armed on the density of
 *   the moment before each change, says whether Chromium fired it under the override: read after two rendering updates
 *   each time (layout forced, then two animation frames), for up to 5 s. The second test does not depend on it.
 * - In place: the same instance id on every host and the same canvas nodes (remembered in the page before the change).
 *   `data-chart-renders` is recorded, not asserted: a change of density may move sub-pixel layout, and a chart's
 *   ResizeObserver then redraws it through `resize()` — the product's own path, not this one. That nothing is drawn
 *   again from the options is `chartPixelRatio.test.ts`'s (no `setOption`, `resize` or `clear` on the change).
 *
 * ## The bridge: a change Chromium does not fire
 *
 * Measured in the slot of 19/10 (Playwright 1.61's Chromium): under `Emulation.setDeviceMetricsOverride`,
 * `window.devicePixelRatio` reached 2, and the probe's `(resolution: 1dppx)` heard no `change` in 10 s. When the probe
 * hears nothing, the first test supplies that event itself, in the open:
 *
 * - an init script, installed before the test's first navigation, wraps `window.matchMedia`: every `MediaQueryList`
 *   whose media names `resolution` is recorded in the page (`__lfResolutionQueries`), the real object returned
 *   unchanged. The probe creates its queries through the native `matchMedia`: none of them is ever recorded;
 * - the test dispatches `change` — a `MediaQueryListEvent` with the list's own `media` and `matches`, what the browser
 *   sends — on the latest query the app created, provided it still names the density before the change: the one the
 *   app's watcher armed. If the app has armed another since, Chromium's own event came after the probe's 5 s and nothing
 *   is dispatched; a native event arriving after a dispatch finds the old query without its listener (the app re-armed)
 *   and the charts already at the density: it changes nothing;
 * - a `density-change` annotation, also printed, says for each direction which it was: `fired by Chromium`, or
 *   `dispatched by the test: Chromium fired no resolution change under Emulation.setDeviceMetricsOverride`. A fact
 *   about the harness, never a failure.
 *
 * Why it is honest: firing that event is the browser's job — MDN's «Monitoring screen resolution or zoom level
 * changes» (`Window.devicePixelRatio`) documents this very query as how a page learns that its density changed — and
 * the test leaves it to the browser whenever the browser does it. Everything else is real: the density change through
 * CDP (`window.devicePixelRatio` is the new one before anything is dispatched), the charts, zrender, the module's
 * handler and its re-arming on the new density, which is asserted, so the way back is delivered on the query the app
 * armed itself. Every failure after the delivery is the product's, and reads so: «the page received the change of
 * density (fired by Chromium | dispatched by the test), yet …».
 *
 * ## Why it is red without the fix
 *
 * Without `chartInitOptions` the charts are created with `{renderer: 'canvas'}`: at the density zrender read when the
 * page loaded (1) whatever the screen's at their creation — the sector pie opened after the change is born at 1× — and
 * nothing brings the charts on screen to the new density: they stay at 1×. Nothing arms a resolution query either, so
 * the first test fails before any change, on the app's watcher: there is nothing to fire, or to dispatch, a change on.
 *
 * Read-only: TEST_USER's seeded data, nothing written; the override is cleared at the end of each test.
 */

// ============================================================================
// Constants and shapes
// ============================================================================

/** An ECharts root that has drawn: ECharts marks it `_echarts_instance_` (emptied on dispose), chartReady adds the flag. */
const HOSTS = '[_echarts_instance_]:not([_echarts_instance_=""])[data-chart-ready="true"]';

/** The allocation pie: the drawn host of the allocation panel that is not its history chart. */
const PIE = `${HOSTS}:not([data-testid="allocation-history-chart"])`;

/** The density the screen moves to: a Retina screen. */
const DENSE = 2;

/** How long the probe listens for Chromium's own `change` before the bridge dispatches it. */
const PROBE_MS = 5_000;

/** The `density-change` annotation when the test dispatched the change. */
const DISPATCHED = 'dispatched by the test: Chromium fired no resolution change under Emulation.setDeviceMetricsOverride';

/** How the page received a change of density. */
type Delivery = 'fired by Chromium' | 'dispatched by the test';

/** The page's screen, kept as it is when the density changes. */
interface Screen {
    width: number;
    height: number;
}

/** What this spec keeps on the page's `window`. */
interface DensityWindow {
    /** Every `MediaQueryList` the page created whose media names `resolution`, oldest first: the init script's record. */
    __lfResolutionQueries?: MediaQueryList[];
    /** The native `window.matchMedia`, kept by the init script: the probe creates its queries through it. */
    __lfNativeMatchMedia?: (query: string) => MediaQueryList;
    /** The probe's query and its listener. */
    __lfDensityProbe?: {query: MediaQueryList; heard: () => void};
    /** The `change` events the probe heard since it was armed. */
    __lfDensityChanges?: number;
}

/** A canvas as the page lays it out: its backing store, its CSS box, and whether it is the node remembered for its host. */
interface CanvasReading {
    width: number;
    height: number;
    cssWidth: number;
    cssHeight: number;
    same: boolean | null;
}

/** A drawn host: its instance id, its renders counter, and its laid-out canvases. */
interface HostReading {
    id: string;
    renders: string | null;
    canvases: CanvasReading[];
}

// ============================================================================
// Reading the charts
// ============================================================================

/** The Dashboard's chart hosts that have drawn: the growth chart's, then the allocation panel's. */
function chartHosts(page: Page): Locator[] {
    return [page.getByTestId('growth-chart').locator(HOSTS), page.getByTestId('allocation-panel').locator(HOSTS)];
}

/** Every host of `hosts`, read in the page: no canvas without a CSS box is measured (nothing to divide by). */
async function readHosts(hosts: Locator[]): Promise<HostReading[]> {
    const readings = await Promise.all(
        hosts.map((locator) =>
            locator.evaluateAll((elements) => {
                const memory = (window as unknown as {__lfDensityCanvases?: Map<string, HTMLCanvasElement[]>}).__lfDensityCanvases;
                return elements.map((host) => {
                    const id = host.getAttribute('_echarts_instance_') ?? '';
                    const known = memory?.get(id) ?? null;
                    const canvases = Array.from(host.querySelectorAll('canvas'));
                    return {
                        id,
                        renders: host.getAttribute('data-chart-renders'),
                        canvases: canvases
                            .map((canvas, index) => {
                                const box = canvas.getBoundingClientRect();
                                return {width: canvas.width, height: canvas.height, cssWidth: box.width, cssHeight: box.height, same: known ? known[index] === canvas && known.length === canvases.length : null};
                            })
                            .filter((canvas) => canvas.cssWidth > 0 && canvas.cssHeight > 0),
                    };
                });
            }),
        ),
    );
    return readings.flat();
}

/** Remembers, in the page, the canvas nodes of every host of `hosts`: what «the same canvases» is measured against. */
async function rememberCanvases(hosts: Locator[]): Promise<void> {
    for (const locator of hosts) {
        await locator.evaluateAll((elements) => {
            const holder = window as unknown as {__lfDensityCanvases?: Map<string, HTMLCanvasElement[]>};
            const memory = (holder.__lfDensityCanvases ??= new Map());
            for (const host of elements) memory.set(host.getAttribute('_echarts_instance_') ?? '', Array.from(host.querySelectorAll('canvas')));
        });
    }
}

const round = (value: number): number => Math.round(value * 100) / 100;

/** A canvas's density, as `width×height` ratios of its backing store to its CSS box. */
const densityOf = (canvas: CanvasReading): string => `${round(canvas.width / canvas.cssWidth)}×${round(canvas.height / canvas.cssHeight)}`;

/** Every host as `id: the density of each canvas`, e.g. `ec_12: 2×2, 2×2`. */
const densities = (hosts: HostReading[]): string[] => hosts.map((host) => `${host.id}: ${host.canvases.map(densityOf).join(', ')}`);

/** The same hosts with every canvas at `ratio`. */
const densitiesAt = (hosts: HostReading[], ratio: number): string[] => hosts.map((host) => `${host.id}: ${host.canvases.map(() => `${ratio}×${ratio}`).join(', ')}`);

/** The hosts of `readings` whose ids are `ids`, in the order of `ids`: a host gone (created again under a new id) is missing. */
const byIds = (readings: HostReading[], ids: string[]): HostReading[] => ids.flatMap((id) => readings.filter((host) => host.id === id));

/** Every host as `id: n canvas(es), the same nodes | new nodes`: the same nodes as those remembered before the change. */
const nodesOf = (hosts: HostReading[]): string[] => hosts.map((host) => `${host.id}: ${host.canvases.length} canvas(es), ${host.canvases.every((canvas) => canvas.same === true) ? 'the same nodes' : 'new nodes'}`);

/** The same hosts, each still on the canvas nodes remembered before the change. */
const sameNodesAs = (hosts: HostReading[]): string[] => hosts.map((host) => `${host.id}: ${host.canvases.length} canvas(es), the same nodes`);

// ============================================================================
// The page and the density
// ============================================================================

/** TEST_USER's Dashboard, overview tab, settled; the allocation panel on «now» × «type»; the growth chart and the pie drawn. */
async function openOverview(page: Page): Promise<void> {
    await login(page, TEST_USER);
    await page.goto('/dashboard');
    const dashboard = page.getByTestId('dashboard-page');
    await expect(dashboard).toBeVisible({timeout: 15_000});
    await expect(dashboard).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
    await expect(page.getByTestId('dashboard-overview-tab')).toBeVisible();

    const now = page.getByTestId('allocation-view-now');
    await now.click();
    await expect(now).toHaveAttribute('aria-pressed', 'true');
    const type = page.getByTestId('allocation-tab-type');
    await type.click();
    await expect(type).toHaveAttribute('aria-pressed', 'true');

    await expect(page.getByTestId('growth-chart').locator(HOSTS), 'precondition: the growth chart drew').not.toHaveCount(0, {timeout: 20_000});
    await expect(page.getByTestId('allocation-panel').locator(PIE), 'precondition: one allocation pie, by type, drew').toHaveCount(1, {timeout: 20_000});
}

/** The page's screen, as Playwright emulates it: kept as it is when the density changes. */
async function screenOf(page: Page): Promise<Screen> {
    return page.evaluate(() => ({width: window.screen.width, height: window.screen.height}));
}

/** Chromium at `deviceScaleFactor`, the same viewport and screen, through the test's own CDP session; the page reads it. */
async function moveToDensity(cdp: CDPSession, page: Page, screen: Screen, deviceScaleFactor: number): Promise<void> {
    const viewport = page.viewportSize();
    if (!viewport) throw new Error('the page has no viewport to keep while the density changes');
    try {
        await cdp.send('Emulation.setDeviceMetricsOverride', {width: viewport.width, height: viewport.height, deviceScaleFactor, mobile: false, screenWidth: screen.width, screenHeight: screen.height});
    } catch (error) {
        throw new Error(`Chromium refused the device metrics override from the test's CDP session (${error instanceof Error ? error.message : String(error)}): the density cannot be changed at runtime in this harness`);
    }
    await expect.poll(() => page.evaluate(() => window.devicePixelRatio), {message: `window.devicePixelRatio reaches ${deviceScaleFactor} under Emulation.setDeviceMetricsOverride`, timeout: 10_000}).toBe(deviceScaleFactor);
}

/** Back to the context's own emulation once the test is over, the session closed. Never fails the test: the context goes next. */
async function leaveDensity(cdp: CDPSession): Promise<void> {
    await cdp.send('Emulation.clearDeviceMetricsOverride').catch(() => undefined);
    await cdp.detach().catch(() => undefined);
}

/**
 * The probe: a `(resolution: <density>dppx)` query of the test's own on the density of this moment, in place of the
 * previous one, its count of `change` events back to 0. Created through the native `matchMedia`, so the bridge never
 * records it, and never dispatches on it.
 */
async function armProbe(page: Page): Promise<void> {
    await page.evaluate(() => {
        const holder = window as unknown as DensityWindow;
        if (holder.__lfDensityProbe) holder.__lfDensityProbe.query.removeEventListener('change', holder.__lfDensityProbe.heard);
        const matchMedia = holder.__lfNativeMatchMedia ?? window.matchMedia;
        const query = matchMedia.call(window, `(resolution: ${window.devicePixelRatio}dppx)`);
        const heard = (): void => {
            holder.__lfDensityChanges = (holder.__lfDensityChanges ?? 0) + 1;
        };
        query.addEventListener('change', heard);
        holder.__lfDensityProbe = {query, heard};
        holder.__lfDensityChanges = 0;
    });
}

/**
 * The probe's count, read after two rendering updates — the step in which a browser fires the media query changes it
 * owes: layout forced first, so that an evaluation of the media queries deferred to the next style update runs, then
 * two animation frames, the second of which comes after the changes the first one enqueued are dispatched.
 */
function probeChanges(page: Page): Promise<number> {
    return page.evaluate(
        () =>
            new Promise<number>((resolve) => {
                void document.documentElement.getBoundingClientRect();
                requestAnimationFrame(() => requestAnimationFrame(() => resolve((window as unknown as DensityWindow).__lfDensityChanges ?? 0)));
            }),
    );
}

/** Whether the probe hears Chromium's `change` within {@link PROBE_MS}, each read after two rendering updates. A silence is an answer, not a failure. */
function chromiumFired(page: Page): Promise<boolean> {
    return expect
        .poll(() => probeChanges(page), {
            message: `probe: does Chromium fire a resolution change within ${PROBE_MS} ms? A timeout here is the harness's answer, bridged next — not a failure`,
            timeout: PROBE_MS,
            intervals: [0],
        })
        .toBeGreaterThan(0)
        .then(
            () => true,
            () => false,
        );
}

/**
 * The init script of the bridge, installed before the test's first navigation: in each document, every `MediaQueryList`
 * the page creates through `window.matchMedia` whose media names `resolution` is recorded, the real object returned
 * unchanged; the native `matchMedia` is kept for the probe. It only records: no query is altered, none is answered for
 * the browser. Playwright sends its source to the page, so it uses nothing outside itself.
 */
function recordResolutionQueries(): void {
    const holder = window as unknown as DensityWindow;
    const native = holder.__lfNativeMatchMedia ?? window.matchMedia;
    if (typeof native !== 'function') return;
    const recorded: MediaQueryList[] = [];
    Object.defineProperty(window, '__lfResolutionQueries', {value: recorded, configurable: true});
    Object.defineProperty(window, '__lfNativeMatchMedia', {value: native, configurable: true});
    window.matchMedia = function matchMedia(query: string): MediaQueryList {
        const list = native.call(window, query);
        if (/resolution/i.test(list.media)) recorded.push(list);
        return list;
    };
}

/** The media of every resolution query the page created, oldest first, as the init script recorded them; `null` in a document it did not run in. */
function resolutionQueries(page: Page): Promise<string[] | null> {
    return page.evaluate(() => (window as unknown as DensityWindow).__lfResolutionQueries?.map((query) => query.media) ?? null);
}

/** A list's media that names `(resolution: <ratio>dppx)`. */
const densityQuery = (ratio: number): RegExp => new RegExp(`\\(\\s*resolution\\s*:\\s*${String(ratio).replace('.', '\\.')}dppx\\s*\\)`, 'i');

/**
 * The bridge: `change` dispatched on the latest resolution query the app created — a `MediaQueryListEvent` with the
 * list's own `media` and `matches`, what the browser sends — provided it still names `from`, the density before the
 * change: the query the app's watcher armed. When the app has armed another since, Chromium's own event came after the
 * probe's window: nothing is dispatched.
 */
function dispatchDensityChange(page: Page, from: number): Promise<{dispatched: boolean; media: string | null}> {
    return page.evaluate((source) => {
        const latest = (window as unknown as DensityWindow).__lfResolutionQueries?.at(-1);
        if (!latest || !new RegExp(source, 'i').test(latest.media)) return {dispatched: false, media: latest?.media ?? null};
        const event = typeof MediaQueryListEvent === 'function' ? new MediaQueryListEvent('change', {media: latest.media, matches: latest.matches}) : new Event('change');
        latest.dispatchEvent(event);
        return {dispatched: true, media: latest.media};
    }, densityQuery(from).source);
}

/**
 * The screen from `from` to `to`, and the change delivered to the page: fired by Chromium, or else dispatched by the
 * bridge on the app's own query — annotated `density-change` and printed, either way. From there the page has the
 * change, so what follows is the product's: the app arms its query again on `to`, the query the next change reaches.
 */
async function changeDensity(page: Page, cdp: CDPSession, screen: Screen, from: number, to: number): Promise<Delivery> {
    await armProbe(page);
    await moveToDensity(cdp, page, screen, to);
    let delivery: Delivery = 'fired by Chromium';
    let account = 'fired by Chromium';
    if (!(await chromiumFired(page))) {
        const bridge = await dispatchDensityChange(page, from);
        if (bridge.dispatched) {
            delivery = 'dispatched by the test';
            account = `${DISPATCHED}; dispatched on «${bridge.media}»`;
        } else {
            account = `fired by Chromium, after the probe's ${PROBE_MS} ms: the app had armed «${bridge.media ?? '(no query)'}» already`;
        }
    }
    const description = `${account} (${from}× → ${to}×)`;
    test.info().annotations.push({type: 'density-change', description});
    console.log(`[density-change] ${description}`);
    await expect
        .poll(async () => (await resolutionQueries(page))?.at(-1) ?? '(no query)', {
            message: `the page received the change of density (${delivery}), yet the app did not arm its resolution query again on ${to}dppx: its query did not get the change, or the handler of chartPixelRatio.ts did not run, or did not re-arm`,
            timeout: 5_000,
        })
        .toMatch(densityQuery(to));
    return delivery;
}

// ============================================================================
// The tests
// ============================================================================

test.describe('Chart pixel density on the Dashboard (DV)', () => {
    test.skip(({browserName, isMobile}) => browserName !== 'chromium' || isMobile, 'Desktop Chromium only: the density is changed through a Chromium DevTools command, from the desktop project’s deviceScaleFactor 1');

    test('the charts on screen follow a change of density in place: 1× → 2× → 1×, the same instances and the same canvases', async ({page}) => {
        test.setTimeout(120_000);
        // Before the first navigation: every resolution query the page creates is recorded, for the bridge (see the header).
        await page.addInitScript(recordResolutionQueries);
        await openOverview(page);
        const hosts = chartHosts(page);
        const before = (await readHosts(hosts)).filter((host) => host.canvases.length > 0);
        const ids = before.map((host) => host.id);
        const pieId = await page.getByTestId('allocation-panel').locator(PIE).getAttribute('_echarts_instance_');
        const growthIds = (await readHosts([hosts[0]])).map((host) => host.id);
        expect(ids, 'precondition: the growth chart and the allocation pie are laid out and measured').toEqual(expect.arrayContaining([...growthIds, pieId ?? '(no pie)']));
        expect(growthIds.length, 'precondition: the growth chart is laid out').toBeGreaterThan(0);
        expect(densities(before), "precondition: at the desktop project's deviceScaleFactor 1, every canvas is drawn at 1×").toEqual(densitiesAt(before, 1));
        const queries = await resolutionQueries(page);
        expect(queries, 'precondition: the init script records the resolution queries of this document').not.toBeNull();
        expect(queries?.at(-1) ?? '(no query)', 'the app armed no resolution query on the density of the screen, 1dppx: nothing in the page hears a change of density (the watcher of chartPixelRatio.ts, armed by the first chart created through chartInitOptions)').toMatch(densityQuery(1));
        await rememberCanvases(hosts);
        const screen = await screenOf(page);

        const cdp = await page.context().newCDPSession(page);
        try {
            const toDense = await changeDensity(page, cdp, screen, 1, DENSE);
            await expect
                .poll(async () => densities(byIds(await readHosts(hosts), ids)), {
                    message: `the page received the change of density (${toDense}), yet the charts created through chartInitOptions did not follow it: their canvases kept their backing store, or a chart was created again under a new id`,
                    timeout: 10_000,
                })
                .toEqual(densitiesAt(before, DENSE));
            const after = byIds(await readHosts(hosts), ids);
            expect(nodesOf(after), `the page received the change of density (${toDense}): the charts followed it in place, the same instances on the same canvas nodes`).toEqual(sameNodesAs(before));
            const renders = `data-chart-renders before → after the change: ${before.map((host) => `${host.id} ${host.renders} → ${after.find((other) => other.id === host.id)?.renders}`).join(', ')}`;
            test.info().annotations.push({type: 'chart-renders', description: renders});
            console.log(`[chart-renders] ${renders}`);

            const backToOne = await changeDensity(page, cdp, screen, DENSE, 1);
            await expect
                .poll(async () => densities(byIds(await readHosts(hosts), ids)), {
                    message: `the page received the change back to density 1 (${backToOne}), yet the charts stayed at 2×`,
                    timeout: 10_000,
                })
                .toEqual(densitiesAt(before, 1));
            expect(nodesOf(byIds(await readHosts(hosts), ids)), `the page received the change back to density 1 (${backToOne}): the charts followed it in place, the same instances on the same canvas nodes`).toEqual(sameNodesAs(before));
        } finally {
            await leaveDensity(cdp);
        }
    });

    test('a chart opened after the change of density is born at it: the allocation pie of another dimension, at 2×', async ({page}) => {
        test.setTimeout(90_000);
        await openOverview(page);
        const panel = page.getByTestId('allocation-panel');
        const typePie = panel.locator(PIE);
        const typeId = await typePie.getAttribute('_echarts_instance_');
        expect(typeId, 'precondition: the pie by type has an instance id').toBeTruthy();
        const [drawnByType] = await readHosts([typePie]);
        expect(drawnByType.canvases.length, 'precondition: the pie by type is laid out').toBeGreaterThan(0);
        expect(densities([drawnByType]), "precondition: at the desktop project's deviceScaleFactor 1, the pie is drawn at 1×").toEqual(densitiesAt([drawnByType], 1));
        const screen = await screenOf(page);

        const cdp = await page.context().newCDPSession(page);
        try {
            await moveToDensity(cdp, page, screen, DENSE);

            const sector = page.getByTestId('allocation-tab-sector');
            await sector.click();
            await expect(sector).toHaveAttribute('aria-pressed', 'true');
            const sectorPie = panel.locator(`${PIE}:not([_echarts_instance_="${typeId}"])`);
            await expect(sectorPie, 'the pie by sector, a chart created after the change, drew').toHaveCount(1, {timeout: 20_000});
            const [born] = await readHosts([sectorPie]);
            expect(born.canvases.length, 'barrier: the new pie is laid out').toBeGreaterThan(0);

            expect(densities([born]), 'a chart created after the density changed is born at the new one: chartInitOptions reads window.devicePixelRatio at creation, where zrender keeps the density it read when the page loaded').toEqual(densitiesAt([born], DENSE));
        } finally {
            await leaveDensity(cdp);
        }
    });
});
