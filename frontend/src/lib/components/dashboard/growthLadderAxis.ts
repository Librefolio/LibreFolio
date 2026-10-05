/**
 * The category x axis of the GrowthChart ladder (P&L candles and Income): which bucket
 * carries a label, which bucket edges carry a separator, and how far an edge label moves
 * inward so the canvas does not clip it (S7 — D4, D4-bis).
 *
 * Pure: the component passes the bucket closing dates and the measured geometry, then
 * turns the plan into ECharts options with `ladderAxisOption`. Everything is keyed by the
 * category's raw value (the ISO closing date), never by index.
 *
 * Contract:
 *   - Bucket i covers the calendar days (closingDates[i-1], closingDates[i]]; bucket 0
 *     covers [firstDate, closingDates[0]]. No buckets: an empty plan.
 *   - Geometry not measured yet (plotWidthPx not a finite number greater than 0): the same
 *     empty plan, no labels, no separators, no shifts, key ''. The component plans again
 *     right after it reads the grid rect.
 *   - The visible window is clamped to the buckets, its ends swapped if reversed.
 *   - The decisions (mode, thinning step, year, separators, edge shifts) are taken on the
 *     VISIBLE window, where slot = plotWidthPx / visible bucket count and the centre of
 *     bucket i sits at (i - visibleStartIndex + 0.5) * slot. Labels are then produced for
 *     EVERY bucket with those decisions, so panning never makes them swim.
 *   - Mode 'closing' (step 1): the day-and-month closing date on every bucket, when all
 *     visible labels fit.
 *   - Otherwise mode 'month': the short month name on the bucket whose covered range
 *     contains that month's 1st, thinned to every k months (k = 1, 2, 3, 6, 12, then
 *     whole years: 24, 36…), aligned on the calendar (month0 % k === 0; beyond twelve,
 *     January of years divisible by k/12). The smallest k whose visible labels fit wins.
 *     A bucket holding several aligned 1sts carries the earliest. A January label always
 *     carries the year, whatever `withYear` says.
 *     The search stops at the first k that leaves fewer than 2 visible labels.
 *   - D4-bis: when no month thinning fits with at least 2 visible labels, fall back to
 *     closing dates on every k-th bucket counted from the last bucket of the series
 *     ((n - 1 - i) % k === 0), with the smallest k >= 2 that fits. Mode 'closing', step k.
 *     k runs from 2 upward and stops at the first k that fits OR leaves fewer than 2
 *     visible labels (the degenerate stop); this always terminates because k = n labels
 *     only the last bucket.
 *   - Year (`withYear`): every label gets a two-digit year when the visible window spans
 *     365 days or more, counted inclusively from the covered start of its first bucket to
 *     the close of its last. A closing label never gets the year otherwise: no January
 *     rule there.
 *   - "Fits": consecutive visible labels are at least LADDER_LABEL_GAP_PX apart, widths
 *     estimated by `estimateLadderLabelWidthPx`, edge shifts included.
 *   - Separators: every bucket while the slot is at least CANDLE_MIN_SLOT_PX, otherwise only
 *     the buckets whose covered range contains a 1st. In that second case, when exactly one
 *     visible bucket holds a 1st and it is not the first visible bucket, the first visible
 *     bucket gets a separator too: ECharts draws a lone band tick on the axis start, and
 *     the first visible bucket's left edge is the plot edge, where a line is drawn anyway.
 *   - Edge shift: the leftmost and rightmost visible labels move inward by the smallest
 *     whole number of px that keeps them LADDER_EDGE_SAFETY_PX inside the room between
 *     the plot and the canvas edge. Negative moves left.
 */
import {CANDLE_MIN_SLOT_PX} from '$lib/components/charts/timeSeriesAggregation';

/** Minimum clear space between two neighbouring axis labels, in px. */
export const LADDER_LABEL_GAP_PX = 8;

/** Distance an edge label keeps from the canvas edge, in px. */
export const LADDER_EDGE_SAFETY_PX = 2;

