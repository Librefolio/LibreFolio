/**
 * The category x axis of the GrowthChart ladder (P&L candles and Income): the text of each
 * bucket, which buckets carry it, whether the labels are rotated, which bucket edges carry a
 * separator, and how far an edge label moves inward so the canvas does not clip it.
 *
 * Pure: the component passes the bucket closing dates, the rung and the measured geometry, then
 * turns the plan into ECharts options with `ladderAxisOption`. Everything is keyed by the
 * category's raw value (the ISO closing date), never by index.
 *
 * Contract (developer's decision of 07/10/2026, which replaces the text rules of D4 and D4-bis;
 * the separators are D4's):
 *   - Bucket i covers the calendar days (closingDates[i-1], closingDates[i]]; bucket 0 covers
 *     [firstDate, closingDates[0]]. No buckets, or geometry not measured yet (plotWidthPx not a
 *     finite number greater than 0): the empty plan, with no labels, no separators, no shifts and
 *     key ''. The component plans again right after it reads the grid rect.
 *   - The visible window is clamped to the buckets, rounded, its ends swapped if reversed. The
 *     decisions are taken on it: slot = plotWidthPx / visible bucket count, and the centre of
 *     bucket i sits at (i - visibleStartIndex + 0.5) * slot.
 *   - Text: a bucket is named after the START of its calendar period on the rung, also when the
 *     series covers only part of it (data from Thursday 1 January 2026: the week is "Dec 29").
 *       - Day rungs (1D, 3D, 1W, 2W): the day ("20"); the day and month ("Nov 3") on the first
 *         visible label and where the month changes; `labelWithYear` of the day and month
 *         ("Jan 5 '26") where the year changes. Never the year on the first visible label.
 *       - 1M: the month ("Nov"). 3M: `quarterLabel` ("Q2"). 6M: the months it spans joined by an
 *         en dash ("Jul–Dec"). Each one through `labelWithYear` ("Oct '25") on the first visible
 *         label and where the year changes.
 *       - 1Y: the year ("2026").
 *     "Changes" compares a bucket with the previous LABELLED bucket, so two neighbouring labels
 *     never print the same text. Every labelled bucket gets its text, visible or not, so a pan
 *     changes only the text of the first visible label.
 *   - Horizontal (rotate 0, step 1): when every visible bucket's label fits, every bucket carries
 *     one. "Fits": consecutive visible labels are at least LADDER_LABEL_GAP_PX apart, widths
 *     estimated by `estimateLadderLabelWidthPx`, edge shifts included. Edge shift: the leftmost
 *     and rightmost visible labels move inward by the smallest whole number of px that keeps them
 *     LADDER_EDGE_SAFETY_PX inside the room between the plot and the canvas edge. Negative moves
 *     left.
 *   - Otherwise every label is rotated by 45°, the way ECharts draws `rotate: 45`: counter-
 *     clockwise, right-aligned and centred on its tick. Rotated labels one slot apart are
 *     slot * √½ apart across their text, so they are thinned only when that is less than one
 *     label row (font * LADDER_LABEL_ROW_EM): every k-th bucket counted from the last one
 *     ((n - 1 - i) % k === 0), with k = ceil(font * LADDER_LABEL_ROW_EM / (slot * √½)), at
 *     least 1. Rotated labels do not shift. From the left, a visible candidate whose text, in
 *     its first-label form, would come closer than LADDER_EDGE_SAFETY_PX to the canvas edge
 *     stays without a label, and the next candidate is tried as the first. From the right, the
 *     same for the label's top corner, which passes its tick by font/2 * √½. Omitted room:
 *     nothing is dropped on that side.
 *   - widestText: the visible label with the most characters, the leftmost of equals; '' when no
 *     visible bucket carries a label. ECharts' legacy `containLabel` measures the formatter on a
 *     sample of buckets (one every ceil(n / 40) past 40) without asking `interval`, and reserves
 *     the band under the axis for the tallest sampled label: a bucket without a label answers
 *     with widestText.
 *   - labelBox: when rotated and the caller passes `measureLabelPx`, the widest measured text
 *     among the visible labelled buckets (W) and one font height; otherwise null. The option
 *     gives every label `width` W and `lineHeight` font, so zrender wraps each one in an
 *     invisible W-wide box: every label the sample measures is W wide, and the band holds the
 *     widest label even when the sample misses it. The boxes change the band, never where a
 *     label is drawn. Without a measure the band rests on widestText alone, which a long label
 *     at an unsampled bucket can overrun.
 *   - Separators: every bucket while the slot is at least CANDLE_MIN_SLOT_PX, otherwise only
 *     the buckets whose covered range contains a 1st. In that second case, when exactly one
 *     visible bucket holds a 1st and it is not the first visible bucket, the first visible
 *     bucket gets a separator too: ECharts draws a lone band tick on the axis start, and
 *     the first visible bucket's left edge is the plot edge, where a line is drawn anyway.
 */
