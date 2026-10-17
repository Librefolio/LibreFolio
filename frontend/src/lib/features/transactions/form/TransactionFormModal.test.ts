// @vitest-environment jsdom
/**
 * TransactionFormModal — component test (Vitest + jsdom) for the beta-feedback
 * form-draft fixes, plus the FX dual-create regression that keeps the shared
 * broker and leg dates stable when Apply pushes a draft into BulkModal.
 *
 * Two behaviors, both decided the moment the draft is seeded:
 *
 *   T1-b — create mode starts with an EMPTY quantity (`emptyDraft().quantity`
 *     is `''`, not `'0'`): a pre-filled zero forced the user to cursor around
 *     it just to type decimals.
 *   T3 — clone preserves the source row's date. The duplicate *mode* of this
 *     modal was removed as dead code (nothing reachable set it): the real clone
 *     paths live in the bulk workspace (resolveInitialRows / createOpFromClone /
 *     cloneRow) and are covered by the tx-clone E2E.
 *
 * Duplicate mode is currently not reachable from any page action (rows clone
 * through the bulk workspace), which is exactly why this is a component test
 * and not an E2E: the mode is a prop here.
 *
 * Store modules are the real ones with only their network loaders stubbed
 * (importOriginal spread, same pattern as ImportWizardModal.test.ts): jsdom
 * has no server, and an unhandled rejection from a loader would fail the suite
 * for a reason that has nothing to do with the subject. Transaction types are
 * loaded from a real minimal TXTypesResponse that contains the actual FX
 * metadata, while BUY and the rest still resolve through FALLBACK_RULE.
 * That keeps the rest of the mock surface unchanged while still letting the
 * form render the FX path.
 *
 * Asserted: input values keyed by data-testid. Never a translated label.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {get, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {_ as translate} from '$lib/i18n';
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

function transferPair(quantity = '999999999999.123455') {
    const sender = txRow({
        id: 101,
        broker_id: 17,
        type: 'TRANSFER',
        quantity: `-${quantity}`,
        cash: null,
        related_transaction_id: 202,
        partner_broker_id: 23,
    });
    const receiver = txRow({
        id: 202,
        broker_id: 23,
        type: 'TRANSFER',
        quantity,
        cash: null,
        related_transaction_id: 101,
        partner_broker_id: 17,
    });
    return {sender, receiver};
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

async function setCashAmount(testid: string, amount: string) {
    const input = screen.getByTestId(`${testid}-amount`) as HTMLInputElement;
    await fireEvent.input(input, {target: {value: amount}});
    await fireEvent.blur(input);
}

function expectNoImportantNeutralQuantityBorder(input: HTMLElement) {
    expect(input.classList).not.toContain('!border-gray-200');
    expect(input.classList).not.toContain('dark:!border-slate-600');
}

async function validateAndFindOperation(operation: 'creates' | 'updates', predicate: (item: Record<string, unknown>) => boolean) {
    const callsBefore = vi.mocked(validateTransactions).mock.calls.length;
    await fireEvent.click(screen.getByTestId('tx-form-validate-now'));

    let matched: Record<string, unknown> | undefined;
    await waitFor(() => {
        matched = vi
            .mocked(validateTransactions)
            .mock.calls.slice(callsBefore)
            .flatMap(([payload]) => ((payload as unknown as Record<string, unknown>)[operation] as Array<Record<string, unknown>> | undefined) ?? [])
            .find(predicate);
        expect(matched).toBeDefined();
    });
    if (!matched) throw new Error(`manual validation did not publish a matching ${operation} item`);
    return matched;
}

function resetGuideState() {
    guideState.active = null;
    guideState.queuedGuides = [];
}

describe('TransactionFormModal — draft seeding (T1-b, T3)', () => {
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

    it('registers four distinct guide anchors for type, required fieldset, optional disclosure, and Save', async () => {
        mount({mode: 'create'});

        const basics = await screen.findByTestId('tx-form-type-wrap');
        const amounts = screen.getByTestId('tx-form-required');
        const details = screen.getByTestId('tx-form-optional-toggle');
        const save = screen.getByTestId('tx-form-save');

        await waitFor(() => {
            expect(guideAnchors.get('transaction.create.basics')).toBe(basics);
            expect(guideAnchors.get('transaction.create.amounts')).toBe(amounts);
            expect(guideAnchors.get('transaction.create.details')).toBe(details);
            expect(guideAnchors.get('transaction.create.save')).toBe(save);
        });

        expect(new Set([basics, amounts, details, save]).size).toBe(4);
        expect(basics).toHaveAttribute('data-testid', 'tx-form-type-wrap');
        expect(amounts.tagName).toBe('FIELDSET');
        expect(amounts).toContainElement(basics);
        expect(details.tagName).toBe('SUMMARY');
        expect(details.closest('details')).not.toBeNull();
        expect(save.tagName).toBe('BUTTON');
    });

    it('T1-b: create mode starts with an empty quantity field', async () => {
        mount({mode: 'create'});

        const qty = (await screen.findByTestId('tx-form-quantity')) as HTMLInputElement;
        expect(qty.value).toBe('');
    });

    it('FX create pushes a two-leg draft with the shared broker and preserved dates', async () => {
        const onPushDraft = vi.fn();
        const {onClose} = mount({commitOnSave: false, defaultBrokerId: 17, onPushDraft});

        await chooseFxType();
        await setTypedDate('tx-form-dual-from', '2024-03-10');
        await setTypedDate('tx-form-dual-to', '2024-03-11');
        await setCashAmount('tx-form-cash-from', '125.5');
        await setCashAmount('tx-form-cash-to', '140.25');

        await waitFor(() => {
            expect(screen.getByTestId('tx-form-validate-now')).toBeEnabled();
            expect(screen.getByTestId('tx-form-save')).toBeEnabled();
        });

        await fireEvent.click(screen.getByTestId('tx-form-save'));

        expect(onPushDraft).toHaveBeenCalledTimes(1);
        const payload = onPushDraft.mock.calls[0]?.[0] as Record<string, unknown>;
        expect(payload._dual).toBe(true);
        expect(payload._items).toHaveLength(2);
        expect(commitTransactions).not.toHaveBeenCalled();
        expect(onClose).toHaveBeenCalledTimes(1);

        const [fromItem, toItem] = payload._items as Array<Record<string, unknown>>;
        expect(fromItem.broker_id).toBe(17);
        expect(toItem.broker_id).toBe(17);
        expect(fromItem.date).toBe('2024-03-10');
        expect(toItem.date).toBe('2024-03-11');
        expect(fromItem.cash).toEqual({code: 'EUR', amount: '-125.5'});
        expect(toItem.cash).toEqual({code: 'USD', amount: '140.25'});
        expect(fromItem.quantity).toBe('0');
        expect(toItem.quantity).toBe('0');
    });

    it('FX keeps Validate Now enabled but blocks Save when the receiver leg is negative', async () => {
        mount({defaultBrokerId: 17});

        await chooseFxType();
        await setTypedDate('tx-form-dual-from', '2024-04-01');
        await setTypedDate('tx-form-dual-to', '2024-04-02');
        await setCashAmount('tx-form-cash-from', '50');
        await setCashAmount('tx-form-cash-to', '-10');

        await waitFor(() => {
            expect(screen.getByTestId('tx-form-validate-now')).toBeEnabled();
            expect(screen.getByTestId('tx-form-save')).toBeDisabled();
        });
    });
});

describe('TransactionFormModal — exact quantity contract', () => {
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

    function itemsFor(type: 'BUY' | 'SELL' | 'ADJUSTMENT' | 'TRANSFER') {
        if (type === 'TRANSFER') {
            const {sender, receiver} = transferPair();
            return [sender, receiver];
        }
        if (type === 'ADJUSTMENT') {
            return [
                txRow({
                    type,
                    quantity: '1',
                    cash: null,
                    cost_basis_mode: 'manual',
                }),
            ];
        }
        return [
            txRow({
                type,
                quantity: type === 'SELL' ? '-1' : '1',
                cash: {code: 'EUR', amount: type === 'SELL' ? '100' : '-100'},
            }),
        ];
    }

    it.each([
        ['TRANSFER', false],
        ['BUY', true],
        ['ADJUSTMENT', true],
    ] as const)('%s renders one exact text quantity and links only a real branch hint', async (type, hasQuantityHint) => {
        mount({
            mode: 'create',
            items: itemsFor(type),
            commitOnSave: false,
            onPushDraft: vi.fn(),
        });

        const input = (await screen.findByTestId('tx-form-quantity')) as HTMLInputElement;
        expect(screen.getAllByTestId('tx-form-quantity')).toHaveLength(1);
        expect(within(screen.getByTestId('tx-form-quantity-wrap')).getAllByRole('textbox')).toHaveLength(1);
        expect(input).toHaveAttribute('type', 'text');
        expect(input).toHaveAttribute('inputmode', 'decimal');
        // No maxlength pin here any more: C-97b removes the attribute (pinned in ExactDecimalInput.test.ts).
        expect(input).not.toHaveAttribute('aria-valuenow');
        expectNoImportantNeutralQuantityBorder(input);
        if (type === 'BUY') expect(screen.getByTestId('tx-form-cash-wrap')).toBeInTheDocument();
        else expect(screen.queryByTestId('tx-form-cash-wrap')).toBeNull();

        const idMatch = /^tx-form-quantity-([a-z0-9]{8})$/.exec(input.id);
        if (!idMatch) throw new Error(`${type} quantity input has invalid nonce id ${input.id}`);
        const nonce = idMatch[1];
        expect(input.name).toBe(`qty-${nonce}`);

        const expectedHintId = `tx-form-quantity-hint-${nonce}`;
        if (!hasQuantityHint) {
            expect(input).not.toHaveAttribute('aria-describedby');
            expect(document.getElementById(expectedHintId)).toBeNull();
            return;
        }

        const hintId = input.getAttribute('aria-describedby');
        expect(hintId).toBe(expectedHintId);
        if (!hintId) throw new Error(`${type} quantity input has no aria-describedby hint`);
        expect(document.querySelectorAll(`[id="${hintId}"]`)).toHaveLength(1);
    });

    it('pushes a pre-blur high SELL as one normalized exact negative string', async () => {
        const onPushDraft = vi.fn();
        mount({
            mode: 'create',
            items: itemsFor('SELL'),
            commitOnSave: false,
            onPushDraft,
        });
        const input = await screen.findByTestId('tx-form-quantity');

        await fireEvent.focus(input);
        await fireEvent.input(input, {target: {value: '999999999999,123456'}});
        expect(input).toHaveValue('999999999999,123456');
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());

        await fireEvent.click(screen.getByTestId('tx-form-save'));

        expect(input).toHaveValue('999999999999,123456');
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        expect(onPushDraft.mock.calls[0]?.[0]).toMatchObject({
            type: 'SELL',
            quantity: '-999999999999.123456',
        });
        expect(commitTransactions).not.toHaveBeenCalled();
    });

    it('preserves an explicit manual override through create validation and commitOnSave=false draft push without a public mode', async () => {
        const override = {code: 'EUR', amount: '123.450000'};
        const onPushDraft = vi.fn();
        mount({
            mode: 'create',
            items: [
                txRow({
                    type: 'ADJUSTMENT',
                    quantity: '1',
                    cash: null,
                    cost_basis_mode: 'manual',
                    cost_basis_override: null,
                }),
            ],
            commitOnSave: false,
            onPushDraft,
        });

        const amountInput = (await screen.findByTestId('tx-form-cost-basis-input-amount')) as HTMLInputElement;
        expect(screen.getByTestId('tx-form-cost-basis-toggle-manual')).toHaveAttribute('aria-pressed', 'true');
        await fireEvent.input(amountInput, {target: {value: override.amount}});
        expect(amountInput).toHaveValue(override.amount);
        await waitFor(() => {
            expect(screen.getByTestId('tx-form-validate-now')).toBeEnabled();
            expect(screen.getByTestId('tx-form-save')).toBeEnabled();
        });

        const validatedCreate = await validateAndFindOperation('creates', (item) => item.type === 'ADJUSTMENT' && (item.cost_basis_override as {amount?: string} | undefined)?.amount === override.amount);
        expect(validatedCreate.cost_basis_override).toEqual(override);
        expect(validatedCreate).not.toHaveProperty('cost_basis_mode');

        await fireEvent.click(screen.getByTestId('tx-form-save'));
        expect(onPushDraft).toHaveBeenCalledTimes(1);
        const pushed = onPushDraft.mock.calls.at(-1)?.[0] as Record<string, unknown> | undefined;
        if (!pushed) throw new Error('manual create did not publish its local draft');
        expect(pushed.cost_basis_override).toEqual(override);
        expect(pushed._cost_basis_mode).toBe('manual');
        expect(pushed).not.toHaveProperty('cost_basis_mode');
        expect(commitTransactions).not.toHaveBeenCalled();
    });

    it('preserves an edited manual override through update validation and commit without an implicit mode', async () => {
        const override = {code: 'EUR', amount: '222.500000'};
        mount({
            mode: 'edit',
            items: [
                txRow({
                    type: 'ADJUSTMENT',
                    quantity: '1',
                    cash: null,
                    cost_basis_mode: 'manual',
                    cost_basis_override: {code: 'EUR', amount: '10'},
                }),
            ],
        });

        const amountInput = (await screen.findByTestId('tx-form-cost-basis-input-amount')) as HTMLInputElement;
        expect(screen.getByTestId('tx-form-cost-basis-toggle-manual')).toHaveAttribute('aria-pressed', 'true');
        await fireEvent.input(amountInput, {target: {value: override.amount}});
        expect(amountInput).toHaveValue(override.amount);
        await waitFor(() => {
            expect(screen.getByTestId('tx-form-validate-now')).toBeEnabled();
            expect(screen.getByTestId('tx-form-save')).toBeEnabled();
        });

        const validatedUpdate = await validateAndFindOperation('updates', (item) => item.id === 101 && (item.cost_basis_override as {amount?: string} | undefined)?.amount === override.amount);
        expect(validatedUpdate).toEqual({
            id: 101,
            cost_basis_override: override,
        });
        expect(validatedUpdate).not.toHaveProperty('cost_basis_mode');

        const commitCallsBefore = vi.mocked(commitTransactions).mock.calls.length;
        await fireEvent.click(screen.getByTestId('tx-form-save'));
        await waitFor(() => expect(vi.mocked(commitTransactions).mock.calls.length).toBeGreaterThan(commitCallsBefore));
        expect(vi.mocked(commitTransactions).mock.calls.at(-1)?.[0]).toEqual({
            updates: [
                {
                    id: 101,
                    cost_basis_override: override,
                },
            ],
        });
    });

    it.each([
        ['edit', 'edit'],
        ['create-from-duplicate-draft', 'create'],
    ] as const)('%s hydrates a high SELL as a positive magnitude and pushes the exact negative payload', async (_label, mode) => {
        const onPushDraft = vi.fn();
        const source = txRow({
            type: 'SELL',
            date: '2017-08-09',
            quantity: '-999999999999.123456',
            cash: {code: 'EUR', amount: '100'},
        });
        mount({mode, items: [source], commitOnSave: false, onPushDraft});

        const input = await screen.findByTestId('tx-form-quantity');
        expect(input).toHaveValue('999999999999.123456');
        const dateInput = within(screen.getByTestId('tx-form-date-wrap')).getByRole('textbox');
        expect(dateInput).toHaveValue('2017-08-09');

        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));

        expect(onPushDraft).toHaveBeenCalledTimes(1);
        expect(onPushDraft.mock.calls[0]?.[0]).toMatchObject({
            type: 'SELL',
            date: '2017-08-09',
            quantity: '-999999999999.123456',
        });
    });

    it.each([
        {
            label: 'auto receiver-first',
            receiverFirst: true,
            mode: 'auto',
            initialOverride: {code: 'EUR', amount: '0'},
            nextOverride: null,
            expectedReceiverCostBasis: {
                cost_basis_mode: 'auto',
                cost_basis_override: {code: 'EUR', amount: '0'},
            },
        },
        {
            label: 'manual sender-first',
            receiverFirst: false,
            mode: 'manual',
            initialOverride: {code: 'EUR', amount: '10'},
            nextOverride: '222.5',
            expectedReceiverCostBasis: {
                cost_basis_override: {code: 'EUR', amount: '222.5'},
            },
        },
    ] as const)('$label maps exact sender/receiver update legs and preserves allowed cost basis', async ({receiverFirst, mode, initialOverride, nextOverride, expectedReceiverCostBasis}) => {
        const {sender, receiver} = transferPair('999999999999.123455');
        Object.assign(receiver, {
            cost_basis_mode: mode,
            cost_basis_override: initialOverride,
        });
        mount({
            mode: 'edit',
            items: receiverFirst ? [receiver, sender] : [sender, receiver],
        });
        const input = await screen.findByTestId('tx-form-quantity');
        expect(input).toHaveValue('999999999999.123455');

        if (nextOverride) {
            const amountInput = (await screen.findByTestId('tx-form-cost-basis-input-amount')) as HTMLInputElement;
            await fireEvent.input(amountInput, {target: {value: nextOverride}});
            expect(amountInput).toHaveValue(nextOverride);
        }
        await fireEvent.input(input, {target: {value: '999999999999,123456'}});
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));

        await waitFor(() => expect(commitTransactions).toHaveBeenCalledTimes(1));
        expect(vi.mocked(commitTransactions).mock.calls[0]?.[0]).toEqual({
            updates: [
                {id: 101, quantity: '-999999999999.123456'},
                {
                    id: 202,
                    quantity: '999999999999.123456',
                    ...expectedReceiverCostBasis,
                },
            ],
        });
    });

    it.each([
        ['1,250000', '1.250000'],
        ['0,000001', '0.000001'],
    ])('preserves exact locale input %j in the pushed payload as %j', async (raw, expected) => {
        const onPushDraft = vi.fn();
        mount({
            mode: 'create',
            items: itemsFor('BUY'),
            commitOnSave: false,
            onPushDraft,
        });
        const input = await screen.findByTestId('tx-form-quantity');

        await fireEvent.input(input, {target: {value: raw}});
        expect(input).toHaveValue(raw);
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('tx-form-save'));

        expect(onPushDraft.mock.calls[0]?.[0]).toMatchObject({
            type: 'BUY',
            quantity: expected,
        });
    });

    // C-97b guard: the overflow is 11 decimals, past the quantity's 10. It was 7 decimals while the form
    // allowed 6, a value C-97b makes valid; the limit itself must survive the cure. W-B64 guard, likewise:
    // the integer overflow is 16 digits, past the 15 W-B64 gives the Form (N63, the backend's limit). It was
    // 13 digits while the form allowed 12, a value W-B64 makes valid.
    it.each(['0.12345678912', '1000000000000000.1'])('keeps precision overflow %j visible, invalid, and out of payloads', async (raw) => {
        const onPushDraft = vi.fn();
        mount({
            mode: 'create',
            items: itemsFor('BUY'),
            commitOnSave: false,
            onPushDraft,
        });
        const input = await screen.findByTestId('tx-form-quantity');

        await fireEvent.input(input, {target: {value: raw}});
        expect(input).toHaveValue(raw);
        expect(input).toHaveAttribute('aria-invalid', 'true');
        expect(input.classList).toContain('aria-invalid:border-lf-danger');
        expect(input.classList, 'a base border-lf-danger would paint every state red').not.toContain('border-lf-danger');
        expectNoImportantNeutralQuantityBorder(input);
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeDisabled());

        await fireEvent.blur(input);
        expect(input).toHaveValue(raw);
        expect(onPushDraft).not.toHaveBeenCalled();
        expect(commitTransactions).not.toHaveBeenCalled();
    });

    it.each([
        ['BUY', '1', 'success', true],
        ['BUY', '-1', 'danger', false],
        ['BUY', '-0.000000', '', false],
        ['SELL', '1', 'success', true],
        ['SELL', '-1', 'danger', false],
        ['TRANSFER', '1', 'success', true],
        ['TRANSFER', '-1', 'danger', false],
        ['ADJUSTMENT', '1', 'success', true],
        ['ADJUSTMENT', '-1', 'success', true],
        ['ADJUSTMENT', '0', 'danger', false],
        ['ADJUSTMENT', '-0.000000', 'danger', false],
    ] as const)('%s quantity %j publishes matching hue and Save gate', async (type, raw, expectedHue, enabled) => {
        mount({
            mode: 'create',
            items: itemsFor(type),
            commitOnSave: false,
            onPushDraft: vi.fn(),
        });
        const input = await screen.findByTestId('tx-form-quantity');

        await fireEvent.input(input, {target: {value: raw}});

        expectNoImportantNeutralQuantityBorder(input);
        if (expectedHue) expect(input.getAttribute('style') ?? '').toContain(`border-color: color-mix(in oklab, var(--lf-${expectedHue}) 70%, transparent)`);
        else {
            expect(input.getAttribute('style') ?? '').not.toContain('border-color');
        }
        const signInvalid = expectedHue === 'danger';
        expect(input).toHaveAttribute('aria-invalid', String(signInvalid));
        if (signInvalid) {
            expect(input.classList).toContain('aria-invalid:border-lf-danger');
            expect(input.classList, 'a base border-lf-danger would paint every state red').not.toContain('border-lf-danger');
        } else {
            expect(input).toHaveAttribute('aria-invalid', 'false');
            expect(input.classList, 'at rest the border is not red').not.toContain('border-lf-danger');
        }
        await waitFor(() => {
            if (enabled) expect(screen.getByTestId('tx-form-save')).toBeEnabled();
            else expect(screen.getByTestId('tx-form-save')).toBeDisabled();
        });
    });

    it('view mode keeps the exact disabled input visible with no Save or mutation path', async () => {
        const onPushDraft = vi.fn();
        mount({
            mode: 'view',
            items: [
                txRow({
                    quantity: '999999999999.123456',
                }),
            ],
            commitOnSave: false,
            onPushDraft,
        });
        const input = await screen.findByTestId('tx-form-quantity');

        expect(input).toBeDisabled();
        expect(input).toHaveValue('999999999999.123456');
        expect(screen.queryByTestId('tx-form-save')).toBeNull();

        await fireEvent.input(input, {target: {value: '1'}});
        await fireEvent.keyDown(input, {key: 'ArrowDown'});
        expect(input).toHaveValue('999999999999.123456');
        expect(onPushDraft).not.toHaveBeenCalled();
        expect(commitTransactions).not.toHaveBeenCalled();
    });

    it('open and openKey resets reseed the private raw buffer from the same model', async () => {
        const source = txRow({quantity: '1.250000'});
        const {rerender} = mount({
            mode: 'create',
            items: [source],
            openKey: 0,
            commitOnSave: false,
            onPushDraft: vi.fn(),
        });
        let input = await screen.findByTestId('tx-form-quantity');

        await fireEvent.input(input, {target: {value: '1,250000'}});
        expect(input).toHaveValue('1,250000');

        await rerender({open: true, openKey: 1});
        input = await screen.findByTestId('tx-form-quantity');
        expect(input).toHaveValue('1.25');

        await fireEvent.input(input, {target: {value: '1,250000'}});
        await rerender({open: false});
        await waitFor(() => expect(screen.queryByTestId('tx-form-quantity')).toBeNull());
        await rerender({open: true});
        input = await screen.findByTestId('tx-form-quantity');
        expect(input).toHaveValue('1.25');
    });

    it.each([
        ['999999999999.123456', true],
        ['-999999999999.123456', false],
        ['-0.000000', false],
    ] as const)('cost-basis warning follows exact quantity sign for %j', async (quantity, warningVisible) => {
        mount({
            mode: 'create',
            items: [
                txRow({
                    type: 'ADJUSTMENT',
                    quantity,
                    cash: null,
                    cost_basis_mode: 'manual',
                    cost_basis_override: null,
                }),
            ],
            commitOnSave: false,
            onPushDraft: vi.fn(),
        });

        await screen.findByTestId('tx-form-quantity');
        await waitFor(() => {
            if (warningVisible) expect(screen.getByTestId('tx-form-cost-basis-warning')).toBeInTheDocument();
            else expect(screen.queryByTestId('tx-form-cost-basis-warning')).toBeNull();
        });
    });
});

/**
 * C-97b — the quantity keeps ten decimals. C-97a made a transaction keep a quantity up to 10 decimal
 * places (15 significant digits) and refuse more with the maximum, never rounding. The form lags:
 * TxFormSingleSection and TxFormPairSection give the quantity's ExactQuantityInput
 * `maxFractionDigits={6}`, so a quantity the backend keeps is refused here.
 *
 * Pinned through the field (`tx-form-quantity`): ten decimals are valid in the single form and in
 * the pair form, and reach the pushed draft whole; eleven are flagged, and the message under the
 * field (`tx-form-quantity-digits-error`, its text the cure's choice) carries `data-max="10"`. The
 * guard that eleven decimals stay out of every payload is «keeps precision overflow» above.
 */
