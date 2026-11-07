<script lang="ts">
    import {LoaderCircle} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import type {BuiltRequest} from '../request';
    import {BUTTON_SECONDARY, CARD, HINT, SECTION_TITLE} from '../ui';

    interface Props {
        /** `refresh`: the copied data is being read again; `compute`: the request is with the solver. */
        phase?: 'refresh' | 'compute';
        built?: BuiltRequest | null;
        /**
         * How long the tool client waits for the answer before it gives up (the descriptor's `client_timeout_ms`). With it the bar fills with the
         * time that passes; without it, or while the copied data is read again, the bar only moves. It measures the wait, never the work done:
         * the solver reports no progress (P4a).
         */
        timeoutMs?: number | null;
        onstop: () => void;
    }

    let {phase = 'compute', built = null, timeoutMs = null, onstop}: Props = $props();

    /** The wait starts when the panel does: one panel per request, one per re-read of the copied data. */
    const startedAt = Date.now();
    let elapsedMs = $state(0);
    const TICK_MS = 250;

    // A timer, not an animation frame: a tab in the background keeps counting the wait.
    $effect(() => {
        const timer = setInterval(() => (elapsedMs = Date.now() - startedAt), TICK_MS);
        return () => clearInterval(timer);
    });

    const limited = $derived(phase === 'compute' && timeoutMs !== null && timeoutMs > 0);
    const limitSeconds = $derived(limited && timeoutMs !== null ? Math.round(timeoutMs / 1000) : 0);
    const elapsedSeconds = $derived(Math.min(Math.floor(elapsedMs / 1000), limitSeconds || Number.POSITIVE_INFINITY));
    const percent = $derived(limited && timeoutMs !== null ? Math.min(100, (elapsedMs / timeoutMs) * 100) : 0);
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
    <div class="mt-3" data-testid="pac-planner-busy-wait">
        <!-- bg-lf-neutral track, bg-lf-checked fill: the roles of the other bars of the planner (AssetTable). -->
        <div
            class="h-2 w-full overflow-hidden rounded-full bg-lf-neutral"
            role="progressbar"
            aria-label={$t('tools.pacAllocator.planner.busy.barLabel', {default: 'Time waited'})}
            aria-valuemin={0}
            aria-valuemax={limited ? limitSeconds : undefined}
            aria-valuenow={limited ? elapsedSeconds : undefined}
            data-testid="pac-planner-busy-bar"
            data-mode={limited ? 'elapsed' : 'indeterminate'}
        >
            {#if limited}
                <div class="h-full rounded-full bg-lf-checked transition-[width] duration-300 motion-reduce:transition-none" style="width: {percent}%" data-testid="pac-planner-busy-bar-fill"></div>
            {:else}
                <div class="indeterminate h-full rounded-full bg-lf-checked"></div>
            {/if}
        </div>
        {#if limited}
            <p class="mt-1 {HINT} tabular-nums" data-testid="pac-planner-busy-elapsed">
                {$t('tools.pacAllocator.planner.busy.elapsed', {default: 'Waiting {elapsed} s of at most {limit} s', values: {elapsed: elapsedSeconds, limit: limitSeconds}})}
            </p>
        {/if}
    </div>
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

<style>
    /* Without a known limit: a segment that slides along the track. Still bar when motion is reduced. */
    @keyframes pac-busy-slide {
        from {
            transform: translateX(-100%);
        }
        to {
            transform: translateX(250%);
        }
    }
    .indeterminate {
        width: 40%;
    }
    @media (prefers-reduced-motion: no-preference) {
        .indeterminate {
            animation: pac-busy-slide 1.4s ease-in-out infinite;
        }
    }
</style>
