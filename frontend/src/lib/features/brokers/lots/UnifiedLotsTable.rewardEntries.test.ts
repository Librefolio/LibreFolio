// @vitest-environment jsdom
/**
 * UnifiedLotsTable — the rewards that entered a lot (86, D-22; Vitest + jsdom).
 *
 * The contract. In the «Rewards in lots» view each lot a reward joined has `REWARD_MERGE` rows in the lot events. Such a lot
 * shows a chevron and how many rewards entered it (`reward-entries-toggle`, `data-state` open|closed); open, one row per
 * reward follows it, in date order, whatever the sort: its day, the reward tag and the units the lot took
 * (`reward-entry`, `reward-entry-units`), nothing else. Those rows are not lots: no checkbox, no selection, no total, no
 * action. Without such events the table is the table it was.
 *
 * Rows are read by `tr[data-row-id]` (the lot id, or `reward-entry:<lot>:<transaction>`), never by position. No translated
 * text is written here: the tag and the units are compared with the catalogue's own keys.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import type {z} from 'zod';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {schemas} from '$lib/api';
import {_} from '$lib/i18n';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import UnifiedLotsTable from './UnifiedLotsTable.svelte';

type LotSummary = z.infer<typeof schemas.LotSummarySchema>;

const CURRENCY = 'EUR';

function lot(id: number, date: string, pnl: number): LotSummary {
    return schemas.LotSummarySchema.parse({
        lot_id: id,
        opening_transaction_id: id,
        opening_kind: 'BUY',
        asset_id: 6,
        direction: 'LONG',
        opening_broker_id: 1,
        opening_date: date,
        opening_unit_price: '10',
        original_quantity: '10',
        original_cost: '100',
        open_quantity: '10',
        realized_quantity: '0',
        states: ['OPEN'],
        current_custody: [],
        open_value: '100',
        total_pnl: String(pnl),
        total_return: String(pnl / 100),
        net_total_pnl: String(pnl),
        net_total_return: String(pnl / 100),
    });
}

const LOTS = [lot(1, '2024-01-10', 30), lot(2, '2024-02-10', 10), lot(3, '2024-03-10', 50)];
const merge = (lotId: number, transactionId: number, date: string, quantity: string) => ({lot_id: lotId, kind: 'REWARD_MERGE', transaction_id: transactionId, date, quantity});
/** Two rewards joined lots 1 and 2 (listed out of date order), one reward joined lot 1 alone; a SPLIT and an opening are not rewards. */
const EVENTS = [merge(1, 92, '2024-05-01', '0.75'), merge(1, 91, '2024-04-01', '0.5'), merge(2, 91, '2024-04-01', '0.25'), {lot_id: 3, kind: 'SPLIT', transaction_id: 80, date: '2024-04-15', quantity: '10'}, {lot_id: 3, kind: 'BUY', transaction_id: 3, date: '2024-03-10', quantity: '10'}];

function mount(props: Record<string, unknown> = {}) {
    const onSelectionChange = vi.fn();
    const view = render(UnifiedLotsTable, {lots: LOTS, currency: CURRENCY, brokers: [], onSelectionChange, lotEvents: EVENTS, ...props});
    return {...view, onSelectionChange};
}

const rowIds = () => [...document.querySelectorAll('tbody tr[data-row-id]')].map((el) => el.getAttribute('data-row-id') ?? '');
const rowOf = (id: string) => document.querySelector<HTMLElement>(`tbody tr[data-row-id="${id}"]`)!;
const toggle = (lotId: number) => within(rowOf(String(lotId))).getByTestId('reward-entries-toggle');
const open = async (lotId: number) => {
    await fireEvent.click(toggle(lotId));
    await waitFor(() => expect(toggle(lotId)).toHaveAttribute('data-state', 'open'));
};

beforeAll(async () => {
    await setupI18n('en');
});
afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

