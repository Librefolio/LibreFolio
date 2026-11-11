/**
 * The calendar-return signal as the page reads it: the request ids, the view and the extraction of a backend answer.
 *
 * `ASSET_CALENDAR_ROLLING_RETURN` answers a rolling return per calendar period; `extractCalendarReturnView` normalises its
 * result (flat at runtime, one level nested after code generation) into points plus the provenance of each date, and
 * `extractCalendarReturnViewsByAsset` does it for a bulk answer's items. It lives in the signals feature, where the
 * backend result schemas and the problem model are; the chart primitives do not know it.
 *
 * @module features/signals/calendarReturn
 */

import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import type {CalendarReturnPointContext, CalendarReturnPointStatus} from '$lib/components/charts/chartSignalContract';
import {ISO_DATE_PATTERN} from '$lib/components/charts/priceChartHelpers';
import {backendSignalSchemas} from './backendTypes';
import {getBackendSignalProblem, type SignalProblem} from './signalProblem';

export const CALENDAR_RETURN_SIGNAL_CODE = 'ASSET_CALENDAR_ROLLING_RETURN';
export const CALENDAR_RETURN_INSTANCE_ID = 'asset-calendar-return';

export type {CalendarReturnPointContext, CalendarReturnPointStatus};

export type CalendarReturnViewState = 'idle' | 'loading' | 'ready' | 'partial' | 'unavailable' | 'error';
export interface CalendarReturnView {
    state: CalendarReturnViewState;
    points: LineDataPoint[];
    contextByDate: Map<string, CalendarReturnPointContext>;
    problem: SignalProblem | null;
}

const CALENDAR_RETURN_STATUSES = new Set<CalendarReturnPointStatus>(['available', 'missing_reference', 'invalid_current_price', 'invalid_reference_price']);
const SIGNAL_RESULT_STATUSES = new Set(['ok', 'partial', 'unavailable', 'failed']);

