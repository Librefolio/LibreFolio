/**
 * Which day does a chart open on? (Y2-I63, GitHub issue #63)
 *
 * Issue #63: the tooltip of the Dashboard's growth chart showed another day's data than the one under the cursor, and the
 * newest days could not be opened at all. Every chart with a time axis is held to the same two promises, and this module is
 * how a spec checks them without reading a translated word:
 *
 *   1. put the pointer on a day the backend served, and the tooltip opens on that day (`expectTooltipOnDay`);
 *   2. put it on the newest and on the oldest day the chart shows, at the edge of the plot and a little outside it, and the
 *      tooltip opens on those (`expectEdgesReachable`).
 *
 * Two facts make it possible. The chart keeps its ECharts instance in `__lfChart` (`lib/utils/chartReady.ts`), so the pixel of a day is asked
 * of the chart itself, at the moment of the call. And the tooltip header says which days it stands for (`data-tooltip-from` / `data-tooltip-to`, ISO, from `buildTooltipHeader`): the
 * header's text is in the interface language.
 *
 * `host` is the element that carries `data-chart-ready` (the chart's container); its `<canvas>` takes the pointer. The tooltip is read
 * page-wide: ECharts shows one at a time, and a hidden one is not counted.
 */

import {expect, type Locator, type Page} from '@playwright/test';

/**
 * What `readTimeAxis` returns, from the chart's left edge: a time axis by its first and last instant (epoch ms), a category axis (one slot
 * per drawn day) by its first and last slot on screen, each with the pixels they are drawn at.
 */
export type TimeAxis = {kind: 'time'; fromMs: number; toMs: number; x0: number; x1: number} | {kind: 'category'; first: number; last: number; x0: number; x1: number};

/** The days a tooltip header stands for (ISO); the same day twice when it stands for one. */
export interface TooltipSpan {
    from: string;
    to: string;
}

/**
 * Where the chart draws its first x axis right now, read from the chart the container keeps in `__lfChart` (`attachChartReady`): the pixel of the
 * axis' ends is asked of ECharts at the moment of the call, so a resize or a zoom is never read stale. Null when the chart has no date axis yet.
 */
export async function readTimeAxis(host: Locator): Promise<TimeAxis> {
    const axis = await host.evaluate((node) => {
        type Axis = {type?: string; scale: {getExtent: () => number[]}};
        type Chart = {getModel: () => {getComponent: (type: string, index: number) => {axis?: Axis} | undefined}; convertToPixel: (finder: {xAxisIndex: number}, value: number) => number | number[]};
        const chart = (node as unknown as {__lfChart?: Chart}).__lfChart;
        const found = chart?.getModel().getComponent('xAxis', 0)?.axis;
        if (!chart || !found || (found.type !== 'time' && found.type !== 'category')) return null;
        const [from, to] = found.scale.getExtent();
        const pixel = (value: number): number => {
            const converted = chart.convertToPixel({xAxisIndex: 0}, value);
            return Array.isArray(converted) ? converted[0] : converted;
        };
        const x0 = pixel(from);
        const x1 = pixel(to);
        if (![from, to, x0, x1].every(Number.isFinite)) return null;
        return found.type === 'time' ? {kind: 'time' as const, fromMs: from, toMs: to, x0, x1} : {kind: 'category' as const, first: from, last: to, x0, x1};
    });
    if (!axis) throw new Error('the chart has no date axis drawn (no __lfChart, or its first x axis is neither a time nor a category axis)');
    return axis;
}

/** The chart's axis once it has been drawn at least once, whatever the render pass. */
export async function waitForTimeAxis(host: Locator, timeout = 15_000): Promise<TimeAxis> {
    await expect.poll(() => readTimeAxis(host).then(() => true, () => false), {timeout}).toBe(true);
    return readTimeAxis(host);
}

/**
 * The days the chart draws, oldest first (ISO), read from the chart the container holds in `__lfChart` (`attachChartReady` hands it over): the
 * days of a category axis when it has them, else those of every line series, after the chart aggregated them. That is what the pointer can reach.
 */
