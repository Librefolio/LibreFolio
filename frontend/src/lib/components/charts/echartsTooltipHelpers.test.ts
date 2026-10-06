// @vitest-environment jsdom
/**
 * echartsTooltipHelpers — unit test (Vitest + jsdom).
 *
 * This module is the shared tooltip/lifecycle layer for every ECharts chart in
 * the app (Growth, AllocationHistory, LineChart, Candlestick, AllocationPie), so
 * a regression here is a regression on all of them at once. None of it draws:
 * the functions build HTML strings, compute tooltip coordinates, and wire touch
 * lifecycle — pure logic and DOM plumbing that a browser is not needed for. What
 * ECharts does with the strings and coordinates is its own concern and is not
 * asserted here (that would be measuring the absence of a canvas engine).
 *
 * jsdom rather than node because four of the functions read `window`/`navigator`
 * or attach real event listeners and timers; the pure builders are exercised in
 * the same file for locality.
 *
 * What it deliberately does NOT assert:
 *   - exact theme hex values as constants. `buildTooltipTheme`/`buildGridColors`
 *     select a palette from the `isDark` input, so the contract under test is
 *     "dark and light differ and both are well-formed colours", not the specific
 *     bytes, which are a styling decision free to change.
 *   - pixel positions against a layout. jsdom reports zeroes for every rect, so
 *     the position functions are driven with explicit `size`/`point` inputs and
 *     asserted on their clamping arithmetic, which is the part that has bugs.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {
    buildDot,
    buildFittedTooltipRow,
    buildGridColors,
    buildTooltipByThreshold,
    buildTooltipDivider,
    buildTooltipHeader,
    buildTooltipRow,
    buildTooltipTheme,
    buildTooltipTopN,
    fitTooltipToWidth,
    scheduleFirstRenderStabilityFix,
    setupTooltipAutoHide,
    tooltipPositionAboveFinger,
    tooltipPositionSide,
    type TooltipTheme,
} from './echartsTooltipHelpers';

const HEX = /^#[0-9a-f]{6}$/i;

const THEME: TooltipTheme = {bg: '#000', border: '#111', textColor: '#222', mutedColor: '#999'};

/** A `size` object shaped like the one ECharts passes to a `position` function. */
function size(contentW: number, contentH: number, viewW: number, viewH: number) {
    return {contentSize: [contentW, contentH] as [number, number], viewSize: [viewW, viewH] as [number, number]};
}

describe('theme palettes', () => {
    it('selects a distinct, well-formed palette per mode', () => {
        const dark = buildTooltipTheme(true);
        const light = buildTooltipTheme(false);

        for (const t of [dark, light]) {
            expect(t.bg).toMatch(HEX);
            expect(t.border).toMatch(HEX);
            expect(t.textColor).toMatch(HEX);
            expect(t.mutedColor).toMatch(HEX);
        }
        // The whole point of the input is that it switches the palette.
        expect(dark).not.toEqual(light);
        expect(dark.bg).not.toBe(light.bg);
    });

    it('grid colours also switch on the mode', () => {
        const dark = buildGridColors(true);
        const light = buildGridColors(false);
        expect(dark.textColor).toMatch(HEX);
        expect(dark.gridColor).toMatch(HEX);
        expect(dark).not.toEqual(light);
    });
});

describe('HTML fragment builders', () => {
    it('embeds the requested colour in a dot', () => {
        const html = buildDot('#abcdef');
        expect(html).toContain('#abcdef');
        expect(html).toContain('border-radius:50%');
    });

    it('carries the header text and colour through unchanged', () => {
        const html = buildTooltipHeader('2026-07-23', '#123456');
        expect(html).toContain('2026-07-23');
        expect(html).toContain('#123456');
    });

    it('includes a dot only when a colour is given', () => {
        const withDot = buildTooltipRow('Label', '<b>1</b>', '#ff0000');
        const withoutDot = buildTooltipRow('Label', '<b>1</b>');
        expect(withDot).toContain('#ff0000');
        expect(withDot).toContain('Label');
        expect(withDot).toContain('<b>1</b>');
        // No colour → no dot span at all, not an empty-coloured one.
        expect(withoutDot).not.toContain('border-radius:50%');
    });

    it('carries the border colour into a divider', () => {
        expect(buildTooltipDivider('#00ff00')).toContain('#00ff00');
    });
});

