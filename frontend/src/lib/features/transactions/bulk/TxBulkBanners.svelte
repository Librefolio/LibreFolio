<!--
  TxBulkBanners — the banners of the bulk workspace: commit failure, validation issues, todos, merge suggestions.

  Cut from TransactionBulkModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Link2, ChevronDown, ChevronRight} from 'lucide-svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import BrimEvidenceTable from '$lib/features/transactions/import/BrimEvidenceTable.svelte';
    import {resolveBrimTodoMessage} from '$lib/features/transactions/resolveBrimNotice';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import TransactionResultBanner from './TransactionResultBanner.svelte';
    import {getTransactionTypeIconUrl, getTypeRule} from '$lib/features/transactions/transactionTypeStore';
    import {resolveIssueMessage, type ResolverContext} from '$lib/features/transactions/resolveValidationMessage';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';
    import {formatCurrencyCodeHtml} from '$lib/utils/currency/currencyFormat';
    import {computeFxConversionInfo, buildFxTooltipData, buildFxTooltipHtml} from '$lib/utils/currency/fxConversionHelper';
    import {promotePairOrder} from './promoteHelpers';
    import {formatFixed} from '$lib/utils/core/formatFixed';
    import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';
    import type {ValidationIssue} from '../types';
    import type {PendingOp, SuggestEntry} from './txBulkTypes';
    import type DataTable from '$lib/components/table/DataTable.svelte';
    import type {ImportTodo} from '$lib/features/transactions/txPayloadHelpers';
    import type {BulkIssueRow} from '$lib/features/transactions/bulk/bulkDisplay';

    interface Props {
        commitFailed: boolean;
        formError: string | null;
        fxMarketCache: Map<string, FxDataPoint | null>;
        issues: ValidationIssue[];
        issuesDismissed: boolean;
        lastDraftKey: string;
        lastIssueDraftKey: string;
        ops: PendingOp[];
        promoteAllOpen: boolean;
        promoteBannerSeen: boolean;
        syncFxLoading: boolean;
        tableRef: DataTable<PendingOp> | undefined;
        todoBlockersExpanded: boolean;
        todoWarningsExpanded: boolean;
        allSuggestions: SuggestEntry[];
        balanceIssues: ValidationIssue[];
        bannerSuggestions: SuggestEntry[];
        fieldIssues: ValidationIssue[];
        hasPairedDelete: boolean;
        hasWacFxIssues: boolean;
        mergeAllPairs: SuggestEntry[];
        resolverCtx: ResolverContext;
        showIssuesBanner: boolean;
        todoBlockerEntries: Array<{rowId: string; rowNumber: string; date: string; todo: ImportTodo}>;
        todoWarningEntries: Array<{rowId: string; rowNumber: string; todo: ImportTodo}>;
        todoWarningRowCount: number;
        visibleOps: PendingOp[];
        AUTO_VALIDATE_THRESHOLD: number;
        bulkDisplayText: (key: string, fallback: string, values?: Record<string, string | number>) => string;
        getIssueRows: (issue: ValidationIssue) => BulkIssueRow[];
        getVisualRowLabel: (issue: ValidationIssue) => string;
        handleSyncFx: () => Promise<void>;
        issueRowsLabel: (issue: ValidationIssue) => string;
        jumpToIssue: (issue: ValidationIssue) => void;
        jumpToTodoRow: (rowId: string) => void;
        triggerPromoteFromSuggestion: (sug: SuggestEntry) => void;
    }

    let {
        commitFailed = $bindable(),
        formError = $bindable(),
        fxMarketCache,
        issues,
        issuesDismissed = $bindable(),
        lastDraftKey,
        lastIssueDraftKey,
        ops,
        promoteAllOpen = $bindable(),
        promoteBannerSeen = $bindable(),
        syncFxLoading,
        tableRef,
        todoBlockersExpanded = $bindable(),
        todoWarningsExpanded = $bindable(),
        allSuggestions,
        balanceIssues,
        bannerSuggestions,
        fieldIssues,
        hasPairedDelete,
        hasWacFxIssues,
        mergeAllPairs,
        resolverCtx,
        showIssuesBanner,
        todoBlockerEntries,
        todoWarningEntries,
        todoWarningRowCount,
        visibleOps,
        AUTO_VALIDATE_THRESHOLD,
        bulkDisplayText,
        getIssueRows,
        getVisualRowLabel,
        handleSyncFx,
        issueRowsLabel,
        jumpToIssue,
        jumpToTodoRow,
        triggerPromoteFromSuggestion,
    }: Props = $props();
