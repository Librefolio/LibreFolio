<script lang="ts">
    /**
     * L4° for Asset Global — historical replay, and nothing else.
     *
     * **Only the first rung, and that is a design constraint rather than a
     * reduction of effort.** `03-mappa-livelli-pagine` §2 gives this page
     * "historical replay only, in %", and §3.3 says the hypothetical shock is
     * out of scope here. Mounting the shock would carry through the redesign
     * exactly the violation the redesign exists to remove, so it is not omitted
     * for now — it is not available.
     *
     * **The reduction is expressed by supplying fewer snippets, not by a
     * variant.** `L4WhatIf` declares all three rungs optional and guards each
     * with an `{#if}`, so a container that hands it one rung gets one rung, with
     * the same headings, the same `data-distance`, and — because the beta notice
     * lives inside the simulation branch — no model warning over a replay that
     * is simply what happened. The seam for this page was already cut; a
     * `variant` prop on four components, or a fifth component, would both have
     * been new machinery for a joint that existed.
     *
     * **Its own controller, mounted under the caller's `{#if}`, for the reason
     * the correlation section documents**: `loadBase` has no emptiness check, so
     * a controller declared at the panel's top level fires on an empty selection
     * and comes back 422. Two controllers on one scope cost no second request —
     * `queryRisk` in `riskStore` returns the cached *promise*, so identical canonical
     * requests share one flight — and the catalogue is only fetched when the
     * drawer is first opened.
     *
     * **No money crosses this component.** A set of assets carries no weights.
     * `showMoney={false}` is passed even though `L4Replay` already derives it
     * from `metadata.scope` — which the risk service's `_metadata` builder sets
     * on every result (`scope=context.scope_kind`), so
     * the derivation is genuinely fail-closed — because an explicit `false`
     * cannot drift if that payload field ever moves.
     *
     * 📌 Two sentences inside `L4Replay` used to read as though a portfolio were
     * on screen, and this docstring carried the warning until they were fixed.
     * Both are repaired, and the repairs are what this page now relies on:
     *   - the composition total is **withheld**, not degraded. `L4Replay` guards
     *     it with `{#if output.portfolio_return != null}`, and `stress.py` leaves that
     *     null on an unweighted scope — so the sentence does not render at all,
     *     rather than printing a dash that reads like a number which failed to
     *     load. The per-asset bars are the whole answer here.
     *   - the exclusions block **names the treatment the payload actually
     *     carries**: `L4Replay` reads `treatment` off the excluded list and, as
     *     soon as one asset was `omitted_from_replay`, says they were left out of
     *     the replay instead of claiming the carried-at-zero-return handling that
     *     an unweighted scope never gets (D372 moved this from the audit sentence
     *     to the block: `replayExclusions` in `levels/l4/scenarioHelpers.ts`).
     * Both were invisible on `portfolio` and surfaced only on this scope, which
     * had no mount until this one — which is why they are recorded here rather
     * than left to be rediscovered.
     */
    import {untrack} from 'svelte';

    import {_ as t} from '$lib/i18n';
    import {createRiskPanelController, discardedErrorCodes} from '$lib/stores/risk/riskPanelController.svelte';
    import type {AssetSetQualitySource} from './assetSetLevels';
    import L4WhatIf from './levels/L4WhatIf.svelte';
    import L4Replay from './levels/l4/L4Replay.svelte';
    import {replaySectionView} from './levels/l4/scenarioHelpers';
    import {degradedResults, levelMetadata, resultErrorCodes, resultReasons} from './levels/levelHelpers';
    import RiskLevelSection from './levels/RiskLevelSection.svelte';

    interface Props {
        /** Already non-empty: the caller's `{#if}` is the guard, see above. */
        assetIds: number[];
        /** Axis names the page already holds. Missing ids degrade to `#id`. */
        assetLabels: ReadonlyMap<number, string>;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        /** Bumped by the panel after an accepted sync (R2-128). */
        refreshVersion?: number;
    }

    let {assetIds, assetLabels, dateStart, dateEnd, targetCurrency, refreshVersion = 0}: Props = $props();
    const controller = createRiskPanelController(() => ({
        scope: {kind: 'asset_set', asset_ids: assetIds},
        dateStart,
        dateEnd,
        targetCurrency,
        // A replay compounds realised returns; no risk-free rate enters it.
        appliedRiskFreePercent: 0,
        refreshVersion,
    }));

    /**
     * After a sync, the replay on screen was computed on the prices that were just
     * replaced. `refreshVersion` alone only re-reads the base — the controller keeps
     * on-demand answers across a refresh — so this one is forgotten explicitly, the
     * way `handleSynced` forgets every on-demand answer on the single-controller
     * pages. The reader re-runs it on the new data; nothing is re-run for them.
     * The first value is the mount, not a sync, and is skipped.
     */
    let lastRefreshVersion: number | null = null;
    $effect(() => {
        const version = refreshVersion;
        if (lastRefreshVersion !== null && version !== lastRefreshVersion) untrack(() => controller.resetAnalysis('replay'));
        lastRefreshVersion = version;
    });

    /** `L4Replay` indexes by id; the page holds a Map, so the shape is adapted here. */
    let assetNames = $derived.by(() => {
        const names: Record<number, string> = {};
        for (const [assetId, label] of assetLabels) names[assetId] = label;
        return names;
    });

    let health = $derived(degradedResults([controller.replayResult]));
    // The block reads the exclusion and coverage warnings itself, beside the number, and
    // explains a replay with nothing left (D372); the section gets the rest.
    let replayView = $derived(replaySectionView(controller.replayResult));
    let reasons = $derived(resultReasons([replayView], $t));
    // A replay answer discarded on every attempt (the page's live price polling invalidates
    // the cache every 30 s) is disclosed here, as the Dashboard's L4 does, instead of vanishing;
    // and so is a replay that failed outright, a timeout for one.
    let errorCodes = $derived([...resultErrorCodes([replayView]), ...discardedErrorCodes(controller.discarded, ['replay'])]);
    let metadata = $derived(levelMetadata([controller.replayResult]));

    /**
     * What the panel reads through `bind:this`: no results, because this frame keeps its own
     * status and notes (it answers over a period of its own, as L4 on the Dashboard), and its
     * controller's data-quality issues, which the lab's banner merges with the other sections'.
     */
    export function qualitySource(): AssetSetQualitySource {
        return {results: [], labels: {}, issues: controller.dataQualityIssues};
    }
</script>

<!-- Closed by default and loading its catalogue on first open only: reopening a
     drawer is not a change of question, so it must not start the work over. -->
<RiskLevelSection title={$t('risk.levels.l4.title')} level={4} collapsible testId="risk-replay-section" {health} {reasons} {errorCodes} {metadata} onfirstopen={() => controller.loadScenarioCatalog()} docsPath="financial-theory/technical-analysis/risk-metrics/historical-replay/">
    <L4WhatIf>
        {#snippet replay()}
            <L4Replay {controller} {assetNames} currency={targetCurrency} {dateStart} {dateEnd} showMoney={false} />
        {/snippet}
    </L4WhatIf>
</RiskLevelSection>
