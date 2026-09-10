// @vitest-environment jsdom
/**
 * Creation owns configuration; the detached sync owns its eventual feedback.
 * Drive the real modal and route picker through DOM, replacing only API/reference
 * data. Every in-flight request is released by the test, never by a clock.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {ChainStep, ProviderInfo} from '$lib/utils/currency/currencyGraph';

const feedback = vi.hoisted(() => ({
    notices: [] as Array<{variant: string; message: string}>,
}));

vi.mock('$lib/api', () => ({
    zodiosApi: {
        create_routes_bulk_api_v1_fx_providers_routes_post: vi.fn(),
        delete_routes_bulk_api_v1_fx_providers_routes_delete: vi.fn(),
        list_routes_api_v1_fx_providers_routes_get: vi.fn(),
        sync_rates_api_v1_fx_currencies_sync_post: vi.fn(),
    },
}));
vi.mock('$lib/stores/currencyGraphStore', () => ({
    findConversionPaths: vi.fn(),
    getCachedFxProviders: vi.fn(),
}));
vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn().mockResolvedValue(undefined),
    getAllCurrencies: vi.fn(),
    getCurrencyInfo: vi.fn(),
}));
vi.mock('$lib/stores/reference/fxRoutesStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/fxRoutesStore')>()),
    ensureFxRoutesLoaded: vi.fn().mockResolvedValue(undefined),
    getConfiguredPairSlugs: vi.fn(() => new Set<string>()),
    getConfiguredCurrencySet: vi.fn(() => new Set<string>()),
}));
vi.mock('$lib/stores/fxStoreRegistry', () => ({
    getRegisteredPairs: vi.fn(() => []),
    createPairSlug: (base: string, quote: string) => [base, quote].sort().join('-'),
    getFxStore: vi.fn(() => ({invalidateAll: vi.fn()})),
}));
vi.mock('$lib/utils/sync/syncToastHelpers', async (importOriginal) => {
    const original = await importOriginal<typeof import('$lib/utils/sync/syncToastHelpers')>();
    return {...original, buildFxSyncToast: vi.fn(original.buildFxSyncToast)};
});
vi.mock('$lib/stores/app/notify.svelte', async (importOriginal) => {
    const original = await importOriginal<typeof import('$lib/stores/app/notify.svelte')>();
    return {...original, notify: vi.fn(original.notify)};
});
vi.mock('$lib/stores/app/toastStore.svelte', () => {
    const show = vi.fn((variant: string, message: string) => {
        feedback.notices.push({variant, message});
        return 'owned-creation-toast';
    });
    return {
        toasts: {
            show,
            success: (message: string) => show('success', message),
            warning: (message: string) => show('warning', message),
            info: (message: string) => show('info', message),
            error: (message: string) => show('error', message),
        },
    };
});

import FxPairAddModal from './FxPairAddModal.svelte';
import {zodiosApi} from '$lib/api';
import {findConversionPaths, getCachedFxProviders} from '$lib/stores/currencyGraphStore';
import {getAllCurrencies, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {getConfiguredPairSlugs} from '$lib/stores/reference/fxRoutesStore';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import {buildFxSyncToast} from '$lib/utils/sync/syncToastHelpers';
import {notify} from '$lib/stores/app/notify.svelte';

const createRoutes = vi.mocked(zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post);
const deleteRoutes = vi.mocked(zodiosApi.delete_routes_bulk_api_v1_fx_providers_routes_delete);
const listRoutes = vi.mocked(zodiosApi.list_routes_api_v1_fx_providers_routes_get);
const syncRates = vi.mocked(zodiosApi.sync_rates_api_v1_fx_currencies_sync_post);
const RANGE = {dateStart: '2024-03-01', dateEnd: '2024-03-31'};
const DIRECT: ChainStep[] = [{from: 'EUR', to: 'GBP', provider: 'ECB'}];
const CHAIN: ChainStep[] = [
    {from: 'EUR', to: 'USD', provider: 'ECB'},
    {from: 'USD', to: 'GBP', provider: 'FED'},
];
const PROVIDERS: ProviderInfo[] = [
    {code: 'ECB', name: 'Fixture ECB', base_currency: 'EUR', base_currencies: ['EUR'], target_currencies: ['GBP', 'USD']},
    {code: 'FED', name: 'Fixture FED', base_currency: 'USD', base_currencies: ['USD'], target_currencies: ['GBP']},
];
const CURRENCIES = [
    {code: 'EUR', flag_emoji: '🇪🇺'},
    {code: 'GBP', flag_emoji: '🇬🇧'},
    {code: 'USD', flag_emoji: '🇺🇸'},
    {code: 'JPY', flag_emoji: '🇯🇵'},
].map((currency) => ({...currency, name: currency.code, symbol: currency.code, country_codes: [], country_names: []}));

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((yes, no) => {
        resolve = yes;
        reject = no;
    });
    return {promise, resolve, reject};
}

type SyncResponse = Awaited<ReturnType<typeof zodiosApi.sync_rates_api_v1_fx_currencies_sync_post>>;

function syncResponse(...pairs: string[]): SyncResponse {
    return {
        results: pairs.map((pair) => ({pair, status: 'ok', points_fetched: 8, points_changed: 3})),
        success_count: pairs.length,
        date_range: {start: RANGE.dateStart, end: RANGE.dateEnd},
        total_points_changed: pairs.length * 3,
    };
}

function creationResponse(items: Parameters<typeof zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post>[0]) {
    return {
        results: items.map((item) => ({
            ...item,
            success: true,
            action: 'created',
            is_chain: item.chain_steps.length > 1,
            providers_used: [...new Set(item.chain_steps.map((step) => step.provider))].sort(),
        })),
        success_count: items.length,
        error_count: 0,
    };
}

function mount(props: Partial<ComponentProps<typeof FxPairAddModal>> = {}) {
    const oncreated = vi.fn();
    const onsynced = vi.fn();
    const onclose = vi.fn();
    const view = render(FxPairAddModal, {open: true, initialBase: 'EUR', initialQuote: 'GBP', ...RANGE, oncreated, onsynced, onclose, ...props});
    return {...view, oncreated, onsynced, onclose};
}

async function ready() {
    await waitFor(() => {
        expect(findConversionPaths).toHaveBeenCalled();
        expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
        expect(screen.queryByTestId('fx-route-loading')).toBeNull();
    });
}

async function pickRoute(kind: 'direct' | 'chain') {
    await ready();
    await fireEvent.click(screen.getByTestId('fx-route-picker-toggle'));
    const picker = screen.getByTestId('fx-route-picker');
    if (kind === 'chain') {
        await fireEvent.click(within(picker).getByTestId('fx-route-chain-toggle-2'));
        await fireEvent.click(within(picker).getByTestId('fx-route-chain-2step-ECB-FED'));
    } else {
        await fireEvent.click(within(picker).getByTestId('fx-route-direct-ECB'));
    }
}

async function save() {
    const button = screen.getByTestId('fx-add-pair-save');
    expect(button).toBeEnabled();
    await fireEvent.click(button);
}

async function closed() {
    await waitFor(() => expect(screen.queryByTestId('fx-add-pair-modal')).not.toBeInTheDocument());
}

/** Only this file's notifications, not a shared UI/global toast count. */
function onlyNotice() {
    expect(feedback.notices).toHaveLength(1);
    const [notice] = feedback.notices;
    return notice!;
}

