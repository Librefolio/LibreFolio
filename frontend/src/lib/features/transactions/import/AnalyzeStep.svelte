<!--
  AnalyzeStep — the analysis step of the import wizard: each file parsed by its plugin, with the totals and the failures.

  Cut from ImportWizardModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Eye, CheckCircle, RefreshCw} from 'lucide-svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import NoticeCounts from '$lib/features/transactions/import/NoticeCounts.svelte';
    import type {ParsedFileResult} from './wizardTypes';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';

    interface Props {
        candidatesRefreshing: boolean;
        duplicateRecheckRunning: boolean;
        parseResults: ParsedFileResult[];
        showAggregateDetail: boolean;
        usingCachedResults: boolean;
        parseAggregateStats: () => {totalTx: number; doneFileCount: number; uniqueAssets: number; unresolvedCount: number; totalWarnings: number; totalNotes: number; totalIssues: number; totalTodos: number; todoBlockers: number; likelyDuplicates: number};
        parseCompletedCount: number;
        parseDone: boolean;
        parseFailures: ParsedFileResult[];
        parseHasErrors: boolean;
        parseHasSuccess: boolean;
        parseState: string;
        parseTotalCount: number;
        step3Columns: ColumnDef<ParsedFileResult>[];
        step3RowActions: RowAction<ParsedFileResult>[];
        handleReparse: () => void;
        openParseDetail: (result: ParsedFileResult) => void;
    }

    let {
        candidatesRefreshing,
        duplicateRecheckRunning,
        parseResults,
        showAggregateDetail = $bindable(),
        usingCachedResults,
        parseAggregateStats,
        parseCompletedCount,
        parseDone,
        parseFailures,
        parseHasErrors,
        parseHasSuccess,
        parseState,
        parseTotalCount,
        step3Columns,
        step3RowActions,
        handleReparse,
        openParseDetail,
    }: Props = $props();
</script>

