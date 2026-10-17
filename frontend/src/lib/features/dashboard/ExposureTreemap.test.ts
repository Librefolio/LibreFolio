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
import type {PortfolioSummary} from '$lib/stores/portfolio/portfolioStore.svelte';
import {formatPercent} from '$lib/utils/core/formatPercent';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
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
    _meta?: {level: string; broker?: string; brokerId?: number | null; assetId?: number};
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

/**
 * R17 / W8 / P4 — a type or broker tile shows the G/L of its holding group, as the backend sends it (MF-P).
 *
 * `summary.holding_groups` carries, for each broker (`asset_type` null) and for each asset type at each broker,
 * the unrealized G/L of the holdings whose value and G/L are both known, and that G/L over their cost
 * (`gain_loss_percent`, a fraction). PositionsPanel hands it to the treemap as `holdingGroups`; a group tile takes
 * its two figures from the group with its `(broker_id, asset_type | null)` and writes them as before — the amount
 * signed, the share ×100. It sums nothing itself. Summing is what went wrong: a holding with a value and no G/L
 * still entered the group's value, so the cost the share divided by (value − G/L) counted that whole value as cost.
 * A group missing from `holdingGroups` reads «—»; a group sent without figures shows none.
 *
 * Fixture: one broker, two asset types — two stocks, one of them with a value and no G/L, and a bond.
 *
 * Read: the tooltip formatter the component handed to ECharts, called with the tiles of the tree it drew, as the
 * cases above do. A type tile is found by an asset it holds, never by its translated name; its G/L rows are the
 * rows after the tooltip's divider, read by their value cell, never by their translated caption. The expected
 * figures are written by the formatters the tooltip uses.
 */