export async function drawnDays(host: Locator): Promise<string[]> {
    const days = await host.evaluate((node) => {
        type Option = {xAxis?: Array<{type?: string; data?: unknown[]}>; series?: Array<{type?: string; data?: unknown[]}>};
        const chart = (node as unknown as {__lfChart?: {getOption: () => Option}}).__lfChart;
        if (!chart) throw new Error('the chart container does not hand over its ECharts instance (__lfChart)');
        const option = chart.getOption();
        const pad = (n: number) => String(n).padStart(2, '0');
        const dayOf = (raw: unknown): string | null => {
            if (typeof raw === 'number') {
                const at = new Date(raw);
                return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}`;
            }
            return typeof raw === 'string' && /^\d{4}-\d{2}-\d{2}/.test(raw) ? raw.slice(0, 10) : null;
        };
        const categories = option.xAxis?.[0]?.type === 'category' ? (option.xAxis[0].data ?? []) : [];
        const fromAxis = categories.map(dayOf).filter((day): day is string => day !== null);
        if (fromAxis.length > 0) return fromAxis;
        const found: string[] = [];
        for (const series of option.series ?? []) {
            if (series.type !== 'line') continue;
            for (const datum of series.data ?? []) {
                const point = Array.isArray(datum) ? datum : (datum as {value?: unknown[]} | null)?.value;
                const day = dayOf(Array.isArray(point) ? point[0] : undefined);
                if (day !== null) found.push(day);
            }
        }
        return found;
    });
    return [...new Set(days)].sort();
}

/** The browser's own local midnight of an ISO day, as epoch ms: the instant ECharts puts that day at on a time axis. */
export async function dayToMs(page: Page, iso: string): Promise<number> {
    return page.evaluate((day) => {
        const [year, month, date] = day.split('-').map(Number);
        return new Date(year, month - 1, date).getTime();
    }, iso);
}

/** The ISO day (browser local time) an epoch ms falls on. */
export async function msToDay(page: Page, ms: number): Promise<string> {
    return page.evaluate((value) => {
        const at = new Date(value);
        const pad = (n: number) => String(n).padStart(2, '0');
        return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}`;
    }, ms);
}

/**
 * The pixel (from the chart's left edge) of `day`. On a time axis the day is an instant; on a category axis it is the slot of the day among
 * `days` (the days the chart draws, oldest first), which a spec reads with `drawnDays`. `hoursIn` moves a time axis' pixel into the day: the pointer of a
 * chart that reads the day it is in, or snaps to the nearest, answers the same from the middle of the morning; at midnight sharp a fraction of a
 * pixel decides which of two days it is.
 */
export async function pixelOfDay(page: Page, axis: TimeAxis, day: string, days?: readonly string[], hoursIn = 0): Promise<number> {
    if (axis.kind === 'time') {
        const ms = (await dayToMs(page, day)) + hoursIn * 3_600_000;
        return axis.x0 + ((ms - axis.fromMs) / (axis.toMs - axis.fromMs)) * (axis.x1 - axis.x0);
    }
    if (!days) throw new Error('a chart with a category axis needs the days it draws (drawnDays) to find the pixel of a day');
    const slot = days.indexOf(day);
    if (slot < 0) throw new Error(`${day} is not one of the days the chart draws`);
    return axis.x0 + ((slot - axis.first) / (axis.last - axis.first)) * (axis.x1 - axis.x0);
}

/** The tooltip the chart shows now: the days its header stands for, or null when none is on screen. */
export async function readTooltipSpan(host: Locator): Promise<TooltipSpan | null> {
    // page-wide: a chart may keep its tooltip in the body (`appendToBody`); the one on screen is the one ECharts shows
    return host.page().locator('[data-tooltip-from]').evaluateAll((headers) => {
        for (const header of headers as HTMLElement[]) {
            // a tooltip ECharts hides keeps its last content: only a shown one counts
            let shown: HTMLElement | null = header;
            while (shown && shown !== document.body) {
                const style = getComputedStyle(shown);
                if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) break;
                shown = shown.parentElement;
            }
            if (shown !== document.body) continue;
            return {from: header.dataset.tooltipFrom ?? '', to: header.dataset.tooltipTo ?? ''};
        }
        return null;
    });
}

/**
 * Put the pointer at `x` pixels from the chart's left edge and return the tooltip it opens, waiting until one is on screen or `timeout`
 * passes (then null).
 *
 * The vertical position alternates by a pixel between tries: two identical positions are coalesced by the browser, and a pointer event
 * delivered while the chart still animates is dropped. The horizontal one never moves, so the day under it stays the same.
 */
