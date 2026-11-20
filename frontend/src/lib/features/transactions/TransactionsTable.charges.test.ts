// @vitest-environment jsdom
/**
 * TransactionsTable — a parent's linked charges fold under it (project 66, lot F5).
 * Component test (Vitest + jsdom). Contract: `66-F5-contract.md` §1 and §3.
 *
 * A BUY with a FEE and a TAX linked to it (`parent_transaction_id`), plus an unrelated DEPOSIT. The list order puts the
 * FEE before its parent and the TAX after the DEPOSIT, so «right after the parent» is something the table must do.
 *
 * What is covered, each absence behind a presence barrier (the BUY and the DEPOSIT rows are rendered):
 *   - folded by default: the charge rows are not in the table, the BUY carries the badge `tx-charges-badge-<id>` with
 *     `data-expanded="false"`;
 *   - a click on the badge shows the two charges right after the BUY and flips `data-expanded`; a second click hides them;
 *   - the BUY's 🔗 (`[data-tx-charges-toggle]`) opens and closes them too, and does not call `onLinkedPairClick`;
 *   - a charge row carries the arrow `tx-charge-arrow-<id>`; its 🔗 (`[data-tx-link]`) calls `onLinkedPairClick` with
 *     the charge;
 *   - a filter that is not on the type keeps the fold (decision R);
 *   - a type filter = FEE shows the FEE as a row of its own, with its arrow (decision S);
 *   - a sort makes the table flat: every row is there and the BUY has no toggle 🔗 (decision T);
 *   - a double-click on the badge or on the BUY's 🔗 does not open the view (a cell of the same row still does);
 *   - one charge and two charges read with different words (the catalogue's plural, not a fixed «charges»);
 *   - mounted on page 2 with a non-type filter, the table does not ask for page 1; a filter change afterwards does.
 *
 * Selection: rows by `tbody tr[data-row-id="tx-<id>"]`, the rest by data-testid / data-* attributes. No translated text.
 */
