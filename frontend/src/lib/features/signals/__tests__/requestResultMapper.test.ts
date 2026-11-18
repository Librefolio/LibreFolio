import {describe, expect, it} from 'vitest';

import type {BackendSignalResult} from '../backendTypes';
import {backendSignalSchemas} from '../backendTypes';
import type {SignalConfig, SignalDefinition} from '../ChartSignal';
import {buildBackendSignalRequestPlan} from '../requestBuilder';
import {riskFreeRate} from '$lib/features/risk/riskFreeRateStore.svelte';
import {mapSignalInstanceResults, SignalResultState} from '../resultMapper';

function config(id: string, signalType: string, params: Record<string, unknown> = {}): SignalConfig {
    return {
        id,
        signalType,
        params,
        style: {
            color: '#3b82f6',
            lineWidth: 1,
            lineType: 'solid',
            markerStart: null,
            markerEnd: null,
        },
    };
}

const backendDefinition: SignalDefinition = {
    type: 'ema',
    displayName: 'EMA',
    icon: 'chart-spline',
    category: 'indicator',
    paramDescriptors: [],
    source: 'backend',
    backendSignalCode: 'EMA',
    compatibleDomains: ['asset', 'fx'],
};

const localDefinition: SignalDefinition = {
    type: 'linear',
    displayName: 'Linear',
    icon: '📈',
    category: 'benchmark',
    paramDescriptors: [],
    source: 'local',
    compatibleDomains: ['asset', 'fx'],
};

function result(instanceId: string, status: BackendSignalResult['status']): BackendSignalResult {
    const payload: Record<string, unknown> = {
        instance_id: instanceId,
        signal_code: 'EMA',
        status,
    };
    if (status === 'failed') {
        payload.error = {
            code: 'compute_error',
            message: 'compute failed',
        };
    }
    return backendSignalSchemas.result.parse(payload);
}

describe('backend signal request/result mapping', () => {
    it('deduplicates identical requests while preserving all instance aliases', () => {
        const first = config('ema-a', 'ema', {period: 20});
        const second = config('ema-b', 'ema', {period: 20});
        const plan = buildBackendSignalRequestPlan([first, second], [backendDefinition]);

        expect(plan.requests).toEqual([
            {
                instance_id: 'ema-a',
                signal_code: 'EMA',
                params: {period: 20},
            },
        ]);
        expect(plan.instanceAliases.get('ema-a')).toEqual(['ema-a', 'ema-b']);

        const mapped = mapSignalInstanceResults([first, second], plan, [result('ema-a', 'partial')]);
        expect(mapped.map((item) => item.status)).toEqual(['partial', 'partial']);
        expect(mapped.map((item) => item.config.id)).toEqual(['ema-a', 'ema-b']);
    });

    it('keeps local-only plans free of backend requests', () => {
        const local = config('linear-a', 'linear', {rate: 5});
        const plan = buildBackendSignalRequestPlan([local], [localDefinition]);

        expect(plan.requests).toEqual([]);
        expect(mapSignalInstanceResults([local], plan, [])).toMatchObject([
            {
                source: 'local',
                status: 'local',
            },
        ]);
    });

    it('keeps backend signals with missing required params out of requests', () => {
        const betaDefinition: SignalDefinition = {
            ...backendDefinition,
            type: 'risk-rolling-beta',
            backendSignalCode: 'RISK_ROLLING_BETA',
            paramDescriptors: [
                {
                    key: 'comparison_asset_id',
                    label: 'Comparison asset',
                    type: 'number',
                    required: true,
                    control: 'comparison_asset',
                    default: undefined,
                },
            ],
        };
        const beta = config('beta-a', 'risk-rolling-beta', {window: 90});
        const plan = buildBackendSignalRequestPlan([beta], [betaDefinition]);

        expect(plan.requests).toEqual([]);
        expect(plan.unavailableConfigs).toEqual([beta]);
    });

    // RN-21 (the consultant, 17/11/2026): a parameter bound to the reader's risk-free rate goes with the shared value, as
    // an annual fraction; a value the chart once saved in the browser is left where it is and no longer read.
    it('fills a risk-free rate parameter from the shared value, over a saved one', () => {
        const sharpeDefinition: SignalDefinition = {
            ...backendDefinition,
            type: 'risk-rolling-sharpe',
            backendSignalCode: 'RISK_ROLLING_SHARPE',
            paramDescriptors: [{key: 'risk_free_annual_rate', label: 'Risk-free rate', type: 'number', control: 'risk_free_rate', default: 0}],
        };
        const saved = config('sharpe-a', 'risk-rolling-sharpe', {window: 90, risk_free_annual_rate: 0.04});
        try {
            riskFreeRate.set(2.5);
            expect(buildBackendSignalRequestPlan([saved], [sharpeDefinition]).requests[0].params).toEqual({window: 90, risk_free_annual_rate: 0.025});
            expect(saved.params.risk_free_annual_rate, 'the saved value is left where it is').toBe(0.04);

            riskFreeRate.set(0);
            expect(buildBackendSignalRequestPlan([config('sharpe-b', 'risk-rolling-sharpe', {window: 90})], [sharpeDefinition]).requests[0].params).toEqual({window: 90, risk_free_annual_rate: 0});
        } finally {
            riskFreeRate.set(0);
        }
    });

    it('maps mixed local/backend/unavailable configs in input order', () => {
        const configs = [config('linear-a', 'linear'), config('ema-a', 'ema'), config('unknown-a', 'removed-signal')];
        const plan = buildBackendSignalRequestPlan(configs, [backendDefinition, localDefinition]);
        const mapped = mapSignalInstanceResults(configs, plan, [result('ema-a', 'ok')]);

        expect(mapped.map((item) => [item.source, item.status])).toEqual([
            ['local', 'local'],
            ['backend', 'ok'],
            ['unavailable', 'missing'],
        ]);
    });

    it.each(['partial', 'unavailable', 'failed'] as const)('preserves backend %s status and structured error', (status) => {
        const backend = config('ema-a', 'ema');
        const plan = buildBackendSignalRequestPlan([backend], [backendDefinition]);
        const mapped = mapSignalInstanceResults([backend], plan, [result('ema-a', status)]);

        expect(mapped[0].status).toBe(status);
        expect(mapped[0].error).toBe(status === 'failed' ? 'compute failed' : null);
    });

    it('rejects stale response application without mutating current state', () => {
        const state = new SignalResultState();
        const oldRequest = state.beginRequest();
        const currentRequest = state.beginRequest();
        const current = [
            {
                config: config('ema-current', 'ema'),
                source: 'backend' as const,
                status: 'ok' as const,
                result: result('ema-current', 'ok'),
                error: null,
            },
        ];

        expect(state.apply(oldRequest, [])).toBe(false);
        expect(state.apply(currentRequest, current)).toBe(true);
        expect(state.values()).toEqual(current);
    });
});
