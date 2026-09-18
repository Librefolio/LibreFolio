<script lang="ts">
    import {SlidersHorizontal} from 'lucide-svelte';

    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {riskOutput} from '$lib/risk/riskTypes';
    import {buildHypotheticalShockParameters, type RiskScenarioDimension} from '$lib/risk/riskRequest';
    import type {RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';

    import {formatCurrencyAmount} from '../../riskAnalysisHelpers';
    import TornadoChart from './TornadoChart.svelte';
    import {shockOptions, shockScenario, tornadoRows, type TornadoRow} from './scenarioHelpers';

    /**
     * L4 rung 2 — hypothetical shock: deterministic, on an assumption stated.
     *
     * The old panel asked the reader to fill in a shock per bucket before
     * anything would run, and **nobody was ever going to do that** (D4). The
     * order is inverted here: a named scenario is one click, and the buckets it
     * implies become visible only when someone asks to see them.
     *
     * That is not merely convenience. A form nobody fills in produces no
     * answers at all, so the level it belongs to is effectively absent — and an
     * absent level reads exactly like a portfolio with nothing to worry about.
     */
    interface Props {
        controller: RiskPanelController;
        assetNames: Record<number, string>;
        currency: string;
    }

    let {controller, assetNames, currency}: Props = $props();

    let presetId = $state('');
    let dimension = $state<RiskScenarioDimension>('asset_class');
    let bucketShocks = $state<Record<string, number>>({});
    let showDetail = $state(false);

    let options = $derived(shockOptions(controller.scenarioCatalog, $currentLanguage));
    let result = $derived(controller.stressResult);
    let output = $derived(riskOutput(result, schemas.RiskStressOutput));
    let rows = $derived(tornadoRows(output));
    let buckets = $derived(Object.keys(bucketShocks).sort((left, right) => left.localeCompare(right)));

    $effect(() => {
        controller.registerLauncher('stress', run);
    });

    async function run(): Promise<void> {
        if (Object.keys(bucketShocks).length === 0) return;
        await controller.runGuarded('stress', () => ({
            code: 'stress',
            mode: 'current_composition',
            parameters: buildHypotheticalShockParameters({dimension, bucketShocks}),
        }));
    }

    /** One click: adopt the scenario's assumption *and* ask the question. */
    async function choose(id: string): Promise<void> {
        const scenario = shockScenario(controller.scenarioCatalog, id);
        if (!scenario) return;
        presetId = id;
        dimension = scenario.dimension as RiskScenarioDimension;
        bucketShocks = {...scenario.bucketShocks};
        await run();
    }

    function editBucket(bucket: string, percent: number): void {
        bucketShocks = {...bucketShocks, [bucket]: percent / 100};
        // The preset no longer describes what is on screen, so it stops claiming
        // to: a named scenario that has been edited is no longer that scenario.
        presetId = '';
        controller.resetAnalysis('stress');
    }

    function rowLabel(row: TornadoRow): string {
        // Bucket ids are already the reader's vocabulary (STOCK, Financials, ITA);
        // the sector/country prettifying the legacy panel does is a separate
        // concern and is listed as debt rather than half-done here.
        if (row.bucketId !== undefined) return row.bucketId;
        return assetNames[row.assetId ?? 0] ?? `#${row.assetId}`;
    }

    function rowAmount(row: TornadoRow): string {
        return row.amount === null ? '' : formatCurrencyAmount(String(row.amount), currency);
    }
</script>

<div class="space-y-3" data-testid="risk-shock">
    <div class="flex flex-wrap gap-2" data-testid="risk-shock-presets">
        {#each options as option (option.value)}
            <button
                type="button"
                class="rounded-full border px-3 py-1 text-xs {presetId === option.value ? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-200' : 'border-gray-200 text-gray-700 dark:border-slate-600 dark:text-gray-200'}"
                onclick={() => choose(option.value)}
                disabled={controller.stressLoading}
                data-testid="risk-shock-preset"
                data-preset-id={option.value}
                data-selected={presetId === option.value}
            >
                {option.label}
            </button>
        {/each}
    </div>

    {#if buckets.length > 0}
        <button type="button" class="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400" onclick={() => (showDetail = !showDetail)} data-testid="risk-shock-detail-toggle" aria-expanded={showDetail}>
            <SlidersHorizontal size={13} />
            {$t(showDetail ? 'risk.levels.l4.shockHideDetail' : 'risk.levels.l4.shockShowDetail')}
        </button>
    {/if}

    {#if showDetail}
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3" data-testid="risk-shock-buckets">
            {#each buckets as bucket (bucket)}
                <div class="flex items-center gap-1.5 text-xs">
                    <span class="min-w-0 flex-1 truncate text-gray-600 dark:text-gray-300" title={bucket}>{bucket}</span>
                    <input
                        type="number"
                        step="1"
                        value={(bucketShocks[bucket] * 100).toFixed(0)}
                        class="w-16 rounded border border-gray-200 px-1 py-0.5 text-right dark:border-slate-600 dark:bg-slate-700"
                        onchange={(event) => editBucket(bucket, Number(event.currentTarget.value))}
                        aria-label={bucket}
                        data-testid="risk-shock-bucket"
                        data-bucket-id={bucket}
                    />
                    <span class="text-gray-400">%</span>
                </div>
            {/each}
            <button type="button" class="col-span-full justify-self-start rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white disabled:opacity-50" onclick={run} disabled={controller.stressLoading} data-testid="risk-shock-run">
                {$t('risk.actions.runScenario')}
            </button>
        </div>
    {/if}

    {#if output}
        <p class="text-sm text-gray-700 dark:text-gray-200" data-testid="risk-shock-total">
            {$t('risk.levels.l4.shockTotal', {
                values: {
                    percent: output.portfolio_return == null ? '—' : `${output.portfolio_return < 0 ? '−' : '+'}${(Math.abs(output.portfolio_return) * 100).toFixed(2)}%`,
                    amount: output.impact_amount == null ? '' : formatCurrencyAmount(output.impact_amount, currency),
                },
            })}
        </p>
        <TornadoChart {rows} label={rowLabel} amount={rowAmount} testId="risk-shock-tornado" />
        {#if output.classification_coverage != null && output.classification_coverage < 1}
            <!-- Coverage below one means some holdings had no bucket to fall in.
                 Unstated, the total would silently speak for less than the whole
                 portfolio while looking as if it spoke for all of it. -->
            <p class="text-xs text-amber-700 dark:text-amber-300" data-testid="risk-shock-coverage">
                {$t('risk.levels.l4.shockCoverage', {values: {percent: `${(output.classification_coverage * 100).toFixed(0)}%`}})}
            </p>
        {/if}
    {/if}
</div>
