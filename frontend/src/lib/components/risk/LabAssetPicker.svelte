<!--
  LabAssetPicker — the "+" of the laboratory's selection card.

  It replaces a fixed single-choice select that took one asset per round trip:
  open, search, click, and the list closed again. Here the list stays open, rows
  are checked, and one press adds them all.

  What it lists is the page's own assets that pass the card's filters and are not
  selected yet — the same candidates "Select all" acts on, so the two never
  disagree about what the filters mean. When a filter is on it says so, with a
  way to clear it: a list that silently hides assets looks like a list that lost
  them.

  The rows carry a name, a type and a currency, and nothing else: this page shows
  no money (`asset-global-page-shows-no-money`).
-->
<script lang="ts">
    import {Check, Plus, Search} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import LabPopover from './LabPopover.svelte';
    import {pickerRows, toggleVisibleRows, visibleRowsAllChecked} from './assetSetSelection';
    import {nameOrder} from './correlationHelpers';

    interface PickerAsset {
        id: number;
        display_name: string;
        currency: string;
        icon_url?: string | null;
        asset_type?: string | null;
    }

    interface Props {
        /** The page's assets that pass the card's filters. */
        candidates: readonly PickerAsset[];
        selected: readonly number[];
        /** How many more assets the selection can take. */
        room: number;
        filtersActive: boolean;
        onclearfilters: () => void;
        onadd: (assetIds: number[]) => void;
    }

    let {candidates, selected, room, filtersActive, onclearfilters, onadd}: Props = $props();

    let open = $state(false);
    let query = $state('');
    let checked = $state<number[]>([]);
    let searchInput = $state<HTMLInputElement>();

    let byId = $derived(new Map(candidates.map((asset) => [asset.id, asset])));
    let ordered = $derived(
        nameOrder(
            candidates.map((asset) => asset.id),
            (assetId) => byId.get(assetId)?.display_name ?? '',
        )
            .map((assetId) => byId.get(assetId))
            .filter((asset): asset is PickerAsset => asset !== undefined),
    );
    let rows = $derived(pickerRows(ordered, selected, query, (asset) => `${asset.display_name} ${asset.currency} ${typeLabel(asset.asset_type)}`));
    let visibleIds = $derived(rows.map((asset) => asset.id));
    let allChecked = $derived(visibleRowsAllChecked(checked, visibleIds, room));
    let full = $derived(checked.length >= room);

    /** Every opening starts clean: a half-made choice from the last visit is not this one. */
    $effect(() => {
        if (!open) return;
        query = '';
        checked = [];
        queueMicrotask(() => searchInput?.focus());
    });

    function typeLabel(type: string | null | undefined): string {
        const key = type || 'OTHER';
        return $t(`assets.types.${key}`) || key;
    }

    function toggleRow(assetId: number): void {
        if (checked.includes(assetId)) checked = checked.filter((id) => id !== assetId);
        else if (!full) checked = [...checked, assetId];
    }

    function confirm(close: () => void): void {
        if (checked.length === 0) return;
        onadd(checked);
        close();
    }

    function hideBrokenIcon(event: Event): void {
        (event.currentTarget as HTMLImageElement).style.visibility = 'hidden';
    }
</script>