describe('buildTooltipTopN', () => {
    const id = (v: number) => String(v);

    it('is empty for no items', () => {
        expect(buildTooltipTopN([], 3, THEME, 'Other')).toBe('');
    });

    it('shows every item individually when there is nothing beyond topN', () => {
        const html = buildTooltipTopN(
            [
                {name: 'A', value: 10, color: '#a'},
                {name: 'B', value: 5, color: '#b'},
            ],
            3,
            THEME,
            'Other',
            id,
        );
        expect(html).toContain('A');
        expect(html).toContain('B');
        // No grouping row when nothing was grouped.
        expect(html).not.toContain('Other (');
    });

    it('sorts descending and groups the tail into a summed "Other (n)" row', () => {
        const html = buildTooltipTopN(
            [
                {name: 'small', value: 1, color: '#1'},
                {name: 'big', value: 100, color: '#2'},
                {name: 'mid', value: 40, color: '#3'},
                {name: 'tiny', value: 4, color: '#4'},
            ],
            2,
            THEME,
            'Other',
            id,
        );
        // Top 2 by value are big and mid; small+tiny (1+4=5) collapse into Other (2).
        expect(html).toContain('big');
        expect(html).toContain('mid');
        expect(html).toContain('Other (2)');
        expect(html).toContain('5'); // summed tail value, via the identity formatter
        // The tail names are not shown individually.
        expect(html).not.toContain('>small<');
        // Descending order: big appears before mid in the string.
        expect(html.indexOf('big')).toBeLessThan(html.indexOf('mid'));
        // The muted colour is used for the grouped row.
        expect(html).toContain(THEME.mutedColor);
    });

    it('applies the default percentage formatter when none is supplied', () => {
        const html = buildTooltipTopN([{name: 'A', value: 12.34, color: '#a'}], 3, THEME, 'Other');
        expect(html).toContain('12.3%');
    });
});

describe('buildTooltipByThreshold', () => {
    const id = (v: number) => String(v);

    it('is empty for no items', () => {
        expect(buildTooltipByThreshold([], 5, THEME, 'Remaining')).toBe('');
    });

    it('shows items at or above the threshold and groups the rest, summed and last', () => {
        const html = buildTooltipByThreshold(
            [
                {name: 'keep1', value: 8, color: '#1'},
                {name: 'drop1', value: 2, color: '#2'},
                {name: 'keep2', value: 5, color: '#3'},
                {name: 'drop2', value: 1, color: '#4'},
            ],
            5,
            THEME,
            'Remaining',
            id,
        );
        expect(html).toContain('keep1');
        expect(html).toContain('keep2');
        expect(html).toContain('Remaining (2)');
        expect(html).toContain('3'); // 2 + 1 grouped sum
        // Grouped row is last: its label comes after both kept items.
        expect(html.indexOf('keep1')).toBeLessThan(html.indexOf('Remaining ('));
        expect(html.indexOf('keep2')).toBeLessThan(html.indexOf('Remaining ('));
    });

    it('shows no grouped row when every item clears the threshold', () => {
        const html = buildTooltipByThreshold(
            [
                {name: 'a', value: 10, color: '#1'},
                {name: 'b', value: 6, color: '#2'},
            ],
            5,
            THEME,
            'Remaining',
            id,
        );
        expect(html).not.toContain('Remaining (');
    });
});

describe('tooltipPositionSide', () => {
    it('places the tooltip on the left when the cursor is on the right half', () => {
        // viewW 1000, cursor at x=800 (>500) → left side: x = 800 - 100 - 36 = 664
        const [x, y] = tooltipPositionSide([800, 200], null, null, null, size(100, 50, 1000, 400));
        expect(x).toBe(664);
        expect(y).toBe(8); // pinned near the top
    });

    it('places the tooltip on the right when the cursor is on the left half', () => {
        // cursor x=100 (<500) → right side: x = 100 + 36 = 136
        const [x] = tooltipPositionSide([100, 200], null, null, null, size(100, 50, 1000, 400));
        expect(x).toBe(136);
    });

    it('clamps a wide tooltip back inside the right edge', () => {
        // cursor on left → x = 40+36 = 76, but tooltip width 990 would overflow →
        // clamped to viewW - w - 8 = 1000 - 990 - 8 = 2.
        const [x] = tooltipPositionSide([40, 10], null, null, null, size(990, 50, 1000, 400));
        expect(x).toBe(2);
    });

    it('pins a tall tooltip up off the bottom edge', () => {
        // tooltip height 390 in a 400 view → y starts at 8 but 8+390 > 392, so it
        // is lifted to viewH - h - 8 = 400 - 390 - 8 = 2 (still non-negative).
        const [, y] = tooltipPositionSide([100, 10], null, null, null, size(100, 390, 1000, 400));
        expect(y).toBe(2);
    });

    it('never lets the top go negative for an over-tall tooltip', () => {
        // height 398 → lifted value would be -6, but the final guard floors it at 0.
        const [, y] = tooltipPositionSide([100, 10], null, null, null, size(100, 398, 1000, 400));
        expect(y).toBe(0);
    });
});

