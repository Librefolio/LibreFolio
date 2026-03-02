<!--
  MeasureOverlay — Click-drag trend measurement arrow for charts.

  Click on point A, drag to point B → shows a trend arrow following the time axis
  with an info box showing: start value, end value, Δ absolute, Δ%, interval days.

  The arrow always points forward in time: if the second click is before the first,
  the points are swapped so the arrow head is at the later date.

  Usage: overlays on top of the chart container via absolute positioning.
-->
<script lang="ts">
    import {X} from 'lucide-svelte';

    interface Props {
        /** Enable measure mode */
        enabled?: boolean;
        /** Chart data for value lookup */
        data?: Array<{date: string; value: number}>;
        /** Currency suffix for display */
        currency?: string;
        /** View mode for suffix */
        viewMode?: 'absolute' | 'percentage';
        /** Called when measure is dismissed */
        onDismiss?: () => void;
    }

    let {
        enabled = false,
        data = [],
        currency = '',
        viewMode = 'absolute',
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
            startPct: (lo / (data.length - 1)) * 100,
            endPct: (hi / (data.length - 1)) * 100,
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

        if (startIndex === null || endIndex !== null) {
            // First click or restart
            startIndex = clampedIdx;
            endIndex = null;
            hoveredIndex = null;
        } else {
            // Second click: finalize
            endIndex = clampedIdx;
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
        onDismiss?.();
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
        class="absolute inset-0 z-20 cursor-crosshair"
        onclick={handleClick}
        onmousemove={handleMouseMove}
    >
        <!-- Arrow line -->
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
                    x1="{measurement.startPct}%"
                    y1="50%"
                    x2="{measurement.endPct}%"
                    y2="50%"
                    stroke={measurement.isPositive ? '#16a34a' : '#ef4444'}
                    stroke-width="2"
                    stroke-dasharray={endIndex === null ? '4,4' : 'none'}
                    marker-end="url(#measure-arrow)"
                />
                <!-- Start dot -->
                <circle cx="{measurement.startPct}%" cy="50%" r="4"
                    fill={measurement.isPositive ? '#16a34a' : '#ef4444'} />
            </svg>

            <!-- Info box -->
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
                        <div class="flex justify-between">
                            <span class="text-gray-400">Start:</span>
                            <span class="font-mono">{measurement.startDate} · {formatValue(measurement.startValue)}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">End:</span>
                            <span class="font-mono">{measurement.endDate} · {formatValue(measurement.endValue)}</span>
                        </div>
                        <hr class="border-gray-200 dark:border-slate-600" />
                        <div class="flex justify-between">
                            <span class="text-gray-400">Δ Abs:</span>
                            <span class="font-mono font-semibold {measurement.isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                                {measurement.deltaAbs >= 0 ? '+' : ''}{formatValue(measurement.deltaAbs)}
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">Δ %:</span>
                            <span class="font-mono font-semibold {measurement.isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                                {measurement.deltaPct >= 0 ? '+' : ''}{measurement.deltaPct.toFixed(2)}%
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">Days:</span>
                            <span class="font-mono">{measurement.days}</span>
                        </div>
                    </div>
                </div>
            {/if}
        {/if}
    </div>
{/if}
