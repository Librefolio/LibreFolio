/**
 * Pure helpers extracted from LotWacPriceChart.svelte.
 *
 * LotWacPriceChart is a ~2000-line ECharts component, but a large, dense core of
 * it is plain arithmetic and event bookkeeping that never touches a canvas:
 * rescaling per-unit prices, normalising a series into a percentage baseline,
 * translating an axis range and a zoom window into a visible logical range,
 * padding axis bounds so bubbles do not spill past the plot, sizing a bubble
 * from a value, and — the densest part — replaying the lot timeline to work out
 * each event's before/after quantity and unit price and matching transfer
 * departures to arrivals.
 *
 * That is exactly the code where an off-by-one, a bad clamp, a missing null
 * guard or a wrong branch hides, and none of it can be reached in jsdom (ECharts
 * draws to a canvas that does not exist there). So it lives here and is unit
 * tested in a plain node environment. The component keeps the ECharts wiring,
 * the tooltip HTML (translated, therefore not asserted) and the reactive glue.
 *
 * @module brokers/lots/lotWacPriceChartHelpers
 */

import {safeDecimal} from '$lib/types';
import {mapDateToBucket} from '$lib/components/charts/timeSeriesAggregation';

/** The seven presentation-level lot chronology event kinds. */
export type LotEventKind = 'BUY' | 'SELL' | 'ADJUSTMENT_IN' | 'ADJUSTMENT_OUT' | 'SPLIT' | 'TRANSFER_DEPART' | 'TRANSFER_ARRIVE';

/** A per-broker series point in both representations. */
export interface ValuePoint {
    date: string;
    absolute: number | null;
    percent: number | null;
}

/** A resolved logical date span the chart is currently showing. */
export interface LogicalRange {
    startDate: string;
    endDate: string;
}

/** Inclusive `{min, max}` date bounds (either bare days or ISO instants). */
export interface DateBounds {
    min: string;
    max: string;
}

/** A dataZoom window expressed as start/end percentages of the axis. */
export interface ZoomPercent {
    start: number;
    end: number;
}

/** The running quantity + unit price of a lot as the timeline is replayed. */
export interface LotEventState {
    quantity: number | null;
    unitPrice: number | null;
}

// ---------------------------------------------------------------------------
// Dates
// ---------------------------------------------------------------------------

/** Lexicographic compare of two `YYYY-MM-DD` strings (which sorts chronologically). */
export function sortDates(a: string, b: string): number {
    return a.localeCompare(b);
}

/**
 * `YYYY-MM-DD` → the UTC-midnight epoch millisecond of that calendar day. Any
 * component that is not a finite number yields `NaN`, which callers test for
 * before using the result (a malformed date must not silently become epoch 0).
 */
export function isoDateToUtcMs(date: string): number {
    const [year, month, day] = date.split('-').map(Number);
    if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return Number.NaN;
    return Date.UTC(year, month - 1, day);
}

