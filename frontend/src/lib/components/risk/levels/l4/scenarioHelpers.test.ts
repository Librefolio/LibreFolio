import {describe, expect, it} from 'vitest';

import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {replayBlocker, replayOptions, shockOptions, shockScenario, tornadoRows} from './scenarioHelpers';

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

function failed(code: string, details: Record<string, unknown>): RiskAnalyticResult {
    return {analytic_code: 'stress', instance_id: 'replay', status: 'unavailable', output: null, error: {code, message: 'x', details}} as unknown as RiskAnalyticResult;
}

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

    it('says nothing for an absent or foreign payload', () => {
        expect(tornadoRows(null)).toEqual([]);
        expect(tornadoRows({kind: 'kpi', volatility: 0.1})).toEqual([]);
    });
});

describe('replayBlocker', () => {
    it('reads the asset the server is asking about', () => {
        const blocker = replayBlocker(failed('insufficient_history', {asset_id: 42, return_source_asset_id: 42, reason: 'insufficient_history'}));
        expect(blocker).toEqual({assetId: 42, reason: 'insufficient_history', proxyAtFault: false});
    });

    it('tells a failing proxy apart from a failing holding', () => {
        // The two need opposite answers: a bad proxy has to be *changed*, while a
        // holding with no history has to be excluded or given one. Reporting both
        // as "needs a proxy" would send the reader round in a circle.
        const blocker = replayBlocker(failed('invalid_parameters', {asset_id: 42, return_source_asset_id: 9, reason: 'insufficient_history'}));
        expect(blocker?.proxyAtFault).toBe(true);
    });

    it('offers nothing for a failure the reader cannot answer', () => {
        expect(replayBlocker(failed('execution_timeout', {asset_id: 42}))).toBeNull();
        expect(replayBlocker(failed('insufficient_history', {}))).toBeNull();
        expect(replayBlocker(null)).toBeNull();
    });

    it('offers nothing for a replay that succeeded', () => {
        expect(replayBlocker({analytic_code: 'stress', instance_id: 'replay', status: 'ok', output: {kind: 'stress'}} as unknown as RiskAnalyticResult)).toBeNull();
    });
});
