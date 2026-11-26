<script lang="ts">
    import {AlertTriangle} from 'lucide-svelte';

    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import type {RenderedSignal} from '$lib/features/signals';
    import LineChart, {type LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import {todayIso} from '$lib/utils/dateOnly';
    import {riskOutput} from '$lib/features/risk/riskTypes';
    import {buildSimulationParameters} from '$lib/features/risk/riskRequest';
    import type {RiskPanelController} from '$lib/features/risk/riskPanelController.svelte';

    import {addDays} from '../../riskAnalysisHelpers';
    import SimulationHorizonField from '../../SimulationHorizonField.svelte';
    import SimulationProvenance from '../SimulationProvenance.svelte';
    import {buildSimulationProvenance} from '../simulationProvenance';
    import {buildDriftUncertainty} from './driftUncertainty';
    import {clampHistoryPeriod, historyAvailable, initialHistoryPeriod, type HistoryWindow} from './simulationHistory';
    import {DEFAULT_SIMULATION_MODE, SIMULATION_MODES, simulationModeSpec, type SimulationMode} from './simulationModes';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {RISK_OVERLAY_COLORS} from '$lib/theme/chartTheme';
    import {currentLanguage} from '$lib/stores/app/language';
    import {calendarLengthText} from '../../assetSetLevels';
    import {dayFormatter} from '../../eligibility';
    import {uiLocale} from '$lib/stores/app/uiLocale';

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
        /** The cone's anchor when an answer does not say where its history ends (one from before RN-16). */
        dateEnd: string;
    }

    let {controller, dateEnd}: Props = $props();

    /**
     * Where the Sobol sequence is entered, fixed rather than typed.
     *
     * The brief asks for this control to go, and it is right that it should: a
     * Sobol start index is a quant's knob, not a question about a portfolio. But
     * it cannot simply stop being *sent* — `SimulationParams._validate_parametric_params` refuses a QMC run
     * without one — so the control disappears and the value becomes a constant.
     * A fixed entry point is also the reproducible choice, and the provenance
     * block states the seed either way.
     */
    const SOBOL_START_INDEX = 0;

    let mode = $state<SimulationMode>(DEFAULT_SIMULATION_MODE);
    let horizonDays = $state(365);
    let horizonValid = $state(true);
    let paths = $state(8192);
    let sampling = $state<'mc' | 'qmc'>('mc');
    let randomSeed = $state(123456);
    /**
     * RSK-SIM1 (P-7, the developer, 23/11/2026): the period the simulation draws its days from. By default all the common
     * history, as before; in turbulent times the reader may keep only a calmer or a rougher stretch of it. The backend
     * owns the rule and states the window a period may be chosen in; the picker stays inside the last one it stated.
     */
    let historyChosen = $state(false);
    let historyPeriod = $state<HistoryWindow | null>(null);
    let lastAvailable = $state<HistoryWindow | null>(null);

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
    // The window outlives the answer: a control change drops the answer, the picker keeps its bounds.
    $effect(() => {
        const available = historyAvailable(output);
        if (available) lastAvailable = available;
    });
    let availableShown = $derived(lastAvailable ? clampHistoryPeriod(lastAvailable, lastAvailable, todayIso()) : null);

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

    /**
     * The history the simulation was estimated on (RN-16, developer's Q4 c): its own — all the common history, the most
     * recent observations that fit — never the page's period. The line says how long, from when to when, and whether a
     * longer history was left out; the cone starts where that history ends.
     */
    let formatDay = $derived(dayFormatter(uiLocale()));
    let estimation = $derived.by(() => {
        if (!output?.estimation_start || !output.estimation_end || !output.estimation_observations) return null;
        return {
            length: calendarLengthText(output.estimation_start, output.estimation_end, $t, $currentLanguage, output.estimation_observations),
            start: formatDay(output.estimation_start),
            end: formatDay(output.estimation_end),
            count: output.estimation_observations,
            truncated: output.history_truncated === true,
        };
    });
    /** Q5 a: fewer paths than asked when the request did not fit, and said. */
    let pathsReduced = $derived(output && output.requested_path_count != null && output.path_count < output.requested_path_count ? {used: output.path_count, requested: output.requested_path_count} : null);
    /**
     * Where the cone starts: where the data ends, today's composition projected forward. With all the common history that
     * is the last return the simulation read; with a chosen period (RSK-SIM1) the period may end years ago, and the
     * future still starts at the end of the data — the available window's end, never after today.
     */
    let coneStart = $derived.by(() => {
        if (output?.history_chosen === true && output.history_available_end) {
            const today = todayIso();
            return output.history_available_end < today ? output.history_available_end : today;
        }
        return output?.estimation_end ?? dateEnd;
    });

    let coneData = $derived.by<LineDataPoint[]>(() => (output?.percentile_bands ?? []).map((point) => ({date: addDays(coneStart, point.day), value: point.p50 * 100})));

    let coneOverlay = $derived.by<RenderedSignal[]>(() => {
        if (!output) return [];
        return [
            {
                id: 'risk-simulation-band',
                label: $t('risk.simulation.simulated'),
                data: coneData,
                color: RISK_OVERLAY_COLORS.simulation,
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
                historyStart: historyChosen ? (historyPeriod?.start ?? null) : null,
                historyEnd: historyChosen ? (historyPeriod?.end ?? null) : null,
            }),
        }));
    }

    function chooseHistory(chosen: boolean): void {
        historyChosen = chosen;
        if (chosen && !historyPeriod) {
            const today = todayIso();
            historyPeriod = initialHistoryPeriod(lastAvailable, today, addDays(today, -365));
        }
        invalidate();
    }

    function changeHistory(start: string, end: string): void {
        historyPeriod = clampHistoryPeriod({start, end}, lastAvailable, todayIso());
        invalidate();
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
        return `${value < 0 ? '−' : '+'}${formatPercent(Math.abs(value), {scale: 100, signed: false})}`;
    }
