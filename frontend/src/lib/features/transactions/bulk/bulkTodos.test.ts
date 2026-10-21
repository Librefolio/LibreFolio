/**
 * The bulk editor's todo auto-clear rule (F1, D6 of the Danske Bank workstream, issue 26), as J-57 complete revises it
 * for blocking cost todos (Q-J57-1 (c), the developer's decision of 19/10).
 *
 * An imported row can carry plugin todos: fields the importer left for the user. The editor
 * retires a todo once its field is answered, and it does so in two places of
 * `TransactionBulkModal.svelte` (the single-row patch and the paired-row patch). Both filters
 * use one pure helper, `remainingTodos(todos, fields)` in `bulkTodos.ts`, with the rule
 * pinned here:
 *
 *   - a todo stays only while its field is empty: `null` or `''`;
 *   - a BLOCKING todo on `cost_basis_override` (`severity: 'blocker'`) is answered only by a value — Q-J57-1 (c),
 *     19/10: the row is not in Auto (`cost_basis_mode !== 'auto'`) and its override is an object whose `amount` is
 *     non-empty once trimmed, `'0'` included (a gift). Auto is no answer to it: in Auto the form sends its
 *     suggested-currency sentinel `{code, amount: '0'}` as the override (`draftToTxFields`,
 *     `TransactionFormModal.svelte`) and the editor stores it on the row (`applyFormPayload`), so a non-null override
 *     in Auto is that sentinel, never an answer. Today all three cost todos are blockers (gap-fix, the Danske split,
 *     the generic CSV's corporate action);
 *   - any other todo on `cost_basis_override` — a warning (none exists today) or a todo of no severity — keeps D6: it
 *     is also answered when the row is applied with `cost_basis_mode === 'auto'`, whether the mode is the default or a
 *     choice: Auto (WAC) is an answer, the cost basis is computed. Developer, D6: "se già lo apre è sufficiente direi".
 *
 * And `hasBlockingCostTodo(todos)` (new in `bulkTodos.ts`): true when a todo is on `cost_basis_override` with severity
 * `'blocker'`: such a row opens in Manual, its field empty.
 *
 * And `initialCostBasisMode(row, todos)` (Q-J57-5 (a), the developer's decision of 19/10 evening): the mode a row the
 * import hands over starts in — the choice `onImportBatch` (`TransactionBulkModal.svelte`) makes, moved into a pure
 * export. The plugin's mode when it sent one; `null` where the type takes no cost on that side; Manual for a cost the
 * plugin wrote (`'0'` included) or a blocking cost todo; Auto otherwise. The last block pins it; the hand-over itself
 * is the modal's, not unit-tested here.
 *
 * Shapes. The todo is the editor's `ImportTodo` (`field`, `severity`, `reasonCode`, `message`, and
 * optionally `evidence`, `context`); the fields are the editor's draft fields, plain objects here.
 * The helper returns the todos that remain, as a new array, in their order; an empty list when
 * none does (the editor drops the key itself).
 *
 * The module is loaded inside each test, through `remaining()`, `blockingCostTodo()` and `initialMode()`: while it — or
 * an export — does not exist, every test fails on its own with "not implemented yet", instead of the whole file failing
 * at collection.
 *
 * RED and CONTROL (J-57 complete). Each test says which it is, and against which code. The reds of Q-J57-1 (c) were red
 * before cure v1 (applied 19/10) for the reasons their docstrings give — «today» there means the code before cure v1 —
 * and are green on it: Auto, its sentinel or a blank Manual amount answered a blocking cost todo (Auto answered any cost
 * todo; any non-null override counted as a value), and `hasBlockingCostTodo` did not exist. The reds of Q-J57-5 (a), the
 * last block, are red against cure v1: `initialCostBasisMode` does not exist yet. CONTROL: green before cure v1 and
 * after — the general rule, the values that answer a blocker (Manual `'0'`, Manual `'28.80'`), the states that leave it
 * open either way, and D6 for a non-blocking cost todo.
 *
 * Plans: `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md`, F.0 (F1 · D6);
 * `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md`, «J-57 completo — esecuzione».
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

type RemainingTodos = <T extends {field: string; severity?: string}>(todos: ReadonlyArray<T>, fields: DraftFieldsLike) => T[];

type HasBlockingCostTodo = (todos: ReadonlyArray<{field: string; severity?: string}>) => boolean;

/** A row as the hand-over reads it (`onImportBatch`): the plugin's mode and cost, and whether its type takes a cost on its side. */
interface HandedOverRowLike {
    mode: 'auto' | 'manual' | null;
    cost: {code?: string; amount?: string} | null;
    costAllowed: boolean;
}

