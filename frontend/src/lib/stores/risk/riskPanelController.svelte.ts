/**
 * riskPanelController — the idraulica behind every risk view, with no markup.
 *
 * One controller serves both compositions: the four-level panel that Dashboard
 * and Broker Detail mount, and the reduced legacy panel that still renders the
 * `asset` and `asset_set` scopes. Keeping the plumbing in one place is not tidiness
 * — it is the mitigation for a defect this subsystem has already paid for once.
 *
 * ## The defect this file exists to prevent
 *
 * `RiskAnalysisPanel` used to watch a signature (scope, dates, currency, risk-free
 * rate) and, when it moved, zero the generations, results and loading flags of all
 * four on-demand analyses. Because `dateStart` and `targetCurrency` settle *late*
 * on the asset page, the signature moved **after** the user had pressed a button,
 * and the run they asked for vanished with no chart, no spinner and no error.
 *
 * Dropping the in-flight *answer* is right: it was computed for parameters that no
 * longer hold. Dropping the *request* is not. `applyBaseSignature` therefore records
 * which analyses were in flight before it zeroes anything, and relaunches exactly
 * those afterwards.
 *
 * Splitting the monolith into four level panels would have multiplied the chances of
 * reintroducing it by four. Here it can only be written once, and
 * `riskPanelController.test.ts` holds the line.
 */
import {untrack} from 'svelte';

import {buildRiskAnalyticRequest, buildRiskQueryRequest, canonicalizeScope, type RiskAnalyticParameters} from '$lib/risk/riskRequest';
import {riskDataQuality, type RiskDataQualityReport} from '$lib/risk/riskTypes';
import {
    fetchRiskCatalog,
    fetchRiskScenarioCatalog,
    getRiskQuerySnapshot,
    hasRiskCapability,
    makeRiskRequestKey,
    markRiskStale,
    queryRisk,
    RISK_DISCARD_ATTEMPTS,
    type RiskAnalyticResult,
    type RiskCatalogResponse,
    type RiskMode,
    type RiskScenarioCatalogResponse,
    type RiskScope,
} from '$lib/stores/risk/riskStore.svelte';

import {buildBaseAnalytics, normalizeQualityIssue, resultByCode} from '$lib/components/risk/riskAnalysisHelpers';
import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';

/** The four analyses the user launches by hand, as opposed to the base wave. */
export type OnDemandAnalysis = 'comparison' | 'stress' | 'replay' | 'simulation';

export const ON_DEMAND_ANALYSES: readonly OnDemandAnalysis[] = ['comparison', 'stress', 'replay', 'simulation'];

/** The error code a level shows when one of its on-demand answers was discarded on every attempt
 *  (`RISK_DISCARD_ATTEMPTS`); worded as `risk.errors.answer_discarded`, like every other error
 *  code a level shows. */
export const ANSWER_DISCARDED_CODE = 'answer_discarded';

/**
 * The discarded-answer code for a level whose analyses include a discarded one, once however many.
 *
 * A level cannot say which of its steps lost its answer, and does not need to: the cure is the same
 * — run it again — and one sentence says so.
 */
export function discardedErrorCodes(discarded: Readonly<Record<OnDemandAnalysis, boolean>>, analyses: readonly OnDemandAnalysis[]): string[] {
    return analyses.some((analysis) => discarded[analysis]) ? [ANSWER_DISCARDED_CODE] : [];
}

/**
 * Which level discloses each on-demand analysis: the benchmark comparison under L3, the three
 * what-if steps under L4. Every analysis belongs to exactly one level, so a discarded answer is
 * never disclosed twice, nor nowhere.
 */
export const LEVEL_ON_DEMAND_ANALYSES = {l3: ['comparison'], l4: ['stress', 'replay', 'simulation']} as const satisfies Record<'l3' | 'l4', readonly OnDemandAnalysis[]>;

/** The reactive inputs a host component feeds in; read through a getter so the
 *  controller tracks them instead of capturing a snapshot at construction. */
export interface RiskControllerInputs {
    scope: RiskScope;
    dateStart: string;
    dateEnd: string;
    targetCurrency: string;
    /** Already divided by 100 by the caller? No — percent, as the user typed it. */
    appliedRiskFreePercent: number;
    refreshVersion: number;
    /**
     * The shared L3 benchmark folded into the asset-set wave, when one applies.
     *
     * An **input** and not an option, because it changes *what the numbers mean*:
     * a different reference is a different beta. Options are read once at
     * creation and never re-read, so a benchmark parked there would be chosen by
     * the reader and quietly ignored by the request.
     *
     * Absent on every other surface, and `JSON.stringify` drops `undefined`, so
     * `baseSignature` is byte-identical for callers that never set it.
     */
    assetSetBenchmarkId?: number | null;
}

