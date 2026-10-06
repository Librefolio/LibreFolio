<script lang="ts">
    import {LoaderCircle} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import type {BuiltRequest} from '../request';
    import {BUTTON_SECONDARY, CARD, HINT, SECTION_TITLE} from '../ui';

    interface Props {
        /** `refresh`: the copied data is being read again; `compute`: the request is with the solver. */
        phase?: 'refresh' | 'compute';
        built?: BuiltRequest | null;
        onstop: () => void;
    }

    let {phase = 'compute', built = null, onstop}: Props = $props();
</script>

<section class={CARD} aria-labelledby="pac-planner-busy-title" data-testid="pac-planner-busy" data-phase={phase} aria-busy="true">
    <h2 id="pac-planner-busy-title" tabindex="-1" class="{SECTION_TITLE} focus:outline-none">{$t('tools.pacAllocator.planner.busy.title', {default: 'Calculation in progress'})}</h2>
    <p class="mt-3 flex items-center gap-2 text-sm" role="status">
        <LoaderCircle class="h-5 w-5 motion-safe:animate-spin" aria-hidden="true" />
        {#if phase === 'refresh'}
            {$t('tools.pacAllocator.planner.busy.refreshing', {default: 'Reading the copied data again from LibreFolio…'})}
        {:else}
            {$t('tools.pacAllocator.planner.busy.searching', {default: 'Validating and searching for the operational plan…'})}
        {/if}
    </p>
    {#if built}
        <p class="mt-3 text-sm" data-testid="pac-planner-busy-snapshot">
            {$t('tools.pacAllocator.planner.busy.snapshot', {
                default: 'Snapshot rev. {revision} · {assets, plural, one {# Asset} other {# Assets}} · {brokers, plural, one {# operative Broker} other {# operative Brokers}} · {routes, plural, one {# BUY route} other {# BUY routes}} · {pairs, plural, one {# FX pair} other {# FX pairs}}',
                values: {revision: built.revision, assets: built.counts.assets, brokers: built.counts.operativeBrokers, routes: built.counts.buyRoutes, pairs: built.counts.fxPairs},
            })}
        </p>
    {/if}
    <p class="mt-1 {HINT}">{$t('tools.pacAllocator.planner.busy.locked', {default: 'The configuration is locked while this request is active.'})}</p>
    <button type="button" class="mt-4 {BUTTON_SECONDARY}" data-testid="pac-planner-busy-stop" onclick={onstop}>{$t('tools.pacAllocator.planner.busy.stop', {default: 'Stop waiting'})}</button>
    <p class="mt-1 {HINT}">{$t('tools.pacAllocator.planner.busy.stopHint', {default: 'Stopping only stops the wait: the server may finish anyway, and that answer is discarded.'})}</p>
</section>
