// @vitest-environment jsdom
/**
 * AssetModal — component test (Vitest + jsdom).
 *
 * The create/edit dialog for an asset. It is a large orchestrator: form fields
 * bind to local `$state`, and on save it calls the bulk zodios endpoints
 * (`create_assets_bulk`, `patch_assets_bulk`, `assign_providers_bulk`,
 * `remove_providers_bulk`, `sync_prices_bulk`). Two things make it worth a
 * component test rather than E2E:
 *
 *   - the payload it POSTs is the contract, and it is never visible on screen;
 *   - every mode (create, edit, prefill) and every guard (validation, duplicate
 *     name, discard-confirm) is a prop or a local transition, not a page to set
 *     up. Reaching them through Playwright means driving the assets page, a
 *     provider search and a table per case.
 *
 * What these tests assert is therefore: what the parent receives (the callback
 * payloads and `oncreated`/`onupdated`/`onclose`), and the `data-testid` /
 * `data-*` state the component publishes. Never translated text, never CSS
 * classes.
 *
 * What is deliberately NOT tested here:
 *   - the identifiers `DataTable` rows, the sector/geographic `DistributionEditor`
 *     and the provider `ProviderAssignmentSection` internals: each is its own
 *     component (table/ and ui/ lanes, or a sibling with its own test). We assert
 *     that AssetModal feeds them the right props and reads their callbacks, not
 *     how they render.
 *   - positioning. jsdom returns zeros for every `getBoundingClientRect`, so a
 *     layout assertion would only measure the absence of a layout engine.
 *   - the online-search flow (`AssetSearchAutocomplete`) — covered by its own
 *     component test. Two exceptions, at the end of the file: AssetModal hands
 *     both of its searches the form (`reportContext`), and the report link of a
 *     search that found nothing must name what the form says (P20); and the quote
 *     base (Z-32 d) is decided by a pick from that search and by the provider's
 *     answer, so the last block picks results from a streamed search and answers
 *     the provider's probe.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import * as navigation from '$app/navigation';

// --- Mocks --------------------------------------------------------------
// zodiosApi has dozens of methods; a Proxy lazily mints (and caches) a spy per
// property, so `vi.mocked(zodiosApi.foo)` retrieves the same fn to program.
vi.mock('$lib/api', async () => {
    // Keep schema exports available to real child components while every API
    // request remains a local spy; importing generated schemas performs no I/O.
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

import AssetModal from './AssetModal.svelte';
import type {ComponentProps} from 'svelte';
import {get} from 'svelte/store';
import {zodiosApi} from '$lib/api';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {getAssetProviderName, isParametricProvider} from '$lib/utils/providerHelpers';
import {DEFAULT_INSTANCE_CONFIG, instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {GITHUB_NEW_ISSUE_URL} from './assetSearchReport';

/** The creation callbacks, typed from the component: the contract under test (O-20). */
type OnCreated = NonNullable<ComponentProps<typeof AssetModal>['oncreated']>;
type OnSynced = NonNullable<ComponentProps<typeof AssetModal>['onsynced']>;

// --- Helpers ------------------------------------------------------------
const createFn = () => vi.mocked(zodiosApi.create_assets_bulk_api_v1_assets_post as never) as ReturnType<typeof vi.fn>;
const patchFn = () => vi.mocked(zodiosApi.patch_assets_bulk_api_v1_assets_patch as never) as ReturnType<typeof vi.fn>;
const listFn = () => vi.mocked(zodiosApi.list_assets_api_v1_assets_query_get as never) as ReturnType<typeof vi.fn>;
const removeProviderFn = () => vi.mocked(zodiosApi.remove_providers_bulk_api_v1_assets_provider_delete as never) as ReturnType<typeof vi.fn>;

/** Fill an input via its bind:value path. */
async function fill(testId: string, value: string) {
    await fireEvent.input(screen.getByTestId(testId), {target: {value}});
}

const nameInput = () => screen.getByTestId('asset-modal-display-name') as HTMLInputElement;
const saveBtn = () => screen.getByTestId('asset-modal-save') as HTMLButtonElement;

async function waitForForm() {
    await waitFor(() => expect(screen.queryByTestId('asset-modal-form')).not.toBeNull());
}

beforeEach(async () => {
    await setupI18n();
    vi.clearAllMocks();
    // Default: no other assets → duplicate-name check finds nothing.
    listFn().mockResolvedValue([] as never);
    vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue([]);
    vi.mocked(zodiosApi.list_currencies_api_v1_utilities_currencies_get).mockResolvedValue({items: [], language: 'en'});
    // A fake fetch for the embedded AssetSearchAutocomplete (never streamed here).
    vi.stubGlobal(
        'fetch',
        vi.fn<typeof fetch>(async () => new Response(null, {status: 503})),
    );
});

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

// =========================================================================
describe('AssetModal — rendering & mode', () => {
    it('renders nothing when open=false', () => {
        render(AssetModal, {open: false, oncreated: vi.fn()});
        expect(screen.queryByTestId('asset-modal-form')).toBeNull();
    });

    it('renders the create form with an empty, invalid name (save disabled)', async () => {
        render(AssetModal, {open: true, editMode: false, oncreated: vi.fn()});
        await waitForForm();
        expect(nameInput().value).toBe('');
        expect(saveBtn()).toBeDisabled();
    });

    it('prefills every field from editData in edit mode', async () => {
        render(AssetModal, {
            open: true,
            editMode: true,
            editData: {id: 7, display_name: 'Tesla Inc.', currency: 'USD', asset_type: 'STOCK', quote_base_quantity: 1, active: true},
            onupdated: vi.fn(),
        });
        await waitForForm();
        expect(nameInput().value).toBe('Tesla Inc.');
        // A populated name makes the form valid → save enabled.
        await waitFor(() => expect(saveBtn()).toBeEnabled());
    });

    it('keeps the configuration anchor explanatory in tour preview while removing save and every mutation path', async () => {
        const oncreated = vi.fn();
        const onupdated = vi.fn();
        const onclose = vi.fn();
        render(AssetModal, {
            open: true,
            tourPreview: true,
            initialNoProvider: true,
            oncreated,
            onupdated,
            onclose,
        });
        await waitForForm();

        const anchor = screen.getByTestId('asset-modal-currency-group');
        expect(anchor).toBeVisible();
        const providerHeader = screen.getByTestId('asset-modal-provider-header');
        expect(providerHeader).toHaveAttribute('role', 'button');
        expect(providerHeader).toHaveAttribute('tabindex', '0');
        await waitFor(() => expect(providerHeader).toHaveAttribute('data-expanded', 'true'));

        const noProvider = screen.getByTestId('asset-modal-no-provider');
        expect(noProvider).toBeEnabled();
        expect(noProvider).not.toBeChecked();

        const providerSelect = await screen.findByTestId('provider-code-select-button');
        expect(providerSelect).toBeEnabled();
        expect(screen.getByTestId('provider-identifier')).toBeEnabled();
        expect(screen.queryByTestId('asset-modal-save')).toBeNull();

        // Make the draft valid so the missing save path, rather than validation,
        // is what prevents a write.
        await fill('asset-modal-display-name', 'Owned tour preview asset');
        expect(nameInput()).toHaveValue('Owned tour preview asset');
        expect(screen.queryByTestId('asset-modal-save')).toBeNull();
        expect(createFn()).not.toHaveBeenCalled();
        expect(patchFn()).not.toHaveBeenCalled();
        expect(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).not.toHaveBeenCalled();
        expect(removeProviderFn()).not.toHaveBeenCalled();
        expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).not.toHaveBeenCalled();
        expect(oncreated).not.toHaveBeenCalled();
        expect(onupdated).not.toHaveBeenCalled();
        expect(onclose).not.toHaveBeenCalled();
    });
});

// =========================================================================
describe('AssetModal — validation (isValid)', () => {
    it('enables save once a name is typed and disables it again when cleared', async () => {
        render(AssetModal, {open: true, oncreated: vi.fn()});
        await waitForForm();
        expect(saveBtn()).toBeDisabled();

        await fill('asset-modal-display-name', 'Apple Inc.');
        await waitFor(() => expect(saveBtn()).toBeEnabled());

        await fill('asset-modal-display-name', '   ');
        await waitFor(() => expect(saveBtn()).toBeDisabled());
    });

    it('rejects a quote base of zero and shows the min error', async () => {
        render(AssetModal, {open: true, oncreated: vi.fn()});
        await waitForForm();
        await fill('asset-modal-display-name', 'Apple Inc.');
        await fill('asset-modal-quote-base-quantity', '0');
        await waitFor(() => expect(screen.queryByTestId('asset-modal-quote-base-quantity-error')).not.toBeNull());
        expect(saveBtn()).toBeDisabled();
    });

    it('rejects a fractional quote base (must be an integer)', async () => {
        render(AssetModal, {open: true, oncreated: vi.fn()});
        await waitForForm();
        await fill('asset-modal-display-name', 'Apple Inc.');
        await fill('asset-modal-quote-base-quantity', '2.5');
        await waitFor(() => expect(screen.queryByTestId('asset-modal-quote-base-quantity-error')).not.toBeNull());
        expect(saveBtn()).toBeDisabled();

        // An integer clears the error and re-enables save.
        await fill('asset-modal-quote-base-quantity', '2');
        await waitFor(() => expect(screen.queryByTestId('asset-modal-quote-base-quantity-error')).toBeNull());
        expect(saveBtn()).toBeEnabled();
    });

    it('truncates the decimals a user typed when the quote-base field loses focus', async () => {
        render(AssetModal, {open: true, oncreated: vi.fn()});
        await waitForForm();
        const qbq = screen.getByTestId('asset-modal-quote-base-quantity') as HTMLInputElement;
        await fill('asset-modal-quote-base-quantity', '2.7');
        // While editing, 2.7 is invalid (non-integer) — the error is shown.
        await waitFor(() => expect(screen.queryByTestId('asset-modal-quote-base-quantity-error')).not.toBeNull());
        // On blur the value is truncated to the integer part, clearing the error.
        await fireEvent.blur(qbq);
        await waitFor(() => expect(qbq.value).toBe('2'));
        expect(screen.queryByTestId('asset-modal-quote-base-quantity-error')).toBeNull();
    });
});

