// @vitest-environment jsdom
/**
 * ExposureTreemap — the tooltip shows broker and node names as text (workstream K, step 13, item 0).
 *
 * ECharts sets the string a function `formatter` returns as the tooltip's innerHTML: it encodes
 * nothing. The treemap's formatter builds that string from the tree the component drew, and the tree
 * carries the broker name as the user typed it — into `buildTooltipHeader(title, …)`, which expects
 * an already-escaped title — while a node without metadata has its `params.name` returned as it is.
 * A broker named `<img src=x onerror=…>` would run in the dashboard of whoever hovers its tile.
 *
 * How it is tested: the real component, with ECharts replaced by the recorder of
 * `GrowthChart.test.ts` — jsdom has no canvas, and pixels are not the subject. The formatter is the
 * one the component handed to `setOption`, called with nodes of the tree the component built, so the
 * test exercises exactly what a hover does. Its output is parsed in a `<template>`, inert.
 *
 * Also stubbed, and why:
 *   - layout: jsdom measures every box as 0×0 and the component draws only into a non-empty box, so
 *     `getBoundingClientRect` reports a panel-sized one;
 *   - the two loaders the mount fires (`ensureBrokersLoaded`, `ensurePluginIconsLoaded`), which call
 *     the API — a unit test must not reach it. The rest of both modules is the real code, and the
 *     broker name comes from the holding itself, the way the dashboard hands it over.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action
 * `component-unit`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/** The ECharts stand-in: a recorder, not a renderer (the `GrowthChart.test.ts` pattern). */
const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface SetOptionCall {
        option: Record<string, unknown>;
    }

    interface FakeChart {
        setOptionCalls: SetOptionCall[];
        setOption: (option: Record<string, unknown>) => void;
        getOption: () => Record<string, unknown>;
        getWidth: () => number;
        getHeight: () => number;
        getDom: () => unknown;
        on: (event: string, handler: () => void) => void;
        off: (event: string, handler: () => void) => void;
        dispatchAction: () => void;
        resize: () => void;
        clear: () => void;
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
            getOption: () => merged,
            getWidth: () => 800,
            getHeight: () => 500,
            getDom: () => dom,
            on: () => {},
            off: () => {},
            dispatchAction: () => {},
            resize: () => {},
            clear: () => {},
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
vi.mock('$lib/stores/reference/brokerStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/brokerStore')>()),
    ensureBrokersLoaded: async () => {},
}));
vi.mock('$lib/utils/broker/brokerHelpers', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/utils/broker/brokerHelpers')>()),
    ensurePluginIconsLoaded: async () => {},
}));

import {cleanup, render, setupI18n, waitFor} from '$test/component';
import ExposureTreemap from './ExposureTreemap.svelte';

const HOSTILE = '<img src=x onerror="window.__k13=1">';

const HOLDINGS = [
    {
        asset_id: 42,
        asset_name: 'K13 Asset',
        asset_type: 'STOCK',
        broker_id: 7,
        broker_name: HOSTILE,
        current_value: '1000',
        nav_weight_percent: '100',
        gain_loss: '50',
        gain_loss_percent: '0.05',
    },
];

interface TreeNode {
    name: string;
    children?: TreeNode[];
    _meta?: {level: string; broker?: string};
}

type Formatter = (params: {name: string; data: unknown}) => string;

/** The tooltip formatter and the tree of the last draw — both exactly as the component produced them. */
function lastDraw(): {formatter: Formatter; tree: TreeNode[]} | null {
    const calls = chartInstances.at(-1)?.setOptionCalls ?? [];
    const option = [...calls].reverse().find((call) => typeof (call.option.tooltip as {formatter?: unknown} | undefined)?.formatter === 'function')?.option;
    if (!option) return null;
    const tooltip = option.tooltip as {formatter: Formatter};
    const series = option.series as Array<{data: TreeNode[]}>;
    return {formatter: tooltip.formatter, tree: series[0].data};
}

function parse(html: string): DocumentFragment {
    const template = document.createElement('template');
    template.innerHTML = html;
    return template.content;
}

const handlerAttributes = (fragment: DocumentFragment): string[] =>
    [...fragment.querySelectorAll('*')].flatMap((el) =>
        el
            .getAttributeNames()
            .filter((name) => name.toLowerCase().startsWith('on'))
            .map((name) => `<${el.tagName.toLowerCase()} ${name}>`),
    );

async function drawTreemap(holdings = HOLDINGS, broker = HOSTILE): Promise<{formatter: Formatter; tree: TreeNode[]}> {
    render(ExposureTreemap, {props: {holdings, displayCurrency: 'EUR'}});
    await waitFor(() => expect(lastDraw()).not.toBeNull(), {timeout: 5_000});
    const draw = lastDraw()!;
    // Presence barrier: the broker of the fixture reached the tree the chart was given.
    expect(draw.tree[0]?._meta?.broker).toBe(broker);
    return draw;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    chartInstances.length = 0;
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({x: 0, y: 0, top: 0, left: 0, right: 800, bottom: 520, width: 800, height: 520, toJSON: () => ({})} as DOMRect);
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

describe('ExposureTreemap — tooltip names are text (K step 13, item 0)', () => {
    it.each([
        {tile: 'broker', pick: (tree: TreeNode[]) => tree[0]},
        {tile: 'asset', pick: (tree: TreeNode[]) => tree[0]?.children?.[0]?.children?.[0]},
    ])('shows the broker name as text in the $tile tile tooltip', async ({pick}) => {
        const {formatter, tree} = await drawTreemap();
        const node = pick(tree);
        expect(node?._meta, 'the tile must carry its metadata').toBeDefined();

        const out = parse(formatter({name: node!.name, data: node}));
        expect.soft(out.querySelectorAll('img').length, 'the broker name must not become an <img>').toBe(0);
        expect.soft(handlerAttributes(out), 'the broker name must not add a handler').toEqual([]);
        // The header is the site: the first line of the tooltip, built by `buildTooltipHeader`. Asserted
        // on its own because the broker tile also lists its name, already escaped, in the "Asset" row —
        // text found anywhere in the tooltip would pass on the strength of that other row.
        const header = out.firstElementChild?.firstElementChild;
        expect.soft(header?.textContent, 'the tooltip header must show the broker name as the characters it is made of').toBe(HOSTILE);
    });

    it('shows the name of a node without metadata as text', async () => {
        const {formatter} = await drawTreemap();

        const out = parse(formatter({name: HOSTILE, data: {name: HOSTILE}}));
        expect.soft(out.querySelectorAll('img').length, 'the node name must not become an <img>').toBe(0);
        expect.soft(handlerAttributes(out), 'the node name must not add a handler').toEqual([]);
        expect.soft(out.textContent, 'the node name must be shown as the characters it is made of').toBe(HOSTILE);
    });

    it('renders the header and the rows of an ordinary broker and asset (control)', async () => {
        // Also the proof that `firstElementChild.firstElementChild` is the header the cases above read.
        const {formatter, tree} = await drawTreemap([{...HOLDINGS[0], broker_name: 'Fineco'}], 'Fineco');
        const asset = tree[0]?.children?.[0]?.children?.[0];

        const out = parse(formatter({name: asset!.name, data: asset}));
        expect(out.firstElementChild?.firstElementChild?.textContent).toBe('Fineco');
        expect(out.textContent).toContain('K13 Asset');
        expect(out.textContent).toContain('100.0%');
    });
});
