// @vitest-environment jsdom
/**
 * DataTable — the two editable cells the asset profile needs (plan 68, E10a, §3.7): a date and an amount.
 *
 * - `editable-date`: the app's own `SingleDatePicker` (typed or picked; never a native date input, which follows the
 *   browser's language, not the app's: `nativeDateInput.gate.test.ts`); future dates allowed (a maturity); a date →
 *   `onchange('yyyy-mm-dd')`, a cleared field → `onchange(null)`.
 * - `editable-amount`: a decimal text and a currency, side by side. The number is typed as text (a native number input
 *   reads the browser locale and eats «5,9»), normalized on blur («1.234,56» → «1234.56») and handed over as TEXT, never
 *   a float, so 55 173 000 000 or 0.0000001 stay exact. An empty field → `amount: null`; a text that is not a number →
 *   nothing is handed over and the field says it is invalid (`aria-invalid`). The currency is a choice among
 *   `currencies`; picking one hands over the amount as it is with the new currency.
 * - `editable-text` (E10c3): an optional `unit` drawn beside the field, inside the cell («0.19 %», «6.8 years»), so a
 *   value typed in percent is not read as a fraction; without one the cell is the field alone.
 * - `editable-select` (E10c2): an optional `placeholder` while nothing is chosen, and an optional `testId` — the select
 *   is `<testId>`, each option `<testId>-option-<value>` — so a table with many select cells (the profile window's voice
 *   and value columns) can be driven without reading translated text.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import DataTable from './DataTable.svelte';
import type {ColumnDef} from './types';

type Row = {id: string; v: unknown};

function mount(cellValue: unknown) {
    render(DataTable, {
        data: [{id: 'r1', v: cellValue}],
        columns: [{id: 'v', header: 'V', type: 'text', cell: (r: Row) => r.v}] as unknown as ColumnDef<unknown>[],
        getRowId: ((r: Row) => r.id) as (row: unknown) => string,
        storageKey: `date-amount-${Math.random()}`,
    });
}

const CURRENCIES = [
    {value: 'EUR', label: 'EUR €'},
    {value: 'USD', label: 'USD $'},
];

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

describe('DataTable — editable-date', () => {
    const dateInput = () => screen.getByTestId('cell-editable-date') as HTMLInputElement;

    it("is the app's own date field, never a native date input (it follows the browser language)", () => {
        mount({type: 'editable-date', value: '2028-10-10', onchange: vi.fn()});

        expect(dateInput().type).not.toBe('date');
        expect(dateInput().value).toBe('2028-10-10');
        expect(screen.getByTestId('cell-editable-date-root')).toBeInTheDocument();
    });

    it('hands over a typed date, future dates included (a maturity)', async () => {
        const onchange = vi.fn();
        mount({type: 'editable-date', value: '2028-10-10', onchange});

        await fireEvent.input(dateInput(), {target: {value: '2031-05-01'}});
        await fireEvent.blur(dateInput());

        expect(onchange).toHaveBeenLastCalledWith('2031-05-01');
    });

    it('reads a cleared field as null', async () => {
        const onchange = vi.fn();
        mount({type: 'editable-date', value: '2028-10-10', onchange});

        await fireEvent.focus(dateInput());
        await fireEvent.click(screen.getByTestId('cell-editable-date-clear'));

        expect(onchange).toHaveBeenLastCalledWith(null);
    });
});

describe('DataTable — editable-amount', () => {
    const amountInput = () => screen.getByTestId('cell-editable-amount-value') as HTMLInputElement;

    it('normalizes the typed number on blur and hands it over as text with the currency', async () => {
        const onchange = vi.fn();
        mount({type: 'editable-amount', amount: '55173000000', currency: 'EUR', currencies: CURRENCIES, onchange});
        expect(amountInput().value).toBe('55173000000');

        await fireEvent.input(amountInput(), {target: {value: '1.234,56'}});
        await fireEvent.blur(amountInput());

        expect(onchange).toHaveBeenLastCalledWith({amount: '1234.56', currency: 'EUR'});
        expect(typeof onchange.mock.lastCall?.[0].amount).toBe('string');
    });

    it('keeps a tiny or huge amount exact: text, never a float', async () => {
        const onchange = vi.fn();
        mount({type: 'editable-amount', amount: null, currency: 'USD', currencies: CURRENCIES, onchange});

        await fireEvent.input(amountInput(), {target: {value: '0.0000001'}});
        await fireEvent.blur(amountInput());
        expect(onchange).toHaveBeenLastCalledWith({amount: '0.0000001', currency: 'USD'});

        await fireEvent.input(amountInput(), {target: {value: '12345678901234567890'}});
        await fireEvent.blur(amountInput());
        expect(onchange).toHaveBeenLastCalledWith({amount: '12345678901234567890', currency: 'USD'});
    });

    it('reads an emptied number as a null amount', async () => {
        const onchange = vi.fn();
        mount({type: 'editable-amount', amount: '10', currency: 'EUR', currencies: CURRENCIES, onchange});

        await fireEvent.input(amountInput(), {target: {value: ''}});
        await fireEvent.blur(amountInput());

        expect(onchange).toHaveBeenLastCalledWith({amount: null, currency: 'EUR'});
    });

    it('hands nothing over for a text that is not a number, and marks the field invalid', async () => {
        const onchange = vi.fn();
        mount({type: 'editable-amount', amount: '10', currency: 'EUR', currencies: CURRENCIES, onchange});

        await fireEvent.input(amountInput(), {target: {value: 'abc'}});
        await fireEvent.blur(amountInput());

        expect(onchange).not.toHaveBeenCalled();
        expect(amountInput()).toHaveAttribute('aria-invalid', 'true');
    });

    it('hands over the amount with the currency picked', async () => {
        const onchange = vi.fn();
        mount({type: 'editable-amount', amount: '10', currency: 'EUR', currencies: CURRENCIES, onchange});

        await fireEvent.click(screen.getByTestId('cell-editable-amount-currency-button'));
        await fireEvent.click(screen.getByTestId('cell-editable-amount-currency-option-USD'));

        expect(onchange).toHaveBeenLastCalledWith({amount: '10', currency: 'USD'});
    });
});

describe('DataTable — editable-select', () => {
    const OPTIONS = [
        {value: 'accumulating', label: 'Accumulating'},
        {value: 'distributing', label: 'Distributing'},
    ];

    it('names the select and its options after testId, and picks a value', async () => {
        const onchange = vi.fn();
        mount({type: 'editable-select', value: '', options: OPTIONS, placeholder: 'Choose one', testId: 'policy', onchange});

        expect(screen.getByTestId('policy-button')).toHaveTextContent('Choose one');
        await fireEvent.click(screen.getByTestId('policy-button'));
        await fireEvent.click(screen.getByTestId('policy-option-distributing'));

        expect(onchange).toHaveBeenCalledWith('distributing');
    });

    it('without a testId the cell keeps its old markup: no test ids', () => {
        mount({type: 'editable-select', value: 'accumulating', options: OPTIONS, onchange: vi.fn()});
        expect(document.querySelector('[data-testid^="undefined"]')).toBeNull();
        expect(screen.queryByTestId('policy-button')).toBeNull();
    });
});

describe('DataTable — editable-text with a unit', () => {
    it('draws the unit beside the field, and hands over the text typed', async () => {
        const onchange = vi.fn();
        mount({type: 'editable-text', value: '0.19', unit: '%', onchange});

        expect(screen.getByTestId('cell-editable-text-unit')).toHaveTextContent(/^%$/);
        const input = screen.getByTestId('cell-editable-text') as HTMLInputElement;
        await fireEvent.input(input, {target: {value: '0.20'}});
        await fireEvent.blur(input);
        expect(onchange).toHaveBeenCalledWith('0.20');
    });

    it('without a unit the cell is the field alone', () => {
        mount({type: 'editable-text', value: 'Vanguard', onchange: vi.fn()});
        expect(screen.queryByTestId('cell-editable-text-unit')).toBeNull();
    });
});
