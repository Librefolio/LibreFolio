// @vitest-environment jsdom
/**
 * UnifiedLotsTable — the reward lots group (project 79, STK-2c; mockup P-25, rules Q-5; Vitest + jsdom).
 *
 * The contract. The lots a REWARD opened at one broker (`opening_kind = REWARD`) become one group row when there are at
 * least two; one alone stays a normal row, none makes no group, and a table without a group is the table it was. The
 * group row is closed by default: its lots have no row until it opens, then they sit right under it. It publishes its
 * state on the head cell, `reward-group-head` (`data-group-id`, `data-state` open|closed, `aria-expanded`); a click on
 * the head cell or anywhere on its row opens or closes it, once. It sorts as one row on its own values (the sum of its
 * lots) and its lots, sorted the same way, stay under it. Selecting it selects all its lots (`onSelectionChange` gets lot
 * ids, never the group id); part of them selected draws its checkbox in the mixed state (`data-state="partial"`). The
 * footer counts each lot once: never the head beside its own lots.
 *
 * The harness. The component runs as in the app, with real i18n, the real DataTable and no module mocked. Every lot is
 * parsed by the generated client's own schema (`schemas.LotSummarySchema`), so a client that dropped `opening_kind`
 * would turn the builder's control red, not the table. No lot holds a custody slice and the broker list is empty, so no
 * broker icon is drawn. Rows are read by `tr[data-row-id]` (the lot id, or the group id `reward-group:<broker>`), never
 * by position; nothing translated is read: amounts are expected through the formatter the component calls, with the
 * options it passes.
 *
 * The book (broker 1, EUR): BUY lot 1 (10 Jan, P&L 30) and three REWARD lots, 11 (1 Feb, P&L 40), 12 (1 Mar, P&L 10)
 * and 13 (1 Apr, P&L 20). The group's P&L is 70, the four lots' 100. Sorted by P&L, a flat sort would interleave the
 * BUY lot with the reward lots; the group keeps them together.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import type {z} from 'zod';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {schemas} from '$lib/api';
import {_} from '$lib/i18n';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import UnifiedLotsTable from './UnifiedLotsTable.svelte';

type LotSummary = z.infer<typeof schemas.LotSummarySchema>;
type Kind = 'BUY' | 'REWARD' | 'ADJUSTMENT_IN';

const CURRENCY = 'EUR';
const GROUP = 'reward-group:1';

interface LotSpec {
    id: number;
    kind: Kind;
    date: string;
    pnl: number;
    /** Opening unit price; every lot is 10 units worth 100 now, so the footer's opening price is a plain mean. */
    price: number;
    broker?: number;
}

function lot({id, kind, date, pnl, price, broker = 1}: LotSpec): LotSummary {
    const parsed = schemas.LotSummarySchema.parse({
        lot_id: id,
        opening_transaction_id: id,
        opening_kind: kind,
        asset_id: 6,
        direction: 'LONG',
        opening_broker_id: broker,
        opening_date: date,
        opening_unit_price: String(price),
        original_quantity: '10',
        original_cost: String(price * 10),
        open_quantity: '10',
        realized_quantity: '0',
        states: ['OPEN'],
        current_custody: [],
        open_value: '100',
        total_pnl: String(pnl),
        total_return: String(pnl / (price * 10)),
        net_total_pnl: String(pnl),
        net_total_return: String(pnl / (price * 10)),
    });
    expect(parsed.opening_kind, 'control: the generated client keeps opening_kind').toBe(kind);
    return parsed;
}

const BUY_1: LotSpec = {id: 1, kind: 'BUY', date: '2024-01-10', pnl: 30, price: 10};
const REWARD_11: LotSpec = {id: 11, kind: 'REWARD', date: '2024-02-01', pnl: 40, price: 20};
const REWARD_12: LotSpec = {id: 12, kind: 'REWARD', date: '2024-03-01', pnl: 10, price: 20};
const REWARD_13: LotSpec = {id: 13, kind: 'REWARD', date: '2024-04-01', pnl: 20, price: 10};

/** The book of the header, in the order the backend sends it (lot id). */
const BOOK = [BUY_1, REWARD_11, REWARD_12, REWARD_13];

function mount(specs: LotSpec[] = BOOK, props: Record<string, unknown> = {}) {
    const onSelectionChange = vi.fn();
    const view = render(UnifiedLotsTable, {lots: specs.map(lot), currency: CURRENCY, brokers: [], onSelectionChange, ...props});
    return {...view, onSelectionChange};
}

