import {describe, expect, it} from 'vitest';

import {backendSignalSchemas} from '../backendTypes';
import type {SignalConfig} from '../ChartSignal';
import type {SignalInstanceResult} from '../resultMapper';
import {getSignalProblem, getSignalProblemSeverity, type SignalProblem} from '../signalProblem';

/**
 * Severity is what the user actually sees: an error badge stops them trusting
 * the line, a notice is a footnote. The mapping tests next door pin the numbers
 * that come out of the backend payload; this file pins the judgement made on
 * them.
 */

const config: SignalConfig = {
    id: 'rsi-a',
    signalType: 'rsi',
    params: {period: 14},
    style: {color: '#3b82f6', lineWidth: 1, lineType: 'solid', markerStart: null, markerEnd: null},
};

/** A problem with nothing wrong in it, so each test states only what it means. */
function problem(overrides: Partial<SignalProblem> = {}): SignalProblem {
    return {
        code: 'partial',
        status: 'partial',
        missingPriceFields: [],
        missingEventTypes: [],
        fieldCoverage: {},
        availablePoints: null,
        requestedPoints: null,
        minimumPoints: null,
        warmupUsedPoints: null,
        warmupRequiredPoints: null,
        missingPoints: null,
        maxConsecutiveMissingPoints: null,
        coverageRatio: null,
        coveragePercent: null,
        selectedStartDate: null,
        selectedEndDate: null,
        excludedPoints: null,
        message: null,
        ...overrides,
    };
}

describe('signal problem severity — a signal that did not compute', () => {
    it.each(['failed', 'unavailable', 'missing'] as const)('calls a %s signal an error whatever else is known', (status) => {
        // No line was drawn, so no amount of coverage detail softens it.
        expect(getSignalProblemSeverity(problem({status, code: 'data_gap', coverageRatio: 1, maxConsecutiveMissingPoints: 0}))).toBe('error');
    });

    it('never calls a partial signal an error', () => {
        // A line exists; the question is only how loudly to qualify it.
        expect(getSignalProblemSeverity(problem({status: 'partial'}))).not.toBe('error');
    });
});

describe('signal problem severity — an incomplete warm-up', () => {
    it('stays a notice while the missing warm-up is under 5% of the window', () => {
        // 4 points short of 20, on a 100-point window: the head of the line is
        // slightly less settled, the rest is unaffected.
        expect(getSignalProblemSeverity(problem({code: 'incomplete_warmup', requestedPoints: 100, warmupUsedPoints: 16, warmupRequiredPoints: 20}))).toBe('notice');
    });

    it('becomes a warning once the shortfall reaches 5% of the window', () => {
        // 5/100 — the boundary itself is a warning.
        expect(getSignalProblemSeverity(problem({code: 'incomplete_warmup', requestedPoints: 100, warmupUsedPoints: 15, warmupRequiredPoints: 20}))).toBe('warning');
    });

    it('scales the judgement to the window, not to the shortfall alone', () => {
        // The same 5 missing points is trivial across 1000 and serious across 20.
        const short = {code: 'incomplete_warmup', warmupUsedPoints: 15, warmupRequiredPoints: 20} as const;
        expect(getSignalProblemSeverity(problem({...short, requestedPoints: 1000}))).toBe('notice');
        expect(getSignalProblemSeverity(problem({...short, requestedPoints: 20}))).toBe('warning');
    });

    it('treats a more-than-complete warm-up as no shortfall at all', () => {
        expect(getSignalProblemSeverity(problem({code: 'incomplete_warmup', requestedPoints: 100, warmupUsedPoints: 40, warmupRequiredPoints: 20}))).toBe('notice');
    });

    it.each([
        ['no window to measure against', {requestedPoints: null}],
        ['an empty window', {requestedPoints: 0}],
        ['an unknown used count', {warmupUsedPoints: null}],
        ['an unknown required count', {warmupRequiredPoints: null}],
    ])('warns rather than guessing when there is %s', (_label, overrides) => {
        expect(getSignalProblemSeverity(problem({code: 'incomplete_warmup', requestedPoints: 100, warmupUsedPoints: 16, warmupRequiredPoints: 20, ...overrides}))).toBe('warning');
    });
});

