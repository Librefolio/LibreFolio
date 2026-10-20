// @vitest-environment jsdom
/**
 * chartPixelRatio.test.ts — DV: a chart draws at the density of the screen it is on, from its creation and after the
 * density changes.
 *
 * ## What it protects
 *
 * ECharts draws on canvases whose backing store is their CSS size times a density. zrender 6 reads that density once,
 * when its module loads (`zrender/lib/config.js`), and fixes it for a chart at `init` (`CanvasPainter`, then each of
 * its `Layer`s); `resize()` keeps it, and no public API changes it. So a tab loaded on a 1× screen drew every chart at
 * 1×, the ones opened later too, until a reload: blurred once the window moved to a denser screen, or the browser
 * zoomed. `chartPixelRatio.ts`:
 *
 * - `chartPixelRatio()`: the screen's density, never under 1 (zrender's own rule), 1 without a window;
 * - `chartInitOptions(element, extra)`: the options of `echarts.init` — the canvas renderer, `extra`, and the density of
 *   this moment, which `extra` cannot override — and, given an element, follows it: the first one arms ONE `matchMedia`
 *   resolution query on the raw `devicePixelRatio`, in both spellings (`resolution: Xdppx`, `-webkit-device-pixel-ratio`);
 * - on that query's `change`: the query is armed again on the new density, the old listener removed, and every followed
 *   element still in the document whose chart is alive is brought to the new density in place;
 * - `setChartPixelRatio(chart, ratio)`: zrender's canvas painter from the inside, each member recognised before anything
 *   is touched; true when it changed the chart, false otherwise — with a debug warning when a member is not what the
 *   module knows, silently for an SVG chart, a disposed one or one already at `ratio` — and never a throw.
 *
 * ## How
 *
 * - The module keeps its state (the followed elements, the armed query), so the registry is reset before every case
 *   and the case imports the module — and ECharts, so that both share one instance whatever Vitest externalises.
 * - `window.devicePixelRatio` and `window.matchMedia` are stubbed (`vi.stubGlobal`), restored after every case. The
 *   fake `matchMedia` keeps every query and its `change` listeners, and fires a query's `change` only when its match
 *   flips, as a browser does: a query matches when one of the densities it names is the screen's. So a query armed on
 *   another density than the screen's (a clamped one, say) is never heard, exactly as in a browser.
 * - jsdom has no 2D canvas: `HTMLCanvasElement.prototype.getContext` answers a recording fake context per canvas (a
 *   Proxy: every method records its call and does nothing; `measureText`, the gradients and `getLineDash` answer what
 *   zrender reads from them). The charts are REAL ECharts 6 / zrender 6 instances on elements of `document.body`,
 *   created at an explicit size (jsdom lays nothing out), so each canvas's backing store and CSS size can be read and
 *   the repaint's scale is the `setTransform` its context records.
 * - `debug` (`$lib/debug`) is replaced by spies: its warning is the only trace of a refused chart.
 *
 * ## The zrender members it relies on
 *
 * `setChartPixelRatio` touches zrender 6's canvas painter from the inside: `painter.getType()`, `painter.dpr`,
 * `painter.getLayers()`, `painter.refresh(true)`, and on each layer `layer.dpr`, `layer.ctx.dpr` and `layer.resize()`.
 * The describe «on the real zrender 6 canvas painter» runs it on the real zrender, a control first listing those members:
 * an upgrade that moves one fails there by name.
 *
 * ## Why it was red before DV
 *
 * `chartPixelRatio.ts` did not exist: every import here failed. The premise below still shows the defect on the real
 * zrender: a chart created at density 2 without `chartInitOptions` draws at the density zrender read when it loaded.
 *
 * Registered in chart-safety-unit (scripts/test_runner/_frontend_portfolio.py).
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import type {EChartsOption, EChartsType} from 'echarts';
import type {PixelRatioChart} from './chartPixelRatio';

/** `debug` from `$lib/debug`, as spies: a no-op outside debug builds, its warning is the only trace of a refusal. */
const {debugMock} = vi.hoisted(() => ({
    debugMock: {log: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn(), group: vi.fn(), groupEnd: vi.fn(), time: vi.fn(), timeEnd: vi.fn()},
}));

vi.mock('$lib/debug', () => ({debug: debugMock, isDebugEnabled: () => true}));

type PixelRatioModule = typeof import('./chartPixelRatio');
type EChartsModule = typeof import('echarts');

// =============================================================================
// Fixtures
// =============================================================================

/** The CSS size of every chart here, in px: explicit, since jsdom lays nothing out. */
const WIDTH = 200;
const HEIGHT = 100;

/** A text every scene draws: its `fillText` is the repaint's witness. */
const TITLE = 'Density';

/** A small chart on two layers: a title and a bar series on zlevel 0, a line series on zlevel 1. No animation. */
const SCENE: EChartsOption = {
    animation: false,
    title: {text: TITLE},
    grid: {left: 30, right: 10, top: 30, bottom: 20},
    xAxis: {type: 'category', data: ['A', 'B', 'C']},
    yAxis: {type: 'value'},
    series: [
        {type: 'bar', data: [3, 1, 2]},
        {type: 'line', data: [1, 2, 3], zlevel: 1},
    ],
};

let pixelRatio: PixelRatioModule;
let echarts: EChartsModule;
let media: FakeMedia;

/** What each case mounted: removed, and its chart disposed, after the case. */
const mounted: Array<{element: HTMLElement; dispose: () => void}> = [];

