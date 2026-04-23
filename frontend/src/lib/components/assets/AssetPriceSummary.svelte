<!--
  AssetPriceSummary.svelte — Price + delta + currency selector.

  Post-Blocco I cleanup: removed 3 redundant inline warnings that duplicated the
  full-width `requiredFxPairs` banners already present in `+page.svelte`:
  - `fxConversionMissing` tooltip + "Add pair" button (was banner #5)
  - `onsyncfx` / `fxSyncing` button (was banner #6)
  - `currency_breakdown` intra-series mismatch banner (was banner #7)

  Kept:
  - `livePriceConversionFailed` (banner #4 - semantically distinct: "FX rate missing
    TODAY" vs the generic "no-data" range coverage in banner #3).
  - Currency selector via `CurrencySearchSelect`.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {goto} from '$app/navigation';
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
        /** Current responsive layout mode */
        layoutMode: LayoutMode;
        /**
         * True when live price FX conversion failed (pair exists but rate unavailable
         * for today specifically). Surfaced as a small warning icon + tooltip next
         * to the price, not as a full-width banner - the full-width banner (#3
         * `no-data`) in `+page.svelte` handles the range-level "no rates" case.
         */
        livePriceConversionFailed?: boolean;
        /**
         * Optional URL to the FX pair detail page.
         * Parent should pass it only when the FX pair is **healthy** (configured + has
         * data for the current range) — otherwise the full-width FX banner already
         * surfaces the issue and we want to avoid a dead/incoherent CTA here.
         * When undefined/empty → icon is hidden.
         */
        fxPairUrl?: string;
    }

    let {lastPrice, deltaPercent, deltaAbs, displayCurrency = $bindable(), assetCurrency, layoutMode, livePriceConversionFailed = false, fxPairUrl}: Props = $props();
</script>

<div class="flex flex-wrap {layoutMode === 'wide' ? 'flex-row items-center gap-4 px-3' : 'flex-col items-center gap-2'}">
    {#if lastPrice !== null}
        <div class="flex items-center gap-2 {layoutMode === 'wide' ? '' : 'justify-center w-full'}">
            <div class="flex items-center gap-1.5">
                <span class="font-mono text-lg font-semibold text-gray-700 dark:text-gray-200">
                    {lastPrice.toFixed(2)}
                </span>
                <span class="text-xs text-gray-400 dark:text-gray-500">{livePriceConversionFailed ? assetCurrency : displayCurrency}</span>
                {#if livePriceConversionFailed}
                    <Tooltip text={$t('assetDetail.livePriceConversionFailed', {values: {currency: assetCurrency}})} position="bottom">
                        <span class="text-amber-500 dark:text-amber-400">
                            <AlertTriangle size={13} />
                        </span>
                    </Tooltip>
                {/if}
                {#if deltaAbs !== null}
                    <span class="text-xs text-gray-400 dark:text-gray-500">
                        ({deltaAbs >= 0 ? '+' : ''}{deltaAbs.toFixed(2)})
                    </span>
                {/if}
            </div>

            {#if deltaPercent !== null}
                <span class="flex items-center gap-0.5 text-xs font-medium {deltaPercent >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                    {#if deltaPercent >= 0}<TrendingUp size={12} />{:else}<TrendingDown size={12} />{/if}
                    {deltaPercent >= 0 ? '+' : ''}{deltaPercent.toFixed(2)}%
                </span>
            {/if}
        </div>
    {/if}

    <div class="flex items-center gap-2">
        <span class="text-[10px] uppercase font-semibold text-gray-400 dark:text-gray-500 tracking-wider">
            {$t('assetDetail.displayCurrency')}
        </span>
        <div class="w-28 sm:w-32">
            <CurrencySearchSelect bind:value={displayCurrency} compact={true} originalCurrency={assetCurrency} placeholder={$t('assetDetail.displayCurrency')} />
        </div>
        {#if fxPairUrl}
            <!--
              Quick link to FX pair detail (only shown when displayCurrency≠assetCurrency AND pair is healthy).
              NOTE: we intentionally use a <button onclick={goto(...)}> instead of an <a href> here, because
              this element is wrapped inside <Tooltip> whose internal handlers call stopPropagation/preventDefault
              on click; a native <a> ends up triggering a full-page reload (breaking SPA navigation and resetting
              the navigationStore stack, which in turn breaks goBack() on the destination page). The signal cards
              on the dashboard use the same pattern.
            -->
            <Tooltip text={$t('assetDetail.openFxPair')} position="bottom">
                <button
                    type="button"
                    onclick={() => {
                        if (fxPairUrl) goto(fxPairUrl);
                    }}
                    class="inline-flex items-center justify-center p-1.5 rounded-lg text-gray-400 dark:text-gray-500 hover:text-libre-green hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors cursor-pointer"
                    data-testid="asset-detail-fx-pair-link"
                    aria-label={$t('assetDetail.openFxPair')}
                >
                    <Coins size={14} />
                </button>
            </Tooltip>
        {/if}
    </div>
</div>