type InitialCostBasisMode = (row: HandedOverRowLike, todos: ReadonlyArray<{field: string; severity?: string}>) => 'auto' | 'manual' | null;

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

/** The J-57 predicate, loaded for the test that needs it: while the export is missing, each of its tests fails on its own. */
async function blockingCostTodo(): Promise<HasBlockingCostTodo> {
    const mod: unknown = await import('./bulkTodos');
    const helper: unknown = Reflect.get(mod as object, 'hasBlockingCostTodo');
    if (typeof helper !== 'function') throw new Error('bulkTodos.hasBlockingCostTodo is not implemented yet (J-57, Q-J57-1)');
    return helper as HasBlockingCostTodo;
}

/** The Q-J57-5 choice, loaded for the test that needs it: while the export is missing, each of its tests fails on its own. */
async function initialMode(): Promise<InitialCostBasisMode> {
    const mod: unknown = await import('./bulkTodos');
    const helper: unknown = Reflect.get(mod as object, 'initialCostBasisMode');
    if (typeof helper !== 'function') throw new Error('bulkTodos.initialCostBasisMode is not implemented yet (J-57, Q-J57-5)');
    return helper as InitialCostBasisMode;
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

/** The same field, as a warning: none is emitted today; it keeps D6 (Auto answers it). */
const WARNING_COST_TODO = todo('cost_basis_override', 'warning', 'probe_cost_basis_warning');

/** What the form sends as the override in Auto (`draftToTxFields`): its suggested currency, amount '0'. No value: by itself it never answers a todo. */
const AUTO_SENTINEL = {code: 'EUR', amount: '0'};

/** A Manual override of `amount` EUR, as the form sends one and the editor stores it. */
const manualCost = (amount: string): {code: string; amount: string} => ({code: 'EUR', amount});

/** A row handed over by the import, as `initialCostBasisMode` reads it: by default no mode, no cost, a type that takes one. */
function handedOver(overrides: Partial<HandedOverRowLike> = {}): HandedOverRowLike {
    return {mode: null, cost: null, costAllowed: true, ...overrides};
}

/** A cost basis the plugin wrote on the row, `amount` EUR, as the editor reads it off the import (`txCreateItemToPendingOp`). */
const pluginCost = (amount: string): {code: string; amount: string} => ({code: 'EUR', amount});

// ---------------------------------------------------------------------------
// The general rule: a todo stays while its field is empty
// ---------------------------------------------------------------------------

// CONTROL, every test of this block: green today and after J-57 — the general rule does not change.
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
// Q-J57-1 (c): a blocking cost basis todo is answered only by a value
// ---------------------------------------------------------------------------

describe('remainingTodos — Q-J57-1 (c): a blocking cost basis todo is answered only by a value', () => {
    /**
     * RED. Q-J57-1 (c) (the developer's decision of 19/10) supersedes D6 for blocking todos: until then this test pinned
     * the opposite, «is answered when the row is applied with cost_basis_mode 'auto' and no override» — D6 made Auto an
     * answer to any cost todo. A blocker now stays open in Auto: Auto gives no cost it can rest on (an Auto cost with
     * nothing to average is refused, N88), and only a value answers it.
     * Fails today: `[]` instead of the todo — `bulkTodos.ts` line 22 lets Auto answer any cost todo.
     */
    it("stays open when the row is applied with cost_basis_mode 'auto' and no override: Auto no longer answers a blocker", async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: null, cost_basis_mode: 'auto'}))).toEqual([COST_BASIS_TODO]);
    });

    /**
     * RED. In Auto the form sends its suggested-currency sentinel as the override (`draftToTxFields`) and the editor
     * stores it (`applyFormPayload`): a non-null override in Auto is that sentinel, never the user's 0.
     * Fails today: `[]` — Auto answers first, and any non-null override would answer too.
     */
    it("stays open in 'auto' with the form's suggested-currency sentinel {code: 'EUR', amount: '0'}", async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: AUTO_SENTINEL, cost_basis_mode: 'auto'}))).toEqual([COST_BASIS_TODO]);
    });

    /**
     * RED. An override whose amount is empty once trimmed holds no value: '' and blanks.
     * Fails today: `[]` for both — the override is an object, neither `null` nor `''`, so the general rule takes it for a value.
     */
    it("stays open in 'manual' while the override's amount is empty: '' or blanks", async () => {
        const remainingTodos = await remaining();

        expect.soft(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: manualCost(''), cost_basis_mode: 'manual'})), "amount ''").toEqual([COST_BASIS_TODO]);
        expect.soft(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: manualCost('  '), cost_basis_mode: 'manual'})), "amount '  '").toEqual([COST_BASIS_TODO]);
    });

    /**
     * RED. The blocker keeps its place among the other todos: the answered ones go, the open ones stay, in their order, in
     * a new list; the one given is untouched.
     * Fails today: `[openDescription]` — the blocker leaves with the answered asset todo (Auto answers it).
     */
    it('keeps an open blocking cost todo in its place among the other todos, in a new list, the given one untouched', async () => {
        const remainingTodos = await remaining();
        const answeredAsset = todo('asset_id');
        const openDescription = todo('description', 'warning');
        const given = [answeredAsset, COST_BASIS_TODO, openDescription];
        const snapshot = JSON.parse(JSON.stringify(given)) as TodoLike[];

        const kept = remainingTodos(given, fields({asset_id: 41, description: '', cost_basis_override: AUTO_SENTINEL, cost_basis_mode: 'auto'}));

        expect(kept).toEqual([COST_BASIS_TODO, openDescription]);
        expect(kept, 'a new array, not the one passed in').not.toBe(given);
        expect(given, 'the input list is not mutated').toEqual(snapshot);
    });

    /**
     * CONTROL — the gift case. Q-J57-1 (c): «Manuale e 0 compreso»: a Manual '0' is a value.
     * Green today (any non-null override answers) and after (not Auto, and '0' is non-empty once trimmed).
     */
    it("is answered in 'manual' by an amount of '0': a gift's cost is a value", async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: manualCost('0'), cost_basis_mode: 'manual'}))).toEqual([]);
    });

    /** CONTROL — green today and after: a Manual amount answers it, as before. */
    it('is answered, as before, by a manual override', async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: {code: 'EUR', amount: '28.80'}, cost_basis_mode: 'manual'}))).toEqual([]);
    });

    /**
     * CONTROL — green today and after: only Auto is no answer (`cost_basis_mode !== 'auto'`); with no mode, an override
     * holding an amount answers it like a Manual one.
     */
    it('is answered with no mode by an override holding an amount', async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: manualCost('12.50'), cost_basis_mode: null}))).toEqual([]);
    });

    /** CONTROL — green today and after: no override, no answer. */
    it("still waits in 'manual' mode while the override is empty", async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: null, cost_basis_mode: 'manual'}))).toEqual([COST_BASIS_TODO]);
    });

    /** CONTROL — green today and after. */
    it('still waits with no mode at all (cost basis not applicable yet) and no override', async () => {
        const remainingTodos = await remaining();

        expect(remainingTodos([COST_BASIS_TODO], fields({cost_basis_override: null, cost_basis_mode: null}))).toEqual([COST_BASIS_TODO]);
    });
});

