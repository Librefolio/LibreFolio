// @vitest-environment jsdom
/**
 * CorrelationHeatmap — the five orderings on every heatmap, and the type row (RN-20, Q12).
 *
 * The developer, 16/11/2026: «in una pagina ci sono 2 sort e in un'altra 5. vorrei ovunque tutti i sort possibili!», and
 * a third badge row, the type, beside the sector and the area, on every heatmap. What this file pins:
 *
 *  - **five buttons, always, in one order** — similarity, type, sector, region, name — whatever the maps hold;
 *  - **an ordering without data is offered but unavailable**, and says why: `aria-disabled`, a stable code in
 *    `data-disabled-reason` (`loading`, `failed`, `no-data`) and the sentence in the project's Tooltip, opened by a click
 *    or by the keyboard. The code follows the state of the metadata read the page hands in (`metadataStatus`): «no
 *    sector known» is true only once the read answered;
 *  - **offered is not available**: a press on an unavailable ordering changes nothing, and a chosen ordering whose data
 *    goes away stops ordering the matrix (similarity is drawn and pressed) and applies again when the data comes back;
 *  - **the type row** is the sector and area rows' twin: one badge per type, in the order the type ordering draws them,
 *    the type's icon and its name, an asset without a type «unclassified».
 *
 * Sentences are read from the shipped catalogue through `$_`, never written here. Every figure is invented.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';

const {chartInstances, echartsModule} = vi.hoisted(() => {
    const chartInstances: {setOptionCalls: unknown[]}[] = [];
    const init = () => {
        let disposed = false;
        const chart = {
            setOptionCalls: [] as unknown[],
            setOption(option: unknown) {
                chart.setOptionCalls.push(option);
            },
            getDom: () => null,
            on: () => {},
            off: () => {},
            dispatchAction: () => {},
            clear: () => {},
            resize: () => {},
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
        chartInstances.push(chart);
        return chart;
    };
    return {chartInstances, echartsModule: {init}};
});

vi.mock('echarts', () => echartsModule);
vi.mock('$lib/api', () => ({zodiosApi: new Proxy({}, {get: () => vi.fn(async () => ({items: [], buckets: [], fallback_emoji: '❔'}))})}));

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {_} from '$lib/i18n';
import type {RiskCorrelationOutput} from '$lib/features/risk/riskTypes';
import {ASSET_TYPE_MENU_ORDER, getAssetTypeIconUrl} from '$lib/utils/assetTypes';
import CorrelationHeatmap from './CorrelationHeatmap.svelte';

const [ALPHA, BETA, GAMMA, DELTA] = [11, 12, 13, 14];
const LABELS: ReadonlyMap<number, string> = new Map([
    [ALPHA, 'Invented fund Alpha'],
    [BETA, 'Invented fund Beta'],
    [GAMMA, 'Invented fund Gamma'],
    [DELTA, 'Invented fund Delta'],
]);

function cell(row: number, column: number, value: number) {
    return {row_asset_id: row, column_asset_id: column, value, observations: 250, coverage: 1, status: 'ok' as const};
}

/** Alpha and Gamma move together, Beta against both: similarity puts Alpha beside Gamma, never in name order. */
const OUTPUT: RiskCorrelationOutput = {
    kind: 'matrix',
    asset_ids: [ALPHA, BETA, GAMMA, DELTA],
    cells: [cell(BETA, ALPHA, -0.92), cell(GAMMA, ALPHA, 0.95), cell(GAMMA, BETA, -0.9), cell(DELTA, ALPHA, 0.1), cell(DELTA, BETA, 0.05), cell(DELTA, GAMMA, 0.2)],
};

/** Two ETFs, one stock, one asset whose type is unknown. */
const TYPES: ReadonlyMap<number, string | null> = new Map([
    [ALPHA, 'ETF'],
    [BETA, 'STOCK'],
    [GAMMA, 'ETF'],
    [DELTA, null],
]);
const SECTORS: ReadonlyMap<number, Readonly<Record<string, number>> | null> = new Map<number, Readonly<Record<string, number>> | null>([
    [ALPHA, {Technology: 1}],
    [BETA, {'Health Care': 1}],
    [GAMMA, {Technology: 1}],
    [DELTA, {'Health Care': 1}],
]);

