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
import {fetchRiskCatalog, fetchRiskScenarioCatalog, hasRiskCapability, invalidateRisk, queryRisk, type RiskAnalyticResult, type RiskCatalogResponse, type RiskMode, type RiskScenarioCatalogResponse, type RiskScope} from '$lib/stores/risk/riskStore.svelte';

import {buildBaseAnalytics, normalizeQualityIssue, resultByCode} from '$lib/components/risk/riskAnalysisHelpers';
import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';

/** The four analyses the user launches by hand, as opposed to the base wave. */
export type OnDemandAnalysis = 'comparison' | 'stress' | 'replay' | 'simulation';

export const ON_DEMAND_ANALYSES: readonly OnDemandAnalysis[] = ['comparison', 'stress', 'replay', 'simulation'];

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
}

export interface RiskControllerOptions {
    /** Called after a sync completes and the base wave has been reloaded. */
    onsynced?: () => void | Promise<void>;
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
    });
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
    let loadError = $state(false);

    let requestGeneration = 0;
    const generations: Record<OnDemandAnalysis, number> = {comparison: 0, stress: 0, replay: 0, simulation: 0};
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
        }
        return inFlight;
    }

    async function loadBase(force: boolean): Promise<void> {
        const generation = ++requestGeneration;
        const {scope, dateStart, dateEnd, targetCurrency, appliedRiskFreePercent} = inputs();
        const hadResults = historicalResults.length > 0 || currentResults.length > 0;
        initialLoading = !hadResults;
        refreshing = hadResults;
        loadError = false;

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
            };
            const historicalAnalytics = buildBaseAnalytics('historical', context);
            const currentAnalytics = buildBaseAnalytics('current_composition', context);

            const [historical, current] = await Promise.all([
                historicalAnalytics.length > 0 ? queryRisk(buildRiskQueryRequest({scope, dateStart, dateEnd, targetCurrency, mode: 'historical', analytics: historicalAnalytics}), force) : null,
                currentAnalytics.length > 0
                    ? queryRisk(
                          buildRiskQueryRequest({
                              scope,
                              dateStart,
                              dateEnd,
                              targetCurrency,
                              mode: 'current_composition',
                              compositionPolicy: 'current_buy_and_hold',
                              analytics: currentAnalytics,
                          }),
                          force,
                      )
                    : null,
            ]);

            if (generation !== requestGeneration) return;
            historicalResults = historical?.items ?? [];
            currentResults = current?.items ?? [];
        } catch (error) {
            console.error('[Risk] Failed to load base analytics:', error);
            if (generation === requestGeneration) loadError = true;
        } finally {
            if (generation === requestGeneration) {
                initialLoading = false;
                refreshing = false;
            }
        }
    }

    async function runSingle(code: string, mode: RiskMode, parameters: RiskAnalyticParameters): Promise<RiskAnalyticResult | null> {
        const {scope, dateStart, dateEnd, targetCurrency} = inputs();
        if (!hasRiskCapability(catalog, code, scope.kind, mode)) return null;
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
        return response?.items?.[0] ?? null;
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
        setLoading(analysis, true);
        try {
            const result = await runSingle(request.code, request.mode, request.parameters);
            if (generation === generations[analysis]) setResult(analysis, result);
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
        invalidateRisk();
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

    const dataQualityIssues = $derived.by<DataQualityIssue[]>(() => {
        const deduped = new Map<string, DataQualityIssue>();
        for (const report of qualityReports) {
            for (const issue of report?.issues ?? []) {
                const normalized = normalizeQualityIssue(issue);
                const key = [normalized.code, normalized.affected_asset_ids?.join(','), normalized.affected_fx_pairs?.join(',')].join('|');
                deduped.set(key, normalized);
            }
        }
        return [...deduped.values()];
    });

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
        get refreshing() {
            return refreshing;
        },
        get loadError() {
            return loadError;
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
        },
        bumpGeneration: (analysis: OnDemandAnalysis) => {
            generations[analysis] += 1;
        },
    };
}

export type RiskPanelController = ReturnType<typeof createRiskPanelController>;