// =========================================================================
describe('AssetModal — create submit', () => {
    it('POSTs the built payload, fires oncreated(assetId), and closes', async () => {
        createFn().mockResolvedValue({results: [{success: true, asset_id: 42}]} as never);
        const oncreated = vi.fn();
        render(AssetModal, {open: true, editMode: false, oncreated});
        await waitForForm();

        await fill('asset-modal-display-name', 'Apple Inc.');
        await waitFor(() => expect(saveBtn()).toBeEnabled());
        await fireEvent.click(saveBtn());

        // No provider: no price sync starts (O-20).
        await waitFor(() => expect(oncreated).toHaveBeenCalledWith(42, {syncing: false}));
        expect(createFn()).toHaveBeenCalledWith([
            expect.objectContaining({
                display_name: 'Apple Inc.',
                currency: 'EUR', // userSettings null → base_currency fallback
                asset_type: 'STOCK',
                quote_base_quantity: 1,
                active: true,
            }),
        ]);
        // The modal closed itself.
        await waitFor(() => expect(screen.queryByTestId('asset-modal-form')).toBeNull());
    });

    it('keeps the modal open and shows a form error when the backend reports failure', async () => {
        createFn().mockResolvedValue({results: [{success: false, message: 'boom'}]} as never);
        const oncreated = vi.fn();
        render(AssetModal, {open: true, editMode: false, oncreated});
        await waitForForm();

        await fill('asset-modal-display-name', 'Apple Inc.');
        await waitFor(() => expect(saveBtn()).toBeEnabled());
        await fireEvent.click(saveBtn());

        await waitFor(() => expect(screen.queryByTestId('asset-modal-form-error')).not.toBeNull());
        expect(oncreated).not.toHaveBeenCalled();
        // Still open.
        expect(screen.queryByTestId('asset-modal-form')).not.toBeNull();
    });

    it('maps a 409 conflict to the duplicate-name form error and stays open', async () => {
        // The bulk POST itself rejects with a 409 (name already taken).
        createFn().mockRejectedValue({response: {status: 409}} as never);
        const oncreated = vi.fn();
        render(AssetModal, {open: true, editMode: false, oncreated});
        await waitForForm();

        await fill('asset-modal-display-name', 'Apple Inc.');
        await waitFor(() => expect(saveBtn()).toBeEnabled());
        await fireEvent.click(saveBtn());

        await waitFor(() => expect(screen.queryByTestId('asset-modal-form-error')).not.toBeNull());
        expect(oncreated).not.toHaveBeenCalled();
        expect(screen.queryByTestId('asset-modal-form')).not.toBeNull();
    });

    it('carries the active flag into the payload after the toggle is switched off', async () => {
        createFn().mockResolvedValue({results: [{success: true, asset_id: 5}]} as never);
        const oncreated = vi.fn();
        render(AssetModal, {open: true, editMode: false, oncreated});
        await waitForForm();

        const toggle = screen.getByTestId('asset-active-toggle');
        expect(toggle).toHaveAttribute('aria-checked', 'true');
        await fireEvent.click(toggle);
        await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'));

        await fill('asset-modal-display-name', 'Dormant Co.');
        await waitFor(() => expect(saveBtn()).toBeEnabled());
        await fireEvent.click(saveBtn());

        await waitFor(() => expect(oncreated).toHaveBeenCalled());
        expect(createFn()).toHaveBeenCalledWith([expect.objectContaining({active: false})]);
    });
});

