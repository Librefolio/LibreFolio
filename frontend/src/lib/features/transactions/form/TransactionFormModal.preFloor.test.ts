// @vitest-environment jsdom
/**
 * TransactionFormModal — the warning for a date before 1900 (D-P4, W5-10), component test (Vitest + jsdom).
 *
 * The backend still refuses a transaction before 1900-01-01; the form warns first and asks for ONE confirmation. The
 * contract, read through test ids and attributes only:
 *   - `tx-form-pre-floor` (an amber banner) appears when the main date, or in a pair the second date, is before 1900 and
 *     the form is not read-only; its `data-pending` is `true` until the user confirms those dates;
 *   - the button `tx-form-pre-floor-confirm` exists only while the answer is pending and only when the form saves by
 *     itself (`commitOnSave`, the default);
 *   - while pending the save button `tx-form-save` is disabled and a click that still reaches `commit()` commits nothing;
 *     after the confirmation the save goes through, with the date typed;
 *   - the confirmation belongs to the dates asked about: another date before 1900 asks again; reopening the form resets it;
 *   - editing a saved row: a date equal to the one the row already holds is not asked about;
 *   - `commitOnSave=false` (the form is opened from the bulk editor): banner without button, Apply is NOT gated (the bulk
 *     editor asks once for all its rows);
 *   - view mode shows nothing.
 *
 * Nothing is asserted on a translated sentence. The commit api is mocked, so «committed» is read from its call list, always
 * with a positive control (after the confirmation the same click does commit).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {mergeAssets, resetAssetStore} from '$lib/stores/reference/assetStore';
import {schemas} from '$lib/api/generated';
import {commitTransactions} from '$lib/features/transactions/txCommitApi';
import {ensureTypesLoaded} from '$lib/features/transactions/transactionTypeStore';

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
// The validate scheduler may fire on a complete draft; keep the wire out of it.
vi.mock('$lib/features/transactions/txCommitApi', () => ({
    commitTransactions: vi.fn(async () => ({committed: true, results: [], issues: []})),
    validateTransactions: vi.fn(async () => ({committed: true, issues: [], rawResponse: {wac_results: []}})),
}));

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
const OLD = '1850-05-01';
const OTHER_OLD = '1851-06-02';
const NORMAL = '2024-03-12';

/** A form on the shared broker, saving by itself unless a test says otherwise. */
function mount(props: Record<string, unknown> = {}) {
    const onClose = vi.fn();
    const onPushDraft = vi.fn();
    return {onClose, onPushDraft, ...render(TransactionFormModal, {open: true, mode: 'create', items: null, defaultBrokerId: 17, onPushDraft, onClose, ...props})};
}

