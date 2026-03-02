<!--
  MeasureOverlay — Click-to-measure trend arrow for charts.

  3-click cycle: 1st click = start point, 2nd click = complete measurement,
  3rd click = dismiss measurement and start waiting for new first click.

  The arrow follows the time axis (X). Y values are looked up from data.
  Arrow always points forward in time.

  Usage: overlays on top of the chart container via absolute positioning.
-->
<script lang="ts">
    import {X} from 'lucide-svelte';

    interface Props {
        /** Enable measure mode (always on when true — 3-click cycle) */
        enabled?: boolean;
        /** Chart data for value lookup */
        data?: Array<{date: string; value: number}>;
        /** Currency suffix for display */
        currency?: string;
        /** View mode for suffix */
        viewMode?: 'absolute' | 'percentage';
        /** ECharts grid bounds for mapping data→pixel coordinates */
        chartGridBounds?: {left: number; right: number; top: number; bottom: number; width: number; height: number} | null;
        /** Y-axis min/max for coordinate mapping */
        yRange?: {min: number; max: number} | null;
        /** Called when measure is dismissed */
        onDismiss?: () => void;
    }

    let {
        enabled = false,
        data = [],
        currency = '',
        viewMode = 'absolute',
        chartGridBounds = null,
        yRange = null,
        onDismiss,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let startIndex: number | null = $state(null);
    let endIndex: number | null = $state(null);
    let hoveredIndex: number | null = $state(null);
    let containerEl: HTMLDivElement | undefined = $state(undefined);

    // =========================================================================
    // Coordinate helpers
    // =========================================================================

    /** Map data index → X pixel percent within the container */
    function indexToXPercent(idx: number): number {
        if (data.length <= 1) return 50;
        return (idx / (data.length - 1)) * 100;
    }

    /** Map data value → Y pixel percent within the container (inverted: top=0%) */
    function valueToYPercent(value: number): number {
        if (!yRange || !chartGridBounds || !containerEl) return 50;
        const {min, max} = yRange;
        if (max === min) return 50;
        // Map value to grid pixel position
        const gridTop = chartGridBounds.top;
        const gridBottom = chartGridBounds.top + chartGridBounds.height;
        const yPixel = gridBottom - ((value - min) / (max - min)) * chartGridBounds.height;
        // Convert to percentage of full container height
        const containerHeight = containerEl.getBoundingClientRect().height;
        return (yPixel / containerHeight) * 100;
    }

    // =========================================================================
    // Derived
    // =========================================================================

    let measurement = $derived.by(() => {
        const si = startIndex;
        const ei = endIndex ?? hoveredIndex;
        if (si === null || ei === null || data.length === 0) return null;

        // Always order by time (arrow points forward)
        const lo = Math.min(si, ei);
        const hi = Math.max(si, ei);

        const startPoint = data[lo];
        const endPoint = data[hi];
        if (!startPoint || !endPoint) return null;

        const deltaAbs = endPoint.value - startPoint.value;
        const deltaPct = startPoint.value !== 0
            ? ((endPoint.value - startPoint.value) / startPoint.value) * 100
            : 0;

        const startDate = new Date(startPoint.date + 'T00:00:00');
        const endDate = new Date(endPoint.date + 'T00:00:00');
        const days = Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));

        return {
            startDate: startPoint.date,
            endDate: endPoint.date,
            startValue: startPoint.value,
            endValue: endPoint.value,
            deltaAbs,
            deltaPct,
            days,
            startXPct: indexToXPercent(lo),
            endXPct: indexToXPercent(hi),
            startYPct: valueToYPercent(startPoint.value),
            endYPct: valueToYPercent(endPoint.value),
            isPositive: deltaAbs >= 0,
        };
    });

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleClick(e: MouseEvent) {
        if (!enabled || !containerEl || data.length === 0) return;

        const rect = containerEl.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const pct = x / rect.width;
        const idx = Math.round(pct * (data.length - 1));
        const clampedIdx = Math.max(0, Math.min(data.length - 1, idx));

        if (startIndex === null) {
            // 1st click: set start point
            startIndex = clampedIdx;
            endIndex = null;
            hoveredIndex = null;
        } else if (endIndex === null) {
            // 2nd click: complete measurement
            endIndex = clampedIdx;
            hoveredIndex = null;
        } else {
            // 3rd click: dismiss and reset
            startIndex = null;
            endIndex = null;
            hoveredIndex = null;
        }
    }

    function handleMouseMove(e: MouseEvent) {
        if (!enabled || !containerEl || startIndex === null || endIndex !== null || data.length === 0) return;

        const rect = containerEl.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const pct = x / rect.width;
        const idx = Math.round(pct * (data.length - 1));
        hoveredIndex = Math.max(0, Math.min(data.length - 1, idx));
    }

    function handleDismiss() {
        startIndex = null;
        endIndex = null;
        hoveredIndex = null;
    }

    function formatValue(v: number): string {
        const suffix = viewMode === 'percentage' ? '%' : '';
        return `${v.toFixed(4)}${suffix}`;
    }
