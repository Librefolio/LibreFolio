<!--
  DateRangePicker — Unified date range picker with quick presets.

  Features:
  - "Flight-style" From/To date fields in a single unified component
  - Quick-select preset buttons: 1W, 1M, 3M, 6M, 1Y, 2Y, 5Y
  - Custom window: number + granularity (days/weeks/months/years) going backwards from today
  - All presets compute "from today backwards"
  - Emits change event with {start, end} dates

  Used by: FX list page, FX detail page, transaction filters, etc.
-->
<script lang="ts">
    import {Calendar, ChevronDown} from 'lucide-svelte';

    // =========================================================================
    // Types
    // =========================================================================

    export type QuickPreset = '1W' | '1M' | '3M' | '6M' | '1Y' | '2Y' | '5Y';
    export type Granularity = 'days' | 'weeks' | 'months' | 'years';

    interface Props {
        /** Start date (ISO YYYY-MM-DD) */
        start: string;
        /** End date (ISO YYYY-MM-DD) */
        end: string;
        /** Active preset (if any) */
        activePreset?: QuickPreset | 'custom' | null;
        /** Show quick presets */
        showPresets?: boolean;
        /** Show custom window input */
        showCustomWindow?: boolean;
        /** Show date input fields (From/To) — set false to show only presets */
        showDateFields?: boolean;
        /** Compact mode (smaller text, tighter spacing) */
        compact?: boolean;
        /** Called when dates change */
        onchange?: (start: string, end: string) => void;
    }

    let {
        start = $bindable(''),
        end = $bindable(''),
        activePreset = $bindable(null),
        showPresets = true,
        showCustomWindow = true,
        showDateFields = true,
        compact = false,
        onchange,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let customAmount = $state(3);
    let customGranularity: Granularity = $state('months');
    let showCustom = $state(false);

    // =========================================================================
    // Preset Definitions
    // =========================================================================

    const presets: {key: QuickPreset; label: string; months?: number; weeks?: number; years?: number}[] = [
        {key: '1W', label: '1W', weeks: 1},
        {key: '1M', label: '1M', months: 1},
        {key: '3M', label: '3M', months: 3},
        {key: '6M', label: '6M', months: 6},
        {key: '1Y', label: '1Y', years: 1},
        {key: '2Y', label: '2Y', years: 2},
        {key: '5Y', label: '5Y', years: 5},
    ];

    const granularityOptions: {value: Granularity; label: string}[] = [
        {value: 'days', label: 'Days'},
        {value: 'weeks', label: 'Weeks'},
        {value: 'months', label: 'Months'},
        {value: 'years', label: 'Years'},
    ];

    // =========================================================================
    // Helpers
    // =========================================================================

    function todayISO(): string {
        return new Date().toISOString().slice(0, 10);
    }

    function computeStartDate(preset: QuickPreset): string {
        const d = new Date();
        switch (preset) {
            case '1W': d.setDate(d.getDate() - 7); break;
            case '1M': d.setMonth(d.getMonth() - 1); break;
            case '3M': d.setMonth(d.getMonth() - 3); break;
            case '6M': d.setMonth(d.getMonth() - 6); break;
            case '1Y': d.setFullYear(d.getFullYear() - 1); break;
            case '2Y': d.setFullYear(d.getFullYear() - 2); break;
            case '5Y': d.setFullYear(d.getFullYear() - 5); break;
        }
        return d.toISOString().slice(0, 10);
    }

    function computeCustomStart(amount: number, granularity: Granularity): string {
        const d = new Date();
        switch (granularity) {
            case 'days': d.setDate(d.getDate() - amount); break;
            case 'weeks': d.setDate(d.getDate() - amount * 7); break;
            case 'months': d.setMonth(d.getMonth() - amount); break;
            case 'years': d.setFullYear(d.getFullYear() - amount); break;
        }
        return d.toISOString().slice(0, 10);
    }

    // =========================================================================
    // Handlers
    // =========================================================================

    function handlePresetClick(preset: QuickPreset) {
        activePreset = preset;
        showCustom = false;
        const newStart = computeStartDate(preset);
        const newEnd = todayISO();
        start = newStart;
        end = newEnd;
        onchange?.(newStart, newEnd);
    }

    function handleCustomApply() {
        if (customAmount <= 0) return;
        activePreset = 'custom';
        const newStart = computeCustomStart(customAmount, customGranularity);
        const newEnd = todayISO();
        start = newStart;
        end = newEnd;
        onchange?.(newStart, newEnd);
    }

    function handleManualChange() {
        activePreset = null;
        onchange?.(start, end);
    }

    function toggleCustom() {
        showCustom = !showCustom;
    }
</script>

<div class="flex flex-col gap-2">
    {#if showDateFields}
    <!-- Date Range Row (Flight-style) -->
    <div class="flex items-center gap-0 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-600 overflow-hidden {compact ? '' : 'shadow-sm'}">
        <!-- From -->
        <div class="flex-1 relative">
            <div class="absolute left-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 pointer-events-none">
                <Calendar size={compact ? 13 : 14} class="text-libre-green" />
                <span class="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">From</span>
            </div>
            <input
                type="date"
                bind:value={start}
                onchange={handleManualChange}
                class="w-full {compact ? 'pl-20 pr-2 py-2 text-xs' : 'pl-[5.5rem] pr-3 py-2.5 text-sm'} bg-transparent text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green focus:outline-none border-none font-mono"
            />
        </div>

        <!-- Divider -->
        <div class="w-px h-8 bg-gray-200 dark:bg-slate-600 flex-shrink-0"></div>

        <!-- To -->
        <div class="flex-1 relative">
            <div class="absolute left-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 pointer-events-none">
                <Calendar size={compact ? 13 : 14} class="text-libre-green" />
                <span class="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">To</span>
            </div>
            <input
                type="date"
                bind:value={end}
                onchange={handleManualChange}
                class="w-full {compact ? 'pl-16 pr-2 py-2 text-xs' : 'pl-[4.5rem] pr-3 py-2.5 text-sm'} bg-transparent text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green focus:outline-none border-none font-mono"
            />
        </div>
    </div>
    {/if}

    {#if showPresets}
        <!-- Quick Presets + Custom Toggle -->
        <div class="flex items-center gap-1 flex-wrap">
            {#each presets as preset}
                <button
                    class="px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150
                        {activePreset === preset.key
                            ? 'bg-libre-green text-white shadow-sm'
                            : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
                    onclick={() => handlePresetClick(preset.key)}
                >
                    {preset.label}
                </button>
            {/each}

            {#if showCustomWindow}
                <!-- Custom toggle -->
                <button
                    class="px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150 flex items-center gap-1
                        {showCustom || activePreset === 'custom'
                            ? 'bg-amber-500 text-white shadow-sm'
                            : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
                    onclick={toggleCustom}
                >
                    Custom
                    <ChevronDown size={12} class="transition-transform {showCustom ? 'rotate-180' : ''}" />
                </button>
            {/if}
        </div>
    {/if}

    {#if showCustom}
        <!-- Custom Window -->
        <div class="flex items-center gap-2 p-2 bg-gray-50 dark:bg-slate-800/50 rounded-lg border border-gray-200 dark:border-slate-600">
            <span class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">Last</span>
            <input
                type="number"
                bind:value={customAmount}
                min="1"
                max="999"
                class="w-16 px-2 py-1 text-xs text-center border border-gray-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green"
            />
            <select
                bind:value={customGranularity}
                class="px-2 py-1 text-xs border border-gray-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green"
            >
                {#each granularityOptions as opt}
                    <option value={opt.value}>{opt.label}</option>
                {/each}
            </select>
            <button
                class="px-3 py-1 text-xs font-medium bg-libre-green text-white rounded-md hover:bg-libre-green/90 transition-colors"
                onclick={handleCustomApply}
            >
                Apply
            </button>
        </div>
    {/if}
</div>