// ---------------------------------------------------------------------------
// D6, kept for a cost basis todo that does not block: Auto (WAC) answers it
// ---------------------------------------------------------------------------

describe('remainingTodos — D6, kept for a non-blocking cost basis todo: Auto (WAC) answers it', () => {
    /** CONTROL — green today (Auto answers any cost todo) and after (Q-J57-1 (c) leaves a non-blocking cost todo to D6). */
    it("a warning cost todo is answered in 'auto', with no override and with the form's sentinel", async () => {
        const remainingTodos = await remaining();

        expect.soft(remainingTodos([WARNING_COST_TODO], fields({cost_basis_override: null, cost_basis_mode: 'auto'})), 'no override').toEqual([]);
        expect.soft(remainingTodos([WARNING_COST_TODO], fields({cost_basis_override: AUTO_SENTINEL, cost_basis_mode: 'auto'})), "the sentinel {code: 'EUR', amount: '0'}").toEqual([]);
    });

    /**
     * CONTROL — green today and after: only the severity 'blocker' blocks. A cost todo of no severity, or of a severity
     * the editor does not know, keeps D6.
     */
    it("a cost todo of no severity, or of another severity, is answered in 'auto'", async () => {
        const remainingTodos = await remaining();
        const noSeverity = {field: 'cost_basis_override', reasonCode: 'probe_no_severity', message: 'Invented todo without a severity'};
        const otherSeverity = {field: 'cost_basis_override', severity: 'info', reasonCode: 'probe_info', message: 'Invented todo of another severity'};

        expect.soft(remainingTodos([noSeverity], fields({cost_basis_override: null, cost_basis_mode: 'auto'})), 'no severity').toEqual([]);
        expect.soft(remainingTodos([otherSeverity], fields({cost_basis_override: null, cost_basis_mode: 'auto'})), "severity 'info'").toEqual([]);
    });

    /** CONTROL — green today and after: outside Auto a warning cost todo follows the general rule. */
    it("a warning cost todo still waits in 'manual' while the override is null, and goes with a manual amount", async () => {
        const remainingTodos = await remaining();

        expect.soft(remainingTodos([WARNING_COST_TODO], fields({cost_basis_override: null, cost_basis_mode: 'manual'})), 'no override').toEqual([WARNING_COST_TODO]);
        expect.soft(remainingTodos([WARNING_COST_TODO], fields({cost_basis_override: manualCost('28.80'), cost_basis_mode: 'manual'})), '28.80 EUR').toEqual([]);
    });

    /**
     * CONTROL — green today and after. Rewritten for J-57: it used the blocking `COST_BASIS_TODO`, which Q-J57-1 (c) keeps
     * open in Auto; with a warning cost todo it keeps its subject.
     */
    it("the 'auto' exception is the cost basis's alone: an empty field of any other todo still waits", async () => {
        const remainingTodos = await remaining();
        const assetTodo = todo('asset_id');
        const descriptionTodo = todo('description', 'warning');

        const kept = remainingTodos([assetTodo, WARNING_COST_TODO, descriptionTodo], fields({asset_id: null, description: '', cost_basis_override: null, cost_basis_mode: 'auto'}));

        expect(kept).toEqual([assetTodo, descriptionTodo]);
    });
});

