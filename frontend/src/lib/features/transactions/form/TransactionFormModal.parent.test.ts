// @vitest-environment jsdom
/**
 * TransactionFormModal — «Linked to» section of a charge and «Open» both ways (project 66, lot F3). RED FIRST:
 * `TxFormParentSection.svelte`, `onOpenTransaction` and `highlightTxId` do not exist yet.
 *
 * Contract: 66-F3-contract.md. data-testid and data-* only. The transactions query answers `queries.ids` (the parent
 * fetch of a charge) and `queries.parent_ids` (the charges fetch of a parent) differently.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
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

const queryApi = () => vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get);

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
function bulkHosted(onPushDraft = vi.fn(), parent: Record<string, unknown> = txRow({charges_count: 2}), extra: Record<string, unknown> = {}) {
    return {onPushDraft, ...mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, allowChargeEdits: true, onPushDraft, items: [parent], ...extra})};
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

const PARENT_10 = () => txRow({id: 10, type: 'BUY', charges_count: 2});
const FEE_ROW = (parentId: number | null = 10) => txRow({id: 11, type: 'FEE', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '-2'}, parent_transaction_id: parentId, charges_count: 0});

/** Answers the parent fetch (`ids`) and the charges fetch (`parent_ids`) separately. */
function answer(byIds: (ids: number[]) => unknown, byParent: (ids: number[]) => unknown = () => []) {
    queryApi().mockImplementation((async (arg: {queries: {ids?: number[]; parent_ids?: number[]}}) => {
        if (arg.queries.ids) return byIds(arg.queries.ids);
        if (arg.queries.parent_ids) return byParent(arg.queries.parent_ids);
        return [];
    }) as never);
}

const idsCalls = () => queryApi().mock.calls.filter((c) => (c[0] as {queries: {ids?: number[]}}).queries.ids);
const parentBox = () => screen.getByTestId('tx-form-parent');