export interface RiskControllerOptions {
    /** Called after a sync completes and the base wave has been reloaded. */
    onsynced?: () => void | Promise<void>;
    /**
     * Called when a refresh of a base wave already on screen fails (page cache, phase 1): the
     * figures stay up and the host tells the user, with a toast. Without it a failed refresh is
     * reported as today, through `loadError`, which the panels render in place of the levels.
     */
    onrefreshfailed?: () => void;
    /** Called once the scenario catalogue settles, successfully or not, so a host
     *  can seed its editors from the presets it just received. */
    scenarioCatalogLoaded?: () => void;
    /** Loads the scenario catalogue eagerly. The legacy asset view needs it up
     *  front; the level panels ask for it when L4 is first opened. */
    eagerScenarioCatalog?: boolean;
    /**
     * Adds `drawdown_summary` to the historical base wave.
     *
     * Opt-in on purpose: only the four-level composition renders it, and turning
     * it on by default would change what the parked Asset Detail surface puts on
     * the wire without anyone editing Asset Detail.
     */
    includeDrawdownSummary?: boolean;
    /**
     * Adds a second, ~1-month-horizon historical VaR to the base wave, so L1 can
     * state a bad month as something the sample did rather than a scaled bad day.
     */
    includeMonthlyVar?: boolean;
    /**
     * Adds the current-composition KPI wave and the per-asset risk/return points.
     *
     * Opt-in like the two above: L3 is the only surface that reads either, and the
     * pair travels together because the scatter's portfolio dot and the card's
     * Sharpe have to come from the same series or the chart contradicts the cards.
     */
    includeCurrentCompositionRiskReturn?: boolean;
    /**
     * Adds the five per-asset analytics of the asset-set laboratory.
     *
     * Every section of that page turns it on, so their requests are canonically
     * equal and `queryRisk` serves all of them from one flight — the frontend's
     * half of clause ⓪, *one preparation per request*.
     */
    includeAssetSetLevels?: boolean;
    /** L1°'s share of the per-asset wave only (`buildBaseAnalytics`): the lab's loss level, never with the benchmark. */
    includeAssetSetLossLevels?: boolean;
    /** L3°'s share of the per-asset wave only: the KPI, the risk/return pair and the comparison. */
    includeAssetSetPaidLevels?: boolean;
}

/**
 * The signature that decides when results stop being valid. Built from the inputs
 * that change *what the numbers mean*, never from presentation state.
 */
export function baseSignature(inputs: RiskControllerInputs): string {
    return JSON.stringify({
        // The signature must ask the same question the request asks. An unordered
        // slice is the same slice, so canonicalize before comparing: otherwise a
        // reordered `asset_ids` looks like a new question and discards the answers.
        scope: canonicalizeScope(inputs.scope),
        dateStart: inputs.dateStart,
        dateEnd: inputs.dateEnd,
        targetCurrency: inputs.targetCurrency,
        appliedRiskFreePercent: inputs.appliedRiskFreePercent,
        // Omitted from the JSON entirely when undefined, so every surface that
        // does not use a benchmark keeps the signature it had before this field
        // existed.
        assetSetBenchmarkId: inputs.assetSetBenchmarkId ?? undefined,
    });
}

type SingleOutcome = {kind: 'answered'; result: RiskAnalyticResult | null} | {kind: 'unsupported'} | {kind: 'discarded'};

const SEVERITY_RANK: Record<DataQualityIssue['severity'], number> = {info: 0, warning: 1, error: 2};
/** Date-range parameters that widen on a merge instead of keeping the first issue's value. */
const RANGE_PARAMS = ['date_from', 'date_to', 'dates_count'] as const;

type IssueParams = NonNullable<DataQualityIssue['message_params']>;

function isoOrNull(value: unknown): string | null {
    return typeof value === 'string' && value !== '' ? value : null;
}

