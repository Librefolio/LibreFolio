/**
 * @vitest-environment node
 *
 * assetSetLevels — pure unit tests (node env: no DOM, no network, no timers).
 *
 * ⚠️ WHERE THESE NUMBERS COME FROM. Every figure below was **invented while
 * writing this file**. Nothing here was read off a running backend, and nothing
 * here may be described as measured — in a comment, in a commit message or in a
 * report. What makes a fixture trustworthy is not its provenance but its
 * *emittability*: each payload satisfies the contract in
 * `backend/app/schemas/risk.py` that would have produced it, so a reader can
 * check it against the model rather than against someone's memory of a run.
 *
 * The contracts that are load-bearing here, and are honoured deliberately:
 *
 *  - `RiskAssetSetVarCvarItem` — both tails are `ge=0`, and a `model_validator`
 *    demands `conditional_value_at_risk >= value_at_risk`.
 *  - `RiskAssetSetDrawdownItem` — the episode contract: `no_drawdown` carries a
 *    zero maximum, no episode dates and no recovered ratio; a real episode
 *    carries a negative maximum, peak and trough dates in order, and a
 *    recovered ratio; only a `recovered` episode may carry a recovery date.
 *  - `RiskAssetSetComparisonOutput` — the reference is never one of the items
 *    it is the yardstick for. It may be one of the *selection* (D371,
 *    `asset_set_comparison` 1.1.0): the backend then measures it like the
 *    others and skips it in `items`, and a selection made of the reference
 *    alone answers with `items == []`.
 *  - `RiskAnalyticResult` — `ok` and `partial` *must* carry an output;
 *    `unavailable` and `failed` must *not*, and must carry an error instead.
 *    That is why no fixture here fakes an unavailable result holding a payload:
 *    the shape does not exist, so a test built on it would prove nothing.
 *
 * `metadata` and `data_quality` are omitted from the row builders' fixtures even
 * though the same model requires them. The row builders read neither, so
 * writing two more payloads there would add fixture surface to maintain and not
 * one assertion. A stated shortcut, not an oversight. The one reader of
 * `metadata` is `assetSetCalculationWindow`, and its fixtures carry a complete
 * one (`windowMetadata`), proved to parse with `schemas.RiskResultMetadata` —
 * the schema `riskMetadata()` refuses anything less than.
 *
 * Where arithmetic links two invented figures, it is made exact so the reader
 * can verify the fixture instead of trusting it: a 40% fall that has given back
 * half of itself leaves the asset 20% down (`recovered_ratio` 0.5), and 20%
 * down needs a 25% rise to get back to the peak (`remaining_to_peak_ratio`
 * 0.25 = 0.2 / 0.8).
 */
import {describe, expect, it} from 'vitest';

import {schemas} from '$lib/api';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {ASSET_SET_DAILY_VAR_INSTANCE, ASSET_SET_MONTHLY_VAR_INSTANCE} from './riskAnalysisHelpers';
import {assetSetCalculationWindow, buildAssetSetBenchmarkPoint, buildAssetSetChartPoints, buildAssetSetHurtRows, buildAssetSetPaidRows, buildAssetSetScatterPoints, calendarLength, type AssetSetBenchmarkPoint, type AssetSetPaidRow, type CalendarLength} from './assetSetLevels';

type Payload = Record<string, unknown>;

/**
 * The selection under test: three assets, deliberately neither sorted nor
 * contiguous, so "selection order" is observable and cannot be confused with
 * "ascending id" or "whatever the payload listed first".
 */
const SELECTION = [7, 3, 12];

/**
 * The shared reference, outside `SELECTION`. Since D371 the reader may select it
 * too — the cases that do say so — but it is never one of the comparison's
 * `items`: the model forbids that.
 */
const BENCHMARK_ID = 41;

/** The label map the sections build from the asset store. */
function labels(entries: Record<number, string>): ReadonlyMap<number, string> {
    return new Map<number, string>(Object.entries(entries).map(([id, name]): [number, string] => [Number(id), name]));
}

const LABELS = labels({3: 'iShares Core MSCI EM IMI', 7: 'Vanguard FTSE All-World', 12: 'Xtrackers EUR Corporate Bond', 41: 'MSCI ACWI'});

/** A successful result carrying an output, shaped like the API's. */
function ok(analyticCode: string, output: Payload | Payload[] | null, instanceId = `base-historical-${analyticCode}`): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'ok', output} as unknown as RiskAnalyticResult;
}

/**
 * A degraded result, which still carries its output.
 *
 * `partial` is not an exotic case for this family: `service.py` sets it when an
 * analytic excluded assets, which is precisely the situation where the items
 * cover fewer assets than were selected. The subset payloads below are what a
 * partial answer actually looks like.
 */
function partial(analyticCode: string, output: Payload, instanceId = `base-historical-${analyticCode}`): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'partial', output} as unknown as RiskAnalyticResult;
}

/** A result the backend could not compute: an error, and no output at all. */
function unavailable(analyticCode: string, instanceId = `base-historical-${analyticCode}`): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'unavailable', output: null, error: {code: 'insufficient_history', message: 'invented: fewer observations than the analytic requires'}} as unknown as RiskAnalyticResult;
}

function varItem(assetId: number, valueAtRisk: number, conditionalValueAtRisk: number): Payload {
    return {asset_id: assetId, value_at_risk: valueAtRisk, conditional_value_at_risk: conditionalValueAtRisk};
}

/** The one-day tail. 502 daily observations over the window below. */
function dailyVar(items: Payload[], overrides: Payload = {}): RiskAnalyticResult {
    return ok('asset_set_var', {kind: 'var_cvar_set', confidence_level: 0.95, horizon_days: 1, horizon_observations: 1, observations: 502, items, ...overrides}, ASSET_SET_DAILY_VAR_INSTANCE);
}

/**
 * The ~1-month tail: same analytic code, different instance.
 *
 * `observations` is 20 lower than the daily run's and that is not decoration —
 * the output's own docstring says compounding to a horizon consumes
 * `horizon_observations - 1` observations, and a 30-day month is 21
 * observations, so 502 − 20 = 482.
 */
function monthlyVar(items: Payload[]): RiskAnalyticResult {
    return ok('asset_set_var', {kind: 'var_cvar_set', confidence_level: 0.95, horizon_days: 30, horizon_observations: 21, observations: 482, items}, ASSET_SET_MONTHLY_VAR_INSTANCE);
}

/**
 * An episode still open: fell 40%, has given half of it back, is 20% down today
 * and needs a 25% rise to see its peak again. Peak and trough are in order; no
 * recovery date, because the contract forbids one on an open episode. The
 * duration of an open episode runs peak → end of window (725 days from
 * 2023-02-06 to 2025-01-31), which is also the current drawdown's duration
 * because the episode's peak is still the running high.
 */
function openFall(assetId: number): Payload {
    return {
        asset_id: assetId,
        current_drawdown: -0.2,
        current_peak_date: '2023-02-06',
        current_drawdown_duration_days: 725,
        maximum_drawdown: -0.4,
        maximum_drawdown_peak_date: '2023-02-06',
        maximum_drawdown_trough_date: '2023-10-27',
        maximum_drawdown_recovery_status: 'open',
        maximum_drawdown_duration_days: 725,
        maximum_drawdown_recovered_ratio: 0.5,
        remaining_to_peak_ratio: 0.25,
    };
}

/**
 * An episode closed: fell 18%, back to the peak on 2024-05-15 and at a new high
 * since, so the *current* drawdown is zero and its peak date is the last day of
 * the window. A recovered episode's duration runs peak → recovery: 288 days.
 */
function recoveredFall(assetId: number): Payload {
    return {
        asset_id: assetId,
        current_drawdown: 0,
        current_peak_date: '2025-01-31',
        current_drawdown_duration_days: 0,
        maximum_drawdown: -0.18,
        maximum_drawdown_peak_date: '2023-08-01',
        maximum_drawdown_trough_date: '2023-10-27',
        maximum_drawdown_recovery_status: 'recovered',
        maximum_drawdown_recovery_date: '2024-05-15',
        maximum_drawdown_duration_days: 288,
        maximum_drawdown_recovered_ratio: 1,
        remaining_to_peak_ratio: 0,
    };
}

/**
 * An asset that never fell: every drawdown figure is a real, measured zero.
 *
 * This is the payload that makes "absent" and "zero" impossible to conflate,
 * and the contract is strict about it — `no_drawdown` may carry no episode
 * dates and no recovered ratio at all.
 */
