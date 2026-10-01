// @vitest-environment jsdom
/**
 * GrowthChart — the tooltips that list names show them as text (workstream K, step 13, item 0).
 *
 * ECharts sets the string a function `formatter` returns as the tooltip's innerHTML: it encodes
 * nothing. GrowthChart's formatter puts a name into that HTML in three places, one per mode:
 *   - P&L → line: a row per broker through a local helper, `pnlRow(label, …)`, whose `label` is HTML
 *     by contract — the total row passes `<b>…</b>` — while the broker rows pass `broker.brokerName`
 *     as the user typed it;
 *   - P&L → candles: after the OHLC quad, a row per broker, `<span>${broker.brokerName}</span>`;
 *   - return % (the `pct` view): a row per series through `buildTooltipRow(p.seriesName, …)`, whose
 *     label is HTML by contract as well.
 * In the first two, a broker named `<img src=x onerror=…>` would run on the dashboard and on the broker
 * detail page of whoever hovers the chart. The third is a contract rather than a path: the `pct` view
 * names its three series with translations, and a mode switch replaces the chart's series
 * (`replaceMerge: ['series']`), so no name a user typed reaches it today. Its case hands the real
 * formatter a hostile series name — what ECharts would pass for any series the chart held.
 *
 * How it is tested: the real component, with ECharts replaced by the recorder of `GrowthChart.test.ts`
 * (jsdom has no canvas, and pixels are not the subject). The user's own clicks take the chart into
 * each mode; the formatter is the one the component handed to `setOption`, called on a point where
 * every series of the fixture has a value — the branch a hover walks. Its output is parsed in a
 * `<template>`, inert. Each red case has a control on the same path, which is also the proof that the
 * rows it reads are the rows the tooltip lists.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action
 * `component-unit`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in of `GrowthChart.test.ts` — a recorder, not a renderer — trimmed of the event
 * bookkeeping nothing here reads. It answers every call the chart and its helpers make on an instance
 * and keeps every `setOption` payload; see that file for which helper needs which method.
 */
const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface FakeChart {
        setOptionCalls: Array<{option: Record<string, unknown>}>;
        setOption: (option: Record<string, unknown>) => void;
        getOption: () => Record<string, unknown>;
        getWidth: () => number;
        getHeight: () => number;
        getDom: () => unknown;
        on: () => void;
        off: () => void;
        dispatchAction: () => void;
        resize: () => void;
        isDisposed: () => boolean;
        dispose: () => void;
    }

    const chartInstances: FakeChart[] = [];

    function createFakeChart(dom: unknown): FakeChart {
        let merged: Record<string, unknown> = {};
        let disposed = false;
        const chart: FakeChart = {
            setOptionCalls: [],
            setOption(option) {
                chart.setOptionCalls.push({option});
                merged = {...merged, ...option};
            },
            // `getZoomPercent()` reads `option.dataZoom?.[0]`: ECharts normalises it into an array.
            getOption: () => {
                const zoom = merged.dataZoom;
                return {...merged, dataZoom: zoom == null ? [] : Array.isArray(zoom) ? zoom : [zoom]};
            },
            // 40 daily buckets over 1200px keep the chart at 'daily': one bucket is one day.
            getWidth: () => 1200,
            getHeight: () => 360,
            getDom: () => dom,
            on: () => {},
            off: () => {},
            dispatchAction: () => {},
            resize: () => {},
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
        chartInstances.push(chart);
        return chart;
    }

    return {chartInstances, echartsModule: {init: (dom: unknown) => createFakeChart(dom)}};
});

vi.mock('echarts', () => echartsModule);

import {cleanup, fireEvent, render, setupI18n, waitFor} from '$test/component';
import type {PortfolioBrokerPnlHistory, PortfolioHistoryPoint, PortfolioPnlCandleSeries} from '$lib/stores/portfolio/portfolioStore.svelte';
import GrowthChart from './GrowthChart.svelte';

const HOSTILE = '<img src=x onerror="window.__k13=1">';
/** Ordinary names. The ampersand is deliberate: it must come out as `&`, never as `&amp;`. */
const ORDINARY = ['Rossi & Figli', 'Banca Semplice'] as const;

const DATES: string[] = Array.from({length: 40}, (_, index) => new Date(Date.UTC(2026, 0, 1 + index)).toISOString().slice(0, 10));
/** The day the formatter is asked about. Every broker of the fixture has a value on every day. */
const DAY = 20;

const eur = (amount: number) => ({code: 'EUR', amount: amount.toFixed(2)});

const HISTORY: PortfolioHistoryPoint[] = DATES.map((date, index) => ({
    date,
    cash_value: eur(1_000 + index),
    market_value: eur(10_000 + index * 100),
    nav_value: eur(11_000 + index * 100),
    capital_baseline: eur(10_500),
    book_asset_like: eur(9_000 + index * 50),
    cash_from_contributed_capital: eur(800),
    cash_from_generated_returns: eur(200 + index),
    total_pnl: eur(500 + index * 100),
    twrr: (index * 0.001).toFixed(6),
    mwrr_cumulative: (index * 0.0012).toFixed(6),
    roi: (index * 0.0009).toFixed(6),
}));

