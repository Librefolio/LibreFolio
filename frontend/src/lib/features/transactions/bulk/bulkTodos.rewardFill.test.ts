/**
 * bulkTodos.ts — «fill from price history» (project 79, STK-4b): the pure half of the bulk workspace's reward fill.
 *
 * A REWARD whose file gave no value arrives in the editor with the blocking todo `{field: 'cost_basis_override',
 * severity: 'blocker', reasonCode: 'reward_value'}` (STK-4a). The banner's button asks the backend for the close of
 * each row's day and writes the values back. The contract pinned here:
 *
 *   - `isRewardValueTodo(todo)`: exactly that todo — the field, the blocker severity and the reason, all three;
 *   - `rewardFillCandidates(ops)`: the rows with such an open todo AND no value written by hand (`hasManualCost`: an
 *     Auto row's sentinel is no value, a Manual `'0'` is one), in the grid's order, as `{tempId, assetId, date}` (a row
 *     without an asset is still a candidate: the modal answers it NO_HISTORY locally);
 *   - `applyRewardFill(ops, answers)`: each FILLED answer with a value writes it in Manual, the price currency as given,
 *     and the row's todo retires through `remainingTodos` (the key is dropped when nothing is left, other todos stay);
 *     every other row is returned as the same object, its todo open; a row that already holds a value is never
 *     overwritten. The counts say how many rows were filled, had no close that day, had no history. The input is
 *     never changed.
 *
 * Node env, pure functions; data built here.
 */
import {describe, expect, it} from 'vitest';
import {REWARD_VALUE_REASON, applyRewardFill, isRewardValueTodo, rewardFillCandidates, type RewardFillAnswer, type RewardFillOp} from './bulkTodos';

type Todo = {field: string; severity?: string; reasonCode?: string; message?: string};
type Op = RewardFillOp & {fields: RewardFillOp['fields'] & {description?: string; quantity?: string}; todos?: Todo[]; marker?: string};

const REWARD_TODO: Todo = {field: 'cost_basis_override', severity: 'blocker', reasonCode: 'reward_value', message: 'Line 3: the file gives no value'};
const DESCRIPTION_TODO: Todo = {field: 'description', severity: 'warning', reasonCode: 'probe_description', message: 'Invented todo on another field'};

/** A REWARD row of the editor; `todos` null: a row without the key. */
function op(tempId: string, overrides: Partial<Op['fields']> = {}, todos: Todo[] | null = [REWARD_TODO]): Op {
    return {
        tempId,
        marker: `row ${tempId}`,
        fields: {asset_id: 42, date: '2024-03-04', cost_basis_mode: 'manual', cost_basis_override: null, quantity: '0.5', description: '', ...overrides},
        ...(todos ? {todos} : {}),
    };
}

const filledAnswer = (tempId: string, amount = '61.25', code = 'USD'): RewardFillAnswer => ({tempId, status: 'FILLED', value: {code, amount}});
const noPrice = (tempId: string): RewardFillAnswer => ({tempId, status: 'NO_PRICE_THAT_DAY', value: null});
const noHistory = (tempId: string): RewardFillAnswer => ({tempId, status: 'NO_HISTORY', value: null});

function deepFreeze<T>(value: T): T {
    if (value && typeof value === 'object') {
        for (const inner of Object.values(value as Record<string, unknown>)) deepFreeze(inner);
        Object.freeze(value);
    }
    return value;
}

describe('isRewardValueTodo — the field, the blocker and the reason', () => {
    it('the reason is reward_value', () => {
        expect(REWARD_VALUE_REASON).toBe('reward_value');
    });

    it('the reward_value blocker on the cost basis is one', () => {
        expect(isRewardValueTodo(REWARD_TODO)).toBe(true);
    });

    it.each([
        ['a warning', {...REWARD_TODO, severity: 'warning'}],
        ['no severity', {field: 'cost_basis_override', reasonCode: 'reward_value'}],
        ['another reason (a corporate action)', {...REWARD_TODO, reasonCode: 'corporate_action'}],
        ['no reason', {field: 'cost_basis_override', severity: 'blocker'}],
        ['another field', {...REWARD_TODO, field: 'quantity'}],
    ])('%s is not', (_label, todo) => {
        expect(isRewardValueTodo(todo)).toBe(false);
    });
});

describe('rewardFillCandidates — the rows a fill may write', () => {
    it('the rows with an open reward_value todo and an empty value, in the grid order', () => {
        const ops = [op('a', {asset_id: 41, date: '2024-03-04'}), op('b', {}, [DESCRIPTION_TODO]), op('c', {asset_id: null, date: '2024-03-05'}), op('d', {}, null), op('e', {asset_id: 43, date: '2024-03-06'}, [DESCRIPTION_TODO, REWARD_TODO])];

        expect(rewardFillCandidates(ops)).toEqual([
            {tempId: 'a', assetId: 41, date: '2024-03-04'},
            {tempId: 'c', assetId: null, date: '2024-03-05'},
            {tempId: 'e', assetId: 43, date: '2024-03-06'},
        ]);
    });

    it.each([
        ['a value written by hand', {cost_basis_override: {code: 'EUR', amount: '12.5'}}],
        ['a value of 0 written by hand (a gift)', {cost_basis_override: {code: 'EUR', amount: '0'}}],
    ])('%s is never a candidate, its todo notwithstanding', (_label, fields) => {
        expect(rewardFillCandidates([op('a', fields as Partial<Op['fields']>)])).toEqual([]);
    });

    it.each([
        ['no override', {cost_basis_override: null}],
        ['a blank amount', {cost_basis_override: {code: 'EUR', amount: '   '}}],
        ['the Auto sentinel, which is no value', {cost_basis_mode: 'auto', cost_basis_override: {code: 'EUR', amount: '0'}}],
    ])('%s: a candidate', (_label, fields) => {
        expect(rewardFillCandidates([op('a', fields as Partial<Op['fields']>)])).toEqual([{tempId: 'a', assetId: 42, date: '2024-03-04'}]);
    });

    it('a corporate-action blocker on the cost basis is not a reward to fill', () => {
        expect(rewardFillCandidates([op('a', {}, [{field: 'cost_basis_override', severity: 'blocker', reasonCode: 'corporate_action'}])])).toEqual([]);
    });

    it('no rows, no candidates', () => {
        expect(rewardFillCandidates([])).toEqual([]);
    });
});

