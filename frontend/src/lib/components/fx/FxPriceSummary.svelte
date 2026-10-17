<!--
  FxPriceSummary.svelte — Price summary for FX detail page.

  Extends the same visual pattern as AssetPriceSummary:
  - Delta % (left) | Rate (right)

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {TrendingUp, TrendingDown} from 'lucide-svelte';
    import type {LayoutMode} from '$lib/utils/layout/responsiveLayout.svelte';
    import {_ as t} from '$lib/i18n';
    import {formatFixed} from '$lib/utils/core/formatFixed';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {SIGN_TEXT} from '$lib/theme/toneClasses';

    interface Props {
        /** Last exchange rate */
        lastRate: number | null;
        /** Period delta in percent */
        deltaPercent: number | null;
        /** Current responsive layout mode */
        layoutMode: LayoutMode;
        /** True when the Filters+Summary zone is stacked below the DateRangePicker
         *  (stackFilters/oneColumn) — drives "giustificata" alignment (start-aligned, never
         *  centered) instead of the beside-the-picker centered look used at oneRow/denseRow. */
        filtersStacked: boolean;
        /** Mirrors the DateRangePicker's own effective max-width (see PageToolbar's
         *  `effectiveMaxWidth`/`pickerMaxWidth` pattern) — applied as this component's own
         *  max-width when `filtersStacked`, so it lines up pixel-perfect with the picker above
         *  it instead of stretching to the wider outer column. */
        maxWidth?: number;
    }

    let {lastRate, deltaPercent, layoutMode, filtersStacked, maxWidth}: Props = $props();
</script>

{#if lastRate !== null}
    <div class="flex items-center gap-3 {layoutMode === 'oneRow' ? 'px-3' : filtersStacked ? 'justify-around w-full' : 'justify-center'}" style={filtersStacked && maxWidth ? `max-width: ${maxWidth}px` : ''}>
        <!-- Left half: rate -->
        <span class="font-mono text-lg font-semibold text-lf-secondary">
            {formatFixed(lastRate, 4)}
        </span>

        <!-- Right half: the backend's Δ over the range (X-R59) -->
        {#if deltaPercent !== null}
            <span class="flex items-center gap-0.5 text-xs font-medium {deltaPercent >= 0 ? SIGN_TEXT.market.gain : SIGN_TEXT.market.loss}" data-testid="fx-price-summary-range-delta">
                {#if deltaPercent >= 0}<TrendingUp size={12} />{:else}<TrendingDown size={12} />{/if}
                {formatPercent(deltaPercent)}
            </span>
        {/if}
    </div>
{:else}
    <div class="text-sm text-lf-muted" data-fx-rate-state="missing" data-testid="fx-price-summary-missing">{$t('fx.rateNotAvailable')}</div>
{/if}