function neverFell(assetId: number): Payload {
    return {
        asset_id: assetId,
        current_drawdown: 0,
        current_peak_date: '2025-01-31',
        current_drawdown_duration_days: 0,
        maximum_drawdown: 0,
        maximum_drawdown_recovery_status: 'no_drawdown',
        maximum_drawdown_duration_days: 0,
        remaining_to_peak_ratio: 0,
    };
}

function drawdownResult(items: Payload[], overrides: Payload = {}): RiskAnalyticResult {
    return ok('asset_set_drawdown', {kind: 'drawdown_set', available_start: '2023-01-02', available_end: '2025-01-31', calculation_basis: 'price_only_close', return_basis: 'price_only', items, ...overrides});
}

/**
 * A KPI row. `max_drawdown` and its duration agree with the drawdown analytic's
 * figures for the same asset, because both are measured on the same joint
 * calendar — a fixture where they disagreed would describe two different runs.
 */
function kpiItem(assetId: number, overrides: Payload = {}): Payload {
    return {asset_id: assetId, volatility: 0.19, max_drawdown: -0.18, max_drawdown_duration_days: 288, sharpe: 0.62, sortino: 0.81, ...overrides};
}

function kpiResult(items: Payload[]): RiskAnalyticResult {
    return ok('asset_set_kpi', {kind: 'kpi_set', drawdown_confidence_level: 0.95, items});
}

function returnItem(assetId: number, volatility: number, expectedAnnualReturn: number): Payload {
    return {asset_id: assetId, volatility, expected_annual_return: expectedAnnualReturn};
}

function returnResult(items: Payload[]): RiskAnalyticResult {
    return ok('asset_set_risk_return', {kind: 'risk_return_set', items});
}

/** `information_ratio` is `active_return / tracking_error`, exactly, in both rows below. */
function comparisonItem(assetId: number, overrides: Payload = {}): Payload {
    return {asset_id: assetId, active_return: 0.013, tracking_error: 0.052, information_ratio: 0.25, correlation: 0.94, beta: 1.07, ...overrides};
}

function comparisonResult(items: Payload[], overrides: Payload = {}): RiskAnalyticResult {
    return ok('asset_set_comparison', {kind: 'comparison_set', comparison_asset_id: BENCHMARK_ID, observations: 502, comparison_volatility: 0.142, comparison_expected_annual_return: 0.081, items, ...overrides});
}

/**
 * The row this assertion is about, found by identity.
 *
 * The throw is the point: if the "a selected asset always gets a row" rule ever
 * breaks, every test written this way fails saying so, instead of failing later
 * on a comparison against `undefined`.
 */
function rowFor<T extends {assetId: number}>(rows: readonly T[], assetId: number): T {
    const found = rows.find((row) => row.assetId === assetId);
    if (!found) throw new Error(`no row for asset ${assetId}: the selection is supposed to guarantee one`);
    return found;
}

/** A row with both coordinates, for the cases a payload would only obscure. Not the reference unless a case says so. */
function paidRow(overrides: Partial<AssetSetPaidRow> = {}): AssetSetPaidRow {
    return {assetId: 7, name: 'Vanguard FTSE All-World', volatility: 0.21, expectedReturn: 0.094, sharpe: 0.62, sortino: 0.81, beta: null, correlation: null, isReference: false, ...overrides};
}

/** Whether a result's output satisfies the generated comparison schema — the parse every reader of it goes through. */
function parsesAsComparison(result: RiskAnalyticResult | null): boolean {
    return schemas.RiskAssetSetComparisonOutput.safeParse(result?.output).success;
}

describe('buildAssetSetHurtRows', () => {
    it('gives every selected asset a row in selection order, even when the analytics answered for fewer', () => {
        // A partial answer covering two of the three assets, and a drawdown
        // covering only the third: between them no single asset is described by
        // both, which is what makes the join visible.
        const rows = buildAssetSetHurtRows(
            SELECTION,
            LABELS,
            partial('asset_set_var', {kind: 'var_cvar_set', confidence_level: 0.95, horizon_days: 1, horizon_observations: 1, observations: 502, items: [varItem(7, 0.021, 0.031), varItem(12, 0.009, 0.013)]}, ASSET_SET_DAILY_VAR_INSTANCE),
            null,
            drawdownResult([openFall(3)]),
        );

        expect(rows.map((row) => row.assetId)).toEqual([7, 3, 12]);
        expect(rowFor(rows, 7).badDay).toBe(0.031);
        expect(rowFor(rows, 3).worstFall).toBe(-0.4);
        expect(rowFor(rows, 12).badDay).toBe(0.013);
    });

    it('leaves an unanswered asset with null cells and never with zeros', () => {
        // 🔴 The rule the level exists to enforce. Every analytic answers for
        // asset 7 only; assets 3 and 12 were still chosen by the reader, so they
        // keep their rows and say nothing rather than saying "no loss".
        const rows = buildAssetSetHurtRows(SELECTION, LABELS, dailyVar([varItem(7, 0.021, 0.031)]), monthlyVar([varItem(7, 0.087, 0.124)]), drawdownResult([recoveredFall(7)]));

        expect(rows).toHaveLength(3);
        expect(rowFor(rows, 3)).toEqual({
            assetId: 3,
            name: 'iShares Core MSCI EM IMI',
            badDay: null,
            badMonth: null,
            worstFall: null,
            worstFallDays: null,
            recovery: null,
            currentFall: null,
            toPeak: null,
        });
        // And the fixture is not vacuously empty: the asset that *was* measured
        // carries its figures, so the nulls above mean absence and not silence.
        expect(rowFor(rows, 7).badMonth).toBe(0.124);
    });

    it('keeps a measured zero as zero, so "never fell" and "never measured" stay different readings', () => {
        // Asset 12 is at its all-time high and its worst 5% of days averaged no
        // loss at all: every figure it publishes is a real zero. Asset 3 was not
        // measured. A helper that zero-filled absences would make these two rows
        // identical, and the reader would have no way to tell them apart.
        const rows = buildAssetSetHurtRows(SELECTION, LABELS, dailyVar([varItem(12, 0, 0)]), null, drawdownResult([neverFell(12)]));
        const measured = rowFor(rows, 12);

        // `toBe` compares with Object.is, so a -0 arriving here fails — which is
        // the intent: -0 reaches a percent formatter as "−0.0%".
        expect(measured.badDay).toBe(0);
        expect(measured.worstFall).toBe(0);
        expect(measured.worstFallDays).toBe(0);
        expect(measured.currentFall).toBe(0);
        expect(measured.toPeak).toBe(0);
        expect(measured.recovery).toBe('no_drawdown');

        const unmeasured = rowFor(rows, 3);
        expect(unmeasured.badDay).toBeNull();
        expect(unmeasured.worstFall).toBeNull();
        expect(unmeasured.worstFallDays).toBeNull();
    });

    it('preserves each contract sign: the VaR pair positive, the drawdown pair negative', () => {
        // The two payloads disagree on sign by design (`ge=0` against `le=0`) and
        // the helper deliberately does not normalise. Both are drawn as a fall,
        // so a "tidy-up" that flipped one would be invisible on screen — which is
        // exactly why the values are pinned here and not at the formatter.
        const rows = buildAssetSetHurtRows([7], LABELS, dailyVar([varItem(7, 0.021, 0.031)]), monthlyVar([varItem(7, 0.087, 0.124)]), drawdownResult([openFall(7)]));
        const row = rowFor(rows, 7);

        expect(row.badDay).toBe(0.031);
        expect(row.badMonth).toBe(0.124);
        expect(row.badDay).toBeGreaterThan(0);
        expect(row.badMonth).toBeGreaterThan(0);

        expect(row.worstFall).toBe(-0.4);
        expect(row.currentFall).toBe(-0.2);
        expect(row.worstFall).toBeLessThan(0);
        expect(row.currentFall).toBeLessThan(0);

        // The rise still owed is a rise, on the same row as two falls.
        expect(row.toPeak).toBe(0.25);
    });

    it('reads each horizon from its own instance, because the two share an analytic code', () => {
        // Both results answer to `asset_set_var`; only the instance id tells them
        // apart. A refactor to a by-code lookup would return whichever arrived
        // first and print one day's loss in the month column, or the reverse.
        const daily = dailyVar([varItem(7, 0.021, 0.031)]);
        const monthly = monthlyVar([varItem(7, 0.087, 0.124)]);
        expect(daily.analytic_code).toBe(monthly.analytic_code);

        const row = rowFor(buildAssetSetHurtRows([7], LABELS, daily, monthly, null), 7);
        expect(row.badDay).toBe(0.031);
        expect(row.badMonth).toBe(0.124);

        // Handed the same two answers the other way round, the columns swap:
        // nothing in the payload pins a figure to a column, the caller does.
        const swapped = rowFor(buildAssetSetHurtRows([7], LABELS, monthly, daily, null), 7);
        expect(swapped.badDay).toBe(0.124);
    });

    it('passes the recovery status through as the backend token, not as anything readable', () => {
        // The row carries the enum value; turning it into a sentence is the
        // renderer's job, in whichever of the four languages is on screen.
        const rows = buildAssetSetHurtRows(SELECTION, LABELS, null, null, drawdownResult([openFall(3), recoveredFall(7), neverFell(12)]));

        expect(rows.map((row) => row.recovery)).toEqual(['recovered', 'open', 'no_drawdown']);
    });

    it('names an asset the label map does not carry as #id, never as a blank', () => {
        const rows = buildAssetSetHurtRows(SELECTION, labels({7: 'Vanguard FTSE All-World'}), null, null, null);

        expect(rows.map((row) => row.name)).toEqual(['Vanguard FTSE All-World', '#3', '#12']);
    });

    it('keeps every row and empties every cell when no analytic ran', () => {
        const rows = buildAssetSetHurtRows(SELECTION, LABELS, unavailable('asset_set_var', ASSET_SET_DAILY_VAR_INSTANCE), unavailable('asset_set_var', ASSET_SET_MONTHLY_VAR_INSTANCE), unavailable('asset_set_drawdown'));

        expect(rows.map((row) => row.assetId)).toEqual([7, 3, 12]);
        expect(rows.every((row) => row.badDay === null && row.badMonth === null && row.worstFall === null && row.recovery === null)).toBe(true);
        // And identically when the caller holds no result at all to pass.
        expect(buildAssetSetHurtRows(SELECTION, LABELS, null, null, null).map((row) => row.badDay)).toEqual([null, null, null]);
    });

    it('discards a payload that breaks its own contract instead of half-reading it', () => {
        // `confidence_level` is required, so this object is not a VaR answer at
        // all — the zod parse rejects it and the level renders empty cells. What
        // it must not do is throw on the way, or read `items` anyway.
        const malformed = ok('asset_set_var', {kind: 'var_cvar_set', horizon_days: 1, observations: 502, items: [varItem(7, 0.021, 0.031)]}, ASSET_SET_DAILY_VAR_INSTANCE);

        expect(() => buildAssetSetHurtRows(SELECTION, LABELS, malformed, null, null)).not.toThrow();
        expect(rowFor(buildAssetSetHurtRows(SELECTION, LABELS, malformed, null, null), 7).badDay).toBeNull();
    });

    it('reads a degraded answer, because a partial result is still an answer', () => {
        // The helper never inspects `status`, and by contract it does not need
        // to: `unavailable` and `failed` may not carry an output at all. What is
        // pinned here is the consequence — a `partial` result *does* carry one
        // and is read, which is the same rule `RiskResultFrame` renders by.
        const rows = buildAssetSetHurtRows([7], LABELS, null, null, partial('asset_set_drawdown', {kind: 'drawdown_set', available_start: '2023-01-02', available_end: '2025-01-31', calculation_basis: 'price_only_close', return_basis: 'price_only', items: [openFall(7)]}));

        expect(rowFor(rows, 7).worstFall).toBe(-0.4);
    });

    it('has no rows when nothing is selected, however much the analytics answered', () => {
        expect(buildAssetSetHurtRows([], LABELS, dailyVar([varItem(7, 0.021, 0.031)]), null, drawdownResult([openFall(3)]))).toEqual([]);
    });
});