function numberOrNull(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/** The first issue's parameters, with keys only the next one has added; ranges widen, `count` is set by the caller. */
function mergeParams(first: IssueParams | undefined, next: IssueParams | undefined): IssueParams | undefined {
    if (!first && !next) return undefined;
    const merged: IssueParams = {...(next ?? {}), ...(first ?? {})};
    const from = [isoOrNull(first?.date_from), isoOrNull(next?.date_from)].filter((value): value is string => value !== null).sort();
    const to = [isoOrNull(first?.date_to), isoOrNull(next?.date_to)].filter((value): value is string => value !== null).sort();
    if (from.length > 0) merged.date_from = from[0];
    if (to.length > 0) merged.date_to = to[to.length - 1];
    const datesCount = [numberOrNull(first?.dates_count), numberOrNull(next?.dates_count)].filter((value): value is number => value !== null);
    if (datesCount.length > 0) merged.dates_count = Math.max(...datesCount);
    return merged;
}

/**
 * A copy of the issue's own shape. Not `structuredClone`: the controller's results live in
 * `$state`, so an issue can hold Svelte proxies, which `structuredClone` refuses to clone.
 */
function copyIssue(issue: DataQualityIssue): DataQualityIssue {
    const copy: DataQualityIssue = {...issue};
    if (issue.message_params) copy.message_params = {...issue.message_params};
    if (issue.affected_asset_ids) copy.affected_asset_ids = [...issue.affected_asset_ids];
    if (issue.affected_asset_names) copy.affected_asset_names = [...issue.affected_asset_names];
    if (issue.affected_fx_pairs) copy.affected_fx_pairs = [...issue.affected_fx_pairs];
    return copy;
}

/** Order-insensitive on object keys, order-sensitive on lists: equal JSON after sorting keys. */
function sameIssue(left: DataQualityIssue, right: DataQualityIssue): boolean {
    const canonical = (value: unknown): unknown =>
        Array.isArray(value)
            ? value.map(canonical)
            : value !== null && typeof value === 'object'
              ? Object.fromEntries(
                    Object.entries(value)
                        .filter(([, entry]) => entry !== undefined)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([key, entry]) => [key, canonical(entry)]),
                )
              : value;
    return JSON.stringify(canonical(left)) === JSON.stringify(canonical(right));
}

function combineIssues(first: DataQualityIssue, next: DataQualityIssue): DataQualityIssue {
    const merged: DataQualityIssue = {...first};
    if (first.affected_asset_ids !== undefined || next.affected_asset_ids !== undefined) {
        // Names travel with their ids: the first real name seen for an id wins, and `#<id>` stands in
        // only where no issue named it — and only when some issue carries names at all.
        const ids: number[] = [];
        const names = new Map<number, string>();
        for (const issue of [first, next]) {
            (issue.affected_asset_ids ?? []).forEach((id, index) => {
                if (!ids.includes(id)) ids.push(id);
                const name = issue.affected_asset_names?.[index];
                // A held `#<id>` is a stand-in, not a name: a real one arriving later replaces it.
                if (name !== undefined && name !== `#${id}` && !names.has(id)) names.set(id, name);
            });
        }
        merged.affected_asset_ids = ids;
        if (first.affected_asset_names !== undefined || next.affected_asset_names !== undefined) merged.affected_asset_names = ids.map((id) => names.get(id) ?? `#${id}`);
    }
    if (first.affected_fx_pairs !== undefined || next.affected_fx_pairs !== undefined) {
        const pairs = [...(first.affected_fx_pairs ?? [])];
        for (const pair of next.affected_fx_pairs ?? []) if (!pairs.includes(pair)) pairs.push(pair);
        merged.affected_fx_pairs = pairs;
    }
    if (SEVERITY_RANK[next.severity] > SEVERITY_RANK[first.severity]) merged.severity = next.severity;
    merged.message_params = mergeParams(first.message_params, next.message_params);
    // The count speaks for the list the issue is about: the pairs, else the assets. With neither, each
    // count keeps the larger of its two values, a lower bound since the counted things do not travel —
    // `count` and `message_params.count` separately, so identical issues stay equal to their input.
    const listed = (merged.affected_fx_pairs?.length ?? 0) > 0 ? merged.affected_fx_pairs!.length : (merged.affected_asset_ids?.length ?? 0) > 0 ? merged.affected_asset_ids!.length : null;
    if (first.count != null || next.count != null) merged.count = listed ?? Math.max(numberOrNull(first.count) ?? 0, numberOrNull(next.count) ?? 0);
    if (merged.message_params && 'count' in merged.message_params) {
        merged.message_params = {...merged.message_params, count: listed ?? Math.max(numberOrNull(first.message_params?.count) ?? 0, numberOrNull(next.message_params?.count) ?? 0)};
    }
    if (merged.message_params === undefined) delete merged.message_params;
    return merged;
}

