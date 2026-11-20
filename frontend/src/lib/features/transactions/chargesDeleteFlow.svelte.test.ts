/**
 * chargesDeleteFlow — the delete flow with linked charges, shared by the Transactions page and the broker's Transactions
 * tab (project 66, lot F7-d). Contract: `66-F7-contract.md` §20.1, §20.2 (corrected by §21.5, §21.7).
 *
 * Today `startDelete`, the panel's state, its counts and the choice live in `routes/(app)/transactions/+page.svelte`.
 * F7-d moves them into `T/chargesDeleteFlow.svelte.ts`, so the broker's tab asks the same question before the Bulk:
 *
 *   createChargesDeleteFlow({openBulk, onReadFailed}) → {panel, counts, start(rows), choose(choice), cancel()}
 *
 *   - `start(rows)`: no row with `charges_count > 0` → `openBulk({action: 'delete', txIds})` at once, nothing read.
 *     Otherwise the charges are read (`query_transactions_api_v1_transactions_get` with `parent_ids`, as the page does
 *     today) and added to the store; a plan (`deletePlan`) with parents whose charges are not all selected sets `panel`
 *     and waits for the choice; an empty plan opens the Bulk at once. A failed read calls `onReadFailed` and opens
 *     nothing.
 *   - `counts`: the page's numbers, from the same intent the Bulk receives (`deleteIntent`): keep = the charges kept,
 *     all = every row «Delete all» deletes.
 *   - `choose(choice)`: the panel closes, `openBulk({action: 'delete', ...deleteIntent(ids, plan, choice)})`, which
 *     carries `chargeIds` (§20.2).
 *   - `cancel()`: the panel closes, nothing opens.
 *
 * What `panel` holds is the implementer's (the page's today is `{ids, plan}`): these cases only read whether it is set.
 *
 * RED until `./chargesDeleteFlow.svelte` exists: the import below fails and the whole file with it.
 *
 * The network is stubbed at its edge (`zodiosApi`); the store is the real one, emptied after each case.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {zodiosApi} from '$lib/api';
import {txStoreGet, txStoreInvalidate} from './txStore.svelte';
import type {TXReadItem} from './types';
import type {WorkspaceIntent} from './bulk/TransactionBulkModal.svelte';
import {createChargesDeleteFlow} from './chargesDeleteFlow.svelte';

vi.mock('$lib/api', () => ({
    zodiosApi: {query_transactions_api_v1_transactions_get: vi.fn()},
    ApiError: class ApiError extends Error {},
    axiosInstance: {},
}));

// ---------------------------------------------------------------------------
// Fixtures: ids in the 930000s, so none can be mistaken for a count or an index
// ---------------------------------------------------------------------------

function tx(id: number, type: string, over: Partial<TXReadItem> = {}): TXReadItem {
    return {
        id,
        broker_id: 77,
        asset_id: 101,
        type,
        date: '2026-10-01',
        quantity: type === 'BUY' ? '1' : '0',
        cash: {code: 'EUR', amount: '-10'},
        related_transaction_id: null,
        partner_broker_id: null,
        parent_transaction_id: null,
        charges_count: 0,
        tags: [],
        description: `F7d flow ${type} ${id}`,
        cost_basis_override: null,
        asset_event_id: null,
        ...over,
    };
}

const BUY = tx(930_001, 'BUY', {charges_count: 2});
const FEE = tx(930_002, 'FEE', {parent_transaction_id: BUY.id});
const TAX = tx(930_003, 'TAX', {parent_transaction_id: BUY.id});
const DEP = tx(930_011, 'DEPOSIT', {asset_id: null, cash: {code: 'EUR', amount: '100'}});

type DeleteIntent = Extract<WorkspaceIntent, {action: 'delete'}> & {unlinkIds?: number[]; chargeIds?: number[]};
type ReadArgs = {queries?: {parent_ids?: number[]}} | undefined;

const readMock = () => vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get);
const sorted = (xs: readonly number[] | undefined) => [...(xs ?? [])].sort((a, b) => a - b);

/** The charges read answers by `parent_ids`, from these rows. */
function answerRead(rows: TXReadItem[]): void {
    readMock().mockImplementation((async (args: ReadArgs) => rows.filter((row) => row.parent_transaction_id != null && (args?.queries?.parent_ids ?? []).includes(row.parent_transaction_id))) as never);
}

function makeFlow() {
    const openBulk = vi.fn<(intent: WorkspaceIntent) => void>();
    const onReadFailed = vi.fn();
    const flow = createChargesDeleteFlow({openBulk, onReadFailed});
    return {flow, openBulk, onReadFailed};
}

/** The one intent handed to `openBulk`. */
function onlyIntent(openBulk: ReturnType<typeof makeFlow>['openBulk']): DeleteIntent {
    expect(openBulk, 'openBulk called once').toHaveBeenCalledTimes(1);
    const intent = openBulk.mock.calls[0][0] as DeleteIntent;
    expect(intent.action).toBe('delete');
    return intent;
}