/** Force the desktop (no-touch) defaults; jsdom's own defaults report touch. */
function forceDesktop() {
    delete (window as unknown as {ontouchstart?: unknown}).ontouchstart;
    Object.defineProperty(navigator, 'maxTouchPoints', {value: 0, configurable: true});
}

describe('tooltipPositionAboveFinger', () => {
    beforeEach(forceDesktop);
    afterEach(forceDesktop);

    it('centres on the cursor and lifts by the desktop gap (30) above the finger', () => {
        // desktop (no touch): x = 400 - 100/2 = 350; y = 300 - 50 - 30 = 220
        const [x, y] = tooltipPositionAboveFinger([400, 300], null, null, null, size(100, 50, 1000, 800));
        expect(x).toBe(350);
        expect(y).toBe(220);
    });

    it('uses the larger touch gap (80) when the device reports touch', () => {
        (window as unknown as {ontouchstart?: unknown}).ontouchstart = null;
        // y = 300 - 50 - 80 = 170
        const [, y] = tooltipPositionAboveFinger([400, 300], null, null, null, size(100, 50, 1000, 800));
        expect(y).toBe(170);
    });

    it('clamps the top to 0 by default and leaves it free when clampTop is off', () => {
        const clamped = tooltipPositionAboveFinger([100, 10], null, null, null, size(100, 50, 1000, 800));
        expect(clamped[1]).toBe(0); // 10 - 50 - 30 = -70 → clamped to 0

        const free = tooltipPositionAboveFinger([100, 10], null, null, null, size(100, 50, 1000, 800), {clampTop: false});
        expect(free[1]).toBe(-70);
    });

    it('clamps horizontally to both viewport edges', () => {
        // far left → x would be negative, clamps to 8
        const left = tooltipPositionAboveFinger([0, 400], null, null, null, size(100, 50, 1000, 800));
        expect(left[0]).toBe(8);
        // far right → x + w overflows, clamps to viewW - w - 8 = 892
        const right = tooltipPositionAboveFinger([1000, 400], null, null, null, size(100, 50, 1000, 800));
        expect(right[0]).toBe(892);
    });
});

describe('setupTooltipAutoHide', () => {
    afterEach(() => vi.useRealTimers());

    it('hides the tip 3s after a touch ends, and a fresh touch cancels a pending hide', () => {
        vi.useFakeTimers();
        const container = document.createElement('div');
        const dispatchAction = vi.fn();
        const cleanup = setupTooltipAutoHide(container, () => ({dispatchAction}));

        container.dispatchEvent(new Event('touchend'));
        vi.advanceTimersByTime(2999);
        expect(dispatchAction).not.toHaveBeenCalled();
        vi.advanceTimersByTime(1);
        expect(dispatchAction).toHaveBeenCalledWith({type: 'hideTip'});

        // A new touchstart before the next timer fires must clear it.
        dispatchAction.mockClear();
        container.dispatchEvent(new Event('touchend'));
        container.dispatchEvent(new Event('touchstart'));
        vi.advanceTimersByTime(5000);
        expect(dispatchAction).not.toHaveBeenCalled();

        cleanup();
    });

    it('does nothing on touchend when there is no chart instance', () => {
        vi.useFakeTimers();
        const container = document.createElement('div');
        const cleanup = setupTooltipAutoHide(container, () => undefined);
        container.dispatchEvent(new Event('touchend'));
        // No throw, no timer scheduled that would blow up.
        expect(() => vi.advanceTimersByTime(5000)).not.toThrow();
        cleanup();
    });

    it('removes its listeners on cleanup', () => {
        vi.useFakeTimers();
        const container = document.createElement('div');
        const dispatchAction = vi.fn();
        const cleanup = setupTooltipAutoHide(container, () => ({dispatchAction}));
        cleanup();
        container.dispatchEvent(new Event('touchend'));
        vi.advanceTimersByTime(5000);
        expect(dispatchAction).not.toHaveBeenCalled();
    });
});

