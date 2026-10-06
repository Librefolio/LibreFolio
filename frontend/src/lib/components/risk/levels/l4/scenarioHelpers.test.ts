import {describe, expect, it} from 'vitest';
import type {z} from 'zod';

import {schemas} from '$lib/api';
import type {RiskResultMetadata, RiskStressOutput} from '$lib/risk/riskTypes';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {degradedResults, resultErrorCodes, resultReasons, type RiskResultWarning} from '../levelHelpers';
import * as scenarioHelpers from './scenarioHelpers';
import {replayOptions, shockOptions, shockScenario, tornadoRows} from './scenarioHelpers';

/** A scenario catalogue entry, shaped like the API's. */
function entry(scenario: Record<string, unknown>) {
    return {scenario};
}

// Shaped on the real built-in YAML (`scenario_catalog/built_in/…`), including the
// fields a hand-written fixture forgets — `schema_version`, `description`,
// `editable`, `limits`. The generated Zod is strict, so a fixture that omits them
// parses to nothing and the helper looks broken when only the fixture was.
const REPLAY = entry({
    schema_version: 1,
    id: 'global_financial_crisis',
    kind: 'historical_replay',
    tags: ['crisis', 'equity', 'global'],
    name: {en: 'Global Financial Crisis', it: 'Crisi finanziaria globale'},
    description: {en: 'Peak-to-trough phase of the 2007-2009 crisis.', it: 'Fase dal massimo al minimo della crisi 2007-2009.'},
    defaults: {start: '2007-10-09', end: '2009-03-09', missing_history_policy: 'manual_proxy_or_exclude', composition_policy: 'current_buy_and_hold'},
    editable: {dates: true, missing_history_policy: true, proxies: true, exclusions: true},
    limits: {minimum_calendar_days: 1},
});

const SHOCK = entry({
    schema_version: 1,
    id: 'equity_crash',
    kind: 'hypothetical_shock',
    tags: ['equity', 'global'],
    name: {en: 'Equity crash', it: 'Crollo azionario'},
    description: {en: 'Editable asset-class shocks.', it: 'Shock modificabili per classe.'},
    allowed_dimensions: ['asset_class'],
    defaults: {dimension: 'asset_class', bucket_shocks: {STOCK: -0.35, ETF: -0.25}},
    editable: {dimension: false, bucket_shocks: true, manual_overrides: true},
    limits: {minimum_shock: -1, maximum_shock: 1, maximum_buckets: 100},
});

describe('replayOptions and shockOptions', () => {
    it('keeps only the scenarios of its own kind, from one mixed catalogue', () => {
        // The catalogue holds both kinds in one list. Parsing the *list* strictly
        // would reject every scenario because of the ones that are simply not
        // this kind — which reads as "no presets" rather than as a parse failure.
        const catalog = {items: [REPLAY, SHOCK]};
        expect(replayOptions(catalog, 'en').map((option) => option.value)).toEqual(['global_financial_crisis']);
        expect(shockOptions(catalog, 'en').map((option) => option.value)).toEqual(['equity_crash']);
    });

    it('speaks the reader’s language, and falls back rather than printing nothing', () => {
        expect(replayOptions({items: [REPLAY]}, 'it')[0].label).toBe('Crisi finanziaria globale');
        // A region tag is not a language: `it-CH` must still find `it`.
        expect(replayOptions({items: [REPLAY]}, 'it-CH')[0].label).toBe('Crisi finanziaria globale');
        // An unknown language falls back to English, never to the raw id.
        expect(replayOptions({items: [REPLAY]}, 'de')[0].label).toBe('Global Financial Crisis');
    });

    it('carries the period a preset means, so one click is a whole question', () => {
        const option = replayOptions({items: [REPLAY]}, 'en')[0];
        expect(option.start).toBe('2007-10-09');
        expect(option.end).toBe('2009-03-09');
    });

    it('says nothing at all for an absent catalogue instead of throwing', () => {
        expect(replayOptions(null, 'en')).toEqual([]);
        expect(shockOptions(undefined, 'en')).toEqual([]);
        expect(shockScenario(null, 'equity_crash')).toBeNull();
    });
});

describe('shockScenario', () => {
    it('reads the shocks a preset applies, so one click fills the whole form', () => {
        // This is the inversion D4 asks for: the reader picks a named scenario,
        // and the buckets are a *consequence* of that choice rather than twelve
        // fields nobody will ever fill in by hand.
        expect(shockScenario({items: [REPLAY, SHOCK]}, 'equity_crash')).toEqual({dimension: 'asset_class', bucketShocks: {STOCK: -0.35, ETF: -0.25}});
    });

    it('returns null for an id the catalogue does not hold', () => {
        expect(shockScenario({items: [SHOCK]}, 'nope')).toBeNull();
    });
});

