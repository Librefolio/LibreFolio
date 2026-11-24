// @vitest-environment jsdom
/**
 * TransactionFormModal — a REWARD in the form (project 79, STK-2a).
 *
 * A REWARD brings units in (quantity > 0, no cash) and its cost basis is its value on receipt, which is also its income:
 * the type table gives it `cost_basis_mode: 'required_qty_pos'` and `cost_basis_auto: false`. The contract pinned here:
 *
 *   - the inline cost-basis field (`tx-form-cost-basis-inline`) shows for a REWARD with a positive quantity, like an
 *     ADJUSTMENT, but without the Auto/Manual toggle (`tx-form-cost-basis-toggle`): the mode is always Manual, even for a
 *     row handed in with `cost_basis_mode: 'auto'` or none;
 *   - an empty value shows the warning (`tx-form-cost-basis-warning`);
 *   - an empty value is filled from the asset's stored close of that very day, per unit, as the backend's one reader
 *     answers it (STK-4b: one `query_reward_values…` call with `[{asset_id, date}]`; the form neither waits for the
 *     asset's quote base nor divides — the backend does) and the note `tx-form-reward-value-from-history` shows while
 *     the value is that suggestion; an answer without a value (no close that day, no history) fills nothing;
 *   - a value the user typed, before or after the answer, is never overwritten; a REWARD that holds a value, or a form
 *     in view mode, asks nothing.
 *
 * Harness: the one of TransactionFormModal.test.ts (stores with their loaders stubbed, `$lib/api` a proxy of vi.fn),
 * with a types answer holding BUY, ADJUSTMENT and REWARD. The reward-value query is reset before every test:
 * `clearAllMocks` keeps implementations, and an answer left by one test would fill the next one's field.
 *
 * Asserted: data-testid and payloads. Never a translated label.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {ensureTypesLoaded} from '$lib/features/transactions/transactionTypeStore';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
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
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({
    fxRoutesVersion: writable(0),
    ensureFxRoutesLoaded: vi.fn(async () => undefined),
    getConfiguredCurrencySet: vi.fn(() => new Set(['EUR', 'USD'])),
}));
vi.mock('$lib/features/transactions/txCommitApi', () => ({
    commitTransactions: vi.fn(async () => ({committed: true, results: [], issues: []})),
    validateTransactions: vi.fn(async () => ({committed: true, issues: [], rawResponse: {wac_results: []}})),
}));
// The guide is not the subject: a neutral stub keeps the real controller out (as TransactionFormModal.parent.test.ts).
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
//  Types: BUY and ADJUSTMENT as in TransactionFormModal.test.ts, REWARD as TX_TYPE_METADATA declares it
// ---------------------------------------------------------------------------------------------------------------

const TYPES_WITH_REWARD = schemas.TXTypesResponse.parse({
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
            cost_basis_auto: true,
        },
        {
            code: 'REWARD',
            name: 'Reward',
            description: 'Reward received in units of an asset',
            icon_slug: 'reward',
            doc_slug: 'reward',
            asset_mode: 'required',
            cash_mode: 'forbidden',
            quantity_mode: 'required',
            requires_link: false,
            quantity_sign: 'positive',
            cash_sign: 'zero',
            event_compatible: false,
            cost_basis_mode: 'required_qty_pos',
            cost_basis_auto: false,
        },
    ],
    event_types: [],
});

// ---------------------------------------------------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------------------------------------------------

const ASSET_ID = 42;
const DAY = '2024-03-10';

const rewardQuery = () => vi.mocked(zodiosApi.query_reward_values_api_v1_assets_prices_reward_values_post);

function txRow(overrides: Record<string, unknown> = {}) {
    return {
        id: 101,
        broker_id: 17,
        asset_id: ASSET_ID,
        type: 'REWARD',
        date: DAY,
        quantity: '2',
        cash: null,
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

/** A new REWARD row in the form (create mode, seeded from `items` as the Bulk editor hands one), pushed on Save. */
function mountReward(overrides: Record<string, unknown> = {}, props: Record<string, unknown> = {}) {
    const onPushDraft = vi.fn();
    const onClose = vi.fn();
    const result = render(TransactionFormModal, {open: true, mode: 'create', items: [txRow(overrides)], commitOnSave: false, onPushDraft, onClose, ...props});
    return {onPushDraft, onClose, ...result};
}