import {CANDLE_MIN_SLOT_PX} from '$lib/components/charts/timeSeriesAggregation';
import {calendarPeriodOf, type LadderRung} from './growthLadderBuckets';

/** Minimum clear space between two neighbouring axis labels, in px. */
export const LADDER_LABEL_GAP_PX = 8;

/** Distance an edge label keeps from the canvas edge, in px. */
export const LADDER_EDGE_SAFETY_PX = 2;

/**
 * One rotated label's row across its text, in font heights.
 *
 * WHY not 1: with the labelBox, ECharts hides an edge label whose box meets its neighbour's
 * (fixMinMaxLabelShow), and W-wide boxes meet as soon as they are closer than one line across
 * the text. Chromium lays a 14 px line out 14.28 px tall, so a row is 14.3 px at 14 px.
 */
export const LADDER_LABEL_ROW_EM = 14.3 / 14;

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
    /** The rung the buckets were built on: it decides the period each label names. */
    rung: LadderRung;
    /** The quarter's short name ("Q4"), from the caller's translations. */
    quarterLabel: (quarter: 1 | 2 | 3 | 4) => string;
    /** A label with its two-digit year ("Oct '25"), from the caller's translations. */
    labelWithYear: (label: string, year: string) => string;
    /** Painted width of a label text, in px. Omitted: no labelBox. */
    measureLabelPx?: (text: string) => number;
}

export interface LadderAxisPlan {
    /** 0: every bucket carries its label. 45: all labels rotated, thinned when even that is too dense. */
    rotate: 0 | 45;
    /** Every step-th bucket counted from the last one carries a label (1 = every bucket). */
    step: number;
    /** Label text by category raw value. A bucket absent from the map carries no label. */
    labels: Map<string, string>;
    /** Category raw values whose bucket gets a separator on its left edge. */
    separators: Set<string>;
    /** Signed inward shift in px by category raw value; negative moves left. Horizontal only. */
    edgeShifts: Map<string, number>;
    /** The widest visible label: what a bucket without a label answers when ECharts measures it. */
    widestText: string;
    /** The box every rotated label is drawn in, so ECharts reserves room for the widest one; null without one. */
    labelBox: {widthPx: number; lineHeightPx: number} | null;
    /** Changes whenever anything above changes: the component re-applies the axis only then. */
    key: string;
}

