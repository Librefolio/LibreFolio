import type {SignalInputField} from './ChartSignal';
import type {SignalInstanceResult, SignalInstanceStatus} from './resultMapper';
import {finiteNumber} from '$lib/utils/core/finiteNumber';

const INPUT_FIELDS: SignalInputField[] = ['open', 'high', 'low', 'close', 'volume'];

export type SignalProblemCode =
    | 'incompatible_domain'
    | 'missing_input_fields'
    | 'missing_event_types'
    | 'insufficient_input_coverage'
    | 'insufficient_event_coverage'
    | 'insufficient_history'
    | 'incomplete_warmup'
    | 'partial_input_coverage'
    | 'partial_event_coverage'
    | 'data_gap'
    | 'partial'
    | 'unavailable'
    | 'calculation_failed'
    | 'result_missing';

export interface SignalProblem {
    code: SignalProblemCode;
    status: Extract<SignalInstanceStatus, 'partial' | 'unavailable' | 'failed' | 'missing'>;
    missingPriceFields: SignalInputField[];
    missingEventTypes: string[];
    fieldCoverage: Partial<Record<SignalInputField, number>>;
    availablePoints: number | null;
    requestedPoints: number | null;
    minimumPoints: number | null;
    warmupUsedPoints: number | null;
    warmupRequiredPoints: number | null;
    missingPoints: number | null;
    maxConsecutiveMissingPoints: number | null;
    coverageRatio: number | null;
    coveragePercent: number | null;
    selectedStartDate: string | null;
    selectedEndDate: string | null;
    excludedPoints: number | null;
    message: string | null;
}

export type SignalProblemSeverity = 'notice' | 'warning' | 'error';