const ORDER = ['similarity', 'type', 'sector', 'region', 'name'];
const button = (mode: string) => screen.getByTestId(`risk-correlation-ordering-${mode}`);
const drawnOrder = () => screen.getByTestId('risk-correlation-heatmap').getAttribute('data-asset-order');
const pressed = () => ORDER.filter((mode) => button(mode).getAttribute('aria-pressed') === 'true');

async function mount(props: Record<string, unknown> = {}) {
    const view = render(CorrelationHeatmap, {props: {output: OUTPUT, assetLabels: LABELS, ...props}});
    await waitFor(() => expect(chartInstances.length).toBeGreaterThan(0));
    return view;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    chartInstances.length = 0;
});

describe('CorrelationHeatmap — the five orderings, always', () => {
    it('draws the five buttons in one order with no data at all, the three that need data unavailable', async () => {
        await mount();

        const group = screen.getByRole('group');
        expect([...group.querySelectorAll('[data-testid^="risk-correlation-ordering-"]')].map((node) => node.getAttribute('data-testid')?.replace('risk-correlation-ordering-', ''))).toEqual(ORDER);
        expect(Object.fromEntries(ORDER.map((mode) => [mode, button(mode).getAttribute('aria-disabled')]))).toEqual({similarity: null, type: 'true', sector: 'true', region: 'true', name: null});
        for (const mode of ['type', 'sector', 'region']) expect(button(mode)).toHaveAttribute('data-disabled-reason', 'no-data');
    });

    it('opens the reason of an unavailable ordering on a click, worded for its own dimension', async () => {
        await mount({assetTypes: TYPES});

        await fireEvent.click(button('sector'));
        const help = await screen.findByRole('tooltip');
        expect(help.textContent?.trim()).toBe(get(_)('risk.assetSet.ordering.unavailable.sector'));
        expect(pressed(), 'a press on an unavailable ordering changes nothing').toEqual(['similarity']);
    });

    it('opens the reason from the keyboard too: the unavailable button stays focusable, and Enter on it is a click', async () => {
        await mount();

        const region = button('region');
        // A natively disabled button takes no focus and no click: the reason would be out of reach.
        expect(region).not.toHaveAttribute('disabled');
        region.focus();
        expect(document.activeElement, 'the unavailable button cannot take the keyboard focus').toBe(region);
        // A browser turns Enter or Space on a focused button into a click; jsdom does not, so the click stands for it.
        await fireEvent.click(region);
        const help = await screen.findByRole('tooltip');
        expect(help.textContent?.trim()).toBe(get(_)('risk.assetSet.ordering.unavailable.region'));
    });

    it.each([
        {status: 'loading', reason: 'loading', key: 'risk.assetSet.ordering.unavailable.loading'},
        {status: 'failed', reason: 'failed', key: 'risk.assetSet.ordering.unavailable.failed'},
    ])('says the read is $status, not that no data exists, while the metadata read is $status', async ({status, reason, key}) => {
        await mount({metadataStatus: status});

        for (const mode of ['type', 'sector', 'region']) expect(button(mode)).toHaveAttribute('data-disabled-reason', reason);
        await fireEvent.click(button('type'));
        const help = await screen.findByRole('tooltip');
        expect(help.textContent?.trim()).toBe(get(_)(key));
    });

    it('counts a type only when an asset has one: a map of unknown types leaves the type ordering unavailable', async () => {
        await mount({
            assetTypes: new Map([
                [ALPHA, null],
                [BETA, null],
                [GAMMA, undefined],
                [DELTA, null],
            ]),
        });

        expect(button('type')).toHaveAttribute('aria-disabled', 'true');
        expect(button('type')).toHaveAttribute('data-disabled-reason', 'no-data');
    });

    it('reads the data of the matrix’s own assets only: a map about other assets orders nothing', async () => {
        const OUTSIDER = 99;
        await mount({assetTypes: new Map([[OUTSIDER, 'ETF']]), assetSectors: new Map([[OUTSIDER, {Technology: 1}]])});

        for (const mode of ['type', 'sector']) {
            expect(button(mode), `${mode}: available on data about an asset the matrix does not draw`).toHaveAttribute('aria-disabled', 'true');
            expect(button(mode)).toHaveAttribute('data-disabled-reason', 'no-data');
        }
        expect(screen.queryByTestId('risk-correlation-groups'), 'a badge row about an asset the matrix does not draw').toBeNull();
    });

    it('makes an ordering available, with no reason, the moment its data is there', async () => {
        await mount({assetTypes: TYPES, assetSectors: SECTORS});

        for (const mode of ['type', 'sector']) {
            expect(button(mode)).not.toHaveAttribute('aria-disabled', 'true');
            expect(button(mode)).not.toHaveAttribute('data-disabled-reason');
        }
        expect(button('region')).toHaveAttribute('aria-disabled', 'true');
    });
});