/** The screen's density as the module and zrender read it: `window.devicePixelRatio`. */
function setDensity(ratio: number | undefined): void {
    vi.stubGlobal('devicePixelRatio', ratio);
}

/** A new element in the document, removed after the case. */
function hostElement(): HTMLDivElement {
    const element = document.createElement('div');
    document.body.append(element);
    mounted.push({element, dispose: () => {}});
    return element;
}

/** Disposes `dispose` with the element after the case. */
function track(element: HTMLElement, dispose: () => void): void {
    const entry = mounted.find((candidate) => candidate.element === element);
    if (entry) entry.dispose = dispose;
}

/** Disposes `chart` unless a case already did: ECharts warns about a second dispose. */
function disposeOnce(chart: EChartsType): void {
    if (!chart.isDisposed()) chart.dispose();
}

/** A real ECharts canvas chart on a new element, created through `chartInitOptions`: followed. */
function followedChart(): {element: HTMLDivElement; chart: EChartsType} {
    const element = hostElement();
    const chart = echarts.init(element, null, {...pixelRatio.chartInitOptions(element), width: WIDTH, height: HEIGHT});
    track(element, () => disposeOnce(chart));
    chart.setOption(SCENE);
    return {element, chart};
}

/** The same chart created at the density of this moment but without `chartInitOptions`: nothing follows it. */
function unfollowedChart(): {element: HTMLDivElement; chart: EChartsType} {
    const element = hostElement();
    const chart = echarts.init(element, null, {renderer: 'canvas', devicePixelRatio: pixelRatio.chartPixelRatio(), width: WIDTH, height: HEIGHT});
    track(element, () => disposeOnce(chart));
    chart.setOption(SCENE);
    return {element, chart};
}

const canvasesOf = (element: Element): HTMLCanvasElement[] => [...element.querySelectorAll('canvas')];

/** Each canvas of `element` as its backing store and its CSS size: `400×200 @ 200px×100px`. */
const sizesOf = (element: Element): string[] => canvasesOf(element).map((canvas) => `${canvas.width}×${canvas.height} @ ${canvas.style.width}×${canvas.style.height}`);

/** `count` canvases of the scene's CSS size at density `ratio`. */
const sizesAt = (ratio: number, count: number): string[] => Array.from({length: count}, () => `${WIDTH * ratio}×${HEIGHT * ratio} @ ${WIDTH}px×${HEIGHT}px`);

// =============================================================================
// The fake 2D context: every call recorded
// =============================================================================

/** One call a canvas context received. */
interface ContextCall {
    name: string;
    args: unknown[];
}

/** What a fake context answers to the calls zrender reads a value from. */
const CONTEXT_RESULTS: Readonly<Record<string, (...args: unknown[]) => unknown>> = {
    measureText: (text) => ({width: String(text ?? '').length * 7, actualBoundingBoxAscent: 9, actualBoundingBoxDescent: 3}),
    createLinearGradient: () => ({addColorStop: () => {}}),
    createRadialGradient: () => ({addColorStop: () => {}}),
    createConicGradient: () => ({addColorStop: () => {}}),
    createPattern: () => ({setTransform: () => {}}),
    getLineDash: () => [],
    isPointInPath: () => false,
    isPointInStroke: () => false,
    getTransform: () => ({a: 1, b: 0, c: 0, d: 1, e: 0, f: 0}),
    getImageData: (...args) => ({width: Number(args[2]) || 0, height: Number(args[3]) || 0, data: new Uint8ClampedArray((Number(args[2]) || 0) * (Number(args[3]) || 0) * 4)}),
};

/** The methods of a 2D context zrender and ECharts may call. */
const CONTEXT_METHODS = new Set([
    ...Object.keys(CONTEXT_RESULTS),
    'arc',
    'arcTo',
    'beginPath',
    'bezierCurveTo',
    'clearRect',
    'clip',
    'closePath',
    'drawImage',
    'ellipse',
    'fill',
    'fillRect',
    'fillText',
    'lineTo',
    'moveTo',
    'putImageData',
    'quadraticCurveTo',
    'rect',
    'resetTransform',
    'restore',
    'rotate',
    'roundRect',
    'save',
    'scale',
    'setLineDash',
    'setTransform',
    'stroke',
    'strokeRect',
    'strokeText',
    'transform',
    'translate',
]);

/** The fake context of each canvas that asked for one in this case, with the calls it received. */
const contexts = new Map<HTMLCanvasElement, ContextCall[]>();

/** A 2D context that keeps what is written to it, records every method call and draws nothing. */
function fakeContext(canvas: HTMLCanvasElement): CanvasRenderingContext2D {
    const calls: ContextCall[] = [];
    contexts.set(canvas, calls);
    const state: Record<PropertyKey, unknown> = {canvas};
    return new Proxy(state, {
        get(target, property) {
            if (property in target) return target[property];
            if (typeof property !== 'string' || !CONTEXT_METHODS.has(property)) return undefined;
            return (...args: unknown[]) => {
                calls.push({name: property, args});
                return CONTEXT_RESULTS[property]?.(...args);
            };
        },
        set(target, property, value) {
            target[property] = value;
            return true;
        },
    }) as unknown as CanvasRenderingContext2D;
}

function installCanvas(): void {
    contexts.clear();
    const known = new Map<HTMLCanvasElement, CanvasRenderingContext2D>();
    const getContext = function (this: HTMLCanvasElement, kind: string): CanvasRenderingContext2D | null {
        if (kind !== '2d') return null;
        const context = known.get(this) ?? fakeContext(this);
        known.set(this, context);
        return context;
    };
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(getContext as unknown as HTMLCanvasElement['getContext']);
}

