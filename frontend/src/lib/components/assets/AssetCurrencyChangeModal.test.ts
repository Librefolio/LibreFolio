// @vitest-environment jsdom
/**
 * AssetCurrencyChangeModal — component test (Vitest + jsdom). Lot X5-3 (N68).
 *
 * The confirm dialog the asset modal opens when the user changes an asset's currency and the server's dry run
 * (`currencyImpact.ts`, `GET /assets/{id}/market-data/summary`) says something would be lost: its prices, its events
 * that are not SPLITs, and the link of the transactions that pointed to a deleted event. Since N68 (developer decision
 * 19/10/2026) the change is no longer blocked: `PATCH /assets/patch` always succeeds and does the deleting itself, in the
 * same call, keeping the SPLIT events and the transactions linked to them. So the modal is no longer the middle of a chain
 * «wipe → patch → sync»: its confirm is ONE `patch_assets_bulk_api_v1_assets_patch([patchPayload])` — `wipe_market_data_…`
 * is never called — followed, when the asset has a provider and had prices, by the price sync from the oldest price to today.
 * What is visible state is the progress element (`currency-change-progress-step`, whose `data-step` is `patch` and then
 * `sync`: there is no `wipe` step any more) and the summary lines; the rest is an API call and two callbacks, which is what a
 * component test pins down.
 *
 * Contract (props). `{open (bindable), impact: CurrencyChangeImpact | null, patchPayload, providerAssigned, zIndex?,
 * onconfirmed?, oncanceled?}` — `blocker` is renamed `impact`, its fields are camelCase:
 * `{assetId, from, to, prices, eventsManual, eventsProvider, splitsKept, linkedTx, oldest, newest}`.
 * A summary line is hidden when its count is 0; the new line `currency-change-summary-splits` (the SPLITs that stay) is
 * shown only when `splitsKept > 0`.
 *
 * The dependencies are mocked at the module boundary:
 *   - `$lib/api` — the endpoints. `wipe_market_data_…` is present only to be proven never called.
 *   - `$lib/api/backupDownload` — the export buttons; we assert the (kind, format) pair handed to it.
 *   - `$lib/stores/app/toastStore.svelte` — asserted by **variant** (`success` / `error`), never by message.
 *   - `$lib/utils/sync/syncToastHelpers` — returns a fixed `{variant, message}`.
 *
 * Expected. Red before the cure: the component still takes `blocker` (so `impact` renders nothing), wipes before it
 * patches, publishes a `wipe` step, and has no splits line. Green before and after (guards): the sync-failure cases, the
 * cancel paths, the exports, the interpolation of the counts.
 *
 * The X-R48 cases of the old file (the wipe's 409 `MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST` worded through
 * `wipeRefusalMessage`) are gone with the wipe: nothing refuses any more, a SPLIT is kept. A failure of the patch keeps
 * the generic error toast, carrying the error's own words.
 *
 * NOT tested here: the exact toast wording (translated), the InfoBanner variant (its component lives in `ui/`; the
 * behavioural consequence, «does sync run?», is asserted instead), and anything positional.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {addMessages, dictionary} from 'svelte-i18n';
import {get} from 'svelte/store';

vi.mock('$lib/api', () => ({
    zodiosApi: {
        // N68: the interface no longer calls the wipe; the spy is here to prove it.
        wipe_market_data_api_v1_assets__asset_id__market_data_wipe_post: vi.fn(),
        patch_assets_bulk_api_v1_assets_patch: vi.fn(),
        sync_prices_bulk_api_v1_assets_prices_sync_post: vi.fn(),
    },
}));
vi.mock('$lib/api/backupDownload', () => ({downloadAssetBackup: vi.fn()}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));
vi.mock('$lib/utils/sync/syncToastHelpers', () => ({
    buildAssetSyncToast: vi.fn(() => ({variant: 'success', message: 'synced'})),
}));

import AssetCurrencyChangeModal from './AssetCurrencyChangeModal.svelte';
import {zodiosApi} from '$lib/api';
import {downloadAssetBackup} from '$lib/api/backupDownload';
import {toasts} from '$lib/stores/app/toastStore.svelte';

const wipe = vi.mocked(zodiosApi.wipe_market_data_api_v1_assets__asset_id__market_data_wipe_post);
const patch = vi.mocked(zodiosApi.patch_assets_bulk_api_v1_assets_patch);
const sync = vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post);
const download = vi.mocked(downloadAssetBackup);
const patchSuccessResponse = {
    results: [{asset_id: 42, success: true, message: 'Synthetic patch accepted', updated_fields: null}],
    success_count: 1,
    errors: [],
};

/** The dry run's answer as the modal receives it. Every count distinct, so a swapped pair reads otherwise. */
function impactOf(over: Record<string, unknown> = {}) {
    return {assetId: 42, from: 'USD', to: 'EUR', prices: 5, eventsManual: 2, eventsProvider: 1, splitsKept: 1, linkedTx: 3, oldest: '2020-01-01', newest: '2024-01-01', ...over};
}

