<!--
  SignalAssetParamControl.svelte — comparison-asset picker for signal parameters (Rolling Beta).

  A thin adapter over the shared asset panel (`AssetPickerPanel mode="single"`, RN-12): it keeps the
  signal-parameter contract (`value: unknown`, `onchange(number)`, `excludeAssetIds`, `testId`) while
  the list, its search, its filters and its rows come from the panel, as on the benchmark picker and
  the «Confronto Asset» signal. The panel never sorts and never loads: the control orders the cache
  (`assetSelectOrder`) and loads it. No asset is created from here (the developer, 16/11/2026).

  The chart's own asset (`mainAssetId`) is listed apart, with the reason «Confronto Asset» gives, and cannot be chosen:
  an asset compared with itself says nothing, in any comparison signal (RN-12b, the consultant, 17/11/2026). A saved
  choice of it stays in the trigger, untouched: the picker only stops new ones.

  It once built its own `SearchSelect` options, and the selected asset appeared as a bare numeric id
  (D73): the panel's trigger shows the asset itself.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import AssetPickerPanel from '$lib/components/ui/select/AssetPickerPanel.svelte';
    import {assetSelectOrder, type PickerVerdict} from '$lib/components/ui/select/assetPicker';
    import {assetStoreVersion, ensureAssetsLoaded, getAllAssets} from '$lib/stores/reference/assetStore';

    interface Props {
        value: unknown;
        onchange: (value: number) => void;
        excludeAssetIds?: number[];
        /** The asset the chart shows: ruled out, with its reason. */
        mainAssetId?: number | null;
        testId?: string;
    }

    let {value, onchange, excludeAssetIds = [], mainAssetId = null, testId = 'signal-comparison-asset-select'}: Props = $props();
    let loading = $state(true);
    let loadFailed = $state(false);

    let selectedId = $derived(typeof value === 'number' && Number.isInteger(value) ? value : null);

    /** An excluded asset leaves the list, the current choice never: the panel shows only a value it is given. */
    let catalogue = $derived.by(() => {
        void $assetStoreVersion;
        return assetSelectOrder(getAllAssets().filter((asset) => !excludeAssetIds.includes(asset.id) || asset.id === selectedId));
    });

    let verdicts = $derived.by((): ReadonlyMap<number, PickerVerdict> | undefined => {
        if (mainAssetId === null || mainAssetId <= 0) return undefined;
        return new Map([[mainAssetId, {level: 'ineligible', codes: ['main-asset'], texts: [$t('signals.comparisonAsset.isMainAsset')]} satisfies PickerVerdict]]);
    });

    onMount(() => {
        let mounted = true;
        ensureAssetsLoaded().then(
            () => {
                if (mounted) loading = false;
            },
            () => {
                if (!mounted) return;
                loading = false;
                loadFailed = true;
            },
        );
        return () => {
            mounted = false;
        };
    });

    function handleChange(selected: number): void {
        if (selected > 0) onchange(selected);
    }
</script>

<div class="w-64" data-testid="{testId}-control">
    <AssetPickerPanel
        mode="single"
        assets={catalogue}
        {verdicts}
        blockedLabel={$t('signals.comparisonAsset.blocked')}
        value={selectedId}
        sections={[{key: 'benchmark', label: $t('assets.benchmarkSection'), match: (asset) => asset.is_benchmark === true}]}
        restLabel={$t('assets.otherAssetsSection')}
        dropdownPosition="auto"
        dropdownMinWidth={280}
        placeholder={$t('signals.comparisonAsset.placeholder')}
        {loading}
        {testId}
        onchange={handleChange}
    />
    {#if loadFailed}
        <p class="mt-1 text-[10px] text-lf-danger" data-testid="signal-comparison-asset-error">
            {$t('signals.comparisonAsset.loadError')}
        </p>
    {/if}
</div>
