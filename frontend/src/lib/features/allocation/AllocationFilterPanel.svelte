<!--
  AllocationFilterPanel — the three foldable panels of the «Allocazione» filters, and the link that removes them (lane 80, F2):

  - **Classes**: the classes the scope holds, each a switch with its amount; the count at the right says how many are on.
  - **Outside the 100 %**: the buckets the dimension has (`applicable_buckets`, the backend's: the panel never copies that
    rule), each a switch that takes it out of the base. Hidden when the dimension has none.
  - **Included assets**: the assets of the classes switched on, each a switch (off = excluded whole); a search box above 10.

  Controlled: it shows `filters` and calls `onchange(next)`; the page remembers them and asks again. Amounts are personal
  money (masked by the privacy toggle). A saved choice that the scope does not hold today is kept untouched.

  One instance is mounted per page (a column on a wide screen, the popover of the «Filters» button on a narrow one), so its
  test ids exist once: `{testId}-class-{CLASS}`, `-bucket-{Unknown|Other}`, `-asset-{id}`, `-assets-search`, `-clear`, and the
  panels `-classes`, `-excluded`, `-assets` (each `-toggle`, `-count`).
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import FoldPanel from '$lib/components/ui/display/FoldPanel.svelte';
    import Switch from '$lib/components/ui/input/Switch.svelte';
    import CurrencyAmount from '$lib/components/ui/display/CurrencyAmount.svelte';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {hasFilters, isClassOn, setAssetExcluded, setBucketExcluded, setClass, type AllocationFilters, type ExcludableBucket} from './allocationFilters';
    import type {AllocationResponse} from './allocationQuery';
    import {bucketHint, bucketLabel, classHint, classLabel, COMPACT_MONEY, type Translate} from './allocationLabels';

    interface Props {
        view: AllocationResponse;
        filters: AllocationFilters;
        onchange: (next: AllocationFilters) => void;
        testId: string;
    }

    let {view, filters, onchange, testId}: Props = $props();

    /** Above this many rows the assets panel gets a search box. */
    const SEARCH_ABOVE = 10;

    const t = (key: string, options?: Parameters<Translate>[1]) => $_(key, options as never);
    /** Every amount here is personal money: masked with the privacy toggle (`CurrencyAmount` follows it both ways). */
    const PERSONAL = {sensitivity: 'personal'} as const;

    const presentClasses = $derived(view.classes.map((row) => row.asset_class));
    const classesOn = $derived(view.classes.filter((row) => isClassOn(filters, row.asset_class)).length);
    const buckets = $derived(view.applicable_buckets as ExcludableBucket[]);
    const bucketsOut = $derived(buckets.filter((bucket) => filters.excludeBuckets.includes(bucket)).length);
    /** The assets of the classes switched on: the others are not in the selection, so there is nothing to include or exclude. */
    const listedAssets = $derived(view.assets.filter((asset) => isClassOn(filters, asset.asset_class)));
    const assetsIncluded = $derived(listedAssets.filter((asset) => !filters.excludeAssetIds.includes(asset.asset_id)).length);

    let search = $state('');
    const shownAssets = $derived.by(() => {
        const needle = search.trim().toLowerCase();
        if (listedAssets.length <= SEARCH_ABOVE || needle === '') return listedAssets;
        return listedAssets.filter((asset) => `${asset.name} ${asset.ticker ?? ''}`.toLowerCase().includes(needle));
    });

    /** What the bucket weighs in this view, when the dimension has a slice for it (the amount of the row). */
    const bucketAmount = (bucket: ExcludableBucket): string | null => view.slices.find((slice) => slice.key === bucket)?.amount ?? view.excluded.by_bucket.find((row) => row.key === bucket)?.amount ?? null;

    const row = 'flex items-center justify-between gap-3 py-1.5';
</script>

