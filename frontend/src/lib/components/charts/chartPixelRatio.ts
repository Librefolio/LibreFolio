/**
 * The pixel density every chart draws at: set when a chart is created, and changed in place when the screen's density
 * changes — the window moved to a screen of another density, or the browser zoomed.
 *
 * ECharts draws on canvases whose backing store is their CSS size times a density. zrender reads that density once,
 * when its module loads (`zrender/lib/config.js`), and fixes it for a chart at `init` (`CanvasPainter`, then each of its
 * `Layer`s); `resize()` keeps it, and no public API changes it. So a tab opened on a 1× screen drew every chart at 1× —
 * the ones opened later too — and blurred them all once moved to a Retina screen, until a reload.
 *
 * - **At creation**, {@link chartInitOptions}: every chart is created as
 *   `echarts.init(element, CHART_INIT_THEME, chartInitOptions(element))`, at the density of that moment. The K-13 gate
 *   (`chartFlagFont.test.ts`) holds every call to it.
 * - **When the density changes**, one `matchMedia` query for the whole app, armed by the first chart and re-armed at
 *   each change: every chart created through {@link chartInitOptions} and still alive is brought to the new density in
 *   place ({@link setChartPixelRatio}). Nothing is created again, so a chart keeps its zoom, its legend, its selection
 *   and its handlers, and nothing is drawn again from its options.
 *
 * In place means zrender 6's canvas painter from the inside: `painter.dpr`, `painter.getLayers()`, and on each layer
 * `dpr`, `ctx.dpr` and `resize()`, then `painter.refresh(true)` — the branch `CanvasPainter.resize` runs when the size
 * changes, at the same size and a new density. Each member is recognised before anything is touched; when one is not
 * what this module knows, the chart stays as it is, with a warning in debug builds, never worse than before.
 * `chartPixelRatio.test.ts` runs the update on the real zrender, so an upgrade that moves them fails there first.
 *
 * @module lib/components/charts/chartPixelRatio
 */
import {getInstanceByDom, type EChartsInitOpts, type EChartsType} from 'echarts';
import {debug} from '$lib/debug';

/** The density a chart draws at: the screen's, never under 1 — zrender's own rule (`zrender/lib/config.js`). */
export function chartPixelRatio(): number {
    if (typeof window === 'undefined') return 1;
    return Math.max(window.devicePixelRatio || 1, 1);
}

/** The elements of the charts created through {@link chartInitOptions}: those whose chart may still be alive. */
const followed = new Set<HTMLElement>();

/** The query that matches the density of the screen: it fires once the density leaves it. */
let densityQuery: MediaQueryList | null = null;

/**
 * The options of `echarts.init` for a chart on `element`: the canvas renderer and the density of this moment, `extra`
 * in between. The element is followed: when the screen's density changes, its chart is brought to it.
 */
export function chartInitOptions(element: HTMLElement | null | undefined, extra: EChartsInitOpts = {}): EChartsInitOpts {
    if (element) follow(element);
    return {renderer: 'canvas', ...extra, devicePixelRatio: chartPixelRatio()};
}

/** Follows `element`, and lets go of the elements no longer in the document: their chart went with them. */
function follow(element: HTMLElement): void {
    for (const known of followed) {
        if (known !== element && !known.isConnected) followed.delete(known);
    }
    followed.add(element);
    if (!densityQuery) watchDensity();
}

/** Arms the query on the density of the screen now, in place of the one that fired. Without `matchMedia`, nothing. */
function watchDensity(): void {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    densityQuery?.removeEventListener('change', onDensityChange);
    const ratio = window.devicePixelRatio || 1;
    // `resolution` and its WebKit spelling, for the Safari releases before 16 that know only the second.
    const query = window.matchMedia(`(resolution: ${ratio}dppx), (-webkit-device-pixel-ratio: ${ratio})`);
    if (typeof query?.addEventListener !== 'function') return;
    query.addEventListener('change', onDensityChange);
    densityQuery = query;
}

