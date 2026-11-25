// @vitest-environment jsdom
/**
 * TxChargesActionModal — the rich confirmation for «link the charges» (Z) and «delete a parent that has charges» (V1)
 * (project 66, lot F6). Component test (Vitest + jsdom). RED FIRST: `./TxChargesActionModal.svelte` does not exist yet.
 * Contract: `66-F6-contract.md` §2 and §5.
 *
 * The props this file pins (the implementer follows them):
 *
 *   {
 *       open: boolean;
 *       mode: 'link' | 'deleteParent';
 *       parents: TXReadItem[];
 *       charges: TXReadItem[];
 *       loading?: boolean;
 *       onConfirm?: () => void;                       // link mode
 *       onChoose?: (choice: 'keep' | 'all') => void;  // deleteParent mode
 *       onCancel: () => void;
 *   }
 *
 * data-testid: `tx-charges-modal` (the dialog), `tx-charges-modal-table` (wraps the DataTable), `tx-charges-modal-cancel`,
 * `tx-charges-modal-confirm` (link and unlink), `tx-charges-modal-keep` and `tx-charges-modal-all` (deleteParent only).
 * Mode `unlink` (66 TL-9: `parents` empty, the charges alone, a field row `parent`) has a block of its own.
 *
 * The table: a DataTable with one COLUMN per transaction, header `TX #<id>`, column ids positional (`c0`, `c1`, …, read
 * from DataTable's own `dt-header-<column id>` testids), parent first then its charges; selection and row actions off.
 * A column for the field names (Date, Type, …) may come first: the per-transaction columns are the headers that name
 * a `#<id>`.
 *
 * On text. `$lib/i18n` is replaced by a translator that renders a key with its values (`key(name=value)`), as in
 * PromoteMergeModal.test.ts: no catalogue key is needed for this file, and the only text read is a NUMBER (the
 * `#<id>` of a column, the count N of «Delete all (N)»), never a word.
 *
 * Storage. This jsdom exposes no `localStorage` (DataTable.test.ts, Y-27 block), so a spy on `Storage.prototype`
 * would never fire: the last block stubs a recording `localStorage` over a Map, and checks that no key and no value
 * written (or read) names a transaction id. Ids are in the 930000s so no width, count or index can collide with one.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

vi.mock('$lib/i18n', async (importOriginal) => {
    const shown = (key: string, options?: {values?: Record<string, unknown>}) => {
        const values = options?.values;
        if (!values) return key;
        const listed = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return `${key}(${listed.join(', ')})`;
    };
    const translator = readable(shown);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator, locale: writable('en')};
});

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    ApiError: class ApiError extends Error {},
    axiosInstance: {},
}));

import TxChargesActionModal from './TxChargesActionModal.svelte';
import type {TXReadItem} from './types';

// ─── fixtures ────────────────────────────────────────────────────────────────────────────────────────────────────

const BROKER = 41;
const base = {broker_id: BROKER, asset_id: 77, date: '2026-05-10', tags: [], description: null, related_transaction_id: null};

const BUY: TXReadItem = {...base, id: 930_101, type: 'BUY', quantity: '10', cash: {code: 'EUR', amount: '-100.00'}, parent_transaction_id: null, charges_count: 2};
const FEE: TXReadItem = {...base, id: 930_102, type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-5.00'}, parent_transaction_id: BUY.id};
const TAX: TXReadItem = {...base, id: 930_103, type: 'TAX', quantity: '0', cash: {code: 'EUR', amount: '-2.00'}, parent_transaction_id: BUY.id};

const SELL: TXReadItem = {...base, id: 930_201, type: 'SELL', quantity: '-4', cash: {code: 'EUR', amount: '60.00'}, parent_transaction_id: null, charges_count: 3};
const SELL_FEE: TXReadItem = {...base, id: 930_202, type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-1.00'}, parent_transaction_id: SELL.id};
const SELL_TAX: TXReadItem = {...base, id: 930_203, type: 'TAX', quantity: '0', cash: {code: 'EUR', amount: '-3.00'}, parent_transaction_id: SELL.id};
const SELL_FEE2: TXReadItem = {...base, id: 930_204, type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-0.50'}, parent_transaction_id: SELL.id};

const ALL_IDS = [BUY, FEE, TAX, SELL, SELL_FEE, SELL_TAX, SELL_FEE2].map((r) => r.id);

type Props = {
    open: boolean;
    mode: 'link' | 'deleteParent';
    parents: TXReadItem[];
    charges: TXReadItem[];
    loading?: boolean;
    onConfirm?: () => void;
    onChoose?: (choice: 'keep' | 'all') => void;
    onCancel: () => void;
    /** deleteParent only: the counts of the real plan (mixed selection), overriding parents + charges. */
    counts?: {keep: number; all: number};
};