// =========================================================================
describe('AssetModal — opt-in creation success links', () => {
    type CreateResponse = Awaited<ReturnType<typeof zodiosApi.create_assets_bulk_api_v1_assets_post>>;
    type SyncResponse = Awaited<ReturnType<typeof zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post>>;

    const PROVIDER_CODE = 'fixture_price_source';
    const PROVIDER_IDENTIFIER = 'OWNED';
    const providerFixture: Awaited<ReturnType<typeof zodiosApi.list_providers_api_v1_assets_provider_get>> = [
        {
            code: PROVIDER_CODE,
            name: 'Owned price source',
            description: 'Synthetic provider metadata; no network implementation',
            kind: 'online_scraper',
            supports_search: false,
            params_schema: [],
            accepted_identifier_types: ['TICKER', 'ISIN'],
        },
    ];

    afterEach(() => {
        // Discard any unconsumed one-shot response after an early assertion
        // failure; the next test must never inherit another asset's result.
        vi.mocked(zodiosApi.create_assets_bulk_api_v1_assets_post).mockReset();
        vi.mocked(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).mockReset();
        vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).mockReset();
        vi.mocked(zodiosApi.patch_assets_bulk_api_v1_assets_patch).mockReset();
        vi.mocked(zodiosApi.remove_providers_bulk_api_v1_assets_provider_delete).mockReset();
    });

    function createdResponse(id: number, name: string): CreateResponse {
        return {results: [{asset_id: id, success: true, message: '[[created-response]]', display_name: name}], success_count: 1};
    }

    function toastMarkup(variant: 'success' | 'warning'): HTMLDivElement {
        const spy = vi.mocked(toasts[variant]);
        expect(spy).toHaveBeenCalledTimes(1);
        const call = spy.mock.calls.at(-1);
        if (!call) throw new Error(`No ${variant} toast was emitted`);
        const [message] = call;
        const content = document.createElement('div');
        content.innerHTML = message;
        return content;
    }

    function expectOnlySuccessToast() {
        expect(toasts.success).toHaveBeenCalledTimes(1);
        expect(toasts.warning).not.toHaveBeenCalled();
        expect(toasts.error).not.toHaveBeenCalled();
        expect(toasts.info).not.toHaveBeenCalled();
    }

    async function mountCreation(id: number, name: string, linkCreatedAsset?: boolean, onsynced?: OnSynced) {
        vi.mocked(zodiosApi.create_assets_bulk_api_v1_assets_post).mockResolvedValueOnce(createdResponse(id, name));
        const oncreated = vi.fn<OnCreated>();
        const goto = vi.spyOn(navigation, 'goto');
        const hrefBefore = window.location.href;
        render(AssetModal, {open: true, oncreated, ...(linkCreatedAsset === undefined ? {} : {linkCreatedAsset}), ...(onsynced ? {onsynced} : {})});
        await waitForForm();
        await fill('asset-modal-display-name', name);
        await waitFor(() => expect(nameInput()).toHaveValue(name));
        await waitFor(() => expect(saveBtn()).toBeEnabled());
        return {oncreated, goto, hrefBefore};
    }

    /**
     * `oncreated` received exactly `expected`: after a creation, the id and whether its one price sync started —
     * `[id, {syncing}]` (O-20); after a failed provider assignment, the id alone — `[id]`.
     */
    async function expectCreationClosed(oncreated: OnCreated, expected: Parameters<OnCreated>) {
        await waitFor(() => expect(oncreated).toHaveBeenCalledWith(...expected));
        await waitFor(() => expect(screen.queryByTestId('asset-modal-form')).toBeNull());
        expect(oncreated).toHaveBeenCalledTimes(1);
    }

    async function chooseProviderWithoutProbing() {
        // Fresh create forms start collapsed. Open that known state, then wait
        // for the owned provider option rather than guessing when metadata loaded.
        expect(screen.queryByTestId('provider-code-select-button')).toBeNull();
        await fireEvent.click(screen.getByTestId('asset-modal-provider-header'));
        await fireEvent.click(await screen.findByTestId('provider-code-select-button'));
        await fireEvent.click(await screen.findByTestId(`provider-option-${PROVIDER_CODE}`));
        await waitFor(() => expect(screen.queryByTestId(`provider-option-${PROVIDER_CODE}`)).toBeNull());
        await fill('provider-identifier', PROVIDER_IDENTIFIER);
        await waitFor(() => expect(screen.getByTestId('provider-identifier')).toHaveValue(PROVIDER_IDENTIFIER));
        await waitFor(() => expect(saveBtn()).toBeEnabled());
    }

    async function saveWithUntestedProvider() {
        await fireEvent.click(saveBtn());
        const confirm = await screen.findByTestId('confirm-modal-confirm');
        expect(confirm).toBeEnabled();
        // This is the existing deliberate "save without testing" path. Do not
        // run a provider probe merely to test creation feedback.
        expect(zodiosApi.create_assets_bulk_api_v1_assets_post).not.toHaveBeenCalled();
        await fireEvent.click(confirm);
    }

    it('links the existing creation success toast only when opted in and returns the same created ID', async () => {
        const id = 4201;
        const name = 'Owned linked asset';
        const {oncreated, goto, hrefBefore} = await mountCreation(id, name, true);

        await fireEvent.click(saveBtn());

        await expectCreationClosed(oncreated, [id, {syncing: false}]);
        const content = toastMarkup('success');
        const anchor = within(content).getByTestId('toast-asset-link');
        expect(anchor).toBeInstanceOf(HTMLAnchorElement);
        expect(anchor).toHaveAttribute('href', `/assets/${id}`);
        expect(anchor).toHaveTextContent(name);
        expect(content.getElementsByTagName('a')).toHaveLength(1);
        expectOnlySuccessToast();
        expect(zodiosApi.create_assets_bulk_api_v1_assets_post).toHaveBeenCalledTimes(1);
        expect(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).not.toHaveBeenCalled();
        expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).not.toHaveBeenCalled();
        expect(goto).not.toHaveBeenCalled();
        expect(window.location.href).toBe(hrefBefore);
    });

    it('keeps default contextual creation as one plain-name success toast with no anchor or navigation', async () => {
        const id = 4202;
        const name = 'Owned contextual asset';
        // Deliberately omit the new prop: this is the shared-component default.
        const {oncreated, goto, hrefBefore} = await mountCreation(id, name);

        await fireEvent.click(saveBtn());

        await expectCreationClosed(oncreated, [id, {syncing: false}]);
        const content = toastMarkup('success');
        expect(content).toHaveTextContent(name);
        expect(content.getElementsByTagName('a')).toHaveLength(0);
        expectOnlySuccessToast();
        expect(goto).not.toHaveBeenCalled();
        expect(window.location.href).toBe(hrefBefore);
    });

    it.each([
        {mode: 'opted-in link', linkCreatedAsset: true},
        {mode: 'default plain name', linkCreatedAsset: undefined},
    ])('escapes a malicious asset name exactly once in the $mode success toast', async ({linkCreatedAsset}) => {
        const id = 4203;
        const name = `<img src=x onerror="alert('x')"> & owned`;
        const {oncreated, goto, hrefBefore} = await mountCreation(id, name, linkCreatedAsset);

        await fireEvent.click(saveBtn());

        await expectCreationClosed(oncreated, [id, {syncing: false}]);
        const content = toastMarkup('success');
        expect(content).toHaveTextContent(name);
        expect(content.getElementsByTagName('img')).toHaveLength(0);
        expect(content.innerHTML).toContain('&lt;img');
        expect(content.innerHTML).not.toContain('&amp;lt;img');
        if (linkCreatedAsset) {
            const anchor = within(content).getByTestId('toast-asset-link');
            expect(anchor).toHaveTextContent(name);
            expect(anchor).toHaveAttribute('href', `/assets/${id}`);
            expect(content.getElementsByTagName('a')).toHaveLength(1);
        } else {
            expect(content.getElementsByTagName('a')).toHaveLength(0);
        }
        expectOnlySuccessToast();
        expect(goto).not.toHaveBeenCalled();
        expect(window.location.href).toBe(hrefBefore);
    });

    it('preserves provider assignment and closes with one linked success while background sync is pending', async () => {
        const id = 4204;
        const name = 'Owned provider-linked asset';
        vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue(providerFixture);
        vi.mocked(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).mockResolvedValueOnce({
            results: [{asset_id: id, success: true, message: '[[assigned-response]]'}],
            success_count: 1,
        });
        let finishSync!: (response: SyncResponse) => void;
        const pendingSync = new Promise<SyncResponse>((resolve) => {
            finishSync = resolve;
        });
        const syncResponse: SyncResponse = {results: [{asset_id: id, status: 'ok', points_fetched: 3, points_changed: 3}], success_count: 1};
        vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).mockReturnValueOnce(pendingSync);
        try {
            const {oncreated, goto, hrefBefore} = await mountCreation(id, name, true);
            await chooseProviderWithoutProbing();

            await saveWithUntestedProvider();

            await expectCreationClosed(oncreated, [id, {syncing: true}]);
            expect(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).toHaveBeenCalledTimes(1);
            expect(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).toHaveBeenCalledWith([{asset_id: id, provider_code: PROVIDER_CODE, identifier: PROVIDER_IDENTIFIER, identifier_type: 'TICKER', provider_params: null}]);
            expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).toHaveBeenCalledTimes(1);
            expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).toHaveBeenCalledWith([{asset_id: id, date_range: {start: 'resume', end: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/)}}]);
            expect(within(toastMarkup('success')).getByTestId('toast-asset-link')).toHaveAttribute('href', `/assets/${id}`);
            expectOnlySuccessToast();
            expect(goto).not.toHaveBeenCalled();
            expect(window.location.href).toBe(hrefBefore);

            finishSync(syncResponse);
            await pendingSync;
            expectOnlySuccessToast();
            expect(oncreated).toHaveBeenCalledTimes(1);
        } finally {
            // Always settle the test-owned promise, even after an assertion fails.
            finishSync(syncResponse);
            await pendingSync;
        }
    });

    it('keeps provider-assignment failure as one warning without a success link or background sync', async () => {
        const id = 4205;
        const name = 'Owned assignment-warning asset';
        vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue(providerFixture);
        vi.mocked(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).mockRejectedValueOnce(new Error('[[assignment-failed]]'));
        const {oncreated, goto, hrefBefore} = await mountCreation(id, name, true);
        await chooseProviderWithoutProbing();

        await saveWithUntestedProvider();

        // The assignment failure reports the id alone: no sync starts (O-20).
        await expectCreationClosed(oncreated, [id]);
        expect(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).toHaveBeenCalledTimes(1);
        const content = toastMarkup('warning');
        expect(content).toHaveTextContent(name);
        expect(content.getElementsByTagName('a')).toHaveLength(0);
        expect(toasts.success).not.toHaveBeenCalled();
        expect(toasts.info).not.toHaveBeenCalled();
        expect(toasts.error).not.toHaveBeenCalled();
        expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).not.toHaveBeenCalled();
        expect(goto).not.toHaveBeenCalled();
        expect(window.location.href).toBe(hrefBefore);
    });

    it('leaves edit-save feedback and onupdated unchanged even when the creation-link prop is true', async () => {
        const id = 4206;
        const oncreated = vi.fn();
        const onupdated = vi.fn();
        const goto = vi.spyOn(navigation, 'goto');
        vi.mocked(zodiosApi.patch_assets_bulk_api_v1_assets_patch).mockResolvedValueOnce({
            results: [{asset_id: id, success: true, message: '[[patched-response]]'}],
            success_count: 1,
        });
        vi.mocked(zodiosApi.remove_providers_bulk_api_v1_assets_provider_delete).mockResolvedValueOnce({
            results: [{asset_id: id, success: true, deleted_count: 0}],
            success_count: 1,
        });
        render(AssetModal, {
            open: true,
            editMode: true,
            editData: {id, display_name: 'Owned previous name', currency: 'USD', asset_type: 'STOCK'},
            linkCreatedAsset: true,
            oncreated,
            onupdated,
        });
        await waitForForm();
        await waitFor(() => expect(nameInput()).toHaveValue('Owned previous name'));
        await fill('asset-modal-display-name', 'Owned edited name');
        await waitFor(() => expect(saveBtn()).toBeEnabled());

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(onupdated).toHaveBeenCalledTimes(1));
        await waitFor(() => expect(screen.queryByTestId('asset-modal-form')).toBeNull());
        const content = toastMarkup('success');
        expect(content).toHaveTextContent('Owned edited name');
        expect(content.getElementsByTagName('a')).toHaveLength(0);
        expectOnlySuccessToast();
        expect(oncreated).not.toHaveBeenCalled();
        expect(zodiosApi.create_assets_bulk_api_v1_assets_post).not.toHaveBeenCalled();
        expect(zodiosApi.patch_assets_bulk_api_v1_assets_patch).toHaveBeenCalledWith([expect.objectContaining({asset_id: id, display_name: 'Owned edited name'})]);
        expect(goto).not.toHaveBeenCalled();
    });

    // =====================================================================
    // O-20: the modal owns the one price sync of a creation. `oncreated(id, {syncing})` says whether it
    // started, `onsynced(id, result)` how it ended — the asset's result, or null when the request failed —
    // so the Assets page shows it and reloads instead of starting a second sync of its own.
    // No sync, no `onsynced`.
    // =====================================================================
    describe('the one price sync of a creation (O-20)', () => {
        const SCHEDULED = 'scheduled_investment';
        const scheduledProviderFixture: Awaited<ReturnType<typeof zodiosApi.list_providers_api_v1_assets_provider_get>> = [
            {
                code: SCHEDULED,
                name: 'Owned scheduled investment',
                description: 'Synthetic parametric provider metadata; no network implementation',
                kind: 'parametric_generation',
                supports_search: false,
                // The real plugin's schema: no field of its own, the schedule editor instead.
                params_schema: [{key: '_ui_component', type: 'ui_component', required: false, description: 'Custom editor: ScheduledInvestmentEditor', default: SCHEDULED}],
                accepted_identifier_types: ['AUTO_GENERATED'],
            },
        ];

        afterEach(() => {
            // Back to the module mock's own answer (`() => false`) for every later test.
            vi.mocked(isParametricProvider).mockReset();
        });

        it('reports the sync through onsynced(assetId, results[0]) once it has answered, never before', async () => {
            const id = 4207;
            const name = 'Owned synced asset';
            vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue(providerFixture);
            vi.mocked(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).mockResolvedValueOnce({
                results: [{asset_id: id, success: true, message: '[[assigned-response]]'}],
                success_count: 1,
            });
            let finishSync!: (response: SyncResponse) => void;
            const pendingSync = new Promise<SyncResponse>((resolve) => {
                finishSync = resolve;
            });
            const result = {asset_id: id, status: 'partial' as const, points_fetched: 5, points_changed: 3, inserted_count: 2, updated_count: 1, errors: ['[[sync-note]]']};
            const syncResponse: SyncResponse = {results: [result], success_count: 1};
            vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).mockReturnValueOnce(pendingSync);
            const onsynced = vi.fn<OnSynced>();
            try {
                const {oncreated} = await mountCreation(id, name, true, onsynced);
                await chooseProviderWithoutProbing();

                await saveWithUntestedProvider();

                await expectCreationClosed(oncreated, [id, {syncing: true}]);
                expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).toHaveBeenCalledTimes(1);
                // The request is out and unanswered: the sync has started, it has not ended.
                expect(onsynced).not.toHaveBeenCalled();

                finishSync(syncResponse);
                await waitFor(() => expect(onsynced).toHaveBeenCalledWith(id, result));
                expect(onsynced).toHaveBeenCalledTimes(1);
                expect(oncreated).toHaveBeenCalledTimes(1);
                // Reported, not announced: the caller owns the sync's toast, the modal only its creation's.
                expectOnlySuccessToast();
            } finally {
                // Always settle the test-owned promise, even after an assertion fails.
                finishSync(syncResponse);
                await pendingSync;
            }
        });

        it('reports a failed sync request through onsynced(assetId, null)', async () => {
            const id = 4208;
            const name = 'Owned sync-failed asset';
            vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue(providerFixture);
            vi.mocked(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).mockResolvedValueOnce({
                results: [{asset_id: id, success: true, message: '[[assigned-response]]'}],
                success_count: 1,
            });
            const syncError = new Error('[[sync-request-failed]]');
            vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).mockRejectedValueOnce(syncError);
            // The failure is logged and swallowed (non-blocking): silenced here, and checked below.
            const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
            const onsynced = vi.fn<OnSynced>();
            const {oncreated} = await mountCreation(id, name, true, onsynced);
            await chooseProviderWithoutProbing();

            await saveWithUntestedProvider();

            await expectCreationClosed(oncreated, [id, {syncing: true}]);
            await waitFor(() => expect(onsynced).toHaveBeenCalledWith(id, null));
            expect(onsynced).toHaveBeenCalledTimes(1);
            expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).toHaveBeenCalledTimes(1);
            expect(warn).toHaveBeenCalledWith(expect.any(String), syncError);
            expectOnlySuccessToast();
        });

        it('starts no sync without a provider: oncreated(assetId, {syncing: false}) and no onsynced', async () => {
            const id = 4209;
            const name = 'Owned provider-less asset';
            const onsynced = vi.fn<OnSynced>();
            const {oncreated} = await mountCreation(id, name, true, onsynced);

            await fireEvent.click(saveBtn());

            await expectCreationClosed(oncreated, [id, {syncing: false}]);
            // The sync, when there is one, is requested in the same synchronous step that calls oncreated: no
            // request now is none ever, and onsynced only answers a request.
            expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).not.toHaveBeenCalled();
            expect(onsynced).not.toHaveBeenCalled();
        });

        it('starts no sync when the provider assignment fails: oncreated(assetId) alone and no onsynced', async () => {
            const id = 4210;
            const name = 'Owned unassigned asset';
            vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue(providerFixture);
            vi.mocked(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).mockRejectedValueOnce(new Error('[[assignment-failed]]'));
            const onsynced = vi.fn<OnSynced>();
            const {oncreated} = await mountCreation(id, name, true, onsynced);
            await chooseProviderWithoutProbing();

            await saveWithUntestedProvider();

            await expectCreationClosed(oncreated, [id]);
            // Presence first: the assignment was attempted, and failed — the reason there is no sync.
            expect(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).toHaveBeenCalledTimes(1);
            // oncreated is the last step of that path: no request now is none ever.
            expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).not.toHaveBeenCalled();
            expect(onsynced).not.toHaveBeenCalled();
        });

        it('syncs a parametric provider too: scheduled_investment with a schedule posts the sync from resume, {syncing: true}', async () => {
            const id = 4211;
            const name = 'Owned scheduled asset';
            // The real classification: the sync used to be skipped exactly because this said true.
            vi.mocked(isParametricProvider).mockImplementation((code) => code === SCHEDULED);
            vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue(scheduledProviderFixture);
            vi.mocked(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).mockResolvedValueOnce({
                results: [{asset_id: id, success: true, message: '[[assigned-response]]'}],
                success_count: 1,
            });
            const result = {asset_id: id, status: 'ok' as const, points_fetched: 31, points_changed: 31};
            vi.mocked(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).mockResolvedValueOnce({results: [result], success_count: 1});
            const onsynced = vi.fn<OnSynced>();
            const {oncreated} = await mountCreation(id, name, true, onsynced);

            // Its identifier is generated (AUTO_GENERATED is its only type) and its parameters are the schedule
            // editor's: the first period it adds is the schedule this creation carries.
            expect(screen.queryByTestId('provider-code-select-button')).toBeNull();
            await fireEvent.click(screen.getByTestId('asset-modal-provider-header'));
            await fireEvent.click(await screen.findByTestId('provider-code-select-button'));
            await fireEvent.click(await screen.findByTestId(`provider-option-${SCHEDULED}`));
            await waitFor(() => expect(screen.queryByTestId(`provider-option-${SCHEDULED}`)).toBeNull());
            await fireEvent.click(await screen.findByTestId('schedule-add-first-period'));
            await waitFor(() => expect(screen.getByTestId('schedule-status')).toHaveAttribute('data-valid', 'true'));
            await waitFor(() => expect(saveBtn()).toBeEnabled());

            await saveWithUntestedProvider();

            await expectCreationClosed(oncreated, [id, {syncing: true}]);
            // Precondition, verified: assigned WITH its schedule — without one the assignment, and the sync, are skipped.
            expect(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).toHaveBeenCalledTimes(1);
            const assignment = vi.mocked(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).mock.calls[0]?.[0]?.[0];
            expect(assignment).toMatchObject({asset_id: id, provider_code: SCHEDULED, identifier_type: 'AUTO_GENERATED'});
            expect(assignment?.provider_params?.schedule, 'the assignment carries the schedule the editor built').toHaveLength(1);
            expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).toHaveBeenCalledTimes(1);
            expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).toHaveBeenCalledWith([{asset_id: id, date_range: {start: 'resume', end: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/)}}]);
            await waitFor(() => expect(onsynced).toHaveBeenCalledWith(id, result));
            expect(onsynced).toHaveBeenCalledTimes(1);
        });
    });
});

