<!--
  LabAssetPicker — the "+" of the laboratory's selection card: `AssetPickerPanel` in multi mode, with
  the lab's own trigger, order, search and words.

  It replaces a fixed single-choice select that took one asset per round trip: open, search, click,
  and the list closed again. Here the list stays open, rows are checked, and one press adds them all.

  It lists the page's own assets that are not selected yet, by name (`nameOrder`, emoji aside). The
  type and currency filters live in the panel, above the list they narrow: on the card they also
  narrowed the quick actions, so "select all" silently meant "select what the filter you forgot about
  lets through".

  Risk's eligibility engine decides which assets the analysis can use in the period
  (`eligibility.ts`). An asset it rules out is listed read-only, in a section of its own, with the
  engine's reasons; one it admits with a warning can be checked, and shows the warning. An asset with
  no verdict is selectable.

  The rows carry a name, a type and a currency, and nothing else: this page shows no money
  (`asset-global-page-shows-no-money`).
-->
<script lang="ts">
    import {Plus} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import AssetPickerPanel from '$lib/components/ui/select/AssetPickerPanel.svelte';
    import type {PickerAsset} from '$lib/components/ui/select/assetPicker';
    import {nameOrder} from './correlationHelpers';
    import type {EligibilityView} from './eligibility';

    interface Props {
        /** The page's whole catalogue. */
        assets: readonly PickerAsset[];
        selected: readonly number[];
        /** How many more assets the selection can take. */
        room: number;
        /** Risk's verdicts, worded. An asset missing from the map is selectable. */
        eligibility: ReadonlyMap<number, EligibilityView>;
        onadd: (assetIds: number[]) => void;
    }

    let {assets, selected, room, eligibility, onadd}: Props = $props();

    let byId = $derived(new Map(assets.map((asset) => [asset.id, asset])));
    let ordered = $derived(
        nameOrder(
            assets.map((asset) => asset.id),
            (assetId) => byId.get(assetId)?.display_name ?? '',
        )
            .map((assetId) => byId.get(assetId))
            .filter((asset): asset is PickerAsset => asset !== undefined),
    );

    function typeLabel(type: string | null | undefined): string {
        const key = type || 'OTHER';
        return $t(`assets.types.${key}`) || key;
    }

    /** The lab searches the name, the currency and the type's label: the words a reader of this card has in front of them. */
    function searchText(asset: PickerAsset): string {
        return `${asset.display_name} ${asset.currency} ${typeLabel(asset.asset_type)}`;
    }
</script>

<AssetPickerPanel mode="multi" assets={ordered} {selected} {room} verdicts={eligibility} blockedLabel={$t('risk.assetSet.picker.notAnalysable')} fullLabel={$t('risk.assetSet.maxAssets')} {searchText} testId="risk-asset-add" {onadd}>
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
</AssetPickerPanel>
