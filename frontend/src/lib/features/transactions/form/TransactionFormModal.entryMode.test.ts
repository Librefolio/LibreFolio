// @vitest-environment jsdom
/**
 * TransactionFormModal — «Total / Unit price» entry selector of the single BUY / SELL form (FB-16), component test
 * (Vitest + jsdom).
 *
 * The contract (developer decision of 28/10/2026; it replaces W5-9's badge + second input):
 *   - `tx-form-entry-mode` is a two-button selector, `…-amount` («Total») and `…-unit-price` («Unit price»), the state in
 *     `aria-pressed`. It sits INSIDE `tx-form-cash-wrap`, on the row of the amount's label, so before the amount input in
 *     the document, not under it. It exists only while the form can be edited and the type has a quantity AND an amount
 *     (BUY, SELL…): never in view mode, for a DEPOSIT / DIVIDEND (no quantity), an ADJUSTMENT (no cash) or a pair;
 *   - the form stays «amount + currency»: ONE input, `tx-form-cash-amount`. `tx-form-unit-price`,
 *     `tx-form-unit-price-computed` and `tx-form-trade-price` are gone. The selector only says how to READ the number in
 *     that input: as the total (Total) or as the price per `quote_base_quantity` units (Unit price);
 *   - switching the selector never rewrites the text of the input: the number stays, what it means changes;
 *   - «the other value» shows in `tx-form-cash-derived`, in place of the sign hint, when there is something to calculate:
 *     `data-mode="total"` (the number is read as a unit price → the total) or `data-mode="unit_price"` (read as a total →
 *     the price), `data-value` the canonical decimal. Nothing to calculate → no element, the sign hint is back. View mode
 *     shows `data-mode="unit_price"` and no selector;
 *   - what is saved is always the total (`cash.amount`): with Unit price active the one the form calculated; when it
 *     cannot be calculated the typed price is NEVER sent as the amount;
 *   - an opening (edit, view, every new one) starts on Total, with the saved total in the input.
 *
 * The calculation is the form's own (`txTradeAmount.ts`): synchronous, exact decimal arithmetic, no network, so nothing is
 * mocked for it: the asset comes from the real asset store seeded with `mergeAssets` (quote base 1 or 100, or none), and the
 * expectations are sums a person can check on paper. The arithmetic itself (ties, limits) is proved in `txTradeAmount.test.ts`.
 *
 * What this file leaves to the E2E (transactions-modals.spec.ts): the comma-decimal typing (`83,40`) on a real page and
 * that no `/transactions/commit` goes out. The four-language catalogue half of the contract (the hint texts, the two derived
 * keys) is `src/lib/i18n/transactionsEntryModeKeys.test.ts`.
 *
 * Absences are proved with a positive control, not with the clock: a value that must NOT be there is shown to be missing for
 * the reason named, then the reason is removed and it appears. The asset is picked through the real select; the broker comes
 * from `defaultBrokerId`.
 *
 * Asserted: data-testid / data-mode / data-value / aria-pressed, and the sign hint by the text its own catalogue key
 * resolves to (never a literal string: the harness runs in English today, the test would hold in any language).
 */

