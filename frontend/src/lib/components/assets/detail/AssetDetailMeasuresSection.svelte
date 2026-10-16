<!--
  AssetDetailMeasuresSection — the foldable frame of the asset detail page's measures: its header, with the
  «measuring» badge, «Add measure» and the chevron. The page renders the two measure panels inside it
  (children): it keeps their instances, to add points and clear them. Svelte 5 runes.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {ChevronDown, Ruler} from 'lucide-svelte';

    interface Props {
        /** The chart's primary mode, exposed as `data-mode`. */
        mode: string;
        /** The measures of the current mode are unfolded. */
        open: boolean;
        /** The measuring tool of the current mode is on. */
        measureModeActive: boolean;
        /** The current chart has at least two points to measure between. */
        canAddMeasure: boolean;
        ontoggle: () => void;
        onaddmeasure: () => void;
        children: Snippet;
    }

    let {mode, open, measureModeActive, canAddMeasure, ontoggle, onaddmeasure, children}: Props = $props();
</script>

<div class="bg-lf-card text-lf-primary rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle" data-testid="asset-detail-measures-section" data-mode={mode}>
    <div
        class="flex items-center justify-between px-4 py-2.5 cursor-pointer select-none hover:bg-lf-hover transition-colors rounded-t-xl"
        role="button"
        tabindex="0"
        data-testid="asset-detail-measures-toggle"
        onclick={ontoggle}
        onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                ontoggle();
            }
        }}
    >
        <div class="flex items-center gap-2 text-sm font-medium text-lf-secondary">
            <Ruler class="text-violet-500" size={15} />
            {$t('common.measures')}
            {#if measureModeActive}
                <span class="text-[10px] px-1.5 py-0.5 bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 rounded-full">{$t('measure.active')}</span>
            {/if}
        </div>
        <div class="flex items-center gap-1.5">
            <button
                type="button"
                class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md
                           bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400
                           hover:bg-violet-100 dark:hover:bg-violet-900/50
                           transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={!canAddMeasure}
                data-testid="asset-detail-add-measure-btn"
                onclick={(e) => {
                    e.stopPropagation();
                    onaddmeasure();
                }}
                title={$t('common.addMeasure')}
            >
                <span class="text-sm leading-none">+</span>
                <span class="hidden sm:inline">{$t('common.addMeasure')}</span>
            </button>
            <ChevronDown class="transition-transform text-lf-muted {open ? 'rotate-180' : ''}" size={15} />
        </div>
    </div>
    {@render children()}
</div>