/** A calendar view with no points and no context; `idle` unless a state is given. */
export function emptyCalendarReturnView(state: CalendarReturnViewState = 'idle', problem: SignalProblem | null = null): CalendarReturnView {
    return {state, points: [], contextByDate: new Map(), problem};
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function flattenOneLevel(value: unknown): unknown[] | null {
    if (!Array.isArray(value)) return null;
    return value.flatMap((item) => (Array.isArray(item) ? item : [item]));
}

function requiredIsoDate(value: unknown): string | null {
    return typeof value === 'string' && ISO_DATE_PATTERN.test(value) ? value : null;
}

function optionalIsoDate(value: unknown): string | null | undefined {
    if (value === null || value === undefined) return null;
    return requiredIsoDate(value) ?? undefined;
}

function requiredNonNegativeInt(value: unknown): number | null {
    return typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : null;
}

function optionalNonNegativeInt(value: unknown): number | null | undefined {
    if (value === null || value === undefined) return null;
    return requiredNonNegativeInt(value) ?? undefined;
}

function calendarResultMatches(value: unknown, instanceId: string): value is Record<string, unknown> {
    return isRecord(value) && value.instance_id === instanceId && value.signal_code === CALENDAR_RETURN_SIGNAL_CODE;
}

export function isCalendarReturnSignalResult(value: unknown, instanceId: string = CALENDAR_RETURN_INSTANCE_ID): boolean {
    return calendarResultMatches(value, instanceId);
}

/**
 * Normalize the calendar-return result without depending on generated union
 * shapes. Runtime payloads are flat; code generation may widen series/points
 * to one-level nested arrays, so this transport seam accepts both.
 */
export function extractCalendarReturnView(rawResults: unknown, instanceId: string = CALENDAR_RETURN_INSTANCE_ID): CalendarReturnView {
    const results = flattenOneLevel(rawResults);
    if (!results) return emptyCalendarReturnView('error');

    const result = results.find((item) => calendarResultMatches(item, instanceId));
    if (!result || typeof result.status !== 'string' || !SIGNAL_RESULT_STATUSES.has(result.status)) {
        return emptyCalendarReturnView('error');
    }
    const parsedResult = backendSignalSchemas.result.safeParse(result);
    const problem = parsedResult.success ? getBackendSignalProblem(parsedResult.data) : null;
    if (result.status === 'unavailable') {
        return parsedResult.success ? emptyCalendarReturnView('unavailable', problem) : emptyCalendarReturnView('error');
    }
    if (result.status === 'failed') return emptyCalendarReturnView('error', problem);

    const seriesCandidates = 'series' in result ? flattenOneLevel(result.series) : [result];
    if (!seriesCandidates) return emptyCalendarReturnView('error', problem);
    const series = seriesCandidates.find((item) => isRecord(item) && item.key === 'calendar_return');
    if (!isRecord(series)) return emptyCalendarReturnView('error', problem);

    const pointCandidates = flattenOneLevel(series.points);
    if (!pointCandidates?.length) return emptyCalendarReturnView('error', problem);

    const points: LineDataPoint[] = [];
    const contextByDate = new Map<string, CalendarReturnPointContext>();
    let hasMissing = false;

    for (const item of pointCandidates) {
        if (!isRecord(item) || !isRecord(item.provenance)) return emptyCalendarReturnView('error', problem);
        const date = requiredIsoDate(item.date);
        const status = typeof item.provenance.status === 'string' && CALENDAR_RETURN_STATUSES.has(item.provenance.status as CalendarReturnPointStatus) ? (item.provenance.status as CalendarReturnPointStatus) : null;
        const referenceTargetDate = requiredIsoDate(item.provenance.reference_target_date);
        const currentPriceDate = requiredIsoDate(item.provenance.current_price_date);
        const currentPriceDaysBack = requiredNonNegativeInt(item.provenance.current_price_days_back);
        const referencePriceDate = optionalIsoDate(item.provenance.reference_price_date);
        const referencePriceDaysBack = optionalNonNegativeInt(item.provenance.reference_price_days_back);
        const currentFxDate = optionalIsoDate(item.provenance.current_fx_date);
        const currentFxDaysBack = optionalNonNegativeInt(item.provenance.current_fx_days_back);
        const referenceFxDate = optionalIsoDate(item.provenance.reference_fx_date);
        const referenceFxDaysBack = optionalNonNegativeInt(item.provenance.reference_fx_days_back);
        const value = item.value === null ? null : typeof item.value === 'number' && Number.isFinite(item.value) ? item.value : undefined;

        if (
            !date ||
            !status ||
            !referenceTargetDate ||
            !currentPriceDate ||
            currentPriceDaysBack === null ||
            referencePriceDate === undefined ||
            referencePriceDaysBack === undefined ||
            currentFxDate === undefined ||
            currentFxDaysBack === undefined ||
            referenceFxDate === undefined ||
            referenceFxDaysBack === undefined ||
            value === undefined ||
            (status === 'available') !== (value !== null) ||
            (referencePriceDate === null) !== (referencePriceDaysBack === null) ||
            (currentFxDate === null) !== (currentFxDaysBack === null) ||
            (referenceFxDate === null) !== (referenceFxDaysBack === null) ||
            contextByDate.has(date)
        ) {
            return emptyCalendarReturnView('error', problem);
        }

        const fxStaleDays = Math.max(currentFxDaysBack ?? 0, referenceFxDaysBack ?? 0);
        const staleDays = Math.max(currentPriceDaysBack, referencePriceDaysBack ?? 0, fxStaleDays);
        hasMissing ||= value === null;
        points.push({
            date,
            value: value ?? 0,
            ...(value === null ? {missing: true} : {}),
            ...(staleDays > 0 ? {staleDays} : {}),
            ...(fxStaleDays > 0 ? {fxStaleDays} : {}),
        });
        contextByDate.set(date, {
            status,
            referenceTargetDate,
            currentPriceDate,
            referencePriceDate,
            currentFxDate,
            referenceFxDate,
        });
    }

    points.sort((left, right) => left.date.localeCompare(right.date));
    return {
        state: result.status === 'partial' || hasMissing ? 'partial' : 'ready',
        points,
        contextByDate,
        problem,
    };
}

export function extractCalendarReturnViewsByAsset(rawItems: unknown, assetIds: readonly number[], instanceId: string = CALENDAR_RETURN_INSTANCE_ID): Map<number, CalendarReturnView> {
    const items = Array.isArray(rawItems) ? rawItems : [];
    return new Map(
        [...new Set(assetIds)].map((assetId) => {
            const item = items.find((candidate) => isRecord(candidate) && candidate.asset_id === assetId);
            return [assetId, item ? extractCalendarReturnView(item.signals, instanceId) : emptyCalendarReturnView('error')];
        }),
    );
}
