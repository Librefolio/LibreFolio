// @vitest-environment jsdom
/**
 * AssetModal — the currency change (component test, Vitest + jsdom). Workstream X, lot X5-3 (N68).
 *
 * Changing an asset's currency is no longer blocked (developer decision 19/10/2026). `PATCH /assets/patch` always succeeds
 * on a currency change and, in the same call, deletes the asset's prices and every non-SPLIT event, and disconnects the
 * transactions linked to a deleted event; it keeps the SPLIT events and the transactions linked to them. So the edit
 * modal's `saveEdit` no longer waits for the PATCH to refuse with a token (`CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA`, parsed
 * by the deleted `currencyBlocker.ts`) or for a 409: it asks the server's dry run first.
 *
 * Contract (the order is the point).
 *   - The form's currency differs from the asset's current one (`editData.currency`) → BEFORE any PATCH, `saveEdit` calls
 *     `loadCurrencyChangeImpact` (`currencyImpact.ts`: ONE `market_data_summary_api_v1_assets__asset_id__market_data_summary_get`
 *     with `{params: {asset_id}}`).
 *       · `hasSomethingToLose(impact)` → the confirm modal (`currency-change-modal`) opens with the impact and the patch
 *         payload, and NO PATCH is sent; its cancel sends nothing and leaves the form as it was; its confirm sends ONE PATCH
 *         (the modal's own test pins the rest) and the asset modal reports `onupdated`.
 *       · nothing to lose (splits kept alone are no loss) → the PATCH goes straight out, no modal, then `onupdated`.
 *       · the dry run throws → the save fails with the inline form error (`asset-modal-form-error`, which is also
 *         `data-form-error`), NO PATCH, no modal: this dry run is a gate, unlike the provider dialog's.
 *   - The currency is unchanged → no dry run at all (a plain save).
 *   - The old branches are gone: a PATCH that fails with a 409 carrying `detail.results[]` is an ordinary failure now (the
 *     inline error), and never opens the modal.
 *
 * How. A dedicated file because the currency picker needs the currency store's list, which `AssetModal.test.ts` leaves
 * empty and caches module-wide. The API is a Proxy of spies (as in `AssetModal.test.ts`); the currency store is replaced by
 * a two-currency list. The currency is chosen through the real `CurrencySearchSelect` (the combobox of
 * `asset-modal-currency-group`, then `search-select-option-<CODE>`). No text is read.
 *
 * Expected. Red before the cure: the save PATCHes first and only a token opens the modal, so «something to lose» sends a
 * PATCH and no modal; the dry run is never asked; a throwing dry run is not looked for. Green before and after (guards):
 * an unchanged currency asks nothing.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

vi.mock('$lib/api', async () => {
    const {schemas} = await import('$lib/api/generated');
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
    return {zodiosApi, schemas, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});
vi.mock('$lib/utils/providerHelpers', () => ({
    ensureAssetProvidersCached: vi.fn(() => Promise.resolve()),
    getAssetProviderName: vi.fn((c: string) => c),
    getAssetProviderIconUrl: vi.fn(() => null),
    isParametricProvider: vi.fn(() => false),
}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));
vi.mock('$lib/stores/reference/assetStore', () => ({mergeAssets: vi.fn(), invalidateAfterMutation: vi.fn()}));
vi.mock('$lib/stores/reference/currencyStore', async () => {
    const {writable} = await import('svelte/store');
    const currencies = [
        {code: 'USD', name: 'US dollar', symbol: '$', flag_emoji: '🇺🇸', country_codes: ['US'], country_names: ['United States']},
        {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
    ];
    return {
        ensureCurrenciesLoaded: vi.fn(() => Promise.resolve()),
        getAllCurrencies: vi.fn(() => currencies),
        getCurrencyInfo: vi.fn((code: string) => currencies.find((entry) => entry.code === code)),
        isCurrenciesLoaded: vi.fn(() => true),
        suggestCurrency: vi.fn(async () => ({canonical: true, suggestion: null, candidates: []})),
        currencyStoreVersion: writable(0),
    };
});

import AssetModal from './AssetModal.svelte';
import {zodiosApi} from '$lib/api';

const ASSET_ID = 7;

const patchFn = () => vi.mocked(zodiosApi.patch_assets_bulk_api_v1_assets_patch as never) as ReturnType<typeof vi.fn>;
const summaryFn = () => vi.mocked(zodiosApi.market_data_summary_api_v1_assets__asset_id__market_data_summary_get as never) as ReturnType<typeof vi.fn>;
const wipeFn = () => vi.mocked(zodiosApi.wipe_market_data_api_v1_assets__asset_id__market_data_wipe_post as never) as ReturnType<typeof vi.fn>;
const syncFn = () => vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post as never) as ReturnType<typeof vi.fn>;
const saveBtn = () => screen.getByTestId('asset-modal-save') as HTMLButtonElement;

/** The server's dry run, every field a case does not name at zero. */
function summary(over: Record<string, unknown> = {}) {
    return {prices: 0, events_manual: 0, events_provider: 0, splits_kept: 0, linked_tx: 0, oldest: null, newest: null, dry_run: true, ...over};
}