describe('buildAssetSetPaidRows', () => {
    it('gives every selected asset a row, with null cells for the ones nobody measured', () => {
        // 🔴 The same rule as L1°, enforced on a different set of analytics.
        const rows = buildAssetSetPaidRows(SELECTION, LABELS, returnResult([returnItem(7, 0.21, 0.094)]), kpiResult([kpiItem(7)]), comparisonResult([comparisonItem(7)]));

        expect(rows.map((row) => row.assetId)).toEqual([7, 3, 12]);
        expect(rowFor(rows, 12)).toEqual({
            assetId: 12,
            name: 'Xtrackers EUR Corporate Bond',
            volatility: null,
            expectedReturn: null,
            sharpe: null,
            sortino: null,
            beta: null,
            correlation: null,
            isReference: false,
        });
        expect(rowFor(rows, 7).sharpe).toBe(0.62);
    });

    it('prefers the scatter point volatility and falls back to the KPI figure', () => {
        // The two analytics measure volatility over the same joint calendar, so
        // in production they agree. They are made to disagree here — 0.21 against
        // 0.19 for asset 7 — because agreement cannot show which one was read.
        const rows = buildAssetSetPaidRows(SELECTION, LABELS, returnResult([returnItem(7, 0.21, 0.094), returnItem(12, 0.058, -0.012)]), kpiResult([kpiItem(7), kpiItem(3, {volatility: 0.34, max_drawdown: -0.4, max_drawdown_duration_days: 725, sharpe: -0.15, sortino: -0.21})]), null);

        expect(rowFor(rows, 7).volatility).toBe(0.21);
        expect(rowFor(rows, 3).volatility).toBe(0.34);
        expect(rowFor(rows, 12).volatility).toBe(0.058);

        // The fallback buys a volatility and nothing else: the KPI payload has no
        // expected return, so asset 3 ends with half a coordinate pair and the
        // scatter below will refuse to place it.
        expect(rowFor(rows, 3).expectedReturn).toBeNull();
        expect(rowFor(rows, 7).expectedReturn).toBe(0.094);
    });

    it('leaves beta and correlation null on every row when no benchmark applies', () => {
        // Which columns to draw is the renderer's decision — it has the benchmark
        // to decide with — so the helper answers null rather than dropping fields.
        const rows = buildAssetSetPaidRows(SELECTION, LABELS, returnResult([returnItem(7, 0.21, 0.094)]), kpiResult([kpiItem(7)]), null);

        expect(rows.every((row) => row.beta === null && row.correlation === null)).toBe(true);
        expect(rowFor(rows, 7).volatility).toBe(0.21);
    });

    it('reads beta and correlation per asset, and never off the wrong row', () => {
        const rows = buildAssetSetPaidRows(SELECTION, LABELS, null, null, comparisonResult([comparisonItem(7), comparisonItem(3, {active_return: -0.041, tracking_error: 0.164, information_ratio: -0.25, correlation: 0.61, beta: 1.28})]));

        expect(rowFor(rows, 7).beta).toBe(1.07);
        expect(rowFor(rows, 7).correlation).toBe(0.94);
        expect(rowFor(rows, 3).beta).toBe(1.28);
        expect(rowFor(rows, 3).correlation).toBe(0.61);
        expect(rowFor(rows, 12).beta).toBeNull();
    });

    it('keeps a ratio of exactly zero and reports an omitted one as null', () => {
        // Sharpe 0 says the asset paid precisely the risk-free rate for its risk,
        // which is a reading. Sortino absent says the producer would not publish
        // one — the contract makes both optional, and the difference is the
        // difference between a fact and a silence.
        const rows = buildAssetSetPaidRows([7, 3], LABELS, null, kpiResult([kpiItem(7, {sharpe: 0, sortino: null}), kpiItem(3, {volatility: 0.34, sharpe: -0.15})]), null);

        expect(rowFor(rows, 7).sharpe).toBe(0);
        expect(rowFor(rows, 7).sortino).toBeNull();
        // A negative ratio is ordinary, and must not be mistaken for a missing one.
        expect(rowFor(rows, 3).sharpe).toBe(-0.15);
        // `kpiItem` publishes a sortino by default; omitting it in the override
        // above is what makes asset 7's null meaningful rather than incidental.
        expect(rowFor(rows, 3).sortino).toBe(0.81);
    });

    it('keeps every row and empties every cell when no analytic ran', () => {
        const rows = buildAssetSetPaidRows(SELECTION, LABELS, unavailable('asset_set_risk_return'), unavailable('asset_set_kpi'), unavailable('asset_set_comparison'));

        expect(rows.map((row) => row.assetId)).toEqual([7, 3, 12]);
        expect(rows.every((row) => row.volatility === null && row.expectedReturn === null && row.sharpe === null && row.beta === null)).toBe(true);
    });

    /**
     * `isReference` (D371): the reference may be one of the selection. Its row is measured like any
     * other, but the backend skips it in the comparison's `items` — its beta and correlation with itself
     * would be 1 by construction — so those two stay null, and the flag says why. Read from the *parsed*
     * output's `comparison_asset_id`: a payload the schema refuses names no reference, whatever its raw
     * fields say.
     */
    const REFERENCE_CASES: {case: string; selection: number[]; comparison: RiskAnalyticResult | null; parses: boolean; reference: number | null}[] = [
        {case: 'the reference selected first', selection: SELECTION, comparison: comparisonResult([comparisonItem(3), comparisonItem(12)], {comparison_asset_id: 7}), parses: true, reference: 7},
        {case: 'the reference selected mid-list', selection: SELECTION, comparison: comparisonResult([comparisonItem(7), comparisonItem(12)], {comparison_asset_id: 3}), parses: true, reference: 3},
        {case: 'the reference selected last', selection: SELECTION, comparison: comparisonResult([comparisonItem(7), comparisonItem(3)], {comparison_asset_id: 12}), parses: true, reference: 12},
        // What the backend answers for it: not one item, the reference's own coordinates beside them.
        {case: 'the reference selected alone', selection: [3], comparison: comparisonResult([], {comparison_asset_id: 3}), parses: true, reference: 3},
        {case: 'the reference outside the selection', selection: SELECTION, comparison: comparisonResult([comparisonItem(7), comparisonItem(3), comparisonItem(12)]), parses: true, reference: null},
        {case: 'no comparison asked for', selection: SELECTION, comparison: null, parses: false, reference: null},
        {case: 'the comparison could not run', selection: SELECTION, comparison: unavailable('asset_set_comparison'), parses: false, reference: null},
        // A tracking error is a standard deviation: the schema refuses a negative one, and with it the
        // whole payload — the selected reference it still names included.
        {case: 'malformed, naming a selected reference', selection: SELECTION, comparison: comparisonResult([comparisonItem(7), comparisonItem(12, {tracking_error: -0.052})], {comparison_asset_id: 3}), parses: false, reference: null},
    ];

    it.each(REFERENCE_CASES)('$case: isReference true on the row the parsed comparison names, false on every other', ({selection, comparison, parses, reference}) => {
        // Barrier: the fixture is what its case says — read, or refused by the schema the builder parses with.
        expect(parsesAsComparison(comparison), 'premise: the comparison parses, or not, as the case says').toBe(parses);
        const rows = buildAssetSetPaidRows(selection, LABELS, null, null, comparison);

        expect(rows.map((row) => row.assetId)).toEqual(selection);
        // `false` itself on every other row, never an absent flag — and so one row at most.
        expect(rows.map((row) => row.isReference)).toEqual(selection.map((assetId) => assetId === reference));
    });

    it('measures a selected reference like any other asset, and leaves only its beta and correlation null', () => {
        // Asset 3 is the reference. Against it, the active return is the asset's minus the reference's,
        // the information ratio is active ÷ tracking error exactly, and the reference's own coordinates
        // are its risk/return point: the backend measures both on the same joint window.
        const against3 = [comparisonItem(7, {active_return: 0.146, tracking_error: 0.292, information_ratio: 0.5, correlation: 0.52, beta: 0.32}), comparisonItem(12, {active_return: 0.04, tracking_error: 0.32, information_ratio: 0.125, correlation: 0.42, beta: 0.07})];
        const comparison = comparisonResult(against3, {comparison_asset_id: 3, comparison_volatility: 0.34, comparison_expected_annual_return: -0.052});
        const kpi = kpiResult([kpiItem(3, {volatility: 0.34, max_drawdown: -0.4, max_drawdown_duration_days: 725, sharpe: -0.15, sortino: -0.21})]);
        const rows = buildAssetSetPaidRows(SELECTION, LABELS, returnResult([returnItem(7, 0.21, 0.094), returnItem(3, 0.34, -0.052), returnItem(12, 0.058, -0.012)]), kpi, comparison);

        // Barrier: the comparison was read — the others carry their beta and correlation from its items.
        expect(rowFor(rows, 7)).toMatchObject({beta: 0.32, correlation: 0.52});
        expect(rowFor(rows, 12)).toMatchObject({beta: 0.07, correlation: 0.42});
        expect(rowFor(rows, 3)).toEqual({assetId: 3, name: 'iShares Core MSCI EM IMI', volatility: 0.34, expectedReturn: -0.052, sharpe: -0.15, sortino: -0.21, beta: null, correlation: null, isReference: true});
    });
});

