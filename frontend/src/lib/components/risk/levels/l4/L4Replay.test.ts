// @vitest-environment jsdom
//
// The docblock above is load-bearing twice over, and the two reasons fail
// differently. `render()` needs a `document`, so deleting the directive breaks
// this file *loudly* — that half announces itself. The quiet half is the one
// riskPanelController.test.ts records: under the default `node` environment a
// `.svelte.ts` compiles but `$effect` never fires and `$derived` returns stale
// values, so a controller built here would hand the component a frozen snapshot
// and every "the block is absent" assertion below would pass on a page that
// never rendered anything at all. `assertEffectsRun()` in the first test turns
// that into an explicit message instead of a green.
/**
 * L4Replay — component test (Vitest + jsdom).
 *
 * The replay block after F3 (developer's decision D372, 02/10/2026). Since 24/09
 * the engine leaves out, on its own, every holding whose quotes do not cover the
 * window, so the block has no question left to put to the reader: the "leave it
 * out and run again" blocker, its chips and the one-line audit are retired. What
 * the block says instead is read off the answer:
 *
 *   1. **The period** is one `DateRangePicker`, without its quick presets — the
 *      crisis menu is this block's preset, and it opens where there is room. Run
 *      asks over exactly the window the picker shows, with nothing excluded by
 *      hand and no stand-in (proxies stay out of L4). Changing the dates or the
 *      crisis drops the answer on screen, as before.
 *   2. **What was left out, and why**: grouped by reason in the block's order,
 *      each asset named, with its share of the value when the scope has weights.
 *      The header names the treatment the payload carries — carried as cash at
 *      zero return on a weighted scope, omitted from the replay on a selection —
 *      and keeps the three-arm discipline the audit sentence had: all residual,
 *      all omitted, one of each.
 *   3. **The strong warning** — the replay describes only part of the
 *      portfolio — stands above the total it qualifies, in the warning's own
 *      words. That the section around the block stops repeating it is the
 *      mounts' half (`AssetSetReplaySection.test.ts`, `risk-analysis.spec.ts`).
 *   4. **Nothing left**: a sentence and the same groups, never a figure.
 *   5. **The common period** the backend verified is one button, and one click
 *      sets the dates *and* asks the question, once. Beside it, a note when that
 *      period is only part of the crisis the reader chose.
 *
 * **How a sentence is asserted without pinning one.** The UI ships in
 * EN/IT/FR/ES, so every expected sentence is resolved *from the shipped
 * catalogue* through the same `$_` the component uses, with the same values —
 * dates and shares through the same `formatReplayDate` / `formatReplayShare`, in
 * the language the app is in. No English is written down here. The harness tests
 * guard the ways that could go vacuous: a key missing from the catalogue
 * (svelte-i18n echoes the id back, and the component would echo it too, so both
 * sides would "agree"), and two keys that resolve alike (then "which branch
 * rendered" has no answer).
 *
 * **A barrier before every absence.** `riskOutput` and `riskMetadata` parse with
 * Zod and answer `null` on a miss, which renders an empty block in which every
 * absence is trivially true. So each negative stands on a positive drawn from the
 * same payload: the tornado's rows in their sorted order (the output parsed), the
 * excluded block (the metadata parsed), the nothing-left line (the error was
 * read), the money in a portfolio's total (the scope was read).
 *
 * **Expected values come from the helpers** (`replayExclusions`,
 * `replaySuggestion`, …) wherever the subject is the block *following* them: their
 * own rules — the order of the reasons, heaviest first, what counts as nothing
 * left — are pinned by `scenarioHelpers.test.ts`, and restating them here would
 * make two copies of one rule that drift apart.
 *
 * Left elsewhere: the backend's treatment, weights and proposal
 * (`test_risk_analytics.py`), the section reading `replaySectionView`
 * (`AssetSetReplaySection.test.ts`), and the replay end to end
 * (`portfolio/risk-analysis.spec.ts`, `portfolio/risk-lab.spec.ts`).
 *
 * ⚠️ Every figure, name and date below is invented; the shapes are the backend's
 * (`stress.py::_historical`, `_replay_exclusion_warning`,
 * `service.py::_with_warning_asset_names`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {parse} from 'svelte/compiler';
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
        // Capability gating belongs to the panel, not to this component: stubbing it
        // keeps the subject singular. `queryRisk` is scripted per question below, so
        // a mounted controller never reaches for a real backend.
        hasRiskCapability: () => true,
    };
});

import type {z} from 'zod';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {assertEffectsRun, effectRoot} from '$test/runes.svelte';
import {schemas} from '$lib/api';
import {_, locale, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import type {RiskQueryRequest} from '$lib/risk/riskRequest';
import type {RiskResultMetadata, RiskStressOutput} from '$lib/risk/riskTypes';
import {currentLanguage} from '$lib/stores/app/language';
import {createRiskPanelController, type RiskControllerInputs, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import {formatCurrencyAmount} from '../../riskAnalysisHelpers';
import {warningSentence, type RiskResultWarning} from '../warningSentence';
import L4Replay from './L4Replay.svelte';
import {formatReplayDate, formatReplayShare, REPLAY_EXCLUSION_REASON_ORDER, replayExclusions, replaySuggestion, type ReplayExclusions, type ReplaySuggestion} from './scenarioHelpers';

/** The component's own source, for the one property that is markup rather than behaviour (see "the crisis menu"). */
const L4_REPLAY_SOURCE = import.meta.glob('./L4Replay.svelte', {query: '?raw', import: 'default', eager: true})['./L4Replay.svelte'] as string;

type Scope = 'portfolio' | 'asset_set';
type ReplayWindow = {start: string; end: string};
/** A type and not an interface: only an alias carries the implicit index signature svelte-i18n's values want. */
type Values = Record<string, string | number>;
type ExcludedAsset = z.infer<typeof schemas.RiskHistoricalReplayExcludedAsset>;
type Audit = z.infer<typeof schemas.RiskHistoricalReplayAudit>;
type ExclusionReason = z.infer<typeof schemas.RiskHistoricalReplayExclusionReason>;
/** One bar of a replay: an asset and its realised return over the window. */
type ImpactSpec = readonly [assetId: number, shockReturn: number];

/** The panel's window, which the block follows until the reader moves it. */
const WINDOW: ReplayWindow = {start: '2020-02-01', end: '2020-03-31'};
/** A start the reader types into the picker. */
const MOVED_START = '2020-02-10';
/** The common period a replay over {@link WINDOW} proposes: from the late listing's first quote. */
const SUGGESTED: ReplayWindow = {start: '2020-02-17', end: WINDOW.end};

