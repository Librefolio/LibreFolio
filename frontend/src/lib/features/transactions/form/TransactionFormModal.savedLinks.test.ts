// @vitest-environment jsdom
/**
 * TransactionFormModal — the window before a change of broker or asset undoes a link with a SAVED transaction (project 66,
 * lot TL-12). RED FIRST: `brokenSavedLinks` and the window `tx-form-unlink-saved` do not exist yet.
 *
 * Only a new row changes broker or asset (a saved one has them locked), so the form is mounted as the Bulk hosts it on a
 * new row: `mode: 'create'` with the row handed. Today a pick made in this very opening is dropped in silence, and a link
 * handed by the Bulk (`_charges` with `linkNew`, `parent_transaction_id`) is left on a transaction it can no longer hold.
 *
 *   1. new parent, new charges only            → no window, they follow (TL-3b)
 *   2. new parent, saved charges linked here   → the window names them. Confirm: they leave the section, the change is made.
 *                                                Cancel: the value, the section and the select are as before.
 *   3. new charge, saved parent (handed, or picked here) → the window names the parent. Confirm: `_parent_unlink: true`
 *                                                (handed), no `_parent_link` (picked).
 *   4. new charge, new parent (`_newParent`)   → no window
 *
 * The window is the ConfirmModal with testId `tx-form-unlink-saved` (on its header, so the dialog is the closest
 * `[role="dialog"]`), one `tx-form-unlink-saved-item[data-tx-id]` per transaction, always on screen.
 *
 * What a select shows, by a handle that is not translated: the asset's and the broker's names are this file's own data; the
 * type's trigger has only its icon (`/icons/transactions/<slug>.png`). The three selects write their own `value` when the
 * user chooses: after «Cancel» they must show the OLD value, not the one refused. Elements are read again every time, so a
 * remount is as good as a reset.
 *
 * The «New broker» and «New asset» windows are stand-ins: what the form does with a row just created is its own callback
 * (`oncreated`), and the real windows have their own tests.
 *
 * data-testid, data-* and payloads only, never a translated text.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {ensureTypesLoaded, getTransactionTypeIconUrl} from '$lib/features/transactions/transactionTypeStore';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
import {mergeAssets, resetAssetStore} from '$lib/stores/reference/assetStore';
import {mergeBrokers, resetBrokerStore} from '$lib/stores/reference/brokerStore';

const {created} = vi.hoisted(() => ({
    /** The props of the two creation windows the form mounts, as it handed them. */
    created: {broker: null as Record<string, unknown> | null, asset: null as Record<string, unknown> | null},
}));
vi.mock('$lib/features/brokers/BrokerModal.svelte', () => ({
    default: (_anchor: unknown, props: Record<string, unknown>) => {
        created.broker = props;
        return {};
    },
}));
vi.mock('$lib/features/assets/AssetModal.svelte', () => ({
    default: (_anchor: unknown, props: Record<string, unknown>) => {
        created.asset = props;
        return {};
    },
}));
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
    ensureBrokerIconFieldsLoaded: vi.fn().mockResolvedValue(undefined),
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
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));
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
// The guide starts in create mode: a neutral stub keeps the real controller out.
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
//  Invented data. Broker and asset ids never meet: their options share `search-select-option-<id>`.
// ---------------------------------------------------------------------------------------------------------------

const BROKER = {id: 71, name: 'Invented broker Alfa'};
const BROKER_2 = {id: 72, name: 'Invented broker Beta'};
const BROKER_NEW = {id: 73, name: 'Invented broker Gamma'};
const ASSET = {id: 5, display_name: 'Invented asset five', currency: 'EUR'};
const ASSET_2 = {id: 9, display_name: 'Invented asset nine', currency: 'USD'};
const ASSET_NEW = {id: 12, display_name: 'Invented asset twelve', currency: 'USD'};

const baseType = {doc_slug: 'x', requires_link: false, event_compatible: false, cost_basis_mode: 'forbidden'} as const;

const TYPES_WITH_CHARGE_ROLES = schemas.TXTypesResponse.parse({
    transaction_types: [
        {...baseType, code: 'BUY', name: 'Buy', description: 'Buy', icon_slug: 'buy', asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'positive', cash_sign: 'negative', charge_role: 'parent'},
        {...baseType, code: 'SELL', name: 'Sell', description: 'Sell', icon_slug: 'sell', asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'negative', cash_sign: 'positive', charge_role: 'parent'},
        {...baseType, code: 'DEPOSIT', name: 'Deposit', description: 'Deposit', icon_slug: 'deposit', asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'positive', charge_role: 'parent'},
        {...baseType, code: 'FEE', name: 'Fee', description: 'Fee', icon_slug: 'fee', asset_mode: 'optional', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'negative', charge_role: 'charge'},
        {...baseType, code: 'TAX', name: 'Tax', description: 'Tax', icon_slug: 'tax', asset_mode: 'optional', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'negative', charge_role: 'charge'},
    ],
    event_types: [],
});

type Row = Record<string, unknown>;
type Draft = Record<string, unknown>;

const queryApi = () => vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get);