/** The calls `canvas`'s context received, from index `from` on. */
function callsOf(canvas: HTMLCanvasElement, from = 0): ContextCall[] {
    return (contexts.get(canvas) ?? []).slice(from);
}

/** How many calls each canvas's context has received so far: the marks to read a repaint from. */
const marksOf = (canvases: HTMLCanvasElement[]): number[] => canvases.map((canvas) => callsOf(canvas).length);

/** A `setTransform` at scale `ratio`: `setTransform(ratio, 0, 0, ratio, …)` — an element without rotation or scale. */
const isScaleAt = (call: ContextCall, ratio: number): boolean => call.name === 'setTransform' && call.args[0] === ratio && call.args[1] === 0 && call.args[2] === 0 && call.args[3] === ratio;

/** For each canvas, whether its context drew at scale `ratio` since its mark. */
const drewAtScale = (canvases: HTMLCanvasElement[], marks: number[], ratio: number): boolean[] => canvases.map((canvas, index) => callsOf(canvas, marks[index]).some((call) => isScaleAt(call, ratio)));

/** The transform the context of `canvas` had when it drew `text` last, since `from`: `a,b,c,d` of the last `setTransform` before it. */
function scaleOfText(canvas: HTMLCanvasElement, text: string, from: number): string {
    const calls = callsOf(canvas, from);
    const drawn = calls.findLastIndex((call) => call.name === 'fillText' && call.args[0] === text);
    if (drawn === -1) return `«${text}» not drawn again`;
    const transform = calls.slice(0, drawn).findLast((call) => call.name === 'setTransform');
    return transform ? transform.args.slice(0, 4).join(',') : 'no setTransform before it';
}

// =============================================================================
// The fake matchMedia: queries, listeners, and a change that flips them
// =============================================================================

type ChangeListener = (event: {matches: boolean; media: string}) => void;

/** One query asked of the fake `matchMedia`: its text, whether it matches the screen, its `change` listeners. */
interface FakeQuery {
    media: string;
    matches: boolean;
    listeners: Set<ChangeListener>;
}

interface FakeMedia {
    matchMedia: Mock<(media: string) => unknown>;
    queries: FakeQuery[];
    /** The `change` listeners alive on every query. */
    liveListeners(): number;
    /** The screen moves to `ratio`: the density changes, then every query whose match flips fires `change`. */
    change(ratio: number): void;
}

/** The densities a resolution query names, in either spelling. */
function densitiesOf(media: string): number[] {
    return [...media.matchAll(/resolution\s*:\s*([\d.]+)dppx|device-pixel-ratio\s*:\s*([\d.]+)/g)].map((match) => Number(match[1] ?? match[2]));
}

function installMatchMedia(): FakeMedia {
    const queries: FakeQuery[] = [];
    const matchMedia = vi.fn((text: string) => {
        const query: FakeQuery = {media: text, matches: densitiesOf(text).includes(window.devicePixelRatio), listeners: new Set()};
        queries.push(query);
        return {
            media: text,
            get matches() {
                return query.matches;
            },
            onchange: null,
            addEventListener(type: string, listener: ChangeListener) {
                if (type === 'change') query.listeners.add(listener);
            },
            removeEventListener(type: string, listener: ChangeListener) {
                if (type === 'change') query.listeners.delete(listener);
            },
            dispatchEvent: () => true,
        };
    });
    vi.stubGlobal('matchMedia', matchMedia);
    return {
        matchMedia,
        queries,
        liveListeners: () => queries.reduce((sum, query) => sum + query.listeners.size, 0),
        change(ratio) {
            setDensity(ratio);
            for (const query of [...queries]) {
                const matches = densitiesOf(query.media).includes(ratio);
                if (matches === query.matches) continue;
                query.matches = matches;
                for (const listener of [...query.listeners]) listener({matches, media: query.media});
            }
        },
    };
}

/** A query as these tests read it: the density it names in each spelling, and its live listeners. */
function describeQuery(query: FakeQuery): string {
    const resolution = /\(resolution:\s*([\d.]+)dppx\)/.exec(query.media)?.[1] ?? '—';
    const webkit = /\(-webkit-device-pixel-ratio:\s*([\d.]+)\)/.exec(query.media)?.[1] ?? '—';
    return `resolution ${resolution}dppx, webkit ${webkit}: ${query.listeners.size} listener(s)`;
}

const queryAt = (ratio: number, listeners: number): string => `resolution ${ratio}dppx, webkit ${ratio}: ${listeners} listener(s)`;

// =============================================================================
// zrender 6's canvas painter, as far as these tests read it
// =============================================================================

interface LayerView {
    dpr: unknown;
    ctx?: {dpr?: unknown} | null;
    dom: HTMLCanvasElement;
    resize: unknown;
}

interface PainterView {
    dpr: unknown;
    getType(): string;
    getLayers(): Record<string, LayerView>;
    refresh: unknown;
}

const painterOf = (zr: unknown): PainterView => (zr as {painter: PainterView}).painter;

/** Every layer of `painter`, by zlevel: `zlevel → dpr/ctx.dpr, backing store @ CSS size`. */
function layersAt(painter: PainterView): string[] {
    return Object.entries(painter.getLayers()).map(([zlevel, layer]) => `${zlevel} → ${String(layer.dpr)}/${String(layer.ctx?.dpr)}, ${layer.dom.width}×${layer.dom.height} @ ${layer.dom.style.width}×${layer.dom.style.height}`);
}

const layerAt = (zlevel: string, ratio: number): string => `${zlevel} → ${ratio}/${ratio}, ${WIDTH * ratio}×${HEIGHT * ratio} @ ${WIDTH}px×${HEIGHT}px`;

