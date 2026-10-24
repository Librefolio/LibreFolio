// @vitest-environment jsdom
/**
 * AllocationPanel.asset.test.ts — Y5-2 (#48): the fourth tab of the allocation panel, «By Asset», and what the panel
 * hands the two charts it reuses for it.
 *
 * ## The subject
 *
 * The backend sends the asset dimension as `summary.allocation_by_asset` (the «now» pie) and `allocationHistory.asset`
 * (the history), both lists of `AllocationItem {name, value, amount, id}`: an asset slice carries the asset's `id`, the
 * `Liquidity` slice carries none. On the asset tab the panel:
 *
 * - hands `AllocationPieChart` the positive entries of `allocation_by_asset`, carrying their `id`, in `mode="asset"`,
 *   with the bottom legend and the display currency;
 * - hands `AllocationHistoryChart` `allocationHistory.asset` with `dimension="asset"`;
 * - hands both the same `colorRanks`, `rankAssetsByWeight(today, history)` (`positionsSeries.ts`): the assets held today
 *   by weight, then the ones that left the portfolio, the one closed most recently first. One rank per asset, so the pie,
 *   the history and the lines of the Dashboard agree on a colour;
 * - shows the negative-cash note, like the type and sector tabs: the `Liquidity` slice is in the list.
 *
 * ## How it is read
 *
 * Both charts are replaced by stand-ins that keep the props object the panel mounts them with (a Svelte 5 component is a
 * function of an anchor and a props object whose getters read the panel's state when read — the technique of
 * `AllocationPanel.negativeCash.test.ts`, which wraps the real pie; here nobody reads pixels, so nothing is drawn).
 * Assertions read the props at the end of the case. Nothing translated is asserted.
 *
 * `echarts` and `$lib/api` are replaced for the one chart the panel still mounts for real (the map of the geography tab,
 * not shown here) and the reference data loads, as in `AllocationPanel.test.ts`; `localStorage` is a Map, because on
 * Node 26 the global is undefined.
 *
 * ## The fixture
 *
 * Alpha (11) is the heaviest held asset, Beta (12) the second; Gamma (13) was sold after 2025-01-02 and Delta (14) after
 * 2025-01-01, so Gamma ranks before Delta; the cash (no id) has no rank. Ranks: Alpha 0, Beta 1, Gamma 2, Delta 3.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const {pieMounts, historyMounts} = vi.hoisted(() => ({
    /** The props object of every AllocationPieChart the panel mounted, in mount order. */
    pieMounts: [] as Array<Record<string, unknown>>,
    /** The props object of every AllocationHistoryChart the panel mounted, in mount order. */
    historyMounts: [] as Array<Record<string, unknown>>,
}));

vi.mock('echarts', () => ({
    init: (dom: HTMLElement) => ({
        setOption: () => {},
        getOption: () => ({}),
        getDom: () => dom,
        getWidth: () => 0,
        getHeight: () => 0,
        on: () => {},
        off: () => {},
        dispatchAction: () => {},
        resize: () => {},
        clear: () => {},
        isDisposed: () => false,
        dispose: () => {},
    }),
}));

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => ({items: []}));
            },
        },
    ),
}));

vi.mock('$lib/components/charts/AllocationPieChart.svelte', () => ({
    default: function RecordedPie(_anchor: unknown, props: Record<string, unknown>): void {
        pieMounts.push(props);
    },
}));

vi.mock('$lib/features/dashboard/AllocationHistoryChart.svelte', () => ({
    default: function RecordedHistory(_anchor: unknown, props: Record<string, unknown>): void {
        historyMounts.push(props);
    },
}));

const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
});

import {render, screen, setupI18n, waitFor} from '$test/component';
import {getUserStorageKey} from '$lib/utils/storage';
import type {AllocationHistoryDimensions, PortfolioSummary} from '$lib/stores/portfolio/portfolioStore.svelte';
import AllocationPanel from './AllocationPanel.svelte';

// =============================================================================
// Fixtures — the backend's numbers
// =============================================================================

