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
        /** Initial radio selection (column id or 'all'). */
        defaultKeep?: string;
        /** When provided AND ≥2 selectable columns, shows the keep selector. */
        onKeep?: (choice: string) => void;
        onClose: () => void;
    }

    let {open, title, hint, fields, columns, zIndex = 60, defaultKeep, onKeep, onClose}: Props = $props();

    const selectableColumns = $derived(columns.filter((c) => c.selectable));
    const showKeep = $derived(typeof onKeep === 'function' && selectableColumns.length >= 2);

    let keepChoice = $state<string>('all');
    $effect(() => {
        // Re-seed the radio whenever the modal (re)opens with a new default.
        if (open) keepChoice = defaultKeep ?? selectableColumns[0]?.id ?? 'all';
    });

    /** Most frequent cmp token for a field; ties resolve to the first column. */
    function majorityCmp(fieldKey: string): string | null {
        const counts = new Map<string, number>();
        for (const col of columns) {
            const v = col.cells[fieldKey]?.cmp ?? '';
            counts.set(v, (counts.get(v) ?? 0) + 1);
        }
        let best: string | null = null;
        let bestN = -1;
        for (const [v, n] of counts) {
            if (n > bestN) {
                best = v;
                bestN = n;
            }
        }
        return best;
    }

    function fieldDiffers(fieldKey: string): boolean {
        const seen = new Set(columns.map((c) => c.cells[fieldKey]?.cmp ?? ''));
        return seen.size > 1;
    }

    function cellIsOutlier(fieldKey: string, col: CompareColumn): boolean {
        if (!fieldDiffers(fieldKey)) return false;
        return (col.cells[fieldKey]?.cmp ?? '') !== majorityCmp(fieldKey);
    }

    function colBadge(index: number): string {
        const circled = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨'];
        return circled[index] ?? `#${index + 1}`;
    }

    function apply() {
        onKeep?.(keepChoice);
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
                <table class="w-full border-collapse text-sm" data-testid="import-wizard-compare-table">
                    <thead>
                        <tr>
                            <th class="sticky left-0 z-10 min-w-[7rem] border-b border-gray-200 bg-white px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-400">
                                {$t('importWizard.compareModal.field')}
                            </th>
                            {#each columns as col, i (col.id)}
                                <th class="min-w-[9rem] max-w-[14rem] border-b border-l border-gray-200 px-2 py-2 text-left align-top dark:border-slate-700" data-testid="import-wizard-compare-col-{col.id}">
                                    <div class="flex items-center gap-1">
                                        <span class="shrink-0 text-xs text-gray-400">{colBadge(i)}</span>
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
                                {#each columns as col (col.id)}
                                    {@const cell = col.cells[field.key]}
                                    {@const outlier = cellIsOutlier(field.key, col)}
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
                <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                    <span class="font-medium text-gray-600 dark:text-gray-300">{$t('importWizard.compareModal.keep')}:</span>
                    {#each columns as col, i (col.id)}
                        {#if col.selectable}
                            <label class="inline-flex cursor-pointer items-center gap-1 text-gray-700 dark:text-gray-200">
                                <input type="radio" name="compare-keep" value={col.id} bind:group={keepChoice} class="text-libre-green focus:ring-libre-green" data-testid="import-wizard-compare-keep-{col.id}" />
                                <span>{colBadge(i)}</span>
                            </label>
                        {/if}
                    {/each}
                    <label class="inline-flex cursor-pointer items-center gap-1 text-gray-700 dark:text-gray-200">
                        <input type="radio" name="compare-keep" value="all" bind:group={keepChoice} class="text-libre-green focus:ring-libre-green" data-testid="import-wizard-compare-keep-all" />
                        <span>{$t('importWizard.compareModal.keepAll')}</span>
                    </label>
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