function brokerPnlHistory(names: readonly string[]): PortfolioBrokerPnlHistory[] {
    return names.map((broker_name, brokerIndex) => ({
        broker_id: 900 + brokerIndex,
        broker_name,
        points: DATES.map((date, index) => ({date, total_pnl: eur(250 + brokerIndex * 100 + index * 5)})),
    }));
}

/** A real candle on every day: the candles tooltip shows its quad before the broker rows. */
const PNL_CANDLES: PortfolioPnlCandleSeries = {
    hypothetical: true,
    points: DATES.map((date, index) => ({
        date,
        open: eur(500 + index * 100),
        high: eur(560 + index * 100),
        low: eur(480 + index * 100),
        close: eur(540 + index * 100),
    })),
};

type Formatter = (params: unknown) => string;

interface Series {
    name: string;
    data: unknown[];
}

/** The payload of the last `setOption` that satisfies `pick`, as the component produced it. */
function lastOption(pick: (option: Record<string, unknown>) => boolean): Record<string, unknown> | null {
    const calls = chartInstances.at(-1)?.setOptionCalls ?? [];
    return [...calls].reverse().find((call) => pick(call.option))?.option ?? null;
}

/** The series of the last draw: a mode switch's full rebuild and a partial update both carry them. */
const renderedSeries = (): Series[] => (lastOption((option) => Array.isArray(option.series))?.series ?? []) as Series[];

/** The tooltip formatter the component handed to ECharts. */
function tooltipFormatter(): Formatter {
    const formatter = (lastOption((option) => typeof (option.tooltip as {formatter?: unknown} | undefined)?.formatter === 'function')?.tooltip as {formatter: Formatter} | undefined)?.formatter;
    if (!formatter) throw new Error('GrowthChart never handed a tooltip formatter to ECharts');
    return formatter;
}

/** A candlestick datum is a real `[open, close, low, high]` quad, or ECharts' `'-'` gap sentinel. */
const isQuad = (datum: unknown): boolean => Array.isArray(datum) && datum.length === 4 && datum.every((part) => typeof part === 'number' && Number.isFinite(part));

function parse(html: string): DocumentFragment {
    const template = document.createElement('template');
    template.innerHTML = html;
    return template.content;
}

/** The rows of a tooltip — `<div><span>label</span><b>value</b></div>` — in order, header excluded. */
const tooltipRows = (fragment: DocumentFragment): Element[] => [...fragment.querySelectorAll('div')].filter((div) => div.children.length === 2 && div.children[0].tagName === 'SPAN' && div.children[1].tagName === 'B');

const rowLabels = (fragment: DocumentFragment): string[] => tooltipRows(fragment).map((row) => row.children[0].textContent ?? '');

const handlerAttributes = (fragment: DocumentFragment): string[] =>
    [...fragment.querySelectorAll('*')].flatMap((el) =>
        el
            .getAttributeNames()
            .filter((name) => name.toLowerCase().startsWith('on'))
            .map((name) => `<${el.tagName.toLowerCase()} ${name}>`),
    );

/** Mount the chart and take it into a mode with the clicks a user makes. */
async function openMode(mode: 'pct' | 'line' | 'candles', props: Record<string, unknown>): Promise<void> {
    const {getByTestId} = render(GrowthChart, {props: {history: HISTORY, ...props}});
    await waitFor(() => expect(chartInstances).toHaveLength(1), {timeout: 5_000});
    if (mode === 'pct') {
        await fireEvent.click(getByTestId('growth-toggle-pct'));
        return;
    }
    await fireEvent.click(getByTestId('growth-toggle-pnl'));
    await fireEvent.click(getByTestId(`growth-pnl-submode-${mode}`));
}

/** P&L → line: the tooltip of `DAY`, parsed. */
async function lineTooltip(brokers: readonly string[]): Promise<DocumentFragment> {
    await openMode('line', {brokerPnlHistory: brokerPnlHistory(brokers)});
    // Presence barrier: the line submode drew one line per broker, so the brokers are in the
    // aggregation the formatter reads — a tooltip without broker rows cannot pass the negatives below.
    await waitFor(() => expect(renderedSeries().map((series) => series.name)).toEqual(expect.arrayContaining([...brokers])), {timeout: 5_000});
    return parse(tooltipFormatter()([{dataIndex: DAY}]));
}