<div class="flex flex-col gap-4 p-4" data-testid="import-wizard-step3" data-parse-state={parseState} data-busy={candidatesRefreshing || duplicateRecheckRunning} aria-busy={candidatesRefreshing || duplicateRecheckRunning}>
    <!-- Progress bar -->
    <div class="space-y-1">
        <div class="flex items-center justify-between text-xs text-lf-muted">
            {#if usingCachedResults}
                <span class="flex items-center gap-1 text-lf-success">
                    <CheckCircle size={14} />
                    {$t('importWizard.cachedResults')}
                </span>
            {:else if parseDone}
                <span>{$t('importWizard.parseComplete')}</span>
            {:else}
                <span>{$t('importWizard.parsingProgress', {values: {done: parseCompletedCount, total: parseTotalCount}})}</span>
            {/if}
            <span>{parseCompletedCount}/{parseTotalCount}</span>
        </div>
        <div class="w-full h-2 bg-lf-neutral rounded-full overflow-hidden">
            <div class="h-full rounded-full transition-all duration-300 ease-out" class:bg-lf-checked={!parseHasErrors} class:bg-lf-warning={parseHasErrors} style="width: {parseTotalCount > 0 ? (parseCompletedCount / parseTotalCount) * 100 : 0}%"></div>
        </div>
    </div>

    <!-- Parse failures: show WHY, not just "Error".
         Without this the only signal is a red badge, which is useless for
         diagnosing e.g. a stale client bundle rejecting a new response shape. -->
    {#if parseFailures.length > 0}
        <div class="bg-lf-danger-soft border border-lf-danger-line rounded-lg p-3 text-xs" data-testid="import-wizard-parse-errors">
            <div class="font-medium text-lf-danger-on-soft mb-1.5">
                {$t('importWizard.parseErrorsTitle', {values: {n: parseFailures.length}})}
            </div>
            <ul class="space-y-1">
                {#each parseFailures as failure}
                    <li class="text-lf-danger">
                        <span class="font-medium">{failure.fileName}</span>
                        <span class="opacity-80"> — {failure.errorMessage ?? $t('common.error')}</span>
                    </li>
                {/each}
            </ul>
        </div>
    {/if}

    <!-- Results DataTable -->
    <DataTable
        data={parseResults}
        columns={step3Columns}
        getRowId={(row) => row.fileId}
        storageKey="import-wizard-parse-results"
        enableSelection={false}
        enableActions={true}
        actionsColumnWidth="64px"
        rowActions={step3RowActions}
        onRowDoubleClick={(row) => {
            if (row.status === 'done') openParseDetail(row);
        }}
        enableSorting={true}
        enableColumnFilters={false}
        enablePagination={false}
        enableColumnVisibility={false}
        defaultPageSize={100}
        tableLayout="auto"
        stickyActions={false}
        enableContextMenu={true}
    />

    <!-- Aggregate summary -->
    {#if parseHasSuccess}
        {@const stats = parseAggregateStats()}
        <div class="grid grid-cols-2 md:grid-cols-8 gap-3 p-3 bg-lf-panel rounded-lg border border-lf-subtle">
            <div class="text-center">
                <div class="text-lg font-semibold text-lf-primary">{stats.totalTx}</div>
                <div class="text-xs text-lf-muted">{$t('importWizard.txCount', {values: {n: stats.totalTx, k: stats.doneFileCount}})}</div>
            </div>
            <div class="text-center">
                <div class="text-lg font-semibold text-lf-primary">
                    {stats.uniqueAssets}
                    {#if stats.unresolvedCount > 0}
                        <span class="text-lf-warning text-sm">({stats.unresolvedCount}?)</span>
                    {/if}
                </div>
                <div class="text-xs text-lf-muted">{$t('importWizard.assetsCount', {values: {n: stats.uniqueAssets, m: stats.unresolvedCount}})}</div>
            </div>
            <div class="text-center">
                <div class="text-lg font-semibold" class:text-lf-warning={stats.totalIssues > 0} class:text-lf-primary={stats.totalIssues === 0}>{stats.totalIssues}</div>
                <div class="text-xs text-lf-muted">{$t('importWizard.validationIssueCount', {values: {n: stats.totalIssues}})}</div>
            </div>
            <div class="text-center">
                <div class="text-lg font-semibold" class:text-lf-danger={stats.todoBlockers > 0} class:text-lf-warning={stats.todoBlockers === 0 && stats.totalTodos > 0} class:text-lf-primary={stats.totalTodos === 0}>{stats.totalTodos}</div>
                <div class="text-xs text-lf-muted">{$t('importWizard.fieldTodoCount', {values: {n: stats.totalTodos}})}</div>
            </div>
            <!-- B-51: the plugins' warnings (amber) and notes (blue) apart; the counts name themselves for screen readers. -->
            <div class="text-center" data-testid="import-wizard-stat-notices">
                <div class="text-lg font-semibold"><NoticeCounts warnings={stats.totalWarnings} notes={stats.totalNotes} size="lg" /></div>
                <div class="text-xs text-lf-muted" aria-hidden="true">{$t('importWizard.warningsCount', {values: {n: stats.totalWarnings}})} · {$t('importWizard.notesCount', {values: {n: stats.totalNotes}})}</div>
            </div>
            <div class="text-center">
                <div class="text-lg font-semibold" class:text-lf-warning={stats.likelyDuplicates > 0} class:text-lf-primary={stats.likelyDuplicates === 0}>{stats.likelyDuplicates}</div>
                <div class="text-xs text-lf-muted">{$t('importWizard.likelyDuplicates', {values: {n: stats.likelyDuplicates}})}</div>
            </div>
            <!-- View All action cell -->
            {#if parseDone || usingCachedResults}
                <button
                    type="button"
                    class="flex flex-col items-center justify-center gap-1 rounded-lg border border-lf-info-line bg-lf-info-soft hover:bg-lf-info-line text-lf-info transition-colors px-2 py-1.5"
                    data-testid="import-wizard-view-all"
                    onclick={() => {
                        showAggregateDetail = true;
                    }}
                >
                    <Eye size={16} />
                    <span class="text-xs font-medium">{$t('importWizard.viewAll')}</span>
                </button>
                <button type="button" class="flex flex-col items-center justify-center gap-1 rounded-lg border border-lf-subtle bg-lf-card hover:bg-lf-hover text-lf-muted transition-colors px-2 py-1.5" data-testid="import-wizard-reparse" onclick={handleReparse}>
                    <RefreshCw size={16} />
                    <span class="text-xs font-medium">{$t('importWizard.reparse')}</span>
                </button>
            {/if}
        </div>
    {/if}
</div>
