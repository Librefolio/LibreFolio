<!--
  AllocationResults — what the base looks like (lane 80, F3): the dimension selector, Now / History, the chart and the table.

  - **Area**: the world map (`GeographyMap`) coloured on the selection, with the line that says what the colours mean.
  - **Sector, Type, Asset**: the pie (`AllocationPieChart`) with the base in its middle.
  - **History**: the selection's history in steps (`AllocationHistoryChart`), from the same answer asked with `include_history`.
  - The table under it (`AllocationTable`): the slices, what they hold, what is excluded.

  The chart and the table follow the dimension of the ANSWER on screen (`view.dimension`), the selector the one asked: while the next
  answer is on its way they differ for a moment, and the old slices are never drawn under the new name.

  Everything is the backend's. Amounts are personal money (masked with the privacy toggle, percentages stay), the one in the middle
  of the pie included; the history chart masks its own.

  Test ids: `{testId}` (root: `data-dimension`, `data-view`), `-chart` (the pie or the map), `-center` (the base in the pie's
  middle), `-no-shares`, `-negative-cash`, `-map-caption`, `-history` (the history chart), `-history-empty`, `-dimension` and `-view-now` / `-view-history`.
-->
<script lang="ts">
    import {AreaChart, PieChart} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import AllocationPieChart from '$lib/components/charts/AllocationPieChart.svelte';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import AllocationHistoryChart from '$lib/features/dashboard/AllocationHistoryChart.svelte';
    import CurrencyAmount from '$lib/components/ui/display/CurrencyAmount.svelte';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import AllocationDimensionSelect from './AllocationDimensionSelect.svelte';
    import AllocationMatrix from './AllocationMatrix.svelte';
    import AllocationTable from './AllocationTable.svelte';
    import type {AllocationFilters} from './allocationFilters';
    import type {AllocationDimension, AllocationResponse} from './allocationQuery';
    import {colorRanksOf, geoData, pieEntries} from './allocationView';
    import {COMPACT_MONEY} from './allocationLabels';

    interface Props {
        view: AllocationResponse;
        dimension: AllocationDimension;
        onDimension: (next: AllocationDimension) => void;
        mode: 'now' | 'history';
        onMode: (next: 'now' | 'history') => void;
        /** A request is on its way (the history is on its way). */
        loading: boolean;
        /** The user's choices, for the matrix (it frames what they keep and a click on it changes them). */
        filters: AllocationFilters;
        onFilters: (next: AllocationFilters) => void;
        testId: string;
    }

    let {view, dimension, onDimension, mode, onMode, loading, filters, onFilters, testId}: Props = $props();

    const PERSONAL = {sensitivity: 'personal', minFraction: 0, maxFraction: 0} as const;

    const geo = $derived(geoData(view));
    const entries = $derived(pieEntries(view));
    const ranks = $derived(colorRanksOf(view));
    const share = $derived(view.base_share_of_portfolio == null ? '' : formatPercent(parseFloat(view.base_share_of_portfolio), {digits: 0, signed: false}));
    /** The history chart reads `geo` where the answer says `geography`. */
    const historyDimension = $derived(view.dimension === 'geography' ? 'geo' : view.dimension);
    /** The pie's middle: 50 % in the asset pie (no legend), 40 % where the legend goes below. */
    const centerTop = $derived(view.dimension === 'asset' ? '50%' : '40%');
    const pieMode = $derived(view.dimension === 'geography' ? 'sector' : view.dimension);
    const historyReady = $derived(view.history !== null && view.dimension === dimension);
    const historyEmpty = $derived(historyReady && (view.history?.length ?? 0) === 0);

    /** The slices add up to zero or less: every share is `null` and the pie would draw equal slices of nothing (MF-C2). */
    const noShares = $derived(view.slices.length > 0 && view.slices.every((slice) => slice.share_of_selection == null));
    /** The cash below zero: an overdraft the pie cannot draw (decision 49). The amount stays in the table. */
    const negativeCash = $derived.by(() => {
        const amount = parseFloat(view.slices.find((slice) => slice.key === 'Liquidity')?.amount ?? '');
        return Number.isFinite(amount) && amount < 0 ? amount : null;
    });

    const toggle = 'px-2.5 py-1.5 transition-colors';
