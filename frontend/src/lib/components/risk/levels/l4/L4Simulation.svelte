<script lang="ts">
    import {AlertTriangle} from 'lucide-svelte';

    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import type {RenderedSignal} from '$lib/charts/signals';
    import LineChart, {type LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import {riskOutput} from '$lib/risk/riskTypes';
    import {buildSimulationParameters} from '$lib/risk/riskRequest';
    import type {RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';

    import {addDays} from '../../riskAnalysisHelpers';
    import SimulationProvenance from '../SimulationProvenance.svelte';
    import {buildSimulationProvenance} from '../simulationProvenance';
    import {buildDriftUncertainty} from './driftUncertainty';
    import {DEFAULT_SIMULATION_MODE, SIMULATION_MODES, simulationModeSpec, type SimulationMode} from './simulationModes';

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

    let mode = $state<SimulationMode>(DEFAULT_SIMULATION_MODE);
    let horizonDays = $state(365);
    let paths = $state(8192);
    let sampling = $state<'mc' | 'qmc'>('mc');
    let randomSeed = $state(123456);

    let spec = $derived(simulationModeSpec(mode));
    /**
     * Quasi-random sampling is a question only the parametric engine can answer.
     *
     * The resampler is pseudo-random by construction, so the control is not
     * disabled under it — it is absent. A greyed-out choice still tells the
     * reader that the knob is theirs and merely unavailable right now; removing
     * it says the truer thing, that the question does not arise.
     */
    let showSampling = $derived(spec.process === 'gbm');
    /** The Sobol path fixes its own entry point, so there is no seed to type. */
    let showSeed = $derived(spec.process === 'block_bootstrap' || sampling === 'mc');

    let result = $derived(controller.simulationResult);
    let output = $derived(riskOutput(result, schemas.RiskSimulationOutput));
    let provenance = $derived(buildSimulationProvenance(result));
    let terminal = $derived(output?.percentile_bands.at(-1) ?? null);

    /**
     * What the band leaves out: that the drift it rests on is itself an estimate.
     *
     * The arithmetic lives in a sibling module, like the modes and the provenance
     * beside it, because it is the part worth asserting on directly.
     */
    let driftUncertainty = $derived(
        buildDriftUncertainty({
            driftUncertaintyFactor: output?.drift_uncertainty_factor,
            driftUncertaintyObservations: output?.drift_uncertainty_observations,
            terminal,
        }),
    );

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
            parameters: buildSimulationParameters({
                process: spec.process,
                regime: spec.regime,
                samplingMethod: sampling,
                horizonDays,
                pathCount: paths,
                randomSeed,
                sobolStartIndex: SOBOL_START_INDEX,
            }),
        }));
    }

    function chooseMode(next: SimulationMode): void {
        mode = next;
        invalidate();
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
    <!-- The hypothesis sits next to the choice, not behind a hover. A regime is
         *declared*, never estimated: a reader who cannot see the assumption is
         reading a number they believe was derived from their own data. -->
    <fieldset class="space-y-1.5" data-testid="risk-simulation-modes">
        <legend class="mb-1 text-xs font-medium text-gray-700 dark:text-gray-200">{$t('risk.simulation.mode.label')}</legend>
        {#each SIMULATION_MODES as option (option.id)}
            <label
                class="flex cursor-pointer items-start gap-2 rounded-lg border px-3 py-2 {mode === option.id ? 'border-libre-green bg-libre-green/10 dark:bg-libre-green/20' : 'border-gray-300 dark:border-slate-600'}"
                data-testid="risk-simulation-mode"
                data-mode-id={option.id}
                data-selected={mode === option.id}
            >
                <input type="radio" name="risk-simulation-mode" value={option.id} checked={mode === option.id} onchange={() => chooseMode(option.id)} class="mt-0.5 shrink-0" />
                <span class="min-w-0">
                    <span class="flex flex-wrap items-center gap-1.5">
                        <span class="text-sm font-medium text-gray-800 dark:text-gray-100">{$t(`risk.simulation.mode.${option.id}.label`)}</span>
                        {#if option.badge}
                            <span class="rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-gray-600 dark:bg-slate-700 dark:text-gray-300" data-testid="risk-simulation-mode-badge">
                                {$t(`risk.simulation.mode.${option.badge}`)}
                            </span>
                        {/if}
                    </span>
                    <span class="block text-xs text-gray-500 dark:text-gray-400" data-testid="risk-simulation-mode-hypothesis">{$t(`risk.simulation.mode.${option.id}.hypothesis`)}</span>
                </span>
            </label>
        {/each}
    </fieldset>

    <div class="flex flex-wrap items-end gap-3 text-xs text-gray-500 dark:text-gray-400">
        <label class="flex flex-col gap-1">
            {$t('risk.params.horizonDays')}
            <input type="number" min="1" bind:value={horizonDays} onchange={invalidate} class="w-24 rounded border border-gray-200 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700" data-testid="risk-simulation-horizon" />
        </label>
        <label class="flex flex-col gap-1">
            {$t('risk.params.paths')}
            <input type="number" min="1" bind:value={paths} onchange={invalidate} class="w-24 rounded border border-gray-200 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700" data-testid="risk-simulation-paths" />
        </label>
        {#if showSampling}
            <div class="flex flex-col gap-1">
                <span>{$t('risk.params.sampling')}</span>
                <SimpleSelect
                    value={sampling}
                    options={[
                        {value: 'mc', label: $t('risk.levels.l4.provenance.values.mc')},
                        {value: 'qmc', label: $t('risk.levels.l4.provenance.values.qmc')},
                    ]}
                    compact
                    ariaLabel={$t('risk.params.sampling')}
                    onchange={(value) => {
                        sampling = value === 'qmc' ? 'qmc' : 'mc';
                        invalidate();
                    }}
                    testId="risk-simulation-sampling"
                />
            </div>
        {/if}
        {#if showSeed}
            <label class="flex flex-col gap-1">
                {$t('risk.params.randomSeed')}
                <input type="number" bind:value={randomSeed} onchange={invalidate} class="w-28 rounded border border-gray-200 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700" data-testid="risk-simulation-seed" />
            </label>
        {/if}
        <button type="button" class="rounded-lg bg-libre-green px-3 py-1.5 text-sm text-white hover:bg-primary-600 disabled:opacity-50" onclick={run} disabled={controller.simulationLoading} data-testid="risk-simulation-run">
            {$t('risk.actions.simulate')}
        </button>
    </div>

    {#if output}
        <div class="flex flex-wrap gap-4 text-sm" data-testid="risk-simulation-terminal">
            <span class="text-gray-700 dark:text-gray-200">{$t('risk.metrics.terminalMean')}: <strong class="tabular-nums">{signedPercent(output.terminal_mean_return)}</strong></span>
            <span class="text-gray-700 dark:text-gray-200">{$t('risk.metrics.probabilityOfLoss')}: <strong class="tabular-nums">{(output.probability_of_loss * 100).toFixed(1)}%</strong></span>
            {#if terminal}
                <!-- The band, not just its middle: a median alone reads as a
                     prediction, and the whole point of a cone is that it is not one. -->
                <span class="text-gray-500 dark:text-gray-400" data-testid="risk-simulation-band-range">{signedPercent(terminal.p05)} … {signedPercent(terminal.p95)}</span>
            {/if}
        </div>
        {#if driftUncertainty}
            <!-- Adjacent to the numbers it qualifies, above the picture of them:
                 the reader meets the caveat before the cone, not after it. -->
            {#if driftUncertainty.exceedsBand}
                <div class="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-900/20" data-testid="risk-simulation-drift-uncertainty" data-exceeds-band="true">
                    <AlertTriangle size={14} class="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                    <p class="text-xs text-amber-800 dark:text-amber-200">
                        {$t('risk.simulation.driftUncertaintyWide', {values: {count: driftUncertainty.observations, low: signedPercent(driftUncertainty.low), high: signedPercent(driftUncertainty.high)}})}
                    </p>
                </div>
            {:else}
                <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-simulation-drift-uncertainty" data-exceeds-band="false">
                    {$t('risk.simulation.driftUncertainty', {values: {count: driftUncertainty.observations, low: signedPercent(driftUncertainty.low), high: signedPercent(driftUncertainty.high)}})}
                </p>
            {/if}
        {/if}
        <div class="rounded-lg border border-gray-100 p-2 dark:border-slate-700">
            <LineChart data={coneData} overlaySignals={coneOverlay} currency="%" viewMode="percentage" colorByBaseline={false} showGradient={false} height="280px" />
        </div>
        <SimulationProvenance {provenance} />
    {/if}
</div>
