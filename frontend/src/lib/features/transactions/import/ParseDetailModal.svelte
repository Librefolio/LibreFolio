<!--
  ParseDetailModal.svelte — Phase 07 Part 5 v5 M2

  Shows a detailed parse summary for a single file or aggregate across multiple files.
  Sections: TX by type (with type icons), asset mappings, duplicates, warnings.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {CheckCircle, HelpCircle, X, CircleAlert, FileText, Wrench, Info, Eye, Download} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import {getTransactionTypeIconUrl} from '$lib/features/transactions/transactionTypeStore';
    import {getIndexColor} from '$lib/utils/colors';
    import {resolveIssueMessage, translateFieldName} from '$lib/features/transactions/resolveValidationMessage';
    import {resolveBrimTodoMessage} from '$lib/features/transactions/resolveBrimNotice';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';
    import BrimNoticeList from '$lib/features/transactions/import/BrimNoticeList.svelte';
    import BrimEvidenceTable from '$lib/features/transactions/import/BrimEvidenceTable.svelte';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {maskable} from '$lib/utils/privacy/maskable';
    import type {BrimParseResponse, BrimAssetMapping, BrimValidationIssue, BrimFieldTodo, BrimNotice} from '$lib/types';

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
        /** A report set analysed through its combined file (the row's `fileId` is the combined file). */
        set?: {memberNames: string[]; summary: Record<string, unknown> | null; reused: boolean} | null;
    }

    /** The combine outcomes shown for a report set, in reading order. */
    const SET_OUTCOMES = ['pair', 'standalone', 'summarized', 'deferred', 'excluded'] as const;
    const OUTCOME_ICON: Record<(typeof SET_OUTCOMES)[number], string> = {pair: '✅', standalone: '💶', summarized: '📦', deferred: '⏳', excluded: '🚫'};

    function summaryCounts(summary: Record<string, unknown> | null | undefined, key: string): Record<string, number> {
        const raw = summary?.[key];
        if (!raw || typeof raw !== 'object') return {};
        const counts: Record<string, number> = {};
        for (const [name, value] of Object.entries(raw as Record<string, unknown>)) {
            if (typeof value === 'number' && Number.isFinite(value)) counts[name] = value;
        }
        return counts;
    }

    function reasonLabel(reason: string): string {
        const key = `importWizard.reportSet.reason.${reason}`;
        const translated = $t(key);
        return translated === key ? reason : translated;
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
    let activeResults = $derived(allResults?.filter((r) => r.response != null && r.status !== 'error') ?? []);

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

    let warnings = $derived.by((): BrimNotice[] => {
        if (parseResult?.response?.warnings) return parseResult.response.warnings;
        if (isAggregate) return activeResults.flatMap((r) => r.response!.warnings ?? []);
        return [];
    });

    let validationIssues = $derived.by((): BrimValidationIssue[] => {
        if (parseResult?.response?.validation_issues) return parseResult.response.validation_issues as BrimValidationIssue[];
        if (isAggregate) return activeResults.flatMap((r) => (r.response!.validation_issues as BrimValidationIssue[] | undefined) ?? []);
        return [];
    });

    let fieldTodoEntries = $derived.by((): Array<{fileName: string | null; todo: BrimFieldTodo}> => {
        if (parseResult?.response?.field_todos) return (parseResult.response.field_todos as BrimFieldTodo[]).map((todo) => ({fileName: null, todo}));
        if (isAggregate) return activeResults.flatMap((r) => ((r.response!.field_todos as BrimFieldTodo[] | undefined) ?? []).map((todo) => ({fileName: r.fileName, todo})));
        return [];
    });
    let hasBlockerTodo = $derived(fieldTodoEntries.some((e) => e.todo.severity === 'blocker'));

    /** A todo as the section shows it: the message, the context keys the frontend understands, the rest. */
    interface TodoView {
        message: string;
        facts: Array<{key: string; label: string; value: string}>;
        suggestions: string[];
        /** The context keys no fact understood, pretty-printed for the closed technical details. */
        technical: string | null;
    }

    /** Plugin hints read by the fix step, with nothing to tell the user here. */
    const TODO_SILENT_KEYS: ReadonlySet<string> = new Set(['split_hint', 'compare_nominal']);

    function todoMoney(value: unknown, code: unknown): string | null {
        const amount = typeof value === 'number' ? value : typeof value === 'string' && value.trim() !== '' ? Number(value) : NaN;
        if (!Number.isFinite(amount) || typeof code !== 'string' || code === '') return null;
        return formatCurrencyAmountPlain(amount, code);
    }

    /** The shared todo rule: the localised wording of the reason code, else the plugin's own message. */
    function todoView(todo: BrimFieldTodo): TodoView {
        const ctx = (todo.context ?? {}) as Record<string, unknown>;
        const message = resolveBrimTodoMessage({reasonCode: todo.reason_code, message: todo.message, context: ctx}, $t);
        const used = new Set<string>(TODO_SILENT_KEYS);
        const facts: TodoView['facts'] = [];

        if (typeof ctx.row === 'number' || (typeof ctx.row === 'string' && ctx.row !== '')) {
            facts.push({key: 'row', label: $t('importWizard.parseDetail.sourceRow'), value: String(ctx.row)});
            used.add('row');
        }
        const cash = todoMoney(ctx.cash, ctx.currency);
        if (cash) {
            facts.push({key: 'cash', label: $t('importWizard.fixStep.splitRowAmountLabel'), value: cash});
            used.add('cash').add('currency');
        }
        const charges = todoMoney(ctx.charges, ctx.currency);
        if (charges) {
            facts.push({key: 'charges', label: $t('importWizard.parseDetail.charges'), value: charges});
            used.add('charges').add('currency');
        }
        // Withheld when the plugin did not compare: on a sale the face value means nothing next to the proceeds.
        if (ctx.compare_nominal === true && (typeof ctx.nominale === 'string' || typeof ctx.nominale === 'number')) {
            facts.push({key: 'nominale', label: $t('importWizard.fixStep.splitNominalLabel'), value: todoMoney(ctx.nominale, ctx.currency) ?? maskable(String(ctx.nominale))});
            used.add('nominale').add('nominale_row');
        }
        const suggestions = Array.isArray(ctx.split_suggestions) ? ctx.split_suggestions.filter((s): s is string => typeof s === 'string' && s !== '') : [];
        if (Array.isArray(ctx.split_suggestions)) used.add('split_suggestions');

        const rest = Object.fromEntries(Object.entries(ctx).filter(([name]) => !used.has(name)));
        return {message, facts, suggestions, technical: Object.keys(rest).length > 0 ? JSON.stringify(rest, null, 2) : null};
    }

    let title = $derived.by(() => {
        if (parseResult) return $t('importWizard.detailTitle', {values: {file: parseResult.fileName}});
        return $t('importWizard.summary');
    });
</script>

<ModalBase {open} {zIndex} maxWidth="2xl" onRequestClose={onClose} testId="parse-detail-modal">
    {#if parseResult || isAggregate}
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-lf-subtle">
            <h2 class="text-lg font-semibold text-lf-primary">
                {title}
            </h2>
            <button type="button" class="p-1.5 rounded-lg hover:bg-lf-hover text-lf-muted" onclick={onClose}>
                <X size={18} />
            </button>
        </div>

        <!-- Body -->
        <div class="p-4 space-y-5 max-h-[70vh] overflow-y-auto">
            <!-- File info bar (single file only) -->
            {#if parseResult}
                <div class="flex flex-wrap items-center gap-4 text-sm text-lf-secondary">
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
                <div class="text-sm text-lf-muted">
                    {$t('importWizard.txCount', {values: {n: activeResults.reduce((s, r) => s + (r.response!.transactions?.length ?? 0), 0), k: activeResults.length}})}
                </div>
            {/if}

            <!-- Report set: how the exports were matched -->
            {#if parseResult?.set}
                {@const outcomes = summaryCounts(parseResult.set.summary, 'outcomes')}
                {@const reasons = summaryCounts(parseResult.set.summary, 'reasons')}
                <section data-testid="parse-detail-pairing" data-pair={outcomes.pair ?? 0} data-standalone={outcomes.standalone ?? 0} data-summarized={outcomes.summarized ?? 0} data-deferred={outcomes.deferred ?? 0} data-excluded={outcomes.excluded ?? 0}>
                    <h3 class="text-sm font-semibold text-lf-secondary mb-2">{$t('importWizard.reportSet.pairingTitle')}</h3>
                    <p class="mb-2 text-xs text-lf-muted">{parseResult.set.memberNames.join(' + ')}</p>
                    <div class="flex flex-wrap gap-1.5">
                        {#each SET_OUTCOMES as outcome}
                            {@const count = outcomes[outcome] ?? 0}
                            <span class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs {count > 0 ? 'bg-lf-panel text-lf-primary' : 'bg-lf-panel text-lf-muted'}" data-testid="parse-detail-pairing-outcome" data-outcome={outcome} data-count={count}>
                                <span aria-hidden="true">{OUTCOME_ICON[outcome]}</span>
                                <span class="font-semibold tabular-nums">{count}</span>
                                <span>{$t(`importWizard.reportSet.outcome.${outcome}`)}</span>
                            </span>
                        {/each}
                    </div>
                    {#if Object.keys(reasons).length > 0}
                        <table class="mt-3 w-full max-w-md text-xs" data-testid="parse-detail-pairing-reasons">
                            <thead>
                                <tr class="text-lf-muted">
                                    <th class="py-1 pr-3 text-left font-normal">{$t('importWizard.reportSet.column.reason')}</th>
                                    <th class="py-1 text-right font-normal">{$t('importWizard.reportSet.column.rows')}</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-lf-subtle">
                                {#each Object.entries(reasons) as [reason, count]}
                                    <tr class="text-lf-secondary" data-testid="parse-detail-pairing-reason" data-reason={reason} data-count={count}>
                                        <td class="py-1 pr-3">{reasonLabel(reason)}</td>
                                        <td class="py-1 text-right font-mono tabular-nums">{count}</td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    {/if}
                    <div class="mt-3 flex flex-wrap items-center gap-3 text-xs">
                        {#if onPreview}
                            <button type="button" class="inline-flex items-center gap-1 text-lf-link hover:underline" onclick={onPreview} data-testid="parse-detail-preview-combined">
                                <Eye size={12} />{$t('importWizard.reportSet.previewCombined')}
                            </button>
                        {/if}
                        <a class="inline-flex items-center gap-1 text-lf-link hover:underline" href={`/api/v1/brokers/import/files/${encodeURIComponent(parseResult.fileId)}/download`} data-testid="parse-detail-download-combined">
                            <Download size={12} />{$t('importWizard.reportSet.downloadCombined')}
                        </a>
                    </div>
                </section>
            {/if}

            <!-- TX by Type -->
            <section>
                <h3 class="text-sm font-semibold text-lf-secondary mb-2">{$t('importWizard.txByType')}</h3>
                {#if txByType.length > 0}
                    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                        {#each txByType as [type, count]}
                            <div class="flex items-center gap-2 px-3 py-1.5 rounded bg-lf-panel">
                                <img src={getTransactionTypeIconUrl(type)} alt={type} class="w-4 h-4" />
                                <span class="text-xs font-medium text-lf-secondary flex-1">{$t('transactions.types.' + type)}</span>
                                <span class="text-sm font-semibold text-lf-primary">{count}</span>
                            </div>
                        {/each}
                    </div>
                {:else}
                    <p class="text-xs text-lf-muted">—</p>
                {/if}
            </section>

            <!-- Assets -->
            <section>
                <h3 class="text-sm font-semibold text-lf-secondary mb-2">{$t('common.assets')}</h3>
                {#if assetMappings.length > 0}
                    <div class="space-y-1.5">
                        {#each assetMappings as mapping}
                            <div class="flex items-center justify-between px-3 py-1.5 rounded bg-lf-panel text-sm">
                                <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1 flex-1 min-w-0 mr-2">
                                    <span class="font-medium text-lf-primary truncate max-w-full">
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
                                        <CheckCircle size={14} class="text-lf-success" />
                                        <span class="text-xs text-lf-success">{$t('importWizard.assetResolved')}</span>
                                    {:else}
                                        <HelpCircle size={14} class="text-lf-warning" />
                                        <span class="text-xs text-lf-warning">{$t('importWizard.assetUnresolved')}</span>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                {:else}
                    <p class="text-xs text-lf-muted">{$t('importWizard.noAssets')}</p>
                {/if}
            </section>

            <!-- Validation Issues -->
            <section>
                <h3 class="text-sm font-semibold text-lf-secondary mb-2">
                    {$t('importWizard.validationIssues')}
                    {#if validationIssues.length > 0}
                        <span class="ml-1 text-xs font-normal text-lf-warning">({validationIssues.length})</span>
                    {/if}
                </h3>
                {#if validationIssues.length > 0}
                    <ul class="space-y-1.5">
                        {#each validationIssues as issue}
                            <li class="flex items-start gap-2 px-3 py-1.5 rounded bg-lf-warning-soft text-sm">
                                <CircleAlert size={14} class="mt-0.5 shrink-0 text-lf-warning" />
                                <div class="min-w-0 flex-1">
                                    <span class="font-medium text-lf-warning-on-soft">{$t('common.rowN', {values: {n: issue.row}})}</span>
                                    {#if issue.field}
                                        <span class="text-xs text-lf-warning ml-1">({issue.field})</span>
                                    {/if}
                                    <span class="text-lf-warning ml-1">{@html sanitizeHtml(resolveIssueMessage({code: issue.code, params: issue.params ?? undefined, error: issue.message}, $t))}</span>
                                    {#if issue.context}
                                        <span class="text-xs text-lf-muted ml-1">— {issue.context}</span>
                                    {/if}
                                </div>
                            </li>
                        {/each}
                    </ul>
                {:else}
                    <p class="text-xs text-lf-muted">{$t('importWizard.noValidationIssues')}</p>
                {/if}
            </section>

            <!-- Manual Fields (Field TODOs) — 'Required' only when blockers exist, else 'To Verify' -->
            <section>
                <h3 class="text-sm font-semibold text-lf-secondary mb-2 flex items-center gap-1.5">
                    <span>
                        {hasBlockerTodo ? $t('importWizard.manualFieldsRequired') : $t('importWizard.manualFieldsToVerify')}
                        {#if fieldTodoEntries.length > 0}
                            <span class="ml-1 text-xs font-normal {hasBlockerTodo ? 'text-lf-danger' : 'text-lf-warning'}">({fieldTodoEntries.length})</span>
                        {/if}
                    </span>
                    {#if fieldTodoEntries.length > 0}
                        <Tooltip text={$t('importWizard.manualFieldsTooltip')} position="right" maxWidth="320px">
                            <Info size={13} class="shrink-0 text-lf-muted hover:text-lf-secondary" />
                        </Tooltip>
                    {/if}
                </h3>
                {#if fieldTodoEntries.length > 0}
                    <ul class="space-y-1.5">
                        {#each fieldTodoEntries as entry}
                            {@const todo = entry.todo}
                            {@const isBlocker = todo.severity === 'blocker'}
                            {@const view = todoView(todo)}
                            <li class="flex items-start gap-2 px-3 py-1.5 rounded text-sm {isBlocker ? 'bg-lf-danger-soft' : 'bg-lf-warning-soft'}" data-testid="parse-detail-todo" data-reason-code={todo.reason_code} data-severity={todo.severity}>
                                <Wrench size={14} class="mt-0.5 shrink-0 {isBlocker ? 'text-lf-danger' : 'text-lf-warning'}" />
                                <div class="min-w-0 flex-1 space-y-1.5">
                                    <div>
                                        {#if entry.fileName}
                                            <span class="text-xs text-lf-muted mr-1">{entry.fileName} ·</span>
                                        {/if}
                                        <span class="font-medium {isBlocker ? 'text-lf-danger-on-soft' : 'text-lf-warning-on-soft'}">{$t('importWizard.todoRow', {values: {n: todo.tx_index + 1}})}</span>
                                        <span class="text-xs ml-1 {isBlocker ? 'text-lf-danger' : 'text-lf-warning'}">({translateFieldName(todo.field, $t)})</span>
                                        <span class="ml-1 {isBlocker ? 'text-lf-danger' : 'text-lf-warning'}">{view.message}</span>
                                    </div>
                                    {#if view.facts.length > 0}
                                        <dl class="flex flex-wrap gap-x-4 gap-y-0.5 text-xs">
                                            {#each view.facts as fact (fact.key)}
                                                <div class="flex gap-1" data-testid="parse-detail-todo-fact" data-fact={fact.key}>
                                                    <dt class="text-lf-muted">{fact.label}</dt>
                                                    <dd class="font-mono text-lf-primary">{fact.value}</dd>
                                                </div>
                                            {/each}
                                        </dl>
                                    {/if}
                                    {#if view.suggestions.length > 0}
                                        <div class="text-xs">
                                            <p class="text-lf-muted">{$t('importWizard.parseDetail.suggestions')}</p>
                                            <ul class="list-disc space-y-0.5 pl-5 text-lf-secondary">
                                                {#each view.suggestions as suggestion}
                                                    <li>{suggestion}</li>
                                                {/each}
                                            </ul>
                                        </div>
                                    {/if}
                                    {#each todo.evidence ?? [] as evidence}
                                        <BrimEvidenceTable {evidence} tone={isBlocker ? 'blocker' : 'warning'} collapsible />
                                    {/each}
                                    {#if view.technical}
                                        <details class="text-xs" data-testid="parse-detail-todo-technical">
                                            <summary class="cursor-pointer text-lf-muted">{$t('importWizard.parseDetail.technical')}</summary>
                                            <pre class="mt-1 overflow-x-auto whitespace-pre-wrap break-all rounded bg-lf-card/70 p-2 font-mono text-[11px] text-lf-secondary">{view.technical}</pre>
                                        </details>
                                    {/if}
                                </div>
                            </li>
                        {/each}
                    </ul>
                {:else}
                    <p class="text-xs text-lf-muted">{$t('importWizard.noFieldTodos')}</p>
                {/if}
            </section>

            <!-- Duplicates -->
            <section>
                <h3 class="text-sm font-semibold text-lf-secondary mb-2">{$t('importWizard.duplicatesSection')}</h3>
                {#if duplicateStats}
                    {@const stats = duplicateStats}
                    {#if stats}
                        <div class="flex flex-wrap gap-2 text-sm">
                            <span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-lf-success-soft text-lf-success-on-soft">✓ {$t('importWizard.uniqueTx', {values: {n: stats.unique}})}</span>
                            {#if stats.possible > 0}
                                <span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-lf-info-soft text-lf-info-on-soft">ℹ {$t('importWizard.possibleDuplicates', {values: {n: stats.possible}})}</span>
                            {/if}
                            {#if stats.likely > 0}
                                <span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-lf-warning-soft text-lf-warning-on-soft">⚠ {$t('importWizard.likelyDuplicates', {values: {n: stats.likely}})}</span>
                            {/if}
                        </div>
                    {/if}
                {:else}
                    <p class="text-xs text-lf-muted">{$t('importWizard.noDuplicates')}</p>
                {/if}
            </section>

            <!-- Warnings -->
            <section>
                <h3 class="text-sm font-semibold text-lf-secondary mb-2">{$t('importWizard.warningsSection')}</h3>
                {#if warnings.length > 0}
                    <BrimNoticeList notices={warnings} />
                {:else}
                    <p class="text-xs text-lf-muted">{$t('importWizard.noWarnings')}</p>
                {/if}
            </section>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between p-4 border-t border-lf-subtle">
            <div>
                {#if parseResult && onPreview}
                    <button type="button" class="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover transition-colors" onclick={onPreview}>
                        <FileText size={14} />{$t('importWizard.previewFile')}
                    </button>
                {/if}
            </div>
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover" onclick={onClose} data-testid="parse-detail-close">
                {$t('common.close')}
            </button>
        </div>
    {/if}
</ModalBase>
