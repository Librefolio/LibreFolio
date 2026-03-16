<!--
  MeasurePanel — Measurement overlay manager and summary table.

  Features:
  - 2-click placement: 1st click = startDate, 2nd click = endDate
  - Expandable card per measure: params row, style row, summary table
  - Measures rendered as overlay signals via onmeasureschange callback

  Used in FX detail page (inline foldable panel).
  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Trash2, ChevronDown, CircleHelp} from 'lucide-svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {MeasureSignal} from '$lib/charts/signals/MeasureSignal';
    import type {MeasurementResult} from '$lib/charts/signals/MeasureSignal';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        chartData: LineDataPoint[];
        overlaySignals?: RenderedSignal[];
        onmeasureschange?: (measures: RenderedSignal[]) => void;
        onmeasuremodechange?: (active: boolean) => void;
        viewMode?: 'absolute' | 'percentage';
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
    let expandedIds = $state<Set<string>>(new Set());

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

    export function addPoint(date: string, value: number) {
        if (!measureActive) return;

        if (pendingStartDate === null) {
            pendingStartDate = date;
            pendingStartValue = value;
        } else {
            const id = `measure-${nextId++}`;
            const [start, end] = pendingStartDate <= date
                ? [pendingStartDate, date]
                : [date, pendingStartDate];

            const measure = new MeasureSignal(
                id,
                {
                    ...MeasureSignal.getDefaultStyle(),
                    color: `hsl(${(30 + measures.length * 137.5) % 360}, 70%, 55%)`,
                },
                {startDate: start, endDate: end},
            );
            measures = [...measures, measure];
            // Auto-expand new measure
            const next = new Set(expandedIds);
            next.add(id);
            expandedIds = next;
            emitRendered();
            stopMeasureMode();
        }
    }

    function removeMeasure(id: string) {
        measures = measures.filter(m => m.id !== id);
        emitRendered();
    }

    function updateMeasureStyle(id: string, key: 'color' | 'lineWidth' | 'lineType', value: string | number) {
        const m = measures.find(m => m.id === id);
        if (!m) return;
        (m.style as any)[key] = value;
        measures = [...measures]; // trigger reactivity
        emitRendered();
    }

    // =========================================================================
    // Render
    // =========================================================================

    function emitRendered() {
        const rendered: RenderedSignal[] = measures.map(m =>
            m.render(chartData, viewMode),
        ).filter(r => r.data.length > 0);
        onmeasureschange?.(rendered);
    }

    $effect(() => {
        void chartData;
        void viewMode;
        if (measures.length > 0) emitRendered();
    });

    // =========================================================================
    // Derived
    // =========================================================================

    let measurements: Array<{measure: MeasureSignal; result: MeasurementResult | null}> = $derived(
        measures.map(m => ({measure: m, result: m.getMeasurement(chartData)}))
    );

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

    function toggleExpand(id: string) {
        const next = new Set(expandedIds);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        expandedIds = next;
    }
</script>

