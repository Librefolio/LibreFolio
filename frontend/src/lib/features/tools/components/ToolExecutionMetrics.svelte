<script module lang="ts">
    import type {z} from 'zod';
    import type {toolTransportSchemas} from '$lib/api/generated-tools';

    // The generated transport codec comes from backend/app/schemas/tools.py.
    type ToolComputeResponse = z.output<typeof toolTransportSchemas.computeResponse>;
    export type ToolItemMetrics = ToolComputeResponse['results'][number]['metrics'];
    export type ToolBatchMetrics = ToolComputeResponse['metrics'];

    export interface ToolExecutionMetricsProps {
        /** Both metrics must belong to the same account/revision-guarded response. */
        item: ToolItemMetrics;
        batch?: ToolBatchMetrics | null;
    }
</script>

<script lang="ts">
    import {Clock3} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import {uiLocale} from '$lib/stores/app/uiLocale';

    let {item, batch = null}: ToolExecutionMetricsProps = $props();

    const phases = [
        {key: 'queue_wait_ms', label: 'tools.metrics.queueWait', fallback: 'Queue wait'},
        {key: 'startup_ms', label: 'tools.metrics.startup', fallback: 'Worker startup'},
        {key: 'compute_ms', label: 'tools.metrics.compute', fallback: 'Compute'},
        {key: 'execution_ms', label: 'tools.metrics.execution', fallback: 'Worker execution'},
        {key: 'cleanup_ms', label: 'tools.metrics.cleanup', fallback: 'Cleanup'},
    ] as const satisfies readonly {key: keyof ToolItemMetrics; label: string; fallback: string}[];

    const validationPhases = [
        {key: 'input_validation_ms', label: 'tools.metrics.inputValidation', fallback: 'Input validation'},
        {key: 'output_validation_ms', label: 'tools.metrics.outputValidation', fallback: 'Output validation'},
        {key: 'serialization_ms', label: 'tools.metrics.serialization', fallback: 'Output serialization'},
    ] as const satisfies readonly {key: keyof ToolItemMetrics; label: string; fallback: string}[];

    const numberFormat = $derived(new Intl.NumberFormat(uiLocale()));

    function duration(value: number | null): string {
        return value === null
            ? $t('common.noData')
            : $t('tools.metrics.milliseconds', {
                  default: '{value} ms',
                  values: {value: numberFormat.format(value)},
              });
    }
</script>

<section class="min-w-0 rounded-xl border border-lf-subtle bg-lf-card p-4 text-lf-primary" aria-label={$t('tools.metrics.title', {default: 'Backend timings'})} data-testid="tool-execution-metrics" data-busy="false" aria-busy={false}>
    <h3 class="flex items-center gap-2 text-sm font-semibold">
        <Clock3 size={16} aria-hidden="true" class="shrink-0" />
        {$t('tools.metrics.title', {default: 'Backend timings'})}
    </h3>
    <p class="mt-2 text-xs text-lf-muted">
        {$t('tools.metrics.description', {
            default: 'Measured by the backend, excluding network time. Phases can overlap; parallel items are not added to obtain the request duration.',
        })}
    </p>

    <dl class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div class="min-w-0 rounded-lg bg-lf-panel p-3">
            <dt class="text-xs text-lf-muted">
                {$t('tools.metrics.serverProcessing', {default: 'Request · server processing'})}
            </dt>
            <dd class="mt-1 break-words text-sm font-semibold tabular-nums" data-testid="tool-metrics-server_processing_ms">
                {duration(batch?.server_processing_ms ?? null)}
            </dd>
        </div>
        <div class="min-w-0 rounded-lg bg-lf-panel p-3">
            <dt class="text-xs text-lf-muted">
                {$t('tools.metrics.itemTotal', {default: 'Item · total'})}
            </dt>
            <dd class="mt-1 break-words text-sm font-semibold tabular-nums" data-testid="tool-metrics-total_ms">
                {duration(item.total_ms)}
            </dd>
        </div>
    </dl>

    <dl class="mt-4 grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
        {#each phases as phase (phase.key)}
            <div class="min-w-0">
                <dt class="text-xs text-lf-muted">
                    {$t(phase.label, {default: phase.fallback})}
                </dt>
                <dd class="mt-1 break-words text-sm tabular-nums" data-testid={`tool-metrics-${phase.key}`}>
                    {duration(item[phase.key])}
                </dd>
            </div>
        {/each}
    </dl>

    <details class="mt-4 border-t border-lf-subtle pt-3" data-testid="tool-metrics-details">
        <summary class="cursor-pointer rounded text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-lf-focus" data-testid="tool-metrics-details-toggle">
            {$t('common.detail')}
        </summary>
        <dl class="mt-3 grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
            {#each validationPhases as phase (phase.key)}
                <div class="min-w-0">
                    <dt class="text-xs text-lf-muted">
                        {$t(phase.label, {default: phase.fallback})}
                    </dt>
                    <dd class="mt-1 break-words text-sm tabular-nums" data-testid={`tool-metrics-${phase.key}`}>
                        {duration(item[phase.key])}
                    </dd>
                </div>
            {/each}
        </dl>
    </details>
</section>
