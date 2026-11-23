// @vitest-environment jsdom
//
// The docblock above is load-bearing: under the default `node` environment a `.svelte.ts` `$derived` returns a stale
// value and `$effect` never runs (`$test/runes.svelte`). `assertEffectsRun()` in `beforeAll` fails the file loudly if
// the docblock is ever lost.
/**
 * chargesLinkFlow — «Link the charges» from a table's selection bar, shared by the Transactions page and the broker's
 * Transactions tab (project 66, F6; shared in TL-5). The contract is the module's header:
 *
 *   createChargesLinkFlow({selection, onLinked, issueContext?}) → {state, open, parent, charges, linking, action,
 *                                                                  confirm(), cancel()}
 *
 *   - `state` / `action`: `linkSelection` on `selection()`; the rules themselves are `chargeLinkRules.test.ts`'s, so
 *     these cases only prove the flow wires them: ok, hidden, off with its reason and a hint.
 *   - The type rules: the flow calls `ensureTypesLoaded` itself once two rows are selected (the broker's tab never loads them). Before they land
 *     every row has no charge role and the action is hidden; once they land the same selection is ok.
 *   - `open`: false until `action.onClick()`; `cancel()` closes it.
 *   - `confirm()`: one commit (`linkCommit`); committed → closed, `tx.charges.linked` notified, `onLinked` once;
 *     refused → `toasts.error` with the reasons (named through `issueContext`, or the broker/asset stores), still open.
 *
 * The network is stubbed at its edges: GET /transactions/types (`zodiosApi`) and the commit (`commitTransactions`).
 * The type store caches its answer at module level and never drops it, so the answer is a deferred promise: the type
 * rules case releases it itself, every other case releases it in its `beforeAll` (releasing twice is harmless).
 */
import {beforeAll, beforeEach, describe, expect, it, onTestFinished, vi} from 'vitest';
import {flushSync} from 'svelte';
import {schemas} from '$lib/api/generated';
import {zodiosApi} from '$lib/api';
import {setupI18n} from '$test/component';
import {assertEffectsRun, effectRoot, reactiveBox, recordReads} from '$test/runes.svelte';
import {commitTransactions, type CommitResult} from './txCommitApi';
import {notify} from '$lib/stores/app/notify.svelte';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {getAllAssets} from '$lib/stores/reference/assetStore';
import {getAllBrokers} from '$lib/stores/reference/brokerStore';
import {ensureTypesLoaded} from './transactionTypeStore';
import type {ResolverContext} from './resolveValidationMessage';
import type {TXReadItem} from './types';
import {createChargesLinkFlow, type ChargesLinkFlow} from './chargesLinkFlow.svelte';

vi.mock('$lib/api', () => ({
    zodiosApi: {get_transaction_types_api_v1_transactions_types_get: vi.fn()},
    ApiError: class ApiError extends Error {},
    axiosInstance: {},
}));
vi.mock('./txCommitApi', () => ({commitTransactions: vi.fn()}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn(), show: vi.fn()},
}));
// Every broker of these rows is editable; the broker list is what the default refusal context names.
vi.mock('$lib/stores/reference/brokerStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/brokerStore')>()),
    canEditBroker: vi.fn(() => true),
    getAllBrokers: vi.fn(() => [{id: 77, name: 'TL5 Broker'}]),
}));
vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/assetStore')>()),
    getAllAssets: vi.fn(() => [{id: 101, display_name: 'TL5 Asset'}]),
}));

// ---------------------------------------------------------------------------
// Fixtures: ids in the 940000s, so none can be mistaken for a count or an index
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
        description: `TL5 link ${type} ${id}`,
        cost_basis_override: null,
        asset_event_id: null,
        ...over,
    };
}

const BUY = tx(940_001, 'BUY');
const FEE = tx(940_002, 'FEE');
const FEE_NO_ASSET = tx(940_003, 'FEE', {asset_id: null});

function chargeType(code: string, chargeRole: 'charge' | 'parent' | null) {
    return {
        code,
        name: code,
        description: code,
        icon_slug: code.toLowerCase(),
        doc_slug: null,
        asset_mode: 'optional',
        cash_mode: 'required',
        quantity_mode: 'forbidden',
        requires_link: false,
        quantity_sign: 'zero',
        cash_sign: 'negative',
        event_compatible: false,
        charge_role: chargeRole,
        swap_group: [],
    };
}

const TYPES_RESPONSE = schemas.TXTypesResponse.parse({
    transaction_types: [chargeType('BUY', 'parent'), chargeType('FEE', 'charge'), chargeType('TAX', 'charge')],
    event_types: [],
});

