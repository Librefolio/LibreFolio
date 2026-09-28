<!--
  AssetTypeSelect.svelte — Svelte 5

  The asset type field of the asset modal: a searchable two-level select (R14 + R15).

  Base types sit at the root; each family — ETF, Crowdfunding — is a group that opens like the
  indicator families of the signals panel, with its generic member first. Every row shows the
  type's icon, and a subtype's icon is the composite of D52 (family icon + content pastille), so
  the select previews exactly what the rest of the app will draw.

  The tree comes from `buildAssetTypeTree()` in `utils/assetTypes.ts`; the mechanics are the
  generic `TreeSelect` (decision D-K1). Test ids: `${testId}-button` on the trigger, and
  `asset-type-tree-group-{FAMILY}` / `asset-type-tree-option-{TYPE}` on the rows.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {buildAssetTypeTree, type AssetTypeTreeItem} from '$lib/utils/assetTypes';
    import TreeSelect from './TreeSelect.svelte';

    interface Props {
        /** Selected asset type (bindable). */
        value?: string;
        /** Stable selector: the trigger is `${testId}-button`. */
        testId?: string;
        placeholder?: string;
        onchange?: (value: string) => void;
    }

    let {value = $bindable(''), testId, placeholder = '', onchange}: Props = $props();

    let groups = $derived(buildAssetTypeTree($t));
</script>

{#snippet row(item: AssetTypeTreeItem)}
    <div class="flex min-w-0 items-center gap-2 text-sm {item.family ? 'pl-4' : ''}">
        <img src={item.icon} alt="" class="h-6 w-6 shrink-0 object-contain" />
        <span class="min-w-0">
            <span class="block truncate text-gray-800 dark:text-gray-100">{item.label}</span>
            {#if item.hint}
                <span class="block truncate text-[11px] leading-4 text-gray-400 dark:text-gray-500" data-testid="asset-type-tree-hint-{item.value}">{item.hint}</span>
            {/if}
        </span>
    </div>
{/snippet}

<TreeSelect
    bind:value
    {groups}
    {testId}
    {placeholder}
    {onchange}
    item={row}
    showSelected
    testIdPrefix="asset-type-tree"
    defaultExpanded="selected"
    minDropdownWidth={300}
    triggerBorderClass="border-gray-300 dark:border-slate-600"
    searchPlaceholder={$t('assets.typeSelect.searchPlaceholder')}
    noMatchesText={$t('assets.typeSelect.noMatches')}
>
    {#snippet groupLabel(group)}
        <span class="flex min-w-0 items-center gap-2">
            {#if group.icon}
                <img src={group.icon} alt="" class="h-5 w-5 shrink-0 object-contain" />
            {/if}
            <span class="truncate text-xs font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-200">{group.label}</span>
        </span>
    {/snippet}
    {#snippet selectedItem(item)}
        <span class="flex min-w-0 items-center gap-2">
            <img src={item.icon} alt="" class="h-5 w-5 shrink-0 object-contain" />
            <span class="truncate">{item.label}</span>
        </span>
    {/snippet}
</TreeSelect>