import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {get, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {_ as t} from '$lib/i18n';
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
        // A type with an asset and a cash amount but no quantity: no «Total / Unit price» selector, a unit price needs units.
        typeMetadata('DIVIDEND', {asset_mode: 'required', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'positive'}),
        // A type with an asset and a quantity but no cash: nothing to read as a total.
        typeMetadata('ADJUSTMENT', {asset_mode: 'required', cash_mode: 'forbidden', quantity_mode: 'required', quantity_sign: 'nonzero', cash_sign: 'zero'}),
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

/** A saved BUY of 12 units for 1000.8, as the list holds it (the cash of a BUY is negative). */
const savedBuy = (overrides: Record<string, unknown> = {}) => txRow({type: 'BUY', quantity: '12', cash: {code: 'EUR', amount: '-1000.8'}, ...overrides});

// ---------------------------------------------------------------------------------------------------------------------
// What this file observes and does
// ---------------------------------------------------------------------------------------------------------------------

const cashWrap = (): HTMLElement => screen.getByTestId('tx-form-cash-wrap');
const entrySelector = (): HTMLElement | null => screen.queryByTestId('tx-form-entry-mode');
const totalButton = (): HTMLElement => screen.getByTestId('tx-form-entry-mode-amount');
const unitPriceButton = (): HTMLElement => screen.getByTestId('tx-form-entry-mode-unit-price');
const cashAmount = (): HTMLInputElement => screen.getByTestId('tx-form-cash-amount') as HTMLInputElement;
const derived = (): HTMLElement | null => screen.queryByTestId('tx-form-cash-derived');

/** The testids that belong to the contract it replaces: none of them may exist, whatever the form shows. */
const DEAD_TESTIDS = ['tx-form-unit-price', 'tx-form-unit-price-computed', 'tx-form-trade-price'] as const;

function expectNoDeadTestids(): void {
    for (const id of DEAD_TESTIDS) expect(screen.queryByTestId(id), `${id} is not part of the form any more`).toBeNull();
}

function expectPressed(which: 'total' | 'unit-price'): void {
    expect(totalButton(), 'the Total button').toHaveAttribute('aria-pressed', which === 'total' ? 'true' : 'false');
    expect(unitPriceButton(), 'the Unit price button').toHaveAttribute('aria-pressed', which === 'unit-price' ? 'true' : 'false');
}

/** The other value, once the form has caught up with what was typed: its meaning (`data-mode`) and its exact decimal. */
async function expectDerived(mode: 'total' | 'unit_price', value: string): Promise<void> {
    await waitFor(() => {
        const element = derived();
        expect(element, `the derived value (${mode} ${value}) is on screen`).not.toBeNull();
        expect(element).toHaveAttribute('data-mode', mode);
        expect(element).toHaveAttribute('data-value', value);
    });
}

/** Nothing to calculate: the element is not there. Always paired with a positive control by the caller. */
async function expectNoDerived(): Promise<void> {
    await waitFor(() => expect(derived(), 'nothing to calculate: no derived value').toBeNull());
}

/** The sign hint of the cash field, found by the text its own catalogue key resolves to (never a literal string). */
function signHintShown(key: string): boolean {
    const text = get(t)(key);
    expect(text, `premise: ${key} resolves to a text`).not.toBe(key);
    return within(cashWrap()).queryAllByText(text).length > 0;
}

async function typeQuantity(value: string): Promise<void> {
    await fireEvent.input(screen.getByTestId('tx-form-quantity'), {target: {value}});
}

/** The number in the amount input, typed and left (the way the user does it): a total or a unit price, as the selector says. */
async function typeNumber(value: string): Promise<void> {
    const input = cashAmount();
    await fireEvent.input(input, {target: {value}});
    await fireEvent.blur(input);
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

async function chooseType(code: string): Promise<void> {
    await openTypeSelect();
    await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
    const dropdown = screen.getByRole('listbox').parentElement as HTMLElement;
    await fireEvent.click(within(dropdown).getByTestId(`search-select-option-${code}`));
    await waitFor(() => expect(screen.queryByRole('listbox')).toBeNull());
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

/** From a seeded BUY (asset 42): quantity 12 and 83.4 written, the selector on Unit price. The total (1000.8) is on screen. */
async function reachUnitPriceMode(assetId = ASSET): Promise<void> {
    await screen.findByTestId('tx-form-quantity');
    await pickAsset(assetId);
    await typeQuantity('12');
    await fireEvent.click(unitPriceButton());
    await typeNumber('83.4');
}

describe('TransactionFormModal — «Total / Unit price» selector (FB-16)', () => {
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
    // (a) who gets the selector, and where it sits
    // -----------------------------------------------------------------------------------------------------------------
    describe('(a) the selector', () => {
        it.each(['BUY', 'SELL'] as const)('a single %s has the selector inside the cash wrap, before the amount input, Total pressed by default', async (type) => {
            mount(seededSingle(type));
            await screen.findByTestId('tx-form-quantity');

            const selector = entrySelector();
            expect(selector, `the ${type} form has the selector`).not.toBeNull();
            expect(cashWrap(), 'the selector is part of the cash field').toContainElement(selector as HTMLElement);
            expect(within(selector as HTMLElement).getByTestId('tx-form-entry-mode-amount'), 'the two buttons live inside the selector').toBeInTheDocument();
            expect(within(selector as HTMLElement).getByTestId('tx-form-entry-mode-unit-price')).toBeInTheDocument();
            // On the row of the amount's label means above the input, not under it: the selector comes first in the document.
            expect((selector as HTMLElement).compareDocumentPosition(cashAmount()) & Node.DOCUMENT_POSITION_FOLLOWING, 'the selector precedes the amount input').toBeTruthy();
            expectPressed('total');
        });

        it('the form is amount + currency only: one input, and none of the replaced testids exists', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            // Presence barrier first: the selector is on screen, so the absences below are about this form and not about a blank page.
            expect(entrySelector()).not.toBeNull();

            expectNoDeadTestids();
            expect(within(cashWrap()).getAllByRole('textbox'), 'the cash wrap holds the amount input and nothing else to type in').toHaveLength(1);
            await fireEvent.click(unitPriceButton());
            expectPressed('unit-price');
            expectNoDeadTestids();
            expect(within(cashWrap()).getAllByRole('textbox'), 'Unit price adds no second input').toHaveLength(1);
        });

        it('a blank create form (BUY by default) has the selector too', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            expect(entrySelector()).not.toBeNull();
            expectPressed('total');
        });

        it('a DEPOSIT has no selector and nothing derived; back to BUY the selector returns', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            expect(entrySelector(), 'premise: the BUY form has the selector').not.toBeNull();

            await chooseType('DEPOSIT');
            // A DEPOSIT has no quantity: its going proves the form is the DEPOSIT one before the absence is asserted.
            await waitFor(() => expect(screen.queryByTestId('tx-form-quantity')).toBeNull());
            expect(screen.getByTestId('tx-form-cash-amount'), 'the DEPOSIT keeps its cash').toBeInTheDocument();

            expect(entrySelector(), 'a DEPOSIT has no selector').toBeNull();
            expect(derived()).toBeNull();
            expectNoDeadTestids();

            await chooseType('BUY');
            await waitFor(() => expect(entrySelector()).not.toBeNull());
        });

        it('a type with an amount but no quantity (DIVIDEND) has no selector: a unit price needs units', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            expect(entrySelector(), 'premise: BUY has it').not.toBeNull();

            await chooseType('DIVIDEND');
            await waitFor(() => expect(screen.queryByTestId('tx-form-quantity')).toBeNull());
            expect(screen.getByTestId('tx-form-cash-amount'), 'the DIVIDEND keeps its cash').toBeInTheDocument();
            expect(entrySelector()).toBeNull();
            expect(derived()).toBeNull();
        });

        it('a type with a quantity but no amount (ADJUSTMENT) has no selector: there is no total to read', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            expect(entrySelector(), 'premise: BUY has it').not.toBeNull();

            await chooseType('ADJUSTMENT');
            await waitFor(() => expect(screen.queryByTestId('tx-form-cash-amount')).toBeNull());
            expect(screen.getByTestId('tx-form-quantity'), 'the ADJUSTMENT keeps its quantity').toBeInTheDocument();
            expect(entrySelector()).toBeNull();
            expect(derived()).toBeNull();
        });

        it('an FX pair has no selector and nothing derived', async () => {
            mount();
            await chooseDualType('FX_CONVERSION');
            expect(entrySelector(), 'an FX pair has no selector').toBeNull();
            expect(derived()).toBeNull();
            expectNoDeadTestids();
        });

        it('a transfer pair has no selector and nothing derived', async () => {
            mount();
            await chooseDualType('TRANSFER');
            expect(entrySelector(), 'a transfer pair has no selector').toBeNull();
            expect(derived()).toBeNull();
            expectNoDeadTestids();
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (b) Total: the number is the total, the form shows the unit price
    // -----------------------------------------------------------------------------------------------------------------
    describe('(b) Total selected: the written number is the total, the derived value is the unit price', () => {
        it.each(['BUY', 'SELL'] as const)('a %s with quantity 12 and 1000.8 shows the unit price 83.4', async (type) => {
            mount(seededSingle(type));
            await screen.findByTestId('tx-form-quantity');
            expect(derived(), 'premise: nothing can be calculated yet').toBeNull();

            await typeQuantity('12');
            await typeNumber('1000.8');

            await expectDerived('unit_price', '83.4');
            expect(cashAmount(), 'the number stays as typed and editable').toHaveValue('1000.8');
            expect(cashAmount()).toBeEnabled();
            expectPressed('total');
        });

        it('the derived value says what it is in words that carry the exact figure', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeNumber('1000.8');
            await expectDerived('unit_price', '83.4');
            expect((derived() as HTMLElement).textContent?.trim(), 'the derived value is a sentence, not an empty node').not.toBe('');
        });

        it('the asset the user picked decides the base: 985 for 1000 units is 0.985 on base 1, 98.5 on base 100', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('1000');
            await typeNumber('985');

            await pickAsset(ASSET);
            await expectDerived('unit_price', '0.985');

            await pickAsset(BOND);
            await expectDerived('unit_price', '98.5');
            expect((derived() as HTMLElement).textContent, 'on base 100 the sentence names the base').toContain('100');
        });

        it('the unit price keeps up to 12 decimals: 1000.9 over 12 units', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeNumber('1000.9');
            await expectDerived('unit_price', '83.408333333333');
        });

        it('a tie rounds half-even, end to end: 1 over 8192 units ends on …312|5, so it stays on 2; 3 ends on …937|5, the odd 7 goes up', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('8192');
            await typeNumber('1');
            await expectDerived('unit_price', '0.000122070312');

            await typeNumber('3');
            await expectDerived('unit_price', '0.000366210938');
        });

        it('an integer price carries no decimal point, and nothing trails', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('10');
            await typeNumber('1000');
            await expectDerived('unit_price', '100');
        });

        it('an asset whose store row has no quote base counts as base 1', async () => {
            mount({items: [txRow({asset_id: NO_BASE})]});
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeNumber('1000.8');
            await expectDerived('unit_price', '83.4');
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (c) Unit price: the same input, read as a price per unit
    // -----------------------------------------------------------------------------------------------------------------
    describe('(c) Unit price selected: the written number is the price, the derived value is the total', () => {
        it('83.4 for 12 units reads as 1000.8 in total; the selector stays on Unit price and the input keeps the price', async () => {
            mount();
            await reachUnitPriceMode();

            await expectDerived('total', '1000.8');
            expectPressed('unit-price');
            expect(cashAmount(), 'the number is the price the user wrote').toHaveValue('83.4');
            expect(cashAmount()).toBeEnabled();
            expectNoDeadTestids();
        });

        it('switching the selector keeps the text of the input: 83.4 for 12 units is 83.4 in total, then 83.4 each; and back', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeNumber('83.4');
            await expectDerived('unit_price', '6.95'); // read as a total: 83.4 / 12
            const written = cashAmount().value;

            await fireEvent.click(unitPriceButton());
            expectPressed('unit-price');
            await expectDerived('total', '1000.8'); // read as a unit price: 12 × 83.4
            expect(cashAmount(), 'the text did not change, only how it is read').toHaveValue(written);

            await fireEvent.click(totalButton());
            expectPressed('total');
            await expectDerived('unit_price', '6.95');
            expect(cashAmount()).toHaveValue(written);
        });

        it('a bond (base 100): 1000 units at 98.5 are 985, not 98500', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(BOND);
            await typeQuantity('1000');
            await fireEvent.click(unitPriceButton());

            await typeNumber('98.5');
            await expectDerived('total', '985');
        });

        it('the total is rounded half-even to its 6 decimals: 0.0000025 for one unit is 0.000002, 0.0000035 is 0.000004', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('1');
            await fireEvent.click(unitPriceButton());

            await typeNumber('0.0000025');
            await expectDerived('total', '0.000002');
            await typeNumber('0.0000035');
            await expectDerived('total', '0.000004');
        });

        it('a zero or negative price calculates nothing; the next price that makes it calculable shows the total', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('12');
            await fireEvent.click(unitPriceButton());

            await typeNumber('0');
            await expectNoDerived();
            await typeNumber('-5');
            await expectNoDerived();
            await typeNumber('83.4');
            await expectDerived('total', '1000.8');
        });

        it('a saved BUY of 12 units for 1000.8 reopened on Unit price reads its 1000.8 as a price: 12009.6 in total', async () => {
            mount({mode: 'edit', items: [savedBuy()]});
            await screen.findByTestId('tx-form-quantity');
            expect(cashAmount(), 'premise: the input starts on the saved total').toHaveValue('1000.8');

            await fireEvent.click(unitPriceButton());

            await expectDerived('total', '12009.6');
            expect(cashAmount(), 'the text is the same one').toHaveValue('1000.8');
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (d) a quantity or asset edit recalculates the other value, whichever way the number is read
    // -----------------------------------------------------------------------------------------------------------------
    describe('(d) a new quantity or asset recalculates the derived value and keeps the written number', () => {
        it('Unit price: quantity 12 → 10 gives 834 in total; the price in the input is untouched', async () => {
            mount();
            await reachUnitPriceMode();
            await expectDerived('total', '1000.8');

            await typeQuantity('10');

            await expectDerived('total', '834');
            expectPressed('unit-price');
            expect(cashAmount()).toHaveValue('83.4');
        });

        it('Total: quantity 12 → 10 gives a unit price of 100.08; the total in the input is untouched', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeNumber('1000.8');
            await expectDerived('unit_price', '83.4');

            await typeQuantity('10');

            await expectDerived('unit_price', '100.08');
            expect(cashAmount()).toHaveValue('1000.8');
            expectPressed('total');
        });

        it('Unit price: picking the bond reads the same 83.4 on base 100 (12 / 100 × 83.4 = 10.008); back to base 1 it is 1000.8', async () => {
            mount();
            await reachUnitPriceMode(ASSET);
            await expectDerived('total', '1000.8');

            await pickAsset(BOND);

            await expectDerived('total', '10.008');
            expectPressed('unit-price');
            expect(cashAmount()).toHaveValue('83.4');

            await pickAsset(ASSET);
            await expectDerived('total', '1000.8');
        });

        it('Total: picking the bond reads the same 1000.8 on base 100: the unit price is 8340', async () => {
            mount({items: [txRow()]});
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeNumber('1000.8');
            await expectDerived('unit_price', '83.4');

            await pickAsset(BOND);

            await expectDerived('unit_price', '8340'); // 1000.8 × 100 / 12
            expect(cashAmount()).toHaveValue('1000.8');
            expectPressed('total');
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (e) nothing to calculate: no derived value, the sign hint is back
    // -----------------------------------------------------------------------------------------------------------------
    describe('(e) nothing to calculate', () => {
        it('the sign hint of the cash field is shown while there is nothing to calculate, gives way to the derived value, and returns', async () => {
            mount(seededSingle('BUY')); // a BUY: the cash rule is negative, so the rule has a hint
            await screen.findByTestId('tx-form-quantity');
            expect(derived(), 'premise: nothing to calculate').toBeNull();
            expect(signHintShown('transactions.form.hintSignNegative'), 'the hint of the rule shows').toBe(true);

            await typeQuantity('12');
            await typeNumber('1000.8');
            await expectDerived('unit_price', '83.4');
            expect(signHintShown('transactions.form.hintSignNegative'), 'the derived value is shown in its place').toBe(false);

            await typeNumber('');
            await expectNoDerived();
            await waitFor(() => expect(signHintShown('transactions.form.hintSignNegative'), 'the hint is back').toBe(true));
        });

        it('a blank or zero quantity calculates nothing; the quantity that makes it complete does', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');

            await typeNumber('1000.8'); // quantity still blank
            expect(derived(), 'blank quantity').toBeNull();
            await typeQuantity('0');
            expect(derived(), 'zero quantity').toBeNull();

            await typeQuantity('12');
            await expectDerived('unit_price', '83.4');
        });

        it('Unit price with a blank quantity calculates nothing either; the quantity brings the total', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await fireEvent.click(unitPriceButton());
            await typeNumber('83.4');
            expect(derived(), 'blank quantity').toBeNull();

            await typeQuantity('12');
            await expectDerived('total', '1000.8');
        });

        it('a zero, negative or blank total calculates nothing and takes away the old unit price; a positive one calculates', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeNumber('1000.8');
            await expectDerived('unit_price', '83.4');

            await typeNumber('0');
            await expectNoDerived();
            await typeNumber('1000.8');
            await expectDerived('unit_price', '83.4');

            await typeNumber('-5');
            await expectNoDerived();
            await typeNumber('1000.8');
            await expectDerived('unit_price', '83.4');

            await typeNumber('');
            await expectNoDerived();
        });

        it('a total past six decimals calculates nothing: it is outside the limits; one decimal less does', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');

            await typeNumber('1000.1234567');
            expect(derived()).toBeNull();
            await typeNumber('1000.8');
            await expectDerived('unit_price', '83.4');
        });

        it('15 significant digits are the limit: a total of fifteen 9s over 3 units calculates, sixteen 9s do not (and the field says why)', async () => {
            mount(seededSingle('BUY'));
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('3');

            await typeNumber('999999999999999');
            await expectDerived('unit_price', '333333333333333');

            await typeNumber('9999999999999999');
            await expectNoDerived();
            expect(screen.getByTestId('tx-form-cash-significant-error'), 'the amount field is red on its own').toBeInTheDocument();

            await typeNumber('999999999999999');
            await expectDerived('unit_price', '333333333333333');
        });

        /** A BUY of 1 unit of the base-1 asset, the selector on Unit price: the written number is the price, the total is the same figure. */
        async function reachUnitPriceOfOneUnit(): Promise<void> {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('1');
            await fireEvent.click(unitPriceButton());
        }

        it('Unit price at the 15 significant digits limit calculates; the 16th digit does not', async () => {
            await reachUnitPriceOfOneUnit();

            await typeNumber('1234567890.12345'); // 15 significant digits
            await expectDerived('total', '1234567890.12345');

            await typeNumber('1234567890.123456'); // 16
            await expectNoDerived();

            await typeNumber('83.4');
            await expectDerived('total', '83.4');
        });

        it('Unit price keeps its 12 decimals, as the calculation reads them: 1 000 000 units at 0.000000123456 are 0.123456, the input keeps the price', async () => {
            // On 8 decimals (what a plain amount display keeps) the same price would read 0.00000012 and the total 0.12.
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('1000000');
            await fireEvent.click(unitPriceButton());

            await typeNumber('0.000000123456');

            await expectDerived('total', '0.123456');
            expect(cashAmount(), 'the 12 decimals are still in the input after it was left').toHaveValue('0.000000123456');
        });

        it('Unit price past 12 decimals calculates nothing: it is outside the limits; the 12th decimal does', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('1000000');
            await fireEvent.click(unitPriceButton());

            await typeNumber('0.0000001234567'); // 13 decimals
            await expectNoDerived();

            await typeNumber('0.000000123456');
            await expectDerived('total', '0.123456');
        });

        it('an asset the store does not know calculates nothing in Total; once the store has it the unit price appears', async () => {
            mount({items: [txRow({asset_id: UNKNOWN_ASSET})]});
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeNumber('1000.8');
            expect(derived(), 'no asset row, no quote base, no unit price').toBeNull();

            // Positive control: the same form, the asset arrives (the store loads late) → the value follows.
            mergeAssets([{id: UNKNOWN_ASSET, display_name: 'Arrived late', currency: 'EUR', quote_base_quantity: 1, active: true}]);
            await expectDerived('unit_price', '83.4');
        });

        it('an asset the store does not know calculates nothing in Unit price; once the store has it (base 100) the total appears', async () => {
            mount({items: [txRow({asset_id: UNKNOWN_ASSET, cash: null})]});
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await fireEvent.click(unitPriceButton());
            await typeNumber('83.4');
            expect(derived(), 'no asset row, nothing to multiply with').toBeNull();
            expect(cashAmount(), 'the price stays as typed').toHaveValue('83.4');

            mergeAssets([{id: UNKNOWN_ASSET, display_name: 'Arrived late', currency: 'EUR', quote_base_quantity: 100, active: true}]);
            await expectDerived('total', '10.008');
        });

        it('no asset picked at all calculates nothing; picking one does', async () => {
            mount();
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await typeNumber('1000.8');
            expect(derived()).toBeNull();

            await pickAsset(ASSET);
            await expectDerived('unit_price', '83.4');
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (f) the payload: the total, always
    // -----------------------------------------------------------------------------------------------------------------
    describe('(f) what is saved is always the total', () => {
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

        it('Total: the quantity and the signed total, no price', async () => {
            const {onPushDraft} = mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(ASSET);
            await typeQuantity('12');
            await typeNumber('1000.8');
            await expectDerived('unit_price', '83.4');

            const payload = await applyAndRead(onPushDraft);

            expect(payload.asset_id).toBe(ASSET);
            expect(payload.quantity).toBe('12');
            expect(payload.cash).toEqual({code: 'EUR', amount: '-1000.8'});
            expectNoUnitPrice(payload);
        });

        it('Unit price: the total the form calculated (12 × 83.4) is the amount sent, not the price', async () => {
            const {onPushDraft} = mount();
            await reachUnitPriceMode();
            await expectDerived('total', '1000.8');

            const payload = await applyAndRead(onPushDraft);

            expect(payload.quantity).toBe('12');
            expect(payload.cash).toEqual({code: 'EUR', amount: '-1000.8'});
            expectNoUnitPrice(payload);
        });

        it('a SELL on Unit price sends its total with the SELL sign rule applied as today (positive cash)', async () => {
            const {onPushDraft} = mount({items: [txRow({type: 'SELL'})]});
            await reachUnitPriceMode();
            await expectDerived('total', '1000.8');

            const payload = await applyAndRead(onPushDraft);

            expect(payload.quantity).toBe('-12');
            expect(payload.cash).toEqual({code: 'EUR', amount: '1000.8'});
            expectNoUnitPrice(payload);
        });

        it('a bond on Unit price: the amount sent is the one on base 100', async () => {
            const {onPushDraft} = mount();
            await screen.findByTestId('tx-form-quantity');
            await pickAsset(BOND);
            await typeQuantity('1000');
            await fireEvent.click(unitPriceButton());
            await typeNumber('98.5');
            await expectDerived('total', '985');

            const payload = await applyAndRead(onPushDraft);

            expect(payload.cash).toEqual({code: 'EUR', amount: '-985'});
            expect(JSON.stringify(payload), 'the unit price (98.5) is nowhere in the payload').not.toContain('98.5');
        });

        it('a quantity edited after the price follows into the amount sent', async () => {
            const {onPushDraft} = mount();
            await reachUnitPriceMode();
            await expectDerived('total', '1000.8');
            await typeQuantity('10');
            await expectDerived('total', '834');

            const payload = await applyAndRead(onPushDraft);

            expect(payload.quantity).toBe('10');
            expect(payload.cash).toEqual({code: 'EUR', amount: '-834'});
        });

        it('Unit price with nothing to calculate keeps Apply closed: the price is not taken for the amount', async () => {
            // Quantity and asset are there; the asset is not in the store, so the total cannot be calculated. If the written
            // 83.4 were taken for the amount the form would be complete and Apply open.
            mount({items: [txRow({asset_id: UNKNOWN_ASSET, cash: null})]});
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await fireEvent.click(unitPriceButton());
            await typeNumber('83.4');
            expect(derived(), 'premise: nothing can be calculated').toBeNull();

            expect(screen.getByTestId('tx-form-save'), 'no total, no Apply').toBeDisabled();

            // Positive control: the asset arrives, the total exists, Apply opens.
            mergeAssets([{id: UNKNOWN_ASSET, display_name: 'Arrived late', currency: 'EUR', quote_base_quantity: 1, active: true}]);
            await expectDerived('total', '1000.8');
            await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        });

        it('Unit price with nothing to calculate sends no amount, never the price', async () => {
            // Saving straight to the server (`commitOnSave`) leaves the button open on an incomplete form: what is sent is what is read.
            mount({commitOnSave: true, items: [txRow({asset_id: UNKNOWN_ASSET, cash: null})]});
            await screen.findByTestId('tx-form-quantity');
            await typeQuantity('12');
            await fireEvent.click(unitPriceButton());
            await typeNumber('83.4');
            expect(derived(), 'premise: nothing can be calculated').toBeNull();

            await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
            await fireEvent.click(screen.getByTestId('tx-form-save'));
            await waitFor(() => expect(commitTransactions).toHaveBeenCalledTimes(1));

            const sent = vi.mocked(commitTransactions).mock.calls[0]?.[0] as {creates: Array<Record<string, unknown>>};
            const cash = sent.creates[0]?.cash as {amount?: string} | null | undefined;
            // «No amount» is absent, or the blank-amount fallback the payload has always had for a signed field (`applySign`: '0').
            expect(['', '0'], 'an amount not written, as the form has always sent it').toContain(cash?.amount ?? '');
            expect(JSON.stringify(sent), 'the unit price (83.4) is nowhere in what was sent').not.toContain('83.4');
        });

        it('an edit read as a unit price sends the new total in the update', async () => {
            // A saved BUY of 12 units for 1000.8; the selector goes to Unit price, so the 1000.8 in the input now reads 12009.6.
            mount({mode: 'edit', commitOnSave: true, items: [savedBuy()]});
            await screen.findByTestId('tx-form-quantity');
            await fireEvent.click(unitPriceButton());
            await expectDerived('total', '12009.6');

            await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
            await fireEvent.click(screen.getByTestId('tx-form-save'));
            await waitFor(() => expect(commitTransactions).toHaveBeenCalledTimes(1));

            const sent = vi.mocked(commitTransactions).mock.calls[0]?.[0] as {updates: Array<{cash?: {amount?: string}}>};
            expect(sent.updates[0]?.cash?.amount, 'the update carries the total, signed as a BUY').toBe('-12009.6');
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (g) opening: always on Total, with the saved total
    // -----------------------------------------------------------------------------------------------------------------
    describe('(g) every opening starts on Total with the saved total in the input', () => {
        it('a saved BUY opened for editing: Total pressed, the saved total in the input, its unit price derived', async () => {
            mount({mode: 'edit', items: [savedBuy()]});
            await screen.findByTestId('tx-form-quantity');

            expect(entrySelector()).not.toBeNull();
            expectPressed('total');
            expect(cashAmount(), 'a BUY shows its total unsigned').toHaveValue('1000.8');
            await expectDerived('unit_price', '83.4');
            expectNoDeadTestids();
        });

        it('opened again after Unit price was selected: Total pressed, the saved total back in the input', async () => {
            const {rerender} = mount({mode: 'edit', items: [savedBuy()], openKey: 0});
            await screen.findByTestId('tx-form-quantity');
            await fireEvent.click(unitPriceButton());
            expectPressed('unit-price');
            await expectDerived('total', '12009.6');

            await rerender({openKey: 1});

            await waitFor(() => expectPressed('total'));
            await waitFor(() => expect(cashAmount()).toHaveValue('1000.8'));
            await expectDerived('unit_price', '83.4');
        });

        it('a blank create form opened again starts on Total too', async () => {
            const {rerender} = mount({openKey: 0});
            await screen.findByTestId('tx-form-quantity');
            await fireEvent.click(unitPriceButton());
            expectPressed('unit-price');

            await rerender({openKey: 1});

            await waitFor(() => expectPressed('total'));
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (h) view mode: the trade reads in both forms, nothing to switch
    // -----------------------------------------------------------------------------------------------------------------
    describe('(h) view mode of a saved trade shows the total in the input and the unit price derived', () => {
        it('a saved BUY: the total in the input, the unit price derived, no selector', async () => {
            mount({mode: 'view', items: [savedBuy()]});
            // The readonly form is on screen (its quantity is there, disabled) before anything is asserted about it.
            expect(await screen.findByTestId('tx-form-quantity')).toBeDisabled();

            expect(cashAmount(), 'the total amount, shown as the form shows a BUY').toHaveValue('1000.8');
            expect(cashAmount()).toBeDisabled();
            await expectDerived('unit_price', '83.4');
            expect(entrySelector(), 'a readonly form has no selector').toBeNull();
            expectNoDeadTestids();
        });

        it('a saved SELL: both forms too', async () => {
            mount({mode: 'view', items: [txRow({type: 'SELL', quantity: '-12', cash: {code: 'EUR', amount: '1000.8'}})]});
            expect(await screen.findByTestId('tx-form-quantity')).toBeDisabled();

            expect(cashAmount()).toHaveValue('1000.8');
            await expectDerived('unit_price', '83.4');
            expect(entrySelector()).toBeNull();
        });

        it('a saved bond BUY is read on its base 100', async () => {
            mount({mode: 'view', items: [txRow({asset_id: BOND, type: 'BUY', quantity: '1000', cash: {code: 'EUR', amount: '-985'}})]});
            expect(await screen.findByTestId('tx-form-quantity')).toBeDisabled();

            expect(cashAmount()).toHaveValue('985');
            await expectDerived('unit_price', '98.5');
        });

        it('a saved trade whose asset the store does not know shows the total and no derived value; the asset arriving shows it', async () => {
            mount({mode: 'view', items: [savedBuy({asset_id: UNKNOWN_ASSET})]});
            expect(await screen.findByTestId('tx-form-quantity')).toBeDisabled();

            expect(cashAmount()).toHaveValue('1000.8');
            expect(derived()).toBeNull();

            mergeAssets([{id: UNKNOWN_ASSET, display_name: 'Arrived late', currency: 'EUR', quote_base_quantity: 1, active: true}]);
            await expectDerived('unit_price', '83.4');
        });

        it('a DEPOSIT in view mode has neither a derived value nor a selector', async () => {
            mount({mode: 'view', items: [txRow({type: 'DEPOSIT', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '500'}})]});
            await screen.findByTestId('tx-form-cash-amount');

            expect(entrySelector()).toBeNull();
            expect(derived()).toBeNull();
            expectNoDeadTestids();
        });
    });
});
