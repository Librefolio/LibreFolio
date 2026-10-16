<!--
  AssetChartModeToggle — the two primary modes of the asset chart: prices, and the rolling return of the
  calendar view. Svelte 5 runes.
-->
<script module lang="ts">
    export type AssetChartPrimaryMode = 'price' | 'calendar-return';
</script>

<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ChartLine, Percent} from 'lucide-svelte';

    interface Props {
        primaryMode: AssetChartPrimaryMode;
        onselect: (mode: AssetChartPrimaryMode) => void;
    }

    let {primaryMode, onselect}: Props = $props();
</script>

<div class="flex rounded-lg overflow-hidden border border-lf-subtle text-xs font-medium">
    <button
        class="inline-flex items-center gap-1.5 px-3 py-1 transition-colors {primaryMode === 'price' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
        data-testid="asset-chart-primary-price"
        aria-pressed={primaryMode === 'price'}
        onclick={() => onselect('price')}
    >
        <ChartLine size={14} data-testid="asset-chart-primary-price-icon" />
        {$t('assetDetail.pricesTab')}
    </button>
    <button
        class="inline-flex items-center gap-1.5 px-3 py-1 border-l border-lf-subtle transition-colors disabled:opacity-40 disabled:cursor-not-allowed {primaryMode === 'calendar-return' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
        data-testid="asset-chart-primary-calendar-return"
        aria-pressed={primaryMode === 'calendar-return'}
        onclick={() => onselect('calendar-return')}
    >
        <Percent size={14} data-testid="asset-chart-primary-calendar-return-icon" />
        {$t('signals.riskRollingReturn.name')}
    </button>
</div>