function mount(props: Record<string, unknown> = {}) {
    const onconfirmed = vi.fn();
    const oncanceled = vi.fn();
    const utils = render(AssetCurrencyChangeModal, {
        open: true,
        impact: impactOf(),
        patchPayload: {asset_id: 42, currency: 'EUR'},
        providerAssigned: true,
        onconfirmed,
        oncanceled,
        ...props,
    });
    return {onconfirmed, oncanceled, ...utils};
}

function deferred<T = unknown>() {
    let resolve!: (v: T) => void;
    let reject!: (e: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

beforeEach(async () => {
    await setupI18n();
    vi.clearAllMocks();
    wipe.mockResolvedValue(undefined as never);
    patch.mockResolvedValue(patchSuccessResponse as never);
    sync.mockResolvedValue({results: [{status: 'ok'}]} as never);
    download.mockResolvedValue(undefined as never);
});

describe('AssetCurrencyChangeModal — conditional rendering', () => {
    it('renders nothing while closed', () => {
        mount({open: false});
        expect(screen.queryByTestId('currency-change-modal')).toBeNull();
    });

    it('renders nothing without an impact', () => {
        mount({impact: null});
        expect(screen.queryByTestId('currency-change-modal')).toBeNull();
    });

    it('shows a summary line and export buttons for each populated category, and the splits that stay', () => {
        mount();
        expect(screen.getByTestId('currency-change-modal')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-summary-prices')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-summary-events')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-summary-linkedtx')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-summary-splits')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-export-prices-csv')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-export-events-json')).toBeInTheDocument();
    });

    it('interpolates the price and linked-transaction counts through the real {n} contract', () => {
        // Synthetic messages exercise the real ICU formatter, not translated prose.
        // Distinct counts catch accidental reuse of the price count for linked TX.
        const originalDictionary = structuredClone(get(dictionary));
        try {
            addMessages('en', {
                assetDetail: {
                    currencyChange: {
                        summaryPrices: 'prices={n};oldest={oldest};newest={newest}',
                        summaryLinkedTx: 'linked={n}',
                    },
                },
            });
            mount({impact: impactOf({prices: 17, linkedTx: 4, oldest: '2021-02-03', newest: '2024-05-06'})});
            expect(screen.getByTestId('currency-change-modal')).toBeVisible();
            expect(screen.getByTestId('currency-change-summary-prices')).toHaveTextContent('prices=17;oldest=2021-02-03;newest=2024-05-06');
            expect(screen.getByTestId('currency-change-summary-linkedtx')).toHaveTextContent('linked=4');
        } finally {
            dictionary.set(originalDictionary);
        }
    });

    it('omits the price rows when there are no prices', () => {
        mount({impact: impactOf({prices: 0, oldest: '', newest: ''})});
        expect(screen.getByTestId('currency-change-modal')).toBeInTheDocument();
        expect(screen.queryByTestId('currency-change-summary-prices')).toBeNull();
        expect(screen.queryByTestId('currency-change-export-prices-csv')).toBeNull();
        // Events still there.
        expect(screen.getByTestId('currency-change-export-events-csv')).toBeInTheDocument();
    });

    it('omits the event rows and export buttons when there are no events', () => {
        mount({impact: impactOf({eventsManual: 0, eventsProvider: 0})});
        expect(screen.getByTestId('currency-change-modal')).toBeInTheDocument();
        expect(screen.queryByTestId('currency-change-summary-events')).toBeNull();
        expect(screen.queryByTestId('currency-change-export-events-csv')).toBeNull();
        expect(screen.getByTestId('currency-change-export-prices-csv')).toBeInTheDocument();
    });

    it('omits the linked-transactions line when none is linked', () => {
        mount({impact: impactOf({linkedTx: 0})});
        expect(screen.getByTestId('currency-change-modal')).toBeInTheDocument();
        expect(screen.queryByTestId('currency-change-summary-linkedtx')).toBeNull();
        expect(screen.getByTestId('currency-change-summary-prices')).toBeInTheDocument();
    });

    it('shows the events line when only the provider’s events are there, and when only the manual ones are', () => {
        const first = mount({impact: impactOf({eventsManual: 0, eventsProvider: 4})});
        expect(screen.getByTestId('currency-change-summary-events')).toBeInTheDocument();
        first.unmount();
        mount({impact: impactOf({eventsManual: 4, eventsProvider: 0})});
        expect(screen.getByTestId('currency-change-summary-events')).toBeInTheDocument();
    });

    it('omits the splits line when no split is kept — it is information, shown only when there is something to say', () => {
        mount({impact: impactOf({splitsKept: 0})});
        expect(screen.getByTestId('currency-change-modal')).toBeInTheDocument();
        expect(screen.queryByTestId('currency-change-summary-splits')).toBeNull();
    });

    it('shows the splits line on its own: kept splits do not depend on any other line', () => {
        mount({impact: impactOf({prices: 0, eventsManual: 0, eventsProvider: 0, linkedTx: 0, oldest: '', newest: '', splitsKept: 2})});
        expect(screen.getByTestId('currency-change-summary-splits')).toBeInTheDocument();
        expect(screen.queryByTestId('currency-change-summary-prices')).toBeNull();
        expect(screen.queryByTestId('currency-change-summary-events')).toBeNull();
        expect(screen.queryByTestId('currency-change-summary-linkedtx')).toBeNull();
    });
});

