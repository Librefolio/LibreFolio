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
 *     component test.
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
import {zodiosApi} from '$lib/api';
import {toasts} from '$lib/stores/app/toastStore.svelte';

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
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async () => new Response(null, {status: 503})));
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

        await waitFor(() => expect(oncreated).toHaveBeenCalledWith(42));
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

    async function mountCreation(id: number, name: string, linkCreatedAsset?: boolean) {
        vi.mocked(zodiosApi.create_assets_bulk_api_v1_assets_post).mockResolvedValueOnce(createdResponse(id, name));
        const oncreated = vi.fn<(assetId: number) => void>();
        const goto = vi.spyOn(navigation, 'goto');
        const hrefBefore = window.location.href;
        render(AssetModal, {open: true, oncreated, ...(linkCreatedAsset === undefined ? {} : {linkCreatedAsset})});
        await waitForForm();
        await fill('asset-modal-display-name', name);
        await waitFor(() => expect(nameInput()).toHaveValue(name));
        await waitFor(() => expect(saveBtn()).toBeEnabled());
        return {oncreated, goto, hrefBefore};
    }

    async function expectCreationClosed(oncreated: (assetId: number) => void, id: number) {
        await waitFor(() => expect(oncreated).toHaveBeenCalledWith(id));
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

        await expectCreationClosed(oncreated, id);
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

        await expectCreationClosed(oncreated, id);
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

        await expectCreationClosed(oncreated, id);
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

            await expectCreationClosed(oncreated, id);
            expect(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).toHaveBeenCalledTimes(1);
            expect(zodiosApi.assign_providers_bulk_api_v1_assets_provider_post).toHaveBeenCalledWith([
                {asset_id: id, provider_code: PROVIDER_CODE, identifier: PROVIDER_IDENTIFIER, identifier_type: 'TICKER', provider_params: null},
            ]);
            expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).toHaveBeenCalledTimes(1);
            expect(zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post).toHaveBeenCalledWith([
                {asset_id: id, date_range: {start: 'resume', end: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/)}},
            ]);
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

        await expectCreationClosed(oncreated, id);
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
        await waitFor(() => expect(oncreated).toHaveBeenCalledWith(99));
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
        await waitFor(() => expect(oncreated).toHaveBeenCalledWith(101));
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