export async function tooltipAt(page: Page, host: Locator, x: number, timeout = 8_000): Promise<TooltipSpan | null> {
    const canvas = host.locator('canvas').first();
    await expect(canvas).toBeVisible({timeout});
    await canvas.scrollIntoViewIfNeeded();
    const box = await canvas.boundingBox();
    if (!box) throw new Error('the chart canvas reports no bounding box: it never laid out');
    const inset = Math.min(Math.max(x, 0), box.width - 1);
    let span: TooltipSpan | null = null;
    let jitter = 0;
    let attempt = 0;
    try {
        await expect
            .poll(
                async () => {
                    jitter = jitter === 0 ? 1 : 0;
                    // a marker under the pointer (a lot opened on the edge day) shows its own tooltip, which is not a day's: after three tries
                    // the pointer settles lower in the plot, where only the axis answers (and stays there, so the tooltip has time to come)
                    const height = attempt++ < 3 ? 0.4 : 0.6;
                    await page.mouse.move(box.x + inset, box.y + box.height * height + jitter);
                    span = await readTooltipSpan(host);
                    return span !== null;
                },
                {timeout},
            )
            .toBe(true);
    } catch {
        return null;
    }
    return span;
}

/** True when `day` is one of the days `span` stands for. */
export function spanHolds(span: TooltipSpan | null, day: string): boolean {
    return span !== null && span.from <= day && day <= span.to;
}

export interface OnDayOptions {
    /** The days the chart draws, oldest first: needed by a chart whose axis is a category axis. */
    days?: readonly string[];
    /** The tooltip stands for that one day alone (a chart that draws steps at its daily resolution), not for a bucket around it. */
    exact?: boolean;
}

/**
 * Put the pointer on `day` and check the tooltip opens on it. The pointer goes where the chart says the day is drawn; the tooltip must
 * stand for the day, whatever else the page is doing (`exact`: for that day alone).
 */
export async function expectTooltipOnDay(page: Page, host: Locator, day: string, options: OnDayOptions = {}): Promise<void> {
    const axis = await readTimeAxis(host);
    const x = await pixelOfDay(page, axis, day, options.days, 6);
    await expect
        .poll(async () => {
            const span = await tooltipAt(page, host, x, 3_000);
            if (!span) return `no tooltip at ${Math.round(x)}px for ${day}`;
            if (!spanHolds(span, day)) return `the tooltip stands for ${span.from}..${span.to}, not ${day} (pointer ${Math.round(x)}px)`;
            if (options.exact && span.from !== span.to) return `the tooltip stands for ${span.from}..${span.to}, one day expected (${day})`;
            return 'ok';
        }, {timeout: 20_000})
        .toBe('ok');
}

export interface EdgesOptions {
    /** The days the chart draws, oldest first: needed by a chart whose axis is a category axis. */
    days?: readonly string[];
    /** The newest day the chart shows. */
    newest: string;
    /** The oldest day the chart shows. */
    oldest: string;
    /** How far outside the plot the pointer also goes, in pixels. Default 10. */
    margin?: number;
}

/**
 * The newest and the oldest day must be reachable: with the pointer at the edge of the plot, and a little outside it in the chart's margin,
 * the tooltip opens on that day (or on the bucket that holds it).
 */
export async function expectEdgesReachable(page: Page, host: Locator, edges: EdgesOptions): Promise<void> {
    const axis = await readTimeAxis(host);
    const margin = edges.margin ?? 10;
    const oldestX = await pixelOfDay(page, axis, edges.oldest, edges.days);
    const newestX = await pixelOfDay(page, axis, edges.newest, edges.days);
    // the edge pixel itself: a pointer on a fractional edge belongs to the plot only from the whole pixel inside it
    const spots: Array<[string, string, number]> = [
        ['newest', edges.newest, Math.floor(newestX)],
        ['newest, in the right margin', edges.newest, Math.ceil(axis.x1) + margin],
        ['oldest', edges.oldest, Math.ceil(oldestX)],
    ];
    for (const [name, day, x] of spots) {
        await expect
            .poll(async () => {
                const span = await tooltipAt(page, host, x, 3_000);
                if (!span) return `${name}: no tooltip at ${Math.round(x)}px`;
                return spanHolds(span, day) ? 'ok' : `${name}: the tooltip stands for ${span.from}..${span.to}, not ${day} (pointer ${Math.round(x)}px)`;
            }, {timeout: 20_000})
            .toBe('ok');
    }
}