describe('buildAssetSetScatterPoints', () => {
    it('emits one dot per placeable row and never a portfolio one', () => {
        // 🔴 `capitalMarketLine()` draws only when a point whose role is
        // `portfolio` exists, so "no portfolio point" *is* the mechanism that
        // keeps the verdict "paid well for the risk" off a chart of a selection
        // that has no weights and therefore no whole to judge.
        const rows = buildAssetSetPaidRows(SELECTION, LABELS, returnResult([returnItem(7, 0.21, 0.094), returnItem(3, 0.34, -0.052), returnItem(12, 0.058, -0.012)]), null, null);
        const points = buildAssetSetScatterPoints(rows);

        expect(points.map((point) => point.id)).toEqual(['asset-7', 'asset-3', 'asset-12']);
        expect(points.map((point) => point.role)).toEqual(['asset', 'asset', 'asset']);
        // 🔑 And the guarantee is stronger than this assertion can express.
        // `buildAssetSetScatterPoints` declares `role` as the *literal* `'asset'`,
        // so `point.role === 'portfolio'` is not a comparison that returns false —
        // it is a type error, and `svelte-check` rejects it before any test runs.
        // The runtime check above is kept for the reader; the compiler holds the
        // invariant, which is why this line is a comment and not an `expect`.
        expect(points[0]).toEqual({id: 'asset-7', name: 'Vanguard FTSE All-World', volatility: 0.21, annualReturn: 0.094, role: 'asset'});
    });

    it('drops a row missing either coordinate instead of pinning it to an axis', () => {
        // A dot on an axis reads as "riskless" or "returned nothing" — a
        // measurement nobody made. Both halves are tested because either one
        // alone would leave the other free to regress.
        const points = buildAssetSetScatterPoints([paidRow(), paidRow({assetId: 3, volatility: null}), paidRow({assetId: 12, expectedReturn: null})]);

        expect(points.map((point) => point.id)).toEqual(['asset-7']);
    });

    it('plots a dot whose coordinates are honestly zero', () => {
        // The drop test above is `=== null`, not truthiness. A fixed-price
        // instrument really does measure zero volatility, and a window that ended
        // where it began really does measure a zero return; a falsy check would
        // silently delete both from the chart.
        const points = buildAssetSetScatterPoints([paidRow({assetId: 3, volatility: 0, expectedReturn: 0})]);

        expect(points).toHaveLength(1);
        expect(points[0].volatility).toBe(0);
        expect(points[0].annualReturn).toBe(0);
    });

    it('carries the row label onto the dot, #id fallback included', () => {
        const points = buildAssetSetScatterPoints([paidRow({assetId: 25, name: '#25'})]);

        expect(points[0]).toEqual({id: 'asset-25', name: '#25', volatility: 0.21, annualReturn: 0.094, role: 'asset'});
    });

    it('has nothing to draw when no row carries both coordinates', () => {
        expect(buildAssetSetScatterPoints([])).toEqual([]);
        expect(buildAssetSetScatterPoints([paidRow({volatility: null, expectedReturn: null})])).toEqual([]);
    });
});

/**
 * buildAssetSetChartPoints — the scatter's dots, the reference's among them (D371).
 *
 * One `asset` dot per row with both coordinates, `asset-<id>`, in row order. The
 * reference gets one dot whenever it has a point: when it is one of the placeable
 * rows, that row's own dot takes the role `benchmark` and keeps everything else —
 * its id, its place, its name and its coordinates; otherwise its own `benchmark`
 * point is appended last, as before D371. Never two dots for one asset.
 */