// ---------------------------------------------------------------------------
// hasBlockingCostTodo: a row the editor opens in Manual with an empty field
// ---------------------------------------------------------------------------

// RED before cure v1, every test of this block: the export did not exist, so each failed with «bulkTodos.hasBlockingCostTodo
// is not implemented yet (J-57, Q-J57-1)»; green on cure v1.
describe('hasBlockingCostTodo — Q-J57-1 (c): a blocking todo on cost_basis_override', () => {
    it('true for a blocker on cost_basis_override', async () => {
        const hasBlockingCostTodo = await blockingCostTodo();

        expect(hasBlockingCostTodo([COST_BASIS_TODO])).toBe(true);
    });

    it('false for a cost todo that does not block: a warning, or a todo of no severity', async () => {
        const hasBlockingCostTodo = await blockingCostTodo();

        expect.soft(hasBlockingCostTodo([WARNING_COST_TODO]), 'a warning').toBe(false);
        expect.soft(hasBlockingCostTodo([{field: 'cost_basis_override'}]), 'no severity').toBe(false);
    });

    it('false for blockers on other fields', async () => {
        const hasBlockingCostTodo = await blockingCostTodo();

        expect(hasBlockingCostTodo([todo('asset_id', 'blocker'), todo('cash', 'blocker')])).toBe(false);
    });

    it('false for an empty list', async () => {
        const hasBlockingCostTodo = await blockingCostTodo();

        expect(hasBlockingCostTodo([])).toBe(false);
    });

    it('true for a mixed list holding a blocker on the cost basis, wherever it sits', async () => {
        const hasBlockingCostTodo = await blockingCostTodo();

        expect.soft(hasBlockingCostTodo([WARNING_COST_TODO, todo('asset_id', 'blocker'), COST_BASIS_TODO]), 'last of three').toBe(true);
        expect.soft(hasBlockingCostTodo([COST_BASIS_TODO, todo('description', 'warning')]), 'first of two').toBe(true);
    });
});