<div class="space-y-3 {COMPACT_MONEY}" data-testid={testId}>
    <FoldPanel title={$_('allocation.filters.classes')} count={$_('allocation.filters.countOf', {values: {on: classesOn, total: presentClasses.length}})} testId="{testId}-classes" open={true}>
        <ul class="divide-y divide-lf-subtle">
            {#each view.classes as item (item.asset_class)}
                {@const on = isClassOn(filters, item.asset_class)}
                {@const hint = classHint(t, item.asset_class)}
                <li class={row} data-testid="{testId}-class-{item.asset_class}" data-on={on ? 'true' : 'false'}>
                    <span class="flex min-w-0 items-center gap-2">
                        <img src={getAssetTypeIconUrl(item.asset_class)} alt="" class="h-4 w-4 shrink-0 object-contain" />
                        <span class="min-w-0">
                            <span class="block text-sm text-lf-primary"
                                >{classLabel(t, item.asset_class)}{#if hint}<span class="ml-1 text-lf-muted">({hint})</span>{/if}</span
                            >
                            <span class="block text-xs text-lf-muted"><CurrencyAmount amount={parseFloat(item.amount)} code={view.currency} options={PERSONAL} /></span>
                        </span>
                    </span>
                    <Switch checked={on} label={classLabel(t, item.asset_class)} testId="{testId}-class-{item.asset_class}-switch" onchange={(next) => onchange(setClass(filters, item.asset_class, next, presentClasses))} />
                </li>
            {/each}
        </ul>
    </FoldPanel>

    {#if buckets.length > 0}
        <FoldPanel title={$_('allocation.filters.excluded')} count={$_('allocation.filters.countActive', {values: {n: bucketsOut}})} testId="{testId}-excluded" open={true}>
            <ul class="divide-y divide-lf-subtle">
                {#each buckets as bucket (bucket)}
                    {@const amount = bucketAmount(bucket)}
                    {@const out = filters.excludeBuckets.includes(bucket)}
                    <li class={row} data-testid="{testId}-bucket-{bucket}" data-on={out ? 'true' : 'false'}>
                        <span class="min-w-0">
                            <span class="block text-sm text-lf-primary">{bucketLabel(t, bucket)}</span>
                            <span class="block text-xs text-lf-muted">
                                {#if amount !== null}<CurrencyAmount amount={parseFloat(amount)} code={view.currency} options={PERSONAL} />{:else}{bucketHint(t, bucket)}{/if}
                            </span>
                        </span>
                        <Switch checked={out} label={bucketLabel(t, bucket)} testId="{testId}-bucket-{bucket}-switch" onchange={(next) => onchange(setBucketExcluded(filters, bucket, next))} />
                    </li>
                {/each}
            </ul>
        </FoldPanel>
    {/if}

    <FoldPanel title={$_('allocation.filters.assets')} count={$_('allocation.filters.countOf', {values: {on: assetsIncluded, total: listedAssets.length}})} testId="{testId}-assets">
        {#if listedAssets.length > SEARCH_ABOVE}
            <input
                type="search"
                class="mb-2 w-full rounded-lg border border-lf-input bg-lf-field px-2.5 py-1.5 text-sm text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:ring-1 focus:ring-lf-focus"
                placeholder={$_('allocation.filters.searchAssets')}
                aria-label={$_('allocation.filters.searchAssets')}
                bind:value={search}
                data-testid="{testId}-assets-search"
            />
        {/if}
        {#if listedAssets.length === 0}
            <p class="text-sm italic text-lf-muted">{$_('allocation.filters.noAssets')}</p>
        {:else if shownAssets.length === 0}
            <p class="text-sm italic text-lf-muted" data-testid="{testId}-assets-nomatch">{$_('allocation.filters.noMatch')}</p>
        {:else}
            <ul class="max-h-72 divide-y divide-lf-subtle overflow-y-auto">
                {#each shownAssets as asset (asset.asset_id)}
                    {@const included = !filters.excludeAssetIds.includes(asset.asset_id)}
                    <li class={row} data-testid="{testId}-asset-{asset.asset_id}" data-on={included ? 'true' : 'false'}>
                        <span class="flex min-w-0 items-center gap-2">
                            <img src={asset.icon_url || getAssetTypeIconUrl(asset.asset_type)} alt="" class="h-4 w-4 shrink-0 object-contain" />
                            <span class="min-w-0">
                                <span class="block truncate text-sm text-lf-primary"
                                    >{asset.name}{#if asset.ticker}<span class="text-lf-muted"> · {asset.ticker}</span>{/if}</span
                                >
                                <span class="block text-xs text-lf-muted"><CurrencyAmount amount={parseFloat(asset.amount)} code={view.currency} options={PERSONAL} /></span>
                            </span>
                        </span>
                        <Switch checked={included} label={asset.name} testId="{testId}-asset-{asset.asset_id}-switch" onchange={(next) => onchange(setAssetExcluded(filters, asset.asset_id, !next))} />
                    </li>
                {/each}
            </ul>
        {/if}
    </FoldPanel>

    <div class="flex items-center justify-between gap-3 px-1 text-xs">
        {#if hasFilters(filters)}
            <button type="button" class="text-lf-link underline hover:no-underline" onclick={() => onchange({classes: null, excludeBuckets: [], excludeAssetIds: []})} data-testid="{testId}-clear">{$_('allocation.filters.clear')}</button>
        {:else}
            <span></span>
        {/if}
        <span class="text-lf-muted">{$_('allocation.filters.remembered')}</span>
    </div>
</div>