describe('applyRewardFill — the values written back', () => {
    it('a FILLED row gets its value in Manual, in the price currency, and its todo retires (the key goes)', () => {
        const ops = [op('a', {cost_basis_mode: 'auto', cost_basis_override: {code: 'EUR', amount: '0'}})];

        const {ops: next, counts} = applyRewardFill(ops, [filledAnswer('a', '61.25', 'USD')]);

        expect(counts).toEqual({filled: 1, noPrice: 0, noHistory: 0});
        expect(next[0].fields.cost_basis_mode).toBe('manual');
        expect(next[0].fields.cost_basis_override).toEqual({code: 'USD', amount: '61.25'});
        expect('todos' in next[0], 'the only todo retired: the key is dropped').toBe(false);
        expect(next[0].marker, 'the rest of the row is kept').toBe('row a');
        expect({...next[0].fields, cost_basis_mode: undefined, cost_basis_override: undefined}).toEqual({...ops[0].fields, cost_basis_mode: undefined, cost_basis_override: undefined});
    });

    it('the other todos of a filled row stay, in their order', () => {
        const ops = [op('a', {}, [DESCRIPTION_TODO, REWARD_TODO])];

        const {ops: next} = applyRewardFill(ops, [filledAnswer('a')]);

        expect(next[0].todos).toEqual([DESCRIPTION_TODO]);
    });

    it('NO_PRICE_THAT_DAY and NO_HISTORY rows stay as they were — the same objects — their todo open, and are counted', () => {
        const ops = [op('a'), op('b'), op('c')];

        const {ops: next, counts} = applyRewardFill(ops, [noPrice('a'), noHistory('b'), filledAnswer('c', '7', 'EUR')]);

        expect(counts).toEqual({filled: 1, noPrice: 1, noHistory: 1});
        expect(next[0]).toBe(ops[0]);
        expect(next[1]).toBe(ops[1]);
        expect(next[0].todos).toEqual([REWARD_TODO]);
        expect(next[2].fields.cost_basis_override).toEqual({code: 'EUR', amount: '7'});
    });

    it('rows without an answer are returned as the same objects, in the same order', () => {
        const ops = [op('a'), op('b', {}, [DESCRIPTION_TODO]), op('c')];

        const {ops: next} = applyRewardFill(ops, [filledAnswer('b')]);

        expect(next.map((row) => row.tempId)).toEqual(['a', 'b', 'c']);
        expect(next[0]).toBe(ops[0]);
        expect(next[2]).toBe(ops[2]);
    });

    it('a row that already holds a value is never overwritten, and is not counted as filled', () => {
        const ops = [op('a', {cost_basis_override: {code: 'EUR', amount: '5'}})];

        const {ops: next, counts} = applyRewardFill(ops, [filledAnswer('a', '61.25', 'USD')]);

        expect(next[0]).toBe(ops[0]);
        expect(next[0].fields.cost_basis_override).toEqual({code: 'EUR', amount: '5'});
        expect(counts).toEqual({filled: 0, noPrice: 0, noHistory: 0});
    });

    it('a FILLED answer without a value fills nothing and is counted in none of the three', () => {
        const ops = [op('a')];

        const {ops: next, counts} = applyRewardFill(ops, [{tempId: 'a', status: 'FILLED', value: null}]);

        expect(next[0]).toBe(ops[0]);
        expect(counts).toEqual({filled: 0, noPrice: 0, noHistory: 0});
    });

    it('the input is never changed', () => {
        const ops = deepFreeze([op('a', {}, [DESCRIPTION_TODO, REWARD_TODO]), op('b')]);
        const before = structuredClone(ops);

        const {ops: next} = applyRewardFill(ops, [filledAnswer('a'), noPrice('b')]);

        expect(ops).toEqual(before);
        expect(next[0]).not.toBe(ops[0]);
        expect(next[0].fields).not.toBe(ops[0].fields);
    });

    it('no answers, nothing changes', () => {
        const ops = [op('a')];

        const {ops: next, counts} = applyRewardFill(ops, []);

        expect(next[0]).toBe(ops[0]);
        expect(counts).toEqual({filled: 0, noPrice: 0, noHistory: 0});
    });

    it('a filled row is no candidate any more; a row left without a price still is', () => {
        const ops = [op('a'), op('b')];

        const {ops: next} = applyRewardFill(ops, [filledAnswer('a'), noPrice('b')]);

        expect(rewardFillCandidates(next)).toEqual([{tempId: 'b', assetId: 42, date: '2024-03-04'}]);
    });
});