const onConfirm = vi.fn<() => void>();
const onChoose = vi.fn<(choice: 'keep' | 'all') => void>();
const onCancel = vi.fn<() => void>();

function mount(over: Partial<Props> = {}) {
    const props: Props = {
        open: true,
        mode: 'link',
        // Link mode: the charges are not linked yet.
        parents: [structuredClone(BUY)],
        charges: [
            {...structuredClone(FEE), parent_transaction_id: null},
            {...structuredClone(TAX), parent_transaction_id: null},
        ],
        loading: false,
        onConfirm,
        onChoose,
        onCancel,
        ...over,
    };
    return render(TxChargesActionModal, props);
}

/** The dialog, the one element carrying `tx-charges-modal`. */
async function dialog(): Promise<HTMLElement> {
    const el = await screen.findByTestId('tx-charges-modal');
    expect(screen.queryAllByTestId('tx-charges-modal'), 'elements carrying data-testid="tx-charges-modal"').toHaveLength(1);
    return el;
}

/** The data-column headers of the modal's DataTable, in DOM order. */
async function headers(): Promise<HTMLElement[]> {
    const table = await screen.findByTestId('tx-charges-modal-table');
    await waitFor(() => expect(table.querySelectorAll('thead th[data-testid^="dt-header-"]').length, 'the table draws its headers').toBeGreaterThan(0));
    return Array.from(table.querySelectorAll<HTMLElement>('thead th[data-testid^="dt-header-"]'));
}

/** The transaction id a header names (`#<id>`), or null for a header that names none (the field-name column). */
function idOf(th: HTMLElement): number | null {
    const m = /#(\d+)\b/.exec(th.textContent ?? '');
    return m ? Number(m[1]) : null;
}

/** The per-transaction columns: their ids in DOM order, and their DataTable column ids. */
async function txColumns(): Promise<{ids: number[]; columnIds: string[]}> {
    const ths = (await headers()).filter((th) => idOf(th) !== null);
    return {
        ids: ths.map((th) => idOf(th) as number),
        columnIds: ths.map((th) => (th.getAttribute('data-testid') ?? '').slice('dt-header-'.length)),
    };
}

/** Whether `text` holds `n` as a whole number (not a digit inside an id). */
const holdsNumber = (text: string | null, n: number) => new RegExp(`(^|\\D)${n}(\\D|$)`).test(text ?? '');

beforeEach(() => {
    onConfirm.mockReset();
    onChoose.mockReset();
    onCancel.mockReset();
});

// ─── the table ───────────────────────────────────────────────────────────────────────────────────────────────────

describe('TxChargesActionModal — one column per transaction', () => {
    it('link mode: the parent first, then the charges in order, each header naming #<id>', async () => {
        mount();
        await dialog();
        const {ids} = await txColumns();
        expect(ids).toEqual([BUY.id, FEE.id, TAX.id]);
    });

    it('the per-transaction column ids are positional (c0, c1, …), never a transaction id', async () => {
        mount();
        await dialog();
        const {columnIds} = await txColumns();
        expect(columnIds).toEqual(['c0', 'c1', 'c2']);
        for (const id of ALL_IDS) for (const col of columnIds) expect(col).not.toContain(String(id));
    });

    it('selection and row actions are off', async () => {
        mount();
        await dialog();
        const table = screen.getByTestId('tx-charges-modal-table');
        // presence barrier: the transaction columns are drawn
        expect((await txColumns()).ids).toHaveLength(3);
        expect(within(table).queryByTestId('dt-select-header')).toBeNull();
        expect(within(table).queryByTestId('dt-select-all')).toBeNull();
        expect(within(table).queryByTestId('dt-actions-header')).toBeNull();
    });

    it('deleteParent with one parent: the parent and all its charges', async () => {
        mount({mode: 'deleteParent', parents: [structuredClone(BUY)], charges: [structuredClone(FEE), structuredClone(TAX)]});
        await dialog();
        const {ids} = await txColumns();
        expect(ids[0], 'the parent comes first').toBe(BUY.id);
        expect([...ids].sort((a, b) => a - b)).toEqual([BUY.id, FEE.id, TAX.id].sort((a, b) => a - b));
    });

    it('deleteParent with several parents: one table, every parent and every charge as a column', async () => {
        mount({mode: 'deleteParent', parents: [structuredClone(BUY), structuredClone(SELL)], charges: [FEE, TAX, SELL_FEE, SELL_TAX, SELL_FEE2].map((r) => structuredClone(r))});
        await dialog();
        expect(screen.queryAllByTestId('tx-charges-modal-table'), 'one table for all the parents').toHaveLength(1);
        const {ids, columnIds} = await txColumns();
        expect([...ids].sort((a, b) => a - b)).toEqual([...ALL_IDS].sort((a, b) => a - b));
        expect(columnIds).toEqual(ALL_IDS.map((_, i) => `c${i}`));
    });
});

