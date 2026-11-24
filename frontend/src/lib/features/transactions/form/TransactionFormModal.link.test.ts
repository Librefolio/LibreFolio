// @vitest-environment jsdom
/**
 * TransactionFormModal — the two pickers (project 66, lot F4). RED FIRST: `tx-form-charges-link-existing`,
 * `tx-form-parent-link`, `linkNew` and the picker's `rows` / `maxSelect` props do not exist yet.
 *
 * Contract: 66-F4-contract.md sections 3 and 4. data-testid and data-* only. The transactions query answers
 * `queries.without_parent` (candidates for a parent's charges) and `queries.types` (candidates for a charge's parent).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {ensureTypesLoaded} from '$lib/features/transactions/transactionTypeStore';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
import {notify} from '$lib/stores/app/notify.svelte';
import {mergeAssets, resetAssetStore} from '$lib/stores/reference/assetStore';

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
    // The picker disables the rows of a broker the user cannot edit; the broker store is empty here.
    canEditBroker: vi.fn(() => true),
    canEditPaired: vi.fn(() => true),
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
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));
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
/** Presence barrier for absences: the form itself is on screen and settled enough to show its fields. Not the Save
 *  button: a read-only form has none. */
async function formIsUp() {
    await screen.findByTestId('tx-form-body');
    await screen.findByTestId('tx-form-cash-wrap');
}

// ---------------------------------------------------------------------------------------------------------------
//  F4 fixtures and helpers
// ---------------------------------------------------------------------------------------------------------------

/** The parent types as the types table of this file declares them (`charge_role` 'parent'): the form reads them from the table. */
const PARENT_TYPES = TYPES_WITH_CHARGE_ROLES.transaction_types.filter((type) => type.charge_role === 'parent').map((type) => type.code);

