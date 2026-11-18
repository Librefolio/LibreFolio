// @vitest-environment jsdom
/**
 * SignalParamControl — a backend signal's parameter, drawn from its descriptor (Vitest + jsdom).
 *
 * RN-21 (the consultant, 17/11/2026): a parameter bound to the reader's risk-free rate (`control: 'risk_free_rate'`)
 * has no field of its own: the chart says which rate it uses, the shared one, so a card and a chart never say two
 * figures. A plain number parameter keeps its field.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';

const cache = vi.hoisted(() => ({entries: [] as Array<Record<string, unknown> & {id: number}>}));

vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/reference/assetStore')>();
    const {readable} = await import('svelte/store');
    return {...actual, assetStoreVersion: readable(0), ensureAssetsLoaded: vi.fn(() => Promise.resolve()), getAllAssets: vi.fn(() => cache.entries.map((asset) => ({...asset})))};
});

vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn(async () => {}),
}));

import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {riskFreeRate} from '$lib/features/risk/riskFreeRateStore.svelte';
import {recordAnsweredParams} from '$lib/features/signals/answeredParams.svelte';
import type {SignalParamDescriptor} from '$lib/features/signals';
import SignalParamControl from './SignalParamControl.svelte';

beforeAll(async () => {
    await setupI18n('en');
});

afterEach(() => {
    cleanup();
    riskFreeRate.set(0);
});

const RATE: SignalParamDescriptor = {key: 'risk_free_annual_rate', label: 'chartSettings.params.riskFreeAnnualRate', type: 'number', control: 'risk_free_rate', default: 0};
const WINDOW: SignalParamDescriptor = {key: 'window', label: 'chartSettings.params.window', type: 'number', default: 90};

// RN-12b: Rolling Beta's comparison asset rules out the chart's own asset, as every backend asset parameter does.
describe('SignalParamControl — Rolling Beta against the chart’s own asset', () => {
    it('hands the chart’s asset to the comparison picker, which rules it out', async () => {
        cache.entries = [
            {id: 7, display_name: 'Own Asset', currency: 'EUR', asset_type: 'STOCK', active: true},
            {id: 8, display_name: 'Other Asset', currency: 'EUR', asset_type: 'STOCK', active: true},
        ];
        const beta: SignalParamDescriptor = {key: 'comparison_asset_id', label: 'chartSettings.params.comparisonAsset', type: 'number', integer: true, control: 'comparison_asset', required: true, default: undefined};
        render(SignalParamControl, {props: {descriptor: beta, value: null, onchange: vi.fn(), mainAssetId: 7}});

        await fireEvent.click(screen.getByTestId('signal-comparison-asset-select-trigger'));
        const blocked = await screen.findByTestId('signal-comparison-asset-select-blocked');
        expect(within(blocked).getByTestId('search-select-option-7')).toHaveAttribute('data-reasons', 'main-asset');
    });
});

describe('SignalParamControl — the risk-free rate', () => {
    // The consultant, 17/11/2026 (B): the line says the rate of the answer the chart draws, never the field's — a field
    // at 2.5 % with a series still at 0 % reads «0 %», which is true; before any answer, no figure.
    it('says the rate of the answer, not the field, and no figure before an answer', () => {
        riskFreeRate.set(2.5);
        render(SignalParamControl, {props: {descriptor: RATE, value: 0.04, onchange: vi.fn(), instanceId: 'sharpe-answered'}});
        expect(screen.getByTestId('signal-param-risk-free-rate')).toHaveAttribute('data-percent', '');
        expect(screen.getByTestId('signal-param-risk_free_annual_rate').querySelector('input'), 'no field of its own').toBeNull();

        recordAnsweredParams([
            {
                config: {id: 'sharpe-answered', signalType: 'risk-rolling-sharpe', params: {}, style: {color: '#000', lineWidth: 1, lineType: 'solid', markerStart: null, markerEnd: null}},
                source: 'backend',
                status: 'ok',
                result: {normalized_params: {window: 90, risk_free_annual_rate: 0}} as never,
                error: null,
            },
        ]);
        flushSync();
        expect(screen.getByTestId('signal-param-risk-free-rate')).toHaveAttribute('data-percent', '0');

        recordAnsweredParams([
            {
                config: {id: 'sharpe-answered', signalType: 'risk-rolling-sharpe', params: {}, style: {color: '#000', lineWidth: 1, lineType: 'solid', markerStart: null, markerEnd: null}},
                source: 'backend',
                status: 'ok',
                result: {normalized_params: {window: 90, risk_free_annual_rate: 0.025}} as never,
                error: null,
            },
        ]);
        flushSync();
        expect(screen.getByTestId('signal-param-risk-free-rate')).toHaveAttribute('data-percent', '2.5');
    });

    it('keeps the field of a plain number parameter', () => {
        render(SignalParamControl, {props: {descriptor: WINDOW, value: 90, onchange: vi.fn()}});
        expect(screen.getByTestId('signal-param-window').querySelector('input[type="number"]')).not.toBeNull();
    });
});
