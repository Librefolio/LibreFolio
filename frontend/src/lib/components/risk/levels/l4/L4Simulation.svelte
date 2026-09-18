<script lang="ts">
    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import type {RenderedSignal} from '$lib/charts/signals';
    import LineChart, {type LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {riskOutput} from '$lib/risk/riskTypes';
    import {buildSimulationParameters} from '$lib/risk/riskRequest';
    import type {RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';

    import {addDays} from '../../riskAnalysisHelpers';
    import SimulationProvenance from '../SimulationProvenance.svelte';
    import {buildSimulationProvenance} from '../simulationProvenance';

    /**
     * L4 rung 3 — simulation: a probabilistic model, on the model's assumptions.
     *
     * The furthest rung from observed data, and the only one that is a model.
     * Everything it says is conditional on assumptions the reader did not make,
     * which is why the provenance block below is not an appendix: without it the
     * cone is a picture of the future rather than of a hypothesis.
     */
    interface Props {
        controller: RiskPanelController;
        /** Anchor for the cone's dates: the simulation starts where history ends. */
        dateEnd: string;
    }

    let {controller, dateEnd}: Props = $props();

    /**
     * Where the Sobol sequence is entered, fixed rather than typed.
     *
     * The brief asks for this control to go, and it is right that it should: a
     * Sobol start index is a quant's knob, not a question about a portfolio. But
     * it cannot simply stop being *sent* — `simulation.py:138` refuses a QMC run
     * without one — so the control disappears and the value becomes a constant.
     * A fixed entry point is also the reproducible choice, and the provenance
     * block states the seed either way.
     */
    const SOBOL_START_INDEX = 0;

    let horizonDays = $state(365);
    let paths = $state(8192);
    let sampling = $state<'mc' | 'qmc'>('mc');
    let randomSeed = $state(123456);

    let result = $derived(controller.simulationResult);
    let output = $derived(riskOutput(result, schemas.RiskSimulationOutput));
    let provenance = $derived(buildSimulationProvenance(result));
    let terminal = $derived(output?.percentile_bands.at(-1) ?? null);

    let coneData = $derived.by<LineDataPoint[]>(() => (output?.percentile_bands ?? []).map((point) => ({date: addDays(dateEnd, point.day), value: point.p50 * 100})));

    let coneOverlay = $derived.by<RenderedSignal[]>(() => {
        if (!output) return [];
        return [
            {
                id: 'risk-simulation-band',
                label: $t('risk.simulation.simulated'),
                data: coneData,
                color: '#2563eb',
                lineWidth: 2,
                lineType: 'solid',
                markerStart: null,
                markerEnd: null,
                aggregationProfile: 'band_envelope',
                unit: 'percentage',
                seriesType: 'band',
                bandData: {
                    lower: output.percentile_bands.map((point) => point.p05 * 100),
                    middle: output.percentile_bands.map((point) => point.p50 * 100),
                    upper: output.percentile_bands.map((point) => point.p95 * 100),
                },
            },
        ];
    });

    $effect(() => {
        controller.registerLauncher('simulation', run);
    });

    async function run(): Promise<void> {
        await controller.runGuarded('simulation', () => ({
            code: 'simulation',
            mode: 'current_composition',
            parameters: buildSimulationParameters({samplingMethod: sampling, horizonDays, pathCount: paths, randomSeed, sobolStartIndex: SOBOL_START_INDEX}),
        }));
    }

    /** Any control change makes the standing answer a reply to a different question. */
    function invalidate(): void {
        controller.resetAnalysis('simulation');
    }

    function signedPercent(value: number | null | undefined): string {
        if (value == null || !Number.isFinite(value)) return '—';
        return `${value < 0 ? '−' : '+'}${(Math.abs(value) * 100).toFixed(2)}%`;
    }
</script>

<div class="space-y-3" data-testid="risk-simulation">
    <div class="flex flex-wrap items-end gap-3 text-xs text-gray-500 dark:text-gray-400">
        <label class="flex flex-col gap-1">
            {$t('risk.params.horizonDays')}
            <input type="number" min="1" bind:value={horizonDays} onchange={invalidate} class="w-24 rounded border border-gray-200 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700" data-testid="risk-simulation-horizon" />
        </label>
        <label class="flex flex-col gap-1">
            {$t('risk.params.paths')}
            <input type="number" min="1" bind:value={paths} onchange={invalidate} class="w-24 rounded border border-gray-200 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700" data-testid="risk-simulation-paths" />
        </label>
        <label class="flex flex-col gap-1">
            {$t('risk.params.sampling')}
            <select bind:value={sampling} onchange={invalidate} class="rounded border border-gray-200 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700" data-testid="risk-simulation-sampling">
                <option value="mc">{$t('risk.levels.l4.provenance.values.mc')}</option>
                <option value="qmc">{$t('risk.levels.l4.provenance.values.qmc')}</option>
            </select>
        </label>
        {#if sampling === 'mc'}
            <label class="flex flex-col gap-1">
                {$t('risk.params.randomSeed')}
                <input type="number" bind:value={randomSeed} onchange={invalidate} class="w-28 rounded border border-gray-200 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700" data-testid="risk-simulation-seed" />
            </label>
        {/if}
        <button type="button" class="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white disabled:opacity-50" onclick={run} disabled={controller.simulationLoading} data-testid="risk-simulation-run">
            {$t('risk.actions.simulate')}
        </button>
    </div>

    {#if output}
        <div class="flex flex-wrap gap-4 text-sm" data-testid="risk-simulation-terminal">
            <span class="text-gray-700 dark:text-gray-200">{$t('risk.simulation.terminalMean')}: <strong class="tabular-nums">{signedPercent(output.terminal_mean_return)}</strong></span>
            <span class="text-gray-700 dark:text-gray-200">{$t('risk.simulation.probabilityOfLoss')}: <strong class="tabular-nums">{(output.probability_of_loss * 100).toFixed(1)}%</strong></span>
            {#if terminal}
                <!-- The band, not just its middle: a median alone reads as a
                     prediction, and the whole point of a cone is that it is not one. -->
                <span class="text-gray-500 dark:text-gray-400" data-testid="risk-simulation-band-range">{signedPercent(terminal.p05)} … {signedPercent(terminal.p95)}</span>
            {/if}
        </div>
        <div class="rounded-lg border border-gray-100 p-2 dark:border-slate-700">
            <LineChart data={coneData} overlaySignals={coneOverlay} currency="%" viewMode="percentage" colorByBaseline={false} showGradient={false} height="280px" />
        </div>
        <SimulationProvenance {provenance} />
    {/if}
</div>
