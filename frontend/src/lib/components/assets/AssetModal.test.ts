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
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';

// --- Mocks --------------------------------------------------------------
// zodiosApi has dozens of methods; a Proxy lazily mints (and caches) a spy per
// property, so `vi.mocked(zodiosApi.foo)` retrieves the same fn to program.
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
    // A fake fetch for the embedded AssetSearchAutocomplete (never streamed here).
    global.fetch = vi.fn(async () => ({ok: false, body: null})) as never;
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
