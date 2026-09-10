<script lang="ts">
    import {AlertTriangle, LoaderCircle, RefreshCw} from 'lucide-svelte';
    import {locale, t} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import type {ToolClientError, ToolDiagnosticsResponse} from './contracts';
    import {toolDocumentationPath, toolErrorMessage, toolName} from './presentation';

    interface Props {
        snapshot: ToolDiagnosticsResponse | null;
        loading: boolean;
        error: ToolClientError | null;
        onRefresh: () => void;
    }

    let {snapshot, loading, error, onRefresh}: Props = $props();

    type Policy = ToolDiagnosticsResponse['policy'];
    type Pool = ToolDiagnosticsResponse['pool'];
    type DiscoveryReason = ToolDiagnosticsResponse['failures'][number]['reason'];

    const poolCounters = [
        {field: 'active', key: 'active', fallback: 'Active jobs'},
        {field: 'queued', key: 'queued', fallback: 'Queued jobs'},
        {field: 'pending', key: 'pending', fallback: 'Pending jobs'},
        {field: 'degraded_lanes', key: 'degradedLanes', fallback: 'Degraded lanes'},
        {field: 'completed', key: 'completed', fallback: 'Completed jobs'},
        {field: 'failed', key: 'failed', fallback: 'Failed jobs'},
    ] as const satisfies readonly {field: Exclude<keyof Pool, 'available'>; key: string; fallback: string}[];

    const policyFields = [
        {field: 'workers', key: 'workers', fallback: 'Worker lanes', unit: 'count'},
        {field: 'max_batch_items', key: 'maxBatchItems', fallback: 'Maximum items per batch', unit: 'count'},
        {field: 'max_pending_items', key: 'maxPendingItems', fallback: 'Maximum pending jobs', unit: 'count'},
        {field: 'max_pending_per_principal', key: 'maxPendingPerPrincipal', fallback: 'Maximum pending jobs per account', unit: 'count'},
        {field: 'max_batches_per_principal', key: 'maxBatchesPerPrincipal', fallback: 'Maximum concurrent batches per account', unit: 'count'},
        {field: 'max_json_depth', key: 'maxJsonDepth', fallback: 'Maximum JSON depth', unit: 'count'},
        {field: 'max_request_bytes', key: 'maxRequestBytes', fallback: 'Maximum request size', unit: 'bytes'},
        {field: 'max_parameter_bytes', key: 'maxParameterBytes', fallback: 'Maximum parameter size per item', unit: 'bytes'},
        {field: 'max_result_bytes', key: 'maxResultBytes', fallback: 'Maximum result size per item', unit: 'bytes'},
        {field: 'max_response_bytes', key: 'maxResponseBytes', fallback: 'Maximum response size', unit: 'bytes'},
        {field: 'envelope_reserve_bytes', key: 'envelopeReserveBytes', fallback: 'Envelope size reserve', unit: 'bytes'},
        {field: 'queue_timeout_ms', key: 'queueTimeout', fallback: 'Queue timeout', unit: 'ms'},
        {field: 'job_timeout_ms', key: 'jobTimeout', fallback: 'Job hard timeout', unit: 'ms'},
        {field: 'soft_timeout_ms', key: 'softTimeout', fallback: 'Job soft timeout', unit: 'ms'},
        {field: 'output_reserve_ms', key: 'outputReserve', fallback: 'Output time reserve', unit: 'ms'},
        {field: 'cleanup_timeout_ms', key: 'cleanupTimeout', fallback: 'Cleanup timeout', unit: 'ms'},
        {field: 'ingress_timeout_ms', key: 'ingressTimeout', fallback: 'Ingress timeout', unit: 'ms'},
        {field: 'response_reserve_ms', key: 'responseReserve', fallback: 'Response time reserve', unit: 'ms'},
        {field: 'request_timeout_ms', key: 'requestTimeout', fallback: 'Server request timeout', unit: 'ms'},
        {field: 'client_timeout_ms', key: 'clientTimeout', fallback: 'Tool client timeout', unit: 'ms'},
    ] as const satisfies readonly {field: keyof Policy; key: string; fallback: string; unit: 'count' | 'bytes' | 'ms'}[];

    const reasonFallbacks = {
        import_failed: 'Plugin import failed',
        invalid_plugin: 'Invalid plugin definition',
        invalid_code: 'Invalid tool code',
        duplicate_code: 'Duplicate tool code; claimants quarantined',
        invalid_descriptor: 'Invalid tool descriptor',
        invalid_input_model: 'Invalid input model',
        invalid_output_model: 'Invalid output model',
        invalid_schema: 'Schema cannot be published',
        invalid_operation_policy: 'Invalid operation policy',
    } satisfies Record<DiscoveryReason, string>;

    const numberFormat = $derived(new Intl.NumberFormat($locale ?? 'en'));
    const errorCopy = $derived(error ? toolErrorMessage(error) : null);
    const degraded = $derived(snapshot !== null && (snapshot.failures.length > 0 || !snapshot.pool.available || snapshot.pool.degraded_lanes > 0));

    function policyValue(value: Policy[keyof Policy], unit: 'count' | 'bytes' | 'ms'): string {
        const formatted = numberFormat.format(value);
        if (unit === 'bytes') return `${formatted} ${$t('common.bytes')}`;
        if (unit === 'ms') return $t('tools.metrics.milliseconds', {default: '{value} ms', values: {value: formatted}});
        return formatted;
    }
