import {describe, expect, it} from 'vitest';

import type {BackendSignalResult} from '../backendTypes';
import {backendSignalSchemas} from '../backendTypes';
import type {SignalConfig, SignalDefinition} from '../ChartSignal';
import {buildBackendSignalRequestPlan} from '../requestBuilder';
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
