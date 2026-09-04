<!--
  BrimEvidenceTable.svelte — P1 Crédit Agricole pre-alarm net

  Renders one `BrimEvidence` block: a caption, a compact scrollable table of the
  raw source rows the plugin is talking about, and the human-readable comment
  explaining what does not add up.

  Why a compact table instead of `DataTable`: evidence blocks carry 1–40 rows and
  are shown inline inside notices and todos. A sticky-header scroll area gives the
  same "look at the actual rows" affordance without a per-instance `storageKey`,
  pagination chrome or column preferences persisted for a throwaway table.
-->
<script lang="ts">
    import {ChevronDown, ChevronRight, FileSearch, MessageSquareWarning} from 'lucide-svelte';
    import {untrack} from 'svelte';
    import {t} from 'svelte-i18n';
    import type {BrimEvidence} from '$lib/types';

    interface Props {
        evidence: BrimEvidence;
        /** Visual accent, matching the severity of the notice/todo that owns it. */
        tone?: 'info' | 'warning' | 'blocker';
        /**
         * Render the row table behind a click-to-open header. Evidence can be 36+ rows,
         * which pushes everything below it off-screen; when the notice text already says
         * what happened, the rows are supporting detail, not the message.
         */
        collapsible?: boolean;
        /** Start expanded when `collapsible` — otherwise the block opens closed. */
        defaultOpen?: boolean;
        /**
         * Open the source file at one of these rows. A single row taken out of its file is
         * often not enough to judge it — a charge only makes sense next to the operation it
         * was charged on — so the neighbours have to be reachable in one click.
         */
        onGotoRow?: (rowNumbers: number[]) => void;
    }

    let {evidence, tone = 'warning', collapsible = false, defaultOpen = false, onGotoRow}: Props = $props();

    let expanded = $state(untrack(() => defaultOpen));

    let headers = $derived(evidence.headers ?? []);
    let rows = $derived(evidence.rows ?? []);
    let rowNumbers = $derived(evidence.row_numbers ?? []);
    let hasRowNumbers = $derived(rowNumbers.length === rows.length && rows.length > 0);

    const toneRing: Record<string, string> = {
        info: 'border-sky-200 dark:border-sky-800',
        warning: 'border-amber-200 dark:border-amber-800',
        blocker: 'border-red-200 dark:border-red-800',
    };
    const toneHead: Record<string, string> = {
        info: 'bg-sky-50 dark:bg-sky-900/30 text-sky-900 dark:text-sky-200',
        warning: 'bg-amber-50 dark:bg-amber-900/30 text-amber-900 dark:text-amber-200',
        blocker: 'bg-red-50 dark:bg-red-900/30 text-red-900 dark:text-red-200',
    };
    /** Only offered when the rows are numbered: without a line number there is nowhere to go. */
    // Every row of the evidence is tinted in the preview, but the jump lands on the
    // first one: the point is to read the block in its file context, from its start.
    let gotoRows = $derived(onGotoRow && hasRowNumbers ? rowNumbers : []);
    let gotoRow = $derived(gotoRows.length > 0 ? gotoRows[0] : null);

    const toneComment: Record<string, string> = {
        info: 'text-sky-800 dark:text-sky-300',
        warning: 'text-amber-800 dark:text-amber-300',
        blocker: 'text-red-800 dark:text-red-300',
    };
</script>