export interface LadderAxisOption {
    axisLabel: {
        rotate: 0 | 45;
        width: number | null;
        lineHeight: number | null;
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
const DAY_RUNGS: ReadonlySet<LadderRung> = new Set<LadderRung>(['1D', '3D', '1W', '2W']);

/** Conservative width estimate of an axis label, in px. */
export function estimateLadderLabelWidthPx(text: string, fontSizePx = DEFAULT_FONT_SIZE_PX): number {
    return text.length * fontSizePx * 0.6;
}

type LabelStyle = 'day' | 'dayMonth' | 'month' | 'year' | 'twoDigitYear';

const LABEL_FORMATS: Record<LabelStyle, Intl.DateTimeFormatOptions> = {
    day: {day: 'numeric', timeZone: 'UTC'},
    dayMonth: {day: 'numeric', month: 'short', timeZone: 'UTC'},
    month: {month: 'short', timeZone: 'UTC'},
    year: {year: 'numeric', timeZone: 'UTC'},
    twoDigitYear: {year: '2-digit', timeZone: 'UTC'},
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
    return {rotate: 0, step: 1, labels: new Map(), separators: new Set(), edgeShifts: new Map(), widestText: '', labelBox: null, key: ''};
}

export function planLadderAxis(input: LadderAxisInput): LadderAxisPlan {
    const {closingDates, firstDate, plotWidthPx, leftRoomPx, rightRoomPx, locale, rung, quarterLabel, labelWithYear, measureLabelPx} = input;
    const fontSizePx = input.fontSizePx ?? DEFAULT_FONT_SIZE_PX;
    const n = closingDates.length;
    if (n === 0 || !Number.isFinite(plotWidthPx) || plotWidthPx <= 0) return emptyPlan();

    const clampIndex = (value: number, fallback: number) => (Number.isFinite(value) ? Math.max(0, Math.min(n - 1, Math.round(value))) : fallback);
    let vs = clampIndex(input.visibleStartIndex, 0);
    let ve = clampIndex(input.visibleEndIndex, n - 1);
    if (vs > ve) [vs, ve] = [ve, vs];
    const slot = plotWidthPx / (ve - vs + 1);
    const centre = (index: number) => (index - vs + 0.5) * slot;
    const widthOf = (text: string) => estimateLadderLabelWidthPx(text, fontSizePx);

    // Texts: every form of a bucket is built at most once, and only when a rule asks for it.
    const dayRung = DAY_RUNGS.has(rung);
    const starts = closingDates.map((closing) => calendarPeriodOf(closing, rung).start);
    const startDay = (index: number) => dayOf(starts[index]);
    const shortTexts: Array<string | undefined> = new Array(n);
    const monthTexts: Array<string | undefined> = new Array(n);
    const yearTexts: Array<string | undefined> = new Array(n);
    const nameOf = (index: number): string => {
        const start = starts[index];
        if (dayRung) return formatDay(locale, 'day', startDay(index));
        if (rung === '1Y') return formatDay(locale, 'year', startDay(index));
        if (rung === '1M') return formatDay(locale, 'month', startDay(index));
        const month0 = Number(start.slice(5, 7)) - 1;
        if (rung === '3M') return quarterLabel((Math.floor(month0 / 3) + 1) as 1 | 2 | 3 | 4);
        const lastMonthDay = Date.UTC(Number(start.slice(0, 4)), month0 + 5, 1) / DAY_MS;
        return `${formatDay(locale, 'month', startDay(index))}–${formatDay(locale, 'month', lastMonthDay)}`;
    };
    const shortText = (index: number): string => (shortTexts[index] ??= nameOf(index));
    const monthText = (index: number): string => (monthTexts[index] ??= formatDay(locale, 'dayMonth', startDay(index)));
    const yearText = (index: number): string => (yearTexts[index] ??= labelWithYear(dayRung ? monthText(index) : shortText(index), formatDay(locale, 'twoDigitYear', startDay(index))));
    /** The text bucket `index` carries as the first visible label. */
    const firstText = (index: number): string => (rung === '1Y' ? shortText(index) : dayRung ? monthText(index) : yearText(index));
    /** The text of a labelled bucket, given the labelled bucket before it and whether it is the first visible one. */
    const textOf = (index: number, previous: number | undefined, first: boolean): string => {
        if (rung === '1Y') return shortText(index);
        if (first || previous === undefined) return firstText(index);
        if (starts[index].slice(0, 4) !== starts[previous].slice(0, 4)) return yearText(index);
        if (dayRung && starts[index].slice(0, 7) !== starts[previous].slice(0, 7)) return monthText(index);
        return shortText(index);
    };

    // Horizontal trial: every bucket labelled, the first visible one in its first form.
    const horizontalText = (index: number) => textOf(index, index > 0 ? index - 1 : undefined, index === vs);
    const visibleWidths: number[] = [];
    for (let index = vs; index <= ve; index++) visibleWidths.push(widthOf(horizontalText(index)));
    const shifts = new Map<number, number>();
    if (leftRoomPx !== undefined) {
        const need = -leftRoomPx + LADDER_EDGE_SAFETY_PX - (centre(vs) - visibleWidths[0] / 2);
        if (need > 0) shifts.set(vs, Math.ceil(need));
    }
    if (rightRoomPx !== undefined) {
        const over = centre(ve) + visibleWidths[visibleWidths.length - 1] / 2 - (plotWidthPx + rightRoomPx - LADDER_EDGE_SAFETY_PX);
        if (over > 0) shifts.set(ve, (shifts.get(ve) ?? 0) - Math.ceil(over));
    }
    if (shifts.get(ve) === 0) shifts.delete(ve);
    let fits = true;
    for (let index = vs + 1; index <= ve && fits; index++) {
        const rightEdge = centre(index - 1) + (shifts.get(index - 1) ?? 0) + visibleWidths[index - 1 - vs] / 2;
        const leftEdge = centre(index) + (shifts.get(index) ?? 0) - visibleWidths[index - vs] / 2;
        fits = leftEdge - rightEdge >= LADDER_LABEL_GAP_PX;
    }

    const labels = new Map<string, string>();
    let rotate: 0 | 45 = 0;
    let step = 1;
    let widestText = '';
    const considerWidest = (index: number, text: string) => {
        if (index >= vs && index <= ve && widthOf(text) > widthOf(widestText)) widestText = text;
    };
    if (fits) {
        for (let index = 0; index < n; index++) {
            const text = horizontalText(index);
            labels.set(closingDates[index], text);
            considerWidest(index, text);
        }
    } else {
        rotate = 45;
        shifts.clear();
        // WHY: `- 1e-9` keeps k at 1 when the slot is exactly one row across, where floating point would round up.
        step = Math.max(1, Math.ceil((fontSizePx * LADDER_LABEL_ROW_EM) / (slot * Math.SQRT1_2) - 1e-9));
        const candidates: number[] = [];
        for (let index = ve - ((step - ((n - 1 - ve) % step)) % step); index >= vs; index -= step) candidates.unshift(index);
        let firstKept = 0;
        let lastKept = candidates.length - 1;
        const halfLineAcross = (fontSizePx / 2) * Math.SQRT1_2;
        if (leftRoomPx !== undefined) {
            while (firstKept <= lastKept && leftRoomPx + centre(candidates[firstKept]) - widthOf(firstText(candidates[firstKept])) * Math.SQRT1_2 - halfLineAcross < LADDER_EDGE_SAFETY_PX) firstKept++;
        }
        if (rightRoomPx !== undefined) {
            while (lastKept >= firstKept && centre(candidates[lastKept]) + halfLineAcross > plotWidthPx + rightRoomPx - LADDER_EDGE_SAFETY_PX) lastKept--;
        }
        const dropped = new Set([...candidates.slice(0, firstKept), ...candidates.slice(lastKept + 1)]);
        const first = firstKept <= lastKept ? candidates[firstKept] : undefined;
        let previous: number | undefined;
        for (let index = (n - 1) % step; index < n; index += step) {
            if (dropped.has(index)) continue;
            const text = textOf(index, previous, index === first);
            labels.set(closingDates[index], text);
            considerWidest(index, text);
            previous = index;
        }
    }

    // Only painted labels size the box: a labelled bucket outside the window, or an unlabelled one, is never drawn.
    let labelBox: LadderAxisPlan['labelBox'] = null;
    if (rotate === 45 && measureLabelPx !== undefined) {
        const measured = new Map<string, number>();
        let widthPx = -Infinity;
        for (let index = vs; index <= ve; index++) {
            const text = labels.get(closingDates[index]);
            if (text === undefined) continue;
            let px = measured.get(text);
            if (px === undefined) {
                px = measureLabelPx(text);
                measured.set(text, px);
            }
            widthPx = Math.max(widthPx, px);
        }
        if (widthPx > -Infinity) labelBox = {widthPx, lineHeightPx: fontSizePx};
    }

    const separators = new Set<string>();
    const closingDays = closingDates.map(dayOf);
    const coveredStart = (index: number) => (index === 0 ? dayOf(firstDate) : closingDays[index - 1] + 1);
    const firsts = closingDays.map((day, index) => monthFirstsBetween(coveredStart(index), day));
    const sparse = slot < CANDLE_MIN_SLOT_PX;
    // WHY: ECharts draws a lone band tick on the axis start (fixOnBandTicksCoords), so one visible month edge would move there; the first visible bucket's edge is the plot edge, where a line is drawn anyway.
    let visibleMonthEdges = 0;
    for (let index = vs; index <= ve; index++) if (firsts[index].length > 0) visibleMonthEdges += 1;
    const anchorIndex = sparse && visibleMonthEdges === 1 && firsts[vs].length === 0 ? vs : -1;
    for (let index = 0; index < n; index++) {
        if (!sparse || firsts[index].length > 0 || index === anchorIndex) separators.add(closingDates[index]);
    }
    const edgeShifts = new Map<string, number>([...shifts].map(([index, px]): [string, number] => [closingDates[index], px]));
    const key = JSON.stringify([rotate, step, [...labels], [...separators], [...edgeShifts], widestText, labelBox]);
    return {rotate, step, labels, separators, edgeShifts, widestText, labelBox, key};
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
            // Always present: an `{xAxis}`-only update merges into the previous option, so an absent rotate would keep 45,
            // and an absent width or lineHeight the previous box. null clears them.
            rotate: plan.rotate,
            width: plan.labelBox?.widthPx ?? null,
            lineHeight: plan.labelBox?.lineHeightPx ?? null,
            interval: (_index, raw) => plan.labels.has(raw),
            formatter: (raw) => {
                const text = plan.labels.get(raw);
                if (text === undefined) return plan.widestText;
                const px = plan.edgeShifts.get(raw) ?? 0;
                return px === 0 ? text : `{${shiftStyleName(px)}|${text}}`;
            },
            rich,
        },
        splitLine: {interval: (_index, raw) => plan.separators.has(raw)},
    };
}
