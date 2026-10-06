<!--
  AssetBrowseOrder — publishes the asset list's order for the detail page's ‹ prev / next ›
  (K step 16, item 2). Renders nothing.

  The list hands over its usage panels as shown (filters applied) and its view; in the table view
  each panel's `AssetTable` also publishes its own row order (sort and column filters). See
  `assetBrowse.ts`. A separate component so the list page — rewritten in parallel by the risk
  family — carries only the line that mounts it.
-->
<script lang="ts">
    import {ASSET_BROWSE_PANEL_ORDER, clearAssetTableOrder, publishAssetListOrder, type AssetPanelId} from './assetBrowse';

    interface Props {
        /** The list's view: the grid ignores table orders. */
        view: 'grid' | 'list';
        /** The usage panels as shown, top to bottom. */
        panels: ReadonlyArray<{id: AssetPanelId; items: ReadonlyArray<{id: number}>}>;
    }

    let {view, panels}: Props = $props();

    $effect(() => {
        publishAssetListOrder(
            view,
            panels.map((panel) => ({id: panel.id, ids: panel.items.map((item) => item.id)})),
        );
        // In the grid the tables are gone: their orders must not resurface in a later table view
        // before the tables have published again.
        if (view === 'grid') for (const panel of ASSET_BROWSE_PANEL_ORDER) clearAssetTableOrder(panel);
    });
</script>
