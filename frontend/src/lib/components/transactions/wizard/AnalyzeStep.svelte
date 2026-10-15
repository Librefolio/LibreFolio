<!--
  AnalyzeStep — the analysis step of the import wizard: each file parsed by its plugin, with the totals and the failures.

  Cut from ImportWizardModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Eye, CheckCircle, RefreshCw} from 'lucide-svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ParsedFileResult} from './wizardTypes';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';

    interface Props {
        candidatesRefreshing: boolean;
        duplicateRecheckRunning: boolean;
        parseResults: ParsedFileResult[];
        showAggregateDetail: boolean;
        usingCachedResults: boolean;
        parseAggregateStats: () => {totalTx: number; doneFileCount: number; uniqueAssets: number; unresolvedCount: number; totalWarnings: number; totalIssues: number; totalTodos: number; todoBlockers: number; likelyDuplicates: number};
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
        <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            {#if usingCachedResults}
                <span class="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
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
        <div class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div class="h-full rounded-full transition-all duration-300 ease-out" class:bg-libre-green={!parseHasErrors} class:bg-amber-500={parseHasErrors} style="width: {parseTotalCount > 0 ? (parseCompletedCount / parseTotalCount) * 100 : 0}%"></div>
        </div>
    </div>

    <!-- Parse failures: show WHY, not just "Error".
         Without this the only signal is a red badge, which is useless for
         diagnosing e.g. a stale client bundle rejecting a new response shape. -->
    {#if parseFailures.length > 0}
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-xs" data-testid="import-wizard-parse-errors">
            <div class="font-medium text-red-800 dark:text-red-200 mb-1.5">
                {$t('importWizard.parseErrorsTitle', {values: {n: parseFailures.length}})}
            </div>
            <ul class="space-y-1">
                {#each parseFailures as failure}
                    <li class="text-red-700 dark:text-red-300">
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
        <div class="grid grid-cols-2 md:grid-cols-8 gap-3 p-3 bg-gray-50 dark:bg-slate-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
            <div class="text-center">
                <div class="text-lg font-semibold text-gray-900 dark:text-white">{stats.totalTx}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.txCount', {values: {n: stats.totalTx, k: stats.doneFileCount}})}</div>
            </div>
            <div class="text-center">
                <div class="text-lg font-semibold text-gray-900 dark:text-white">
                    {stats.uniqueAssets}
                    {#if stats.unresolvedCount > 0}
                        <span class="text-amber-500 text-sm">({stats.unresolvedCount}?)</span>
                    {/if}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.assetsCount', {values: {n: stats.uniqueAssets, m: stats.unresolvedCount}})}</div>
            </div>
            <div class="text-center">
                <div class="text-lg font-semibold" class:text-amber-500={stats.totalIssues > 0} class:text-gray-900={stats.totalIssues === 0} class:dark:text-white={stats.totalIssues === 0}>{stats.totalIssues}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.validationIssueCount', {values: {n: stats.totalIssues}})}</div>
            </div>
            <div class="text-center">
                <div
                    class="text-lg font-semibold"
                    class:text-red-600={stats.todoBlockers > 0}
                    class:dark:text-red-400={stats.todoBlockers > 0}
                    class:text-amber-500={stats.todoBlockers === 0 && stats.totalTodos > 0}
                    class:text-gray-900={stats.totalTodos === 0}
                    class:dark:text-white={stats.totalTodos === 0}
                >
                    {stats.totalTodos}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.fieldTodoCount', {values: {n: stats.totalTodos}})}</div>
            </div>
            <div class="text-center">
                <div class="text-lg font-semibold" class:text-amber-500={stats.totalWarnings > 0} class:text-gray-900={stats.totalWarnings === 0} class:dark:text-white={stats.totalWarnings === 0}>{stats.totalWarnings}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.warningsCount', {values: {n: stats.totalWarnings}})}</div>
            </div>
            <div class="text-center">
                <div class="text-lg font-semibold" class:text-amber-500={stats.likelyDuplicates > 0} class:text-gray-900={stats.likelyDuplicates === 0} class:dark:text-white={stats.likelyDuplicates === 0}>{stats.likelyDuplicates}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.likelyDuplicates', {values: {n: stats.likelyDuplicates}})}</div>
            </div>
            <!-- View All action cell -->
            {#if parseDone || usingCachedResults}
                <button
                    type="button"
                    class="flex flex-col items-center justify-center gap-1 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/40 text-blue-600 dark:text-blue-400 transition-colors px-2 py-1.5"
                    data-testid="import-wizard-view-all"
                    onclick={() => {
                        showAggregateDetail = true;
                    }}
                >
                    <Eye size={16} />
                    <span class="text-xs font-medium">{$t('importWizard.viewAll')}</span>
                </button>
                <button
                    type="button"
                    class="flex flex-col items-center justify-center gap-1 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-slate-800 hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors px-2 py-1.5"
                    data-testid="import-wizard-reparse"
                    onclick={handleReparse}
                >
                    <RefreshCw size={16} />
                    <span class="text-xs font-medium">{$t('importWizard.reparse')}</span>
                </button>
            {/if}
        </div>
    {/if}
</div>
