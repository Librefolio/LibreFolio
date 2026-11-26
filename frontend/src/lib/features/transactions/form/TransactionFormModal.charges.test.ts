// @vitest-environment jsdom
/**
 * TransactionFormModal — the «Linked charges» section (project 66, lot F2b). RED FIRST: the section
 * (`TxFormChargesSection.svelte`) and its wiring in the form do not exist yet.
 *
 * Contract: the F2b note of the lane. In short: a parent type (`chargeRole: 'parent'`) in a single-row form lists its
 * linked FEE/TAX rows (`GET /transactions?parent_ids=[id]`); the section is editable only in the Bulk-hosted form
 * (`commitOnSave: false`, not `view`), read-only elsewhere; Apply pushes the full list of drafts as `payload._charges`;
 * any change in the section makes the form «modified»; a new row with no amount blocks Apply.
 *
 * Types: the store caches the response at module level, and Vitest gives every test file its own module graph, so the
 * real-roles response below is loaded once in `beforeAll` (before `ensureTypesLoaded()`), and no other file sees it.
 * The shared minimal response of TransactionFormModal.test.ts cannot be reused: it leaves BUY/FEE/TAX on the fallback
 * rule, which has no `chargeRole`.
 *
 * Asserted: data-testid and data-* only. The total's text is checked loosely (it contains the number), because the
 * amount is formatted by the locale.
 *
 * Assumption to confirm with the component: the section root carries `data-testid="tx-form-charges"` (the contract names
 * the rows, buttons, total and error, not the root). Its absence is asserted only after a presence barrier.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {ensureTypesLoaded} from '$lib/features/transactions/transactionTypeStore';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';

vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});
vi.mock('$lib/stores/reference/brokerStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/brokerStore')>()),
    ensureBrokersLoaded: vi.fn().mockResolvedValue(undefined),
    refreshAllBrokers: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/assetStore')>()),
    ensureAssetsLoaded: vi.fn().mockResolvedValue(undefined),
    refreshAllAssets: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({
    fxRoutesVersion: writable(0),
    ensureFxRoutesLoaded: vi.fn(async () => undefined),
    getConfiguredCurrencySet: vi.fn(() => new Set(['EUR', 'USD'])),
}));
vi.mock('$lib/features/transactions/txCommitApi', () => ({
    commitTransactions: vi.fn(async () => ({committed: true, results: [], issues: []})),
    validateTransactions: vi.fn(async () => ({committed: true, issues: [], rawResponse: {wac_results: []}})),
}));
// The guide only starts in create mode; these cases are view/edit. A neutral stub keeps the real controller out.
vi.mock('$lib/features/onboarding/onboardingGuide.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/features/onboarding/onboardingGuide.svelte')>()),
    onboardingGuide: {
        active: null,
        queuedFlow: null,
        queuedFlows: [],
        queuedGuides: [],
        maybeStartContextual: vi.fn(() => false),
        queueContextual: vi.fn(),
        clearQueued: vi.fn(),
        maybeStartQueued: vi.fn(() => false),
        dismissHost: vi.fn(),
    },
}));

import TransactionFormModal from './TransactionFormModal.svelte';

// ---------------------------------------------------------------------------------------------------------------
//  Types with real charge roles (shape of an entry of the minimal fixture of TransactionFormModal.test.ts, validated
//  by the generated schema the store parses).
// ---------------------------------------------------------------------------------------------------------------

const baseType = {doc_slug: 'x', requires_link: false, event_compatible: false, cost_basis_mode: 'forbidden'} as const;

const TYPES_WITH_CHARGE_ROLES = schemas.TXTypesResponse.parse({
    transaction_types: [
        {...baseType, code: 'BUY', name: 'Buy', description: 'Buy', icon_slug: 'buy', asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'positive', cash_sign: 'negative', charge_role: 'parent'},
        {...baseType, code: 'SELL', name: 'Sell', description: 'Sell', icon_slug: 'sell', asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'negative', cash_sign: 'positive', charge_role: 'parent'},
        {...baseType, code: 'DEPOSIT', name: 'Deposit', description: 'Deposit', icon_slug: 'deposit', asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'positive', charge_role: 'parent'},
        {...baseType, code: 'FEE', name: 'Fee', description: 'Fee', icon_slug: 'fee', asset_mode: 'optional', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'negative', charge_role: 'charge'},
        {...baseType, code: 'TAX', name: 'Tax', description: 'Tax', icon_slug: 'tax', asset_mode: 'optional', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'negative', charge_role: 'charge'},
        {
            ...baseType,
            code: 'TRANSFER',
            name: 'Asset Transfer',
            description: 'Asset transfer',
            icon_slug: 'transfer',
            doc_slug: 'transfer',
            asset_mode: 'required',
            cash_mode: 'forbidden',
            quantity_mode: 'required',
            requires_link: true,
            quantity_sign: 'nonzero',
            cash_sign: 'zero',
            pair_form_layout: 'transfer_asset',
            cost_basis_pair: ['forbidden', 'required_qty_pos'],
            charge_role: null,
        },
    ],
    event_types: [],
});

// ---------------------------------------------------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------------------------------------------------

const queryCharges = () => vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get);

function mount(props: Record<string, unknown> = {}) {
    const onClose = vi.fn();
    return {onClose, ...render(TransactionFormModal, {open: true, mode: 'edit', items: null, onClose, ...props})};
}

function txRow(overrides: Record<string, unknown> = {}) {
    return {
        id: 10,
        broker_id: 17,
        asset_id: 42,
        type: 'BUY',
        date: '2024-03-10',
        quantity: '1',
        cash: {code: 'EUR', amount: '-100'},
        related_transaction_id: null,
        partner_broker_id: null,
        parent_transaction_id: null,
        charges_count: 0,
        tags: [],
        description: '',
        cost_basis_override: null,
        cost_basis_mode: null,
        asset_event_id: null,
        created_at: '2024-03-10T00:00:00Z',
        updated_at: '2024-03-10T00:00:00Z',
        ...overrides,
    };
}

/** A saved charge row of a parent, as `GET /transactions?parent_ids=…` returns it. */
function chargeRow(id: number, type: 'FEE' | 'TAX', amount: string, parentId = 10, description = '') {
    return txRow({id, type, asset_id: null, quantity: '0', cash: {code: 'EUR', amount: `-${amount}`}, parent_transaction_id: parentId, charges_count: 0, description});
}