// =========================================================================
describe('AssetModal — edit submit', () => {
    it('PATCHes with the asset id and the edited name, then fires onupdated', async () => {
        patchFn().mockResolvedValue({results: [{success: true, asset_id: 7}], success_count: 1} as never);
        const onupdated = vi.fn();
        render(AssetModal, {
            open: true,
            editMode: true,
            editData: {id: 7, display_name: 'Old Name', currency: 'USD', asset_type: 'STOCK', quote_base_quantity: 1, active: true},
            onupdated,
        });
        await waitForForm();
        await waitFor(() => expect(nameInput().value).toBe('Old Name'));

        await fill('asset-modal-display-name', 'New Name');
        await fireEvent.click(saveBtn());

        await waitFor(() => expect(onupdated).toHaveBeenCalled());
        expect(patchFn()).toHaveBeenCalledWith([expect.objectContaining({asset_id: 7, display_name: 'New Name', currency: 'USD'})]);
        // No provider on editData → provider removed.
        expect(removeProviderFn()).toHaveBeenCalled();
    });

    it('opens the destructive currency-change modal when the PATCH is blocked by market data', async () => {
        patchFn().mockResolvedValue({
            results: [
                {
                    success: false,
                    message: 'CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|prices=3|events_manual=1|events_provider=0|linked_tx=2|oldest=2020-01-01|newest=2024-01-01|from=USD|to=EUR',
                },
            ],
        } as never);
        const onupdated = vi.fn();
        render(AssetModal, {
            open: true,
            editMode: true,
            editData: {id: 7, display_name: 'Blocked Asset', currency: 'EUR', asset_type: 'STOCK', quote_base_quantity: 1, active: true},
            onupdated,
        });
        await waitForForm();
        await waitFor(() => expect(nameInput().value).toBe('Blocked Asset'));

        await fireEvent.click(saveBtn());

        // The blocker token routes into the destructive confirm modal instead of updating.
        await waitFor(() => expect(screen.queryByTestId('currency-change-modal')).not.toBeNull());
        expect(onupdated).not.toHaveBeenCalled();
    });
});

// =========================================================================
describe('AssetModal — prefill (create wizard)', () => {
    it('populates name + identifier from prefillData and carries the ISIN into the create payload', async () => {
        createFn().mockResolvedValue({results: [{success: true, asset_id: 99}]} as never);
        const oncreated = vi.fn();
        render(AssetModal, {
            open: true,
            editMode: false,
            prefillData: {display_name: 'Apple Inc.', identifier_isin: 'US0378331005'},
            oncreated,
        });
        await waitForForm();
        expect(nameInput().value).toBe('Apple Inc.');
        // An identifier row auto-expands the more-info disclosure.
        await waitFor(() => expect(screen.getByTestId('asset-modal-more-info')).toHaveAttribute('data-expanded', 'true'));

        await fireEvent.click(saveBtn());
        await waitFor(() => expect(oncreated).toHaveBeenCalledWith(99, {syncing: false}));
        expect(createFn()).toHaveBeenCalledWith([expect.objectContaining({display_name: 'Apple Inc.', identifier_isin: 'US0378331005'})]);
    });

    it('carries currency, asset type, quote base and short description from the import, and stays collapsed without identifiers', async () => {
        createFn().mockResolvedValue({results: [{success: true, asset_id: 101}]} as never);
        const oncreated = vi.fn();
        render(AssetModal, {
            open: true,
            editMode: false,
            prefillData: {
                display_name: 'Vanguard FTSE',
                currency: 'EUR',
                asset_type: 'ETF',
                quote_base_quantity: 5,
                classification_params: {short_description: 'A short blurb'},
            },
            oncreated,
        });
        await waitForForm();
        expect(nameInput().value).toBe('Vanguard FTSE');
        // The prefilled quote base is applied (guard `data.quote_base_quantity > 0`).
        expect((screen.getByTestId('asset-modal-quote-base-quantity') as HTMLInputElement).value).toBe('5');
        // No identifier came in → the more-info disclosure stays collapsed.
        expect(screen.getByTestId('asset-modal-more-info')).toHaveAttribute('data-expanded', 'false');

        await fireEvent.click(saveBtn());
        await waitFor(() => expect(oncreated).toHaveBeenCalledWith(101, {syncing: false}));
        expect(createFn()).toHaveBeenCalledWith([
            expect.objectContaining({
                display_name: 'Vanguard FTSE',
                currency: 'EUR',
                asset_type: 'ETF',
                classification_params: expect.objectContaining({short_description: 'A short blurb'}),
            }),
        ]);
    });
});

// =========================================================================
describe('AssetModal — more-info disclosure', () => {
    it('starts collapsed and toggles open on click', async () => {
        render(AssetModal, {open: true, oncreated: vi.fn()});
        await waitForForm();
        const header = screen.getByTestId('asset-modal-more-info');
        expect(header).toHaveAttribute('data-expanded', 'false');

        await fireEvent.click(header);
        await waitFor(() => expect(header).toHaveAttribute('data-expanded', 'true'));
        // The add-identifier control is now reachable.
        expect(screen.queryByTestId('asset-modal-add-identifier')).not.toBeNull();
    });
});

// =========================================================================
describe('AssetModal — duplicate name detection', () => {
    it('surfaces a warning when another asset already has that name', async () => {
        listFn().mockResolvedValue([{id: 1, display_name: 'Apple Inc.'}] as never);
        render(AssetModal, {open: true, oncreated: vi.fn()});
        await waitForForm();

        await fill('asset-modal-display-name', 'Apple Inc.');
        await waitFor(() => expect(screen.queryByTestId('asset-modal-duplicate-warning')).not.toBeNull());
        expect(screen.getByTestId('asset-modal-duplicate-warning')).toHaveAttribute('data-duplicate-name', 'Apple Inc.');
    });

    it('does not warn when the name is unique', async () => {
        listFn().mockResolvedValue([{id: 1, display_name: 'Something Else'}] as never);
        render(AssetModal, {open: true, oncreated: vi.fn()});
        await waitForForm();

        await fill('asset-modal-display-name', 'Apple Inc.');
        // Give the debounce time to run, then assert the warning never appeared.
        await waitFor(() => expect(listFn()).toHaveBeenCalled());
        expect(screen.queryByTestId('asset-modal-duplicate-warning')).toBeNull();
    });
});

