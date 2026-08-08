<script lang="ts">
    /**
     * TransactionCompareModal — presentational N-way comparison of transactions.
     *
     * Renders a field×transaction grid (rows = fields, columns = transactions) and
     * highlights the cells of a field that differ across columns, so the user can
     * eyeball what makes two "duplicate" rows actually different. Optionally exposes
     * a "keep which" selector (radio) wired back by the parent via `onKeep`.
     *
     * The component is intentionally dumb: the parent formats every cell (`display`)
     * and supplies a normalized comparison token (`cmp`) used only for diffing, so
     * markup differences (icons, currency spans) never count as a difference.
     */
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {t} from 'svelte-i18n';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';

    export interface CompareCell {
        /** Rendered content (may be HTML when `html` is true). */
        display: string;
        /** Normalized token used only to decide whether cells differ. */
        cmp: string;
        /** Render `display` as raw HTML (type icon, currency span…). */
        html?: boolean;
    }

    export interface CompareColumn {
        id: string;
        /** Provenance shown in the column header (file name or "DB #id"). */
        title: string;
        /** Optional secondary line (e.g. broker name). */
        subtitle?: string;
        /** Whether this column can be chosen as the one to keep. */
        selectable: boolean;
        cells: Record<string, CompareCell>;
    }

    export interface CompareField {
        key: string;
        label: string;
        align?: 'left' | 'right' | 'center';
    }

    interface Props {
        open: boolean;
        title: string;
        hint?: string;
        fields: CompareField[];
        columns: CompareColumn[];
        zIndex?: number;
        /** Column ids kept when the modal opens. */
        defaultKept?: string[];
        /** Column ids the "restore default" button goes back to. */
        resetKept?: string[];
        /** When provided AND ≥2 selectable columns, shows the keep toggles. */
        onKeep?: (keptIds: string[]) => void;
        onClose: () => void;
    }

    let {open, title, hint, fields, columns, zIndex = 60, defaultKept, resetKept, onKeep, onClose}: Props = $props();

    const selectableColumns = $derived(columns.filter((c) => c.selectable));
    const showKeep = $derived(typeof onKeep === 'function' && selectableColumns.length >= 2);

    // Mirrors the resolver table: one toggle per row, not a single-choice radio. The two
    // views arbitrate the same thing, so they must not disagree on how a choice is made.
    let kept = $state<Set<string>>(new Set());
    $effect(() => {
        if (open) kept = new Set(defaultKept ?? selectableColumns.map((c) => c.id));
    });

    function toggleKept(id: string) {
        const next = new Set(kept);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        kept = next;
    }

    /**
     * The cmp token shared by strictly more columns than any other, or `null` when no
     * value holds a majority. Two columns that disagree have no majority at all: calling
     * one of them the odd one out would be a coin toss dressed up as a finding.
     */
    function majorityCmp(fieldKey: string): string | null {
        const counts = new Map<string, number>();
        for (const col of columns) {
            const v = col.cells[fieldKey]?.cmp ?? '';
            counts.set(v, (counts.get(v) ?? 0) + 1);
        }
        let best: string | null = null;
        let bestN = 0;
        let tied = false;
        for (const [v, n] of counts) {
            if (n > bestN) {
                best = v;
                bestN = n;
                tied = false;
            } else if (n === bestN) {
                tied = true;
            }
        }
        return tied ? null : best;
    }

    function fieldDiffers(fieldKey: string): boolean {
        const seen = new Set(columns.map((c) => c.cells[fieldKey]?.cmp ?? ''));
        return seen.size > 1;
    }

    /** Without a majority every differing cell is highlighted — none of them is "the wrong one". */
    function cellIsOutlier(fieldKey: string, col: CompareColumn): boolean {
        if (!fieldDiffers(fieldKey)) return false;
        const majority = majorityCmp(fieldKey);
        return majority === null || (col.cells[fieldKey]?.cmp ?? '') !== majority;
    }

    /**
     * Splits a cell against the value it is being read next to, so the part that actually
     * differs can be marked. Two names that differ by one letter at the end
     * ("…FOICU" / "…FOICUM") are indistinguishable side by side in a narrow column, which
     * turns a real difference into an apparent bug in the comparison.
     */
    function diffParts(value: string, reference: string): {head: string; mid: string; tail: string} {
        if (value === '' || reference === '' || value === reference) return {head: value, mid: '', tail: ''};
        const max = Math.min(value.length, reference.length);
        let start = 0;
        while (start < max && value[start] === reference[start]) start += 1;
        let end = 0;
        while (end < max - start && value[value.length - 1 - end] === reference[reference.length - 1 - end]) end += 1;
        return {head: value.slice(0, start), mid: value.slice(start, value.length - end), tail: value.slice(value.length - end)};
    }

    /** What a cell is compared against: the majority reading, or the other column when there are two. */
    function referenceDisplay(fieldKey: string, index: number): string {
        const majority = majorityCmp(fieldKey);
        if (majority !== null) {
            const peer = columns.find((c) => (c.cells[fieldKey]?.cmp ?? '') === majority);
            if (peer) return peer.cells[fieldKey]?.display ?? '';
        }
        return columns[index === 0 ? 1 : 0]?.cells[fieldKey]?.display ?? '';
    }

    function colBadge(index: number): string {
        const circled = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨'];
        return circled[index] ?? `#${index + 1}`;
    }

    function apply() {
        onKeep?.([...kept]);
        onClose();
    }
