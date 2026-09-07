import {describe, expect, it, vi} from 'vitest';

import type {RenderedSignal, SignalConfig, SignalDefinition} from '../ChartSignal';
import {resolveSignalPreview} from '../previewPolicy';

const style = {
    color: '#3b82f6',
    lineWidth: 1,
    lineType: 'solid' as const,
    markerStart: null,
    markerEnd: null,
};

const backendDefinition: SignalDefinition = {
    type: 'ema',
    displayName: 'EMA',
    icon: 'chart-spline',
    category: 'indicator',
    paramDescriptors: [],
    source: 'backend',
    backendSignalCode: 'EMA',
};

const localDefinition: SignalDefinition = {
    type: 'linear',
    displayName: 'Linear',
    icon: '📈',
    category: 'benchmark',
    paramDescriptors: [],
    source: 'local',
};

function config(id: string, signalType: string): SignalConfig {
    return {
        id,
        signalType,
        params: {},
        style,
    };
}

function rendered(id: string): RenderedSignal {
    return {
        id,
        label: id,
        data: [{date: '2026-07-23', value: 1}],
        color: style.color,
        lineWidth: 1,
        lineType: 'solid',
        markerStart: null,
        markerEnd: null,
        aggregationProfile: 'last_with_range',
    };
}

describe('chart settings backend preview policy', () => {
    it('never calls the local TypeScript renderer for backend configs', () => {
        const renderLocal = vi.fn(() => [rendered('unexpected')]);
        const resolution = resolveSignalPreview({
            configs: [config('ema-1', 'ema')],
            definitions: [backendDefinition],
            mode: 'global',
            backendSignals: [],
            renderLocal,
        });

        expect(renderLocal).not.toHaveBeenCalled();
        expect(resolution).toEqual({
            signals: [],
            backendState: 'real-target-required',
        });
    });

    it('keeps local benchmark preview active in global mode', () => {
        const localPreview = rendered('linear-1');
        const resolution = resolveSignalPreview({
            configs: [config('linear-1', 'linear')],
            definitions: [localDefinition],
            mode: 'global',
            backendSignals: [],
            renderLocal: () => [localPreview],
        });

        expect(resolution).toEqual({
            signals: [localPreview],
            backendState: 'none',
        });
    });

    it('uses latest page-provided backend results in pair mode', () => {
        const backendPreview = rendered('ema-1:ema');
        const resolution = resolveSignalPreview({
            configs: [config('ema-1', 'ema')],
            definitions: [backendDefinition],
            mode: 'pair',
            backendSignals: [backendPreview],
            renderLocal: () => [],
        });

        expect(resolution).toEqual({
            signals: [backendPreview],
            backendState: 'apply-required',
        });
    });

    it('shows an explicit unavailable state until a pair/asset supplies results', () => {
        const resolution = resolveSignalPreview({
            configs: [config('ema-1', 'ema')],
            definitions: [backendDefinition],
            mode: 'pair',
            backendSignals: [],
            renderLocal: () => [],
        });

        expect(resolution.backendState).toBe('unavailable');
    });
});
