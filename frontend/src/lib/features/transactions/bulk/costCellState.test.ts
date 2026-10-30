/**
 * costCellState (W6-2, V-24) — what the Bulk editor's cost cell shows in cost mode «auto».
 *
 * In Auto the editor sends `{code, amount: '0'}` as a currency hint, not as a cost. So until validation has come
 * back (`settled`: nothing pending or running, and at least one run done) an amount of zero is a placeholder and
 * the cell must not read as a computed 0.00. Once settled, a zero is a computed value (a split lot costs nothing).
 *
 * - 'ready'   — a computed cost to show;
 * - 'pending' — nothing to show yet, the server has not answered;
 * - 'empty'   — settled, and there is no cost.
 *
 * The module is imported statically: it was loaded by name per case while it did not exist (the red phase), and under a loaded
 * machine the first dynamic load of `../txPayloadHelpers` took longer than the 5 s a case is given.
 */
import {describe, expect, it} from 'vitest';
import {autoCostCellState as stateOf} from './costCellState';

type CellState = 'ready' | 'pending' | 'empty';

/** Kept `async` so the cases below read the same as when the module was loaded by name. */
async function autoCostCellState(amount: string | null | undefined, settled: boolean): Promise<CellState> {
    return stateOf(amount, settled);
}

describe('autoCostCellState — amount absent or empty', () => {
    it.each([null, undefined, ''])('%j is pending while validation is unsettled', async (amount) => {
        expect(await autoCostCellState(amount, false)).toBe('pending');
    });

    it.each([null, undefined, ''])('%j is empty once validation has settled', async (amount) => {
        expect(await autoCostCellState(amount, true)).toBe('empty');
    });
});

describe('autoCostCellState — a non-zero amount is a computed cost, settled or not', () => {
    it.each(['12.34', '-5', '0.01', '-0.01', '1000000000000.000001'])('%s is ready unsettled and settled', async (amount) => {
        expect(await autoCostCellState(amount, false)).toBe('ready');
        expect(await autoCostCellState(amount, true)).toBe('ready');
    });

    it('compares exactly: a digit far past the float precision still makes it non-zero', async () => {
        expect(await autoCostCellState('0.0000000000000000000001', false)).toBe('ready');
    });
});

describe('autoCostCellState — a zero amount is the currency-hint placeholder until settled, a true zero after', () => {
    it.each(['0', '0.00', '-0', '0.000000', '+0'])('%s is pending while unsettled', async (amount) => {
        expect(await autoCostCellState(amount, false)).toBe('pending');
    });

    it.each(['0', '0.00', '-0', '0.000000', '+0'])('%s is ready once settled: a computed zero cost (a split lot)', async (amount) => {
        expect(await autoCostCellState(amount, true)).toBe('ready');
    });
});
