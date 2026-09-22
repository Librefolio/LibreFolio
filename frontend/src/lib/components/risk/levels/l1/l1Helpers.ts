/**
 * Pure logic for L1 — "how much can it hurt?".
 *
 * Split out of `levelHelpers.ts` rather than added to it, for two reasons that
 * were both measured rather than preferred:
 *
 * - `levelHelpers.ts` stood at **507 lines against a 600 ceiling** before this
 *   mandate started. L1's three new readings would have taken it past the line,
 *   and the ceiling exists precisely to stop the four levels from collapsing
 *   back into the monolith they were extracted from.
 * - `levelHelpers.ts` is a **shared surface**: S2…S5 send their changes through
 *   its single writer. Every function that does not need to sit in the contended
 *   file is one less reason for two mandates to touch the same lines.
 *
 * The dependency runs one way — this file reads `levelHelpers`, never the
 * reverse — so the split adds no cycle.
 *
 * Everything here is a plain function over plain data: no runes, no stores, no
 * components, so all of it is assertable without mounting anything.
 */
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {DAILY_VAR_INSTANCE, resultByCode, resultByInstance} from '../../riskAnalysisHelpers';
import {finite, lossMagnitude, okOutput, record} from '../levelHelpers';

/* ---------------------------------------------------------- underwater --- */

/**
 * One point of the underwater curve, **already in percent units**.
 *
 * ⚠️ The scaling is not cosmetic and it is not the chart's job. `LineChart`'s
 * `viewMode='percentage'` does **not** convert anything: it moves the baseline
 * to zero, formats the axis as `` `${v.toFixed(1)}%` `` and suffixes the tooltip
 * (`LineChart.svelte:378`, `:636`, `:714`), while the series still plots
 * `d.value` verbatim (`:373`). Handing it the decimal ratio the API returns
 * would draw a curve of exactly the right *shape* labelled with numbers a
 * hundred times too small — the failure no visual check can catch.
 *
 * Shape-compatible with `LineDataPoint` on purpose, so it can be passed straight
 * through without a second mapping at the call site.
 */
export interface UnderwaterPoint {
    date: string;
    /** Peak-relative loss in percent, never positive. */
    value: number;
}

/**
 * The underwater curve: how far below its last peak the portfolio sat, day by day.
 *
 * Each point arrives **already dated** from the backend (`RiskDrawdownPoint`),
 * which is what makes this drawable at all: the series is shorter than the
 * window it spans, because only trading days appear, so spreading the points
 * evenly across the period would misplace every interior one.
 *
 * Points that contradict the field's declared `le=0` convention are dropped
 * rather than rescued with `Math.abs`, for the reason `lossMagnitude` documents:
 * a rescued point is indistinguishable from a measured one.
 */
export function buildUnderwater(historicalResults: RiskAnalyticResult[]): UnderwaterPoint[] {
    const output = okOutput(resultByCode(historicalResults, 'drawdown_summary'));
    if (!output) return [];

    const raw = output.underwater_series;
    if (!Array.isArray(raw)) return [];

    const points: UnderwaterPoint[] = [];
    for (const entry of raw) {
        const point = record(entry);
        const date = typeof point.date === 'string' ? point.date : null;
        const depth = lossMagnitude(point.drawdown, 'negative');
        if (date === null || depth === null) continue;
        // A day exactly at the peak is a plain zero: `-0` would print as "−0.0%".
        points.push({date, value: depth === 0 ? 0 : -(depth * 100)});
    }
    return points;
}

/* ----------------------------------------------------------- histogram --- */

/** One bar of the return distribution, in percent units. */
export interface ReturnBin {
    /** Inclusive lower edge, in percent. */
    lowerBound: number;
    /** Exclusive upper edge, in percent. */
    upperBound: number;
    /** Observations that fell in this bin. */
    count: number;
    /** Height relative to the tallest bar, in `0…1`. */
    share: number;
    /** Whether the VaR cut falls inside this bar. At most one bar has it. */
    holdsCut: boolean;
    /**
     * Whether the whole bar lies at or beyond the cut — the tail the VaR describes.
     *
     * This is what makes the threshold mean something: a highlighted bar says
     * "here is the number", the shaded run to its left says "here is the mass it
     * is talking about". The bar *holding* the cut is straddling it and so is
     * deliberately excluded from both.
     */
    belowCut: boolean;
}

/** The distribution of realised returns, with the VaR threshold located in it. */
export interface ReturnHistogram {
    bins: ReturnBin[];
    /** Total observations across the bins. */
    observations: number;
    /**
     * The VaR cut in percent units, or `null` when the backend published none.
     *
     * ⚠️ Read with `=== null`, **never** `?? 0` or a falsy test: a cut of exactly
     * zero is a legitimate answer — the threshold sits at break-even — and a
     * falsy check would erase it precisely on the portfolio where it is most
     * interesting.
     */
    cut: number | null;
}