describe('scheduleFirstRenderStabilityFix', () => {
    afterEach(() => vi.unstubAllGlobals());

    it('performs an immediate corrective resize and notifies afterResize', () => {
        // Make rAF synchronous so the rect-stability poll runs to completion (jsdom
        // rects are constant zeroes, so it stabilises after two identical frames).
        vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
            cb(0);
            return 0;
        });
        const chart = {isDisposed: () => false, resize: vi.fn()} as never;
        const container = document.createElement('div');
        const afterResize = vi.fn();

        scheduleFirstRenderStabilityFix(chart, container, afterResize);

        expect((chart as unknown as {resize: ReturnType<typeof vi.fn>}).resize).toHaveBeenCalled();
        expect(afterResize).toHaveBeenCalledWith(chart);
    });

    it('never resizes a disposed chart', () => {
        vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
            cb(0);
            return 0;
        });
        const resize = vi.fn();
        const chart = {isDisposed: () => true, resize} as never;
        scheduleFirstRenderStabilityFix(chart, document.createElement('div'));
        expect(resize).not.toHaveBeenCalled();
    });

    it('re-resizes on window load when the document is still loading', () => {
        vi.stubGlobal('requestAnimationFrame', () => 0); // freeze the poll for this test
        Object.defineProperty(document, 'readyState', {value: 'loading', configurable: true});
        const resize = vi.fn();
        const chart = {isDisposed: () => false, resize} as never;

        scheduleFirstRenderStabilityFix(chart, document.createElement('div'));
        const immediate = resize.mock.calls.length;
        window.dispatchEvent(new Event('load'));
        expect(resize.mock.calls.length).toBeGreaterThan(immediate);

        Object.defineProperty(document, 'readyState', {value: 'complete', configurable: true});
    });

    it('re-resizes once fonts are ready', async () => {
        vi.stubGlobal('requestAnimationFrame', () => 0);
        Object.defineProperty(document, 'fonts', {value: {ready: Promise.resolve()}, configurable: true});
        const resize = vi.fn();
        const chart = {isDisposed: () => false, resize} as never;

        scheduleFirstRenderStabilityFix(chart, document.createElement('div'));
        const immediate = resize.mock.calls.length;
        await Promise.resolve(); // let the fonts.ready .then microtask run
        await Promise.resolve();
        expect(resize.mock.calls.length).toBeGreaterThan(immediate);

        delete (document as unknown as {fonts?: unknown}).fonts;
    });
});

// =============================================================================
// K step 16, item 1 — the price tooltip truncates its label, never its value
// =============================================================================

/**
 * The asset detail's price chart (PriceChartFull, line mode) writes each series as one line, `label: value`,
 * inside ECharts' tooltip box, which is `white-space: nowrap`. A long asset name made that box wider than the
 * chart at phone width, and the value was cut at the screen edge (measured by K on 06/10: a tooltip 362–386 px
 * wide on a chart 309 px wide, at a 390 px viewport).
 *
 * Approved cure (developer, 06/10): truncate, never wrap. Two helpers carry it, pinned here before they exist:
 *   - `buildFittedTooltipRow(labelHtml, valueHtml)`: one inline-level flex row, capped at the width of its line
 *     (`max-width: 100%`). Inline, because the tooltip joins its rows with `<br/>` and appends inline notes after
 *     them (the delta, "value at …", stale warnings): a block would add a blank line. Its label item shrinks and
 *     ellipsizes; its value item — the currency suffix travels with the value — never shrinks and never wraps;
 *   - `fitTooltipToWidth(html, maxWidthPx)`: the whole tooltip in a block frame capped at an integer width, with
 *     wrapping turned back on inside it, so that the cap can bind inside ECharts' nowrap box.
 * Both take HTML by contract: the caller escapes, the helpers pass their inputs through unchanged.
 *
 * The output is read through the HTML parser (an inert `<template>`), as a browser would build it: the tree,
 * and the declarations each box carries (jsdom's own CSS parser, so `min-width:0` reads `0px` however it is
 * written). The row's tags are not pinned — a flex item is a block whatever its tag — only what each box
 * declares. Whether Chromium then lays the row out as intended is the E2E's question
 * (`e2e/assets/asset-mobile-layout.spec.ts`, "Price chart tooltip at phone width").
 */