</script>

<div class="space-y-3" data-testid="risk-simulation">
    <!-- The hypothesis sits next to the choice, not behind a hover. A regime is
         *declared*, never estimated: a reader who cannot see the assumption is
         reading a number they believe was derived from their own data. -->
    <fieldset class="space-y-1.5" data-testid="risk-simulation-modes">
        <legend class="mb-1 text-xs font-medium text-lf-secondary">{$t('risk.simulation.mode.label')}</legend>
        {#each SIMULATION_MODES as option (option.id)}
            <label class="flex cursor-pointer items-start gap-2 rounded-lg border px-3 py-2 {mode === option.id ? 'border-lf-checked bg-lf-selected' : 'border-lf-input'}" data-testid="risk-simulation-mode" data-mode-id={option.id} data-selected={mode === option.id}>
                <input type="radio" name="risk-simulation-mode" value={option.id} checked={mode === option.id} onchange={() => chooseMode(option.id)} class="mt-0.5 shrink-0" />
                <span class="min-w-0">
                    <span class="flex flex-wrap items-center gap-1.5">
                        <span class="text-sm font-medium text-lf-primary">{$t(`risk.simulation.mode.${option.id}.label`)}</span>
                        {#if option.badge}
                            <span class="rounded-full bg-lf-panel px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-lf-secondary" data-testid="risk-simulation-mode-badge">
                                {$t(`risk.simulation.mode.${option.badge}`)}
                            </span>
                        {/if}
                    </span>
                    <span class="block text-xs text-lf-muted" data-testid="risk-simulation-mode-hypothesis">{$t(`risk.simulation.mode.${option.id}.hypothesis`)}</span>
                </span>
            </label>
        {/each}
    </fieldset>

    <!-- RSK-SIM1: the period the days are drawn from, a row of its own above the parameters (their row is lane 81's). -->
    <!-- min-w-0: a fieldset is as wide as its content by default, and the period picker would push it out of its box on a phone (TL 25/11). -->
    <fieldset class="min-w-0 space-y-1.5 text-xs text-lf-muted" data-testid="risk-simulation-history" data-chosen={historyChosen}>
        <legend class="mb-1 text-xs font-medium text-lf-secondary">{$t('risk.simulation.history.label')}</legend>
        <div class="flex flex-wrap items-center gap-2">
            <!-- The same look as the mode options above: a bordered choice, the selected one tinted. -->
            <label class="flex cursor-pointer items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm text-lf-primary {historyChosen ? 'border-lf-input' : 'border-lf-checked bg-lf-selected'}">
                <input type="radio" name="risk-simulation-history" checked={!historyChosen} onchange={() => chooseHistory(false)} data-testid="risk-simulation-history-all" />
                {$t('risk.simulation.history.all')}
            </label>
            <label class="flex cursor-pointer items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm text-lf-primary {historyChosen ? 'border-lf-checked bg-lf-selected' : 'border-lf-input'}">
                <input type="radio" name="risk-simulation-history" checked={historyChosen} onchange={() => chooseHistory(true)} data-testid="risk-simulation-history-chosen" />
                {$t('risk.simulation.history.chosen')}
            </label>
        </div>
        {#if historyChosen && historyPeriod}
            <div data-testid="risk-simulation-history-period" data-start={historyPeriod.start} data-end={historyPeriod.end}>
                <DateRangePicker start={historyPeriod.start} end={historyPeriod.end} excludePresets={['MAX']} showCustomWindow={false} compact align="start" onchange={changeHistory} />
            </div>
            {#if availableShown}
                <p data-testid="risk-simulation-history-available" data-start={availableShown.start} data-end={availableShown.end}>
                    {$t('risk.simulation.history.available', {values: {start: formatDay(availableShown.start), end: formatDay(availableShown.end)}})}
                </p>
            {/if}
        {/if}
    </fieldset>

    <!-- T-4: on a phone one parameter per row, its label on the left and its field on the right, every field of one width (w-28, 81 U30); from sm up the fields share a row, each with the width it had. -->
    <div class="flex flex-col gap-3 text-xs text-lf-muted sm:flex-row sm:flex-wrap sm:items-end sm:pb-5">
        <SimulationHorizonField bind:days={horizonDays} bind:valid={horizonValid} onchange={invalidate} phoneRow />
        <label class="flex items-center justify-between gap-3 sm:flex-col sm:items-stretch sm:justify-start sm:gap-1" data-testid="risk-simulation-paths-row">
            {$t('risk.params.paths')}
            <input
                type="number"
                min="1"
                bind:value={paths}
                onchange={invalidate}
                class="w-28 sm:w-24 rounded border border-lf-input bg-lf-field px-2 py-1 text-sm text-lf-primary hover:border-lf-input-hover focus:border-lf-focus focus:ring-1 focus:ring-lf-focus"
                data-testid="risk-simulation-paths"
            />
        </label>
        {#if showSampling}
            <div class="flex items-center justify-between gap-3 sm:flex-col sm:items-stretch sm:justify-start sm:gap-1" data-testid="risk-simulation-sampling-row">
                <span>{$t('risk.params.sampling')}</span>
                <SimpleSelect
                    class="w-28 sm:w-auto"
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
            <label class="flex items-center justify-between gap-3 sm:flex-col sm:items-stretch sm:justify-start sm:gap-1" data-testid="risk-simulation-seed-row">
                {$t('risk.params.randomSeed')}
                <input type="number" bind:value={randomSeed} onchange={invalidate} class="w-28 rounded border border-lf-input bg-lf-field px-2 py-1 text-sm text-lf-primary hover:border-lf-input-hover focus:border-lf-focus focus:ring-1 focus:ring-lf-focus" data-testid="risk-simulation-seed" />
            </label>
        {/if}
        <button type="button" class="self-end rounded-lg bg-lf-action px-3 py-1.5 text-sm sm:self-auto text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50" onclick={run} disabled={controller.simulationLoading || !horizonValid} data-testid="risk-simulation-run">
            {$t('risk.actions.simulate')}
        </button>
    </div>

    {#if output}
        {#if estimation}
            <p class="text-xs text-lf-muted" data-testid="risk-simulation-estimation" data-truncated={estimation.truncated} data-history-chosen={output.history_chosen === true}>
                {$t('risk.simulation.estimation', {values: {length: estimation.length, start: estimation.start, end: estimation.end, count: estimation.count}})}
                {#if estimation.truncated}
                    {$t('risk.simulation.estimationTruncated', {values: {count: estimation.count}})}
                {/if}
                {#if output.history_chosen === true}
                    {$t('risk.simulation.history.chosenNote')}
                {/if}
            </p>
        {/if}
        {#if pathsReduced}
            <p class="text-xs text-lf-muted" data-testid="risk-simulation-paths-reduced" data-used={pathsReduced.used} data-requested={pathsReduced.requested}>
                {$t('risk.simulation.pathsReduced', {values: {used: pathsReduced.used, requested: pathsReduced.requested}})}
            </p>
        {/if}
        <div class="flex flex-wrap gap-4 text-sm" data-testid="risk-simulation-terminal">
            <span class="text-lf-secondary">{$t('risk.metrics.terminalMean')}: <strong class="tabular-nums">{signedPercent(output.terminal_mean_return)}</strong></span>
            <span class="text-lf-secondary">{$t('risk.metrics.probabilityOfLoss')}: <strong class="tabular-nums">{formatPercent(output.probability_of_loss, {scale: 100, signed: false, digits: 1})}</strong></span>
            {#if terminal}
                <!-- The band, not just its middle: a median alone reads as a
                     prediction, and the whole point of a cone is that it is not one. -->
                <span class="text-lf-muted" data-testid="risk-simulation-band-range">{signedPercent(terminal.p05)} … {signedPercent(terminal.p95)}</span>
            {/if}
        </div>
        {#if driftUncertainty}
            <!-- Adjacent to the numbers it qualifies, above the picture of them:
                 the reader meets the caveat before the cone, not after it. -->
            {#if driftUncertainty.exceedsBand}
                <div class="flex items-start gap-2 rounded-lg bg-lf-warning-soft px-3 py-2" data-testid="risk-simulation-drift-uncertainty" data-exceeds-band="true">
                    <AlertTriangle size={14} class="mt-0.5 shrink-0 text-lf-warning" />
                    <p class="text-xs text-lf-warning-on-soft">
                        {$t('risk.simulation.driftUncertaintyWide', {values: {count: driftUncertainty.observations, low: signedPercent(driftUncertainty.low), high: signedPercent(driftUncertainty.high)}})}
                    </p>
                </div>
            {:else}
                <p class="text-xs text-lf-muted" data-testid="risk-simulation-drift-uncertainty" data-exceeds-band="false">
                    {$t('risk.simulation.driftUncertainty', {values: {count: driftUncertainty.observations, low: signedPercent(driftUncertainty.low), high: signedPercent(driftUncertainty.high)}})}
                </p>
            {/if}
        {/if}
        <div class="rounded-lg border border-lf-subtle p-2">
            <LineChart data={coneData} overlaySignals={coneOverlay} currency="%" viewMode="percentage" colorByBaseline={false} showGradient={false} height="280px" />
        </div>
        <SimulationProvenance {provenance} />
    {/if}
</div>
