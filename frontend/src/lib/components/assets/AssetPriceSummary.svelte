<!--
  AssetPriceSummary.svelte — Combined price summary + currency selector + FX warning.

  Groups:
  - Delta % (left) | Price + Delta$ (right)
  - Currency selector + FX warning/link

  When layout stacks, the block centers relative to the parent (date filter).
  Used only in asset detail page.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {TrendingUp, TrendingDown, AlertTriangle, Coins} from 'lucide-svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import type {LayoutMode} from '$lib/utils/responsiveLayout.svelte';

    interface Props {
        /** Last (closing) price */
        lastPrice: number | null;
        /** Period delta in percent */
        deltaPercent: number | null;
        /** Period delta in absolute value */
        deltaAbs: number | null;
        /** Currently selected display currency (bindable) */
        displayCurrency: string;
        /** Asset's native currency */
        assetCurrency: string;
        /** True when required FX pair is not configured */
        fxConversionMissing: boolean;
        /** Canonical slug for the FX pair link */
        fxPairSlug: string;
        /** Current responsive layout mode */
        layoutMode: LayoutMode;
        /** Callback to open FX pair add modal */
        onAddFxPair?: () => void;
    }

    let {
        lastPrice,
        deltaPercent,
        deltaAbs,
        displayCurrency = $bindable(),
        assetCurrency,
        fxConversionMissing,
        fxPairSlug,
        layoutMode,
        onAddFxPair,
    }: Props = $props();

    let showFxPairLink = $derived(
        displayCurrency && assetCurrency && displayCurrency !== assetCurrency && fxPairSlug && !fxConversionMissing
    );
</script>

<div class="flex {layoutMode === 'wide' ? 'flex-row items-center gap-4 px-3 border-l border-gray-200 dark:border-slate-600' : 'flex-col items-center gap-2'}">
    <!-- Price row: [Δ%  |  Price (Δ$)] -->
    {#if lastPrice !== null}
        <div class="flex items-center gap-3 {layoutMode === 'wide' ? '' : 'justify-center w-full'}">
            <!-- Left half: delta % -->
            {#if deltaPercent !== null}
                <span class="flex items-center gap-0.5 text-xs font-medium {deltaPercent >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                    {#if deltaPercent >= 0}<TrendingUp size={12}/>{:else}<TrendingDown size={12}/>{/if}
                    {deltaPercent >= 0 ? '+' : ''}{deltaPercent.toFixed(2)}%
                </span>
            {/if}

            <!-- Right half: price + delta abs -->
            <div class="flex items-center gap-1.5">
                <span class="font-mono text-lg font-semibold text-gray-700 dark:text-gray-200">
                    {lastPrice.toFixed(2)}
                </span>
                <span class="text-xs text-gray-400 dark:text-gray-500">{displayCurrency}</span>
                {#if deltaAbs !== null}
                    <span class="text-xs text-gray-400 dark:text-gray-500">
                        ({deltaAbs >= 0 ? '+' : ''}{deltaAbs.toFixed(2)})
                    </span>
                {/if}
            </div>
        </div>
    {/if}

    <!-- Currency selector row -->
    <div class="flex items-center gap-2">
        <span class="text-[10px] uppercase font-semibold text-gray-400 dark:text-gray-500 tracking-wider">
            {$t('assetDetail.displayCurrency')}
        </span>
        <div class="w-28 sm:w-32">
            <CurrencySearchSelect
                    bind:value={displayCurrency}
                    compact={true}
                    placeholder={$t('assetDetail.displayCurrency')}
            />
        </div>

        <!-- FX warning or link -->
        {#if fxConversionMissing}
            <Tooltip text={$t('assetDetail.fxPairMissing', {values: {base: assetCurrency, quote: displayCurrency}})} position="bottom">
                <span class="p-1 text-amber-500 dark:text-amber-400">
                    <AlertTriangle size={16}/>
                </span>
            </Tooltip>
            {#if onAddFxPair}
                <button
                    class="p-1 rounded text-amber-500 dark:text-amber-400 hover:text-amber-600 dark:hover:text-amber-300 cursor-pointer transition-colors"
                    onclick={onAddFxPair}
                    title={$t('assetDetail.addFxPair')}
                >
                    <Coins size={14}/>
                </button>
            {/if}
        {:else if showFxPairLink}
            <a
                href="/fx/{fxPairSlug}"
                class="p-1 rounded text-gray-400 dark:text-gray-500 hover:text-libre-green dark:hover:text-emerald-400 transition-colors"
                title={$t('assetDetail.goToFxPair')}
            >
                <Coins size={14}/>
            </a>
        {/if}
    </div>
</div>