const SOMETHING_TO_LOSE = summary({prices: 12, events_manual: 2, events_provider: 1, splits_kept: 1, linked_tx: 3, oldest: '2020-01-02', newest: '2024-05-06'});

/** Open the edit modal on an asset that is in USD, with the form ready. */
async function mountEdit() {
    const onupdated = vi.fn();
    render(AssetModal, {
        open: true,
        editMode: true,
        editData: {id: ASSET_ID, display_name: 'Currency asset', currency: 'USD', asset_type: 'STOCK', quote_base_quantity: 1, active: true},
        onupdated,
    });
    await waitFor(() => expect(screen.queryByTestId('asset-modal-form')).not.toBeNull());
    await waitFor(() => expect(saveBtn()).toBeEnabled());
    return {onupdated};
}

/** Pick a currency in the form through the real combobox, and wait until the form says it. */
async function chooseCurrency(code: string) {
    const group = screen.getByTestId('asset-modal-currency-group');
    await fireEvent.click(within(group).getByRole('combobox'));
    await fireEvent.click(await screen.findByTestId(`search-select-option-${code}`));
    await waitFor(() => expect(within(group).getByRole('combobox')).toHaveTextContent(code));
}

beforeEach(async () => {
    await setupI18n();
    vi.clearAllMocks();
    (zodiosApi.list_assets_api_v1_assets_query_get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (zodiosApi.list_providers_api_v1_assets_provider_get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    patchFn().mockResolvedValue({results: [{success: true, asset_id: ASSET_ID}], success_count: 1} as never);
    summaryFn().mockResolvedValue(summary() as never);
    vi.stubGlobal(
        'fetch',
        vi.fn<typeof fetch>(async () => new Response(null, {status: 503})),
    );
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('AssetModal — a currency change with something to lose', () => {
    it('asks the dry run, opens the confirm modal and sends NO patch', async () => {
        summaryFn().mockResolvedValue(SOMETHING_TO_LOSE as never);
        const {onupdated} = await mountEdit();
        await chooseCurrency('EUR');

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).not.toBeNull());
        expect(summaryFn()).toHaveBeenCalledTimes(1);
        expect(summaryFn()).toHaveBeenCalledWith({params: {asset_id: ASSET_ID}});
        expect(patchFn(), 'the question comes before any write').not.toHaveBeenCalled();
        expect(wipeFn()).not.toHaveBeenCalled();
        expect(onupdated).not.toHaveBeenCalled();
        // The modal got the impact: the lines of what is lost, and the splits that stay.
        expect(screen.getByTestId('currency-change-summary-prices')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-summary-events')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-summary-linkedtx')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-summary-splits')).toBeInTheDocument();
    });

    it('cancel sends nothing at all and leaves the edit form open as it was', async () => {
        summaryFn().mockResolvedValue(SOMETHING_TO_LOSE as never);
        const {onupdated} = await mountEdit();
        await chooseCurrency('EUR');
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).not.toBeNull());

        await fireEvent.click(screen.getByTestId('currency-change-cancel'));

        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).toBeNull());
        expect(patchFn()).not.toHaveBeenCalled();
        expect(wipeFn()).not.toHaveBeenCalled();
        expect(syncFn()).not.toHaveBeenCalled();
        expect(onupdated).not.toHaveBeenCalled();
        expect(screen.getByTestId('asset-modal-form'), 'the draft is still there').toBeInTheDocument();
        expect(within(screen.getByTestId('asset-modal-currency-group')).getByRole('combobox'), 'with the currency the user chose').toHaveTextContent('EUR');
    });

    it('confirm sends ONE patch with the edited currency and the asset id, never the wipe, then reports onupdated', async () => {
        summaryFn().mockResolvedValue(SOMETHING_TO_LOSE as never);
        const {onupdated} = await mountEdit();
        await chooseCurrency('EUR');
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).not.toBeNull());

        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(onupdated).toHaveBeenCalledTimes(1));
        expect(patchFn()).toHaveBeenCalledTimes(1);
        expect(patchFn()).toHaveBeenCalledWith([expect.objectContaining({asset_id: ASSET_ID, currency: 'EUR'})]);
        expect(wipeFn(), 'the patch deletes by itself').not.toHaveBeenCalled();
        expect(summaryFn(), 'the dry run is not asked again by the confirm').toHaveBeenCalledTimes(1);
        // No provider on this asset: nothing to resync.
        expect(syncFn()).not.toHaveBeenCalled();
    });

    it('splits kept alone are no loss: the patch goes straight out and no modal opens', async () => {
        summaryFn().mockResolvedValue(summary({splits_kept: 2}) as never);
        const {onupdated} = await mountEdit();
        await chooseCurrency('EUR');

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(onupdated).toHaveBeenCalledTimes(1));
        expect(screen.queryByTestId('currency-change-modal')).toBeNull();
        expect(summaryFn(), 'the question was asked: kept splits are what it answered').toHaveBeenCalledTimes(1);
        expect(patchFn()).toHaveBeenCalledTimes(1);
        expect(patchFn()).toHaveBeenCalledWith([expect.objectContaining({asset_id: ASSET_ID, currency: 'EUR'})]);
    });
});

