/**
 * Designer Lab — L3, the ECharts options (`engine/charts.ts`): the pure mapping behind the `setOption` wrapper
 * (`mapChartOption`) and the patch sent to the charts already on screen (`chartPatch`).
 *
 * Only the pure exports are exercised. Importing the module does not load ECharts — `echarts` is a type import there
 * and the library is fetched by `applyCharts` alone — and the mock below is a tripwire for that: any import of
 * `echarts` fails this file. No plan is ever installed in the engine here (`applyCharts` would need ECharts and a
 * DOM), so a wrapped formatter returns what the app's function returns; the E2E specs cover the live engine.
 *
 * Expected canvas strings are written by hand: `#dc2626` is (220, 38, 38), and the engine writes `rgba()` with four
 * alpha decimals so it can tell its own output from the app's. The engine remembers every string it wrote with the
 * colour it replaced, and a written string stands for one colour: a second colour landing on the same string gets
 * another spelling of it (one more alpha decimal, identical on the canvas). That memory is module state, so every
 * test starts from an empty one (`forgetProducedColors`).
 */

import {beforeEach, describe, expect, it, vi} from 'vitest';
import {parseColor} from './color.js';
import {chartPatch, forgetProducedColors, mapChartOption, originalColor, type ChartRule} from './engine/charts';
import {resolveTarget} from './engine/targets';

vi.mock('echarts', () => {
    throw new Error('echarts was imported: the pure mapping of engine/charts.ts must not need it');
});

beforeEach(() => {
    forgetProducedColors();
});

function rule(to: string, alphaVariants = true): ChartRule {
    const target = resolveTarget(to);
    if (!target) throw new Error(`not a target: ${to}`);
    return {changeId: `chart-color:#10b981@both`, target, alphaVariants};
}

/** A colour the parser must read: the test fails here, with the text, rather than on a null later. */
function colorOf(text: string): NonNullable<ReturnType<typeof parseColor>> {
    const rgba = parseColor(text);
    if (!rgba) throw new Error(`not a colour: ${text}`);
    return rgba;
}

/** Emerald `#10b981` → red `#dc2626`, translucent variants included. */
const PLAN = new Map([['#10b981', rule('#dc2626')]]);
const RED = 'rgba(220, 38, 38, 1.0000)';
const NONE = new Map<string, ChartRule>();

type Json = Record<string, unknown>;
const at = (value: unknown, ...path: (string | number)[]): unknown => path.reduce<unknown>((v, key) => (v as Record<string | number, unknown>)[key], value);

describe('mapChartOption — copy on write', () => {
    const option = () => ({
        color: ['#10b981', '#3b82f6'],
        series: [
            {id: 'a', type: 'line', itemStyle: {color: '#10b981'}, data: [1, 2, null, 4]},
            {id: 'b', type: 'bar', itemStyle: {color: '#3b82f6'}},
        ],
        xAxis: {axisLabel: {color: '#94a3b8'}},
        animation: true,
        title: {text: 'Net worth'},
    });

    it('returns the very same option when the plan changes nothing in it', () => {
        const unchanged = {series: [{type: 'line', data: [1, 2, null], itemStyle: {color: '#3b82f6'}}], xAxis: {axisLabel: {color: '#94a3b8'}}, animation: true};
        expect(mapChartOption(unchanged, PLAN)).toBe(unchanged);
        const any = option();
        expect(mapChartOption(any, NONE)).toBe(any);
    });

    it('copies only the path to a changed colour, and leaves the app’s object as it was', () => {
        const input = option();
        const before = structuredClone(input);
        const out = mapChartOption(input, PLAN) as ReturnType<typeof option>;

        expect(input).toEqual(before);
        expect(out).not.toBe(input);
        expect(out.color).toEqual([RED, '#3b82f6']);
        expect(out.series).not.toBe(input.series);
        expect(out.series[0]).not.toBe(input.series[0]);
        expect(out.series[0].itemStyle.color).toBe(RED);
        // Untouched branches are shared, not copied.
        expect(out.series[0].data).toBe(input.series[0].data);
        expect(out.series[1]).toBe(input.series[1]);
        expect(out.xAxis).toBe(input.xAxis);
        expect(out.title).toBe(input.title);
    });

    it('keeps the prototype of a copied object, so an ECharts gradient stays a gradient', () => {
        class Gradient {
            type = 'linear';
            colorStops: {offset: number; color: string}[];
            constructor(colorStops: {offset: number; color: string}[]) {
                this.colorStops = colorStops;
            }
        }
        const input = new Gradient([
            {offset: 0, color: '#10b981'},
            {offset: 1, color: '#ffffff'},
        ]);
        const out = mapChartOption({areaStyle: {color: input}}, PLAN);
        const mapped = at(out, 'areaStyle', 'color');
        expect(mapped).toBeInstanceOf(Gradient);
        expect(mapped).not.toBe(input);
        expect(at(mapped, 'colorStops', 0, 'color')).toBe(RED);
        expect(at(mapped, 'colorStops', 1)).toBe(input.colorStops[1]);
    });

    it('leaves numbers, typed arrays and dates alone, and terminates on an option that refers to itself', () => {
        const opaque = {data: new Float64Array([1, 2, 3]), when: new Date(0), count: 3, label: 'Total'};
        expect(mapChartOption(opaque, PLAN)).toBe(opaque);

        const looped: Json = {color: '#10b981'};
        looped.self = looped;
        expect(at(mapChartOption(looped, PLAN), 'color')).toBe(RED);
    });
});