/** A charge row (FEE) with its own asset, as the candidates endpoint returns it. */
const charge = (id: number, assetId: number | null, extra: Record<string, unknown> = {}) => txRow({id, broker_id: 1, asset_id: assetId, type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-2'}, parent_transaction_id: null, ...extra});

/** A parent candidate. */
const parentRow = (id: number, assetId: number | null, extra: Record<string, unknown> = {}) => txRow({id, broker_id: 1, asset_id: assetId, type: 'BUY', ...extra});

/**
 * Answers `without_parent` (candidates for a charge), `types` (candidates for a parent), and `parent_ids` (the linked
 * charges of the parent). A candidates answer may be a function that throws or rejects.
 */
function answerPickers(opts: {linked?: unknown[]; withoutParent?: () => unknown; parents?: () => unknown}) {
    queryApi().mockImplementation((async (arg: {queries: {without_parent?: boolean; types?: string[]; parent_ids?: number[]; ids?: number[]}}) => {
        if (arg.queries.without_parent) return opts.withoutParent ? opts.withoutParent() : [];
        if (arg.queries.types) return opts.parents ? opts.parents() : [];
        if (arg.queries.parent_ids) return opts.linked ?? [];
        return [];
    }) as never);
}

const callsWith = (key: 'without_parent' | 'types') => queryApi().mock.calls.filter((c) => (c[0] as {queries: Record<string, unknown>}).queries[key] !== undefined);

const picker = () => within(screen.getByTestId('tx-picker-modal'));
/** The ids of the rows the open picker offers (the table prefixes its row ids with `tx-`). */
const pickerIds = () =>
    picker()
        .queryAllByTestId(/^dt-row-checkbox-tx-/)
        .map((el) => Number((el.getAttribute('data-testid') as string).replace('dt-row-checkbox-tx-', '')))
        .sort((a, b) => a - b);

async function waitForPickerIds(ids: number[]) {
    await waitFor(() => expect(pickerIds()).toEqual(ids));
}

async function pickRow(id: number) {
    await fireEvent.click(await picker().findByTestId(`dt-row-checkbox-tx-${id}`));
    await waitFor(() => expect(picker().getByTestId(`dt-row-checkbox-tx-${id}`)).toHaveAttribute('data-state', 'checked'));
}

const parentBox = () => screen.getByTestId('tx-form-parent');

describe('TransactionFormModal — the two pickers (66 F4)', () => {
    beforeAll(async () => {
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_WITH_CHARGE_ROLES);
        await setupI18n();
        await ensureTypesLoaded();
    });

    beforeEach(() => {
        queryApi().mockReset();
        queryApi().mockImplementation(async () => []);
        vi.mocked(notify).mockClear();
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    // 1
    it('parent side: Link an existing charge lists only same-asset unlinked charges, Add appends a linkNew row, Apply carries it', async () => {
        answerPickers({
            linked: [charge(11, 5, {parent_transaction_id: 10})],
            withoutParent: () => [charge(21, 5), charge(22, null), charge(23, 9), charge(11, 5)],
        });
        const onPushDraft = vi.fn();
        bulkHosted(onPushDraft, txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 1}));
        await waitForSavedRows([11]);

        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));

        await waitForPickerIds([21]);
        expect(callsWith('without_parent')).toHaveLength(1);
        expect(callsWith('without_parent')[0][0]).toMatchObject({queries: {without_parent: true, broker_id: 1}});
        expect(screen.getByTestId('tx-picker-filter-label')).toBeInTheDocument();

        await pickRow(21);
        await fireEvent.click(screen.getByTestId('tx-picker-add'));

        await waitFor(() => expect(rowById(21)).toBeDefined());
        expect(rowById(21)).toHaveAttribute('data-charge-key', 'saved-21');
        expect(rowById(11)).toBeDefined();
        await waitFor(() => expect(screen.queryByTestId('tx-picker-modal')).toBeNull());

        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        const drafts = (onPushDraft.mock.calls[0][0] as {_charges: Array<Record<string, unknown>>})._charges;
        expect(drafts.find((d) => d.id === 21)).toMatchObject({id: 21, linkNew: true, state: 'linked'});
        expect(drafts.find((d) => d.id === 11)?.linkNew).toBeFalsy();
    });

    // 2
    it('a parent without an asset is offered only the charges without an asset', async () => {
        answerPickers({withoutParent: () => [charge(21, null), charge(22, 5, {type: 'TAX'}), charge(23, 9)]});
        bulkHosted(vi.fn(), txRow({id: 10, broker_id: 1, asset_id: null, type: 'DEPOSIT', quantity: '0', cash: {code: 'EUR', amount: '100'}, charges_count: 0}));

        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));

        await waitForPickerIds([21]);
    });

    // 3
    it('a failed candidates fetch raises the notification and opens no picker', async () => {
        answerPickers({
            withoutParent: () => {
                throw new Error('boom');
            },
        });
        bulkHosted(vi.fn(), txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 0}));

        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));

        await waitFor(() => expect(notify).toHaveBeenCalledWith(expect.objectContaining({name: 'tx.form.charges.candidates.failed'})));
        expect(screen.queryByTestId('tx-picker-modal')).toBeNull();
    });

    // 4
    it('read-only, or without allowChargeEdits: no Link an existing charge', async () => {
        answerPickers({linked: [charge(11, 5, {parent_transaction_id: 10})]});
        const parent = () => txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 1});

        mount({mode: 'view', items: [parent()], onOpenTransaction: vi.fn()});
        await waitForSavedRows([11]);
        expect(screen.queryByTestId('tx-form-charges-link-existing')).toBeNull();
        cleanup();

        mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, onPushDraft: vi.fn(), items: [parent()]});
        await waitForSavedRows([11]);
        expect(screen.queryByTestId('tx-form-charges-link-existing')).toBeNull();
    });

    // 5
    it('charge side: Link to a transaction lists only same-asset unpaired parents, one pick, Undo, and Apply carries _parent_link', async () => {
        answerPickers({
            parents: () => [parentRow(10, 5), parentRow(12, 5, {type: 'SELL'}), parentRow(40, 5, {type: 'DEPOSIT', related_transaction_id: 41}), parentRow(11, 9)],
        });
        const onPushDraft = vi.fn();
        const fee = txRow({id: 30, broker_id: 1, asset_id: 5, type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-2'}, parent_transaction_id: null});
        mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, allowChargeEdits: true, onPushDraft, items: [fee]});

        await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'empty'));
        await fireEvent.click(screen.getByTestId('tx-form-parent-link'));

        await waitForPickerIds([10, 12]);
        expect(callsWith('types')).toHaveLength(1);
        const queries = (callsWith('types')[0][0] as {queries: {broker_id: number; types: string[]}}).queries;
        expect(queries.broker_id).toBe(1);
        expect([...queries.types].sort()).toEqual([...PARENT_TYPES].sort());
        expect(screen.getByTestId('tx-picker-filter-label')).toBeInTheDocument();

        // maxSelect 1: two selected → Add disabled
        await pickRow(10);
        await pickRow(12);
        await waitFor(() => expect(screen.getByTestId('tx-picker-add')).toBeDisabled());
        await fireEvent.click(picker().getByTestId('dt-row-checkbox-tx-12'));
        await waitFor(() => expect(screen.getByTestId('tx-picker-add')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-picker-add'));

        await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'pending'));
        expect(parentBox()).toHaveAttribute('data-parent-id', '10');
        expect(screen.getByTestId('tx-form-parent-summary')).toHaveTextContent('#10');
        await waitFor(() => expect(screen.queryByTestId('tx-picker-modal')).toBeNull());

        // Undo → empty again, then link again
        await fireEvent.click(screen.getByTestId('tx-form-parent-link-undo'));
        await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'empty'));
        expect(screen.queryByTestId('tx-form-parent-link-undo')).toBeNull();

        await fireEvent.click(screen.getByTestId('tx-form-parent-link'));
        await pickRow(10);
        await fireEvent.click(screen.getByTestId('tx-picker-add'));
        await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'pending'));

        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        expect(onPushDraft.mock.calls[0][0]).toMatchObject({_parent_link: 10});
    });

    it('charge side: a failed candidates fetch raises the notification and opens no picker', async () => {
        answerPickers({
            parents: () => {
                throw new Error('boom');
            },
        });
        const fee = txRow({id: 30, broker_id: 1, asset_id: 5, type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-2'}, parent_transaction_id: null});
        mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, allowChargeEdits: true, onPushDraft: vi.fn(), items: [fee]});

        await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'empty'));
        await fireEvent.click(screen.getByTestId('tx-form-parent-link'));

        await waitFor(() => expect(notify).toHaveBeenCalledWith(expect.objectContaining({name: 'tx.form.parent.candidates.failed'})));
        expect(screen.queryByTestId('tx-picker-modal')).toBeNull();
        expect(parentBox()).toHaveAttribute('data-state', 'empty');
    });

    // 6
    it('view mode: a FEE without a parent shows no Linked to section at all', async () => {
        mount({mode: 'view', items: [txRow({id: 30, broker_id: 1, asset_id: 5, type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-2'}, parent_transaction_id: null})]});

        await formIsUp();
        expect(screen.queryByTestId('tx-form-parent')).toBeNull();
        expect(screen.queryByTestId('tx-form-parent-link')).toBeNull();
    });

    // ---------------------------------------------------------------------------------------------------------------
    //  F4b: a picked charge taken out again, and a pending parent dropped when its premise changes
    // ---------------------------------------------------------------------------------------------------------------

    /** Parent 10 (broker 1, asset 5) with no charges, the picker offering charge 21; 21 picked and added to the section. */
    async function pickChargeIntoParent(onPushDraft = vi.fn()) {
        answerPickers({withoutParent: () => [charge(21, 5)]});
        const mounted = bulkHosted(onPushDraft, txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 0}));
        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));
        await waitForPickerIds([21]);
        await pickRow(21);
        await fireEvent.click(screen.getByTestId('tx-picker-add'));
        await waitFor(() => expect(rowById(21)).toBeDefined());
        await waitFor(() => expect(screen.queryByTestId('tx-picker-modal')).toBeNull());
        return mounted;
    }

    async function applyDrafts(onPushDraft: ReturnType<typeof vi.fn>): Promise<Array<Record<string, unknown>>> {
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        return (onPushDraft.mock.calls[0][0] as {_charges: Array<Record<string, unknown>>})._charges;
    }

    /** Open «Link an existing charge…» again: the charge taken out of the section is a candidate once more. */
    async function expectOfferedAgain(id: number) {
        await fireEvent.click(screen.getByTestId('tx-form-charges-link-existing'));
        await screen.findByTestId('tx-picker-modal');
        await waitForPickerIds([id]);
    }

    for (const action of ['unlink', 'remove'] as const) {
        it(`parent side: a picked charge taken out with ${action} leaves no draft at all in _charges`, async () => {
            const onPushDraft = vi.fn();
            await pickChargeIntoParent(onPushDraft);

            await fireEvent.click(screen.getByTestId(`tx-form-charge-${action}-saved-21`));
            await waitFor(() => expect(rowById(21)).toBeUndefined());

            const drafts = await applyDrafts(onPushDraft);
            expect(drafts.filter((d) => d.id === 21)).toEqual([]);
        });

        it(`parent side: a picked charge taken out with ${action} is offered again by the picker`, async () => {
            await pickChargeIntoParent();

            await fireEvent.click(screen.getByTestId(`tx-form-charge-${action}-saved-21`));
            await waitFor(() => expect(rowById(21)).toBeUndefined());

            await expectOfferedAgain(21);
        });
    }

    it('parent side: pick one charge then unlink it → the form is clean again, closing asks no discard', async () => {
        const {onClose} = await pickChargeIntoParent();

        await fireEvent.click(screen.getByTestId('tx-form-charge-unlink-saved-21'));
        await waitFor(() => expect(rowById(21)).toBeUndefined());

        await fireEvent.click(screen.getByTestId('tx-form-close'));
        // Presence barrier: the close path answered one way or the other (closed, or asked to discard).
        await waitFor(() => expect(onClose.mock.calls.length > 0 || screen.queryByTestId('confirm-modal-confirm') !== null).toBe(true));
        expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull();
        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('charge side: a pending parent is dropped when the charge changes asset; Apply carries no _parent_link', async () => {
        resetAssetStore();
        mergeAssets([
            {id: 5, display_name: 'Link asset five', currency: 'EUR', quote_base_quantity: 1, active: true},
            {id: 9, display_name: 'Link asset nine', currency: 'EUR', quote_base_quantity: 1, active: true},
        ] as never);
        try {
            answerPickers({parents: () => [parentRow(10, 5)]});
            const onPushDraft = vi.fn();
            // Create mode: a new charge picks its asset (a saved row has it locked, #58).
            const fee = txRow({id: 30, broker_id: 1, asset_id: 5, type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-2'}, parent_transaction_id: null});
            mount({mode: 'create', commitOnSave: false, allowChargeEdits: true, onPushDraft, items: [fee]});

            await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'empty'));
            await fireEvent.click(screen.getByTestId('tx-form-parent-link'));
            await waitForPickerIds([10]);
            await pickRow(10);
            await fireEvent.click(screen.getByTestId('tx-picker-add'));
            await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'pending'));
            await waitFor(() => expect(screen.queryByTestId('tx-picker-modal')).toBeNull());

            const trigger = await screen.findByTestId('tx-form-asset-trigger');
            expect(trigger).toHaveAttribute('data-disabled', 'false');
            await fireEvent.click(trigger);
            const list = await screen.findByRole('listbox');
            await fireEvent.click(within(list).getByTestId('search-select-option-9'));
            await waitFor(() => expect(screen.queryByRole('listbox')).toBeNull());

            await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'empty'));

            await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
            await fireEvent.click(screen.getByTestId('tx-form-save'));
            expect(onPushDraft).toHaveBeenCalledTimes(1);
            expect(onPushDraft.mock.calls[0][0]).not.toHaveProperty('_parent_link');
        } finally {
            resetAssetStore();
        }
    });
});