/** A row as the API gives it; a new BUY (no id) unless `over` says otherwise. */
function txRow(over: Row = {}): Row {
    return {
        id: 0,
        broker_id: BROKER.id,
        asset_id: ASSET.id,
        type: 'BUY',
        date: '2024-03-10',
        quantity: '3',
        cash: {code: 'EUR', amount: '-137'},
        related_transaction_id: null,
        partner_broker_id: null,
        parent_transaction_id: null,
        charges_count: 0,
        tags: [],
        description: '',
        cost_basis_override: null,
        cost_basis_mode: null,
        asset_event_id: null,
        created_at: '2024-03-10T00:00:00Z',
        updated_at: '2024-03-10T00:00:00Z',
        ...over,
    };
}

/** A new FEE (no id). */
const newFee = (over: Row = {}) => txRow({type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-4'}, ...over});
/** A saved FEE linked to nothing, as the picker's candidates come. */
const freeFee = (id: number) => newFee({id, description: `saved fee ${id}`});
/** A saved BUY, a parent candidate. */
const savedBuy = (id: number) => txRow({id});

/** A saved charge linked here (`linkNew`), as the Bulk hands it in `_charges`. */
function savedDraft(id: number, over: Draft = {}): Draft {
    const type = (over.type as string | undefined) ?? 'FEE';
    const values = {type, cash: {amount: '4', code: 'EUR'}, description: `saved fee ${id}`};
    return {key: `saved-${id}`, id, ...values, original: {...values}, state: 'linked', linkNew: true, ...over};
}
/** A new charge of the Bulk, as it hands it in `_charges`. */
const opDraft = (tempId: string): Draft => ({key: `op-${tempId}`, id: null, type: 'FEE', cash: {amount: '2', code: 'EUR'}, description: 'new fee', original: null, state: 'linked'});

/** The candidates of the two pickers, and the parent read by id. */
function answer(opts: {withoutParent?: Row[]; parents?: Row[]; byId?: () => unknown}) {
    queryApi().mockImplementation((async (arg: {queries: {without_parent?: boolean; types?: string[]; ids?: number[]}}) => {
        if (arg.queries.without_parent) return opts.withoutParent ?? [];
        if (arg.queries.types) return opts.parents ?? [];
        if (arg.queries.ids) return opts.byId ? opts.byId() : [];
        return [];
    }) as never);
}

/** The form as the Bulk hosts it on a new row. */
function bulkNewRow(row: Row, extra: Record<string, unknown> = {}) {
    const onPushDraft = vi.fn();
    const onClose = vi.fn();
    return {onPushDraft, onClose, ...render(TransactionFormModal, {open: true, mode: 'create', commitOnSave: false, allowChargeEdits: true, onPushDraft, onClose, items: [row], ...extra} as never)};
}

const rowKeys = () => screen.queryAllByTestId('tx-form-charge-row').map((row) => row.getAttribute('data-charge-key'));
const parentBox = () => screen.getByTestId('tx-form-parent');

/** A new BUY opened with these charges already linked under it (a reopened form: nothing picked here). */
async function reopenedBuy(charges: Draft[], over: Row = {}) {
    const mounted = bulkNewRow({...txRow(over), _charges: charges});
    await waitFor(() => expect(rowKeys()).toEqual(charges.map((draft) => draft.key)));
    await formSettled();
    return mounted;
}

/** The form's own hydration ended: the broker is named on screen (the store is the form's source). */
async function formSettled() {
    await waitFor(() => expect(brokerTrigger()).toHaveTextContent(BROKER.name));
}

// ---------------------------------------------------------------------------------------------------------------
//  The three selects: what they show, and a choice made in them
// ---------------------------------------------------------------------------------------------------------------

function comboboxIn(testId: string): HTMLElement {
    const combobox = screen.getByTestId(testId).querySelector<HTMLElement>('[role="combobox"]');
    if (!combobox) throw new Error(`no combobox in ${testId}`);
    return combobox;
}
const brokerTrigger = () => comboboxIn('tx-form-broker-wrap');
const typeTrigger = () => comboboxIn('tx-form-type');
const assetTrigger = () => screen.getByTestId('tx-form-asset-trigger');

const options = () => screen.queryAllByTestId(/^search-select-option-/);

/** Choose `value` in the select of `trigger`; ends on no option left on screen (option ids are shared). */
async function choose(trigger: () => HTMLElement, value: string | number) {
    expect(options(), 'no other list is open').toHaveLength(0);
    await fireEvent.click(trigger());
    await fireEvent.click(await screen.findByTestId(`search-select-option-${value}`));
    await waitFor(() => expect(options()).toHaveLength(0));
}

const showsAsset = (name: string) => waitFor(() => expect(assetTrigger(), 'the asset select').toHaveTextContent(name));
const showsBroker = (name: string) => waitFor(() => expect(brokerTrigger(), 'the broker select').toHaveTextContent(name));
/** The type's trigger is named by a translated label: its icon is the only thing that is not. */
const showsType = (type: string) => waitFor(() => expect(typeTrigger().querySelector('img')?.getAttribute('src'), 'the type select').toBe(getTransactionTypeIconUrl(type)));

/** One change of a new BUY: how the user makes it, what its select shows and what «Apply» carries, before and after. */
const CHANGES = [
    {what: 'asset', make: () => choose(assetTrigger, ASSET_2.id), shows: {old: () => showsAsset(ASSET.display_name), next: () => showsAsset(ASSET_2.display_name)}, payload: {old: {asset_id: ASSET.id}, next: {asset_id: ASSET_2.id}}},
    {what: 'broker', make: () => choose(brokerTrigger, BROKER_2.id), shows: {old: () => showsBroker(BROKER.name), next: () => showsBroker(BROKER_2.name)}, payload: {old: {broker_id: BROKER.id}, next: {broker_id: BROKER_2.id}}},
    {what: 'type (to one with no asset)', make: () => choose(typeTrigger, 'DEPOSIT'), shows: {old: () => showsType('BUY'), next: () => showsType('DEPOSIT')}, payload: {old: {type: 'BUY', asset_id: ASSET.id, quantity: '3'}, next: {type: 'DEPOSIT'}}},
] as const;
const [ASSET_CHANGE, BROKER_CHANGE, TYPE_CHANGE] = CHANGES;

// ---------------------------------------------------------------------------------------------------------------
//  The window, and the other confirmation of this form
// ---------------------------------------------------------------------------------------------------------------

const unlinkWindow = () => screen.queryByTestId('tx-form-unlink-saved');

/** The window is up and names these transactions, all on screen with no click. */
async function windowNames(ids: number[]): Promise<HTMLElement> {
    await waitFor(() => expect(unlinkWindow(), '66 TL-12: the window tx-form-unlink-saved does not open').not.toBeNull());
    const dialog = unlinkWindow()!.closest<HTMLElement>('[role="dialog"]');
    expect(dialog, 'the window is a dialog').not.toBeNull();
    const items = within(dialog!).queryAllByTestId('tx-form-unlink-saved-item');
    expect(
        items.map((item) => item.getAttribute('data-tx-id')),
        'the transactions it names, with no click',
    ).toEqual(ids.map(String));
    for (const item of items) {
        expect(item).toBeVisible();
        expect((item.textContent ?? '').trim(), 'an item says which transaction it is').not.toBe('');
    }
    // The catalogue is loaded: a key on screen is a text that was never written.
    expect(dialog!.textContent, 'no text is missing').not.toMatch(/\b(?:transactions|common)(?:\.[A-Za-z]+)+/);
    return dialog!;
}

async function answerWindow(button: 'confirm' | 'cancel') {
    const dialog = unlinkWindow()!.closest<HTMLElement>('[role="dialog"]')!;
    await fireEvent.click(within(dialog).getByTestId(`confirm-modal-${button}`));
    await waitFor(() => expect(unlinkWindow()).toBeNull());
    expect(screen.queryByTestId('confirm-modal-confirm'), 'no other question follows').toBeNull();
}

/** Nothing asks anything: a window would be up by now, since the change itself is on screen. */
function noWindow() {
    expect(unlinkWindow(), 'no window').toBeNull();
    expect(screen.queryByTestId('confirm-modal-confirm'), 'no question').toBeNull();
}

async function applied(onPushDraft: ReturnType<typeof vi.fn>): Promise<Record<string, unknown>> {
    await waitFor(() => expect(screen.getByTestId('tx-form-save')).toBeEnabled());
    await fireEvent.click(screen.getByTestId('tx-form-save'));
    expect(onPushDraft).toHaveBeenCalledTimes(1);
    return onPushDraft.mock.calls[0][0] as Record<string, unknown>;
}

const draftsOf = (payload: Record<string, unknown>) => payload._charges as Draft[];

/** «Cancel» of the form closes it at once: nothing to discard. */
async function closesWithoutAsking(onClose: ReturnType<typeof vi.fn>) {
    await fireEvent.click(screen.getByTestId('tx-form-cancel'));
    await waitFor(() => expect(onClose.mock.calls.length > 0 || screen.queryByTestId('confirm-modal-confirm') !== null).toBe(true));
    expect(screen.queryByTestId('confirm-modal-confirm'), 'nothing to discard').toBeNull();
    expect(onClose).toHaveBeenCalledTimes(1);
}

// ---------------------------------------------------------------------------------------------------------------
//  The pickers
// ---------------------------------------------------------------------------------------------------------------

async function pickIn(id: number) {
    const picker = within(await screen.findByTestId('tx-picker-modal'));
    await fireEvent.click(await picker.findByTestId(`dt-row-checkbox-tx-${id}`));
    await waitFor(() => expect(picker.getByTestId(`dt-row-checkbox-tx-${id}`)).toHaveAttribute('data-state', 'checked'));
}

async function addPicked() {
    await fireEvent.click(screen.getByTestId('tx-picker-add'));
    await waitFor(() => expect(screen.queryByTestId('tx-picker-modal')).toBeNull());
}

/** A new BUY with the saved FEEs `ids` picked in this very opening. */
async function buyWithPicked(ids: number[]) {
    answer({withoutParent: ids.map(freeFee)});
    const mounted = bulkNewRow({...txRow(), _charges: []});
    await formSettled();
    await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));
    for (const id of ids) await pickIn(id);
    await addPicked();
    await waitFor(() => expect(rowKeys().sort()).toEqual(ids.map((id) => `saved-${id}`).sort()));
    return mounted;
}