function expectLinkedPair(message: string, slug: string) {
    const html = document.createElement('div');
    html.innerHTML = message;
    const links = within(html).getAllByTestId('toast-fx-link').filter((candidate) => candidate.getAttribute('href') === `/fx/${slug}`);
    expect(links).toHaveLength(1);
    const [link] = links;
    expect(link).toHaveAttribute('href', `/fx/${slug}`);
    const [base, quote] = slug.split('-');
    expect(link!.textContent).toBe(`${base} / ${quote}`);
    const baseFlag = CURRENCIES.find((currency) => currency.code === base)!.flag_emoji;
    const quoteFlag = CURRENCIES.find((currency) => currency.code === quote)!.flag_emoji;
    const plain = html.textContent!;
    expect(plain.indexOf(baseFlag)).toBeGreaterThanOrEqual(0);
    expect(plain.indexOf(baseFlag)).toBeLessThan(plain.indexOf(`${base} / ${quote}`));
    expect(plain.indexOf(quoteFlag)).toBeGreaterThan(plain.indexOf(`${base} / ${quote}`));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    feedback.notices.length = 0;
    transitionClientSession('fx-creation-component-owner');
    createRoutes.mockReset().mockImplementation(async (items) => creationResponse(items));
    deleteRoutes.mockReset().mockResolvedValue({
        results: [{success: true, deleted_count: 1, base: 'EUR', quote: 'GBP'}],
        success_count: 1,
        total_deleted: 1,
    });
    listRoutes.mockReset().mockResolvedValue({items: []});
    syncRates.mockReset().mockResolvedValue(syncResponse('EUR-GBP'));
    // Deliberate UI-only metadata: the POST must pick the three wire fields,
    // not spread whatever the route picker happens to return.
    vi.mocked(findConversionPaths).mockResolvedValue([DIRECT, CHAIN].map((route) => route.map((step) => ({...step, fixtureDisplayLabel: 'not-a-wire-field'}))));
    vi.mocked(getCachedFxProviders).mockReturnValue(PROVIDERS);
    vi.mocked(getAllCurrencies).mockReturnValue(CURRENCIES);
    vi.mocked(getCurrencyInfo).mockImplementation((code) => {
        const currency = CURRENCIES.find((item) => item.code === code);
        if (!currency) throw new Error(`Unexpected currency in owned fixture: ${code}`);
        return currency;
    });
    vi.mocked(getConfiguredPairSlugs).mockReturnValue(new Set());
});

