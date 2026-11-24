// @vitest-environment jsdom
/**
 * PortfolioAllocationTab — the Allocazione tab (Vitest + jsdom, the API mocked at its edge): what it asks, when, and what it
 * shows. The panels have their own specs (`features/allocation`); here the page-level contract:
 *
 * - nothing is asked before the page can (`scope` null), and the same scope asks once;
 * - the body is the report's scope plus the tab's choices; a broker's page counts the broker whole;
 * - a filter is a new question, remembered under the page's own key; a bump of `refreshVersion` asks again;
 * - `data-busy` follows the request; a failure keeps the last answer and offers a retry;
 * - the filter panel is mounted once: a column on a wide screen, behind the «Filters» button on a narrow one.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';

const mocks = vi.hoisted(() => ({fetch: vi.fn(), results: vi.fn()}));
// The chart, the map and the table have their own specs; here they would need a canvas.
vi.mock('$lib/features/allocation/AllocationResults.svelte', () => ({default: mocks.results}));
vi.mock('$lib/api', async (importOriginal) => ({...(await importOriginal<typeof import('$lib/api')>()), zodiosApi: {get_portfolio_allocation_api_v1_portfolio_allocation_post: mocks.fetch}}));

import PortfolioAllocationTab from './PortfolioAllocationTab.svelte';
import {makeView} from '$lib/features/allocation/allocation.fixture';
import type {PortfolioScope} from './portfolioDataScope';

beforeAll(async () => {
    await setupI18n();
});

const scope: PortfolioScope = {brokerIds: [1, 2], start: '2025-11-23', end: '2026-11-23', currency: 'EUR', fullShare: false};
const props = (overrides: Record<string, unknown> = {}) => ({
    testId: 'alloc',
    page: {kind: 'portfolio'} as const,
    scope: scope as PortfolioScope | null,
    refreshVersion: 0,
    busyKey: 'dashboard-allocation',
    brokers: {kind: 'all'} as const,
    ...overrides,
});

function viewport(wide: boolean) {
    window.matchMedia = ((query: string) => ({matches: wide, media: query, addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {}, onchange: null, dispatchEvent: () => false})) as unknown as typeof window.matchMedia;
}

/** jsdom under Node has no usable `localStorage` here: a Map-backed one, the same interface the user-scoped helpers call. */
function memoryStorage(): Storage {
    const map = new Map<string, string>();
    return {
        get length() {
            return map.size;
        },
        clear: () => map.clear(),
        getItem: (key: string) => map.get(key) ?? null,
        key: (index: number) => [...map.keys()][index] ?? null,
        removeItem: (key: string) => void map.delete(key),
        setItem: (key: string, value: string) => void map.set(key, String(value)),
    } as Storage;
}

beforeEach(() => {
    vi.stubGlobal('localStorage', memoryStorage());
    mocks.fetch.mockReset();
    mocks.results.mockReset();
    mocks.fetch.mockImplementation(async () => makeView());
    viewport(true);
});
afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

const calls = () => mocks.fetch.mock.calls.map((call) => call[0] as Record<string, unknown>);
const loaded = () => waitFor(() => expect(screen.getByTestId('alloc')).toHaveAttribute('data-busy', 'false'));

