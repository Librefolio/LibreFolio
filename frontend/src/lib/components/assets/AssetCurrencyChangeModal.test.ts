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
 *   - `./currencyChangeErrors` (X-R48) — `wipeRefusalMessage`, the sentence for a
 *     refused wipe, answers `null` (an error it does not know) unless a test says
 *     otherwise; the test that needs the refusal makes it answer a marker string,
 *     so that toast is checked against the module's answer, never a translation.
 *     The handle comes from `vi.hoisted` and nothing here imports the module: it
 *     does not exist before the cure, Vitest 4 accepts a mock whose id does not
 *     resolve yet (it keeps the raw id), and this file still loads. Once the module
 *     exists the factory spreads its real exports and replaces that one.
 *
 * X-R48. The wipe refuses, 409 MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST, before
 * writing anything, when a split of the asset has linked adjustments without a
 * purchase cost. The confirm `catch` toasts
 * `wipeRefusalMessage(err, tr, formatDay) ?? <the generic «failed: …» of today>`:
 * on that refusal the user reads the module's sentence in their language — not the
 * server's English — and the chain stops there: no patch, no sync, no
 * `onconfirmed`, the modal open. Red before the cure, both cases of the refusal:
 * the toast is «failed: <the server's English>» and the module is never asked. The
 * guard is green before and after: a failure the module does not know (it answers
 * null) keeps the generic error toast, carrying the error's own words.
 *
 * NOT tested here: the exact toast wording (translated), the InfoBanner variant
 * (its component lives in `ui/`, off-limits, and the branch it renders is display
 * only — the behavioural consequence, "does sync run?", is asserted instead), and
 * anything positional.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {_, addMessages, dictionary} from 'svelte-i18n';
import {get} from 'svelte/store';

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

/** The translator a refusal reader is handed: svelte-i18n's `$t`, as `currencyChangeErrors` types it. */
type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

// X-R48: the module that words a refused wipe. Nothing imports it here — it does not exist before the cure — so the
// handle is hoisted, and the factory runs only when the component imports the module, spreading its real exports.
const {refusalMessage} = vi.hoisted(() => ({
    refusalMessage: vi.fn<(err: unknown, t: Translate, dateLabel?: (iso: string) => string) => string | null>(() => null),
}));
vi.mock('./currencyChangeErrors', async (importOriginal) => ({...(await importOriginal<Record<string, unknown>>()), wipeRefusalMessage: refusalMessage}));

import AssetCurrencyChangeModal from './AssetCurrencyChangeModal.svelte';
import {zodiosApi} from '$lib/api';
import {downloadAssetBackup} from '$lib/api/backupDownload';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {formatDay} from '$lib/utils/core/formatAxisDate';

const wipe = vi.mocked(zodiosApi.wipe_market_data_api_v1_assets__asset_id__market_data_wipe_post);
const patch = vi.mocked(zodiosApi.patch_assets_bulk_api_v1_assets_patch);
const sync = vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post);
const download = vi.mocked(downloadAssetBackup);
const patchSuccessResponse = {
    results: [{asset_id: 42, success: true, message: 'Synthetic patch accepted', updated_fields: null}],
    success_count: 1,
    errors: [],
};

/** What the mocked `wipeRefusalMessage` answers for the refusal: a marker, so the toast is checked against the module's answer. */
const REFUSAL_SENTENCE = '⟨wipeRefusalMessage: the refused wipe, worded⟩';

/** The wipe's X-R48 refusal as a zodios (axios) call throws it: 409, a structured detail, the server's sentence in English. */
function splitAdjustmentsRefusal() {
    return Object.assign(new Error('Request failed with status code 409'), {
        response: {
            status: 409,
            data: {
                detail: {
                    error_code: 'MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST',
                    message: 'Market data not wiped: 1 split has 2 linked adjustments without a purchase cost',
                    params: {splits: [{event_id: 12, date: '2026-02-10', transaction_ids: [5], hidden_transactions_count: 1}]},
                },
            },
        },
    });
}

function blockerOf(over: Record<string, unknown> = {}) {
    return {assetId: 42, prices: 5, eventsManual: 2, eventsProvider: 1, linkedTx: 3, oldest: '2020-01-01', newest: '2024-01-01', from: 'USD', to: 'EUR', ...over};
}