/** UTC-midnight epoch millisecond → `YYYY-MM-DD`, the inverse of {@link isoDateToUtcMs}. */
export function utcMsToIsoDate(ms: number): string {
    const date = new Date(ms);
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// ---------------------------------------------------------------------------
// Price / series arithmetic
// ---------------------------------------------------------------------------

/**
 * The positive scale factor a bond's `quote_base_quantity` implies (1 for
 * stocks, e.g. 100 for a bond priced per 100 nominal). A non-positive or
 * missing input degrades to 1 so the caller can always multiply safely.
 */
export function resolveQbqScale(quoteBaseQuantity: number | null | undefined): number {
    return quoteBaseQuantity != null && quoteBaseQuantity > 0 ? quoteBaseQuantity : 1;
}

/**
 * Rescale a per-single-unit price (WAC / opening_unit_price = cost ÷ raw
 * quantity) up to the per-`quote_base_quantity` market scale that
 * `price_history.close` uses, so cost lines, bubbles and the market line share
 * one absolute price axis. A `null` price stays `null`.
 */
export function scaleUnitPrice(value: number | null, qbqScale: number): number | null {
    return value == null ? null : value * qbqScale;
}

/**
 * Blank out a weighted-average cost that is meaningless as a line point: a
 * `null` WAC stays `null`, and a WAC of exactly zero — or a WAC against an
 * empty pool — also becomes `null` (there is no cost basis to draw). Every
 * other WAC passes through.
 */
export function nullifyZeroWac(wac: number | null, poolQty: number | null): number | null {
    if (wac == null) return null;
    return wac === 0 || poolQty === 0 ? null : wac;
}

/**
 * Attach a percentage representation to a value series, rebased on the first
 * non-null, non-zero value (the baseline). Points before a baseline exists, or
 * with a null value, get a `null` percent; the absolute value is preserved as
 * given. With no usable baseline every percent is `null`.
 */
export function toPercentSeries(points: ReadonlyArray<{date: string; value: number | null}>): ValuePoint[] {
    let baseline: number | null = null;
    for (const point of points) {
        if (point.value != null && point.value !== 0) {
            baseline = point.value;
            break;
        }
    }

    return points.map((point) => ({
        date: point.date,
        absolute: point.value,
        percent: point.value != null && baseline != null ? ((point.value - baseline) / baseline) * 100 : null,
    }));
}

// ---------------------------------------------------------------------------
// Axis bounds & zoom
// ---------------------------------------------------------------------------

/**
 * Order a pair of resolved bounds into a valid `{min, max}`. Either side being
 * absent yields `null` (no drawable domain); otherwise the smaller string comes
 * first, swapping if the caller handed them in reversed.
 */
export function orderDateBounds(min: string | null | undefined, max: string | null | undefined): DateBounds | null {
    if (!min || !max) return null;
    return min <= max ? {min, max} : {min: max, max: min};
}

/**
 * Read a raw dataZoom `{start, end}` (whatever ECharts stored) into a clean
 * percentage window: a non-number start defaults to 0, a non-number end to 100,
 * and both are clamped into `[0, 100]`.
 */
export function readZoomPercent(zoom: {start?: unknown; end?: unknown} | null | undefined): ZoomPercent {
    const start = typeof zoom?.start === 'number' ? zoom.start : 0;
    const end = typeof zoom?.end === 'number' ? zoom.end : 100;
    return {
        start: Math.min(100, Math.max(0, start)),
        end: Math.min(100, Math.max(0, end)),
    };
}

/**
 * Project a zoom percentage window onto an axis logical range to get the range
 * actually visible. A degenerate axis (unparseable or non-increasing bounds)
 * returns the axis range unchanged; otherwise start/end are ordered and mapped
 * linearly across the UTC span.
 */
export function computeVisibleLogicalRange(axisRange: LogicalRange, zoom: ZoomPercent): LogicalRange {
    const minMs = isoDateToUtcMs(axisRange.startDate);
    const maxMs = isoDateToUtcMs(axisRange.endDate);
    if (!Number.isFinite(minMs) || !Number.isFinite(maxMs) || maxMs <= minMs) return axisRange;

    const startPercent = Math.min(zoom.start, zoom.end);
    const endPercent = Math.max(zoom.start, zoom.end);
    const spanMs = maxMs - minMs;

    return {
        startDate: utcMsToIsoDate(minMs + spanMs * (startPercent / 100)),
        endDate: utcMsToIsoDate(minMs + spanMs * (endPercent / 100)),
    };
}

/**
 * How many daily / weekly / monthly buckets the given dates span inside a
 * logical range. Dates outside the range are skipped; weekly and monthly counts
 * are the number of distinct bucket ends. Drives the resolution cascade.
 */
export function computeLineBucketCounts(dates: ReadonlyArray<string>, range: LogicalRange): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
    let dailyCount = 0;
    const weekly = new Set<string>();
    const monthly = new Set<string>();

    for (const date of dates) {
        if (date < range.startDate || date > range.endDate) continue;
        dailyCount += 1;
        weekly.add(mapDateToBucket(date, 'weekly').bucketEnd);
        monthly.add(mapDateToBucket(date, 'monthly').bucketEnd);
    }

    return {dailyCount, weeklyCount: weekly.size, monthlyCount: monthly.size};
}

