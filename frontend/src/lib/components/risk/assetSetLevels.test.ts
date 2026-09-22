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
 *    it is the yardstick for.
 *  - `RiskAnalyticResult` — `ok` and `partial` *must* carry an output;
 *    `unavailable` and `failed` must *not*, and must carry an error instead.
 *    That is why no fixture here fakes an unavailable result holding a payload:
 *    the shape does not exist, so a test built on it would prove nothing.
 *
 * `metadata` and `data_quality` are omitted from the successful fixtures even
 * though the same model requires them. Nothing in `assetSetLevels.ts` reads
 * either, so writing two more payloads would add fixture surface to maintain
 * and not one assertion. A stated shortcut, not an oversight.
 *
 * Where arithmetic links two invented figures, it is made exact so the reader
 * can verify the fixture instead of trusting it: a 40% fall that has given back
 * half of itself leaves the asset 20% down (`recovered_ratio` 0.5), and 20%
 * down needs a 25% rise to get back to the peak (`remaining_to_peak_ratio`
 * 0.25 = 0.2 / 0.8).
 */
import {describe, expect, it} from 'vitest';

import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {ASSET_SET_DAILY_VAR_INSTANCE, ASSET_SET_MONTHLY_VAR_INSTANCE} from './riskAnalysisHelpers';
import {buildAssetSetBenchmarkPoint, buildAssetSetHurtRows, buildAssetSetPaidRows, buildAssetSetScatterPoints, type AssetSetPaidRow} from './assetSetLevels';

type Payload = Record<string, unknown>;

/**
 * The selection under test: three assets, deliberately neither sorted nor
 * contiguous, so "selection order" is observable and cannot be confused with
 * "ascending id" or "whatever the payload listed first".
 */
const SELECTION = [7, 3, 12];

/** The shared reference. Never a member of the selection — the model forbids it. */
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
    return ok('asset_set_var', {kind: 'var_cvar_set', confidence_level: 0.95, horizon_days: 1, observations: 502, items, ...overrides}, ASSET_SET_DAILY_VAR_INSTANCE);
}

/**
 * The ~1-month tail: same analytic code, different instance.
 *
 * `observations` is 20 lower than the daily run's and that is not decoration —
 * the output's own docstring says compounding to a horizon consumes
 * `horizon_days - 1` observations, so 502 − 20 = 482.
 */
function monthlyVar(items: Payload[]): RiskAnalyticResult {
    return ok('asset_set_var', {kind: 'var_cvar_set', confidence_level: 0.95, horizon_days: 21, observations: 482, items}, ASSET_SET_MONTHLY_VAR_INSTANCE);
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

describe('buildAssetSetHurtRows', () => {
    it('gives every selected asset a row in selection order, even when the analytics answered for fewer', () => {
        // A partial answer covering two of the three assets, and a drawdown
        // covering only the third: between them no single asset is described by
        // both, which is what makes the join visible.
        const rows = buildAssetSetHurtRows(
            SELECTION,
            LABELS,
            partial('asset_set_var', {kind: 'var_cvar_set', confidence_level: 0.95, horizon_days: 1, observations: 502, items: [varItem(7, 0.021, 0.031), varItem(12, 0.009, 0.013)]}, ASSET_SET_DAILY_VAR_INSTANCE),
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
});

describe('buildAssetSetScatterPoints', () => {
    /** A row with both coordinates, for the cases a payload would only obscure. */
    function paidRow(overrides: Partial<AssetSetPaidRow> = {}): AssetSetPaidRow {
        return {assetId: 7, name: 'Vanguard FTSE All-World', volatility: 0.21, expectedReturn: 0.094, sharpe: 0.62, sortino: 0.81, beta: null, correlation: null, ...overrides};
    }

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
        const wrapped = ok('asset_set_var', [{kind: 'var_cvar_set', confidence_level: 0.95, horizon_days: 1, observations: 502, items: [varItem(7, 0.021, 0.031)]}], ASSET_SET_DAILY_VAR_INSTANCE);

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
