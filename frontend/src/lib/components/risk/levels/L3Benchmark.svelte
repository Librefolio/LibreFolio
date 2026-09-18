<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import type {RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
    import {riskBenchmark} from '$lib/stores/risk/riskBenchmarkStore.svelte';

    /**
     * The one benchmark L3 measures against, on every page at once.
     *
     * The choice lives in `riskBenchmark`, not here, because Dashboard and Broker
     * Detail must answer "am I paid for this risk" against the *same* reference.
     * If one said "vs MSCI World" and the other "vs S&P 500" the two pages would
     * stop being comparable, which is the property D10 exists to build.
     *
     * Kept out of `L3RiskAdjusted` on purpose: that component renders figures and
     * takes no decisions, so it stays testable as a pure read of the payload.
     */
    interface Props {
        controller: RiskPanelController;
        /** Asset ids already in scope, excluded so nothing is compared to itself. */
        excludeAssetIds?: number[];
    }

    let {controller, excludeAssetIds = []}: Props = $props();

    let selected = $state<number | null>(null);
    /**
     * The base epoch the benchmark was last asked for.
     *
     * A plain boolean latch would be wrong in both directions. Never re-arming
     * leaves the reader a benchmark *name* standing over an em dash the moment
     * they narrow the period, because a completed on-demand answer is discarded
     * on a signature change and only the in-flight ones are re-issued. Re-arming
     * on "there is no result" instead would spin forever the first time the run
     * legitimately comes back empty. Keying on the epoch asks exactly once per
     * move of the ground, which is the number of times the question changed.
     */
    let launchedEpoch = $state<number | null>(null);

    $effect(() => {
        controller.registerLauncher('comparison', run);
    });

    // Hydration is deliberately an effect and not an initialiser: the store reads
    // `localStorage`, which does not exist during SSR, and reading it at module
    // evaluation would throw while rendering rather than on the client.
    $effect(() => {
        const stored = riskBenchmark.assetId;
        if (selected === null && stored !== null) selected = stored;
        // `catalogState` is read here for its *dependency*, not just its value.
        // The capability gate in `runSingle` returns null when the catalogue has
        // not landed yet, and it does so silently — so launching before it is
        // ready burns the one attempt and leaves the benchmark shown but never
        // computed. On a cold load this effect runs first, so without this guard
        // the persisted choice only ever worked on client-side navigation, where
        // the catalogue was already cached. Reading it makes the effect re-run
        // the moment it arrives.
        const ready = controller.catalogState === 'ready';
        const epoch = controller.baseEpoch;
        // A persisted benchmark that needed a click on every page load would make
        // the persistence worth nothing: the reader would re-choose the same
        // reference twice per visit, and the two pages would disagree in between.
        if (launchedEpoch !== epoch && ready && selected !== null && !controller.comparisonResult) {
            launchedEpoch = epoch;
            void run();
        }
    });

    async function run(): Promise<void> {
        // `current_composition`, not `historical`, and the reason is measured rather
        // than stylistic. In `historical` the primary series is the portfolio's real
        // TWRR, which on a portfolio built recently is dominated by deposits and by a
        // cash share rather than by markets — against a stock benchmark its
        // correlation collapses towards zero. That is not a weak relationship but the
        // absence of one, so a beta computed there is not an imprecise estimate:
        // there is nothing present to estimate. The same portfolio, the same
        // benchmark and the same days correlate strongly under today's composition.
        //
        // L3 asks "am I being paid for this risk" in the present tense, about the risk
        // held now — so the series has to be the composition held now. The answer is a
        // backtest and says so: the result carries `current_composition_backtest`, and
        // the card declares the perimeter it read rather than assuming one.
        //
        // The measurement that settled it, with its fixture and date, is in the
        // journal under `implementation_2/progress/S3-esecuzione.md`; the figures are
        // not repeated here because the mock dataset moves under them.
        await controller.runGuarded('comparison', () => (selected === null ? null : {code: 'comparison', mode: 'current_composition', parameters: {comparison_asset_id: selected}}));
    }

    function choose(next: number | null): void {
        // Bumping first discards the answer to the *previous* question, so a slow
        // reply to the old benchmark cannot land under the new one's name.
        controller.bumpGeneration('comparison');
        selected = next;
        riskBenchmark.set(next);
        controller.resetAnalysis('comparison');
        // Claim the current epoch so the effect reads this as already asked and
        // does not fire a second, identical request behind the click.
        launchedEpoch = controller.baseEpoch;
        if (next !== null) void run();
    }
</script>

<div class="flex items-center gap-2" data-testid="risk-l3-benchmark" data-benchmark-id={selected ?? ''}>
    <span class="shrink-0 text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l3.benchmark')}</span>
    <div class="min-w-0 max-w-xs flex-1">
        <!-- `sections` and `restLabel` (K3, mandate B) are not in this tree yet.
             They are additive and default to today's behaviour, so the day they
             land this call gains them without changing anything it does now. -->
        <!-- `auto`, because the default `bottom` does not clip the list — it
             *shortens* it. `SearchSelect` already renders the dropdown at a
             computed `position: fixed`, so no ancestor's overflow is involved;
             what it does with `bottom` is set the height to the space below the
             trigger (`dynamicMaxHeight = maxBelow * ITEM_HEIGHT`). Near the foot
             of the page that leaves the two-item floor, and the picker reads as
             truncated. `auto` takes the side with more room instead, which is
             the behaviour asked for: go down while the page allows, else open
             upwards. -->
        <AssetSelect value={selected} compact testid="risk-l3-benchmark-select" dropdownPosition="auto" placeholder={$t('risk.comparison.comparisonAsset')} filter={(asset) => !excludeAssetIds.includes(asset.id)} onchange={choose} />
    </div>
</div>