describe('signal problem severity — gaps in the input', () => {
    /** Good coverage, one short gap: the only shape that can end up a notice. */
    const mild = {coverageRatio: 0.99, maxConsecutiveMissingPoints: 3} as const;

    it.each(['partial_input_coverage', 'data_gap'] as const)('downgrades %s to a notice when the gaps are short and rare', (code) => {
        expect(getSignalProblemSeverity(problem({code, ...mild}))).toBe('notice');
    });

    it.each(['partial', 'insufficient_history', 'missing_input_fields'] as const)('keeps %s a warning however good the coverage', (code) => {
        // Only the two coverage codes describe a merely-gappy series; the rest
        // are about the request itself and are not softened by a good ratio.
        expect(getSignalProblemSeverity(problem({code, ...mild}))).toBe('warning');
    });

    it('warns once more than 5% of the points are missing', () => {
        expect(getSignalProblemSeverity(problem({code: 'data_gap', coverageRatio: 0.951, maxConsecutiveMissingPoints: 3}))).toBe('notice');
        expect(getSignalProblemSeverity(problem({code: 'data_gap', coverageRatio: 0.95, maxConsecutiveMissingPoints: 3}))).toBe('warning');
    });

    it('warns on a single gap longer than a week, even with excellent coverage', () => {
        // A week is the holiday-and-weekend threshold: beyond it the line is
        // bridging real absence, not a closed market.
        expect(getSignalProblemSeverity(problem({code: 'data_gap', coverageRatio: 0.99, maxConsecutiveMissingPoints: 7}))).toBe('notice');
        expect(getSignalProblemSeverity(problem({code: 'data_gap', coverageRatio: 0.99, maxConsecutiveMissingPoints: 8}))).toBe('warning');
    });

    it('warns when the coverage ratio is unknown', () => {
        expect(getSignalProblemSeverity(problem({code: 'data_gap', coverageRatio: null, maxConsecutiveMissingPoints: 3}))).toBe('warning');
    });

    it('falls back to the total missing count when no run length was reported', () => {
        // Up to a week of missing points cannot hide a longer run than itself.
        expect(getSignalProblemSeverity(problem({code: 'data_gap', coverageRatio: 0.99, missingPoints: 7}))).toBe('notice');
    });

    it('warns when the missing points could hide a run longer than a week', () => {
        // 8 missing points with no run length: they might be one long outage.
        expect(getSignalProblemSeverity(problem({code: 'data_gap', coverageRatio: 0.99, missingPoints: 8}))).toBe('warning');
        expect(getSignalProblemSeverity(problem({code: 'data_gap', coverageRatio: 0.99, missingPoints: null}))).toBe('warning');
    });
});

describe('signal problem mapping — which results carry a problem at all', () => {
    function instance(overrides: Partial<SignalInstanceResult>): SignalInstanceResult {
        return {config, source: 'backend', status: 'partial', result: null, error: null, ...overrides};
    }

    it('reports nothing for a signal that has no result yet', () => {
        expect(getSignalProblem(undefined)).toBeNull();
    });

    it.each(['local', 'ok'] as const)('reports nothing for a %s signal', (status) => {
        // Computed in the browser, or computed and fine: neither has a problem
        // to describe.
        expect(getSignalProblem(instance({status, source: status === 'local' ? 'local' : 'backend'}))).toBeNull();
    });

    it('reports a missing result, keeping the reason the mapper attached', () => {
        expect(getSignalProblem(instance({status: 'missing', source: 'unavailable', error: "Signal definition 'rsi' is unavailable"}))).toMatchObject({
            code: 'result_missing',
            status: 'missing',
            message: "Signal definition 'rsi' is unavailable",
            coverageRatio: null,
        });
    });

    it('reports a missing result when the backend answered with no payload', () => {
        // Status and payload disagree; the absent payload wins.
        expect(getSignalProblem(instance({status: 'partial', result: null}))).toMatchObject({code: 'result_missing', status: 'missing'});
    });
});

