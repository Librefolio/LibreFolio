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

const {probe, typesLoad} = vi.hoisted(() => ({
    /** The props the editor hands its two nested modals, recorded at mount. */
    probe: {
        form: null as Record<string, unknown> | null,
        wizard: null as Record<string, unknown> | null,
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
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
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