describe('TransactionFormModal — a quantity keeps ten decimals (C-97b)', () => {
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

    const TEN_DECIMALS = '0.1234567891';
    const ELEVEN_DECIMALS = '0.12345678912';

    /** A complete standalone BUY: the single form. */
    function buyItems() {
        return [txRow({type: 'BUY', quantity: '1', cash: {code: 'EUR', amount: '-100'}})];
    }

    /** A TRANSFER pair: the pair form, its shared quantity in `tx-form-quantity`. */
    function transferItems() {
        const {sender, receiver} = transferPair();
        return [sender, receiver];
    }

    /** Within the budget: no message — absent, or rendered hidden. */
    function expectNoQuantityDigitsError() {
        const message = screen.queryByTestId('tx-form-quantity-digits-error');
        if (message) expect(message, 'tx-form-quantity-digits-error shows for a quantity within the budget').not.toBeVisible();
    }

    // Red today: the single form passes maxFractionDigits={6}, so ten decimals are aria-invalid and Save stays disabled.
    it('BUY (single form): ten decimals are a valid quantity, and reach the pushed draft whole', async () => {
        const onPushDraft = vi.fn();
        mount({mode: 'create', items: buyItems(), commitOnSave: false, onPushDraft});
        const input = (await screen.findByTestId('tx-form-quantity')) as HTMLInputElement;

        await fireEvent.input(input, {target: {value: TEN_DECIMALS}});

        expect(input).toHaveValue(TEN_DECIMALS);
        expect(input, 'ten decimals are within the quantity a transaction keeps (C-97a: 10)').toHaveAttribute('aria-invalid', 'false');
        expectNoQuantityDigitsError();
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());

        await fireEvent.click(screen.getByTestId('tx-form-save'));

        expect(onPushDraft).toHaveBeenCalledTimes(1);
        expect(onPushDraft.mock.calls[0]?.[0], 'the draft carries the ten decimals, none cut').toMatchObject({type: 'BUY', quantity: TEN_DECIMALS});
        expect(commitTransactions).not.toHaveBeenCalled();
    });

    // Red today: the pair form passes maxFractionDigits={6} as well.
    it('TRANSFER (pair form): ten decimals are a valid quantity', async () => {
        mount({mode: 'create', items: transferItems(), commitOnSave: false, onPushDraft: vi.fn()});
        const input = (await screen.findByTestId('tx-form-quantity')) as HTMLInputElement;
        expect(screen.getByTestId('tx-form-dual-split'), 'premise: the pair form').toBeInTheDocument();

        await fireEvent.input(input, {target: {value: TEN_DECIMALS}});

        expect(input).toHaveValue(TEN_DECIMALS);
        expect(input, 'ten decimals are within the quantity a transaction keeps (C-97a: 10)').toHaveAttribute('aria-invalid', 'false');
        expectNoQuantityDigitsError();
    });

    // Red today: eleven decimals are already flagged and block Save (that part is the guard: the limit
    // survives the cure), but no message says why.
    it.each([
        ['BUY (single form)', buyItems],
        ['TRANSFER (pair form)', transferItems],
    ] as const)('%s: eleven decimals are refused, and the message under the field names the budget of ten', async (_label, items) => {
        mount({mode: 'create', items: items(), commitOnSave: false, onPushDraft: vi.fn()});
        const input = (await screen.findByTestId('tx-form-quantity')) as HTMLInputElement;

        await fireEvent.input(input, {target: {value: ELEVEN_DECIMALS}});

        expect(input).toHaveValue(ELEVEN_DECIMALS);
        expect(input, 'eleven decimals are over the quantity budget').toHaveAttribute('aria-invalid', 'true');
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeDisabled());
        const message = screen.queryByTestId('tx-form-quantity-digits-error');
        expect(message, 'tx-form-quantity-digits-error must say why eleven decimals are refused; no such element is rendered').not.toBeNull();
        expect(message).toBeVisible();
        expect(message, 'the message carries the quantity budget: ten decimals').toHaveAttribute('data-max', '10');
    });
});

