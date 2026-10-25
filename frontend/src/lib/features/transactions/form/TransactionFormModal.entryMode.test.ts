// @vitest-environment jsdom
/**
 * TransactionFormModal — «Total amount / Unit price» badge of the single BUY / SELL form (#47), component test (Vitest + jsdom).
 *
 * The contract:
 *   - `data-testid="tx-form-entry-mode"` is a badge of two buttons, `…-amount` and `…-unit-price`, the state in `aria-pressed`
 *     (amount pressed by default). It exists ONLY for a single BUY or SELL (never for a DEPOSIT, an FX or a transfer pair,
 *     nor in view mode);
 *   - amount mode: a read-only `tx-form-unit-price-computed` carries the calculated price in `data-value` (empty while
 *     nothing can be calculated); the amount is the field the user types;
 *   - unit-price mode: an editable `tx-form-unit-price` input is shown and the cash amount (`tx-form-cash-amount`, still
 *     editable) receives the calculated amount;
 *   - the driver is the value written last; the other value comes from the BACKEND (`convertTradeAmount`, mocked here as a
 *     lookup table keyed by the request: the test never calculates). The request is {asset_id, quantity, mode, value}.
 *     Typing an amount hands the driver (and the badge) back to amount; a quantity or asset edit keeps it.
 *
 * What this file leaves to the E2E (transactions-modals.spec.ts):
 *   - a real backend answer (here every answer is a table entry) and the comma-decimal typing (`83,40`);
 *   - that no `/transactions/commit` goes out (this harness mocks the commit api, so «nothing was committed» says nothing).
 *
 * Absences are proved with a positive control, not with the clock: a request that must NOT have gone out is shown by the
 * request that must, arriving later with every earlier call accounted for. The asset is picked through the real select, from
 * the real asset store seeded with `mergeAssets`; the broker comes from `defaultBrokerId`.
 *
 * Asserted: data-testid / data-value / aria-pressed only, never a translated label.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {mergeAssets, resetAssetStore} from '$lib/stores/reference/assetStore';
import {schemas} from '$lib/api/generated';
import {commitTransactions, validateTransactions} from '$lib/features/transactions/txCommitApi';
import {convertTradeAmount} from '$lib/features/transactions/form/txTradeAmountApi';
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
// #47: the backend's calculator is a lookup table keyed by the request. The test never does the arithmetic: an answer
// is written next to the request that earns it, and a request nobody wrote an answer for gets `null` (a refusal).
const {answers, answerKey, answer} = vi.hoisted(() => {
    type Request = {asset_id: number; quantity: string; mode: string; value: string};
    const answers = new Map<string, string>();
    const answerKey = (request: Request) => `${request.asset_id}|${request.mode}|${request.quantity}|${request.value}`;
    const answer = (assetId: number, mode: 'amount_to_price' | 'price_to_amount', quantity: string, value: string, result: string) => {
        answers.set(answerKey({asset_id: assetId, mode, quantity, value}), result);
    };
    return {answers, answerKey, answer};
});
vi.mock('$lib/features/transactions/form/txTradeAmountApi', () => ({
    convertTradeAmount: vi.fn(async (request: {asset_id: number; quantity: string; mode: string; value: string}) => {
        const result = answers.get(answerKey(request));
        return result === undefined ? null : {result, quote_base_quantity: 1};
    }),
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

function typeMetadata(code: string, fields: Record<string, unknown>): Record<string, unknown> {
    return {code, name: code, description: code, icon_slug: code.toLowerCase(), doc_slug: code.toLowerCase(), requires_link: false, event_compatible: false, ...fields};
}

const TYPES_RESPONSE = schemas.TXTypesResponse.parse({
    transaction_types: [
        typeMetadata('DEPOSIT', {asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'positive'}),
        typeMetadata('BUY', {asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'positive', cash_sign: 'negative'}),
        typeMetadata('SELL', {asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'negative', cash_sign: 'positive'}),
        typeMetadata('TRANSFER', {
            asset_mode: 'required',
            cash_mode: 'forbidden',
            quantity_mode: 'required',
            requires_link: true,
            quantity_sign: 'nonzero',
            cash_sign: 'zero',
            pair_form_layout: 'transfer_asset',
            cost_basis_mode: 'forbidden',
            cost_basis_pair: ['forbidden', 'required_qty_pos'],
        }),
        typeMetadata('FX_CONVERSION', {asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', requires_link: true, quantity_sign: 'zero', cash_sign: 'nonzero', pair_form_layout: 'fx'}),
    ],
    event_types: [],
});

import TransactionFormModal from './TransactionFormModal.svelte';

const ASSET = 42;
const OTHER_ASSET = 43;
/** Past the debounce the form may put before a request, short of the test's own budget. */
const WAIT = {timeout: 4_000};