</script>

<div class="space-y-3" data-testid={testId} data-dimension={view.dimension} data-view={mode}>
    <div class="flex flex-wrap items-center gap-2">
        <AllocationDimensionSelect value={dimension} onchange={onDimension} testId="{testId}-dimension" />
        <div class="ml-auto flex overflow-hidden rounded-lg border border-lf-subtle text-xs font-medium" role="group" aria-label={$_('allocation.view.label')}>
            <button
                type="button"
                class="{toggle} {mode === 'now' ? 'bg-lf-action text-lf-on-action' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                aria-pressed={mode === 'now'}
                aria-label={$_('allocation.view.now')}
                title={$_('allocation.view.now')}
                onclick={() => onMode('now')}
                data-testid="{testId}-view-now"
            >
                <PieChart size={14} aria-hidden="true" />
            </button>
            <button
                type="button"
                class="{toggle} {mode === 'history' ? 'bg-lf-action text-lf-on-action' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                aria-pressed={mode === 'history'}
                aria-label={$_('allocation.view.history')}
                title={$_('allocation.view.history')}
                onclick={() => onMode('history')}
                data-testid="{testId}-view-history"
            >
                <AreaChart size={14} aria-hidden="true" />
            </button>
        </div>
    </div>

    {#if mode === 'history'}
        <div class="h-80" data-testid="{testId}-history">
            {#if historyEmpty}
                <p class="py-12 text-center text-sm italic text-lf-muted" data-testid="{testId}-history-empty">{$_('allocation.history.empty')}</p>
            {:else if !historyReady}
                <p class="py-12 text-center text-sm italic text-lf-muted" data-testid="{testId}-history-loading">{$_('allocation.history.loading')}</p>
            {:else}
                <AllocationHistoryChart data={view.history ?? []} dimension={historyDimension} colorRanks={ranks} height="100%" {loading} />
            {/if}
        </div>
    {:else if noShares}
        <p class="py-8 text-center text-sm text-lf-muted" data-testid="{testId}-no-shares">{$_('dashboard.allocationNoShares')}</p>
    {:else if view.dimension === 'geography'}
        <div data-testid="{testId}-chart">
            <GeographyMap data={geo.data} amounts={geo.amounts} currency={view.currency} height="320px" language={$currentLanguage} />
            <p class="mt-1 text-center text-sm text-lf-secondary {COMPACT_MONEY}" data-testid="{testId}-map-caption">
                {$_('allocation.map.captionBefore')}
                <CurrencyAmount amount={parseFloat(view.base)} code={view.currency} options={PERSONAL} />{#if share}, {share} {$_('allocation.map.captionAfter')}{/if}
            </p>
        </div>
    {:else}
        <div class="relative" data-testid="{testId}-chart">
            <AllocationPieChart data={entries} mode={pieMode} colorRanks={ranks} legendPosition="bottom" currency={view.currency} height="320px" />
            <div class="pointer-events-none absolute left-1/2 -translate-x-1/2 -translate-y-1/2 text-center text-lf-primary [&_.emoji-flag]:hidden [&:has(.currency-symbol)_.currency-code]:hidden" style="top: {centerTop}" data-testid="{testId}-center">
                <div class="text-xs font-semibold"><CurrencyAmount amount={parseFloat(view.base)} code={view.currency} options={PERSONAL} /></div>
            </div>
        </div>
    {/if}

    {#if mode === 'now' && negativeCash !== null}
        <p class="text-center text-xs text-lf-muted" data-testid="{testId}-negative-cash">{$_('dashboard.allocationNegativeCash', {values: {amount: formatCurrencyAmountPlain(negativeCash, view.currency)}})}</p>
    {/if}

    <AllocationTable {view} testId="{testId}-table" />

    <AllocationMatrix {view} {filters} onchange={onFilters} testId="{testId}-matrix" />
</div>