beforeEach(() => {
    readMock().mockReset();
});

afterEach(() => {
    txStoreInvalidate();
});

describe('createChargesDeleteFlow — start', () => {
    it('no row with charges: the Bulk opens at once on the delete, nothing is read, no panel', async () => {
        const {flow, openBulk} = makeFlow();

        await flow.start([DEP, {...BUY, charges_count: 0}]);

        const intent = onlyIntent(openBulk);
        expect(sorted(intent.txIds)).toEqual(sorted([DEP.id, BUY.id]));
        expect(intent.unlinkIds ?? [], 'nothing to unlink').toEqual([]);
        expect(intent.chargeIds ?? [], 'no charge chosen with a parent').toEqual([]);
        expect(readMock(), 'nothing to read').not.toHaveBeenCalled();
        expect(flow.panel ?? null).toBeNull();
    });

    it('a parent whose charges are not all selected: the charges are read by parent_ids, the panel opens with the page’s counts, the Bulk waits', async () => {
        answerRead([FEE, TAX]);
        const {flow, openBulk} = makeFlow();

        await flow.start([BUY, DEP]);

        expect(readMock()).toHaveBeenCalledTimes(1);
        expect((readMock().mock.calls[0][0] as ReadArgs)?.queries?.parent_ids, 'the read names the parent').toEqual([BUY.id]);
        expect(flow.panel ?? null, 'the panel is open').not.toBeNull();
        expect(flow.counts, 'keep: the two charges; all: BUY + DEP + the two charges').toEqual({keep: 2, all: 4});
        expect(openBulk, 'nothing opens before the choice').not.toHaveBeenCalled();
    });

    it('the charges read are added to the store, so the Bulk resolves them even when the list does not show them', async () => {
        answerRead([FEE, TAX]);
        const {flow} = makeFlow();

        await flow.start([BUY]);

        expect(txStoreGet(FEE.id)?.parent_transaction_id).toBe(BUY.id);
        expect(txStoreGet(TAX.id)?.parent_transaction_id).toBe(BUY.id);
    });

    it('a parent selected with all its charges: no panel, the Bulk opens at once on the selection', async () => {
        answerRead([FEE, TAX]);
        const {flow, openBulk} = makeFlow();

        await flow.start([BUY, FEE, TAX]);

        const intent = onlyIntent(openBulk);
        expect(sorted(intent.txIds)).toEqual(sorted([BUY.id, FEE.id, TAX.id]));
        expect(flow.panel ?? null).toBeNull();
    });

    it('a failed read: onReadFailed, no panel, no Bulk', async () => {
        readMock().mockRejectedValue(new Error('network down'));
        const {flow, openBulk, onReadFailed} = makeFlow();

        await flow.start([BUY]);

        expect(onReadFailed).toHaveBeenCalledTimes(1);
        expect(openBulk).not.toHaveBeenCalled();
        expect(flow.panel ?? null).toBeNull();
    });
});

describe('createChargesDeleteFlow — the choice', () => {
    async function opened() {
        answerRead([FEE, TAX]);
        const made = makeFlow();
        await made.flow.start([BUY, DEP]);
        expect(made.flow.panel ?? null, 'premise: the panel is open').not.toBeNull();
        return made;
    }

    it('«Delete all»: the panel closes, the Bulk opens deleting the selection and the charges; unlinkIds empty; chargeIds the charges', async () => {
        const {flow, openBulk} = await opened();

        flow.choose('all');

        expect(flow.panel ?? null, 'the panel closed').toBeNull();
        const intent = onlyIntent(openBulk);
        expect(sorted(intent.txIds)).toEqual(sorted([BUY.id, DEP.id, FEE.id, TAX.id]));
        expect(intent.unlinkIds ?? []).toEqual([]);
        expect(sorted(intent.chargeIds), 'the charges chosen with the parent').toEqual(sorted([FEE.id, TAX.id]));
    });

    it('«Keep»: the Bulk opens deleting the selection alone, unlinking the charges; chargeIds the same charges', async () => {
        const {flow, openBulk} = await opened();

        flow.choose('keep');

        expect(flow.panel ?? null).toBeNull();
        const intent = onlyIntent(openBulk);
        expect(sorted(intent.txIds)).toEqual(sorted([BUY.id, DEP.id]));
        expect(sorted(intent.unlinkIds)).toEqual(sorted([FEE.id, TAX.id]));
        expect(sorted(intent.chargeIds)).toEqual(sorted([FEE.id, TAX.id]));
    });

    it('«Cancel»: the panel closes and nothing opens; a choice after it does nothing', async () => {
        const {flow, openBulk} = await opened();

        flow.cancel();
        flow.choose('all');

        expect(flow.panel ?? null).toBeNull();
        expect(openBulk).not.toHaveBeenCalled();
    });
});
