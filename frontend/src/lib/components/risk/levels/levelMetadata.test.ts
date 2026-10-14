import {describe, expect, it} from 'vitest';

import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {levelMetadata, translateOrRaw} from './levelMetadata';

/**
 * A metadata payload the generated Zod schema actually accepts.
 *
 * `riskMetadata` runs `safeParse` and returns **null** on failure, so a fixture
 * missing one required field produces an empty result rather than an error —
 * and every assertion written against it would pass while measuring nothing.
 * Required here: `analyzed_range`, `n_observations`, `calendar_days`,
 * `coverage`, `currency`, `return_basis`, `algorithm_version`, `computed_at` —
 * the last two discovered the hard way, by the first run of this file returning
 * empty rows rather than an error.
 */
function meta(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        analyzed_range: {start: '2025-01-02', end: '2025-06-30'},
        n_observations: 93,
        calendar_days: 180,
        coverage: 0.98,
        currency: 'EUR',
        return_basis: 'twrr',
        annualization_factor: 252,
        algorithm_version: 'test-1',
        computed_at: '2025-07-01T00:00:00Z',
        ...overrides,
    };
}

function withMeta(code: string, instanceId: string, metadata: unknown): RiskAnalyticResult {
    return {analytic_code: code, instance_id: instanceId, status: 'ok', output: {}, metadata} as unknown as RiskAnalyticResult;
}

describe('levelMetadata', () => {
    // The ordinary case, and the one the reader is meant to see: every analytic
    // in the level measured the same window, so the level has one provenance,
    // not three.
    it('collapses analytics that agree into a single row, naming each of them', () => {
        const rows = levelMetadata([withMeta('historical_var', 'day', meta()), withMeta('drawdown_summary', 'dd', meta())]);
        expect(rows).toHaveLength(1);
        expect(rows[0].observations).toBe(93);
        expect(rows[0].coverage).toBe(0.98);
        expect(rows[0].returnBasis).toBe('twrr');
        expect(rows[0].codes).toEqual(['historical_var', 'drawdown_summary']);
    });

    // The case a representative would have hidden. Picking one result's metadata
    // would show 93 observations over figures partly computed from 40 — a window
    // presented as covering numbers it does not cover, which reads as a fact
    // rather than as a missing one.
    it('splits when two analytics disagree about the window', () => {
        const rows = levelMetadata([withMeta('historical_var', 'day', meta()), withMeta('historical_kpi', 'kpi', meta({n_observations: 40}))]);
        expect(rows).toHaveLength(2);
        expect(rows.map((row) => row.observations)).toEqual([93, 40]);
        expect(rows.map((row) => row.codes)).toEqual([['historical_var'], ['historical_kpi']]);
    });

    // One analytic asked twice — L1 asks `historical_var` for a daily and a
    // monthly horizon — reports its window once, not twice. A code repeated in
    // the list would read as a rendering fault.
    it('names one analytic once even when it answered twice', () => {
        const rows = levelMetadata([withMeta('historical_var', 'day', meta()), withMeta('historical_var', 'month', meta())]);
        expect(rows).toHaveLength(1);
        expect(rows[0].codes).toEqual(['historical_var']);
    });

    // `riskMetadata` parses, and a payload that fails validation comes back null.
    // Skipping it is the point: a half-parsed row would publish a window nobody
    // measured.
    it('says nothing for metadata the contract rejects', () => {
        const rows = levelMetadata([withMeta('historical_var', 'day', meta({currency: undefined}))]);
        expect(rows).toEqual([]);
    });

    it('ignores results that carry no metadata at all', () => {
        expect(levelMetadata([withMeta('historical_var', 'day', null), null, undefined])).toEqual([]);
    });

    // `annualization_factor` is the one optional figure of the four, so it is the
    // one that can arrive absent or unusable. A `NaN` rendered through
    // `toFixed(2)` prints "NaN" beside three real numbers.
    it('drops an annualization factor that is not a usable number', () => {
        const rows = levelMetadata([withMeta('historical_var', 'day', meta({annualization_factor: null}))]);
        expect(rows).toHaveLength(1);
        expect(rows[0].annualizationFactor).toBeNull();
        expect(rows[0].observations).toBe(93);
    });
});

describe('translateOrRaw', () => {
    const catalogue: Record<string, string> = {'risk.returnBasis.twrr': 'Time-weighted return'};
    const translate = (key: string): string => catalogue[key] ?? key;

    it('words a basis the catalogue knows', () => {
        expect(translateOrRaw('risk.returnBasis', 'twrr', translate)).toBe('Time-weighted return');
    });

    // `RiskResultFrame:108` builds this same key with no guard, which is the
    // defect `levelHelpers` records in prose: an unseen value prints its own key.
    // Falling back to the backend token loses the wording and keeps the meaning —
    // the difference between a degraded answer and a broken screen.
    it('falls back to the raw value, never to the key', () => {
        const rendered = translateOrRaw('risk.returnBasis', 'a_basis_added_next_year', translate);
        expect(rendered).toBe('a_basis_added_next_year');
        expect(rendered).not.toContain('risk.returnBasis.');
    });
});