const FEE_11 = () => chargeRow(11, 'FEE', '2');
const TAX_12 = () => chargeRow(12, 'TAX', '5');

/** The Bulk-hosted form: a saved row in edit mode that pushes its draft to the parent. */
function bulkHosted(onPushDraft = vi.fn(), parent = txRow({charges_count: 2})) {
    return {onPushDraft, ...mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, allowChargeEdits: true, onPushDraft, items: [parent]})};
}

const rows = () => screen.queryAllByTestId('tx-form-charge-row');
const rowById = (id: number) => rows().find((r) => r.getAttribute('data-charge-id') === String(id));
const newRows = () => rows().filter((r) => r.getAttribute('data-charge-id') === '');

async function waitForSavedRows(ids: number[]) {
    await waitFor(() => expect(rows().map((r) => r.getAttribute('data-charge-id'))).toEqual(ids.map(String)));
}

async function typeInto(testid: string, value: string) {
    const input = screen.getByTestId(testid) as HTMLInputElement;
    await fireEvent.input(input, {target: {value}});
    await fireEvent.blur(input);
}

/** Presence barrier for absences: the form itself is on screen and settled enough to show its fields. Not the Save
 *  button: a read-only form has none. */
async function formIsUp() {
    await screen.findByTestId('tx-form-body');
    await screen.findByTestId('tx-form-cash-wrap');
}

/** A promise settled by hand. */
function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

