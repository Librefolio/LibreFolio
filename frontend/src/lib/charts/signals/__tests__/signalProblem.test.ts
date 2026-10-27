import {describe, expect, it} from 'vitest';

import {backendSignalSchemas} from '../backendTypes';
import type {SignalConfig} from '../ChartSignal';
import type {SignalInstanceResult} from '../resultMapper';
import {getSignalProblem, getSignalProblemSeverity} from '../signalProblem';

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
        max_consecutive_missing_points: 0,
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

    it('preserves undefined_metric as the unavailable reason code', () => {
        const result = backendSignalSchemas.result.parse({
            instance_id: config.id,
            signal_code: 'CCI',
            status: 'unavailable',
            availability: {
                domain_compatible: true,
                can_compute: false,
                input_coverage: inputCoverage(),
                required_points: 20,
                warmup_complete: false,
                reason_code: 'undefined_metric',
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

        expect(getSignalProblem(item)?.code).toBe('undefined_metric');
    });

    it('preserves partial_undefined_metric when its warning code is not a problem code', () => {
        const backendMessage = 'Metric is undefined for part of the selected window';
        const result = backendSignalSchemas.result.parse({
            instance_id: config.id,
            signal_code: 'CCI',
            status: 'partial',
            series: [
                {
                    kind: 'line',
                    key: 'cci',
                    label_key: 'signals.cci.label',
                    semantic_id: 'momentum.cci',
                    semantic_description: 'Commodity Channel Index momentum output.',
                    unit: 'index',
                    axis: {key: 'cci', role: 'independent'},
                    points: [{date: '2026-01-01', value: 12}],
                },
            ],
            availability: {
                domain_compatible: true,
                can_compute: true,
                input_coverage: inputCoverage(),
                required_points: 20,
                warmup_complete: true,
                partial_coverage_used: true,
                reason_code: 'partial_undefined_metric',
            },
            warmup: {
                requirement: {
                    minimum_points: 20,
                    stabilization_points: 0,
                    total_points: 20,
                },
                loaded_points: 100,
                used_points: 100,
                complete: true,
            },
            warnings: [{code: 'undefined_metric_window', message: backendMessage}],
        });
        const item: SignalInstanceResult = {
            config,
            source: 'backend',
            status: 'partial',
            result,
            error: null,
        };

        expect(getSignalProblem(item)).toMatchObject({
            code: 'partial_undefined_metric',
            message: backendMessage,
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
                    semantic_id: 'momentum.cci',
                    semantic_description: 'Commodity Channel Index momentum output.',
                    unit: 'index',
                    axis: {key: 'cci', role: 'independent'},
                    points: [{date: '2026-01-01', value: 12}],
                },
            ],
            availability: {
                domain_compatible: true,
                can_compute: true,
                input_coverage: inputCoverage({
                    available_points: 99,
                    contiguous_points: 99,
                    observed_points: 99,
                    missing_points: 1,
                    max_consecutive_missing_points: 1,
                    coverage_ratio: 0.99,
                }),
                required_points: 40,
                warmup_complete: false,
                partial_coverage_used: true,
                reason_code: 'partial_input_coverage',
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
            warnings: [
                {code: 'incomplete_warmup', message: 'Signal warm-up is incomplete'},
                {
                    code: 'partial_input_coverage',
                    message: 'Signal used one complete contiguous input segment',
                    details: {
                        selected_start_date: '2026-01-01',
                        selected_end_date: '2026-01-01',
                        excluded_points: 1,
                        max_consecutive_missing_points: 1,
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

        const problem = getSignalProblem(item);
        expect(problem).toMatchObject({
            code: 'incomplete_warmup',
            warmupUsedPoints: 5,
            warmupRequiredPoints: 40,
        });
        expect(getSignalProblemSeverity(problem!)).toBe('warning');
        expect(
            getSignalProblemSeverity({
                ...problem!,
                requestedPoints: 9_292,
                warmupUsedPoints: 0,
                warmupRequiredPoints: 2,
            }),
        ).toBe('notice');
        expect(
            getSignalProblemSeverity({
                ...problem!,
                requestedPoints: 7,
                warmupUsedPoints: 0,
                warmupRequiredPoints: 2,
            }),
        ).toBe('warning');
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
                    semantic_id: 'momentum.cci',
                    semantic_description: 'Commodity Channel Index momentum output.',
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

        const problem = getSignalProblem(item);
        expect(problem).toMatchObject({
            code: 'partial_input_coverage',
            selectedStartDate: '2025-07-23',
            selectedEndDate: '2026-07-21',
            excludedPoints: 2,
            maxConsecutiveMissingPoints: null,
        });
        expect(getSignalProblemSeverity(problem!)).toBe('notice');
        expect(
            getSignalProblemSeverity({
                ...problem!,
                missingPoints: 2,
                maxConsecutiveMissingPoints: null,
                coverageRatio: 616 / 618,
                coveragePercent: 99.6,
            }),
        ).toBe('notice');
        expect(
            getSignalProblemSeverity({
                ...problem!,
                missingPoints: 2,
                maxConsecutiveMissingPoints: 2,
                coverageRatio: 616 / 618,
                coveragePercent: 99.6,
            }),
        ).toBe('notice');
        expect(
            getSignalProblemSeverity({
                ...problem!,
                missingPoints: 2,
                maxConsecutiveMissingPoints: 7,
                coverageRatio: 0.951,
                coveragePercent: 95.1,
            }),
        ).toBe('notice');
        expect(
            getSignalProblemSeverity({
                ...problem!,
                maxConsecutiveMissingPoints: 8,
                coverageRatio: 0.996,
                coveragePercent: 99.6,
            }),
        ).toBe('warning');
        expect(
            getSignalProblemSeverity({
                ...problem!,
                maxConsecutiveMissingPoints: 2,
                coverageRatio: 0.95,
                coveragePercent: 95,
            }),
        ).toBe('warning');
    });

    describe('the days an undefined metric window leaves out (Z5-F1)', () => {
        /** A calendar-return result as the backend sends it: `reasonCode` on its availability, `details` on its warning. */
        function undefinedWindowItem(status: 'partial' | 'unavailable', reasonCode: string, details?: Record<string, unknown>): SignalInstanceResult {
            const result = backendSignalSchemas.result.parse({
                instance_id: config.id,
                signal_code: 'ASSET_CALENDAR_ROLLING_RETURN',
                status,
                availability: {
                    domain_compatible: true,
                    can_compute: status === 'partial',
                    input_coverage: inputCoverage(),
                    required_points: 30,
                    warmup_complete: true,
                    reason_code: reasonCode,
                },
                warmup: {requirement: {minimum_points: 1, stabilization_points: 29, total_points: 30}, loaded_points: 100, used_points: 100, complete: true},
                warnings: [{code: 'undefined_metric_window', message: 'One or more calendar-return points are unavailable', ...(details ? {details} : {})}],
                ...(status === 'partial' ? {series: [{kind: 'line', key: 'calendar_return', label_key: 'k', semantic_id: 's', semantic_description: 'd', unit: 'percentage', axis: {key: 'calendar_return', role: 'independent'}, points: [{date: '2026-01-01', value: 1}]}]} : {}),
            });
            return {config, source: 'backend', status, result, error: null};
        }

        const DETAILS = {unavailable_points: 3, reasons: {missing_reference: 3}, unavailable_start: '2026-02-03', unavailable_end: '2026-02-05', resync_start: '2025-12-01', resync_end: '2026-02-05'};

        it('reads the count, the undefined days and the period to sync again from the warning of a partial result', () => {
            expect(getSignalProblem(undefinedWindowItem('partial', 'partial_undefined_metric', DETAILS))).toMatchObject({
                code: 'partial_undefined_metric',
                unavailablePoints: 3,
                unavailableStart: '2026-02-03',
                unavailableEnd: '2026-02-05',
                resyncStart: '2025-12-01',
                resyncEnd: '2026-02-05',
            });
        });

        it('reads them from the warning of an unavailable result too', () => {
            expect(getSignalProblem(undefinedWindowItem('unavailable', 'undefined_metric', DETAILS))).toMatchObject({
                code: 'undefined_metric',
                unavailablePoints: 3,
                unavailableStart: '2026-02-03',
                resyncStart: '2025-12-01',
            });
        });

        it('leaves them null when the warning has no details, as the other signals’ do not', () => {
            expect(getSignalProblem(undefinedWindowItem('partial', 'partial_undefined_metric'))).toMatchObject({unavailablePoints: null, unavailableStart: null, unavailableEnd: null, resyncStart: null, resyncEnd: null});
        });

        it('ignores a detail that is not a day or a count', () => {
            const problem = getSignalProblem(undefinedWindowItem('partial', 'partial_undefined_metric', {...DETAILS, unavailable_start: 20260203, resync_end: null, unavailable_points: 'many'}));

            expect(problem).toMatchObject({unavailablePoints: null, unavailableStart: null, resyncEnd: null, unavailableEnd: '2026-02-05'});
        });
    });
});
