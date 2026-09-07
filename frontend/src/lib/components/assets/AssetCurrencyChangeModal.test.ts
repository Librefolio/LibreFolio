// @vitest-environment jsdom
/**
 * AssetCurrencyChangeModal — component test (Vitest + jsdom).
 *
 * This is the destructive-confirm modal that opens when a currency change is
 * blocked by existing market data. Its whole reason to exist is a fixed sequence
 * of side effects — wipe → patch → (conditionally) sync — plus the promise that
 * the modal stays open if the irreversible part fails, so the user can retry
 * rather than be left wondering. None of that is visible state; it is three API
 * calls in an order, and two callbacks. That is exactly what a component test can
 * pin down and an E2E cannot without seeding an asset with prices, events and a
 * linked transaction all at once.
 *
 * The dependencies are mocked at the module boundary:
 *   - `$lib/api` — the three zodios endpoints, so we assert the call *order* via
 *     `invocationCallOrder` and the fact that a failed step stops the chain.
 *   - `$lib/api/backupDownload` — the export buttons; we assert the (kind, format)
 *     pair handed to it, which is the button's only job.
 *   - `$lib/stores/app/toastStore.svelte` — asserted by **variant** (`success` /
 *     `error`), never by message, because the message is translated.
 *   - `$lib/utils/sync/syncToastHelpers` — returns a fixed `{variant, message}` so
 *     the success path is deterministic without reaching into its internals.
 *
 * NOT tested here: the exact toast wording (translated), the InfoBanner variant
 * (its component lives in `ui/`, off-limits, and the branch it renders is display
 * only — the behavioural consequence, "does sync run?", is asserted instead), and
 * anything positional.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';

vi.mock('$lib/api', () => ({
    zodiosApi: {
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

function blockerOf(over: Record<string, unknown> = {}) {
    return {assetId: 42, prices: 5, eventsManual: 2, eventsProvider: 1, linkedTx: 3, oldest: '2020-01-01', newest: '2024-01-01', from: 'USD', to: 'EUR', ...over};
}

function mount(props: Record<string, unknown> = {}) {
    const onconfirmed = vi.fn();
    const oncanceled = vi.fn();
    const utils = render(AssetCurrencyChangeModal, {open: true, blocker: blockerOf(), patchPayload: {id: 42, currency: 'EUR'}, providerAssigned: true, onconfirmed, oncanceled, ...props});
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
    patch.mockResolvedValue(undefined as never);
    sync.mockResolvedValue({results: [{status: 'ok'}]} as never);
    download.mockResolvedValue(undefined as never);
});

describe('AssetCurrencyChangeModal — conditional rendering', () => {
    it('renders nothing while closed', () => {
        mount({open: false});
        expect(screen.queryByTestId('currency-change-modal')).toBeNull();
    });

    it('renders nothing without a blocker', () => {
        mount({blocker: null});
        expect(screen.queryByTestId('currency-change-modal')).toBeNull();
    });

    it('shows a summary line and export buttons for each populated category', () => {
        mount();
        expect(screen.getByTestId('currency-change-summary-prices')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-summary-events')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-summary-linkedtx')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-export-prices-csv')).toBeInTheDocument();
        expect(screen.getByTestId('currency-change-export-events-json')).toBeInTheDocument();
    });

    it('omits the price rows when there are no prices', () => {
        mount({blocker: blockerOf({prices: 0, oldest: '', newest: ''})});
        expect(screen.queryByTestId('currency-change-summary-prices')).toBeNull();
        expect(screen.queryByTestId('currency-change-export-prices-csv')).toBeNull();
        // Events still there.
        expect(screen.getByTestId('currency-change-export-events-csv')).toBeInTheDocument();
    });

    it('omits the event export buttons when there are no events', () => {
        mount({blocker: blockerOf({eventsManual: 0, eventsProvider: 0})});
        expect(screen.queryByTestId('currency-change-summary-events')).toBeNull();
        expect(screen.queryByTestId('currency-change-export-events-csv')).toBeNull();
        expect(screen.getByTestId('currency-change-export-prices-csv')).toBeInTheDocument();
    });
});

describe('AssetCurrencyChangeModal — the confirm sequence', () => {
    it('runs wipe → patch → sync in that order, then closes and confirms', async () => {
        const {onconfirmed} = mount({providerAssigned: true});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(onconfirmed).toHaveBeenCalledTimes(1));
        expect(wipe).toHaveBeenCalledTimes(1);
        expect(patch).toHaveBeenCalledTimes(1);
        expect(sync).toHaveBeenCalledTimes(1);
        // The irreversible order is the contract: wipe before patch before sync.
        expect(wipe.mock.invocationCallOrder[0]).toBeLessThan(patch.mock.invocationCallOrder[0]);
        expect(patch.mock.invocationCallOrder[0]).toBeLessThan(sync.mock.invocationCallOrder[0]);
        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).toBeNull());
    });

    it('passes the blocker asset id to wipe and the payload to patch', async () => {
        mount({providerAssigned: true});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));
        await waitFor(() => expect(patch).toHaveBeenCalled());

        expect(wipe.mock.calls[0][1]).toEqual({params: {asset_id: 42}});
        expect(patch.mock.calls[0][0]).toEqual([{id: 42, currency: 'EUR'}]);
    });

    it('skips sync when no provider is assigned', async () => {
        const {onconfirmed} = mount({providerAssigned: false});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(onconfirmed).toHaveBeenCalled());
        expect(patch).toHaveBeenCalledTimes(1);
        expect(sync).not.toHaveBeenCalled();
    });

    it('skips sync when a provider is assigned but there were no prices', async () => {
        const {onconfirmed} = mount({providerAssigned: true, blocker: blockerOf({prices: 0, oldest: ''})});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(onconfirmed).toHaveBeenCalled());
        expect(sync).not.toHaveBeenCalled();
    });

    it('stops the chain and keeps the modal open when wipe fails', async () => {
        wipe.mockRejectedValueOnce(new Error('boom'));
        const {onconfirmed} = mount();
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(toasts.error).toHaveBeenCalled());
        expect(patch).not.toHaveBeenCalled();
        expect(onconfirmed).not.toHaveBeenCalled();
        // The destructive step failed — the modal is still there to retry.
        expect(screen.getByTestId('currency-change-modal')).toBeInTheDocument();
    });

    it('keeps the modal open when the patch fails after a successful wipe', async () => {
        patch.mockRejectedValueOnce(new Error('boom'));
        const {onconfirmed} = mount();
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(toasts.error).toHaveBeenCalled());
        expect(wipe).toHaveBeenCalledTimes(1);
        expect(onconfirmed).not.toHaveBeenCalled();
        expect(screen.getByTestId('currency-change-modal')).toBeInTheDocument();
    });

    it('still closes and confirms when only the post-patch sync fails', async () => {
        sync.mockRejectedValueOnce(new Error('sync down'));
        const {onconfirmed} = mount({providerAssigned: true});
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        // The PATCH already went through, so the change stands: modal closes anyway.
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

describe('AssetCurrencyChangeModal — in-progress lock', () => {
    it('disables both buttons and shows the progress step while the wipe is pending', async () => {
        const gate = deferred();
        wipe.mockReturnValueOnce(gate.promise as never);
        const {oncanceled} = mount();

        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        // Frozen mid-wipe: the progress indicator is up and both controls are locked.
        await waitFor(() => expect(screen.getByTestId('currency-change-progress-step')).toBeInTheDocument());
        expect(screen.getByTestId('currency-change-confirm')).toBeDisabled();
        expect(screen.getByTestId('currency-change-cancel')).toBeDisabled();

        // A cancel click in this state must be ignored.
        await fireEvent.click(screen.getByTestId('currency-change-cancel'));
        expect(oncanceled).not.toHaveBeenCalled();

        gate.resolve(undefined);
        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).toBeNull());
    });
});

describe('AssetCurrencyChangeModal — exports and cancel', () => {
    it('exports each price/event format with the right (kind, format)', async () => {
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

    it('cancels via the footer button', async () => {
        const {oncanceled} = mount();
        await fireEvent.click(screen.getByTestId('currency-change-cancel'));
        expect(oncanceled).toHaveBeenCalledTimes(1);
        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).toBeNull());
    });

    it('cancels via the header X', async () => {
        const {oncanceled} = mount();
        await fireEvent.click(screen.getByTestId('currency-change-close-x'));
        expect(oncanceled).toHaveBeenCalledTimes(1);
    });
});