describe('AssetCurrencyChangeModal — the confirm sequence', () => {
    it('sends ONE patch, then the sync, then closes and confirms — and never the wipe', async () => {
        const {onconfirmed} = mount({providerAssigned: true});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(onconfirmed).toHaveBeenCalledTimes(1));
        expect(patch).toHaveBeenCalledTimes(1);
        expect(sync).toHaveBeenCalledTimes(1);
        expect(wipe, 'the patch deletes by itself: the interface no longer wipes').not.toHaveBeenCalled();
        expect(patch.mock.invocationCallOrder[0]).toBeLessThan(sync.mock.invocationCallOrder[0]);
        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).toBeNull());
    });

    it('hands the payload to the patch as a one-item list, untouched', async () => {
        mount({providerAssigned: true});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));
        await waitFor(() => expect(patch).toHaveBeenCalled());

        expect(patch.mock.calls[0][0]).toEqual([{asset_id: 42, currency: 'EUR'}]);
    });

    it('syncs from the oldest price to today, for the impact’s asset, exactly as before', async () => {
        const {onconfirmed} = mount({providerAssigned: true});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));
        await waitFor(() => expect(onconfirmed).toHaveBeenCalled());

        expect(sync).toHaveBeenCalledWith([{asset_id: 42, date_range: {start: '2020-01-01', end: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/)}}]);
    });

    it('skips sync when no provider is assigned', async () => {
        const {onconfirmed} = mount({providerAssigned: false});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(onconfirmed).toHaveBeenCalled());
        expect(patch).toHaveBeenCalledTimes(1);
        expect(sync).not.toHaveBeenCalled();
        expect(wipe).not.toHaveBeenCalled();
    });

    it('skips sync when a provider is assigned but there were no prices (nothing to resume from)', async () => {
        const {onconfirmed} = mount({providerAssigned: true, impact: impactOf({prices: 0, oldest: '', newest: ''})});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(onconfirmed).toHaveBeenCalled());
        expect(patch).toHaveBeenCalledTimes(1);
        expect(sync).not.toHaveBeenCalled();
    });

    it('keeps the modal open and stops there when the patch rejects: no sync, no confirm, an error toast', async () => {
        patch.mockRejectedValueOnce(new Error('boom'));
        const {onconfirmed} = mount();
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(toasts.error).toHaveBeenCalled());
        expect(toasts.error, 'one error toast').toHaveBeenCalledTimes(1);
        expect(vi.mocked(toasts.error).mock.calls[0][0], 'the generic sentence carries the error’s own words').toContain('boom');
        expect(sync).not.toHaveBeenCalled();
        expect(wipe).not.toHaveBeenCalled();
        expect(onconfirmed).not.toHaveBeenCalled();
        // The destructive step failed — the modal is still there to retry.
        expect(screen.getByTestId('currency-change-modal')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-confirm'), 'the buttons are unlocked for a retry').toBeEnabled();
    });

    it('keeps the modal open when the per-item patch result reports success false', async () => {
        patch.mockResolvedValueOnce({
            results: [{asset_id: 42, success: false, message: 'Asset patch rejected by API', updated_fields: null}],
            success_count: 0,
            errors: [],
        } as never);
        const {onconfirmed} = mount({providerAssigned: true});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(toasts.error).toHaveBeenCalled());
        expect(sync).not.toHaveBeenCalled();
        expect(onconfirmed).not.toHaveBeenCalled();
        expect(screen.getByTestId('currency-change-modal')).toBeInTheDocument();
    });

    it('a failed patch can be retried: the second confirm sends the patch again and succeeds', async () => {
        patch.mockRejectedValueOnce(new Error('boom'));
        const {onconfirmed} = mount({providerAssigned: false});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));
        await waitFor(() => expect(toasts.error).toHaveBeenCalled());

        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(onconfirmed).toHaveBeenCalledTimes(1));
        expect(patch).toHaveBeenCalledTimes(2);
    });

    it('still closes and confirms when only the post-patch sync fails (the change stands)', async () => {
        sync.mockRejectedValueOnce(new Error('sync down'));
        const {onconfirmed} = mount({providerAssigned: true});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(onconfirmed).toHaveBeenCalledTimes(1));
        expect(toasts.error).toHaveBeenCalled();
        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).toBeNull());
    });

    it('reports an error but still closes when sync returns no result', async () => {
        sync.mockResolvedValueOnce({results: []} as never);
        const {onconfirmed} = mount({providerAssigned: true});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(onconfirmed).toHaveBeenCalled());
        expect(toasts.error).toHaveBeenCalled();
    });
});

