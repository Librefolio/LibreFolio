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
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {commitTransactions} from '$lib/utils/transactions/txCommitApi';
import {ensureTypesLoaded} from '$lib/stores/transactions/transactionTypeStore';
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
vi.mock('$lib/utils/transactions/txCommitApi', () => ({
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

function openTypeSelect() {
    return fireEvent.click(within(screen.getByTestId('tx-form-type')).getByRole('combobox'));
}

async function chooseFxType() {
    await openTypeSelect();
    await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
    const dropdown = screen.getByRole('listbox').parentElement as HTMLElement;
    await fireEvent.click(within(dropdown).getByTestId('search-select-option-FX_CONVERSION'));
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
