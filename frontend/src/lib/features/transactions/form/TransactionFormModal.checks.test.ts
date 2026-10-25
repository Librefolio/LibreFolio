// @vitest-environment jsdom
/**
 * TransactionFormModal — «⚡ Validate now» as a complete pre-check (V-37b), component test (Vitest + jsdom).
 *
 * The contract:
 *   - the button is ALWAYS enabled on an editable form (an incomplete form used to disable it, with no visible cause);
 *   - a click while the form holds a problem NEVER asks the server (`validateTransactions`) and never commits: it
 *     marks the wrong cells and leads the user to the first one;
 *   - a cell is a wrapper element `[data-cell="<cell>"]` (date, dateTo, quantity, cash, cashTo, asset, broker,
 *     brokerTo). It carries `data-cell-invalid="required"|"format"` ONLY while it is wrong, and only AFTER the click:
 *     before it no cell carries the attribute;
 *   - `data-testid="tx-form-check-summary"` appears with `data-check-count="<n>"`;
 *   - the focus lands inside the first marked cell in SCREEN (DOM) order: `document.activeElement.closest('[data-cell]')`;
 *   - a mark disappears live when its field is fixed, and a click with nothing left wrong validates, once.
 *
 * What this file does NOT drive, and leaves to the E2E (tx-fx-completeness.spec.ts):
 *   - a real picked broker or asset (the harness has no broker/asset catalogue, so a form that needs them is seeded
 *     through `items`, the way the Bulk editor opens it);
 *   - the currency dropdown (the harness has no currency list): the same-currency FX is seeded the same way.
 *
 * The mock header is the one of TransactionFormModal.test.ts. Asserted: data-testid / data-cell / data-* only,
 * never a translated label.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {commitTransactions, validateTransactions} from '$lib/features/transactions/txCommitApi';
import {ensureTypesLoaded} from '$lib/features/transactions/transactionTypeStore';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
import type {ContextualOnboardingFlow, GuideStepId, GuidedOnboardingFlow} from '$lib/features/onboarding/onboardingGuideCatalog';

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
// CompactCashCell's currency dropdown reads the FX route cache.
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({
    fxRoutesVersion: writable(0),
    ensureFxRoutesLoaded: vi.fn(async () => undefined),
    getConfiguredCurrencySet: vi.fn(() => new Set(['EUR', 'USD'])),
}));
// The validate scheduler may fire on a complete duplicate draft; keep the wire out of it.
vi.mock('$lib/features/transactions/txCommitApi', () => ({
    commitTransactions: vi.fn(async () => ({committed: true, results: [], issues: []})),
    validateTransactions: vi.fn(async () => ({committed: true, issues: [], rawResponse: {wac_results: []}})),
}));

/**
 * Keep the component at the public onboardingGuide boundary while owning the
 * queue and active state in this file. The real controller's persistence and
 * replay machinery is covered by onboardingGuide tests; these cases need the
 * state transitions that make a queued guide observable across close/unmount.
 */