describe('ExposureTreemap — type and broker tiles show their holding group’s G/L (R17 / W8 / P4)', () => {
    const EM_DASH = '\u2014';
    const BROKER_ID = 31;
    const BROKER_NAME = 'Group Probe Broker';

    /** A holding as the dashboard hands it to the treemap. */
    interface GroupedHolding {
        asset_id: number;
        asset_name: string;
        asset_type: string;
        broker_id: number;
        broker_name: string;
        current_value: string;
        nav_weight_percent: string;
        gain_loss: string | null;
        gain_loss_percent: string | null;
    }

    /** A holding group as the summary sends it. */
    type HoldingGroup = NonNullable<PortfolioSummary['holding_groups']>[number];

    const STOCK_PRICED: GroupedHolding = {asset_id: 3101, asset_name: 'Group Probe Equity', asset_type: 'STOCK', broker_id: BROKER_ID, broker_name: BROKER_NAME, current_value: '1000', nav_weight_percent: '28.57', gain_loss: '100', gain_loss_percent: '0.1111'};
    /** A value and no G/L: its cost is unknown. */
    const STOCK_NO_GL: GroupedHolding = {asset_id: 3102, asset_name: 'Group Probe Equity Without Cost', asset_type: 'STOCK', broker_id: BROKER_ID, broker_name: BROKER_NAME, current_value: '500', nav_weight_percent: '14.29', gain_loss: null, gain_loss_percent: null};
    const BOND_PRICED: GroupedHolding = {asset_id: 3103, asset_name: 'Group Probe Bond', asset_type: 'BOND', broker_id: BROKER_ID, broker_name: BROKER_NAME, current_value: '2000', nav_weight_percent: '57.14', gain_loss: '-200', gain_loss_percent: '-0.0909'};

    /** The group of `assetType` at the probe broker — null for the broker's whole group — with its G/L and share, or none. */
    const group = (assetType: string | null, gainLoss: string | null, gainLossPercent: string | null): HoldingGroup => ({
        broker_id: BROKER_ID,
        asset_type: assetType,
        gain_loss: gainLoss == null ? null : {code: 'EUR', amount: gainLoss},
        gain_loss_percent: gainLossPercent,
    });

    /** Draws the treemap with the groups beside the holdings, as PositionsPanel hands `summary.holding_groups` over; returns the broker tile. */
    async function drawGroups(holdings: GroupedHolding[], holdingGroups: HoldingGroup[]): Promise<{formatter: Formatter; broker: TreeNode}> {
        const props = {holdings, displayCurrency: 'EUR', holdingGroups};
        render(ExposureTreemap, {props});
        await waitFor(() => expect(lastDraw()).not.toBeNull(), {timeout: 5_000});
        const {formatter, tree} = lastDraw()!;
        // Presence barrier: the probe broker reached the tree the chart was given.
        const broker = tree.find((tile) => tile._meta?.level === 'broker' && tile._meta.brokerId === BROKER_ID);
        if (!broker) throw new Error(`the treemap drew no tile for broker ${BROKER_ID}`);
        return {formatter, broker};
    }

    /** The type tile holding `assetId`: found by an asset it holds, never by its translated name. */
    function typeTileOf(broker: TreeNode, assetId: number): TreeNode {
        const tile = broker.children?.find((node) => node._meta?.level === 'type' && node.children?.some((asset) => asset._meta?.assetId === assetId));
        if (!tile) throw new Error(`the broker tile holds no type tile with asset ${assetId}`);
        return tile;
    }

    /** The G/L rows of a tile's tooltip — every row after its divider — by their value cell, never by their translated caption. */
    function glRows(formatter: Formatter, tile: TreeNode): string[] {
        const rows = [...(parse(formatter({name: tile.name, data: tile})).firstElementChild?.children ?? [])];
        const divider = rows.findIndex((row) => row.tagName === 'HR');
        if (divider < 0) throw new Error(`the tooltip of the ${tile._meta?.level} tile has no divider before its G/L rows`);
        return rows.slice(divider + 1).map((row) => ((row.querySelector('b') ?? row).textContent ?? '').trim());
    }

    /** A group's two G/L rows as the tooltip writes them: the amount signed, the share ×100. */
    const glOf = (gainLoss: string, gainLossPercent: string): string[] => [formatCurrencyAmountPlain(Number(gainLoss), 'EUR', {showSign: true}), formatPercent(Number(gainLossPercent), {scale: 100, signed: false})];

    /** The rows that hold a figure: every one but «—». */
    const figuresIn = (rows: string[]): string[] => rows.filter((value) => value !== EM_DASH);

    it('shows the group’s G/L and share — not a sum that counts a holding without G/L as cost — and «—» for a group not sent', async () => {
        // The backend's groups for these holdings. The stocks count only the one whose G/L is known: 100 on a cost of
        // 900. The broker counts both priced holdings: 100 − 200 on a cost of 900 + 2 200. The bond group is not sent.
        const {formatter, broker} = await drawGroups([STOCK_PRICED, STOCK_NO_GL, BOND_PRICED], [group(null, '-100', '-0.03225806451612903'), group('STOCK', '100', '0.1111111111111111')]);

        expect.soft(glRows(formatter, broker), 'broker tile').toEqual(glOf('-100', '-0.03225806451612903'));
        expect.soft(glRows(formatter, typeTileOf(broker, STOCK_PRICED.asset_id)), 'stock tile').toEqual(glOf('100', '0.1111111111111111'));
        const bond = glRows(formatter, typeTileOf(broker, BOND_PRICED.asset_id));
        expect.soft(bond.length, 'bond tile: a group not sent reads «—», its rows are not dropped').toBeGreaterThan(0);
        expect.soft(figuresIn(bond), 'bond tile: no figure for a group not sent').toEqual([]);
    });

    it('takes each tile’s figures from the group of its (broker_id, asset_type), null for the broker — figures no sum of the holdings gives', async () => {
        // Set apart from anything these holdings add up to: whatever a tile shows can only come from its group.
        const FIGURES = {broker: ['-33.33', '-0.0444'], stock: ['111.11', '0.2222'], bond: ['-222.22', '-0.1234']} as const;
        const {formatter, broker} = await drawGroups([STOCK_PRICED, STOCK_NO_GL, BOND_PRICED], [group(null, ...FIGURES.broker), group('BOND', ...FIGURES.bond), group('STOCK', ...FIGURES.stock)]);

        expect({
            broker: glRows(formatter, broker),
            stock: glRows(formatter, typeTileOf(broker, STOCK_PRICED.asset_id)),
            bond: glRows(formatter, typeTileOf(broker, BOND_PRICED.asset_id)),
        }).toEqual({broker: glOf(...FIGURES.broker), stock: glOf(...FIGURES.stock), bond: glOf(...FIGURES.bond)});
    });

    it('shows no figure for a group sent without one — its holdings have no G/L — where a sum makes up a zero', async () => {
        const bondNoGl: GroupedHolding = {...BOND_PRICED, gain_loss: null, gain_loss_percent: null};
        const {formatter, broker} = await drawGroups([STOCK_PRICED, STOCK_NO_GL, bondNoGl], [group(null, '100', '0.1111111111111111'), group('BOND', null, null), group('STOCK', '100', '0.1111111111111111')]);

        // Barrier: a sibling tile of the same draw writes its group's amount, so the bond's G/L rows are rows that could hold one.
        expect(glRows(formatter, typeTileOf(broker, STOCK_PRICED.asset_id))[0], 'stock tile').toBe(formatCurrencyAmountPlain(100, 'EUR', {showSign: true}));
        // «—» or no row at all: what is excluded is a figure.
        expect(figuresIn(glRows(formatter, typeTileOf(broker, BOND_PRICED.asset_id))), 'bond tile').toEqual([]);
    });
});