/** The one answer of GET /transactions/types, held until a case releases it. */
let releaseTypes!: () => void;
const typesAnswer = new Promise<unknown>((resolve) => {
    releaseTypes = () => resolve(TYPES_RESPONSE);
});
vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockImplementation((() => typesAnswer) as never);

/** Release the type rules and wait until the store holds them. */
async function typesLoaded(): Promise<void> {
    releaseTypes();
    await ensureTypesLoaded();
}

const commitMock = () => vi.mocked(commitTransactions);
const COMMITTED: CommitResult = {committed: true, issues: [], results: [], rawResponse: {}};
const REFUSED: CommitResult = {committed: false, issues: [{error: 'charge refused', code: 'chargeOtherBroker', ref_id: FEE.id}], rawResponse: {}};

/** A flow built as a page builds it: inside an effect root, over a reactive selection read through a getter. */
function mount(rows: TXReadItem[], issueContext?: () => ResolverContext) {
    const page = reactiveBox<{rows: TXReadItem[]}>({rows});
    const onLinked = vi.fn<() => Promise<void>>(async () => {});
    const root = effectRoot(() => createChargesLinkFlow({selection: () => page.rows, onLinked, ...(issueContext ? {issueContext} : {})}));
    flushSync();
    onTestFinished(() => root.stop());
    return {flow: root.value, page, onLinked};
}

// The bar hands the action its rows; the flow reads its own `selection()` instead, so the argument does not matter here.
// Both hooks are optional on `BulkAction`: this flow must define them, and `!` fails loudly when it does not.
const pointless = (flow: ChargesLinkFlow): boolean => flow.action.pointless!([]);
const blocked = (flow: ChargesLinkFlow) => flow.action.blocked!([]);

beforeAll(async () => {
    assertEffectsRun();
    await setupI18n('en');
});

beforeEach(() => {
    commitMock().mockReset();
    vi.mocked(notify).mockClear();
    vi.mocked(toasts.error).mockClear();
    vi.mocked(getAllBrokers).mockClear();
    vi.mocked(getAllAssets).mockClear();
});

// Runs first on purpose: the type store caches for the whole file, and only this case sees it empty. Filtered out,
// the other blocks release the rules themselves.
describe('createChargesLinkFlow — the type rules', () => {
    it('before the rules land every row has no charge role (hidden); once ensureTypesLoaded resolves the same selection is ok', async () => {
        // One row cannot be linked: the rules are not asked for yet (the broker's page keeps its cold path, TL-1b).
        const {flow, page} = mount([BUY]);
        expect(zodiosApi.get_transaction_types_api_v1_transactions_types_get, 'one row selected: the type rules are not asked for').not.toHaveBeenCalled();
        page.rows = [BUY, FEE];
        flushSync();
        const kinds = recordReads(() => flow.state.kind);
        onTestFinished(() => kinds.stop());

        expect(zodiosApi.get_transaction_types_api_v1_transactions_types_get, 'two rows selected: the flow asks for the type rules itself').toHaveBeenCalled();
        expect(flow.state.kind, 'no rules yet: no charge role, the action is hidden').toBe('hidden');
        expect(pointless(flow)).toBe(true);

        await typesLoaded();
        flushSync();

        expect(kinds.values[0], 'the reader first saw it hidden').toBe('hidden');
        expect(kinds.values.at(-1), 'a reader of the state sees it turn ok').toBe('ok');
        expect(flow.state.kind).toBe('ok');
        expect(pointless(flow)).toBe(false);
    });
});

describe('createChargesLinkFlow — state and action', () => {
    beforeAll(typesLoaded);

    it('a BUY and a free FEE of the same broker, asset and date: ok, the action is offered and not blocked', () => {
        const {flow} = mount([BUY, FEE]);

        expect(flow.state.kind).toBe('ok');
        expect(flow.parent?.id).toBe(BUY.id);
        expect(flow.charges.map((c) => c.id)).toEqual([FEE.id]);
        expect(flow.action.id).toBe('link-charges');
        expect(pointless(flow)).toBe(false);
        expect(blocked(flow)).toBeNull();
    });

    it('one row only: hidden', () => {
        const {flow} = mount([BUY]);

        expect(flow.state.kind).toBe('hidden');
        expect(pointless(flow)).toBe(true);
        expect(flow.parent).toBeNull();
        expect(flow.charges).toEqual([]);
    });

    it('a FEE without asset beside a BUY with one: blocked on noAsset, with a hint', () => {
        const {flow} = mount([BUY, FEE_NO_ASSET]);

        expect(flow.state.kind).toBe('disabled');
        expect(pointless(flow)).toBe(false);
        const block = blocked(flow);
        expect(block?.reason).toBe('noAsset');
        const hint = typeof block?.hint === 'function' ? block.hint() : block?.hint;
        expect(hint ?? '', 'the hint says why').not.toBe('');
    });

    it('the state follows the selection: a row added to it is read through the getter', () => {
        const {flow, page} = mount([BUY]);
        expect(flow.state.kind).toBe('hidden');

        page.rows = [BUY, FEE];
        flushSync();

        expect(flow.state.kind).toBe('ok');
    });
});

