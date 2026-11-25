<!--
  AllocationFilterPanel — the three foldable panels of the «Allocazione» filters, and the link that removes them (lane 80, F2;
  two levels since lane 86, D-13/D-14):

  - **Classes**: the classes the scope holds, each a switch with its total; one that holds more than one asset type opens on its
    types, each a switch with its amount. A class kept in part is mixed; its switch from there turns all of it on.
  - **Unclassified**: the buckets the dimension has (`applicable_buckets`, the backend's: the panel never copies that rule), all
    on at first; one switched off leaves the base. Hidden when the dimension has none.
  - **Included assets**: the assets of the types switched on, each a switch (off = excluded whole); a search box above 10. A
    name that does not fit scrolls by itself.

  Each panel's title has a switch for everything the panel lists (mixed when only some are on); the assets' one acts on the rows
  the search shows.

  Controlled: it shows `filters` and calls `onchange(next)`; the page remembers them and asks again. Amounts are personal
  money (masked by the privacy toggle). A saved choice that the scope does not hold today is kept untouched.

  One instance is mounted per page (a column on a wide screen, the popover of the «Filters» button on a narrow one), so its
  test ids exist once: `{testId}-class-{CLASS}` (`data-state` on|off|mixed, `-toggle`, `-switch`), `-type-{TYPE}`,
  `-bucket-{Unknown|Other}`, `-asset-{id}` (`data-on`), `-assets-search`, `-clear`, and the panels `-classes`, `-excluded`,
  `-assets` (each `-toggle`, `-count`, `-all` its title's switch).
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {ChevronRight} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import FoldPanel from '$lib/components/ui/display/FoldPanel.svelte';
    import Switch from '$lib/components/ui/input/Switch.svelte';
    import CurrencyAmount from '$lib/components/ui/display/CurrencyAmount.svelte';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {choiceState, classState, emptyFilters, hasFilters, isTypeOn, setAssetExcluded, setAssetsExcluded, setBucketExcluded, setClass, setEveryClass, setType, type AllocationFilters, type ExcludableBucket} from './allocationFilters';
    import type {AllocationResponse} from './allocationQuery';
    import {bucketHint, bucketLabel, classLabel, COMPACT_MONEY, typeLabel, type Translate} from './allocationLabels';

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

    const classStates = $derived(view.classes.map((item) => classState(filters, item)));
    const classesKept = $derived(classStates.filter((state) => state !== 'off').length);
    const classesState = $derived(classStates.every((state) => state === 'on') ? 'on' : classStates.every((state) => state === 'off') ? 'off' : 'mixed');
    /** The classes whose types are listed; the ones kept in part start open, so what makes them mixed is in sight. */
    let openClasses = $state<string[]>(untrack(() => view.classes.filter((item) => classState(filters, item) === 'mixed').map((item) => item.asset_class)));
    /** Room for the chevrons only where one class opens. */
    const anyOpens = $derived(view.classes.some((item) => item.types.length > 1));
    const toggleClass = (assetClass: string) => (openClasses = openClasses.includes(assetClass) ? openClasses.filter((item) => item !== assetClass) : [...openClasses, assetClass]);

    const buckets = $derived(view.applicable_buckets as ExcludableBucket[]);
    const bucketsIn = $derived(buckets.filter((bucket) => !filters.excludeBuckets.includes(bucket)).length);
    /** The assets of the types switched on: the others are not in the selection, so there is nothing to include or exclude. */
    const listedAssets = $derived(view.assets.filter((asset) => isTypeOn(filters, asset.asset_class, asset.asset_type ?? asset.asset_class)));
    const assetsIncluded = $derived(listedAssets.filter((asset) => !filters.excludeAssetIds.includes(asset.asset_id)).length);

    let search = $state('');
    const shownAssets = $derived.by(() => {
        const needle = search.trim().toLowerCase();
        if (listedAssets.length <= SEARCH_ABOVE || needle === '') return listedAssets;
        return listedAssets.filter((asset) => `${asset.name} ${asset.ticker ?? ''}`.toLowerCase().includes(needle));
    });
    const shownState = $derived(choiceState(shownAssets.filter((asset) => !filters.excludeAssetIds.includes(asset.asset_id)).length, shownAssets.length));

    /** What the bucket weighs in this view, when the dimension has a slice for it (the amount of the row). */
    const bucketAmount = (bucket: ExcludableBucket): string | null => view.slices.find((slice) => slice.key === bucket)?.amount ?? view.excluded.by_bucket.find((row) => row.key === bucket)?.amount ?? null;

    function setEveryBucket(on: boolean): void {
        onchange(buckets.reduce((next, bucket) => setBucketExcluded(next, bucket, !on), filters));
    }

    const row = 'flex items-center justify-between gap-3 py-1.5';
</script>

<div class="space-y-3 {COMPACT_MONEY}" data-testid={testId}>
    <FoldPanel title={$_('allocation.filters.classes')} count={$_('allocation.filters.countOf', {values: {on: classesKept, total: view.classes.length}})} testId="{testId}-classes" open={true}>
        {#snippet control()}
            {#if view.classes.length > 0}
                <Switch checked={classesState === 'on'} mixed={classesState === 'mixed'} label={$_('allocation.filters.classes')} testId="{testId}-classes-all" onchange={(next) => onchange(setEveryClass(filters, next))} />
            {/if}
        {/snippet}
        <ul class="divide-y divide-lf-subtle">
            {#each view.classes as item (item.asset_class)}
                {@const state = classState(filters, item)}
                {@const many = item.types.length > 1}
                {@const open = many && openClasses.includes(item.asset_class)}
                <li data-testid="{testId}-class-{item.asset_class}" data-state={state} data-on={state === 'off' ? 'false' : 'true'}>
                    <div class={row}>
                        <svelte:element
                            this={many ? 'button' : 'span'}
                            type={many ? 'button' : undefined}
                            role={many ? 'button' : undefined}
                            class="flex min-w-0 flex-1 items-center gap-2 rounded text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus {many ? 'cursor-pointer' : ''}"
                            aria-expanded={many ? open : undefined}
                            onclick={many ? () => toggleClass(item.asset_class) : undefined}
                            data-testid={many ? `${testId}-class-${item.asset_class}-toggle` : undefined}
                        >
                            {#if anyOpens}
                                <span class="w-4 shrink-0 text-lf-secondary" aria-hidden="true">
                                    {#if many}<ChevronRight size={16} class="transition-transform {open ? 'rotate-90' : ''}" />{/if}
                                </span>
                            {/if}
                            <img src={getAssetTypeIconUrl(item.asset_class)} alt="" class="h-4 w-4 shrink-0 object-contain" />
                            <span class="min-w-0 flex-1">
                                <span class="block text-sm text-lf-primary">
                                    {classLabel(t, item.asset_class)}
                                    {#if state === 'mixed'}
                                        <span class="text-xs text-lf-muted">{$_('allocation.filters.countOf', {values: {on: item.types.filter((type) => isTypeOn(filters, item.asset_class, type.asset_type)).length, total: item.types.length}})}</span>
                                    {/if}
                                </span>
                                <span class="block text-xs text-lf-muted"><CurrencyAmount amount={parseFloat(item.amount)} code={view.currency} options={PERSONAL} /></span>
                            </span>
                        </svelte:element>
                        <Switch checked={state === 'on'} mixed={many ? state === 'mixed' : undefined} label={classLabel(t, item.asset_class)} testId="{testId}-class-{item.asset_class}-switch" onchange={(next) => onchange(setClass(filters, item.asset_class, next, view.classes))} />
                    </div>
                    {#if open}
                        <ul class="pb-1 pl-6">
                            {#each item.types as type (type.asset_type)}
                                {@const on = isTypeOn(filters, item.asset_class, type.asset_type)}
                                <li class={row} data-testid="{testId}-type-{type.asset_type}" data-on={on ? 'true' : 'false'}>
                                    <span class="flex min-w-0 flex-1 items-center gap-2">
                                        <img src={getAssetTypeIconUrl(type.asset_type)} alt="" class="h-4 w-4 shrink-0 object-contain" />
                                        <span class="min-w-0 flex-1">
                                            <span use:scrollOnOverflow class="{overflowScrollTextClass} text-sm text-lf-primary">{typeLabel(t, type.asset_type)}</span>
                                            <span class="block text-xs text-lf-muted"><CurrencyAmount amount={parseFloat(type.amount)} code={view.currency} options={PERSONAL} /></span>
                                        </span>
                                    </span>
                                    <Switch checked={on} label={typeLabel(t, type.asset_type)} testId="{testId}-type-{type.asset_type}-switch" onchange={(next) => onchange(setType(filters, item.asset_class, type.asset_type, next, view.classes))} />
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </li>
            {/each}
        </ul>
    </FoldPanel>

    {#if buckets.length > 0}
        <FoldPanel title={$_('allocation.filters.excluded')} count={$_('allocation.filters.countOf', {values: {on: bucketsIn, total: buckets.length}})} testId="{testId}-excluded" open={true}>
            {#snippet control()}
                <Switch checked={bucketsIn === buckets.length} mixed={choiceState(bucketsIn, buckets.length) === 'mixed'} label={$_('allocation.filters.excluded')} testId="{testId}-excluded-all" onchange={setEveryBucket} />
            {/snippet}
            <ul class="divide-y divide-lf-subtle">
                {#each buckets as bucket (bucket)}
                    {@const amount = bucketAmount(bucket)}
                    {@const included = !filters.excludeBuckets.includes(bucket)}
                    <li class={row} data-testid="{testId}-bucket-{bucket}" data-on={included ? 'true' : 'false'}>
                        <span class="min-w-0 flex-1">
                            <span class="block text-sm text-lf-primary">{bucketLabel(t, bucket)}</span>
                            <span class="block text-xs text-lf-muted">
                                {#if amount !== null}<CurrencyAmount amount={parseFloat(amount)} code={view.currency} options={PERSONAL} />{' · '}{/if}{bucketHint(t, bucket)}
                            </span>
                        </span>
                        <Switch checked={included} label={bucketLabel(t, bucket)} testId="{testId}-bucket-{bucket}-switch" onchange={(next) => onchange(setBucketExcluded(filters, bucket, !next))} />
                    </li>
                {/each}
            </ul>
        </FoldPanel>
    {/if}

    <FoldPanel title={$_('allocation.filters.assets')} count={$_('allocation.filters.countOf', {values: {on: assetsIncluded, total: listedAssets.length}})} testId="{testId}-assets">
        {#snippet control()}
            {#if shownAssets.length > 0}
                <Switch
                    checked={shownState === 'on'}
                    mixed={shownState === 'mixed'}
                    label={$_('allocation.filters.assets')}
                    testId="{testId}-assets-all"
                    onchange={(next) =>
                        onchange(
                            setAssetsExcluded(
                                filters,
                                shownAssets.map((asset) => asset.asset_id),
                                !next,
                            ),
                        )}
                />
            {/if}
        {/snippet}
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
                        <span class="flex min-w-0 flex-1 items-center gap-2">
                            <img src={asset.icon_url || getAssetTypeIconUrl(asset.asset_type)} alt="" class="h-4 w-4 shrink-0 object-contain" />
                            <span class="min-w-0 flex-1">
                                <span use:scrollOnOverflow class="{overflowScrollTextClass} text-sm text-lf-primary" title={asset.ticker ? `${asset.name} · ${asset.ticker}` : asset.name} data-testid="{testId}-asset-{asset.asset_id}-name"
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
            <button type="button" class="text-lf-link underline hover:no-underline" onclick={() => onchange(emptyFilters())} data-testid="{testId}-clear">{$_('allocation.filters.clear')}</button>
        {:else}
            <span></span>
        {/if}
        <span class="text-lf-muted">{$_('allocation.filters.remembered')}</span>
    </div>
</div>