/** The row ids in `<tbody>`, in DOM order. */
function rowIds(): string[] {
    return [...document.querySelectorAll('tbody tr[data-row-id]')].map((el) => el.getAttribute('data-row-id') ?? '');
}

function rowOf(id: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="${id}"]`);
    if (!el) throw new Error(`row ${id} is not shown (rows: ${rowIds().join(', ') || 'none'})`);
    return el;
}

const head = () => screen.getByTestId('reward-group-head');
const checkbox = (rowId: string) => screen.getByTestId(`dt-row-checkbox-${rowId}`);

/** The lot ids the parent was handed last, sorted. */
function lastSelection(spy: ReturnType<typeof vi.fn>): number[] | undefined {
    const ids = spy.mock.calls.at(-1)?.[0] as number[] | undefined;
    return ids ? [...ids].sort((a, b) => a - b) : undefined;
}

/** A signed amount as `signedAmountCell` writes it. */
function signed(value: number): string {
    return formatCurrencyAmountPlain(value, CURRENCY, {showSign: value !== 0});
}

const footerText = (columnId: string) => (screen.getByTestId(`dt-footer-${columnId}`).textContent ?? '').trim();

async function openGroup() {
    await fireEvent.click(head());
    await waitFor(() => expect(head()).toHaveAttribute('data-state', 'open'));
}

beforeAll(async () => {
    await setupI18n('en');
});

afterEach(() => {
    cleanup();
});

describe('UnifiedLotsTable — the reward lots group: shape', () => {
    it('draws one closed group row for three reward lots, beside the BUY lot; its lots have no row', async () => {
        mount();
        // Presence barrier: the BUY lot and the head are drawn
        expect(rowOf('1')).toBeInTheDocument();
        expect(rowOf(GROUP)).toBeInTheDocument();
        expect(screen.getAllByTestId('reward-group-head')).toHaveLength(1);
        expect(head()).toHaveAttribute('data-group-id', GROUP);
        expect(head()).toHaveAttribute('data-state', 'closed');
        expect(head()).toHaveAttribute('aria-expanded', 'false');
        expect(rowIds()).toEqual(['1', GROUP]);
    });

    it('opens on a click on its head cell: the lots follow it, in opening order; a second click closes it', async () => {
        mount();
        await openGroup();
        expect(head()).toHaveAttribute('aria-expanded', 'true');
        expect(rowIds()).toEqual(['1', GROUP, '11', '12', '13']);

        await fireEvent.click(head());
        await waitFor(() => expect(head()).toHaveAttribute('data-state', 'closed'));
        expect(rowIds()).toEqual(['1', GROUP]);
    });

    it('opens and closes on a click elsewhere on its row, and that click selects nothing', async () => {
        const {onSelectionChange} = mount();
        await fireEvent.click(rowOf(GROUP));
        await waitFor(() => expect(head()).toHaveAttribute('data-state', 'open'));
        expect(rowIds()).toEqual(['1', GROUP, '11', '12', '13']);
        expect(checkbox(GROUP)).toHaveAttribute('data-state', 'unchecked');
        expect(onSelectionChange.mock.calls.some(([ids]) => (ids as number[]).length > 0)).toBe(false);

        await fireEvent.click(rowOf(GROUP));
        await waitFor(() => expect(head()).toHaveAttribute('data-state', 'closed'));
    });

    it('leaves a single reward lot as a normal row: no group', async () => {
        mount([BUY_1, REWARD_11]);
        expect(rowIds()).toEqual(['1', '11']);
        expect(screen.queryByTestId('reward-group-head')).toBeNull();
    });

    it('without a reward lot the table is the table it was: the lots as given, no group, sorted by the table itself', async () => {
        const book: LotSpec[] = [BUY_1, {...REWARD_11, kind: 'BUY'}, {...REWARD_12, kind: 'ADJUSTMENT_IN'}, {...REWARD_13, kind: 'BUY'}];
        mount(book);
        expect(rowIds()).toEqual(['1', '11', '12', '13']);
        expect(screen.queryByTestId('reward-group-head')).toBeNull();
        expect(['1', '11', '12', '13'].map((id) => checkbox(id).getAttribute('data-state'))).toEqual(['unchecked', 'unchecked', 'unchecked', 'unchecked']);

        await fireEvent.click(screen.getByTestId('dt-sort-total-pnl'));
        expect(rowIds()).toEqual(['12', '13', '1', '11']);
    });

    it('makes one group per broker', async () => {
        const otherBroker: LotSpec[] = [
            {id: 21, kind: 'REWARD', date: '2024-02-15', pnl: 1, price: 10, broker: 2},
            {id: 22, kind: 'REWARD', date: '2024-03-15', pnl: 2, price: 10, broker: 2},
        ];
        mount([...BOOK, ...otherBroker]);
        const groups = screen.getAllByTestId('reward-group-head').map((el) => el.getAttribute('data-group-id'));
        expect(new Set(groups)).toEqual(new Set([GROUP, 'reward-group:2']));
        expect(rowIds().filter((id) => /^\d+$/.test(id))).toEqual(['1']);
    });

    it('with no sort, sits where its first lot is in the lots order: before a BUY that came after its first reward', async () => {
        // The lots as the backend sends them: REWARD 1 Jan, BUY 1 Feb, REWARD 1 Mar, REWARD 1 Apr
        const book: LotSpec[] = [
            {id: 2, kind: 'REWARD', date: '2024-01-05', pnl: 5, price: 10},
            {id: 3, kind: 'BUY', date: '2024-02-01', pnl: 30, price: 10},
            {id: 4, kind: 'REWARD', date: '2024-03-01', pnl: 6, price: 10},
            {id: 5, kind: 'REWARD', date: '2024-04-01', pnl: 7, price: 10},
        ];
        mount(book);
        expect(screen.getByTestId('dt-header-total-pnl')).toHaveAttribute('data-sort', 'none');
        expect(rowIds()).toEqual([GROUP, '3']);

        await openGroup();
        expect(rowIds()).toEqual([GROUP, '2', '4', '5', '3']);

        // A sort cleared by its third click gives the same order back
        for (const state of ['asc', 'desc', 'none']) {
            await fireEvent.click(screen.getByTestId('dt-sort-total-pnl'));
            await waitFor(() => expect(screen.getByTestId('dt-header-total-pnl')).toHaveAttribute('data-sort', state));
        }
        await waitFor(() => expect(rowIds()).toEqual([GROUP, '2', '4', '5', '3']));
    });
});

describe('UnifiedLotsTable — the reward lots group: sorting', () => {
    it('sorts as one row on its own P&L, its lots sorted the same way under it, in both directions', async () => {
        mount();
        await openGroup();

        await fireEvent.click(screen.getByTestId('dt-sort-total-pnl'));
        await waitFor(() => expect(screen.getByTestId('dt-header-total-pnl')).toHaveAttribute('data-sort', 'asc'));
        // BUY 30 < group 70; under the group 10, 20, 40. A flat sort would read 12, 13, 1, 11.
        await waitFor(() => expect(rowIds()).toEqual(['1', GROUP, '12', '13', '11']));

        await fireEvent.click(screen.getByTestId('dt-sort-total-pnl'));
        await waitFor(() => expect(screen.getByTestId('dt-header-total-pnl')).toHaveAttribute('data-sort', 'desc'));
        await waitFor(() => expect(rowIds()).toEqual([GROUP, '11', '13', '12', '1']));
    });

    it('sorted and closed, the group sorts on its own value and its lots stay hidden', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('dt-sort-total-pnl'));
        await fireEvent.click(screen.getByTestId('dt-sort-total-pnl'));
        await waitFor(() => expect(screen.getByTestId('dt-header-total-pnl')).toHaveAttribute('data-sort', 'desc'));
        await waitFor(() => expect(rowIds()).toEqual([GROUP, '1']));
    });
});

describe('UnifiedLotsTable — the reward lots group: selection', () => {
    it('its checkbox selects all its lots, and unchecking it drops them', async () => {
        const {onSelectionChange} = mount();
        await fireEvent.click(checkbox(GROUP));
        await waitFor(() => expect(lastSelection(onSelectionChange)).toEqual([11, 12, 13]));
        expect(checkbox(GROUP)).toHaveAttribute('data-state', 'checked');
        expect(checkbox('1')).toHaveAttribute('data-state', 'unchecked');

        // Opened, its lots show selected
        await openGroup();
        await waitFor(() => expect(['11', '12', '13'].map((id) => checkbox(id).getAttribute('data-state'))).toEqual(['checked', 'checked', 'checked']));

        await fireEvent.click(checkbox(GROUP));
        await waitFor(() => expect(lastSelection(onSelectionChange)).toEqual([]));
        await waitFor(() => expect(['11', '12', '13'].map((id) => checkbox(id).getAttribute('data-state'))).toEqual(['unchecked', 'unchecked', 'unchecked']));
        expect(checkbox(GROUP)).toHaveAttribute('data-state', 'unchecked');
    });

    it('one of its lots selected draws the group in the mixed state, open and closed', async () => {
        const {onSelectionChange} = mount();
        await openGroup();
        await fireEvent.click(checkbox('12'));
        await waitFor(() => expect(lastSelection(onSelectionChange)).toEqual([12]));
        await waitFor(() => expect(checkbox(GROUP)).toHaveAttribute('data-state', 'partial'));

        // Closed, no row shows lot 12: it stays selected, and the group still says so
        await fireEvent.click(head());
        await waitFor(() => expect(head()).toHaveAttribute('data-state', 'closed'));
        expect(checkbox(GROUP)).toHaveAttribute('data-state', 'partial');
        expect(lastSelection(onSelectionChange)).toEqual([12]);

        // A lot outside the group selected meanwhile does not drop it
        await fireEvent.click(checkbox('1'));
        await waitFor(() => expect(lastSelection(onSelectionChange)).toEqual([1, 12]));
        expect(checkbox(GROUP)).toHaveAttribute('data-state', 'partial');

        await openGroup();
        await waitFor(() => expect(checkbox('12')).toHaveAttribute('data-state', 'checked'));
        expect(checkbox('11')).toHaveAttribute('data-state', 'unchecked');
    });

    it('all three selected, then one unchecked: from checked to mixed', async () => {
        const {onSelectionChange} = mount();
        await fireEvent.click(checkbox(GROUP));
        await waitFor(() => expect(lastSelection(onSelectionChange)).toEqual([11, 12, 13]));
        await openGroup();
        await waitFor(() => expect(checkbox('13')).toHaveAttribute('data-state', 'checked'));

        await fireEvent.click(checkbox('13'));
        await waitFor(() => expect(lastSelection(onSelectionChange)).toEqual([11, 12]));
        await waitFor(() => expect(checkbox(GROUP)).toHaveAttribute('data-state', 'partial'));
    });

    it('controlled by the parent (selectedLotIds, as the panel passes it): part of the group is mixed, all of it is checked', async () => {
        const view = mount(BOOK, {selectedLotIds: [12]});
        await waitFor(() => expect(checkbox(GROUP)).toHaveAttribute('data-state', 'partial'));
        expect(checkbox('1')).toHaveAttribute('data-state', 'unchecked');

        await view.rerender({lots: BOOK.map(lot), currency: CURRENCY, brokers: [], onSelectionChange: view.onSelectionChange, selectedLotIds: [11, 12, 13]});
        await waitFor(() => expect(checkbox(GROUP)).toHaveAttribute('data-state', 'checked'));
        expect(checkbox('1')).toHaveAttribute('data-state', 'unchecked');
    });

    it('controlled round trip, as the panel wires it (its selection never undefined): clicks reach the parent and come back', async () => {
        const lots = BOOK.map(lot);
        let selected: number[] = [];
        let view: ReturnType<typeof render>;
        const onSelectionChange = vi.fn((ids: number[]) => {
            selected = [...ids];
            void view.rerender({lots, currency: CURRENCY, brokers: [], onSelectionChange, selectedLotIds: selected});
        });
        view = render(UnifiedLotsTable, {lots, currency: CURRENCY, brokers: [], onSelectionChange, selectedLotIds: selected});

        await openGroup();
        await fireEvent.click(checkbox('11'));
        await waitFor(() => expect(selected).toEqual([11]));
        await waitFor(() => expect(checkbox(GROUP)).toHaveAttribute('data-state', 'partial'));
        expect(checkbox('11')).toHaveAttribute('data-state', 'checked');

        // The mixed head checked takes the rest of its lots
        await fireEvent.click(checkbox(GROUP));
        await waitFor(() => expect([...selected].sort((a, b) => a - b)).toEqual([11, 12, 13]));
        await waitFor(() => expect(checkbox(GROUP)).toHaveAttribute('data-state', 'checked'));
        expect(['11', '12', '13'].map((id) => checkbox(id).getAttribute('data-state'))).toEqual(['checked', 'checked', 'checked']);
        expect(checkbox('1')).toHaveAttribute('data-state', 'unchecked');
    });
});

describe('UnifiedLotsTable — the reward lots group: totals', () => {
    it('control: the formatter tells a total from its double (no masking in this runtime)', () => {
        expect(signed(100)).not.toBe(signed(170));
        expect(signed(70)).not.toBe(signed(140));
    });

    it('totals each lot once, the group closed or open', async () => {
        mount();
        // Closed: the BUY lot and the group's three lots, 30 + 70
        expect(footerText('total-pnl')).toBe(signed(100));
        await openGroup();
        // Open: the head and its lots are all rows, but each lot counts once
        expect(footerText('total-pnl')).toBe(signed(100));
    });

    it('with the group selected, totals its lots once, closed and open', async () => {
        const {onSelectionChange} = mount();
        await fireEvent.click(checkbox(GROUP));
        await waitFor(() => expect(lastSelection(onSelectionChange)).toEqual([11, 12, 13]));
        await waitFor(() => expect(footerText('total-pnl')).toBe(signed(70)));

        await openGroup();
        await waitFor(() => expect(['11', '12', '13'].map((id) => checkbox(id).getAttribute('data-state'))).toEqual(['checked', 'checked', 'checked']));
        // The head and its three lots are selected rows: 70, not 140
        expect(footerText('total-pnl')).toBe(signed(70));
    });

    it('a closed group totals through its lots, not its own row: the opening price column, which the group row leaves empty', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('column-visibility-toggle'));
        await fireEvent.click(await screen.findByTestId('column-visibility-item-opening-price'));
        await waitFor(() => expect(screen.getByTestId('dt-footer-opening-price')).toBeInTheDocument());
        // Closed: the group's own unit price is empty, so a total over the head would be «—». Over the lots it is the mean
        // of 10, 20, 20, 10 (every lot is worth 100 now).
        expect(head()).toHaveAttribute('data-state', 'closed');
        expect(footerText('opening-price')).toBe(formatCurrencyAmountPlain(15, CURRENCY, {sensitivity: 'public'}));
    });
});

describe('UnifiedLotsTable — the reward lots group: navigation', () => {
    it('navigating to a lot inside a closed group opens the group first', async () => {
        const {component} = mount();
        expect(rowIds()).toEqual(['1', GROUP]);
        (component as unknown as {navigateToRowId: (id: string) => void}).navigateToRowId('12');
        await waitFor(() => expect(head()).toHaveAttribute('data-state', 'open'));
        await waitFor(() => expect(rowOf('12')).toHaveAttribute('data-highlighted', 'true'));
    });
});

describe('UnifiedLotsTable — the reward tag (86, A9)', () => {
    const tags = () => screen.queryAllByTestId('reward-lot-tag').map((el) => el.closest('tr')?.getAttribute('data-row-id'));

    it('every reward lot of an open group wears it; the group row and the BUY lot do not', async () => {
        mount();
        expect(tags()).toEqual([]);
        await openGroup();
        expect(tags()).toEqual(['11', '12', '13']);
    });

    it('a lone reward lot wears it too', () => {
        mount([BUY_1, REWARD_11]);
        expect(tags()).toEqual(['11']);
    });

    it('takes the rewards colour as a measured pair, and names the type as the app does', async () => {
        mount([REWARD_11]);
        const tag = screen.getByTestId('reward-lot-tag');
        expect(tag).toHaveClass('bg-lf-cat-index-soft', 'text-lf-cat-index-on-soft');
        expect(tag.textContent).toBe(get(_)('transactions.types.REWARD'));
    });

    it('a lot without a reward keeps the date cell it had', () => {
        mount([BUY_1]);
        expect(tags()).toEqual([]);
        expect(screen.queryByTestId('reward-lot-tag')).toBeNull();
    });
});

describe('UnifiedLotsTable — the number of lots (86, A10)', () => {
    it('stands beside the title, not after the line under it', () => {
        mount();
        const count = screen.getByTestId('unified-lots-count');
        expect(count.textContent?.trim()).toBe('4');
        expect(count.parentElement?.firstElementChild).toBe(screen.getByTestId('unified-lots-title'));
        expect(count.parentElement?.children).toHaveLength(2);
    });
});