const {guideState, guideMocks} = vi.hoisted(() => {
    const state = {
        active: null as {
            flow: GuidedOnboardingFlow;
            version: number;
            stepId: GuideStepId;
            mode: 'automatic' | 'replay';
        } | null,
        queuedGuides: [] as Array<{flow: ContextualOnboardingFlow; stepId?: GuideStepId}>,
    };

    const queueContextual = vi.fn((flow: ContextualOnboardingFlow, stepId?: GuideStepId) => {
        if (!state.queuedGuides.some((queued) => queued.flow === flow && queued.stepId === stepId)) {
            state.queuedGuides = [...state.queuedGuides, {flow, ...(stepId ? {stepId} : {})}];
        }
    });
    const maybeStartContextual = vi.fn((flow: ContextualOnboardingFlow, requestedStepId?: GuideStepId) => {
        if (state.active) {
            if (state.active.flow === flow && (!requestedStepId || state.active.stepId === requestedStepId)) return true;
            queueContextual(flow, requestedStepId);
            return false;
        }
        state.active = {
            flow,
            version: 1,
            stepId: requestedStepId ?? 'transaction.create.basics',
            mode: 'automatic',
        };
        return true;
    });
    const clearQueued = vi.fn((flow?: ContextualOnboardingFlow, stepId?: GuideStepId) => {
        if (!flow) {
            state.queuedGuides = [];
        } else if (stepId) {
            state.queuedGuides = state.queuedGuides.filter((queued) => queued.flow !== flow || queued.stepId !== stepId);
        } else {
            state.queuedGuides = state.queuedGuides.filter((queued) => queued.flow !== flow);
        }
    });
    const maybeStartQueued = vi.fn((expectedFlow?: ContextualOnboardingFlow, expectedStepId?: GuideStepId) => {
        if (state.active || state.queuedGuides.length === 0) return false;
        const index = expectedFlow ? state.queuedGuides.findIndex((queued) => queued.flow === expectedFlow && (!expectedStepId || queued.stepId === expectedStepId)) : 0;
        if (index < 0) return false;
        const queued = state.queuedGuides[index];
        const started = maybeStartContextual(queued.flow, queued.stepId);
        state.queuedGuides = state.queuedGuides.filter((_, queuedIndex) => queuedIndex !== index);
        return started;
    });
    const dismissHost = vi.fn((_options?: {restartAtFirst?: boolean}) => {
        state.active = null;
    });

    return {
        guideState: state,
        guideMocks: {
            queueContextual,
            maybeStartContextual,
            clearQueued,
            maybeStartQueued,
            dismissHost,
        },
    };
});

vi.mock('$lib/features/onboarding/onboardingGuide.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/onboarding/onboardingGuide.svelte')>();
    return {
        ...actual,
        onboardingGuide: {
            get active() {
                return guideState.active;
            },
            get queuedFlow() {
                return guideState.queuedGuides[0]?.flow ?? null;
            },
            get queuedFlows() {
                return guideState.queuedGuides.map((queued) => queued.flow);
            },
            get queuedGuides() {
                return guideState.queuedGuides;
            },
            maybeStartContextual: (...args: Parameters<typeof guideMocks.maybeStartContextual>) => guideMocks.maybeStartContextual(...args),
            queueContextual: (...args: Parameters<typeof guideMocks.queueContextual>) => guideMocks.queueContextual(...args),
            clearQueued: (...args: Parameters<typeof guideMocks.clearQueued>) => guideMocks.clearQueued(...args),
            maybeStartQueued: (...args: Parameters<typeof guideMocks.maybeStartQueued>) => guideMocks.maybeStartQueued(...args),
            dismissHost: (...args: Parameters<typeof guideMocks.dismissHost>) => guideMocks.dismissHost(...args),
        },
    };
});

const validMinimalTXTypesResponse = schemas.TXTypesResponse.parse({
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
            code: 'SELL',
            name: 'Sell',
            description: 'Sell asset for cash',
            icon_slug: 'sell',
            doc_slug: 'buy-sell',
            asset_mode: 'required',
            cash_mode: 'required',
            quantity_mode: 'required',
            requires_link: false,
            quantity_sign: 'negative',
            cash_sign: 'positive',
            event_compatible: false,
            cost_basis_mode: 'forbidden',
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
            cost_basis_mode: 'forbidden',
            cost_basis_pair: ['forbidden', 'required_qty_pos'],
        },
        {
            code: 'ADJUSTMENT',
            name: 'Adjustment',
            description: 'Manual quantity correction',
            icon_slug: 'adjustment',
            doc_slug: 'adjustment',
            asset_mode: 'required',
            cash_mode: 'forbidden',
            quantity_mode: 'required',
            requires_link: false,
            quantity_sign: 'nonzero',
            cash_sign: 'zero',
            event_compatible: true,
            cost_basis_mode: 'required_qty_pos',
        },
        {
            code: 'FX_CONVERSION',
            name: 'FX Conversion',
            description: 'Currency exchange',
            icon_slug: 'fx-conversion',
            doc_slug: 'fx-conversion',
            asset_mode: 'forbidden',
            cash_mode: 'required',
            quantity_mode: 'forbidden',
            requires_link: true,
            quantity_sign: 'zero',
            cash_sign: 'nonzero',
            event_compatible: false,
            pair_form_layout: 'fx',
            cost_basis_mode: 'forbidden',
        },
    ],
    event_types: [],
});

import TransactionFormModal from './TransactionFormModal.svelte';

