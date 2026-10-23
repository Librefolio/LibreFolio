/**
 * chartSignalsHelpers — pure unit tests (node env, no jsdom).
 *
 * `formatSignalProblem` is translation-heavy, so the translator is injected: the
 * fake here records the *key* and *values* each branch produces and returns the
 * key as its "translation". The tests therefore assert on stable message keys and
 * the computed interpolation values (coverage percentages, joined field lists,
 * '?'-for-null counts) — never on a localized string. The coverage percentages are
 * figures, written in the interface language (M-18): the English cases run under an
 * English UI on an en-US browser, and the last describe switches the UI.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

// The interface locale is the UI language regionalised by `navigator.language` (M-18). Node's tag
// follows the host's ICU locale, so it is pinned to en-US — jsdom's own — before any import.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import type {SignalConfig, SignalInputField, SignalProblem} from '$lib/charts/signals';
import {currentLanguage} from '$lib/stores/app/language';
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
        unavailablePoints: null,
        unavailableStart: null,
        unavailableEnd: null,
        resyncStart: null,
        resyncEnd: null,
        message: null,
        ...overrides,
    };
}

function signal(params: Record<string, unknown>): SignalConfig {
    return {id: 's1', signalType: 'linear', params} as unknown as SignalConfig;
}

/** `value` as JSON with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
function spelled(value: unknown): string {
    return JSON.stringify(value).replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
}

/**
 * Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. The language
 * is module state: every block that switches it puts English back after each of its tests.
 */