/** zrender's hover layer: elements in a hover state are drawn on it (`HOVER_LAYER_ZLEVEL`, `canvas/Painter.js`). */
const HOVER_ZLEVEL = '100000';

/**
 * A bare zrender 6 scene through ECharts' own zrender: a Rect and a Text on the main layer, and a Rect put in a hover
 * state, which zrender draws on its hover layer. Handed to `setChartPixelRatio` through the adapter its type allows.
 */
function zrenderScene(ratio: number) {
    const element = hostElement();
    const zr = echarts.zrender.init(element, {renderer: 'canvas', devicePixelRatio: ratio, width: WIDTH, height: HEIGHT});
    track(element, () => zr.dispose());
    zr.add(new echarts.graphic.Rect({shape: {x: 10, y: 10, width: 60, height: 40}, style: {fill: '#336699'}}));
    zr.add(new echarts.graphic.Text({x: 90, y: 30, style: {text: TITLE, fill: '#222222'}}));
    const hovered = new echarts.graphic.Rect({shape: {x: 150, y: 60, width: 20, height: 20}, style: {fill: '#993366'}});
    hovered.states = {emphasis: {style: {fill: '#669933'}}};
    zr.add(hovered);
    zr.flush();
    hovered.useState('emphasis', false, true, true);
    zr.flush();
    const chart = {getZr: () => zr, isDisposed: () => false, getWidth: () => zr.getWidth() ?? 0, getHeight: () => zr.getHeight() ?? 0} as unknown as PixelRatioChart;
    return {element, zr, chart, painter: painterOf(zr)};
}

beforeEach(async () => {
    vi.resetModules();
    for (const spy of Object.values(debugMock)) spy.mockClear();
    setDensity(1);
    installCanvas();
    media = installMatchMedia();
    pixelRatio = await import('./chartPixelRatio');
    echarts = await import('echarts');
});

