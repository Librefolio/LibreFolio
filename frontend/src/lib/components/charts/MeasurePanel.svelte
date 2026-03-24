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
    import {Trash2, ChevronDown} from 'lucide-svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {MeasureSignal} from '$lib/charts/signals/MeasureSignal';
    import type {MeasurementResult} from '$lib/charts/signals/MeasureSignal';
    import {hslToHex} from '$lib/utils/colors';
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    import SignalStyleEditor from './SignalStyleEditor.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type {ColumnDef, HtmlCell} from '$lib/components/table/types';

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
    let pendingMeasure: MeasureSignal | null = $state(null);
    let measureActive = $state(false);
    let nextId = $state(0);
    let expandedIds = $state<Set<string>>(new Set());
    let measureTableRefs = $state<Record<string, DataTable<MeasureSummaryRow> | undefined>>({});

    // Responsive breakpoint for tablet layout (<640px)
    let isNarrow = $state(false);
    $effect(() => {
        const mql = window.matchMedia('(max-width: 639px)');
        isNarrow = mql.matches;
        const handler = (e: MediaQueryListEvent) => { isNarrow = e.matches; };
        mql.addEventListener('change', handler);
        return () => mql.removeEventListener('change', handler);
    });

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
        pendingMeasure = null;
        onmeasuremodechange?.(false);
        emitRendered(); // clear pending preview
    }

    /** Called from parent on mousemove to update live preview line */
    export function updatePendingEnd(date: string, value: number) {
        if (!measureActive || pendingStartDate === null) return;
        if (date === pendingStartDate) return; // no zero-length measure
        const [s, e] = pendingStartDate <= date
            ? [pendingStartDate, date]
            : [date, pendingStartDate];
        pendingMeasure = new MeasureSignal(
            '__pending__',
            {
                ...MeasureSignal.getDefaultStyle(),
                color: hslToHex((30 + measures.length * 137.5) % 360, 70, 55),
                lineType: 'dashed',
            },
            {startDate: s, endDate: e},
        );
        emitRendered();
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
                    color: hslToHex((30 + measures.length * 137.5) % 360, 70, 55),
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

    function updateMeasureStyle(id: string, key: keyof import('$lib/charts/signals').SignalStyle, value: any) {
        const m = measures.find(m => m.id === id);
        if (!m) return;
        (m.style as any)[key] = value;
        measures = [...measures]; // trigger reactivity
        emitRendered();
    }

    function updateMeasureDates(id: string, newStart: string, newEnd: string) {
        const m = measures.find(m => m.id === id);
        if (!m) return;
        // Ensure start <= end
        const [s, e] = newStart <= newEnd ? [newStart, newEnd] : [newEnd, newStart];
        if (s === e) return; // measure needs 2 different days
        // Update dates on the object (mutation, no reactivity trigger yet)
        m.params.startDate = s;
        m.params.endDate = e;
        // Check if the new range produces a valid measurement BEFORE triggering reactivity
        const check = m.getMeasurement(chartData);
        if (!check) {
            // Auto-delete: range doesn't have matching data points for start/end
            removeMeasure(id);
            return;
        }
        measures = [...measures]; // trigger reactivity only if valid
        emitRendered();
    }

    // =========================================================================
    // Render
    // =========================================================================

    function emitRendered() {
        const rendered: RenderedSignal[] = measures.map(m =>
            m.render(chartData, viewMode),
        ).filter(r => r.data.length > 0);
        // Include pending preview (live measure during placement)
        if (pendingMeasure) {
            const preview = pendingMeasure.render(chartData, viewMode);
            if (preview.data.length > 0) rendered.push(preview);
        }
        onmeasureschange?.(rendered);
    }

    $effect(() => {
        void chartData;
        void viewMode;
        if (measures.length > 0) {
            // Auto-delete measures whose start/end dates are no longer in chartData
            const valid = measures.filter(m => m.getMeasurement(chartData) !== null);
            if (valid.length < measures.length) {
                measures = valid;
            }
            emitRendered();
        }
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

    // =========================================================================
    // Measure summary table (DataTable)
    // =========================================================================

    interface MeasureSummaryRow {
        id: string;
        signal: string;
        signalColor: string | null;
        valueStart: number;
        valueEnd: number;
        deltaAbs: number;
        deltaPct: number;
        annualizedPct: number | null;
    }

    function colorClass(v: number): string {
        return v >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400';
    }

    function htmlNum(v: number, formatter: (n: number) => string): HtmlCell {
        return {type: 'html', html: `<span class="font-mono ${colorClass(v)}">${formatter(v)}</span>`};
    }

    const summaryColumns: ColumnDef<MeasureSummaryRow>[] = [
        {
            id: 'signal', header: () => $t('measure.table.signal'), type: 'text',
            cell: (r) => ({type: 'html', html: r.signalColor ? `<span style="color:${r.signalColor}">●</span> ${r.signal}` : `<span class="font-medium">${r.signal}</span>`}),
            sortable: false, filterable: false, width: 100,
        },
        {
            id: 'valueStart', header: () => $t('common.start'), type: 'number',
            cell: (r) => ({type: 'html', html: `<span class="font-mono text-right text-gray-600 dark:text-gray-300">${fmtValue(r.valueStart)}</span>`}),
            getValue: (r) => r.valueStart, sortable: true, filterable: true, width: 90,
        },
        {
            id: 'valueEnd', header: () => $t('common.end'), type: 'number',
            cell: (r) => ({type: 'html', html: `<span class="font-mono text-right text-gray-600 dark:text-gray-300">${fmtValue(r.valueEnd)}</span>`}),
            getValue: (r) => r.valueEnd, sortable: true, filterable: true, width: 90,
        },
        {
            id: 'deltaAbs', header: () => $t('measure.table.deltaAbs'), type: 'number',
            cell: (r) => htmlNum(r.deltaAbs, fmtDelta),
            getValue: (r) => r.deltaAbs, sortable: true, filterable: true, width: 80,
        },
        {
            id: 'deltaPct', header: () => $t('measure.table.deltaPct'), type: 'number',
            cell: (r) => htmlNum(r.deltaPct, fmtPct),
            getValue: (r) => r.deltaPct, sortable: true, filterable: true, width: 80,
        },
        {
            id: 'annualizedPct', header: () => $t('measure.table.annualized'), type: 'number',
            headerTooltip: '$\\large (1 + \\Delta\\%)^{\\frac{365}{d}} - 1$',
            cell: (r) => r.annualizedPct !== null
                ? htmlNum(r.annualizedPct, fmtPct)
                : ({type: 'html', html: '<span class="text-gray-400">—</span>'}),
            getValue: (r) => r.annualizedPct ?? 0, sortable: true, filterable: true, width: 80,
        },
    ];

    function buildSummaryRows(result: MeasurementResult, measureObj: MeasureSignal): MeasureSummaryRow[] {
        const rows: MeasureSummaryRow[] = [
            {
                id: 'main',
                signal: pairLabel,
                signalColor: null,
                valueStart: result.startValue,
                valueEnd: result.endValue,
                deltaAbs: result.deltaAbs,
                deltaPct: result.deltaPct,
                annualizedPct: result.annualizedPct,
            },
        ];
        for (const signal of overlaySignals.filter(s => s.data.length > 0 && (s.yAxisIndex ?? 0) === 0)) {
            const sigResult = measureObj.getMeasurementForSignal(signal.data);
            if (sigResult) {
                rows.push({
                    id: `sig-${signal.label}`,
                    signal: signal.label,
                    signalColor: signal.color,
                    valueStart: sigResult.startValue,
                    valueEnd: sigResult.endValue,
                    deltaAbs: sigResult.deltaAbs,
                    deltaPct: sigResult.deltaPct,
                    annualizedPct: sigResult.annualizedPct,
                });
            }
        }
        return rows;
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
                <div class="rounded-lg border border-gray-200 dark:border-slate-600 overflow-visible">
                    <!-- Card header: responsive layout (wide=1 row, tablet=2 rows via stacked DRP) -->
                    <div
                        class="flex {isNarrow ? 'items-stretch' : 'items-center'} gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-700/50
                                    hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                    >
                        <!-- 1. Chevron -->
                        <button
                            type="button"
                            class="flex items-center text-xs font-mono text-gray-600 dark:text-gray-300 shrink-0 self-center"
                            onclick={() => toggleExpand(measure.id)}
                        >
                            <ChevronDown size={13} class="transition-transform shrink-0 {isExpanded ? 'rotate-180' : ''}" />
                        </button>

                        <!-- 2. DateRangePicker (or collapsed summary) -->
                        {#if isExpanded}
                            <!-- svelte-ignore a11y_no_static_element_interactions -->
                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                            <div class="min-w-0 max-w-[300px] shrink-0 self-center" onclick={(e) => e.stopPropagation()}>
                                <DateRangePicker
                                    start={String(measure.params.startDate)}
                                    end={String(measure.params.endDate)}
                                    showPresets={false}
                                    showCustomWindow={false}
                                    compact={true}
                                    stacked={isNarrow}
                                    onchange={(s, e) => updateMeasureDates(measure.id, s, e)}
                                />
                            </div>
                        {:else}
                            <!-- svelte-ignore a11y_no_static_element_interactions -->
                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                            <span class="flex items-center gap-2 text-xs font-mono text-gray-600 dark:text-gray-300 cursor-pointer self-center" onclick={() => toggleExpand(measure.id)}>
                                📏 {measure.params.startDate} → {measure.params.endDate}
                                {#if result}
                                    <span class="{result.deltaPct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                                        {fmtPct(result.deltaPct)}
                                    </span>
                                    <span class="text-gray-400 dark:text-gray-500">· {result.days}{$t('measure.days', {values: {days: ''}}).replace(/^\s*$/, 'd')}</span>
                                {/if}
                            </span>
                        {/if}

                        <!-- 3. Stats + Style wrapper (flex-1 fills remaining space) -->
                        <div class="flex-1 flex {isNarrow ? 'flex-col justify-between items-end' : 'items-center gap-2'} min-w-0">
                            {#if result}
                                <div class="flex items-center gap-2 shrink-0 {isExpanded ? '' : 'hidden'}">
                                    <span class="text-xs font-mono shrink-0 {result.deltaPct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                                        {fmtPct(result.deltaPct)}
                                    </span>
                                    <span class="text-xs font-mono text-gray-400 dark:text-gray-500 shrink-0">· {result.days}d</span>
                                </div>
                            {/if}
                            <!-- svelte-ignore a11y_no_static_element_interactions -->
                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                            <div class="{isNarrow ? 'w-full' : 'ml-auto flex-1 min-w-[100px] max-w-[400px]'}" onclick={(e) => e.stopPropagation()}>
                                <SignalStyleEditor
                                    style={measure.style}
                                    onstylechange={(key, value) => updateMeasureStyle(measure.id, key, value)}
                                    simplified
                                />
                            </div>
                        </div>

                        <!-- 4. Icons: eye + trash (flex-col-reverse in narrow → trash on top, eye on bottom) -->
                        <div class="flex {isNarrow ? 'flex-col-reverse justify-between items-center' : 'items-center'} gap-1 shrink-0">
                            {#if isExpanded}
                                <!-- svelte-ignore a11y_no_static_element_interactions -->
                                <!-- svelte-ignore a11y_click_events_have_key_events -->
                                <div onclick={(e) => e.stopPropagation()}>
                                    <ColumnVisibilityToggle tableRef={measureTableRefs[measure.id]} />
                                </div>
                            {/if}
                            <span
                                class="p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 rounded transition-colors flex items-center justify-center"
                                role="button"
                                tabindex="-1"
                                title={$t('common.remove')}
                                onclick={(e) => { e.stopPropagation(); removeMeasure(measure.id); }}
                                onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); removeMeasure(measure.id); }}}
                            >
                                <Trash2 size={13} />
                            </span>
                        </div>
                    </div>

                    <!-- Expanded content -->
                    {#if isExpanded}

                        <!-- Summary table (DataTable) -->
                        {#if result}
                        <div class="border-t border-gray-200 dark:border-slate-600">
                            <DataTable
                                bind:this={measureTableRefs[measure.id]}
                                data={buildSummaryRows(result, measure)}
                                columns={summaryColumns}
                                getRowId={(r) => r.id}
                                storageKey="measure-summary-{measure.id}"
                                enableSelection={false}
                                enableActions={false}
                                enableSorting={true}
                                enableColumnFilters={true}
                                enableColumnVisibility={true}
                                enableColumnResize={true}
                                enablePagination={false}
                                tableLayout="auto"
                            />
                        </div>
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