/** A standalone BUY row, dated deliberately far from "today". */
function mount(props: Record<string, unknown> = {}) {
    const onClose = vi.fn();
    return {onClose, ...render(TransactionFormModal, {open: true, mode: 'create', items: null, onClose, ...props})};
}

function txRow(overrides: Record<string, unknown> = {}) {
    return {
        id: 101,
        broker_id: 17,
        asset_id: 42,
        type: 'BUY',
        date: '2024-03-10',
        quantity: '1',
        cash: {code: 'EUR', amount: '-100'},
        related_transaction_id: null,
        partner_broker_id: null,
        tags: [],
        description: '',
        cost_basis_override: null,
        cost_basis_mode: null,
        asset_event_id: null,
        ...overrides,
    };
}

function openTypeSelect() {
    return fireEvent.click(within(screen.getByTestId('tx-form-type')).getByRole('combobox'));
}

async function chooseFxType() {
    await chooseDualType('FX_CONVERSION');
}

/** Pick a type that always comes as a pair (FX_CONVERSION, TRANSFER), and wait for the two-panel layout it brings. */
async function chooseDualType(code: 'FX_CONVERSION' | 'TRANSFER') {
    await openTypeSelect();
    await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
    const dropdown = screen.getByRole('listbox').parentElement as HTMLElement;
    await fireEvent.click(within(dropdown).getByTestId(`search-select-option-${code}`));
    await waitFor(() => expect(screen.getByTestId('tx-form-dual-split')).toBeInTheDocument());
}

async function setTypedDate(wrapperTestId: string, date: string) {
    const wrapper = screen.getByTestId(wrapperTestId);
    const input = within(within(wrapper).getByTestId('single-date-picker-root')).getByRole('textbox') as HTMLInputElement;
    await fireEvent.input(input, {target: {value: date}});
    await fireEvent.blur(input);
}

function resetGuideState() {
    guideState.active = null;
    guideState.queuedGuides = [];
}

// ---------------------------------------------------------------------------------------------------------------------
// What this file observes
// ---------------------------------------------------------------------------------------------------------------------

type CellName = 'date' | 'dateTo' | 'quantity' | 'cash' | 'cashTo' | 'asset' | 'broker' | 'brokerTo';

const cell = (name: CellName): HTMLElement | null => document.querySelector<HTMLElement>(`[data-cell="${name}"]`);
/** Every cell that carries a mark, in document (screen) order. */
const markedCells = (): HTMLElement[] => Array.from(document.querySelectorAll<HTMLElement>('[data-cell-invalid]'));
/** The cell the focus is inside, if any. */
const focusedCell = (): HTMLElement | null => (document.activeElement as HTMLElement | null)?.closest<HTMLElement>('[data-cell]') ?? null;
const validateNowButton = (): HTMLElement => screen.getByTestId('tx-form-validate-now');

/** Click ⚡. A real click leaves the focus on the button; the handler is what may move it. */
async function clickValidateNow(): Promise<void> {
    const button = validateNowButton();
    expect(button, 'V-37b: Validate now is available whatever the form holds').toBeEnabled();
    button.focus();
    await fireEvent.click(button);
}

function expectMarked(name: CellName, kind: 'required' | 'format'): void {
    const element = cell(name);
    expect(element, `a [data-cell="${name}"] wrapper is rendered`).not.toBeNull();
    expect(element, `${name} is marked ${kind}`).toHaveAttribute('data-cell-invalid', kind);
}

function expectNotMarked(name: CellName): void {
    const element = cell(name);
    expect(element, `a [data-cell="${name}"] wrapper is rendered`).not.toBeNull();
    expect(element, `${name} is not marked`).not.toHaveAttribute('data-cell-invalid');
}

function expectSummary(count: number): void {
    const summary = screen.getByTestId('tx-form-check-summary');
    expect(summary).toHaveAttribute('data-check-count', String(count));
    expect(markedCells().length, 'the summary counts the cells on screen that carry a mark').toBe(count);
}

/** A saved-looking pair of FX rows: broker 17 on both legs, the currencies given. */
function fxPair(from = 'EUR', to = 'USD') {
    const base = {type: 'FX_CONVERSION', asset_id: null, quantity: '0', broker_id: 17, partner_broker_id: 17};
    return [txRow({...base, id: 101, cash: {code: from, amount: '-100'}, related_transaction_id: 202}), txRow({...base, id: 202, cash: {code: to, amount: '110'}, related_transaction_id: 101})];
}