describe('buildAssetSetChartPoints', () => {
    /** The contract's dot, written out rather than read off the implementation's own type. */
    type Dot = {id: string; name: string; volatility: number; annualReturn: number; role: 'asset' | 'benchmark'};

    const WORLD = paidRow({assetId: 7, name: 'Vanguard FTSE All-World', volatility: 0.21, expectedReturn: 0.094});
    const EMERGING = paidRow({assetId: 3, name: 'iShares Core MSCI EM IMI', volatility: 0.34, expectedReturn: -0.052});
    const BONDS = paidRow({assetId: 12, name: 'Xtrackers EUR Corporate Bond', volatility: 0.058, expectedReturn: -0.012});
    /** A selected reference's row: measured on the same joint window as its point, so the two agree. */
    const ACWI = paidRow({assetId: BENCHMARK_ID, name: 'MSCI ACWI', volatility: 0.142, expectedReturn: 0.081, isReference: true});
    /** The reference's point, as `buildAssetSetBenchmarkPoint` reads it off the comparison. */
    const REFERENCE: AssetSetBenchmarkPoint = {assetId: BENCHMARK_ID, name: 'MSCI ACWI', volatility: 0.142, expectedReturn: 0.081};
    /** The reference's own dot, when no row carries it. */
    const SEPARATE: Dot = {id: 'benchmark', name: 'MSCI ACWI', volatility: 0.142, annualReturn: 0.081, role: 'benchmark'};

    /** A placeable row's own dot. */
    function dot(row: AssetSetPaidRow, role: Dot['role'] = 'asset'): Dot {
        return {id: `asset-${row.assetId}`, name: row.name, volatility: row.volatility as number, annualReturn: row.expectedReturn as number, role};
    }

    const CASES: {case: string; rows: AssetSetPaidRow[]; benchmark: AssetSetBenchmarkPoint | null; dots: Dot[]}[] = [
        {case: 'no benchmark', rows: [WORLD, EMERGING, BONDS], benchmark: null, dots: [dot(WORLD), dot(EMERGING), dot(BONDS)]},
        {case: 'a benchmark outside the selection', rows: [WORLD, EMERGING, BONDS], benchmark: REFERENCE, dots: [dot(WORLD), dot(EMERGING), dot(BONDS), SEPARATE]},
        {case: 'the benchmark is the first row', rows: [ACWI, WORLD, BONDS], benchmark: REFERENCE, dots: [dot(ACWI, 'benchmark'), dot(WORLD), dot(BONDS)]},
        {case: 'the benchmark is a middle row', rows: [WORLD, ACWI, BONDS], benchmark: REFERENCE, dots: [dot(WORLD), dot(ACWI, 'benchmark'), dot(BONDS)]},
        {case: 'the benchmark is the last row', rows: [WORLD, BONDS, ACWI], benchmark: REFERENCE, dots: [dot(WORLD), dot(BONDS), dot(ACWI, 'benchmark')]},
        {case: 'the selection is the benchmark alone', rows: [ACWI], benchmark: REFERENCE, dots: [dot(ACWI, 'benchmark')]},
        // Selected but not placeable: no row dot carries it, so it is drawn as before D371 — its own point, last.
        {case: 'the benchmark row has no volatility', rows: [WORLD, {...ACWI, volatility: null}, BONDS], benchmark: REFERENCE, dots: [dot(WORLD), dot(BONDS), SEPARATE]},
        {case: 'the benchmark row has no return', rows: [WORLD, {...ACWI, expectedReturn: null}, BONDS], benchmark: REFERENCE, dots: [dot(WORLD), dot(BONDS), SEPARATE]},
        {case: 'no row, a benchmark', rows: [], benchmark: REFERENCE, dots: [SEPARATE]},
        {case: 'no row and no benchmark', rows: [], benchmark: null, dots: []},
    ];

    it.each(CASES)('$case: the dots in row order, the reference marked where it is drawn', ({rows, benchmark, dots}) => {
        expect(buildAssetSetChartPoints(rows, benchmark)).toEqual(dots);
    });

    it.each(CASES)('$case: one dot per asset, and exactly one benchmark dot whenever there is a benchmark', ({rows, benchmark}) => {
        // The rule itself, read off the output rather than off the expected list above.
        const points = buildAssetSetChartPoints(rows, benchmark);
        const ids = points.map((point) => point.id);
        const referenceIds = benchmark === null ? [] : ids.filter((id) => id === 'benchmark' || id === `asset-${benchmark.assetId}`);
        const benchmarkIds = points.filter((point) => point.role === 'benchmark').map((point) => point.id);
        const strangers = points.filter((point) => point.role !== 'asset' && point.role !== 'benchmark').map((point) => point.id);

        expect(new Set(ids).size, `a dot drawn twice: ${ids.join(', ')}`).toBe(ids.length);
        expect(referenceIds.length, `the reference drawn twice, as its row and as its own point: ${referenceIds.join(', ')}`).toBeLessThanOrEqual(1);
        expect(benchmarkIds, 'one benchmark dot when there is a benchmark, none without').toHaveLength(benchmark === null ? 0 : 1);
        expect(strangers, 'a dot neither an asset nor the benchmark — a portfolio dot would anchor the capital market line').toEqual([]);
    });

    it("draws a selected reference with its row's own name and coordinates, never the comparison's", () => {
        // In production the two agree: the backend measures both on the same joint window. They are made to
        // disagree here, because agreement cannot show which one was read — and the row is what the table
        // beside the chart shows, so the dot must not contradict it.
        const row = {...ACWI, name: '#41', volatility: 0.15, expectedReturn: 0.07};

        expect(buildAssetSetChartPoints([WORLD, row, BONDS], REFERENCE)).toEqual([dot(WORLD), {id: 'asset-41', name: '#41', volatility: 0.15, annualReturn: 0.07, role: 'benchmark'}, dot(BONDS)]);
    });
});

describe('buildAssetSetBenchmarkPoint', () => {
    it('places the reference when both of its coordinates arrived', () => {
        const point = buildAssetSetBenchmarkPoint(comparisonResult([comparisonItem(7)]), LABELS);

        expect(point).toEqual({assetId: BENCHMARK_ID, name: 'MSCI ACWI', volatility: 0.142, expectedReturn: 0.081});
    });

    it('refuses to place a reference with only one coordinate', () => {
        // Half of the position would be a figure nobody measured, and the dot
        // would still look like a measurement.
        const noReturn = comparisonResult([comparisonItem(7)], {comparison_expected_annual_return: null});
        const noVolatility = comparisonResult([comparisonItem(7)], {comparison_volatility: null});

        expect(buildAssetSetBenchmarkPoint(noReturn, LABELS)).toBeNull();
        expect(buildAssetSetBenchmarkPoint(noVolatility, LABELS)).toBeNull();
        // An older backend that published beta and nothing about the reference
        // itself omits both fields rather than nulling them.
        expect(buildAssetSetBenchmarkPoint(comparisonResult([comparisonItem(7)], {comparison_volatility: undefined, comparison_expected_annual_return: undefined}), LABELS)).toBeNull();
    });

    it('places a reference measured at zero, which is a reading and not an absence', () => {
        const flat = comparisonResult([comparisonItem(7)], {comparison_volatility: 0, comparison_expected_annual_return: 0});

        expect(buildAssetSetBenchmarkPoint(flat, LABELS)).toEqual({assetId: BENCHMARK_ID, name: 'MSCI ACWI', volatility: 0, expectedReturn: 0});
    });

    it('names the reference #id when the label map has no entry for it', () => {
        const point = buildAssetSetBenchmarkPoint(comparisonResult([comparisonItem(7)]), labels({7: 'Vanguard FTSE All-World'}));

        expect(point?.name).toBe('#41');
    });

    it.each<{reference: string; names: ReadonlyMap<number, string>; name: string}>([
        // Outside the selection, a map built from the *selection* has no entry for the reference, and without
        // a resolver the dot shipped labelled `#41` on every chart — which is why the section passes one (below).
        {reference: 'outside the selection', names: labels({7: 'Vanguard FTSE All-World'}), name: '#41'},
        // Since D371 the reader may select it too: the backend skips it in `items`, and the selection's own map
        // names it. A `LABELS` holding 41, as in the cases above, is a state production can now produce.
        {reference: 'also selected', names: labels({7: 'Vanguard FTSE All-World', 41: 'MSCI ACWI'}), name: 'MSCI ACWI'},
    ])('a reference $reference: the selection map alone labels it $name', ({names, name}) => {
        expect(buildAssetSetBenchmarkPoint(comparisonResult([comparisonItem(7)]), names)?.name).toBe(name);
    });

    it('names the reference through the resolver when the selection map cannot', () => {
        // The contract `AssetSetRiskReturnSection` relies on for a reference outside the selection: it passes
        // the asset store's lookup, the same one the portfolio L3 uses for its benchmark name.
        const selectionOnly = labels({7: 'Vanguard FTSE All-World'});
        const store = (assetId: number) => (assetId === BENCHMARK_ID ? 'MSCI ACWI' : undefined);

        expect(buildAssetSetBenchmarkPoint(comparisonResult([comparisonItem(7)]), selectionOnly, store)?.name).toBe('MSCI ACWI');
        // A resolver that does not know the asset still degrades to `#id`, never to a blank.
        expect(buildAssetSetBenchmarkPoint(comparisonResult([comparisonItem(7)]), selectionOnly, () => undefined)?.name).toBe('#41');
    });

    it('has no point when the comparison did not run, was not asked for, or came back malformed', () => {
        expect(buildAssetSetBenchmarkPoint(null, LABELS)).toBeNull();
        expect(buildAssetSetBenchmarkPoint(unavailable('asset_set_comparison'), LABELS)).toBeNull();
        // `comparison_asset_id` is required: without it there is no reference to
        // name, so the whole payload is refused rather than half-read.
        expect(buildAssetSetBenchmarkPoint(ok('asset_set_comparison', {kind: 'comparison_set', observations: 502, comparison_volatility: 0.142, comparison_expected_annual_return: 0.081, items: []}), LABELS)).toBeNull();
    });
});

