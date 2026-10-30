/**
 * costCellState.ts — what the Bulk editor's cost cell shows in cost mode «auto» (W6-2, V-24).
 *
 * In Auto the form and the editor send `{code, amount: '0'}` as a currency hint, so a cost of 0 in the row is either that
 * hint (nothing computed yet) or a true zero cost (a split lot, a gift). Only the validation tells them apart: while one is
 * pending or running, or before the first has run, a zero is not yet an answer.
 */
import {exactDecimalSign} from '../txPayloadHelpers';

export type AutoCostCellState = 'ready' | 'pending' | 'empty';

/**
 * The state of an Auto cost cell. `settled`: no validation pending or running and at least one run done.
 * - no amount: `empty` once settled (there is nothing to propose), `pending` before;
 * - a non-zero amount: `ready`, whatever the validation does;
 * - a zero amount: `ready` once settled (a true zero cost), `pending` before (it may be only the hint).
 */
export function autoCostCellState(amount: string | null | undefined, settled: boolean): AutoCostCellState {
    const sign = exactDecimalSign(amount);
    if (sign === null) return settled ? 'empty' : 'pending';
    if (sign !== 0) return 'ready';
    return settled ? 'ready' : 'pending';
}