/** Named holdings. 14 is deliberately absent, for the `#id` fallback. */
const ASSET_NAMES: Record<number, string> = {
    7: 'Synthetic Holding A',
    9: 'Synthetic Holding B',
    11: 'Synthetic Holding C',
    12: 'Synthetic Holding D',
    13: 'Synthetic Holding E',
    15: 'Synthetic Holding F',
    16: 'Synthetic Holding G',
};
const UNNAMED = 14;

/**
 * The scenario catalogue, shaped on the built-in YAML so the strict generated Zod
 * accepts it (`scenarioHelpers.test.ts` says why every field is here). One crisis
 * with both dates, and the open entry that names none. The labels are this test's
 * own data, not catalogue sentences: they are what it picks the entries by.
 */
const CRISIS = {id: 'covid_crash_2020', label: 'Synthetic crash (invented)', start: '2020-02-19', end: '2020-03-23'};
const OPEN_PERIOD = {id: 'custom_period', label: 'Synthetic open period (invented)'};
/** Inside the crisis and strictly shorter: a late listing starts mid-crisis, a holding goes stale before its end. */
const PART_OF_CRISIS: ReplayWindow = {start: '2020-03-02', end: '2020-03-23'};

function historicalScenario(id: string, label: string, start: string | null, end: string | null) {
    return {
        source: 'built_in',
        source_file: `historical/${id}.yml`,
        scenario: {
            schema_version: 1,
            id,
            kind: 'historical_replay',
            tags: ['crisis'],
            name: {en: label},
            description: {en: `${label}: a description.`},
            defaults: {start, end, missing_history_policy: 'manual_proxy_or_exclude', composition_policy: 'current_buy_and_hold'},
            editable: {dates: true, missing_history_policy: true, proxies: true, exclusions: true},
            limits: {minimum_calendar_days: 1},
        },
    };
}

const SCENARIO_CATALOG = {
    items: [historicalScenario(CRISIS.id, CRISIS.label, CRISIS.start, CRISIS.end), historicalScenario(OPEN_PERIOD.id, OPEN_PERIOD.label, null, null)],
    geography_groups: [],
};

const L4 = 'risk.levels.l4';
const KEYS = {
    period: `${L4}.replayPeriod`,
    excludedResidual: `${L4}.replayExcludedResidual`,
    excludedOmitted: `${L4}.replayExcludedOmitted`,
    nothing: `${L4}.replayNothing`,
    suggested: `${L4}.replaySuggested`,
    suggestedPartial: `${L4}.replaySuggestedPartial`,
} as const;

/** The label of each reason the engine gives, one literal key each. */
const REASON_KEYS: Readonly<Record<string, string>> = {
    no_prices_in_window: `${L4}.replayReasonNoPrices`,
    starts_after_window_start: `${L4}.replayReasonStartsLate`,
    stale_at_window_start: `${L4}.replayReasonStaleAtStart`,
    stale_at_window_end: `${L4}.replayReasonStaleAtEnd`,
    missing_fx: `${L4}.replayReasonMissingFx`,
    manual_exclusion: `${L4}.replayReasonManual`,
};
/** A reason the block does not know is still a reason, said in general terms. */
const REASON_OTHER_KEY = `${L4}.replayReasonOther`;

const NEW_KEYS = [...Object.values(KEYS), ...Object.values(REASON_KEYS), REASON_OTHER_KEY];

/** The sentences of the exclude-and-retry flow and of the one-line audit: retired with them. */
const RETIRED_KEYS = ['replayNeedsChoice', 'replayProxyUnusable', 'replayExcludeAndRetry', 'replayExcluded', 'replayAudit', 'replayAuditOmitted'].map((name) => `${L4}.${name}`);
/** Their handles. None may come back in any state the block can be in. */
const RETIRED_TEST_IDS = ['risk-replay-blocker', 'risk-replay-exclude', 'risk-replay-exclusions', 'risk-replay-exclusion', 'risk-replay-audit'];

const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

/** The per-reason exclusion warnings, keyed as `_replay_exclusion_warning` writes them out. */
const EXCLUSION_WARNING_KEYS: Record<ExclusionReason, string> = {
    manual_exclusion: 'risk.warnings.historical_replay_excluded_manual',
    no_prices_in_window: 'risk.warnings.historical_replay_excluded_no_prices',
    starts_after_window_start: 'risk.warnings.historical_replay_excluded_starts_late',
    stale_at_window_start: 'risk.warnings.historical_replay_excluded_stale_at_start',
    stale_at_window_end: 'risk.warnings.historical_replay_excluded_stale_at_end',
    missing_fx: 'risk.warnings.historical_replay_excluded_missing_fx',
};

/** Declared against the tornado's sort (the worse bar second), so the rendered order proves the payload was parsed and sorted rather than echoed. */
const DEFAULT_IMPACTS: readonly ImpactSpec[] = [
    [9, 0.05],
    [7, -0.2],
];
const DEFAULT_BARS = ['asset:7', 'asset:9'];
/** The answer over the common period: the two assets it brought back are among the bars. */
const RECOVERED_IMPACTS: readonly ImpactSpec[] = [
    [9, 0.05],
    [12, -0.05],
    [13, -0.1],
    [7, -0.2],
];
const RECOVERED_BARS = ['asset:7', 'asset:13', 'asset:12', 'asset:9'];