/** One `AllocationItem` of the asset dimension: share and amount are decimal strings, `id` the asset's (null for the cash). */
interface Item {
    name: string;
    value: string;
    amount: string;
    id: number | null;
}

const item = (name: string, value: string, amount: string, id: number | null): Item => ({name, value, amount, id});

/** Today: Alpha 6000, Beta 3000, the cash 1000. Sorted as the backend sorts them, by amount. */
const TODAY: Item[] = [item('Alpha', '60.00', '6000.00', 11), item('Beta', '30.00', '3000.00', 12), item('Liquidity', '10.00', '1000.00', null)];

/** The same portfolio overdrawn: positions 12 000, cash −2 000, shares on the net total. */
const OVERDRAWN: Item[] = [item('Alpha', '70.00', '7000.00', 11), item('Beta', '50.00', '5000.00', 12), item('Liquidity', '-20.00', '-2000.00', null)];

/** The history: Gamma and Delta are gone today; Delta was last held on the first day, Gamma on the second. */
const HISTORY: Array<{date: string; components: Item[]}> = [
    {date: '2025-01-01', components: [item('Alpha', '40.00', '4000.00', 11), item('Gamma', '20.00', '2000.00', 13), item('Delta', '30.00', '3000.00', 14), item('Liquidity', '10.00', '1000.00', null)]},
    {date: '2025-01-02', components: [item('Alpha', '50.00', '5000.00', 11), item('Gamma', '40.00', '4000.00', 13), item('Liquidity', '10.00', '1000.00', null)]},
    {date: '2025-01-03', components: [item('Alpha', '60.00', '6000.00', 11), item('Beta', '30.00', '3000.00', 12), item('Liquidity', '10.00', '1000.00', null)]},
];

/** The ranks the fixture gives, spelled out: the heaviest held first, then the closed ones, the most recently closed first. */
const EXPECTED_RANKS = {11: 0, 12: 1, 13: 2, 14: 3};

function summaryWith(byAsset: Item[]): PortfolioSummary {
    // The generated client does not know the asset dimension yet: the summary is built with a cast, as AllocationPanel.negativeCash.test.ts does.
    return {allocation_by_type: [], allocation_by_sector: [], allocation_by_geography: [], allocation_by_asset: byAsset} as unknown as PortfolioSummary;
}

const HISTORY_DIMENSIONS = {type: [], sector: [], geography: [], asset: HISTORY} as unknown as AllocationHistoryDimensions;

// =============================================================================
// Mounting and reading
// =============================================================================

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    storage.clear();
    pieMounts.length = 0;
    historyMounts.length = 0;
});

/** Mounts the panel on `view` and the asset tab, as a user who left it there finds it. */
function mountOnAssetTab(view: 'now' | 'history', byAsset: Item[] = TODAY): void {
    storage.set(getUserStorageKey('dashboard-allocation-view'), view);
    storage.set(getUserStorageKey('dashboard-allocation-tab'), 'asset');
    render(AllocationPanel, {
        summary: summaryWith(byAsset),
        loading: false,
        displayCurrency: 'EUR',
        brokerIds: undefined,
        currentLanguage: 'en',
        allocationHistory: HISTORY_DIMENSIONS,
        onRequestAllocationHistory: vi.fn(async () => {}),
    });
}

/** The props of the pie mounted last. Fails when the panel mounted none. */
function pie(): Record<string, unknown> {
    const props = pieMounts.at(-1);
    if (!props) throw new Error('the panel mounted no AllocationPieChart');
    return props;
}

/** The props of the history chart mounted last. Fails when the panel mounted none. */
function history(): Record<string, unknown> {
    const props = historyMounts.at(-1);
    if (!props) throw new Error('the panel mounted no AllocationHistoryChart');
    return props;
}

/** A rank map as a plain object, so a red names the asset ids and their ranks. */
function ranksOf(props: Record<string, unknown>): Record<number, number> {
    const ranks = props.colorRanks;
    if (!(ranks instanceof Map)) throw new Error(`colorRanks is not a Map: ${String(ranks)}`);
    return Object.fromEntries(ranks);
}

// =============================================================================
// The «now» view
// =============================================================================