// ---------------------------------------------------------------------------
// Bubble padding & sizing
// ---------------------------------------------------------------------------

/**
 * The extra span to add on each side of a plot so a bubble of `maxBubbleRadius`
 * px, opened at the very edge, is not clipped. The radius is converted to a
 * fraction of the plot (capped at 30%), then to a span delta that — because
 * ECharts maps `[min,max]` linearly across the plot — reserves exactly that many
 * pixels regardless of the domain width. The `1 - 2·fraction` denominator is
 * floored at 0.1 so an enormous radius cannot divide by zero or flip sign.
 */
export function bubbleEdgePadding(span: number, maxBubbleRadius: number, plotSizePx: number): number {
    const edgeFraction = Math.min(0.3, maxBubbleRadius / plotSizePx);
    return (span * edgeFraction) / Math.max(0.1, 1 - 2 * edgeFraction);
}

/**
 * Extend date bounds horizontally to reserve `maxBubbleRadius` px on each side.
 * A no-op (returns the input) without bounds, without bubbles, or when the
 * bounds are unparseable / non-increasing. Operates on ISO instants.
 */
export function padDateBoundsForBubbles(bounds: DateBounds | null, maxBubbleRadius: number, plotWidthPx: number): DateBounds | null {
    if (!bounds) return bounds;
    if (maxBubbleRadius <= 0) return bounds;
    const minMs = new Date(bounds.min).getTime();
    const maxMs = new Date(bounds.max).getTime();
    if (!Number.isFinite(minMs) || !Number.isFinite(maxMs) || maxMs <= minMs) return bounds;
    const padMs = bubbleEdgePadding(maxMs - minMs, maxBubbleRadius, Math.max(1, plotWidthPx));
    return {min: new Date(minMs - padMs).toISOString(), max: new Date(maxMs + padMs).toISOString()};
}

/**
 * The padded `{min, max}` for a y-axis given the collected values. Empty input
 * yields `null`. A real span pads 4% each side; a degenerate span (all equal)
 * pads 4% of the largest magnitude (or 1). When bubbles are present, both sides
 * are then expanded again by {@link bubbleEdgePadding} so the largest bubble is
 * not clipped vertically.
 */
export function computePaddedValueBounds(values: ReadonlyArray<number>, maxBubbleRadius: number, plotHeightPx: number): {min: number; max: number} | null {
    if (values.length === 0) return null;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min;
    const padding = span > 0 ? span * 0.04 : Math.max(Math.abs(min), Math.abs(max), 1) * 0.04;
    let paddedMin = min - padding;
    let paddedMax = max + padding;

    if (maxBubbleRadius > 0) {
        const bubblePadding = bubbleEdgePadding(paddedMax - paddedMin, maxBubbleRadius, Math.max(1, plotHeightPx));
        paddedMin -= bubblePadding;
        paddedMax += bubblePadding;
    }

    return {min: paddedMin, max: paddedMax};
}

/** Bubbles smaller than this magnitude count as "flat" (neither gain nor loss). */
export const LOT_BUBBLE_ZERO_EPS = 0.0005;
/** Smallest / largest bubble radius, in px. */
export const LOT_BUBBLE_MIN_RADIUS = 7;
export const LOT_BUBBLE_MAX_RADIUS = 22;

/**
 * A bubble radius in `[LOT_BUBBLE_MIN_RADIUS, LOT_BUBBLE_MAX_RADIUS]`, scaled by
 * the square root of the value (so area, not radius, tracks magnitude) between
 * the series min and max. Degenerate ranges (max ≤ min, or equal roots) return
 * the midpoint radius; the normalised position is clamped to `[0, 1]`, and
 * negative inputs are floored at 0 before the root.
 */