describe('AssetModal — a currency change with nothing to lose', () => {
    it('asks the dry run first, then PATCHes directly with the new currency: no modal, then onupdated', async () => {
        summaryFn().mockResolvedValue(summary() as never);
        const {onupdated} = await mountEdit();
        await chooseCurrency('EUR');

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(onupdated).toHaveBeenCalledTimes(1));
        expect(screen.queryByTestId('currency-change-modal')).toBeNull();
        expect(summaryFn()).toHaveBeenCalledTimes(1);
        expect(summaryFn()).toHaveBeenCalledWith({params: {asset_id: ASSET_ID}});
        expect(patchFn()).toHaveBeenCalledTimes(1);
        expect(patchFn()).toHaveBeenCalledWith([expect.objectContaining({asset_id: ASSET_ID, currency: 'EUR'})]);
        expect(summaryFn().mock.invocationCallOrder[0], 'the question precedes the write').toBeLessThan(patchFn().mock.invocationCallOrder[0]);
        expect(wipeFn()).not.toHaveBeenCalled();
    });
});

describe('AssetModal — the dry run is a gate', () => {
    it('a dry run that fails fails the save with the inline form error: no patch, no modal, no onupdated', async () => {
        summaryFn().mockRejectedValue(Object.assign(new Error('Network Error'), {response: {status: 500}}));
        const {onupdated} = await mountEdit();
        await chooseCurrency('EUR');

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(screen.queryByTestId('asset-modal-form-error')).not.toBeNull());
        expect(summaryFn()).toHaveBeenCalledTimes(1);
        expect(patchFn(), 'the save must not go on blind').not.toHaveBeenCalled();
        expect(screen.queryByTestId('currency-change-modal')).toBeNull();
        expect(onupdated).not.toHaveBeenCalled();
        expect(screen.getByTestId('asset-modal-form'), 'the draft stays for a retry').toBeInTheDocument();
        await waitFor(() => expect(saveBtn(), 'and the save is available again').toBeEnabled());
    });

    it('a retry after the failed dry run asks again and, answered, goes on', async () => {
        summaryFn().mockRejectedValueOnce(new Error('Network Error'));
        summaryFn().mockResolvedValueOnce(summary() as never);
        const {onupdated} = await mountEdit();
        await chooseCurrency('EUR');
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(screen.queryByTestId('asset-modal-form-error')).not.toBeNull());
        await waitFor(() => expect(saveBtn()).toBeEnabled());

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(onupdated).toHaveBeenCalledTimes(1));
        expect(summaryFn()).toHaveBeenCalledTimes(2);
        expect(patchFn()).toHaveBeenCalledTimes(1);
    });
});

