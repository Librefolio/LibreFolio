<!--
  CellDateRange — Date range picker embedded directly in DataTable cells.

  For normal periods: renders DateRangePicker inline (stacked 2-row trigger).
  Clicking opens the dual calendar directly — 1 click, not 2.
  Uses usePortal to escape table stacking context.

  For late interest row: shows "⚡ Late (+Nd grace → ∞)" with grace days popover.

  Props:
  - start / end: ISO YYYY-MM-DD
  - disabled: disable editing
  - isLateInterest: special display mode
  - graceDays: grace period for late interest
  - onchange: callback for date changes
  - onGraceDaysChange: callback for grace days changes
-->
<script lang="ts">
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';

    interface Props {
        start: string;
        end: string;
        disabled?: boolean;
        isLateInterest?: boolean;
        graceDays?: number;
        onchange?: (start: string, end: string) => void;
        onGraceDaysChange?: (days: number) => void;
    }

    let {start, end, disabled = false, isLateInterest = false, graceDays = 0, onchange, onGraceDaysChange}: Props = $props();

    let showGracePopover = $state(false);
    let anchorEl: HTMLElement | undefined = $state();
    let gracePopoverStyle = $state('');
    let localGraceDays = $state(0);
    let localY = $state(0);
    let localM = $state(0);
    let localD = $state(0);

    function daysToYMD(total: number) {
        const y = Math.floor(total / 365);
        const rem = total % 365;
        const m = Math.floor(rem / 30);
        const d = rem % 30;
        return {y, m, d};
    }

    function ymdToDays(y: number, m: number, d: number) {
        return y * 365 + m * 30 + d;
    }

    // Sync graceDays from parent
    $effect(() => {
        localGraceDays = graceDays;
        const ymd = daysToYMD(graceDays);
        localY = ymd.y;
        localM = ymd.m;
        localD = ymd.d;
    });

    // Note: No scroll listener needed — grace popover uses position:fixed.

    /** Svelte action: portal — moves the node to document.body */
    function portal(node: HTMLElement) {
        document.body.appendChild(node);
        return {
            destroy() {
                if (node.parentElement === document.body) node.remove();
            },
        };
    }

    function openGracePopover() {
        if (disabled || !anchorEl) return;
        const rect = anchorEl.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        const top = spaceBelow > 200 ? rect.bottom + 4 : rect.top - 200;
        const left = Math.min(rect.left, window.innerWidth - 260);
        gracePopoverStyle = `position:fixed;top:${Math.max(4, top)}px;left:${Math.max(4, left)}px;z-index:99999;`;
        showGracePopover = true;
    }

    function handleDateChange(newStart: string, newEnd: string) {
        onchange?.(newStart, newEnd);
    }

    function handleGraceDaysBlur() {
        const clamped = Math.max(0, Math.round(localGraceDays));
        localGraceDays = clamped;
        const ymd = daysToYMD(clamped);
        localY = ymd.y;
        localM = ymd.m;
        localD = ymd.d;
        onGraceDaysChange?.(clamped);
    }

    function handleYMDBlur() {
        const y = Math.max(0, Math.round(localY || 0));
        const m = Math.max(0, Math.round(localM || 0));
        const d = Math.max(0, Math.round(localD || 0));
        localY = y;
        localM = m;
        localD = d;
        const total = ymdToDays(y, m, d);
        localGraceDays = total;
        onGraceDaysChange?.(total);
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') showGracePopover = false;
    }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isLateInterest}
    <!-- Late interest: special compact display with grace popover -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        bind:this={anchorEl}
        class="inline-flex items-center gap-1 text-sm cursor-pointer select-none
               {disabled ? 'opacity-50 cursor-not-allowed' : 'hover:text-libre-green'}"
        onclick={() => !disabled && openGracePopover()}
    >
        <span class="text-amber-500">⚡</span>
        <span class="font-medium">Late</span>
        <span class="text-gray-400 text-xs">(+{graceDays}d grace → ∞)</span>
    </div>

    {#if showGracePopover}
        <div use:portal>
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
                class="fixed inset-0"
                style="z-index:99998;"
                onclick={() => {
                    showGracePopover = false;
                }}
            ></div>
            <div style={gracePopoverStyle}>
                <div
                    class="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600
                            rounded-xl shadow-xl p-3 space-y-3"
                    style="min-width:260px;"
                >
                    <div class="text-xs font-medium text-gray-500 dark:text-gray-400">⚡ Late Interest — Grace Period</div>
                    <!-- Y / M / D inputs -->
                    <div class="flex items-center gap-1.5">
                        <input
                            type="number"
                            bind:value={localY}
                            oninput={handleYMDBlur}
                            min="0"
                            class="w-14 px-1.5 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                   bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 text-center
                                   focus:outline-none focus:ring-2 focus:ring-libre-green/50"
                        />
                        <span class="text-xs text-gray-500">y</span>
                        <input
                            type="number"
                            bind:value={localM}
                            oninput={handleYMDBlur}
                            min="0"
                            class="w-14 px-1.5 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                   bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 text-center
                                   focus:outline-none focus:ring-2 focus:ring-libre-green/50"
                        />
                        <span class="text-xs text-gray-500">m</span>
                        <input
                            type="number"
                            bind:value={localD}
                            oninput={handleYMDBlur}
                            min="0"
                            class="w-14 px-1.5 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                   bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 text-center
                                   focus:outline-none focus:ring-2 focus:ring-libre-green/50"
                        />
                        <span class="text-xs text-gray-500">d</span>
                    </div>
                    <!-- Total days (also editable for convenience) -->
                    <div class="flex items-center gap-2">
                        <label for="grace-days" class="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap"> = Total: </label>
                        <input
                            id="grace-days"
                            type="number"
                            bind:value={localGraceDays}
                            oninput={handleGraceDaysBlur}
                            min="0"
                            class="w-20 px-2 py-1 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                   bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 text-center
                                   focus:outline-none focus:ring-2 focus:ring-libre-green/50"
                        />
                        <span class="text-xs text-gray-400">days</span>
                    </div>
                    <button
                        type="button"
                        onclick={() => {
                            showGracePopover = false;
                        }}
                        class="w-full px-3 py-1.5 text-xs rounded-lg bg-gray-100 dark:bg-slate-700
                               text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    {/if}
{:else}
    <!-- Normal period: DateRangePicker embedded directly — 1 click to open calendar -->
    <div class="cell-drp-inline" class:opacity-50={disabled} class:pointer-events-none={disabled}>
        <DateRangePicker {start} {end} showPresets={false} showCustomWindow={false} showDateFields={true} compact={true} stacked={true} usePortal={true} allowFuture={true} onchange={handleDateChange} />
    </div>
{/if}

<style>
    .cell-drp-inline {
        max-width: 100%;
    }
    .cell-drp-inline :global(.drp-trigger) {
        width: 100%;
    }
</style>
