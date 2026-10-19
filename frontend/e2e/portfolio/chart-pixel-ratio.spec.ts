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
 * - The page hears a change of density only through a `resolution` media query's `change`. A probe of the test's own,
 *   armed in the page on the same kind of query, says whether Chromium fired it under the override: if it did not, the
 *   first test fails on that, naming the harness, before any chart is read. The second test does not depend on it.
 * - In place: the same instance id on every host and the same canvas nodes (remembered in the page before the change).
 *   `data-chart-renders` is recorded, not asserted: a change of density may move sub-pixel layout, and a chart's
 *   ResizeObserver then redraws it through `resize()` — the product's own path, not this one. That nothing is drawn
 *   again from the options is `chartPixelRatio.test.ts`'s (no `setOption`, `resize` or `clear` on the change).
 *
 * ## Why it is red without the fix
 *
 * Without `chartInitOptions` the charts are created with `{renderer: 'canvas'}`: at the density zrender read when the
 * page loaded (1) whatever the screen's at their creation — the sector pie opened after the change is born at 1× — and
 * nothing brings the charts on screen to the new density: they stay at 1×.
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
async function screenOf(page: Page): Promise<{width: number; height: number}> {
    return page.evaluate(() => ({width: window.screen.width, height: window.screen.height}));
}

/** Chromium at `deviceScaleFactor`, the same viewport and screen, through the test's own CDP session; the page reads it. */
async function moveToDensity(cdp: CDPSession, page: Page, screen: {width: number; height: number}, deviceScaleFactor: number): Promise<void> {
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
 * The probe: a `(resolution: <density>dppx)` query of the test's own, armed in the page, re-armed at each change, that
 * counts the changes Chromium fires. The product hears a change of density in no other way.
 */
async function listenToDensity(page: Page): Promise<void> {
    await page.evaluate(() => {
        const holder = window as unknown as {__lfDensityChanges?: number};
        holder.__lfDensityChanges = 0;
        const arm = (): void => {
            const query = window.matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`);
            const heard = (): void => {
                query.removeEventListener('change', heard);
                holder.__lfDensityChanges = (holder.__lfDensityChanges ?? 0) + 1;
                arm();
            };
            query.addEventListener('change', heard);
        };
        arm();
    });
}

const densityChangesHeard = (page: Page): Promise<number> => page.evaluate(() => (window as unknown as {__lfDensityChanges?: number}).__lfDensityChanges ?? 0);

/** Waits for the probe to have heard `count` changes, or fails naming the harness. */
async function expectDensityChangeHeard(page: Page, count: number): Promise<void> {
    await expect
        .poll(() => densityChangesHeard(page), {
            message: 'Chromium fired no `change` on a (resolution: …dppx) media query under Emulation.setDeviceMetricsOverride: the page cannot hear the density change in this harness, so the charts on screen cannot follow it here. A harness limit to check before suspecting the product',
            timeout: 10_000,
        })
        .toBeGreaterThanOrEqual(count);
}

// ============================================================================
// The tests
// ============================================================================

test.describe('Chart pixel density on the Dashboard (DV)', () => {
    test.skip(({browserName, isMobile}) => browserName !== 'chromium' || isMobile, 'Desktop Chromium only: the density is changed through a Chromium DevTools command, from the desktop project’s deviceScaleFactor 1');

    test('the charts on screen follow a change of density in place: 1× → 2× → 1×, the same instances and the same canvases', async ({page}) => {
        test.setTimeout(90_000);
        await openOverview(page);
        const hosts = chartHosts(page);
        const before = (await readHosts(hosts)).filter((host) => host.canvases.length > 0);
        const ids = before.map((host) => host.id);
        const pieId = await page.getByTestId('allocation-panel').locator(PIE).getAttribute('_echarts_instance_');
        const growthIds = (await readHosts([hosts[0]])).map((host) => host.id);
        expect(ids, 'precondition: the growth chart and the allocation pie are laid out and measured').toEqual(expect.arrayContaining([...growthIds, pieId ?? '(no pie)']));
        expect(growthIds.length, 'precondition: the growth chart is laid out').toBeGreaterThan(0);
        expect(densities(before), "precondition: at the desktop project's deviceScaleFactor 1, every canvas is drawn at 1×").toEqual(densitiesAt(before, 1));
        await rememberCanvases(hosts);
        await listenToDensity(page);
        const screen = await screenOf(page);

        const cdp = await page.context().newCDPSession(page);
        try {
            await moveToDensity(cdp, page, screen, DENSE);
            await expectDensityChangeHeard(page, 1);
            await expect
                .poll(async () => densities(byIds(await readHosts(hosts), ids)), {
                    message: 'the page heard the change of density, yet the charts created through chartInitOptions did not follow it: their canvases kept their backing store (or a chart was created again under a new id)',
                    timeout: 10_000,
                })
                .toEqual(densitiesAt(before, DENSE));

            const after = byIds(await readHosts(hosts), ids);
            expect(
                after.map((host) => `${host.id}: ${host.canvases.length} canvas(es), ${host.canvases.every((canvas) => canvas.same === true) ? 'the same nodes' : 'new nodes'}`),
                'in place: the same instances, the same canvas nodes',
            ).toEqual(before.map((host) => `${host.id}: ${host.canvases.length} canvas(es), the same nodes`));
            test.info().annotations.push({type: 'chart-renders', description: `data-chart-renders before → after the change: ${before.map((host) => `${host.id} ${host.renders} → ${after.find((other) => other.id === host.id)?.renders}`).join(', ')}`});

            await moveToDensity(cdp, page, screen, 1);
            await expectDensityChangeHeard(page, 2);
            await expect
                .poll(async () => densities(byIds(await readHosts(hosts), ids)), {
                    message: 'back to density 1, the charts stayed at 2×: the query was not armed again on the new density',
                    timeout: 10_000,
                })
                .toEqual(densitiesAt(before, 1));
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