describe('asking', () => {
    it('asks nothing while the page cannot, and says it is loading', async () => {
        render(PortfolioAllocationTab, props({scope: null}));
        await Promise.resolve();
        expect(mocks.fetch).not.toHaveBeenCalled();
        expect(screen.getByTestId('alloc-loading')).toBeInTheDocument();
    });

    it('asks once with the report’s scope and the first-opening filters, busy until the answer lands', async () => {
        let answer!: (value: ReturnType<typeof makeView>) => void;
        mocks.fetch.mockImplementationOnce(() => new Promise((resolve) => (answer = resolve)));
        render(PortfolioAllocationTab, props());
        await waitFor(() => expect(mocks.fetch).toHaveBeenCalledTimes(1));
        expect(calls()[0]).toEqual({dimension: 'sector', broker_ids: [1, 2], date_range: {start: '2025-11-23', end: '2026-11-23'}, target_currency: 'EUR'});
        expect(screen.getByTestId('alloc')).toHaveAttribute('data-busy', 'true');
        expect(screen.getByTestId('alloc')).toHaveAttribute('aria-busy', 'true');
        answer(makeView());
        await loaded();
        expect(screen.getByTestId('alloc-tiles')).toBeInTheDocument();
        expect(mocks.fetch).toHaveBeenCalledTimes(1);
    });

    it('a broker’s page counts the broker whole and remembers its filters under its own key', async () => {
        render(PortfolioAllocationTab, props({page: {kind: 'broker', brokerId: 7}, scope: {...scope, brokerIds: [7], fullShare: true}, brokers: {kind: 'this'}}));
        await loaded();
        expect(calls()[0]).toMatchObject({broker_ids: [7], apply_ownership_share: false});

        await fireEvent.click(screen.getByTestId('alloc-filters-class-BOND-switch'));
        await loaded();
        const stored = (suffix: string) => Array.from({length: localStorage.length}, (_, index) => localStorage.key(index) ?? '').filter((key) => key.endsWith(suffix));
        const keys = stored('allocation-filters:broker:7');
        expect(keys).toHaveLength(1);
        expect(stored('allocation-filters:dashboard')).toHaveLength(0);
    });

    it('asks again when the page bumps its refresh version, not when the same scope is passed again', async () => {
        const {rerender} = render(PortfolioAllocationTab, props());
        await loaded();
        await rerender(props({scope: {...scope}}));
        await Promise.resolve();
        expect(mocks.fetch).toHaveBeenCalledTimes(1);
        await rerender(props({refreshVersion: 1}));
        await waitFor(() => expect(mocks.fetch).toHaveBeenCalledTimes(2));
    });

    it('asks again when the scope changes (another currency)', async () => {
        const {rerender} = render(PortfolioAllocationTab, props());
        await loaded();
        await rerender(props({scope: {...scope, currency: 'USD'}}));
        await waitFor(() => expect(mocks.fetch).toHaveBeenCalledTimes(2));
        expect(calls()[1]).toMatchObject({target_currency: 'USD'});
    });
});