export interface LadderAxisInput {
    /** Category raw values: the ISO closing date of each bucket, oldest first. */
    closingDates: readonly string[];
    /** First day of the series (ISO): bucket 0 covers [firstDate, closingDates[0]]. */
    firstDate: string;
    /** Visible window as category indices, inclusive. Out-of-range values are clamped. */
    visibleStartIndex: number;
    visibleEndIndex: number;
    /** Width of the plot (the grid rect, margins excluded), in px. */
    plotWidthPx: number;
    /** Room between the plot and the canvas edge, in px. Omitted: unlimited. */
    leftRoomPx?: number;
    rightRoomPx?: number;
    /** BCP 47 locale for Intl.DateTimeFormat. */
    locale: string;
    /** Axis label font size, in px. Default 14. */
    fontSizePx?: number;
}

export type LadderAxisMode = 'closing' | 'month';

export interface LadderAxisPlan {
    mode: LadderAxisMode;
    /** 'closing': every step-th bucket counted from the last (1 = every bucket).
     *  'month': months per label (1, 2, 3, 6, 12, 24…). */
    step: number;
    /** The visible window spans 365 days or more, so every label carries the year. */
    withYear: boolean;
    /** Label text by category raw value. A bucket absent from the map carries no label. */
    labels: Map<string, string>;
    /** Category raw values whose bucket gets a separator on its left edge. */
    separators: Set<string>;
    /** Signed inward shift in px by category raw value; negative moves left. */
    edgeShifts: Map<string, number>;
    /** Changes whenever anything above changes: the component re-applies the axis only then. */
    key: string;
}

export interface LadderAxisOption {
    axisLabel: {
        interval: (index: number, raw: string) => boolean;
        formatter: (raw: string) => string;
        rich: Record<string, {padding: [number, number, number, number]}>;
    };
    splitLine: {
        interval: (index: number, raw: string) => boolean;
    };
}

const DEFAULT_FONT_SIZE_PX = 14;
const DAY_MS = 86_400_000;

/** Conservative width estimate of an axis label, in px. */
export function estimateLadderLabelWidthPx(text: string, fontSizePx = DEFAULT_FONT_SIZE_PX): number {
    return text.length * fontSizePx * 0.6;
}

type LabelStyle = 'closing' | 'closingYear' | 'month' | 'monthYear';

const LABEL_FORMATS: Record<LabelStyle, Intl.DateTimeFormatOptions> = {
    closing: {day: 'numeric', month: 'short', timeZone: 'UTC'},
    closingYear: {day: 'numeric', month: 'short', year: '2-digit', timeZone: 'UTC'},
    month: {month: 'short', timeZone: 'UTC'},
    monthYear: {month: 'short', year: '2-digit', timeZone: 'UTC'},
};

const formatterCache = new Map<string, Intl.DateTimeFormat>();

// WHY: building an Intl.DateTimeFormat costs far more than formatting with one, and the axis is planned again on every zoom and resize.
function formatDay(locale: string, style: LabelStyle, day: number): string {
    const cacheKey = `${locale}|${style}`;
    let formatter = formatterCache.get(cacheKey);
    if (formatter === undefined) {
        formatter = new Intl.DateTimeFormat(locale, LABEL_FORMATS[style]);
        formatterCache.set(cacheKey, formatter);
    }
    return formatter.format(day * DAY_MS);
}

/** Whole UTC day number of an ISO date: calendar arithmetic free of time zones and DST. */
function dayOf(iso: string): number {
    return Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10))) / DAY_MS;
}

interface MonthFirst {
    day: number;
    year: number;
    month0: number;
}

/** The 1sts of a month inside [fromDay, toDay], oldest first. */
function monthFirstsBetween(fromDay: number, toDay: number): MonthFirst[] {
    const firsts: MonthFirst[] = [];
    const from = new Date(fromDay * DAY_MS);
    let year = from.getUTCFullYear();
    let month0 = from.getUTCMonth() + (from.getUTCDate() === 1 ? 0 : 1);
    for (;;) {
        if (month0 > 11) {
            year += 1;
            month0 -= 12;
        }
        const day = Date.UTC(year, month0, 1) / DAY_MS;
        if (day > toDay) return firsts;
        firsts.push({day, year, month0});
        month0 += 1;
    }
}