/** The weight of each replayed bar on a weighted scope, and the value the money is a share of. */
const IMPACT_WEIGHT = 0.4;
const SCOPE_VALUE = 20_000;
const PORTFOLIO_RETURN = -0.0612;

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** A catalogue sentence as the component words it: `$_`, with the same values. Never a literal. */
function t(key: string, values?: Values): string {
    return normalize(get(_)(key, values === undefined ? undefined : {values}));
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The language the block formats dates and shares in. The harness proves the two stores that could carry it agree. */
function lang(): string {
    return get(currentLanguage);
}

function nameOf(assetId: number): string {
    return ASSET_NAMES[assetId] ?? `#${assetId}`;
}

function money(fraction: number): string {
    return (fraction * SCOPE_VALUE).toFixed(2);
}

function residual(assetId: number, reason: ExclusionReason, weight: number): ExcludedAsset {
    return {asset_id: assetId, reason, weight, treatment: 'zero_return_residual'};
}

function omitted(assetId: number, reason: ExclusionReason): ExcludedAsset {
    return {asset_id: assetId, reason, weight: null, treatment: 'omitted_from_replay'};
}

/**
 * An audit as `stress.py` builds it: the total is the sum of the weights, zero when
 * there are none. The weights below are binary fractions, so the sum is exact and a
 * `data-weight-total` can be compared as the string it is.
 */
function audit(excluded: ExcludedAsset[], extra: Partial<Audit> = {}): Audit {
    const weights = excluded.flatMap((item) => (typeof item.weight === 'number' ? [item.weight] : []));
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

/** One warning per reason, in the engine's own order, named the way `service.py` names them. */
function exclusionWarnings(excluded: readonly ExcludedAsset[]): RiskResultWarning[] {
    return schemas.RiskHistoricalReplayExclusionReason.options.flatMap((reason) => {
        const items = excluded.filter((item) => item.reason === reason);
        if (items.length === 0) return [];
        const treatment = items[0].treatment;
        const assetIds = items.map((item) => item.asset_id);
        return [
            {
                code: 'historical_replay_assets_excluded',
                message: 'Historical replay excluded one or more assets.',
                details: {asset_ids: assetIds, treatment, reason},
                degrades_result: true,
                message_i18n_key: EXCLUSION_WARNING_KEYS[reason],
                message_params: {treatment, names: assetIds.map(nameOf).join(', '), count: assetIds.length},
            },
        ];
    });
}

/** The strong warning, which the engine sends on a weighted scope once more than half of the value is left out. */
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

function metadata(scope: Scope, replayAudit: Audit, range: ReplayWindow): RiskResultMetadata {
    return {
        analyzed_range: {start: range.start, end: range.end},
        frequency: 'daily',
        n_observations: 42,
        calendar_days: 60,
        coverage: 1,
        currency: 'EUR',
        scope,
        return_basis: 'current_composition_backtest',
        algorithm_version: 'test-l4-replay',
        computed_at: '2026-10-05T10:00:00+00:00',
        historical_replay_audit: replayAudit,
    };
}

/** A replay's figures. On a weighted scope a bar is a contribution with its money; on a selection, the bare return with neither — as `stress.py` sends them. */
function output(scope: Scope, portfolioReturn: number | null, range: ReplayWindow, impacts: readonly ImpactSpec[]): RiskStressOutput {
    const weighted = scope === 'portfolio';
    return {
        kind: 'stress',
        method: 'historical_replay',
        portfolio_return: portfolioReturn,
        impact_amount: portfolioReturn === null ? null : money(portfolioReturn),
        replay_range: {start: range.start, end: range.end},
        impacts: impacts.map(([assetId, shockReturn]) => ({
            asset_id: assetId,
            weight: weighted ? IMPACT_WEIGHT : null,
            shock_return: shockReturn,
            contribution_return: weighted ? IMPACT_WEIGHT * shockReturn : null,
            impact_amount: weighted ? money(IMPACT_WEIGHT * shockReturn) : null,
            metadata_fallback: false,
        })),
    };
}

interface ReplayedOptions {
    /** Defaults to the exclusion warnings the audit implies. */
    warnings?: RiskResultWarning[];
    /** Defaults to a loss on a weighted scope and to none on a selection, which has no aggregate. */
    portfolioReturn?: number | null;
    range?: ReplayWindow;
    impacts?: readonly ImpactSpec[];
}

/** A replay that ran: `partial` as soon as anything was left out or a warning degrades it. */
function replayed(scope: Scope, replayAudit: Audit, options: ReplayedOptions = {}): RiskAnalyticResult {
    const excluded = replayAudit.excluded_assets ?? [];
    const warnings = options.warnings ?? exclusionWarnings(excluded);
    const range = options.range ?? WINDOW;
    const portfolioReturn = 'portfolioReturn' in options ? (options.portfolioReturn ?? null) : scope === 'portfolio' ? PORTFOLIO_RETURN : null;
    return {
        instance_id: 'single-stress',
        analytic_code: 'stress',
        status: excluded.length > 0 || warnings.some((warning) => warning.degrades_result) ? 'partial' : 'ok',
        output: output(scope, portfolioReturn, range, options.impacts ?? DEFAULT_IMPACTS),
        metadata: metadata(scope, replayAudit, range),
        warnings,
    };
}

/** Nothing left to replay: every asset excluded (`stress.py`, the `if not selected:` branch). No output, as `schemas/risk.py` demands. */
function nothingLeft(details: Record<string, unknown>): RiskAnalyticResult {
    return {instance_id: 'single-stress', analytic_code: 'stress', status: 'unavailable', output: null, error: {code: 'insufficient_history', message: 'No asset in the replay scope covers the replay window', details}};
}

function exclusionsOf(result: RiskAnalyticResult): ReplayExclusions {
    const exclusions = replayExclusions(result);
    if (!exclusions) throw new Error('fixture error: replayExclusions reads nothing left out of this answer, so the block would have nothing to list');
    return exclusions;
}

function suggestionOf(result: RiskAnalyticResult): ReplaySuggestion {
    const suggestion = replaySuggestion(result);
    if (!suggestion) throw new Error('fixture error: replaySuggestion reads no common period in this answer');
    return suggestion;
}

function controllerInputs(scope: Scope): RiskControllerInputs {
    return {
        scope: scope === 'portfolio' ? {kind: 'portfolio'} : {kind: 'asset_set', asset_ids: [7, 9, 12, 13, 15]},
        dateStart: WINDOW.start,
        dateEnd: WINDOW.end,
        targetCurrency: 'EUR',
        appliedRiskFreePercent: 0,
        refreshVersion: 0,
    };
}

const stops: (() => void)[] = [];

/**
 * A real controller, optionally carrying one replay answer, and the component on top.
 *
 * The `flushSync()` is not decoration: the controller's first effect applies the
 * base signature, and applying it discards every on-demand result. Seeding the
 * answer before that runs would hand the component a `null`.
 */
function mount(scope: Scope, result: RiskAnalyticResult | null = null): RiskPanelController {
    const {value: controller, stop} = effectRoot(() => createRiskPanelController(() => controllerInputs(scope)));
    stops.push(stop);
    flushSync();
    if (result) controller.setResult('replay', result);
    render(L4Replay, {props: {controller, assetNames: ASSET_NAMES, currency: 'EUR', dateStart: WINDOW.start, dateEnd: WINDOW.end}});
    return controller;
}

/** Every replay question put to `queryRisk`, as asked; and how this test answers the next one, given the window it was asked over. */
const replay = {
    asked: [] as RiskQueryRequest[],
    answer: null as ((window: ReplayWindow) => RiskAnalyticResult) | null,
};

function replayAnalytic(request: RiskQueryRequest) {
    return request.analytics.find((analytic) => analytic.analytic_code === 'stress' && (analytic.parameters as Record<string, unknown> | undefined)?.method === 'historical_replay');
}

function replayParameters(request: RiskQueryRequest): Record<string, unknown> {
    return (replayAnalytic(request)?.parameters ?? {}) as Record<string, unknown>;
}

/** The whole question L4 may ask since D372: the window, nothing excluded by hand, no stand-in. */
function expectedParameters(window: ReplayWindow): Record<string, unknown> {
    return {method: 'historical_replay', replay_range: {start: window.start, end: window.end}, missing_history_policy: 'manual_proxy_or_exclude', proxy_assets: [], excluded_assets: []};
}

function barKeys(): string[] {
    return screen.queryAllByTestId('risk-replay-tornado-row').map((row) => row.getAttribute('data-row-key') ?? '');
}

/** The output barrier: the bars the payload describes, in the tornado's order — so the output parsed, and was sorted rather than echoed. */
function expectBars(keys: readonly string[], context = 'the replay output did not parse, or the tornado stopped sorting by signed damage: any absence asserted next would be about an empty block'): void {
    expect(barKeys(), context).toEqual(keys);
}

function expectRetiredControlsGone(): void {
    const present = RETIRED_TEST_IDS.filter((testId) => screen.queryAllByTestId(testId).length > 0);
    expect(present, 'the retired exclude-and-retry flow, or its one-line audit, is still on screen (D372)').toEqual([]);
}

/** The groups as the block lists them, in document order: why, under which label, and who. */
function groupsOnScreen(root: HTMLElement) {
    return within(root)
        .getAllByTestId('risk-replay-excluded-group')
        .map((group) => ({
            reason: group.getAttribute('data-reason'),
            label: normalize(within(group).getByTestId('risk-replay-excluded-reason').textContent),
            assets: within(group)
                .getAllByTestId('risk-replay-excluded-asset')
                .map((item) => item.getAttribute('data-asset-id')),
        }));
}

/** What the block must list for this answer: the helper's groups, each label resolved from the catalogue. */
function groupsExpected(exclusions: ReplayExclusions) {
    return exclusions.groups.map((group) => ({
        reason: group.reason,
        label: t(REASON_KEYS[group.reason] ?? REASON_OTHER_KEY),
        assets: group.assets.map((asset) => String(asset.assetId)),
    }));
}

/** Each asset named — `#id` when the page knows no name — with its share when it has one, and no number at all when it has none. */
function expectItems(root: HTMLElement, exclusions: ReplayExclusions): void {
    for (const asset of exclusions.groups.flatMap((group) => group.assets)) {
        const item = root.querySelector<HTMLElement>(`[data-testid="risk-replay-excluded-asset"][data-asset-id="${asset.assetId}"]`);
        if (!item) throw new Error(`asset ${asset.assetId} was left out of the replay and the block does not list it`);
        const text = normalize(item.textContent);
        expect(text, `asset ${asset.assetId} is listed without its name`).toContain(nameOf(asset.assetId));
        if (asset.weight === null) {
            expect(item, `asset ${asset.assetId} carries no weight and publishes one`).not.toHaveAttribute('data-weight');
            expect(text, `a share was printed for asset ${asset.assetId}, which the scope never weighed`).not.toContain('%');
        } else {
            expect(item).toHaveAttribute('data-weight', String(asset.weight));
            expect(text, `asset ${asset.assetId} is listed without its share of the value`).toContain(formatReplayShare(asset.weight, lang()));
        }
    }
}

/**
 * Assert *which* header was chosen. Equality against the chosen key is the real
 * assertion; the inequality against the other localises a failure, and the harness
 * proves the two keys exist and do not resolve alike.
 */
function expectHeader(chosen: 'residual' | 'omitted', exclusions: ReplayExclusions): void {
    const residualSentence = t(KEYS.excludedResidual, {count: exclusions.count, weight: formatReplayShare(exclusions.weightTotal ?? 0, lang())});
    const omittedSentence = t(KEYS.excludedOmitted, {count: exclusions.count});
    const header = normalize(screen.getByTestId('risk-replay-excluded-header').textContent);
    expect(header, `the header is not the one ${chosen === 'residual' ? KEYS.excludedResidual : KEYS.excludedOmitted} words`).toBe(chosen === 'residual' ? residualSentence : omittedSentence);
    expect(header, 'the header names a treatment the backend did not apply: the wrong branch of the treatment rule was taken').not.toBe(chosen === 'residual' ? omittedSentence : residualSentence);
}

function expectSuggestionButton(suggestion: ReplaySuggestion): void {
    const button = screen.getByTestId('risk-replay-suggested');
    expect(button.tagName, 'the common period is offered as something other than a button').toBe('BUTTON');
    expect(button).toHaveAttribute('data-start', suggestion.start);
    expect(button).toHaveAttribute('data-end', suggestion.end);
    expect(button).toHaveAttribute('data-recovers', String(suggestion.recovers.length));
    expect(normalize(button.textContent), `the button is not worded by ${KEYS.suggested} with the period and the count it brings back`).toBe(t(KEYS.suggested, {start: formatReplayDate(suggestion.start, lang()), end: formatReplayDate(suggestion.end, lang()), count: suggestion.recovers.length}));
}

function periodInputs(): {start: HTMLInputElement; end: HTMLInputElement} {
    const period = screen.getByTestId('risk-replay-period');
    return {
        start: within(period).getByTestId('date-range-input-start') as HTMLInputElement,
        end: within(period).getByTestId('date-range-input-end') as HTMLInputElement,
    };
}

/**
 * The window the picker holds, read the way it offers it for editing: a focused
 * field shows the ISO date whether the picker is compact or not. Leaving a field
 * untouched publishes nothing — `onchange` belongs to the reader's gestures.
 */
async function pickerWindow(): Promise<ReplayWindow> {
    const {start, end} = periodInputs();
    await fireEvent.focus(start);
    const startValue = start.value;
    await fireEvent.blur(start);
    await fireEvent.focus(end);
    const endValue = end.value;
    await fireEvent.blur(end);
    return {start: startValue, end: endValue};
}

/** Type a start into the picker and leave the field, as a reader does: the picker publishes the range when focus leaves it. */
async function typeStart(iso: string): Promise<void> {
    const {start} = periodInputs();
    await fireEvent.focus(start);
    await fireEvent.input(start, {target: {value: iso}});
    await fireEvent.blur(start);
}

/** Pick a catalogue entry from the crisis menu, by the label this test gave it. */
async function choosePreset(label: string): Promise<void> {
    await fireEvent.click(screen.getByTestId('risk-replay-preset-button'));
    const menu = screen.getByTestId('risk-replay-preset-dropdown');
    await fireEvent.click(within(menu).getByRole('option', {name: (accessibleName) => accessibleName.includes(label)}));
}

/**
 * Script the next replay to leave out a late listing and a holding gone stale and to
 * propose `proposal`, press Run, and end on the answer being on screen.
 */
async function runAnsweringWith(proposal: ReplayWindow): Promise<ReplaySuggestion> {
    const answers: RiskAnalyticResult[] = [];
    replay.answer = (window) => {
        const answer = replayed('asset_set', audit([omitted(13, 'starts_after_window_start'), omitted(15, 'stale_at_window_end')], {suggested_range: proposal, suggested_range_recovers: [13, 15]}), {range: window});
        answers.push(answer);
        return answer;
    };
    await fireEvent.click(screen.getByTestId('risk-replay-run'));
    await waitFor(() => expectBars(DEFAULT_BARS, 'the replay answer never reached the screen'));
    expect(answers, 'Run did not ask exactly once').toHaveLength(1);
    return suggestionOf(answers[0]);
}

type AstNode = Record<string, unknown> & {type: string};

function isAstNode(value: unknown): value is AstNode {
    return value !== null && typeof value === 'object' && typeof (value as {type?: unknown}).type === 'string';
}

/** Every node of a parsed component, depth first. The seen-set guards against a shared reference. */
function* astNodes(root: unknown, seen: WeakSet<object> = new WeakSet()): Generator<AstNode> {
    if (root === null || typeof root !== 'object' || seen.has(root)) return;
    seen.add(root);
    if (isAstNode(root)) yield root;
    for (const child of Array.isArray(root) ? root : Object.values(root)) yield* astNodes(child, seen);
}

/** The components of one name in a `.svelte` source, read through the Svelte compiler's own parser rather than a regex. */
function componentsNamed(source: string, name: string): AstNode[] {
    return [...astNodes(parse(source, {modern: true}))].filter((node) => node.type === 'Component' && node.name === name);
}

/** An attribute written as a constant — `name="x"` or `name={'x'}` — or `undefined` when absent or computed. */
function constantAttribute(component: AstNode, name: string): string | undefined {
    const attributes = Array.isArray(component.attributes) ? component.attributes : [];
    const attribute = attributes.find((candidate): candidate is AstNode => isAstNode(candidate) && candidate.type === 'Attribute' && candidate.name === name);
    if (!attribute) return undefined;
    const parts: unknown[] = Array.isArray(attribute.value) ? attribute.value : [attribute.value];
    const [part] = parts;
    if (parts.length !== 1 || !isAstNode(part)) return undefined;
    if (part.type === 'Text') return typeof part.data === 'string' ? part.data : undefined;
    const expression = part.expression;
    if (part.type === 'ExpressionTag' && isAstNode(expression) && expression.type === 'Literal') return typeof expression.value === 'string' ? expression.value : undefined;
    return undefined;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    replay.asked = [];
    replay.answer = null;
    fetchRiskCatalog.mockReset().mockResolvedValue({items: []});
    fetchRiskScenarioCatalog.mockReset().mockResolvedValue(SCENARIO_CATALOG);
    invalidateRisk.mockReset();
    queryRisk.mockReset().mockImplementation(async (request: RiskQueryRequest) => {
        // The base wave the controller fires on mount is answered empty and never counted.
        if (!replayAnalytic(request)) return {items: []};
        replay.asked.push(request);
        if (!replay.answer) throw new Error('the replay was asked, and this test scripted no answer for it');
        return {items: [replay.answer(replayParameters(request).replay_range as ReplayWindow)]};
    });
});

afterEach(() => {
    while (stops.length > 0) stops.pop()?.();
});

describe('L4Replay — the harness itself', () => {
    it('runs effects, and formats in the language the catalogue speaks', () => {
        // Without effects the controller hands over stale state; see the header.
        expect(() => assertEffectsRun()).not.toThrow();
        // Dates and shares are formatted in a language the block reads from a store;
        // the two stores that could carry it agree, so the expectations below do not
        // depend on which one the component reads.
        expect(get(currentLanguage), 'the app language and the catalogue locale disagree: a date could be formatted in one and worded in the other').toBe(get(locale));
    });

    it('has every sentence the block words, the two headers apart, and none of the retired ones', () => {
        // One line per key, so a red names every key that is missing rather than the first.
        expect(Object.fromEntries(NEW_KEYS.map((key) => [key, typeof at(en, key)])), 'keys the block words its sentences with are missing from en.json').toEqual(Object.fromEntries(NEW_KEYS.map((key) => [key, 'string'])));

        const samples: Readonly<Record<string, Values>> = {
            [KEYS.excludedResidual]: {count: 2, weight: formatReplayShare(0.125, lang())},
            [KEYS.excludedOmitted]: {count: 2},
            [KEYS.suggested]: {start: formatReplayDate(SUGGESTED.start, lang()), end: formatReplayDate(SUGGESTED.end, lang()), count: 2},
        };
        // svelte-i18n echoes the id back on a miss, and so would the component: both
        // sides would then "agree" on a key that does not exist.
        for (const key of NEW_KEYS) expect(t(key, samples[key]), `${key} does not resolve: the catalogue is not loaded`).not.toBe(key);
        // If the two headers resolved alike, every "which header" assertion below would be satisfied by either branch.
        expect(t(KEYS.excludedOmitted, samples[KEYS.excludedOmitted]), 'the two headers read alike: which treatment the block named could not be told').not.toBe(t(KEYS.excludedResidual, samples[KEYS.excludedResidual]));
        // Every reason the block orders has a label here, and the seven labels are seven sentences.
        expect(Object.keys(REASON_KEYS).sort()).toEqual([...REPLAY_EXCLUSION_REASON_ORDER].sort());
        const labels = [...Object.values(REASON_KEYS), REASON_OTHER_KEY].map((key) => t(key));
        expect(new Set(labels).size, 'two reasons share a label: which reason a group stands for could not be told').toBe(labels.length);

        // The retired sentences leave every catalogue with the flow they belonged to.
        const leftovers = SUPPORTED_LOCALES.flatMap((code) => RETIRED_KEYS.filter((key) => at(CATALOGUES[code], key) !== undefined).map((key) => `${code}: ${key}`));
        expect(leftovers, 'sentences of the retired exclude-and-retry flow are still in the catalogues').toEqual([]);
    });
});

describe('L4Replay — the period', () => {
    it('is one range picker holding the panel’s window, without quick presets, under its own label', async () => {
        mount('portfolio');

        const period = screen.getByTestId('risk-replay-period');
        // Barrier: the picker itself, inside the period, so the absences below are about it.
        expect(within(period).getByTestId('date-range-picker-root')).toBeInTheDocument();
        expect(await pickerWindow(), 'the picker does not hold the panel’s window').toEqual(WINDOW);
        expect(
            within(period)
                .queryAllByTestId(/^date-preset-/)
                .map((node) => node.getAttribute('data-testid')),
            'the picker shows its own quick presets: a second preset row beside the crisis menu, answering another question (how far back from today)',
        ).toEqual([]);
        expect(period, `the period is not labelled by ${KEYS.period}`).toHaveTextContent(t(KEYS.period));
        // The two single-date pickers it replaces are gone from the whole block.
        expect(
            screen.queryAllByTestId(/^risk-replay-(?:start|end)(?:-|$)/).map((node) => node.getAttribute('data-testid')),
            'the single-date pickers the range picker replaces are still mounted',
        ).toEqual([]);
        expectRetiredControlsGone();
    });

    it('drops the answer on screen when its dates change, and the next run asks over the new window', async () => {
        const controller = mount('portfolio', replayed('portfolio', audit([])));
        expectBars(DEFAULT_BARS, 'the answer meant to be dropped never reached the screen');

        await typeStart(MOVED_START);

        await waitFor(() => expect(controller.replayResult, 'the dates moved and the old answer stayed, replying to a question nobody is asking any more').toBeNull());
        expect(barKeys()).toEqual([]);
        expect(replay.asked, 'moving the dates asked a question by itself').toHaveLength(0);
        expect(await pickerWindow()).toEqual({start: MOVED_START, end: WINDOW.end});

        replay.answer = (window) => replayed('portfolio', audit([]), {range: window});
        await fireEvent.click(screen.getByTestId('risk-replay-run'));
        await waitFor(() => expectBars(DEFAULT_BARS, 'the replay over the new window never reached the screen'));
        expect(replay.asked.map(replayParameters), 'Run did not ask over the window the picker shows').toEqual([expectedParameters({start: MOVED_START, end: WINDOW.end})]);
    });

    it('drops the answer on screen when a crisis is chosen, and takes the crisis’s dates', async () => {
        const controller = mount('portfolio', replayed('portfolio', audit([])));
        await controller.loadScenarioCatalog();
        expectBars(DEFAULT_BARS, 'the answer meant to be dropped never reached the screen');

        await choosePreset(CRISIS.label);

        await waitFor(() => expect(controller.replayResult, 'a crisis was chosen and the old answer stayed, replying to another period').toBeNull());
        expect(barKeys()).toEqual([]);
        expect(replay.asked, 'choosing a crisis asked a question by itself').toHaveLength(0);
        expect(await pickerWindow(), 'the crisis was chosen and the picker does not show its dates').toEqual({start: CRISIS.start, end: CRISIS.end});
    });
});

describe('L4Replay — the crisis menu', () => {
    it('opens where there is room', () => {
        // Markup, not behaviour: jsdom has no layout, so where the menu opens cannot be
        // measured here. What can be read is that the block asks `SimpleSelect` to choose
        // (`dropdownPosition="auto"`), instead of always opening downwards — off screen
        // when the block sits at the bottom of the page.
        const menus = componentsNamed(L4_REPLAY_SOURCE, 'SimpleSelect').filter((node) => constantAttribute(node, 'testId') === 'risk-replay-preset');
        expect(menus, 'L4Replay.svelte holds no SimpleSelect with testId="risk-replay-preset": this check would be reading nothing').toHaveLength(1);
        expect(constantAttribute(menus[0], 'dropdownPosition'), 'the crisis menu does not open where there is room').toBe('auto');
    });
});

describe('L4Replay — Run', () => {
    it('asks once, over the window on screen, with nothing excluded and no stand-in', async () => {
        const controller = mount('portfolio');
        replay.answer = (window) => replayed('portfolio', audit([]), {range: window});

        await fireEvent.click(screen.getByTestId('risk-replay-run'));

        // Barrier: the answer is on screen, so the question log is complete.
        await waitFor(() => expectBars(DEFAULT_BARS, 'the replay answer never reached the screen'));
        expect(controller.replayLoading).toBe(false);
        expect(replay.asked.map(replayParameters), 'one press, one question: over the window, with nothing excluded by hand and no stand-in (D372)').toEqual([expectedParameters(WINDOW)]);
    });
});

describe('L4Replay — the composition total', () => {
    it('states it on a weighted scope, where the backend always sends one', () => {
        mount('portfolio', replayed('portfolio', audit([residual(12, 'no_prices_in_window', 0.125)])));

        expectBars(DEFAULT_BARS);
        expect(screen.getByTestId('risk-replay-total')).toBeVisible();
    });

    it('states it when the weighted replay came out flat, instead of reading the 0.0 as "no answer"', () => {
        // `stress.py` falls back to `portfolio_return = 0.0` rather than to null on a
        // weighted scope, so a guard written as a truthiness check would hide the one
        // honest sentence the reader is owed here.
        mount('portfolio', replayed('portfolio', audit([]), {portfolioReturn: 0}));

        expectBars(DEFAULT_BARS);
        expect(screen.getByTestId('risk-replay-total')).toBeVisible();
    });

    it('withholds it on an unweighted scope rather than printing a dash for the percent', () => {
        mount('asset_set', replayed('asset_set', audit([omitted(12, 'no_prices_in_window')])));

        // The barrier first: the paragraph being absent must mean "the component chose
        // not to render it", not "the component rendered nothing".
        expectBars(DEFAULT_BARS);
        expect(screen.queryAllByTestId('risk-replay-total'), 'the composition total was rendered for a scope that has no composition return').toHaveLength(0);
    });
});

describe('L4Replay — the strong warning', () => {
    it('stands above the total, in the warning’s own words', () => {
        const excluded = [residual(12, 'no_prices_in_window', 0.375), residual(13, 'starts_after_window_start', 0.25)];
        const coverage = coverageWarning(0.625);
        mount('portfolio', replayed('portfolio', audit(excluded), {warnings: [coverage, ...exclusionWarnings(excluded)]}));

        expectBars(DEFAULT_BARS);
        const total = screen.getByTestId('risk-replay-total');
        // The sentence `warningSentence` gives with the translator, as the block must give
        // it. Were the key unknown it would fall back to the backend's English, and the
        // comparison below would agree with a block printing English: hence the guard.
        const expected = normalize(warningSentence(coverage, get(_)));
        expect(expected, 'the coverage warning does not word through its key: the sentence below would be the backend’s English').not.toBe(normalize(coverage.message));

        const line = screen.getByTestId('risk-replay-coverage');
        expect(normalize(line.textContent)).toBe(expected);
        expect(line.compareDocumentPosition(total) & Node.DOCUMENT_POSITION_FOLLOWING, 'the strong warning is read after the figure it qualifies, not before it').toBeTruthy();
        expectRetiredControlsGone();
    });

    it('is not there when the replay covers enough of the portfolio', () => {
        mount('portfolio', replayed('portfolio', audit([residual(12, 'no_prices_in_window', 0.25)])));

        expectBars(DEFAULT_BARS);
        expect(screen.getByTestId('risk-replay-total')).toBeVisible();
        expect(screen.queryAllByTestId('risk-replay-coverage'), 'a coverage warning was drawn for an answer that carries none').toHaveLength(0);
    });
});

describe('L4Replay — what the replay left out', () => {
    it('lists it by reason on a weighted scope, each asset with its share, under the zero-return header', () => {
        const result = replayed('portfolio', audit([residual(13, 'starts_after_window_start', 0.125), residual(12, 'no_prices_in_window', 0.25), residual(UNNAMED, 'no_prices_in_window', 0.0625)]));
        mount('portfolio', result);
        const exclusions = exclusionsOf(result);

        expectBars(DEFAULT_BARS);
        const block = screen.getByTestId('risk-replay-excluded');
        expect(block).toHaveAttribute('data-count', String(exclusions.count));
        expect(block).toHaveAttribute('data-treatment', 'zero_return_residual');
        expect(block).toHaveAttribute('data-weight-total', String(exclusions.weightTotal));
        expectHeader('residual', exclusions);
        expect(groupsOnScreen(block)).toEqual(groupsExpected(exclusions));
        expectItems(block, exclusions);
        expectRetiredControlsGone();
    });

    it('lists it on a selection without a single weight, under the omitted header', () => {
        const result = replayed('asset_set', audit([omitted(13, 'starts_after_window_start'), omitted(UNNAMED, 'stale_at_window_end'), omitted(12, 'no_prices_in_window')]));
        mount('asset_set', result);
        const exclusions = exclusionsOf(result);

        expectBars(DEFAULT_BARS);
        const block = screen.getByTestId('risk-replay-excluded');
        expect(block).toHaveAttribute('data-count', String(exclusions.count));
        expect(block).toHaveAttribute('data-treatment', 'omitted_from_replay');
        // `stress.py` pins the total to 0.0 on an unweighted scope; published, it would say
        // "0% of the scope" about assets that were never weighed.
        expect(block, 'a total weight was published for a selection, which carries no weights').not.toHaveAttribute('data-weight-total');
        expectHeader('omitted', exclusions);
        expect(groupsOnScreen(block)).toEqual(groupsExpected(exclusions));
        expectItems(block, exclusions);
        expectRetiredControlsGone();
    });

    it('says "omitted" as soon as one exclusion was omitted, even beside one carried at zero return', () => {
        // The backend assigns one treatment per scope and does not emit a mixed list
        // today; this pins the block's stated rule, which is the one that decides what
        // happens the day it does.
        const result = replayed('asset_set', audit([residual(11, 'manual_exclusion', 0.03125), omitted(12, 'no_prices_in_window')]));
        mount('asset_set', result);
        const exclusions = exclusionsOf(result);

        expectBars(DEFAULT_BARS);
        const block = screen.getByTestId('risk-replay-excluded');
        expect(block).toHaveAttribute('data-treatment', 'omitted_from_replay');
        expectHeader('omitted', exclusions);
        expect(groupsOnScreen(block)).toEqual(groupsExpected(exclusions));
        expect(
            within(block)
                .getAllByTestId('risk-replay-excluded-asset')
                .map((item) => [item.getAttribute('data-asset-id'), item.getAttribute('data-weight')]),
        ).toEqual(exclusions.groups.flatMap((group) => group.assets.map((asset) => [String(asset.assetId), asset.weight === null ? null : String(asset.weight)])));
    });

    it('labels every reason the engine gives, in the block’s order rather than the order they arrive in', () => {
        // Arriving in the engine's own enum order — the reader's exclusion first — which
        // is not the block's: listing them as they come fails here.
        const result = replayed(
            'portfolio',
            audit([residual(11, 'manual_exclusion', 0.03125), residual(UNNAMED, 'no_prices_in_window', 0.0625), residual(16, 'starts_after_window_start', 0.03125), residual(15, 'stale_at_window_start', 0.0625), residual(13, 'stale_at_window_end', 0.03125), residual(12, 'missing_fx', 0.0625)]),
        );
        mount('portfolio', result);
        const exclusions = exclusionsOf(result);

        expectBars(DEFAULT_BARS);
        const block = screen.getByTestId('risk-replay-excluded');
        const groups = groupsOnScreen(block);
        expect(groups.map((group) => group.reason)).toEqual([...REPLAY_EXCLUSION_REASON_ORDER]);
        expect(groups).toEqual(groupsExpected(exclusions));
        expectItems(block, exclusions);
    });

    it('is not there when nothing was left out', () => {
        mount('portfolio', replayed('portfolio', audit([])));

        expectBars(DEFAULT_BARS);
        // Barrier on the metadata: the amount is printed only because `metadata.scope`
        // was read as a portfolio, so the audit beside it was read too.
        expect(normalize(screen.getByTestId('risk-replay-total').textContent), 'the metadata did not parse: the block could not have read what was left out').toContain(normalize(formatCurrencyAmount(money(PORTFOLIO_RETURN), 'EUR')));
        expect(screen.queryAllByTestId('risk-replay-excluded'), 'a block of exclusions was drawn for a replay that left nothing out').toHaveLength(0);
        expect(screen.queryAllByTestId('risk-replay-excluded-group')).toHaveLength(0);
        expectRetiredControlsGone();
    });
});

describe('L4Replay — nothing left to replay', () => {
    it('says so, lists who and why with their shares, offers the common period, and draws no figure', () => {
        const result = nothingLeft({
            excluded_asset_ids: [12, 13],
            excluded_assets: [
                {asset_id: 12, reason: 'starts_after_window_start', weight: 0.5},
                {asset_id: 13, reason: 'no_prices_in_window', weight: 0.25},
            ],
            suggested_range: {start: SUGGESTED.start, end: SUGGESTED.end},
            suggested_range_recovers: [12],
        });
        mount('portfolio', result);
        const exclusions = exclusionsOf(result);

        // Barrier, and the claim: the refusal was read as "nothing left", not as an error.
        expect(screen.getByTestId('risk-replay-nothing'), `the line is not worded by ${KEYS.nothing}`).toHaveTextContent(t(KEYS.nothing));
        const root = screen.getByTestId('risk-replay');
        expect(groupsOnScreen(root)).toEqual(groupsExpected(exclusions));
        expectItems(root, exclusions);
        // Nothing was replayed, so no figure treated these assets in any way.
        expect(screen.queryAllByTestId('risk-replay-excluded-header'), 'the header names a treatment, and nothing was replayed to treat them').toHaveLength(0);
        expectSuggestionButton(suggestionOf(result));
        expect(screen.queryAllByTestId('risk-replay-total'), 'a figure was drawn for a replay that ran on nothing').toHaveLength(0);
        expect(screen.queryAllByTestId('risk-replay-tornado')).toHaveLength(0);
        expect(screen.queryAllByTestId('risk-replay-coverage')).toHaveLength(0);
        expectRetiredControlsGone();
    });

    it('names a reason it does not know and an asset it has no name for, and offers no period it was not given', () => {
        const result = nothingLeft({
            excluded_asset_ids: [12, UNNAMED],
            excluded_assets: [
                {asset_id: UNNAMED, reason: 'delisted', weight: null},
                {asset_id: 12, reason: 'no_prices_in_window', weight: null},
            ],
        });
        mount('asset_set', result);
        const exclusions = exclusionsOf(result);

        expect(screen.getByTestId('risk-replay-nothing')).toHaveTextContent(t(KEYS.nothing));
        const root = screen.getByTestId('risk-replay');
        expect(groupsOnScreen(root)).toEqual(groupsExpected(exclusions));
        expectItems(root, exclusions);
        expect(screen.queryAllByTestId('risk-replay-suggested'), 'a common period was offered that the backend never proposed').toHaveLength(0);
        expectRetiredControlsGone();
    });
});

describe('L4Replay — the common period', () => {
    const proposing = () => replayed('asset_set', audit([omitted(12, 'starts_after_window_start'), omitted(13, 'stale_at_window_start')], {suggested_range: {start: SUGGESTED.start, end: SUGGESTED.end}, suggested_range_recovers: [12, 13]}));

    it('is one button naming the period and how many it brings back', () => {
        const result = proposing();
        mount('asset_set', result);

        expectBars(DEFAULT_BARS);
        expectSuggestionButton(suggestionOf(result));
        expectRetiredControlsGone();
    });

    it('sets the dates and asks the question in one click, once', async () => {
        const controller = mount('asset_set', proposing());
        expectBars(DEFAULT_BARS, 'the answer carrying the proposal never reached the screen');
        replay.answer = (window) => replayed('asset_set', audit([]), {range: window, impacts: RECOVERED_IMPACTS});

        await fireEvent.click(screen.getByTestId('risk-replay-suggested'));

        // Barrier: the answer over the common period is on screen — the two assets it
        // brought back are among its bars — so the question log is complete.
        await waitFor(() => expectBars(RECOVERED_BARS, 'the answer over the common period never reached the screen: the click did not ask, or asked and dropped the reply'));
        expect(controller.replayLoading).toBe(false);
        expect(replay.asked.map(replayParameters), 'one click must ask exactly one question, over the proposed period, with nothing excluded and no stand-in').toEqual([expectedParameters(SUGGESTED)]);
        expect(await pickerWindow(), 'the question went out over the common period and the picker does not show it').toEqual(SUGGESTED);
    });
});

describe('L4Replay — the note beside the common period', () => {
    it('says the period is only part of the crisis the reader chose', async () => {
        const controller = mount('asset_set');
        await controller.loadScenarioCatalog();
        await choosePreset(CRISIS.label);

        const suggestion = await runAnsweringWith(PART_OF_CRISIS);

        // The premise: the crisis's own dates are the question that was asked.
        expect(replay.asked.map(replayParameters)).toEqual([expectedParameters({start: CRISIS.start, end: CRISIS.end})]);
        expectSuggestionButton(suggestion);
        const note = screen.getByTestId('risk-replay-suggested-partial');
        expect(normalize(note.textContent), `the note is not worded by ${KEYS.suggestedPartial}`).toBe(t(KEYS.suggestedPartial));
    });

    it('is not there over dates the reader set', async () => {
        // The crisis is on offer and the proposal lies inside it; only "not chosen"
        // separates this from the case above.
        const controller = mount('asset_set');
        await controller.loadScenarioCatalog();

        const suggestion = await runAnsweringWith(PART_OF_CRISIS);

        expect(replay.asked.map(replayParameters)).toEqual([expectedParameters(WINDOW)]);
        // Barrier: the button the note would stand beside.
        expectSuggestionButton(suggestion);
        expect(screen.queryAllByTestId('risk-replay-suggested-partial'), 'the note speaks of a crisis the reader never chose').toHaveLength(0);
    });

    it('is not there for a catalogue entry that names no period', async () => {
        const controller = mount('asset_set');
        await controller.loadScenarioCatalog();
        await choosePreset(OPEN_PERIOD.label);

        const suggestion = await runAnsweringWith(PART_OF_CRISIS);

        // The entry names no dates, so the panel's window stands.
        expect(replay.asked.map(replayParameters)).toEqual([expectedParameters(WINDOW)]);
        expectSuggestionButton(suggestion);
        expect(screen.queryAllByTestId('risk-replay-suggested-partial'), 'the note speaks of a crisis for an entry that has no period').toHaveLength(0);
    });

    it('is not there once the chosen crisis was edited by hand, even inside its dates', async () => {
        // The crisis stays chosen in the menu, but the question is no longer the crisis:
        // the note speaks of the period that was asked, not of the preset still shown.
        // Edited inside the crisis, and the proposal lies inside the crisis and is shorter
        // than it — so "is a crisis chosen" and "was the crisis asked" give opposite answers.
        const edited: ReplayWindow = {start: '2020-02-24', end: CRISIS.end};
        const controller = mount('asset_set');
        await controller.loadScenarioCatalog();
        await choosePreset(CRISIS.label);
        await typeStart(edited.start);

        const suggestion = await runAnsweringWith(PART_OF_CRISIS);

        // The premise: the question went out over the edited window, not over the crisis.
        expect(replay.asked.map(replayParameters), 'the run did not ask over the window the reader edited').toEqual([expectedParameters(edited)]);
        // Barrier: the button the note would stand beside.
        expectSuggestionButton(suggestion);
        expect(screen.queryAllByTestId('risk-replay-suggested-partial'), 'the note speaks of the chosen crisis, though the question asked was the window edited by hand').toHaveLength(0);
    });
});

describe('L4Replay — the exclude-and-retry flow is retired', () => {
    it('turns no refusal into a question, not even one shaped like the old blocker', () => {
        // The one payload the retired flow turned into "leave it out and run again": the
        // shape `stress.py` sent before it excluded on its own. It is the payload that
        // proves the flow is gone, because it is the only one that ever summoned it.
        const controller = mount('portfolio', {
            instance_id: 'single-stress',
            analytic_code: 'stress',
            status: 'unavailable',
            output: null,
            error: {code: 'insufficient_history', message: 'Asset 12 requires a manual proxy or explicit exclusion', details: {asset_id: 12, return_source_asset_id: 12, reason: 'insufficient_history'}},
        });

        // Barrier: the block is mounted, ready to run, over a controller holding this refusal.
        expect(controller.replayResult?.status).toBe('unavailable');
        expect(screen.getByTestId('risk-replay-run')).toBeEnabled();
        expectRetiredControlsGone();
        // Not a window that left everything out either: it names no excluded list.
        expect(screen.queryAllByTestId('risk-replay-nothing')).toHaveLength(0);
    });
});
