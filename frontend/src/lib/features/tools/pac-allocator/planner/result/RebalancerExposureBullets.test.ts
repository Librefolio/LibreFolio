// @vitest-environment jsdom
/**
 * The Rebalancer's exposure, a bullet chart (F4a of project 67, step 8; the developer's decision of 13/11, option (c)).
 *
 * For every category of a dimension (Asset type, sector, country): a grey bar «today» (`before_weight`), a coloured bar
 * «after the plan» (`final_weight`) and a thin tick on the target (`target_weight`) across both. The cash row has the same
 * form and is always the last. Rows by target, largest first, then by the weight after; above 12 categories (the
 * countries) the first 12 and «Show all», never an «Others» row, which would be a sum.
 *
 * Colours: today in the PAC's neutral grey (`PAC_EXPOSURE_COLORS.ideal`); after in the category's colour (types by
 * family, sectors by name, countries by the country sequence on their rank by target, «Uncategorised» in the unclassified
 * colour); the cash in its own (`--lf-cat-liquidity`); the tick in the primary text role with a halo in the card's colour.
 *
 * How: `echarts` is a recorder, not a renderer (jsdom has no canvas), as in `ExposureBars.test.ts`. The roles are
 * invented and injected with `setRoleReader` for the chart's own element only, per theme. Expected colours come from the
 * theme's own functions and tables, never from the component's helpers. The weights are the engine's G5 answer
 * (`rebalancer-browser.json`, untouched) or variants built here. Nothing translated is asserted.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface FakeChart {
        options: Record<string, unknown>[];
        setOption: (option: Record<string, unknown>) => void;
        getDom: () => unknown;
        on: () => void;
        off: () => void;
        resize: () => void;
        isDisposed: () => boolean;
        dispose: () => void;
    }
    const chartInstances: FakeChart[] = [];
    function createFakeChart(dom: unknown): FakeChart {
        let disposed = false;
        const chart: FakeChart = {
            options: [],
            setOption(option) {
                chart.options.push(option);
            },
            getDom: () => dom,
            on: () => {},
            off: () => {},
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
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
}));

import {flushSync, tick} from 'svelte';
import {fireEvent, render, setupI18n, waitFor} from '$test/component';
import {categoryColor, COUNTRY_SEQUENCE, sequenceColor} from '$lib/theme/chartCategories';
import {shadePoles} from '$lib/theme/chartShades';
import {PAC_EXPOSURE_COLORS} from '$lib/theme/chartTheme';
import {setRoleReader} from '$lib/theme/roleColors';
import {notifyChartColorsChange} from '$lib/theme/themeMode';
import {themed} from '$lib/theme/themePair';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {REBALANCER_PLANNER_PROFILE} from '../profile';
import type {PlannerExactNumber, PlannerNumberAvailability} from '../types';
import browser from './__fixtures__/rebalancer-browser.json';
import {chartPercent, UNCATEGORISED_CATEGORY_ID} from './model';
import RebalancerExposureBullets from './RebalancerExposureBullets.svelte';
import type {BulletRow} from './rebalancerExposureTooltip';

type Json = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Theme = 'light' | 'dark';

interface Roles {
    primary: string;
    card: string;
    liquidity: string;
}
const ROLES: Record<Theme, Roles> = {
    light: {primary: '#101820', card: '#f7f3ea', liquidity: '#3a5f8f'},
    dark: {primary: '#eef2ee', card: '#1d2622', liquidity: '#6a9dc2'},
};
const EDITED: Record<Theme, Roles> = {
    light: {primary: '#241010', card: '#fbfbf2', liquidity: '#2d4f7c'},
    dark: {primary: '#f4e9e9', card: '#202a33', liquidity: '#7aa9cf'},
};
const themeNow = (): Theme => (document.documentElement.classList.contains('dark') ? 'dark' : 'light');

function injectRoles(current: () => Record<Theme, Roles>): void {
    setRoleReader((role, scope) => {
        if (scope?.getAttribute('data-chart') !== 'exposure-bullets') return '';
        const roles = current()[themeNow()];
        if (role === '--lf-text-primary') return roles.primary;
        if (role === '--lf-surface-card') return roles.card;
        if (role === '--lf-cat-liquidity') return roles.liquidity;
        return '';
    });
}

beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => {
    chartInstances.length = 0;
    injectRoles(() => ROLES);
});
afterEach(() => {
    setRoleReader(null);
    document.documentElement.classList.remove('dark');
});

/** The rows of one dimension as `ExposureSection` hands them: the key is the backend's name, the label invented. */
function bulletRows(rows: Json[], dimension: string): BulletRow[] {
    return rows
        .filter((row) => row.dimension === dimension)
        .map((row) =>
            row.kind === 'cash'
                ? {id: 'cash', key: 'cash', label: 'CASH-label', kind: 'cash', before: row.before_weight, target: row.target_weight, final: row.final_weight}
                : {
                      id: row.category_id,
                      key: row.category_id === UNCATEGORISED_CATEGORY_ID ? UNCATEGORISED_CATEGORY_ID : dimension === 'asset_type' ? row.category_id : row.label,
                      label: `label:${row.category_id}`,
                      kind: 'category',
                      before: row.before_weight,
                      target: row.target_weight,
                      final: row.final_weight,
                  },
        );
}