describe('mapChartOption — colours', () => {
    it('maps every spelling of the colour, inside strings that hold more than a colour, to one string', () => {
        const out = mapChartOption(
            {
                hex: '#10B981',
                hexAlpha: '#10b981ff',
                rgbComma: 'rgb(16, 185, 129)',
                rgbSpace: 'rgb(16 185 129)',
                tooltip: '<span style="color:#10b981">●</span> Gain',
                other: '#3b82f6',
                keyword: 'transparent',
            },
            PLAN,
        );
        expect(out).toEqual({hex: RED, hexAlpha: RED, rgbComma: RED, rgbSpace: RED, tooltip: `<span style="color:${RED}">●</span> Gain`, other: '#3b82f6', keyword: 'transparent'});
        // One colour, one string: it comes back as the first spelling the engine saw.
        expect(originalColor(RED)).toBe('#10B981');
        expect(mapChartOption(out, NONE)).toEqual({hex: '#10B981', hexAlpha: '#10B981', rgbComma: '#10B981', rgbSpace: '#10B981', tooltip: '<span style="color:#10B981">●</span> Gain', other: '#3b82f6', keyword: 'transparent'});
    });

    it('keeps the alpha of a translucent variant', () => {
        expect(at(mapChartOption({c: 'rgba(16, 185, 129, 0.25)'}, PLAN), 'c')).toBe('rgba(220, 38, 38, 0.2500)');
        expect(at(mapChartOption({c: 'rgba(16, 185, 129, 0)'}, PLAN), 'c')).toBe('rgba(220, 38, 38, 0.0000)');
    });

    it('combines the alpha of the target with the alpha of the variant', () => {
        const halfRed = new Map([['#10b981', rule('rgba(220, 38, 38, 0.5)')]]);
        expect(at(mapChartOption({c: '#10b981'}, halfRed), 'c')).toBe('rgba(220, 38, 38, 0.5000)');
        expect(at(mapChartOption({c: 'rgba(16, 185, 129, 0.5)'}, halfRed), 'c')).toBe('rgba(220, 38, 38, 0.2500)');
    });

    it('leaves the translucent variants alone when the change excludes them', () => {
        const opaqueOnly = new Map([['#10b981', rule('#dc2626', false)]]);
        const input = {area: 'rgba(16, 185, 129, 0.25)'};
        expect(mapChartOption(input, opaqueOnly)).toBe(input);
        expect(at(mapChartOption({line: '#10b981'}, opaqueOnly), 'line')).toBe(RED);
    });

    it('writes concrete sRGB for the canvas: a target outside sRGB is clamped, one that does not resolve changes nothing', () => {
        // Tailwind v4 emerald-600, outside sRGB.
        const wide = new Map([['#10b981', rule('oklch(59.6% .145 163.225)')]]);
        const written = at(mapChartOption({c: '#10b981'}, wide), 'c') as string;
        const m = /^rgba\((\d{1,3}), (\d{1,3}), (\d{1,3}), 1\.0000\)$/.exec(written);
        expect(m, written).not.toBeNull();
        for (const channel of (m as RegExpExecArray).slice(1)) expect(Number(channel)).toBeLessThanOrEqual(255);

        // `var()` is read from the page, and there is no page here: nothing to write.
        const unresolved = new Map([['#10b981', rule('var(--theme-accent)')]]);
        const input = {c: '#10b981'};
        expect(mapChartOption(input, unresolved)).toBe(input);
    });

    it('turns its own output back into the app’s colour first, so a new plan, or none, starts from the app', () => {
        const input = {series: [{itemStyle: {color: '#10b981'}}]};
        const red = mapChartOption(input, PLAN);
        expect(at(red, 'series', 0, 'itemStyle', 'color')).toBe(RED);
        expect(originalColor(RED)).toBe('#10b981');
        expect(originalColor('#123456')).toBe('#123456');

        expect(mapChartOption(red, NONE)).toEqual(input);
        const blue = mapChartOption(red, new Map([['#10b981', rule('#2563eb')]]));
        expect(at(blue, 'series', 0, 'itemStyle', 'color')).toBe('rgba(37, 99, 235, 1.0000)');
    });
});