/**
 * W-B64 — a quantity keeps fifteen integer digits. The backend keeps a quantity of up to 15 digits before the decimal
 * point (decision N63, backend/app/db/precision.py); the Form gives the quantity's ExactQuantityInput
 * `maxIntegerDigits={12}` — twice in TxFormSingleSection, once in TxFormPairSection — so a quantity the backend keeps is
 * refused here, and Apply stays disabled.
 *
 * Pinned through the field (`tx-form-quantity`), in the three layouts that carry one: fifteen integer digits are a valid
 * quantity, Apply is enabled, and the pushed draft carries them whole — the single layout beside cash (BUY), the single
 * layout alone (ADJUSTMENT, its cash forbidden), the pair layout (TRANSFER: the sender's leg negative, the receiver's
 * positive). The guard that sixteen stay refused and out of every payload is «keeps precision overflow» above.
 */
describe('TransactionFormModal — a quantity keeps fifteen integer digits (W-B64)', () => {
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

    const FIFTEEN_DIGITS = '9'.repeat(15);

    /** A complete standalone BUY: the single layout, its quantity beside cash. */
    function buyItems() {
        return [txRow({type: 'BUY', quantity: '1', cash: {code: 'EUR', amount: '-100'}})];
    }

    /** A complete ADJUSTMENT, as «exact quantity contract» builds one: the single layout, its quantity alone. */
    function adjustmentItems() {
        return [txRow({type: 'ADJUSTMENT', quantity: '1', cash: null, cost_basis_mode: 'manual'})];
    }

    /** A TRANSFER pair, the sender (broker 17) first: the pair layout, its shared quantity in `tx-form-quantity`. */
    function transferItems() {
        const {sender, receiver} = transferPair();
        return [sender, receiver];
    }

    /** The form on `items`, its Apply pushing the draft instead of committing it. */
    async function mountForm(items: unknown[]) {
        const onPushDraft = vi.fn();
        mount({mode: 'create', items, commitOnSave: false, onPushDraft});
        const input = (await screen.findByTestId('tx-form-quantity')) as HTMLInputElement;
        return {input, onPushDraft};
    }

    /**
     * Types the fifteen digits, presses Apply, and returns the draft it pushed. Red before the W-B64 cure at its second
     * assertion: the field allows 12 integer digits, so it refuses the fifteen, and Apply stays disabled.
     */
    async function applyFifteenDigits(input: HTMLInputElement, onPushDraft: ReturnType<typeof vi.fn>): Promise<Record<string, unknown>> {
        await fireEvent.input(input, {target: {value: FIFTEEN_DIGITS}});

        expect(input, 'kept as typed').toHaveValue(FIFTEEN_DIGITS);
        expect(input, 'fifteen integer digits are within the quantity the backend keeps (N63: 15)').toHaveAttribute('aria-invalid', 'false');
        await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());

        await fireEvent.click(screen.getByTestId('tx-form-save'));

        expect(onPushDraft).toHaveBeenCalledTimes(1);
        expect(commitTransactions).not.toHaveBeenCalled();
        const pushed = onPushDraft.mock.calls[0]?.[0] as Record<string, unknown> | undefined;
        if (!pushed) throw new Error('Apply pushed no draft');
        return pushed;
    }

    it('BUY (single layout, quantity beside cash): fifteen integer digits are a valid quantity, and reach the pushed draft whole', async () => {
        const {input, onPushDraft} = await mountForm(buyItems());
        expect(screen.getByTestId('tx-form-cash-wrap'), 'premise: the single layout, cash beside the quantity').toBeInTheDocument();

        const pushed = await applyFifteenDigits(input, onPushDraft);

        expect(pushed, 'the draft carries the fifteen digits, none cut').toMatchObject({type: 'BUY', quantity: FIFTEEN_DIGITS});
    });

    it('ADJUSTMENT (single layout, quantity alone): fifteen integer digits are a valid quantity, and reach the pushed draft whole', async () => {
        const {input, onPushDraft} = await mountForm(adjustmentItems());
        expect(screen.queryByTestId('tx-form-dual-split'), 'premise: the single layout').toBeNull();
        expect(screen.queryByTestId('tx-form-cash-wrap'), 'premise: the quantity alone, its cash forbidden').toBeNull();

        const pushed = await applyFifteenDigits(input, onPushDraft);

        expect(pushed, 'the draft carries the fifteen digits, none cut').toMatchObject({type: 'ADJUSTMENT', quantity: FIFTEEN_DIGITS});
    });

    it('TRANSFER (pair layout): fifteen integer digits are a valid quantity, and reach both legs whole', async () => {
        const {input, onPushDraft} = await mountForm(transferItems());
        expect(screen.getByTestId('tx-form-dual-split'), 'premise: the pair layout').toBeInTheDocument();

        const pushed = await applyFifteenDigits(input, onPushDraft);

        expect(pushed._dual, 'premise: the pair pushes its two legs').toBe(true);
        const legs = ((pushed._items ?? []) as Array<Record<string, unknown>>).map(({broker_id, quantity}) => ({broker_id, quantity}));
        expect(legs, 'the sender gives the fifteen digits, the receiver gets them, none cut').toEqual([
            {broker_id: 17, quantity: `-${FIFTEEN_DIGITS}`},
            {broker_id: 23, quantity: FIFTEEN_DIGITS},
        ]);
    });
});

