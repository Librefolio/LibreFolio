<!--
  SignalAssetParamControl.svelte — comparison-asset picker for signal parameters.

  A thin adapter over `AssetSelect`: it keeps the signal-parameter contract
  (`value: unknown`, `onchange(number)`, `excludeAssetIds`, `testId`) while the
  list itself, its search and its rendering come from the shared asset picker.

  It used to build its own `SearchSelect` options, which is why the selected
  asset appeared as a bare numeric id: with no `selectedItem` snippet,
  `SearchSelect` prints `option.value` as the primary line, and here that value
  is the asset id (D73).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';

    interface Props {
        value: unknown;
        onchange: (value: number) => void;
        excludeAssetIds?: number[];
        testId?: string;
    }

    let {value, onchange, excludeAssetIds = [], testId = 'signal-comparison-asset-select'}: Props = $props();
    let loadFailed = $state(false);

    let selectedId = $derived(typeof value === 'number' && Number.isInteger(value) ? value : null);

    function handleChange(selected: number | null): void {
        if (selected !== null && selected > 0) onchange(selected);
    }
</script>

<div class="w-64" data-testid="{testId}-control">
    <AssetSelect
        value={selectedId}
        filter={(asset) => !excludeAssetIds.includes(asset.id)}
        sections={[{key: 'benchmark', label: $t('assets.benchmarkSection'), match: (asset) => asset.is_benchmark === true}]}
        restLabel={$t('assets.otherAssetsSection')}
        compact
        dropdownPosition="auto"
        dropdownMinWidth={280}
        placeholder={$t('signals.comparisonAsset.placeholder')}
        testid={testId}
        onchange={handleChange}
        onLoadError={() => (loadFailed = true)}
    />
    {#if loadFailed}
        <p class="mt-1 text-[10px] text-red-500" data-testid="signal-comparison-asset-error">
            {$t('signals.comparisonAsset.loadError')}
        </p>
    {/if}
</div>