describe('TransactionFormModal — linked charges (66 F2b)', () => {
    beforeAll(async () => {
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_WITH_CHARGE_ROLES);
        await setupI18n();
        await ensureTypesLoaded();
    });

    beforeEach(() => {
        // Reset only the charges call and the draft spies; the types stay loaded in the store.
        queryCharges().mockReset();
        queryCharges().mockImplementation(async () => []);
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    // 1
    it('view mode: a BUY with two charges lists them read-only and totals the charged amount (out)', async () => {
        queryCharges().mockResolvedValue([FEE_11(), TAX_12()] as never);
        mount({mode: 'view', items: [txRow({charges_count: 2})]});

        await waitForSavedRows([11, 12]);
        expect(queryCharges()).toHaveBeenCalledWith(expect.objectContaining({queries: expect.objectContaining({parent_ids: [10]})}));
        expect(rowById(11)).toHaveAttribute('data-charge-type', 'FEE');
        expect(rowById(12)).toHaveAttribute('data-charge-type', 'TAX');

        expect(screen.queryByTestId('tx-form-charges-add-FEE')).toBeNull();
        expect(screen.queryByTestId('tx-form-charges-add-TAX')).toBeNull();
        expect(screen.queryByTestId('tx-form-charge-unlink-saved-11')).toBeNull();
        expect(screen.queryByTestId('tx-form-charge-remove-saved-11')).toBeNull();
        expect(screen.queryByTestId('tx-form-charge-note-saved-11')).toBeNull();
        expect(screen.queryByTestId('tx-form-charge-note-saved-12')).toBeNull();

        expect(screen.getByTestId('tx-form-charges-total')).toHaveAttribute('data-direction', 'out');
        expect(screen.getByTestId('tx-form-charges-total-EUR')).toHaveTextContent(/107/);
    });

    // 2
    it('view mode: charges_count 0 makes no charges call and shows no section', async () => {
        mount({mode: 'view', items: [txRow({charges_count: 0})]});

        await formIsUp();
        expect(queryCharges()).not.toHaveBeenCalled();
        expect(screen.queryByTestId('tx-form-charges')).toBeNull();
        expect(screen.queryByTestId('tx-form-charge-row')).toBeNull();
    });

    // 3
    it('a load failure shows the error line, never an empty section', async () => {
        queryCharges().mockRejectedValue(new Error('boom'));
        mount({mode: 'view', items: [txRow({charges_count: 2})]});

        const error = await screen.findByTestId('tx-form-charges-error');
        expect(error).toHaveAttribute('data-state', 'error');
        expect(screen.queryByTestId('tx-form-charge-row')).toBeNull();
    });

    // 4
    it('Bulk-hosted edit: add, type, unlink, remove, then Apply pushes the three drafts in _charges', async () => {
        queryCharges().mockResolvedValue([FEE_11(), TAX_12()] as never);
        const {onPushDraft} = bulkHosted();
        await waitForSavedRows([11, 12]);

        await fireEvent.click(screen.getByTestId('tx-form-charges-add-FEE'));
        await waitFor(() => expect(newRows()).toHaveLength(1));
        const fresh = newRows()[0];
        const key = fresh.getAttribute('data-charge-key') ?? '';
        expect(key.startsWith('new-')).toBe(true);
        expect(fresh).toHaveAttribute('data-charge-type', 'FEE');

        await typeInto(`tx-form-charge-cash-${key}-amount`, '3');
        const note = screen.getByTestId(`tx-form-charge-note-${key}`) as HTMLInputElement;
        await fireEvent.input(note, {target: {value: 'Tobin tax'}});
        expect(note).toHaveValue('Tobin tax');

        await fireEvent.click(screen.getByTestId('tx-form-charge-unlink-saved-11'));
        await waitFor(() => expect(rowById(11)).toBeUndefined());
        await fireEvent.click(screen.getByTestId('tx-form-charge-remove-saved-12'));
        await waitFor(() => expect(rowById(12)).toBeUndefined());
        expect(newRows()).toHaveLength(1);

        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));

        expect(onPushDraft).toHaveBeenCalledTimes(1);
        const payload = onPushDraft.mock.calls[0]?.[0] as {_charges?: Array<Record<string, any>>};
        const charges = payload._charges ?? [];
        expect(charges).toHaveLength(3);
        const created = charges.find((c) => c.key === key);
        const unlinked = charges.find((c) => c.id === 11);
        const deleted = charges.find((c) => c.id === 12);
        expect(created).toMatchObject({id: null, type: 'FEE', state: 'linked', description: 'Tobin tax'});
        expect(created?.cash?.amount).toBe('3');
        expect(unlinked).toMatchObject({type: 'FEE', state: 'unlink'});
        expect(deleted).toMatchObject({type: 'TAX', state: 'delete'});
    });

    // 5
    it('a new row with no amount is marked missing and blocks Apply until an amount is typed', async () => {
        queryCharges().mockResolvedValue([FEE_11(), TAX_12()] as never);
        bulkHosted();
        await waitForSavedRows([11, 12]);
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());

        await fireEvent.click(screen.getByTestId('tx-form-charges-add-TAX'));
        await waitFor(() => expect(newRows()).toHaveLength(1));
        const fresh = newRows()[0];
        const key = fresh.getAttribute('data-charge-key') ?? '';
        expect(fresh).toHaveAttribute('data-missing', 'true');
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeDisabled());

        await typeInto(`tx-form-charge-cash-${key}-amount`, '1.5');
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        expect(newRows()[0]).not.toHaveAttribute('data-missing', 'true');
    });

    // 6
    it('removing a NEW row drops it, and _charges after Apply does not contain it', async () => {
        queryCharges().mockResolvedValue([FEE_11(), TAX_12()] as never);
        const {onPushDraft} = bulkHosted();
        await waitForSavedRows([11, 12]);

        await fireEvent.click(screen.getByTestId('tx-form-charges-add-FEE'));
        await waitFor(() => expect(newRows()).toHaveLength(1));
        const key = newRows()[0].getAttribute('data-charge-key') ?? '';
        await fireEvent.click(screen.getByTestId(`tx-form-charge-remove-${key}`));
        await waitFor(() => expect(newRows()).toHaveLength(0));

        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        const charges = ((onPushDraft.mock.calls[0]?.[0] as {_charges?: Array<{key: string; id: number | null}>})._charges ?? []).slice();
        expect(charges.some((c) => c.key === key)).toBe(false);
        expect(charges.filter((c) => c.id === null)).toHaveLength(0);
        expect(charges.map((c) => c.id).sort()).toEqual([11, 12]);
    });

    // 7
    it('dirty: adding a charge makes Cancel ask to discard; with no change Cancel closes straight away', async () => {
        queryCharges().mockResolvedValue([FEE_11(), TAX_12()] as never);
        const first = bulkHosted();
        await waitForSavedRows([11, 12]);

        // Loading the charges is not a change.
        await fireEvent.click(screen.getByTestId('tx-form-cancel'));
        expect(first.onClose).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull();
        cleanup();

        const second = bulkHosted();
        await waitForSavedRows([11, 12]);
        await fireEvent.click(screen.getByTestId('tx-form-charges-add-FEE'));
        await waitFor(() => expect(newRows()).toHaveLength(1));
        await fireEvent.click(screen.getByTestId('tx-form-cancel'));

        await screen.findByTestId('confirm-modal-confirm');
        expect(second.onClose).not.toHaveBeenCalled();
    });

    // 8
    describe('hidden', () => {
        it('a FEE row (a charge itself) shows no section', async () => {
            queryCharges().mockResolvedValue([FEE_11()] as never);
            mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, allowChargeEdits: true, onPushDraft: vi.fn(), items: [txRow({id: 11, type: 'FEE', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '-2'}, parent_transaction_id: 10, charges_count: 1})]});

            await formIsUp();
            await screen.findByTestId('tx-form-cash-amount');
            expect(screen.queryByTestId('tx-form-charges')).toBeNull();
            expect(screen.queryByTestId('tx-form-charges-add-FEE')).toBeNull();
            expect(screen.queryByTestId('tx-form-charge-row')).toBeNull();
        });

        it('a TRANSFER pair (pair layout) shows no section', async () => {
            const sender = txRow({id: 101, type: 'TRANSFER', quantity: '-5', cash: null, related_transaction_id: 202, partner_broker_id: 23});
            const receiver = txRow({id: 202, broker_id: 23, type: 'TRANSFER', quantity: '5', cash: null, related_transaction_id: 101, partner_broker_id: 17});
            mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, allowChargeEdits: true, onPushDraft: vi.fn(), items: [sender, receiver]});

            await screen.findByTestId('tx-form-dual-split');
            expect(screen.queryByTestId('tx-form-charges')).toBeNull();
            expect(screen.queryByTestId('tx-form-charges-add-FEE')).toBeNull();
        });

        it('the parent leg of an old pair (DEPOSIT with a related id) shows its rows but offers no add buttons', async () => {
            queryCharges().mockResolvedValue([chargeRow(31, 'FEE', '1', 30)] as never);
            mount({
                mode: 'edit',
                unlockImmutable: true,
                commitOnSave: false,
                allowChargeEdits: true,
                onPushDraft: vi.fn(),
                items: [txRow({id: 30, type: 'DEPOSIT', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '100'}, related_transaction_id: 999, partner_broker_id: 23, charges_count: 1})],
            });

            await waitForSavedRows([31]);
            expect(screen.queryByTestId('tx-form-charges-add-FEE')).toBeNull();
            expect(screen.queryByTestId('tx-form-charges-add-TAX')).toBeNull();
        });
    });

    // 9
    it('a SELL totals the net received (in): 100 with a FEE of 5 contains 95', async () => {
        queryCharges().mockResolvedValue([chargeRow(41, 'FEE', '5', 40)] as never);
        mount({mode: 'view', items: [txRow({id: 40, type: 'SELL', quantity: '-1', cash: {code: 'EUR', amount: '100'}, charges_count: 1})]});

        await waitForSavedRows([41]);
        expect(screen.getByTestId('tx-form-charges-total')).toHaveAttribute('data-direction', 'in');
        expect(screen.getByTestId('tx-form-charges-total-EUR')).toHaveTextContent(/95/);
    });

    // 10
    it('a late answer for the previous row is ignored: the rows stay those of the row now open', async () => {
        const late = deferred<unknown[]>();
        queryCharges().mockImplementation((async (arg: {queries: {parent_ids: number[]}}) => {
            const [id] = arg.queries.parent_ids;
            if (id === 10) return late.promise;
            return [chargeRow(21, 'TAX', '4', 20)];
        }) as never);

        const {rerender} = mount({mode: 'view', items: [txRow({id: 10, charges_count: 1})], openKey: 0});
        await waitFor(() => expect(queryCharges()).toHaveBeenCalledTimes(1));

        await rerender({open: true, openKey: 1, items: [txRow({id: 20, charges_count: 1})]});
        await waitForSavedRows([21]);

        late.resolve([chargeRow(11, 'FEE', '2', 10)]);
        // Let the stale promise settle and any state write it would make land.
        for (let i = 0; i < 5; i++) await tick();

        expect(rows().map((r) => r.getAttribute('data-charge-id'))).toEqual(['21']);
        expect(within(screen.getByTestId('tx-form-charges-total')).getByTestId('tx-form-charges-total-EUR')).toHaveTextContent(/104/);
    });

    // 11 (lane): until the Bulk saves the charges (F7), a host that does not opt in gets the section read-only.
    it('a Bulk-hosted form without allowChargeEdits lists the charges read-only and pushes no _charges', async () => {
        queryCharges().mockResolvedValue([FEE_11(), TAX_12()] as never);
        const onPushDraft = vi.fn();
        mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, onPushDraft, items: [txRow({charges_count: 2})]});

        await waitFor(() => expect(rows()).toHaveLength(2));
        expect(screen.queryByTestId('tx-form-charges-add-FEE')).toBeNull();
        expect(screen.queryByTestId('tx-form-charge-unlink-saved-11')).toBeNull();
        expect(screen.queryByTestId('tx-form-charge-note-saved-11')).toBeNull();
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        expect(onPushDraft.mock.calls[0][0]).not.toHaveProperty('_charges');
    });

    // 12 (lane): only the charges of this parent are shown, whatever else the answer holds.
    it('a charge of another parent in the answer is not listed', async () => {
        queryCharges().mockResolvedValue([FEE_11(), chargeRow(99, 'TAX', '7', 55)] as never);
        mount({mode: 'view', items: [txRow({charges_count: 1})]});

        await waitFor(() => expect(rows()).toHaveLength(1));
        expect(rows()[0]).toHaveAttribute('data-charge-id', '11');
    });
});