describe('the widened optional numerics', () => {
    /**
     * ⚠️ WHAT THIS GROUP ACTUALLY PINS, WHICH IS NOT WHAT `num()` ADVERTISES.
     *
     * The generated client disagrees with itself: the emitted TypeScript widens
     * every optional numeric to `((number | null) | Array<number | null>)`,
     * while the zod validator beside it is `z.union([z.number(),
     * z.null()]).optional()` — which rejects a list. Since every payload here
     * reaches the helpers through `riskOutput()`, *which parses with that zod
     * schema*, a list can never reach `num()` at a field: the parse has already
     * refused the whole output. `singleValue` inside `num()` is an answer to the
     * compiler, not a runtime unwrapper, and the docstring's "a cast is exactly
     * how an array would reach `toFixed`" overstates it.
     *
     * Where the widening is real at runtime is one level up: `result.output` is
     * widened the same way, and `riskOutput` unwraps it with `singleValue`
     * before parsing. So both tests below are true, and they are true for
     * different reasons — which is the whole reason to write them separately.
     */
    it('unwraps an output that arrived wrapped in a list', () => {
        const wrapped = ok('asset_set_var', [{kind: 'var_cvar_set', confidence_level: 0.95, horizon_days: 1, horizon_observations: 1, observations: 502, items: [varItem(7, 0.021, 0.031)]}], ASSET_SET_DAILY_VAR_INSTANCE);

        expect(rowFor(buildAssetSetHurtRows([7], LABELS, wrapped, null, null), 7).badDay).toBe(0.031);
    });

    it('has nothing to read when the output list is empty, and says so with nulls', () => {
        const empty = ok('asset_set_var', [], ASSET_SET_DAILY_VAR_INSTANCE);
        const row = rowFor(buildAssetSetHurtRows([7], LABELS, empty, null, null), 7);

        expect(row.badDay).toBeNull();
        expect(row.badMonth).toBeNull();
    });

    it('discards the whole payload when a widened field really does arrive as a list', () => {
        // Not "reads the first element": the zod schema refuses the list, the
        // parse of the entire output fails, and asset 7's perfectly ordinary
        // sharpe is lost along with asset 3's list-wrapped one. That collateral
        // loss is the behaviour, and pinning it here means the day the API does
        // start sending windows, this test fails and names the reason.
        const rows = buildAssetSetPaidRows([7, 3], LABELS, null, kpiResult([kpiItem(7), kpiItem(3, {volatility: 0.34, sharpe: [0.8]})]), null);

        expect(rowFor(rows, 7).sharpe).toBeNull();
        expect(rowFor(rows, 3).sharpe).toBeNull();
        // The KPI volatility fallback goes with it, which is how a reader would
        // notice: the whole column empties, not one cell.
        expect(rowFor(rows, 7).volatility).toBeNull();
        // What must never happen is the list itself surviving into a cell, where
        // the next stop is a percent formatter and the output is `NaN%`.
        expect(rows.every((row) => row.sharpe === null || typeof row.sharpe === 'number')).toBe(true);
    });
});

/**
 * A result's `metadata`, complete — it parses with `schemas.RiskResultMetadata`, which is what
 * `riskMetadata()` reads it through — and filled the way the engine fills it for an asset set
 * (`RiskService` loads prices from the day before the requested start, `series_preparation.py`
 * prepares them):
 *
 *  - the BASELINE PRICE — the one the first return is measured from — is the last complete date
 *    before the requested start whenever every asset has history before it. Prices are carried over
 *    every calendar day, so that is the day before the toolbar's first day, quoted or not. Only when
 *    some asset has no earlier history is it the first complete date inside the range;
 *  - `analyzed_range` runs from the first RETURN date to the last one, and a return exists only on a
 *    day some asset is freshly quoted: a weekend or a holiday is a carry, not a return;
 *  - `calendar_days` runs from the baseline price date to the last return date;
 *  - `annualization_factor` is `observed_annualization`'s, `n · 365 / calendar_days`, and nothing
 *    when nothing was observed.
 *
 * So the period the figures cover opens on `end − calendar_days + 1`, the day after the baseline
 * price — the first day whose price movement they capture, and the toolbar's first day itself
 * whenever there is history before it — and holds `calendar_days` days, both ends counted. Not on
 * `end − calendar_days`, the baseline price day, which lies outside the period asked for; nor on
 * `analyzed_range.start`, which drops the weekend or the holiday a first return spans. Every count of
 * returns below is invented, of the order a joint calendar of exchange-traded assets gives: about 252
 * a year.
 */
function windowMetadata(firstReturn: string, lastReturn: string | null, calendarDays: number, observations: number): Payload {
    return {
        analyzed_range: {start: firstReturn, end: lastReturn},
        frequency: 'daily',
        n_observations: observations,
        calendar_days: calendarDays,
        annualization_factor: observations > 0 && calendarDays > 0 ? (observations * 365) / calendarDays : null,
        coverage: 1,
        currency: 'EUR',
        scope: 'asset_set',
        return_basis: 'price_only',
        algorithm_version: 'invented-asset-set',
        computed_at: '2026-10-01T09:00:00+00:00',
    };
}

/** The same result, carrying the metadata the API sends beside its output. */
function withMetadata(result: RiskAnalyticResult, metadata: Payload | null): RiskAnalyticResult {
    return {...result, metadata} as unknown as RiskAnalyticResult;
}

/**
 * The period L3°'s note states: the window the figures were actually calculated on, against the one
 * the toolbar asked for. Read from the first result, in the order handed, whose metadata measured
 * something — the section hands `[riskReturn, kpi, comparison]`.
 */