function txRow(overrides: Record<string, unknown> = {}) {
    return {
        id: 101,
        broker_id: 17,
        asset_id: ASSET,
        type: 'BUY',
        date: '2024-03-10',
        quantity: '12',
        cash: {code: 'EUR', amount: '-1000.8'},
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

/** A saved transfer: the sender (101) and the receiver (202), each with its own date. */
function transferPair(senderDate: string, receiverDate: string) {
    const sender = txRow({id: 101, broker_id: 17, type: 'TRANSFER', quantity: '-5', cash: null, date: senderDate, related_transaction_id: 202, partner_broker_id: 23});
    const receiver = txRow({id: 202, broker_id: 23, type: 'TRANSFER', quantity: '5', cash: null, date: receiverDate, related_transaction_id: 101, partner_broker_id: 17});
    return {items: [sender, receiver]};
}

const banner = (): HTMLElement | null => screen.queryByTestId('tx-form-pre-floor');
const confirmButton = (): HTMLElement | null => screen.queryByTestId('tx-form-pre-floor-confirm');
const saveButton = (): HTMLElement => screen.getByTestId('tx-form-save');

/** Types a date in the picker of the wrapper and leaves the field (the way the user commits it). */
async function setTypedDate(wrapperTestId: string, date: string) {
    const wrapper = screen.getByTestId(wrapperTestId);
    const input = within(within(wrapper).getByTestId('single-date-picker-root')).getByRole('textbox') as HTMLInputElement;
    await fireEvent.input(input, {target: {value: date}});
    await fireEvent.blur(input);
}

/** The main date of a single form. */
const setMainDate = (date: string) => setTypedDate('tx-form-date-wrap', date);

async function setCashAmount(testid: string, amount: string) {
    const input = screen.getByTestId(`${testid}-amount`) as HTMLInputElement;
    await fireEvent.input(input, {target: {value: amount}});
    await fireEvent.blur(input);
}

async function chooseDualType(code: 'FX_CONVERSION' | 'TRANSFER') {
    await fireEvent.click(within(screen.getByTestId('tx-form-type')).getByRole('combobox'));
    await waitFor(() => expect(screen.getByRole('listbox')).toBeInTheDocument());
    const dropdown = screen.getByRole('listbox').parentElement as HTMLElement;
    await fireEvent.click(within(dropdown).getByTestId(`search-select-option-${code}`));
    await waitFor(() => expect(screen.getByTestId('tx-form-dual-split')).toBeInTheDocument());
}

/** The form is on screen and its save is usable: the premise every «now it is disabled» below leans on. */
async function formReady(): Promise<void> {
    await screen.findByTestId('tx-form-date-wrap');
    await waitFor(() => expect(saveButton()).toBeEnabled());
}

describe('TransactionFormModal — a date before 1900 (D-P4)', () => {
    beforeEach(async () => {
        vi.clearAllMocks();
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_RESPONSE);
        resetAssetStore();
        mergeAssets([{id: ASSET, display_name: 'Pre-floor asset', currency: 'EUR', quote_base_quantity: 1, active: true}]);
        await setupI18n();
        await ensureTypesLoaded();
    });

    afterEach(() => {
        cleanup();
        resetAssetStore();
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (a) the single form that saves by itself
    // -----------------------------------------------------------------------------------------------------------------
    describe('(a) a single form that saves by itself', () => {
        it('a normal date shows no banner and no button; the save is enabled', async () => {
            mount({mode: 'edit', items: [txRow()]});
            await formReady();

            expect(banner()).toBeNull();
            expect(confirmButton()).toBeNull();
            expect(saveButton()).toBeEnabled();
        });

        it('1900-01-01 itself is not before the floor: no banner', async () => {
            mount({mode: 'edit', items: [txRow()]});
            await formReady();

            await setMainDate('1900-01-01');
            await waitFor(() => expect(within(screen.getByTestId('tx-form-date-wrap')).getByRole('textbox')).toHaveValue('1900-01-01'));

            expect(banner()).toBeNull();
            expect(saveButton()).toBeEnabled();
        });

        it('a typed date before 1900: the banner is pending, with the confirm button, and the save is disabled', async () => {
            mount({mode: 'edit', items: [txRow()]});
            await formReady();

            await setMainDate(OLD);

            await waitFor(() => expect(banner()).not.toBeNull());
            expect(banner()).toHaveAttribute('data-pending', 'true');
            expect(confirmButton(), 'a form that saves by itself offers the answer').not.toBeNull();
            expect(saveButton()).toBeDisabled();
        });

        it('a click that still reaches the save while pending commits nothing; after the confirmation the same click commits the date typed', async () => {
            mount({mode: 'edit', items: [txRow()]});
            await formReady();
            await setMainDate(OLD);
            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'true'));

            // A dispatched click reaches a disabled control in jsdom: the guard in commit() is what is proved.
            await fireEvent.click(saveButton());
            expect(commitTransactions).not.toHaveBeenCalled();

            await fireEvent.click(screen.getByTestId('tx-form-pre-floor-confirm'));
            await waitFor(() => expect(saveButton()).toBeEnabled());
            await fireEvent.click(saveButton());

            await waitFor(() => expect(commitTransactions).toHaveBeenCalledTimes(1));
            expect(vi.mocked(commitTransactions).mock.calls[0]?.[0]).toEqual({updates: [{id: 101, date: OLD}]});
        });

        it('the confirmation: the banner stays but is no longer pending, the button goes, the save is enabled', async () => {
            mount({mode: 'edit', items: [txRow()]});
            await formReady();
            await setMainDate(OLD);
            await waitFor(() => expect(confirmButton()).not.toBeNull());

            await fireEvent.click(screen.getByTestId('tx-form-pre-floor-confirm'));

            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'false'));
            expect(confirmButton()).toBeNull();
            expect(saveButton()).toBeEnabled();
        });

        it('another date before 1900 asks again; a normal date clears the banner', async () => {
            mount({mode: 'edit', items: [txRow()]});
            await formReady();
            await setMainDate(OLD);
            await fireEvent.click(await screen.findByTestId('tx-form-pre-floor-confirm'));
            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'false'));

            await setMainDate(OTHER_OLD);

            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'true'));
            expect(confirmButton(), 'the button is back').not.toBeNull();
            expect(saveButton()).toBeDisabled();

            await setMainDate(NORMAL);

            await waitFor(() => expect(banner()).toBeNull());
            expect(confirmButton()).toBeNull();
            expect(saveButton()).toBeEnabled();
        });

        it('a new form (create): the default date is today, no banner; a date before 1900 typed asks', async () => {
            mount();
            await formReady();
            expect(banner()).toBeNull();

            await setMainDate(OLD);

            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'true'));
            expect(saveButton()).toBeDisabled();
        });

        it('reopening the form resets the confirmation: a form opened again on the same date asks again', async () => {
            const first = mount({mode: 'create'});
            await formReady();
            await setMainDate(OLD);
            await fireEvent.click(await screen.findByTestId('tx-form-pre-floor-confirm'));
            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'false'));

            // Closed, then opened again by the parent (`open` false -> true): the form starts over.
            await first.rerender({open: false});
            await first.rerender({open: true, mode: 'create', items: null});
            await formReady();
            await setMainDate(OLD);

            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'true'));
            expect(confirmButton()).not.toBeNull();
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (b) editing a saved row
    // -----------------------------------------------------------------------------------------------------------------
    describe('(b) a saved row opened for editing', () => {
        it('a row saved before 1900 is not asked about while its date is untouched', async () => {
            mount({mode: 'edit', items: [txRow({date: OLD})]});
            await formReady();

            expect(banner(), 'the date is the row’s own: nothing to ask').toBeNull();
            expect(saveButton()).toBeEnabled();
        });

        it('changing it to another date before 1900 asks, and putting the saved date back stops asking', async () => {
            mount({mode: 'edit', items: [txRow({date: OLD})]});
            await formReady();

            await setMainDate(OTHER_OLD);
            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'true'));
            expect(saveButton()).toBeDisabled();

            await setMainDate(OLD);
            await waitFor(() => expect(banner()).toBeNull());
            expect(saveButton()).toBeEnabled();
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (c) a pair
    // -----------------------------------------------------------------------------------------------------------------
    describe('(c) a pair', () => {
        it('a new FX pair: the second date before 1900 asks, the main one normal', async () => {
            mount();
            await chooseDualType('FX_CONVERSION');
            expect(banner()).toBeNull();

            await setTypedDate('tx-form-dual-to', OLD);

            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'true'));
            expect(saveButton()).toBeDisabled();
            await fireEvent.click(screen.getByTestId('tx-form-pre-floor-confirm'));
            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'false'));
        });

        it('a new FX pair: the first date before 1900 asks too', async () => {
            mount();
            await chooseDualType('FX_CONVERSION');

            await setTypedDate('tx-form-dual-from', OLD);

            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'true'));
        });

        it('a new FX pair, both dates before 1900: one banner for both, one confirmation', async () => {
            mount();
            await chooseDualType('FX_CONVERSION');
            await setTypedDate('tx-form-dual-from', OLD);
            await setTypedDate('tx-form-dual-to', OTHER_OLD);

            await waitFor(() => expect(screen.getAllByTestId('tx-form-pre-floor')).toHaveLength(1));
            await fireEvent.click(screen.getByTestId('tx-form-pre-floor-confirm'));

            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'false'));
            expect(saveButton()).toBeEnabled();
        });

        it('a saved transfer: the second leg’s date changed to before 1900 asks; its saved date does not', async () => {
            mount({mode: 'edit', ...transferPair('2024-03-10', '2024-03-11')});
            await screen.findByTestId('tx-form-dual-split');
            expect(banner()).toBeNull();

            await setTypedDate('tx-form-dual-to', OLD);

            await waitFor(() => expect(banner()).toHaveAttribute('data-pending', 'true'));
        });

        it('a saved transfer whose second leg was saved before 1900 is not asked about while it stays', async () => {
            mount({mode: 'edit', ...transferPair('2024-03-10', OLD)});
            await screen.findByTestId('tx-form-dual-split');

            expect(banner()).toBeNull();
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (d) a form that only hands the row to the bulk editor
    // -----------------------------------------------------------------------------------------------------------------
    describe('(d) commitOnSave = false (opened from the bulk editor)', () => {
        it('the banner shows without the button, and Apply is not gated: it pushes the draft with the date', async () => {
            const {onPushDraft, onClose} = mount({mode: 'edit', items: [txRow()], commitOnSave: false});
            await formReady();

            await setMainDate(OLD);

            await waitFor(() => expect(banner()).not.toBeNull());
            expect(banner()).toHaveAttribute('data-pending', 'false');
            expect(confirmButton(), 'the bulk editor asks, not the form').toBeNull();
            expect(saveButton()).toBeEnabled();

            await fireEvent.click(saveButton());

            expect(onPushDraft).toHaveBeenCalledTimes(1);
            expect(onPushDraft.mock.calls[0]?.[0]).toMatchObject({date: OLD});
            expect(onClose).toHaveBeenCalledTimes(1);
            expect(commitTransactions).not.toHaveBeenCalled();
        });

        it('a new pair pushed from the bulk editor: banner without button, Apply pushes both legs', async () => {
            const {onPushDraft} = mount({commitOnSave: false});
            await chooseDualType('FX_CONVERSION');
            await setCashAmount('tx-form-cash-from', '125.5');
            await setCashAmount('tx-form-cash-to', '140.25');
            await setTypedDate('tx-form-dual-to', OLD);

            await waitFor(() => expect(banner()).not.toBeNull());
            expect(confirmButton()).toBeNull();
            expect(banner()).toHaveAttribute('data-pending', 'false');
            await waitFor(() => expect(saveButton()).toBeEnabled());
            await fireEvent.click(saveButton());

            expect(onPushDraft).toHaveBeenCalledTimes(1);
            expect(onPushDraft.mock.calls[0]?.[0]).toMatchObject({_dual: true, _partnerDate: OLD});
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // (e) view mode
    // -----------------------------------------------------------------------------------------------------------------
    describe('(e) view mode', () => {
        it('a saved transaction dated before 1900 shows no banner and no button', async () => {
            mount({mode: 'view', items: [txRow({date: OLD})]});

            expect(await screen.findByTestId('tx-form-date-readonly')).toHaveTextContent(OLD);
            expect(banner()).toBeNull();
            expect(confirmButton()).toBeNull();
        });
    });
});