describe('AssetCurrencyChangeModal — in-progress lock and the steps', () => {
    it('publishes data-step="patch" while the patch is pending and locks both buttons; a cancel click is ignored', async () => {
        const gate = deferred();
        patch.mockReturnValueOnce(gate.promise as never);
        const {oncanceled} = mount({providerAssigned: false});

        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(screen.getByTestId('currency-change-progress-step')).toHaveAttribute('data-step', 'patch'));
        expect(screen.getByTestId('currency-change-confirm')).toBeDisabled();
        expect(screen.getByTestId('currency-change-cancel')).toBeDisabled();
        expect(screen.getByTestId('currency-change-close-x')).toBeDisabled();

        await fireEvent.click(screen.getByTestId('currency-change-cancel'));
        expect(oncanceled).not.toHaveBeenCalled();

        gate.resolve(patchSuccessResponse);
        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).toBeNull());
    });

    it('moves to data-step="sync" once the patch is in, and there is never a wipe step', async () => {
        const patchGate = deferred();
        const syncGate = deferred();
        patch.mockReturnValueOnce(patchGate.promise as never);
        sync.mockReturnValueOnce(syncGate.promise as never);
        const {onconfirmed} = mount({providerAssigned: true});

        await fireEvent.click(screen.getByTestId('currency-change-confirm'));
        await waitFor(() => expect(screen.getByTestId('currency-change-progress-step')).toHaveAttribute('data-step', 'patch'));
        expect(sync, 'no sync before the patch answers').not.toHaveBeenCalled();

        patchGate.resolve(patchSuccessResponse);
        await waitFor(() => expect(screen.getByTestId('currency-change-progress-step')).toHaveAttribute('data-step', 'sync'));
        expect(screen.getByTestId('currency-change-confirm'), 'still locked while the sync runs').toBeDisabled();
        expect(onconfirmed, 'not confirmed before the sync ends').not.toHaveBeenCalled();

        syncGate.resolve({results: [{status: 'ok'}]});
        await waitFor(() => expect(onconfirmed).toHaveBeenCalledTimes(1));
        expect(wipe).not.toHaveBeenCalled();
    });

    it('shows no progress element before the confirm', () => {
        mount();
        expect(screen.queryByTestId('currency-change-progress-step')).toBeNull();
    });
});

describe('AssetCurrencyChangeModal — exports and cancel', () => {
    it('exports each price/event format with the right (kind, format), for the impact’s asset', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('currency-change-export-prices-csv'));
        await fireEvent.click(screen.getByTestId('currency-change-export-events-json'));

        expect(download).toHaveBeenNthCalledWith(1, 42, 'prices', 'csv');
        expect(download).toHaveBeenNthCalledWith(2, 42, 'events', 'json');
    });

    it('raises an error toast when an export fails', async () => {
        download.mockRejectedValueOnce(new Error('nope'));
        mount();
        await fireEvent.click(screen.getByTestId('currency-change-export-prices-csv'));
        await waitFor(() => expect(toasts.error).toHaveBeenCalled());
    });

    it('cancels via the footer button: no patch, no sync, no wipe', async () => {
        const {oncanceled} = mount();
        await fireEvent.click(screen.getByTestId('currency-change-cancel'));
        expect(oncanceled).toHaveBeenCalledTimes(1);
        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).toBeNull());
        expect(patch).not.toHaveBeenCalled();
        expect(sync).not.toHaveBeenCalled();
        expect(wipe).not.toHaveBeenCalled();
    });

    it('cancels via the header X: nothing is sent', async () => {
        const {oncanceled} = mount();
        await fireEvent.click(screen.getByTestId('currency-change-close-x'));
        expect(oncanceled).toHaveBeenCalledTimes(1);
        expect(patch).not.toHaveBeenCalled();
        expect(wipe).not.toHaveBeenCalled();
    });
});
