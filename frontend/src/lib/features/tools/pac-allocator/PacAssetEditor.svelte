<script lang="ts">
    import {t} from '$lib/i18n';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import {currencyStoreVersion, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {getIndexColor} from '$lib/utils/colors';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {Info, Settings2, Trash2} from 'lucide-svelte';
    import type {PacEditorAsset} from './editorTypes';

    interface Props {
        asset: PacEditorAsset;
        index: number;
        disabled?: boolean;
        onremove: () => void;
        onchange: () => void;
    }

    let {asset = $bindable(), index, disabled = false, onremove, onchange}: Props = $props();
    const scopes = ['owned', 'other_users', 'observed'] as const;

    function scopeLabel(): string {
        if (asset.source?.usageScope === 'owned') return $t('tools.pacAllocator.gallery.owned', {default: 'Owned'});
        if (asset.source?.usageScope === 'other_users') return $t('tools.pacAllocator.gallery.otherUsers', {default: 'Other users'});
        return $t('tools.pacAllocator.gallery.observed', {default: 'Observed'});
    }

    function scopeStyle(): string {
        const scope = asset.source?.usageScope ?? 'observed';
        const colors = getIndexColor(scopes.indexOf(scope), 205);
        return `--scope-bg:${colors.bg};--scope-text:${colors.text};--scope-dark-bg:${colors.darkBg};--scope-dark-text:${colors.darkText};--scope-border:${colors.vivid};`;
    }

    function display(value: string | null | undefined): string {
        return formatDecimalForDisplay(value, {maxFrac: 12}) || '—';
    }

    function flag(code: string | null | undefined): string {
        void $currencyStoreVersion;
        const value = getCurrencyInfo(code ?? '').flag_emoji;
        return value === '🏳️' ? '' : value;
    }

    function setGridMode(mode: 'whole' | 'fractional'): void {
        asset.value.buy_grid.mode = mode;
        if (!asset.value.buy_grid.quantity_step) asset.value.buy_grid.quantity_step = mode === 'whole' ? '1' : '0.001';
        onchange();
    }
</script>

<article class="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid="pac-asset-editor" data-index={index} data-stale={asset.stale}>
    <header class="flex items-start gap-2.5">
        <AssetIcon iconUrl={asset.source?.iconUrl ?? null} assetType={asset.source?.assetType ?? null} altText={asset.value.name} size="md" />
        <div class="min-w-0 flex-1">
            {#if asset.source}
                <h3 class="truncate text-sm font-semibold text-gray-900 dark:text-white">{asset.value.name}</h3>
            {:else}
                <label class="block">
                    <span class="sr-only">{$t('common.name')}</span>
                    <input
                        class="min-h-9 w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm font-semibold text-gray-900 outline-none focus:border-libre-green focus:ring-1 focus:ring-libre-green dark:border-gray-600 dark:bg-gray-900 dark:text-white"
                        value={asset.value.name}
                        placeholder={$t('tools.pacAllocator.newManualAsset', {default: 'New manual Asset'})}
                        {disabled}
                        oninput={(event) => {
                            asset.value.name = event.currentTarget.value;
                            onchange();
                        }}
                        data-testid={`pac-asset-name-${index}`}
                    />
                </label>
            {/if}
            <div class="mt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
                {#if asset.source}
                    <span class="scope-badge rounded-full border px-2 py-0.5 font-medium" style={scopeStyle()}>{scopeLabel()}</span>
                    {#if asset.source.quote.rawPrice}
                        <span class="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-gray-700 dark:bg-gray-700 dark:text-gray-200" data-testid={`pac-current-price-${index}`}>
                            <strong class="font-medium">{$t('common.currentPrice')}</strong>
                            {#if flag(asset.source.quote.currency)}<span class="emoji-flag" aria-hidden="true">{flag(asset.source.quote.currency)}</span>{/if}
                            <span>{asset.source.quote.currency}</span>
                            <span class="font-mono">{display(asset.source.quote.rawPrice)}</span>
                        </span>
                    {:else}
                        <span class="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">{$t('tools.pacAllocator.missingPrice')}</span>
                    {/if}
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                        {$t('tools.allocation.asset.custodyCount', {
                            default: '{count} custody contexts',
                            values: {count: asset.source.contexts.length},
                        })}
                    </span>
                    {#if asset.stale}
                        <span class="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
                            {$t('tools.pacAllocator.staleLabel')}
                        </span>
                    {/if}
                {:else}
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 text-gray-600 dark:bg-gray-700 dark:text-gray-300">{$t('tools.pacAllocator.manual')}</span>
                {/if}
            </div>
            {#if asset.source && (asset.source.quote.source || asset.source.quote.referenceDate)}
                <p class="mt-1 text-[10px] text-gray-400 dark:text-gray-500">
                    {#if asset.source.quote.source}{$t('common.provider')}: {asset.source.quote.source}{/if}
                    {#if asset.source.quote.source && asset.source.quote.referenceDate}<span aria-hidden="true"> · </span>{/if}
                    {#if asset.source.quote.referenceDate}{$t('tools.pacAllocator.priceAt')}: {asset.source.quote.referenceDate}{/if}
                </p>
            {/if}
        </div>
        <Tooltip text={$t('common.remove')} position="top" interactiveChild>
            <button
                class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-red-600 transition hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500/70 dark:text-red-400 dark:hover:bg-red-950/30"
                type="button"
                onclick={onremove}
                {disabled}
                data-testid={`pac-remove-asset-${index}`}
                aria-label={$t('common.remove')}
            >
                <Trash2 size={15} />
            </button>
        </Tooltip>
    </header>

    <details class="mt-3 border-t border-gray-200 pt-2 dark:border-gray-700" data-testid={`pac-asset-constraints-${index}`}>
        <summary class="inline-flex cursor-pointer list-none items-center gap-1.5 text-xs font-medium text-gray-600 dark:text-gray-300">
            <Settings2 size={14} />
            {$t('tools.allocation.asset.futureConstraints', {default: 'Future purchase constraints'})}
            <Tooltip
                text={$t('tools.allocation.asset.futureConstraintsHint', {
                    default: 'Recorded for the future solver. P1 does not quantize this theoretical monetary allocation.',
                })}
                position="top"
                maxWidth="300px"
            >
                <button type="button" class="inline-flex text-gray-400" aria-label={$t('tools.allocation.asset.futureConstraintsHint', {default: 'Constraint details'})}>
                    <Info size={13} />
                </button>
            </Tooltip>
        </summary>
        <div class="mt-2 grid gap-2 sm:grid-cols-2">
            <div class="grid grid-cols-2 rounded-md border border-gray-300 bg-gray-100 p-1 dark:border-gray-600 dark:bg-gray-900" role="group">
                <button
                    class="rounded px-2 py-1 text-xs font-medium {asset.value.buy_grid.mode === 'whole' ? 'bg-white text-libre-green shadow-sm dark:bg-gray-700 dark:text-green-300' : 'text-gray-500'}"
                    type="button"
                    aria-pressed={asset.value.buy_grid.mode === 'whole'}
                    onclick={() => setGridMode('whole')}
                    {disabled}
                >
                    {$t('tools.pacAllocator.rows.whole')}
                </button>
                <button
                    class="rounded px-2 py-1 text-xs font-medium {asset.value.buy_grid.mode === 'fractional' ? 'bg-white text-libre-green shadow-sm dark:bg-gray-700 dark:text-green-300' : 'text-gray-500'}"
                    type="button"
                    aria-pressed={asset.value.buy_grid.mode === 'fractional'}
                    onclick={() => setGridMode('fractional')}
                    {disabled}
                >
                    {$t('tools.pacAllocator.rows.fractional')}
                </button>
            </div>
            <ExactDecimalInput
                value={asset.value.buy_grid.quantity_step ?? ''}
                step={asset.value.buy_grid.mode === 'whole' ? '1' : '0.001'}
                maxIntegerDigits={12}
                maxFractionDigits={asset.value.buy_grid.mode === 'whole' ? 0 : 12}
                ariaLabel={$t('tools.pacAllocator.rows.quantityStep')}
                testid={`pac-asset-quantity-step-${index}`}
                className="min-h-8 !rounded-md !px-2 !py-1 text-sm"
                {disabled}
                onchange={(value) => {
                    asset.value.buy_grid.quantity_step = value;
                    onchange();
                }}
            />
        </div>
    </details>
</article>

<style>
    .scope-badge {
        border-color: color-mix(in srgb, var(--scope-border) 45%, transparent);
        background: var(--scope-bg);
        color: var(--scope-text);
    }

    :global(.dark) .scope-badge {
        background: var(--scope-dark-bg);
        color: var(--scope-dark-text);
    }
</style>