// ─── link mode ───────────────────────────────────────────────────────────────────────────────────────────────────

describe('TxChargesActionModal — link mode (Z)', () => {
    it('has cancel and confirm, and no keep / all', async () => {
        mount();
        const dlg = await dialog();
        // presence barrier: the footer of this mode is there
        expect(within(dlg).getByTestId('tx-charges-modal-cancel')).toBeVisible();
        expect(within(dlg).getByTestId('tx-charges-modal-confirm')).toBeVisible();
        expect(within(dlg).queryByTestId('tx-charges-modal-keep')).toBeNull();
        expect(within(dlg).queryByTestId('tx-charges-modal-all')).toBeNull();
    });

    it('confirm calls onConfirm once, and neither onChoose nor onCancel', async () => {
        mount();
        const dlg = await dialog();
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-confirm'));
        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onChoose).not.toHaveBeenCalled();
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('cancel calls onCancel, not onConfirm', async () => {
        mount();
        const dlg = await dialog();
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-cancel'));
        expect(onCancel).toHaveBeenCalledTimes(1);
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('while loading, confirm is disabled and a click does not confirm', async () => {
        mount({loading: true});
        const dlg = await dialog();
        const confirm = within(dlg).getByTestId('tx-charges-modal-confirm');
        expect(confirm).toBeDisabled();
        await fireEvent.click(confirm);
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('not loading, confirm is enabled', async () => {
        mount({loading: false});
        const dlg = await dialog();
        expect(within(dlg).getByTestId('tx-charges-modal-confirm')).toBeEnabled();
    });
});

// ─── deleteParent mode ───────────────────────────────────────────────────────────────────────────────────────────

describe('TxChargesActionModal — deleteParent mode (V1)', () => {
    function mountDelete(over: Partial<Props> = {}) {
        return mount({mode: 'deleteParent', parents: [structuredClone(BUY)], charges: [structuredClone(FEE), structuredClone(TAX)], ...over});
    }

    it('has cancel, keep and all, and no confirm', async () => {
        mountDelete();
        const dlg = await dialog();
        expect(within(dlg).getByTestId('tx-charges-modal-cancel')).toBeVisible();
        expect(within(dlg).getByTestId('tx-charges-modal-keep')).toBeVisible();
        expect(within(dlg).getByTestId('tx-charges-modal-all')).toBeVisible();
        expect(within(dlg).queryByTestId('tx-charges-modal-confirm')).toBeNull();
    });

    it('«Delete all (N)»: N = parents + charges (1 + 2 = 3)', async () => {
        mountDelete();
        const dlg = await dialog();
        const all = within(dlg).getByTestId('tx-charges-modal-all');
        expect(holdsNumber(all.textContent, 3), `«all» names the count 3, got: ${all.textContent}`).toBe(true);
    });

    it('«Delete all (N)» with several parents: N = 2 parents + 5 charges = 7', async () => {
        mountDelete({parents: [structuredClone(BUY), structuredClone(SELL)], charges: [FEE, TAX, SELL_FEE, SELL_TAX, SELL_FEE2].map((r) => structuredClone(r))});
        const dlg = await dialog();
        const all = within(dlg).getByTestId('tx-charges-modal-all');
        expect(holdsNumber(all.textContent, 7), `«all» names the count 7, got: ${all.textContent}`).toBe(true);
    });

    it("keep calls onChoose('keep'), once, and nothing else", async () => {
        mountDelete();
        const dlg = await dialog();
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-keep'));
        expect(onChoose).toHaveBeenCalledTimes(1);
        expect(onChoose).toHaveBeenCalledWith('keep');
        expect(onCancel).not.toHaveBeenCalled();
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it("all calls onChoose('all'), once, and nothing else", async () => {
        mountDelete();
        const dlg = await dialog();
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-all'));
        expect(onChoose).toHaveBeenCalledTimes(1);
        expect(onChoose).toHaveBeenCalledWith('all');
        expect(onCancel).not.toHaveBeenCalled();
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('cancel calls onCancel, not onChoose', async () => {
        mountDelete();
        const dlg = await dialog();
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-cancel'));
        expect(onCancel).toHaveBeenCalledTimes(1);
        expect(onChoose).not.toHaveBeenCalled();
    });
});

// ─── deleteParent with a mixed selection: the plan's counts ──────────────────────────────────────────────────────

/*
 * The panel alone sees only the plan's parents and ALL their charges. With a mixed selection that is not what the
 * buttons do: selection = BUY + its FEE (TAX not selected) + an unrelated row → «keep» leaves 1 charge (TAX), «all»
 * deletes 4 rows (BUY, FEE, the unrelated row, TAX). The caller passes `counts: {keep, all}`; the «Before» table
 * still shows the parent and all its charges.
 */
describe('TxChargesActionModal — deleteParent, counts of a mixed selection', () => {
    function mountMixed(over: Partial<Props> = {}) {
        return mount({mode: 'deleteParent', parents: [structuredClone(BUY)], charges: [structuredClone(FEE), structuredClone(TAX)], ...over});
    }

    it('counts {keep: 1, all: 4}: «all» names 4, the keep after-line 1, the all after-line 4', async () => {
        mountMixed({counts: {keep: 1, all: 4}});
        const dlg = await dialog();
        const all = within(dlg).getByTestId('tx-charges-modal-all');
        expect(holdsNumber(all.textContent, 4), `«all» names the plan's count 4, got: ${all.textContent}`).toBe(true);
        expect(holdsNumber(all.textContent, 3), `«all» does not name parents + charges (3), got: ${all.textContent}`).toBe(false);

        const keepAfter = within(dlg).getByTestId('tx-charges-modal-keep-after');
        expect(holdsNumber(keepAfter.textContent, 1), `the keep after-line names 1 charge left, got: ${keepAfter.textContent}`).toBe(true);
        expect(holdsNumber(keepAfter.textContent, 2), `the keep after-line does not name all the charges (2), got: ${keepAfter.textContent}`).toBe(false);

        const allAfter = within(dlg).getByTestId('tx-charges-modal-all-after');
        expect(holdsNumber(allAfter.textContent, 4), `the all after-line names 4 rows, got: ${allAfter.textContent}`).toBe(true);
        expect(holdsNumber(allAfter.textContent, 3), `the all after-line does not name 3, got: ${allAfter.textContent}`).toBe(false);
    });

    it('without counts: the keep after-line names the charges (2), the all after-line parents + charges (3)', async () => {
        mountMixed();
        const dlg = await dialog();
        const keepAfter = within(dlg).getByTestId('tx-charges-modal-keep-after');
        expect(holdsNumber(keepAfter.textContent, 2), `the keep after-line names 2, got: ${keepAfter.textContent}`).toBe(true);
        const allAfter = within(dlg).getByTestId('tx-charges-modal-all-after');
        expect(holdsNumber(allAfter.textContent, 3), `the all after-line names 3, got: ${allAfter.textContent}`).toBe(true);
    });

    it('counts given: the table still has one column per parent and per charge (3)', async () => {
        mountMixed({counts: {keep: 1, all: 4}});
        await dialog();
        const {ids} = await txColumns();
        expect(ids[0], 'the parent comes first').toBe(BUY.id);
        expect([...ids].sort((a, b) => a - b)).toEqual([BUY.id, FEE.id, TAX.id].sort((a, b) => a - b));
    });
});

// ─── 66 F7-c2: new charges (id 0) inside the Bulk ───────────────────────────────────────────────────────────────

/**
 * In the Bulk a parent's charges may be new (id 0, not saved yet). The Bulk hands each with `parent_transaction_id` = its
 * owner's id (contract 66-F7 §18.1), so the panel places it under its parent. Two new charges both have id 0: the panel
 * groups by object, never by id, or the second one vanishes. A column of a transaction not saved yet is headed by the
 * catalogue's `transactions.bulk.stateNew` (here, under the key-rendering translator, the key itself), never `TX #0`.
 */
describe('TxChargesActionModal — deleteParent with new charges (66 F7-c2)', () => {
    const NEW_FEE: TXReadItem = {...base, id: 0, type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-5.00'}, parent_transaction_id: BUY.id};
    const NEW_TAX: TXReadItem = {...base, id: 0, type: 'TAX', quantity: '0', cash: {code: 'EUR', amount: '-3.00'}, parent_transaction_id: SELL.id};

    /** The headers of the per-transaction columns (every header but the field-name column), in DOM order. */
    async function columnHeaders(): Promise<HTMLElement[]> {
        return (await headers()).filter((th) => th.getAttribute('data-testid') !== 'dt-header-field');
    }

    /** The text of a field's cell in a transaction column. */
    function cellText(field: string, columnId: string): string {
        const table = screen.getByTestId('tx-charges-modal-table');
        return (table.querySelector(`tbody tr[data-row-id="${field}"] td[data-column-id="${columnId}"]`)?.textContent ?? '').trim();
    }

    it('two parents, each with one new charge: four columns, each new charge right after its own parent', async () => {
        mount({mode: 'deleteParent', parents: [structuredClone(BUY), structuredClone(SELL)], charges: [structuredClone(NEW_FEE), structuredClone(NEW_TAX)]});
        await dialog();
        const ths = await columnHeaders();
        expect(ths, 'two parents + two new charges: no charge is lost to a shared id 0').toHaveLength(4);
        const ids = ths.map((th) => th.getAttribute('data-testid')!.slice('dt-header-'.length));
        expect(idOf(ths[0]), 'the BUY first').toBe(BUY.id);
        expect(cellText('type', ids[1]), 'then the BUY’s new FEE').toBe('transactions.types.FEE');
        expect(idOf(ths[2]), 'then the SELL').toBe(SELL.id);
        expect(cellText('type', ids[3]), 'then the SELL’s new TAX').toBe('transactions.types.TAX');
    });

    it('a new charge’s column is headed by the catalogue’s «new», never TX #0', async () => {
        mount({mode: 'deleteParent', parents: [structuredClone(BUY), structuredClone(SELL)], charges: [structuredClone(NEW_FEE), structuredClone(NEW_TAX)]});
        await dialog();
        const ths = await columnHeaders();
        for (const at of [1, 3]) {
            expect(ths[at].textContent ?? '', `column ${at}`).toContain('transactions.bulk.stateNew');
            expect(ths[at].textContent ?? '', `column ${at}`).not.toContain('#0');
        }
    });

    it('without counts, the keep after-line counts both new charges (2) and «all» names 2 parents + 2 charges (4)', async () => {
        mount({mode: 'deleteParent', parents: [structuredClone(BUY), structuredClone(SELL)], charges: [structuredClone(NEW_FEE), structuredClone(NEW_TAX)]});
        const dlg = await dialog();
        expect(holdsNumber(within(dlg).getByTestId('tx-charges-modal-keep-after').textContent, 2)).toBe(true);
        expect(holdsNumber(within(dlg).getByTestId('tx-charges-modal-all').textContent, 4)).toBe(true);
    });

    it('a saved charge and a new one under the same parent: both columns, the saved one headed by its #id', async () => {
        mount({mode: 'deleteParent', parents: [structuredClone(BUY)], charges: [structuredClone(FEE), structuredClone(NEW_FEE)]});
        await dialog();
        const ths = await columnHeaders();
        expect(ths).toHaveLength(3);
        expect(ths.map((th) => idOf(th))).toEqual([BUY.id, FEE.id, null]);
        expect(ths[2].textContent ?? '').toContain('transactions.bulk.stateNew');
    });
});

// ─── unlink mode (66 TL-9) ───────────────────────────────────────────────────────────────────────────────────────

/*
 * «Unlink the charges» from a table's selection bar: the panel gets the charges alone (`parents` is empty: a parent may
 * not be in the page's list, and it is not read from the server). One column per charge, and a field row `parent` — in
 * this mode only — naming each charge's own parent by its `#id`, taken from the charge itself.
 *
 * `mode: 'unlink'` is cast in `mountUnlink`: the component's union does not hold it until the mode exists.
 */
describe('TxChargesActionModal — unlink mode (66 TL-9)', () => {
    function mountUnlink(over: Partial<Props> = {}) {
        return mount({mode: 'unlink' as never, parents: [], charges: [structuredClone(TAX), structuredClone(FEE)], ...over});
    }

    /** The cell of field row `field` in the transaction column `columnId`, or null when the row is not drawn. */
    function cell(field: string, columnId: string): HTMLElement | null {
        return screen.getByTestId('tx-charges-modal-table').querySelector<HTMLElement>(`tbody tr[data-row-id="${field}"] td[data-column-id="${columnId}"]`);
    }

    /** The field rows drawn; ends with the five of every mode on screen (the barrier of an absence). */
    async function fieldRows(): Promise<string[]> {
        await headers();
        const rows = Array.from(screen.getByTestId('tx-charges-modal-table').querySelectorAll<HTMLElement>('tbody tr[data-row-id]')).map((tr) => tr.getAttribute('data-row-id') ?? '');
        expect(rows, 'premise: the five fields of every mode are drawn').toEqual(expect.arrayContaining(['date', 'type', 'cash', 'quantity', 'broker']));
        return rows;
    }

    it('publishes data-mode="unlink"', async () => {
        mountUnlink();
        const dlg = await dialog();
        expect(within(dlg).getByTestId('tx-charges-modal-content')).toHaveAttribute('data-mode', 'unlink');
    });

    it('one column per charge and no other transaction, in order, each header naming #<id>; column ids positional', async () => {
        mountUnlink();
        await dialog();
        const {ids, columnIds} = await txColumns();
        expect(ids).toEqual([TAX.id, FEE.id]);
        expect(columnIds).toEqual(['c0', 'c1']);
    });

    it('the row «parent» names each charge’s own parent by its #id, read from the charge (two parents, none listed)', async () => {
        mountUnlink({charges: [structuredClone(SELL_TAX), structuredClone(FEE)]});
        await dialog();
        expect(await fieldRows(), 'the field row «parent» is drawn in this mode').toContain('parent');
        expect(cell('parent', 'c0')?.textContent ?? '', 'the SELL’s TAX').toMatch(new RegExp(`#${SELL.id}\\b`));
        expect(cell('parent', 'c1')?.textContent ?? '', 'the BUY’s FEE').toMatch(new RegExp(`#${BUY.id}\\b`));
    });

    it('the row «parent» is a row of its own: the other five fields keep their cells, so the charge’s date is still there', async () => {
        mountUnlink();
        await dialog();
        const rows = await fieldRows();
        expect(rows).toHaveLength(6);
        expect((cell('date', 'c0')?.textContent ?? '').trim()).toBe(TAX.date);
    });

    it('link mode has no row «parent»', async () => {
        mount();
        await dialog();
        expect(await fieldRows()).not.toContain('parent');
    });

    it('deleteParent mode has no row «parent», although its charges have one', async () => {
        mount({mode: 'deleteParent', parents: [structuredClone(BUY)], charges: [structuredClone(FEE), structuredClone(TAX)]});
        await dialog();
        expect(await fieldRows()).not.toContain('parent');
    });

    it('the outcome names the count of the charges: 2', async () => {
        mountUnlink();
        const dlg = await dialog();
        const target = within(dlg).getByTestId('tx-charges-modal-target');
        expect(holdsNumber(target.textContent, 2), `the target names 2, got: ${target.textContent}`).toBe(true);
    });

    it('the outcome names the count of the charges: 1', async () => {
        mountUnlink({charges: [structuredClone(TAX)]});
        const dlg = await dialog();
        const target = within(dlg).getByTestId('tx-charges-modal-target');
        expect(holdsNumber(target.textContent, 1), `the target names 1, got: ${target.textContent}`).toBe(true);
    });

    it('has cancel and confirm, and no keep / all', async () => {
        mountUnlink();
        const dlg = await dialog();
        expect(within(dlg).getByTestId('tx-charges-modal-cancel')).toBeVisible();
        expect(within(dlg).getByTestId('tx-charges-modal-confirm')).toBeVisible();
        expect(within(dlg).queryByTestId('tx-charges-modal-keep')).toBeNull();
        expect(within(dlg).queryByTestId('tx-charges-modal-all')).toBeNull();
    });

    it('confirm calls onConfirm once, and neither onChoose nor onCancel', async () => {
        mountUnlink();
        const dlg = await dialog();
        const confirm = within(dlg).getByTestId('tx-charges-modal-confirm');
        expect(confirm).toBeEnabled();
        await fireEvent.click(confirm);
        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onChoose).not.toHaveBeenCalled();
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('cancel calls onCancel, not onConfirm', async () => {
        mountUnlink();
        const dlg = await dialog();
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-cancel'));
        expect(onCancel).toHaveBeenCalledTimes(1);
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('while loading, confirm is disabled and a click does not confirm', async () => {
        mountUnlink({loading: true});
        const dlg = await dialog();
        const confirm = within(dlg).getByTestId('tx-charges-modal-confirm');
        expect(confirm).toBeDisabled();
        await fireEvent.click(confirm);
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('closed: nothing is drawn', async () => {
        const {rerender} = mountUnlink();
        // Presence barrier: the same panel, open, is drawn.
        await dialog();
        await rerender({open: false});
        await waitFor(() => expect(screen.queryByTestId('tx-charges-modal-content')).toBeNull());
    });
});

// ─── storage ─────────────────────────────────────────────────────────────────────────────────────────────────────

describe('TxChargesActionModal — nothing tied to a transaction id reaches localStorage', () => {
    let storage: Map<string, string>;
    let writes: [string, string][];
    let reads: string[];
    let stub: Storage;

    beforeEach(() => {
        storage = new Map();
        writes = [];
        reads = [];
        stub = {
            get length() {
                return storage.size;
            },
            key: (i: number) => Array.from(storage.keys())[i] ?? null,
            getItem: (key: string) => {
                reads.push(key);
                return storage.get(key) ?? null;
            },
            setItem: (key: string, value: string) => {
                writes.push([key, String(value)]);
                storage.set(key, String(value));
            },
            removeItem: (key: string) => void storage.delete(key),
            clear: () => storage.clear(),
        };
        vi.stubGlobal('localStorage', stub);
    });

    afterEach(() => {
        // Unmount while the stub is still in place, then give the rest of the file back its storage-less jsdom.
        cleanup();
        vi.unstubAllGlobals();
    });

    function expectNoTxId(): void {
        // Presence barrier: DataTable reads its saved layout at mount, so the recorder must have seen the table's fixed
        // storage key (`txChargesModal`). Without it, «nothing names an id» would also hold for a table never mounted.
        expect(
            reads.some((key) => key.includes('dataTable_txChargesModal_')),
            `the table read its layout under the fixed storageKey; keys read: ${reads.join(', ')}`,
        ).toBe(true);
        for (const [key, value] of writes) {
            for (const id of ALL_IDS) {
                expect(key, `a written key names #${id}`).not.toContain(String(id));
                expect(value, `the value written under ${key} names #${id}`).not.toContain(String(id));
            }
        }
        for (const key of reads) for (const id of ALL_IDS) expect(key, `a read key names #${id}`).not.toContain(String(id));
    }

    it('link mode: mount, click every header and the buttons', async () => {
        expect(globalThis.localStorage, 'precondition: the recording storage is the one the component sees').toBe(stub);
        mount();
        const dlg = await dialog();
        for (const th of await headers()) await fireEvent.click(th);
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-confirm'));
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-cancel'));
        expectNoTxId();
    });

    it('unlink mode: mount, click every header and the buttons', async () => {
        expect(globalThis.localStorage, 'precondition: the recording storage is the one the component sees').toBe(stub);
        mount({mode: 'unlink' as never, parents: [], charges: [structuredClone(TAX), structuredClone(SELL_TAX)]});
        const dlg = await dialog();
        for (const th of await headers()) await fireEvent.click(th);
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-confirm'));
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-cancel'));
        expectNoTxId();
    });

    it('deleteParent with several parents: mount, click every header and the buttons', async () => {
        expect(globalThis.localStorage, 'precondition: the recording storage is the one the component sees').toBe(stub);
        mount({mode: 'deleteParent', parents: [structuredClone(BUY), structuredClone(SELL)], charges: [FEE, TAX, SELL_FEE, SELL_TAX, SELL_FEE2].map((r) => structuredClone(r))});
        const dlg = await dialog();
        for (const th of await headers()) await fireEvent.click(th);
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-keep'));
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-all'));
        await fireEvent.click(within(dlg).getByTestId('tx-charges-modal-cancel'));
        expectNoTxId();
    });
});
