/**
 * Pure helpers extracted from PriceChartFull.svelte.
 *
 * PriceChartFull is a 1200-line ECharts component, but a compact core of it is
 * plain arithmetic on the data array: synthesizing OHLC from a line series,
 * counting weekly/monthly buckets, resolving a dataZoom edge to a data index,
 * and translating a logical date range to a zoom window (and back). None of that
 * needs a canvas — it is exactly the arithmetic where an off-by-one or a bad
 * clamp hides — so it lives here and is unit-tested in a plain node environment.
 * The component keeps the ECharts wiring and the tooltip HTML (which is
 * translated and therefore not asserted here).
 *
 * @module charts/priceChartHelpers
 */

import type {LineDataPoint} from './LineChart.svelte';
import type {ViewMode} from './ChartToolbar.svelte';
import type {EventMarker} from './PriceChartFull.svelte';
import {truncateName} from '$lib/utils/text';
import {aggregateLineSeries, bucketEventMarkers, mapDateToBucket, type ChartResolution} from './timeSeriesAggregation';

/** A resolved logical date span the chart is currently showing. */
export interface LogicalVisibleRange {
    startDate: string;
    endDate: string;
}

/** The inclusive date span a single (possibly aggregated) point covers. */
export interface BucketInfo {
    bucketStart: string;
    bucketEnd: string;
}

/**
 * Localized "Month YYYY" label for a `YYYY-MM-DD` date. Anchored to UTC so the
 * month never drifts across a timezone boundary. `locale` defaults to the host
 * default (what the component uses); tests pass an explicit locale to stay
 * deterministic regardless of the machine's locale.
 */
export function formatMonthLabel(date: string, locale?: string | string[]): string {
    return new Intl.DateTimeFormat(locale, {
        month: 'long',
        year: 'numeric',
        timeZone: 'UTC',
    }).format(new Date(`${date}T00:00:00Z`));
}

/**
 * The bucket span for a point at a given resolution. Daily points are their own
 * bucket; coarser resolutions prefer the point's own `bucketStart`/`bucketEnd`
 * when present, otherwise derive the start from `mapDateToBucket` and treat the
 * point's date as the bucket end.
 */
export function getBucketInfo(point: LineDataPoint, currentResolution: ChartResolution): BucketInfo {
    if (currentResolution === 'daily') {
        return {bucketStart: point.date, bucketEnd: point.date};
    }

    return {
        bucketStart: typeof (point as {bucketStart?: unknown}).bucketStart === 'string' ? (point as {bucketStart: string}).bucketStart : mapDateToBucket(point.date, currentResolution).bucketStart,
        bucketEnd: typeof (point as {bucketEnd?: unknown}).bucketEnd === 'string' ? (point as {bucketEnd: string}).bucketEnd : point.date,
    };
}

/**
 * Fill in OHLC for a line series that may only carry `value`. Open borrows the
 * previous point's close (the first point opens at its own close); high/low
 * default to the open/close envelope. `value` is normalized to close so the two
 * representations agree.
 */
export function synthesizeDailyOHLC(points: LineDataPoint[]): LineDataPoint[] {
    return points.map((point, index) => {
        const close = point.close ?? point.value;
        const prevClose = index > 0 ? (points[index - 1].close ?? points[index - 1].value) : close;
        const open = point.open ?? prevClose;
        const high = point.high ?? Math.max(open, close);
        const low = point.low ?? Math.min(open, close);

        return {...point, open, high, low, close, value: close};
    });
}

/**
 * How many daily / weekly / monthly buckets a set of daily points spans. Used to
 * decide when to cascade the chart to a coarser resolution.
 */