<LabPopover bind:open testId="risk-asset-add-panel" panelClass="w-80">
    {#snippet trigger({toggle})}
        <Tooltip text={room > 0 ? $t('risk.assetSet.addAsset') : $t('risk.assetSet.maxAssets')} position="top" interactiveChild>
            <button
                type="button"
                class="inline-flex h-7 items-center gap-1 rounded-full border border-dashed border-gray-300 px-2.5 text-xs font-medium text-gray-500 transition-colors hover:border-libre-green hover:text-libre-green disabled:opacity-40 disabled:hover:border-gray-300 disabled:hover:text-gray-500 dark:border-slate-500 dark:text-gray-400"
                onclick={(event) => {
                    // Not up to the Tooltip wrapper: its click would pin the hint over the list.
                    event.stopPropagation();
                    toggle();
                }}
                disabled={room <= 0}
                aria-label={$t('risk.assetSet.addAsset')}
                data-testid="risk-asset-add-button"
            >
                <Plus size={14} />
            </button>
        </Tooltip>
    {/snippet}

    {#snippet children({close})}
        <div class="border-b border-gray-100 p-2 dark:border-slate-700">
            <div class="relative">
                <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                <input
                    bind:this={searchInput}
                    bind:value={query}
                    type="text"
                    class="w-full rounded-md border border-gray-200 bg-white py-1.5 pl-8 pr-2 text-sm text-gray-700 placeholder-gray-400 focus:border-libre-green focus:ring-1 focus:ring-libre-green dark:border-slate-600 dark:bg-slate-700 dark:text-gray-200"
                    placeholder={$t('assets.searchPlaceholder')}
                    onkeydown={(event) => {
                        if (event.key === 'Enter') confirm(close);
                    }}
                    data-testid="risk-asset-add-search"
                />
            </div>
            {#if filtersActive}
                <p class="mt-1.5 flex items-center justify-between gap-2 text-[11px] text-blue-700 dark:text-blue-300">
                    <span>{$t('risk.assetSet.picker.filtersOn')}</span>
                    <button type="button" class="shrink-0 text-libre-green hover:underline" onclick={onclearfilters} data-testid="risk-asset-add-clear-filters">{$t('risk.assetSet.filters.clear')}</button>
                </p>
            {/if}
        </div>

        {#if rows.length > 0}
            <div class="flex items-center justify-between px-3 pt-2 text-[11px] text-gray-500 dark:text-gray-400">
                <button
                    type="button"
                    class="text-libre-green hover:underline disabled:opacity-40 disabled:hover:no-underline"
                    disabled={allChecked && !visibleIds.some((id) => checked.includes(id))}
                    onclick={() => (checked = toggleVisibleRows(checked, visibleIds, room))}
                    data-testid="risk-asset-add-toggle-visible"
                >
                    {allChecked ? $t('risk.assetSet.picker.deselectVisible') : $t('risk.assetSet.picker.selectVisible')}
                </button>
                <span class="tabular-nums">{rows.length}</span>
            </div>
            <div class="max-h-72 overflow-y-auto p-1" role="listbox" aria-multiselectable="true">
                {#each rows as asset (asset.id)}
                    {@const on = checked.includes(asset.id)}
                    <button
                        type="button"
                        role="option"
                        aria-selected={on}
                        class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-200 dark:hover:bg-slate-700"
                        disabled={!on && full}
                        onclick={() => toggleRow(asset.id)}
                        data-testid="risk-asset-add-option-{asset.id}"
                    >
                        <span
                            class="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border transition-colors {on
                                ? 'border-libre-green bg-libre-green text-white dark:border-emerald-400 dark:bg-emerald-400 dark:text-slate-900'
                                : 'border-gray-300 bg-white dark:border-slate-500 dark:bg-slate-900'}"
                        >
                            {#if on}<Check size={12} />{/if}
                        </span>
                        <img src={asset.icon_url || getAssetTypeIconUrl(asset.asset_type)} alt="" class="h-4 w-4 shrink-0 object-contain" onerror={hideBrokenIcon} />
                        <span use:scrollOnOverflow class="{overflowScrollTextClass} min-w-0 flex-1">{asset.display_name}</span>
                        <span class="shrink-0 text-[10px] text-gray-400 dark:text-gray-500">{typeLabel(asset.asset_type)}</span>
                        <span class="w-8 shrink-0 text-right font-mono text-[10px] text-gray-500 dark:text-gray-400">{asset.currency}</span>
                    </button>
                {/each}
            </div>
        {:else}
            <p class="px-3 py-4 text-center text-xs text-gray-400 dark:text-gray-500" data-testid="risk-asset-add-empty">
                {query.trim() ? $t('common.noResults') : $t('risk.assetSet.picker.allSelected')}
            </p>
        {/if}

        {#if full && room > 0}
            <p class="px-3 pb-1 text-[11px] text-amber-600 dark:text-amber-400">{$t('risk.assetSet.maxAssets')}</p>
        {/if}

        <div class="flex items-center justify-end gap-2 border-t border-gray-100 p-2 dark:border-slate-700">
            <button type="button" class="rounded-md px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-slate-700" onclick={close}>{$t('common.cancel')}</button>
            <button type="button" class="rounded-md bg-libre-green px-2.5 py-1 text-xs font-medium text-white hover:bg-libre-green/90 disabled:opacity-40" disabled={checked.length === 0} onclick={() => confirm(close)} data-testid="risk-asset-add-confirm">
                {$t('risk.assetSet.picker.confirm', {values: {count: checked.length}})}
            </button>
        </div>
    {/snippet}
</LabPopover>
