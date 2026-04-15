<!--
  BoundaryDateModal — Reusable modal for choosing boundary date(s).

  Used by ScheduledInvestmentEditor for:
  - Delete period (middle): redistribute range between neighbors
  - Split period: choose where to split into two
  - Bulk delete (multi-gap): choose N boundary dates, one per gap

  Supports single-gap mode (minDate/maxDate) and multi-gap mode (gaps array).

  Props:
  - open: boolean (bindable)
  - mode: 'delete' | 'split'
  - minDate / maxDate / defaultDate: for single-gap mode
  - gaps: array of {minDate, maxDate, defaultDate, label} for multi-gap mode
  - onconfirm: (boundaryDate: string) => void — single-gap
  - onconfirmMulti: (boundaryDates: string[]) => void — multi-gap
  - oncancel: () => void
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Scissors, Trash2} from 'lucide-svelte';
    import SingleDatePicker from '$lib/components/ui/SingleDatePicker.svelte';

    interface GapInfo {
        minDate: string;
        maxDate: string;
        defaultDate: string;
        label?: string;
    }

    interface Props {
        open: boolean;
        mode: 'delete' | 'split';
        /** Single-gap mode */
        minDate?: string;
        maxDate?: string;
        defaultDate?: string;
        /** Multi-gap mode */
        gaps?: GapInfo[];
        onconfirm?: (boundaryDate: string) => void;
        onconfirmMulti?: (boundaryDates: string[]) => void;
        oncancel: () => void;
    }

    let {
        open = $bindable(false),
        mode,
        minDate = '',
        maxDate = '',
        defaultDate = '',
        gaps = [],
        onconfirm,
        onconfirmMulti,
        oncancel,
    }: Props = $props();

    // Single-gap state
    let boundaryDate = $state('');

    // Multi-gap state
    let boundaryDates = $state<string[]>([]);

    let isMultiGap = $derived(gaps.length > 0);

    // Reset dates when modal opens
    $effect(() => {
        if (open) {
            if (gaps.length > 0) {
                boundaryDates = gaps.map(g => g.defaultDate);
            } else {
                boundaryDate = defaultDate;
            }
        }
    });

    /** Format a Date to ISO YYYY-MM-DD using local timezone (not UTC) */
    function toLocalISO(d: Date): string {
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    }

    /** Build a Set of disabled dates (everything outside min..max range) */
    function buildDisabledDates(min: string, max: string): Set<string> {
        const disabled = new Set<string>();
        if (!min || !max) return disabled;

        const minD = new Date(min + 'T00:00:00');
        const maxD = new Date(max + 'T00:00:00');

        const rangeStart = new Date(minD);
        rangeStart.setDate(rangeStart.getDate() - 60);
        const rangeEnd = new Date(maxD);
        rangeEnd.setDate(rangeEnd.getDate() + 60);

        const cursor = new Date(rangeStart);
        while (cursor <= rangeEnd) {
            const iso = toLocalISO(cursor);
            if (iso < min || iso > max) {
                disabled.add(iso);
            }
            cursor.setDate(cursor.getDate() + 1);
        }
        return disabled;
    }

    /** Single-gap disabled dates */
    let disabledDates = $derived.by(() => buildDisabledDates(minDate, maxDate));

    /** Multi-gap disabled dates (one set per gap) */
    let multiDisabledDates = $derived.by(() => gaps.map(g => buildDisabledDates(g.minDate, g.maxDate)));

    function handleDateSelected(date: string) {
        boundaryDate = date;
    }

    function handleMultiDateSelected(index: number, date: string) {
        boundaryDates = boundaryDates.map((d, i) => i === index ? date : d);
    }

    let isValid = $derived.by(() => {
        if (isMultiGap) {
            return boundaryDates.every((d, i) => {
                const g = gaps[i];
                return d && d >= g.minDate && d <= g.maxDate;
            });
        }
        return boundaryDate >= minDate && boundaryDate <= maxDate;
    });

    function handleConfirm() {
        if (!isValid) return;
        if (isMultiGap) {
            onconfirmMulti?.(boundaryDates);
        } else {
            onconfirm?.(boundaryDate);
        }
        open = false;
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
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-xl p-6 w-full max-w-sm mx-4 space-y-4
                     {isMultiGap ? 'max-w-md' : 'max-w-sm'} max-h-[90vh] overflow-y-auto">
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

            {#if isMultiGap}
                <!-- Multi-gap mode: N boundary date pickers -->
                <div class="space-y-4">
                    {#each gaps as gap, i}
                        <div class="space-y-2 p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-100 dark:border-slate-600">
                            <div class="text-xs font-medium text-gray-500 dark:text-gray-400">
                                {gap.label || `${$t('assets.schedule.boundaryDate')} ${i + 1}`}
                            </div>
                            <div class="flex justify-center">
                                <SingleDatePicker
                                    value={boundaryDates[i] ?? gap.defaultDate}
                                    label={gap.label || $t('assets.schedule.boundaryDate')}
                                    compact={true}
                                    onchange={(d) => handleMultiDateSelected(i, d)}
                                    disabledDates={multiDisabledDates[i]}
                                    allowFuture={true}
                                />
                            </div>
                            <p class="text-center text-[10px] text-gray-400">
                                {gap.minDate} → {gap.maxDate}
                            </p>
                        </div>
                    {/each}
                </div>
            {:else}
                <!-- Single-gap mode: one DatePicker -->
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
            {/if}

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
                    disabled={!isValid}
                    class="px-4 py-2 text-sm rounded-lg font-medium transition-colors disabled:opacity-50
                           {mode === 'delete'
                               ? 'bg-red-500 hover:bg-red-600 text-white'
                               : 'bg-libre-green hover:bg-libre-green-dark text-white'}"
                >
                    {mode === 'delete' ? $t('common.confirmDelete') : $t('assets.schedule.confirmSplit')}
                </button>
            </div>
        </div>
    </div>
{/if}