export function countBuckets(points: LineDataPoint[]): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
    const weeklyBuckets = new Set<string>();
    const monthlyBuckets = new Set<string>();

    for (const point of points) {
        const weekly = mapDateToBucket(point.date, 'weekly');
        const monthly = mapDateToBucket(point.date, 'monthly');
        weeklyBuckets.add(`${weekly.bucketStart}|${weekly.bucketEnd}`);
        monthlyBuckets.add(`${monthly.bucketStart}|${monthly.bucketEnd}`);
    }

    return {
        dailyCount: points.length,
        weeklyCount: weeklyBuckets.size,
        monthlyCount: monthlyBuckets.size,
    };
}

/**
 * Resolve a dataZoom edge to a data index. A number is rounded and clamped into
 * `[0, len-1]`; a string is looked up as an exact date; anything else (or a
 * missing date) yields `fallback`.
 */
export function resolveZoomIndex(value: unknown, dates: string[], fallback: number): number {
    if (typeof value === 'number') {
        return Math.min(Math.max(Math.round(value), 0), dates.length - 1);
    }

    if (typeof value === 'string') {
        const index = dates.indexOf(value);
        if (index >= 0) return index;
    }

    return fallback;
}

/** The subset of `displayData` inside a logical range (whole set when null). */
export function getVisibleDailyPoints(points: LineDataPoint[], range: LogicalVisibleRange | null): LineDataPoint[] {
    if (!range) return points;
    return points.filter((point) => point.date >= range.startDate && point.date <= range.endDate);
}

/**
 * Translate a logical date range into a dataZoom `{start, end}` percentage window
 * over `points`. Finds the first bucket whose end reaches the range start and the
 * last bucket whose start is within the range end, then expresses both as a
 * percentage of the last index. Degenerate inputs map to the full `0..100`.
 */
export function computeZoomWindow(points: LineDataPoint[], currentResolution: ChartResolution, range: LogicalVisibleRange | null): {start: number; end: number} {
    const lastIndex = points.length - 1;
    if (!range || lastIndex <= 0) return {start: 0, end: 100};

    let startIndex = lastIndex;
    let endIndex = 0;

    for (let index = 0; index < points.length; index++) {
        const bucket = getBucketInfo(points[index], currentResolution);
        if (bucket.bucketEnd >= range.startDate) {
            startIndex = index;
            break;
        }
    }

    for (let index = lastIndex; index >= 0; index--) {
        const bucket = getBucketInfo(points[index], currentResolution);
        if (bucket.bucketStart <= range.endDate) {
            endIndex = index;
            break;
        }
    }

    if (endIndex < startIndex) {
        endIndex = startIndex;
    }

    return {
        start: (startIndex / lastIndex) * 100,
        end: (endIndex / lastIndex) * 100,
    };
}

// ===========================================================================
// View-mode transforms
// ===========================================================================

/**
 * The series the chart actually draws for a view mode. Absolute view (and an
 * empty series) draws the raw values; percentage view rebases every point to
 * its change from the first point. A first value of exactly 0 has no defined
 * percentage change, so the series is left untouched rather than dividing by 0.
 */
export function toDisplaySeries(data: LineDataPoint[], viewMode: ViewMode): LineDataPoint[] {
    if (viewMode === 'absolute' || data.length === 0) return data;
    const baseValue = data[0].value;
    if (baseValue === 0) return data;
    return data.map((d) => ({...d, value: ((d.value - baseValue) / baseValue) * 100}));
}

/**
 * Undo the percentage rebase for a single value, so a click/hover on the chart
 * reports the absolute value the user's data actually holds. Only percentage
 * view with a known base rebases; every other case is already absolute.
 */
export function toAbsoluteValue(value: number, viewMode: ViewMode, baseValue: number | undefined): number {
    if (viewMode === 'percentage' && baseValue !== undefined) {
        return baseValue * (1 + value / 100);
    }
    return value;
}

// ===========================================================================
// Zoom / hit-testing
// ===========================================================================

/** The subset of an ECharts dataZoom descriptor these helpers read. */
export interface ZoomDescriptor {
    startValue?: unknown;
    endValue?: unknown;
    start?: unknown;
    end?: unknown;
}

