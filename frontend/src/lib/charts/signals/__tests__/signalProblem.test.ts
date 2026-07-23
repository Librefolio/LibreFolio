import {describe, expect, it} from 'vitest';

import {backendSignalSchemas} from '../backendTypes';
import type {SignalConfig} from '../ChartSignal';
import type {SignalInstanceResult} from '../resultMapper';
import {getSignalProblem} from '../signalProblem';

const config: SignalConfig = {
    id: 'cci-a',
    signalType: 'cci',
    params: {period: 20},
    style: {
        color: '#3b82f6',
        lineWidth: 1,
        lineType: 'solid',
        markerStart: null,
        markerEnd: null,
    },
};

function inputCoverage(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        requested_points: 100,
        available_points: 100,
        contiguous_points: 100,
        observed_points: 100,
        backfilled_points: 0,
        missing_points: 0,
        internal_gap_count: 0,
        coverage_ratio: 1,
        field_coverage: {close: 1, high: 0, low: 0},
        ...overrides,
    };
}

describe('signal problem mapping', () => {
    it('preserves missing OHLCV fields even when dated points exist', () => {
        const result = backendSignalSchemas.result.parse({
            instance_id: config.id,
            signal_code: 'CCI',
            status: 'unavailable',
            availability: {
                domain_compatible: true,
                can_compute: false,
                missing_price_fields: ['high', 'low'],
                input_coverage: inputCoverage(),
                required_points: 20,
                warmup_complete: false,
                reason_code: 'missing_input_fields',
            },
            warmup: {
                requirement: {
                    minimum_points: 20,
                    stabilization_points: 0,
                    total_points: 20,
                },
                loaded_points: 100,
                used_points: 0,
                complete: false,
            },
        });
        const item: SignalInstanceResult = {
            config,
            source: 'backend',
            status: 'unavailable',
            result,
            error: null,
        };

        expect(getSignalProblem(item)).toMatchObject({
            code: 'missing_input_fields',
            missingPriceFields: ['high', 'low'],
            availablePoints: 100,
            requestedPoints: 100,
        });
    });

    it('reports incomplete warm-up counts for partial results', () => {
        const result = backendSignalSchemas.result.parse({
            instance_id: config.id,
            signal_code: 'CCI',
            status: 'partial',
            series: [
                {
                    kind: 'line',
                    key: 'cci',
                    label_key: 'signals.cci.label',
                    unit: 'index',
                    axis: {key: 'cci', role: 'independent'},
                    points: [{date: '2026-01-01', value: 12}],
                },
            ],
            availability: {
                domain_compatible: true,
                can_compute: true,
                input_coverage: inputCoverage(),
                required_points: 40,
                warmup_complete: false,
                reason_code: 'incomplete_warmup',
            },
            warmup: {
                requirement: {
                    minimum_points: 20,
                    stabilization_points: 20,
                    total_points: 40,
                },
                loaded_points: 25,
                used_points: 5,
                complete: false,
            },
            warnings: [{code: 'incomplete_warmup', message: 'Signal warm-up is incomplete'}],
        });
        const item: SignalInstanceResult = {
            config,
            source: 'backend',
            status: 'partial',
            result,
            error: null,
        };

        expect(getSignalProblem(item)).toMatchObject({
            code: 'incomplete_warmup',
            warmupUsedPoints: 5,
            warmupRequiredPoints: 40,
        });
    });

    it('maps contiguous-segment details for partial coverage', () => {
        const result = backendSignalSchemas.result.parse({
            instance_id: config.id,
            signal_code: 'CCI',
            status: 'partial',
            series: [
                {
                    kind: 'line',
                    key: 'cci',
                    label_key: 'signals.cci.label',
                    unit: 'index',
                    axis: {key: 'cci', role: 'independent'},
                    points: [{date: '2026-07-21', value: 12}],
                },
            ],
            availability: {
                domain_compatible: true,
                can_compute: true,
                input_coverage: inputCoverage({
                    requested_points: 618,
                    available_points: 617,
                    contiguous_points: 616,
                    missing_points: 1,
                    coverage_ratio: 617 / 618,
                }),
                required_points: 14,
                warmup_complete: true,
                partial_coverage_used: true,
                reason_code: 'partial_input_coverage',
            },
            warmup: {
                requirement: {
                    minimum_points: 14,
                    stabilization_points: 0,
                    total_points: 14,
                },
                loaded_points: 618,
                used_points: 252,
                complete: true,
            },
            warnings: [
                {
                    code: 'partial_input_coverage',
                    message: 'Signal used one complete contiguous input segment',
                    details: {
                        selected_start_date: '2025-07-23',
                        selected_end_date: '2026-07-21',
                        excluded_points: 2,
                    },
                },
            ],
        });
        const item: SignalInstanceResult = {
            config,
            source: 'backend',
            status: 'partial',
            result,
            error: null,
        };

        expect(getSignalProblem(item)).toMatchObject({
            code: 'partial_input_coverage',
            selectedStartDate: '2025-07-23',
            selectedEndDate: '2026-07-21',
            excludedPoints: 2,
        });
    });
});