export function lotBubbleRadius(value: number, minValue: number, maxValue: number): number {
    const mid = (LOT_BUBBLE_MIN_RADIUS + LOT_BUBBLE_MAX_RADIUS) / 2;
    if (maxValue <= minValue) return mid;
    const minRoot = Math.sqrt(Math.max(0, minValue));
    const maxRoot = Math.sqrt(Math.max(0, maxValue));
    if (maxRoot === minRoot) return mid;
    const valueRoot = Math.sqrt(Math.max(0, value));
    const normalized = Math.min(1, Math.max(0, (valueRoot - minRoot) / (maxRoot - minRoot)));
    return LOT_BUBBLE_MIN_RADIUS + normalized * (LOT_BUBBLE_MAX_RADIUS - LOT_BUBBLE_MIN_RADIUS);
}

/**
 * The green / red / neutral color for a signed bubble metric, with a dead band
 * of ±{@link LOT_BUBBLE_ZERO_EPS} around zero so a rounding crumb never paints a
 * flat lot as a gain or a loss. `isDark` selects the theme's brighter variants.
 */
export function lotBubbleSignColor(signed: number, isDark: boolean): string {
    if (signed > LOT_BUBBLE_ZERO_EPS) return isDark ? '#4ade80' : '#16a34a';
    if (signed < -LOT_BUBBLE_ZERO_EPS) return isDark ? '#f87171' : '#dc2626';
    return isDark ? '#94a3b8' : '#64748b';
}

// ---------------------------------------------------------------------------
// Lot timeline events
// ---------------------------------------------------------------------------

/**
 * The identity fields that make an event's key and drive transfer matching.
 *
 * The optional id / fragment fields are typed scalar-or-array to accept the API schema verbatim: its
 * OpenAPI generator emits `(x | null) | Array<x | null>` for these. The matching logic compares them
 * as scalars (an array simply never `===` a number), exactly as the original component did.
 */
export interface LotEventIdentity {
    lot_id: number;
    date: string;
    kind: LotEventKind;
    transaction_id: number;
    related_transaction_id?: number | (number | null)[] | null;
    fragment_id?: string | (string | null)[] | null;
}

/** The broker/transaction fields a transfer departure ↔ arrival match reads. */
export interface TransferMatchFields {
    lot_id: number;
    date: string;
    transaction_id: number;
    related_transaction_id?: number | (number | null)[] | null;
    fragment_id?: string | (string | null)[] | null;
    source_broker_id?: number | (number | null)[] | null;
    destination_broker_id?: number | (number | null)[] | null;
}

/** The numeric-ish fields the state reducer parses off an event. */
export interface LotEventInput {
    kind: LotEventKind;
    quantity?: unknown;
    unit_price?: unknown;
    open_unit_price?: unknown;
    close_unit_price?: unknown;
    ratio?: unknown;
}

/** A stable de-duplication key for a timeline event. */
export function eventKey(event: LotEventIdentity): string {
    return `${event.lot_id}:${event.date}:${event.kind}:${event.transaction_id}:${event.related_transaction_id ?? ''}:${event.fragment_id ?? ''}`;
}

/** The marker series an event kind belongs to, or `null` if it draws no marker. */
export function eventCategory(kind: LotEventKind): 'buy' | 'sell' | 'transfer' | 'adjustment' | 'split' | null {
    if (kind === 'BUY') return 'buy';
    if (kind === 'SELL') return 'sell';
    if (kind === 'TRANSFER_ARRIVE') return 'transfer';
    if (kind === 'ADJUSTMENT_IN' || kind === 'ADJUSTMENT_OUT') return 'adjustment';
    if (kind === 'SPLIT') return 'split';
    return null;
}

/**
 * The intra-day ordering rank of an event kind, so that on a single date a
 * departure is replayed before an arrival before a split before an opening,
 * and closures last. Ties beyond this are broken by transaction id.
 */
export function eventTimelineOrder(kind: LotEventKind): number {
    if (kind === 'TRANSFER_DEPART') return 0;
    if (kind === 'TRANSFER_ARRIVE') return 1;
    if (kind === 'SPLIT') return 2;
    if (kind === 'BUY' || kind === 'ADJUSTMENT_IN') return 3;
    return 4;
}

