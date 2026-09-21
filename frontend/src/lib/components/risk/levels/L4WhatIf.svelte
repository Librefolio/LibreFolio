<script lang="ts">
    import {AlertTriangle} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import type {Snippet} from 'svelte';

    import RiskBetaBanner from '../RiskBetaBanner.svelte';

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
     *
     * WHY THE BETA BANNER LIVES HERE, AND ONLY HERE. It used to sit above every
     * risk surface, which said the whole subsystem was provisional. It is not
     * any more — L1, L2 and L3 rest on observed facts and have left beta. This
     * rung has not, and the reason is recorded rather than general: the
     * simulation answers the *window* rather than the portfolio, because the
     * bootstrap resamples each observation `horizon / observations` times, so a
     * short window under a long horizon extrapolates a single quarter across a
     * year. Asking for more history can silently return the same history, so the
     * denominator of any ratio guard is inflated and saturable — which is why no
     * threshold is shipped yet and the rung is still declared beta instead.
     *
     * Two notices, not one, and they are not redundant: the banner is about
     * *maturity* and is the one that gets deleted the day the defect is fixed;
     * the amber warning below it is about *epistemics* and is permanent, because
     * a model stays a model. Merging them would turn that future deletion into a
     * rewrite of prose.
     *
     * The `{#if simulation}` guard is load-bearing, not cosmetic: a surface that
     * supplies no simulation snippet — Asset Global mounts replay alone — cannot
     * inherit the banner by accident. The scope of the claim is structural.
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
            <div class="mb-2">
                <RiskBetaBanner scope="simulation" />
            </div>
            <div class="mb-2 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-900/20" data-testid="risk-l4-model-warning">
                <AlertTriangle size={14} class="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                <p class="text-xs text-amber-800 dark:text-amber-200">{$t('risk.levels.l4.modelWarning')}</p>
            </div>
            {@render simulation()}
        </div>
    {/if}
</div>