/**
 * Resolve a dataZoom descriptor to an inclusive `[startIndex, endIndex]` over
 * `dates`. A descriptor carrying explicit `startValue`/`endValue` is resolved
 * by date/index; otherwise a `start`/`end` percentage window is projected onto
 * the index range (defaulting to the full 0..100). The bounds are swapped if
 * they arrive inverted. Caller guarantees `dates` is non-empty.
 */
export function resolveZoomBounds(zoom: ZoomDescriptor, dates: string[]): {startIndex: number; endIndex: number} {
    const lastIndex = dates.length - 1;
    let startIndex = 0;
    let endIndex = lastIndex;

    if (zoom.startValue !== undefined || zoom.endValue !== undefined) {
        startIndex = resolveZoomIndex(zoom.startValue, dates, 0);
        endIndex = resolveZoomIndex(zoom.endValue, dates, lastIndex);
    } else if (lastIndex > 0) {
        const start = typeof zoom.start === 'number' ? zoom.start : 0;
        const end = typeof zoom.end === 'number' ? zoom.end : 100;
        startIndex = Math.min(Math.max(Math.floor((start / 100) * lastIndex), 0), lastIndex);
        endIndex = Math.min(Math.max(Math.ceil((end / 100) * lastIndex), 0), lastIndex);
    }

    if (startIndex > endIndex) [startIndex, endIndex] = [endIndex, startIndex];
    return {startIndex, endIndex};
}

/**
 * Round a chart grid X coordinate to a data index, returning `null` when the
 * pointer resolved outside the series (`[0, length)`). This is the guard every
 * click / double-click / long-press / hover handler shares before it dares to
 * index the active series.
 */
export function resolveActivePointIndex(gridX: number, length: number): number | null {
    const index = Math.round(gridX);
    return index >= 0 && index < length ? index : null;
}

// ===========================================================================
// Ghost (original-currency) series
// ===========================================================================

/** The label and per-date lookup for the dashed original-currency ghost line. */
export interface GhostSeriesData {
    label: string;
    lookup: Map<string, number>;
}

/**
 * Build the dashed "ghost" line that shows an FX-converted asset in its own
 * original currency, or `null` when no point carries an `originalValue` (the
 * common, un-converted case). The label reuses the main series label when the
 * caller has one, always prefixed with 💱 and the original currency flag+code.
 * In percentage view the ghost is rebased to its own first original value
 * (a 0 first value stays flat, never dividing by 0), and coarser resolutions
 * aggregate the daily ghost points the same way the main series does.
 */
export function computeGhostSeries(data: LineDataPoint[], isPercentage: boolean, activeResolution: ChartResolution, mainSeriesLabel: string | undefined): GhostSeriesData | null {
    const hasOriginalValues = data.some((point) => point.originalValue !== undefined);
    if (!hasOriginalValues) return null;

    const origCur = data.find((point) => point.originalCurrency)?.originalCurrency ?? '';
    const origFlag = data.find((point) => point.originalCurrencyFlag)?.originalCurrencyFlag ?? '';
    const label = mainSeriesLabel ? `💱 ${mainSeriesLabel} (${origFlag} ${origCur})`.trim() : `💱 ${origCur}`;

    const dailyGhostPoints = data.flatMap((point) => (point.originalValue === undefined ? [] : [{...point, value: point.originalValue}]));
    // The `hasOriginalValues` guard above guarantees ≥1 ghost point whose `value`
    // is a defined number, so `[0]?.value` is never nullish here — the `?? 1` is a
    // TypeScript-satisfying guard, not a reachable state, and stays uncovered.
    const firstOriginalValue = dailyGhostPoints[0]?.value ?? 1;
    const normalizedGhostPoints = isPercentage ? dailyGhostPoints.map((point) => ({...point, value: firstOriginalValue !== 0 ? ((point.value - firstOriginalValue) / firstOriginalValue) * 100 : 0})) : dailyGhostPoints;
    const resolvedGhostPoints = activeResolution === 'daily' ? normalizedGhostPoints : aggregateLineSeries(normalizedGhostPoints, activeResolution);

    return {label, lookup: new Map(resolvedGhostPoints.map((point) => [point.date, point.value]))};
}