describe('filters', () => {
    it('a choice is a new question with the filters in it, and the subtitle says the selection', async () => {
        render(PortfolioAllocationTab, props());
        await loaded();
        expect(screen.getByTestId('alloc-subtitle').textContent).toContain(' · ');

        await fireEvent.click(screen.getByTestId('alloc-filters-class-BOND-switch'));
        await waitFor(() => expect(mocks.fetch).toHaveBeenCalledTimes(2));
        expect(calls()[1]).toMatchObject({classes: ['STOCK', 'Liquidity']});
        await loaded();

        await fireEvent.click(screen.getByTestId('alloc-filters-bucket-Unknown-switch'));
        await waitFor(() => expect(mocks.fetch).toHaveBeenCalledTimes(3));
        expect(calls()[2]).toMatchObject({classes: ['STOCK', 'Liquidity'], exclude_buckets: ['Unknown']});
    });

    it('opens on what the page remembered', async () => {
        const probe = render(PortfolioAllocationTab, props());
        await loaded();
        await fireEvent.click(screen.getByTestId('alloc-filters-asset-2-switch'));
        await loaded();
        probe.unmount();
        mocks.fetch.mockClear();

        render(PortfolioAllocationTab, props());
        await waitFor(() => expect(mocks.fetch).toHaveBeenCalledTimes(1));
        expect(calls()[0]).toMatchObject({exclude_asset_ids: [2]});
    });

    it('«Remove filters» goes back to the whole portfolio', async () => {
        render(PortfolioAllocationTab, props());
        await loaded();
        await fireEvent.click(screen.getByTestId('alloc-filters-class-BOND-switch'));
        await waitFor(() => expect(screen.getByTestId('alloc-filters-clear')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('alloc-filters-clear'));
        await waitFor(() => expect(calls().at(-1)).not.toHaveProperty('classes'));
    });
});

describe('states', () => {
    it('a first failure offers a retry, which asks again', async () => {
        mocks.fetch.mockRejectedValueOnce(new Error('boom'));
        render(PortfolioAllocationTab, props());
        await waitFor(() => expect(screen.getByTestId('alloc-failed')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('alloc-retry'));
        await waitFor(() => expect(screen.getByTestId('alloc-tiles')).toBeInTheDocument());
        expect(mocks.fetch).toHaveBeenCalledTimes(2);
    });

    it('a later failure keeps the last answer on screen, with a notice', async () => {
        const {rerender} = render(PortfolioAllocationTab, props());
        await loaded();
        mocks.fetch.mockRejectedValueOnce(new Error('boom'));
        await rerender(props({refreshVersion: 1}));
        await waitFor(() => expect(screen.getByTestId('alloc-failed')).toBeInTheDocument());
        expect(screen.getByTestId('alloc-tiles'), 'the screen does not blank').toBeInTheDocument();
    });

    it('says so when the scope holds nothing', async () => {
        mocks.fetch.mockImplementation(async () => makeView({classes: [], assets: [], as_of: null}));
        render(PortfolioAllocationTab, props());
        await waitFor(() => expect(screen.getByTestId('alloc-empty')).toBeInTheDocument());
        expect(screen.queryByTestId('alloc-tiles')).toBeNull();
    });
});

describe('the filter panel is mounted once', () => {
    it('in a column on a wide screen', async () => {
        viewport(true);
        render(PortfolioAllocationTab, props());
        await loaded();
        expect(screen.getByTestId('alloc-filters-column')).toBeInTheDocument();
        expect(screen.getAllByTestId('alloc-filters')).toHaveLength(1);
        expect(screen.queryByTestId('alloc-filters-button')).toBeNull();
    });

    it('behind the «Filters» button on a narrow one, with the choices as chips and their count on the button', async () => {
        viewport(false);
        render(PortfolioAllocationTab, props());
        await loaded();
        expect(screen.queryByTestId('alloc-filters-column')).toBeNull();
        expect(screen.queryByTestId('alloc-filters'), 'closed: not mounted').toBeNull();
        await fireEvent.click(screen.getByTestId('alloc-filters-button'));
        expect(screen.getAllByTestId('alloc-filters')).toHaveLength(1);

        await fireEvent.click(screen.getByTestId('alloc-filters-class-STOCK-switch'));
        await waitFor(() => expect(mocks.fetch).toHaveBeenCalledTimes(2));
        await loaded();
        expect(screen.getAllByTestId('alloc-chips-chip').length, 'the other two classes are kept').toBe(2);
        expect(screen.getByTestId('alloc-filters-button')).toHaveTextContent('2');
    });
});

describe('the results', () => {
    /** The props the (mocked) results component was last mounted or updated with. */
    const resultsProps = () => mocks.results.mock.calls.at(-1)?.[1] as {view: {dimension: string}; dimension: string; mode: string; onDimension: (next: string) => void; onMode: (next: string) => void};

    it('are given the answer, the dimension and the mode of the first opening', async () => {
        render(PortfolioAllocationTab, props());
        await loaded();
        await waitFor(() => expect(mocks.results).toHaveBeenCalled());
        expect(resultsProps().dimension).toBe('sector');
        expect(resultsProps().mode).toBe('now');
    });

    it('choosing another dimension is a new question for that dimension', async () => {
        render(PortfolioAllocationTab, props());
        await loaded();
        await waitFor(() => expect(mocks.results).toHaveBeenCalled());
        resultsProps().onDimension('geography');
        await waitFor(() => expect(mocks.fetch).toHaveBeenCalledTimes(2));
        expect(calls()[1]).toMatchObject({dimension: 'geography'});
        expect(calls()[1]).not.toHaveProperty('include_history');
    });

    it('«History» asks the same question with the history, and «Now» goes back to asking without it', async () => {
        render(PortfolioAllocationTab, props());
        await loaded();
        await waitFor(() => expect(mocks.results).toHaveBeenCalled());
        resultsProps().onMode('history');
        await waitFor(() => expect(mocks.fetch).toHaveBeenCalledTimes(2));
        expect(calls()[1]).toMatchObject({dimension: 'sector', include_history: true});
        await loaded();
        resultsProps().onMode('now');
        await waitFor(() => expect(mocks.fetch).toHaveBeenCalledTimes(3));
        expect(calls()[2]).not.toHaveProperty('include_history');
    });
});
