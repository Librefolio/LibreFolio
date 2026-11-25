// @vitest-environment jsdom
//
// The docblock above is load-bearing: under the default `node` environment a `.svelte.ts` `$derived` returns a stale
// value and `$effect` never runs (`$test/runes.svelte`). `assertEffectsRun()` in `beforeAll` fails the file loudly if
// the docblock is ever lost.
/**
 * chargesUnlinkFlow — «Unlink the charges» from a table's selection bar, shared by the Transactions page and the broker's
 * Transactions tab (project 66, TL-9), sibling of `chargesLinkFlow`. The contract:
 *
 *   createChargesUnlinkFlow({onUnlinked, issueContext?}) → {open, charges, unlinking, action, confirm(), cancel()}
 *
 *   - `action`: `unlink-charges`. It takes the rows `isUnlinkable` says (a saved parent, a broker the user edits:
 *     `canEditBroker`), whatever the rest of the selection; with none it is hidden; it is never off (no `blocked`). The
 *     predicate's own cases are `chargeLinkRules.test.ts`'s.
 *   - `action.onClick(rows)`: the unlinkable ones of `rows` are fixed, and the panel opens on them.
 *   - `confirm()`: one commit (`unlinkCommit`); committed → closed, `tx.charges.unlinked` notified with no toast, then
 *     `onUnlinked` once; refused → `toasts.error` with the reasons (named through `issueContext`, or the broker/asset
 *     stores), still open. While it saves, a second `confirm()` sends nothing and `cancel()` does not close.
 *   - The type rules are never asked for: the broker page opens without them (its cold path, brokers-detail 6b).
 *
 * The bar is `resolveSelectionAction`, as the tables use it. The network is stubbed at its edges: GET /transactions/types
 * (`zodiosApi`, and `ensureTypesLoaded` in front of it) and the commit (`commitTransactions`). The module is loaded by a
 * glob, so while it is missing each case fails by name and the file still collects.
 */
import {beforeAll, beforeEach, describe, expect, it, onTestFinished, vi} from 'vitest';
import {flushSync} from 'svelte';
import {zodiosApi} from '$lib/api';
import {setupI18n} from '$test/component';
import {assertEffectsRun, effectRoot, recordReads} from '$test/runes.svelte';
import {resolveSelectionAction} from '$lib/components/table/selectionActions';
import type {BulkAction} from '$lib/components/table/types';
import {commitTransactions, type CommitResult} from './txCommitApi';
import {notify} from '$lib/stores/app/notify.svelte';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {getAllAssets} from '$lib/stores/reference/assetStore';
import {canEditBroker, getAllBrokers} from '$lib/stores/reference/brokerStore';
import {ensureTypesLoaded} from './transactionTypeStore';
import type {ResolverContext} from './resolveValidationMessage';
import type {TXReadItem} from './types';

const {EDITABLE_BROKER, READ_ONLY_BROKER} = vi.hoisted(() => ({EDITABLE_BROKER: 78, READ_ONLY_BROKER: 79}));

vi.mock('$lib/api', () => ({
    zodiosApi: {get_transaction_types_api_v1_transactions_types_get: vi.fn(async () => ({transaction_types: [], event_types: []}))},
    ApiError: class ApiError extends Error {},
    axiosInstance: {},
}));
vi.mock('./transactionTypeStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./transactionTypeStore')>()),
    ensureTypesLoaded: vi.fn(async () => {}),
}));
vi.mock('./txCommitApi', () => ({commitTransactions: vi.fn()}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn(), show: vi.fn()},
}));
// One broker the user edits, one read-only; the broker list is what the default refusal context names.
vi.mock('$lib/stores/reference/brokerStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/brokerStore')>()),
    canEditBroker: vi.fn((id: number) => id === EDITABLE_BROKER),
    getAllBrokers: vi.fn(() => [{id: EDITABLE_BROKER, name: 'TL9 Broker'}]),
}));
vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/assetStore')>()),
    getAllAssets: vi.fn(() => [{id: 101, display_name: 'TL9 Asset'}]),
}));

// ---------------------------------------------------------------------------
// The flow under test
// ---------------------------------------------------------------------------