// ===========================================================================
// Event-marker scatter groups
// ===========================================================================

/** One placed scatter point: a single daily marker or a bucket of them. */
export interface EventScatterPoint {
    value: [string, number];
    marker?: EventMarker;
    markers?: EventMarker[];
    bucketInfo: BucketInfo;
    bucketValue: number;
}

/** A group of event markers sharing a type (and comparison asset) → one series. */
export interface EventScatterGroup {
    label: string;
    color: string;
    eventType: string;
    points: EventScatterPoint[];
}

/** The chart context `buildEventScatterGroups` needs to place its points. */
export interface EventScatterContext {
    dateIndexMap: Map<string, number>;
    resolvedLineData: LineDataPoint[];
    overlayDataByLabel: Map<string, Map<string, number>>;
    bucketInfoByDate: Map<string, BucketInfo>;
    baseColor: string;
}

/**
 * Group event markers into scatter series and place each on the price axis.
 *
 * Markers are grouped by type, and comparison markers (those carrying an
 * `assetLabel`) are additionally split per asset and coloured by their overlay
 * signal. A marker's Y value follows its overlay line when it belongs to one,
 * otherwise the main price at that date; a date the axis does not contain is
 * skipped. Coarser resolutions bucket the markers first and carry the whole
 * bucket on one point. Groups that placed nothing are dropped.
 */
export function buildEventScatterGroups(eventMarkers: EventMarker[], activeResolution: ChartResolution, ctx: EventScatterContext): EventScatterGroup[] {
    const {dateIndexMap, resolvedLineData, overlayDataByLabel, bucketInfoByDate, baseColor} = ctx;

    const grouped = new Map<string, {markers: EventMarker[]; color: string; label: string}>();
    for (const marker of eventMarkers) {
        const isComparison = !!marker.assetLabel;
        const groupKey = isComparison ? `${marker.assetLabel}::${marker.type}` : marker.type;
        const color = isComparison ? (marker.signalColor ?? '#6b7280') : baseColor;
        const seriesLabel = isComparison ? `${marker.assetLabel} ${marker.type}` : marker.type;
        if (!grouped.has(groupKey)) {
            grouped.set(groupKey, {markers: [], color, label: seriesLabel});
        }
        grouped.get(groupKey)!.markers.push(marker);
    }

    const resolveY = (assetLabel: string | undefined, date: string, index: number): number => {
        // `index` is always a valid position in `resolvedLineData` — it comes from
        // `dateIndexMap`, which is built from that same array, and an absent date is
        // `continue`d before we get here. So the trailing `?? 0` on both arms below
        // guards an internally-inconsistent context the component never produces,
        // and stays deliberately uncovered.
        if (assetLabel) {
            const overlayLookup = overlayDataByLabel.get(assetLabel);
            return overlayLookup?.get(date) ?? resolvedLineData[index]?.value ?? 0;
        }
        return resolvedLineData[index]?.value ?? 0;
    };

    const groups: EventScatterGroup[] = [];
    for (const [, group] of grouped) {
        const {markers, color: eventColor, label: seriesLabel} = group;
        const eventType = markers[0].type;
        const points: EventScatterPoint[] = [];

        if (activeResolution === 'daily') {
            for (const marker of markers) {
                const index = dateIndexMap.get(marker.date);
                if (index === undefined) continue;
                const yValue = resolveY(marker.assetLabel, marker.date, index);
                points.push({value: [marker.date, yValue], marker, bucketInfo: {bucketStart: marker.date, bucketEnd: marker.date}, bucketValue: yValue});
            }
        } else {
            const bucketedMarkers = bucketEventMarkers(markers, activeResolution);
            for (const [bucketDate, bucketEntries] of bucketedMarkers) {
                const index = dateIndexMap.get(bucketDate);
                if (index === undefined) continue;
                const yValue = resolveY(bucketEntries[0]?.assetLabel, bucketDate, index);
                points.push({value: [bucketDate, yValue], markers: bucketEntries, bucketInfo: bucketInfoByDate.get(bucketDate) ?? mapDateToBucket(bucketDate, activeResolution), bucketValue: yValue});
            }
        }

        if (points.length === 0) continue;
        groups.push({label: seriesLabel, color: eventColor, eventType, points});
    }

    return groups;
}

