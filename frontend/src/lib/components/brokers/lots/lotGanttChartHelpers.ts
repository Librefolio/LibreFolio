/**
 * Pure helpers extracted from LotGanttChart.svelte.
 *
 * The Gantt renders each lot as one or more custody lanes, branching on
 * transfers, with event markers inferred from segment transitions. The pure
 * work — parsing opaque fields, choosing a segment's colour/opacity/thickness,
 * deciding whether two adjacent segments are a split vs a sale, classifying an
 * event kind into a marker, building lane keys and sort tuples, and computing a
 * shared zoom window — is lifted here so it can be unit tested without an
 * ECharts canvas (custom-series `renderItem` closures never run in jsdom).
 *
 * What is deliberately NOT here: `formatDate` / `formatDateShort` /
 * `formatDateLong`. They build `new Date(value)` (UTC midnight for a date-only
 * string) and render it with `toLocaleDateString`, so a date-only value shows a
 * day early west of UTC — a product defect reported separately. Extracting them
 * would enshrine the bug behind a green test. Note that {@link parseDateToUtcMs}
 * below is the *correct* counterpart used for axis math: it reads the Y-M-D via a
 * regex and rebuilds the instant with `Date.UTC`, so it is zone-independent.
 *
 * @module brokers/lots/lotGanttChartHelpers
 */

import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {clamp} from './lotChartShared';

/** The marker kinds the Gantt can draw for a lot event. */
export type EventMarkerKind = 'BUY' | 'SELL' | 'TRANSFER' | 'ADJUSTMENT_IN' | 'ADJUSTMENT_OUT' | 'SPLIT';

/** Bar thickness bounds (px). Only {@link thicknessForQuantity} reads these. */
export const THICKNESS_MIN = 10;
export const THICKNESS_MAX = 26;
export const BRANCH_THICKNESS_MAX = 22;

// ---------------------------------------------------------------------------
// Field parsing
// ---------------------------------------------------------------------------

/**
 * Coerce an unknown field into a string: unwrap a single-element array (the
 * OpenAPI scalar-or-array shape), pass a string through, stringify a finite
 * number, else `null`.
 */
export function safeUnknownString(value: unknown): string | null {
    if (Array.isArray(value)) return safeUnknownString(value[0]);
    if (typeof value === 'string') return value;
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
    return null;
}

