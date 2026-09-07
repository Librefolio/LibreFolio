<script lang="ts">
    import type {Snippet} from 'svelte';
    import {AlertTriangle, ChevronDown, RefreshCw} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import {riskMetadata, singleValue} from '$lib/risk/riskTypes';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

    interface Props {
        title: string;
        description?: string;
        result?: RiskAnalyticResult | null;
        loading?: boolean;
        refreshing?: boolean;
        testId: string;
        children?: Snippet;
    }

    let {title, description = '', result = null, loading = false, refreshing = false, testId, children}: Props = $props();

    let metadata = $derived(riskMetadata(result));
    let errorCode = $derived(singleValue(result?.error)?.code ?? null);
    let canRender = $derived(Boolean(result && (result.status === 'ok' || result.status === 'partial') && result.output));

    function translatedCode(prefix: 'errors' | 'warnings', code: string | null | undefined, fallbackKey: string): string {
        if (!code) return $t(fallbackKey);
        const key = `risk.${prefix}.${code}`;
        const translated = $t(key);
        return translated === key ? $t(fallbackKey) : translated;
    }

    function percent(value: number | null | undefined): string {
        return value == null ? '—' : `${(value * 100).toFixed(1)}%`;
    }

    function fixed(value: number | readonly (number | null)[] | null | undefined): string {
        const scalar = singleValue(value);
        return scalar == null ? '—' : scalar.toFixed(2);
    }
</script>

<section class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4" data-testid={testId}>
    <div class="flex items-start justify-between gap-3">
        <div>
            <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{title}</h3>
            {#if description}
                <p class="mt-0.5 text-xs text-gray-400 dark:text-gray-500">{description}</p>
            {/if}
        </div>
        {#if refreshing}
            <RefreshCw size={14} class="animate-spin text-libre-green shrink-0" data-testid="{testId}-refreshing" />
        {:else if result?.status === 'partial'}
            <span class="rounded-full bg-amber-100 dark:bg-amber-900/30 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-300" data-testid="{testId}-partial">
                {$t('risk.states.partial')}
            </span>
        {/if}
    </div>

    {#if loading && !result}
        <div class="mt-4 space-y-2" data-testid="{testId}-loading">
            <div class="h-8 rounded bg-gray-100 dark:bg-slate-700 animate-pulse"></div>
            <div class="h-8 rounded bg-gray-100 dark:bg-slate-700 animate-pulse"></div>
        </div>
    {:else if !result}
        <p class="mt-4 text-sm text-gray-400 dark:text-gray-500" data-testid="{testId}-empty">{$t('risk.states.empty')}</p>
    {:else if result.status === 'unavailable' || result.status === 'failed'}
        <div class="mt-4 flex items-start gap-2 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-3 text-sm text-amber-700 dark:text-amber-300" data-testid="{testId}-{result.status}">
            <AlertTriangle size={16} class="mt-0.5 shrink-0" />
            <span>{translatedCode('errors', errorCode, result.status === 'unavailable' ? 'risk.states.unavailable' : 'risk.states.failed')}</span>
        </div>
    {:else if canRender}
        <div class:opacity-60={refreshing} class="transition-opacity">
            {@render children?.()}
        </div>
    {/if}

    {#if result?.warnings?.length}
        <div class="mt-3 space-y-1" data-testid="{testId}-warnings">
            {#each result.warnings as warning}
                <p class="text-xs text-amber-600 dark:text-amber-400">
                    {translatedCode('warnings', warning.code, 'risk.states.warning')}
                </p>
            {/each}
        </div>
    {/if}

    {#if metadata}
        <details class="mt-3 border-t border-gray-100 dark:border-slate-700 pt-2 text-xs text-gray-500 dark:text-gray-400" data-testid="{testId}-metadata">
            <summary class="flex cursor-pointer list-none items-center gap-1 font-medium">
                <ChevronDown size={13} />
                {$t('risk.metadata.title')}
            </summary>
            <dl class="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
                <div>
                    <dt>{$t('risk.metadata.observations')}</dt>
                    <dd class="font-mono text-gray-700 dark:text-gray-200">{metadata.n_observations}</dd>
                </div>
                <div>
                    <dt>{$t('risk.metadata.coverage')}</dt>
                    <dd class="font-mono text-gray-700 dark:text-gray-200">{percent(metadata.coverage)}</dd>
                </div>
                <div>
                    <dt>{$t('risk.metadata.annualization')}</dt>
                    <dd class="font-mono text-gray-700 dark:text-gray-200">{fixed(metadata.annualization_factor)}</dd>
                </div>
                <div>
                    <dt>{$t('risk.metadata.returnBasis')}</dt>
                    <dd class="font-mono text-gray-700 dark:text-gray-200">{$t(`risk.returnBasis.${metadata.return_basis}`)}</dd>
                </div>
                {#if singleValue(metadata.method)}
                    <div class="col-span-2 sm:col-span-4">
                        <dt>{$t('risk.metadata.method')}</dt>
                        <dd class="break-all font-mono text-gray-700 dark:text-gray-200">{singleValue(metadata.method)}</dd>
                    </div>
                {/if}
            </dl>
        </details>
    {/if}
</section>
