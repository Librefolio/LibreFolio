// @vitest-environment jsdom
/**
 * TransactionFormModal — «Total amount / Unit price» of the single BUY / SELL form (#47), component test (Vitest + jsdom).
 *
 * The calculation is the form's own (W5-9, `txTradeAmount.ts`): synchronous, exact decimal arithmetic, no network. So
 * nothing is mocked for it: the asset comes from the real asset store seeded with `mergeAssets` (with its
 * `quote_base_quantity`, 1 or 100, or without one), and the expectations below are sums a person can check on paper.
 * The arithmetic itself (ties, limits, parity with the backend it replaced) is proved in `txTradeAmount.test.ts`.
 *
 * The contract:
 *   - `data-testid="tx-form-entry-mode"` is a badge of two buttons, `…-amount` and `…-unit-price`, the state in `aria-pressed`
 *     (amount pressed by default). It exists ONLY for a single BUY or SELL being edited (never for a DEPOSIT, an FX or a
 *     transfer pair, nor in view mode);
 *   - amount mode: a read-only `tx-form-unit-price-computed` carries the calculated price in `data-value` (empty while
 *     nothing can be calculated); the amount is the field the user types;
 *   - unit-price mode: an editable `tx-form-unit-price` input is shown and the cash amount (`tx-form-cash-amount`, still
 *     editable) receives the calculated amount;
 *   - the driver is the value written last; the other value is calculated from it. Typing an amount hands the driver (and
 *     the badge) back to amount; a quantity or asset edit keeps it;
 *   - an asset the store does not know (yet) calculates nothing; one whose row carries no quote base counts as base 1;
 *   - view mode of a saved BUY / SELL shows both the amount (cash cell) and the unit price, read-only, with no badge;
 *   - the payload carries the amount only, never a unit price.
 *
 * What this file leaves to the E2E (transactions-modals.spec.ts): the comma-decimal typing (`83,40`) on a real page and
 * that no `/transactions/commit` goes out (this harness mocks the commit api, so «nothing was committed» says nothing).
 *
 * Absences are proved with a positive control, not with the clock: a price that must NOT be there is shown to be missing
 * for the reason named (the asset is unknown), then the reason is removed and the price appears. The asset is picked
 * through the real select; the broker comes from `defaultBrokerId`.
 *
 * Asserted: data-testid / data-value / aria-pressed only, never a translated label.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {mergeAssets, resetAssetStore} from '$lib/stores/reference/assetStore';
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
/** A bond: the quote refers to 100 units. */
const BOND = 44;
/** An asset whose store row carries no quote base. */
const NO_BASE = 43;
/** An asset the store does not hold (yet). */
const UNKNOWN_ASSET = 999;

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

/** The calculated price in amount mode, once the form has caught up with what was typed. */
async function expectComputed(value: string): Promise<void> {
    await waitFor(() => expect(computedPrice()).toHaveAttribute('data-value', value));
}

/** Quantity 12 and an amount of 1000.8 in amount mode on the seeded BUY: the calculated price (83.4) on screen. */
async function reachAmountDriverWithPrice(): Promise<void> {
    await screen.findByTestId('tx-form-quantity');
    await typeQuantity('12');
    await typeAmount('1000.8');
    await expectComputed('83.4');
}

/** From a blank BUY: asset, quantity 12, the badge on Unit price, a price of 83.4: the amount calculated, the price the driver. */
async function reachUnitPriceDriver(assetId = ASSET): Promise<void> {
    await screen.findByTestId('tx-form-quantity');
    await pickAsset(assetId);
    await typeQuantity('12');
    await fireEvent.click(unitPriceButton());
    await screen.findByTestId('tx-form-unit-price');
    await typeUnitPrice('83.4');
    await waitFor(() => expect(cashAmount()).toHaveValue('1000.8'));
}

