/**
 * «How does it move?» — the positive twins of «How much can it hurt?» (RN-14 computes them, Q21 c), read once.
 *
 * Two surfaces show them: the lab's table «How did each one move?» (RN-19, one row per asset, from the `asset_set_*`
 * items) and the levels' block «How does it move?» (RN-18, one scope: a portfolio, a broker, one asset). The backend
 * publishes the same field names on both shapes, so the reading lives here once — which field is which figure, when a
 * rally has dates, which warning blanks which figure — and each surface only says where its three answers come from.
 *
 * Fractions as the contract states them; a blank is `null`.
 */
import type {z} from 'zod';
import {schemas} from '$lib/api';
import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';
import {riskOutput, singleValue} from '$lib/features/risk/riskTypes';
import {formatFixed} from '$lib/utils/core/formatFixed';

type KpiItem = z.infer<typeof schemas.RiskAssetSetKpiItem>;
type DrawdownItem = z.infer<typeof schemas.RiskAssetSetDrawdownItem>;
type HorizonWindow = z.infer<typeof schemas.RiskWorstHorizonWindow>;

/** The KPI fields the figures read: the same names on `historical_kpi` and on an `asset_set_kpi` item. */
export type MoveShapeFields = Partial<
    Pick<
        KpiItem,
        | 'best_realization'
        | 'best_realization_date'
        | 'positive_observation_share'
        | 'mean_positive_return'
        | 'mean_negative_return'
        | 'longest_positive_run_observations'
        | 'longest_positive_run_start_date'
        | 'longest_positive_run_end_date'
        | 'omega_ratio'
        | 'downside_deviation'
        | 'extreme_day_ratio'
    >
>;
/** The drawdown fields the figures read: the same names on `drawdown_summary` and on an `asset_set_drawdown` item. */
export type MoveFallFields = Partial<Pick<DrawdownItem, 'largest_rally' | 'largest_rally_start_date' | 'largest_rally_end_date' | 'largest_rally_duration_days' | 'average_drawdown'>>;

/**
 * A finite number, or null — through the house unwrapper.
 *
 * ⚠️ The generated client widens every optional numeric field to
 * `((number | null) | Array<number | null>)`, because that is how the OpenAPI
 * `anyOf` round-trips — so a field is *typed* as a value or a list of them and
 * will not compile without unwrapping.
 *
 * 📌 The widening is a TypeScript artefact, not a runtime one: the emitted **zod**
 * schema for those same fields is `z.union([z.number(), z.null()]).optional()`,
 * which rejects a list outright — so `riskOutput` discards the whole payload
 * before a list could reach here. `CorrelationCell.value` (`correlationHelpers.ts`)
 * records the same disagreement between the two halves of the generated client.
 * What `singleValue` actually earns is the right to read the field without a
 * cast, and a cast is how a future shape change would arrive unannounced.
 */
export function finiteOrNull(value: number | null | undefined | readonly (number | null)[]): number | null {
    const single = singleValue(value);
    return typeof single === 'number' && Number.isFinite(single) ? single : null;
}

/** A pair of ISO dates from the payload, in order, or null: a lone date would point at a stretch nobody stated. */
export function datePeriod(from: string | null | undefined, to: string | null | undefined): {from: string; to: string} | null {
    return typeof from === 'string' && typeof to === 'string' && from <= to ? {from, to} : null;
}

/** The figures whose blank can say why. */
export type MoveColumn = 'bestDay' | 'omega' | 'meanUp' | 'meanDown' | 'streak' | 'extremeDays';

/** Each figure a backend warning code leaves blank, and the warning that says why (Q20: «—» with its reason). */
export const MOVE_BLANK_REASONS: ReadonlyArray<readonly [string, readonly MoveColumn[]]> = [
    ['best_realization_undefined', ['bestDay', 'meanUp', 'streak']],
    ['average_loss_undefined', ['meanDown']],
    ['omega_undefined', ['omega']],
    ['extreme_day_ratio_undefined', ['extremeDays']],
];

/** The positive twins of one subject, every figure read from one calendar. */
export interface MoveFigures {
    /** The best single return, and the day of it. */
    bestDay: number | null;
    bestDayDate: string | null;
    /** The best compounded 30-day window the subject lived through: a figure even when it lost (never floored). */
    bestMonth: {gain: number; from: string; to: string} | null;
    /** The largest rise from a low to a later high; no rise is a measured 0 with no dates. */
    rally: {gain: number; from: string | null; to: string | null; days: number | null} | null;
    /** Gains against losses (Omega). */
    omega: number | null;
    /** Share of the days with a gain. */
    positiveShare: number | null;
    /** The semi-deviation, annualized. */
    downsideDeviation: number | null;
    /** The average up day and down day (Q21 c). */
    meanUp: number | null;
    meanDown: number | null;
    /** The longest run of positive days, and when (Q21 c). */
    streak: {days: number; from: string; to: string} | null;
    /** «Below the peak, on average» (ADD), ≤ 0. */
    averageDrawdown: number | null;
    /** How much more frequent extreme days are than on the bell curve: the kurtosis over 3. */
    extremeDays: number | null;
    /** The reason of a blank, as the catalogue key of the backend warning that names it. */
    reasons: Partial<Record<MoveColumn, string>>;
}

