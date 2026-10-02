<script lang="ts">
    import type {Snippet} from 'svelte';
    import {ChevronDown, ChevronRight} from 'lucide-svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import {CARD, SECTION_TITLE} from '../ui';

    interface Props {
        id: string;
        title: string;
        /** Shown next to the title when collapsed (e.g. the number of orders). */
        count?: number | null;
        /** R10.8: a «?» beside the title, outside the toggle. */
        help?: string | null;
        open: boolean;
        ontoggle: (id: string) => void;
        /** Header actions, rendered only while open. */
        actions?: Snippet;
        children: Snippet;
    }

    let {id, title, count = null, help = null, open, ontoggle, actions, children}: Props = $props();
</script>

<section class="{CARD} scroll-mt-20" aria-labelledby="pac-planner-section-{id}-title" data-testid="pac-planner-result-section" data-section={id} data-open={open ? 'true' : 'false'}>
    <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-1">
            <h3 id="pac-planner-section-{id}-title" class="min-w-0">
                <button
                    type="button"
                    class="flex items-center gap-1 rounded text-left {SECTION_TITLE} focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green"
                    aria-expanded={open}
                    aria-controls="pac-planner-section-{id}-body"
                    data-testid="pac-planner-result-section-toggle"
                    onclick={() => ontoggle(id)}
                >
                    {#if open}<ChevronDown size={16} aria-hidden="true" />{:else}<ChevronRight size={16} aria-hidden="true" />{/if}
                    <span>{title}</span>
                    {#if count !== null}<span class="font-normal normal-case tabular-nums">({count})</span>{/if}
                </button>
            </h3>
            {#if help}<HelpTip label={title} {help} testid="pac-planner-result-section-help" />{/if}
        </div>
        {#if open && actions}
            <div class="flex flex-wrap items-center gap-2">{@render actions()}</div>
        {/if}
    </div>
    <div id="pac-planner-section-{id}-body" class="mt-3" hidden={!open}>
        {#if open}{@render children()}{/if}
    </div>
</section>
