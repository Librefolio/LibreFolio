// @vitest-environment jsdom
/**
 * R1 duplicate-name handling through the real BrokerForm, BrokerModal and trySave.
 * Only API/reference stores/toasts/notify are bounded fixtures. The synthetic
 * catalogue exercises real interpolation without asserting translated prose.
 * HTTP errors and HTTP-success/per-item failures deliberately remain different
 * contracts.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {addMessages, dictionary} from 'svelte-i18n';
import {get} from 'svelte/store';
import {getClientSessionUserId, transitionClientSession} from '$lib/stores/app/clientSession';
import BrokerModal from './BrokerModal.svelte';
import {trySave} from '$lib/utils/trySave';
import {schemas} from '$lib/api/generated';

const mocks = vi.hoisted(() => ({
    create: vi.fn(),
    update: vi.fn(),
    plugins: vi.fn(),
    merge: vi.fn(),
    loadIcon: vi.fn(),
    notify: vi.fn(),
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));

vi.mock('$lib/api', () => ({
    zodiosApi: {
        create_brokers_api_v1_brokers_post: mocks.create,
        update_broker_api_v1_brokers__broker_id__patch: mocks.update,
        list_plugins_api_v1_brokers_import_plugins_get: mocks.plugins,
    },
    axiosInstance: {},
}));
vi.mock('$lib/stores/reference/brokerStore', () => ({
    mergeBrokers: mocks.merge,
    ensureBrokerIconFieldsLoaded: mocks.loadIcon,
}));
vi.mock('$lib/stores/app/notify.svelte', () => ({
    notify: mocks.notify,
}));
vi.mock('$lib/stores/app/settings', async () => {
    const {readable} = await import('svelte/store');
    return {userSettings: {...readable({base_currency: 'EUR'}), load: vi.fn()}};
});
vi.mock('$lib/stores/app/toastStore.svelte', () => ({toasts: mocks.toasts}));
vi.mock('$lib/utils/trySave', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/utils/trySave')>();
    return {...actual, trySave: vi.fn(actual.trySave)};
});

const NAME = `R1 O'Neil <b>desk</b> & "sons"`;
const OWNER = `D'Angelo <i>owner</i>`;
const ESCAPED_NAME = 'R1 O&#39;Neil &lt;b&gt;desk&lt;/b&gt; &amp; &quot;sons&quot;';
const RECOVERY = 'To resolve this, rename the existing broker or choose a different name for the broker you are adding.';
const BASE_INITIAL_DATA = {
    description: '  Synthetic R1 draft  ',
    allow_cash_overdraft: true,
    opened_at: '2020-01-02',
};
const REOPENED_INITIAL_DATA = {
    name: 'Fresh reopened draft',
    description: 'Reopened synthetic draft',
    allow_cash_overdraft: false,
    allow_asset_shorting: true,
    is_active: true,
    opened_at: '2021-03-04',
};
const submitted = {
    name: NAME,
    description: 'Synthetic R1 draft',
    portal_url: undefined,
    icon_url: undefined,
    default_import_plugin: undefined,
    allow_cash_overdraft: true,
    allow_asset_shorting: false,
    is_active: true,
    opened_at: '2020-01-02',
    initial_balances: undefined,
};
let originalDictionary = get(dictionary);
let previousSession = getClientSessionUserId();

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((yes, no) => {
        resolve = yes;
        reject = no;
    });
    return {promise, resolve, reject};
}

function mountModal(overrides: Record<string, unknown> = {}) {
    const callbacks = {oncreated: vi.fn(), onupdated: vi.fn(), onclose: vi.fn()};
    const view = render(BrokerModal, {
        isOpen: true,
        mode: 'create',
        initialData: BASE_INITIAL_DATA,
        ...callbacks,
        ...overrides,
    });
    return {callbacks, view};
}

beforeEach(async () => {
    await setupI18n();
    originalDictionary = structuredClone(get(dictionary));
    addMessages('en', {
        brokers: {
            created: 'created-marker[{name}]',
            duplicateNameOwn: 'duplicate-own[{name}]',
            duplicateNameOwned: 'duplicate-owned[{name}][{owner}]',
            duplicateNameExists: 'duplicate-exists[{name}]',
            duplicateNameRecovery: 'recovery-marker',
        },
    });
    vi.clearAllMocks();
    mocks.create.mockReset();
    mocks.update.mockReset();
    mocks.plugins.mockResolvedValue([]);
    mocks.loadIcon.mockResolvedValue(undefined);
    mocks.notify.mockReset();
    previousSession = getClientSessionUserId();
    transitionClientSession('r1-broker-modal-owner');
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.stubGlobal(
        'fetch',
        vi.fn(() => {
            throw new Error('BrokerModal component tests must not reach the network');
        }),
    );
});

afterEach(async () => {
    try {
        await cleanup();
        expect(fetch).not.toHaveBeenCalled();
        expect(mocks.update).not.toHaveBeenCalled();
    } finally {
        dictionary.set(originalDictionary);
        transitionClientSession(previousSession);
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    }
});

async function mountAndSubmit() {
    const {callbacks} = mountModal();
    expect(screen.getByTestId('broker-modal')).toBeVisible();
    const name = screen.getByTestId('broker-name-input');
    await fireEvent.input(name, {target: {value: `  ${NAME}  `}});
    expect(name).toHaveValue(`  ${NAME}  `);
    expect(screen.getByTestId('broker-form-submit')).toBeEnabled();
    await fireEvent.click(screen.getByTestId('broker-form-submit'));
    await waitFor(() => expect(screen.getByTestId('info-banner-error')).toBeVisible());
    await waitFor(() => expect(screen.getByTestId('broker-form-submit')).toBeEnabled());
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(mocks.create).toHaveBeenCalledWith([submitted]);
    expect(trySave).toHaveBeenCalledTimes(1);
    return callbacks;
}

function expectRetained(callbacks: Awaited<ReturnType<typeof mountAndSubmit>>) {
    expect(screen.getByTestId('broker-modal')).toBeVisible();
    expect(screen.getByTestId('broker-name-input')).toHaveValue(`  ${NAME}  `);
    expect(callbacks.onclose).not.toHaveBeenCalled();
    expect(callbacks.oncreated).not.toHaveBeenCalled();
    expect(callbacks.onupdated).not.toHaveBeenCalled();
    expect(mocks.merge).not.toHaveBeenCalled();
    expect(mocks.notify).not.toHaveBeenCalled();
    expect(mocks.toasts.success).not.toHaveBeenCalled();
}

describe('BrokerModal — known duplicate responses', () => {
    it.each([
        {kind: 'self', message: `You already have a broker named '${NAME}'`, key: 'duplicate-own'},
        {kind: 'other owner', message: `Broker '${NAME}' already exists (owned by '${OWNER}')`, key: 'duplicate-owned'},
        {kind: 'unknown owner', message: `Broker with name '${NAME}' already exists`, key: 'duplicate-exists'},
    ])('localizes the entire $kind per-item failure without changing its successful HTTP status', async ({message, key}) => {
        const backendMessage = `${message}. ${RECOVERY}`;
        const response = schemas.BRBulkCreateResponse.parse({
            results: [{broker_id: null, name: NAME, success: false, error: backendMessage}],
            success_count: 0,
            errors: [],
        });
        mocks.create.mockResolvedValueOnce(response);
        const callbacks = await mountAndSubmit();
        const banner = screen.getByTestId('info-banner-error');
        const expected = `${key}[${NAME}]${key === 'duplicate-owned' ? `[${OWNER}]` : ''} recovery-marker`;
        expect(banner.textContent?.trim()).toBe(expected);
        // The synthetic <b>/<i> values stay text, not executable/rendered markup.
        expect(banner.querySelector('b, i')).toBeNull();
        expect(mocks.toasts.error).not.toHaveBeenCalled();
        expectRetained(callbacks);
        // This collection contains exactly the one real trySave call asserted above.
        expect(await vi.mocked(trySave).mock.results[0].value).toEqual({status: 'success', data: response});
    });

    it('rejects array-shaped errors at the real response schema boundary', () => {
        expect(
            schemas.BRBulkCreateResponse.safeParse({
                results: [{broker_id: null, name: NAME, success: false, error: [`You already have a broker named '${NAME}'. ${RECOVERY}`]}],
                success_count: 0,
                errors: [],
            }).success,
        ).toBe(false);
        expect(mocks.create).not.toHaveBeenCalled();
    });

    it('localizes a 409 race once, escapes the success toast, and emits broker.created before callbacks on retry', async () => {
        const failure = {response: {status: 409, data: {detail: 'A broker with that name already exists'}}};
        mocks.create.mockRejectedValueOnce(failure);
        const callbacks = await mountAndSubmit();
        expect(screen.getByTestId('info-banner-error').textContent?.trim()).toBe(`duplicate-exists[${NAME}] recovery-marker`);
        expect(screen.getByTestId('info-banner-error').querySelector('b')).toBeNull();
        expect(mocks.toasts.error).toHaveBeenCalledExactlyOnceWith(`duplicate-exists[${ESCAPED_NAME}] recovery-marker`);
        expectRetained(callbacks);
        expect(await vi.mocked(trySave).mock.results[0].value).toEqual({
            status: 'error',
            message: 'A broker with that name already exists',
            error: failure,
            status_code: 409,
        });

        mocks.create.mockResolvedValueOnce(
            schemas.BRBulkCreateResponse.parse({
                results: [{broker_id: 8201, name: NAME, success: true, error: null}],
                success_count: 1,
                errors: [],
            }),
        );
        await fireEvent.click(screen.getByTestId('broker-form-submit'));
        await waitFor(() => expect(callbacks.oncreated).toHaveBeenCalledExactlyOnceWith({id: 8201}));
        expect(mocks.create).toHaveBeenCalledTimes(2);
        expect(trySave).toHaveBeenCalledTimes(2);
        expect(mocks.create).toHaveBeenNthCalledWith(2, [submitted]);
        expect(mocks.merge).toHaveBeenCalledExactlyOnceWith([{id: 8201, ...submitted}]);
        expect(mocks.notify).toHaveBeenCalledExactlyOnceWith({
            name: 'broker.created',
            detail: {brokerId: 8201},
            toast: {variant: 'success', message: `created-marker[${ESCAPED_NAME}]`},
        });
        expect(mocks.toasts.success).not.toHaveBeenCalled();
        expect(mocks.notify.mock.invocationCallOrder[0]).toBeLessThan(callbacks.oncreated.mock.invocationCallOrder[0]);
        expect(callbacks.oncreated.mock.invocationCallOrder[0]).toBeLessThan(callbacks.onclose.mock.invocationCallOrder[0]);
        expect(callbacks.onclose).toHaveBeenCalledTimes(1);
        expect(mocks.toasts.error).toHaveBeenCalledTimes(1);
    });
});

describe('BrokerModal — unknown failures are not duplicate-name matches', () => {
    it.each([
        {status: 500, message: 'Synthetic upstream save failure'},
        {status: 409, message: `Broker 'Different synthetic name' already exists (owned by '${OWNER}')`},
    ])('preserves the current trySave path for HTTP $status', async ({status, message}) => {
        const failure = {response: {status, data: {detail: message}}};
        mocks.create.mockRejectedValueOnce(failure);
        const callbacks = await mountAndSubmit();
        expect(screen.getByTestId('info-banner-error').textContent?.trim()).toBe(message);
        expect(mocks.toasts.error).toHaveBeenCalledExactlyOnceWith(message);
        expectRetained(callbacks);
        expect(await vi.mocked(trySave).mock.results[0].value).toEqual({status: 'error', message, error: failure, status_code: status});
    });

    it('preserves an unknown per-item message without turning it into an HTTP error toast', async () => {
        const response = schemas.BRBulkCreateResponse.parse({
            results: [{broker_id: null, name: NAME, success: false, error: 'Synthetic per-item rejection'}],
            success_count: 0,
            errors: [],
        });
        mocks.create.mockResolvedValueOnce(response);
        const callbacks = await mountAndSubmit();
        expect(screen.getByTestId('info-banner-error').textContent?.trim()).toBe('Synthetic per-item rejection');
        expect(mocks.toasts.error).not.toHaveBeenCalled();
        expectRetained(callbacks);
        expect(await vi.mocked(trySave).mock.results[0].value).toEqual({status: 'success', data: response});
    });
});

describe('BrokerModal — opening-context resets and stale responses', () => {
    it('clears the old error when reopened with a fresh draft', async () => {
        mocks.create.mockRejectedValueOnce({response: {status: 409, data: {detail: 'A broker with that name already exists'}}});
        const {callbacks, view} = mountModal();

        await fireEvent.input(screen.getByTestId('broker-name-input'), {target: {value: `  ${NAME}  `}});
        await fireEvent.click(screen.getByTestId('broker-form-submit'));
        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toBeVisible());
        expect(mocks.notify).not.toHaveBeenCalled();

        await view.rerender({
            isOpen: false,
            mode: 'create',
            initialData: BASE_INITIAL_DATA,
            onclose: callbacks.onclose,
            oncreated: callbacks.oncreated,
            onupdated: callbacks.onupdated,
        });
        await waitFor(() => expect(screen.queryByTestId('broker-modal')).toBeNull());

        await view.rerender({
            isOpen: true,
            mode: 'create',
            initialData: REOPENED_INITIAL_DATA,
            onclose: callbacks.onclose,
            oncreated: callbacks.oncreated,
            onupdated: callbacks.onupdated,
        });
        await waitFor(() => expect(screen.getByTestId('broker-modal')).toBeVisible());
        expect(screen.queryByTestId('info-banner-error')).toBeNull();
        expect(screen.getByTestId('broker-name-input')).toHaveValue(REOPENED_INITIAL_DATA.name);
        expect(callbacks.onclose).not.toHaveBeenCalled();
    });

    it('keeps the draft intact across unrelated rerenders while the modal stays open', async () => {
        const {callbacks, view} = mountModal();
        const name = screen.getByTestId('broker-name-input');
        await fireEvent.input(name, {target: {value: 'Draft still here'}});
        expect(name).toHaveValue('Draft still here');

        await view.rerender({
            isOpen: true,
            mode: 'create',
            brokerId: null,
            initialData: BASE_INITIAL_DATA,
            zIndex: 61,
            onclose: callbacks.onclose,
            oncreated: callbacks.oncreated,
            onupdated: callbacks.onupdated,
        });
        expect(screen.getByTestId('broker-modal')).toBeVisible();
        expect(screen.getByTestId('broker-name-input')).toHaveValue('Draft still here');
        expect(screen.queryByTestId('info-banner-error')).toBeNull();
    });

    it('ignores a late success from the previous opening after a close and reopen', async () => {
        const stale = deferred<unknown>();
        const staleResult = schemas.BRBulkCreateResponse.parse({
            results: [{broker_id: 8201, name: NAME, success: true, error: null}],
            success_count: 1,
            errors: [],
        });
        mocks.create.mockReturnValueOnce(stale.promise as never);
        const {callbacks, view} = mountModal();

        await fireEvent.input(screen.getByTestId('broker-name-input'), {target: {value: `  ${NAME}  `}});
        await fireEvent.click(screen.getByTestId('broker-form-submit'));
        await waitFor(() => expect(screen.getByTestId('broker-form-submit')).toBeDisabled());

        await view.rerender({
            isOpen: false,
            mode: 'create',
            initialData: BASE_INITIAL_DATA,
            onclose: callbacks.onclose,
            oncreated: callbacks.oncreated,
            onupdated: callbacks.onupdated,
        });
        await waitFor(() => expect(screen.queryByTestId('broker-modal')).toBeNull());
        await view.rerender({
            isOpen: true,
            mode: 'create',
            initialData: REOPENED_INITIAL_DATA,
            onclose: callbacks.onclose,
            oncreated: callbacks.oncreated,
            onupdated: callbacks.onupdated,
        });
        await waitFor(() => expect(screen.getByTestId('broker-modal')).toBeVisible());
        expect(screen.getByTestId('broker-name-input')).toHaveValue(REOPENED_INITIAL_DATA.name);
        stale.resolve(staleResult);
        await stale.promise;
        await waitFor(() => expect(screen.getByTestId('broker-form-submit')).toBeEnabled());

        expect(screen.getByTestId('broker-modal')).toBeVisible();
        expect(screen.queryByTestId('info-banner-error')).toBeNull();
        expect(screen.getByTestId('broker-name-input')).toHaveValue(REOPENED_INITIAL_DATA.name);
        expect(mocks.notify).not.toHaveBeenCalled();
        expect(mocks.toasts.success).not.toHaveBeenCalled();
        expect(callbacks.oncreated).not.toHaveBeenCalled();
        expect(callbacks.onclose).not.toHaveBeenCalled();
        expect(mocks.merge).not.toHaveBeenCalled();
    });
});