interface UnlinkFlow {
    readonly open: boolean;
    readonly charges: TXReadItem[];
    readonly unlinking: boolean;
    readonly action: BulkAction<TXReadItem>;
    confirm(): Promise<void>;
    cancel(): void;
}
interface UnlinkFlowDeps {
    onUnlinked: () => Promise<void>;
    issueContext?: () => ResolverContext;
}
type UnlinkFlowModule = {createChargesUnlinkFlow?: (deps: UnlinkFlowDeps) => UnlinkFlow};

const MODULES = import.meta.glob<UnlinkFlowModule>('./chargesUnlinkFlow.svelte.ts');

async function createFlow(deps: UnlinkFlowDeps): Promise<() => UnlinkFlow> {
    const load = MODULES['./chargesUnlinkFlow.svelte.ts'];
    if (!load) throw new Error('chargesUnlinkFlow.svelte.ts does not exist (66 TL-9)');
    const create = (await load()).createChargesUnlinkFlow;
    if (!create) throw new Error('chargesUnlinkFlow.svelte.ts exports no createChargesUnlinkFlow (66 TL-9)');
    return () => create(deps);
}

// ---------------------------------------------------------------------------
// Fixtures: ids in the 950000s, so none can be mistaken for a count or an index
// ---------------------------------------------------------------------------

function tx(id: number, type: string, over: Partial<TXReadItem> = {}): TXReadItem {
    return {
        id,
        broker_id: EDITABLE_BROKER,
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
        description: `TL9 unlink ${type} ${id}`,
        cost_basis_override: null,
        asset_event_id: null,
        ...over,
    };
}

const BUY = tx(950_001, 'BUY', {charges_count: 2});
const FEE = tx(950_002, 'FEE', {parent_transaction_id: BUY.id});
const TAX = tx(950_003, 'TAX', {parent_transaction_id: BUY.id});
const FREE_FEE = tx(950_004, 'FEE');
const READ_ONLY_FEE = tx(950_005, 'FEE', {broker_id: READ_ONLY_BROKER, parent_transaction_id: 950_099});
const DEPOSIT = tx(950_006, 'DEPOSIT', {asset_id: null});

const commitMock = () => vi.mocked(commitTransactions);
const typesRequest = () => vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get);
const COMMITTED: CommitResult = {committed: true, issues: [], results: [], rawResponse: {}};
const REFUSED: CommitResult = {committed: false, issues: [{error: 'unlink refused', code: 'chargeOtherBroker', ref_id: TAX.id}], rawResponse: {}};

const ids = (rows: readonly TXReadItem[]): number[] => rows.map((r) => r.id);

/** A flow built as a page builds it, inside an effect root. `onUnlinked` records what the flow showed when it ran. */
async function mount(issueContext?: () => ResolverContext) {
    const seen: Array<{open: boolean; notified: number}> = [];
    const onUnlinked = vi.fn<() => Promise<void>>(async () => {
        seen.push({open: root.value.open, notified: vi.mocked(notify).mock.calls.length});
    });
    const create = await createFlow({onUnlinked, ...(issueContext ? {issueContext} : {})});
    const root = effectRoot(create);
    flushSync();
    onTestFinished(() => root.stop());
    return {flow: root.value, onUnlinked, seen};
}

/** The rows and the number the bar shows for this selection, or `hidden`. */
function bar(flow: UnlinkFlow, selected: TXReadItem[]) {
    const item = resolveSelectionAction(flow.action, selected);
    return item.state === 'hidden' ? {state: item.state} : {state: item.state, count: item.count, rows: ids(item.rows)};
}

/** Click the bar's button for this selection, as the bar does: on the rows the action takes. */
function clickBar(flow: UnlinkFlow, selected: TXReadItem[]): void {
    const item = resolveSelectionAction(flow.action, selected);
    if (item.state !== 'on') throw new Error(`premise: the bar offers «Unlink» for ${ids(selected).join(', ')}, it is ${item.state}`);
    void item.action.onClick(item.rows);
    flushSync();
}

/** A flow with its panel open on this selection. */
async function opened(selected: TXReadItem[] = [BUY, TAX], issueContext?: () => ResolverContext) {
    const made = await mount(issueContext);
    clickBar(made.flow, selected);
    expect(made.flow.open, 'premise: the panel is open').toBe(true);
    return made;
}