import {afterAll, afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') {
                    return vi.fn(async () => ({items: [{code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []}]}));
                }
                if (property === 'list_assets_api_v1_assets_query_get') return vi.fn(async () => []);
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {get} from 'svelte/store';
import {addMessages} from 'svelte-i18n';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {_ as t, locale} from '$lib/i18n';
import {ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
import type {FilterValue} from '$lib/components/table/types';
import TransactionsTable from './TransactionsTable.svelte';
import type {TXReadItem} from './types';

const BROKER = {id: 61, name: 'F5 broker', portal_url: 'https://f5.example.com', icon_url: null, default_import_plugin: null};

const base = {asset_id: null, asset_event_id: null, tags: [], description: null, related_transaction_id: null, parent_transaction_id: null};

const BUY: TXReadItem = {...base, id: 9101, broker_id: BROKER.id, asset_id: 77, type: 'BUY', date: '2026-05-10', quantity: '10', cash: {code: 'EUR', amount: '-100.00'}};
const FEE: TXReadItem = {...base, id: 9102, broker_id: BROKER.id, asset_id: 77, type: 'FEE', date: '2026-05-10', quantity: '0', cash: {code: 'EUR', amount: '-5.00'}, parent_transaction_id: BUY.id};
const TAX: TXReadItem = {...base, id: 9103, broker_id: BROKER.id, asset_id: 77, type: 'TAX', date: '2026-05-10', quantity: '0', cash: {code: 'EUR', amount: '-2.00'}, parent_transaction_id: BUY.id};
const DEPOSIT: TXReadItem = {...base, id: 9104, broker_id: BROKER.id, type: 'DEPOSIT', date: '2026-05-01', quantity: '0', cash: {code: 'EUR', amount: '1000.00'}};

/** List order: a charge before its parent, the other after an unrelated row. */
const LIST = [FEE, BUY, DEPOSIT, TAX];

let mountSeq = 0;

type MountOpts = {
    rows?: TXReadItem[];
    onLinkedPairClick?: (row: TXReadItem) => void;
    onViewRow?: (row: TXReadItem) => void;
    onPageChange?: (page: number) => void;
    onFiltersChange?: (filters: Record<string, FilterValue>) => void;
    initialFilters?: Record<string, FilterValue>;
    currentPage?: number;
    pageSize?: number;
};

function mount({rows = LIST, ...opts}: MountOpts = {}): void {
    mountSeq += 1;
    render(TransactionsTable, {
        mainRows: rows.map((r) => structuredClone(r)),
        partnerRows: [],
        brokers: [{...BROKER}],
        eventTooltipMap: new Map(),
        // Each mount its own preferences key: nothing a previous test left in localStorage reaches this one.
        storageKeyOverride: `tx-charges-test-${mountSeq}`,
        ...opts,
    });
}

function trOf(id: number): HTMLElement | null {
    return document.querySelector<HTMLElement>(`tbody tr[data-row-id="tx-${id}"]`);
}

/** The ids of the rendered rows, in table order. */
function renderedIds(): string[] {
    return Array.from(document.querySelectorAll<HTMLElement>('tbody tr[data-row-id]')).map((tr) => tr.getAttribute('data-row-id') ?? '');
}

/** Presence barrier: the rows the table must draw in every mode are drawn. */
async function rowsReady(...txIds: number[]): Promise<void> {
    for (const id of txIds) await waitFor(() => expect(trOf(id), `row tx-${id} is rendered`).not.toBeNull());
}

async function badge(): Promise<HTMLElement> {
    return screen.findByTestId(`tx-charges-badge-${BUY.id}`);
}

beforeAll(async () => {
    await setupI18n();
    await ensureCurrenciesLoaded('en');
});

afterEach(() => {
    try {
        localStorage.clear();
    } catch {
        /* no storage: nothing to clear */
    }
});

describe('TransactionsTable — charges folded by default', () => {
    it('hides the charge rows and gives the BUY a closed badge', async () => {
        mount();
        await rowsReady(BUY.id, DEPOSIT.id);

        expect(trOf(FEE.id), 'FEE folded under the BUY').toBeNull();
        expect(trOf(TAX.id), 'TAX folded under the BUY').toBeNull();
        const b = await badge();
        expect(b).toHaveAttribute('data-expanded', 'false');
        // The badge sits in the BUY row, not anywhere else.
        expect(trOf(BUY.id)!.contains(b)).toBe(true);
    });

    it('an unrelated row has no badge', async () => {
        mount();
        await rowsReady(BUY.id, DEPOSIT.id);
        await badge();

        expect(screen.queryByTestId(`tx-charges-badge-${DEPOSIT.id}`)).toBeNull();
    });
});

describe('TransactionsTable — the badge opens and closes the charges', () => {
    it('a click shows both charges right after the BUY; a second click hides them', async () => {
        mount();
        await rowsReady(BUY.id, DEPOSIT.id);
        const b = await badge();

        await fireEvent.click(b);

        await waitFor(() => expect(trOf(FEE.id)).not.toBeNull());
        await waitFor(() => expect(trOf(TAX.id)).not.toBeNull());
        expect(await badge()).toHaveAttribute('data-expanded', 'true');
        const order = renderedIds();
        const at = order.indexOf(`tx-${BUY.id}`);
        expect(order.slice(at, at + 3), 'the charges come right after their parent, in list order').toEqual([`tx-${BUY.id}`, `tx-${FEE.id}`, `tx-${TAX.id}`]);

        await fireEvent.click(await badge());

        await waitFor(() => expect(trOf(FEE.id)).toBeNull());
        expect(trOf(TAX.id)).toBeNull();
        expect(trOf(BUY.id)).not.toBeNull();
        expect(await badge()).toHaveAttribute('data-expanded', 'false');
    });

    it('a charge row carries the arrow, the BUY does not', async () => {
        mount();
        await rowsReady(BUY.id, DEPOSIT.id);
        await fireEvent.click(await badge());
        await waitFor(() => expect(trOf(FEE.id)).not.toBeNull());

        expect(trOf(FEE.id)!.querySelector(`[data-testid="tx-charge-arrow-${FEE.id}"]`)).not.toBeNull();
        expect(trOf(TAX.id)!.querySelector(`[data-testid="tx-charge-arrow-${TAX.id}"]`)).not.toBeNull();
        expect(trOf(BUY.id)!.querySelector('[data-testid^="tx-charge-arrow-"]')).toBeNull();
    });
});

describe('TransactionsTable — the 🔗 of the BUY and of a charge', () => {
    it('the BUY 🔗 opens and closes the charges, and is not a link to another row', async () => {
        const onLinkedPairClick = vi.fn();
        mount({onLinkedPairClick});
        await rowsReady(BUY.id, DEPOSIT.id);
        const toggle = await waitFor(() => {
            const el = trOf(BUY.id)!.querySelector<HTMLElement>('[data-tx-charges-toggle]');
            expect(el, 'the BUY carries the charges toggle 🔗').not.toBeNull();
            return el!;
        });

        await fireEvent.click(toggle);
        await waitFor(() => expect(trOf(FEE.id)).not.toBeNull());
        expect(trOf(TAX.id)).not.toBeNull();
        expect(await badge()).toHaveAttribute('data-expanded', 'true');

        await fireEvent.click(trOf(BUY.id)!.querySelector<HTMLElement>('[data-tx-charges-toggle]')!);
        await waitFor(() => expect(trOf(FEE.id)).toBeNull());
        expect(await badge()).toHaveAttribute('data-expanded', 'false');

        expect(onLinkedPairClick).not.toHaveBeenCalled();
    });

    it('the 🔗 of a charge calls onLinkedPairClick with that charge', async () => {
        const onLinkedPairClick = vi.fn();
        mount({onLinkedPairClick});
        await rowsReady(BUY.id, DEPOSIT.id);
        await fireEvent.click(await badge());
        await waitFor(() => expect(trOf(FEE.id)).not.toBeNull());
        const link = trOf(FEE.id)!.querySelector<HTMLElement>(`[data-tx-link="${FEE.id}"]`);
        expect(link, 'the FEE carries its 🔗').not.toBeNull();

        await fireEvent.click(link!);

        expect(onLinkedPairClick).toHaveBeenCalledTimes(1);
        expect(onLinkedPairClick.mock.calls[0][0]).toMatchObject({id: FEE.id, parent_transaction_id: BUY.id});
    });
});

describe('TransactionsTable — filters and sort', () => {
    it('a filter that is not on the type keeps the charges folded', async () => {
        // An id range that holds all four rows: the filter is active, the fold stays (decision R).
        mount({initialFilters: {id: {type: 'number', min: BUY.id, max: DEPOSIT.id}}});
        await rowsReady(BUY.id, DEPOSIT.id);

        const b = await badge();
        expect(b).toHaveAttribute('data-expanded', 'false');
        expect(trOf(FEE.id)).toBeNull();
        expect(trOf(TAX.id)).toBeNull();

        await fireEvent.click(b);
        await waitFor(() => expect(trOf(FEE.id)).not.toBeNull());
        expect(trOf(TAX.id)).not.toBeNull();
    });

    it('a type filter = FEE shows the FEE as a row of its own, with its arrow', async () => {
        mount({initialFilters: {types: {type: 'enum', selected: ['FEE']}}});
        await rowsReady(FEE.id);

        expect(trOf(FEE.id)!.querySelector(`[data-testid="tx-charge-arrow-${FEE.id}"]`)).not.toBeNull();
        expect(trOf(BUY.id)).toBeNull();
        expect(trOf(TAX.id)).toBeNull();
        expect(trOf(DEPOSIT.id)).toBeNull();
    });

    it('a sort makes the table flat: every row is there, the BUY has no toggle 🔗', async () => {
        mount();
        await rowsReady(BUY.id, DEPOSIT.id);
        // Folded before the sort: the flat rows below are the sort's doing.
        await badge();
        expect(trOf(FEE.id)).toBeNull();

        await fireEvent.click(await screen.findByTestId('dt-sort-cash'));
        await waitFor(() => expect(screen.getByTestId('dt-header-cash')).not.toHaveAttribute('data-sort', 'none'));

        await rowsReady(BUY.id, FEE.id, TAX.id, DEPOSIT.id);
        expect(trOf(FEE.id)!.querySelector(`[data-testid="tx-charge-arrow-${FEE.id}"]`)).not.toBeNull();
        expect(trOf(BUY.id)!.querySelector('[data-tx-charges-toggle]')).toBeNull();
        // The badge stays, as a label.
        expect(trOf(BUY.id)!.querySelector(`[data-testid="tx-charges-badge-${BUY.id}"]`)).not.toBeNull();
    });
});

describe('TransactionsTable — a double-click on the charges toggles is not a double-click on the row', () => {
    it('the badge and the BUY 🔗 swallow the double-click; a cell of the same row still opens the view', async () => {
        const onViewRow = vi.fn();
        mount({onViewRow});
        await rowsReady(BUY.id, DEPOSIT.id);
        const toggle = await waitFor(() => {
            const el = trOf(BUY.id)!.querySelector<HTMLElement>('[data-tx-charges-toggle]');
            expect(el, 'the BUY carries the charges toggle 🔗').not.toBeNull();
            return el!;
        });

        await fireEvent.dblClick(await badge());
        await fireEvent.dblClick(toggle);
        expect(onViewRow, 'a double-click on the badge or the 🔗 does not open the view').not.toHaveBeenCalled();

        // Positive control in the same mount: the row's own double-click does reach onViewRow, so the silence above is
        // the toggles' doing and not a missing wiring.
        const idCell = trOf(BUY.id)!.querySelector<HTMLElement>(`[data-testid="tx-id-${BUY.id}"]`);
        expect(idCell, 'the BUY shows its id cell').not.toBeNull();
        await fireEvent.dblClick(idCell!);
        expect(onViewRow).toHaveBeenCalledTimes(1);
        expect(onViewRow.mock.calls[0][0]).toMatchObject({id: BUY.id});
    });
});

describe('TransactionsTable — the badge counts in the catalogue plural', () => {
    it('one charge and two charges do not read with the same word', async () => {
        // A second parent with a single FEE, beside the BUY with two charges.
        const BUY1: TXReadItem = {...BUY, id: 9111};
        const FEE1: TXReadItem = {...FEE, id: 9112, parent_transaction_id: BUY1.id};
        mount({rows: [...LIST, BUY1, FEE1]});
        await rowsReady(BUY.id, BUY1.id, DEPOSIT.id);

        const two = (await screen.findByTestId(`tx-charges-badge-${BUY.id}`)).textContent?.trim() ?? '';
        const one = (await screen.findByTestId(`tx-charges-badge-${BUY1.id}`)).textContent?.trim() ?? '';
        // The ICU `#` renders the count: the catalogue value was used, not its key.
        expect(two).toMatch(/\b2\b/);
        expect(one).toMatch(/\b1\b/);
        const lastWord = (text: string): string => text.split(/\s+/).at(-1) ?? '';
        expect(lastWord(one), `«${one}» and «${two}» end with the same word: no singular form`).not.toBe(lastWord(two));
    });
});

describe('TransactionsTable — the page resets on a filter change, not on mount', () => {
    /** Enough unrelated rows for three pages of two while the charges fold (BUY, DEPOSIT and four more). */
    const MORE: TXReadItem[] = [9105, 9106, 9107, 9108].map((id) => ({...DEPOSIT, id}));

    it('mounted on page 2 with a non-type filter, it stays; a filter change afterwards goes back to page 1', async () => {
        const onPageChange = vi.fn();
        const onFiltersChange = vi.fn();
        mount({
            rows: [...LIST, ...MORE],
            initialFilters: {id: {type: 'number', min: BUY.id, max: 9110}},
            currentPage: 2,
            pageSize: 2,
            onPageChange,
            onFiltersChange,
        });

        // Barriers: the table is on page 2 of its own paginator, and the filter record it opened with has come back.
        await waitFor(() => expect(document.querySelector('tbody tr[data-row-id]')).not.toBeNull());
        await waitFor(() => expect(screen.getByTestId('pagination-prev')).toBeEnabled());
        await waitFor(() =>
            expect(
                onFiltersChange.mock.calls.some(([record]) => record?.id != null),
                'the id filter came back',
            ).toBe(true),
        );
        // In jsdom the DataTable emits the opening record (with the id filter) more than once: none of those repeats
        // may read as a change. (jsdom never emits the empty record first, so this does not reach that guard.)
        expect(onPageChange, 'the filters the table opened with are not a change').not.toHaveBeenCalled();

        // Now a real change: reset the id filter from its header popover.
        await fireEvent.click(screen.getByTestId('col-filter-trigger-id'));
        await fireEvent.click(await screen.findByTestId('column-filter-reset'));

        await waitFor(() => expect(onPageChange).toHaveBeenCalledWith(1));
    });
});

describe('TransactionsTable — the 🔗 tooltip of a charge and of a folded parent shows its text once escaped', () => {
    /**
     * Marker values with the characters an extra escape would show as entities: an apostrophe (IT «un'altra», FR
     * «d'une»), an ampersand and angle brackets. Written into the active locale for this block and put back after it,
     * so no catalogue string is asserted.
     */
    const CHARGE_OF_OTHER = "Charge d'X & <Y>";
    const CHARGES_TOGGLE = "Toggle l'Z & <W>";
    const ENTITY = /&(#39|#x27|amp|lt|gt|quot);/;

    let current = 'en';
    let original: Record<string, string> = {};

    beforeAll(() => {
        current = get(locale) ?? 'en';
        original = {chargeOfOther: get(t)('transactions.linkTooltip.chargeOfOther'), chargesToggle: get(t)('transactions.linkTooltip.chargesToggle')};
        addMessages(current, {transactions: {linkTooltip: {chargeOfOther: CHARGE_OF_OTHER, chargesToggle: CHARGES_TOGGLE}}});
    });

    afterAll(() => {
        addMessages(current, {transactions: {linkTooltip: original}});
    });

    /**
     * Open the 🔗's tooltip from the keyboard (Enter on its trigger: shown at once, no hover delay) and return what the
     * user reads in it. A click cannot open it: the table takes the 🔗's click in the capture phase.
     */
    async function tooltipTextOf(link: HTMLElement): Promise<string> {
        const trigger = link.closest<HTMLElement>('[role="button"]');
        expect(trigger, 'the 🔗 sits inside its Tooltip trigger').not.toBeNull();
        await fireEvent.keyDown(trigger!, {key: 'Enter'});
        const tip = await screen.findByTestId('tooltip-content');
        return tip.textContent?.trim() ?? '';
    }

    it('a charge whose parent is not in the list reads chargeOfOther verbatim, never as entities', async () => {
        expect(get(t)('transactions.linkTooltip.chargeOfOther'), 'the marker is live in the active locale').toBe(CHARGE_OF_OTHER);
        const ORPHAN: TXReadItem = {...FEE, id: 9121, parent_transaction_id: 9999};
        mount({rows: [...LIST, ORPHAN]});
        await rowsReady(BUY.id, DEPOSIT.id, ORPHAN.id);

        const link = trOf(ORPHAN.id)!.querySelector<HTMLElement>(`[data-tx-link="${ORPHAN.id}"]`);
        expect(link, 'the orphan FEE carries its 🔗').not.toBeNull();
        const text = await tooltipTextOf(link!);
        expect(text, 'no entity reaches the reader').not.toMatch(ENTITY);
        expect(text).toBe(CHARGE_OF_OTHER);
    });

    it('the folded parent toggle reads chargesToggle verbatim, never as entities', async () => {
        expect(get(t)('transactions.linkTooltip.chargesToggle'), 'the marker is live in the active locale').toBe(CHARGES_TOGGLE);
        mount();
        await rowsReady(BUY.id, DEPOSIT.id);

        const toggle = await waitFor(() => {
            const el = trOf(BUY.id)!.querySelector<HTMLElement>('[data-tx-charges-toggle]');
            expect(el, 'the folded BUY carries the charges toggle 🔗').not.toBeNull();
            return el!;
        });
        const text = await tooltipTextOf(toggle);
        expect(text, 'no entity reaches the reader').not.toMatch(ENTITY);
        expect(text).toBe(CHARGES_TOGGLE);
    });
});
