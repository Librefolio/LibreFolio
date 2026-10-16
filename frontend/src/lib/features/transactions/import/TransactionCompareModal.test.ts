// @vitest-environment jsdom
/**
 * TransactionCompareModal — component test (Vitest + jsdom)
 *
 * The grid the import wizard opens when two rows look like the same transaction
 * and the user has to decide whether they are. It had **zero branch coverage**
 * out of 75 — not dead code, simply a step of the import flow that no test ever
 * reached.
 *
 * It is deliberately dumb: the parent formats every cell (`display`) and hands
 * in a normalised token (`cmp`) used only for diffing, so an icon or a currency
 * span never counts as a difference. That makes it a pure function of its props
 * and a natural component test — reaching the same ground through Playwright
 * would mean staging a duplicate import for every shape below.
 *
 * The judgement worth pinning is what it calls an **outlier**. With three
 * columns and one disagreeing, the odd one out is a finding. With two columns
 * that disagree there is no majority, and the component highlights *both* rather
 * than picking one — as its own comment puts it, calling one of them wrong would
 * be a coin toss dressed up as a finding. That rule is easy to "simplify" into a
 * bug, so it is asserted from three directions here.
 *
 * On assertions: `data-differs` and `data-outlier` were added for this file.
 * Both states existed only as background colours, so the alternative was to
 * assert on a Tailwind class — the thing the rules forbid, and rightly: a colour
 * is not a contract, and the last time a test in this repo asserted on one it
 * was the only test that broke during a refactor that changed no behaviour.
 */