describe('assetSetCalculationWindow', () => {
    /** The toolbar's period in most cases below: a year, Wednesday to Wednesday. */
    const SELECTED_START = '2025-10-01';
    const SELECTED_END = '2026-09-30';

    /**
     * The year as an asset set with history before it reports it: the baseline price on 30 September,
     * the day before the selection opens, the first return on its first day, the last return on its
     * last day — 365 days from the baseline to the last return, which are the selection's own 365.
     */
    const FULL_YEAR = windowMetadata('2025-10-01', '2026-09-30', 365, 252);

    /**
     * The same history, under a selection opening on Saturday 4 October: the baseline is Friday's
     * price, the first return Monday's — which holds the weekend's movement as well — and 362 days
     * run from that Friday to the last return.
     */
    const SATURDAY_START = windowMetadata('2025-10-06', '2026-09-30', 362, 249);

    /**
     * Where the window opens and closes against the selection, and whether that makes it narrower.
     * With history before the selection the window opens on its first day whatever the calendar, so
     * a late start is an asset first priced inside the selection — its first price is the baseline,
     * and the window opens the day after it — and an early end is a last return before the
     * selection's last day. The tolerance is a week on either side, so seven days is the last that is
     * not narrowed, and eight the first that is.
     */
    const NARROWING = [
        {case: 'an asset first priced three and a half months into the selection, with no history before it', dateStart: SELECTED_START, dateEnd: SELECTED_END, metadata: windowMetadata('2026-01-16', '2026-09-30', 258, 178), start: '2026-01-16', end: '2026-09-30', days: 258, narrowed: true},
        {case: 'a selection closing on a Sunday, last quoted on the Friday', dateStart: SELECTED_START, dateEnd: '2026-09-27', metadata: windowMetadata('2025-10-01', '2026-09-25', 360, 249), start: '2025-10-01', end: '2026-09-25', days: 360, narrowed: false},
        {case: 'a last return a fortnight before the selection closes', dateStart: SELECTED_START, dateEnd: SELECTED_END, metadata: windowMetadata('2025-10-01', '2026-09-15', 350, 241), start: '2025-10-01', end: '2026-09-15', days: 350, narrowed: true},
        {case: 'a start exactly seven days late', dateStart: SELECTED_START, dateEnd: SELECTED_END, metadata: windowMetadata('2025-10-08', '2026-09-30', 358, 247), start: '2025-10-08', end: '2026-09-30', days: 358, narrowed: false},
        {case: 'a start eight days late', dateStart: SELECTED_START, dateEnd: SELECTED_END, metadata: windowMetadata('2025-10-09', '2026-09-30', 357, 246), start: '2025-10-09', end: '2026-09-30', days: 357, narrowed: true},
        {case: 'an end exactly seven days early', dateStart: SELECTED_START, dateEnd: SELECTED_END, metadata: windowMetadata('2025-10-01', '2026-09-23', 358, 247), start: '2025-10-01', end: '2026-09-23', days: 358, narrowed: false},
        {case: 'an end eight days early', dateStart: SELECTED_START, dateEnd: SELECTED_END, metadata: windowMetadata('2025-10-01', '2026-09-22', 357, 246), start: '2025-10-01', end: '2026-09-22', days: 357, narrowed: true},
    ];

    /**
     * `end − calendar_days + 1`, counted in whole UTC days. Each row is a place where counting any
     * other way comes out a day off: a month end crossed together with a weekend, a leap day, a year
     * that contains one, and the night the clocks go back in most of Europe — where a local midnight
     * is still the previous day in UTC. The selection is the window itself, with history before it,
     * so none is narrowed.
     */
    const COUNTING_BACK = [
        {case: 'across a month end and a weekend, to the Saturday the selection opens on — never the Friday of the baseline price, nor the Monday of the first return', metadata: windowMetadata('2026-03-02', '2026-03-02', 3, 1), start: '2026-02-28', end: '2026-03-02', days: 3},
        {case: 'onto a leap day', metadata: windowMetadata('2028-02-29', '2028-03-01', 2, 2), start: '2028-02-29', end: '2028-03-01', days: 2},
        {case: 'over a leap day: 365 days ending on 29 September 2028 open on 1 October of the year before, not on the 30th a plain year back would give', metadata: windowMetadata('2027-10-01', '2028-09-29', 365, 252), start: '2027-10-01', end: '2028-09-29', days: 365},
        {case: 'across the night the clocks go back, to the Saturday before it', metadata: windowMetadata('2025-10-27', '2025-10-27', 3, 1), start: '2025-10-25', end: '2025-10-27', days: 3},
    ];

    /** A single day, as `DateRangeModel` allows it: an `end` of null is "the start day only". One return, measured from the price the day before. */
    const SINGLE_DAY = windowMetadata('2026-09-30', null, 1, 1);

    /**
     * What a result that measured nothing carries: `RiskService._metadata` zeroes `calendar_days`
     * whenever `n_observations` is 0, and an unavailable result may still carry its metadata. Its
     * range is the one asked for, which is no window at all.
     */
    const MEASURED_NOTHING = windowMetadata(SELECTED_START, SELECTED_END, 0, 0);

    /** The window one metadata describes, read off the risk/return result alone. */
    function windowOf(metadata: Payload, dateStart = SELECTED_START, dateEnd = SELECTED_END) {
        return assetSetCalculationWindow([withMetadata(returnResult([returnItem(7, 0.16, 0.071)]), metadata), null, null], dateStart, dateEnd);
    }

    it('every metadata fixture here is complete: it parses as the API would send it', () => {
        const fixtures = [FULL_YEAR, SATURDAY_START, ...NARROWING.map((row) => row.metadata), ...COUNTING_BACK.map((row) => row.metadata), SINGLE_DAY, MEASURED_NOTHING];
        for (const metadata of fixtures) {
            const parsed = schemas.RiskResultMetadata.safeParse(metadata);
            expect(parsed.success, `${JSON.stringify(metadata.analyzed_range)}: ${parsed.success ? '' : parsed.error.message}`).toBe(true);
        }
    });

    it('opens the window on the day after the baseline price — with history before the selection, its first day — and holds calendar_days days, both ends counted', () => {
        const window = windowOf(FULL_YEAR);
        expect(window?.start, 'opened on end − calendar_days: the baseline price day, outside the period asked for — the figures start from its price, not from its movement').not.toBe('2025-09-30');
        expect(window).toEqual({start: '2025-10-01', end: '2026-09-30', days: 365, narrowed: false});
    });

    it("opens on the selection's first day even when nothing is quoted on it, and not on the first return", () => {
        const window = windowOf(SATURDAY_START, '2025-10-04');
        expect(window?.start, "opened on analyzed_range.start, the first return: the weekend that Monday's return spans would fall out of the period stated").not.toBe('2025-10-06');
        expect(window).toEqual({start: '2025-10-04', end: '2026-09-30', days: 362, narrowed: false});
    });

    it.each(NARROWING)('$case: opens on $start, narrowed $narrowed', ({dateStart, dateEnd, metadata, start, end, days, narrowed}) => {
        expect(windowOf(metadata, dateStart, dateEnd)).toEqual({start, end, days, narrowed});
    });

    it.each(COUNTING_BACK)('counts back $case', ({metadata, start, end, days}) => {
        expect(windowOf(metadata, start, end)).toEqual({start, end, days, narrowed: false});
    });

    it('reads a range given as a single day — its end null — as ending on its start: a period of that one day', () => {
        expect(windowOf(SINGLE_DAY, '2026-09-30', '2026-09-30')).toEqual({start: '2026-09-30', end: '2026-09-30', days: 1, narrowed: false});
    });

    it('reads the first result that measured anything, in the order it is handed', () => {
        // In one answer the three normally agree: the KPI and the risk/return are measured on one
        // joint calendar, and the comparison's can only be narrower, since the reference's prices
        // join it. They differ here only so the one read can be told apart: the KPI's as if its
        // first common price were Monday 6 October, the comparison's as if it were 15 January, with
        // no history before either.
        const own = withMetadata(returnResult([returnItem(7, 0.16, 0.071)]), FULL_YEAR);
        const kpi = withMetadata(kpiResult([kpiItem(7)]), windowMetadata('2025-10-07', '2026-09-30', 359, 248));
        const comparison = withMetadata(comparisonResult([comparisonItem(7)]), windowMetadata('2026-01-16', '2026-09-30', 258, 178));
        const ownWindow = {start: '2025-10-01', end: '2026-09-30', days: 365, narrowed: false};
        const kpiWindow = {start: '2025-10-07', end: '2026-09-30', days: 359, narrowed: false};
        const comparisonWindow = {start: '2026-01-16', end: '2026-09-30', days: 258, narrowed: true};

        expect(assetSetCalculationWindow([own, kpi, comparison], SELECTED_START, SELECTED_END), 'the risk/return result comes first: its window is the one read').toEqual(ownWindow);
        expect(assetSetCalculationWindow([null, kpi, comparison], SELECTED_START, SELECTED_END), 'no risk/return result: the KPI is next').toEqual(kpiWindow);
        expect(assetSetCalculationWindow([returnResult([returnItem(7, 0.16, 0.071)]), kpi, comparison], SELECTED_START, SELECTED_END), 'a risk/return result without metadata is passed over, never read as an empty window').toEqual(kpiWindow);
        expect(assetSetCalculationWindow([null, null, comparison], SELECTED_START, SELECTED_END), 'the comparison is the last resort').toEqual(comparisonWindow);
        // The order is the caller's, not a ranking of analytic codes: the same three, handed the other way round.
        expect(assetSetCalculationWindow([comparison, kpi, own], SELECTED_START, SELECTED_END)).toEqual(comparisonWindow);
    });

    it('passes over a result that measured nothing — zero returns over zero days — and reads the next', () => {
        const nothing = withMetadata(unavailable('asset_set_risk_return'), MEASURED_NOTHING);
        const kpi = withMetadata(kpiResult([kpiItem(7)]), FULL_YEAR);

        expect(assetSetCalculationWindow([nothing, kpi, null], SELECTED_START, SELECTED_END)).toEqual({start: '2025-10-01', end: '2026-09-30', days: 365, narrowed: false});
    });

    it('passes over a metadata that breaks its own contract instead of half-reading it', () => {
        const kpi = withMetadata(kpiResult([kpiItem(7)]), windowMetadata('2025-10-07', '2026-09-30', 359, 248));
        // Returns observed over no days at all: `observed_annualization` raises before it emits this.
        const noDays = withMetadata(returnResult([returnItem(7, 0.16, 0.071)]), windowMetadata('2025-10-01', '2026-09-30', 0, 252));
        // No range at all: the model requires one.
        const rangeless: Payload = {...FULL_YEAR};
        delete rangeless.analyzed_range;
        const noRange = withMetadata(returnResult([returnItem(7, 0.16, 0.071)]), rangeless);

        for (const [why, broken] of [
            ['no days', noDays],
            ['no range', noRange],
        ] as const) {
            expect(assetSetCalculationWindow([broken, kpi, null], SELECTED_START, SELECTED_END), `${why}: the KPI's window must be read instead`).toEqual({start: '2025-10-07', end: '2026-09-30', days: 359, narrowed: false});
        }
    });

    it('is null when no result qualifies: none handed, none answered, none carrying metadata, none that measured anything', () => {
        expect(assetSetCalculationWindow([], SELECTED_START, SELECTED_END)).toBeNull();
        expect(assetSetCalculationWindow([null, null, null], SELECTED_START, SELECTED_END)).toBeNull();
        // The row builders' fixtures above: answers with figures and no metadata.
        expect(assetSetCalculationWindow([returnResult([returnItem(7, 0.16, 0.071)]), kpiResult([kpiItem(7)]), comparisonResult([comparisonItem(7)])], SELECTED_START, SELECTED_END)).toBeNull();
        expect(assetSetCalculationWindow([withMetadata(returnResult([returnItem(7, 0.16, 0.071)]), null), null, null], SELECTED_START, SELECTED_END)).toBeNull();
        expect(assetSetCalculationWindow([withMetadata(unavailable('asset_set_risk_return'), MEASURED_NOTHING), null, null], SELECTED_START, SELECTED_END)).toBeNull();
    });
});

