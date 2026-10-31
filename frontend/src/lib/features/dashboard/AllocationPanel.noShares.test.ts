// @vitest-environment jsdom
/**
 * AllocationPanel.noShares.test.ts — MF-C2 on the Dashboard: when the slices of a list add up to zero or less the backend
 * gives every slice a `null` percentage (`AllocationItem.value`), and keeps the amounts.
 *
 * ## The contract (`charts.en.md#allocation-negative-cash`)
 *
 * - the list has nothing to draw: the panel does not mount the pie (a `null` read as `0` left an empty pie, or kept the
 *   last one drawn), and says so, test id `allocation-no-shares`;
 * - each slice is listed with its amount and `—` in place of a percentage, test ids `allocation-no-shares-row` (with
 *   `data-slice`, the backend's name) holding `allocation-no-shares-percent` and `allocation-no-shares-amount`;
 * - a list with percentages draws as before and shows no such message;
 * - the geography tab follows the same rule.
 *
 * The sentence is not under test (its wording is a proposal): only its place, its rows and the dash. The amount is the
 * backend's, shown as the app's formatter writes it.
 *
 * Harness as `AllocationPanel.negativeCash.test.ts`: `echarts` a recorder, `$lib/api` answered empty, the currency
 * described, a Map for `localStorage`.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const {echartsModule, EUR_INFO} = vi.hoisted(() => {
    const createFakeChart = (dom: unknown) => {
        let disposed = false;
        return {
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
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
    };
    return {
        echartsModule: {init: (dom: unknown) => createFakeChart(dom), format: {getTextRect: (text: string) => ({x: 0, y: 0, width: text.length * 7, height: 14})}},
        EUR_INFO: {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [] as string[], country_names: [] as string[]},
    };
});

vi.mock('echarts', () => echartsModule);
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
vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    getCurrencyInfo: (code: string) => (code === EUR_INFO.code ? EUR_INFO : {code, name: code, symbol: code, flag_emoji: '🏳️', country_codes: [], country_names: []}),
}));

const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
});

import {render, screen, setupI18n, within} from '$test/component';
import {getUserStorageKey} from '$lib/utils/storage';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import type {PortfolioSummary} from '$lib/stores/portfolio/portfolioStore.svelte';
import AllocationPanel from './AllocationPanel.svelte';

interface Item {
    name: string;
    value: string | null;
    amount: string;
    emoji: string | null;
}
const item = (name: string, value: string | null, amount: string): Item => ({name, value, amount, emoji: null});

/** 500 of stocks bought on an overdraft of -500: the slices add up to zero, so no slice has a percentage. */
const NO_SHARES = [item('STOCK', null, '500.00'), item('Liquidity', null, '-500.00')];
const WITH_SHARES = [item('STOCK', '100.00', '1000.00')];

function mountPanel(tab: 'type' | 'sector' | 'geo' | 'asset', items: Item[]): void {
    storage.set(getUserStorageKey('dashboard-allocation-view'), 'now');
    storage.set(getUserStorageKey('dashboard-allocation-tab'), tab);
    const summary = {allocation_by_type: tab === 'type' ? items : WITH_SHARES, allocation_by_sector: tab === 'sector' ? items : WITH_SHARES, allocation_by_geography: tab === 'geo' ? items : WITH_SHARES, allocation_by_asset: tab === 'asset' ? items : WITH_SHARES};
    render(AllocationPanel, {
        summary: summary as unknown as PortfolioSummary,
        loading: false,
        displayCurrency: EUR_INFO.code,
        brokerIds: undefined,
        currentLanguage: 'en',
        allocationHistory: null,
        onRequestAllocationHistory: vi.fn(async () => {}),
    });
}

const readable = (text: string | null | undefined): string => (text ?? '').replace(/−/g, '-').replace(/\s+/g, ' ').trim();

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    storage.clear();
});

describe('AllocationPanel — slices without percentages (MF-C2)', () => {
    it.each(['type', 'sector', 'geo', 'asset'] as const)('%s: says there is nothing to draw and lists each slice with its amount and a dash', (tab) => {
        mountPanel(tab, NO_SHARES);
        expect(screen.getByTestId('allocation-no-shares')).toBeInTheDocument();
        const rows = screen.getAllByTestId('allocation-no-shares-row');
        expect(rows.map((row) => row.getAttribute('data-slice'))).toEqual(['STOCK', 'Liquidity']);
        for (const row of rows) expect(within(row).getByTestId('allocation-no-shares-percent').textContent?.trim()).toBe('—');
        const amounts = rows.map((row) => readable(within(row).getByTestId('allocation-no-shares-amount').textContent));
        expect(amounts).toEqual([500, -500].map((amount) => readable(formatCurrencyAmountPlain(amount, EUR_INFO.code))));
    });

    it('draws nothing in its place: neither a pie nor a map', () => {
        mountPanel('type', NO_SHARES);
        expect(screen.queryByTestId('allocation-now-chart')).toBeNull();
        expect(screen.queryByTestId('allocation-negative-cash-note'), 'the dash rows say it already').toBeNull();
    });

    it.each(['type', 'sector', 'geo', 'asset'] as const)('%s: a list with percentages is drawn as before, with no such message', (tab) => {
        mountPanel(tab, WITH_SHARES);
        expect(screen.queryByTestId('allocation-no-shares')).toBeNull();
        expect(screen.getByTestId('allocation-now-chart')).toBeInTheDocument();
    });
});