</script>

{#if enabled}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
        bind:this={containerEl}
        class="absolute inset-0 z-20 {endIndex !== null ? 'cursor-pointer' : startIndex !== null ? 'cursor-crosshair' : 'cursor-crosshair'}"
        onclick={handleClick}
        onmousemove={handleMouseMove}
    >
        <!-- Arrow line + dots at actual Y values -->
        {#if measurement}
            <svg class="absolute inset-0 w-full h-full pointer-events-none" style="overflow: visible;">
                <defs>
                    <marker id="measure-arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                        <polygon
                            points="0 0, 8 3, 0 6"
                            fill={measurement.isPositive ? '#16a34a' : '#ef4444'}
                        />
                    </marker>
                </defs>
                <line
                    x1="{measurement.startXPct}%"
                    y1="{measurement.startYPct}%"
                    x2="{measurement.endXPct}%"
                    y2="{measurement.endYPct}%"
                    stroke={measurement.isPositive ? '#16a34a' : '#ef4444'}
                    stroke-width="2"
                    stroke-dasharray={endIndex === null ? '4,4' : 'none'}
                    marker-end="url(#measure-arrow)"
                />
                <!-- Start dot -->
                <circle cx="{measurement.startXPct}%" cy="{measurement.startYPct}%" r="5"
                    fill={measurement.isPositive ? '#16a34a' : '#ef4444'}
                    stroke="white" stroke-width="1.5" />
                <!-- End dot -->
                <circle cx="{measurement.endXPct}%" cy="{measurement.endYPct}%" r="5"
                    fill={measurement.isPositive ? '#16a34a' : '#ef4444'}
                    stroke="white" stroke-width="1.5" />
            </svg>

            <!-- Info box (shown after 2nd click) -->
            {#if endIndex !== null}
                <div class="absolute top-2 right-2 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-gray-200 dark:border-slate-600 p-3 text-xs pointer-events-auto z-30 min-w-[180px]">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-semibold text-gray-700 dark:text-gray-200">Measurement</span>
                        <button
                            class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400"
                            onclick={handleDismiss}
                        >
                            <X size={12} />
                        </button>
                    </div>
                    <div class="space-y-1 text-gray-600 dark:text-gray-300">
                        <div class="flex justify-between gap-3">
                            <span class="text-gray-400">Start:</span>
                            <span class="font-mono">{measurement.startDate} · {formatValue(measurement.startValue)}</span>
                        </div>
                        <div class="flex justify-between gap-3">
                            <span class="text-gray-400">End:</span>
                            <span class="font-mono">{measurement.endDate} · {formatValue(measurement.endValue)}</span>
                        </div>
                        <hr class="border-gray-200 dark:border-slate-600" />
                        <div class="flex justify-between gap-3">
                            <span class="text-gray-400">Δ Abs:</span>
                            <span class="font-mono font-semibold {measurement.isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                                {measurement.deltaAbs >= 0 ? '+' : ''}{formatValue(measurement.deltaAbs)}
                            </span>
                        </div>
                        <div class="flex justify-between gap-3">
                            <span class="text-gray-400">Δ %:</span>
                            <span class="font-mono font-semibold {measurement.isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                                {measurement.deltaPct >= 0 ? '+' : ''}{measurement.deltaPct.toFixed(2)}%
                            </span>
                        </div>
                        <div class="flex justify-between gap-3">
                            <span class="text-gray-400">Days:</span>
                            <span class="font-mono">{measurement.days}</span>
                        </div>
                    </div>
                    <div class="mt-2 text-[10px] text-gray-400 dark:text-gray-500 text-center">
                        Click anywhere to dismiss
                    </div>
                </div>
            {/if}
        {/if}
    </div>
{/if}