describe('TransactionFormModal — parent link and Open (66 F3)', () => {
    beforeAll(async () => {
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_WITH_CHARGE_ROLES);
        await setupI18n();
        await ensureTypesLoaded();
    });

    beforeEach(() => {
        queryApi().mockReset();
        queryApi().mockImplementation(async () => []);
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    // 1
    it('view mode: a FEE shows its parent (fetched by id), and Open calls onOpenTransaction without closing', async () => {
        answer(() => [PARENT_10()]);
        const onOpenTransaction = vi.fn();
        const {onClose} = mount({mode: 'view', items: [FEE_ROW()], onOpenTransaction});

        await waitFor(() => expect(screen.getByTestId('tx-form-parent')).toHaveAttribute('data-state', 'ready'));
        expect(queryApi()).toHaveBeenCalledWith(expect.objectContaining({queries: expect.objectContaining({ids: [10]})}));
        expect(parentBox()).toHaveAttribute('data-parent-id', '10');
        expect(screen.getByTestId('tx-form-parent-summary')).toHaveTextContent('#10');

        await fireEvent.click(screen.getByTestId('tx-form-parent-open'));
        expect(onOpenTransaction).toHaveBeenCalledTimes(1);
        expect(onOpenTransaction).toHaveBeenCalledWith(10);
        expect(onClose).not.toHaveBeenCalled();
    });

    // 2
    it('view mode without onOpenTransaction: no Open and no Unlink (read-only)', async () => {
        answer(() => [PARENT_10()]);
        mount({mode: 'view', items: [FEE_ROW()]});

        await waitFor(() => expect(screen.getByTestId('tx-form-parent')).toHaveAttribute('data-state', 'ready'));
        expect(screen.queryByTestId('tx-form-parent-open')).toBeNull();
        expect(screen.queryByTestId('tx-form-parent-unlink')).toBeNull();
    });

    // 3
    it('a parent fetch that fails shows the error state and line', async () => {
        queryApi().mockRejectedValue(new Error('boom'));
        mount({mode: 'view', items: [FEE_ROW()]});

        await waitFor(() => expect(screen.getByTestId('tx-form-parent')).toHaveAttribute('data-state', 'error'));
        expect(screen.getByTestId('tx-form-parent-error')).toBeInTheDocument();
    });

    // 4
    it('a FEE without a parent and a BUY show no parent section', async () => {
        mount({mode: 'view', items: [FEE_ROW(null)]});
        await formIsUp();
        expect(screen.queryByTestId('tx-form-parent')).toBeNull();
        expect(idsCalls()).toHaveLength(0);
        cleanup();

        mount({mode: 'view', items: [txRow({charges_count: 0})]});
        await formIsUp();
        expect(screen.queryByTestId('tx-form-parent')).toBeNull();
    });

    // 5
    it('view mode: a saved charge row opens its transaction; highlightTxId marks only that row', async () => {
        answer(
            () => [],
            () => [FEE_11(), TAX_12()],
        );
        const onOpenTransaction = vi.fn();
        mount({mode: 'view', items: [PARENT_10()], onOpenTransaction, highlightTxId: 11});

        await waitForSavedRows([11, 12]);
        expect(rowById(11)).toHaveAttribute('data-highlighted', 'true');
        expect(rowById(12)).toHaveAttribute('data-highlighted', 'false');
        await fireEvent.click(screen.getByTestId('tx-form-charge-open-saved-11'));
        expect(onOpenTransaction).toHaveBeenCalledTimes(1);
        expect(onOpenTransaction).toHaveBeenCalledWith(11);
    });

    it('view mode without onOpenTransaction: no charge Open buttons', async () => {
        answer(
            () => [],
            () => [FEE_11(), TAX_12()],
        );
        mount({mode: 'view', items: [PARENT_10()]});

        await waitForSavedRows([11, 12]);
        expect(screen.queryByTestId('tx-form-charge-open-saved-11')).toBeNull();
        expect(screen.queryByTestId('tx-form-charge-open-saved-12')).toBeNull();
    });

    // 6
    it('unsaved changes: Open asks to discard first; confirming opens, cancelling does nothing', async () => {
        answer(
            () => [],
            () => [FEE_11(), TAX_12()],
        );
        const onOpenTransaction = vi.fn();
        const first = bulkHosted(vi.fn(), PARENT_10(), {onOpenTransaction});
        await waitForSavedRows([11, 12]);

        await fireEvent.click(screen.getByTestId('tx-form-charges-add-FEE'));
        await waitFor(() => expect(newRows()).toHaveLength(1));
        await fireEvent.click(screen.getByTestId('tx-form-charge-open-saved-11'));

        const confirm = await screen.findByTestId('confirm-modal-confirm');
        expect(onOpenTransaction).not.toHaveBeenCalled();
        await fireEvent.click(confirm);
        expect(onOpenTransaction).toHaveBeenCalledTimes(1);
        expect(onOpenTransaction).toHaveBeenCalledWith(11);
        expect(first.onClose).not.toHaveBeenCalled();
        cleanup();

        const cancelled = vi.fn();
        const second = bulkHosted(vi.fn(), PARENT_10(), {onOpenTransaction: cancelled});
        await waitForSavedRows([11, 12]);
        await fireEvent.click(screen.getByTestId('tx-form-charges-add-FEE'));
        await waitFor(() => expect(newRows()).toHaveLength(1));
        await fireEvent.click(screen.getByTestId('tx-form-charge-open-saved-11'));
        await fireEvent.click(await screen.findByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());
        expect(cancelled).not.toHaveBeenCalled();
        expect(second.onClose).not.toHaveBeenCalled();
        expect(newRows()).toHaveLength(1);
    });

    // 7
    it('Bulk-hosted charge: Unlink marks it unlinked, makes the form dirty, and Apply carries _parent_unlink', async () => {
        answer(() => [PARENT_10()]);
        const onPushDraft = vi.fn();
        const {onClose} = mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, allowChargeEdits: true, onPushDraft, onOpenTransaction: vi.fn(), items: [FEE_ROW()]});

        await waitFor(() => expect(screen.getByTestId('tx-form-parent')).toHaveAttribute('data-state', 'ready'));
        await fireEvent.click(screen.getByTestId('tx-form-parent-unlink'));

        await waitFor(() => expect(screen.getByTestId('tx-form-parent')).toHaveAttribute('data-state', 'unlinked'));
        expect(screen.getByTestId('tx-form-parent-unlinked')).toBeInTheDocument();
        expect(screen.queryByTestId('tx-form-parent-open')).toBeNull();
        expect(screen.queryByTestId('tx-form-parent-unlink')).toBeNull();

        await fireEvent.click(screen.getByTestId('tx-form-cancel'));
        await screen.findByTestId('confirm-modal-confirm');
        expect(onClose).not.toHaveBeenCalled();
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());

        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        expect(onPushDraft.mock.calls[0][0]).toMatchObject({_parent_unlink: true});
    });

    it('without allowChargeEdits: no Unlink and the payload has no _parent_unlink', async () => {
        answer(() => [PARENT_10()]);
        const onPushDraft = vi.fn();
        mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, onPushDraft, items: [FEE_ROW()]});

        await waitFor(() => expect(screen.getByTestId('tx-form-parent')).toHaveAttribute('data-state', 'ready'));
        expect(screen.queryByTestId('tx-form-parent-unlink')).toBeNull();
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        expect(onPushDraft.mock.calls[0][0]).not.toHaveProperty('_parent_unlink');
    });

    // 8
    it('a late parent answer for the previous row is ignored', async () => {
        const late = deferred<unknown[]>();
        answer((ids) => (ids[0] === 10 ? late.promise : [txRow({id: 20, type: 'SELL', quantity: '-1', cash: {code: 'EUR', amount: '100'}})]));

        const {rerender} = mount({mode: 'view', items: [FEE_ROW(10)], openKey: 0});
        await waitFor(() => expect(idsCalls()).toHaveLength(1));

        await rerender({open: true, openKey: 1, items: [txRow({id: 31, type: 'FEE', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '-1'}, parent_transaction_id: 20})]});
        await waitFor(() => expect(screen.getByTestId('tx-form-parent')).toHaveAttribute('data-state', 'ready'));
        expect(parentBox()).toHaveAttribute('data-parent-id', '20');

        late.resolve([PARENT_10()]);
        for (let i = 0; i < 5; i++) await tick();

        expect(parentBox()).toHaveAttribute('data-parent-id', '20');
        expect(parentBox()).toHaveAttribute('data-state', 'ready');
        expect(screen.getByTestId('tx-form-parent-summary')).toHaveTextContent('#20');
        expect(screen.getByTestId('tx-form-parent-summary')).not.toHaveTextContent('#10');
    });
});