/** Parse an unknown field into a finite number via {@link safeUnknownString}, or `null`. */
export function parseUnknownNumber(value: unknown): number | null {
    const raw = safeUnknownString(value);
    if (raw == null) return null;
    const parsed = Number.parseFloat(raw);
    return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Parse a date to the UTC-midnight epoch ms of its calendar day, zone-independent.
 * A `YYYY-MM-DD` string is read field-by-field and rebuilt with `Date.UTC`; any
 * other parseable value is normalised to the UTC midnight of its UTC date; an
 * unparseable value is `null`. This is the correct counterpart to the buggy
 * `formatDate*` label formatters left in the component.
 */
export function parseDateToUtcMs(value: string): number | null {
    const dateOnlyMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (dateOnlyMatch) {
        const [, year, month, day] = dateOnlyMatch;
        return Date.UTC(Number(year), Number(month) - 1, Number(day));
    }

    const parsed = Date.parse(value);
    if (!Number.isFinite(parsed)) return null;
    const date = new Date(parsed);
    return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
}

/**
 * The first "present" value: for an array, its first non-null element; for a
 * scalar, itself when non-null. Returns `undefined` when nothing qualifies. Used
 * to pick the first populated field among the scalar-or-array schema variants.
 */
export function firstPresentUnknown(...values: unknown[]): unknown {
    for (const value of values) {
        if (Array.isArray(value)) {
            const scalar = value[0];
            if (scalar != null) return scalar;
        } else if (value != null) {
            return value;
        }
    }
    return undefined;
}

// ---------------------------------------------------------------------------
// Number / label formatting
// ---------------------------------------------------------------------------

/**
 * Format a quantity with up to 6 fraction digits. `locale` is exposed for
 * deterministic tests; it defaults to the machine locale, matching the component.
 */
export function formatQuantity(value: number, locale?: string): string {
    return value.toLocaleString(locale, {minimumFractionDigits: 0, maximumFractionDigits: 6});
}

/** Rough Latin-glyph width estimate (no canvas `measureText` inside renderItem). */
export function estimateTextWidthPx(text: string, fontSize = 11): number {
    return text.length * fontSize * 0.58;
}

/**
 * Wrap a formatted numeric field in a green/red span by sign, or return the
 * escaped plain text when the value is missing or exactly zero. The `formatter`
 * is applied to the raw value; its output is HTML-escaped.
 */
export function signedColorField(value: unknown, formatter: (v: unknown) => string, themeDark: boolean): string {
    const num = parseUnknownNumber(value);
    const text = escapeHtml(formatter(value));
    if (num == null || num === 0) return text;
    const color = num > 0 ? (themeDark ? '#4ade80' : '#16a34a') : themeDark ? '#f87171' : '#dc2626';
    return `<span style="color:${color}">${text}</span>`;
}

// ---------------------------------------------------------------------------
// Segment visual attributes
// ---------------------------------------------------------------------------

/** The custody + broker fields that decide a segment's base colour. */
interface ColorSegment {
    custodyType: 'BROKER' | 'IN_TRANSIT';
    brokerId: number | null;
}

/**
 * A segment's base colour: violet while in transit, blue when unassigned to a
 * broker, else the broker's vivid colour (theme-adjusted).
 */
export function segmentBaseColor(segment: ColorSegment, themeDark: boolean, brokers: ReadonlyArray<BrokerLike>): string {
    if (segment.custodyType === 'IN_TRANSIT') return themeDark ? '#c084fc' : '#7c3aed';
    if (segment.brokerId == null) return themeDark ? '#60a5fa' : '#2563eb';
    const brokerColor = getBrokerColor(segment.brokerId, brokers);
    return themeDark ? brokerColor.vivid : brokerColor.vividLight;
}

/** A segment's fill opacity: dim in transit, strong while open, faint once closed. */
export function segmentOpacity(segment: {custodyType: 'BROKER' | 'IN_TRANSIT'; endDate: string | null}): number {
    if (segment.custodyType === 'IN_TRANSIT') return 0.65;
    return segment.endDate == null ? 0.9 : 0.45;
}

/**
 * Bar thickness for a quantity, interpolated between {@link THICKNESS_MIN} and the
 * branch/trunk maximum. A non-positive `qMax` collapses to the minimum; the
 * quantity is clamped into `[0, qMax]` so an outlier cannot overshoot.
 */
export function thicknessForQuantity(quantity: number, qMax: number, isBranch: boolean): number {
    if (qMax <= 0) return THICKNESS_MIN;
    const maxThickness = isBranch ? BRANCH_THICKNESS_MAX : THICKNESS_MAX;
    return THICKNESS_MIN + (clamp(quantity, 0, qMax) / qMax) * (maxThickness - THICKNESS_MIN);
}

/**
 * Whether a segment overlaps a `[minMs, maxMs]` window (half-open on both ends,
 * as the chart draws it). A null bound means "unbounded", so the segment always
 * intersects.
 */
export function segmentIntersectsRange(segment: {startMs: number; endMs: number}, minMs: number | null, maxMs: number | null): boolean {
    if (minMs == null || maxMs == null) return true;
    return segment.endMs > minMs && segment.startMs < maxMs;
}

// ---------------------------------------------------------------------------
// Lane keys & ordering
// ---------------------------------------------------------------------------

/** The transfer-pair id embedded in a fragment id as `/transfer:<id>`, or `null`. */
export function transferPairId(fragmentId: string): string | null {
    return fragmentId.match(/\/transfer:([^/]+)/)?.[1] ?? null;
}

/** Whether a segment is part of a transfer (by fragment id or in-transit custody). */
export function isTransferFragment(segment: {fragmentId: string; custodyType: 'BROKER' | 'IN_TRANSIT'}): boolean {
    return segment.fragmentId.includes('/transfer:') || segment.custodyType === 'IN_TRANSIT';
}

/**
 * The lane key for a (lotId, fragmentId): transfer fragments collapse onto a
 * shared `lot:<lotId>/transfer:<pairId>` lane; everything else keys by its own
 * fragment id.
 */
export function laneKeyForFragmentId(lotId: number, fragmentId: string): string {
    const pairId = transferPairId(fragmentId);
    if (pairId != null) return `lot:${lotId}/transfer:${pairId}`;
    return fragmentId;
}

/** {@link laneKeyForFragmentId} for a segment. */
export function laneKeyForSegment(segment: {lotId: number; fragmentId: string}): string {
    return laneKeyForFragmentId(segment.lotId, segment.fragmentId);
}

/** A transfer lane branches (depth 1); a plain lane is at depth 0. */
export function branchDepthForLaneKey(laneKey: string): number {
    return laneKey.includes('/transfer:') ? 1 : 0;
}

/**
 * The sort tuple for a lane: `[branchDepth, earliestSegmentStartMs, laneKey]`, so
 * trunks precede branches, earlier lanes precede later ones, and the key breaks
 * ties deterministically.
 */
export function laneSortKey(segmentsForLane: ReadonlyArray<{startMs: number}>, laneKey: string): [number, number, string] {
    const firstStart = Math.min(...segmentsForLane.map((segment) => segment.startMs));
    return [branchDepthForLaneKey(laneKey), firstStart, laneKey];
}

// ---------------------------------------------------------------------------
// Event marker classification
// ---------------------------------------------------------------------------

/** Map a raw event kind string to a marker kind (unknown kinds fall back to BUY). */
export function eventMarkerKind(kind: string): EventMarkerKind {
    if (kind === 'TRANSFER_DEPART' || kind === 'TRANSFER_ARRIVE') return 'TRANSFER';
    if (kind === 'ADJUSTMENT_IN') return 'ADJUSTMENT_IN';
    if (kind === 'ADJUSTMENT_OUT') return 'ADJUSTMENT_OUT';
    if (kind === 'SPLIT') return 'SPLIT';
    if (kind === 'SELL') return 'SELL';
    return 'BUY';
}

/** The glyph drawn for a marker kind. */
export function eventMarkerSymbol(kind: EventMarkerKind): string {
    if (kind === 'SELL') return '▼';
    if (kind === 'TRANSFER') return '◆';
    if (kind === 'ADJUSTMENT_IN') return '+';
    if (kind === 'ADJUSTMENT_OUT') return '×';
    if (kind === 'SPLIT') return '│';
    return '▲';
}

/** The subset of a rendered segment needed to classify a transition. */
interface TransitionSegment {
    quantity: number;
    unitPrice: number;
    startMs: number;
}

/**
 * Whether two adjacent segments look like a stock split: quantity changed but
 * notional (quantity × unitPrice) is preserved within a tiny relative tolerance.
 * A zero/negative unit price on either side, or an unchanged quantity, rules it
 * out.
 */
export function isSplitTransition(prev: {quantity: number; unitPrice: number}, next: {quantity: number; unitPrice: number}): boolean {
    if (prev.quantity === next.quantity || prev.unitPrice <= 0 || next.unitPrice <= 0) return false;
    const prevNotional = prev.quantity * prev.unitPrice;
    const nextNotional = next.quantity * next.unitPrice;
    return Math.abs(prevNotional - nextNotional) <= Math.max(0.000001, Math.abs(prevNotional) * 0.0001);
}

/**
 * Classify a transition between two adjacent segments: a known transfer date
 * wins, then a split, then a quantity increase (adjustment in) or decrease
 * (sale); anything else is treated as a transfer.
 */
export function inferredTransitionKind(prev: TransitionSegment, next: TransitionSegment, transferDates: Set<number> | undefined): EventMarkerKind {
    if (transferDates?.has(next.startMs)) return 'TRANSFER';
    if (isSplitTransition(prev, next)) return 'SPLIT';
    if (next.quantity > prev.quantity) return 'ADJUSTMENT_IN';
    if (next.quantity < prev.quantity) return 'SELL';
    return 'TRANSFER';
}

// ---------------------------------------------------------------------------
// Zoom window
// ---------------------------------------------------------------------------

/**
 * Overwrite each dataZoom's `{start, end}` with the externally-driven window when
 * both external bounds are present, otherwise with the initial window. Other
 * zoom fields are preserved.
 */
export function applySharedZoomWindow<T extends {start?: number; end?: number}>(zooms: T[], externalStart: number | null | undefined, externalEnd: number | null | undefined, initialStart: number, initialEnd: number): T[] {
    if (externalStart != null && externalEnd != null) {
        return zooms.map((zoom) => ({...zoom, start: externalStart, end: externalEnd}));
    }
    return zooms.map((zoom) => ({...zoom, start: initialStart, end: initialEnd}));
}