describe('createChargesLinkFlow — the panel', () => {
    beforeAll(typesLoaded);

    it('closed until the action is clicked, open after it, closed again by cancel; nothing is committed', () => {
        const {flow} = mount([BUY, FEE]);
        expect(flow.open).toBe(false);

        flow.action.onClick([BUY, FEE]);
        flushSync();
        expect(flow.open).toBe(true);

        flow.cancel();
        flushSync();
        expect(flow.open).toBe(false);
        expect(commitMock()).not.toHaveBeenCalled();
    });
});

describe('createChargesLinkFlow — confirm', () => {
    beforeAll(typesLoaded);

    async function opened(issueContext?: () => ResolverContext) {
        const made = mount([BUY, FEE], issueContext);
        made.flow.action.onClick([BUY, FEE]);
        flushSync();
        expect(made.flow.open, 'premise: the panel is open').toBe(true);
        return made;
    }

    it('committed: one commit linking the FEE to the BUY, the panel closes, tx.charges.linked is sent, onLinked runs once', async () => {
        commitMock().mockResolvedValue(COMMITTED);
        const {flow, onLinked} = await opened();

        await flow.confirm();
        flushSync();

        expect(commitMock()).toHaveBeenCalledTimes(1);
        expect(commitMock().mock.calls[0][0]).toEqual({updates: [{id: FEE.id, parent_transaction_id: BUY.id}]});
        expect(flow.open).toBe(false);
        expect(flow.linking).toBe(false);
        expect(notify).toHaveBeenCalledTimes(1);
        expect(vi.mocked(notify).mock.calls[0][0]).toEqual({name: 'tx.charges.linked', detail: {parent: BUY.id, charges: [FEE.id]}});
        expect(onLinked).toHaveBeenCalledTimes(1);
        expect(toasts.error).not.toHaveBeenCalled();
    });

    it('linking is true while the commit is in flight and false once it lands', async () => {
        let land!: (r: CommitResult) => void;
        commitMock().mockImplementation(() => new Promise<CommitResult>((resolve) => (land = resolve)));
        const {flow} = await opened();

        const pending = flow.confirm();
        flushSync();
        expect(flow.linking).toBe(true);

        land(COMMITTED);
        await pending;
        flushSync();
        expect(flow.linking).toBe(false);
    });

    it('refused: a toast with the reasons, onLinked not called, nothing notified, the panel stays open, linking back to false', async () => {
        commitMock().mockResolvedValue(REFUSED);
        const issueContext = vi.fn<() => ResolverContext>(() => ({brokers: [{id: 77, name: 'TL5 Broker'}], assets: []}));
        const {flow, onLinked} = await opened(issueContext);

        await flow.confirm();
        flushSync();

        expect(toasts.error).toHaveBeenCalledTimes(1);
        expect(typeof vi.mocked(toasts.error).mock.calls[0][0]).toBe('string');
        expect(onLinked).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
        expect(flow.open, 'the panel stays open').toBe(true);
        expect(flow.linking).toBe(false);
        expect(issueContext, 'the refusal names what the page hands it').toHaveBeenCalledTimes(1);
        expect(getAllBrokers, 'the stores are not read when the page hands a context').not.toHaveBeenCalled();
    });

    it('refused without an issueContext: the broker and asset stores name the reasons, and the toast still comes', async () => {
        commitMock().mockResolvedValue(REFUSED);
        const {flow, onLinked} = await opened();

        await expect(flow.confirm()).resolves.toBeUndefined();

        expect(toasts.error).toHaveBeenCalledTimes(1);
        expect(getAllBrokers).toHaveBeenCalled();
        expect(getAllAssets).toHaveBeenCalled();
        expect(onLinked).not.toHaveBeenCalled();
        expect(flow.open).toBe(true);
    });

    it('a selection that is not ok: confirm commits nothing', async () => {
        const {flow} = mount([BUY, FEE_NO_ASSET]);

        await flow.confirm();

        expect(commitMock()).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
    });
});