describe('TransactionFormModal — Validate now is a complete pre-check (V-37b)', () => {
    beforeEach(async () => {
        vi.clearAllMocks();
        guideAnchors.clear();
        resetGuideState();
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(validMinimalTXTypesResponse);
        await setupI18n();
        await ensureTypesLoaded();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
        resetGuideState();
    });

    it('a fresh empty create form: Validate now is enabled, nothing is marked, there is no summary', async () => {
        mount({mode: 'create'});
        await screen.findByTestId('tx-form-quantity');

        expect(validateNowButton(), 'V-37b: an empty form no longer disables Validate now').toBeEnabled();
        expect(markedCells(), 'nothing is marked before the click').toHaveLength(0);
        expect(screen.queryByTestId('tx-form-check-summary')).toBeNull();
    });

    it('(a) an empty single BUY: the click marks what the rule demands, summarises, focuses the first one, and asks nobody', async () => {
        mount({mode: 'create'});
        await screen.findByTestId('tx-form-quantity');
        expect(markedCells(), 'premise: the form starts unmarked').toHaveLength(0);

        await clickValidateNow();
        await waitFor(() => expect(markedCells().length).toBeGreaterThan(0));

        // BUY requires a quantity, a cash, an asset and a broker. The date is pre-filled with today.
        // No broker is loaded in this harness, so the unset sentinel stays: the broker is missing too.
        expectMarked('quantity', 'required');
        expectMarked('cash', 'required');
        expectMarked('asset', 'required');
        expectMarked('broker', 'required');
        expectNotMarked('date');
        expectSummary(4);

        // Screen order of a single form: date, type, quantity, cash, asset, broker.
        expect(markedCells()[0], 'the first mark in screen order is the quantity').toBe(cell('quantity'));
        expect(focusedCell(), 'the focus is inside the first marked cell').toBe(cell('quantity'));

        expect(validateTransactions, 'a form with problems is never sent to the server').not.toHaveBeenCalled();
        expect(commitTransactions).not.toHaveBeenCalled();
    });

    it('(b) a required quantity empty and a date typed as «abc»: quantity is required, the date is format, the focus goes to the date', async () => {
        mount({mode: 'create'});
        await screen.findByTestId('tx-form-quantity');

        await setTypedDate('tx-form-date-wrap', 'abc');
        await waitFor(() => expect(screen.getByTestId('tx-form-date-wrap').querySelector('[data-invalid="true"]'), 'premise: the picker refused the typed text').not.toBeNull());
        expect(markedCells(), 'a refused date is not marked until the user asks').toHaveLength(0);

        await clickValidateNow();
        await waitFor(() => expect(markedCells().length).toBeGreaterThan(0));

        expectMarked('quantity', 'required');
        expectMarked('date', 'format');

        expect(markedCells()[0], 'the date sits before the quantity on screen').toBe(cell('date'));
        expect(focusedCell(), 'the focus is inside the date cell, the first marked in screen order').toBe(cell('date'));

        expect(validateTransactions).not.toHaveBeenCalled();
        expect(commitTransactions).not.toHaveBeenCalled();
    });

    it('(c) a mark disappears live when its field is fixed, and a click with nothing left wrong validates exactly once', async () => {
        // A BUY complete but for its quantity: broker, asset, cash and date come with the seeded row.
        mount({mode: 'create', items: [txRow({quantity: ''})], commitOnSave: false, onPushDraft: vi.fn()});
        const quantity = await screen.findByTestId('tx-form-quantity');
        expect(quantity, 'premise: the quantity is empty').toHaveValue('');
        expect(markedCells(), 'premise: nothing is marked before the click').toHaveLength(0);

        await clickValidateNow();
        await waitFor(() => expect(markedCells().length).toBeGreaterThan(0));
        expectMarked('quantity', 'required');
        expectSummary(1);
        expect(focusedCell()).toBe(cell('quantity'));
        expect(validateTransactions, 'the incomplete form is not sent').not.toHaveBeenCalled();

        // Fixed: the mark goes away on its own, without another click.
        await fireEvent.input(quantity, {target: {value: '2'}});
        await waitFor(() => expect(cell('quantity'), 'the quantity wrapper is still rendered').not.toBeNull());
        await waitFor(() => expect(cell('quantity')).not.toHaveAttribute('data-cell-invalid'));
        expect(markedCells(), 'nothing is left to mark').toHaveLength(0);

        // Nothing wrong any more: the click asks the server, once. (The manual run cancels the debounced one the edit armed.)
        await clickValidateNow();
        await waitFor(() => expect(validateTransactions).toHaveBeenCalledTimes(1));
        await waitFor(() => expect(screen.getByTestId('tx-form-modal-root')).toHaveAttribute('data-validate-runs', '1'));
        expect(validateTransactions, 'one click, one run').toHaveBeenCalledTimes(1);
        const payload = vi.mocked(validateTransactions).mock.calls[0]?.[0] as unknown as {creates?: Array<{quantity?: unknown}>};
        expect(payload.creates?.[0]?.quantity, 'the run is about the corrected quantity').toBe('2');
        expect(markedCells(), 'a clean click marks nothing').toHaveLength(0);
        expect(commitTransactions).not.toHaveBeenCalled();
    });

    it('(d) an FX create with both cash empty: cash and cashTo are required, the focus goes to the From cash', async () => {
        mount({mode: 'create', defaultBrokerId: 17});
        await chooseFxType();
        expect(markedCells(), 'premise: nothing is marked before the click').toHaveLength(0);

        await clickValidateNow();
        await waitFor(() => expect(markedCells().length).toBeGreaterThan(0));

        expectMarked('cash', 'required');
        expectMarked('cashTo', 'required');
        // The shared broker is picked and both dates are pre-filled.
        expectNotMarked('broker');
        expectNotMarked('date');
        expectNotMarked('dateTo');
        expectSummary(2);

        expect(markedCells()[0], 'screen order of an FX: the From cash comes before the To cash').toBe(cell('cash'));
        expect(focusedCell(), 'the focus is inside the From cash').toBe(cell('cash'));
        expect(validateTransactions).not.toHaveBeenCalled();
    });

    it('(e) an FX with the same currency on both legs: cashTo is a format problem, the From cash is not marked', async () => {
        mount({mode: 'create', items: fxPair('EUR', 'EUR'), commitOnSave: false, onPushDraft: vi.fn()});
        await screen.findByTestId('tx-form-dual-split');
        await screen.findByTestId('tx-form-dual-error'); // premise: the form itself already sees two equal currencies
        expect(markedCells(), 'premise: nothing is marked before the click').toHaveLength(0);

        await clickValidateNow();
        await waitFor(() => expect(markedCells().length).toBeGreaterThan(0));

        expectMarked('cashTo', 'format');
        expectNotMarked('cash');
        expectSummary(1);
        expect(focusedCell(), 'the focus is inside the To cash').toBe(cell('cashTo'));
        expect(validateTransactions, 'a form with a problem of its own is not sent').not.toHaveBeenCalled();
        expect(commitTransactions).not.toHaveBeenCalled();
    });

    it('(f) a transfer with the same broker on both sides: brokerTo is a format problem, the From broker is not marked', async () => {
        const sender = txRow({id: 101, broker_id: 17, type: 'TRANSFER', quantity: '-5', cash: null, related_transaction_id: 202, partner_broker_id: 17});
        const receiver = txRow({id: 202, broker_id: 17, type: 'TRANSFER', quantity: '5', cash: null, related_transaction_id: 101, partner_broker_id: 17});
        mount({mode: 'create', items: [sender, receiver], commitOnSave: false, onPushDraft: vi.fn()});
        await screen.findByTestId('tx-form-dual-split');
        await screen.findByTestId('tx-form-dual-error'); // premise: the form itself already sees two equal brokers
        expect(markedCells(), 'premise: nothing is marked before the click').toHaveLength(0);

        await clickValidateNow();
        await waitFor(() => expect(markedCells().length).toBeGreaterThan(0));

        expectMarked('brokerTo', 'format');
        expectNotMarked('broker');
        expectSummary(1);
        expect(focusedCell(), 'the focus is inside the To broker').toBe(cell('brokerTo'));
        expect(validateTransactions).not.toHaveBeenCalled();
        expect(commitTransactions).not.toHaveBeenCalled();
    });
});