/** A commit held until `land`. */
function heldCommit(): {land: (result: CommitResult) => void} {
    let resolve: ((result: CommitResult) => void) | undefined;
    commitMock().mockImplementation(() => new Promise<CommitResult>((r) => (resolve = r)));
    return {
        land: (result) => {
            if (!resolve) throw new Error('no commit was sent: there is nothing to land');
            resolve(result);
        },
    };
}

beforeAll(async () => {
    assertEffectsRun();
    await setupI18n('en');
});

beforeEach(() => {
    commitMock().mockReset();
    vi.mocked(notify).mockClear();
    for (const toast of Object.values(toasts)) if (vi.isMockFunction(toast)) toast.mockClear();
    vi.mocked(getAllBrokers).mockClear();
    vi.mocked(getAllAssets).mockClear();
    vi.mocked(canEditBroker).mockClear();
    vi.mocked(ensureTypesLoaded).mockClear();
    typesRequest().mockClear();
});

// ---------------------------------------------------------------------------
// The bar
// ---------------------------------------------------------------------------

describe('createChargesUnlinkFlow — the action in the bar', () => {
    it('is unlink-charges, and never off: it has no `blocked`', async () => {
        const {flow} = await mount();

        expect(flow.action.id).toBe('unlink-charges');
        expect(flow.action.blocked).toBeUndefined();
    });

    it('one linked charge is enough: shown with the number 1', async () => {
        const {flow} = await mount();

        expect(bar(flow, [TAX])).toEqual({state: 'on', count: 1, rows: [TAX.id]});
    });

    it('a mixed selection: it counts and takes the linked charges only, in selection order', async () => {
        const {flow} = await mount();

        expect(bar(flow, [DEPOSIT, TAX, BUY, FREE_FEE, FEE])).toEqual({state: 'on', count: 2, rows: [TAX.id, FEE.id]});
    });

    it('a ticked parent drags none of its charges', async () => {
        const {flow} = await mount();

        // The barrier: with one of its charges ticked too, the action is there — for that one.
        expect(bar(flow, [BUY, TAX])).toEqual({state: 'on', count: 1, rows: [TAX.id]});
        expect(bar(flow, [BUY])).toEqual({state: 'hidden'});
    });

    it('nothing to unlink (a free FEE, a parent, a DEPOSIT): hidden', async () => {
        const {flow} = await mount();

        expect(bar(flow, [TAX]).state, 'the barrier: a linked charge shows it').toBe('on');
        expect(bar(flow, [FREE_FEE])).toEqual({state: 'hidden'});
        expect(bar(flow, [BUY, FREE_FEE, DEPOSIT])).toEqual({state: 'hidden'});
    });

    it('a linked charge on a broker the user cannot edit: left out; alone, hidden (canEditBroker says so)', async () => {
        const {flow} = await mount();

        expect(bar(flow, [READ_ONLY_FEE, TAX])).toEqual({state: 'on', count: 1, rows: [TAX.id]});
        expect(bar(flow, [READ_ONLY_FEE])).toEqual({state: 'hidden'});
        expect(canEditBroker).toHaveBeenCalledWith(READ_ONLY_BROKER);
        expect(canEditBroker).toHaveBeenCalledWith(EDITABLE_BROKER);
    });

    it('`appliesTo` and `pointless` read alone, off the bar: the same predicate', async () => {
        const {flow} = await mount();

        expect(flow.action.appliesTo!(FEE)).toBe(true);
        expect(flow.action.appliesTo!(FREE_FEE)).toBe(false);
        expect(flow.action.appliesTo!(READ_ONLY_FEE)).toBe(false);
        expect(flow.action.pointless!([BUY, FEE])).toBe(false);
        expect(flow.action.pointless!([BUY, FREE_FEE, READ_ONLY_FEE])).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// The panel
// ---------------------------------------------------------------------------

describe('createChargesUnlinkFlow — the panel', () => {
    it('closed until the action is clicked, open after it on the linked charges, closed again by cancel; nothing is committed', async () => {
        const {flow} = await mount();
        expect(flow.open).toBe(false);

        clickBar(flow, [BUY, TAX, FREE_FEE]);
        expect(flow.open).toBe(true);
        expect(ids(flow.charges)).toEqual([TAX.id]);

        flow.cancel();
        flushSync();
        expect(flow.open).toBe(false);
        expect(commitMock()).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
    });

    it('a reader sees it open and close: `open` and `charges` are reactive', async () => {
        const {flow} = await mount();
        const opens = recordReads(() => flow.open);
        onTestFinished(() => opens.stop());
        const charges = recordReads(() => ids(flow.charges).join(','));
        onTestFinished(() => charges.stop());

        clickBar(flow, [BUY, TAX]);
        flow.cancel();
        flushSync();

        expect(opens.values).toEqual([false, true, false]);
        expect(charges.values).toContain(String(TAX.id));
    });

    it('onClick on the whole selection takes the unlinkable ones itself', async () => {
        const {flow} = await mount();

        void flow.action.onClick([BUY, READ_ONLY_FEE, FEE, FREE_FEE, TAX]);
        flushSync();

        expect(flow.open).toBe(true);
        expect(ids(flow.charges)).toEqual([FEE.id, TAX.id]);
    });

    it('the rows are fixed at the click: the selection changed under the open panel changes neither the panel nor the commit', async () => {
        commitMock().mockResolvedValue(COMMITTED);
        const {flow} = await mount();
        const selected = [BUY, TAX];

        void flow.action.onClick(selected);
        flushSync();
        // The page's selection moves on: the very array handed to the click now holds another charge.
        selected.splice(0, selected.length, FEE);
        flushSync();

        expect(ids(flow.charges)).toEqual([TAX.id]);
        await flow.confirm();
        expect(commitMock()).toHaveBeenCalledTimes(1);
        expect(commitMock().mock.calls[0][0]).toEqual({updates: [{id: TAX.id, parent_transaction_id: 0}]});
    });

    it('a second click, after a cancel, opens on its own rows', async () => {
        const {flow} = await opened([BUY, TAX]);
        flow.cancel();
        flushSync();

        clickBar(flow, [BUY, FEE]);

        expect(flow.open).toBe(true);
        expect(ids(flow.charges)).toEqual([FEE.id]);
    });
});

// ---------------------------------------------------------------------------
// Confirm
// ---------------------------------------------------------------------------

describe('createChargesUnlinkFlow — confirm', () => {
    it('committed: one commit unlinking the charges in order, the panel closes, tx.charges.unlinked is sent with no toast, onUnlinked runs once', async () => {
        commitMock().mockResolvedValue(COMMITTED);
        const {flow, onUnlinked, seen} = await opened([BUY, TAX, FEE]);

        await flow.confirm();
        flushSync();

        expect(commitMock()).toHaveBeenCalledTimes(1);
        expect(commitMock().mock.calls[0][0]).toEqual({
            updates: [
                {id: TAX.id, parent_transaction_id: 0},
                {id: FEE.id, parent_transaction_id: 0},
            ],
        });
        expect(flow.open).toBe(false);
        expect(flow.unlinking).toBe(false);
        expect(notify).toHaveBeenCalledTimes(1);
        const sent = vi.mocked(notify).mock.calls[0][0];
        expect(sent).toEqual({name: 'tx.charges.unlinked', detail: {charges: [TAX.id, FEE.id]}});
        expect(onUnlinked).toHaveBeenCalledTimes(1);
        expect(seen, 'onUnlinked runs last: the panel is closed and the event sent').toEqual([{open: false, notified: 1}]);
        for (const toast of Object.values(toasts)) if (vi.isMockFunction(toast)) expect(toast).not.toHaveBeenCalled();
    });

    it('unlinking is true while the commit is in flight and false once it lands', async () => {
        const commit = heldCommit();
        const {flow} = await opened();
        expect(flow.unlinking).toBe(false);

        const pending = flow.confirm();
        flushSync();
        expect(flow.unlinking).toBe(true);
        expect(flow.open, 'the panel stays up while it saves').toBe(true);

        commit.land(COMMITTED);
        await pending;
        flushSync();
        expect(flow.unlinking).toBe(false);
        expect(flow.open).toBe(false);
    });

    it('while saving, a second confirm sends nothing', async () => {
        const commit = heldCommit();
        const {flow, onUnlinked} = await opened();

        const first = flow.confirm();
        flushSync();
        const second = flow.confirm();
        flushSync();
        expect(commitMock(), 'one commit in flight').toHaveBeenCalledTimes(1);

        commit.land(COMMITTED);
        await Promise.all([first, second]);
        flushSync();
        expect(commitMock()).toHaveBeenCalledTimes(1);
        expect(notify).toHaveBeenCalledTimes(1);
        expect(onUnlinked).toHaveBeenCalledTimes(1);
    });

    it('while saving, cancel does not close; once the save is refused it does', async () => {
        const commit = heldCommit();
        const {flow} = await opened();

        const pending = flow.confirm();
        flushSync();
        flow.cancel();
        flushSync();
        expect(flow.open, 'cancel does not close while saving').toBe(true);

        commit.land(REFUSED);
        await pending;
        flushSync();
        expect(flow.open, 'refused: still open').toBe(true);
        flow.cancel();
        flushSync();
        expect(flow.open, 'nothing in flight: cancel closes').toBe(false);
    });

    it('refused: a toast with the reasons, onUnlinked not called, nothing notified, the panel stays open, unlinking back to false', async () => {
        commitMock().mockResolvedValue(REFUSED);
        const issueContext = vi.fn<() => ResolverContext>(() => ({brokers: [{id: EDITABLE_BROKER, name: 'TL9 Broker'}], assets: []}));
        const {flow, onUnlinked} = await opened([BUY, TAX], issueContext);

        await flow.confirm();
        flushSync();

        expect(toasts.error).toHaveBeenCalledTimes(1);
        expect(typeof vi.mocked(toasts.error).mock.calls[0][0]).toBe('string');
        expect(onUnlinked).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
        expect(flow.open, 'the panel stays open').toBe(true);
        expect(ids(flow.charges), 'on the same charges').toEqual([TAX.id]);
        expect(flow.unlinking).toBe(false);
        expect(issueContext, 'the refusal names what the page hands it').toHaveBeenCalledTimes(1);
        expect(getAllBrokers, 'the stores are not read when the page hands a context').not.toHaveBeenCalled();
    });

    it('refused without an issueContext: the broker and asset stores name the reasons, and the toast still comes', async () => {
        commitMock().mockResolvedValue(REFUSED);
        const {flow, onUnlinked} = await opened();

        await expect(flow.confirm()).resolves.toBeUndefined();

        expect(toasts.error).toHaveBeenCalledTimes(1);
        expect(getAllBrokers).toHaveBeenCalled();
        expect(getAllAssets).toHaveBeenCalled();
        expect(onUnlinked).not.toHaveBeenCalled();
        expect(flow.open).toBe(true);
    });

    it('refused, then confirmed again: a second commit of the same charges, and this time it closes', async () => {
        commitMock().mockResolvedValueOnce(REFUSED).mockResolvedValueOnce(COMMITTED);
        const {flow, onUnlinked} = await opened();

        await flow.confirm();
        flushSync();
        await flow.confirm();
        flushSync();

        expect(commitMock()).toHaveBeenCalledTimes(2);
        expect(commitMock().mock.calls[1][0]).toEqual(commitMock().mock.calls[0][0]);
        expect(flow.open).toBe(false);
        expect(onUnlinked).toHaveBeenCalledTimes(1);
    });

    it('nothing clicked yet: confirm commits nothing', async () => {
        const {flow, onUnlinked} = await mount();

        await flow.confirm();

        expect(commitMock()).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
        expect(onUnlinked).not.toHaveBeenCalled();
    });
});

// ---------------------------------------------------------------------------
// The type rules
// ---------------------------------------------------------------------------

describe('createChargesUnlinkFlow — the type rules are never asked for', () => {
    for (const [outcome, result] of [
        ['committed', COMMITTED],
        ['refused', REFUSED],
    ] as const) {
        it(`mounted, read by the bar, opened and ${outcome}: no request for the types`, async () => {
            commitMock().mockResolvedValue(result);
            const {flow} = await mount();
            expect(bar(flow, [BUY, FEE, TAX])).toEqual({state: 'on', count: 2, rows: [FEE.id, TAX.id]});

            clickBar(flow, [BUY, FEE, TAX]);
            await flow.confirm();
            flushSync();

            // The barrier: the whole path ran, to its end.
            expect(commitMock()).toHaveBeenCalledTimes(1);
            expect(flow.open).toBe(outcome === 'refused');
            expect(ensureTypesLoaded).not.toHaveBeenCalled();
            expect(typesRequest()).not.toHaveBeenCalled();
        });
    }
});