describe('CorrelationHeatmap — offered is not available: a choice whose data goes away stops ordering the matrix', () => {
    it('falls back to similarity, drawn and pressed, and applies the choice again when the data comes back', async () => {
        const view = await mount({assetTypes: TYPES, assetSectors: SECTORS});
        const similarity = drawnOrder();

        await fireEvent.click(button('sector'));
        await waitFor(() => expect(pressed()).toEqual(['sector']));
        const bySector = drawnOrder();
        expect(bySector, 'premise: by sector draws another order than similarity').not.toBe(similarity);

        await view.rerender({assetSectors: new Map()});
        await waitFor(() => expect(pressed()).toEqual(['similarity']));
        expect(drawnOrder(), 'the matrix kept ordering by a sector it no longer has').toBe(similarity);
        expect(button('sector')).toHaveAttribute('aria-disabled', 'true');

        await view.rerender({assetSectors: SECTORS});
        await waitFor(() => expect(pressed()).toEqual(['sector']));
        expect(drawnOrder()).toBe(bySector);
    });
});

describe('CorrelationHeatmap — the type row, beside the sector and the area', () => {
    it('draws one badge per type, in the type ordering’s order, with the type’s icon and name and how many assets', async () => {
        await mount({assetTypes: TYPES});

        const row = screen.getByTestId('risk-correlation-groups-type');
        const badges = within(row).getAllByTestId('risk-correlation-group-badge');
        const t = get(_);
        // The type ordering's own order (`ASSET_TYPE_MENU_ORDER`: stocks before ETFs), the unknown type last.
        const known = ['ETF', 'STOCK'].sort((left, right) => ASSET_TYPE_MENU_ORDER.indexOf(left) - ASSET_TYPE_MENU_ORDER.indexOf(right));
        const count: Record<string, number> = {ETF: 2, STOCK: 1};
        expect(badges.map((badge) => badge.textContent?.replace(/\s+/g, ' ').trim())).toEqual([...known.map((type) => `${t(`assets.types.${type}`)} · ${count[type]}`), `❔ ${t('risk.assetSet.group.unclassified')} · 1`]);
        expect(badges.slice(0, 2).map((badge) => badge.querySelector('img')?.getAttribute('src'))).toEqual(known.map((type) => getAssetTypeIconUrl(type)));
        expect(within(row).getAllByText(t('risk.assetSet.exposure.type'))[0]).toBeTruthy();
    });

    it('draws the rows type, sector, area — the order of the buttons', async () => {
        await mount({assetTypes: TYPES, assetSectors: SECTORS});

        const rows = [...screen.getByTestId('risk-correlation-groups').querySelectorAll('[data-testid^="risk-correlation-groups-"]')].map((node) => node.getAttribute('data-testid'));
        expect(rows).toEqual(['risk-correlation-groups-type', 'risk-correlation-groups-sector']);
    });

    it('draws no type row when no asset has a type', async () => {
        await mount({assetSectors: SECTORS});

        expect(screen.getByTestId('risk-correlation-groups-sector')).toBeInTheDocument();
        expect(screen.queryByTestId('risk-correlation-groups-type')).toBeNull();
    });
});