describe('AllocationPanel — the asset tab, Now view (Y5-2)', () => {
    it('draws the asset pie: mode asset, the positive entries with their id, the bottom legend, the display currency', async () => {
        // CONTRACT: `allocation_by_asset` goes to the pie as `{name, value, amount, id}` entries, value > 0 only, in
        // `mode="asset"`. RED TODAY: the tab does not exist, the panel mounts no asset pie.
        mountOnAssetTab('now');
        await waitFor(() => expect(screen.getByTestId('allocation-tab-asset')).toHaveAttribute('aria-pressed', 'true'));

        const props = pie();
        expect(props.mode).toBe('asset');
        expect(props.legendPosition).toBe('bottom');
        expect(props.currency).toBe('EUR');
        const entries = props.data as Array<{name: string; value: number; amount: number; id?: number | null}>;
        expect(entries.map(({name, value, amount, id}) => ({name, value, amount, id: id ?? null}))).toEqual([
            {name: 'Alpha', value: 60, amount: 6000, id: 11},
            {name: 'Beta', value: 30, amount: 3000, id: 12},
            {name: 'Liquidity', value: 10, amount: 1000, id: null},
        ]);
    });

    it('hands the pie the colour ranks of rankAssetsByWeight: the heaviest held asset 0, a closed asset after the held ones, the cash none', async () => {
        // CONTRACT: `colorRanks` = rankAssetsByWeight(today, history), so the heaviest held asset (Alpha) is rank 0,
        // Beta rank 1, then the closed ones, the most recently closed first (Gamma before Delta). RED TODAY: no pie.
        mountOnAssetTab('now');
        await waitFor(() => expect(screen.getByTestId('allocation-tab-asset')).toHaveAttribute('aria-pressed', 'true'));

        expect(ranksOf(pie())).toEqual(EXPECTED_RANKS);
    });

    it('only the positive entries reach the pie when the cash is overdrawn, and the note says so, as on the type and sector tabs', async () => {
        // CONTRACT: decision 49 reaches the asset tab: the negative `Liquidity` slice is not drawn (an arc cannot be
        // negative) and the note `allocation-negative-cash-note` states it. RED TODAY: no asset tab.
        mountOnAssetTab('now', OVERDRAWN);
        await waitFor(() => expect(screen.getByTestId('allocation-tab-asset')).toHaveAttribute('aria-pressed', 'true'));

        const entries = pie().data as Array<{name: string}>;
        expect(entries.map(({name}) => name)).toEqual(['Alpha', 'Beta']);
        expect(screen.getByTestId('allocation-negative-cash-note')).toBeInTheDocument();
    });

    it('shows no negative-cash note when the cash is positive', async () => {
        // CONTRACT: no overdraft, no note. The presence barrier is the pie mounted with its entries: the view where a note would sit is on screen.
        mountOnAssetTab('now');
        await waitFor(() => expect(screen.getByTestId('allocation-tab-asset')).toHaveAttribute('aria-pressed', 'true'));
        expect((pie().data as unknown[]).length).toBeGreaterThan(0);

        expect(screen.queryByTestId('allocation-negative-cash-note')).toBeNull();
    });
});

// =============================================================================
// The History view
// =============================================================================

describe('AllocationPanel — the asset tab, History view (Y5-2)', () => {
    it('draws the history of allocationHistory.asset with dimension asset and the same colour ranks as the pie', async () => {
        // CONTRACT: the history chart gets `allocationHistory.asset` (the closed assets are components of the days they
        // were held), `dimension="asset"` and the SAME ranks as the pie, so an asset is one colour in both. RED TODAY:
        // there is no asset tab, the chart keeps the dimension of the stored tab's fallback.
        mountOnAssetTab('history');
        await waitFor(() => expect(screen.getByTestId('allocation-tab-asset')).toHaveAttribute('aria-pressed', 'true'));

        const props = history();
        expect(props.dimension).toBe('asset');
        expect(props.data).toEqual(HISTORY);
        expect(ranksOf(props)).toEqual(EXPECTED_RANKS);
    });
});
