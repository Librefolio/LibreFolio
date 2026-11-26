// @vitest-environment jsdom
/**
 * AllocationResults — the chart and the toggles over the table (Vitest + jsdom, the charts and the table stubbed: they need a canvas
 * and have their own specs): which chart each dimension draws, what it is given, the base in the pie's middle (masked, both ways),
 * and the History view's three states.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';

const mocks = vi.hoisted(() => ({pie: vi.fn(), map: vi.fn(), history: vi.fn(), table: vi.fn(), matrix: vi.fn()}));
vi.mock('$lib/components/charts/AllocationPieChart.svelte', () => ({default: mocks.pie}));
vi.mock('$lib/components/charts/GeographyMap.svelte', () => ({default: mocks.map}));
vi.mock('$lib/features/dashboard/AllocationHistoryChart.svelte', () => ({default: mocks.history}));
vi.mock('./AllocationTable.svelte', () => ({default: mocks.table}));
vi.mock('./AllocationMatrix.svelte', () => ({default: mocks.matrix}));

import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import AllocationResults from './AllocationResults.svelte';
import {makeView} from './allocation.fixture';
import {emptyFilters} from './allocationFilters';
import type {AllocationDimension, AllocationResponse} from './allocationQuery';

beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => {
    for (const mock of Object.values(mocks)) mock.mockReset();
    setPrivacyEnabled(false);
    window.matchMedia = ((query: string) => ({matches: true, media: query, addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {}, onchange: null, dispatchEvent: () => false})) as unknown as typeof window.matchMedia;
});
afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

const lastProps = (mock: ReturnType<typeof vi.fn>) => mock.mock.calls.at(-1)?.[1] as Record<string, unknown>;

function mount(overrides: {view?: Partial<AllocationResponse>; dimension?: AllocationDimension; mode?: 'now' | 'history'; loading?: boolean} = {}) {
    const dimension = overrides.dimension ?? overrides.view?.dimension ?? 'sector';
    const onDimension = vi.fn();
    const onMode = vi.fn();
    const onFilters = vi.fn();
    render(AllocationResults, {view: makeView({dimension, ...overrides.view}), dimension, onDimension, mode: overrides.mode ?? 'now', onMode, loading: overrides.loading ?? false, filters: emptyFilters(), onFilters, testId: 'r'});
    return {onDimension, onMode};
}

describe('Area', () => {
    it('draws the map on the selection, with the line that says what the colours are, and no pie', () => {
        mount({
            dimension: 'geography',
            view: {
                slices: [
                    {key: 'USA', asset_id: null, amount: '23600.00', share_of_selection: '64.00', share_of_portfolio: '29.50', assets: []},
                    {key: 'Unknown', asset_id: null, amount: '4120.00', share_of_selection: '1.00', share_of_portfolio: '5.00', assets: []},
                ],
            },
        });
        expect(mocks.pie).not.toHaveBeenCalled();
        expect(lastProps(mocks.map)).toMatchObject({data: {USA: 0.64}, amounts: {USA: 23600}, currency: 'EUR'});
        expect(screen.getByTestId('r-map-caption').textContent).toContain('46');
        expect(screen.queryByTestId('r-center')).toBeNull();
    });
});

describe('Sector, Type, Asset', () => {
    it.each([['sector'], ['type'], ['asset']] as const)('%s: the pie with the entries of the slices, the legend below, and the base in its middle', (dimension) => {
        mount({dimension});
        expect(mocks.map).not.toHaveBeenCalled();
        const pie = lastProps(mocks.pie);
        expect(pie).toMatchObject({mode: dimension, legendPosition: 'bottom', currency: 'EUR'});
        expect((pie.data as Array<{name: string}>).map((entry) => entry.name)).toEqual(['USA', 'Unknown']);
        expect(screen.getByTestId('r-center').textContent).toContain('36');
        expect(screen.getByTestId('r-center')).toHaveStyle({top: dimension === 'asset' ? '50%' : '40%'});
    });

    it('the middle of the pie holds the amount and nothing else (86, A5)', () => {
        mount();
        expect(screen.getByTestId('r-center').children).toHaveLength(1);
        expect(screen.getByTestId('r-center').firstElementChild).toHaveClass('font-semibold');
    });

    it('masks the base in the middle and shows it again, in place', async () => {
        mount();
        expect(screen.getByTestId('r-center').textContent).not.toContain(PRIVACY_PLACEHOLDER);
        setPrivacyEnabled(true);
        await Promise.resolve();
        await vi.waitFor(() => expect(screen.getByTestId('r-center').textContent).toContain(PRIVACY_PLACEHOLDER));
        expect(screen.getByTestId('r-center').textContent).not.toContain('36');
        setPrivacyEnabled(false);
        await Promise.resolve();
        await vi.waitFor(() => expect(screen.getByTestId('r-center').textContent).not.toContain(PRIVACY_PLACEHOLDER));
    });
});

describe('a selection with no shares, or with the cash below zero', () => {
    const noShareSlices = [
        {key: 'Liquidity', asset_id: null, amount: '-500.00', share_of_selection: null, share_of_portfolio: null, assets: []},
        {key: 'STOCK', asset_id: null, amount: '300.00', share_of_selection: null, share_of_portfolio: null, assets: []},
    ];

    it('says so instead of drawing equal slices of nothing: no pie, no map, the table stays', () => {
        mount({dimension: 'type', view: {slices: noShareSlices}});
        expect(screen.getByTestId('r-no-shares')).toBeInTheDocument();
        expect(mocks.pie).not.toHaveBeenCalled();
        expect(screen.queryByTestId('r-center')).toBeNull();
        expect(lastProps(mocks.table)).toMatchObject({testId: 'r-table'});
        cleanup();
        mocks.map.mockClear();
        mount({dimension: 'geography', view: {slices: noShareSlices}});
        expect(mocks.map).not.toHaveBeenCalled();
    });

    it('notes the cash below zero, masked under privacy and shown again, and draws the pie as usual when shares exist', async () => {
        mount({
            dimension: 'type',
            view: {
                slices: [
                    {key: 'Liquidity', asset_id: null, amount: '-500.00', share_of_selection: '-10.00', share_of_portfolio: '-5.00', assets: []},
                    {key: 'STOCK', asset_id: null, amount: '5500.00', share_of_selection: '110.00', share_of_portfolio: '55.00', assets: []},
                ],
            },
        });
        expect(mocks.pie).toHaveBeenCalled();
        expect(screen.getByTestId('r-negative-cash').textContent).toContain('500');
        setPrivacyEnabled(true);
        await Promise.resolve();
        await vi.waitFor(() => expect(screen.getByTestId('r-negative-cash').textContent).toContain(PRIVACY_PLACEHOLDER));
        expect(screen.getByTestId('r-negative-cash').textContent).not.toContain('500');
        setPrivacyEnabled(false);
        await Promise.resolve();
        await vi.waitFor(() => expect(screen.getByTestId('r-negative-cash').textContent).toContain('500'));
    });

    it('has no note with the cash at zero or above, and none in the History view', () => {
        mount();
        expect(screen.queryByTestId('r-negative-cash')).toBeNull();
        cleanup();
        mount({mode: 'history', dimension: 'type', view: {slices: [{key: 'Liquidity', asset_id: null, amount: '-500.00', share_of_selection: '-10.00', share_of_portfolio: null, assets: []}], history: []}});
        expect(screen.queryByTestId('r-negative-cash')).toBeNull();
    });
});

describe('the table and the matrix', () => {
    it('are always under the chart, given the answer; the matrix also gets the filters and a way to change them', () => {
        mount();
        expect(lastProps(mocks.table)).toMatchObject({testId: 'r-table'});
        expect(lastProps(mocks.matrix)).toMatchObject({testId: 'r-matrix', filters: emptyFilters()});
        expect(typeof lastProps(mocks.matrix).onchange).toBe('function');
    });

    it('stay in the History view too (the matrix is the whole portfolio, whatever the view)', () => {
        mount({mode: 'history', view: {history: []}});
        expect(mocks.matrix).toHaveBeenCalled();
    });
});

describe('toggles', () => {
    it('ask for the other dimension and for the other view', async () => {
        const {onDimension, onMode} = mount();
        await fireEvent.click(screen.getByTestId('r-dimension-asset'));
        expect(onDimension).toHaveBeenCalledWith('asset');
        await fireEvent.click(screen.getByTestId('r-view-history'));
        expect(onMode).toHaveBeenCalledWith('history');
        expect(screen.getByTestId('r-view-now')).toHaveAttribute('aria-pressed', 'true');
    });
});

describe('History', () => {
    const step = {date: '2026-01-01', through: '2026-06-30', base: '100.00', components: [{name: 'USA', value: '100.00', amount: '100.00', emoji: null, id: null}]};

    it('waits for the history while the answer has none, and says so', () => {
        mount({mode: 'history', view: {history: null}});
        expect(screen.getByTestId('r-history-loading')).toBeInTheDocument();
        expect(mocks.history).not.toHaveBeenCalled();
        expect(mocks.pie).not.toHaveBeenCalled();
    });

    it('says there is none for a selection with no step', () => {
        mount({mode: 'history', view: {history: []}});
        expect(screen.getByTestId('r-history-empty')).toBeInTheDocument();
    });

    it('draws the chart with the steps; the Area dimension is «geo» for it', () => {
        mount({mode: 'history', dimension: 'geography', view: {history: [step]}});
        expect(lastProps(mocks.history)).toMatchObject({data: [step], dimension: 'geo'});
        expect(screen.getByTestId('r-history')).toBeInTheDocument();
    });

    it('does not take the history of another dimension for this one', () => {
        mount({mode: 'history', dimension: 'type', view: {dimension: 'sector', history: [step]}});
        expect(screen.getByTestId('r-history-loading')).toBeInTheDocument();
        expect(mocks.history).not.toHaveBeenCalled();
    });
});
