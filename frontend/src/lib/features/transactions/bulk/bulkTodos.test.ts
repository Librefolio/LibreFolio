/**
 * The bulk editor's todo auto-clear rule (F1, D6 of the Danske Bank workstream, issue 26).
 *
 * An imported row can carry plugin todos: fields the importer left for the user. The editor
 * retires a todo once its field is answered, and it does so in two places of
 * `TransactionBulkModal.svelte` (the single-row patch and the paired-row patch). Both filters
 * move into one pure helper, `remainingTodos(todos, fields)` in `bulkTodos.ts`, with the rule
 * pinned here:
 *
 *   - a todo stays only while its field is empty: `null` or `''`;
 *   - EXCEPT a todo on `cost_basis_override`, which is also answered when the row is applied with
 *     `cost_basis_mode === 'auto'` — whether the mode is the default or a choice: Auto (WAC) is an
 *     answer, the cost basis is computed. Developer, D6: "se già lo apre è sufficiente direi".
 *
 * Shapes. The todo is the editor's `ImportTodo` (`field`, `severity`, `reasonCode`, `message`, and
 * optionally `evidence`, `context`); the fields are the editor's draft fields, plain objects here.
 * The helper returns the todos that remain, as a new array, in their order; an empty list when
 * none does (the editor drops the key itself).
 *
 * The module is loaded inside each test, through `remaining()`: while it — or its export — does
 * not exist, every test fails on its own with "not implemented yet", instead of the whole file
 * failing at collection.
 *
 * Plan: `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md`, F.0 (F1 · D6).
 */
import {describe, expect, it} from 'vitest';

// ---------------------------------------------------------------------------
// The pinned shapes
// ---------------------------------------------------------------------------

interface TodoLike {
    field: string;
    severity: 'blocker' | 'warning';
    reasonCode: string;
    message: string;
    evidence?: unknown[];
    context?: Record<string, unknown>;
}

interface DraftFieldsLike {
    broker_id: number;
    asset_id: number | null;
    type: string;
    date: string;
    quantity: string;
    cash: {code: string; amount: string} | null;
    tags: string[];
    description: string;
    asset_event_id: number | null;
    cost_basis_override: {code: string; amount: string} | null;
    cost_basis_mode: 'auto' | 'manual' | null;
}

type RemainingTodos = (todos: ReadonlyArray<TodoLike>, fields: DraftFieldsLike) => TodoLike[];

/** The helper, loaded for the test that needs it. */
async function remaining(): Promise<RemainingTodos> {
    let mod: {remainingTodos?: unknown};
    try {
        mod = (await import('./bulkTodos')) as {remainingTodos?: unknown};
    } catch (error) {
        throw new Error(`bulkTodos.ts cannot be loaded — not implemented yet (F1, D6): ${String(error)}`);
    }
    if (typeof mod.remainingTodos !== 'function') throw new Error('bulkTodos.remainingTodos is not implemented yet (F1, D6)');
    return mod.remainingTodos as RemainingTodos;
}

// ---------------------------------------------------------------------------
// Fixtures: invented rows and todos
// ---------------------------------------------------------------------------

/** A BUY draft as the editor holds it once applied: every field set, cost basis per the arguments. */
function fields(overrides: Partial<DraftFieldsLike> = {}): DraftFieldsLike {
    return {
        broker_id: 7,
        asset_id: 41,
        type: 'BUY',
        date: '2024-03-14',
        quantity: '12',
        cash: {code: 'EUR', amount: '345.60'},
        tags: ['import'],
        description: 'Invented purchase',
        asset_event_id: null,
        cost_basis_override: null,
        cost_basis_mode: null,
        ...overrides,
    };
}

function todo(field: string, severity: 'blocker' | 'warning' = 'blocker', reasonCode = `probe_${field}`): TodoLike {
    return {field, severity, reasonCode, message: `Invented todo on ${field}`};
}

const COST_BASIS_TODO = todo('cost_basis_override', 'blocker', 'corporate_action');

// ---------------------------------------------------------------------------
// The general rule: a todo stays while its field is empty
// ---------------------------------------------------------------------------

describe('remainingTodos — a todo stays only while its field is empty', () => {
    it('stays while its field is null', async () => {
        const remainingTodos = await remaining();
        const assetTodo = todo('asset_id');

        expect(remainingTodos([assetTodo], fields({asset_id: null}))).toEqual([assetTodo]);
    });

    it("stays while its field is the empty string ''", async () => {
        const remainingTodos = await remaining();
        const descriptionTodo = todo('description', 'warning');

        expect(remainingTodos([descriptionTodo], fields({description: ''}))).toEqual([descriptionTodo]);
    });

    it('goes once its field holds a value: a number, a string, an object', async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([todo('asset_id')], fields({asset_id: 41})), 'asset_id = 41').toEqual([]);
        expect(remainingTodos([todo('quantity', 'warning')], fields({quantity: '12'})), "quantity = '12'").toEqual([]);
        expect(remainingTodos([todo('cash')], fields({cash: {code: 'EUR', amount: '345.60'}})), 'cash = 345.60 EUR').toEqual([]);
    });

    it('keeps the unanswered todos, in their order, and drops only the answered ones', async () => {
        const remainingTodos = await remaining();
        const answeredAsset = todo('asset_id');
        const openDescription = todo('description', 'warning');
        const answeredQuantity = todo('quantity', 'warning');
        const openCash = todo('cash');

        const kept = remainingTodos([answeredAsset, openDescription, answeredQuantity, openCash], fields({asset_id: 41, description: '', quantity: '12', cash: null}));

        expect(kept).toEqual([openDescription, openCash]);
    });

    it('returns a new list and leaves the one it was given untouched', async () => {
        const remainingTodos = await remaining();
        const answered = todo('asset_id');
        const open = todo('description', 'warning');
        const given = [answered, open];
        const snapshot = JSON.parse(JSON.stringify(given)) as TodoLike[];

        const kept = remainingTodos(given, fields({asset_id: 41, description: ''}));

        expect(kept).toEqual([open]);
        expect(kept, 'a new array, not the one passed in').not.toBe(given);
        expect(given, 'the input list is not mutated').toEqual(snapshot);
    });

    it('no todos, nothing remains', async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([], fields())).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// D6: Auto (WAC) answers the cost basis
// ---------------------------------------------------------------------------

describe('remainingTodos — D6: a cost basis todo is answered by Auto (WAC)', () => {
    it("is answered when the row is applied with cost_basis_mode 'auto' and no override", async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: null, cost_basis_mode: 'auto'}))).toEqual([]);
    });

    it("still waits in 'manual' mode while the override is empty", async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: null, cost_basis_mode: 'manual'}))).toEqual([COST_BASIS_TODO]);
    });

    it('still waits with no mode at all (cost basis not applicable yet) and no override', async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: null, cost_basis_mode: null}))).toEqual([COST_BASIS_TODO]);
    });

    it('is answered, as before, by a manual override', async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: {code: 'EUR', amount: '28.80'}, cost_basis_mode: 'manual'}))).toEqual([]);
    });

    it("the 'auto' exception is the cost basis's alone: an empty field of any other todo still waits", async () => {
        const remainingTodos = await remaining();
        const assetTodo = todo('asset_id');
        const descriptionTodo = todo('description', 'warning');

        const kept = remainingTodos([assetTodo, COST_BASIS_TODO, descriptionTodo], fields({asset_id: null, description: '', cost_basis_override: null, cost_basis_mode: 'auto'}));

        expect(kept).toEqual([assetTodo, descriptionTodo]);
    });
});
