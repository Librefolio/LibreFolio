<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import type {RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
    import type {RiskBenchmarkState} from '$lib/stores/risk/riskBenchmarkStore.svelte';

    import BenchmarkSelect from '../BenchmarkSelect.svelte';

    /**
     * The one benchmark L3 measures against, on every page at once.
     *
     * The choice lives in `riskBenchmark`, not here, because Dashboard and Broker
     * Detail must answer "am I paid for this risk" against the *same* reference.
     * If one said "vs MSCI World" and the other "vs S&P 500" the two pages would
     * stop being comparable, which is the property D10 exists to build.
     *
     * The picker is the shared `BenchmarkSelect` (developer's decision of 01/10/2026):
     * it opens on the stored choice once the asset list confirms it, writes the store,
     * and is the same on every Risk surface. Nothing is left out of its list here:
     * these scopes measure the portfolio, not an asset, so a held asset is a fair
     * benchmark. This component keeps only what is L3's own — when to ask the
     * controller, and against which epoch.
     *
     * Kept out of `L3RiskAdjusted` on purpose: that component renders figures and
     * takes no decisions, so it stays testable as a pure read of the payload.
     */
    interface Props {
        controller: RiskPanelController;
        /**
         * The risk-free rate the page applies, in percent. The benchmark's Sharpe is measured at
         * the same rate as the portfolio's, or its row would rate it on a different footing.
         */
        riskFreePercent: number;
        /**
         * The page's period and currency (D378, developer, 06/10/2026: «uguale su tutte le
         * pagine»). With them the picker asks the engine which benchmarks can be measured over
         * that period, lists the others apart with the engine's reasons, and publishes `blocked`
         * for a stored choice that cannot be measured — which L3 then does not try.
         */
        period: {start: string; end: string};
        currency: string;
    }

    let {controller, riskFreePercent, period, currency}: Props = $props();

    /** The choice in force, resolved by the picker: an id the asset list does not hold reads as null. */
    let selected = $state<number | null>(null);
    /**
     * Only `set` is a benchmark to measure against. `pending` is still being confirmed — with a
     * period, until its verdict arrives — and `blocked` cannot be measured over this period.
     */
    let benchmarkState = $state<RiskBenchmarkState>('none');
    /**
     * The question last asked: the base epoch and the benchmark, as one key.
     *
     * A plain boolean latch would be wrong in both directions. Never re-arming
     * leaves the reader a benchmark *name* standing over an em dash the moment
     * they narrow the period, because a completed on-demand answer is discarded
     * on a signature change and only the in-flight ones are re-issued. Re-arming
     * on "there is no result" instead would spin forever the first time the run
     * legitimately comes back empty. Keying on the epoch and the choice asks
     * exactly once per question, which is the number of times the question changed.
     */
    let askedFor = $state<string | null>(null);

    $effect(() => {
        controller.registerLauncher('comparison', run);
    });

    // Launched by an effect, not at mount nor on the click: the picker confirms a choice
    // asynchronously (`pending` — against the asset list, and with a period against the
    // engine's verdict), and only a confirmed one (`set`) is measured. A stored id that names
    // no asset (`unknown`) and a benchmark that cannot be measured here (`blocked`) are never
    // sent.
    $effect(() => {
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
        if (benchmarkState !== 'set' || selected === null) return;
        const key = `${epoch}|${selected}`;
        // A persisted benchmark that needed a click on every page load would make
        // the persistence worth nothing: the reader would re-choose the same
        // reference twice per visit, and the two pages would disagree in between.
        if (askedFor !== key && ready && !controller.comparisonResult) {
            askedFor = key;
            void run();
        }
    });

    // D378 (developer: «Non lo prova: la riga del benchmark sparisce, e il motivo lo dice solo
    // il selettore»). When the choice stops being measurable here — `blocked`, or `pending`
    // again because the period moved and its new verdict is not in yet — the comparison
    // already on screen goes with it, so the benchmark's row and figures do not outlive the
    // choice that justified them. Bumping first discards a reply still in flight.
    $effect(() => {
        if (benchmarkState === 'set') return;
        if (askedFor === null && !controller.comparisonResult) return;
        askedFor = null;
        controller.bumpGeneration('comparison');
        controller.resetAnalysis('comparison');
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
        // The controller may call this launcher by itself (a re-run on a new period), so the
        // guard is here and not only in the effect: nothing but a confirmed choice is asked.
        //
        // The two rates are `historical_kpi`'s (`riskAnalysisHelpers`), so the benchmark's Sharpe
        // and Sortino stand beside the portfolio's on one footing. They are two because Sortino
        // measures against a target return (the MAR), not against the risk-free rate.
        await controller.runGuarded('comparison', () => (benchmarkState !== 'set' || selected === null ? null : {code: 'comparison', mode: 'current_composition', parameters: {comparison_asset_id: selected, risk_free_annual_rate: riskFreePercent / 100, target_annual_return: 0}}));
    }

    /**
     * After the picker has written the store, `value` and `state` — so `selected` is
     * already the new choice here.
     */
    function choose(next: number | null): void {
        // Bumping first discards the answer to the *previous* question, so a slow
        // reply to the old benchmark cannot land under the new one's name.
        controller.bumpGeneration('comparison');
        controller.resetAnalysis('comparison');
        // Not asked here: the effect asks once the picker confirms the choice as `set` — at
        // once when it already knows the verdict, after it when it is still asking — so a
        // click never asks for what D378 would then drop, and never twice.
        askedFor = null;
    }
</script>

<!-- `data-benchmark-id` is the choice in force, `data-benchmark-state` how far the picker got
     confirming it: republished from the picker, because the rest of this page and its tests
     read L3's benchmark here. -->
<div class="flex items-center gap-2" data-testid="risk-l3-benchmark" data-benchmark-id={selected ?? ''} data-benchmark-state={benchmarkState}>
    <span class="shrink-0 text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l3.benchmark')}</span>
    <div class="min-w-0 max-w-xs flex-1">
        <BenchmarkSelect bind:value={selected} bind:state={benchmarkState} measuredAssetIds={[]} {period} {currency} boxClass="w-full" testid="risk-l3-benchmark-select" onchange={choose} />
    </div>
</div>