</script>

<div class="px-5 pt-3 space-y-2 shrink-0">
    {#if formError}
        <TransactionResultBanner variant="error" title={`⛔ ${$t('common.saveCancelled')}`} subtitle={formError} dismissible ondismiss={() => (formError = null)} testId="tx-bulk-error" />
    {:else if commitFailed && issues.length > 0}
        <TransactionResultBanner variant="error" title={`⛔ ${$t('common.saveCancelled')}`} dismissible ondismiss={() => (commitFailed = false)} testId="tx-bulk-error">
            {#snippet titleAction()}
                {#if hasWacFxIssues}
                    <button type="button" class="text-xs px-2 py-0.5 rounded bg-lf-danger-line/50 hover:bg-lf-danger-line font-medium whitespace-nowrap" onclick={handleSyncFx} disabled={syncFxLoading} data-testid="tx-bulk-sync-fx-error">
                        {syncFxLoading ? '⏳' : '🔄'} Sync FX
                    </button>
                {/if}
            {/snippet}
            {#if fieldIssues.length > 0}
                <p class="font-semibold text-sm mt-1 mb-1">{$t('transactions.validate.issuesHeader')}</p>
                <ul class="list-disc pl-4 space-y-0.5 text-sm text-left" data-testid="tx-bulk-issues">
                    {#each fieldIssues as issue}
                        <li>
                            <button type="button" class="underline hover:opacity-80 text-left" onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-issue" data-code={issue.code} data-row-label={getVisualRowLabel(issue)}>
                                {#if issue.index < 0}{getVisualRowLabel(issue)}:
                                {:else}{$t('common.rowN', {values: {n: getVisualRowLabel(issue)}})}:
                                {/if}{@html sanitizeHtml(resolveIssueMessage(issue, $t, resolverCtx))}
                            </button>
                        </li>
                    {/each}
                </ul>
            {/if}
            {#if balanceIssues.length > 0}
                <p class="font-semibold text-sm mt-2 mb-1">{$t('transactions.validate.balanceIssuesHeader')}</p>
                <ul class="list-disc pl-4 space-y-0.5 text-sm text-left" data-testid="tx-bulk-balance-issues">
                    {#each balanceIssues as issue}
                        <li data-testid="tx-bulk-balance-issue">
                            {@html sanitizeHtml(resolveIssueMessage(issue, $t, resolverCtx))}
                            {#if getIssueRows(issue).length > 0}
                                <button type="button" class="block underline hover:opacity-80 text-left disabled:opacity-50" disabled={lastIssueDraftKey !== lastDraftKey} onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-balance-rows">
                                    {issueRowsLabel(issue)}
                                </button>
                            {:else}
                                <span class="block text-xs">{bulkDisplayText('transactions.bulk.balanceGroupOutsideWorkspace', "No contributing rows from this workspace match this group. Check the broker's history.")}</span>
                            {/if}
                        </li>
                    {/each}
                </ul>
            {/if}
        </TransactionResultBanner>
    {/if}
    {#if showIssuesBanner && !formError && !commitFailed}
        <TransactionResultBanner variant="warning" title={`⚠️ ${$t('transactions.validate.issuesHeader')}`} dismissible ondismiss={() => (issuesDismissed = true)} testId="tx-bulk-issues-header">
            {#snippet titleAction()}
                {#if hasWacFxIssues}
                    <button type="button" class="text-xs px-2 py-0.5 rounded bg-lf-warning-line/50 hover:bg-lf-warning-line font-medium whitespace-nowrap" onclick={handleSyncFx} disabled={syncFxLoading} data-testid="tx-bulk-sync-fx">
                        {syncFxLoading ? '⏳' : '🔄'} Sync FX
                    </button>
                {/if}
            {/snippet}
            {#if fieldIssues.length > 0}
                <ul class="list-disc pl-4 space-y-0.5 text-sm text-left" data-testid="tx-bulk-issues">
                    {#each fieldIssues as issue}
                        <li>
                            <button type="button" class="underline hover:opacity-80 text-left" onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-issue" data-code={issue.code} data-row-label={getVisualRowLabel(issue)}>
                                {#if issue.index < 0}{getVisualRowLabel(issue)}:
                                {:else}{$t('common.rowN', {values: {n: getVisualRowLabel(issue)}})}:
                                {/if}{@html sanitizeHtml(resolveIssueMessage(issue, $t, resolverCtx))}
                            </button>
                        </li>
                    {/each}
                </ul>
            {/if}
            {#if balanceIssues.length > 0}
                <p class="font-semibold text-sm {fieldIssues.length > 0 ? 'mt-2' : ''} mb-1">{$t('transactions.validate.balanceIssuesHeader')}</p>
                <ul class="list-disc pl-4 space-y-0.5 text-sm text-left" data-testid="tx-bulk-balance-issues">
                    {#each balanceIssues as issue}
                        <li data-testid="tx-bulk-balance-issue">
                            {@html sanitizeHtml(resolveIssueMessage(issue, $t, resolverCtx))}
                            {#if getIssueRows(issue).length > 0}
                                <button type="button" class="block underline hover:opacity-80 text-left disabled:opacity-50" disabled={lastIssueDraftKey !== lastDraftKey} onclick={() => jumpToIssue(issue)} data-testid="tx-bulk-balance-rows">
                                    {issueRowsLabel(issue)}
                                </button>
                            {:else}
                                <span class="block text-xs">{bulkDisplayText('transactions.bulk.balanceGroupOutsideWorkspace', "No contributing rows from this workspace match this group. Check the broker's history.")}</span>
                            {/if}
                        </li>
                    {/each}
                </ul>
            {/if}
        </TransactionResultBanner>
    {/if}
    {#if visibleOps.length > AUTO_VALIDATE_THRESHOLD}
        <InfoBanner variant="info">
            <p data-testid="tx-bulk-auto-off">ⓘ {$t('transactions.validate.autoOff', {values: {n: visibleOps.length, threshold: AUTO_VALIDATE_THRESHOLD}})}</p>
        </InfoBanner>
    {/if}
    {#if hasPairedDelete}
        <InfoBanner variant="info">
            <p data-testid="tx-bulk-split-hint">ℹ️ {$t('transactions.bulk.splitHint')}</p>
        </InfoBanner>
    {/if}
    {#if todoBlockerEntries.length > 0}
        <div class="bg-lf-danger-soft border border-lf-danger-line rounded-lg text-xs" data-testid="tx-bulk-todo-blockers">
            <button type="button" class="flex w-full items-center gap-1.5 p-3 text-left font-medium text-lf-danger-on-soft" onclick={() => (todoBlockersExpanded = !todoBlockersExpanded)} data-testid="tx-bulk-todo-blockers-toggle">
                {#if todoBlockersExpanded}
                    <ChevronDown size={14} class="shrink-0" />
                {:else}
                    <ChevronRight size={14} class="shrink-0" />
                {/if}
                <span class="min-w-0 flex-1">🔴 {$t('importWizard.todoBlockerVerifyHint', {values: {n: todoBlockerEntries.length}})}</span>
            </button>
            {#if todoBlockersExpanded}
                <ul class="max-h-72 space-y-2 overflow-y-auto px-3 pb-3">
                    {#each todoBlockerEntries as entry}
                        <li class="space-y-1.5">
                            <button type="button" class="block w-full text-left text-lf-danger-on-soft leading-relaxed hover:underline" onclick={() => jumpToTodoRow(entry.rowId)} title={$t('importWizard.todoGoto')} data-testid="tx-bulk-todo-goto" data-row-id={entry.rowId}>
                                <span class="font-mono opacity-70">#{entry.rowNumber}</span>
                                {resolveBrimTodoMessage(entry.todo, $t)}
                            </button>
                            {#each entry.todo.evidence ?? [] as evidence}
                                <BrimEvidenceTable {evidence} tone="blocker" collapsible />
                            {/each}
                        </li>
                    {/each}
                </ul>
            {/if}
        </div>
    {/if}
    {#if todoWarningRowCount > 0}
        <InfoBanner variant="warning">
            <div data-testid="tx-bulk-todo-warnings">
                <button type="button" class="flex w-full items-center gap-1.5 text-left" onclick={() => (todoWarningsExpanded = !todoWarningsExpanded)} data-testid="tx-bulk-todo-warnings-toggle">
                    {#if todoWarningsExpanded}
                        <ChevronDown size={14} class="shrink-0" />
                    {:else}
                        <ChevronRight size={14} class="shrink-0" />
                    {/if}
                    <span class="min-w-0 flex-1">🔧 {$t('importWizard.todoWarningVerifyHint', {values: {n: todoWarningRowCount}})}</span>
                </button>
                {#if todoWarningsExpanded}
                    <ul class="mt-1.5 max-h-48 space-y-1 overflow-y-auto">
                        {#each todoWarningEntries as entry}
                            <li>
                                <button type="button" class="block w-full text-left leading-relaxed hover:underline" onclick={() => jumpToTodoRow(entry.rowId)} title={$t('importWizard.todoGoto')} data-testid="tx-bulk-todo-goto" data-row-id={entry.rowId}>
                                    <span class="font-mono opacity-70">#{entry.rowNumber}</span>
                                    {resolveBrimTodoMessage(entry.todo, $t) || entry.todo.field}
                                </button>
                            </li>
                        {/each}
                    </ul>
                {/if}
            </div>
        </InfoBanner>
    {/if}
    {#if bannerSuggestions.length > 0}
        <div class="bg-lf-success-soft border border-lf-success-line rounded-lg p-3 text-xs" data-testid="promote-suggest-banner" onclickcapture={() => (promoteBannerSeen = true)}>
            <div class="flex items-center gap-2 mb-1.5">
                <span class="font-medium text-lf-success-on-soft">{$t('transactions.promoteSuggest.detected')}</span>
                {#if mergeAllPairs.length > 1}
                    <button type="button" class="ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded bg-lf-action text-lf-on-action hover:bg-lf-action-hover font-medium" onclick={() => (promoteAllOpen = true)} data-testid="promote-suggest-merge-all">
                        <Link2 size={12} />
                        {$t('transactions.promoteSuggest.mergeAll', {values: {n: mergeAllPairs.length}})}
                    </button>
                {/if}
            </div>
            <ul class="space-y-1.5">
                {#each bannerSuggestions.slice(0, 5) as sug, idx}
                    {@const rawA = ops.find((o) => o.tempId === sug.tempIdA)}
                    {@const rawB = ops.find((o) => o.tempId === sug.tempIdB)}
                    <!-- Semantic order: the paying row ("from") first, the other ("to") second (promotePairOrder) -->
                    {@const needSwap = rawA && rawB ? promotePairOrder(rawA, rawB, getTypeRule).swapped : false}
                    {@const opA = needSwap ? rawB : rawA}
                    {@const opB = needSwap ? rawA : rawB}
                    {@const rowIdxA = opA ? ops.indexOf(opA) : -1}
                    {@const rowIdxB = sug.isDB ? ops.findIndex((o) => o.op === 'edit' && (o as any).txId === sug.dbCandidateId) : opB ? ops.indexOf(opB) : -1}
                    {@const typeA = opA?.fields.type ?? ''}
                    {@const typeB = opB?.fields.type ?? ''}
                    {@const deltaDays = opA && opB ? Math.round((new Date(opB.fields.date).getTime() - new Date(opA.fields.date).getTime()) / 86400000) : 0}
                    {@const targetLabel = $t('transactions.types.' + sug.targetType) || sug.targetType}
                    <li class="relative pl-3 flex items-center gap-1.5 flex-wrap" data-testid="promote-suggest-item-{idx}">
                        <span class="absolute left-0 top-1 text-lf-success-on-soft">•</span>
                        <button type="button" class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-lf-info-soft border border-lf-info-line text-lf-info-on-soft hover:bg-lf-info-line font-medium" onclick={() => triggerPromoteFromSuggestion(sug)} data-testid="promote-suggest-link-{idx}">
                            <Link2 size={12} />
                            {$t('transactions.promoteSuggest.merge')}
                        </button>
                        <!-- Row A reference (clickable — "from" / negative side) -->
                        <button
                            type="button"
                            class="underline text-lf-secondary hover:text-lf-link"
                            onclick={() => {
                                if (opA) tableRef?.navigateToRowId(opA.tempId);
                            }}
                        >
                            {rowIdxA >= 0 ? $t('transactions.promoteSuggest.rowRef', {values: {n: rowIdxA + 1}}) : typeA}
                        </button>
                        <img src={getTransactionTypeIconUrl(typeA)} alt="" class="w-4 h-4 inline object-contain" />
                        <span class="text-lf-muted">{$t('common.and')}</span>
                        <!-- Row B reference -->
                        {#if sug.isDB}
                            <button
                                type="button"
                                class="underline text-lf-secondary hover:text-lf-link"
                                onclick={() => {
                                    const op = ops.find((o) => o.op === 'edit' && (o as any).txId === sug.dbCandidateId);
                                    if (op) tableRef?.navigateToRowId(op.tempId);
                                }}
                            >
                                {rowIdxB >= 0 ? $t('transactions.promoteSuggest.rowRef', {values: {n: rowIdxB + 1}}) : `#${sug.dbCandidateId}`}
                            </button>
                        {:else}
                            <button
                                type="button"
                                class="underline text-lf-secondary hover:text-lf-link"
                                onclick={() => {
                                    if (opB) tableRef?.navigateToRowId(opB.tempId);
                                }}
                            >
                                {rowIdxB >= 0 ? $t('transactions.promoteSuggest.rowRef', {values: {n: rowIdxB + 1}}) : typeB}
                            </button>
                        {/if}
                        <img src={getTransactionTypeIconUrl(typeB)} alt="" class="w-4 h-4 inline object-contain" />
                        <span class="text-lf-muted">→</span>
                        <span class="font-medium text-lf-success-on-soft">{targetLabel}</span>
                        <img src={getTransactionTypeIconUrl(sug.targetType)} alt="" class="w-4 h-4 inline object-contain" />
                        {#if deltaDays !== 0}
                            <span class="text-lf-muted">(Δ{deltaDays > 0 ? '+' : ''}{deltaDays}d)</span>
                        {/if}
                        {#if sug.targetType === 'FX_CONVERSION' && opA?.fields.cash && opB?.fields.cash}
                            {@const fxSides = promotePairOrder(opA, opB, getTypeRule)}
                            {@const fromOpFx = fxSides.from}
                            {@const toOpFx = fxSides.to}
                            {#if fromOpFx.fields.cash && toOpFx.fields.cash && fromOpFx.fields.cash.code !== toOpFx.fields.cash.code}
                                {@const fxInfo = computeFxConversionInfo(Number(fromOpFx.fields.cash.amount), fromOpFx.fields.cash.code, Number(toOpFx.fields.cash.amount), toOpFx.fields.cash.code)}
                                {#if fxInfo}
                                    {@const cacheKey = `${fxInfo.base}-${fxInfo.quote}-${fromOpFx.fields.date}`}
                                    {@const fxPoint = fxMarketCache.get(cacheKey)}
                                    {@const tooltipData = buildFxTooltipData(fxInfo, fxPoint)}
                                    <span class="text-lf-muted mx-0.5">·</span>
                                    <Tooltip html={buildFxTooltipHtml(tooltipData, $t)} position="bottom">
                                        <span class="inline-flex items-center gap-0.5 text-xs text-violet-600 dark:text-violet-400 cursor-help" data-testid="promote-suggest-fx-info-{idx}">
                                            {@html formatCurrencyCodeHtml(fxInfo.base)}
                                            <span>→</span>
                                            {@html formatCurrencyCodeHtml(fxInfo.quote)}
                                            <span class="font-mono">@ {formatFixed(fxInfo.impliedRate, 4)}</span>
                                            {#if tooltipData.staleDays != null && tooltipData.staleDays > 0}
                                                <span class="text-lf-warning">⚠️</span>
                                            {/if}
                                        </span>
                                    </Tooltip>
                                {/if}
                            {/if}
                        {/if}
                    </li>
                {/each}
            </ul>
            {#if allSuggestions.length > 5}
                <span class="text-lf-muted text-[11px] mt-1">{$t('transactions.promoteSuggest.bannerMore', {values: {n: allSuggestions.length - 5}})}</span>
            {/if}
        </div>
    {/if}
</div>