// ---------------------------------------------------------------------------
// initialCostBasisMode: the mode a row handed over by the import starts in (Q-J57-5 (a))
// ---------------------------------------------------------------------------

/**
 * Q-J57-5 (a), the developer's decision of 19/10 evening: «se il plugin non è in grado di mettere un numero esplicito,
 * allora deve andare in auto, se poi quel numero esplicito è 0, va bene, ma lasciarlo non selezionato direi che è un
 * bug». On cure v1 `onImportBatch` keeps the plugin's mode, usually none, and gives Manual only to a row with a blocking
 * cost todo: a row the plugin leaves without a mode reaches the hand-over's validation without one, refused with
 * `costBasisRequired`, and takes Auto only once the user applies its form (`applyFormPayload`). The choice moves into a
 * pure export of `bulkTodos.ts`, `initialCostBasisMode(row, todos)`, which answers in this order:
 *
 *   1. the plugin's mode, when it sent one (`mode !== null`), as it is;
 *   2. `costAllowed === false` → `null`: the type takes no cost on that side;
 *   3. a cost the plugin wrote — an `amount` non-empty once trimmed, `'0'` included (a gift) → `'manual'`;
 *   4. a blocking todo on `cost_basis_override` (`hasBlockingCostTodo`) → `'manual'`: its form opens in Manual, the
 *      field empty (Q-J57-1 (c));
 *   5. otherwise → `'auto'`.
 *
 * RED, every test of this block: against cure v1 the export does not exist, so each fails with
 * «bulkTodos.initialCostBasisMode is not implemented yet (J-57, Q-J57-5)»; once the cure lands each passes.
 *
 * Fixtures. `handedOver()` is a row with no mode, no cost and a type that takes one, as the hand-over reads it; each case
 * changes only what it names. The todos are the invented ones above.
 */
