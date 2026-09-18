<script lang="ts">
    import {AlertTriangle} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import type {Snippet} from 'svelte';

    /**
     * L4 — "what if…?", closed by default.
     *
     * L4 is the only level that is not homogeneous: it holds three things at
     * increasing distance from observed data, and the internal order has to make
     * that visible rather than leave the reader to guess.
     *
     *   historical replay → real returns from a real period
     *   hypothetical shock → deterministic, on an assumption the user states
     *   simulation         → a probabilistic model, on the model's assumptions
     *
     * Only the last rung is a model. That is the one and only place a beta
     * warning belongs: putting it on the section would tar the replay, which is
     * simply what happened, and a warning that is everywhere is read nowhere.
     */
    interface Props {
        /** The three rungs, supplied by the container in order. */
        replay?: Snippet;
        shock?: Snippet;
        simulation?: Snippet;
    }

    let {replay, shock, simulation}: Props = $props();
</script>

<div class="space-y-4" data-testid="risk-l4">
    {#if replay}
        <div data-testid="risk-l4-replay" data-distance="observed">
            <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200">{$t('risk.levels.l4.replay')}</h4>
            <p class="mb-2 text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l4.replayHint')}</p>
            {@render replay()}
        </div>
    {/if}

    {#if shock}
        <div data-testid="risk-l4-shock" data-distance="assumed">
            <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200">{$t('risk.levels.l4.shock')}</h4>
            <p class="mb-2 text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l4.shockHint')}</p>
            {@render shock()}
        </div>
    {/if}

    {#if simulation}
        <div data-testid="risk-l4-simulation" data-distance="modelled">
            <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200">{$t('risk.levels.l4.simulation')}</h4>
            <p class="mb-2 text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l4.simulationHint')}</p>
            <div class="mb-2 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-900/20" data-testid="risk-l4-model-warning">
                <AlertTriangle size={14} class="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                <p class="text-xs text-amber-800 dark:text-amber-200">{$t('risk.levels.l4.modelWarning')}</p>
            </div>
            {@render simulation()}
        </div>
    {/if}
</div>
