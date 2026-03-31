<!--
  BoundaryDateModal — Reusable modal for choosing a boundary date.

  Used by ScheduledInvestmentEditor for:
  - Delete period (middle): redistribute range between neighbors
  - Split period: choose where to split into two

  Uses SingleDatePicker with disabledDates to restrict selection to the valid range.

  Props:
  - open: boolean (bindable)
  - mode: 'delete' | 'split'
  - minDate / maxDate: ISO YYYY-MM-DD range constraints
  - defaultDate: initial boundary date
  - onconfirm: (boundaryDate: string) => void
  - oncancel: () => void
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Scissors, Trash2} from 'lucide-svelte';
    import SingleDatePicker from '$lib/components/ui/SingleDatePicker.svelte';

    interface Props {
        open: boolean;
        mode: 'delete' | 'split';
        minDate: string;
        maxDate: string;
        defaultDate: string;
        onconfirm: (boundaryDate: string) => void;
        oncancel: () => void;
    }

    let {open = $bindable(false), mode, minDate, maxDate, defaultDate, onconfirm, oncancel}: Props = $props();

    let boundaryDate = $state('');

    // Reset date when modal opens
    $effect(() => {
        if (open) boundaryDate = defaultDate;
    });

    /** Format a Date to ISO YYYY-MM-DD using local timezone (not UTC) */
    function toLocalISO(d: Date): string {
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    }

    /** Build a Set of disabled dates (everything outside minDate..maxDate range) */
    let disabledDates = $derived.by(() => {
        const disabled = new Set<string>();
        if (!minDate || !maxDate) return disabled;

        const min = new Date(minDate + 'T00:00:00');
        const max = new Date(maxDate + 'T00:00:00');

        // Generate dates from 60 days before min to 60 days after max
        // to cover the visible calendar range
        const rangeStart = new Date(min);
        rangeStart.setDate(rangeStart.getDate() - 60);
        const rangeEnd = new Date(max);
        rangeEnd.setDate(rangeEnd.getDate() + 60);

        const cursor = new Date(rangeStart);
        while (cursor <= rangeEnd) {
            const iso = toLocalISO(cursor);
            if (iso < minDate || iso > maxDate) {
                disabled.add(iso);
            }
            cursor.setDate(cursor.getDate() + 1);
        }
        return disabled;
    });

    function handleDateSelected(date: string) {
        boundaryDate = date;
    }

    function handleConfirm() {
        if (boundaryDate >= minDate && boundaryDate <= maxDate) {
            onconfirm(boundaryDate);
            open = false;
        }
    }

    function handleCancel() {
        oncancel();
        open = false;
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') handleCancel();
        if (e.key === 'Enter') handleConfirm();
    }
</script>

{#if open}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        onkeydown={handleKeydown}
        onclick={(e) => { if (e.target === e.currentTarget) handleCancel(); }}
    >
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-xl p-6 w-full max-w-sm mx-4 space-y-4">
            <!-- Header -->
            <div class="flex items-center gap-3">
                {#if mode === 'delete'}
                    <div class="p-2 rounded-lg bg-red-100 dark:bg-red-900/30">
                        <Trash2 size={18} class="text-red-500"/>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {$t('assets.schedule.deletePeriodTitle')}
                    </h3>
                {:else}
                    <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                        <Scissors size={18} class="text-blue-500"/>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {$t('assets.schedule.splitPeriodTitle')}
                    </h3>
                {/if}
            </div>

            <!-- Description -->
            <p class="text-sm text-gray-500 dark:text-gray-400">
                {#if mode === 'delete'}
                    {$t('assets.schedule.deleteBoundaryHint')}
                {:else}
                    {$t('assets.schedule.splitBoundaryHint')}
                {/if}
            </p>

            <!-- Date picker using SingleDatePicker -->
            <div class="space-y-2">
                <div class="text-xs font-medium text-gray-500 dark:text-gray-400">
                    {$t('assets.schedule.boundaryDate')}
                </div>
                <div class="flex justify-center">
                    <SingleDatePicker
                        value={boundaryDate}
                        label={$t('assets.schedule.boundaryDate')}
                        compact={true}
                        onchange={handleDateSelected}
                        {disabledDates}
                        allowFuture={true}
                    />
                </div>
                <p class="text-center text-[10px] text-gray-400">
                    {minDate} → {maxDate}
                </p>
            </div>

            <!-- Actions -->
            <div class="flex justify-end gap-2 pt-2">
                <button
                    type="button"
                    onclick={handleCancel}
                    class="px-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-slate-600
                           text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
                >
                    {$t('common.cancel')}
                </button>
                <button
                    type="button"
                    onclick={handleConfirm}
                    disabled={!boundaryDate || boundaryDate < minDate || boundaryDate > maxDate}
                    class="px-4 py-2 text-sm rounded-lg font-medium transition-colors disabled:opacity-50
                           {mode === 'delete'
                               ? 'bg-red-500 hover:bg-red-600 text-white'
                               : 'bg-libre-green hover:bg-libre-green-dark text-white'}"
                >
                    {mode === 'delete' ? $t('assets.schedule.confirmDelete') : $t('assets.schedule.confirmSplit')}
                </button>
            </div>
        </div>
    </div>
{/if}
