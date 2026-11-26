// @vitest-environment jsdom
/**
 * TL-5 of project 67 (the developer, 23/11: «la mappa geografica e le sue barre falle come ti ho detto in pac e
 * ribilanciatore»): one layout of the exposures in both Tools.
 *
 *   - types and sectors first, side by side, then the countries on the whole width;
 *   - in the countries' block the two maps first, their bars under them: the Rebalancer's bullets, the PAC's two bars (the
 *     same chart as types and sectors, never a bullet);
 *   - one accessible list per dimension, one entry per published row.
 *
 * The rows are the Rebalancer's G5 answer (`rebalancer-browser.json`); the PAC's are the same categories without the
 * Rebalancer's own fields (`before_weight`, the cash row). ECharts is a recorder: jsdom has no canvas. Nothing translated
 * is asserted.
 */
import {flushSync} from 'svelte';
import {beforeAll, describe, expect, it, vi} from 'vitest';

const {echartsModule} = vi.hoisted(() => {
    function fakeChart(dom: unknown) {
        let disposed = false;
        return {
            setOption: () => {},
            getOption: () => ({}),
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
    }
    return {echartsModule: {init: (dom: unknown) => fakeChart(dom), registerMap: () => {}}};
});

vi.mock('echarts', () => echartsModule);

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {render, screen, setupI18n} from '$test/component';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, type PlannerProfile} from '../profile';
import type {PlannerExposureRow} from '../types';
import browser from './__fixtures__/rebalancer-browser.json';
import ExposureSection from './ExposureSection.svelte';

beforeAll(async () => {
    await setupI18n();
});

type WireRow = Record<string, unknown> & {kind?: string};
const REBALANCER_ROWS = browser.result.primary_solution.exposure_rows as unknown as PlannerExposureRow[];
/** The PAC publishes the same categories without the Rebalancer's own fields: no «today», no cash row. */
const PAC_ROWS = (browser.result.primary_solution.exposure_rows as WireRow[]).filter((row) => row.kind !== 'cash').map(({before_weight: _before, kind: _kind, ...row}) => row) as unknown as PlannerExposureRow[];

function mounted(profile: PlannerProfile, rows: PlannerExposureRow[]): HTMLElement {
    render(ProfileHarness, {props: {profile, child: ExposureSection, childProps: {rows}}});
    flushSync();
    return screen.getByTestId(`${profile.testIdPrefix}-exposures`);
}

const ids = (root: ParentNode, profile: PlannerProfile, name: string) => [...root.querySelectorAll(`[data-testid="${profile.testIdPrefix}-${name}"]`)] as HTMLElement[];
const follows = (first: Node, second: Node) => Boolean(first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING);

describe('the exposures, one layout in both Tools (TL-5)', () => {
    it.each([
        ['pac', PAC_PLANNER_PROFILE, PAC_ROWS],
        ['rebalancer', REBALANCER_PLANNER_PROFILE, REBALANCER_ROWS],
    ] as const)('%s: types, sectors, then the countries; in the countries the maps first, their chart under them', (tool, profile, rows) => {
        const exposures = mounted(profile, rows);
        const blocks = ids(exposures, profile, 'exposures-dimension');
        expect(blocks.map((block) => block.getAttribute('data-dimension'))).toEqual(['asset_type', 'sector', 'geography']);

        const geography = blocks[2];
        const [maps] = ids(geography, profile, 'exposures-maps');
        const chart = tool === 'pac' ? ids(geography, profile, 'exposures-bars') : ids(geography, profile, 'exposures-bullets');
        expect(maps, 'the two maps').toBeDefined();
        expect(chart).toHaveLength(1);
        expect(chart[0].getAttribute('data-dimension')).toBe('geography');
        expect(follows(maps, chart[0]), 'the chart under the maps').toBe(true);
        expect(ids(exposures, profile, 'exposures-maps'), 'the maps in the countries only').toHaveLength(1);
        expect(ids(exposures, profile, 'exposures-values'), 'one accessible list per dimension').toHaveLength(3);
        expect(ids(exposures, profile, 'exposures-row')).toHaveLength(rows.length);
    });

    it('the PAC draws its three dimensions as two bars, never a bullet', () => {
        const exposures = mounted(PAC_PLANNER_PROFILE, PAC_ROWS);
        expect(ids(exposures, PAC_PLANNER_PROFILE, 'exposures-bars').map((chart) => chart.getAttribute('data-dimension'))).toEqual(['asset_type', 'sector', 'geography']);
        expect(ids(exposures, PAC_PLANNER_PROFILE, 'exposures-bullets')).toHaveLength(0);
    });
});