/** A create form on the shared broker; Apply pushes the draft (no commit on the wire). */
function mount(props: Record<string, unknown> = {}) {
    const onClose = vi.fn();
    const onPushDraft = vi.fn();
    return {onClose, onPushDraft, ...render(TransactionFormModal, {open: true, mode: 'create', items: null, defaultBrokerId: 17, commitOnSave: false, onPushDraft, onClose, ...props})};
}

function txRow(overrides: Record<string, unknown> = {}) {
    return {
        id: 101,
        broker_id: 17,
        asset_id: ASSET,
        type: 'BUY',
        date: '2024-03-10',
        quantity: '',
        cash: {code: 'EUR', amount: ''},
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

/** A single BUY or SELL seeded with its asset and broker, quantity and cash still blank. */
const seededSingle = (type: 'BUY' | 'SELL') => ({items: [txRow({type})]});

type TradeRequest = {asset_id: number; quantity: string; mode: string; value: string};

// ---------------------------------------------------------------------------------------------------------------------
// What this file observes and does
// ---------------------------------------------------------------------------------------------------------------------

const entryBadge = (): HTMLElement | null => screen.queryByTestId('tx-form-entry-mode');
const amountButton = (): HTMLElement => screen.getByTestId('tx-form-entry-mode-amount');
const unitPriceButton = (): HTMLElement => screen.getByTestId('tx-form-entry-mode-unit-price');
const computedPrice = (): HTMLElement => screen.getByTestId('tx-form-unit-price-computed');
const unitPriceInput = (): HTMLInputElement => screen.getByTestId('tx-form-unit-price') as HTMLInputElement;
const cashAmount = (): HTMLInputElement => screen.getByTestId('tx-form-cash-amount') as HTMLInputElement;
/** The calculated price shown in amount mode: `''` while the attribute is empty or absent. */
const computedValue = (): string => computedPrice().getAttribute('data-value') ?? '';

/** Every request the form sent to the backend, in order. */
const requests = (): TradeRequest[] => vi.mocked(convertTradeAmount).mock.calls.map(([request]) => request as unknown as TradeRequest);

/** Wait for the request `{asset_id, quantity, mode, value}` (exactly this shape) to have gone out. */
function asked(mode: 'amount_to_price' | 'price_to_amount', quantity: string, value: string, assetId = ASSET): Promise<void> {
    return waitFor(() => expect(requests(), `the form asks ${mode} for quantity ${quantity}, value ${value}`).toContainEqual({asset_id: assetId, quantity, mode, value}), WAIT);
}

function expectPressed(which: 'amount' | 'unit-price'): void {
    expect(amountButton(), 'the amount button').toHaveAttribute('aria-pressed', which === 'amount' ? 'true' : 'false');
    expect(unitPriceButton(), 'the unit price button').toHaveAttribute('aria-pressed', which === 'unit-price' ? 'true' : 'false');
}

async function typeQuantity(value: string): Promise<void> {
    await fireEvent.input(screen.getByTestId('tx-form-quantity'), {target: {value}});
}

/** The cash amount, typed and left (the way the user does it). */
async function typeAmount(value: string): Promise<void> {
    const input = cashAmount();
    await fireEvent.input(input, {target: {value}});
    await fireEvent.blur(input);
}

async function typeUnitPrice(value: string): Promise<void> {
    await fireEvent.input(unitPriceInput(), {target: {value}});
}

/** Pick an asset through the real select: the list is the real store, seeded in `beforeEach`. */
async function pickAsset(id: number): Promise<void> {
    await fireEvent.click(await screen.findByTestId('tx-form-asset-trigger'));
    const list = await screen.findByRole('listbox');
    await fireEvent.click(within(list).getByTestId(`search-select-option-${id}`));
    await waitFor(() => expect(screen.queryByRole('listbox')).toBeNull());
}

function openTypeSelect() {
    return fireEvent.click(within(screen.getByTestId('tx-form-type')).getByRole('combobox'));
}

async function chooseDualType(code: 'FX_CONVERSION' | 'TRANSFER') {
    await openTypeSelect();
    await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
    const dropdown = screen.getByRole('listbox').parentElement as HTMLElement;
    await fireEvent.click(within(dropdown).getByTestId(`search-select-option-${code}`));
    await waitFor(() => expect(screen.getByTestId('tx-form-dual-split')).toBeInTheDocument());
}

function resetGuideState() {
    guideState.active = null;
    guideState.queuedGuides = [];
}

/** Quantity 12 and an amount of 1000.8 in amount mode, the calculated price on screen. Calls so far are forgotten. */
async function reachAmountDriverWithPrice(): Promise<void> {
    await screen.findByTestId('tx-form-quantity');
    await typeQuantity('12');
    await typeAmount('1000.8');
    await waitFor(() => expect(computedValue()).toBe('83.4'), WAIT);
}

/** From a blank BUY: asset, quantity 12, the badge on Unit price, a price of 83.4: the amount calculated, the price the driver. Calls so far are forgotten. */
async function reachUnitPriceDriver(): Promise<void> {
    await screen.findByTestId('tx-form-quantity');
    await pickAsset(ASSET);
    await typeQuantity('12');
    await fireEvent.click(unitPriceButton());
    await screen.findByTestId('tx-form-unit-price');
    await typeUnitPrice('83.4');
    await asked('price_to_amount', '12', '83.4');
    await waitFor(() => expect(cashAmount()).toHaveValue('1000.8'), WAIT);
    vi.mocked(convertTradeAmount).mockClear();
}

describe('TransactionFormModal — «Total amount / Unit price» (#47)', () => {
    beforeEach(async () => {
        vi.clearAllMocks();
        guideAnchors.clear();
        resetGuideState();
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_RESPONSE);
        resetAssetStore();
        mergeAssets([
            {id: ASSET, display_name: 'Entry mode asset A', currency: 'EUR', active: true},
            {id: OTHER_ASSET, display_name: 'Entry mode asset B', currency: 'EUR', active: true},
        ]);
        // What the backend would answer, written next to the request that earns it (no arithmetic here).
        answers.clear();
        answer(ASSET, 'amount_to_price', '12', '1000.8', '83.4');
        answer(ASSET, 'price_to_amount', '12', '83.4', '1000.8');
        answer(ASSET, 'amount_to_price', '12', '1000.9', '83.4083333333');
        answer(ASSET, 'price_to_amount', '10', '83.4', '834');
        answer(ASSET, 'amount_to_price', '10', '1000.8', '100.08');
        answer(OTHER_ASSET, 'price_to_amount', '12', '83.4', '1200');
        await setupI18n();
        await ensureTypesLoaded();
    });

    afterEach(() => {
        cleanup();
        resetAssetStore();
        guideAnchors.clear();
        resetGuideState();
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (a) who gets the badge
    // -----------------------------------------------------------------------------------------------------------------
    describe('(a) the badge', () => {
        it.each(['BUY', 'SELL'] as const)('a single %s has the badge, the amount pressed by default, the calculated price and no unit-price input', async (type) => {
            mount(seededSingle(type));
            await screen.findByTestId('tx-form-quantity');

            expect(entryBadge(), `the ${type} form has the badge`).not.toBeNull();
            expectPressed('amount');
            expect(within(entryBadge() as HTMLElement).getByTestId('tx-form-entry-mode-amount'), 'the two buttons live inside the badge').toBeInTheDocument();
            expect(within(entryBadge() as HTMLElement).getByTestId('tx-form-entry-mode-unit-price')).toBeInTheDocument();
            expect(computedPrice(), 'the calculated price is not an input to type in').not.toBeInstanceOf(HTMLInputElement);
            expect(screen.queryByTestId('tx-form-unit-price'), 'amount mode has no unit-price input').toBeNull();
        });

        it('a blank create form (BUY by default) has the badge too', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            expect(entryBadge()).not.toBeNull();
            expectPressed('amount');
        });

        it('a DEPOSIT has no badge, no calculated price and no unit-price input; back to BUY the badge returns', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            expect(entryBadge(), 'premise: the BUY form has the badge').not.toBeNull();

            await openTypeSelect();
            await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
            const dropdown = screen.getByRole('listbox').parentElement as HTMLElement;
            await fireEvent.click(within(dropdown).getByTestId('search-select-option-DEPOSIT'));
            // A DEPOSIT has no quantity: its going proves the form is the DEPOSIT one before the absence is asserted.
            await waitFor(() => expect(screen.queryByTestId('tx-form-quantity')).toBeNull());
            expect(screen.getByTestId('tx-form-cash-amount'), 'the DEPOSIT keeps its cash').toBeInTheDocument();

            expect(entryBadge(), 'a DEPOSIT has no badge').toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price-computed')).toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price')).toBeNull();

            await openTypeSelect();
            await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
            await fireEvent.click(within(screen.getByRole('listbox').parentElement as HTMLElement).getByTestId('search-select-option-BUY'));
            await waitFor(() => expect(entryBadge()).not.toBeNull());
        });

        it('an FX pair has no badge', async () => {
            mount();
            await chooseDualType('FX_CONVERSION');
            expect(entryBadge(), 'an FX pair has no badge').toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price-computed')).toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price')).toBeNull();
        });

        it('a transfer pair has no badge', async () => {
            mount();
            await chooseDualType('TRANSFER');
            expect(entryBadge(), 'a transfer pair has no badge').toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price-computed')).toBeNull();
        });

        it('a BUY in view (readonly) mode has no badge', async () => {
            mount({mode: 'view', items: [txRow({type: 'BUY', quantity: '12', cash: {code: 'EUR', amount: '-1000.8'}})]});
            // The readonly form is on screen (its quantity is there, disabled) before the absence is asserted.
            expect(await screen.findByTestId('tx-form-quantity')).toBeDisabled();

            expect(entryBadge(), 'a readonly form has no badge').toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price-computed')).toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price')).toBeNull();
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (b) amount mode
    // -----------------------------------------------------------------------------------------------------------------
    describe('(b) amount mode: the backend calculates the unit price', () => {
        it.each(['BUY', 'SELL'] as const)('a %s with quantity 12 and amount 1000.8 asks amount_to_price and shows the answer in data-value', async (type) => {
            mount(seededSingle(type));
            await screen.findByTestId('tx-form-quantity');
            expect(computedValue(), 'premise: nothing can be calculated yet').toBe('');

            await typeQuantity('12');
            await typeAmount('1000.8');

            await asked('amount_to_price', '12', '1000.8');
            await waitFor(() => expect(computedPrice()).toHaveAttribute('data-value', '83.4'), WAIT);
            expect(cashAmount(), 'the amount stays as typed and editable').toHaveValue('1000.8');
            expect(cashAmount()).toBeEnabled();
            expectPressed('amount');
        });

        it('the request carries the asset the user picked from the real select', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('12');
            await typeAmount('1000.8');

            await asked('amount_to_price', '12', '1000.8', ASSET);
            await waitFor(() => expect(computedValue()).toBe('83.4'), WAIT);
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (c) unit-price mode
    // -----------------------------------------------------------------------------------------------------------------
    describe('(c) unit-price mode: the backend calculates the amount', () => {
        it('switching to Unit price shows the editable price input; typing 83.4 with quantity 12 asks price_to_amount and fills the amount', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('12');

            await fireEvent.click(unitPriceButton());
            expectPressed('unit-price');
            const price = await screen.findByTestId('tx-form-unit-price');
            expect(price, 'an editable input').toBeEnabled();
            expect(price).not.toHaveAttribute('readonly');
            expect(screen.queryByTestId('tx-form-unit-price-computed'), 'unit-price mode has no calculated-price element').toBeNull();

            await typeUnitPrice('83.4');
            await asked('price_to_amount', '12', '83.4');
            await waitFor(() => expect(cashAmount()).toHaveValue('1000.8'), WAIT);
            expect(unitPriceInput(), 'the price stays as typed').toHaveValue('83.4');
            expect(cashAmount(), 'the calculated amount is still editable').toBeEnabled();
            expect(cashAmount()).not.toHaveAttribute('readonly');
        });

        it('on Unit price, a zero price asks nothing: the first request is the one for the price that makes it calculable', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('12');
            await fireEvent.click(unitPriceButton());
            await screen.findByTestId('tx-form-unit-price');

            await typeUnitPrice('0');
            await typeUnitPrice('83.4');
            await asked('price_to_amount', '12', '83.4');
            expect(
                requests().every((request) => request.mode === 'price_to_amount' && request.value === '83.4'),
                `nothing was asked for the blank amount or the zero price, only for the price: ${JSON.stringify(requests())}`,
            ).toBe(true);
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (d) the amount edit gives the driver back
    // -----------------------------------------------------------------------------------------------------------------
    describe('(d) editing the amount after a unit price hands the driver back to the amount', () => {
        it('the price follows through amount_to_price, the badge is back on amount, and no price_to_amount goes out for that edit', async () => {
            mount();
            await reachUnitPriceDriver();

            await typeAmount('1000.9');

            await asked('amount_to_price', '12', '1000.9');
            await waitFor(() => expect(computedPrice()).toHaveAttribute('data-value', '83.4083333333'), WAIT);
            expectPressed('amount');
            expect(cashAmount(), 'the amount is what the user typed').toHaveValue('1000.9');
            expect(
                requests().filter((request) => request.mode === 'price_to_amount'),
                'the edit of the amount asked no price_to_amount',
            ).toEqual([]);
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (e) a quantity or asset edit keeps the driver
    // -----------------------------------------------------------------------------------------------------------------
    describe('(e) a quantity or asset edit keeps the driver and recalculates the other value', () => {
        it('driver unit price: a new quantity asks price_to_amount again, the amount follows, the price is kept', async () => {
            mount();
            await reachUnitPriceDriver();

            await typeQuantity('10');

            await asked('price_to_amount', '10', '83.4');
            await waitFor(() => expect(cashAmount()).toHaveValue('834'), WAIT);
            expectPressed('unit-price');
            expect(unitPriceInput(), 'the price the user wrote is untouched').toHaveValue('83.4');
            expect(
                requests().filter((request) => request.mode === 'amount_to_price'),
                'a quantity edit asked no amount_to_price while the unit price drives',
            ).toEqual([]);
        });

        it('driver amount: a new quantity asks amount_to_price again, the price follows, the amount is kept', async () => {
            mount(seededSingle('BUY'));
            await reachAmountDriverWithPrice();
            vi.mocked(convertTradeAmount).mockClear();

            await typeQuantity('10');

            await asked('amount_to_price', '10', '1000.8');
            await waitFor(() => expect(computedPrice()).toHaveAttribute('data-value', '100.08'), WAIT);
            expect(cashAmount(), 'the amount the user wrote is untouched').toHaveValue('1000.8');
            expect(
                requests().filter((request) => request.mode === 'price_to_amount'),
                'a quantity edit asked no price_to_amount while the amount drives',
            ).toEqual([]);
        });

        it('driver unit price: picking another asset asks price_to_amount for the new asset, with the same price', async () => {
            mount();
            await reachUnitPriceDriver();

            await pickAsset(OTHER_ASSET);

            await asked('price_to_amount', '12', '83.4', OTHER_ASSET);
            await waitFor(() => expect(cashAmount()).toHaveValue('1200'), WAIT);
            expectPressed('unit-price');
            expect(unitPriceInput()).toHaveValue('83.4');
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (f) nothing to ask
    // -----------------------------------------------------------------------------------------------------------------
    describe('(f) no request while there is nothing to ask', () => {
        it('a blank or zero quantity asks nothing; the quantity that makes it complete is the first request', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);

            await typeAmount('1000.8'); // quantity still blank
            await typeQuantity('0');
            await typeQuantity('12');

            await asked('amount_to_price', '12', '1000.8');
            expect(
                requests().every((request) => request.quantity === '12'),
                `no request left with a blank or zero quantity: ${JSON.stringify(requests())}`,
            ).toBe(true);
        });

        it('no asset asks nothing; picking the asset is what sends the first request', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');

            await typeQuantity('12');
            await typeAmount('1000.8'); // no asset yet
            await pickAsset(ASSET);

            await asked('amount_to_price', '12', '1000.8');
            expect(
                requests().every((request) => request.asset_id === ASSET),
                `no request left without the asset: ${JSON.stringify(requests())}`,
            ).toBe(true);
        });

        it('an amount of zero or a negative one asks nothing; a positive amount asks', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('12');

            await typeAmount('0');
            await typeAmount('-5');
            await typeAmount('1000.8');

            await asked('amount_to_price', '12', '1000.8');
            expect(
                requests().every((request) => request.value === '1000.8'),
                `no request left for a zero or negative amount: ${JSON.stringify(requests())}`,
            ).toBe(true);
        });

        it('an amount past six decimals asks nothing: it is red in its own field', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('12');

            await typeAmount('1000.1234567');
            await typeAmount('1000.8');

            await asked('amount_to_price', '12', '1000.8');
            expect(
                requests().every((request) => request.value === '1000.8'),
                `no request left for the seven-decimal amount: ${JSON.stringify(requests())}`,
            ).toBe(true);
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (g) a refusal leaves the form usable
    // -----------------------------------------------------------------------------------------------------------------
    describe('(g) the backend answering null', () => {
        it('amount mode: the stale price goes away, ⚡ and Save are not blocked, and the next quantity calculates again', async () => {
            const {onPushDraft} = mount(seededSingle('BUY'));
            await reachAmountDriverWithPrice();

            await typeQuantity('7'); // nobody wrote an answer for it: the backend refuses
            await asked('amount_to_price', '7', '1000.8');
            await waitFor(() => expect(computedValue(), 'the price of the old quantity is not kept').toBe(''), WAIT);

            expect(screen.getByTestId('tx-form-validate-now'), '⚡ is not blocked by an empty calculated price').toBeEnabled();
            await waitFor(() => expect(screen.getByTestId('tx-form-save'), 'Save is not blocked either').toBeEnabled());

            await fireEvent.click(screen.getByTestId('tx-form-validate-now'));
            await waitFor(() => expect(validateTransactions).toHaveBeenCalled());
            await fireEvent.click(screen.getByTestId('tx-form-save'));
            expect(onPushDraft, 'the form can still be applied').toHaveBeenCalledTimes(1);
            expect(commitTransactions).not.toHaveBeenCalled();
        });

        it('amount mode: after a refusal the next calculable quantity fills the price again', async () => {
            mount(seededSingle('BUY'));
            await reachAmountDriverWithPrice();
            await typeQuantity('7');
            await waitFor(() => expect(computedValue()).toBe(''), WAIT);

            await typeQuantity('12');

            await waitFor(() => expect(computedValue()).toBe('83.4'), WAIT);
        });

        it('unit-price mode: a refused price leaves the amount empty and the form usable; the next price fills it', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('12');
            await fireEvent.click(unitPriceButton());
            await screen.findByTestId('tx-form-unit-price');

            await typeUnitPrice('99'); // nobody wrote an answer for it
            await asked('price_to_amount', '12', '99');
            await tick();
            expect(cashAmount(), 'nothing was calculated: the amount stays empty').toHaveValue('');
            expect(unitPriceInput(), 'the price stays as typed').toHaveValue('99');
            expect(cashAmount(), 'the amount can still be typed').toBeEnabled();

            await typeUnitPrice('83.4');
            await waitFor(() => expect(cashAmount()).toHaveValue('1000.8'), WAIT);
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (h) back to amount
    // -----------------------------------------------------------------------------------------------------------------
    describe('(h) switching the badge', () => {
        it('back to amount keeps the calculated amount on screen, drops the price input and shows the price again', async () => {
            mount();
            await reachUnitPriceDriver();

            await fireEvent.click(amountButton());

            expectPressed('amount');
            expect(cashAmount(), 'the amount stays on screen').toHaveValue('1000.8');
            await waitFor(() => expect(computedPrice()).toHaveAttribute('data-value', '83.4'), WAIT);
            expect(screen.queryByTestId('tx-form-unit-price'), 'the price input goes away').toBeNull();
            await asked('amount_to_price', '12', '1000.8');
        });

        it('to Unit price keeps the amount that was typed', async () => {
            mount(seededSingle('BUY'));
            await reachAmountDriverWithPrice();

            await fireEvent.click(unitPriceButton());

            expectPressed('unit-price');
            await screen.findByTestId('tx-form-unit-price');
            expect(cashAmount(), 'switching the badge does not clear the amount').toHaveValue('1000.8');
        });
    });
});
