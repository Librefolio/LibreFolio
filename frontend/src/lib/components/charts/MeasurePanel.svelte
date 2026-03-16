<!--
  MeasurePanel — Measurement overlay manager and summary table.

  Features:
  - "Add Measure" button activates measure mode on the chart
  - 2-click placement: 1st click = startDate, 2nd click = endDate
  - List of active measures with remove button
  - Summary table: all signals × all measures with Δabs, Δ%, days, annualized
  - Measures rendered as overlay signals via onmeasureschange callback

  Used in FX detail page (inline foldable panel, below ChartSignalsSection).

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Ruler, Trash2, ChevronDown, Info} from 'lucide-svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {MeasureSignal} from '$lib/charts/signals/MeasureSignal';
    import type {MeasurementResult} from '$lib/charts/signals/MeasureSignal';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Base chart data for value lookups */
        chartData: LineDataPoint[];
        /** Overlay signals currently shown (for summary table) */
        overlaySignals?: RenderedSignal[];
        /** Emits rendered measure signals to be added to chart overlay */
        onmeasureschange?: (measures: RenderedSignal[]) => void;
        /** Emits when measure mode should be toggled */
        onmeasuremodechange?: (active: boolean) => void;
        /** View mode for correct value formatting */
        viewMode?: 'absolute' | 'percentage';
        /** Label for the main signal row (e.g. "🇪🇺 EUR → 🇺🇸 USD") — replaces "Main" */
        pairLabel?: string;
    }

    let {
        chartData,
        overlaySignals = [],
        onmeasureschange,
        onmeasuremodechange,
        viewMode = 'absolute',
        pairLabel = 'Main',
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let measures: MeasureSignal[] = $state([]);
    let pendingStartDate: string | null = $state(null);
    let pendingStartValue: number | null = $state(null);
    let measureActive = $state(false);
    let nextId = $state(0);
    /** Track which measure cards are expanded */
    let expandedIds = $state<Set<string>>(new Set());

    const annualizedTooltipHtml = `<strong>Annualized Return (Δ%/yr)</strong><br/><br/>Computes the equivalent yearly return assuming compound growth over the measurement period.<br/><br/>$\\Delta\\%_{\\text{yr}} = \\left(1 + \\frac{\\Delta\\%}{100}\\right)^{\\frac{365}{\\text{days}}} - 1$<br/><br/>where <em>Δ%</em> is the period return and <em>days</em> is the duration.`;

    // =========================================================================
    // Measure mode
    // =========================================================================

    export function startMeasureMode() {
        measureActive = true;
        pendingStartDate = null;
        pendingStartValue = null;
        onmeasuremodechange?.(true);
    }

    export function stopMeasureMode() {
        measureActive = false;
        pendingStartDate = null;
        pendingStartValue = null;
        onmeasuremodechange?.(false);
    }

    /** Called by parent when chart is clicked in measure mode */
    export function addPoint(date: string, value: number) {
        if (!measureActive) return;

        if (pendingStartDate === null) {
            // First click — set start
            pendingStartDate = date;
            pendingStartValue = value;
        } else {
            // Second click — create measure
            const id = `measure-${nextId++}`;
            // Ensure startDate < endDate
            const [start, end] = pendingStartDate <= date
                ? [pendingStartDate, date]
                : [date, pendingStartDate];

            const measure = new MeasureSignal(
                id,
                MeasureSignal.getDefaultStyle(),
                {startDate: start, endDate: end},
            );
            measures = [...measures, measure];
            emitRendered();
            stopMeasureMode();
        }
    }

    function removeMeasure(id: string) {
        measures = measures.filter(m => m.id !== id);
        emitRendered();
    }

    // =========================================================================
    // Render measures as overlay signals
    // =========================================================================

    function emitRendered() {
        const rendered: RenderedSignal[] = measures.map(m =>
            m.render(chartData, viewMode),
        ).filter(r => r.data.length > 0);
        onmeasureschange?.(rendered);
    }

    // Re-render when chartData or viewMode changes
    $effect(() => {
        void chartData;
        void viewMode;
        if (measures.length > 0) emitRendered();
    });

    // =========================================================================
    // Derived
    // =========================================================================

    /** Measurement results for all active measures */
    let measurements: Array<{measure: MeasureSignal; result: MeasurementResult | null}> = $derived(
        measures.map(m => ({measure: m, result: m.getMeasurement(chartData)}))
    );

    /** Show summary table when we have at least one measure with results */
    let hasResults = $derived(measurements.some(m => m.result !== null));

    // =========================================================================
    // Formatting helpers
    // =========================================================================

    function fmtValue(v: number): string {
        if (Math.abs(v) >= 1) return v.toFixed(4);
        return v.toFixed(6).replace(/\.?0+$/, '');
    }

    function fmtDelta(v: number): string {
        const sign = v >= 0 ? '+' : '';
        return `${sign}${v.toFixed(4)}`;
    }

    function fmtPct(v: number): string {
        const sign = v >= 0 ? '+' : '';
        return `${sign}${v.toFixed(2)}%`;
    }
</script>

<div class="space-y-3">

    <!-- Pending indicator -->
    {#if measureActive && pendingStartDate}
        <div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded px-3 py-1.5 border border-amber-200 dark:border-amber-800">
            📍 Start: {pendingStartDate} ({pendingStartValue?.toFixed(4)}) — click chart for end point
        </div>
    {/if}

    <!-- Measure cards (unified: summary header + expandable table) -->
    {#if measures.length > 0}
        <div class="space-y-2">
            {#each measurements as {measure, result}}
                {@const isExpanded = expandedIds.has(measure.id)}
                <div class="rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                    <!-- Card header: clickable summary -->
                    <div class="flex items-center justify-between gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-700/50
                                hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors cursor-pointer"
                         onclick={() => {
                             const next = new Set(expandedIds);
                             if (next.has(measure.id)) next.delete(measure.id);
                             else next.add(measure.id);
                             expandedIds = next;
                         }}
                         role="button"
                         tabindex="0"
                    >
                        <span class="flex items-center gap-2 text-xs font-mono text-gray-600 dark:text-gray-300">
                            <ChevronDown size={13} class="transition-transform shrink-0 {isExpanded ? 'rotate-180' : ''}" />
                            📏 {measure.params.startDate} → {measure.params.endDate}
                            {#if result}
                                <span class="{result.deltaPct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                                    {fmtPct(result.deltaPct)}
                                </span>
                                <span class="text-gray-400 dark:text-gray-500">· {result.days}d</span>
                            {/if}
                        </span>
                        <button
                            class="p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 rounded transition-colors"
                            title="Remove"
                            onclick={(e) => { e.stopPropagation(); removeMeasure(measure.id); }}
                        >
                            <Trash2 size={13} />
                        </button>
                    </div>

                    <!-- Expanded content: summary table -->
                    {#if isExpanded && result}
                        <table class="w-full text-xs border-t border-gray-200 dark:border-slate-600">
                            <thead>
                                <tr class="bg-gray-50/50 dark:bg-slate-700/30">
                                    <th class="px-3 py-1.5 text-left text-gray-500 dark:text-gray-400 font-medium">Signal</th>
                                    <th class="px-2 py-1.5 text-right text-gray-500 dark:text-gray-400 font-medium">Start</th>
                                    <th class="px-2 py-1.5 text-right text-gray-500 dark:text-gray-400 font-medium">End</th>
                                    <th class="px-2 py-1.5 text-right text-gray-500 dark:text-gray-400 font-medium">Δ Abs</th>
                                    <th class="px-2 py-1.5 text-right text-gray-500 dark:text-gray-400 font-medium">Δ %</th>
                                    <th class="px-2 py-1.5 text-right text-gray-500 dark:text-gray-400 font-medium">
                                        <span class="inline-flex items-center gap-0.5">
                                            Δ%/yr
                                            <Tooltip html={annualizedTooltipHtml} math={true} position="top" maxWidth="350px">
                                                <Info size={11} class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
                                            </Tooltip>
                                        </span>
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Main data row -->
                                <tr class="border-t border-gray-100 dark:border-slate-700/50">
                                    <td class="px-3 py-1.5 font-medium text-gray-700 dark:text-gray-200">{pairLabel}</td>
                                    <td class="px-2 py-1.5 text-right font-mono text-gray-600 dark:text-gray-300">{fmtValue(result.startValue)}</td>
                                    <td class="px-2 py-1.5 text-right font-mono text-gray-600 dark:text-gray-300">{fmtValue(result.endValue)}</td>
                                    <td class="px-2 py-1.5 text-right font-mono {result.deltaAbs >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">{fmtDelta(result.deltaAbs)}</td>
                                    <td class="px-2 py-1.5 text-right font-mono {result.deltaPct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">{fmtPct(result.deltaPct)}</td>
                                    <td class="px-2 py-1.5 text-right font-mono {result.annualizedPct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">{fmtPct(result.annualizedPct)}</td>
                                </tr>
                                <!-- Signal rows -->
                                {#each overlaySignals.filter(s => s.data.length > 0 && (s.yAxisIndex ?? 0) === 0) as signal}
                                    {#if true}
                                        {@const sigResult = measure.getMeasurementForSignal(signal.data)}
                                        {#if sigResult}
                                            <tr class="border-t border-gray-100 dark:border-slate-700/50">
                                                <td class="px-3 py-1.5 text-gray-600 dark:text-gray-300">
                                                    <span style="color: {signal.color}">●</span> {signal.label}
                                                </td>
                                                <td class="px-2 py-1.5 text-right font-mono text-gray-500 dark:text-gray-400">{fmtValue(sigResult.startValue)}</td>
                                                <td class="px-2 py-1.5 text-right font-mono text-gray-500 dark:text-gray-400">{fmtValue(sigResult.endValue)}</td>
                                                <td class="px-2 py-1.5 text-right font-mono {sigResult.deltaAbs >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">{fmtDelta(sigResult.deltaAbs)}</td>
                                                <td class="px-2 py-1.5 text-right font-mono {sigResult.deltaPct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">{fmtPct(sigResult.deltaPct)}</td>
                                                <td class="px-2 py-1.5 text-right font-mono text-gray-400">—</td>
                                            </tr>
                                        {/if}
                                    {/if}
                                {/each}
                            </tbody>
                        </table>
                    {/if}
                </div>
            {/each}
        </div>
    {:else if !measureActive}
        <p class="text-xs text-gray-400 dark:text-gray-500 italic">
            No measures. Click the 📏 ruler icon on the chart to add a measurement.
        </p>
    {/if}
</div>