describe('FxPairAddModal — configuration before background sync', () => {
    it('keeps creation pending until the POST commits and ignores a second save activation', async () => {
        const posted = deferred<Awaited<ReturnType<typeof zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post>>>();
        const pending = deferred<SyncResponse>();
        createRoutes.mockReturnValue(posted.promise);
        syncRates.mockReturnValue(pending.promise);
        const {oncreated, onsynced} = mount();
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(createRoutes).toHaveBeenCalledTimes(1));
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            const button = screen.getByTestId('fx-add-pair-save');
            expect(button).toBeDisabled();
            await fireEvent.click(button);
            expect(oncreated).not.toHaveBeenCalled();
            expect(syncRates).not.toHaveBeenCalled();
            expect(feedback.notices).toEqual([]);

            posted.resolve(creationResponse([{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]));
            await closed();
            await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]]);
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP'], start: RANGE.dateStart, end: RANGE.dateEnd}]);
            expect(oncreated).toHaveBeenCalledTimes(1);
            pending.resolve(syncResponse('EUR-GBP'));
            await waitFor(() => expect(onsynced).toHaveBeenCalledTimes(1));
            expect(oncreated).toHaveBeenCalledTimes(1);
        } finally {
            posted.resolve(creationResponse([{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]));
            pending.resolve(syncResponse('EUR-GBP'));
            await Promise.all([posted.promise, pending.promise]);
        }
    });

    it.each(['direct', 'chain'] as const)('closes after %s creation, before one sync resolves, and reports creation only once', async (kind) => {
        const pending = deferred<SyncResponse>();
        syncRates.mockReturnValue(pending.promise);
        const {oncreated, onsynced, onclose} = mount();
        try {
            await pickRoute(kind);
            if (kind === 'chain') {
                await fireEvent.click(screen.getByTestId('fx-add-pair-intermediates'));
                expect(screen.getByTestId('fx-add-pair-intermediates')).toBeChecked();
            }
            await save();
            await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
            await closed();

            const expectedPairs = kind === 'chain' ? ['EUR-GBP', 'EUR-USD', 'GBP-USD'] : ['EUR-GBP'];
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: expectedPairs, start: RANGE.dateStart, end: RANGE.dateEnd}]);
            expect(createRoutes).toHaveBeenCalledTimes(1);
            // Deep equality is an allowlist: presentation-only ChainStep data,
            // dates, session IDs and callback options cannot leak into the POST.
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([
                kind === 'chain'
                    ? [
                          {base: 'EUR', quote: 'GBP', chain_steps: CHAIN, priority: 1},
                          {base: 'EUR', quote: 'USD', chain_steps: [CHAIN[0]], priority: 1},
                          {base: 'GBP', quote: 'USD', chain_steps: [CHAIN[1]], priority: 1},
                      ]
                    : [{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}],
            ]);
            expect(oncreated).toHaveBeenCalledTimes(1);
            expect(oncreated).toHaveBeenCalledWith({base: 'EUR', quote: 'GBP', slug: 'EUR-GBP', hasRealProvider: true, autoSyncStarted: true});
            expect(onclose).toHaveBeenCalledTimes(1);
            expect(onsynced).not.toHaveBeenCalled();
            expect(feedback.notices).toEqual([]);

            // Reverse response order deliberately: the primary pair is not row 0.
            pending.resolve(syncResponse(...[...expectedPairs].reverse()));
            await waitFor(() => expect(onsynced).toHaveBeenCalledTimes(1));
            expect(oncreated).toHaveBeenCalledTimes(1);
            expect(syncRates).toHaveBeenCalledTimes(1);
            expect(onlyNotice().variant).toBe('success');
            expectLinkedPair(onlyNotice().message, 'EUR-GBP');
            expect(buildFxSyncToast).toHaveBeenCalledWith(
                expect.objectContaining({pair: 'EUR-GBP', status: 'ok'}),
                'EUR-GBP',
                expect.any(Function),
                undefined,
                expect.any(Function),
                {outerFlags: true, linkToDetail: true},
            );
        } finally {
            pending.resolve(syncResponse('EUR-GBP', 'EUR-USD', 'GBP-USD'));
            await pending.promise;
        }
    });

    it('does not re-create or sync existing intermediates', async () => {
        vi.mocked(getConfiguredPairSlugs).mockReturnValue(new Set(['EUR-USD']));
        const {onsynced} = mount();
        await pickRoute('chain');
        await fireEvent.click(screen.getByTestId('fx-add-pair-intermediates'));
        syncRates.mockResolvedValue(syncResponse('GBP-USD', 'EUR-GBP'));
        await save();
        await waitFor(() => expect(onsynced).toHaveBeenCalledTimes(1));
        expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([
            [
                {base: 'EUR', quote: 'GBP', chain_steps: CHAIN, priority: 1},
                {base: 'GBP', quote: 'USD', chain_steps: [CHAIN[1]], priority: 1},
            ],
        ]);
        expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP', 'GBP-USD'], start: RANGE.dateStart, end: RANGE.dateEnd}]);
    });

    it.each([
        {name: 'MANUAL', route: false, dates: RANGE},
        {name: 'no start date', route: true, dates: {...RANGE, dateStart: ''}},
        {name: 'no end date', route: true, dates: {...RANGE, dateEnd: ''}},
    ])('shows one linked creation toast without sync for $name', async ({route, dates}) => {
        const {oncreated, onsynced} = mount(dates);
        if (route) await pickRoute('direct');
        else await ready();
        await save();
        await closed();
        expect(oncreated).toHaveBeenCalledTimes(1);
        expect(oncreated).toHaveBeenCalledWith({base: 'EUR', quote: 'GBP', slug: 'EUR-GBP', hasRealProvider: route, autoSyncStarted: false});
        expect(syncRates).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(buildFxSyncToast).not.toHaveBeenCalled();
        expect(onlyNotice().variant).toBe('success');
        expectLinkedPair(onlyNotice().message, 'EUR-GBP');
        expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([
            [{base: 'EUR', quote: 'GBP', chain_steps: route ? DIRECT : [{from: 'EUR', to: 'GBP', provider: 'MANUAL'}], priority: route ? 1 : 999}],
        ]);
    });

    it('editing a provider does not start creation-time sync or creation feedback', async () => {
        const {oncreated, onsynced} = mount({editMode: true, editBase: 'EUR', editQuote: 'GBP'});
        await pickRoute('direct');
        await save();
        await closed();
        expect(deleteRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP'}]]);
        expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]]);
        expect(oncreated).toHaveBeenCalledTimes(1);
        expect(syncRates).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(feedback.notices).toEqual([]);
    });

    it.each([409, 500])('keeps the owned draft after configuration HTTP %s and never starts sync', async (status) => {
        createRoutes.mockRejectedValue({response: {status, data: {detail: 'owned-configuration-rejected'}}});
        const {oncreated, onsynced, onclose} = mount();
        await pickRoute('direct');
        await save();
        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toBeVisible());
        expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
        expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
        expect(screen.getByTestId('fx-route-selected')).toHaveAttribute('data-route-key', 'EUR-GBP:ECB');
        expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]]);
        expect(syncRates).not.toHaveBeenCalled();
        expect(oncreated).not.toHaveBeenCalled();
        expect(onsynced).not.toHaveBeenCalled();
        expect(onclose).not.toHaveBeenCalled();
        expect(feedback.notices).toEqual([]);
    });

    it('an old sync may finish after reopening without changing the new pair, range or callbacks', async () => {
        const pending = deferred<SyncResponse>();
        syncRates.mockReturnValue(pending.promise);
        const {rerender, oncreated, onsynced} = mount();
        const newSynced = vi.fn();
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
            await closed();
            vi.mocked(findConversionPaths).mockResolvedValue([]);
            await rerender({open: true, initialBase: 'JPY', initialQuote: 'USD', dateStart: '2023-01-01', dateEnd: '2023-02-01', onsynced: newSynced});
            await ready();
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();

            pending.resolve(syncResponse('EUR-GBP'));
            await waitFor(() => expect(feedback.notices).toHaveLength(1));
            expectLinkedPair(onlyNotice().message, 'EUR-GBP');
            expect(newSynced).not.toHaveBeenCalled();
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
            expect(oncreated).toHaveBeenCalledTimes(1);
            expect(onsynced).toHaveBeenCalledTimes(1);

            await save();
            await closed();
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([
                [{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}],
                [{base: 'JPY', quote: 'USD', chain_steps: [{from: 'JPY', to: 'USD', provider: 'MANUAL'}], priority: 999}],
            ]);
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP'], start: RANGE.dateStart, end: RANGE.dateEnd}]);
        } finally {
            pending.resolve(syncResponse('EUR-GBP'));
            await pending.promise;
        }
    });

    it('unmounting just the modal does not cancel sync or the still-live host completion', async () => {
        const pending = deferred<SyncResponse>();
        syncRates.mockReturnValue(pending.promise);
        const {unmount, oncreated, onsynced} = mount();
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
            await closed();
            unmount();
            expect(onsynced).not.toHaveBeenCalled();
            pending.resolve(syncResponse('EUR-GBP'));
            await waitFor(() => expect(feedback.notices).toHaveLength(1));
            expect(oncreated).toHaveBeenCalledTimes(1);
            expect(onsynced).toHaveBeenCalledTimes(1);
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP'], start: RANGE.dateStart, end: RANGE.dateEnd}]);
            expect(onlyNotice().variant).toBe('success');
            expectLinkedPair(onlyNotice().message, 'EUR-GBP');
        } finally {
            pending.resolve(syncResponse('EUR-GBP'));
            await pending.promise;
        }
    });

    it('a changed account cannot close or notify a newly opened draft when the old POST completes', async () => {
        const posted = deferred<Awaited<ReturnType<typeof zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post>>>();
        createRoutes.mockReturnValue(posted.promise);
        const old = mount();
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(createRoutes).toHaveBeenCalledTimes(1));
            old.unmount();
            transitionClientSession('new-fx-creation-owner');
            vi.mocked(findConversionPaths).mockResolvedValue([]);
            const fresh = mount({initialBase: 'JPY', initialQuote: 'USD'});
            await ready();
            posted.resolve(creationResponse([{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]));
            await posted.promise;
            // Fire a new owned action after the old response, then wait for its
            // success. This is a positive barrier for all negative assertions.
            createRoutes.mockImplementation(async (items) => creationResponse(items));
            await save();
            await closed();
            expect(fresh.oncreated).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: 'JPY-USD', autoSyncStarted: false}));
            expect(old.oncreated).not.toHaveBeenCalled();
            expect(old.onclose).not.toHaveBeenCalled();
            expect(old.onsynced).not.toHaveBeenCalled();
            expect(syncRates).not.toHaveBeenCalled();
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([
                [{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}],
                [{base: 'JPY', quote: 'USD', chain_steps: [{from: 'JPY', to: 'USD', provider: 'MANUAL'}], priority: 999}],
            ]);
            expectLinkedPair(onlyNotice().message, 'JPY-USD');
        } finally {
            posted.resolve(creationResponse([{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]));
            await posted.promise;
        }
    });

    it('a committed CREATE still syncs its captured chain after same-account modal replacement', async () => {
        const posted = deferred<Awaited<ReturnType<typeof zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post>>>();
        const pending = deferred<SyncResponse>();
        const items = [
            {base: 'EUR', quote: 'GBP', chain_steps: CHAIN, priority: 1},
            {base: 'EUR', quote: 'USD', chain_steps: [CHAIN[0]!], priority: 1},
            {base: 'GBP', quote: 'USD', chain_steps: [CHAIN[1]!], priority: 1},
        ];
        createRoutes.mockReturnValue(posted.promise);
        syncRates.mockReturnValue(pending.promise);
        const old = mount();
        try {
            await pickRoute('chain');
            await fireEvent.click(screen.getByTestId('fx-add-pair-intermediates'));
            await save();
            await waitFor(() => expect(createRoutes).toHaveBeenCalledTimes(1));
            expect(syncRates).not.toHaveBeenCalled();
            old.unmount();
            vi.mocked(findConversionPaths).mockResolvedValue([]);
            const fresh = mount({initialBase: 'JPY', initialQuote: 'USD', dateStart: '2023-01-01', dateEnd: '2023-02-01'});
            await ready();

            posted.resolve(creationResponse(items));
            await waitFor(() => expect(syncRates).toHaveBeenCalledTimes(1));
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([items]);
            expect(syncRates.mock.calls.map(([body]) => body)).toEqual([{pairs: ['EUR-GBP', 'EUR-USD', 'GBP-USD'], start: RANGE.dateStart, end: RANGE.dateEnd}]);
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
            expect(fresh.oncreated).not.toHaveBeenCalled();
            expect(fresh.onclose).not.toHaveBeenCalled();
            pending.resolve(syncResponse('GBP-USD', 'EUR-USD', 'EUR-GBP'));
            await waitFor(() => expect(feedback.notices).toHaveLength(1));
            expectLinkedPair(onlyNotice().message, 'EUR-GBP');
            expect(onlyNotice().variant).toBe('success');
            expect(old.onsynced).toHaveBeenCalledTimes(1);
            expect(fresh.onsynced).not.toHaveBeenCalled();

            // The replacement draft must still create its own manual pair, not
            // reuse any currency, route, date or callback from the old request.
            createRoutes.mockImplementation(async (body) => creationResponse(body));
            await save();
            await closed();
            expect(fresh.oncreated).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: 'JPY-USD', autoSyncStarted: false}));
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([
                items,
                [{base: 'JPY', quote: 'USD', chain_steps: [{from: 'JPY', to: 'USD', provider: 'MANUAL'}], priority: 999}],
            ]);
            expect(syncRates).toHaveBeenCalledTimes(1);
        } finally {
            posted.resolve(creationResponse(items));
            pending.resolve(syncResponse('EUR-GBP', 'EUR-USD', 'GBP-USD'));
            await Promise.all([posted.promise, pending.promise]);
        }
    });

    it.each(['CREATE', 'DELETE'] as const)('reports a failed %s globally if the original form is already gone', async (operation) => {
        const pending = deferred<never>();
        if (operation === 'CREATE') createRoutes.mockReturnValue(pending.promise);
        else deleteRoutes.mockReturnValue(pending.promise);
        const old = mount(operation === 'DELETE' ? {editMode: true, editBase: 'EUR', editQuote: 'GBP'} : {});
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(operation === 'CREATE' ? createRoutes : deleteRoutes).toHaveBeenCalledTimes(1));
            old.unmount();
            vi.mocked(findConversionPaths).mockResolvedValue([]);
            const fresh = mount({initialBase: 'JPY', initialQuote: 'USD'});
            await ready();
            pending.reject({response: {status: 503, data: {detail: 'owned-detached-configuration-failure'}}});

            await waitFor(() => {
                expect(notify).toHaveBeenCalledWith(
                    expect.objectContaining({
                        name: 'fx.pair.configuration-failed',
                        detail: expect.objectContaining({slug: 'EUR-GBP', editMode: operation === 'DELETE'}),
                        toast: expect.objectContaining({variant: 'error'}),
                    }),
                );
            });
            expect(onlyNotice().variant).toBe('error');
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
            expect(screen.queryByTestId('info-banner-error')).not.toBeInTheDocument();
            expect(fresh.oncreated).not.toHaveBeenCalled();
            expect(fresh.onclose).not.toHaveBeenCalled();
            expect(fresh.onsynced).not.toHaveBeenCalled();
            expect(syncRates).not.toHaveBeenCalled();
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual(operation === 'CREATE' ? [[{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]] : []);
            expect(deleteRoutes.mock.calls.map(([body]) => body)).toEqual(operation === 'DELETE' ? [[{base: 'EUR', quote: 'GBP'}]] : []);
        } finally {
            pending.reject(new Error('release-owned-failed-configuration'));
            await pending.promise.catch(() => undefined);
        }
    });

    it.each([false, true])('finishes pending edit DELETE without adopting a new draft (account changed: %s)', async (changeAccount) => {
        const deleted = deferred<Awaited<ReturnType<typeof zodiosApi.delete_routes_bulk_api_v1_fx_providers_routes_delete>>>();
        const deletedResponse = {
            results: [{success: true, deleted_count: 1, base: 'EUR', quote: 'GBP'}],
            success_count: 1,
            total_deleted: 1,
        };
        deleteRoutes.mockReturnValue(deleted.promise);
        const old = mount({editMode: true, editBase: 'EUR', editQuote: 'GBP'});
        try {
            await pickRoute('direct');
            await save();
            await waitFor(() => expect(deleteRoutes).toHaveBeenCalledTimes(1));
            expect(createRoutes).not.toHaveBeenCalled();
            old.unmount();
            if (changeAccount) transitionClientSession('replacement-edit-account');
            vi.mocked(findConversionPaths).mockResolvedValue([]);
            const fresh = mount({initialBase: 'JPY', initialQuote: 'USD'});
            await ready();
            deleted.resolve(deletedResponse);
            if (!changeAccount) {
                await waitFor(() => expect(notify).toHaveBeenCalledWith(expect.objectContaining({name: 'fx.pair.updated', detail: expect.objectContaining({slug: 'EUR-GBP'})})));
                expect(createRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}]]);
                expect(feedback.notices).toEqual([]);
            }
            expect(screen.getByTestId('fx-add-pair-modal')).toBeVisible();
            expect(screen.getByTestId('fx-add-pair-save')).toBeEnabled();
            expect(fresh.oncreated).not.toHaveBeenCalled();
            expect(fresh.onclose).not.toHaveBeenCalled();
            // A new owned successful save also establishes a completion barrier
            // for the negative account case: the old DELETE cannot POST as it.
            await save();
            await closed();
            const manual = [{base: 'JPY', quote: 'USD', chain_steps: [{from: 'JPY', to: 'USD', provider: 'MANUAL'}], priority: 999}];
            expect(createRoutes.mock.calls.map(([body]) => body)).toEqual(changeAccount ? [manual] : [[{base: 'EUR', quote: 'GBP', chain_steps: DIRECT, priority: 1}], manual]);
            expect(deleteRoutes.mock.calls.map(([body]) => body)).toEqual([[{base: 'EUR', quote: 'GBP'}]]);
            expect(syncRates).not.toHaveBeenCalled();
            expect(fresh.oncreated).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({slug: 'JPY-USD', autoSyncStarted: false}));
            expectLinkedPair(onlyNotice().message, 'JPY-USD');
            if (changeAccount) {
                expect(vi.mocked(notify).mock.calls.some(([event]) => event.name === 'fx.pair.updated')).toBe(false);
            }
        } finally {
            deleted.resolve(deletedResponse);
            await deleted.promise;
        }
    });
});
