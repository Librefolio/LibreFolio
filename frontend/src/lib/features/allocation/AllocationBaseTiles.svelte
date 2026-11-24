<!--
  AllocationBaseTiles — the three boxes over the «Allocazione» tab: the base of the 100 %, what the filter leaves out, and
  what is excluded (lane 80, F2).

  Every number is the backend's: base + outside + excluded = the net worth of the view's day. Nothing is added here, so the
  classes of «Outside the filter» are all listed, and the fixed rows of the excluded box (securities in transit, cash with
  no country) come with their reason. Amounts are personal money: masked with the privacy toggle, the percentages stay.

  On a phone the three boxes are one: the base, its bar, and a line with the other two.

  Test ids: `{testId}` (root), `-base`, `-base-amount`, `-base-share`, `-base-bar`, `-outside`, `-outside-amount`,
  `-excluded`, `-excluded-amount`, `-compact`.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import CurrencyAmount from '$lib/components/ui/display/CurrencyAmount.svelte';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import type {AllocationResponse} from './allocationQuery';
    import {bucketLabel, classLabel, COMPACT_MONEY, type Translate} from './allocationLabels';

    interface Props {
        view: AllocationResponse;
        testId: string;
    }

    let {view, testId}: Props = $props();

    const t = (key: string, options?: Parameters<Translate>[1]) => $_(key, options as never);
    /** Every amount here is personal money: masked with the privacy toggle (`CurrencyAmount` follows it both ways). */
    const PERSONAL = {sensitivity: 'personal'} as const;
    const percent = (value: string | null | undefined) => formatPercent(value == null ? null : parseFloat(value), {signed: false, digits: 1});

    const names = $derived(new Map(view.assets.map((asset) => [asset.asset_id, asset.name])));
    /** The bar is a drawing of a percentage the backend gave; a missing share draws nothing. */
    const barWidth = $derived(view.base_share_of_portfolio == null ? 0 : Math.max(0, Math.min(100, parseFloat(view.base_share_of_portfolio))));
    const hasExcludedRows = $derived(view.excluded.by_bucket.length + view.excluded.by_asset.length + view.excluded.unattributable.length > 0);
    const isZero = (value: string) => parseFloat(value) === 0;

    const card = 'rounded-xl border border-lf-subtle bg-lf-card p-4 shadow-sm shadow-lf-shadow-card';
    const label = 'text-xs font-medium uppercase tracking-wide text-lf-muted';
</script>

<div class="grid grid-cols-1 gap-3 md:grid-cols-3 {COMPACT_MONEY}" data-testid={testId}>
    <div class={card} data-testid="{testId}-base">
        <div class={label}>{$_('allocation.tiles.base')}</div>
        <div class="mt-1 text-2xl font-semibold text-lf-primary" data-testid="{testId}-base-amount"><CurrencyAmount amount={parseFloat(view.base)} code={view.currency} options={PERSONAL} /></div>
        <div class="mt-1 text-sm text-lf-secondary" data-testid="{testId}-base-share">
            {#if view.base_share_of_portfolio != null}{percent(view.base_share_of_portfolio)}{/if}
            {$_('allocation.tiles.ofPortfolio')} (<CurrencyAmount amount={parseFloat(view.portfolio_total)} code={view.currency} options={PERSONAL} />)
        </div>
        <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-lf-neutral" data-testid="{testId}-base-bar" data-share={view.base_share_of_portfolio ?? ''}>
            <div class="h-full rounded-full bg-lf-checked" style="width: {barWidth}%"></div>
        </div>
        <!-- Phone: the other two boxes in one line. -->
        <div class="mt-2 text-sm text-lf-secondary md:hidden" data-testid="{testId}-compact">
            {$_('allocation.tiles.outsideShort')}
            <CurrencyAmount amount={parseFloat(view.outside.amount)} code={view.currency} options={PERSONAL} /> · {$_('allocation.tiles.excludedShort')}
            <CurrencyAmount amount={parseFloat(view.excluded.amount)} code={view.currency} options={PERSONAL} />
        </div>
    </div>

    <div class="{card} hidden md:block" data-testid="{testId}-outside">
        <div class={label}>{$_('allocation.tiles.outside')}</div>
        <div class="mt-1 text-2xl font-semibold text-lf-primary" data-testid="{testId}-outside-amount"><CurrencyAmount amount={parseFloat(view.outside.amount)} code={view.currency} options={PERSONAL} /></div>
        <div class="mt-1 text-sm text-lf-secondary">
            {#if view.outside.by_class.length === 0}
                {$_('allocation.tiles.none')}
            {:else}
                {#each view.outside.by_class as row, index (row.asset_class)}
                    {#if index > 0}<span aria-hidden="true"> · </span>{/if}<span data-testid="{testId}-outside-class" data-class={row.asset_class}>{classLabel(t, row.asset_class)} <CurrencyAmount amount={parseFloat(row.amount)} code={view.currency} options={PERSONAL} /></span>
                {/each}
            {/if}
        </div>
    </div>

    <div class="{card} hidden md:block" data-testid="{testId}-excluded">
        <div class={label}>{$_('allocation.tiles.excluded')}</div>
        <div class="mt-1 text-2xl font-semibold text-lf-primary" data-testid="{testId}-excluded-amount"><CurrencyAmount amount={parseFloat(view.excluded.amount)} code={view.currency} options={PERSONAL} /></div>
        <div class="mt-1 space-y-0.5 text-sm text-lf-secondary">
            {#if !hasExcludedRows}
                {$_('allocation.tiles.none')}
            {/if}
            {#each view.excluded.by_bucket as row (row.key)}
                <div data-testid="{testId}-excluded-bucket" data-key={row.key}>{bucketLabel(t, row.key)} <CurrencyAmount amount={parseFloat(row.amount)} code={view.currency} options={PERSONAL} /></div>
            {/each}
            {#each view.excluded.by_asset as row (row.asset_id)}
                <div data-testid="{testId}-excluded-asset" data-asset-id={row.asset_id}>{names.get(row.asset_id) ?? `#${row.asset_id}`} <CurrencyAmount amount={parseFloat(row.amount)} code={view.currency} options={PERSONAL} /></div>
            {/each}
            {#each view.excluded.unattributable as row (row.reason)}
                {#if !isZero(row.amount)}
                    <div data-testid="{testId}-excluded-unattributable" data-reason={row.reason}>{$_(`allocation.unattributable.${row.reason}`)} <CurrencyAmount amount={parseFloat(row.amount)} code={view.currency} options={PERSONAL} /></div>
                {/if}
            {/each}
        </div>
    </div>
</div>