import {describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import TransactionCompareModal, {type CompareColumn, type CompareField} from './TransactionCompareModal.svelte';

await setupI18n();

const FIELDS: CompareField[] = [
    {key: 'date', label: 'Date'},
    {key: 'amount', label: 'Amount', align: 'right'},
];

/** A column whose cells are plain text; `cmp` defaults to the display value. */
function col(id: string, cells: Record<string, string>, over: Partial<CompareColumn> = {}): CompareColumn {
    return {
        id,
        title: `file-${id}.csv`,
        selectable: true,
        cells: Object.fromEntries(Object.entries(cells).map(([k, v]) => [k, {display: v, cmp: v}])),
        ...over,
    };
}

function mount(columns: CompareColumn[], props: Record<string, unknown> = {}) {
    const onClose = vi.fn();
    const onKeep = vi.fn();
    const utils = render(TransactionCompareModal, {open: true, title: 'Compare', fields: FIELDS, columns, onClose, onKeep, ...props});
    return {onClose, onKeep, ...utils};
}

/** The cells of one field row, in column order. */
function cellsOf(fieldKey: string): HTMLElement[] {
    const row = screen.getAllByTestId('import-wizard-compare-row').find((r) => r.getAttribute('data-field') === fieldKey);
    if (!row) throw new Error(`no row for field "${fieldKey}" — fields rendered: ${screen.getAllByTestId('import-wizard-compare-row').map((r) => r.getAttribute('data-field'))}`);
    return within(row).getAllByTestId('import-wizard-compare-cell');
}

function outliersOf(fieldKey: string): string[] {
    return cellsOf(fieldKey)
        .filter((c) => c.getAttribute('data-outlier') === 'true')
        .map((c) => c.getAttribute('data-col') ?? '');
}

function rowDiffers(fieldKey: string): boolean {
    const row = screen.getAllByTestId('import-wizard-compare-row').find((r) => r.getAttribute('data-field') === fieldKey);
    return row?.getAttribute('data-differs') === 'true';
}

describe('what counts as a difference', () => {
    it('says nothing differs when every column agrees', () => {
        mount([col('a', {date: '2024-01-01', amount: '10'}), col('b', {date: '2024-01-01', amount: '10'})]);
        expect(rowDiffers('date')).toBe(false);
        expect(outliersOf('date')).toEqual([]);
    });

    it('compares the token, not what is on screen', () => {
        // The whole reason `cmp` exists: an icon or a currency span must not read
        // as a difference when the underlying value is the same.
        const a: CompareColumn = {id: 'a', title: 'A', selectable: true, cells: {date: {display: '<b>1 Jan</b>', cmp: '2024-01-01', html: true}, amount: {display: '10', cmp: '10'}}};
        const b: CompareColumn = {id: 'b', title: 'B', selectable: true, cells: {date: {display: '01/01/2024', cmp: '2024-01-01'}, amount: {display: '10', cmp: '10'}}};
        mount([a, b]);
        expect(rowDiffers('date')).toBe(false);
    });

    it('treats a missing cell as a value of its own', () => {
        const b: CompareColumn = {id: 'b', title: 'B', selectable: true, cells: {amount: {display: '10', cmp: '10'}}};
        mount([col('a', {date: '2024-01-01', amount: '10'}), b]);
        expect(rowDiffers('date')).toBe(true);
        // …and the column with nothing to show says so rather than rendering blank.
        expect(cellsOf('date')[1]).toHaveTextContent('—');
    });
});

describe('which cell is the odd one out', () => {
    it('marks the single dissenter when the others agree', () => {
        mount([col('a', {date: '2024-01-01'}), col('b', {date: '2024-01-01'}), col('c', {date: '2024-03-09'})]);
        expect(outliersOf('date')).toEqual(['c']);
    });

    it('marks both when two columns simply disagree', () => {
        // No majority exists, so neither is "the wrong one".
        mount([col('a', {date: '2024-01-01'}), col('b', {date: '2024-03-09'})]);
        expect(outliersOf('date')).toEqual(['a', 'b']);
    });

    it('marks every column when a three-way tie leaves no majority', () => {
        mount([col('a', {date: 'x'}), col('b', {date: 'y'}), col('c', {date: 'z'})]);
        expect(outliersOf('date')).toEqual(['a', 'b', 'c']);
    });

    it('marks every column when two readings are equally common', () => {
        // 2–2 is a tie: promoting either pair would be arbitrary.
        mount([col('a', {date: 'x'}), col('b', {date: 'x'}), col('c', {date: 'y'}), col('d', {date: 'y'})]);
        expect(outliersOf('date')).toEqual(['a', 'b', 'c', 'd']);
    });

    it('marks both dissenters when the majority is real but not alone', () => {
        mount([col('a', {date: 'x'}), col('b', {date: 'x'}), col('c', {date: 'x'}), col('d', {date: 'y'}), col('e', {date: 'z'})]);
        expect(outliersOf('date')).toEqual(['d', 'e']);
    });

    it('marks nothing on a field where the columns agree, even when another differs', () => {
        mount([col('a', {date: '2024-01-01', amount: '10'}), col('b', {date: '2024-03-09', amount: '10'})]);
        expect(outliersOf('date')).toEqual(['a', 'b']);
        expect(outliersOf('amount')).toEqual([]);
    });
});

describe('the part of the value that actually differs', () => {
    /** The highlighted fragment of a cell, or null when nothing is marked. */
    function markOf(fieldKey: string, index: number): string | null {
        return within(cellsOf(fieldKey)[index]).queryByTestId('import-wizard-compare-diff')?.querySelector('mark')?.textContent ?? null;
    }

    it('marks only the tail when two values share a prefix', () => {
        // The case that motivated it: two ISINs differing by one trailing letter
        // are indistinguishable side by side in a narrow column.
        mount([col('a', {date: 'IT0005FOICU'}), col('b', {date: 'IT0005FOICUM'})]);
        expect(markOf('date', 1)).toBe('M');
    });

    it('marks only the head when two values share a suffix', () => {
        mount([col('a', {date: 'AAA-999'}), col('b', {date: 'BBB-999'})]);
        expect(markOf('date', 0)).toBe('AAA');
        expect(markOf('date', 1)).toBe('BBB');
    });

    it('marks the middle when both ends match', () => {
        mount([col('a', {date: 'IT0001X'}), col('b', {date: 'IT0002X'})]);
        expect(markOf('date', 0)).toBe('1');
        expect(markOf('date', 1)).toBe('2');
    });

    it('marks the whole value when the two share nothing', () => {
        mount([col('a', {date: 'abc'}), col('b', {date: 'xyz'})]);
        expect(markOf('date', 0)).toBe('abc');
    });

    it('marks nothing when a cell is empty', () => {
        // There is no "differing part" of a value that is not there.
        mount([col('a', {date: ''}), col('b', {date: 'something'})]);
        expect(markOf('date', 0)).toBeNull();
    });

    it('leaves an html cell whole, since its markup is not text to slice', () => {
        const a: CompareColumn = {id: 'a', title: 'A', selectable: true, cells: {date: {display: '<b>one</b>', cmp: 'one', html: true}}};
        mount([a, col('b', {date: 'two'})]);
        expect(markOf('date', 0)).toBeNull();
        expect(cellsOf('date')[0]).toHaveTextContent('one');
    });

    it('compares against the majority reading rather than the neighbour', () => {
        // Three columns: the dissenter is measured against what the other two say.
        mount([col('a', {date: 'IT0001'}), col('b', {date: 'IT0001'}), col('c', {date: 'IT0009'})]);
        expect(markOf('date', 2)).toBe('9');
    });
});

describe('choosing what to keep', () => {
    it('offers the toggles only when the parent can act on them', () => {
        mount([col('a', {date: 'x'}), col('b', {date: 'y'})], {onKeep: undefined});
        expect(screen.queryByTestId('import-wizard-compare-keep-all')).toBeNull();
    });

    it('offers nothing to choose between when only one column is selectable', () => {
        mount([col('a', {date: 'x'}), col('b', {date: 'y'}, {selectable: false})]);
        expect(screen.queryByTestId('import-wizard-compare-keep-all')).toBeNull();
    });

    it('starts with every selectable column kept', () => {
        mount([col('a', {date: 'x'}), col('b', {date: 'y'}), col('c', {date: 'z'}, {selectable: false})]);
        expect(screen.getByTestId('import-wizard-compare-keep-a')).toBeChecked();
        expect(screen.getByTestId('import-wizard-compare-keep-b')).toBeChecked();
        expect(screen.queryByTestId('import-wizard-compare-keep-c')).toBeNull();
    });

    it('honours the parent choice of what starts kept', () => {
        mount([col('a', {date: 'x'}), col('b', {date: 'y'})], {defaultKept: ['b']});
        expect(screen.getByTestId('import-wizard-compare-keep-a')).not.toBeChecked();
        expect(screen.getByTestId('import-wizard-compare-keep-b')).toBeChecked();
    });

    it('is a set of toggles, not a single choice', async () => {
        // It mirrors the resolver table, and the two views arbitrate the same
        // thing: they must not disagree on how a choice is made.
        mount([col('a', {date: 'x'}), col('b', {date: 'y'})]);
        await fireEvent.click(screen.getByTestId('import-wizard-compare-keep-a'));
        expect(screen.getByTestId('import-wizard-compare-keep-a')).not.toBeChecked();
        expect(screen.getByTestId('import-wizard-compare-keep-b')).toBeChecked();
        await fireEvent.click(screen.getByTestId('import-wizard-compare-keep-a'));
        expect(screen.getByTestId('import-wizard-compare-keep-a')).toBeChecked();
    });

    it('takes them all back with the keep-all control', async () => {
        mount([col('a', {date: 'x'}), col('b', {date: 'y'})], {defaultKept: []});
        await fireEvent.click(screen.getByTestId('import-wizard-compare-keep-all'));
        expect(screen.getByTestId('import-wizard-compare-keep-a')).toBeChecked();
        expect(screen.getByTestId('import-wizard-compare-keep-b')).toBeChecked();
    });

    it('offers a way back to the parent default, and only when there is one', async () => {
        const {unmount} = mount([col('a', {date: 'x'}), col('b', {date: 'y'})], {resetKept: ['a']});
        await fireEvent.click(screen.getByTestId('import-wizard-compare-reset'));
        expect(screen.getByTestId('import-wizard-compare-keep-a')).toBeChecked();
        expect(screen.getByTestId('import-wizard-compare-keep-b')).not.toBeChecked();
        unmount();

        mount([col('a', {date: 'x'}), col('b', {date: 'y'})]);
        expect(screen.queryByTestId('import-wizard-compare-reset')).toBeNull();
    });
});

describe('leaving the modal', () => {
    it('reports the selection and closes, in that order', async () => {
        const {onKeep, onClose} = mount([col('a', {date: 'x'}), col('b', {date: 'y'})], {defaultKept: ['a']});
        await fireEvent.click(screen.getByTestId('import-wizard-compare-apply'));
        expect(onKeep).toHaveBeenCalledWith(['a']);
        expect(onClose).toHaveBeenCalled();
        expect(onKeep.mock.invocationCallOrder[0]).toBeLessThan(onClose.mock.invocationCallOrder[0]);
    });

    it('reports an empty selection rather than nothing at all', async () => {
        const {onKeep} = mount([col('a', {date: 'x'}), col('b', {date: 'y'})], {defaultKept: []});
        await fireEvent.click(screen.getByTestId('import-wizard-compare-apply'));
        expect(onKeep).toHaveBeenCalledWith([]);
    });

    it('closes without reporting when dismissed', async () => {
        const {onKeep, onClose} = mount([col('a', {date: 'x'}), col('b', {date: 'y'})]);
        await fireEvent.click(screen.getByTestId('import-wizard-compare-close'));
        expect(onClose).toHaveBeenCalled();
        expect(onKeep).not.toHaveBeenCalled();
    });

    it('offers only a way out when there is nothing to decide', async () => {
        // With no `onKeep` the grid is a read-only comparison: applying a choice
        // the parent cannot receive would be a button that does nothing.
        const {onClose} = mount([col('a', {date: 'x'}), col('b', {date: 'y'})], {onKeep: undefined});
        expect(screen.queryByTestId('import-wizard-compare-apply')).toBeNull();
        await fireEvent.click(screen.getByTestId('import-wizard-compare-close'));
        expect(onClose).toHaveBeenCalled();
    });
});

describe('the column headers', () => {
    it('numbers the first nine with a circled digit and the rest plainly', () => {
        // The badge takes the place of the keep toggle, so it only shows where
        // there is no choice to make.
        const many = Array.from({length: 10}, (_, i) => col(`c${i}`, {date: `d${i}`}));
        mount(many, {onKeep: undefined});
        expect(screen.getByTestId('import-wizard-compare-col-c0')).toHaveTextContent('①');
        expect(screen.getByTestId('import-wizard-compare-col-c8')).toHaveTextContent('⑨');
        expect(screen.getByTestId('import-wizard-compare-col-c9')).toHaveTextContent('#10');
    });

    it('shows the provenance, and the second line only when there is one', () => {
        mount([col('a', {date: 'x'}, {title: 'jan.csv', subtitle: 'Fineco'}), col('b', {date: 'y'}, {title: 'DB #42'})]);
        const first = screen.getByTestId('import-wizard-compare-col-a');
        expect(first).toHaveTextContent('jan.csv');
        expect(first).toHaveTextContent('Fineco');
        expect(screen.getByTestId('import-wizard-compare-col-b')).toHaveTextContent('DB #42');
    });
});

describe('the hint above the grid', () => {
    it('is there when the parent supplies one', () => {
        mount([col('a', {date: 'x'}), col('b', {date: 'y'})], {hint: 'Pick the row to keep'});
        expect(screen.getByText('Pick the row to keep')).toBeVisible();
    });

    it('takes no room when it does not', () => {
        mount([col('a', {date: 'x'}), col('b', {date: 'y'})]);
        expect(screen.queryByText('Pick the row to keep')).toBeNull();
    });
});