/**
 * The length L3°'s note writes after the period's dates (the developer, 2026-10-01): no longer a count of
 * days but the same span in calendar units — «3 mesi e 1 giorno», «1 anno», «8 mesi e 15 giorni» — which
 * the section words from three plural keys, leaving out the parts that are zero.
 *
 * The span is the window's, both ends counted, so it runs to the day after `end`. Into it go as many
 * whole calendar months as fit, each count of them added to `start` itself — never chained from the
 * month before — with a day the target month lacks clamped to its last: 31 January plus one month is 28
 * February, or 29. Twelve months make a year; what is left over is whole days. Nothing at all when `end`
 * precedes `start`. All on UTC days, as `assetSetCalculationWindow` counts: the note's `data-days` is this
 * very span, counted in days.
 *
 * Every row was worked out by hand from that definition, not read off an implementation: each one can be
 * redone with a calendar.
 */
describe('calendarLength', () => {
    const LENGTHS: {case: string; start: string; end: string; length: CalendarLength}[] = [
        {case: "the developer's own: 93 days from 1 July are three whole months — July, August, September — and 1 October", start: '2026-07-01', end: '2026-10-01', length: {years: 0, months: 3, days: 1}},
        {case: 'three months to the day: up to 30 September, nothing is left over', start: '2026-07-01', end: '2026-09-30', length: {years: 0, months: 3, days: 0}},
        {case: "the toolbar's year, Wednesday to Wednesday: twelve months make one year", start: '2025-10-01', end: '2026-09-30', length: {years: 1, months: 0, days: 0}},
        {case: 'one day more: a year and a day', start: '2025-10-01', end: '2026-10-01', length: {years: 1, months: 0, days: 1}},
        {case: 'a year that holds a leap day is still one year: 366 days, not a year and a day', start: '2027-10-01', end: '2028-09-30', length: {years: 1, months: 0, days: 0}},
        {case: 'less than a month: only days, both ends counted', start: '2026-09-01', end: '2026-09-15', length: {years: 0, months: 0, days: 15}},
        {case: 'a single day: start and end the same', start: '2026-09-30', end: '2026-09-30', length: {years: 0, months: 0, days: 1}},
        {case: 'from 16 January: eight months to 16 September, and fifteen days to the end of the month', start: '2026-01-16', end: '2026-09-30', length: {years: 0, months: 8, days: 15}},
        {case: 'over two years: twenty-five months are two years and a month, and fifteen days', start: '2024-10-01', end: '2026-11-15', length: {years: 2, months: 1, days: 15}},
        {case: 'clamped: 31 January plus a month is 28 February, so to 28 February is a month and a day — not 29 days, as with a month rolling over into March', start: '2026-01-31', end: '2026-02-28', length: {years: 0, months: 1, days: 1}},
        {case: 'from the start, never chained: 31 January plus two months is 31 March, not 28 March by way of a clamped February', start: '2026-01-31', end: '2026-03-30', length: {years: 0, months: 2, days: 0}},
        {case: 'from a leap day: a year on is clamped to 28 February 2029, and 1 March is one day more', start: '2028-02-29', end: '2029-02-28', length: {years: 1, months: 0, days: 1}},
    ];

    /**
     * The nights the clocks change in most of Europe — back on Sunday 26 October 2025, forward on Sunday
     * 29 March 2026 — when a local day lasts 25 hours, or 23. Between local midnights, days across one of
     * them are an hour longer or shorter than a whole number, which a count rounded the wrong way turns
     * into a day too many or too few; and a month added in local time to a UTC midnight lands an hour past
     * the end it must fit before, so it is not counted at all. On UTC days neither can happen.
     */
    const CLOCK_CHANGES: {case: string; start: string; end: string; length: CalendarLength}[] = [
        {case: "the developer's own: October 2025, across the night the clocks go back, is one month", start: '2025-10-01', end: '2025-10-31', length: {years: 0, months: 1, days: 0}},
        {case: 'the twelve days left over after a month span the night the clocks go back', start: '2025-09-20', end: '2025-10-31', length: {years: 0, months: 1, days: 12}},
        {case: 'the twelve days left over after a month span the night the clocks go forward', start: '2026-02-20', end: '2026-03-31', length: {years: 0, months: 1, days: 12}},
    ];

    /** How long a local day lasts, in hours: 24, except on the nights the clocks change. */
    function localDayHours(year: number, monthIndex: number, day: number): number {
        return (new Date(year, monthIndex, day + 1).getTime() - new Date(year, monthIndex, day).getTime()) / 3_600_000;
    }

    /**
     * `read`, run with the process in Europe/Rome — whose clocks change, and where the lab is read —
     * whatever zone the suite started in, the zone put back after. Node re-reads the zone when
     * `process.env.TZ` is assigned, which `chartCoreHelpers.test.ts` relies on too; the two premises prove
     * it took, so a suite started in UTC cannot pass these rows for want of a night that is not 24 hours.
     */
    function inEuropeRome<T>(read: () => T): T {
        const previousTimeZone = process.env.TZ;
        process.env.TZ = 'Europe/Rome';
        try {
            expect(localDayHours(2025, 9, 26), 'premise: in Europe/Rome, Sunday 26 October 2025 lasts 25 hours').toBe(25);
            expect(localDayHours(2026, 2, 29), 'premise: in Europe/Rome, Sunday 29 March 2026 lasts 23 hours').toBe(23);
            return read();
        } finally {
            if (previousTimeZone === undefined) delete process.env.TZ;
            else process.env.TZ = previousTimeZone;
        }
    }

    it.each(LENGTHS)('$case ($start … $end)', ({start, end, length}) => {
        expect(calendarLength(start, end)).toEqual(length);
    });

    it("counts calendar months, not 30-day ones: the developer's 93 days are three months and a day, not three months and three days", () => {
        const length = calendarLength('2026-07-01', '2026-10-01');
        expect(length, '93 = 3 × 30 + 3: counted in 30-day months').not.toEqual({years: 0, months: 3, days: 3});
        expect(length).toEqual({years: 0, months: 3, days: 1});
    });

    it.each(CLOCK_CHANGES)('$case ($start … $end): counted on UTC days, in a zone whose clocks change', ({start, end, length}) => {
        expect(inEuropeRome(() => calendarLength(start, end))).toEqual(length);
    });

    it.each([
        {before: 'by a day', start: '2026-09-30', end: '2026-09-29'},
        {before: 'by three months', start: '2026-10-01', end: '2026-07-01'},
        {before: 'by two years', start: '2027-10-01', end: '2025-10-01'},
    ])('is nothing when the end precedes the start $before — never a negative part', ({start, end}) => {
        expect(calendarLength(start, end)).toEqual({years: 0, months: 0, days: 0});
    });
});