/**
 * Data-quality issues merged on the key the banner renders them by: `code` and `group_key`.
 *
 * `DataQualityBanner` keys each item by `code + group_key`, so two issues sharing that pair would
 * make Svelte throw `each_key_duplicate`. They share it as soon as requests that prepare different
 * windows carry issues — the Asset Global lab's controllers, a base wave beside a replay — each
 * naming the stale assets of its own window. One item per key, naming everything any of them named:
 * - asset ids and FX pairs are unions, in order of first appearance; names stay aligned with their
 *   ids (the first name seen wins, `#<id>` when an issue names none);
 * - `count` and `message_params.count` are the size of the union of the list the issue is about —
 *   the pairs if it has any, else the assets; with neither, the larger count, a lower bound;
 * - the most severe severity wins; everything else comes from the first issue, keys only a later
 *   issue has are added, and a date range widens (`dates_count` keeps the larger, a lower bound,
 *   since the dates themselves do not travel).
 * Identical issues collapse to one, equal to the input — the Dashboard's case, unchanged. Inputs
 * are never mutated. Exported because the lab merges its four controllers with the same rule.
 */
export function mergeQualityIssues(issues: Iterable<DataQualityIssue>): DataQualityIssue[] {
    const merged = new Map<string, DataQualityIssue>();
    for (const issue of issues) {
        const key = `${issue.code}|${issue.group_key ?? ''}`;
        const current = merged.get(key);
        // An issue equal to the one already held adds nothing: skipping it keeps the Dashboard's
        // identical reports equal to their input, whatever shape they arrive in.
        if (current && sameIssue(current, issue)) continue;
        merged.set(key, current ? combineIssues(current, issue) : copyIssue(issue));
    }
    return [...merged.values()];
}