describe('one new value for several colours', () => {
    /** Emerald, blue and amber all → red `#dc2626`, opaque. */
    const ALL_RED = new Map([
        ['#10b981', rule('#dc2626')],
        ['#3b82f6', rule('#dc2626')],
        ['#f59e0b', rule('#dc2626')],
    ]);

    it('gives each colour its own spelling of the new value, and an empty plan gives each its own original back', () => {
        const app = {color: ['#10b981', '#3b82f6', '#f59e0b'], series: [{itemStyle: {color: '#3b82f6'}}, {itemStyle: {color: '#10b981'}}, {areaStyle: {color: '#f59e0b'}}]};
        const out = mapChartOption(app, ALL_RED);
        const [green, blue, amber] = at(out, 'color') as string[];

        expect(green).toBe(RED);
        expect(new Set([green, blue, amber]).size).toBe(3);
        // Other spellings of one colour: identical on the canvas.
        for (const spelled of [blue, amber]) expect(colorOf(spelled), spelled).toEqual(colorOf(RED));
        // A colour keeps its spelling wherever it appears.
        expect(at(out, 'series', 0, 'itemStyle', 'color')).toBe(blue);
        expect(at(out, 'series', 1, 'itemStyle', 'color')).toBe(green);
        expect(at(out, 'series', 2, 'areaStyle', 'color')).toBe(amber);

        expect([green, blue, amber].map(originalColor)).toEqual(['#10b981', '#3b82f6', '#f59e0b']);
        expect(mapChartOption(out, NONE)).toEqual(app);
    });

    it('does the same for the charts already on screen: forward and back through the patch', () => {
        const app = {
            color: ['#10b981', '#3b82f6'],
            series: [
                {id: 'g', type: 'line', itemStyle: {color: '#10b981'}},
                {id: 'b', type: 'bar', itemStyle: {color: '#3b82f6'}},
            ],
        };
        const forward = chartPatch(app, ALL_RED);
        const [green, blue] = at(forward, 'color') as string[];
        expect(green).toBe(RED);
        expect(blue).not.toBe(green);
        expect(colorOf(blue)).toEqual(colorOf(RED));
        expect(forward).toEqual({
            color: [green, blue],
            series: [
                {id: 'g', itemStyle: {color: green}},
                {id: 'b', itemStyle: {color: blue}},
            ],
        });

        // What `getOption()` reads back once ECharts merged the patch; an empty plan patches each colour back.
        const onScreen = {
            color: [green, blue],
            series: [
                {id: 'g', type: 'line', itemStyle: {color: green}},
                {id: 'b', type: 'bar', itemStyle: {color: blue}},
            ],
        };
        expect(chartPatch(onScreen, NONE)).toEqual({
            color: ['#10b981', '#3b82f6'],
            series: [
                {id: 'g', itemStyle: {color: '#10b981'}},
                {id: 'b', itemStyle: {color: '#3b82f6'}},
            ],
        });
    });

    it('gives two alphas of one colour that land on one result their own spellings too', () => {
        const halfRed = new Map([['#10b981', rule('rgba(220, 38, 38, 0.5)')]]);
        // 0.25 of opaque red, and 0.5 of half-transparent red: both 0.25 on the canvas.
        const quarter = at(mapChartOption({c: 'rgba(16, 185, 129, 0.25)'}, PLAN), 'c') as string;
        const half = at(mapChartOption({c: 'rgba(16, 185, 129, 0.5)'}, halfRed), 'c') as string;

        expect(quarter).toBe('rgba(220, 38, 38, 0.2500)');
        expect(half).not.toBe(quarter);
        expect(colorOf(half)).toEqual(colorOf(quarter));
        expect(originalColor(quarter)).toBe('rgba(16, 185, 129, 0.25)');
        expect(originalColor(half)).toBe('rgba(16, 185, 129, 0.5)');
    });

    it('in a mixed case, gives the spellings of one colour one string, and another colour its own', () => {
        const plan = new Map([
            ['#ffffff', rule('#dc2626')],
            ['#10b981', rule('#dc2626')],
        ]);
        const out = mapChartOption({short: '#fff', long: '#ffffff', green: '#10b981'}, plan) as Record<string, string>;

        expect(out.short).toBe(RED);
        expect(out.long).toBe(RED);
        expect(out.green).not.toBe(RED);
        expect(colorOf(out.green)).toEqual(colorOf(RED));
        // White comes back as one spelling of white, the first the engine saw; emerald as itself.
        expect(mapChartOption(out, NONE)).toEqual({short: '#fff', long: '#fff', green: '#10b981'});
    });
});

