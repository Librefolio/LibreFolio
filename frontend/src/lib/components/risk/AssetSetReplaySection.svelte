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
     * `riskStore:134` returns the cached *promise*, so identical canonical
     * requests share one flight — and the catalogue is only fetched when the
     * drawer is first opened.
     *
     * **No money crosses this component.** A set of assets carries no weights.
     * `showMoney={false}` is passed even though `L4Replay` already derives it
     * from `metadata.scope` — which `service.py:840` sets on every result, so
     * the derivation is genuinely fail-closed — because an explicit `false`
     * cannot drift if that payload field ever moves.
     *
     * ⚠️ Two sentences inside `L4Replay` still read as though a portfolio were
     * on screen, and they are not fixable from here:
     *   - `:198` renders `replayTotal` — "This composition would have ended the
     *     period at {percent}" — but `stress.py:480-494` leaves
     *     `portfolio_return` null on an unweighted scope, so `{percent}`
     *     degrades to `—`. That is the very failure `L4Replay:42` argues about
     *     for the *amount*: a dash inside a sentence reads as a number that
     *     failed to load, not as one that does not apply.
     *   - `:212` renders `replayAudit` — "({weight} of the scope, carried at
     *     zero return)" — but `stress.py:482` pins `excluded_weight_total` to
     *     0.0 without weights and `:497` marks those assets
     *     `OMITTED_FROM_REPLAY`, so the sentence states a treatment the backend
     *     did not apply.
     * Both are invisible on `portfolio`, where `portfolio_return` is always a
     * number and weights exist. They surface only on the scope that had no
     * mount until this one.
     */
    import {_ as t} from '$lib/i18n';
    import {createRiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
    import L4WhatIf from './levels/L4WhatIf.svelte';
    import L4Replay from './levels/l4/L4Replay.svelte';
    import {degradedResults, levelMetadata, resultReasons} from './levels/levelHelpers';
    import RiskLevelSection from './levels/RiskLevelSection.svelte';

    interface Props {
        /** Already non-empty: the caller's `{#if}` is the guard, see above. */
        assetIds: number[];
        /** Axis names the page already holds. Missing ids degrade to `#id`. */
        assetLabels: ReadonlyMap<number, string>;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
    }

    let {assetIds, assetLabels, dateStart, dateEnd, targetCurrency}: Props = $props();

    const controller = createRiskPanelController(() => ({
        scope: {kind: 'asset_set', asset_ids: assetIds},
        dateStart,
        dateEnd,
        targetCurrency,
        // A replay compounds realised returns; no risk-free rate enters it.
        appliedRiskFreePercent: 0,
        refreshVersion: 0,
    }));

    /** `L4Replay` indexes by id; the page holds a Map, so the shape is adapted here. */
    let assetNames = $derived.by(() => {
        const names: Record<number, string> = {};
        for (const [assetId, label] of assetLabels) names[assetId] = label;
        return names;
    });

    let health = $derived(degradedResults([controller.replayResult]));
    let reasons = $derived(resultReasons([controller.replayResult]));
    let metadata = $derived(levelMetadata([controller.replayResult]));
</script>

<!-- Closed by default and loading its catalogue on first open only: reopening a
     drawer is not a change of question, so it must not start the work over. -->
<RiskLevelSection title={$t('risk.levels.l4.title')} level={4} collapsible testId="risk-replay-section" {health} {reasons} {metadata} onfirstopen={() => controller.loadScenarioCatalog()}>
    <L4WhatIf>
        {#snippet replay()}
            <L4Replay {controller} {assetNames} currency={targetCurrency} {dateStart} {dateEnd} showMoney={false} />
        {/snippet}
    </L4WhatIf>
</RiskLevelSection>