/**
 * Read the figures of one subject: its KPI fields (`shape`), the best window of its 30-day VaR (`best`), its drawdown
 * fields (`fall`) and the warning codes that concern it (`codes`). Any of the three may be absent: what it carries stays
 * blank.
 */
export function readMoveFigures(shape: MoveShapeFields | null | undefined, best: HorizonWindow | null | undefined, fall: MoveFallFields | null | undefined, codes: ReadonlySet<string>): MoveFigures {
    const bestGain = best ? finiteOrNull(best.compounded_return) : null;
    const bestPeriod = best ? datePeriod(singleValue(best.start_date), singleValue(best.end_date)) : null;
    const rallyGain = finiteOrNull(fall?.largest_rally);
    const rallyPeriod = datePeriod(singleValue(fall?.largest_rally_start_date), singleValue(fall?.largest_rally_end_date));
    const streakDays = finiteOrNull(shape?.longest_positive_run_observations);
    const streakPeriod = datePeriod(singleValue(shape?.longest_positive_run_start_date), singleValue(shape?.longest_positive_run_end_date));
    const reasons: Partial<Record<MoveColumn, string>> = {};
    for (const [code, columns] of MOVE_BLANK_REASONS) {
        if (!codes.has(code)) continue;
        // The singular sentence: the figure speaks of its own subject.
        for (const column of columns) reasons[column] = `risk.warnings.${code}`;
    }
    return {
        bestDay: finiteOrNull(shape?.best_realization),
        bestDayDate: singleValue(shape?.best_realization_date) ?? null,
        bestMonth: bestGain !== null && bestPeriod ? {gain: bestGain, ...bestPeriod} : null,
        rally: rallyGain === null ? null : {gain: rallyGain, from: rallyGain > 0 ? (rallyPeriod?.from ?? null) : null, to: rallyGain > 0 ? (rallyPeriod?.to ?? null) : null, days: finiteOrNull(fall?.largest_rally_duration_days)},
        omega: finiteOrNull(shape?.omega_ratio),
        positiveShare: finiteOrNull(shape?.positive_observation_share),
        downsideDeviation: finiteOrNull(shape?.downside_deviation),
        meanUp: finiteOrNull(shape?.mean_positive_return),
        meanDown: finiteOrNull(shape?.mean_negative_return),
        streak: streakDays !== null && streakPeriod ? {days: streakDays, ...streakPeriod} : null,
        averageDrawdown: finiteOrNull(fall?.average_drawdown),
        extremeDays: finiteOrNull(shape?.extreme_day_ratio),
        reasons,
    };
}

/** The codes of a result's warnings, whoever they name. */
export function warningCodes(result: RiskAnalyticResult | null): Set<string> {
    const warnings = (result as {warnings?: unknown} | null)?.warnings;
    const codes = new Set<string>();
    for (const warning of Array.isArray(warnings) ? warnings : []) if (typeof warning?.code === 'string') codes.add(warning.code);
    return codes;
}

/**
 * The figures of one scope (RN-18), with the volatility the semi-deviation is read against (Q23 a; the consultant,
 * 17/11/2026): the same historical KPI, so the two are of one series and comparable — «downward 9.8% · out of a 13.9%
 * swing». Not the lab's: its table has the volatility in its own column.
 */
export interface ScopeMoveFigures extends MoveFigures {
    /** The historical KPI's annualized volatility, the semi-deviation's term of comparison. */
    volatility: number | null;
}

/**
 * The figures of one scope (RN-18) — a portfolio, a broker, one asset — from the answers L1 already reads: the
 * historical KPI, the 30-day VaR (its best window) and the drawdown summary. Null when none of the three answered: the
 * block then has nothing to draw.
 */
export function buildMoveFigures(kpi: RiskAnalyticResult | null, monthlyVar: RiskAnalyticResult | null, drawdown: RiskAnalyticResult | null): ScopeMoveFigures | null {
    const shape = riskOutput(kpi, schemas.RiskKpiOutput);
    const month = riskOutput(monthlyVar, schemas.RiskVarCvarOutput);
    const fall = riskOutput(drawdown, schemas.RiskDrawdownOutput);
    if (!shape && !month && !fall) return null;
    return {volatility: finiteOrNull(shape?.volatility), ...readMoveFigures(shape, singleValue(month?.best_horizon) ?? null, fall, warningCodes(kpi))};
}

/** A translator as the components hand it: `$t`. */
export type MoveTranslator = (key: string, options?: {values?: Record<string, string | number>}) => string;

/** Gains against losses as the block writes it: two decimals, in the reader's language. */
export function omegaFigure(omega: number): string {
    return formatFixed(omega, 2);
}

/**
 * The block's headline (RN-18): gains against losses, and how long the largest rally lasted when it lasted at all.
 * Empty without gains against losses — the figure the sentence is about: an invented headline reads like a measured one.
 */
export function moveLead(figures: MoveFigures | null, t: MoveTranslator): string {
    if (figures?.omega == null) return '';
    const omega = omegaFigure(figures.omega);
    const days = figures.rally?.days;
    if (typeof days === 'number' && days > 0) return t('risk.levels.move.lead.both', {values: {omega, days: t('risk.levels.l1.daysCount', {values: {days}})}});
    return t('risk.levels.move.lead.omega', {values: {omega}});
}