</script>

<ModalBase {open} {zIndex} maxWidth="5xl" onRequestClose={onClose} testId="import-wizard-compare-modal" closeOnBackdropClick={true}>
    <div class="flex max-h-[85vh] flex-col">
        <div class="flex shrink-0 items-center justify-between border-b border-gray-100 p-5 pb-4 dark:border-slate-700">
            <h2 class="text-base font-semibold text-gray-800 dark:text-gray-100">{title}</h2>
            <button type="button" class="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-slate-700 dark:hover:text-gray-200" onclick={onClose} aria-label="Close" data-testid="import-wizard-compare-close"> ✕ </button>
        </div>

        <div class="min-h-0 flex-1 overflow-auto p-5">
            {#if hint}
                <p class="mb-3 text-xs text-gray-500 dark:text-gray-400">{hint}</p>
            {/if}

            <div class="overflow-x-auto">
                <!-- table-fixed + a pinned label column: leftover width goes to the data
                     columns (which is what the reader compares), never to the field names.
                     min-width keeps columns readable and scrolls instead of squeezing. -->
                <table class="w-full table-fixed border-collapse text-sm" style="min-width: {8 + columns.length * 10}rem" data-testid="import-wizard-compare-table">
                    <thead>
                        <tr>
                            <th class="sticky left-0 z-10 w-32 border-b border-gray-200 bg-white px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-400">
                                {$t('importWizard.compareModal.field')}
                            </th>
                            {#each columns as col, i (col.id)}
                                <th class="border-b border-l border-gray-200 px-2 py-2 text-left align-top dark:border-slate-700" data-testid="import-wizard-compare-col-{col.id}">
                                    <div class="flex items-center gap-1.5">
                                        {#if showKeep && col.selectable}
                                            <button
                                                type="button"
                                                onclick={() => toggleKept(col.id)}
                                                aria-label={$t('importWizard.compareModal.keep')}
                                                title={$t('importWizard.compareModal.keep')}
                                                class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors {kept.has(col.id) ? 'bg-emerald-500' : 'bg-gray-300 dark:bg-slate-600'}"
                                                data-testid="import-wizard-compare-keep-{col.id}"
                                            >
                                                <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform {kept.has(col.id) ? 'translate-x-5' : 'translate-x-1'}"></span>
                                            </button>
                                        {:else}
                                            <span class="shrink-0 text-xs text-gray-400">{colBadge(i)}</span>
                                        {/if}
                                        <span use:scrollOnOverflow class="{overflowScrollTextClass} text-xs font-semibold text-gray-700 dark:text-gray-200" title={col.title}>{col.title}</span>
                                    </div>
                                    {#if col.subtitle}
                                        <span use:scrollOnOverflow class="{overflowScrollTextClass} mt-0.5 text-[11px] font-normal text-gray-400 dark:text-gray-500" title={col.subtitle}>{col.subtitle}</span>
                                    {/if}
                                </th>
                            {/each}
                        </tr>
                    </thead>
                    <tbody>
                        {#each fields as field (field.key)}
                            {@const differs = fieldDiffers(field.key)}
                            <tr class={differs ? 'bg-amber-50/40 dark:bg-amber-900/10' : ''}>
                                <th class="sticky left-0 z-10 border-b border-gray-100 bg-white px-2 py-1.5 text-left align-top text-xs font-medium dark:border-slate-800 dark:bg-slate-900 {differs ? 'text-amber-700 dark:text-amber-300' : 'text-gray-500 dark:text-gray-400'}">
                                    <span class="inline-flex items-center gap-1">
                                        {#if differs}<span aria-hidden="true">≠</span>{/if}
                                        {field.label}
                                    </span>
                                </th>
                                {#each columns as col, colIndex (col.id)}
                                    {@const cell = col.cells[field.key]}
                                    {@const outlier = cellIsOutlier(field.key, col)}
                                    {@const parts = differs && cell && !cell.html ? diffParts(cell.display, referenceDisplay(field.key, colIndex)) : null}
                                    <td
                                        class="border-b border-l border-gray-100 px-2 py-1.5 align-top text-xs dark:border-slate-800 {outlier ? 'bg-amber-100 font-medium text-amber-900 dark:bg-amber-900/30 dark:text-amber-200' : 'text-gray-700 dark:text-gray-200'} {field.align === 'right'
                                            ? 'text-right'
                                            : field.align === 'center'
                                              ? 'text-center'
                                              : 'text-left'}"
                                    >
                                        {#if cell}
                                            {#if cell.html}
                                                <span use:scrollOnOverflow class={overflowScrollTextClass}>{@html cell.display}</span>
                                            {:else if parts && parts.mid !== ''}
                                                <span use:scrollOnOverflow class={overflowScrollTextClass} title={cell.display} data-testid="import-wizard-compare-diff"
                                                    >{parts.head}<mark class="rounded-sm bg-amber-300 px-0.5 text-amber-950 dark:bg-amber-500/70 dark:text-amber-50">{parts.mid}</mark>{parts.tail}</span
                                                >
                                            {:else}
                                                <span use:scrollOnOverflow class={overflowScrollTextClass} title={cell.display}>{cell.display}</span>
                                            {/if}
                                        {:else}
                                            <span class="text-gray-300">—</span>
                                        {/if}
                                    </td>
                                {/each}
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="flex shrink-0 items-center justify-between gap-3 border-t border-gray-100 p-4 dark:border-slate-700">
            {#if showKeep}
                <div class="flex flex-wrap items-center gap-2 text-xs">
                    <span class="font-medium text-gray-600 dark:text-gray-300">{$t('importWizard.compareModal.keptCount', {values: {n: kept.size, total: selectableColumns.length}})}</span>
                    <button
                        type="button"
                        class="rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-300 dark:hover:bg-slate-700"
                        onclick={() => (kept = new Set(selectableColumns.map((c) => c.id)))}
                        data-testid="import-wizard-compare-keep-all"
                    >
                        {$t('importWizard.compareModal.keepAll')}
                    </button>
                    {#if resetKept}
                        <button type="button" class="rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-300 dark:hover:bg-slate-700" onclick={() => (kept = new Set(resetKept))} data-testid="import-wizard-compare-reset">
                            {$t('importWizard.resolver.resetDefault')}
                        </button>
                    {/if}
                </div>
                <div class="flex items-center gap-2">
                    <button type="button" class="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-300 dark:hover:bg-slate-700" onclick={onClose}>
                        {$t('common.cancel')}
                    </button>
                    <button type="button" class="rounded-lg bg-libre-green px-3 py-1.5 text-sm text-white hover:bg-libre-green/90" onclick={apply} data-testid="import-wizard-compare-apply">
                        {$t('common.apply')}
                    </button>
                </div>
            {:else}
                <span></span>
                <button type="button" class="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-300 dark:hover:bg-slate-700" onclick={onClose}>
                    {$t('common.close')}
                </button>
            {/if}
        </div>
    </div>
</ModalBase>