describe('tornadoRows', () => {
    it('ranks buckets by damage, worst first', () => {
        const rows = tornadoRows({
            dimension: 'asset_class',
            configured_buckets: [
                {bucket_id: 'BOND', shock: -0.05, applied_asset_count: 1, asset_exposure_total: 0.3, contribution_return: -0.015},
                {bucket_id: 'STOCK', shock: -0.2, applied_asset_count: 2, asset_exposure_total: 0.6, contribution_return: -0.12},
                {bucket_id: 'CRYPTO', shock: 0.1, applied_asset_count: 1, asset_exposure_total: 0.1, contribution_return: 0.01},
            ],
        });
        expect(rows.map((row) => row.bucketId)).toEqual(['STOCK', 'BOND', 'CRYPTO']);
    });

    it('orders by signed value, not by magnitude', () => {
        // Sorting on `Math.abs` would put a large gain above a small loss and
        // interleave the two, destroying the single property the shape exists
        // for: that the eye travels down the damage.
        const rows = tornadoRows({
            dimension: 'asset_class',
            configured_buckets: [
                {bucket_id: 'UP', shock: 0.5, applied_asset_count: 1, asset_exposure_total: 0.5, contribution_return: 0.25},
                {bucket_id: 'DOWN', shock: -0.02, applied_asset_count: 1, asset_exposure_total: 0.5, contribution_return: -0.01},
            ],
        });
        expect(rows.map((row) => row.bucketId)).toEqual(['DOWN', 'UP']);
    });

    it('reads a bucket’s contribution, never its bare shock', () => {
        // The shock is what the reader typed; the contribution is what it did to
        // this portfolio. Showing the first would make a 1%-weight bucket look
        // exactly as damaging as a 60% one.
        const rows = tornadoRows({dimension: 'sector', configured_buckets: [{bucket_id: 'TECH', shock: -0.9, applied_asset_count: 1, asset_exposure_total: 0.01, contribution_return: -0.009}]});
        expect(rows[0].value).toBeCloseTo(-0.009, 10);
    });

    it('falls back to per-asset impacts when there is no dimension, as a replay has none', () => {
        const rows = tornadoRows({
            impacts: [
                {asset_id: 7, weight: 0.4, shock_return: -0.5, contribution_return: -0.2, impact_amount: '-8000.00'},
                {asset_id: 3, weight: 0.6, shock_return: -0.1, contribution_return: -0.06, impact_amount: '-2400.00'},
            ],
        });
        expect(rows.map((row) => row.assetId)).toEqual([7, 3]);
        expect(rows[0].amount).toBeCloseTo(-8000, 6);
    });

    it('drops a row it cannot place instead of drawing a bar at zero', () => {
        // A bar at zero is a statement ("this did nothing"); a missing number is
        // not. Inventing the first from the second is the whole failure mode.
        const rows = tornadoRows({dimension: 'asset_class', configured_buckets: [{bucket_id: 'STOCK', shock: -0.2, applied_asset_count: 0, asset_exposure_total: 0, contribution_return: null}]});
        expect(rows).toEqual([]);
    });

    it('keeps a replayed asset that came out flat: a zero is a figure, not an abstention (D151)', () => {
        // The other side of the rule above, for a replay. Since D376 the backend leaves the
        // excluded assets out of `impacts`, so every row that arrives was replayed — and one that
        // ended where it started says so with its 0%. Dropping the zero rows here to hide the old
        // excluded ones would erase that statement along with them.
        const rows = tornadoRows({
            impacts: [
                {asset_id: 7, weight: 0.4, shock_return: -0.1, contribution_return: -0.04, impact_amount: '-400.00'},
                {asset_id: 3, weight: 0.3, shock_return: 0, contribution_return: 0, impact_amount: '0.00'},
            ],
        });
        expect(rows.map((row) => [row.assetId, row.value, row.amount])).toEqual([
            [7, -0.04, -400],
            [3, 0, 0],
        ]);
    });

    it('says nothing for an absent or foreign payload', () => {
        expect(tornadoRows(null)).toEqual([]);
        expect(tornadoRows({kind: 'kpi', volatility: 0.1})).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// F3 — the historical replay block (developer's decision D372 of 02/10/2026)
// ---------------------------------------------------------------------------
//
// The engine excludes on its own every asset whose quotes do not cover the replay window
// (24/09), so the "exclude and retry" question `replayBlocker` used to read is gone, and with it
// the helper. What the block reads instead is *who* was left out, *why*, and *how much* of a
// weighted scope they held — from the audit when something was replayed, from the error's
// `details` when nothing was left — plus the verified common period the backend proposes.
//
// The new exports are read through the module namespace and typed by the contract written below,
// for two reasons. The file type-checks before they exist, so `svelte-check` stays at its floor
// while these tests are red; and a missing export fails its own tests at run time ("… is not a
// function") instead of failing the whole file at collection, which would also hide the scenario
// and tornado tests above. The names and shapes are the contract's, fixed by the Risk owner.

/** One asset the replay left out, as the block lists it. */
interface ReplayExcludedAsset {
    assetId: number;
    weight: number | null;
}

/** The assets left out for one reason. */
interface ReplayExclusionGroup {
    reason: string;
    assets: ReplayExcludedAsset[];
}

interface ReplayExclusions {
    groups: ReplayExclusionGroup[];
    count: number;
    weightTotal: number | null;
    treatment: 'zero_return_residual' | 'omitted_from_replay' | null;
}

interface ReplaySuggestion {
    start: string;
    end: string;
    recovers: number[];
}

/** What `scenarioHelpers` exports for F3, exactly as the contract names it. */
interface ReplayBlockContract {
    REPLAY_BLOCK_WARNING_CODES: readonly string[];
    REPLAY_EXCLUSION_REASON_ORDER: readonly string[];
    replayExclusions(result: RiskAnalyticResult | null | undefined): ReplayExclusions | null;
    replaySuggestion(result: RiskAnalyticResult | null | undefined): ReplaySuggestion | null;
    replayCoverageWarning(result: RiskAnalyticResult | null | undefined): RiskResultWarning | null;
    replayNothingLeft(result: RiskAnalyticResult | null | undefined): boolean;
    replaySectionView(result: RiskAnalyticResult | null | undefined): RiskAnalyticResult | null;
    formatReplayDate(iso: string, language: string): string;
    formatReplayShare(fraction: number, language: string): string;
}

const replayBlock = scenarioHelpers as unknown as ReplayBlockContract;

type ReplayAudit = z.infer<typeof schemas.RiskHistoricalReplayAudit>;
type AuditExcludedAsset = z.infer<typeof schemas.RiskHistoricalReplayExcludedAsset>;
type ExclusionReason = z.infer<typeof schemas.RiskHistoricalReplayExclusionReason>;
type ReplayErrorCode = z.infer<typeof schemas.RiskErrorCode>;

const BLOCK_CODES = ['historical_replay_assets_excluded', 'historical_replay_mostly_excluded'];
const REASON_ORDER = ['no_prices_in_window', 'starts_after_window_start', 'stale_at_window_start', 'stale_at_window_end', 'missing_fx', 'manual_exclusion'];

// ⚠️ Every figure and id below is invented; the shapes are the backend's (`stress.py::_historical`,
// `_replay_exclusion_warning`, `service.py::_with_warning_asset_names`).
const WINDOW = {start: '2020-02-03', end: '2020-03-31'};
const NOTHING_LEFT_MESSAGE = 'No asset in the replay scope covers the replay window';

/** The backend's English sentence of each per-reason exclusion warning, and its key. */
const EXCLUSION_WARNING: Record<ExclusionReason, {key: string; message: string}> = {
    manual_exclusion: {key: 'risk.warnings.historical_replay_excluded_manual', message: 'Historical replay omitted one or more assets using the declared exclusion policy.'},
    no_prices_in_window: {key: 'risk.warnings.historical_replay_excluded_no_prices', message: 'Historical replay excluded assets with no prices in the replay window.'},
    starts_after_window_start: {key: 'risk.warnings.historical_replay_excluded_starts_late', message: 'Historical replay excluded assets that start quoting after the replay window begins.'},
    stale_at_window_start: {key: 'risk.warnings.historical_replay_excluded_stale_at_start', message: 'Historical replay excluded assets quoted before the replay window but with no price in the 7 days before it begins.'},
    stale_at_window_end: {key: 'risk.warnings.historical_replay_excluded_stale_at_end', message: 'Historical replay excluded assets with no price in the last 7 days of the replay window.'},
    missing_fx: {key: 'risk.warnings.historical_replay_excluded_missing_fx', message: 'Historical replay excluded assets whose currency cannot be converted over the replay window.'},
};

function residual(assetId: number, reason: ExclusionReason, weight: number): AuditExcludedAsset {
    return {asset_id: assetId, reason, weight, treatment: 'zero_return_residual'};
}

function omitted(assetId: number, reason: ExclusionReason): AuditExcludedAsset {
    return {asset_id: assetId, reason, weight: null, treatment: 'omitted_from_replay'};
}

/** An audit as `stress.py` builds it: the total is the sum of the weights, zero when there are none. */
function audit(excluded: AuditExcludedAsset[], extra: Partial<ReplayAudit> = {}): ReplayAudit {
    const weights = excluded.map((item) => item.weight).filter((weight): weight is number => typeof weight === 'number');
    return {
        proxy_count: 0,
        proxy_assets: [],
        excluded_count: excluded.length,
        excluded_assets: excluded,
        excluded_weight_total: weights.reduce((total, weight) => total + weight, 0),
        missing_history_policy: 'manual_proxy_or_exclude',
        composition_policy: 'current_buy_and_hold',
        proxy_series_usage: 'returns_only',
        ...extra,
    };
}

function exclusionWarning(reason: ExclusionReason, assetIds: number[], treatment: 'zero_return_residual' | 'omitted_from_replay'): RiskResultWarning {
    return {
        code: 'historical_replay_assets_excluded',
        message: EXCLUSION_WARNING[reason].message,
        details: {asset_ids: assetIds, treatment, reason},
        degrades_result: true,
        message_i18n_key: EXCLUSION_WARNING[reason].key,
        message_params: {treatment, names: assetIds.map((assetId) => `#${assetId}`).join(', '), count: assetIds.length},
    };
}

/** The strong warning, emitted on a weighted scope past half of the value excluded. */
function coverageWarning(excludedWeightTotal: number): RiskResultWarning {
    const covered = Math.round((1 - excludedWeightTotal) * 10_000) / 10_000;
    return {
        code: 'historical_replay_mostly_excluded',
        message: `Historical replay describes only ${Math.round(covered * 100)}% of the portfolio: the rest is excluded.`,
        details: {excluded_weight_total: excludedWeightTotal, threshold: 0.5},
        degrades_result: true,
        message_i18n_key: 'risk.warnings.historical_replay_mostly_excluded',
        message_params: {covered},
    };
}

/** A warning that is about the replay's data, not about the block: it must stay on the section. */
const STALE_PRICES: RiskResultWarning = {
    code: 'data_quality_degraded',
    message: 'Risk result uses incomplete or carried-forward source data.',
    details: {status: 'carried_forward', cause: 'stale_prices', asset_ids: [7]},
    degrades_result: true,
    message_i18n_key: 'risk.warnings.data_quality_stale_prices',
    message_params: {days: 7, names: '#7', count: 1},
};

function replayMetadata(scope: 'portfolio' | 'asset_set', replayAudit: ReplayAudit): RiskResultMetadata {
    return {
        analyzed_range: WINDOW,
        frequency: 'daily',
        n_observations: 40,
        calendar_days: 58,
        coverage: 1,
        currency: 'EUR',
        scope,
        return_basis: 'current_composition_backtest',
        algorithm_version: 'test-replay-block',
        computed_at: '2026-10-02T10:00:00+00:00',
        historical_replay_audit: replayAudit,
    };
}

function replayOutput(scope: 'portfolio' | 'asset_set'): RiskStressOutput {
    const weighted = scope === 'portfolio';
    return {
        kind: 'stress',
        method: 'historical_replay',
        portfolio_return: weighted ? -0.02 : null,
        impact_amount: weighted ? '-200.00' : null,
        replay_range: WINDOW,
        impacts: [{asset_id: 7, shock_return: -0.1, contribution_return: weighted ? -0.02 : null, impact_amount: weighted ? '-200.00' : null, weight: weighted ? 0.2 : null, metadata_fallback: false}],
    };
}

/** A replay that ran: `partial` as soon as anything was left out or any warning degrades it. */
function replayed(scope: 'portfolio' | 'asset_set', replayAudit: ReplayAudit, warnings: RiskResultWarning[] = []): RiskAnalyticResult {
    const degraded = warnings.length > 0 || (replayAudit.excluded_assets ?? []).length > 0;
    return {instance_id: 'single-stress', analytic_code: 'stress', status: degraded ? 'partial' : 'ok', output: replayOutput(scope), metadata: replayMetadata(scope, replayAudit), warnings};
}

/**
 * A replay that did not run. `unavailable` and no output, as `schemas/risk.py` demands of it.
 *
 * `wrapped` sends the error inside a list: the generated client types the field as a value *or*
 * a list, and the helpers read it the way `firstError` / `singleValue` do.
 */
function refused(code: ReplayErrorCode, details: Record<string, unknown> | undefined, {wrapped = false, message = 'Refused'}: {wrapped?: boolean; message?: string} = {}): RiskAnalyticResult {
    const error = {code, message, ...(details === undefined ? {} : {details})};
    return {instance_id: 'single-stress', analytic_code: 'stress', status: 'unavailable', output: null, error: wrapped ? [error] : error};
}

/** Nothing left to replay: every asset excluded (`stress.py`, the `if not selected:` branch). */
function nothingLeft(details: Record<string, unknown>, {wrapped = false}: {wrapped?: boolean} = {}): RiskAnalyticResult {
    return refused('insufficient_history', details, {wrapped, message: NOTHING_LEFT_MESSAGE});
}

/** Freeze a payload all the way down, so a helper that writes into its input throws instead of passing. */
function deepFreeze<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const nested of Object.values(value as Record<string, unknown>)) deepFreeze(nested);
        Object.freeze(value);
    }
    return value;
}

describe('the replay block — its exports', () => {
    it('exports the F3 contract, and no longer the exclude-and-retry reader', () => {
        // One line per name, so a red lists exactly what is missing rather than the first absence.
        const functions = ['replayExclusions', 'replaySuggestion', 'replayCoverageWarning', 'replayNothingLeft', 'replaySectionView', 'formatReplayDate', 'formatReplayShare'];
        const exported = scenarioHelpers as unknown as Record<string, unknown>;
        expect(Object.fromEntries(functions.map((name) => [name, typeof exported[name]]))).toEqual(Object.fromEntries(functions.map((name) => [name, 'function'])));
        // The engine auto-excludes since 24/09: nothing is left for the reader to answer, so the
        // helper that read the question is gone, not merely unused.
        expect('replayBlocker' in scenarioHelpers, 'replayBlocker is still exported: the dead exclude-and-retry flow was not removed').toBe(false);
    });

    it('names the two warnings the block shows, and the order its reasons are listed in', () => {
        expect(replayBlock.REPLAY_BLOCK_WARNING_CODES).toEqual(BLOCK_CODES);
        expect(replayBlock.REPLAY_EXCLUSION_REASON_ORDER).toEqual(REASON_ORDER);
        // Every reason the API can send has a place in the order, and nothing else does: a reason
        // added to the backend enum must be placed here on purpose, not fall into "unknown".
        expect([...replayBlock.REPLAY_EXCLUSION_REASON_ORDER].sort()).toEqual([...schemas.RiskHistoricalReplayExclusionReason.options].sort());
    });
});

describe('replayExclusions — from the audit, when something was replayed', () => {
    it('groups the exclusions by reason, in the block’s order of reasons, whatever order they arrive in', () => {
        // Ids run against the reason order, and the backend's own enum order (manual first) is not
        // the block's: an answer in either of those orders fails here.
        const replayAudit = audit([
            residual(11, 'missing_fx', 0.05),
            residual(12, 'no_prices_in_window', 0.1),
            residual(13, 'starts_after_window_start', 0.2),
            residual(14, 'no_prices_in_window', 0.3),
            residual(15, 'manual_exclusion', 0.02),
            residual(16, 'stale_at_window_end', 0.1),
            residual(17, 'stale_at_window_start', 0.04),
        ]);

        expect(replayBlock.replayExclusions(replayed('portfolio', replayAudit))).toEqual({
            groups: [
                // Heaviest first inside a group.
                {
                    reason: 'no_prices_in_window',
                    assets: [
                        {assetId: 14, weight: 0.3},
                        {assetId: 12, weight: 0.1},
                    ],
                },
                {reason: 'starts_after_window_start', assets: [{assetId: 13, weight: 0.2}]},
                {reason: 'stale_at_window_start', assets: [{assetId: 17, weight: 0.04}]},
                {reason: 'stale_at_window_end', assets: [{assetId: 16, weight: 0.1}]},
                {reason: 'missing_fx', assets: [{assetId: 11, weight: 0.05}]},
                {reason: 'manual_exclusion', assets: [{assetId: 15, weight: 0.02}]},
            ],
            count: 7,
            // The audit's own total, as the backend weighed it.
            weightTotal: replayAudit.excluded_weight_total,
            treatment: 'zero_return_residual',
        });
    });

    it('reads an asset set as having no weights at all — no total, not a total of zero', () => {
        // `stress.py` pins `excluded_weight_total` to 0.0 on an unweighted scope; read as a number
        // it would print "0.0% of the scope" beside assets that were never weighed.
        const result = replayed('asset_set', audit([omitted(21, 'starts_after_window_start'), omitted(22, 'no_prices_in_window')]), [exclusionWarning('no_prices_in_window', [22], 'omitted_from_replay'), exclusionWarning('starts_after_window_start', [21], 'omitted_from_replay')]);

        expect(replayBlock.replayExclusions(result)).toEqual({
            groups: [
                {reason: 'no_prices_in_window', assets: [{assetId: 22, weight: null}]},
                {reason: 'starts_after_window_start', assets: [{assetId: 21, weight: null}]},
            ],
            count: 2,
            weightTotal: null,
            treatment: 'omitted_from_replay',
        });
    });

    it('says "omitted" as soon as one exclusion was omitted, beside one carried as residual', () => {
        // The backend assigns one treatment per scope; the stated rule is what decides the day it
        // does not. A total still exists, because one weight does.
        const result = replayed('asset_set', audit([residual(31, 'manual_exclusion', 0.03), omitted(32, 'no_prices_in_window')]));

        const exclusions = replayBlock.replayExclusions(result);
        expect(exclusions?.treatment).toBe('omitted_from_replay');
        expect(exclusions?.weightTotal).toBe(0.03);
        expect(exclusions?.count).toBe(2);
    });

    it('says nothing when the replay left nothing out', () => {
        expect(replayBlock.replayExclusions(replayed('portfolio', audit([])))).toBeNull();
        // `excluded_assets` is optional in the contract.
        const withoutList = audit([]);
        delete withoutList.excluded_assets;
        expect(replayBlock.replayExclusions(replayed('portfolio', withoutList))).toBeNull();
    });
});

describe('replayExclusions — from the error, when nothing was left to replay', () => {
    it('reads the error’s excluded assets, with the weights summed and no treatment', () => {
        const details = {
            excluded_asset_ids: [41, 42, 43],
            excluded_assets: [
                {asset_id: 41, reason: 'starts_after_window_start', weight: 0.25},
                {asset_id: 42, reason: 'no_prices_in_window', weight: 0.5},
                {asset_id: 43, reason: 'starts_after_window_start', weight: 0.125},
            ],
        };

        for (const wrapped of [false, true]) {
            const exclusions = replayBlock.replayExclusions(nothingLeft(details, {wrapped}));
            expect(exclusions, `wrapped=${wrapped}`).toEqual({
                groups: [
                    {reason: 'no_prices_in_window', assets: [{assetId: 42, weight: 0.5}]},
                    {
                        reason: 'starts_after_window_start',
                        assets: [
                            {assetId: 41, weight: 0.25},
                            {assetId: 43, weight: 0.125},
                        ],
                    },
                ],
                count: 3,
                // Nothing was replayed, so no treatment was applied to anything.
                weightTotal: 0.875,
                treatment: null,
            });
        }
    });

    it('has no total when no weight was named (an asset set)', () => {
        const exclusions = replayBlock.replayExclusions(
            nothingLeft({
                excluded_asset_ids: [51, 52],
                excluded_assets: [
                    {asset_id: 51, reason: 'missing_fx', weight: null},
                    {asset_id: 52, reason: 'missing_fx', weight: null},
                ],
            }),
        );

        expect(exclusions).toEqual({
            groups: [
                {
                    reason: 'missing_fx',
                    assets: [
                        {assetId: 51, weight: null},
                        {assetId: 52, weight: null},
                    ],
                },
            ],
            count: 2,
            weightTotal: null,
            treatment: null,
        });
    });

    it('orders one group’s assets by weight, heaviest first, ties and the unweighted by id', () => {
        const exclusions = replayBlock.replayExclusions(
            nothingLeft({
                excluded_asset_ids: [18, 19, 20, 21, 23],
                excluded_assets: [
                    {asset_id: 18, reason: 'no_prices_in_window', weight: null},
                    {asset_id: 19, reason: 'no_prices_in_window', weight: 0.1},
                    {asset_id: 20, reason: 'no_prices_in_window', weight: null},
                    {asset_id: 21, reason: 'no_prices_in_window', weight: 0.1},
                    {asset_id: 23, reason: 'no_prices_in_window', weight: 0.3},
                ],
            }),
        );

        expect(exclusions?.groups).toEqual([
            {
                reason: 'no_prices_in_window',
                assets: [
                    {assetId: 23, weight: 0.3},
                    {assetId: 19, weight: 0.1},
                    {assetId: 21, weight: 0.1},
                    {assetId: 18, weight: null},
                    {assetId: 20, weight: null},
                ],
            },
        ]);
        expect(exclusions?.weightTotal).toBeCloseTo(0.5, 12);
    });

    it('lists a reason it does not know after the known ones, in the order it first arrives', () => {
        const exclusions = replayBlock.replayExclusions(
            nothingLeft({
                excluded_asset_ids: [61, 62, 63, 64, 65],
                excluded_assets: [
                    {asset_id: 61, reason: 'delisted', weight: null},
                    {asset_id: 62, reason: 'no_prices_in_window', weight: null},
                    {asset_id: 63, reason: 'halted', weight: null},
                    {asset_id: 64, reason: 'delisted', weight: null},
                    {asset_id: 65, reason: 'missing_fx', weight: null},
                ],
            }),
        );

        expect(exclusions?.groups.map((group) => group.reason)).toEqual(['no_prices_in_window', 'missing_fx', 'delisted', 'halted']);
        expect(exclusions?.groups.find((group) => group.reason === 'delisted')?.assets).toEqual([
            {assetId: 61, weight: null},
            {assetId: 64, weight: null},
        ]);
        expect(exclusions?.count).toBe(5);
    });

    it('puts every asset under one unknown reason when the error names only their ids', () => {
        // A backend from before D372 sends the ids alone; they are still the assets left out.
        expect(replayBlock.replayExclusions(nothingLeft({excluded_asset_ids: [71, 72]}))).toEqual({
            groups: [
                {
                    reason: 'unknown',
                    assets: [
                        {assetId: 71, weight: null},
                        {assetId: 72, weight: null},
                    ],
                },
            ],
            count: 2,
            weightTotal: null,
            treatment: null,
        });
    });

    it('says nothing for any other refusal, or for no answer at all', () => {
        expect(replayBlock.replayExclusions(null)).toBeNull();
        expect(replayBlock.replayExclusions(undefined)).toBeNull();
        expect(replayBlock.replayExclusions(refused('execution_timeout', undefined))).toBeNull();
        // Refused for want of history, but not because the window left everything out.
        expect(replayBlock.replayExclusions(refused('insufficient_history', undefined, {message: 'Historical replay has no observations in the requested range'}))).toBeNull();
        expect(replayBlock.replayExclusions(refused('insufficient_history', {excluded_asset_ids: []}))).toBeNull();
    });
});

describe('replaySuggestion', () => {
    it('reads the verified proposal off the audit', () => {
        const result = replayed('asset_set', audit([omitted(13, 'starts_after_window_start'), omitted(17, 'stale_at_window_start')], {suggested_range: {start: '2020-02-17', end: '2020-03-31'}, suggested_range_recovers: [13, 17]}));

        expect(replayBlock.replaySuggestion(result)).toEqual({start: '2020-02-17', end: '2020-03-31', recovers: [13, 17]});
    });

    it('reads it off the error when nothing was left, whichever shape the error came in', () => {
        const details = {excluded_asset_ids: [41], excluded_assets: [{asset_id: 41, reason: 'starts_after_window_start', weight: null}], suggested_range: {start: '2020-03-02', end: '2020-03-31'}, suggested_range_recovers: [41]};

        expect(replayBlock.replaySuggestion(nothingLeft(details))).toEqual({start: '2020-03-02', end: '2020-03-31', recovers: [41]});
        expect(replayBlock.replaySuggestion(nothingLeft(details, {wrapped: true}))).toEqual({start: '2020-03-02', end: '2020-03-31', recovers: [41]});
    });

    it('offers nothing without a proposal, or with one that brings nothing back', () => {
        expect(replayBlock.replaySuggestion(replayed('asset_set', audit([omitted(13, 'no_prices_in_window')])))).toBeNull();
        expect(replayBlock.replaySuggestion(replayed('asset_set', audit([omitted(13, 'starts_after_window_start')], {suggested_range: {start: '2020-02-17', end: '2020-03-31'}, suggested_range_recovers: []})))).toBeNull();
        expect(replayBlock.replaySuggestion(nothingLeft({excluded_asset_ids: [41]}))).toBeNull();
        expect(replayBlock.replaySuggestion(nothingLeft({excluded_asset_ids: [41], suggested_range: {start: '2020-03-02', end: '2020-03-31'}, suggested_range_recovers: []}))).toBeNull();
        expect(replayBlock.replaySuggestion(refused('execution_timeout', undefined))).toBeNull();
        expect(replayBlock.replaySuggestion(null)).toBeNull();
    });
});

describe('replayCoverageWarning', () => {
    it('picks the strong warning out of the others', () => {
        const coverage = coverageWarning(0.6);
        const result = replayed('portfolio', audit([residual(12, 'no_prices_in_window', 0.6)]), [coverage, exclusionWarning('no_prices_in_window', [12], 'zero_return_residual'), STALE_PRICES]);

        expect(replayBlock.replayCoverageWarning(result)).toEqual(coverage);
    });

    it('is null when the replay covers enough, or when there is no answer', () => {
        expect(replayBlock.replayCoverageWarning(replayed('portfolio', audit([residual(12, 'no_prices_in_window', 0.1)]), [exclusionWarning('no_prices_in_window', [12], 'zero_return_residual')]))).toBeNull();
        expect(replayBlock.replayCoverageWarning(null)).toBeNull();
    });
});

describe('replayNothingLeft', () => {
    it('recognises the refusal of a window that left every asset out, in either shape', () => {
        expect(replayBlock.replayNothingLeft(nothingLeft({excluded_asset_ids: [41, 42]}))).toBe(true);
        expect(replayBlock.replayNothingLeft(nothingLeft({excluded_asset_ids: [41, 42]}, {wrapped: true}))).toBe(true);
    });

    it('does not mistake any other refusal for it', () => {
        // Refused for want of history, with no ids: "no observations in the requested range".
        expect(replayBlock.replayNothingLeft(refused('insufficient_history', undefined))).toBe(false);
        expect(replayBlock.replayNothingLeft(refused('insufficient_history', {excluded_asset_ids: []}))).toBe(false);
        expect(replayBlock.replayNothingLeft(refused('insufficient_history', {excluded_asset_ids: 41}))).toBe(false);
        expect(replayBlock.replayNothingLeft(refused('execution_timeout', {excluded_asset_ids: [41]}))).toBe(false);
        expect(replayBlock.replayNothingLeft({...nothingLeft({excluded_asset_ids: [41]}), status: 'failed'})).toBe(false);
        expect(replayBlock.replayNothingLeft(replayed('portfolio', audit([residual(12, 'no_prices_in_window', 0.1)])))).toBe(false);
        expect(replayBlock.replayNothingLeft(null)).toBe(false);
        expect(replayBlock.replayNothingLeft(undefined)).toBe(false);
    });
});

describe('replaySectionView — what the section reads once the block shows the rest', () => {
    it('is null for no answer', () => {
        expect(replayBlock.replaySectionView(null)).toBeNull();
        expect(replayBlock.replaySectionView(undefined)).toBeNull();
    });

    it('takes the two block warnings off the section and keeps every other, without touching its input', () => {
        const coverage = coverageWarning(0.55);
        const exclusions = [exclusionWarning('no_prices_in_window', [12], 'zero_return_residual'), exclusionWarning('starts_after_window_start', [13], 'zero_return_residual')];
        const input = replayed('portfolio', audit([residual(12, 'no_prices_in_window', 0.3), residual(13, 'starts_after_window_start', 0.25)]), [coverage, ...exclusions, STALE_PRICES]);
        const snapshot = structuredClone(input);
        // The section's own reading of the answer as it arrives — the positive control: all four
        // sentences are there to be removed.
        expect(resultReasons([input]).map((reason) => reason.message)).toEqual([coverage.message, ...exclusions.map((warning) => warning.message), STALE_PRICES.message]);

        const view = replayBlock.replaySectionView(deepFreeze(input));

        expect(view, 'the view must be a new object, so the block keeps reading the whole answer').not.toBe(input);
        expect(input, 'the answer itself was changed: the block would lose what it shows').toEqual(snapshot);
        // Everything else unchanged: status, output, metadata and the rest.
        expect({...view, error: view?.error ?? null}).toEqual({...snapshot, warnings: [STALE_PRICES], error: snapshot.error ?? null});
        // Read through the helpers the mounts use: the block's sentences are gone from the reasons,
        // the data warning stays, and the status line still says "partial".
        expect(resultReasons([view]).map((reason) => reason.message)).toEqual([STALE_PRICES.message]);
        expect(resultErrorCodes([view])).toEqual([]);
        expect(degradedResults([view])).toEqual([{instanceId: 'single-stress', code: 'stress', status: 'partial'}]);
    });

    it('takes a nothing-left refusal off the section’s errors, which keeps its status line', () => {
        for (const wrapped of [false, true]) {
            const input = nothingLeft(
                {
                    excluded_asset_ids: [41, 42],
                    excluded_assets: [
                        {asset_id: 41, reason: 'starts_after_window_start', weight: 0.6},
                        {asset_id: 42, reason: 'no_prices_in_window', weight: 0.4},
                    ],
                },
                {wrapped},
            );
            const snapshot = structuredClone(input);
            // Positive control: the section would otherwise say "insufficient history".
            expect(resultErrorCodes([input])).toEqual(['insufficient_history']);

            const view = replayBlock.replaySectionView(deepFreeze(input));

            expect(view, `wrapped=${wrapped}`).not.toBe(input);
            expect(input).toEqual(snapshot);
            expect(view?.error, 'the nothing-left refusal is the block’s to explain, not the section’s').toBeNull();
            expect({...view, error: null}).toEqual({...snapshot, error: null, warnings: view?.warnings});
            expect(view?.status).toBe('unavailable');
            expect(resultErrorCodes([view])).toEqual([]);
            expect(degradedResults([view])).toEqual([{instanceId: 'single-stress', code: 'stress', status: 'unavailable'}]);
        }
    });

    it.each([
        ['a timeout', refused('execution_timeout', undefined, {message: 'Risk analytic exceeded its time limit'})],
        ['a parameter error', refused('invalid_parameters', {asset_id: 1, return_source_asset_id: 3, reason: 'missing_fx'})],
        ['a history refusal that names no asset', refused('insufficient_history', undefined, {message: 'Historical replay has no observations in the requested range'})],
        ['a history refusal with an empty list', refused('insufficient_history', {excluded_asset_ids: []})],
    ])('keeps %s on the section, where it is the only explanation there is', (_label, input) => {
        const code = resultErrorCodes([input]);
        expect(code).toHaveLength(1);

        const view = replayBlock.replaySectionView(deepFreeze(input));

        expect(view?.error).toEqual(input.error);
        expect(resultErrorCodes([view])).toEqual(code);
        expect(degradedResults([view])).toEqual(degradedResults([input]));
    });
});

describe('formatReplayDate and formatReplayShare', () => {
    // Pinned against `Intl` itself, never against a written month: the formatters are a choice of
    // options, and the words belong to the platform's locale data.
    const LANGUAGES = ['en', 'it'] as const;

    function intlDate(iso: string, language: string): string {
        return new Intl.DateTimeFormat(language, {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'}).format(new Date(`${iso}T00:00:00Z`));
    }

    function intlShare(fraction: number, language: string): string {
        return new Intl.NumberFormat(language, {style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1}).format(fraction);
    }

    it.each(LANGUAGES)('writes a day the way Intl does in %s, on that calendar day whatever the zone', (language) => {
        // New Year's Day is the trap: parsed at local midnight east of UTC, it is formatted as the
        // last day of the year before.
        for (const iso of ['2020-01-01', '2020-03-09', '2008-12-31']) {
            expect(replayBlock.formatReplayDate(iso, language), `${iso} in ${language}`).toBe(intlDate(iso, language));
        }
    });

    it.each(LANGUAGES)('writes a share the way Intl does in %s, with one decimal', (language) => {
        for (const fraction of [0, 0.05, 0.125, 0.4567, 1]) {
            expect(replayBlock.formatReplayShare(fraction, language), `${fraction} in ${language}`).toBe(intlShare(fraction, language));
        }
    });

    it('follows the language it is given rather than a fixed one', () => {
        // The pins above would agree with a formatter that ignored its argument, were the two
        // languages to read alike; they do not, which is what makes the argument observable.
        expect(intlDate('2020-03-09', 'it')).not.toBe(intlDate('2020-03-09', 'en'));
        expect(intlShare(0.125, 'it')).not.toBe(intlShare(0.125, 'en'));
        expect(replayBlock.formatReplayDate('2020-03-09', 'it')).not.toBe(replayBlock.formatReplayDate('2020-03-09', 'en'));
        expect(replayBlock.formatReplayShare(0.125, 'it')).not.toBe(replayBlock.formatReplayShare(0.125, 'en'));
    });
});