describe('initialCostBasisMode — Q-J57-5 (a): the mode a row handed over by the import starts in', () => {
    it('no mode, a type that takes a cost, no cost, no todo: Auto — the row is never left without a mode (the core of Q-J57-5 (a))', async () => {
        const initialCostBasisMode = await initialMode();

        expect(initialCostBasisMode(handedOver(), [])).toBe('auto');
    });

    it('a blocking cost todo: Manual, its field empty (Q-J57-1 (c)) — alone, or among other todos', async () => {
        const initialCostBasisMode = await initialMode();

        expect.soft(initialCostBasisMode(handedOver(), [COST_BASIS_TODO]), 'alone').toBe('manual');
        expect.soft(initialCostBasisMode(handedOver(), [todo('description', 'warning'), todo('asset_id', 'blocker'), COST_BASIS_TODO]), 'last of three').toBe('manual');
    });

    it("a cost of '0' the plugin wrote: Manual — a gift's cost is a value", async () => {
        const initialCostBasisMode = await initialMode();

        expect(initialCostBasisMode(handedOver({cost: pluginCost('0')}), [])).toBe('manual');
    });

    it("a cost of '12.5' the plugin wrote: Manual", async () => {
        const initialCostBasisMode = await initialMode();

        expect(initialCostBasisMode(handedOver({cost: pluginCost('12.5')}), [])).toBe('manual');
    });

    it("an amount empty once trimmed is no cost: Auto — blanks, '', or no amount at all", async () => {
        const initialCostBasisMode = await initialMode();

        expect.soft(initialCostBasisMode(handedOver({cost: pluginCost('   ')}), []), "amount '   '").toBe('auto');
        expect.soft(initialCostBasisMode(handedOver({cost: pluginCost('')}), []), "amount ''").toBe('auto');
        expect.soft(initialCostBasisMode(handedOver({cost: {code: 'EUR'}}), []), 'no amount').toBe('auto');
    });

    it('a cost todo that does not block leaves the row to Auto: a warning, or a todo of no severity', async () => {
        const initialCostBasisMode = await initialMode();

        expect.soft(initialCostBasisMode(handedOver(), [WARNING_COST_TODO]), 'a warning').toBe('auto');
        expect.soft(initialCostBasisMode(handedOver(), [{field: 'cost_basis_override'}]), 'no severity').toBe('auto');
    });

    it('a blocker on another field does not choose the mode: Auto', async () => {
        const initialCostBasisMode = await initialMode();

        expect(initialCostBasisMode(handedOver(), [todo('asset_id', 'blocker'), todo('cash', 'blocker')])).toBe('auto');
    });

    it('a type that takes no cost on its side: null — even with a blocking cost todo, or a cost the plugin wrote', async () => {
        const initialCostBasisMode = await initialMode();
        const takesNoCost = {costAllowed: false};

        expect.soft(initialCostBasisMode(handedOver(takesNoCost), []), 'nothing else').toBeNull();
        expect.soft(initialCostBasisMode(handedOver(takesNoCost), [COST_BASIS_TODO]), 'a blocking cost todo').toBeNull();
        expect.soft(initialCostBasisMode(handedOver({...takesNoCost, cost: pluginCost('12.5')}), []), "a cost of '12.5'").toBeNull();
        expect.soft(initialCostBasisMode(handedOver({...takesNoCost, cost: pluginCost('0')}), [COST_BASIS_TODO]), "a cost of '0' and a blocking cost todo").toBeNull();
    });

    it("the plugin's explicit mode wins: Auto stays Auto beside a blocking cost todo or its currency hint, Manual stays Manual where the rest would give Auto", async () => {
        const initialCostBasisMode = await initialMode();

        expect.soft(initialCostBasisMode(handedOver({mode: 'auto'}), [COST_BASIS_TODO]), "'auto' and a blocking cost todo").toBe('auto');
        // In Auto a cost of 0 is the currency hint the form itself sends (`draftToTxFields`), never a gift.
        expect.soft(initialCostBasisMode(handedOver({mode: 'auto', cost: pluginCost('0')}), []), "'auto' and the currency hint {code: 'EUR', amount: '0'}").toBe('auto');
        expect.soft(initialCostBasisMode(handedOver({mode: 'manual'}), []), "'manual', no cost, no todo").toBe('manual');
    });

    it("the plugin's mode comes first, even where the type takes no cost: kept as it is (step 1 before step 2)", async () => {
        const initialCostBasisMode = await initialMode();

        expect.soft(initialCostBasisMode(handedOver({mode: 'manual', costAllowed: false}), []), "'manual'").toBe('manual');
        expect.soft(initialCostBasisMode(handedOver({mode: 'auto', costAllowed: false}), []), "'auto'").toBe('auto');
    });

    it('reads its inputs without changing them, and answers the same twice', async () => {
        const initialCostBasisMode = await initialMode();
        // No blocking cost todo: the answer rests on the cost, ' 0 ', which is '0' once trimmed.
        const row = handedOver({cost: pluginCost(' 0 ')});
        const todos = [WARNING_COST_TODO, todo('asset_id', 'blocker')];
        const rowBefore = structuredClone(row);
        const todosBefore = structuredClone(todos);

        const first = initialCostBasisMode(row, todos);
        const second = initialCostBasisMode(row, todos);

        expect(first, "a cost of ' 0 ': '0' once trimmed, a value").toBe('manual');
        expect(second, 'the same answer twice').toBe(first);
        expect(row, 'the row: its mode still none, its cost and amount as given, untrimmed').toEqual(rowBefore);
        expect(todos, 'the todos, in their order').toEqual(todosBefore);
    });
});
