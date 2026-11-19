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
import {flushSync, tick} from 'svelte';
import {get, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {_} from '$lib/i18n';
import {schemas} from '$lib/api/generated';
import {currentLanguage} from '$lib/stores/app/language';
import {ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
import {ensureTypesLoaded, isTypesLoaded} from '$lib/features/transactions/transactionTypeStore';
import {txStoreInvalidate, txStoreSetAll} from '$lib/features/transactions/txStore.svelte';
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
 *   - The indented row (§13.5–§13.6): the label cell carries `data-charge-of="<parent tempId>"` and `↳`; no selection
 *     checkbox; a state badge `tx-bulk-charge-state` with `data-state="linked|unlink|del"`; its menu offers «Delete» /
 *     «Restore» only; a double-click opens its own Form.
 *   - A charge unlinked from a parent that stays is a top-level row, with the badge `unlink` (§13.1).
 *   - The group opens by itself when the parent is «del», when the charges came in the intent with the parent, when a
 *     charge is created or linked in the parent's Form; it starts closed for the charges the Bulk read itself (§14.7).
 *   - Order (§14.5): one order, ours — the top-level rows by date (the header's direction), each open parent followed by
 *     its charges.
 *   - Selection (§14.6): a selected top-level row that becomes indented leaves the selection.
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

    it('the chip opens the group: the two charges, indented right after the parent, ↳, no checkbox, state linked; a second click closes it; no Form opens', async () => {
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
            expect(rowCheckbox(row), `${charge.type}: no selection checkbox`).toBeNull();
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
        expect(del, '«del» on a parent whose charges could not be read is off').toBeDisabled();
        expect(del.getAttribute('title') ?? '', 'and says why').not.toBe('');
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
    it('the menu of an indented row offers exactly «Edit row» and «Delete» / «Restore»; Delete → del, Restore → linked', async () => {
        await openLoaded();
        await fireEvent.click(theChip());
        await settle();

        await openMenu(gridRow(FEE.id));
        expect(screen.getByTestId('context-menu-action-mark-delete'), 'barrier: the menu offers «Delete»').toBeInTheDocument();
        expect(screen.getByTestId('context-menu-action-edit-single'), 'and «Edit row»').toBeInTheDocument();
        expect(
            [...screen.getByTestId('context-menu').querySelectorAll('[data-testid^="context-menu-action-"]')].map((item) => item.getAttribute('data-testid')),
            'exactly those two',
        ).toEqual(expect.arrayContaining(['context-menu-action-edit-single', 'context-menu-action-mark-delete']));
        expect(screen.getByTestId('context-menu').querySelectorAll('[data-testid^="context-menu-action-"]'), 'exactly those two').toHaveLength(2);
        for (const hidden of ['clone', 'split', 'remove-from-batch', 'reset']) {
            expect(screen.queryByTestId(`context-menu-action-${hidden}`), `no «${hidden}» on a charge`).toBeNull();
        }
        await clickCollectingErrors(screen.getByTestId('context-menu-action-mark-delete'));
        expect(chargeState(gridRow(FEE.id)), 'Delete marks the charge').toBe('del');
        expect(rowStatus(gridRow(FEE.id)), 'its own status cell says «delete» too (the Bulk’s «del» counts include it)').toBe('delete');
        expect(theChip(), 'a charge marked: the chip says its group changed').toHaveAttribute('data-charges-modified', 'true');
        expect(rowStatus(gridRow(BUY.id)), 'the parent’s own status does not change').toBe('original');

        // A charge marked «del» is a changed row: its menu still offers «Restore» only (no «reset», no «remove»).
        await openMenu(gridRow(FEE.id));
        expect(screen.getByTestId('context-menu-action-mark-delete'), 'barrier: the menu offers «Restore»').toBeInTheDocument();
        expect(screen.getByTestId('context-menu-action-edit-single'), 'and «Edit row»').toBeInTheDocument();
        for (const hidden of ['clone', 'remove-from-batch', 'reset']) {
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

    it('a selected top-level row that goes back under its parent leaves the selection', async () => {
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

        expect(screen.queryByTestId('tx-bulk-delete-selected'), 'the FEE, under its parent again, left the selection').toBeNull();
        expect(theChip(), 'a charge linked in the parent’s Form opens the group').toHaveAttribute('aria-expanded', 'true');
        expect(chargeOfCell(gridRow(FEE.id)), 'the FEE is indented under the BUY again').toBe(buyRowId());
        expect(rowCheckbox(gridRow(FEE.id)), 'with no checkbox').toBeNull();
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
        expect(screen.getByTestId('context-menu-action-mark-delete'), 'the charges are read: «del» is on again').toBeEnabled();
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
        expect(rowCheckbox(gridRow(FEE.id)), 'and no longer selectable').toBeNull();
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
            const verdict = {enabled: !(action as HTMLButtonElement).disabled, reason: action.getAttribute('title') ?? ''};
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
        expect(screen.getByTestId('context-menu-action-mark-delete'), '«del» is on again').toBeEnabled();
        expect(screen.queryByTestId('context-menu-action-reset'), 'and, read, the untouched parent no longer offers «Reset row»').toBeNull();
    });

    it('an untouched parent whose read succeeded offers no «Reset row»', async () => {
        await openLoaded();
        expect(rowStatus(gridRow(BUY.id)), 'premise: the parent is untouched').toBe('original');

        await openMenu(gridRow(BUY.id));

        expect(screen.getByTestId('context-menu-action-mark-delete'), 'barrier: the menu is drawn, «del» on').toBeEnabled();
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
            expect(ths[1].textContent ?? '').toContain(get(_)('transactions.bulk.stateNew'));
            expect(typeCell(ths[1]), 'A’s new FEE under A').toBe(get(_)('transactions.types.FEE'));
            expect(ths[2].textContent ?? '').toContain(`#${PARENT_B.id}`);
            expect(ths[3].textContent ?? '').toContain(get(_)('transactions.bulk.stateNew'));
            expect(typeCell(ths[3]), 'B’s new TAX under B').toBe(get(_)('transactions.types.TAX'));
            for (const th of ths) expect(th.textContent ?? '', 'no TX #0').not.toContain('#0');
        });
    });
});
