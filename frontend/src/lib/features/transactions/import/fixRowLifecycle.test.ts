import {describe, it, expect} from 'vitest';
import {isDupRelevantBlocker, isUnallocatedAssetWarning, isCashSplitWarning, isFixStepTodo, rowStaysInFixStep, todosAfterSettle, todosAfterReopen, type FixTodoLike} from './fixRowLifecycle';

const blocker = (field: string): FixTodoLike => ({severity: 'blocker', field});
const warning = (field: string, context?: unknown): FixTodoLike => ({severity: 'warning', field, context});

describe('fix step membership predicates', () => {
    it('claims a blocker on a field the duplicate comparison keys on', () => {
        for (const field of ['type', 'date', 'quantity', 'asset_id', 'cash', 'cash.amount', 'cash.code']) {
            expect(isDupRelevantBlocker(blocker(field))).toBe(true);
        }
    });

    it('leaves a cost-basis blocker to the bulk editor', () => {
        // It blocks the import, not the comparison — and this step has no per-unit tooling.
        expect(isDupRelevantBlocker(blocker('cost_basis_override'))).toBe(false);
        expect(isFixStepTodo(blocker('cost_basis_override'))).toBe(false);
    });

    it('claims an unallocated charge, which is a warning and not a blocker', () => {
        expect(isUnallocatedAssetWarning(warning('asset_id'))).toBe(true);
        expect(isUnallocatedAssetWarning(blocker('asset_id'))).toBe(false);
    });

    it('claims a split hint whatever field it is filed under', () => {
        expect(isCashSplitWarning(warning('cash', {split_hint: 'trade_charges'}))).toBe(true);
        expect(isCashSplitWarning(warning('cash', {reason: 'fund_redemption'}))).toBe(false);
        expect(isCashSplitWarning(warning('cash'))).toBe(false);
    });

    it('does not claim a split hint carried by a blocker: the blocker path already has it', () => {
        expect(isCashSplitWarning({severity: 'blocker', field: 'cash', context: {split_hint: 'trade_charges'}})).toBe(false);
    });
});

describe('rowStaysInFixStep', () => {
    it('keeps a row that still carries something to fix', () => {
        expect(rowStaysInFixStep([blocker('type')], null)).toBe(true);
    });

    it('keeps a settled row, whose todos have been retired', () => {
        expect(rowStaysInFixStep([], 'corrected')).toBe(true);
        expect(rowStaysInFixStep([], 'kept')).toBe(true);
    });

    it('drops a row with neither: it was never this step’s business', () => {
        expect(rowStaysInFixStep([warning('cost_basis_override')], null)).toBe(false);
        expect(rowStaysInFixStep([], undefined)).toBe(false);
    });
});

describe('settling and re-opening a row', () => {
    it('retires the step’s todos and keeps the others', () => {
        const kept = warning('cost_basis_override');
        expect(todosAfterSettle([blocker('type'), kept, warning('cash', {split_hint: 'x'})])).toEqual([kept]);
    });

    it('gives the todos back when the decision is withdrawn', () => {
        const snapshot = [blocker('type'), warning('asset_id')];
        const settled = todosAfterSettle([...snapshot, warning('cost_basis_override')]);

        const reopened = todosAfterReopen(settled, snapshot);

        expect(reopened).toHaveLength(3);
        expect(rowStaysInFixStep(reopened, null)).toBe(true);
    });

    it('the defect: re-opening without restoring makes the row vanish', () => {
        // This is what shipped. Kept as an executable statement of why the snapshot exists:
        // withdraw the decision, hand back nothing, and the row matches neither half of the
        // membership test — it disappeared mid-edit and only a reload brought it back.
        const settled = todosAfterSettle([blocker('type')]);

        expect(rowStaysInFixStep(settled, null)).toBe(false);
        expect(rowStaysInFixStep(todosAfterReopen(settled, [blocker('type')]), null)).toBe(true);
    });

    it('does not duplicate the step’s todos when re-opening twice', () => {
        const snapshot = [blocker('type')];
        const once = todosAfterReopen(todosAfterSettle(snapshot), snapshot);
        const twice = todosAfterReopen(once, snapshot);

        expect(twice).toHaveLength(1);
    });

    it('leaves the row alone when no snapshot was ever taken', () => {
        const current = [warning('cost_basis_override')];
        expect(todosAfterReopen(current, undefined)).toEqual(current);
    });
});