/** P&L → candles: the tooltip of the middle candle, parsed. */
async function candlesTooltip(brokers: readonly string[]): Promise<DocumentFragment> {
    await openMode('candles', {brokerPnlHistory: brokerPnlHistory(brokers), pnlCandles: PNL_CANDLES, onRequestPnlCandles: vi.fn()});
    // Presence barrier: the submode drew real candles. How many days a candle spans is the ladder's
    // choice, so the index is read off the drawn series instead of being assumed to be a day.
    await waitFor(() => expect(renderedSeries()[0]?.data.some(isQuad)).toBe(true), {timeout: 5_000});
    const candles = renderedSeries()[0].data;
    const index = Math.floor(candles.length / 2);
    expect(isQuad(candles[index]), 'the candle the tooltip is asked about is a real one').toBe(true);
    return parse(tooltipFormatter()([{dataIndex: index}]));
}

/**
 * The `pct` view: the return-% tooltip of `DAY`, parsed, for the series the component drew plus the
 * `extra` series names. ECharts calls the formatter with one entry per series at the pointer: the
 * drawn ones are built from the component's own series, the extra ones stand for any other series the
 * chart could hold.
 */
async function pctTooltip(extra: readonly string[]): Promise<{out: DocumentFragment; drawn: string[]}> {
    await openMode('pct', {});
    // Presence barrier: the view drew its three return series (the view it leaves draws five).
    await waitFor(() => expect(renderedSeries()).toHaveLength(3), {timeout: 5_000});
    const series = renderedSeries();
    const drawnParams = series.map((entry) => ({dataIndex: DAY, seriesName: entry.name, value: (entry.data[DAY] as {value?: unknown} | undefined)?.value, color: '#2563eb'}));
    const extraParams = extra.map((seriesName) => ({dataIndex: DAY, seriesName, value: [DATES[DAY], 1.25], color: '#dc2626'}));
    return {out: parse(tooltipFormatter()([...drawnParams, ...extraParams])), drawn: series.map((entry) => entry.name)};
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    chartInstances.length = 0;
});

afterEach(() => {
    cleanup();
});

const expectNamedAsText = (out: DocumentFragment, name: string, what: string): void => {
    expect.soft(out.querySelectorAll('img').length, `the ${what} must not become an <img>`).toBe(0);
    expect.soft(handlerAttributes(out), `the ${what} must not add a handler`).toEqual([]);
    expect.soft(rowLabels(out), `the row must show the ${what} as the characters it is made of — rows: ${JSON.stringify(rowLabels(out))}`).toContain(name);
};

describe('GrowthChart tooltips — names are text, not markup (K step 13, item 0)', () => {
    describe('P&L → line', () => {
        it('lists ordinary broker names unchanged and keeps the bold total row (control)', async () => {
            const out = await lineTooltip(ORDINARY);
            const rows = tooltipRows(out);

            // The total, then one row per broker of the fixture — the whole collection is this test's own.
            expect(rows).toHaveLength(1 + ORDINARY.length);
            // The total row's label is markup on purpose, and must stay markup.
            expect(rows[0].children[0].querySelector('b')).not.toBeNull();
            // Also the proof that `tooltipRows` reads the rows the case below reads.
            expect(rowLabels(out).slice(1).sort()).toEqual([...ORDINARY].sort());
        });

        it('shows a broker name made of markup as text, not as an element', async () => {
            const out = await lineTooltip([HOSTILE, ORDINARY[0]]);
            // Presence barrier: the broker rows of this day are there, so the negatives are about them.
            expect(rowLabels(out)).toContain(ORDINARY[0]);
            expectNamedAsText(out, HOSTILE, 'broker name');
        });
    });

    describe('P&L → candles', () => {
        it('lists ordinary broker names unchanged after the OHLC quad (control)', async () => {
            const out = await candlesTooltip(ORDINARY);
            const labels = rowLabels(out);

            // Open, close, high and low, then one row per broker of the fixture.
            expect(labels).toHaveLength(4 + ORDINARY.length);
            expect(labels.slice(4).sort()).toEqual([...ORDINARY].sort());
        });

        it('shows a broker name made of markup as text, not as an element', async () => {
            const out = await candlesTooltip([HOSTILE, ORDINARY[0]]);
            // Presence barrier: the broker rows of this candle are there, so the negatives are about them.
            expect(rowLabels(out)).toContain(ORDINARY[0]);
            expectNamedAsText(out, HOSTILE, 'broker name');
        });
    });

    describe('return % (pct view)', () => {
        it('lists the series by the names the component gave them, and an ordinary name unchanged (control)', async () => {
            const {out, drawn} = await pctTooltip([ORDINARY[0]]);
            // The drawn series come first, in their order: their names are translations, so they are
            // compared with what the component itself handed to ECharts, never with a literal.
            expect(rowLabels(out)).toEqual([...drawn, ORDINARY[0]]);
        });

        it('shows a series name made of markup as text, not as an element', async () => {
            const {out, drawn} = await pctTooltip([HOSTILE]);
            // Presence barrier: the drawn series are listed, so the branch under test ran.
            expect(rowLabels(out)).toEqual(expect.arrayContaining(drawn));
            expectNamedAsText(out, HOSTILE, 'series name');
        });
    });
});