// ---------------------------------------------------------------------------------------------------------------
//  TL-11 — the new charges of the Bulk in their parent's form. A draft the Bulk hands keyed `op-<tempId>` is a row of
//  its own there: «Open» (`onOpenRow('<tempId>')`), «Unlink» (state `unlink` in `_charges`) and the bin. A `new-<n>` row,
//  written in this opening, has only the bin. `highlightKey` marks the row with that key (the charge the user came from).
//  RED until then; the discard question's testids are the ConfirmModal's own.
// ---------------------------------------------------------------------------------------------------------------

/** A charge of the Bulk as its drafts hand it (`chargeDraftsFor`): a new one (`op-<tempId>`). */
const opDraft = (tempId: string, description: string) => ({key: `op-${tempId}`, id: null, type: 'FEE', cash: {amount: '2', code: 'EUR'}, description, original: null, state: 'linked'});
/** A saved one (`saved-<id>`). */
const savedDraft = (id: number) => ({key: `saved-${id}`, id, type: 'TAX', cash: {amount: '5', code: 'EUR'}, description: 'saved tax', original: {type: 'TAX', cash: {amount: '5', code: 'EUR'}, description: 'saved tax'}, state: 'linked'});

/** A new BUY in the form the Bulk hosts, its charges handed. */
function newParentHosted(charges: unknown[], extra: Record<string, unknown> = {}) {
    const onPushDraft = vi.fn();
    const onOpenRow = vi.fn();
    const onOpenTransaction = vi.fn();
    return {onPushDraft, onOpenRow, onOpenTransaction, ...mount({mode: 'create', commitOnSave: false, allowChargeEdits: true, onPushDraft, onOpenRow, onOpenTransaction, items: [{...txRow({id: 0}), _charges: charges}], ...extra})};
}