function mount(props: Record<string, unknown> = {}) {
    const onconfirmed = vi.fn();
    const oncanceled = vi.fn();
    const utils = render(AssetCurrencyChangeModal, {
        open: true,
        blocker: blockerOf(),
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
    // X-R48: the module's answer for an error it does not know is null, and the generic sentence stays.
    refusalMessage.mockReset();
    refusalMessage.mockReturnValue(null);
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
            mount({blocker: blockerOf({prices: 17, linkedTx: 4, oldest: '2021-02-03', newest: '2024-05-06'})});
            expect(screen.getByTestId('currency-change-modal')).toBeVisible();
            expect(screen.getByTestId('currency-change-summary-prices')).toHaveTextContent('prices=17;oldest=2021-02-03;newest=2024-05-06');
            expect(screen.getByTestId('currency-change-summary-linkedtx')).toHaveTextContent('linked=4');
        } finally {
            dictionary.set(originalDictionary);
        }
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
        expect(patch.mock.calls[0][0]).toEqual([{asset_id: 42, currency: 'EUR'}]);
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

    it('X-R48: a wipe refused for a split with costless adjustments toasts the sentence the module writes, once, and stops the chain', async () => {
        const refused = splitAdjustmentsRefusal();
        wipe.mockRejectedValueOnce(refused);
        refusalMessage.mockImplementation((err) => (err === refused ? REFUSAL_SENTENCE : null));
        const {onconfirmed} = mount();
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(toasts.error).toHaveBeenCalled());
        expect(toasts.error, 'one error toast').toHaveBeenCalledTimes(1);
        expect(toasts.error, "its text is the module's sentence for that error, not «failed: <the server's English>»").toHaveBeenCalledWith(REFUSAL_SENTENCE);
        expect(toasts.success, 'nothing was wiped').not.toHaveBeenCalled();
        expect(patch).not.toHaveBeenCalled();
        expect(sync).not.toHaveBeenCalled();
        expect(onconfirmed).not.toHaveBeenCalled();
        expect(screen.getByTestId('currency-change-modal')).toBeInTheDocument();
    });

    it('X-R48: the module is asked about the very error the wipe threw, with the interface translator and its day label', async () => {
        const refused = splitAdjustmentsRefusal();
        wipe.mockRejectedValueOnce(refused);
        mount();
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));
        await waitFor(() => expect(toasts.error).toHaveBeenCalled());

        expect(refusalMessage, 'asked once, when the chain failed').toHaveBeenCalledTimes(1);
        const [err, translate, dateLabel] = refusalMessage.mock.calls[0];
        expect(err, 'the error as the wipe rejected with it').toBe(refused);
        const key = 'assetDetail.currencyChange.failed';
        expect(get(_)(key), `premise: the catalogue has ${key}`).not.toBe(key);
        expect(translate(key), 'the translator of the interface: a key reads as the catalogue writes it').toBe(get(_)(key));
        expect(dateLabel, 'a day label is handed over').toBeTypeOf('function');
        expect(dateLabel?.('2026-02-10'), 'the day written as the interface writes one in a detail line (formatDay)').toBe(formatDay('2026-02-10'));
    });

    it('X-R48 guard: a failure the module does not know (it answers null) keeps the generic error toast, with the error’s own words', async () => {
        wipe.mockRejectedValueOnce(new Error('boom'));
        refusalMessage.mockReturnValue(null);
        const {onconfirmed} = mount();
        await fireEvent.click(screen.getByTestId('currency-change-confirm'));

        await waitFor(() => expect(toasts.error).toHaveBeenCalled());
        expect(toasts.error, 'one error toast').toHaveBeenCalledTimes(1);
        // 'boom' is this test's own text, not a translation: the generic path still carries the error's words.
        expect(vi.mocked(toasts.error).mock.calls[0][0], 'the generic sentence, not null and not empty').toContain('boom');
        expect(toasts.success).not.toHaveBeenCalled();
        expect(patch).not.toHaveBeenCalled();
        expect(sync).not.toHaveBeenCalled();
        expect(onconfirmed).not.toHaveBeenCalled();
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
