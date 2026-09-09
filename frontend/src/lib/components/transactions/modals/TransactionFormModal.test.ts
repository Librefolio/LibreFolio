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
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {commitTransactions} from '$lib/utils/transactions/txCommitApi';
import {ensureTypesLoaded} from '$lib/stores/transactions/transactionTypeStore';

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

describe('TransactionFormModal — draft seeding (T1-b, T3)', () => {
    beforeEach(async () => {
        vi.clearAllMocks();
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(validMinimalTXTypesResponse);
        await setupI18n();
        await ensureTypesLoaded();
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
