/**
 * The data-quality banner's actions of the portfolio view (Y6-7, delivery 2, checkpoint 9e; moved out of the Dashboard
 * page, behaviour kept).
 *
 * What the old inline code did and a browser spec reaches only through a whole page: a chip leads to the asset or the pair;
 * «add pair» opens the dialog on the pair of the chip pressed (the currency selector opens it too); «sync rates» sends the
 * dates the issue carries, asks the report again unless the request failed, and tells the outcome once the report is known
 * (a pair still missing or still stale turns a success into a warning); «sync prices» asks the flagged assets from where
 * they stopped, up to the period's end; both hold the page busy meanwhile and never act on a page that is gone.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {setupI18n} from '$test/component';

const mocks = vi.hoisted(() => ({
    syncRates: vi.fn(),
    syncPrices: vi.fn(),
    goto: vi.fn(),
    notify: vi.fn(),
    toast: {info: vi.fn(), error: vi.fn(), success: vi.fn(), warning: vi.fn()},
    invalidate: vi.fn(),
    invalidateFxRoutes: vi.fn(),
}));
vi.mock('$lib/api', () => ({zodiosApi: {sync_rates_api_v1_fx_currencies_sync_post: mocks.syncRates, sync_prices_bulk_api_v1_assets_prices_sync_post: mocks.syncPrices}}));
vi.mock('$app/navigation', () => ({goto: mocks.goto}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: mocks.notify}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({toasts: mocks.toast}));
vi.mock('$lib/stores/portfolio/portfolioStore.svelte', () => ({invalidate: mocks.invalidate}));
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({invalidateFxRoutes: mocks.invalidateFxRoutes}));

import {PortfolioBannerActions, type PortfolioBannerInputs} from './portfolioBannerActions.svelte';
import {STALE_FX_ACTION, STALE_FX_CODE} from '$lib/features/dashboard/staleFxIssue';
import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';

const missingFx = (overrides: Partial<DataQualityIssue> = {}): DataQualityIssue => ({
    domain: 'portfolio',
    code: 'MISSING_FX_RATES',
    severity: 'warning',
    message_i18n_key: 'dataQuality.missingFxRates',
    message_params: {date_from: '2020-01-02', date_to: '2020-01-09', dates_count: 3},
    affected_fx_pairs: ['EUR-USD'],
    cta_action: 'sync_fx_pair',
    cta_target: 'EUR-USD',
    ...overrides,
});

const stalePrice = (overrides: Partial<DataQualityIssue> = {}): DataQualityIssue => ({
    domain: 'portfolio',
    code: 'STALE_PRICE',
    severity: 'warning',
    message_i18n_key: 'dataQuality.stalePrice',
    affected_asset_ids: [7, 9],
    affected_asset_names: ['Alpha', 'Beta'],
    cta_action: 'sync_asset_prices',
    ...overrides,
});

interface Knobs {
    issues: DataQualityIssue[];
    stalePairs: {pair: string; last_rate_date: string; stale_days: number}[] | undefined;
    alive: boolean;
}

function make(overrides: Partial<Knobs> = {}, reload?: PortfolioBannerInputs['reload']) {
    const knobs: Knobs = {issues: [], stalePairs: undefined, alive: true, ...overrides};
    const inputs: PortfolioBannerInputs = {
        issues: () => knobs.issues,
        staleFxPairs: () => knobs.stalePairs,
        periodEnd: () => '2026-06-30',
        alive: () => knobs.alive,
        reload: reload ?? vi.fn(async () => undefined),
        onDataChanged: vi.fn(),
        translate: (key: string) => key,
    };
    return {knobs, inputs, actions: new PortfolioBannerActions(inputs)};
}

const okSync = (pair = 'EUR-USD') => ({results: [{pair, status: 'ok', provider_used: 'ECB', message: 'ok', detail: []}], errors: []});

beforeEach(async () => {
    await setupI18n();
    for (const mock of [mocks.syncRates, mocks.syncPrices, mocks.goto, mocks.notify, mocks.invalidate, mocks.invalidateFxRoutes, ...Object.values(mocks.toast)]) mock.mockReset();
});

describe('PortfolioBannerActions · chips', () => {
    it('leads an asset chip to the asset and a pair chip to the pair', async () => {
        const {actions} = make();
        await actions.handleAction('navigate_asset', '12', missingFx());
        await actions.handleAction('navigate_fx', 'EUR-USD', missingFx());
        expect(mocks.goto.mock.calls.map((call) => call[0])).toEqual(['/assets/12', '/fx/EUR-USD']);
    });

    it('opens the pair dialog on the pair of the chip pressed, and on the base currency from the selector', async () => {
        const {actions} = make();
        await actions.handleAction('add_fx_pair', 'GBP-JPY', missingFx());
        expect(actions.fxPairModalOpen).toBe(true);
        expect(actions.fxPairSlug).toBe('GBP-JPY');
        actions.fxPairModalOpen = false;
        actions.openFxPairModal('EUR-');
        expect(actions.fxPairModalOpen).toBe(true);
        expect(actions.fxPairSlug).toBe('EUR-');
    });

    it('opens the dialog empty when the chip carries no pair', async () => {
        const {actions} = make();
        await actions.handleAction('add_fx_pair', null, missingFx());
        expect(actions.fxPairSlug).toBe('');
    });
});

describe('PortfolioBannerActions · sync rates', () => {
    it('sends the dates of the issue, asks the report again and tells a clean success once', async () => {
        mocks.syncRates.mockResolvedValue(okSync());
        const {inputs, actions} = make({issues: []});
        await actions.handleAction('sync_fx_pair', 'EUR-USD', missingFx());

        const [body] = mocks.syncRates.mock.calls[0];
        expect(body.pairs).toEqual(['EUR-USD']);
        expect(body.start <= '2019-12-26').toBe(true);
        expect(inputs.reload).toHaveBeenCalledWith(true, true);
        expect(inputs.onDataChanged).toHaveBeenCalledTimes(1);
        expect(mocks.invalidate).toHaveBeenCalledTimes(1);
        expect(mocks.invalidateFxRoutes).toHaveBeenCalledTimes(1);
        expect(mocks.notify).toHaveBeenCalledTimes(1);
        const note = mocks.notify.mock.calls[0][0];
        expect(note.name).toBe('fx.rates.synced');
        expect(note.detail).toMatchObject({origin: 'dashboard-banner', outcome: 'ok', stillMissing: false, stillStale: false});
        expect(note.toast.variant).toBe('success');
        expect(actions.syncLoading).toBe(false);
        expect(actions.syncingCode).toBeNull();
    });

    it('holds the busy state and names the code while it runs', async () => {
        let release!: (value: unknown) => void;
        mocks.syncRates.mockReturnValue(new Promise((resolve) => (release = resolve)));
        const {actions} = make();
        const running = actions.handleAction('sync_fx_pair', 'EUR-USD', missingFx());
        expect(actions.syncLoading).toBe(true);
        expect(actions.syncingCode).toBe('MISSING_FX_RATES');
        release(okSync());
        await running;
        expect(actions.syncLoading).toBe(false);
    });

    it('does not ask the report again after a transport error: the backend may still be writing', async () => {
        mocks.syncRates.mockRejectedValue(new Error('boom'));
        const {inputs, actions} = make();
        await actions.handleAction('sync_fx_pair', 'EUR-USD', missingFx());
        expect(inputs.reload).not.toHaveBeenCalled();
        expect(inputs.onDataChanged).not.toHaveBeenCalled();
        const note = mocks.notify.mock.calls[0][0];
        expect(note.detail).toMatchObject({outcome: 'transport-error', stillMissing: null});
        expect(note.toast.variant).toBe('error');
    });

    it('turns a success into a warning when the report still lists the pair as missing', async () => {
        mocks.syncRates.mockResolvedValue(okSync());
        const {actions} = make({issues: [missingFx()]});
        await actions.handleAction('sync_fx_pair', 'EUR-USD', missingFx());
        const note = mocks.notify.mock.calls[0][0];
        expect(note.detail).toMatchObject({outcome: 'ok', stillMissing: true});
        expect(note.toast.variant).toBe('warning');
    });

    it('reads what is still missing AFTER the report came back, not before', async () => {
        mocks.syncRates.mockResolvedValue(okSync());
        const state = {issues: [missingFx()]};
        const {knobs, actions} = make({issues: state.issues}, async () => {
            knobs.issues = []; // the new report no longer lists it
        });
        await actions.handleAction('sync_fx_pair', 'EUR-USD', missingFx());
        expect(mocks.notify.mock.calls[0][0].detail).toMatchObject({stillMissing: false});
    });

    it('says the old rate is still old when the report keeps the pair stale, and warns', async () => {
        mocks.syncRates.mockResolvedValue(okSync());
        const staleIssue = {...missingFx({code: STALE_FX_CODE, cta_action: STALE_FX_ACTION}), affected_fx_pairs: undefined};
        const {actions} = make({stalePairs: [{pair: 'EUR-USD', last_rate_date: '2026-05-01', stale_days: 60}]});
        await actions.handleAction(STALE_FX_ACTION, 'EUR-USD', staleIssue);
        const note = mocks.notify.mock.calls[0][0];
        expect(note.detail).toMatchObject({stillStale: true});
        expect(note.toast.variant).toBe('warning');
    });

    it('ignores an issue that names no pair', async () => {
        const {actions} = make();
        await actions.handleAction('sync_fx_pair', null, missingFx({affected_fx_pairs: [], cta_target: null}));
        expect(mocks.syncRates).not.toHaveBeenCalled();
        expect(actions.syncLoading).toBe(false);
    });

    it('does nothing after the page is gone', async () => {
        mocks.syncRates.mockResolvedValue(okSync());
        const {knobs, inputs, actions} = make();
        const running = actions.handleAction('sync_fx_pair', 'EUR-USD', missingFx());
        knobs.alive = false;
        await running;
        expect(inputs.reload).not.toHaveBeenCalled();
        expect(mocks.notify).not.toHaveBeenCalled();
        expect(actions.syncLoading).toBe(false);
    });
});

describe('PortfolioBannerActions · sync prices', () => {
    it('asks the flagged assets from where they stopped up to the period end, then reloads', async () => {
        mocks.syncPrices.mockResolvedValue({
            results: [
                {asset_id: 7, status: 'ok'},
                {asset_id: 9, status: 'ok'},
            ],
        });
        const {inputs, actions} = make();
        await actions.handleAction('sync_asset_prices', null, stalePrice());
        expect(mocks.syncPrices.mock.calls[0][0]).toEqual([
            {asset_id: 7, date_range: {start: 'resume', end: '2026-06-30'}},
            {asset_id: 9, date_range: {start: 'resume', end: '2026-06-30'}},
        ]);
        expect(mocks.invalidate).toHaveBeenCalledTimes(1);
        expect(inputs.onDataChanged).toHaveBeenCalledTimes(1);
        expect(inputs.reload).toHaveBeenCalledWith(true);
        expect(actions.syncLoading).toBe(false);
        expect(actions.syncingCode).toBeNull();
    });

    it('asks nothing when the issue flags no asset', async () => {
        const {actions} = make();
        await actions.handleAction('sync_asset_prices', null, stalePrice({affected_asset_ids: []}));
        expect(mocks.syncPrices).not.toHaveBeenCalled();
        expect(actions.syncLoading).toBe(false);
    });

    it('tells an error and lets go of the busy state when the request fails', async () => {
        mocks.syncPrices.mockRejectedValue(new Error('provider down'));
        const {inputs, actions} = make();
        await actions.handleAction('sync_asset_prices', null, stalePrice());
        expect(mocks.toast.error).toHaveBeenCalledTimes(1);
        expect(inputs.reload).not.toHaveBeenCalled();
        expect(actions.syncLoading).toBe(false);
        expect(actions.syncingCode).toBeNull();
    });
});
