// @vitest-environment jsdom
/**
 * ErasableNumberCell — component test (Vitest + jsdom). N92 (i) with «clear» (developer's decisions of 19/10).
 *
 * The cell of an optional OHLC/volume column in the asset's data editor (F.5). It is controlled: it never changes
 * `value`, it calls `onchange(next)` and waits to be re-rendered, so these tests assert the call — the contract with
 * DataEditor — and render a value to read the state it shows.
 *
 * Before N92 the «cleared» value was the number -1: the eraser called `onchange(-1)`, a value of -1 showed the cleared
 * state, and the save path sent -1, which the server read as «set NULL». So a -1 read from a CSV looked erased and
 * erased the stored value.
 *
 * The contract (N92): the cleared value is the text `'clear'`, the one the server reads as «set NULL».
 * - the eraser (`erasable-cell-eraser`), and `Delete` on an empty field, call `onchange('clear')`;
 * - a value `'clear'` shows the cleared state; clicking it opens an empty field, and a number typed there is handed on;
 * - a value of -1 is a number like any other: shown in the field.
 *
 * The cleared state publishes no `data-state`: it is the state that renders no text field (a button replaces the input,
 * besides the eraser). The tests read that structure — never the translated «not set» label, never a CSS class. If the
 * cure gives the cell a `data-state`, switch the reads to it.
 *
 * RED (expected failure before the cure): the eraser and `Delete` call `onchange(-1)`; a value `'clear'` renders a field
 * holding the text «clear» (no cleared state); a value of -1 renders the cleared state (no field). GUARD (green before
 * and after): null shows an empty field; a typed number is handed on as a number; a negative typed number is clamped to
 * the column's `min` (0 in the editor), which is why a negative OHLC value only reaches a save from a CSV import.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, `front_component_unit` (action `component-unit`).
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import ErasableNumberCell from './ErasableNumberCell.svelte';

/** What the cell may be given: a number, the cleared marker, or nothing (not set). */
type CellValue = number | 'clear' | null | undefined;

/** The cell rendered with `value` (typed loosely: before N92 its props declare no `'clear'`), its `onchange` a spy. */
function mount(value: CellValue, extra: {min?: number} = {}) {
    const onchange = vi.fn();
    const props = {value, onchange, ...extra} as unknown as ComponentProps<typeof ErasableNumberCell>;
    render(ErasableNumberCell, {props});
    return {onchange, cell: screen.getByTestId('erasable-number-cell')};
}

/** The cell's text field, or null in the cleared state. */
function field(cell: HTMLElement): HTMLInputElement | null {
    return within(cell).queryByRole('textbox') as HTMLInputElement | null;
}

/** The buttons of the cell other than the eraser: the cleared state renders exactly one. */
function clearedButtons(cell: HTMLElement): HTMLButtonElement[] {
    return Array.from(cell.querySelectorAll<HTMLButtonElement>('button:not([data-testid="erasable-cell-eraser"])'));
}

beforeAll(async () => {
    await setupI18n();
});

describe('ErasableNumberCell — erasing hands the parent the text clear (N92)', () => {
    it('the eraser calls onchange once, with clear', async () => {
        const {onchange, cell} = mount(12.5);

        await fireEvent.click(within(cell).getByTestId('erasable-cell-eraser'));

        expect(onchange).toHaveBeenCalledTimes(1);
        expect(onchange).toHaveBeenLastCalledWith('clear');
    });

    it('Delete on an empty field erases it as the eraser does: onchange(clear)', async () => {
        const {onchange, cell} = mount(null);
        const input = field(cell);
        expect(input, 'premise: a value not set shows a text field').not.toBeNull();

        await fireEvent.focus(input!);
        await fireEvent.keyDown(input!, {key: 'Delete'});

        expect(onchange).toHaveBeenCalledTimes(1);
        expect(onchange).toHaveBeenLastCalledWith('clear');
    });
});

describe('ErasableNumberCell — the cleared state is the value clear, and -1 is a number (N92)', () => {
    it('a value clear shows the cleared state: no text field, one button besides the eraser', () => {
        const {cell} = mount('clear');

        expect(field(cell), 'a value clear must show the cleared state, not a field holding the text').toBeNull();
        expect(clearedButtons(cell)).toHaveLength(1);
    });

    it('clicking the cleared state opens an empty field, and a number typed there is handed on', async () => {
        const {onchange, cell} = mount('clear');
        const [cleared] = clearedButtons(cell);
        expect(cleared, 'premise: a value clear shows the cleared state').toBeDefined();

        await fireEvent.click(cleared);
        const input = field(cell);
        expect(input, 'clicking the cleared state opens a field').not.toBeNull();
        expect(input!.value).toBe('');
        await fireEvent.input(input!, {target: {value: '7.25'}});
        await fireEvent.blur(input!);

        expect(onchange).toHaveBeenLastCalledWith(7.25);
    });

    it('a value of -1 is a number like any other: shown in the field, not as cleared', () => {
        const {cell} = mount(-1);

        const input = field(cell);
        expect(input, 'a value of -1 must show a field holding it, not the cleared state').not.toBeNull();
        expect(input!.value).toBe('-1');
        expect(clearedButtons(cell)).toHaveLength(0);
    });
});

describe('ErasableNumberCell — guards, green before and after N92', () => {
    it('a value not set shows an empty field, not the cleared state', () => {
        const {cell} = mount(null);

        expect(field(cell)?.value).toBe('');
        expect(clearedButtons(cell)).toHaveLength(0);
    });

    it('a typed number is handed on as a number', async () => {
        const {onchange, cell} = mount(5);
        const input = field(cell)!;

        await fireEvent.focus(input);
        await fireEvent.input(input, {target: {value: '7.5'}});
        await fireEvent.blur(input);

        expect(onchange).toHaveBeenCalledTimes(1);
        expect(onchange).toHaveBeenLastCalledWith(7.5);
    });

    it('a negative typed number is clamped to min 0, as in the editor: the field never hands on a negative', async () => {
        const {onchange, cell} = mount(5, {min: 0});
        const input = field(cell)!;

        await fireEvent.focus(input);
        await fireEvent.input(input, {target: {value: '-3'}});
        await fireEvent.blur(input);

        expect(onchange).toHaveBeenCalledTimes(1);
        expect(onchange).toHaveBeenLastCalledWith(0);
    });
});
