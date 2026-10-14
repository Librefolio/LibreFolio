<script lang="ts">
    import {Copy, PenLine} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import {ORIGIN_FALLBACKS} from '../labels';
    import {BADGE} from '../ui';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        origin: 'copied' | 'manual';
        /** A copied fact the user changed afterwards. */
        modified?: boolean;
        /** Copy or entry time, already formatted. */
        when?: string | null;
        testid?: string;
    }

    let {origin, modified = false, when = null, testid}: Props = $props();

    const tone = $derived(origin === 'manual' ? BADGE.neutral : modified ? BADGE.warning : BADGE.info);
    const label = $derived(modified ? 'modified' : origin);
</script>

<span class={tone} data-testid={testid} data-origin={origin} data-modified={modified ? 'true' : 'false'}>
    {#if origin === 'copied'}
        <Copy size={12} aria-hidden="true" />
    {:else}
        <PenLine size={12} aria-hidden="true" />
    {/if}
    {$t(`${PLANNER_KEY}.origin.${label}`, {default: ORIGIN_FALLBACKS[label]})}
    {#if when}
        <span class="font-normal">· {when}</span>
    {/if}
</span>
