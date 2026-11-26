// @vitest-environment jsdom
/**
 * TransactionBulkModal — component test (Vitest + jsdom): the editor's open lifecycle, lot K3a.
 *
 * Four defects of the `$effect` that sets the editor up when it opens (`open` → `resolveInitialRows` → `ops`), and of
 * the resets that rebuild those rows from the store:
 *
 *   K-4  The effect reads the language (`ensureCurrenciesLoaded($currentLanguage)`, in its async IIFE but before the
 *        first `await`), so it tracks it: a language change runs it again, and it rebuilds `ops` from the intent. Every
 *        unsaved edit in the editor is gone, without a word. Cure: the language is read with `untrack`.
 *   K-2  With the types not loaded yet when the editor opens (`isTypesLoaded()` false: the slow path), it opens the
 *        Form (no rows, any intent but import) or the import wizard (import intent) at once, and when the load ends it
 *        calls `scheduleAutoOpen` again whenever the Form is closed: what the user closed meanwhile opens again. Cure:
 *        the auto-open after the load runs only when nothing was opened early. The guard: with rows and a one-row edit
 *        intent nothing opens early, so the Form still opens on that row once the load ends.
 *   K-3  `resetAll` maps every saved row through `editOpFromTx`, the W4b placeholder too: the half of a pair that lives
 *        on a broker the user cannot read (`inaccessible`, built by `collapsePairedOps`). It is not in the store, so
 *        `editOpFromTx` reads `undefined` and throws. `resetRow` already skips it. Cure: the same guard in `resetAll`.
 *   K-3b After a reset, `collapsePairedOps` pairs the rows again (pass 1) by direction: the sender stays on screen, the
 *        receiver becomes its hidden partner. The placeholder's cash is unknown and reads 0, so when the readable half
 *        is the receiver it is the one hidden — behind a placeholder that still points at the readable half's old row —
 *        and the pair leaves the screen. Cure: a placeholder found in the batch always becomes the hidden partner of the
 *        readable half, whatever the direction, as the first build does (pass 2).
 *
 * And one regression guard, green: C-46, moved here from the E2E PC5 (tx-bulk-promote-cost-basis.spec.ts) when B-48
 * made its quantities impossible to type into the form. Two legs opposite as doubles and not as decimals are never
 * offered as a merge by the selection toolbar; the rows are brought in the way an import brings them.
 *
 * The editor is the subject, so its two nested modals are probes (the pattern of ImportWizardModal.test.ts): each
 * records the props the editor hands it — live getters, so `probe.form.open` reads the editor's own `formOpen` — and
 * renders nothing. A probe's `onClose`/`onPushDraft`/`onImportBatch` is the very callback the real modal calls on
 * Cancel, on Apply and on a finished import. The network is stubbed at its edge: the reference loaders resolve, the
 * types are a real TXTypesResponse loaded once through the real store, and K-2 holds the types load with a gate it
 * resolves itself. The language store is a plain writable, as the app's store is to a component that reads
 * `$currentLanguage`.
 *
 * Rows are found by the transaction id the grid shows (`#91101`) or by the description the test itself gave them, never
 * by position; asserted are `data-testid`, `data-status`, `data-state` and the test's own values — never a translated
 * label.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
import {flushSync, tick} from 'svelte';
import {get, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {_} from '$lib/i18n';
import {schemas} from '$lib/api/generated';
import {currentLanguage} from '$lib/stores/app/language';
import {ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
import {ensureTypesLoaded, getTypeRule, isTypesLoaded} from '$lib/features/transactions/transactionTypeStore';
import {txStoreGet, txStoreInvalidate, txStoreSetAll} from '$lib/features/transactions/txStore.svelte';
import {mergeBrokers, resetBrokerStore} from '$lib/stores/reference/brokerStore';
import type {TransactionCreateItem} from '$lib/types';
import type {TXReadItem} from '../types';
import type {ChargeDraft} from '../form/txCharges';

const {probe, typesLoad} = vi.hoisted(() => ({
    /** The props the editor hands its two nested modals, recorded at mount. */
    probe: {
        form: null as Record<string, unknown> | null,
        wizard: null as Record<string, unknown> | null,
        /** 66 F7-c1: the two TransactionPickerModal the editor mounts («Search & add», and the suggest picker, which
         *  receives `includeIds`), in mount order. */
        pickers: [] as Record<string, unknown>[],
    },
    /** K-2: `slow` makes the editor open on the slow path, `gate` holds its types load until the test resolves it. */
    typesLoad: {
        slow: false,
        gate: null as Promise<void> | null,
    },
}));

vi.mock('../form/TransactionFormModal.svelte', () => ({
    default: (_anchor: unknown, props: Record<string, unknown>) => {
        probe.form = props;
        return {};
    },
}));
// 66 F7-c1: the add-rows picker is a probe too; its `onAdd` is the editor's own handler (`handlePickerAdd`). No case
// before F7-c1 opens it.
vi.mock('./TransactionPickerModal.svelte', () => ({
    default: (_anchor: unknown, props: Record<string, unknown>) => {
        probe.pickers.push(props);
        return {};
    },
}));
vi.mock('../import/ImportWizardModal.svelte', () => ({
    default: (_anchor: unknown, props: Record<string, unknown>) => {
        probe.wizard = props;
        return {};
    },
}));
// W-B87: the possible-split banner links an existing event through the shared AssetEventPicker; its stand-in publishes the
// props it is given and answers event 555 (`$test/harness/AssetEventPickerStub.svelte`). Nothing else of the editor draws one:
// the Form that does is the probe above.
vi.mock('$lib/features/transactions/events/AssetEventPicker.svelte', async () => ({default: (await import('$test/harness/AssetEventPickerStub.svelte')).default}));

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
vi.mock('$lib/features/transactions/transactionTypeStore', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/transactions/transactionTypeStore')>();
    return {
        ...actual,
        isTypesLoaded: vi.fn(() => !typesLoad.slow && actual.isTypesLoaded()),
        ensureTypesLoaded: vi.fn(() => typesLoad.gate ?? actual.ensureTypesLoaded()),
    };
});
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    // `show` is what `notify()` calls for its toast (66 F7-c1: the charges read that fails raises an error toast).
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn(), show: vi.fn()},
}));
vi.mock('$lib/features/transactions/txCommitApi', () => ({
    commitTransactions: vi.fn(async () => ({committed: true, results: [], issues: []})),
    validateTransactions: vi.fn(async () => ({committed: true, issues: [], rawResponse: {wac_results: []}})),
}));
// The editor queues and dismisses its guides; the controller's persistence and replay are covered by its own tests.
vi.mock('$lib/features/onboarding/onboardingGuide.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/features/onboarding/onboardingGuide.svelte')>()),
    onboardingGuide: {
        active: null,
        queuedGuides: [],
        queueContextual: vi.fn(),
        clearQueued: vi.fn(),
        maybeStartQueued: vi.fn(() => false),
        dismissHost: vi.fn(),
        startImportAt: vi.fn(() => false),
    },
}));

import TransactionBulkModal, {type WorkspaceIntent} from './TransactionBulkModal.svelte';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/** TRANSFER's pair constraints, as TX_TYPE_METADATA declares them for `promote_from` and `pair_field_constraints`. */
const TRANSFER_CONSTRAINTS = [
    {field: 'asset_id', relation: 'equal'},
    {field: 'broker_id', relation: 'different'},
    {field: 'quantity', relation: 'opposite'},
];

/** CASH_TRANSFER's pair constraints, as TX_TYPE_METADATA declares them for `promote_from` and `pair_field_constraints`. */
const CASH_TRANSFER_CONSTRAINTS = [
    {field: 'cash_currency', relation: 'equal'},
    {field: 'broker_id', relation: 'different'},
    {field: 'cash_amount', relation: 'opposite'},
];

/** The types these cases use, shaped as the backend declares them (TX_TYPE_METADATA). */
const TYPES_RESPONSE = schemas.TXTypesResponse.parse({
    transaction_types: [
        {
            code: 'BUY',
            name: 'Buy',
            description: 'Purchase asset with cash',
            icon_slug: 'buy',
            doc_slug: 'buy-sell',
            asset_mode: 'required',
            cash_mode: 'required',
            quantity_mode: 'required',
            requires_link: false,
            quantity_sign: 'positive',
            cash_sign: 'negative',
            event_compatible: false,
            cost_basis_mode: 'forbidden',
            charge_role: 'parent',
        },
        // 66 F7-b: the two charge types, as TX_TYPE_METADATA declares them. Without them a FEE or a TAX row reads the
        // fallback rule, and the sign of its cash in a body would mean nothing.
        {
            code: 'FEE',
            name: 'Fee',
            description: 'Fee or commission (trading or account)',
            icon_slug: 'fee',
            doc_slug: 'fee',
            asset_mode: 'optional',
            cash_mode: 'required',
            quantity_mode: 'forbidden',
            requires_link: false,
            quantity_sign: 'zero',
            cash_sign: 'negative',
            event_compatible: false,
            charge_role: 'charge',
        },
        {
            code: 'TAX',
            name: 'Tax',
            description: 'Tax payment (capital gain or stamp duty)',
            icon_slug: 'tax',
            doc_slug: 'fee',
            asset_mode: 'optional',
            cash_mode: 'required',
            quantity_mode: 'forbidden',
            requires_link: false,
            quantity_sign: 'zero',
            cash_sign: 'negative',
            event_compatible: false,
            charge_role: 'charge',
        },
        {
            code: 'DEPOSIT',
            name: 'Deposit',
            description: 'Add cash to broker account',
            icon_slug: 'deposit',
            doc_slug: 'deposit-withdrawal',
            asset_mode: 'forbidden',
            cash_mode: 'required',
            quantity_mode: 'forbidden',
            requires_link: false,
            quantity_sign: 'zero',
            cash_sign: 'positive',
            event_compatible: false,
            swap_group: ['WITHDRAWAL'],
            // 66 C21: a parent of linked charges, as TX_TYPE_METADATA declares it.
            charge_role: 'parent',
        },
        {
            code: 'WITHDRAWAL',
            name: 'Withdrawal',
            description: 'Remove cash from broker account',
            icon_slug: 'withdrawal',
            doc_slug: 'deposit-withdrawal',
            asset_mode: 'forbidden',
            cash_mode: 'required',
            quantity_mode: 'forbidden',
            requires_link: false,
            quantity_sign: 'zero',
            cash_sign: 'negative',
            event_compatible: false,
            swap_group: ['DEPOSIT'],
            // 66 C21: a parent of linked charges, as TX_TYPE_METADATA declares it.
            charge_role: 'parent',
        },
        {
            code: 'CASH_TRANSFER',
            name: 'Cash Transfer',
            description: 'Wire transfer between brokers',
            icon_slug: 'cash-transfer',
            doc_slug: 'cash-transfer',
            asset_mode: 'forbidden',
            cash_mode: 'required',
            quantity_mode: 'forbidden',
            requires_link: true,
            quantity_sign: 'zero',
            cash_sign: 'nonzero',
            event_compatible: false,
            pair_form_layout: 'transfer_cash',
            split_into: {from_type: 'WITHDRAWAL', to_type: 'DEPOSIT'},
            // 66 C21: a WITHDRAWAL and a DEPOSIT on two brokers, same currency, amounts that cancel, as TX_TYPE_METADATA declares it.
            promote_from: [{type_a: 'WITHDRAWAL', type_b: 'DEPOSIT', field_constraints: CASH_TRANSFER_CONSTRAINTS}],
            pair_field_constraints: CASH_TRANSFER_CONSTRAINTS,
            swap_group: [],
        },
        {
            code: 'TRANSFER',
            name: 'Asset Transfer',
            description: 'Asset transfer between brokers',
            icon_slug: 'transfer',
            doc_slug: 'transfer',
            asset_mode: 'required',
            cash_mode: 'forbidden',
            quantity_mode: 'required',
            requires_link: true,
            quantity_sign: 'nonzero',
            cash_sign: 'zero',
            event_compatible: false,
            pair_form_layout: 'transfer_asset',
            split_into: {from_type: 'ADJUSTMENT', to_type: 'ADJUSTMENT'},
            promote_from: [{type_a: 'ADJUSTMENT', type_b: 'ADJUSTMENT', field_constraints: TRANSFER_CONSTRAINTS}],
            pair_field_constraints: TRANSFER_CONSTRAINTS,
            swap_group: [],
            cost_basis_pair: ['forbidden', 'required_qty_pos'],
        },
        {
            code: 'ADJUSTMENT',
            name: 'Adjustment',
            description: 'Manual quantity correction (splits, gifts)',
            icon_slug: 'adjustment',
            doc_slug: 'adjustment',
            asset_mode: 'required',
            cash_mode: 'forbidden',
            quantity_mode: 'required',
            requires_link: false,
            quantity_sign: 'nonzero',
            cash_sign: 'zero',
            event_compatible: true,
            swap_group: [],
            cost_basis_mode: 'required_qty_pos',
        },
    ],
    event_types: [],
});

/** A saved BUY: the row K-4 edits, and the row of the K-2 guard. */
const SAVED_BUY: TXReadItem = {
    id: 91_101,
    broker_id: 77,
    asset_id: 101,
    type: 'BUY',
    date: '2026-09-13',
    quantity: '1.000000',
    cash: {code: 'EUR', amount: '-10.000000'},
    related_transaction_id: null,
    partner_broker_id: null,
    tags: [],
    description: 'K-4 as saved',
    cost_basis_override: null,
    asset_event_id: null,
};

/** K-3: the sending half of a cash transfer whose receiving half (91302, on broker 88) the user cannot read: that half is
 *  in no store of this page, and the editor stands a W4b placeholder in for it. */
const SAVED_SENDER: TXReadItem = {
    id: 91_301,
    broker_id: 77,
    asset_id: null,
    type: 'CASH_TRANSFER',
    date: '2026-09-20',
    quantity: '0.000000',
    cash: {code: 'EUR', amount: '-50.000000'},
    related_transaction_id: 91_302,
    partner_broker_id: 88,
    tags: [],
    description: 'K-3 transfer out',
    cost_basis_override: null,
    asset_event_id: null,
};

/** K-3b: the receiving half of a cash transfer whose sending half (91402, on broker 88) the user cannot read. */
const SAVED_RECEIVER: TXReadItem = {
    id: 91_401,
    broker_id: 77,
    asset_id: null,
    type: 'CASH_TRANSFER',
    date: '2026-09-21',
    quantity: '0.000000',
    cash: {code: 'EUR', amount: '50.000000'},
    related_transaction_id: 91_402,
    partner_broker_id: 88,
    tags: [],
    description: 'K-3b transfer in',
    cost_basis_override: null,
    asset_event_id: null,
};

/**
 * C-46: PC5's legs (tx-bulk-promote-cost-basis.spec.ts, before B-48). A's leg is the same in both pairs; B's cancels it
 * exactly in the control, and one digit off in the 6th decimal in the pair under test — one double all the same:
 * between 2^36 and 2^37 consecutive doubles are 2^-16 ≈ 1.5e-5 apart, and .123456 and .123457 round to the same one.
 */
const C46 = {
    out: '-123456789012.123456',
    exactIn: '123456789012.123456',
    nearIn: '123456789012.123457',
    brokerA: 77,
    brokerB: 88,
    assetId: 101,
    date: '2026-09-25',
} as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mountEditor(intent: WorkspaceIntent) {
    const onClose = vi.fn();
    return {onClose, ...render(TransactionBulkModal, {open: true, intent, onClose})};
}

/** The props the editor hands its nested Form. */
function formProbe(): Record<string, unknown> {
    if (!probe.form) throw new Error('TransactionBulkModal did not mount its nested TransactionFormModal');
    return probe.form;
}

/** The props the editor hands its nested import wizard. */
function wizardProbe(): Record<string, unknown> {
    if (!probe.wizard) throw new Error('TransactionBulkModal did not mount its nested ImportWizardModal');
    return probe.wizard;
}

/** The text of a row's ID cell: `#91101`, or both ids of a pair (`#91301` then `#91302`, the row's own first). */
function idCellText(row: HTMLElement): string {
    return row.querySelector('td[data-column-id="id"]')?.textContent ?? '';
}

/** Every data row of the grid. */
function gridRows(): HTMLElement[] {
    return [...screen.getByTestId('tx-bulk-body').querySelectorAll<HTMLElement>('tbody tr[data-row-id]')];
}

/** The grid row of a saved transaction, found by the id its ID cell shows: exactly one, or a failure saying how many. */
function gridRow(txId: number): HTMLElement {
    const rows = gridRows().filter((row) => idCellText(row).includes(`#${txId}`));
    if (rows.length !== 1) throw new Error(`expected one grid row for #${txId}, found ${rows.length}`);
    return rows[0];
}

/** The grid row of a new transaction, found by the description the test gave it: exactly one, or a failure saying how many. */
function gridRowDescribed(description: string): HTMLElement {
    const rows = gridRows().filter((row) => rowDescription(row) === description);
    if (rows.length !== 1) throw new Error(`expected one grid row described ${JSON.stringify(description)}, found ${rows.length}`);
    return rows[0];
}

/** What the status cell of a row says: original, edited, delete, new. */
function rowStatus(row: HTMLElement): string | null {
    return row.querySelector('[data-testid="tx-bulk-row-status"]')?.getAttribute('data-status') ?? null;
}

/** The description cell of a row, as text. */
function rowDescription(row: HTMLElement): string {
    return (row.querySelector('td[data-column-id="description"]')?.textContent ?? '').trim();
}

/** A held promise and the hand that releases it. */
function deferred(): {promise: Promise<void>; resolve: () => void} {
    let resolve: () => void = () => undefined;
    const promise = new Promise<void>((release) => (resolve = release));
    return {promise, resolve};
}

/**
 * One real macrotask, then Svelte's flush. Not a wait on the clock — nothing in these chains is timed: when a
 * zero-delay timer fires, every microtask queued before it has run, the ones it queued in turn included (the load's
 * `Promise.all`, the continuation after its `await`, the `queueMicrotask` of an auto-open, Svelte's own batch).
 */
async function settle(): Promise<void> {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    flushSync();
    await tick();
}

/**
 * Click, let the editor settle, and return what the click handler threw. An error thrown by a handler reaches the
 * window, not the test: listened for here, it is reported by the case that caused it, by name, instead of as an
 * unhandled error of the run.
 */
async function clickCollectingErrors(target: HTMLElement): Promise<string[]> {
    const thrown: unknown[] = [];
    const onError = (event: ErrorEvent) => {
        thrown.push(event.error ?? event.message);
        event.preventDefault();
    };
    window.addEventListener('error', onError);
    try {
        await fireEvent.click(target);
        await settle();
    } finally {
        window.removeEventListener('error', onError);
    }
    return thrown.map(String);
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

beforeAll(async () => {
    await setupI18n();
    // The real type store, loaded once from the fixture: `getTypeRule` answers with the backend's rules, not the fallback.
    vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_RESPONSE);
    await ensureTypesLoaded();
    expect(isTypesLoaded(), 'premise: the type store holds the fixture').toBe(true);
});

beforeEach(() => {
    vi.clearAllMocks();
    probe.form = null;
    probe.wizard = null;
    probe.pickers = [];
    typesLoad.slow = false;
    typesLoad.gate = null;
    currentLanguage.set('en');
    // The promote search the editor runs on its saved rows: nothing to suggest.
    vi.mocked(zodiosApi.promote_suggest_api_v1_transactions_promote_suggest_post).mockResolvedValue({results: {}} as never);
});

afterEach(() => {
    cleanup();
    txStoreInvalidate();
    typesLoad.slow = false;
    typesLoad.gate = null;
    currentLanguage.set('en');
});

// ---------------------------------------------------------------------------
// K-4 — a language change must not rebuild the open editor
// ---------------------------------------------------------------------------

describe('TransactionBulkModal — K-4: a language change keeps the unsaved edits', () => {
    // Red today: the open effect tracks `$currentLanguage`, so the change runs it again and `ops` is rebuilt from the
    // intent: the row is back to original, its description to the stored one.
    it('K-4: an edit applied from the Form is still in the grid after the language changes', async () => {
        txStoreSetAll([SAVED_BUY], []);
        mountEditor({action: 'edit', txIds: [SAVED_BUY.id]});

        // One selected row opens its Form over the grid, on that row.
        await waitFor(() => expect(formProbe().open, 'one selected row auto-opens its Form').toBe(true));
        expect((formProbe().items as TXReadItem[] | null)?.[0]?.id, 'the Form is on the saved BUY').toBe(SAVED_BUY.id);
        expect(vi.mocked(ensureCurrenciesLoaded), 'premise: the editor loads the currencies in the language of the store this test drives').toHaveBeenCalledWith('en');

        // «Apply» with a new description: the payload the Form pushes for an edited saved row (commitOnSave=false).
        const applyFromForm = formProbe().onPushDraft as (payload: Record<string, unknown>) => void;
        applyFromForm({
            broker_id: SAVED_BUY.broker_id,
            type: SAVED_BUY.type,
            date: SAVED_BUY.date,
            quantity: '1.000000',
            asset_id: SAVED_BUY.asset_id,
            cash: {code: 'EUR', amount: '-10.000000'},
            description: 'K-4 unsaved edit',
            _cost_basis_mode: 'auto',
            _wac_currency_hint: null,
        });
        flushSync();
        await tick();

        expect(formProbe().open, 'Apply closes the Form').toBe(false);
        expect({status: rowStatus(gridRow(SAVED_BUY.id)), description: rowDescription(gridRow(SAVED_BUY.id))}, 'premise: the grid holds the edit, unsaved').toEqual({status: 'edited', description: 'K-4 unsaved edit'});

        // The user switches the interface language while the editor is open.
        currentLanguage.set('it');
        flushSync();
        await settle();

        expect({status: rowStatus(gridRow(SAVED_BUY.id)), description: rowDescription(gridRow(SAVED_BUY.id))}, 'K-4: the language change rebuilt the editor from its intent and threw the unsaved edit away').toEqual({
            status: 'edited',
            description: 'K-4 unsaved edit',
        });
    });
});

// ---------------------------------------------------------------------------
// K-2 — the slow path opens the Form or the wizard once
// ---------------------------------------------------------------------------

describe('TransactionBulkModal — K-2: on the slow path, what opened early and was closed stays closed', () => {
    /** Open the editor on the slow path: the types are not loaded, and their load waits for the returned gate. */
    function openOnSlowPath(intent: WorkspaceIntent): {releaseTypes: () => void} {
        const gate = deferred();
        typesLoad.slow = true;
        typesLoad.gate = gate.promise;
        mountEditor(intent);
        expect(vi.mocked(isTypesLoaded), 'premise: the editor asked whether the types are loaded').toHaveBeenCalled();
        return {releaseTypes: gate.resolve};
    }

    // Red today: when the load ends, `if (!formOpen) scheduleAutoOpen('create', [])` opens the Form again.
    it('K-2: a new editor (create) opens its Form at once; closed before the types load, it stays closed once they do', async () => {
        const {releaseTypes} = openOnSlowPath({action: 'create'});

        await waitFor(() => expect(formProbe().open, 'the slow path opens the Form without waiting for the types').toBe(true));
        expect(vi.mocked(ensureTypesLoaded), 'premise: the types load is under way, held by the test').toHaveBeenCalled();

        // The user closes the Form (its Cancel) while the types are still loading.
        (formProbe().onClose as () => void)();
        flushSync();
        expect(formProbe().open, 'premise: the Form is closed').toBe(false);

        releaseTypes();
        await settle();

        expect(formProbe().open, 'K-2: the end of the types load opened again the Form the user had closed').toBe(false);
    });

    // Red today: when the load ends, the Form is not open, so `scheduleAutoOpen(null, [])` opens the wizard again.
    it('K-2: an import editor opens its wizard at once; closed before the types load, it stays closed once they do', async () => {
        const {releaseTypes} = openOnSlowPath({action: 'import'});

        await waitFor(() => expect(wizardProbe().open, 'the slow path opens the wizard without waiting for the types').toBe(true));

        // The user closes the wizard while the types are still loading.
        (wizardProbe().onClose as () => void)();
        flushSync();
        expect(wizardProbe().open, 'premise: the wizard is closed').toBe(false);

        releaseTypes();
        await settle();

        expect(wizardProbe().open, 'K-2: the end of the types load opened again the wizard the user had closed').toBe(false);
        expect(formProbe().open, 'and no Form opened instead').toBe(false);
    });

    // Guard, green today: with rows nothing opens early, so the auto-open after the load is the only one — and the
    // same `settle()` the two cases above rely on is enough for it to run.
    it('K-2 guard: with one saved row to edit nothing opens early, and its Form opens once the types load', async () => {
        txStoreSetAll([SAVED_BUY], []);
        const {releaseTypes} = openOnSlowPath({action: 'edit', txIds: [SAVED_BUY.id]});

        await settle();
        expect(formProbe().open, 'with rows, the slow path opens nothing before the types load').toBe(false);
        expect(wizardProbe().open, 'nor the wizard').toBe(false);

        releaseTypes();
        await settle();

        expect(formProbe().open, 'once the types load, the one row to edit opens its Form').toBe(true);
        expect({mode: formProbe().mode, id: (formProbe().items as TXReadItem[] | null)?.[0]?.id}, 'in edit mode, on that row').toEqual({mode: 'edit', id: SAVED_BUY.id});
        expect(rowStatus(gridRow(SAVED_BUY.id)), 'and the grid shows the row').toBe('original');
    });
});

// ---------------------------------------------------------------------------
// K-3 and K-3b — a reset keeps the placeholder of an unreadable partner, as the hidden half of its pair
// ---------------------------------------------------------------------------

describe('TransactionBulkModal — K-3 and K-3b: a reset on a pair whose partner the user cannot read', () => {
    /** The id of the partner a saved half names: on a broker the user cannot read, so it is in no store of this page. */
    function partnerIdOf(readable: TXReadItem): number {
        if (readable.related_transaction_id == null) throw new Error(`#${readable.id} names no partner`);
        return readable.related_transaction_id;
    }

    /** The grid rows that name either half of the pair in their ID cell. */
    function rowsOfPair(readable: TXReadItem): HTMLElement[] {
        const ids = [readable.id, partnerIdOf(readable)].map((id) => `#${id}`);
        return gridRows().filter((row) => ids.some((id) => idCellText(row).includes(id)));
    }

    /**
     * The pair as the editor first builds it (`collapsePairedOps`, pass 2): one row on screen, the readable half, whose
     * hidden partner is the placeholder — its ID cell names the readable half first and the partner second, and its
     * broker cell shows the partner's broker as a lock (`tx-bulk-partner-lock`, drawn only when the hidden partner is
     * `inaccessible`). Returns that row.
     */
    function expectPairRow(readable: TXReadItem, what: string): HTMLElement {
        const rows = rowsOfPair(readable);
        expect(rows.length, `${what}: the pair is one row on screen`).toBe(1);
        const [row] = rows;
        expect(idCellText(row), `${what}: the row is the readable half, the placeholder named after it as its partner`).toMatch(new RegExp(`#${readable.id}[\\s\\S]*#${partnerIdOf(readable)}`));
        expect(row.querySelector('[data-testid="tx-bulk-partner-lock"]'), `${what}: the partner's broker is shown as a lock`).not.toBeNull();
        return row;
    }

    /** The editor opened by the delete intent on the readable half: marked for deletion, its partner the W4b placeholder. */
    async function openPairMarkedForDeletion(readable: TXReadItem): Promise<void> {
        txStoreSetAll([readable], []);
        mountEditor({action: 'delete', txIds: [readable.id]});
        await waitFor(() => expect(rowsOfPair(readable).length, 'premise: the pair is on screen').toBe(1));
        expect(rowStatus(expectPairRow(readable, 'premise')), 'premise: the readable half is marked for deletion').toBe('delete');
    }

    /** The row's own Reset, and what it threw. */
    async function resetFromRowMenu(readable: TXReadItem): Promise<string[]> {
        // The row's action menu through its right-click: the ⋮ button positions the same menu against an anchor in a
        // requestAnimationFrame, which jsdom does not drive (see DataEditor.test.ts).
        await fireEvent.contextMenu(expectPairRow(readable, 'premise'), {clientX: 10, clientY: 10});
        return clickCollectingErrors(await screen.findByTestId('context-menu-action-reset'));
    }

    // Red today: `resetAll` maps the W4b placeholder through `editOpFromTx`, which reads its transaction from the store,
    // finds nothing and throws; the reset never happens, so the row stays marked for deletion.
    it('K-3: Reset all resets the readable half, throws nothing, and keeps the placeholder of the unreadable one', async () => {
        await openPairMarkedForDeletion(SAVED_SENDER);

        const thrown = await clickCollectingErrors(screen.getByTestId('tx-bulk-reset-all'));

        expect(thrown, 'K-3: Reset all threw on the placeholder of the unreadable partner').toEqual([]);
        const row = expectPairRow(SAVED_SENDER, 'after Reset all');
        expect(rowStatus(row), 'the readable half is reset: no longer marked for deletion').toBe('original');
    });

    // Guard, green today: the row's own Reset (`resetRow`) already skips the placeholder, and on a readable sender the
    // collapse that follows pairs it again the right way. It ends where Reset all must end, which is what makes the end
    // state of the case above reachable, not invented.
    it('K-3 guard: on a readable sender, the row Reset skips the placeholder: the readable half reset, nothing thrown, the placeholder kept', async () => {
        await openPairMarkedForDeletion(SAVED_SENDER);

        const thrown = await resetFromRowMenu(SAVED_SENDER);

        expect(thrown, 'the row Reset throws nothing').toEqual([]);
        const row = expectPairRow(SAVED_SENDER, 'after the row Reset');
        expect(rowStatus(row), 'the readable half is reset').toBe('original');
    });

    /*
     * K-3b — the readable half is the receiver, the placeholder the sender. After a reset the collapse pairs the rows by
     * direction (pass 1): the half with the positive cash is hidden behind the other, and the placeholder's cash, unknown,
     * reads 0. So the readable receiver is hidden behind the placeholder, which still points at the receiver's row before
     * the reset: both are hidden, and the pair is no longer on screen — nothing says why, and the transfer is out of the
     * batch's view.
     */

    // Red today: after the row Reset no row names either half.
    it('K-3b: on a readable receiver, the row Reset keeps the pair one row: the receiver on screen, the placeholder its hidden partner', async () => {
        await openPairMarkedForDeletion(SAVED_RECEIVER);

        const thrown = await resetFromRowMenu(SAVED_RECEIVER);

        expect(thrown, 'the row Reset throws nothing').toEqual([]);
        const row = expectPairRow(SAVED_RECEIVER, 'K-3b: after the row Reset');
        expect(rowStatus(row), 'the readable receiver is reset').toBe('original');
    });

    // Red today, and for two reasons in turn: first K-3's — Reset all throws on the placeholder (soft, so the end state
    // is reported too), and the row stays marked for deletion; with K-3's guard alone, then K-3b's — no row names either
    // half. Green once both are cured.
    it('K-3b: on a readable receiver, Reset all keeps the pair one row: the receiver on screen, the placeholder its hidden partner', async () => {
        await openPairMarkedForDeletion(SAVED_RECEIVER);

        const thrown = await clickCollectingErrors(screen.getByTestId('tx-bulk-reset-all'));

        expect.soft(thrown, 'K-3 (cured first): Reset all threw on the placeholder of the unreadable partner').toEqual([]);
        const row = expectPairRow(SAVED_RECEIVER, 'K-3b: after Reset all');
        expect(rowStatus(row), 'the readable receiver is reset').toBe('original');
    });
});

// ---------------------------------------------------------------------------
// C-46 — two legs opposite as doubles, not as decimals, are never offered as a merge (regression guard)
// ---------------------------------------------------------------------------

/**
 * C-46, moved from the E2E PC5 (tx-bulk-promote-cost-basis.spec.ts). The selection toolbar (`selectedForPromote` →
 * `promote-toolbar-confirm`) asked `findPromoteMatch` only, whose TRANSFER rule compares the quantities as JavaScript
 * numbers (`buildPromoteCtx` reads `Number(quantity)`): two legs opposite as doubles and not as decimals were offered as
 * a merge, and the save was refused (`pairQuantityMismatch`). Since C-46 it asks the exact `assetQuantitiesCancel` too,
 * as the banner always did. Green: a regression guard.
 *
 * PC5 typed its legs into the form. They have eighteen significant digits, and since B-48 the form refuses more than
 * fifteen — as the backend does (`significantDigitsExceeded`) — while within fifteen two different decimals are always
 * two different doubles: the case exists only outside what the form and the backend accept. An import still hands the
 * editor such rows (`onImportBatch` → `txCreateItemToPendingOp`, the quantity of an ADJUSTMENT kept as the file gives
 * it), so the guard stays here, on rows brought in the way an import brings them: the import editor's wizard hands over
 * its batch, as the real wizard does when it finishes.
 */
describe('TransactionBulkModal — C-46: the selection toolbar never offers to merge legs opposite as doubles only', () => {
    /** One ADJUSTMENT as an import hands it over: no todos, the quantity as the file gives it. */
    function importedAdjustment(brokerId: number, quantity: string, description: string): {tx: TransactionCreateItem; todos: []} {
        return {tx: {broker_id: brokerId, type: 'ADJUSTMENT', date: C46.date, asset_id: C46.assetId, quantity, tags: [], description} as TransactionCreateItem, todos: []};
    }

    /** A new editor on the import intent, its wizard handing over `batch`; ends on the wizard closed and the rows in the grid. */
    async function importIntoNewEditor(batch: Array<{tx: TransactionCreateItem; todos: []}>): Promise<void> {
        mountEditor({action: 'import'});
        await waitFor(() => expect(wizardProbe().open, 'the import intent opens the wizard').toBe(true));
        const handOver = wizardProbe().onImportBatch as (creates: Array<{tx: TransactionCreateItem; todos: []}>) => void;
        handOver(batch);
        await settle();
        expect(wizardProbe().open, 'the hand-over closes the wizard').toBe(false);
        for (const {tx} of batch) {
            const row = gridRowDescribed(String(tx.description));
            expect(rowStatus(row), `premise: ${tx.description} is a new row`).toBe('new');
            expect((row.querySelector('td[data-column-id="quantity"]')?.textContent ?? '').trim(), `premise: ${tx.description} holds its quantity as imported, every digit`).toBe(String(tx.quantity));
        }
    }

    /** Tick the row described `description`, and prove it ticked. */
    async function select(description: string): Promise<void> {
        const checkbox = gridRowDescribed(description).querySelector<HTMLElement>('[data-testid^="dt-row-checkbox-"]');
        if (!checkbox) throw new Error(`the row described ${JSON.stringify(description)} has no checkbox`);
        await fireEvent.click(checkbox);
        expect(checkbox, `${description} is selected`).toHaveAttribute('data-state', 'checked');
    }

    // Control, green: the toolbar does offer a merge in this harness — two legs that cancel exactly.
    it('C-46 control: two imported legs that cancel exactly, −123456789012.123456 on A and +123456789012.123456 on B, are offered as a merge', async () => {
        expect(C46.out, 'premise: the control is exactly opposite as decimals').toBe(`-${C46.exactIn}`);
        await importIntoNewEditor([importedAdjustment(C46.brokerA, C46.out, 'C-46 exact out'), importedAdjustment(C46.brokerB, C46.exactIn, 'C-46 exact in')]);
        // Side check, the banner's: it compares the decimal strings, and offers the pair.
        expect(screen.queryByTestId('promote-suggest-banner'), 'the banner offers the exact pair').not.toBeNull();

        await select('C-46 exact out');
        await select('C-46 exact in');

        expect(screen.queryByTestId('tx-bulk-delete-selected'), 'premise: the selection toolbar is on screen').not.toBeNull();
        expect(screen.queryByTestId('promote-toolbar-confirm'), 'the control: the selection toolbar offers the merge of two legs that cancel exactly').not.toBeNull();
    });

    // Green since C-46: one digit off in the 6th decimal, the same double.
    it('C-46: two imported legs opposite as doubles and not as decimals, −123456789012.123456 on A and +123456789012.123457 on B, are offered no merge', async () => {
        // The premise, re-checked here as PC5 did: without it this case would pass for the wrong reason.
        expect(C46.out, 'premise: the pair under test is not opposite as decimals').not.toBe(`-${C46.nearIn}`);
        expect(Number(C46.out), 'premise: yet it is opposite as doubles, the comparison findPromoteMatch makes').toBe(-Number(C46.nearIn));
        await importIntoNewEditor([importedAdjustment(C46.brokerA, C46.out, 'C-46 near out'), importedAdjustment(C46.brokerB, C46.nearIn, 'C-46 near in')]);
        // Side check, the banner's: it compares the decimal strings, and offers nothing.
        expect(screen.queryByTestId('promote-suggest-banner'), 'the banner offers no merge: the legs differ in the 6th decimal').toBeNull();

        await select('C-46 near out');
        await select('C-46 near in');

        // Presence barrier: the toolbar did answer the selection of the two legs.
        expect(screen.queryByTestId('tx-bulk-delete-selected'), 'premise: the selection toolbar is on screen').not.toBeNull();
        expect(screen.queryByTestId('promote-toolbar-confirm'), `C-46: the selection toolbar offers the merge — Number() makes ${C46.out} and ${C46.nearIn} one double, and the save would be refused (pairQuantityMismatch)`).toBeNull();
        expect(
            gridRows().filter((row) => rowDescription(row).startsWith('C-46 near')),
            'the two legs stay apart',
        ).toHaveLength(2);
    });
});

// ---------------------------------------------------------------------------
// N78-1 — an outgoing ADJUSTMENT loads into the editor without a cost mode
// ---------------------------------------------------------------------------

/** A saved ADJUSTMENT of asset 101 on broker 77, `quantity` signed, storing `cost` or no value. */
function savedAdjustment(id: number, quantity: string, cost: {code: string; amount: string} | null): TXReadItem {
    return {
        id,
        broker_id: 77,
        asset_id: 101,
        type: 'ADJUSTMENT',
        date: '2026-09-27',
        quantity,
        cash: null,
        related_transaction_id: null,
        partner_broker_id: null,
        tags: [],
        description: `N78-1 adjustment ${quantity}`,
        cost_basis_override: cost,
        asset_event_id: null,
    } as TXReadItem;
}

describe('TransactionBulkModal — N78-1: an outgoing ADJUSTMENT has no cost mode', () => {
    // N78-1 (the developer's decision, 21/10/2026): an ADJUSTMENT taking units out has no value, so the editor loads it
    // (`fieldsFromTx`) without a cost mode — the grid shows no cost for it, and the Form it opens is handed none. RED until
    // the cure for the outgoing rows: today every ADJUSTMENT read from the store loads as 'manual'. The incoming row is the
    // guard: it keeps 'manual'. Read through the props the editor hands its Form (`opToTxLike`), on the row it opens.
    it.each([
        ['an outgoing ADJUSTMENT without a value', null, 91_501, '-3.000000', null],
        ['an outgoing ADJUSTMENT storing a value (an old row)', null, 91_502, '-3.000000', {code: 'EUR', amount: '20.000000'}],
        ['an incoming ADJUSTMENT (guard)', 'manual', 91_503, '3.000000', {code: 'EUR', amount: '20.000000'}],
    ] as const)('N78-1: %s loads with cost mode %j', async (_label, expectedMode, id, quantity, cost) => {
        const saved = savedAdjustment(id, quantity, cost ? {...cost} : null);
        txStoreSetAll([saved], []);
        mountEditor({action: 'edit', txIds: [saved.id]});

        await waitFor(() => expect(formProbe().open, 'one selected row auto-opens its Form').toBe(true));
        const item = (formProbe().items as TXReadItem[] | null)?.[0] as (TXReadItem & {cost_basis_mode?: unknown}) | undefined;
        expect(item?.id, 'the Form is on the saved ADJUSTMENT').toBe(saved.id);
        expect(item?.cost_basis_mode ?? null, `N78-1: ${_label} — an ADJUSTMENT of quantity ${quantity} takes a cost mode only when it adds units`).toBe(expectedMode);
    });
});

// ---------------------------------------------------------------------------
// W-B87 — a stock split an import flagged `possible_split`: its own banner, its own way out
// ---------------------------------------------------------------------------

/**
 * An importer enters a stock split as an incoming ADJUSTMENT at no cost and attaches a todo `{field: 'asset_event_id',
 * severity: 'warning', reasonCode: 'possible_split', context: {ticker, added_quantity, isin?}}`. The editor shows it where the
 * user can act on it:
 *
 *   - `tx-bulk-possible-split` lists one `possible-split-row` per such row, keyed by the visible row (`data-row-id`);
 *   - the generic «fields to verify» banner (`tx-bulk-todo-warnings`) neither counts nor lists those todos any more;
 *   - the save gate still counts them: a batch whose only warning is a possible split asks for the confirmation
 *     (`confirm-modal-confirm`) before it saves;
 *   - «link an existing event» (`possible-split-link`, then the picker): the row gets that `asset_event_id`, its todo is
 *     recomputed (`remainingTodos`) and gone, so the row leaves the banner and the editor stops asking;
 *   - «create the SPLIT event and link it» (`possible-split-create`): the real EventCreateMiniModal opens for the row's asset on
 *     the row's date, on SPLIT; a ratio typed and created sends `upsert_events_bulk` as `mode: 'create'`, `type: 'SPLIT'`, with
 *     the ratio as typed; the event it returns is linked the same way.
 *
 * Rows come in the way an import brings them (the wizard probe's `onImportBatch`); the nested Form and wizard stay probes, the
 * picker is the shared stand-in. Rows are found by the description the test gave them, never by position; the language is the
 * real English catalogue, read only through the keys of the labels it compares (`assetDetail.eventType.SPLIT`).
 */
describe('TransactionBulkModal — W-B87: the possible-split banner', () => {
    const PICKED_EVENT_ID = 555;
    const CREATED_EVENT_ID = 901;
    const SPLIT_DATE = '2022-08-25';

    type Handed = {tx: TransactionCreateItem; todos: Array<Record<string, unknown>>};

    const splitTodo = (context: Record<string, unknown> = {}): Record<string, unknown> => ({
        field: 'asset_event_id',
        severity: 'warning',
        reasonCode: 'possible_split',
        message: 'Invented possible split',
        context: {ticker: 'TSLA', added_quantity: '0.16431924', ...context},
    });
    const otherTodo = (): Record<string, unknown> => ({field: 'asset_event_id', severity: 'warning', reasonCode: 'probe_other_reason', message: 'Invented other todo'});

    /** An incoming ADJUSTMENT as an import hands it over: the split of asset 101 on broker 77. */
    function importedSplit(description: string, todos: Array<Record<string, unknown>>): Handed {
        return {tx: {broker_id: 77, type: 'ADJUSTMENT', date: SPLIT_DATE, asset_id: 101, quantity: '0.16431924', tags: [], description} as TransactionCreateItem, todos};
    }

    async function importIntoNewEditor(batch: Handed[]): Promise<void> {
        mountEditor({action: 'import'});
        await waitFor(() => expect(wizardProbe().open, 'the import intent opens the wizard').toBe(true));
        const handOver = wizardProbe().onImportBatch as (creates: Handed[]) => void;
        handOver(batch);
        await settle();
        expect(wizardProbe().open, 'the hand-over closes the wizard').toBe(false);
        for (const {tx} of batch) expect(rowStatus(gridRowDescribed(String(tx.description))), `premise: ${tx.description} is a new row`).toBe('new');
    }

    /** The `data-row-id` of the grid row described `description`: what the banner's row must name. */
    const rowIdOf = (description: string): string => gridRowDescribed(description).getAttribute('data-row-id') ?? '';

    /** The rows of the possible-split banner, by the visible row they name. */
    const bannerRowIds = (): string[] => screen.queryAllByTestId('possible-split-row').map((row) => row.getAttribute('data-row-id') ?? '');

    function bannerRowOf(description: string): HTMLElement {
        const id = rowIdOf(description);
        const row = screen.queryAllByTestId('possible-split-row').find((candidate) => candidate.getAttribute('data-row-id') === id);
        if (!row) throw new Error(`the possible-split banner has no row for ${JSON.stringify(description)} (it names: ${JSON.stringify(bannerRowIds())})`);
        return row;
    }

    /** The text of the event cell of a grid row. */
    const eventCellOf = (description: string): string => (gridRowDescribed(description).querySelector('td[data-column-id="asset_event_id"]')?.textContent ?? '').trim();

    const upsert = () => vi.mocked(zodiosApi.upsert_events_bulk_api_v1_assets_events_post);

    beforeEach(() => {
        upsert().mockResolvedValue(
            schemas.FABulkEventUpsertResponse.parse({
                results: [{asset_id: 101, count: 1, message: 'ok', event_ids: [CREATED_EVENT_ID]}],
                success_count: 1,
            }),
        );
    });

    // --- the banner ---------------------------------------------------------------------------------------------

    it('lists a row that carries the todo, by its visible row, and no row that does not', async () => {
        await importIntoNewEditor([importedSplit('W-B87 split', [splitTodo()]), importedSplit('W-B87 plain', [])]);

        expect(screen.queryByTestId('tx-bulk-possible-split'), 'the banner is on screen').not.toBeNull();
        expect(bannerRowIds(), 'one row, the split').toEqual([rowIdOf('W-B87 split')]);
    });

    it('is absent when no row carries the todo', async () => {
        await importIntoNewEditor([importedSplit('W-B87 plain only', [])]);

        expect(screen.queryByTestId('tx-bulk-possible-split')).toBeNull();
    });

    it('a todo with another reason on the same field is not a split', async () => {
        await importIntoNewEditor([importedSplit('W-B87 other reason', [otherTodo()])]);

        expect(screen.queryByTestId('tx-bulk-possible-split')).toBeNull();
        expect(screen.queryByTestId('tx-bulk-todo-warnings'), 'it stays a generic todo').not.toBeNull();
    });

    it('keeps the split rows out of the generic «fields to verify» banner, which still lists its own', async () => {
        await importIntoNewEditor([importedSplit('W-B87 split', [splitTodo()]), importedSplit('W-B87 generic', [otherTodo()])]);

        const generic = await screen.findByTestId('tx-bulk-todo-warnings');
        await fireEvent.click(screen.getByTestId('tx-bulk-todo-warnings-toggle'));
        const listed = [...generic.querySelectorAll('[data-testid="tx-bulk-todo-goto"]')].map((goto) => goto.getAttribute('data-row-id'));
        expect(listed, 'the generic banner lists the other row only').toEqual([rowIdOf('W-B87 generic')]);
        expect(bannerRowIds(), 'and the split banner the split row only').toEqual([rowIdOf('W-B87 split')]);
    });

    it('draws no generic banner when the split is the only warning', async () => {
        await importIntoNewEditor([importedSplit('W-B87 split', [splitTodo()])]);

        expect(screen.queryByTestId('tx-bulk-possible-split')).not.toBeNull();
        expect(screen.queryByTestId('tx-bulk-todo-warnings'), 'the split is counted by its own banner').toBeNull();
    });

    // --- the save gate ------------------------------------------------------------------------------------------

    // Guard, green today: the gate counts every row with a warning, the split included — and it must keep doing so once the
    // generic banner stops counting it.
    it('guard: a batch whose only warning is a possible split still asks for the confirmation before saving', async () => {
        const {commitTransactions} = await import('$lib/features/transactions/txCommitApi');
        await importIntoNewEditor([importedSplit('W-B87 split', [splitTodo()])]);

        await fireEvent.click(screen.getByTestId('tx-bulk-commit'));

        expect(await screen.findByTestId('confirm-modal-confirm'), 'the save gate asks about the fields to verify').toBeInTheDocument();
        expect(commitTransactions, 'and nothing is saved yet').not.toHaveBeenCalled();
    });

    // --- link an existing event ---------------------------------------------------------------------------------

    it('linking an event writes it on the row, closes its todo, and the row leaves the banner', async () => {
        await importIntoNewEditor([importedSplit('W-B87 split', [splitTodo()]), importedSplit('W-B87 other split', [splitTodo({ticker: 'OTH'})])]);
        expect(eventCellOf('W-B87 split'), 'premise: no event on the row yet').not.toMatch(/\d/);
        const row = bannerRowOf('W-B87 split');

        await fireEvent.click(within(row).getByTestId('possible-split-link'));
        await fireEvent.click(within(row).getByTestId('event-picker-stub-pick'));
        await settle();

        expect(bannerRowIds(), 'only the other split is still listed').toEqual([rowIdOf('W-B87 other split')]);
        expect(eventCellOf('W-B87 split'), 'the row shows the event it is linked to').toMatch(new RegExp(`${PICKED_EVENT_ID}|✂`));
        expect(eventCellOf('W-B87 other split'), 'the other row is untouched').not.toMatch(/\d/);
    });

    it('with its last split linked the banner is gone and the save gate no longer asks', async () => {
        const {commitTransactions} = await import('$lib/features/transactions/txCommitApi');
        await importIntoNewEditor([importedSplit('W-B87 split', [splitTodo()])]);
        const row = bannerRowOf('W-B87 split');
        await fireEvent.click(within(row).getByTestId('possible-split-link'));
        await fireEvent.click(within(row).getByTestId('event-picker-stub-pick'));
        await settle();
        expect(screen.queryByTestId('tx-bulk-possible-split'), 'the last row left: no banner').toBeNull();

        await fireEvent.click(screen.getByTestId('tx-bulk-commit'));
        await settle();

        expect(screen.queryByTestId('confirm-modal-confirm'), 'nothing left to verify: no confirmation').toBeNull();
        expect(commitTransactions, 'the batch goes straight to the save').toHaveBeenCalled();
    });

    // --- create the event ---------------------------------------------------------------------------------------

    it('«create» opens the mini modal for the row on SPLIT, and a typed ratio creates the event and links it', async () => {
        await importIntoNewEditor([importedSplit('W-B87 split', [splitTodo()])]);

        await fireEvent.click(within(bannerRowOf('W-B87 split')).getByTestId('possible-split-create'));

        const modal = await screen.findByTestId('event-create-mini-modal');
        expect(within(modal).getByTestId('event-create-type-button'), 'the modal starts on SPLIT').toHaveTextContent(get(_)('assetDetail.eventType.SPLIT'));
        expect(within(modal).queryByTestId('event-create-ratio-hint'), 'a SPLIT amount is a ratio, and says so').not.toBeNull();
        const date = within(within(modal).getByTestId('single-date-picker-root')).getByRole('textbox');
        await waitFor(() => expect(date, 'premise: the modal is seeded with the row date').toHaveValue(SPLIT_DATE));
        const ratio = within(modal).getByTestId('event-create-amount');
        await fireEvent.input(ratio, {target: {value: '3'}});
        await fireEvent.blur(ratio);
        await fireEvent.click(within(modal).getByTestId('event-create-submit'));

        await waitFor(() => expect(upsert()).toHaveBeenCalledTimes(1));
        const item = upsert().mock.calls[0]?.[0]?.[0];
        expect(item, 'the event is created on the row asset').toMatchObject({asset_id: 101, mode: 'create'});
        const point = item?.events?.[0];
        expect(point).toMatchObject({type: 'SPLIT', date: SPLIT_DATE});
        expect(String(point?.value.amount), 'the ratio as typed').toBe('3');
        await waitFor(() => expect(screen.queryByTestId('tx-bulk-possible-split'), 'the created event is linked: the row left the banner').toBeNull());
        expect(eventCellOf('W-B87 split')).toMatch(new RegExp(`${CREATED_EVENT_ID}|✂`));
    });

    it('a ratio the importer suggested is prefilled in the mini modal as given', async () => {
        await importIntoNewEditor([importedSplit('W-B87 split', [splitTodo({held_before: '0.08215962', ratio: '3', suggested_ratio: '3', rounding_delta: '0'})])]);

        await fireEvent.click(within(bannerRowOf('W-B87 split')).getByTestId('possible-split-create'));

        const modal = await screen.findByTestId('event-create-mini-modal');
        const date = within(within(modal).getByTestId('single-date-picker-root')).getByRole('textbox');
        await waitFor(() => expect(date).toHaveValue(SPLIT_DATE));
        expect(within(modal).getByTestId('event-create-amount'), 'the suggestion, not 3.00').toHaveValue('3');
    });

    it('closing the mini modal without creating leaves the row in the banner, unlinked', async () => {
        await importIntoNewEditor([importedSplit('W-B87 split', [splitTodo()])]);
        await fireEvent.click(within(bannerRowOf('W-B87 split')).getByTestId('possible-split-create'));
        const modal = await screen.findByTestId('event-create-mini-modal');

        await fireEvent.click(within(modal).getByRole('button', {name: get(_)('common.cancel')}));
        await settle();

        expect(upsert()).not.toHaveBeenCalled();
        expect(bannerRowIds()).toEqual([rowIdOf('W-B87 split')]);
    });
});

// ---------------------------------------------------------------------------
// D-P4 (W5-10) — a date before 1900: its own banner, one confirmation at Save All
// ---------------------------------------------------------------------------

/**
 * The backend still refuses a transaction before 1900-01-01; the editor warns and asks once. The contract:
 *
 *   - `tx-bulk-pre-floor` (`data-count` = rows) lists one `tx-bulk-pre-floor-row` per row dated before 1900, keyed by the
 *     visible row (`data-row-id`) and carrying `data-date`. It comes from the row's DATE, so a row that reached the grid
 *     without the import's `date_before_1900` todo (the Form's Apply) is listed all the same;
 *   - the todo `date_before_1900` is not a «field to verify»: a row whose only warning is that one draws no
 *     `tx-bulk-todo-warnings` banner and does not trigger the warnings gate;
 *   - Save All: after the suggestions gate and the fields-to-verify gate comes ONE confirmation for all the rows (the
 *     `ConfirmModal`, titled `transactions.bulk.preFloorDate.confirmTitle`). Cancel returns to the grid and commits
 *     nothing; confirm commits. A batch with no such row goes straight to the save.
 *
 * Which of the two ConfirmModals is on screen is told by its message (`confirm-modal-message`), compared with the real
 * catalogue read through the key, as the case above reads its labels. Rows come in the way an import brings them.
 */
describe('TransactionBulkModal — D-P4: the date-before-1900 banner and its Save All confirmation', () => {
    const OLD = '1850-05-01';
    const OTHER_OLD = '1899-12-31';
    const NORMAL = '2024-03-12';

    type Handed = {tx: TransactionCreateItem; todos: Array<Record<string, unknown>>};

    /** The todo an import review puts on such a row (`withPreFloorDateTodo`). */
    const preFloorTodo = (date: string): Record<string, unknown> => ({field: 'date', severity: 'warning', reasonCode: 'date_before_1900', message: 'Invented pre-floor', context: {date}});
    const genericTodo = (): Record<string, unknown> => ({field: 'description', severity: 'warning', reasonCode: 'probe_generic', message: 'Invented generic todo'});

    /** A deposit on broker 77 as an import hands it over. */
    function deposit(description: string, date: string, todos: Array<Record<string, unknown>> = []): Handed {
        return {tx: {broker_id: 77, type: 'DEPOSIT', date, quantity: '0', cash: {code: 'EUR', amount: '100'}, tags: [], description} as unknown as TransactionCreateItem, todos};
    }

    async function importIntoNewEditor(batch: Handed[]): Promise<void> {
        mountEditor({action: 'import'});
        await waitFor(() => expect(wizardProbe().open, 'the import intent opens the wizard').toBe(true));
        (wizardProbe().onImportBatch as (creates: Handed[]) => void)(batch);
        await settle();
        for (const {tx} of batch) expect(rowStatus(gridRowDescribed(String(tx.description))), `premise: ${tx.description} is a new row`).toBe('new');
    }

    const rowIdOf = (description: string): string => gridRowDescribed(description).getAttribute('data-row-id') ?? '';
    const bannerLines = (): HTMLElement[] => screen.queryAllByTestId('tx-bulk-pre-floor-row');
    const bannerRowIds = (): string[] => bannerLines().map((line) => line.getAttribute('data-row-id') ?? '');
    const commitCalls = async () => vi.mocked((await import('$lib/features/transactions/txCommitApi')).commitTransactions);
    const confirmMessage = (): string => screen.queryByTestId('confirm-modal-message')?.textContent ?? '';
    const preFloorMessage = (n: number): string => get(_)('transactions.bulk.preFloorDate.confirmMessage', {values: {n}});
    const warningsMessage = (n: number): string => get(_)('importWizard.todoWarningConfirmMessage', {values: {n}});

    /** Click Save All and wait until the editor has answered: a confirmation is up, or the commit went out. */
    async function saveAll(): Promise<void> {
        await fireEvent.click(screen.getByTestId('tx-bulk-commit'));
        await settle();
    }

    // --- the banner ---------------------------------------------------------------------------------------------

    it('lists the rows dated before 1900, by their visible row and date, and no other row', async () => {
        await importIntoNewEditor([deposit('D-P4 old', OLD, [preFloorTodo(OLD)]), deposit('D-P4 normal', NORMAL), deposit('D-P4 other old', OTHER_OLD, [preFloorTodo(OTHER_OLD)])]);

        const banner = screen.getByTestId('tx-bulk-pre-floor');
        expect(banner).toHaveAttribute('data-count', '2');
        expect(new Set(bannerRowIds())).toEqual(new Set([rowIdOf('D-P4 old'), rowIdOf('D-P4 other old')]));
        const dateOf = (description: string) =>
            bannerLines()
                .find((line) => line.getAttribute('data-row-id') === rowIdOf(description))
                ?.getAttribute('data-date');
        expect(dateOf('D-P4 old')).toBe(OLD);
        expect(dateOf('D-P4 other old')).toBe(OTHER_OLD);
    });

    it('comes from the date: a row without the import’s todo is listed all the same', async () => {
        await importIntoNewEditor([deposit('D-P4 no todo', OLD, [])]);

        expect(screen.getByTestId('tx-bulk-pre-floor')).toHaveAttribute('data-count', '1');
        expect(bannerRowIds()).toEqual([rowIdOf('D-P4 no todo')]);
    });

    it('is absent when no row is dated before 1900, 1900-01-01 included', async () => {
        await importIntoNewEditor([deposit('D-P4 normal', NORMAL), deposit('D-P4 first day', '1900-01-01')]);

        expect(screen.queryByTestId('tx-bulk-pre-floor')).toBeNull();
    });

    it('the todo is not a «field to verify»: a row whose only warning is that one draws no generic banner', async () => {
        await importIntoNewEditor([deposit('D-P4 old', OLD, [preFloorTodo(OLD)])]);

        expect(screen.queryByTestId('tx-bulk-pre-floor')).not.toBeNull();
        expect(screen.queryByTestId('tx-bulk-todo-warnings')).toBeNull();
    });

    it('beside a real warning the generic banner lists that row only', async () => {
        await importIntoNewEditor([deposit('D-P4 old', OLD, [preFloorTodo(OLD)]), deposit('D-P4 generic', NORMAL, [genericTodo()])]);

        const generic = await screen.findByTestId('tx-bulk-todo-warnings');
        await fireEvent.click(screen.getByTestId('tx-bulk-todo-warnings-toggle'));
        const listed = [...generic.querySelectorAll('[data-testid="tx-bulk-todo-goto"]')].map((goto) => goto.getAttribute('data-row-id'));
        expect(listed).toEqual([rowIdOf('D-P4 generic')]);
        expect(bannerRowIds()).toEqual([rowIdOf('D-P4 old')]);
    });

    // --- Save All -----------------------------------------------------------------------------------------------

    it('a batch with no row before 1900 goes straight to the save, asking nothing', async () => {
        const commit = await commitCalls();
        await importIntoNewEditor([deposit('D-P4 normal', NORMAL)]);

        await saveAll();

        expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull();
        expect(commit).toHaveBeenCalled();
    });

    it('a row before 1900 (its only warning is the date): Save All asks the date question, not the fields to verify, and saves nothing yet', async () => {
        const commit = await commitCalls();
        await importIntoNewEditor([deposit('D-P4 old', OLD, [preFloorTodo(OLD)])]);

        await saveAll();

        expect(await screen.findByTestId('confirm-modal-confirm')).toBeInTheDocument();
        expect(confirmMessage(), 'the date question').toBe(preFloorMessage(1));
        expect(commit).not.toHaveBeenCalled();
    });

    it('Cancel returns to the grid: nothing committed, the banner and the rows still there, and a second Save All asks again', async () => {
        const commit = await commitCalls();
        await importIntoNewEditor([deposit('D-P4 old', OLD, [preFloorTodo(OLD)])]);
        await saveAll();
        await screen.findByTestId('confirm-modal-cancel');

        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await settle();

        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());
        expect(commit).not.toHaveBeenCalled();
        expect(screen.getByTestId('tx-bulk-pre-floor')).toHaveAttribute('data-count', '1');
        expect(rowStatus(gridRowDescribed('D-P4 old'))).toBe('new');

        await saveAll();
        expect(confirmMessage(), 'asked again').toBe(preFloorMessage(1));
        expect(commit).not.toHaveBeenCalled();
    });

    it('Confirm commits, once, with the date as it is', async () => {
        const commit = await commitCalls();
        await importIntoNewEditor([deposit('D-P4 old', OLD, [preFloorTodo(OLD)])]);
        await saveAll();
        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));
        await settle();

        await waitFor(() => expect(commit).toHaveBeenCalledTimes(1));
        const payload = commit.mock.calls[0]?.[0] as {creates?: Array<{date?: string}>};
        expect(payload.creates?.map((create) => create.date)).toEqual([OLD]);
    });

    it('two rows before 1900 are ONE question, naming the count', async () => {
        const commit = await commitCalls();
        await importIntoNewEditor([deposit('D-P4 old', OLD, [preFloorTodo(OLD)]), deposit('D-P4 other old', OTHER_OLD, [preFloorTodo(OTHER_OLD)]), deposit('D-P4 normal', NORMAL)]);

        await saveAll();
        expect(confirmMessage()).toBe(preFloorMessage(2));
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await settle();

        await waitFor(() => expect(commit).toHaveBeenCalledTimes(1));
        expect(screen.queryByTestId('confirm-modal-confirm'), 'no second question').toBeNull();
        const payload = commit.mock.calls[0]?.[0] as {creates?: Array<{date?: string}>};
        expect(payload.creates?.map((create) => create.date).sort()).toEqual([OLD, OTHER_OLD, NORMAL].sort());
    });

    it('the order of the gates: the fields to verify first, then the date; Cancel on the first stops everything', async () => {
        const commit = await commitCalls();
        await importIntoNewEditor([deposit('D-P4 old', OLD, [preFloorTodo(OLD)]), deposit('D-P4 generic', NORMAL, [genericTodo()])]);

        await saveAll();
        expect(confirmMessage(), 'first the fields to verify (one row, the generic one: the date todo is not counted)').toBe(warningsMessage(1));
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await settle();
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());
        expect(commit).not.toHaveBeenCalled();

        await saveAll();
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(confirmMessage(), 'then the date').toBe(preFloorMessage(1)));
        expect(commit).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await settle();
        await waitFor(() => expect(commit).toHaveBeenCalledTimes(1));
    });

    it('Cancel on the date question after the fields to verify were confirmed commits nothing', async () => {
        const commit = await commitCalls();
        await importIntoNewEditor([deposit('D-P4 old', OLD, [preFloorTodo(OLD)]), deposit('D-P4 generic', NORMAL, [genericTodo()])]);
        await saveAll();
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(confirmMessage()).toBe(preFloorMessage(1)));

        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await settle();

        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());
        expect(commit).not.toHaveBeenCalled();
    });
});

// ---------------------------------------------------------------------------
// 66 F6 (choice A) — delete a parent and keep its charges: `unlinkIds` on the delete intent
// ---------------------------------------------------------------------------

/**
 * «Keep the charges» (V1) opens the editor with `{action: 'delete', txIds: [parent], unlinkIds: [charges]}`. The contract
 * (66-F6 §3, choice A; re-targeted by 66-F7 §10-§11 in F7-b — same behaviour, new mechanism: each charge kept is an
 * operation of its own, `chargeOf` the parent and `parentUnlink`, instead of the `chargeUnlinks` list):
 *   - the parent is a row, marked for deletion; since F7-b (§11.1: no operation that writes is invisible) each charge kept
 *     is a row too, «edited» by its unlink alone (§11.3) — F6 had them off the grid;
 *   - since F7-c1 (§13.5, §13.9) the charges kept sit indented under their parent (the group opens by itself on a parent
 *     «del»): the label cell carries `data-charge-of` = the parent's row id and the state badge `tx-bulk-charge-state`
 *     says `unlink`. The F6 banner `tx-bulk-unlink-hint` is gone;
 *   - the batch unlinks them in the same request as the deletion: `updates` `{id, parent_transaction_id: 0}` beside
 *     `deletes: [parent]`, in the three places that build a payload — the nested Form's bulk context
 *     (`getBulkContextExcluding`), «Validate now» and «Save all»;
 *   - «Restore» on the parent (the row's mark-delete toggle) takes the unlinks back: no charge left «unlink», no update
 *     to 0, and the parent no longer deleted;
 *   - a delete intent without `unlinkIds` is today's: no banner, no updates.
 *
 * Payloads are read from the mocked `validateTransactions` / `commitTransactions` (the last call, after the click that
 * sends it) and from the Form probe's `getBulkContext`. Rows are found by the `#id` their ID cell shows.
 */
describe('TransactionBulkModal — 66 F6: delete a parent, keep its charges (unlinkIds)', () => {
    const PARENT: TXReadItem = {...SAVED_BUY, id: 91_501, charges_count: 2, description: 'F6 parent'};
    const FEE: TXReadItem = {
        id: 91_502,
        broker_id: 77,
        asset_id: null,
        type: 'FEE',
        date: PARENT.date,
        quantity: '0',
        cash: {code: 'EUR', amount: '-1.500000'},
        related_transaction_id: null,
        partner_broker_id: null,
        parent_transaction_id: PARENT.id,
        tags: [],
        description: 'F6 fee',
        cost_basis_override: null,
        asset_event_id: null,
    };
    const TAX: TXReadItem = {...FEE, id: 91_503, type: 'TAX', cash: {code: 'EUR', amount: '-0.500000'}, description: 'F6 tax'};

    type Payload = {creates?: unknown[]; updates?: Array<Record<string, unknown>>; deletes?: number[]};

    const api = async () => vi.mocked(await import('$lib/features/transactions/txCommitApi'));

    // F7-c1: one case stubs the charges read through an implementation, which `vi.clearAllMocks()` keeps.
    afterEach(() => {
        vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get).mockReset();
    });

    /** The editor opened by the delete intent on the parent, the charges in the store beside it. */
    async function openDelete(intent: WorkspaceIntent): Promise<void> {
        txStoreSetAll([PARENT, FEE, TAX], []);
        mountEditor(intent);
        await waitFor(() =>
            expect(
                gridRows().some((row) => idCellText(row).includes(`#${PARENT.id}`)),
                'premise: the parent is on screen',
            ).toBe(true),
        );
        await settle();
        expect(rowStatus(gridRow(PARENT.id)), 'premise: the parent is marked for deletion').toBe('delete');
    }

    /** The updates of a payload that unlink a charge (`parent_transaction_id: 0`), by id. */
    function unlinksOf(payload: Payload | undefined): Array<Record<string, unknown>> {
        return (payload?.updates ?? []).filter((update) => update.parent_transaction_id === 0);
    }

    /** «Validate now», and the payload it sent. */
    async function validateNow(): Promise<Payload> {
        const {validateTransactions} = await api();
        const before = validateTransactions.mock.calls.length;
        await fireEvent.click(screen.getByTestId('tx-bulk-validate-now'));
        await settle();
        await waitFor(() => expect(validateTransactions.mock.calls.length, 'a validate run went out').toBeGreaterThan(before));
        return validateTransactions.mock.calls.at(-1)?.[0] as Payload;
    }

    /** «Save all», and the payload it committed. */
    async function saveAll(): Promise<Payload> {
        const {commitTransactions} = await api();
        await fireEvent.click(screen.getByTestId('tx-bulk-commit'));
        await settle();
        await waitFor(() => expect(commitTransactions, 'Save all committed').toHaveBeenCalledTimes(1));
        return commitTransactions.mock.calls[0]?.[0] as Payload;
    }

    /** The nested Form's bulk context: the batch as the Form validates it. */
    function bulkContext(): Payload {
        return (formProbe().getBulkContext as () => Payload)();
    }

    /** «Restore» on the parent: the row's mark-delete toggle, through its right-click menu. */
    async function restoreParent(): Promise<void> {
        await fireEvent.contextMenu(gridRow(PARENT.id), {clientX: 10, clientY: 10});
        const thrown = await clickCollectingErrors(await screen.findByTestId('context-menu-action-mark-delete'));
        expect(thrown, 'Restore throws nothing').toEqual([]);
        expect(rowStatus(gridRow(PARENT.id)), 'premise: the parent is restored').toBe('original');
    }

    /** Invariant 1 of 66-F7 §3: every id once across the updates and the deletes. */
    function expectIdsOnce(payload: Payload): void {
        const ids = [...(payload.updates ?? []).map((update) => update.id as number), ...(payload.deletes ?? [])];
        expect(
            ids.filter((id, at) => ids.indexOf(id) !== at),
            'every id once across updates and deletes',
        ).toEqual([]);
    }

    /** F7-c1: the parent a row is indented under (`data-charge-of` on its label cell), `null` for a top-level row. */
    function chargeOfCell(row: HTMLElement): string | null {
        return row.querySelector('[data-testid="tx-bulk-row-label"]')?.getAttribute('data-charge-of') ?? null;
    }

    /** F7-c1: the state badge of an indented row (`linked`, `unlink`, `del`), `null` without one. */
    function chargeState(row: HTMLElement): string | null {
        return row.querySelector('[data-testid="tx-bulk-charge-state"]')?.getAttribute('data-state') ?? null;
    }

    const EXPECTED_UNLINKS = [
        {id: FEE.id, parent_transaction_id: 0},
        {id: TAX.id, parent_transaction_id: 0},
    ];

    // Re-targeted in F7-b (§11.1, §11.3): F6 kept the charges off the grid; each became a row of its own, named by the
    // banner. Re-targeted again in F7-c1 (§13.5, §13.9): the charges kept sit indented under their parent «del», their
    // group open by itself, each with the state «unlink»; the banner is gone.
    it('the parent is a row marked for deletion, each charge kept sits indented under it with the state «unlink»; no banner', async () => {
        await openDelete({action: 'delete', txIds: [PARENT.id], unlinkIds: [FEE.id, TAX.id]} as WorkspaceIntent);

        const parentRowId = gridRow(PARENT.id).getAttribute('data-row-id');
        await waitFor(() => expect(chargeOfCell(gridRow(FEE.id)), 'F7-c1: the FEE kept is indented under the parent').toBe(parentRowId));
        expect(chargeOfCell(gridRow(TAX.id)), 'F7-c1: the TAX kept is indented under the parent').toBe(parentRowId);
        expect(chargeState(gridRow(FEE.id)), 'the FEE kept says «unlink»').toBe('unlink');
        expect(chargeState(gridRow(TAX.id)), 'the TAX kept says «unlink»').toBe('unlink');
        expect(screen.queryByTestId('tx-bulk-unlink-hint'), 'F7-c1: the F6 banner is gone').toBeNull();
    });

    it('«Validate now» sends the deletion and the unlinks in one batch', async () => {
        await openDelete({action: 'delete', txIds: [PARENT.id], unlinkIds: [FEE.id, TAX.id]} as WorkspaceIntent);

        const payload = await validateNow();

        expect(payload.deletes).toEqual([PARENT.id]);
        expect(payload.updates ?? []).toEqual(expect.arrayContaining(EXPECTED_UNLINKS));
        expect(unlinksOf(payload), 'each charge unlinked once').toHaveLength(2);
        expectIdsOnce(payload);
    });

    it('the nested Form validates against the same batch: its bulk context carries the unlinks', async () => {
        await openDelete({action: 'delete', txIds: [PARENT.id], unlinkIds: [FEE.id, TAX.id]} as WorkspaceIntent);

        const context = bulkContext();

        expect(context.deletes).toEqual([PARENT.id]);
        expect(context.updates ?? []).toEqual(expect.arrayContaining(EXPECTED_UNLINKS));
    });

    it('«Save all» commits the deletion and the unlinks in one batch', async () => {
        await openDelete({action: 'delete', txIds: [PARENT.id], unlinkIds: [FEE.id, TAX.id]} as WorkspaceIntent);

        const payload = await saveAll();

        expect(payload.deletes).toEqual([PARENT.id]);
        expect(payload.updates ?? []).toEqual(expect.arrayContaining(EXPECTED_UNLINKS));
        expect(unlinksOf(payload), 'each charge unlinked once').toHaveLength(2);
        expectIdsOnce(payload);
    });

    // Re-targeted in F7-c1: the premise and the effect are read on the indented rows' state badge, not on the banner.
    it('«Restore» on the parent takes the unlinks back: no charge «unlink», no update to 0, the parent no longer deleted', async () => {
        await openDelete({action: 'delete', txIds: [PARENT.id], unlinkIds: [FEE.id, TAX.id]} as WorkspaceIntent);
        await waitFor(() => expect(chargeState(gridRow(FEE.id)), 'premise: the FEE kept says «unlink»').toBe('unlink'));

        await restoreParent();

        expect(document.querySelectorAll('[data-testid="tx-bulk-charge-state"][data-state="unlink"]'), 'no charge is left «unlink»').toHaveLength(0);
        const payload = await validateNow();
        expect(unlinksOf(payload), 'no charge is unlinked').toEqual([]);
        expect(payload.deletes ?? [], 'the parent is not deleted').not.toContain(PARENT.id);
        expect(unlinksOf(bulkContext()), 'nor in the Form bulk context').toEqual([]);
    });

    // Re-targeted in F7-c1 (coordinator's decision, 19/11): the Bulk reads the charges of a saved parent on entry (§14.2);
    // under a parent already «del» they arrive with the F7-b interim, unlinked. Before F7-c1 this intent sent the deletion
    // alone, a batch the backend refuses (`chargesDeleteIncomplete`) for a parent that has charges.
    it('a delete intent without unlinkIds: the charges read on entry arrive under the parent «del», unlinked; the deletion and two unlinks', async () => {
        vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get).mockImplementation((async (args: {queries?: {parent_ids?: number[]}} | undefined) => [FEE, TAX].filter((row) => (args?.queries?.parent_ids ?? []).includes(row.parent_transaction_id ?? -1))) as never);
        await openDelete({action: 'delete', txIds: [PARENT.id]});

        // A parent «del» opens its group: the charges read sit under it, «unlink».
        await waitFor(() => expect(chargeState(gridRow(FEE.id)), 'the FEE read sits under the parent «del», unlinked').toBe('unlink'));
        expect(chargeState(gridRow(TAX.id)), 'the TAX read sits under the parent «del», unlinked').toBe('unlink');
        expect(screen.queryByTestId('tx-bulk-unlink-hint')).toBeNull();
        const validated = await validateNow();
        expect(validated.deletes).toEqual([PARENT.id]);
        expect(validated.updates ?? []).toEqual(expect.arrayContaining(EXPECTED_UNLINKS));
        expect(unlinksOf(validated), 'each charge unlinked once').toHaveLength(2);
        expect(validated.creates ?? []).toEqual([]);
        expectIdsOnce(validated);
        const committed = await saveAll();
        expect(committed.deletes).toEqual([PARENT.id]);
        expect(committed.updates ?? []).toEqual(expect.arrayContaining(EXPECTED_UNLINKS));
        expect(unlinksOf(committed), 'each charge unlinked once').toHaveLength(2);
        expectIdsOnce(committed);
    });
});

// ---------------------------------------------------------------------------
// 66 F7-b — the charges are operations of the Bulk (model H): the parent's form, the payload, the reset, the close guard
// ---------------------------------------------------------------------------

/**
 * Contract 66-F7 §10, corrected by §11. A charge brought into the Bulk is an operation of its own, owned by its parent
 * (`chargeOf`); in F7-b it stays a visible row of the grid (§11.1). The parent's form receives its charges as drafts
 * (`_charges` on the row it opens on, always — `[]` too — with `allowChargeEdits`), and its answer goes back onto the
 * operations (`applyChargeDrafts`). Asserted on what the editor really sends: the bodies of «Validate now» and «Save all»
 * (the mocked `validateTransactions` / `commitTransactions`) and the nested Form's bulk context, and on the props the
 * editor hands its Form (the probe).
 *
 * The drafts pushed back are always the ones the probe was handed, modified: a key the editor did not make cannot match.
 *
 * Before opening a saved parent with `charges_count > 0` and no charge in the Bulk, the editor reads its charges
 * (`GET /transactions?parent_ids=…`, the same call the Form makes, `query_transactions_api_v1_transactions_get`): stubbed
 * here to answer by `parent_ids` from the rows given.
 */
describe('TransactionBulkModal — 66 F7-b: the charges as operations of the Bulk', () => {
    const BUY: TXReadItem = {...SAVED_BUY, id: 91_601, charges_count: 2, description: 'F7b parent'};
    const FEE: TXReadItem = {
        id: 91_602,
        broker_id: 77,
        asset_id: 101,
        type: 'FEE',
        date: BUY.date,
        quantity: '0',
        cash: {code: 'EUR', amount: '-1.500000'},
        related_transaction_id: null,
        partner_broker_id: null,
        parent_transaction_id: BUY.id,
        tags: [],
        description: 'F7b fee',
        cost_basis_override: null,
        asset_event_id: null,
    };
    const TAX: TXReadItem = {...FEE, id: 91_603, type: 'TAX', cash: {code: 'EUR', amount: '-0.500000'}, description: 'F7b tax'};
    /** A saved BUY with no charge. */
    const LONE_BUY: TXReadItem = {...SAVED_BUY, id: 91_611, charges_count: 0, description: 'F7b lone parent'};

    // The charges read answers through a mockImplementation, which `vi.clearAllMocks()` keeps: reset it after each case.
    afterEach(() => {
        vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get).mockReset();
    });

    type Payload = {creates?: Array<Record<string, unknown>>; updates?: Array<Record<string, unknown>>; deletes?: number[]};
    type FormRow = TXReadItem & {_charges?: ChargeDraft[]};

    const api = async () => vi.mocked(await import('$lib/features/transactions/txCommitApi'));

    /** The charges read answers by `parent_ids`, from these rows. */
    function answerChargesRead(rows: TXReadItem[]): void {
        vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get).mockImplementation((async (args: {queries?: {parent_ids?: number[]}} | undefined) => {
            const parents = args?.queries?.parent_ids ?? [];
            return rows.filter((row) => row.parent_transaction_id != null && parents.includes(row.parent_transaction_id));
        }) as never);
    }

    /** The row the Form is open on, as the editor hands it. */
    function formRow(): FormRow | undefined {
        return (formProbe().items as FormRow[] | null)?.[0];
    }

    /** The drafts the editor handed the Form, or a failure. */
    function handedDrafts(): ChargeDraft[] {
        const drafts = formRow()?._charges;
        if (!Array.isArray(drafts)) throw new Error('the editor handed the Form no _charges');
        return drafts;
    }

    /** Wait for the Form open on `txId` (0 for a new row) with `count` drafts handed. */
    async function waitForParentForm(txId: number, count: number): Promise<void> {
        await waitFor(() => {
            expect(formProbe().open, 'the Form is open').toBe(true);
            expect(formRow()?.id, 'on the parent').toBe(txId);
            expect(formRow()?._charges, 'the editor hands the Form the parent’s charges as drafts (_charges)').toHaveLength(count);
        });
    }

    /** The saved BUY of this describe as the Form pushes it back unchanged (signed values, W-B65), with `over` applied. */
    function buyPayload(over: Record<string, unknown> = {}): Record<string, unknown> {
        return {
            broker_id: BUY.broker_id,
            type: 'BUY',
            date: BUY.date,
            quantity: '1.000000',
            asset_id: BUY.asset_id,
            cash: {code: 'EUR', amount: '-10.000000'},
            description: BUY.description,
            _cost_basis_mode: 'auto',
            _wac_currency_hint: null,
            ...over,
        };
    }

    /** A new charge as the Form adds it (`newCharge`), with an amount and a note typed. */
    function newDraft(type: 'FEE' | 'TAX', amount: string, description: string): ChargeDraft {
        return {key: 'new-1', id: null, type, cash: {amount, code: 'EUR'}, description, original: null, state: 'linked'};
    }

    /** «Apply» in the Form: the payload pushed back; ends on the Form closed. */
    async function push(payload: Record<string, unknown>): Promise<void> {
        (formProbe().onPushDraft as (payload: Record<string, unknown>) => void)(payload);
        flushSync();
        await settle();
        expect(formProbe().open, 'Apply closes the Form').toBe(false);
    }

    /** The row's own action, through its right-click menu. */
    async function rowAction(row: HTMLElement, action: string): Promise<void> {
        await fireEvent.contextMenu(row, {clientX: 10, clientY: 10});
        const thrown = await clickCollectingErrors(await screen.findByTestId(`context-menu-action-${action}`));
        expect(thrown, `${action} throws nothing`).toEqual([]);
    }

    async function validateNow(): Promise<Payload> {
        const {validateTransactions} = await api();
        const before = validateTransactions.mock.calls.length;
        await fireEvent.click(screen.getByTestId('tx-bulk-validate-now'));
        await settle();
        await waitFor(() => expect(validateTransactions.mock.calls.length, 'a validate run went out').toBeGreaterThan(before));
        return validateTransactions.mock.calls.at(-1)?.[0] as Payload;
    }

    async function saveAll(): Promise<Payload> {
        const {commitTransactions} = await api();
        await fireEvent.click(screen.getByTestId('tx-bulk-commit'));
        await settle();
        await waitFor(() => expect(commitTransactions, 'Save all committed').toHaveBeenCalledTimes(1));
        return commitTransactions.mock.calls[0]?.[0] as Payload;
    }

    function bulkContext(): Payload {
        return (formProbe().getBulkContext as () => Payload)();
    }

    /** Invariant 1 of §3: every id once across the updates and the deletes. */
    function expectIdsOnce(payload: Payload, where: string): void {
        const ids = [...(payload.updates ?? []).map((update) => update.id as number), ...(payload.deletes ?? [])];
        expect(
            ids.filter((id, at) => ids.indexOf(id) !== at),
            `${where}: every id once across updates and deletes`,
        ).toEqual([]);
    }

    /** The one create of this type in a body, or a failure saying how many. */
    function onlyCreate(payload: Payload, type: string, where: string): Record<string, unknown> {
        const found = (payload.creates ?? []).filter((create) => create.type === type);
        expect(found, `${where}: one ${type} create`).toHaveLength(1);
        return found[0];
    }

    /** The editor on an edit intent of the saved BUY, its two charges in the store and behind the read; ends on its Form open. */
    async function openSavedParent(): Promise<void> {
        txStoreSetAll([BUY, FEE, TAX], []);
        answerChargesRead([FEE, TAX]);
        mountEditor({action: 'edit', txIds: [BUY.id]});
        await waitForParentForm(BUY.id, 2);
    }

    // -----------------------------------------------------------------------
    // 2 — the round trip with the parent's form, on the real bodies
    // -----------------------------------------------------------------------

    it('the Form of a saved parent gets allowChargeEdits and its saved charges as drafts: original from the store, state linked', async () => {
        await openSavedParent();

        expect(formProbe().allowChargeEdits, 'the Bulk saves the charges the Form edits').toBe(true);
        const drafts = handedDrafts();
        const fee = drafts.find((draft) => draft.key === `saved-${FEE.id}`);
        const tax = drafts.find((draft) => draft.key === `saved-${TAX.id}`);
        expect(fee, 'the FEE, keyed by its id').toMatchObject({id: FEE.id, type: 'FEE', description: 'F7b fee', state: 'linked', original: {type: 'FEE', description: 'F7b fee'}});
        expect(tax, 'the TAX, keyed by its id').toMatchObject({id: TAX.id, type: 'TAX', description: 'F7b tax', state: 'linked', original: {type: 'TAX', description: 'F7b tax'}});
    });

    it('a new FEE, the TAX note changed and the FEE unlinked in the parent’s Form: one create under the parent, two updates, in Validate and in Save all', async () => {
        await openSavedParent();
        const drafts = handedDrafts().map((draft): ChargeDraft => {
            if (draft.id === TAX.id) return {...draft, description: 'F7b tax note changed'};
            if (draft.id === FEE.id) return {...draft, state: 'unlink'};
            return draft;
        });

        await push(buyPayload({_charges: [...drafts, newDraft('FEE', '2', 'F7b new fee')]}));

        // §11.1: every operation that writes is a row. F7-c1: the TAX sits indented in its parent's group, which a charge
        // created in the parent's Form opens (§14.7); the FEE unlinked from a parent that stays is a top-level row.
        expect(rowStatus(gridRow(TAX.id)), 'the TAX is a row, edited').toBe('edited');
        expect(rowStatus(gridRow(FEE.id)), 'the FEE is a row, edited by its unlink').toBe('edited');
        expect(rowStatus(gridRowDescribed('F7b new fee')), 'the new FEE is a row, new').toBe('new');

        const validated = await validateNow();
        const committed = await saveAll();
        for (const [where, body] of [
            ['validate', validated],
            ['commit', committed],
        ] as const) {
            const create = onlyCreate(body, 'FEE', where);
            expect(create, `${where}: the new FEE names its saved parent by id and takes its broker, asset and date`).toMatchObject({
                broker_id: BUY.broker_id,
                asset_id: BUY.asset_id,
                date: BUY.date,
                parent_transaction_id: BUY.id,
                cash: {code: 'EUR', amount: '-2'},
                description: 'F7b new fee',
            });
            expect(create, `${where}: a saved parent is named by id, never by ref`).not.toHaveProperty('parent_ref');
            expect(body.updates ?? [], `${where}: the TAX sends its note only`).toContainEqual({id: TAX.id, description: 'F7b tax note changed'});
            expect(body.updates ?? [], `${where}: the FEE sends its unlink only`).toContainEqual({id: FEE.id, parent_transaction_id: 0});
            expect(
                (body.updates ?? []).filter((update) => update.id === BUY.id),
                `${where}: the parent itself did not change`,
            ).toEqual([]);
            expect(body.deletes ?? [], `${where}: nothing deleted`).toEqual([]);
            expectIdsOnce(body, where);
        }
    });

    // -----------------------------------------------------------------------
    // 3 — a new parent with a new charge: ref / parent_ref, and the charge follows the parent's date
    // -----------------------------------------------------------------------

    it('a new BUY with a new FEE from its Form: the BUY carries a ref, the FEE names it by parent_ref, and follows the BUY’s date when it changes', async () => {
        mountEditor({action: 'create'});
        await waitFor(() => expect(formProbe().open, 'a create intent opens the Form').toBe(true));
        expect(formProbe().allowChargeEdits, 'the Form of a new row in the Bulk edits charges too').toBe(true);

        await push(buyPayload({description: 'F7b new buy', date: '2026-09-13', _charges: [newDraft('FEE', '1.25', 'F7b new fee')]}));
        expect(rowStatus(gridRowDescribed('F7b new buy')), 'premise: the new BUY is a row').toBe('new');
        expect(rowStatus(gridRowDescribed('F7b new fee')), 'the new FEE is a row').toBe('new');

        const first = await validateNow();
        const buy = onlyCreate(first, 'BUY', 'validate');
        const fee = onlyCreate(first, 'FEE', 'validate');
        expect(typeof buy.ref, 'the new parent carries a ref').toBe('string');
        expect((buy.ref as string).length, 'a ref of at most 36 characters (the schema’s limit)').toBeGreaterThan(0);
        expect((buy.ref as string).length).toBeLessThanOrEqual(36);
        expect(fee, 'the new FEE names the new BUY by its ref, with its broker, asset and date').toMatchObject({parent_ref: buy.ref, broker_id: 77, asset_id: 101, date: '2026-09-13'});
        expect(fee, 'a new parent is named by ref, never by id').not.toHaveProperty('parent_transaction_id');

        // The user changes the BUY's date in its Form; the FEE was never opened on its own, so it follows (§11.4).
        await rowAction(gridRowDescribed('F7b new buy'), 'edit-single');
        await waitForParentForm(0, 1);
        const handed = handedDrafts();
        expect(handed[0], 'the new FEE comes back as a draft of its parent, keyed by its operation').toMatchObject({id: null, original: null, description: 'F7b new fee', state: 'linked'});
        expect(handed[0].key.startsWith('op-'), `the key names the operation: ${handed[0].key}`).toBe(true);
        await push(buyPayload({description: 'F7b new buy', date: '2026-09-20', _charges: handed}));

        const context = bulkContext();
        expect(onlyCreate(context, 'FEE', 'bulk context'), 'the Form’s bulk context: the FEE follows the BUY’s new date').toMatchObject({date: '2026-09-20'});
        const second = await validateNow();
        expect(onlyCreate(second, 'FEE', 'validate'), 'validate: the FEE follows the BUY’s new date').toMatchObject({date: '2026-09-20', parent_ref: onlyCreate(second, 'BUY', 'validate').ref});
        const committed = await saveAll();
        const committedBuy = onlyCreate(committed, 'BUY', 'commit');
        expect(committedBuy).toMatchObject({date: '2026-09-20'});
        expect(onlyCreate(committed, 'FEE', 'commit'), 'commit: the FEE follows the BUY’s new date, and names it by ref').toMatchObject({date: '2026-09-20', parent_ref: committedBuy.ref});
    });

    // -----------------------------------------------------------------------
    // 4 — a reset of the parent keeps its charges attached (§11.2)
    // -----------------------------------------------------------------------

    it.each([
        ['the row’s Reset', 'row'],
        ['Reset all', 'all'],
    ] as const)('%s on the parent keeps its charges attached: the new FEE still names it, its Form still lists all three', async (_label, how) => {
        await openSavedParent();
        await push(buyPayload({description: 'F7b parent edited', _charges: [...handedDrafts(), newDraft('FEE', '2', 'F7b new fee')]}));
        expect(rowStatus(gridRow(BUY.id)), 'premise: the parent is edited, so it can be reset').toBe('edited');

        if (how === 'row') await rowAction(gridRow(BUY.id), 'reset');
        else expect(await clickCollectingErrors(screen.getByTestId('tx-bulk-reset-all')), 'Reset all throws nothing').toEqual([]);

        expect({status: rowStatus(gridRow(BUY.id)), description: rowDescription(gridRow(BUY.id))}, 'the parent is back as saved').toEqual({status: 'original', description: 'F7b parent'});
        const body = await validateNow();
        expect(onlyCreate(body, 'FEE', 'validate'), 'the new FEE still names its parent, and takes its broker, asset and date').toMatchObject({
            parent_transaction_id: BUY.id,
            broker_id: BUY.broker_id,
            asset_id: BUY.asset_id,
            date: BUY.date,
        });
        expect(
            (body.updates ?? []).filter((update) => update.id === BUY.id),
            'the parent sends nothing',
        ).toEqual([]);

        // chargeOf followed the parent's new tempId: its Form finds all three of its charges.
        await rowAction(gridRow(BUY.id), 'edit-single');
        await waitForParentForm(BUY.id, 3);
        const keys = handedDrafts().map((draft) => draft.key);
        expect(keys).toEqual(expect.arrayContaining([`saved-${FEE.id}`, `saved-${TAX.id}`]));
        expect(
            handedDrafts().filter((draft) => draft.id === null && draft.description === 'F7b new fee'),
            'the new FEE is still the parent’s',
        ).toHaveLength(1);
    });

    // -----------------------------------------------------------------------
    // 5 — opening the parent's Form and leaving it changes nothing (§11.6)
    // -----------------------------------------------------------------------

    it.each([
        ['Cancel', 'cancel'],
        ['Apply with nothing changed', 'apply'],
    ] as const)('%s on the Form of a saved parent whose charges were read: Save all stays off and closing asks nothing', async (_label, how) => {
        const {onClose} = await (async () => {
            txStoreSetAll([BUY, FEE, TAX], []);
            answerChargesRead([FEE, TAX]);
            const mounted = mountEditor({action: 'edit', txIds: [BUY.id]});
            await waitForParentForm(BUY.id, 2);
            return mounted;
        })();
        // Presence barrier: the charges were read and are operations of the Bulk. Re-targeted in F7-c1 (§13.4, §14.2): a
        // charge the Bulk read itself sits in its parent's group, closed — the parent's chip counts them, unchanged.
        const chipId = `tx-bulk-charges-toggle-${gridRow(BUY.id).getAttribute('data-row-id')}`;
        await waitFor(() => expect(screen.getByTestId(chipId), 'the parent’s chip counts the two charges read').toHaveAttribute('data-charges-count', '2'));
        expect(screen.getByTestId(chipId), 'the charges read are unchanged').not.toHaveAttribute('data-charges-modified', 'true');

        if (how === 'cancel') {
            (formProbe().onClose as () => void)();
            flushSync();
            await settle();
        } else {
            await push(buyPayload({_charges: handedDrafts()}));
        }

        expect(formProbe().open, 'premise: the Form is closed').toBe(false);
        expect(rowStatus(gridRow(BUY.id)), 'the parent is unchanged').toBe('original');
        expect(screen.getByTestId(chipId), 'its charges are unchanged').not.toHaveAttribute('data-charges-modified', 'true');
        expect(screen.getByTestId('tx-bulk-commit'), 'nothing to save: Save all stays off').toBeDisabled();
        await fireEvent.click(screen.getByTestId('tx-bulk-close'));
        await settle();
        expect(screen.queryByTestId('confirm-modal-confirm'), 'no «Discard changes?»: the rows read for the Form are no change').toBeNull();
        expect(onClose, 'the editor closes at once').toHaveBeenCalledTimes(1);
    });

    it('the Form of a saved parent with no charge gets _charges = [] (never reads on its own) and allowChargeEdits', async () => {
        txStoreSetAll([LONE_BUY], []);
        answerChargesRead([]);
        mountEditor({action: 'edit', txIds: [LONE_BUY.id]});

        await waitForParentForm(LONE_BUY.id, 0);
        expect(handedDrafts()).toEqual([]);
        expect(formProbe().allowChargeEdits).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// 66 F7-c1 — the grid BK2: linked charges grouped under their parent, and the read of a saved parent's charges on entry
// ---------------------------------------------------------------------------

/**
 * Contract 66-F7 §13 (F7-c1 part), corrected by §14 (which wins). What the editor shows and does:
 *
 *   - Entry load (§14.2): a saved parent entering the Bulk with `charges_count` above the charges it holds makes the Bulk
 *     read them (`GET /transactions?parent_ids=<id>`, `query_transactions_api_v1_transactions_get`) and add them as
 *     unchanged edit operations, adopted (`loadedWithParent`). While a read is in flight «Save all» is off; an answer
 *     that arrives after a reopen or a reset is dropped (a generation number); the close guard's baseline always holds
 *     the operations read, so closing an editor the user did not change asks nothing; a failed read raises an error
 *     toast and leaves «del» on that parent off, with a reason.
 *   - The chip (§13.4, §14.8): in the parent's Type cell, `<button data-testid="tx-bulk-charges-toggle-<tempId>"
 *     aria-expanded data-charges-count="N">`, N = the charges under it (`isUnderParent`); a click opens and closes the
 *     group and nothing else; `data-charges-modified="true"` when one of its charges is not `original` — the parent's
 *     own status does not change.
 *   - The indented row (§13.5–§13.6): the label cell carries `data-charge-of="<parent tempId>"` and `↳`; its own selection
 *     checkbox (66 TL-4, P-2 = C: was «no checkbox»; ticking the parent never ticks it, nor the reverse); a state badge `tx-bulk-charge-state` with `data-state="linked|unlink|del"`; its menu offers «Delete» /
 *     «Restore» only; a double-click opens its own Form.
 *   - A charge unlinked from a parent that stays is a top-level row, with the badge `unlink` (§13.1).
 *   - The group opens by itself when the parent is «del», when the charges came in the intent with the parent, when a
 *     charge is created or linked in the parent's Form; it starts closed for the charges the Bulk read itself (§14.7).
 *   - Order (§14.5): one order, ours — the top-level rows by date (the header's direction), each open parent followed by
 *     its charges.
 *   - Selection (§14.6, reversed by 66 TL-4): a selected top-level row that becomes indented stays selected; only the
 *     half a merge hides leaves the selection.
 *   - «Remove from batch» on a saved parent takes along its charges read by the Bulk and still unchanged; any other
 *     stays, as a top-level row without a parent (§14.2).
 *   - Issues (§13.8, §14.3): a refusal on a charge of a closed group is in the banner with the derived label
 *     (`<parent>·k`), and a click on it opens the group and goes to the charge's row.
 *
 * Rows are found by the `#id` their ID cell shows, never by position; the order assertions read the ids of the rows in
 * DOM order, which IS the subject there. The charges read is stubbed by `parent_ids`; a read held by a test is released
 * by the test itself. The parent's row id (its `tempId`) is read from the grid, never assumed.
 */
describe('TransactionBulkModal — 66 F7-c1: the charges grouped under their parent, and read on entry', () => {
    const BUY: TXReadItem = {...SAVED_BUY, id: 91_701, charges_count: 2, description: 'F7c1 parent'};
    const FEE: TXReadItem = {
        id: 91_702,
        broker_id: 77,
        asset_id: 101,
        type: 'FEE',
        date: BUY.date,
        quantity: '0',
        cash: {code: 'EUR', amount: '-1.500000'},
        related_transaction_id: null,
        partner_broker_id: null,
        parent_transaction_id: BUY.id,
        tags: [],
        description: 'F7c1 fee',
        cost_basis_override: null,
        asset_event_id: null,
    };
    const TAX: TXReadItem = {...FEE, id: 91_703, type: 'TAX', cash: {code: 'EUR', amount: '-0.500000'}, description: 'F7c1 tax'};
    /** An unrelated saved row, a day after the BUY: opening on two rows keeps the Form shut, and it gives an action to take. */
    const DEP: TXReadItem = {
        id: 91_711,
        broker_id: 77,
        asset_id: null,
        type: 'DEPOSIT',
        date: '2026-09-14',
        quantity: '0',
        cash: {code: 'EUR', amount: '100.000000'},
        related_transaction_id: null,
        partner_broker_id: null,
        parent_transaction_id: null,
        tags: [],
        description: 'F7c1 deposit',
        cost_basis_override: null,
        asset_event_id: null,
    };

    type Payload = {creates?: Array<Record<string, unknown>>; updates?: Array<Record<string, unknown>>; deletes?: number[]};
    type FormRow = TXReadItem & {_charges?: ChargeDraft[]};
    type ReadArgs = {queries?: {parent_ids?: number[]}} | undefined;
    type HeldRead = {parents: number[]; resolve: (rows: TXReadItem[]) => void; reject: (error: unknown) => void};

    const readMock = () => vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get);
    const api = async () => vi.mocked(await import('$lib/features/transactions/txCommitApi'));
    const toastsMock = async () => vi.mocked((await import('$lib/stores/app/toastStore.svelte')).toasts);

    let heldReads: HeldRead[] = [];

    beforeEach(() => {
        heldReads = [];
    });

    // The read, the validate and the commit answer through implementations, which `vi.clearAllMocks()` keeps: put the
    // describe-wide defaults back after each case.
    afterEach(async () => {
        readMock().mockReset();
        const {validateTransactions, commitTransactions} = await api();
        validateTransactions.mockImplementation((async () => ({committed: true, issues: [], rawResponse: {wac_results: []}})) as never);
        commitTransactions.mockImplementation((async () => ({committed: true, results: [], issues: []})) as never);
    });

    /** The rows of `rows` whose parent is among `parents`. */
    function chargesOf(parents: number[], rows: TXReadItem[]): TXReadItem[] {
        return rows.filter((row) => row.parent_transaction_id != null && parents.includes(row.parent_transaction_id));
    }

    /** The charges read answers at once, by `parent_ids`, from these rows. */
    function answerChargesRead(rows: TXReadItem[]): void {
        readMock().mockImplementation((async (args: ReadArgs) => chargesOf(args?.queries?.parent_ids ?? [], rows)) as never);
    }

    /** Every charges read is held until the test releases it (`heldReads`, one entry per call, in call order). */
    function holdChargesReads(): void {
        readMock().mockImplementation(((args: ReadArgs) => new Promise<TXReadItem[]>((resolve, reject) => heldReads.push({parents: args?.queries?.parent_ids ?? [], resolve, reject}))) as never);
    }

    /** Release the held read `at` with the charges of its parents among FEE and TAX. */
    async function releaseRead(at: number): Promise<void> {
        const read = heldReads[at];
        if (!read) throw new Error(`no charges read #${at} was made (made: ${heldReads.length})`);
        read.resolve(chargesOf(read.parents, [FEE, TAX]));
        await settle();
    }

    /** Whether the editor asked for the charges of `parentId`. */
    function readAskedFor(parentId: number): boolean {
        return readMock().mock.calls.some((call) => ((call[0] as ReadArgs)?.queries?.parent_ids ?? []).includes(parentId));
    }

    /** The grid rows of a saved transaction (0 or more), by the id their ID cell shows. */
    function rowsOf(txId: number): HTMLElement[] {
        return gridRows().filter((row) => idCellText(row).includes(`#${txId}`));
    }

    /** The parent's row id (its tempId), read from the grid. */
    function buyRowId(): string {
        const id = gridRow(BUY.id).getAttribute('data-row-id');
        if (!id) throw new Error('the BUY row publishes no data-row-id');
        return id;
    }

    /** The BUY's chip, or null. */
    function chip(): HTMLElement | null {
        return screen.queryByTestId(`tx-bulk-charges-toggle-${buyRowId()}`);
    }

    /** The BUY's chip, which must be there. */
    function theChip(): HTMLElement {
        const found = chip();
        if (!found) throw new Error(`the BUY row has no chip tx-bulk-charges-toggle-${buyRowId()}`);
        return found;
    }

    /** The parent a row is indented under, `null` for a top-level row. */
    function chargeOfCell(row: HTMLElement): string | null {
        return row.querySelector('[data-testid="tx-bulk-row-label"]')?.getAttribute('data-charge-of') ?? null;
    }

    /** The state badge of a charge row (`linked`, `unlink`, `del`), `null` without one. */
    function chargeState(row: HTMLElement): string | null {
        return row.querySelector('[data-testid="tx-bulk-charge-state"]')?.getAttribute('data-state') ?? null;
    }

    /** Every indented row of the grid. */
    function indentedRows(): HTMLElement[] {
        return gridRows().filter((row) => chargeOfCell(row) !== null);
    }

    /** The selection checkbox of a row, or null. */
    function rowCheckbox(row: HTMLElement): HTMLElement | null {
        return row.querySelector<HTMLElement>(`[data-testid="dt-row-checkbox-${row.getAttribute('data-row-id')}"]`);
    }

    /** The ids of the grid's rows, in DOM order (the subject of the order cases). */
    function gridTxIds(): number[] {
        return gridRows().map((row) => Number((idCellText(row).match(/#(\d+)/) ?? [])[1]));
    }

    function formRow(): FormRow | undefined {
        return (formProbe().items as FormRow[] | null)?.[0];
    }

    function handedDrafts(): ChargeDraft[] {
        const drafts = formRow()?._charges;
        if (!Array.isArray(drafts)) throw new Error('the editor handed the Form no _charges');
        return drafts;
    }

    async function waitForParentForm(txId: number, count: number): Promise<void> {
        await waitFor(() => {
            expect(formProbe().open, 'the Form is open').toBe(true);
            expect(formRow()?.id, 'on the parent').toBe(txId);
            expect(formRow()?._charges, 'the parent’s charges as drafts').toHaveLength(count);
        });
    }

    /** The saved BUY as the Form pushes it back unchanged (signed values, W-B65), with `over` applied. */
    function buyPayload(over: Record<string, unknown> = {}): Record<string, unknown> {
        return {
            broker_id: BUY.broker_id,
            type: 'BUY',
            date: BUY.date,
            quantity: '1.000000',
            asset_id: BUY.asset_id,
            cash: {code: 'EUR', amount: '-10.000000'},
            description: BUY.description,
            _cost_basis_mode: 'auto',
            _wac_currency_hint: null,
            ...over,
        };
    }

    function newDraft(type: 'FEE' | 'TAX', amount: string, description: string): ChargeDraft {
        return {key: 'new-1', id: null, type, cash: {amount, code: 'EUR'}, description, original: null, state: 'linked'};
    }

    /** «Apply» in the Form; ends on the Form closed. */
    async function push(payload: Record<string, unknown>): Promise<void> {
        (formProbe().onPushDraft as (payload: Record<string, unknown>) => void)(payload);
        flushSync();
        await settle();
        expect(formProbe().open, 'Apply closes the Form').toBe(false);
    }

    /** Open a row's right-click menu; ends on the menu drawn. */
    async function openMenu(row: HTMLElement): Promise<void> {
        await fireEvent.contextMenu(row, {clientX: 10, clientY: 10});
        await screen.findByTestId('context-menu');
    }

    /** The row's own action, through its right-click menu. */
    async function rowAction(row: HTMLElement, action: string): Promise<void> {
        await openMenu(row);
        const thrown = await clickCollectingErrors(await screen.findByTestId(`context-menu-action-${action}`));
        expect(thrown, `${action} throws nothing`).toEqual([]);
    }

    /** Open the BUY's Form from its menu, with its `count` charges handed as drafts. */
    async function openBuyForm(count: number): Promise<void> {
        await rowAction(gridRow(BUY.id), 'edit-single');
        await waitForParentForm(BUY.id, count);
    }

    /** The editor on an edit intent of the BUY and the DEPOSIT (two rows: no Form opens by itself), the charges only
     *  behind the read. Ends on the grid holding both rows. */
    async function openBuyAndDeposit(): Promise<ReturnType<typeof mountEditor>> {
        txStoreSetAll([BUY, DEP], []);
        const mounted = mountEditor({action: 'edit', txIds: [BUY.id, DEP.id]});
        await waitFor(() => expect(rowsOf(BUY.id), 'premise: the BUY is on screen').toHaveLength(1));
        expect(rowsOf(DEP.id), 'premise: the DEPOSIT is on screen').toHaveLength(1);
        return mounted;
    }

    /** As `openBuyAndDeposit`, with the read answering at once; ends on the chip counting the two charges read. */
    async function openLoaded(): Promise<ReturnType<typeof mountEditor>> {
        answerChargesRead([FEE, TAX]);
        const mounted = await openBuyAndDeposit();
        await waitFor(() => expect(chip(), 'the BUY row carries the chip of its charges').not.toBeNull());
        await waitFor(() => expect(theChip()).toHaveAttribute('data-charges-count', '2'));
        return mounted;
    }

    /** Close the editor with ✕; ends on the close settled. */
    async function closeEditor(): Promise<void> {
        await fireEvent.click(screen.getByTestId('tx-bulk-close'));
        await settle();
    }

    async function validateNow(): Promise<Payload> {
        const {validateTransactions} = await api();
        const before = validateTransactions.mock.calls.length;
        await fireEvent.click(screen.getByTestId('tx-bulk-validate-now'));
        await settle();
        await waitFor(() => expect(validateTransactions.mock.calls.length, 'a validate run went out').toBeGreaterThan(before));
        return validateTransactions.mock.calls.at(-1)?.[0] as Payload;
    }

    /** A refusal of the TAX's update, at the index it holds in the body the backend received (never hardcoded). */
    function refuseTaxUpdate(payload: Payload): Array<Record<string, unknown>> {
        const index = (payload.updates ?? []).findIndex((update) => update.id === TAX.id);
        return index < 0 ? [] : [{operation: 'update', index, ref_id: TAX.id, error: 'refused by the test', code: 'f7c1TestRefusal', params: null}];
    }

    /** Edit the TAX's note through the BUY's Form: the TAX is no longer `original`; nothing creates or links a charge. */
    async function editTaxNoteInParentForm(): Promise<void> {
        await openBuyForm(2);
        const drafts = handedDrafts().map((draft): ChargeDraft => (draft.id === TAX.id ? {...draft, description: 'F7c1 tax note changed'} : draft));
        await push(buyPayload({_charges: drafts}));
    }

    // -----------------------------------------------------------------------
    // The entry load (§14.2)
    // -----------------------------------------------------------------------

    it('a saved parent entering with charges_count 2 and no charge held: the Bulk reads its charges at once, and the group starts closed', async () => {
        await openLoaded();

        expect(readAskedFor(BUY.id), 'the Bulk asked for the BUY’s charges (parent_ids) on entry, no Form open').toBe(true);
        expect(probe.form?.open ?? false, 'no Form was opened to get them').toBe(false);
        expect(theChip(), 'closed: the charges were read by the Bulk itself').toHaveAttribute('aria-expanded', 'false');
        expect(rowsOf(FEE.id), 'a closed group shows no FEE row').toHaveLength(0);
        expect(rowsOf(TAX.id), 'a closed group shows no TAX row').toHaveLength(0);
        expect(indentedRows(), 'no indented row').toHaveLength(0);
        expect(rowStatus(gridRow(BUY.id)), 'the parent is unchanged').toBe('original');
        expect(screen.getByTestId('tx-bulk-commit'), 'the charges read are no change: nothing to save').toBeDisabled();
    });

    it('the chip opens the group: the two charges, indented right after the parent, ↳, a checkbox of their own (TL-4) unticked, state linked; a second click closes it; no Form opens', async () => {
        await openLoaded();
        const parentRowId = buyRowId();
        expect(rowCheckbox(gridRow(BUY.id)), 'premise: a top-level row has its checkbox').not.toBeNull();

        await fireEvent.click(theChip());
        await settle();

        expect(theChip()).toHaveAttribute('aria-expanded', 'true');
        const ids = gridTxIds();
        const at = ids.indexOf(BUY.id);
        expect(new Set(ids.slice(at + 1, at + 3)), 'the two charges come right after their parent').toEqual(new Set([FEE.id, TAX.id]));
        for (const charge of [FEE, TAX]) {
            const row = gridRow(charge.id);
            expect(chargeOfCell(row), `${charge.type}: indented under the BUY`).toBe(parentRowId);
            expect(row.querySelector('[data-testid="tx-bulk-row-label"]')?.textContent ?? '', `${charge.type}: ↳ instead of a number`).toContain('↳');
            // 66 TL-4 (P-2 = C): was «no selection checkbox». Opening the group ticks nothing.
            expect(rowCheckbox(row), `${charge.type}: TL-4, its own selection checkbox`).not.toBeNull();
            expect(rowCheckbox(row), `${charge.type}: unticked`).toHaveAttribute('data-state', 'unchecked');
            expect(chargeState(row), `${charge.type}: linked`).toBe('linked');
            expect(rowStatus(row), `${charge.type}: an indented row keeps its own status cell`).toBe('original');
        }
        expect(probe.form?.open ?? false, 'the chip opens no Form').toBe(false);

        await fireEvent.click(theChip());
        await settle();

        expect(theChip()).toHaveAttribute('aria-expanded', 'false');
        expect(rowsOf(FEE.id)).toHaveLength(0);
        expect(rowsOf(TAX.id)).toHaveLength(0);
    });

    it('«Save all» is off while the read is in flight, and comes on when it lands', async () => {
        holdChargesReads();
        await openBuyAndDeposit();
        await rowAction(gridRow(DEP.id), 'mark-delete');
        expect(rowStatus(gridRow(DEP.id)), 'premise: there is something to save').toBe('delete');
        await waitFor(() => expect(readAskedFor(BUY.id), 'premise: the read went out').toBe(true));

        expect(screen.getByTestId('tx-bulk-commit'), 'a read in flight: Save all is off').toBeDisabled();

        await releaseRead(0);

        await waitFor(() => expect(theChip()).toHaveAttribute('data-charges-count', '2'));
        expect(screen.getByTestId('tx-bulk-commit'), 'the read landed: Save all is on').toBeEnabled();
    });

    it('closing an editor the user did not change asks nothing, the charges read included', async () => {
        const {onClose} = await openLoaded();

        await closeEditor();

        expect(screen.queryByTestId('confirm-modal-confirm'), 'no «Discard changes?»').toBeNull();
        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it.each([
        ['edit, the read lands while the editor is dirty, undo', 'land-dirty'],
        ['edit, undo, then the read lands', 'land-clean'],
    ] as const)('the close guard’s baseline holds the charges read: %s → closing asks nothing', async (_label, order) => {
        holdChargesReads();
        const {onClose} = await openBuyAndDeposit();
        await waitFor(() => expect(readAskedFor(BUY.id), 'premise: the read went out').toBe(true));

        await rowAction(gridRow(DEP.id), 'mark-delete');
        expect(rowStatus(gridRow(DEP.id)), 'premise: the DEPOSIT is marked').toBe('delete');
        if (order === 'land-dirty') {
            await releaseRead(0);
            await waitFor(() => expect(theChip()).toHaveAttribute('data-charges-count', '2'));
        }
        await rowAction(gridRow(DEP.id), 'mark-delete');
        expect(rowStatus(gridRow(DEP.id)), 'premise: the DEPOSIT is restored').toBe('original');
        if (order === 'land-clean') {
            await releaseRead(0);
            await waitFor(() => expect(theChip()).toHaveAttribute('data-charges-count', '2'));
        }

        await closeEditor();

        expect(screen.queryByTestId('confirm-modal-confirm'), 'no «Discard changes?»: the charges read are part of the baseline').toBeNull();
        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('an answer that arrives after the editor was reopened on other rows is dropped', async () => {
        holdChargesReads();
        const {rerender, onClose} = await openBuyAndDeposit();
        await waitFor(() => expect(readAskedFor(BUY.id), 'premise: the read went out').toBe(true));

        await rerender({open: false, intent: {action: 'edit', txIds: [BUY.id, DEP.id]}, onClose});
        await settle();
        await rerender({open: true, intent: {action: 'edit', txIds: [DEP.id]}, onClose});
        await settle();
        await waitFor(() => expect(rowsOf(DEP.id), 'premise: the reopened editor holds the DEPOSIT').toHaveLength(1));
        expect(rowsOf(BUY.id), 'premise: the editor was rebuilt on the new intent (no BUY)').toHaveLength(0);
        await releaseRead(0);

        expect(rowsOf(BUY.id), 'the BUY is not in this editor').toHaveLength(0);
        expect(rowsOf(FEE.id), 'nor its FEE').toHaveLength(0);
        expect(rowsOf(TAX.id), 'nor its TAX').toHaveLength(0);
        expect(screen.getByTestId('tx-bulk-commit'), 'nothing to save').toBeDisabled();
        await closeEditor();
        expect(screen.queryByTestId('confirm-modal-confirm'), 'closing asks nothing').toBeNull();
    });

    it('an answer that arrives after «Reset all» is dropped; the read the reset made is the one adopted', async () => {
        holdChargesReads();
        await openBuyAndDeposit();
        await waitFor(() => expect(readAskedFor(BUY.id), 'premise: the first read went out').toBe(true));
        await rowAction(gridRow(DEP.id), 'mark-delete');
        expect(await clickCollectingErrors(screen.getByTestId('tx-bulk-reset-all')), 'Reset all throws nothing').toEqual([]);
        await waitFor(() => expect(heldReads.length, 'the reset brings the BUY in again: a second read').toBe(2));

        await releaseRead(0);

        expect(chip(), 'the first answer is stale: nothing adopted from it, so no chip (a parent with no charge held has none)').toBeNull();

        await releaseRead(1);

        await waitFor(() => expect(theChip()).toHaveAttribute('data-charges-count', '2'));
    });

    it('a failed read raises an error toast, and «del» on that parent is off, with a reason; the row stays unmarked', async () => {
        readMock().mockImplementation((async () => {
            throw new Error('network down');
        }) as never);
        await openBuyAndDeposit();
        await waitFor(() => expect(readAskedFor(BUY.id), 'premise: the read went out').toBe(true));
        await settle();

        const toasts = await toastsMock();
        await waitFor(() =>
            expect(
                toasts.show.mock.calls.some((call) => call[0] === 'error'),
                'an error toast',
            ).toBe(true),
        );
        // Its message is the catalogue's, naming the parent whose read failed as #<id> (it says «Reset row» reads again).
        const expected = get(_)('transactions.bulk.chargesReadFailed', {values: {ids: `#${BUY.id}`}});
        expect(expected, 'premise: the catalogue holds the key').not.toBe('transactions.bulk.chargesReadFailed');
        expect(
            toasts.show.mock.calls.filter((call) => call[0] === 'error').map((call) => call[1]),
            'the error toast names the parent whose charges could not be read',
        ).toContain(expected);

        await openMenu(gridRow(BUY.id));
        const del = screen.getByTestId('context-menu-action-mark-delete');
        // 77 SEL-M: off and reachable, its reason in the shared Tooltip and its code in `data-disabled-reason`
        expect(del, '«del» on a parent whose charges could not be read is off').toHaveAttribute('aria-disabled', 'true');
        expect(del, 'and says why').toHaveAttribute('data-disabled-reason', 'charges-failed');
        await fireEvent.click(del);
        await settle();
        expect(rowStatus(gridRow(BUY.id)), 'the click marked nothing').toBe('original');
    });

    it('«Remove from batch» on the parent takes along the charges it read and nobody changed; one changed stays, a top-level row', async () => {
        await openLoaded();
        await editTaxNoteInParentForm();
        expect(theChip(), 'premise: the TAX is changed').toHaveAttribute('data-charges-modified', 'true');

        await rowAction(gridRow(BUY.id), 'remove-from-batch');

        expect(rowsOf(BUY.id), 'the BUY left the batch').toHaveLength(0);
        expect(rowsOf(FEE.id), 'its unchanged FEE left with it').toHaveLength(0);
        expect(rowsOf(TAX.id), 'the changed TAX stays').toHaveLength(1);
        expect(chargeOfCell(gridRow(TAX.id)), 'as a top-level row').toBeNull();
        const body = await validateNow();
        expect(body.updates ?? []).toEqual([{id: TAX.id, description: 'F7c1 tax note changed'}]);
        expect(body.deletes ?? []).toEqual([]);
        expect(body.creates ?? []).toEqual([]);
    });

    // -----------------------------------------------------------------------
    // When the group opens by itself (§14.7)
    // -----------------------------------------------------------------------

    it('charges that came in the intent with their parent: the group is open, and nothing is read', async () => {
        txStoreSetAll([BUY, FEE, TAX, DEP], []);
        answerChargesRead([FEE, TAX]);
        mountEditor({action: 'edit', txIds: [BUY.id, FEE.id, TAX.id]});
        await waitFor(() => expect(rowsOf(BUY.id), 'premise: the BUY is on screen').toHaveLength(1));
        await waitFor(() => expect(chip(), 'the BUY row carries the chip of its charges').not.toBeNull());

        expect(theChip()).toHaveAttribute('data-charges-count', '2');
        expect(theChip(), 'brought by the user with the parent: open').toHaveAttribute('aria-expanded', 'true');
        expect(chargeOfCell(gridRow(FEE.id))).toBe(buyRowId());
        expect(chargeOfCell(gridRow(TAX.id))).toBe(buyRowId());
        expect(readAskedFor(BUY.id), 'all its charges are held: no read').toBe(false);
    });

    // Re-targeted in F7-c2 (§17.5, §17.9): the F7-b interim is gone — the parent goes «del» through the panel, «Keep».
    it('the parent marked «del» through the panel, «Keep»: the group opens, its charges sit under it «unlink»; «del» was on for a parent read', async () => {
        await openLoaded();

        await rowAction(gridRow(BUY.id), 'mark-delete');
        await fireEvent.click(await screen.findByTestId('tx-charges-modal-keep'));
        await settle();

        expect(rowStatus(gridRow(BUY.id)), 'the parent is marked').toBe('delete');
        expect(theChip(), 'a parent «del» opens its group').toHaveAttribute('aria-expanded', 'true');
        for (const charge of [FEE, TAX]) {
            expect(chargeOfCell(gridRow(charge.id)), `${charge.type}: under its parent`).toBe(buyRowId());
            expect(chargeState(gridRow(charge.id)), `${charge.type}: unlinked from the parent «del»`).toBe('unlink');
        }

        // «Restore» on the parent: everything as it was, and a group never closes by itself.
        await rowAction(gridRow(BUY.id), 'mark-delete');

        expect(rowStatus(gridRow(BUY.id)), 'the parent is restored').toBe('original');
        expect(theChip(), 'the group stays open after «Restore»').toHaveAttribute('aria-expanded', 'true');
        for (const charge of [FEE, TAX]) expect(chargeState(gridRow(charge.id)), `${charge.type}: linked again`).toBe('linked');
    });

    it('a charge created in the parent’s Form opens the group, the new charge indented under the parent', async () => {
        await openLoaded();
        await openBuyForm(2);

        await push(buyPayload({_charges: [...handedDrafts(), newDraft('FEE', '2', 'F7c1 new fee')]}));

        expect(theChip(), 'created in the parent’s Form: open').toHaveAttribute('aria-expanded', 'true');
        expect(theChip()).toHaveAttribute('data-charges-count', '3');
        expect(chargeOfCell(gridRowDescribed('F7c1 new fee')), 'the new FEE is under the BUY').toBe(buyRowId());
    });

    // -----------------------------------------------------------------------
    // The indented row, the chip's mark, a charge unlinked (§13.4–§13.6, §14.6)
    // -----------------------------------------------------------------------

    // Re-targeted (consultant's decision, 19/11): the menu of an indented row is «Edit row» + «Delete»/«Restore» — «Edit row»
    // is the double-click's twin on touch and from the keyboard. Nothing else: no clone, split, remove or reset.
    it('the menu of an indented row offers exactly «Edit row», «Clone row» (66 TL-3) and «Delete» / «Restore»; Delete → del, Restore → linked', async () => {
        await openLoaded();
        await fireEvent.click(theChip());
        await settle();

        await openMenu(gridRow(FEE.id));
        expect(screen.getByTestId('context-menu-action-mark-delete'), 'barrier: the menu offers «Delete»').toBeInTheDocument();
        expect(screen.getByTestId('context-menu-action-edit-single'), 'and «Edit row»').toBeInTheDocument();
        expect(
            [...screen.getByTestId('context-menu').querySelectorAll('[data-testid^="context-menu-action-"]')].map((item) => item.getAttribute('data-testid')),
            'exactly those three',
        ).toEqual(expect.arrayContaining(['context-menu-action-edit-single', 'context-menu-action-clone', 'context-menu-action-mark-delete']));
        // 66 TL-3 (FEE consultant): «Clone row» is back on a charge under its parent; its copy sits under the same parent.
        expect(screen.getByTestId('context-menu').querySelectorAll('[data-testid^="context-menu-action-"]'), 'exactly those three').toHaveLength(3);
        for (const hidden of ['split', 'remove-from-batch', 'reset']) {
            expect(screen.queryByTestId(`context-menu-action-${hidden}`), `no «${hidden}» on a charge`).toBeNull();
        }
        await clickCollectingErrors(screen.getByTestId('context-menu-action-mark-delete'));
        expect(chargeState(gridRow(FEE.id)), 'Delete marks the charge').toBe('del');
        expect(rowStatus(gridRow(FEE.id)), 'its own status cell says «delete» too (the Bulk’s «del» counts include it)').toBe('delete');
        expect(theChip(), 'a charge marked: the chip says its group changed').toHaveAttribute('data-charges-modified', 'true');
        expect(rowStatus(gridRow(BUY.id)), 'the parent’s own status does not change').toBe('original');

        // A charge marked «del» is a changed row: its menu still offers «Restore» (no «reset», no «remove»); «Clone row»
        // too (66 TL-3: its copy is born free when the «Link» rule refuses the parent).
        await openMenu(gridRow(FEE.id));
        expect(screen.getByTestId('context-menu-action-mark-delete'), 'barrier: the menu offers «Restore»').toBeInTheDocument();
        expect(screen.getByTestId('context-menu-action-edit-single'), 'and «Edit row»').toBeInTheDocument();
        for (const hidden of ['remove-from-batch', 'reset']) {
            expect(screen.queryByTestId(`context-menu-action-${hidden}`), `no «${hidden}» on a charge marked «del»`).toBeNull();
        }
        await clickCollectingErrors(screen.getByTestId('context-menu-action-mark-delete'));
        expect(chargeState(gridRow(FEE.id)), 'Restore under a parent that stays: linked again').toBe('linked');
    });

    it('«Edit row» from the menu of an indented row opens that charge’s Form', async () => {
        await openLoaded();
        await fireEvent.click(theChip());
        await settle();

        await rowAction(gridRow(TAX.id), 'edit-single');

        await waitFor(() => expect(formProbe().open, 'the Form is open').toBe(true));
        expect(formRow()?.id, 'on the TAX, not on its parent').toBe(TAX.id);
    });

    it('a double-click on an indented row opens that charge’s Form', async () => {
        await openLoaded();
        await fireEvent.click(theChip());
        await settle();

        await fireEvent.dblClick(gridRow(TAX.id));
        await settle();

        await waitFor(() => expect(formProbe().open, 'the Form is open').toBe(true));
        expect(formRow()?.id, 'on the TAX, not on its parent').toBe(TAX.id);
    });

    it('a charge changed in the parent’s Form marks the chip; the parent’s status stays, the group stays closed, Save all comes on', async () => {
        await openLoaded();
        expect(theChip(), 'premise: nothing changed yet').not.toHaveAttribute('data-charges-modified', 'true');

        await editTaxNoteInParentForm();

        expect(theChip()).toHaveAttribute('data-charges-modified', 'true');
        expect(theChip(), 'a note changed neither creates nor links: the group stays closed').toHaveAttribute('aria-expanded', 'false');
        expect(rowStatus(gridRow(BUY.id)), 'the parent itself is unchanged').toBe('original');
        expect(screen.getByTestId('tx-bulk-commit'), 'the TAX’s change is something to save').toBeEnabled();
    });

    it('a charge unlinked from a parent that stays is a top-level row: no parent, the badge «unlink», a checkbox', async () => {
        await openLoaded();
        await openBuyForm(2);

        await push(buyPayload({_charges: handedDrafts().map((draft): ChargeDraft => (draft.id === FEE.id ? {...draft, state: 'unlink'} : draft))}));

        expect(rowsOf(FEE.id), 'the FEE is on screen whatever its old group does').toHaveLength(1);
        expect(chargeOfCell(gridRow(FEE.id)), 'top-level').toBeNull();
        expect(chargeState(gridRow(FEE.id)), 'with the badge «unlink»').toBe('unlink');
        expect(rowCheckbox(gridRow(FEE.id)), 'a top-level row can be selected').not.toBeNull();
        expect(theChip(), 'the BUY now counts the TAX alone').toHaveAttribute('data-charges-count', '1');
    });

    // 66 TL-4 (P-2 = C): reversed. Was «leaves the selection»: the effect that dropped every indented row from the
    // selection stays only for the hidden half of a pair; a charge under its parent has its checkbox and keeps its tick.
    it('a selected top-level row that goes back under its parent stays selected, its checkbox ticked (TL-4)', async () => {
        await openLoaded();
        await openBuyForm(2);
        await push(buyPayload({_charges: handedDrafts().map((draft): ChargeDraft => (draft.id === FEE.id ? {...draft, state: 'unlink'} : draft))}));
        const checkbox = rowCheckbox(gridRow(FEE.id));
        if (!checkbox) throw new Error('premise: the unlinked FEE has a checkbox');
        await fireEvent.click(checkbox);
        await settle();
        expect(screen.getByTestId('tx-bulk-delete-selected'), 'premise: the FEE is selected').toBeInTheDocument();

        await openBuyForm(2);
        await push(buyPayload({_charges: handedDrafts().map((draft): ChargeDraft => (draft.id === FEE.id ? {...draft, state: 'linked'} : draft))}));

        expect(theChip(), 'a charge linked in the parent’s Form opens the group').toHaveAttribute('aria-expanded', 'true');
        expect(chargeOfCell(gridRow(FEE.id)), 'the FEE is indented under the BUY again').toBe(buyRowId());
        expect(rowCheckbox(gridRow(FEE.id)), 'TL-4: with its own checkbox, still ticked').toHaveAttribute('data-state', 'checked');
        expect(screen.queryByTestId('tx-bulk-delete-selected'), 'TL-4: the FEE, under its parent again, is still selected').not.toBeNull();
    });

    // -----------------------------------------------------------------------
    // One order, ours (§14.5)
    // -----------------------------------------------------------------------

    it('the date header orders the top-level rows both ways; an open group stays right after its parent in both', async () => {
        txStoreSetAll([BUY, FEE, TAX, DEP], []);
        mountEditor({action: 'edit', txIds: [BUY.id, FEE.id, TAX.id, DEP.id]});
        await waitFor(() => expect(rowsOf(DEP.id), 'premise: the DEPOSIT is on screen').toHaveLength(1));
        await waitFor(() => expect(chip(), 'premise: the BUY carries its chip').not.toBeNull());
        expect(theChip(), 'premise: the group came open with the intent').toHaveAttribute('aria-expanded', 'true');
        const group = (ids: number[]) => ids.slice(ids.indexOf(BUY.id), ids.indexOf(BUY.id) + 3);

        await fireEvent.click(screen.getByTestId('dt-sort-date'));
        await settle();
        const asc = gridTxIds();
        expect(asc.indexOf(BUY.id), 'ascending: the BUY (13/09) before the DEPOSIT (14/09)').toBeLessThan(asc.indexOf(DEP.id));
        expect(new Set(group(asc).slice(1)), 'ascending: the charges right after the BUY').toEqual(new Set([FEE.id, TAX.id]));

        await fireEvent.click(screen.getByTestId('dt-sort-date'));
        await settle();
        const desc = gridTxIds();
        expect(desc.indexOf(DEP.id), 'descending: the DEPOSIT first').toBeLessThan(desc.indexOf(BUY.id));
        expect(new Set(group(desc).slice(1)), 'descending: the charges still right after the BUY, not before it').toEqual(new Set([FEE.id, TAX.id]));
        expect(group(desc), 'the group is the same in both directions: the parent, then its charges in the order of the operations').toEqual(group(asc));
    });

    // -----------------------------------------------------------------------
    // Issues on a charge of a closed group (§13.8, §14.3)
    // -----------------------------------------------------------------------

    it('a refusal of a charge in a closed group is in the banner with the derived label; a click opens the group and goes to the charge', async () => {
        await openLoaded();
        await editTaxNoteInParentForm();
        expect(theChip(), 'premise: the group is closed').toHaveAttribute('aria-expanded', 'false');
        const parentLabel = (gridRow(BUY.id).querySelector('[data-testid="tx-bulk-row-label"]')?.textContent ?? '').trim();
        const {validateTransactions} = await api();
        validateTransactions.mockImplementation((async (payload: Payload) => ({committed: false, issues: refuseTaxUpdate(payload), rawResponse: {wac_results: []}})) as never);

        await validateNow();

        const issue = await screen.findByTestId('tx-bulk-issue');
        // The TAX is the second of the BUY's charges in the order the read answered (FEE, TAX).
        expect(issue, 'the issue names the charge by the label derived from its parent').toHaveAttribute('data-row-label', `${parentLabel}·2`);

        await fireEvent.click(issue);
        await settle();

        expect(theChip(), 'the jump opens the group').toHaveAttribute('aria-expanded', 'true');
        await waitFor(() => expect(gridRow(TAX.id), 'and lands on the TAX row').toHaveAttribute('data-highlighted', 'true'));
    });

    it('a commit refused on a charge of a closed group: the editor stays open, the banner names the charge by its derived label', async () => {
        const {onClose} = await openLoaded();
        await editTaxNoteInParentForm();
        const parentLabel = (gridRow(BUY.id).querySelector('[data-testid="tx-bulk-row-label"]')?.textContent ?? '').trim();
        const {commitTransactions} = await api();
        commitTransactions.mockImplementation((async (payload: Payload) => ({committed: false, issues: refuseTaxUpdate(payload), results: []})) as never);

        await fireEvent.click(screen.getByTestId('tx-bulk-commit'));
        await settle();

        await waitFor(() => expect(commitTransactions, 'Save all reached the backend').toHaveBeenCalledTimes(1));
        expect(refuseTaxUpdate(commitTransactions.mock.calls[0]?.[0] as Payload), 'premise: the body held the TAX update').toHaveLength(1);
        expect(onClose, 'refused: the editor stays open').not.toHaveBeenCalled();
        const issue = await screen.findByTestId('tx-bulk-issue');
        expect(issue).toHaveAttribute('data-row-label', `${parentLabel}·2`);
    });

    // -----------------------------------------------------------------------
    // More entries and the indented menu (coordinator's gaps, 19/11)
    // -----------------------------------------------------------------------

    /** The «Search & add» picker the editor mounts (the one without `includeIds`). */
    function addRowsPicker(): Record<string, unknown> {
        const found = probe.pickers.find((props) => props.includeIds === undefined);
        if (!found) throw new Error(`TransactionBulkModal did not mount its «Search & add» picker (${probe.pickers.length} pickers)`);
        return found;
    }

    it('a saved parent added through the «Search & add» picker: its charges are read, and its group starts closed', async () => {
        txStoreSetAll([BUY, DEP], []);
        answerChargesRead([FEE, TAX]);
        mountEditor({action: 'edit', txIds: [DEP.id]});
        await waitFor(() => expect(formProbe().open, 'one row opens its Form').toBe(true));
        (formProbe().onClose as () => void)();
        flushSync();
        await settle();
        expect(rowsOf(BUY.id), 'premise: the BUY is not in the editor yet').toHaveLength(0);
        expect(readAskedFor(BUY.id), 'premise: nothing asked about the BUY yet').toBe(false);

        (addRowsPicker().onAdd as (rows: TXReadItem[]) => void)([BUY]);
        flushSync();
        await settle();

        await waitFor(() => expect(rowsOf(BUY.id), 'the BUY joined the batch').toHaveLength(1));
        expect(readAskedFor(BUY.id), 'the Bulk asked for the charges of the parent it was handed').toBe(true);
        await waitFor(() => expect(theChip()).toHaveAttribute('data-charges-count', '2'));
        expect(theChip(), 'read by the Bulk itself: closed').toHaveAttribute('aria-expanded', 'false');
        expect(rowsOf(FEE.id)).toHaveLength(0);
        expect(screen.getByTestId('tx-bulk-commit'), 'the charges read are no change').toBeDisabled();
    });

    it('the row Reset of a parent whose charges are not held reads them again: adopted, closed, and «del» on it back on', async () => {
        // Every read fails at first: the entry load, and the Form's own read when the parent's Form opens.
        readMock().mockImplementation((async () => {
            throw new Error('network down');
        }) as never);
        await openBuyAndDeposit();
        await waitFor(() => expect(readAskedFor(BUY.id), 'premise: the entry read went out').toBe(true));
        await rowAction(gridRow(BUY.id), 'edit-single');
        await waitFor(() => expect(formProbe().open, 'the parent’s Form opens, its charges unread').toBe(true));
        expect(formRow()?.id).toBe(BUY.id);
        await push(buyPayload({description: 'F7c1 parent edited'}));
        expect(rowStatus(gridRow(BUY.id)), 'premise: the parent is edited, so it can be reset').toBe('edited');
        expect(chip(), 'premise: no charge is held').toBeNull();

        answerChargesRead([FEE, TAX]);
        const before = readMock().mock.calls.length;
        await rowAction(gridRow(BUY.id), 'reset');

        expect(rowStatus(gridRow(BUY.id)), 'the parent is back as saved').toBe('original');
        await waitFor(() => expect(readMock().mock.calls.length, 'the reset brings the parent in again: a new read').toBeGreaterThan(before));
        expect(readAskedFor(BUY.id)).toBe(true);
        await waitFor(() => expect(theChip()).toHaveAttribute('data-charges-count', '2'));
        expect(theChip(), 'read by the Bulk itself: closed').toHaveAttribute('aria-expanded', 'false');
        await openMenu(gridRow(BUY.id));
        expect(screen.getByTestId('context-menu-action-mark-delete'), 'the charges are read: «del» is on again').not.toHaveAttribute('aria-disabled');
    });

    it('«Delete» on a new charge created in the parent’s Form: the row leaves the Bulk, the chip counts one less, no create is sent', async () => {
        await openLoaded();
        await openBuyForm(2);
        await push(buyPayload({_charges: [...handedDrafts(), newDraft('FEE', '2', 'F7c1 new fee')]}));
        expect(theChip(), 'premise: three charges under the BUY').toHaveAttribute('data-charges-count', '3');
        expect(chargeOfCell(gridRowDescribed('F7c1 new fee')), 'premise: the new FEE is indented').toBe(buyRowId());

        await rowAction(gridRowDescribed('F7c1 new fee'), 'mark-delete');

        expect(
            gridRows().filter((row) => rowDescription(row) === 'F7c1 new fee'),
            'a new row trashed leaves the Bulk',
        ).toHaveLength(0);
        expect(theChip(), 'the chip counts the two saved charges again').toHaveAttribute('data-charges-count', '2');
        const body = await validateNow();
        expect(body.creates ?? [], 'nothing created').toEqual([]);
    });

    it('«Restore» from the menu of a saved charge under a parent «del»: «unlink», not linked; the batch still unlinks it', async () => {
        await openLoaded();
        // Re-targeted in F7-c2 (§17.9): the parent goes «del» through the panel, «Keep».
        await rowAction(gridRow(BUY.id), 'mark-delete');
        await fireEvent.click(await screen.findByTestId('tx-charges-modal-keep'));
        await settle();
        expect(chargeState(gridRow(FEE.id)), 'premise: the FEE sits under the parent «del», unlinked').toBe('unlink');
        await rowAction(gridRow(FEE.id), 'mark-delete');
        expect(chargeState(gridRow(FEE.id)), 'premise: the FEE is marked «del»').toBe('del');

        await rowAction(gridRow(FEE.id), 'mark-delete');

        expect(chargeState(gridRow(FEE.id)), 'restored under a parent «del»: unlinked, never linked to a parent going away').toBe('unlink');
        const body = await validateNow();
        expect(body.deletes ?? [], 'the parent alone is deleted').toEqual([BUY.id]);
        expect(body.updates ?? [], 'the FEE is unlinked').toContainEqual({id: FEE.id, parent_transaction_id: 0});
        expect(body.updates ?? [], 'the TAX is unlinked').toContainEqual({id: TAX.id, parent_transaction_id: 0});
    });

    // -----------------------------------------------------------------------
    // The title counts the rows drawn at top level; a charge the user brought opens its parent's group (coordinator, 19/11)
    // -----------------------------------------------------------------------

    /** The title as the catalogue renders it for `total` rows: the interpolated number is the subject, never the words. */
    const titleFor = (total: number): string => get(_)('transactions.bulk.title', {values: {total}});

    it('the title counts the top-level rows: a BUY with its two charges read is 1, closed or open', async () => {
        txStoreSetAll([BUY], []);
        answerChargesRead([FEE, TAX]);
        mountEditor({action: 'edit', txIds: [BUY.id]});
        await waitFor(() => expect(formProbe().open, 'one row opens its Form').toBe(true));
        (formProbe().onClose as () => void)();
        flushSync();
        await settle();
        await waitFor(() => expect(theChip(), 'premise: the two charges are read and held').toHaveAttribute('data-charges-count', '2'));
        expect(theChip(), 'premise: closed').toHaveAttribute('aria-expanded', 'false');
        expect(titleFor(1), 'premise: the catalogue renders 1 and 3 differently').not.toBe(titleFor(3));

        const title = screen.getByTestId('tx-bulk-title');
        expect(title, 'closed group: one row at top level').toHaveTextContent(titleFor(1));
        expect(title).not.toHaveTextContent(titleFor(3));

        await fireEvent.click(theChip());
        await settle();
        expect(theChip(), 'premise: open').toHaveAttribute('aria-expanded', 'true');
        expect(rowsOf(FEE.id), 'premise: the charges are drawn').toHaveLength(1);

        expect(title, 'open group: the charges drawn indented do not count').toHaveTextContent(titleFor(1));
        expect(title).not.toHaveTextContent(titleFor(3));
    });

    it('a charge already in the Bulk on its own, then its parent added through the picker: adopted, and its group opens (the user brought it)', async () => {
        txStoreSetAll([BUY, FEE], []);
        answerChargesRead([FEE, TAX]);
        mountEditor({action: 'edit', txIds: [FEE.id]});
        await waitFor(() => expect(formProbe().open, 'one row opens its Form').toBe(true));
        (formProbe().onClose as () => void)();
        flushSync();
        await settle();
        expect(rowsOf(FEE.id), 'premise: the FEE is a row').toHaveLength(1);
        expect(chargeOfCell(gridRow(FEE.id)), 'premise: its parent is not in the Bulk, so it is top-level').toBeNull();
        expect(rowsOf(BUY.id), 'premise: the BUY is not in the Bulk').toHaveLength(0);

        (addRowsPicker().onAdd as (rows: TXReadItem[]) => void)([BUY]);
        flushSync();
        await settle();

        await waitFor(() => expect(rowsOf(BUY.id), 'the BUY joined the batch').toHaveLength(1));
        await waitFor(() => expect(theChip(), 'the FEE held plus the TAX read').toHaveAttribute('data-charges-count', '2'));
        expect(theChip(), 'a charge the user brought opens its parent’s group').toHaveAttribute('aria-expanded', 'true');
        expect(chargeOfCell(gridRow(FEE.id)), 'the FEE is adopted: indented under the BUY').toBe(buyRowId());
        // 66 TL-4 (P-2 = C): was «and no longer selectable».
        expect(rowCheckbox(gridRow(FEE.id)), 'TL-4: still selectable, under its parent').not.toBeNull();
        expect(chargeOfCell(gridRow(TAX.id)), 'the TAX read sits in the same open group').toBe(buyRowId());
    });

    // -----------------------------------------------------------------------
    // A failed read stays per parent; a parent «del» pulls its unlinked charges back under it (coordinator, 19/11)
    // -----------------------------------------------------------------------

    it('two parents whose reads failed: the row Reset of A reads A again and turns «del» on for A only; B stays off, with its reason', async () => {
        const BUY_B: TXReadItem = {...BUY, id: 91_721, date: '2026-09-15', description: 'F7c1 parent B'};
        const FEE_B: TXReadItem = {...FEE, id: 91_722, date: BUY_B.date, parent_transaction_id: BUY_B.id, description: 'F7c1 fee B'};
        const TAX_B: TXReadItem = {...TAX, id: 91_723, date: BUY_B.date, parent_transaction_id: BUY_B.id, description: 'F7c1 tax B'};
        // Every read fails at first, batched or not: the entry load of A and B, and the Form's own read of A.
        readMock().mockImplementation((async () => {
            throw new Error('network down');
        }) as never);
        txStoreSetAll([BUY, BUY_B], []);
        mountEditor({action: 'edit', txIds: [BUY.id, BUY_B.id]});
        await waitFor(() => expect(rowsOf(BUY_B.id), 'premise: both parents are on screen').toHaveLength(1));
        await waitFor(() => expect(readAskedFor(BUY.id) && readAskedFor(BUY_B.id), 'premise: the charges of both were asked for').toBe(true));
        await settle();

        /** Whether «del» is on in a row's menu, and its reason; the menu is closed again before returning. */
        async function deleteAction(row: HTMLElement): Promise<{enabled: boolean; reason: string}> {
            await openMenu(row);
            const action = screen.getByTestId('context-menu-action-mark-delete');
            // 77 SEL-M: off with its reason is `aria-disabled`, reachable, its reason code in `data-disabled-reason`
            const verdict = {enabled: action.getAttribute('aria-disabled') !== 'true', reason: action.getAttribute('data-disabled-reason') ?? ''};
            await fireEvent.keyDown(window, {key: 'Escape'});
            await settle();
            await waitFor(() => expect(screen.queryByTestId('context-menu'), 'the menu closed').toBeNull());
            return verdict;
        }
        expect(await deleteAction(gridRow(BUY.id)), 'premise: «del» on A is off').toMatchObject({enabled: false});
        expect(await deleteAction(gridRow(BUY_B.id)), 'premise: «del» on B is off').toMatchObject({enabled: false});

        // A edited through its Form (charges unread), so that it can be reset.
        await rowAction(gridRow(BUY.id), 'edit-single');
        await waitFor(() => expect(formProbe().open, 'A’s Form opens, its charges unread').toBe(true));
        expect(formRow()?.id).toBe(BUY.id);
        await push(buyPayload({description: 'F7c1 parent edited'}));
        expect(rowStatus(gridRow(BUY.id)), 'premise: A is edited').toBe('edited');

        // From now on A's charges can be read; B's still cannot.
        readMock().mockImplementation((async (args: ReadArgs) => {
            const parents = args?.queries?.parent_ids ?? [];
            if (parents.includes(BUY_B.id)) throw new Error('network down');
            return chargesOf(parents, [FEE, TAX, FEE_B, TAX_B]);
        }) as never);
        await rowAction(gridRow(BUY.id), 'reset');

        await waitFor(() => expect(theChip(), 'A’s charges are read and held').toHaveAttribute('data-charges-count', '2'));
        expect(await deleteAction(gridRow(BUY.id)), 'A’s charges are read: «del» on A is on').toMatchObject({enabled: true});
        const onB = await deleteAction(gridRow(BUY_B.id));
        expect(onB.enabled, 'B’s read still failed: the reset of A does not turn «del» on for B').toBe(false);
        expect(onB.reason, 'and B still says why').not.toBe('');
    });

    it('both charges unlinked in the parent’s Form, then the parent marked «del»: they go back under it, «unlink», and its group opens', async () => {
        await openLoaded();
        await openBuyForm(2);
        await push(buyPayload({_charges: handedDrafts().map((draft): ChargeDraft => ({...draft, state: 'unlink'}))}));
        for (const charge of [FEE, TAX]) {
            expect(chargeOfCell(gridRow(charge.id)), `premise: the ${charge.type} is a top-level row`).toBeNull();
            expect(chargeState(gridRow(charge.id)), `premise: the ${charge.type} says «unlink»`).toBe('unlink');
        }
        expect(chip(), 'premise: nothing under the BUY, so no chip').toBeNull();

        await rowAction(gridRow(BUY.id), 'mark-delete');

        expect(rowStatus(gridRow(BUY.id)), 'the BUY is marked').toBe('delete');
        await waitFor(() => expect(chip(), 'its two unlinked charges are under it again').not.toBeNull());
        expect(theChip()).toHaveAttribute('data-charges-count', '2');
        expect(theChip(), 'a parent «del» opens its group').toHaveAttribute('aria-expanded', 'true');
        for (const charge of [FEE, TAX]) {
            expect(chargeOfCell(gridRow(charge.id)), `the ${charge.type} is indented under the BUY`).toBe(buyRowId());
            expect(chargeState(gridRow(charge.id)), `the ${charge.type} still says «unlink»`).toBe('unlink');
        }
    });

    // -----------------------------------------------------------------------
    // The Status cell of a charge row: one chip (consultant's correction to C14, 19/11)
    // -----------------------------------------------------------------------

    it('the Status cell of a charge row holds one chip, inside the charge wrapper: «del» → delete, «unlink» → edited, linked → its status and 🔗', async () => {
        await openLoaded();
        await openBuyForm(2);
        // The TAX unlinked (a top-level row «unlink»), a new FEE created (linked, it opens the group).
        await push(buyPayload({_charges: [...handedDrafts().map((draft): ChargeDraft => (draft.id === TAX.id ? {...draft, state: 'unlink'} : draft)), newDraft('FEE', '2', 'F7c1 new fee')]}));
        expect(theChip(), 'premise: the group is open').toHaveAttribute('aria-expanded', 'true');
        await rowAction(gridRow(FEE.id), 'mark-delete');

        const scene: Array<[string, HTMLElement, string, string]> = [
            ['the saved FEE «del», indented', gridRow(FEE.id), 'del', 'delete'],
            ['the TAX «unlink», top-level', gridRow(TAX.id), 'unlink', 'edited'],
            ['the new FEE, linked', gridRowDescribed('F7c1 new fee'), 'linked', 'new'],
        ];
        expect(chargeOfCell(scene[0][1]), 'premise: the FEE is indented').toBe(buyRowId());
        expect(chargeOfCell(scene[1][1]), 'premise: the TAX is top-level').toBeNull();
        expect(chargeOfCell(scene[2][1]), 'premise: the new FEE is indented').toBe(buyRowId());

        for (const [label, row, state, status] of scene) {
            const cell = row.querySelector<HTMLElement>('td[data-column-id="status"]');
            if (!cell) throw new Error(`${label}: no Status cell`);
            const chips = cell.querySelectorAll('[data-testid="tx-bulk-row-status"]');
            expect(chips, `${label}: exactly one status chip`).toHaveLength(1);
            const wrapper = cell.querySelector('[data-testid="tx-bulk-charge-state"]');
            expect(wrapper, `${label}: the charge wrapper is in the Status cell`).not.toBeNull();
            expect(wrapper!.contains(chips[0]), `${label}: the chip is inside the charge wrapper`).toBe(true);
            expect(wrapper, `${label}: the wrapper's state`).toHaveAttribute('data-state', state);
            expect(chips[0], `${label}: the chip says the row's own status`).toHaveAttribute('data-status', status);
            expect(cell.querySelector('.flex-col'), `${label}: nothing stacked in the cell`).toBeNull();
            if (state === 'linked') expect(wrapper!.textContent ?? '', `${label}: 🔗 beside the chip`).toContain('🔗');
            else expect(wrapper!.textContent ?? '', `${label}: no 🔗 on a charge that is not linked`).not.toContain('🔗');
        }
    });

    // -----------------------------------------------------------------------
    // «Reset row» on an untouched parent whose read failed (coordinator, 19/11)
    // -----------------------------------------------------------------------

    it('an untouched parent whose read failed offers «Reset row», and choosing it reads the charges again: the chip appears, «del» comes on', async () => {
        readMock().mockImplementation((async () => {
            throw new Error('network down');
        }) as never);
        await openBuyAndDeposit();
        await waitFor(() => expect(readAskedFor(BUY.id), 'premise: the read went out').toBe(true));
        await settle();
        expect(rowStatus(gridRow(BUY.id)), 'premise: the parent is untouched').toBe('original');
        expect(chip(), 'premise: no charge held').toBeNull();

        answerChargesRead([FEE, TAX]);
        const before = readMock().mock.calls.length;
        await openMenu(gridRow(BUY.id));
        expect(screen.getByTestId('context-menu-action-reset'), 'an untouched parent whose read failed offers «Reset row»').toBeInTheDocument();
        await clickCollectingErrors(screen.getByTestId('context-menu-action-reset'));

        await waitFor(() => expect(readMock().mock.calls.length, '«Reset row» reads the charges again').toBeGreaterThan(before));
        await waitFor(() => expect(theChip(), 'the chip appears with the two charges').toHaveAttribute('data-charges-count', '2'));
        expect(rowStatus(gridRow(BUY.id)), 'the parent is still untouched').toBe('original');
        await openMenu(gridRow(BUY.id));
        expect(screen.getByTestId('context-menu-action-mark-delete'), '«del» is on again').not.toHaveAttribute('aria-disabled');
        expect(screen.queryByTestId('context-menu-action-reset'), 'and, read, the untouched parent no longer offers «Reset row»').toBeNull();
    });

    it('an untouched parent whose read succeeded offers no «Reset row»', async () => {
        await openLoaded();
        expect(rowStatus(gridRow(BUY.id)), 'premise: the parent is untouched').toBe('original');

        await openMenu(gridRow(BUY.id));

        expect(screen.getByTestId('context-menu-action-mark-delete'), 'barrier: the menu is drawn, «del» on').not.toHaveAttribute('aria-disabled');
        expect(screen.queryByTestId('context-menu-action-reset'), 'nothing to reset').toBeNull();
    });

    // =======================================================================
    // 66 F7-c2 — the V1 panel inside the Bulk (contract 66-F7 §12, §16.4, §17 corrected by §18)
    // =======================================================================

    /**
     * «Delete» on a saved parent that has linked charges (`linkedChargesOf`) opens `TxChargesActionModal` in
     * `deleteParent` mode BEFORE marking anything; «Keep» / «Delete all» / «Cancel» (or Esc, which closes the panel only)
     * decide. «Delete selected» asks once for every selected parent, after the reads in flight land; a parent whose read
     * failed is skipped with a warning toast (`transactions.bulk.deleteSkippedUnread`, `{n}`). The F7-b interim (a parent
     * «del» unlinks its charges by itself) is gone; the delete intent from the page (§15.1) is not this path.
     * The panel's counts are read as the catalogue renders them for the expected numbers, never as words.
     */
    // -----------------------------------------------------------------------
    // 66 TL-4 (P-2 = C, P-19): a checkbox on every charge under its parent, and «Scollega» on the selection bar
    // -----------------------------------------------------------------------

    /**
     * TL-4 (lane 66, the developer's P-2 = C; spec `lotti-testlist-20261123-FEE.md` «TL-4», P-19 under «TL-9»):
     *   - every charge sitting under its parent has its own checkbox; ticking the parent never ticks its charges, nor
     *     the reverse; the hidden half of a pair is never selectable;
     *   - «Scollega» on the selection bar (`tx-bulk-unlink-charges`, its count `tx-bulk-unlink-charges-count`): it takes
     *     only the ticked charges still linked under their parent, is absent without one, asks nothing, and empties the
     *     selection; the outcome is «Scollega» in the form;
     *   - «Elimina» on a parent and a charge of it already «del» leaves the charge «del» (P-19);
     *   - «Reimposta», select-all, closing a group, «show only selected», the double-click: see each case.
     * RED until the Bulk draws the checkbox and the action: the reds below fail on the tick of an indented row (no
     * checkbox) or on the absent button. Cases marked «guard» pin what holds today and must stay green.
     */
    describe('66 TL-4: a checkbox on the charges under their parent, and «Scollega» on the bar', () => {
        const PANEL = 'tx-charges-modal-content';

        function unlinkButton(): HTMLElement | null {
            return screen.queryByTestId('tx-bulk-unlink-charges');
        }

        /** The checkbox of a row, which TL-4 requires on an indented row too. */
        function boxOf(row: HTMLElement): HTMLElement {
            const box = rowCheckbox(row);
            if (!box) throw new Error(`TL-4: the row ${row.getAttribute('data-row-id')} (${idCellText(row).trim() || rowDescription(row)}) has no checkbox${chargeOfCell(row) !== null ? ' — an indented charge, which TL-4 gives one' : ''}`);
            return box;
        }

        /** Bring a row's checkbox to `on`; ends in that state. */
        async function setTick(row: HTMLElement, on: boolean): Promise<void> {
            const box = boxOf(row);
            if ((box.getAttribute('data-state') === 'checked') !== on) {
                await fireEvent.click(box);
                await settle();
            }
            expect(boxOf(row), `${idCellText(row).trim() || rowDescription(row)} ${on ? 'ticked' : 'unticked'}`).toHaveAttribute('data-state', on ? 'checked' : 'unchecked');
        }

        /** What the selection bar counts, `0` when it is not drawn. */
        function selectedCount(): number {
            const bar = screen.queryByTestId('selection-toolbar');
            return bar ? Number(bar.getAttribute('data-selected-count')) : 0;
        }

        /** The BUY's group open; ends on it open. */
        async function openGroup(): Promise<void> {
            if (theChip().getAttribute('aria-expanded') !== 'true') {
                await fireEvent.click(theChip());
                await settle();
            }
            expect(theChip()).toHaveAttribute('aria-expanded', 'true');
            expect(rowsOf(FEE.id), 'premise: the FEE is drawn').toHaveLength(1);
        }

        /** «Scollega», present and on; click; ends settled. */
        async function unlinkSelected(): Promise<void> {
            const button = unlinkButton();
            expect(button, 'TL-4: the selection offers «Scollega» (tx-bulk-unlink-charges)').not.toBeNull();
            expect(button).not.toHaveAttribute('aria-disabled', 'true');
            expect(await clickCollectingErrors(button!), '«Scollega» throws nothing').toEqual([]);
        }

        it('ticking a charge under its parent does not tick the parent, nor the other charge; ticking the parent ticks no charge', async () => {
            await openLoaded();
            await openGroup();

            await setTick(gridRow(FEE.id), true);
            expect(boxOf(gridRow(BUY.id)), 'the parent stays unticked').toHaveAttribute('data-state', 'unchecked');
            expect(boxOf(gridRow(TAX.id)), 'the TAX stays unticked').toHaveAttribute('data-state', 'unchecked');
            expect(selectedCount()).toBe(1);

            await setTick(gridRow(FEE.id), false);
            await setTick(gridRow(BUY.id), true);
            for (const charge of [FEE, TAX]) expect(boxOf(gridRow(charge.id)), `${charge.type} not ticked by its parent`).toHaveAttribute('data-state', 'unchecked');
            expect(selectedCount()).toBe(1);
        });

        it('guard: no linked charge among the ticked rows — no «Scollega»', async () => {
            await openLoaded();
            await setTick(gridRow(BUY.id), true);
            await setTick(gridRow(DEP.id), true);

            expect(screen.queryByTestId('tx-bulk-delete-selected'), 'barrier: the selection bar is drawn').not.toBeNull();
            expect(unlinkButton(), 'a parent and a deposit: nothing «Scollega» could take').toBeNull();
        });

        it('«Scollega» takes only the linked charges ticked and says how many: BUY + FEE + TAX + DEPOSIT ticked → 2', async () => {
            await openLoaded();
            await openGroup();
            for (const id of [BUY.id, FEE.id, TAX.id, DEP.id]) await setTick(gridRow(id), true);
            expect(selectedCount(), 'premise: four rows ticked').toBe(4);

            expect(unlinkButton(), 'TL-4: «Scollega» on the bar').not.toBeNull();
            expect(screen.getByTestId('tx-bulk-unlink-charges-count'), 'it takes the FEE and the TAX').toHaveTextContent('2');
        });

        it('«Scollega» on the TAX: a row of its own with the badge «unlink», the BUY counts 1, no panel, the selection empty; the payload unlinks it (0)', async () => {
            await openLoaded();
            await openGroup();
            await setTick(gridRow(TAX.id), true);

            await unlinkSelected();

            expect(screen.queryByTestId(PANEL), 'no confirmation panel').toBeNull();
            expect(chargeOfCell(gridRow(TAX.id)), 'the TAX is a top-level row').toBeNull();
            expect(chargeState(gridRow(TAX.id)), 'with the badge «unlink»').toBe('unlink');
            expect(theChip(), 'the BUY keeps the FEE alone').toHaveAttribute('data-charges-count', '1');
            expect(chargeState(gridRow(FEE.id)), 'the FEE, not ticked, untouched').toBe('linked');
            expect(rowStatus(gridRow(BUY.id)), 'the parent unchanged').toBe('original');
            expect(selectedCount(), 'after «Scollega» the selection is empty').toBe(0);

            const body = await validateNow();
            expect(
                (body.updates ?? []).filter((update) => update.id === TAX.id).map((update) => update.parent_transaction_id),
                'the TAX is sent unlinked',
            ).toEqual([0]);
            expect(
                (body.updates ?? []).filter((update) => update.id === FEE.id),
                'nothing sent for the FEE',
            ).toEqual([]);
        });

        it('«Scollega» on a new charge born in the parent’s Form: a new row of its own, with the BUY’s broker, asset and date; no parent_ref', async () => {
            await openLoaded();
            await openBuyForm(2);
            await push(buyPayload({_charges: [...handedDrafts(), newDraft('FEE', '2', 'TL4 new fee')]}));
            expect(chargeOfCell(gridRowDescribed('TL4 new fee')), 'premise: the new FEE sits under the BUY').toBe(buyRowId());

            await setTick(gridRowDescribed('TL4 new fee'), true);
            await unlinkSelected();

            expect(chargeOfCell(gridRowDescribed('TL4 new fee')), 'a row of its own').toBeNull();
            expect(theChip(), 'the BUY keeps its two saved charges').toHaveAttribute('data-charges-count', '2');
            const body = await validateNow();
            const creates = (body.creates ?? []).filter((create) => create.description === 'TL4 new fee');
            expect(creates, 'one create of the new FEE').toHaveLength(1);
            expect({parent_ref: creates[0].parent_ref, broker_id: creates[0].broker_id, asset_id: creates[0].asset_id, date: creates[0].date}).toEqual({parent_ref: undefined, broker_id: BUY.broker_id, asset_id: BUY.asset_id, date: BUY.date});
        });

        it('a charge «del» under a parent that stays, ticked → «Scollega»: «unlink», no longer «del» (Del → Scollega)', async () => {
            await openLoaded();
            await openGroup();
            await rowAction(gridRow(FEE.id), 'mark-delete');
            expect(chargeState(gridRow(FEE.id)), 'premise: the FEE is «del»').toBe('del');
            await setTick(gridRow(FEE.id), true);
            expect(screen.getByTestId('tx-bulk-unlink-charges-count'), 'a «del» charge counts').toHaveTextContent('1');

            await unlinkSelected();

            expect(chargeState(gridRow(FEE.id))).toBe('unlink');
            expect(rowStatus(gridRow(FEE.id)), 'no longer «del»').not.toBe('delete');
            const body = await validateNow();
            expect(body.deletes ?? [], 'no delete of the FEE').not.toContain(FEE.id);
            expect((body.updates ?? []).filter((update) => update.id === FEE.id).map((update) => update.parent_transaction_id)).toEqual([0]);
        });

        it('P-19: «Elimina» on the BUY, its FEE already «del» and its TAX, ticked together: no panel; BUY «del», the FEE still «del», the TAX «del»', async () => {
            await openLoaded();
            await openGroup();
            await rowAction(gridRow(FEE.id), 'mark-delete');
            expect(chargeState(gridRow(FEE.id)), 'premise: the FEE is «del»').toBe('del');
            for (const id of [BUY.id, FEE.id, TAX.id]) await setTick(gridRow(id), true);

            await fireEvent.click(screen.getByTestId('tx-bulk-delete-selected'));
            await settle();

            expect(screen.queryByTestId(PANEL), 'every charge ticked: no panel').toBeNull();
            expect(rowStatus(gridRow(BUY.id))).toBe('delete');
            expect(chargeState(gridRow(FEE.id)), 'P-19: the FEE stays «del»').toBe('del');
            expect(chargeState(gridRow(TAX.id))).toBe('del');
        });

        it('«Reimposta» on a ticked charge «del» under a parent that stays: back as saved, linked', async () => {
            await openLoaded();
            await openGroup();
            await rowAction(gridRow(FEE.id), 'mark-delete');
            expect(chargeState(gridRow(FEE.id)), 'premise').toBe('del');
            await setTick(gridRow(FEE.id), true);

            const reset = screen.queryByTestId('tx-bulk-reset-selected');
            expect(reset, '«Reimposta» is offered for the ticked «del» charge').not.toBeNull();
            expect(await clickCollectingErrors(reset!)).toEqual([]);

            expect(chargeState(gridRow(FEE.id)), 'linked again').toBe('linked');
            expect(rowStatus(gridRow(FEE.id))).toBe('original');
            expect(chargeOfCell(gridRow(FEE.id)), 'under the BUY').toBe(buyRowId());
        });

        it('«Reimposta» on a ticked charge whose note changed: back to its saved note', async () => {
            await openLoaded();
            await editTaxNoteInParentForm();
            await openGroup();
            expect(rowStatus(gridRow(TAX.id)), 'premise: the TAX is edited').toBe('edited');
            await setTick(gridRow(TAX.id), true);

            const reset = screen.queryByTestId('tx-bulk-reset-selected');
            expect(reset).not.toBeNull();
            expect(await clickCollectingErrors(reset!)).toEqual([]);

            expect(rowStatus(gridRow(TAX.id))).toBe('original');
            expect(rowDescription(gridRow(TAX.id))).toBe(TAX.description);
            expect(chargeOfCell(gridRow(TAX.id)), 'still under the BUY').toBe(buyRowId());
        });

        it('«Reimposta» on a ticked charge «scollega» under a parent «del» (Keep): it stays «scollega» under it (C21)', async () => {
            await openLoaded();
            await editTaxNoteInParentForm();
            await rowAction(gridRow(BUY.id), 'mark-delete');
            await fireEvent.click(within(await screen.findByTestId(PANEL)).getByTestId('tx-charges-modal-keep'));
            await settle();
            await waitFor(() => expect(screen.queryByTestId(PANEL)).toBeNull());
            await openGroup();
            expect(chargeState(gridRow(TAX.id)), 'premise: the TAX is «scollega» under the parent «del»').toBe('unlink');
            await setTick(gridRow(TAX.id), true);

            const reset = screen.queryByTestId('tx-bulk-reset-selected');
            expect(reset, '«Reimposta» is offered (the TAX’s note changed)').not.toBeNull();
            expect(await clickCollectingErrors(reset!)).toEqual([]);

            expect(rowStatus(gridRow(BUY.id)), 'the parent stays «del»').toBe('delete');
            expect(chargeState(gridRow(TAX.id)), 'under a parent «del» the TAX stays «scollega»').toBe('unlink');
            expect(rowDescription(gridRow(TAX.id)), 'its note back as saved').toBe(TAX.description);
            expect(chargeOfCell(gridRow(TAX.id)), 'still drawn under it').toBe(buyRowId());
        });

        // Derived (lane): the same rule from a charge «del» (Delete all) instead of «scollega».
        it('derived: «Reimposta» on a ticked charge «del» under a parent «del» (Delete all): it comes back «scollega» under it (C21)', async () => {
            await openLoaded();
            await rowAction(gridRow(BUY.id), 'mark-delete');
            await fireEvent.click(within(await screen.findByTestId(PANEL)).getByTestId('tx-charges-modal-all'));
            await settle();
            await waitFor(() => expect(screen.queryByTestId(PANEL)).toBeNull());
            await openGroup();
            expect(chargeState(gridRow(FEE.id)), 'premise: the FEE is «del» under the parent «del»').toBe('del');
            await setTick(gridRow(FEE.id), true);

            const reset = screen.queryByTestId('tx-bulk-reset-selected');
            expect(reset).not.toBeNull();
            expect(await clickCollectingErrors(reset!)).toEqual([]);

            expect(rowStatus(gridRow(BUY.id)), 'the parent stays «del»').toBe('delete');
            expect(chargeState(gridRow(FEE.id)), 'under a parent «del» the FEE comes back «scollega»').toBe('unlink');
            expect(chargeOfCell(gridRow(FEE.id)), 'still drawn under it').toBe(buyRowId());
        });

        it('no «Unisci in coppia» with charges ticked', async () => {
            await openLoaded();
            await openGroup();
            await setTick(gridRow(FEE.id), true);
            await setTick(gridRow(TAX.id), true);

            expect(screen.queryByTestId('tx-bulk-delete-selected'), 'barrier: the selection bar is drawn').not.toBeNull();
            expect(screen.queryByTestId('promote-toolbar-confirm'), 'a FEE and a TAX make no pair').toBeNull();
        });

        it('select-all ticks the drawn rows: a closed group’s charges no, an open group’s yes', async () => {
            await openLoaded();
            const all = screen.getByTestId('dt-select-all');

            await fireEvent.click(all);
            await settle();
            expect(selectedCount(), 'closed group: the BUY and the DEPOSIT').toBe(2);
            await fireEvent.click(screen.getByTestId('dt-select-all'));
            await settle();
            expect(selectedCount(), 'premise: none ticked').toBe(0);

            await openGroup();
            await fireEvent.click(screen.getByTestId('dt-select-all'));
            await settle();
            for (const id of [BUY.id, FEE.id, TAX.id, DEP.id]) expect(boxOf(gridRow(id)), `#${id} ticked`).toHaveAttribute('data-state', 'checked');
            expect(selectedCount(), 'the open group’s charges too').toBe(4);
        });

        it('closing a group keeps its ticked charges ticked and counted; reopened, still ticked', async () => {
            await openLoaded();
            await openGroup();
            await setTick(gridRow(FEE.id), true);
            await setTick(gridRow(DEP.id), true);

            await fireEvent.click(theChip());
            await settle();
            expect(theChip()).toHaveAttribute('aria-expanded', 'false');
            expect(rowsOf(FEE.id), 'premise: the FEE is not drawn').toHaveLength(0);

            expect(selectedCount(), 'the FEE, out of sight, still counts').toBe(2);
            expect(unlinkButton(), '«Scollega» still takes it').not.toBeNull();
            expect(screen.getByTestId('tx-bulk-unlink-charges-count')).toHaveTextContent('1');

            await openGroup();
            expect(boxOf(gridRow(FEE.id)), 'reopened: still ticked').toHaveAttribute('data-state', 'checked');
        });

        it('«show only selected» with only charges ticked shows them', async () => {
            await openLoaded();
            await openGroup();
            await setTick(gridRow(FEE.id), true);
            await setTick(gridRow(TAX.id), true);

            await fireEvent.click(screen.getByTestId('dt-show-selected-only'));
            await settle();

            expect(screen.getByTestId('dt-show-selected-only')).toHaveAttribute('data-state', 'on');
            expect(rowsOf(FEE.id), 'the FEE is shown').toHaveLength(1);
            expect(rowsOf(TAX.id), 'the TAX is shown').toHaveLength(1);
            expect(rowsOf(DEP.id), 'the DEPOSIT, not ticked, is not').toHaveLength(0);
        });

        it('guard: a double-click on an indented row opens its Form once (the capture and the table’s own handler never both)', async () => {
            await openLoaded();
            await openGroup();
            const before = Number(formProbe().openKey);

            await fireEvent.dblClick(gridRow(TAX.id));
            await settle();

            await waitFor(() => expect(formProbe().open, 'the Form is open').toBe(true));
            expect(formRow()?.id, 'on the TAX').toBe(TAX.id);
            expect(Number(formProbe().openKey) - before, 'opened once').toBe(1);
        });

        it('guard: the hidden half of a merged pair is never selected — every ticked row is a row on screen', async () => {
            mountEditor({action: 'import'});
            await waitFor(() => expect(wizardProbe().open, 'the import intent opens the wizard').toBe(true));
            const leg = (brokerId: number, quantity: string) => ({tx: {broker_id: brokerId, type: 'ADJUSTMENT', date: C46.date, asset_id: C46.assetId, quantity, tags: [], description: 'TL4 pair leg'} as TransactionCreateItem, todos: [] as []});
            (wizardProbe().onImportBatch as (creates: unknown[]) => void)([leg(C46.brokerA, '-5'), leg(C46.brokerB, '5')]);
            await settle();
            const legs = gridRows().filter((row) => rowDescription(row) === 'TL4 pair leg');
            expect(legs, 'premise: two legs on screen').toHaveLength(2);
            for (const row of legs) await setTick(row, true);
            const merge = screen.queryByTestId('promote-toolbar-confirm');
            expect(merge, 'premise: the two legs are offered as a merge').not.toBeNull();

            expect(await clickCollectingErrors(merge!)).toEqual([]);
            await waitFor(() =>
                expect(
                    gridRows().filter((row) => rowDescription(row) === 'TL4 pair leg'),
                    'one row for the pair',
                ).toHaveLength(1),
            );

            const ticked = gridRows().filter((row) => row.getAttribute('data-selected') === 'true').length;
            expect(ticked, 'premise: the merged pair’s row is still ticked, so the check below has something to compare').toBeGreaterThan(0);
            expect(selectedCount(), 'the bar counts only rows on screen: the hidden half is not selected').toBe(ticked);
        });
    });

    describe('66 F7-c2: the delete panel inside the Bulk', () => {
        const PANEL = 'tx-charges-modal-content';
        const FREE: TXReadItem = {...FEE, id: 91_731, parent_transaction_id: null, description: 'F7c2 free fee'};
        const PARENT_A: TXReadItem = {...SAVED_BUY, id: 91_741, charges_count: 0, description: 'F7c2 parent A'};
        const PARENT_B: TXReadItem = {...SAVED_BUY, id: 91_751, date: '2026-09-16', charges_count: 0, description: 'F7c2 parent B'};

        /** The panel, open in deleteParent mode. */
        async function panel(): Promise<HTMLElement> {
            const content = await screen.findByTestId(PANEL);
            expect(content).toHaveAttribute('data-mode', 'deleteParent');
            return content;
        }

        /** Click a panel button (keep / all / cancel); ends on the panel gone. */
        async function choose(button: 'keep' | 'all' | 'cancel'): Promise<void> {
            const content = await panel();
            await fireEvent.click(within(content).getByTestId(`tx-charges-modal-${button}`));
            await settle();
            await waitFor(() => expect(screen.queryByTestId(PANEL), 'the panel closed').toBeNull());
        }

        /** Tick a row's checkbox. */
        async function tick(row: HTMLElement): Promise<void> {
            const box = rowCheckbox(row);
            if (!box) throw new Error('the row has no checkbox');
            await fireEvent.click(box);
            await settle();
        }

        /** «Delete selected» in the selection toolbar. */
        async function deleteSelected(): Promise<void> {
            await fireEvent.click(screen.getByTestId('tx-bulk-delete-selected'));
            await settle();
        }

        /** The one create of this type in a body. */
        function onlyCreateOf(body: Payload, type: string): Record<string, unknown> {
            const found = (body.creates ?? []).filter((create) => create.type === type);
            expect(found, `one ${type} create`).toHaveLength(1);
            return found[0];
        }

        /** The kept-charges count and the all count the panel shows, read against the catalogue. */
        function expectCounts(content: HTMLElement, keep: number, all: number): void {
            expect(within(content).getByTestId('tx-charges-modal-keep-after')).toHaveTextContent(get(_)('transactions.chargesDelete.keepAfter', {values: {n: keep}}));
            expect(within(content).getByTestId('tx-charges-modal-all-after')).toHaveTextContent(get(_)('transactions.chargesDelete.allAfter', {values: {n: all}}));
        }

        // -------------------------------------------------------------------
        // Single «Delete» (row menu)
        // -------------------------------------------------------------------

        it('«Delete» on a saved parent with linked charges opens the panel before marking: the parent is not «del» while it is open; counts 2 / 3', async () => {
            await openLoaded();

            await rowAction(gridRow(BUY.id), 'mark-delete');

            const content = await panel();
            expect(rowStatus(gridRow(BUY.id)), 'nothing marked yet').toBe('original');
            expectCounts(content, 2, 3);
            for (const id of ['keep', 'all', 'cancel']) expect(within(content).getByTestId(`tx-charges-modal-${id}`)).toBeInTheDocument();
        });

        it('«Delete» on a row with no linked charge marks it at once, no panel', async () => {
            await openLoaded();

            await rowAction(gridRow(DEP.id), 'mark-delete');

            expect(rowStatus(gridRow(DEP.id))).toBe('delete');
            expect(screen.queryByTestId(PANEL)).toBeNull();
        });

        it('«Cancel» changes nothing: the parent unmarked, its charges linked, the Bulk open', async () => {
            const {onClose} = await openLoaded();
            await rowAction(gridRow(BUY.id), 'mark-delete');

            await choose('cancel');

            expect(rowStatus(gridRow(BUY.id))).toBe('original');
            expect(theChip()).toHaveAttribute('data-charges-count', '2');
            expect(theChip(), 'no charge changed').not.toHaveAttribute('data-charges-modified', 'true');
            expect(screen.getByTestId('tx-bulk-modal')).toBeInTheDocument();
            expect(onClose).not.toHaveBeenCalled();
        });

        it('Esc closes the panel only: nothing changes and the Bulk stays open', async () => {
            const {onClose} = await openLoaded();
            await rowAction(gridRow(BUY.id), 'mark-delete');
            await panel();

            await fireEvent.keyDown(screen.getByTestId('tx-charges-modal'), {key: 'Escape'});
            await settle();

            await waitFor(() => expect(screen.queryByTestId(PANEL)).toBeNull());
            expect(rowStatus(gridRow(BUY.id))).toBe('original');
            expect(screen.getByTestId('tx-bulk-modal')).toBeInTheDocument();
            expect(onClose, 'Esc on the panel does not close the Bulk').not.toHaveBeenCalled();
        });

        it('«Keep»: the parent «del», its saved charges unlinked under it; the batch deletes the parent and unlinks both', async () => {
            await openLoaded();
            await rowAction(gridRow(BUY.id), 'mark-delete');

            await choose('keep');

            expect(rowStatus(gridRow(BUY.id))).toBe('delete');
            for (const charge of [FEE, TAX]) expect(chargeState(gridRow(charge.id)), charge.type).toBe('unlink');
            const body = await validateNow();
            expect(body.deletes ?? []).toEqual([BUY.id]);
            expect(body.updates ?? []).toEqual(
                expect.arrayContaining([
                    {id: FEE.id, parent_transaction_id: 0},
                    {id: TAX.id, parent_transaction_id: 0},
                ]),
            );
        });

        it('«Delete all»: the parent and its saved charges «del», all three in the deletes', async () => {
            await openLoaded();
            await rowAction(gridRow(BUY.id), 'mark-delete');

            await choose('all');

            expect(rowStatus(gridRow(BUY.id))).toBe('delete');
            for (const charge of [FEE, TAX]) expect(chargeState(gridRow(charge.id)), charge.type).toBe('del');
            const body = await validateNow();
            expect([...(body.deletes ?? [])].sort((a, b) => a - b)).toEqual([BUY.id, FEE.id, TAX.id]);
            expect(
                (body.updates ?? []).filter((u) => u.parent_transaction_id === 0),
                'nothing unlinked',
            ).toEqual([]);
        });

        it('«Keep» with a new charge: it becomes a new row of its own, top-level, with the date it followed; no parent sent', async () => {
            await openLoaded();
            await openBuyForm(2);
            await push(buyPayload({date: '2026-09-20', _charges: [...handedDrafts(), newDraft('FEE', '2', 'F7c2 new fee')]}));
            expect(chargeOfCell(gridRowDescribed('F7c2 new fee')), 'premise: the new FEE is under the BUY').toBe(buyRowId());
            await rowAction(gridRow(BUY.id), 'mark-delete');
            expectCounts(await panel(), 3, 4);

            await choose('keep');

            const fresh = gridRowDescribed('F7c2 new fee');
            expect(chargeOfCell(fresh), 'on its own, top-level').toBeNull();
            expect(rowStatus(fresh)).toBe('new');
            const body = await validateNow();
            const create = onlyCreateOf(body, 'FEE');
            expect(create, 'the date it followed, frozen').toMatchObject({date: '2026-09-20', broker_id: BUY.broker_id, asset_id: BUY.asset_id});
            expect(create).not.toHaveProperty('parent_transaction_id');
            expect(create).not.toHaveProperty('parent_ref');
        });

        it('«Delete all» with a new charge: it leaves the Bulk, and «Restore» on the parent does not bring it back', async () => {
            await openLoaded();
            await openBuyForm(2);
            await push(buyPayload({_charges: [...handedDrafts(), newDraft('FEE', '2', 'F7c2 new fee')]}));
            await rowAction(gridRow(BUY.id), 'mark-delete');

            await choose('all');

            expect(
                gridRows().filter((row) => rowDescription(row) === 'F7c2 new fee'),
                'the new charge left',
            ).toHaveLength(0);
            await rowAction(gridRow(BUY.id), 'mark-delete');
            expect(rowStatus(gridRow(BUY.id)), 'restored').toBe('original');
            expect(
                gridRows().filter((row) => rowDescription(row) === 'F7c2 new fee'),
                'and it does not come back',
            ).toHaveLength(0);
            for (const charge of [FEE, TAX]) expect(chargeState(gridRow(charge.id)), `${charge.type} linked again`).toBe('linked');
            expect((await validateNow()).creates ?? []).toEqual([]);
        });

        it('a linkNew charge with «Keep» only loses the local link: no parent_transaction_id is sent for it', async () => {
            txStoreSetAll([BUY, DEP, FREE], []);
            answerChargesRead([FEE, TAX]);
            mountEditor({action: 'edit', txIds: [BUY.id, DEP.id]});
            await waitFor(() => expect(chip(), 'premise: the charges are read').not.toBeNull());
            await openBuyForm(2);
            const linkNew: ChargeDraft = {key: `saved-${FREE.id}`, id: FREE.id, type: 'FEE', cash: {amount: '1.5', code: 'EUR'}, description: FREE.description ?? '', original: null, state: 'linked', linkNew: true};
            await push(buyPayload({_charges: [...handedDrafts(), linkNew]}));
            expect(chargeOfCell(gridRow(FREE.id)), 'premise: the free FEE is linked here').toBe(buyRowId());
            await rowAction(gridRow(BUY.id), 'mark-delete');

            await choose('keep');

            expect(chargeOfCell(gridRow(FREE.id)), 'top-level again').toBeNull();
            const body = await validateNow();
            expect(
                (body.updates ?? []).filter((u) => u.id === FREE.id && 'parent_transaction_id' in u),
                'nothing about a parent it never had saved',
            ).toEqual([]);
            expect(body.deletes ?? []).toEqual([BUY.id]);
        });

        it('«Restore» after «Keep» undoes only what the panel set: a charge unlinked by hand before stays unlinked', async () => {
            await openLoaded();
            await openBuyForm(2);
            await push(buyPayload({_charges: handedDrafts().map((draft): ChargeDraft => (draft.id === TAX.id ? {...draft, state: 'unlink'} : draft))}));
            expect(chargeOfCell(gridRow(TAX.id)), 'premise: the TAX is unlinked by hand, top-level').toBeNull();
            await rowAction(gridRow(BUY.id), 'mark-delete');
            expectCounts(await panel(), 1, 2);
            await choose('keep');
            expect(chargeState(gridRow(FEE.id))).toBe('unlink');

            await rowAction(gridRow(BUY.id), 'mark-delete');

            expect(rowStatus(gridRow(BUY.id))).toBe('original');
            expect(chargeState(gridRow(FEE.id)), 'the FEE the panel unlinked is linked again').toBe('linked');
            expect(chargeState(gridRow(TAX.id)), 'the TAX unlinked by hand stays unlinked').toBe('unlink');
            const body = await validateNow();
            expect(body.updates ?? []).toContainEqual({id: TAX.id, parent_transaction_id: 0});
            expect((body.updates ?? []).filter((u) => u.id === FEE.id && u.parent_transaction_id === 0)).toEqual([]);
            expect(body.deletes ?? []).toEqual([]);
        });

        // -------------------------------------------------------------------
        // «Delete selected»
        // -------------------------------------------------------------------

        it('«Delete selected» with a parent and an unrelated row: one panel; the unrelated row waits for the choice; «Cancel» changes nothing and keeps the selection', async () => {
            await openLoaded();
            await tick(gridRow(BUY.id));
            await tick(gridRow(DEP.id));

            await deleteSelected();

            const content = await panel();
            expectCounts(content, 2, 4);
            expect(rowStatus(gridRow(DEP.id)), 'the unrelated row waits for the choice').toBe('original');
            await choose('cancel');
            expect(rowStatus(gridRow(BUY.id))).toBe('original');
            expect(rowStatus(gridRow(DEP.id))).toBe('original');
            expect(screen.getByTestId('tx-bulk-delete-selected'), 'the selection is kept').toBeInTheDocument();

            await deleteSelected();
            await choose('keep');

            expect(rowStatus(gridRow(BUY.id))).toBe('delete');
            expect(rowStatus(gridRow(DEP.id))).toBe('delete');
            for (const charge of [FEE, TAX]) expect(chargeState(gridRow(charge.id)), charge.type).toBe('unlink');
        });

        it('«Delete selected» on a row already «del» restores it without asking', async () => {
            await openLoaded();
            await rowAction(gridRow(DEP.id), 'mark-delete');
            expect(rowStatus(gridRow(DEP.id)), 'premise').toBe('delete');
            await tick(gridRow(DEP.id));

            await deleteSelected();

            expect(screen.queryByTestId(PANEL)).toBeNull();
            expect(rowStatus(gridRow(DEP.id))).toBe('original');
        });

        it('a top-level charge selected with its parent: its own toggle wins; the panel asks for the linked FEE alone', async () => {
            await openLoaded();
            await openBuyForm(2);
            await push(buyPayload({_charges: handedDrafts().map((draft): ChargeDraft => (draft.id === TAX.id ? {...draft, state: 'unlink'} : draft))}));
            await tick(gridRow(BUY.id));
            await tick(gridRow(TAX.id));

            await deleteSelected();

            expectCounts(await panel(), 1, 3);
            await choose('keep');
            expect(rowStatus(gridRow(BUY.id))).toBe('delete');
            expect(chargeState(gridRow(FEE.id)), 'the linked FEE kept').toBe('unlink');
            expect(rowStatus(gridRow(TAX.id)), 'the TAX the user selected is deleted').toBe('delete');
        });

        it('a selected parent whose read is in flight: nothing happens until it lands, then the panel asks', async () => {
            holdChargesReads();
            await openBuyAndDeposit();
            await waitFor(() => expect(readAskedFor(BUY.id)).toBe(true));
            await tick(gridRow(BUY.id));
            await tick(gridRow(DEP.id));

            await deleteSelected();

            expect(screen.queryByTestId(PANEL), 'waiting for the read').toBeNull();
            expect(rowStatus(gridRow(DEP.id)), 'nothing done yet').toBe('original');
            await releaseRead(0);
            await panel();
            await choose('keep');
            expect(rowStatus(gridRow(BUY.id))).toBe('delete');
            expect(rowStatus(gridRow(DEP.id))).toBe('delete');
        });

        it('a wait cut short by closing the Bulk: when the read lands nothing happens', async () => {
            holdChargesReads();
            const {rerender, onClose} = await openBuyAndDeposit();
            await waitFor(() => expect(readAskedFor(BUY.id)).toBe(true));
            await tick(gridRow(BUY.id));
            await tick(gridRow(DEP.id));
            await deleteSelected();
            expect(rowStatus(gridRow(DEP.id)), 'premise: waiting for the read, nothing done yet').toBe('original');

            await rerender({open: false, intent: {action: 'edit', txIds: [BUY.id, DEP.id]}, onClose});
            await settle();
            heldReads[0].resolve([FEE, TAX]);
            await settle();

            expect(screen.queryByTestId(PANEL), 'no panel for a closed Bulk').toBeNull();
        });

        it('a wait cut short by «Reset all»: when the reads land nothing is marked and no panel opens', async () => {
            const DEP2: TXReadItem = {...DEP, id: 91_712, description: 'F7c2 deposit 2'};
            holdChargesReads();
            txStoreSetAll([BUY, DEP, DEP2], []);
            mountEditor({action: 'edit', txIds: [BUY.id, DEP.id, DEP2.id]});
            await waitFor(() => expect(readAskedFor(BUY.id)).toBe(true));
            await rowAction(gridRow(DEP2.id), 'mark-delete');
            await tick(gridRow(BUY.id));
            await tick(gridRow(DEP.id));
            await deleteSelected();
            expect(rowStatus(gridRow(DEP.id)), 'premise: waiting for the read, nothing done yet').toBe('original');
            expect(screen.queryByTestId(PANEL), 'premise: no panel yet').toBeNull();

            expect(await clickCollectingErrors(screen.getByTestId('tx-bulk-reset-all'))).toEqual([]);
            await releaseRead(0);
            for (let at = 1; at < heldReads.length; at++) await releaseRead(at);

            expect(screen.queryByTestId(PANEL), 'the wait was cancelled by the reset').toBeNull();
            expect(rowStatus(gridRow(DEP.id)), 'nothing marked').toBe('original');
            expect(rowStatus(gridRow(BUY.id))).toBe('original');
        });

        it('a selected parent whose read failed is skipped: the others proceed, and a warning toast says how many were skipped', async () => {
            readMock().mockImplementation((async () => {
                throw new Error('network down');
            }) as never);
            await openBuyAndDeposit();
            await waitFor(() => expect(readAskedFor(BUY.id)).toBe(true));
            await settle();
            await tick(gridRow(BUY.id));
            await tick(gridRow(DEP.id));
            const toasts = await toastsMock();
            toasts.show.mockClear();

            await deleteSelected();

            expect(screen.queryByTestId(PANEL), 'no panel: the only parent was skipped').toBeNull();
            expect(rowStatus(gridRow(BUY.id)), 'the parent stays as it is').toBe('original');
            expect(rowStatus(gridRow(DEP.id)), 'the other row proceeds').toBe('delete');
            const expected = get(_)('transactions.bulk.deleteSkippedUnread', {values: {n: 1}});
            expect(expected, 'premise: the catalogue holds transactions.bulk.deleteSkippedUnread').not.toBe('transactions.bulk.deleteSkippedUnread');
            expect(
                toasts.show.mock.calls.filter((call) => call[0] === 'warning').map((call) => call[1]),
                'a warning toast counts the skipped parent',
            ).toContain(expected);
        });

        it('two saved parents, each with one new charge, selected together: one panel, each new charge under its own parent', async () => {
            txStoreSetAll([PARENT_A, PARENT_B], []);
            mountEditor({action: 'edit', txIds: [PARENT_A.id, PARENT_B.id]});
            await waitFor(() => expect(rowsOf(PARENT_B.id)).toHaveLength(1));
            for (const [parent, type, note] of [
                [PARENT_A, 'FEE', 'F7c2 new fee A'],
                [PARENT_B, 'TAX', 'F7c2 new tax B'],
            ] as const) {
                await rowAction(gridRow(parent.id), 'edit-single');
                await waitForParentForm(parent.id, 0);
                await push(buyPayload({description: parent.description, date: parent.date, _charges: [newDraft(type, '2', note)]}));
            }
            await tick(gridRow(PARENT_A.id));
            await tick(gridRow(PARENT_B.id));

            await deleteSelected();

            const content = await panel();
            expectCounts(content, 2, 4);
            const table = within(content).getByTestId('tx-charges-modal-table');
            const ths = [...table.querySelectorAll<HTMLElement>('thead th[data-testid^="dt-header-"]')].filter((th) => th.getAttribute('data-testid') !== 'dt-header-field');
            expect(ths, 'two parents + two new charges').toHaveLength(4);
            const column = (th: HTMLElement) => th.getAttribute('data-testid')!.slice('dt-header-'.length);
            const typeCell = (th: HTMLElement) => (table.querySelector(`tbody tr[data-row-id="type"] td[data-column-id="${column(th)}"]`)?.textContent ?? '').trim();
            expect(ths[0].textContent ?? '').toContain(`#${PARENT_A.id}`);
            expect(typeCell(ths[1]), 'A’s new FEE under A').toBe(get(_)('transactions.types.FEE'));
            expect(ths[2].textContent ?? '').toContain(`#${PARENT_B.id}`);
            expect(typeCell(ths[3]), 'B’s new TAX under B').toBe(get(_)('transactions.types.TAX'));
            // Re-targeted in F7-d (§22.1, §23.1): a new row is named by its Bulk label, so the two new charges are told apart.
            expect((ths[1].textContent ?? '').trim(), 'the two new charges are told apart').not.toBe((ths[3].textContent ?? '').trim());
            for (const th of ths) expect(th.textContent ?? '', 'no TX #0').not.toContain('#0');
        });
    });

    // -----------------------------------------------------------------------
    // 66 F7-d (contract 66-F7 §20, corrected by §21, §22)
    // -----------------------------------------------------------------------

    /**
     * F7-d inside the Bulk:
     *   - §20.2: a delete intent carries `chargeIds` (the charges chosen with their parent on the page); the Bulk marks
     *     them `byParentChoice`, so «Restore» on the parent takes them back too (deviation 1 of C15);
     *   - §20.3 + §21.1: a delete request while another waits leaves out the rows the first holds; the guard is released
     *     in `finally`, a cut wait included;
     *   - §20.4 + §21.4 + §22.4: «Open» in the nested Form (`onOpenTransaction`) moves the Form to that row, adding a
     *     saved row absent from the Bulk (store first, then the server); the row it adds joins the close guard's baseline;
     *   - §20.5 + §21.2 + §22.1: U3, «Link» in the selection group of the toolbar (`tx-bulk-link-charges`), its panel
     *     (`TxChargesActionModal`, `mode="link"`), and the payload «Save all» sends.
     *
     * The Form is a probe: «Open» is the probe's `onOpenTransaction`, called as the real Form calls it after its own
     * discard confirmation. A read by id goes through the same mocked `query_transactions_api_v1_transactions_get` as the
     * charges read, with `ids` instead of `parent_ids` (the page's `fetchTransactionById` does so today).
     */
    describe('66 F7-d: chargeIds, the delete guard, «Open» and «Link» inside the Bulk', () => {
        const PANEL = 'tx-charges-modal-content';
        /** A saved BUY with one charge, absent from the Bulk until «Open» brings it. */
        const BUY_S: TXReadItem = {...SAVED_BUY, id: 91_801, charges_count: 1, description: 'F7d parent'};
        const FEE_S: TXReadItem = {...FEE, id: 91_802, parent_transaction_id: BUY_S.id, description: 'F7d fee'};
        /** A saved BUY with no charge, and a saved FEE linked to nothing, on the same broker and asset. */
        const BUY_L: TXReadItem = {...SAVED_BUY, id: 91_811, charges_count: 0, description: 'F7d lone buy'};
        const BUY_L2: TXReadItem = {...SAVED_BUY, id: 91_813, date: '2026-09-15', charges_count: 0, description: 'F7d lone buy 2'};
        const FREE: TXReadItem = {...FEE, id: 91_812, parent_transaction_id: null, description: 'F7d free fee'};
        /** A saved BUY A with its FEE, and a saved BUY B with none: the FEE unlinked from A here and linked to B. */
        const PARENT_A: TXReadItem = {...SAVED_BUY, id: 91_821, charges_count: 1, description: 'F7d parent A'};
        const FEE_A: TXReadItem = {...FEE, id: 91_822, parent_transaction_id: PARENT_A.id, description: 'F7d fee of A'};
        const PARENT_B: TXReadItem = {...SAVED_BUY, id: 91_831, date: '2026-09-16', charges_count: 0, description: 'F7d parent B'};

        type IdsArgs = {queries?: {parent_ids?: number[]; ids?: number[]}} | undefined;
        type HeldById = {ids: number[]; resolve: (rows: TXReadItem[]) => void; reject: (error: unknown) => void};
        let heldById: HeldById[] = [];

        beforeEach(() => {
            heldById = [];
            // «Link» reads the user's right to edit a row's broker, as the page does: broker 77 is the user's own.
            mergeBrokers([{id: 77, name: 'F7d broker', user_role: 'OWNER'}]);
        });

        afterEach(() => {
            resetBrokerStore();
        });

        /**
         * One responder for both kinds of read: `parent_ids` answers from `charges`, `ids` from `byId` (`'hold'`: held
         * in `heldById` until the test answers; `'fail'`: rejected).
         */
        function answerReads(charges: TXReadItem[], byId: TXReadItem[] | 'hold' | 'fail' = []): void {
            readMock().mockImplementation(((args: IdsArgs) => {
                const ids = args?.queries?.ids;
                if (ids) {
                    if (byId === 'fail') return Promise.reject(new Error('network down'));
                    if (byId === 'hold') return new Promise<TXReadItem[]>((resolve, reject) => heldById.push({ids, resolve, reject}));
                    return Promise.resolve(byId.filter((row) => ids.includes(row.id)));
                }
                return Promise.resolve(chargesOf(args?.queries?.parent_ids ?? [], charges));
            }) as never);
        }

        /** Whether the editor read these ids (`ids`, not `parent_ids`). */
        function readById(id: number): boolean {
            return readMock().mock.calls.some((call) => ((call[0] as IdsArgs)?.queries?.ids ?? []).includes(id));
        }

        /** «Open» in the nested Form: the probe's `onOpenTransaction`, which TBM must hand its Form. */
        async function openFromForm(id: number): Promise<void> {
            const onOpen = formProbe().onOpenTransaction;
            expect(onOpen, 'TBM hands its nested Form onOpenTransaction (§20.4)').toBeTypeOf('function');
            (onOpen as (id: number) => void)(id);
            flushSync();
            await settle();
        }

        /** The Form is open on the saved row `txId`. */
        async function formOn(txId: number): Promise<void> {
            await waitFor(() => {
                expect(formProbe().open, 'the Form is open').toBe(true);
                expect(formRow()?.id, `the Form shows #${txId}`).toBe(txId);
            });
        }

        /** The Form opened on a saved row from its menu. */
        async function openRowForm(txId: number): Promise<void> {
            await rowAction(gridRow(txId), 'edit-single');
            await formOn(txId);
        }

        /** The events of the app's ring buffer after `since` with this name (`notify`, the machine half). */
        function eventsSince(since: number, name: string): Array<{name: string; detail?: Record<string, unknown>}> {
            const lf = (window as unknown as {__lf?: {events?: Array<{seq: number; name: string; detail?: Record<string, unknown>}>}}).__lf;
            return (lf?.events ?? []).filter((event) => event.seq > since && event.name === name);
        }

        function eventSeq(): number {
            const lf = (window as unknown as {__lf?: {seq?: () => number}}).__lf;
            return lf?.seq?.() ?? 0;
        }

        /** Tick a row's checkbox, whatever state it is in; ends checked. */
        async function tickRow(row: HTMLElement): Promise<void> {
            const box = rowCheckbox(row);
            if (!box) throw new Error('the row has no checkbox');
            if (box.getAttribute('data-state') !== 'checked') {
                await fireEvent.click(box);
                await settle();
            }
            expect(rowCheckbox(row)).toHaveAttribute('data-state', 'checked');
        }

        async function deleteSelected(): Promise<void> {
            await fireEvent.click(screen.getByTestId('tx-bulk-delete-selected'));
            await settle();
        }

        async function saveAll(): Promise<Payload> {
            const {commitTransactions} = await api();
            const commit = screen.getByTestId('tx-bulk-commit');
            expect(commit, '«Save all» is on').not.toBeDisabled();
            await fireEvent.click(commit);
            await settle();
            await waitFor(() => expect(commitTransactions, 'Save all committed').toHaveBeenCalledTimes(1));
            return commitTransactions.mock.calls[0]?.[0] as Payload;
        }

        /** «+ Add row», and the row the Form pushes back; ends on the Form closed. */
        async function addRow(payload: Record<string, unknown>): Promise<void> {
            await fireEvent.click(screen.getByTestId('tx-bulk-add-row'));
            await settle();
            await waitFor(() => expect(formProbe().open, '«Add row» opens the Form').toBe(true));
            await push(payload);
        }

        /** A new charge typed on its own in the Form (not in a parent's charges section). */
        function chargePayload(type: 'FEE' | 'TAX', description: string, over: Record<string, unknown> = {}): Record<string, unknown> {
            return {broker_id: 77, type, date: '2026-09-13', quantity: '0', asset_id: 101, cash: {code: 'EUR', amount: '-1.500000'}, description, ...over};
        }

        /** A DEPOSIT typed in the Form. */
        function depositPayload(description: string): Record<string, unknown> {
            return {broker_id: 77, type: 'DEPOSIT', date: '2026-09-14', quantity: '0', asset_id: null, cash: {code: 'EUR', amount: '50.000000'}, description};
        }

        /** The one create of this type in a body. */
        function onlyCreateOf(body: Payload, type: string): Record<string, unknown> {
            const found = (body.creates ?? []).filter((create) => create.type === type);
            expect(found, `one ${type} create`).toHaveLength(1);
            return found[0];
        }

        /** The updates of a body for this id. */
        function updatesOf(body: Payload, id: number): Array<Record<string, unknown>> {
            return (body.updates ?? []).filter((update) => update.id === id);
        }

        /** The grid row id (tempId) of a row. */
        function rowIdOf(row: HTMLElement): string {
            const id = row.getAttribute('data-row-id');
            if (!id) throw new Error('the row publishes no data-row-id');
            return id;
        }

        // -------------------------------------------------------------------
        // §20.2 — the delete intent carries chargeIds
        // -------------------------------------------------------------------

        describe('§20.2: a delete intent with chargeIds', () => {
            /** The editor opened by a delete intent on the BUY and its charges, all three in the store. */
            async function openDeleteIntent(intent: Record<string, unknown>): Promise<void> {
                txStoreSetAll([BUY, FEE, TAX], []);
                answerChargesRead([FEE, TAX]);
                mountEditor(intent as WorkspaceIntent);
                await waitFor(() => expect(rowsOf(BUY.id), 'premise: the BUY is on screen').toHaveLength(1));
                await settle();
                expect(rowStatus(gridRow(BUY.id)), 'premise: the BUY is marked for deletion').toBe('delete');
            }

            it('«Delete all» from the page: the charges «del» under the BUY; «Restore» on the BUY restores them too, and Save all goes off', async () => {
                await openDeleteIntent({action: 'delete', txIds: [BUY.id, FEE.id, TAX.id], unlinkIds: [], chargeIds: [FEE.id, TAX.id]});
                await waitFor(() => expect(chargeState(gridRow(FEE.id)), 'premise: the FEE is «del» under the BUY').toBe('del'));
                expect(chargeState(gridRow(TAX.id)), 'premise: the TAX is «del» under the BUY').toBe('del');

                await rowAction(gridRow(BUY.id), 'mark-delete');

                expect(rowStatus(gridRow(BUY.id)), 'the BUY is restored').toBe('original');
                expect(chargeState(gridRow(FEE.id)), 'the FEE chosen with the BUY comes back linked').toBe('linked');
                expect(chargeState(gridRow(TAX.id)), 'the TAX chosen with the BUY comes back linked').toBe('linked');
                expect(screen.getByTestId('tx-bulk-commit'), 'nothing left to save').toBeDisabled();
            });

            it('a charge the user selected on the page (in txIds, not in chargeIds) stays «del» when the BUY is restored', async () => {
                await openDeleteIntent({action: 'delete', txIds: [BUY.id, FEE.id, TAX.id], unlinkIds: [], chargeIds: [TAX.id]});
                await waitFor(() => expect(chargeState(gridRow(FEE.id))).toBe('del'));

                await rowAction(gridRow(BUY.id), 'mark-delete');

                expect(rowStatus(gridRow(BUY.id))).toBe('original');
                expect(chargeState(gridRow(TAX.id)), 'the TAX chosen with the BUY comes back').toBe('linked');
                // A charge restored under a parent that is no longer «del» is under it: its own «del» stays, the user asked for it.
                expect(chargeState(gridRow(FEE.id)), 'the FEE the user selected stays «del»').toBe('del');
                const body = await validateNow();
                expect(body.deletes ?? []).toEqual([FEE.id]);
            });

            it('guard: «Keep» from the page (unlinkIds with chargeIds) — unchanged: «unlink» under the BUY, and «Restore» links them again', async () => {
                await openDeleteIntent({action: 'delete', txIds: [BUY.id], unlinkIds: [FEE.id, TAX.id], chargeIds: [FEE.id, TAX.id]});
                await waitFor(() => expect(chargeState(gridRow(FEE.id))).toBe('unlink'));
                expect(chargeState(gridRow(TAX.id))).toBe('unlink');

                await rowAction(gridRow(BUY.id), 'mark-delete');

                expect(chargeState(gridRow(FEE.id))).toBe('linked');
                expect(chargeState(gridRow(TAX.id))).toBe('linked');
                expect(screen.getByTestId('tx-bulk-commit')).toBeDisabled();
            });
        });

        // -------------------------------------------------------------------
        // §20.3 + §21.1 — a delete request while another waits
        // -------------------------------------------------------------------

        describe('§21.1: a delete request while another waits for a read', () => {
            /** The BUY's read lands with no charge left (its charges were deleted elsewhere): «del» needs no choice. */
            async function releaseEmpty(at: number): Promise<void> {
                const read = heldReads[at];
                if (!read) throw new Error(`no charges read #${at} was made (made: ${heldReads.length})`);
                read.resolve([]);
                await settle();
            }

            it('two «Delete selected» on the same rows during the wait: the rows end «del» once, not toggled back', async () => {
                holdChargesReads();
                await openBuyAndDeposit();
                await waitFor(() => expect(readAskedFor(BUY.id)).toBe(true));
                await tickRow(gridRow(BUY.id));
                await tickRow(gridRow(DEP.id));

                await deleteSelected();
                await deleteSelected();
                expect(rowStatus(gridRow(DEP.id)), 'premise: waiting for the read, nothing done yet').toBe('original');
                await releaseEmpty(0);

                expect(screen.queryByTestId(PANEL), 'no linked charge: no panel').toBeNull();
                expect(rowStatus(gridRow(BUY.id)), 'the BUY «del» once').toBe('delete');
                expect(rowStatus(gridRow(DEP.id)), 'the DEPOSIT «del» once').toBe('delete');
            });

            it('guard: «Delete» on a row the waiting request does not hold proceeds at once', async () => {
                const DEP2: TXReadItem = {...DEP, id: 91_714, description: 'F7d deposit 2'};
                holdChargesReads();
                txStoreSetAll([BUY, DEP, DEP2], []);
                mountEditor({action: 'edit', txIds: [BUY.id, DEP.id, DEP2.id]});
                await waitFor(() => expect(readAskedFor(BUY.id)).toBe(true));
                await tickRow(gridRow(BUY.id));
                await tickRow(gridRow(DEP.id));
                await deleteSelected();
                expect(rowStatus(gridRow(DEP.id)), 'premise: the selection waits').toBe('original');

                await rowAction(gridRow(DEP2.id), 'mark-delete');

                expect(rowStatus(gridRow(DEP2.id)), 'the unrelated row does not wait').toBe('delete');
                expect(rowStatus(gridRow(DEP.id)), 'the waiting rows still wait').toBe('original');
            });

            it('guard: after a wait cut by «Reset all», a new request on a row the cut one held works (the guard was released)', async () => {
                holdChargesReads();
                await openBuyAndDeposit();
                await waitFor(() => expect(readAskedFor(BUY.id)).toBe(true));
                // A new row keeps its tempId across «Reset all»: the guard is the only thing that could still hold it.
                await addRow(depositPayload('F7d new deposit'));
                // «Reset all» is offered once a saved row is changed: the DEPOSIT «del».
                await rowAction(gridRow(DEP.id), 'mark-delete');
                await tickRow(gridRow(BUY.id));
                await tickRow(gridRowDescribed('F7d new deposit'));
                await deleteSelected();
                expect(
                    gridRows().some((row) => rowDescription(row) === 'F7d new deposit'),
                    'premise: waiting, the new row is still there',
                ).toBe(true);

                expect(await clickCollectingErrors(screen.getByTestId('tx-bulk-reset-all'))).toEqual([]);
                for (let at = 0; at < heldReads.length; at++) await releaseEmpty(at);
                expect(
                    gridRows().some((row) => rowDescription(row) === 'F7d new deposit'),
                    'the cut request removed nothing',
                ).toBe(true);

                await tickRow(gridRowDescribed('F7d new deposit'));
                await deleteSelected();

                expect(
                    gridRows().filter((row) => rowDescription(row) === 'F7d new deposit'),
                    'the new request removes the new row',
                ).toHaveLength(0);
            });
        });

        // -------------------------------------------------------------------
        // §20.4 + §21.4 + §22.4 — «Open» in the nested Form
        // -------------------------------------------------------------------

        describe('§20.4: «Open» in the nested Form', () => {
            it('a saved row present in the Bulk: the Form moves to it, highlighting the row the user came from', async () => {
                await openLoaded();
                await openBuyForm(2);

                await openFromForm(FEE.id);

                await formOn(FEE.id);
                expect(formProbe().highlightTxId, 'the row the user came from').toBe(BUY.id);
            });

            it('a charge under a closed group: the group opens, so the row is on screen when the Form closes', async () => {
                await openLoaded();
                expect(rowsOf(FEE.id), 'premise: the group is closed').toHaveLength(0);
                await openBuyForm(2);

                await openFromForm(FEE.id);

                await formOn(FEE.id);
                expect(rowsOf(FEE.id), 'the FEE is on screen under its BUY').toHaveLength(1);
                expect(chargeOfCell(gridRow(FEE.id))).toBe(buyRowId());
            });

            it('a parent absent from the Bulk, held by the store: added as a saved row, its charge adopted and shown; the Form moves to it; no server read', async () => {
                txStoreSetAll([BUY_S, FEE_S, DEP], []);
                answerReads([FEE_S]);
                mountEditor({action: 'edit', txIds: [FEE_S.id, DEP.id]});
                await waitFor(() => expect(rowsOf(FEE_S.id), 'premise: the FEE is on screen').toHaveLength(1));
                expect(rowsOf(BUY_S.id), 'premise: its BUY is not in the Bulk').toHaveLength(0);
                await openRowForm(FEE_S.id);

                await openFromForm(BUY_S.id);

                await formOn(BUY_S.id);
                expect(formProbe().highlightTxId, 'the row the user came from').toBe(FEE_S.id);
                expect(rowsOf(BUY_S.id), 'the BUY is a row of the Bulk').toHaveLength(1);
                expect(rowStatus(gridRow(BUY_S.id)), 'a saved row, unchanged').toBe('original');
                expect(chargeOfCell(gridRow(FEE_S.id)), 'the FEE sits under it: the user brought it, the group is open').toBe(rowIdOf(gridRow(BUY_S.id)));
                expect(readById(BUY_S.id), 'the store had it: nothing read by id').toBe(false);
            });

            it('a parent the store does not hold: read from the server by id, added to the store and to the Bulk, then opened', async () => {
                txStoreSetAll([FEE_S, DEP], []);
                answerReads([FEE_S], [BUY_S]);
                mountEditor({action: 'edit', txIds: [FEE_S.id, DEP.id]});
                await waitFor(() => expect(rowsOf(FEE_S.id)).toHaveLength(1));
                await openRowForm(FEE_S.id);

                await openFromForm(BUY_S.id);

                expect(readById(BUY_S.id), 'read from the server by id').toBe(true);
                await formOn(BUY_S.id);
                expect(txStoreGet(BUY_S.id)?.id, 'the row read is in the store').toBe(BUY_S.id);
                expect(rowsOf(BUY_S.id), 'the BUY is a row of the Bulk').toHaveLength(1);
                expect(chargeOfCell(gridRow(FEE_S.id))).toBe(rowIdOf(gridRow(BUY_S.id)));
            });

            it('a target marked «del»: the «restore and edit» confirmation first (the double-click entry); confirmed, the Form moves to it restored', async () => {
                await openLoaded();
                await openBuyForm(2);
                await push(buyPayload({_charges: handedDrafts().map((draft): ChargeDraft => (draft.id === FEE.id ? {...draft, state: 'delete'} : draft))}));
                await openBuyForm(2);

                await openFromForm(FEE.id);

                const message = await screen.findByTestId('confirm-modal-message');
                expect(message, 'the «restore and edit» question').toHaveTextContent(get(_)('transactions.bulk.confirmEditDeleteMessage'));
                expect(formRow()?.id, 'the Form has not moved yet').toBe(BUY.id);
                await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
                await settle();
                await formOn(FEE.id);
                expect(rowsOf(FEE.id), 'the FEE is on screen').toHaveLength(1);
                expect(chargeState(gridRow(FEE.id)), 'restored').toBe('linked');
            });

            it('a failed read: an error notification tx.form.open.failed, and nothing changes', async () => {
                txStoreSetAll([FEE_S, DEP], []);
                answerReads([FEE_S], 'fail');
                mountEditor({action: 'edit', txIds: [FEE_S.id, DEP.id]});
                await waitFor(() => expect(rowsOf(FEE_S.id)).toHaveLength(1));
                await openRowForm(FEE_S.id);
                const toasts = await toastsMock();
                toasts.show.mockClear();
                const since = eventSeq();

                await openFromForm(BUY_S.id);

                await waitFor(() => expect(readById(BUY_S.id), 'premise: the read by id was made').toBe(true));
                await settle();
                expect(eventsSince(since, 'tx.form.open.failed'), 'one tx.form.open.failed event').toHaveLength(1);
                expect(
                    toasts.show.mock.calls.filter((call) => call[0] === 'error'),
                    'an error toast',
                ).toHaveLength(1);
                expect(formRow()?.id, 'the Form stays on the FEE').toBe(FEE_S.id);
                expect(rowsOf(BUY_S.id), 'no row added').toHaveLength(0);
            });

            it('a late answer after the Form moved to another row: nothing happens', async () => {
                txStoreSetAll([FEE_S, DEP], []);
                answerReads([FEE_S], 'hold');
                mountEditor({action: 'edit', txIds: [FEE_S.id, DEP.id]});
                await waitFor(() => expect(rowsOf(FEE_S.id)).toHaveLength(1));
                await openRowForm(FEE_S.id);
                await openFromForm(BUY_S.id);
                await waitFor(() => expect(heldById.length, 'premise: the read by id is in flight').toBe(1));
                (formProbe().onClose as () => void)();
                flushSync();
                await settle();
                await openRowForm(DEP.id);

                heldById[0].resolve([BUY_S]);
                await settle();

                expect(formRow()?.id, 'the Form stays on the DEPOSIT').toBe(DEP.id);
                expect(rowsOf(BUY_S.id), 'no row added').toHaveLength(0);
            });

            it('a late answer after the Bulk closed: nothing happens', async () => {
                txStoreSetAll([FEE_S, DEP], []);
                answerReads([FEE_S], 'hold');
                const {rerender, onClose} = mountEditor({action: 'edit', txIds: [FEE_S.id, DEP.id]});
                await waitFor(() => expect(rowsOf(FEE_S.id)).toHaveLength(1));
                await openRowForm(FEE_S.id);
                await openFromForm(BUY_S.id);
                await waitFor(() => expect(heldById.length, 'premise: the read by id is in flight').toBe(1));
                await rerender({open: false, intent: {action: 'edit', txIds: [FEE_S.id, DEP.id]}, onClose});
                await settle();
                const since = eventSeq();

                heldById[0].resolve([BUY_S]);
                await settle();

                expect(formProbe().open, 'no Form opens for a closed Bulk').toBe(false);
                expect(eventsSince(since, 'tx.form.open.failed'), 'and no error').toHaveLength(0);
            });

            // §22.4: a row «Open» brings in is navigation, not a change: it joins the close guard's baseline.
            it('a row brought by «Open», looked at and closed: closing the Bulk asks nothing', async () => {
                txStoreSetAll([BUY_S, FEE_S, DEP], []);
                answerReads([FEE_S]);
                const {onClose} = mountEditor({action: 'edit', txIds: [FEE_S.id, DEP.id]});
                await waitFor(() => expect(rowsOf(FEE_S.id)).toHaveLength(1));
                await openRowForm(FEE_S.id);
                await openFromForm(BUY_S.id);
                await formOn(BUY_S.id);
                expect(rowsOf(BUY_S.id), 'premise: the BUY joined the Bulk').toHaveLength(1);
                (formProbe().onClose as () => void)();
                flushSync();
                await settle();

                await closeEditor();

                expect(screen.queryByTestId('confirm-modal-confirm'), 'no «Discard changes?»').toBeNull();
                expect(onClose, 'the Bulk closes at once').toHaveBeenCalledTimes(1);
            });

            it('a row brought by «Open» and then edited: closing the Bulk asks', async () => {
                txStoreSetAll([BUY_S, FEE_S, DEP], []);
                answerReads([FEE_S]);
                const {onClose} = mountEditor({action: 'edit', txIds: [FEE_S.id, DEP.id]});
                await waitFor(() => expect(rowsOf(FEE_S.id)).toHaveLength(1));
                await openRowForm(FEE_S.id);
                await openFromForm(BUY_S.id);
                await formOn(BUY_S.id);
                await push(buyPayload({description: 'F7d parent edited', _charges: handedDrafts()}));
                expect(rowStatus(gridRow(BUY_S.id)), 'premise: the BUY is edited').toBe('edited');

                await closeEditor();

                expect(screen.queryByTestId('confirm-modal-confirm'), '«Discard changes?»').not.toBeNull();
                expect(onClose).not.toHaveBeenCalled();
            });
        });

        // -------------------------------------------------------------------
        // 66 TL-11 — moving between a new parent and its charges, and unlinking them, from the two Forms
        // -------------------------------------------------------------------

        /**
         * The Bulk hands its Form what it needs to show a NEW parent: on the charge's item, `_newParent: {key:
         * 'op-<tempId>', ref, row}` (`isUnderParent`, no `parentUnlink`); never with a saved parent, which keeps
         * `parent_transaction_id`. It also hands `onOpenRow(tempId)` («Open» on a row with no id): the row's own Form, its
         * group opened, the row the user came from in `highlightKey`. The outcome of «Unlink» + «Apply» already exists
         * (`applyChargeDrafts`, `unlinkCharge`): those cases are guards.
         */
        describe('66 TL-11: a new parent and its charges — the hand-over, onOpenRow, «Unlink»', () => {
            type NewParentRow = FormRow & {_newParent?: {key: string; ref: string; row: TXReadItem} | null};

            const NEW_BUY = 'TL11 new buy';
            const NEW_FEE = 'TL11 new fee';

            const tempIdOf = (description: string) => rowIdOf(gridRowDescribed(description));
            const newParentOf = () => (formRow() as NewParentRow | undefined)?._newParent ?? null;

            /** The name a text gives a new row: its label in the grid through the app's own phrase (`txRowRef`). */
            function refOf(row: HTMLElement): string {
                const label = (row.querySelector('[data-testid="tx-bulk-row-label"]')?.textContent ?? '').trim();
                expect(label, 'premise: the row has a label').not.toBe('');
                return get(_)('transactions.bulk.rowRef', {values: {n: label}});
            }

            /** The Form is open on the Bulk's row `tempId`, opened after `keyBefore`. */
            async function formOnRow(tempId: string): Promise<void> {
                await waitFor(() => {
                    expect(formProbe().open, 'the Form is open').toBe(true);
                    expect(formProbe().editingTempId, 'on the row asked for').toBe(tempId);
                });
            }

            async function editRow(row: HTMLElement): Promise<void> {
                const tempId = rowIdOf(row);
                await rowAction(row, 'edit-single');
                await formOnRow(tempId);
            }

            /** «Open» on a row with no id: the probe's `onOpenRow`, which TBM must hand its Form. */
            async function openRowFromForm(tempId: string): Promise<void> {
                const onOpenRow = formProbe().onOpenRow;
                expect(onOpenRow, '66 TL-11: TBM hands its nested Form no onOpenRow').toBeTypeOf('function');
                (onOpenRow as (tempId: string) => void)(tempId);
                flushSync();
                await settle();
            }

            async function closeForm(): Promise<void> {
                (formProbe().onClose as () => void)();
                flushSync();
                await settle();
                expect(formProbe().open).toBe(false);
            }

            /** The Form's item pushed back as it is (the Form's «Apply» with nothing typed), `over` applied. */
            function shown(over: Record<string, unknown> = {}): Record<string, unknown> {
                const item = formRow()!;
                return {
                    broker_id: item.broker_id,
                    type: item.type,
                    date: item.date,
                    quantity: item.quantity,
                    asset_id: item.asset_id,
                    cash: item.cash ? {code: item.cash.code, amount: `-${String(item.cash.amount).replace('-', '')}`} : null,
                    tags: item.tags ?? [],
                    description: item.description ?? '',
                    ...over,
                };
            }

            /** The editor on two saved rows (no Form opens by itself), the saved FREE fee in its store. */
            async function openEditor(txIds: number[] = [DEP.id, BUY_L.id]): Promise<void> {
                txStoreSetAll([DEP, BUY_L, FREE], []);
                answerReads([]);
                mountEditor({action: 'edit', txIds});
                await waitFor(() => expect(rowsOf(DEP.id), 'premise: the rows are on screen').toHaveLength(1));
            }

            /** A new BUY with a new FEE born in its Form; the group is open. */
            async function newBuyWithNewFee(): Promise<void> {
                await openEditor();
                await addRow(buyPayload({description: NEW_BUY, _charges: [newDraft('FEE', '2', NEW_FEE)]}));
                expect(chargeOfCell(gridRowDescribed(NEW_FEE)), 'premise: the new FEE sits under the new BUY').toBe(tempIdOf(NEW_BUY));
            }

            /** A new BUY with the SAVED free fee linked under it in its Form. */
            async function newBuyWithSavedFee(): Promise<void> {
                await openEditor([DEP.id, FREE.id]);
                const original: NonNullable<ChargeDraft['original']> = {type: 'FEE', cash: {amount: '1.500000', code: 'EUR'}, description: FREE.description ?? ''};
                const picked: ChargeDraft = {key: `saved-${FREE.id}`, id: FREE.id, type: 'FEE', cash: original.cash, description: original.description, original, state: 'linked', linkNew: true};
                await addRow(buyPayload({description: NEW_BUY, _charges: [picked]}));
                expect(chargeOfCell(gridRow(FREE.id)), 'premise: the saved FEE sits under the new BUY').toBe(tempIdOf(NEW_BUY));
            }

            /** The `_newParent` of the Form open now is the new BUY. */
            function expectNewBuyHanded(): void {
                const handed = newParentOf();
                expect(handed, '66 TL-11: the Form of a charge under a new parent is handed no _newParent').not.toBeNull();
                expect(handed!.key).toBe(`op-${tempIdOf(NEW_BUY)}`);
                expect(handed!.ref, 'named as every text of the Bulk names it').toBe(refOf(gridRowDescribed(NEW_BUY)));
                expect(handed!.row, 'the parent as the Bulk holds it').toMatchObject({type: 'BUY', date: BUY.date, broker_id: BUY.broker_id, asset_id: BUY.asset_id, description: NEW_BUY});
                expect(handed!.row.cash?.code).toBe('EUR');
                expect(Number(handed!.row.cash?.amount), 'signed, as the panels show it').toBe(-10);
            }

            // --- the hand-over, cell by cell ---

            it('new charge / new parent: _newParent names the BUY by its key and its row reference, with its row', async () => {
                await newBuyWithNewFee();

                await editRow(gridRowDescribed(NEW_FEE));

                expectNewBuyHanded();
                expect(formRow()?.parent_transaction_id ?? null, 'a new parent has no id').toBeNull();
            });

            it('saved charge linked here / new parent: the same _newParent, the charge keeps its own id', async () => {
                await newBuyWithSavedFee();

                await editRow(gridRow(FREE.id));

                expect(formRow()?.id).toBe(FREE.id);
                expectNewBuyHanded();
                expect(formRow()?.parent_transaction_id ?? null).toBeNull();
            });

            it('the row handed is the BUY as it is now: its Form changed, then the FEE’s opened', async () => {
                await newBuyWithNewFee();
                await editRow(gridRowDescribed(NEW_BUY));
                await push(buyPayload({description: NEW_BUY, date: '2026-09-18', cash: {code: 'EUR', amount: '-12.000000'}, _charges: handedDrafts()}));

                await editRow(gridRowDescribed(NEW_FEE));

                const handed = newParentOf();
                expect(handed, '66 TL-11: the Form of a charge under a new parent is handed no _newParent').not.toBeNull();
                expect(handed!.row.date).toBe('2026-09-18');
                expect(Number(handed!.row.cash?.amount)).toBe(-12);
            });

            it('guard: saved charge / saved parent: no _newParent, the saved parent’s id as today', async () => {
                await openLoaded();
                await openBuyForm(2);
                await openFromForm(FEE.id);
                await formOn(FEE.id);

                expect(newParentOf()).toBeNull();
                expect(formRow()?.parent_transaction_id).toBe(BUY.id);
            });

            it('guard: new charge / saved parent: no _newParent, the saved parent’s id', async () => {
                await openLoaded();
                await openBuyForm(2);
                await push(buyPayload({_charges: [...handedDrafts(), newDraft('FEE', '2', NEW_FEE)]}));

                await editRow(gridRowDescribed(NEW_FEE));

                expect(newParentOf()).toBeNull();
                expect(formRow()?.parent_transaction_id).toBe(BUY.id);
            });

            it('guard: an unlinked charge has no _newParent — a new one, and a saved one unlinked from a saved parent', async () => {
                await newBuyWithNewFee();
                await editRow(gridRowDescribed(NEW_BUY));
                await push(buyPayload({description: NEW_BUY, _charges: handedDrafts().map((draft): ChargeDraft => ({...draft, state: 'unlink'}))}));
                expect(chargeOfCell(gridRowDescribed(NEW_FEE)), 'premise: top level').toBeNull();

                await editRow(gridRowDescribed(NEW_FEE));
                expect(newParentOf()).toBeNull();
                cleanup();

                await openLoaded();
                await openBuyForm(2);
                await push(buyPayload({_charges: handedDrafts().map((draft): ChargeDraft => (draft.id === FEE.id ? {...draft, state: 'unlink'} : draft))}));
                await editRow(gridRow(FEE.id));
                expect(newParentOf()).toBeNull();
                expect(formRow()?.parent_transaction_id ?? null).toBeNull();
            });

            // --- onOpenRow ---

            it('onOpenRow from the new FEE: the Form moves to the new BUY, the FEE in highlightKey; closed and opened from the menu, nothing is highlighted', async () => {
                await newBuyWithNewFee();
                const [buyId, feeId] = [tempIdOf(NEW_BUY), tempIdOf(NEW_FEE)];
                await editRow(gridRowDescribed(NEW_FEE));
                const keyBefore = formProbe().openKey as number;

                await openRowFromForm(buyId);

                await formOnRow(buyId);
                expect(formProbe().openKey as number, 'the Form reads its items again').toBeGreaterThan(keyBefore);
                expect(formRow()?.type).toBe('BUY');
                expect(
                    handedDrafts().map((draft) => draft.key),
                    'the BUY’s charges are handed, the FEE among them',
                ).toEqual([`op-${feeId}`]);
                expect(formProbe().highlightKey, 'the row the user came from').toBe(`op-${feeId}`);
                expect(formProbe().highlightTxId ?? null, 'it has no id').toBeNull();

                await closeForm();
                await editRow(gridRowDescribed(NEW_BUY));
                expect(formProbe().highlightKey ?? null, 'a Form opened from the grid highlights nothing').toBeNull();
            });

            it('onOpenRow from the new BUY on a charge of a closed group: the group opens, so the row is on screen; the Form moves to the FEE', async () => {
                await newBuyWithNewFee();
                const [buyId, feeId] = [tempIdOf(NEW_BUY), tempIdOf(NEW_FEE)];
                const chip = screen.getByTestId(`tx-bulk-charges-toggle-${buyId}`);
                await fireEvent.click(chip);
                await settle();
                expect(
                    gridRows().filter((row) => rowDescription(row) === NEW_FEE),
                    'premise: the group is closed',
                ).toHaveLength(0);
                await editRow(gridRowDescribed(NEW_BUY));

                await openRowFromForm(feeId);

                await formOnRow(feeId);
                expect(formRow()).toMatchObject({type: 'FEE', description: NEW_FEE});
                expect(chargeOfCell(gridRowDescribed(NEW_FEE)), 'the FEE is on screen under its BUY').toBe(buyId);
            });

            it('onOpenRow from a SAVED charge under a new BUY: the Form moves to the BUY, highlighting that charge', async () => {
                await newBuyWithSavedFee();
                const buyId = tempIdOf(NEW_BUY);
                await editRow(gridRow(FREE.id));

                await openRowFromForm(buyId);

                await formOnRow(buyId);
                expect(
                    handedDrafts().map((draft) => draft.key),
                    'the saved FEE is handed under the BUY',
                ).toEqual([`saved-${FREE.id}`]);
                // Either name marks that row in the section: by its id, as «Open» on a saved row does, or by its key.
                expect(formProbe().highlightTxId === FREE.id || formProbe().highlightKey === `saved-${FREE.id}`, `the row the user came from — highlightTxId ${String(formProbe().highlightTxId)}, highlightKey ${String(formProbe().highlightKey)}`).toBe(true);
            });

            // Lane, after the final review: the cell «new charge / saved parent» goes through «Open» by id.
            for (const deleted of [false, true]) {
                it(`«Open» by id from a NEW charge under a saved BUY${deleted ? ' marked «del» (through «restore and edit»)' : ''}: the BUY’s Form highlights it by its key`, async () => {
                    await openLoaded();
                    await openBuyForm(2);
                    await push(buyPayload({_charges: [...handedDrafts(), newDraft('FEE', '2', NEW_FEE)]}));
                    const feeId = tempIdOf(NEW_FEE);
                    await editRow(gridRowDescribed(NEW_FEE));
                    if (deleted) {
                        await rowAction(gridRow(BUY.id), 'mark-delete');
                        await fireEvent.click(within(await screen.findByTestId('tx-charges-modal-content')).getByTestId('tx-charges-modal-keep'));
                        await settle();
                        expect(rowStatus(gridRow(BUY.id)), 'premise: the BUY is «del»').toBe('delete');
                    }

                    await openFromForm(BUY.id);
                    if (deleted) {
                        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));
                        await settle();
                    }

                    await formOn(BUY.id);
                    expect(formProbe().highlightKey, 'the row the user came from').toBe(`op-${feeId}`);
                    expect(formProbe().highlightTxId ?? null).toBeNull();
                });
            }

            it('onOpenRow on a row that is not there: nothing happens, the Form stays', async () => {
                await newBuyWithNewFee();
                const feeId = tempIdOf(NEW_FEE);
                await editRow(gridRowDescribed(NEW_FEE));

                await openRowFromForm('tl11-no-such-row');

                await formOnRow(feeId);
            });

            // --- «Unlink» + «Apply» (guards: `unlinkCharge` and `applyChargeDrafts` already do it) ---

            it('guard: _parent_unlink on a new charge that followed its new BUY: a row of its own with the broker, asset and date it showed, sent with no parent', async () => {
                await newBuyWithNewFee();
                // The BUY moves to another day after the FEE was born: what the FEE shows is the new day.
                await editRow(gridRowDescribed(NEW_BUY));
                await push(buyPayload({description: NEW_BUY, date: '2026-09-18', _charges: handedDrafts()}));
                await editRow(gridRowDescribed(NEW_FEE));
                expect(formRow(), 'premise: the FEE shows the BUY’s broker, asset and date').toMatchObject({broker_id: BUY.broker_id, asset_id: BUY.asset_id, date: '2026-09-18'});

                await push(shown({_parent_unlink: true}));

                expect(chargeOfCell(gridRowDescribed(NEW_FEE)), 'top level').toBeNull();
                expect(rowStatus(gridRowDescribed(NEW_FEE))).toBe('new');
                const body = await saveAll();
                const fee = onlyCreateOf(body, 'FEE');
                expect(fee).toMatchObject({broker_id: BUY.broker_id, asset_id: BUY.asset_id, date: '2026-09-18', description: NEW_FEE});
                expect(fee).not.toHaveProperty('parent_ref');
                expect(fee).not.toHaveProperty('parent_transaction_id');
                onlyCreateOf(body, 'BUY');
            });

            it('guard: an op- draft unlinked in the new BUY’s Form: the FEE is a row of its own, sent with no parent; it no longer follows the BUY', async () => {
                await newBuyWithNewFee();
                await editRow(gridRowDescribed(NEW_BUY));
                await push(buyPayload({description: NEW_BUY, _charges: handedDrafts().map((draft): ChargeDraft => ({...draft, state: 'unlink'}))}));
                expect(chargeOfCell(gridRowDescribed(NEW_FEE)), 'top level').toBeNull();
                // The BUY moved afterwards: the FEE stays on the day it showed.
                await editRow(gridRowDescribed(NEW_BUY));
                expect(handedDrafts(), 'the BUY has no charge any more').toEqual([]);
                await push(buyPayload({description: NEW_BUY, date: '2026-09-18', _charges: []}));

                const body = await saveAll();
                const fee = onlyCreateOf(body, 'FEE');
                expect(fee).toMatchObject({broker_id: BUY.broker_id, asset_id: BUY.asset_id, date: BUY.date, description: NEW_FEE});
                expect(fee).not.toHaveProperty('parent_ref');
                expect(fee).not.toHaveProperty('parent_transaction_id');
                expect(onlyCreateOf(body, 'BUY')).toMatchObject({date: '2026-09-18'});
            });

            it('guard: _parent_unlink on a SAVED charge linked only here: free again, nothing sent about it', async () => {
                await newBuyWithSavedFee();
                await editRow(gridRow(FREE.id));

                await push(shown({_parent_unlink: true}));

                expect(chargeOfCell(gridRow(FREE.id)), 'top level').toBeNull();
                expect(chargeState(gridRow(FREE.id)), 'no badge: there was no saved link to cut').toBeNull();
                expect(rowStatus(gridRow(FREE.id)), 'back as saved').toBe('original');
                const body = await saveAll();
                onlyCreateOf(body, 'BUY');
                expect(updatesOf(body, FREE.id), 'the saved FEE sends nothing').toEqual([]);
            });

            // --- 66 TL-12: what the Form hands back after its window («unlink the saved ones») is confirmed. The window is
            // the Form's (TransactionFormModal.savedLinks.test.ts); the Bulk's half already exists: guards. ---

            /** A saved FREE, as the Form picks it. */
            function pickedFree(): ChargeDraft {
                const original: NonNullable<ChargeDraft['original']> = {type: 'FEE', cash: {amount: '1.500000', code: 'EUR'}, description: FREE.description ?? ''};
                return {key: `saved-${FREE.id}`, id: FREE.id, type: 'FEE', cash: original.cash, description: original.description, original, state: 'linked', linkNew: true};
            }

            /** FREE is as saved: top level, untouched, and the batch says nothing about it. */
            function expectFreeUntouched(): void {
                expect(chargeOfCell(gridRow(FREE.id)), 'top level').toBeNull();
                expect(chargeState(gridRow(FREE.id)), 'no badge: there was no saved link to cut').toBeNull();
                expect(rowStatus(gridRow(FREE.id)), 'back as saved').toBe('original');
            }

            for (const [field, value] of [
                ['asset_id', 102],
                ['broker_id', 88],
            ] as const) {
                for (const sibling of ['born in the BUY’s Form (it follows it)', 'a row of the Bulk linked there'] as const) {
                    it(`66 TL-12 guard: a new ${field} without the saved FEE’s draft: the FEE is free, nothing sent for it; the new sibling, ${sibling}, takes it`, async () => {
                        mergeBrokers([{id: 88, name: 'TL12 other broker', user_role: 'OWNER'}]);
                        await openEditor([DEP.id, FREE.id]);
                        if (sibling === 'born in the BUY’s Form (it follows it)') {
                            await addRow(buyPayload({description: NEW_BUY, _charges: [pickedFree(), newDraft('FEE', '2', NEW_FEE)]}));
                        } else {
                            await addRow(chargePayload('FEE', NEW_FEE, {date: BUY.date}));
                            const op: ChargeDraft = {...newDraft('FEE', '2', NEW_FEE), key: `op-${tempIdOf(NEW_FEE)}`};
                            await addRow(buyPayload({description: NEW_BUY, _charges: [pickedFree(), op]}));
                        }
                        const buyId = tempIdOf(NEW_BUY);
                        expect([chargeOfCell(gridRow(FREE.id)), chargeOfCell(gridRowDescribed(NEW_FEE))], 'premise: a mixed group').toEqual([buyId, buyId]);
                        await editRow(gridRowDescribed(NEW_BUY));

                        await push(buyPayload({description: NEW_BUY, [field]: value, _charges: handedDrafts().filter((draft) => draft.id === null)}));

                        expectFreeUntouched();
                        expect(chargeOfCell(gridRowDescribed(NEW_FEE)), 'the new sibling is still under the BUY').toBe(buyId);
                        const body = await saveAll();
                        const buy = onlyCreateOf(body, 'BUY');
                        const fee = onlyCreateOf(body, 'FEE');
                        expect(buy).toMatchObject({[field]: value});
                        expect(fee, 'it took the change').toMatchObject({[field]: value, description: NEW_FEE});
                        expect(fee.parent_ref, 'sent under the BUY').toBe(buy.ref);
                        expect(updatesOf(body, FREE.id), 'the saved FEE sends nothing').toEqual([]);
                        expect((body.deletes ?? []) as unknown[], 'nor is it deleted').not.toContain(FREE.id);
                    });
                }
            }

            for (const born of ['in the saved BUY’s Form (it follows it)', 'a row of its own, linked to it'] as const) {
                it(`66 TL-12 guard: cell 3, a new FEE ${born}: _parent_unlink with a new asset leaves it a row of its own ON THAT asset, sent with no parent`, async () => {
                    await openEditor([DEP.id, BUY_L.id]);
                    if (born === 'in the saved BUY’s Form (it follows it)') {
                        await openRowForm(BUY_L.id);
                        await push(buyPayload({description: BUY_L.description, _charges: [newDraft('FEE', '2', NEW_FEE)]}));
                    } else {
                        await addRow(chargePayload('FEE', NEW_FEE, {date: BUY.date, _parent_link: BUY_L.id}));
                    }
                    expect(chargeOfCell(gridRowDescribed(NEW_FEE)), 'premise: under the saved BUY').toBe(rowIdOf(gridRow(BUY_L.id)));
                    await editRow(gridRowDescribed(NEW_FEE));
                    expect(formRow()?.parent_transaction_id, 'premise: the Form is handed its saved parent').toBe(BUY_L.id);

                    await push(shown({asset_id: 102, _parent_unlink: true}));

                    expect(chargeOfCell(gridRowDescribed(NEW_FEE)), 'top level').toBeNull();
                    const fee = onlyCreateOf(await saveAll(), 'FEE');
                    expect(fee, 'the asset the user chose, not the parent’s').toMatchObject({asset_id: 102, broker_id: BUY.broker_id, description: NEW_FEE});
                    expect(fee).not.toHaveProperty('parent_ref');
                    expect(fee).not.toHaveProperty('parent_transaction_id');
                });
            }

            // Lane, after the code (no red). The Form's Confirm on a change of type sends `_parent_unlink` with the new type.
            it('66 TL-12 guard: a new FEE under a saved BUY turned into a DEPOSIT, with _parent_unlink: a row of its own, sent with no parent', async () => {
                await openEditor([DEP.id, BUY_L.id]);
                await openRowForm(BUY_L.id);
                await push(buyPayload({description: BUY_L.description, _charges: [newDraft('FEE', '2', NEW_FEE)]}));
                await editRow(gridRowDescribed(NEW_FEE));

                await push(shown({type: 'DEPOSIT', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '2.000000'}, _parent_unlink: true}));

                expect(chargeOfCell(gridRowDescribed(NEW_FEE)), 'top level').toBeNull();
                const deposits = ((await saveAll()).creates ?? []).filter((create) => create.type === 'DEPOSIT' && create.description === NEW_FEE);
                expect(deposits).toHaveLength(1);
                expect(deposits[0]).not.toHaveProperty('parent_ref');
                expect(deposits[0]).not.toHaveProperty('parent_transaction_id');
            });

            // Outside D-26's words (the lane's note): a type change that ends the charge role but keeps the asset asks
            // nothing; the Bulk still names the parent, and the backend answers chargeNotACharge, a flag, never a silent unlink.
            it('66 TL-12 guard: a new FEE with no asset under a saved DEPOSIT, turned into a DEPOSIT without unlinking: still sent with its parent', async () => {
                await openEditor([DEP.id, BUY_L.id]);
                await openRowForm(DEP.id);
                await push(shown({_charges: [newDraft('FEE', '2', NEW_FEE)]}));
                await editRow(gridRowDescribed(NEW_FEE));

                await push(shown({type: 'DEPOSIT', quantity: '0', cash: {code: 'EUR', amount: '2.000000'}}));

                const deposits = ((await validateNow()).creates ?? []).filter((create) => create.type === 'DEPOSIT' && create.description === NEW_FEE);
                expect(deposits).toHaveLength(1);
                expect(deposits[0].parent_transaction_id, 'the parent is still named: the backend flags it').toBe(DEP.id);
            });
        });

        // -------------------------------------------------------------------
        // §20.5 + §21.2 + §22.1 — U3, «Link» in the toolbar
        // -------------------------------------------------------------------

        describe('§20.5: «Link» in the Bulk toolbar (U3)', () => {
            function linkButton(): HTMLElement | null {
                return screen.queryByTestId('tx-bulk-link-charges');
            }

            /** «Link», on; click; ends on the panel open in link mode. */
            async function openLinkPanel(): Promise<HTMLElement> {
                const button = linkButton();
                expect(button, 'the selection offers «Link» (tx-bulk-link-charges)').not.toBeNull();
                expect(button, '«Link» is on').not.toHaveAttribute('aria-disabled', 'true');
                await fireEvent.click(button!);
                await settle();
                const content = await screen.findByTestId(PANEL);
                expect(content).toHaveAttribute('data-mode', 'link');
                return content;
            }

            /** The panel's confirm; ends on the panel gone. */
            async function confirmLink(content: HTMLElement): Promise<void> {
                await fireEvent.click(within(content).getByTestId('tx-charges-modal-confirm'));
                await settle();
                await waitFor(() => expect(screen.queryByTestId(PANEL), 'the panel closed').toBeNull());
            }

            /** Select the rows, «Link», confirm; ends on the selection empty. */
            async function link(rows: HTMLElement[]): Promise<void> {
                for (const row of rows) await tickRow(row);
                await confirmLink(await openLinkPanel());
                expect(screen.queryByTestId('tx-bulk-delete-selected'), 'the selection is empty').toBeNull();
            }

            it('a parent and a free charge selected: «Link» is in the toolbar, on; a parent and a DEPOSIT: no «Link»', async () => {
                txStoreSetAll([BUY_L, FREE, DEP], []);
                answerReads([]);
                mountEditor({action: 'edit', txIds: [BUY_L.id, FREE.id, DEP.id]});
                await waitFor(() => expect(rowsOf(DEP.id)).toHaveLength(1));

                await tickRow(gridRow(BUY_L.id));
                await tickRow(gridRow(DEP.id));
                expect(linkButton(), 'no charge selected: no «Link»').toBeNull();
                await fireEvent.click(rowCheckbox(gridRow(DEP.id))!);
                await settle();
                await tickRow(gridRow(FREE.id));

                expect(linkButton(), '«Link» is offered').not.toBeNull();
                expect(linkButton()).not.toHaveAttribute('aria-disabled', 'true');
            });

            it('a parent «del» in the selection: «Link» off, aria-disabled, data-reason deleted; a click opens no panel', async () => {
                txStoreSetAll([BUY_L, FREE], []);
                answerReads([]);
                mountEditor({action: 'edit', txIds: [BUY_L.id, FREE.id]});
                await waitFor(() => expect(rowsOf(FREE.id)).toHaveLength(1));
                await rowAction(gridRow(BUY_L.id), 'mark-delete');
                expect(rowStatus(gridRow(BUY_L.id)), 'premise').toBe('delete');
                await tickRow(gridRow(BUY_L.id));
                await tickRow(gridRow(FREE.id));

                const button = linkButton();
                expect(button, '«Link» is there, off').not.toBeNull();
                expect(button).toHaveAttribute('aria-disabled', 'true');
                expect(button).toHaveAttribute('data-disabled-reason', 'deleted');
                await fireEvent.click(button!);
                await settle();
                expect(screen.queryByTestId(PANEL), 'off: no panel').toBeNull();
            });

            it('two parents and a charge: «Link» off, data-reason twoParents', async () => {
                txStoreSetAll([BUY_L, BUY_L2, FREE], []);
                answerReads([]);
                mountEditor({action: 'edit', txIds: [BUY_L.id, BUY_L2.id, FREE.id]});
                await waitFor(() => expect(rowsOf(FREE.id)).toHaveLength(1));
                for (const id of [BUY_L.id, BUY_L2.id, FREE.id]) await tickRow(gridRow(id));

                expect(linkButton(), '«Link» is there, off').not.toBeNull();
                expect(linkButton()).toHaveAttribute('aria-disabled', 'true');
                expect(linkButton()).toHaveAttribute('data-disabled-reason', 'twoParents');
            });

            it('new BUY + new FEE: confirm puts the FEE under the BUY, the group open; «Save all» sends the FEE with parent_ref = the BUY’s ref', async () => {
                mountEditor({action: 'create'});
                await waitFor(() => expect(formProbe().open, 'a create intent opens the Form').toBe(true));
                await push(buyPayload({description: 'F7d new buy'}));
                await addRow(chargePayload('FEE', 'F7d new fee'));
                expect(chargeOfCell(gridRowDescribed('F7d new fee')), 'premise: the FEE is a top-level row').toBeNull();

                await link([gridRowDescribed('F7d new buy'), gridRowDescribed('F7d new fee')]);

                expect(chargeOfCell(gridRowDescribed('F7d new fee')), 'the FEE sits under the BUY, the group open').toBe(rowIdOf(gridRowDescribed('F7d new buy')));
                const body = await saveAll();
                const buy = onlyCreateOf(body, 'BUY');
                const fee = onlyCreateOf(body, 'FEE');
                expect(typeof buy.ref, 'the new BUY carries a ref').toBe('string');
                expect(fee.parent_ref).toBe(buy.ref);
                expect(fee).not.toHaveProperty('parent_transaction_id');
                expect(fee, 'linked here, it keeps its own values').toMatchObject({broker_id: 77, asset_id: 101, date: '2026-09-13'});
            });

            it('saved BUY + saved free FEE: one update of the FEE with parent_transaction_id = the BUY', async () => {
                txStoreSetAll([BUY_L, FREE], []);
                answerReads([]);
                mountEditor({action: 'edit', txIds: [BUY_L.id, FREE.id]});
                await waitFor(() => expect(rowsOf(FREE.id)).toHaveLength(1));

                await link([gridRow(BUY_L.id), gridRow(FREE.id)]);

                expect(chargeOfCell(gridRow(FREE.id))).toBe(rowIdOf(gridRow(BUY_L.id)));
                const body = await saveAll();
                const updates = updatesOf(body, FREE.id);
                expect(updates, 'one update of the FEE').toHaveLength(1);
                expect(updates[0]).toMatchObject({parent_transaction_id: BUY_L.id});
                expect(updates[0]).not.toHaveProperty('parent_ref');
                expect(updatesOf(body, BUY_L.id), 'the BUY sends nothing').toEqual([]);
            });

            it('saved BUY + new FEE: the FEE create names the BUY by parent_transaction_id', async () => {
                txStoreSetAll([BUY_L, DEP], []);
                answerReads([]);
                mountEditor({action: 'edit', txIds: [BUY_L.id, DEP.id]});
                await waitFor(() => expect(rowsOf(DEP.id)).toHaveLength(1));
                await addRow(chargePayload('FEE', 'F7d new fee'));

                await link([gridRow(BUY_L.id), gridRowDescribed('F7d new fee')]);

                const fee = onlyCreateOf(await saveAll(), 'FEE');
                expect(fee.parent_transaction_id).toBe(BUY_L.id);
                expect(fee).not.toHaveProperty('parent_ref');
            });

            it('new BUY + saved free FEE: the FEE update names the BUY by parent_ref', async () => {
                txStoreSetAll([FREE, DEP], []);
                answerReads([]);
                mountEditor({action: 'edit', txIds: [FREE.id, DEP.id]});
                await waitFor(() => expect(rowsOf(DEP.id)).toHaveLength(1));
                await addRow(buyPayload({description: 'F7d new buy'}));

                await link([gridRowDescribed('F7d new buy'), gridRow(FREE.id)]);

                const body = await saveAll();
                const buy = onlyCreateOf(body, 'BUY');
                const updates = updatesOf(body, FREE.id);
                expect(updates, 'one update of the FEE').toHaveLength(1);
                expect(updates[0].parent_ref).toBe(buy.ref);
                expect(updates[0]).not.toHaveProperty('parent_transaction_id');
            });

            it('a FEE unlinked from A in this Bulk, then linked to B: ONE update, parent_transaction_id = B', async () => {
                txStoreSetAll([PARENT_A, FEE_A, PARENT_B], []);
                answerReads([FEE_A]);
                mountEditor({action: 'edit', txIds: [PARENT_A.id, FEE_A.id, PARENT_B.id]});
                await waitFor(() => expect(rowsOf(PARENT_B.id)).toHaveLength(1));
                await rowAction(gridRow(PARENT_A.id), 'edit-single');
                await waitForParentForm(PARENT_A.id, 1);
                await push(buyPayload({description: PARENT_A.description, _charges: handedDrafts().map((draft): ChargeDraft => ({...draft, state: 'unlink'}))}));
                expect(chargeOfCell(gridRow(FEE_A.id)), 'premise: the FEE is a top-level row, unlinked from A').toBeNull();

                await link([gridRow(PARENT_B.id), gridRow(FEE_A.id)]);

                expect(chargeOfCell(gridRow(FEE_A.id)), 'the FEE sits under B').toBe(rowIdOf(gridRow(PARENT_B.id)));
                const body = await saveAll();
                const updates = updatesOf(body, FEE_A.id);
                expect(updates, 'one update of the FEE, A → B').toHaveLength(1);
                expect(updates[0]).toMatchObject({parent_transaction_id: PARENT_B.id});
            });

            // §22.1: a new row is named by its Bulk label, so two new charges are told apart in the panel's columns.
            it('the panel names two new charges apart: their column headers differ, and none says #0', async () => {
                mountEditor({action: 'create'});
                await waitFor(() => expect(formProbe().open).toBe(true));
                await push(buyPayload({description: 'F7d new buy'}));
                await addRow(chargePayload('FEE', 'F7d new fee'));
                await addRow(chargePayload('TAX', 'F7d new tax'));
                for (const description of ['F7d new buy', 'F7d new fee', 'F7d new tax']) await tickRow(gridRowDescribed(description));

                const content = await openLinkPanel();

                const table = within(content).getByTestId('tx-charges-modal-table');
                const headers = [...table.querySelectorAll<HTMLElement>('thead th[data-testid^="dt-header-"]')].filter((th) => th.getAttribute('data-testid') !== 'dt-header-field').map((th) => (th.textContent ?? '').trim());
                expect(headers, 'one column per row: the BUY and the two charges').toHaveLength(3);
                expect(new Set(headers).size, `the three columns are told apart: ${JSON.stringify(headers)}`).toBe(3);
                for (const header of headers) expect(header, 'no TX #0').not.toContain('#0');
            });
        });
    });

    /*
     * 66 P1b — the names of an import hand-over become the Bulk's links (contract `66-P1b-contract.md` §1.3, corrected by
     * §4.1 and §5). Within ONE hand-over (`onImportBatch`), a row carrying `ref` is a parent and a row naming it in
     * `parent_ref` its charge (`chargeOf`), but only when the Bulk's own rule accepts the pair: `bulkLinkSelection([parent,
     * …charges], ops, get, {roleOf, canEdit})` → `ok`; otherwise the charges stay free, as in P1a. No `followsParent`: an
     * imported charge keeps its values and stays when its parent leaves. The groups start CLOSED (§5: the consultant's
     * answer — 200 trades → 600 rows), the wizard's split legs included; a problem on a charge of a closed group is in
     * the banner, and its jump opens the group (the C14 rule). The save goes through F7: `parent_ref` = the parent's `ref`.
     *
     * Today the hand-over drops `ref` and `parent_ref` (`txCreateItemToPendingOp`), so every case that needs a link is
     * red; the cases about a link that must NOT form carry a positive premise in the same test (a pair of the same
     * hand-over that does link), so none of them is green for the wrong reason.
     *
     * Broker 77 is the user's own (`canEdit`, as F7-d's «Link»). New rows are found by the description the test gave
     * them; a parent's chip by the parent's `data-row-id`.
     */
    describe('66 P1b: an import hand-over brings its linked charges', () => {
        const P1B_DATE = '2026-09-13';
        type Handed = {tx: TransactionCreateItem; todos: unknown[]};

        beforeEach(() => {
            mergeBrokers([{id: 77, name: 'P1b broker', user_role: 'OWNER'}]);
        });

        afterEach(() => {
            resetBrokerStore();
        });

        function importedParent(description: string, ref: string | null, over: Record<string, unknown> = {}): Handed {
            const tx = {broker_id: 77, asset_id: 101, type: 'BUY', date: P1B_DATE, quantity: '1', cash: {code: 'EUR', amount: '-10'}, tags: [], description, ...(ref ? {ref} : {}), ...over};
            return {tx: tx as unknown as TransactionCreateItem, todos: []};
        }

        function importedCharge(type: 'FEE' | 'TAX', description: string, parentRef: string | null, over: Record<string, unknown> = {}): Handed {
            const tx = {broker_id: 77, asset_id: 101, type, date: P1B_DATE, quantity: '0', cash: {code: 'EUR', amount: '-1.5'}, tags: [], description, ...(parentRef ? {parent_ref: parentRef} : {}), ...over};
            return {tx: tx as unknown as TransactionCreateItem, todos: []};
        }

        /** A new editor on the import intent; ends on its wizard open. */
        async function openImportEditor(): Promise<ReturnType<typeof mountEditor>> {
            const mounted = mountEditor({action: 'import'});
            await waitFor(() => expect(wizardProbe().open, 'the import intent opens the wizard').toBe(true));
            return mounted;
        }

        /** One hand-over of the wizard; ends on its first row on screen (a parent, which is never indented). */
        async function handOver(batch: Handed[]): Promise<void> {
            await (wizardProbe().onImportBatch as (creates: Handed[]) => Promise<void>)(batch);
            await settle();
            const first = String(batch[0].tx.description);
            await waitFor(() =>
                expect(
                    gridRows().filter((row) => rowDescription(row) === first),
                    `premise: ${first} is on screen`,
                ).toHaveLength(1),
            );
        }

        function rowIdOf(row: HTMLElement): string {
            const id = row.getAttribute('data-row-id');
            if (!id) throw new Error('the row publishes no data-row-id');
            return id;
        }

        /** The chip of the parent described `description`, or null. */
        function chipOf(description: string): HTMLElement | null {
            return screen.queryByTestId(`tx-bulk-charges-toggle-${rowIdOf(gridRowDescribed(description))}`);
        }

        function theChipOf(description: string): HTMLElement {
            const found = chipOf(description);
            if (!found) throw new Error(`the row described ${JSON.stringify(description)} has no charges chip: no charge was linked to it`);
            return found;
        }

        /** The rows on screen described `description` (0 when a closed group hides it). */
        function rowsDescribed(description: string): HTMLElement[] {
            return gridRows().filter((row) => rowDescription(row) === description);
        }

        async function openGroup(description: string): Promise<void> {
            const chip = theChipOf(description);
            if (chip.getAttribute('aria-expanded') !== 'true') {
                await fireEvent.click(chip);
                await settle();
            }
            expect(theChipOf(description)).toHaveAttribute('aria-expanded', 'true');
        }

        async function saveAll(): Promise<Payload> {
            const {commitTransactions} = await api();
            const commit = screen.getByTestId('tx-bulk-commit');
            expect(commit, '«Save all» is on').not.toBeDisabled();
            await fireEvent.click(commit);
            await settle();
            await waitFor(() => expect(commitTransactions, 'Save all committed').toHaveBeenCalledTimes(1));
            return commitTransactions.mock.calls[0]?.[0] as Payload;
        }

        /** The one create of a body described `description`. */
        function createDescribed(body: Payload, description: string): Record<string, unknown> {
            const found = (body.creates ?? []).filter((create) => create.description === description);
            expect(found, `one create described ${JSON.stringify(description)}`).toHaveLength(1);
            return found[0];
        }

        /** A body's parent and charge, by description: the charge names the parent's `ref`, never by id. */
        function expectLinkedInBody(body: Payload, where: string, parent: string, charge: string): void {
            const parentCreate = createDescribed(body, parent);
            const chargeCreate = createDescribed(body, charge);
            expect(typeof parentCreate.ref, `${where}: ${parent} carries a ref`).toBe('string');
            expect((parentCreate.ref as string).length, `${where}: a ref within 36 characters`).toBeLessThanOrEqual(36);
            expect(chargeCreate.parent_ref, `${where}: ${charge} names ${parent} by its ref`).toBe(parentCreate.ref);
            expect(chargeCreate, `${where}: a new parent is named by ref, never by id`).not.toHaveProperty('parent_transaction_id');
        }

        it('an imported BUY and its FEE become parent and charge: the group starts closed, the chip counts 1, opening it shows the FEE under the BUY', async () => {
            await openImportEditor();
            await handOver([importedParent('P1b buy', 'r1'), importedCharge('FEE', 'P1b fee', 'r1')]);

            const chip = theChipOf('P1b buy');
            expect(chip).toHaveAttribute('data-charges-count', '1');
            expect(chip, 'closed: an import brings its charges closed (§5)').toHaveAttribute('aria-expanded', 'false');
            expect(rowsDescribed('P1b fee'), 'a closed group shows no FEE row').toHaveLength(0);

            await openGroup('P1b buy');

            expect(chargeOfCell(gridRowDescribed('P1b fee')), 'the FEE sits under the BUY').toBe(rowIdOf(gridRowDescribed('P1b buy')));
            expect(rowStatus(gridRowDescribed('P1b fee')), 'a new row').toBe('new');
        });

        it('the split legs of the wizard arrive as any imported charge: one closed group of two', async () => {
            await openImportEditor();
            const legs = {tags: ['split_leg']};
            await handOver([importedParent('P1b split trade', 'n-split'), importedCharge('FEE', 'P1b split fee', 'n-split', legs), importedCharge('TAX', 'P1b split tax', 'n-split', {...legs, cash: {code: 'EUR', amount: '-0.5'}})]);

            const chip = theChipOf('P1b split trade');
            expect(chip).toHaveAttribute('data-charges-count', '2');
            expect(chip).toHaveAttribute('aria-expanded', 'false');
            expect(rowsDescribed('P1b split fee')).toHaveLength(0);
            expect(rowsDescribed('P1b split tax')).toHaveLength(0);
        });

        it('«Validate now» and «Save all» send the FEE with parent_ref = the BUY’s ref', async () => {
            await openImportEditor();
            await handOver([importedParent('P1b buy', 'r1'), importedCharge('FEE', 'P1b fee', 'r1')]);

            expectLinkedInBody(await validateNow(), 'validate', 'P1b buy', 'P1b fee');
            expectLinkedInBody(await saveAll(), 'commit', 'P1b buy', 'P1b fee');
        });

        it('two hand-overs reusing r1 never cross; a third one’s lone FEE naming r1 joins neither', async () => {
            await openImportEditor();
            await handOver([importedParent('P1b buy A', 'r1'), importedCharge('FEE', 'P1b fee A', 'r1')]);
            await handOver([importedParent('P1b buy B', 'r1', {date: '2026-09-14'}), importedCharge('FEE', 'P1b fee B', 'r1', {date: '2026-09-14'})]);
            await handOver([importedCharge('FEE', 'P1b lone fee', 'r1', {date: '2026-09-15'})]);

            expect(theChipOf('P1b buy A'), 'A holds its own FEE only').toHaveAttribute('data-charges-count', '1');
            expect(theChipOf('P1b buy B'), 'B holds its own FEE only').toHaveAttribute('data-charges-count', '1');
            await openGroup('P1b buy A');
            await openGroup('P1b buy B');
            expect(chargeOfCell(gridRowDescribed('P1b fee A'))).toBe(rowIdOf(gridRowDescribed('P1b buy A')));
            expect(chargeOfCell(gridRowDescribed('P1b fee B'))).toBe(rowIdOf(gridRowDescribed('P1b buy B')));
            expect(chargeOfCell(gridRowDescribed('P1b lone fee')), 'the names hold for one hand-over: the lone FEE is free').toBeNull();

            const body = await validateNow();
            expectLinkedInBody(body, 'validate', 'P1b buy A', 'P1b fee A');
            expectLinkedInBody(body, 'validate', 'P1b buy B', 'P1b fee B');
            expect(createDescribed(body, 'P1b buy A').ref, 'two parents, two refs').not.toBe(createDescribed(body, 'P1b buy B').ref);
            expect(createDescribed(body, 'P1b lone fee'), 'the lone FEE names no parent').not.toHaveProperty('parent_ref');
            expect(createDescribed(body, 'P1b lone fee')).not.toHaveProperty('parent_transaction_id');
        });

        it('a pair the Bulk’s rule refuses stays free — a parent retyped ADJUSTMENT, a FEE on another asset — while a valid pair of the same hand-over links', async () => {
            await openImportEditor();
            await handOver([
                importedParent('P1b valid buy', 'r2'),
                importedCharge('FEE', 'P1b valid fee', 'r2'),
                importedParent('P1b adjustment', 'r1', {type: 'ADJUSTMENT', cash: null, date: '2026-09-14'}),
                importedCharge('FEE', 'P1b fee of the adjustment', 'r1', {date: '2026-09-14'}),
                importedParent('P1b other buy', 'r3', {date: '2026-09-15'}),
                importedCharge('FEE', 'P1b fee on another asset', 'r3', {date: '2026-09-15', asset_id: 202}),
            ]);

            // Positive premise, in the same hand-over: the rule does link a valid pair.
            expect(theChipOf('P1b valid buy'), 'premise: the valid pair links').toHaveAttribute('data-charges-count', '1');
            expect(chipOf('P1b adjustment'), 'an ADJUSTMENT is no parent: no chip').toBeNull();
            expect(chipOf('P1b other buy'), 'a FEE on another asset is not its charge: no chip').toBeNull();
            for (const free of ['P1b fee of the adjustment', 'P1b fee on another asset']) {
                expect(rowsDescribed(free), `${free}: a top-level row, on screen`).toHaveLength(1);
                expect(chargeOfCell(gridRowDescribed(free)), `${free}: free`).toBeNull();
            }

            const body = await validateNow();
            expectLinkedInBody(body, 'validate', 'P1b valid buy', 'P1b valid fee');
            for (const free of ['P1b fee of the adjustment', 'P1b fee on another asset']) {
                expect(createDescribed(body, free), `${free}: no parent_ref (the backend would refuse it)`).not.toHaveProperty('parent_ref');
                expect(createDescribed(body, free)).not.toHaveProperty('parent_transaction_id');
            }
            expect(createDescribed(body, 'P1b adjustment').ref ?? null, 'nothing names the ADJUSTMENT: no ref').toBeNull();
        });

        // Coordinator's decision (20/11): the imported link is judged charge by charge, as the backend judges it — one
        // invalid charge does not take the link away from the other charges of the same parent.
        it('charge by charge: a FEE on another asset stays free, and does not take the link away from its sibling on the BUY’s asset', async () => {
            await openImportEditor();
            await handOver([importedParent('P1b buy', 'r1'), importedCharge('FEE', 'P1b fee on the asset', 'r1'), importedCharge('FEE', 'P1b fee on another asset', 'r1', {asset_id: 202})]);

            expect(theChipOf('P1b buy'), 'the FEE on the BUY’s asset is linked: the chip counts it alone').toHaveAttribute('data-charges-count', '1');
            expect(rowsDescribed('P1b fee on another asset'), 'the FEE on another asset is a top-level row, on screen').toHaveLength(1);
            expect(chargeOfCell(gridRowDescribed('P1b fee on another asset')), 'free').toBeNull();
            await openGroup('P1b buy');
            expect(chargeOfCell(gridRowDescribed('P1b fee on the asset')), 'the FEE on the asset sits under the BUY').toBe(rowIdOf(gridRowDescribed('P1b buy')));

            const body = await validateNow();
            expectLinkedInBody(body, 'validate', 'P1b buy', 'P1b fee on the asset');
            const other = createDescribed(body, 'P1b fee on another asset');
            expect(other, 'the FEE on another asset names no parent').not.toHaveProperty('parent_ref');
            expect(other).not.toHaveProperty('parent_transaction_id');
            expect(other.asset_id, 'and keeps its own asset').toBe(202);
        });

        // §5, second half of the consultant's condition: a problem the import itself raised on a charge of a closed group.
        // The banner of blocking todos names the FEE by the label derived from its parent (the entry's `#<label>`; the
        // entry publishes no data-row-label, so its leading row number is read — data, not wording); its jump opens the
        // group and lands on the FEE; «Save all» is off and says why (its title is the catalogue's blocker hint).
        it('a blocking import todo on an imported FEE in its closed group: the banner names it <parent>·1, the jump opens the group, Save all is off with its reason', async () => {
            const blocker = {field: 'description', severity: 'blocker' as const, reasonCode: 'p1b_probe_blocker', message: 'p1b probe blocker'};
            await openImportEditor();
            await handOver([importedParent('P1b buy', 'r1'), {...importedCharge('FEE', 'P1b fee', 'r1'), todos: [blocker]}]);
            expect(theChipOf('P1b buy'), 'premise: the group is closed').toHaveAttribute('aria-expanded', 'false');
            expect(rowsDescribed('P1b fee'), 'premise: the FEE is not on screen').toHaveLength(0);
            const parentLabel = (gridRowDescribed('P1b buy').querySelector('[data-testid="tx-bulk-row-label"]')?.textContent ?? '').trim();

            const commit = screen.getByTestId('tx-bulk-commit');
            expect(commit, '«Save all» is off while a blocking todo stands').toBeDisabled();
            expect(commit, 'and says why').toHaveAttribute('title', get(_)('importWizard.todoBlockerCommitHint'));

            const banner = screen.getByTestId('tx-bulk-todo-blockers');
            if (within(banner).queryAllByTestId('tx-bulk-todo-goto').length === 0) {
                await fireEvent.click(within(banner).getByTestId('tx-bulk-todo-blockers-toggle'));
                await settle();
            }
            const gotos = within(banner).getAllByTestId('tx-bulk-todo-goto');
            expect(gotos, 'one entry: the one blocker this test handed over').toHaveLength(1);
            expect((gotos[0].textContent ?? '').trim().startsWith(`#${parentLabel}·1`), `the entry names the FEE by its derived label #${parentLabel}·1: ${gotos[0].textContent}`).toBe(true);

            await fireEvent.click(gotos[0]);
            await settle();

            expect(theChipOf('P1b buy'), 'the jump opens the group').toHaveAttribute('aria-expanded', 'true');
            const fee = gridRowDescribed('P1b fee');
            expect(rowIdOf(fee), 'the entry leads to the FEE').toBe(gotos[0].getAttribute('data-row-id'));
            await waitFor(() => expect(fee, 'and the jump lands on it').toHaveAttribute('data-highlighted', 'true'));
        });

        it('no followsParent: the BUY leaves the batch, its imported FEE stays, free, with its own values', async () => {
            await openImportEditor();
            await handOver([importedParent('P1b buy', 'r1'), importedCharge('FEE', 'P1b fee', 'r1')]);
            expect(theChipOf('P1b buy'), 'premise: linked').toHaveAttribute('data-charges-count', '1');

            // A new row's «Delete» takes it out of the batch (`removeRow` → `withoutRows`).
            await rowAction(gridRowDescribed('P1b buy'), 'mark-delete');

            expect(rowsDescribed('P1b buy'), 'the BUY left the batch').toHaveLength(0);
            expect(rowsDescribed('P1b fee'), 'the FEE stays, on screen').toHaveLength(1);
            expect(chargeOfCell(gridRowDescribed('P1b fee')), 'as a top-level row').toBeNull();
            const body = await validateNow();
            expect(body.creates ?? []).toHaveLength(1);
            const charge = createDescribed(body, 'P1b fee');
            expect(charge, 'its own values').toMatchObject({broker_id: 77, asset_id: 101, date: P1B_DATE, cash: {code: 'EUR', amount: '-1.5'}});
            expect(charge).not.toHaveProperty('parent_ref');
        });

        it('a refusal of an imported FEE in its closed group is in the banner with the derived label; the jump opens the group and goes to the FEE', async () => {
            const {validateTransactions} = await api();
            // The hand-over validates once by itself: the FEE's create is refused, at the index it holds in that body.
            validateTransactions.mockImplementation((async (payload: Payload) => {
                const index = (payload.creates ?? []).findIndex((create) => create.description === 'P1b fee');
                const issues = index < 0 ? [] : [{operation: 'create', index, ref_id: null, error: 'refused by the test', code: 'p1bTestRefusal', params: null}];
                return {committed: issues.length === 0, issues, rawResponse: {wac_results: []}};
            }) as never);
            await openImportEditor();
            await handOver([importedParent('P1b buy', 'r1'), importedCharge('FEE', 'P1b fee', 'r1')]);
            expect(theChipOf('P1b buy'), 'premise: the group is closed').toHaveAttribute('aria-expanded', 'false');
            const parentLabel = (gridRowDescribed('P1b buy').querySelector('[data-testid="tx-bulk-row-label"]')?.textContent ?? '').trim();

            const issue = await screen.findByTestId('tx-bulk-issue');
            expect(issue, 'the issue names the FEE by the label derived from its parent').toHaveAttribute('data-row-label', `${parentLabel}·1`);

            await fireEvent.click(issue);
            await settle();

            expect(theChipOf('P1b buy'), 'the jump opens the group').toHaveAttribute('aria-expanded', 'true');
            await waitFor(() => expect(gridRowDescribed('P1b fee'), 'and lands on the FEE row').toHaveAttribute('data-highlighted', 'true'));
        });
    });

    /*
     * 66 C21 — no pair-promote for a row that still has linked charges (contract `66-C21-promote-contract.md` §1–§3,
     * corrected by §4 and §5; the Transactions page and the disabled toolbar button are C22, not here).
     *
     * Rule 6 of the plan: a row with linked charges is refused as a leg of a pair until they are unlinked; nothing unlinks
     * by itself (rule 5, D4). One predicate, `hasLinkedCharges(op)`: the charges still under it in the Bulk's pending
     * state (`linkedChargesOf`: «del» and «scollega» do not count), or saved charges of it the Bulk does not hold yet
     * (`charges_count` minus the saved charges of that parent present in `ops`, wherever they sit now — §4.3, so a charge
     * moved A → B by «Collega» leaves A free). Every offer is cut at its source, on both legs: the database search
     * (`isSuggestable`), the banner (`localSuggestions`, `editStandalone`, `mixedPromotePairs`) and so «Merge all», and the
     * selection toolbar (`selectedForPromote` → `promote-toolbar-confirm`). `executePromote` refuses as a defence
     * (`tx.bulk.promote.refused.charges`, an error toast). «Reset row» on a charge whose parent is a leg of a pair keeps it
     * «scollega» (§5.2), with the `paired` reason of «Link» as its toast.
     *
     * Every "no offer" stands beside a positive control in the same editor: two clean pairs (70 and 90) that are offered,
     * so an absence never passes because nothing was offered at all. The blocked pair is 50 EUR, a DEPOSIT on 77 and a
     * WITHDRAWAL on 88 (CASH_TRANSFER: two brokers, one currency, amounts that cancel). The FEE has no asset (a DEPOSIT has
     * none: `noAsset` / `otherAsset` would refuse the link). Rows are found by `#id` or by the description the test gave
     * them; a payload row by its broker, type and amount; the search's inputs by id (saved) or by type, broker and amount
     * (a new row's id is synthetic).
     *
     * Already covered, not repeated: a charge under a parent «del» keeps «unlink» on «Restore» (F7-c1, ««Restore» from the
     * menu of a saved charge under a parent «del»»), and an indented charge offers no «Reset row» (F7-c1, «the menu of an
     * indented row…»), so `resetRow` on it is reachable only through «Reset all». The «saved pair» half of §5.2 (a saved
     * charge whose saved parent is a leg of a saved pair) is a state the backend refuses to save (rule 8,
     * `row_is_paired`): not built here.
     */
    describe('66 C21: no pair-promote for a row that still has linked charges', () => {
        const C21_DATE = '2026-10-05';
        const CONTROL_AMOUNTS = [70, 90] as const;
        type Side = 'DEPOSIT' | 'WITHDRAWAL';
        /** A row of a case: saved by its id, new by the description the test gave it; broker, type and amount (a magnitude)
         *  find it in a payload. */
        type RowRef = {kind: 'saved' | 'new'; id: number | null; type: Side; broker: number; amount: number; description: string};
        type PairRef = {dep: RowRef; wd: RowRef};
        /** A case: the pair whose `charged` leg has linked charges, and the two clean pairs beside it. */
        type Scenario = {blocked: PairRef; controls: PairRef[]; charged: Side};
        type SuggestInput = {id: number; type: string; broker_id: number; amount: number | null};
        type PromoteItem = {id_a?: number; id_b?: number; link_uuid_a?: string; link_uuid_b?: string};
        type C21Payload = {creates?: Array<Record<string, unknown>>; updates?: Array<Record<string, unknown>>; deletes?: number[]; promotes?: PromoteItem[]};

        beforeEach(() => {
            // «Link» and the import's links read the user's right to edit both brokers.
            mergeBrokers([
                {id: 77, name: 'C21 broker A', user_role: 'OWNER'},
                {id: 88, name: 'C21 broker B', user_role: 'OWNER'},
            ]);
        });

        afterEach(() => {
            resetBrokerStore();
        });

        /** A saved cash row of the case's day, no asset. */
        function savedCash(id: number, type: Side | 'FEE', broker: number, amount: string, description: string, over: Partial<TXReadItem> = {}): TXReadItem {
            return {
                id,
                broker_id: broker,
                asset_id: null,
                type,
                date: C21_DATE,
                quantity: '0',
                cash: {code: 'EUR', amount},
                related_transaction_id: null,
                partner_broker_id: null,
                parent_transaction_id: null,
                tags: [],
                description,
                cost_basis_override: null,
                asset_event_id: null,
                charges_count: 0,
                ...over,
            } as TXReadItem;
        }

        function savedRef(tx: TXReadItem): RowRef {
            return {kind: 'saved', id: tx.id, type: tx.type as Side, broker: tx.broker_id, amount: Math.abs(Number(tx.cash?.amount)), description: tx.description ?? ''};
        }

        function newRef(type: Side, broker: number, amount: number, description: string): RowRef {
            return {kind: 'new', id: null, type, broker, amount, description};
        }

        function labelOf(ref: RowRef): string {
            return ref.kind === 'saved' ? `saved ${ref.type} #${ref.id}` : `new ${ref.type} «${ref.description}»`;
        }

        function rowOf(ref: RowRef): HTMLElement {
            return ref.kind === 'saved' ? gridRow(ref.id as number) : gridRowDescribed(ref.description);
        }

        /** The chip of a parent row, or null. */
        function chipOfRow(row: HTMLElement): HTMLElement | null {
            return screen.queryByTestId(`tx-bulk-charges-toggle-${row.getAttribute('data-row-id')}`);
        }

        /** Bring a row's checkbox to `on`, whatever state it is in. */
        async function setTicked(row: HTMLElement, on: boolean): Promise<void> {
            const box = rowCheckbox(row);
            if (!box) throw new Error(`the row ${row.getAttribute('data-row-id')} has no checkbox`);
            if ((box.getAttribute('data-state') === 'checked') !== on) {
                await fireEvent.click(box);
                await settle();
            }
            if (on) expect(rowCheckbox(row)).toHaveAttribute('data-state', 'checked');
            else expect(rowCheckbox(row)).not.toHaveAttribute('data-state', 'checked');
        }

        /** Whether the selection toolbar offers to merge these two rows: both ticked, the toolbar read, both unticked. 66 C22:
         *  a merge button drawn off (`aria-disabled`) is not an offer; off, it must say the C22 reason (`hasCharges`). */
        async function toolbarOffers(a: RowRef, b: RowRef): Promise<boolean> {
            await setTicked(rowOf(a), true);
            await setTicked(rowOf(b), true);
            expect(screen.queryByTestId('tx-bulk-delete-selected'), 'premise: the selection toolbar answers the selection').not.toBeNull();
            const button = screen.queryByTestId('promote-toolbar-confirm');
            const offered = button !== null && button.getAttribute('aria-disabled') !== 'true';
            if (button !== null && !offered) expect(button, 'a merge button drawn off says why: hasCharges').toHaveAttribute('data-disabled-reason', 'hasCharges');
            await setTicked(rowOf(a), false);
            await setTicked(rowOf(b), false);
            return offered;
        }

        /** How many pairs the banner lists (the editor's rows are all this case's own). */
        function bannerItems(): number {
            return document.querySelectorAll('[data-testid^="promote-suggest-item-"]').length;
        }

        const suggestMock = () => vi.mocked(zodiosApi.promote_suggest_api_v1_transactions_promote_suggest_post);

        /** The inputs of every promote-suggest request so far. */
        function suggestCalls(): SuggestInput[][] {
            return suggestMock().mock.calls.map((call) => call[0] as unknown as SuggestInput[]);
        }

        function asks(input: SuggestInput, ref: RowRef): boolean {
            if (ref.kind === 'saved') return input.id === ref.id;
            return input.type === ref.type && input.broker_id === ref.broker && Math.abs(Number(input.amount)) === ref.amount;
        }

        /** The database search, debounced (500 ms): a poll with a deadline until it asks about `barrier`, then `blocked`
         *  must be in no request. */
        async function expectSearchSkips(blocked: RowRef, barrier: RowRef): Promise<void> {
            await waitFor(
                () =>
                    expect(
                        suggestCalls().some((inputs) => inputs.some((input) => asks(input, barrier))),
                        `premise: the search asked about ${labelOf(barrier)}`,
                    ).toBe(true),
                {timeout: 3_000},
            );
            const asked = suggestCalls().filter((inputs) => inputs.some((input) => asks(input, blocked)));
            expect.soft(asked.length, `C21: ${labelOf(blocked)} has linked charges, yet the Bulk sends it to promote-suggest (isSuggestable)`).toBe(0);
        }

        /** «Merge all» from the banner, with its default answer. */
        async function mergeAll(): Promise<void> {
            const button = screen.queryByTestId('promote-suggest-merge-all');
            expect(button, 'premise: «Merge all» is offered (two clean pairs at least)').not.toBeNull();
            await fireEvent.click(button!);
            await settle();
            await fireEvent.click(await screen.findByTestId('promote-all-confirm'));
            await settle();
        }

        /** Whether a payload merges this row: a saved one named by a promote, a new one promoted locally (its create a
         *  CASH_TRANSFER) or named by a promote through its link_uuid. */
        function merged(ref: RowRef, body: C21Payload): boolean {
            const promotes = body.promotes ?? [];
            if (ref.kind === 'saved') return promotes.some((item) => item.id_a === ref.id || item.id_b === ref.id);
            const create = (body.creates ?? []).find((item) => item.broker_id === ref.broker && Math.abs(Number((item.cash as {amount?: string} | null)?.amount)) === ref.amount && (item.type === ref.type || item.type === 'CASH_TRANSFER'));
            if (!create) throw new Error(`no create of ${labelOf(ref)} in ${JSON.stringify(body.creates)}`);
            const link = typeof create.link_uuid === 'string' ? create.link_uuid : null;
            return create.type === 'CASH_TRANSFER' || (link !== null && promotes.some((item) => item.link_uuid_a === link || item.link_uuid_b === link));
        }

        /**
         * The whole check of a case, on every surface, each C21 absence soft so one run names them all: the search, the
         * banner, the toolbar (with a clean pair offered first), «Merge all» (the clean pairs merged, the blocked one not).
         */
        async function expectNoOffer(s: Scenario): Promise<void> {
            const chargedLeg = s.charged === 'DEPOSIT' ? s.blocked.dep : s.blocked.wd;
            const otherLeg = s.charged === 'DEPOSIT' ? s.blocked.wd : s.blocked.dep;

            // 1. The database search: the charged leg is not asked about; the other leg is, it has no charge.
            await expectSearchSkips(chargedLeg, otherLeg);

            // 2. The banner: the clean pairs, and only them.
            expect(screen.queryByTestId('promote-suggest-banner'), 'control: the banner offers the clean pairs').not.toBeNull();
            expect.soft(bannerItems(), `C21: the banner lists the pair whose ${s.charged} has linked charges (expected only the ${s.controls.length} clean pairs)`).toBe(s.controls.length);

            // 3. The selection toolbar.
            expect(await toolbarOffers(s.controls[0].dep, s.controls[0].wd), 'control: the toolbar offers a clean pair').toBe(true);
            expect.soft(await toolbarOffers(s.blocked.dep, s.blocked.wd), `C21: the selection toolbar offers to merge ${labelOf(s.blocked.dep)} and ${labelOf(s.blocked.wd)}, while the ${s.charged} has linked charges`).toBe(false);

            // 4. «Merge all».
            await mergeAll();
            const body = (await validateNow()) as C21Payload;
            for (const pair of s.controls) expect(merged(pair.dep, body) || merged(pair.wd, body), `control: «Merge all» merges the clean pair ${labelOf(pair.dep)} / ${labelOf(pair.wd)} — ${JSON.stringify(body)}`).toBe(true);
            expect(merged(s.blocked.dep, body) || merged(s.blocked.wd, body), `C21: «Merge all» merges the pair whose ${s.charged} has linked charges — ${JSON.stringify(body)}`).toBe(false);
        }

        /** «+ Add row» and the row the Form pushes back; ends on the Form closed. */
        async function addRow(payload: Record<string, unknown>): Promise<void> {
            await fireEvent.click(screen.getByTestId('tx-bulk-add-row'));
            await settle();
            await waitFor(() => expect(formProbe().open, '«Add row» opens the Form').toBe(true));
            await push(payload);
        }

        /** A cash row as the Form pushes it back: signed values (W-B65). */
        function cashPayload(type: Side, broker: number, signedAmount: string, description: string, over: Record<string, unknown> = {}): Record<string, unknown> {
            return {broker_id: broker, type, date: C21_DATE, quantity: '0', asset_id: null, cash: {code: 'EUR', amount: signedAmount}, tags: [], description, ...over};
        }

        /** A saved cash row pushed back unchanged by its Form, with `over` applied. */
        function savedPayload(tx: TXReadItem, over: Record<string, unknown> = {}): Record<string, unknown> {
            return cashPayload(tx.type as Side, tx.broker_id, tx.cash?.amount ?? '0', tx.description ?? '', over);
        }

        /** «scollega» of every charge of a saved parent, in its Form (`_charges` state `unlink`), `fee` applied to each. */
        async function unlinkInParentForm(parent: TXReadItem, count: number, fee: Partial<ChargeDraft> = {}): Promise<void> {
            await rowAction(gridRow(parent.id), 'edit-single');
            await waitForParentForm(parent.id, count);
            await push(savedPayload(parent, {_charges: handedDrafts().map((draft): ChargeDraft => ({...draft, ...fee, state: 'unlink'}))}));
        }

        // -------------------------------------------------------------------
        // The cases of §2.1: one builder each, then `expectNoOffer`
        // -------------------------------------------------------------------

        /** New + new, the way an import brings them: the FEE named under the charged leg (`ref` / `parent_ref`). */
        async function newNewScenario(charged: Side): Promise<Scenario> {
            const item = (type: Side | 'FEE', broker: number, amount: string, description: string, extra: Record<string, unknown> = {}) => ({
                tx: {broker_id: broker, asset_id: null, type, date: C21_DATE, quantity: '0', cash: {code: 'EUR', amount}, tags: [], description, ...extra} as unknown as TransactionCreateItem,
                todos: [],
            });
            mountEditor({action: 'import'});
            await waitFor(() => expect(wizardProbe().open, 'the import intent opens the wizard').toBe(true));
            const chargedBroker = charged === 'DEPOSIT' ? 77 : 88;
            const batch = [
                item('DEPOSIT', 77, '50', 'C21 new deposit', charged === 'DEPOSIT' ? {ref: 'c21'} : {}),
                item('WITHDRAWAL', 88, '-50', 'C21 new withdrawal', charged === 'WITHDRAWAL' ? {ref: 'c21'} : {}),
                item('FEE', chargedBroker, '-1.5', 'C21 new fee', {parent_ref: 'c21'}),
                ...CONTROL_AMOUNTS.flatMap((amount) => [item('DEPOSIT', 77, String(amount), `C21 control deposit ${amount}`), item('WITHDRAWAL', 88, `-${amount}`, `C21 control withdrawal ${amount}`)]),
            ];
            await (wizardProbe().onImportBatch as (creates: unknown[]) => Promise<void>)(batch);
            await settle();
            const chargedDescription = charged === 'DEPOSIT' ? 'C21 new deposit' : 'C21 new withdrawal';
            await waitFor(() => expect(chipOfRow(gridRowDescribed(chargedDescription)), `premise: the FEE is linked under the new ${charged}`).toHaveAttribute('data-charges-count', '1'));
            return {
                charged,
                blocked: {dep: newRef('DEPOSIT', 77, 50, 'C21 new deposit'), wd: newRef('WITHDRAWAL', 88, 50, 'C21 new withdrawal')},
                controls: CONTROL_AMOUNTS.map((amount) => ({dep: newRef('DEPOSIT', 77, amount, `C21 control deposit ${amount}`), wd: newRef('WITHDRAWAL', 88, amount, `C21 control withdrawal ${amount}`)})),
            };
        }

        /** The saved clean pairs of a case: a DEPOSIT on 77 and a WITHDRAWAL on 88 for each control amount. */
        function savedControls(): TXReadItem[][] {
            return CONTROL_AMOUNTS.map((amount, at) => [savedCash(92_111 + 2 * at, 'DEPOSIT', 77, `${amount}.000000`, `C21 control deposit ${amount}`), savedCash(92_112 + 2 * at, 'WITHDRAWAL', 88, `-${amount}.000000`, `C21 control withdrawal ${amount}`)]);
        }

        /**
         * Saved + saved: the charged leg counts one charge, a FEE whose read is answered (the FEE under it), held (still
         * reading) or failed (`charges_count` alone says it has one).
         */
        async function savedSavedScenario(charged: Side, read: 'answered' | 'held' | 'failed'): Promise<Scenario> {
            const dep = savedCash(92_101, 'DEPOSIT', 77, '50.000000', 'C21 saved deposit', {charges_count: charged === 'DEPOSIT' ? 1 : 0});
            const wd = savedCash(92_103, 'WITHDRAWAL', 88, '-50.000000', 'C21 saved withdrawal', {charges_count: charged === 'WITHDRAWAL' ? 1 : 0});
            const parent = charged === 'DEPOSIT' ? dep : wd;
            const fee = savedCash(92_102, 'FEE', parent.broker_id, '-1.500000', 'C21 saved fee', {parent_transaction_id: parent.id});
            const controls = savedControls();
            if (read === 'answered') answerChargesRead([fee]);
            else if (read === 'held') holdChargesReads();
            else readMock().mockRejectedValue(new Error('network down'));
            txStoreSetAll([dep, wd, ...controls.flat()], []);
            mountEditor({action: 'edit', txIds: [dep.id, wd.id, ...controls.flat().map((tx) => tx.id)]});
            await waitFor(() => expect(rowsOf(wd.id), 'premise: the WITHDRAWAL is on screen').toHaveLength(1));
            await waitFor(() => expect(readAskedFor(parent.id), `premise: the Bulk asked for the ${charged}’s charges`).toBe(true));
            if (read === 'answered') await waitFor(() => expect(chipOfRow(gridRow(parent.id)), `premise: the FEE read sits under the ${charged}`).toHaveAttribute('data-charges-count', '1'));
            if (read === 'held') expect(heldReads.length, 'premise: the read is still out').toBeGreaterThan(0);
            if (read === 'failed') {
                const toasts = await toastsMock();
                await waitFor(() =>
                    expect(
                        toasts.show.mock.calls.some((call) => call[0] === 'error'),
                        'premise: the read failed (its error toast)',
                    ).toBe(true),
                );
                expect(chipOfRow(gridRow(parent.id)), 'premise: no charge of it is in the Bulk').toBeNull();
            }
            return {
                charged,
                blocked: {dep: savedRef(dep), wd: savedRef(wd)},
                controls: controls.map(([d, w]) => ({dep: savedRef(d), wd: savedRef(w)})),
            };
        }

        /** New + saved (`mixedPromotePairs`): saved DEPOSITs, new WITHDRAWALs typed in the Form. The charge is the saved
         *  DEPOSIT's FEE (read), or a new FEE typed in the new WITHDRAWAL's charges. */
        async function mixedScenario(charged: Side): Promise<Scenario> {
            const dep = savedCash(92_101, 'DEPOSIT', 77, '50.000000', 'C21 saved deposit', {charges_count: charged === 'DEPOSIT' ? 1 : 0});
            const fee = savedCash(92_102, 'FEE', 77, '-1.500000', 'C21 saved fee', {parent_transaction_id: dep.id});
            const controlDeps = savedControls().map(([d]) => d);
            answerChargesRead(charged === 'DEPOSIT' ? [fee] : []);
            txStoreSetAll([dep, ...controlDeps], []);
            mountEditor({action: 'edit', txIds: [dep.id, ...controlDeps.map((tx) => tx.id)]});
            await waitFor(() => expect(rowsOf(dep.id), 'premise: the DEPOSIT is on screen').toHaveLength(1));
            if (charged === 'DEPOSIT') await waitFor(() => expect(chipOfRow(gridRow(dep.id)), 'premise: the FEE read sits under the DEPOSIT').toHaveAttribute('data-charges-count', '1'));
            const newFee: ChargeDraft = {key: 'new-1', id: null, type: 'FEE', cash: {amount: '1.500000', code: 'EUR'}, description: 'C21 new fee', original: null, state: 'linked'};
            await addRow(cashPayload('WITHDRAWAL', 88, '-50.000000', 'C21 new withdrawal', charged === 'WITHDRAWAL' ? {_charges: [newFee]} : {}));
            for (const amount of CONTROL_AMOUNTS) await addRow(cashPayload('WITHDRAWAL', 88, `-${amount}.000000`, `C21 control withdrawal ${amount}`));
            if (charged === 'WITHDRAWAL') expect(chipOfRow(gridRowDescribed('C21 new withdrawal')), 'premise: the new FEE sits under the new WITHDRAWAL').toHaveAttribute('data-charges-count', '1');
            return {
                charged,
                blocked: {dep: savedRef(dep), wd: newRef('WITHDRAWAL', 88, 50, 'C21 new withdrawal')},
                controls: controlDeps.map((d) => ({dep: savedRef(d), wd: newRef('WITHDRAWAL', 88, Math.abs(Number(d.cash?.amount)), `C21 control withdrawal ${Math.abs(Number(d.cash?.amount))}`)})),
            };
        }

        // Red today: no surface asks whether a leg has linked charges. Each case reports the search, the banner, the
        // toolbar and «Merge all» together (soft), beside the clean pairs that must stay offered (hard).
        it.each([
            ['new + new, the FEE under the DEPOSIT', () => newNewScenario('DEPOSIT')],
            ['new + new, the FEE under the WITHDRAWAL', () => newNewScenario('WITHDRAWAL')],
            ['saved + saved, the FEE read under the DEPOSIT', () => savedSavedScenario('DEPOSIT', 'answered')],
            ['saved + saved, the FEE read under the WITHDRAWAL', () => savedSavedScenario('WITHDRAWAL', 'answered')],
            ['saved + saved, the DEPOSIT counts a charge still being read', () => savedSavedScenario('DEPOSIT', 'held')],
            ['saved + saved, the DEPOSIT counts a charge whose read failed', () => savedSavedScenario('DEPOSIT', 'failed')],
            ['new + saved, the FEE read under the saved DEPOSIT', () => mixedScenario('DEPOSIT')],
            ['new + saved, a new FEE under the new WITHDRAWAL', () => mixedScenario('WITHDRAWAL')],
        ] as const)('C21 §2.1: %s — no offer anywhere (search, banner, toolbar, «Merge all»); the clean pairs still offered', async (_label, build) => {
            await expectNoOffer(await build());
        });

        // -------------------------------------------------------------------
        // §4.3 — «Collega» A → B: the charge counts where it sits now
        // -------------------------------------------------------------------

        const A = savedCash(92_301, 'DEPOSIT', 77, '50.000000', 'C21 parent A', {charges_count: 1});
        const FEE_A = savedCash(92_302, 'FEE', 77, '-1.500000', 'C21 fee of A', {parent_transaction_id: A.id});
        const WD_A = savedCash(92_303, 'WITHDRAWAL', 88, '-50.000000', 'C21 counterpart of A');
        /** A charge of A the server holds but A's count did not know of (saved meanwhile elsewhere): what a late read brings. */
        const LATE_FEE_A = savedCash(92_304, 'FEE', 77, '-0.500000', 'C21 late fee of A', {parent_transaction_id: A.id});
        const B = savedCash(92_311, 'DEPOSIT', 77, '60.000000', 'C21 parent B');
        const WD_B = savedCash(92_312, 'WITHDRAWAL', 88, '-60.000000', 'C21 counterpart of B');

        /** «Link» in the toolbar on these two rows, confirmed; ends on the panel closed. */
        async function linkRows(parent: HTMLElement, charge: HTMLElement): Promise<void> {
            await setTicked(parent, true);
            await setTicked(charge, true);
            const button = screen.queryByTestId('tx-bulk-link-charges');
            expect(button, 'premise: the selection offers «Link»').not.toBeNull();
            expect(button, 'premise: «Link» is on').not.toHaveAttribute('aria-disabled', 'true');
            await fireEvent.click(button!);
            await settle();
            const content = await screen.findByTestId('tx-charges-modal-content');
            await fireEvent.click(within(content).getByTestId('tx-charges-modal-confirm'));
            await settle();
            await waitFor(() => expect(screen.queryByTestId('tx-charges-modal-content'), 'the panel closed').toBeNull());
        }

        /** A with its FEE read, the FEE unlinked in A's Form, then linked to B by «Link» (F7-d §21.2). Ends on the FEE
         *  under B; A's own count still says 1. */
        async function openAtoB(): Promise<void> {
            answerChargesRead([FEE_A]);
            txStoreSetAll([A, WD_A, B, WD_B], []);
            mountEditor({action: 'edit', txIds: [A.id, WD_A.id, B.id, WD_B.id]});
            await waitFor(() => expect(rowsOf(WD_B.id), 'premise: the four rows are on screen').toHaveLength(1));
            await waitFor(() => expect(chipOfRow(gridRow(A.id)), 'premise: A’s FEE read sits under A').toHaveAttribute('data-charges-count', '1'));
            await unlinkInParentForm(A, 1);
            expect(chargeState(gridRow(FEE_A.id)), 'premise: the FEE is unlinked from A').toBe('unlink');
            await linkRows(gridRow(B.id), gridRow(FEE_A.id));
            expect(chargeOfCell(gridRow(FEE_A.id)), 'premise: the FEE now sits under B').toBe(gridRow(B.id).getAttribute('data-row-id'));
        }

        // Red today on B (nothing refuses a leg with linked charges). The A half is a guard, green today: it fixes the
        // predicate of §4.3 — A's saved charge is in the Bulk, under B, so A's count no longer blocks it.
        it('C21 §4.3: «Collega» A → B — B, which now holds the FEE, is offered nothing; A is offered with its counterpart (guard)', async () => {
            await openAtoB();

            expect(await toolbarOffers(savedRef(A), savedRef(WD_A)), 'guard (§4.3): A’s only saved charge is in the Bulk, under B — A is free, its counterpart is offered').toBe(true);
            expect.soft(bannerItems(), 'C21: the banner lists B’s pair too (expected A’s alone)').toBe(1);
            expect(await toolbarOffers(savedRef(B), savedRef(WD_B)), 'C21: the toolbar offers to merge B, which holds a linked FEE').toBe(false);
        });

        // -------------------------------------------------------------------
        // §2.2 — «scollega», then the offer comes back and the batch carries both
        // -------------------------------------------------------------------

        /** A DEPOSIT with its FEE and the WITHDRAWAL that cancels it, both legs with the same note (no merge dialog). */
        const DEP = savedCash(92_401, 'DEPOSIT', 77, '50.000000', 'C21 transfer', {charges_count: 1});
        const FEE_D = savedCash(92_402, 'FEE', 77, '-1.500000', 'C21 fee', {parent_transaction_id: DEP.id});
        const WD = savedCash(92_403, 'WITHDRAWAL', 88, '-50.000000', 'C21 transfer');

        async function openDepositWithFee(): Promise<void> {
            answerChargesRead([FEE_D]);
            txStoreSetAll([DEP, WD], []);
            mountEditor({action: 'edit', txIds: [DEP.id, WD.id]});
            await waitFor(() => expect(rowsOf(WD.id), 'premise: both rows are on screen').toHaveLength(1));
            await waitFor(() => expect(chipOfRow(gridRow(DEP.id)), 'premise: the FEE read sits under the DEPOSIT').toHaveAttribute('data-charges-count', '1'));
        }

        /** The toolbar's merge of the DEPOSIT and the WITHDRAWAL (same notes: no dialog); ends on the pair one row. */
        async function mergeFromToolbar(): Promise<void> {
            await setTicked(gridRow(DEP.id), true);
            await setTicked(gridRow(WD.id), true);
            const confirm = screen.queryByTestId('promote-toolbar-confirm');
            expect(confirm, 'the toolbar offers the merge').not.toBeNull();
            await fireEvent.click(confirm!);
            await settle();
            expect(screen.queryByTestId('promote-merge-modal-content'), 'premise: same notes, no merge dialog').toBeNull();
            const pairRows = gridRows().filter((row) => idCellText(row).includes(`#${DEP.id}`) || idCellText(row).includes(`#${WD.id}`));
            expect(pairRows, 'premise: the pair is one row').toHaveLength(1);
            const box = rowCheckbox(pairRows[0]);
            if (box?.getAttribute('data-state') === 'checked') {
                await fireEvent.click(box);
                await settle();
            }
        }

        /** «Save all», and the payload it committed. */
        async function saveAll(): Promise<C21Payload> {
            const {commitTransactions} = await api();
            const commit = screen.getByTestId('tx-bulk-commit');
            expect(commit, '«Save all» is on').not.toBeDisabled();
            await fireEvent.click(commit);
            await settle();
            await waitFor(() => expect(commitTransactions, 'Save all committed').toHaveBeenCalledTimes(1));
            return commitTransactions.mock.calls[0]?.[0] as C21Payload;
        }

        function promotedPairs(body: C21Payload): number[][] {
            return (body.promotes ?? []).map((item) => [item.id_a ?? 0, item.id_b ?? 0].sort((x, y) => x - y));
        }

        // Red today on its first premise (soft): before the unlink the toolbar already offers the merge, and the unlink
        // asks the search nothing new. The rest is the end state C21 must keep, green today: after «scollega» the merge
        // is offered, and one batch carries the unlink and the promote (the backend accepts both, 66-R4-R5).
        it('C21 §2.2: «scollega» on the FEE brings the offer back (the search asked again); merged, «Save all» sends the unlink and the promote in one batch', async () => {
            await openDepositWithFee();
            expect.soft(await toolbarOffers(savedRef(DEP), savedRef(WD)), 'C21: before the unlink, the toolbar already offers to merge the DEPOSIT that holds a linked FEE').toBe(false);
            await waitFor(
                () =>
                    expect(
                        suggestCalls().some((inputs) => inputs.some((input) => input.id === WD.id)),
                        'premise: the search asked about the WITHDRAWAL',
                    ).toBe(true),
                {timeout: 3_000},
            );
            const callsBefore = suggestCalls().length;

            await unlinkInParentForm(DEP, 1);

            expect(chargeState(gridRow(FEE_D.id)), 'premise: the FEE is unlinked, a top-level row').toBe('unlink');
            let askedAgain = true;
            try {
                await waitFor(
                    () =>
                        expect(
                            suggestCalls()
                                .slice(callsBefore)
                                .some((inputs) => inputs.some((input) => input.id === DEP.id)),
                        ).toBe(true),
                    {timeout: 3_000},
                );
            } catch {
                askedAgain = false;
            }
            expect.soft(askedAgain, 'C21: the unlink frees the DEPOSIT, and the search must be asked again about it').toBe(true);
            expect(screen.queryByTestId('promote-suggest-banner'), 'the banner offers the pair again').not.toBeNull();
            await mergeFromToolbar();

            const body = await saveAll();
            expect(
                (body.updates ?? []).filter((update) => update.id === FEE_D.id),
                'the FEE’s update is its unlink alone',
            ).toEqual([{id: FEE_D.id, parent_transaction_id: 0}]);
            expect(promotedPairs(body), 'one promote, the DEPOSIT and the WITHDRAWAL').toEqual([[DEP.id, WD.id].sort((x, y) => x - y)]);
            expect(body.deletes ?? [], 'nothing deleted').toEqual([]);
        });

        // -------------------------------------------------------------------
        // §4.4 — the defence in `executePromote`
        // -------------------------------------------------------------------

        // The one window (§4.4): the merge dialog open while a charges read lands. Reached through the UI: after A → B,
        // A counts one saved charge and holds none under it, so opening A's Form reads A's charges again (held here); the
        // user meanwhile merges A with its counterpart from the toolbar (different notes: the dialog opens); the read lands
        // with a charge of A the Bulk did not have. Confirming must merge nothing. Red today: the merge goes through.
        it('C21 §4.4: a charge read lands under A while the merge dialog is open — the confirmation merges nothing, notify tx.bulk.promote.refused.charges, an error toast', async () => {
            await openAtoB();
            holdChargesReads();
            await rowAction(gridRow(A.id), 'edit-single');
            const readOfA = heldReads.find((read) => read.parents.includes(A.id));
            expect(readOfA, 'premise: opening A’s Form reads A’s charges again (A counts one, holds none under it)').toBeDefined();
            expect(probe.form?.open ?? false, 'premise: the Form waits for that read').toBe(false);

            await setTicked(gridRow(A.id), true);
            await setTicked(gridRow(WD_A.id), true);
            const confirm = screen.queryByTestId('promote-toolbar-confirm');
            expect(confirm, 'premise: A, free since A → B, is offered with its counterpart').not.toBeNull();
            await fireEvent.click(confirm!);
            await settle();
            expect(await screen.findByTestId('promote-merge-modal-content'), 'premise: different notes open the merge dialog').toBeInTheDocument();

            readOfA!.resolve([LATE_FEE_A]);
            await settle();
            await waitFor(() => expect(chipOfRow(gridRow(A.id)), 'premise: the late charge sits under A').toHaveAttribute('data-charges-count', '1'));
            expect(screen.queryByTestId('promote-merge-modal-content'), 'premise: the merge dialog is still open').not.toBeNull();

            const since = eventSeq();
            const toasts = await toastsMock();
            toasts.show.mockClear();
            await fireEvent.click(screen.getByTestId('promote-merge-confirm'));
            await settle();

            expect.soft(eventsSince(since, 'tx.bulk.promote.refused.charges'), 'C21: the refusal is published (notify tx.bulk.promote.refused.charges)').toHaveLength(1);
            expect
                .soft(
                    toasts.show.mock.calls.some((call) => call[0] === 'error'),
                    'C21: the refusal raises an error toast',
                )
                .toBe(true);
            const body = (await validateNow()) as C21Payload;
            expect(promotedPairs(body), `C21: A holds a linked charge, yet the dialog’s confirmation merged it — ${JSON.stringify(body.promotes)}`).toEqual([]);
        });

        // -------------------------------------------------------------------
        // §5.2 — «Reset row» on a charge whose parent is now a leg of a pair keeps it «scollega»
        // -------------------------------------------------------------------

        /** The events of the app's ring buffer after `since` with this name (`notify`, the machine half). */
        function eventsSince(since: number, name: string): Array<{name: string; detail?: Record<string, unknown>}> {
            const lf = (window as unknown as {__lf?: {events?: Array<{seq: number; name: string; detail?: Record<string, unknown>}>}}).__lf;
            return (lf?.events ?? []).filter((event) => event.seq > since && event.name === name);
        }

        function eventSeq(): number {
            const lf = (window as unknown as {__lf?: {seq?: () => number}}).__lf;
            return lf?.seq?.() ?? 0;
        }

        /** The state of a charge on screen: its badge, or why it has none. */
        function chargeStateOf(id: number): string {
            const rows = rowsOf(id);
            if (rows.length === 0) return 'not on screen (back under its parent, linked)';
            return chargeState(rows[0]) ?? 'no state badge (a linked top-level row)';
        }

        /** Every toast message raised so far, whatever its variant. */
        async function toastMessages(): Promise<string[]> {
            const toasts = await toastsMock();
            return [...toasts.show.mock.calls.map((call) => String(call[1])), ...(['success', 'error', 'warning', 'info'] as const).flatMap((variant) => toasts[variant].mock.calls.map((call) => String(call[0])))];
        }

        /** The `paired` reason of «Link» (`transactions.chargesLink.reason.paired`), whatever row it names. */
        function pairedReason(): RegExp {
            const template = get(_)('transactions.chargesLink.reason.paired', {values: {type: '\u0001', ref: '\u0002'}});
            const escaped = template.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            return new RegExp(escaped.replace('\u0001', '.+').replace('\u0002', '.+'));
        }

        // Red today: `resetRow` rebuilds the charge from the store (`editOpFromTx`), so it goes back under its parent —
        // now the hidden leg of the pending pair — and the batch would link a charge to a pair (refused by the backend).
        // The contract names no event for this notify (§5.2: the existing text only): the toast is asserted, by its key.
        it.each([
            ['the row’s «Reset row»', 'row'],
            ['«Reset selected»', 'selected'],
        ] as const)('C21 §5.2: %s on a FEE unlinked from a DEPOSIT now merged (pending): it stays «unlink», its note restored, the paired reason toasted; Save all sends the unlink and the promote', async (_label, how) => {
            // Premise: the reason's pattern resolves the catalogue key and matches the text it renders.
            const reason = pairedReason();
            expect(reason.source, 'premise: the paired reason key resolves in the catalogue').not.toContain('chargesLink');
            expect(get(_)('transactions.chargesLink.reason.paired', {values: {type: 'FEE', ref: '#1'}}), 'premise: the pattern matches the rendered reason').toMatch(reason);
            await openDepositWithFee();
            await unlinkInParentForm(DEP, 1, {description: 'C21 fee note changed'});
            expect(chargeState(gridRow(FEE_D.id)), 'premise: the FEE is unlinked').toBe('unlink');
            expect(rowDescription(gridRow(FEE_D.id)), 'premise: its note changed').toBe('C21 fee note changed');
            await mergeFromToolbar();
            expect(chargeStateOf(FEE_D.id), 'premise: after the merge the FEE is still unlinked, a top-level row').toBe('unlink');
            const toasts = await toastsMock();
            for (const variant of ['show', 'success', 'error', 'warning', 'info'] as const) toasts[variant].mockClear();

            if (how === 'row') {
                await rowAction(gridRow(FEE_D.id), 'reset');
            } else {
                await setTicked(gridRow(FEE_D.id), true);
                const reset = screen.queryByTestId('tx-bulk-reset-selected');
                expect(reset, 'premise: «Reset selected» is offered for the edited FEE').not.toBeNull();
                expect(await clickCollectingErrors(reset!), '«Reset selected» throws nothing').toEqual([]);
            }

            expect(chargeStateOf(FEE_D.id), 'C21 §5.2: the reset gave the FEE back to its parent, a leg of the pending pair').toBe('unlink');
            expect(rowDescription(gridRow(FEE_D.id)), 'the reset restores the other fields: the saved note').toBe('C21 fee');
            const pattern = pairedReason();
            expect(
                (await toastMessages()).some((message) => pattern.test(message)),
                `C21 §5.2: a toast with the paired reason of «Link» (${pattern}) — got ${JSON.stringify(await toastMessages())}`,
            ).toBe(true);

            const body = await saveAll();
            expect(
                (body.updates ?? []).filter((update) => update.id === FEE_D.id),
                'the FEE’s update is its unlink alone',
            ).toEqual([{id: FEE_D.id, parent_transaction_id: 0}]);
            expect(promotedPairs(body), 'one promote, the DEPOSIT and the WITHDRAWAL').toEqual([[DEP.id, WD.id].sort((x, y) => x - y)]);
        });

        // -------------------------------------------------------------------
        // §TL-11 — a leg of a pair is no parent (rule 8): a charge owned by one is handed no `_newParent`
        // -------------------------------------------------------------------

        // The only way a charge keeps a NEW leg as its owner is the «del» door: «del» does not count as linked, so the new
        // DEPOSIT can be merged with the new WITHDRAWAL; the saved FEE, still owned by it, is a top-level row. Its Form
        // opens through «restore and edit», which undoes the link to the leg. A guard, green before and after.
        it('TL-11 guard: a saved FEE «del» under a new DEPOSIT, then the DEPOSIT merged with a new WITHDRAWAL: the FEE’s Form has no _newParent', async () => {
            const free = savedCash(92_421, 'FEE', 77, '-1.500000', 'TL11 free fee');
            const other = savedCash(92_422, 'DEPOSIT', 77, '7.000000', 'TL11 other deposit');
            answerChargesRead([]);
            txStoreSetAll([free, other], []);
            mountEditor({action: 'edit', txIds: [free.id, other.id]});
            await waitFor(() => expect(rowsOf(free.id), 'premise: the FEE is on screen').toHaveLength(1));
            const original: NonNullable<ChargeDraft['original']> = {type: 'FEE', cash: {amount: '1.500000', code: 'EUR'}, description: 'TL11 free fee'};
            const picked: ChargeDraft = {key: `saved-${free.id}`, id: free.id, type: 'FEE', cash: original.cash, description: original.description, original, state: 'linked', linkNew: true};
            // The same note on both legs: no merge dialog.
            const LEG = 'TL11 leg';
            await addRow(cashPayload('DEPOSIT', 77, '50.000000', LEG, {_charges: [picked]}));
            await addRow(cashPayload('WITHDRAWAL', 88, '-50.000000', LEG));
            const legs = () => gridRows().filter((row) => rowDescription(row) === LEG);
            expect(legs(), 'premise: two new legs').toHaveLength(2);
            expect(
                legs().map((row) => row.getAttribute('data-row-id')),
                'premise: the FEE sits under the new DEPOSIT',
            ).toContain(chargeOfCell(gridRow(free.id)));
            await rowAction(gridRow(free.id), 'mark-delete');
            expect(chargeState(gridRow(free.id)), 'premise: the FEE is «del»').toBe('del');

            for (const id of legs().map((row) => row.getAttribute('data-row-id'))) await setTicked(gridRows().find((row) => row.getAttribute('data-row-id') === id)!, true);
            const merge = screen.queryByTestId('promote-toolbar-confirm');
            expect(merge, 'premise: the toolbar offers the merge').not.toBeNull();
            await fireEvent.click(merge!);
            await settle();
            expect(legs(), 'premise: the pair is one row').toHaveLength(1);
            expect(rowsOf(free.id), 'premise: the FEE is on screen').toHaveLength(1);
            expect(chargeOfCell(gridRow(free.id)), 'premise: not under the leg').toBeNull();

            await rowAction(gridRow(free.id), 'edit-single');
            await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));
            await settle();

            await waitFor(() => {
                expect(formProbe().open, 'the Form is open').toBe(true);
                expect(formRow()?.id, 'on the FEE').toBe(free.id);
            });
            expect((formRow() as {_newParent?: unknown} | undefined)?._newParent ?? null, 'a leg is no parent').toBeNull();
        });

        // -------------------------------------------------------------------
        // §1.1 and §5.2 — the «del» door: a charge «del» does not count as linked; restoring it under a pair leg keeps
        // it «scollega»
        // -------------------------------------------------------------------

        /** The DEPOSIT's group opened by its chip; ends on the FEE drawn under it, indented. */
        async function openDepositGroup(): Promise<void> {
            const chip = chipOfRow(gridRow(DEP.id));
            expect(chip, 'premise: the DEPOSIT carries the chip of its FEE').not.toBeNull();
            if (chip!.getAttribute('aria-expanded') !== 'true') {
                await fireEvent.click(chip!);
                await settle();
            }
            expect(chipOfRow(gridRow(DEP.id)), 'premise: the DEPOSIT’s group is open').toHaveAttribute('aria-expanded', 'true');
            expect(rowsOf(FEE_D.id), 'premise: the FEE is drawn').toHaveLength(1);
            expect(chargeOfCell(gridRow(FEE_D.id)), 'premise: the FEE is indented under the DEPOSIT').toBe(gridRow(DEP.id).getAttribute('data-row-id'));
        }

        /** The DEPOSIT with its FEE read, the FEE marked «del» from its own row menu (the DEPOSIT untouched). */
        async function markFeeDeleted(): Promise<void> {
            await openDepositWithFee();
            await openDepositGroup();
            await rowAction(gridRow(FEE_D.id), 'mark-delete');
            expect(chargeState(gridRow(FEE_D.id)), 'premise: the FEE is marked «del»').toBe('del');
            expect(rowStatus(gridRow(DEP.id)), 'premise: the DEPOSIT is untouched by the FEE’s «del»').toBe('original');
        }

        /** The FEE's rows on screen after the merge; when none is drawn, the pair row's chip (if it has one) is opened
         *  first, so a row under a closed group is not taken for a vanished one. */
        async function feeRowsAfterMerge(): Promise<HTMLElement[]> {
            if (rowsOf(FEE_D.id).length > 0) return rowsOf(FEE_D.id);
            const pairRow = gridRows().find((row) => idCellText(row).includes(`#${DEP.id}`) || idCellText(row).includes(`#${WD.id}`));
            const chip = pairRow ? chipOfRow(pairRow) : null;
            if (chip && chip.getAttribute('aria-expanded') !== 'true') {
                await fireEvent.click(chip);
                await settle();
            }
            return rowsOf(FEE_D.id);
        }

        // Guard (§1.1): a charge «del» does not count as linked, so its parent is offered and merged; the backend accepts
        // the delete and the promote in one batch (`test_transaction_charge_edits.py`,
        // `test_deleting_the_charge_in_the_same_batch_lets_the_promote_pass`).
        it('C21 §1.1: the FEE marked «del» frees the DEPOSIT — the merge is offered (toolbar, banner) and done; «Save all» sends the FEE delete and the promote in one batch (guard)', async () => {
            await openDepositWithFee();
            await openDepositGroup();
            expect(await toolbarOffers(savedRef(DEP), savedRef(WD)), 'premise: with the FEE linked, the toolbar offers no merge').toBe(false);

            await rowAction(gridRow(FEE_D.id), 'mark-delete');
            expect(chargeState(gridRow(FEE_D.id)), 'premise: the FEE is marked «del»').toBe('del');

            expect(await toolbarOffers(savedRef(DEP), savedRef(WD)), 'C21 §1.1: a FEE «del» does not count as linked — the toolbar offers the merge').toBe(true);
            expect(screen.queryByTestId('promote-suggest-banner'), 'C21 §1.1: the banner offers the pair').not.toBeNull();
            expect(bannerItems(), 'C21 §1.1: the banner lists the DEPOSIT / WITHDRAWAL pair').toBe(1);
            await mergeFromToolbar();

            const body = await saveAll();
            expect(body.deletes ?? [], 'the FEE alone is deleted').toEqual([FEE_D.id]);
            expect(promotedPairs(body), 'one promote, the DEPOSIT and the WITHDRAWAL').toEqual([[DEP.id, WD.id].sort((x, y) => x - y)]);
            expect(
                (body.updates ?? []).filter((update) => update.id === FEE_D.id),
                'no update of the deleted FEE',
            ).toEqual([]);
        });

        // §1.1, after the merge: the FEE «del» keeps `chargeOf` the DEPOSIT, which may now be the hidden half of the pair.
        // The user must still see the row they marked (to restore it, or to know it goes): top-level or under the pair row.
        it('C21 §1.1: after the merge, the FEE «del» is still on screen (top-level or under the visible pair row), still «del»', async () => {
            await markFeeDeleted();
            await mergeFromToolbar();

            const feeRows = await feeRowsAfterMerge();
            const pairRow = gridRows().find((row) => idCellText(row).includes(`#${DEP.id}`) || idCellText(row).includes(`#${WD.id}`));
            expect(feeRows, `C21 §1.1: the FEE «del» vanished from the grid after the merge (visible pair row ${pairRow ? idCellText(pairRow) : 'none'}, its chip ${pairRow && chipOfRow(pairRow) ? 'present' : 'absent'})`).toHaveLength(1);
            expect(chargeState(feeRows[0]), 'the FEE is still marked «del»').toBe('del');
            expect(rowStatus(feeRows[0]), 'its status cell says «delete»').toBe('delete');
        });

        // Red today on its premise, with the test above: after the merge the DEPOSIT is the hidden half of the pair and the
        // FEE «del» is drawn nowhere, so its «Restore» door cannot be opened. Past that premise, a second red is predicted
        // from the code, not observed: «Restore» goes through `setRowDeleted` → `applyDeleteChoice`, which sets
        // `parentUnlink` on a restored charge only when its owner is «del» (a pair leg is not considered), so the FEE would
        // be linked again under a leg of the pending pair (`keepUnlinkedFromUnfitParents` guards `resetRow` only), and the
        // batch would promote a DEPOSIT that keeps a linked FEE (rule 6, refused by the backend).
        it('C21 §5.2: the FEE «del», the DEPOSIT merged, then «Restore» on the FEE: it stays «unlink», the paired reason toasted; Save all sends the unlink and the promote', async () => {
            // Premise: the reason's pattern resolves the catalogue key and matches the text it renders.
            const reason = pairedReason();
            expect(reason.source, 'premise: the paired reason key resolves in the catalogue').not.toContain('chargesLink');
            await markFeeDeleted();
            await mergeFromToolbar();
            const feeRows = await feeRowsAfterMerge();
            expect(feeRows, 'premise: the FEE «del» is reachable after the merge (its row menu is the «Restore» door)').toHaveLength(1);
            const toasts = await toastsMock();
            for (const variant of ['show', 'success', 'error', 'warning', 'info'] as const) toasts[variant].mockClear();

            await rowAction(feeRows[0], 'mark-delete');

            expect(chargeStateOf(FEE_D.id), 'C21 §5.2: «Restore» gave the FEE back to its parent, a leg of the pending pair').toBe('unlink');
            expect(
                (await toastMessages()).some((message) => reason.test(message)),
                `C21 §5.2: a toast with the paired reason of «Link» (${reason}) — got ${JSON.stringify(await toastMessages())}`,
            ).toBe(true);

            const body = await saveAll();
            expect(
                (body.updates ?? []).filter((update) => update.id === FEE_D.id),
                'C21 §5.2: the FEE’s update is its unlink alone',
            ).toEqual([{id: FEE_D.id, parent_transaction_id: 0}]);
            expect(promotedPairs(body), 'one promote, the DEPOSIT and the WITHDRAWAL').toEqual([[DEP.id, WD.id].sort((x, y) => x - y)]);
            expect(body.deletes ?? [], 'nothing deleted: the FEE was restored').toEqual([]);
        });

        // ===================================================================
        // 66 C22 — the merge off with its reason, one «leg of a pair», the resets with a queued merge
        // ===================================================================

        /**
         * Contract `66-C22-contract.md` (§5 corrects §1–§4). Nested in C21 to reuse its fixtures and helpers.
         *
         *   - §1.2 / §2.2 the selection toolbar: when every check of today passes (two rows, no partner, no «del»,
         *     `findPromoteMatch`, the exact cancel) but one row has linked charges, `promote-toolbar-confirm` is there,
         *     `aria-disabled="true"`, `data-reason="hasCharges"`; a click or a tap opens its reason (the shared Tooltip,
         *     `tooltip-content`, asserted on its state and on the catalogue key, never on a literal) and merges nothing.
         *     After «scollega» it is on; two rows that make no pair have none, as today.
         *   - §1.4 / §2.4 path 3: the charge's own Form, «Link to a transaction…» (`_parent_link`), naming a leg of a
         *     merge queued here, is refused: no `chargeOf`, `notify` `tx.bulk.charge.link.refused.paired` (a warning
         *     toast), the rest of the Form applied, the batch saves. A saved FEE (`patchRowFromForm`) and a new FEE
         *     (`addRowFromForm`) both reach the one branch, `applyChargePayload` called by `handleFormPushed`.
         *   - §1.5 / §2.5 / §5.1 path 5: a reset that touches a row of a queued merge undoes the merge first; «Reset
         *     selected» undoes every queued merge among the chosen rows, then resets, whatever the order of the rows.
         *   - §5.4 TBM:712 (`opToTxLike`, the Form's `related_transaction_id` of the visible row): not null exactly when
         *     the row is a leg (`isPairLeg`, `bulkCharges.test.ts`). A guard.
         *
         * The selection's order is the order of the operations (`handleBulkTableSelectionChange` filters `ops`), never the
         * order of the ticks; the operations follow the intent's `txIds` (`resolveInitialRows`), so the intent sets it.
         * The payload witness of a reset is «Validate now» (`validateTransactions`): it sends the same `pendingPromotes` as
         * «Save all», and a batch left with nothing to save makes «Save all» close the editor without a commit.
         */
        describe('66 C22: the merge off with its reason; «Link to a transaction» on a leg; the resets with a queued merge', () => {
            /** A plain pair (no charge): a DEPOSIT on 77 and the WITHDRAWAL on 88 that cancels it, same notes. */
            const D0 = savedCash(92_511, 'DEPOSIT', 77, '50.000000', 'C22 plain transfer');
            const W0 = savedCash(92_513, 'WITHDRAWAL', 88, '-50.000000', 'C22 plain transfer');
            /** A saved FEE of nobody, on the DEPOSIT's broker. */
            const FREE = savedCash(92_512, 'FEE', 77, '-1.500000', 'C22 free fee');
            /** Two WITHDRAWALs that make no pair with C21's DEP: amounts that do not cancel, the same broker. */
            const W_OTHER = savedCash(92_504, 'WITHDRAWAL', 88, '-60.000000', 'C21 transfer');
            const W_SAME = savedCash(92_505, 'WITHDRAWAL', 77, '-50.000000', 'C21 transfer');
            /** A saved CASH_TRANSFER pair, linked in the store (W, the sender, is the visible half). */
            const L_D = savedCash(92_521, 'DEPOSIT', 77, '50.000000', 'C22 linked', {type: 'CASH_TRANSFER', related_transaction_id: 92_522, partner_broker_id: 88});
            const L_W = savedCash(92_522, 'WITHDRAWAL', 88, '-50.000000', 'C22 linked', {type: 'CASH_TRANSFER', related_transaction_id: 92_521, partner_broker_id: 77});

            type FormItem = TXReadItem & {_charges?: ChargeDraft[]};

            /** The merge button of the selection toolbar, or null. */
            function promoteButton(): HTMLElement | null {
                return screen.queryByTestId('promote-toolbar-confirm');
            }

            /** The new rows of the grid (status `new`). */
            function newRows(): HTMLElement[] {
                return gridRows().filter((row) => rowStatus(row) === 'new');
            }

            /** The grid rows that show either of these saved ids. */
            function rowsShowing(...ids: number[]): HTMLElement[] {
                return gridRows().filter((row) => ids.some((id) => idCellText(row).includes(`#${id}`)));
            }

            /** Untick every ticked row; ends on an empty selection. */
            async function clearTicks(): Promise<void> {
                for (const row of gridRows()) {
                    const box = rowCheckbox(row);
                    if (box?.getAttribute('data-state') === 'checked') {
                        await fireEvent.click(box);
                        await settle();
                    }
                }
            }

            /** The toolbar's merge of two rows with the same notes (no dialog); ends on nothing ticked. */
            async function mergeSelected(a: HTMLElement, b: HTMLElement): Promise<void> {
                await setTicked(a, true);
                await setTicked(b, true);
                const button = promoteButton();
                expect(button, 'premise: the toolbar offers the merge').not.toBeNull();
                expect(button, 'premise: the merge is on').not.toHaveAttribute('aria-disabled', 'true');
                await fireEvent.click(button!);
                await settle();
                expect(screen.queryByTestId('promote-merge-modal-content'), 'premise: same notes, no merge dialog').toBeNull();
                await clearTicks();
            }

            /** The `chargesBlock` reason (`transactions.promote.chargesBlock`) naming a row of this type, any ref. */
            function chargesBlockReason(type: string): RegExp {
                const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const template = get(_)('transactions.promote.chargesBlock', {values: {type: '\u0001', ref: '\u0002'}});
                expect(template, 'premise: the chargesBlock key resolves in the catalogue').not.toContain('transactions.promote');
                const typeName = get(_)(`transactions.types.${type}`);
                return new RegExp(escape(template).replace('\u0001', escape(typeName)).replace('\u0002', '.+'));
            }

            /** The promotes of a payload, as sorted id pairs. */
            function promotesOf(body: C21Payload): number[][] {
                return promotedPairs(body);
            }

            async function warningToasts(): Promise<unknown[][]> {
                const toasts = await toastsMock();
                return toasts.show.mock.calls.filter((call) => call[0] === 'warning');
            }

            async function clearToasts(): Promise<void> {
                const toasts = await toastsMock();
                for (const variant of ['show', 'success', 'error', 'warning', 'info'] as const) toasts[variant].mockClear();
            }

            // ---------------------------------------------------------------
            // §2.2 — the merge button off, with its reason
            // ---------------------------------------------------------------

            /** C21's DEPOSIT and WITHDRAWAL, the DEPOSIT counting one charge whose read is held (never answered). */
            async function openDepositWithHeldCharge(): Promise<void> {
                holdChargesReads();
                txStoreSetAll([DEP, WD], []);
                mountEditor({action: 'edit', txIds: [DEP.id, WD.id]});
                await waitFor(() => expect(rowsOf(WD.id), 'premise: both rows are on screen').toHaveLength(1));
                await waitFor(() => expect(heldReads.length, 'premise: the read of the DEPOSIT’s charge is still out').toBeGreaterThan(0));
            }

            // Red today: with a linked charge `selectedForPromote` is null, so the button is not drawn at all (the first
            // assertion). After C22 it is drawn off, with its reason, and a click or a tap only opens that reason.
            it.each([
                ['the FEE read under the DEPOSIT, a click', 'answered', 'click'],
                ['the FEE read under the DEPOSIT, a tap', 'answered', 'tap'],
                ['the DEPOSIT counting a charge still being read, a click', 'held', 'click'],
            ] as const)('C22 §2.2: %s — promote-toolbar-confirm is there, aria-disabled, data-reason hasCharges; the reason opens; nothing merges', async (_label, read, how) => {
                if (read === 'answered') await openDepositWithFee();
                else await openDepositWithHeldCharge();
                await setTicked(gridRow(DEP.id), true);
                await setTicked(gridRow(WD.id), true);
                expect(screen.queryByTestId('tx-bulk-delete-selected'), 'premise: the selection toolbar answers the selection').not.toBeNull();

                const button = promoteButton();
                expect(button, 'C22: the merge button is drawn, off, when a leg has linked charges (today it is absent)').not.toBeNull();
                expect(button).toHaveAttribute('aria-disabled', 'true');
                expect(button).toHaveAttribute('data-disabled-reason', 'hasCharges');
                expect(screen.queryByTestId('tooltip-content'), 'premise: no reason open yet').toBeNull();

                if (how === 'click') {
                    await fireEvent.click(button!);
                } else {
                    await fireEvent.touchStart(button!);
                    await fireEvent.touchEnd(button!);
                    await fireEvent.click(button!);
                }
                await settle();

                const reason = await screen.findByTestId('tooltip-content');
                expect(reason, 'the reason is open').toBeInTheDocument();
                expect(reason.textContent ?? '', 'the reason is chargesBlock, naming the DEPOSIT (the row holding the charge)').toMatch(chargesBlockReason('DEPOSIT'));
                expect(screen.queryByTestId('promote-merge-modal-content'), 'no merge dialog').toBeNull();
                expect(rowsShowing(DEP.id, WD.id), 'no merge: two rows, as before').toHaveLength(2);
                // With the read held «Validate now» waits for it; the two rows are the witness there.
                if (read === 'answered') {
                    const body = (await validateNow()) as C21Payload;
                    expect(body.promotes ?? [], 'no merge queued').toEqual([]);
                }
            });

            // Guard, green today (C21 §2.2 reaches it too): after «scollega» on the FEE the button is on — no
            // aria-disabled, no data-reason — and merges.
            it('C22 §2.2 guard: «scollega» on the FEE — the button is on (no aria-disabled, no data-reason) and merges', async () => {
                await openDepositWithFee();
                await unlinkInParentForm(DEP, 1);
                expect(chargeState(gridRow(FEE_D.id)), 'premise: the FEE is unlinked').toBe('unlink');
                await setTicked(gridRow(DEP.id), true);
                await setTicked(gridRow(WD.id), true);
                const button = promoteButton();
                expect(button, 'the merge is offered').not.toBeNull();
                expect(button).not.toHaveAttribute('aria-disabled');
                expect(button).not.toHaveAttribute('data-disabled-reason');
                await fireEvent.click(button!);
                await settle();
                expect(rowsShowing(DEP.id, WD.id), 'merged: one row').toHaveLength(1);
            });

            // Guard, green today: rows that make no pair have no merge button, linked charge or not — the reason is shown
            // only when every check of today passes but the charges (§1.2).
            it.each([
                ['amounts that do not cancel', W_OTHER],
                ['the same broker', W_SAME],
            ] as const)('C22 §2.2 guard: the DEPOSIT with its FEE and a WITHDRAWAL on %s — no merge button at all', async (_label, other) => {
                answerChargesRead([FEE_D]);
                txStoreSetAll([DEP, other], []);
                mountEditor({action: 'edit', txIds: [DEP.id, other.id]});
                await waitFor(() => expect(rowsOf(other.id), 'premise: both rows are on screen').toHaveLength(1));
                await waitFor(() => expect(chipOfRow(gridRow(DEP.id)), 'premise: the FEE read sits under the DEPOSIT').toHaveAttribute('data-charges-count', '1'));
                await setTicked(gridRow(DEP.id), true);
                await setTicked(gridRow(other.id), true);
                expect(screen.queryByTestId('tx-bulk-delete-selected'), 'premise: the selection toolbar answers the selection').not.toBeNull();
                expect(promoteButton(), 'no pair: no merge button, on or off').toBeNull();
            });

            // ---------------------------------------------------------------
            // §2.4 — path 3: «Link to a transaction…» in the charge's Form, naming a leg of a queued merge
            // ---------------------------------------------------------------

            /** D0, W0 and the free FEE; D0 and W0 merged from the toolbar (queued). Ends on the pair one row. */
            async function openQueuedMergeWithFreeFee(): Promise<void> {
                answerChargesRead([]);
                txStoreSetAll([D0, W0, FREE], []);
                mountEditor({action: 'edit', txIds: [D0.id, W0.id, FREE.id]});
                await waitFor(() => expect(rowsOf(FREE.id), 'premise: the three rows are on screen').toHaveLength(1));
                await mergeSelected(gridRow(D0.id), gridRow(W0.id));
                expect(rowsShowing(D0.id, W0.id), 'premise: the merge is one row').toHaveLength(1);
            }

            /** The FEE's own Form, from its row menu; ends on the Form open on it. */
            async function openFeeForm(): Promise<void> {
                await rowAction(gridRow(FREE.id), 'edit-single');
                await waitFor(() => {
                    expect(formProbe().open, 'the FEE’s Form is open').toBe(true);
                    expect((formProbe().items as FormItem[] | null)?.[0]?.id, 'on the FEE').toBe(FREE.id);
                });
            }

            // Red today: TBM:3278 makes the picked row `chargeOf` without asking whether it is a leg, so the payload sends
            // `parent_transaction_id` = the leg (rule 8, refused by the backend), and no refusal is published. The FEE
            // staying a top-level row is a guard (rule 8 of `isUnderParent`, C21).
            it.each([
                ['the DEPOSIT (the hidden half)', 'dep'],
                ['the WITHDRAWAL (the visible half)', 'wd'],
            ] as const)('C22 §2.4: a saved FEE’s Form links it to %s of a queued merge — refused: no chargeOf, notify tx.bulk.charge.link.refused.paired, its note applied; the batch saves', async (_label, which) => {
                const leg = which === 'dep' ? D0 : W0;
                await openQueuedMergeWithFreeFee();
                await openFeeForm();
                const since = eventSeq();
                await clearToasts();

                await push(savedPayload(FREE, {description: 'C22 fee note changed', _parent_link: leg.id}));

                expect.soft(eventsSince(since, 'tx.bulk.charge.link.refused.paired'), 'C22: the refusal is published (notify tx.bulk.charge.link.refused.paired)').toHaveLength(1);
                expect.soft(await warningToasts(), 'C22: a warning toast says why').toHaveLength(1);
                expect(rowsOf(FREE.id), 'guard: the FEE is a row of its own').toHaveLength(1);
                expect(chargeOfCell(gridRow(FREE.id)), 'guard: not under the pair (rule 8)').toBeNull();
                expect(rowDescription(gridRow(FREE.id)), 'the rest of the Form applies: the note').toBe('C22 fee note changed');

                const validated = (await validateNow()) as C21Payload;
                const feeUpdates = (validated.updates ?? []).filter((update) => update.id === FREE.id);
                expect
                    .soft(
                        feeUpdates.filter((update) => 'parent_transaction_id' in update),
                        `C22: the FEE is sent with a parent, a leg of the pair — ${JSON.stringify(feeUpdates)}`,
                    )
                    .toEqual([]);
                expect(
                    feeUpdates.some((update) => update.description === 'C22 fee note changed'),
                    `the FEE’s note is sent — ${JSON.stringify(feeUpdates)}`,
                ).toBe(true);
                expect(promotesOf(validated), 'the merge stays queued').toEqual([[D0.id, W0.id].sort((x, y) => x - y)]);

                const body = await saveAll();
                expect(
                    (body.updates ?? []).filter((update) => update.id === FREE.id && 'parent_transaction_id' in update),
                    'C22: «Save all» sends no parent for the FEE',
                ).toEqual([]);
                expect(promotedPairs(body), 'one promote, the DEPOSIT and the WITHDRAWAL').toEqual([[D0.id, W0.id].sort((x, y) => x - y)]);
            });

            // Red today, as above, for a FEE born in its own Form («+ Add row»): `addRowFromForm`, then the same branch of
            // `applyChargePayload` (`handleFormPushed` calls it after either). It must not become a create with a parent.
            it('C22 §2.4: a new FEE from «+ Add row» linked to the DEPOSIT of a queued merge — refused: no parent in its create, the refusal published; the batch saves', async () => {
                await openQueuedMergeWithFreeFee();
                const since = eventSeq();
                await clearToasts();

                await addRow(cashPayload('FEE' as Side, 77, '-2.000000', 'C22 new fee', {_parent_link: D0.id}));

                expect.soft(eventsSince(since, 'tx.bulk.charge.link.refused.paired'), 'C22: the refusal is published (notify tx.bulk.charge.link.refused.paired)').toHaveLength(1);
                expect.soft(await warningToasts(), 'C22: a warning toast says why').toHaveLength(1);
                expect(chargeOfCell(gridRowDescribed('C22 new fee')), 'guard: the new FEE is a row of its own (rule 8)').toBeNull();

                const body = await saveAll();
                const create = (body.creates ?? []).find((item) => item.description === 'C22 new fee');
                expect(create, `the new FEE is created — ${JSON.stringify(body.creates)}`).toBeDefined();
                expect({parent_transaction_id: create?.parent_transaction_id ?? null, parent_ref: create?.parent_ref ?? null}, `C22: the new FEE is created with no parent — ${JSON.stringify(create)}`).toEqual({parent_transaction_id: null, parent_ref: null});
                expect(promotedPairs(body), 'one promote, the DEPOSIT and the WITHDRAWAL').toEqual([[D0.id, W0.id].sort((x, y) => x - y)]);
            });

            // Guard, green before and after: a row that is no leg is linked as today — the refusal is for legs only.
            it('C22 §2.4 guard: before any merge, the FEE’s Form links it to the DEPOSIT — chargeOf, sent with the parent, no refusal', async () => {
                answerChargesRead([]);
                txStoreSetAll([D0, W0, FREE], []);
                mountEditor({action: 'edit', txIds: [D0.id, W0.id, FREE.id]});
                await waitFor(() => expect(rowsOf(FREE.id), 'premise: the three rows are on screen').toHaveLength(1));
                await openFeeForm();
                const since = eventSeq();

                await push(savedPayload(FREE, {_parent_link: D0.id}));

                expect(eventsSince(since, 'tx.bulk.charge.link.refused.paired'), 'no refusal').toHaveLength(0);
                expect(chargeOfCell(gridRow(FREE.id)), 'the FEE sits under the DEPOSIT').toBe(gridRow(D0.id).getAttribute('data-row-id'));
                const body = (await validateNow()) as C21Payload;
                expect((body.updates ?? []).filter((update) => update.id === FREE.id)).toEqual([{id: FREE.id, parent_transaction_id: D0.id}]);
            });

            // ---------------------------------------------------------------
            // §2.5 — path 5: a reset with a queued merge
            // ---------------------------------------------------------------

            type Mix = 'saved+saved' | 'saved+new';

            /**
             * A merge queued from the toolbar. Saved + saved: D0 and W0. Saved + new: the saved W0 and a new DEPOSIT typed
             * in the Form (same note), so the saved row is the visible half — a create has no «Reset row». Ends on the pair
             * one row, edited, its merge in the payload.
             */
            async function openQueued(mix: Mix): Promise<HTMLElement> {
                answerChargesRead([]);
                if (mix === 'saved+saved') {
                    txStoreSetAll([D0, W0], []);
                    mountEditor({action: 'edit', txIds: [D0.id, W0.id]});
                    await waitFor(() => expect(rowsOf(W0.id), 'premise: both rows are on screen').toHaveLength(1));
                    await mergeSelected(gridRow(D0.id), gridRow(W0.id));
                } else {
                    // Two saved rows (the FEE is no pair of anything): the editor opens no Form by itself.
                    txStoreSetAll([W0, FREE], []);
                    mountEditor({action: 'edit', txIds: [W0.id, FREE.id]});
                    await waitFor(() => expect(rowsOf(FREE.id), 'premise: both rows are on screen').toHaveLength(1));
                    await addRow(cashPayload('DEPOSIT', 77, '50.000000', 'C22 plain transfer'));
                    expect(newRows(), 'premise: the new DEPOSIT is on screen').toHaveLength(1);
                    await mergeSelected(gridRow(W0.id), newRows()[0]);
                    expect(newRows(), 'premise: the new DEPOSIT is the hidden half').toHaveLength(0);
                }
                const pair = rowsShowing(D0.id, W0.id);
                expect(pair, 'premise: the merge is one row').toHaveLength(1);
                expect(idCellText(pair[0]), 'premise: the saved WITHDRAWAL (the sender) is the visible half').toContain(`#${W0.id}`);
                expect(rowStatus(pair[0]), 'premise: the visible half is edited (its type), so the resets are offered').toBe('edited');
                const queued = (await validateNow()) as C21Payload;
                expect((queued.promotes ?? []).length, `premise: one merge queued — ${JSON.stringify(queued.promotes)}`).toBe(1);
                return pair[0];
            }

            // Red today (the defect of 66-C22-mirror-audit row 5, reproduced): `resetAll` empties `pendingSplits` but not
            // `pendingPromotes`, and `resetRow` resets both halves from the store but leaves the merge in the queue. The
            // grid shows two rows of their own while the payload still merges them. In the mixed case the new half also
            // stays hidden (`pairedWith` naming the saved half's old tempId). Expected (§1.5): the merge undone first, as
            // «Split pair» does (`undoPendingPromote`), then the reset.
            it.each([
                ['saved + saved', 'Reset all', 'saved+saved', 'all'],
                ['saved + saved', 'Reset row on the visible half', 'saved+saved', 'row'],
                ['saved + new', 'Reset all', 'saved+new', 'all'],
                ['saved + new', 'Reset row on the visible (saved) half', 'saved+new', 'row'],
            ] as const)('C22 §2.5: %s merged, then «%s» — no merge left in the queue, both rows back on their own', async (_label, _door, mix, door) => {
                const pairRow = await openQueued(mix);
                if (door === 'all') {
                    const reset = screen.queryByTestId('tx-bulk-reset-all');
                    expect(reset, 'premise: «Reset all» is offered').not.toBeNull();
                    expect(await clickCollectingErrors(reset!), '«Reset all» throws nothing').toEqual([]);
                } else {
                    await rowAction(pairRow, 'reset');
                }

                expect.soft(rowsOf(W0.id), 'the saved WITHDRAWAL is a row').toHaveLength(1);
                expect.soft(rowStatus(gridRow(W0.id)), 'the saved WITHDRAWAL is back as saved').toBe('original');
                if (mix === 'saved+saved') {
                    expect.soft(rowsShowing(D0.id, W0.id), 'two rows of their own').toHaveLength(2);
                    expect.soft(rowStatus(gridRow(D0.id)), 'the saved DEPOSIT is back as saved').toBe('original');
                } else {
                    expect.soft(newRows(), 'C22: the new DEPOSIT is visible again, a row of its own (today it stays hidden behind the reset half)').toHaveLength(1);
                }
                const body = (await validateNow()) as C21Payload;
                expect.soft(body.promotes ?? [], `C22: the reset left a merge in the queue that the grid no longer shows — ${JSON.stringify(body.promotes)}`).toEqual([]);
                if (mix === 'saved+new') {
                    const create = (body.creates ?? []).find((item) => item.broker_id === 77 && item.type === 'DEPOSIT');
                    expect.soft(create, `C22: the new DEPOSIT is created as a DEPOSIT, on its own — ${JSON.stringify(body.creates)}`).toBeDefined();
                    expect.soft(create?.link_uuid ?? null, 'C22: the new DEPOSIT keeps no link of the undone merge').toBeNull();
                }
                expect(
                    (body.updates ?? []).filter((update) => update.id === W0.id || update.id === D0.id),
                    'no update of the saved rows: they are back as saved',
                ).toEqual([]);
            });

            // ---------------------------------------------------------------
            // §5.1 — «Reset selected» on the visible pair row and the FEE unlinked from the DEPOSIT, both orders
            // ---------------------------------------------------------------

            /** Where the FEE sits: under the DEPOSIT (indented in its open group, or counted by its chip while the group
             *  is closed) and linked, or a description of where it is instead. */
            function feeUnderDeposit(): string {
                if (rowsOf(DEP.id).length !== 1) return `the DEPOSIT is not one row of its own (${rowsOf(DEP.id).length})`;
                const depRow = gridRow(DEP.id);
                const feeRows = rowsOf(FEE_D.id);
                if (feeRows.length === 0) return chipOfRow(depRow)?.getAttribute('data-charges-count') === '1' ? 'under the DEPOSIT, linked' : 'not on screen, and not counted by the DEPOSIT’s chip';
                const under = chargeOfCell(feeRows[0]) === depRow.getAttribute('data-row-id');
                const state = chargeState(feeRows[0]);
                return under && state === 'linked' ? 'under the DEPOSIT, linked' : `${under ? 'under the DEPOSIT' : 'a top-level row'}, state ${state ?? 'none'}`;
            }

            // Red today, differently in each order — evidence that the two orders are distinct:
            //   - FEE first: `resetRow(FEE)` runs while the DEPOSIT is still a leg, so the FEE stays «unlink» and the
            //     kept-unlinked notify fires (C21 §5.2); then the pair is reset and the merge stays queued;
            //   - pair first: the pair is reset (the DEPOSIT no longer a leg), the FEE goes back under it, but the merge
            //     stays queued: the batch would link a FEE to a leg (rule 8) and promote a parent with a charge (rule 6).
            // After C22 (`resetRows`) the merges among the chosen rows are undone first: the same end state either way.
            it.each([
                ['the FEE before the pair in the operations', 'fee-first'],
                ['the pair before the FEE in the operations', 'pair-first'],
            ] as const)('C22 §5.1: «Reset selected» on the visible pair row and the FEE unlinked from its DEPOSIT, %s — the FEE back under the DEPOSIT, no merge queued, no pair notify', async (_label, order) => {
                answerChargesRead([FEE_D]);
                txStoreSetAll([DEP, WD, FEE_D], []);
                // The selection is the operations' order (`handleBulkTableSelectionChange` filters `ops`), which follows
                // the intent (`resolveInitialRows`); the FEE came with its parent, so it is adopted and nothing is read.
                mountEditor({action: 'edit', txIds: order === 'fee-first' ? [FEE_D.id, DEP.id, WD.id] : [DEP.id, WD.id, FEE_D.id]});
                await waitFor(() => expect(rowsOf(WD.id), 'premise: the rows are on screen').toHaveLength(1));
                await waitFor(() => expect(chipOfRow(gridRow(DEP.id)), 'premise: the FEE sits under the DEPOSIT').toHaveAttribute('data-charges-count', '1'));
                await unlinkInParentForm(DEP, 1);
                expect(chargeState(gridRow(FEE_D.id)), 'premise: the FEE is unlinked, a top-level row').toBe('unlink');
                await mergeSelected(gridRow(DEP.id), gridRow(WD.id));
                const pair = rowsShowing(DEP.id, WD.id);
                expect(pair, 'premise: the merge is one row').toHaveLength(1);

                await setTicked(pair[0], true);
                await setTicked(gridRow(FEE_D.id), true);
                const reset = screen.queryByTestId('tx-bulk-reset-selected');
                expect(reset, 'premise: «Reset selected» is offered').not.toBeNull();
                const since = eventSeq();
                await clearToasts();
                expect(await clickCollectingErrors(reset!), '«Reset selected» throws nothing').toEqual([]);

                expect.soft(eventsSince(since, 'tx.bulk.reset.charge.kept-unlinked'), 'C22: no «half of a pair» notify — the pair is undone before the FEE is reset').toHaveLength(0);
                expect.soft(await warningToasts(), 'C22: no warning toast').toHaveLength(0);
                expect.soft(rowsShowing(DEP.id, WD.id), 'the pair undone: two rows of their own').toHaveLength(2);
                expect.soft(feeUnderDeposit(), 'C22: the FEE is back under the DEPOSIT, linked').toBe('under the DEPOSIT, linked');
                const body = (await validateNow()) as C21Payload;
                expect.soft(body.promotes ?? [], `C22: a merge is still queued — ${JSON.stringify(body.promotes)}`).toEqual([]);
                expect
                    .soft(
                        (body.updates ?? []).filter((update) => update.id === FEE_D.id),
                        'C22: the FEE is back as saved: no update',
                    )
                    .toEqual([]);
            });

            // ---------------------------------------------------------------
            // §5.4 — TBM:712, the Form's related_transaction_id of the visible row: not null exactly on a leg (guard)
            // ---------------------------------------------------------------

            // Guard, green before and after: `opToTxLike` keeps its own computation (it needs the partner's id, or 0 for a
            // new one); on the visible row its «not null» is `isPairLeg`. Read from the Form probe, by the row's own id.
            it.each([
                ['a saved pair loaded as such', 'loaded', true],
                ['a merge queued in this Bulk', 'queued', true],
                ['a saved pair split in this Bulk', 'split', false],
                ['two lone rows', 'lone', false],
            ] as const)('C22 §5.4 guard: %s — the Form’s related_transaction_id of the visible row is not null exactly on a leg (%s)', async (_label, state, leg) => {
                answerChargesRead([]);
                const [from, to] = state === 'loaded' || state === 'split' ? [L_W, L_D] : [W0, D0];
                txStoreSetAll([from, to], []);
                mountEditor({action: 'edit', txIds: [to.id, from.id]});
                await waitFor(() => expect(rowsShowing(from.id, to.id).length, 'premise: the rows are on screen').toBeGreaterThan(0));
                if (state === 'queued') await mergeSelected(gridRow(to.id), gridRow(from.id));
                if (state === 'split') {
                    const pair = rowsShowing(from.id, to.id);
                    expect(pair, 'premise: the saved pair is one row').toHaveLength(1);
                    await rowAction(pair[0], 'split');
                }
                const rows = rowsShowing(from.id, to.id);
                expect(rows, 'premise: one row for a pair, two otherwise').toHaveLength(leg ? 1 : 2);
                const visible = leg ? rows[0] : gridRow(from.id);
                await rowAction(visible, 'edit-single');
                await waitFor(() => expect(formProbe().open, 'the Form is open').toBe(true));
                const item = ((formProbe().items as FormItem[] | null) ?? []).find((candidate) => candidate.id === from.id);
                expect(item, `the Form holds the visible row #${from.id}`).toBeDefined();
                expect(item!.related_transaction_id != null, `related_transaction_id = ${item!.related_transaction_id}`).toBe(leg);
            });

            // ---------------------------------------------------------------
            // C22b — a reset after «Split pair» on a saved pair
            // ---------------------------------------------------------------

            type C22bPayload = C21Payload & {splits?: Array<{id_a: number; id_b: number}>};

            /** The splits of a payload, as sorted id pairs. */
            function splitsOf(body: C22bPayload): number[][] {
                return (body.splits ?? []).map((split) => [split.id_a, split.id_b].sort((a, b) => a - b));
            }

            /** Whether a row's menu offers «Reset row»; the menu is closed again before returning. */
            async function offersReset(row: HTMLElement): Promise<boolean> {
                await openMenu(row);
                expect(screen.getByTestId('context-menu-action-edit-single'), 'barrier: the menu is drawn').toBeInTheDocument();
                const offered = screen.queryByTestId('context-menu-action-reset') !== null;
                await fireEvent.keyDown(window, {key: 'Escape'});
                await settle();
                await waitFor(() => expect(screen.queryByTestId('context-menu'), 'the menu closed').toBeNull());
                return offered;
            }

            /**
             * The saved CASH_TRANSFER pair (L_W the sender, L_D the receiver) split with «Split pair», then the note of
             * `edited` changed in its own Form — a split half that is not edited is `original`, and neither «Reset row»
             * nor «Reset selected» is offered on an `original` row. The push is the row the Form was handed (its post-split
             * type), only the note changed. Ends on two rows, the split queued, the edited half `edited`. `read` answers the
             * charges read (C22c: a saved parent in `extra` with its saved FEE).
             */
            async function openSplitAndEdit(edited: TXReadItem, extra: readonly TXReadItem[] = [], read: TXReadItem[] = []): Promise<void> {
                answerChargesRead(read);
                txStoreSetAll([L_W, L_D, ...extra], []);
                mountEditor({action: 'edit', txIds: [L_D.id, L_W.id, ...extra.map((tx) => tx.id)]});
                await waitFor(() => expect(rowsShowing(L_W.id, L_D.id), 'premise: the saved pair is one row').toHaveLength(1));
                for (const tx of extra) await waitFor(() => expect(rowsOf(tx.id), `premise: #${tx.id} is a row on screen`).toHaveLength(1));
                const pair = rowsShowing(L_W.id, L_D.id)[0];
                // The ID cell of a pair names the row's own id first, then its hidden partner's (`renderDualHtml`).
                const ids = idCellText(pair);
                expect(ids.indexOf(`#${L_W.id}`), `premise: the saved WITHDRAWAL (the sender) is the visible half — ${ids}`).toBeLessThan(ids.indexOf(`#${L_D.id}`));
                expect(rowStatus(pair), 'premise: the pair is as saved').toBe('original');

                await rowAction(pair, 'split');
                expect(rowsShowing(L_W.id, L_D.id), 'premise: «Split pair» shows two rows').toHaveLength(2);
                expect(rowsOf(L_W.id), 'premise: the WITHDRAWAL is a row of its own').toHaveLength(1);
                expect(rowsOf(L_D.id), 'premise: the DEPOSIT is a row of its own').toHaveLength(1);
                expect(screen.queryByTestId('split-queued-badge'), 'premise: the split is queued (badge)').not.toBeNull();
                // The status cell of a split-queued half says `split` whatever its fields: «edited» is read from the menu.
                expect(rowStatus(gridRow(L_W.id)), 'premise: the WITHDRAWAL is marked split').toBe('split');
                expect(rowStatus(gridRow(L_D.id)), 'premise: the DEPOSIT is marked split').toBe('split');
                const queued = (await validateNow()) as C22bPayload;
                expect(splitsOf(queued), `premise: one split queued, the saved pair — ${JSON.stringify(queued.splits)}`).toEqual([[L_W.id, L_D.id].sort((a, b) => a - b)]);

                await editHalfNote(edited, 'C22b note changed');
            }

            /**
             * The note of a split half changed in its own Form: the push is the row the Form was handed (its post-split
             * type), only the note changed. Ends on the half offering «Reset row», its note in the payload, the split
             * still queued.
             */
            async function editHalfNote(half: TXReadItem, note: string): Promise<void> {
                await rowAction(gridRow(half.id), 'edit-single');
                await waitFor(() => expect(formProbe().open, 'premise: the Form of the half is open').toBe(true));
                const item = ((formProbe().items as TXReadItem[] | null) ?? []).find((candidate) => candidate.id === half.id);
                expect(item, `premise: the Form holds #${half.id}`).toBeDefined();
                await push({broker_id: item!.broker_id, type: item!.type, date: item!.date, quantity: item!.quantity, asset_id: item!.asset_id, cash: item!.cash, tags: item!.tags ?? [], description: note});
                expect(await offersReset(gridRow(half.id)), `premise: the edited half #${half.id} offers «Reset row»`).toBe(true);
                const withEdit = (await validateNow()) as C22bPayload;
                expect(
                    (withEdit.updates ?? []).some((update) => update.id === half.id && update.description === note),
                    `premise: the note change of #${half.id} is sent — ${JSON.stringify(withEdit.updates)}`,
                ).toBe(true);
                expect(splitsOf(withEdit), 'premise: the split is still queued').toHaveLength(1);
            }

            // Red today: `handleSplitRow` (case A) queues `{id_a, id_b}` in `pendingSplits`; «Reset row» and «Reset selected»
            // reach `resetRows` → `resetOne`, which reads the row back from the store and `collapsePairedOps` joins the pair
            // again, but the split stays queued — the grid shows one row while the payload still splits it. Only «Reset all»
            // empties `pendingSplits`. Expected (C22, nothing queued that the grid does not show): the split undone.
            it.each([
                ['«Reset row» on the half visible before the split (the WITHDRAWAL)', 'row', 'sender'],
                ['«Reset row» on the half the split made visible (the DEPOSIT)', 'row', 'receiver'],
                ['both halves ticked, «Reset selected» (the DEPOSIT edited)', 'selected', 'receiver'],
            ] as const)('C22b: a saved pair split, one half edited, then %s — no split queued, the pair one row as saved', async (_label, door, half) => {
                const edited = half === 'sender' ? L_W : L_D;
                await openSplitAndEdit(edited);
                if (door === 'row') {
                    await rowAction(gridRow(edited.id), 'reset');
                } else {
                    await setTicked(gridRow(L_W.id), true);
                    await setTicked(gridRow(L_D.id), true);
                    const reset = screen.queryByTestId('tx-bulk-reset-selected');
                    expect(reset, 'premise: «Reset selected» is offered (one ticked half is edited)').not.toBeNull();
                    expect(await clickCollectingErrors(reset!), '«Reset selected» throws nothing').toEqual([]);
                }

                const rows = rowsShowing(L_W.id, L_D.id);
                expect.soft(rows, 'the pair is one row again').toHaveLength(1);
                if (rows.length === 1) expect.soft(rowStatus(rows[0]), 'C22b: the pair is back as saved (today its status cell still says split)').toBe('original');
                expect.soft(screen.queryByTestId('split-queued-badge'), 'C22b: no split badge — the grid shows no split').toBeNull();
                const body = (await validateNow()) as C22bPayload;
                expect.soft(splitsOf(body), `C22b: the reset left a split in the queue that the grid no longer shows — ${JSON.stringify(body.splits)}`).toEqual([]);
                expect
                    .soft(
                        (body.updates ?? []).filter((update) => update.id === L_W.id || update.id === L_D.id),
                        'no update of the saved halves: they are back as saved',
                    )
                    .toEqual([]);
            });

            // Green with `resetRows`' `undone` halves. Without them `resetOne` would reset only the chosen half (a split
            // half has no `pairedWith` partner, so `getPartnerOp` finds none), then `collapsePairedOps` would join the
            // pair again with the other half still holding its edit: its post-split type and its note would be sent as
            // an update, on the visible half (WITHDRAWAL kept) or on the hidden one (DEPOSIT kept).
            it.each([
                ['the WITHDRAWAL', 'sender'],
                ['the DEPOSIT', 'receiver'],
            ] as const)('C22b: a saved pair split, both halves edited, «Reset row» on %s only — no split queued, the pair one row as saved, no update of either half', async (_label, half) => {
                await openSplitAndEdit(L_W);
                await editHalfNote(L_D, 'C22b other note changed');
                expect(await offersReset(gridRow(L_W.id)), 'premise: the WITHDRAWAL still offers «Reset row»').toBe(true);
                const both = (await validateNow()) as C22bPayload;
                expect(
                    (both.updates ?? []).filter((update) => update.id === L_W.id || update.id === L_D.id).map((update) => [update.id, update.description]),
                    `premise: both halves are sent with their notes — ${JSON.stringify(both.updates)}`,
                ).toEqual(
                    expect.arrayContaining([
                        [L_W.id, 'C22b note changed'],
                        [L_D.id, 'C22b other note changed'],
                    ]),
                );
                expect(splitsOf(both), 'premise: the split is still queued').toHaveLength(1);

                await rowAction(gridRow(half === 'sender' ? L_W.id : L_D.id), 'reset');

                const rows = rowsShowing(L_W.id, L_D.id);
                expect.soft(rows, 'the pair is one row again').toHaveLength(1);
                if (rows.length === 1) expect.soft(rowStatus(rows[0]), 'C22b: the pair is back as saved').toBe('original');
                expect.soft(screen.queryByTestId('split-queued-badge'), 'C22b: no split badge').toBeNull();
                const body = (await validateNow()) as C22bPayload;
                expect.soft(splitsOf(body), `C22b: a split left in the queue — ${JSON.stringify(body.splits)}`).toEqual([]);
                expect(
                    (body.updates ?? []).filter((update) => update.id === L_W.id || update.id === L_D.id),
                    'C22b: no update of either half: the other half was reset too, its post-split type and its note dropped',
                ).toEqual([]);
            });

            /** How a charge row looks on screen: where it sits, its badge, its status; or how many rows show it. */
            function lookOf(rows: HTMLElement[]): string {
                if (rows.length !== 1) return `${rows.length} rows on screen`;
                const under = chargeOfCell(rows[0]);
                return [under === null ? 'top level' : `under ${under}`, `badge ${chargeState(rows[0]) ?? 'none'}`, `status ${rowStatus(rows[0]) ?? 'none'}`].join(', ');
            }

            /** A saved charge back exactly as saved with no saved parent: its own row, no badge, `original`. */
            const AS_SAVED = 'top level, badge none, status original';

            // A saved pair split here is no pair leg (`isPairLeg`, `pairIdOf`), so «Link» accepts a split half as a
            // parent. A reset that undoes the split joins the pair again, whichever door undoes it: the charge must not
            // stay linked to what is now a leg (rule 8) and no split may stay queued. 66 C22c (consultant, 20/11): the
            // FEE — saved with no parent — was only linked here, so the link is dropped (`chargeOf`), never turned into
            // an «unlink» (`parentUnlink` is for a charge cut from its SAVED parent): it comes back exactly as saved, a top
            // level row with no badge, `original`, nothing sent. Both halves are reset by every door (`resetRows`'
            // `undone` halves); in (b2) the DEPOSIT, the FEE's owner, is reset second.
            // The DEPOSIT is edited first in every case: a saved split half keeps the pair's type (CASH_TRANSFER) until
            // its Form hands it its own (`handleSplitRow`, case A), and a CASH_TRANSFER has no charge role, so «Link» is
            // not offered on an untouched split half. (b2) then edits the WITHDRAWAL and resets from it.
            // C22c flips this case's last C22b assertion: the FEE was expected «unlink» (C21 §5.2 applied as is); it is now
            // expected back as saved, with no badge. Red today on that line: `keepUnlinkedFromUnfitParents` sets
            // `parentUnlink` on it.
            it.each([
                ['«Reset row» on the DEPOSIT (the FEE’s owner)', 'row-deposit'],
                ['the WITHDRAWAL edited too, «Reset row» on it (the half that does not own the FEE)', 'row-withdrawal'],
                ['both halves ticked, «Reset selected»', 'selected'],
            ] as const)('C22b: a saved FEE linked by «Link» to the split DEPOSIT, the DEPOSIT edited, then %s — no split queued, no update of the FEE, the FEE back as saved (no badge), one pair notify', async (_label, door) => {
                await openSplitAndEdit(L_D, [FREE]);
                await linkRows(gridRow(L_D.id), gridRow(FREE.id));
                expect(chargeOfCell(gridRow(FREE.id)), 'premise: the FEE sits under the split DEPOSIT').toBe(gridRow(L_D.id).getAttribute('data-row-id'));
                expect(await offersReset(gridRow(L_D.id)), 'premise: the DEPOSIT still offers «Reset row»').toBe(true);
                if (door === 'row-withdrawal') await editHalfNote(L_W, 'C22b withdrawal note changed');
                const linked = (await validateNow()) as C22bPayload;
                expect(
                    (linked.updates ?? []).filter((update) => update.id === FREE.id).map((update) => update.parent_transaction_id),
                    `premise: the FEE is sent under the split DEPOSIT — ${JSON.stringify(linked.updates)}`,
                ).toEqual([L_D.id]);
                expect(splitsOf(linked), 'premise: the split is still queued').toHaveLength(1);

                const since = eventSeq();
                await clearToasts();
                if (door !== 'selected') {
                    await rowAction(gridRow(door === 'row-deposit' ? L_D.id : L_W.id), 'reset');
                } else {
                    // The selection is the two halves, nothing else: «Link» cleared its own (`confirmLinkPanel`). 66 TL-4:
                    // the FEE, now a charge row, has a checkbox too — what matters is that it is not ticked.
                    expect(gridRow(FREE.id), 'premise: the linked FEE, a charge row, is not selected').toHaveAttribute('data-selected', 'false');
                    await setTicked(gridRow(L_W.id), true);
                    await setTicked(gridRow(L_D.id), true);
                    const reset = screen.queryByTestId('tx-bulk-reset-selected');
                    expect(reset, 'premise: «Reset selected» is offered (one ticked half is edited)').not.toBeNull();
                    expect(await clickCollectingErrors(reset!), '«Reset selected» throws nothing').toEqual([]);
                }

                const body = (await validateNow()) as C22bPayload;
                expect.soft(splitsOf(body), `C22b: a split left in the queue — ${JSON.stringify(body.splits)}`).toEqual([]);
                expect.soft(rowsShowing(L_W.id, L_D.id), 'C22b: the pair is one row again').toHaveLength(1);
                expect
                    .soft(
                        (body.updates ?? []).filter((update) => update.id === FREE.id && (update.parent_transaction_id === L_D.id || update.parent_transaction_id === L_W.id)),
                        `C22b: the FEE is sent under a leg of the pair again (rule 8) — ${JSON.stringify(body.updates)}`,
                    )
                    .toEqual([]);
                // The FEE has no saved parent: its «unlink» sends nothing, so no update of the FEE at all.
                expect
                    .soft(
                        (body.updates ?? []).filter((update) => update.id === FREE.id),
                        `C22b: an update of the FEE is sent — ${JSON.stringify(body.updates)}`,
                    )
                    .toEqual([]);
                // C22c: the link was pending, so it is dropped: the FEE is back as saved (it was «unlink» in C22b). The
                // pair is still named once, by the notify the reset raises today.
                expect.soft(lookOf(rowsOf(FREE.id)), 'C22c: the FEE is back as saved — a top-level row, no «unlink» badge, original (today it stays «unlink»)').toBe(AS_SAVED);
                expect.soft(eventsSince(since, 'tx.bulk.reset.charge.kept-unlinked'), 'C22b: exactly one «half of a pair» notify').toHaveLength(1);
                expect.soft(screen.getByTestId('tx-bulk-commit'), 'C22c: nothing left to save — «Save all» off').toBeDisabled();
            });

            // ---------------------------------------------------------------
            // C22c — «unlink» only from a SAVED parent; a pending link is undone by dropping it
            // ---------------------------------------------------------------

            /** A saved DEPOSIT out of the Bulk (in the store, not in the intent): the Form picker's `_parent_link` target. */
            const OUTSIDE = savedCash(92_531, 'DEPOSIT', 77, '70.000000', 'C22c outside parent');

            /** A charge's own Form, from its row menu; ends on the Form open on it. */
            async function openOwnForm(tx: TXReadItem): Promise<void> {
                await rowAction(gridRow(tx.id), 'edit-single');
                await waitFor(() => {
                    expect(formProbe().open, `the Form of #${tx.id} is open`).toBe(true);
                    expect((formProbe().items as FormItem[] | null)?.[0]?.id, `on #${tx.id}`).toBe(tx.id);
                });
            }

            /** A parent's group opened by its chip (a no-op when open); ends on the group open. */
            async function openGroupOf(parent: TXReadItem): Promise<void> {
                const chip = chipOfRow(gridRow(parent.id));
                expect(chip, `premise: #${parent.id} carries the chip of its charges`).not.toBeNull();
                if (chip!.getAttribute('aria-expanded') !== 'true') {
                    await fireEvent.click(chip!);
                    await settle();
                }
                expect(chipOfRow(gridRow(parent.id)), `premise: the group of #${parent.id} is open`).toHaveAttribute('aria-expanded', 'true');
            }

            /** The updates of a payload for one id. */
            function updatesOf(body: C21Payload, id: number): Array<Record<string, unknown>> {
                return (body.updates ?? []).filter((update) => update.id === id);
            }

            /** The lone DEPOSIT D0 (W0 is not loaded: no pair) and FREE, both as saved; ends on both rows on screen. */
            async function openLoneDepositAndFree(): Promise<void> {
                answerChargesRead([]);
                txStoreSetAll([D0, FREE, OUTSIDE], []);
                mountEditor({action: 'edit', txIds: [D0.id, FREE.id]});
                await waitFor(() => expect(rowsOf(FREE.id), 'premise: both rows are on screen').toHaveLength(1));
                expect(rowsOf(D0.id), 'premise: the DEPOSIT is a row').toHaveLength(1);
                expect(lookOf(rowsOf(FREE.id)), 'premise: FREE as saved').toBe(AS_SAVED);
            }

            /** FREE linked to D0, pending: by «Link» in the toolbar, or by its Form's picker (`_parent_link`). Ends on FREE
             *  under D0, sent with D0 as its parent. */
            async function linkFreeToD0(how: 'link' | 'picker'): Promise<void> {
                if (how === 'link') {
                    await linkRows(gridRow(D0.id), gridRow(FREE.id));
                } else {
                    await openOwnForm(FREE);
                    await push(savedPayload(FREE, {_parent_link: D0.id}));
                }
                expect(chargeOfCell(gridRow(FREE.id)), 'premise: FREE sits under D0').toBe(gridRow(D0.id).getAttribute('data-row-id'));
                const linked = (await validateNow()) as C21Payload;
                expect(updatesOf(linked, FREE.id), `premise: FREE is sent under D0 — ${JSON.stringify(linked.updates)}`).toEqual([{id: FREE.id, parent_transaction_id: D0.id}]);
            }

            // Case 4. Red today: `_parent_unlink` sets `parentUnlink` and keeps `chargeOf`, so FREE becomes a top-level row
            // with the «unlink» badge, an unlink that changes nothing saved (nothing is sent). Expected: the pending link
            // dropped, FREE exactly as saved, nothing to save.
            it.each([
                ['«Link» in the toolbar', 'link'],
                ['its own Form’s picker (_parent_link)', 'picker'],
            ] as const)('C22c: FREE linked to a saved lone DEPOSIT by %s, then «unlink» in FREE’s own Form — FREE back as saved: no badge, original, no update; «Save all» off', async (_label, how) => {
                await openLoneDepositAndFree();
                await linkFreeToD0(how);

                await openOwnForm(FREE);
                await push(savedPayload(FREE, {_parent_unlink: true}));

                expect.soft(lookOf(rowsOf(FREE.id)), 'C22c: FREE is back as saved (today: the «unlink» badge, with nothing to unlink)').toBe(AS_SAVED);
                const body = (await validateNow()) as C21Payload;
                expect.soft(updatesOf(body, FREE.id), `C22c: no update of FREE — ${JSON.stringify(body.updates)}`).toEqual([]);
                expect.soft(updatesOf(body, D0.id), 'the DEPOSIT is untouched').toEqual([]);
                expect.soft(screen.getByTestId('tx-bulk-commit'), 'C22c: nothing left to save — «Save all» off').toBeDisabled();
            });

            // Coordinator's extra case: a pending link held as `parentLinkId` (the picker naming a saved row out of the
            // Bulk), then «unlink» in the same Form. Expected: the pending link dropped, FREE as saved, nothing sent.
            it('C22c: FREE’s Form picker links it to a saved DEPOSIT out of the Bulk (parentLinkId), then «unlink» in its Form — FREE back as saved: no badge, original, no update; «Save all» off', async () => {
                await openLoneDepositAndFree();
                await openOwnForm(FREE);
                await push(savedPayload(FREE, {_parent_link: OUTSIDE.id}));
                const linked = (await validateNow()) as C21Payload;
                expect(updatesOf(linked, FREE.id), `premise: FREE is sent under the DEPOSIT out of the Bulk — ${JSON.stringify(linked.updates)}`).toEqual([{id: FREE.id, parent_transaction_id: OUTSIDE.id}]);

                await openOwnForm(FREE);
                await push(savedPayload(FREE, {_parent_unlink: true}));

                expect.soft(lookOf(rowsOf(FREE.id)), 'C22c: FREE is back as saved').toBe(AS_SAVED);
                const body = (await validateNow()) as C21Payload;
                expect.soft(updatesOf(body, FREE.id), `C22c: no update of FREE — ${JSON.stringify(body.updates)}`).toEqual([]);
                expect.soft(screen.getByTestId('tx-bulk-commit'), 'C22c: nothing left to save — «Save all» off').toBeDisabled();
            });

            // Case 3, `applyDeleteChoice` ~450 (`ownerStaysDeleted`). The brief's route («Keep charges» on the parent, then
            // «Restore» FREE) cannot reach it: «Keep» already drops a pending link (~434, guard below) and leaves FREE not
            // «del», so there is nothing to restore. Reached instead with FREE «del» while still under the DEPOSIT: «Delete
            // all» on the DEPOSIT, or FREE «del» first and the DEPOSIT after. Red today: «Restore» sets `parentUnlink` (the
            // «unlink» badge, nothing sent). Expected: the pending link dropped, FREE as saved; the DEPOSIT stays «del».
            it.each([
                ['«Delete all» on the DEPOSIT', 'all'],
                ['FREE «del» first, then the DEPOSIT «del»', 'charge-first'],
            ] as const)('C22c: FREE linked by «Link» to a saved lone DEPOSIT, both «del» (%s), then «Restore» on FREE alone — FREE back as saved, no update; the DEPOSIT stays «del»', async (_label, route) => {
                await openLoneDepositAndFree();
                await linkFreeToD0('link');
                if (route === 'all') {
                    await rowAction(gridRow(D0.id), 'mark-delete');
                    const content = await screen.findByTestId('tx-charges-modal-content');
                    await fireEvent.click(within(content).getByTestId('tx-charges-modal-all'));
                    await settle();
                    await waitFor(() => expect(screen.queryByTestId('tx-charges-modal-content'), 'the panel closed').toBeNull());
                } else {
                    await rowAction(gridRow(FREE.id), 'mark-delete');
                    expect(chargeState(gridRow(FREE.id)), 'premise: FREE is «del»').toBe('del');
                    await rowAction(gridRow(D0.id), 'mark-delete');
                    expect(screen.queryByTestId('tx-charges-modal-content'), 'premise: no linked charge left, no panel').toBeNull();
                }
                expect(rowStatus(gridRow(D0.id)), 'premise: the DEPOSIT is «del»').toBe('delete');
                expect(chargeState(gridRow(FREE.id)), 'premise: FREE is «del», under the DEPOSIT').toBe('del');

                await rowAction(gridRow(FREE.id), 'mark-delete');

                expect.soft(rowStatus(gridRow(D0.id)), 'the DEPOSIT stays «del»').toBe('delete');
                expect.soft(lookOf(rowsOf(FREE.id)), 'C22c: FREE is back as saved (today: «unlink» under the DEPOSIT «del»)').toBe(AS_SAVED);
                const body = (await validateNow()) as C21Payload;
                expect.soft(updatesOf(body, FREE.id), `C22c: no update of FREE — ${JSON.stringify(body.updates)}`).toEqual([]);
                expect.soft(body.deletes ?? [], 'the DEPOSIT alone is deleted').toEqual([D0.id]);
            });

            // Guard 5(b), green today (`applyDeleteChoice` ~434): «Keep charges» on a parent whose charge was only linked
            // here drops the link. Its siblings: «a linkNew charge with «Keep» only loses the local link» (F7-c2, through
            // the parent's Form) and `bulkCharges.test.ts` «a linkNew charge (linked here, saved under no parent): «keep»
            // only drops the local link». This one goes through «Link» and asserts the whole as-saved look.
            it('C22c guard: FREE linked by «Link» to a saved lone DEPOSIT, the DEPOSIT «del» with «Keep charges» — FREE back as saved, no update', async () => {
                await openLoneDepositAndFree();
                await linkFreeToD0('link');
                await rowAction(gridRow(D0.id), 'mark-delete');
                const content = await screen.findByTestId('tx-charges-modal-content');
                await fireEvent.click(within(content).getByTestId('tx-charges-modal-keep'));
                await settle();
                await waitFor(() => expect(screen.queryByTestId('tx-charges-modal-content'), 'the panel closed').toBeNull());

                expect(rowStatus(gridRow(D0.id)), 'the DEPOSIT is «del»').toBe('delete');
                expect(lookOf(rowsOf(FREE.id)), 'FREE is back as saved').toBe(AS_SAVED);
                const body = (await validateNow()) as C21Payload;
                expect(updatesOf(body, FREE.id), `no update of FREE — ${JSON.stringify(body.updates)}`).toEqual([]);
                expect(body.deletes ?? [], 'the DEPOSIT alone is deleted').toEqual([D0.id]);
            });

            // Guard 5(c), green today (`applyChargeDrafts`, `linkNew` + `unlink`): the parent's Form unlinking a chip linked
            // only here drops the link. No other test of the Bulk reaches that branch.
            it('C22c guard: FREE linked by «Link» to a saved lone DEPOSIT, then «unlink» on its chip in the DEPOSIT’s Form (linkNew) — FREE back as saved, no update; «Save all» off', async () => {
                await openLoneDepositAndFree();
                await linkFreeToD0('link');
                await rowAction(gridRow(D0.id), 'edit-single');
                await waitForParentForm(D0.id, 1);
                expect(handedDrafts()[0], 'premise: FREE is handed as a link made here').toMatchObject({id: FREE.id, linkNew: true, state: 'linked'});

                await push(savedPayload(D0, {_charges: handedDrafts().map((draft): ChargeDraft => ({...draft, state: 'unlink'}))}));

                expect(lookOf(rowsOf(FREE.id)), 'FREE is back as saved').toBe(AS_SAVED);
                const body = (await validateNow()) as C21Payload;
                expect(updatesOf(body, FREE.id), `no update of FREE — ${JSON.stringify(body.updates)}`).toEqual([]);
                expect(screen.getByTestId('tx-bulk-commit'), 'nothing left to save — «Save all» off').toBeDisabled();
            });

            // Guard 5(a), green today: a charge cut from its SAVED parent in its own Form is a real «unlink»: badge, and
            // `parent_transaction_id: 0`. Only the Form side had a test (`TransactionFormModal.parent.test.ts`, «Bulk-hosted
            // charge: Unlink marks it unlinked…»); this is the Bulk side.
            it('C22c guard: FEE_D, saved under the DEPOSIT, «unlink» in its own Form — the «unlink» badge, and parent_transaction_id 0 sent', async () => {
                await openDepositWithFee();
                await openGroupOf(DEP);
                await openOwnForm(FEE_D);

                await push(savedPayload(FEE_D, {_parent_unlink: true}));

                expect(chargeState(gridRow(FEE_D.id)), 'the FEE is «unlink»').toBe('unlink');
                expect(chargeOfCell(gridRow(FEE_D.id)), 'a top-level row').toBeNull();
                const body = (await validateNow()) as C21Payload;
                expect(updatesOf(body, FEE_D.id)).toEqual([{id: FEE_D.id, parent_transaction_id: 0}]);
            });

            // -----------------------------------------------------------------
            // C22c — «Undo split» and a reset with a charge linked to a split half
            // -----------------------------------------------------------------

            /** «Undo split» from this half's row menu; ends on the pair one row and no split queued. */
            async function undoSplitFrom(half: TXReadItem): Promise<void> {
                await rowAction(gridRow(half.id), 'undo-split');
                expect(rowsShowing(L_W.id, L_D.id), '«Undo split» joins the pair again: one row').toHaveLength(1);
            }

            /** Warning toasts naming the `paired` reason of «Link». */
            async function pairedToasts(): Promise<string[]> {
                const pattern = pairedReason();
                expect(pattern.source, 'premise: the paired reason key resolves in the catalogue').not.toContain('chargesLink');
                return (await toastMessages()).filter((message) => pattern.test(message));
            }

            // Case 2. Red today: «Undo split» only drops the split and hides the partner again; FREE keeps `chargeOf` the
            // DEPOSIT, now a leg — a top-level row (rule 8 of `isUnderParent`) that the payload still sends under the leg
            // (`parent_transaction_id: 92521`, refused by the backend), and nothing is notified. Expected, as the reset
            // (C22c): the pending link dropped, FREE as saved, one notify `tx.bulk.undo-split.charge.kept-unlinked` with the
            // `paired` toast (no new key). The DEPOSIT's own edit stays: «Undo split» resets nothing.
            it.each([
                ['the DEPOSIT (FREE’s owner)', 'dep'],
                ['the WITHDRAWAL', 'wd'],
            ] as const)('C22c: FREE linked by «Link» to the split DEPOSIT, then «Undo split» on %s — FREE back as saved (no link to a leg, no badge, no update), no split, one undo-split notify with the paired toast', async (_label, which) => {
                await openSplitAndEdit(L_D, [FREE]);
                await linkRows(gridRow(L_D.id), gridRow(FREE.id));
                expect(chargeOfCell(gridRow(FREE.id)), 'premise: FREE sits under the split DEPOSIT').toBe(gridRow(L_D.id).getAttribute('data-row-id'));
                const since = eventSeq();
                await clearToasts();

                await undoSplitFrom(which === 'dep' ? L_D : L_W);

                const body = (await validateNow()) as C22bPayload;
                expect.soft(splitsOf(body), `C22c: «Undo split» left a split queued — ${JSON.stringify(body.splits)}`).toEqual([]);
                expect
                    .soft(
                        updatesOf(body, FREE.id).filter((update) => update.parent_transaction_id === L_D.id || update.parent_transaction_id === L_W.id),
                        `C22c: FREE is sent under a leg of the pair (rule 8) — ${JSON.stringify(body.updates)}`,
                    )
                    .toEqual([]);
                expect.soft(updatesOf(body, FREE.id), `C22c: an update of FREE is sent — ${JSON.stringify(body.updates)}`).toEqual([]);
                expect.soft(lookOf(rowsOf(FREE.id)), 'C22c: FREE is back as saved').toBe(AS_SAVED);
                expect.soft(eventsSince(since, 'tx.bulk.undo-split.charge.kept-unlinked'), 'C22c: one notify tx.bulk.undo-split.charge.kept-unlinked').toHaveLength(1);
                expect.soft(await pairedToasts(), 'C22c: one toast with the paired reason of «Link»').toHaveLength(1);
            });

            /** A saved DEPOSIT out of the pair, with its saved FEE: the charge whose SAVED parent is not the split half. */
            const P = A;
            const FEE_P = FEE_A;

            /** The saved pair split, the DEPOSIT edited (`openSplitAndEdit`), P loaded with FEE_P read under it; FEE_P
             *  «unlink» from P in its own Form. Ends on FEE_P a top-level row with the «unlink» badge. */
            async function openSavedParentFeeUnlinked(): Promise<void> {
                await openSplitAndEdit(L_D, [P], [FEE_P]);
                await waitFor(() => expect(chipOfRow(gridRow(P.id)), 'premise: FEE_P is read under P').toHaveAttribute('data-charges-count', '1'));
                await openGroupOf(P);
                await openOwnForm(FEE_P);
                await push(savedPayload(FEE_P, {_parent_unlink: true}));
                expect(lookOf(rowsOf(FEE_P.id)), 'premise: FEE_P is «unlink» from P, a top-level row').toBe('top level, badge unlink, status edited');
            }

            /**
             * The saved pair split, the DEPOSIT edited (`openSplitAndEdit`), P loaded with FEE_P read under it; FEE_P
             * «unlink» from P in its own Form, then linked by «Link» to the split DEPOSIT. Ends on FEE_P under the split
             * DEPOSIT, sent with it as its parent.
             */
            async function openSavedParentFeeLinkedToHalf(): Promise<void> {
                await openSavedParentFeeUnlinked();
                await linkRows(gridRow(L_D.id), gridRow(FEE_P.id));
                expect(chargeOfCell(gridRow(FEE_P.id)), 'premise: FEE_P sits under the split DEPOSIT').toBe(gridRow(L_D.id).getAttribute('data-row-id'));
                const linked = (await validateNow()) as C22bPayload;
                expect(updatesOf(linked, FEE_P.id), `premise: FEE_P is sent under the split DEPOSIT — ${JSON.stringify(linked.updates)}`).toEqual([{id: FEE_P.id, parent_transaction_id: L_D.id}]);
            }

            // Consultant's default (a), 20/11: a FEE whose SAVED parent is P, unlinked from P, then linked to a split half
            // and that half reset (or the split undone): the link to the leg goes, the unlink from P stays — the «unlink»
            // badge is true here, and `parent_transaction_id: 0` is sent. The reset raises `tx.bulk.reset.charge.kept-unlinked`,
            // «Undo split» `tx.bulk.undo-split.charge.kept-unlinked`, both with the `paired` toast.
            it.each([
                ['«Reset row» on the split DEPOSIT', 'reset'],
                ['«Undo split» on the DEPOSIT', 'undo-dep'],
                ['«Undo split» on the WITHDRAWAL', 'undo-wd'],
            ] as const)('C22c: a FEE saved under P, «unlink» in its Form, «Link» to the split DEPOSIT, then %s — FEE «unlink» from P, parent_transaction_id 0, no link to a leg, one notify', async (_label, door) => {
                await openSavedParentFeeLinkedToHalf();
                const since = eventSeq();
                await clearToasts();

                if (door === 'reset') await rowAction(gridRow(L_D.id), 'reset');
                else await undoSplitFrom(door === 'undo-dep' ? L_D : L_W);

                const body = (await validateNow()) as C22bPayload;
                expect.soft(splitsOf(body), `C22c: a split left in the queue — ${JSON.stringify(body.splits)}`).toEqual([]);
                expect.soft(updatesOf(body, FEE_P.id), `C22c: FEE_P is sent unlinked from P, and only that — ${JSON.stringify(body.updates)}`).toEqual([{id: FEE_P.id, parent_transaction_id: 0}]);
                expect.soft(lookOf(rowsOf(FEE_P.id)), 'C22c: FEE_P is a top-level row with the «unlink» badge').toBe(`top level, badge unlink, status edited`);
                const event = door === 'reset' ? 'tx.bulk.reset.charge.kept-unlinked' : 'tx.bulk.undo-split.charge.kept-unlinked';
                expect.soft(eventsSince(since, event), `C22c: one notify ${event}`).toHaveLength(1);
                expect.soft(await pairedToasts(), 'C22c: one toast with the paired reason of «Link»').toHaveLength(1);
            });

            // Next to it, a distinct path, green today: «Reset row» on the FEE itself brings it back as saved — under P,
            // linked, nothing sent; the split is untouched. Taken while the FEE is a top-level «unlink» row: once «Link»
            // puts it under the split DEPOSIT it is an indented row, and an indented row's menu offers no «Reset row»
            // (`!indentedIds.has`); «Reset selected» on it is TL-4's own case.
            it('C22c guard: a FEE saved under P, «unlink» in its Form, then «Reset row» on the FEE itself — back under P, linked, nothing sent for it; the split stays queued', async () => {
                await openSavedParentFeeUnlinked();

                await rowAction(gridRow(FEE_P.id), 'reset');

                expect(lookOf(rowsOf(FEE_P.id)), 'FEE_P is back under P, linked, as saved').toBe(`under ${gridRow(P.id).getAttribute('data-row-id')}, badge linked, status original`);
                const body = (await validateNow()) as C22bPayload;
                expect(updatesOf(body, FEE_P.id), `nothing sent for FEE_P — ${JSON.stringify(body.updates)}`).toEqual([]);
                expect(splitsOf(body), 'the split stays queued').toHaveLength(1);
            });

            // Coordinator's extra case: a NEW FEE born in the split DEPOSIT's Form (its charges section), then «Reset row»
            // on that half or «Undo split». Expected: the new FEE stays a new row of its own, with no link to a leg (no
            // `parent_transaction_id`, no `parent_ref` in its create) and no badge. Today: the reset sets `parentUnlink` on
            // it (the «unlink» badge, nothing sent); «Undo split» keeps it `chargeOf` the leg, sent with the leg's id.
            it.each([
                ['«Reset row» on the DEPOSIT', 'reset'],
                ['«Undo split» on the DEPOSIT', 'undo-dep'],
                ['«Undo split» on the WITHDRAWAL', 'undo-wd'],
            ] as const)('C22c: a new FEE born in the split DEPOSIT’s Form, then %s — a new row of its own, no badge, created with no parent', async (_label, door) => {
                await openSplitAndEdit(L_D);
                await rowAction(gridRow(L_D.id), 'edit-single');
                await waitForParentForm(L_D.id, 0);
                const item = formRow()!;
                await push({broker_id: item.broker_id, type: item.type, date: item.date, quantity: item.quantity, asset_id: item.asset_id, cash: item.cash, tags: item.tags ?? [], description: 'C22b note changed', _charges: [newDraft('FEE', '2.000000', 'C22c new fee')]});
                expect(chargeOfCell(gridRowDescribed('C22c new fee')), 'premise: the new FEE sits under the split DEPOSIT').toBe(gridRow(L_D.id).getAttribute('data-row-id'));

                if (door === 'reset') await rowAction(gridRow(L_D.id), 'reset');
                else await undoSplitFrom(door === 'undo-dep' ? L_D : L_W);

                const fresh = gridRows().filter((row) => rowDescription(row) === 'C22c new fee');
                expect.soft(lookOf(fresh), 'C22c: the new FEE is a new row of its own, no badge').toBe('top level, badge none, status new');
                const body = (await validateNow()) as C22bPayload;
                expect.soft(splitsOf(body), `C22c: a split left in the queue — ${JSON.stringify(body.splits)}`).toEqual([]);
                const create = (body.creates ?? []).find((c) => c.description === 'C22c new fee');
                expect(create, `the new FEE is created — ${JSON.stringify(body.creates)}`).toBeDefined();
                expect.soft({parent_transaction_id: create?.parent_transaction_id ?? null, parent_ref: create?.parent_ref ?? null}, `C22c: the new FEE is created with no parent — ${JSON.stringify(create)}`).toEqual({parent_transaction_id: null, parent_ref: null});
            });

            /**
             * The saved pair split, the DEPOSIT edited, then a new FEE typed in the split DEPOSIT's own Form (its charges
             * section), the DEPOSIT pushed with `date`. Ends on the new FEE under the split DEPOSIT.
             */
            async function newFeeInSplitDeposit(date: string = C21_DATE): Promise<void> {
                await openSplitAndEdit(L_D);
                await rowAction(gridRow(L_D.id), 'edit-single');
                await waitForParentForm(L_D.id, 0);
                const item = formRow()!;
                await push({broker_id: item.broker_id, type: item.type, date, quantity: item.quantity, asset_id: item.asset_id, cash: item.cash, tags: item.tags ?? [], description: 'C22b note changed', _charges: [newDraft('FEE', '2.000000', 'C22c new fee')]});
                expect(chargeOfCell(gridRowDescribed('C22c new fee')), 'premise: the new FEE sits under the split DEPOSIT').toBe(gridRow(L_D.id).getAttribute('data-row-id'));
            }

            /** The one create of the new FEE in a payload. */
            function newFeeCreate(body: C22bPayload): Record<string, unknown> | undefined {
                const found = (body.creates ?? []).filter((c) => c.description === 'C22c new fee');
                expect(found, `one create of the new FEE — ${JSON.stringify(body.creates)}`).toHaveLength(1);
                return found[0];
            }

            // Final review, «Reset all»: it drops the half the split made visible (`addedBySplit`) and rebuilds the rest
            // from the store, so the new FEE's owner (the split DEPOSIT's operation) is gone or a hidden leg again. The new
            // FEE must name no leg and no vanished row: a new row of its own, created with no parent; no split queued.
            // Note: a `chargeOf` naming a vanished operation has no DOM or payload trace of its own (`effectiveParentId`
            // and `chargeParentFields` fall through to «no parent»); the row's place and its create are what is observable.
            it('C22c: a new FEE born in the split DEPOSIT’s Form, then «Reset all» — a new row of its own, no badge, created with no parent; no split', async () => {
                await newFeeInSplitDeposit();
                const reset = screen.queryByTestId('tx-bulk-reset-all');
                expect(reset, 'premise: «Reset all» is offered').not.toBeNull();
                expect(await clickCollectingErrors(reset!), '«Reset all» throws nothing').toEqual([]);

                expect.soft(rowsShowing(L_W.id, L_D.id), 'the pair is one row again').toHaveLength(1);
                expect.soft(lookOf(gridRows().filter((row) => rowDescription(row) === 'C22c new fee')), 'C22c: the new FEE is a new row of its own, no badge').toBe('top level, badge none, status new');
                const body = (await validateNow()) as C22bPayload;
                expect.soft(splitsOf(body), `C22c: a split left in the queue — ${JSON.stringify(body.splits)}`).toEqual([]);
                const create = newFeeCreate(body);
                expect.soft({parent_transaction_id: create?.parent_transaction_id ?? null, parent_ref: create?.parent_ref ?? null}, `C22c: the new FEE is created with no parent — ${JSON.stringify(create)}`).toEqual({parent_transaction_id: null, parent_ref: null});
                expect.soft(updatesOf(body, L_W.id).concat(updatesOf(body, L_D.id)), 'the saved halves are back as saved').toEqual([]);
            });

            // Final review, the discriminating date: a new FEE follows its parent's broker, asset and date (`followsParent`)
            // until it leaves it. The split DEPOSIT's date is changed after the FEE was born; «Undo split» then cuts the FEE
            // from what became a leg, and the FEE keeps the date it was following — the new one, not the one it was born
            // with (`unlinkCharge` takes the owner's three fields, as «Keep» does).
            it.each([
                ['the DEPOSIT', 'dep'],
                ['the WITHDRAWAL', 'wd'],
            ] as const)('C22c: a new FEE born in the split DEPOSIT’s Form, the DEPOSIT’s date changed, then «Undo split» on %s — the FEE is created on the new date, with no parent', async (_label, which) => {
                const NEW_DATE = '2026-10-09';
                await newFeeInSplitDeposit();
                await rowAction(gridRow(L_D.id), 'edit-single');
                await waitForParentForm(L_D.id, 1);
                const item = formRow()!;
                await push({broker_id: item.broker_id, type: item.type, date: NEW_DATE, quantity: item.quantity, asset_id: item.asset_id, cash: item.cash, tags: item.tags ?? [], description: 'C22b note changed', _charges: handedDrafts()});
                const followed = newFeeCreate((await validateNow()) as C22bPayload);
                expect(followed?.date, 'premise: the new FEE follows the DEPOSIT’s new date').toBe(NEW_DATE);

                await undoSplitFrom(which === 'dep' ? L_D : L_W);

                const body = (await validateNow()) as C22bPayload;
                const create = newFeeCreate(body);
                expect.soft(create?.date, `C22c: the new FEE keeps the date it was following — ${JSON.stringify(create)}`).toBe(NEW_DATE);
                expect.soft({parent_transaction_id: create?.parent_transaction_id ?? null, parent_ref: create?.parent_ref ?? null}, `C22c: the new FEE is created with no parent — ${JSON.stringify(create)}`).toEqual({parent_transaction_id: null, parent_ref: null});
                expect.soft(lookOf(gridRows().filter((row) => rowDescription(row) === 'C22c new fee')), 'C22c: the new FEE is a new row of its own, no badge').toBe('top level, badge none, status new');
            });

            // ---------------------------------------------------------------
            // C22d — «Link» reads the type the split will give a half
            // ---------------------------------------------------------------

            /**
             * 66 C22d (FEE consultant, 21/11). «Split pair» on a saved pair (`handleSplitRow`, case A) queues the split and
             * leaves each half's `fields.type` the pair's own (CASH_TRANSFER) until its Form hands it one. The Type cell
             * already shows the type the split gives (CASH_TRANSFER → DEPOSIT), and the backend assigns it when it splits
             * (`apply_splits`), checking the rules on the batch's final state (rule 7). «Link» must read that same type:
             * one computation (`splitTypes.ts`, `postSplitType`) for the Type cell, the half's Form and the mirror rows of
             * `bulkLinkSelection`. A type the user picked by hand wins; a split TRANSFER gives two ADJUSTMENT, which are no
             * parents, so «Link» stays hidden. The Type cell's split branch also draws the chip of a half's charges.
             */
            describe('66 C22d: «Link» on a split half reads the type the split will give it', () => {
                /** A saved FEE of nobody on the WITHDRAWAL's broker (88): FREE is on 77, and «Link» wants one broker. */
                const FREE_88 = savedCash(92_541, 'FEE', 88, '-1.500000', 'C22d free fee on 88');
                /** A saved TRANSFER pair of asset 101: the sender on 77 (quantity −5), the receiver on 88. */
                const T_S = savedCash(92_551, 'DEPOSIT', 77, '0', 'C22d asset transfer', {type: 'TRANSFER', asset_id: 101, quantity: '-5.000000', cash: null, related_transaction_id: 92_552, partner_broker_id: 88});
                const T_R = savedCash(92_552, 'DEPOSIT', 88, '0', 'C22d asset transfer', {type: 'TRANSFER', asset_id: 101, quantity: '5.000000', cash: null, related_transaction_id: 92_551, partner_broker_id: 77});

                /** «Link» as the toolbar draws it for the ticked rows: `absent`, `off (<reason>)` or `on`. */
                function linkOffer(): string {
                    const button = screen.queryByTestId('tx-bulk-link-charges');
                    if (!button) return 'absent';
                    return button.getAttribute('aria-disabled') === 'true' ? `off (${button.getAttribute('data-disabled-reason') ?? 'no reason'})` : 'on';
                }

                /** What the chip in a row's Type cell counts, or `no chip`. */
                function chipCount(row: HTMLElement): string {
                    return chipOfRow(row)?.getAttribute('data-charges-count') ?? 'no chip';
                }

                /** The type a split half's Type cell says the split gives it: the slug of its last icon (`renderTypeHtml`,
                 *  `/icons/transactions/<slug>.png`), never its translated label. */
                function typeCellTarget(row: HTMLElement): string | null {
                    const icons = row.querySelectorAll('td[data-column-id="type"] img');
                    const src = icons[icons.length - 1]?.getAttribute('src') ?? '';
                    return (src.match(/\/icons\/transactions\/([a-z-]+)\.png$/) ?? [])[1] ?? null;
                }

                /**
                 * The saved pair `[sender, receiver]` split with «Split pair», neither half edited, `extra` loaded beside
                 * it (no charge read). Ends on two rows, both `split`, the split queued, the receiver offering no
                 * «Reset row» (untouched).
                 */
                async function openSplitUntouched(sender: TXReadItem, receiver: TXReadItem, extra: readonly TXReadItem[] = []): Promise<void> {
                    answerChargesRead([]);
                    txStoreSetAll([sender, receiver, ...extra], []);
                    mountEditor({action: 'edit', txIds: [receiver.id, sender.id, ...extra.map((tx) => tx.id)]});
                    await waitFor(() => expect(rowsShowing(sender.id, receiver.id), 'premise: the saved pair is one row').toHaveLength(1));
                    for (const tx of extra) await waitFor(() => expect(rowsOf(tx.id), `premise: #${tx.id} is a row on screen`).toHaveLength(1));
                    const pair = rowsShowing(sender.id, receiver.id)[0];
                    expect(rowStatus(pair), 'premise: the pair is as saved').toBe('original');

                    await rowAction(pair, 'split');
                    expect(rowsOf(sender.id), 'premise: the sender is a row of its own').toHaveLength(1);
                    expect(rowsOf(receiver.id), 'premise: the receiver is a row of its own').toHaveLength(1);
                    expect(rowStatus(gridRow(sender.id)), 'premise: the sender is marked split').toBe('split');
                    expect(rowStatus(gridRow(receiver.id)), 'premise: the receiver is marked split').toBe('split');
                    expect(await offersReset(gridRow(receiver.id)), 'premise: the receiver is untouched (no «Reset row»)').toBe(false);
                    const queued = (await validateNow()) as C22bPayload;
                    expect(splitsOf(queued), `premise: one split queued, the saved pair — ${JSON.stringify(queued.splits)}`).toEqual([[sender.id, receiver.id].sort((a, b) => a - b)]);
                }

                // Case 1. Red today: the untouched DEPOSIT half still holds CASH_TRANSFER, no charge role, so the mirror
                // row of `bulkLinkSelection` makes the selection `hidden`. Expected: the mirror reads DEPOSIT (the type the
                // split gives the receiver), «Link» on, FREE under the half, and one batch holding the split and the link
                // (the backend splits first, then checks rule 7 on the final state). The chip in the Type cell is the
                // split branch's, which today returns before the chip.
                it('C22d: the saved CASH_TRANSFER pair split, no edit, the DEPOSIT half + FREE ticked — «Link» on; FREE under the half; the split and FREE’s parent in one batch; the half’s chip counts 1', async () => {
                    await openSplitUntouched(L_W, L_D, [FREE]);
                    expect(typeCellTarget(gridRow(L_D.id)), 'premise: the Type cell says the split gives the DEPOSIT half DEPOSIT').toBe('deposit');
                    await setTicked(gridRow(L_D.id), true);
                    await setTicked(gridRow(FREE.id), true);
                    expect(linkOffer(), 'C22d: «Link» reads the type the split gives the untouched half (DEPOSIT, a parent)').toBe('on');

                    await linkRows(gridRow(L_D.id), gridRow(FREE.id));

                    expect(chargeOfCell(gridRow(FREE.id)), 'C22d: FREE sits under the split DEPOSIT').toBe(gridRow(L_D.id).getAttribute('data-row-id'));
                    const body = (await validateNow()) as C22bPayload;
                    expect.soft(splitsOf(body), `C22d: the split is queued in the batch — ${JSON.stringify(body.splits)}`).toEqual([[L_W.id, L_D.id].sort((a, b) => a - b)]);
                    expect.soft(updatesOf(body, FREE.id), `C22d: FREE is sent under the DEPOSIT half, in the same batch — ${JSON.stringify(body.updates)}`).toEqual([{id: FREE.id, parent_transaction_id: L_D.id}]);
                    expect.soft(chipCount(gridRow(L_D.id)), 'C22d: the split DEPOSIT’s Type cell carries the chip of its charge').toBe('1');
                });

                // Case 2. WITHDRAWAL is a parent (`charge_role: "parent"`, `type_metadata.py`, and this file's
                // TYPES_RESPONSE). Red today for the same reason as case 1. FREE is on 77 and the WITHDRAWAL on 88, so the
                // brief's literal pairing gives «Link» off with `otherBroker` once the type is read; FREE_88 (on 88) is
                // the one «Link» accepts. Both are asserted.
                it('C22d: the saved CASH_TRANSFER pair split, no edit, the WITHDRAWAL half + a free FEE on its broker — «Link» on; the FEE under the half, in the split’s batch', async () => {
                    expect(getTypeRule('WITHDRAWAL').chargeRole, 'premise: WITHDRAWAL is a parent type').toBe('parent');
                    await openSplitUntouched(L_W, L_D, [FREE_88]);
                    await setTicked(gridRow(L_W.id), true);
                    await setTicked(gridRow(FREE_88.id), true);
                    expect(linkOffer(), 'C22d: «Link» reads the type the split gives the untouched half (WITHDRAWAL, a parent)').toBe('on');

                    await linkRows(gridRow(L_W.id), gridRow(FREE_88.id));

                    expect(chargeOfCell(gridRow(FREE_88.id)), 'C22d: the FEE sits under the split WITHDRAWAL').toBe(gridRow(L_W.id).getAttribute('data-row-id'));
                    const body = (await validateNow()) as C22bPayload;
                    expect.soft(splitsOf(body), `C22d: the split is queued in the batch — ${JSON.stringify(body.splits)}`).toEqual([[L_W.id, L_D.id].sort((a, b) => a - b)]);
                    expect.soft(updatesOf(body, FREE_88.id), `C22d: the FEE is sent under the WITHDRAWAL half — ${JSON.stringify(body.updates)}`).toEqual([{id: FREE_88.id, parent_transaction_id: L_W.id}]);
                    expect.soft(chipCount(gridRow(L_W.id)), 'C22d: the split WITHDRAWAL’s Type cell carries the chip of its charge').toBe('1');
                });

                it('C22d: the saved CASH_TRANSFER pair split, no edit, the WITHDRAWAL half (broker 88) + FREE (broker 77) — «Link» drawn off with otherBroker', async () => {
                    await openSplitUntouched(L_W, L_D, [FREE]);
                    await setTicked(gridRow(L_W.id), true);
                    await setTicked(gridRow(FREE.id), true);
                    expect(linkOffer(), 'C22d: the WITHDRAWAL half is a parent, FREE on another broker').toBe('off (otherBroker)');
                });

                // Case 3, a guard, green today (the half still holds TRANSFER, no charge role) and after the fix (the split
                // gives ADJUSTMENT, no charge role either). The presence barrier: in the same mount D0 (a lone DEPOSIT on
                // 77) + FREE draw «Link» on; swapping D0 for the TRANSFER sender (77, the FEE's broker) takes it away.
                it('C22d guard: a saved TRANSFER pair split, no edit — the sender half (ADJUSTMENT after the split) + FREE: no «Link»', async () => {
                    await openSplitUntouched(T_S, T_R, [D0, FREE]);
                    await setTicked(gridRow(D0.id), true);
                    await setTicked(gridRow(FREE.id), true);
                    expect(linkOffer(), 'barrier: a DEPOSIT + FREE draw «Link» on').toBe('on');
                    await setTicked(gridRow(D0.id), false);
                    await setTicked(gridRow(T_S.id), true);
                    expect(rowCheckbox(gridRow(FREE.id)), 'premise: FREE still ticked').toHaveAttribute('data-state', 'checked');

                    expect(linkOffer(), 'C22d: an ADJUSTMENT half is no parent — no «Link»').toBe('absent');
                });

                // Case 4. The real Form, on a saved row of the Bulk (`unlockImmutable`), offers the swap group of the type
                // it was handed (`allowedTypes`, `getSwapGroup`): the DEPOSIT half may become a WITHDRAWAL. The Form pushes
                // a WITHDRAWAL's cash signed (−50), and the editor holds a negative-rule cash as its magnitude (W-B65,
                // `applyFormPayload` → `magnitudeForRule`): the half ends as WITHDRAWAL with cash +50. The sign rule
                // (`postSplitTypeForForm`, the Type cell) reads +50 as the receiver, DEPOSIT, and overrides the user;
                // the decision keeps the user's type. «Link» itself reads `fields.type` today, a parent either way, so it
                // is on today and stays on (guard lines); the red lines are the Type cell and the Form handed again.
                // An ADJUSTMENT half (a split TRANSFER) has no swap partner: not reachable there.
                it('C22d: the DEPOSIT half turned WITHDRAWAL in its own Form — the Type cell and the Form read the user’s WITHDRAWAL; + FREE: «Link» on, FREE under it', async () => {
                    await openSplitUntouched(L_W, L_D, [FREE]);
                    await rowAction(gridRow(L_D.id), 'edit-single');
                    await waitFor(() => expect(formProbe().open, 'premise: the Form of the DEPOSIT half is open').toBe(true));
                    const item = ((formProbe().items as TXReadItem[] | null) ?? []).find((candidate) => candidate.id === L_D.id);
                    expect(item?.type, 'premise: the Form is handed the type the split gives (DEPOSIT)').toBe('DEPOSIT');
                    // What the real Form pushes for a WITHDRAWAL: its cash signed negative (`autoNegateCash`).
                    await push({broker_id: item!.broker_id, type: 'WITHDRAWAL', date: item!.date, quantity: item!.quantity, asset_id: item!.asset_id, cash: {code: 'EUR', amount: '-50.000000'}, tags: item!.tags ?? [], description: item!.description});

                    expect.soft(typeCellTarget(gridRow(L_D.id)), 'C22d: the Type cell shows the user’s type, not the one the sign gives').toBe('withdrawal');

                    await setTicked(gridRow(L_D.id), true);
                    await setTicked(gridRow(FREE.id), true);
                    expect(linkOffer(), 'guard: the user’s WITHDRAWAL is a parent — «Link» on').toBe('on');
                    await linkRows(gridRow(L_D.id), gridRow(FREE.id));
                    expect(chargeOfCell(gridRow(FREE.id)), 'guard: FREE sits under the half').toBe(gridRow(L_D.id).getAttribute('data-row-id'));
                    const body = (await validateNow()) as C22bPayload;
                    expect(updatesOf(body, FREE.id), `guard: FREE is sent under the half — ${JSON.stringify(body.updates)}`).toEqual([{id: FREE.id, parent_transaction_id: L_D.id}]);

                    await rowAction(gridRow(L_D.id), 'edit-single');
                    await waitFor(() => expect(formProbe().open, 'the Form of the half is open again').toBe(true));
                    const again = ((formProbe().items as TXReadItem[] | null) ?? []).find((candidate) => candidate.id === L_D.id);
                    expect.soft(again?.type, 'C22d: the Form is handed the user’s type again (today the sign’s DEPOSIT)').toBe('WITHDRAWAL');
                });

                // The chip on the edited path (the C22b/C22c route: the DEPOSIT edited, so «Link» is on today). Red today on
                // its own line: the Type cell's split branch returns before `chargesChipHtml`.
                it('C22d: the split DEPOSIT edited, FREE linked to it by «Link» — the half’s Type cell carries the chip counting 1', async () => {
                    await openSplitAndEdit(L_D, [FREE]);
                    await linkRows(gridRow(L_D.id), gridRow(FREE.id));
                    expect(chargeOfCell(gridRow(FREE.id)), 'premise: FREE sits under the split DEPOSIT').toBe(gridRow(L_D.id).getAttribute('data-row-id'));

                    expect(chipCount(gridRow(L_D.id)), 'C22d: the split DEPOSIT’s Type cell carries the chip of its charge').toBe('1');
                });

                /**
                 * What the batch makes of a saved half: the type and the cash the backend holds once it has split the pair
                 * (`apply_splits` runs first and gives the sender, read on the saved sign, its type) and applied the half's
                 * update (a type sent wins, a cash sent replaces the saved one), plus the splits queued.
                 */
                function savedOutcome(body: C22bPayload, half: TXReadItem, splitType: string): {type: string; cash: number; splits: number[][]} {
                    const update = updatesOf(body, half.id)[0] ?? {};
                    const cash = (update.cash as {amount?: string} | undefined)?.amount ?? half.cash?.amount;
                    return {type: typeof update.type === 'string' ? update.type : splitType, cash: Number(cash), splits: splitsOf(body)};
                }

                // The common route of case 4: only the note of the WITHDRAWAL half changed in its Form. The Form pushes the
                // type it was handed (WITHDRAWAL) with its cash signed (−50); the editor holds it as +50 (W-B65). The type
                // the half holds is now WITHDRAWAL, its own: the Type cell and the Form must keep saying WITHDRAWAL.
                //
                // And what is SAVED, after a first and a second note edit. Before C22d the sign rule read the held +50 as the
                // receiver and handed the Form DEPOSIT on the second opening: the Form pushed DEPOSIT +50, the editor held
                // DEPOSIT +50, and the batch sent `{id: 92522, cash: +50, description}` (its type stripped, the split assigns
                // it; measured on the old modal). Read from the backend's code, not run here: `apply_splits` splits first and
                // `pair_sides` picks the sender on the saved amount (−50 → WITHDRAWAL), so the update writes +50 on a
                // WITHDRAWAL, which rule 11 (`cash_sign: negative`, `cashSignNegative`) refuses. The half must keep cash −50
                // and send no DEPOSIT.
                it('C22d: the split WITHDRAWAL half, only its note edited in its Form, twice — the Type cell and the Form handed again still say WITHDRAWAL; the batch keeps it a WITHDRAWAL with cash −50', async () => {
                    await openSplitUntouched(L_W, L_D);
                    expect(typeCellTarget(gridRow(L_W.id)), 'premise: the Type cell says the split gives the WITHDRAWAL half WITHDRAWAL').toBe('withdrawal');
                    await editHalfNote(L_W, 'C22d note a');
                    const first = (await validateNow()) as C22bPayload;
                    expect.soft(savedOutcome(first, L_W, 'WITHDRAWAL'), `C22d: after the first edit the half is saved a WITHDRAWAL, cash −50 — ${JSON.stringify(first.updates)}`).toEqual({type: 'WITHDRAWAL', cash: -50, splits: [[L_W.id, L_D.id].sort((a, b) => a - b)]});

                    expect.soft(typeCellTarget(gridRow(L_W.id)), 'C22d: the Type cell still shows WITHDRAWAL after a note edit').toBe('withdrawal');
                    await rowAction(gridRow(L_W.id), 'edit-single');
                    await waitFor(() => expect(formProbe().open, 'the Form of the half is open again').toBe(true));
                    const again = ((formProbe().items as TXReadItem[] | null) ?? []).find((candidate) => candidate.id === L_W.id);
                    expect.soft(again?.type, 'C22d: the Form is handed WITHDRAWAL again').toBe('WITHDRAWAL');

                    // The second edit: the Form pushes back what it was handed, only the note changed.
                    await push({broker_id: again!.broker_id, type: again!.type, date: again!.date, quantity: again!.quantity, asset_id: again!.asset_id, cash: again!.cash, tags: again!.tags ?? [], description: 'C22d note b'});
                    const second = (await validateNow()) as C22bPayload;
                    expect(
                        updatesOf(second, L_W.id).some((update) => update.description === 'C22d note b'),
                        `premise: the second note is sent — ${JSON.stringify(second.updates)}`,
                    ).toBe(true);
                    expect.soft(savedOutcome(second, L_W, 'WITHDRAWAL'), `C22d: after the second edit the half is still saved a WITHDRAWAL, cash −50 — ${JSON.stringify(second.updates)}`).toEqual({type: 'WITHDRAWAL', cash: -50, splits: [[L_W.id, L_D.id].sort((a, b) => a - b)]});
                    expect.soft(updatesOf(second, L_W.id), 'C22d: the update of the half is its note alone: no type (the split gives WITHDRAWAL), no cash (the saved −50 stays)').toEqual([{id: L_W.id, description: 'C22d note b'}]);
                    expect.soft(typeCellTarget(gridRow(L_W.id)), 'C22d: the Type cell still shows WITHDRAWAL after the second edit').toBe('withdrawal');
                });

                // «Split pair» on a NEW pair is local (`handleSplitRow`, no backend split). Two shapes reach it: a visible
                // create with its hidden create partner (case B, what the toolbar's merge of two new rows leaves), and two
                // VISIBLE creates sharing a `link_uuid` with no `pairedWith` (case «legacy»). The legacy shape is built here
                // by two single pushes carrying the same `link_uuid` (`addRowFromForm` keeps it); no flow of today's UI was
                // found that leaves it (the merge, the import and the clone all hide the partner). Both now read the split
                // row's side through `splitHalfType`. Guards: with a ±50 pair they are green before and after C22d; they
                // pin that each row takes its type by its own sign and the link is dropped.

                /** The creates of a payload as {description, type, cash, link_uuid}, sorted by description. */
                function createsOf(body: C22bPayload): Array<{description: unknown; type: unknown; cash: number; link_uuid: unknown}> {
                    return (body.creates ?? []).map((create) => ({description: create.description, type: create.type, cash: Number((create.cash as {amount?: string} | null)?.amount), link_uuid: create.link_uuid ?? null})).sort((a, b) => String(a.description).localeCompare(String(b.description)));
                }

                /** The editor on two saved rows (no Form opens by itself), ends on both on screen. */
                async function openTwoSaved(): Promise<void> {
                    answerChargesRead([]);
                    txStoreSetAll([D0, FREE], []);
                    mountEditor({action: 'edit', txIds: [D0.id, FREE.id]});
                    await waitFor(() => expect(rowsOf(FREE.id), 'premise: both saved rows are on screen').toHaveLength(1));
                }

                it.each([
                    ['the split row the sender (cash −50 on 88), the other +50 on 77', 'C22d legacy sender', '-50.000000', 88, 'C22d legacy receiver', '50.000000', 77],
                    ['the split row the receiver (cash +50 on 77), the other −50 on 88', 'C22d legacy receiver', '50.000000', 77, 'C22d legacy sender', '-50.000000', 88],
                ] as const)('C22d: a NEW CASH_TRANSFER pair of two visible rows sharing a link_uuid (case «legacy»), «Split pair» on %s — each row takes WITHDRAWAL / DEPOSIT by its sign, no link left', async (_label, mainNote, mainCash, mainBroker, otherNote, otherCash, otherBroker) => {
                    await openTwoSaved();
                    await addRow(cashPayload('DEPOSIT', mainBroker, mainCash, mainNote, {type: 'CASH_TRANSFER', link_uuid: 'c22d-legacy-pair'}));
                    await addRow(cashPayload('DEPOSIT', otherBroker, otherCash, otherNote, {type: 'CASH_TRANSFER', link_uuid: 'c22d-legacy-pair'}));
                    // The legacy shape: both rows visible (no hidden partner), both CASH_TRANSFER, one link.
                    expect(typeCellTarget(gridRowDescribed(mainNote)), 'premise: the split row is a visible CASH_TRANSFER').toBe('cash-transfer');
                    expect(typeCellTarget(gridRowDescribed(otherNote)), 'premise: its partner is a visible CASH_TRANSFER too').toBe('cash-transfer');
                    const before = (await validateNow()) as C22bPayload;
                    expect(
                        createsOf(before).map((create) => create.link_uuid),
                        `premise: both creates share the link — ${JSON.stringify(before.creates)}`,
                    ).toEqual(['c22d-legacy-pair', 'c22d-legacy-pair']);

                    await rowAction(gridRowDescribed(mainNote), 'split');

                    expect.soft(typeCellTarget(gridRowDescribed('C22d legacy sender')), 'C22d: the sender row (−50) is a WITHDRAWAL').toBe('withdrawal');
                    expect.soft(typeCellTarget(gridRowDescribed('C22d legacy receiver')), 'C22d: the receiver row (+50) is a DEPOSIT').toBe('deposit');
                    const body = (await validateNow()) as C22bPayload;
                    expect(createsOf(body), `C22d: two standalone creates, typed by their sign, no link — ${JSON.stringify(body.creates)}`).toEqual([
                        {description: 'C22d legacy receiver', type: 'DEPOSIT', cash: 50, link_uuid: null},
                        {description: 'C22d legacy sender', type: 'WITHDRAWAL', cash: -50, link_uuid: null},
                    ]);
                });

                it('C22d: a NEW CASH_TRANSFER pair merged from two new rows (case B: the receiver a hidden partner), «Split pair» on its visible row — WITHDRAWAL −50 / DEPOSIT +50, no link left', async () => {
                    await openTwoSaved();
                    await addRow(cashPayload('DEPOSIT', 77, '50.000000', 'C22d new pair'));
                    await addRow(cashPayload('WITHDRAWAL', 88, '-50.000000', 'C22d new pair'));
                    const created = newRows();
                    expect(created, 'premise: two new rows').toHaveLength(2);
                    await mergeSelected(created[0], created[1]);
                    const merged = newRows();
                    expect(merged, 'premise: the merge is one visible row, its partner hidden').toHaveLength(1);
                    expect(typeCellTarget(merged[0]), 'premise: the visible row is a CASH_TRANSFER').toBe('cash-transfer');

                    await rowAction(merged[0], 'split');

                    const rows = newRows();
                    expect(rows, 'C22d: both halves are rows of their own').toHaveLength(2);
                    expect.soft(rows.map((row) => typeCellTarget(row)).sort(), 'C22d: one WITHDRAWAL and one DEPOSIT').toEqual(['deposit', 'withdrawal']);
                    const body = (await validateNow()) as C22bPayload;
                    expect(
                        createsOf(body)
                            .map(({type, cash, link_uuid}) => ({type, cash, link_uuid}))
                            .sort((a, b) => a.cash - b.cash),
                        `C22d: two standalone creates, typed by their sign, no link — ${JSON.stringify(body.creates)}`,
                    ).toEqual([
                        {type: 'WITHDRAWAL', cash: -50, link_uuid: null},
                        {type: 'DEPOSIT', cash: 50, link_uuid: null},
                    ]);
                });

                // `twoParents`, on the two halves of the split: before C22d each mirror row read CASH_TRANSFER (no charge
                // role) and «Link» was hidden; now both read their post-split type, two parents. The type the reason names
                // (`params.type`) only reaches the screen inside the translated hint, so it is pinned on `bulkLinkSelection`
                // in `bulkCharges.test.ts` (66 C22d, `typeOf`); here the reason, through `data-reason`.
                it('C22d: the saved CASH_TRANSFER pair split, no edit, BOTH halves + FREE ticked — «Link» drawn off with twoParents', async () => {
                    await openSplitUntouched(L_W, L_D, [FREE]);
                    await setTicked(gridRow(L_D.id), true);
                    await setTicked(gridRow(FREE.id), true);
                    expect(linkOffer(), 'barrier: the DEPOSIT half + FREE draw «Link» on').toBe('on');
                    await setTicked(gridRow(L_W.id), true);

                    expect(linkOffer(), 'C22d: two halves, two parents (WITHDRAWAL and DEPOSIT) — «Link» off, twoParents').toBe('off (twoParents)');
                });

                // ---------------------------------------------------------------
                // C22e — the update of a split half carries the type the user chose
                // ---------------------------------------------------------------

                /**
                 * 66 C22e (FEE consultant + coordinator, 21/11). `resolveOps` strips `type` from the update of every
                 * split-queued row: the backend's split assigns it (`apply_splits`, on the SAVED side, `pair_sides`). Once the
                 * user swaps a half in its Form (DEPOSIT ↔ WITHDRAWAL, the swap group the Form offers), the update still goes
                 * out without a type: the DEPOSIT half turned WITHDRAWAL is sent `{id, cash: −50}`, the split makes it a
                 * DEPOSIT, rule 11 refuses −50 on a DEPOSIT and the whole batch fails (present since v1.3.0).
                 *
                 * The decision: the update carries `type` exactly when the type the Bulk shows for the half (`postSplitType`)
                 * differs from the one the backend's split gives it (`splitHalfType` on the saved side) —
                 * `splitTypes.ts`, `splitTypeToSend`. The backend accepts a swap in an update (`SWAP_GROUPS`), and updates run
                 * after splits, then `link_charges`.
                 *
                 * Read through «Save all», the path that fails. `push` stands in for the real Form's Apply: a WITHDRAWAL's
                 * cash signed negative (`autoNegateCash`), a DEPOSIT's positive; the editor holds a WITHDRAWAL as its
                 * magnitude (W-B65).
                 */
                describe('66 C22e: the update of a swapped split half carries its type', () => {
                    /** The cash amount of one update, as a number (NaN when it carries none). */
                    function cashOf(update: Record<string, unknown> | undefined): number {
                        return Number((update?.cash as {amount?: string} | undefined)?.amount);
                    }

                    /** The half's own Form, its type swapped to `type` with `cash` as the real Form signs it. Ends on the
                     *  Form closed and the half's Type cell showing the user's type. */
                    async function swapHalf(half: TXReadItem, type: 'DEPOSIT' | 'WITHDRAWAL', cash: string): Promise<void> {
                        await rowAction(gridRow(half.id), 'edit-single');
                        await waitFor(() => expect(formProbe().open, `premise: the Form of #${half.id} is open`).toBe(true));
                        const item = ((formProbe().items as TXReadItem[] | null) ?? []).find((candidate) => candidate.id === half.id);
                        expect(item, `premise: the Form holds #${half.id}`).toBeDefined();
                        expect(item!.type, `premise: the Form of #${half.id} is handed the other type of its swap group`).not.toBe(type);
                        await push({broker_id: item!.broker_id, type, date: item!.date, quantity: item!.quantity, asset_id: item!.asset_id, cash: {code: 'EUR', amount: cash}, tags: item!.tags ?? [], description: item!.description});
                        expect(typeCellTarget(gridRow(half.id)), `premise: the Type cell of #${half.id} shows the user’s ${type}`).toBe(type.toLowerCase());
                    }

                    const PAIR_SPLIT = [[L_W.id, L_D.id].sort((a, b) => a - b)];

                    // The defect. Today: `{id: 92521, cash: {amount: "-50…"}}`, no type.
                    it('C22e: the DEPOSIT half swapped to WITHDRAWAL in its Form — «Save all» sends its update with type WITHDRAWAL and cash −50', async () => {
                        await openSplitUntouched(L_W, L_D);
                        await swapHalf(L_D, 'WITHDRAWAL', '-50.000000');

                        const body = (await saveAll()) as C22bPayload;
                        const sent = JSON.stringify({splits: body.splits, updates: body.updates});
                        expect(splitsOf(body), `premise: the split is in the batch — ${sent}`).toEqual(PAIR_SPLIT);
                        const updates = updatesOf(body, L_D.id);
                        expect(updates, `premise: one update for the swapped half — ${sent}`).toHaveLength(1);
                        expect.soft(updates[0].type, `C22e: the swapped half carries the user’s type, or the split makes it a DEPOSIT — ${sent}`).toBe('WITHDRAWAL');
                        expect.soft(cashOf(updates[0]), `C22e: and its cash signed as a WITHDRAWAL — ${sent}`).toBe(-50);
                        expect.soft(updatesOf(body, L_W.id), `C22e: the untouched sender is not sent — ${sent}`).toEqual([]);
                    });

                    // Guard, green today and after the cure: a half edited without a swap (its note, twice — C22d's route) shows
                    // the type the split gives it, so its update carries none. The WITHDRAWAL half is the discriminating one: its
                    // draft holds +50 (W-B65) while the saved side, the one the server reads, is −50.
                    it.each([
                        ['the DEPOSIT half', 'dep'],
                        ['the WITHDRAWAL half', 'wd'],
                    ] as const)('C22e guard: %s, only its note edited in its Form, twice — «Save all» sends the note and no type', async (_label, which) => {
                        const half = which === 'dep' ? L_D : L_W;
                        await openSplitUntouched(L_W, L_D);
                        await editHalfNote(half, 'C22e note a');
                        await editHalfNote(half, 'C22e note b');

                        const body = (await saveAll()) as C22bPayload;
                        const sent = JSON.stringify({splits: body.splits, updates: body.updates});
                        expect(splitsOf(body), `premise: the split is in the batch — ${sent}`).toEqual(PAIR_SPLIT);
                        const updates = updatesOf(body, half.id);
                        expect(
                            updates.some((update) => update.description === 'C22e note b'),
                            `premise: the second note is sent — ${sent}`,
                        ).toBe(true);
                        expect(
                            updates.filter((update) => 'type' in update),
                            `C22e guard: no swap, no type — the split gives #${half.id} its type — ${sent}`,
                        ).toEqual([]);
                    });

                    // Both halves swapped: the sender (saved −50) turned DEPOSIT, the receiver (saved +50) turned WITHDRAWAL.
                    // Today both go out without a type: the WITHDRAWAL half as `cash: −50`, the DEPOSIT half as `cash: +50`.
                    it('C22e: both halves swapped in their Forms — each update carries its own type and its cash signed by it', async () => {
                        await openSplitUntouched(L_W, L_D);
                        await swapHalf(L_D, 'WITHDRAWAL', '-50.000000');
                        await swapHalf(L_W, 'DEPOSIT', '50.000000');
                        // The swapped halves now cancel each other (a DEPOSIT +50 on 88, a WITHDRAWAL −50 on 77): the banner
                        // offers them as a merge, and «Save all» stops at the unseen-suggestions gate until it is looked at.
                        // A click inside the banner (not on its link, which would merge) marks it seen.
                        const banner = screen.queryByTestId('promote-suggest-banner');
                        expect(banner, 'premise: the banner offers the two swapped halves').not.toBeNull();
                        await fireEvent.click(banner!);
                        await settle();
                        expect(screen.queryByTestId('promote-suggest-banner'), 'premise: looking at the banner merges nothing').not.toBeNull();

                        const body = (await saveAll()) as C22bPayload;
                        const sent = JSON.stringify({splits: body.splits, updates: body.updates});
                        expect(splitsOf(body), `premise: the split is in the batch — ${sent}`).toEqual(PAIR_SPLIT);
                        const deposit = updatesOf(body, L_D.id);
                        const withdrawal = updatesOf(body, L_W.id);
                        expect([deposit.length, withdrawal.length], `premise: one update for each half — ${sent}`).toEqual([1, 1]);
                        expect.soft({type: deposit[0].type, cash: cashOf(deposit[0])}, `C22e: the receiver (saved +50) goes out a WITHDRAWAL −50 — ${sent}`).toEqual({type: 'WITHDRAWAL', cash: -50});
                        expect.soft({type: withdrawal[0].type, cash: cashOf(withdrawal[0])}, `C22e: the sender (saved −50) goes out a DEPOSIT +50 — ${sent}`).toEqual({type: 'DEPOSIT', cash: 50});
                    });

                    // The swap and a link in one batch: FREE (a saved FEE of nobody, on 77, the DEPOSIT half's broker) linked by
                    // «Link» to the half swapped to WITHDRAWAL (a parent type either way). One commit holds the split, the
                    // half's update with its type, and FREE's parent; the backend splits, updates, then links
                    // (`test_transaction_charge_edits.py`, C22e).
                    it('C22e: the DEPOSIT half swapped to WITHDRAWAL and FREE linked to it by «Link» — one «Save all»: the split, the half’s update with its type, FREE under the half', async () => {
                        await openSplitUntouched(L_W, L_D, [FREE]);
                        await swapHalf(L_D, 'WITHDRAWAL', '-50.000000');
                        await linkRows(gridRow(L_D.id), gridRow(FREE.id));
                        expect(chargeOfCell(gridRow(FREE.id)), 'premise: FREE sits under the swapped half').toBe(gridRow(L_D.id).getAttribute('data-row-id'));

                        const body = (await saveAll()) as C22bPayload;
                        const sent = JSON.stringify({splits: body.splits, updates: body.updates});
                        expect(splitsOf(body), `premise: the split is in the batch — ${sent}`).toEqual(PAIR_SPLIT);
                        expect.soft(updatesOf(body, FREE.id), `C22e: FREE is sent under the half, in the same batch — ${sent}`).toEqual([{id: FREE.id, parent_transaction_id: L_D.id}]);
                        const updates = updatesOf(body, L_D.id);
                        expect(updates, `premise: one update for the swapped half — ${sent}`).toHaveLength(1);
                        expect.soft({type: updates[0].type, cash: cashOf(updates[0])}, `C22e: the half goes out a WITHDRAWAL −50, so FREE’s parent is the type the user sees — ${sent}`).toEqual({type: 'WITHDRAWAL', cash: -50});
                    });
                });
            });
        });
    });
});

// ---------------------------------------------------------------------------
// 77 SEL-E — the selection's actions on the table's panel, each with its number
// ---------------------------------------------------------------------------

/**
 * SEL-E (plan 77): the Bulk's selection actions leave the fixed toolbar for the table's selection panel — the bar at the top
 * of the table, the balloon when it scrolls away — and each shows the number of rows it takes (Q-SEL-1). Their test ids
 * stay the Bulk's own (`tx-bulk-delete-selected`, `promote-toolbar-confirm`, …), so the specs that read them keep reading
 * them. Rows brought in the way an import brings them, as the C-46 guard above does.
 */
describe('TransactionBulkModal — the selection on the table panel (77 SEL-E)', () => {
    async function importTwoLegs(): Promise<void> {
        mountEditor({action: 'import'});
        await waitFor(() => expect(wizardProbe().open, 'the import intent opens the wizard').toBe(true));
        const handOver = wizardProbe().onImportBatch as (creates: Array<{tx: TransactionCreateItem; todos: []}>) => void;
        const leg = (brokerId: number, quantity: string, description: string) => ({tx: {broker_id: brokerId, type: 'ADJUSTMENT', date: C46.date, asset_id: C46.assetId, quantity, tags: [], description} as TransactionCreateItem, todos: [] as []});
        handOver([leg(C46.brokerA, '-5', 'SEL-E out'), leg(C46.brokerB, '5', 'SEL-E in')]);
        await settle();
    }

    async function tick(description: string): Promise<void> {
        const checkbox = gridRowDescribed(description).querySelector<HTMLElement>('[data-testid^="dt-row-checkbox-"]');
        if (!checkbox) throw new Error(`no checkbox on ${description}`);
        await fireEvent.click(checkbox);
    }

    it('two ticked legs: «Delete» and the merge sit in the table panel’s bar, each with its number; nothing to reset', async () => {
        await importTwoLegs();
        await tick('SEL-E out');
        await tick('SEL-E in');

        const bar = await screen.findByTestId('selection-toolbar');
        expect(screen.getByTestId('tx-bulk-body').contains(bar), 'the bar is the table’s, in the body that scrolls').toBe(true);
        expect(within(bar).getByTestId('tx-bulk-delete-selected-count').textContent?.trim()).toBe('2');
        expect(within(bar).getByTestId('promote-toolbar-confirm-count').textContent?.trim()).toBe('2');
        // Two new rows: nothing saved to go back to
        expect(within(bar).queryByTestId('tx-bulk-reset-selected')).toBeNull();
    });

    it('the Bulk guide’s «selection» anchor follows the bar: at the top, then in the balloon once the top scrolls away', async () => {
        // jsdom has no IntersectionObserver: a stub stands in, and the test says when the top of the table leaves the view
        const observers: Array<{callback: IntersectionObserverCallback; targets: Element[]}> = [];
        vi.stubGlobal(
            'IntersectionObserver',
            class {
                private entry: {callback: IntersectionObserverCallback; targets: Element[]};
                constructor(callback: IntersectionObserverCallback) {
                    this.entry = {callback, targets: []};
                    observers.push(this.entry);
                }
                observe(target: Element) {
                    this.entry.targets.push(target);
                }
                unobserve() {}
                disconnect() {}
                takeRecords() {
                    return [];
                }
            },
        );
        try {
            await importTwoLegs();
            await tick('SEL-E out');
            const top = await screen.findByTestId('selection-toolbar');
            await waitFor(() => expect(guideAnchors.get('transaction.bulk.selection'), 'the anchor is the bar at the top').toBe(top));

            for (const observer of observers)
                observer.callback(
                    observer.targets.map((target) => ({isIntersecting: false, target}) as IntersectionObserverEntry),
                    {} as IntersectionObserver,
                );
            await waitFor(() => expect(screen.getByTestId('dt-dock')).toHaveAttribute('data-actions', 'true'));
            const docked = screen.getByTestId('dt-dock').querySelector('[data-testid="selection-toolbar"]');
            expect(docked, 'premise: the actions are in the balloon').not.toBeNull();
            await waitFor(() => expect(guideAnchors.get('transaction.bulk.selection'), 'the anchor followed the bar into the balloon').toBe(docked));
        } finally {
            vi.unstubAllGlobals();
        }
    });

    it('one ticked leg: no merge (it takes two), «Delete» with 1', async () => {
        await importTwoLegs();
        await tick('SEL-E out');

        const bar = await screen.findByTestId('selection-toolbar');
        expect(within(bar).queryByTestId('promote-toolbar-confirm')).toBeNull();
        expect(within(bar).getByTestId('tx-bulk-delete-selected-count').textContent?.trim()).toBe('1');
    });
});

// ---------------------------------------------------------------------------
// 77 SEL-M part 2 — the Bulk's row menu: off says why
// ---------------------------------------------------------------------------

/**
 * SEL-M part 2 (plan 77, Q-SEL-12): a row action that makes sense but is blocked is off with its reason, reachable
 * (`aria-disabled`, the reason in the shared Tooltip, its code in `data-disabled-reason`). «Edit row» on a pair whose
 * partner sits on a broker the user cannot read is one; «del» while the charges are read (or could not be) is the other,
 * covered above by the F7-c1 cases.
 */
describe('TransactionBulkModal — the row menu says why (77 SEL-M part 2)', () => {
    it('«Edit row» on a pair whose partner is on an unreadable broker: off, with its reason', async () => {
        txStoreSetAll([SAVED_SENDER], []);
        mountEditor({action: 'edit', txIds: [SAVED_SENDER.id]});
        const lock = await screen.findByTestId('tx-bulk-partner-lock');
        const row = lock.closest('tr') as HTMLElement;
        await fireEvent.contextMenu(row, {clientX: 10, clientY: 10});
        const edit = await screen.findByTestId('context-menu-action-edit-single');
        expect(edit).toHaveAttribute('aria-disabled', 'true');
        expect(edit).toHaveAttribute('data-disabled-reason', 'partner-inaccessible');
        await fireEvent.click(edit);
        expect(screen.getByTestId('context-menu'), 'a click on an item that is off runs nothing: the menu stays open').toBeInTheDocument();
    });
});
