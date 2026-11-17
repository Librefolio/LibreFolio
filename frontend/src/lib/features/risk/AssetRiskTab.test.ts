// @vitest-environment jsdom
/**
 * AssetRiskTab — the Asset Detail's «Risk and scenarios» tab as an x-ray of the asset (RN-17, Q1, Q3, Q17, Q20).
 *
 * The tab mounts the levels panel on the asset, reads once the value of your position from the backend's portfolio
 * report (grouped by asset) and says, once, which value the amounts are on — only when you own the asset (Q17 A1). On an
 * asset whose prices come from a plan (a scheduled investment, a HOLD, a crowdfunding) it says so above the levels
 * (Q20 a). Sentences come from the catalogue through `$_`; every figure is invented.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';

const fetchRiskCatalog = vi.hoisted(() => vi.fn());
const fetchRiskScenarioCatalog = vi.hoisted(() => vi.fn());
const queryRisk = vi.hoisted(() => vi.fn());
const invalidateRisk = vi.hoisted(() => vi.fn());
const reportApi = vi.hoisted(() => vi.fn());

vi.mock('$lib/features/risk/riskStore.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/risk/riskStore.svelte')>();
    return {...actual, fetchRiskCatalog, fetchRiskScenarioCatalog, queryRisk, invalidateRisk, hasRiskCapability: () => true};
});
vi.mock('$lib/api', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/api')>();
    return {...actual, zodiosApi: new Proxy(actual.zodiosApi, {get: (target, name) => (name === 'get_portfolio_report_api_v1_portfolio_report_post' ? reportApi : Reflect.get(target, name))})};
});
vi.mock('echarts', () => ({
    init: (dom: unknown) => ({setOption: () => {}, getDom: () => dom, on: () => {}, off: () => {}, dispatchAction: () => {}, clear: () => {}, resize: () => {}, isDisposed: () => false, dispose: () => {}}),
}));

import {cleanup, render, screen, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {formatCurrencyAmount} from './riskAnalysisHelpers';
import AssetRiskTab from './AssetRiskTab.svelte';

const ASSET = 7;

function mount(props: Record<string, unknown> = {}) {
    return render(AssetRiskTab, {props: {assetId: ASSET, assetType: 'ETF', parametricPrices: false, dateStart: '2025-01-01', dateEnd: '2025-12-31', targetCurrency: 'EUR', ...props}});
}

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    fetchRiskCatalog.mockReset().mockResolvedValue({items: []});
    fetchRiskScenarioCatalog.mockReset().mockResolvedValue({items: []});
    invalidateRisk.mockReset();
    queryRisk.mockReset().mockResolvedValue({items: []});
    reportApi.mockReset().mockResolvedValue({summary: {holdings: [{asset_id: ASSET, current_value: '12400.00'}]}});
});

afterEach(() => cleanup());

describe('AssetRiskTab — the levels on the asset, and the money on your position (Q17 A1)', () => {
    it('mounts the levels panel on the asset, and asks the report once, grouped by asset, in the page’s currency, today (no period)', async () => {
        mount();

        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-scope', 'asset'));
        await waitFor(() => expect(reportApi).toHaveBeenCalledTimes(1));
        expect(reportApi.mock.calls[0][0]).toMatchObject({include_summary: true, include_history: false, group_by: 'asset', target_currency: 'EUR'});
        // «Your position today» (Q17): the summary at today, never at the end of a past period the page shows.
        expect(reportApi.mock.calls[0][0]).not.toHaveProperty('date_range');
    });

    it('says once which value the amounts are on, when you own the asset', async () => {
        mount();

        const line = await screen.findByTestId('asset-risk-position');
        expect(line.textContent?.replace(/\s+/g, ' ').trim()).toBe(
            get(_)('risk.assetDetail.positionNote', {values: {amount: formatCurrencyAmount('12400', 'EUR')}})
                .replace(/\s+/g, ' ')
                .trim(),
        );
    });

    it('masks the amount when privacy is on, and shows it again when it is off', async () => {
        mount();
        const line = await screen.findByTestId('asset-risk-position');
        expect(line.textContent).toMatch(/12[,.\u202f\u00a0]?400/);

        setPrivacyEnabled(true);
        await waitFor(() => expect(line.textContent).not.toMatch(/12[,.\u202f\u00a0]?400/));
        setPrivacyEnabled(false);
        await waitFor(() => expect(line.textContent).toMatch(/12[,.\u202f\u00a0]?400/));
    });

    it.each([
        {why: 'the asset is not held', answer: {summary: {holdings: [{asset_id: 3, current_value: '500'}]}}},
        {why: 'the read failed', answer: null},
    ])('says nothing of money when $why', async ({answer}) => {
        if (answer === null) reportApi.mockRejectedValue(new Error('invented: the report failed'));
        else reportApi.mockResolvedValue(answer);
        mount();

        await waitFor(() => expect(reportApi).toHaveBeenCalled());
        // The read is over: the absence below is final, not a sentence still on its way.
        await waitFor(() => expect(screen.getByTestId('asset-risk-tab')).toHaveAttribute('data-position', 'ready'));
        expect(screen.queryByTestId('asset-risk-position')).toBeNull();
    });
});

describe('AssetRiskTab — prices from the plan, not the market (Q20 a)', () => {
    it.each([
        {kind: 'a scheduled investment', props: {assetType: 'BOND', parametricPrices: true}},
        {kind: 'a HOLD', props: {assetType: 'HOLD'}},
        {kind: 'a crowdfunding asset', props: {assetType: 'CROWDFUND_REAL_ESTATE'}},
    ])('says so above the levels on $kind', async ({props}) => {
        mount(props);

        const notice = await screen.findByTestId('asset-risk-plan-prices');
        expect(notice.textContent?.replace(/\s+/g, ' ').trim()).toBe(get(_)('risk.assetDetail.planPrices'));
    });

    it('says nothing of the kind on an asset priced on a market', async () => {
        mount();

        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.queryByTestId('asset-risk-plan-prices')).toBeNull();
    });
});