/** The density changed: the query is armed on the new one, and every chart still alive is brought to it. */
function onDensityChange(): void {
    watchDensity();
    const ratio = chartPixelRatio();
    for (const element of followed) {
        const chart = element.isConnected ? getInstanceByDom(element) : undefined;
        if (!chart || chart.isDisposed()) {
            followed.delete(element);
            continue;
        }
        setChartPixelRatio(chart, ratio);
    }
}

/** A chart as {@link setChartPixelRatio} reads it: its public API, so a test can hand in a zrender of its own. */
export type PixelRatioChart = Pick<EChartsType, 'getZr' | 'isDisposed' | 'getWidth' | 'getHeight'>;

/** zrender 6's canvas painter: the members this module touches. */
interface CanvasPainterInternals {
    dpr: number;
    getType(): string;
    getLayers(): Record<string, CanvasLayerInternals>;
    refresh(paintAll?: boolean): unknown;
}

/** One of its layers, a canvas each: the members this module touches. */
interface CanvasLayerInternals {
    dpr: number;
    ctx?: {dpr?: number} | null;
    resize(width: number, height: number): unknown;
}

/**
 * The canvas painter of `chart` and its layers, once each member this module touches is there with the type it
 * expects; `null` for a painter that is not a canvas (an SVG draws at any density); otherwise the member missing.
 */
function recognise(chart: PixelRatioChart): {painter: CanvasPainterInternals; layers: CanvasLayerInternals[]} | null | string {
    const painter = (chart.getZr() as unknown as {painter?: Partial<CanvasPainterInternals>} | undefined)?.painter;
    if (!painter || typeof painter.getType !== 'function') return 'painter.getType()';
    if (painter.getType() !== 'canvas') return null;
    if (typeof painter.dpr !== 'number') return 'painter.dpr';
    if (typeof painter.getLayers !== 'function') return 'painter.getLayers()';
    if (typeof painter.refresh !== 'function') return 'painter.refresh()';
    const layers = painter.getLayers();
    if (!layers || typeof layers !== 'object') return 'painter.getLayers()';
    const list = Object.values(layers) as Partial<CanvasLayerInternals>[];
    for (const layer of list) {
        if (typeof layer?.dpr !== 'number') return 'layer.dpr';
        if (typeof layer.resize !== 'function') return 'layer.resize()';
        if (layer.ctx != null && typeof layer.ctx !== 'object') return 'layer.ctx';
    }
    return {painter: painter as CanvasPainterInternals, layers: list as CanvasLayerInternals[]};
}

/**
 * Brings `chart` to the density `ratio` in place: what zrender's `CanvasPainter.resize` does when the size changes —
 * every layer's canvas resized, then everything painted again — at the same size and the new density. True when the
 * chart changed. A chart already at `ratio`, a disposed one and an SVG one are left alone; so is one whose painter this
 * module does not recognise, with a warning in debug builds: it keeps drawing as before. It never throws.
 */
export function setChartPixelRatio(chart: PixelRatioChart, ratio: number): boolean {
    try {
        if (chart.isDisposed()) return false;
        const found = recognise(chart);
        if (found === null) return false;
        if (typeof found === 'string') {
            debug.warn('chartPixelRatio', `zrender's canvas painter has no ${found} as this module knows it: the chart keeps its density`);
            return false;
        }
        const {painter, layers} = found;
        if (painter.dpr === ratio && layers.every((layer) => layer.dpr === ratio)) return false;
        const width = chart.getWidth();
        const height = chart.getHeight();
        painter.dpr = ratio;
        for (const layer of layers) {
            layer.dpr = ratio;
            if (layer.ctx) layer.ctx.dpr = ratio;
            layer.resize(width, height);
        }
        painter.refresh(true);
        return true;
    } catch (error) {
        debug.warn('chartPixelRatio', 'the density could not be changed in place: the chart keeps drawing as before', error);
        return false;
    }
}