export function createRiskPanelController(inputs: () => RiskControllerInputs, options: RiskControllerOptions = {}) {
    let catalog = $state<RiskCatalogResponse | null>(null);
    let scenarioCatalog = $state<RiskScenarioCatalogResponse | null>(null);
    let scenarioCatalogLoading = $state(false);

    let historicalResults = $state<RiskAnalyticResult[]>([]);
    let currentResults = $state<RiskAnalyticResult[]>([]);

    let comparisonResult = $state<RiskAnalyticResult | null>(null);
    let stressResult = $state<RiskAnalyticResult | null>(null);
    let replayResult = $state<RiskAnalyticResult | null>(null);
    let simulationResult = $state<RiskAnalyticResult | null>(null);

    let comparisonLoading = $state(false);
    let stressLoading = $state(false);
    let replayLoading = $state(false);
    let simulationLoading = $state(false);

    let initialLoading = $state(true);
    let refreshing = $state(false);
    /** The base wave on screen came from the cache (fresh or stale) when the panel had nothing yet:
     *  a host tells its tweened figures to start from their value instead of counting up from 0. */
    let hydratedFromCache = $state(false);
    /** The question the base results on screen answer — the request keys of its two waves — so a
     *  failed refresh keeps them only when they answer the very question that failed. */
    let shownQuestion: string | null = null;
    let loadError = $state(false);
    /** A load whose answer *arrived and was discarded* — the client session or the
     *  cache generation moved while the request was in flight. Kept apart from
     *  `loadError` (nothing failed) and from an empty result (nothing is missing),
     *  for the same reason `catalogState` keeps "slow" apart from "failed": one flag
     *  cannot carry two meanings without lying about one of them. */
    let loadDiscarded = $state(false);

    let requestGeneration = 0;
    const generations: Record<OnDemandAnalysis, number> = {comparison: 0, stress: 0, replay: 0, simulation: 0};
    /** On-demand answers that arrived and were discarded on every attempt — the same fact
     *  `loadDiscarded` states for the base wave, kept per analysis. */
    const discarded = $state<Record<OnDemandAnalysis, boolean>>({comparison: false, stress: false, replay: false, simulation: false});
    let lastBaseSignature = '';
    /**
     * Counts how many times the base signature actually moved.
     *
     * Deliberately *not* a relaunch: the policy above — re-issue only what was in
     * flight — is the right one for a one-off question like a stress run, and a
     * test pins it. But a *standing* choice, such as the shared L3 benchmark, is
     * not a question the reader asked once; it is a setting they expect to keep
     * holding. Its answer is discarded here like every other, so its owner needs
     * to know the ground moved. Exposing the epoch lets that owner re-ask exactly
     * once per move, instead of this module guessing which analyses are standing.
     */
    let baseEpoch = $state(0);
    // Deliberately *not* seeded from `inputs()` here. The factory runs while the
    // host component's `<script>` is still executing, so reading the inputs now
    // would touch `$state` bindings declared further down the file and throw a
    // temporal-dead-zone ReferenceError — which in a Svelte component does not
    // surface as a broken panel but as a page that never renders at all. The
    // first effect seeds it instead.
    let lastRefreshVersion: number | null = null;

    /** The launcher each on-demand analysis is relaunched through after a
     *  signature change. Hosts register them; unregistered ones are simply not
     *  relaunched, which is what the level panels want for a closed L4. */
    const launchers = new Map<OnDemandAnalysis, () => Promise<void>>();

    function setLoading(analysis: OnDemandAnalysis, value: boolean): void {
        if (analysis === 'comparison') comparisonLoading = value;
        else if (analysis === 'stress') stressLoading = value;
        else if (analysis === 'replay') replayLoading = value;
        else simulationLoading = value;
    }

    function setResult(analysis: OnDemandAnalysis, value: RiskAnalyticResult | null): void {
        if (analysis === 'comparison') comparisonResult = value;
        else if (analysis === 'stress') stressResult = value;
        else if (analysis === 'replay') replayResult = value;
        else simulationResult = value;
    }

    function isLoading(analysis: OnDemandAnalysis): boolean {
        if (analysis === 'comparison') return comparisonLoading;
        if (analysis === 'stress') return stressLoading;
        if (analysis === 'replay') return replayLoading;
        return simulationLoading;
    }

    function hasCapability(code: string, mode: RiskMode): boolean {
        return hasRiskCapability(catalog, code, inputs().scope.kind, mode);
    }

    /** Invalidate every on-demand analysis. Returns which of them were in flight,
     *  so the caller can decide whether the user's intent deserves a relaunch. */
    function discardOnDemand(): OnDemandAnalysis[] {
        const inFlight = ON_DEMAND_ANALYSES.filter((analysis) => isLoading(analysis));
        for (const analysis of ON_DEMAND_ANALYSES) {
            generations[analysis] += 1;
            setResult(analysis, null);
            setLoading(analysis, false);
            discarded[analysis] = false;
        }
        return inFlight;
    }

    /** The public entry: the bound on re-asks stays private, so no caller can start past it. */
    function loadBase(force: boolean): Promise<void> {
        return loadBaseAttempt(force, 1);
    }

    async function loadBaseAttempt(force: boolean, attempt: number): Promise<void> {
        const generation = ++requestGeneration;
        const {scope, dateStart, dateEnd, targetCurrency, appliedRiskFreePercent, assetSetBenchmarkId} = inputs();
        const hadResults = historicalResults.length > 0 || currentResults.length > 0;
        initialLoading = !hadResults;
        refreshing = hadResults;
        loadError = false;
        loadDiscarded = false;
        let question: string | null = null;

        try {
            catalog = await fetchRiskCatalog();
            if (generation !== requestGeneration) return;
            // A null catalog is a *failure* to load, not a slow load: without this
            // the panel would sit at data-catalog="pending" forever and every gated
            // section would silently look "not supported".
            if (!catalog) {
                loadError = true;
                return;
            }

            const context = {
                appliedRiskFreePercent,
                hasCapability: (code: string, mode: RiskMode) => hasRiskCapability(catalog, code, scope.kind, mode),
                includeDrawdownSummary: options.includeDrawdownSummary === true,
                includeMonthlyVar: options.includeMonthlyVar === true,
                includeCurrentCompositionRiskReturn: options.includeCurrentCompositionRiskReturn === true,
                includeAssetSetLevels: options.includeAssetSetLevels === true,
                includeAssetSetLossLevels: options.includeAssetSetLossLevels === true,
                includeAssetSetPaidLevels: options.includeAssetSetPaidLevels === true,
                assetSetBenchmarkId: assetSetBenchmarkId ?? null,
            };
            const historicalAnalytics = buildBaseAnalytics('historical', context);
            const currentAnalytics = buildBaseAnalytics('current_composition', context);
            const historicalRequest = historicalAnalytics.length > 0 ? buildRiskQueryRequest({scope, dateStart, dateEnd, targetCurrency, mode: 'historical', analytics: historicalAnalytics}) : null;
            const currentRequest =
                currentAnalytics.length > 0
                    ? buildRiskQueryRequest({
                          scope,
                          dateStart,
                          dateEnd,
                          targetCurrency,
                          mode: 'current_composition',
                          compositionPolicy: 'current_buy_and_hold',
                          analytics: currentAnalytics,
                      })
                    : null;
            question = [historicalRequest ? makeRiskRequestKey(historicalRequest) : '', currentRequest ? makeRiskRequestKey(currentRequest) : ''].join('||');

            // Page cache (E1): whatever the store still holds for this very wave — fresh, or marked
            // stale by a mutation — goes on screen at once, and the requests below refresh it.
            const cachedHistorical = historicalRequest ? getRiskQuerySnapshot(historicalRequest).response : null;
            const cachedCurrent = currentRequest ? getRiskQuerySnapshot(currentRequest).response : null;
            if ((historicalRequest || currentRequest) && (!historicalRequest || cachedHistorical) && (!currentRequest || cachedCurrent)) {
                historicalResults = cachedHistorical?.items ?? [];
                currentResults = cachedCurrent?.items ?? [];
                shownQuestion = question;
                if (initialLoading) hydratedFromCache = true;
                initialLoading = false;
                refreshing = true;
            }

            const [historical, current] = await Promise.all([historicalRequest ? queryRisk(historicalRequest, force) : null, currentRequest ? queryRisk(currentRequest, force) : null]);

            if (generation !== requestGeneration) return;

            // `queryRisk` answers in three ways — a response, a throw, and a *discard*:
            // a null returned when the client session or the cache generation moved
            // while the request was in flight. `?? []` folded that third answer into
            // "no data", which asserts something about the world when the fact is about
            // this client, and `applyBaseSignature` then never re-asked — so a complete,
            // healthy matrix could render as "no result" until the user happened to
            // change the inputs. The first identity resolution alone is enough to arm it
            // (`clientSession.transition` bumps the generation before any resetter runs),
            // which is why it shows up on a reload and never on an in-app navigation.
            //
            // The analytics lengths are not decoration: the ternaries above *also* yield
            // null for "not asked", so without them the two nulls are indistinguishable.
            if ((historicalAnalytics.length > 0 && historical === null) || (currentAnalytics.length > 0 && current === null)) {
                // Re-ask under the generation that did the discarding, up to
                // RISK_DISCARD_ATTEMPTS in all (D374). The guard itself stays: discarding
                // another account's answer is correct. What was missing is that a guard
                // which protects by discarding must be able to say so, or the protection is
                // indistinguishable from an absence of data. A superseded attempt never gets
                // here: the generation check above returns first.
                if (attempt < RISK_DISCARD_ATTEMPTS) {
                    await loadBaseAttempt(force, attempt + 1);
                    return;
                }
                loadDiscarded = true;
                return;
            }

            historicalResults = historical?.items ?? [];
            currentResults = current?.items ?? [];
            shownQuestion = question;
        } catch (error) {
            console.error('[Risk] Failed to load base analytics:', error);
            if (generation === requestGeneration) {
                // Figures of another question (the period or the currency before the change) must
                // not stay under the new inputs: only the refresh of the very question on screen
                // keeps them, with the host's toast.
                const answersThisQuestion = question !== null && question === shownQuestion && (historicalResults.length > 0 || currentResults.length > 0);
                if (answersThisQuestion && options.onrefreshfailed) options.onrefreshfailed();
                else loadError = true;
            }
        } finally {
            if (generation === requestGeneration) {
                initialLoading = false;
                refreshing = false;
            }
        }
    }

    /**
     * One on-demand question, answered in one of three ways — kept apart because `queryRisk`
     * answers in three: a response, a throw, and a *discard* (`null`, when the client session or
     * the cache generation moved while the request was in flight). Folding the discard into "no
     * result" made an analysis vanish without a word, which the live price polling of Asset Global
     * (decision D11) turned from an accident into a routine while it invalidated the cache every 30 s.
     * Since the page cache a poll only marks the answers stale; a session change still discards.
     */
    async function runSingle(code: string, mode: RiskMode, parameters: RiskAnalyticParameters): Promise<SingleOutcome> {
        const {scope, dateStart, dateEnd, targetCurrency} = inputs();
        if (!hasRiskCapability(catalog, code, scope.kind, mode)) return {kind: 'unsupported'};
        const response = await queryRisk(
            buildRiskQueryRequest({
                scope,
                dateStart,
                dateEnd,
                targetCurrency,
                mode,
                compositionPolicy: mode === 'current_composition' ? 'current_buy_and_hold' : undefined,
                analytics: [buildRiskAnalyticRequest(`single-${code}`, code, parameters)],
            }),
        );
        if (response === null) return {kind: 'discarded'};
        return {kind: 'answered', result: response?.items?.[0] ?? null};
    }

    /**
     * Run one on-demand analysis under its own generation guard, so a stale answer
     * can never overwrite a fresh one. `build` returns `null` to decline the run
     * without touching any state — used when a precondition the host owns fails.
     */
    async function runGuarded(analysis: OnDemandAnalysis, build: () => {code: string; mode: RiskMode; parameters: RiskAnalyticParameters} | null): Promise<void> {
        const request = build();
        if (!request) return;
        const generation = ++generations[analysis];
        discarded[analysis] = false;
        setLoading(analysis, true);
        try {
            let outcome = await runSingle(request.code, request.mode, request.parameters);
            // Re-ask, as `loadBase` does, up to RISK_DISCARD_ATTEMPTS in all and only while this
            // run is still the current question: a superseded run leaves everything to the one
            // that replaced it. A throw is never re-asked; it goes to the catch below.
            for (let attempt = 1; attempt < RISK_DISCARD_ATTEMPTS && outcome.kind === 'discarded' && generation === generations[analysis]; attempt += 1) {
                outcome = await runSingle(request.code, request.mode, request.parameters);
            }
            if (generation !== generations[analysis]) return;
            setResult(analysis, outcome.kind === 'answered' ? outcome.result : null);
            discarded[analysis] = outcome.kind === 'discarded';
        } catch (error) {
            console.error(`[Risk] ${analysis} failed:`, error);
            if (generation === generations[analysis]) setResult(analysis, null);
        } finally {
            if (generation === generations[analysis]) setLoading(analysis, false);
        }
    }

    /** Register how an on-demand analysis relaunches itself after a signature
     *  change. A host that never registers one simply never has it relaunched. */
    function registerLauncher(analysis: OnDemandAnalysis, launch: () => Promise<void>): void {
        launchers.set(analysis, launch);
    }

    /**
     * Apply a new base signature. Exported so the regression test can drive it
     * without a component: this is the exact seam where the answers used to be
     * discarded together with the questions.
     */
    function applyBaseSignature(signature: string): void {
        if (signature === lastBaseSignature) return;
        lastBaseSignature = signature;
        baseEpoch += 1;
        const rerun = untrack(() => discardOnDemand());
        untrack(() => {
            void loadBase(false);
            for (const analysis of rerun) void launchers.get(analysis)?.();
        });
    }

    async function loadScenarioCatalog(): Promise<void> {
        if (scenarioCatalog || scenarioCatalogLoading) return;
        scenarioCatalogLoading = true;
        try {
            scenarioCatalog = await fetchRiskScenarioCatalog();
        } catch (error) {
            console.error('[Risk] Failed to load scenario catalog:', error);
        } finally {
            scenarioCatalogLoading = false;
            options.scenarioCatalogLoaded?.();
        }
    }

    async function handleSynced(): Promise<void> {
        // A sync marks the answers stale instead of forgetting them: the figures stay on screen
        // while the base wave is asked again, and the catalogs, which a sync cannot change, stay.
        markRiskStale();
        discardOnDemand();
        await loadBase(true);
        await options.onsynced?.();
    }

    const allResults = $derived(
        [
            resultByCode(historicalResults, 'historical_kpi'),
            resultByCode(historicalResults, 'correlation'),
            resultByCode(historicalResults, 'historical_var'),
            resultByCode(historicalResults, 'drawdown_summary'),
            resultByCode(currentResults, 'risk_contribution'),
            comparisonResult,
            stressResult,
            replayResult,
            simulationResult,
        ].filter((result): result is RiskAnalyticResult => result !== null && result !== undefined),
    );
    const qualityReports = $derived(allResults.map(riskDataQuality).filter((report): report is RiskDataQualityReport => report !== null));

    // One item per banner key across every result, through the shared rule (`mergeQualityIssues`).
    const dataQualityIssues = $derived(mergeQualityIssues(qualityReports.flatMap((report) => (report?.issues ?? []).map(normalizeQualityIssue))));

    const qualityStatus = $derived.by(() => {
        const statuses = qualityReports.map((report) => report?.data_quality_status);
        if (statuses.includes('partial')) return 'partial';
        if (statuses.includes('carried_forward')) return 'carried_forward';
        return statuses.length > 0 ? 'ok' : null;
    });

    $effect(() => {
        applyBaseSignature(baseSignature(inputs()));
    });

    $effect(() => {
        const version = inputs().refreshVersion;
        if (lastRefreshVersion === null) {
            lastRefreshVersion = version;
            return;
        }
        if (version === lastRefreshVersion) return;
        lastRefreshVersion = version;
        untrack(() => void loadBase(true));
    });

    if (options.eagerScenarioCatalog) {
        $effect(() => {
            untrack(() => void loadScenarioCatalog());
        });
    }

    return {
        get catalog() {
            return catalog;
        },

        /** How many times the base signature moved. See the declaration: this is
         *  the signal a standing analysis re-asks itself on. */
        get baseEpoch() {
            return baseEpoch;
        },
        get scenarioCatalog() {
            return scenarioCatalog;
        },
        get historicalResults() {
            return historicalResults;
        },
        get currentResults() {
            return currentResults;
        },
        get comparisonResult() {
            return comparisonResult;
        },
        get stressResult() {
            return stressResult;
        },
        get replayResult() {
            return replayResult;
        },
        get simulationResult() {
            return simulationResult;
        },
        get comparisonLoading() {
            return comparisonLoading;
        },
        get stressLoading() {
            return stressLoading;
        },
        get replayLoading() {
            return replayLoading;
        },
        get simulationLoading() {
            return simulationLoading;
        },
        get initialLoading() {
            return initialLoading;
        },
        get hydratedFromCache() {
            return hydratedFromCache;
        },
        get refreshing() {
            return refreshing;
        },
        get loadError() {
            return loadError;
        },
        /** True when the base load's answer was discarded on every attempt. Distinct from
         *  `loadError` and from an empty result: the cure is to ask again, not to
         *  explain, so a surface reading this should offer the action, not a diagnosis. */
        get loadDiscarded() {
            return loadDiscarded;
        },
        /** Per on-demand analysis: its answer was discarded on every attempt. The same fact as
         *  `loadDiscarded`, and the same cure: ask again. Cleared by a new run of that analysis,
         *  by `resetAnalysis` and whenever the question changes. */
        get discarded(): Readonly<Record<OnDemandAnalysis, boolean>> {
            return discarded;
        },
        /** `ready` | `error` | `pending` — the attribute that separates "slow" from
         *  "failed", which a single `pending` could not say. */
        get catalogState(): 'ready' | 'error' | 'pending' {
            return catalog ? 'ready' : loadError ? 'error' : 'pending';
        },
        get dataQualityIssues() {
            return dataQualityIssues;
        },
        get qualityStatus() {
            return qualityStatus;
        },
        get carriedPricePoints() {
            return Math.max(0, ...qualityReports.map((report) => report?.carried_forward_price_points ?? 0));
        },
        get carriedFxPoints() {
            return Math.max(0, ...qualityReports.map((report) => report?.carried_forward_fx_points ?? 0));
        },
        hasCapability,
        resultFor: (results: RiskAnalyticResult[], code: string) => resultByCode(results, code),
        loadBase,
        loadScenarioCatalog,
        runGuarded,
        registerLauncher,
        applyBaseSignature,
        discardOnDemand,
        handleSynced,
        setResult,
        /** Forget one analysis entirely: its answer, its spinner and its
         *  generation. Used when an editor control changes the question. */
        resetAnalysis: (analysis: OnDemandAnalysis) => {
            generations[analysis] += 1;
            setResult(analysis, null);
            setLoading(analysis, false);
            discarded[analysis] = false;
        },
        bumpGeneration: (analysis: OnDemandAnalysis) => {
            generations[analysis] += 1;
        },
    };
}

export type RiskPanelController = ReturnType<typeof createRiskPanelController>;
