<!--
  ParseDetailModal.svelte — Phase 07 Part 5 v5 M2

  Shows a detailed parse summary for a single file or aggregate across multiple files.
  Sections: TX by type (with type icons), asset mappings, duplicates, warnings.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {CheckCircle, AlertTriangle, HelpCircle, X, CircleAlert, FileText, Wrench} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import {getTypeIconUrl} from '$lib/stores/transactions/transactionTypeStore';
    import {getIndexColor} from '$lib/utils/colors';
    import {resolveIssueMessage} from '$lib/utils/transactions/resolveValidationMessage';
    import type {BrimParseResponse, BrimAssetMapping, BrimValidationIssue, BrimFieldTodo} from '$lib/types';

    interface ParsedFileResult {
        fileId: string;
        fileName: string;
        brokerId: number;
        brokerName: string;
        brokerIconUrl: string | null;
        brokerPortalUrl: string | null;
        pluginUsed: string;
        pluginName: string;
        status: 'pending' | 'parsing' | 'done' | 'error';
        response: BrimParseResponse | null;
        errorMessage?: string;
    }

    interface Props {
        open: boolean;
        parseResult: ParsedFileResult | null;
        /** When set, shows aggregate summary across multiple results */
        allResults?: ParsedFileResult[];
        zIndex?: number;
        onClose: () => void;
        /** Called when user clicks "Preview File" (single-file mode only) */
        onPreview?: () => void;
    }

    let {open, parseResult, allResults, zIndex = 80, onClose, onPreview}: Props = $props();

    // Determine if we're in aggregate mode
    let isAggregate = $derived(!parseResult && (allResults?.length ?? 0) > 0);
    let activeResults = $derived(allResults?.filter((r) => r.status === 'done' && r.response) ?? []);

    // Group transactions by type — works for single or aggregate
    let txByType = $derived.by(() => {
        const map = new Map<string, number>();
        if (parseResult?.response?.transactions) {
            for (const tx of parseResult.response.transactions) {
                const type = tx.type ?? 'UNKNOWN';
                map.set(type, (map.get(type) ?? 0) + 1);
            }
        } else if (isAggregate) {
            for (const r of activeResults) {
                for (const tx of r.response!.transactions ?? []) {
                    const type = tx.type ?? 'UNKNOWN';
                    map.set(type, (map.get(type) ?? 0) + 1);
                }
            }
        }
        return [...map.entries()].sort((a, b) => b[1] - a[1]);
    });

    // Asset mappings — single or merged
    let assetMappings = $derived.by(() => {
        if (parseResult?.response?.asset_mappings) return parseResult.response.asset_mappings;
        if (isAggregate) {
            // Merge, dedup by fake_asset_id
            const seen = new Set<number>();
            const result: BrimAssetMapping[] = [];
            for (const r of activeResults) {
                for (const m of r.response!.asset_mappings ?? []) {
                    if (!seen.has(m.fake_asset_id)) {
                        seen.add(m.fake_asset_id);
                        result.push(m);
                    }
                }
            }
            return result;
        }
        return [];
    });

    // Duplicate stats
    let duplicateStats = $derived.by(() => {
        if (parseResult?.response?.duplicates) {
            const dup = parseResult.response.duplicates;
            if (!dup || Array.isArray(dup)) return null;
            return {
                unique: dup.tx_unique_indices?.length ?? 0,
                possible: dup.tx_possible_duplicates?.length ?? 0,
                likely: dup.tx_likely_duplicates?.length ?? 0,
            };
        }
        if (isAggregate) {
            let unique = 0,
                possible = 0,
                likely = 0;
            for (const r of activeResults) {
                const dup = r.response!.duplicates;
                if (dup && !Array.isArray(dup)) {
                    unique += dup.tx_unique_indices?.length ?? 0;
                    possible += dup.tx_possible_duplicates?.length ?? 0;
                    likely += dup.tx_likely_duplicates?.length ?? 0;
                }
            }
            return {unique, possible, likely};
        }
        return null;
    });

    let warnings = $derived.by(() => {
        if (parseResult?.response?.warnings) return parseResult.response.warnings;
        if (isAggregate) return activeResults.flatMap((r) => r.response!.warnings ?? []);
        return [];
    });

    let validationIssues = $derived.by((): BrimValidationIssue[] => {
        if (parseResult?.response?.validation_issues) return parseResult.response.validation_issues as BrimValidationIssue[];
        if (isAggregate) return activeResults.flatMap((r) => (r.response!.validation_issues as BrimValidationIssue[] | undefined) ?? []);
        return [];
    });

    let fieldTodos = $derived.by((): BrimFieldTodo[] => {
        if (parseResult?.response?.field_todos) return parseResult.response.field_todos as BrimFieldTodo[];
        if (isAggregate) return activeResults.flatMap((r) => (r.response!.field_todos as BrimFieldTodo[] | undefined) ?? []);
        return [];
    });

    let title = $derived.by(() => {
        if (parseResult) return $t('importWizard.detailTitle', {values: {file: parseResult.fileName}});
        return $t('importWizard.summary');
    });
