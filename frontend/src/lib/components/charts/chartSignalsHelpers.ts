/**
 * Pure helpers extracted from ChartSignalsSection.svelte.
 *
 * The section is a large, translation-heavy component, but a few pieces are pure
 * data logic worth testing in isolation:
 *  - `formatSignalProblem` selects one of ~14 message branches from a
 *    `SignalProblem` and computes the numbers that go into it (coverage
 *    percentages, missing-field lists). The translation itself is injected, so a
 *    test can assert *which* branch fired and *what values* it computed without
 *    ever asserting a translated string.
 *  - `getParamNumber` / `getParamString` read a signal's loosely-typed params
 *    with a type guard and a fallback.
 *  - `problemCount` renders a nullable count as `'?'` or its number.
 *
 * @module charts/chartSignalsHelpers
 */

import type {SignalConfig, SignalInputField, SignalProblem} from '$lib/charts/signals';

/** Canonical OHLCV field order used for coverage listings. */
export const INPUT_FIELD_ORDER: SignalInputField[] = ['open', 'high', 'low', 'close', 'volume'];

/** Translate a message key with optional interpolation values. Injected so the
 *  pure logic never depends on the i18n store. */
export type SignalProblemTranslate = (key: string, values?: Record<string, string | number>) => string;

/** Human label for an input field (also injected — it is a translation too). */
export type SignalFieldLabel = (field: SignalInputField) => string;

/** A nullable count rendered for a message: `'?'` when unknown, else the number. */
export function problemCount(value: number | null): string {
    return value === null ? '?' : String(value);
}

/**
 * Turn a `SignalProblem` into a user message by selecting the branch for its
 * `code` and filling in the interpolation values. `translate` and `fieldLabel`
 * are injected, so this function is pure: it decides the message *key* and the
 * *values*, and leaves the actual localization to the caller.
 */
export function formatSignalProblem(problem: SignalProblem, translate: SignalProblemTranslate, fieldLabel: SignalFieldLabel): string {
    const missingFields = problem.missingPriceFields.map(fieldLabel).join(', ');
    const incompleteFields = INPUT_FIELD_ORDER.filter((field) => {
        const coverage = problem.fieldCoverage[field];
        return typeof coverage === 'number' && coverage < 1;
    })
        .map((field) => {
            const percentage = Math.floor((problem.fieldCoverage[field] ?? 0) * 1000) / 10;
            return `${fieldLabel(field)} ${percentage}%`;
        })
        .join(', ');

    switch (problem.code) {
        case 'missing_input_fields':
            return translate('chartSettings.signalProblems.missingInputFields', {fields: missingFields || 'OHLCV'});
        case 'insufficient_input_coverage':
            return translate('chartSettings.signalProblems.incompleteInputCoverage', {
                fields: incompleteFields || 'OHLCV',
                available: problemCount(problem.availablePoints),
                requested: problemCount(problem.requestedPoints),
            });
        case 'insufficient_history':
            return translate('chartSettings.signalProblems.insufficientHistory', {
                available: problemCount(problem.availablePoints),
                required: problemCount(problem.minimumPoints),
            });
        case 'incomplete_warmup':
            return translate('chartSettings.signalProblems.incompleteWarmup', {
                used: problemCount(problem.warmupUsedPoints),
                required: problemCount(problem.warmupRequiredPoints),
            });
        case 'partial_input_coverage':
        case 'partial_event_coverage':
        case 'data_gap':
            if (problem.selectedStartDate && problem.selectedEndDate) {
                return translate('chartSettings.signalProblems.partialContiguousSegment', {
                    start: problem.selectedStartDate,
                    end: problem.selectedEndDate,
                    excluded: problemCount(problem.excludedPoints),
                    available: problemCount(problem.availablePoints),
                    requested: problemCount(problem.requestedPoints),
                    coverage: problemCount(problem.coveragePercent),
                    consecutive: problemCount(problem.maxConsecutiveMissingPoints),
                });
            }
            return translate('chartSettings.signalProblems.dataGaps', {
                missing: problemCount(problem.missingPoints),
                requested: problemCount(problem.requestedPoints),
                coverage: problemCount(problem.coveragePercent),
            });
        case 'missing_event_types':
        case 'insufficient_event_coverage':
            return translate('chartSettings.signalProblems.missingEvents', {events: problem.missingEventTypes.join(', ') || '?'});
        case 'incompatible_domain':
            return translate('chartSettings.signalProblems.incompatibleDomain');
        case 'calculation_failed':
            return translate('chartSettings.signalProblems.calculationFailed', {message: problem.message || translate('common.error')});
        case 'result_missing':
            return translate('chartSettings.signalProblems.resultMissing');
        case 'partial':
            return problem.message || translate('chartSettings.signalProblems.partialResult');
        case 'unavailable':
            return problem.message || translate('chartSettings.signalProblems.unavailable');
    }
}

/** Read a numeric param by key; non-numbers fall back to `Number(fallback ?? 0)`. */
export function getParamNumber(signal: SignalConfig, key: string, fallback: unknown): number {
    const v = signal.params[key];
    return typeof v === 'number' ? v : Number(fallback ?? 0);
}

/** Read a string param by key; anything non-string yields the empty string. */
export function getParamString(signal: SignalConfig, key: string): string {
    const v = signal.params[key];
    return typeof v === 'string' ? v : '';
}