export function getSignalProblemSeverity(problem: SignalProblem): SignalProblemSeverity {
    if (problem.status === 'failed' || problem.status === 'unavailable' || problem.status === 'missing') return 'error';

    if (problem.code === 'incomplete_warmup') {
        if (problem.requestedPoints === null || problem.requestedPoints <= 0 || problem.warmupUsedPoints === null || problem.warmupRequiredPoints === null) return 'warning';
        const shortfall = Math.max(0, problem.warmupRequiredPoints - problem.warmupUsedPoints);
        return shortfall / problem.requestedPoints >= 0.05 ? 'warning' : 'notice';
    }

    const isCoverageNotice = problem.code === 'partial_input_coverage' || problem.code === 'data_gap';
    if (!isCoverageNotice || problem.coverageRatio === null) return 'warning';
    const maximumMissingRun = problem.maxConsecutiveMissingPoints ?? (problem.missingPoints !== null && problem.missingPoints <= 7 ? problem.missingPoints : null);
    if (maximumMissingRun === null) return 'warning';
    return problem.coverageRatio <= 0.95 || maximumMissingRun > 7 ? 'warning' : 'notice';
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function firstRecord(value: unknown): Record<string, unknown> | null {
    if (isRecord(value)) return value;
    if (!Array.isArray(value)) return null;
    return value.find(isRecord) ?? null;
}

function recordList(value: unknown): Record<string, unknown>[] {
    if (isRecord(value)) return [value];
    return Array.isArray(value) ? value.filter(isRecord) : [];
}

function firstString(value: unknown): string | null {
    if (typeof value === 'string') return value;
    if (!Array.isArray(value)) return null;
    return value.find((item): item is string => typeof item === 'string') ?? null;
}

function stringList(value: unknown): string[] {
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function inputFieldList(value: unknown): SignalInputField[] {
    const values = new Set(stringList(value));
    return INPUT_FIELDS.filter((field) => values.has(field));
}

function fieldCoverage(value: unknown): Partial<Record<SignalInputField, number>> {
    if (!isRecord(value)) return {};
    return Object.fromEntries(
        INPUT_FIELDS.flatMap((field) => {
            const coverage = finiteNumber(value[field]);
            return coverage === null ? [] : [[field, coverage]];
        }),
    );
}

function normalizeProblemCode(value: unknown, fallback: SignalProblemCode): SignalProblemCode {
    const code = firstString(value);
    switch (code) {
        case 'incompatible_domain':
        case 'missing_input_fields':
        case 'missing_event_types':
        case 'insufficient_input_coverage':
        case 'insufficient_event_coverage':
        case 'insufficient_history':
        case 'incomplete_warmup':
        case 'partial_input_coverage':
        case 'partial_event_coverage':
        case 'data_gap':
            return code;
        default:
            return fallback;
    }
}

export function getSignalProblem(item: SignalInstanceResult | undefined): SignalProblem | null {
    if (!item || item.status === 'local' || item.status === 'ok') return null;

    if (item.status === 'missing' || !item.result) {
        return {
            code: 'result_missing',
            status: 'missing',
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
            message: item.error,
        };
    }

    const availability = firstRecord(item.result.availability);
    const coverage = firstRecord(availability?.input_coverage);
    const warmup = firstRecord(item.result.warmup);
    const requirement = firstRecord(warmup?.requirement);
    const warnings = recordList(item.result.warnings);
    const warning = warnings[0] ?? null;
    const coverageWarning =
        warnings.find((item) => {
            const code = firstString(item.code);
            return code === 'partial_input_coverage' || code === 'data_gap';
        }) ?? null;
    const nonCoverageWarning =
        warnings.find((item) => {
            const code = firstString(item.code);
            return code !== 'partial_input_coverage' && code !== 'data_gap';
        }) ?? null;
    const coverageWarningDetails = firstRecord(coverageWarning?.details);
    const missingPointCount = finiteNumber(coverage?.missing_points);
    const rawMaximumMissingRun = finiteNumber(coverage?.max_consecutive_missing_points) ?? finiteNumber(coverageWarningDetails?.max_consecutive_missing_points);
    const maximumMissingRun = rawMaximumMissingRun === 0 && (missingPointCount ?? 0) > 0 ? null : rawMaximumMissingRun;

    if (item.status === 'failed') {
        return {
            code: 'calculation_failed',
            status: 'failed',
            missingPriceFields: [],
            missingEventTypes: [],
            fieldCoverage: {},
            availablePoints: finiteNumber(coverage?.available_points),
            requestedPoints: finiteNumber(coverage?.requested_points),
            minimumPoints: finiteNumber(requirement?.minimum_points),
            warmupUsedPoints: finiteNumber(warmup?.used_points),
            warmupRequiredPoints: finiteNumber(requirement?.total_points),
            missingPoints: missingPointCount,
            maxConsecutiveMissingPoints: maximumMissingRun,
            coverageRatio: finiteNumber(coverage?.coverage_ratio),
            coveragePercent: null,
            selectedStartDate: null,
            selectedEndDate: null,
            excludedPoints: null,
            message: item.error,
        };
    }

    const coverageRatio = finiteNumber(coverage?.coverage_ratio);
    const fallback = item.status === 'partial' ? 'partial' : 'unavailable';

    return {
        code: normalizeProblemCode(nonCoverageWarning?.code ?? availability?.reason_code ?? warning?.code, fallback),
        status: item.status,
        missingPriceFields: inputFieldList(availability?.missing_price_fields),
        missingEventTypes: stringList(availability?.missing_event_types),
        fieldCoverage: fieldCoverage(coverage?.field_coverage),
        availablePoints: finiteNumber(coverage?.available_points),
        requestedPoints: finiteNumber(coverage?.requested_points),
        minimumPoints: finiteNumber(requirement?.minimum_points) ?? finiteNumber(availability?.required_points),
        warmupUsedPoints: finiteNumber(warmup?.used_points),
        warmupRequiredPoints: finiteNumber(requirement?.total_points) ?? finiteNumber(availability?.required_points),
        missingPoints: missingPointCount,
        maxConsecutiveMissingPoints: maximumMissingRun,
        coverageRatio,
        coveragePercent: coverageRatio === null ? null : Math.floor(coverageRatio * 1000) / 10,
        selectedStartDate: firstString(coverageWarningDetails?.selected_start_date),
        selectedEndDate: firstString(coverageWarningDetails?.selected_end_date),
        excludedPoints: finiteNumber(coverageWarningDetails?.excluded_points),
        message: firstString(nonCoverageWarning?.message) ?? firstString(coverageWarning?.message) ?? firstString(warning?.message) ?? item.error,
    };
}