describe('AssetModal — an unchanged currency asks nothing', () => {
    it('a save that leaves the currency alone sends the patch and never the dry run', async () => {
        const {onupdated} = await mountEdit();
        await fireEvent.input(screen.getByTestId('asset-modal-display-name'), {target: {value: 'Renamed asset'}});

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(onupdated).toHaveBeenCalledTimes(1));
        expect(summaryFn()).not.toHaveBeenCalled();
        expect(patchFn()).toHaveBeenCalledTimes(1);
        expect(patchFn()).toHaveBeenCalledWith([expect.objectContaining({asset_id: ASSET_ID, display_name: 'Renamed asset', currency: 'USD'})]);
        expect(screen.queryByTestId('currency-change-modal')).toBeNull();
    });

    it('choosing another currency and then the original again is no change: no dry run', async () => {
        const {onupdated} = await mountEdit();
        await chooseCurrency('EUR');
        await chooseCurrency('USD');

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(onupdated).toHaveBeenCalledTimes(1));
        expect(summaryFn()).not.toHaveBeenCalled();
        expect(patchFn()).toHaveBeenCalledWith([expect.objectContaining({asset_id: ASSET_ID, currency: 'USD'})]);
    });
});

describe('AssetModal — the blocker token and the 409 are gone', () => {
    it('a patch that fails with the old 409 shape is an ordinary failure: the inline error, never the confirm modal', async () => {
        summaryFn().mockResolvedValue(summary() as never);
        patchFn().mockRejectedValue(
            Object.assign(new Error('Request failed with status code 409'), {
                response: {
                    status: 409,
                    data: {detail: {results: [{asset_id: ASSET_ID, success: false, message: 'CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|prices=3|events_manual=1|events_provider=0|linked_tx=2|oldest=2020-01-01|newest=2024-01-01|from=USD|to=EUR'}]}},
                },
            }),
        );
        const {onupdated} = await mountEdit();
        await chooseCurrency('EUR');

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(screen.queryByTestId('asset-modal-form-error')).not.toBeNull());
        expect(screen.queryByTestId('currency-change-modal')).toBeNull();
        expect(onupdated).not.toHaveBeenCalled();
    });

    it('a per-item failure carrying the old token opens no modal either: the message is just a failure', async () => {
        summaryFn().mockResolvedValue(summary() as never);
        patchFn().mockResolvedValue({
            results: [{success: false, asset_id: ASSET_ID, message: 'CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|prices=3|events_manual=1|events_provider=0|linked_tx=2|oldest=2020-01-01|newest=2024-01-01|from=USD|to=EUR'}],
            success_count: 0,
        } as never);
        const {onupdated} = await mountEdit();
        await chooseCurrency('EUR');

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(screen.queryByTestId('asset-modal-form-error')).not.toBeNull());
        expect(screen.queryByTestId('currency-change-modal')).toBeNull();
        expect(onupdated).not.toHaveBeenCalled();
    });
});
