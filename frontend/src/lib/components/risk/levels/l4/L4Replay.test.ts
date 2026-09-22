// @vitest-environment jsdom
//
// The docblock above is load-bearing twice over, and the two reasons fail
// differently. `render()` needs a `document`, so deleting the directive breaks
// this file *loudly* — that half announces itself. The quiet half is the one
// riskPanelController.test.ts records: under the default `node` environment a
// `.svelte.ts` compiles but `$effect` never fires and `$derived` returns stale
// values, so a controller built here would hand the component a frozen snapshot
// and the "the sentence is absent" assertions below would pass on a page that
// never rendered anything at all. `assertEffectsRun()` in the first test turns
// that into an explicit message instead of a green.
/**
 * L4Replay — component test (Vitest + jsdom).
 *
 * Two sentences in this component used to speak as though every replay had
 * portfolio weights behind it. Both were repaired, and both repairs are *branch*
 * repairs: they are only proved by exercising the weighted and the unweighted
 * payload, because each one was correct on one of them before the change.
 *
 *   1. **The total is withheld, not degraded.** `stress.py::_historical` sets
 *      `portfolio_return` on every weighted scope — 0.0 at worst — and leaves it
 *      null on the unweighted ones. The markup used to print `—` for the
 *      percent, which inside a sentence reads as a number that failed to load
 *      rather than one that does not apply. Pinned structurally: the `<p>` is
 *      present on a weighted scope and *absent* on an unweighted one.
 *
 *   2. **The audit reads its treatment off the payload.** The backend attaches
 *      `zero_return_residual` to every excluded asset on a weighted scope and
 *      `omitted_from_replay` everywhere else; the default wording states the
 *      first as though it were the only one ("carried at zero return"), which on
 *      an unweighted scope names a treatment the backend did not apply. Pinned
 *      in all three arms of the predicate: some omitted → the new key, all
 *      zero-return → the original key, and *no* exclusions → the original key,
 *      since `.some([])` is false and portfolio rendering had to stay untouched.
 *
 * **How "which key was chosen" is asserted without pinning a sentence.** The UI
 * ships in EN/IT/FR/ES and the two branches differ only by the key they select,
 * so there is no testid, attribute or event to read the choice off. Both
 * candidates are therefore resolved *from the shipped catalogue* through the
 * same `$_` formatter the component uses, with the same interpolation values,
 * and the rendered text is compared against them. No English is written down
 * here; translating `en.json` differently changes both sides identically. The
 * first test guards the two ways that could go vacuous — a key missing from the
 * catalogue (svelte-i18n echoes the id back, and the component would echo it
 * too, so both sides would "agree") and two keys that happen to resolve alike.
 *
 * **Guarding against a vacuous pass from a rejected payload.** `riskOutput` and
 * `riskMetadata` parse with Zod and hand back `null` on a miss, which would
 * render an empty `<div>` in which every absence assertion is trivially true.
 * Every case therefore asserts the tornado rows the fixture describes — their
 * order and their formatted values — and the audit's `data-proxy-count` /
 * `data-excluded-count`. Those come from the parsed output and the parsed
 * metadata respectively, so a fixture that stopped satisfying either schema goes
 * red at the barrier rather than silently passing at the negative.
 *
 * What is deliberately left elsewhere: the *backend* treatment assignment and
 * the `excluded_weight_total` pinning are already asserted by
 * `test_risk_analytics.py::test_historical_replay_exclusion_preserves_zero_return_residual_weight`
 * and `::test_historical_replay_asset_set_exclusion_is_omitted_not_zero_weighted`,
 * and are relied on here rather than restated. Running a replay end to end — the
 * Run button, the blocker/exclude-and-retry loop, the no-money rule on an
 * asset-set scope — stays in the Playwright suite (`portfolio/risk-lab.spec.ts`,
 * `portfolio/risk-analysis.spec.ts`), which has a real backend to refuse things.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {get} from 'svelte/store';

const fetchRiskCatalog = vi.hoisted(() => vi.fn());
const fetchRiskScenarioCatalog = vi.hoisted(() => vi.fn());
const queryRisk = vi.hoisted(() => vi.fn());
const invalidateRisk = vi.hoisted(() => vi.fn());

vi.mock('$lib/stores/risk/riskStore.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/risk/riskStore.svelte')>();
    return {
        ...actual,
        fetchRiskCatalog,
        fetchRiskScenarioCatalog,
        queryRisk,
        invalidateRisk,
        // Capability gating belongs to the panel, not to this component: stubbing
        // it keeps the subject singular. Nothing here presses Run, so no request
        // is ever built — the mocks exist so that mounting a real controller does
        // not reach for a real backend.
        hasRiskCapability: () => true,
    };
});

import type {z} from 'zod';
import {render, screen, setupI18n} from '$test/component';
import {assertEffectsRun, effectRoot} from '$test/runes.svelte';
import {schemas} from '$lib/api';
import {_} from '$lib/i18n';
import type {RiskResultMetadata, RiskStressOutput} from '$lib/risk/riskTypes';
import {createRiskPanelController, type RiskControllerInputs} from '$lib/stores/risk/riskPanelController.svelte';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import L4Replay from './L4Replay.svelte';

const AUDIT_DEFAULT_KEY = 'risk.levels.l4.replayAudit';
const AUDIT_OMITTED_KEY = 'risk.levels.l4.replayAuditOmitted';

const DATE_START = '2020-02-01';
const DATE_END = '2020-03-31';
const ASSET_NAMES: Record<number, string> = {7: 'Synthetic Holding A', 9: 'Synthetic Holding B'};

/** The audit shapes come off the Zod schemas rather than off
 *  `RiskResultMetadata['historical_replay_audit']`: the generated field type is a
 *  union with an array branch (the wire admits both), so indexing into it does
 *  not type-check — and normalising that union is exactly what `singleValue`
 *  does for the component. */