describe('TransactionFormModal — a quantity the form refuses is never validated (V-37)', () => {
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

    /**
     * The automatic validate waits out the scheduler's debounce (500 ms by default); this is past it
     * with room to spare, and far short of the 60 s idle run.
     */
    const PAST_THE_DEBOUNCE_MS = 5_000;

    /** What each `validateTransactions` call from call `from` on asked about: the quantity of every create, one array per call. */
    function validatedQuantitiesSince(from: number): unknown[][] {
        return vi
            .mocked(validateTransactions)
            .mock.calls.slice(from)
            .map(([payload]) => ((payload as unknown as {creates?: Array<{quantity?: unknown}>}).creates ?? []).map((create) => create.quantity));
    }

    it('BUY quantity -1: no automatic or manual validate, Validate now focuses the field, no valid; a corrected quantity validates once', async () => {
        // Only the timers decide whether a run goes out, and only the scheduler sets them: faking
        // setTimeout/clearTimeout from before the mount puts every debounce on a clock the test advances.
        vi.useFakeTimers({toFake: ['setTimeout', 'clearTimeout']});
        try {
            mount({mode: 'create', items: [txRow({quantity: '2'})], commitOnSave: false, onPushDraft: vi.fn()});
            const quantity = await screen.findByTestId('tx-form-quantity');
            const validateNow = screen.getByTestId('tx-form-validate-now');

            // Before: the complete BUY of 2 validates on its own and says so.
            await vi.advanceTimersByTimeAsync(PAST_THE_DEBOUNCE_MS);
            expect(validatedQuantitiesSince(0), 'premise: the complete BUY validates on its own').toContainEqual(['2']);
            expect(screen.getByTestId('tx-form-valid-inline')).toBeInTheDocument();

            const callsAtEdit = vi.mocked(validateTransactions).mock.calls.length;
            await fireEvent.input(quantity, {target: {value: '-1'}});
            await tick();
            expect(quantity, 'premise: the form refuses -1 on a BUY').toHaveAttribute('aria-invalid', 'true');
            expect(screen.getByTestId('tx-form-save')).toBeDisabled();
            expect(validateNow, 'Validate now is disabled only by an incomplete form').toBeEnabled();

            // The automatic run has had every chance to go out.
            await vi.advanceTimersByTimeAsync(PAST_THE_DEBOUNCE_MS);
            expect(validatedQuantitiesSince(callsAtEdit), 'the refused quantity must not be validated, not even sign-corrected to 1').toEqual([]);
            expect(screen.queryByTestId('tx-form-valid-inline')).toBeNull();

            // Validate now sends nothing and takes the user to the field. A real click leaves the
            // focus on the button; the handler is what may move it.
            validateNow.focus();
            expect(quantity).not.toHaveFocus();
            await fireEvent.click(validateNow);
            expect(quantity, 'Validate now leads to the refused quantity').toHaveFocus();
            expect(validatedQuantitiesSince(callsAtEdit), 'Validate now must not send the refused quantity').toEqual([]);
            await vi.advanceTimersByTimeAsync(PAST_THE_DEBOUNCE_MS);
            expect(validatedQuantitiesSince(callsAtEdit)).toEqual([]);
            expect(screen.queryByTestId('tx-form-valid-inline')).toBeNull();

            // Corrected: validated once, and valid again.
            await fireEvent.input(quantity, {target: {value: '3'}});
            await vi.advanceTimersByTimeAsync(PAST_THE_DEBOUNCE_MS);
            expect(validatedQuantitiesSince(callsAtEdit), 'the corrected quantity is validated, once').toEqual([['3']]);
            expect(screen.getByTestId('tx-form-valid-inline')).toBeInTheDocument();
        } finally {
            vi.useRealTimers();
        }
    });
});