describe('TransactionFormModal — «Total amount / Unit price» (#47)', () => {
    beforeEach(async () => {
        vi.clearAllMocks();
        guideAnchors.clear();
        resetGuideState();
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_RESPONSE);
        resetAssetStore();
        mergeAssets([
            {id: ASSET, display_name: 'Entry mode asset A', currency: 'EUR', quote_base_quantity: 1, active: true},
            {id: BOND, display_name: 'Entry mode bond (base 100)', currency: 'EUR', quote_base_quantity: 100, active: true},
            // A row of an older payload: no quote base at all.
            {id: NO_BASE, display_name: 'Entry mode asset without base', currency: 'EUR', active: true},
        ]);
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

        it('an FX pair has no badge and no unit price', async () => {
            mount();
            await chooseDualType('FX_CONVERSION');
            expect(entryBadge(), 'an FX pair has no badge').toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price-computed')).toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price')).toBeNull();
        });

        it('a transfer pair has no badge and no unit price', async () => {
            mount();
            await chooseDualType('TRANSFER');
            expect(entryBadge(), 'a transfer pair has no badge').toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price-computed')).toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price')).toBeNull();
        });

        it('a saved BUY opened for editing has the badge, and its price is calculated at once from the amount it holds', async () => {
            mount({mode: 'edit', items: [txRow({type: 'BUY', quantity: '12', cash: {code: 'EUR', amount: '-1000.8'}})]});
            await screen.findByTestId('tx-form-quantity');

            expect(entryBadge()).not.toBeNull();
            expectPressed('amount');
            await expectComputed('83.4');
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (b) amount mode
    // -----------------------------------------------------------------------------------------------------------------
    describe('(b) amount mode: the form calculates the unit price', () => {
        it.each(['BUY', 'SELL'] as const)('a %s with quantity 12 and amount 1000.8 shows 83.4 in data-value', async (type) => {
            mount(seededSingle(type));
            await screen.findByTestId('tx-form-quantity');
            expect(computedValue(), 'premise: nothing can be calculated yet').toBe('');

            await typeQuantity('12');
            await typeAmount('1000.8');

            await expectComputed('83.4');
            expect(cashAmount(), 'the amount stays as typed and editable').toHaveValue('1000.8');
            expect(cashAmount()).toBeEnabled();
            expectPressed('amount');
        });

        it('the asset the user picked from the real select decides the base: base 1 against base 100', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('1000');
            await typeAmount('985');

            await pickAsset(ASSET);
            await expectComputed('0.985');

            await pickAsset(BOND);
            await expectComputed('98.5');
        });

        it('the price keeps up to 12 decimals: 1000.9 over 12 units', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeAmount('1000.9');
            await expectComputed('83.408333333333');
        });

        it('a tie rounds half-even, end to end: 1 over 8192 units ends on …312|5, so it stays on 2', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('8192');
            await typeAmount('1');
            await expectComputed('0.000122070312');

            await typeAmount('3'); // …937|5: the odd 7 goes up
            await expectComputed('0.000366210938');
        });

        it('an integer price carries no decimal point, and nothing trails', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('10');
            await typeAmount('1000');
            await expectComputed('100');
        });

        it('an asset whose store row has no quote base counts as base 1', async () => {
            mount({items: [txRow({asset_id: NO_BASE})]});
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeAmount('1000.8');
            await expectComputed('83.4');
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (c) unit-price mode
    // -----------------------------------------------------------------------------------------------------------------
    describe('(c) unit-price mode: the form calculates the amount', () => {
        it('switching to Unit price shows the editable price input; typing 83.4 with quantity 12 fills the amount with 1000.8', async () => {
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
            await waitFor(() => expect(cashAmount()).toHaveValue('1000.8'));
            expect(unitPriceInput(), 'the price stays as typed').toHaveValue('83.4');
            expect(cashAmount(), 'the calculated amount is still editable').toBeEnabled();
            expect(cashAmount()).not.toHaveAttribute('readonly');
        });

        it('a bond (base 100): 1000 units at 98.5 are 985, not 98500', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(BOND);
            await typeQuantity('1000');
            await fireEvent.click(unitPriceButton());
            await screen.findByTestId('tx-form-unit-price');

            await typeUnitPrice('98.5');
            await waitFor(() => expect(cashAmount()).toHaveValue('985'));
        });

        it('the amount is rounded half-even to its 6 decimals: a price of 0.0000025 for one unit is 0.000002, 0.0000035 is 0.000004', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('1');
            await fireEvent.click(unitPriceButton());
            await screen.findByTestId('tx-form-unit-price');

            await typeUnitPrice('0.0000025');
            await waitFor(() => expect(cashAmount()).toHaveValue('0.000002'));
            await typeUnitPrice('0.0000035');
            await waitFor(() => expect(cashAmount()).toHaveValue('0.000004'));
        });

        it('a zero price calculates nothing; the next price that makes it calculable fills the amount', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('12');
            await fireEvent.click(unitPriceButton());
            await screen.findByTestId('tx-form-unit-price');

            await typeUnitPrice('0');
            expect(cashAmount(), 'a zero price gives no amount').toHaveValue('');
            await typeUnitPrice('83.4');
            await waitFor(() => expect(cashAmount()).toHaveValue('1000.8'));
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (d) the amount edit gives the driver back
    // -----------------------------------------------------------------------------------------------------------------
    describe('(d) editing the amount after a unit price hands the driver back to the amount', () => {
        it('the price follows the new amount, the badge is back on amount, and the amount is what the user typed', async () => {
            mount();
            await reachUnitPriceDriver();
            expectPressed('unit-price');

            await typeAmount('1000.9');

            expectPressed('amount');
            await expectComputed('83.408333333333');
            expect(cashAmount(), 'the amount is what the user typed').toHaveValue('1000.9');
            expect(screen.queryByTestId('tx-form-unit-price'), 'the price input is gone').toBeNull();
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (e) a quantity or asset edit keeps the driver
    // -----------------------------------------------------------------------------------------------------------------
    describe('(e) a quantity or asset edit keeps the driver and recalculates the other value', () => {
        it('driver unit price: a new quantity recalculates the amount, the price is kept', async () => {
            mount();
            await reachUnitPriceDriver();

            await typeQuantity('10');

            await waitFor(() => expect(cashAmount()).toHaveValue('834'));
            expectPressed('unit-price');
            expect(unitPriceInput(), 'the price the user wrote is untouched').toHaveValue('83.4');
        });

        it('driver amount: a new quantity recalculates the price, the amount is kept', async () => {
            mount(seededSingle('BUY'));
            await reachAmountDriverWithPrice();

            await typeQuantity('10');

            await expectComputed('100.08');
            expect(cashAmount(), 'the amount the user wrote is untouched').toHaveValue('1000.8');
            expectPressed('amount');
        });

        it('driver unit price: picking the bond keeps the price and recalculates the amount on base 100', async () => {
            mount();
            await reachUnitPriceDriver(ASSET);

            await pickAsset(BOND);

            await waitFor(() => expect(cashAmount()).toHaveValue('10.008')); // 12 / 100 × 83.4
            expectPressed('unit-price');
            expect(unitPriceInput()).toHaveValue('83.4');

            await pickAsset(ASSET);
            await waitFor(() => expect(cashAmount()).toHaveValue('1000.8'));
        });

        it('driver amount: picking the bond keeps the amount and recalculates the price on base 100', async () => {
            mount({items: [txRow()]});
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeAmount('1000.8');
            await expectComputed('83.4');

            await pickAsset(BOND);

            await expectComputed('8340'); // 1000.8 × 100 / 12
            expect(cashAmount()).toHaveValue('1000.8');
            expectPressed('amount');
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (f) nothing to calculate
    // -----------------------------------------------------------------------------------------------------------------
    describe('(f) nothing to calculate', () => {
        it('a blank or zero quantity calculates nothing; the quantity that makes it complete does', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');

            await typeAmount('1000.8'); // quantity still blank
            expect(computedValue(), 'blank quantity').toBe('');
            await typeQuantity('0');
            expect(computedValue(), 'zero quantity').toBe('');

            await typeQuantity('12');
            await expectComputed('83.4');
        });

        it('an amount of zero, a negative one or a blank one calculates nothing and takes away the old price; a positive one calculates', async () => {
            mount(seededSingle('BUY'));
            await reachAmountDriverWithPrice();

            await typeAmount('0');
            await expectComputed('');
            await typeAmount('1000.8');
            await expectComputed('83.4');

            await typeAmount('-5');
            await expectComputed('');
            await typeAmount('1000.8');
            await expectComputed('83.4');

            await typeAmount('');
            await expectComputed('');
        });

        it('an amount past six decimals calculates nothing: it is red in its own field', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');

            await typeAmount('1000.1234567');
            expect(computedValue()).toBe('');
            await typeAmount('1000.8');
            await expectComputed('83.4');
        });

        it('an asset the store does not know calculates nothing, in amount mode; once the store has it the price appears', async () => {
            mount({items: [txRow({asset_id: UNKNOWN_ASSET})]});
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeAmount('1000.8');
            expect(computedValue(), 'no asset row, no quote base, no price').toBe('');

            // Positive control: the same form, the asset arrives (the store loads late) → the price follows.
            mergeAssets([{id: UNKNOWN_ASSET, display_name: 'Arrived late', currency: 'EUR', quote_base_quantity: 1, active: true}]);
            await expectComputed('83.4');
        });

        it('an asset the store does not know calculates nothing, in unit-price mode; once the store has it the amount appears', async () => {
            mount({items: [txRow({asset_id: UNKNOWN_ASSET, cash: null})]});
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await fireEvent.click(unitPriceButton());
            await screen.findByTestId('tx-form-unit-price');
            await typeUnitPrice('83.4');
            expect(cashAmount(), 'no asset row, nothing to multiply with').toHaveValue('');
            expect(unitPriceInput(), 'the price stays as typed').toHaveValue('83.4');

            mergeAssets([{id: UNKNOWN_ASSET, display_name: 'Arrived late', currency: 'EUR', quote_base_quantity: 100, active: true}]);
            await waitFor(() => expect(cashAmount()).toHaveValue('10.008'));
        });

        it('no asset picked at all calculates nothing; picking one does', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeAmount('1000.8');
            expect(computedValue()).toBe('');

            await pickAsset(ASSET);
            await expectComputed('83.4');
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (g) the payload
    // -----------------------------------------------------------------------------------------------------------------
    describe('(g) the payload carries the amount, never a unit price', () => {
        async function applyAndRead(onPushDraft: ReturnType<typeof vi.fn>): Promise<Record<string, unknown>> {
            await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
            await fireEvent.click(screen.getByTestId('tx-form-save'));
            expect(onPushDraft, 'the form was applied').toHaveBeenCalledTimes(1);
            expect(commitTransactions).not.toHaveBeenCalled();
            return onPushDraft.mock.calls[0]?.[0] as Record<string, unknown>;
        }

        function expectNoUnitPrice(payload: Record<string, unknown>): void {
            expect(
                Object.keys(payload).filter((key) => /price/i.test(key)),
                'no key of the payload names a price',
            ).toEqual([]);
            expect(JSON.stringify(payload), 'the unit price (83.4) is nowhere in the payload').not.toContain('83.4');
        }

        it('amount mode: the quantity and the signed amount, no price', async () => {
            const {onPushDraft} = mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('12');
            await typeAmount('1000.8');
            await expectComputed('83.4');

            const payload = await applyAndRead(onPushDraft);

            expect(payload.asset_id).toBe(ASSET);
            expect(payload.quantity).toBe('12');
            expect(payload.cash).toEqual({code: 'EUR', amount: '-1000.8'});
            expectNoUnitPrice(payload);
        });

        it('unit-price mode: the amount the form calculated is the one sent, no price', async () => {
            const {onPushDraft} = mount();
            await reachUnitPriceDriver();

            const payload = await applyAndRead(onPushDraft);

            expect(payload.quantity).toBe('12');
            expect(payload.cash).toEqual({code: 'EUR', amount: '-1000.8'});
            expectNoUnitPrice(payload);
        });

        it('a bond: the amount sent is the one on base 100', async () => {
            const {onPushDraft} = mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(BOND);
            await typeQuantity('1000');
            await fireEvent.click(unitPriceButton());
            await screen.findByTestId('tx-form-unit-price');
            await typeUnitPrice('98.5');
            await waitFor(() => expect(cashAmount()).toHaveValue('985'));

            const payload = await applyAndRead(onPushDraft);

            expect(payload.cash).toEqual({code: 'EUR', amount: '-985'});
            expect(Object.keys(payload).filter((key) => /price/i.test(key))).toEqual([]);
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (h) switching the badge
    // -----------------------------------------------------------------------------------------------------------------
    describe('(h) switching the badge', () => {
        it('back to amount keeps the calculated amount on screen, drops the price input and shows the price again', async () => {
            mount();
            await reachUnitPriceDriver();

            await fireEvent.click(amountButton());

            expectPressed('amount');
            expect(cashAmount(), 'the amount stays on screen').toHaveValue('1000.8');
            await expectComputed('83.4');
            expect(screen.queryByTestId('tx-form-unit-price'), 'the price input goes away').toBeNull();
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

    // -----------------------------------------------------------------------------------------------------------------
    // (i) view mode: both forms of the same trade
    // -----------------------------------------------------------------------------------------------------------------
    describe('(i) view mode of a saved trade shows the total amount and the unit price', () => {
        it('a saved BUY: the amount in the cash cell and the price next to it, read-only, no badge', async () => {
            mount({mode: 'view', items: [txRow({type: 'BUY', quantity: '12', cash: {code: 'EUR', amount: '-1000.8'}})]});
            // The readonly form is on screen (its quantity is there, disabled) before anything is asserted about it.
            expect(await screen.findByTestId('tx-form-quantity')).toBeDisabled();

            expect(cashAmount(), 'the total amount, shown as the form shows a BUY').toHaveValue('1000.8');
            expect(cashAmount()).toBeDisabled();
            await expectComputed('83.4');
            expect(computedPrice(), 'the unit price is text, not a field').not.toBeInstanceOf(HTMLInputElement);
            expect(entryBadge(), 'a readonly form has no badge').toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price'), 'no input for the price').toBeNull();
        });

        it('a saved SELL: both forms too', async () => {
            mount({mode: 'view', items: [txRow({type: 'SELL', quantity: '-12', cash: {code: 'EUR', amount: '1000.8'}})]});
            expect(await screen.findByTestId('tx-form-quantity')).toBeDisabled();

            expect(cashAmount()).toHaveValue('1000.8');
            await expectComputed('83.4');
            expect(entryBadge()).toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price')).toBeNull();
        });

        it('a saved bond BUY is read on its base 100', async () => {
            mount({mode: 'view', items: [txRow({asset_id: BOND, type: 'BUY', quantity: '1000', cash: {code: 'EUR', amount: '-985'}})]});
            expect(await screen.findByTestId('tx-form-quantity')).toBeDisabled();

            expect(cashAmount()).toHaveValue('985');
            await expectComputed('98.5');
        });

        it('a saved trade whose asset the store does not know shows the amount and an empty price; the asset arriving fills it', async () => {
            mount({mode: 'view', items: [txRow({asset_id: UNKNOWN_ASSET, type: 'BUY', quantity: '12', cash: {code: 'EUR', amount: '-1000.8'}})]});
            expect(await screen.findByTestId('tx-form-quantity')).toBeDisabled();

            expect(cashAmount()).toHaveValue('1000.8');
            expect(computedValue()).toBe('');

            mergeAssets([{id: UNKNOWN_ASSET, display_name: 'Arrived late', currency: 'EUR', quote_base_quantity: 1, active: true}]);
            await expectComputed('83.4');
        });

        it('a DEPOSIT in view mode has neither a price nor a badge', async () => {
            mount({mode: 'view', items: [txRow({type: 'DEPOSIT', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '500'}})]});
            await screen.findByTestId('tx-form-cash-amount');

            expect(entryBadge()).toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price-computed')).toBeNull();
            expect(screen.queryByTestId('tx-form-unit-price')).toBeNull();
        });
    });
});