/** The reader's answer: the asset's value on receipt on `date`, per unit, as the backend computed it. */
function rewardAnswer(amount: string, currency = 'USD', date = DAY, assetId = ASSET_ID) {
    return {items: [{asset_id: assetId, date, status: 'FILLED', value: {code: currency, amount}}]} as never;
}

/** The reader's answer without a value: `status` NO_PRICE_THAT_DAY or NO_HISTORY. */
function noValueAnswer(status: 'NO_PRICE_THAT_DAY' | 'NO_HISTORY', date = DAY, assetId = ASSET_ID) {
    return {items: [{asset_id: assetId, date, status, value: null}]} as never;
}

/** Let the suggestion's promise chain (query → fetchRewardValue → the form's `.then`) run out, then render. */
async function settleSuggestion() {
    for (const result of rewardQuery().mock.results) await result.value;
    for (let i = 0; i < 20; i++) await Promise.resolve();
    await tick();
}

function amountInput(): HTMLInputElement {
    return screen.getByTestId('tx-form-cost-basis-input-amount') as HTMLInputElement;
}

async function typeAmount(value: string) {
    const input = amountInput();
    await fireEvent.input(input, {target: {value}});
    expect(input).toHaveValue(value);
}

async function saveAndReadPush(onPushDraft: ReturnType<typeof vi.fn>): Promise<Record<string, unknown>> {
    await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
    await fireEvent.click(screen.getByTestId('tx-form-save'));
    expect(onPushDraft).toHaveBeenCalledTimes(1);
    const pushed = onPushDraft.mock.calls.at(-1)?.[0] as Record<string, unknown> | undefined;
    if (!pushed) throw new Error('Save did not push the draft');
    return pushed;
}

async function setFormDate(date: string) {
    const wrapper = screen.getByTestId('tx-form-date-wrap');
    const input = within(within(wrapper).getByTestId('single-date-picker-root')).getByRole('textbox') as HTMLInputElement;
    await fireEvent.input(input, {target: {value: date}});
    await fireEvent.blur(input);
}