<div class="rounded-lg border {toneRing[tone]} overflow-hidden" data-testid="brim-evidence">
    {#if collapsible && rows.length > 0}
        <!-- Toggle and "open the file" sit side by side rather than nested: they are two
             different destinations, and a button inside a button is not clickable. -->
        <div class="flex w-full items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold {toneHead[tone]}">
            <button type="button" class="flex min-w-0 flex-1 items-center gap-1.5 text-left" onclick={() => (expanded = !expanded)} data-testid="brim-evidence-toggle">
                {#if expanded}
                    <ChevronDown size={12} class="shrink-0 opacity-70" />
                {:else}
                    <ChevronRight size={12} class="shrink-0 opacity-70" />
                {/if}
                <span class="min-w-0 flex-1 truncate">{evidence.title || $t('importWizard.evidenceRowsTitle')}</span>
                <span class="shrink-0 font-normal opacity-70">{$t('importWizard.evidenceRowCount', {values: {n: rows.length}})}</span>
            </button>
            {#if gotoRow !== null}
                <button
                    type="button"
                    class="inline-flex shrink-0 items-center gap-1 rounded-md border border-current/30 px-1.5 py-0.5 font-medium opacity-80 transition-opacity hover:opacity-100"
                    onclick={() => onGotoRow?.(gotoRows)}
                    title={$t('importWizard.evidenceOpenFileHint')}
                    data-testid="brim-evidence-goto"
                >
                    <FileSearch size={11} />
                    {$t('importWizard.evidenceOpenFile', {values: {n: gotoRow}})}
                </button>
            {/if}
        </div>
    {:else if evidence.title || gotoRow !== null}
        <div class="flex items-center gap-2 px-2.5 py-1.5 text-[11px] font-semibold {toneHead[tone]}">
            <span class="min-w-0 flex-1 truncate" data-testid="brim-evidence-title">{evidence.title}</span>
            {#if gotoRow !== null}
                <button
                    type="button"
                    class="inline-flex shrink-0 items-center gap-1 rounded-md border border-current/30 px-1.5 py-0.5 font-medium opacity-80 transition-opacity hover:opacity-100"
                    onclick={() => onGotoRow?.(gotoRows)}
                    title={$t('importWizard.evidenceOpenFileHint')}
                    data-testid="brim-evidence-goto"
                >
                    <FileSearch size={11} />
                    {$t('importWizard.evidenceOpenFile', {values: {n: gotoRow}})}
                </button>
            {/if}
        </div>
    {/if}

    <!-- The comment sits above the rows: it is the message, the rows are the proof. -->
    {#if evidence.comment && (!collapsible || expanded)}
        <div class="flex items-start gap-1.5 border-b border-gray-100 bg-white px-2.5 py-1.5 dark:border-slate-700 dark:bg-slate-800">
            <MessageSquareWarning size={12} class="mt-0.5 shrink-0 {toneComment[tone]}" />
            <p class="text-[11px] leading-relaxed {toneComment[tone]}" data-testid="brim-evidence-comment">{evidence.comment}</p>
        </div>
    {/if}

    {#if rows.length > 0 && (!collapsible || expanded)}
        <div class="max-h-48 overflow-auto bg-white dark:bg-slate-800">
            <table class="w-full text-[11px] border-collapse">
                <thead class="sticky top-0 z-10">
                    <tr class="bg-gray-50 dark:bg-slate-700/80">
                        {#if hasRowNumbers}
                            <th class="px-2 py-1 text-right font-medium text-gray-400 dark:text-gray-500 border-b border-gray-200 dark:border-slate-600 whitespace-nowrap">#</th>
                        {/if}
                        {#each headers as header}
                            <th class="px-2 py-1 text-left font-medium text-gray-600 dark:text-gray-300 border-b border-gray-200 dark:border-slate-600 whitespace-nowrap">{header}</th>
                        {/each}
                    </tr>
                </thead>
                <tbody>
                    {#each rows as row, i}
                        <tr class="odd:bg-white even:bg-gray-50/60 dark:odd:bg-slate-800 dark:even:bg-slate-700/30">
                            {#if hasRowNumbers}
                                <td class="px-2 py-1 text-right font-mono text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-slate-700 whitespace-nowrap">{rowNumbers[i]}</td>
                            {/if}
                            {#each row as cell}
                                <td class="px-2 py-1 text-gray-700 dark:text-gray-200 border-b border-gray-100 dark:border-slate-700 align-top">{cell}</td>
                            {/each}
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>