// ===========================================================================
// Tooltip fragments (data-derived; no translated text)
// ===========================================================================

/**
 * The green/red "(Δ …)" delta suffix for the main-axis tooltip row. The colour
 * is *derived from the sign* (≥0 green `#10b981`, otherwise red `#ef4444`) — the
 * contract this asserts. In percentage view the value already is the delta; in
 * absolute view both the absolute and percentage delta from `firstValue` are
 * shown (a `firstValue` of 0 yields a 0% delta rather than dividing by 0).
 */
export function buildDeltaHtml(value: number, firstValue: number, isPercentage: boolean): string {
    const color = (n: number) => (n >= 0 ? '#10b981' : '#ef4444');
    const sign = (n: number) => (n >= 0 ? '+' : '');

    if (isPercentage) {
        return ` <span style="font-size:10px;color:${color(value)}">(Δ ${sign(value)}${value.toFixed(2)}%)</span>`;
    }

    const deltaAbs = value - firstValue;
    const deltaPct = firstValue !== 0 ? ((value - firstValue) / firstValue) * 100 : 0;
    return ` <span style="font-size:10px;color:${color(deltaAbs)}">(Δ ${sign(deltaAbs)}${deltaAbs.toFixed(4)} / ${sign(deltaPct)}${deltaPct.toFixed(2)}%)</span>`;
}

/**
 * The amber stale-data warning line(s) for a tooltip. Nothing is emitted when
 * the point is not stale (`priceStaleDays` undefined). A live FX staleness
 * (`fxStaleDays > 0`) adds a second line. The `{days}` templates are supplied
 * by the caller (translated at the component boundary); the built-in English
 * fallbacks are code constants used only when no template is given.
 */
export function buildStaleTooltipHtml(priceStaleDays: number | undefined, fxStaleDays: number | undefined, staleLabel?: string, fxStaleLabel?: string): string {
    if (priceStaleDays === undefined) return '';
    const warn = (text: string) => `<br/><span style="color:#f59e0b;font-size:11px">⚠ ${text}</span>`;
    const priceText = staleLabel ? staleLabel.replace('{days}', String(priceStaleDays)) : `Stale: ${priceStaleDays}d`;

    if (fxStaleDays !== undefined && fxStaleDays > 0) {
        const fxText = fxStaleLabel ? fxStaleLabel.replace('{days}', String(fxStaleDays)) : `FX rate: ${fxStaleDays}d old`;
        return warn(priceText) + warn(fxText);
    }
    return warn(priceText);
}

/**
 * Truncate the *name* portion of a ghost label of the form
 * `"💱 Name (🇺🇸 USD)"`, keeping the 💱 prefix and the currency parenthetical
 * intact. A label that does not match that shape is truncated whole.
 */
export function formatTruncatedGhostLabel(ghostLabel: string): string {
    const nameMatch = ghostLabel.match(/^💱\s*(.+?)\s*(\([^)]+\))$/);
    if (nameMatch) {
        return `💱 ${truncateName(nameMatch[1])} ${nameMatch[2]}`;
    }
    return truncateName(ghostLabel);
}