describe('TransactionFormModal — a REWARD states its value on receipt (79 STK-2a)', () => {
    beforeEach(async () => {
        vi.clearAllMocks();
        guideAnchors.clear();
        rewardQuery().mockReset();
        rewardQuery().mockResolvedValue(noValueAnswer('NO_HISTORY'));
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_WITH_REWARD);
        // The asset in the store, as the form normally has it (the suggestion itself no longer waits for it: STK-4b)
        resetAssetStore();
        mergeAssets([{id: ASSET_ID, display_name: 'Reward asset', currency: 'EUR', quote_base_quantity: 1, active: true}]);
        await setupI18n();
        await ensureTypesLoaded();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    // -------------------------------------------------------------------------------------------------------
    //  The field
    // -------------------------------------------------------------------------------------------------------

    it('quantity > 0: the inline value field shows, with its amount input and without the Auto/Manual toggle', async () => {
        mountReward();

        await screen.findByTestId('tx-form-cost-basis-inline');
        expect(amountInput()).toBeInTheDocument();
        expect(screen.queryByTestId('tx-form-cost-basis-toggle'), 'a REWARD never takes the average cost: no Auto/Manual toggle').toBeNull();
        expect(screen.queryByTestId('tx-form-cost-basis-toggle-auto')).toBeNull();
    });

    it('guard: an ADJUSTMENT with the same quantity keeps its toggle, and asks no price', async () => {
        mountReward({type: 'ADJUSTMENT', cost_basis_mode: 'manual'});

        await screen.findByTestId('tx-form-cost-basis-inline');
        expect(screen.getByTestId('tx-form-cost-basis-toggle')).toBeInTheDocument();
        await settleSuggestion();
        expect(rewardQuery(), 'only a REWARD suggests its value from the price history').not.toHaveBeenCalled();
    });

    it.each(['0', ''])('quantity %j: no value field (units in only)', async (quantity) => {
        mountReward({quantity});

        await screen.findByTestId('tx-form-quantity');
        expect(screen.queryByTestId('tx-form-cost-basis-inline')).toBeNull();
    });

    it.each([
        ['none', null],
        ['auto', 'auto'],
    ] as const)('a REWARD handed with mode %s, no value and no stored price: the warning shows — the form is in Manual', async (_label, mode) => {
        mountReward({cost_basis_mode: mode});

        await screen.findByTestId('tx-form-cost-basis-inline');
        await waitFor(() => expect(rewardQuery()).toHaveBeenCalledTimes(1));
        await settleSuggestion();
        // The warning shows only outside Auto: here it proves the forced Manual too.
        expect(screen.getByTestId('tx-form-cost-basis-warning')).toBeInTheDocument();
        expect(screen.queryByTestId('tx-form-reward-value-from-history'), 'no stored price, no note').toBeNull();
        expect(amountInput()).toHaveValue('');
    });

    it("a REWARD handed in 'auto' is pushed in Manual with the value typed", async () => {
        const {onPushDraft} = mountReward({cost_basis_mode: 'auto'});

        await screen.findByTestId('tx-form-cost-basis-inline');
        await waitFor(() => expect(rewardQuery()).toHaveBeenCalledTimes(1));
        await settleSuggestion();
        await typeAmount('3.5');
        await waitFor(() => expect(screen.queryByTestId('tx-form-cost-basis-warning')).toBeNull());

        const pushed = await saveAndReadPush(onPushDraft);
        expect(pushed.type).toBe('REWARD');
        expect(pushed._cost_basis_mode, 'rule 12c refuses Auto: the form never sends it for a REWARD').toBe('manual');
        expect(pushed.cost_basis_override).toEqual({code: 'EUR', amount: '3.5'});
    });

    // -------------------------------------------------------------------------------------------------------
    //  The suggestion from the price history
    // -------------------------------------------------------------------------------------------------------

    it('an empty value is filled from the close of that day: one reader query for {asset, day}, the note shows, no warning', async () => {
        // The reader keeps the stored form of the close (61.250000 at base 1): the field shows it without trailing zeros
        rewardQuery().mockResolvedValue(rewardAnswer('61.250000', 'USD'));
        const {onPushDraft} = mountReward();

        await waitFor(() => expect(amountInput()).toHaveValue('61.25'));
        expect(rewardQuery()).toHaveBeenCalledTimes(1);
        expect(rewardQuery().mock.calls[0][0]).toEqual([{asset_id: ASSET_ID, date: DAY}]);
        expect(screen.getByTestId('tx-form-reward-value-from-history')).toBeInTheDocument();
        expect(screen.queryByTestId('tx-form-cost-basis-warning')).toBeNull();

        const pushed = await saveAndReadPush(onPushDraft);
        expect(pushed._cost_basis_mode).toBe('manual');
        const override = pushed.cost_basis_override as {code: string; amount: string};
        expect(override.code, 'the price currency').toBe('USD');
        expect(Number(override.amount)).toBe(61.25);
    });

    it('the form asks without waiting for the asset in the store, and never divides: the value is per unit as answered', async () => {
        // STK-4b: the backend divides the close by the quote base. A bond quoted per 100 answers 0.985 per unit; the
        // form shows it as given, before and after the store learns the base of 100.
        resetAssetStore();
        rewardQuery().mockResolvedValue(rewardAnswer('0.985', 'EUR'));
        mountReward();

        await waitFor(() => expect(rewardQuery(), 'no asset in the store yet: the form asks all the same').toHaveBeenCalledTimes(1));
        await waitFor(() => expect(amountInput()).toHaveValue('0.985'));

        mergeAssets([{id: ASSET_ID, display_name: 'Reward bond', currency: 'EUR', quote_base_quantity: 100, active: true}]);
        await settleSuggestion();
        expect(amountInput(), 'the store learning the base divides nothing').toHaveValue('0.985');
        expect(rewardQuery(), 'and asks nothing again').toHaveBeenCalledTimes(1);
    });

    it.each(['NO_PRICE_THAT_DAY', 'NO_HISTORY'] as const)('%s: nothing is filled, the warning stays', async (status) => {
        rewardQuery().mockResolvedValue(noValueAnswer(status));
        mountReward();

        await waitFor(() => expect(rewardQuery()).toHaveBeenCalledTimes(1));
        await settleSuggestion();
        expect(amountInput()).toHaveValue('');
        expect(screen.getByTestId('tx-form-cost-basis-warning')).toBeInTheDocument();
        expect(screen.queryByTestId('tx-form-reward-value-from-history')).toBeNull();
    });

    it('an answer for another day fills nothing: only the reward day is read', async () => {
        rewardQuery().mockResolvedValue(rewardAnswer('61.25', 'USD', '2024-03-08'));
        mountReward();

        await waitFor(() => expect(rewardQuery()).toHaveBeenCalledTimes(1));
        await settleSuggestion();
        expect(amountInput()).toHaveValue('');
        expect(screen.queryByTestId('tx-form-reward-value-from-history')).toBeNull();
    });

    it('calibration of settleSuggestion: once it returns, a suggestion that arrives is already on screen', async () => {
        // The negative cases below («asks nothing», «never overwritten») rest on settleSuggestion having let the
        // suggestion's chain run out. This positive proves it does: red here means those negatives prove nothing.
        rewardQuery().mockResolvedValue(rewardAnswer('61.25'));
        mountReward();

        await screen.findByTestId('tx-form-cost-basis-inline');
        await waitFor(() => expect(rewardQuery()).toHaveBeenCalledTimes(1));
        await settleSuggestion();
        expect(screen.getByTestId('tx-form-reward-value-from-history')).toBeInTheDocument();
        expect(amountInput()).toHaveValue('61.25');
    });

    it('a suggested value the user changes is the user’s: the note goes, the typed value stays', async () => {
        rewardQuery().mockResolvedValue(rewardAnswer('61.25'));
        mountReward();

        await waitFor(() => expect(screen.getByTestId('tx-form-reward-value-from-history')).toBeInTheDocument());
        await typeAmount('70');

        await waitFor(() => expect(screen.queryByTestId('tx-form-reward-value-from-history')).toBeNull());
        expect(amountInput()).toHaveValue('70');
        expect(rewardQuery(), 'no new query for the same asset and day').toHaveBeenCalledTimes(1);
    });

    it('a value typed while the price query is still out is never overwritten by its answer', async () => {
        let answer: (value: unknown) => void = () => undefined;
        rewardQuery().mockReturnValue(new Promise((resolve) => (answer = resolve)) as never);
        const {onPushDraft} = mountReward();

        await waitFor(() => expect(rewardQuery()).toHaveBeenCalledTimes(1));
        await typeAmount('7');
        answer(rewardAnswer('61.25'));
        await settleSuggestion();

        expect(amountInput()).toHaveValue('7');
        expect(screen.queryByTestId('tx-form-reward-value-from-history')).toBeNull();
        const pushed = await saveAndReadPush(onPushDraft);
        expect(pushed.cost_basis_override).toEqual({code: 'EUR', amount: '7'});
    });

    it('a REWARD that already holds a value asks nothing', async () => {
        mountReward({cost_basis_mode: 'manual', cost_basis_override: {code: 'EUR', amount: '5'}});

        await screen.findByTestId('tx-form-cost-basis-inline');
        await waitFor(() => expect(amountInput()).toHaveValue('5'));
        await settleSuggestion();
        expect(rewardQuery()).not.toHaveBeenCalled();
        expect(screen.queryByTestId('tx-form-reward-value-from-history')).toBeNull();
    });

    it('view mode asks nothing', async () => {
        render(TransactionFormModal, {open: true, mode: 'view', items: [txRow({cost_basis_mode: 'manual'})], onClose: vi.fn()});

        await screen.findByTestId('tx-form-quantity');
        await settleSuggestion();
        expect(rewardQuery()).not.toHaveBeenCalled();
    });

    it('a new day with the value still empty asks again, once, for that day', async () => {
        mountReward();

        await waitFor(() => expect(rewardQuery()).toHaveBeenCalledTimes(1));
        await settleSuggestion();
        expect(screen.getByTestId('tx-form-cost-basis-warning'), 'premise: nothing stored on the first day').toBeInTheDocument();

        rewardQuery().mockResolvedValue(rewardAnswer('12', 'EUR', '2024-03-12'));
        await setFormDate('2024-03-12');

        await waitFor(() => expect(rewardQuery()).toHaveBeenCalledTimes(2));
        expect(rewardQuery().mock.calls[1][0]).toEqual([{asset_id: ASSET_ID, date: '2024-03-12'}]);
        await waitFor(() => expect(amountInput()).toHaveValue('12'));
        expect(screen.getByTestId('tx-form-reward-value-from-history')).toBeInTheDocument();
    });
});
