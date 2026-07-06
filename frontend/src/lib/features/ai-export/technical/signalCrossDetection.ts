/**
 * Generic cross detection — detects when one series crosses above/below
 * another series or a numeric threshold.
 *
 * Works on any pair of time-aligned series. Handles null/NaN gracefully.
 */

// ─── Types ───────────────────────────────────────────────────────────────────

export interface TimeSeriesPoint {
    date: string;
    value: number | null;
}

export interface CrossDetectionOptions {
    /** Values within epsilon of zero are treated as zero (default: 0) */
    epsilon?: number;
    /** Minimum gap in days between reported crosses (default: 0) */
    minGapDays?: number;
    /** Only report crosses in this direction (default: 'both') */
    direction?: 'both' | 'above' | 'below';
    /** Label for series A (used in output) */
    labelA?: string;
    /** Label for series B or threshold (used in output) */
    labelB?: string;
}

export interface CrossEvent {
    date: string;
    event: 'CROSSED_ABOVE' | 'CROSSED_BELOW';
    seriesA: string;
    seriesB: string;
    previousDate: string;
    previousA: number;
    previousB: number;
    currentA: number;
    currentB: number;
    previousDelta: number;
    currentDelta: number;
}

// ─── Main Function ───────────────────────────────────────────────────────────

/**
 * Detects crosses between seriesA and seriesB (or a constant threshold).
 *
 * Rules:
 * - Ignores null/NaN points
 * - Requires two consecutive valid points to detect a cross
 * - Aligns series by date when comparing two series
 * - Applies epsilon tolerance: |delta| <= epsilon is treated as zero
 */
export function detectCrosses(seriesA: TimeSeriesPoint[], seriesBOrThreshold: TimeSeriesPoint[] | number, options: CrossDetectionOptions = {}): CrossEvent[] {
    const {epsilon = 0, minGapDays = 0, direction = 'both', labelA = 'A', labelB = 'B'} = options;

    const aligned = alignSeries(seriesA, seriesBOrThreshold);
    const events: CrossEvent[] = [];
    let lastCrossDate: string | null = null;

    for (let i = 1; i < aligned.length; i++) {
        const prev = aligned[i - 1];
        const curr = aligned[i];

        if (prev.a === null || prev.b === null || curr.a === null || curr.b === null) continue;

        const prevDelta = applyEpsilon(prev.a - prev.b, epsilon);
        const currDelta = applyEpsilon(curr.a - curr.b, epsilon);

        let event: 'CROSSED_ABOVE' | 'CROSSED_BELOW' | null = null;

        if (prevDelta <= 0 && currDelta > 0) {
            event = 'CROSSED_ABOVE';
        } else if (prevDelta >= 0 && currDelta < 0) {
            event = 'CROSSED_BELOW';
        }

        if (!event) continue;
        if (direction === 'above' && event !== 'CROSSED_ABOVE') continue;
        if (direction === 'below' && event !== 'CROSSED_BELOW') continue;

        if (lastCrossDate && minGapDays > 0) {
            const gap = daysBetween(lastCrossDate, curr.date);
            if (gap < minGapDays) continue;
        }

        events.push({
            date: curr.date,
            event,
            seriesA: labelA,
            seriesB: labelB,
            previousDate: prev.date,
            previousA: prev.a,
            previousB: prev.b,
            currentA: curr.a,
            currentB: curr.b,
            previousDelta: prev.a - prev.b,
            currentDelta: curr.a - curr.b,
        });

        lastCrossDate = curr.date;
    }

    return events;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

interface AlignedPoint {
    date: string;
    a: number | null;
    b: number | null;
}

function alignSeries(seriesA: TimeSeriesPoint[], seriesBOrThreshold: TimeSeriesPoint[] | number): AlignedPoint[] {
    if (typeof seriesBOrThreshold === 'number') {
        const threshold = seriesBOrThreshold;
        return seriesA.map((p) => ({
            date: p.date,
            a: isValid(p.value) ? p.value : null,
            b: threshold,
        }));
    }

    // Build date-indexed map for series B
    const bMap = new Map<string, number | null>();
    for (const p of seriesBOrThreshold) {
        bMap.set(p.date, isValid(p.value) ? p.value : null);
    }

    // Only include dates present in both series
    const result: AlignedPoint[] = [];
    for (const p of seriesA) {
        if (!bMap.has(p.date)) continue;
        result.push({
            date: p.date,
            a: isValid(p.value) ? p.value : null,
            b: bMap.get(p.date)!,
        });
    }

    return result;
}

function isValid(v: number | null): v is number {
    return v !== null && !Number.isNaN(v);
}

function applyEpsilon(delta: number, epsilon: number): number {
    return Math.abs(delta) <= epsilon ? 0 : delta;
}

function daysBetween(dateA: string, dateB: string): number {
    const a = new Date(dateA).getTime();
    const b = new Date(dateB).getTime();
    return Math.abs(b - a) / 86_400_000;
}