type ExcludedAsset = z.infer<typeof schemas.RiskHistoricalReplayExcludedAsset>;
type Audit = z.infer<typeof schemas.RiskHistoricalReplayAudit>;
/** The three values the component interpolates into whichever audit key it picks.
 *  A `type` and not an `interface` on purpose: only an alias of an object literal
 *  carries the implicit index signature svelte-i18n's `InterpolationValues` wants. */
type AuditValues = {
    proxies: number;
    excluded: number;
    weight: string;
};

/** Whitespace in the rendered `<p>` comes from the template, not from the
 *  message; collapse it on both sides so the comparison is about the sentence. */
function normalize(text: string): string {
    return text.replace(/\s+/g, ' ').trim();
}

/** One audit key, resolved from the shipped catalogue exactly as the component
 *  resolves it. Never a literal: `en.json` may be reworded in any language. */
function resolveAudit(key: string, values: AuditValues): string {
    return normalize(get(_)(key, {values}));
}

function auditText(): string {
    return normalize(screen.getByTestId('risk-replay-audit').textContent ?? '');
}

/**
 * Assert *which* of the two audit keys was selected.
 *
 * Equality against the chosen key is the real assertion; the inequality against
 * the other one localises the failure and says out loud that the two arms are
 * distinguishable. What keeps that pair honest is the harness test below, which
 * proves the two keys exist in the catalogue and do not resolve alike — without
 * it, a deleted key would make both sides echo the same id and agree.
 */
function expectAuditKey(chosen: 'default' | 'omitted', values: AuditValues): void {
    const expected = resolveAudit(chosen === 'omitted' ? AUDIT_OMITTED_KEY : AUDIT_DEFAULT_KEY, values);
    const rejected = resolveAudit(chosen === 'omitted' ? AUDIT_DEFAULT_KEY : AUDIT_OMITTED_KEY, values);
    expect(auditText(), `the audit sentence is not the one ${chosen === 'omitted' ? AUDIT_OMITTED_KEY : AUDIT_DEFAULT_KEY} produces`).toBe(expected);
    expect(auditText(), `the audit sentence is the one ${chosen === 'omitted' ? AUDIT_DEFAULT_KEY : AUDIT_OMITTED_KEY} produces: the wrong branch of the treatment predicate was taken`).not.toBe(rejected);
}

function excludedAsset(assetId: number, treatment: ExcludedAsset['treatment'], weight: number | null): ExcludedAsset {
    return {asset_id: assetId, reason: 'manual_exclusion', weight, treatment};
}

function audit(excluded: ExcludedAsset[] | undefined, excludedWeightTotal: number, excludedCount = excluded?.length ?? 0): Audit {
    return {
        proxy_count: 1,
        proxy_assets: [{asset_id: 41, proxy_asset_id: 42}],
        excluded_count: excludedCount,
        ...(excluded === undefined ? {} : {excluded_assets: excluded}),
        excluded_weight_total: excludedWeightTotal,
        missing_history_policy: 'manual_proxy_or_exclude',
        composition_policy: 'current_buy_and_hold',
        proxy_series_usage: 'returns_only',
    };
}

function metadata(scope: 'portfolio' | 'asset_set', replayAudit: Audit): RiskResultMetadata {
    return {
        analyzed_range: {start: DATE_START, end: DATE_END},
        frequency: 'daily',
        n_observations: 42,
        calendar_days: 60,
        coverage: 1,
        currency: 'EUR',
        scope,
        return_basis: 'current_composition_backtest',
        algorithm_version: 'test-l4-replay',
        computed_at: '2026-01-05T10:00:00+00:00',
        historical_replay_audit: replayAudit,
    };
}