// =========================================================================
describe('AssetModal — cancel & discard', () => {
    it('closes immediately via onclose when the form is pristine', async () => {
        const onclose = vi.fn();
        render(AssetModal, {open: true, oncreated: vi.fn(), onclose});
        await waitForForm();
        // Let the initial snapshot settle so isDirty is a real (false) answer.
        await waitFor(() => expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-snapshot-ready', 'true'));
        expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'false');

        await fireEvent.click(screen.getByTestId('asset-modal-cancel'));
        await waitFor(() => expect(onclose).toHaveBeenCalled());
        expect(screen.queryByTestId('asset-modal-form')).toBeNull();
    });

    it('asks to discard when there are unsaved changes, and closes only on confirm', async () => {
        const onclose = vi.fn();
        render(AssetModal, {open: true, oncreated: vi.fn(), onclose});
        await waitForForm();
        // Wait for the pristine baseline to be captured before editing.
        await waitFor(() => expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-snapshot-ready', 'true'));
        await fill('asset-modal-display-name', 'Half typed');
        await waitFor(() => expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true'));

        await fireEvent.click(screen.getByTestId('asset-modal-cancel'));
        // The discard confirmation appears instead of closing.
        await waitFor(() => expect(screen.queryByTestId('asset-modal-discard-confirm')).not.toBeNull());
        expect(onclose).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(onclose).toHaveBeenCalled());
        expect(screen.queryByTestId('asset-modal-form')).toBeNull();
    });

    it('keeps editing when the discard confirmation is dismissed', async () => {
        const onclose = vi.fn();
        render(AssetModal, {open: true, oncreated: vi.fn(), onclose});
        await waitForForm();
        await waitFor(() => expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-snapshot-ready', 'true'));
        await fill('asset-modal-display-name', 'Half typed');
        await waitFor(() => expect(screen.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'true'));

        await fireEvent.click(screen.getByTestId('asset-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('asset-modal-discard-confirm')).not.toBeNull());

        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('asset-modal-discard-confirm')).toBeNull());
        expect(onclose).not.toHaveBeenCalled();
        // Form still there.
        expect(screen.queryByTestId('asset-modal-form')).not.toBeNull();
    });
});

// =========================================================================
// The description's placeholder is a catalogue sentence (13/10/2026). It was written in English in
// the markup, so an Italian or French form showed an English hint. The expected sentence is read
// from the loaded catalogue (`get(_)`), in the language the UI is in — never written here — and the
// harness half proves it differs from the English one, else the language could not be told.
describe('AssetModal — the description placeholder speaks the UI language', () => {
    const PLACEHOLDER_KEY = 'assets.modal.descriptionPlaceholder';
    const description = () => screen.getByTestId('asset-modal-description');

    it('reads the catalogue sentence with the UI in English (guard)', async () => {
        // beforeEach put the UI in English.
        const sentence = get(_)(PLACEHOLDER_KEY);
        expect(sentence, `${PLACEHOLDER_KEY} does not resolve: the catalogue is not loaded, or the key is gone`).not.toBe(PLACEHOLDER_KEY);
        render(AssetModal, {open: true, oncreated: vi.fn()});
        await waitForForm();

        expect(description(), `the description's placeholder is not ${PLACEHOLDER_KEY} in English`).toHaveAttribute('placeholder', sentence);
    });

    it.each(['it', 'fr'] as const)('reads the catalogue sentence with the UI in %s, not the English one', async (language) => {
        // beforeEach put the UI in English: the sentence the form must no longer show in another language.
        const english = get(_)(PLACEHOLDER_KEY);
        await setupI18n(language);
        currentLanguage.set(language);
        try {
            const sentence = get(_)(PLACEHOLDER_KEY);
            expect(sentence, `${PLACEHOLDER_KEY} does not resolve in ${language}: the catalogue is not loaded, or the key is gone`).not.toBe(PLACEHOLDER_KEY);
            expect(sentence, `premise: ${PLACEHOLDER_KEY} reads alike in English and ${language}, so the placeholder's language could not be told`).not.toBe(english);
            render(AssetModal, {open: true, oncreated: vi.fn()});
            await waitForForm();

            expect(description(), `the description's placeholder is not ${PLACEHOLDER_KEY} in ${language}: it is written in the markup`).toHaveAttribute('placeholder', sentence);
        } finally {
            currentLanguage.set('en');
            await setupI18n('en');
        }
    });
});

// =========================================================================
// P20 (workstream X, sub-lot 3): the report of a search carries the form. Both <AssetSearchAutocomplete> calls —
// with the import's search badges and without — get `reportContext={{currency, assetType, identifiers}}`, the
// identifiers being the rows with a value. The form is prefilled as the import wizard does, the search it opens
// with (`initialSearchQuery`) finds nothing, and the report link of that search must name what the form says. The
// instance is the real `instanceConfig`, answered in `beforeEach` without a request: a self-hosted instance with no
// support address, the one that falls back to a public GitHub issue (N61). The link is that issue, whose body is
// decoded from the href.
//
// What the form says, never what it merely defaults to (16/10/2026): a blank create form starts at the user's base
// currency (EUR here: this file has no user settings) and at STOCK, and naming those hands support a hint nobody gave.
// So the currency is named in edit mode, or when the prefill had one, or the user chose one, or it is not the blank
// form's; the type in edit mode, or when the prefill had one, or it is not STOCK. Identifiers as before.
describe('AssetModal — the report of a search carries the form (P20)', () => {
    type ProviderList = Awaited<ReturnType<typeof zodiosApi.list_providers_api_v1_assets_provider_get>>;
    const SEARCH_PROVIDER = 'fixture_search_source';
    const QUERY = 'Owned unfindable fund';
    const searchable: ProviderList = [
        {
            code: SEARCH_PROVIDER,
            name: 'Owned search source',
            description: 'Synthetic searchable provider metadata; no network implementation',
            kind: 'online_scraper',
            supports_search: true,
            params_schema: [],
            accepted_identifier_types: ['ISIN', 'TICKER'],
        },
    ];

    // N61: with no support address the report falls back to GitHub only on a self-hosted instance whose configuration
    // has loaded. The store's own `load`, with an answer instead of the request: no module mock, the store as it runs.
    beforeEach(async () => {
        await instanceConfig.load({force: true, fetchConfig: async () => ({profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}, support_url: null})});
        expect(instanceConfig.loaded, 'precondition: the instance configuration has loaded').toBe(true);
        expect(instanceConfig.config.profile, 'precondition: a self-hosted instance').toBe('selfhosted');
    });

    afterEach(async () => {
        // The defaults again for whatever runs next. `loaded` has no way back to false; no other block of this file reads it.
        await instanceConfig.load({force: true, fetchConfig: async () => DEFAULT_INSTANCE_CONFIG});
    });

    /** The streamed search's Response, replaying `events` as SSE `data:` lines (as AssetSearchAutocomplete.test.ts does). */
    function streamedSearch(events: unknown[]) {
        const encoder = new TextEncoder();
        const chunks = events.map((event) => encoder.encode(`data: ${JSON.stringify(event)}\n`));
        let next = 0;
        return {
            ok: true,
            body: {
                getReader: () => ({
                    read: async () => (next < chunks.length ? {done: false, value: chunks[next++]} : {done: true, value: undefined}),
                    cancel: vi.fn(),
                }),
            },
        };
    }

    it.each([
        {call: 'the search without badges', initialSearchBadges: []},
        {call: 'the search under the import badges', initialSearchBadges: [{label: `Name: ${QUERY}`, value: QUERY}]},
    ])('$call: the report link names the currency, the type and the identifier of the form', async ({initialSearchBadges}) => {
        vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue(searchable);
        // The streamed search finds nothing; any other request gets this file's default answer.
        const search = vi.fn(async (url: string) => (String(url).includes('/assets/provider/search/stream') ? streamedSearch([{event: 'provider_results', provider_code: SEARCH_PROVIDER, results: []}, {event: 'done'}]) : new Response(null, {status: 503})));
        vi.stubGlobal('fetch', search);
        render(AssetModal, {
            open: true,
            editMode: false,
            prefillData: {display_name: QUERY, currency: 'CHF', asset_type: 'ETF', identifier_isin: 'IE00BK5BQT80'},
            initialSearchQuery: QUERY,
            initialSearchBadges,
            oncreated: vi.fn(),
        });
        await waitForForm();

        // Precondition, verified: the search ran, with the query the modal opened with, and found nothing.
        await waitFor(() => expect(screen.getByTestId('asset-search-results')).toHaveAttribute('data-state', 'empty'), {timeout: 3_000});
        const streamed = search.mock.calls.map(([url]) => String(url)).filter((url) => url.includes('/assets/provider/search/stream'));
        expect(streamed.at(-1)).toContain(`q=${encodeURIComponent(QUERY)}`);

        const link = await waitFor(() => screen.getByTestId('asset-search-report'));
        const url = new URL(link.getAttribute('href') ?? '');
        expect(`${url.origin}${url.pathname}`).toBe(GITHUB_NEW_ISSUE_URL);
        const lines = (url.searchParams.get('body') ?? '').split('\n');
        expect(lines).toContain(`Search: ${QUERY}`);
        expect(lines.filter((line) => line.startsWith('In the form:'))).toEqual(['In the form: currency CHF, type ETF, ISIN IE00BK5BQT80']);
    });

    /** The online search finds nothing; any other request gets this file's default answer. */
    function searchFindingNothing(): void {
        vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue(searchable);
        vi.stubGlobal(
            'fetch',
            vi.fn(async (url: string) => (String(url).includes('/assets/provider/search/stream') ? streamedSearch([{event: 'provider_results', provider_code: SEARCH_PROVIDER, results: []}, {event: 'done'}]) : new Response(null, {status: 503}))),
        );
    }

    /** Types `query` into the form's online search, as a user does: in edit mode it opens empty and searches nothing. */
    async function searchFor(query: string): Promise<void> {
        const box = document.querySelector<HTMLElement>('[data-search-autocomplete]');
        expect(box, 'the form shows its online search').not.toBeNull();
        await fireEvent.input(within(box!).getByRole('textbox'), {target: {value: query}});
    }

    /** The report of the search for `query` once it has found nothing: its body, line by line, decoded from the link. */
    async function reportOfEmptySearch(query: string): Promise<string[]> {
        await waitFor(() => expect(screen.getByTestId('asset-search-results')).toHaveAttribute('data-state', 'empty'), {timeout: 3_000});
        const link = await waitFor(() => screen.getByTestId('asset-search-report'));
        const url = new URL(link.getAttribute('href') ?? '');
        expect(`${url.origin}${url.pathname}`).toBe(GITHUB_NEW_ISSUE_URL);
        const lines = (url.searchParams.get('body') ?? '').split('\n');
        expect(lines, 'the report of this very search').toContain(`Search: ${query}`);
        return lines;
    }

    const formLines = (lines: string[]): string[] => lines.filter((line) => line.startsWith('In the form:'));

    it('(c) a blank create form: no «In the form:» line — no identifier, and a currency and a type nobody chose are no hint', async () => {
        searchFindingNothing();
        render(AssetModal, {open: true, editMode: false, initialSearchQuery: QUERY, oncreated: vi.fn()});
        await waitForForm();

        const lines = await reportOfEmptySearch(QUERY);

        expect(formLines(lines), 'the blank form’s EUR and STOCK are defaults, not what the user said').toEqual([]);
        // Nothing in its place either: the providers are followed straight by the line of the app.
        const app = lines.findIndex((line) => line.startsWith('LibreFolio '));
        expect(app, 'the report names the app that wrote it').toBeGreaterThan(0);
        expect(lines[app - 1]).toBe(`- ${SEARCH_PROVIDER}: 0 results`);
    });

    it('(d) edit mode: the asset’s own currency and type are named — STOCK too, the blank default, because the asset has it', async () => {
        searchFindingNothing();
        render(AssetModal, {
            open: true,
            editMode: true,
            editData: {id: 7, display_name: 'Tesla Inc.', currency: 'USD', asset_type: 'STOCK', quote_base_quantity: 1, active: true},
            onupdated: vi.fn(),
        });
        await waitForForm();
        await waitFor(() => expect(nameInput()).toHaveValue('Tesla Inc.'));

        await searchFor(QUERY);

        const lines = await reportOfEmptySearch(QUERY);
        expect(formLines(lines), 'the asset has no identifier: currency and type only').toEqual(['In the form: currency USD, type STOCK']);
    });

    it('(e) a blank create form whose type the user changed: that type is named, and still no currency', async () => {
        searchFindingNothing();
        render(AssetModal, {open: true, editMode: false, oncreated: vi.fn()});
        await waitForForm();

        // The type picker, driven as a user does: open it, open the ETF family, pick its generic member.
        const field = screen.getByTestId('asset-modal-type');
        const trigger = screen.getByTestId('asset-modal-type-button');
        await fireEvent.click(trigger);
        await fireEvent.click(within(field).getByTestId('asset-type-tree-group-ETF'));
        await fireEvent.click(within(field).getByTestId('asset-type-tree-option-ETF'));
        await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'));
        // Precondition, verified: the form holds ETF — the closed picker shows that type's picture, and only it.
        const pictures = trigger.querySelectorAll('img');
        expect(pictures, 'the closed type select shows exactly one picture, the one of the selected type').toHaveLength(1);
        expect(pictures[0]).toHaveAttribute('src', '/icons/asset-types/etf.png');

        await searchFor(QUERY);

        const lines = await reportOfEmptySearch(QUERY);
        expect(formLines(lines), 'the type the user chose; the currency is still the blank form’s').toEqual(['In the form: type ETF']);
    });
});

// =========================================================================
// Z-32 (d): the quote base — the plugin's suggestion for the line, else the type's default (a BOND 100, any other 1).
//
// A search selection writes it as it writes the name, the type and the currency: over any value, typed ones included,
// in create and in edit (Q-Q6). A suggestion shows its hint (`asset-modal-qbq-suggestion-hint`) while the line is still
// the one it was made for; a keystroke in the field hides it. «Ask the provider» — the automatic read after a selection
// too — never fills the field in silence: a different proposal is a checked row of the comparison, applied only on the
// user's word, and an equal one is nothing. R1: the line's latest explicit suggestion answers for a read whose own
// suggestion failed. A stored asset changes only on Save; a manual type change does nothing to the field.
//
// The search is the real AssetSearchAutocomplete over a streamed answer, as in the P20 block. The probe is answered by
// operation: the connection test passes, the metadata of a line is the case's. The hint's and the note's sentences are
// read from the loaded catalogue (`get(_)`), each key proven present first — never written here. A read that finds
// nothing to ask ends on `toasts.success(assets.comparison.allMatch)`: that toast is the barrier a case waits on before
// it asserts that nothing was proposed. RED until the modal follows the ladder (and AssetSearchAutocomplete hands it the
// suggestion): today a selection keeps the field, only a BOND gets 100 (the seed, and only over an untouched 1), and no
// read ever proposes a quote base. The guards, green today, say so in their names.
describe('AssetModal — the quote base: the plugin’s suggestion, else the type’s default (Z-32 d)', () => {
    type ProviderList = Awaited<ReturnType<typeof zodiosApi.list_providers_api_v1_assets_provider_get>>;
    /** The plugin's suggestion, as the API sends it (`FAQuoteBaseSuggestion`). */
    interface Suggestion {
        quantity: number;
        quote_currency?: string | null;
    }
    /** A search result (`FAProviderSearchResultItem`). */
    interface Line {
        identifier: string;
        identifier_type: string;
        display_name: string;
        provider_code: string;
        currency: string;
        asset_type: string;
        via_web: boolean;
        quote_base_suggestion?: Suggestion | null;
    }

    const LINE_PROVIDER = 'fixture_quote_source';
    const LINE_PROVIDER_NAME = 'Owned quote source';
    const QUERY = 'Owned quote base query';
    const quoteSource: ProviderList = [
        {
            code: LINE_PROVIDER,
            name: LINE_PROVIDER_NAME,
            description: 'Synthetic searchable provider metadata; no network implementation',
            kind: 'online_scraper',
            supports_search: true,
            params_schema: [],
            // Two types: with only one, the provider panel would rewrite a picked line's identifier type, and the line with it.
            accepted_identifier_types: ['TICKER', 'ISIN'],
        },
    ];

    /** A line quoted in pence: its plugin suggests one price per 100 shares, in GBp (Yahoo's VOD.L). */
    const PENCE: Line = {identifier: 'VOD.L', identifier_type: 'TICKER', display_name: 'Owned Vodafone Group', provider_code: LINE_PROVIDER, currency: 'GBP', asset_type: 'STOCK', via_web: false, quote_base_suggestion: {quantity: 100, quote_currency: 'GBp'}};
    /** A STOCK its plugin says nothing about. */
    const PLAIN_STOCK: Line = {identifier: 'US0378331005', identifier_type: 'ISIN', display_name: 'Owned Apple Inc.', provider_code: LINE_PROVIDER, currency: 'USD', asset_type: 'STOCK', via_web: false, quote_base_suggestion: null};
    /** A BOND whose result has no suggestion field at all. */
    const PLAIN_BOND: Line = {identifier: 'IT0005557006', identifier_type: 'ISIN', display_name: 'Owned BTP Valore 2028', provider_code: LINE_PROVIDER, currency: 'EUR', asset_type: 'BOND', via_web: false};
    /** A pence line the search found without its suggestion: only a metadata read brings it. */
    const PENCE_UNSUGGESTED: Line = {identifier: 'BARC.L', identifier_type: 'TICKER', display_name: 'Owned Barclays', provider_code: LINE_PROVIDER, currency: 'GBP', asset_type: 'STOCK', via_web: false, quote_base_suggestion: null};
    const LINES = [PENCE, PLAIN_STOCK, PLAIN_BOND, PENCE_UNSUGGESTED];

    /** The same split for every line: the first read fills the empty form, every later one agrees with it. */
    const CLASSIFICATION = {sector_area: {distribution: {Telecommunications: 1}}, geographic_area: {distribution: {GBR: 1}}};

    /** The probe's metadata of a line, agreeing with its search result on every field; `suggestion` is what the plugin says of its quote base this time. */
    function metadataOf(line: Pick<Line, 'display_name' | 'asset_type' | 'currency'>, suggestion: Suggestion | null) {
        return {success: true, execution_time_ms: 1, patch_data: {display_name: line.display_name, asset_type: line.asset_type, currency: line.currency, classification_params: CLASSIFICATION}, quote_base_suggestion: suggestion};
    }
    type Metadata = ReturnType<typeof metadataOf>;

    /**
     * The probe, answered by operation: the connection test (current price, history) passes, and the metadata of a line
     * is `metadata[identifier]` — each line's own by default, its search suggestion included. Returns the map, which a
     * case may change between two reads.
     */
    function probeAnswers(overrides: Record<string, Metadata> = {}): Record<string, Metadata> {
        const metadata: Record<string, Metadata> = {...Object.fromEntries(LINES.map((line) => [line.identifier, metadataOf(line, line.quote_base_suggestion ?? null)])), ...overrides};
        vi.mocked(zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post).mockImplementation((async (body: {provider_code: string; identifier: string; operations: string[]}) => {
            const answer = {provider_code: body.provider_code, identifier: body.identifier, total_execution_time_ms: 1};
            if (!body.operations.includes('metadata')) return {...answer, current_price: {success: true, execution_time_ms: 1}, history: {success: true, execution_time_ms: 1}};
            const read = metadata[body.identifier];
            if (!read) throw new Error(`this case gave no metadata for ${body.identifier}`);
            return {...answer, metadata: read};
        }) as never);
        return metadata;
    }

    /** The online search lists every line; any other request gets this file's default answer. */
    function searchListing(): void {
        vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue(quoteSource);
        const encoder = new TextEncoder();
        const events = [{event: 'provider_results', provider_code: LINE_PROVIDER, results: LINES}, {event: 'done'}];
        vi.stubGlobal(
            'fetch',
            vi.fn(async (url: string) => {
                if (!String(url).includes('/assets/provider/search/stream')) return new Response(null, {status: 503});
                // A fresh stream per search, replaying the events as SSE `data:` lines (as the P20 block does).
                const chunks = events.map((event) => encoder.encode(`data: ${JSON.stringify(event)}\n`));
                let next = 0;
                return {ok: true, body: {getReader: () => ({read: async () => (next < chunks.length ? {done: false, value: chunks[next++]} : {done: true, value: undefined}), cancel: vi.fn()})}};
            }),
        );
    }

    /** A blank create form that opens on a search listing every line; returns the probe's metadata map. */
    async function openCreate(overrides: Record<string, Metadata> = {}): Promise<Record<string, Metadata>> {
        const metadata = probeAnswers(overrides);
        searchListing();
        render(AssetModal, {open: true, editMode: false, initialSearchQuery: QUERY, oncreated: vi.fn()});
        await waitForForm();
        return metadata;
    }

    /** The form's online search box. */
    function searchBox(): HTMLElement {
        const box = document.querySelector<HTMLElement>('[data-search-autocomplete]');
        expect(box, 'the form shows its online search').not.toBeNull();
        return within(box!).getByRole('textbox');
    }

    /** Picks `line` among the search results; the focus reopens a dropdown an earlier pick closed. */
    async function pick(line: Line): Promise<void> {
        await fireEvent.focusIn(searchBox());
        const row = await waitFor(
            () => {
                const found = document.querySelector<HTMLElement>(`[data-testid^="asset-search-result-"][data-identifier="${line.identifier}"]`);
                expect(found, `the search lists ${line.identifier}`).not.toBeNull();
                return found!;
            },
            {timeout: 3_000},
        );
        await fireEvent.click(row);
    }

    const quoteBase = () => screen.getByTestId('asset-modal-quote-base-quantity') as HTMLInputElement;
    const suggestionHint = () => screen.queryByTestId('asset-modal-qbq-suggestion-hint');
    const bondHint = () => screen.queryByTestId('asset-modal-bond-qbq-hint');
    const askProvider = () => screen.getByTestId('asset-modal-ask-provider') as HTMLButtonElement;

    /** A sentence of the loaded catalogue. The key must resolve: a missing one echoes itself and would pass for text. */
    function sentence(key: string, values?: Record<string, string | number>): string {
        const text = get(_)(key, values === undefined ? undefined : {values});
        expect(text, `${key} does not resolve: the catalogue is not loaded, or the key is not there yet`).not.toBe(key);
        return text;
    }

    /** What the hint and the note say of a suggestion: with its quote currency, or the plain sentence without one. */
    function suggested(quantity: number, currency: string | null): string {
        return currency ? sentence('assets.modal.quoteBaseSuggested', {provider: LINE_PROVIDER_NAME, currency, quantity}) : sentence('assets.modal.quoteBaseSuggestedPlain', {provider: LINE_PROVIDER_NAME, quantity});
    }

    /** The suggestion hint is on screen, under the field, and says `text`. */
    function expectSuggestionHint(text: string): void {
        const hint = suggestionHint();
        expect(hint, 'the suggestion hint').not.toBeNull();
        expect(quoteBase().compareDocumentPosition(hint!) & Node.DOCUMENT_POSITION_FOLLOWING, 'the hint comes under the field, not above it').toBeTruthy();
        expect(hint).toHaveTextContent(text);
    }

    /** How many metadata reads have ended with nothing to ask: each one says so with `assets.comparison.allMatch`. */
    function agreements(): number {
        const allMatch = sentence('assets.comparison.allMatch');
        return vi.mocked(toasts.success).mock.calls.filter(([message]) => message === allMatch).length;
    }

    /** A value box of the comparison shows `n` — not merely a number that contains its digits. */
    function showsNumber(testId: string, n: number): void {
        expect(screen.getByTestId(testId).textContent ?? '', `${testId} does not show ${n}`).toMatch(new RegExp(`(^|\\D)${n}(\\D|$)`));
    }

    beforeEach(() => {
        // The provider's name, never its code: what the hint and the note must say.
        vi.mocked(getAssetProviderName).mockImplementation((code: string) => (code === LINE_PROVIDER ? LINE_PROVIDER_NAME : code));
    });

    afterEach(() => {
        // Back to the module mocks' own answers for whatever runs next.
        vi.mocked(zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post).mockReset();
        vi.mocked(getAssetProviderName).mockReset();
    });

    describe('create: a search selection', () => {
        it('a pence result sets 100 and its suggestion hint, which names the provider, the quote currency and the quantity', async () => {
            await openCreate();

            await pick(PENCE);
            // Barrier: the selection's own metadata read has ended, with nothing to ask.
            await waitFor(() => expect(agreements()).toBe(1));

            expect(nameInput()).toHaveValue(PENCE.display_name);
            // RED today: the field keeps 1, and there is no such hint.
            expect(quoteBase()).toHaveValue(100);
            expectSuggestionHint(suggested(100, 'GBp'));
            expect(bondHint(), 'a STOCK: no bond hint').toBeNull();
        });

        it('then a result without a suggestion: the type’s default, 1 for a STOCK, and no hint', async () => {
            await openCreate();
            await pick(PENCE);
            await waitFor(() => expect(agreements()).toBe(1));
            // Precondition — RED today: the pence result left 1, with no hint.
            expect(quoteBase()).toHaveValue(100);
            expectSuggestionHint(suggested(100, 'GBp'));

            await pick(PLAIN_STOCK);
            await waitFor(() => expect(agreements()).toBe(2));

            expect(nameInput()).toHaveValue(PLAIN_STOCK.display_name);
            expect(quoteBase()).toHaveValue(1);
            expect(suggestionHint()).toBeNull();
        });

        it('a BOND result without a suggestion: 100 from its type, the bond hint, and the earlier suggestion hint gone', async () => {
            await openCreate();
            await pick(PENCE);
            await waitFor(() => expect(agreements()).toBe(1));
            // Precondition — RED today: no suggestion hint after the pence result.
            expectSuggestionHint(suggested(100, 'GBp'));

            await pick(PLAIN_BOND);
            await waitFor(() => expect(agreements()).toBe(2));

            expect(nameInput()).toHaveValue(PLAIN_BOND.display_name);
            expect(quoteBase()).toHaveValue(100);
            expect(bondHint()).not.toBeNull();
            // The pence line's number, another source: the hint follows the source, not the value.
            expect(suggestionHint()).toBeNull();
        });

        it.each([
            {label: 'a pence result, its suggestion: 100', line: PENCE, expected: 100},
            {label: 'a STOCK result without one, its type’s default: 1', line: PLAIN_STOCK, expected: 1},
            {label: 'a BOND result without one, its type’s default: 100', line: PLAIN_BOND, expected: 100},
        ])('overwrites a quote base the user typed, as it overwrites the name — $label', async ({line, expected}) => {
            await openCreate();
            await fill('asset-modal-quote-base-quantity', '7');
            expect(quoteBase()).toHaveValue(7);

            await pick(line);
            await waitFor(() => expect(agreements()).toBe(1));

            expect(nameInput()).toHaveValue(line.display_name);
            // RED today: a typed value is never replaced — the bond seed, too, stops at a touched field.
            expect(quoteBase()).toHaveValue(expected);
        });

        it('a keystroke in the field hides the suggestion hint', async () => {
            await openCreate();
            await pick(PENCE);
            await waitFor(() => expect(agreements()).toBe(1));
            // Precondition — RED today: there is no hint to hide.
            expectSuggestionHint(suggested(100, 'GBp'));

            await fill('asset-modal-quote-base-quantity', '50');

            await waitFor(() => expect(suggestionHint()).toBeNull());
            expect(quoteBase()).toHaveValue(50);
        });
    });

    describe('create: an import’s prefill, and a manual type change', () => {
        it.each([
            {label: 'a BOND without a quote base: its type’s default, 100 (guard)', prefill: {asset_type: 'BOND'}, expected: 100},
            {label: 'a BOND with a quote base of 0, which is none: its type’s default, 100 (guard)', prefill: {asset_type: 'BOND', quote_base_quantity: 0}, expected: 100},
            {label: 'a BOND with a quote base of 1: the import’s value, never a seed over it', prefill: {asset_type: 'BOND', quote_base_quantity: 1}, expected: 1},
            {label: 'an ETF without a quote base: its type’s default, 1 (guard)', prefill: {asset_type: 'ETF'}, expected: 1},
        ])('a prefill of $label, and no suggestion hint', async ({prefill, expected}) => {
            render(AssetModal, {open: true, editMode: false, prefillData: {display_name: 'Owned imported line', currency: 'EUR', ...prefill}, oncreated: vi.fn()});
            await waitForForm();

            expect(nameInput()).toHaveValue('Owned imported line');
            // RED today for the BOND with 1: the bond seed turns the import's 1 into 100.
            expect(quoteBase()).toHaveValue(expected);
            expect(suggestionHint(), 'an import suggests nothing').toBeNull();
        });

        it('a manual type change does nothing to the field: a blank form made a BOND keeps 1, under the bond hint (guard)', async () => {
            render(AssetModal, {open: true, editMode: false, oncreated: vi.fn()});
            await waitForForm();
            expect(quoteBase()).toHaveValue(1);

            // The type picker, driven as a user does (as the P20 block does for an ETF): BOND sits at the root.
            const field = screen.getByTestId('asset-modal-type');
            const trigger = screen.getByTestId('asset-modal-type-button');
            await fireEvent.click(trigger);
            await fireEvent.click(within(field).getByTestId('asset-type-tree-option-BOND'));
            await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'));

            // Presence barrier: the form holds BOND — the bond hint says so.
            await waitFor(() => expect(bondHint()).not.toBeNull());
            expect(quoteBase()).toHaveValue(1);
            expect(suggestionHint()).toBeNull();
        });
    });

    describe('edit: a search selection overwrites the stored value too (Q-Q6); the asset changes only on Save', () => {
        /** Types `query` into the online search, as a user does: in edit mode it opens empty and searches nothing. */
        async function searchFor(query: string): Promise<void> {
            await fireEvent.input(searchBox(), {target: {value: query}});
        }

        it.each([
            {label: 'a STOCK stored at 1 takes a pence result’s 100, and its hint', stored: 1, line: PENCE, expected: 100, hint: {quantity: 100, currency: 'GBp'}},
            {label: 'a STOCK stored at 100 takes a plain STOCK result’s 1, and no hint', stored: 100, line: PLAIN_STOCK, expected: 1, hint: null},
        ])('$label', async ({stored, line, expected, hint}) => {
            probeAnswers();
            searchListing();
            render(AssetModal, {
                open: true,
                editMode: true,
                editData: {id: 7, display_name: 'Owned stored line', currency: line.currency, asset_type: 'STOCK', quote_base_quantity: stored, active: true},
                onupdated: vi.fn(),
            });
            await waitForForm();
            await waitFor(() => expect(quoteBase()).toHaveValue(stored));

            await searchFor(QUERY);
            await pick(line);
            await waitFor(() => expect(agreements()).toBe(1));

            // The selection overwrote the stored name, as it does in edit mode: the quote base goes the same way.
            expect(nameInput()).toHaveValue(line.display_name);
            // RED today: the stored value stays.
            expect(quoteBase()).toHaveValue(expected);
            if (hint) expectSuggestionHint(suggested(hint.quantity, hint.currency));
            else expect(suggestionHint()).toBeNull();
            expect(patchFn(), 'nothing is written before Save').not.toHaveBeenCalled();
        });
    });

    describe('«Ask the provider»: a different proposal is a checked row, an equal one is nothing', () => {
        /**
         * Opens the pence line as stored — under the quote source, with the type and the quote base a case gives it — and
         * makes the provider's read of it agree on every field but the quote base: `suggestion` is what the plugin says of
         * it, and `providerType` the type the provider names (the stored one by default).
         */
        async function openStored(assetType: string, stored: number, suggestion: Suggestion | null, providerType: string = assetType): Promise<void> {
            probeAnswers({[PENCE.identifier]: metadataOf({...PENCE, asset_type: providerType}, suggestion)});
            vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get).mockResolvedValue(quoteSource);
            render(AssetModal, {
                open: true,
                editMode: true,
                editData: {id: 7, display_name: PENCE.display_name, currency: PENCE.currency, asset_type: assetType, quote_base_quantity: stored, active: true, provider_code: LINE_PROVIDER, provider_identifier: PENCE.identifier, provider_identifier_type: PENCE.identifier_type},
                onupdated: vi.fn(),
            });
            await waitForForm();
            await waitFor(() => expect(quoteBase()).toHaveValue(stored));
            expect(askProvider(), 'precondition: the stored line has a provider to ask').toBeEnabled();
        }

        it.each([
            {label: 'a STOCK at 1, the plugin suggesting 100 GBp', type: 'STOCK', stored: 1, suggestion: {quantity: 100, quote_currency: 'GBp'}, proposed: 100, note: () => suggested(100, 'GBp'), hint: () => suggested(100, 'GBp')},
            {label: 'a STOCK at 1, the plugin suggesting 10 with no currency', type: 'STOCK', stored: 1, suggestion: {quantity: 10}, proposed: 10, note: () => suggested(10, null), hint: () => suggested(10, null)},
            {label: 'a BOND at 1, no suggestion: its type’s default, noted by the bond hint', type: 'BOND', stored: 1, suggestion: null, proposed: 100, note: () => sentence('assets.modal.bondQuoteBaseHint'), hint: null},
            {label: 'a STOCK at 100, no suggestion: its type’s default alone, with no note (Q-Q5 a)', type: 'STOCK', stored: 100, suggestion: null, proposed: 1, note: null, hint: null},
        ])('$label: a checked row; applying it sets the value, and the hint of a suggestion', async ({type, stored, suggestion, proposed, note, hint}) => {
            await openStored(type, stored, suggestion);

            await fireEvent.click(askProvider());

            // RED today: no read proposes a quote base, so no dialog opens at all.
            const checkbox = await screen.findByTestId('comparison-checkbox-quote_base_quantity');
            expect(checkbox, 'every row starts checked, this one too').toBeChecked();
            showsNumber('comparison-current-quote_base_quantity', stored);
            showsNumber('comparison-provider-quote_base_quantity', proposed);
            if (note) expect(screen.getByTestId('comparison-note-quote_base_quantity')).toHaveTextContent(note());
            else expect(screen.queryByTestId('comparison-note-quote_base_quantity'), 'the default of a type other than BOND has no note').toBeNull();
            expect(quoteBase(), 'nothing is filled in silence').toHaveValue(stored);

            await fireEvent.click(screen.getByTestId('comparison-apply'));
            await waitFor(() => expect(screen.queryByTestId('comparison-modal')).toBeNull());

            expect(quoteBase()).toHaveValue(proposed);
            if (hint) expectSuggestionHint(hint());
            else expect(suggestionHint(), 'a type’s default leaves no suggestion hint').toBeNull();
            expect(patchFn(), 'nothing is written before Save').not.toHaveBeenCalled();
        });

        it.each([
            {label: 'a STOCK at 100 its plugin quotes per 100', type: 'STOCK', stored: 100, suggestion: {quantity: 100, quote_currency: 'GBp'}},
            {label: 'a STOCK at 1 its plugin says nothing about', type: 'STOCK', stored: 1, suggestion: null},
            {label: 'a BOND at 100 its plugin says nothing about', type: 'BOND', stored: 100, suggestion: null},
        ])('$label: the proposal equals the field, so there is nothing to ask (guard)', async ({type, stored, suggestion}) => {
            await openStored(type, stored, suggestion);

            await fireEvent.click(askProvider());

            // Barrier: the read has ended, and found the form in agreement on every field.
            await waitFor(() => expect(agreements()).toBe(1));
            expect(screen.queryByTestId('comparison-modal')).toBeNull();
            expect(quoteBase()).toHaveValue(stored);
        });

        it('applying the provider’s type no longer seeds a BOND’s 100: the quote base is a row of its own', async () => {
            await openStored('STOCK', 1, null, 'BOND');

            await fireEvent.click(askProvider());

            // Two rows, both checked: the type (STOCK → BOND), and the quote base that type's default proposes (1 → 100).
            expect(await screen.findByTestId('comparison-checkbox-asset_type')).toBeChecked();
            // RED today: there is no quote base row.
            const quoteBaseRow = await screen.findByTestId('comparison-checkbox-quote_base_quantity');
            expect(quoteBaseRow).toBeChecked();
            showsNumber('comparison-provider-quote_base_quantity', 100);
            expect(screen.getByTestId('comparison-note-quote_base_quantity')).toHaveTextContent(sentence('assets.modal.bondQuoteBaseHint'));

            // The user takes the type and leaves the quote base.
            await fireEvent.click(quoteBaseRow);
            expect(quoteBaseRow).not.toBeChecked();
            await fireEvent.click(screen.getByTestId('comparison-apply'));
            await waitFor(() => expect(screen.queryByTestId('comparison-modal')).toBeNull());

            // Presence barrier: the form holds BOND now — the bond hint says so.
            await waitFor(() => expect(bondHint()).not.toBeNull());
            // RED today as well: applying the type seeds 100 over the untouched 1.
            expect(quoteBase()).toHaveValue(1);
        });
    });

    describe('R1: the line’s latest explicit suggestion answers for a read whose own suggestion failed', () => {
        it('after a pence selection, a read that lost its suggestion proposes nothing — the automatic read, then an asked one', async () => {
            await openCreate({[PENCE.identifier]: metadataOf(PENCE, null)});

            await pick(PENCE);
            // Barrier: the selection's read — its suggestion lost, as a timeout or a pause loses it — has ended with nothing to ask.
            await waitFor(() => expect(agreements()).toBe(1));
            expect(screen.queryByTestId('comparison-modal'), 'the read does not propose to undo the suggestion').toBeNull();
            // RED today: the selection left 1, and no hint.
            expect(quoteBase()).toHaveValue(100);
            expectSuggestionHint(suggested(100, 'GBp'));

            expect(askProvider()).toBeEnabled();
            await fireEvent.click(askProvider());
            await waitFor(() => expect(agreements()).toBe(2));
            expect(screen.queryByTestId('comparison-modal')).toBeNull();
            expect(quoteBase()).toHaveValue(100);
            expectSuggestionHint(suggested(100, 'GBp'));
        });

        it('a suggestion only the metadata brings is a checked row, never a silent fill — and once brought, it answers for its line', async () => {
            const metadata = await openCreate({[PENCE_UNSUGGESTED.identifier]: metadataOf(PENCE_UNSUGGESTED, {quantity: 100, quote_currency: 'GBp'})});

            await pick(PENCE_UNSUGGESTED);

            // The selection's read asks, and the field keeps its type's default meanwhile. RED today: no row, so no dialog.
            expect(await screen.findByTestId('comparison-checkbox-quote_base_quantity')).toBeChecked();
            showsNumber('comparison-provider-quote_base_quantity', 100);
            expect(screen.getByTestId('comparison-note-quote_base_quantity')).toHaveTextContent(suggested(100, 'GBp'));
            expect(quoteBase(), 'nothing is filled in silence').toHaveValue(1);
            expect(suggestionHint()).toBeNull();

            await fireEvent.click(screen.getByTestId('comparison-apply'));
            await waitFor(() => expect(screen.queryByTestId('comparison-modal')).toBeNull());
            expect(quoteBase()).toHaveValue(100);
            expectSuggestionHint(suggested(100, 'GBp'));

            // The next read of the same line loses its suggestion: the one the last read brought still answers for it.
            metadata[PENCE_UNSUGGESTED.identifier] = metadataOf(PENCE_UNSUGGESTED, null);
            expect(askProvider()).toBeEnabled();
            await fireEvent.click(askProvider());
            await waitFor(() => expect(agreements()).toBe(1));
            expect(screen.queryByTestId('comparison-modal')).toBeNull();
            expect(quoteBase()).toHaveValue(100);
        });

        it('the hint and the suggestion belong to their line: another identifier hides the hint, keeps the value, and its read proposes the type’s default', async () => {
            await openCreate({VOD: metadataOf(PENCE, null)});
            await pick(PENCE);
            await waitFor(() => expect(agreements()).toBe(1));
            // Precondition — RED today: the field keeps 1, with no hint.
            expect(quoteBase()).toHaveValue(100);
            expectSuggestionHint(suggested(100, 'GBp'));

            // The same provider, another line: the suggestion was made for VOD.L, not for VOD.
            await fill('provider-identifier', 'VOD');
            await waitFor(() => expect(suggestionHint()).toBeNull());
            expect(quoteBase(), 'only the user, a selection or an applied row changes the value').toHaveValue(100);

            expect(askProvider()).toBeEnabled();
            await fireEvent.click(askProvider());

            // VOD's read brings no suggestion, and VOD.L's does not answer for it: a STOCK's default, asked as a row.
            expect(await screen.findByTestId('comparison-checkbox-quote_base_quantity')).toBeChecked();
            showsNumber('comparison-current-quote_base_quantity', 100);
            showsNumber('comparison-provider-quote_base_quantity', 1);
            expect(screen.queryByTestId('comparison-note-quote_base_quantity'), 'a STOCK’s default has no note').toBeNull();
        });
    });
});
