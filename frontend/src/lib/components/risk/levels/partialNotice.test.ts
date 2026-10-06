/**
 * partialNotice — the pure half of the one notice above the risk levels.
 *
 * Developer's decision of 24/09/2026: what came back partial, and every warning
 * worth reading, is disclosed **once**, at the top of the four-level panel; under
 * L1–L3 only what did not come back at all stays. These tests pin the pieces the
 * panel composes, and the two ways a composition like that miscounts:
 *
 *   - **by code instead of by instance** — L1 asks `historical_var` twice (a day
 *     and a month), so a notice keyed by code would name one horizon and lose
 *     the other while reading perfectly plausibly;
 *   - **by slice instead of by measurement** — `historical_kpi` feeds both L1 and
 *     L3, so a notice built from the concatenated slices would count its warning
 *     twice, as if two measurements had carried it.
 *
 * Synthetic results only; sentences a translator words are resolved from the
 * shipped catalogue, never written down.
 */
import {beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';

import {setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {DAILY_VAR_INSTANCE, MONTHLY_VAR_INSTANCE} from '../riskAnalysisHelpers';
import type {ResultHealth, ResultReason} from './levelHelpers';
import {analyticNameKey, levelErrorHealth, partialNotice, uniqueByInstance} from './partialNotice';

type Status = 'ok' | 'partial' | 'unavailable' | 'failed';
type Warning = NonNullable<RiskAnalyticResult['warnings']>[number];

const KPI = 'base-historical-historical_kpi';
const CORRELATION = 'base-historical-correlation';
const DRAWDOWN = 'base-historical-drawdown_summary';

/** The labels the panel passes for L1's two VaR horizons (`RiskLevelsPanel`'s `L1_LABELS`). */
const L1_LABELS = {[DAILY_VAR_INSTANCE]: 'risk.levels.l1.rows.day', [MONTHLY_VAR_INSTANCE]: 'risk.levels.l1.rows.month'};

const VAR_SENTENCE = 'Synthetic: only 41 of the 60 sessions had a usable close at this horizon.';
const DRAWDOWN_SENTENCE = 'Synthetic: the peak-to-trough window was truncated at the start of history.';
const CORRELATION_SENTENCE = 'Synthetic: two pairs had too few overlapping sessions.';
const KPI_SENTENCE = 'Synthetic: the risk-free series had gaps and was carried forward.';

/** A result shaped like the API's; only `ok` and `partial` may carry an output. */
function result(instanceId: string, code: string, status: Status, warnings: Warning[] = []): RiskAnalyticResult {
    return {instance_id: instanceId, analytic_code: code, status, output: status === 'ok' || status === 'partial' ? {kind: 'synthetic'} : null, warnings} as unknown as RiskAnalyticResult;
}

function warning(code: string, message: string): Warning {
    return {code, message};
}

/** The camelCase leaves of `risk.analytics.*` that carry a `name`, read off `en.json`. */
function catalogueAnalyticNames(): string[] {
    return Object.entries(en.risk.analytics as Record<string, unknown>)
        .filter(([, entry]) => entry !== null && typeof entry === 'object' && typeof (entry as Record<string, unknown>).name === 'string')
        .map(([leaf]) => leaf);
}

describe('uniqueByInstance', () => {
    it('keeps the first result of each instance, in order, and drops the missing ones', () => {
        const kpi = result(KPI, 'historical_kpi', 'ok');
        // The same instance again, as L3's slice hands it back after L1's: a different
        // object with a different status, so which one survived is observable.
        const kpiAgain = result(KPI, 'historical_kpi', 'partial');
        const correlation = result(CORRELATION, 'correlation', 'partial');
        const day = result(DAILY_VAR_INSTANCE, 'historical_var', 'ok');
        const month = result(MONTHLY_VAR_INSTANCE, 'historical_var', 'ok');

        const unique = uniqueByInstance([kpi, null, correlation, undefined, day, kpiAgain, month]);

        expect(unique, 'not one entry per instance in arrival order: a repeated slice was counted twice, a missing result survived, or two horizons sharing a code collapsed').toEqual([kpi, correlation, day, month]);
        expect(unique[0], 'a later copy of an instance replaced the first one').toBe(kpi);
    });

    it('returns nothing for an input with nothing in it', () => {
        expect(uniqueByInstance([])).toEqual([]);
        expect(uniqueByInstance([null, undefined])).toEqual([]);
    });
});

describe('partialNotice', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('names only what came back partial: not the unavailable, not the failed, not the whole', () => {
        const notice = partialNotice([result(DRAWDOWN, 'drawdown_summary', 'ok'), result(CORRELATION, 'correlation', 'partial'), result(KPI, 'historical_kpi', 'unavailable'), result('base-current_composition-risk_contribution', 'risk_contribution', 'failed')]);

        expect(notice.partial, 'a measurement that did not come back at all was named as partial: its status belongs under its level, with its error').toStrictEqual([{instanceId: CORRELATION, code: 'correlation', status: 'partial'}]);
    });

    it('tells the two VaR horizons apart by instance, each with its own label', () => {
        const notice = partialNotice([result(DAILY_VAR_INSTANCE, 'historical_var', 'partial'), result(MONTHLY_VAR_INSTANCE, 'historical_var', 'partial'), result(CORRELATION, 'correlation', 'partial')], undefined, L1_LABELS);

        expect(notice.partial, 'the day and the month were not named separately, or lost the label that tells them apart').toStrictEqual([
            {instanceId: DAILY_VAR_INSTANCE, code: 'historical_var', status: 'partial', label: 'risk.levels.l1.rows.day'},
            {instanceId: MONTHLY_VAR_INSTANCE, code: 'historical_var', status: 'partial', label: 'risk.levels.l1.rows.month'},
            {instanceId: CORRELATION, code: 'correlation', status: 'partial'},
        ]);
    });

    it('counts a measurement the input repeats once, and its warning once', () => {
        // `historical_kpi` is in L1's slice and in L3's: the panel concatenates both.
        const kpi = result(KPI, 'historical_kpi', 'partial', [warning('risk_free_carried_forward', KPI_SENTENCE)]);

        const notice = partialNotice([kpi, result(CORRELATION, 'correlation', 'partial', [warning('low_pair_coverage', CORRELATION_SENTENCE)]), kpi]);

        expect(
            notice.partial.map((entry: ResultHealth) => entry.instanceId),
            'a measurement read by two levels was named twice',
        ).toEqual([KPI, CORRELATION]);
        expect(notice.reasons, 'a warning on a measurement read by two levels was counted as if two measurements had carried it').toStrictEqual([
            {key: `risk_free_carried_forward:${KPI_SENTENCE}`, message: KPI_SENTENCE, occurrences: 1},
            {key: `low_pair_coverage:${CORRELATION_SENTENCE}`, message: CORRELATION_SENTENCE, occurrences: 1},
        ]);
    });

    it('says one sentence once across measurements, counts the measurements that carried it, and keeps warnings on whole results', () => {
        // All three `ok`: nothing is partial, and the sentences are still worth reading.
        const notice = partialNotice(
            [result(DAILY_VAR_INSTANCE, 'historical_var', 'ok', [warning('sparse_history', VAR_SENTENCE)]), result(MONTHLY_VAR_INSTANCE, 'historical_var', 'ok', [warning('sparse_history', VAR_SENTENCE)]), result(DRAWDOWN, 'drawdown_summary', 'ok', [warning('truncated_window', DRAWDOWN_SENTENCE)])],
            undefined,
            L1_LABELS,
        );

        expect(notice.partial).toStrictEqual([]);
        expect(notice.reasons, 'the sentence both horizons carried was not shown once and counted twice, or a warning on a whole result was filtered out').toStrictEqual([
            {key: `sparse_history:${VAR_SENTENCE}`, message: VAR_SENTENCE, occurrences: 2},
            {key: `truncated_window:${DRAWDOWN_SENTENCE}`, message: DRAWDOWN_SENTENCE, occurrences: 1},
        ]);
    });

    it('words a keyed warning through the translator it is given, and keeps the backend sentence without one', () => {
        const params = {count: 2, names: 'Synthetic Holding A, Synthetic Holding B'};
        const backendSentence = 'Some requested assets are not held in the selected portfolio scope and were ignored.';
        const keyed: Warning = {code: 'slice_assets_not_held', message: backendSentence, message_i18n_key: 'risk.warnings.slice_assets_not_held', message_params: params};
        const input = [result(KPI, 'historical_kpi', 'partial', [keyed])];

        const worded = get(_)('risk.warnings.slice_assets_not_held', {values: params});
        expect(worded, 'guard: the catalogue sentence reads like the backend one, so which branch rendered would have no answer').not.toBe(backendSentence);
        expect(worded, 'guard: the catalogue sentence did not format with these values').not.toContain('{');

        expect(
            partialNotice(input, get(_)).reasons.map((reason: ResultReason) => reason.message),
            'the translator was not used for a warning whose key the catalogue ships',
        ).toEqual([worded]);
        expect(
            partialNotice(input).reasons.map((reason: ResultReason) => reason.message),
            'without a translator the backend sentence was not kept verbatim',
        ).toEqual([backendSentence]);
    });

    it('hands each reason on with the cause and the assets the notice picks its tone and draws its badges from', () => {
        // The exclusion as the backend sends it: one `assets_excluded` warning per cause, the
        // cause and the ids in `details`, repeated on every result read off the scope's own series.
        const key = 'risk.warnings.assets_excluded_no_price_source';
        const params = {count: 2, names: 'Synthetic Holding A, Synthetic Holding B'};
        const excluded: Warning = {code: 'assets_excluded', message: 'One or more scope assets were excluded from risk calculations.', message_i18n_key: key, message_params: params, details: {asset_ids: [41, 42], reason: 'no_price_source'}};

        const worded = get(_)(key, {values: params});
        expect(worded, 'guard: the key does not resolve through svelte-i18n').not.toBe(key);
        expect(worded, 'guard: the catalogue sentence did not format with these values').not.toContain('{');

        const notice = partialNotice([result(CORRELATION, 'correlation', 'partial', [excluded]), result('base-current_composition-risk_contribution', 'risk_contribution', 'partial', [excluded])], get(_));

        expect(notice.reasons, 'the notice lost the cause (its tone) or the assets (its badges) on the way from the warnings').toStrictEqual([{key: `assets_excluded:${worded}`, message: worded, occurrences: 2, reason: 'no_price_source', assetIds: [41, 42]}]);
    });

    it('has nothing to disclose for a wave that came back whole and silent', () => {
        expect(partialNotice([result(KPI, 'historical_kpi', 'ok'), result(CORRELATION, 'correlation', 'ok'), null])).toStrictEqual({partial: [], reasons: []});
    });
});

describe('levelErrorHealth', () => {
    it('keeps only what did not come back at all, in order, labels included', () => {
        const health: ResultHealth[] = [
            {instanceId: CORRELATION, code: 'correlation', status: 'partial'},
            {instanceId: DAILY_VAR_INSTANCE, code: 'historical_var', status: 'unavailable', label: 'risk.levels.l1.rows.day'},
            {instanceId: KPI, code: 'historical_kpi', status: 'failed'},
            {instanceId: MONTHLY_VAR_INSTANCE, code: 'historical_var', status: 'partial', label: 'risk.levels.l1.rows.month'},
        ];

        expect(levelErrorHealth(health), 'a partial measurement stayed under its level, where the notice above now names it').toStrictEqual([health[1], health[2]]);
    });

    it('leaves a level with nothing to say when everything that fell short is merely partial', () => {
        expect(levelErrorHealth([{instanceId: CORRELATION, code: 'correlation', status: 'partial'}])).toStrictEqual([]);
    });
});

describe('analyticNameKey', () => {
    it('builds the catalogue key from a snake_case code, the rule RiskLevelSection names analytics by', () => {
        expect(analyticNameKey('historical_var')).toBe('risk.analytics.historicalVar.name');
        expect(analyticNameKey('correlation')).toBe('risk.analytics.correlation.name');
        expect(analyticNameKey('asset_set_risk_return')).toBe('risk.analytics.assetSetRiskReturn.name');
    });

    it('reaches every analytic name the catalogue ships from its own code', () => {
        const leaves = catalogueAnalyticNames();
        expect(leaves.length, 'guard: no analytic names were read off en.json, so the check below would pass on nothing').toBeGreaterThan(0);
        for (const leaf of leaves) {
            const code = leaf.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
            expect(analyticNameKey(code), `${code} does not reach its catalogue name`).toBe(`risk.analytics.${leaf}.name`);
        }
    });
});