/**
 * A replay output whose two impacts are fixed and *ordered against* the tornado's
 * sort, so the rendered order is evidence that the payload was parsed and sorted
 * rather than echoed: the worse bar (asset 7) is declared second.
 */
function output(portfolioReturn: number | null): RiskStressOutput {
    return {
        kind: 'stress',
        method: 'historical_replay',
        portfolio_return: portfolioReturn,
        impact_amount: portfolioReturn === null ? null : '-1234.50',
        replay_range: {start: DATE_START, end: DATE_END},
        impacts: [
            {asset_id: 9, shock_return: 0.05, contribution_return: 0.02, impact_amount: '200.00', weight: 0.4, metadata_fallback: false},
            {asset_id: 7, shock_return: -0.2, contribution_return: -0.08, impact_amount: '-800.00', weight: 0.4, metadata_fallback: false},
        ],
    };
}

function replayResult(scope: 'portfolio' | 'asset_set', portfolioReturn: number | null, replayAudit: Audit): RiskAnalyticResult {
    return {
        instance_id: 'single-stress',
        analytic_code: 'stress',
        status: 'ok',
        output: output(portfolioReturn),
        metadata: metadata(scope, replayAudit),
    };
}

function controllerInputs(scope: 'portfolio' | 'asset_set'): RiskControllerInputs {
    return {
        scope: scope === 'portfolio' ? {kind: 'portfolio'} : {kind: 'asset_set', asset_ids: [7, 9]},
        dateStart: DATE_START,
        dateEnd: DATE_END,
        targetCurrency: 'EUR',
        appliedRiskFreePercent: 0,
        refreshVersion: 0,
    };
}

const stops: (() => void)[] = [];

/**
 * A real controller carrying one replay answer, and the component on top of it.
 *
 * The `flushSync()` is not decoration: the controller's first effect applies the
 * base signature, and applying it discards every on-demand result. Seeding the
 * replay answer before that runs would hand the component a `null` and every
 * assertion below would be about an empty div.
 */
function mount(scope: 'portfolio' | 'asset_set', portfolioReturn: number | null, replayAudit: Audit): void {
    const {value: controller, stop} = effectRoot(() => createRiskPanelController(() => controllerInputs(scope)));
    stops.push(stop);
    flushSync();
    controller.setResult('replay', replayResult(scope, portfolioReturn, replayAudit));
    render(L4Replay, {props: {controller, assetNames: ASSET_NAMES, currency: 'EUR', dateStart: DATE_START, dateEnd: DATE_END}});
}

/**
 * The barrier every negative assertion in this file stands on.
 *
 * `riskOutput`/`riskMetadata` answer `null` for a payload their schema rejects,
 * and a null output renders *nothing at all* — at which point "the total is
 * absent" is true for the wrong reason. Asserting the bars the fixture describes
 * (ordered worst-first, formatted by the component) and the audit's two counts
 * proves the output and the metadata both parsed before anything is said to be
 * missing.
 */
function expectPayloadRendered(proxies: number, excluded: number): void {
    const rows = screen.getAllByTestId('risk-replay-tornado-row');
    expect(
        rows.map((row) => row.getAttribute('data-row-key')),
        'the stress output did not parse, or the tornado stopped sorting by signed damage — either way the absence assertions below would be about an empty component',
    ).toEqual(['asset:7', 'asset:9']);
    expect(normalize(screen.getAllByTestId('risk-replay-tornado-value')[0].textContent ?? '')).toContain('−8.00%');

    const auditEl = screen.getByTestId('risk-replay-audit');
    expect(auditEl, 'the result metadata did not parse: the audit paragraph is rendered from it, so its wording could not be under test').toHaveAttribute('data-proxy-count', String(proxies));
    expect(auditEl).toHaveAttribute('data-excluded-count', String(excluded));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    fetchRiskCatalog.mockReset().mockResolvedValue({items: []});
    fetchRiskScenarioCatalog.mockReset().mockResolvedValue({items: []});
    queryRisk.mockReset().mockResolvedValue({items: []});
    invalidateRisk.mockReset();
});

afterEach(() => {
    while (stops.length > 0) stops.pop()?.();
});