/** A new FEE with the saved BUY #10 picked as its parent in this very opening. */
async function feeWithPickedParent() {
    answer({parents: [savedBuy(10)]});
    const mounted = bulkNewRow(newFee());
    await formSettled();
    await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'empty'));
    await fireEvent.click(screen.getByTestId('tx-form-parent-link'));
    await pickIn(10);
    await addPicked();
    await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'pending'));
    return mounted;
}

/** A new FEE the Bulk holds under the saved BUY #10. */
async function feeUnderSavedParent() {
    answer({byId: () => [savedBuy(10)]});
    const mounted = bulkNewRow(newFee({parent_transaction_id: 10}));
    await formSettled();
    await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'ready'));
    return mounted;
}

describe('TransactionFormModal — the window before a saved transaction is unlinked (66 TL-12)', () => {
    beforeAll(async () => {
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_WITH_CHARGE_ROLES);
        await setupI18n();
        await ensureTypesLoaded();
    });

    beforeEach(() => {
        queryApi().mockReset();
        queryApi().mockImplementation(async () => []);
        guideAnchors.clear();
        resetAssetStore();
        resetBrokerStore();
        mergeAssets([ASSET, ASSET_2].map((asset) => ({...asset, quote_base_quantity: 1, active: true})) as never);
        mergeBrokers([BROKER, BROKER_2].map((broker) => ({...broker, user_role: 'OWNER'})) as never);
        created.broker = null;
        created.asset = null;
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
        resetAssetStore();
        resetBrokerStore();
    });

    // ---------------------------------------------------------------------------------------------------------
    //  Cell 2, a reopened form: the saved charges come in `_charges`, nothing picked here
    // ---------------------------------------------------------------------------------------------------------

    describe('cell 2, reopened: saved charges handed under a new parent', () => {
        for (const change of CHANGES) {
            it(`${change.what}: the window names the saved charge; Confirm takes it out and makes the change`, async () => {
                const {onPushDraft, onClose} = await reopenedBuy([savedDraft(21)]);

                await change.make();
                await windowNames([21]);
                await answerWindow('confirm');

                await change.shows.next();
                await waitFor(() => expect(rowKeys(), 'the charge left the section').toEqual([]));
                expect(onClose, 'the window closes, not the form').not.toHaveBeenCalled();
                const payload = await applied(onPushDraft);
                expect(payload).toMatchObject(change.payload.next);
                expect(draftsOf(payload), 'no draft about it').toEqual([]);
            });

            it(`${change.what}: Cancel keeps the charge, the value and what the select shows`, async () => {
                const {onPushDraft} = await reopenedBuy([savedDraft(21)]);

                await change.make();
                await windowNames([21]);
                await answerWindow('cancel');

                await change.shows.old();
                expect(rowKeys()).toEqual(['saved-21']);
                const payload = await applied(onPushDraft);
                expect(payload).toMatchObject({type: 'BUY', broker_id: BROKER.id, asset_id: ASSET.id, quantity: '3', cash: {code: 'EUR', amount: '-137'}});
                expect(draftsOf(payload)).toEqual([expect.objectContaining({id: 21, linkNew: true, state: 'linked'})]);
            });

            it(`${change.what}: after Cancel, closing the form asks nothing`, async () => {
                const {onClose} = await reopenedBuy([savedDraft(21)]);

                await change.make();
                await windowNames([21]);
                await answerWindow('cancel');

                await closesWithoutAsking(onClose);
            });
        }

        it('two saved charges: both named, on screen with no click, in the section’s order; Confirm takes both out', async () => {
            const {onPushDraft} = await reopenedBuy([savedDraft(21), savedDraft(22, {type: 'TAX'})]);

            await ASSET_CHANGE.make();
            await windowNames([21, 22]);
            await answerWindow('confirm');

            await waitFor(() => expect(rowKeys()).toEqual([]));
            expect(draftsOf(await applied(onPushDraft))).toEqual([]);
        });

        it('mixed, a saved charge and a new one of the Bulk: only the saved one is named; Confirm keeps the new one linked', async () => {
            const {onPushDraft} = await reopenedBuy([savedDraft(21), opDraft('n-fee')]);

            await ASSET_CHANGE.make();
            await windowNames([21]);
            await answerWindow('confirm');

            await waitFor(() => expect(rowKeys()).toEqual(['op-n-fee']));
            const payload = await applied(onPushDraft);
            expect(payload).toMatchObject({asset_id: ASSET_2.id});
            expect(draftsOf(payload)).toEqual([expect.objectContaining({key: 'op-n-fee', id: null, state: 'linked'})]);
        });

        it('mixed, Cancel: both rows stay, in their order', async () => {
            const {onPushDraft} = await reopenedBuy([savedDraft(21), opDraft('n-fee')]);

            await ASSET_CHANGE.make();
            await windowNames([21]);
            await answerWindow('cancel');

            expect(rowKeys()).toEqual(['saved-21', 'op-n-fee']);
            expect(draftsOf(await applied(onPushDraft)).map((draft) => [draft.key, draft.state])).toEqual([
                ['saved-21', 'linked'],
                ['op-n-fee', 'linked'],
            ]);
        });

        it('refused once, the same change can be made again: the window comes back, and Confirm makes it', async () => {
            const {onPushDraft} = await reopenedBuy([savedDraft(21)]);
            await ASSET_CHANGE.make();
            await windowNames([21]);
            await answerWindow('cancel');
            await ASSET_CHANGE.shows.old();

            await ASSET_CHANGE.make();
            await windowNames([21]);
            await answerWindow('confirm');

            await ASSET_CHANGE.shows.next();
            expect(await applied(onPushDraft)).toMatchObject({asset_id: ASSET_2.id});
        });

        it('from no asset to an asset: it breaks the link too', async () => {
            const {onPushDraft} = await reopenedBuy([savedDraft(21)], {asset_id: null});

            await ASSET_CHANGE.make();
            await windowNames([21]);
            await answerWindow('confirm');

            await waitFor(() => expect(rowKeys()).toEqual([]));
            expect(await applied(onPushDraft)).toMatchObject({asset_id: ASSET_2.id});
        });

        // `setAsset` seeds an empty cash with the new asset's currency. The cash cell falls back on the asset's currency
        // anyway, so the seed is not on screen: what shows it is the form's baseline.
        it('the cash seed of a new asset is not written before Confirm: after Cancel the form is as it was opened', async () => {
            const {onClose} = await reopenedBuy([savedDraft(21)], {cash: null});
            expect(screen.getByTestId('tx-form-cash-currency'), 'premise: the currency of the asset shown').toHaveTextContent(ASSET.currency);

            await ASSET_CHANGE.make();
            await windowNames([21]);
            expect(screen.getByTestId('tx-form-cash-currency'), 'nothing moves while it asks').toHaveTextContent(ASSET.currency);
            await answerWindow('cancel');

            await ASSET_CHANGE.shows.old();
            expect(screen.getByTestId('tx-form-cash-currency')).toHaveTextContent(ASSET.currency);
            await closesWithoutAsking(onClose);
        });

        it('Confirm on an empty cash: the cash cell shows the new asset’s currency', async () => {
            await reopenedBuy([savedDraft(21)], {cash: null});

            await ASSET_CHANGE.make();
            await windowNames([21]);
            await answerWindow('confirm');

            await waitFor(() => expect(screen.getByTestId('tx-form-cash-currency')).toHaveTextContent(ASSET_2.currency));
        });

        it('a broker created from the form: the window, with the creation closed; Confirm takes the new broker', async () => {
            const {onPushDraft} = await reopenedBuy([savedDraft(21)]);
            await fireEvent.click(brokerTrigger());
            await fireEvent.click(await screen.findByTestId('search-select-create-new'));
            await waitFor(() => expect(created.broker?.isOpen, 'premise: the creation is open').toBe(true));
            mergeBrokers([{...BROKER_NEW, user_role: 'OWNER'}] as never);

            (created.broker!.oncreated as (d: {id: number}) => void)({id: BROKER_NEW.id});

            await windowNames([21]);
            await waitFor(() => expect(created.broker?.isOpen, 'the creation is closed').toBe(false));
            await answerWindow('confirm');
            await showsBroker(BROKER_NEW.name);
            await waitFor(() => expect(rowKeys()).toEqual([]));
            expect(await applied(onPushDraft)).toMatchObject({broker_id: BROKER_NEW.id});
        });

        it('a broker created from the form, Cancel: the broker of before, the charge kept, nothing to discard', async () => {
            const {onClose} = await reopenedBuy([savedDraft(21)]);
            mergeBrokers([{...BROKER_NEW, user_role: 'OWNER'}] as never);

            (created.broker!.oncreated as (d: {id: number}) => void)({id: BROKER_NEW.id});

            await windowNames([21]);
            await answerWindow('cancel');
            await showsBroker(BROKER.name);
            expect(rowKeys()).toEqual(['saved-21']);
            await closesWithoutAsking(onClose);
        });

        it('an asset created from the form: the window, with the creation closed; Confirm takes the new asset', async () => {
            const {onPushDraft} = await reopenedBuy([savedDraft(21)]);
            await fireEvent.click(assetTrigger());
            await fireEvent.click(await screen.findByTestId('tx-form-asset-create-new'));
            await waitFor(() => expect(created.asset?.open, 'premise: the creation is open').toBe(true));
            mergeAssets([{...ASSET_NEW, quote_base_quantity: 1, active: true}] as never);

            (created.asset!.oncreated as (id: number) => void)(ASSET_NEW.id);

            await windowNames([21]);
            await waitFor(() => expect(created.asset?.open, 'the creation is closed').toBe(false));
            await answerWindow('confirm');
            await showsAsset(ASSET_NEW.display_name);
            await waitFor(() => expect(rowKeys()).toEqual([]));
            expect(await applied(onPushDraft)).toMatchObject({asset_id: ASSET_NEW.id});
        });

        it('an asset created from the form, Cancel: the asset of before, the charge kept, nothing to discard', async () => {
            const {onClose} = await reopenedBuy([savedDraft(21)]);
            mergeAssets([{...ASSET_NEW, quote_base_quantity: 1, active: true}] as never);

            (created.asset!.oncreated as (id: number) => void)(ASSET_NEW.id);

            await windowNames([21]);
            await answerWindow('cancel');
            await showsAsset(ASSET.display_name);
            expect(rowKeys()).toEqual(['saved-21']);
            await closesWithoutAsking(onClose);
        });
    });

    // ---------------------------------------------------------------------------------------------------------
    //  Cell 2, the same opening: the saved charge picked here, then the change
    // ---------------------------------------------------------------------------------------------------------

    describe('cell 2, same opening: a saved charge picked here', () => {
        it('asset: the window names it; Confirm takes it out, Apply has no draft for it', async () => {
            const {onPushDraft} = await buyWithPicked([21]);

            await ASSET_CHANGE.make();
            await windowNames([21]);
            expect(rowKeys(), 'still there while it asks').toEqual(['saved-21']);
            await answerWindow('confirm');

            await ASSET_CHANGE.shows.next();
            await waitFor(() => expect(rowKeys()).toEqual([]));
            const payload = await applied(onPushDraft);
            expect(payload).toMatchObject({asset_id: ASSET_2.id});
            expect(draftsOf(payload).filter((draft) => draft.id === 21)).toEqual([]);
        });

        it('asset, Cancel: the section, the payload and the select keep the old value', async () => {
            const {onPushDraft} = await buyWithPicked([21]);

            await ASSET_CHANGE.make();
            await windowNames([21]);
            await answerWindow('cancel');

            await ASSET_CHANGE.shows.old();
            expect(rowKeys()).toEqual(['saved-21']);
            const payload = await applied(onPushDraft);
            expect(payload).toMatchObject({asset_id: ASSET.id});
            expect(draftsOf(payload)).toEqual([expect.objectContaining({id: 21, linkNew: true, state: 'linked'})]);
        });

        it('one handed and one picked: both are named, Confirm takes both out', async () => {
            answer({withoutParent: [freeFee(22)]});
            const {onPushDraft} = await reopenedBuy([savedDraft(21)]);
            await fireEvent.click(await screen.findByTestId('tx-form-charges-link-existing'));
            await pickIn(22);
            await addPicked();
            await waitFor(() => expect(rowKeys()).toEqual(['saved-21', 'saved-22']));

            await BROKER_CHANGE.make();
            await windowNames([21, 22]);
            await answerWindow('confirm');

            await waitFor(() => expect(rowKeys()).toEqual([]));
            expect(draftsOf(await applied(onPushDraft))).toEqual([]);
        });

        it('picked, unlinked again, then the asset changed: nothing is linked any more, no window', async () => {
            const {onPushDraft} = await buyWithPicked([21]);
            await fireEvent.click(screen.getByTestId('tx-form-charge-unlink-saved-21'));
            await waitFor(() => expect(rowKeys()).toEqual([]));

            await ASSET_CHANGE.make();

            await ASSET_CHANGE.shows.next();
            noWindow();
            expect(await applied(onPushDraft)).toMatchObject({asset_id: ASSET_2.id});
        });
    });

    // ---------------------------------------------------------------------------------------------------------
    //  No window
    // ---------------------------------------------------------------------------------------------------------

    describe('no window', () => {
        for (const [what, make, shows] of [
            ['asset', () => choose(assetTrigger, ASSET.id), ASSET_CHANGE.shows.old],
            ['broker', () => choose(brokerTrigger, BROKER.id), BROKER_CHANGE.shows.old],
            ['type', () => choose(typeTrigger, 'BUY'), TYPE_CHANGE.shows.old],
        ] as const) {
            it(`the same ${what} chosen again: nothing asked, the saved charge stays, nothing to discard`, async () => {
                const {onClose} = await reopenedBuy([savedDraft(21)]);

                await make();

                await shows();
                noWindow();
                expect(rowKeys()).toEqual(['saved-21']);
                await closesWithoutAsking(onClose);
            });
        }

        it('a type that takes an asset (SELL): the asset stays, nothing asked, the saved charge stays', async () => {
            const {onPushDraft} = await reopenedBuy([savedDraft(21)]);

            await choose(typeTrigger, 'SELL');

            await showsType('SELL');
            noWindow();
            const payload = await applied(onPushDraft);
            expect(payload).toMatchObject({type: 'SELL', asset_id: ASSET.id});
            expect(draftsOf(payload)).toEqual([expect.objectContaining({id: 21, linkNew: true, state: 'linked'})]);
        });

        for (const change of CHANGES) {
            it(`cell 1, only new charges of the Bulk, ${change.what}: the change is made at once, the charges stay`, async () => {
                const {onPushDraft} = await reopenedBuy([opDraft('n-fee'), opDraft('n-fee2')]);

                await change.make();

                await change.shows.next();
                noWindow();
                expect(rowKeys()).toEqual(['op-n-fee', 'op-n-fee2']);
                const payload = await applied(onPushDraft);
                expect(payload).toMatchObject(change.payload.next);
                expect(draftsOf(payload).map((draft) => [draft.key, draft.state])).toEqual([
                    ['op-n-fee', 'linked'],
                    ['op-n-fee2', 'linked'],
                ]);
            });
        }

        it('cell 1, a charge written in this opening (new-N): the asset changes at once, the row stays', async () => {
            await reopenedBuy([]);
            await fireEvent.click(screen.getByTestId('tx-form-charges-add-FEE'));
            await waitFor(() => expect(rowKeys()).toHaveLength(1));
            const [key] = rowKeys();
            expect(key).toMatch(/^new-/);

            await ASSET_CHANGE.make();

            await ASSET_CHANGE.shows.next();
            noWindow();
            expect(rowKeys()).toEqual([key]);
        });

        // Synthetic: a parent with a really saved charge is saved itself, so its broker and asset are locked, and the Bulk
        // marks every saved charge of a NEW parent `linkNew`. The form is handed one without it here.
        it('a saved charge really saved under this parent (no linkNew): no window, as today', async () => {
            const {onPushDraft} = await reopenedBuy([savedDraft(21, {linkNew: undefined})]);

            await ASSET_CHANGE.make();

            await ASSET_CHANGE.shows.next();
            noWindow();
            const payload = await applied(onPushDraft);
            expect(draftsOf(payload).map((draft) => [draft.id, draft.state])).toEqual([[21, 'linked']]);
        });

        for (const change of [ASSET_CHANGE, BROKER_CHANGE]) {
            it(`cell 4, a new charge under a NEW parent of the Bulk (_newParent), ${change.what}: no window, the link stays`, async () => {
                const row = txRow({date: '2024-05-17'});
                const {onPushDraft} = bulkNewRow(newFee({_newParent: {key: 'op-n-buy', ref: 'row 4', row}}));
                await formSettled();
                await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'ready'));

                await change.make();

                await change.shows.next();
                noWindow();
                expect(parentBox()).toHaveAttribute('data-state', 'ready');
                const payload = await applied(onPushDraft);
                expect(payload).toMatchObject(change.payload.next);
                expect(payload).not.toHaveProperty('_parent_unlink');
            });
        }

        it('a new charge with no parent: the asset changes at once', async () => {
            const {onPushDraft} = bulkNewRow(newFee());
            await formSettled();
            await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'empty'));

            await ASSET_CHANGE.make();

            await ASSET_CHANGE.shows.next();
            noWindow();
            expect(await applied(onPushDraft)).toMatchObject({asset_id: ASSET_2.id});
        });

        it('a new charge already unlinked here from its saved parent: the asset changes at once, the unlink stays', async () => {
            const {onPushDraft} = await feeUnderSavedParent();
            await fireEvent.click(screen.getByTestId('tx-form-parent-unlink'));
            await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'unlinked'));

            await ASSET_CHANGE.make();

            await ASSET_CHANGE.shows.next();
            noWindow();
            expect(await applied(onPushDraft)).toMatchObject({asset_id: ASSET_2.id, _parent_unlink: true});
        });

        it('a parent picked, then undone: the asset changes at once', async () => {
            const {onPushDraft} = await feeWithPickedParent();
            await fireEvent.click(screen.getByTestId('tx-form-parent-link-undo'));
            await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'empty'));

            await ASSET_CHANGE.make();

            await ASSET_CHANGE.shows.next();
            noWindow();
            expect(await applied(onPushDraft)).not.toHaveProperty('_parent_link');
        });

        it('a FEE under a saved parent turned into a TAX: the asset stays, so does the link', async () => {
            const {onPushDraft} = await feeUnderSavedParent();

            await choose(typeTrigger, 'TAX');

            await showsType('TAX');
            noWindow();
            expect(parentBox()).toHaveAttribute('data-state', 'ready');
            const payload = await applied(onPushDraft);
            expect(payload).toMatchObject({type: 'TAX', asset_id: ASSET.id});
            expect(payload).not.toHaveProperty('_parent_unlink');
        });
    });

    // ---------------------------------------------------------------------------------------------------------
    //  Cell 3: a new charge, its saved parent
    // ---------------------------------------------------------------------------------------------------------

    describe('cell 3: a new charge and its saved parent', () => {
        for (const change of [ASSET_CHANGE, BROKER_CHANGE]) {
            it(`picked here, ${change.what}: the window names the parent; Confirm drops the pick (no _parent_link)`, async () => {
                const {onPushDraft} = await feeWithPickedParent();

                await change.make();
                await windowNames([10]);
                expect(parentBox(), 'not dropped before the answer').toHaveAttribute('data-state', 'pending');
                await answerWindow('confirm');

                await change.shows.next();
                await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'empty'));
                expect(screen.getByTestId('tx-form-parent-link'), 'another parent can be picked').toBeInTheDocument();
                const payload = await applied(onPushDraft);
                expect(payload).toMatchObject(change.payload.next);
                expect(payload).not.toHaveProperty('_parent_link');
                expect(payload, 'there was no link to undo').not.toHaveProperty('_parent_unlink');
            });

            it(`picked here, ${change.what}, Cancel: the pick and the value are kept`, async () => {
                const {onPushDraft} = await feeWithPickedParent();

                await change.make();
                await windowNames([10]);
                await answerWindow('cancel');

                await change.shows.old();
                expect(parentBox()).toHaveAttribute('data-state', 'pending');
                expect(await applied(onPushDraft)).toMatchObject({...change.payload.old, _parent_link: 10});
            });

            it(`handed by the Bulk, ${change.what}: the window names the parent; Confirm unlinks it (_parent_unlink)`, async () => {
                const {onPushDraft} = await feeUnderSavedParent();

                await change.make();
                await windowNames([10]);
                expect(parentBox(), 'not unlinked before the answer').toHaveAttribute('data-state', 'ready');
                await answerWindow('confirm');

                await change.shows.next();
                await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'unlinked'));
                const payload = await applied(onPushDraft);
                expect(payload).toMatchObject({...change.payload.next, _parent_unlink: true});
                expect(payload).not.toHaveProperty('_parent_link');
            });

            it(`handed by the Bulk, ${change.what}, Cancel: the link and the value are kept, nothing to discard`, async () => {
                const first = await feeUnderSavedParent();
                await change.make();
                await windowNames([10]);
                await answerWindow('cancel');
                await change.shows.old();
                expect(parentBox()).toHaveAttribute('data-state', 'ready');
                await closesWithoutAsking(first.onClose);
                cleanup();

                const second = await feeUnderSavedParent();
                await change.make();
                await windowNames([10]);
                await answerWindow('cancel');
                const payload = await applied(second.onPushDraft);
                expect(payload).toMatchObject(change.payload.old);
                expect(payload).not.toHaveProperty('_parent_unlink');
            });
        }

        it('handed, the type changed to one with no asset: the window names the parent; Cancel keeps the FEE, its asset and its link', async () => {
            const {onPushDraft} = await feeUnderSavedParent();

            await TYPE_CHANGE.make();
            await windowNames([10]);
            await answerWindow('cancel');

            await showsType('FEE');
            await showsAsset(ASSET.display_name);
            expect(parentBox()).toHaveAttribute('data-state', 'ready');
            const payload = await applied(onPushDraft);
            expect(payload).toMatchObject({type: 'FEE', asset_id: ASSET.id});
            expect(payload).not.toHaveProperty('_parent_unlink');
        });

        // Lane, after the code (no red): Confirm on a change of type that hides «Linked to» still sends the unlink.
        it('handed, the type changed to one with no asset, Confirm: Apply still carries _parent_unlink, though the form is no longer a charge', async () => {
            const {onPushDraft} = await feeUnderSavedParent();

            await TYPE_CHANGE.make();
            await windowNames([10]);
            await answerWindow('confirm');

            await showsType('DEPOSIT');
            const payload = await applied(onPushDraft);
            expect(payload).toMatchObject({type: 'DEPOSIT', _parent_unlink: true});
            expect(payload).not.toHaveProperty('_parent_link');
        });

        for (const button of ['confirm', 'cancel'] as const) {
            it(`handed and still loading: the window names it by its id; ${button}, then the parent arrives`, async () => {
                let land!: (rows: Row[]) => void;
                const pending = new Promise<Row[]>((resolve) => {
                    land = resolve;
                });
                answer({byId: () => pending});
                const {onPushDraft} = bulkNewRow(newFee({parent_transaction_id: 10}));
                await formSettled();
                await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', 'loading'));

                await ASSET_CHANGE.make();
                await windowNames([10]);
                expect(parentBox(), 'premise: still loading').toHaveAttribute('data-state', 'loading');
                await answerWindow(button);
                land([savedBuy(10)]);

                await waitFor(() => expect(parentBox()).toHaveAttribute('data-state', button === 'confirm' ? 'unlinked' : 'ready'));
                await (button === 'confirm' ? ASSET_CHANGE.shows.next() : ASSET_CHANGE.shows.old());
                const payload = await applied(onPushDraft);
                expect(payload.asset_id).toBe(button === 'confirm' ? ASSET_2.id : ASSET.id);
                expect(payload._parent_unlink ?? false).toBe(button === 'confirm');
            });
        }
    });

    // ---------------------------------------------------------------------------------------------------------
    //  The form has another confirmation («discard changes»): the two never mix
    // ---------------------------------------------------------------------------------------------------------

    it('the window refused, then the form cancelled with other changes: the discard question, on its own, and it works', async () => {
        const {onClose} = await reopenedBuy([savedDraft(21)]);
        await ASSET_CHANGE.make();
        await windowNames([21]);
        await answerWindow('cancel');
        await fireEvent.input(screen.getByTestId('tx-form-description'), {target: {value: 'a note of mine'}});

        // Refused: the form stays, and the window can still be answered afterwards.
        await fireEvent.click(screen.getByTestId('tx-form-cancel'));
        await screen.findByTestId('confirm-modal-cancel');
        expect(unlinkWindow(), 'the discard question is not the window').toBeNull();
        expect(onClose).not.toHaveBeenCalled();
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());
        expect(rowKeys(), 'the discard question unlinks nothing').toEqual(['saved-21']);
        await ASSET_CHANGE.shows.old();

        await ASSET_CHANGE.make();
        await windowNames([21]);
        await answerWindow('confirm');
        await ASSET_CHANGE.shows.next();
        expect(onClose, 'the window’s Confirm discards nothing').not.toHaveBeenCalled();
        expect(screen.getByTestId('tx-form-description')).toHaveValue('a note of mine');

        await fireEvent.click(screen.getByTestId('tx-form-cancel'));
        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
