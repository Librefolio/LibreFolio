<!--
  AssetChip — an asset as a small pill: its icon and its name.

  Born as the Asset Global laboratory's selection chip (F-3b) and extracted when
  the Dashboard's banner needed the same look for the assets it leaves out: one
  component, so the two cannot drift apart. The laboratory owns it; the banner
  mounts it.

  Three variants, and nothing else changes between them:
  - `default`: a grey pill;
  - `warning`: an amber border — the asset is in, with something to know;
  - `excluded`: a dashed border, a faded icon and the name struck through — the
    asset is shown but left out.

  The variant is published as `data-variant`, so a test reads it without
  depending on the classes; it comes after the spread, so nothing passed in can
  contradict it. `help` adds the help cursor, and only a caller that
  wraps the chip in a tooltip should set it. Any `data-*` attribute passed in
  lands on the pill; `trailing` renders after the name (the laboratory's ✕).

  It carries no text of its own, so no translation: the name is the asset's.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import type {HTMLAttributes} from 'svelte/elements';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {STATUS_TONES} from '$lib/theme/toneClasses';

    export type AssetChipVariant = 'default' | 'warning' | 'excluded';

    interface Props extends Omit<HTMLAttributes<HTMLSpanElement>, 'class' | 'children'> {
        asset: {id: number; display_name: string; icon_url?: string | null; asset_type?: string | null};
        variant?: AssetChipVariant;
        /** The help cursor, for a chip a tooltip explains. */
        help?: boolean;
        testId?: string;
        /** Rendered after the name, inside the pill. */
        trailing?: Snippet;
    }

    let {asset, variant = 'default', help = false, testId, trailing, ...rest}: Props = $props();

    const VARIANT_CLASSES: Record<AssetChipVariant, string> = {
        default: STATUS_TONES.riskAssetChip.default,
        warning: `border ${STATUS_TONES.riskAssetChip.warning}`,
        excluded: `border border-dashed ${STATUS_TONES.riskAssetChip.excluded}`,
    };

    let excluded = $derived(variant === 'excluded');

    function hideBrokenIcon(event: Event): void {
        (event.currentTarget as HTMLImageElement).style.visibility = 'hidden';
    }
</script>

<span class="inline-flex h-7 items-center gap-1.5 rounded-full py-1 pl-1.5 pr-1 text-xs {help ? 'cursor-help' : ''} {VARIANT_CLASSES[variant]}" data-testid={testId} {...rest} data-variant={variant}>
    <img src={asset.icon_url || getAssetTypeIconUrl(asset.asset_type)} alt="" class="h-4 w-4 shrink-0 object-contain {excluded ? 'opacity-50' : ''}" onerror={hideBrokenIcon} />
    <span class={excluded ? 'line-through decoration-lf-input' : ''}>{asset.display_name}</span>
    {@render trailing?.()}
</span>