// ---------------------------------------------------------------------------------------------------------------
//  TL-2 — inside the Bulk the charges picker sees the Bulk's rows. The Bulk passes `bulkCandidates(mode, probe)`:
//  `{rows, exclude}` (rows: mirrors of its candidates, signed as the ledger, a saved one by its txId, a new one by a
//  synthetic negative id with `_bulkKey: 'op-<tempId>'` and `_rowRef`), or null for nothing from the Bulk. The picker
//  shows the DB rows minus `exclude` minus the ids the Bulk's rows carry, plus the Bulk's rows, then today's filters
//  (same asset, not in the section by id or by `_bulkKey`). The ID cell shows `_rowRef` when present, `#id` otherwise.
//  RED until the prop exists.
// ---------------------------------------------------------------------------------------------------------------

/** A mirror of a Bulk row as `bulkCandidates` hands it: a charge row, with the Bulk's own key and reference. */
const bulkCharge = (id: number, assetId: number | null, bulk: {_bulkKey?: string; _rowRef?: string}, extra: Record<string, unknown> = {}) => ({...charge(id, assetId, extra), ...bulk});

/** The ID cell of the picker's row for transaction `id` (the table's row ids are `tx-<id>`). */
function pickerIdCell(id: number): HTMLElement | null {
    return screen.getByTestId('tx-picker-modal').querySelector<HTMLElement>(`tr[data-row-id="tx-${id}"] td[data-column-id="id"]`);
}

