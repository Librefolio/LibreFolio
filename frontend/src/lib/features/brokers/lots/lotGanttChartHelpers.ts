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

import {buildTooltipDivider, buildTooltipRow} from '$lib/components/charts/echartsTooltipHelpers';
import {utcMs} from '$lib/utils/dateOnly';
import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {clamp, LOT_QUANTITY_FRACTION_DIGITS, scopeBoundaryOf, type ScopeBoundary} from './lotChartShared';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {themed} from '$lib/theme/themePair';
import {CHART_GAIN_LOSS, LOT_GANTT_COLORS} from '$lib/theme/chartTheme';

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
        return utcMs(Number(year), Number(month) - 1, Number(day));
    }

    const parsed = Date.parse(value);
    if (!Number.isFinite(parsed)) return null;
    const date = new Date(parsed);
    return utcMs(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
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
 * Format a quantity with the lots' `LOT_QUANTITY_FRACTION_DIGITS`, up to 10 (C-97a, C-97c). `locale` is exposed for
 * deterministic tests; it defaults to the interface locale (`uiLocale()`, M-18).
 */
export function formatQuantity(value: number, locale: string = uiLocale()): string {
    return value.toLocaleString(locale, {minimumFractionDigits: 0, maximumFractionDigits: LOT_QUANTITY_FRACTION_DIGITS});
}

/**
 * The ICU plural count of `formatQuantity`: the integer part shown, plus 0.5 when a fraction is shown. The plural
 * follows the digits the user reads, never `Number(value)`: «1.0004» is plural in English, although
 * `Intl.PluralRules`, which rounds to three decimals, reads the raw number as singular. `NaN` (`other` in every
 * language) for a value that is not finite.
 */
export function quantityPluralCount(value: number, locale: string = uiLocale()): number {
    if (!Number.isFinite(value)) return NaN;
    const parts = new Intl.NumberFormat(locale, {minimumFractionDigits: 0, maximumFractionDigits: LOT_QUANTITY_FRACTION_DIGITS}).formatToParts(Math.abs(value));
    const whole = Number(
        parts
            .filter((part) => part.type === 'integer')
            .map((part) => part.value)
            .join(''),
    );
    return whole + (parts.some((part) => part.type === 'fraction') ? 0.5 : 0);
}

/** The translator `lotQuantityLine` needs: the app's `$t`. */
type QuantityTranslate = (key: string, options?: {values?: Record<string, string | number>}) => string;

/**
 * The quantity line of a lot's tooltip, its noun in the language's plural: «10 → 0 shares» for a closed lot, «3
 * shares open out of 10» for an open one. `openText` and `originalText` are the figures as shown — formatted, and
 * masked when privacy is on. The open line's plural comes from the digits shown (`quantityPluralCount`) and is
 * always `other` while the figures are masked, so the noun cannot reveal a quantity of 1.
 */
export function lotQuantityLine(t: QuantityTranslate, {closed, open, openText, originalText, masked}: {closed: boolean; open: number; openText: string; originalText: string; masked: boolean}): string {
    if (closed) return t('brokers.lots.tooltip.quantityClosed', {values: {original: originalText, count: 0}});
    return t('brokers.lots.tooltip.quantityOpen', {values: {open: openText, original: originalText, count: masked ? NaN : quantityPluralCount(open)}});
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
    const color = num > 0 ? themed(CHART_GAIN_LOSS.portfolio.gain, themeDark) : themed(CHART_GAIN_LOSS.portfolio.loss, themeDark);
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
    if (segment.custodyType === 'IN_TRANSIT') return themed(LOT_GANTT_COLORS.inTransit, themeDark);
    if (segment.brokerId == null) return themed(LOT_GANTT_COLORS.noBroker, themeDark);
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

/** Map a raw event kind string to a marker kind (unknown kinds fall back to BUY). A transfer leg read at the scope's
 *  edge (`scopeBoundary`, J-48) is a transfer, whatever adjustment kind carries its figures. */
export function eventMarkerKind(kind: string, scopeBoundary?: ScopeBoundary | null): EventMarkerKind {
    if (scopeBoundary === 'IN' || scopeBoundary === 'OUT') return 'TRANSFER';
    if (kind === 'TRANSFER_DEPART' || kind === 'TRANSFER_ARRIVE') return 'TRANSFER';
    if (kind === 'ADJUSTMENT_IN') return 'ADJUSTMENT_IN';
    if (kind === 'ADJUSTMENT_OUT') return 'ADJUSTMENT_OUT';
    if (kind === 'SPLIT') return 'SPLIT';
    if (kind === 'SELL') return 'SELL';
    return 'BUY';
}

/** The i18n key of a marker's label: `labelKind` when the event has one (`TRANSFER_IN`/`TRANSFER_OUT`, J-48), else the
 *  marker kind's own, a transfer reading the departure's. */
export function eventMarkerLabelKey(kind: EventMarkerKind, labelKind?: string | null): string {
    return `brokers.lots.chartMarkers.eventType.${labelKind ?? (kind === 'TRANSFER' ? 'TRANSFER_DEPART' : kind)}`;
}

// ---------------------------------------------------------------------------
// Marker tooltips (Q-G29-1)
// ---------------------------------------------------------------------------

/**
 * One event behind a marker, as its tooltip names it (Q-G29-1, the developer's option (a)): every marker says what
 * happened, when, how many units and at which broker.
 */
export interface GanttMarkerEvent {
    /** The marker kind ({@link eventMarkerKind}). */
    kind: EventMarkerKind;
    /** `TRANSFER_IN`/`TRANSFER_OUT` at the scope's edge, `TRANSFER_DEPART`/`TRANSFER_ARRIVE` for an internal leg, else `null`. */
    labelKind: string | null;
    /** `YYYY-MM-DD`, as sent. */
    date: string;
    quantity: number | null;
    brokerId: number | null;
    sourceBrokerId: number | null;
    destinationBrokerId: number | null;
}

/** One block of a marker tooltip: the event's title and its rows, as plain text (escaped by {@link markerTooltipHtml}). */
export interface GanttMarkerTooltipBlock {
    title: string;
    rows: Array<{label: string; value: string}>;
}

/** What {@link ganttMarkerTooltipBlocks} needs from the page: the translator, the broker names and the formats. */
export interface GanttMarkerTooltipDeps {
    t: (key: string) => string;
    brokerName: (brokerId: number | null) => string;
    formatDate: (date: string) => string;
    formatQuantity: (value: number) => string;
    /** `maskableQuantity`: the placeholder while privacy mode is on. */
    maskQuantity: (formatted: string) => string;
}

/**
 * The label kind of a `lot_events` row: `TRANSFER_IN`/`TRANSFER_OUT` when it crosses the scope (any kind, J-48), its
 * own kind for an internal transfer leg — so an arrival reads `TRANSFER_ARRIVE`, not the departure's label —, else
 * `null` (the marker kind's own label).
 */
export function markerLabelKind(event: {kind: string; scope_boundary?: unknown}): string | null {
    const boundary = scopeBoundaryOf(event);
    if (boundary === 'IN') return 'TRANSFER_IN';
    if (boundary === 'OUT') return 'TRANSFER_OUT';
    if (event.kind === 'TRANSFER_DEPART' || event.kind === 'TRANSFER_ARRIVE') return event.kind;
    return null;
}

function parseBrokerId(value: unknown): number | null {
    const parsed = parseUnknownNumber(value);
    return parsed != null && Number.isInteger(parsed) ? parsed : null;
}

/**
 * A `lot_events` row as the event of a marker. A row at the scope's edge keeps its own broker only: the partner of a
 * transfer leg read at the edge is never named (J-48), whatever ids the row carries.
 */
export function ganttMarkerEvent(row: {kind: string; date: unknown; quantity?: unknown; broker_id?: unknown; source_broker_id?: unknown; destination_broker_id?: unknown; scope_boundary?: unknown}): GanttMarkerEvent {
    const boundary = scopeBoundaryOf(row);
    return {
        kind: eventMarkerKind(row.kind, boundary),
        labelKind: markerLabelKind(row),
        date: safeUnknownString(row.date) ?? '',
        quantity: parseUnknownNumber(row.quantity),
        brokerId: parseBrokerId(row.broker_id),
        sourceBrokerId: boundary ? null : parseBrokerId(row.source_broker_id),
        destinationBrokerId: boundary ? null : parseBrokerId(row.destination_broker_id),
    };
}

/**
 * The broker rows of an event: «From A / To B» for a transfer between the user's brokers — the side a row does not
 * carry is left out, never guessed: an arrival row with no source names only where it went —, else the event's
 * broker.
 */
function markerBrokerRows(event: GanttMarkerEvent, deps: GanttMarkerTooltipDeps): Array<{label: string; value: string}> {
    const internalTransfer = event.kind === 'TRANSFER' && (event.labelKind == null || event.labelKind === 'TRANSFER_DEPART' || event.labelKind === 'TRANSFER_ARRIVE');
    if (internalTransfer) {
        const from = event.sourceBrokerId ?? (event.labelKind === 'TRANSFER_DEPART' ? event.brokerId : null);
        const to = event.destinationBrokerId ?? (event.labelKind === 'TRANSFER_ARRIVE' ? event.brokerId : null);
        if (from != null || to != null) {
            const rows: Array<{label: string; value: string}> = [];
            if (from != null) rows.push({label: deps.t('common.from'), value: deps.brokerName(from)});
            if (to != null) rows.push({label: deps.t('common.to'), value: deps.brokerName(to)});
            return rows;
        }
    }
    return event.brokerId != null ? [{label: deps.t('common.broker'), value: deps.brokerName(event.brokerId)}] : [];
}

/**
 * One tooltip block per event, in the given order: its label as the title, then its date, its quantity (unsigned, the
 * title says which way the units went; masked in privacy mode) and its broker rows.
 */
export function ganttMarkerTooltipBlocks(events: readonly GanttMarkerEvent[], deps: GanttMarkerTooltipDeps): GanttMarkerTooltipBlock[] {
    return events.map((event) => {
        const rows: Array<{label: string; value: string}> = [{label: deps.t('common.date'), value: deps.formatDate(event.date)}];
        if (event.quantity != null) rows.push({label: deps.t('common.quantity'), value: deps.maskQuantity(deps.formatQuantity(Math.abs(event.quantity)))});
        rows.push(...markerBrokerRows(event, deps));
        return {title: deps.t(eventMarkerLabelKey(event.kind, event.labelKind)), rows};
    });
}

/**
 * The markers to draw, one per kind, lane and day in first-appearance order — the glyphs the chart always drew —, each
 * with every event of its point (same lane, same day, whatever the kind), in input order: two events on one point are
 * one glyph or two overlapping ones, and the tooltip lists them all instead of dropping the second.
 */
export function groupMarkerEvents<T extends {kind: EventMarkerKind; laneIndex: number; dateMs: number; event: GanttMarkerEvent}>(entries: readonly T[]): Array<{first: T; events: GanttMarkerEvent[]}> {
    const eventsByPoint = new Map<string, GanttMarkerEvent[]>();
    const markers: Array<{first: T; events: GanttMarkerEvent[]}> = [];
    const drawn = new Set<string>();
    for (const entry of entries) {
        const point = `${entry.laneIndex}:${entry.dateMs}`;
        let events = eventsByPoint.get(point);
        if (!events) {
            events = [];
            eventsByPoint.set(point, events);
        }
        events.push(entry.event);
        const glyph = `${entry.kind}:${point}`;
        if (drawn.has(glyph)) continue;
        drawn.add(glyph);
        markers.push({first: entry, events});
    }
    return markers;
}

/** The HTML of a marker tooltip: each block's title, then its rows, blocks apart by a divider; every text escaped. */
export function markerTooltipHtml(blocks: readonly GanttMarkerTooltipBlock[], theme: {bg: string; border: string; textColor: string; mutedColor: string}): string {
    const body = blocks.map((block) => `<div style="font-weight:700;margin-bottom:2px">${escapeHtml(block.title)}</div>${block.rows.map((row) => buildTooltipRow(escapeHtml(row.label), escapeHtml(row.value))).join('')}`).join(buildTooltipDivider(theme.border));
    return `<div style="min-width:180px;font-size:11px;color:${theme.textColor}">${body}</div>`;
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
    /** `null` when the price has no rate to the target currency. */
    unitPrice: number | null;
    startMs: number;
}

/**
 * Whether two adjacent segments look like a stock split: quantity changed but
 * notional (quantity × unitPrice) is preserved within a tiny relative tolerance.
 * An unknown, zero or negative unit price on either side, or an unchanged
 * quantity, rules it out. This inference is only the fallback for a chart given
 * no explicit lot events; the backend's own SPLIT events need no price.
 */
export function isSplitTransition(prev: {quantity: number; unitPrice: number | null}, next: {quantity: number; unitPrice: number | null}): boolean {
    if (prev.quantity === next.quantity || prev.unitPrice == null || next.unitPrice == null || prev.unitPrice <= 0 || next.unitPrice <= 0) return false;
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