describe('L4Replay — the harness itself', () => {
    it('runs effects, and the two audit keys are present and distinguishable', () => {
        // Without effects the controller hands over stale state; see the header.
        expect(() => assertEffectsRun()).not.toThrow();

        const values: AuditValues = {proxies: 1, excluded: 2, weight: '12.5%'};
        const original = resolveAudit(AUDIT_DEFAULT_KEY, values);
        const omitted = resolveAudit(AUDIT_OMITTED_KEY, values);

        // svelte-i18n echoes the id back on a miss, and so would the component:
        // both sides would then "agree" on a key that no longer exists.
        expect(original, `${AUDIT_DEFAULT_KEY} is missing from the catalogue`).not.toBe(AUDIT_DEFAULT_KEY);
        expect(omitted, `${AUDIT_OMITTED_KEY} is missing from the catalogue`).not.toBe(AUDIT_OMITTED_KEY);
        // If the two ever resolved alike, every "which key" assertion below would
        // be satisfied by either branch.
        expect(omitted, 'the two audit keys resolve to the same sentence: nothing below can tell the branches apart').not.toBe(original);
    });
});

describe('L4Replay — the composition total', () => {
    it('states it on a weighted scope, where the backend always sends one', () => {
        mount('portfolio', -0.0612, audit([excludedAsset(11, 'zero_return_residual', 0.08), excludedAsset(12, 'zero_return_residual', 0.045)], 0.125));

        expectPayloadRendered(1, 2);
        expect(screen.getByTestId('risk-replay-total')).toBeVisible();
    });

    it('states it when the weighted replay came out flat, instead of reading the 0.0 as "no answer"', () => {
        // `stress.py` falls back to `portfolio_return = 0.0` rather than to null on
        // a weighted scope, so a guard written as a truthiness check would hide the
        // one honest sentence the reader is owed here.
        mount('portfolio', 0, audit([], 0));

        expectPayloadRendered(1, 0);
        expect(screen.getByTestId('risk-replay-total')).toBeVisible();
    });

    it('withholds it on an unweighted scope rather than printing a dash for the percent', () => {
        mount('asset_set', null, audit([excludedAsset(11, 'omitted_from_replay', null)], 0));

        // The barrier first: the paragraph being absent must mean "the component
        // chose not to render it", not "the component rendered nothing".
        expectPayloadRendered(1, 1);
        expect(screen.queryAllByTestId('risk-replay-total'), 'the composition total was rendered for a scope that has no composition return').toHaveLength(0);
    });
});

describe('L4Replay — the audit sentence names the treatment the backend applied', () => {
    it('says "omitted" when an excluded asset was omitted from the replay', () => {
        mount('asset_set', null, audit([excludedAsset(11, 'omitted_from_replay', null), excludedAsset(12, 'omitted_from_replay', null)], 0));

        expectPayloadRendered(1, 2);
        expectAuditKey('omitted', {proxies: 1, excluded: 2, weight: '0.0%'});
    });

    it('keeps the zero-return wording when every exclusion really was carried at zero return', () => {
        mount('portfolio', -0.0612, audit([excludedAsset(11, 'zero_return_residual', 0.08), excludedAsset(12, 'zero_return_residual', 0.045)], 0.125));

        expectPayloadRendered(1, 2);
        expectAuditKey('default', {proxies: 1, excluded: 2, weight: '12.5%'});
    });

    it('keeps the zero-return wording when nothing was excluded at all', () => {
        // `.some([])` is false, which is what leaves ordinary portfolio rendering —
        // the overwhelmingly common case — byte-for-byte unchanged by the repair.
        mount('portfolio', -0.0612, audit([], 0));

        expectPayloadRendered(1, 0);
        expectAuditKey('default', {proxies: 1, excluded: 0, weight: '0.0%'});
    });

    it('keeps the zero-return wording when the payload carries no excluded list at all', () => {
        // `excluded_assets` is optional in the contract, so the `?? []` in the
        // predicate is reachable; without it the component would throw on mount
        // instead of falling back to the wording that was always used before.
        mount('portfolio', -0.0612, audit(undefined, 0, 0));

        expectPayloadRendered(1, 0);
        expectAuditKey('default', {proxies: 1, excluded: 0, weight: '0.0%'});
    });

    it('says "omitted" as soon as one exclusion was omitted, even beside one that was not', () => {
        // The predicate asks whether the sentence has a subject it would
        // misdescribe, so it is `.some(...)` and not `.every(...)`. The backend
        // assigns one treatment per scope and does not emit a mixed list today;
        // this pins the component's stated rule, which is the one that decides
        // what happens the day it does.
        mount('asset_set', null, audit([excludedAsset(11, 'zero_return_residual', 0.03), excludedAsset(12, 'omitted_from_replay', null)], 0.03));

        expectPayloadRendered(1, 2);
        expectAuditKey('omitted', {proxies: 1, excluded: 2, weight: '3.0%'});
    });
});