describe('signal problem mapping — coverage figures', () => {
    function partial(coverage: Record<string, unknown>, warnings: Record<string, unknown>[] = [], reasonCode?: string): SignalProblem {
        const result = backendSignalSchemas.result.parse({
            instance_id: config.id,
            signal_code: 'RSI',
            status: 'partial',
            availability: {
                domain_compatible: true,
                can_compute: true,
                required_points: 14,
                warmup_complete: true,
                reason_code: reasonCode ?? null,
                input_coverage: {
                    requested_points: 100,
                    available_points: 90,
                    contiguous_points: 90,
                    observed_points: 90,
                    backfilled_points: 0,
                    missing_points: 0,
                    internal_gap_count: 1,
                    ...coverage,
                },
            },
            warnings,
        });
        return getSignalProblem({config, source: 'backend', status: 'partial', result, error: null})!;
    }

    it('rounds the coverage percentage down, never flattering the data', () => {
        // 98.79% must not be shown as 98.8%.
        expect(partial({coverage_ratio: 0.9879, missing_points: 1}).coveragePercent).toBe(98.7);
        expect(partial({coverage_ratio: 1, missing_points: 0}).coveragePercent).toBe(100);
    });

    it('distrusts a zero-length gap reported alongside missing points', () => {
        // The two figures contradict each other, so the run length is dropped
        // rather than passed to the UI as a confident "longest gap: 0".
        const contradictory = partial({coverage_ratio: 0.99, missing_points: 3, max_consecutive_missing_points: 0}, [{code: 'data_gap', message: 'gap'}]);

        expect(contradictory.missingPoints).toBe(3);
        expect(contradictory.maxConsecutiveMissingPoints).toBeNull();
        // Severity still resolves it: three missing points cannot form a run
        // longer than three, so the bound is enough to stay a notice.
        expect(getSignalProblemSeverity(contradictory)).toBe('notice');
    });

    it('warns when the dropped run length leaves too many points unaccounted for', () => {
        // Nine missing points with no trustworthy run length might be one
        // outage longer than a week, so the benefit of the doubt runs out.
        const unbounded = partial({coverage_ratio: 0.99, missing_points: 9, max_consecutive_missing_points: 0}, [{code: 'data_gap', message: 'gap'}]);

        expect(unbounded.maxConsecutiveMissingPoints).toBeNull();
        expect(getSignalProblemSeverity(unbounded)).toBe('warning');
    });

    it('believes a zero-length gap when nothing is missing', () => {
        const consistent = partial({coverage_ratio: 1, missing_points: 0, max_consecutive_missing_points: 0}, [{code: 'data_gap', message: 'gap'}]);

        expect(consistent.maxConsecutiveMissingPoints).toBe(0);
        expect(getSignalProblemSeverity(consistent)).toBe('notice');
    });

    it('keeps a backend reason code it recognises', () => {
        expect(partial({coverage_ratio: 0.9, missing_points: 10}, [], 'incompatible_domain').code).toBe('incompatible_domain');
    });

    it('falls back to the result status for a reason code it does not model', () => {
        // `missing_source_capability` is a real availability reason the backend
        // can send and this frontend deliberately does not describe. It must not
        // leak through as an i18n key nothing translates.
        expect(partial({coverage_ratio: 0.9, missing_points: 10}, [], 'missing_source_capability').code).toBe('partial');
    });

    it('falls back for a warning code it does not model either', () => {
        expect(partial({coverage_ratio: 0.9, missing_points: 10}, [{code: 'output_truncated', message: 'truncated'}]).code).toBe('partial');
    });

    it('prefers a non-coverage warning over the gap warning', () => {
        // The gap is already described by the numbers; the other warning is the
        // one carrying news, so it supplies both the code and the message.
        const both = partial({coverage_ratio: 0.9, missing_points: 4}, [
            {code: 'data_gap', message: 'series has gaps'},
            {code: 'incomplete_warmup', message: 'warm-up truncated'},
        ]);

        expect(both).toMatchObject({code: 'incomplete_warmup', message: 'warm-up truncated'});
    });

    it('has no coverage percentage to show when no coverage was reported', () => {
        const result = backendSignalSchemas.result.parse({instance_id: config.id, signal_code: 'RSI', status: 'unavailable'});
        const problem = getSignalProblem({config, source: 'backend', status: 'unavailable', result, error: 'no data source'})!;

        expect(problem).toMatchObject({code: 'unavailable', coverageRatio: null, coveragePercent: null, message: 'no data source'});
    });
});

describe('signal problem mapping — a calculation that threw', () => {
    it('reports the failure while keeping the coverage figures that were gathered', () => {
        // The inputs were fine and the maths was not; showing the coverage keeps
        // the user from hunting for a data problem that is not there.
        const result = backendSignalSchemas.result.parse({
            instance_id: config.id,
            signal_code: 'RSI',
            status: 'failed',
            availability: {
                domain_compatible: true,
                can_compute: true,
                required_points: 14,
                warmup_complete: true,
                input_coverage: {
                    requested_points: 100,
                    available_points: 100,
                    contiguous_points: 100,
                    observed_points: 100,
                    backfilled_points: 0,
                    missing_points: 0,
                    internal_gap_count: 0,
                    coverage_ratio: 1,
                },
            },
            error: {code: 'compute_error', message: 'division by zero'},
        });
        const problem = getSignalProblem({config, source: 'backend', status: 'failed', result, error: 'division by zero'})!;

        expect(problem).toMatchObject({
            code: 'calculation_failed',
            status: 'failed',
            availablePoints: 100,
            requestedPoints: 100,
            coverageRatio: 1,
            message: 'division by zero',
        });
        // Full coverage yet no line: a percentage next to a failure would only
        // suggest the data was the problem.
        expect(problem.coveragePercent).toBeNull();
        expect(getSignalProblemSeverity(problem)).toBe('error');
    });
});