</script>

<section
    class="mt-4 min-w-0 space-y-4"
    aria-label={$t('tools.diagnostics.title', {default: 'Tool diagnostics'})}
    data-testid="tool-diagnostics-panel"
    data-state={loading ? 'loading' : error ? 'error' : snapshot ? (degraded ? 'degraded' : 'ready') : 'idle'}
    data-busy={loading ? 'true' : 'false'}
    aria-busy={loading}
>
    <header class="flex flex-wrap items-start justify-between gap-3">
        <p class="max-w-prose text-xs text-gray-500 dark:text-gray-400">
            {$t('tools.diagnostics.scopeDescription', {
                default: 'This snapshot describes one responding API process, not the whole instance. Catalogue and diagnostics are separate reads. Reload to update the snapshot.',
            })}
        </p>
        <button
            type="button"
            onclick={onRefresh}
            disabled={loading}
            class="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700 dark:focus-visible:outline-green-400"
            data-testid="tool-diagnostics-refresh"
        >
            <RefreshCw size={15} aria-hidden="true" />
            {$t('common.refresh')}
        </button>
    </header>

    {#if loading}
        <p class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300" role="status" data-testid="tool-diagnostics-loading">
            <LoaderCircle size={18} class="animate-spin motion-reduce:animate-none" aria-hidden="true" />
            {$t('common.loading')}
        </p>
    {:else if error && errorCopy}
        <div class="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="tool-diagnostics-error" data-error-code={error.code}>
            <p>{$t(errorCopy.key, {default: errorCopy.fallback})}</p>
            <button type="button" onclick={onRefresh} class="rounded border border-current px-3 py-1.5 focus-visible:outline-2 focus-visible:outline-offset-2" data-testid="tool-diagnostics-retry">{$t('common.retry')}</button>
        </div>
    {:else if snapshot}
        <dl class="grid grid-cols-1 gap-3 text-xs sm:grid-cols-2">
            <div class="min-w-0">
                <dt class="font-medium text-gray-700 dark:text-gray-300">{$t('tools.diagnostics.scope', {default: 'Snapshot scope'})}</dt>
                <dd class="mt-1 break-words text-gray-600 dark:text-gray-400" data-testid="tool-diagnostics-scope"><code>{snapshot.scope}</code></dd>
            </div>
            <div class="min-w-0">
                <dt class="font-medium text-gray-700 dark:text-gray-300">{$t('tools.diagnostics.runtime', {default: 'API process identifier'})}</dt>
                <dd class="mt-1 break-words text-gray-600 dark:text-gray-400" data-testid="tool-diagnostics-runtime"><code>{snapshot.runtime_id}</code></dd>
            </div>
        </dl>

        {#if degraded}
            <p class="flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-200" role="status" data-testid="tool-diagnostics-degraded">
                <AlertTriangle size={17} aria-hidden="true" class="shrink-0" />
                {$t('tools.diagnostics.degraded', {default: 'Discovery failures or reduced execution capacity were reported. Other tools may remain available.'})}
            </p>
        {/if}

        <section class="space-y-3 rounded-lg border border-gray-200 p-3 dark:border-gray-700" data-testid="tool-diagnostics-pool">
            <h5 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$t('tools.diagnostics.pool.title', {default: 'Execution pool snapshot'})}</h5>
            <p class="text-xs text-gray-600 dark:text-gray-400">
                {$t('tools.diagnostics.pool.availability', {default: 'Execution pool availability'})}:
                <span class={snapshot.pool.available ? 'text-green-800 dark:text-green-300' : 'text-amber-800 dark:text-amber-300'} data-testid="tool-pool-available">
                    {snapshot.pool.available ? $t('tools.status.available', {default: 'Available'}) : $t('tools.status.unavailable', {default: 'Unavailable'})}
                </span>
            </p>
            <dl class="grid grid-cols-1 gap-3 text-xs sm:grid-cols-2 lg:grid-cols-3">
                {#each poolCounters as counter (counter.field)}
                    <div class="min-w-0">
                        <dt class="text-gray-500 dark:text-gray-400">{$t(`tools.diagnostics.pool.${counter.key}`, {default: counter.fallback})}</dt>
                        <dd class="mt-1 break-words font-medium tabular-nums text-gray-900 dark:text-gray-100" data-testid={`tool-pool-${counter.field}`}>{numberFormat.format(snapshot.pool[counter.field])}</dd>
                    </div>
                {/each}
            </dl>
        </section>

        <section class="space-y-3" data-testid="tool-diagnostics-loaded">
            <h5 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$t('tools.diagnostics.loaded', {default: 'Tools loaded in this API process'})} ({numberFormat.format(snapshot.loaded.length)})</h5>
            {#if snapshot.loaded.length === 0}
                <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="tool-diagnostics-loaded-empty">{$t('tools.diagnostics.noLoaded', {default: 'No tools are loaded in this API process.'})}</p>
            {:else}
                <ul class="space-y-2 text-xs">
                    {#each snapshot.loaded as item (item.tool_code)}
                        {@const documentation = toolDocumentationPath(item)}
                        <li class="flex min-w-0 flex-wrap items-start justify-between gap-2 rounded-lg bg-gray-50 p-3 dark:bg-gray-900/40" data-testid="tool-diagnostics-loaded-entry">
                            <div class="min-w-0">
                                <p class="break-words font-medium text-gray-800 dark:text-gray-200">{toolName(item, $t)} · <code>{item.tool_code}</code></p>
                                <p class="mt-1 break-words text-gray-500 dark:text-gray-400">
                                    {$t('tools.contractVersion', {default: 'Contract'})}: {item.contract_version}
                                    · {$t('tools.implementationVersion', {default: 'Implementation'})}: {item.implementation_version}
                                </p>
                            </div>
                            {#if documentation}
                                <DocsLink path={documentation} label={$t('common.documentation')} icon="book" size={16} testId={`tool-diagnostics-docs-${item.tool_code}`} />
                            {/if}
                        </li>
                    {/each}
                </ul>
            {/if}
        </section>

        <section class="space-y-3" data-testid="tool-diagnostics-failures">
            <h5 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$t('tools.diagnostics.failures', {default: 'Discovery failures'})} ({numberFormat.format(snapshot.failures.length)})</h5>
            {#if snapshot.failures.length === 0}
                <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="tool-diagnostics-failures-empty">{$t('tools.diagnostics.noFailures', {default: 'No discovery failures were reported in this snapshot.'})}</p>
            {:else}
                <ul class="space-y-2 text-xs">
                    {#each snapshot.failures as failure}
                        <li class="space-y-1 rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" data-testid="tool-diagnostic-failure" data-reason={failure.reason}>
                            <p class="break-words font-medium">{failure.tool_code ?? $t('tools.catalog.unknownTool', {default: 'Unidentified tool'})}</p>
                            <p class="break-words" data-testid="tool-diagnostic-failure-filename"><code>{failure.filename || $t('common.noData')}</code></p>
                            <p>{$t(`tools.diagnostics.reason.${failure.reason}`, {default: reasonFallbacks[failure.reason]})}</p>
                        </li>
                    {/each}
                </ul>
            {/if}
        </section>

        <details class="border-t border-gray-200 pt-3 dark:border-gray-700" data-testid="tool-diagnostics-policy">
            <summary class="cursor-pointer rounded text-sm font-medium text-gray-800 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-libre-green dark:text-gray-200 dark:focus-visible:outline-green-400" data-testid="tool-diagnostics-policy-toggle">
                {$t('tools.diagnostics.policy.title', {default: 'Effective platform limits'})}
            </summary>
            <p class="mt-3 text-xs text-gray-500 dark:text-gray-400">
                {$t('tools.diagnostics.policy.description', {
                    default: 'Configuration limits, not measured timings or performance guarantees. Tool operations may declare stricter limits. Durations are not added together.',
                })}
            </p>
            <dl class="mt-3 grid grid-cols-1 gap-3 text-xs sm:grid-cols-2 lg:grid-cols-3">
                {#each policyFields as field (field.field)}
                    <div class="min-w-0">
                        <dt class="text-gray-500 dark:text-gray-400">{$t(`tools.diagnostics.policy.${field.key}`, {default: field.fallback})}</dt>
                        <dd class="mt-1 break-words font-medium tabular-nums text-gray-900 dark:text-gray-100" data-testid={`tool-policy-${field.field}`}>{policyValue(snapshot.policy[field.field], field.unit)}</dd>
                    </div>
                {/each}
            </dl>
        </details>
    {:else}
        <p class="text-xs text-gray-500 dark:text-gray-400" role="status" data-testid="tool-diagnostics-idle">
            {$t('tools.diagnostics.notLoaded', {default: 'No diagnostic snapshot is loaded. Reload to request one.'})}
        </p>
    {/if}
</section>