afterEach(() => {
    for (const {element, dispose} of mounted.splice(0)) {
        dispose();
        element.remove();
    }
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

// =============================================================================
// chartPixelRatio()
// =============================================================================

describe('chartPixelRatio() — the screen’s density, never under 1', () => {
    it.each([
        [2, 2],
        [1.5, 1.5],
        [3, 3],
        [1, 1],
        [0.8, 1],
        [0.5, 1],
        [0, 1],
        [undefined, 1],
    ])('window.devicePixelRatio %s → %s', (screen, expected) => {
        setDensity(screen);

        expect(pixelRatio.chartPixelRatio()).toBe(expected);
    });

    it('1 where there is no window', () => {
        vi.stubGlobal('window', undefined);
        let ratio: number;
        try {
            ratio = pixelRatio.chartPixelRatio();
        } finally {
            vi.unstubAllGlobals();
        }

        expect(ratio).toBe(1);
    });
});

// =============================================================================
// chartInitOptions() — a chart is born at the density of its moment
// =============================================================================

describe('chartInitOptions() — the options of echarts.init: the canvas renderer and the density of this moment', () => {
    it('{renderer: canvas, devicePixelRatio: <the screen’s>}, with an element or without', () => {
        setDensity(1.5);

        expect(pixelRatio.chartInitOptions(hostElement())).toEqual({renderer: 'canvas', devicePixelRatio: 1.5});
        expect(pixelRatio.chartInitOptions(null)).toEqual({renderer: 'canvas', devicePixelRatio: 1.5});
        expect(pixelRatio.chartInitOptions(undefined)).toEqual({renderer: 'canvas', devicePixelRatio: 1.5});
    });

    it('keeps what extra adds, and extra cannot override the density', () => {
        setDensity(2);

        expect(pixelRatio.chartInitOptions(hostElement(), {locale: 'IT', useDirtyRect: false})).toEqual({renderer: 'canvas', locale: 'IT', useDirtyRect: false, devicePixelRatio: 2});
        expect(pixelRatio.chartInitOptions(hostElement(), {devicePixelRatio: 3}).devicePixelRatio).toBe(2);
    });

    it('never under 1: a zoomed-out screen at 0.8 gives 1, as zrender would', () => {
        setDensity(0.8);

        expect(pixelRatio.chartInitOptions(hostElement()).devicePixelRatio).toBe(1);
    });

    it('read at each call, never kept: created under density 1 then under 2, the second options carry 2', () => {
        setDensity(1);
        const first = pixelRatio.chartInitOptions(hostElement());
        setDensity(2);
        const second = pixelRatio.chartInitOptions(hostElement());

        expect([first.devicePixelRatio, second.devicePixelRatio]).toEqual([1, 2]);
    });

    it('premise, the defect on the real zrender: at density 2, a chart created without chartInitOptions draws at the density zrender read when it loaded (1 here); one created through it draws at 2', () => {
        setDensity(2);
        const bare = hostElement();
        const before = echarts.init(bare, null, {renderer: 'canvas', width: WIDTH, height: HEIGHT});
        track(bare, () => disposeOnce(before));
        before.setOption(SCENE);
        const {element, chart} = followedChart();

        expect(canvasesOf(bare).length, 'barrier: the bare chart drew on canvases').toBeGreaterThan(0);
        expect(sizesOf(bare), "without chartInitOptions: zrender's density of its load, not the screen's").toEqual(sizesAt(1, canvasesOf(bare).length));
        expect(before.getDevicePixelRatio()).toBe(1);
        expect(canvasesOf(element).length, 'barrier: the scene draws on two layers (zlevel 0 and 1)').toBeGreaterThanOrEqual(2);
        expect(sizesOf(element), 'through chartInitOptions: the screen’s density').toEqual(sizesAt(2, canvasesOf(element).length));
        expect(chart.getDevicePixelRatio()).toBe(2);
    });
});

// =============================================================================
// The watcher: one query for the whole app, armed lazily, re-armed at each change
// =============================================================================

describe('the density watcher — one matchMedia query on the raw density, armed by the first chart, re-armed at each change', () => {
    it('is not armed at import, nor by a call without an element; the first element arms it, the next ones do not', () => {
        expect(media.matchMedia, 'armed at import').not.toHaveBeenCalled();

        pixelRatio.chartInitOptions(null);
        pixelRatio.chartInitOptions(undefined);
        expect(media.matchMedia, 'armed by a call without an element').not.toHaveBeenCalled();

        pixelRatio.chartInitOptions(hostElement());
        pixelRatio.chartInitOptions(hostElement());
        expect(media.queries.map(describeQuery), 'one query, on density 1, in both spellings').toEqual([queryAt(1, 1)]);
    });

    it('on a change the old listener is removed and a query on the new density armed; again at the next change, and back: one live listener at any time', () => {
        pixelRatio.chartInitOptions(hostElement());

        media.change(2);
        expect(media.queries.map(describeQuery)).toEqual([queryAt(1, 0), queryAt(2, 1)]);

        media.change(3);
        expect(media.queries.map(describeQuery)).toEqual([queryAt(1, 0), queryAt(2, 0), queryAt(3, 1)]);

        media.change(1);
        expect(media.queries.map(describeQuery)).toEqual([queryAt(1, 0), queryAt(2, 0), queryAt(3, 0), queryAt(1, 1)]);
        expect(media.liveListeners()).toBe(1);
    });

    it('names the raw density, not the clamped one: armed at 0.8 (zoomed out), a step to 0.9 is heard, and the next to 2 brings the chart to 2×', () => {
        setDensity(0.8);
        const {element, chart} = followedChart();
        const count = canvasesOf(element).length;
        expect(sizesOf(element), 'born at 1: never under 1').toEqual(sizesAt(1, count));
        expect(media.queries.map(describeQuery)).toEqual([queryAt(0.8, 1)]);

        media.change(0.9);
        expect(media.queries.map(describeQuery), 'a query on 1dppx would not have flipped from 0.8 to 0.9: nothing heard, ever after').toEqual([queryAt(0.8, 0), queryAt(0.9, 1)]);
        expect(sizesOf(element), 'still never under 1').toEqual(sizesAt(1, count));

        media.change(2);
        expect(sizesOf(element)).toEqual(sizesAt(2, count));
        expect(chart.getDevicePixelRatio()).toBe(2);
    });

    it.each([
        ['no matchMedia', undefined],
        ['a matchMedia whose list has no addEventListener (Safari before 14)', () => ({matches: true, media: '(resolution: 2dppx)', addListener: () => {}, removeListener: () => {}})],
        ['a matchMedia that answers null', () => null],
    ])('%s: chartInitOptions answers all the same, and throws nothing', (_, replacement) => {
        vi.stubGlobal('matchMedia', replacement);
        setDensity(2);

        expect(pixelRatio.chartInitOptions(hostElement())).toEqual({renderer: 'canvas', devicePixelRatio: 2});
        expect(() => pixelRatio.chartInitOptions(hostElement())).not.toThrow();
    });
});

// =============================================================================
// On a change: every live chart followed is brought to the new density, in place
// =============================================================================

describe('on a change of density — every live chart created through chartInitOptions is brought to it in place (real ECharts)', () => {
    it('to 2: every canvas’s backing store doubles while its CSS size stays; the same instance and the same canvas nodes; nothing is set or resized from its options', () => {
        const {element, chart} = followedChart();
        const canvases = canvasesOf(element);
        const id = element.getAttribute('_echarts_instance_');
        expect(canvases.length, 'barrier: the scene draws on two layers (zlevel 0 and 1)').toBeGreaterThanOrEqual(2);
        expect(sizesOf(element), 'precondition: born at 1').toEqual(sizesAt(1, canvases.length));
        const setOption = vi.spyOn(chart, 'setOption');
        const resize = vi.spyOn(chart, 'resize');
        const clear = vi.spyOn(chart, 'clear');
        const marks = marksOf(canvases);

        media.change(2);

        expect(chart.getDevicePixelRatio()).toBe(2);
        expect(sizesOf(element)).toEqual(sizesAt(2, canvases.length));
        expect(drewAtScale(canvases, marks, 2), 'every layer painted again at scale 2').toEqual(canvases.map(() => true));
        expect(echarts.getInstanceByDom(element), 'the same instance on the element').toBe(chart);
        expect(element.getAttribute('_echarts_instance_')).toBe(id);
        expect(
            canvasesOf(element).every((canvas, index) => canvas === canvases[index]),
            'the same canvas nodes: nothing created again',
        ).toBe(true);
        expect({setOption: setOption.mock.calls.length, resize: resize.mock.calls.length, clear: clear.mock.calls.length}, 'nothing drawn again from the options').toEqual({setOption: 0, resize: 0, clear: 0});
    });

    it('and back to 1 at the next change: the query re-armed on 2 hears it', () => {
        const {element, chart} = followedChart();
        const count = canvasesOf(element).length;

        media.change(2);
        expect(sizesOf(element)).toEqual(sizesAt(2, count));
        media.change(1);

        expect(sizesOf(element)).toEqual(sizesAt(1, count));
        expect(chart.getDevicePixelRatio()).toBe(1);
    });

    it('a chart whose element left the document before the change is not touched, while one still in it is', () => {
        const gone = followedChart();
        const kept = followedChart();
        gone.element.remove();

        media.change(2);

        expect(sizesOf(kept.element), 'control: the chart still in the document follows').toEqual(sizesAt(2, canvasesOf(kept.element).length));
        expect(sizesOf(gone.element), 'the detached chart keeps its density').toEqual(sizesAt(1, canvasesOf(gone.element).length));
        expect(gone.chart.getDevicePixelRatio()).toBe(1);
    });

    it('a chart disposed before the change is skipped without a throw, and the charts followed after it still follow', () => {
        const disposed = followedChart();
        disposed.chart.dispose();
        const live = followedChart();
        expect(disposed.element.isConnected, 'precondition: the disposed chart’s element is still in the document').toBe(true);

        expect(() => media.change(2)).not.toThrow();

        expect(sizesOf(live.element)).toEqual(sizesAt(2, canvasesOf(live.element).length));
        expect(disposed.chart.isDisposed()).toBe(true);
        expect(echarts.getInstanceByDom(disposed.element), 'nothing created again on the disposed chart’s element').toBeUndefined();
    });

    it('a chart created without chartInitOptions is not followed: it keeps its density, while one created through it follows', () => {
        const alone = unfollowedChart();
        const followed = followedChart();

        media.change(2);

        expect(sizesOf(followed.element), 'control: the followed chart moves to 2').toEqual(sizesAt(2, canvasesOf(followed.element).length));
        expect(sizesOf(alone.element)).toEqual(sizesAt(1, canvasesOf(alone.element).length));
        expect(alone.chart.getDevicePixelRatio()).toBe(1);
    });

    it('every followed chart, not only the first: three charts all at 2', () => {
        const charts = [followedChart(), followedChart(), followedChart()];

        media.change(2);

        expect(charts.map(({chart}) => chart.getDevicePixelRatio())).toEqual([2, 2, 2]);
        expect(charts.flatMap(({element}) => sizesOf(element))).toEqual(charts.flatMap(({element}) => sizesAt(2, canvasesOf(element).length)));
    });
});

// =============================================================================
// setChartPixelRatio on the real zrender — the guard of a zrender upgrade
// =============================================================================

describe('setChartPixelRatio on the real zrender 6 canvas painter — relies on painter.getType(), painter.dpr, painter.getLayers(), painter.refresh(true), layer.dpr, layer.ctx.dpr, layer.resize()', () => {
    it('control — zrender still has every member chartPixelRatio reads and writes, with the types it expects', () => {
        const {painter} = zrenderScene(1);
        const layers = Object.values(painter.getLayers());
        const types = (read: (layer: LayerView) => unknown): string[] => [...new Set(layers.map((layer) => typeof read(layer)))];

        expect({
            'painter.getType()': painter.getType(),
            'painter.dpr': typeof painter.dpr,
            'painter.getLayers()': typeof painter.getLayers,
            'painter.refresh()': typeof painter.refresh,
            'its layers, the hover one among them': Object.keys(painter.getLayers()).includes(HOVER_ZLEVEL) && layers.length >= 2,
            'layer.dpr': types((layer) => layer.dpr),
            'layer.ctx': types((layer) => layer.ctx),
            'layer.ctx.dpr': types((layer) => layer.ctx?.dpr),
            'layer.resize()': types((layer) => layer.resize),
        }).toEqual({
            'painter.getType()': 'canvas',
            'painter.dpr': 'number',
            'painter.getLayers()': 'function',
            'painter.refresh()': 'function',
            'its layers, the hover one among them': true,
            'layer.dpr': ['number'],
            'layer.ctx': ['object'],
            'layer.ctx.dpr': ['number'],
            'layer.resize()': ['function'],
        });
    });

    it('a Rect and a Text on the main layer, a Rect on the hover layer — from 1 to 2: true; every layer at 2 (painter, layer, context), its backing store doubled, its CSS size kept; repainted at scale 2, the text included', () => {
        const {chart, painter} = zrenderScene(1);
        const zlevels = Object.keys(painter.getLayers());
        const canvases = Object.values(painter.getLayers()).map((layer) => layer.dom);
        const unmarked = canvases.map(() => 0);
        expect(layersAt(painter), 'precondition: every layer at 1').toEqual(zlevels.map((zlevel) => layerAt(zlevel, 1)));
        expect(drewAtScale(canvases, unmarked, 2), 'control: nothing was drawn at scale 2 before').toEqual(canvases.map(() => false));
        const marks = marksOf(canvases);
        const main = painter.getLayers()['0'].dom;

        expect(pixelRatio.setChartPixelRatio(chart, 2)).toBe(true);

        expect(painter.dpr).toBe(2);
        expect(layersAt(painter)).toEqual(zlevels.map((zlevel) => layerAt(zlevel, 2)));
        expect(
            Object.values(painter.getLayers()).every((layer, index) => layer.dom === canvases[index]),
            'the same canvas nodes',
        ).toBe(true);
        expect(drewAtScale(canvases, marks, 2), 'every layer, the hover one included, painted again at scale 2').toEqual(canvases.map(() => true));
        expect(scaleOfText(main, TITLE, marks[zlevels.indexOf('0')]), 'the text drawn again at scale 2').toBe('2,0,0,2');
        expect(debugMock.warn).not.toHaveBeenCalled();
    });

    it('at the density it already has: false, and nothing painted again; back to 1: true, every layer at 1 and painted at scale 1', () => {
        const {chart, painter} = zrenderScene(1);
        const zlevels = Object.keys(painter.getLayers());
        const canvases = Object.values(painter.getLayers()).map((layer) => layer.dom);
        expect(pixelRatio.setChartPixelRatio(chart, 2)).toBe(true);
        const settled = marksOf(canvases);

        expect(pixelRatio.setChartPixelRatio(chart, 2), 'already at 2').toBe(false);
        expect(marksOf(canvases), 'nothing painted again').toEqual(settled);

        expect(pixelRatio.setChartPixelRatio(chart, 1)).toBe(true);
        expect(layersAt(painter)).toEqual(zlevels.map((zlevel) => layerAt(zlevel, 1)));
        expect(drewAtScale(canvases, settled, 1), 'painted again at scale 1').toEqual(canvases.map(() => true));
    });

    it('a real ECharts chart on two layers: true; getDevicePixelRatio() follows; the same instance and canvases', () => {
        const element = hostElement();
        const chart = echarts.init(element, null, {renderer: 'canvas', devicePixelRatio: 1, width: WIDTH, height: HEIGHT});
        track(element, () => disposeOnce(chart));
        chart.setOption(SCENE);
        const canvases = canvasesOf(element);
        expect(canvases.length, 'barrier: two layers').toBeGreaterThanOrEqual(2);

        expect(pixelRatio.setChartPixelRatio(chart, 2)).toBe(true);

        expect(chart.getDevicePixelRatio()).toBe(2);
        expect(sizesOf(element)).toEqual(sizesAt(2, canvases.length));
        expect(canvasesOf(element).every((canvas, index) => canvas === canvases[index])).toBe(true);
        expect(echarts.getInstanceByDom(element)).toBe(chart);
    });
});

// =============================================================================
// Recognition: what it does not know, it leaves alone — and it never throws
// =============================================================================

/** A layer as zrender 6 has it, faked: a number `dpr`, a context, a `resize`. */
function fakeLayer(dpr = 1): {dpr: unknown; ctx?: unknown; resize?: unknown} {
    return {dpr, ctx: {dpr}, resize: vi.fn()};
}

/** A canvas painter as zrender 6 has it, faked, over `layers`; `overrides` breaks or replaces a member. */
function fakePainter(layers: Record<string, ReturnType<typeof fakeLayer>>, overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {getType: () => 'canvas', dpr: 1, getLayers: () => layers, refresh: vi.fn(), ...overrides};
}

/** A chart over `zr`, as `setChartPixelRatio` reads one. */
function fakeChart(zr: unknown, disposed = false): PixelRatioChart & {getZr: Mock} {
    return {getZr: vi.fn(() => zr), isDisposed: () => disposed, getWidth: () => WIDTH, getHeight: () => HEIGHT} as unknown as PixelRatioChart & {getZr: Mock};
}

/** A member that throws `message` when called. */
const throwing = (message: string) => (): never => {
    throw new Error(message);
};

/** Everything a refused call must not have changed: the densities, and whether anything was resized or repainted. */
function stateOf(painter: Record<string, unknown>, layers: Array<ReturnType<typeof fakeLayer>>): string {
    const calls = (fn: unknown): number => (vi.isMockFunction(fn) ? fn.mock.calls.length : 0);
    return JSON.stringify({
        painter: painter.dpr,
        refreshed: calls(painter.refresh),
        layers: layers.map((layer) => ({dpr: layer.dpr, ctx: (layer.ctx as {dpr?: unknown} | null | undefined)?.dpr ?? null, resized: calls(layer.resize)})),
    });
}

describe('setChartPixelRatio — recognises before it touches: what it does not know it leaves alone, with a debug warning; never a throw', () => {
    it('control — a painter that has every member, as zrender 6 has it: true, everything at 2, each layer resized to the chart’s size, refresh(true)', () => {
        const layers = {0: fakeLayer(), 100000: fakeLayer()};
        const painter = fakePainter(layers);

        expect(pixelRatio.setChartPixelRatio(fakeChart({painter}), 2)).toBe(true);

        expect(painter.dpr).toBe(2);
        expect(Object.values(layers).map((layer) => [layer.dpr, (layer.ctx as {dpr: number}).dpr])).toEqual([
            [2, 2],
            [2, 2],
        ]);
        expect(Object.values(layers).map((layer) => (layer.resize as Mock).mock.calls)).toEqual([[[WIDTH, HEIGHT]], [[WIDTH, HEIGHT]]]);
        expect((painter.refresh as Mock).mock.calls).toEqual([[true]]);
        expect(debugMock.warn).not.toHaveBeenCalled();
    });

    it('a layer without a context (ctx absent) is still recognised: true, its dpr set and the layer resized', () => {
        const bare = {dpr: 1, resize: vi.fn()};
        const painter = fakePainter({0: bare});

        expect(pixelRatio.setChartPixelRatio(fakeChart({painter}), 2)).toBe(true);
        expect([bare.dpr, bare.resize.mock.calls]).toEqual([2, [[WIDTH, HEIGHT]]]);
    });

    it.each([
        ['painter.getType()', 'no painter at all', () => ({layers: [fakeLayer()], zr: {}})],
        ['painter.getType()', 'a painter without getType', () => ({layers: [fakeLayer()], painter: {getType: undefined}})],
        ['painter.dpr', 'a painter whose dpr is not a number', () => ({layers: [fakeLayer()], painter: {dpr: '1'}})],
        ['painter.getLayers()', 'a painter without getLayers', () => ({layers: [fakeLayer()], painter: {getLayers: undefined}})],
        ['painter.getLayers()', 'a painter whose getLayers answers null', () => ({layers: [fakeLayer()], painter: {getLayers: () => null}})],
        ['painter.refresh()', 'a painter without refresh', () => ({layers: [fakeLayer()], painter: {refresh: undefined}})],
        ['layer.dpr', 'a second layer whose dpr is not a number', () => ({layers: [fakeLayer(), {...fakeLayer(), dpr: '1'}]})],
        ['layer.resize()', 'a second layer without resize', () => ({layers: [fakeLayer(), {...fakeLayer(), resize: undefined}]})],
        ['layer.ctx', 'a second layer whose ctx is not an object', () => ({layers: [fakeLayer(), {...fakeLayer(), ctx: 5}]})],
    ])('%s — %s: false, nothing changed, a warning naming it', (member, _, build) => {
        const built = build() as {layers: Array<ReturnType<typeof fakeLayer>>; painter?: Record<string, unknown>; zr?: unknown};
        const layers = Object.fromEntries(built.layers.map((layer, index) => [String(index), layer]));
        const painter = fakePainter(layers, built.painter);
        const zr = built.zr ?? {painter};
        const before = stateOf(painter, built.layers);

        expect(pixelRatio.setChartPixelRatio(fakeChart(zr), 2)).toBe(false);

        expect(stateOf(painter, built.layers), 'nothing touched, the valid layer included: recognised before anything is changed').toBe(before);
        expect(debugMock.warn).toHaveBeenCalledTimes(1);
        expect(debugMock.warn).toHaveBeenCalledWith('chartPixelRatio', expect.stringContaining(member));
    });

    it.each([
        ['painter.refresh(true) throws', () => fakePainter({0: fakeLayer()}, {refresh: throwing('refresh failed')})],
        ['layer.resize() throws', () => fakePainter({0: {...fakeLayer(), resize: throwing('resize failed')}})],
        ['painter.getType() throws', () => fakePainter({0: fakeLayer()}, {getType: throwing('getType failed')})],
    ])('%s: false, no exception escapes, a warning with the error', (_, build) => {
        const chart = fakeChart({painter: build()});
        let result: boolean | undefined;

        expect(() => {
            result = pixelRatio.setChartPixelRatio(chart, 2);
        }).not.toThrow();

        expect(result).toBe(false);
        expect(debugMock.warn).toHaveBeenCalledTimes(1);
        expect(debugMock.warn).toHaveBeenCalledWith('chartPixelRatio', expect.any(String), expect.any(Error));
    });

    it('getZr() throws: false, no exception escapes', () => {
        const chart = fakeChart(null);
        chart.getZr.mockImplementation(() => {
            throw new Error('getZr failed');
        });

        expect(() => pixelRatio.setChartPixelRatio(chart, 2)).not.toThrow();
        expect(pixelRatio.setChartPixelRatio(chart, 2)).toBe(false);
    });

    it('a disposed chart: false, not even read, no warning — the fake one and a real ECharts one', () => {
        const layers = [fakeLayer()];
        const painter = fakePainter({0: layers[0]});
        const fake = fakeChart({painter}, true);
        const before = stateOf(painter, layers);
        const element = hostElement();
        const real = echarts.init(element, null, {renderer: 'canvas', devicePixelRatio: 1, width: WIDTH, height: HEIGHT});
        real.setOption(SCENE);
        real.dispose();

        expect(pixelRatio.setChartPixelRatio(fake, 2)).toBe(false);
        expect(fake.getZr).not.toHaveBeenCalled();
        expect(stateOf(painter, layers)).toBe(before);
        expect(pixelRatio.setChartPixelRatio(real, 2)).toBe(false);
        expect(debugMock.warn).not.toHaveBeenCalled();
    });

    it('a chart already at the density, painter and every layer: false, nothing resized or repainted', () => {
        const layers = [fakeLayer(2), fakeLayer(2)];
        const painter = fakePainter({0: layers[0], 1: layers[1]}, {dpr: 2});
        const before = stateOf(painter, layers);

        expect(pixelRatio.setChartPixelRatio(fakeChart({painter}), 2)).toBe(false);
        expect(stateOf(painter, layers)).toBe(before);
        expect(debugMock.warn).not.toHaveBeenCalled();
    });

    it('a painter at the density with one layer that is not: true, that layer brought to it', () => {
        const layers = [fakeLayer(2), fakeLayer(1)];
        const painter = fakePainter({0: layers[0], 1: layers[1]}, {dpr: 2});

        expect(pixelRatio.setChartPixelRatio(fakeChart({painter}), 2)).toBe(true);
        expect(layers.map((layer) => layer.dpr)).toEqual([2, 2]);
    });

    it('an SVG chart (real ECharts): false, without a warning — an SVG draws at any density — and its painter untouched', () => {
        const element = hostElement();
        const chart = echarts.init(element, null, {renderer: 'svg', width: WIDTH, height: HEIGHT});
        track(element, () => disposeOnce(chart));
        chart.setOption(SCENE);
        const painter = painterOf(chart.getZr()) as PainterView & {refresh: (...args: unknown[]) => unknown};
        expect(painter.getType(), 'precondition: the SVG painter').toBe('svg');
        const refresh = vi.spyOn(painter, 'refresh');
        const dpr = painter.dpr;

        expect(pixelRatio.setChartPixelRatio(chart, 2)).toBe(false);

        expect(debugMock.warn).not.toHaveBeenCalled();
        expect(refresh).not.toHaveBeenCalled();
        expect(painter.dpr).toBe(dpr);
    });
});