describe('buildFittedTooltipRow / fitTooltipToWidth — truncate the label, never the value (K step 16, item 1)', () => {
    /** A main-row label as PriceChartFull builds it: the crown, the type icon, the name cut at 30 characters. */
    const LABEL_HTML =
        '<span style="display:inline-block;width:16px;text-align:center;margin-right:2px;vertical-align:middle">👑</span>' +
        '<img src="/asset-types/etf.png" alt="" style="width:14px;height:14px" />' +
        '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="Xtrackers MSCI World Industri…">Xtrackers MSCI World Industri…</span>';
    /** Its value part after the cure: the currency suffix, then the value. */
    const VALUE_HTML = ' <span style="font-size:10px">(🇪🇺 EUR)</span>: 66.6800';

    /** The nodes a browser builds from `html`, through an inert `<template>`: nothing runs, nothing loads. */
    function parse(html: string): DocumentFragment {
        const template = document.createElement('template');
        template.innerHTML = html;
        return template.content;
    }

    /** `html` as the browser serialises it once parsed: compares content without caring about quoting or `<br/>`. */
    function normalised(html: string): string {
        const template = document.createElement('template');
        template.innerHTML = html;
        return template.innerHTML;
    }

    /** The single element `html` is made of, with nothing — not even whitespace — beside it. */
    function soleElement(html: string): HTMLElement {
        const fragment = parse(html);
        expect(fragment.childNodes.length, `one root node and nothing beside it: ${html}`).toBe(1);
        const root = fragment.firstElementChild;
        if (!(root instanceof HTMLElement)) throw new Error(`the root is not an element: ${html}`);
        return root;
    }

    /** The row and its two items, in order: the label first, the value second. Tags are free; the declarations are the contract. */
    function rowParts(html: string): {row: HTMLElement; label: HTMLElement; value: HTMLElement} {
        const row = soleElement(html);
        expect(row.childNodes.length, `the row holds exactly its two items, no text beside them: ${row.innerHTML}`).toBe(2);
        const [label, value] = Array.from(row.children);
        if (!(label instanceof HTMLElement) || !(value instanceof HTMLElement)) throw new Error(`the row's children are not elements: ${row.innerHTML}`);
        return {row, label, value};
    }

    describe('buildFittedTooltipRow', () => {
        it('is one inline-level flex row, capped at the width of its line, that never wraps', () => {
            const {row} = rowParts(buildFittedTooltipRow(LABEL_HTML, VALUE_HTML));
            // Inline-level: rows are joined with <br/> and notes follow them on the same line — a block would add a blank line.
            expect(row.style.display).toBe('inline-flex');
            // Capped at its line: the row never makes the tooltip wider than the frame that holds it.
            expect(row.style.maxWidth).toBe('100%');
            // Truncate, never wrap: nothing may move the value onto a line of its own.
            expect(['', 'nowrap'], `flex-wrap is "${row.style.flexWrap}"`).toContain(row.style.flexWrap);
        });

        it('lets the label shrink below its content and ellipsize what no longer fits, on one line', () => {
            const {label} = rowParts(buildFittedTooltipRow(LABEL_HTML, VALUE_HTML));
            expect(label.style.minWidth, 'min-width: 0 — otherwise a flex item never shrinks below its content').toBe('0px');
            expect(label.style.overflow).toBe('hidden');
            expect(label.style.textOverflow).toBe('ellipsis');
            expect(label.style.whiteSpace).toBe('nowrap');
            // Shrinking is the flex default (flex-shrink: 1): the label must not opt out of it.
            expect(label.style.flexShrink, 'the label keeps the default flex-shrink').not.toBe('0');
        });

        it('never shrinks, wraps or clips the value: the currency suffix and the number stay whole', () => {
            const {value} = rowParts(buildFittedTooltipRow(LABEL_HTML, VALUE_HTML));
            expect(value.style.flexShrink).toBe('0');
            expect(value.style.whiteSpace).toBe('nowrap');
            expect(['', 'visible'], `the value is never clipped (overflow is "${value.style.overflow}")`).toContain(value.style.overflow);
            expect(value.style.textOverflow, 'the value is never ellipsized').toBe('');
        });

        it('carries both inputs verbatim: the label HTML inside the label item, the value HTML inside the value item', () => {
            const html = buildFittedTooltipRow(LABEL_HTML, VALUE_HTML);
            expect(html).toContain(LABEL_HTML);
            expect(html).toContain(VALUE_HTML);
            expect(html.indexOf(LABEL_HTML), 'the label comes first').toBeLessThan(html.indexOf(VALUE_HTML));
            const {label, value} = rowParts(html);
            expect(label.innerHTML).toBe(normalised(LABEL_HTML));
            expect(value.innerHTML).toBe(normalised(VALUE_HTML));
        });

        it("passes hostile HTML through untouched — escaping is the caller's job, not the helper's: both arguments are HTML by contract", () => {
            const hostileLabel = `<b onclick="steal()">Tom & Jerry</b> "quoted" 'single' &lt;already escaped&gt;`;
            const hostileValue = `<i data-x="1 & 2">1 234,50 €</i> & more`;
            const html = buildFittedTooltipRow(hostileLabel, hostileValue);
            // Exactly once each, byte for byte: neither escaped (`&` → `&amp;`, `<` → `&lt;`) nor sanitised.
            expect(html.split(hostileLabel).length - 1, 'the label appears once, unchanged').toBe(1);
            expect(html.split(hostileValue).length - 1, 'the value appears once, unchanged').toBe(1);
            for (const escaped of ['&amp;', '&quot;', '&#39;', '&#x27;']) {
                expect(html, `the helper escaped something itself: found "${escaped}"`).not.toContain(escaped);
            }
            // The caller's markup stays markup, handler included: the helper is no sanitiser either.
            const {label, value} = rowParts(html);
            expect(label.querySelector('b')?.getAttribute('onclick')).toBe('steal()');
            expect(value.querySelector('i')?.getAttribute('data-x')).toBe('1 & 2');
        });
    });

    describe('fitTooltipToWidth', () => {
        it.each([
            [277.9, '277px'],
            [300, '300px'],
            [12.0001, '12px'],
            [0, '0px'],
            [-0.5, '0px'],
            [-40, '0px'],
        ])('caps the frame at max-width %s → %s: floored to an integer, never negative', (maxWidthPx, expected) => {
            const frame = soleElement(fitTooltipToWidth('<b>66.6800</b>', maxWidthPx));
            expect(frame.tagName, 'the frame is a block: a div').toBe('DIV');
            expect(frame.style.maxWidth).toBe(expected);
        });

        it("turns wrapping back on inside the frame: ECharts' tooltip box is white-space: nowrap, where no cap could bind", () => {
            const frame = soleElement(fitTooltipToWidth('<b>66.6800</b>', 277));
            expect(frame.style.whiteSpace).toBe('normal');
        });

        it('wraps the whole tooltip verbatim: header, rows, inline notes and breaks, in order, inside the one frame', () => {
            const tooltip =
                '<strong>2026-10-05</strong><br/>' +
                '<span style="display:inline-flex;align-items:baseline;max-width:100%;min-width:0;vertical-align:bottom"><span>row</span><span>: 66.6800</span></span>' +
                ' <span style="font-size:10px">(Δ +0.3700 / +0.60%)</span>' +
                '<br/><span style="color:#f59e0b;font-size:11px">⚠ 2</span>';
            const html = fitTooltipToWidth(tooltip, 277);
            expect(html).toContain(tooltip);
            const frame = soleElement(html);
            expect(frame.innerHTML).toBe(normalised(tooltip));
        });

        it("passes hostile HTML through untouched — escaping is the caller's job, not the helper's", () => {
            const hostile = `<b onclick="steal()">Tom & Jerry</b> "quoted" 'single' &lt;already escaped&gt;`;
            const html = fitTooltipToWidth(hostile, 200);
            expect(html.split(hostile).length - 1, 'the tooltip appears once, unchanged').toBe(1);
            for (const escaped of ['&amp;', '&quot;', '&#39;', '&#x27;']) {
                expect(html, `the helper escaped something itself: found "${escaped}"`).not.toContain(escaped);
            }
        });
    });
});