const keys = () => rows().map((r) => r.getAttribute('data-charge-key'));
const rowByKey = (key: string) => rows().find((r) => r.getAttribute('data-charge-key') === key);

async function waitForKeys(expected: string[]) {
    await waitFor(() => expect(keys()).toEqual(expected));
}

async function appliedCharges(onPushDraft: ReturnType<typeof vi.fn>): Promise<Array<Record<string, unknown>>> {
    await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
    await fireEvent.click(screen.getByTestId('tx-form-save'));
    expect(onPushDraft).toHaveBeenCalledTimes(1);
    return (onPushDraft.mock.calls[0][0] as {_charges: Array<Record<string, unknown>>})._charges;
}

describe('TransactionFormModal — the Bulk’s new charges in their parent’s form (66 TL-11)', () => {
    beforeAll(async () => {
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_WITH_CHARGE_ROLES);
        await setupI18n();
        await ensureTypesLoaded();
    });

    beforeEach(() => {
        queryCharges().mockReset();
        queryCharges().mockImplementation(async () => []);
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    it('an op- row has «Open», «Unlink» and the bin', async () => {
        newParentHosted([opDraft('n-fee', 'new fee')]);

        await waitForKeys(['op-n-fee']);
        expect(screen.getByTestId('tx-form-charge-remove-op-n-fee'), 'the bin stays').toBeInTheDocument();
        expect(screen.queryByTestId('tx-form-charge-open-op-n-fee'), '66 TL-11: no «Open» on a new charge of the Bulk').not.toBeNull();
        expect(screen.queryByTestId('tx-form-charge-unlink-op-n-fee'), '66 TL-11: no «Unlink» on a new charge of the Bulk').not.toBeNull();
    });

    it('«Open» on an op- row asks the host for that row (onOpenRow with its tempId), never for a saved id', async () => {
        const {onOpenRow, onOpenTransaction, onClose} = newParentHosted([opDraft('n-fee', 'new fee')]);
        await waitForKeys(['op-n-fee']);

        await fireEvent.click(screen.getByTestId('tx-form-charge-open-op-n-fee'));

        expect(onOpenRow).toHaveBeenCalledTimes(1);
        expect(onOpenRow.mock.calls[0][0]).toBe('n-fee');
        expect(onOpenTransaction).not.toHaveBeenCalled();
        expect(onClose).not.toHaveBeenCalled();
    });

    it('without onOpenRow an op- row has no «Open» (a saved one keeps its own), but keeps «Unlink»', async () => {
        newParentHosted([opDraft('n-fee', 'new fee'), savedDraft(12)], {onOpenRow: undefined});

        await waitForKeys(['op-n-fee', 'saved-12']);
        expect(screen.getByTestId('tx-form-charge-open-saved-12')).toBeInTheDocument();
        expect(screen.queryByTestId('tx-form-charge-open-op-n-fee')).toBeNull();
        expect(screen.queryByTestId('tx-form-charge-unlink-op-n-fee'), '66 TL-11: no «Unlink» on a new charge of the Bulk').not.toBeNull();
    });

    it('«Unlink» on an op- row handed by the Bulk: out of the section, the form dirty, Apply’s _charges holds it with the state unlink', async () => {
        const {onPushDraft, onClose} = newParentHosted([opDraft('n-fee', 'new fee'), opDraft('n-fee2', 'new fee 2')]);
        await waitForKeys(['op-n-fee', 'op-n-fee2']);

        await fireEvent.click(screen.getByTestId('tx-form-charge-unlink-op-n-fee'));

        await waitForKeys(['op-n-fee2']);
        await fireEvent.click(screen.getByTestId('tx-form-cancel'));
        await screen.findByTestId('confirm-modal-confirm');
        expect(onClose, 'a change not applied: closing asks').not.toHaveBeenCalled();
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());

        const drafts = await appliedCharges(onPushDraft);
        expect(drafts).toHaveLength(2);
        expect(drafts.find((d) => d.key === 'op-n-fee')).toMatchObject({id: null, type: 'FEE', description: 'new fee', cash: {amount: '2', code: 'EUR'}, state: 'unlink'});
        expect(drafts.find((d) => d.key === 'op-n-fee2')).toMatchObject({state: 'linked'});
    });

    it('highlightKey marks the row with that key and no other', async () => {
        newParentHosted([opDraft('n-fee', 'new fee'), opDraft('n-fee2', 'new fee 2'), savedDraft(12)], {highlightKey: 'op-n-fee2'});

        await waitForKeys(['op-n-fee', 'op-n-fee2', 'saved-12']);
        expect(rowByKey('op-n-fee2'), '66 TL-11: the charge the user came from is not highlighted').toHaveAttribute('data-highlighted', 'true');
        expect(rowByKey('op-n-fee')).toHaveAttribute('data-highlighted', 'false');
        expect(rowByKey('saved-12')).toHaveAttribute('data-highlighted', 'false');
    });

    it('unsaved changes: «Open» on an op- row asks to discard first; Cancel keeps everything, confirming navigates', async () => {
        const {onOpenRow, onClose} = newParentHosted([opDraft('n-fee', 'new fee')]);
        await waitForKeys(['op-n-fee']);
        await fireEvent.click(screen.getByTestId('tx-form-charges-add-TAX'));
        await waitFor(() => expect(rows()).toHaveLength(2));
        const typed = keys();

        await fireEvent.click(screen.getByTestId('tx-form-charge-open-op-n-fee'));
        await screen.findByTestId('confirm-modal-confirm');
        expect(onOpenRow).not.toHaveBeenCalled();
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());
        expect(onOpenRow).not.toHaveBeenCalled();
        expect(onClose).not.toHaveBeenCalled();
        expect(keys(), 'everything typed is kept').toEqual(typed);

        await fireEvent.click(screen.getByTestId('tx-form-charge-open-op-n-fee'));
        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));
        expect(onOpenRow).toHaveBeenCalledTimes(1);
        expect(onOpenRow.mock.calls[0][0]).toBe('n-fee');
        expect(onClose).not.toHaveBeenCalled();
    });

    // --- guards, green before and after ---

    it('guard: a new-<n> row, written in this opening, has only the bin', async () => {
        newParentHosted([]);
        await screen.findByTestId('tx-form-charges-add-FEE');
        await fireEvent.click(screen.getByTestId('tx-form-charges-add-FEE'));
        await waitFor(() => expect(rows()).toHaveLength(1));
        const key = keys()[0] ?? '';
        expect(key.startsWith('new-'), `premise: ${key}`).toBe(true);

        expect(screen.getByTestId(`tx-form-charge-remove-${key}`)).toBeInTheDocument();
        expect(screen.queryByTestId(`tx-form-charge-open-${key}`)).toBeNull();
        expect(screen.queryByTestId(`tx-form-charge-unlink-${key}`)).toBeNull();
    });

    it('guard: the bin on an op- row takes it out of the section and of Apply’s _charges', async () => {
        const {onPushDraft} = newParentHosted([opDraft('n-fee', 'new fee'), opDraft('n-fee2', 'new fee 2')]);
        await waitForKeys(['op-n-fee', 'op-n-fee2']);

        await fireEvent.click(screen.getByTestId('tx-form-charge-remove-op-n-fee'));

        await waitForKeys(['op-n-fee2']);
        expect((await appliedCharges(onPushDraft)).map((d) => d.key)).toEqual(['op-n-fee2']);
    });

    it('guard: not editable — an op- row has neither «Unlink» nor the bin', async () => {
        newParentHosted([opDraft('n-fee', 'new fee')], {allowChargeEdits: false});

        await waitForKeys(['op-n-fee']);
        expect(screen.queryByTestId('tx-form-charge-unlink-op-n-fee')).toBeNull();
        expect(screen.queryByTestId('tx-form-charge-remove-op-n-fee')).toBeNull();
    });
});
