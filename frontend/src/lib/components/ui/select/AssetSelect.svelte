<!--
  AssetSelect.svelte — Reusable asset picker backed by `assetStore`.

  Wraps `SearchSelect` with options derived from the global asset cache.
  The cache is loaded lazily (`ensureAssetsLoaded()` is called on mount), so
  the component is self-sufficient — callers just bind a `value: number | null`.

  Each option shows: [type icon] display_name [(currency)]; inactive assets are
  greyed out via `disabled`.

  Pattern: Svelte 5 runes, dark mode via Tailwind, `data-testid` for E2E.

  Used by: TransactionStagingModal, TransferPromoteModal, future BRIM staging.
  Migrate other asset_id pickers (e.g. DistributionEditor) to use this when convenient.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import SearchSelect from './SearchSelect.svelte';
    import type {SelectOption} from './types';
    import {ensureAssetsLoaded, getAllAssets, assetStoreVersion, type AssetInfo} from '$lib/stores/assetStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

    interface Props {
        /** Currently selected asset id (null = none). */
        value: number | null;
        /** Disable the select. */
        disabled?: boolean;
        /** Optional filter applied on top of the cache (e.g. only same currency). */
        filter?: (a: AssetInfo) => boolean;
        /** Placeholder when no value is selected. */
        placeholder?: string;
        /** Test id for E2E targeting. */
        testid?: string;
        /** Compact trigger padding (matches standard inputs). */
        compact?: boolean;
        /** Change callback (number | null). */
        onchange?: (value: number | null) => void;
    }

    let {value = $bindable(null), disabled = false, filter, placeholder, testid = 'asset-select', compact = false, onchange}: Props = $props();

    let loading = $state(true);

    onMount(async () => {
        await ensureAssetsLoaded();
        loading = false;
    });

    /** Build SearchSelect options from the asset store cache. */
    let options = $derived.by<SelectOption[]>(() => {
        // Subscribe to version counter so the list re-derives on cache mutation.
        void $assetStoreVersion;
        const all = getAllAssets();
        const filtered = filter ? all.filter(filter) : all;
        // Sort: active first, then by display_name.
        filtered.sort((a, b) => {
            if (a.active !== b.active) return a.active ? -1 : 1;
            return a.display_name.localeCompare(b.display_name);
        });
        return filtered.map<SelectOption>((a) => ({
            value: String(a.id),
            label: a.display_name,
            searchText: [a.identifier_isin, a.identifier_ticker, a.currency, a.asset_type].filter(Boolean).join(' '),
            disabled: !a.active,
            icon: a.icon_url || (a.asset_type ? getAssetTypeIconUrl(a.asset_type) : undefined),
            data: a,
        }));
    });

    let stringValue = $derived(value == null ? '' : String(value));

    function handleChange(v: string) {
        const next = v === '' ? null : Number(v);
        value = next;
        onchange?.(next);
    }

    function hideOnError(e: Event) {
        const img = e.currentTarget as HTMLImageElement | null;
        if (img) img.style.display = 'none';
    }
</script>

<div data-testid={testid}>
    <SearchSelect value={stringValue} {options} {disabled} {loading} placeholder={placeholder ?? $t('common.select')} {compact} onchange={handleChange}>
        {#snippet item(option)}
            {@const a = option.data as AssetInfo | undefined}
            <div class="flex items-center gap-2 min-w-0">
                {#if option.icon}
                    <img src={option.icon} alt="" class="w-4 h-4 rounded-sm object-contain shrink-0" onerror={hideOnError} />
                {/if}
                <span class="truncate text-sm">{option.label}</span>
                {#if a?.currency}
                    <span class="ml-auto text-[10px] font-mono uppercase opacity-60 shrink-0">{a.currency}</span>
                {/if}
            </div>
        {/snippet}
    </SearchSelect>
</div>