</script>

<ModalBase {open} {zIndex} maxWidth="2xl" onRequestClose={onClose} testId="parse-detail-modal">
    {#if parseResult || isAggregate}
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
                {title}
            </h2>
            <button type="button" class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400" onclick={onClose}>
                <X size={18} />
            </button>
        </div>

        <!-- Body -->
        <div class="p-4 space-y-5 max-h-[70vh] overflow-y-auto">
            <!-- File info bar (single file only) -->
            {#if parseResult}
                <div class="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                    <span class="flex items-center gap-1.5">
                        <BrokerIcon iconUrl={parseResult.brokerIconUrl} portalUrl={parseResult.brokerPortalUrl} altText={parseResult.brokerName} size="sm" />
                        <strong>{parseResult.brokerName}</strong>
                    </span>
                    <span class="flex items-center gap-1.5">
                        <BrokerIcon pluginCode={parseResult.pluginUsed} altText={parseResult.pluginName} size="sm" />
                        <strong>{parseResult.pluginName}</strong>
                    </span>
                    <span><strong>TX:</strong> {parseResult.response?.transactions?.length ?? 0}</span>
                </div>
            {:else if isAggregate}
                <div class="text-sm text-gray-500 dark:text-gray-400">
                    {$t('importWizard.txCount', {values: {n: activeResults.reduce((s, r) => s + (r.response!.transactions?.length ?? 0), 0), k: activeResults.length}})}
                </div>
            {/if}

            <!-- TX by Type -->
            <section>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{$t('importWizard.txByType')}</h3>
                {#if txByType.length > 0}
                    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                        {#each txByType as [type, count]}
                            <div class="flex items-center gap-2 px-3 py-1.5 rounded bg-gray-100 dark:bg-slate-800">
                                <img src={getTypeIconUrl(type)} alt={type} class="w-4 h-4" />
                                <span class="text-xs font-medium text-gray-600 dark:text-gray-400 flex-1">{type}</span>
                                <span class="text-sm font-semibold text-gray-900 dark:text-white">{count}</span>
                            </div>
                        {/each}
                    </div>
                {:else}
                    <p class="text-xs text-gray-400">—</p>
                {/if}
            </section>

            <!-- Assets -->
            <section>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{$t('importWizard.assetsSection')}</h3>
                {#if assetMappings.length > 0}
                    <div class="space-y-1.5">
                        {#each assetMappings as mapping}
                            <div class="flex items-center justify-between px-3 py-1.5 rounded bg-gray-50 dark:bg-slate-800 text-sm">
                                <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1 flex-1 min-w-0 mr-2">
                                    <span class="font-medium text-gray-900 dark:text-white truncate max-w-full">
                                        {(mapping.extracted_name as string | null) ?? (mapping.extracted_symbol as string | null) ?? (mapping.extracted_isin as string | null) ?? `ID ${mapping.fake_asset_id}`}
                                    </span>
                                    {#if mapping.extracted_symbol}
                                        {@const tc = getIndexColor(0, 200)}
                                        <span class="font-mono text-xs px-1.5 py-0.5 rounded-full shrink-0" style="background-color:{tc.bg};color:{tc.text}">
                                            Ticker: {mapping.extracted_symbol as string}
                                        </span>
                                    {/if}
                                    {#if mapping.extracted_isin}
                                        {@const ic = getIndexColor(1, 200)}
                                        <span class="font-mono text-xs px-1.5 py-0.5 rounded-full shrink-0" style="background-color:{ic.bg};color:{ic.text}">
                                            ISIN: {mapping.extracted_isin as string}
                                        </span>
                                    {/if}
                                </div>
                                <div class="flex items-center gap-1 shrink-0">
                                    {#if mapping.selected_asset_id != null}
                                        <CheckCircle size={14} class="text-emerald-500" />
                                        <span class="text-xs text-emerald-600 dark:text-emerald-400">{$t('importWizard.assetResolved')}</span>
                                    {:else}
                                        <HelpCircle size={14} class="text-amber-500" />
                                        <span class="text-xs text-amber-600 dark:text-amber-400">{$t('importWizard.assetUnresolved')}</span>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                {:else}
                    <p class="text-xs text-gray-400">{$t('importWizard.noAssets')}</p>
                {/if}
            </section>

            <!-- Validation Issues -->
            <section>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    {$t('importWizard.validationIssues')}
                    {#if validationIssues.length > 0}
                        <span class="ml-1 text-xs font-normal text-amber-600 dark:text-amber-400">({validationIssues.length})</span>
                    {/if}
                </h3>
                {#if validationIssues.length > 0}
                    <ul class="space-y-1.5">
                        {#each validationIssues as issue}
                            <li class="flex items-start gap-2 px-3 py-1.5 rounded bg-amber-50 dark:bg-amber-900/20 text-sm">
                                <CircleAlert size={14} class="mt-0.5 shrink-0 text-amber-500" />
                                <div class="min-w-0 flex-1">
                                    <span class="font-medium text-amber-800 dark:text-amber-300">{$t('importWizard.issueRow', {values: {n: issue.row}})}</span>
                                    {#if issue.field}
                                        <span class="text-xs text-amber-600 dark:text-amber-400 ml-1">({issue.field})</span>
                                    {/if}
                                    <span class="text-amber-700 dark:text-amber-400 ml-1">{@html resolveIssueMessage({code: issue.code, params: issue.params ?? undefined, error: issue.message}, $t)}</span>
                                    {#if issue.context}
                                        <span class="text-xs text-gray-500 dark:text-gray-400 ml-1">— {issue.context}</span>
                                    {/if}
                                </div>
                            </li>
                        {/each}
                    </ul>
                {:else}
                    <p class="text-xs text-gray-400">{$t('importWizard.noValidationIssues')}</p>
                {/if}
            </section>

            <!-- Manual Fields Required (Field TODOs) -->
            <section>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    {$t('importWizard.manualFieldsRequired')}
                    {#if fieldTodos.length > 0}
                        {@const hasBlocker = fieldTodos.some((t) => t.severity === 'blocker')}
                        <span class="ml-1 text-xs font-normal {hasBlocker ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'}">({fieldTodos.length})</span>
                    {/if}
                </h3>
                {#if fieldTodos.length > 0}
                    <ul class="space-y-1.5">
                        {#each fieldTodos as todo}
                            {@const isBlocker = todo.severity === 'blocker'}
                            <li class="flex items-start gap-2 px-3 py-1.5 rounded text-sm {isBlocker ? 'bg-red-50 dark:bg-red-900/20' : 'bg-amber-50 dark:bg-amber-900/20'}">
                                <Wrench size={14} class="mt-0.5 shrink-0 {isBlocker ? 'text-red-500' : 'text-amber-500'}" />
                                <div class="min-w-0 flex-1">
                                    <span class="font-medium {isBlocker ? 'text-red-800 dark:text-red-300' : 'text-amber-800 dark:text-amber-300'}">{$t('importWizard.todoRow', {values: {n: todo.tx_index + 1}})}</span>
                                    <span class="text-xs ml-1 {isBlocker ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'}">({todo.field})</span>
                                    <span class="ml-1 {isBlocker ? 'text-red-700 dark:text-red-400' : 'text-amber-700 dark:text-amber-400'}">{todo.message}</span>
                                    {#if todo.context}
                                        <span class="text-xs text-gray-500 dark:text-gray-400 ml-1">— {JSON.stringify(todo.context)}</span>
                                    {/if}
                                </div>
                            </li>
                        {/each}
                    </ul>
                {:else}
                    <p class="text-xs text-gray-400">{$t('importWizard.noFieldTodos')}</p>
                {/if}
            </section>

            <!-- Duplicates -->
            <section>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{$t('importWizard.duplicatesSection')}</h3>
                {#if duplicateStats}
                    {@const stats = duplicateStats}
                    {#if stats}
                        <div class="flex flex-wrap gap-2 text-sm">
                            <span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">✓ {$t('importWizard.uniqueTx', {values: {n: stats.unique}})}</span>
                            {#if stats.possible > 0}
                                <span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">ℹ {$t('importWizard.possibleDuplicates', {values: {n: stats.possible}})}</span>
                            {/if}
                            {#if stats.likely > 0}
                                <span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">⚠ {$t('importWizard.likelyDuplicates', {values: {n: stats.likely}})}</span>
                            {/if}
                        </div>
                    {/if}
                {:else}
                    <p class="text-xs text-gray-400">{$t('importWizard.noDuplicates')}</p>
                {/if}
            </section>

            <!-- Warnings -->
            <section>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{$t('importWizard.warningsSection')}</h3>
                {#if warnings.length > 0}
                    <ul class="space-y-1">
                        {#each warnings as warning}
                            <li class="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-400">
                                <AlertTriangle size={14} class="mt-0.5 shrink-0" />
                                <span>{warning}</span>
                            </li>
                        {/each}
                    </ul>
                {:else}
                    <p class="text-xs text-gray-400">{$t('importWizard.noWarnings')}</p>
                {/if}
            </section>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700">
            <div>
                {#if parseResult && onPreview}
                    <button
                        type="button"
                        class="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                        onclick={onPreview}
                    >
                        <FileText size={14} />{$t('importWizard.previewFile')}
                    </button>
                {/if}
            </div>
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={onClose}>
                {$t('common.close')}
            </button>
        </div>
    {/if}
</ModalBase>