async function mounted(rows: BulletRow[], dimension: string): Promise<void> {
    render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: RebalancerExposureBullets, childProps: {rows, dimension}}});
    flushSync();
    await tick();
    await waitFor(() => expect(lastOption()).not.toBeNull());
}

function lastOption(): Json | null {
    const chart = chartInstances.at(-1);
    return (chart?.options.at(-1) as Json | undefined) ?? null;
}
const series = (id: string) => (lastOption()?.series as Json[]).find((item) => item.id === id) as Json;
const shownLabels = () => lastOption()?.yAxis.data as string[];
const afterColours = () => (series('after').data as Json[]).map((item) => item.itemStyle.color as string);

const exact = (value: string): PlannerExactNumber => ({kind: 'finite_decimal', value});
const available = (value: string): PlannerNumberAvailability => ({kind: 'available', value: exact(value)});
const G5 = browser.result.primary_solution.exposure_rows as Json[];

describe('the Rebalancer exposure bullets (F4a step 8)', () => {
    it('exposure bullets read the three published weights', async () => {
        // A variant in which no weight can be read off another: today, after and the target are unrelated in every row.
        const rows: BulletRow[] = [
            {id: 'STOCK', key: 'STOCK', label: 'A', kind: 'category', before: available('0.137'), target: exact('0.5'), final: available('0.421')},
            {id: 'CRYPTO', key: 'CRYPTO', label: 'B', kind: 'category', before: available('0.611'), target: exact('0.3'), final: available('0.093')},
            {id: 'cash', key: 'cash', label: 'C', kind: 'cash', before: available('0.252'), target: exact('0.2'), final: available('0.486')},
        ];
        await mounted(rows, 'asset_type');
        expect(series('now').data).toEqual(rows.map((row) => chartPercent(row.before)));
        expect((series('after').data as Json[]).map((item) => item.value)).toEqual(rows.map((row) => chartPercent(row.final)));
        expect(series('target').data).toEqual(rows.map((row, index) => [chartPercent(row.target), index]));
        expect(series('target-halo').data).toEqual(series('target').data);
    });

    it('the box of a row names it, with the dot of each of its three marks', async () => {
        const rows = bulletRows(G5, 'sector');
        await mounted(rows, 'sector');
        const option = lastOption() as Json;
        const index = shownLabels().indexOf('label:Energy');
        const html = option.tooltip.formatter([{dataIndex: index}]) as string;
        expect(html).toContain('label:Energy');
        for (const colour of [series('now').itemStyle.color, afterColours()[index], series('target').itemStyle.color]) expect(html).toContain(colour);
    });

    it('cash is the last row of every dimension, in the cash colour', async () => {
        for (const dimension of ['asset_type', 'sector', 'geography']) {
            chartInstances.length = 0;
            const rows = bulletRows(G5, dimension);
            await mounted(rows, dimension);
            expect(shownLabels().at(-1), dimension).toBe('CASH-label');
            expect(afterColours().at(-1), dimension).toBe(ROLES.light.liquidity);
            document.body.innerHTML = '';
        }
    });

    it('rows by target, largest first, then by the weight after; each category in its own colour', async () => {
        const rows = bulletRows(G5, 'sector');
        await mounted(rows, 'sector');
        // G5's sectors: Uncategorised 0.3, Other 0.2 = Real Estate 0.2 (Other after 0.112 < Real Estate 0.255), Consumer
        // Discretionary 0.07, Energy 0.03, then the cash.
        expect(shownLabels()).toEqual(['label:allocation.uncategorised', 'label:enc:Real_20Estate', 'label:Other', 'label:enc:Consumer_20Discretionary', 'label:Energy', 'CASH-label']);
        expect(afterColours()).toEqual([categoryColor('sector', 'Unknown', false), categoryColor('sector', 'Real Estate', false), categoryColor('sector', 'Other', false), categoryColor('sector', 'Consumer Discretionary', false), categoryColor('sector', 'Energy', false), ROLES.light.liquidity]);
        expect(categoryColor('sector', 'Consumer Discretionary', false), 'PREMISE: a sector with a space has a colour of its own').not.toBe(categoryColor('sector', 'Unknown', false));
        // Today in the designer's neutral grey, the theme's own table.
        expect(series('now').itemStyle.color).toBe(themed(PAC_EXPOSURE_COLORS.ideal, false));
    });

    it('the countries take the country sequence by rank, and «Show all» keeps every colour', async () => {
        const codes = ['USA', 'ITA', 'DEU', 'FRA', 'GBR', 'JPN', 'CHN', 'ESP', 'NLD', 'CHE', 'SWE', 'CAN', 'AUS', 'IND'];
        const rows: BulletRow[] = [
            ...codes.map((code, index): BulletRow => ({id: code, key: code, label: code, kind: 'category', before: available('0.01'), target: exact(String((0.2 - index * 0.01).toFixed(2))), final: available('0.02')})),
            {id: 'cash', key: 'cash', label: 'CASH-label', kind: 'cash', before: available('0.1'), target: exact('0.05'), final: available('0.1')},
        ];
        await mounted(rows, 'geography');
        expect(shownLabels(), 'the first 12 countries, then the cash').toEqual([...codes.slice(0, 12), 'CASH-label']);
        const poles = shadePoles(false, ROLES.light.card);
        const expected = codes.map((_code, rank) => sequenceColor(COUNTRY_SEQUENCE, rank, false, poles));
        expect(afterColours()).toEqual([...expected.slice(0, 12), ROLES.light.liquidity]);
        await fireEvent.click(document.querySelector('[data-action="show-all"]') as HTMLElement);
        flushSync();
        await tick();
        await waitFor(() => expect(shownLabels()).toHaveLength(codes.length + 1));
        expect(afterColours()).toEqual([...expected, ROLES.light.liquidity]);
    });

    it('the target tick reads the primary text role with a card halo, and follows the theme and a colour edit', async () => {
        await mounted(bulletRows(G5, 'asset_type'), 'asset_type');
        expect(series('target').itemStyle.color).toBe(ROLES.light.primary);
        expect(series('target-halo').itemStyle.color).toBe(ROLES.light.card);
        const [haloWidth] = series('target-halo').symbolSize as number[];
        const [tickWidth] = series('target').symbolSize as number[];
        expect(haloWidth - tickWidth, 'a halo of one pixel on each side').toBe(2);

        document.documentElement.classList.add('dark');
        await waitFor(() => expect(series('target').itemStyle.color).toBe(ROLES.dark.primary));
        expect(series('now').itemStyle.color).toBe(themed(PAC_EXPOSURE_COLORS.ideal, true));

        injectRoles(() => EDITED);
        notifyChartColorsChange();
        await waitFor(() => expect(series('target').itemStyle.color).toBe(EDITED.dark.primary));
        expect(series('target-halo').itemStyle.color).toBe(EDITED.dark.card);
        expect(afterColours().at(-1)).toBe(EDITED.dark.liquidity);
    });
});
