<!--
  AssetDetailSignalsPanel — the foldable frame of the asset detail page's signals: its header and toggle.
  The page renders the signals section inside it (children), only while it is unfolded. Svelte 5 runes.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {ChevronDown, TrendingUp} from 'lucide-svelte';

    interface Props {
        /** The panel is unfolded; kept by the page, which also opens it to configure a signal. */
        open: boolean;
        children: Snippet;
    }

    let {open = $bindable(), children}: Props = $props();
</script>

<div class="bg-lf-card text-lf-primary rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle">
    <div class="relative">
        <button type="button" class="absolute inset-0 z-0 w-full rounded-xl hover:bg-lf-hover" data-testid="asset-detail-signals-toggle" aria-expanded={open} aria-label={$t('common.signals')} onclick={() => (open = !open)}></button>
        <div class="relative z-10 pointer-events-none w-full flex items-center gap-1 px-2 py-1.5" data-testid="asset-detail-signals-header">
            <span class="flex items-center gap-2 px-2 py-1 text-sm font-medium text-lf-secondary">
                <!-- colour: closest role, to review: decorative section icon in blue, mapped to the info state -->
                <TrendingUp class="text-lf-info" size={15} />
                {$t('common.signals')}
            </span>
            <div class="flex-1"></div>
            <span class="flex items-center px-1 py-1 text-lf-secondary" data-testid="asset-detail-signals-chevron">
                <ChevronDown class="transition-transform {open ? 'rotate-180' : ''}" size={15} />
            </span>
        </div>
    </div>
    {#if open}
        <div data-testid="asset-detail-signals-panel" class="px-4 pb-4 border-t border-lf-subtle pt-3">
            {@render children()}
        </div>
    {/if}
</div>