async function uiLanguage(lang: 'en' | 'it' | 'fr'): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
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

    it('insufficient_history: keeps an ordinary positive requirement translated and count-based', () => {
        const t = recordingTranslate();
        const out = formatSignalProblem(problem({code: 'insufficient_history', availablePoints: 5, minimumPoints: 8, message: 'backend detail'}), t.fn, echoFieldLabel);

        expect(out).toBe('chartSettings.signalProblems.insufficientHistory');
        expect(t.calls).toEqual([{key: 'chartSettings.signalProblems.insufficientHistory', values: {available: '5', required: '8'}}]);
    });

    it('insufficient_history: returns the backend reason when zero is not a real point requirement', () => {
        const t = recordingTranslate();
        const backendReason = 'No overlapping history remains after alignment';
        const out = formatSignalProblem(problem({code: 'insufficient_history', availablePoints: 0, minimumPoints: 0, message: backendReason}), t.fn, echoFieldLabel);

        expect(out).toBe(backendReason);
        expect(t.calls).toEqual([]);
    });

    it('undefined_metric: uses the backend warning message, else the unavailable fallback', () => {
        const t = recordingTranslate();
        const backendMessage = 'backend undefined-metric warning';
        expect(formatSignalProblem(problem({code: 'undefined_metric', message: backendMessage}), t.fn, echoFieldLabel)).toBe(backendMessage);
        expect(t.calls).toEqual([]);

        const fallback = recordingTranslate();
        expect(formatSignalProblem(problem({code: 'undefined_metric', message: null}), fallback.fn, echoFieldLabel)).toBe('chartSettings.signalProblems.unavailable');
        expect(fallback.calls).toEqual([{key: 'chartSettings.signalProblems.unavailable', values: undefined}]);
    });

    it('partial_undefined_metric: uses the backend warning message, else the partial-result fallback', () => {
        const t = recordingTranslate();
        const backendMessage = 'backend partial undefined-metric warning';
        expect(formatSignalProblem(problem({code: 'partial_undefined_metric', message: backendMessage}), t.fn, echoFieldLabel)).toBe(backendMessage);
        expect(t.calls).toEqual([]);

        const fallback = recordingTranslate();
        expect(formatSignalProblem(problem({code: 'partial_undefined_metric', message: null}), fallback.fn, echoFieldLabel)).toBe('chartSettings.signalProblems.partialResult');
        expect(fallback.calls).toEqual([{key: 'chartSettings.signalProblems.partialResult', values: undefined}]);
    });

    describe('the undefined window of the calendar return (Z5-F1)', () => {
        const WINDOW = {unavailablePoints: 3, unavailableStart: '2026-02-03', unavailableEnd: '2026-02-05', resyncStart: '2025-12-01', resyncEnd: '2026-02-05'};

        it('partial_undefined_metric with the days: says them from the catalogue, not from the plugin’s English sentence', () => {
            const t = recordingTranslate();
            const text = formatSignalProblem(problem({code: 'partial_undefined_metric', message: 'One or more calendar-return points are unavailable', ...WINDOW}), t.fn, echoFieldLabel);

            expect(text).toBe('chartSettings.signalProblems.undefinedWindowPartial');
            expect(t.calls).toEqual([{key: 'chartSettings.signalProblems.undefinedWindowPartial', values: {count: '3', start: '2026-02-03', end: '2026-02-05', resyncStart: '2025-12-01', resyncEnd: '2026-02-05'}}]);
        });

        it('undefined_metric with the days: the same, in the unavailable form', () => {
            const t = recordingTranslate();
            formatSignalProblem(problem({code: 'undefined_metric', status: 'unavailable', message: 'Calendar return is undefined for every point in the selected range', ...WINDOW}), t.fn, echoFieldLabel);

            expect(t.calls).toEqual([{key: 'chartSettings.signalProblems.undefinedWindowUnavailable', values: {count: '3', start: '2026-02-03', end: '2026-02-05', resyncStart: '2025-12-01', resyncEnd: '2026-02-05'}}]);
        });

        it('a window without its days keeps the old rule: the backend message, else the generic sentence', () => {
            const t = recordingTranslate();

            expect(formatSignalProblem(problem({code: 'partial_undefined_metric', message: 'backend sentence', ...WINDOW, unavailableStart: null}), t.fn, echoFieldLabel)).toBe('backend sentence');
            expect(t.calls).toEqual([]);
        });
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

/**
 * M-18 CP2: the field coverage in the interface language.
 *
 * `insufficient_input_coverage` lists each incomplete field with its coverage, floored to one decimal and
 * interpolated, `${percentage}%`: an Italian reader gets `high 87.6%` inside an Italian sentence. Every
 * figure is written in the interface language (the developer's decision M-18, 2026-10-12): the coverage
 * becomes `formatPercent(percentage, {digits: 1, signed: false, trim: true})` — the one decimal it may
 * have, none when it has none, in the interface locale. The floor stays: `99.9`, never `100`.
 *
 * Read: the `fields` value handed to the translator, as the rest of this file reads it. Expectations from
 * `Intl` in an explicit locale: a percent with at most one decimal, after `toFixed(1)`.
 */
describe('formatSignalProblem — the field coverage in the interface language (M-18)', () => {
    /** open at half, high at 87.65% floored to 87.6, low at 99.99% floored to 99.9; close complete, so left out. */
    const COVERAGE = {open: 0.5, high: 0.8765, low: 0.9999, close: 1};

    /** A coverage as the message must write it in `localeTag`: at most one decimal, after `toFixed(1)`. */
    const percentIn = (value: number, localeTag: string) => new Intl.NumberFormat(localeTag, {style: 'percent', minimumFractionDigits: 0, maximumFractionDigits: 1}).format(Number(value.toFixed(1)) / 100);

    /** The `fields` value the coverage branch hands the translator. */
    function fieldsWritten(): string | number | undefined {
        const t = recordingTranslate();
        formatSignalProblem(problem({code: 'insufficient_input_coverage', fieldCoverage: COVERAGE, availablePoints: 10, requestedPoints: 20}), t.fn, echoFieldLabel);
        expect(t.calls.at(-1)?.key, 'the coverage branch fired').toBe('chartSettings.signalProblems.incompleteInputCoverage');
        return t.calls.at(-1)?.values?.fields;
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it('English UI on an en-US browser (guard): today’s text, floored, with the decimal it has', async () => {
        await uiLanguage('en');

        expect(fieldsWritten()).toBe('open 50%, high 87.6%, low 99.9%');
    });

    it.each(['it', 'fr'] as const)('%s UI: each incomplete field’s coverage as that language writes a percentage, floored, with the decimal it has', async (lang) => {
        await uiLanguage(lang);
        const expected = `open ${percentIn(50, lang)}, high ${percentIn(87.6, lang)}, low ${percentIn(99.9, lang)}`;
        // Control: this runtime carries the language's data, so its coverage is not written the English way.
        expect(percentIn(87.6, lang), `${lang} differs from English`).not.toBe('87.6%');

        expect(fieldsWritten(), spelled(expected)).toBe(expected);
    });
});

/**
 * M-18 CP2: the counts and the coverage of the signal messages in the interface language.
 *
 * `problemCount` writes every count and the coverage the messages interpolate — points available,
 * requested, missing and excluded, the warm-up used and required, the longest gap, the coverage of the
 * data — with `String(value)`: an Italian reader gets `12345` and `copertura 87.5%` inside an Italian
 * sentence. The catalogues write the `%` themselves (`{coverage}%`, French `{coverage} %`), so the value
 * stays a bare number. Every figure is written in the interface language (the developer's decision M-18,
 * 2026-10-12): `problemCount` becomes `formatFixed(value, 1, {trim: true})` — a count keeps no decimal,
 * the coverage its one floored decimal, both grouped and written as the interface locale writes numbers.
 * An unknown value stays `?`.
 *
 * English on an en-US browser keeps today's text below 1,000 and is grouped from 1,000 on — `12,345`, the
 * new contract. Italian groups only from 10,000, so the counts read here have five digits.
 *
 * Read: the values each branch hands the injected translator, as the rest of this file reads them — the
 * numeric ones only; dates and names pass through untouched and are not this block's subject.
 * Expectations from `Intl` in an explicit locale: a number with at most one decimal, after `toFixed(1)`.
 */
describe('problemCount — the counts and the coverage of the signal messages in the interface language (M-18)', () => {
    /** A number as a message must write it in `localeTag`: grouped, with at most one decimal, after `toFixed(1)`. */
    const numberIn = (value: number, localeTag: string) => new Intl.NumberFormat(localeTag, {minimumFractionDigits: 0, maximumFractionDigits: 1}).format(Number(value.toFixed(1)));

    /** Each branch that interpolates counts or a coverage: the problem it is given, and the numbers it must hand over, by value name. */
    const CASES = [
        {
            key: 'chartSettings.signalProblems.dataGaps',
            given: problem({code: 'data_gap', missingPoints: 12_345, requestedPoints: 98_765, coveragePercent: 87.5}),
            numbers: {missing: 12_345, requested: 98_765, coverage: 87.5},
        },
        {
            key: 'chartSettings.signalProblems.partialContiguousSegment',
            given: problem({
                code: 'data_gap',
                selectedStartDate: '2024-01-01',
                selectedEndDate: '2024-02-01',
                excludedPoints: 12_345,
                availablePoints: 86_420,
                requestedPoints: 98_765,
                coveragePercent: 87.5,
                maxConsecutiveMissingPoints: 3,
            }),
            numbers: {excluded: 12_345, available: 86_420, requested: 98_765, coverage: 87.5, consecutive: 3},
        },
        {
            key: 'chartSettings.signalProblems.incompleteWarmup',
            given: problem({code: 'incomplete_warmup', warmupUsedPoints: 12_345, warmupRequiredPoints: 20_000}),
            numbers: {used: 12_345, required: 20_000},
        },
        {
            key: 'chartSettings.signalProblems.insufficientHistory',
            given: problem({code: 'insufficient_history', availablePoints: 12_345, minimumPoints: 20_000}),
            numbers: {available: 12_345, required: 20_000},
        },
        {
            key: 'chartSettings.signalProblems.incompleteInputCoverage',
            given: problem({code: 'insufficient_input_coverage', fieldCoverage: {open: 0.5}, availablePoints: 12_345, requestedPoints: 98_765}),
            numbers: {available: 12_345, requested: 98_765},
        },
    ];

    /** What each branch hands the translator: its key, and its numeric values by name. */
    function written(): Array<{key: string; values: Record<string, unknown>}> {
        return CASES.map(({given, numbers}) => {
            const t = recordingTranslate();
            formatSignalProblem(given, t.fn, echoFieldLabel);
            const last = t.calls.at(-1);
            return {key: last?.key ?? '(no translator call)', values: Object.fromEntries(Object.keys(numbers).map((name) => [name, last?.values?.[name]]))};
        });
    }

    /** What each branch must hand the translator in `localeTag`. */
    function expectedIn(localeTag: string): Array<{key: string; values: Record<string, unknown>}> {
        return CASES.map(({key, numbers}) => ({key, values: Object.fromEntries(Object.entries(numbers).map(([name, value]) => [name, numberIn(value, localeTag)]))}));
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it('English UI on an en-US browser (guard): a count or a coverage below 1,000 is today’s text, and an unknown one is ?', async () => {
        await uiLanguage('en');

        expect([problemCount(0), problemCount(42), problemCount(999), problemCount(87.5), problemCount(null)]).toEqual(['0', '42', '999', '87.5', '?']);
    });

    it('English UI on an en-US browser: a count from 1,000 on is grouped, `12,345` where today reads `12345` — the new contract', async () => {
        await uiLanguage('en');
        const expected = expectedIn('en-US');
        // Control: the grouped text of the rule, which today's `String(value)` is not; the coverage reads as today.
        expect(expected[0].values).toEqual({missing: '12,345', requested: '98,765', coverage: '87.5'});

        expect(written(), spelled(expected)).toEqual(expected);
    });

    it.each(['it', 'fr'] as const)('%s UI: every count and the coverage handed to the messages in that language — grouped, the coverage with its decimal', async (lang) => {
        await uiLanguage(lang);
        const expected = expectedIn(lang);
        // Controls: this runtime carries the language's data — it groups five digits and writes a decimal
        // comma — so neither figure reads the English way.
        expect(numberIn(12_345, lang), `${lang} groups 12345`).not.toBe('12345');
        expect(numberIn(87.5, lang), `${lang} writes 87.5 with a comma`).not.toBe('87.5');

        expect(written(), spelled(expected)).toEqual(expected);
    });

    it.each(['it', 'fr'] as const)('%s UI (guard): an unknown count is still ?', async (lang) => {
        await uiLanguage(lang);
        const t = recordingTranslate();
        formatSignalProblem(problem({code: 'insufficient_history', availablePoints: 12_345, minimumPoints: null}), t.fn, echoFieldLabel);

        expect({required: t.calls.at(-1)?.values?.required, direct: problemCount(null)}).toEqual({required: '?', direct: '?'});
    });
});