describe('mapChartOption — functions', () => {
    it('wraps a function once, without calling it, and the wrapper returns what the function returns', () => {
        const formatter = vi.fn(function (this: unknown, p: {value: number}) {
            return `<b style="color:#10b981">${p.value}</b>`;
        });
        const input = {tooltip: {formatter}};
        const out = mapChartOption(input, PLAN);
        const wrapper = at(out, 'tooltip', 'formatter') as (this: unknown, p: {value: number}) => string;

        expect(typeof wrapper).toBe('function');
        expect(wrapper).not.toBe(formatter);
        expect(formatter).not.toHaveBeenCalled();
        // Wrapped once: a second mapping reuses the wrapper, and an option already wrapped is left as it is.
        expect(at(mapChartOption(input, PLAN), 'tooltip', 'formatter')).toBe(wrapper);
        expect(mapChartOption(out, PLAN)).toBe(out);

        // A formatter runs later, with the plan the engine has then — none here — and gets `this` and its arguments.
        const self = {name: 'series'};
        expect(wrapper.call(self, {value: 5})).toBe('<b style="color:#10b981">5</b>');
        expect(formatter).toHaveBeenCalledOnce();
        expect(formatter.mock.contexts[0]).toBe(self);
        expect(formatter.mock.calls[0]).toEqual([{value: 5}]);
    });
});

describe('chartPatch', () => {
    /** An option as `getOption()` returns it: every component is a list. */
    const readBack = () => ({
        backgroundColor: 'transparent',
        color: ['#10b981', '#3b82f6'],
        series: [
            {id: 's1', type: 'line', data: [1, 2, 3], itemStyle: {color: '#3b82f6'}, lineStyle: {width: 2}},
            {
                id: 's2',
                type: 'bar',
                data: [{value: 1, itemStyle: {color: '#10b981'}}, {value: 2}],
                areaStyle: {
                    color: {
                        type: 'linear',
                        x: 0,
                        y: 0,
                        x2: 0,
                        y2: 1,
                        colorStops: [
                            {offset: 0, color: 'rgba(16, 185, 129, 0.4)'},
                            {offset: 1, color: 'rgba(16, 185, 129, 0)'},
                        ],
                    },
                },
            },
        ],
        xAxis: [{type: 'category', axisLine: {lineStyle: {color: '#94a3b8'}}}],
        yAxis: [{splitLine: {lineStyle: {color: 'rgba(16, 185, 129, 0.1)'}}}],
    });

    it('sends only the changed paths: placeholders for unchanged components, whole arrays and gradients, ids kept', () => {
        const option = readBack();
        const before = structuredClone(option);
        expect(chartPatch(option, PLAN)).toEqual({
            color: [RED, '#3b82f6'],
            series: [
                {},
                {
                    id: 's2',
                    data: [{value: 1, itemStyle: {color: RED}}, {value: 2}],
                    areaStyle: {
                        color: {
                            type: 'linear',
                            x: 0,
                            y: 0,
                            x2: 0,
                            y2: 1,
                            colorStops: [
                                {offset: 0, color: 'rgba(220, 38, 38, 0.4000)'},
                                {offset: 1, color: 'rgba(220, 38, 38, 0.0000)'},
                            ],
                        },
                    },
                },
            ],
            yAxis: [{splitLine: {lineStyle: {color: 'rgba(220, 38, 38, 0.1000)'}}}],
        });
        expect(option).toEqual(before);
    });

    it('is null when no colour of the option changes', () => {
        expect(chartPatch(readBack(), NONE)).toBeNull();
        expect(chartPatch(readBack(), new Map([['#ffffff', rule('#000000')]]))).toBeNull();
    });

    it('patches a function once, with its wrapper, and never again', () => {
        const formatter = () => 'label';
        const first = chartPatch({tooltip: [{formatter}]}, NONE);
        const wrapper = at(first, 'tooltip', 0, 'formatter');
        expect(typeof wrapper).toBe('function');
        expect(wrapper).not.toBe(formatter);
        expect(chartPatch({tooltip: [{formatter: wrapper}]}, NONE)).toBeNull();
    });
});