describe('TransactionFormModal — a currency exchange says why its two dates may differ (C-89)', () => {
    // The paired layout gives each side its own date, «From» and «To»: a currency exchange and a transfer
    // share it (`pairLayout`). For an exchange the two dates read as a question to a user who is not an
    // expert — which one, and why two? The contract: in the exchange's layout only, a hint
    // (`tx-form-fx-dates-hint`) reads `transactions.form.fxDatesHint` — the two dates usually match, and
    // differ when the broker credits the new currency on another day. Its text is the message, nothing
    // else (an icon beside it has no text); the asset transfer, with the same two dates, has no hint.
    //
    // The expectation is the app's own formatter, in the locale the form is mounted in, never the English
    // copied here. A key the catalogue lacks comes back as the key itself, so the first assertion asks the
    // catalogue, and is soft: the hint's absence is reported too.
    //
    // Red today: the key is missing, and so is the hint. The transfer case is a control, green today.
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

    const HINT_KEY = 'transactions.form.fxDatesHint';
    const squash = (text: string | null | undefined): string => (text ?? '').replace(/\s+/g, ' ').trim();

    /** Presence barrier: the paired layout is on screen, each of its two sides with a date of its own. */
    function expectTwoDates() {
        for (const side of ['tx-form-dual-from', 'tx-form-dual-to']) {
            expect(within(screen.getByTestId(side)).getByTestId('single-date-picker-root'), `premise: ${side} has a date of its own`).toBeInTheDocument();
        }
    }

    it('FX_CONVERSION: a hint about the two dates reads transactions.form.fxDatesHint', async () => {
        mount({defaultBrokerId: 17});
        await chooseFxType();
        expectTwoDates();
        const message = get(translate)(HINT_KEY);
        const hint = screen.queryByTestId('tx-form-fx-dates-hint');

        expect.soft(message, `the catalogue has ${HINT_KEY}: the formatter answers a missing key with the key itself`).not.toBe(HINT_KEY);
        expect(hint, 'the exchange shows a hint about its two dates').not.toBeNull();
        expect(squash(hint?.textContent), 'the hint reads the message, and nothing else').toBe(message);
    });

    it('TRANSFER (control): the asset transfer has the same two dates, and no such hint', async () => {
        mount({defaultBrokerId: 17});
        await chooseDualType('TRANSFER');
        expectTwoDates();
        expect(screen.queryByTestId('tx-form-cash-from'), 'premise: the transfer layout, not the exchange one').toBeNull();

        expect(screen.queryByTestId('tx-form-fx-dates-hint')).toBeNull();
    });
});