describe('the rewards that entered a lot', () => {
    it('a lot with rewards says how many, closed; a lot without has no chevron', () => {
        mount();
        expect(rowIds()).toEqual(['1', '2', '3']);
        expect(toggle(1)).toHaveAttribute('data-state', 'closed');
        expect(toggle(1)).toHaveTextContent(get(_)('brokers.lots.rewardGroup.title', {values: {n: 2}}));
        expect(toggle(2)).toHaveTextContent(get(_)('brokers.lots.rewardGroup.title', {values: {n: 1}}));
        expect(within(rowOf('3')).queryByTestId('reward-entries-toggle')).toBeNull();
        expect(screen.queryByTestId('reward-lot-tag'), 'the lot itself is a BUY: no tag').toBeNull();
    });

    it('opens on its chevron: one row per reward, in date order, with its tag and the units the lot took; closes again', async () => {
        mount();
        await open(1);
        expect(rowIds()).toEqual(['1', 'reward-entry:1:91', 'reward-entry:1:92', '2', '3']);
        const first = rowOf('reward-entry:1:91');
        expect(within(first).getByTestId('reward-lot-tag')).toHaveTextContent(get(_)('transactions.types.REWARD'));
        expect(within(first).getByTestId('reward-entry-units').textContent).toMatch(/0[.,]5/);
        expect(within(rowOf('reward-entry:1:92')).getByTestId('reward-entry-units').textContent).toMatch(/0[.,]75/);
        await fireEvent.click(toggle(1));
        await waitFor(() => expect(rowIds()).toEqual(['1', '2', '3']));
    });

    it('its rows hold nothing but the first cell, and no figure of the lot', async () => {
        mount();
        await open(1);
        const cells = [...rowOf('reward-entry:1:91').querySelectorAll('td')].map((td) => (td.textContent ?? '').trim());
        expect(cells.filter((text) => text !== '')).toHaveLength(1);
        expect(rowOf('reward-entry:1:91').textContent).not.toContain(formatCurrencyAmountPlain(30, CURRENCY, {showSign: true}));
    });

    it('an open lot keeps its rewards under it when the table is sorted, in both directions', async () => {
        mount();
        await open(1);
        await fireEvent.click(screen.getByTestId('dt-sort-total-pnl'));
        await waitFor(() => expect(rowIds()).toEqual(['2', '1', 'reward-entry:1:91', 'reward-entry:1:92', '3']));
        await fireEvent.click(screen.getByTestId('dt-sort-total-pnl'));
        await waitFor(() => expect(rowIds()).toEqual(['3', '1', 'reward-entry:1:91', 'reward-entry:1:92', '2']));
    });

    it('is not a lot: no checkbox, a click selects nothing, and the totals count the lots once', async () => {
        const {onSelectionChange} = mount();
        const total = () => (screen.getByTestId('dt-footer-total-pnl').textContent ?? '').trim();
        const before = total();
        expect(before).toBe(formatCurrencyAmountPlain(90, CURRENCY, {showSign: true}));
        await open(1);
        expect(screen.queryByTestId('dt-row-checkbox-reward-entry:1:91')).toBeNull();
        onSelectionChange.mockClear();
        await fireEvent.click(rowOf('reward-entry:1:91'));
        expect(onSelectionChange.mock.calls.some(([ids]) => (ids as number[]).length > 0)).toBe(false);
        expect(total()).toBe(before);
    });

    it('its lot selected: the parent gets the lot id alone', async () => {
        const {onSelectionChange} = mount();
        await open(1);
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-1'));
        await waitFor(() => expect(onSelectionChange.mock.calls.at(-1)?.[0]).toEqual([1]));
    });

    it('masks the units with the privacy toggle, both ways', async () => {
        mount();
        await open(1);
        const units = () => within(rowOf('reward-entry:1:91')).getByTestId('reward-entry-units').textContent;
        setPrivacyEnabled(true);
        await waitFor(() => expect(units()).toContain(PRIVACY_PLACEHOLDER));
        setPrivacyEnabled(false);
        await waitFor(() => expect(units()).not.toContain(PRIVACY_PLACEHOLDER));
    });

    it('without rewards in the events the table is the table it was', async () => {
        mount({lotEvents: EVENTS.filter((event) => event.kind !== 'REWARD_MERGE')});
        expect(screen.queryByTestId('reward-entries-toggle')).toBeNull();
        await fireEvent.click(screen.getByTestId('dt-sort-total-pnl'));
        await waitFor(() => expect(rowIds()).toEqual(['2', '1', '3']));
    });
});