// ---------------------------------------------------------------------------------------------------------------
//  TL-11 — a charge under a NEW parent of the Bulk. The Bulk hands `_newParent: {key: 'op-<tempId>', ref, row}` on the
//  charge's item: the section shows that row (no server read), named by `ref`, with «Open» (`onOpenRow('<tempId>')`) and
//  «Unlink» (`_parent_unlink: true`). With a saved parent nothing changes. RED until `_newParent` / `onOpenRow` exist.
//
//  The discard question's testids are the ConfirmModal's own (`confirm-modal-confirm` / `confirm-modal-cancel`).
// ---------------------------------------------------------------------------------------------------------------

/** A new BUY of the Bulk as it hands it to the charge's form: no id, signed as the ledger. */
const NEW_PARENT = () => ({key: 'op-n-buy', ref: 'row 4', row: txRow({id: 0, date: '2024-05-17', cash: {code: 'EUR', amount: '-137'}, description: 'new buy'})});

/** A new FEE of the Bulk (no id), under a new parent unless `over` says otherwise. */
const newFee = (over: Record<string, unknown> = {}) => txRow({id: 0, type: 'FEE', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '-2'}, description: 'new fee', _newParent: NEW_PARENT(), ...over});

/** The form as the Bulk hosts it on a new row (`mode: 'create'` with the row handed). */
function bulkNewRow(row: Record<string, unknown>, extra: Record<string, unknown> = {}) {
    const onPushDraft = vi.fn();
    const onOpenRow = vi.fn();
    const onOpenTransaction = vi.fn();
    return {onPushDraft, onOpenRow, onOpenTransaction, ...mount({mode: 'create', commitOnSave: false, allowChargeEdits: true, onPushDraft, onOpenRow, onOpenTransaction, items: [row], ...extra})};
}

/** The section shows the handed new parent: the barrier of every case below. */
async function showsNewParent() {
    await waitFor(() => expect(screen.getByTestId('tx-form-parent'), '66 TL-11: the form does not show the new parent it was handed').toHaveAttribute('data-state', 'ready'));
    expect(parentBox()).toHaveAttribute('data-parent-key', 'op-n-buy');
}

