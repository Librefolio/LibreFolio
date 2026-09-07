/**
 * chartSignalsHelpers — pure unit tests (node env, no jsdom).
 *
 * `formatSignalProblem` is translation-heavy, so the translator is injected: the
 * fake here records the *key* and *values* each branch produces and returns the
 * key as its "translation". The tests therefore assert on stable message keys and
 * the computed interpolation values (coverage percentages, joined field lists,
 * '?'-for-null counts) — never on a localized string.
 */
import {describe, expect, it} from 'vitest';

import type {SignalConfig, SignalInputField, SignalProblem} from '$lib/charts/signals';
import {formatSignalProblem, getParamNumber, getParamString, problemCount} from './chartSignalsHelpers';

/** A translator that records every call and echoes the key back. */
function recordingTranslate() {
    const calls: Array<{key: string; values?: Record<string, string | number>}> = [];
    const fn = (key: string, values?: Record<string, string | number>): string => {
        calls.push({key, values});
        return key;
    };
    return {fn, calls};
}

/** Echoes the field name so joined field lists are readable and deterministic. */
const echoFieldLabel = (field: SignalInputField): string => field;

/** A SignalProblem with everything nulled out; `code` (and any override) on top. */
function problem(overrides: Partial<SignalProblem> & Pick<SignalProblem, 'code'>): SignalProblem {
    return {
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

function signal(params: Record<string, unknown>): SignalConfig {
    return {id: 's1', signalType: 'linear', params} as unknown as SignalConfig;
}

describe('problemCount', () => {
    it('renders null as a question mark', () => {
        expect(problemCount(null)).toBe('?');
    });

    it('renders a number as its string, including zero', () => {
        expect(problemCount(0)).toBe('0');
        expect(problemCount(42)).toBe('42');
    });
});

describe('getParamNumber', () => {
    it('returns a numeric param unchanged', () => {
        expect(getParamNumber(signal({period: 14}), 'period', 9)).toBe(14);
        expect(getParamNumber(signal({period: 0}), 'period', 9)).toBe(0);
    });

    it('coerces the fallback when the param is not a number', () => {
        expect(getParamNumber(signal({period: 'abc'}), 'period', 9)).toBe(9);
        expect(getParamNumber(signal({}), 'period', '5')).toBe(5);
    });

    it('treats a null/undefined fallback as zero', () => {
        expect(getParamNumber(signal({}), 'period', null)).toBe(0);
        expect(getParamNumber(signal({}), 'period', undefined)).toBe(0);
    });
});

describe('getParamString', () => {
    it('returns a string param unchanged', () => {
        expect(getParamString(signal({slug: 'EUR-GBP'}), 'slug')).toBe('EUR-GBP');
    });

    it('returns empty string for a non-string or missing param', () => {
        expect(getParamString(signal({slug: 42}), 'slug')).toBe('');
        expect(getParamString(signal({}), 'slug')).toBe('');
    });
});

describe('formatSignalProblem', () => {
    it('missing_input_fields: joins the missing fields (labels), defaulting to OHLCV', () => {
        const t = recordingTranslate();
        formatSignalProblem(problem({code: 'missing_input_fields', missingPriceFields: ['open', 'high']}), t.fn, echoFieldLabel);
        expect(t.calls.at(-1)).toEqual({key: 'chartSettings.signalProblems.missingInputFields', values: {fields: 'open, high'}});

        const t2 = recordingTranslate();
        formatSignalProblem(problem({code: 'missing_input_fields', missingPriceFields: []}), t2.fn, echoFieldLabel);
        expect(t2.calls.at(-1)?.values).toEqual({fields: 'OHLCV'});
    });

    it('insufficient_input_coverage: lists only fields below 100% with truncated percentages', () => {
        const t = recordingTranslate();
        // close is at 1.0 (complete) and must be excluded; open/high are incomplete.
        formatSignalProblem(problem({code: 'insufficient_input_coverage', fieldCoverage: {open: 0.5, high: 0.8, close: 1}, availablePoints: 10, requestedPoints: 20}), t.fn, echoFieldLabel);
        expect(t.calls.at(-1)).toEqual({
            key: 'chartSettings.signalProblems.incompleteInputCoverage',
            values: {fields: 'open 50%, high 80%', available: '10', requested: '20'},
        });
    });

    it('insufficient_input_coverage: truncates (not rounds) the coverage percentage', () => {
        const t = recordingTranslate();
        // 0.9999 -> floor(999.9)/10 = 99.9, never 100.
        formatSignalProblem(problem({code: 'insufficient_input_coverage', fieldCoverage: {open: 0.9999}}), t.fn, echoFieldLabel);
        expect(t.calls.at(-1)?.values?.fields).toBe('open 99.9%');
    });

    it('insufficient_input_coverage: falls back to OHLCV when nothing is incomplete', () => {
        const t = recordingTranslate();
        formatSignalProblem(problem({code: 'insufficient_input_coverage', fieldCoverage: {open: 1}}), t.fn, echoFieldLabel);
        expect(t.calls.at(-1)?.values?.fields).toBe('OHLCV');
    });

    it('insufficient_history: renders available/required with ? for null', () => {
        const t = recordingTranslate();
        formatSignalProblem(problem({code: 'insufficient_history', availablePoints: 5, minimumPoints: null}), t.fn, echoFieldLabel);
        expect(t.calls.at(-1)).toEqual({key: 'chartSettings.signalProblems.insufficientHistory', values: {available: '5', required: '?'}});
    });

    it('incomplete_warmup: renders used/required counts', () => {
        const t = recordingTranslate();
        formatSignalProblem(problem({code: 'incomplete_warmup', warmupUsedPoints: 3, warmupRequiredPoints: 10}), t.fn, echoFieldLabel);
        expect(t.calls.at(-1)).toEqual({key: 'chartSettings.signalProblems.incompleteWarmup', values: {used: '3', required: '10'}});
    });

    it('data_gap with a selected segment uses the contiguous-segment message', () => {
        const t = recordingTranslate();
        formatSignalProblem(
            problem({
                code: 'data_gap',
                selectedStartDate: '2024-01-01',
                selectedEndDate: '2024-02-01',
                excludedPoints: 2,
                availablePoints: 18,
                requestedPoints: 20,
                coveragePercent: 90,
                maxConsecutiveMissingPoints: 3,
            }),
            t.fn,
            echoFieldLabel,
        );
        expect(t.calls.at(-1)).toEqual({
            key: 'chartSettings.signalProblems.partialContiguousSegment',
            values: {start: '2024-01-01', end: '2024-02-01', excluded: '2', available: '18', requested: '20', coverage: '90', consecutive: '3'},
        });
    });

    it('data_gap without a selected segment uses the generic data-gaps message', () => {
        const t = recordingTranslate();
        formatSignalProblem(problem({code: 'data_gap', missingPoints: 4, requestedPoints: 20, coveragePercent: 80}), t.fn, echoFieldLabel);
        expect(t.calls.at(-1)).toEqual({key: 'chartSettings.signalProblems.dataGaps', values: {missing: '4', requested: '20', coverage: '80'}});
    });

    it('missing_event_types: joins the event types, defaulting to ?', () => {
        const t = recordingTranslate();
        formatSignalProblem(problem({code: 'missing_event_types', missingEventTypes: ['dividend', 'split']}), t.fn, echoFieldLabel);
        expect(t.calls.at(-1)).toEqual({key: 'chartSettings.signalProblems.missingEvents', values: {events: 'dividend, split'}});

        const t2 = recordingTranslate();
        formatSignalProblem(problem({code: 'missing_event_types', missingEventTypes: []}), t2.fn, echoFieldLabel);
        expect(t2.calls.at(-1)?.values).toEqual({events: '?'});
    });

    it('incompatible_domain: a plain message with no values', () => {
        const t = recordingTranslate();
        const out = formatSignalProblem(problem({code: 'incompatible_domain'}), t.fn, echoFieldLabel);
        expect(out).toBe('chartSettings.signalProblems.incompatibleDomain');
        expect(t.calls.at(-1)).toEqual({key: 'chartSettings.signalProblems.incompatibleDomain', values: undefined});
    });

    it('calculation_failed: uses the problem message, else the common error key', () => {
        const t = recordingTranslate();
        formatSignalProblem(problem({code: 'calculation_failed', message: 'boom'}), t.fn, echoFieldLabel);
        expect(t.calls.at(-1)).toEqual({key: 'chartSettings.signalProblems.calculationFailed', values: {message: 'boom'}});

        const t2 = recordingTranslate();
        formatSignalProblem(problem({code: 'calculation_failed', message: null}), t2.fn, echoFieldLabel);
        // With no message the inner common.error key is resolved and passed through.
        expect(t2.calls.map((c) => c.key)).toEqual(['common.error', 'chartSettings.signalProblems.calculationFailed']);
        expect(t2.calls.at(-1)?.values).toEqual({message: 'common.error'});
    });

    it('result_missing: a plain message', () => {
        const t = recordingTranslate();
        const out = formatSignalProblem(problem({code: 'result_missing'}), t.fn, echoFieldLabel);
        expect(out).toBe('chartSettings.signalProblems.resultMissing');
    });

    it('partial/unavailable: the problem message wins over the fallback key', () => {
        const t = recordingTranslate();
        expect(formatSignalProblem(problem({code: 'partial', message: 'halfway'}), t.fn, echoFieldLabel)).toBe('halfway');
        // message present -> the fallback key is never translated.
        expect(t.calls).toHaveLength(0);

        const t2 = recordingTranslate();
        expect(formatSignalProblem(problem({code: 'partial', message: null}), t2.fn, echoFieldLabel)).toBe('chartSettings.signalProblems.partialResult');

        const t3 = recordingTranslate();
        expect(formatSignalProblem(problem({code: 'unavailable', message: 'gone'}), t3.fn, echoFieldLabel)).toBe('gone');
        const t4 = recordingTranslate();
        expect(formatSignalProblem(problem({code: 'unavailable', message: null}), t4.fn, echoFieldLabel)).toBe('chartSettings.signalProblems.unavailable');
    });
});