describe('TransactionFormModal — the charges picker inside the Bulk (66 TL-2)', () => {
    beforeAll(async () => {
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_WITH_CHARGE_ROLES);
        await setupI18n();
        await ensureTypesLoaded();
    });

    beforeEach(() => {
        queryApi().mockReset();
        queryApi().mockImplementation(async () => []);
        vi.mocked(notify).mockClear();
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    it('the picker merges the Bulk’s rows: DB minus exclude minus the Bulk’s ids, plus the Bulk’s rows, same asset, not in the section', async () => {
        answerPickers({
            linked: [charge(11, 5, {parent_transaction_id: 10})],
            withoutParent: () => [charge(21, 5), charge(22, 5), charge(23, 5), charge(24, 9)],
        });
        const bulkCandidates = vi.fn(() => ({
            rows: [bulkCharge(-7, 5, {_bulkKey: 'op-n-fee', _rowRef: 'row 4'}), bulkCharge(23, 5, {_rowRef: '#23'}, {description: 'the Bulk’s values of 23'}), bulkCharge(-8, 9, {_bulkKey: 'op-n-other', _rowRef: 'row 5'}), bulkCharge(11, 5, {_rowRef: '#11'})],
            exclude: [22],
        }));
        bulkHosted(vi.fn(), txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 1}), {bulkCandidates});
        await waitForSavedRows([11]);

        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));

        await waitForPickerIds([-7, 21, 23]);
        expect(bulkCandidates).toHaveBeenCalledWith('charges', expect.objectContaining({broker_id: 1, asset_id: 5, type: 'BUY'}));
        expect(callsWith('without_parent'), 'the DB is still read').toHaveLength(1);
    });

    it('the ID cell names a new Bulk row by its row reference, a saved one by #id', async () => {
        answerPickers({withoutParent: () => [charge(21, 5)]});
        const bulkCandidates = vi.fn(() => ({rows: [bulkCharge(-7, 5, {_bulkKey: 'op-n-fee', _rowRef: 'row 4'})], exclude: []}));
        bulkHosted(vi.fn(), txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 0}), {bulkCandidates});

        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));

        await waitForPickerIds([-7, 21]);
        expect(pickerIdCell(-7)?.textContent?.trim()).toBe('row 4');
        expect(pickerIdCell(21)?.textContent?.trim()).toBe('#21');
    });

    it('a new Bulk row picked joins the section as that row (op-<tempId>); Apply carries it without linkNew', async () => {
        answerPickers({withoutParent: () => []});
        const bulkCandidates = vi.fn(() => ({rows: [bulkCharge(-7, 5, {_bulkKey: 'op-n-fee', _rowRef: 'row 4'}, {description: 'bulk fee'})], exclude: []}));
        const onPushDraft = vi.fn();
        bulkHosted(onPushDraft, txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 0}), {bulkCandidates});

        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));
        await waitForPickerIds([-7]);
        await pickRow(-7);
        await fireEvent.click(screen.getByTestId('tx-picker-add'));
        await waitFor(() => expect(screen.queryByTestId('tx-picker-modal')).toBeNull());

        await waitFor(() => expect(rows().map((r) => r.getAttribute('data-charge-key'))).toEqual(['op-n-fee']));
        expect(rows()[0]).toHaveAttribute('data-charge-id', '');

        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        const drafts = (onPushDraft.mock.calls[0][0] as {_charges: Array<Record<string, unknown>>})._charges;
        expect(drafts).toHaveLength(1);
        expect(drafts[0]).toMatchObject({key: 'op-n-fee', id: null, state: 'linked', type: 'FEE', original: null});
        expect(drafts[0].linkNew).toBeFalsy();
    });

    it('a Bulk row already in the section (by its _bulkKey) is not offered again', async () => {
        answerPickers({withoutParent: () => [charge(21, 5)]});
        const handed = [{key: 'op-n-fee', id: null, type: 'FEE', cash: {amount: '2', code: 'EUR'}, description: '', original: null, state: 'linked'}];
        const bulkCandidates = vi.fn(() => ({rows: [bulkCharge(-7, 5, {_bulkKey: 'op-n-fee', _rowRef: 'row 4'}), bulkCharge(-8, 5, {_bulkKey: 'op-n-fee2', _rowRef: 'row 5'})], exclude: []}));
        bulkHosted(vi.fn(), {...txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 0}), _charges: handed}, {bulkCandidates});
        await waitFor(() => expect(rows().map((r) => r.getAttribute('data-charge-key'))).toEqual(['op-n-fee']));

        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));

        await waitForPickerIds([-8, 21]);
    });

    it('guard: bulkCandidates answering null leaves the DB rows exactly as today', async () => {
        answerPickers({withoutParent: () => [charge(21, 5), charge(22, 5), charge(23, 9)]});
        const bulkCandidates = vi.fn(() => null);
        bulkHosted(vi.fn(), txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 0}), {bulkCandidates});

        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));

        await waitForPickerIds([21, 22]);
        expect(pickerIdCell(21)?.textContent?.trim(), 'the picker’s ID cell names a saved row #id').toBe('#21');
    });

    it('a new Bulk row picked, then trashed before Apply: offered again, and Apply does not carry it', async () => {
        answerPickers({withoutParent: () => [charge(21, 5)]});
        const bulkCandidates = vi.fn(() => ({rows: [bulkCharge(-7, 5, {_bulkKey: 'op-n-fee', _rowRef: 'row 4'})], exclude: []}));
        const onPushDraft = vi.fn();
        bulkHosted(onPushDraft, txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 0}), {bulkCandidates});

        // A saved FEE picked and kept: the form has a change to apply, whatever the trash leaves behind.
        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));
        await waitForPickerIds([-7, 21]);
        await pickRow(21);
        await pickRow(-7);
        await fireEvent.click(screen.getByTestId('tx-picker-add'));
        await waitFor(() => expect(screen.queryByTestId('tx-picker-modal')).toBeNull());
        await waitFor(() =>
            expect(
                rows()
                    .map((r) => r.getAttribute('data-charge-key'))
                    .sort(),
            ).toEqual(['op-n-fee', 'saved-21']),
        );

        await fireEvent.click(screen.getByTestId('tx-form-charge-remove-op-n-fee'));
        await waitFor(() => expect(rows().map((r) => r.getAttribute('data-charge-key'))).toEqual(['saved-21']));

        // Out of the section, the Bulk's row is a candidate again.
        await fireEvent.click(screen.getByTestId('tx-form-charges-link-existing'));
        await waitForPickerIds([-7]);
        await fireEvent.click(screen.getByTestId('tx-picker-cancel'));
        await waitFor(() => expect(screen.queryByTestId('tx-picker-modal')).toBeNull());

        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        const drafts = (onPushDraft.mock.calls[0][0] as {_charges: Array<Record<string, unknown>>})._charges;
        expect(
            drafts.map((d) => d.key),
            'the trashed Bulk row is not in the answer: applyChargeDrafts leaves it where it is',
        ).toEqual(['saved-21']);
    });

    it('a row in both sources is the Bulk’s: picked, its draft carries the Bulk’s values, not the database’s', async () => {
        answerPickers({withoutParent: () => [charge(23, 5, {description: 'saved note of 23', cash: {code: 'EUR', amount: '-2'}})]});
        const bulkCandidates = vi.fn(() => ({rows: [bulkCharge(23, 5, {_rowRef: '#23'}, {description: 'Bulk note of 23', cash: {code: 'EUR', amount: '-7'}})], exclude: []}));
        const onPushDraft = vi.fn();
        bulkHosted(onPushDraft, txRow({id: 10, broker_id: 1, asset_id: 5, type: 'BUY', charges_count: 0}), {bulkCandidates});

        await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));
        await waitForPickerIds([23]);
        await pickRow(23);
        await fireEvent.click(screen.getByTestId('tx-picker-add'));
        await waitFor(() => expect(rowById(23)).toBeDefined());
        await waitFor(() => expect(screen.queryByTestId('tx-picker-modal')).toBeNull());

        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        const drafts = (onPushDraft.mock.calls[0][0] as {_charges: Array<Record<string, unknown>>})._charges;
        expect(drafts.find((d) => d.id === 23)).toMatchObject({id: 23, linkNew: true, state: 'linked', description: 'Bulk note of 23', cash: {amount: '7', code: 'EUR'}});
    });
});