/**
 * The last point whose date is at or before `date`, by binary search over a
 * date-sorted array. Returns `null` when every point is strictly after `date`.
 */
export function resolveMarketPriceAtOrBefore<T extends {date: string}>(date: string, points: ReadonlyArray<T>): T | null {
    let low = 0;
    let high = points.length - 1;
    let matchIndex = -1;

    while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        if (points[mid].date <= date) {
            matchIndex = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    return matchIndex >= 0 ? points[matchIndex] : null;
}

/**
 * Match a transfer arrival to its departure. A candidate departure must be the
 * same lot, dated on or before the arrival, and — when both sides name the same
 * broker slot — agree on it. It matches when the transaction ids are paired
 * (either direction) or the fragment ids are equal. The most recent, then
 * highest-id, candidate wins.
 */
export function findTransferDepartEvent<T extends TransferMatchFields>(arriveEvent: TransferMatchFields, departEvents: ReadonlyArray<T>): T | null {
    const candidates = departEvents.filter((candidate) => {
        if (candidate.lot_id !== arriveEvent.lot_id) return false;
        if (sortDates(candidate.date, arriveEvent.date) > 0) return false;
        if (candidate.source_broker_id != null && arriveEvent.source_broker_id != null && candidate.source_broker_id !== arriveEvent.source_broker_id) return false;
        if (candidate.destination_broker_id != null && arriveEvent.destination_broker_id != null && candidate.destination_broker_id !== arriveEvent.destination_broker_id) return false;
        if (arriveEvent.related_transaction_id != null && candidate.transaction_id === arriveEvent.related_transaction_id) return true;
        if (candidate.related_transaction_id != null && candidate.related_transaction_id === arriveEvent.transaction_id) return true;
        if (arriveEvent.fragment_id != null && candidate.fragment_id != null && candidate.fragment_id === arriveEvent.fragment_id) return true;
        return false;
    });

    candidates.sort((left, right) => sortDates(right.date, left.date) || right.transaction_id - left.transaction_id);
    return candidates[0] ?? null;
}

/**
 * Mirror of {@link findTransferDepartEvent}: match a departure to its arrival. A
 * candidate arrival must be the same lot, dated on or after the departure, and
 * broker-consistent; the earliest, then lowest-id, candidate wins.
 */
export function findTransferArriveEvent<T extends TransferMatchFields>(departEvent: TransferMatchFields, arriveEvents: ReadonlyArray<T>): T | null {
    const candidates = arriveEvents.filter((candidate) => {
        if (candidate.lot_id !== departEvent.lot_id) return false;
        if (sortDates(candidate.date, departEvent.date) < 0) return false;
        if (candidate.source_broker_id != null && departEvent.source_broker_id != null && candidate.source_broker_id !== departEvent.source_broker_id) return false;
        if (candidate.destination_broker_id != null && departEvent.destination_broker_id != null && candidate.destination_broker_id !== departEvent.destination_broker_id) return false;
        if (departEvent.related_transaction_id != null && candidate.transaction_id === departEvent.related_transaction_id) return true;
        if (candidate.related_transaction_id != null && candidate.related_transaction_id === departEvent.transaction_id) return true;
        if (departEvent.fragment_id != null && candidate.fragment_id != null && candidate.fragment_id === departEvent.fragment_id) return true;
        return false;
    });

    candidates.sort((left, right) => sortDates(left.date, right.date) || left.transaction_id - right.transaction_id);
    return candidates[0] ?? null;
}

/** A defensive copy of a lot's running state (missing state reads as all-null). */
export function cloneLotEventState(state: LotEventState | undefined): LotEventState {
    return {quantity: state?.quantity ?? null, unitPrice: state?.unitPrice ?? null};
}

/**
 * Replay one timeline event onto a lot's running `{quantity, unitPrice}` and
 * return the state after it. Each kind moves the pair differently:
 *
 * - **BUY** adds the (absolute) quantity onto the base (a null base counts as 0)
 *   and adopts the event's unit price when it has one.
 * - **ADJUSTMENT_IN** adds quantity and, when both prices and a positive base
 *   exist, blends the unit price by quantity-weighted average; otherwise it
 *   adopts the event price if present.
 * - **SELL / ADJUSTMENT_OUT** subtracts the (absolute) quantity, floored at 0,
 *   and leaves the unit price untouched.
 * - **SPLIT** multiplies quantity and divides unit price by the ratio, deriving
 *   a missing base quantity from `quantity / ratio` when it can.
 * - **TRANSFER_DEPART / TRANSFER_ARRIVE** carry the state across, seeding it from
 *   the event only when the running state is still null.
 *
 * A `null` quantity (or ratio, where it matters) leaves that dimension as it was.
 */
export function applyLotEvent(before: LotEventState, event: LotEventInput): LotEventState {
    const beforeQuantity = before.quantity;
    const beforeUnitPrice = before.unitPrice;
    const quantity = safeDecimal(event.quantity);
    const unitPrice = safeDecimal(event.unit_price ?? event.open_unit_price ?? event.close_unit_price);
    const ratio = safeDecimal(event.ratio);
    let afterQuantity = beforeQuantity;
    let afterUnitPrice = beforeUnitPrice;

    if (event.kind === 'BUY') {
        const openedQuantity = quantity == null ? null : Math.abs(quantity);
        const baseQuantity = beforeQuantity ?? 0;
        afterQuantity = openedQuantity == null ? beforeQuantity : baseQuantity + openedQuantity;
        afterUnitPrice = unitPrice ?? beforeUnitPrice;
    } else if (event.kind === 'ADJUSTMENT_IN') {
        const addedQuantity = quantity == null ? null : Math.abs(quantity);
        const baseQuantity = beforeQuantity ?? 0;
        if (addedQuantity != null) {
            afterQuantity = baseQuantity + addedQuantity;
            if (unitPrice != null && beforeUnitPrice != null && baseQuantity > 0) {
                afterUnitPrice = (beforeUnitPrice * baseQuantity + unitPrice * addedQuantity) / afterQuantity;
            } else {
                afterUnitPrice = unitPrice ?? beforeUnitPrice;
            }
        }
    } else if (event.kind === 'SELL' || event.kind === 'ADJUSTMENT_OUT') {
        const closedQuantity = quantity == null ? null : Math.abs(quantity);
        afterQuantity = beforeQuantity != null && closedQuantity != null ? Math.max(0, beforeQuantity - closedQuantity) : beforeQuantity;
        afterUnitPrice = beforeUnitPrice;
    } else if (event.kind === 'SPLIT') {
        const fallbackAfterQuantity = quantity == null ? null : Math.abs(quantity);
        const fallbackBeforeQuantity = ratio != null && ratio !== 0 && fallbackAfterQuantity != null ? fallbackAfterQuantity / ratio : null;
        const splitBeforeQuantity = beforeQuantity ?? fallbackBeforeQuantity;
        afterQuantity = splitBeforeQuantity != null && ratio != null ? splitBeforeQuantity * ratio : beforeQuantity;
        afterUnitPrice = beforeUnitPrice != null && ratio != null && ratio !== 0 ? beforeUnitPrice / ratio : beforeUnitPrice;
    } else if (event.kind === 'TRANSFER_DEPART' || event.kind === 'TRANSFER_ARRIVE') {
        afterQuantity = beforeQuantity ?? (quantity == null ? null : Math.abs(quantity));
        afterUnitPrice = beforeUnitPrice ?? unitPrice;
    }
    // NOTE: the implicit `else` of the chain above is intentionally uncovered — `LotEventKind` is a
    // closed 7-value union and every value is handled, so no input can reach the fall-through. It
    // exists only as a defensive no-op should an eighth kind ever be added upstream without a branch.

    return {quantity: afterQuantity, unitPrice: afterUnitPrice};
}
