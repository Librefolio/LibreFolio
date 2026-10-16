// @vitest-environment jsdom
/**
 * chartFont.load.test.ts — K-13: the flag face is asked for before a chart can paint, and a chart that painted before it
 * arrived paints again once it is in.
 *
 * ## What it protects (K-13)
 *
 * ECharts paints its text on a canvas, once, with the faces loaded at that moment. 'LF Flags' (`static/lf-flags.css`)
 * holds the flags and nothing else, `unicode-range: U+1F1E6-1F1FF`, and a browser fetches such a face only for text of
 * the page that needs it — canvas text does not count. Left alone, no chart would ever make the browser fetch it, and a
 * flag painted before the face is in stays two letters until the chart paints again. So `chartFont.ts`:
 * - asks for the face itself, once, when the module loads: `document.fonts.load` with the 'LF Flags' family and a flag.
 *   Every chart imports the module before it can paint, so the request is ahead of the first paint;
 * - keeps that request: `chartFontReady()` hands back the same promise every time and never rejects — a face that fails
 *   to load leaves the system's fallback, as before K-13 — and resolves at once where nothing can load a font;
 * - says whether the face is in, `chartFontLoaded()`, by asking `document.fonts.check` the question it gave `load`;
 * - lets no throw of `document.fonts` out: `load` is called while the module loads, so a `load` that throws would fail
 *   the import of every chart module — the request resolves instead; a `check` that throws reads as a face already in,
 *   so no repaint waits on it;
 * and `scheduleFirstRenderStabilityFix` (`echartsTooltipHelpers.ts`), which a chart runs after its first full
 * `setOption`, resizes the chart once more when the face arrives if it was not in at the first paint: a resize repaints.
 *
 * The coordinator's condition on K-13 is that the request before the first draw is covered by a test: that is (e).
 *
 * ## How
 *
 * jsdom has no `document.fonts`. Each case installs a fake as an own property of `document`, removed after it: its
 * `load` answers a promise the case settles itself when it chooses (a deferred), or a face that is in at once; its
 * `check` answers what the case decides. The module asks for the face when it is evaluated and keeps the request, so the
 * module registry is reset before every case, and the case imports the module after installing its fake.
 *
 * - (a)–(d) import `chartFont.ts` alone.
 * - (e) mounts a real chart, `SemiDonutChart`, with ECharts replaced by a recorder (as in `SemiDonutChart.test.ts`) that
 *   writes into the same ordered log as the fake `load`. The donut runs its first-render fix after its first
 *   `setOption`, so a face asked for only when a chart asks would land after the first draw: a control proves the log
 *   tells that order apart. The test harness is imported after the reset too, so `render` and the component share one
 *   Svelte runtime, and the harness's own `cleanup` unmounts what it mounted.
 * - (f) calls `scheduleFirstRenderStabilityFix` on a fake chart, its other signals held still: `requestAnimationFrame`
 *   never calls back (the rect poll adds nothing), `fonts.ready` is a resolved promise whose resize lands before the
 *   count, and between the counts only microtasks run — no frame, timer or window `load` can slip in. Each case asserts
 *   the delta the face adds, never an absolute count.
 * - (g) installs a `load` or a `check` that throws, and proves first that it did throw — a fake nobody called would make
 *   every assertion after it trivially true — then that the throw went no further: the import succeeds,
 *   `chartFontReady()` resolves, `chartFontLoaded()` answers true, and the first-render fix neither throws nor adds a
 *   resize when the face arrives.
 *
 * Registered in chart-safety-unit (scripts/test_runner/_frontend_portfolio.py).
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import type {ECharts} from 'echarts';

/**
 * The ECharts stand-in of (e): it answers what the donut and its helpers call on an instance (`attachChartReady` → `on`,
 * `scheduleFirstRenderStabilityFix` → `isDisposed`/`resize`, the teardown → `dispose`) and writes `echarts.init`,
 * `setOption` and `resize` into the log the fake `document.fonts.load` writes into too.
 */