/**
 * Build the return distribution from the daily VaR result.
 *
 * The cut is located by **inequality on a half-open interval**,
 * `lower <= edge < upper`, never by an equality against a float. `var_bin_edge`
 * is a *value* expressed in the same space as the bounds, not an index, so an
 * equality test would be at the mercy of the last bit of a division.
 *
 * ⚠️ Bar widths come from `upper − lower` rather than from a constant, and that
 * is deliberate. `validate_return_bins` (`schemas/risk.py:959`) polices only that
 * `lower_bound` ascends — **not** contiguity, and **not** that the counts sum to
 * the observation total. The current producer happens to emit a uniform grid
 * (`historical_var.py:90` slices one edge array), but that is the producer's
 * contract and not the schema's, and drawing from the real widths costs nothing
 * while surviving a grid that stops being uniform.
 */
export function buildReturnHistogram(historicalResults: RiskAnalyticResult[], instanceId: string = DAILY_VAR_INSTANCE): ReturnHistogram | null {
    const output = okOutput(resultByInstance(historicalResults, instanceId));
    if (!output) return null;

    const raw = output.return_bins;
    if (!Array.isArray(raw) || raw.length === 0) return null;

    // `finite` already answers null for an absent, null or non-numeric edge, and
    // it answers 0 for a real zero. That distinction is the whole point.
    const edge = finite(output.var_bin_edge);

    const parsed: {lower: number; upper: number; count: number}[] = [];
    let observations = 0;
    let tallest = 0;
    for (const entry of raw) {
        const bin = record(entry);
        const lower = finite(bin.lower_bound);
        const upper = finite(bin.upper_bound);
        const count = finite(bin.count);
        if (lower === null || upper === null || count === null) continue;
        // A bin with no width cannot contain an observation, and would make the
        // half-open cut test unsatisfiable for every edge.
        if (upper <= lower || count < 0) continue;
        parsed.push({lower, upper, count});
        observations += count;
        if (count > tallest) tallest = count;
    }
    if (parsed.length === 0) return null;

    const bins = parsed.map(({lower, upper, count}) => ({
        lowerBound: lower * 100,
        upperBound: upper * 100,
        count,
        // A histogram of all-empty bins would divide by zero; it stays flat instead.
        share: tallest > 0 ? count / tallest : 0,
        // Compared in the API's own space, before the display scaling, so the
        // comparison never inherits the rounding of a multiplication.
        holdsCut: edge !== null && lower <= edge && edge < upper,
        belowCut: edge !== null && upper <= edge,
    }));

    return {bins, observations, cut: edge === null ? null : edge * 100};
}

/* --------------------------------------------------------------- tails --- */

/**
 * The four measures that had no home, read from the KPI output.
 *
 * Every one is `Optional` on the wire, and one of them is optional **by
 * decision** rather than by accident — see {@link TailMeasures.worstRealization}.
 */
export interface TailMeasures {
    /**
     * The worst single day the window actually contained, as a positive magnitude.
     *
     * ⚠️ `null` here is a **refusal, not a gap**. When every day in the window
     * gained, the producer sets the field to `None` on purpose
     * (`historical_kpi.py:126-137`): *"reporting zero here would claim a loss
     * that never happened while pointing at a profitable date."* Substituting a
     * zero downstream would reinstate exactly the number the producer declined
     * to publish, and hand it the authority of a measurement.
     */
    worstRealization: number | null;
    /** The day it happened. Travels with the value: both are cleared together. */
    worstRealizationDate: string | null;
    /** Drawdown at risk, as a positive magnitude. */
    drawdownAtRisk: number | null;
    /** Conditional drawdown at risk — the mean beyond the cut, so never shallower than DaR. */
    conditionalDrawdownAtRisk: number | null;
    /**
     * The confidence the backend actually used, as a fraction in `(0,1)`.
     *
     * ⚠️ Read, never assumed. `drawdown_confidence_level` is a **parameter**
     * (`historical_kpi.py:59`) that the backend publishes on its output, so a
     * hardcoded "95%" in a caption is a sentence that turns false silently the
     * day the parameter moves.
     */
    drawdownConfidence: number | null;
    /**
     * Ulcer index — the root-mean-square depth of the underwater curve.
     *
     * A **dispersion, not a loss**: the schema constrains it `ge=0` where the
     * three above are `le=0`, and the comment there states the convention
     * outright. It is read with `finite`, not `lossMagnitude`, because there is
     * no sign to interpret.
     */
    ulcerIndex: number | null;
}

/** Read the four acquired measures, honouring each field's declared sign. */
export function buildTailMeasures(historicalResults: RiskAnalyticResult[]): TailMeasures {
    const kpi = okOutput(resultByCode(historicalResults, 'historical_kpi'));
    if (!kpi) {
        return {
            worstRealization: null,
            worstRealizationDate: null,
            drawdownAtRisk: null,
            conditionalDrawdownAtRisk: null,
            drawdownConfidence: null,
            ulcerIndex: null,
        };
    }

    const worst = lossMagnitude(kpi.worst_realization, 'negative');
    const worstDate = kpi.worst_realization_date;
    return {
        worstRealization: worst,
        // The date is only meaningful alongside a value; a lone date would point
        // at a day whose loss we just declined to state.
        worstRealizationDate: worst !== null && typeof worstDate === 'string' ? worstDate : null,
        drawdownAtRisk: lossMagnitude(kpi.drawdown_at_risk, 'negative'),
        conditionalDrawdownAtRisk: lossMagnitude(kpi.conditional_drawdown_at_risk, 'negative'),
        drawdownConfidence: finite(kpi.drawdown_confidence_level),
        ulcerIndex: finite(kpi.ulcer_index),
    };
}
