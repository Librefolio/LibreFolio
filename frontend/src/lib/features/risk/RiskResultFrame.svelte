<script lang="ts">
    import type {Snippet} from 'svelte';
    import {AlertTriangle, ChevronDown, RefreshCw} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import {riskMetadata, singleValue} from '$lib/features/risk/riskTypes';
    import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';

    import {errorDisplayCode, warningSentence, type RiskResultWarning} from './levels/levelHelpers';
    import {formatFixed} from '$lib/utils/core/formatFixed';
    import {formatPercent} from '$lib/utils/core/formatPercent';

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
    // A size limit is worded by the remedy it names, like the levels' errors (D379).
    let errorCode = $derived(errorDisplayCode(singleValue(result?.error)));
    let canRender = $derived(Boolean(result && (result.status === 'ok' || result.status === 'partial') && result.output));

    function translatedCode(prefix: 'errors', code: string | null | undefined, fallbackKey: string): string {
        if (!code) return $t(fallbackKey);
        const key = `risk.${prefix}.${code}`;
        const translated = $t(key);
        return translated === key ? $t(fallbackKey) : translated;
    }

    // A warning is read through the key and the values the backend sends, never
    // through a key built from its code: a code-named key with ICU arguments,
    // looked up without values, shows its braces on screen.
    function warningText(warning: RiskResultWarning): string {
        return warningSentence(warning, $t) || $t('risk.states.warning');
    }

    function percent(value: number | null | undefined): string {
        return value == null ? '—' : formatPercent(value, {scale: 100, signed: false, digits: 1});
    }

    function fixed(value: number | readonly (number | null)[] | null | undefined): string {
        const scalar = singleValue(value);
        return scalar == null ? '—' : formatFixed(scalar, 2);
    }
</script>

<section class="bg-lf-card rounded-xl border border-lf-subtle shadow-sm p-4" data-testid={testId}>
    <div class="flex items-start justify-between gap-3">
        <div>
            <h3 class="text-sm font-semibold text-lf-secondary">{title}</h3>
            {#if description}
                <p class="mt-0.5 text-xs text-lf-muted">{description}</p>
            {/if}
        </div>
        {#if refreshing}
            <RefreshCw size={14} class="animate-spin text-lf-link shrink-0" data-testid="{testId}-refreshing" />
        {:else if result?.status === 'partial'}
            <span class="rounded-full bg-lf-warning-soft px-2 py-0.5 text-[10px] font-medium text-lf-warning-on-soft" data-testid="{testId}-partial">
                {$t('risk.states.partial')}
            </span>
        {/if}
    </div>

    {#if loading && !result}
        <div class="mt-4 space-y-2" data-testid="{testId}-loading">
            <div class="h-8 rounded bg-lf-panel animate-pulse"></div>
            <div class="h-8 rounded bg-lf-panel animate-pulse"></div>
        </div>
    {:else if !result}
        <p class="mt-4 text-sm text-lf-muted" data-testid="{testId}-empty">{$t('risk.states.empty')}</p>
    {:else if result.status === 'unavailable' || result.status === 'failed'}
        <div class="mt-4 flex items-start gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="{testId}-{result.status}">
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
                <p class="text-xs text-lf-warning">
                    {warningText(warning)}
                </p>
            {/each}
        </div>
    {/if}

    {#if metadata}
        <details class="mt-3 border-t border-lf-subtle pt-2 text-xs text-lf-muted" data-testid="{testId}-metadata">
            <summary class="flex cursor-pointer list-none items-center gap-1 font-medium">
                <ChevronDown size={13} />
                {$t('risk.metadata.title')}
            </summary>
            <dl class="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
                <div>
                    <dt>{$t('risk.metadata.observations')}</dt>
                    <dd class="font-mono text-lf-secondary">{metadata.n_observations}</dd>
                </div>
                <div>
                    <dt>{$t('risk.metadata.coverage')}</dt>
                    <dd class="font-mono text-lf-secondary">{percent(metadata.coverage)}</dd>
                </div>
                <div>
                    <dt>{$t('risk.metadata.annualization')}</dt>
                    <dd class="font-mono text-lf-secondary">{fixed(metadata.annualization_factor)}</dd>
                </div>
                <div>
                    <dt>{$t('risk.metadata.returnBasis')}</dt>
                    <dd class="font-mono text-lf-secondary">{$t(`risk.returnBasis.${metadata.return_basis}`)}</dd>
                </div>
                {#if singleValue(metadata.method)}
                    <div class="col-span-2 sm:col-span-4">
                        <dt>{$t('risk.metadata.method')}</dt>
                        <dd class="break-all font-mono text-lf-secondary">{singleValue(metadata.method)}</dd>
                    </div>
                {/if}
            </dl>
        </details>
    {/if}
</section>
