<!--
  TxFormAssetField — the transaction form's asset field, on the shared asset panel (RN-12, A1).

  One field for the single form and the asset transfer pair: `AssetPickerPanel mode="single"`
  over the asset cache, which it loads and orders itself (`assetSelectOrder`: the panel never
  sorts), with the test ids the form always had (`tx-form-asset`, `-trigger`, `-search`,
  `search-select-option-{id}`). It keeps «New asset» at the foot of the list while the row can
  be edited (the consultant, 17/11/2026: A1 replaces a picker, it removes no flow).
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import AssetPickerPanel from '$lib/components/ui/select/AssetPickerPanel.svelte';
    import {assetSelectOrder} from '$lib/components/ui/select/assetPicker';
    import {assetStoreVersion, ensureAssetsLoaded, getAllAssets} from '$lib/stores/reference/assetStore';

    interface Props {
        value: number | null;
        disabled?: boolean;
        onchange: (assetId: number) => void;
        /** «New asset» at the foot of the list; left out, the field offers none. */
        onCreateNew?: () => void;
    }

    let {value, disabled = false, onchange, onCreateNew}: Props = $props();
    let loading = $state(true);

    let catalogue = $derived.by(() => {
        void $assetStoreVersion;
        return assetSelectOrder(getAllAssets());
    });

    onMount(() => {
        let mounted = true;
        // A failed load leaves the list empty, as it did with AssetSelect: the form's own load reports it.
        ensureAssetsLoaded()
            .catch(() => undefined)
            .finally(() => {
                if (mounted) loading = false;
            });
        return () => {
            mounted = false;
        };
    });
</script>

<AssetPickerPanel mode="single" assets={catalogue} blockedLabel="" {value} {disabled} {loading} testId="tx-form-asset" createLabel={onCreateNew ? $t('assets.create') : ''} {onCreateNew} {onchange} />