async function applyAndRead(onPushDraft: ReturnType<typeof vi.fn>): Promise<Record<string, unknown>> {
    await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
    await fireEvent.click(screen.getByTestId('tx-form-save'));
    expect(onPushDraft).toHaveBeenCalledTimes(1);
    return onPushDraft.mock.calls[0][0] as Record<string, unknown>;
}

describe('TransactionFormModal — a charge under a new parent of the Bulk (66 TL-11)', () => {
    beforeAll(async () => {
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_WITH_CHARGE_ROLES);
        await setupI18n();
        await ensureTypesLoaded();
    });

    beforeEach(() => {
        queryApi().mockReset();
        queryApi().mockImplementation(async () => []);
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    it('the new parent is shown from the handed row, named by its ref, with no server read and no «Link to a transaction…»', async () => {
        bulkNewRow(newFee());

        await showsNewParent();
        expect(parentBox(), 'a new row has no id').toHaveAttribute('data-parent-id', '');
        const summary = screen.getByTestId('tx-form-parent-summary');
        expect(summary, 'named by its ref').toHaveTextContent('row 4');
        expect(summary, 'never by an id').not.toHaveTextContent('#');
        expect(summary, 'its date').toHaveTextContent('2024-05-17');
        expect(summary, 'its amount').toHaveTextContent(/137/);
        expect(screen.queryByTestId('tx-form-parent-link'), 'a linked charge offers no other parent').toBeNull();
        expect(idsCalls(), 'no read by id').toHaveLength(0);
        expect(queryApi(), 'no read at all').not.toHaveBeenCalled();
    });

    it('a SAVED charge linked under a new parent here is shown the same way (its own id is not the parent’s)', async () => {
        const onOpenRow = vi.fn();
        mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, allowChargeEdits: true, onPushDraft: vi.fn(), onOpenRow, onOpenTransaction: vi.fn(), items: [{...FEE_ROW(null), _newParent: NEW_PARENT()}]});

        await showsNewParent();
        expect(parentBox()).toHaveAttribute('data-parent-id', '');
        expect(screen.getByTestId('tx-form-parent-summary')).toHaveTextContent('row 4');
        expect(screen.queryByTestId('tx-form-parent-link')).toBeNull();
        expect(idsCalls()).toHaveLength(0);
    });

    it('«Open» asks the host for the new row (onOpenRow with its tempId), never for a saved id, and closes nothing', async () => {
        const {onOpenRow, onOpenTransaction, onClose} = bulkNewRow(newFee());
        await showsNewParent();

        await fireEvent.click(screen.getByTestId('tx-form-parent-open'));

        expect(onOpenRow).toHaveBeenCalledTimes(1);
        expect(onOpenRow.mock.calls[0][0]).toBe('n-buy');
        expect(onOpenTransaction).not.toHaveBeenCalled();
        expect(onClose).not.toHaveBeenCalled();
    });

    it('without onOpenRow there is no «Open» on a new parent, even with onOpenTransaction', async () => {
        bulkNewRow(newFee(), {onOpenRow: undefined});

        await showsNewParent();
        expect(screen.queryByTestId('tx-form-parent-open')).toBeNull();
        // The rest of the section is there: the absence is «Open»'s alone.
        expect(screen.getByTestId('tx-form-parent-unlink')).toBeInTheDocument();
    });

    it('«Unlink»: the state unlinked, no «Open», no «Unlink», no «Link to a transaction…»; the form is dirty; Apply carries _parent_unlink', async () => {
        const {onPushDraft, onClose} = bulkNewRow(newFee());
        await showsNewParent();

        await fireEvent.click(screen.getByTestId('tx-form-parent-unlink'));

        await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'unlinked'));
        expect(screen.getByTestId('tx-form-parent-unlinked')).toBeInTheDocument();
        for (const gone of ['tx-form-parent-open', 'tx-form-parent-unlink', 'tx-form-parent-link']) expect(screen.queryByTestId(gone), gone).toBeNull();

        await fireEvent.click(screen.getByTestId('tx-form-cancel'));
        await screen.findByTestId('confirm-modal-confirm');
        expect(onClose).not.toHaveBeenCalled();
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());

        const payload = await applyAndRead(onPushDraft);
        expect(payload._parent_unlink).toBe(true);
        expect(payload).not.toHaveProperty('_parent_link');
    });

    it('nothing touched: Apply carries no _parent_unlink, and closing asks nothing', async () => {
        const first = bulkNewRow(newFee());
        await showsNewParent();
        await fireEvent.click(screen.getByTestId('tx-form-cancel'));
        expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull();
        expect(first.onClose).toHaveBeenCalledTimes(1);
        cleanup();

        const second = bulkNewRow(newFee());
        await showsNewParent();
        expect(await applyAndRead(second.onPushDraft)).not.toHaveProperty('_parent_unlink');
    });

    it('not editable (no allowChargeEdits, then a read-only form): the new parent is shown with no «Unlink»', async () => {
        bulkNewRow(newFee(), {allowChargeEdits: false});
        await showsNewParent();
        expect(screen.queryByTestId('tx-form-parent-unlink')).toBeNull();
        cleanup();

        bulkNewRow(newFee(), {mode: 'view'});
        await showsNewParent();
        expect(screen.queryByTestId('tx-form-parent-unlink')).toBeNull();
    });

    it('unsaved changes: «Open» asks to discard first; Cancel keeps everything, confirming navigates', async () => {
        const {onOpenRow, onClose} = bulkNewRow(newFee());
        await showsNewParent();
        await typeInto('tx-form-cash-amount', '9');

        await fireEvent.click(screen.getByTestId('tx-form-parent-open'));
        await screen.findByTestId('confirm-modal-confirm');
        expect(onOpenRow).not.toHaveBeenCalled();
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());
        expect(onOpenRow).not.toHaveBeenCalled();
        expect(onClose).not.toHaveBeenCalled();
        expect(screen.getByTestId('tx-form-cash-amount'), 'the amount typed is kept').toHaveDisplayValue(/^9/);
        expect(parentBox()).toHaveAttribute('data-state', 'ready');

        await fireEvent.click(screen.getByTestId('tx-form-parent-open'));
        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));
        expect(onOpenRow).toHaveBeenCalledTimes(1);
        expect(onOpenRow.mock.calls[0][0]).toBe('n-buy');
        expect(onClose).not.toHaveBeenCalled();
    });

    it('an «Open» cancelled at the question is forgotten: a later Cancel, discarded, closes and does not navigate', async () => {
        const {onOpenRow, onClose} = bulkNewRow(newFee());
        await showsNewParent();
        await typeInto('tx-form-cash-amount', '9');
        await fireEvent.click(screen.getByTestId('tx-form-parent-open'));
        await fireEvent.click(await screen.findByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());

        await fireEvent.click(screen.getByTestId('tx-form-cancel'));
        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));

        expect(onClose).toHaveBeenCalledTimes(1);
        expect(onOpenRow).not.toHaveBeenCalled();
    });

    // --- guards, green before and after ---

    it('guard: a saved parent is unchanged — read by id, named by #id, «Open» by id, no data-parent-key of a new row', async () => {
        answer(() => [PARENT_10()]);
        const onOpenRow = vi.fn();
        const onOpenTransaction = vi.fn();
        mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, allowChargeEdits: true, onPushDraft: vi.fn(), onOpenRow, onOpenTransaction, items: [FEE_ROW()]});

        await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'ready'));
        expect(parentBox()).toHaveAttribute('data-parent-id', '10');
        expect(parentBox().getAttribute('data-parent-key') ?? '', 'no new row').not.toMatch(/^op-/);
        expect(screen.getByTestId('tx-form-parent-summary')).toHaveTextContent('#10');
        expect(idsCalls()).toHaveLength(1);
        await fireEvent.click(screen.getByTestId('tx-form-parent-open'));
        expect(onOpenTransaction).toHaveBeenCalledWith(10);
        expect(onOpenRow).not.toHaveBeenCalled();
    });

    it('guard: a charge with no parent at all still offers «Link to a transaction…»', async () => {
        bulkNewRow(newFee({_newParent: undefined}));

        await waitFor(() => expect(screen.getByTestId('tx-form-parent')).toHaveAttribute('data-state', 'empty'));
        expect(screen.getByTestId('tx-form-parent-link')).toBeInTheDocument();
        expect(screen.queryByTestId('tx-form-parent-unlink')).toBeNull();
        expect(screen.queryByTestId('tx-form-parent-open')).toBeNull();
    });
});