<div class="space-y-3">

    <!-- Pending indicator -->
    {#if measureActive && pendingStartDate}
        <div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded px-3 py-1.5 border border-amber-200 dark:border-amber-800">
            📍 {$t('measure.pending', {values: {startDate: pendingStartDate, startValue: pendingStartValue?.toFixed(4) ?? ''}})}
        </div>
    {/if}

    <!-- Measure cards -->
    {#if measures.length > 0}
        <div class="space-y-2">
            {#each measurements as {measure, result}}
                {@const isExpanded = expandedIds.has(measure.id)}
                <div class="rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                    <!-- Card header: clickable summary (button for a11y) -->
                    <button
                        type="button"
                        class="w-full flex items-center justify-between gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-700/50
                                    hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors text-left"
                        onclick={() => toggleExpand(measure.id)}
                    >
                        <span class="flex items-center gap-2 text-xs font-mono text-gray-600 dark:text-gray-300">
                            <ChevronDown size={13} class="transition-transform shrink-0 {isExpanded ? 'rotate-180' : ''}" />
                            📏 {measure.params.startDate} → {measure.params.endDate}
                            {#if result}
                                <span class="{result.deltaPct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                                    {fmtPct(result.deltaPct)}
                                </span>
                                <span class="text-gray-400 dark:text-gray-500">· {result.days}{$t('measure.days', {values: {days: ''}}).replace(/^\s*$/, 'd')}</span>
                            {/if}
                        </span>
                        <span
                            class="p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 rounded transition-colors"
                            role="button"
                            tabindex="-1"
                            title={$t('measure.remove')}
                            onclick={(e) => { e.stopPropagation(); removeMeasure(measure.id); }}
                            onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); removeMeasure(measure.id); }}}
                        >
                            <Trash2 size={13} />
                        </span>
                    </button>

                    <!-- Expanded content -->
                    {#if isExpanded}
                        <!-- Style customization row -->
                        <div class="flex items-center gap-1.5 px-3 py-1.5 border-t border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800">
                            <input
                                type="color"
                                class="w-6 h-6 p-0 border border-gray-200 dark:border-slate-600 rounded cursor-pointer shrink-0"
                                title="Color"
                                value={measure.style.color}
                                oninput={(e) => { updateMeasureStyle(measure.id, 'color', e.currentTarget.value); }}
                            />
                            <div class="flex-1 relative">
                                <button
                                    type="button"
                                    class="w-full h-7 flex items-center cursor-pointer rounded hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors relative"
                                    title="Line style"
                                    onclick={() => {
                                        const types = ['solid', 'dashed', 'dotted'];
                                        const current = measure.style.lineType ?? 'solid';
                                        const next = types[(types.indexOf(current) + 1) % types.length];
                                        updateMeasureStyle(measure.id, 'lineType', next);
                                    }}
                                >
                                    <svg width="100%" height="24" class="absolute inset-0">
                                        <line x1="2%" y1="14" x2="98%" y2="14"
                                              stroke={measure.style.color}
                                              stroke-width={measure.style.lineWidth}
                                              stroke-dasharray={measure.style.lineType === 'dashed' ? '8,4' : measure.style.lineType === 'dotted' ? '2,4' : 'none'}
                                        />
                                    </svg>
                                </button>
                            </div>
                            <select
                                class="text-xs px-1 py-0.5 border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-600 dark:text-gray-300"
                                value={String(measure.style.lineWidth)}
                                onchange={(e) => { updateMeasureStyle(measure.id, 'lineWidth', Number(e.currentTarget.value)); }}
                            >
                                <option value="1">1px</option>
                                <option value="2">2px</option>
                                <option value="3">3px</option>
                            </select>
                        </div>

                        <!-- Summary table -->
                        {#if result}
                        <table class="w-full text-xs border-t border-gray-200 dark:border-slate-600">
                            <thead>
                                <tr class="bg-gray-50/50 dark:bg-slate-700/30">
                                    <th class="px-3 py-1.5 text-left text-gray-500 dark:text-gray-400 font-medium">{$t('measure.table.signal')}</th>
                                    <th class="px-2 py-1.5 text-right text-gray-500 dark:text-gray-400 font-medium">{$t('measure.table.start')}</th>
                                    <th class="px-2 py-1.5 text-right text-gray-500 dark:text-gray-400 font-medium">{$t('measure.table.end')}</th>
                                    <th class="px-2 py-1.5 text-right text-gray-500 dark:text-gray-400 font-medium">Δ Abs</th>
                                    <th class="px-2 py-1.5 text-right text-gray-500 dark:text-gray-400 font-medium">Δ %</th>
                                    <th class="px-2 py-1.5 text-right text-gray-500 dark:text-gray-400 font-medium">
                                        <span class="inline-flex items-center gap-0.5">
                                            {$t('measure.table.annualized')}
                                            <Tooltip text="(1 + Δ%)^(365/days) − 1" position="top" maxWidth="220px">
                                                <CircleHelp size={11} class="text-gray-400 hover:text-libre-green cursor-help transition-colors" />
                                            </Tooltip>
                                        </span>
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr class="border-t border-gray-100 dark:border-slate-700/50">
                                    <td class="px-3 py-1.5 font-medium text-gray-700 dark:text-gray-200">{pairLabel}</td>
                                    <td class="px-2 py-1.5 text-right font-mono text-gray-600 dark:text-gray-300">{fmtValue(result.startValue)}</td>
                                    <td class="px-2 py-1.5 text-right font-mono text-gray-600 dark:text-gray-300">{fmtValue(result.endValue)}</td>
                                    <td class="px-2 py-1.5 text-right font-mono {result.deltaAbs >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">{fmtDelta(result.deltaAbs)}</td>
                                    <td class="px-2 py-1.5 text-right font-mono {result.deltaPct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">{fmtPct(result.deltaPct)}</td>
                                    <td class="px-2 py-1.5 text-right font-mono {result.annualizedPct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">{fmtPct(result.annualizedPct)}</td>
                                </tr>
                                {#each overlaySignals.filter(s => s.data.length > 0 && (s.yAxisIndex ?? 0) === 0) as signal}
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
                                {/each}
                            </tbody>
                        </table>
                        {/if}
                    {/if}
                </div>
            {/each}
        </div>
    {:else if !measureActive}
        <p class="text-xs text-gray-400 dark:text-gray-500 italic">
            {$t('measure.empty')}
        </p>
    {/if}
</div>