function emptyPlan(): LadderAxisPlan {
    return {mode: 'closing', step: 1, withYear: false, labels: new Map(), separators: new Set(), edgeShifts: new Map(), key: ''};
}

interface Candidate {
    mode: LadderAxisMode;
    step: number;
    /** Label of bucket i under this candidate's decisions; undefined = no label. */
    textOf: (index: number) => string | undefined;
}

export function planLadderAxis(input: LadderAxisInput): LadderAxisPlan {
    const {closingDates, firstDate, plotWidthPx, leftRoomPx, rightRoomPx, locale} = input;
    const fontSizePx = input.fontSizePx ?? DEFAULT_FONT_SIZE_PX;
    const n = closingDates.length;
    if (n === 0 || !Number.isFinite(plotWidthPx) || plotWidthPx <= 0) return emptyPlan();

    const clampIndex = (value: number, fallback: number) => (Number.isFinite(value) ? Math.max(0, Math.min(n - 1, Math.round(value))) : fallback);
    let vs = clampIndex(input.visibleStartIndex, 0);
    let ve = clampIndex(input.visibleEndIndex, n - 1);
    if (vs > ve) [vs, ve] = [ve, vs];
    const slot = plotWidthPx / (ve - vs + 1);
    const centre = (index: number) => (index - vs + 0.5) * slot;

    const closingDays = closingDates.map(dayOf);
    const coveredStart = (index: number) => (index === 0 ? dayOf(firstDate) : closingDays[index - 1] + 1);
    const firsts = closingDays.map((day, index) => monthFirstsBetween(coveredStart(index), day));
    const withYear = closingDays[ve] - coveredStart(vs) + 1 >= 365;

    const closingTexts: Array<string | undefined> = new Array(n);
    const closingText = (index: number): string => (closingTexts[index] ??= formatDay(locale, withYear ? 'closingYear' : 'closing', closingDays[index]));
    const monthText = (first: MonthFirst): string => formatDay(locale, withYear || first.month0 === 0 ? 'monthYear' : 'month', first.day);

    // Visible labelled buckets in index order → their edge shifts (by index) and whether they all fit.
    const evaluate = (visible: readonly number[], textOf: (index: number) => string | undefined) => {
        const widths = visible.map((index) => estimateLadderLabelWidthPx(textOf(index) as string, fontSizePx));
        const shifts = new Map<number, number>();
        if (visible.length > 0) {
            const lo = visible[0];
            const hi = visible[visible.length - 1];
            if (leftRoomPx !== undefined) {
                const need = -leftRoomPx + LADDER_EDGE_SAFETY_PX - (centre(lo) - widths[0] / 2);
                if (need > 0) shifts.set(lo, Math.ceil(need));
            }
            if (rightRoomPx !== undefined) {
                const over = centre(hi) + widths[widths.length - 1] / 2 - (plotWidthPx + rightRoomPx - LADDER_EDGE_SAFETY_PX);
                if (over > 0) shifts.set(hi, (shifts.get(hi) ?? 0) - Math.ceil(over));
            }
            if (shifts.get(hi) === 0) shifts.delete(hi);
        }
        let fits = true;
        for (let j = 1; j < visible.length && fits; j++) {
            const rightEdge = centre(visible[j - 1]) + (shifts.get(visible[j - 1]) ?? 0) + widths[j - 1] / 2;
            const leftEdge = centre(visible[j]) + (shifts.get(visible[j]) ?? 0) - widths[j] / 2;
            fits = leftEdge - rightEdge >= LADDER_LABEL_GAP_PX;
        }
        return {shifts, fits};
    };

    const visibleWhere = (textOf: (index: number) => string | undefined): number[] => {
        const visible: number[] = [];
        for (let index = vs; index <= ve; index++) if (textOf(index) !== undefined) visible.push(index);
        return visible;
    };

    let chosen: (Candidate & {shifts: Map<number, number>}) | undefined;

    const everyClosing: Candidate = {mode: 'closing', step: 1, textOf: closingText};
    const allVisible = visibleWhere(everyClosing.textOf);
    const closingTrial = evaluate(allVisible, everyClosing.textOf);
    if (closingTrial.fits) chosen = {...everyClosing, shifts: closingTrial.shifts};

    if (chosen === undefined) {
        const years = new Date(closingDays[n - 1] * DAY_MS).getUTCFullYear() - new Date(coveredStart(0) * DAY_MS).getUTCFullYear() + 1;
        // WHY: beyond `years + 1` whole years at most one aligned January remains, so the search has always stopped by then.
        const steps = [1, 2, 3, 6, 12, ...Array.from({length: years}, (_unused, m) => 12 * (m + 2))];
        for (const k of steps) {
            const aligned = (first: MonthFirst) => (k <= 12 ? first.month0 % k === 0 : first.month0 === 0 && first.year % (k / 12) === 0);
            const textOf = (index: number) => {
                const first = firsts[index].find(aligned);
                return first === undefined ? undefined : monthText(first);
            };
            const visible = visibleWhere(textOf);
            if (visible.length < 2) break;
            const trial = evaluate(visible, textOf);
            if (trial.fits) {
                chosen = {mode: 'month', step: k, textOf, shifts: trial.shifts};
                break;
            }
        }
    }

    // D4-bis: closing dates on every k-th bucket counted from the last one.
    for (let k = 2; chosen === undefined && k <= n; k++) {
        const textOf = (index: number) => ((n - 1 - index) % k === 0 ? closingText(index) : undefined);
        const visible: number[] = [];
        for (let index = ve - ((k - ((n - 1 - ve) % k)) % k); index >= vs; index -= k) visible.unshift(index);
        const trial = evaluate(visible, textOf);
        if (trial.fits || visible.length < 2) chosen = {mode: 'closing', step: k, textOf, shifts: trial.shifts};
    }
    // WHY: unreachable (one bucket always fits every closing), kept so the plan type never widens to undefined.
    chosen ??= {...everyClosing, shifts: new Map()};

    const labels = new Map<string, string>();
    const separators = new Set<string>();
    const sparse = slot < CANDLE_MIN_SLOT_PX;
    // WHY: ECharts draws a lone band tick on the axis start (fixOnBandTicksCoords), so one visible month edge would move there; the first visible bucket's edge is the plot edge, where a line is drawn anyway.
    let visibleMonthEdges = 0;
    for (let index = vs; index <= ve; index++) if (firsts[index].length > 0) visibleMonthEdges += 1;
    const anchorIndex = sparse && visibleMonthEdges === 1 && firsts[vs].length === 0 ? vs : -1;
    for (let index = 0; index < n; index++) {
        const text = chosen.textOf(index);
        if (text !== undefined) labels.set(closingDates[index], text);
        if (!sparse || firsts[index].length > 0 || index === anchorIndex) separators.add(closingDates[index]);
    }
    const edgeShifts = new Map<string, number>([...chosen.shifts].map(([index, px]): [string, number] => [closingDates[index], px]));
    const key = JSON.stringify([chosen.mode, chosen.step, withYear, [...labels], [...separators], [...edgeShifts]]);
    return {mode: chosen.mode, step: chosen.step, withYear, labels, separators, edgeShifts, key};
}

/** The rich style that moves a label `px` inward: padding on the far side shifts the centred glyph by half of it. */
function shiftStyleName(px: number): string {
    return `lfShift${px < 0 ? 'L' : 'R'}${Math.abs(px)}`;
}

export function ladderAxisOption(plan: LadderAxisPlan): LadderAxisOption {
    const rich: Record<string, {padding: [number, number, number, number]}> = {};
    for (const px of plan.edgeShifts.values()) {
        if (px !== 0) rich[shiftStyleName(px)] = {padding: px < 0 ? [0, 2 * -px, 0, 0] : [0, 0, 0, 2 * px]};
    }
    return {
        axisLabel: {
            interval: (_index, raw) => plan.labels.has(raw),
            formatter: (raw) => {
                const text = plan.labels.get(raw);
                if (text === undefined) return '';
                const px = plan.edgeShifts.get(raw) ?? 0;
                return px === 0 ? text : `{${shiftStyleName(px)}|${text}}`;
            },
            rich,
        },
        splitLine: {interval: (_index, raw) => plan.separators.has(raw)},
    };
}