describe('TransactionFormModal — create guide lifecycle', () => {
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

    it('does not let a guide queued behind another active flow survive closing the observed form', async () => {
        const otherGuide = {
            flow: 'transactions_page_guide',
            version: 1,
            stepId: 'transactions.page.overview',
            mode: 'automatic',
        } as const;
        guideState.active = otherGuide;
        const {onClose, rerender} = mount();

        await waitFor(() => {
            expect(guideMocks.maybeStartContextual).toHaveBeenCalledExactlyOnceWith('transaction_create_guide');
            expect(guideMocks.queueContextual).toHaveBeenCalledExactlyOnceWith('transaction_create_guide', undefined);
            expect(guideState.queuedGuides).toEqual([{flow: 'transaction_create_guide'}]);
        });

        await fireEvent.click(await screen.findByTestId('tx-form-close'));
        expect(onClose).toHaveBeenCalledTimes(1);
        expect(guideMocks.clearQueued).not.toHaveBeenCalled();

        await rerender({open: false});
        await waitFor(() => {
            expect(guideMocks.clearQueued).toHaveBeenCalledExactlyOnceWith('transaction_create_guide');
            expect(guideState.queuedGuides).toEqual([]);
        });
        expect(guideMocks.dismissHost).not.toHaveBeenCalled();
        expect(guideState.active).toEqual(otherGuide);

        guideState.active = null;
        expect(guideMocks.maybeStartQueued('transaction_create_guide')).toBe(false);
        expect(guideState.queuedGuides).toEqual([]);
        expect(guideState.active).toBeNull();
        expect(guideMocks.maybeStartContextual).toHaveBeenCalledTimes(1);
    });

    it('clears a guide queued behind another active flow when the observed form unmounts', async () => {
        const otherGuide = {
            flow: 'transactions_page_guide',
            version: 1,
            stepId: 'transactions.page.overview',
            mode: 'automatic',
        } as const;
        guideState.active = otherGuide;
        const {unmount} = mount();

        await waitFor(() => {
            expect(guideMocks.maybeStartContextual).toHaveBeenCalledExactlyOnceWith('transaction_create_guide');
            expect(guideState.queuedGuides).toEqual([{flow: 'transaction_create_guide'}]);
        });

        unmount();
        await tick();

        await waitFor(() => {
            expect(guideMocks.clearQueued).toHaveBeenCalledExactlyOnceWith('transaction_create_guide');
            expect(guideState.queuedGuides).toEqual([]);
        });
        expect(guideMocks.dismissHost).not.toHaveBeenCalled();
        expect(guideState.active).toEqual(otherGuide);
    });

    it('dismisses the active create guide and clears its queued entry when the observed form unmounts', async () => {
        guideState.queuedGuides = [{flow: 'transaction_create_guide'}];
        const {unmount} = mount();

        await waitFor(() => {
            expect(guideMocks.maybeStartContextual).toHaveBeenCalledExactlyOnceWith('transaction_create_guide');
            expect(guideState.active).toMatchObject({
                flow: 'transaction_create_guide',
                stepId: 'transaction.create.basics',
            });
        });

        unmount();
        await tick();

        await waitFor(() => {
            expect(guideMocks.dismissHost).toHaveBeenCalledExactlyOnceWith({restartAtFirst: true});
            expect(guideMocks.clearQueued).toHaveBeenCalledExactlyOnceWith('transaction_create_guide');
            expect(guideState.active).toBeNull();
            expect(guideState.queuedGuides).toEqual([]);
        });
        expect(guideMocks.dismissHost.mock.invocationCallOrder.at(0) ?? 0).toBeLessThan(guideMocks.clearQueued.mock.invocationCallOrder.at(0) ?? 0);
    });
});