const {log, echartsModule} = vi.hoisted(() => {
    /** One ordered log of the face's requests and the chart's calls: which came first is the subject of (e). */
    const log: string[] = [];

    function createFakeChart(dom: unknown) {
        let disposed = false;
        log.push('echarts.init');
        return {
            setOption: () => {
                log.push('setOption');
            },
            getDom: () => dom,
            on: () => {},
            off: () => {},
            resize: () => {
                log.push('resize');
            },
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
    }

    return {log, echartsModule: {init: (dom: unknown) => createFakeChart(dom)}};
});

vi.mock('echarts', () => echartsModule);

type ChartFontModule = typeof import('./chartFont');

// =============================================================================
// Fixtures
// =============================================================================

/** The face every chart's text is asked to draw its flags with. */
const FLAG_FACE = 'LF Flags';

/** The regional indicators: two of them make a flag. */
const REGIONAL_INDICATOR_FIRST = 0x1f1e6;
const REGIONAL_INDICATOR_LAST = 0x1f1ff;

/** Three owners, no avatar — an image never loads in jsdom — and the label of the share still available: the donut's smallest real draw. */
const OWNERS = [
    {name: 'Alba', percentage: 40, avatarUrl: null},
    {name: 'Bruno', percentage: 30, avatarUrl: null},
    {name: 'Carla', percentage: 20, avatarUrl: null},
];
const AVAILABLE = 'Still available';

// =============================================================================
// The fake document.fonts, and promises the case settles
// =============================================================================

type Load = (font: string, text?: string) => Promise<unknown[]>;
type Check = (font: string, text?: string) => boolean;

/** The part of `FontFaceSet` the code reads: `load` and `check` as spies, `ready` an already resolved promise. */
interface FakeFonts {
    ready: Promise<void>;
    load: Mock<Load>;
    check: Mock<Check>;
}

/**
 * A fake `document.fonts`, installed as an own property of `document`. Its `load` writes `fonts.load` into the log, then
 * answers what `load` answers — by default a face that is in at once. Its `check` answers `false` by default: the face is
 * not in yet, as on a cold start.
 */
function installFonts({load = () => Promise.resolve([]), check = () => false}: {load?: Load; check?: Check} = {}): FakeFonts {
    const fonts: FakeFonts = {
        ready: Promise.resolve(),
        load: vi.fn<Load>((font, text) => {
            log.push('fonts.load');
            return load(font, text);
        }),
        check: vi.fn<Check>(check),
    };
    Object.defineProperty(document, 'fonts', {configurable: true, value: fonts});
    return fonts;
}

/** A promise the case settles itself, when it chooses. */
interface Deferred<T> {
    promise: Promise<T>;
    resolve: (value: T) => void;
    reject: (reason: unknown) => void;
}

function deferred<T>(): Deferred<T> {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((onResolve, onReject) => {
        resolve = onResolve;
        reject = onReject;
    });
    return {promise, resolve, reject};
}

type PromiseState = 'pending' | 'resolved' | 'rejected';

/** Where a promise stands, readable without awaiting it. */
function track(promise: Promise<unknown>): {state: PromiseState} {
    const status: {state: PromiseState} = {state: 'pending'};
    promise.then(
        () => {
            status.state = 'resolved';
        },
        () => {
            status.state = 'rejected';
        },
    );
    return status;
}

/** Lets every pending promise reaction run: microtask turns only, more than any chain here needs — no timer, no frame. */
async function flushMicrotasks(turns = 10): Promise<void> {
    for (let turn = 0; turn < turns; turn++) await Promise.resolve();
}

/** chartFont imported with `fonts` in place, and the font and text of the one request its loading made. */
async function importChartFont(fonts: FakeFonts): Promise<{chartFont: ChartFontModule; font: string; text: string | undefined}> {
    const chartFont = await import('./chartFont');
    expect(fonts.load, 'importing chartFont did not call document.fonts.load exactly once').toHaveBeenCalledTimes(1);
    const [font, text] = fonts.load.mock.calls[0];
    return {chartFont, font, text};
}

// =============================================================================
// Reading the request
// =============================================================================

/** A family without its quotes. */
const unquote = (family: string): string => family.trim().replace(/^(['"])([\s\S]*)\1$/, '$2');

/** A family list as the CSSOM serialises it (`"LF Flags", sans-serif`), one family per entry, quotes gone. */
function splitFamilies(value: string): string[] {
    return (value.match(/"[^"]*"|'[^']*'|[^,]+/g) ?? []).map(unquote).filter((family) => family !== '');
}

/**
 * The families of a CSS `font` shorthand, read by the CSSOM: the grammar `document.fonts.load` reads its first argument
 * with. `null` when the CSSOM rejects the shorthand — the real API would then reject the request, `chartFontReady` would
 * swallow the rejection, and the face would never be asked for.
 */
function familiesOfFont(font: string): string[] | null {
    const probe = document.createElement('span');
    probe.style.font = font;
    return probe.style.font === '' ? null : splitFamilies(probe.style.fontFamily);
}

const hex = (codePoint: number): string => `U+${codePoint.toString(16).toUpperCase()}`;

// =============================================================================
// Lifecycle
// =============================================================================

/** The `cleanup` of the harness a case imported after the reset: only it knows the components that case mounted. */
let cleanupMounted: (() => void) | undefined;

beforeEach(() => {
    log.length = 0;
    // Every case evaluates the modules afresh, after installing its own document.fonts.
    vi.resetModules();
});

afterEach(() => {
    cleanupMounted?.();
    cleanupMounted = undefined;
    vi.doUnmock('./chartFont');
    vi.unstubAllGlobals();
    delete (document as unknown as {fonts?: unknown}).fonts;
});

// =============================================================================
// (a) The request, made when the module loads
// =============================================================================

describe('chartFont — the face is asked for when the module loads (K-13)', () => {
    it('importing the module calls document.fonts.load exactly once, before any of its functions is called', async () => {
        const fonts = installFonts();

        await import('./chartFont');

        expect(fonts.load).toHaveBeenCalledTimes(1);
    });

    it("the font names the family 'LF Flags', in a font shorthand the CSSOM accepts", async () => {
        const {font} = await importChartFont(installFonts());

        const families = familiesOfFont(font);
        expect(families, `«${font}» is no font shorthand the CSSOM accepts: document.fonts.load would reject it, and chartFontReady swallows the rejection`).not.toBeNull();
        expect(families, `the families of «${font}»`).toContain(FLAG_FACE);
    });

    it('the text is not empty and is made only of regional indicators, U+1F1E6–U+1F1FF: the characters the face holds', async () => {
        const {text = ''} = await importChartFont(installFonts());

        const codePoints = [...text].map((character) => character.codePointAt(0) ?? 0);
        expect(codePoints.length, 'the sample text is empty: the request would ask for no face').toBeGreaterThan(0);
        expect(codePoints.filter((codePoint) => codePoint < REGIONAL_INDICATOR_FIRST || codePoint > REGIONAL_INDICATOR_LAST).map(hex), `code points of «${text}» that are no regional indicator`).toEqual([]);
    });
});

// =============================================================================
// (b) One request, kept
// =============================================================================

describe('chartFontReady — one request, kept (K-13)', () => {
    it('called again and again it hands back the same promise, also once the face is in, and load is never called again', async () => {
        const fonts = installFonts();
        const {chartFont} = await importChartFont(fonts);

        const promises = [chartFont.chartFontReady(), chartFont.chartFontReady(), chartFont.chartFontReady()];
        expect(new Set(promises).size, 'chartFontReady handed back different promises').toBe(1);
        await promises[0];
        expect(chartFont.chartFontReady(), 'once the face was in, chartFontReady handed back another promise').toBe(promises[0]);

        expect(fonts.load, 'chartFontReady asked for the face again').toHaveBeenCalledTimes(1);
    });
});

// =============================================================================
// (c) Never rejects
// =============================================================================

describe('chartFontReady — never rejects (K-13)', () => {
    it('resolves once load resolves, and not before', async () => {
        const face = deferred<unknown[]>();
        const {chartFont} = await importChartFont(installFonts({load: () => face.promise}));
        const ready = track(chartFont.chartFontReady());

        await flushMicrotasks();
        expect(ready.state, 'chartFontReady settled while the face was still loading').toBe('pending');

        face.resolve([]);
        await expect(chartFont.chartFontReady()).resolves.toBeUndefined();
        expect(ready.state).toBe('resolved');
    });

    it('resolves when load rejects: a face that fails to load leaves the fallback, and no rejection escapes', async () => {
        const face = deferred<unknown[]>();
        const {chartFont} = await importChartFont(installFonts({load: () => face.promise}));
        const ready = track(chartFont.chartFontReady());

        await flushMicrotasks();
        expect(ready.state, 'chartFontReady settled while the face was still loading').toBe('pending');

        face.reject(new DOMException('A network error occurred.', 'NetworkError'));
        await expect(chartFont.chartFontReady()).resolves.toBeUndefined();
        expect(ready.state).toBe('resolved');
    });

    it('with no document.fonts it resolves at once, and chartFontLoaded() is true', async () => {
        expect('fonts' in document, 'premise: jsdom has no document.fonts, and no case left its fake behind').toBe(false);
        const chartFont = await import('./chartFont');

        const ready = track(chartFont.chartFontReady());
        await Promise.resolve();

        expect(ready.state, 'chartFontReady was not resolved within one microtask turn: it waited on something').toBe('resolved');
        expect(chartFont.chartFontLoaded()).toBe(true);
    });
});

// =============================================================================
// (d) chartFontLoaded follows document.fonts.check
// =============================================================================

describe('chartFontLoaded — what document.fonts.check answers (K-13)', () => {
    it('returns what check returns, asked with the font and the sample the request was made with', async () => {
        let checkAnswer = false;
        const fonts = installFonts({check: () => checkAnswer});
        const {chartFont, font, text} = await importChartFont(fonts);

        expect(chartFont.chartFontLoaded(), 'check answered false').toBe(false);
        checkAnswer = true;
        expect(chartFont.chartFontLoaded(), 'check answered true').toBe(true);

        expect(fonts.check.mock.calls, 'check was not asked the question load was asked').toEqual([
            [font, text],
            [font, text],
        ]);
    });
});

// =============================================================================
// (e) A real chart: the request comes before its first draw
// =============================================================================

/**
 * The control's foil: chartFont without the request at load. The face is asked for only when a chart asks — for the
 * donut, its first-render fix, after the first `setOption`. The same font, sample and answers otherwise.
 */
function chartFontAskingOnDemand(): Partial<ChartFontModule> {
    const font = "16px 'LF Flags'";
    const sample = '\u{1F1FA}\u{1F1F8}';
    let request: Promise<void> | undefined;
    return {
        CHART_FONT_FAMILY: "'LF Flags', sans-serif",
        CHART_INIT_THEME: {textStyle: {fontFamily: "'LF Flags', sans-serif"}},
        chartFontReady: () =>
            (request ??= document.fonts.load(font, sample).then(
                () => undefined,
                () => undefined,
            )),
        chartFontLoaded: () => document.fonts.check(font, sample),
    };
}

/** The test harness, imported after the reset like the chart so that both run on one Svelte runtime; its `cleanup` is kept for `afterEach`. */
async function importHarness(): Promise<typeof import('$test/component')> {
    const harness = await import('$test/component');
    cleanupMounted = harness.cleanup;
    return harness;
}

/** The donut mounted with `harness`, and its first draw awaited. */
async function drawDonut(harness: typeof import('$test/component'), SemiDonutChart: typeof import('./SemiDonutChart.svelte').default): Promise<void> {
    harness.render(SemiDonutChart, {props: {data: OWNERS, availableLabel: AVAILABLE}});
    await harness.waitFor(() => expect(log, 'barrier: the donut never drew').toContain('setOption'), {timeout: 5_000});
}

/** What the log holds before the first `setOption`. */
const beforeFirstDraw = (): string[] => log.slice(0, log.indexOf('setOption'));

describe('a real chart asks for the face before its first draw (K-13 — the coordinator’s condition)', {timeout: 20_000}, () => {
    it('SemiDonutChart: the face is asked for when the chart module loads, before its first setOption — and only then', async () => {
        const fonts = installFonts();
        const harness = await importHarness();
        expect(log, 'premise: the test harness asks for no face').toEqual([]);

        const {default: SemiDonutChart} = await import('./SemiDonutChart.svelte');
        expect(log, 'importing the chart did not ask for the face, or did something else as well').toEqual(['fonts.load']);

        await drawDonut(harness, SemiDonutChart);

        expect(beforeFirstDraw(), `the face was not asked for before the first draw: ${log.join(' → ')}`).toContain('fonts.load');
        expect(fonts.load, `the face was asked for more than once: ${log.join(' → ')}`).toHaveBeenCalledTimes(1);
    });

    it('control — the log tells the order apart: with a chartFont that asks only when a chart asks, the request lands after the first setOption', async () => {
        installFonts();
        vi.doMock('./chartFont', chartFontAskingOnDemand);
        const harness = await importHarness();

        const {default: SemiDonutChart} = await import('./SemiDonutChart.svelte');
        expect(log, 'premise: the foil asks for nothing when it loads').toEqual([]);

        await drawDonut(harness, SemiDonutChart);

        expect(log, 'barrier: the donut’s first-render fix asked for the face').toContain('fonts.load');
        expect(beforeFirstDraw(), `the foil’s request came before the first draw: the log cannot tell the orders apart — ${log.join(' → ')}`).not.toContain('fonts.load');
    });
});

// =============================================================================
// (f) The repaint once the face arrives
// =============================================================================

/** A chart as `scheduleFirstRenderStabilityFix` uses one: it resizes, and knows whether it was disposed. */
interface FakeChart {
    resize: Mock<() => void>;
    isDisposed: () => boolean;
    dispose: () => void;
}

function fakeChart(): FakeChart {
    let disposed = false;
    return {
        resize: vi.fn<() => void>(),
        isDisposed: () => disposed,
        dispose: () => {
            disposed = true;
        },
    };
}

interface Counts {
    resize: number;
    afterResize: number;
}

/** A first-render fix scheduled on a fake chart while the face is still loading, its resizes counted once the other signals are done. */
interface Scheduled {
    face: Deferred<unknown[]>;
    fonts: FakeFonts;
    chart: FakeChart;
    afterResize: Mock<(chart: ECharts) => void>;
    before: Counts;
    chartFontReady: ChartFontModule['chartFontReady'];
}

function countsOf(chart: FakeChart, afterResize: Scheduled['afterResize']): Counts {
    return {resize: chart.resize.mock.calls.length, afterResize: afterResize.mock.calls.length};
}

/** `check` answering that the face is not in yet, as on a cold start, or that it is already in. */
const faceNotIn: Check = () => false;
const faceIn: Check = () => true;

/**
 * `scheduleFirstRenderStabilityFix` called on a fake chart, with the face still loading (a deferred) and `check` as
 * given. The counts are taken once the immediate resize and the one of `fonts.ready` have landed, and are proved
 * settled: the same after a second flush.
 */
async function scheduled(check: Check): Promise<Scheduled> {
    const face = deferred<unknown[]>();
    const fonts = installFonts({load: () => face.promise, check});
    // The rect poll's frames never come: its resize is not in the count.
    vi.stubGlobal('requestAnimationFrame', () => 0);
    const {scheduleFirstRenderStabilityFix} = await import('./echartsTooltipHelpers');
    const {chartFontReady} = await import('./chartFont');
    expect(fonts.load, 'premise: the face is asked for once, when the modules load').toHaveBeenCalledTimes(1);

    const chart = fakeChart();
    const afterResize = vi.fn<(chart: ECharts) => void>();
    expect(() => scheduleFirstRenderStabilityFix(chart as unknown as ECharts, document.createElement('div'), afterResize), 'scheduleFirstRenderStabilityFix threw: the chart that called it would stop after its first draw').not.toThrow();

    await flushMicrotasks();
    const before = countsOf(chart, afterResize);
    await flushMicrotasks();
    expect(countsOf(chart, afterResize), 'barrier: the other signals still resize the chart, so the face’s delta would blur').toEqual(before);

    return {face, fonts, chart, afterResize, before, chartFontReady};
}

/** The face arrives: `load` resolves, and every reaction to it runs. */
async function faceArrives({face, chartFontReady}: Scheduled): Promise<void> {
    face.resolve([]);
    await chartFontReady();
    await flushMicrotasks();
}

/** What the face's arrival added to the counts. */
function delta({chart, afterResize, before}: Scheduled): Counts {
    const now = countsOf(chart, afterResize);
    return {resize: now.resize - before.resize, afterResize: now.afterResize - before.afterResize};
}

describe('scheduleFirstRenderStabilityFix — a chart that painted before the face arrived paints again once it is in (K-13)', {timeout: 20_000}, () => {
    it('the face not in at the first paint (check false): exactly one more resize when it arrives, handed to afterResize', async () => {
        const fix = await scheduled(faceNotIn);

        await faceArrives(fix);

        expect(delta(fix), 'what the face added: one resize, one afterResize').toEqual({resize: 1, afterResize: 1});
    });

    it('the face already in at the first paint (check true): its arrival adds no resize', async () => {
        const fix = await scheduled(faceIn);
        expect(fix.fonts.check, 'premise: the fix asked whether the face was in').toHaveBeenCalled();

        await faceArrives(fix);

        expect(delta(fix), 'what the face added').toEqual({resize: 0, afterResize: 0});
    });

    it('a chart disposed before the face arrives is not resized', async () => {
        const fix = await scheduled(faceNotIn);
        fix.chart.dispose();

        await faceArrives(fix);

        expect(delta(fix), 'what the face added to a disposed chart').toEqual({resize: 0, afterResize: 0});
    });
});

// =============================================================================
// (g) The guards: a document.fonts that throws breaks nothing
// =============================================================================

/**
 * A `load` that throws at once instead of answering a promise. The font loading API rejects rather than throws, but a
 * polyfill or a broken environment may not: the request runs while the module loads, so this throw would fail the import
 * of every chart module.
 */
const loadThrows: Load = () => {
    throw new TypeError('the fake document.fonts.load threw synchronously');
};

/** A `check` that throws instead of answering. */
const checkThrows: Check = () => {
    throw new TypeError('the fake document.fonts.check threw');
};

/** How each call of a spy ended: `return`, or `throw` — the proof that a throwing fake was called and did throw. */
function outcomes(spy: {mock: {results: ReadonlyArray<{type: string}>}}): string[] {
    return spy.mock.results.map((result) => result.type);
}

describe('chartFont — a document.fonts that throws breaks nothing (K-13)', {timeout: 20_000}, () => {
    it('a load that throws at once: importing the module does not throw, and chartFontReady() resolves', async () => {
        const fonts = installFonts({load: loadThrows});

        const imported = import('./chartFont');
        await expect(imported, 'importing chartFont threw: a document.fonts.load that throws would fail the import of every chart module').resolves.toBeTruthy();
        expect(outcomes(fonts.load), 'premise: the import called load once, and load threw').toEqual(['throw']);

        const chartFont = await imported;
        const ready = track(chartFont.chartFontReady());
        await flushMicrotasks();
        expect(ready.state, 'chartFontReady did not resolve after a load that threw').toBe('resolved');
    });

    it('a check that throws: chartFontLoaded() lets nothing out, and answers true', async () => {
        const fonts = installFonts({check: checkThrows});
        const chartFont = await import('./chartFont');

        expect(() => chartFont.chartFontLoaded(), 'chartFontLoaded let the throw of check out').not.toThrow();
        expect(outcomes(fonts.check), 'premise: chartFontLoaded asked check, and check threw').toContain('throw');
        expect(chartFont.chartFontLoaded(), 'after a check that threw, chartFontLoaded does not answer that the face is in').toBe(true);
    });

    it('a check that throws: scheduleFirstRenderStabilityFix does not throw, and the face’s arrival adds no resize — the repaint path is skipped', async () => {
        const fix = await scheduled(checkThrows);
        expect(outcomes(fix.fonts.check), 'premise: the fix asked check, and check threw').toContain('throw');

        await faceArrives(fix);

        expect(delta(fix), 'what the face added').toEqual({resize: 0, afterResize: 0});
    });
});
